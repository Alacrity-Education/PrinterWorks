"""Locally-adaptive phase tracking + interval-aware fall classification.

Pass 1: global comb -> P0, cell bit-counts n_c = round(d/P0).
Pass 2: cumulative bit index k_c per cell; LOCAL linear regression of rise
        midpoint vs k over a window of W cells -> tau(k), P_local(k).
Pass 3: fall phase = (m_f - tau(k_last)) / P_local, plus its bracket.

Reports: cell-classification error for midpoint vs interval rules, and how
much the local tracker beats a single global P.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 12
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)


def cells_of(c, x):
    """[(r_lo,r_hi, f_lo,f_hi, j_fall_prev, next r_lo,r_hi)] per rise."""
    lv = c["lv"]
    ev = edge_list(lv)
    rises = ([(x[0] - 250.0, x[0], 0)] if lv[0] == 1 else [])
    falls = []
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((x[a], x[b], b))
    out = []
    fi = 0
    for qi in range(len(rises)):
        rl, rh, rj = rises[qi]
        while fi < len(falls) and falls[fi][2] <= rj:
            fi += 1
        if fi >= len(falls) or qi + 1 >= len(rises):
            break
        fl, fh, fj = falls[fi]
        nl, nh, nj = rises[qi + 1]
        out.append(dict(rl=rl, rh=rh, rj=rj, fl=fl, fh=fh, fj=fj,
                        nl=nl, nh=nh, nj=nj))
    return out


def comb(per, lo, hi, n=6001):
    per = np.asarray(per, float)
    best = None
    for k in range(n):
        P = lo + k * (hi - lo) / (n - 1)
        q = per / P
        s = q <= 4.5
        e = float(np.sum((q[s] - np.round(q[s])) ** 2))
        if best is None or e < best[1]:
            best = (P, e)
    return best[0]


meta, caps = load_all()
res = defaultdict(list)
rows = []
for c in caps:
    x = coord(c["it"], c["sl"], O, G)
    cs = cells_of(c, x)
    rm = np.array([0.5 * (z["rl"] + z["rh"]) for z in cs])
    fm = np.array([0.5 * (z["fl"] + z["fh"]) for z in cs])
    nm = np.array([0.5 * (z["nl"] + z["nh"]) for z in cs])
    P0 = comb(nm - rm, 1200.0, 1320.0)
    n_c = np.maximum(1, np.round((nm - rm) / P0)).astype(int)
    k_c = np.concatenate([[0], np.cumsum(n_c)[:-1]])
    # local linear fit of rm vs k_c
    tau = np.zeros(len(cs)); Ploc = np.zeros(len(cs))
    for i in range(len(cs)):
        a = max(0, i - W); b = min(len(cs), i + W + 1)
        kk = k_c[a:b].astype(float); yy = rm[a:b]
        A = np.vstack([kk, np.ones_like(kk)]).T
        sol, *_ = np.linalg.lstsq(A, yy, rcond=None)
        Ploc[i] = sol[0]
        tau[i] = sol[0] * k_c[i] + sol[1]
    # truth labels
    tt = c["ttrue"]; bits = c["bits"]
    for i, z in enumerate(cs):
        kb = int(np.floor(tt[z["fj"] - 1] / BIT))
        if not (0 <= kb < 192):
            continue
        lab = int(bits[kb])
        # merged prefix length from truth
        k0 = int(np.floor(tt[z["rj"]] / BIT))
        mlen = max(1, kb - k0 + 1)
        # phase relative to the bit that owns the fall
        base = tau[i] + (mlen - 1) * Ploc[i]
        ph = (fm[i] - base) / Ploc[i]
        plo = (z["fl"] - base) / Ploc[i]
        phi_ = (z["fh"] - base) / Ploc[i]
        res["ph"].append(ph); res["lab"].append(lab)
        res["lo"].append(plo); res["hi"].append(phi_)
        res["key"].append(c["key"])
        res["mlen"].append(mlen)
        # global-P comparison
        base2 = rm[i] + (mlen - 1) * P0
        res["phg"].append((fm[i] - base2) / P0)
    rows.append((c["key"], P0, float(np.median(Ploc)), len(cs)))

ph = np.array(res["ph"]); lab = np.array(res["lab"])
phg = np.array(res["phg"])
lo = np.array(res["lo"]); hi = np.array(res["hi"])
print(f"geom={GEOM} W={W}")
P0s = np.array([r[1] for r in rows]); Pls = np.array([r[2] for r in rows])
print("P0 med %.2f  Ploc med %.2f" % (np.median(P0s), np.median(Pls)))

for nm_, arr in (("global-P (rise midpoint base)", phg),
                 ("local tracker", ph)):
    print(f"\n=== {nm_} ===")
    for b in (0, 1):
        v = np.sort(arr[lab == b])
        print(f"  bit={b} n={len(v):5d} p1 %.3f p5 %.3f p50 %.3f p95 %.3f p99 %.3f"
              % (v[len(v)//100], v[len(v)//20], v[len(v)//2],
                 v[-1-len(v)//20], v[-1-len(v)//100]))
    best = None
    for th in np.arange(0.28, 0.60, 0.005):
        fp = int((arr[lab == 0] > th).sum()); fn = int((arr[lab == 1] <= th).sum())
        e = (fp + fn) / len(arr)
        if best is None or e < best[0]:
            best = (e, th, fp, fn)
    print("  best global thr: err %.4f at %.3f (0->1 %d, 1->0 %d)" % best)

print("\n=== interval rule (h0=0.28, h1=0.56 nominal, per-capture learned) ===")
# per-capture 2-means on ph
keys = np.array(res["key"])
tot_e = tot_n = 0
amb = 0
worst = Counter()
for k in sorted(set(keys.tolist())):
    m = keys == k
    v = ph[m]; l = lab[m]
    a, b_ = 0.28, 0.56
    for _ in range(40):
        sel = v < 0.5 * (a + b_)
        if sel.any(): a = float(np.median(v[sel]))
        if (~sel).any(): b_ = float(np.median(v[~sel]))
    th = 0.5 * (a + b_)
    e = int(((v > th).astype(int) != l).sum())
    tot_e += e; tot_n += len(v)
    worst[k] = e
print("  per-capture 2-median threshold: errors %d of %d (%.4f)"
      % (tot_e, tot_n, tot_e / tot_n))
for k, e in worst.most_common(10):
    print("   ", k, e)

print("\n=== how informative is the fall bracket? ===")
wid = hi - lo
print("  bracket width in bit units: p50 %.3f p90 %.3f max %.3f"
      % (np.percentile(wid, 50), np.percentile(wid, 90), wid.max()))
h0n, h1n = 0.28, 0.56
c_both = int(((lo <= h0n) & (hi >= h0n) & (lo <= h1n) & (hi >= h1n)).sum())
c_h0 = int(((lo <= h0n) & (hi >= h0n) & ~((lo <= h1n) & (hi >= h1n))).sum())
c_h1 = int(((lo <= h1n) & (hi >= h1n) & ~((lo <= h0n) & (hi >= h0n))).sum())
c_none = len(lo) - c_both - c_h0 - c_h1
print(f"  bracket contains both hypotheses: {c_both} ({c_both/len(lo):.3%})")
print(f"  only h0: {c_h0}   only h1: {c_h1}   neither: {c_none}")
sel = (c_h0 > 0)
mh0 = (lo <= h0n) & (hi >= h0n) & ~((lo <= h1n) & (hi >= h1n))
mh1 = (lo <= h1n) & (hi >= h1n) & ~((lo <= h0n) & (hi >= h0n))
print("  errors when only-h0 decided:", int((lab[mh0] != 0).sum()), "/", int(mh0.sum()))
print("  errors when only-h1 decided:", int((lab[mh1] != 1).sum()), "/", int(mh1.sum()))
