"""E14: where do the real-capture ANCHOR mismatches sit?

Locks (t0, kappa) on the anchors with the nominal grid, then reports the
mismatch rate per slot, per loop index and per template phase -- the
diagnostic that tells the calibration technique what the affine 8-slot grid
is missing.  Also tries a 2-loop (even/odd iteration) grid.
"""
import sys
from collections import Counter

import numpy as np

from common import load, bits_of, HEADER, TRAILER, BIT_NS

HDR = bits_of(HEADER).astype(bool)
TRL = bits_of(TRAILER).astype(bool)
NW = 900
T0S = np.arange(0., 460., 2.)
KS = np.arange(60.5, 64.5, 0.005)


def score_grid(u, ob, t0s, ks, h1, h0):
    S = np.empty((len(t0s), len(ks)))
    for b, k in enumerate(ks):
        t = t0s[:, None] + k * u[None, :]
        j = np.floor(t / BIT_NS).astype(int)
        act = ((j >= 0) & (j < 32)) | ((j >= 160) & (j < 192))
        jj = np.clip(j, 0, 191)
        bits = np.where(jj < 32, HDR[np.clip(jj, 0, 31)],
                        TRL[np.clip(jj - 160, 0, 31)])
        p = t - jj * BIT_NS
        pred = p < np.where(bits, h1, h0)
        S[:, b] = np.where(act, np.where(pred == ob[None, :], 1, -1), 0).sum(1)
    return S


def main():
    meta, caps = load()
    G = 40.0
    P = np.array([0., 4., 8., 12., 16., 20., 26., 31.])
    h1, h0 = 750.0, 390.0
    by_slot = Counter()
    n_slot = Counter()
    by_loop = Counter()
    n_loop = Counter()
    by_ph = Counter()
    n_ph = Counter()
    tot = n = 0
    for c in caps:
        it = c["it"][:NW].astype(float)
        sl = c["sl"][:NW]
        ob = c["lv"][:NW].astype(bool)
        u = it * G + P[sl]
        S = score_grid(u, ob, T0S, KS, h1, h0)
        a, b = np.unravel_index(np.argmax(S), S.shape)
        t0, k = float(T0S[a]), float(KS[b])
        t = t0 + k * u
        j = np.floor(t / BIT_NS).astype(int)
        act = ((j >= 0) & (j < 32)) | ((j >= 160) & (j < 192))
        jj = np.clip(j, 0, 191)
        bits = np.where(jj < 32, HDR[np.clip(jj, 0, 31)],
                        TRL[np.clip(jj - 160, 0, 31)])
        p = t - jj * BIT_NS
        pred = p < np.where(bits, h1, h0)
        bad = act & (pred != ob)
        tot += int(bad.sum())
        n += int(act.sum())
        for i in np.where(act)[0]:
            by_slot[int(sl[i])] += int(bad[i])
            n_slot[int(sl[i])] += 1
            by_loop[int(it[i]) // 8] += int(bad[i])
            n_loop[int(it[i]) // 8] += 1
            pb = int(p[i] // 125)
            by_ph[pb] += int(bad[i])
            n_ph[pb] += 1
        print(f"{c['key']:14s} t0={t0:6.1f} k={k:.4f} loop={G*k:7.1f} "
              f"anchor mismatch {int(bad.sum()):3d}/{int(act.sum()):3d}",
              flush=True)
    print(f"\nOVERALL anchor mismatch {tot}/{n} = {100*tot/n:.2f}%")
    print("by slot :", {s: f"{100*by_slot[s]/max(n_slot[s],1):.1f}%"
                        for s in range(8)})
    print("by loop-group (8 loops each):",
          {g: f"{100*by_loop[g]/max(n_loop[g],1):.0f}%" for g in sorted(n_loop)})
    print("by cell phase (125 ns bins):",
          {b: f"{100*by_ph[b]/max(n_ph[b],1):.0f}%({n_ph[b]})"
           for b in sorted(n_ph)})


main()
