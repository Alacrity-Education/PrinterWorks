"""Emission-model calibration under the best GLOBAL LINEAR sample-time model.

Uses nfit.json (jointly fitted slot offsets o[0..7] in nominal ns +
per-capture (phi, k)).  Produces:
  * overall / per-capture sample agreement
  * P(observed high | within-bit phase u, true bit value)  -> emission curve
  * per-slot mismatch rate
  * where the mismatches sit relative to the ideal edge (edge-timing jitter)
"""
import json
from collections import defaultdict
import numpy as np
import model as M

FRAME_NS = 192 * 1250.0
fit = json.load(open("nfit.json"))
O = np.array(fit["o"])
meta, D = M.load()
names = fit["caps"]

BW = 25.0
NB = int(1250 / BW)
cnt = np.zeros((2, NB))
hi = np.zeros((2, NB))
slot_n = np.zeros(8); slot_m = np.zeros(8)
tot_ok = tot_n = 0
percap = []
for d, (phi, k) in zip(D, fit["nuis"]):
    bits = np.array(d["bits"])
    I = np.array([i for i, s in d["idx"]], dtype=float)
    S = np.array([s for i, s in d["idx"]])
    obs = np.array(d["obs"])
    t = phi + k * (I * M.L_NOM + O[S])
    m = (t >= 0) & (t < FRAME_NS)
    tt = t[m]; ss = S[m]; oo = obs[m]
    kk = (tt // 1250).astype(int)
    u = tt - kk * 1250.0
    b = bits[kk]
    thr = np.where(b == 1, 750.0, 375.0)
    pred = (u < thr).astype(int)
    ok = (pred == oo)
    tot_ok += ok.sum(); tot_n += len(ok)
    percap.append((f"{d['pattern']}_{d['rep']}", ok.sum(), len(ok), phi, k))
    ub = np.clip((u // BW).astype(int), 0, NB - 1)
    for bv in (0, 1):
        sel = b == bv
        np.add.at(cnt[bv], ub[sel], 1)
        np.add.at(hi[bv], ub[sel], oo[sel])
    np.add.at(slot_n, ss, 1)
    np.add.at(slot_m, ss, ~ok)

print(f"GLOBAL agreement {tot_ok}/{tot_n} = {tot_ok/tot_n:.4f}")
percap.sort(key=lambda r: r[1] / r[2])
print("worst 6:", [(n, f"{a/b:.4f}") for n, a, b, _, _ in percap[:6]])
print("best  3:", [(n, f"{a/b:.4f}") for n, a, b, _, _ in percap[-3:]])
ks = np.array([k for _, k in fit["nuis"]])
print(f"k: min={ks.min():.5f} med={np.median(ks):.5f} max={ks.max():.5f}"
      f"  -> loop_ns {2500*ks.min():.1f}..{2500*ks.max():.1f}")

print("\nP(high) vs within-bit phase u  (25 ns bins)")
print("   u(ns)     bit0: n  P(hi)     bit1: n  P(hi)")
for j in range(NB):
    a = cnt[0, j]; b = cnt[1, j]
    print(f" {j*BW:6.0f} {(j+1)*BW:6.0f}  {a:7.0f} {hi[0,j]/max(a,1):6.3f}   "
          f"{b:7.0f} {hi[1,j]/max(b,1):6.3f}")

print("\nper-slot mismatch:")
for s in range(8):
    print(f"  slot{s} o={O[s]:7.1f}  {slot_m[s]:5.0f}/{slot_n[s]:5.0f}"
          f" = {slot_m[s]/slot_n[s]:.4f}")

# transition-width estimate: fit sigmoid width to the bit=1 falling edge
for bv, edge in ((0, 375.0), (1, 750.0)):
    j0 = int((edge - 150) // BW); j1 = int((edge + 150) // BW)
    print(f"\nbit{bv} edge @{edge:.0f}: ", " ".join(
        f"{j*BW:.0f}:{hi[bv,j]/max(cnt[bv,j],1):.2f}" for j in range(j0, j1)))
