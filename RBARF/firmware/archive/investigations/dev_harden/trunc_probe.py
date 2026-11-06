#!/usr/bin/env python3
"""What do the (5,6) L=1 payload llrs look like on truncated captures vs
clean, for all 54?  Informs the truncation knife gate threshold."""
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
HDR = cm._bits_of(cm.HDR)
TRL = cm._bits_of(cm.TRL)


def drop_loops(samples, n, renumber):
    return [(i - n if renumber else i, s, v)
            for (i, s, v) in samples if i >= n]


def klist(best, tb):
    out = []
    for p in best["seg"]:
        if (p["sfa"], p["sfb"]) != (5, 6) or p["k1"] - p["k0"] != 1:
            continue
        t = p["k0"]
        if not (32 <= t < 160):
            continue
        l = best["llr"][t]
        if abs(l) < 3.0:
            good = (1 if l > 0 else 0) == tb[t]
            out.append((t, round(l, 2), "ok" if good else "WRONG"))
    return out


BY = {f"{c['pattern']}_{c['rep']}": c for c in caps}
for name in ["rnd1_0", "rnd1_1", "rnd2_1", "rnd3_1", "count_0",
             "impulse_hi_0"]:
    c = BY[name]
    s0 = linearize(c["capture"])
    tb = HDR + cm._bits_of(bytes.fromhex(c["payload"])) + TRL
    for tag, sv in (("clean", s0), ("drop1", drop_loops(s0, 1, False)),
                    ("drop2", drop_loops(s0, 2, False)),
                    ("drop3", drop_loops(s0, 3, False))):
        best, _ = cm._decode_full(sv, meta)
        if best is None:
            print(f"{name}/{tag}: no decode")
            continue
        d = cm.decode(sv, meta)
        exp = bytes.fromhex(c["payload"])
        st = "OK " if d == exp else ("REFU" if d is None else "WRONG")
        print(f"{name}/{tag:6s} {st} cover0={best['cover0']} "
              f"knife_open={best['knife_open']} "
              f"|llr|<3 bits: {klist(best, tb)}")
