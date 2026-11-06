#!/usr/bin/env python3
"""Margin-investigation driver for the trim-cycling bench image
(rbarf_prod_tfc.ihx: rbarf_prod_tf.c default build, VERBOSE).

The firmware round-robins CLK_HSITRIMR through codes {7, 0, 6, 1}
(eps {+0.02, -1.07, +1.27, -2.25} %), advancing after every report, and
reports  D:<status>:<eps-centi%>:<code-digit>  (+ V:<96 hex> on emit).

This driver sends each of the 10 gate payloads until every one of the 4
codes has been observed for it (the cycle advances only on reports, so
no-report frames do not desynchronize anything), for --passes rounds.
Every (payload, code) cell therefore gets ~--passes single-transmission
frames, and the four operating points interleave within one session --
same thermal trajectory for all four (the CAMPAIGN.md design).

Scoring per frame (single transmission, like drive_prod.py):
  DELIVERED (O/C + V: == ground truth) | CATASTROPHIC (V: mismatch)
  MISSED (refusal or no report) -- refusal cause kept.

Usage: python3 bench/drive_tf.py [--passes 3] [--out FILE]
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
from drive_prod import FRAMES, LineReader, frame, CAUSE  # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600

CODES = (7, 0, 6, 1)
CODE_EPS = {7: "+0.02", 0: "-1.07", 6: "+1.27", 1: "-2.25"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--port", default=None)
    ap.add_argument("--out", default=str(
        Path(__file__).parents[1] / "recon" / "approaches" / "dev_prod" /
        "bench_tf_cycle.json"))
    args = ap.parse_args()

    port = probe_port(args.port)

    reader = LineReader()
    rows = []
    n_sent = n_noreport = n_cat = n_proto = 0

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
                    t0 = time.monotonic()
                    probe.ws2812_write(fr)          # single transmission
                    ts_d, td_d, dec = reader.wait_for("D:", 1.5)
                    n_sent += 1
                    row = {"pattern": name, "pass": pss, "try": tries,
                           "t_s": round(time.monotonic() - t_session, 1)}
                    if dec is None:
                        n_noreport += 1
                        row.update(verdict="MISSED", status="NO-REPORT",
                                   code=None)
                        rows.append(row)
                        print(f"[tf] {n_sent:3d} {name:13s} p{pss}: NO-REPORT")
                        continue
                    try:
                        _, status, eps_s, code_s = dec.split(":")
                        eps = int(eps_s)
                        code = int(code_s)
                    except ValueError:
                        n_proto += 1
                        row.update(verdict="PROTOCOL-ERROR", line=dec)
                        rows.append(row)
                        print(f"[tf] {n_sent:3d} {name:13s} p{pss}: BAD LINE "
                              f"{dec[:40]!r}")
                        continue
                    seen_codes.add(code)
                    got = None
                    verdict = "MISSED"
                    if status in ("O", "C"):
                        ts_v, td_v, ver = reader.wait_for("V:", 3.0)
                        if ver is None:
                            n_proto += 1
                            row.update(verdict="PROTOCOL-ERROR",
                                       note="no V: after verified decode")
                            rows.append(row)
                            continue
                        got = ver[2:]
                        if got.lower() == data.hex().lower():
                            verdict = "DELIVERED"
                        else:
                            verdict = "CATASTROPHIC"
                            n_cat += 1
                    row.update(verdict=verdict, status=status, code=code,
                               eps_centi=eps, got=got)
                    rows.append(row)
                    cz = ("R" + CAUSE.get(status[1], "?")) \
                        if status.startswith("R") else status
                    print(f"[tf] {n_sent:3d} {name:13s} p{pss} code{code}"
                          f"({CODE_EPS.get(code,'?'):>6s}%): {verdict:12s} "
                          f"{cz:10s} eps {eps/100.0:+.2f}%")

    # ---- per-code / per-payload tally -----------------------------------
    tab = {}
    for r in rows:
        c = r.get("code")
        if c is None:
            continue
        cell = tab.setdefault(c, {}).setdefault(r["pattern"], [0, 0])
        cell[1] += 1
        cell[0] += r["verdict"] == "DELIVERED"
    print()
    print("=" * 78)
    pats = [n for n, _ in FRAMES]
    print(f"{'code(eps table)':16s}" + "".join(f"{p[:7]:>8s}" for p in pats)
          + "   TOTAL")
    summary = {}
    for c in CODES:
        tot = [0, 0]
        cells = []
        for p in pats:
            d, n = tab.get(c, {}).get(p, [0, 0])
            tot[0] += d
            tot[1] += n
            cells.append(f"{d}/{n}")
        summary[c] = {"delivered": tot[0], "n": tot[1]}
        print(f"{c} ({CODE_EPS[c]:>6s}%)     " +
              "".join(f"{s:>8s}" for s in cells) +
              f"   {tot[0]}/{tot[1]}")
    print(f"no-report {n_noreport}, catastrophic {n_cat}, "
          f"protocol-errors {n_proto}, frames sent {n_sent}")
    print("=" * 78)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "firmware": "rbarf_prod_tf.c (cycle {7,0,6,1}) VERBOSE=1 + "
                        "PROD_RELS (ND_DATA=48, CHK_LEN=4, CAP_BYTES=288)",
            "design": "forced-trim round-robin, one code per report; "
                      "adaptive per-payload until all 4 codes seen; "
                      "single transmission; thermal trajectory shared",
        },
        "summary": {"per_code": summary, "sent": n_sent,
                    "no_report": n_noreport, "catastrophic": n_cat,
                    "protocol_errors": n_proto},
        "rows": rows,
    }, indent=1))
    print(f"[tf] wrote {out}")
    if n_cat or n_proto:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
