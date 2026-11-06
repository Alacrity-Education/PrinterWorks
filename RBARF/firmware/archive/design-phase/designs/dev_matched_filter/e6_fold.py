"""E6: phase-fold the periodic payload regions to read off the EFFECTIVE
pulse shape and the true sample grid, without assuming h1/h0.

'zeros' payload  = 128 identical 0 bits  -> period 1250 ns
'ones'  payload  = 128 identical 1 bits  -> period 1250 ns
'aa'/'p55'       = 10101010 / 01010101   -> period 2500 ns
"""
import numpy as np

from common import load
from mf import phase

NB0, NB1 = 32, 160          # payload bit range


def fold_score(u, lv, per, ph0, k, nbin=50):
    """Consistency of level as a function of folded phase (max over any
    single high-window [0,w)) -- returns best agreement and window."""
    ph = np.mod(ph0 + k * u, per)
    order = np.argsort(ph)
    L = lv[order].astype(int)
    # best threshold w: level==1 for ph<w
    # cumulative: agreement(w=ph_i) = (#1 in first i) + (#0 in rest)
    c1 = np.concatenate([[0], np.cumsum(L)])
    tot0 = len(L) - c1[-1]
    agree = c1 + (tot0 - (np.arange(len(L) + 1) - c1))
    i = int(np.argmax(agree))
    w = ph[order][i - 1] if 0 < i <= len(L) else 0.0
    return int(agree[i]), float(w), len(L)


def main():
    meta, caps = load()
    for key, per in (("zeros_0", 1250.), ("zeros_1", 1250.), ("zeros_2", 1250.),
                     ("ones_0", 1250.), ("ones_1", 1250.), ("ones_2", 1250.),
                     ("aa_0", 2500.), ("p55_0", 2500.)):
        c = [x for x in caps if x["key"] == key][0]
        # payload occupies roughly samples 128..640; be conservative
        n0, n1 = 150, 620
        it, sl, lv = c["it"][n0:n1].astype(float), c["sl"][n0:n1], c["lv"][n0:n1]
        u = phase(it, sl)
        best = None
        for k in np.arange(61.8, 63.4, 0.002):
            for ph0 in np.arange(0, per, 10.0):
                a, w, n = fold_score(u, lv, per, ph0, k)
                if best is None or a > best[0]:
                    best = (a, w, k, ph0, n)
        a, w, k, ph0, n = best
        print(f"{key:9s} per={per:6.0f} k={k:.4f} loop={40*k:8.2f} "
              f"high_window={w:7.1f}ns agree={a}/{n} ({100*a/n:.2f}%)")


main()
