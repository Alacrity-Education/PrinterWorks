"""Oracle per-capture clock scale: fit t = phi + c*C using ground-truth edges.

Gives (a) the true spread of the receiver cycle duration across the 54
captures, (b) the residual of a pure linear (constant-rate) clock model,
which bounds how much within-capture wander there is.
"""
import numpy as np
from common import load_all, true_edges, transitions, BIT_NS

C0 = 2507.3 / 40.0


def fit_capture(cap, C0=C0, phi0=0.0, iters=6, trim=1.0):
    cyc, lev = cap["cyc"], cap["lev"]
    idx, kind = transitions(lev)
    cmid = 0.5 * (cyc[idx] + cyc[idx + 1])
    gap = cyc[idx + 1] - cyc[idx]
    rt, ft = true_edges(cap["bits"])
    C, phi = C0, phi0
    for _ in range(iters):
        t = phi + cmid * C
        tgt = np.empty_like(t)
        err = np.empty_like(t)
        for j, (tt, k) in enumerate(zip(t, kind)):
            ref = rt if k > 0 else ft
            m = np.argmin(np.abs(ref - tt))
            tgt[j] = ref[m]
            err[j] = abs(ref[m] - tt)
        keep = err < trim * BIT_NS / 2
        A = np.vstack([np.ones(keep.sum()), cmid[keep]]).T
        sol, *_ = np.linalg.lstsq(A, tgt[keep], rcond=None)
        phi, C = sol
    t = phi + cmid * C
    res = tgt - t
    return dict(phi=phi, C=C, n=len(idx), nkeep=int(keep.sum()),
                res=res[keep], cmid=cmid[keep], gap=gap[keep],
                kind=kind[keep], tgt=tgt[keep])


if __name__ == "__main__":
    meta, caps = load_all()
    Cs = []
    print(f"{'pattern':11s} {'rep':>3s} {'C(ns/cy)':>9s} {'loop_ns':>9s} "
          f"{'eps%':>7s} {'phi':>7s} {'nedge':>5s} {'res_rms':>8s} {'res_max':>8s}")
    for cap in caps:
        r = fit_capture(cap)
        Cs.append(r["C"])
        eps = (62.5 / r["C"] - 1) * 100
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {r['C']:9.4f} "
              f"{r['C']*40:9.2f} {eps:7.3f} {r['phi']:7.1f} {r['nkeep']:5d} "
              f"{np.sqrt((r['res']**2).mean()):8.1f} {np.abs(r['res']).max():8.1f}")
    Cs = np.array(Cs)
    print(f"\nC: mean={Cs.mean():.4f} std={Cs.std():.4f} "
          f"min={Cs.min():.4f} max={Cs.max():.4f} "
          f"spread={(Cs.max()/Cs.min()-1)*100:.3f}%")
    print(f"loop_ns: mean={Cs.mean()*40:.2f} min={Cs.min()*40:.2f} max={Cs.max()*40:.2f}")
