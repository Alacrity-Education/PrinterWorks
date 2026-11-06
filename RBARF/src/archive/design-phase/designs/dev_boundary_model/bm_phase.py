"""Per-loop phase: ground-truth Viterbi track vs. blind rising-edge track.

Geometry is fixed (global hardware):  t(i,s) = 2500*i + phi_i + tau*C[s]
with C = documented cycle positions and slot7 pulled in by one cycle.
phi_i is the loop's phase against the exact 1250 ns bit grid.

(a) ORACLE phi: Viterbi over phi using the known frame bits.
(b) BLIND  phi: tracked only from observed rising edges, which sit on the
    exact 1250 ns bit-boundary lattice for EVERY bit regardless of value.
"""
import json

import numpy as np

from bm_common import BIT_NS, load

C = np.array([1, 5, 9, 13, 17, 21, 27, 31], float)
LOOP_CY = 40
TAU = 62.75
H1, H0 = 750.0, 375.0
NL = 96
STEP = 2.5
PHI = np.arange(-1250.0, 1250.0, STEP)
BAND = int(40.0 / STEP)


def cost_grid(c, tau):
    """cost[i, k] = mismatched samples of loop i at phase PHI[k]."""
    bits = c["bits"]
    hwv = np.where(bits == 1, H1, H0)
    nb = len(bits)
    lv = np.zeros((NL, 8), np.int8)
    for k in range(len(c["lv"])):
        i, s = c["it"][k], c["sl"][k]
        if i < NL:
            lv[i, s] = c["lv"][k]
    I = np.arange(NL, dtype=float)[:, None]
    acc = np.zeros((NL, len(PHI)), np.int16)
    for s in range(8):
        t = 2500.0 * I + tau * C[s] + PHI[None, :]
        j = np.floor(t / BIT_NS).astype(np.int64)
        ok = (j >= 0) & (j < nb)
        jc = np.clip(j, 0, nb - 1)
        pred = (ok & ((t - jc * BIT_NS) < hwv[jc])).astype(np.int8)
        acc += (pred != lv[:, s][:, None]).astype(np.int16)
    return acc


def viterbi(cost, alpha=0.02):
    n, m = cost.shape
    D = cost[0].astype(float).copy()
    bk = np.zeros((n, m), np.int32)
    pen = alpha * STEP * np.abs(np.arange(-BAND, BAND + 1))
    for i in range(1, n):
        best = np.full(m, np.inf)
        arg = np.zeros(m, np.int32)
        for d in range(-BAND, BAND + 1):
            src = np.roll(D, d) + pen[d + BAND]
            if d > 0:
                src[:d] = np.inf
            elif d < 0:
                src[d:] = np.inf
            upd = src < best
            best[upd] = src[upd]
            arg[upd] = (np.arange(m) - d)[upd]
        D = best + cost[i]
        bk[i] = arg
    path = np.zeros(n, np.int32)
    path[-1] = int(np.argmin(D))
    for i in range(n - 1, 0, -1):
        path[i - 1] = bk[i][path[i]]
    return PHI[path], float(np.min(D))


def blind_phase(c, tau, nloops=NL):
    """Track phi from rising edges only (no knowledge of bit values).

    A rising edge between consecutive samples m-1 (low) and m (high) means
    a bit boundary k*1250 lies in (t_{m-1}, t_m].  Given an approximate
    phi, snap and least-squares update.  Returns per-loop phi.
    """
    it = c["it"]
    sl = c["sl"]
    lv = c["lv"]
    m = it < nloops
    it, sl, lv = it[m].astype(float), sl[m], lv[m]
    base = 2500.0 * it + tau * C[sl]
    ris = np.nonzero((lv[1:] == 1) & (lv[:-1] == 0))[0] + 1
    # bracket midpoint of each rising edge, in the phi=0 time base
    mid = 0.5 * (base[ris] + base[ris - 1])
    loop = it[ris]
    # coarse phi0 by scanning: minimise squared distance of mid+phi to lattice
    best = (1e18, 0.0)
    for p in np.arange(-1250.0, 1250.0, 2.0):
        r = (mid + p) % BIT_NS
        r = np.minimum(r, BIT_NS - r)
        v = float(np.sum(np.minimum(r, 300.0) ** 2))
        if v < best[0]:
            best = (v, p)
    phi0 = best[1]
    # linear + local smoothing: robust IRLS on (phi0, slope)
    a, b = phi0, 0.0
    for _ in range(30):
        p = a + b * loop
        k = np.round((mid + p) / BIT_NS)
        resid = k * BIT_NS - (mid + p)
        w = (np.abs(resid) < 320.0).astype(float)
        if w.sum() < 6:
            break
        A = np.vstack([w, w * loop]).T
        sol, *_ = np.linalg.lstsq(A, w * resid, rcond=None)
        a += sol[0]
        b += sol[1]
    # per-loop refinement: local median of residuals in a +-3 loop window
    phi = np.array([a + b * i for i in range(nloops)])
    for _ in range(3):
        p = phi[loop.astype(int)]
        k = np.round((mid + p) / BIT_NS)
        resid = k * BIT_NS - (mid + p)
        ok = np.abs(resid) < 320.0
        adj = np.zeros(nloops)
        for i in range(nloops):
            w = ok & (np.abs(loop - i) <= 3)
            if w.sum() >= 2:
                adj[i] = float(np.median(resid[w]))
        phi = phi + adj
    return phi, len(ris)


def main():
    meta, caps = load()
    rows = []
    for c in caps:
        cost = cost_grid(c, TAU)
        phi_o, dmin = viterbi(cost)
        phi_b, nris = blind_phase(c, TAU)
        # residual of oracle phi from a straight line (loops 0..93)
        x = np.arange(94)
        A = np.vstack([np.ones(94), x]).T
        sol, *_ = np.linalg.lstsq(A, phi_o[:94], rcond=None)
        lin = A @ sol
        nonlin = float(np.max(np.abs(phi_o[:94] - lin)))
        err = phi_b[:94] - phi_o[:94]
        mism = int(sum(cost[i, int(round((phi_o[i] + 1250.0) / STEP))]
                       for i in range(94)))
        rows.append((c["key"], sol[1], nonlin, float(np.max(np.abs(err))),
                     float(np.median(np.abs(err))), mism, nris))
        print("%-14s slope=%+7.2f ns/loop (G=%.1f)  nonlin=%5.1f ns | "
              "blind err med %5.1f max %6.1f | oracle mism %3d | rises %3d"
              % (c["key"], sol[1], 2500 + sol[1], nonlin,
                 rows[-1][4], rows[-1][3], mism, nris), flush=True)
    sl = np.array([r[1] for r in rows])
    nl = np.array([r[2] for r in rows])
    em = np.array([r[3] for r in rows])
    ed = np.array([r[4] for r in rows])
    print("\nslope ns/loop: min %+.2f med %+.2f max %+.2f  -> G %.1f..%.1f"
          % (sl.min(), np.median(sl), sl.max(), 2500 + sl.min(), 2500 + sl.max()))
    print("non-linearity of oracle phi (max dev from line): med %.1f max %.1f ns"
          % (np.median(nl), nl.max()))
    print("blind-track error vs oracle: median-of-medians %.1f ns, "
          "median-of-max %.1f ns, worst %.1f ns"
          % (np.median(ed), np.median(em), em.max()))
    json.dump({r[0]: dict(slope=r[1], nonlin=r[2], blind_max=r[3],
                          blind_med=r[4], mism=r[5], rises=r[6]) for r in rows},
              open("bm_phase.json", "w"), indent=1)


if __name__ == "__main__":
    main()
