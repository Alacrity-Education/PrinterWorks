"""3-param per-capture fit (scale, t0, drift) + shared slot offsets."""
from common import *
import numpy as np, json
OFF0=np.array(SLOT_OFF); H0,H1=375.0,750.0
meta,caps=load()
D=[]
for c in caps:
    s=linearize(c['capture']); bits=np.array(bits_of(bytes.fromhex(c['frame'])),np.int8)
    it=np.array([i for i,_,_ in s],float); sl=np.array([x for _,x,_ in s]); lv=np.array([v for _,_,v in s],bool)
    D.append((c,it,sl,lv,bits))

def times(off,scale,t0,drift,it,sl):
    p=it*LOOP_NOM+off[sl]
    return t0+scale*p*(1.0+drift*p/240000.0)

def ag(off,scale,t0,drift,it,sl,lv,bits):
    t=times(off,scale,t0,drift,it,sl)
    k=np.floor(t/BIT).astype(np.int64); ok=(k>=0)&(k<len(bits)); kc=np.clip(k,0,len(bits)-1)
    hi=np.where(bits[kc]==1,H1,H0)
    return int(np.count_nonzero((((t-k*BIT)<hi)&ok)==lv))

def fit_cap(off,it,sl,lv,bits):
    best=None
    for scale in np.linspace(0.994,1.010,321):
        for drift in (-0.004,-0.002,0.0,0.002,0.004):
            for t0 in np.arange(-100,400,10.0):
                a=ag(off,scale,t0,drift,it,sl,lv,bits)
                if best is None or a>best[0]: best=(a,scale,t0,drift)
    for _ in range(4):
        a0,s0,t00,d0=best
        for scale in s0+np.linspace(-6e-5,6e-5,13):
            for drift in d0+np.linspace(-1.5e-3,1.5e-3,13):
                for t0 in t00+np.linspace(-12,12,13):
                    a=ag(off,scale,t0,drift,it,sl,lv,bits)
                    if a>best[0]: best=(a,scale,t0,drift)
    return best

off=OFF0.copy()
P=[None]*len(D)
for rnd in range(3):
    tot=0
    for j,(c,it,sl,lv,bits) in enumerate(D):
        P[j]=fit_cap(off,it,sl,lv,bits); tot+=P[j][0]
    N=sum(len(d[3]) for d in D)
    print(f"round {rnd} agree {tot}/{N}={tot/N:.5f} off={np.round(off,1).tolist()}",flush=True)
    for si in range(1,8):
        cur=off[si]; b=None
        for d in np.linspace(-100,100,81):
            o=off.copy(); o[si]=cur+d
            a=sum(ag(o,P[j][1],P[j][2],P[j][3],*D[j][1:]) for j in range(len(D)))
            if b is None or a>b[0]: b=(a,cur+d)
        off[si]=b[1]
json.dump(dict(off=off.tolist(),caps=[dict(pattern=D[j][0]['pattern'],rep=D[j][0]['rep'],
        agree=P[j][0],scale=P[j][1],t0=P[j][2],drift=P[j][3],loop=P[j][1]*2500) for j in range(len(D))]),
        open('fit3.json','w'),indent=1)
print("gaps(cy)",np.round(np.diff(list(off)+[LOOP_NOM])/62.5,3).tolist())
for j in range(len(D)):
    print(f"{D[j][0]['pattern']:11s} {D[j][0]['rep']} ag={P[j][0]:4d} loop={P[j][1]*2500:7.2f} t0={P[j][2]:6.1f} drift={P[j][3]:+.5f}")
