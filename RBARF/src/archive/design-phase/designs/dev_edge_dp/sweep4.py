import sys, time
import numpy as np
import dp2
meta, caps = dp2.CM.load()
AS=[dp2.A_of(c) for c in caps]
WES=[32.,24.,28.,18.,12.,38.,26.,46.]
BASE=dict(dlo=-900.,dhi=900.,d0sig=1000.,we=25.,floor=.01,dstep=12.5,
          vpen=1.2,vmax=25.,vstep=6.25,wes=WES,sr=40.,dr=-28.)
def run(**kw):
    p=dict(BASE); p.update(kw); nex=nbe=0
    for c,A in zip(caps,AS):
        tot,bits,dtr,kap,k0=dp2.run_capture(c,A,**p)
        true=np.array(c["bits"])
        nex+=(bits[32:160]==true[32:160]).all(); nbe+=int((bits[32:160]!=true[32:160]).sum())
    return int(nex),nbe
cases=[
 ("kg +-0.005 /5e-4", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.0005)))),
 ("kg +-0.005 /2.5e-4", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.00025)))),
 ("kg +-0.008 /2.5e-4", dict(kgrid=tuple(np.arange(-0.008,0.00801,0.00025)))),
 ("kg fine + dstep6.25", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.00025)),dstep=6.25)),
 ("kg fine + dlo/hi 500", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.00025)),dlo=-700.,dhi=700.)),
 ("kg fine, no rise", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.00025)),sr=0.)),
 ("kg fine, flat we=25", dict(kgrid=tuple(np.arange(-0.005,0.00501,0.00025)),wes=None)),
]
for n,kw in cases:
    t=time.time(); a,b=run(**kw)
    print(f"{n:24s} EXACT {a:2d}/54 biterr {b:3d}/6912 = {b/6912:.5f} ({time.time()-t:.0f}s)"); sys.stdout.flush()
