"""Per-loop feasible-window diagnostic: is the time base linear in i?"""
import sys

import numpy as np

import model
from model import wire_levels


def loop_windows(cap, o, h1, h0, k, T_guess, span=900.0, step=0.5):
    """For each loop, the feasible interval of t(i,0) (all 8 samples match)."""
    o = np.asarray(o, float)
    bits = cap["bits"]
    res = []
    nit = min(int(cap["it"].max()) + 1, len(T_guess))
    grid = {}
    for i, s, v in zip(cap["it"], cap["sl"], cap["lv"]):
        grid.setdefault(int(i), {})[int(s)] = int(v)
    for i in range(nit):
        d = grid[i]
        cand = np.arange(T_guess[i] - span, T_guess[i] + span, step)
        ok = np.ones(len(cand), bool)
        for s, v in d.items():
            t = cand + k * o[s]
            ok &= (wire_levels(t, bits, h1, h0) == v)
        idx = np.nonzero(ok)[0]
        if len(idx) == 0:
            res.append(None)
        else:
            # take the contiguous run closest to the guess
            splits = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
            best = min(splits, key=lambda r: abs(cand[r].mean() - T_guess[i]))
            res.append((cand[best[0]], cand[best[-1]]))
    return res


def main():
    meta, caps = model.load()
    byk = {c["key"]: c for c in caps}
    o = np.array([62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0])
    G = 2500.0
    for key in sys.argv[1:] or ["ones_0", "zeros_0", "aa_0", "rnd1_0"]:
        cap = byk[key]
        best = None
        for k in np.arange(0.995, 1.016, 2e-5):
            for t0 in np.arange(-150, 350, 8.0):
                T = t0 + k * (np.arange(102) * G)
                # quick score on the linear model
                A = cap["it"][:816] * G + o[cap["sl"][:816]]
                m = int(np.count_nonzero(
                    wire_levels(t0 + k * A, cap["bits"], 750.0, 375.0)
                    == cap["lv"][:816]))
                if best is None or m > best[0]:
                    best = (m, t0, k)
        m, t0, k = best
        T = t0 + k * G * np.arange(102)
        w = loop_windows(cap, o, 750.0, 375.0, k, T)
        print(f"=== {key}  linear-best {m}/816  t0={t0:.1f} k={k:.5f} "
              f"(L={k*G:.2f} ns)")
        Ncum = np.concatenate([[0], np.cumsum(cap["lv"].astype(np.int64))[:-1]])
        for i in range(0, 100):
            if w[i] is None:
                print(f"  {i:3d}  INFEASIBLE")
            else:
                lo, hi = w[i]
                mid = (lo + hi) / 2
                print(f"  {i:3d}  u=[{lo-T[i]:8.1f},{hi-T[i]:8.1f}] "
                      f"mid={mid-T[i]:8.1f}  N={Ncum[i*8]}")


if __name__ == "__main__":
    main()
