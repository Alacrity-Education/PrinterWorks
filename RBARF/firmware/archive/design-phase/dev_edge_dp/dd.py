"""Test data-dependent sample-instant shifts (unbiased, global parameters).

Models tried:
  base                 t = t0 + P*i + off[s]
  +prev  (a)           + a * level(previous sample)
  +cum   (b)           + b * (#high samples earlier in the same iteration)
  +own   (c)           + c * level(this sample)
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
from soft import BIT, NB, FRAME_END, MISS_BASE, MISS_TOL


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
    cum = np.zeros(len(s2))
    run = 0
    for n in range(len(s2)):
        if sl[n] == 0:
            run = 0
        cum[n] = run
        run += lv[n]
    return it, sl, lv, bits, anchor, prev, cum


def cost(pr, off, P, t0, dr=0.0, a=0.0, b=0.0, cc=0.0, aslot=None):
    it, sl, lv, bits, anchor, prev, cum = pr
    t = t0 + P * it + dr * it * it + np.asarray(off)[sl]
    if a:
        t = t + a * prev
    if b:
        t = t + b * cum
    if cc:
        t = t + cc * lv
    if aslot is not None:
        t = t + np.asarray(aslot)[sl] * prev
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


def fit(pr, off, **kw):
    it, sl, lv, bits, anchor, prev, cum = pr
    (i1, s1, _), (i2, s2, _) = anchor
    f1 = i1 + off[s1] / 2500.0
    f2 = i2 + off[s2] / 2500.0
    lo = (FRAME_END - 700.0) / f2 - 2.5
    hi = (FRAME_END + 100.0) / f1 + 2.5
    best = None
    for P in np.arange(lo, hi, 0.3):
        for t0 in np.arange(-120.0, 720.0, 10.0):
            c = cost(pr, off, P, t0, **kw)
            if best is None or c < best[0]:
                best = (c, P, t0)
    cur, P, t0 = best
    dr = 0.0
    for _ in range(60):
        imp = False
        for s in (0.4, 0.12, 0.04):
            for d in (s, -s):
                c = cost(pr, off, P + d, t0, dr, **kw)
                if c < cur - 1e-9:
                    cur, P = c, P + d; imp = True
        for s in (5.0, 1.5, 0.5):
            for d in (s, -s):
                c = cost(pr, off, P, t0 + d, dr, **kw)
                if c < cur - 1e-9:
                    cur, t0 = c, t0 + d; imp = True
        for s in (0.02, 0.006):
            for d in (s, -s):
                c = cost(pr, off, P, t0, dr + d, **kw)
                if c < cur - 1e-9:
                    cur, dr = c, dr + d; imp = True
        if not imp:
            break
    return cur


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    off = [62.5 * (x - 1) for x in [1, 5, 9, 13, 17, 21, 27, 32]]
    for name, kw in [('base', {}),
                     ('prev -60', {'a': -60.0}), ('prev -30', {'a': -30.0}),
                     ('prev +30', {'a': 30.0}), ('prev +60', {'a': 60.0}),
                     ('cum -60', {'b': -60.0}), ('cum -30', {'b': -30.0}),
                     ('cum +30', {'b': 30.0}), ('cum +60', {'b': 60.0}),
                     ('own -60', {'cc': -60.0}), ('own +60', {'cc': 60.0})]:
        tot = sum(fit(pr, off, **kw) for pr in preps)
        print('%-10s %.1f' % (name, tot)); sys.stdout.flush()


if __name__ == '__main__':
    main()
