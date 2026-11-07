#!/usr/bin/env python3
"""Isolate the WS2812 pad-byte effect on the decoder's clock fit.

test_klipper_macro.py showed every 60-byte Klipper transmission reading
eps ~ +1.85 % against ~ +0.35 % for the same frame sent as 59 bare bytes,
and refusing (R3 infeasible / R2 marker) -- with the pad LEADING or
TRAILING alike.  That rules out "the pad disturbs the trailer scan" and
points at the clock fit: K is fitted over the whole captured burst, so
n extra bytes inflate the fitted bit period by n/59.

This probe tests that law directly.  It uses ONE payload whose delivery
is not margin limited (drive_prod's "rnd": 3/3 in the gate, 24/24 in the
240-frame soak), and sends it with 0, 1, 2 and 3 pad bytes, leading and
trailing, measuring the reported eps each time.

    predicted eps offset for n pad bytes = n / 60  (+1.67 % per byte;
    the law was measured on the 59-byte v2.1 frame at 1/59 = +1.69 %)

Usage: python3 bench/pad_law.py --bench-is-free [--reps 4]
"""

import argparse
import glob
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST

from testprobe import TestProbe                                    # noqa: E402
from drive_prod import (FRAMES, frame, LineReader, CAUSE,           # noqa: E402
                        PIN_POWER, POWER_ON_LEVEL, PIN_UART_RX,
                        PIN_UART_TX, PIN_WS2812, BAUD)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-is-free", action="store_true", required=True)
    ap.add_argument("--pattern", default="rnd")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        HERE.parents[0] / "recon" / "approaches" / "dev_prod" /
        "pad_law_results.json"))
    args = ap.parse_args()

    data = dict(FRAMES)[args.pattern]
    truth = data.hex().lower()
    fr = frame(data)

    variants = [("trail_0", fr)]
    for n in (1, 2, 3):
        variants.append(("trail_%d" % n, fr + bytes(n)))
        variants.append(("lead_%d" % n, bytes(n) + fr))

    port = probe_port(args.port)

    reader = LineReader()
    rows = []

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
            ts, td, banner = reader.wait_for("RBARF-P", 15.0)
            if banner is not None:
                print(f"[bench] banner {banner!r} at {ts - t_on:.2f} s")
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles")

        # warm up the auto-trim on a clean (60-byte, v2.2) frame first
        time.sleep(0.3)
        for _ in range(2):
            reader.drop_all()
            probe.ws2812_write(fr)
            reader.wait_for("D:", 2.0)
            time.sleep(0.4)

        for name, wire in variants:
            for rep in range(args.reps):
                time.sleep(0.4)
                reader.drop_all()
                probe.ws2812_write(wire)
                ts, td, dec = reader.wait_for("D:", 2.0)
                if dec is None:
                    rows.append({"variant": name, "rep": rep,
                                 "bytes": len(wire), "status": "NO-REPORT"})
                    print(f"[pad] {name:8s} r{rep} {len(wire)}B: NO REPORT")
                    continue
                _, st, eps_s = dec.split(":")
                eps = int(eps_s)
                got = None
                if st in ("O", "C"):
                    _, _, ver = reader.wait_for("V:", 2.0)
                    got = ver[2:].lower() if ver else None
                ok = got == truth if got is not None else None
                rows.append({"variant": name, "rep": rep, "bytes": len(wire),
                             "status": st, "eps_centi": eps,
                             "delivered": bool(ok),
                             "catastrophic": got is not None and not ok})
                cz = CAUSE.get(st[1:], st) if st.startswith("R") else st
                print(f"[pad] {name:8s} r{rep} {len(wire)}B: {cz:11s} "
                      f"eps {eps/100.0:+.2f}%  "
                      f"{'DELIVERED' if ok else ''}")

    print()
    base = [r["eps_centi"] for r in rows
            if r["variant"] == "trail_0" and "eps_centi" in r]
    base_mean = sum(base) / len(base) if base else 0.0
    print(f"{'variant':10s} {'bytes':>5s} {'eps mean':>9s} {'offset':>8s} "
          f"{'predicted':>10s}  delivered")
    summary = []
    for name, wire in variants:
        v = [r for r in rows if r["variant"] == name and "eps_centi" in r]
        if not v:
            continue
        m = sum(r["eps_centi"] for r in v) / len(v)
        npad = len(wire) - 59
        pred = 100.0 * (npad / 59.0) * 100.0 / 100.0   # in percent
        nd = sum(1 for r in v if r.get("delivered"))
        print(f"{name:10s} {len(wire):5d} {m/100.0:+8.2f}% "
              f"{(m-base_mean)/100.0:+7.2f}% {pred:+9.2f}%  {nd}/{len(v)}")
        summary.append({"variant": name, "bytes": len(wire), "n_pad": npad,
                        "eps_mean_centi": m,
                        "offset_centi": m - base_mean,
                        "predicted_offset_pct": pred,
                        "delivered": nd, "n": len(v)})
    print()
    print("law: each extra WS2812 byte inflates the fitted bit period by "
          "1/60 = +1.67 %")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {"pattern": args.pattern,
                 "firmware": "rbarf_prod_verbose.ihx",
                 "hypothesis": "K is fitted over the whole captured burst; "
                               "n extra bytes -> eps offset n/59"},
        "summary": summary, "rows": rows}, indent=1))
    print(f"[bench] wrote {out}")


if __name__ == "__main__":
    main()
