"""Explain the per-iteration timing deviation from the observed sample levels.

Hypothesis: the polling loop takes a data-dependent number of cycles, so the
iteration start times accumulate an offset that depends on the levels seen so
far.  All the regressors below are computable from the capture itself.
"""
import sys
import numpy as np
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_edge_dp')
from harness import load_dataset, linearize
from prof import devprofile


def regressors(c):
    s = [x for x in linearize(c['capture']) if x[0] <= 100]
    nh = np.zeros(96)          # high samples per iteration
    ntr = np.zeros(96)         # level changes per iteration
    per_slot = np.zeros((96, 8))
    prev = None
    for (i, sl, v) in s:
        if i >= 96:
            continue
        nh[i] += v
        per_slot[i, sl] = v
        if prev is not None and prev != v:
            ntr[i] += 1
        prev = v
    return nh, ntr, per_slot


def cum(x):
    return np.concatenate([[0.0], np.cumsum(x)[:-1]])


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c['rep'] in (0, 1)]
    rows = []
    for c in train:
        cost, p, prof = devprofile(c, meta)
        nh, ntr, ps = regressors(c)
        rows.append((c, prof, nh, ntr, ps))
        sys.stdout.write('.')
        sys.stdout.flush()
    print()

    def score(build, name):
        tot = 0.0
        base = 0.0
        coefs = []
        for (c, prof, nh, ntr, ps) in rows:
            ok = ~np.isnan(prof)
            x = np.arange(96.0)
            X = [np.ones(96), x, x * x] + build(nh, ntr, ps)
            X = np.array(X).T[ok]
            y = prof[ok]
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            r = y - X @ beta
            tot += float(np.sum(r * r))
            X0 = np.array([np.ones(96), x, x * x]).T[ok]
            b0, *_ = np.linalg.lstsq(X0, y, rcond=None)
            r0 = y - X0 @ b0
            base += float(np.sum(r0 * r0))
            coefs.append(beta[3:])
        rms = (tot / (96 * len(rows))) ** 0.5
        rms0 = (base / (96 * len(rows))) ** 0.5
        cm = np.mean(np.array(coefs), axis=0) if coefs and len(coefs[0]) else []
        print('%-28s rms %6.1f (quad-only %6.1f)  mean coef %s' % (
            name, rms, rms0, ' '.join('%+.3f' % v for v in cm)))

    score(lambda nh, ntr, ps: [], 'quadratic only')
    score(lambda nh, ntr, ps: [cum(nh)], 'cum(n_high)')
    score(lambda nh, ntr, ps: [cum(ntr)], 'cum(n_transitions)')
    score(lambda nh, ntr, ps: [cum(nh), cum(ntr)], 'cum(nh)+cum(ntr)')
    score(lambda nh, ntr, ps: [cum(ps[:, k]) for k in range(8)], 'cum(per-slot level)')
    score(lambda nh, ntr, ps: [nh], 'n_high (instant)')
    score(lambda nh, ntr, ps: [cum(nh), nh], 'cum(nh)+nh')


if __name__ == '__main__':
    main()
