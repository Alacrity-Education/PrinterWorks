"""Compare the DP's chosen trajectory with the ground-truth trajectory
under the decoder's own (payload-agnostic) cost."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa
from viterbi_S import build, viterbi  # noqa


def emission_cost(samples, th, S_by_loop, L):
    """decoder's payload-agnostic mismatch count along a given trajectory"""
    offs = [L * f for f in bm.F]
    bad = 0
    for it, sl, v in samples:
        s = S_by_loop.get(it)
        if s is None:
            continue
        t = s + offs[sl]
        runs = []
        bm._cost_runs(t, t + 1e-6, v, th, runs)
        if runs:
            bad += 1
    return bad


def main():
    meta, caps = load_dataset()
    th0 = bm._thresholds(bytes.fromhex(meta["header"]),
                         bytes.fromhex(meta["trailer"]))
    for pat in sys.argv[1:] or ["count", "zeros", "sparse", "p55", "edges", "lone1"]:
        cap = [c for c in caps if c["pattern"] == pat and c["rep"] == 0][0]
        s = linearize(cap["capture"])
        # decoder trajectory
        cands = bm._seed_candidates(s, th0)
        best = None
        for _sc, L, B in cands:
            res, cost, L2, B2 = bm._track(s, L, B, th0)
            if res is None:
                continue
            if best is None or cost < best[0]:
                best = (cost, res, L2)
        cost, (loops, S), L = best
        dec = {it: S[k] for k, it in enumerate(loops)}
        # ground-truth trajectory
        sl, vv, hi = build(cap)
        g = None
        for L0 in np.arange(2488, 2518, 0.5):
            ev, bad = viterbi(sl, vv, hi, bm.F, L0, lam=1.0, badw=120.0, half=2200.0)
            if g is None or bad < g[1]:
                g = (ev, bad, L0)
        ev, gbad, L0 = g
        gt = {i: L0 * i + ev[i] for i in range(len(ev))}
        for it in loops:
            if it not in gt:
                gt[it] = gt[max(gt)] + L0 * (it - max(gt))

        def tv(d):
            xs = [d[it] for it in loops]
            base = np.polyfit(loops, xs, 1)
            e = [xs[i] - np.polyval(base, loops[i]) for i in range(len(xs))]
            return sum(abs(e[i + 1] - e[i]) for i in range(len(e) - 1))

        bd = emission_cost(s, th0, dec, L)
        bg = emission_cost(s, th0, gt, L0)
        print(f"{pat:11s} decoder: bad={bd:3d} TV={tv(dec):8.0f}  "
              f"cost={bd + tv(dec) * bm.LAMBDA:8.2f}   |   "
              f"truth: bad={bg:3d} TV={tv(gt):8.0f}  "
              f"cost={bg + tv(gt) * bm.LAMBDA:8.2f}")


if __name__ == "__main__":
    main()
