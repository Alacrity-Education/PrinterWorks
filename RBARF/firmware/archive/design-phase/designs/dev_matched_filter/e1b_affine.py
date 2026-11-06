"""E1b: pure-affine fine-grid time base.

    t(i,s) = t0 + kappa * ( i*G + p[s] )      p[0] = 0

Global: G (cycles), p[1..7] (cycles), h1, h0 (ns).
Per capture: t0 (ns), kappa (ns/cycle).
Objective: sample-level agreement on the in-frame window (n < NW).
"""
import json

import numpy as np

from common import load, wire

NW = 1024
meta, caps = load()
for c in caps:
    c["it"] = c["it"][:NW].astype(float)
    c["sl"] = c["sl"][:NW]
    c["lv"] = c["lv"][:NW]
    c["n"] = NW

G = 40.0
p = [0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 26.0, 31.0]
h1, h0 = 750.0, 375.0
state = {}


def Aof(c, G, p):
    return c["it"] * G + np.asarray(p)[c["sl"]]


def best_t0k(c, A, h1, h0, t0c=None, kc=None):
    lv, bits = c["lv"], c["bits"]
    if t0c is None:
        ks = np.arange(56.0, 70.0, 0.02)
        t0s = np.arange(-300.0, 400.0, 6.0)
    else:
        ks = np.arange(kc - 0.6, kc + 0.6, 0.01)
        t0s = np.arange(t0c - 60, t0c + 60, 3.0)
    best = (-1, 0.0, 62.5)
    for k in ks:
        base = k * A
        for t0 in t0s:
            m = int(np.count_nonzero(wire(t0 + base, bits, h1, h0) == lv))
            if m > best[0]:
                best = (m, t0, k)
    m, t0, k = best
    st, sk = 3.0, 0.01
    while st > 1e-3:
        found = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = int(np.count_nonzero(
                wire(t0 + a + (k + b) * A, bits, h1, h0) == lv))
            if mm > m:
                m, found = mm, (t0 + a, k + b)
        if found is None:
            st /= 2
            sk /= 2
        else:
            t0, k = found
    return m, t0, k


def total(G, p, h1, h0, coarse=False):
    tot = 0
    for c in caps:
        A = Aof(c, G, p)
        st = state.get(c["key"])
        if coarse or st is None:
            m, t0, k = best_t0k(c, A, h1, h0)
        else:
            m, t0, k = best_t0k(c, A, h1, h0, st[0], st[1])
        state[c["key"]] = (t0, k, m)
        tot += m
    return tot


N = NW * len(caps)
tot = total(G, p, h1, h0, coarse=True)
print(f"seed: {100*tot/N:.4f}%", flush=True)

for step in (1.0, 0.5, 0.25, 0.125):
    for rnd in range(6):
        prev = tot
        for s in range(1, 8):
            base = p[s]
            best = (tot, base)
            for v in np.arange(base - 3 * step, base + 3 * step + 1e-9, step):
                t = total(G, p[:s] + [float(v)] + p[s + 1:], h1, h0)
                if t > best[0]:
                    best = (t, float(v))
            p[s] = best[1]
        best = (tot, G)
        for v in np.arange(G - 3 * step, G + 3 * step + 1e-9, step):
            t = total(float(v), p, h1, h0)
            if t > best[0]:
                best = (t, float(v))
        G = best[1]
        for nm in ("h1", "h0"):
            cur = h1 if nm == "h1" else h0
            best = (tot, cur)
            for v in np.arange(cur - 30, cur + 30.1, 10.0 * step):
                t = total(G, p, v if nm == "h1" else h1,
                          h0 if nm == "h1" else v)
                if t > best[0]:
                    best = (t, float(v))
            if nm == "h1":
                h1 = best[1]
            else:
                h0 = best[1]
        tot = total(G, p, h1, h0)
        print(f" step={step} rnd={rnd}: {100*tot/N:.4f}% G={G} "
              f"p={[round(x,3) for x in p]} h1={h1} h0={h0}", flush=True)
        if tot <= prev:
            break

tot = total(G, p, h1, h0)
print(f"FINAL {100*tot/N:.4f}%  G={G} p={p} h1={h1} h0={h0}")
ks = np.array([state[c["key"]][1] for c in caps])
print("kappa ns/cy: %.4f..%.4f med %.4f -> loop_ns %.2f..%.2f"
      % (ks.min(), ks.max(), np.median(ks), ks.min() * G, ks.max() * G))
for c in caps:
    t0, k, m = state[c["key"]]
    print(f"  {c['key']:14s} t0={t0:8.2f} kap={k:.4f} loop={k*G:8.2f} "
          f"agree={m}/{NW} miss={NW-m}")
json.dump({"G": G, "p": p, "h1": h1, "h0": h0, "NW": NW,
           "state": {k: list(v) for k, v in state.items()}},
          open("e1b_affine.json", "w"), indent=1)
