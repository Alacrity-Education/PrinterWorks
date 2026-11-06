"""Non-parametric slot-boundary estimator.

For every TRUE waveform edge we know its absolute time e.  With a
per-capture linear time base (phi, P) that edge has a loop phase
p = frac((e - phi)/P).  In the capture we can see WHICH inter-sample gap
the transition actually landed in (slot s -> slot s+1, or slot7 -> next
slot0).  The phase at which the observed gap index switches from s to s+1
IS the slot offset u[s+1].  No parametric model, no loss surface.
"""
import json
import numpy as np
from common import load_caps, fit_cap, sample_times

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)


def u_of(g):
    return np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])


g = DOC.copy(); g[7] += 3.0
u = u_of(g)

for rnd in range(4):
    obs = []            # (phase, gap_index)
    for cap in caps:
        phi, P = fit_cap(cap, u)[:2]
        t = sample_times(cap, phi, P, u)
        order = np.lexsort((cap.sl, cap.it))
        t, sl, lv, it = t[order], cap.sl[order], cap.lev[order], cap.it[order]
        E = cap.E
        # level just before / after each true edge
        for j, e in enumerate(E):
            pre, post = (j & 1), 1 - (j & 1)      # even j = rise (0 -> 1)
            # nearest true edges on either side: require an isolated edge so
            # that a single sample interval cannot contain two of them
            lo = E[j - 1] if j > 0 else -1e9
            hi = E[j + 1] if j + 1 < len(E) else 1e9
            k = np.searchsorted(t, e)             # first sample after e
            if k == 0 or k >= len(t):
                continue
            a, b = k - 1, k
            if not (t[a] > lo and t[b] < hi):
                continue                          # interval spans another edge
            if lv[a] != pre or lv[b] != post:
                continue                          # transition not cleanly seen
            if it[b] - it[a] > 1:
                continue
            gapidx = int(sl[a])
            p = ((e - phi) / P) % 1.0
            obs.append((p, gapidx, float(sl[b])))
    obs = np.array(obs)
    ph, gi = obs[:, 0], obs[:, 1].astype(int)
    print(f"--- round {rnd}: {len(obs)} clean edges;  u={np.round(u,5).tolist()}")
    newu = [0.0]
    for s in range(8):
        m = gi == s
        if m.sum() == 0:
            print(f"  gap{s}: EMPTY")
            newu.append(np.nan)
            continue
        q = np.sort(ph[m])
        print(f"  gap{s}: n={m.sum():5d}  phase p5={np.percentile(q,5):.4f} "
              f"p50={np.percentile(q,50):.4f} p95={np.percentile(q,95):.4f} "
              f"min={q[0]:.4f} max={q[-1]:.4f}")
    # boundary between gap s-1 and gap s = midpoint of (max of s-1, min of s)
    bnd = [0.0]
    for s in range(1, 8):
        a = ph[gi == s - 1]
        b = ph[gi == s]
        if len(a) == 0 or len(b) == 0:
            bnd.append(np.nan); continue
        # robust: 99th pct of lower group, 1st pct of upper group
        lo = np.percentile(a, 99.0)
        hi = np.percentile(b, 1.0)
        bnd.append(0.5 * (lo + hi))
    bnd = np.array(bnd)
    print("  boundaries (=u):", np.round(bnd, 5).tolist())
    print("  gaps cycles(L=40):", np.round(np.diff(np.append(bnd, 1.0)) * 40, 2))
    if not np.any(np.isnan(bnd)):
        u = bnd

print("FINAL u:", np.round(u, 6).tolist())
print("offsets ns @P=2507.3:", np.round(u * 2507.3, 1).tolist())
json.dump({"u": u.tolist()}, open(
    "/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/"
    "dev_boundary_model/u_phase.json", "w"), indent=1)
