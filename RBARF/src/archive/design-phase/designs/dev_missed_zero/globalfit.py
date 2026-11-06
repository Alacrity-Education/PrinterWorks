"""Global fit: 8 slot offsets + h0/h1 + per-capture (scale,t0).

Coordinate descent maximizing total sample-level agreement over all 54
captures.  Ground truth used (analysis only).
"""
from common import *
import numpy as np, json

meta, caps = load()
DATA=[]
for c in caps:
    s = linearize(c['capture'])
    bits = np.array(bits_of(bytes.fromhex(c['frame'])), dtype=np.int8)
    it = np.array([i for i,_,_ in s], dtype=float)
    sl = np.array([x for _,x,_ in s], dtype=int)
    lv = np.array([v for _,_,v in s], dtype=bool)
    DATA.append((c,it,sl,lv,bits))

def agree(off, h0, h1, scale, t0, it, sl, lv, bits):
    t = t0 + scale*(it*LOOP_NOM + off[sl])
    k = np.floor(t/BIT).astype(np.int64)
    ok = (k>=0)&(k<len(bits))
    kc = np.clip(k,0,len(bits)-1)
    hi = np.where(bits[kc]==1, h1, h0)
    pred = ((t-k*BIT)<hi)&ok
    return int(np.count_nonzero(pred==lv))

def fit_cap(off,h0,h1,it,sl,lv,bits,s0=None,t00=None):
    best=None
    if s0 is None:
        ss=np.linspace(0.997,1.016,761); ts=np.arange(-500,500,8.0)
    else:
        ss=s0+np.linspace(-4e-4,4e-4,41); ts=t00+np.linspace(-60,60,61)
    for s in ss:
        base=s*(it*LOOP_NOM+off[sl])
        for t0 in ts:
            t=base+t0
            k=np.floor(t/BIT).astype(np.int64)
            ok=(k>=0)&(k<len(bits)); kc=np.clip(k,0,len(bits)-1)
            hi=np.where(bits[kc]==1,h1,h0)
            a=int(np.count_nonzero((((t-k*BIT)<hi)&ok)==lv))
            if best is None or a>best[0]: best=(a,float(s),float(t0))
    return best

off = np.array(SLOT_OFF)
h0,h1 = 375.0, 750.0
params=[None]*len(DATA)
for rnd in range(6):
    # E-step: per capture
    tot=0
    for j,(c,it,sl,lv,bits) in enumerate(DATA):
        if params[j] is None:
            r=fit_cap(off,h0,h1,it,sl,lv,bits)
        else:
            r=fit_cap(off,h0,h1,it,sl,lv,bits,params[j][1],params[j][2])
        params[j]=r; tot+=r[0]
    N=sum(len(d[3]) for d in DATA)
    print(f"round {rnd} agree {tot}/{N} = {tot/N:.5f}  off={np.round(off,1).tolist()} h0={h0:.1f} h1={h1:.1f}")
    # M-step: slot offsets (slot 0 fixed at 0; t0 absorbs it)
    for s_idx in range(1,8):
        cur=off[s_idx]; bestv=None
        for d in np.linspace(-140,140,113):
            o2=off.copy(); o2[s_idx]=cur+d
            a=sum(agree(o2,h0,h1,params[j][1],params[j][2],*DATA[j][1:]) for j in range(len(DATA)))
            if bestv is None or a>bestv[0]: bestv=(a,cur+d)
        off[s_idx]=bestv[1]
    for name in ('h0','h1'):
        cur = h0 if name=='h0' else h1
        bestv=None
        for d in np.linspace(-120,120,97):
            hh0,hh1=(cur+d,h1) if name=='h0' else (h0,cur+d)
            a=sum(agree(off,hh0,hh1,params[j][1],params[j][2],*DATA[j][1:]) for j in range(len(DATA)))
            if bestv is None or a>bestv[0]: bestv=(a,cur+d)
        if name=='h0': h0=bestv[1]
        else: h1=bestv[1]

json.dump(dict(off=off.tolist(),h0=h0,h1=h1,loop_nom=LOOP_NOM,
               caps=[dict(pattern=DATA[j][0]['pattern'],rep=DATA[j][0]['rep'],
                          agree=params[j][0],scale=params[j][1],t0=params[j][2],
                          loop_ns=params[j][1]*LOOP_NOM) for j in range(len(DATA))]),
          open('globalfit.json','w'), indent=1)
print("gaps(ns)", np.round(np.diff(list(off)+[LOOP_NOM]),1).tolist())
print("gaps(cy)", np.round(np.diff(list(off)+[LOOP_NOM])/62.5,2).tolist())
