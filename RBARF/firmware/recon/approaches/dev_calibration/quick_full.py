"""Descend straight from the best-known integer seed."""
import json, sys, time
import numpy as np
import fitlib as F, fit_full as FF
from fit_full import CY
from run_full import layout

out = sys.argv[1]
extra = [int(x) for x in sys.argv[2].split(',')]
w0 = [int(x) for x in sys.argv[3].split(',')]
meta, caps = F.load(); caps = FF.prepare(caps)
N = sum(c["an"] for c in caps)
o, G = layout(extra)
w = [x * CY for x in w0]
t = time.time()
tot, nuis = FF.seed(caps, G, o, w, 750.0, 375.0)
print(f"seed act={100*tot/N:.3f}% [{time.time()-t:.0f}s]", flush=True)
res = FF.descend(caps, G, list(o), list(w), 750.0, 375.0,
                 {k: list(v) for k, v in nuis.items()},
                 steps=[CY, CY/2, 12.0, 4.0, 1.0, 0.25],
                 log=lambda s: print(s, flush=True))
tot, G, o, w, h1, h0, nuis = res
print(f"FINAL act={100*tot/N:.3f}% [{time.time()-t:.0f}s]", flush=True)
json.dump(dict(G=G, o=list(o), w=list(w), h1=h1, h0=h0, act=tot/N, nuis=nuis),
          open(out, "w"), indent=1)
