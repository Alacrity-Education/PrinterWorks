"""Global constraint repair over the adaptive cell classification.

Front end = g8 (local tracker + per-capture cluster fit).
Repair    = small DP over cells:
              state  = bit index k reached so far (0..192)
              action = (n, m, b) for the current cell
              cost   = interval excursion of the predicted fall from the
                       observed fall bracket + of the predicted next rise
                       from the observed next-rise bracket
              hard   = emitted bits must match the known header/trailer
              final  = k == 192
Iterated: after the DP the bit indices change, so tau is refitted and the
DP re-run.
"""
import sys
from collections import Counter

import numpy as np

from g0_common import *
from g8_full import brackets, comb, local_track, two_cluster

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 10
USE_KNOWN = "-noknown" not in sys.argv
USE_LEN = "-nolen" not in sys.argv
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)

HDRBITS = [(b >> (7 - k)) & 1 for b in HDR for k in range(8)]
TRLBITS = [(b >> (7 - k)) & 1 for b in TRL for k in range(8)]
KNOWN = [-1] * 192
KNOWN[:32] = HDRBITS
KNOWN[160:] = TRLBITS
NB = 192
BIG = 1e9


def build_cells(c, geom):
    O, G = geom
    x = coord(c["it"], c["sl"], O, G)
    rises, falls = brackets(c["lv"], x)
    cells = []
    fi = 0
    for i, (ra, rb, rj) in enumerate(rises):
        while fi < len(falls) and falls[fi][2] <= rj:
            fi += 1
        if fi >= len(falls):
            break
        cells.append(dict(ra=ra, rb=rb, rj=rj,
                          fa=falls[fi][0], fb=falls[fi][1], fj=falls[fi][2]))
    return cells


def initial_index(cells, W):
    rmid = np.array([0.5 * (z["ra"] + z["rb"]) for z in cells])
    P0 = comb(np.diff(rmid))
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


def learn_h(cells, kk, tau, Pl):
    fmid = np.array([0.5 * (z["fa"] + z["fb"]) for z in cells])
    mlen = np.maximum(1, np.floor((fmid - tau) / Pl).astype(int) + 1)
    ph = (fmid - tau) / Pl - (mlen - 1)
    return two_cluster(ph), ph, mlen


def dp(cells, tau, Pl, h0, h1, use_known=True, use_len=True,
       nmax=3, mmax=3, wr=1.0, wf=1.0):
    """Return list of (n, m, b) per cell, or None."""
    C = len(cells)
    INF = BIG
    # transition costs
    acts = [[] for _ in range(C)]
    for i, z in enumerate(cells):
        t_i = tau[i]; P_i = Pl[i]
        nxt = cells[i + 1] if i + 1 < C else None
        for m in range(1, mmax + 1):
            for b in (0, 1):
                h = h0 if b == 0 else h1
                tf = t_i + (m - 1 + h) * P_i
                cf = max(0.0, z["fa"] - tf, tf - z["fb"]) / P_i
                for n in range(m, m + nmax):
                    if nxt is None:
                        cr = 0.0
                    else:
                        tr = t_i + n * P_i
                        cr = max(0.0, nxt["ra"] - tr, tr - nxt["rb"]) / P_i
                    acts[i].append((n, m, b, wf * cf + wr * cr))
    # DP
    prev = [INF] * (NB + 1)
    prev[0] = 0.0
    bp = [dict() for _ in range(C)]
    for i in range(C):
        cur = [INF] * (NB + 1)
        last = (i == C - 1)
        for k in range(NB + 1):
            if prev[k] >= INF:
                continue
            base = prev[k]
            for (n, m, b, cst) in acts[i]:
                if last and use_len:
                    n = NB - k
                    if n < m or n > m + nmax - 1 + 4:
                        continue
                k2 = k + n
                if k2 > NB:
                    continue
                if use_known:
                    ok = True
                    for j in range(n):
                        kv = KNOWN[k + j] if k + j < NB else -1
                        if kv < 0:
                            continue
                        val = 1 if j < m - 1 else (b if j == m - 1 else 0)
                        if val != kv:
                            ok = False
                            break
                    if not ok:
                        continue
                v = base + cst
                if v < cur[k2]:
                    cur[k2] = v
                    bp[i][k2] = (k, n, m, b)
        prev = cur
    end = NB if use_len else int(np.argmin(prev))
    if prev[end] >= INF:
        return None
    out = []
    k = end
    for i in range(C - 1, -1, -1):
        if k not in bp[i]:
            return None
        pk, n, m, b = bp[i][k]
        out.append((n, m, b))
        k = pk
    out.reverse()
    return out


def emit(sol):
    bits = []
    for (n, m, b) in sol:
        bits.extend([1] * (m - 1) + [b] + [0] * (n - m))
    return bits


def decode(c, geom, W, use_known=True, use_len=True, iters=3):
    cells = build_cells(c, geom)
    if len(cells) < 80:
        return None
    kk, tau, Pl, rmid, P0 = initial_index(cells, W)
    (h0, h1), ph, mlen = learn_h(cells, kk, tau, Pl)
    sol = None
    for _ in range(iters):
        s = dp(cells, tau, Pl, h0, h1, use_known, use_len)
        if s is None:
            break
        sol = s
        n = np.array([a for a, _, _ in s])
        kk = np.concatenate([[0], np.cumsum(n)[:-1]])
        tau, Pl = local_track(rmid, kk, W)
        # supervised refit of h0/h1 from known-position cells
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
        return None
    return emit(sol)


def main():
    meta, caps = load_all()
    tot = Counter()
    rows = []
    for c in caps:
        for tag, uk, ul in (("front-end", False, False),
                            ("len-only", False, True),
                            ("full", USE_KNOWN, USE_LEN)):
            b = decode(c, (O, G), W, use_known=uk, use_len=ul)
            if b is None:
                tot[(tag, "fail")] += 1
                continue
            b = (b + [0] * NB)[:NB]
            b = np.array(b)
            t = np.array(c["bits"])
            nerr = int((b != t).sum())
            pay = bytes(int("".join(map(str, b[32 + 8 * i:40 + 8 * i])), 2)
                        for i in range(16))
            ex = pay == bytes.fromhex(c["payload"])
            tot[(tag, "exact")] += int(ex)
            tot[(tag, "n")] += 1
            tot[(tag, "biterr")] += nerr
            if tag == "full":
                rows.append((c["key"], nerr, ex))
    for tag in ("front-end", "len-only", "full"):
        n = max(1, tot[(tag, "n")])
        print("%-10s exact %2d/%2d  biterr %4d (%.4f/bit)  fails %d"
              % (tag, tot[(tag, "exact")], n, tot[(tag, "biterr")],
                 tot[(tag, "biterr")] / (NB * n), tot[(tag, "fail")]))
    print("\nremaining errors (full):")
    for k, e, ex in sorted(rows, key=lambda r: -r[1]):
        if e:
            print("   %-14s biterr=%3d exact=%d" % (k, e, ex))


if __name__ == "__main__":
    main()
