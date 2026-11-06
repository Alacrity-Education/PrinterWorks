"""Unconstrained per-slot phase search on a LINEAR time base.

Allows F[k] anywhere in [-1.2, 2.2] loops, i.e. lets a slot belong to a
different iteration than harness.linearize assumes.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from calib9 import Cap  # noqa
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness import load_dataset  # noqa


def run(data, F0, rounds=30, lo=-1.2, hi=2.2, verbose=True):
    F = np.array(F0, float)
    prev = None
    for r in range(rounds):
        tot = sum(c.fit(F, wide=(r == 0)) for c in data)
        n = sum(c.n for c in data)
        if verbose:
            print(f"   r{r}: {tot:.0f}/{n} = {tot/n:.3%} "
                  f"F={[round(float(x), 4) for x in F]}", flush=True)
        if prev is not None and tot >= prev[0]:
            return prev
        prev = (tot, F.copy())
        newF = F.copy()
        for k in range(8):
            if r < 2:
                cands = np.arange(lo, hi, 0.002)
            else:
                cands = np.arange(newF[k] - 0.04, newF[k] + 0.04, 0.0003)
            acc = np.zeros(len(cands))
            for c in data:
                acc += c.slot_curve(k, cands, newF)
            newF[k] = float(cands[int(np.argmin(acc))])
        newF = newF - newF[0]
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
        "shift67": [0, .1, .2, .3, .4, .5, 1.65, 1.775],
        "flat": [0, .12, .25, .37, .5, .62, .75, .87],
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
    Path(__file__).with_name("F10.json").write_text(json.dumps(best[1]))


if __name__ == "__main__":
    main()
