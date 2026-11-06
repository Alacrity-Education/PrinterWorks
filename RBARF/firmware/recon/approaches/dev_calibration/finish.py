"""Final fine polish: individual slot offsets, whole-gap shifts, G, and the
two effective high widths -- the last three with a per-capture (t0, eps)
refit at every candidate, since a frozen nuisance set hides them."""
import json
import sys
import time

import numpy as np

import fitlib as F
import fit_full as FF
from fit_full import CY


def main():
    src, out = sys.argv[1], sys.argv[2]
    st = json.load(open(src))
    G, o, w, h1, h0 = st["G"], list(st["o"]), list(st["w"]), st["h1"], st["h0"]
    meta, caps = F.load()
    caps = FF.prepare(caps)
    N = sum(c["an"] for c in caps)
    t = time.time()
    tot, nuis = FF.seed(caps, G, o, w, h1, h0, lo=2380.0, hi=2620.0, step=0.4)
    nuis = {k: list(v) for k, v in nuis.items()}
    print(f"reseed act={100*tot/N:.3f}%  [{time.time()-t:.0f}s]", flush=True)
    best = (tot, G, list(o), list(w), h1, h0,
            {k: list(v) for k, v in nuis.items()})

    def refit_ev(GG, oo, ww, a, b, nu):
        n2 = {k: list(v) for k, v in nu.items()}
        return FF.refit(caps, GG, oo, ww, a, b, n2), n2

    for step in (10.0, 4.0, 1.5, 0.5, 0.15):
        for rnd in range(5):
            prev = tot
            Bs = {c["key"]: F.edges_of(c["bits"], h1, h0) for c in caps}
            cur = FF.score(caps, G, o, w, h1, h0, nuis, Bs)
            # single slot offsets
            for s in range(1, 8):
                bx, bv = None, cur
                for z in o[s] + np.arange(-6, 7) * step:
                    oo = o[:s] + [z] + o[s + 1:]
                    v = FF.score(caps, G, oo, w, h1, h0, nuis, Bs)
                    if v > bv:
                        bv, bx = v, z
                if bx is not None:
                    o[s], cur = bx, bv
            # whole-gap shifts: move o[s:] together
            for s in range(1, 8):
                bx, bv = None, cur
                for dz in np.arange(-6, 7) * step:
                    if dz == 0:
                        continue
                    oo = [x + (dz if i >= s else 0.0) for i, x in enumerate(o)]
                    v = FF.score(caps, G, oo, w, h1, h0, nuis, Bs)
                    if v > bv:
                        bv, bx = v, dz
                if bx is not None:
                    o = [x + (bx if i >= s else 0.0) for i, x in enumerate(o)]
                    cur = bv
            tot = FF.refit(caps, G, o, w, h1, h0, nuis)
            # G / h1 / h0 with refit
            for name in ("G", "h1", "h0"):
                base = {"G": G, "h1": h1, "h0": h0}[name]
                bx, bn, bv = None, None, tot
                for z in base + np.arange(-5, 6) * step:
                    if z == base:
                        continue
                    GG, a, b = ((z, h1, h0) if name == "G" else
                                ((G, z, h0) if name == "h1" else (G, h1, z)))
                    v, nu = refit_ev(GG, o, w, a, b, nuis)
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
            if tot > best[0]:
                best = (tot, G, list(o), list(w), h1, h0,
                        {k: list(v) for k, v in nuis.items()})
            print(f"  step={step} r{rnd}: act={100*tot/N:.3f}% G={G:.2f} "
                  f"h1={h1:.2f} h0={h0:.2f} o={[round(z,2) for z in o]} "
                  f"[{time.time()-t:.0f}s]", flush=True)
            if tot <= prev:
                break
    tot, G, o, w, h1, h0, nuis = best
    print(f"FINAL act={100*tot/N:.3f}%  [{time.time()-t:.0f}s]", flush=True)
    json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot / N,
                   nuis=nuis), open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
