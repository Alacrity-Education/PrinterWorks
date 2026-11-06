"""Slow-corner physics: dead-zone width, swallow rate, merge rate, max span,
intrinsic (information-free) ambiguity vs eps -- measured on synth truth."""
import sys
from pathlib import Path
import numpy as np
from collections import Counter

RECON = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(RECON)); sys.path.insert(0, str(RECON.parent / "bench"))
from synth import synth_capture, SLOT_POS_CY, LOOP_CY, CY_NS  # noqa: E402
from patterns import PATTERNS, frame  # noqa: E402

BIT, H0, H1, NBITS = 1250.0, 350.0, 700.0, 192


def bits_of(fb):
    return [(b >> (7 - k)) & 1 for b in fb for k in range(8)]


print("%7s %9s %9s %9s %9s %9s %7s" %
      ("eps", "gap7_ns", "swal/f", "merge/f", "amb/f", "amb%", "maxspan"))
for eps in (-0.08, -0.075, -0.05, -0.025, -0.003, 0.0, 0.025, 0.05, 0.075, 0.08):
    c = Counter(); maxspan = 0
    gap7 = (LOOP_CY - SLOT_POS_CY[-1] + SLOT_POS_CY[0]) * CY_NS / (1 + eps)
    for name, payload in PATTERNS.items():
        for rep in range(3):
            phase = (rep * 83.0) % 250.0
            bits = bits_of(frame(payload))
            s = synth_capture(payload, eps=eps, phase_ns=phase)
            it = np.array([i for i, _, _ in s], float)
            sl = np.array([x for _, x, _ in s], int)
            lv = np.array([v for _, _, v in s], bool)
            t = phase + (it * LOOP_CY + np.array(SLOT_POS_CY)[sl]) * CY_NS / (1 + eps)
            for n in range(NBITS):
                a = ((t >= n * BIT) & (t < n * BIT + H0)).sum()
                d = ((t >= n * BIT + H0) & (t < n * BIT + H1)).sum()
                m = ((t >= n * BIT + H1) & (t < (n + 1) * BIT)).sum()
                if bits[n] == 0 and a == 0:
                    c["swal"] += 1
                if bits[n] == 1 and m == 0 and n + 1 < NBITS:
                    c["merge"] += 1
                if d == 0:
                    c["amb"] += 1
                c["bits"] += 1
            # observed span distribution
            i = 0
            while i < len(lv):
                if lv[i]:
                    j = i
                    while j + 1 < len(lv) and lv[j + 1]:
                        j += 1
                    ks = {int(t[m] // BIT) for m in range(i, j + 1)}
                    maxspan = max(maxspan, len([k for k in ks if 0 <= k < NBITS]))
                    i = j + 1
                else:
                    i += 1
    print("%+7.3f %9.1f %9.2f %9.2f %9.2f %9.3f %7d" %
          (eps, gap7, c["swal"] / 54, c["merge"] / 54, c["amb"] / 54,
           100 * c["amb"] / c["bits"], maxspan))
