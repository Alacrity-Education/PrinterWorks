"""Second-stage refinement.

o[] and w[] are searched with the per-capture nuisances frozen (cheap and
valid: they are relative offsets).  G, eff_high_1 and eff_high_0 are
searched WITH a per-capture (t0, eps) refit, because a fixed nuisance set
absorbs them and makes them look like they never help.
"""
import json
import sys
import time

import numpy as np

import fitlib as F
import fit_full as FF
from fit_full import CY, A_of, refit, score


def refit_score(caps, G, o, w, h1, h0, nuis):
    nu = {k: list(v) for k, v in nuis.items()}
    tot = refit(caps, G, o, w, h1, h0, nu, st=5.0, sk=8e-6)
    return tot, nu


def round_once(caps, G, o, w, h1, h0, nuis, step, log):
    N = sum(c["an"] for c in caps)
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
        x = line(o[s] + np.arange(-6, 7) * step,
                 lambda z, s=s: (G, o[:s] + [z] + o[s + 1:], w))
        if x is not None:
            o[s] = x
    for s in range(8):
        x = line(w[s] + np.arange(-6, 7) * step,
                 lambda z, s=s: (G, o, w[:s] + [z] + w[s + 1:]))
        if x is not None:
            w[s] = x
    tot = refit(caps, G, o, w, h1, h0, nuis)

    # G / h1 / h0 with a real refit each
    for name in ("G", "h1", "h0"):
        base = {"G": G, "h1": h1, "h0": h0}[name]
        bx, bv, bn = None, tot, None
        span = step * (0.4 if name == "G" else 1.0)
        for z in base + np.arange(-4, 5) * span:
            if z == base:
                continue
            GG, a, b = (z, h1, h0) if name == "G" else \
                ((G, z, h0) if name == "h1" else (G, h1, z))
            v, nu = refit_score(caps, GG, o, w, a, b, nuis)
            if v > bv:
                bv, bx, bn = v, z, nu
        if bx is not None:
            tot, nuis = bv, bn
            if name == "G":
                G = bx
            elif name == "h1":
                h1 = bx
            else:
                h0 = bx
    log(f"    step={step}: act={100*tot/N:.3f}% G={G:.2f} h1={h1:.2f} "
        f"h0={h0:.2f}\n      o={[round(z,2) for z in o]}\n"
        f"      w={[round(z/CY,3) for z in w]} cy")
    return tot, G, o, w, h1, h0, nuis


def main():
    src, out = sys.argv[1], sys.argv[2]
    st = json.load(open(src))
    G, o, w, h1, h0 = st["G"], list(st["o"]), list(st["w"]), st["h1"], st["h0"]
    nuis = {k: list(v) for k, v in st["nuis"].items()}
    meta, caps = F.load()
    caps = FF.prepare(caps)
    N = sum(c["an"] for c in caps)
    t = time.time()
    tot = refit(caps, G, o, w, h1, h0, nuis)
    print(f"start act={100*tot/N:.3f}%", flush=True)
    best = (tot, G, list(o), list(w), h1, h0,
            {k: list(v) for k, v in nuis.items()})
    for step in (CY, 20.0, 8.0, 3.0, 1.0, 0.3, 0.1):
        for rnd in range(6):
            prev = tot
            tot, G, o, w, h1, h0, nuis = round_once(
                caps, G, o, w, h1, h0, nuis, step,
                lambda s: print(s, flush=True))
            if tot > best[0]:
                best = (tot, G, list(o), list(w), h1, h0,
                        {k: list(v) for k, v in nuis.items()})
            if tot <= prev:
                break
    tot, G, o, w, h1, h0, nuis = best
    # final full re-seed of the nuisances, then one more polish
    tot2, nu2 = FF.seed(caps, G, o, w, h1, h0)
    if tot2 > tot:
        tot, nuis = tot2, {k: list(v) for k, v in nu2.items()}
    print(f"FINAL act={100*tot/N:.3f}%  [{time.time()-t:.0f}s]", flush=True)
    json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot / N,
                   nuis=nuis), open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
