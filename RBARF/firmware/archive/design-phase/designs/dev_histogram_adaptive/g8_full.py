"""Full blind pipeline with a LOCAL phase tracker + margin ROC + repair.

tau(k) is tracked by local linear regression over a window of W cells
(absorbs the data-dependent loop stretching), then every cell is
classified by its fall phase against per-capture learned clusters.
Reports:
  * cell-level error and margin ROC (is |margin| predictive?)
  * bits assembled, length-constraint violations, header/trailer errors
  * exact payload match before / after constraint repair
"""
import sys
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

GEOM = sys.argv[1] if len(sys.argv) > 1 else "cal"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 10
O, G = (NOM_O, NOM_G) if GEOM == "nom" else (CAL_O, CAL_G)

HDRBITS = [(b >> (7 - k)) & 1 for b in HDR for k in range(8)]
TRLBITS = [(b >> (7 - k)) & 1 for b in TRL for k in range(8)]
KNOWN = [-1] * 192
KNOWN[:32] = HDRBITS
KNOWN[160:] = TRLBITS


def brackets(lv, x):
    ev = edge_list(lv)
    rises, falls = [], []
    if lv[0] == 1:
        rises.append((x[0] - 300.0, x[0], 0))
    for kind, a, b in ev:
        (rises if kind == "R" else falls).append((x[a], x[b], b))
    return rises, falls


def comb(per, lo=1180.0, hi=1330.0, n=6001):
    per = np.asarray(per, float)
    best = None
    for k in range(n):
        P = lo + k * (hi - lo) / (n - 1)
        q = per / P
        s = q <= 4.5
        e = float(np.sum((q[s] - np.round(q[s])) ** 2))
        if best is None or e < best[1]:
            best = (P, e)
    return best[0]


def local_track(rmid, kk, W):
    tau = np.zeros(len(rmid)); Pl = np.zeros(len(rmid))
    for i in range(len(rmid)):
        a = max(0, i - W); b = min(len(rmid), i + W + 1)
        x = kk[a:b].astype(float); y = rmid[a:b]
        A = np.vstack([x, np.ones_like(x)]).T
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        Pl[i] = sol[0]; tau[i] = sol[0] * kk[i] + sol[1]
    return tau, Pl


def two_cluster(v, a=0.30, b=0.59, iters=80):
    v = np.asarray(v)
    for _ in range(iters):
        th = 0.5 * (a + b)
        s = v < th
        if s.any(): a = float(np.median(v[s]))
        if (~s).any(): b = float(np.median(v[~s]))
    return a, b


def pipeline(c, W=10, geom=(CAL_O, CAL_G)):
    O, G = geom
    x = coord(c["it"], c["sl"], O, G)
    rises, falls = brackets(c["lv"], x)
    # pair
    cells = []
    fi = 0
    for i, (ra, rb, rj) in enumerate(rises):
        while fi < len(falls) and falls[fi][2] <= rj:
            fi += 1
        if fi >= len(falls):
            break
        cells.append((ra, rb, rj, falls[fi][0], falls[fi][1], falls[fi][2]))
    ra = np.array([z[0] for z in cells]); rb = np.array([z[1] for z in cells])
    fa = np.array([z[3] for z in cells]); fb = np.array([z[4] for z in cells])
    rmid = 0.5 * (ra + rb)
    P0 = comb(np.diff(rmid))
    kk = None
    for _ in range(3):
        n = np.ones(len(cells), int)
        if kk is None:
            n[:-1] = np.maximum(1, np.round(np.diff(rmid) / P0))
            kk = np.concatenate([[0], np.cumsum(n)[:-1]])
        tau, Pl = local_track(rmid, kk, W)
        # re-quantise periods with the local period
        n = np.ones(len(cells), int)
        n[:-1] = np.maximum(1, np.round(np.diff(rmid) / Pl[:-1]))
        kk2 = np.concatenate([[0], np.cumsum(n)[:-1]])
        if np.array_equal(kk2, kk):
            break
        kk = kk2
    tau, Pl = local_track(rmid, kk, W)
    fmid = 0.5 * (fa + fb)
    mlen = np.maximum(1, np.floor((fmid - tau) / Pl).astype(int) + 1)
    base = tau + (mlen - 1) * Pl
    ph_lo = (fa - base) / Pl
    ph_hi = (fb - base) / Pl
    ph = 0.5 * (ph_lo + ph_hi)
    h0, h1 = two_cluster(ph)
    th = 0.5 * (h0 + h1)
    half = 0.5 * (ph_hi - ph_lo) + 1e-9
    margin = (ph - th) / half
    last = (ph > th).astype(int)
    ncell = np.ones(len(cells), int)
    ncell[:-1] = np.diff(kk)
    return dict(cells=cells, kk=kk, ncell=ncell, mlen=mlen, last=last,
                margin=margin, ph=ph, ph_lo=ph_lo, ph_hi=ph_hi,
                h0=h0, h1=h1, th=th, tau=tau, Pl=Pl, P0=P0)


def assemble(st, total=192):
    kk, ncell, mlen, last = st["kk"], st["ncell"].copy(), st["mlen"], st["last"]
    ncell[-1] = max(1, total - int(kk[-1]))
    bits = []
    for i in range(len(ncell)):
        n = int(ncell[i]); m = int(min(mlen[i], n))
        bits.extend([1] * (m - 1) + [int(last[i])] + [0] * (n - m))
    return bits[:total] + [0] * max(0, total - len(bits))


def main():
    meta, caps = load_all()
    CE = []       # (|margin|, is_error)
    tot = Counter()
    rows = []
    for c in caps:
        st = pipeline(c, W=W, geom=(O, G))
        tt = c["ttrue"]; bits_t = c["bits"]
        # label each cell's fall bit
        for i, z in enumerate(st["cells"]):
            kb = int(np.floor(tt[z[5] - 1] / BIT))
            if not (0 <= kb < 192):
                continue
            err = int(st["last"][i]) != int(bits_t[kb])
            CE.append((abs(st["margin"][i]), err))
            tot["cells"] += 1; tot["cellerr"] += err
        b = np.array(assemble(st))
        t = np.array(bits_t)
        nerr = int((b != t).sum())
        hdr_err = int((b[:32] != t[:32]).sum() + (b[160:] != t[160:]).sum())
        pay = bytes(int("".join(map(str, b[32 + 8 * i:40 + 8 * i])), 2)
                    for i in range(16))
        exact = pay == bytes.fromhex(c["payload"])
        tot["exact"] += int(exact); tot["n"] += 1; tot["biterr"] += nerr
        # length before forcing
        raw_len = int(st["kk"][-1]) + int(st["ncell"][-1])
        tot["len_ok"] += int(raw_len == 192)
        rows.append((c["key"], nerr, hdr_err, raw_len, st["P0"],
                     float(np.median(st["Pl"])), st["h0"], st["h1"]))
    print(f"geom={GEOM} W={W}")
    print("cell classification error %d / %d = %.4f"
          % (tot["cellerr"], tot["cells"], tot["cellerr"] / tot["cells"]))
    print("exact %d/%d   bit errors %d (%.4f/bit)   length==192 in %d/%d"
          % (tot["exact"], tot["n"], tot["biterr"],
             tot["biterr"] / (192 * tot["n"]), tot["len_ok"], tot["n"]))

    CE.sort()
    m = np.array([a for a, _ in CE]); e = np.array([b for _, b in CE])
    print("\n=== margin ROC: fraction of cell errors captured by the "
          "lowest-|margin| cells ===")
    ne = int(e.sum())
    for q in (0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50):
        k = int(q * len(CE))
        print("  lowest %4.1f%% of |margin| (%4d cells) contains %4d / %d "
              "errors (%.1f%%)" % (100 * q, k, int(e[:k].sum()), ne,
                                   100 * e[:k].sum() / max(1, ne)))
    for thr in (0.25, 0.5, 1.0, 2.0):
        sel = m < thr
        print("  |margin| < %.2f : %5d cells, %4d errors -> error rate %.3f "
              "(covers %.1f%% of all errors)"
              % (thr, int(sel.sum()), int(e[sel].sum()),
                 e[sel].sum() / max(1, sel.sum()),
                 100 * e[sel].sum() / max(1, ne)))
    sel = m >= 2.0
    print("  |margin| >= 2.0 : %5d cells, error rate %.5f"
          % (int(sel.sum()), e[sel].sum() / max(1, sel.sum())))

    print("\nper capture:")
    for r in sorted(rows, key=lambda r: -r[1]):
        print("  %-14s biterr=%3d hdr/trl_err=%2d len=%3d P0=%.2f Ploc=%.2f "
              "h=(%.3f,%.3f)" % r)


if __name__ == "__main__":
    main()
