#!/usr/bin/env python3
"""Evaluate a reconstruction approach against the acquired dataset.

Usage:
    python3 eval.py approaches/<name>.py            # train split (reps 0,1)
    python3 eval.py approaches/<name>.py --all      # every capture
    python3 eval.py approaches/<name>.py --holdout  # holdout split (rep 2)

Scoring: per-capture exact payload match + byte accuracy. The holdout
split exists to catch overfitting to individual captures.
"""

import argparse
import importlib.util
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness import load_dataset, linearize, score  # noqa: E402


def load_module(path: str):
    p = Path(path)
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("approach")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--data", default=None,
                    help="alternate dataset json (e.g. ../data/captures_val.json)")
    args = ap.parse_args()

    mod = load_module(args.approach)
    if args.data:
        meta, caps = load_dataset(args.data)
        args.all = True
    else:
        meta, caps = load_dataset()

    if args.all:
        subset = caps
    elif args.holdout:
        subset = [c for c in caps if c["rep"] == 2]
    else:
        subset = [c for c in caps if c["rep"] in (0, 1)]

    per_pattern = defaultdict(lambda: [0, 0, 0.0])   # n, exact, acc_sum
    t0 = time.monotonic()
    for c in subset:
        samples = linearize(c["capture"])
        expected = bytes.fromhex(c["payload"])
        try:
            decoded = mod.decode(samples, meta)
        except Exception as e:
            decoded = None
            print(f"  ! {c['pattern']} rep {c['rep']}: decode raised {e!r}")
        exact, acc = score(decoded, expected)
        st = per_pattern[c["pattern"]]
        st[0] += 1
        st[1] += int(exact)
        st[2] += acc
    dt = time.monotonic() - t0

    total_n = total_exact = 0
    total_acc = 0.0
    print(f"{'pattern':12s} {'exact':>9s} {'byte-acc':>9s}")
    for name, (n, ex, accs) in per_pattern.items():
        print(f"{name:12s} {ex:4d}/{n:<4d} {accs/n:8.1%}")
        total_n += n
        total_exact += ex
        total_acc += accs
    print("-" * 32)
    print(f"{'TOTAL':12s} {total_exact:4d}/{total_n:<4d} {total_acc/total_n:8.1%}"
          f"   ({dt:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
