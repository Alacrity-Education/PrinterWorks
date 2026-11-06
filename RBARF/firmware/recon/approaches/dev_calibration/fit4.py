"""Calibration with a smooth surrogate loss (distance-to-correct-interval).

Model (all times ns, k = 1/(1+eps) per capture):

    A(i,s) = i*G + P[s] + sum_j w[j] * Hc[i,s][j]
    t(i,s) = t0 + k * A(i,s) * (1 + q * A/Aend)

G = sum(g), P = cumsum(g).  w[j] = extra loop time after a HIGH read at
slot j; it makes the sampler period depend on the signal, i.e. the loop
phase-locks to the WS2812 stream.  q is an optional per-capture linear
clock drift.

Objective for optimisation: sum over samples of the distance from t to
the nearest time interval whose wire level equals the observed level
(zero when the sample is already explained).  Piecewise linear and far
better behaved than the raw 0/1 agreement, which is used only for the
final polish and for reporting.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels, BIT_NS

ACT = 102


def prepare(caps):
    for c in caps:
        keep = c["it"] < ACT
        it, sl, lv = c["it"][keep], c["sl"][keep], c["lv"][keep]
        n = len(it)
        Hc = np.zeros((n, 8))
        run = np.zeros(8)
        for m in range(n):
            Hc[m] = run
            run[sl[m]] += lv[m]
        c.update(ait=it.astype(float), asl=sl, alv=lv, Hc=Hc, na=n)
        c["nbits"] = len(c["bits"])
    return caps


def A_of(c, g, w):
    g = np.asarray(g, float)
    P = np.concatenate([[0.0], np.cumsum(g)[:-1]])
    return c["ait"] * g.sum() + P[c["asl"]] + c["Hc"] @ np.asarray(w, float)


def times(A, t0, k, q=0.0):
    if q == 0.0:
        return t0 + k * A
    return t0 + k * A * (1.0 + q * A / A[-1])


def loss(t, bits, lv, h1, h0):
    """Distance from each t to the nearest interval with the observed level."""
    nb = len(bits)
    hw = np.where(bits == 1, h1, h0)
    b = np.floor(t / BIT_NS).astype(np.int64)
    best = np.full(len(t), 1e18)
    for db in (-1, 0, 1):
        bb = b + db
        ok = (bb >= 0) & (bb < nb)
        j = np.clip(bb, 0, nb - 1)
        base = j * BIT_NS
        hi_lo, hi_hi = base, base + hw[j]          # HIGH interval
        lo_lo, lo_hi = base + hw[j], base + BIT_NS  # LOW interval
        lo = np.where(lv == 1, hi_lo, lo_lo)
        hi = np.where(lv == 1, hi_hi, lo_hi)
        d = np.maximum(lo - t, t - hi)
        d = np.maximum(d, 0.0)
        d = np.where(ok, d, 1e18)
        best = np.minimum(best, d)
    # outside the frame the line is low, so low samples are free there
    outside = (t < 0) | (t >= nb * BIT_NS)
    free = outside & (lv == 0)
    best = np.where(free, 0.0, best)
    # low samples can also be satisfied by the pre/post-frame idle
    if True:
        d_pre = np.where(lv == 0, np.maximum(t - 0.0, 0.0), 1e18)
        d_post = np.where(lv == 0, np.maximum(nb * BIT_NS - t, 0.0), 1e18)
        best = np.minimum(best, np.minimum(d_pre, d_post))
    return best.sum()


def nmatch(t, bits, lv, h1, h0):
    return int(np.count_nonzero(wire_levels(t, bits, h1, h0) == lv))


def fit_nuis(c, A, h1, h0, t0=None, k=None, q=0.0, blind=False,
             ks=None, t0s=None, use_q=False):
    bits, lv = c["bits"], c["alv"]
    if blind:
        best = (1e30, 0.0, 1.0)
        for kk in ks:
            base = kk * A
            for tt in t0s:
                L = loss(tt + base, bits, lv, h1, h0)
                if L < best[0]:
                    best = (L, tt, kk)
        _, t0, k = best
    cur = loss(times(A, t0, k, q), bits, lv, h1, h0)
    st, sk, sq = 30.0, 5e-5, 2e-3
    while st > 1e-3:
        found = None
        moves = [(st, 0, 0), (-st, 0, 0), (0, sk, 0), (0, -sk, 0),
                 (st, sk, 0), (st, -sk, 0), (-st, sk, 0), (-st, -sk, 0)]
        if use_q:
            moves += [(0, 0, sq), (0, 0, -sq)]
        for dt, dk, dq in moves:
            L = loss(times(A, t0 + dt, k + dk, q + dq), bits, lv, h1, h0)
            if L < cur - 1e-9:
                cur, found = L, (t0 + dt, k + dk, q + dq)
        if found is None:
            st /= 2.0
            sk /= 2.0
            sq /= 2.0
        else:
            t0, k, q = found
    return cur, t0, k, q


def polish_count(c, A, h1, h0, t0, k, q):
    bits, lv = c["bits"], c["alv"]
    m = nmatch(times(A, t0, k, q), bits, lv, h1, h0)
    st, sk, sq = 12.0, 2e-5, 1e-3
    while st > 5e-4:
        found = None
        for dt, dk, dq in ((st, 0, 0), (-st, 0, 0), (0, sk, 0), (0, -sk, 0),
                           (st, sk, 0), (st, -sk, 0), (-st, sk, 0),
                           (-st, -sk, 0), (0, 0, sq), (0, 0, -sq)):
            mm = nmatch(times(A, t0 + dt, k + dk, q + dq), bits, lv, h1, h0)
            if mm > m:
                m, found = mm, (t0 + dt, k + dk, q + dq)
        if found is None:
            st /= 2.0
            sk /= 2.0
            sq /= 2.0
        else:
            t0, k, q = found
    return m, t0, k, q


def total_loss(caps, g, w, h1, h0, nuis):
    s = 0.0
    for c in caps:
        A = A_of(c, g, w)
        t0, k, q = nuis[c["key"]][:3]
        s += loss(times(A, t0, k, q), c["bits"], c["alv"], h1, h0)
    return s


def total_count(caps, g, w, h1, h0, nuis):
    s = 0
    for c in caps:
        A = A_of(c, g, w)
        t0, k, q = nuis[c["key"]][:3]
        s += nmatch(times(A, t0, k, q), c["bits"], c["alv"], h1, h0)
    return s


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    N = sum(c["na"] for c in caps)

    g = [250.0, 250.0, 250.0, 250.0, 250.0, 375.0, 312.5, 562.5]
    w = [0.0, -62.5, 0.0, 0.0, 0.0, 0.0, 0.0, 62.5]
    h1, h0 = 750.0, 375.0
    ks = np.arange(0.9930, 1.0130, 5e-5)
    t0s = np.arange(-200.0, 400.0, 20.0)

    nuis = {}
    t = time.time()
    for c in caps:
        A = A_of(c, g, w)
        L, t0, k, q = fit_nuis(c, A, h1, h0, blind=True, ks=ks, t0s=t0s)
        nuis[c["key"]] = (t0, k, q)
    print(f"init loss={total_loss(caps,g,w,h1,h0,nuis):.0f} "
          f"count={100*total_count(caps,g,w,h1,h0,nuis)/N:.3f}% "
          f"[{time.time()-t:.0f}s]", flush=True)

    def line(which, idx, vals):
        nonlocal g, w, h1, h0
        best = (1e30, None)
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
            L = total_loss(caps, gg, ww, a, b, nuis)
            if L < best[0]:
                best = (L, v)
        return best[1]

    use_q = False
    for phase, step in enumerate([25.0, 8.0, 2.5, 0.8, 0.25]):
        if phase >= 2:
            use_q = True
        for rnd in range(8):
            prev = total_loss(caps, g, w, h1, h0, nuis)
            for s in range(8):
                g[s] = line("g", s, g[s] + np.arange(-8, 9) * step)
            for s in range(8):
                w[s] = line("w", s, w[s] + np.arange(-8, 9) * step)
            h1 = line("h1", 0, h1 + np.arange(-8, 9) * step)
            h0 = line("h0", 0, h0 + np.arange(-8, 9) * step)
            for c in caps:
                A = A_of(c, g, w)
                t0, k, q = nuis[c["key"]][:3]
                L, t0, k, q = fit_nuis(c, A, h1, h0, t0, k, q, use_q=use_q)
                nuis[c["key"]] = (t0, k, q)
            cur = total_loss(caps, g, w, h1, h0, nuis)
            print(f"p{phase} r{rnd}: loss={cur:.0f} "
                  f"count={100*total_count(caps,g,w,h1,h0,nuis)/N:.3f}%\n"
                  f"   g={[round(x,2) for x in g]}\n"
                  f"   w={[round(x,2) for x in w]} h1={h1:.2f} h0={h0:.2f}",
                  flush=True)
            if cur > prev - 1.0:
                break

    for c in caps:
        A = A_of(c, g, w)
        t0, k, q = nuis[c["key"]][:3]
        m, t0, k, q = polish_count(c, A, h1, h0, t0, k, q)
        nuis[c["key"]] = (t0, k, q, m)
    cnt = sum(v[3] for v in nuis.values())
    print(f"FINAL count={100*cnt/N:.4f}%")
    json.dump({"g": g, "w": w, "h1": h1, "h0": h0, "rate": cnt / N,
               "nuis": {k: list(v) for k, v in nuis.items()}},
              open("stage4.json", "w"), indent=1)


if __name__ == "__main__":
    main()
