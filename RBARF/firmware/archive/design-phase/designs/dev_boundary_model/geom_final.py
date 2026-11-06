"""Score candidate intra-loop geometries under TV-regularised tracking, then
polish the offsets continuously."""
import sys
import numpy as np
from common import load_caps, fit_cap
from track import track

meta, caps = load_caps()
NLOOP = 100


def u_of(g):
    g = np.asarray(g, float)
    return np.concatenate([[0.0], np.cumsum(g)[:-1] / g.sum()])


def score_u(u, lam=0.02, report=False):
    tot = n = 0
    steps = []
    for cap in caps:
        phi, P = fit_cap(cap, u)[:2]
        t, d, mism = track(cap, phi, P, u, NLOOP, lam)
        tot += mism; n += NLOOP * 8
        steps.append(np.abs(np.diff(d)))
    if report:
        s = np.concatenate(steps)
        print(f"    |step|: mean={s.mean():.1f} p95={np.percentile(s,95):.0f} "
              f"max={s.max():.0f} ns/loop")
    return tot, n


CANDS = [[4, 4, 4, 4, 5, 6, 6, 7], [4, 4, 4, 4, 5, 6, 5, 8],
         [4, 4, 4, 4, 4, 6, 5, 9], [4, 4, 4, 5, 4, 6, 5, 8],
         [4, 4, 4, 5, 4, 6, 6, 7], [4, 4, 4, 4, 5, 6, 7, 6],
         [4, 4, 4, 4, 4, 6, 6, 8], [4, 4, 4, 4, 4, 7, 5, 8],
         [4, 4, 4, 4, 4, 6, 7, 7], [5, 4, 4, 4, 4, 6, 5, 8]]

best = None
for lam in (0.02,):
    print(f"lam={lam}")
    for g in CANDS:
        t, n = score_u(u_of(g), lam, report=True)
        print(f"  g={g}  mism={t}/{n} ({t/n*100:.4f}%)", flush=True)
        if best is None or t < best[0]:
            best = (t, g)
print("best integer geometry:", best)

# continuous polish
u = u_of(best[1])
cur, n = score_u(u)
print(f"polish start {cur}/{n} ({cur/n*100:.4f}%)  u={np.round(u,5).tolist()}")
for rnd in range(3):
    for s in range(1, 8):
        step = 0.008
        while step > 0.0008:
            improved = False
            for dd in (step, -step):
                uu = u.copy(); uu[s] += dd
                if not np.all(np.diff(uu) > 0.01) or uu[-1] > 0.99:
                    continue
                v, _ = score_u(uu)
                if v < cur:
                    cur, u = v, uu; improved = True; break
            if not improved:
                step *= 0.5
    print(f"round{rnd}: {cur}/{n} ({cur/n*100:.4f}%)  u={np.round(u,5).tolist()}"
          f"  gaps cy(L=40)={np.round(np.diff(np.append(u,1.0))*40,2).tolist()}",
          flush=True)
