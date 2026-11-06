"""Model-free test: is the intra-loop slot structure constant?

In a 1250 ns-periodic payload region, model phase(i,s) = (psi_i + o_s) mod 1250
with psi_i free per iteration and o_s free per slot.  Alternating maximization.
If this reaches ~100% the slot offsets are constant and all the trouble is in
the loop period; if not, the offsets themselves move.
"""
import sys
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

BIT = 1250.0
meta, allc = load_dataset()


def levels(pat, rep, i0, i1):
    for c in allc:
        if c['pattern'] == pat and c['rep'] == rep:
            s = linearize(c['capture'])
            g = {}
            for it, sl, v in s:
                g[(it, sl)] = v
            return np.array([[g[(i, k)] for k in range(8)]
                             for i in range(i0, i1)], dtype=np.int8)


def fit(L, width, rounds=60):
    ni, ns = L.shape
    grid = np.arange(0, BIT, 1.0)
    o = np.array([s * BIT / 4.0 for s in range(ns)]) % BIT   # arbitrary init
    psi = np.zeros(ni)
    best = -1
    for r in range(rounds):
        # optimize psi_i
        ph = (grid[:, None] + o[None, :]) % BIT
        pred = (ph < width).astype(np.int8)          # [1250, ns]
        m = (pred[:, None, :] == L[None, :, :]).sum(axis=2)   # [1250, ni]
        psi = grid[np.argmax(m, axis=0)]
        # optimize o_s
        ph = (psi[:, None] + grid[None, :]) % BIT
        pred = (ph < width).astype(np.int8)          # [ni, 1250]
        m = (pred[:, :, None] == L[:, None, :]).sum(axis=0)   # [1250, ns]
        o = grid[np.argmax(m, axis=0)]
        ph = (psi[:, None] + o[None, :]) % BIT
        tot = int(((ph < width).astype(np.int8) == L).sum())
        if tot == best:
            break
        best = tot
    return best, ni * ns, o, psi


for pat, w, i0, i1 in (('zeros', 350.0, 17, 79), ('ones', 700.0, 17, 79)):
    for rep in (0, 1, 2):
        L = levels(pat, rep, i0, i1)
        b, n, o, psi = fit(L, w)
        print(f"{pat} r{rep}: {b}/{n} = {b/n:.2%}  o={np.round(o,0).tolist()}")
        print("   psi:", np.round(psi, 0).astype(int).tolist())
