"""Compare the free DP alignment against the ground-truth-forced alignment."""
import sys
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
from run import load


def best_run(m, samples, forced, pstep=0.5, pad=0.0):
    lo, hi = m._p_window(samples)
    lo -= pad; hi += pad
    best = None
    p = lo
    while p <= hi:
        r = m._run(samples, p, forced)
        if r is not None and (best is None or r[0] < best[0]):
            best = (r[0], p, r[1])
        p += pstep
    return best


def main():
    m = load()
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    for c in train:
        samples = linearize(c['capture'])
        expd = bytes.fromhex(c['payload'])
        free = m._frame_masks(meta)
        full = list(free)
        pb = [(b >> (7 - k)) & 1 for b in expd for k in range(8)]
        for i, v in enumerate(pb):
            full[32 + i] = v
        bf = best_run(m, samples, free)
        bo = best_run(m, samples, full)
        got = bytes(sum(bf[2].get(32 + n * 8 + k, 0) << (7 - k) for k in range(8))
                    for n in range(16))
        nerr = sum(1 for i in range(128)
                   if bf[2].get(32 + i, 0) != pb[i])
        print('%-11s r%d  free cost=%7.2f P=%8.2f | oracle cost=%7.2f P=%8.2f | '
              'errbits=%2d %s' % (c['pattern'], c['rep'], bf[0], bf[1], bo[0], bo[1],
                                  nerr, 'OK' if got == expd else ''))
        sys.stdout.flush()


if __name__ == '__main__':
    main()
