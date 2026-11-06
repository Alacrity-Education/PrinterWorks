"""Where does the fixed-linear-time-base model fail? Per-capture and
per-position residual structure, plus a *local* phase-track diagnostic.
"""
import json, sys
from collections import Counter
import model as M
from fit_slots import score_cap, FRAME_NS, fit_cap

fit = json.load(open("slotfit.json"))
o = fit["o"]
meta, D = M.load()

print("per-capture in-frame agreement (global linear fit):")
rows = []
for d, (phi, k) in zip(D, fit["nuis"]):
    ok, n = score_cap(d["bits"], d["idx"], d["obs"], o, k, phi)
    rows.append((ok / n, d["pattern"], d["rep"], phi, k, n))
rows.sort()
for r in rows:
    print(f"  {r[0]:.3f} {r[1]:12s} r{r[2]}  phi={r[3]:7.1f} k={r[4]:.5f} n={r[5]}")

# residual vs loop index for the worst and best capture
print("\nmismatch count vs loop-index decile, worst 3 captures:")
for acc, pat, rep, phi, k, n in rows[:3]:
    d = next(x for x in D if x["pattern"] == pat and x["rep"] == rep)
    per = Counter()
    for (i, s), v in zip(d["idx"], d["obs"]):
        t = phi + k * (i * M.L_NOM + o[s])
        if not (-200 <= t < FRAME_NS + 200):
            continue
        if M.level_at(d["bits"], t) != v:
            per[i // 10] += 1
    print(f"  {pat} r{rep}: {sorted(per.items())}")
