"""Stabilised version of fit5 with the HIGH-read corrections quantised to
whole CPU cycles, plus a coordinate search over that integer vector."""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels
import fit5
from fit5 import prepare, intra, NLOOP

fit5.HALF = 800.0
fit5.STEP = 1.0
CY = 62.5


def solve_T(caps, LO, HI, w, iters=30):
    """Per-capture (T0, Gc) least squares with w fixed."""
    T = {}
    for c in caps:
        lo, hi = LO[c["key"]], HI[c["key"]]
        base = c["C"] @ np.asarray(w, float)
        X = np.column_stack([np.ones(NLOOP), np.arange(NLOOP)])
        y = (lo + hi) / 2.0 - base
        for _ in range(iters):
            b, *_ = np.linalg.lstsq(X, y, rcond=None)
            y = np.clip(X @ b + base, lo, hi) - base
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        T[c["key"]] = (b[0] + b[1] * np.arange(NLOOP) + base, b[0], b[1])
    return T


def run(caps, w, o, h1, h0, rounds=3, verbose=False):
    Gc = {c["key"]: 2500.0 for c in caps}
    T = None
    for r in range(rounds):
        LO, HI = {}, {}
        for c in caps:
            lo, hi = fit5.windows(c, o, w, h1, h0, Gc[c["key"]])
            LO[c["key"]], HI[c["key"]] = lo, hi
        Tf = solve_T(caps, LO, HI, w)
        T = {k: v[0] for k, v in Tf.items()}
        for c in caps:
            Gc[c["key"]] = Tf[c["key"]][2]
        o, h1, h0 = fit5.profile(caps, T, o, w, h1, h0)
        m, n = fit5.count_all(caps, T, o, w, h1, h0)
        if verbose:
            print(f"    inner {r}: {100*m/n:.4f}%  o={[round(x,2) for x in o]}"
                  f" h1={h1:.2f} h0={h0:.2f}", flush=True)
    return m / n, o, h1, h0, T, Tf


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    o0 = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    wc = [0, -1, 0, 2, 0, 0, 0, 1]           # in CPU cycles
    best = None
    t = time.time()
    rate, o, h1, h0, T, Tf = run(caps, [x * CY for x in wc], list(o0),
                                 750.0, 375.0, rounds=3, verbose=True)
    best = (rate, list(wc), o, h1, h0)
    print(f"start w={wc}: {100*rate:.4f}%  [{time.time()-t:.0f}s]", flush=True)

    for sweep in range(3):
        improved = False
        for s in range(8):
            for delta in (-1, 1):
                cand = list(best[1])
                cand[s] += delta
                if abs(cand[s]) > 3:
                    continue
                r, o, h1, h0, T, Tf = run(caps, [x * CY for x in cand],
                                          list(o0), 750.0, 375.0, rounds=3)
                print(f"  w={cand}: {100*r:.4f}%", flush=True)
                if r > best[0] + 1e-9:
                    best = (r, cand, o, h1, h0)
                    improved = True
        print(f"sweep {sweep}: best {100*best[0]:.4f}% w={best[1]}", flush=True)
        if not improved:
            break

    rate, wc, o, h1, h0 = best
    r, o, h1, h0, T, Tf = run(caps, [x * CY for x in wc], list(o0),
                              750.0, 375.0, rounds=4, verbose=True)
    json.dump({"w_cycles": wc, "w": [x * CY for x in wc], "o": o,
               "h1": h1, "h0": h0, "rate": r,
               "T0_Gc": {k: [float(v[1]), float(v[2])] for k, v in Tf.items()}},
              open("stage6.json", "w"), indent=1)
    print(f"FINAL {100*r:.4f}%  w={wc}")


if __name__ == "__main__":
    main()
