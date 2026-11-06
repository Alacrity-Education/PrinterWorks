"""Diagnostics: does level-dependence / width correction explain misses?

Per-slot free offsets (decoupled), optionally split by a context key
(previous sample level, or count of highs so far in the loop).
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
NBITS = 192
FRAME_END = NBITS * BIT


def frame_bits(frame_hex):
    return np.array([int(b) for byte in bytes.fromhex(frame_hex)
                     for b in f"{byte:08b}"], dtype=np.int8)


def levels_at(bits, t, t0h, t1h):
    k = np.floor(t / BIT).astype(np.int64)
    ok = (k >= 0) & (k < NBITS)
    kc = np.clip(k, 0, NBITS - 1)
    u = t - k * BIT
    thr = np.where(bits[kc] > 0, t1h, t0h)
    return ((ok & (u < thr)) & (u >= 0)).astype(np.int8)


def run(samples, bits, ctxfn, nctx, Pgrid, driftgrid, t0h, t1h, ostep=1.0):
    its = np.array([s[0] for s in samples], dtype=np.float64)
    sls = np.array([s[1] for s in samples], dtype=np.int64)
    vs = np.array([s[2] for s in samples], dtype=np.int8)
    ctx = np.array(ctxfn(samples), dtype=np.int64)
    groups = []
    for s in range(8):
        for cc in range(nctx):
            idx = np.where((sls == s) & (ctx == cc))[0]
            if len(idx):
                groups.append(idx)
    best = None
    cand = np.arange(0.0, 2500.0, ostep)
    for drift in driftgrid:
        for P in Pgrid:
            base = its * P + drift * its * its
            tot = 0
            for idx in groups:
                b = base[idx]
                v = vs[idx]
                tm = b[None, :] + cand[:, None]
                lv = levels_at(bits, tm, t0h, t1h)
                infr = (tm < FRAME_END + 700)
                g = ((lv == v[None, :]) & infr).sum(axis=1)
                tot += int(g.max())
            if best is None or tot > best[0]:
                best = (tot, P, drift)
    return best


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    Pg = np.arange(2488, 2506, 1.0)
    variants = {
        'plain': (lambda s: [0] * len(s), 1, 350.0, 700.0),
        'prevlvl': (lambda s: [0] + [s[i - 1][2] for i in range(1, len(s))], 2, 350.0, 700.0),
        'curlvl': (lambda s: [v for _, _, v in s], 2, 350.0, 700.0),
        'w+60': (lambda s: [0] * len(s), 1, 410.0, 760.0),
        'w-60': (lambda s: [0] * len(s), 1, 290.0, 640.0),
        'w+120': (lambda s: [0] * len(s), 1, 470.0, 820.0),
    }
    for name, (fn, nc, a, b) in variants.items():
        tot = 0; totn = 0
        for c in train:
            s = linearize(c['capture'])
            bits = frame_bits(c['frame'])
            r = run(s, bits, fn, nc, Pg, [0.0], a, b, 2.0)
            r = run(s, bits, fn, nc, np.arange(r[1] - 1, r[1] + 1.01, 0.1), np.arange(-0.06, 0.061, 0.02), a, b, 1.0)
            tot += r[0]
            totn += len([1 for it, sl, v in s if it * r[1] < FRAME_END + 700])
        print(f"{name:9s} match {tot}/{totn} = {tot/totn:.3%}")


main()
