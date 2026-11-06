#!/usr/bin/env python3
"""Per-capture diagnostics for embedded_ref: lock quality, calibration,
quality counters, and bit-error positions vs ground truth (diagnostic
only -- the decoder itself never sees the truth)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from harness import load_dataset, linearize  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "embedded_ref", ROOT / "approaches" / "embedded_ref.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)

meta, caps = load_dataset()
only = sys.argv[1] if len(sys.argv) > 1 else None

for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    if only and only not in name:
        continue
    samples = linearize(c["capture"])
    exp = bytes.fromhex(c["payload"])
    seed = er._seed(samples)
    if seed is None:
        print(f"{name:14s} SEED FAIL")
        continue
    K, tau, np_ = seed
    K0, tau0 = K, tau
    for _ in range(2):
        K, tau = er._refine(samples, K, tau)
    # lock quality: rise-bracket hit rate + residual stats across frame
    y_end = er.BIAS_U + er.NB * er.BIT_U + er.TAIL_U
    hits = tot = 0
    es_first, es_last = [], []
    mid_u = er.BIAS_U + (er.NB // 2) * er.BIT_U
    for p in er._pulse_stream(samples):
        ya = er._map(p[0], K, tau)
        yb = er._map(p[1], K, tau)
        ym = (ya + yb) >> 1
        if ym > y_end:
            break
        q = (ym + 64) >> 7
        g = q << 7
        if ya <= g <= yb:
            hits += 1
        tot += 1
        e = ym - g
        (es_first if ym < mid_u else es_last).append(e)
    def ms(v):
        return f"{sum(v)/len(v):+6.1f}" if v else "  n/a "
    cal = er._calibrate(samples, K, tau)
    st = er._decide_pass(samples, K, tau, cal)
    dec = er.decode(samples, meta)
    ok = dec == exp
    nerr = "REFUSED" if dec is None else \
        f"{sum(1 for a, b in zip(dec, exp) if a != b)} byte err"
    # bit error positions
    bits = st["bits"]
    truth = er._bits_of(bytes.fromhex(c["payload"]))
    berr = [32 + i for i, (a, b) in enumerate(
        zip(bits[32:er.NB - 32], truth)) if a != b]
    print(f"{name:14s} {'OK ' if ok else 'MISS'} {nerr:12s}"
          f" K {K0}->{K} tau {tau0}->{tau}"
          f" hits {hits}/{tot} e_lo {ms(es_first)} e_hi {ms(es_last)}"
          f" h0c={cal.h0c} h1c={cal.h1c} off={cal.off}"
          f" inf={st['infeasible']} laberr={st['label_err']}"
          f" berr={berr[:14]}")
