"""Full calibration: nominal gaps + per-slot data-dependent gap modifier.

    t(i,s) = t0 + k * ( i*G + P[s] + sum_j w[j] * Hc[i,s][j] )

P[s] = cumsum of the nominal inter-sample gaps g[0..7] (G = sum g).
Hc[i,s][j] = how many times slot j has read HIGH strictly before sample
(i,s).  w[j] is the extra time the loop spends after a HIGH read at slot
j -- physically the BTJT branch-taken cost at that code site minus the
skipped NOP, which is +-1 CPU cycle depending on flash-prefetch
alignment.  Because w != 0 the sampler's period depends on the signal it
is watching: it phase-locks to the WS2812 stream, which is what makes the
frame occupy exactly 96 loops in every capture and what produces the
near-alternating merge pattern in `ones`.

Everything is closed form: Hc comes from the observed samples, so the
whole time base is an explicit function of the data and 18 globals plus
two nuisance parameters per capture.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels

ACT = 102


def prepare(caps):
    for c in caps:
        keep = c["it"] < ACT
        it = c["it"][keep]
        sl = c["sl"][keep]
        lv = c["lv"][keep]
        n = len(it)
        # cumulative per-slot high counts strictly before each sample
        Hc = np.zeros((n, 8), dtype=np.float64)
        run = np.zeros(8, dtype=np.float64)
        for m in range(n):
            Hc[m] = run
            run[sl[m]] += lv[m]
        c["ait"], c["asl"], c["alv"], c["Hc"], c["na"] = \
            it.astype(float), sl, lv, Hc, n
        c["slot_idx"] = [np.nonzero(sl == s)[0] for s in range(8)]
    return caps


def base_A(c, g, w):
    g = np.asarray(g, float)
    G = g.sum()
    P = np.concatenate([[0.0], np.cumsum(g)[:-1]])
    return c["ait"] * G + P[c["asl"]] + c["Hc"] @ np.asarray(w, float)


def nm(A, bits, lv, t0, k, h1, h0):
    return int(np.count_nonzero(wire_levels(t0 + k * A, bits, h1, h0) == lv))


def fit_tk(c, A, h1, h0, ks, t0s, t0=None, k=None):
    bits, lv = c["bits"], c["alv"]
    if t0 is None:
        best = (-1, 0.0, 1.0)
        for kk in ks:
            base = kk * A
            for tt in t0s:
                m = int(np.count_nonzero(
                    wire_levels(tt + base, bits, h1, h0) == lv))
                if m > best[0]:
                    best = (m, tt, kk)
        _, t0, k = best
    m = nm(A, bits, lv, t0, k, h1, h0)
    st, sk = 24.0, 4e-5
    while st > 5e-4 or sk > 1e-9:
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


def total(caps, g, w, h1, h0, nuis):
    tot = 0
    for c in caps:
        A = base_A(c, g, w)
        t0, k = nuis[c["key"]][:2]
        tot += nm(A, c["bits"], c["alv"], t0, k, h1, h0)
    return tot


def refresh(caps, g, w, h1, h0, nuis, ks=None, t0s=None, blind=False):
    tot = 0
    for c in caps:
        A = base_A(c, g, w)
        if blind:
            m, t0, k = fit_tk(c, A, h1, h0, ks, t0s)
        else:
            t0, k = nuis[c["key"]][:2]
            m, t0, k = fit_tk(c, A, h1, h0, None, None, t0, k)
        nuis[c["key"]] = (t0, k, m)
        tot += m
    return tot


def scan1(caps, g, w, h1, h0, nuis, which, idx, vals):
    """Exhaustive 1-D scan of one global parameter."""
    best = (-1, None)
    for v in vals:
        gg, ww, a, b = list(g), list(w), h1, h0
        if which == "g":
            gg[idx] = v
        elif which == "w":
            ww[idx] = v
        elif which == "h1":
            a = v
        else:
            b = v
        t = total(caps, gg, ww, a, b, nuis)
        if t > best[0]:
            best = (t, v)
    return best


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    N = sum(c["na"] for c in caps)

    g = [250.0, 250.0, 250.0, 250.0, 250.0, 375.0, 312.5, 562.5]
    w = [0.0, -62.5, 0.0, 0.0, 0.0, 0.0, 0.0, 62.5]
    h1, h0 = 750.0, 375.0
    nuis = {}
    ks = np.arange(0.9950, 1.0110, 5e-5)
    t0s = np.arange(-200.0, 400.0, 20.0)

    t = time.time()
    tot = refresh(caps, g, w, h1, h0, nuis, ks, t0s, blind=True)
    print(f"init {100*tot/N:.3f}%  [{time.time()-t:.0f}s]", flush=True)

    steps = [(31.25, 2.0), (7.8125, 0.5), (1.953125, 0.125), (0.5, 0.03125)]
    for phase, (gs, hs) in enumerate(steps):
        for rnd in range(6):
            improved = False
            for s in range(8):
                b, v = scan1(caps, g, w, h1, h0, nuis, "g", s,
                             g[s] + np.arange(-6, 7) * gs)
                if v != g[s]:
                    g[s] = v
                    improved = True
            for s in range(8):
                b, v = scan1(caps, g, w, h1, h0, nuis, "w", s,
                             w[s] + np.arange(-6, 7) * gs)
                if v != w[s]:
                    w[s] = v
                    improved = True
            for nmv in ("h1", "h0"):
                cur = h1 if nmv == "h1" else h0
                b, v = scan1(caps, g, w, h1, h0, nuis, nmv, 0,
                             cur + np.arange(-8, 9) * hs)
                if nmv == "h1":
                    h1 = v
                else:
                    h0 = v
            tot = refresh(caps, g, w, h1, h0, nuis)
            print(f"p{phase} r{rnd}: {100*tot/N:.4f}%  "
                  f"g={[round(x,2) for x in g]}\n        "
                  f"w={[round(x,2) for x in w]} h1={h1:.2f} h0={h0:.2f}",
                  flush=True)
            if not improved:
                break
    json.dump({"g": g, "w": w, "h1": h1, "h0": h0, "rate": tot / N,
               "nuis": {k: list(v) for k, v in nuis.items()}},
              open("stage3.json", "w"), indent=1)


if __name__ == "__main__":
    main()
