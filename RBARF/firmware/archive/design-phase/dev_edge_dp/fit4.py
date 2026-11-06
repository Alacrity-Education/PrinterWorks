"""Hinge-loss timing fit, payload-free + known-bit terms."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
MAXI = 112
T0H, T1H = 350.0, 700.0


def frame_bits(payload_hex, meta):
    fr = bytes.fromhex(meta['header']) + bytes.fromhex(payload_hex) + bytes.fromhex(meta['trailer'])
    return np.array([(b >> (7 - k)) & 1 for b in fr for k in range(8)], dtype=np.int8)


def prep(c, meta):
    s = [x for x in linearize(c['capture']) if x[0] <= MAXI]
    return (np.array([x[0] for x in s], dtype=np.float64),
            np.array([x[1] for x in s], dtype=np.int64),
            np.array([x[2] for x in s], dtype=np.int8),
            frame_bits(c['payload'], meta))


class Model:
    """t(i,s) = t0 + A*i + B*i^2 + off[s]  (off[0] = 0)."""

    def __init__(self, t0, A, B, off):
        self.p = np.array([t0, A, B] + list(off[1:]), dtype=np.float64)

    def times(self, it, sl):
        t0, A, B = self.p[0], self.p[1], self.p[2]
        off = np.concatenate([[0.0], self.p[3:]])
        return t0 + A * it + B * it * it + off[sl]


def loss(t, lv, lo, hi):
    """lo/hi: allowed phase interval per sample (arrays). squared hinge."""
    k = np.floor(t / BIT)
    ph = t - k * BIT
    a = np.maximum(0.0, lo - ph)
    b = np.maximum(0.0, ph - hi)
    pen = a * a + b * b
    # out-of-frame handling: after frame end everything must be low
    bad_after = (k >= NB) & (lv == 1)
    pen = pen + np.where(bad_after, (t - NB * BIT) ** 2 + 1e4, 0.0)
    bad_before = (k < 0) & (lv == 1)
    pen = pen + np.where(bad_before, t * t + 1e4, 0.0)
    return pen.sum()


def bounds(t, lv, bits, known):
    """allowed phase interval given assigned bit index & knowledge."""
    k = np.clip(np.floor(t / BIT).astype(np.int64), 0, NB - 1)
    kn = known[k]
    b1 = bits[k] == 1
    hi = np.where(lv == 1,
                  np.where(kn, np.where(b1, T1H, T0H), T1H),
                  BIT + 1e9)
    lo = np.where(lv == 1, 0.0,
                  np.where(kn, np.where(b1, T1H, T0H), T0H))
    return lo, hi


def fit(it, sl, lv, bits, known, t0, A, B=0.0, off=None, iters=250):
    m = Model(t0, A, B, off)
    steps = np.array([8.0, 0.6, 0.004] + [8.0] * 7)
    cur = None
    for _ in range(iters):
        t = m.times(it, sl)
        lo, hi = bounds(t, lv, bits, known)
        cur = loss(t, lv, lo, hi)
        improved = False
        for j in range(len(m.p)):
            for d in (steps[j], -steps[j]):
                q = m.p.copy(); q[j] += d
                mm = Model(0, 0, 0, [0] * 8); mm.p = q
                t2 = mm.times(it, sl)
                lo2, hi2 = bounds(t2, lv, bits, known)
                l2 = loss(t2, lv, lo2, hi2)
                if l2 < cur - 1e-9:
                    m.p = q; cur = l2; improved = True
                    break
        if not improved:
            steps = steps * 0.5
            if steps[1] < 1e-4:
                break
    return m, cur


def errcount(m, it, sl, lv, bits, mask):
    t = m.times(it, sl)
    k = np.floor(t / BIT).astype(np.int64)
    ph = t - k * BIT
    kk = np.clip(k, 0, NB - 1)
    thr = np.where(bits[kk] > 0, T1H, T0H)
    exp = np.where((k >= 0) & (k < NB), (ph < thr).astype(np.int8), np.int8(0))
    use = mask[np.clip(k, 0, NB)]
    return int(((exp != lv) & use).sum()), int(use.sum())


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    KN = np.zeros(NB, dtype=bool); KN[0:32] = True; KN[160:192] = True
    MK = np.zeros(NB + 1, dtype=bool); MK[0:32] = True; MK[160:192] = True; MK[NB] = True
    ALL = np.ones(NB + 1, dtype=bool)
    cyc = [1, 5, 9, 13, 17, 21, 27, 32]
    tk = te = nk = ne = 0
    for c in train:
        it, sl, lv, bits = prep(c, meta)
        best = None
        for A in np.arange(2494.0, 2536.0, 1.0):
            off = [(A / 40.0) * (x - 1) for x in cyc]
            for t0 in np.arange(-60.0, 520.0, 30.0):
                m, l = fit(it, sl, lv, bits, KN, t0, A, 0.0, off, iters=40)
                if best is None or l < best[1]:
                    best = (m, l)
        m = best[0]
        m2, l2 = fit(it, sl, lv, bits, KN, m.p[0], m.p[1], m.p[2],
                     np.concatenate([[0.0], m.p[3:]]), iters=400)
        ek, nk_ = errcount(m2, it, sl, lv, bits, MK)
        ea, na_ = errcount(m2, it, sl, lv, bits, ALL)
        tk += ek; nk += nk_; te += ea; ne += na_
        print('%-11s r%d known %2d/%3d  all %3d/%3d  A=%.2f B=%.4f t0=%.0f off=%s'
              % (c['pattern'], c['rep'], ek, nk_, ea, na_, m2.p[1], m2.p[2], m2.p[0],
                 ' '.join('%.0f' % x for x in np.concatenate([[0.0], m2.p[3:]]))))
    print('TOTAL known %d/%d  all %d/%d' % (tk, nk, te, ne))


if __name__ == '__main__':
    main()
