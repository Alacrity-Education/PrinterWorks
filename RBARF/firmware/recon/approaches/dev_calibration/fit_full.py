"""Global calibration of the full sampler timing model.

    A(i,s) = i*G + o[s] + sum_j w[j] * C_j(i,s)
    t(i,s) = t0_c + k_c * A(i,s),      k_c = 1/(1+eps_c)

C_j(i,s) = number of HIGH reads at slot j strictly before sample (i,s).
w[j] is the extra time the loop takes when slot j reads HIGH (the
BTJT-taken / NOP-skipped path); it comes out quantised to whole 62.5 ns
CPU cycles.  o[], G, w[], eff_high_1, eff_high_0 are global; (t0, eps)
are per capture.
"""
import json
import sys
import time

import numpy as np

import fitlib as F

CY = 62.5


def prepare(caps):
    for c in caps:
        sl, lv = c["sl"], c["lv"]
        n = len(sl)
        H = np.zeros((n, 8))
        run = np.zeros(8)
        for m in range(n):
            H[m] = run
            run[sl[m]] += lv[m]
        c["H"] = H
        c["aH"] = H[c["amask"]]
    return caps


def A_of(c, G, o, w, active=True):
    o = np.asarray(o, float)
    w = np.asarray(w, float)
    if active:
        return c["ait"] * G + o[c["asl"]] + c["aH"] @ w
    return c["it"] * G + o[c["sl"]] + c["H"] @ w


def grid_tk(A, B, lv, Ls, G, t0s):
    best = (-1, 0.0, 1.0)
    for Lt in Ls:
        k = Lt / G
        T = t0s[:, None] + k * A[None, :]
        pred = (np.searchsorted(B, T.ravel(), side="right") & 1
                ).reshape(T.shape).astype(np.int8)
        m = (pred == lv[None, :]).sum(axis=1)
        j = int(np.argmax(m))
        if m[j] > best[0]:
            best = (int(m[j]), float(t0s[j]), float(k))
    return best


def seed(caps, G, o, w, h1, h0, lo=2470.0, hi=2545.0, step=0.25,
         t0lo=-200.0, t0hi=700.0, t0step=5.0):
    t0s = np.arange(t0lo, t0hi, t0step)
    Ls = np.arange(lo, hi, step)
    nuis = {}
    tot = 0
    for c in caps:
        A = A_of(c, G, o, w)
        B = F.edges_of(c["bits"], h1, h0)
        m, t0, k = grid_tk(A, B, c["alv"], Ls, G, t0s)
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k, st=6.0, sk=1e-5)
        nuis[c["key"]] = [t0, k, m]
        tot += m
    return tot, nuis


def refit(caps, G, o, w, h1, h0, nuis, st=6.0, sk=1e-5):
    tot = 0
    for c in caps:
        A = A_of(c, G, o, w)
        B = F.edges_of(c["bits"], h1, h0)
        t0, k = nuis[c["key"]][:2]
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k, st=st, sk=sk)
        nuis[c["key"]] = [t0, k, m]
        tot += m
    return tot


def score(caps, G, o, w, h1, h0, nuis, Bs=None):
    tot = 0
    for c in caps:
        A = A_of(c, G, o, w)
        B = Bs[c["key"]] if Bs else F.edges_of(c["bits"], h1, h0)
        t0, k = nuis[c["key"]][:2]
        pred = F.level_at(t0 + k * A, B)
        tot += int(np.count_nonzero(pred == c["alv"]))
    return tot


def descend(caps, G, o, w, h1, h0, nuis, steps, log=print):
    N = sum(c["an"] for c in caps)
    tot = refit(caps, G, o, w, h1, h0, nuis)
    best = (tot, G, list(o), list(w), h1, h0,
            {k: list(v) for k, v in nuis.items()})
    for si, step in enumerate(steps):
        for rnd in range(8):
            prev = tot
            Bs = {c["key"]: F.edges_of(c["bits"], h1, h0) for c in caps}
            cur = score(caps, G, o, w, h1, h0, nuis, Bs)

            def line(vals, setter):
                nonlocal cur
                bx, bv = None, cur
                for x in vals:
                    GG, oo, ww = setter(x)
                    v = score(caps, GG, oo, ww, h1, h0, nuis, Bs)
                    if v > bv:
                        bv, bx = v, x
                cur = bv
                return bx

            for s in range(1, 8):
                x = line(o[s] + np.arange(-5, 6) * step,
                         lambda z, s=s: (G, o[:s] + [z] + o[s + 1:], w))
                if x is not None:
                    o[s] = x
            for s in range(8):
                x = line(w[s] + np.arange(-5, 6) * step,
                         lambda z, s=s: (G, o, w[:s] + [z] + w[s + 1:]))
                if x is not None:
                    w[s] = x
            x = line(G + np.arange(-5, 6) * step * 0.4, lambda z: (z, o, w))
            if x is not None:
                G = x
            for name in (1, 0):
                base = h1 if name else h0
                bx, bv = None, cur
                for z in base + np.arange(-5, 6) * step:
                    a, b = (z, h0) if name else (h1, z)
                    v = score(caps, G, o, w, a, b, nuis)
                    if v > bv:
                        bv, bx = v, z
                if bx is not None:
                    cur = bv
                    if name:
                        h1 = bx
                    else:
                        h0 = bx
            tot = refit(caps, G, o, w, h1, h0, nuis)
            if tot > best[0]:
                best = (tot, G, list(o), list(w), h1, h0,
                        {k: list(v) for k, v in nuis.items()})
            log(f"  s{si} r{rnd}: act={100*tot/N:.3f}% G={G:.2f} "
                f"h1={h1:.1f} h0={h0:.1f}\n"
                f"     o={[round(z,1) for z in o]}\n"
                f"     w={[round(z/CY,3) for z in w]} cy")
            if tot <= prev:
                break
    return best
