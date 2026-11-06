"""Independent check: rebuild every sample level straight from
fitted_model.json + the dataset, with no reuse of the fitting code."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import harness                                            # noqa: E402

M = json.load(open(Path(__file__).parent / "fitted_model.json"))
LOOP = M["loop_ns"]
O = np.array(M["slot_offsets_ns"])
W = np.array(M["branch_cost_ns"])
H1, H0 = M["eff_high_1_ns"], M["eff_high_0_ns"]

meta, caps = harness.load_dataset()
tot = good = 0
worst = (2.0, None)
for c in caps:
    key = f"{c['pattern']}_{c['rep']}"
    p = M["per_capture"][key]
    t0, eps = p["t0_ns"], p["eps"]
    s = harness.linearize(c["capture"])
    it = np.array([x[0] for x in s], float)
    sl = np.array([x[1] for x in s])
    lv = np.array([x[2] for x in s])
    # cumulative HIGH count per slot, strictly before each sample
    C = np.zeros((len(s), 8))
    run = np.zeros(8)
    for m in range(len(s)):
        C[m] = run
        run[sl[m]] += lv[m]
    A = it * LOOP + O[sl] + C @ W
    t = t0 + A / (1.0 + eps)
    frame = bytes.fromhex(c["frame"])
    bits = np.array([(b >> (7 - j)) & 1 for b in frame for j in range(8)])
    k = np.floor(t / 1250.0).astype(np.int64)
    inside = (k >= 0) & (k < len(bits))
    kk = np.clip(k, 0, len(bits) - 1)
    hw = np.where(bits[kk] == 1, H1, H0)
    pred = (inside & ((t - kk * 1250.0) < hw)).astype(int)
    g = int((pred == lv).sum())
    good += g
    tot += len(lv)
    if g / len(lv) < worst[0]:
        worst = (g / len(lv), key)
print(f"samples {tot}, agree {good}  -> {100*good/tot:.4f}%")
print(f"worst capture: {worst[1]} {100*worst[0]:.4f}%")
print(f"json says      {100*M['agreement_rate']:.4f}%")
