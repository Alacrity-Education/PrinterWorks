#!/usr/bin/env python3
"""Step-6 miss-rate campaign: rbarf_v21_trim firmware vs ground truth.

Flashes build/rbarf_v21_trim.ihx (forced CLK_HSITRIMR cycling through
{6, 7, 0, 1, 2} -- real eps roughly +1.3 % .. -3.3 %, TRIM_SWEEP.md --
one code per decode, decode itself runs AT the forced trim), then for
each of those 5 codes sends 30 single, independent transmissions (10
patterns x 3 reps; no repetition -- every send stands alone, matching
the wire protocol) synchronized to the firmware's own TRIM:/READY
handshake, and scores every DEC line against ground truth.

Because TRIM_CYCLE in the firmware is exactly the 5 codes this campaign
needs, EVERY loop iteration is a target code: the script sends a frame
on every iteration whose code still has unmet quota, and lets iterations
for already-completed codes pass through un-signaled (still consuming
the resulting REFUSE/idle DEC+TIM lines so the handshake stays in sync).

Resumable: results are written incrementally to
bench/campaign_results.json (or --out) after every scored transmission;
re-running the script reloads prior rows and only fills the remaining
quota per trim code.

Usage: python3 bench/run_campaign.py [--out FILE] [--max-iters N]
"""

import argparse
import glob
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).parents[1]
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port, stm8flash        # noqa: E402
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

IHX = str(REPO / "build" / "rbarf_v21_trim.ihx")
BANNER = "RBARF-V21TRIM"

# The 5 forced trim codes the firmware cycles through, in its own
# round-robin order (must match TRIM_CYCLE in rbarf_v21_trim.c).
TRIM_ORDER = [6, 7, 0, 1, 2]
TRIM_EPS_PCT = {6: 1.274, 7: 0.022, 0: -1.072, 1: -2.248, 2: -3.281}  # TRIM_SWEEP.md

# Same 10-pattern bench sample as bench/drive_v21.py (task 5), so this
# campaign's ground truth is directly comparable to that proof run.
BENCH_PATTERNS = ["zeros", "ones", "aa", "count", "blocks",
                  "nibbles", "dense", "runs", "rnd1", "rnd3"]
REPS_PER_CODE = 3
QUOTA_PER_CODE = len(BENCH_PATTERNS) * REPS_PER_CODE   # 30


class LineReader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []
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
                    self.lines.append((now, line.decode("ascii", errors="replace")))
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


def power_cycle(probe: TestProbe) -> None:
    probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
    time.sleep(2.0)
    probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)


def flash_firmware(probe: TestProbe, ihx: str) -> None:
    """Flash via the same stm8flash invocation flash.py uses (bench rule:
    exclusive access, 3-attempt SWIM window, no series resistor, TVCC
    fed)."""
    for attempt in range(1, 4):
        print(f"[campaign] flash attempt {attempt}/3: power-cycling + stm8flash")
        power_cycle(probe)
        time.sleep(0.3)
        cmd = [stm8flash(), "-c", "stlinkv2", "-p", "stm8s001j3", "-w", ihx]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = (res.stdout + res.stderr).strip()
        if out:
            print("\n".join(f"[stm8flash] {l}" for l in out.splitlines()))
        if res.returncode == 0:
            print("[campaign] flash OK")
            return
        print(f"[campaign] flash failed (rc={res.returncode})")
    raise SystemExit("[campaign] FAIL: stm8flash failed on every attempt")


def load_state(out_path: Path):
    if out_path.exists():
        try:
            doc = json.loads(out_path.read_text())
            return doc.get("rows", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


def remaining_tasks(done_by_code):
    """Per code, the (pattern, rep) combos not yet recorded with a scored
    verdict (DELIVERED/MISSED/CATASTROPHIC -- PROTOCOL-ERROR rows are
    retried, they don't consume quota)."""
    tasks = {}
    for code in TRIM_ORDER:
        done = done_by_code.get(code, set())
        q = [(p, r) for p in BENCH_PATTERNS for r in range(REPS_PER_CODE)
             if (p, r) not in done]
        tasks[code] = q
    return tasks


def write_out(out_path: Path, rows, meta):
    by_code = {}
    for r in rows:
        by_code.setdefault(r["trim_code"], []).append(r)
    summary_by_code = {}
    n_ok = n_chase = n_refuse = n_cat = n_proto = 0
    for code, rs in by_code.items():
        ok = sum(1 for r in rs if r["verdict"] == "DELIVERED" and r["status"] == "OK")
        chase = sum(1 for r in rs if r["verdict"] == "DELIVERED" and r["status"] == "CHASED")
        refuse = sum(1 for r in rs if r["verdict"] == "MISSED")
        cat = sum(1 for r in rs if r["verdict"] == "CATASTROPHIC")
        proto = sum(1 for r in rs if r["verdict"] == "PROTOCOL-ERROR")
        n_ok += ok; n_chase += chase; n_refuse += refuse
        n_cat += cat; n_proto += proto
        summary_by_code[str(code)] = {
            "eps_pct_table": TRIM_EPS_PCT[code], "n": len(rs),
            "ok": ok, "chased": chase, "refused": refuse,
            "catastrophic": cat, "protocol_errors": proto,
            "delivered_rate": (ok + chase) / len(rs) if rs else None,
        }
    total = n_ok + n_chase + n_refuse + n_cat
    delivered = n_ok + n_chase
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "meta": meta,
        "summary": {
            "total_scored": total, "delivered": delivered, "ok": n_ok,
            "chased": n_chase, "refused": n_refuse,
            "catastrophic": n_cat, "protocol_errors": n_proto,
            "single_shot_success_rate": delivered / total if total else None,
            "by_trim_code": summary_by_code,
        },
        "rows": rows,
    }, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(REPO / "bench" / "campaign_results.json"))
    ap.add_argument("--max-iters", type=int, default=400,
                     help="safety cap on firmware loop iterations consumed")
    args = ap.parse_args()

    port = probe_port(args.port)

    out_path = Path(args.out)
    rows = load_state(out_path)
    done_by_code = {}
    for r in rows:
        if r["verdict"] in ("DELIVERED", "MISSED", "CATASTROPHIC"):
            done_by_code.setdefault(r["trim_code"], set()).add(
                (r["pattern"], r["rep"]))
    tasks = remaining_tasks(done_by_code)
    already = sum(len(v) for v in done_by_code.values())
    print(f"[campaign] resuming: {already} transmissions already scored, "
          f"{sum(len(v) for v in tasks.values())} remaining")

    meta = {
        "firmware": "rbarf_v21_trim.c + decode.c + scan.s (ND_DATA=16, "
                    "CHECK_EN=1, USE_ASM_SCAN=1, CAP_BYTES=256), forced "
                    "CLK_HSITRIMR cycling {6,7,0,1,2} per decode, decode "
                    "runs at forced trim, UART TX at factory trim",
        "trim_order": TRIM_ORDER, "trim_eps_pct_table": TRIM_EPS_PCT,
        "quota_per_code": QUOTA_PER_CODE, "patterns": BENCH_PATTERNS,
        "scoring": "single transmission: DELIVERED = emitted AND equal to "
                   "ground truth; REFUSE = missed frame; emitted != truth "
                   "= CATASTROPHIC (must be 0)",
    }
    if not any(tasks.values()):
        print("[campaign] all quotas already met -- nothing to do")
        write_out(out_path, rows, meta)
        return

    reader = LineReader()
    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        flash_firmware(probe, IHX)

        banner = None
        for cycle in range(1, 4):        # bench rule: stop after 3 cycles
            print(f"[campaign] power cycle {cycle}/3 (5 s SWIM window)...")
            power_cycle(probe)
            _, banner = reader.wait_for(BANNER, 15.0)
            if banner is not None:
                break
        if banner is None:
            raise SystemExit(f"[campaign] FAIL: no {BANNER} banner after 3 "
                              "power cycles -- STOP (bench rule)")
        print(f"[campaign] firmware banner: {banner!r}")

        iters = 0
        total_remaining = sum(len(v) for v in tasks.values())
        done_count = 0
        while any(tasks.values()) and iters < args.max_iters:
            iters += 1
            t_trim, trim_line = reader.wait_for("TRIM:", 10.0)
            if trim_line is None:
                raise SystemExit("[campaign] FAIL: no TRIM: line (firmware "
                                  "stopped responding)")
            try:
                code = int(trim_line.split(":")[1])
            except (IndexError, ValueError):
                raise SystemExit(f"[campaign] FAIL: bad TRIM line {trim_line!r}")

            t_rdy, rdy = reader.wait_for("READY", 5.0)
            if rdy is None:
                raise SystemExit("[campaign] FAIL: no READY after TRIM line")

            queue = tasks.get(code, [])
            if not queue:
                # quota already met for this code -- let the loop pass,
                # just drain its DEC/TIM lines to stay in sync.
                reader.wait_for("DEC:", 5.0)
                reader.wait_for("TIM:", 3.0)
                continue

            pattern, rep = queue.pop(0)
            data = PATTERNS[pattern]
            payload = PATTERNS_V21[pattern]
            fr = frame(payload)

            time.sleep(0.05)             # firmware arms shortly after READY
            t0 = time.monotonic()
            probe.ws2812_write(fr)
            t_dec, dec = reader.wait_for("DEC:", 15.0)
            if dec is None:
                raise SystemExit(f"[campaign] FAIL: no DEC line for "
                                  f"code={code} {pattern} rep={rep}")
            t_tim, tim = reader.wait_for("TIM:", 5.0)

            row = {"trim_code": code, "pattern": pattern, "rep": rep,
                   "line": dec}
            try:
                _, hexdata, eps_s, status = dec.split(":")
                ticks = int(tim.split(":")[1]) if tim else None
                eps_centi = int(eps_s)
            except (ValueError, AttributeError, IndexError):
                verdict = "PROTOCOL-ERROR"
                row["verdict"] = verdict
                queue.insert(0, (pattern, rep))   # retry this combo
                rows.append(row)
                write_out(out_path, rows, meta)
                print(f"[campaign] code={code} {pattern} r{rep}: BAD LINE "
                      f"{dec[:60]!r} (queued for retry)")
                continue

            if status in ("OK", "CHASED"):
                if hexdata.lower() == data.hex().lower():
                    verdict = "DELIVERED"
                else:
                    verdict = "CATASTROPHIC"
            elif status == "REFUSE":
                verdict = "MISSED" if hexdata == "00" * 16 else "PROTOCOL-ERROR"
            else:
                verdict = "PROTOCOL-ERROR"

            if verdict == "PROTOCOL-ERROR":
                queue.insert(0, (pattern, rep))   # retry this combo

            row.update(verdict=verdict, status=status, eps_centi=eps_centi,
                        eps_pct_table=TRIM_EPS_PCT[code], tim_ticks=ticks,
                        t_send=t0)
            rows.append(row)
            done_count += 1
            write_out(out_path, rows, meta)

            print(f"[campaign] {done_count:3d}/{total_remaining} "
                  f"code={code} ({TRIM_EPS_PCT[code]:+.2f}%) "
                  f"{pattern:8s} r{rep}: {verdict:12s} {status:6s}")

        if iters >= args.max_iters and any(tasks.values()):
            print(f"[campaign] WARNING: hit --max-iters={args.max_iters} "
                  "with quota unmet -- re-run to resume")

    write_out(out_path, rows, meta)
    print(f"[campaign] wrote {out_path}")


if __name__ == "__main__":
    main()
