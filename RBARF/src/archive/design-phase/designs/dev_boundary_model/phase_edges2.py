"""Unbiased slot-boundary estimator.

Assignment of a true edge to an observed transition uses only the
transition's DIRECTION and its rough time - not the assumed intra-loop
offsets - so the recovered phase interval per gap is not clipped by the
assumed u.  Each observed transition between slot s and slot s+1 proves
    u[s] <= phase(edge) <= u[s+1]
so max(phase | gap s-1) and min(phase | gap s) bracket u[s] from both
sides.  The residual OVERLAP of those two brackets measures how much the
sampling grid really wanders (clock noise + data-dependent loop timing).
"""
import json
import numpy as np
from common import load_caps, fit_cap, sample_times

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
g = DOC.copy(); g[7] += 3.0
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])

MAXR = 500.0        # ns: reject an edge/transition pair further apart than this

for rnd in range(6):
    per_gap = [[] for _ in range(8)]
    nmatch = 0
    for cap in caps:
        phi, P = fit_cap(cap, u)[:2]
        t = sample_times(cap, phi, P, u)
        o = np.lexsort((cap.sl, cap.it))
        t, sl, lv, it = t[o], cap.sl[o], cap.lev[o], cap.it[o]
        ch = np.nonzero(np.diff(lv) != 0)[0]         # transition after index ch
        if len(ch) == 0:
            continue
        tmid = 0.5 * (t[ch] + t[ch + 1])
        tdir = lv[ch + 1]                            # 1 = rise, 0 = fall
        E, Edir = cap.E, np.arange(len(cap.E)) % 2 == 0   # even index = rise
        for m in range(len(ch)):
            cand = np.nonzero(Edir == bool(tdir[m]))[0]
            j = cand[np.argmin(np.abs(E[cand] - tmid[m]))]
            if abs(E[j] - tmid[m]) > MAXR:
                continue
            # the edge must actually be inside the observed sample interval
            p = ((E[j] - phi) / P) % 1.0
            # loop index of the earlier sample; phase must be measured in the
            # same loop
            k = (E[j] - phi) / P
            if int(np.floor(k)) != int(it[ch[m]]):
                continue
            per_gap[int(sl[ch[m]])].append(p)
            nmatch += 1
    print(f"--- round {rnd}  n={nmatch}  u={np.round(u,5).tolist()}")
    stats = []
    for s in range(8):
        a = np.sort(np.array(per_gap[s]))
        if len(a) < 10:
            stats.append((np.nan, np.nan, 0)); print(f"  gap{s}: n={len(a)}"); continue
        stats.append((a[0], a[-1], len(a)))
        print(f"  gap{s}: n={len(a):5d} min={a[0]:.5f} p1={np.percentile(a,1):.5f}"
              f"  p99={np.percentile(a,99):.5f} max={a[-1]:.5f}")
    bnd = [0.0]
    for s in range(1, 8):
        lo_hi = stats[s - 1][1]      # max phase seen in gap s-1  -> u[s] >= it
        hi_lo = stats[s][0]          # min phase seen in gap s    -> u[s] <= it
        ov = (lo_hi - hi_lo)
        bnd.append(0.5 * (lo_hi + hi_lo))
        print(f"  u[{s}] in [{hi_lo:.5f}, {lo_hi:.5f}]  overlap={ov*2507.3:+.1f}ns")
    bnd = np.array(bnd)
    print("  u:", np.round(bnd, 5).tolist(),
          " gaps cy(L=40):", np.round(np.diff(np.append(bnd, 1.0)) * 40, 3))
    u = bnd

print("FINAL u:", np.round(u, 6).tolist())
print("ns @2507.3:", np.round(u * 2507.3, 1).tolist())
json.dump({"u": u.tolist()}, open(
    "/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/"
    "dev_boundary_model/u_phase2.json", "w"), indent=1)
