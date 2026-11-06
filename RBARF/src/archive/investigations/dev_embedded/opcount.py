#!/usr/bin/env python3
"""Measured operation counts for the embedded decoder.

Runs embedded_ref with its OPS counters over (a) the real 54 captures
(192-bit frames) and (b) synthetic PRODUCTION-SIZE frames (48-byte
payload = 448 bits) built with synth.py's fitted sampler model at the
bench operating point and at the envelope corners, then converts the
worst case to STM8 cycles with per-op cost models (documented margins).
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402
import synth  # noqa: E402
from synth import _simulate  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "embedded_ref", ROOT / "approaches" / "embedded_ref.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)

meta, caps = load_dataset()


def report(tag, runs):
    keys = ("scan", "sample", "pulse", "mul", "div", "cand", "bit")
    print(f"\n== {tag} ==")
    print("        " + "".join(f"{k:>9s}" for k in keys) + "   est_cycles")
    worst = None
    for name, ops in runs:
        cyc = cycles(ops)
        if worst is None or cyc > worst[2]:
            worst = (name, ops, cyc)
        print(f"{name:14s}" + "".join(f"{ops[k]:9d}" for k in keys)
              + f"   {cyc:9d}")
    name, ops, cyc = worst
    print(f"WORST {name}: {cyc} cycles = {cyc/16000:.2f} ms @16MHz")
    return worst


# Per-op STM8 cycle model (documented in EMBEDDED_FEASIBILITY.md):
#   sample: unpack bit + incremental clock + edge test    ~14 cy
#   pulse:  bracket bookkeeping + stream state            ~40 cy
#   mul:    16x16->32 asm helper (4 hw MULs + adds)       ~60 cy
#   div:    32/16 or 32/32 library division               ~400 cy
#   cand:   one hypothesis hinge eval (16-bit cmp/sub)    ~30 cy
#   bit:    per-bit emit/margin/vote bookkeeping          ~40 cy
# plus 2x safety margin applied at the end (STM8_CYCLE_COUNTING.md warns
# documented counts can be wrong; pipeline stalls, SDCC overhead).
COST = dict(scan=200, sample=14, pulse=40, mul=60, div=400, cand=30, bit=40)
MARGIN = 2.0


def cycles(ops):
    return int(MARGIN * sum(COST[k] * v for k, v in ops.items()))


# ---- (a) real captures, 192-bit frames --------------------------------
runs = []
for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    samples = linearize(c["capture"])
    er.ops_reset()
    er.decode(samples, meta)
    runs.append((name, dict(er.OPS)))
runs.sort(key=lambda r: -cycles(r[1]))
report("real captures 192-bit (top 6 by cycles)", runs[:6])

# ---- (b) production-size 448-bit frames -------------------------------
er._configure(48)
PROD = {
    "zeros48": bytes(48),
    "ones48": bytes([0xFF] * 48),
    "aa48": bytes([0xAA] * 48),           # worst pulse count
    "p5548": bytes([0x55] * 48),
    "rnd48": synth._lcg_bytes(7, 48) if hasattr(synth, "_lcg_bytes") else
             bytes((i * 37 + 11) & 0xFF for i in range(48)),
    "grb48": bytes((i * 5) & 0xFF for i in range(48)),
}
runs = []
ok = 0
for name, payload in PROD.items():
    fr = synth.frame(payload)
    bits = [int(b) for byte in fr for b in f"{byte:08b}"]
    for eps, tag in ((synth.BENCH_EPS, "bench"), (-0.075, "slow"),
                     (0.075, "fast")):
        samples = _simulate(bits, eps, 0.0, 385.0, 640)
        er.ops_reset()
        d = er.decode(samples, meta)
        good = (d == payload)
        ok += int(good)
        runs.append((f"{name}/{tag}{'' if good else ' *MISS*'}",
                     dict(er.OPS)))
runs.sort(key=lambda r: -cycles(r[1]))
print(f"\nproduction-size decodes correct: {ok}/{len(runs)}")
report("PRODUCTION 448-bit frames (all, sorted by cycles)", runs)
er._configure(16)
