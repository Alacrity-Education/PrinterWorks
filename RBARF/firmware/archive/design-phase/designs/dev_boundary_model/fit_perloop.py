"""Identify the intra-loop geometry with the clock nuisance marginalised out.

For a candidate slot geometry u we give EVERY loop its own free time shift
delta_i (searched on a 2.5 ns grid) and count the residual sample
mismatches.  A per-loop shift can absorb any amount of clock wander or
scale error, so whatever mismatch survives is caused by the intra-loop
geometry alone -> the objective discriminates geometries sharply, unlike
a global linear fit where clock error and slot offsets trade off.
"""
import itertools, json, sys
import numpy as np
from common import load_caps, fit_cap, sample_times

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
DEL = np.arange(-400, 401, 2.5)
NLOOP = 100          # 192 bits * 1250 ns / 2507 ns ~ 96 loops


def u_of(g):
    g = np.asarray(g, float)
    return np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])


def prep(cap, u):
    phi, P = fit_cap(cap, u)[:2]
    t = sample_times(cap, phi, P, u)
    return phi, P, t


def perloop_mismatch(cap, u, phi, P):
    """min over per-loop shift of the sample mismatch count."""
    t = sample_times(cap, phi, P, u)
    it = cap.it.astype(int)
    E = cap.E
    tot, ncmp = 0, 0
    dsel = np.zeros(NLOOP)
    for i in range(NLOOP):
        m = it == i
        if not m.any():
            continue
        tt = t[m][:, None] + DEL[None, :]
        pred = np.searchsorted(E, tt.ravel(), side="right").reshape(tt.shape) & 1
        mism = (pred != cap.lev[m][:, None]).sum(0)
        j = int(np.argmin(mism))
        tot += int(mism[j]); ncmp += int(m.sum()); dsel[i] = DEL[j]
    return tot, ncmp, dsel


def score(g, fits):
    u = u_of(g)
    T = N = 0
    for cap in caps:
        phi, P = fits[cap.name]
        a, b, _ = perloop_mismatch(cap, u, phi, P)
        T += a; N += b
    return T, N


if __name__ == "__main__":
    EXTRA = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    combos = [c for c in itertools.product(range(EXTRA + 1), repeat=8)
              if sum(c) == EXTRA]
    res = []
    for c in combos:
        g = DOC + np.array(c, float)
        u = u_of(g)
        fits = {cap.name: fit_cap(cap, u)[:2] for cap in caps}
        T, N = score(g, fits)
        res.append((T, [int(x) for x in g]))
        print(f"g={[int(x) for x in g]}  perloop_mism={T}/{N} "
              f"({T/N*100:.4f}%)", flush=True)
    res.sort()
    print("\nTOP 10:")
    for T, g in res[:10]:
        print(f"  {g}  {T}")
    json.dump([[t, g] for t, g in res], open(
        "/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/"
        f"dev_boundary_model/perloop{EXTRA}.json", "w"), indent=1)
