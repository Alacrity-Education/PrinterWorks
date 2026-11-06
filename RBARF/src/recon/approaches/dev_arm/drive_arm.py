#!/usr/bin/env python3
"""Bench driver for the ARM investigation (bench-only, dev_arm scratch).

Drives the flashed arm-diagnostic image (dev_arm/rbarf_arm.c) with the 10
PRODUCTION payloads (bench/drive_prod.py FRAMES, imported from the file --
the bench sources are never modified) as v2.3 60-byte wire frames, each
put on the wire EXACTLY ONCE, and records the whole UART stream with
timestamps:

    A<28 hex>   telemetry, every captured frame
    B<576 hex>  raw capture, every refusal + every 4th capture

  --phase a   250 ms schedule + uniform 0..12 ms dither (default): makes
              the frame-arrival phase uniform w.r.t. the chip's 10 ms
              render cycle -- the attribution run
  --phase b   STRICT 250.0 ms schedule, no dither: the host-cadence /
              render-aliasing probe

Frames that arrive while the chip is unarmed (mid-render, mid-decode,
mid-UART) produce no report at all and are recorded as NO-REPORT: that is
a real production outcome and part of the measurement.
"""
import argparse
import glob
import importlib.util
import json
import random
import sys
import threading
import time
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
sys.path.insert(0, str(NEWIMPL / "bench"))
from testprobe import TestProbe                                 # noqa: E402
from crc import build_payload_v23                               # noqa: E402
from patterns import HEADER_V23, TRAILER_V23                    # noqa: E402

PIN_POWER, POWER_ON_LEVEL = 28, 1
PIN_UART_RX, PIN_UART_TX = 1, 0
PIN_WS2812 = 29
BAUD = 38400


def prod_frames():
    spec = importlib.util.spec_from_file_location(
        "drive_prod_frames", NEWIMPL / "bench" / "drive_prod.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.FRAMES


def wire(data48: bytes) -> bytes:
    p = build_payload_v23(data48)
    fr = HEADER_V23 + p + TRAILER_V23
    assert len(fr) == 60, len(fr)
    return fr


class Reader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []            # (t_done, text)
        self.banners = 0
        self.t_last = 0.0
        self.cond = threading.Condition()

    def feed(self, data):
        now = time.monotonic()
        with self.cond:
            self.t_last = now
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[:nl + 1]
                if line:
                    txt = line.decode("ascii", errors="replace")
                    if txt.startswith("RBARF-A"):
                        self.banners += 1
                    self.lines.append((now, txt))
            self.cond.notify_all()

    def wait_prefix(self, pfx, timeout):
        end = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, ln) in enumerate(self.lines):
                    if ln.startswith(pfx):
                        return t, ln
                r = end - time.monotonic()
                if r <= 0:
                    return None, None
                self.cond.wait(r)

    def wait_quiet(self, gap, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            with self.cond:
                q = time.monotonic() - self.t_last
            if q >= gap:
                return True
            time.sleep(0.01)
        return False

    def take(self):
        with self.cond:
            out = list(self.lines)
            self.lines.clear()
            return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("a", "b"), default="a")
    ap.add_argument("--reps", type=int, default=24)
    ap.add_argument("--period", type=float, default=0.250)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out or (Path(__file__).parent /
                         ("arm_run_%s.json" % a.phase)))
    port = probe_port(a.port)
    FRAMES = prod_frames()
    rnd = random.Random(0xA12 if a.phase == "a" else 0xB12)
    rd = Reader()
    events, stream = [], []

    with TestProbe(port) as probe:
        print("[probe] %s on %s" % (probe.ident(), port))
        probe.on_uart_rx = rd.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        banner = None
        for cyc in range(1, 4):
            print("[bench] power cycle %d/3 (5 s SWIM window)..." % cyc)
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            rd.take()
            t_on = time.monotonic()
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            t, banner = rd.wait_prefix("RBARF-A", 15.0)
            if banner is not None:
                dt = t - t_on
                print("[bench] banner %r at %.2f s (SWIM quiet window %s)"
                      % (banner, dt, "OK" if dt >= 4.5 else "VIOLATED"))
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles "
                             "-- STOP (bench rule)")
        time.sleep(0.3)
        rd.take()
        b0 = rd.banners

        total = len(FRAMES) * a.reps
        t_sched = time.monotonic() + 0.3
        n = 0
        t_run0 = time.monotonic()
        for rep in range(a.reps):
            for name, data in FRAMES:
                fr = wire(data)
                dt = t_sched - time.monotonic()
                if dt > 0:
                    time.sleep(dt)
                t0 = time.monotonic()
                probe.ws2812_write(fr)
                t1 = time.monotonic()
                n += 1
                events.append({"i": n, "pattern": name, "rep": rep,
                               "sent": data.hex(), "t_send": t0 - t_run0,
                               "t_send_done": t1 - t_run0})
                # wait for this frame's report, then for the stream to go
                # quiet (the 288-byte dump, when present, takes ~150 ms)
                tA, lnA = rd.wait_prefix("A", 1.2)
                if lnA is not None:
                    rd.wait_quiet(0.030, 0.6)
                for t, ln in rd.take():
                    stream.append({"t": t - t_run0, "line": ln})
                nxt = a.period + (rnd.uniform(0.0, 0.012)
                                  if a.phase == "a" else 0.0)
                t_sched = t0 + nxt
                if n % 20 == 0:
                    nA = sum(1 for s in stream if s["line"].startswith("A"))
                    nB = sum(1 for s in stream if s["line"].startswith("B"))
                    print("[bench] %3d/%d sent  %d A-lines  %d dumps  "
                          "%.0f s elapsed" % (n, total, nA, nB,
                                              time.monotonic() - t_run0))
        time.sleep(0.5)
        for t, ln in rd.take():
            stream.append({"t": t - t_run0, "line": ln})
        resets = rd.banners - b0

    nA = sum(1 for s in stream if s["line"].startswith("A"))
    nB = sum(1 for s in stream if s["line"].startswith("B"))
    print("=" * 70)
    print("phase %s: %d frames sent, %d A-lines (%.1f%% captured), "
          "%d dumps, %d MCU resets"
          % (a.phase, n, nA, 100.0 * nA / max(n, 1), nB, resets))
    out.write_text(json.dumps({
        "meta": {"phase": a.phase, "reps": a.reps, "period_s": a.period,
                 "baud": BAUD, "frames_sent": n, "resets": resets,
                 "firmware": "dev_arm/rbarf_arm.c (bench-only) + the "
                             "UNMODIFIED production rel set",
                 "dither": "uniform 0..12 ms" if a.phase == "a" else "none"},
        "events": events, "stream": stream}, indent=1))
    print("[bench] wrote %s" % out)


if __name__ == "__main__":
    main()
