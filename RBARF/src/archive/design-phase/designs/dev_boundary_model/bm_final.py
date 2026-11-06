"""Per-capture tau fit + decision-window (dead-zone) analysis.

Grid:   t(i,s) = 2500*i + phi_i + tau*C[s]
        C = [1,5,9,13,17,21,27,31] cycles (global hardware geometry)
phi_i is fitted per loop by Viterbi against the known bits (oracle) and
also tracked blind from rising edges only.  Then every sample is mapped
to (bit index, in-bit phase) and we ask which bits are decidable.
"""
import json
import sys
from collections import Counter

import numpy as np

from bm_common import BIT_NS, load
from bm_phase import C, cost_grid, viterbi, blind_phase, PHI, STEP, NL, H1, H0


def grid_times(c, phi, tau, nloops=NL):
    m = c["it"] < nloops
    it = c["it"][m].astype(float)
    sl = c["sl"][m]
    lv = c["lv"][m].astype(np.int8)
    t = 2500.0 * it + phi[c["it"][m]] + tau * C[sl]
    return t, lv, it, sl


def decide(t, lv, bits, h1=H1, h0=H0):
    j = np.floor(t / BIT_NS).astype(np.int64)
    p = t - j * BIT_NS
    ok = (j >= 0) & (j < 192)
    inf = ok & (p >= h0) & (p < h1)
    votes = {}
    for k in np.nonzero(inf)[0]:
        votes.setdefault(int(j[k]), []).append(int(lv[k]))
    blind, wrong, confl = [], [], []
    for b in range(192):
        v = votes.get(b)
        if not v:
            blind.append(b)
            continue
        if len(set(v)) > 1:
            confl.append(b)
        if (1 if sum(v) * 2 > len(v) else 0) != int(bits[b]):
            wrong.append(b)
    return blind, wrong, confl, j, p, inf, ok


def runs(idx):
    out, cur = [], []
    for b in sorted(idx):
        if cur and b == cur[-1] + 1:
            cur.append(b)
        else:
            if cur:
                out.append(cur)
            cur = [b]
    if cur:
        out.append(cur)
    return out


def main():
    meta, caps = load()
    taus = np.arange(62.20, 63.10, 0.05)
    agg = Counter()
    infh = Counter()
    slot_inf = Counter()
    slot_n = Counter()
    tau_best, G_best, mr_all, blind_err = [], [], [], []
    gap_blind = Counter()
    rec = {}
    for c in caps:
        best = None
        for tau in taus:
            cg = cost_grid(c, tau)
            phi, d = viterbi(cg)
            if best is None or d < best[0]:
                best = (d, tau, phi, cg)
        d, tau, phi, cg = best
        slope = float(np.polyfit(np.arange(94), phi[:94], 1)[0])
        t, lv, it, sl = grid_times(c, phi, tau)
        bl, wr, cf, j, p, inf, ok = decide(t, lv, c["bits"])
        pb = [b for b in bl if 32 <= b < 160]
        pw = [b for b in wr if 32 <= b < 160]
        pc = [b for b in cf if 32 <= b < 160]
        # blind (no-ground-truth) phase track, corrected for the whole-bit
        # ambiguity that the trigger anchor resolves
        pb_t, nris = blind_phase(c, tau)
        e = pb_t[:94] - phi[:94]
        e = e - BIT_NS * np.round(np.median(e) / BIT_NS)
        blind_err.append((float(np.median(np.abs(e))), float(np.max(np.abs(e)))))
        # which inter-slot gap swallowed each blind bit's decision window
        for b in pb:
            lo, hi = b * BIT_NS + H0, b * BIT_NS + H1
            before = np.nonzero(t < lo)[0]
            after = np.nonzero(t >= hi)[0]
            if len(before) and len(after):
                gap_blind[int(sl[before[-1]])] += 1
        cnt = Counter(int(x) for x in j[inf])
        for b in range(32, 160):
            infh[min(cnt.get(b, 0), 4)] += 1
        for s in range(8):
            slot_n[s] += int(np.count_nonzero((sl == s) & ok))
            slot_inf[s] += int(np.count_nonzero((sl == s) & inf))
        mr = max([len(r) for r in runs(pb)] or [0])
        mr_all.append(mr)
        agg["blind"] += len(pb); agg["wrong"] += len(pw); agg["confl"] += len(pc)
        agg["hdr_blind"] += len([b for b in bl if b < 32 or b >= 160])
        tau_best.append(tau); G_best.append(2500 + slope)
        rec[c["key"]] = dict(tau=tau, G=2500 + slope, phi=[float(x) for x in phi],
                             blind=pb, wrong=pw, confl=pc, mism=int(d))
        print("%-14s tau=%.2f G=%.1f (tau_loop=%.2f) | mism %3d | blind %3d "
              "(maxrun %d) wrong %2d confl %2d | blindphase err med %.0f max %.0f"
              % (c["key"], tau, 2500 + slope, (2500 + slope) / 40.0, int(d),
                 len(pb), mr, len(pw), len(pc), blind_err[-1][0], blind_err[-1][1]),
              flush=True)

    n = 128 * len(caps)
    print("\n=== payload bits %d ===" % n)
    print("blind (no sample in [h0,h1))  %4d = %.2f%%  -> %.2f bits/capture"
          % (agg["blind"], 100 * agg["blind"] / n, agg["blind"] / len(caps)))
    print("wrong (majority of in-window) %4d = %.3f%%" % (agg["wrong"], 100 * agg["wrong"] / n))
    print("conflicting in-window votes   %4d" % agg["confl"])
    print("header/trailer blind bits     %4d (of %d)" % (agg["hdr_blind"], 64 * len(caps)))
    print("informative samples per payload bit:", {k: infh[k] for k in range(5)})
    print("per-slot informative fraction:",
          {s: round(slot_inf[s] / max(slot_n[s], 1), 3) for s in range(8)})
    print("blind bit attributed to gap AFTER slot:", dict(sorted(gap_blind.items())))
    print("max consecutive blind payload bits: med %.0f max %d"
          % (np.median(mr_all), max(mr_all)))
    print("tau fitted: min %.2f med %.2f max %.2f" %
          (min(tau_best), float(np.median(tau_best)), max(tau_best)))
    print("loop G: min %.1f med %.1f max %.1f | G/40 = %.2f..%.2f ns"
          % (min(G_best), float(np.median(G_best)), max(G_best),
             min(G_best) / 40, max(G_best) / 40))
    be = np.array(blind_err)
    print("blind phase track (rising edges only) vs oracle: "
          "med %.1f ns, p90 %.1f ns, worst %.1f ns"
          % (np.median(be[:, 0]), np.percentile(be[:, 1], 90), be[:, 1].max()))
    json.dump(rec, open("bm_final.json", "w"), indent=1)


if __name__ == "__main__":
    main()
