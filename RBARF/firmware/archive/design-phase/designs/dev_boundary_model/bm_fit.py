"""Fit the sampling grid per capture by minimising total distance-to-legal.

Model:  t(i,s) = T0 + G*i + O[s] - d*N(i,s)
Objective: sum over frame-region samples of the distance from t to the
nearest instant where the (known) wire waveform has the observed level.
Zero objective == the grid is fully consistent with the wire.
"""
import json

import numpy as np

from bm_common import BIT_NS, load, window

CY = 62.5


def wire_segments(bits, h1, h0):
    """Return (edges, levels): waveform is `levels[k]` on [edges[k], edges[k+1])."""
    e = [-1e9]
    lv = [0]
    for j, b in enumerate(bits):
        hw = h1 if b else h0
        e.append(j * BIT_NS)
        lv.append(1)
        e.append(j * BIT_NS + hw)
        lv.append(0)
    e.append(len(bits) * BIT_NS)
    lv.append(0)
    e.append(1e9)
    # merge equal-level neighbours (a 0-bit followed by 1-bit etc. keeps low runs)
    E = [e[0]]
    L = [lv[0]]
    for k in range(1, len(lv)):
        if lv[k] == L[-1]:
            continue
        E.append(e[k])
        L.append(lv[k])
    E.append(1e9)
    return np.array(E, float), np.array(L, np.int8)


def dist_to_legal(t, E, L, obs):
    """Distance from each t to the nearest instant whose wire level == obs."""
    k = np.searchsorted(E, t, side="right") - 1
    k = np.clip(k, 0, len(L) - 1)
    ok = L[k] == obs
    lo = E[k]
    hi = E[np.clip(k + 1, 0, len(E) - 1)]
    d = np.minimum(t - lo, hi - t)
    return np.where(ok, 0.0, d)


class Cap:
    def __init__(self, c, h1, h0, margin=16):
        w = window(c, margin)
        self.it = c["it"][w].astype(float)
        self.sl = c["sl"][w]
        self.lv = c["lv"][w].astype(np.int8)
        self.N = np.concatenate([[0], np.cumsum(c["lv"].astype(np.int64))[:-1]])[w].astype(float)
        self.E, self.L = wire_segments(c["bits"], h1, h0)
        self.key = c["key"]
        self.n = len(self.lv)

    def cost(self, p):
        T0, G, d = p[0], p[1], p[2]
        O = p[3:11]
        t = T0 + G * self.it + O[self.sl] - d * self.N
        return float(dist_to_legal(t, self.E, self.L, self.lv).sum())

    def nbad(self, p):
        T0, G, d = p[0], p[1], p[2]
        O = p[3:11]
        t = T0 + G * self.it + O[self.sl] - d * self.N
        return int(np.count_nonzero(dist_to_legal(t, self.E, self.L, self.lv) > 0))


def coord_descent(cap, p, steps=(64.0, 16.0, 4.0, 1.0, 0.25, 0.0625), rounds=8):
    p = np.array(p, float)
    c = cap.cost(p)
    idx = [0, 1, 2] + list(range(3, 11))
    for st in steps:
        for _ in range(rounds):
            improved = False
            for i in idx:
                sc = st * (0.02 if i == 1 else 1.0)  # G moves in finer steps
                for dv in (sc, -sc, 2 * sc, -2 * sc):
                    q = p.copy()
                    q[i] += dv
                    cc = cap.cost(q)
                    if cc < c - 1e-9:
                        p, c, improved = q, cc, True
            if not improved:
                break
    return p, c


def initial(h1, h0):
    O = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * CY
    return np.concatenate([[100.0, 40.4 * CY, 0.0], O])


def main():
    h1, h0 = 737.0, 339.0
    meta, caps = load()
    res = {}
    tot_bad = tot_n = 0
    for c in caps:
        cap = Cap(c, h1, h0)
        best = None
        for T0 in np.arange(-40.0, 320.0, 20.0):
            for G in np.arange(2500.0, 2545.0, 1.5):
                p = initial(h1, h0)
                p[0], p[1] = T0, G
                cc = cap.cost(p)
                if best is None or cc < best[0]:
                    best = (cc, p)
        p, c0 = coord_descent(cap, best[1])
        res[cap.key] = dict(p=list(map(float, p)), cost=c0, nbad=cap.nbad(p),
                            n=cap.n)
        tot_bad += cap.nbad(p)
        tot_n += cap.n
        print(f"{cap.key:16s} cost={c0:9.1f} bad={cap.nbad(p):3d}/{cap.n:4d} "
              f"G={p[1]:.2f} d={p[2]:6.2f} "
              f"O={[round(x, 1) for x in p[3:11]]}", flush=True)
    print(f"TOTAL bad {tot_bad}/{tot_n} = {100*tot_bad/tot_n:.3f}%")
    json.dump(res, open("bm_fit1.json", "w"), indent=1)


if __name__ == "__main__":
    main()
