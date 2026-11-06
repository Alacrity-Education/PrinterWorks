"""What the clock estimate is actually worth downstream: how accurately
does the fitted (phi, L) reproduce the TRUE sample times / bit indices?
(synthetic, where the truth is exact).  Also: alias-candidate enumeration
and header/trailer disambiguation."""
import sys
import numpy as np
from common import REC, BIT_NS
sys.path.insert(0, str(REC))
from synth import synth_capture, CY_NS, LOOP_CY, SLOT_POS_CY  # noqa: E402
sys.path.insert(0, str(REC.parent / "bench"))
from patterns import PATTERNS                                  # noqa: E402
from exp9_envelope import pack, coarse as coarseS, refine as refineS, truth_L

A = np.array(SLOT_POS_CY, float) / LOOP_CY
LG = np.arange(2280.0, 2740.0, 2.0)


def true_times(cap, eps, phase_ns):
    cy = cap["it"] * LOOP_CY + np.array(SLOT_POS_CY)[cap["slot"]]
    return phase_ns + cy * CY_NS / (1 + eps)


if __name__ == "__main__":
    bf0 = np.zeros(8)
    print(f"{'eps':>8s} {'maxdt_frame':>12s} {'rms_dt':>8s} "
          f"{'bit_misassign':>14s} {'worst_cap':>10s}")
    for eps in (-0.08, -0.075, -0.05, -0.025, -0.005, 0.0,
                0.005, 0.025, 0.05, 0.075, 0.08):
        mx, rms, mis = [], [], []
        for name, pay in PATTERNS.items():
            for r in range(3):
                ph = (r * 83.0) % 250
                cap = pack(synth_capture(pay, eps=eps, phase_ns=ph))
                Lc, J = coarseS(cap, LG, bf0)
                phi, L, c2, res, nk, n = refineS(cap, Lc, bf0)
                tt = true_times(cap, eps, ph)
                tm = phi + (cap["it"] + A[cap["slot"]]) * L
                m = tt < 192 * BIT_NS
                d = (tm - tt)[m]
                mx.append(np.abs(d).max()); rms.append(np.sqrt((d**2).mean()))
                mis.append(np.mean(np.floor(tm[m]/BIT_NS) !=
                                   np.floor(tt[m]/BIT_NS)))
        print(f"{eps:+8.3f} {np.max(mx):12.1f} {np.mean(rms):8.1f} "
              f"{np.mean(mis):13.4%} {np.max(mis):10.4%}")
