#!/usr/bin/env python3
"""Append the measured trim->eps table into data/captures_trim.json meta."""

import json
from pathlib import Path
from statistics import mean, pstdev

HERE = Path(__file__).parent
DATA = HERE.parent.parent.parent / "data" / "captures_trim.json"

results = json.loads((HERE / "results.json").read_text())
by_trim = {}
for r in results:
    by_trim.setdefault(r["trim"], []).append(r)

SIGNED = {0: 0, 1: 1, 2: 2, 3: 3, 4: -4, 5: -3, 6: -2, 7: -1}

table = {}
for t in sorted(by_trim):
    es = [r["eps_align"] for r in by_trim[t]]
    sp = [r["eps_span"] for r in by_trim[t]]
    table[str(t)] = {
        "signed_value": SIGNED[t],
        "eps_mean": round(mean(es), 6),
        "eps_sd": round(pstdev(es), 6),
        "eps_min": round(min(es), 6),
        "eps_max": round(max(es), 6),
        "eps_span_method_mean": round(mean(sp), 6),
        "n": len(es),
    }

d = json.loads(DATA.read_text())
d["meta"]["trim_eps_table"] = table
d["meta"]["trim_eps_notes"] = (
    "eps = relative HSI frequency error vs nominal 16 MHz, measured per "
    "capture by (t0,eps) alignment against the calibrated sampler model "
    "(synth.py constants), cross-checked with a frame-span estimate "
    "(first rise -> last fall = 191*1250+752 ns). Mapping is SIGNED "
    "3-bit two's complement: codes 0..3 = +0..+3 steps (each step "
    "LOWERS frequency ~1.16%), codes 4..7 = -4..-1 steps (raise it). "
    "Strictly monotonic in signed order 4,5,6,7,0,1,2,3; non-monotonic "
    "in unsigned code order (wraparound jump +8.1% between codes 3 and "
    "4). Factory (code 0) = -1.07% on this unit; code 7 (-1 step) "
    "best cancels it at +0.02%. Full authority -4.38%..+3.73%. "
    "See recon/TRIM_SWEEP.md."
)
DATA.write_text(json.dumps(d, indent=1))
print("meta updated:")
for t, row in table.items():
    print(f"  trim {t} (v={row['signed_value']:+d}): "
          f"{row['eps_mean'] * 100:+.4f}% +/- {row['eps_sd'] * 100:.4f}%")
