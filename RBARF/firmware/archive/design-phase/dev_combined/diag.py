#!/usr/bin/env python3
"""Diagnose combined.py against ground truth (dev only -- decode() stays blind)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset, linearize  # noqa: E402
import combined  # noqa: E402


def frame_bits(payload_hex):
    fr = combined.HDR + bytes.fromhex(payload_hex) + combined.TRL
    return combined._bits_of(fr)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "train"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    meta, caps = load_dataset()
    if which == "train":
        caps = [c for c in caps if c["rep"] in (0, 1)]
    elif which == "holdout":
        caps = [c for c in caps if c["rep"] == 2]
    n_exact = 0
    tot_bits_wrong = 0
    for c in caps:
        name = f"{c['pattern']}_{c['rep']}"
        if only and only not in name:
            continue
        samples = linearize(c["capture"])
        best, q = combined._decode_full(samples, meta)
        truth = frame_bits(c["payload"])
        if best is None:
            print(f"{name:14s}  DECODE FAILED")
            continue
        bits = best["bits"]
        wrong = [t for t in range(combined.NB) if bits[t] != truth[t]]
        exact = bytes(best["payload"]) == bytes.fromhex(c["payload"])
        n_exact += exact
        tot_bits_wrong += len(wrong)
        flag = "OK " if exact else "BAD"
        print(f"{name:14s} {flag} model={best['model']} alias={best['alias']} "
              f"kappa={best['kappa']:.5f} tau={best['tau']:6.1f} "
              f"hits={best['hits']} viol={best['violations']} "
              f"infeas={best['infeasible']} laberr={best['label_err']}/"
              f"{best['n_forced']} h=({best['h0c']:.0f},{best['h1c']:.0f}) "
              f"slip0={best['slip0']} wrong={len(wrong)}")
        if wrong and (only or len(wrong) < 12):
            # per wrong bit, find the pulse
            for t in wrong:
                pl = None
                for p in best["seg"]:
                    if p["k0"] <= t < p["k1"]:
                        pl = p
                        break
                if pl is None:
                    print(f"    bit {t:3d}: truth={truth[t]} got={bits[t]} "
                          f"(no pulse: hidden region)")
                else:
                    off = t - pl["k0"]
                    print(f"    bit {t:3d}: truth={truth[t]} got={bits[t]} "
                          f"llr={best['llr'][t]:+7.2f} pulse k0={pl['k0']} "
                          f"L={pl['k1']-pl['k0']} a_hat={pl['a_hat']} off={off} "
                          f"u={pl['u']:7.1f} v={pl['v']:7.1f} "
                          f"slots=({pl['sfa']},{pl['sfb']}) nh={pl['nhigh']} "
                          f"cost={pl['cost']:.3f}")
    print(f"\nEXACT {n_exact}/{len([1 for c in caps if not only or only in f'{c['pattern']}_{c['rep']}'])}  "
          f"wrong-bits total {tot_bits_wrong}")


if __name__ == "__main__":
    main()
