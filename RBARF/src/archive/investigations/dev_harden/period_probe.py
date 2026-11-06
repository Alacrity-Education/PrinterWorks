#!/usr/bin/env python3
"""Measure payload byte-period agreement (lag 8 / lag 16) per capture over
confidently decoded bits -- the gate statistic for the knife vote."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

meta, caps = load_dataset()

print(f"{'capture':ekp14s}" if False else f"{'capture':14s} "
      f"{'A8':>12s} {'A16':>12s}")
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        print(f"{name:14s} REFUSED")
        continue
    llr = best["llr"]
    bits = best["bits"]
    out = []
    for lag in (8, 16):
        n = a = 0
        for t in range(32, 160 - lag):
            s = t + lag
            # exclude weakly decided bits on either side
            if abs(llr[t]) < 1.0 or abs(llr[s]) < 1.0:
                continue
            n += 1
            a += (bits[t] == bits[s])
        out.append((n, a))
    (n8, a8), (n16, a16) = out
    print(f"{name:14s} {a8:4d}/{n8:<4d}={a8/max(n8,1):.3f} "
          f"{a16:4d}/{n16:<4d}={a16/max(n16,1):.3f}")
