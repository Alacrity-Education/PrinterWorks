import json
import sys
import time

import numpy as np

import dp2

meta, caps = dp2.CM.load()
F = dp2.F

kw = {}
for a in sys.argv[1:]:
    k, v = a.split("=")
    kw[k] = tuple(float(x) for x in v.split(",")) if "," in v else float(v)

t0 = time.time()
nex = 0
nbe = 0
rows = []
for c in caps:
    A = dp2.A_of(c)
    tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, **kw)
    true = np.array(c["bits"])
    pay = dp2.bits_to_payload(bits)
    tpay = dp2.bits_to_payload(true)
    ex = pay == tpay
    nex += ex
    be = int((bits[32:160] != true[32:160]).sum())
    nbe += be
    kref = F["nuis"][c["key"]][1]
    rows.append((c["key"], ex, be, kap, kref, dtr))
    if not ex:
        bad = np.where(bits[32:160] != true[32:160])[0] + 32
        print(f"  {c['key']:14s} MISS biterr={be:3d} at {list(map(int,bad))[:10]} "
              f"kap={kap:.5f} ref={kref:.5f} d0={dtr[0]:6.1f} dN={dtr[-1]:6.1f}")
print(f"\nEXACT {nex}/{len(caps)}   payload biterr {nbe}/{len(caps)*128} "
      f"= {nbe/(len(caps)*128):.5f}   ({time.time()-t0:.0f}s) kw={kw}")
dk = np.array([abs(r[3] - r[4]) / r[4] for r in rows])
print(f"blind kappa vs calibration-fitted: max rel err {dk.max():.2e} "
      f"median {np.median(dk):.2e}")
tr = np.array([r[5] for r in rows])
print(f"phase track d: range over captures {tr.min():.0f}..{tr.max():.0f} ns; "
      f"per-capture span median {np.median(tr.max(1)-tr.min(1)):.0f} ns; "
      f"|step| p90 {np.percentile(np.abs(np.diff(tr,axis=1)),90):.1f} ns")
json.dump({r[0]: [bool(r[1]), r[2], r[3]] for r in rows},
          open("dp2_last.json", "w"), indent=0)
