"""Seed from several integer-cycle layouts, descend, keep the best."""
import itertools
import json
import sys
import time

import numpy as np

import fitlib as F
import fit_full as FF
from fit_full import CY

BASE = np.array([4, 4, 4, 4, 4, 6, 5, 6])


def layout(extra):
    g = (BASE + np.array(extra)).astype(float) * CY
    return list(np.concatenate([[0.0], np.cumsum(g)[:-1]])), float(g.sum())


def main():
    out = sys.argv[1]
    meta, caps = F.load()
    caps = FF.prepare(caps)
    N = sum(c["an"] for c in caps)
    seeds = []
    for extra in ([0, 0, 0, 0, 0, 0, 0, 3], [0, 0, 0, 0, 0, 1, 1, 1],
                  [0, 0, 0, 0, 0, 3, 0, 0], [0, 0, 0, 0, 0, 2, 0, 1],
                  [0, 0, 0, 0, 0, 0, 0, 4], [0, 0, 0, 0, 0, 1, 1, 2]):
        for w0 in ([0, -1, 0, 1, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0],
                   [0, -1, 0, 2, 0, 0, 0, 1], [-1, -1, -1, -1, -1, -1, -1, -1],
                   [1, 1, 1, 1, 1, 1, 1, 1]):
            seeds.append((extra, w0))
    best = None
    t = time.time()
    for extra, w0 in seeds:
        o, G = layout(extra)
        w = [x * CY for x in w0]
        tot, nuis = FF.seed(caps, G, o, w, 750.0, 375.0)
        print(f"seed extra={extra} w={w0}: act={100*tot/N:.3f}% "
              f"[{time.time()-t:.0f}s]", flush=True)
        if best is None or tot > best[0]:
            best = (tot, G, o, w, 750.0, 375.0,
                    {k: list(v) for k, v in nuis.items()})
    print(f"BEST SEED act={100*best[0]/N:.3f}%", flush=True)
    tot, G, o, w, h1, h0, nuis = best
    res = FF.descend(caps, G, list(o), list(w), h1, h0, nuis,
                     steps=[CY, CY / 2, 12.0, 4.0, 1.0, 0.25],
                     log=lambda s: print(s, flush=True))
    tot, G, o, w, h1, h0, nuis = res
    print(f"FINAL act={100*tot/N:.3f}%  [{time.time()-t:.0f}s]", flush=True)
    json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot / N,
                   nuis=nuis), open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
