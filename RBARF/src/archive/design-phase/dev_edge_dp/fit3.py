"""Single-capture full-truth fit: how good can the model get?"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
from fit2 import frame_bits, prep, BIT, NB, ALLMASK, KMASK


def badcount(it, sl, lv, thr, g, P, t0, mask):
    t = t0 + P * (it + np.asarray(g)[sl])
    k = np.floor(t / BIT).astype(np.int64)
    ph = t - k * BIT
    ok = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    exp = np.where(ok, (ph < thr[kk]).astype(np.int8), np.int8(0))
    m = ok & mask[kk]
    return int(((exp != lv) & m).sum()), int(m.sum()), (k, ph, exp, m)


def fit_one(it, sl, lv, bits, mask, g0=None, verbose=True):
    thr = np.where(bits > 0, 700.0, 350.0)
    g = list(g0 or [x / 40.0 for x in [1, 5, 9, 13, 17, 21, 27, 32]])
    # coarse P,t0
    best = None
    for P in np.arange(2490.0, 2540.0, 0.25):
        for t0 in np.arange(0.0, 700.0, 8.0):
            b, n, _ = badcount(it, sl, lv, thr, g, P, t0, mask)
            if best is None or b < best[0]:
                best = (b, P, t0)
    b, P, t0 = best
    # coordinate descent over g, P, t0
    for rnd in range(60):
        improved = False
        for step in (0.02, 0.008, 0.003, 0.001):
            for s in range(8):
                for d in (step, -step):
                    g2 = list(g); g2[s] += d
                    b2, _, _ = badcount(it, sl, lv, thr, g2, P, t0, mask)
                    if b2 < b:
                        b, g = b2, g2; improved = True
        for dP in (2.0, 0.5, 0.2, 0.05):
            for d in (dP, -dP):
                b2, _, _ = badcount(it, sl, lv, thr, g, P + d, t0, mask)
                if b2 < b:
                    b, P = b2, P + d; improved = True
        for dt in (20.0, 5.0, 1.0):
            for d in (dt, -dt):
                b2, _, _ = badcount(it, sl, lv, thr, g, P, t0 + d, mask)
                if b2 < b:
                    b, t0 = b2, t0 + d; improved = True
        if not improved:
            break
    n = badcount(it, sl, lv, thr, g, P, t0, mask)[1]
    if verbose:
        print('  bad=%d/%d P=%.2f t0=%.1f g=%s cyc=%s' % (
            b, n, P, t0, ['%.4f' % x for x in g], ['%.2f' % (x * 40) for x in g]))
    return b, n, P, t0, g


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    for c in train[:8]:
        it, sl, lv, bits = prep(c, meta)
        print(c['pattern'], c['rep'])
        fit_one(it, sl, lv, bits, ALLMASK)


if __name__ == '__main__':
    main()
