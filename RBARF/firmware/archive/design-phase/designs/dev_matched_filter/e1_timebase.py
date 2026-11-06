"""E1: fit the mechanistic gap vector g[0..7] + (h1,h0) globally,
(t0, kappa) per capture. Establishes the fine-grid sample-time model the
matched filter runs on."""
import itertools
import json

import numpy as np

from common import load, cycles, fit_t0k, agree

meta, caps = load()
N = sum(c["n"] for c in caps)

# start from documented gaps with the 3 unaccounted cycles in the end gap
g = [4, 4, 4, 4, 4, 6, 5, 9]
h1, h0 = 750.0, 375.0

state = {}


def total(g, h1, h0, refit=True):
    tot = 0
    for c in caps:
        u = cycles(c["sl"], c["lv"], g)
        if refit or c["key"] not in state:
            m, t0, k = fit_t0k(u, c["lv"], c["bits"], h1, h0)
        else:
            t0, k = state[c["key"]][:2]
            m, t0, k = polish(u, c, h1, h0, t0, k)
        state[c["key"]] = (t0, k, m)
        tot += m
    return tot


def polish(u, c, h1, h0, t0, k, st=20.0, sk=0.02):
    m = agree(u, c["lv"], c["bits"], t0, k, h1, h0)
    while st > 1e-3:
        found = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = agree(u, c["lv"], c["bits"], t0 + a, k + b, h1, h0)
            if mm > m:
                m, found = mm, (t0 + a, k + b)
        if found is None:
            st /= 2
            sk /= 2
        else:
            t0, k = found
    return m, t0, k


tot = total(g, h1, h0, refit=True)
print(f"seed g={g} h1={h1} h0={h0}: {100*tot/N:.4f}%", flush=True)

for step in (1.0, 0.5, 0.25):
    for rnd in range(8):
        prev = tot
        for s in range(8):
            best = (tot, g[s])
            for v in np.arange(g[s] - 3 * step, g[s] + 3 * step + 1e-9, step):
                gg = g[:s] + [float(v)] + g[s + 1:]
                t = total(gg, h1, h0, refit=False)
                if t > best[0]:
                    best = (t, float(v))
            g[s] = best[1]
            tot = total(g, h1, h0, refit=False)
        for name in ("h1", "h0"):
            cur = h1 if name == "h1" else h0
            best = (tot, cur)
            for v in np.arange(cur - 40, cur + 40.1, 5.0):
                t = total(g, v if name == "h1" else h1,
                          h0 if name == "h1" else v, refit=False)
                if t > best[0]:
                    best = (t, float(v))
            if name == "h1":
                h1 = best[1]
            else:
                h0 = best[1]
            tot = total(g, h1, h0, refit=False)
        print(f"  step={step} rnd={rnd}: {100*tot/N:.4f}% g={g} h1={h1} h0={h0}",
              flush=True)
        if tot <= prev:
            break

tot = total(g, h1, h0, refit=True)
print(f"FINAL {100*tot/N:.4f}% g={g} h1={h1} h0={h0}")
loop_cy = sum(g)
print("loop cycles (all-low) =", loop_cy)
ks = [state[c['key']][1] for c in caps]
print("kappa ns/cycle: min %.4f med %.4f max %.4f  -> f_HSI %.4f..%.4f MHz"
      % (min(ks), float(np.median(ks)), max(ks), 1000/max(ks), 1000/min(ks)))
for c in caps:
    t0, k, m = state[c["key"]]
    print(f"  {c['key']:14s} t0={t0:8.2f} kap={k:.4f} loop_ns={k*loop_cy:8.2f} "
          f"agree={m}/{c['n']} ({100*m/c['n']:.2f}%)")

json.dump({"g": g, "h1": h1, "h0": h0,
           "state": {k: list(v) for k, v in state.items()}},
          open("e1_timebase.json", "w"), indent=1)
