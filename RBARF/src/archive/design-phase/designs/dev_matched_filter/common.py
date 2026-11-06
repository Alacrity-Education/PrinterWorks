"""Shared loading + mechanistic time-base model for matched_filter design work."""
import sys
from pathlib import Path

import numpy as np

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON))
sys.path.insert(0, str(RECON / "bench"))

import harness  # noqa: E402

BIT_NS = 1250.0
NBITS = 192
HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")


def bits_of(bs):
    return np.array([(b >> (7 - j)) & 1 for b in bs for j in range(8)], dtype=np.int8)


def load(all_caps=True):
    meta, caps = harness.load_dataset()
    out = []
    for c in caps:
        s = harness.linearize(c["capture"])
        it = np.array([a for a, _, _ in s], dtype=np.int32)
        sl = np.array([b for _, b, _ in s], dtype=np.int32)
        lv = np.array([v for _, _, v in s], dtype=np.int8)
        out.append(dict(pattern=c["pattern"], rep=c["rep"],
                        key=f"{c['pattern']}_{c['rep']}",
                        it=it, sl=sl, lv=lv,
                        payload=bytes.fromhex(c["payload"]),
                        frame=bytes.fromhex(c["frame"]),
                        bits=bits_of(bytes.fromhex(c["frame"])),
                        n=len(s)))
    return meta, out


def cycles(sl, lv, g):
    """u[n] = cumulative CPU cycles at sample n.

    Gap from sample with slot s to the next sample is g[s] cycles, minus 1
    cycle when that sample READ HIGH (BTJT branches, NOP skipped).
    u[0] = 0 by convention (t0 absorbs the pre-roll).
    """
    g = np.asarray(g, float)
    step = g[sl] - lv          # cycles from sample n to sample n+1
    u = np.empty(len(sl))
    u[0] = 0.0
    np.cumsum(step[:-1], out=u[1:])
    return u


def wire(t, bits, h1, h0):
    idx = np.floor(t / BIT_NS).astype(np.int64)
    inside = (idx >= 0) & (idx < len(bits))
    j = np.clip(idx, 0, len(bits) - 1)
    hw = np.where(bits[j] == 1, h1, h0)
    return (inside & ((t - j * BIT_NS) < hw)).astype(np.int8)


def agree(u, lv, bits, t0, kap, h1, h0):
    return int(np.count_nonzero(wire(t0 + kap * u, bits, h1, h0) == lv))


def fit_t0k(u, lv, bits, h1, h0, t0_rng=(-400, 500), k_rng=(57.0, 70.0),
            dk=0.01, dt=8.0):
    best = (-1, 0.0, 62.5)
    ks = np.arange(k_rng[0], k_rng[1], dk)
    t0s = np.arange(t0_rng[0], t0_rng[1], dt)
    for k in ks:
        base = k * u
        for t0 in t0s:
            m = int(np.count_nonzero(wire(t0 + base, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, t0, k)
    m, t0, k = best
    st, sk = dt, dk
    while st > 1e-3:
        found = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = agree(u, lv, bits, t0 + a, k + b, h1, h0)
            if mm > m:
                m, found = mm, (t0 + a, k + b)
        if found is None:
            st /= 2
            sk /= 2
        else:
            t0, k = found
    return m, t0, k
