#!/usr/bin/env python3
"""Portability-audit ablations of combined.py (constants mutated in memory
only; combined.py untouched).  Measures what each host-only mechanism is
worth so the embedded port can drop/adapt with known cost.
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
    print(f"{label:46s} all {len(ex):2d}/54  holdout {len(ho):2d}/18"
          f"  miss={sorted(miss)}", flush=True)
    return len(ex)


print("--- baseline ---")
run("baseline (as shipped)")

print("\n--- dual-model arbitration ---")
orig_models = cm.MODELS
cm.MODELS = (orig_models[1],)          # fitted integer-cycle model only
run("single model: fit only")
cm.MODELS = (orig_models[0],)
run("single model: cal only")
cm.MODELS = orig_models

print("\n--- per-slot probit widths WE ---")
orig_we = cm.WE
cm.WE = (28.0,) * 8                    # flat = mean-ish width
run("WE flat 28ns (no per-slot widths)")
cm.WE = orig_we

print("\n--- per-slot offsets psi ---")
orig_shrink = cm.PSI_SHRINK
cm.PSI_SHRINK = 1e-9                   # shrinkage forces psi == 0
run("psi fit disabled (PSI_SHRINK->0)")
cm.PSI_SHRINK = orig_shrink

print("\n--- per-family boundary eps ---")
orig_eps = cm.EPS_CLAMP
cm.EPS_CLAMP = 0.0
run("eps fit disabled (EPS_CLAMP=0)")
cm.EPS_CLAMP = orig_eps

print("\n--- byte-period votes ---")
orig_dv = cm.DEAD_VOTE_MIN
cm.DEAD_VOTE_MIN = 99
run("dead-window vote disabled")
orig_kp = cm.KNIFE_PERIOD_MIN
cm.KNIFE_PERIOD_MIN = 2.0
run("dead + knife votes disabled")
cm.DEAD_VOTE_MIN = orig_dv
run("knife vote only disabled")
cm.KNIFE_PERIOD_MIN = orig_kp

print("\n--- self-training second pass ---")
orig_td = cm._try_decode
cm._try_decode = lambda seg, model, self_train=True: orig_td(
    seg, model, False)
run("self-training disabled")
cm._try_decode = orig_td

print("\n--- repair retries / aliases ---")
orig_rr = cm.REPAIR_MAX_ROUNDS
cm.REPAIR_MAX_ROUNDS = 0
run("repair retries disabled")
cm.REPAIR_MAX_ROUNDS = orig_rr
orig_na = cm.N_ALIAS
cm.N_ALIAS = 1
run("alias candidates N_ALIAS=1")
cm.N_ALIAS = orig_na

print("\n--- combined embedded-shaped drop set ---")
cm.MODELS = (orig_models[1],)
cm.WE = (28.0,) * 8
cm.PSI_SHRINK = 1e-9
cm.N_ALIAS = 1
cm.REPAIR_MAX_ROUNDS = 0
run("fit-only + flat WE + no psi + 1 alias")
cm.DEAD_VOTE_MIN = 99
cm.KNIFE_PERIOD_MIN = 2.0
run("... + votes disabled")
cm._try_decode = lambda seg, model, self_train=True: orig_td(
    seg, model, False)
run("... + self-train disabled")
cm.EPS_CLAMP = 0.0
run("... + eps disabled (full drop set)")
