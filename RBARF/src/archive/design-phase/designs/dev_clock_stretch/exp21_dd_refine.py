"""Decision-directed second pass: once the bits are known (oracle = upper
bound on what a downstream slicer can supply), refit (phi,L) using BOTH
rising and falling edges.  How much does the time base tighten?"""
import numpy as np
from common import load_all, BIT_NS
from exp8_pipeline import A, BIAS_F, coarse, refine

T0H, T1H = 350.0, 700.0


def dd_fit(cap, phi, L, bits, iters=15):
    lev = cap["lev"]; d = np.diff(lev.astype(int))
    idx = np.nonzero(d != 0)[0]; kind = d[idx]
    u = cap["it"] + A[cap["slot"]]
    umid = .5 * (u[idx] + u[idx+1]); s0 = cap["slot"][idx]
    # target times: rises at k*1250, falls at k*1250 + (T1H if bit else T0H)
    rt = np.arange(192) * BIT_NS
    ft = rt + np.where(bits == 1, T1H, T0H)
    for _ in range(iters):
        b = BIAS_F[s0] * L
        t = phi + umid * L + b
        tgt = np.empty_like(t); err = np.empty_like(t)
        for j, (tt, kd) in enumerate(zip(t, kind)):
            ref = rt if kd > 0 else ft
            m = int(np.argmin(np.abs(ref - tt)))
            tgt[j] = ref[m]; err[j] = abs(ref[m] - tt)
        keep = err < 0.45 * BIT_NS
        X = np.vstack([np.ones(keep.sum()), umid[keep]]).T
        sol, *_ = np.linalg.lstsq(X, (tgt - b)[keep], rcond=None)
        phi, L = sol
    b = BIAS_F[s0] * L
    t = phi + umid * L + b
    return phi, L, (tgt - t)[keep], int(keep.sum())


meta, caps = load_all()
LG = np.arange(2300., 2705., 2.)
r1, r2, dl = [], [], []
for cap in caps:
    Lc, J, _ = coarse(cap, LG)
    phi, L, res, k, umid, s0 = refine(cap, Lc)
    phi2, L2, res2, n2 = dd_fit(cap, phi, L, cap["bits"])
    r1.append(np.sqrt((res**2).mean())); r2.append(np.sqrt((res2**2).mean()))
    dl.append(L2 - L)
    print(f"{cap['pattern']:11s} {cap['rep']} rise-only L={L:8.3f} "
          f"rms={r1[-1]:5.1f} n={len(res):3d} | +falls L={L2:8.3f} "
          f"rms={r2[-1]:5.1f} n={n2:3d}  dL={L2-L:+6.2f}")
dl = np.array(dl)
print(f"\nrise-only rms mean={np.mean(r1):.1f}; rise+fall rms mean={np.mean(r2):.1f}")
print(f"dL: mean={dl.mean():+.3f} std={dl.std():.3f} max|.|={np.abs(dl).max():.2f}")
