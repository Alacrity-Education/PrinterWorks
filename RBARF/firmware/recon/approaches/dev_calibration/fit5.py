"""Calibration by alternating interval-propagation and linear solve.

Round structure
  A. For every capture, score each candidate loop-start time T_i against
     that loop's 8 samples (using the current slot offsets, the current
     intra-loop HIGH corrections and the current effective high widths),
     then forward/backward-propagate so only loop-start times reachable
     with a plausible loop period survive.  This yields a tight interval
     [lo_i, hi_i] per loop, with no linearity assumed.
  B. Solve, jointly over all 54 captures, the LINEAR system

         T_i = T0_c + Gc_c * i + sum_j w[j] * C_j(i)

     (C_j(i) = number of HIGH reads at slot j in loops < i) against those
     intervals, by iteratively-projected least squares.  T0_c and Gc_c
     are per capture; w is global.
  C. With the resulting T_i, profile each slot offset o[s] and the two
     effective high widths exactly, on the raw sample-agreement count.

Repeat.  Finally refit (t0, eps) per capture on the agreement count.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels, BIT_NS

G0 = 2500.0
NLOOP = 96
HALF = 1500.0
STEP = 0.5


def prepare(caps):
    for c in caps:
        d = {}
        for i, s, v in zip(c["it"], c["sl"], c["lv"]):
            ii = int(i)
            if ii < NLOOP:
                d.setdefault(ii, {})[int(s)] = int(v)
        c["loop"] = d
        H = np.zeros((NLOOP, 8))
        for i in range(NLOOP):
            for s in range(8):
                H[i, s] = d[i].get(s, 0)
        c["H"] = H
        c["C"] = np.vstack([np.zeros(8), np.cumsum(H, axis=0)[:-1]])  # C_j(i)
    return caps


def intra(H_i, w):
    """Intra-loop offset correction: sum_{j<s} w[j]*h_j for each slot s."""
    cw = np.concatenate([[0.0], np.cumsum(H_i * np.asarray(w, float))[:-1]])
    return cw


def windows(c, o, w, h1, h0, Gc, dl=110.0):
    off = np.arange(-HALF, HALF, STEP)
    n = len(off)
    sc = np.zeros((NLOOP, n), dtype=np.int16)
    o = np.asarray(o, float)
    for i in range(NLOOP):
        cw = intra(c["H"][i], w)
        base = i * Gc + off
        tot = np.zeros(n, dtype=np.int16)
        for s, v in c["loop"][i].items():
            tot += (wire_levels(base + o[s] + cw[s], c["bits"], h1, h0) == v)
        sc[i] = tot
    F = sc >= 8
    for i in range(NLOOP):
        if not F[i].any():
            F[i] = sc[i] >= sc[i].max()
    wd = int(round(dl / STEP))

    def dil(mask):
        m = mask.astype(np.int32)
        cs = np.concatenate([[0], np.cumsum(m)])
        lo = np.maximum(np.arange(n) - wd, 0)
        hi = np.minimum(np.arange(n) + wd + 1, n)
        return (cs[hi] - cs[lo]) > 0

    R = F.copy()
    for i in range(1, NLOOP):
        R[i] &= dil(R[i - 1])
        if not R[i].any():
            R[i] = F[i]
    S = R.copy()
    for i in range(NLOOP - 2, -1, -1):
        S[i] &= dil(S[i + 1])
        if not S[i].any():
            S[i] = R[i]
    lo = np.empty(NLOOP)
    hi = np.empty(NLOOP)
    for i in range(NLOOP):
        idx = np.nonzero(S[i])[0]
        lo[i] = i * Gc + off[idx[0]]
        hi[i] = i * Gc + off[idx[-1]]
    return lo, hi


def solve_linear(caps, LO, HI, iters=40):
    """Projected least squares for T0_c, Gc_c (per capture) and w (global)."""
    nc = len(caps)
    rows = nc * NLOOP
    X = np.zeros((rows, 2 * nc + 8))
    for ci, c in enumerate(caps):
        r = slice(ci * NLOOP, (ci + 1) * NLOOP)
        X[r, 2 * ci] = 1.0
        X[r, 2 * ci + 1] = np.arange(NLOOP)
        X[r, 2 * nc:] = c["C"]
    lo = np.concatenate([LO[c["key"]] for c in caps])
    hi = np.concatenate([HI[c["key"]] for c in caps])
    y = (lo + hi) / 2.0
    beta = None
    for _ in range(iters):
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        y = np.clip(pred, lo, hi)
    return beta


def profile(caps, T, o, w, h1, h0):
    """Exact 1-D profiling of o[s] then h1/h0 given fixed loop starts."""
    o = list(o)
    for s in range(8):
        vals = np.arange(max(0.0, o[s] - 350.0), o[s] + 350.0, 0.25)
        tot = np.zeros(len(vals), dtype=np.int64)
        for c in caps:
            Ti = T[c["key"]]
            base, obs = [], []
            for i in range(NLOOP):
                if s in c["loop"][i]:
                    cw = intra(c["H"][i], w)
                    base.append(Ti[i] + cw[s])
                    obs.append(c["loop"][i][s])
            base = np.asarray(base)
            obs = np.asarray(obs)
            t = base[:, None] + vals[None, :]
            pred = wire_levels(t.ravel(), c["bits"], h1, h0).reshape(t.shape)
            tot += (pred == obs[:, None]).sum(axis=0)
        o[s] = float(vals[int(np.argmax(tot))])
    for name in ("h1", "h0"):
        cur = h1 if name == "h1" else h0
        vals = np.arange(max(40.0, cur - 160.0), cur + 160.0, 0.25)
        best = (-1, cur)
        for v in vals:
            a = v if name == "h1" else h1
            b = v if name == "h0" else h0
            tot = 0
            for c in caps:
                Ti = T[c["key"]]
                t, obs = [], []
                for i in range(NLOOP):
                    cw = intra(c["H"][i], w)
                    for s2, vv in c["loop"][i].items():
                        t.append(Ti[i] + o[s2] + cw[s2])
                        obs.append(vv)
                tot += int(np.count_nonzero(
                    wire_levels(np.asarray(t), c["bits"], a, b)
                    == np.asarray(obs)))
            if tot > best[0]:
                best = (tot, v)
        if name == "h1":
            h1 = best[1]
        else:
            h0 = best[1]
    return o, h1, h0


def count_all(caps, T, o, w, h1, h0):
    m = n = 0
    for c in caps:
        Ti = T[c["key"]]
        t, obs = [], []
        for i in range(NLOOP):
            cw = intra(c["H"][i], w)
            for s, vv in c["loop"][i].items():
                t.append(Ti[i] + o[s] + cw[s])
                obs.append(vv)
        m += int(np.count_nonzero(
            wire_levels(np.asarray(t), c["bits"], h1, h0) == np.asarray(obs)))
        n += len(t)
    return m, n


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    w = [0.0] * 8
    h1, h0 = 750.0, 375.0
    Gc = {c["key"]: G0 for c in caps}

    for rnd in range(8):
        t0 = time.time()
        LO, HI = {}, {}
        for c in caps:
            lo, hi = windows(c, o, w, h1, h0, Gc[c["key"]])
            LO[c["key"]], HI[c["key"]] = lo, hi
        beta = solve_linear(caps, LO, HI)
        nc = len(caps)
        wnew = list(beta[2 * nc:])
        T = {}
        for ci, c in enumerate(caps):
            T0c, Gcc = beta[2 * ci], beta[2 * ci + 1]
            Gc[c["key"]] = Gcc
            T[c["key"]] = T0c + Gcc * np.arange(NLOOP) + c["C"] @ np.asarray(wnew)
        w = wnew
        o, h1, h0 = profile(caps, T, o, w, h1, h0)
        m, n = count_all(caps, T, o, w, h1, h0)
        gs = np.mean([Gc[c["key"]] for c in caps])
        print(f"round {rnd}: {100*m/n:.4f}%  ({m}/{n})  Gmean={gs:.3f} "
              f"[{time.time()-t0:.0f}s]\n   o={[round(x,2) for x in o]}\n"
              f"   w={[round(x,3) for x in w]} h1={h1:.2f} h0={h0:.2f}",
              flush=True)
    json.dump({"o": o, "w": w, "h1": h1, "h0": h0,
               "Gc": {k: float(v) for k, v in Gc.items()},
               "T": {k: list(map(float, v)) for k, v in T.items()}},
              open("stage5.json", "w"), indent=1)


if __name__ == "__main__":
    main()
