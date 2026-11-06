#!/usr/bin/env python3
"""What label pool predicts a capture's payload dead-window truth?

Per capture and family: (a) all marker-labelled class counts, (b) counts
restricted to marker-labelled pulses whose own window is dead (both
generators interior), vs (c) the payload dead windows' truth."""
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


rows = []
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    h0c, h1c = best["h0c"], best["h1c"]
    seg = best["seg"]
    # marker labels (same rule as _try_decode)
    forced = []
    for p in seg:
        k0, k1 = p["k0"], p["k1"]
        if k1 > 192 or any(cm.KNOWN[t] < 0 for t in range(k0, k1)):
            continue
        amin, amax = cm._a_bounds(k0, k1)
        if amin == amax:
            forced.append((p, amin))
    forced_ids = {id(p) for p, _ in forced}
    # all-label class counts per family
    all_cnt = defaultdict(lambda: [0, 0])
    dead_cnt = defaultdict(lambda: [0, 0])   # labelled dead: [chose-small, chose-large]
    for (p, a) in forced:
        li = cm._label_interval(p, a, h0c, h1c)
        if li is None:
            continue
        fam = (p["sfa"], p["sfb"])
        all_cnt[fam][li[0]] += 1
        ins = interior_as(p, h0c, h1c)
        if len(ins) >= 2:
            # truth relative to the tie: smaller or larger hypothesis?
            if a == ins[0]:
                dead_cnt[fam][0] += 1
            elif a in ins[1:]:
                dead_cnt[fam][1] += 1
    # payload dead windows and their truth
    pay_dead = defaultdict(lambda: [0, 0])
    for p in seg:
        if id(p) in forced_ids or p["k0"] >= 192:
            continue
        ins = interior_as(p, h0c, h1c)
        if len(ins) >= 2:
            a_true = 0
            for t in range(p["k0"], min(p["k1"], 192)):
                if tb[t]:
                    a_true += 1
                else:
                    break
            fam = (p["sfa"], p["sfb"])
            if a_true == ins[0]:
                pay_dead[fam][0] += 1
            else:
                pay_dead[fam][1] += 1
    for fam in sorted(set(all_cnt) | set(pay_dead)):
        if pay_dead.get(fam, [0, 0]) == [0, 0]:
            continue
        rows.append((name, fam, all_cnt.get(fam, [0, 0]),
                     dead_cnt.get(fam, [0, 0]), pay_dead[fam]))

print(f"{'capture':14s} {'fam':7s} {'lab all 0/1':>12s} "
      f"{'lab dead s/l':>13s} {'PAYLOAD dead s/l':>17s}")
for name, fam, ac, dc, pd in rows:
    print(f"{name:14s} {str(fam):7s} {ac[0]:5d}/{ac[1]:<5d} "
          f"{dc[0]:6d}/{dc[1]:<6d} {pd[0]:8d}/{pd[1]:<8d}")
