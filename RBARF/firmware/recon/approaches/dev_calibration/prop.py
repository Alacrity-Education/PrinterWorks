"""Forward/backward interval propagation of the per-loop start time.

Gives the tightest window for each t(i,0) consistent with (a) all 8 of the
loop's samples matching the wire and (b) the loop length staying inside
[G-dl, G+dl].  The resulting T_i sequence is model-free evidence about
what the loop period actually does.
"""
import sys

import numpy as np

import model
from model import wire_levels

G = 2500.0


def feasible(cap, o, h1, h0, nloop, half=1600.0, step=0.5, need=8):
    o = np.asarray(o, float)
    grid = {}
    for i, s, v in zip(cap["it"], cap["sl"], cap["lv"]):
        ii = int(i)
        if ii < nloop:
            grid.setdefault(ii, []).append((int(s), int(v)))
    off = np.arange(-half, half, step)
    sc = np.zeros((nloop, len(off)), dtype=np.int16)
    for i in range(nloop):
        base = i * G + off
        tot = np.zeros(len(off), dtype=np.int16)
        for s, v in grid[i]:
            tot += (wire_levels(base + o[s], cap["bits"], h1, h0) == v)
        sc[i] = tot
    return off, sc


def dilate(mask, w):
    """Boolean dilation by +-w samples."""
    m = mask.astype(np.int32)
    c = np.concatenate([[0], np.cumsum(m)])
    n = len(m)
    lo = np.maximum(np.arange(n) - w, 0)
    hi = np.minimum(np.arange(n) + w + 1, n)
    return (c[hi] - c[lo]) > 0


def propagate(off, sc, dl=100.0, step=0.5, need=8):
    n, m = sc.shape
    w = int(round(dl / step))
    F = sc >= need
    for i in range(n):
        if not F[i].any():
            F[i] = sc[i] >= sc[i].max()
    R = F.copy()
    for i in range(1, n):
        R[i] &= dilate(R[i - 1], w)
        if not R[i].any():
            R[i] = F[i]
    S = R.copy()
    for i in range(n - 2, -1, -1):
        S[i] &= dilate(S[i + 1], w)
        if not S[i].any():
            S[i] = R[i]
    return S


def main():
    meta, caps = model.load()
    byk = {c["key"]: c for c in caps}
    o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    h1, h0 = 750.0, 375.0
    nloop = 96
    for key in sys.argv[1:] or ["ones_0"]:
        cap = byk[key]
        off, sc = feasible(cap, o, h1, h0, nloop)
        S = propagate(off, sc)
        grid = {}
        for i, s, v in zip(cap["it"], cap["sl"], cap["lv"]):
            grid.setdefault(int(i), {})[int(s)] = int(v)
        print(f"=== {key}")
        for i in range(nloop):
            idx = np.nonzero(S[i])[0]
            lo, hi = off[idx[0]], off[idx[-1]]
            pat = ''.join(str(grid[i].get(k, 9)) for k in range(8))
            nh = sum(grid[i].values())
            print(f"  {i:3d} off=[{lo:8.1f},{hi:8.1f}] w={hi-lo:6.1f} "
                  f"pat={pat} nh={nh} maxsc={sc[i].max()}")


if __name__ == "__main__":
    main()
