#!/usr/bin/env python3
"""Check marker-label coverage per bracket family and the phi_f fit quality."""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset, linearize  # noqa: E402
import combined as C  # noqa: E402


def frame_bits(payload_hex):
    fr = C.HDR + bytes.fromhex(payload_hex) + C.TRL
    return C._bits_of(fr)


def main():
    meta, caps = load_dataset()
    caps = [c for c in caps if c["rep"] in (0, 1)]
    model = C.MODELS[0]
    for c in caps:
        if c["pattern"] not in ("rnd2", "rnd3", "blocks", "sparse", "p55") or c["rep"] != 0:
            continue
        samples = linearize(c["capture"])
        truth = frame_bits(c["payload"])
        pulses = C._model_clock_pulses(samples, model)
        kappa, tau, hits, resid = C._hough_candidates(pulses)[0]
        seg, slip0 = C._segment(pulses, kappa, tau)
        # global h fit labels (marker pulses)
        fam_lab = defaultdict(list)      # (sfa,sfb) -> list of (phi_lo, phi_hi, class)
        fam_all = defaultdict(int)
        h0c, h1c = model["H0"], model["H1"]
        for j, p in enumerate(seg):
            k0, k1 = p["k0"], p["k1"]
            fam = (p["sfa"], p["sfb"])
            fam_all[fam] += 1
            if k1 > C.NB or any(C.KNOWN[t] < 0 for t in range(k0, k1)):
                continue
            amin, amax = C._a_bounds(k0, k1)
            if amin != amax:
                continue
            a = amin
            L = k1 - k0
            u, v = p["u"], p["v"]
            if a == 0:
                H = h0c
                cls = 0
            elif a == L:
                H = (a - 1) * C.BIT + h1c
                cls = 1
            else:
                mid = (u + v) / 2
                d1 = abs(mid - ((a - 1) * C.BIT + h1c))
                d0 = abs(mid - (a * C.BIT + h0c))
                if d1 <= d0:
                    H = (a - 1) * C.BIT + h1c
                    cls = 1
                else:
                    H = a * C.BIT + h0c
                    cls = 0
            fam_lab[fam].append((round(u - H, 1), round(v - H, 1), cls))
        name = f"{c['pattern']}_{c['rep']}"
        print(f"== {name}  kappa={kappa:.5f} tau={tau:.1f}")
        for fam in sorted(fam_all):
            labs = fam_lab.get(fam, [])
            lo = max((x[0] for x in labs), default=None)
            hi = min((x[1] for x in labs), default=None)
            n0 = sum(1 for x in labs if x[2] == 0)
            n1 = sum(1 for x in labs if x[2] == 1)
            print(f"   fam {fam}: pulses={fam_all[fam]:3d} labels={len(labs):2d} "
                  f"(c0={n0},c1={n1}) phi in [{lo},{hi}]")


if __name__ == "__main__":
    main()
