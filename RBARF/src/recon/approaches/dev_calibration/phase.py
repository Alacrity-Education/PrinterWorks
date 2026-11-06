"""Per-loop phase extraction: with slot offsets held fixed, find for every
loop the set of loop-start times phi consistent with its 8 samples, and
report the centre.  Reveals whether the loop period is constant or
data dependent."""
import numpy as np

import fitlib as F
import dpfit


def loop_phase(cap, i, o, B, lo, hi, step=1.0):
    m = cap["ait"] == i
    sl = cap["asl"][m]
    lv = cap["alv"][m].astype(np.int64)
    n = int(round((hi - lo) / step))
    grid = lo + step * np.arange(n)
    c = o[sl]
    xlo = c + lo
    xhi = c + hi
    j0 = np.searchsorted(B, xlo, side="right")
    j1 = np.searchsorted(B, xhi, side="right")
    j = j0[:, None] + np.arange(dpfit.MAXR)[None, :]
    ok = (j <= j1[:, None]) & ((j & 1) == lv[:, None])
    a = np.where(j > 0, B[np.clip(j - 1, 0, len(B) - 1)], -1e15)
    b = np.where(j < len(B), B[np.clip(j, 0, len(B) - 1)], 1e15)
    ai = np.maximum(a, xlo[:, None]) - c[:, None]
    bi = np.minimum(b, xhi[:, None]) - c[:, None]
    ok &= bi > ai
    ai, bi = ai[ok], bi[ok]
    lo_i = np.clip(np.ceil((ai - lo) / step).astype(np.int64), 0, n)
    hi_i = np.clip(np.ceil((bi - lo) / step).astype(np.int64), 0, n)
    diff = np.zeros(n + 1, dtype=np.int32)
    np.add.at(diff, lo_i, 1)
    np.add.at(diff, hi_i, -1)
    cov = np.cumsum(diff)[:n]
    best = int(cov.max())
    idx = np.flatnonzero(cov == best)
    # centre of the widest plateau
    brk = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[0], brk + 1])
    ends = np.concatenate([brk, [len(idx) - 1]])
    w = ends - starts
    q = int(np.argmax(w))
    return float(grid[idx[starts[q]]] + grid[idx[ends[q]]]) / 2.0, best, len(sl)


def track(cap, o, L, h1, h0, nloops=100, win=700.0):
    B = F.edges_of(cap["bits"], h1, h0)
    phis, hits, tots = [], [], []
    for i in range(nloops):
        p, h, t = loop_phase(cap, i, o, B, i * L - win, i * L + win)
        phis.append(p)
        hits.append(h)
        tots.append(t)
    return np.array(phis), np.array(hits), np.array(tots)
