"""E3: global fine-grid calibration -- G, P[1..7], h1, h0 -- with warm
per-capture (t0, kappa).  Uses only the in-frame window."""
import json

import numpy as np

from common import load
from mf import corr_grid, refine

NW = 900
meta, caps = load()
for c in caps:
    c["it"] = c["it"][:NW].astype(float)
    c["sl"] = c["sl"][:NW]
    c["lv"] = c["lv"][:NW]

G = 40.0
P = [0., 4., 8., 12., 16., 20., 26., 31.]
h1, h0 = 750.0, 375.0
warm = {}


def ph(c, G, P):
    return c["it"] * G + np.asarray(P)[c["sl"]]


def total(G, P, h1, h0, coarse=False, save=True):
    tot = 0
    for c in caps:
        u = ph(c, G, P)
        if coarse or c["key"] not in warm:
            Gr = corr_grid(u, c["lv"], c["bits"],
                           np.arange(-300., 420., 4.), np.arange(61.0, 64.5, 0.005),
                           h1, h0)
            a, b = np.unravel_index(np.argmax(Gr), Gr.shape)
            t0, k = -300. + 4. * a, 61.0 + 0.005 * b
        else:
            t0, k = warm[c["key"]]
        m, t0, k = refine(u, c["lv"], c["bits"], t0, k, h1, h0, st=6.0, sk=0.03)
        if save:
            warm[c["key"]] = (t0, k)
        tot += m
    return tot


N = NW * len(caps)
tot = total(G, P, h1, h0, coarse=True)
print(f"seed {100*tot/N:.4f}%", flush=True)

for step in (1.0, 0.5, 0.25, 0.1):
    for rnd in range(5):
        prev = tot
        for s in range(1, 8):
            cur = P[s]
            best = (tot, cur)
            for v in np.arange(cur - 3 * step, cur + 3 * step + 1e-9, step):
                t = total(G, P[:s] + [float(v)] + P[s + 1:], h1, h0, save=False)
                if t > best[0]:
                    best = (t, float(v))
            P[s] = best[1]
            tot = total(G, P, h1, h0)
        cur = G
        best = (tot, cur)
        for v in np.arange(cur - 3 * step, cur + 3 * step + 1e-9, step):
            t = total(float(v), P, h1, h0, save=False)
            if t > best[0]:
                best = (t, float(v))
        G = best[1]
        tot = total(G, P, h1, h0)
        for nm in ("h1", "h0"):
            cur = h1 if nm == "h1" else h0
            best = (tot, cur)
            for v in np.arange(cur - 40, cur + 40.1, 10 * step):
                t = total(G, P, v if nm == "h1" else h1,
                          h0 if nm == "h1" else v, save=False)
                if t > best[0]:
                    best = (t, float(v))
            if nm == "h1":
                h1 = best[1]
            else:
                h0 = best[1]
            tot = total(G, P, h1, h0)
        print(f" step={step} r{rnd}: {100*tot/N:.4f}% G={G:.3f} "
              f"P={[round(x,3) for x in P]} h1={h1:.1f} h0={h0:.1f}", flush=True)
        if tot <= prev:
            break

print(f"FINAL {100*tot/N:.4f}% G={G} P={P} h1={h1} h0={h0}")
gaps = [P[i + 1] - P[i] for i in range(7)] + [G - P[7]]
print("gaps(cy) =", [round(x, 3) for x in gaps])
out = {}
for c in caps:
    u = ph(c, G, P)
    t0, k = warm[c["key"]]
    m, t0, k = refine(u, c["lv"], c["bits"], t0, k, h1, h0, st=4.0, sk=0.02)
    out[c["key"]] = (t0, k, m)
    print(f"  {c['key']:14s} t0={t0:8.2f} kap={k:.4f} loop={G*k:8.2f} miss={NW-m}")
json.dump({"G": G, "P": P, "h1": h1, "h0": h0, "NW": NW,
           "res": {k: list(v) for k, v in out.items()}},
          open("e3_globalfit.json", "w"), indent=1)
