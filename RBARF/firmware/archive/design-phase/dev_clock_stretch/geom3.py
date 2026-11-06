"""geom2 + a level-dependent intra-loop stretch term (dev, uses truth).

t(i, s) = u_i + [ delta_s + sum_{s' < s} eps_{s'} * level(i, s') ] * P/2500

If the sampling instruction path really costs one extra CPU cycle when the
pin reads high, eps should come out near +62.5 ns for the responsible
slot(s).
"""
import sys, math, json
sys.path.insert(0, '/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
import importlib.util
spec = importlib.util.spec_from_file_location(
    'g2', '/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_clock_stretch/geom2.py')

from harness import load_dataset, linearize

BIT = 1250.0
T0H, T1H, SIG, SIG_R = 350.0, 700.0, 45.0, 45.0
LAM = 0.004
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
    LUT.append([(lambda p: (math.log(p), math.log(1 - p)))(p_high(j * _ST, b))
                for j in range(_N)])


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
        self.its = [i for i in sorted(self.by_it) if len(self.by_it[i]) == 8]
        self.name = c['pattern'] + str(c['rep'])
        self.P = 2500.0
        self.u = {i: 2500.0 * i for i in sorted(self.by_it)}
        # cumulative high count before each slot
        self.pre = {}
        for i in self.its:
            lv = {sl: v for sl, v in self.by_it[i]}
            self.pre[i] = [[lv[t] for t in range(s_)] for s_ in range(8)]


def offs(cap, i, s, delta, eps):
    o = delta[s]
    pre = cap.pre.get(i)
    if pre is not None:
        for t, v in enumerate(pre[s]):
            if v:
                o += eps[t]
    return o


def opt_cap(cap, delta, eps, rounds=3):
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
                        c -= ll(cand + offs(cap, i, sl, delta, eps) * sc, cap.bits, v)
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
    cap.P = (cap.u[cap.its[-1]] - cap.u[cap.its[0]]) / (cap.its[-1] - cap.its[0])


def total_ll(data, delta, eps):
    c = 0.0
    for cap in data:
        sc = cap.P / 2500.0
        for i in cap.its:
            ui = cap.u[i]
            for sl, v in cap.by_it[i]:
                c -= ll(ui + offs(cap, i, sl, delta, eps) * sc, cap.bits, v)
    return c


def main():
    meta, caps = load_dataset()
    data = [Cap(c) for c in caps if c['rep'] in (0, 1)]
    delta = [x * 62.5 for x in [1.41, 4.78, 9.38, 13.19, 19.06, 21.97, 27.50, 31.44]]
    d0 = delta[0]
    delta = [d - d0 for d in delta]
    eps = [0.0] * 8
    for outer in range(6):
        for cap in data:
            opt_cap(cap, delta, eps, rounds=3 if outer == 0 else 2)
        print(f"outer {outer} cost={total_ll(data, delta, eps):.0f} "
              f"delta={[round(x,1) for x in delta]} eps={[round(x,1) for x in eps]}",
              flush=True)
        for s in range(1, 8):
            best = None
            for j in range(-30, 31):
                cand = list(delta)
                cand[s] += j * 4.0
                c = total_ll(data, cand, eps)
                if best is None or c < best[0]:
                    best = (c, cand[s])
            delta[s] = best[1]
        for s in range(0, 7):
            best = None
            for j in range(-8, 9):
                cand = list(eps)
                cand[s] = j * 10.0
                c = total_ll(data, delta, cand)
                if best is None or c < best[0]:
                    best = (c, cand[s])
            eps[s] = best[1]
    print(json.dumps({'delta': delta, 'eps': eps,
                      'pos_cycles': [round(x / 62.5, 3) for x in delta]}))


main()
