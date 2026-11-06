"""Final parametric fit and polish.

    t(i,s) = t0 + k * ( i*G + o[s] + sum_j w[j]*Hc_j(i,s) ),  k = 1/(1+eps)

Hc_j(i,s) = number of HIGH reads at slot j strictly before sample (i,s).
Seeded from the stage-A/B solution, then coordinate-descended directly on
the raw sample-agreement count with the per-capture (t0, eps) refitted
every round.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels

CY = 62.5


def prepare(caps):
    for c in caps:
        it, sl, lv = c["it"], c["sl"], c["lv"]
        n = len(it)
        Hc = np.zeros((n, 8))
        run = np.zeros(8)
        for m in range(n):
            Hc[m] = run
            run[sl[m]] += lv[m]
        c["Hc"] = Hc
        c["n"] = n
    return caps


def A_of(c, G, o, w):
    return (c["it"] * G + np.asarray(o, float)[c["sl"]]
            + c["Hc"] @ np.asarray(w, float))


def nm(A, bits, lv, t0, k, h1, h0):
    return int(np.count_nonzero(wire_levels(t0 + k * A, bits, h1, h0) == lv))


def polish_tk(c, A, h1, h0, t0, k, st=40.0, sk=6e-5):
    bits, lv = c["bits"], c["lv"]
    m = nm(A, bits, lv, t0, k, h1, h0)
    while st > 2e-4:
        found = None
        for dt, dk in ((st, 0.0), (-st, 0.0), (0.0, sk), (0.0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = nm(A, bits, lv, t0 + dt, k + dk, h1, h0)
            if mm > m:
                m, found = mm, (t0 + dt, k + dk)
        if found is None:
            st /= 2.0
            sk /= 2.0
        else:
            t0, k = found
    return m, t0, k


def refit(caps, G, o, w, h1, h0, nuis):
    tot = 0
    for c in caps:
        A = A_of(c, G, o, w)
        t0, k = nuis[c["key"]][:2]
        m, t0, k = polish_tk(c, A, h1, h0, t0, k)
        nuis[c["key"]] = (t0, k, m)
        tot += m
    return tot


def score(caps, G, o, w, h1, h0, nuis):
    tot = 0
    for c in caps:
        A = A_of(c, G, o, w)
        t0, k = nuis[c["key"]][:2]
        tot += nm(A, c["bits"], c["lv"], t0, k, h1, h0)
    return tot


def main():
    st = json.load(open("stageAB.json"))
    G, o, w, h1, h0 = st["G"], list(st["o"]), list(st["w"]), st["h1"], st["h0"]
    meta, caps = model.load()
    caps = prepare(caps)
    N = sum(c["n"] for c in caps)

    nuis = {}
    for c in caps:
        T0c, Gcc = st["par"][c["key"]]
        nuis[c["key"]] = (T0c, Gcc / G, 0)
    tot = refit(caps, G, o, w, h1, h0, nuis)
    print(f"seeded: {100*tot/N:.4f}%", flush=True)

    def line(vals, setter):
        best = (-1, None)
        for v in vals:
            GG, oo, ww, a, b = setter(v)
            t = score(caps, GG, oo, ww, a, b, nuis)
            if t > best[0]:
                best = (t, v)
        return best[1]

    for phase, step in enumerate([8.0, 2.0, 0.5, 0.125]):
        for rnd in range(6):
            prev = tot
            for s in range(8):
                cur = o[s]
                v = line(cur + np.arange(-6, 7) * step,
                         lambda x, s=s: (G, o[:s] + [x] + o[s+1:], w, h1, h0))
                o[s] = v
            for s in range(8):
                cur = w[s]
                v = line(cur + np.arange(-6, 7) * step,
                         lambda x, s=s: (G, o, w[:s] + [x] + w[s+1:], h1, h0))
                w[s] = v
            G = line(G + np.arange(-6, 7) * step * 0.25,
                     lambda x: (x, o, w, h1, h0))
            h1 = line(h1 + np.arange(-8, 9) * step,
                      lambda x: (G, o, w, x, h0))
            h0 = line(h0 + np.arange(-8, 9) * step,
                      lambda x: (G, o, w, h1, x))
            tot = refit(caps, G, o, w, h1, h0, nuis)
            print(f"p{phase} r{rnd}: {100*tot/N:.4f}%  G={G:.3f}\n"
                  f"   o={[round(x,2) for x in o]}\n"
                  f"   w={[round(x,2) for x in w]} h1={h1:.2f} h0={h0:.2f}",
                  flush=True)
            if tot <= prev:
                break

    json.dump({"G": G, "o": o, "w": w, "h1": h1, "h0": h0, "rate": tot / N,
               "nuis": {k: list(v) for k, v in nuis.items()}},
              open("final.json", "w"), indent=1)
    print(f"FINAL {100*tot/N:.4f}%")


if __name__ == "__main__":
    main()
