"""Careful oracle scan over L (with phi optimised at each L) for the
captures where the span anchor and the periodogram disagree."""
import sys
import numpy as np
from common import load_all, wave

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0


def scan(cap, a, Ls, phis):
    u = cap["it"] + a[cap["slot"]]
    lev = cap["lev"]
    best = np.empty(len(Ls)); bphi = np.empty(len(Ls))
    for k, L in enumerate(Ls):
        base = u * L
        sc = np.array([(wave(cap["bits"], base + p) == lev).sum() for p in phis])
        j = int(np.argmax(sc)); best[k] = sc[j]; bphi[k] = phis[j]
    return best, bphi


if __name__ == "__main__":
    meta, caps = load_all()
    want = sys.argv[1:] or ["p55", "sparse", "count", "lone1", "msb1",
                            "edges", "zeros", "aa", "ones"]
    Ls = np.arange(2470.0, 2540.0, 0.5)
    phis = np.arange(-1300.0, 1300.0, 10.0)
    for cap in caps:
        if cap["pattern"] not in want or cap["rep"] != 0:
            continue
        sc, bp = scan(cap, A, Ls, phis)
        k = int(np.argmax(sc))
        # refine
        Ls2 = np.arange(Ls[k] - 1.0, Ls[k] + 1.0, 0.05)
        phis2 = np.arange(bp[k] - 20, bp[k] + 20, 1.0)
        sc2, bp2 = scan(cap, A, Ls2, phis2)
        k2 = int(np.argmax(sc2))
        top = np.argsort(sc)[::-1][:6]
        s = " ".join(f"{Ls[t]:.1f}:{sc[t]/5117:.3f}" for t in sorted(top))
        print(f"{cap['pattern']:11s} best L={Ls2[k2]:8.2f} phi={bp2[k2]:7.1f} "
              f"match={sc2[k2]/5117:.4f} | top: {s}")
