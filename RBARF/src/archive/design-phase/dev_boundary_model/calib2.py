"""Slot-offset calibration, take 2.

Discrete search: the documented inter-sample gaps are [4,4,4,4,4,6,5,6]
cycles (the last one crossing the loop boundary), summing to 37, but the
measured loop is ~40.1 cycles.  Enumerate every way of distributing the
missing ~3 cycles across the 8 gaps, fit per-capture (L, B) for each
candidate with a smooth (distance-transform) loss, and rank by hard
sample mismatch.  Then refine continuously.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import linearize, load_dataset  # noqa: E402

BIT = 1250.0
T0H, T1H = 350.0, 700.0
NB = 192
END = NB * BIT
GLO, GHI = -6000, 246000       # distance-transform grid range (ns, 1 ns step)


def frame_bits(frame_hex):
    fb = bytes.fromhex(frame_hex)
    return np.array([(b >> (7 - k)) & 1 for b in fb for k in range(8)])


def dist_transform(mask):
    """1-D distance (in samples/ns) to nearest True in mask."""
    n = len(mask)
    INF = 10 ** 9
    d = np.where(mask, 0, INF).astype(np.int64)
    for i in range(1, n):
        if d[i] > d[i - 1] + 1:
            d[i] = d[i - 1] + 1
    for i in range(n - 2, -1, -1):
        if d[i] > d[i + 1] + 1:
            d[i] = d[i + 1] + 1
    return d


def dist_transform_fast(mask):
    n = len(mask)
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return np.full(n, 10 ** 9, dtype=np.int64)
    pos = np.arange(n)
    j = np.searchsorted(idx, pos)
    jl = np.clip(j - 1, 0, len(idx) - 1)
    jr = np.clip(j, 0, len(idx) - 1)
    return np.minimum(np.abs(pos - idx[jl]), np.abs(pos - idx[jr])).astype(np.int64)


class Cap:
    def __init__(self, cap, max_it=115):
        s = [x for x in linearize(cap["capture"]) if x[0] <= max_it]
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s], dtype=int)
        self.v = np.array([x[2] for x in s], dtype=int)
        bits = frame_bits(cap["frame"])
        self.th = np.where(bits == 1, T1H, T0H)
        self.pattern, self.rep = cap["pattern"], cap["rep"]
        # waveform on a 1 ns grid
        g = np.arange(GLO, GHI)
        hi = np.zeros(len(g), dtype=bool)
        for i in range(NB):
            a = int(i * BIT) - GLO
            b = a + int(self.th[i])
            hi[a:b] = True
        self.hi = hi
        self.d1 = dist_transform_fast(hi)
        self.d0 = dist_transform_fast(~hi)
        allsam = linearize(cap["capture"])
        h = [k for k, x in enumerate(allsam) if x[2] == 1]
        self.last_hi = allsam[h[-1]]

    def _idx(self, t):
        return np.clip(np.round(t).astype(np.int64) - GLO, 0, len(self.hi) - 1)

    def hard(self, L, B, farr):
        t = B + L * (self.it + farr[self.sl])
        i = self._idx(t)
        pred = self.hi[i].astype(int)
        pred[(t < 0) | (t >= END)] = 0
        return int(np.sum(pred != self.v)), len(self.v)

    def soft(self, L, B, farr, cap_ns=600.0):
        t = B + L * (self.it + farr[self.sl])
        i = self._idx(t)
        d = np.where(self.v == 1, self.d1[i], self.d0[i]).astype(float)
        return float(np.minimum(d, cap_ns).sum())


def fit_LB(c, farr, L_lo=2470.0, L_hi=2545.0):
    it, sl, _ = c.last_hi
    denom = it + farr[sl]
    L0 = (END - BIT + T1H - 200.0) / denom if denom > 0 else 2507.3
    L0 = min(max(L0, L_lo), L_hi)
    Ls = np.arange(L0 - 25, L0 + 25, 0.4)
    Bs = np.arange(-250, 500, 15.0)
    x = c.it + farr[c.sl]                       # (n,)
    LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
    LL = LL.ravel()
    BB = BB.ravel()
    T = BB[:, None] + LL[:, None] * x[None, :]   # (nc, n)
    I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(c.hi) - 1)
    D = np.where(c.v[None, :] == 1, c.d1[I], c.d0[I]).astype(np.float64)
    np.minimum(D, 600.0, out=D)
    tot_s = D.sum(axis=1)
    k = int(np.argmin(tot_s))
    s, L, B = float(tot_s[k]), float(LL[k]), float(BB[k])
    for stepL, stepB in ((0.2, 6.0), (0.07, 2.0), (0.025, 0.7), (0.01, 0.25)):
        for _ in range(300):
            improved = False
            for dL in (-stepL, 0.0, stepL):
                for dB in (-stepB, 0.0, stepB):
                    if dL == 0 and dB == 0:
                        continue
                    ns = c.soft(L + dL, B + dB, farr)
                    if ns < s - 1e-9:
                        s, L, B = ns, L + dL, B + dB
                        improved = True
            if not improved:
                break
    # polish on the hard objective locally
    hb = c.hard(L, B, farr)[0]
    bL, bB = L, B
    for dL in np.arange(-0.6, 0.61, 0.05):
        for dB in np.arange(-25, 25.1, 2.5):
            h = c.hard(L + dL, B + dB, farr)[0]
            if h < hb:
                hb, bL, bB = h, L + dL, B + dB
    return hb, bL, bB


def farr_from_gaps(gaps):
    """gaps[0..7] cycles; gaps[7] crosses the loop boundary."""
    tot = float(sum(gaps))
    cum = [0.0]
    for g in gaps[:7]:
        cum.append(cum[-1] + g)
    return np.array([x / tot for x in cum]), tot


def main():
    meta, caps = load_dataset()
    base = [4, 4, 4, 4, 4, 6, 5, 6]
    train = [c for c in caps if c["rep"] in (0, 1)]
    # use a diverse subset for the discrete sweep (speed)
    pick = ["ones", "zeros", "aa", "rnd1", "count", "edges", "lone1", "dense"]
    sub = [Cap(c) for c in train if c["pattern"] in pick and c["rep"] == 0]
    print("subset:", [c.pattern for c in sub])

    results = []
    for extra in (2, 3, 4):
        for combo in itertools.combinations_with_replacement(range(8), extra):
            add = [0] * 8
            for i in combo:
                add[i] += 1
            gaps = [b + a for b, a in zip(base, add)]
            farr, tot = farr_from_gaps(gaps)
            bad = n = 0
            for c in sub:
                h, L, B = fit_LB(c, farr)
                bad += h
                n += len(c.v)
            results.append((bad / n, tuple(gaps), bad, n))
    results.sort()
    for r in results[:20]:
        print(f"  {r[0]:.4%}  gaps={r[1]}  ({r[2]}/{r[3]})")
    Path(__file__).with_name("disc.json").write_text(
        json.dumps([[r[0], list(r[1])] for r in results[:40]]))


if __name__ == "__main__":
    main()
