#!/usr/bin/env python3
"""Two audit questions:
 (a) Is DEAD_PRIOR_NATS (prior FOR fewer ones) correctly signed?  Measure
     the truth distribution of pulses the decoder actually flags dead.
 (b) Did _fit_family_eps fire for family (5,6) in the captures that fail?
"""
import sys
from collections import Counter, defaultdict
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

# instrument _fit_family_eps to record what it returned
_orig = cm._fit_family_eps
LAST = {}


def spy(seg, labelled, h0c, h1c, psi):
    r = _orig(seg, labelled, h0c, h1c, psi)
    LAST["eps"] = dict(r)
    LAST["psi"] = list(psi)
    LAST["h"] = (h0c, h1c)
    return r


cm._fit_family_eps = spy

dead_truth = Counter()
dead_by_fam = defaultdict(Counter)
rows = []
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    exact = best["payload"] == bytes.fromhex(c["payload"])
    eps = LAST.get("eps", {})
    h0c, h1c = best["h0c"], best["h1c"]
    for p in best["seg"]:
        L = p["k1"] - p["k0"]
        ef = eps.get((p["sfa"], p["sfb"]), 0.0)
        u = p["u"] - LAST["psi"][p["sfa"]] - ef
        v = p["v"] - LAST["psi"][p["sfb"]] - ef
        ins = []
        for a in range(0, L + 1):
            Hs = [h0c] if a == 0 else (
                [(a - 1) * 1250.0 + h1c] +
                ([a * 1250.0 + h0c] if a < L else []))
            if any(u < H <= v for H in Hs):
                ins.append(a)
        if len(ins) >= 2 and p["k0"] < 192:
            # truth leading-ones count for this pulse
            a_true = 0
            for t in range(p["k0"], min(p["k1"], 192)):
                if tb[t]:
                    a_true += 1
                else:
                    break
            dead_truth[(min(ins), a_true)] += 1
            dead_by_fam[(p["sfa"], p["sfb"])][a_true] += 1
    rows.append((name, exact, eps.get((5, 6), None), h0c, h1c,
                 LAST["psi"][5], LAST["psi"][6]))

print("DEAD WINDOW pulses: (fewest-ones hypothesis, truth a) -> count")
for k, v in sorted(dead_truth.items()):
    print(f"   min_ins={k[0]} truth_a={k[1]}: {v}")
n_pref = sum(v for (mi, ta), v in dead_truth.items() if ta == mi)
n_tot = sum(dead_truth.values())
print(f"-> fewer-ones prior correct on {n_pref}/{n_tot} dead windows "
      f"({n_pref/max(1,n_tot):.0%});  DEAD_PRIOR_NATS={cm.DEAD_PRIOR_NATS} "
      f"assumes ~82%")
print("dead windows by family, truth-a histogram:")
for fam, cnt in sorted(dead_by_fam.items()):
    print(f"   fam {fam}: {dict(sorted(cnt.items()))}")

print("\nper-capture eps_f[(5,6)] and psi[5]/psi[6]:")
print(f"{'capture':14s} {'ok':>3s} {'eps56':>8s} {'h0c':>7s} {'h1c':>7s} "
      f"{'psi5':>7s} {'psi6':>7s}")
n_none_ok = n_none_bad = 0
for name, ok, e, h0c, h1c, p5, p6 in rows:
    es = "None" if e is None else f"{e:.1f}"
    if e is None:
        if ok:
            n_none_ok += 1
        else:
            n_none_bad += 1
    print(f"{name:14s} {'Y' if ok else 'N':>3s} {es:>8s} {h0c:7.1f} "
          f"{h1c:7.1f} {p5:7.1f} {p6:7.1f}")
print(f"eps_f[(5,6)] skipped (guard fired): "
      f"{n_none_ok} passing, {n_none_bad} failing captures")
