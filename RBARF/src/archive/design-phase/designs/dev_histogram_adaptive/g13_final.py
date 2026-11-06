NMAX, MMAX = 3, 3
"""Recommended configuration, scored by train (reps 0,1) / holdout (rep 2)."""
import sys
from collections import Counter

import numpy as np

import sys as _s
_argv=list(_s.argv)
_s.argv=[_argv[0]]
from g0_common import *
from g8_full import local_track, comb
from g9_repair import build_cells, learn_h, KNOWN, NB, BIG
_s.argv=_argv


def dp(cells, tau, Pl, h0, h1, eps, wr):
    C = len(cells)
    acts = []
    for i, z in enumerate(cells):
        t_i, P_i = tau[i], Pl[i]
        nxt = cells[i + 1] if i + 1 < C else None
        fmid = 0.5 * (z["fa"] + z["fb"])
        nmid = 0.5 * (nxt["ra"] + nxt["rb"]) if nxt else None
        A = []
        for m in range(1, MMAX + 1):
            for b in (0, 1):
                h = h0 if b == 0 else h1
                tf = t_i + (m - 1 + h) * P_i
                cf = max(0.0, z["fa"] - tf, tf - z["fb"]) / P_i
                cf += eps * ((tf - fmid) / P_i) ** 2
                for n in range(m, m + NMAX):
                    if nxt is None:
                        cr = 0.0
                    else:
                        tr = t_i + n * P_i
                        cr = max(0.0, nxt["ra"] - tr, tr - nxt["rb"]) / P_i
                        cr += eps * ((tr - nmid) / P_i) ** 2
                    A.append((n, m, b, cf + wr * cr))
        acts.append(A)
    prev = np.full(NB + 1, BIG)
    prev[0] = 0.0
    bp = [dict() for _ in range(C)]
    for i in range(C):
        cur = np.full(NB + 1, BIG)
        last = (i == C - 1)
        for k in range(NB + 1):
            v = prev[k]
            if v >= BIG:
                continue
            for (n, m, b, cst) in acts[i]:
                if last:
                    n = NB - k
                    if not (m <= n <= m + 6):
                        continue
                if k + n > NB:
                    continue
                ok = True
                for j in range(n):
                    kv = KNOWN[k + j]
                    if kv < 0:
                        continue
                    val = 1 if j < m - 1 else (b if j == m - 1 else 0)
                    if val != kv:
                        ok = False
                        break
                if not ok:
                    continue
                if v + cst < cur[k + n]:
                    cur[k + n] = v + cst
                    bp[i][k + n] = (k, n, m, b)
        prev = cur
    if prev[NB] >= BIG:
        return None
    k = NB
    out = []
    for i in range(C - 1, -1, -1):
        if k not in bp[i]:
            return None
        pk, n, m, b = bp[i][k]
        out.append((n, m, b))
        k = pk
    out.reverse()
    return out




W = int(sys.argv[1]) if len(sys.argv) > 1 else 3
EPSC = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1


def initial_index(cells, W, lo=1080.0, hi=1420.0):
    rmid = np.array([0.5 * (z["ra"] + z["rb"]) for z in cells])
    P0 = comb(np.diff(rmid), lo=lo, hi=hi)
    n = np.ones(len(cells), int)
    n[:-1] = np.maximum(1, np.round(np.diff(rmid) / P0))
    kk = np.concatenate([[0], np.cumsum(n)[:-1]])
    for _ in range(3):
        tau, Pl = local_track(rmid, kk, W)
        n = np.ones(len(cells), int)
        n[:-1] = np.maximum(1, np.round(np.diff(rmid) / Pl[:-1]))
        kk2 = np.concatenate([[0], np.cumsum(n)[:-1]])
        if np.array_equal(kk2, kk):
            break
        kk = kk2
    tau, Pl = local_track(rmid, kk, W)
    return kk, tau, Pl, rmid, P0


def decode(c, geom, W, epsc, iters=3):
    cells = build_cells(c, geom)
    kk, tau, Pl, rmid, P0 = initial_index(cells, W)
    (h0, h1), ph, mlen = learn_h(cells, kk, tau, Pl)
    sol = None
    for _ in range(iters):
        s = dp(cells, tau, Pl, h0, h1, epsc, 1.0)
        if s is None:
            break
        sol = s
        n = np.array([a for a, _, _ in s])
        kk = np.concatenate([[0], np.cumsum(n)[:-1]])
        tau, Pl = local_track(rmid, kk, W)
        fmid = np.array([0.5 * (z["fa"] + z["fb"]) for z in cells])
        lab, val = [], []
        for i, (nn, mm, bb) in enumerate(s):
            kb = kk[i] + mm - 1
            if kb < NB and KNOWN[kb] >= 0:
                lab.append(KNOWN[kb])
                val.append((fmid[i] - tau[i]) / Pl[i] - (mm - 1))
        if len(lab) > 8:
            lab = np.array(lab); val = np.array(val)
            if (lab == 0).any(): h0 = float(np.median(val[lab == 0]))
            if (lab == 1).any(): h1 = float(np.median(val[lab == 1]))
    if sol is None:
        return None, (h0, h1, float(np.median(Pl)), len(cells))
    bits = []
    for (n, m, b) in sol:
        bits.extend([1] * (m - 1) + [b] + [0] * (n - m))
    return np.array((bits + [0] * NB)[:NB]), (h0, h1, float(np.median(Pl)),
                                              len(cells))


meta, caps = load_all()
for gname, geom in (("nominal", (NOM_O, NOM_G)), ("calibrated", (CAL_O, CAL_G))):
    agg = {}
    hs = []
    for c in caps:
        b, info = decode(c, geom, W, EPSC)
        split = "train" if c["rep"] in (0, 1) else "holdout"
        st = agg.setdefault(split, Counter())
        st["n"] += 1
        hs.append(info)
        if b is None:
            st["fail"] += 1
            continue
        t = np.array(c["bits"])
        st["biterr"] += int((b != t).sum())
        pay = bytes(int("".join(map(str, b[32 + 8 * i:40 + 8 * i])), 2)
                    for i in range(16))
        st["exact"] += int(pay == bytes.fromhex(c["payload"]))
        st["bytes_ok"] += sum(1 for i in range(16)
                              if pay[i] == bytes.fromhex(c["payload"])[i])
    print(f"geometry={gname}  W={W} eps_center={EPSC}")
    for split in ("train", "holdout"):
        s = agg[split]
        print("   %-8s exact %2d/%2d (%.1f%%)  byte-acc %.1f%%  biterr %3d "
              "(%.4f/bit)  fails %d"
              % (split, s["exact"], s["n"], 100 * s["exact"] / s["n"],
                 100 * s["bytes_ok"] / (16 * s["n"]), s["biterr"],
                 s["biterr"] / (NB * s["n"]), s["fail"]))
    h0 = np.array([x[0] for x in hs]); h1 = np.array([x[1] for x in hs])
    P = np.array([x[2] for x in hs]); nc = np.array([x[3] for x in hs])
    print("   learned h0 %.3f..%.3f (med %.3f)  h1 %.3f..%.3f (med %.3f)"
          % (h0.min(), h0.max(), np.median(h0),
             h1.min(), h1.max(), np.median(h1)))
    print("   local P %.1f..%.1f (med %.1f) receiver-ns   cells %d..%d"
          % (P.min(), P.max(), np.median(P), nc.min(), nc.max()))
