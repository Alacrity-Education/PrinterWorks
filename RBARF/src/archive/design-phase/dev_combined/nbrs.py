#!/usr/bin/env python3
"""For the failing bits, print same-family neighbours (u, truth) to see
whether local context separates the knife-edge cases."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset, linearize  # noqa: E402
import combined as C  # noqa: E402

CASES = [
    ("zeros", 0, 37), ("p55", 0, 35), ("msb1", 0, 80), ("blocks", 0, 41),
    ("blocks", 0, 55), ("nibbles", 1, 49), ("nibbles", 1, 53),
    ("sparse", 0, 39), ("sparse", 1, 39), ("rnd2", 1, 49), ("rnd2", 1, 35),
]


def frame_bits(payload_hex):
    fr = C.HDR + bytes.fromhex(payload_hex) + C.TRL
    return C._bits_of(fr)


def truth_a(truth, k0, k1):
    a = 0
    for t in range(k0, k1):
        if truth[t] == 1:
            a += 1
        else:
            break
    return a


def main():
    meta, caps = load_dataset()
    bycap = {(c["pattern"], c["rep"]): c for c in caps}
    done = set()
    for pat, rep, bit in CASES:
        if (pat, rep) in done:
            continue
        done.add((pat, rep))
        c = bycap[(pat, rep)]
        samples = linearize(c["capture"])
        truth = frame_bits(c["payload"])
        model = C.MODELS[0]
        pulses = C._model_clock_pulses(samples, model)
        kappa, tau, hits, resid = C._hough_candidates(pulses)[0]
        seg, slip0 = C._segment(pulses, kappa, tau)
        bits_of_interest = [b for p, r, b in CASES if p == pat and r == rep]
        print(f"== {pat}_{rep} (interest: {bits_of_interest})")
        for p in seg:
            if p["sfa"] != 5 and not any(p["k0"] <= b < p["k1"]
                                         for b in bits_of_interest):
                continue
            fam = (p["sfa"], p["sfb"])
            if fam != (5, 6) and not any(p["k0"] <= b < p["k1"]
                                         for b in bits_of_interest):
                continue
            at = truth_a(truth, p["k0"], min(p["k1"], C.NB))
            mark = " ***" if any(p["k0"] <= b < p["k1"]
                                 for b in bits_of_interest) else ""
            known = all(C.KNOWN[t] >= 0
                        for t in range(p["k0"], min(p["k1"], C.NB)))
            print(f"  k0={p['k0']:3d} L={p['k1']-p['k0']} fam={fam} "
                  f"u={p['u']:7.1f} v={p['v']:7.1f} nh={p['nhigh']} "
                  f"a_true={at}{' M' if known else ''}{mark}")


if __name__ == "__main__":
    main()
