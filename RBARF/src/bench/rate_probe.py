#!/usr/bin/env python3
"""Applied-frame-rate / minimum-inter-frame-gap probe for the production build.

drive_prod.py --rate-probe drives FRAMES[0] ("colors"), which is one of the
weak-margin payloads (1/3 delivered in the 30-frame gate), so its "applied
frames/s" conflates the receiver's TIMING ceiling with that payload's decode
margin.  This probe separates the two:

  * it drives a payload whose delivery is not margin-limited (default "rnd",
    3/3 in the gate and 24/24 in the 240-frame soak), so a lost frame means
    the receiver was BLIND, not that it refused;
  * it reports three separate numbers per period:
        armed%      D: reports / frames sent   (receiver saw the frame)
        delivered   D:O|C whose V: bytes == ground truth
        refused     D:R<cause>
  * it sweeps the inter-frame PERIOD directly, which is what the Klipper
    macro docs need (minimum gap between two RBARF_SET calls).

Frames are put on the wire exactly once each (single transmission), free
running: the script does not wait for a report before sending the next
frame, so the measurement is a real applied rate, not a request/response
round trip.  Reports are parsed from the accumulated line stream afterwards.

Usage:
    python3 bench/rate_probe.py --bench-is-free [--pattern rnd]
                                [--n 12] [--periods 500,400,...] [--out F]
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

from testprobe import TestProbe                                   # noqa: E402
from drive_prod import (FRAMES, frame, LineReader, CAUSE,          # noqa: E402
                        PIN_POWER, POWER_ON_LEVEL, PIN_UART_RX,
                        PIN_UART_TX, PIN_WS2812, BAUD)

DEFAULT_PERIODS = [500, 400, 333, 300, 250, 220, 200, 180, 160, 140, 120, 100]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-is-free", action="store_true", required=True,
                    help="confirm no other workflow owns the bench")
    ap.add_argument("--pattern", default="rnd")
    ap.add_argument("--n", type=int, default=12, help="frames per period")
    ap.add_argument("--periods", default=None,
                    help="comma-separated inter-frame periods in ms")
    ap.add_argument("--terse", action="store_true",
                    help="shipping rbarf_prod.ihx: no V: line, so an "
                         "accepted decode is scored without a byte check")
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        HERE.parents[0] / "recon" / "approaches" / "dev_prod" /
        "rate_probe_results.json"))
    args = ap.parse_args()

    periods = ([float(x) for x in args.periods.split(",")]
               if args.periods else list(DEFAULT_PERIODS))

    data = dict(FRAMES)[args.pattern]
    truth = data.hex().lower()
    fr = frame(data)

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
                print(f"[bench] banner {banner!r} at {ts - t_on:.2f} s "
                      f"(SWIM window {'OK' if ts - t_on >= 4.5 else 'VIOLATED'})")
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no banner after 3 power cycles")

        # one warm-up frame so HSITRIMR auto-trim has converged before the
        # sweep (the first decode after boot is at factory trim)
        time.sleep(0.3)
        probe.ws2812_write(fr)
        reader.wait_for("D:", 2.0)
        time.sleep(0.5)

        for per_ms in periods:
            reader.drop_all()
            b0 = reader.banners
            period = per_ms / 1000.0
            t_start = time.monotonic()
            for k in range(args.n):
                probe.ws2812_write(fr)
                nxt = t_start + (k + 1) * period
                dt = nxt - time.monotonic()
                if dt > 0:
                    time.sleep(dt)
            span = time.monotonic() - t_start
            time.sleep(1.5)               # drain trailing reports / V: lines

            with reader.cond:
                lines = [l for _, _, l in reader.lines]
                resets = reader.banners - b0

            nd = ndel = nref = ncat = nprot = 0
            causes = {}
            i = 0
            while i < len(lines):
                ln = lines[i]
                if ln.startswith("D:"):
                    nd += 1
                    parts = ln.split(":")
                    st = parts[1] if len(parts) > 1 else "?"
                    if st in ("O", "C"):
                        ver = lines[i + 1] if i + 1 < len(lines) else ""
                        if ver.startswith("V:"):
                            if ver[2:].lower() == truth:
                                ndel += 1
                            else:
                                ncat += 1
                            i += 1
                        elif args.terse:
                            ndel += 1          # accepted; no V: to check
                        else:
                            nprot += 1
                    elif st.startswith("R"):
                        nref += 1
                        causes[CAUSE.get(st[1:], st)] = \
                            causes.get(CAUSE.get(st[1:], st), 0) + 1
                    else:
                        nprot += 1
                i += 1

            row = {"period_ms": per_ms, "hz": 1000.0 / per_ms,
                   "sent": args.n, "reports": nd, "delivered": ndel,
                   "refused": nref, "catastrophic": ncat,
                   "protocol_errors": nprot, "resets": resets,
                   "causes": causes, "span_s": span,
                   "armed_pct": 100.0 * nd / args.n,
                   "applied_hz": ndel / span}
            rows.append(row)
            print(f"[rate] {per_ms:5.0f} ms ({1000.0/per_ms:4.1f} Hz) x{args.n}"
                  f" -> armed {nd:2d}/{args.n} ({100.0*nd/args.n:5.1f}%)  "
                  f"delivered {ndel:2d}  refused {nref:2d}  "
                  f"CAT {ncat}  resets {resets}  "
                  f"applied {ndel/span:4.2f} frames/s  {causes}")

    print()
    ok = [r for r in rows if r["reports"] == r["sent"]]
    best = min(ok, key=lambda r: r["period_ms"]) if ok else None
    if best:
        print(f"minimum inter-frame period with 100% armed: "
              f"{best['period_ms']:.0f} ms ({best['hz']:.1f} Hz)")
    full = [r for r in rows if r["delivered"] == r["sent"]]
    if full:
        b2 = min(full, key=lambda r: r["period_ms"])
        print(f"minimum period with 100% DELIVERED ({args.pattern}): "
              f"{b2['period_ms']:.0f} ms ({b2['hz']:.1f} Hz)")
    print(f"total catastrophic across sweep: "
          f"{sum(r['catastrophic'] for r in rows)}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {"pattern": args.pattern, "n_per_period": args.n,
                 "firmware": "rbarf_prod_verbose.ihx (VERBOSE adds ~103 ms "
                             "of V: TX to the blind window vs the shipping "
                             "terse rbarf_prod.ihx)",
                 "scoring": "armed = D: report seen; delivered = O/C with "
                            "V: bytes == ground truth; free-running send, "
                            "single transmission"},
        "rows": rows}, indent=1))
    print(f"[bench] wrote {out}")


if __name__ == "__main__":
    main()
