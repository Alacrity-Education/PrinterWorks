"""Scan the paired move (gamma_s += n cycles, w_s -= n cycles): keeps the
HIGH-read gap at slot s fixed and changes only the LOW-read gap."""
import json, sys, time
import numpy as np
import fitlib as F, fit_full as FF
from fit_full import CY

st = json.load(open(sys.argv[1]))
G, o, w, h1, h0 = st["G"], list(st["o"]), list(st["w"]), st["h1"], st["h0"]
meta, caps = F.load(); caps = FF.prepare(caps)
N = sum(c["an"] for c in caps)

def gaps_of(o, G):
    return list(np.diff(list(o) + [G]))

def from_gaps(g):
    g = np.asarray(g, float)
    return list(np.concatenate([[0.0], np.cumsum(g)[:-1]])), float(g.sum())

def ev(o, G, w):
    tot, nu = FF.seed(caps, G, o, w, h1, h0, lo=2380.0, hi=2620.0, step=0.4)
    return tot, nu

g0 = gaps_of(o, G)
base, nu0 = ev(o, G, w)
print(f"base gaps={[round(x/CY,2) for x in g0]} w={[round(x/CY,2) for x in w]}"
      f" act={100*base/N:.3f}%", flush=True)
best = (base, list(o), G, list(w), nu0)
t = time.time()
for s in range(8):
    for n in (-2, -1, 1, 2):
        g = list(g0); g[s] += n * CY
        ww = list(w); ww[s] -= n * CY
        oo, GG = from_gaps(g)
        tot, nu = ev(oo, GG, ww)
        print(f"  s={s} n={n:+d}: gaps={[round(x/CY,2) for x in g]} "
              f"w={[round(x/CY,2) for x in ww]} act={100*tot/N:.3f}% "
              f"[{time.time()-t:.0f}s]", flush=True)
        if tot > best[0]:
            best = (tot, oo, GG, ww, nu)
tot, o, G, w, nu = best
print(f"BEST act={100*tot/N:.3f}%", flush=True)
json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot/N,
               nuis={k: list(v) for k, v in nu.items()}),
          open(sys.argv[2], "w"), indent=1)
