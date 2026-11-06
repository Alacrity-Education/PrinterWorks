"""Forward model + oracle fitting utilities for edge_dp exploration.

Sample time model:
    t(i,s) = phi + k * ( i*L_NOM + o[s] )
with L_NOM = 2500 ns (nominal 40 cycles @16 MHz), o[s] the intra-loop
slot offsets in nominal ns, k the receiver time-scale (>1 = slow clock).

Waveform: bit period 1250 ns, level high for T1H=750 (bit 1) or
T0H=375 (bit 0) ns from the bit boundary.  (The dataset brief quotes
700/350 for the WS2812 spec but the actual PIO generator on the bench
uses 750/500 and 375/875 -- see the task statement; both are checked.)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from harness import load_dataset, linearize  # noqa: E402

L_NOM = 2500.0
BIT = 1250.0
CY = 62.5

# documented cycle positions, plus the 3 undocumented cycles placed in
# the end-of-loop gap (this is synth.py's model)
DOC_CY = [1, 5, 9, 13, 17, 21, 27, 32]
O_NOM = [p * CY for p in DOC_CY]          # 62.5 .. 2000 ns

HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")


def frame_bits(payload: bytes):
    fr = HEADER + payload + TRAILER
    return [(byte >> (7 - j)) & 1 for byte in fr for j in range(8)]


def level_at(bits, t, t1h=750.0, t0h=375.0):
    if t < 0:
        return 0
    kk = int(t // BIT)
    if kk >= len(bits):
        return 0
    u = t - kk * BIT
    return 1 if u < (t1h if bits[kk] else t0h) else 0


def sample_times(o, k, phi, n_iter=640):
    """[(i,s)] -> flat list of times, chronological."""
    ts = []
    for i in range(n_iter):
        base = i * L_NOM
        for s in range(8):
            ts.append(phi + k * (base + o[s]))
    return ts


def predict(bits, o, k, phi, idx, t1h=750.0, t0h=375.0):
    """idx: list of (i,s). returns predicted levels."""
    return [level_at(bits, phi + k * (i * L_NOM + o[s]), t1h, t0h)
            for i, s in idx]


def fit_phi_k(bits, idx, obs, o=O_NOM, t1h=750.0, t0h=375.0,
              phis=None, ks=None):
    """Coarse-to-fine oracle fit of (phi, k) maximizing sample agreement."""
    if phis is None:
        phis = [x * 10.0 for x in range(-40, 41)]
    if ks is None:
        ks = [1.0 + 0.0005 * j for j in range(-20, 41)]
    best = (-1, None, None)
    for k in ks:
        for phi in phis:
            p = predict(bits, o, k, phi, idx, t1h, t0h)
            m = sum(1 for a, b in zip(p, obs) if a == b)
            if m > best[0]:
                best = (m, phi, k)
    # refine
    _, phi0, k0 = best
    for _ in range(3):
        phis = [phi0 + d for d in (-8, -4, -2, -1, 0, 1, 2, 4, 8)]
        ks = [k0 + d * 1e-5 for d in range(-20, 21)]
        for k in ks:
            for phi in phis:
                p = predict(bits, o, k, phi, idx, t1h, t0h)
                m = sum(1 for a, b in zip(p, obs) if a == b)
                if m > best[0]:
                    best = (m, phi, k)
        _, phi0, k0 = best
    return best  # (matches, phi, k)


def load():
    meta, caps = load_dataset()
    out = []
    for c in caps:
        s = linearize(c["capture"])
        idx = [(i, sl) for i, sl, _ in s]
        obs = [v for _, _, v in s]
        out.append(dict(pattern=c["pattern"], rep=c["rep"],
                        payload=bytes.fromhex(c["payload"]),
                        idx=idx, obs=obs,
                        bits=frame_bits(bytes.fromhex(c["payload"]))))
    return meta, out
