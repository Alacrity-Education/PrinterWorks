"""How much loop-to-loop phase jitter does the data demand?

Free per-loop phase gives the mismatch floor.  Restricting the loop-to-loop
phase step to +-B ns tells us how rigid the clock really is.
"""
import numpy as np

from bm_common import load
from bm_phase import cost_grid, PHI, STEP

TAU = 62.75
NL = 96


def band_viterbi(cost, B):
    n, m = cost.shape
    band = max(int(B / STEP), 0)
    D = cost[0].astype(float).copy()
    for i in range(1, n):
        best = np.full(m, np.inf)
        for d in range(-band, band + 1):
            src = np.roll(D, d)
            if d > 0:
                src[:d] = np.inf
            elif d < 0:
                src[d:] = np.inf
            best = np.minimum(best, src)
        D = best + cost[i]
    return float(D.min())


def main():
    meta, caps = load()
    N = 0
    res = {}
    for B in (0, 5, 10, 20, 40, 80, 160, 100000):
        res[B] = 0
    freefloor = 0
    widths = []
    for c in caps:
        cg = cost_grid(c, TAU)[:94]
        N += 94 * 8
        freefloor += int(cg.min(axis=1).sum())
        for i in range(94):
            lo = cg[i].min()
            widths.append(float(np.count_nonzero(cg[i] == lo) * STEP))
        for B in res:
            res[B] += int(band_viterbi(cg, B))
    print(f"free per-loop phase floor: {freefloor}/{N} = {100*freefloor/N:.3f}%")
    for B in sorted(res):
        lab = "unbounded" if B > 1000 else f"+-{B} ns/loop"
        print(f"  step limit {lab:14s}: {res[B]}/{N} = {100*res[B]/N:.3f}%")
    w = np.array(widths)
    print(f"per-loop feasible-phase plateau width: med {np.median(w):.0f} ns, "
          f"p10 {np.percentile(w,10):.0f}, p90 {np.percentile(w,90):.0f}")


if __name__ == "__main__":
    main()
