"""E15: how accurate must the anchor be?  Perturb the (known-exact) anchor
and watch BER among decidable cells."""
import sys

import numpy as np

sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/bench")
from patterns import PATTERNS                    # noqa: E402
import synth                                     # noqa: E402
from common import bits_of, BIT_NS               # noqa: E402

G, P = 40.0, np.array([0., 4., 8., 12., 16., 20., 26., 31.])
H1, H0 = synth.T1H_NS, synth.T0H_NS


def cells(u, ob, t0, k):
    t = t0 + k * u
    hard = np.zeros(128, int)
    nd = np.zeros(128, int)
    for j in range(32, 160):
        lo = j * BIT_NS
        m = (t >= lo) & (t < lo + BIT_NS)
        if not m.any():
            continue
        p, o = t[m] - lo, ob[m]
        s1 = int(((p < H1) == o).sum()) - int(((p < H1) != o).sum())
        s0 = int(((p < H0) == o).sum()) - int(((p < H0) != o).sum())
        hard[j - 32] = 1 if s1 > s0 else 0
        nd[j - 32] = int(((p >= H0) & (p < H1)).sum())
    return hard, nd


for eps in (-0.075, -0.003, 0.075):
    print(f"eps={eps:+.3f}")
    ktrue = 62.5 / (1 + eps)
    print(f"{'dt0(ns)':>9} " + " ".join(f"{d:+7.0f}" for d in
                                        (-160, -120, -80, -40, 0, 40, 80, 120, 160)))
    for dkrel in (0.0, 2e-4, 5e-4, 1e-3):
        row = []
        for dt in (-160, -120, -80, -40, 0, 40, 80, 120, 160):
            e = d = 0
            for name, payload in PATTERNS.items():
                s = synth.synth_capture(payload, eps=eps, phase_ns=100.0)
                it = np.array([a for a, _, _ in s], float)
                sl = np.array([b for _, b, _ in s])
                ob = np.array([v for _, _, v in s], bool)
                u = it * G + P[sl]
                hard, nd = cells(u, ob, 100.0 + dt, ktrue * (1 + dkrel))
                truth = bits_of(payload)
                dec = nd > 0
                e += int(((hard != truth) & dec).sum())
                d += int(dec.sum())
            row.append(100 * e / d)
        print(f"dk={dkrel*100:5.3f}%  " + " ".join(f"{v:7.2f}" for v in row))
