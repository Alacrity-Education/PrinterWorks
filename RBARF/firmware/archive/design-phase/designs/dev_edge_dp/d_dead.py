"""Per-capture distribution of information-dead payload bits vs eps."""
import numpy as np, dp2, synth2
meta, rcaps = dp2.CM.load()
PAY={}
for c in rcaps:
    if c["pattern"] not in PAY:
        b=c["bits"]; PAY[c["pattern"]]=bytes(int("".join(map(str,b[i*8:i*8+8])),2) for i in range(4,20))
PH=[40.,120.,200.,300.,400.,480.,560.]
print(f"{'eps':>7s} {'mean':>6s} {'med':>5s} {'p90':>5s} {'max':>5s} {'frac cap 0 dead':>16s}")
for eps in (-0.08,-0.075,-0.05,-0.025,-0.01,0.0,0.005,0.01,0.02,0.025,0.05,0.075):
    n=[]
    for name,pay in PAY.items():
        for ph in PH:
            c=synth2.as_cap(pay,eps=eps,t0=ph)
            t=ph+(1/(1+eps))*dp2.A_of(c)
            j=np.floor(t/1250).astype(int); m=(j>=32)&(j<160)
            u=t[m]-j[m]*1250; d=(u>=synth2.H0)&(u<synth2.H1)
            cnt=np.zeros(192); np.add.at(cnt,j[m],d.astype(float))
            n.append(int((cnt[32:160]==0).sum()))
    n=np.array(n)
    print(f"{eps:+7.3f} {n.mean():6.2f} {np.median(n):5.0f} {np.percentile(n,90):5.0f} {n.max():5d} {(n==0).mean():16.3f}")
# real captures, same metric with the calibration time base
n=[]
for c in rcaps:
    t0,k=dp2.F["nuis"][c["key"]][:2]
    t=t0+k*dp2.A_of(c)
    j=np.floor(t/1250).astype(int); m=(j>=32)&(j<160)
    u=t[m]-j[m]*1250; d=(u>=synth2.H0)&(u<synth2.H1)
    cnt=np.zeros(192); np.add.at(cnt,j[m],d.astype(float))
    n.append(int((cnt[32:160]==0).sum()))
n=np.array(n)
print(f"REAL    {n.mean():6.2f} {np.median(n):5.0f} {np.percentile(n,90):5.0f} {n.max():5d} {(n==0).mean():16.3f}")
