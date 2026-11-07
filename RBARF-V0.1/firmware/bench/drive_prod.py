#!/usr/bin/env python3
"""Bench proof for the PRODUCTION firmware (rbarf_prod.c, ND_DATA=48).

Drives the flashed VERBOSE production image end to end: 10 distinct
PRODUCTION frames (48-byte DATA payloads built with bench/crc.py's
build_payload) x N reps, each put on the wire EXACTLY ONCE (single
transmission, docs/PROTOCOL.md), and scores every delivered DEC line against
ground truth.

Production UART protocol (rbarf_prod.c):
    banner   "RBARF-P 1"
    report   "D:<status>:<eps>"          status = O | C | R<cause 1..8>
                                        eps = decimal centi-% (terse) or
                                        "x<4 hex>" int16 (VERBOSE, v2.3+)
    verbose  "V:<96 hex DATA>"           only after a verified decode

Scoring (single transmission):
    DELIVERED   status O/C and the 48 V: bytes == ground truth
    CATASTROPHIC status O/C but bytes != truth        -- must be 0
    MISSED      status R<cause> (refusal) or no D line at all
    PROTOCOL-ERROR anything else

The firmware has NO ready mark: it arms ~1.2 ms capture windows back to
back between render ticks, so a frame that lands during a render
(~0.4-0.66 ms every 40 ms since PROD_CLOSURE.md SS16 dropped the render
from 100 Hz to 25 Hz) or during the decode blind window is lost with no
report at all.  That is a real production outcome and is scored MISSED.

Usage: python3 bench/drive_prod.py [--reps 3] [--rate-probe]
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
from crc import build_payload_v23  # noqa: E402
from epsfmt import parse_eps  # noqa: E402
from patterns import HEADER_V23, TRAILER_V23  # noqa: E402

HEADER = HEADER_V23                       # FF AA 65
TRAILER = TRAILER_V23                     # 9A 00 FF (trailer[1] = zeros probe)

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600

CHAR_MS = 10.0 / BAUD * 1000.0            # 8N1: 10 bit times per char
FACTORY_EPS = -0.0107                     # this unit at trim 0
CAPTURE_MS = 288 * 40 / 16e6 * 1e3 / (1.0 + FACTORY_EPS)   # 288 loops
FRAME_TX_MS = 60 * 8 * 1.25e-3            # 60 bytes @ 1.25 us/bit = 0.60 ms

CAUSE = {"1": "lock", "2": "marker", "3": "infeasible", "4": "labelerr",
         "5": "emitgate", "6": "nocand", "7": "admit", "8": "chase"}


def frame(data48: bytes) -> bytes:
    """DATA(48) -> full 60-byte v2.3 wire frame (= exactly 20 LEDs).

    v2.3 sizing: 3 (HEADER) + 48 (DATA) + 6 (CRC-16 x3) + 3 (TRAILER).
    """
    payload = build_payload_v23(data48)   # DATA + (C16_HI C16_LO) x3
    assert len(payload) == 54
    fr = HEADER + payload + TRAILER
    assert len(fr) == 60
    return fr


def _lcg(seed, n):
    x, out = seed, bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def _mk(base, flags):
    """base = 24 B (8 LEDs GRB), flags = 24 B (flag LEDs) -> 48 B DATA."""
    b = bytearray(24)
    b[:len(base)] = base
    f = bytearray(24)
    f[:len(flags)] = flags
    return bytes(b + f)


# 8 distinct LED colors (GRB)
COLORS = bytes([
    0x40, 0x00, 0x00,   # green
    0x00, 0x40, 0x00,   # red
    0x00, 0x00, 0x40,   # blue
    0x40, 0x40, 0x00,   # yellow
    0x00, 0x40, 0x40,   # magenta
    0x40, 0x00, 0x40,   # cyan
    0x20, 0x20, 0x20,   # white-ish
    0x10, 0x08, 0x04,   # dim amber
])

# ---- the 10 production frames ----------------------------------------
# flags[0]=mode 1=dur 2=mask 3..5=alt/bg 6..8=maskcolor (6=features and
# 7..22=seq nibbles in mode 3) 23=gamma
FRAMES = [
    # 1. static colors, gamma on
    ("colors", _mk(COLORS, [0x00, 0x00, 0x00, 0, 0, 0, 0, 0, 0] +
                   [0] * 14 + [0x02])),
    # 2. all dark -- degenerate all-zero DATA, max swallowed-0 stress
    ("dark", bytes(48)),
    # 3. all bright -- max merged-1 stress
    ("full", _mk(bytes([0xFF] * 24),
                 [0x00, 0x00, 0x00, 0, 0, 0, 0, 0, 0] + [0] * 14 + [0x02])),
    # 4. blink, cycle 1000 ms, mask 0xA5 -> LEDs 0,2,5,7 forced to maskcolor
    ("blink", _mk(COLORS,
                  [0x01, 0x14, 0xA5, 0x00, 0x00, 0x30,      # alt = blue
                   0x30, 0x30, 0x00] + [0] * 14 + [0x02])), # maskcolor
    # 5. fade, cycle 2000 ms
    ("fade", _mk(COLORS,
                 [0x02, 0x28, 0x00, 0x00, 0x00, 0x00] + [0] * 17 + [0x02])),
    # 6. sequence 0..7, terminator, no fading
    ("seq_plain", _mk(COLORS,
                      [0x03, 0x1E, 0x00, 0x02, 0x00, 0x02,  # bg dim
                       0x00,                                 # features = 0
                       0x01, 0x23, 0x45, 0x67, 0xFF] +      # seq + term
                      [0] * 11 + [0x02])),
    # 7. sequence with pauses (nibble >= 8) + duplicates + early terminator
    ("seq_pause", _mk(COLORS,
                      [0x03, 0x28, 0x00, 0x00, 0x04, 0x00,
                       0x0C,                                 # features: gsz4
                       0x08, 0x81, 0x18, 0x3F, 0xFF] +
                      [0] * 11 + [0x02])),
    # 8. HOST-EXPANDED preset 0x04 "spin"  (flags[0]=3, flags[7..]=01 57 62 FF)
    ("preset_spin", _mk(COLORS,
                        [0x03, 0x1E, 0x00, 0x00, 0x00, 0x08,
                         0x01,                               # features: fade3
                         0x01, 0x57, 0x62, 0xFF] +
                        [0] * 12 + [0x02])),
    # 9. HOST-EXPANDED preset 0x07 "rain rev" (flags[7..]=26 75 10 43 FF)
    ("preset_rainR", _mk(COLORS,
                         [0x03, 0x32, 0x00, 0x00, 0x00, 0x00,
                          0x02,                              # features: fade2
                          0x26, 0x75, 0x10, 0x43, 0xFF] +
                         [0] * 11 + [0x02])),
    # 10. pseudo-random 48 B -- worst-case mixed-run decoder stress
    ("rnd", _lcg(0xC0FFEE, 48)),
]
assert len(FRAMES) == 10
assert all(len(d) == 48 for _, d in FRAMES)
assert len({d for _, d in FRAMES}) == 10, "frames must be distinct"


class LineReader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []                  # (t_start, t_done, str)
        self.banners = 0                 # MCU boot banners seen (resets)
        self.t_chunk0 = None
        self.cond = threading.Condition()

    def feed(self, data: bytes) -> None:
        now = time.monotonic()
        with self.cond:
            if not self.buf:
                self.t_chunk0 = now
            t0 = self.t_chunk0
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[: nl + 1]
                if line:
                    txt = line.decode("ascii", errors="replace")
                    if txt.startswith("RBARF-P"):
                        self.banners += 1
                    self.lines.append((t0, now, txt))
                t0 = now
                self.t_chunk0 = now
            self.cond.notify_all()

    def wait_for(self, prefix, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (ts, td, line) in enumerate(self.lines):
                    if line.startswith(prefix):
                        del self.lines[: i + 1]
                        return ts, td, line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, None, None
                self.cond.wait(remaining)

    def drop_all(self):
        with self.cond:
            self.lines.clear()
            self.buf.clear()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rate-probe", action="store_true")
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_prod" /
        "bench_prod_results.json"))
    args = ap.parse_args()

    port = probe_port(args.port)

    reader = LineReader()
    rows = []
    n_ok = n_chase = n_refuse = n_cat = n_proto = n_noreport = 0
    n_reset = [0]
    b_seen = [0]
    rate_rows = []

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
            reader.drop_all()
            t_on = time.monotonic()
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            ts, td, banner = reader.wait_for("RBARF-P", 15.0)
            if banner is not None:
                print(f"[bench] banner {banner!r} at "
                      f"{ts - t_on:.2f} s after power-on "
                      f"(SWIM quiet window {'OK' if ts - t_on >= 4.5 else 'VIOLATED'})")
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no RBARF-P banner after 3 power "
                             "cycles -- STOP (bench rule)")

        time.sleep(0.3)
        reader.drop_all()
        with reader.cond:
            b_seen[0] = reader.banners        # boot banner is not a reset

        total = len(FRAMES) * args.reps
        done = 0
        for rep in range(args.reps):
            for name, data in FRAMES:
                fr = frame(data)
                time.sleep(0.25)          # let the firmware settle/re-arm
                reader.drop_all()
                t0 = time.monotonic()
                probe.ws2812_write(fr)    # SINGLE transmission
                t1 = time.monotonic()

                ts_d, td_d, dec = reader.wait_for("D:", 1.5)
                done += 1
                row = {"pattern": name, "rep": rep, "sent": data.hex()}

                # did the MCU reset (banner) around this frame?  counted in
                # feed(), so drop_all() can never hide one
                with reader.cond:
                    b_now = reader.banners
                reset_here = b_now > b_seen[0]
                if reset_here:
                    n_reset[0] += b_now - b_seen[0]
                    b_seen[0] = b_now

                if dec is None:
                    n_noreport += 1
                    cause = ("MCU RESET (illegal-opcode) -- 5 s SWIM window"
                             if reset_here else
                             "no report: render/blind gap, or a reset window")
                    row.update(verdict="MISSED", status="NO-REPORT",
                               reset_seen=reset_here)
                    rows.append(row)
                    print(f"[bench] {done:3d}/{total} {name:13s} r{rep}: "
                          f"MISSED       ({cause})")
                    continue

                try:
                    _, status, eps_s = dec.split(":")
                    eps = parse_eps(eps_s)
                except ValueError:
                    n_proto += 1
                    row.update(verdict="PROTOCOL-ERROR", line=dec)
                    rows.append(row)
                    print(f"[bench] {done:3d}/{total} {name:13s} r{rep}: "
                          f"BAD LINE {dec[:50]!r}")
                    continue

                got = None
                if status in ("O", "C"):
                    ts_v, td_v, ver = reader.wait_for("V:", 3.0)
                    if ver is None:
                        n_proto += 1
                        row.update(verdict="PROTOCOL-ERROR",
                                   note="no V: after verified decode")
                        rows.append(row)
                        print(f"[bench] {done:3d}/{total} {name:13s} r{rep}:"
                              f" PROTOCOL-ERROR (no V: line)")
                        continue
                    got = ver[2:]
                    if got.lower() == data.hex().lower():
                        verdict = "DELIVERED"
                        if status == "O":
                            n_ok += 1
                        else:
                            n_chase += 1
                    else:
                        verdict = "CATASTROPHIC"
                        n_cat += 1
                elif status.startswith("R") and len(status) == 2:
                    verdict = "MISSED"
                    n_refuse += 1
                else:
                    verdict = "PROTOCOL-ERROR"
                    n_proto += 1

                # timing: D line starts transmitting the instant decode ends
                transit_ms = (len(dec) + 2) * CHAR_MS
                lat_ms = (td_d - t0) * 1e3
                decode_ms = lat_ms - FRAME_TX_MS - CAPTURE_MS - transit_ms

                row.update(verdict=verdict, status=status, eps_centi=eps,
                           got=got, line=dec, latency_ms=lat_ms,
                           decode_ms=decode_ms, uplink_ms=(t1 - t0) * 1e3)
                rows.append(row)
                cz = ("R" + CAUSE.get(status[1], "?")) if verdict == "MISSED" \
                     and status.startswith("R") else status
                print(f"[bench] {done:3d}/{total} {name:13s} r{rep}: "
                      f"{verdict:12s} {cz:10s} eps {eps/100.0:+.2f}%  "
                      f"decode ~{decode_ms:.1f} ms  (latency {lat_ms:.1f} ms)")

        # ---- blind-window / applied-rate probe --------------------------
        if args.rate_probe:
            print()
            for hz in (10.0, 5.0, 4.0, 2.0):
                reader.drop_all()
                period = 1.0 / hz
                nsend = int(round(hz * 4))         # ~4 s per rate
                name, data = FRAMES[0]
                fr = frame(data)
                t_start = time.monotonic()
                for k in range(nsend):
                    probe.ws2812_write(fr)
                    nxt = t_start + (k + 1) * period
                    dt = nxt - time.monotonic()
                    if dt > 0:
                        time.sleep(dt)
                time.sleep(1.0)
                with reader.cond:
                    lines = [l for _, _, l in reader.lines]
                nd = sum(1 for l in lines if l.startswith("D:"))
                nv = sum(1 for l in lines if l.startswith("V:"))
                nr = sum(1 for l in lines
                         if l.startswith("D:R"))
                rate_rows.append({"hz": hz, "sent": nsend, "reports": nd,
                                  "delivered": nv, "refused": nr})
                print(f"[rate] {hz:4.1f} Hz x {nsend} frames -> {nd} reports,"
                      f" {nv} delivered, {nr} refused "
                      f"(applied {nv/ (nsend/hz):.1f} frames/s)")

    delivered = n_ok + n_chase
    decs = [r["decode_ms"] for r in rows if r.get("decode_ms") is not None]
    lats = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    epss = [r["eps_centi"] for r in rows if r.get("eps_centi") is not None]
    print()
    print("=" * 72)
    print(f"BENCH PROOF (production, VERBOSE): {delivered}/{total} delivered "
          f"correct ({n_ok} O + {n_chase} C), {n_refuse} refused, "
          f"{n_noreport} no-report, {n_cat} CATASTROPHIC, "
          f"{n_proto} protocol errors")
    print(f"MCU RESETS observed during the 30-frame run: {n_reset[0]} "
          f"(each costs a 5 s SWIM dead window)")
    if decs:
        print(f"decode window (latency - frame tx - capture - UART transit): "
              f"min {min(decs):.1f}  mean {sum(decs)/len(decs):.1f}  "
              f"max {max(decs):.1f} ms")
    if lats:
        print(f"host latency (frame start -> D line complete):  "
              f"min {min(lats):.1f}  mean {sum(lats)/len(lats):.1f}  "
              f"max {max(lats):.1f} ms")
    if epss:
        print(f"eps reported: first {epss[0]/100.0:+.2f}%  "
              f"last {epss[-1]/100.0:+.2f}%  "
              f"min {min(epss)/100.0:+.2f}%  max {max(epss)/100.0:+.2f}%")
    print("=" * 72)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "firmware": "rbarf_prod.c VERBOSE=1 + decode_asm.s + caploop.s + "
                        "cap_arm.s + anim.c (ND_DATA=48, CHECK_EN=1, "
                        "USE_ASM_DEC=1, CAP_BYTES=288)",
            "capture_ms": CAPTURE_MS, "frame_tx_ms": FRAME_TX_MS,
            "scoring": "single transmission; DELIVERED = O/C AND V: bytes == "
                       "ground truth; refusal or no report = MISSED; "
                       "emitted != truth = CATASTROPHIC (must be 0)",
        },
        "summary": {
            "total": total, "delivered": delivered, "ok": n_ok,
            "chased": n_chase, "refused": n_refuse,
            "no_report": n_noreport, "catastrophic": n_cat,
            "protocol_errors": n_proto,
            "mcu_resets": n_reset[0],
            "decode_ms_min": min(decs) if decs else None,
            "decode_ms_mean": sum(decs) / len(decs) if decs else None,
            "decode_ms_max": max(decs) if decs else None,
            "latency_ms_max": max(lats) if lats else None,
        },
        "rate_probe": rate_rows,
        "rows": rows,
    }, indent=1))
    print(f"[bench] wrote {out}")

    if n_cat or n_proto:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
