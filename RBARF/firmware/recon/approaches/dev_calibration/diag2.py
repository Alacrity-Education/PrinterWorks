"""Diagnostic: per-capture effective loop period under a STATIC slot model,
vs. the number of HIGH samples in the capture.  If the loop period tracks
the high-count, the BTJT/NOP one-cycle data dependence is real.
"""
import numpy as np
import model
from model import wire_levels

DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)


def fit(cap, Lgrid, t0grid, h1=750.0, h0=375.0, scale_o=True, o=None):
    bits, lv, it, sl = cap["bits"], cap["lv"], cap["it"], cap["sl"]
    best = (-1, 0, 0)
    for L in Lgrid:
        oo = DOC * L / 37.0 if scale_o else o
        A = it * L + oo[sl]
        for t0 in t0grid:
            m = int(np.count_nonzero(wire_levels(t0 + A, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, L, t0)
    return best


def main():
    meta, caps = model.load()
    Lg = np.arange(2470.0, 2560.0, 0.5)
    Tg = np.arange(-200.0, 400.0, 10.0)
    print(f"{'key':14s} {'#high':>6s} {'L_eff':>9s} {'t0':>7s} {'agree%':>7s} {'act%':>7s}")
    for c in caps:
        m, L, t0 = fit(c, Lg, Tg)
        # refine
        for step in (0.1, 0.02):
            Lg2 = np.arange(L - 1.0, L + 1.0, step)
            Tg2 = np.arange(t0 - 20, t0 + 20, max(1.0, step * 20))
            m, L, t0 = fit(c, Lg2, Tg2)
        nh = int(c["lv"].sum())
        act = c["it"] < 100
        A = c["it"] * L + (DOC * L / 37.0)[c["sl"]]
        pred = wire_levels(t0 + A, c["bits"], 750.0, 375.0)
        agr = np.count_nonzero(pred == c["lv"]) / c["n"]
        aact = np.count_nonzero(pred[act] == c["lv"][act]) / act.sum()
        print(f"{c['key']:14s} {nh:6d} {L:9.2f} {t0:7.1f} {100*agr:7.3f} {100*aact:7.3f}")


if __name__ == "__main__":
    main()
