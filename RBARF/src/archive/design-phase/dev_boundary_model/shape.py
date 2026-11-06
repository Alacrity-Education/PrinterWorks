"""Shape of the true per-loop start trajectory: how smooth is it?"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import load_dataset  # noqa
import boundary_model as bm  # noqa
from viterbi_S import build, viterbi  # noqa


def main():
    meta, caps = load_dataset()
    F = bm.F
    for cap in caps:
        if cap["rep"] != 0:
            continue
        sl, vv, hi = build(cap)
        best = None
        for L0 in np.arange(2490, 2517, 0.5):
            ev, bad = viterbi(sl, vv, hi, F, L0, lam=1.0, badw=120.0, half=2200.0)
            if best is None or bad < best[1]:
                best = (ev, bad, L0)
        ev, bad, L0 = best
        n = len(ev)
        it = np.arange(n)
        S = L0 * it + ev
        msg = []
        for deg in (1, 2, 3, 5, 8):
            c = np.polyfit(it, S, deg)
            r = S - np.polyval(c, it)
            msg.append(f"deg{deg}: rms {r.std():6.1f} max {np.abs(r).max():6.1f}")
        print(f"{cap['pattern']:11s} bad={bad:2d} L0={L0:.1f}  " + "  ".join(msg))


if __name__ == "__main__":
    main()
