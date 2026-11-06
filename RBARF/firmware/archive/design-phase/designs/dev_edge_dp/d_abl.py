"""Ablations: which part of edge_dp buys what."""
import sys, time
import numpy as np
import dp2
meta, caps = dp2.CM.load()
AS=[dp2.A_of(c) for c in caps]
WES=[32.,24.,28.,18.,12.,38.,26.,46.]
KG=tuple(np.arange(-0.005,0.00501,0.00025))
P=dict(kgrid=KG,dlo=-900.,dhi=900.,d0sig=1000.,we=25.,floor=.01,dstep=12.5,
       vpen=1.2,vmax=25.,vstep=6.25,wes=WES,sr=40.,dr=-28.)

def run(pin=True, **kw):
    p=dict(P); p.update(kw); nex=nbe=0
    for c,A in zip(caps,AS):
        lv=c["lv"]; k0,a0,a1=dp2.blind_kappa(A,lv)
        dgrid=np.arange(p["dlo"],p["dhi"]+1e-9,p["dstep"])
        vgrid=np.arange(-p["vmax"],p["vmax"]+1e-9,p["vstep"])
        d0=-k0*a0; best=None
        for dk in p["kgrid"]:
            kap=k0*(1+dk)
            E=dp2.emissions(A,lv,kap,dgrid,p["we"],p["floor"],hoff=p["hoff"] if "hoff" in p else 0.,
                            sr=p["sr"],dr=p["dr"],slots=c["sl"],wes=p["wes"])
            pen=lambda d,d0=d0,s=p["d0sig"]:0.5*((d-d0)/s)**2
            tot,bits,dtr,_=dp2.viterbi(E,dgrid,vgrid,p["vpen"],pen,None,pin=pin)
            if best is None or tot<best[0]: best=(tot,bits)
        true=np.array(c["bits"])
        bits=best[1]
        nex+=(bits[32:160]==true[32:160]).all(); nbe+=int((bits[32:160]!=true[32:160]).sum())
    return int(nex),nbe

cases=[("full",dict()),
       ("no header/trailer pin",dict(pin=False)),
       ("no slope state (vmax=0)",dict(vmax=0.,vstep=6.25)),
       ("stiff phase (vpen=1e6)",dict(vpen=1e6)),
       ("free phase per bit (vpen=0, vmax=100)",dict(vpen=0.,vmax=100.,vstep=12.5)),
       ]
for n,kw in cases:
    t=time.time(); a,b=run(**kw)
    print(f"{n:38s} EXACT {a:2d}/54 biterr {b:4d}/6912 = {b/6912:.5f} ({time.time()-t:.0f}s)"); sys.stdout.flush()
