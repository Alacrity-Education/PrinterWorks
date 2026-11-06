"""Physical calibration of SLOT_O by minimising the SUPERVISED model cost.

With every bit forced to its true value the trellis collapses to a plain
phase DP, so the total matched-filter cost is a direct measure of how well a
candidate slot-offset vector explains the captures -- independent of whether
the decoder happens to get bits right, so it cannot overfit decode luck.
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


class Cap:
    def __init__(self, c):
        s = linearize(c['capture'])
        lv, last = mf._grid(s)
        self.nl = min(len(lv), (NB + 1) // 2 + 1 + mf.TAIL_LOOPS)
        self.V = np.array([lv[i] for i in range(self.nl)], dtype=np.int8)
        bits = [int(b) for byte in bytes.fromhex(c['frame']) for b in f"{byte:08b}"]
        self.W = np.array([(mf.T1H if b else mf.T0H) for b in bits]
                          + [-1.0] * 40, dtype=np.float64)
        self.name = c['pattern'] + ' r' + str(c['rep'])
        self.P = 2500.0


def cost_for(cap, O, P, PSI, J):
    """min total matched-filter cost over phase tracks, truth forced."""
    nl = cap.nl
    Oa = np.asarray(O)
    i = np.arange(nl, dtype=np.float64)
    # t[i, p, s]
    t = (P * i)[:, None, None] + PSI[None, :, None] + Oa[None, None, :]
    k = np.floor(t * (1.0 / BIT)).astype(np.int64)
    k = np.clip(k, 0, NB + 39)
    u = t - np.floor(t * (1.0 / BIT)) * BIT
    W = cap.W[k]
    pred = (W >= 0) & (u < W)
    bad = pred != (cap.V[:, None, :] != 0)
    if mf.EDGE_SOFT > 0:
        disc = np.where(pred, np.minimum(u, W - u),
                        np.where(W >= 0, np.minimum(np.abs(u - W), BIT - u),
                                 mf.EDGE_SOFT))
        E = (bad * np.minimum(1.0, disc / mf.EDGE_SOFT)).sum(axis=2)
    else:
        E = bad.sum(axis=2).astype(np.float64)
    D = E[0]
    for x in range(1, nl):
        D = np.min(D[None, :] + J, axis=1) + E[x]
    return float(D.min())


def total(caps, O, PSI, J, Pset):
    s = 0.0
    for c in caps:
        s += min(cost_for(c, O, P, PSI, J) for P in Pset(c))
    return s


if __name__ == '__main__':
    caps = [Cap(c) for c in allc if c['rep'] in (0, 1)]
    PSI = np.arange(mf.PSI_LO, mf.PSI_HI + 1e-9, mf.PSI_STEP)
    J = mf.JIT_LAM * np.maximum(0.0, np.abs(PSI[:, None] - PSI[None, :])
                                - mf.JIT_DEAD)
    O = list(json.loads(sys.argv[1])) if len(sys.argv) > 1 else list(mf.SLOT_O)
    # per-capture best P on a coarse grid, once
    coarse = np.arange(2488, 2524.1, 2.0)
    for c in caps:
        c.P = min(coarse, key=lambda P: cost_for(c, O, P, PSI, J))
    def Pset(c):
        return (c.P - 2.0, c.P - 1.0, c.P, c.P + 1.0, c.P + 2.0)
    cur = total(caps, O, PSI, J, Pset)
    print(f"start {cur:.3f} O={[round(x,1) for x in O]}", flush=True)
    step = 16.0
    while step >= 1.0:
        improved = False
        for s in range(8):
            for d in (-step, step):
                O2 = list(O); O2[s] += d
                v = total(caps, O2, PSI, J, Pset)
                if v < cur - 1e-9:
                    cur, O = v, O2
                    improved = True
        print(f"step={step:5.1f} cost={cur:.3f} O={[round(x,1) for x in O]}", flush=True)
        if not improved:
            step /= 2.0
    print("FINAL", json.dumps([round(float(x), 2) for x in O]))
