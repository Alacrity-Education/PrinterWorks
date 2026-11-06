"""Timing model + fitting utilities for the STM8 GPIO oversampler.

Model
-----
Sample times are built by walking the sampling loop.  Slot s of loop i is
read at

    t(i,s) = t0 + k * ( i*G + P[s] - d * N(i,s) )

where
    G      = sum(g[0..7])              nominal loop length (ns)
    P[s]   = sum(g[0..s-1])            nominal intra-loop offset (ns)
    N(i,s) = number of HIGH samples strictly before (i,s)
    d      = per-high-sample shortening of the loop (ns)
    k      = 1/(1+eps) per-capture clock scale, t0 per-capture phase.

The `d` term is the mechanistic part: every sample is taken by
`BTJT PC_IDR,#3,skip / NOP / RLC A`.  When the pin reads HIGH the BTJT
branches and the NOP is *skipped*, so a high sample makes the loop one
cycle shorter.  Because N(i,s) is computed from the *observed* levels the
whole time base is a closed-form function of the data plus 10 globals.

Wire model: WS2812 from an RP2040 PIO, bit period exactly 1250 ns,
'1' = eff_high_1 ns high, '0' = eff_high_0 ns high (nominal 750/375, the
corrections absorb the STM8 input threshold / edge-rate skew).
"""

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RECON = HERE.parent.parent
BIT_NS = 1250.0
NOM_H1 = 750.0
NOM_H0 = 375.0
NBITS_FRAME = 192

# nominal gaps from cap_code.s (cycles), *when the NOP executes*
DOC_GAPS_CY = [4, 4, 4, 4, 4, 6, 5, 6]
CY = 62.5


def load():
    import sys
    sys.path.insert(0, str(RECON))
    import harness
    meta, caps = harness.load_dataset()
    out = []
    for c in caps:
        samples = harness.linearize(c["capture"])
        lv = np.array([v for _, _, v in samples], dtype=np.int8)
        it = np.array([i for i, _, _ in samples], dtype=np.int32)
        sl = np.array([s for _, s, _ in samples], dtype=np.int32)
        frame = bytes.fromhex(c["frame"])
        bits = np.array([(b >> (7 - j)) & 1 for b in frame for j in range(8)],
                        dtype=np.int8)
        out.append(dict(pattern=c["pattern"], rep=c["rep"], key=f"{c['pattern']}_{c['rep']}",
                        it=it, sl=sl, lv=lv, bits=bits, n=len(samples)))
    return meta, out


def prep(cap, g, d):
    """Precompute A = i*G + P[s] - d*N(i,s) for one capture."""
    g = np.asarray(g, dtype=float)
    G = g.sum()
    P = np.concatenate([[0.0], np.cumsum(g)[:-1]])
    # N(i,s) = number of highs strictly before this sample (chronological)
    N = np.concatenate([[0], np.cumsum(cap["lv"].astype(np.int64))[:-1]])
    return cap["it"] * G + P[cap["sl"]] - d * N


def wire_levels(t, bits, h1, h0):
    """True line level at times t (ns) for the given frame bit sequence."""
    idx = np.floor(t / BIT_NS).astype(np.int64)
    inside = (idx >= 0) & (idx < len(bits))
    j = np.clip(idx, 0, len(bits) - 1)
    hw = np.where(bits[j] == 1, h1, h0)
    return (inside & ((t - j * BIT_NS) < hw)).astype(np.int8)


def agree(A, cap, t0, k, h1, h0):
    t = t0 + k * A
    return int(np.count_nonzero(wire_levels(t, cap["bits"], h1, h0) == cap["lv"]))


def fit_capture(A, cap, h1, h0, k0=1.0, t0_rng=(-150.0, 450.0), k_rng=(0.990, 1.012)):
    """Grid + pattern-search for (t0, k) maximising sample agreement."""
    best = (-1, 0.0, 1.0)
    ks = np.arange(k_rng[0], k_rng[1], 2e-5)
    t0s = np.arange(t0_rng[0], t0_rng[1], 10.0)
    bits, lv = cap["bits"], cap["lv"]
    for k in ks:
        base = k * A
        for t0 in t0s:
            t = t0 + base
            m = int(np.count_nonzero(wire_levels(t, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, t0, k)
    # local pattern search
    m, t0, k = best
    st, sk = 5.0, 1e-5
    while st > 1e-3 or sk > 1e-9:
        improved = False
        for dt, dk in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = agree(A, cap, t0 + dt, k + dk, h1, h0)
            if mm > m:
                m, t0, k = mm, t0 + dt, k + dk
                improved = True
                break
        if not improved:
            st /= 2.0
            sk /= 2.0
    return m, t0, k


def total_agreement(caps, g, d, h1, h0, nuis=None, refit=True):
    tot = 0
    n = 0
    out = {}
    for cap in caps:
        A = prep(cap, g, d)
        if refit or nuis is None or cap["key"] not in nuis:
            m, t0, k = fit_capture(A, cap, h1, h0)
        else:
            t0, k = nuis[cap["key"]]
            m, t0, k = _polish(A, cap, h1, h0, t0, k)
        out[cap["key"]] = (t0, k, m, cap["n"])
        tot += m
        n += cap["n"]
    return tot / n, out


def _polish(A, cap, h1, h0, t0, k, st=8.0, sk=2e-5):
    m = agree(A, cap, t0, k, h1, h0)
    while st > 1e-3 or sk > 1e-9:
        improved = False
        for dt, dk in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = agree(A, cap, t0 + dt, k + dk, h1, h0)
            if mm > m:
                m, t0, k = mm, t0 + dt, k + dk
                improved = True
                break
        if not improved:
            st /= 2.0
            sk /= 2.0
    return m, t0, k
