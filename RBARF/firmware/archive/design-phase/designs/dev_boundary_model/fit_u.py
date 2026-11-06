"""Fit global slot fractions u[0..7] + per-capture (phi, P)."""
import json, sys
import numpy as np
from common import load_caps, fit_cap, eval_all, sample_times, violation, REC

meta, caps = load_caps()

# doc estimate scaled onto a ~40.1-cycle loop with the 3 spare cycles at the
# end-of-loop gap
LCY = 40.1
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)
u = (DOC - DOC[0]) / LCY
print("init u:", np.round(u, 5))


def refit_all(u):
    fits = {}
    for cap in caps:
        phi, P, v = fit_cap(cap, u)
        fits[cap.name] = (phi, P)
    return fits


fits = refit_all(u)
v, m, n = eval_all(caps, u, fits)
print(f"init: viol={v:.0f}ns  mism={m}/{n} ({m/n*100:.3f}%)")

for it in range(6):
    # coordinate descent on u[1..7]
    for s in range(1, 8):
        step = 0.010 if it == 0 else 0.002
        cur = u[s]
        bestv = eval_all(caps, u, fits)[0]
        while step > 1e-5:
            improved = False
            for d in (step, -step):
                uu = u.copy(); uu[s] = cur + d
                if not (0 < uu[s] < 1.0) or not np.all(np.diff(uu) > 0.005):
                    continue
                vv = eval_all(caps, uu, fits)[0]
                if vv < bestv - 1e-6:
                    bestv, cur = vv, cur + d
                    improved = True
                    break
            if not improved:
                step *= 0.5
        u[s] = cur
    fits = refit_all(u)
    v, m, n = eval_all(caps, u, fits)
    print(f"iter{it}: viol={v:.0f}  mism={m}/{n} ({m/n*100:.3f}%)  "
          f"u={np.round(u,5).tolist()}")

# report in cycles assuming a 40.1-cycle loop
print("gaps (fraction):", np.round(np.diff(np.append(u, 1.0)), 5))
print("gaps (cycles @40.1):", np.round(np.diff(np.append(u, 1.0)) * LCY, 3))
print("offsets ns @P=2507.3:", np.round(u * 2507.3, 2))

out = {"u": u.tolist(),
       "fits": {k: list(v_) for k, v_ in fits.items()}}
json.dump(out, open("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/dev_boundary_model/fitA.json", "w"), indent=1)
