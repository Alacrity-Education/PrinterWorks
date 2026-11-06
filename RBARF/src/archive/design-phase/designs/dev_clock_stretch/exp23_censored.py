"""Interval-censored edge fit: no empirical bias table, only the
calibrated slot fractions.  An observed 0->1 transition between samples n
and n+1 proves the true rising edge lies in (t_n, t_{n+1}]; the cost is
the distance by which the model's nearest bit boundary falls OUTSIDE that
interval (zero if inside).  Same for falls, with the T0H/T1H ambiguity
handled by taking the min over both hypotheses.

Compared against the bias-table estimator on real data and, crucially,
across the +/-8% envelope on synthetic captures (where the bias table is
invalid).
"""
import sys
import numpy as np
from common import load_all, BIT_NS, REC
sys.path.insert(0, str(REC))
from synth import synth_capture                       # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                         # noqa: E402
from exp9_envelope import pack, truth_L

A = np.array([1, 5, 9, 13, 17, 21, 27, 32], float) / 40.0
T0H, T1H = 350.0, 700.0
CLIP = 0.45 * BIT_NS


def brackets(cap, a, kind):
    d = np.diff(cap["lev"].astype(int))
    idx = np.nonzero(d > 0 if kind > 0 else d < 0)[0]
    u = cap["it"] + a[cap["slot"]]
    return u[idx], u[idx + 1]


def cost_rise(u0, u1, phi, L, clip=CLIP):
    t0, t1 = phi + u0 * L, phi + u1 * L
    tm = .5 * (t0 + t1)
    k = np.round(tm / BIT_NS)
    e = k * BIT_NS
    c = np.maximum(0.0, np.maximum(t0 - e, e - t1))
    return np.minimum(c, clip)


def cost_fall(u0, u1, phi, L, clip=CLIP):
    t0, t1 = phi + u0 * L, phi + u1 * L
    tm = .5 * (t0 + t1)
    out = None
    for TH in (T0H, T1H):
        k = np.round((tm - TH) / BIT_NS)
        e = k * BIT_NS + TH
        c = np.maximum(0.0, np.maximum(t0 - e, e - t1))
        out = c if out is None else np.minimum(out, c)
    return np.minimum(out, clip)


def total(cap, a, phi, L, use_falls=True):
    r0, r1 = brackets(cap, a, +1)
    c = cost_rise(r0, r1, phi, L)
    s = (c ** 2).sum()
    n = len(c)
    if use_falls:
        f0, f1 = brackets(cap, a, -1)
        cf = cost_fall(f0, f1, phi, L)
        s += (cf ** 2).sum(); n += len(cf)
    return s / n


def acquire(cap, a, Lgrid, phigrid, use_falls=True):
    best = (1e30, 0, 0)
    for L in Lgrid:
        for phi in phigrid:
            v = total(cap, a, phi, L, use_falls)
            if v < best[0]:
                best = (v, phi, L)
    return best


def polish(cap, a, phi, L, use_falls=True, rounds=7):
    dphi, dL = 60.0, 3.0
    for r in range(rounds):
        improved = True
        while improved:
            improved = False
            base = total(cap, a, phi, L, use_falls)
            for dp, dl in ((dphi, 0), (-dphi, 0), (0, dL), (0, -dL),
                           (dphi, dL), (-dphi, -dL), (dphi, -dL), (-dphi, dL)):
                v = total(cap, a, phi + dp, L + dl, use_falls)
                if v < base - 1e-12:
                    phi, L, base, improved = phi + dp, L + dl, v, True
        dphi *= 0.45; dL *= 0.45
    return phi, L, total(cap, a, phi, L, use_falls)


if __name__ == "__main__":
    LGRID = np.arange(2300., 2710., 2.0)
    PGRID = np.arange(-100., 400., 50.)

    print("== real captures ==")
    meta, caps = load_all()
    Ls = []
    for cap in caps:
        v, phi, L = acquire(cap, A, LGRID, PGRID)
        phi, L, v = polish(cap, A, phi, L)
        Ls.append(L)
        print(f"{cap['pattern']:11s} {cap['rep']} L={L:8.2f} phi={phi:7.1f} "
              f"cost_rms={np.sqrt(v):6.1f}")
    Ls = np.array(Ls)
    print(f"L: mean={Ls.mean():.2f} std={Ls.std():.2f} "
          f"min={Ls.min():.2f} max={Ls.max():.2f}")

    print("\n== synthetic envelope (a = true slot fractions, no bias table) ==")
    print(f"{'eps':>8s} {'Ltrue':>8s} {'med|err|':>9s} {'max|err|':>9s} {'fail>4.5ns':>11s}")
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.01, -0.002, 0.0,
                0.002, 0.01, 0.025, 0.05, 0.075, 0.08):
        Lt = truth_L(eps); err = []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=eps, phase_ns=(r*83.)%250))
                v, phi, L = acquire(cap, A, LGRID, PGRID)
                phi, L, v = polish(cap, A, phi, L)
                err.append(L - Lt)
        err = np.abs(np.array(err))
        print(f"{eps:+8.3f} {Lt:8.2f} {np.median(err):9.3f} {err.max():9.3f} "
              f"{(err>4.5).sum():8d}/54")
