#!/usr/bin/env python3
"""Acquire the CLK_HSITRIMR trim-sweep dataset from the STM8 bench.

The capture_trim firmware rotates the HSI trim code 0,1,...,7,0,...
on its own schedule, one capture per code.  Per cycle it announces
(at factory trim, so the UART is always clean):

    TRIM:<code>\r\n
    READY\r\n
    ... capture at CLK_HSITRIMR=<code> ...
    CAP:<1280 hex>:<2 hex sum>\r\n

The host cannot choose the trim — it just keeps sending frames and
records whatever trim the firmware announces, sending the pattern that
the announced trim still needs, until every (trim 0..7 x pattern) cell
holds --reps captures.  6-pattern subset {aa, zeros, ones, rnd1, rnd2,
edges}, 2 reps -> 96 captures total.

IMPORTANT: cap_code blocks until a frame arrives, so the host must send
a frame on EVERY cycle — if the announced trim has no remaining need,
a dummy frame is sent and its capture discarded.

Usage: python3 bench/acquire_trim.py [--reps 2] [--port PORT] [--out FILE]
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
from patterns import PATTERNS, frame  # noqa: E402
from acquire import META as BASE_META  # noqa: E402  (import only, not run)

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600
CAP_BYTES = 640

TRIM_CODES = list(range(8))
SWEEP_PATTERNS = ["aa", "zeros", "ones", "rnd1", "rnd2", "edges"]

MAX_BAD_DUMPS = 12          # persistent-garble bail-out threshold

META = dict(BASE_META)
META.update({
    "firmware": "capture_trim.c + cap_code.s",
    "trim_sweep": "CLK_HSITRIMR (0x50CC) swept over codes 0..7 (3-bit "
                  "trimming, default option bytes; reset value 0x00 = "
                  "factory calibration). The firmware rotates the code "
                  "0,1,...,7,0,... one capture per code; the trim is "
                  "applied only around cap_code (sampling runs at the "
                  "trimmed clock) and restored to 0x00 before any UART "
                  "output, so all UART traffic is at factory trim. The "
                  "code->frequency mapping was deliberately NOT assumed; "
                  "measure it from the captures.",
    "temperature": "no on-chip temperature sensor (DS12129 §4.12); "
                   "ambient room temperature, not instrumented",
    "sweep_patterns": SWEEP_PATTERNS,
})


class LineReader:
    """Assemble UART RX bytes into lines."""

    def __init__(self):
        self.buf = bytearray()
        self.lines = []
        self.cond = threading.Condition()

    def feed(self, data: bytes) -> None:
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[: nl + 1]
                if line:
                    self.lines.append(line.decode("ascii", errors="replace"))
            self.cond.notify_all()

    def wait_for(self, prefix: str, timeout: float):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, line in enumerate(self.lines):
                    if line.startswith(prefix):
                        del self.lines[: i + 1]
                        return line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.cond.wait(remaining)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.out is None:
        args.out = str(Path(__file__).parent / "data"
                       / "captures_trim.json")

    port = probe_port(args.port)

    # need[trim] = ordered [(pattern, rep), ...] still to collect
    need = {t: [(p, r) for r in range(args.reps) for p in SWEEP_PATTERNS]
            for t in TRIM_CODES}
    total = sum(len(v) for v in need.values())

    reader = LineReader()
    captures = []
    bad_dumps = 0
    t_start = time.time()

    reader_meta = dict(META)
    reader_meta["acquired_iso"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S%z", time.localtime(t_start))

    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        print("[bench] power-cycling target (5s boot window)...")
        probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
        time.sleep(2.0)
        probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)

        if reader.wait_for("RBARF-CAPTRIM", 15.0) is None:
            raise SystemExit("[bench] FAIL: no banner from capture_trim "
                             "firmware")
        print("[bench] capture_trim firmware is up")

        done = 0
        cycles = 0
        max_cycles = total + 8 * (args.reps + 4)   # slack for retries/dummies
        while any(need.values()):
            cycles += 1
            if cycles > max_cycles:
                raise SystemExit(f"[bench] FAIL: cell needs not met after "
                                 f"{cycles - 1} cycles; remaining: "
                                 f"{ {t: len(v) for t, v in need.items()} }")

            tline = reader.wait_for("TRIM:", 12.0)
            if tline is None:
                raise SystemExit("[bench] FAIL: no TRIM announcement")
            try:
                trim = int(tline.split(":", 1)[1])
            except ValueError:
                raise SystemExit(f"[bench] FAIL: bad TRIM line: {tline!r}")
            if trim not in need:
                raise SystemExit(f"[bench] FAIL: unexpected trim code {trim}")

            if reader.wait_for("READY", 10.0) is None:
                raise SystemExit(f"[bench] FAIL: no READY after {tline}")

            if need[trim]:
                pat, rep = need[trim][0]
                dummy = False
            else:
                pat, rep = SWEEP_PATTERNS[0], -1    # keep firmware moving
                dummy = True
            payload = PATTERNS[pat]
            fr = frame(payload)

            time.sleep(0.05)
            probe.ws2812_write(fr)

            line = reader.wait_for("CAP:", 15.0)
            if line is None:
                raise SystemExit(f"[bench] FAIL: no dump for trim {trim} "
                                 f"{pat} rep {rep}")
            try:
                _, hexdata, cksum = line.split(":")
                raw = bytes.fromhex(hexdata)
                ok = (len(raw) == CAP_BYTES
                      and (sum(raw) & 0xFF) == int(cksum, 16))
            except ValueError:
                raw, ok = b"", False

            if dummy:
                print(f"[bench] trim {trim}: cell full, dummy frame "
                      f"({'ok' if ok else 'bad'} dump discarded)")
                continue

            if not ok:
                bad_dumps += 1
                print(f"[bench] WARN: bad dump for trim {trim} {pat} rep "
                      f"{rep} ({len(raw)} bytes) — will retry "
                      f"[{bad_dumps}/{MAX_BAD_DUMPS}]")
                if bad_dumps >= MAX_BAD_DUMPS:
                    raise SystemExit("[bench] FAIL: persistent bad dumps — "
                                     "diagnose before proceeding")
                continue

            need[trim].pop(0)
            captures.append({
                "pattern": pat,
                "rep": rep,
                "trim": trim,
                "payload": payload.hex().upper(),
                "frame": fr.hex().upper(),
                "capture": hexdata,
            })
            done += 1
            print(f"[bench] {done:3d}/{total}  trim {trim}  {pat} rep {rep}: "
                  f"OK ({sum(bin(b).count('1') for b in raw)} high samples)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"meta": reader_meta, "acquired_unix": t_start, "captures": captures},
        indent=1))
    print(f"[bench] wrote {len(captures)} captures to {out} "
          f"({bad_dumps} bad dumps retried)")


if __name__ == "__main__":
    main()
