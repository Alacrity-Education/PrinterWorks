#!/usr/bin/env python3
"""Which gate catches the corrupted captures? Counterfactual on the
truncation knife gate (TRUNC_KNIFE_LLR -> 0 disables it)."""
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
BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
TARGETS = ["rnd1_0", "ones_0", "zeros_1", "aa_2", "dense_1"]


def drop_loops(s, n, renum):
    return [(i - n if renum else i, sl, v) for (i, sl, v) in s if i >= n]


def acc(d, e):
    return 0.0 if d is None else sum(
        1 for a, b in zip(d, e) if a == b) / max(len(e), len(d))


for name in TARGETS:
    c = BY[name]
    s0 = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    print(f"\n=== {name} ===")
    for n, renum in [(1, False), (2, False), (2, True), (5, False),
                     (5, True)]:
        s = drop_loops(s0, n, renum)
        best, _ = cm._decode_full(s, meta)
        stats = (f"viol={best['violations']} infeas={best['infeasible']} "
                 f"laberr={best['label_err']} cover0={best['cover0']} "
                 f"knife_open={best['knife_open']}")
        d_on = cm.decode(s, meta)
        cm.TRUNC_KNIFE_LLR = 0.0          # disable ONLY the new gate
        d_off = cm.decode(s, meta)
        cm.TRUNC_KNIFE_LLR = 2.0
        def tag(d):
            return ("None" if d is None
                    else ("EXACT" if d == exp else f"WRONG({acc(d,exp):.1%})"))
        print(f"  drop {n} {'renum' if renum else 'keep '}: "
              f"gate_ON={tag(d_on):14s} gate_OFF={tag(d_off):14s}  {stats}")
