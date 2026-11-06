"""Refine per-capture fit and inspect residuals."""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset
from cal2 import prep, KNOWN, BIT, NB, eval_grid

MAXI = 112


def times(it, sl, off, P, t0, drift=0.0):
    return t0 + P * it + drift * it * it + np.asarray(off)[sl]


def bads(it, sl, lv, thr2, off, P, t0, mask, drift=0.0):
    t = times(it, sl, off, P, t0, drift)
    k = np.floor(t / BIT).astype(np.int64)
    ph = t - k * BIT
    k = np.where(k < 0, 0, np.where(k >= NB, NB, k))
    exp = (ph < thr2[k]).astype(np.int8)
    m = mask[k]
    return (exp != lv) & m, m, k, ph


def refine(it, sl, lv, bits, mask, P, t0, off, drift=0.0, rounds=40):
    thr2 = np.concatenate([np.where(bits > 0, 700.0, 350.0), [0.0]])
    def cost(off, P, t0, drift):
        b, m, _, _ = bads(it, sl, lv, thr2, off, P, t0, mask, drift)
        return int(b.sum())
    cur = cost(off, P, t0, drift)
    for _ in range(rounds):
        imp = False
        for s in range(8):
            for step in (16.0, 6.0, 2.0, 0.5):
                for d in (step, -step):
                    o2 = list(off); o2[s] += d
                    c2 = cost(o2, P, t0, drift)
                    if c2 < cur:
                        cur, off = c2, o2; imp = True
        for step in (1.0, 0.3, 0.1, 0.03):
            for d in (step, -step):
                c2 = cost(off, P + d, t0, drift)
                if c2 < cur:
                    cur, P = c2, P + d; imp = True
        for step in (12.0, 4.0, 1.0):
            for d in (step, -step):
                c2 = cost(off, P, t0 + d, drift)
                if c2 < cur:
                    cur, t0 = c2, t0 + d; imp = True
        for step in (0.05, 0.015, 0.005):
            for d in (step, -step):
                c2 = cost(off, P, t0, drift + d)
                if c2 < cur:
                    cur, drift = c2, drift + d; imp = True
        if not imp:
            break
    return cur, P, t0, off, drift


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    Pgrid = np.arange(2494.0, 2536.0, 0.25)
    t0grid = np.arange(-100.0, 560.0, 4.0)
    L = 40
    cyc = [1, 5, 9, 13, 17, 21, 27, 32]
    for c in train[:8]:
        it, sl, lv, bits = prep(c, meta)
        b, P, t0, _ = eval_grid(it, sl, lv, np.where(bits > 0, 700.0, 350.0),
                                cyc, L, Pgrid, t0grid, KNOWN, slots=[0, 1, 2, 3, 4, 5])
        off = [(P / L) * x for x in cyc]
        cur, P2, t02, off2, dr = refine(it, sl, lv, bits, KNOWN, P, t0, off)
        thr2 = np.concatenate([np.where(bits > 0, 700.0, 350.0), [0.0]])
        bmask, m, k, ph = bads(it, sl, lv, thr2, off2, P2, t02, KNOWN, dr)
        print('%-11s r%d  bad=%d/%d  P=%.2f t0=%.1f drift=%.3f' % (
            c['pattern'], c['rep'], cur, int(m.sum()), P2, t02, dr))
        print('   off cyc:', ' '.join('%.2f' % (x / (P2 / L)) for x in off2))
        idx = np.nonzero(bmask)[0]
        print('   resid (slot,bit,phase,lv):',
              ' '.join('(%d,%d,%.0f,%d)' % (sl[i], k[i], ph[i], lv[i]) for i in idx[:24]))
        # full-frame check with refined params
        bA, mA, _, _ = bads(it, sl, lv, thr2, off2, P2, t02,
                            np.ones(NB + 1, dtype=bool), dr)
        print('   full-frame bad=%d/%d' % (int(bA.sum()), int(mA.sum())))


if __name__ == '__main__':
    main()
