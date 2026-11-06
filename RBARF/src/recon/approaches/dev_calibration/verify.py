"""Final neighbourhood check around the fitted model, each candidate
evaluated with a fresh per-capture (t0, eps) seed."""
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

    def ev(GG, oo, ww, a, b):
        tot, nu = FF.seed(caps, GG, oo, ww, a, b,
                          lo=2500.0, hi=2556.0, step=0.15,
                          t0lo=150.0, t0hi=620.0, t0step=4.0)
        return tot, {k: list(v) for k, v in nu.items()}

    t = time.time()
    tot, nu = ev(G, o, w, h1, h0)
    best = (tot, G, list(o), list(w), h1, h0, nu)
    print(f"base act={100*tot/N:.4f}%  [{time.time()-t:.0f}s]", flush=True)

    cands = []
    for s in range(8):
        for dz in (-CY, CY):
            ww = list(w); ww[s] += dz
            cands.append(("w%d%+g" % (s, dz / CY), G, o, ww, h1, h0))
    for dz in (-8.0, -4.0, -2.0, 2.0, 4.0, 8.0):
        cands.append(("h1%+g" % dz, G, o, w, h1 + dz, h0))
        cands.append(("h0%+g" % dz, G, o, w, h1, h0 + dz))
        cands.append(("both%+g" % dz, G, o, w, h1 + dz, h0 + dz))
    for s in range(1, 8):
        for dz in (-6.0, 6.0):
            oo = [x + (dz if i >= s else 0.0) for i, x in enumerate(o)]
            cands.append(("gap%d%+g" % (s - 1, dz), G, oo, w, h1, h0))
    for dz in (-6.0, 6.0):
        cands.append(("G%+g" % dz, G + dz, o, w, h1, h0))

    for name, GG, oo, ww, a, b in cands:
        v, nn = ev(GG, oo, ww, a, b)
        flag = "  <<<" if v > best[0] else ""
        print(f"  {name:10s} act={100*v/N:.4f}%{flag}  [{time.time()-t:.0f}s]",
              flush=True)
        if v > best[0]:
            best = (v, GG, list(oo), list(ww), a, b, nn)
    tot, G, o, w, h1, h0, nu = best
    print(f"BEST act={100*tot/N:.4f}%", flush=True)
    json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot / N,
                   nuis=nu), open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
