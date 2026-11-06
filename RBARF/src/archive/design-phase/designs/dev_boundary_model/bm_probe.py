"""(A) diagnose the P(hi|bit=1) dip near phase 625-650
   (B) interval-constraint rising-edge phase track (vs midpoint version)
   (C) global intra-loop stretch kappa with tau tied to G/40
"""
import json
from collections import Counter

import numpy as np

from bm_common import BIT_NS, load
from bm_phase import C, cost_grid, viterbi, blind_phase, NL, H1, H0


def grid(c, r, tau=None):
    tau = r["tau"] if tau is None else tau
    phi = np.array(r["phi"])
    m = c["it"] < NL
    it, sl, lv = c["it"][m], c["sl"][m], c["lv"][m]
    t = 2500.0 * it + phi[it] + tau * C[sl]
    return t, it, sl, lv


def main():
    meta, caps = load()
    fin = json.load(open("bm_final.json"))

    print("== (A) samples with bit=1, phase in [600,725), read LOW ==")
    bad_slot = Counter(); all_slot = Counter(); bad_key = Counter()
    for c in caps:
        r = fin[c["key"]]
        t, it, sl, lv = grid(c, r)
        j = np.floor(t / BIT_NS).astype(int)
        p = t - j * BIT_NS
        ok = (j >= 0) & (j < 192) & (c["bits"][np.clip(j, 0, 191)] == 1)
        sel = ok & (p >= 600) & (p < 725)
        for k in np.nonzero(sel)[0]:
            all_slot[int(sl[k])] += 1
            if lv[k] == 0:
                bad_slot[int(sl[k])] += 1
                bad_key[c["key"]] += 1
    print("  per slot  low/total:",
          {s: f"{bad_slot[s]}/{all_slot[s]}" for s in sorted(all_slot)})
    print("  worst captures:", bad_key.most_common(8))

    print("\n== (C) tau tied to G/40 with a global intra-loop stretch kappa ==")
    for kap in (1.000, 1.002, 1.004, 1.005, 1.006, 1.008, 1.010):
        tot = 0
        for c in caps:
            r = fin[c["key"]]
            cg = cost_grid(c, kap * r["G"] / 40.0)
            _, d = viterbi(cg)
            tot += int(d)
        print(f"  kappa={kap:.3f} tau=kappa*G/40: {tot} mismatched samples")

    print("\n== (B) interval-constraint rising-edge track ==")
    res = []
    for c in caps:
        r = fin[c["key"]]
        tau = r["tau"]
        phio = np.array(r["phi"])[:94]
        m = c["it"] < NL
        it, sl, lv = c["it"][m].astype(float), c["sl"][m], c["lv"][m]
        base = 2500.0 * it + tau * C[sl]
        ris = np.nonzero((lv[1:] == 1) & (lv[:-1] == 0))[0] + 1
        lo_t, hi_t = base[ris - 1], base[ris]
        loop = it[ris].astype(int)
        pm, _ = blind_phase(c, tau)           # midpoint seed
        phi = pm[:94].copy()
        for _ in range(6):
            newphi = phi.copy()
            for i in range(94):
                w = np.abs(loop - i) <= 2
                if w.sum() == 0:
                    continue
                A, B = [], []
                for a, b in zip(lo_t[w], hi_t[w]):
                    k = np.round((a + b) / 2 / BIT_NS + phi[i] / BIT_NS)
                    A.append(k * BIT_NS - b)       # phi >= k*1250 - hi_t
                    B.append(k * BIT_NS - a)       # phi <  k*1250 - lo_t
                A, B = np.array(A), np.array(B)
                lo, hi = A.max(), B.min()
                if lo <= hi:
                    newphi[i] = 0.5 * (lo + hi)
                else:                              # infeasible: median centre
                    newphi[i] = float(np.median(0.5 * (A + B)))
            phi = newphi
        e = phi - phio
        e -= BIT_NS * np.round(e / BIT_NS)
        res.append((c["key"], float(np.median(np.abs(e))), float(np.max(np.abs(e))),
                    int(np.count_nonzero(np.abs(e) > 60))))
    a = np.array([[x[1], x[2], x[3]] for x in res])
    print("  interval track |err|: med-of-med %.1f  med-of-max %.1f  worst %.1f ns"
          % (np.median(a[:, 0]), np.median(a[:, 1]), a[:, 1].max()))
    print("  loops with |err|>60 ns: med %.0f of 94, max %d"
          % (np.median(a[:, 2]), a[:, 2].max()))
    for k, md, mx, n in sorted(res, key=lambda x: -x[2])[:5]:
        print(f"    worst {k:14s} med {md:5.1f} max {mx:6.1f} n>60 {n}")


if __name__ == "__main__":
    main()
