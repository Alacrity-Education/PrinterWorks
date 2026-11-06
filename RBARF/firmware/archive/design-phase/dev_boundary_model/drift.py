"""Recover per-loop start times (feasible intervals + smoothing) and look
for what drives the loop-to-loop period variation."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import linearize, load_dataset  # noqa
import boundary_model as bm  # noqa
from diag import fit_full  # noqa

BIT, T0H, T1H = 1250.0, 350.0, 700.0
GLO, GHI = -9000, 320000


def loop_intervals(s, bits, L, B, F, nloops=96, span=1400.0):
    hi = np.zeros(GHI - GLO, dtype=bool)
    for i, b in enumerate(bits):
        a = int(i * BIT) - GLO
        hi[a:a + int(T1H if b else T0H)] = True
    Fa = np.array(F)
    byit = {}
    for it, sl, v in s:
        if it < nloops:
            byit.setdefault(it, []).append((sl, v))
    out = []
    for it in sorted(byit):
        sl = np.array([x[0] for x in byit[it]])
        vv = np.array([x[1] for x in byit[it]]) == 1
        base = B + L * it
        cand = np.arange(base - span, base + span, 1.0)
        T = cand[:, None] + L * Fa[sl][None, :]
        I = np.clip(np.rint(T).astype(np.int64) - GLO, 0, len(hi) - 1)
        bad = (hi[I] != vv[None, :]).sum(axis=1)
        mn = bad.min()
        ok = np.flatnonzero(bad == mn)
        # split into contiguous runs, keep the run nearest the prediction
        runs = np.split(ok, np.flatnonzero(np.diff(ok) > 1) + 1)
        best = min(runs, key=lambda r: abs(cand[r].mean() - base))
        out.append((it, float(cand[best[0]]), float(cand[best[-1]]), int(mn),
                    int(vv.sum())))
    return out


def main():
    meta, caps = load_dataset()
    pat, rep = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0
    c = [x for x in caps if x["pattern"] == pat and x["rep"] == rep][0]
    s = linearize(c["capture"])
    frame = bytes.fromhex(c["frame"])
    bits = bm._bits(frame)
    L, B, sc, nx = fit_full(s, frame)
    print(f"{pat} r{rep} L={L:.2f} B={B:.1f} score={sc}/{nx}")
    iv = loop_intervals(s, bits, L, B, bm.F)
    # smooth pick inside intervals
    S = np.array([min(max(B + L * it, lo), hi) for it, lo, hi, _, _ in iv])
    lo = np.array([x[1] for x in iv])
    hi2 = np.array([x[2] for x in iv])
    for _ in range(4000):
        Sn = S.copy()
        Sn[1:-1] = 0.5 * (S[:-2] + S[2:])
        S = np.clip(Sn, lo, hi2)
    d = np.diff(S)
    print("interval widths: median %.0f  max %.0f" % (np.median(hi2 - lo), (hi2 - lo).max()))
    print("delta: mean %.2f  std %.2f  min %.1f max %.1f" % (d.mean(), d.std(), d.min(), d.max()))
    nh = np.array([x[4] for x in iv])
    print("bad total", sum(x[3] for x in iv))
    for k in range(len(iv)):
        dd = d[k] if k < len(d) else float("nan")
        print(f"  it{iv[k][0]:3d} S={S[k]:9.1f} (lo{lo[k]:9.1f} hi{hi2[k]:9.1f}) "
              f"d={dd:8.2f}  nhigh={nh[k]} bad={iv[k][3]}")


if __name__ == "__main__":
    main()
