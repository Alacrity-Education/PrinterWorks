"""E2: oracle (t0, kappa) per capture from the FULL known frame, on the
nominal fine grid.  Establishes the reference against which header-only /
trailer-only / joint anchors are measured."""
import json

import numpy as np

from common import load
from mf import phase, corr_grid, refine

NW = 900
H1, H0 = 750.0, 375.0

meta, caps = load()
t0s = np.arange(-250.0, 400.0, 4.0)
ks = np.arange(61.6, 64.2, 0.005)

res = {}
for c in caps:
    it, sl, lv = c["it"][:NW], c["sl"][:NW], c["lv"][:NW]
    u = phase(it, sl)
    Gr = corr_grid(u, lv, c["bits"], t0s, ks, H1, H0)
    a, b = np.unravel_index(np.argmax(Gr), Gr.shape)
    m, t0, k = refine(u, lv, c["bits"], t0s[a], ks[b], H1, H0)
    res[c["key"]] = (t0, k, m, NW)
    print(f"{c['key']:14s} t0={t0:8.2f} kap={k:.4f} loop={40*k:8.2f} "
          f"agree={m}/{NW} miss={NW-m}", flush=True)

ks_ = np.array([v[1] for v in res.values()])
print("kappa %.4f..%.4f med %.4f | loop_ns %.2f..%.2f med %.2f"
      % (ks_.min(), ks_.max(), np.median(ks_),
         40 * ks_.min(), 40 * ks_.max(), 40 * np.median(ks_)))
miss = np.array([v[3] - v[2] for v in res.values()])
print("miss per capture: min %d med %d max %d" % (miss.min(), int(np.median(miss)), miss.max()))
json.dump({"H1": H1, "H0": H0, "NW": NW, "res": {k: list(v) for k, v in res.items()}},
          open("e2_oracle.json", "w"), indent=1)
