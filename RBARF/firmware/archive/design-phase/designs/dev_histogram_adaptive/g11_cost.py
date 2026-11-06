"""Sweep the cell cost model: hinge-only vs hinge + centering term."""
import sys
from collections import Counter

import numpy as np

from g0_common import *
from g8_full import local_track
from g9_repair import (build_cells, initial_index, learn_h, KNOWN, NB, BIG)

GEOM = "cal"
O, G = CAL_O, CAL_G
W = 10
NMAX, MMAX = 3, 3


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


def run(eps, wr, iters=3):
    tot = Counter()
    for c in caps:
        cells = build_cells(c, (O, G))
        kk, tau, Pl, rmid, P0 = initial_index(cells, W)
        (h0, h1), ph, mlen = learn_h(cells, kk, tau, Pl)
        sol = None
        for _ in range(iters):
            s = dp(cells, tau, Pl, h0, h1, eps, wr)
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
                if (lab == 0).any():
                    h0 = float(np.median(val[lab == 0]))
                if (lab == 1).any():
                    h1 = float(np.median(val[lab == 1]))
        if sol is None:
            tot["fail"] += 1
            continue
        bits = []
        for (n, m, b) in sol:
            bits.extend([1] * (m - 1) + [b] + [0] * (n - m))
        bits = np.array((bits + [0] * NB)[:NB])
        t = np.array(c["bits"])
        tot["biterr"] += int((bits != t).sum())
        pay = bytes(int("".join(map(str, bits[32 + 8 * i:40 + 8 * i])), 2)
                    for i in range(16))
        tot["exact"] += int(pay == bytes.fromhex(c["payload"]))
        tot["n"] += 1
    return tot


meta, caps = load_all()
for eps in (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0):
    for wr in (0.5, 1.0, 2.0):
        t = run(eps, wr)
        print("eps=%.2f wr=%.1f : exact %2d/%2d biterr %4d (%.4f/bit) fail %d"
              % (eps, wr, t["exact"], t["n"], t["biterr"],
                 t["biterr"] / (NB * max(1, t["n"])), t["fail"]))
