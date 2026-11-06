#!/usr/bin/env python3
"""Truncation sweep across ALL 18 patterns (rep 0), drops of 1/2/5 loops.
Any confident WRONG payload is a FAIL."""
import importlib.util
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

meta, caps = load_dataset()


def drop_loops(s, n):
    return [(i, sl, v) for (i, sl, v) in s if i >= n]


tally = Counter()
wrong = []
print(f"{'capture':14s} " + "  ".join(f"drop{n}" for n in (1, 2, 5)))
for c in caps:
    if c["rep"] != 0:
        continue
    name = f"{c['pattern']}_{c['rep']}"
    s0 = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    row = []
    for n in (1, 2, 5):
        d = cm.decode(drop_loops(s0, n), meta)
        if d is None:
            v = "REFUSE"
        elif d == exp:
            v = "EXACT "
        else:
            v = "WRONG "
            wrong.append((name, n, d.hex()))
        tally[v.strip()] += 1
        row.append(v)
    print(f"{name:14s} " + "  ".join(row))

print("\n" + "=" * 60)
print("tally:", dict(tally))
for w in wrong:
    print("  WRONG:", w)
print("VERDICT:", "PASS (no confident wrong payload under truncation)"
      if not wrong else "FAIL")
