"""Calibration-free variant.

Acquisition statistic that is invariant to any per-slot-pair timing
offset (i.e. needs no slot calibration at all):

    Jg(L) = (1/W) * SUM_over_slotpair_s | SUM_{j in s} w_j e^{2 pi i u_j L / T} |

Each slot-pair group is summed coherently (its unknown offset is a common
phase inside the group, so |.| removes it); groups are then combined
incoherently.

Refinement: joint least squares for (phi, L, b_0..b_7) with sum(b)=0,
where b_s is the per-slot-pair timing offset -- 10 parameters against
~180 rising edges.
"""
import sys
import numpy as np
from common import load_all, REC, BIT_NS
sys.path.insert(0, str(REC))
from synth import synth_capture                       # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                         # noqa: E402
from exp9_envelope import pack, truth_L

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
NB = 192


def rise(cap, a=A):
    d = np.diff(cap["lev"].astype(int))
    idx = np.nonzero(d > 0)[0]
    u = cap["it"] + a[cap["slot"]]
    return .5 * (u[idx] + u[idx + 1]), (u[idx + 1] - u[idx]), cap["slot"][idx]


def Jg(cap, Ls):
    umid, g, s0 = rise(cap)
    out = np.empty(len(Ls))
    for k, L in enumerate(Ls):
        w = np.sinc(g * L / BIT_NS)
        z = w * np.exp(2j * np.pi * umid * L / BIT_NS)
        tot = 0.0
        for s in range(8):
            m = s0 == s
            if m.any():
                tot += abs(z[m].sum())
        out[k] = tot / np.abs(w).sum()
    return out


def refine_joint(cap, L0, iters=30):
    umid, g, s0 = rise(cap)
    n = len(umid)
    D = np.zeros((n, 8))
    D[np.arange(n), s0] = 1.0
    L, phi, b = L0, 0.0, np.zeros(8)
    for _ in range(iters):
        t = phi + umid * L + b[s0]
        k = np.round(t / BIT_NS)
        keep = np.abs(k * BIT_NS - t) < 0.45 * BIT_NS
        X = np.hstack([np.ones((keep.sum(), 1)), umid[keep, None], D[keep]])
        # sum(b)=0 via a soft constraint row
        Xc = np.vstack([X, np.r_[0, 0, np.ones(8)] * 1e3])
        yc = np.r_[(k * BIT_NS)[keep], 0.0]
        sol, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
        phi, L, b = sol[0], sol[1], sol[2:]
    t = phi + umid * L + b[s0]
    k = np.round(t / BIT_NS)
    return phi, L, b, (k * BIT_NS - t)[keep], int(keep.sum())


def peak(Ls, j):
    k = int(np.argmax(j))
    if 0 < k < len(j) - 1:
        y0, y1, y2 = j[k-1], j[k], j[k+1]
        d = .5 * (y0 - y2) / (y0 - 2*y1 + y2 + 1e-12)
        return Ls[k] + d * (Ls[1] - Ls[0]), j[k]
    return Ls[k], j[k]


if __name__ == "__main__":
    LG = np.arange(2280.0, 2740.0, 1.0)
    meta, caps = load_all()
    print("== real captures: calibration-free acquire + joint refine ==")
    Ls_, bs = [], []
    for cap in caps:
        j = Jg(cap, LG)
        Lc, jv = peak(LG, j)
        phi, L, b, res, nk = refine_joint(cap, Lc)
        Ls_.append(L); bs.append(b)
        print(f"{cap['pattern']:11s} {cap['rep']} Lc={Lc:8.2f} Jg={jv:5.3f} "
              f"L={L:8.2f} phi={phi:7.1f} n={nk:3d} "
              f"rms={np.sqrt((res**2).mean()):5.1f} max={np.abs(res).max():5.1f}")
    Ls_ = np.array(Ls_); bs = np.array(bs)
    print(f"\nL: mean={Ls_.mean():.3f} std={Ls_.std():.3f} "
          f"min={Ls_.min():.2f} max={Ls_.max():.2f}")
    print(f"per-capture b (mean over captures, ns): "
          f"{np.round(bs.mean(0),1).tolist()}")
    print(f"per-capture b (std  over captures, ns): "
          f"{np.round(bs.std(0),1).tolist()}")

    print("\n== synth envelope: calibration-free acquire + joint refine ==")
    print(f"{'eps':>8s} {'Ltrue':>8s} {'Jg':>6s} {'coarse_maxerr':>13s} "
          f"{'L_maxerr':>9s} {'fail':>7s}")
    for eps in (-0.08, -0.075, -0.05, -0.025, 0.0, 0.025, 0.05, 0.075, 0.08):
        Lt = truth_L(eps); ce, fe, jj, fail = [], [], [], 0
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=eps, phase_ns=(r*83.)%250))
                j = Jg(cap, LG); Lc, jv = peak(LG, j)
                phi, L, b, res, nk = refine_joint(cap, Lc)
                ce.append(Lc - Lt); fe.append(L - Lt); jj.append(jv)
                fail += abs(L - Lt) > 1.0
        print(f"{eps:+8.3f} {Lt:8.2f} {np.mean(jj):6.3f} "
              f"{np.max(np.abs(ce)):13.2f} {np.max(np.abs(fe)):9.3f} {fail:3d}/54")

    print("\n== synth drift +0.2% at eps=-7.5% ==")
    fe = []
    for name, pay in PATTERNS.items():
        for r in range(3):
            cap = pack(synth_capture(pay, eps=-0.075, drift=0.002,
                                     phase_ns=(r*83.)%250))
            j = Jg(cap, LG); Lc, jv = peak(LG, j)
            phi, L, b, res, nk = refine_joint(cap, Lc)
            fe.append(np.abs(res).max())
    print(f"  residual max over 54: {np.max(fe):.1f} ns, mean {np.mean(fe):.1f}")
