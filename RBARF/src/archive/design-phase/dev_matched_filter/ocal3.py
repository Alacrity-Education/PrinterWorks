"""Supervised physical calibration of SLOT_O + T0H + T1H (coordinate descent).

Objective: total matched-filter cost of the true waveform over the train
captures, minimised over the phase track.  Purely a model-fidelity measure.
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
SOFT = mf.EDGE_SOFT


class Cap:
    def __init__(self, c):
        s = linearize(c['capture'])
        lv, _ = mf._grid(s)
        self.nl = min(len(lv), (NB + 1) // 2 + 1 + mf.TAIL_LOOPS)
        self.V = np.array([lv[i] for i in range(self.nl)], dtype=np.int8)
        self.bits = np.array([int(b) for byte in bytes.fromhex(c['frame'])
                              for b in f"{byte:08b}"] + [-1] * 40)
        self.P = 2500.0
        self.name = c['pattern'] + ' r' + str(c['rep'])


def cost_for(cap, O, t0, t1, P, PSI, J):
    W = np.where(cap.bits < 0, -1.0, np.where(cap.bits > 0, t1, t0))
    i = np.arange(cap.nl, dtype=np.float64)
    t = (P * i)[:, None, None] + PSI[None, :, None] + np.asarray(O)[None, None, :]
    kf = np.floor(t * (1.0 / BIT))
    k = np.clip(kf.astype(np.int64), 0, NB + 39)
    u = t - kf * BIT
    Wk = W[k]
    pred = (Wk >= 0) & (u < Wk)
    bad = pred != (cap.V[:, None, :] != 0)
    disc = np.where(pred, np.minimum(u, Wk - u),
                    np.where(Wk >= 0, np.minimum(np.abs(u - Wk), BIT - u), SOFT))
    E = (bad * np.minimum(1.0, disc / SOFT)).sum(axis=2)
    D = E[0]
    for x in range(1, cap.nl):
        D = np.min(D[None, :] + J, axis=1) + E[x]
    return float(D.min())


def total(caps, O, t0, t1, PSI, J):
    return sum(min(cost_for(c, O, t0, t1, P, PSI, J)
                   for P in (c.P - 2.0, c.P - 1.0, c.P, c.P + 1.0, c.P + 2.0))
               for c in caps)


if __name__ == '__main__':
    caps = [Cap(c) for c in allc if c['rep'] in (0, 1)]
    PSI = np.arange(mf.PSI_LO, mf.PSI_HI + 1e-9, mf.PSI_STEP)
    J = mf.JIT_LAM * np.maximum(0.0, np.abs(PSI[:, None] - PSI[None, :])
                                - mf.JIT_DEAD)
    O = json.loads(sys.argv[1]) if len(sys.argv) > 1 else list(mf.SLOT_O)
    t0 = float(sys.argv[2]) if len(sys.argv) > 2 else mf.T0H
    t1 = float(sys.argv[3]) if len(sys.argv) > 3 else mf.T1H
    for c in caps:
        c.P = min(np.arange(2486, 2526.1, 2.0),
                  key=lambda P: cost_for(c, O, t0, t1, P, PSI, J))
    cur = total(caps, O, t0, t1, PSI, J)
    print(f"start {cur:.3f}", flush=True)
    step = 8.0
    while step >= 0.5:
        improved = False
        for idx in range(10):
            for d in (-step, step):
                O2, a, b = list(O), t0, t1
                if idx < 8:
                    O2[idx] += d
                elif idx == 8:
                    a += d
                else:
                    b += d
                v = total(caps, O2, a, b, PSI, J)
                if v < cur - 1e-9:
                    cur, O, t0, t1 = v, O2, a, b
                    improved = True
        print(f"step={step:5.1f} cost={cur:.3f} T0={t0:.1f} T1={t1:.1f} "
              f"O={[round(x,1) for x in O]}", flush=True)
        if not improved:
            step /= 2.0
    print("FINAL", json.dumps([round(float(x), 2) for x in O]), t0, t1)
