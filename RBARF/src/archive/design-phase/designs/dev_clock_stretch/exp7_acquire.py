"""Blind acquisition across the full +/-8% envelope.

Objective (no payload knowledge):
    J(L) = | SUM_j w_j exp(2*pi*i*(umid_j*L + bias[s_j]) / 1250) |
with bias[] the per-slot-pair correction learned globally in exp6.
Scan L over the envelope, look at the peak structure, and check that the
iterated closest-bit least squares (exp6.fit_capture) converges to the
same answer from a coarse start.
"""
import numpy as np
from common import load_all, BIT_NS
from exp6_residual_decomp import rise_events, fit_capture

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
BIAS = np.array([-296.3, -530.4, 444.1, 168.5, -63.6, -346.1, 539.5, 84.3])


def J(cap, Ls, a=A, bias=BIAS, phi=0.0):
    idx, u0, u1, s0 = rise_events(cap, a)
    umid = 0.5 * (u0 + u1)
    g = (u1 - u0)
    out = np.empty(len(Ls))
    for k, L in enumerate(Ls):
        t = umid * L + bias[s0] + phi
        w = np.sinc(g * L / BIT_NS)
        out[k] = abs((w * np.exp(2j * np.pi * t / BIT_NS)).sum()) / np.abs(w).sum()
    return out


def local_maxima(x):
    return np.nonzero((x[1:-1] > x[:-2]) & (x[1:-1] >= x[2:]))[0] + 1


if __name__ == "__main__":
    meta, caps = load_all()
    Ls = np.arange(2300.0, 2705.0, 0.25)
    print("== bias-corrected periodogram over +/-8% ==")
    print(f"{'pattern':11s} {'rep':>3s} {'Lpk':>8s} {'J':>6s} "
          f"{'2nd L':>8s} {'J2':>6s} {'Lfit':>8s} {'|dL|':>6s}")
    d1, d2 = [], []
    for cap in caps:
        j = J(cap, Ls)
        pk = local_maxima(j)
        order = pk[np.argsort(j[pk])[::-1]]
        Lpk = Ls[order[0]]
        second = next((Ls[o] for o in order[1:] if abs(Ls[o] - Lpk) > 6.0), np.nan)
        j2 = j[Ls == second][0] if second == second else 0.0
        f = fit_capture(cap, A, BIAS, L0=Lpk, phi0=0.0, iters=12)
        d1.append(j[order[0]]); d2.append(j2 / j[order[0]])
        print(f"{cap['pattern']:11s} {cap['rep']:3d} {Lpk:8.2f} {j[order[0]]:6.3f} "
              f"{second:8.2f} {j2:6.3f} {f['L']:8.2f} {abs(f['L']-2499.6):6.2f}")
    print(f"\npeak J: mean={np.mean(d1):.3f} min={np.min(d1):.3f}")
    print(f"2nd/1st ratio: mean={np.mean(d2):.3f} max={np.max(d2):.3f}")

    print("\n== cold-start capture range: fit from L0 offsets ==")
    for off in (-180, -120, -60, -26, -13, -6.5, 0, 6.5, 13, 26, 60, 120, 180):
        ok = 0
        for cap in caps:
            f = fit_capture(cap, A, BIAS, L0=2499.6 + off, phi0=150.0, iters=25)
            ok += abs(f["L"] - 2499.6) < 1.0
        print(f"  L0 = 2499.6{off:+7.1f} ({off/2499.6*100:+.2f}%) -> "
              f"{ok:2d}/54 converge")
