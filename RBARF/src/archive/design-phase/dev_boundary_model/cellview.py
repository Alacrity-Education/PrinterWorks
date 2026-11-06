"""Per-cell view: decoder timebase vs ground-truth timebase."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa
from viterbi_S import build, viterbi  # noqa

meta, caps = load_dataset()
pat = sys.argv[1]
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 0
j0 = int(sys.argv[3]) if len(sys.argv) > 3 else 30
j1 = int(sys.argv[4]) if len(sys.argv) > 4 else 56
c = [x for x in caps if x["pattern"] == pat and x["rep"] == rep][0]
s = linearize(c["capture"])
th = bm._thresholds(bytes.fromhex(meta["header"]), bytes.fromhex(meta["trailer"]))
exp = bm._bits(bytes.fromhex(c["frame"]))

cands = bm._seed_candidates(s, th)
print("seed candidates:", [(sc, round(L, 2), round(B, 1)) for sc, L, B in cands])
best = None
for sc, L, B in cands:
    res, cost, L2, B2 = bm._track(s, L, B, th)
    print(f"  seed L={L:.2f} -> cost {cost:.2f} L2={L2:.2f} B2={B2:.1f}")
    if best is None or cost < best[0]:
        best = (cost, res, L2, B2)
cost, (loops, S), L, B = best
print(f"chosen L={L:.2f} B={B:.1f} cost={cost:.2f}")

# ground-truth trajectory
sl, vv, hi = build(c)
gbest = None
for L0 in np.arange(2488, 2518, 0.5):
    ev, bad = viterbi(sl, vv, hi, bm.F, L0)
    if gbest is None or bad < gbest[1]:
        gbest = (ev, bad, L0)
ev, gbad, L0 = gbest
Sg = [L0 * i + ev[i] for i in range(len(ev))]
print(f"ground-truth track L0={L0} bad={gbad}")
dec = {it: S[k] for k, it in enumerate(loops)}
print("loop | S_dec   S_gt   diff")
for i in range(0, min(40, len(Sg))):
    d = dec.get(i)
    print(f"  {i:3d} {d:9.1f} {Sg[i]:9.1f} {(d - Sg[i]) if d else 0:+8.1f}")

cells = bm._cells_from(s, loops, S, L)
print("\ncell exp dec  samples(phase,level)")
for j in range(j0, j1):
    ph = cells.get(j, [])
    b = bm._classify(ph)
    tag = "  " if b == exp[j] else "<<"
    print(f" {j:4d}  {exp[j]}  {b}  {tag} " +
          " ".join(f"{int(p):4d}/{v}" for p, v in ph))
