import numpy as np, dp2, synth2
meta, rcaps = dp2.CM.load()
PAY={}
for c in rcaps:
    if c["pattern"] not in PAY:
        b=c["bits"]; PAY[c["pattern"]]=bytes(int("".join(map(str,b[i*8:i*8+8])),2) for i in range(4,20))
print("eps      median      p95|e|      min       max")
for eps in (-0.075,-0.05,-0.025,0.0,0.025,0.05,0.075):
    e=[]
    for name,pay in PAY.items():
        for ph in (80.,300.,520.):
            c=synth2.as_cap(pay,eps=eps,t0=ph); A=dp2.A_of(c)
            k0,_,_=dp2.blind_kappa(A,c["lv"])
            e.append(k0/(1/(1+eps))-1)
    e=np.array(e); print(f"{eps:+.3f}  {np.median(e):+.5f}  {np.percentile(np.abs(e),95):.5f}  {e.min():+.5f}  {e.max():+.5f}")
e=[]
for c in rcaps:
    A=dp2.A_of(c); k0,_,_=dp2.blind_kappa(A,c["lv"])
    e.append(k0/dp2.F["nuis"][c["key"]][1]-1)
e=np.array(e); print(f"REAL    {np.median(e):+.5f}  {np.percentile(np.abs(e),95):.5f}  {e.min():+.5f}  {e.max():+.5f}")
