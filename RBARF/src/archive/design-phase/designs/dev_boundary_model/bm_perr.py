"""Per-slot error rate restricted to INFORMATIVE samples, and vs margin.

An informative sample is one whose in-bit phase p lies in [H0, H1); it
should read HIGH iff the bit is 1.  We tabulate the error rate per slot
and per distance-to-window-edge, which is exactly what the soft model
needs.
"""
import json
from collections import Counter

import numpy as np

from bm_common import BIT_NS, load
from bm_phase import C, NL, H1, H0


def main():
    meta, caps = load()
    fin = json.load(open("bm_final.json"))
    err = Counter(); tot = Counter()
    merr = Counter(); mtot = Counter()
    for c in caps:
        r = fin[c["key"]]
        phi = np.array(r["phi"])
        m = c["it"] < NL
        it, sl, lv = c["it"][m], c["sl"][m], c["lv"][m]
        t = 2500.0 * it + phi[it] + r["tau"] * C[sl]
        j = np.floor(t / BIT_NS).astype(np.int64)
        p = t - j * BIT_NS
        ok = (j >= 0) & (j < 192)
        inf = ok & (p >= H0) & (p < H1)
        b = c["bits"][np.clip(j, 0, 191)]
        bad = inf & (lv != b)
        margin = np.minimum(p - H0, H1 - p)
        for k in np.nonzero(inf)[0]:
            tot[int(sl[k])] += 1
            mb = int(min(margin[k] // 25, 7))
            mtot[mb] += 1
            if bad[k]:
                err[int(sl[k])] += 1
                merr[mb] += 1
    print("slot  informative  errors   rate")
    T = E = 0
    for s in range(8):
        T += tot[s]; E += err[s]
        print("  %d   %8d %7d   %.4f" % (s, tot[s], err[s],
                                         err[s] / max(tot[s], 1)))
    print("  all %8d %7d   %.4f" % (T, E, E / T))
    print("\nmargin to nearest window edge (ns)   errors/total   rate")
    for mb in range(8):
        lo = mb * 25
        lab = f"{lo:3d}-{lo+25:3d}" if mb < 7 else "175+   "
        print("  %s  %7d/%-7d  %.4f" % (lab, merr[mb], mtot[mb],
                                        merr[mb] / max(mtot[mb], 1)))


if __name__ == "__main__":
    main()
