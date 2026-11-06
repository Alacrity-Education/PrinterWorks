"""Per-capture exact slot calibration with a PER-SLOT branch-cost term.

Every sample is taken by `BTJT PC_IDR,#3,skip / NOP / RLC A`.  Reading
HIGH takes the branch and skips the NOP; the net cost difference between
the taken and the not-taken path need not be the same at every sample
site (STM8 prefetch/alignment), so allow one delta per slot:

    A(i,s) = i*G + o[s] - sum_j d[j] * C_j(i,s)

C_j(i,s) = number of HIGH reads at slot j strictly before sample (i,s).
For fixed (G, d, h1, h0) the 8 offsets still decouple, so the same
difference-array + sliding-window-max DP finds the exact optimum.
"""
import numpy as np

import dpfit
import fitlib as F
from dpfit import GRID, NG, STEP, GAP_MIN, GAP_MAX

CY = 62.5


def counts(cap):
    """C[m, j] = #HIGH reads at slot j strictly before sample m (active)."""
    sl, lv = cap["asl"], cap["alv"]
    n = len(sl)
    C = np.zeros((n, 8))
    run = np.zeros(8)
    for m in range(n):
        C[m] = run
        run[sl[m]] += lv[m]
    return C


def dp_from_base(cap, base, B, L, o0_box=(-140.0, 440.0)):
    """base[m] = model time of sample m WITHOUT o[slot]."""
    sl, lv = cap["asl"], cap["alv"]
    NEG = -(1 << 30)
    covs = []
    for s in range(8):
        m = sl == s
        covs.append(dpfit.coverage(base[m], lv[m].astype(np.int64),
                                   B).astype(np.int64))
    gmin_idx = int(np.ceil(GAP_MIN / STEP))
    gmax_idx = int(np.floor(GAP_MAX / STEP))
    w = gmax_idx - gmin_idx + 1
    dp = covs[0].copy()
    dp[(GRID < o0_box[0]) | (GRID > o0_box[1])] = NEG
    back = []
    for s in range(1, 8):
        prev = dp
        b = np.full(NG, NEG, dtype=np.int64)
        arg = np.full(NG, -1, dtype=np.int64)
        if gmin_idx < NG:
            b[gmin_idx:] = prev[:NG - gmin_idx]
            arg[gmin_idx:] = np.arange(NG - gmin_idx)
        acc, aarg = b, arg
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
    dp = dp.copy()
    dp[(GRID < L - 1050.0) | (GRID > L + 320.0)] = NEG
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


def scan(cap, C, B, Ls, d):
    """Best over the L grid for a fixed d vector."""
    it = cap["ait"]
    shift = C @ np.asarray(d, float)
    best = (-1, None, None)
    for L in Ls:
        base = it * L - shift
        o, tot = dp_from_base(cap, base, B, L)
        if tot > best[0]:
            best = (tot, L, o)
    return best


def fit_capture(cap, h1, h0, Ls, dvals=(-2, -1, 0, 1, 2), rounds=4,
                d0=None, log=None):
    """Coordinate descent on the (quantised) per-slot deltas."""
    C = counts(cap)
    B = F.edges_of(cap["bits"], h1, h0)
    d = np.zeros(8) if d0 is None else np.array(d0, float)
    tot, L, o = scan(cap, C, B, Ls, d)
    for r in range(rounds):
        prev = tot
        for s in range(8):
            cur = d[s]
            bb = (tot, L, o, cur)
            for q in dvals:
                v = q * CY
                if v == cur:
                    continue
                d[s] = v
                t2, L2, o2 = scan(cap, C, B, Ls, d)
                if t2 > bb[0]:
                    bb = (t2, L2, o2, v)
            tot, L, o, d[s] = bb
        if log:
            log(f"    r{r}: {tot}/{cap['an']} L={L:.2f} "
                f"d={(d/CY).astype(int).tolist()} o={np.round(o,0).tolist()}")
        if tot <= prev:
            break
    return tot, L, o, d.copy()
