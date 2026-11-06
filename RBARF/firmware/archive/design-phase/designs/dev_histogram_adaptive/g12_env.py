"""Envelope sweep on synthetic captures (nominal slot geometry).

synth.py's sampler matches the NOMINAL slot layout, so the receiver
coordinate here uses NOM_O/NOM_G.  Sweeps the HSI error eps and reports
the front-end + repair performance, plus how the artifact rates (swallowed
zeros / merged ones) move with eps.
"""
import sys
from collections import Counter

import numpy as np

from g0_common import *
from g8_full import brackets, comb, local_track, two_cluster
from g9_repair import KNOWN, NB, BIG, learn_h


def initial_index(cells, W, lo=1080.0, hi=1420.0):
    """Same as g9.initial_index but with a comb range wide enough for the
    full +/-7.5% HSI envelope (P_receiver = BIT*(1+eps) in nominal ns)."""
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

sys.path.insert(0, str(R))
sys.path.insert(0, str(R.parent / "bench"))
import synth  # noqa: E402
from patterns import PATTERNS  # noqa: E402

W = 10
NMAX, MMAX = 3, 3
O, G = NOM_O, NOM_G


def build_cells_raw(samples):
    it = np.array([a for a, _, _ in samples])
    sl = np.array([b for _, b, _ in samples])
    lv = np.array([v for _, _, v in samples], dtype=np.int8)
    x = coord(it, sl, O, G)
    rises, falls = brackets(lv, x)
    cells, fi = [], 0
    for i, (ra, rb, rj) in enumerate(rises):
        while fi < len(falls) and falls[fi][2] <= rj:
            fi += 1
        if fi >= len(falls):
            break
        cells.append(dict(ra=ra, rb=rb, rj=rj, fa=falls[fi][0],
                          fb=falls[fi][1], fj=falls[fi][2]))
    return cells, lv


def dp(cells, tau, Pl, h0, h1, eps=0.25, wr=1.0):
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
    prev = np.full(NB + 1, BIG); prev[0] = 0.0
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
                        ok = False; break
                if not ok:
                    continue
                if v + cst < cur[k + n]:
                    cur[k + n] = v + cst
                    bp[i][k + n] = (k, n, m, b)
        prev = cur
    if prev[NB] >= BIG:
        return None
    k, out = NB, []
    for i in range(C - 1, -1, -1):
        if k not in bp[i]:
            return None
        pk, n, m, b = bp[i][k]
        out.append((n, m, b)); k = pk
    out.reverse()
    return out


def decode(samples, iters=3):
    cells, lv = build_cells_raw(samples)
    if len(cells) < 60:
        return None, len(cells)
    kk, tau, Pl, rmid, P0 = initial_index(cells, W)
    (h0, h1), ph, mlen = learn_h(cells, kk, tau, Pl)
    sol = None
    for _ in range(iters):
        s = dp(cells, tau, Pl, h0, h1)
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
                lab.append(KNOWN[kb]); val.append((fmid[i] - tau[i]) / Pl[i] - (mm - 1))
        if len(lab) > 8:
            lab = np.array(lab); val = np.array(val)
            if (lab == 0).any(): h0 = float(np.median(val[lab == 0]))
            if (lab == 1).any(): h1 = float(np.median(val[lab == 1]))
    if sol is None:
        return None, len(cells)
    bits = []
    for (n, m, b) in sol:
        bits.extend([1] * (m - 1) + [b] + [0] * (n - m))
    return np.array((bits + [0] * NB)[:NB]), len(cells)


def main():
    for eps in (-0.08, -0.075, -0.05, -0.025, 0.0, 0.025, 0.05, 0.075):
        tot = Counter()
        ncells = []
        for name, payload in PATTERNS.items():
            for rep in range(2):
                ph = (rep * 83.0) % 250.0
                s = synth.synth_capture(payload, eps=eps, phase_ns=ph)
                bits, nc = decode(s)
                ncells.append(nc)
                tot["n"] += 1
                if bits is None:
                    tot["fail"] += 1
                    continue
                fr = HDR + payload + TRL
                t = np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)])
                tot["biterr"] += int((bits != t).sum())
                pay = bytes(int("".join(map(str, bits[32 + 8 * i:40 + 8 * i])), 2)
                            for i in range(16))
                tot["exact"] += int(pay == payload)
        print("eps=%+6.3f  exact %2d/%2d  biterr %4d (%.4f/bit)  fail %d  "
              "median cells %.0f (192 = no artifacts)"
              % (eps, tot["exact"], tot["n"], tot["biterr"],
                 tot["biterr"] / (NB * max(1, tot["n"])), tot["fail"],
                 np.median(ncells)))


if __name__ == "__main__":
    main()
