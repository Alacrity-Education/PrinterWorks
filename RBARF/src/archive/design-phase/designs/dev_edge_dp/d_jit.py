"""Per-slot timing-jitter estimate under the calibrated time model.

For every in-frame sample compute the signed distance x to the nearest
wire edge, oriented so that x>0 means "the model says we are inside the
level we observed".  A sample whose |x| is small is a near-edge sample;
mismatches at large |x| indicate model error, not aperture jitter.

MLE of a per-slot Gaussian timing jitter sigma[s]:
    P(observed level correct) = Phi(x / sigma)     (probit in x)
plus a per-slot systematic offset mu[s] (x -> x + mu).
"""
import json
import sys
from pathlib import Path

import numpy as np
import math

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM      # noqa: E402
import final as CF      # noqa: E402

F = json.load(open(CAL / "final.json"))
G, O, W, H1, H0 = F["G"], np.array(F["o"]), np.array(F["w"]), F["h1"], F["h0"]
meta, caps = CM.load()
CF.prepare(caps)

X = {s: [] for s in range(8)}     # signed distance to nearest edge (ns)
Y = {s: [] for s in range(8)}     # observed level
P = {s: [] for s in range(8)}     # predicted level
for c in caps:
    t0, k = F["nuis"][c["key"]][:2]
    t = t0 + k * CF.A_of(c, G, O, W)
    bits = c["bits"]
    j = np.floor(t / 1250.0).astype(int)
    m = (j >= 0) & (j < 192)
    tt = t[m]; jj = j[m]; u = tt - jj * 1250.0
    h = np.where(bits[jj] == 1, H1, H0)
    pred = (u < h).astype(int)
    # distance to the two edges of this bit: rise at 0, fall at h,
    # next rise at 1250 (only if the next bit exists)
    dist_rise = u                       # >0
    dist_fall = h - u                   # >0 inside high
    dist_next = 1250.0 - u
    x = np.where(pred == 1, np.minimum(dist_rise, dist_fall),
                 np.minimum(u - h, dist_next))
    for s in range(8):
        sel = c["sl"][m] == s
        X[s].append(x[sel]); Y[s].append(c["lv"][m][sel]); P[s].append(pred[sel])

print("slot   n    mism   MLE mu(ns)  sigma(ns)   P(mis|x>150)")
tot = []
for s in range(8):
    x = np.concatenate(X[s]); y = np.concatenate(Y[s]); p = np.concatenate(P[s])
    ok = (y == p).astype(float)

    def nll(th, x=x, ok=ok):
        mu, ls = th
        sg = np.exp(ls)
        q = np.clip(0.5*(1+np.vectorize(math.erf)((x + mu)/(sg*math.sqrt(2)))), 1e-9, 1-1e-9)
        return -np.sum(ok * np.log(q) + (1 - ok) * np.log(1 - q))

    best = None
    for mu in np.arange(-60, 60.1, 2.0):
        for sg in np.arange(5.0, 160.1, 2.5):
            v = nll((mu, np.log(sg)))
            if best is None or v < best[0]:
                best = (v, mu, sg)
    mu, sg = best[1], best[2]
    far = x > 150
    print(f" {s}  {len(x):5d}  {int((~ok.astype(bool)).sum()):4d}   "
          f"{mu:8.1f}   {sg:8.1f}     {1-ok[far].mean():.4f}")
    tot.append((mu, sg))
xa = np.concatenate([np.concatenate(X[s]) for s in range(8)])
ya = np.concatenate([np.concatenate(Y[s]) for s in range(8)])
pa = np.concatenate([np.concatenate(P[s]) for s in range(8)])
oka = (ya == pa).astype(float)
print("\nP(mismatch) vs distance-to-edge (all slots):")
for lo in range(0, 400, 25):
    m = (xa >= lo) & (xa < lo + 25)
    if m.sum():
        print(f"  x={lo:4d}-{lo+25:4d}  n={m.sum():5d}  P(mis)={1-oka[m].mean():.4f}")
m = xa >= 400
print(f"  x>=400        n={m.sum():5d}  P(mis)={1-oka[m].mean():.4f}")
