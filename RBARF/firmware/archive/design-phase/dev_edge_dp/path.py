"""Dump the oracle residual path for a few captures to see what the DP drift
is actually compensating for."""
import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
import slotcal as S
from slotcal import M, viterbi_path, frame_bits, quadfit


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    want = sys.argv[1:] or ['zeros', 'msb1', 'rnd1', 'count']
    for c in train:
        if c['pattern'] not in want or c['rep'] != 0:
            continue
        s = [x for x in linearize(c['capture']) if x[0] <= 100]
        bits = frame_bits(c['payload'], meta)
        lv = [v for _, _, v in s]
        slot_off = [M.SLOT_CYCLES[i] / M.LOOP_CYCLES for i in range(8)]
        best = None
        plo, phi = M._p_window(s)
        p = plo
        while p <= phi:
            nom = [p * i + p * slot_off[sl] for i, sl, v in s]
            cost, path = viterbi_path(nom, lv, bits)
            if best is None or cost < best[0]:
                best = (cost, p, path)
            p += 0.5
        cost, p, path = best
        xs = [float(i) for i, _, _ in s]
        r = quadfit(xs, [float(v) for v in path])
        dev = [path[n] - (r[0] + r[1] * xs[n] + r[2] * xs[n] ** 2)
               for n in range(len(s))]
        print('%-11s r%d cost=%.1f P=%.2f quad=%.1f %+.3f %+.5f' % (
            c['pattern'], c['rep'], cost, p, r[0], r[1], r[2]))
        # per-iteration mean deviation
        rows = []
        for i0 in range(0, 96, 1):
            vals = [dev[n] for n in range(len(s)) if s[n][0] == i0]
            if vals:
                rows.append('%d:%+.0f' % (i0, sum(vals) / len(vals)))
        print('   iter dev:', ' '.join(rows))
        # per-slot spread within iterations
        for sl in range(8):
            vals = [dev[n] for n in range(len(s)) if s[n][1] == sl]
            m = sum(vals) / len(vals)
            sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
            print('   slot%d mean=%+6.1f sd=%5.1f' % (sl, m, sd))


if __name__ == '__main__':
    main()
