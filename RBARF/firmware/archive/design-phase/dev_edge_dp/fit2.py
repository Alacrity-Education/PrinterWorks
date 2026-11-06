"""Fast numpy calibration of the sample-time model."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
MAXI = 108


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], dtype=np.int8)


def prep(c, meta):
    s = [x for x in linearize(c['capture']) if x[0] <= MAXI]
    it = np.array([x[0] for x in s], dtype=np.float64)
    sl = np.array([x[1] for x in s], dtype=np.int64)
    lv = np.array([x[2] for x in s], dtype=np.int8)
    return it, sl, lv, frame_bits(c['payload'], meta)


def expected(t, bits, thr):
    """expected level array; t may be any shape. Out-of-frame -> 0."""
    k = np.floor(t / BIT).astype(np.int64)
    ph = t - k * BIT
    ok = (k >= 0) & (k < NB)
    kk = np.clip(k, 0, NB - 1)
    exp = np.where(ok, (ph < thr[kk]).astype(np.int8), np.int8(0))
    return k, exp


def scan(it, sl, lv, bits, g, Pgrid, t0grid, usemask_bits):
    thr = np.where(bits > 0, 700.0, 350.0)
    goff = np.asarray(g)[sl]                      # (N,)
    best = (10 ** 9, None, None)
    for P in Pgrid:
        base = P * (it + goff)                     # (N,)
        t = base[None, :] + t0grid[:, None]        # (T,N)
        k, exp = expected(t, bits, thr)
        m = usemask_bits[np.clip(k, 0, NB - 1)] & ((k >= 0) & (k < NB))
        bad = ((exp != lv[None, :]) & m).sum(axis=1)
        j = int(np.argmin(bad))
        if bad[j] < best[0]:
            best = (int(bad[j]), float(P), float(t0grid[j]))
    return best


KMASK = np.zeros(NB, dtype=bool)
KMASK[0:32] = True
KMASK[160:192] = True
ALLMASK = np.ones(NB, dtype=bool)


def total(preps, g, Pgrid, t0grid, mask=KMASK):
    tot = 0
    res = []
    for (it, sl, lv, bits) in preps:
        b, P, t0 = scan(it, sl, lv, bits, g, Pgrid, t0grid, mask)
        tot += b
        res.append((b, P, t0))
    return tot, res


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    Pgrid = np.arange(2490.0, 2540.0, 0.2)
    t0grid = np.arange(0.0, 700.0, 5.0)
    for cy in ([1, 5, 9, 13, 17, 21, 27, 32], [1, 5, 9, 13, 17, 21, 28, 33],
               [1, 5, 9, 13, 17, 21, 27, 33], [1, 5, 9, 13, 17, 22, 28, 33],
               [1, 5, 9, 13, 18, 22, 28, 34]):
        g = [x / 40.0 for x in cy]
        tot, res = total(preps, g, Pgrid, t0grid)
        print(cy, 'total bad', tot, 'of', sum(int(KMASK[np.clip(np.floor((r[2]+r[1]*(p[0]+np.asarray(g)[p[1]]))/BIT).astype(int),0,191)].sum()) for p, r in zip(preps, res)))


if __name__ == '__main__':
    main()
