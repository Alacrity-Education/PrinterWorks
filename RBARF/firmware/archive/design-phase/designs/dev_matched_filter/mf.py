"""Matched-filter core: vectorised (t0, kappa) correlation on the fine grid."""
import numpy as np

from common import BIT_NS

# fine-grid sample-phase model, in CPU cycles
G_CY = 40.0
P_CY = np.array([0., 4., 8., 12., 16., 20., 26., 31.])


def phase(it, sl, G=G_CY, P=P_CY):
    """u[n] : receiver phase of each sample, in nominal CPU cycles."""
    return it.astype(float) * G + P[sl]


def wire_from_bits(t, bits, h1, h0, t_end=None):
    idx = np.floor(t / BIT_NS).astype(np.int64)
    inside = (idx >= 0) & (idx < len(bits))
    j = np.clip(idx, 0, len(bits) - 1)
    hw = np.where(bits[j] == 1, h1, h0)
    return (inside & ((t - j * BIT_NS) < hw))


def corr_grid(u, lv, bits, t0s, ks, h1, h0, mask=None):
    """agreement[len(t0s), len(ks)] for template `bits` starting at wire t=0."""
    if mask is None:
        mask = np.ones(len(u), bool)
    uu = u[mask]
    ll = lv[mask].astype(bool)
    out = np.empty((len(t0s), len(ks)))
    for a, k in enumerate(ks):
        base = k * uu
        T = t0s[:, None] + base[None, :]
        pred = wire_from_bits(T, bits, h1, h0)
        out[:, a] = (pred == ll[None, :]).sum(1)
    return out


def refine(u, lv, bits, t0, k, h1, h0, mask=None, st=4.0, sk=0.02):
    if mask is None:
        mask = np.ones(len(u), bool)
    uu, ll = u[mask], lv[mask].astype(bool)

    def sc(t0, k):
        return int(np.count_nonzero(
            wire_from_bits(t0 + k * uu, bits, h1, h0) == ll))
    m = sc(t0, k)
    while st > 1e-3:
        found = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = sc(t0 + a, k + b)
            if mm > m:
                m, found = mm, (t0 + a, k + b)
        if found is None:
            st /= 2
            sk /= 2
        else:
            t0, k = found
    return m, t0, k
