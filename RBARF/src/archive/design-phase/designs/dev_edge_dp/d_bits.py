"""Per-bit observability under the calibrated sample-time model.

For each of the 192 frame bits: which samples land in its window, and do
those samples DISCRIMINATE b=0 from b=1?  A sample at within-bit phase u
discriminates iff h0 <= u < h1 (predicted high for '1', low for '0').
Everything else is uninformative about that bit.

Also: how often does the observed pattern contradict the true bit
(local hard decision would flip it), and how do those failures cluster.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

CAL = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_calibration")
sys.path.insert(0, str(CAL))
import model as CM      # noqa: E402
import final as CF      # noqa: E402

F = json.load(open(CAL / "final.json"))
G, o, w, h1, h0 = F["G"], F["o"], F["w"], F["h1"], F["h0"]
meta, caps = CM.load()
CF.prepare(caps)

disc_hist = Counter()
nsamp_hist = Counter()
zero_bits_by_val = Counter()
local_err = 0
local_tot = 0
err_by_val = Counter()
tie_by_val = Counter()
runs = []
percap = []
gapzero = 0
for c in caps:
    t0, k = F["nuis"][c["key"]][:2]
    t = t0 + k * CF.A_of(c, G, o, w)
    lv = c["lv"]; bits = c["bits"]
    idx = np.floor(t / 1250.0).astype(int)
    u = t - idx * 1250.0
    caperr = 0
    zero_run = 0
    for b in range(192):
        m = idx == b
        uu = u[m]; oo = lv[m]
        nsamp_hist[int(m.sum())] += 1
        d = (uu >= h0) & (uu < h1)             # discriminating window
        nd = int(d.sum())
        disc_hist[nd] += 1
        tv = int(bits[b])
        if nd == 0:
            zero_bits_by_val[tv] += 1
            zero_run += 1
        else:
            if zero_run:
                runs.append(zero_run)
            zero_run = 0
        # local hard decision: majority of discriminating samples
        local_tot += 1
        if nd == 0:
            tie_by_val[tv] += 1
            caperr += 1                        # undecidable locally
        else:
            vote = oo[d].mean()
            if vote == 0.5:
                tie_by_val[tv] += 1
                caperr += 1
            elif (vote > 0.5) != (tv == 1):
                local_err += 1
                err_by_val[tv] += 1
                caperr += 1
    if zero_run:
        runs.append(zero_run)
    percap.append((c["key"], caperr))

N = 192 * len(caps)
print(f"captures={len(caps)}  bits={N}")
print("samples per bit window:", dict(sorted(nsamp_hist.items())))
print("discriminating samples per bit:", dict(sorted(disc_hist.items())))
nz = disc_hist[0]
print(f"\nbits with ZERO discriminating sample: {nz}/{N} = {nz/N:.4f}"
      f"   (true 0: {zero_bits_by_val[0]}, true 1: {zero_bits_by_val[1]})")
print(f"local hard-decision outright errors: {local_err}/{N} = {local_err/N:.4f}"
      f"  (true0->1: {err_by_val[0]}, true1->0: {err_by_val[1]})")
print(f"local ties/undecidable: {sum(tie_by_val.values())}/{N}"
      f"  (true 0: {tie_by_val[0]}, true 1: {tie_by_val[1]})")
print(f"=> per-bit locally-unresolved rate "
      f"{(local_err+sum(tie_by_val.values()))/N:.4f}")
print("run lengths of consecutive zero-discriminating bits:",
      dict(sorted(Counter(runs).items())))
percap.sort(key=lambda r: -r[1])
print("worst captures (unresolved bits/192):", percap[:8])
print("median unresolved/capture:", np.median([e for _, e in percap]))
print("captures with 0 unresolved:", sum(1 for _, e in percap if e == 0))
