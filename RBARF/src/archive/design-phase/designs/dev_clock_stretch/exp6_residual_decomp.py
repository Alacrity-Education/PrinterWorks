"""Decompose rising-edge timing residuals into
   (a) per-slot-pair systematic bias  (calibration's job)
   (b) slow within-capture phase wander (the tracker's job)
   (c) bracket noise.

For every observed 0->1 transition we know (ground truth, analysis only)
the bit index k, hence the exact edge time k*1250 ns.  Fit a global
two-parameter clock model t = phi + u*L per capture, then look at what
is left.
"""
import numpy as np
from common import load_all, BIT_NS

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
NB = 192


def rise_events(cap, a):
    lev = cap["lev"]
    d = np.diff(lev.astype(int))
    idx = np.nonzero(d > 0)[0]
    u = cap["it"] + a[cap["slot"]]
    s0 = cap["slot"][idx]
    return idx, u[idx], u[idx + 1], s0


def fit_capture(cap, a, bias=None, L0=2497.0, phi0=0.0, iters=8):
    idx, u0, u1, s0 = rise_events(cap, a)
    umid = 0.5 * (u0 + u1)
    b = np.zeros(len(umid)) if bias is None else bias[s0]
    L, phi = L0, phi0
    kk = None
    for _ in range(iters):
        t = phi + umid * L + b
        k = np.round(t / BIT_NS)
        k = np.clip(k, 0, NB - 1)
        tgt = k * BIT_NS
        err = np.abs(tgt - t)
        keep = err < 0.45 * BIT_NS
        X = np.vstack([np.ones(keep.sum()), umid[keep]]).T
        sol, *_ = np.linalg.lstsq(X, (tgt - b)[keep], rcond=None)
        phi, L = sol
        kk = k
    t = phi + umid * L + b
    return dict(phi=phi, L=L, umid=umid, s0=s0, res=(kk * BIT_NS - t),
                keep=keep, k=kk, gap=(u1 - u0))


if __name__ == "__main__":
    meta, caps = load_all()
    # --- pass 1: fit each capture, collect residuals by starting slot ---
    bias = np.zeros(8)
    for it in range(4):
        allres = [[] for _ in range(8)]
        fits = []
        for cap in caps:
            f = fit_capture(cap, A, bias)
            fits.append(f)
            for s, r, kp in zip(f["s0"], f["res"], f["keep"]):
                if kp:
                    allres[s].append(r)
        newbias = bias + np.array([np.median(v) if v else 0.0 for v in allres])
        newbias -= newbias.mean()
        print(f"it{it}: slot-pair bias(ns) = {np.round(newbias,1).tolist()}  "
              f"rms_all={np.sqrt(np.mean([r**2 for v in allres for r in v])):.1f}")
        bias = newbias

    print("\nper-capture after removing global slot-pair bias:")
    print(f"{'pattern':11s} {'rep':>3s} {'L':>8s} {'phi':>7s} {'n':>4s} "
          f"{'rms':>6s} {'lin_ns':>7s} {'quad_ns':>8s} {'rms_detr':>8s}")
    lin_all, rms_all, rmsd_all = [], [], []
    for cap, f in zip(caps, fits):
        m = f["keep"]
        u, r = f["umid"][m], f["res"][m]
        un = (u - u.mean()) / (u.max() - u.min())
        V = np.vstack([np.ones(len(un)), un, un**2]).T
        c, *_ = np.linalg.lstsq(V, r, rcond=None)
        detr = r - V @ c
        rms = np.sqrt((r**2).mean()); rmsd = np.sqrt((detr**2).mean())
        lin_all.append(c[1]); rms_all.append(rms); rmsd_all.append(rmsd)
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {f['L']:8.2f} "
              f"{f['phi']:7.1f} {m.sum():4d} {rms:6.1f} {c[1]:+7.1f} "
              f"{c[2]:+8.1f} {rmsd:8.1f}")
    lin_all = np.array(lin_all)
    print(f"\nlinear term across capture (ns end-to-end): "
          f"mean={lin_all.mean():+.1f} std={lin_all.std():.1f} "
          f"max|.|={np.abs(lin_all).max():.1f}")
    print(f"  -> equivalent residual rate error: "
          f"{np.abs(lin_all).max()/240000*100:.4f}% of clock")
    print(f"rms before detrend={np.mean(rms_all):.1f}  after={np.mean(rmsd_all):.1f}")
