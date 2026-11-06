#!/usr/bin/env python3
"""Strict re-verification of the robustness probes.

Classifies every perturbed decode as EXACT / REFUSE(None) / WRONG.
PASS criterion: no WRONG anywhere. A confident wrong payload is a FAIL.
Same perturbations as dev_audit/robustness.py, same seed.
"""
import random
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
BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
TARGETS = ["rnd1_0", "ones_0", "zeros_1", "aa_2", "dense_1"]

RESULTS = []


def classify(tag, cap, d, exp):
    if d is None:
        v = "REFUSE"
    elif bytes(d) == exp:
        v = "EXACT"
    else:
        v = "WRONG"
    acc = 0.0 if d is None else sum(
        1 for a, b in zip(d, exp) if a == b) / max(len(exp), len(d))
    RESULTS.append((cap, tag, v, acc, None if d is None else bytes(d).hex()))
    print(f"    {tag:44s} {v:6s} acc {acc:6.1%} "
          f"{'<None>' if d is None else d.hex()}")
    return v


def drop_loops(samples, n, renumber):
    return [(i - n if renumber else i, s, v)
            for (i, s, v) in samples if i >= n]


def isolated_positions(samples, k, seed):
    rng = random.Random(seed)
    cand = [m for m in range(1, len(samples) - 1)
            if samples[m - 1][2] == samples[m + 1][2] == samples[m][2]
            and samples[m][0] < 100]
    return sorted(rng.sample(cand, k))


for name in TARGETS:
    c = BY[name]
    s0 = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    print(f"\n=== {name} ({len(s0)} samples) ===")
    classify("unperturbed", name, cm.decode(s0, meta), exp)

    for n, renum in [(1, False), (1, True), (2, False), (2, True),
                     (5, False), (5, True)]:
        tag = f"drop first {n} loop(s) ({'renumber' if renum else 'keep idx'})"
        classify(tag, name, cm.decode(drop_loops(s0, n, renum), meta), exp)

    pos = isolated_positions(s0, 3, seed=20260905)
    sf = list(s0)
    for m in pos:
        i, sl, v = sf[m]
        sf[m] = (i, sl, 1 - v)
    classify(f"flip 3 isolated {pos}", name, cm.decode(sf, meta), exp)

    for m in pos:
        s1 = list(s0)
        i, sl, v = s1[m]
        s1[m] = (i, sl, 1 - v)
        classify(f"  flip only idx {m} (it={i} sl={sl} {v}->{1-v})",
                 name, cm.decode(s1, meta), exp)

print("\n" + "=" * 70)
n_exact = sum(1 for r in RESULTS if r[2] == "EXACT")
n_ref = sum(1 for r in RESULTS if r[2] == "REFUSE")
wrong = [r for r in RESULTS if r[2] == "WRONG"]
print(f"cases={len(RESULTS)}  EXACT={n_exact}  REFUSE={n_ref}  "
      f"WRONG={len(wrong)}")
for r in wrong:
    print(f"  WRONG: {r[0]} / {r[1]} acc={r[3]:.1%} {r[4]}")
print("VERDICT:", "PASS (no confident wrong payload)" if not wrong
      else "FAIL (confident wrong payload returned)")
