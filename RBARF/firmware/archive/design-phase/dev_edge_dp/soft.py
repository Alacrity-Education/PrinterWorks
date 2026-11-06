"""Smooth (soft-cost) calibration of the receiver timing model on train truth."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
FRAME_END = 191 * BIT + 700.0
MISS_BASE = 0.30
MISS_TOL = 90.0


def prep(c, meta):
    s = linearize(c['capture'])
    ni = max(k for k, x in enumerate(s) if x[2] == 1)
    anchor = (s[ni], s[ni + 1])
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(c['payload']) + bytes.fromhex(meta['trailer'])
    bits = np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], dtype=np.int8)
    s2 = [x for x in s if x[0] <= 100]
    it = np.array([x[0] for x in s2], dtype=np.float64)
    sl = np.array([x[1] for x in s2], dtype=np.int64)
    lv = np.array([x[2] for x in s2], dtype=np.int8)
    prev = np.concatenate([[0], lv[:-1]]).astype(np.float64)
    return it, sl, lv, bits, anchor, prev


def cost(it, sl, lv, bits, off, P, t0, prev=None, alpha=0.0, drift=0.0):
    t = t0 + P * it + drift * it * it + np.asarray(off)[sl]
    if alpha:
        t = t + alpha * prev
    kf = np.floor(t / BIT)
    k = kf.astype(np.int64)
    ph = t - kf * BIT
    inside = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    th = np.where(bits[kk] > 0, 700.0, 350.0)
    pred = np.where(inside, (ph < th).astype(np.int8), np.int8(0))
    match = pred == lv
    d = np.where(lv == 1, np.where(ph >= th, ph - th, -ph), th - ph)
    d = np.maximum(d, 0.0)
    c = MISS_BASE + (1.0 - MISS_BASE) * np.minimum(1.0, d / MISS_TOL)
    c = np.where(inside, c, 1.0)
    return float(np.where(match, 0.0, c).sum())


def fit_capture(pr, off, alpha=0.0, P0=None, t00=None):
    it, sl, lv, bits, anchor, prev = pr
    if P0 is None:
        (i1, s1, _), (i2, s2, _) = anchor
        f1 = i1 + off[s1] / 2500.0
        f2 = i2 + off[s2] / 2500.0
        lo = (FRAME_END - 700.0) / f2 - 2.0
        hi = (FRAME_END + 100.0) / f1 + 2.0
        best = None
        for P in np.arange(lo, hi, 0.25):
            for t0 in np.arange(-100.0, 700.0, 10.0):
                c = cost(it, sl, lv, bits, off, P, t0, prev, alpha)
                if best is None or c < best[0]:
                    best = (c, P, t0)
        cur, P, t0 = best
    else:
        P, t0 = P0, t00
        cur = cost(it, sl, lv, bits, off, P, t0, prev, alpha)
    dr = 0.0
    for _ in range(80):
        imp = False
        for st in (1.0, 0.3, 0.1, 0.03):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P + d, t0, prev, alpha, dr)
                if c < cur - 1e-9:
                    cur, P = c, P + d; imp = True
        for st in (12.0, 4.0, 1.0, 0.3):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P, t0 + d, prev, alpha, dr)
                if c < cur - 1e-9:
                    cur, t0 = c, t0 + d; imp = True
        for st in (0.03, 0.01, 0.003):
            for d in (st, -st):
                c = cost(it, sl, lv, bits, off, P, t0, prev, alpha, dr + d)
                if c < cur - 1e-9:
                    cur, dr = c, dr + d; imp = True
        if not imp:
            break
    return cur, P, t0, dr


def total(preps, off, alpha=0.0, warm=None):
    tot = 0.0
    out = []
    for n, pr in enumerate(preps):
        if warm is not None:
            c, P, t0, dr = fit_capture(pr, off, alpha, warm[n][0], warm[n][1])
        else:
            c, P, t0, dr = fit_capture(pr, off, alpha)
        tot += c
        out.append((P, t0, dr, c))
    return tot, out


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    off = [62.5 * (x - 1) for x in [1, 5, 9, 13, 17, 21, 27, 32]]
    alpha = 0.0
    tot, warm = total(preps, off, alpha)
    print('start %.2f  (mean %.2f/capture)' % (tot, tot / len(preps)))
    sys.stdout.flush()
    step = 16.0
    while step > 0.4:
        imp = False
        for s in range(1, 8):
            for d in (step, -step):
                o2 = list(off); o2[s] += d
                t2, w2 = total(preps, o2, alpha, warm)
                if t2 < tot - 1e-6:
                    off, tot, warm = o2, t2, w2
                    imp = True
                    print('  off[%d]%+.1f -> %.2f' % (s, d, tot)); sys.stdout.flush()
                    break
        for d in (8.0, -8.0, 3.0, -3.0, 1.0, -1.0):
            t2, w2 = total(preps, off, alpha + d, warm)
            if t2 < tot - 1e-6:
                alpha, tot, warm = alpha + d, t2, w2
                imp = True
                print('  alpha%+.1f -> %.2f' % (d, tot)); sys.stdout.flush()
        if not imp:
            step *= 0.5
    print('off', ['%.1f' % x for x in off])
    print('cyc', ['%.3f' % (x / 62.5 + 1) for x in off])
    print('alpha %.2f  total %.2f  mean %.2f' % (alpha, tot, tot / len(preps)))
    for c, w in zip(train, warm):
        print('  %-11s r%d cost=%6.2f P=%8.3f t0=%7.1f dr=%.4f' % (
            c['pattern'], c['rep'], w[3], w[0], w[1], w[2]))


if __name__ == '__main__':
    main()
