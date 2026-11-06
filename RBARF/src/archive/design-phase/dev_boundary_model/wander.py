"""What drives loop-to-loop period variation?

Recover well-constrained per-loop start intervals (ground truth), pick S
inside them with a smoothness prior, then regress the per-loop period on
the 8 sampled levels of the loop.
"""
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
F = [0.0, 0.1, 0.2, 0.2804, 0.4, 0.51, 0.65, 0.7748]


def intervals(cap, F, L=2497.0, span=1600.0):
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
    Fa = np.array(F) * L
    out = []
    pred = 150.0
    for i in range(NLOOP):
        ss = np.array(sl[i])
        v = np.array(vv[i]) == 1
        cand = np.arange(pred - span, pred + span, 1.0)
        T = cand[:, None] + Fa[ss][None, :]
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(hi) - 1)
        bad = (hi[I] != v[None, :]).sum(axis=1)
        mn = bad.min()
        ok = np.flatnonzero(bad == mn)
        runs = np.split(ok, np.flatnonzero(np.diff(ok) > 1) + 1)
        r = min(runs, key=lambda rr: abs(cand[rr].mean() - pred))
        lo, hiv = float(cand[r[0]]), float(cand[r[-1]])
        out.append((lo, hiv, int(mn), v.astype(int).tolist()))
        pred = 0.5 * (lo + hiv) + L
    return out


def smooth_pick(iv, L=2497.0):
    lo = np.array([x[0] for x in iv])
    hi = np.array([x[1] for x in iv])
    S = np.clip(np.arange(len(iv)) * L + 150.0, lo, hi)
    for _ in range(20000):
        Sn = S.copy()
        Sn[1:-1] = 0.5 * (S[:-2] + S[2:])
        Sn[0] = S[1] - L
        Sn[-1] = S[-2] + L
        S = np.clip(Sn, lo, hi)
    return S


def main():
    meta, caps = load_dataset()
    rows = []
    for cap in caps:
        if cap["rep"] != 0:
            continue
        iv = intervals(cap, F)
        S = smooth_pick(iv)
        d = np.diff(S)
        lv = np.array([x[3] for x in iv])
        badtot = sum(x[2] for x in iv)
        print(f"{cap['pattern']:11s} bad={badtot:3d} width med={np.median([x[1]-x[0] for x in iv]):5.0f} "
              f"d mean={d.mean():8.2f} std={d.std():6.2f} min={d.min():8.1f} max={d.max():8.1f}")
        for i in range(len(d)):
            rows.append((d[i], lv[i], lv[i + 1] if i + 1 < len(lv) else lv[i]))
    D = np.array([r[0] for r in rows])
    V = np.array([r[1] for r in rows])
    V2 = np.array([r[2] for r in rows])
    keep = np.abs(D - np.median(D)) < 200
    D, V, V2 = D[keep], V[keep], V2[keep]
    print("\nn =", len(D), " mean d =", D.mean().round(2), " std =", D.std().round(2))
    print("corr(d, level_k) for this loop:")
    for k in range(8):
        print(f"   slot{k}: corr={np.corrcoef(D, V[:, k])[0,1]:+.3f}  "
              f"mean d|v=0 {D[V[:,k]==0].mean():8.2f}  mean d|v=1 {D[V[:,k]==1].mean():8.2f}")
    print("corr(d, nhigh) =", np.corrcoef(D, V.sum(axis=1))[0, 1].round(3))
    print("corr with next loop levels:")
    for k in range(8):
        print(f"   slot{k}: corr={np.corrcoef(D, V2[:, k])[0,1]:+.3f}")
    A = np.column_stack([np.ones(len(D)), V])
    coef, *_ = np.linalg.lstsq(A, D, rcond=None)
    print("lstsq coefs (ns):", coef.round(2))
    print("in cycles (/62.4):", (coef / 62.4).round(3))


if __name__ == "__main__":
    main()
