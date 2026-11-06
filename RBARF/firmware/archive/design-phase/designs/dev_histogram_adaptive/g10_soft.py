"""Soft outputs: constrained max-marginals from the repair DP.

Forward/backward min-cost tables give, for every cell and every value of
its (n, m, b) action, the cost of the best CONSTRAINT-SATISFYING global
solution containing that action.  The per-bit score is

    LLR(k) = min-cost(any solution with bit k = 0)
             - min-cost(any solution with bit k = 1)

which is exactly the soft decision the fusion stage wants.  Measures how
well |LLR| ranks the surviving errors, and the N-best list-decoding depth
needed to contain the truth.
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *
from g8_full import brackets, comb, local_track, two_cluster
from g9_repair import (build_cells, initial_index, learn_h, KNOWN, NB, BIG,
                       emit)

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 10
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)
NMAX, MMAX = 3, 3


def actions(cells, tau, Pl, h0, h1):
    C = len(cells)
    acts = []
    for i, z in enumerate(cells):
        t_i, P_i = tau[i], Pl[i]
        nxt = cells[i + 1] if i + 1 < C else None
        A = []
        for m in range(1, MMAX + 1):
            for b in (0, 1):
                h = h0 if b == 0 else h1
                tf = t_i + (m - 1 + h) * P_i
                cf = max(0.0, z["fa"] - tf, tf - z["fb"]) / P_i
                for n in range(m, m + NMAX):
                    if nxt is None:
                        cr = 0.0
                    else:
                        tr = t_i + n * P_i
                        cr = max(0.0, nxt["ra"] - tr, tr - nxt["rb"]) / P_i
                    A.append((n, m, b, cf + cr))
        acts.append(A)
    return acts


def feasible(k, n, m, b, use_known=True):
    if not use_known:
        return True
    for j in range(n):
        if k + j >= NB:
            return False
        kv = KNOWN[k + j]
        if kv < 0:
            continue
        val = 1 if j < m - 1 else (b if j == m - 1 else 0)
        if val != kv:
            return False
    return True


def fwd_bwd(acts, C, use_known=True):
    F = np.full((C + 1, NB + 1), BIG)
    F[0, 0] = 0.0
    for i in range(C):
        for k in range(NB + 1):
            v = F[i, k]
            if v >= BIG:
                continue
            for (n, m, b, cst) in acts[i]:
                if i == C - 1:
                    n2 = NB - k
                    if not (m <= n2 <= m + 6):
                        continue
                    n = n2
                if k + n > NB or not feasible(k, n, m, b, use_known):
                    continue
                if v + cst < F[i + 1, k + n]:
                    F[i + 1, k + n] = v + cst
    B = np.full((C + 1, NB + 1), BIG)
    B[C, NB] = 0.0
    for i in range(C - 1, -1, -1):
        for k in range(NB + 1):
            best = BIG
            for (n, m, b, cst) in acts[i]:
                if i == C - 1:
                    n2 = NB - k
                    if not (m <= n2 <= m + 6):
                        continue
                    n = n2
                if k + n > NB or not feasible(k, n, m, b, use_known):
                    continue
                v = cst + B[i + 1, k + n]
                if v < best:
                    best = v
            B[i, k] = best
    return F, B


def bit_marginals(acts, F, B, C, use_known=True):
    """cost0[k], cost1[k] : best global cost with bit k emitted as 0 / 1."""
    c0 = np.full(NB, BIG)
    c1 = np.full(NB, BIG)
    for i in range(C):
        for k in range(NB + 1):
            if F[i, k] >= BIG:
                continue
            for (n, m, b, cst) in acts[i]:
                if i == C - 1:
                    n2 = NB - k
                    if not (m <= n2 <= m + 6):
                        continue
                    n = n2
                if k + n > NB or not feasible(k, n, m, b, use_known):
                    continue
                tot = F[i, k] + cst + B[i + 1, k + n]
                if tot >= BIG:
                    continue
                for j in range(n):
                    val = 1 if j < m - 1 else (b if j == m - 1 else 0)
                    tgt = c1 if val else c0
                    if tot < tgt[k + j]:
                        tgt[k + j] = tot
    return c0, c1


def main():
    meta, caps = load_all()
    rec = []
    tot = Counter()
    for c in caps:
        cells = build_cells(c, (O, G))
        kk, tau, Pl, rmid, P0 = initial_index(cells, W)
        (h0, h1), ph, mlen = learn_h(cells, kk, tau, Pl)
        C = len(cells)
        for _ in range(3):
            acts = actions(cells, tau, Pl, h0, h1)
            F, B = fwd_bwd(acts, C)
            if F[C, NB] >= BIG:
                break
            # viterbi path
            k = NB
            path = []
            for i in range(C - 1, -1, -1):
                found = None
                for (n, m, b, cst) in acts[i]:
                    if i == C - 1:
                        n2 = NB - 0
                    for kp in range(0, k + 1):
                        pass
                    break
                break
            c0, c1 = bit_marginals(acts, F, B, C)
            bits = (c0 > c1).astype(int)
            # refit tau from the decoded bit grid: cell i's k index
            # recover a consistent path greedily from marginals
            break
        t = np.array(c["bits"])
        nerr = int((bits != t).sum())
        llr = c0 - c1
        pay = bytes(int("".join(map(str, bits[32 + 8 * i:40 + 8 * i])), 2)
                    for i in range(16))
        ex = pay == bytes.fromhex(c["payload"])
        tot["exact"] += int(ex); tot["n"] += 1; tot["biterr"] += nerr
        for k in range(NB):
            if KNOWN[k] >= 0:
                continue
            rec.append((abs(llr[k]), int(bits[k] != t[k])))
        # list decoding depth: how many bits must be revisited
        idx = np.argsort(np.abs(llr))
        bad = [int(np.where(idx == k)[0][0]) for k in range(NB)
               if bits[k] != t[k] and KNOWN[k] < 0]
        tot_depth = max(bad) + 1 if bad else 0
        rec.append if False else None
        tot["depth_sum"] += tot_depth
        if nerr:
            tot["capwitherr"] += 1
            tot["maxdepth"] = max(tot["maxdepth"], tot_depth)
        print("  %-14s biterr=%3d exact=%d worst-error-rank=%d"
              % (c["key"], nerr, ex, tot_depth))
    n = tot["n"]
    print("\nmarginal decode: exact %d/%d  biterr %d (%.4f/bit)"
          % (tot["exact"], n, tot["biterr"], tot["biterr"] / (NB * n)))
    r = sorted(rec)
    a = np.array([x for x, _ in r]); e = np.array([y for _, y in r])
    ne = int(e.sum())
    print("\n=== |LLR| ROC over payload bits (%d bits, %d errors) ===" % (len(r), ne))
    for q in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20):
        k = int(q * len(r))
        print("  lowest %5.1f%% |LLR| (%4d bits) holds %3d/%d errors (%.1f%%)"
              % (100 * q, k, int(e[:k].sum()), ne, 100 * e[:k].sum() / max(1, ne)))
    for thr in (0.0, 0.02, 0.05, 0.1, 0.2, 0.5):
        sel = a <= thr
        if sel.sum():
            print("  |LLR| <= %.2f : %5d bits, %3d errors (rate %.3f, %.1f%% of all)"
                  % (thr, int(sel.sum()), int(e[sel].sum()),
                     e[sel].sum() / sel.sum(), 100 * e[sel].sum() / max(1, ne)))
    sel = a > 0.5
    print("  |LLR| >  0.50 : %5d bits, error rate %.5f"
          % (int(sel.sum()), e[sel].sum() / max(1, sel.sum())))
    print("\nmax worst-error-rank over captures:", tot["maxdepth"],
          " (a list decoder flipping the K lowest-|LLR| payload bits needs "
          "K >= that)")


if __name__ == "__main__":
    main()
