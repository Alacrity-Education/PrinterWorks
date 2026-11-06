#!/usr/bin/env python3
"""Where does the knife vote fire, and is it right? (truth used for eval
only).  Also lists knife bits that abstained, with their sibling votes."""
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
if len(sys.argv) > 1:
    for ov in sys.argv[1:]:
        k, v = ov.split("=", 1)
        setattr(cm, k, float(v))

meta, caps = load_dataset()
HDR = cm._bits_of(cm.HDR)
TRL = cm._bits_of(cm.TRL)

for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    best, _ = cm._decode_full(samples, meta)
    if best is None:
        print(f"{name}: REFUSED")
        continue
    ok = best["payload"] == bytes.fromhex(c["payload"])
    llr = best["llr"]
    bits = best["bits"]
    lines = []
    for p in best["seg"]:
        if (p["sfa"], p["sfb"]) != (5, 6) or p["k1"] - p["k0"] != 1:
            continue
        t = p["k0"]
        if not (32 <= t < 160):
            continue
        # a bit the vote resolved has |llr| == DEAD_VOTE_SET exactly;
        # a knife bit that abstained still has |llr| < KNIFE_LLR
        fired = abs(abs(llr[t]) - cm.DEAD_VOTE_SET) < 1e-9
        knife = abs(llr[t]) < cm.KNIFE_LLR
        if not (fired or knife):
            continue
        sib = []
        for dt in (-16, -8, 8, 16):
            s = t + dt
            if 32 <= s < 160:
                sib.append((s, bits[s], round(llr[s], 2), tb[s]))
        good = bits[t] == tb[t]
        lines.append((t, fired, bits[t], tb[t], round(llr[t], 3), good, sib))
    if lines:
        print(f"{name} {'OK' if ok else 'MISS'}:")
        for t, fired, b, tt, l, good, sib in lines:
            print(f"   bit{t:3d} {'VOTE' if fired else 'abst'} got={b} "
                  f"truth={tt} llr={l:+.3f} {'RIGHT' if good else 'WRONG'} "
                  f"sibs={[(s, bb, ll) for s, bb, ll, _tt in sib]}")
