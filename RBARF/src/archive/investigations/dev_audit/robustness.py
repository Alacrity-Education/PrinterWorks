#!/usr/bin/env python3
"""Robustness probe: prefix deletion and isolated single-sample flips."""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "approaches"))
from harness import load_dataset, linearize  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "combined", ROOT / "approaches" / "combined.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

meta, caps = load_dataset()
BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
TARGETS = ["rnd1_0", "ones_0", "zeros_1", "aa_2", "dense_1"]


def bacc(d, e):
    if d is None:
        return 0.0
    return sum(1 for a, b in zip(d, e) if a == b) / max(len(e), len(d))


def report(tag, d, exp):
    ok = (d == exp)
    print(f"    {tag:38s} {'OK ' if ok else 'BREAK'} "
          f"byte-acc {bacc(d, exp):6.1%}"
          f"{'' if d is None else '  ' + d.hex()}")
    return ok


def drop_loops(samples, n, renumber):
    out = [(i - n if renumber else i, s, v)
           for (i, s, v) in samples if i >= n]
    return out


def isolated_positions(samples, k, seed):
    """k sample indices whose two neighbours share the opposite level
    (a flip there creates a 1-sample glitch)."""
    rng = random.Random(seed)
    cand = [m for m in range(1, len(samples) - 1)
            if samples[m - 1][2] == samples[m + 1][2] == samples[m][2]
            and samples[m][0] < 100]        # inside the frame window
    return sorted(rng.sample(cand, k))


for name in TARGETS:
    c = BY[name]
    s0 = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    print(f"\n=== {name} ({len(s0)} samples) ===")
    report("unperturbed", cm.decode(s0, meta), exp)

    report("drop first 2 loops (keep iter index)",
           cm.decode(drop_loops(s0, 2, False), meta), exp)
    report("drop first 2 loops (renumber i-2)",
           cm.decode(drop_loops(s0, 2, True), meta), exp)
    report("drop first 1 loop (keep iter index)",
           cm.decode(drop_loops(s0, 1, False), meta), exp)
    report("drop first 5 loops (keep iter index)",
           cm.decode(drop_loops(s0, 5, False), meta), exp)

    pos = isolated_positions(s0, 3, seed=20260905)
    sf = list(s0)
    for m in pos:
        i, sl, v = sf[m]
        sf[m] = (i, sl, 1 - v)
    lv = [s0[m][2] for m in pos]
    report(f"flip 3 isolated samples {pos} (lvl {lv})",
           cm.decode(sf, meta), exp)

    # each flip individually, to localize
    for m in pos:
        s1 = list(s0)
        i, sl, v = s1[m]
        s1[m] = (i, sl, 1 - v)
        report(f"  flip only idx {m} (it={i} slot={sl} {v}->{1-v})",
               cm.decode(s1, meta), exp)
