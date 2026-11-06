#!/usr/bin/env python3
"""Independent ablation of the hardening mechanisms + psi-clamp check.

Mutates module-level constants in memory only (combined.py untouched).
"""
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
DATA = [(f"{c['pattern']}_{c['rep']}", linearize(c["capture"]),
         bytes.fromhex(c["payload"]), c["rep"]) for c in caps]


def run(label):
    ex = []
    miss = []
    for name, s, exp, rep in DATA:
        d = cm.decode(s, meta)
        (ex if d == exp else miss).append(name)
    ho = [n for n, s, e, r in DATA if r == 2 and n in ex]
    print(f"{label:44s} all {len(ex):2d}/54   holdout {len(ho):2d}/18"
          f"   miss={sorted(miss)}")
    return len(ex), sorted(miss)


print("--- baseline ---")
base = run("baseline (as shipped)")

print("\n--- knife-bit byte-period vote ---")
o = cm.KNIFE_PERIOD_MIN
cm.KNIFE_PERIOD_MIN = 2.0          # gate can never pass -> vote off
run("vote DISABLED (KNIFE_PERIOD_MIN=2.0)")
cm.KNIFE_PERIOD_MIN = 0.0          # gate always passes -> ungated vote
run("vote UNGATED (KNIFE_PERIOD_MIN=0.0)")
cm.KNIFE_PERIOD_MIN = o

print("\n--- periodicity gate margin sweep ---")
for v in (0.90, 0.95, 0.97, 0.99, 0.995, 1.0):
    cm.KNIFE_PERIOD_MIN = v
    run(f"KNIFE_PERIOD_MIN={v}")
cm.KNIFE_PERIOD_MIN = o

print("\n--- TIE_NATS plateau ---")
o2 = cm.TIE_NATS
for v in (0.0, 0.05, 0.10, 0.15, 0.20):
    cm.TIE_NATS = v
    run(f"TIE_NATS={v}")
cm.TIE_NATS = o2

print("\n--- KNIFE_LLR sweep ---")
o3 = cm.KNIFE_LLR
for v in (0.5, 0.7, 0.9, 1.1, 1.3):
    cm.KNIFE_LLR = v
    run(f"KNIFE_LLR={v}")
cm.KNIFE_LLR = o3

print("\n--- psi clamp hits on the 54 winners ---")
tot = 0
for name, s, exp, rep in DATA:
    best, _ = cm._decode_full(s, meta)
    pc = best["psi_clamped"]
    ko = best["knife_open"]
    c0 = best["cover0"]
    tot += pc
    if pc or c0:
        print(f"    {name}: psi_clamped={pc} cover0={c0} knife_open={ko}")
print(f"    total psi_clamped across 54 winners = {tot}")
print("\n--- clean-capture gate stats (refusal-gate calibration) ---")
mx = {}
for name, s, exp, rep in DATA:
    best, _ = cm._decode_full(s, meta)
    for k in ("violations", "infeasible", "label_err", "cover0",
              "knife_open"):
        mx[k] = max(mx.get(k, 0), best[k])
print("    max over 54 clean captures:", mx)
print("    gates:", dict(VIOL=cm.GATE_VIOL, INFEAS=cm.GATE_INFEAS,
                         LABERR=cm.GATE_LABERR, COVER=cm.GATE_COVER,
                         TRUNC_KNIFE_LLR=cm.TRUNC_KNIFE_LLR))
