"""Per-capture exact-on-a-grid slot calibration by dynamic programming.

For fixed (L, d, h1, h0) the model time of sample (i,s) is
    T = i*L + o[s] - d*N(i,s)        (t0 absorbed into o[])
so slots decouple except for the physical ordering constraint
    GAP_MIN <= o[s+1] - o[s] <= GAP_MAX,   o[0] in O0_BOX,
    o[7] in [L-1000, L+275]  (wrap gap back to the next loop's slot 0)

cov[s][o] (number of the ~100 loop constraints satisfied by that offset)
is built exactly with a difference array, then a DP over slots with a
sliding-window max finds the global optimum for those (L, d).
"""
import numpy as np

import fitlib as F

STEP = 2.0
OLO = -320.0
OHI = 2760.0
NG = int(round((OHI - OLO) / STEP))
GRID = OLO + STEP * np.arange(NG)
GAP_MIN, GAP_MAX = 120.0, 920.0
MAXR = 12


def coverage(c, v, B):
    """cov[g] = #constraints satisfied when o = GRID[g]."""
    xlo = c + OLO
    xhi = c + OHI
    j0 = np.searchsorted(B, xlo, side="right")
    j1 = np.searchsorted(B, xhi, side="right")
    j = j0[:, None] + np.arange(MAXR)[None, :]
    ok = (j <= j1[:, None]) & ((j & 1) == v[:, None])
    jm1 = np.clip(j - 1, 0, len(B) - 1)
    jc = np.clip(j, 0, len(B) - 1)
    a = np.where(j > 0, B[jm1], -1e15)
    b = np.where(j < len(B), B[jc], 1e15)
    ai = np.maximum(a, xlo[:, None]) - c[:, None]
    bi = np.minimum(b, xhi[:, None]) - c[:, None]
    ok &= bi > ai
    ai = ai[ok]
    bi = bi[ok]
    lo = np.clip(np.ceil((ai - OLO) / STEP).astype(np.int64), 0, NG)
    hi = np.clip(np.ceil((bi - OLO) / STEP).astype(np.int64), 0, NG)
    diff = np.zeros(NG + 1, dtype=np.int32)
    np.add.at(diff, lo, 1)
    np.add.at(diff, hi, -1)
    return np.cumsum(diff)[:NG]


def dp_capture(cap, L, d, B, o0_box=(-120.0, 420.0)):
    it, sl, lv, N = cap["ait"], cap["asl"], cap["alv"], cap["aN"]
    covs = []
    for s in range(8):
        m = sl == s
        c = it[m] * L - d * N[m]
        covs.append(coverage(c, lv[m].astype(np.int64), B).astype(np.int64))
    NEG = -(1 << 30)
    gmin_idx = int(np.ceil(GAP_MIN / STEP))
    gmax_idx = int(np.floor(GAP_MAX / STEP))
    # slot 0 box
    dp = covs[0].copy()
    bad = (GRID < o0_box[0]) | (GRID > o0_box[1])
    dp[bad] = NEG
    back = []
    for s in range(1, 8):
        prev = dp
        w = gmax_idx - gmin_idx + 1
        base = np.full(NG, NEG, dtype=np.int64)
        if gmin_idx < NG:
            base[gmin_idx:] = prev[:NG - gmin_idx]
        arg = np.full(NG, -1, dtype=np.int64)
        if gmin_idx < NG:
            arg[gmin_idx:] = np.arange(NG - gmin_idx)
        # naive sliding window max with argmax (w ~ 400, NG ~ 1540)
        acc = base.copy()
        aarg = arg.copy()
        sh = 1
        while sh < w:
            t = min(sh, w - sh)
            cand = np.full(NG, NEG, dtype=np.int64)
            cand[t:] = acc[:-t]
            carg = np.full(NG, -1, dtype=np.int64)
            carg[t:] = aarg[:-t]
            take = cand > acc
            acc = np.where(take, cand, acc)
            aarg = np.where(take, carg, aarg)
            sh += t
        dp = acc + covs[s]
        back.append(aarg)
    # slot 7 window (loop wrap)
    lo7 = L - 1000.0
    hi7 = L + 300.0
    dp = dp.copy()
    dp[(GRID < lo7) | (GRID > hi7)] = NEG
    g = int(np.argmax(dp))
    tot = int(dp[g])
    o = np.zeros(8)
    for s in range(7, 0, -1):
        o[s] = GRID[g]
        g = int(back[s - 1][g])
        if g < 0:
            return None, -1
    o[0] = GRID[g]
    return o, tot


def grid_capture(cap, Ls, ds, h1, h0, hbar=None):
    B = F.edges_of(cap["bits"], h1, h0)
    if hbar is None:
        hbar = float(cap["alv"].sum()) / (cap["an"] / 8.0)
    best = (-1, None, None, None)
    for d in ds:
        for Le in Ls:
            L = Le + d * hbar
            o, tot = dp_capture(cap, L, d, B)
            if tot > best[0]:
                best = (tot, L, d, o)
    return best
