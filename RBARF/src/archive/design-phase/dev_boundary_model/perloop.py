"""Per-iteration free loop-start fit (ground truth) - drift diagnostic."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa
from diag import fit_full  # noqa

BIT, T0H, T1H, NB = 1250.0, 350.0, 700.0, 192
END = NB * BIT
GLO, GHI = -9000, 320000

meta, caps = load_dataset()
F = [float(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else [])] or bm.F
pat, rep = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0
c = [x for x in caps if x["pattern"] == pat and x["rep"] == rep][0]
s = [x for x in linearize(c["capture"]) if x[0] <= 96]
bits = bm._bits(bytes.fromhex(c["frame"]))
hi = np.zeros(GHI - GLO, dtype=bool)
for i, b in enumerate(bits):
    a = int(i * BIT) - GLO
    hi[a:a + int(T1H if b else T0H)] = True

L, B, sc, nx = fit_full(linearize(c["capture"]), bytes.fromhex(c["frame"]), F)
print(f"{pat} r{rep} global L={L:.2f} B={B:.1f} score={sc}/{nx}")

byit = {}
for it, sl, v in s:
    byit.setdefault(it, []).append((sl, v))

Fa = np.array(F)
prev = None
tot_bad = 0
rows = []
for it in sorted(byit):
    sl = np.array([x[0] for x in byit[it]])
    vv = np.array([x[1] for x in byit[it]]) == 1
    pred_S = B + L * it
    cand = np.arange(pred_S - 900, pred_S + 900, 1.0)
    T = cand[:, None] + L * Fa[sl][None, :]
    I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(hi) - 1)
    bad = (hi[I] != vv[None, :]).sum(axis=1)
    k = int(np.argmin(bad))
    # prefer the candidate closest to prediction among the minima
    mins = np.flatnonzero(bad == bad[k])
    k = mins[int(np.argmin(np.abs(cand[mins] - pred_S)))]
    tot_bad += int(bad[k])
    rows.append((it, cand[k] - pred_S, int(bad[k]), len(vv)))
print("resid bad (free per-loop start):", tot_bad, "/", sum(r[3] for r in rows))
for it, dev, bad, n in rows:
    print(f"  it{it:3d} dev {dev:+8.1f}  bad {bad}/{n}")
