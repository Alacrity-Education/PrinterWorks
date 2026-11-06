"""Emission-refinement sweep: h offset, rise term, per-slot widths."""
import sys
import time

import numpy as np

import dp2

meta, caps = dp2.CM.load()
AS = [dp2.A_of(c) for c in caps]
KG = tuple(np.arange(-0.001, 0.0071, 0.0005))
BASE = dict(kgrid=KG, dlo=-900.0, dhi=900.0, d0sig=1000.0, we=25.0,
            floor=0.01, dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25)
# per-slot fall widths measured by d_edge.py (sigma_fall), floored at 12
WES = [32.0, 24.0, 28.0, 18.0, 12.0, 38.0, 26.0, 46.0]


def run(**kw):
    p = dict(BASE); p.update(kw)
    nex = nbe = 0
    for c, A in zip(caps, AS):
        tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, **p)
        true = np.array(c["bits"])
        nex += (bits[32:160] == true[32:160]).all()
        nbe += int((bits[32:160] != true[32:160]).sum())
    return int(nex), nbe


cases = [
    ("baseline", {}),
    ("hoff=+12.5", dict(hoff=12.5)),
    ("hoff=+25", dict(hoff=25.0)),
    ("hoff=+40", dict(hoff=40.0)),
    ("hoff=-12.5", dict(hoff=-12.5)),
    ("rise sr=40 dr=-28", dict(sr=40.0, dr=-28.0)),
    ("rise+hoff25", dict(sr=40.0, dr=-28.0, hoff=25.0)),
    ("per-slot we", dict(wes=WES)),
    ("per-slot we + hoff25", dict(wes=WES, hoff=25.0)),
    ("per-slot we + rise + hoff25", dict(wes=WES, sr=40.0, dr=-28.0, hoff=25.0)),
    ("dstep=6.25", dict(dstep=6.25)),
    ("vpen=0.5", dict(vpen=0.5)),
    ("vpen=3", dict(vpen=3.0)),
    ("vstep=3.125", dict(vstep=3.125, dstep=6.25)),
]
for name, kw in cases:
    t = time.time()
    nex, nbe = run(**kw)
    print(f"{name:30s} EXACT {nex:2d}/54  biterr {nbe:3d}/6912 "
          f"= {nbe/6912:.5f} ({time.time()-t:.0f}s)")
    sys.stdout.flush()
