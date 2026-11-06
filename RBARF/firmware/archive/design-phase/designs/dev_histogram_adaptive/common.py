"""Shared exploration utilities (analysis only; reads ground truth)."""
import sys, json
from pathlib import Path
R = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(R))
from harness import load_dataset, linearize  # noqa

BIT = 1250.0
T0H = 350.0
T1H = 700.0
HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")


def frame_bits(payload_hex):
    fr = HDR + bytes.fromhex(payload_hex) + TRL
    return [(b >> (7 - k)) & 1 for b in fr for k in range(8)]


def level_at(bits, t):
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    w = t - k * BIT
    return 1 if w < (T1H if bits[k] else T0H) else 0


def runs_of(samples):
    """[(level, start_idx, end_idx_inclusive, n)] over the sample list."""
    out = []
    cur = samples[0][2]
    st = 0
    for j in range(1, len(samples)):
        if samples[j][2] != cur:
            out.append((cur, st, j - 1, j - st))
            cur = samples[j][2]
            st = j
    out.append((cur, st, len(samples) - 1, len(samples) - st))
    return out


def fit_timebase(samples, bits, f0=None, n_l=241, n_t=241):
    """Grid-fit (t0, L) with fixed fractional slot offsets f (loop units).

    Returns (t0, L, f, mismatches).
    """
    if f0 is None:
        f0 = [p / 40.0 for p in (1, 5, 9, 13, 17, 21, 27, 32)]
    f = list(f0)
    best = None
    for li in range(n_l):
        L = 2470.0 + li * (70.0 / (n_l - 1))
        for ti in range(n_t):
            t0 = -300.0 + ti * (600.0 / (n_t - 1))
            m = 0
            for (i, s, v) in samples:
                if level_at(bits, t0 + (i + f[s]) * L) != v:
                    m += 1
            if best is None or m < best[3]:
                best = (t0, L, list(f), m)
        # coarse->fine handled by caller
    return best


def mismatch(samples, bits, t0, L, f):
    return sum(1 for (i, s, v) in samples
               if level_at(bits, t0 + (i + f[s]) * L) != v)


def refine(samples, bits, t0, L, f, rounds=6):
    """Coordinate descent over t0, L, and per-slot offsets f."""
    f = list(f)
    m = mismatch(samples, bits, t0, L, f)
    for r in range(rounds):
        stepL = 4.0 / (2 ** r)
        stepT = 30.0 / (2 ** r)
        stepF = (30.0 / (2 ** r)) / L
        improved = True
        while improved:
            improved = False
            for dL in (-stepL, stepL):
                mm = mismatch(samples, bits, t0, L + dL, f)
                if mm < m:
                    m, L = mm, L + dL
                    improved = True
            for dT in (-stepT, stepT):
                mm = mismatch(samples, bits, t0 + dT, L, f)
                if mm < m:
                    m, t0 = mm, t0 + dT
                    improved = True
            for s in range(8):
                for df in (-stepF, stepF):
                    g = list(f)
                    g[s] += df
                    mm = mismatch(samples, bits, t0, L, g)
                    if mm < m:
                        m, f = mm, g
                        improved = True
    return t0, L, f, m


def align_capture(c, f0=None):
    samples = linearize(c["capture"])
    bits = frame_bits(c["payload"])
    t0, L, f, m = fit_timebase(samples, bits, f0=f0, n_l=61, n_t=61)
    t0, L, f, m = refine(samples, bits, t0, L, f)
    return samples, bits, t0, L, f, m
