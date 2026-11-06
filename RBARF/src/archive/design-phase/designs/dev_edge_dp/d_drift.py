"""Value of the slope state and of endpoint pinning at the corners."""
import time
import numpy as np
import dp2, synth2
meta, rcaps = dp2.CM.load()
PAY={}
for c in rcaps:
    if c["pattern"] not in PAY:
        b=c["bits"]; PAY[c["pattern"]]=bytes(int("".join(map(str,b[i*8:i*8+8])),2) for i in range(4,20))
WES=[32.,24.,28.,18.,12.,38.,26.,46.]
KG=tuple(np.arange(-0.006,0.0031,0.00025))
P=dict(kgrid=KG,dlo=-900.,dhi=900.,d0sig=1000.,we=25.,floor=.01,dstep=12.5,
       vpen=1.2,vmax=25.,vstep=6.25,wes=WES,sr=40.,dr=-28.)
def run(eps, drift, pin=True, **kw):
    p=dict(P); p.update(kw); nex=nbe=nb=0
    for name,pay in PAY.items():
        for ph in (80.,300.,520.):
            c=synth2.as_cap(pay,eps=eps,t0=ph,drift=drift)
            A=dp2.A_of(c); lv=c["lv"]
            k0,a0,a1=dp2.blind_kappa(A,lv)
            dg=np.arange(p["dlo"],p["dhi"]+1e-9,p["dstep"])
            vg=np.arange(-p["vmax"],p["vmax"]+1e-9,p["vstep"])
            d0=-k0*a0; best=None
            for dk in p["kgrid"]:
                E=dp2.emissions(A,lv,k0*(1+dk),dg,p["we"],p["floor"],sr=p["sr"],
                                dr=p["dr"],slots=c["sl"],wes=p["wes"])
                pen=lambda d,d0=d0,s=p["d0sig"]:0.5*((d-d0)/s)**2
                tot,bits,dtr,_=dp2.viterbi(E,dg,vg,p["vpen"],pen,None,pin=pin)
                if best is None or tot<best[0]: best=(tot,bits)
            bits=best[1]; true=c["bits"]
            nex+=(bits[32:160]==true[32:160]).all(); nbe+=int((bits[32:160]!=true[32:160]).sum()); nb+=128
    return int(nex),nbe,nb
for eps,drift,pin,vmax,tag in [(0.0,0.0,True,25.,"base"),
                               (0.0,0.002,True,25.,"drift+0.2% slope on"),
                               (0.0,0.002,True,0.,"drift+0.2% slope OFF"),
                               (0.0,0.0,False,25.,"no pin"),
                               (-0.075,0.0,True,25.,"eps-7.5 pin"),
                               (-0.075,0.0,False,25.,"eps-7.5 NO pin"),
                               (-0.075,0.002,True,25.,"eps-7.5 drift slope on"),
                               (-0.075,0.002,True,0.,"eps-7.5 drift slope OFF")]:
    t=time.time(); a,b,n=run(eps,drift,pin,vmax=vmax)
    print(f"{tag:26s} eps={eps:+.3f} EXACT {a:2d}/54 biterr {b:4d}/{n} = {b/n:.5f} ({time.time()-t:.0f}s)",flush=True)
