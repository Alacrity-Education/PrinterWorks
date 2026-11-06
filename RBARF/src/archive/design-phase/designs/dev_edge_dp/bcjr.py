"""Forward-backward (BCJR) over the edge_dp trellis -> per-bit posteriors.

Same state space as dp2.viterbi ((d, v) phase/slope lattice), but the
min-sum recursion is replaced by log-sum-exp, so the output is the exact
posterior log-odds of each payload bit under the model, marginalised over
the phase track and over the (kappa) hypotheses in the grid.
"""
import numpy as np

import dp2

NB = dp2.NB
BIG = 1e12


def _lse(a, axis=0):
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return np.squeeze(m, axis=axis) + np.log(np.sum(np.exp(a - m), axis=axis))


def _trans(L, vsteps, vpen, forward=True):
    """One transition step on log-weights L[(nd, nv)] -> same shape."""
    nd, nv = L.shape
    out = np.full((nd, nv), -np.inf)
    stack = []
    for vi in range(nv):
        sh = vsteps[vi] if forward else -vsteps[vi]
        for dv in (-1, 0, 1):
            vs = vi + dv if forward else vi - dv
            if not (0 <= vs < nv):
                continue
            src = L[:, vs] if forward else L[:, vs]
            dst = np.full(nd, -np.inf)
            if sh >= 0:
                if sh < nd:
                    dst[sh:] = src[:nd - sh]
            else:
                if -sh < nd:
                    dst[:nd + sh] = src[-sh:]
            col = np.full((nd, nv), -np.inf)
            col[:, vi] = dst - (vpen if dv else 0.0)
            stack.append(col)
    return _lse(np.stack(stack, 0), axis=0)


def posteriors(E, dgrid, vgrid, vpen, dpen0, prior=None, temp=1.0):
    """Returns llr[192] = log P(bit=1) - log P(bit=0), and total logZ."""
    nd, nv = len(dgrid), len(vgrid)
    dstep = dgrid[1] - dgrid[0]
    vsteps = np.rint(vgrid / dstep).astype(int)
    lg = np.zeros((NB, 2, nd))
    for j in range(NB):
        if j < 32:
            b = int(dp2.HDR_BITS[j])
            lg[j, b] = -E[b, j] / temp
            lg[j, 1 - b] = -BIG
        elif j >= 160:
            b = int(dp2.TRL_BITS[j - 160])
            lg[j, b] = -E[b, j] / temp
            lg[j, 1 - b] = -BIG
        else:
            lg[j, 0] = -E[0, j] / temp
            lg[j, 1] = -E[1, j] / temp
            if prior is not None:
                lg[j, 0] -= prior[j, 0]
                lg[j, 1] -= prior[j, 1]
    lgm = _lse(lg, axis=1)                       # (NB, nd) bit-marginal emission

    # forward
    F = np.zeros((NB + 1, nd, nv))
    F[0] = (-dpen0(dgrid) / temp)[:, None] - np.log(nv)
    for j in range(NB):
        F[j + 1] = _trans(F[j], vsteps, vpen, True) + lgm[j][:, None]
    # backward
    B = np.zeros((NB + 1, nd, nv))
    B[NB] = 0.0
    for j in range(NB - 1, -1, -1):
        B[j] = _trans(B[j + 1] + lgm[j][:, None], vsteps, vpen, False)
    logZ = _lse(_lse(F[NB], 0), 0)

    llr = np.zeros(NB)
    for j in range(NB):
        # occupancy of the phase state at the START of bit j
        occ = _lse((_trans(F[j], vsteps, vpen, True) + B[j + 1]).reshape(-1))
        w = _trans(F[j], vsteps, vpen, True) + B[j + 1]      # (nd, nv)
        wd = _lse(w, axis=1)                                  # (nd,)
        a1 = _lse(wd + lg[j, 1] - lgm[j])
        a0 = _lse(wd + lg[j, 0] - lgm[j])
        llr[j] = a1 - a0
    return llr, float(logZ)


def run_capture_soft(c, A=None, prior=None, **kw):
    """Marginalise over the kappa grid too: returns llr[192], best kappa."""
    p = dict(dp2.DEF); p.update(kw)
    if A is None:
        A = dp2.A_of(c)
    lv = c["lv"]
    k0, a0, a1 = dp2.blind_kappa(A, lv)
    dgrid = np.arange(p["dlo"], p["dhi"] + 1e-9, p["dstep"])
    vgrid = np.arange(-p["vmax"], p["vmax"] + 1e-9, p["vstep"])
    d0 = -k0 * a0
    accZ = []
    accL = []
    for dk in p["kgrid"]:
        kap = k0 * (1.0 + dk)
        E = dp2.emissions(A, lv, kap, dgrid, p["we"], p["floor"],
                          hoff=p["hoff"], sr=p["sr"], dr=p["dr"],
                          slots=c["sl"], wes=p["wes"])
        pen = lambda d, d0=d0, s=p["d0sig"]: 0.5 * ((d - d0) / s) ** 2
        llr, lz = posteriors(E, dgrid, vgrid, p["vpen"], pen, prior)
        accZ.append(lz)
        accL.append(llr)
    accZ = np.array(accZ)
    wgt = np.exp(accZ - accZ.max())
    wgt /= wgt.sum()
    L = np.stack(accL, 0)
    # mix posteriors across kappa hypotheses in probability domain
    p1 = (wgt[:, None] * (1.0 / (1.0 + np.exp(-L)))).sum(0)
    p1 = np.clip(p1, 1e-12, 1 - 1e-12)
    return np.log(p1 / (1 - p1)), float(accZ.max())
