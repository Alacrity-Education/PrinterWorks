"""Viterbi over per-loop start times (ground truth) to recover the true
S trajectory and measure how much real loop-period wander there is."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa

BIT, T0H, T1H = 1250.0, 350.0, 700.0
GLO, GHI = -12000, 330000
NLOOP = 96
F5 = [0.0, 0.1, 0.2, 0.2804, 0.4, 0.51, 0.65, 0.7748]


def build(cap):
    s = [x for x in linearize(cap["capture"]) if x[0] < NLOOP]
    sl = [[] for _ in range(NLOOP)]
    vv = [[] for _ in range(NLOOP)]
    for it, k, v in s:
        sl[it].append(k)
        vv[it].append(v)
    bits = bm._bits(bytes.fromhex(cap["frame"]))
    hi = np.zeros(GHI - GLO, dtype=bool)
    for i, b in enumerate(bits):
        a = int(i * BIT) - GLO
        hi[a:a + int(T1H if b else T0H)] = True
    return [np.array(a) for a in sl], [np.array(a) == 1 for a in vv], hi


def viterbi(sl, vv, hi, F, L0, lam=1.0, badw=60.0, half=1800.0, step=5.0):
    Fa = np.array(F) * L0
    e = np.arange(-half, half + 1e-9, step)
    ne = len(e)
    # emission cost
    em = np.empty((NLOOP, ne))
    for i in range(NLOOP):
        cand = i * L0 + e
        T = cand[:, None] + Fa[sl[i]][None, :]
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(hi) - 1)
        em[i] = (hi[I] != vv[i][None, :]).sum(axis=1) * badw
    trans = lam * np.abs(e[:, None] - e[None, :])
    dp = em[0].copy()
    ptr = np.zeros((NLOOP, ne), dtype=np.int32)
    for i in range(1, NLOOP):
        tot = dp[:, None] + trans
        j = np.argmin(tot, axis=0)
        dp = tot[j, np.arange(ne)] + em[i]
        ptr[i] = j
    k = int(np.argmin(dp))
    path = np.empty(NLOOP, dtype=int)
    path[-1] = k
    for i in range(NLOOP - 1, 0, -1):
        path[i - 1] = ptr[i][path[i]]
    ev = e[path]
    bad = sum(int(em[i][path[i]] / badw) for i in range(NLOOP))
    return ev, bad


def main():
    meta, caps = load_dataset()
    F = F5
    for cap in caps:
        if cap["rep"] != 0:
            continue
        sl, vv, hi = build(cap)
        best = None
        for L0 in np.arange(2488, 2516, 1.0):
            ev, bad = viterbi(sl, vv, hi, F, L0)
            rng = ev.max() - ev.min()
            if best is None or (bad, rng) < (best[1], best[3]):
                best = (ev, bad, L0, rng)
        ev, bad, L0, rng = best
        d = np.diff(ev) + L0
        print(f"{cap['pattern']:11s} L0={L0:.0f} bad={bad:3d} "
              f"e range {ev.min():+7.0f}..{ev.max():+7.0f} (span {rng:5.0f})  "
              f"period mean {d.mean():7.1f} std {d.std():5.1f} min {d.min():6.0f} max {d.max():6.0f}")
        if cap["pattern"] in ("rnd1", "zeros", "count"):
            print("   e:", " ".join(f"{x:+.0f}" for x in ev))


if __name__ == "__main__":
    main()
