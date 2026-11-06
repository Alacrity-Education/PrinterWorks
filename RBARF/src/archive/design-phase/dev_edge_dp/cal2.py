"""ML calibration on KNOWN bits only (header, trailer, post-frame low).

Model: t(i,s) = t0 + P*i + (P/L)*c[s],  c = cycle position of slot s.
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
MAXI = 112

KNOWN = np.zeros(NB + 1, dtype=bool)   # index NB = "after frame"
KNOWN[0:32] = True
KNOWN[160:192] = True
KNOWN[NB] = True


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], dtype=np.int8)


def prep(c, meta):
    s = [x for x in linearize(c['capture']) if x[0] <= MAXI]
    return (np.array([x[0] for x in s], dtype=np.float64),
            np.array([x[1] for x in s], dtype=np.int64),
            np.array([x[2] for x in s], dtype=np.int8),
            frame_bits(c['payload'], meta))


def eval_grid(it, sl, lv, thr, cyc, L, Pgrid, t0grid, mask, slots=None):
    if slots is not None:
        keep = np.isin(sl, slots)
        it, sl, lv = it[keep], sl[keep], lv[keep]
    cs = np.asarray(cyc, dtype=np.float64)[sl]
    best = (10 ** 9, 0.0, 0.0, 0)
    thr2 = np.concatenate([thr, [0.0]])
    for P in Pgrid:
        t = (P * it + (P / L) * cs)[None, :] + t0grid[:, None]
        k = np.floor(t / BIT).astype(np.int64)
        k = np.where((k < 0), 0, np.where(k >= NB, NB, k))
        ph = t - np.floor(t / BIT) * BIT
        exp = (ph < thr2[k]).astype(np.int8)
        m = mask[k]
        bad = ((exp != lv[None, :]) & m).sum(axis=1)
        j = int(np.argmin(bad))
        if bad[j] < best[0]:
            best = (int(bad[j]), float(P), float(t0grid[j]), int(m.sum()))
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    Pgrid = np.arange(2494.0, 2536.0, 0.25)
    t0grid = np.arange(-100.0, 560.0, 4.0)
    for L in (39, 40, 41):
        cyc = [1, 5, 9, 13, 17, 21, 27, 32]
        tot = 0; totn = 0
        rows = []
        for c, (it, sl, lv, bits) in zip(train, preps):
            thr = np.where(bits > 0, 700.0, 350.0)
            b, P, t0, n = eval_grid(it, sl, lv, thr, cyc, L, Pgrid, t0grid,
                                    KNOWN, slots=[0, 1, 2, 3, 4, 5])
            tot += b; totn += n
            rows.append((c['pattern'], c['rep'], b, n, P, t0))
        print('L=%d  total bad %d / %d' % (L, tot, totn))
        if L == 40:
            for r in rows:
                print('   %-11s r%d bad=%2d/%3d P=%7.2f t0=%6.1f' % r)


if __name__ == '__main__':
    main()
