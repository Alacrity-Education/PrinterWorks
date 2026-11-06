"""How much per-loop timing jitter does the data demand?

DP over loops: state = loop-start time on a grid, transition constrained
to phi_{i+1} - phi_i in [L-delta, L+delta].  delta = 0 is the rigid
static model; growing delta shows how much per-loop wander is needed to
explain the samples, and the recovered trajectory shows its structure.
"""
import numpy as np

import fitlib as F

STEP = 2.0


def build_cov(cap, o, L, B, W=520.0, nloops=96):
    n = int(2 * W / STEP)
    rel = -W + STEP * np.arange(n)
    it, sl, lv = cap["ait"], cap["asl"], cap["alv"]
    cov = np.zeros((nloops, n), dtype=np.int32)
    for i in range(nloops):
        m = it == i
        base = i * L + rel
        for s, v in zip(sl[m], lv[m]):
            cov[i] += (F.level_at(base + o[s], B) == v)
    return cov, rel


def dp_jitter(cov, rel, delta):
    nloops, n = cov.shape
    w = int(2 * delta / STEP) + 1
    NEG = -(1 << 30)
    dp = cov[0].astype(np.int64)
    back = []
    off = int(round(delta / STEP))       # phi_{i+1}-phi_i = L + rel_j - rel_g
    for i in range(1, nloops):
        b = np.full(n, NEG, dtype=np.int64)
        arg = np.full(n, -1, dtype=np.int64)
        # state j at loop i can come from g with rel_g - rel_j in [-delta, delta];
        # b[j] = dp[j+off] so the width-w trailing max covers [j-off, j+off]
        src = np.arange(n) + off
        valid = (src >= 0) & (src < n)
        b[valid] = dp[src[valid]]
        arg[valid] = src[valid]
        acc, aarg = b, arg
        sh = 1
        while sh < w:
            t = min(sh, w - sh)
            cand = np.full(n, NEG, dtype=np.int64)
            cand[t:] = acc[:-t]
            carg = np.full(n, -1, dtype=np.int64)
            carg[t:] = aarg[:-t]
            take = cand > acc
            acc = np.where(take, cand, acc)
            aarg = np.where(take, carg, aarg)
            sh += t
        dp = acc + cov[i]
        back.append(aarg)
    g = int(np.argmax(dp))
    tot = int(dp[g])
    path = [0] * nloops
    for i in range(nloops - 1, 0, -1):
        path[i] = g
        g = int(back[i - 1][g])
    path[0] = g
    return tot, np.array([rel[p] for p in path])
