#!/usr/bin/env python3
"""Quick eval of any combined-like module: all/train/holdout + miss list.

Usage: quick_eval.py <path> [VAR=value ...]   (float/int var overrides)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402

meta, caps = load_dataset()
DATA = [(f"{c['pattern']}_{c['rep']}", c["rep"], linearize(c["capture"]),
         bytes.fromhex(c["payload"])) for c in caps]


def load(path):
    spec = importlib.util.spec_from_file_location("cmb", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(m, tag):
    ok = tr = ho = 0
    miss = []
    refuse = []
    for name, rep, s, exp in DATA:
        d = m.decode(s, meta)
        good = (d == exp)
        ok += good
        if rep == 2:
            ho += good
        else:
            tr += good
        if not good:
            miss.append(name)
            if d is None:
                refuse.append(name)
    print(f"{tag:44s} all={ok}/54 train={tr}/36 holdout={ho}/18")
    print(f"    misses: {miss}")
    if refuse:
        print(f"    refused: {refuse}")
    return ok


if __name__ == "__main__":
    path = sys.argv[1]
    m = load(path)
    tag = Path(path).name
    for ov in sys.argv[2:]:
        k, v = ov.split("=", 1)
        try:
            val = int(v)
        except ValueError:
            val = float(v)
        setattr(m, k, val)
        tag += f" {k}={v}"
    run(m, tag)
