"""Calibration library for the STM8 GPIO oversampler timing model.

Model
-----
Sample (i, s) is read at receiver-clock position

    A(i,s) = i*G + P[s] - d * N(i,s)

    P[s]   = sum(g[0..s-1])   nominal intra-loop offset (ns, "all-low" path)
    G      = sum(g[0..7])     nominal loop length (ns, "all-low" path)
    N(i,s) = number of HIGH samples strictly before (i,s), chronological
    d      = per-high-sample loop shortening (ns)

and lands on the transmitter time axis at

    t(i,s) = t0 + k * A(i,s),      k = 1/(1+eps)

t0, eps are per-capture nuisances.  The d term is mechanistic: every
sample is `BTJT PC_IDR,#3,skip / NOP / RLC A`; a HIGH read takes the
branch and skips the NOP, so a high sample costs one cycle less.

Wire model: bit period exactly 1250 ns, '1' high for eff_high_1 ns,
'0' high for eff_high_0 ns (nominal 750 / 375; corrections absorb the
STM8 input threshold and edge-rate skew).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RECON = HERE.parent.parent
BIT_NS = 1250.0
CY = 62.5
ACTIVE_LOOPS = 100          # frame = 192 bits = 240 us ~= 96 loops


def load(active_loops=ACTIVE_LOOPS):
    sys.path.insert(0, str(RECON))
    import harness
    meta, raw = harness.load_dataset()
    caps = []
    for c in raw:
        samples = harness.linearize(c["capture"])
        it = np.array([i for i, _, _ in samples], dtype=np.float64)
        sl = np.array([s for _, s, _ in samples], dtype=np.int64)
        lv = np.array([v for _, _, v in samples], dtype=np.int8)
        # cumulative highs strictly before each sample (full capture)
        N = np.concatenate([[0.0], np.cumsum(lv.astype(np.float64))[:-1]])
        frame = bytes.fromhex(c["frame"])
        bits = np.array([(b >> (7 - j)) & 1 for b in frame for j in range(8)],
                        dtype=np.int8)
        m = it < active_loops
        caps.append(dict(
            key=f"{c['pattern']}_{c['rep']}", pattern=c["pattern"], rep=c["rep"],
            it=it, sl=sl, lv=lv, N=N, bits=bits, n=len(lv),
            ait=it[m], asl=sl[m], alv=lv[m], aN=N[m], an=int(m.sum()), amask=m,
        ))
    return meta, caps


def edges_of(bits, h1, h0):
    """Sorted edge times; level(t) = searchsorted(B,t,'right') & 1."""
    k = np.arange(len(bits), dtype=np.float64)
    rise = k * BIT_NS
    fall = rise + np.where(bits == 1, h1, h0)
    B = np.empty(2 * len(bits))
    B[0::2] = rise
    B[1::2] = fall
    return B


def level_at(t, B):
    return (np.searchsorted(B, t, side="right") & 1).astype(np.int8)


def miss_dist(t, B, lv):
    """(n_match, sum of |t - nearest edge| over mismatched samples)."""
    idx = np.searchsorted(B, t, side="right")
    pred = (idx & 1).astype(np.int8)
    bad = pred != lv
    if not bad.any():
        return len(t), 0.0
    tb = t[bad]
    ib = idx[bad]
    lo = np.where(ib > 0, B[np.clip(ib - 1, 0, len(B) - 1)], -np.inf)
    hi = np.where(ib < len(B), B[np.clip(ib, 0, len(B) - 1)], np.inf)
    dd = np.minimum(tb - lo, hi - tb)
    return len(t) - int(bad.sum()), float(dd.sum())


# ---------------------------------------------------------------- objective

def A_of(cap, o, G, d, active=True):
    o = np.asarray(o, float)
    if active:
        return cap["ait"] * G + o[cap["asl"]] - d * cap["aN"]
    return cap["it"] * G + o[cap["sl"]] - d * cap["N"]


PW = 1e-3   # weight of the mismatch-depth term (ns -> match units)


def obj(A, B, lv, t0, k):
    m, pd = miss_dist(t0 + k * A, B, lv)
    return m - pd * PW, m


def fit_tk_grid(A, B, lv, t0s, ks):
    best = (-1e18, 0.0, 1.0, 0)
    for k in ks:
        base = k * A
        for t0 in t0s:
            idx = np.searchsorted(B, t0 + base, side="right")
            m = int(np.count_nonzero((idx & 1).astype(np.int8) == lv))
            if m > best[3]:
                best = (float(m), t0, k, m)
    return best


def polish_tk(A, B, lv, t0, k, st=20.0, sk=4e-5, tol=1e-4, maxit=3000):
    v, m = obj(A, B, lv, t0, k)
    it = 0
    while st > tol and it < maxit:
        it += 1
        found = None
        for dt, dk in ((st, 0.0), (-st, 0.0), (0.0, sk), (0.0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            vv, mm = obj(A, B, lv, t0 + dt, k + dk)
            if vv > v:
                v, m, found = vv, mm, (t0 + dt, k + dk)
        if found is None:
            st /= 2.0
            sk /= 2.0
        else:
            t0, k = found
    return v, m, t0, k


def evaluate(caps, o, G, d, h1, h0, nuis, refit=True, active=True):
    """Returns (total objective, total matches, total samples)."""
    tot_v = 0.0
    tot_m = 0
    tot_n = 0
    for c in caps:
        A = A_of(c, o, G, d, active)
        B = edges_of(c["bits"], h1, h0)
        lv = c["alv"] if active else c["lv"]
        t0, k = nuis[c["key"]][:2]
        if refit:
            v, m, t0, k = polish_tk(A, B, lv, t0, k)
            nuis[c["key"]] = (t0, k, m)
        else:
            v, m = obj(A, B, lv, t0, k)
        tot_v += v
        tot_m += m
        tot_n += len(lv)
    return tot_v, tot_m, tot_n
