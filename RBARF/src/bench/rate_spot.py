#!/usr/bin/env python3
"""Rate spot-check: N frames at a fixed spacing, count how many ARM.

Step 4 of the v2.2 bench re-gate.  The production firmware re-arms its
~1.2 ms capture window back to back between 100 Hz render ticks, so a
frame that lands during a render tick or during the decode blind window
is never seen at all (no report).  This probe asks one narrow question:

    at SPACING ms between frames, does the device see EVERY frame?

"ARMED" = the device emitted a D: report for that frame (it was armed,
captured and adjudicated it).  Whether the adjudication delivered or
refused is the margin question, reported separately and NOT the pass
criterion here.

Usage:
    python3 bench/rate_spot.py --bench-is-free [--spacing-ms 250]
                               [--frames 12] [--pattern rnd]
"""

import argparse
import glob
import json
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST

from crc import build_payload_v23                                   # noqa: E402
from epsfmt import parse_eps                                        # noqa: E402

HEADER = bytes.fromhex("FFAA65")    # v2.3: sync / ruler / byte align
TRAILER = bytes.fromhex("9A00FF")   # v2.3: end marker, ZEROS probe, FF

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600

CAUSE = {"1": "lock", "2": "marker", "3": "infeasible", "4": "labelerr",
         "5": "emitgate", "6": "nocand", "7": "admit", "8": "chase"}


def frame(data48: bytes) -> bytes:
    payload = build_payload_v23(data48)
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


class LineReader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []
        self.cond = threading.Condition()

    def feed(self, data):
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

    def wait_any(self, prefixes, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, line) in enumerate(self.lines):
                    if any(line.startswith(p) for p in prefixes):
                        del self.lines[: i + 1]
                        return t, line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, None
                self.cond.wait(remaining)

    def drain_v(self, timeout=1.0):
        t, line = self.wait_any(("V:",), timeout)
        return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-is-free", action="store_true", required=True)
    ap.add_argument("--spacing-ms", type=float, default=250.0)
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--pattern", default="rnd")
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data = _lcg(0xC0FFEE, 48)          # the drive_prod "rnd" payload
    wire = frame(data)
    truth = data.hex()

    port = probe_port(args.port)

    from testprobe import TestProbe                                 # noqa: E402

    reader = LineReader()
    rows = []
    armed = delivered = refused = silent = cat = 0

    with TestProbe(port) as probe:
        print("[probe] %s on %s" % (probe.ident(), port))
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        banner = None
        for cycle in range(1, 4):
            print("[bench] power cycle %d/3 (5 s SWIM window)..." % cycle)
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            _, banner = reader.wait_any(("RBARF-P",), 15.0)
            if banner is not None:
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles")
        print("[bench] banner: %r" % banner)
        print("[bench] %d frames of pattern %r at %.0f ms spacing"
              % (args.frames, args.pattern, args.spacing_ms))

        period = args.spacing_ms / 1000.0
        t_start = time.monotonic()
        for k in range(args.frames):
            probe.ws2812_write(wire)
            t_rep, line = reader.wait_any(("D:",), max(period, 0.5) + 0.6)
            row = {"n": k, "line": line}
            if line is None:
                silent += 1
                row["verdict"] = "NOT-ARMED"
                print("[rate] %2d/%d: NOT ARMED (no report)"
                      % (k + 1, args.frames))
            else:
                armed += 1
                _, st, eps_s = line.split(":")
                eps = parse_eps(eps_s)
                row["status"], row["eps_centi"] = st, eps
                if st in ("O", "C"):
                    v = reader.drain_v(1.0)
                    got = v.split(":", 1)[1].strip().lower() if v else None
                    if got == truth:
                        delivered += 1
                        row["verdict"] = "DELIVERED"
                    elif got is None:
                        row["verdict"] = "ACCEPTED-UNCHECKED"
                    else:
                        cat += 1
                        row["verdict"] = "CATASTROPHIC"
                        row["decoded"] = got
                else:
                    refused += 1
                    row["verdict"] = "REFUSED"
                    row["cause"] = CAUSE.get(st[1:], st)
                print("[rate] %2d/%d: ARMED  %-12s %-10s eps %+.2f%%"
                      % (k + 1, args.frames, row["verdict"],
                         row.get("cause", st), eps / 100.0))
            rows.append(row)
            nxt = t_start + (k + 1) * period
            dt = nxt - time.monotonic()
            if dt > 0:
                time.sleep(dt)

    print()
    print("=" * 68)
    print("RATE SPOT-CHECK  %.0f ms spacing, %d frames"
          % (args.spacing_ms, args.frames))
    print("  ARMED (saw the frame): %d/%d   [pass criterion]"
          % (armed, args.frames))
    print("  of those: %d delivered, %d refused, %d CATASTROPHIC"
          % (delivered, refused, cat))
    epss = [r["eps_centi"] for r in rows if r.get("eps_centi") is not None]
    if epss:
        print("  eps: first %+.2f%%  last %+.2f%%  min %+.2f%%  max %+.2f%%"
              % (epss[0] / 100.0, epss[-1] / 100.0,
                 min(epss) / 100.0, max(epss) / 100.0))
    print("=" * 68)

    if args.out:
        Path(args.out).write_text(json.dumps({
            "spacing_ms": args.spacing_ms, "frames": args.frames,
            "pattern": args.pattern, "truth": truth,
            "summary": {"armed": armed, "delivered": delivered,
                        "refused": refused, "catastrophic": cat,
                        "not_armed": silent},
            "rows": rows}, indent=1))
        print("[bench] wrote %s" % args.out)

    return 0 if (armed == args.frames and cat == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
