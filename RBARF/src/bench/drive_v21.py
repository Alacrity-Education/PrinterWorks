#!/usr/bin/env python3
"""Bench proof for the rbarf_v21 firmware (task 5).

Drives the flashed v2.1 decode firmware end to end: send N distinct v2.1
frames x R reps on the WS2812 pin, collect the DEC:<data>:<eps>:<status>
and TIM:<ticks> reports, score every capture against ground truth
(single-shot: OK/CHASED must match the 16 DATA bytes exactly; REFUSE is a
missed frame; an emitted mismatch is a CATASTROPHIC and fails the run),
and measure the decode time two independent ways:

  on-chip   TIM:<ticks> from the firmware's TIM1 stopwatch around
            ws_decode_ex (16 us/tick at nominal 16 MHz; the decode runs
            at factory trim, eps ~ -1.07%, so real time = ticks * 16 us
            / (1 - 0.0107) -- the printed ms uses that correction)
  host      t(DEC line complete) - t(frame sent) - capture tail (256
            loops = 0.64 ms) - DEC line UART transit at 9600 baud
            (cross-check only; USB batching adds ~ms jitter)

DECODE TIME IS A BLIND WINDOW: the firmware cannot capture while it
decodes + reports; a frame sent before the next READY is silently lost
(single transmission -- nothing re-covers it).  The run therefore also
measures the full re-arm latency t(READY) - t(frame sent): the MINIMUM
INTER-FRAME GAP the host must respect.

Usage: python3 bench/drive_v21.py [--reps 3] [--port PORT] [--out FILE]

Needs the rbarf_v21 firmware flashed first:
    python3 flash.py --ihx build/rbarf_v21.ihx flash-only
"""

import argparse
import glob
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
from testprobe import TestProbe  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from patterns import PATTERNS, PATTERNS_V21, frame  # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600

# 10 distinct frames spanning the stress classes (incl. the historically
# chase-heavy blocks/runs/rnd patterns -- an honest sample, not a soft one)
BENCH_PATTERNS = ["zeros", "ones", "aa", "count", "blocks",
                  "nibbles", "dense", "runs", "rnd1", "rnd3"]

CHAR_MS = 10.0 / BAUD * 1000.0          # 8N1: 10 bit times per char
FACTORY_EPS = -0.0107                   # this unit at trim 0 (TRIM_SWEEP.md)
TICK_MS = 0.016 / (1.0 + FACTORY_EPS)   # TIM1 tick, real ms (clock slow)
CAPTURE_MS = 256 * 40 / 16e6 * 1e3 / (1.0 + FACTORY_EPS)  # 256 loops


class LineReader:
    """acquire.py's line assembler + a completion timestamp per line."""

    def __init__(self):
        self.buf = bytearray()
        self.lines = []                  # (t_monotonic, str)
        self.cond = threading.Condition()

    def feed(self, data: bytes) -> None:
        now = time.monotonic()
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[: nl + 1]
                if line:
                    self.lines.append(
                        (now, line.decode("ascii", errors="replace")))
            self.cond.notify_all()

    def wait_for(self, prefix: str, timeout: float):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, line) in enumerate(self.lines):
                    if line.startswith(prefix):
                        del self.lines[: i + 1]
                        return t, line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, None
                self.cond.wait(remaining)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_fw" /
        "bench_v21_results.json"))
    args = ap.parse_args()

    port = probe_port(args.port)

    reader = LineReader()
    rows = []
    n_ok = n_chase = n_refuse = n_cat = n_proto = 0

    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        banner = None
        for cycle in range(1, 4):        # bench rule: stop after 3 cycles
            print(f"[bench] power cycle {cycle}/3 (5 s SWIM window)...")
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            _, banner = reader.wait_for("RBARF-V21", 15.0)
            if banner is not None:
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no RBARF-V21 banner after 3 "
                             "power cycles -- STOP (bench rule)")
        print(f"[bench] firmware banner: {banner!r}")

        total = len(BENCH_PATTERNS) * args.reps
        done = 0
        # the firmware prints ONE READY per cycle; consume it exactly once
        # (it is both the previous frame's re-arm mark and the next gate)
        t_armed, rdy = reader.wait_for("READY", 10.0)
        if rdy is None:
            raise SystemExit("[bench] FAIL: no first READY")
        for name in BENCH_PATTERNS:
            data = PATTERNS[name]
            payload = PATTERNS_V21[name]
            fr = frame(payload)
            for rep in range(args.reps):
                time.sleep(0.05)         # firmware arms ~1 ms after READY
                t0 = time.monotonic()
                probe.ws2812_write(fr)
                t1 = time.monotonic()
                t_dec, dec = reader.wait_for("DEC:", 15.0)
                if dec is None:
                    raise SystemExit(f"[bench] FAIL: no DEC line for "
                                     f"{name} rep {rep}")
                t_tim, tim = reader.wait_for("TIM:", 5.0)
                t_rdy2, rdy2 = reader.wait_for("READY", 10.0)
                if rdy2 is None:
                    raise SystemExit(f"[bench] FAIL: no re-arm READY after "
                                     f"{name} rep {rep}")
                t_armed = t_rdy2

                row = {"pattern": name, "rep": rep, "line": dec}
                try:
                    _, hexdata, eps_s, status = dec.split(":")
                    ticks = int(tim.split(":")[1]) if tim else None
                    eps = int(eps_s)
                except (ValueError, AttributeError, IndexError):
                    n_proto += 1
                    row["verdict"] = "PROTOCOL-ERROR"
                    rows.append(row)
                    print(f"[bench] {done+1:3d}/{total} {name} r{rep}: "
                          f"BAD LINE {dec[:60]!r}")
                    done += 1
                    continue

                # ---- score against ground truth (single-shot) ----------
                if status in ("OK", "CHASED"):
                    if hexdata.lower() == data.hex().lower():
                        verdict = "DELIVERED"
                        if status == "OK":
                            n_ok += 1
                        else:
                            n_chase += 1
                    else:
                        verdict = "CATASTROPHIC"     # emitted != truth
                        n_cat += 1
                elif status == "REFUSE":
                    verdict = "MISSED"
                    n_refuse += 1
                    if hexdata != "00" * 16:
                        verdict = "PROTOCOL-ERROR"   # refuse must be zeros
                        n_proto += 1
                else:
                    verdict = "PROTOCOL-ERROR"
                    n_proto += 1

                # ---- timing --------------------------------------------
                tim_ms = ticks * TICK_MS if ticks is not None else None
                transit_ms = (len(dec) + 2) * CHAR_MS / (1.0 + FACTORY_EPS)
                host_ms = (t_dec - t0) * 1e3 - CAPTURE_MS - transit_ms
                rearm_ms = (t_rdy2 - t0) * 1e3 if t_rdy2 else None

                row.update(verdict=verdict, status=status, eps_centi=eps,
                           tim_ticks=ticks, tim_ms=tim_ms, host_ms=host_ms,
                           rearm_ms=rearm_ms, uplink_ms=(t1 - t0) * 1e3)
                rows.append(row)
                done += 1
                msg = (f"[bench] {done:3d}/{total} {name:8s} r{rep}: "
                       f"{verdict:12s} {status:6s} eps {eps/100.0:+.2f}%")
                if tim_ms is not None:
                    msg += f"  decode {tim_ms:.1f} ms (chip)"
                msg += f" / {host_ms:.1f} ms (host)"
                if rearm_ms is not None:
                    msg += f"  re-arm {rearm_ms:.1f} ms"
                print(msg)

    # ---- summary ------------------------------------------------------
    delivered = n_ok + n_chase
    scored = delivered + n_refuse + n_cat
    tims = [r["tim_ms"] for r in rows if r.get("tim_ms") is not None]
    hosts = [r["host_ms"] for r in rows if r.get("host_ms") is not None]
    rearms = [r["rearm_ms"] for r in rows if r.get("rearm_ms") is not None]
    print()
    print("=" * 70)
    print(f"BENCH PROOF: {delivered}/{total} delivered correct "
          f"({n_ok} OK + {n_chase} CHASED), {n_refuse} refused (missed), "
          f"{n_cat} CATASTROPHIC, {n_proto} protocol errors")
    if tims:
        print(f"decode time (on-chip TIM1, factory-trim-corrected): "
              f"min {min(tims):.1f}  mean {sum(tims)/len(tims):.1f}  "
              f"max {max(tims):.1f} ms")
    if hosts:
        print(f"decode time (host wall-clock cross-check):          "
              f"min {min(hosts):.1f}  mean {sum(hosts)/len(hosts):.1f}  "
              f"max {max(hosts):.1f} ms")
    if rearms:
        print(f"BLIND WINDOW / min inter-frame gap (frame start -> READY): "
              f"max {max(rearms):.1f} ms")
    print("=" * 70)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "firmware": "rbarf_v21.c + decode.c + scan.s (ND_DATA=16, "
                        "CHECK_EN=1, USE_ASM_SCAN=1, CAP_BYTES=256)",
            "tick_ms": TICK_MS, "capture_ms": CAPTURE_MS,
            "factory_eps": FACTORY_EPS,
            "scoring": "single transmission: DELIVERED = emitted AND equal "
                       "to ground truth; REFUSE = missed frame; emitted != "
                       "truth = CATASTROPHIC (must be 0)",
        },
        "summary": {
            "total": total, "delivered": delivered, "ok": n_ok,
            "chased": n_chase, "refused": n_refuse, "catastrophic": n_cat,
            "protocol_errors": n_proto,
            "tim_ms_min": min(tims) if tims else None,
            "tim_ms_mean": sum(tims) / len(tims) if tims else None,
            "tim_ms_max": max(tims) if tims else None,
            "rearm_ms_max": max(rearms) if rearms else None,
        },
        "rows": rows,
    }, indent=1))
    print(f"[bench] wrote {out}")

    if n_cat or n_proto:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
