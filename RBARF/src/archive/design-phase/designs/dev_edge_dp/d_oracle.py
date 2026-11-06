"""Is edge_dp's residual error a SEARCH failure or a MODEL failure?

For each capture run the trellis twice over the same (kappa, d, v) search:
  A) payload bits free (the real decoder)
  B) all 192 bits pinned to ground truth (oracle path)
If cost(B) < cost(A) the ML path is not the true path -> the SEARCH is
fine but the objective is mis-specified is FALSE; it means the search
missed it.  If cost(B) > cost(A) the model genuinely prefers the wrong
bits -> a MODEL failure that only extra evidence (priors from the other
techniques, or a better emission) can fix.
"""
import sys
import time

import numpy as np

import dp2

meta, caps = dp2.CM.load()
KG = tuple(np.arange(-0.001, 0.0071, 0.0005))
P = dict(kgrid=KG, dlo=-900.0, dhi=900.0, d0sig=1000.0, we=25.0, floor=0.01,
         dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25)
for a in sys.argv[1:]:
    k, v = a.split("=")
    P[k] = float(v)


def run(c, A, pin_all_bits=None):
    p = dict(P)
    lv = c["lv"]
    k0, a0, a1 = dp2.blind_kappa(A, lv)
    dgrid = np.arange(p["dlo"], p["dhi"] + 1e-9, p["dstep"])
    vgrid = np.arange(-p["vmax"], p["vmax"] + 1e-9, p["vstep"])
    d0 = -k0 * a0
    best = None
    for dk in p["kgrid"]:
        kap = k0 * (1 + dk)
        E = dp2.emissions(A, lv, kap, dgrid, p["we"], p["floor"])
        prior = None
        if pin_all_bits is not None:
            prior = np.zeros((192, 2))
            for j in range(192):
                prior[j, 1 - int(pin_all_bits[j])] = 1e9
        pen = lambda d, d0=d0, s=p["d0sig"]: 0.5 * ((d - d0) / s) ** 2
        tot, bits, dtr, _ = dp2.viterbi(E, dgrid, vgrid, p["vpen"], pen, prior)
        if best is None or tot < best[0]:
            best = (tot, bits, dtr, kap)
    return best


t0 = time.time()
search_fail = model_fail = nex = 0
gaps = []
for c in caps:
    A = dp2.A_of(c)
    true = np.array(c["bits"])
    cf, bf, _, kf = run(c, A)
    ex = (bf[32:160] == true[32:160]).all()
    nex += ex
    if ex:
        continue
    ct, bt, _, kt = run(c, A, pin_all_bits=true)
    ct -= 0.0
    gap = ct - cf
    gaps.append(gap)
    if gap < 0:
        search_fail += 1
        tag = "SEARCH"
    else:
        model_fail += 1
        tag = "MODEL "
    ne = int((bf[32:160] != true[32:160]).sum())
    print(f"  {c['key']:14s} {tag} nerr={ne:2d} cost_free={cf:9.3f} "
          f"cost_true={ct:9.3f} gap={gap:+8.3f} kf={kf:.5f} kt={kt:.5f}")
print(f"\nEXACT {nex}/54;  of the {54-nex} misses: SEARCH failures "
      f"{search_fail}, MODEL failures {model_fail}")
if gaps:
    print(f"cost gap (true - ML): median {np.median(gaps):+.3f} nats, "
          f"max {max(gaps):+.3f}, min {min(gaps):+.3f}  ({time.time()-t0:.0f}s)")
