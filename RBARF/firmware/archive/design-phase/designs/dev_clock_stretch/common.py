"""Shared helpers for clock_stretch exploration (analysis only)."""
import sys, json
from pathlib import Path
import numpy as np

REC = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(REC))
sys.path.insert(0, str(REC.parent / "bench"))

from harness import load_dataset, linearize          # noqa: E402
from patterns import frame                            # noqa: E402

BIT_NS = 1250.0
T0H = 350.0
T1H = 700.0
LOOP_CY = 40
P_CY = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)   # documented slot cycles


def cycles_of(samples):
    """cycle index of each sample under the LOOP_CY/P_CY model."""
    return np.array([LOOP_CY * i + P_CY[s] for i, s, _ in samples])


def levels_of(samples):
    return np.array([v for _, _, v in samples], dtype=np.int8)


def slots_of(samples):
    return np.array([s for _, s, _ in samples], dtype=np.int8)


def iters_of(samples):
    return np.array([i for i, _, _ in samples], dtype=np.int32)


def frame_bits(payload_hex):
    fr = frame(bytes.fromhex(payload_hex))
    return np.array([int(b) for byte in fr for b in f"{byte:08b}"], dtype=np.int8)


def wave(bits, t):
    """level of the ideal waveform at absolute ns t (array)."""
    t = np.asarray(t, float)
    k = np.floor(t / BIT_NS).astype(np.int64)
    ok = (k >= 0) & (k < len(bits))
    kc = np.clip(k, 0, len(bits) - 1)
    within = t - k * BIT_NS
    hi = np.where(bits[kc] == 1, T1H, T0H)
    return np.where(ok & (within < hi) & (t >= 0), 1, 0).astype(np.int8)


def true_edges(bits):
    """(rising_times, falling_times) of the ideal waveform, ns."""
    r, f = [], []
    for k, b in enumerate(bits):
        r.append(k * BIT_NS)
        f.append(k * BIT_NS + (T1H if b else T0H))
    return np.array(r), np.array(f)


def transitions(levels):
    """indices n where levels[n] != levels[n+1]; returns (n, kind) kind=+1 rise."""
    d = np.diff(levels.astype(int))
    idx = np.nonzero(d)[0]
    return idx, d[idx]


def load_all():
    meta, caps = load_dataset()
    out = []
    for c in caps:
        s = linearize(c["capture"])
        out.append(dict(pattern=c["pattern"], rep=c["rep"], payload=c["payload"],
                        samples=s, cyc=cycles_of(s), lev=levels_of(s),
                        slot=slots_of(s), it=iters_of(s),
                        bits=frame_bits(c["payload"])))
    return meta, out
