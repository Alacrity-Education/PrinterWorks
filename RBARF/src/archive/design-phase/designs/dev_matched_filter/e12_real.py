"""E12: the technique on REAL captures, with anchor-driven per-slot
calibration.  Nothing but the 64 known anchor bits is used to fit the grid;
the payload is then read off the same grid.  Ground truth is used ONLY to
score afterwards.

  grid:  t(i,s) = t0 + kappa * ( i*G + P[s] + d[s] ),  d[0] = 0
  fit :  (t0, kappa)              from header, then header+trailer
         d[1..7], h1, h0          coordinate ascent on the anchor score
"""
import json
import sys
from collections import Counter

import numpy as np

from common import load, bits_of, HEADER, TRAILER, BIT_NS

G_CY = 40.0
P0 = np.array([0., 4., 8., 12., 16., 20., 26., 31.])
HDR = bits_of(HEADER).astype(bool)
TRL = bits_of(TRAILER).astype(bool)
T_TRL0 = 160 * BIT_NS
T_END = 192 * BIT_NS
N_HDR = 112
NW = 900


def seg(t, obs, bits, t_lo, t_hi):
    m = (t >= t_lo) & (t < t_hi)
    if not m.any():
        return -10 ** 6, 0
    tt = t[m] - t_lo
    j = np.clip(np.floor(tt / BIT_NS).astype(int), 0, len(bits) - 1)
    p = tt - j * BIT_NS
    return m, j, p, obs[m]


def anchor_score(u, obs, t0, k, h1, h0, hdr=True, trl=True):
    t = t0 + k * u
    s = 0
    n = 0
    for use, bits, lo, hi in ((hdr, HDR, 0.0, 32 * BIT_NS),
                              (trl, TRL, T_TRL0, T_END)):
        if not use:
            continue
        r = seg(t, obs, bits, lo, hi)
        if r[0] is -10 ** 6 or (isinstance(r[0], int)):
            return -10 ** 6, 0
        _, j, p, o = r
        if len(j) < 20:
            return -10 ** 6, 0
        pred = p < np.where(bits[j], h1, h0)
        s += int((pred == o).sum()) - int((pred != o).sum())
        n += len(j)
    return s, n


def coarse_hdr(u, obs, h1, h0, t0s, ks):
    best = (-1e18, 0., 62.5)
    uh, oh = u[:N_HDR], obs[:N_HDR]
    for k in ks:
        t = t0s[:, None] + k * uh[None, :]
        j = np.floor(t / BIT_NS).astype(int)
        inb = (j >= 0) & (j < 32)
        jj = np.clip(j, 0, 31)
        p = t - jj * BIT_NS
        pred = p < np.where(HDR[jj], h1, h0)
        s = np.where(inb, np.where(pred == oh[None, :], 1, -1), 0).sum(1)
        a = int(np.argmax(s))
        if s[a] > best[0]:
            best = (float(s[a]), float(t0s[a]), float(k))
    return best[1], best[2]


def joint(u, obs, t0, k, h1, h0, kw=0.5, tw=40.0):
    b = (-1e18, t0, k)
    for kk in np.arange(k - kw, k + kw, 0.004):
        for tt in np.arange(max(0., t0 - tw), t0 + tw, 2.0):
            v = anchor_score(u, obs, tt, kk, h1, h0)[0]
            if v > b[0]:
                b = (v, tt, kk)
    s, t0, k = b
    st, sk = 2.0, 0.02
    while st > 1e-3:
        f = None
        for da, db in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            v = anchor_score(u, obs, t0 + da, k + db, h1, h0)[0]
            if v > s:
                s, f = v, (t0 + da, k + db)
        if f is None:
            st /= 2
            sk /= 2
        else:
            t0, k = f
    return s, t0, k


def fit_capture(it, sl, obs, nslot_rounds=3, h1=750.0, h0=375.0):
    d = np.zeros(8)
    t0 = k = None
    best = -1e18
    for rnd in range(nslot_rounds):
        u = it * G_CY + (P0 + d)[sl]
        if t0 is None:
            t0, k = coarse_hdr(u, obs, h1, h0,
                               np.arange(0., 460., 4.), np.arange(56., 69., 0.02))
        best, t0, k = joint(u, obs, t0, k, h1, h0)
        if rnd == nslot_rounds - 1:
            break
        for step in (1.0, 0.5, 0.25):
            for s in range(1, 8):
                cur = d[s]
                for v in np.arange(cur - 2 * step, cur + 2 * step + 1e-9, step):
                    dd = d.copy()
                    dd[s] = v
                    uu = it * G_CY + (P0 + dd)[sl]
                    sc, tt, kk = joint(uu, obs, t0, k, h1, h0, kw=0.06, tw=8.0)
                    if sc > best:
                        best, d, t0, k = sc, dd, tt, kk
            for nm in ("h1", "h0"):
                cur = h1 if nm == "h1" else h0
                for v in np.arange(cur - 60, cur + 60.1, 20.0):
                    a = v if nm == "h1" else h1
                    b = h0 if nm == "h1" else v
                    uu = it * G_CY + (P0 + d)[sl]
                    sc, tt, kk = joint(uu, obs, t0, k, a, b, kw=0.06, tw=8.0)
                    if sc > best:
                        best, t0, k = sc, tt, kk
                        h1, h0 = a, b
    u = it * G_CY + (P0 + d)[sl]
    return t0, k, d, h1, h0, best, u


def read_cells(u, obs, t0, k, h1, h0):
    t = t0 + k * u
    hard = np.zeros(128, int)
    marg = np.zeros(128, int)
    ndis = np.zeros(128, int)
    imp = 0
    for j in range(32, 160):
        lo = j * BIT_NS
        m = (t >= lo) & (t < lo + BIT_NS)
        if not m.any():
            continue
        p, o = t[m] - lo, obs[m]
        s1 = int(((p < h1) == o).sum()) - int(((p < h1) != o).sum())
        s0 = int(((p < h0) == o).sum()) - int(((p < h0) != o).sum())
        hard[j - 32] = 1 if s1 > s0 else 0
        marg[j - 32] = s1 - s0
        ndis[j - 32] = int(((p >= h0) & (p < h1)).sum())
        imp += int(((p >= h1) & o).sum())
    return hard, marg, ndis, imp


def main():
    meta, caps = load()
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    tot = Counter()
    runs = Counter()
    out = {}
    for c in caps:
        it = c["it"][:NW].astype(float)
        sl = c["sl"][:NW]
        obs = c["lv"][:NW].astype(bool)
        t0, k, d, h1, h0, sc, u = fit_capture(it, sl, obs, rounds)
        hard, marg, ndis, imp = read_cells(u, obs, t0, k, h1, h0)
        truth = c["bits"][32:160]
        bad = hard != truth
        dec = ndis > 0
        tot["nb"] += 128
        tot["era"] += int((~dec).sum())
        tot["errd"] += int((bad & dec).sum())
        tot["err"] += int(bad.sum())
        tot["imp"] += imp
        tot["ex"] += int(not bad.any())
        tot["cap"] += 1
        cur = 0
        for v in ~dec:
            if v:
                cur += 1
            elif cur:
                runs[cur] += 1
                cur = 0
        if cur:
            runs[cur] += 1
        out[c["key"]] = dict(t0=t0, k=k, d=list(d), h1=h1, h0=h0,
                             anchor=sc, era=int((~dec).sum()),
                             errdec=int((bad & dec).sum()), err=int(bad.sum()))
        print(f"{c['key']:14s} t0={t0:6.1f} k={k:.4f} loop={40*k:7.1f} "
              f"d={np.round(d,2)} h1={h1:.0f} h0={h0:.0f} anch={sc:4d} "
              f"era={int((~dec).sum()):3d} errdec={int((bad&dec).sum()):3d} "
              f"err={int(bad.sum()):3d}", flush=True)
    n = tot["nb"]
    print(f"\nTOTAL erasures {100*tot['era']/n:.2f}%  "
          f"BER(decidable) {100*tot['errd']/max(n-tot['era'],1):.3f}%  "
          f"BER(all) {100*tot['err']/n:.2f}%  impossible/cap {tot['imp']/tot['cap']:.2f}  "
          f"exact {tot['ex']}/{tot['cap']}")
    print("erasure run lengths:", dict(sorted(runs.items())))
    json.dump(out, open("e12_real.json", "w"), indent=1, default=float)


main()
