"""Is the per-iteration timing deviation reproducible across captures?"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
from slotcal import M, viterbi_path, frame_bits, quadfit


def devprofile(c, meta):
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
    	# noqa
        p += 0.5
    cost, p, path = best
    xs = [float(i) for i, _, _ in s]
    r = quadfit(xs, [float(v) for v in path])
    prof = np.full(96, np.nan)
    for i0 in range(96):
        vals = [path[n] - (r[0] + r[1] * xs[n] + r[2] * xs[n] ** 2)
                for n in range(len(s)) if s[n][0] == i0]
        if vals:
            prof[i0] = float(np.mean(vals))
    return cost, p, prof


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    profs = []
    names = []
    for c in train:
        cost, p, prof = devprofile(c, meta)
        profs.append(prof)
        names.append('%s r%d' % (c['pattern'], c['rep']))
        print('%-14s cost=%5.1f P=%8.2f rms=%6.1f' % (names[-1], cost, p,
                                                      np.nanstd(prof)))
        sys.stdout.flush()
    A = np.array(profs)
    m = np.nanmean(A, axis=0)
    print('mean profile:', ' '.join('%+.0f' % x for x in m))
    print('mean rms %.1f' % np.nanstd(m))
    # correlation between reps of the same pattern
    C = np.corrcoef(np.nan_to_num(A))
    print('rep0-rep1 corr per pattern:')
    for i in range(0, len(train), 2):
        print('   %-12s %.2f' % (train[i]['pattern'], C[i, i + 1]))
    off = [C[i, j] for i in range(len(train)) for j in range(len(train))
           if abs(i - j) > 1]
    print('mean off-diagonal corr %.2f' % float(np.mean(off)))


if __name__ == '__main__':
    main()
