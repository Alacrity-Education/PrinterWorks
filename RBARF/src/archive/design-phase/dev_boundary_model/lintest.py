"""Can a smooth global time base stay inside the per-loop feasible
intervals?  (intervals from the ground-truth free-S fit)"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import load_dataset  # noqa
from wander import intervals  # noqa

F5 = [0.0, 0.1, 0.2, 0.2804, 0.4, 0.51, 0.65, 0.7748]
FDOC = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.775]


def best_linear(lo, hi):
    n = len(lo)
    it = np.arange(n)
    best = (-1, 0, 0)
    for L in np.arange(2470, 2545, 0.05):
        blo = lo - L * it
        bhi = hi - L * it
        # max number of overlapping [blo,bhi] intervals
        pts = np.concatenate([blo, bhi])
        cnt = ((blo[None, :] <= pts[:, None]) & (pts[:, None] <= bhi[None, :])).sum(axis=1)
        k = int(np.argmax(cnt))
        if cnt[k] > best[0]:
            best = (int(cnt[k]), L, float(pts[k]))
    return best


def best_quad(lo, hi):
    n = len(lo)
    it = np.arange(n)
    best = (-1, 0, 0, 0)
    for D in np.arange(-0.35, 0.351, 0.025):
        l2 = lo - D * it ** 2
        h2 = hi - D * it ** 2
        c, L, B = best_linear(l2, h2)
        if c > best[0]:
            best = (c, L, B, D)
    return best


def main():
    meta, caps = load_dataset()
    for name, F in (("F5", F5), ("Fdoc", FDOC)):
        print("=== F:", name)
        tl = tq = tn = 0
        for cap in caps:
            if cap["rep"] != 0:
                continue
            iv = intervals(cap, F)
            lo = np.array([x[0] for x in iv])
            hi = np.array([x[1] for x in iv])
            cl, L, B = best_linear(lo, hi)
            cq, Lq, Bq, D = best_quad(lo, hi)
            tl += cl
            tq += cq
            tn += len(iv)
            print(f"  {cap['pattern']:11s} lin {cl:3d}/{len(iv)} (L={L:.2f} B={B:7.1f})"
                  f"   quad {cq:3d}/{len(iv)} (L={Lq:.2f} D={D:+.3f})")
        print(f"  TOTAL lin {tl}/{tn}  quad {tq}/{tn}")


if __name__ == "__main__":
    main()
