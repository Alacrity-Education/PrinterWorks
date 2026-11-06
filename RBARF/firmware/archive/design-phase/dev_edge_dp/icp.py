"""Alternating (ICP-style) calibration of slot offsets from level violations."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset
from soft import prep, cost, BIT, NB, FRAME_END

MAXCORR = 420.0


def fit_pt(pr, off, P0=None, t00=None, alpha=0.0):
    it, sl, lv, bits, anchor, prev = pr
    if P0 is None:
        (i1, s1, _), (i2, s2, _) = anchor
        f1 = i1 + off[s1] / 2500.0
        f2 = i2 + off[s2] / 2500.0
        lo = (FRAME_END - 700.0) / f2 - 2.5
        hi = (FRAME_END + 100.0) / f1 + 2.5
        best = None
        for P in np.arange(lo, hi, 0.2):
            for t0 in np.arange(-120.0, 720.0, 8.0):
                c = cost(it, sl, lv, bits, off, P, t0, prev, alpha)
                if best is None or c < best[0]:
                    best = (c, P, t0)
        cur, P, t0 = best
    else:
        P, t0 = P0, t00
        cur = cost(it, sl, lv, bits, off, P, t0, prev, alpha)
    dr = 0.0
    for _ in range(120):
        imp = False
        for st in (0.6, 0.2, 0.06, 0.02):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P + d, t0, prev, alpha, dr)
                if c < cur - 1e-9:
                    cur, P = c, P + d; imp = True
        for st in (6.0, 2.0, 0.6, 0.2):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P, t0 + d, prev, alpha, dr)
                if c < cur - 1e-9:
                    cur, t0 = c, t0 + d; imp = True
        for st in (0.02, 0.006, 0.002):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P, t0, prev, alpha, dr + d)
                if c < cur - 1e-9:
                    cur, dr = c, dr + d; imp = True
        if not imp:
            break
    return cur, P, t0, dr


def corrections(pr, off, P, t0, dr):
    it, sl, lv, bits, anchor, prev = pr
    t = t0 + P * it + dr * it * it + np.asarray(off)[sl]
    kf = np.floor(t / BIT)
    k = kf.astype(np.int64)
    ph = t - kf * BIT
    ok = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    th = np.where(bits[kk] > 0, 700.0, 350.0)
    thn = np.where(bits[np.clip(kk + 1, 0, NB - 1)] > 0, 700.0, 350.0)
    corr = np.zeros_like(t)
    # level 1 but phase >= th  -> move earlier by (ph-th) or later to next bit
    m = ok & (lv == 1) & (ph >= th)
    back = -(ph - th)
    fwd = BIT - ph
    corr = np.where(m, np.where(np.abs(back) <= fwd, back, fwd), corr)
    # level 0 but phase < th -> move later by (th-ph) or earlier into prev low
    m0 = ok & (lv == 0) & (ph < th)
    fwd0 = th - ph
    back0 = -(ph + 1.0)
    corr = np.where(m0, np.where(fwd0 <= np.abs(back0), fwd0, back0), corr)
    good = ok & (np.abs(corr) < MAXCORR)
    return corr, good, sl, prev, kk


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    off = [62.5 * (x - 1) for x in [1, 5, 9, 13, 17, 21, 27, 32]]
    warm = [None] * len(preps)
    for rnd in range(8):
        tot = 0.0
        allc = [[] for _ in range(8)]
        bylev = [[[], []] for _ in range(8)]
        for n, pr in enumerate(preps):
            if warm[n] is None:
                c, P, t0, dr = fit_pt(pr, off)
            else:
                c, P, t0, dr = fit_pt(pr, off, warm[n][0], warm[n][1])
            warm[n] = (P, t0, dr)
            tot += c
            corr, good, sl, prev, _ = corrections(pr, off, P, t0, dr)
            for s in range(8):
                m = good & (sl == s) & (corr != 0.0)
                vals = corr[m]
                allc[s].extend(vals.tolist())
                for L in (0, 1):
                    m2 = m & (prev == L)
                    bylev[s][L].extend(corr[m2].tolist())
        print('round %d  soft cost %.1f (mean %.2f)  off=%s' % (
            rnd, tot, tot / len(preps), ['%.1f' % x for x in off]))
        for s in range(8):
            v = np.array(allc[s]) if allc[s] else np.array([0.0])
            v0 = np.array(bylev[s][0]) if bylev[s][0] else np.array([0.0])
            v1 = np.array(bylev[s][1]) if bylev[s][1] else np.array([0.0])
            print('   slot%d n=%4d med=%+7.1f  prev0 n=%4d med=%+7.1f | prev1 n=%4d med=%+7.1f'
                  % (s, len(v), np.median(v), len(v0), np.median(v0), len(v1), np.median(v1)))
        sys.stdout.flush()
        # update offsets by a damped median step
        for s in range(1, 8):
            if allc[s]:
                off[s] += 0.5 * float(np.median(np.array(allc[s])))
        off = [round(x, 2) for x in off]
    print('FINAL off', ['%.1f' % x for x in off])
    print('FINAL cyc', ['%.3f' % (x / 62.5 + 1) for x in off])


if __name__ == '__main__':
    main()
