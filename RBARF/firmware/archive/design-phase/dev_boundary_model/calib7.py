"""Is the loop period data-dependent?

Model: S_{it+1} = S_it + L + cyc * sum_k a_k * v(it,k), a_k in {0,1}.
Exhaustively try all 256 masks; for each, fit (L, B) per capture against
the known frame and report total sample mismatch.
"""
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


class Cap:
    def __init__(self, cap):
        s = [x for x in linearize(cap["capture"]) if x[0] <= MAXIT]
        self.it = np.array([x[0] for x in s])
        self.sl = np.array([x[1] for x in s])
        self.v = np.array([x[2] for x in s]) == 1
        lv = np.zeros((MAXIT + 1, 8), dtype=float)
        for it, sl, v in s:
            lv[it, sl] = v
        self.lv = lv
        bits = bm._bits(bytes.fromhex(cap["frame"]))
        hi = np.zeros(GHI - GLO, dtype=bool)
        for i, b in enumerate(bits):
            a = int(i * BIT) - GLO
            hi[a:a + int(T1H if b else T0H)] = True
        self.hi = hi
        self.pattern = cap["pattern"]
        self.n = len(self.v)
        self.F = np.array(bm.F)

    def fit(self, mask):
        extra = self.lv @ np.array(mask, dtype=float)     # cycles added after loop it
        K = np.concatenate([[0.0], np.cumsum(extra)[:-1]])  # cycles before loop it
        Kk = K[self.it]
        best = None
        for Ls, Bs in ((np.arange(2440, 2546, 0.4), np.arange(-500, 800, 20.0)),):
            LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
            LL, BB = LL.ravel(), BB.ravel()
            step = max(1, int(8e6 // self.n))
            for a in range(0, len(LL), step):
                b = min(a + step, len(LL))
                cyc = LL[a:b] / 40.0
                T = (BB[a:b, None] + LL[a:b, None] * self.it[None, :]
                     + cyc[:, None] * Kk[None, :]
                     + cyc[:, None] * 40.0 * self.F[self.sl][None, :])
                I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
                sc = (self.hi[I] != self.v[None, :]).sum(axis=1)
                k = int(np.argmin(sc))
                if best is None or sc[k] < best[0]:
                    best = (int(sc[k]), float(LL[a + k]), float(BB[a + k]))
        # local refine
        bad, L, B = best
        for sL, sB in ((0.1, 5.0), (0.03, 1.0)):
            Ls = np.arange(L - 20 * sL, L + 20 * sL, sL)
            Bs = np.arange(B - 20 * sB, B + 20 * sB, sB)
            LL, BB = np.meshgrid(Ls, Bs, indexing="ij")
            LL, BB = LL.ravel(), BB.ravel()
            cyc = LL / 40.0
            T = (BB[:, None] + LL[:, None] * self.it[None, :]
                 + cyc[:, None] * Kk[None, :]
                 + cyc[:, None] * 40.0 * self.F[self.sl][None, :])
            I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
            sc = (self.hi[I] != self.v[None, :]).sum(axis=1)
            k = int(np.argmin(sc))
            if sc[k] < bad:
                bad, L, B = int(sc[k]), float(LL[k]), float(BB[k])
        return bad, L, B


def main():
    meta, caps = load_dataset()
    pick = ["zeros", "ones", "count", "sparse", "rnd1", "p55", "edges", "dense"]
    data = [Cap(c) for c in caps if c["rep"] == 0 and c["pattern"] in pick]
    n = sum(c.n for c in data)
    res = []
    for m in range(256):
        mask = [(m >> k) & 1 for k in range(8)]
        bad = sum(c.fit(mask)[0] for c in data)
        res.append((bad, mask))
        if m % 32 == 0:
            print(f"  ...{m} best {min(res)[0]}/{n} {min(res)[1]}", flush=True)
    res.sort()
    for bad, mask in res[:15]:
        print(f"  {bad}/{n} = {bad/n:.3%}  mask={mask}")


if __name__ == "__main__":
    main()
