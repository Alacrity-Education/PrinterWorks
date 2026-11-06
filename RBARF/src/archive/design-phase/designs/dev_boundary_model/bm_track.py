"""Model-free per-loop phase tracking.

For each loop i we place its 8 samples at 2500*i + O[s] + phi_i and scan
phi_i.  2500 ns == exactly 2 bit periods, so phi_i is the loop's phase
relative to the bit grid; a plot of phi_i vs i shows the true crawl and
any within-capture drift, with NO global timing model assumed.
"""
import numpy as np

from bm_common import BIT_NS, load, wire_level

CY = 62.5
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * CY


def track(c, O=DOC, h1=750.0, h0=375.0, grid=np.arange(-400.0, 1300.0, 2.0),
          nloops=96):
    it, sl, lv, bits = c["it"], c["sl"], c["lv"], c["bits"]
    out = []
    for i in range(nloops):
        m = it == i
        s = sl[m]
        v = lv[m]
        base = 2500.0 * i + O[s]
        best = []
        for phi in grid:
            pred = wire_level(base + phi, bits, h1, h0)
            nb = int(np.count_nonzero(pred != v))
            best.append(nb)
        best = np.array(best)
        lo = best.min()
        ok = grid[best == lo]
        out.append((i, lo, ok.min(), ok.max(), float(np.median(ok)), len(s)))
    return out


def main():
    meta, caps = load()
    for key in ("aa_0", "zeros_0", "ones_0", "rnd1_0", "p55_0", "aa_1", "aa_2"):
        c = next(x for x in caps if x["key"] == key)
        t = track(c)
        med = np.array([r[4] for r in t])
        nb = np.array([r[1] for r in t])
        # unwrap: phase can wrap by 1250 between loops
        print(f"--- {key}: total min-mismatch {nb.sum()} "
              f"(loops with >0: {int((nb>0).sum())})")
        print("   phi med:", " ".join(f"{x:.0f}" for x in med[:40]))
        print("   phi med:", " ".join(f"{x:.0f}" for x in med[40:96]))
        w = np.array([r[3] - r[2] for r in t])
        print(f"   plateau width: med {np.median(w):.0f} ns  max {w.max():.0f} ns")


if __name__ == "__main__":
    main()
