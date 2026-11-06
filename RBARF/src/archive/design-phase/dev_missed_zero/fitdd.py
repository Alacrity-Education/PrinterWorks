import sys, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0;T0H=350.0;T1H=700.0;NB=192;FE=191*BIT+T1H
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
def pen(ph,v,W):
    p=1 if ph<W else 0
    if p==v: return 0.0
    return ph if ph<W else min(ph-W,BIT-ph)
def times(work,a,b,tau,t0):
    """a[k],b[k] in cycles: gap AFTER sample at slot k = a[k]+b[k]*level"""
    ts=[];cyc=0.0
    for it,sl,v in work:
        ts.append(t0+cyc*tau)
        cyc+=a[sl]+b[sl]*v
    return ts
def obj(work,bits,ts,cap=300.0):
    tot=0.0
    for (it,sl,v),tt in zip(work,ts):
        bidx=int(tt//BIT)
        if bidx<0 or bidx>=NB:
            if v: tot+=60.0
            continue
        W=T1H if bits[bidx] else T0H
        tot+=min(cap,pen(tt-bidx*BIT,v,W))
    return tot
DS=[]
for c in caps:
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    DS.append((c,s[:lastn+32],fb(c)))
a=[4.,4.,4.,4.,4.,6.,5.,6.]
b=[0.4]*8
tt0=[(62.5,30.0)]*len(DS)
def fit_local(work,bits,a,b,tau,t0):
    cur=obj(work,bits,times(work,a,b,tau,t0))
    for st in (2.0,0.5,0.12,0.03,0.008):
        for _ in range(30):
            imp=False
            for d in (-st*0.01,st*0.01):
                v=obj(work,bits,times(work,a,b,tau+d,t0))
                if v<cur-1e-9: cur=v;tau=tau+d;imp=True
            for d in (-st*8,st*8):
                v=obj(work,bits,times(work,a,b,tau,t0+d))
                if v<cur-1e-9: cur=v;t0=t0+d;imp=True
            if not imp: break
    return cur,tau,t0
for rnd in range(8):
    tot=0.0;newt=[]
    for (c,work,bits),(tau,t0) in zip(DS,tt0):
        # multistart on first round
        if rnd==0:
            best=None
            for taui in range(6200,6320,2):
                for t0i in range(-100,400,50):
                    v=obj(work,bits,times(work,a,b,taui/100.0,float(t0i)))
                    if best is None or v<best[0]: best=(v,taui/100.0,float(t0i))
            tau,t0=best[1],best[2]
        cur,tau,t0=fit_local(work,bits,a,b,tau,t0)
        newt.append((tau,t0)); tot+=cur
    tt0=newt
    print('rnd',rnd,'J',round(tot),'a',[round(x,3) for x in a],'b',[round(x,3) for x in b])
    # fit a,b globally
    for st in (0.4,0.1,0.025):
        for k in range(8):
            for which in (0,1):
                arr=a if which==0 else b
                base=arr[k]
                cur=sum(obj(w,bt,times(w,a,b,t,o)) for (c,w,bt),(t,o) in zip(DS,tt0))
                for d in (-st,st):
                    arr[k]=base+d
                    v=sum(obj(w,bt,times(w,a,b,t,o)) for (c,w,bt),(t,o) in zip(DS,tt0))
                    if v<cur-1e-9: cur=v;base=arr[k]
                    else: arr[k]=base
print('final a',[round(x,3) for x in a],'b',[round(x,3) for x in b])
for (c,w,bt),(t,o) in zip(DS,tt0):
    print(f"{c['pattern']:11s}{c['rep']} J{obj(w,bt,times(w,a,b,t,o)):8.0f} tau={t:.4f} t0={o:.1f}")
json.dump({'a':a,'b':b},open('approaches/dev_missed_zero/dd.json','w'))
