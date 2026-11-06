import sys, time
import numpy as np
import dp2
meta, caps = dp2.CM.load()
AS = [dp2.A_of(c) for c in caps]
KG = tuple(np.arange(-0.001, 0.0071, 0.0005))
BASE = dict(kgrid=KG, dlo=-900.0, dhi=900.0, d0sig=1000.0, we=25.0,
            floor=0.01, dstep=12.5, vpen=1.2, vmax=25.0, vstep=6.25)
WES = [32.0, 24.0, 28.0, 18.0, 12.0, 38.0, 26.0, 46.0]
def run(**kw):
    p = dict(BASE); p.update(kw); nex = nbe = 0
    for c, A in zip(caps, AS):
        tot, bits, dtr, kap, k0 = dp2.run_capture(c, A, **p)
        true = np.array(c["bits"])
        nex += (bits[32:160] == true[32:160]).all()
        nbe += int((bits[32:160] != true[32:160]).sum())
    return int(nex), nbe
cases = [
 ("wes+rise", dict(wes=WES, sr=40.0, dr=-28.0)),
 ("wes+rise+hoff-12.5", dict(wes=WES, sr=40.0, dr=-28.0, hoff=-12.5)),
 ("wes+hoff-12.5", dict(wes=WES, hoff=-12.5)),
 ("wes+rise dstep6.25", dict(wes=WES, sr=40.0, dr=-28.0, dstep=6.25)),
 ("wes+rise vpen0.5", dict(wes=WES, sr=40.0, dr=-28.0, vpen=0.5)),
 ("wes+rise vpen3", dict(wes=WES, sr=40.0, dr=-28.0, vpen=3.0)),
 ("wes+rise floor.005", dict(wes=WES, sr=40.0, dr=-28.0, floor=0.005)),
 ("wes+rise floor.02", dict(wes=WES, sr=40.0, dr=-28.0, floor=0.02)),
 ("wes*0.7+rise", dict(wes=[x*0.7 for x in WES], sr=40.0, dr=-28.0)),
 ("wes*1.4+rise", dict(wes=[x*1.4 for x in WES], sr=40.0, dr=-28.0)),
 ("wes+rise kgrid fine", dict(wes=WES, sr=40.0, dr=-28.0,
                              kgrid=tuple(np.arange(-0.001, 0.00701, 0.00025)))),
]
for name, kw in cases:
    t = time.time(); nex, nbe = run(**kw)
    print(f"{name:28s} EXACT {nex:2d}/54  biterr {nbe:3d}/6912 = {nbe/6912:.5f} ({time.time()-t:.0f}s)")
    sys.stdout.flush()
