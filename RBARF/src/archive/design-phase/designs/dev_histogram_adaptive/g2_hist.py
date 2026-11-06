"""Blind (no ground truth used to build features) pulse statistics.

Features per cell:  rise bracket, fall bracket, next-rise bracket, all in a
receiver coordinate built from *nominal* or *calibrated* slot offsets with
NO per-capture scale.  Then a comb fit gives the bit period P in receiver
units, and every cell yields (d = period/P, w = width/P).

Ground truth is used only to LABEL the resulting features.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "nom"
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)


def comb_fit(per, lo, hi, n=6001, maxq=4.5):
    per = np.asarray(per, float)
    best = None
    for k in range(n):
        P = lo + k * (hi - lo) / (n - 1)
        q = per / P
        sel = q <= maxq
        e = float(np.sum((q[sel] - np.round(q[sel])) ** 2))
        if best is None or e < best[1]:
            best = (P, e)
    return best[0]


def cells_of(c, x):
    lv = c["lv"]
    ev = edge_list(lv)
    rises = [("R", -1, 0)] + [e for e in ev if e[0] == "R"]
    falls = [e for e in ev if e[0] == "F"]
    out = []
    fi = 0
    for qi, (_, a, b) in enumerate(rises):
        while fi < len(falls) and falls[fi][2] <= b:
            fi += 1
        if fi >= len(falls):
            break
        fa, fb = falls[fi][1], falls[fi][2]
        if qi + 1 >= len(rises):
            break
        na, nb = rises[qi + 1][1], rises[qi + 1][2]
        rl = x[a] if a >= 0 else x[0] - 250.0
        out.append(dict(jr=b, r_lo=rl, r_hi=x[b],
                        f_lo=x[fa], f_hi=x[fb],
                        n_lo=x[na], n_hi=x[nb], jn=nb))
    return out


brackets_r, brackets_f = [], []
Pest = {}
D = []          # (d, n_true)
Wr = defaultdict(list)   # last-bit -> residual r
ROWS = []
for c in caps if False else []:
    pass

meta, caps = load_all()
for c in caps:
    x = coord(c["it"], c["sl"], O, G)
    cs = cells_of(c, x)
    rmid = np.array([0.5 * (z["r_lo"] + z["r_hi"]) for z in cs])
    fmid = np.array([0.5 * (z["f_lo"] + z["f_hi"]) for z in cs])
    nmid = np.array([0.5 * (z["n_lo"] + z["n_hi"]) for z in cs])
    per = nmid - rmid
    P = comb_fit(per, 1150.0, 1350.0)
    Pest[c["key"]] = P
    tt = c["ttrue"]
    bits = c["bits"]
    nbad = 0
    for z, rm, fm, nm_ in zip(cs, rmid, fmid, nmid):
        brackets_r.append(z["r_hi"] - z["r_lo"])
        brackets_f.append(z["f_hi"] - z["f_lo"])
        k0 = int(np.floor(tt[z["jr"]] / BIT))
        k1 = int(np.floor(tt[z["jn"]] / BIT))
        if not (0 <= k0 < 192 and k0 < k1 <= 192):
            continue
        ntrue = k1 - k0
        d = (nm_ - rm) / P
        w = (fm - rm) / P
        D.append((d, ntrue))
        if round(d) != ntrue:
            nbad += 1
        sub = "".join(str(int(b)) for b in bits[k0:k1])
        # m = index of the bit whose fall we see = length of leading 1-run,
        # but at least 1
        m = len(sub) - len(sub.lstrip("1"))
        m = max(m, 1)
        last = int(sub[m - 1])
        Wr[(m, last)].append(w - (m - 1))
    ROWS.append((c["key"], P, len(cs), nbad))

print(f"geometry = {GEOM}   o={[round(v,1) for v in O]}  G={G}")
print("\n=== bracket widths (ns, nominal receiver units) ===")
br = np.array(brackets_r + brackets_f)
print("  rise/fall bracket: min %.1f  p50 %.1f  p90 %.1f  max %.1f  mean %.1f"
      % (br.min(), np.percentile(br, 50), np.percentile(br, 90), br.max(),
         br.mean()))
print("  histogram:", dict(sorted(Counter(np.round(br, 1)).items())))

Ps = np.array([r[1] for r in ROWS])
print("\n=== comb-fit bit period P (receiver ns) ===")
print("  min %.2f  p50 %.2f  max %.2f  spread %.3f%%"
      % (Ps.min(), np.median(Ps), Ps.max(),
         100 * (Ps.max() - Ps.min()) / np.median(Ps)))
print("  total cells with round(d) != n_true:", sum(r[3] for r in ROWS),
      "of", sum(r[2] for r in ROWS))
for k, P, nc, nb in ROWS:
    if nb:
        print(f"    {k:14s} P={P:8.2f} cells={nc} d-errors={nb}")

Da = np.array([d for d, n in D])
Na = np.array([n for d, n in D])
print("\n=== d = cell period / P, by true bit count ===")
for n in sorted(set(Na.tolist())):
    v = np.sort(Da[Na == n])
    print(f"  n={n} cnt={len(v):5d} min %.3f p1 %.3f p50 %.3f p99 %.3f max %.3f"
          % (v[0], v[max(0, len(v)//100)], v[len(v)//2],
             v[-1-len(v)//100], v[-1]))

print("\n=== residual r = w/P - (m-1), grouped by (m, last bit) ===")
for key in sorted(Wr):
    v = np.sort(np.array(Wr[key]))
    if len(v) < 3:
        print(f"  m={key[0]} last={key[1]} n={len(v)} vals={np.round(v,3)}")
        continue
    print(f"  m={key[0]} last={key[1]} n={len(v):5d} "
          "min %.3f p1 %.3f p5 %.3f p50 %.3f p95 %.3f p99 %.3f max %.3f"
          % (v[0], v[len(v)//100], v[len(v)//20], v[len(v)//2],
             v[-1-len(v)//20], v[-1-len(v)//100], v[-1]))

z = np.concatenate([np.array(Wr[k]) for k in Wr if k[1] == 0])
o1 = np.concatenate([np.array(Wr[k]) for k in Wr if k[1] == 1])
print("\n=== single global threshold on r ===")
for th in np.arange(0.30, 0.52, 0.02):
    fp = int((z > th).sum()); fn = int((o1 <= th).sum())
    print(f"  thr={th:.2f}  0->1 {fp:4d}   1->0 {fn:4d}   err {(fp+fn)/(len(z)+len(o1)):.4f}")
