"""Does a half-loop phase granularity explain the captures better?

Supervised (true bits forced) phase DP, comparing one phase per sampling
loop against one phase per half loop (slots 0-4 / slots 5-7).
"""
import sys, importlib.util, json
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

spec = importlib.util.spec_from_file_location('mf', R + '/approaches/matched_filter.py')
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
meta, allc = load_dataset()
BIT = mf.BIT
NB = mf.NBITS


def prep(c):
    s = linearize(c['capture'])
    lv, last = mf._grid(s)
    nl = min(len(lv), (NB + 1) // 2 + 1 + mf.TAIL_LOOPS)
    V = np.array([lv[i] for i in range(nl)], dtype=np.int8)
    bits = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
    W = np.array([(mf.T1H if b else mf.T0H) for b in bits] + [-1.0] * 40)
    return nl, V, W


def emis(nl, V, W, O, P, PSI, slots):
    Oa = np.asarray([O[s] for s in slots])
    i = np.arange(nl, dtype=np.float64)
    t = (P * i)[:, None, None] + PSI[None, :, None] + Oa[None, None, :]
    kf = np.floor(t * (1.0 / BIT))
    k = np.clip(kf.astype(np.int64), 0, NB + 39)
    u = t - kf * BIT
    Wk = W[k]
    pred = (Wk >= 0) & (u < Wk)
    bad = pred != (V[:, None, slots] != 0)
    if mf.EDGE_SOFT > 0:
        disc = np.where(pred, np.minimum(u, Wk - u),
                        np.where(Wk >= 0, np.minimum(np.abs(u - Wk), BIT - u),
                                 mf.EDGE_SOFT))
        return (bad * np.minimum(1.0, disc / mf.EDGE_SOFT)).sum(axis=2)
    return bad.sum(axis=2).astype(np.float64)


def run(nl, V, W, O, P, PSI, J, half):
    if not half:
        E = emis(nl, V, W, O, P, PSI, list(range(8)))
        D = E[0]
        for x in range(1, nl):
            D = np.min(D[None, :] + J, axis=1) + E[x]
        return float(D.min())
    EA = emis(nl, V, W, O, P, PSI, [0, 1, 2, 3, 4])
    EB = emis(nl, V, W, O, P, PSI, [5, 6, 7])
    D = EA[0]
    for x in range(nl):
        if x:
            D = np.min(D[None, :] + J, axis=1) + EA[x]
        D = np.min(D[None, :] + J, axis=1) + EB[x]
    return float(D.min())


if __name__ == '__main__':
    caps = [(c, prep(c)) for c in allc if c['rep'] in (0, 1)]
    PSI = np.arange(mf.PSI_LO, mf.PSI_HI + 1e-9, mf.PSI_STEP)
    O = list(mf.SLOT_O)
    for lam in (mf.JIT_LAM, mf.JIT_LAM * 2):
        J = lam * np.maximum(0.0, np.abs(PSI[:, None] - PSI[None, :]) - mf.JIT_DEAD)
        for half in (False, True):
            tot = 0.0
            for c, (nl, V, W) in caps:
                tot += min(run(nl, V, W, O, P, PSI, J, half)
                           for P in np.arange(2490, 2522.1, 2.0))
            print(f"lam={lam:.4f} half={half}  supervised cost {tot:.2f}", flush=True)
