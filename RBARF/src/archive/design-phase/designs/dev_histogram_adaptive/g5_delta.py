"""Does a data-dependent loop-length term help the histogram front end?

x(j) = it*G + o[sl] + delta * N(j),  N = #HIGH samples strictly before j.
delta is blind-computable (depends only on observed levels).  Sweep delta
and report the cell classification error of the local-tracker + adaptive
threshold pipeline.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 12
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)

meta, caps = load_all()

# precompute per capture
PRE = []
for c in caps:
    lv = c["lv"]
    N = np.concatenate([[0], np.cumsum(lv.astype(np.int64))[:-1]]).astype(float)
    base = c["it"] * G + np.asarray(O, float)[c["sl"]]
    ev = edge_list(lv)
    ridx = ([0] if lv[0] == 1 else [])
    rjs = [(-1 if lv[0] == 1 else None)]
    rises, falls = [], []
    if lv[0] == 1:
        rises.append((-1, 0))
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((a, b))
    PRE.append((c, base, N, rises, falls))


def comb(per, lo, hi, n=4001):
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


def run(delta):
    tot_e = tot_n = 0
    per_cap = Counter()
    for (c, base, N, rises, falls) in PRE:
        x = base + delta * N
        rm, rlo, rhi, rj = [], [], [], []
        for a, b in rises:
            lo_ = x[a] if a >= 0 else x[0] - 250.0
            rm.append(0.5 * (lo_ + x[b])); rlo.append(lo_); rhi.append(x[b])
            rj.append(b)
        fm, flo, fhi, fj = [], [], [], []
        for a, b in falls:
            fm.append(0.5 * (x[a] + x[b])); flo.append(x[a]); fhi.append(x[b])
            fj.append(b)
        rm = np.array(rm); fm = np.array(fm)
        # pair rises with falls
        cells = []
        fi = 0
        for qi in range(len(rm) - 1):
            while fi < len(fj) and fj[fi] <= rj[qi]:
                fi += 1
            if fi >= len(fj):
                break
            cells.append((qi, fi))
        if not cells:
            continue
        ri = np.array([q for q, _ in cells]); fidx = np.array([f for _, f in cells])
        per = rm[ri + 1] - rm[ri]
        P0 = comb(per, 1180.0, 1320.0)
        n_c = np.maximum(1, np.round(per / P0)).astype(int)
        k_c = np.concatenate([[0], np.cumsum(n_c)[:-1]])
        tau = np.zeros(len(ri)); Pl = np.zeros(len(ri))
        for i in range(len(ri)):
            a = max(0, i - W); b = min(len(ri), i + W + 1)
            kk = k_c[a:b].astype(float); yy = rm[ri[a:b]]
            A = np.vstack([kk, np.ones_like(kk)]).T
            sol, *_ = np.linalg.lstsq(A, yy, rcond=None)
            Pl[i], tau[i] = sol[0], sol[0] * k_c[i] + sol[1]
        tt = c["ttrue"]; bits = c["bits"]
        phs, labs = [], []
        for i in range(len(ri)):
            jf = fj[fidx[i]]
            kb = int(np.floor(tt[jf - 1] / BIT))
            if not (0 <= kb < 192):
                continue
            k0 = int(np.floor(tt[rj[ri[i]]] / BIT))
            mlen = max(1, kb - k0 + 1)
            b0 = tau[i] + (mlen - 1) * Pl[i]
            phs.append((fm[fidx[i]] - b0) / Pl[i]); labs.append(int(bits[kb]))
        phs = np.array(phs); labs = np.array(labs)
        a_, b_ = 0.28, 0.56
        for _ in range(40):
            sel = phs < 0.5 * (a_ + b_)
            if sel.any(): a_ = float(np.median(phs[sel]))
            if (~sel).any(): b_ = float(np.median(phs[~sel]))
        th = 0.5 * (a_ + b_)
        e = int(((phs > th).astype(int) != labs).sum())
        tot_e += e; tot_n += len(phs)
        per_cap[c["key"]] = e
    return tot_e, tot_n, per_cap


print(f"geom={GEOM} W={W}")
best = None
for delta in (-40, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 40):
    e, n, pc = run(float(delta))
    print(f"  delta={delta:+5d} ns/high : errors {e:5d}/{n} = {e/n:.4f}")
    if best is None or e < best[0]:
        best = (e, delta, pc)
print("best delta", best[1], "err", best[0])
print("worst captures:", best[2].most_common(8))
