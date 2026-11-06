"""(a) How accurate must the slot calibration be for the scale estimate to
    survive at the envelope corners?
(b) Second-order PLL tracker vs the global 2-parameter fit: gain sweep on
    real captures and on synthetic drifting captures.
"""
import sys
import numpy as np
from common import load_all, REC, BIT_NS
sys.path.insert(0, str(REC))
from synth import synth_capture                        # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                          # noqa: E402
from exp9_envelope import pack, coarse as coarseS, refine as refineS, truth_L
from exp8_pipeline import A, BIAS_F, coarse as coarseR, refine as refineR

LG = np.arange(2280.0, 2740.0, 2.0)
RNG = np.random.default_rng(11)


def tol_scan(eps, amps):
    """inject a random per-slot offset error of RMS `amp` ns."""
    out = []
    for amp in amps:
        fail, err = 0, []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=eps, phase_ns=(r*83.)%250))
                e = RNG.normal(0, amp, 8); e -= e.mean()
                bf = e / 2500.0
                Lc, J = coarseS(cap, LG, bf)
                phi, L, c2, res, nk, n = refineS(cap, Lc, bf)
                err.append(abs(L - truth_L(eps))); fail += abs(L-truth_L(eps)) > 1.0
        out.append((amp, np.median(err), np.max(err), fail))
    return out


def pll(cap, L0, phi0, bf, kp, ki):
    """2nd-order tracker over rising edges, in loop-index time.
    state: th (grid phase, ns), nu (loop period, ns/loop)."""
    d = np.diff(cap["lev"].astype(int))
    idx = np.nonzero(d > 0)[0]
    u = cap["it"] + A[cap["slot"]]
    umid = .5 * (u[idx] + u[idx + 1]); s0 = cap["slot"][idx]
    th, nu = phi0, L0
    prev_u = 0.0
    hist = []
    for j in range(len(umid)):
        du = umid[j] - prev_u
        th = th + 0.0                       # phase advances with nu implicitly
        t = th + umid[j] * nu + bf[s0[j]] * nu
        e = t - round(t / BIT_NS) * BIT_NS
        if abs(e) > 0.45 * BIT_NS:
            prev_u = umid[j]; continue
        th -= kp * e
        nu -= ki * e / max(umid[j], 1e-6)
        hist.append((umid[j], e))
        prev_u = umid[j]
    return th, nu, np.array([h[1] for h in hist])


if __name__ == "__main__":
    print("== slot-calibration tolerance (random per-slot error, rms ns) ==")
    for eps in (-0.075, -0.025, -0.005, 0.0, 0.075):
        rows = tol_scan(eps, [10, 20, 40, 60, 90, 130, 190, 260])
        s = "  ".join(f"{a:3.0f}ns:{f:2d}f" for a, m, x, f in rows)
        print(f"  eps={eps:+.3f}: {s}")

    print("\n== PLL gain sweep, real captures (metric: max |phase error| "
          "over the frame, after tracking) ==")
    meta, caps = load_all()
    base = {}
    for cap in caps:
        Lc, J, _ = coarseR(cap, np.arange(2300., 2705., 2.))
        phi, L, res, k, umid, s0 = refineR(cap, Lc)
        base[(cap["pattern"], cap["rep"])] = (phi, L, np.abs(res).max(),
                                              np.sqrt((res**2).mean()))
    print(f"  global 2-param fit: mean rms={np.mean([v[3] for v in base.values()]):.1f} "
          f"worst max={np.max([v[2] for v in base.values()]):.1f} ns")
    for kp, ki in ((0.0, 0.0), (0.02, 0.0002), (0.05, 0.001), (0.1, 0.004),
                   (0.3, 0.02), (0.6, 0.08)):
        mx, rm = [], []
        for cap in caps:
            phi, L, _, _ = base[(cap["pattern"], cap["rep"])]
            th, nu, e = pll(cap, L, phi, BIAS_F, kp, ki)
            mx.append(np.abs(e).max()); rm.append(np.sqrt((e**2).mean()))
        print(f"  kp={kp:5.2f} ki={ki:7.4f}: rms={np.mean(rm):6.1f} "
              f"worst={np.max(mx):6.1f} ns")

    print("\n== PLL on synthetic drift (+0.2%) at eps=-7.5%, bias=0 ==")
    bf0 = np.zeros(8)
    for kp, ki in ((0.0, 0.0), (0.05, 0.001), (0.1, 0.004), (0.3, 0.02)):
        mx = []
        for name, pay in PATTERNS.items():
            for r in range(3):
                cap = pack(synth_capture(pay, eps=-0.075, drift=0.002,
                                         phase_ns=(r*83.)%250))
                Lc, J = coarseS(cap, LG, bf0)
                phi, L, c2, res, nk, n = refineS(cap, Lc, bf0)
                th, nu, e = pll(cap, L, phi, bf0, kp, ki)
                mx.append(np.abs(e).max())
        print(f"  kp={kp:5.2f} ki={ki:7.4f}: worst={np.max(mx):7.1f} "
              f"mean={np.mean(mx):7.1f} ns")
