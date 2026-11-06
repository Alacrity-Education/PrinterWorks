"""Assumption-free check of the loop period: does the sample-grid/bit-grid
relationship crawl or is it frozen?

If loop L = 2*1250 + delta, the slot at which successive rising edges are
detected advances by delta per loop.  Print the detected rise slot vs
iteration; a frozen column pattern => |delta| small; a marching pattern
=> large delta.  Also derive delta from a linear fit of (rise slot offset
in ns) vs iteration, which needs no bit counting at all.
"""
import numpy as np
from common import load_all

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)          # cycles
LOOPCY = 40.0


def rise_slots(cap):
    d = np.diff(cap["lev"].astype(int))
    idx = np.nonzero(d > 0)[0]
    return cap["it"][idx], cap["slot"][idx]


if __name__ == "__main__":
    meta, caps = load_all()
    for pat in ("aa", "ones", "p55", "zeros", "rnd1"):
        cap = next(c for c in caps if c["pattern"] == pat and c["rep"] == 0)
        it, sl = rise_slots(cap)
        m = it < 100
        it, sl = it[m], sl[m]
        # per-iteration list of rise slots
        rows = []
        for i in range(0, 96):
            s = sl[it == i]
            rows.append("".join(str(x) for x in s) if len(s) else ".")
        print(f"{pat:6s} rise-slot per loop 0..95: {' '.join(rows)}")
        # crawl estimate: position of the 1st rise in each loop, in cycles
        first = np.array([sl[it == i][0] if (it == i).any() else -1
                          for i in range(96)])
        ok = first >= 0
        x = np.arange(96)[ok]; y = A[first[ok]]
        # unwrap: subtract 2 bits worth of drift, look at slope
        c = np.polyfit(x, y, 1)
        print(f"       first-rise slot-cycle slope = {c[0]:+.4f} cy/loop "
              f"= {c[0]*62.5:+.2f} ns/loop  -> L = {2*1250 + c[0]*62.5:.1f} ns")
        print(f"       distinct first-rise slots: "
              f"{np.bincount(first[ok], minlength=8).tolist()}")
