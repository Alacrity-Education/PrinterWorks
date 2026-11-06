"""Direct measurement of the intra-loop slot geometry (dev, uses truth).

t(i, s) = u_i + delta_s * Pbar / 2500      (u_i free per iteration)

u is regularised to be smooth (the loop period cannot jump); delta is
global across all train captures.  Alternating 1-D line searches on the
soft sample log-likelihood.  Output: delta in ns, and SLOT_POS in cycles
(delta / 62.5) for a nominal 2500 ns / 40-cycle loop.
"""
import sys, math, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

BIT = 1250.0
T0H = 350.0
T1H = 700.0
SIG = 45.0
SIG_R = 45.0
LAM = 0.004          # smoothness on u (per ns^2)
NBITS = 192


def p_high(ph, bit):
    th = T1H if bit else T0H
    a = 1.0 / (1.0 + math.exp(-ph / SIG_R))
    c = 1.0 / (1.0 + math.exp((ph - th) / SIG))
    v = a * c
    return 1e-4 if v < 1e-4 else (1 - 1e-4 if v > 1 - 1e-4 else v)


_ST = 2.0
_N = int(BIT / _ST) + 3
LUT = []
for b in (0, 1):
    row = []
    for j in range(_N):
        p = p_high(j * _ST, b)
        row.append((math.log(p), math.log(1 - p)))
    LUT.append(row)


def ll(t, bits, v):
    if t < 0:
        return math.log(1e-4) if v else 0.0
    k = int(t // BIT)
    if k >= NBITS:
        return math.log(1e-4) if v else 0.0
    j = int((t - k * BIT) / _ST)
    if j >= _N:
        j = _N - 1
    e = LUT[bits[k]][j]
    return e[0] if v else e[1]


class Cap:
    def __init__(self, c):
        s = linearize(c['capture'])
        self.bits = [int(x) for b in bytes.fromhex(c['frame']) for x in f"{b:08b}"]
        self.by_it = {}
        for it, sl, v in s:
            if it > 97:
                continue
            self.by_it.setdefault(it, []).append((sl, v))
        self.its = sorted(self.by_it)
        self.name = c['pattern'] + str(c['rep'])
        self.P = 2500.0
        self.u = {i: 2500.0 * i for i in self.its}


def cap_cost(cap, delta):
    sc = cap.P / 2500.0
    tot = 0.0
    for i in cap.its:
        ui = cap.u[i]
        for sl, v in cap.by_it[i]:
            tot -= ll(ui + delta[sl] * sc, cap.bits, v)
    for i in cap.its[1:-1]:
        s2 = cap.u[i + 1] - 2 * cap.u[i] + cap.u[i - 1] if (i + 1) in cap.u else 0.0
        tot += LAM * s2 * s2
    return tot


def opt_cap(cap, delta, rounds=4):
    sc = cap.P / 2500.0
    for _ in range(rounds):
        for i in cap.its:
            base = cap.u[i]
            best = None
            for step in (60.0, 20.0, 6.0, 2.0):
                centre = best[1] if best else base
                for j in range(-6, 7):
                    cand = centre + j * step
                    c = 0.0
                    for sl, v in cap.by_it[i]:
                        c -= ll(cand + delta[sl] * sc, cap.bits, v)
                    for nb in (i - 1, i + 1):
                        pass
                    # smoothness with neighbours
                    if i - 1 in cap.u and i + 1 in cap.u:
                        s2 = cap.u[i + 1] - 2 * cand + cap.u[i - 1]
                        c += LAM * s2 * s2
                    if i - 2 in cap.u and i - 1 in cap.u:
                        s2 = cand - 2 * cap.u[i - 1] + cap.u[i - 2]
                        c += LAM * s2 * s2
                    if i + 2 in cap.u and i + 1 in cap.u:
                        s2 = cap.u[i + 2] - 2 * cap.u[i + 1] + cand
                        c += LAM * s2 * s2
                    if best is None or c < best[0]:
                        best = (c, cand)
            cap.u[i] = best[1]
    n = len(cap.its)
    cap.P = (cap.u[cap.its[-1]] - cap.u[cap.its[0]]) / (cap.its[-1] - cap.its[0])
    return cap


def main():
    meta, caps = load_dataset()
    data = [Cap(c) for c in caps if c['rep'] in (0, 1)]
    delta = [x * 62.5 for x in [1.41, 4.78, 9.38, 13.19, 19.06, 21.97, 27.50, 31.44]]
    d0 = delta[0]
    delta = [d - d0 for d in delta]
    # init u from a rough linear model per capture
    for cap in data:
        for i in cap.its:
            cap.u[i] = 2500.0 * i
    for outer in range(6):
        tot = 0.0
        for cap in data:
            opt_cap(cap, delta, rounds=2 if outer else 4)
            tot += cap_cost(cap, delta)
        print(f"outer {outer} cost={tot:.0f} "
              f"delta={[round(x, 1) for x in delta]} "
              f"pos={[round(x/62.5, 2) for x in delta]}", flush=True)
        # optimise delta
        for s in range(1, 8):
            best = None
            for j in range(-40, 41):
                cand = list(delta)
                cand[s] += j * 4.0
                if not (cand[s - 1] < cand[s] if s else True):
                    continue
                c = 0.0
                for cap in data:
                    sc = cap.P / 2500.0
                    for i in cap.its:
                        ui = cap.u[i]
                        for sl, v in cap.by_it[i]:
                            if sl == s:
                                c -= ll(ui + cand[sl] * sc, cap.bits, v)
                if best is None or c < best[0]:
                    best = (c, cand[s])
            delta[s] = best[1]
    print(json.dumps({'delta_ns': delta,
                      'slot_pos_cycles': [round(x / 62.5, 3) for x in delta],
                      'P': [round(c.P, 1) for c in data]}))


main()
