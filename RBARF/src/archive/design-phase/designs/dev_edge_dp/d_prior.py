"""Fusion sensitivity: how strong / how accurate must an external per-bit
prior be for edge_dp to close the remaining gap?

Model the upstream technique as emitting, per payload bit, a hint that is
correct with probability `acc`, injected as a log-prior of magnitude
`lam` nats in favour of the hinted value.  Deterministic (seeded) hints.
"""
import sys
import time

import numpy as np

import dp2

meta, caps = dp2.CM.load()
AS = [dp2.A_of(c) for c in caps]
KG = tuple(np.arange(-0.001, 0.0071, 0.0005))
BASE = dict(kgrid=KG, dlo=-900.0, dhi=900.0, d0sig=1000.0, we=25.0,
            floor=0.01, dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25)

rng = np.random.default_rng(12345)
HINT = {c["key"]: rng.random(192) for c in caps}


def run(acc, lam):
    nex = nbe = 0
    for c, A in zip(caps, AS):
        true = np.array(c["bits"])
        prior = np.zeros((192, 2))
        if lam > 0:
            flip = HINT[c["key"]] > acc
            hint = np.where(flip, 1 - true, true)
            for j in range(32, 160):
                prior[j, 1 - int(hint[j])] = lam
        tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, prior=prior, **BASE)
        nex += (bits[32:160] == true[32:160]).all()
        nbe += int((bits[32:160] != true[32:160]).sum())
    return int(nex), nbe


print(f"{'acc':>6s} {'lam':>6s}  EXACT   biterr")
for acc in (0.0, 0.80, 0.90, 0.95, 0.98, 1.00):
    for lam in ((0.0,) if acc == 0.0 else (0.25, 0.5, 1.0, 2.0, 4.0)):
        t = time.time()
        nex, nbe = run(acc, lam)
        print(f"{acc:6.2f} {lam:6.2f}  {nex:2d}/54  {nbe:4d}/6912 "
              f"= {nbe/6912:.5f}  ({time.time()-t:.0f}s)")
        sys.stdout.flush()
