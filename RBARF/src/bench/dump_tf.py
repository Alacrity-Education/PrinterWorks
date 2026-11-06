#!/usr/bin/env python3
"""Instrumented-capture collector for the margin investigation
(rbarf_dbg_tfc.ihx: rbarf_dbg_tf.c -- dump-before-decode + trim cycle
{7, 0, 6, 1}).

Per frame the firmware emits
    B:<576 hex>                    raw 288-byte capture, BEFORE decode
    D:<status>:<eps>:<code>        the on-chip decode verdict at <code>
so every row pairs a real silicon capture with the operating point it was
taken at and the device's own verdict. The host analysis re-decodes each
dump with the bit-exact host decoder and fits (t0, eps) against the
calibrated sampler model.

Usage: python3 bench/dump_tf.py [--passes 2] [--out FILE]
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
from drive_prod import FRAMES, LineReader, frame  # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_prod" /
        "margin_dumps.json"))
    args = ap.parse_args()

    port = probe_port(args.port)

    reader = LineReader()
    rows = []
    n_sent = 0

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
                      f"(SWIM {'OK' if ts - t_on >= 4.5 else 'VIOLATED'})")
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles "
                             "-- STOP (bench rule)")
        time.sleep(0.3)
        reader.drop_all()
        t_session = time.monotonic()

        for pss in range(args.passes):
            for name, data in FRAMES:
                fr = frame(data)
                seen_codes = set()
                tries = 0
                while len(seen_codes) < 4 and tries < 7:
                    tries += 1
                    time.sleep(0.25)
                    reader.drop_all()
                    probe.ws2812_write(fr)          # single transmission
                    n_sent += 1
                    ts_b, td_b, bline = reader.wait_for("B:", 2.5)
                    if bline is None:
                        print(f"[dump] {n_sent:3d} {name:13s}: no dump "
                              f"(render/blind window)")
                        continue
                    caphex = bline[2:]
                    if len(caphex) != 576:
                        print(f"[dump] {n_sent:3d} {name:13s}: short dump "
                              f"({len(caphex)}) -- ignored")
                        continue
                    ts_d, td_d, dline = reader.wait_for("D:", 2.0)
                    if dline is None:
                        print(f"[dump] {n_sent:3d} {name:13s}: dump but no "
                              f"D: line")
                        continue
                    try:
                        _, status, eps_s, code_s = dline.split(":")
                        eps = int(eps_s)
                        code = int(code_s)
                    except ValueError:
                        print(f"[dump] {n_sent:3d} {name:13s}: bad D line "
                              f"{dline[:40]!r}")
                        continue
                    seen_codes.add(code)
                    rows.append({"pattern": name, "pass": pss,
                                 "sent": data.hex(), "cap": caphex,
                                 "status": status, "eps_centi": eps,
                                 "code": code,
                                 "t_s": round(time.monotonic() - t_session,
                                              1)})
                    print(f"[dump] {n_sent:3d} {name:13s} p{pss} "
                          f"code{code}: {status} eps {eps/100.0:+.2f}%")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "firmware": "rbarf_dbg_tf.c (dump-before-decode, trim cycle "
                        "{7,0,6,1}) + PROD_RELS",
            "note": "cap = raw 288-byte capture (hex) BEFORE decode; "
                    "status/eps/code = on-chip verdict at that trim code",
        },
        "rows": rows, "sent": n_sent,
    }, indent=1))
    print(f"[dump] wrote {out}  ({len(rows)} captures)")


if __name__ == "__main__":
    main()
