#!/usr/bin/env python3
"""Pulse-level autopsy of embedded_ref misses: for every wrong payload bit,
dump the covering segment, its bracket, costs, and the host's view."""
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
want = sys.argv[1:] or ["nibbles_1", "rnd1_0", "rnd2_0", "rnd2_1",
                        "rnd3_0", "rnd3_2", "sparse_1"]

for c in caps:
    name = f"{c['pattern']}_{c['rep']}"
    if name not in want:
        continue
    samples = linearize(c["capture"])
    truth = er._bits_of(bytes.fromhex(c["payload"]))
    K, tau, np_ = er._seed(samples)
    for _ in range(2):
        K, tau = er._refine(samples, K, tau)
    st = er._decode_full(samples)
    bits = st["bits"]
    berr = [32 + i for i, (a, b) in enumerate(
        zip(bits[32:er.NB - 32], truth)) if a != b]
    print(f"== {name}: K={K} tau={tau} nseg={st['n_seg']} "
          f"inf={st['infeasible']} laberr={st['label_err']} "
          f"knife={st['knife']} berr={berr}")
    cal = er._calibrate(samples, K, tau)
    # rebuild final cal exactly as decode does
    if er.SELF_TRAIN:
        cal1 = cal

        def extra(k0, k1, u, v, fam, _c=cal1):
            a_hat, c_hat, costs, lo, hi, inter, a_free = er._decide(
                k0, k1, u, v, fam, _c)
            t = k0 + a_hat - 1 if a_hat > 0 else k0
            t = min(max(t, k0), min(k1, er.NB) - 1)
            off = t - k0
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            m = 255 if (c0 is None or c1 is None) else min(255, abs(c0 - c1))
            return a_hat, m
        cal = er._calibrate(samples, K, tau, extra=extra)
    print(f"   h0c={cal.h0c} h1c={cal.h1c} "
          f"h0f={cal.h0f} h1f={cal.h1f}")
    for (k0, k1, u, v, fam) in er._seg_stream(samples, K, tau):
        cover = [t for t in berr if k0 <= t < min(k1, er.NB)]
        if not cover:
            continue
        a_hat, c_hat, costs, lo, hi, inter, a_free = er._decide(
            k0, k1, u, v, fam, cal)
        a_true = sum(1 for t in range(k0, min(k1, er.NB))
                     if truth[t - 32] if 32 <= t < er.NB - 32)
        # truth leading ones for this pulse
        tt = []
        for t in range(k0, min(k1, er.NB)):
            if 32 <= t < er.NB - 32:
                tt.append(truth[t - 32])
            else:
                tt.append(er.KNOWN[t])
        a_tr = 0
        for b in tt:
            if b == 1:
                a_tr += 1
            else:
                break
        print(f"   bit{cover} k0={k0} k1={k1} L={k1-k0} fam={fam} "
              f"u={u} v={v} gap={v-u} costs={costs} "
              f"a_hat={a_hat} a_true={a_tr} allowed=[{lo},{hi}] "
              f"inter={inter} tied={[st['tied'][t] for t in cover]} "
              f"conf@sib={[(dt, st['conf'][cover[0]+dt] if 0 <= cover[0]+dt < er.NB else '-', bits[cover[0]+dt] if 0 <= cover[0]+dt < er.NB else '-') for dt in (-16, -8, 8, 16)]}")
