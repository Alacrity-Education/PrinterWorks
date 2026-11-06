"""Vectorised joint fit: global slot offsets o[0..7] + per-capture (phi,k).

t(i,s) = phi + k*(i*2500 + o[s]).  Score = in-frame sample agreement.
"""
import json, sys, time
import numpy as np
import model as M

FRAME_NS = 192 * 1250.0
BIT = 1250.0
THR = np.array([375.0, 750.0])


def prep(D):
    caps = []
    for d in D:
        I = np.array([i for i, s in d["idx"]], dtype=np.float64)
        S = np.array([s for i, s in d["idx"]], dtype=np.int64)
        obs = np.array(d["obs"], dtype=np.int8)
        bits = np.array(d["bits"], dtype=np.int64)
        caps.append(dict(I=I, S=S, obs=obs, bits=bits,
                         name=f"{d['pattern']}_{d['rep']}"))
    return caps


def agree(c, o, k, phi):
    t = phi + k * (c["I"] * 2500.0 + o[c["S"]])
    m = (t >= 0) & (t < FRAME_NS)
    tt = t[m]
    kk = (tt // BIT).astype(np.int64)
    u = tt - kk * BIT
    pred = (u < THR[c["bits"][kk]]).astype(np.int8)
    return int((pred == c["obs"][m]).sum()), int(m.sum())


def agree_grid(c, o, ks, phis):
    """returns array [len(ks), len(phis)] of match counts."""
    base = c["I"] * 2500.0 + o[c["S"]]
    out = np.zeros((len(ks), len(phis)), dtype=np.int32)
    for a, k in enumerate(ks):
        tb = k * base
        for b, phi in enumerate(phis):
            t = tb + phi
            m = (t >= 0) & (t < FRAME_NS)
            tt = t[m]
            kk = (tt // BIT).astype(np.int64)
            u = tt - kk * BIT
            pred = (u < THR[c["bits"][kk]]).astype(np.int8)
            out[a, b] = (pred == c["obs"][m]).sum()
    return out


def fit_cap(c, o, coarse=True, phi0=0.0, k0=1.0):
    if coarse:
        ks = np.arange(0.985, 1.0201, 0.0004)
        phis = np.arange(-700.0, 700.0, 10.0)
        g = agree_grid(c, o, ks, phis)
        a, b = np.unravel_index(g.argmax(), g.shape)
        best = (int(g[a, b]), float(phis[b]), float(ks[a]))
    else:
        best = (agree(c, o, k0, phi0)[0], phi0, k0)
    for sp, sk in ((4.0, 1.5e-4), (1.5, 5e-5), (0.5, 1.5e-5), (0.2, 5e-6)):
        ks = np.array([best[2] + j * sk for j in range(-3, 4)])
        phis = np.array([best[1] + j * sp for j in range(-3, 4)])
        for _ in range(6):
            g = agree_grid(c, o, ks, phis)
            a, b = np.unravel_index(g.argmax(), g.shape)
            if int(g[a, b]) <= best[0]:
                break
            best = (int(g[a, b]), float(phis[b]), float(ks[a]))
            ks = np.array([best[2] + j * sk for j in range(-3, 4)])
            phis = np.array([best[1] + j * sp for j in range(-3, 4)])
    return best


def totscore(caps, o, nuis):
    ok = n = 0
    for c, (_, phi, k) in zip(caps, nuis):
        a, b = agree(c, o, k, phi)
        ok += a; n += b
    return ok, n


def main():
    meta, D = M.load()
    caps = prep(D)
    o = np.array(M.O_NOM, dtype=np.float64)
    t0 = time.time()
    nuis = [fit_cap(c, o) for c in caps]
    print("start", totscore(caps, o, nuis), f"{time.time()-t0:.0f}s")

    for rnd in range(8):
        step = [80, 40, 20, 10, 6, 4, 2, 1][rnd]
        for s in range(8):
            base = o[s]
            best = (totscore(caps, o, nuis)[0], base)
            for d in range(-6, 7):
                if d == 0:
                    continue
                o2 = o.copy(); o2[s] = base + d * step
                if not (-100 < o2[s] < 2600):
                    continue
                a = totscore(caps, o2, nuis)[0]
                if a > best[0]:
                    best = (a, o2[s])
            o[s] = best[1]
        nuis = [fit_cap(c, o, coarse=False, phi0=p, k0=k) for c, (_, p, k) in zip(caps, nuis)]
        ok, n = totscore(caps, o, nuis)
        print(f"r{rnd} step={step:3d}: {ok}/{n}={ok/n:.4f} o={np.round(o,1).tolist()} ({time.time()-t0:.0f}s)")

    json.dump({"o": o.tolist(), "nuis": [[p, k] for _, p, k in nuis],
               "caps": [c["name"] for c in caps]}, open("nfit.json", "w"), indent=1)
    for c, (m, p, k) in zip(caps, nuis):
        a, n = agree(c, o, k, p)
        print(f"  {c['name']:14s} {a}/{n}={a/n:.3f} phi={p:8.1f} k={k:.5f} loop={k*2500:.1f}")


if __name__ == "__main__":
    main()
