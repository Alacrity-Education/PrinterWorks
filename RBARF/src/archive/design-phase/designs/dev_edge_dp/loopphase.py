"""Per-loop feasible-phase analysis.

For each sampling loop i, find every loop-start time tau (1 ns grid,
+/-900 ns around the global linear fit) for which ALL 8 slot samples of
that loop agree with the known waveform, using slot offsets k*o[s].
Report: feasibility, interval width, and the deviation of the feasible
midpoint from the linear model.  A constant-period sampler => deviation
is flat; a per-loop-varying period => a staircase / random walk.
"""
import json, sys, statistics
import numpy as np
import model as M
import nfit

fit = json.load(open("nfit.json"))
O = np.array(fit["o"])
meta, D = M.load()
caps = nfit.prep(D)
FRAME_NS = 192 * 1250.0
GRID = np.arange(-900.0, 900.1, 1.0)


def analyse(c, phi, k, verbose=False):
    bits = c["bits"]
    off = k * O
    res = []
    for i in range(200):
        m = c["I"] == i
        if not m.any():
            continue
        S = c["S"][m]; obs = c["obs"][m]
        tau0 = phi + k * i * 2500.0
        if tau0 + off[0] < -300 or tau0 > FRAME_NS:
            continue
        T = tau0 + GRID[:, None] + off[S][None, :]        # (G, nslot)
        kk = np.floor(T / 1250.0).astype(np.int64)
        ok_rng = (kk >= 0) & (kk < len(bits))
        kkc = np.clip(kk, 0, len(bits) - 1)
        u = T - kk * 1250.0
        thr = np.where(bits[kkc] == 1, 750.0, 375.0)
        pred = np.where(ok_rng & (u < thr), 1, 0)
        good = (pred == obs[None, :]).all(axis=1)
        if good.any():
            idxs = np.where(good)[0]
            # largest contiguous run
            splits = np.where(np.diff(idxs) > 1)[0]
            runs = np.split(idxs, splits + 1)
            best = max(runs, key=len)
            res.append((i, float(GRID[best].mean()), len(best), len(idxs)))
        else:
            res.append((i, None, 0, 0))
    return res


print("cap             nloop infeas  dev-range  step-rms  medwidth")
summ = []
for c, (phi, k) in zip(caps, fit["nuis"]):
    r = analyse(c, phi, k)
    dev = [x[1] for x in r if x[1] is not None]
    infeas = sum(1 for x in r if x[1] is None)
    if len(dev) < 3:
        continue
    steps = [dev[j + 1] - dev[j] for j in range(len(dev) - 1)]
    w = statistics.median([x[2] for x in r if x[1] is not None])
    print(f"{c['name']:15s} {len(r):4d} {infeas:5d}  {max(dev)-min(dev):8.1f} "
          f"{statistics.pstdev(steps):8.1f}  {w:6.0f}")
    summ.append((c["name"], r))

json.dump({n: [[x[0], x[1], x[2]] for x in r] for n, r in summ},
          open("loopphase.json", "w"))

# print one detailed track
for name in ("ones_0", "p55_0", "zeros_0"):
    r = dict(summ)[name]
    print(f"\n--- {name} dev(tau) per loop (None = infeasible) ---")
    print(" ".join(f"{x[1]:6.0f}" if x[1] is not None else "  None" for x in r))
