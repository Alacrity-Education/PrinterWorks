"""Coordinate-ascent calibration of the 8 fractional slot phases.

Alternates:
  (a) exact-ish grid fit of per-capture (L, B) with F fixed
  (b) exhaustive 1-D grid fit of each F[k] with all (L, B) fixed
maximizing agreement between observed levels and the known full frame
waveform.  Multi-start over several initial F vectors.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import linearize, load_dataset  # noqa: E402

BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
END = NB * BIT
GLO, GHI = -8000, 310000
MAXIT = 118


def bits_of(h):
    fb = bytes.fromhex(h)
    return [(b >> (7 - k)) & 1 for b in fb for k in range(8)]


def dtrans(mask):
    n = len(mask)
    idx = np.flatnonzero(mask)
    pos = np.arange(n)
    j = np.searchsorted(idx, pos)
    jl = np.clip(j - 1, 0, len(idx) - 1)
    jr = np.clip(j, 0, len(idx) - 1)
    return np.minimum(np.abs(pos - idx[jl]),
                      np.abs(pos - idx[jr])).astype(np.float64)


class Cap:
    def __init__(self, cap):
        s = [x for x in linearize(cap["capture"]) if x[0] <= MAXIT]
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s], dtype=int)
        self.v = np.array([x[2] for x in s], dtype=np.int8)
        bits = bits_of(cap["frame"])
        hi = np.zeros(GHI - GLO, dtype=bool)
        for i, b in enumerate(bits):
            a = int(i * BIT) - GLO
            hi[a:a + int(T1H if b else T0H)] = True
        self.hi = hi
        self.d1, self.d0 = dtrans(hi), dtrans(~hi)
        self.pattern, self.rep = cap["pattern"], cap["rep"]
        self.n = len(self.v)
        self.slmask = [self.sl == k for k in range(8)]

    def _lookup(self, T):
        return np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)

    def score_grid(self, Ls, Bs, F, hard=True):
        x = self.it + F[self.sl]
        LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
        LL, BB = LL.ravel(), BB.ravel()
        best = None
        step = max(1, int(6e6 // max(1, self.n)))
        for a in range(0, len(LL), step):
            b = min(a + step, len(LL))
            T = BB[a:b, None] + LL[a:b, None] * x[None, :]
            I = self._lookup(T)
            if hard:
                sc = (self.hi[I] != (self.v[None, :] == 1)).sum(axis=1).astype(float)
            else:
                D = np.where(self.v[None, :] == 1, self.d1[I], self.d0[I])
                sc = np.minimum(D, 700.0).sum(axis=1)
            k = int(np.argmin(sc))
            if best is None or sc[k] < best[0]:
                best = (float(sc[k]), float(LL[a + k]), float(BB[a + k]))
        return best

    def fit(self, F):
        _, L, B = self.score_grid(np.arange(2470, 2551, 0.5),
                                  np.arange(-700, 701, 20.0), F, hard=False)
        h, L, B = self.score_grid(np.arange(L - 1.5, L + 1.51, 0.02),
                                  np.arange(B - 40, B + 40.1, 1.0), F)
        h, L, B = self.score_grid(np.arange(L - 0.08, L + 0.081, 0.004),
                                  np.arange(B - 3, B + 3.01, 0.2), F)
        return h, L, B

    def slot_bad_curve(self, L, B, k, cands):
        """bad count per candidate F[k] value."""
        m = self.slmask[k]
        it = self.it[m]
        v = self.v[m] == 1
        T = B + L * (it[None, :] + cands[:, None])
        I = self._lookup(T)
        return (self.hi[I] != v[None, :]).sum(axis=1)


def run(data, F0, rounds=8, verbose=True):
    F = np.array(F0, dtype=float)
    LBs = None
    prev = None
    for r in range(rounds):
        LBs = [c.fit(F) for c in data]
        bad = sum(x[0] for x in LBs)
        n = sum(c.n for c in data)
        if verbose:
            print(f"   round {r}: bad {bad:.0f}/{n} = {bad/n:.3%} "
                  f"F={[round(x,5) for x in F]}", flush=True)
        if prev is not None and bad >= prev:
            return prev_F, prev_LBs, prev
        prev, prev_F, prev_LBs = bad, F.copy(), LBs
        newF = F.copy()
        for k in range(1, 8):
            lo = newF[k - 1] + 0.0008
            hi = (newF[k + 1] - 0.0008) if k < 7 else 0.999
            cands = np.arange(lo, hi, 0.0004)
            if len(cands) == 0:
                continue
            tot = np.zeros(len(cands), dtype=np.int64)
            for c, (_, L, B) in zip(data, LBs):
                tot += c.slot_bad_curve(L, B, k, cands)
            newF[k] = float(cands[int(np.argmin(tot))])
        if np.max(np.abs(newF - F)) < 1e-6:
            break
        F = newF
    return prev_F, prev_LBs, prev


def main():
    meta, caps = load_dataset()
    train = [c for c in caps if c["rep"] in (0, 1)]
    data = [Cap(c) for c in train if c["rep"] == 0]
    print("captures:", len(data), flush=True)
    inits = {
        "doc40": [0, .1, .2, .3, .4, .5, .65, .775],
        "doc37": [p / 37.0 for p in (0, 4, 8, 12, 16, 20, 26, 31)],
        "uniform": [k / 8.0 for k in range(8)],
        "boundary_split": [0, .1, .2, .3, .4, .5, .625, .8],
        "mid": [0, .095, .19, .285, .38, .475, .60, .74],
        "late": [0, .105, .21, .32, .43, .54, .70, .84],
    }
    best = None
    for name, F0 in inits.items():
        print("init", name, flush=True)
        F, LBs, bad = run(data, F0)
        n = sum(c.n for c in data)
        print(f"  -> {name}: {bad:.0f}/{n} = {bad/n:.3%} F={[round(float(x),5) for x in F]}",
              flush=True)
        if best is None or bad < best[0]:
            best = (bad, [float(x) for x in F], name)
    print("BEST", best)
    Path(__file__).with_name("F.json").write_text(json.dumps(best[1]))


if __name__ == "__main__":
    main()
