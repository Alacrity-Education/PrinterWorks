"""Two-stage calibration.

STAGE A - slot geometry.  Let the loop-start time T_i float freely (DP,
one state per candidate T_i on a 1 ns grid, loop period allowed to move
by at most +-1 CPU cycle from loop to loop) and fit only the SHARED
quantities: the 8 slot offsets o[s] and the two effective high widths.
T_i cannot hide an error in o[s], because o[s] is common to every loop of
every capture while T_i shifts all eight samples of one loop together.

STAGE B - time base.  Regress the DP's T_i onto

    T_i = T0_c + Gc_c * i + sum_j w[j] * C_j(i)

C_j(i) = number of HIGH reads at slot j in loops < i.  w is global: it is
the extra loop time caused by a HIGH read at slot j (BTJT branches and
skips its NOP; the net cost of that code site differs by about +-1 CPU
cycle).  This is what makes the sampler phase-lock to the WS2812 stream.
"""
import json
import sys
import time

import numpy as np

import model
from model import wire_levels

NLOOP = 96
CY = 62.5


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
        c["C"] = np.vstack([np.zeros(8), np.cumsum(H, axis=0)[:-1]])
    return caps


def intra(H_i, w):
    return np.concatenate([[0.0], np.cumsum(H_i * np.asarray(w, float))[:-1]])


def dp_path(c, o, w, h1, h0, G=2500.0, half=900.0, step=1.0, dl=70.0):
    off = np.arange(-half, half, step)
    n = len(off)
    o = np.asarray(o, float)
    # centre the search window on the model's own accumulated loop time,
    # otherwise the phase-lock term walks the true T_i out of the window
    ctr = np.arange(NLOOP) * G + c["C"] @ np.asarray(w, float)
    sc = np.zeros((NLOOP, n), dtype=np.int32)
    for i in range(NLOOP):
        cw = intra(c["H"][i], w)
        base = ctr[i] + off
        tot = np.zeros(n, dtype=np.int32)
        for s, v in c["loop"][i].items():
            tot += (wire_levels(base + o[s] + cw[s], c["bits"], h1, h0) == v)
        sc[i] = tot
    wd = int(round(dl / step))
    best = sc[0].copy()
    back = np.zeros((NLOOP, n), dtype=np.int32)
    ar = np.arange(n)
    for i in range(1, NLOOP):
        pad = np.full(n + 2 * wd, -10**6, dtype=np.int32)
        pad[wd:wd + n] = best
        sw = np.lib.stride_tricks.sliding_window_view(pad, 2 * wd + 1)
        rel = sw.argmax(axis=1)
        back[i] = np.clip(rel - wd + ar, 0, n - 1)
        best = sw.max(axis=1) + sc[i]
    path = np.zeros(NLOOP, dtype=np.int32)
    path[-1] = int(np.argmax(best))
    for i in range(NLOOP - 1, 0, -1):
        path[i - 1] = back[i][path[i]]
    return int(best.max()), ctr + off[path]


def sample_times(c, T, o, w):
    t, obs = [], []
    for i in range(NLOOP):
        cw = intra(c["H"][i], w)
        for s, v in c["loop"][i].items():
            t.append(T[i] + o[s] + cw[s])
            obs.append(v)
    return np.asarray(t), np.asarray(obs)


def count(caps, Ts, o, w, h1, h0):
    m = n = 0
    for c in caps:
        t, obs = sample_times(c, Ts[c["key"]], o, w)
        m += int(np.count_nonzero(wire_levels(t, c["bits"], h1, h0) == obs))
        n += len(t)
    return m, n


def profile(caps, Ts, o, w, h1, h0, span=140.0, step=0.25):
    o = list(o)
    for s in range(8):
        vals = np.arange(o[s] - span, o[s] + span, step)
        tot = np.zeros(len(vals), dtype=np.int64)
        for c in caps:
            T = Ts[c["key"]]
            base, obs = [], []
            for i in range(NLOOP):
                if s in c["loop"][i]:
                    cw = intra(c["H"][i], w)
                    base.append(T[i] + cw[s])
                    obs.append(c["loop"][i][s])
            base = np.asarray(base)[:, None]
            obs = np.asarray(obs)[:, None]
            tt = base + vals[None, :]
            pred = wire_levels(tt.ravel(), c["bits"], h1, h0).reshape(tt.shape)
            tot += (pred == obs).sum(axis=0)
        o[s] = float(vals[int(np.argmax(tot))])
    pre = {c["key"]: sample_times(c, Ts[c["key"]], o, w) for c in caps}
    for name, lo_b, hi_b in (("h1", 400.0, 950.0), ("h0", 120.0, 650.0)):
        cur = h1 if name == "h1" else h0
        vals = np.arange(max(lo_b, cur - span), min(hi_b, cur + span), 0.25)
        best = (-1, cur)
        for v in vals:
            a = v if name == "h1" else h1
            b = v if name == "h0" else h0
            tot = 0
            for c in caps:
                t, obs = pre[c["key"]]
                tot += int(np.count_nonzero(
                    wire_levels(t, c["bits"], a, b) == obs))
            if tot > best[0]:
                best = (tot, v)
        if name == "h1":
            h1 = best[1]
        else:
            h0 = best[1]
    return o, h1, h0


def stageA(caps, o, w, h1, h0, rounds=5):
    for r in range(rounds):
        t0 = time.time()
        Ts, ceil = {}, 0
        for c in caps:
            sc, T = dp_path(c, o, w, h1, h0)
            Ts[c["key"]] = T
            ceil += sc
        o, h1, h0 = profile(caps, Ts, o, w, h1, h0)
        m, n = count(caps, Ts, o, w, h1, h0)
        print(f" A{r}: dp_ceiling={100*ceil/n:.3f}%  after_profile={100*m/n:.3f}%"
              f"  o={[round(x,2) for x in o]} h1={h1:.2f} h0={h0:.2f}"
              f"  [{time.time()-t0:.0f}s]", flush=True)
    return o, h1, h0, Ts


def stageB(caps, Ts):
    """Least squares for per-capture (T0, Gc) and global w."""
    nc = len(caps)
    X = np.zeros((nc * NLOOP, 2 * nc + 8))
    y = np.zeros(nc * NLOOP)
    for ci, c in enumerate(caps):
        r = slice(ci * NLOOP, (ci + 1) * NLOOP)
        X[r, 2 * ci] = 1.0
        X[r, 2 * ci + 1] = np.arange(NLOOP)
        X[r, 2 * nc:] = c["C"]
        y[r] = Ts[c["key"]]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    w = beta[2 * nc:]
    par = {}
    for ci, c in enumerate(caps):
        par[c["key"]] = (beta[2 * ci], beta[2 * ci + 1])
    resid = y - X @ beta
    return list(w), par, float(np.sqrt((resid ** 2).mean()))


def main():
    meta, caps = model.load()
    caps = prepare(caps)
    o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]
    w = [0.0] * 8
    h1, h0 = 750.0, 375.0
    for outer in range(4):
        o, h1, h0, Ts = stageA(caps, o, w, h1, h0, rounds=2 if outer else 4)
        wn, par, rms = stageB(caps, Ts)
        print(f"B{outer}: w={[round(x,2) for x in wn]} "
              f"({[round(x/CY,3) for x in wn]} cy) rms={rms:.1f} ns", flush=True)
        wq = [round(x / CY) * CY for x in wn]
        Tp = {c["key"]: par[c["key"]][0] + par[c["key"]][1] * np.arange(NLOOP)
              + c["C"] @ np.asarray(wq) for c in caps}
        m, n = count(caps, Tp, o, wq, h1, h0)
        print(f"    parametric(w quantised {[int(x/CY) for x in wq]}): "
              f"{100*m/n:.3f}%", flush=True)
        Tp2 = {c["key"]: par[c["key"]][0] + par[c["key"]][1] * np.arange(NLOOP)
               + c["C"] @ np.asarray(wn) for c in caps}
        m2, _ = count(caps, Tp2, o, wn, h1, h0)
        print(f"    parametric(w raw): {100*m2/n:.3f}%", flush=True)
        w = wq
    json.dump({"o": o, "w": w, "h1": h1, "h0": h0,
               "par": {k: [float(a), float(b)] for k, (a, b) in par.items()}},
              open("stage7.json", "w"), indent=1)


if __name__ == "__main__":
    main()
