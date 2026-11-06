"""Is the residual of a linear time base clock wander, or data-dependent
loop timing?  Estimate a per-loop time offset d[i] and regress it on
(a) iteration index and (b) cumulative count of HIGH samples read so far."""
import numpy as np
from common import load_caps, fit_cap, sample_times, violation

meta, caps = load_caps()
DOC = np.array([4, 4, 4, 4, 4, 6, 5, 6], float)
g = DOC.copy(); g[7] += 3.0                     # synth.py hypothesis
u = np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])
NIT = 640


def per_loop_offsets(cap, phi, P, u, half=3, rng=700.0, step=5.0):
    t0 = sample_times(cap, phi, P, u)
    d = np.zeros(NIT)
    cand = np.arange(-rng, rng + step, step)
    it = cap.it.astype(int)
    for i in range(NIT):
        m = (it >= i - half) & (it <= i + half)
        if m.sum() < 8:
            d[i] = np.nan
            continue
        tt = t0[m]
        best, bd = None, 0.0
        for c in cand:
            _, dd = violation(cap, tt + c, lev=cap.lev[m])
            # weight: keep samples inside the frame only
            v = dd.sum()
            if best is None or v < best:
                best, bd = v, c
        d[i] = bd
    return d


ACTIVE = 100        # loops that actually contain frame (192 bits ~ 96 loops)
for cap in caps:
    if cap.name not in ("zeros_0", "ones_0", "aa_0", "rnd1_0", "count_1",
                        "msb1_1", "p55_2", "dense_0"):
        continue
    phi, P, v = fit_cap(cap, u)
    d = per_loop_offsets(cap, phi, P, u)
    dd = d[:ACTIVE]
    # cumulative HIGH samples read before the start of each loop
    hi = np.zeros(NIT)
    it = cap.it.astype(int)
    for i, lv in zip(it, cap.lev):
        hi[i] += lv
    cum = np.concatenate([[0], np.cumsum(hi)[:-1]])[:ACTIVE]
    idx = np.arange(ACTIVE)
    ok = ~np.isnan(dd)
    A1 = np.stack([np.ones(ok.sum()), idx[ok]], 1)
    s1, r1, *_ = np.linalg.lstsq(A1, dd[ok], rcond=None)
    A2 = np.stack([np.ones(ok.sum()), cum[ok]], 1)
    s2, r2, *_ = np.linalg.lstsq(A2, dd[ok], rcond=None)
    A3 = np.stack([np.ones(ok.sum()), idx[ok], cum[ok]], 1)
    s3, r3, *_ = np.linalg.lstsq(A3, dd[ok], rcond=None)
    tot = ((dd[ok] - dd[ok].mean()) ** 2).sum()
    print(f"{cap.name:10s} P={P:8.2f} span[d]={np.nanmin(dd):7.1f}..{np.nanmax(dd):7.1f} "
          f"sd={np.nanstd(dd):6.1f} | R2(i)={1-r1[0]/tot:.3f} "
          f"R2(cumHi)={1-r2[0]/tot:.3f} R2(both)={1-r3[0]/tot:.3f} "
          f"slope_i={s1[1]:+.3f} slope_hi={s2[1]:+.3f}")
    print("   d[0:40] =", np.round(dd[:40], 0).tolist())
