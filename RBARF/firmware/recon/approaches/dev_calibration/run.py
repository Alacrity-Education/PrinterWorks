"""Multi-start joint calibration: globals (G, o[1..7], d, h1, h0) by
coordinate descent, per-capture (t0, k) refit every round.

usage: python3 run.py <out.json> [d0 d1 d2 ...]
"""
import json
import sys
import time

import numpy as np

import fitlib as F

CY = 62.5
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)


def seed_nuis(caps, o, G, d, h1, h0, loop_lo=2470.0, loop_hi=2545.0, step=0.5):
    nuis = {}
    ks = np.arange(loop_lo, loop_hi, step) / G
    t0s = np.arange(-350.0, 500.0, 10.0)
    for c in caps:
        A = F.A_of(c, o, G, d)
        B = F.edges_of(c["bits"], h1, h0)
        v, t0, k, m = F.fit_tk_grid(A, B, c["alv"], t0s, ks)
        v, m, t0, k = F.polish_tk(A, B, c["alv"], t0, k)
        nuis[c["key"]] = (t0, k, m)
    return nuis


def descend(caps, o, G, d, h1, h0, nuis, rounds=14, log=print):
    N = sum(c["an"] for c in caps)
    v, m, _ = F.evaluate(caps, o, G, d, h1, h0, nuis)
    best = (v, m, list(o), G, d, h1, h0)
    for phase, step in enumerate([16.0, 6.0, 2.0, 0.6, 0.2, 0.06]):
        for rnd in range(rounds):
            prev = v

            def line(vals, setter):
                nonlocal v, m
                bv, bx = v, None
                for x in vals:
                    oo, GG, dd, a, b = setter(x)
                    vv, mm, _ = F.evaluate(caps, oo, GG, dd, a, b, nuis,
                                           refit=False)
                    if vv > bv:
                        bv, bx = vv, x
                if bx is not None:
                    v = bv
                return bx

            for s in range(1, 8):
                x = line(o[s] + np.arange(-8, 9) * step,
                         lambda z, s=s: (o[:s] + [z] + o[s + 1:], G, d, h1, h0))
                if x is not None:
                    o[s] = x
            x = line(G + np.arange(-8, 9) * step * 0.25,
                     lambda z: (o, z, d, h1, h0))
            if x is not None:
                G = x
            x = line(d + np.arange(-8, 9) * step * 0.5,
                     lambda z: (o, G, z, h1, h0))
            if x is not None:
                d = x
            x = line(h1 + np.arange(-8, 9) * step,
                     lambda z: (o, G, d, z, h0))
            if x is not None:
                h1 = x
            x = line(h0 + np.arange(-8, 9) * step,
                     lambda z: (o, G, d, h1, z))
            if x is not None:
                h0 = x
            v, m, _ = F.evaluate(caps, o, G, d, h1, h0, nuis)
            if v > best[0]:
                best = (v, m, list(o), G, d, h1, h0)
            log(f"  p{phase} r{rnd}: act={100*m/N:.3f}%  G={G:.2f} d={d:.2f} "
                f"h1={h1:.1f} h0={h0:.1f} o={[round(z,1) for z in o]}")
            if v <= prev + 1e-9:
                break
    return best


def main():
    out = sys.argv[1]
    ds = [float(x) for x in sys.argv[2:]] or [62.5]
    meta, caps = F.load()
    N = sum(c["an"] for c in caps)
    results = []
    for d in ds:
        t = time.time()
        G0 = 2507.3 + d * 5.0
        o0 = list(DOC * G0 / 37.0)
        o0[0] = 62.5
        nuis = seed_nuis(caps, o0, G0, d, 750.0, 375.0)
        v, m, _ = F.evaluate(caps, o0, G0, d, 750.0, 375.0, nuis)
        print(f"d0={d}: seed act={100*m/N:.3f}%  [{time.time()-t:.0f}s]",
              flush=True)
        best = descend(caps, o0, G0, d, 750.0, 375.0, nuis,
                       log=lambda s: print(s, flush=True))
        v, m, oo, G, dd, h1, h0 = best
        print(f"d0={d}: FINAL act={100*m/N:.3f}%  G={G:.3f} d={dd:.3f} "
              f"h1={h1:.2f} h0={h0:.2f}  [{time.time()-t:.0f}s]", flush=True)
        results.append(dict(d0=d, act=m / N, o=oo, G=G, d=dd, h1=h1, h0=h0,
                            nuis={k: list(v2) for k, v2 in nuis.items()}))
    results.sort(key=lambda r: -r["act"])
    json.dump(results, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
