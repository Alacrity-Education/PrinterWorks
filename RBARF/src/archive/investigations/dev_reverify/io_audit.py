#!/usr/bin/env python3
"""Log every filesystem open performed while decode() runs.

Patches builtins.open, io.open, os.open and Path.read_text/read_bytes
AFTER combined.py is imported (so module-import-time reads are recorded
separately from per-call reads), then decodes all 54 captures.
Any touch of a dataset file is a hard FAIL.
"""
import builtins
import io
import os
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

IMPORT_OPENS = []
DECODE_OPENS = []
SINK = IMPORT_OPENS

_open = builtins.open
_ioopen = io.open
_osopen = os.open
_prt = Path.read_text
_prb = Path.read_bytes


def rec(p):
    try:
        SINK.append(str(p))
    except Exception:
        SINK.append("<unprintable>")


def p_open(f, *a, **k):
    rec(f)
    return _open(f, *a, **k)


def p_ioopen(f, *a, **k):
    rec(f)
    return _ioopen(f, *a, **k)


def p_osopen(f, *a, **k):
    rec(f)
    return _osopen(f, *a, **k)


def p_rt(self, *a, **k):
    rec(self)
    return _prt(self, *a, **k)


def p_rb(self, *a, **k):
    rec(self)
    return _prb(self, *a, **k)


builtins.open = p_open
io.open = p_ioopen
os.open = p_osopen
Path.read_text = p_rt
Path.read_bytes = p_rb

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

# switch sink: everything from here on is per-decode-call IO
SINK = DECODE_OPENS

builtins.open = _open
io.open = _ioopen
os.open = _osopen
Path.read_text = _prt
Path.read_bytes = _prb
meta, caps = load_dataset()
builtins.open = p_open
io.open = p_ioopen
os.open = p_osopen
Path.read_text = p_rt
Path.read_bytes = p_rb

for c in caps:
    cm.decode(linearize(c["capture"]), meta)

builtins.open = _open
io.open = _ioopen
os.open = _osopen
Path.read_text = _prt
Path.read_bytes = _prb

print("=== opens during module import (import-time constants) ===")
for p in IMPORT_OPENS:
    print("   ", p)
if not IMPORT_OPENS:
    print("    <none>")
print(f"\n=== opens during 54 decode() calls ===")
for p in sorted(set(DECODE_OPENS)):
    print(f"    {DECODE_OPENS.count(p):4d}x  {p}")
if not DECODE_OPENS:
    print("    <none>")

allp = IMPORT_OPENS + DECODE_OPENS
bad = [p for p in allp
       if "captures" in p or "/data/" in p.replace("\\", "/")]
print("\nDATASET TOUCHES:", bad if bad else "none")
print("VERDICT:", "FAIL - decoder touched dataset" if bad
      else "PASS - decoder never opened a dataset file")
