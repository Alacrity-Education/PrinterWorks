"""Payload-free calibration.

Constraints used (independent of the payload, since every WS2812 bit
starts with a rising edge at k*1250 and T0H=350 <= Th <= 700=T1H):
   level 1  ->  phase in [0, 700)
   level 0  ->  phase in [350, 1250)
Given P, each slot offset u[s] can be scanned independently.
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NB = 192
FRAME_NS = NB * BIT


def prep(c):
    s = [x for x in linearize(c['capture']) if x[0] <= 100]
    it = np.array([x[0] for x in s], dtype=np.float64)
    sl = np.array([x[1] for x in s], dtype=np.int64)
    lv = np.array([x[2] for x in s], dtype=np.int8)
    return it, sl, lv


def viol_for_slot(iv, lvv, P, ugrid):
    """iv: iterations for one slot, lvv levels; returns violations per u."""
    t = P * iv[None, :] + ugrid[:, None]          # (U,N)
    inframe = (t >= -1.0) & (t < FRAME_NS)
    ph = t - np.floor(t / BIT) * BIT
    hi = lvv[None, :] == 1
    bad = np.where(hi, ph >= 700.0, ph < 350.0) & inframe
    return bad.sum(axis=1), inframe.sum(axis=1)


def calibrate(it, sl, lv, Pgrid=None, ulo=-100.0, uhi=2700.0, ustep=2.0):
    if Pgrid is None:
        Pgrid = np.arange(2495.0, 2535.0, 0.25)
    ugrid = np.arange(ulo, uhi, ustep)
    best = None
    per = [(it[sl == s], lv[sl == s]) for s in range(8)]
    for P in Pgrid:
        us = []
        tot = 0
        prev_u = ulo - 1
        okall = True
        for s in range(8):
            iv, lvv = per[s]
            bad, nin = viol_for_slot(iv, lvv, P, ugrid)
            # enforce monotone u increasing, and u[7] < u[0] + P
            m = ugrid > prev_u
            if s > 0:
                m &= ugrid < us[0] + P
            if not m.any():
                okall = False
                break
            b2 = np.where(m, bad, 10 ** 9)
            j = int(np.argmin(b2))
            us.append(float(ugrid[j]))
            prev_u = ugrid[j]
            tot += int(bad[j])
        if not okall:
            continue
        if best is None or tot < best[0]:
            best = (tot, float(P), us)
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    for c in train:
        it, sl, lv = prep(c)
        tot, P, us = calibrate(it, sl, lv)
        print('%-11s r%d  viol=%3d P=%7.2f  u=%s' % (
            c['pattern'], c['rep'], tot, P, ' '.join('%6.1f' % x for x in us)))


if __name__ == '__main__':
    main()
