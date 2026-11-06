"""Is the loop period identifiable, and is it 2499.8 or harness' 2507.3?

exp13 showed that with per-capture-FREE slot offsets the rising-edge-only
problem is exactly degenerate at L = 2*BIT (zero crawl).  Here we use the
full SAMPLE-LEVEL likelihood (every sample, not just rises), with

    t(i,s) = phi_c + i*L + o[s]        o[] GLOBAL (8 params, o[0]=0)
    phi_c  per capture

and scan the shared L.  At each L we alternately optimise o[] (global)
and phi_c (per capture) to maximise the number of samples whose predicted
level matches.  A sharp peak => L identifiable.
"""
import numpy as np
from common import load_all, wave, BIT_NS

NFR = 100 * 8          # only the first 100 loops carry the frame


def prep(caps):
    out = []
    for c in caps:
        m = c["it"] < 100
        out.append(dict(it=c["it"][m].astype(float), slot=c["slot"][m],
                        lev=c["lev"][m], bits=c["bits"]))
    return out


def match(c, phi, L, o):
    t = phi + c["it"] * L + o[c["slot"]]
    return int((wave(c["bits"], t) == c["lev"]).sum())


def best_phi(c, L, o, phis):
    sc = [match(c, p, L, o) for p in phis]
    j = int(np.argmax(sc))
    return phis[j], sc[j]


def evaluate(cs, L, o0, rounds=4):
    o = o0.copy()
    phis0 = np.arange(-1250.0, 1250.0, 10.0)
    phi = [best_phi(c, L, o, phis0)[0] for c in cs]
    tot = 0
    for r in range(rounds):
        step = 40.0 if r < 2 else 8.0
        for j in range(1, 8):
            cand = o[j] + np.linspace(-step, step, 9)
            bv, bc = -1, o[j]
            for v in cand:
                oo = o.copy(); oo[j] = v
                s = sum(match(c, p, L, oo) for c, p in zip(cs, phi))
                if s > bv: bv, bc = s, v
            o[j] = bc
        tot = 0
        for i, c in enumerate(cs):
            p, s = best_phi(c, L, o, phi[i] + np.linspace(-60, 60, 25))
            phi[i] = p; tot += s
    return tot, o, phi


if __name__ == "__main__":
    meta, caps = load_all()
    cs = prep(caps)
    N = sum(len(c["lev"]) for c in cs)
    o0 = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * 62.5
    o0 = o0 - o0[0]
    print(f"total samples in frame window: {N}")
    print(f"{'L':>8s} {'match':>7s} {'frac':>8s}  slot offsets (ns, o[0]=0)")
    prof = []
    for L in (2480., 2490., 2495., 2497.5, 2499.8, 2502.5, 2505., 2507.3,
              2510., 2515., 2520.):
        tot, o, phi = evaluate(cs, L, o0)
        prof.append((L, tot))
        print(f"{L:8.1f} {tot:7d} {tot/N:8.4%}  {np.round(o,1).tolist()}")
    prof = np.array(prof)
    k = int(np.argmax(prof[:, 1]))
    print(f"\nbest L on this grid: {prof[k,0]:.1f} ({prof[k,1]/N:.4%})")
