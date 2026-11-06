"""Dead-zone / decision-window analysis on the fitted sampling grid.

Grid:  t(i,s) = T0 + tau * (LOOP_CY*i + C[s]),  LOOP_CY = 40.
Per-capture (T0, tau) is fitted two ways:
  ALL    -- against all 192 known frame bits    (ceiling)
  ANCHOR -- against header bits 0..31 + trailer bits 160..191 only
            (what a real decoder can actually do)
then every sample is mapped to its bit cell + in-bit phase, and we ask
which bits are decidable at all.
"""
import json
import sys
from collections import Counter

import numpy as np

from bm_common import BIT_NS, load

C = np.array([1, 4, 8, 13, 17, 21, 27, 31], float)
LOOP_CY = 40.0
TAU0 = 62.75
H1, H0 = 750.0, 375.0
ANCHOR = np.array(list(range(0, 32)) + list(range(160, 192)))
ALLB = np.arange(192)
NL = 96


def prep(c):
    m = c["it"] < NL
    return (c["it"][m].astype(float), c["sl"][m], c["lv"][m].astype(np.int8))


def times(it, sl, T0, tau):
    return T0 + tau * (LOOP_CY * it + C[sl])


def predict(t, bits, h1=H1, h0=H0):
    j = np.floor(t / BIT_NS).astype(np.int64)
    ok = (j >= 0) & (j < len(bits))
    jc = np.clip(j, 0, len(bits) - 1)
    hw = np.where(bits[jc] == 1, h1, h0)
    return (ok & ((t - jc * BIT_NS) < hw)).astype(np.int8), j


def fit(c, bitsel):
    it, sl, lv = prep(c)
    bits = c["bits"]
    best = (-1, 0.0, TAU0)
    for tau in np.arange(62.0, 63.5, 0.0025):
        for T0 in np.arange(-80.0, 340.0, 6.0):
            pred, j = predict(times(it, sl, T0, tau), bits)
            m = np.isin(j, bitsel)
            n = int(np.count_nonzero(pred[m] == lv[m]))
            if n > best[0]:
                best = (n, T0, tau)
    n, T0, tau = best
    st, sk = 6.0, 0.0025
    while st > 1e-2:
        found = False
        for dt, dk in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            pred, j = predict(times(it, sl, T0 + dt, tau + dk), bits)
            m = np.isin(j, bitsel)
            nn = int(np.count_nonzero(pred[m] == lv[m]))
            if nn > n:
                n, T0, tau, found = nn, T0 + dt, tau + dk, True
                break
        if not found:
            st /= 2.0
            sk /= 2.0
    return T0, tau, n, int(np.isin(np.floor(times(it, sl, T0, tau) / BIT_NS), bitsel).sum())


def analyse(c, T0, tau):
    it, sl, lv = prep(c)
    t = times(it, sl, T0, tau)
    bits = c["bits"]
    j = np.floor(t / BIT_NS).astype(np.int64)
    p = t - j * BIT_NS
    ok = (j >= 0) & (j < 192)
    inf = ok & (p >= H0) & (p < H1)
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
        d = 1 if sum(v) * 2 > len(v) else 0
        if d != int(bits[b]):
            wrong.append(b)
    return blind, wrong, confl, j, p, inf, ok, lv, sl


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
    agg = Counter()
    infhist = Counter()
    slot_inf = Counter()
    slot_n = Counter()
    maxruns = []
    taus = []
    rec = {}
    for c in caps:
        T0a, taua, na, tota = fit(c, ALLB)
        T0h, tauh, nh, toth = fit(c, ANCHOR)
        ba, wa, ca_, j, p, inf, ok, lv, sl = analyse(c, T0a, taua)
        bh, wh, ch, *_ = analyse(c, T0h, tauh)
        pb = [b for b in ba if 32 <= b < 160]
        pw = [b for b in wa if 32 <= b < 160]
        pbh = [b for b in bh if 32 <= b < 160]
        pwh = [b for b in wh if 32 <= b < 160]
        agg["blind"] += len(pb); agg["wrong"] += len(pw)
        agg["confl"] += len([b for b in ca_ if 32 <= b < 160])
        agg["blind_h"] += len(pbh); agg["wrong_h"] += len(pwh)
        agg["mis_all"] += (na and 0) or 0
        agg["samp_bad"] += tota - na
        cnt = Counter(int(x) for x in j[inf])
        for b in range(32, 160):
            infhist[min(cnt.get(b, 0), 4)] += 1
        for s in range(8):
            slot_n[s] += int(np.count_nonzero((sl == s) & ok))
            slot_inf[s] += int(np.count_nonzero((sl == s) & inf))
        mr = max([len(r) for r in runs(pb)] or [0])
        maxruns.append(mr)
        taus.append(taua)
        rec[c["key"]] = dict(T0=T0a, tau=taua, T0h=T0h, tauh=tauh,
                             blind=pb, wrong=pw, blind_h=pbh, wrong_h=pwh,
                             sample_mismatch=tota - na, nsamp=tota)
        print("%-14s tau=%.3f (G=%.1f) dtau_anchor=%+.3f | blind %3d wrong %2d "
              "maxrun %2d | anchor blind %3d wrong %2d | badsamp %3d/%d"
              % (c["key"], taua, taua * 40, tauh - taua, len(pb), len(pw), mr,
                 len(pbh), len(pwh), tota - na, tota), flush=True)

    n = 128 * len(caps)
    print("\n=== payload bits: %d ===" % n)
    print("blind  (ALL fit)   %4d = %.2f%%" % (agg["blind"], 100 * agg["blind"] / n))
    print("wrong  (ALL fit)   %4d = %.2f%%" % (agg["wrong"], 100 * agg["wrong"] / n))
    print("conflict           %4d" % agg["confl"])
    print("blind  (ANCHOR)    %4d = %.2f%%" % (agg["blind_h"], 100 * agg["blind_h"] / n))
    print("wrong  (ANCHOR)    %4d = %.2f%%" % (agg["wrong_h"], 100 * agg["wrong_h"] / n))
    print("informative samples per payload bit:",
          {k: infhist[k] for k in range(5)})
    print("per-slot informative fraction:",
          {s: round(slot_inf[s] / max(slot_n[s], 1), 3) for s in range(8)})
    print("max blind-run per capture: med %.0f max %d" %
          (np.median(maxruns), max(maxruns)))
    print("tau: min %.3f med %.3f max %.3f  (f_cpu %.4f..%.4f MHz, eps %.2f%%..%.2f%%)"
          % (min(taus), float(np.median(taus)), max(taus),
             1000 / max(taus), 1000 / min(taus),
             100 * (62.5 / max(taus) - 1), 100 * (62.5 / min(taus) - 1)))
    json.dump(rec, open("bm_deadzone.json", "w"), indent=1)


if __name__ == "__main__":
    main()
