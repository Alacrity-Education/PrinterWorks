"""boundary_model exploration: data layer + sampling-grid model."""
import sys
from pathlib import Path

import numpy as np

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON))
import harness  # noqa: E402

BIT_NS = 1250.0
H1_NOM = 750.0
H0_NOM = 375.0
NBITS = 192


def load():
    meta, caps = harness.load_dataset()
    out = []
    for c in caps:
        s = harness.linearize(c["capture"])
        it = np.array([a for a, _, _ in s], dtype=np.int64)
        sl = np.array([b for _, b, _ in s], dtype=np.int64)
        lv = np.array([v for _, _, v in s], dtype=np.int8)
        fr = bytes.fromhex(c["frame"])
        bits = np.array([(b >> (7 - j)) & 1 for b in fr for j in range(8)],
                        dtype=np.int8)
        # frame region: up to the final long low run
        last_hi = int(np.max(np.nonzero(lv)[0]))
        out.append(dict(pattern=c["pattern"], rep=c["rep"],
                        key=f"{c['pattern']}_{c['rep']}",
                        it=it, sl=sl, lv=lv, bits=bits, last_hi=last_hi,
                        payload=bytes.fromhex(c["payload"])))
    return meta, out


def wire_level(t, bits, h1, h0):
    j = np.floor(t / BIT_NS).astype(np.int64)
    ok = (j >= 0) & (j < len(bits))
    jc = np.clip(j, 0, len(bits) - 1)
    hw = np.where(bits[jc] == 1, h1, h0)
    return (ok & ((t - jc * BIT_NS) < hw)).astype(np.int8)


def times(c, T0, G, O, d=0.0):
    """t(i,s) = T0 + G*i + O[s] - d*N(i,s); N = #highs strictly before."""
    A = c["it"] * G + np.asarray(O, float)[c["sl"]]
    if d:
        N = np.concatenate([[0], np.cumsum(c["lv"].astype(np.int64))[:-1]])
        A = A - d * N
    return T0 + A


def window(c, n_extra=16):
    """Index range of samples covering the frame + a little margin."""
    return slice(0, min(len(c["lv"]), c["last_hi"] + 1 + n_extra))
