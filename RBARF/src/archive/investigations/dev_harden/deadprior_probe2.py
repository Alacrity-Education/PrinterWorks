#!/usr/bin/env python3
"""Class mix of CONFIDENT same-capture (7,0)-family pulses (marker labels +
payload pulses decided with |llr| >= thresh, dead windows excluded) vs the
truth of the capture's payload dead windows."""
import sys
from collections import defaultdict
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
HDR = cm._bits_of(cm.HDR)
TRL = cm._bits_of(cm.TRL)


def interior_as(p, h0c, h1c):
    L = p["k1"] - p["k0"]
    u, v = p["u"], p["v"]
    ins = []
    for a in range(0, L + 1):
        Hs = [h0c] if a == 0 else (
            [(a - 1) * 1250.0 + h1c] + ([a * 1250.0 + h0c] if a < L else []))
        if any(u < H <= v for H in Hs):
            ins.append(a)
    return ins


print(f"{'capture':14s} {'conf 0/1 (L=1)':>15s} {'conf 0/1 (all)':>15s} "
      f"{'PAYLOAD dead truth s/l':>22s}")
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    h0c, h1c = best["h0c"], best["h1c"]
    seg = best["seg"]
    llr = best["llr"]
    conf1 = [0, 0]
    confa = [0, 0]
    pay_dead = [0, 0]
    dead_us = []
    for p in seg:
        if p["k0"] >= 192:
            continue
        fam = (p["sfa"], p["sfb"])
        if fam != (7, 0):
            continue
        L = p["k1"] - p["k0"]
        ins = interior_as(p, h0c, h1c)
        a_true = 0
        for t in range(p["k0"], min(p["k1"], 192)):
            if tb[t]:
                a_true += 1
            else:
                break
        forced = not any(cm.KNOWN[t] < 0
                         for t in range(p["k0"], min(p["k1"], 192)))
        if len(ins) >= 2 and not forced:
            pay_dead[0 if a_true == ins[0] else 1] += 1
            dead_us.append(round(p["u"], 1))
            continue
        # confident: marker-forced, or decided with margin
        t = p["k0"] + max(p["a_hat"] - 1, 0)
        t = min(max(t, p["k0"]), min(p["k1"], 192) - 1)
        if forced or abs(llr[t]) >= 1.0:
            cls = 1 if p["a_hat"] > 0 else 0
            confa[cls] += 1
            if L == 1:
                conf1[cls] += 1
    if pay_dead == [0, 0]:
        continue
    print(f"{name:14s} {conf1[0]:6d}/{conf1[1]:<7d} {confa[0]:6d}/{confa[1]:<7d} "
          f"{pay_dead[0]:9d}/{pay_dead[1]:<9d} dead_u={dead_us}")
