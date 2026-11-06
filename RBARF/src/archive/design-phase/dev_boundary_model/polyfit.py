"""Can a smooth polynomial time base explain the samples (ground truth)?"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa

BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
GLO, GHI = -12000, 330000
MAXIT = 100


def prep(cap):
    s = [x for x in linearize(cap["capture"]) if x[0] <= MAXIT]
    it = np.array([x[0] for x in s], float)
    sl = np.array([x[1] for x in s])
    v = np.array([x[2] for x in s]) == 1
    bits = bm._bits(bytes.fromhex(cap["frame"]))
    hi = np.zeros(GHI - GLO, dtype=bool)
    for i, b in enumerate(bits):
        a = int(i * BIT) - GLO
        hi[a:a + int(T1H if b else T0H)] = True
    return it, sl, v, hi


def score(coef, it, sl, v, hi, F):
    u = it / 96.0
    S = np.zeros(len(it))
    for k, c in enumerate(coef):
        S = S + c * u ** k
    L = coef[1] / 96.0 if len(coef) > 1 else 2500.0
    T = S + L * np.array(F)[sl]
    I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(hi) - 1)
    return int((hi[I] != v).sum())


def optimize(deg, it, sl, v, hi, F, c0):
    coef = list(c0) + [0.0] * (deg + 1 - len(c0))
    best = score(coef, it, sl, v, hi, F)
    steps = [200.0, 60.0, 20.0, 6.0, 2.0, 0.5]
    for st in steps:
        improved = True
        while improved:
            improved = False
            for k in range(len(coef)):
                sk = st * (1.0 if k > 0 else 1.0)
                for d in (sk, -sk):
                    trial = list(coef)
                    trial[k] += d
                    sc = score(trial, it, sl, v, hi, F)
                    if sc < best:
                        best, coef = sc, trial
                        improved = True
    return best, coef


def main():
    meta, caps = load_dataset()
    F = bm.F
    for cap in caps:
        if cap["rep"] != 0:
            continue
        it, sl, v, hi = prep(cap)
        # seed from a good linear fit
        bestlin = None
        for L in np.arange(2470, 2545, 0.25):
            for B in np.arange(-300, 600, 25.0):
                sc = score([B, L * 96.0], it, sl, v, hi, F)
                if bestlin is None or sc < bestlin[0]:
                    bestlin = (sc, [B, L * 96.0])
        row = [f"{cap['pattern']:11s}"]
        c0 = bestlin[1]
        for deg in (1, 2, 3, 4, 6, 8):
            sc, c0d = optimize(deg, it, sl, v, hi, F, c0)
            row.append(f"d{deg}:{sc:4d}")
            if deg <= 3:
                c0 = c0d
        print("  ".join(row), f"  n={len(v)}", flush=True)


if __name__ == "__main__":
    main()
