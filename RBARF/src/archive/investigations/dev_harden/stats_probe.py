#!/usr/bin/env python3
"""Measure the winning result's quality stats on all 54 clean captures
(gate calibration) and on corrupted variants (gate separation)."""
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

print(f"{'capture':14s} {'ok':>2s} {'viol':>4s} {'infeas':>6s} {'laberr':>6s} "
      f"{'labunc':>6s} {'dead':>4s} {'cost':>9s} {'slip':>4s} {'cov0':>4s}")
mx = dict(viol=0, infeas=0, laberr=0, cost=0.0)
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        print(f"{name:14s} REFUSED")
        continue
    ok = best["payload"] == exp
    cov0 = best["seg"][0]["k0"] if best["seg"] else -1
    print(f"{name:14s} {'Y' if ok else 'N':>2s} {best['violations']:4d} "
          f"{best['infeasible']:6d} {best['label_err']:6d} "
          f"{best['lab_unc']:6d} {best['dead_ct']:4d} "
          f"{best['total_cost']:9.2f} {best.get('slip0', 0):4d} {cov0:4d}")
    mx["viol"] = max(mx["viol"], best["violations"])
    mx["infeas"] = max(mx["infeas"], best["infeasible"])
    mx["laberr"] = max(mx["laberr"], best["label_err"])
    mx["cost"] = max(mx["cost"], best["total_cost"])
print("\nclean maxima:", mx)

# corrupted variants: dropped loops (keep / renumber) and single flips
import random  # noqa: E402


def drop_loops(samples, n, renumber):
    return [(i - n if renumber else i, s, v)
            for (i, s, v) in samples if i >= n]


def isolated_positions(samples, k, seed):
    rng = random.Random(seed)
    cand = [m for m in range(1, len(samples) - 1)
            if samples[m - 1][2] == samples[m + 1][2] == samples[m][2]
            and samples[m][0] < 100]
    return sorted(rng.sample(cand, k))


TARGETS = ["rnd1_0", "ones_0", "zeros_1", "aa_2", "dense_1"]
BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
print(f"\n{'case':44s} {'ok':>3s} {'viol':>4s} {'infeas':>6s} {'laberr':>6s} "
      f"{'cost':>9s} {'slip':>4s} {'cov0':>4s}")
for name in TARGETS:
    c = BY[name]
    s0 = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    variants = [
        ("drop2_keep", drop_loops(s0, 2, False)),
        ("drop2_renum", drop_loops(s0, 2, True)),
        ("drop1_keep", drop_loops(s0, 1, False)),
        ("drop5_keep", drop_loops(s0, 5, False)),
    ]
    pos = isolated_positions(s0, 3, seed=20260905)
    sf = list(s0)
    for m in pos:
        i, sl, v = sf[m]
        sf[m] = (i, sl, 1 - v)
    variants.append(("flip3", sf))
    for m in pos:
        s1 = list(s0)
        i, sl, v = s1[m]
        s1[m] = (i, sl, 1 - v)
        variants.append((f"flip1@{m}", s1))
    for tag, sv in variants:
        best, _ = cm._decode_full(sv, meta)
        if best is None:
            print(f"{name+'/'+tag:44s} REFUSED")
            continue
        ok = best["payload"] == exp
        cov0 = best["seg"][0]["k0"] if best["seg"] else -1
        print(f"{name+'/'+tag:44s} {'Y' if ok else 'N':>3s} "
              f"{best['violations']:4d} {best['infeasible']:6d} "
              f"{best['label_err']:6d} {best['total_cost']:9.2f} "
              f"{best.get('slip0', 0):4d} {cov0:4d}")
