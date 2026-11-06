#!/usr/bin/env python3
"""Grid-tune the (5,6) preg estimator against the real pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402

meta, caps = load_dataset()
DATA = [(f"{c['pattern']}_{c['rep']}", c["rep"], linearize(c["capture"]),
         bytes.fromhex(c["payload"])) for c in caps]


def fresh():
    spec = importlib.util.spec_from_file_location(
        "combined", ROOT / "approaches" / "combined.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(m, tag):
    ok = tr = ho = 0
    miss = []
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
    print(f"{tag:26s} all={ok}/54 train={tr}/36 holdout={ho}/18  miss={miss}",
          flush=True)
    return ok


import itertools  # noqa: E402

for sig, w in itertools.product((35.0, 40.0, 45.0), (0.7, 1.0, 1.5, 2.0)):
    m = fresh()
    m.PREG_PRIOR_W = w
    orig = m._preg_boundary

    def patched(b, p0, p1, _s, span=m.EPS_CLAMP, _sig=sig, _orig=orig):
        return _orig(b, p0, p1, _sig, span)

    m._preg_boundary = patched
    run(m, f"sig={sig:.0f} w={w}")
