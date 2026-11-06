"""E7: global fine-grid slot calibration with an honest per-capture global
(t0, kappa) scan every time (no warm starts, no local optima).

Model:  t(i,s) = t0 + kappa * ( i*G + P[s] ),  G = 40 cycles fixed
        wire:   '1' high for h1 ns, '0' high for h0 ns, bit = 1250 ns
"""
import json
import sys

import numpy as np

from common import load
from mf import wire_from_bits

NW = 800
T0S = np.arange(0.0, 460.0, 4.0)      # edge-trigger prior: t(0,0) in [0, 460)
KS = np.arange(61.9, 63.2, 0.004)

meta, caps = load()
SUB = [c for c in caps if c["rep"] == 0]     # fit on rep 0; rep 1/2 held out
for c in SUB:
    c["itf"] = c["it"][:NW].astype(float)
    c["slf"] = c["sl"][:NW]
    c["lvb"] = c["lv"][:NW].astype(bool)


def best_cap(c, G, P, h1, h0):
    u = c["itf"] * G + P[c["slf"]]
    bits = c["bits"]
    lv = c["lvb"]
    bm = -1
    bt = bk = 0.0
    for k in KS:
        T = T0S[:, None] + k * u[None, :]
        s = (wire_from_bits(T, bits, h1, h0) == lv[None, :]).sum(1)
        j = int(np.argmax(s))
        if s[j] > bm:
            bm, bt, bk = int(s[j]), T0S[j], k
    return bm, bt, bk


def total(G, P, h1, h0, detail=False):
    P = np.asarray(P, float)
    tot = 0
    det = {}
    for c in SUB:
        m, t0, k = best_cap(c, G, P, h1, h0)
        tot += m
        det[c["key"]] = (t0, k, m)
    return (tot, det) if detail else tot


def main():
    G = 40.0
    P = [0., 4., 8., 12., 16., 20., 26., 31.]
    h1, h0 = 750.0, 375.0
    N = NW * len(SUB)
    tot = total(G, P, h1, h0)
    print(f"seed {100*tot/N:.3f}%", flush=True)
    for step in (1.0, 0.5, 0.25, 0.125):
        for rnd in range(4):
            prev = tot
            for s in range(1, 8):
                cur = P[s]
                best = (tot, cur)
                for v in np.arange(cur - 2 * step, cur + 2 * step + 1e-9, step):
                    if abs(v - cur) < 1e-9:
                        continue
                    t = total(G, P[:s] + [float(v)] + P[s + 1:], h1, h0)
                    if t > best[0]:
                        best = (t, float(v))
                P[s] = best[1]
                tot = best[0]
                print(f"   P{s}={P[s]:.3f} -> {100*tot/N:.3f}%", flush=True)
            for nm, rng in (("h1", 25.0), ("h0", 35.0)):
                cur = h1 if nm == "h1" else h0
                best = (tot, cur)
                for v in np.arange(cur - rng, cur + rng + 1e-9, rng / 2.5):
                    if abs(v - cur) < 1e-9:
                        continue
                    t = total(G, P, v if nm == "h1" else h1,
                              h0 if nm == "h1" else v)
                    if t > best[0]:
                        best = (t, float(v))
                if nm == "h1":
                    h1 = best[1]
                else:
                    h0 = best[1]
                tot = best[0]
            cur = G
            best = (tot, cur)
            for v in np.arange(cur - 0.4, cur + 0.4001, 0.1):
                if abs(v - cur) < 1e-9:
                    continue
                t = total(float(v), P, h1, h0)
                if t > best[0]:
                    best = (t, float(v))
            G, tot = best[1], best[0]
            print(f"step={step} r{rnd}: {100*tot/N:.3f}% G={G:.3f} "
                  f"P={[round(x,3) for x in P]} h1={h1:.1f} h0={h0:.1f}",
                  flush=True)
            if tot <= prev:
                break
    tot, det = total(G, P, h1, h0, detail=True)
    print(f"FINAL {100*tot/N:.3f}% G={G} P={P} h1={h1} h0={h0}")
    gaps = [P[i + 1] - P[i] for i in range(7)] + [G - P[7]]
    print("gaps(cy):", [round(x, 3) for x in gaps])
    for k, v in det.items():
        print(f"  {k:14s} t0={v[0]:8.1f} kap={v[1]:.4f} loop={G*v[1]:8.2f} miss={NW-v[2]}")
    json.dump({"G": G, "P": P, "h1": h1, "h0": h0, "NW": NW,
               "res": {k: list(v) for k, v in det.items()}},
              open("e7_gridfit.json", "w"), indent=1)


main()
