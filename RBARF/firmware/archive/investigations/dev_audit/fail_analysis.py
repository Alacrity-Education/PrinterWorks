#!/usr/bin/env python3
"""Adversarial audit: per-capture failure mechanism for combined.py."""
import sys
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


def bits_of(bs):
    return [(b >> (7 - i)) & 1 for b in bs for i in range(8)]


rows = []
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    best, q1 = cm._decode_full(samples, meta)
    if best is None:
        print(f"{name}: NO DECODE")
        continue
    got = best["payload"]
    ok = got == exp
    ebits = bits_of(exp)
    gbits = best["bits"][32:160]
    bad = [i for i in range(128) if ebits[i] != gbits[i]]
    rows.append((name, ok, bad, best))
    if ok:
        continue
    print(f"\n=== {name}  rep={c['rep']}  MISS  model={best['model']} "
          f"alias={best['alias']} kappa={best['kappa']:.6f} "
          f"tau={best['tau']:.1f} hits={best['hits']} "
          f"viol={best['violations']} infeas={best['infeasible']} "
          f"lab_err={best['label_err']} dead={best['dead_ct']} "
          f"h0c={best['h0c']:.1f} h1c={best['h1c']:.1f}")
    print(f"  exp={exp.hex()}")
    print(f"  got={got.hex()}")
    print(f"  wrong payload bits (0-127): {bad}  "
          f"(abs bit idx {[b + 32 for b in bad]})")
    seg = best["seg"]
    for b in bad:
        t = b + 32
        p = None
        for pp in seg:
            if pp["k0"] <= t < pp["k1"]:
                p = pp
                break
        if p is None:
            print(f"    bit{t}: NO PULSE covers it (hidden/merged region)")
            continue
        L = p["k1"] - p["k0"]
        off = t - p["k0"]
        print(f"    bit{t}: truth={ebits[b]} got={gbits[b]} "
              f"pulse k0={p['k0']} L={L} off={off} a_hat={p['a_hat']} "
              f"fam=({p['sfa']},{p['sfb']}) u={p['u']:.1f} v={p['v']:.1f} "
              f"width={p['v']-p['u']:.1f} nhigh={p['nhigh']} "
              f"cost={p['cost']:.3f} llr={best['llr'][t]:+.3f}")
        # dead-window test against the fitted widths
        h0, h1 = best["h0c"], best["h1c"]
        cand = []
        for a in range(0, L + 1):
            if a == 0:
                Hs = [h0]
            else:
                Hs = [(a - 1) * 1250.0 + h1]
                if a < L:
                    Hs.append(a * 1250.0 + h0)
            for H in Hs:
                cand.append((a, H, p["u"] < H <= p["v"]))
        ins = sorted(set(a for a, H, i in cand if i))
        print(f"       generators inside bracket -> a in {ins} "
              f"{'DEAD WINDOW' if len(ins) >= 2 else ''}")

n_ok = sum(1 for r in rows if r[1])
print(f"\nTOTAL exact {n_ok}/{len(rows)}")
print("\nmodel/alias usage:")
from collections import Counter  # noqa: E402
print(Counter((r[3]["model"], r[3]["alias"]) for r in rows))
print("misses:", [r[0] for r in rows if not r[1]])
print("dead_ct distribution:", sorted(r[3]["dead_ct"] for r in rows))
