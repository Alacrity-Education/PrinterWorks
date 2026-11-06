"""Robustness of the clock estimator to (a) wrong slot-offset calibration,
(b) loss of rising edges, (c) restriction to header/trailer only."""
import sys
import numpy as np
from common import load_all, REC, BIT_NS
sys.path.insert(0, str(REC))
from synth import synth_capture                       # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                         # noqa: E402
from exp9_envelope import pack, coarse as coarseS, refine as refineS, truth_L
from exp8_pipeline import A, BIAS_F, coarse as coarseR, refine as refineR

LGRID = np.arange(2280.0, 2740.0, 2.0)


def sweep_bias(scale, eps):
    bf = BIAS_F * scale
    err, fail = [], 0
    for name, pay in PATTERNS.items():
        for r in range(3):
            cap = pack(synth_capture(pay, eps=eps, phase_ns=(r * 83.0) % 250))
            Lc, J = coarseS(cap, LGRID, bf)
            phi, L, c2, res, nk, n = refineS(cap, Lc, bf)
            err.append(L - truth_L(eps)); fail += abs(L - truth_L(eps)) > 1.0
    return np.max(np.abs(err)), fail


def real_with_bias(bfscale):
    bf = BIAS_F * bfscale
    Ls, fails = [], 0
    meta, caps = load_all()
    for cap in caps:
        idx = None
        Lc, J, _ = coarseR(cap, np.arange(2300.0, 2705.0, 2.0), bf=bf)
        phi, L, res, k, umid, s0 = refineR(cap, Lc, bf=bf)
        Ls.append(L); fails += abs(L - 2499.8) > 3.0
    return np.array(Ls), fails


def decimate_test(frac):
    """keep only a fraction of rising edges (simulates heavy swallowing)."""
    meta, caps = load_all()
    rng = np.random.default_rng(7)
    errs = []
    for cap in caps:
        d = np.diff(cap["lev"].astype(int))
        ridx = np.nonzero(d > 0)[0]
        keep = rng.random(len(ridx)) < frac
        lev = cap["lev"].copy()
        # remove a rising edge by extending the previous low over the pulse
        for j, k in enumerate(ridx):
            if not keep[j]:
                n = k + 1
                while n < len(lev) and lev[n] == 1:
                    lev[n] = 0; n += 1
        c2 = dict(cap); c2["lev"] = lev
        Lc, J, _ = coarseR(c2, np.arange(2300.0, 2705.0, 2.0))
        phi, L, res, k, umid, s0 = refineR(c2, Lc)
        errs.append(L - 2499.8)
    return np.array(errs)


if __name__ == "__main__":
    print("== synth: wrong slot calibration (bias scaled) ==")
    print(f"{'bias x':>8s} {'eps=-7.5%':>22s} {'eps=0':>22s} {'eps=+7.5%':>22s}")
    for sc in (0.0, 0.25, 0.5, 1.0, 2.0):
        row = []
        for eps in (-0.075, 0.0, 0.075):
            e, f = sweep_bias(sc, eps)
            row.append(f"maxerr={e:6.2f} fail={f:2d}/54")
        print(f"{sc:8.2f} {row[0]:>22s} {row[1]:>22s} {row[2]:>22s}")

    print("\n== real captures: sensitivity to the bias vector ==")
    for sc in (0.0, 0.5, 0.75, 1.0, 1.25, 1.5):
        Ls, f = real_with_bias(sc)
        print(f"  bias x{sc:4.2f}: L mean={Ls.mean():8.2f} std={Ls.std():5.2f} "
              f"min={Ls.min():8.2f} max={Ls.max():8.2f} outliers={f}/54")

    print("\n== real captures: rising edges randomly destroyed ==")
    for frac in (1.0, 0.75, 0.5, 0.35, 0.25, 0.15):
        e = decimate_test(frac)
        print(f"  keep {frac:4.2f}: |dL| med={np.median(np.abs(e)):6.2f} "
              f"max={np.max(np.abs(e)):7.2f} ns  >3ns: {(np.abs(e)>3).sum()}/54")
