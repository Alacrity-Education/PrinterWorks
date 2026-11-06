"""Local phase tracking: how much does the true sample time deviate from
the best global linear model, as a function of loop index?

For each loop-window we search a local time shift dt that maximises
agreement with the (known) waveform, holding slot offsets and k fixed.
The resulting track dt(i) is the *alignment error process* that the DP
transition model has to absorb.
"""
import json, statistics
import model as M
from fit_slots import FRAME_NS

fit = json.load(open("slotfit.json"))
O = fit["o"]
meta, D = M.load()
W = 4            # window in loops
SH = [x * 10.0 for x in range(-70, 71)]


def track(d, phi, k):
    bits = d["bits"]
    by_loop = {}
    for (i, s), v in zip(d["idx"], d["obs"]):
        by_loop.setdefault(i, []).append((s, v))
    out = []
    maxi = max(by_loop)
    for i0 in range(0, maxi + 1):
        items = []
        for i in range(i0, min(i0 + W, maxi + 1)):
            for s, v in by_loop.get(i, []):
                items.append((i, s, v))
        if not items:
            continue
        base = [phi + k * (i * M.L_NOM + O[s]) for i, s, _ in items]
        if base[0] > FRAME_NS or base[-1] < 0:
            continue
        best = (-1, 0.0)
        for dt in SH:
            m = sum(1 for t, (_, _, v) in zip(base, items)
                    if M.level_at(bits, t + dt) == v)
            if m > best[0]:
                best = (m, dt)
        out.append((i0, best[1], best[0], len(items)))
    return out


allsteps = []
print("capture      mean|dt|  max|dt|  span  step-rms  frac-perfect-window")
for d, (phi, k) in zip(D, fit["nuis"]):
    tr = track(d, phi, k)
    if not tr:
        continue
    dts = [x[1] for x in tr]
    steps = [dts[j + 1] - dts[j] for j in range(len(dts) - 1)]
    allsteps += steps
    perfect = sum(1 for x in tr if x[2] == x[3]) / len(tr)
    print(f"{d['pattern']:11s}r{d['rep']} {statistics.mean(map(abs,dts)):7.1f} "
          f"{max(map(abs,dts)):7.1f} {max(dts)-min(dts):6.1f} "
          f"{statistics.pstdev(steps):8.1f} {perfect:6.2f}")

print(f"\nglobal step stats: n={len(allsteps)} rms={statistics.pstdev(allsteps):.1f} "
      f"mean={statistics.mean(allsteps):.2f} "
      f"p90|step|={sorted(map(abs,allsteps))[int(.9*len(allsteps))]:.1f}")
