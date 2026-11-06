"""Exact per-slot sweep-line calibration.

For a fixed loop period L and per-high shortening d, the model time of
sample (i,s) is

    T = i*L + o[s] - d*N(i,s)                 (t0 absorbed into o[])

so the 8 slot offsets DECOUPLE: for each slot, every loop i contributes a
constraint "level(c_i + o) == lv_i" whose solution set in o is a union of
intervals.  A sweep line over those intervals gives the o[s] that
satisfies the maximum number of constraints -- the exact optimum for that
slot, no local minima.  Grid over (L, d) on the outside.
"""
import numpy as np

import fitlib as F

MAXR = 10          # max signal regions spanned by the o-window


def slot_opt(c, v, B, lo, hi):
    """Best o in [lo,hi] and its hit count for one slot.

    c: base times (n,), v: observed levels (n,), B: edge times.
    """
    n = len(c)
    xlo = c + lo
    xhi = c + hi
    j0 = np.searchsorted(B, xlo, side="right")
    j1 = np.searchsorted(B, xhi, side="right")
    j = j0[:, None] + np.arange(MAXR)[None, :]
    ok = (j <= j1[:, None]) & ((j & 1) == v[:, None].astype(np.int64))
    jm1 = np.clip(j - 1, 0, len(B) - 1)
    jc = np.clip(j, 0, len(B) - 1)
    a = np.where(j > 0, B[jm1], -1e15)
    b = np.where(j < len(B), B[jc], 1e15)
    ai = np.maximum(a, xlo[:, None]) - c[:, None]
    bi = np.minimum(b, xhi[:, None]) - c[:, None]
    ok &= bi > ai
    ai = ai[ok]
    bi = bi[ok]
    if len(ai) == 0:
        return lo, 0
    pts = np.concatenate([ai, bi])
    dlt = np.concatenate([np.ones(len(ai)), -np.ones(len(bi))])
    # intervals are half-open [a, b): at equal x process closes before opens
    order = np.lexsort((dlt, pts))
    sp = pts[order]
    cs = np.cumsum(dlt[order])
    best = int(cs.max())
    # widest plateau at the maximum
    idx = np.flatnonzero(cs == best)
    idx = idx[idx + 1 < len(sp)]
    if len(idx) == 0:
        return float(sp[int(np.argmax(cs))]), best
    w = sp[idx + 1] - sp[idx]
    k = idx[int(np.argmax(w))]
    return float(0.5 * (sp[k] + sp[k + 1])), best


def capture_opt(cap, L, d, lo=-250.0, hi=None, B=None):
    """Exact best (o[0..7], hits) for one capture at fixed (L, d)."""
    if hi is None:
        hi = L + 250.0
    it, sl, lv, N = cap["ait"], cap["asl"], cap["alv"], cap["aN"]
    o = np.zeros(8)
    tot = 0
    for s in range(8):
        m = sl == s
        c = it[m] * L - d * N[m]
        os_, h = slot_opt(c, lv[m].astype(np.int64), B, lo, hi)
        o[s] = os_
        tot += h
    return o, tot


def grid_capture(cap, Ls, ds, h1, h0, hbar=None):
    B = F.edges_of(cap["bits"], h1, h0)
    if hbar is None:
        hbar = float(cap["alv"].sum()) / (cap["an"] / 8.0)
    best = (-1, None, None, None)
    for d in ds:
        for Le in Ls:
            L = Le + d * hbar          # Le = effective (mean) loop period
            o, tot = capture_opt(cap, L, d, B=B)
            if tot > best[0]:
                best = (tot, L, d, o)
    return best
