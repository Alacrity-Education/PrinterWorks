"""Assumption-free tracking of the per-loop start time.

DP over loops: state = t(i,0) on a 1 ns grid, score = number of the loop's
8 samples that the wire model reproduces, transition = loop length within
[Lmin, Lmax].  The recovered T_i tells us what the real time base does
without imposing linearity.
"""
import sys

import numpy as np

import model
from model import wire_levels

G = 2500.0


def loop_scores(cap, o, h1, h0, nloop, half=2000, step=1.0):
    """score[i, j] for candidate t(i,0) = i*G - half + j*step."""
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


def dp(off, sc, dl=90.0, step=1.0):
    """Best path with |L - G| <= dl."""
    n, m = sc.shape
    w = int(round(dl / step))
    best = sc[0].astype(np.int32)
    back = np.zeros((n, m), dtype=np.int32)
    for i in range(1, n):
        # prev index j maps to same off index (since base already has i*G)
        pad = np.full(m + 2 * w, -10**6, dtype=np.int32)
        pad[w:w + m] = best
        strides = np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1)
        rel = strides.argmax(axis=1)
        mx = strides.max(axis=1)
        am = np.clip(rel - w + np.arange(m), 0, m - 1)
        back[i] = am
        best = mx + sc[i]
    path = np.zeros(n, dtype=np.int32)
    path[-1] = int(np.argmax(best))
    for i in range(n - 1, 0, -1):
        path[i - 1] = back[i][path[i]]
    return best.max(), path


def main():
    meta, caps = model.load()
    byk = {c["key"]: c for c in caps}
    o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    h1, h0 = 750.0, 375.0
    nloop = 96
    for key in sys.argv[1:] or ["ones_0", "zeros_0", "p55_0"]:
        cap = byk[key]
        off, sc = loop_scores(cap, o, h1, h0, nloop)
        tot, path = dp(off, sc)
        T = np.arange(nloop) * G + off[path]
        L = np.diff(T)
        print(f"=== {key}: DP best {tot}/{nloop*8} "
              f"({100*tot/(nloop*8):.2f}%)  mean L={L.mean():.2f} "
              f"min={L.min():.1f} max={L.max():.1f}")
        for i in range(nloop):
            print(f"  {i:3d} T={T[i]:10.1f} off={off[path[i]]:8.1f} "
                  f"L={(L[i] if i < nloop-1 else float('nan')):7.1f} "
                  f"score={sc[i][path[i]]}")


if __name__ == "__main__":
    main()
