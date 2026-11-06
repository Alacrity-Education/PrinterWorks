"""Envelope behaviour: acquisition + refinement across eps = -8%..+8%
on synthetic captures (synth.py sampler model, bias == 0 by construction),
plus the +/-0.2% within-capture drift case and a tracker comparison.
"""
import sys
import numpy as np
from pathlib import Path
from common import REC, BIT_NS
sys.path.insert(0, str(REC))
from synth import synth_capture                      # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                        # noqa: E402

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
NB = 192


def pack(samples):
    it = np.array([i for i, _, _ in samples])
    sl = np.array([s for _, s, _ in samples])
    lv = np.array([v for _, _, v in samples], dtype=np.int8)
    return dict(it=it, slot=sl, lev=lv)


def rise(cap, a=A):
    d = np.diff(cap["lev"].astype(int))
    idx = np.nonzero(d > 0)[0]
    u = cap["it"] + a[cap["slot"]]
    return u[idx], u[idx + 1], cap["slot"][idx]


def coarse(cap, Lgrid, bf):
    u0, u1, s0 = rise(cap)
    umid = .5 * (u0 + u1); g = u1 - u0
    best = (-1, 0)
    for L in Lgrid:
        t = umid * L * (1 + 0) + bf[s0] * L
        w = np.sinc(g * L / BIT_NS)
        v = abs((w * np.exp(2j * np.pi * t / BIT_NS)).sum()) / np.abs(w).sum()
        if v > best[0]:
            best = (v, L)
    return best[1], best[0]


def refine(cap, L0, bf, iters=25, order=1):
    u0, u1, s0 = rise(cap)
    umid = .5 * (u0 + u1)
    L, phi, c2 = L0, 0.0, 0.0
    un = (umid - umid.mean())
    for _ in range(iters):
        b = bf[s0] * L
        t = phi + umid * L + c2 * un**2 + b
        k = np.round(t / BIT_NS)
        keep = np.abs(k * BIT_NS - t) < 0.45 * BIT_NS
        cols = [np.ones(keep.sum()), umid[keep]]
        if order >= 2:
            cols.append(un[keep]**2)
        X = np.vstack(cols).T
        sol, *_ = np.linalg.lstsq(X, (k * BIT_NS - b)[keep], rcond=None)
        phi, L = sol[0], sol[1]
        c2 = sol[2] if order >= 2 else 0.0
    b = bf[s0] * L
    t = phi + umid * L + c2 * un**2 + b
    k = np.round(t / BIT_NS)
    return phi, L, c2, (k * BIT_NS - t)[keep], keep.sum(), len(u0)


def truth_L(eps):
    return 40 * 62.5 / (1 + eps)


if __name__ == "__main__":
    bf0 = np.zeros(8)
    Lgrid = np.arange(2280.0, 2740.0, 2.0)
    print(f"{'eps':>8s} {'Ltrue':>8s} {'nrise':>6s} {'Lc_err':>7s} "
          f"{'Lerr_med':>9s} {'Lerr_max':>9s} {'res_rms':>8s} {'res_max':>8s} "
          f"{'lockfail':>8s}")
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.01, 0.0,
                0.01, 0.025, 0.05, 0.075, 0.08):
        Lt = truth_L(eps)
        errs, cerrs, rms, mx, nr, fail = [], [], [], [], [], 0
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=eps, phase_ns=(r * 83.0) % 250))
                Lc, J = coarse(cap, Lgrid, bf0)
                phi, L, _, res, nk, n = refine(cap, Lc, bf0)
                cerrs.append(Lc - Lt); errs.append(L - Lt); nr.append(n)
                rms.append(np.sqrt((res**2).mean())); mx.append(np.abs(res).max())
                fail += abs(L - Lt) > 1.0
        print(f"{eps:+8.3f} {Lt:8.2f} {np.mean(nr):6.1f} "
              f"{np.max(np.abs(cerrs)):7.2f} {np.median(np.abs(errs)):9.3f} "
              f"{np.max(np.abs(errs)):9.3f} {np.mean(rms):8.2f} "
              f"{np.max(mx):8.1f} {fail:5d}/54")

    print("\n== within-capture drift (+0.2% ramp) at eps=-7.5% ==")
    for order in (1, 2):
        rms, mx, errs = [], [], []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=-0.075, drift=0.002,
                                         phase_ns=(r * 83.0) % 250))
                Lc, J = coarse(cap, Lgrid, bf0)
                phi, L, c2, res, nk, n = refine(cap, Lc, bf0, order=order)
                rms.append(np.sqrt((res**2).mean())); mx.append(np.abs(res).max())
        print(f"  order={order}: res_rms={np.mean(rms):6.2f} "
              f"res_max={np.max(mx):7.2f} ns")

    print("\n== no-drift reference at eps=-7.5% ==")
    for order in (1, 2):
        rms, mx = [], []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=-0.075, phase_ns=(r*83.)%250))
                Lc, J = coarse(cap, Lgrid, bf0)
                phi, L, c2, res, nk, n = refine(cap, Lc, bf0, order=order)
                rms.append(np.sqrt((res**2).mean())); mx.append(np.abs(res).max())
        print(f"  order={order}: res_rms={np.mean(rms):6.2f} "
              f"res_max={np.max(mx):7.2f} ns")
