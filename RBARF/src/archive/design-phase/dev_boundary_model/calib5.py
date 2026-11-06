"""Joint fit: global slot phases F + free per-loop start times.

If the intra-loop geometry F is right, every loop's 8 samples should be
explainable by *some* loop start time, so the residual with free per-loop
starts measures the quality of F alone (independent of clock drift).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa

BIT, T0H, T1H = 1250.0, 350.0, 700.0
GLO, GHI = -9000, 320000
NLOOP = 96


class Cap:
    def __init__(self, cap):
        s = [x for x in linearize(cap["capture"]) if x[0] < NLOOP]
        self.sl = [[] for _ in range(NLOOP)]
        self.vv = [[] for _ in range(NLOOP)]
        for it, k, v in s:
            self.sl[it].append(k)
            self.vv[it].append(v)
        self.sl = [np.array(a) for a in self.sl]
        self.vv = [np.array(a) == 1 for a in self.vv]
        bits = bm._bits(bytes.fromhex(cap["frame"]))
        hi = np.zeros(GHI - GLO, dtype=bool)
        for i, b in enumerate(bits):
            a = int(i * BIT) - GLO
            hi[a:a + int(T1H if b else T0H)] = True
        self.hi = hi
        self.pattern = cap["pattern"]
        self.L = 2497.0
        self.S = np.arange(NLOOP) * self.L + 150.0
        self.n = sum(len(a) for a in self.vv)

    def fit_S(self, F, span=1500.0):
        Fa = np.array(F) * self.L
        # robust linear prediction from the current S
        it = np.arange(NLOOP)
        A = np.polyfit(it, self.S, 1)
        pred = np.polyval(A, it)
        tot = 0
        newS = np.empty(NLOOP)
        for i in range(NLOOP):
            cand = np.arange(pred[i] - span, pred[i] + span, 1.0)
            T = cand[:, None] + Fa[self.sl[i]][None, :]
            I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
            bad = (self.hi[I] != self.vv[i][None, :]).sum(axis=1)
            mn = bad.min()
            ok = np.flatnonzero(bad == mn)
            j = ok[int(np.argmin(np.abs(cand[ok] - pred[i])))]
            newS[i] = cand[j]
            tot += int(mn)
        self.S = newS
        return tot

    def slot_curve(self, k, cands):
        """bad per candidate F[k] (fraction of loop) with S fixed."""
        c = cands * self.L
        rows = []
        for i in range(NLOOP):
            m = self.sl[i] == k
            if not m.any():
                continue
            rows.append((self.S[i], self.vv[i][m][0]))
        if not rows:
            return np.zeros(len(cands), dtype=np.int64)
        S = np.array([r[0] for r in rows])
        v = np.array([r[1] for r in rows])
        T = S[None, :] + c[:, None]
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(self.hi) - 1)
        return (self.hi[I] != v[None, :]).sum(axis=1)


def run(data, F0, rounds=12, verbose=True):
    F = np.array(F0, dtype=float)
    prev = None
    for r in range(rounds):
        tot = sum(c.fit_S(F) for c in data)
        n = sum(c.n for c in data)
        if verbose:
            print(f"   r{r}: bad {tot}/{n} = {tot/n:.3%} "
                  f"F={[round(float(x), 5) for x in F]}", flush=True)
        if prev is not None and tot >= prev[0]:
            return prev
        prev = (tot, F.copy())
        newF = F.copy()
        for k in range(1, 8):
            lo = newF[k - 1] + 0.002
            hi = (newF[k + 1] - 0.002) if k < 7 else 0.999
            cands = np.arange(lo, hi, 0.0004)
            if len(cands) < 2:
                continue
            acc = np.zeros(len(cands), dtype=np.int64)
            for c in data:
                acc += c.slot_curve(k, cands)
            newF[k] = float(cands[int(np.argmin(acc))])
        if np.max(np.abs(newF - F)) < 1e-6:
            break
        F = newF
    return prev


def main():
    meta, caps = load_dataset()
    data = [Cap(c) for c in caps if c["rep"] == 0]
    print("captures:", len(data), flush=True)
    inits = {
        "doc40": [0, .1, .2, .3, .4, .5, .65, .775],
        "calib3": [0, 4 / 40, 9 / 40, 13 / 40, 18 / 40, 22 / 40, 28 / 40, 33 / 40],
        "doc37": [0, 4 / 37, 8 / 37, 12 / 37, 16 / 37, 20 / 37, 26 / 37, 31 / 37],
        "uniform": [k / 8 for k in range(8)],
        "u2": [0, .11, .22, .33, .44, .55, .69, .83],
    }
    best = None
    for name, F0 in inits.items():
        print("init", name, flush=True)
        tot, F = run(data, F0)
        n = sum(c.n for c in data)
        print(f"  -> {name}: {tot}/{n} = {tot/n:.3%} "
              f"F={[round(float(x), 5) for x in F]}", flush=True)
        print("     cycles(x40):", [round(float(x) * 40, 2) for x in F], flush=True)
        if best is None or tot < best[0]:
            best = (tot, [float(x) for x in F], name)
    print("BEST", best, flush=True)
    Path(__file__).with_name("F5.json").write_text(json.dumps(best[1]))


if __name__ == "__main__":
    main()
