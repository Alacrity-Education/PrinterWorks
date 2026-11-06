#!/usr/bin/env python3
"""Which payloads the chase-budget raise actually buys, frame by frame.

Same grid as sweep_amax_tmax.py `suite` (70 single-shot payloads x 5 eps
x 48 arm phases, ND=48), but the outcome is kept PER PAYLOAD and PER
CAPTURE so a gain can be attributed rather than just counted, and so a
regression (a capture that delivered at the baseline and refuses at the
new point) can never hide inside a net total.

  python3 per_payload.py 14:131 16:192
"""
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from amaxlib import (BASE, EPS_GRID, T0_GRID, CAUSE_R, NI,      # noqa: E402
                     make_ref, point, outcome, capture, linearize)
from sweep_amax_tmax import suite_payloads                      # noqa: E402

POINTS = [BASE]
_EV = {}


def _task(arg):
    # POINTS travels IN the task: Python 3.14 defaults to a forkserver
    # start method on Linux, so a runtime-set global is NOT inherited.
    fam, name, data, eps, pts = arg
    global _EV
    if not _EV:
        _EV['ev'] = make_ref(48)
    ev = _EV['ev']
    rows = []
    for t0 in T0_GRID:
        lin = linearize(capture(data, eps, t0))
        per = []
        for p in pts:
            point(ev, *p)
            v, tag, tr, cp = outcome(ev, lin, data)
            per.append((v, tag, tr, cp))
        rows.append((t0, per))
    return (fam, name, eps, rows)


def main(argv):
    global POINTS
    pts = [BASE] + [tuple(int(x) for x in a.split(":")) for a in argv]
    POINTS = pts
    suite = suite_payloads()
    tasks = [(f, n, d, e, pts) for f, n, d in suite for e in EPS_GRID]
    tot = [Counter() for _ in pts]
    per_pay = {}
    moved = []
    with Pool(11) as pool:
        for fam, name, eps, rows in pool.imap_unordered(_task, tasks, 4):
            st = per_pay.setdefault((fam, name), [0] * len(pts))
            for t0, per in rows:
                for i, (v, tag, tr, cp) in enumerate(per):
                    tot[i][v] += 1
                    if v == "DELIVERED":
                        st[i] += 1
                b = per[0]
                for i in range(1, len(pts)):
                    if per[i][0] != b[0]:
                        moved.append((pts[i], fam, name, eps, t0,
                                      b[0], b[1], per[i][0], per[i][1],
                                      per[i][2], per[i][3]))
    hdr = "  ".join("A%dT%d" % p for p in pts)
    print("TOTAL  " + hdr)
    for i, p in enumerate(pts):
        print("  A%-3d T%-5d delivered %5d  wrong %2d  refused %5d"
              % (p[0], p[1], tot[i]["DELIVERED"], tot[i]["WRONG"],
                 tot[i]["REFUSED"]))
    print("\nPER PAYLOAD (only those that move; /240 captures each)")
    for (fam, name), st in sorted(per_pay.items()):
        if len(set(st)) == 1:
            continue
        print("  %-9s %-20s " % (fam, name)
              + "  ".join("%3d" % x for x in st)
              + "   " + "  ".join("%+d" % (x - st[0]) for x in st[1:]))
    print("\nEVERY CAPTURE WHOSE VERDICT MOVES (baseline -> point)")
    for m in sorted(moved, key=lambda r: (r[0], r[1], r[2], r[3], r[4])):
        pt, fam, name, eps, t0, bv, bt, nv, nt, tr, cp = m
        print("  A%-3dT%-4d %-9s %-20s eps%+.2f%% t0=%3.0fns  %-9s(%s) -> "
              "%-9s(%s) trials=%d comps=%d"
              % (pt[0], pt[1], fam, name, eps * 100, t0,
                 bv, CAUSE_R.get(bt, bt), nv, CAUSE_R.get(nt, nt), tr, cp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["14:131", "16:192"]))
