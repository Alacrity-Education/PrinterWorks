#!/usr/bin/env python3
"""Diagnose combined.py on synthetic envelope points."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import load_dataset  # noqa: E402
from synth import synth_capture  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "bench"))
from patterns import PATTERNS, frame  # noqa: E402
import combined as C  # noqa: E402


def main():
    eps = float(sys.argv[1]) if len(sys.argv) > 1 else 0.025
    drift = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    meta, _ = load_dataset()
    n_exact = 0
    n = 0
    for name, payload in PATTERNS.items():
        for r in range(3):
            phase = 254.0 + (r * 83.0) % 250.0
            samples = synth_capture(payload, eps=eps, drift=drift,
                                    phase_ns=phase)
            fr = frame(payload)
            truth = C._bits_of(fr)
            best, q = C._decode_full(samples, meta)
            n += 1
            if best is None:
                print(f"{name}_{r:d}  DECODE FAILED")
                continue
            bits = best["bits"]
            wrong = [t for t in range(C.NB) if bits[t] != truth[t]]
            exact = bytes(best["payload"]) == payload
            n_exact += exact
            flag = "OK " if exact else "BAD"
            wp = [t for t in wrong if 32 <= t < 160]
            print(f"{name:11s}_{r} {flag} model={best['model']} "
                  f"al={best['alias']} kap={best['kappa']:.5f} "
                  f"hits={best['hits']} viol={best['violations']} "
                  f"inf={best['infeasible']} le={best['label_err']} "
                  f"h=({best['h0c']:.0f},{best['h1c']:.0f}) "
                  f"slip0={best['slip0']} wrong={len(wrong)} "
                  f"pay={len(wp)} {wp[:8] if len(wp)<9 else wp[:8]+['...']}")
    print(f"\nEXACT {n_exact}/{n}")


if __name__ == "__main__":
    main()
