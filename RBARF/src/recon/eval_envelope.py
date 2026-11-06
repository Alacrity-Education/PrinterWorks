#!/usr/bin/env python3
"""Evaluate a decoder across the HSI temperature envelope (synthetic).

Sweeps the receiver clock error over the +/-7.5% guaranteed envelope
(one point past each corner), all 18 test patterns x 3 phases per point,
plus a within-capture drift case. See HSI_TEMPERATURE.md.

Usage:
    python3 eval_envelope.py approaches/<name>.py
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness import load_dataset, score  # noqa: E402
from synth import synth_capture, envelope_cases  # noqa: E402
from eval import load_module  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("approach")
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    mod = load_module(args.approach)
    meta, _ = load_dataset()

    by_case = defaultdict(lambda: [0, 0, 0.0])    # n, exact, acc_sum
    for case, pname, payload, eps, drift, phase in envelope_cases(args.reps):
        samples = synth_capture(payload, eps=eps, drift=drift,
                                phase_ns=phase)
        try:
            decoded = mod.decode(samples, meta)
        except Exception:
            decoded = None
        exact, acc = score(decoded, payload)
        st = by_case[case]
        st[0] += 1
        st[1] += int(exact)
        st[2] += acc

    print(f"{'clock error':16s} {'exact':>9s} {'byte-acc':>9s}")
    worst = 1.0
    for case, (n, ex, accs) in by_case.items():
        rate = ex / n
        worst = min(worst, rate)
        print(f"{case:16s} {ex:4d}/{n:<4d} {accs/n:8.1%}")
    print("-" * 36)
    verdict = "TEMPERATURE-READY" if worst == 1.0 else \
              ("DEGRADES AT CORNERS" if worst > 0.5 else "FAILS ENVELOPE")
    print(f"worst-case exact rate {worst:.1%} -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
