"""Global sampling-grid fit.

  t(i,s) = T0_c + G_c*i + O[s] - d*N(i,s)

O[0..7], d, h1, h0 are GLOBAL (hardware); T0_c, G_c are per-capture.
Objective: mismatched samples in the frame region (+ tiny distance
tie-break so the optimiser can see downhill inside a plateau).
"""
import json
import sys

import numpy as np

from bm_common import BIT_NS, load, window
from bm_fit import wire_segments, dist_to_legal

CY = 62.5
DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) * CY


class C:
    def __init__(self, c, margin=16):
        w = window(c, margin)
        self.key = c["key"]
        self.it = c["it"][w].astype(float)
        self.sl = c["sl"][w]
        self.lv = c["lv"][w].astype(np.int8)
        self.N = np.concatenate(
            [[0], np.cumsum(c["lv"].astype(np.int64))[:-1]])[w].astype(float)
        self.bits = c["bits"]
        self.n = len(self.lv)
        self.T0 = 100.0
        self.G = 2505.0

    def seg(self, h1, h0):
        self.E, self.L = wire_segments(self.bits, h1, h0)

    def t(self, O, d):
        return self.T0 + self.G * self.it + O[self.sl] - d * self.N

    def cost(self, O, d):
        dd = dist_to_legal(self.t(O, d), self.E, self.L, self.lv)
        return float(np.count_nonzero(dd)) + 1e-4 * float(dd.sum())

    def fit_tg(self, O, d, coarse=False):
        best = (1e18, self.T0, self.G)
        if coarse:
            for G in np.arange(2470.0, 2540.0, 0.5):
                for T0 in np.arange(-60.0, 300.0, 8.0):
                    self.T0, self.G = T0, G
                    c = self.cost(O, d)
                    if c < best[0]:
                        best = (c, T0, G)
        _, self.T0, self.G = best if coarse else (self.cost(O, d), self.T0, self.G)
        c = self.cost(O, d)
        st, sg = 8.0, 0.5
        while st > 1e-3:
            found = False
            for dt, dg in ((st, 0), (-st, 0), (0, sg), (0, -sg),
                           (st, sg), (st, -sg), (-st, sg), (-st, -sg)):
                self.T0 += dt
                self.G += dg
                cc = self.cost(O, d)
                if cc < c - 1e-12:
                    c, found = cc, True
                    break
                self.T0 -= dt
                self.G -= dg
            if not found:
                st /= 2.0
                sg /= 2.0
        return c


def total(caps, O, d):
    return sum(c.cost(O, d) for c in caps)


def refit(caps, O, d, coarse=False):
    return sum(c.fit_tg(O, d, coarse) for c in caps)


def main(use_d=True, tag="A"):
    meta, raw = load()
    caps = [C(c) for c in raw]
    h1, h0 = 750.0, 375.0
    O = DOC.copy()
    d = 0.0
    for c in caps:
        c.seg(h1, h0)
    tot = refit(caps, O, d, coarse=True)
    N = sum(c.n for c in caps)
    print(f"seed: {tot:.1f}  bad~{int(tot)}/{N}", flush=True)

    for phase, step in enumerate([16.0, 8.0, 4.0, 2.0, 1.0, 0.5, 0.25]):
        for rnd in range(6):
            prev = tot
            for s in range(8):
                base = O[s]
                best = (total(caps, O, d), base)
                for v in base + np.arange(-4, 5) * step:
                    O[s] = v
                    cc = total(caps, O, d)
                    if cc < best[0]:
                        best = (cc, v)
                O[s] = best[1]
            if use_d:
                best = (total(caps, O, d), d)
                for v in d + np.arange(-4, 5) * step * 0.25:
                    cc = total(caps, O, v)
                    if cc < best[0]:
                        best = (cc, v)
                d = best[1]
            for nm, lo, hi in (("h1", 700.0, 790.0), ("h0", 320.0, 420.0)):
                cur = h1 if nm == "h1" else h0
                best = (total(caps, O, d), cur)
                for v in np.clip(cur + np.arange(-4, 5) * step, lo, hi):
                    if nm == "h1":
                        for c in caps:
                            c.seg(v, h0)
                    else:
                        for c in caps:
                            c.seg(h1, v)
                    cc = total(caps, O, d)
                    if cc < best[0]:
                        best = (cc, v)
                if nm == "h1":
                    h1 = best[1]
                else:
                    h0 = best[1]
                for c in caps:
                    c.seg(h1, h0)
            tot = refit(caps, O, d)
            print(f"p{phase} r{rnd}: cost={tot:.2f} bad={sum(1 for _ in [])} "
                  f"O={[round(x,1) for x in O]} d={d:.2f} h1={h1:.1f} h0={h0:.1f}",
                  flush=True)
            if tot >= prev - 1e-9:
                break

    bad = 0
    for c in caps:
        dd = dist_to_legal(c.t(O, d), c.E, c.L, c.lv)
        bad += int(np.count_nonzero(dd))
    print(f"FINAL bad {bad}/{N} = {100*bad/N:.3f}%")
    gaps = np.diff(np.concatenate([O, [O[0]]]))
    gaps[-1] = O[0] + np.mean([c.G for c in caps]) - O[7]
    print("gaps ns  :", [round(x, 1) for x in gaps])
    print("gaps cy  :", [round(x / CY, 2) for x in gaps])
    print("Gc: min %.1f med %.1f max %.1f" % (
        min(c.G for c in caps), float(np.median([c.G for c in caps])),
        max(c.G for c in caps)))
    json.dump(dict(O=list(O), d=d, h1=h1, h0=h0, bad=bad, N=N,
                   per={c.key: [c.T0, c.G, c.n] for c in caps}),
              open(f"bm_global_{tag}.json", "w"), indent=1)


if __name__ == "__main__":
    main(use_d=(sys.argv[1] != "nod") if len(sys.argv) > 1 else True,
         tag=sys.argv[1] if len(sys.argv) > 1 else "A")
