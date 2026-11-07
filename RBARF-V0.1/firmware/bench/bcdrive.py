#!/usr/bin/env python3
"""Breadcrumb driver: drive rbarf_bc and collect the boot reports.

The firmware reports, after every boot banner:
    R:<RST_SR> C:<crumb> S:<sub> M:<magic-valid>
crumb pins the stage that was executing at the fault (see rbarf_bc.c).
Drives the 10 production frames continuously; each reset's next-boot line
attributes the crash to a stage.  Bench rules: GPIO28 ON=1, 5 s SWIM
window, abort after 3 failed power cycles.

Usage: python3 bench/bcdrive.py [--resets 8] [--max-frames 400]
"""
import argparse
import glob
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
from testprobe import TestProbe  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from crc import build_payload  # noqa: E402
from drive_prod import FRAMES, LineReader, HEADER, TRAILER  # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600


def frame(data48: bytes) -> bytes:
    return HEADER + build_payload(data48) + TRAILER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resets", type=int, default=8)
    ap.add_argument("--max-frames", type=int, default=500)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_prod" /
        "bc_reports.json"))
    args = ap.parse_args()

    port = probe_port(args.port)

    reader = LineReader()
    reports = []            # every R:/boot line
    decodes = 0

    def wait_boot(timeout):
        ts, td, bn = reader.wait_for("RBARF-", timeout)
        if bn is None:
            return None
        _, _, rl = reader.wait_for("R:", 3.0)
        return rl

    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        rl = None
        for cycle in range(1, 4):
            print(f"[bench] power cycle {cycle}/3 (5 s SWIM window)...")
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            reader.drop_all()
            t_on = time.monotonic()
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            rl = wait_boot(15.0)
            if rl is not None:
                print(f"[bench] boot report {rl!r}")
                reports.append({"boot": "cold", "line": rl})
                break
        if rl is None:
            raise SystemExit("[bench] FAIL: no RBARF- banner after 3 cycles")

        n_reset = 0
        sent = 0
        fi = 0
        while n_reset < args.resets and sent < args.max_frames:
            name, data = FRAMES[fi % len(FRAMES)]
            fi += 1
            fr = frame(data)
            time.sleep(0.25)
            reader.drop_all()
            probe.ws2812_write(fr)
            sent += 1
            # a decode report OR a reboot (crash) will follow
            ts, td, line = reader.wait_for("D:", 1.2)
            if line is not None:
                decodes += 1
                continue
            # no D: -- a crash? look for the reboot + its R: report
            rl = wait_boot(9.0)
            if rl is not None:
                n_reset += 1
                reports.append({"boot": "reset", "after_frame": name,
                                "sent": sent, "decodes_since": decodes,
                                "line": rl})
                print(f"[bench] sent {sent:3d} decodes {decodes:3d}: RESET -> "
                      f"{rl!r}")
    # tally crumb values
    from collections import Counter
    crumbs = Counter()
    rsts = Counter()
    for r in reports:
        if r.get("boot") != "reset":
            continue
        parts = dict(p.split(":") for p in r["line"].split()
                     if ":" in p)
        crumbs[parts.get("C")] += 1
        rsts[parts.get("R")] += 1
    print()
    print(f"[bench] {sent} frames, {decodes} decodes, {n_reset} resets")
    print(f"[bench] RST_SR at reboot: {dict(rsts)}")
    print(f"[bench] crumb (faulting stage) histogram: {dict(crumbs)}")
    Path(args.out).write_text(json.dumps(
        {"sent": sent, "decodes": decodes, "resets": n_reset,
         "rst_hist": dict(rsts), "crumb_hist": dict(crumbs),
         "reports": reports}, indent=1))
    print(f"[bench] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
