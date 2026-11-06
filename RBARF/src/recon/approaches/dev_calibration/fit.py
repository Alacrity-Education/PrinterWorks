"""Global fit: coordinate descent on the sampler timing model."""
import json
import sys
import time

import numpy as np

import model
from model import BIT_NS, wire_levels

ACT_ITERS = 102          # iterations that can contain frame signal
ACT_N = ACT_ITERS * 8


def build(caps):
    for c in caps:
        c["act"] = min(ACT_N, c["n"])
        c["Ncum"] = np.concatenate([[0], np.cumsum(c["lv"].astype(np.int64))[:-1]])
    return caps


def A_of(cap, g, d, lim=None):
    g = np.asarray(g, float)
    G = g.sum()
    P = np.concatenate([[0.0], np.cumsum(g)[:-1]])
    sl = slice(0, lim) if lim else slice(None)
    return cap["it"][sl] * G + P[cap["sl"][sl]] - d * cap["Ncum"][sl]


def agree_arr(A, bits, lv, t0, k, h1, h0):
    return int(np.count_nonzero(wire_levels(t0 + k * A, bits, h1, h0) == lv))


def coarse(cap, A, h1, h0, ks, t0s):
    bits = cap["bits"]
    lv = cap["lv"][:len(A)]
    best = (-1, 0.0, 1.0)
    for k in ks:
        base = k * A
        for t0 in t0s:
            m = int(np.count_nonzero(wire_levels(t0 + base, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, t0, k)
    return best


def polish(cap, A, h1, h0, t0, k, st=20.0, sk=4e-5, tol_t=1e-3, tol_k=1e-9):
    bits = cap["bits"]
    lv = cap["lv"][:len(A)]
    m = agree_arr(A, bits, lv, t0, k, h1, h0)
    while st > tol_t or sk > tol_k:
        best = None
        for dt, dk in ((st, 0.0), (-st, 0.0), (0.0, sk), (0.0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = agree_arr(A, bits, lv, t0 + dt, k + dk, h1, h0)
            if mm > m:
                m, best = mm, (t0 + dt, k + dk)
        if best is None:
            st /= 2.0
            sk /= 2.0
        else:
            t0, k = best
    return m, t0, k


def evaluate(caps, g, d, h1, h0, nuis, coarse_first=False,
             ks=None, t0s=None, lim=ACT_N):
    tot = 0
    n = 0
    new = {}
    for c in caps:
        L = min(lim, c["n"])
        A = A_of(c, g, d, L)
        if coarse_first:
            m, t0, k = coarse(c, A, h1, h0, ks, t0s)
        else:
            t0, k = nuis[c["key"]][:2]
        m, t0, k = polish(c, A, h1, h0, t0, k)
        new[c["key"]] = (t0, k, m, L)
        tot += m
        n += L
    return tot / n, new


def main():
    meta, caps = model.load()
    caps = build(caps)

    # initial globals: synth-style 40-cycle loop, 9-cycle end gap
    g = [250.0, 250.0, 250.0, 250.0, 250.0, 375.0, 312.5, 562.5]
    d = 0.0
    h1, h0 = 750.0, 375.0

    ks = np.arange(0.995, 1.016, 3e-5)
    t0s = np.arange(-200.0, 400.0, 15.0)
    t = time.time()
    rate, nuis = evaluate(caps, g, d, h1, h0, None, coarse_first=True,
                          ks=ks, t0s=t0s)
    print(f"initial (uniform, d=0): {rate*100:.3f}%  [{time.time()-t:.1f}s]",
          flush=True)

    params = list(g) + [d, h1, h0]

    def unpack(p):
        return p[:8], p[8], p[9], p[10]

    def score(p, nu):
        gg, dd, hh1, hh0 = unpack(p)
        return evaluate(caps, gg, dd, hh1, hh0, nu)

    steps = [40.0] * 8 + [20.0, 30.0, 30.0]
    best_rate, best_nuis = rate, nuis
    for rnd in range(40):
        improved = False
        for j in range(len(params)):
            for sgn in (1, -1):
                trial = list(params)
                trial[j] += sgn * steps[j]
                if j < 8 and trial[j] < 30.0:
                    continue
                if j in (9, 10) and not (100.0 < trial[j] < 1150.0):
                    continue
                r, nu = score(trial, best_nuis)
                if r > best_rate + 1e-12:
                    best_rate, best_nuis, params = r, nu, trial
                    improved = True
                    break
        print(f"round {rnd}: {best_rate*100:.4f}%  steps={steps[0]:.3f} "
              f"g={[round(x,1) for x in params[:8]]} d={params[8]:.2f} "
              f"h1={params[9]:.1f} h0={params[10]:.1f}", flush=True)
        if not improved:
            steps = [s / 2.0 for s in steps]
            if steps[0] < 0.02:
                break
    json.dump({"params": params, "rate": best_rate,
               "nuis": {k: list(v) for k, v in best_nuis.items()}},
              open("stage1.json", "w"), indent=1)
    print("done", best_rate)


if __name__ == "__main__":
    main()
