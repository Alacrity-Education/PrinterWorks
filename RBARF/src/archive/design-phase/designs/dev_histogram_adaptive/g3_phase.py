"""Phase-domain adaptive statistics.

Blind per capture:
  1. receiver coordinate x(i,s) from slot geometry (nominal or calibrated)
  2. rise events -> bracket (x_lo, x_hi]; take midpoint m_r
  3. estimate bit period P by maximising the phase concentration of the
     rise midpoints (|mean(exp(2i*pi*m/P))|), then beta = circular mean
  4. fall midpoints -> phase phi = frac((m_f - beta)/P): bimodal at
     h0/P (~0.28) and h1/P (~0.56) *independently of merging*
  5. threshold from the 2-cluster split of that per-capture histogram

Truth is used only to score.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)


def rise_fall(c, x):
    lv = c["lv"]
    ev = edge_list(lv)
    rises, falls = [], []
    if lv[0] == 1:
        rises.append((x[0] - 250.0, x[0], 0))
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((x[a], x[b], b))
    return rises, falls


def fit_P_beta(mr, lo, hi, n=8001):
    mr = np.asarray(mr)
    best = None
    for k in range(n):
        P = lo + k * (hi - lo) / (n - 1)
        z = np.exp(2j * np.pi * mr / P)
        v = abs(z.mean())
        if best is None or v > best[1]:
            best = (P, v, np.angle(z.mean()))
    P, v, ang = best
    beta = ang / (2 * np.pi) * P
    return P, beta, v


def refine_P_beta(mr, P, beta, span=6.0, iters=40):
    mr = np.asarray(mr)
    best = (P, beta, -1)
    for _ in range(iters):
        pass
    # local golden-ish scan
    for P2 in np.linspace(P - span, P + span, 601):
        z = np.exp(2j * np.pi * (mr - beta) / P2)
        v = abs(z.mean())
        if v > best[2]:
            best = (P2, beta + np.angle(z.mean()) / (2 * np.pi) * P2, v)
    return best[0], best[1], best[2]


meta, caps = load_all()
ALL = defaultdict(list)
rows = []
for c in caps:
    x = coord(c["it"], c["sl"], O, G)
    rises, falls = rise_fall(c, x)
    mr = np.array([0.5 * (a + b) for a, b, _ in rises])
    P, beta, v = fit_P_beta(mr, 1230.0, 1300.0)
    P, beta, v = refine_P_beta(mr, P, beta)
    tt = c["ttrue"]
    bits = c["bits"]
    # label each fall by the bit whose high it terminates
    phis, labels, lo_hi = [], [], []
    for a, b, j in falls:
        mfd = 0.5 * (a + b)
        ph = ((mfd - beta) / P) % 1.0
        k = int(np.floor(tt[j - 1] / BIT))   # last HIGH sample's bit
        if not (0 <= k < 192):
            continue
        phis.append(ph)
        labels.append(int(bits[k]))
        lo_hi.append((((a - beta) / P) % 1.0, ((b - beta) / P) % 1.0))
    phis = np.array(phis); labels = np.array(labels)
    ALL["phi"].append(phis); ALL["lab"].append(labels)
    rows.append((c["key"], P, beta, v, len(phis)))

phi = np.concatenate(ALL["phi"])
lab = np.concatenate(ALL["lab"])
print(f"geometry={GEOM}")
Ps = np.array([r[1] for r in rows])
print("P: min %.2f med %.2f max %.2f (spread %.2f%%)  conc: min %.3f med %.3f"
      % (Ps.min(), np.median(Ps), Ps.max(), 100*(Ps.max()-Ps.min())/np.median(Ps),
         min(r[3] for r in rows), np.median([r[3] for r in rows])))
for r in sorted(rows, key=lambda r: r[3])[:5]:
    print("   low concentration:", r[0], round(r[1], 2), round(r[3], 3))

print("\n=== fall-phase distribution by true bit ===")
for b in (0, 1):
    v = np.sort(phi[lab == b])
    print(f" bit={b} n={len(v):5d} min %.3f p1 %.3f p5 %.3f p50 %.3f p95 %.3f p99 %.3f max %.3f"
          % (v[0], v[len(v)//100], v[len(v)//20], v[len(v)//2],
             v[-1-len(v)//20], v[-1-len(v)//100], v[-1]))
print("\n=== global threshold sweep on fall phase ===")
best = None
for th in np.arange(0.30, 0.56, 0.01):
    fp = int((phi[lab == 0] > th).sum()); fn = int((phi[lab == 1] <= th).sum())
    e = (fp + fn) / len(phi)
    if best is None or e < best[0]:
        best = (e, th, fp, fn)
    print(f"  thr={th:.2f} 0->1 {fp:4d} 1->0 {fn:4d} err {e:.4f}")
print("best", best)

print("\n=== per-capture threshold (2-means on that capture's fall phases) ===")
tot_e = 0
tot_n = 0
worst = []
for (key, P, beta, v, n), ph, lb in zip(rows, ALL["phi"], ALL["lab"]):
    # 1-D 2-means seeded at 0.28 / 0.56
    a, b_ = 0.28, 0.56
    for _ in range(30):
        m = ph < 0.5 * (a + b_)
        if m.any():
            a = ph[m].mean()
        if (~m).any():
            b_ = ph[~m].mean()
    th = 0.5 * (a + b_)
    pred = (ph > th).astype(int)
    e = int((pred != lb).sum())
    tot_e += e; tot_n += len(ph)
    worst.append((e, key, round(a, 3), round(b_, 3), round(th, 3), len(ph)))
print("  total cell errors", tot_e, "of", tot_n, f"({tot_e/tot_n:.4f})")
for w in sorted(worst, reverse=True)[:10]:
    print("   ", w)
