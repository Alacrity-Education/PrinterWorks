#!/usr/bin/env python3
"""Crash-input capture driver for the rbarf_dbg firmware.

Drives the flashed RBARF-D image with the 10 production frames and logs
every line.  The firmware dumps each raw 288-byte capture as
"B:<576 hex>" BEFORE decoding it, and reports "R:<RST_SR hex>" after
every boot banner, so:

    B: line followed by a banner with NO intervening D: line
        -> that capture crashed the decoder; RST_SR on the next boot
           says why (04 = ILLOPF).

Crashing captures are written to recon/approaches/dev_prod/crashcaps/
as <n>_<pattern>.cap (hex, one line) for ucsim replay.

Stops after --crashes crashing inputs or --max-frames frames.  Bench
rules honoured: power gate GPIO28 ON=1, 5 s SWIM quiet window respected,
abort after 3 failed power cycles.

Usage: python3 bench/crashcap.py [--crashes 5] [--max-frames 400]
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
    payload = build_payload(data48)
    assert len(payload) == 52   # v2.2: DATA + CRC8 x4
    fr = HEADER + payload + TRAILER
    assert len(fr) == 60         # v2.2: exactly 20 LEDs
    return fr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crashes", type=int, default=5)
    ap.add_argument("--max-frames", type=int, default=400)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out-dir", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_prod" /
        "crashcaps"))
    args = ap.parse_args()
    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    port = probe_port(args.port)

    reader = LineReader()
    crashes = []          # (idx, pattern, hex)
    log = []              # every event for the record

    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        banner = None
        for cycle in range(1, 4):
            print(f"[bench] power cycle {cycle}/3 (5 s SWIM window)...")
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            reader.drop_all()
            t_on = time.monotonic()
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            ts, td, banner = reader.wait_for("RBARF-D", 15.0)
            if banner is not None:
                print(f"[bench] banner {banner!r} at {ts - t_on:.2f} s "
                      f"(SWIM window {'OK' if ts - t_on >= 4.5 else 'VIOLATED'})")
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no RBARF-D banner after 3 power "
                             "cycles -- STOP (bench rule)")
        _, _, rline = reader.wait_for("R:", 3.0)
        print(f"[bench] boot reset cause {rline!r} (00 = power-on)")

        pending_b = None      # (pattern, hexdump) of the last un-decoded B:
        sent = 0
        fi = 0
        t_deadline = time.time() + 3600
        while (len(crashes) < args.crashes and sent < args.max_frames
               and time.time() < t_deadline):
            name, data = FRAMES[fi % len(FRAMES)]
            fi += 1
            fr = frame(data)
            time.sleep(0.30)              # settle / re-arm
            probe.ws2812_write(fr)        # single transmission
            sent += 1

            # wait for the B: dump (uart ~640 ms for 578 chars)
            ts_b, td_b, bline = reader.wait_for("B:", 2.5)
            if bline is None:
                # frame lost to render/blind window -- check for a banner
                ts_x, _, bn = reader.wait_for("RBARF-D", 0.1)
                if bn is not None:
                    # reset with no dump?! decode of a *previous* capture
                    # crashed after its B: was consumed -- shouldn't happen
                    # with our accounting, log it
                    log.append({"ev": "reset_no_dump", "sent": sent})
                    print(f"[bench] {sent:3d} {name:13s}: RESET (no dump "
                          f"attributable)")
                    reader.wait_for("R:", 8.0)
                continue
            caphex = bline[2:]
            if len(caphex) != 576:
                log.append({"ev": "short_dump", "len": len(caphex)})
                print(f"[bench] {sent:3d} {name:13s}: short/mangled dump "
                      f"({len(caphex)} chars) -- ignored")
                continue

            # now: either a D: report (survived) or a banner (crashed)
            ts_d, td_d, dline = reader.wait_for("D:", 2.0)
            if dline is not None:
                log.append({"ev": "decode", "pattern": name, "line": dline})
                print(f"[bench] {sent:3d} {name:13s}: {dline}")
                continue
            # no D: -- crash? wait for the reboot banner (5 s window + slack)
            ts_x, _, bn = reader.wait_for("RBARF-D", 9.0)
            if bn is None:
                log.append({"ev": "no_report_no_reset", "pattern": name})
                print(f"[bench] {sent:3d} {name:13s}: dump but no D: and no "
                      f"reset (?)")
                continue
            _, _, rline = reader.wait_for("R:", 3.0)
            rst = (rline or "R:??")[2:]
            idx = len(crashes)
            (outdir / f"{idx:02d}_{name}.cap").write_text(caphex)
            crashes.append({"idx": idx, "pattern": name, "rst_sr": rst,
                            "hex": caphex})
            log.append({"ev": "CRASH", "pattern": name, "rst_sr": rst})
            print(f"[bench] {sent:3d} {name:13s}: *** CRASH (RST_SR={rst}) "
                  f"-- capture {idx:02d} saved ***")

        print()
        print(f"[bench] done: {sent} frames sent, {len(crashes)} crashing "
              f"captures collected")
        (outdir / "crashlog.json").write_text(json.dumps(
            {"sent": sent, "crashes": crashes, "log": log}, indent=1))
        for c in crashes:
            print(f"   {c['idx']:02d} {c['pattern']:13s} RST_SR={c['rst_sr']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
