"""Shared model helpers for boundary_model exploration."""
import sys, json
from pathlib import Path
import numpy as np

REC = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(REC))
from harness import load_dataset, linearize  # noqa: E402

BIT = 1250.0
T1H = 700.0
T0H = 350.0
HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")


def frame_bits(payload_hex):
    fr = HEADER + bytes.fromhex(payload_hex) + TRAILER
    return [int(b) for byte in fr for b in f"{byte:08b}"]


def edges_ns(bits):
    """Strictly increasing alternating edge times (rise, fall, rise, ...)."""
    E = []
    for k, b in enumerate(bits):
        E.append(k * BIT)
        E.append(k * BIT + (T1H if b else T0H))
    return np.array(E, dtype=float)


class Cap:
    def __init__(self, c):
        self.pattern = c["pattern"]
        self.rep = c["rep"]
        self.name = f"{c['pattern']}_{c['rep']}"
        s = linearize(c["capture"])
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s], dtype=np.int64)
        self.lev = np.array([x[2] for x in s], dtype=np.int64)
        self.bits = frame_bits(c["payload"])
        self.E = edges_ns(self.bits)
        self.tend = self.E[-1]


def load_caps():
    meta, caps = load_dataset()
    return meta, [Cap(c) for c in caps]


def sample_times(cap, phi, P, u):
    return phi + P * (cap.it + u[cap.sl])


def violation(cap, t, tmax_guard=True, lev=None):
    """Per-sample (mismatch, distance-to-consistency) against known waveform.

    Samples past the end of the frame are all low and carry no info about
    slot geometry, so they are excluded (mask returned)."""
    E = cap.E
    idx = np.searchsorted(E, t, side="right")
    pred = idx & 1
    mism = pred != (cap.lev if lev is None else lev)
    dprev = np.where(idx > 0, t - E[np.clip(idx - 1, 0, len(E) - 1)], np.inf)
    dnext = np.where(idx < len(E), E[np.clip(idx, 0, len(E) - 1)] - t, np.inf)
    d = np.minimum(dprev, dnext)
    d = np.where(mism, d, 0.0)
    mask = (t > -400.0) & (t < cap.tend + 400.0) if tmax_guard else np.ones_like(t, bool)
    return mism & mask, d * mask


def observed_transitions(cap, u):
    """Receiver-coordinate x (loop units) midway across each level change."""
    x = cap.it + u[cap.sl]
    ch = np.nonzero(np.diff(cap.lev) != 0)[0]
    return 0.5 * (x[ch] + x[ch + 1]), ch


def icp_fit(cap, u, phi0=250.0, P0=2507.3, iters=25, tol=350.0):
    """Iterative-closest-edge alignment of observed transitions to true edges."""
    xm, _ = observed_transitions(cap, u)
    phi, P = phi0, P0
    for _ in range(iters):
        t = phi + P * xm
        j = np.clip(np.searchsorted(cap.E, t), 1, len(cap.E) - 1)
        e = np.where(t - cap.E[j - 1] < cap.E[j] - t, cap.E[j - 1], cap.E[j])
        r = np.abs(t - e)
        k = r < tol
        if k.sum() < 20:
            break
        A = np.stack([np.ones(k.sum()), xm[k]], 1)
        sol, *_ = np.linalg.lstsq(A, e[k], rcond=None)
        nphi, nP = sol
        if abs(nphi - phi) < 1e-6 and abs(nP - P) < 1e-9:
            phi, P = nphi, nP
            break
        phi, P = nphi, nP
    return float(phi), float(P)


def fit_cap(cap, u, P0=2507.3):
    """ICP init (multi-start) then pattern search on the violation loss."""
    best = None
    for phi0 in (0.0, 150.0, 300.0, 450.0, 600.0):
        for p0 in (2495.0, 2507.3, 2520.0):
            phi, P = icp_fit(cap, u, phi0, p0)
            _, d = violation(cap, sample_times(cap, phi, P, u))
            v = d.sum()
            if best is None or v < best[0]:
                best = (v, phi, P)
    v, phi, P = best
    stepP, stepphi = 1.0, 16.0
    while stepP > 1e-4 or stepphi > 1e-3:
        improved = False
        for dP, dphi in ((stepP, 0), (-stepP, 0), (0, stepphi), (0, -stepphi)):
            _, d = violation(cap, sample_times(cap, phi + dphi, P + dP, u))
            vv = d.sum()
            if vv < v - 1e-9:
                v, phi, P = vv, phi + dphi, P + dP
                improved = True
                break
        if not improved:
            stepP *= 0.5
            stepphi *= 0.5
    return phi, P, v


def eval_all(caps, u, fits):
    tot_v, tot_m, tot_n = 0.0, 0, 0
    for cap in caps:
        phi, P = fits[cap.name]
        m, d = violation(cap, sample_times(cap, phi, P, u))
        tot_v += d.sum()
        tot_m += int(m.sum())
        tot_n += int(len(m))
    return tot_v, tot_m, tot_n
