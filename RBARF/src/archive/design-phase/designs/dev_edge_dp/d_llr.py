"""Soft per-bit log-likelihood ratios under the calibrated time model.

Emission:  P(sample high | within-bit phase u, bit b)
             = f + (1-2f) * sigmoid((h_b - u)/we)
LLR(bit k) = sum over samples in window k of
             log P(obs|u,1) - log P(obs|u,0)

Reports the LLR distribution, sign-error rate, and how many bits are
weakly determined (|LLR| below thresholds) -- i.e. how much work the
global DP has to do.  Also sweeps we and the floor f.
"""
import json
import sys
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM      # noqa: E402
import final as CF      # noqa: E402

F = json.load(open(CAL / "final.json"))
G, o, w, H1, H0 = F["G"], F["o"], F["w"], F["h1"], F["h0"]
meta, caps = CM.load()
CF.prepare(caps)

pre = []
for c in caps:
    t0, k = F["nuis"][c["key"]][:2]
    t = t0 + k * CF.A_of(c, G, o, w)
    idx = np.floor(t / 1250.0).astype(int)
    m = (idx >= 0) & (idx < 192)
    pre.append((c["key"], idx[m], t[m] - idx[m] * 1250.0, c["lv"][m],
                np.array(c["bits"])))


def llrs(we, f, h1=H1, h0=H0):
    out = []
    for key, idx, u, lv, bits in pre:
        p1 = f + (1 - 2 * f) / (1 + np.exp(-(h1 - u) / we))
        p0 = f + (1 - 2 * f) / (1 + np.exp(-(h0 - u) / we))
        l = lv * (np.log(p1) - np.log(p0)) + (1 - lv) * (np.log(1 - p1) - np.log(1 - p0))
        acc = np.zeros(192)
        np.add.at(acc, idx, l)
        out.append((key, acc, bits))
    return out


print(f"{'we':>5s} {'floor':>6s} {'signerr':>9s} {'|LLR|<1':>8s} {'|LLR|<3':>8s}"
      f" {'medLLR':>8s} {'mean-nats-correct':>18s}")
best = None
for we in (15.0, 25.0, 35.0, 50.0, 70.0):
    for f in (0.002, 0.01, 0.03):
        R = llrs(we, f)
        se = w1 = w3 = tot = 0
        mags = []
        nats = 0.0
        for key, acc, bits in R:
            s = np.where(bits == 1, acc, -acc)      # >0 = correct direction
            se += int((s < 0).sum()); tot += 192
            w1 += int((np.abs(acc) < 1).sum())
            w3 += int((np.abs(acc) < 3).sum())
            mags.append(np.abs(acc))
            nats += float(s.mean())
        print(f"{we:5.0f} {f:6.3f} {se:4d}/{tot:5d} {se/tot:7.4f} {w1/tot:8.4f}"
              f" {w3/tot:8.4f} {np.median(np.concatenate(mags)):8.2f}"
              f" {nats/len(R):18.2f}")
        if best is None or se < best[0]:
            best = (se, we, f)

se, we, f = best
print(f"\nbest: we={we} floor={f} sign-error {se}/10368 = {se/10368:.4f}")
R = llrs(we, f)
# per-capture breakdown and position of errors
print("\nper-capture sign errors (bit index of each error, payload region 32..159):")
tot_pay = 0
for key, acc, bits in R:
    s = np.where(bits == 1, acc, -acc)
    e = np.where(s < 0)[0]
    pay = [int(x) for x in e if 32 <= x < 160]
    tot_pay += len(pay)
    if len(e):
        print(f"  {key:14s} nerr={len(e):3d} pay={len(pay):3d} "
              f"minLLR={s.min():7.2f} idx={list(map(int,e))[:14]}")
print(f"payload-region sign errors: {tot_pay} over {len(R)} captures "
      f"({tot_pay/(len(R)*128):.4f}/bit)")
ex = sum(1 for key, acc, bits in R
         if not np.any(np.where(bits == 1, acc, -acc)[32:160] < 0))
print(f"captures whose 128 payload bits are ALL correct by sign(LLR): {ex}/{len(R)}")
