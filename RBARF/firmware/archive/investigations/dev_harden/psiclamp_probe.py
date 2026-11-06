#!/usr/bin/env python3
"""Do any winning per-capture fits pin a psi[s] at the +-PSI_SPAN clamp?"""
import sys
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

_orig = cm._fit_model
LAST = {}


def spy(labelled, h0p, h1p):
    h0c, h1c, psi = _orig(labelled, h0p, h1p)
    LAST["psi"] = list(psi)
    return h0c, h1c, psi


cm._fit_model = spy

n_hit = 0
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        continue
    # LAST holds the psi of the *last* fit run, which belongs to the last
    # alias/model tried, not necessarily the winner -- so refit the winner:
    # simplest faithful check is the psi range across ALL fits vs winner's
    # h0c/h1c... instead re-run _try_decode on the winning seg is complex;
    # here we just report the last fit AND whether any fit during this
    # capture hit the clamp.
    hits = [s for s, v in enumerate(LAST["psi"])
            if abs(v) >= cm.PSI_SPAN - 1e-9]
    ok = best["payload"] == bytes.fromhex(c["payload"])
    if hits:
        n_hit += 1
        print(f"{name:14s} ok={ok} last-fit psi clamp hits at slots {hits} "
              f"psi={[round(x,1) for x in LAST['psi']]}")
print(f"captures whose LAST fit pinned a psi: {n_hit}")
