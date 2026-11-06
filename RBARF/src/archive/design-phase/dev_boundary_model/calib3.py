"""Fast discrete sweep over inter-sample gap vectors (fully vectorized)."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import linearize, load_dataset  # noqa: E402

BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
END = NB * BIT
GLO, GHI = -6000, 246000


def frame_bits(h):
    fb = bytes.fromhex(h)
    return np.array([(b >> (7 - k)) & 1 for b in fb for k in range(8)])


def dt(mask):
    n = len(mask)
    idx = np.flatnonzero(mask)
    pos = np.arange(n)
    j = np.searchsorted(idx, pos)
    jl = np.clip(j - 1, 0, len(idx) - 1)
    jr = np.clip(j, 0, len(idx) - 1)
    return np.minimum(np.abs(pos - idx[jl]), np.abs(pos - idx[jr])).astype(np.float64)


class Cap:
    def __init__(self, cap, max_it=112):
        s = [x for x in linearize(cap["capture"]) if x[0] <= max_it]
        self.it = np.array([x[0] for x in s], dtype=float)
        self.sl = np.array([x[1] for x in s], dtype=int)
        self.v = np.array([x[2] for x in s], dtype=int)
        bits = frame_bits(cap["frame"])
        th = np.where(bits == 1, T1H, T0H)
        g = np.arange(GLO, GHI)
        hi = np.zeros(len(g), dtype=bool)
        for i in range(NB):
            a = int(i * BIT) - GLO
            hi[a:a + int(th[i])] = True
        self.hi = hi
        self.d1, self.d0 = dt(hi), dt(~hi)
        self.pattern, self.rep = cap["pattern"], cap["rep"]
        allsam = linearize(cap["capture"])
        h = [k for k, x in enumerate(allsam) if x[2] == 1]
        self.last_hi = allsam[h[-1]]
        self.n = len(self.v)

    def grid(self, Ls, Bs, farr, hard):
        x = self.it + farr[self.sl]
        LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
        LL, BB = LL.ravel(), BB.ravel()
        T = BB[:, None] + LL[:, None] * x[None, :]
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
        if hard:
            pred = self.hi[I]
            score = (pred != (self.v[None, :] == 1)).sum(axis=1).astype(float)
        else:
            D = np.where(self.v[None, :] == 1, self.d1[I], self.d0[I])
            score = np.minimum(D, 600.0).sum(axis=1)
        k = int(np.argmin(score))
        return float(score[k]), float(LL[k]), float(BB[k])

    def fit(self, farr):
        _, L, B = self.grid(np.arange(2478, 2542, 0.5),
                            np.arange(-260, 420, 20.0), farr, False)
        h, L, B = self.grid(np.arange(L - 1.2, L + 1.21, 0.02),
                            np.arange(B - 30, B + 30.1, 1.0), farr, True)
        h, L, B = self.grid(np.arange(L - 0.1, L + 0.101, 0.005),
                            np.arange(B - 3, B + 3.01, 0.25), farr, True)
        return h, L, B


def farr_from_gaps(gaps):
    tot = float(sum(gaps))
    cum = [0.0]
    for g in gaps[:7]:
        cum.append(cum[-1] + g)
    return np.array([c / tot for c in cum])


def main():
    meta, caps = load_dataset()
    base = [4, 4, 4, 4, 4, 6, 5, 6]
    pick = ["ones", "zeros", "aa", "rnd1", "count", "dense"]
    sub = [Cap(c) for c in caps
           if c["pattern"] in pick and c["rep"] == 0]
    print("subset:", [c.pattern for c in sub], flush=True)
    res = []
    for extra in (2, 3, 4):
        for combo in itertools.combinations_with_replacement(range(8), extra):
            add = [0] * 8
            for i in combo:
                add[i] += 1
            gaps = [b + a for b, a in zip(base, add)]
            farr = farr_from_gaps(gaps)
            bad = sum(c.fit(farr)[0] for c in sub)
            n = sum(c.n for c in sub)
            res.append((bad / n, tuple(gaps), bad, n))
        print(f"extra={extra} done, best so far {min(res)[0]:.4%} {min(res)[1]}",
              flush=True)
    res.sort()
    for r in res[:25]:
        print(f"  {r[0]:.4%}  gaps={r[1]}")
    Path(__file__).with_name("disc.json").write_text(
        json.dumps([[r[0], list(r[1])] for r in res[:60]]))


if __name__ == "__main__":
    main()
