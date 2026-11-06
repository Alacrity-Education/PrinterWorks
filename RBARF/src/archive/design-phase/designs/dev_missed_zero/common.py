"""Shared exploration utilities for the missed_zero design study.

Builds a per-capture time base (scale + phase) fitted against ground truth
(analysis only), then exposes visible-pulse / gap structures.
"""
import sys, json, math
from pathlib import Path

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON))
from harness import load_dataset, linearize  # noqa: E402

BIT = 1250.0
T0H = 350.0
T1H = 700.0
HEADER = bytes([0xFF, 0x00, 0xAA, 0x65])
TRAILER = bytes([0x9A, 0x55, 0x00, 0xFF])

# Nominal (16 MHz-exact) inter-slot gaps in ns; 3 undocumented cycles put
# into the slot7->slot0 end-of-loop gap.  Sum = 2500 ns = 40 cycles.
GAPS_CY = [4, 4, 4, 4, 4, 6, 5, 9]
CY = 62.5
LOOP_NOM = sum(GAPS_CY) * CY            # 2500.0
SLOT_OFF = [0.0]
for g in GAPS_CY[:-1]:
    SLOT_OFF.append(SLOT_OFF[-1] + g * CY)
# SLOT_OFF = [0,250,500,750,1000,1250,1625,1937.5]


def bits_of(frame_bytes):
    return [(b >> (7 - k)) & 1 for b in frame_bytes for k in range(8)]


def wave_level(bits, t):
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    return 1 if (t - k * BIT) < (T1H if bits[k] else T0H) else 0


def sample_times(scale, t0):
    """(iteration, slot) -> ns, on the model time base."""
    return lambda i, s: t0 + scale * (i * LOOP_NOM + SLOT_OFF[s])


import numpy as np


def _wave_np(bits_np, t):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < len(bits_np))
    kc = np.clip(k, 0, len(bits_np) - 1)
    hi = np.where(bits_np[kc] == 1, T1H, T0H)
    return ((t - k * BIT) < hi) & ok


def fit_timebase(samples, bits, s_lo=0.998, s_hi=1.016):
    """Coarse->fine grid search on (scale, t0) maximizing sample agreement."""
    bits_np = np.array(bits, dtype=np.int8)
    pos = np.array([i * LOOP_NOM + SLOT_OFF[s] for i, s, _ in samples])
    lev = np.array([v for _, _, v in samples], dtype=bool)
    best = None
    for stage in range(4):
        if best is None:
            ss = np.linspace(s_lo, s_hi, 601)
            ts = np.arange(-400.0, 400.0, 10.0)
        else:
            f = 4.0 ** -stage
            ss = best[1] + np.linspace(-3e-4, 3e-4, 41) * f
            ts = best[2] + np.linspace(-40.0, 40.0, 41) * f
        cur = None
        for s in ss:
            T = t0mat = s * pos
            for t0 in ts:
                agree = int(np.count_nonzero(_wave_np(bits_np, T + t0) == lev))
                if cur is None or agree > cur[0]:
                    cur = (agree, float(s), float(t0))
        best = cur
    return best  # (agree, scale, t0)


def runs(samples, f):
    """Level runs as [(level, t_first, t_last, n_samples, idx_first, idx_last)]."""
    out = []
    cur = None
    for idx, (i, sl, v) in enumerate(samples):
        t = f(i, sl)
        if cur is None or cur[0] != v:
            if cur is not None:
                out.append(tuple(cur))
            cur = [v, t, t, 1, idx, idx]
        else:
            cur[2] = t
            cur[3] += 1
            cur[5] = idx
    if cur is not None:
        out.append(tuple(cur))
    return out


def load(pattern=None, rep=None):
    meta, caps = load_dataset()
    out = []
    for c in caps:
        if pattern and c["pattern"] != pattern:
            continue
        if rep is not None and c["rep"] != rep:
            continue
        out.append(c)
    return meta, out


def prepare(c):
    """-> dict with samples, bits, scale, t0, f, runs."""
    samples = linearize(c["capture"])
    fr = bytes.fromhex(c["frame"])
    bits = bits_of(fr)
    agree, scale, t0 = fit_timebase(samples, bits)
    f = sample_times(scale, t0)
    return dict(cap=c, samples=samples, bits=bits, frame=fr,
                agree=agree, n=len(samples), scale=scale, t0=t0,
                f=f, runs=runs(samples, f))
