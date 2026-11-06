"""Empirical soft-decision curve + single-clock-parameter check.

(1) P(sample reads HIGH | true bit b, in-bit phase p) measured on the
    oracle grid  -> the sigmoid the decoder should use.
(2) Does tau = G/40 (one clock parameter) fit as well as a free tau?
(3) Blind rising-edge phase track quality with per-sample bit unwrapping.
"""
import json

import numpy as np

from bm_common import BIT_NS, load
from bm_phase import C, cost_grid, viterbi, blind_phase, NL, H1, H0


def main():
    meta, caps = load()
    fin = json.load(open("bm_final.json"))

    # ---- (2) one-parameter clock: tau = G/40 vs free tau -----------------
    print("== clock parametrisation ==")
    tot_free = tot_tied = 0
    for c in caps:
        r = fin[c["key"]]
        cgf = cost_grid(c, r["tau"])
        _, df = viterbi(cgf)
        cgt = cost_grid(c, r["G"] / 40.0)
        _, dt = viterbi(cgt)
        tot_free += int(df)
        tot_tied += int(dt)
    print(f"  free tau  : {tot_free} mismatched samples")
    print(f"  tau = G/40: {tot_tied} mismatched samples "
          f"({tot_tied - tot_free:+d})")

    # ---- (1) soft curve --------------------------------------------------
    print("\n== P(read HIGH | bit, in-bit phase) ==")
    BW = 25.0
    nb = int(BIT_NS / BW)
    hi = {0: np.zeros(nb), 1: np.zeros(nb)}
    tt = {0: np.zeros(nb), 1: np.zeros(nb)}
    for c in caps:
        r = fin[c["key"]]
        phi = np.array(r["phi"])
        m = c["it"] < NL
        it, sl, lv = c["it"][m], c["sl"][m], c["lv"][m]
        t = 2500.0 * it + phi[it] + r["tau"] * C[sl]
        j = np.floor(t / BIT_NS).astype(np.int64)
        ok = (j >= 0) & (j < 192)
        p = (t - j * BIT_NS)[ok]
        b = c["bits"][j[ok]]
        v = lv[ok]
        k = np.clip((p / BW).astype(int), 0, nb - 1)
        for bb in (0, 1):
            s = b == bb
            np.add.at(tt[bb], k[s], 1)
            np.add.at(hi[bb], k[s], v[s])
    print("  phase[ns]   bit=0 P(hi)  n    | bit=1 P(hi)  n")
    for k in range(nb):
        lo = k * BW
        if not (200 <= lo <= 900):
            continue
        f0 = hi[0][k] / tt[0][k] if tt[0][k] else float("nan")
        f1 = hi[1][k] / tt[1][k] if tt[1][k] else float("nan")
        print("  %4.0f-%4.0f   %6.3f %5d   | %6.3f %5d"
              % (lo, lo + BW, f0, tt[0][k], f1, tt[1][k]))

    # transition widths
    for bb, nom in ((0, H0), (1, H1)):
        ctr = np.array([(k + .5) * BW for k in range(nb)])
        f = np.divide(hi[bb], np.maximum(tt[bb], 1))
        sel = (ctr > nom - 200) & (ctr < nom + 200) & (tt[bb] > 20)
        x, y = ctr[sel], f[sel]
        w = x[(y < 0.95) & (y > 0.05)]
        print(f"  bit={bb}: nominal edge {nom:.0f} ns, "
              f"10-90%% transition spans {w.min():.0f}..{w.max():.0f} ns "
              f"(width {w.max()-w.min():.0f})" if len(w) else
              f"  bit={bb}: transition sharper than the {BW:.0f} ns bin")

    # ---- (3) blind phase track ------------------------------------------
    print("\n== rising-edge-only phase track (no bit knowledge) ==")
    errs = []
    for c in caps:
        r = fin[c["key"]]
        phi = np.array(r["phi"])[:94]
        pb, nris = blind_phase(c, r["tau"])
        e = pb[:94] - phi
        e = e - BIT_NS * np.round(e / BIT_NS)       # per-loop bit unwrap
        errs.append((c["key"], float(np.median(np.abs(e))), float(np.max(np.abs(e))),
                     int(np.count_nonzero(np.abs(e) > 60))))
    a = np.array([[x[1], x[2], x[3]] for x in errs])
    print("  |err| median  : med %.1f  p90 %.1f  max %.1f ns"
          % (np.median(a[:, 0]), np.percentile(a[:, 0], 90), a[:, 0].max()))
    print("  |err| max     : med %.1f  p90 %.1f  max %.1f ns"
          % (np.median(a[:, 1]), np.percentile(a[:, 1], 90), a[:, 1].max()))
    print("  loops with |err|>60 ns: med %.0f of 94, max %d"
          % (np.median(a[:, 2]), a[:, 2].max()))
    worst = sorted(errs, key=lambda x: -x[2])[:5]
    for k, md, mx, n in worst:
        print(f"    worst {k:14s} med {md:5.1f} max {mx:6.1f} n>60 {n}")


if __name__ == "__main__":
    main()
