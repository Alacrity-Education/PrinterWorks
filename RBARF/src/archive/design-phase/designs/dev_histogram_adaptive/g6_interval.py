"""Interval ("definitive") classification and the self-consistency objective.

For every fall the true fall time lies in (t_lastHigh, t_firstLow].  On the
wire a fall happens at phase h0 or h1 of its bit.  So a cell is
DEFINITIVELY classified when its fall bracket contains exactly one of the
two learned phases.  This script measures:

  (a) the ceiling: using the calibrated truth time base
  (b) a blind per-capture fit of (P, beta) by maximising the number of RISE
      brackets that contain a grid point k*P+beta  (pure self-consistency,
      no ns constants, no ground truth)
  (c) the same with a linear drift term (P varies along the capture)
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)
meta, caps = load_all()


def events(c, x):
    lv = c["lv"]
    ev = edge_list(lv)
    rises, falls = [], []
    if lv[0] == 1:
        rises.append((x[0] - 300.0, x[0], 0))
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((x[a], x[b], b))
    return rises, falls


def frac(v):
    return v - np.floor(v)


def rise_score(rlo, rhi, P, beta, drift=0.0):
    """count of rise brackets containing a grid point."""
    u_lo = (rlo - beta) / P
    u_hi = (rhi - beta) / P
    return int(np.sum(np.floor(u_hi) >= np.ceil(u_lo) - 1e-12))


def fit_P_beta(rlo, rhi, Plo=1230.0, Phi=1300.0, nP=1401, nB=200):
    best = None
    for P in np.linspace(Plo, Phi, nP):
        for beta in np.linspace(0.0, P, nB, endpoint=False):
            s = rise_score(rlo, rhi, P, beta)
            if best is None or s > best[0]:
                best = (s, P, beta)
    # refine
    s, P, beta = best
    for _ in range(4):
        dP = (Phi - Plo) / (nP - 1) / 3
        dB = P / nB / 3
        for P2 in np.linspace(P - 3 * dP, P + 3 * dP, 25):
            for b2 in np.linspace(beta - 3 * dB, beta + 3 * dB, 25):
                sc = rise_score(rlo, rhi, P2, b2)
                if sc > s:
                    s, P, beta = sc, P2, b2
        Plo, Phi = P - 3 * dP, P + 3 * dP
        nP, nB = 25, 25
    return P, beta, s


def cluster_two(vals, a=0.28, b=0.56, iters=50):
    v = np.asarray(vals)
    for _ in range(iters):
        sel = v < 0.5 * (a + b)
        if sel.any(): a = float(np.median(v[sel]))
        if (~sel).any(): b = float(np.median(v[~sel]))
    return a, b


print(f"geom={GEOM}")
for MODE in ("truth", "blind"):
    tot = Counter()
    per = []
    for c in caps:
        lv = c["lv"]
        if MODE == "truth":
            x = c["ttrue"]
            P, beta = BIT, 0.0
        else:
            x = coord(c["it"], c["sl"], O, G)
        rises, falls = events(c, x)
        rlo = np.array([r[0] for r in rises]); rhi = np.array([r[1] for r in rises])
        flo = np.array([f[0] for f in falls]); fhi = np.array([f[1] for f in falls])
        fj = [f[2] for f in falls]
        if MODE == "blind":
            P, beta, s = fit_P_beta(rlo, rhi)
        # phase of the fall bracket relative to the bit that owns the fall:
        # bit index of a fall = floor((t_lastHigh - beta)/P)
        klo = np.floor((flo - beta) / P)
        plo = (flo - beta) / P - klo
        phi = (fhi - beta) / P - klo
        h0, h1 = cluster_two(0.5 * (plo + phi))
        # definitive test
        in0 = (plo <= h0) & (phi >= h0)
        in1 = (plo <= h1) & (phi >= h1)
        dec = np.where(in1 & ~in0, 1, np.where(in0 & ~in1, 0, -1))
        # truth label
        tt = c["ttrue"]; bits = c["bits"]
        lab = np.array([int(bits[int(np.floor(tt[j - 1] / BIT))])
                        if 0 <= int(np.floor(tt[j - 1] / BIT)) < 192 else -1
                        for j in fj])
        m = lab >= 0
        tot["cells"] += int(m.sum())
        tot["def"] += int(((dec >= 0) & m).sum())
        tot["deferr"] += int(((dec >= 0) & m & (dec != lab)).sum())
        tot["both"] += int((in0 & in1 & m).sum())
        tot["none"] += int((~in0 & ~in1 & m).sum())
        per.append((c["key"], P, beta, h0, h1,
                    int(((dec >= 0) & m & (dec != lab)).sum()),
                    int((~in0 & ~in1 & m).sum())))
    print(f"\n--- {MODE} ---")
    print("  cells %d  definitive %d (%.2f%%)  definitive-errors %d (%.4f)"
          % (tot["cells"], tot["def"], 100 * tot["def"] / tot["cells"],
             tot["deferr"], tot["deferr"] / max(1, tot["def"])))
    print("  ambiguous(both) %d   unexplained(neither) %d"
          % (tot["both"], tot["none"]))
    hs = np.array([[p[3], p[4]] for p in per])
    print("  learned h0: med %.3f (min %.3f max %.3f)   h1: med %.3f (min %.3f max %.3f)"
          % (np.median(hs[:, 0]), hs[:, 0].min(), hs[:, 0].max(),
             np.median(hs[:, 1]), hs[:, 1].min(), hs[:, 1].max()))
    for p in sorted(per, key=lambda p: -(p[5] * 100 + p[6]))[:8]:
        print("   worst:", p[0], "P=%.2f" % p[1], "h=(%.3f,%.3f)" % (p[3], p[4]),
              "deferr", p[5], "none", p[6])
