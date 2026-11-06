"""Parameter sweep for the edge_dp prototype on the 54 real captures."""
import itertools
import sys
import time

import numpy as np

import dp2

meta, caps = dp2.CM.load()
AS = [dp2.A_of(c) for c in caps]
KG = tuple(np.arange(-0.001, 0.0071, 0.0005))


def run(**kw):
    kw.setdefault("kgrid", KG)
    kw.setdefault("dlo", -900.0)
    kw.setdefault("dhi", 900.0)
    kw.setdefault("d0sig", 1000.0)
    nex = nbe = 0
    for c, A in zip(caps, AS):
        tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, **kw)
        true = np.array(c["bits"])
        nex += dp2.bits_to_payload(bits) == dp2.bits_to_payload(true)
        nbe += int((bits[32:160] != true[32:160]).sum())
    return nex, nbe


base = dict(we=45.0, floor=0.01, dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25)
grid = {
    "we": [25.0, 35.0, 45.0, 60.0, 80.0],
    "floor": [0.002, 0.005, 0.01, 0.02, 0.05],
    "dstep": [6.25, 12.5, 25.0],
    "vpen": [0.3, 0.6, 1.2, 2.5, 5.0],
    "vmax": [12.5, 25.0, 43.75],
}
which = sys.argv[1:] or list(grid)
for key in which:
    for v in grid[key]:
        kw = dict(base); kw[key] = v
        t = time.time()
        nex, nbe = run(**kw)
        print(f"{key}={v:<8} EXACT {nex:2d}/54  biterr {nbe:3d}/6912 "
              f"= {nbe/6912:.5f}  ({time.time()-t:.0f}s)")
        sys.stdout.flush()
