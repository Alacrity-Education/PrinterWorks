#!/usr/bin/env python3
"""Byte-exact determinism: decode every capture, dump hex per capture."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

meta, caps = load_dataset()
for c in caps:
    s = linearize(c["capture"])
    d = cm.decode(s, meta)
    print(f"{c['pattern']}_{c['rep']}\t{'None' if d is None else d.hex()}")
