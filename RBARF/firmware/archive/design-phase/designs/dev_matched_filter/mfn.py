"""Numpy matched-filter core."""
import sys
from pathlib import Path
import numpy as np
R = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(R))
from harness import load_dataset, linearize  # noqa

BIT = 1250.0
T1H = 700.0
T0H = 350.0
HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")
CY = 62.5
LOOP_CY = 40

# slot layouts, in cycles from loop start
LAY_DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)
LAY_END3 = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)
G3 = [250.0, 250.0, 250.0, 250.0, 250.0, 375.0, 312.5, 562.5]
_o = [0.0]
for g in G3[:-1]:
    _o.append(_o[-1] + g)
LAY_S3 = np.array(_o) / CY


def bits_of(payload: bytes) -> np.ndarray:
    fr = HEADER + payload + TRAILER
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], np.int8)


def tau_array(samples, lay=LAY_END3):
    it = np.array([s[0] for s in samples], float)
    sl = np.array([s[1] for s in samples], int)
    lv = np.array([s[2] for s in samples], np.int8)
    return (it * LOOP_CY + lay[sl]) * CY, lv, it, sl


def level_at(bits, t):
    """Vectorized transmitter level at times t (ns, frame start = 0)."""
    t = np.asarray(t, float)
    k = np.floor(t / BIT).astype(np.int64)
    inb = (k >= 0) & (k < len(bits))
    kk = np.clip(k, 0, len(bits) - 1)
    w = t - k * BIT
    h = np.where(bits[kk] == 1, T1H, T0H)
    return np.where(inb & (w < h) & (w >= 0), 1, 0).astype(np.int8)


def load():
    return load_dataset()


def caps_by(caps, pattern=None, rep=None):
    return [c for c in caps
            if (pattern is None or c["pattern"] == pattern)
            and (rep is None or c["rep"] == rep)]
