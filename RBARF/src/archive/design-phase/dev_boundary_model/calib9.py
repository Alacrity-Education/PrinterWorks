"""Joint fit of F with a strictly LINEAR per-capture time base.

If the intra-loop geometry were exactly right and the clock stable, a
linear base should explain nearly every sample.  This measures how close
we can get, i.e. how much of the apparent 'wander' is really an F error.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa

BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
GLO, GHI = -9000, 320000
MAXIT = 112


def dtrans(mask):
    n = len(mask)
    idx = np.flatnonzero(mask)
    pos = np.arange(n)
    j = np.searchsorted(idx, pos)
    jl = np.clip(j - 1, 0, len(idx) - 1)
    jr = np.clip(j, 0, len(idx) - 1)
    return np.minimum(np.abs(pos - idx[jl]), np.abs(pos - idx[jr])).astype(float)


class Cap:
    def __init__(self, cap):
        s = [x for x in linearize(cap["capture"]) if x[0] <= MAXIT]
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s])
        self.v = np.array([x[2] for x in s]) == 1
        bits = bm._bits(bytes.fromhex(cap["frame"]))
        hi = np.zeros(GHI - GLO, dtype=bool)
        for i, b in enumerate(bits):
            a = int(i * BIT) - GLO
            hi[a:a + int(T1H if b else T0H)] = True
        self.hi = hi
        self.d1, self.d0 = dtrans(hi), dtrans(~hi)
        self.pattern = cap["pattern"]
        self.n = len(self.v)
        self.L = 2500.0
        self.B = 150.0

    def _sc(self, LL, BB, F, hard):
        x = self.it + F[self.sl]
        out = np.empty(len(LL))
        step = max(1, int(8e6 // self.n))
        for a in range(0, len(LL), step):
            b = min(a + step, len(LL))
            T = BB[a:b, None] + LL[a:b, None] * x[None, :]
            I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
            if hard:
                out[a:b] = (self.hi[I] != self.v[None, :]).sum(axis=1)
            else:
                D = np.where(self.v[None, :], self.d1[I], self.d0[I])
                out[a:b] = np.minimum(D, 700.0).sum(axis=1)
        return out

    def grid(self, Ls, Bs, F, hard=True):
        LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
        LL, BB = LL.ravel(), BB.ravel()
        sc = self._sc(LL, BB, F, hard)
        k = int(np.argmin(sc))
        return float(sc[k]), float(LL[k]), float(BB[k])

    def fit(self, F, wide=True):
        if wide:
            _, L, B = self.grid(np.arange(2470, 2551, 0.4),
                                np.arange(-700, 701, 20.0), F, False)
        else:
            L, B = self.L, self.B
        h, L, B = self.grid(np.arange(L - 2.0, L + 2.01, 0.02),
                            np.arange(B - 50, B + 50.1, 1.0), F)
        h, L, B = self.grid(np.arange(L - 0.06, L + 0.061, 0.003),
                            np.arange(B - 3, B + 3.01, 0.2), F)
        self.L, self.B = L, B
        return h

    def slot_curve(self, k, cands, F):
        m = self.sl == k
        x = self.it[m]
        v = self.v[m]
        T = self.B + self.L * (x[None, :] + cands[:, None])
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
        return (self.hi[I] != v[None, :]).sum(axis=1)


def run(data, F0, rounds=25, wide_first=True, verbose=True):
    F = np.array(F0, float)
    prev = None
    for r in range(rounds):
        tot = sum(c.fit(F, wide=(r == 0 and wide_first)) for c in data)
        n = sum(c.n for c in data)
        if verbose:
            print(f"   r{r}: {tot:.0f}/{n} = {tot/n:.3%} "
                  f"F={[round(float(x), 5) for x in F]}", flush=True)
        if prev is not None and tot >= prev[0]:
            return prev
        prev = (tot, F.copy())
        newF = F.copy()
        for k in range(1, 8):
            lo = max(newF[k - 1] + 0.002, newF[k] - 0.05)
            hi = min(newF[k + 1] - 0.002 if k < 7 else 0.999, newF[k] + 0.05)
            cands = np.arange(lo, hi, 0.0003)
            if len(cands) < 2:
                continue
            acc = np.zeros(len(cands))
            for c in data:
                acc += c.slot_curve(k, cands, newF)
            newF[k] = float(cands[int(np.argmin(acc))])
        if np.max(np.abs(newF - F)) < 1e-7:
            break
        F = newF
    return prev


def main():
    meta, caps = load_dataset()
    data = [Cap(c) for c in caps if c["rep"] == 0]
    inits = {
        "F5": [0.0, 0.1, 0.2, 0.2804, 0.4, 0.51, 0.65, 0.7748],
        "doc40": [0, .1, .2, .3, .4, .5, .65, .775],
        "c3": [0, 4 / 40, 9 / 40, 13 / 40, 18 / 40, 22 / 40, 28 / 40, 33 / 40],
        "F5b": [0.0, 0.095, 0.195, 0.275, 0.395, 0.505, 0.645, 0.77],
        "F5c": [0.0, 0.105, 0.205, 0.29, 0.41, 0.52, 0.66, 0.785],
    }
    best = None
    for name, F0 in inits.items():
        print("init", name, flush=True)
        tot, F = run(data, F0)
        n = sum(c.n for c in data)
        print(f"  -> {name}: {tot:.0f}/{n} = {tot/n:.3%} "
              f"F={[round(float(x), 5) for x in F]}", flush=True)
        if best is None or tot < best[0]:
            best = (tot, [float(x) for x in F], name)
    print("BEST", best, flush=True)
    Path(__file__).with_name("F9.json").write_text(json.dumps(best[1]))


if __name__ == "__main__":
    main()
