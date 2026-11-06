"""Identifiability scan around the fitted integer-cycle geometry."""
import json

import numpy as np

from bm_common import load
from bm_int import Cap, total

C0 = [1, 4, 8, 13, 17, 21, 27, 31]
DOC = [1, 5, 9, 13, 17, 21, 27, 32]


def main():
    meta, raw = load()
    caps = [Cap(c) for c in raw]
    for c in caps:
        c.prep(750.0, 375.0)
    N = 94 * 8 * len(caps)

    print("tau scan (C fixed):")
    for tau in np.arange(62.0, 63.6, 0.125):
        print(f"  tau={tau:6.3f}  {100*total(caps, C0, tau, 0)/N:.3f}%")

    tau = 62.75
    print(f"\nper-slot scan at tau={tau}:")
    for s in range(1, 8):
        row = []
        for dv in range(-3, 4):
            C = list(C0)
            C[s] += dv
            row.append((dv, 100 * total(caps, C, tau, 0) / N))
        print(f"  C[{s}]={C0[s]:2d}: " +
              "  ".join(f"{dv:+d}:{v:.3f}%" for dv, v in row))

    print("\nnamed variants:")
    for nm, C, t in (("fit", C0, 62.75), ("doc", DOC, 62.5),
                     ("doc@62.75", DOC, 62.75),
                     ("doc-31", [1, 5, 9, 13, 17, 21, 27, 31], 62.75),
                     ("uniform4", [1, 5, 9, 13, 17, 21, 25, 29], 62.75),
                     ("calib", [1, 5, 9, 14, 18, 22, 28, 32], 62.5)):
        print(f"  {nm:10s} C={C} tau={t}: {100*total(caps, C, t, 0)/N:.3f}%")

    print("\nh1/h0 scan at fit:")
    for h1 in (730.0, 740.0, 750.0, 760.0, 770.0):
        row = []
        for h0 in (355.0, 365.0, 375.0, 385.0, 395.0):
            for c in caps:
                c.prep(h1, h0)
            row.append(100 * total(caps, C0, tau, 0) / N)
        print(f"  h1={h1:5.0f}: " + "  ".join(f"{v:.3f}" for v in row))
    for c in caps:
        c.prep(750.0, 375.0)

    print("\nper-capture residual (free-phase, fitted geometry):")
    tot = 0
    for c in caps:
        m = c.mism(C0, tau, 0)
        tot += m
        print(f"  {c.key:14s} {m:4d}/752 = {100*m/752:.2f}%")
    print(f"  TOTAL {tot}/{N} = {100*tot/N:.3f}%")


if __name__ == "__main__":
    main()
