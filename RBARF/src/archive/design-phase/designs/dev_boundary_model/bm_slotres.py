"""Per-slot residual position error on the oracle grid.

Hold the fitted per-loop phase and tau; add a per-slot offset delta_s and
find the delta that minimises that slot's own sample mismatches.  A slot
whose true cycle position differs from C[s] shows up as a non-zero delta.
"""
import json

import numpy as np

from bm_common import BIT_NS, load
from bm_phase import C, NL, H1, H0

D = np.arange(-160.0, 161.0, 2.0)


def main():
    meta, caps = load()
    fin = json.load(open("bm_final.json"))
    tot = np.zeros((8, len(D)))
    n = np.zeros(8)
    for c in caps:
        r = fin[c["key"]]
        phi = np.array(r["phi"])
        m = c["it"] < NL
        it, sl, lv = c["it"][m], c["sl"][m], c["lv"][m]
        base = 2500.0 * it + phi[it] + r["tau"] * C[sl]
        hwv = np.where(c["bits"] == 1, H1, H0)
        for s in range(8):
            k = sl == s
            t = base[k][:, None] + D[None, :]
            j = np.floor(t / BIT_NS).astype(np.int64)
            ok = (j >= 0) & (j < 192)
            jc = np.clip(j, 0, 191)
            pred = (ok & ((t - jc * BIT_NS) < hwv[jc])).astype(np.int8)
            tot[s] += (pred != lv[k][:, None]).sum(axis=0)
            n[s] += int(k.sum())
    print("slot  n     best_delta  mism@0   mism@best   curve (every 20 ns)")
    for s in range(8):
        b = int(np.argmin(tot[s]))
        z = int(np.argmin(np.abs(D)))
        cur = " ".join(f"{int(tot[s][i]):4d}" for i in range(0, len(D), 10))
        print("%d  %5d   %+6.0f ns   %5d      %5d   %s"
              % (s, n[s], D[b], tot[s][z], tot[s][b], cur))
    print("D grid every 20 ns:", [int(x) for x in D[::10]])
    # combined: what if only slot 7 moves?
    base0 = sum(tot[s][int(np.argmin(np.abs(D)))] for s in range(8))
    alt = base0 - tot[7][int(np.argmin(np.abs(D)))] + tot[7].min()
    print(f"total mismatch delta=0: {int(base0)}; with slot7 shifted "
          f"{D[int(np.argmin(tot[7]))]:+.0f} ns: {int(alt)}")


if __name__ == "__main__":
    main()
