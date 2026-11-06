"""Anchored calibration: narrow P by the frame-end anchor, then ML on known bits.

Also globally optimises the 8 slot cycle-offsets (shared across captures).
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
FRAME_END = 191 * BIT + 700.0     # last falling edge (bit191 of trailer FF = 1)
MAXI = 106


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], dtype=np.int8)


def prep(c, meta):
    s = linearize(c['capture'])
    ni = max(k for k, x in enumerate(s) if x[2] == 1)
    anchor = (s[ni], s[ni + 1])
    s2 = [x for x in s if x[0] <= MAXI]
    return (np.array([x[0] for x in s2], dtype=np.float64),
            np.array([x[1] for x in s2], dtype=np.int64),
            np.array([x[2] for x in s2], dtype=np.int8),
            frame_bits(c['payload'], meta), anchor)


KN = np.zeros(NB + 1, dtype=bool)
KN[0:32] = True
KN[160:192] = True
KN[NB] = True
ALL = np.ones(NB + 1, dtype=bool)


def score_grid(it, sl, lv, thr2, off, Pgrid, t0grid, mask):
    o = np.asarray(off)[sl]
    best = (10 ** 9, 0.0, 0.0)
    for P in Pgrid:
        t = (P * it)[None, :] + (o * (P / 2500.0))[None, :] + t0grid[:, None]
        kf = np.floor(t / BIT)
        ph = t - kf * BIT
        k = np.clip(kf.astype(np.int64), 0, NB)
        exp = (ph < thr2[k]).astype(np.int8)
        bad = ((exp != lv[None, :]) & mask[k]).sum(axis=1)
        j = int(np.argmin(bad))
        if bad[j] < best[0]:
            best = (int(bad[j]), float(P), float(t0grid[j]))
    return best


def pwindow(anchor, off):
    (i1, s1, _), (i2, s2, _) = anchor
    f1 = i1 + off[s1] / 2500.0
    f2 = i2 + off[s2] / 2500.0
    lo = (FRAME_END - 640.0) / f2
    hi = (FRAME_END + 80.0) / f1
    return lo - 1.0, hi + 1.0


def fit_capture(it, sl, lv, bits, anchor, off, mask=KN, fine=True):
    thr2 = np.concatenate([np.where(bits > 0, 700.0, 350.0), [0.0]])
    lo, hi = pwindow(anchor, off)
    Pg = np.arange(lo, hi, 0.2)
    t0g = np.arange(-70.0, 650.0, 4.0)
    b, P, t0 = score_grid(it, sl, lv, thr2, off, Pg, t0g, mask)
    if fine:
        Pg = np.arange(P - 0.6, P + 0.6, 0.04)
        t0g = np.arange(t0 - 8.0, t0 + 8.0, 0.5)
        b, P, t0 = score_grid(it, sl, lv, thr2, off, Pg, t0g, mask)
    return b, P, t0


def errcount(it, sl, lv, bits, off, P, t0, mask):
    thr2 = np.concatenate([np.where(bits > 0, 700.0, 350.0), [0.0]])
    t = t0 + P * it + np.asarray(off)[sl] * (P / 2500.0)
    kf = np.floor(t / BIT)
    ph = t - kf * BIT
    k = np.clip(kf.astype(np.int64), 0, NB)
    exp = (ph < thr2[k]).astype(np.int8)
    m = mask[k]
    return int(((exp != lv) & m).sum()), int(m.sum())


def total(preps, off, mask=KN):
    tot = n = 0
    fits = []
    for (it, sl, lv, bits, anchor) in preps:
        b, P, t0 = fit_capture(it, sl, lv, bits, anchor, off, mask)
        e, nn = errcount(it, sl, lv, bits, off, P, t0, mask)
        tot += e; n += nn
        fits.append((P, t0, e, nn))
    return tot, n, fits


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    # slot offsets in ns at nominal 2500 ns loop; cyc*62.5
    off = [62.5 * (x - 1) for x in [1, 5, 9, 13, 17, 21, 27, 32]]
    tot, n, fits = total(preps, off)
    print('start off', off, '->', tot, '/', n)
    step = 20.0
    while step > 0.8:
        improved = False
        for s in range(1, 8):
            for d in (step, -step):
                o2 = list(off); o2[s] += d
                t2, n2, f2 = total(preps, o2)
                if t2 < tot:
                    off, tot, fits = o2, t2, f2
                    improved = True
                    print('  off[%d]%+.1f -> %d' % (s, d, tot))
                    break
        if not improved:
            step *= 0.5
    print('final off', ['%.1f' % x for x in off], 'cyc',
          ['%.2f' % (x / 62.5 + 1) for x in off], '->', tot, '/', n)
    for c, f in zip(train, fits):
        print('  %-11s r%d bad=%2d/%3d P=%8.3f t0=%7.2f' % (
            c['pattern'], c['rep'], f[2], f[3], f[0], f[1]))
    # full-frame error with these params
    te = tn = 0
    for (it, sl, lv, bits, anchor), f in zip(preps, fits):
        e, nn = errcount(it, sl, lv, bits, off, f[0], f[1], ALL)
        te += e; tn += nn
    print('full-frame err %d/%d' % (te, tn))
    np.save('/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp/off.npy', np.array(off))


if __name__ == '__main__':
    main()
