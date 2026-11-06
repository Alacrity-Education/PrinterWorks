#!/usr/bin/env python3
"""Is the (5,6)-family knife edge really an information limit?

Collect every L=1 pulse in every capture, tag it with ground truth (audit
only -- the decoder never sees this), and ask whether a per-capture or
global threshold on the fall-bracket statistic separates 0 from 1.
"""
import sys
from collections import defaultdict
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

HDR = cm._bits_of(cm.HDR)
TRL = cm._bits_of(cm.TRL)


def truth_bits(payload_hex):
    pay = bytes.fromhex(payload_hex)
    return HDR + cm._bits_of(pay) + TRL


byfam = defaultdict(list)     # fam -> [(u, v, cls, capname, k0, forced)]
percap = defaultdict(list)
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = truth_bits(c["payload"])
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    for p in best["seg"]:
        L = p["k1"] - p["k0"]
        if L != 1 or p["k0"] >= 192:
            continue
        cls = tb[p["k0"]]
        fam = (p["sfa"], p["sfb"])
        forced = cm.KNOWN[p["k0"]] >= 0
        byfam[fam].append((p["u"], p["v"], cls, name, p["k0"], forced))
        percap[(name, fam)].append((p["u"], cls, p["k0"], forced))

print(f"{'fam':8s} {'n':>5s} {'n0':>5s} {'n1':>5s} "
      f"{'max u|cls0':>11s} {'min u|cls1':>11s} {'sep':>8s} {'gapwidth':>9s}")
for fam in sorted(byfam):
    rows = byfam[fam]
    u0 = [r[0] for r in rows if r[2] == 0]
    u1 = [r[0] for r in rows if r[2] == 1]
    w = sum(r[1] - r[0] for r in rows) / len(rows)
    if u0 and u1:
        sep = min(u1) - max(u0)
        print(f"{str(fam):8s} {len(rows):5d} {len(u0):5d} {len(u1):5d} "
              f"{max(u0):11.1f} {min(u1):11.1f} {sep:8.1f} {w:9.1f}"
              f"{'   OVERLAP' if sep <= 0 else ''}")
    else:
        print(f"{str(fam):8s} {len(rows):5d} {len(u0):5d} {len(u1):5d} "
              f"{'-':>11s} {'-':>11s} {'-':>8s} {w:9.1f}   single-class")

print("\n--- per-capture oracle threshold on u, family (5,6) ---")
tot_err = 0
tot_n = 0
worst = []
for (name, fam), rows in sorted(percap.items()):
    if fam != (5, 6):
        continue
    u0 = [r[0] for r in rows if r[1] == 0]
    u1 = [r[0] for r in rows if r[1] == 1]
    n = len(rows)
    tot_n += n
    if not u0 or not u1:
        continue
    # best single threshold (oracle)
    cands = sorted(r[0] for r in rows)
    best_e = None
    for i in range(len(cands) + 1):
        th = (cands[i - 1] + cands[i]) / 2 if 0 < i < len(cands) else (
            cands[0] - 1 if i == 0 else cands[-1] + 1)
        e = sum(1 for u, cl, k, f in rows
                if (0 if u <= th else 1) != cl)
        if best_e is None or e < best_e:
            best_e = e
    tot_err += best_e
    if best_e:
        worst.append((name, best_e, n, max(u0), min(u1)))
print(f"family (5,6) L=1 pulses: {tot_n}; "
      f"residual errors under per-capture ORACLE threshold: {tot_err}")
for w in worst:
    print(f"   {w[0]}: {w[1]} err / {w[2]} pulses  max u|0={w[3]:.1f} "
          f"min u|1={w[4]:.1f}")

print("\n--- global oracle threshold on u, family (5,6) ---")
rows = byfam[(5, 6)]
cands = sorted(set(r[0] for r in rows))
best = None
for th in cands:
    e = sum(1 for u, v, cl, n, k, f in rows if (0 if u <= th else 1) != cl)
    if best is None or e < best[0]:
        best = (e, th)
print(f"best global threshold {best[1]:.1f} -> {best[0]} errors / {len(rows)}")

print("\n--- does nhigh / rise-phase add information? (5,6), near boundary ---")
near = [r for r in rows if 360.0 <= r[0] <= 400.0]
print(f"{len(near)} pulses with u in [360,400]: "
      f"{sum(1 for r in near if r[2]==0)} zeros / "
      f"{sum(1 for r in near if r[2]==1)} ones")
for r in sorted(near, key=lambda r: r[0])[:60]:
    print(f"   u={r[0]:7.1f} v={r[1]:7.1f} cls={r[2]} {r[3]:12s} k0={r[4]}"
          f"{'  [marker]' if r[5] else ''}")
