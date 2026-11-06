"""Integer-constrained search over the sampling-loop gap structure."""
import sys
import itertools
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset
from soft import prep, cost, FRAME_END

BASE = [4, 4, 4, 4, 4, 6, 5, 6]     # documented inter-slot gaps (sum 37)


def cyc_from(gaps):
    c = [1.0]
    for g in gaps[:7]:
        c.append(c[-1] + g)
    return c, float(sum(gaps))


def fit_pt(pr, off, coarse=True):
    it, sl, lv, bits, anchor, prev = pr
    (i1, s1, _), (i2, s2, _) = anchor
    f1 = i1 + off[s1] / 2500.0
    f2 = i2 + off[s2] / 2500.0
    lo = (FRAME_END - 700.0) / f2 - 2.5
    hi = (FRAME_END + 100.0) / f1 + 2.5
    best = None
    st = 0.35 if coarse else 0.15
    for P in np.arange(lo, hi, st):
        for t0 in np.arange(-120.0, 720.0, 10.0):
            c = cost(it, sl, lv, bits, off, P, t0, prev, 0.0)
            if best is None or c < best[0]:
                best = (c, P, t0)
    cur, P, t0 = best
    dr = 0.0
    for _ in range(60):
        imp = False
        for s in (0.5, 0.15, 0.05):
            for d in (s, -s):
                c = cost(it, sl, lv, bits, off, P + d, t0, prev, 0.0, dr)
                if c < cur - 1e-9:
                    cur, P = c, P + d; imp = True
        for s in (5.0, 1.5, 0.5):
            for d in (s, -s):
                c = cost(it, sl, lv, bits, off, P, t0 + d, prev, 0.0, dr)
                if c < cur - 1e-9:
                    cur, t0 = c, t0 + d; imp = True
        for s in (0.02, 0.006):
            for d in (s, -s):
                c = cost(it, sl, lv, bits, off, P, t0, prev, 0.0, dr + d)
                if c < cur - 1e-9:
                    cur, dr = c, dr + d; imp = True
        if not imp:
            break
    return cur


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    preps = [prep(c, meta) for c in train]
    tot_extra = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['3'])]
    cands = []
    for extra in tot_extra:
        for combo in itertools.combinations_with_replacement(range(8), extra):
            d = [0] * 8
            for i in combo:
                d[i] += 1
            g = [BASE[i] + d[i] for i in range(8)]
            if max(g) > 12:
                continue
            cands.append(tuple(g))
    cands = sorted(set(cands))
    print(len(cands), 'candidates'); sys.stdout.flush()
    res = []
    for g in cands:
        c, L = cyc_from(g)
        # offsets in ns at a nominal 2500 ns loop
        off = [(x - 1) * 2500.0 / L for x in c]
        tot = sum(fit_pt(pr, off) for pr in preps)
        res.append((tot, g))
        print('  %s L=%2d -> %.1f' % (g, int(L), tot)); sys.stdout.flush()
    res.sort()
    print('BEST:')
    for r in res[:12]:
        print('  %.1f  %s' % r)


if __name__ == '__main__':
    main()
