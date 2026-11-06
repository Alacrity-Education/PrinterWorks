"""Evaluate the dev_calibration fitted model IN-FRAME (read-only use).

The calibration fit scores agreement over all 5120 samples, most of which
sit in the trivially-low post-frame latch region.  What edge_dp cares
about is the agreement over the ~768 samples that actually land inside
the 240 us frame, and the *structure* of the residuals there.
"""
import json
import sys
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM          # noqa: E402  (dev_calibration/model.py)
import final as CF          # noqa: E402

F = json.load(open(CAL / "final.json"))
G, o, w, h1, h0 = F["G"], F["o"], F["w"], F["h1"], F["h0"]
print(f"G={G:.2f} o={[round(x,1) for x in o]} w={w} h1={h1} h0={h0}")
print("gaps:", [round(o[i + 1] - o[i], 1) for i in range(7)],
      "end-gap:", round(G - o[7] + o[0], 1))

meta, caps = CM.load()
CF.prepare(caps)
FRAME_NS = 192 * 1250.0

BW = 25.0
NB = int(1250 / BW)
cnt = np.zeros((2, NB)); hi = np.zeros((2, NB))
slot_n = np.zeros(8); slot_m = np.zeros(8)
tot_ok = tot_n = 0
rows = []
resid_edges = []
for c in caps:
    t0, k = F["nuis"][c["key"]][:2]
    A = CF.A_of(c, G, o, w)
    t = t0 + k * A
    lv = c["lv"]; bits = c["bits"]
    pred = CM.wire_levels(t, bits, h1, h0)
    m = (t >= -50) & (t < FRAME_NS)
    ok = (pred == lv)
    tot_ok += int(ok[m].sum()); tot_n += int(m.sum())
    rows.append((c["key"], int(ok[m].sum()), int(m.sum())))
    tt = t[m]; kk = np.clip((tt // 1250).astype(int), 0, 191)
    u = tt - kk * 1250.0
    b = bits[kk]; oo = lv[m]
    ub = np.clip((u // BW).astype(int), 0, NB - 1)
    for bv in (0, 1):
        sel = b == bv
        np.add.at(cnt[bv], ub[sel], 1)
        np.add.at(hi[bv], ub[sel], oo[sel])
    np.add.at(slot_n, c["sl"][m], 1)
    np.add.at(slot_m, c["sl"][m], ~ok[m])

print(f"\nIN-FRAME agreement {tot_ok}/{tot_n} = {tot_ok/tot_n:.4f}"
      f"   ({tot_n/len(caps):.0f} in-frame samples/capture)")
rows.sort(key=lambda r: r[1] / r[2])
for k_, a, b in rows[:8]:
    print(f"   worst {k_:14s} {a}/{b} = {a/b:.4f}  ({b-a} mismatches)")
print(f"   median mismatches/capture: "
      f"{np.median([b-a for _,a,b in rows]):.0f}")

print("\nP(high) vs within-bit phase (25 ns bins), in-frame:")
for j in range(NB):
    a = cnt[0, j]; b = cnt[1, j]
    print(f" {j*BW:6.0f}-{(j+1)*BW:6.0f}  bit0 n={a:5.0f} P={hi[0,j]/max(a,1):6.3f}"
          f"   bit1 n={b:5.0f} P={hi[1,j]/max(b,1):6.3f}")

print("\nper-slot in-frame mismatch:")
for s in range(8):
    print(f"  slot{s} {slot_m[s]:4.0f}/{slot_n[s]:5.0f} = {slot_m[s]/slot_n[s]:.4f}")
