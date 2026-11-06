import sys, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0;T0H=350.0;T1H=700.0;NB=192
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
DS=[]
for c in caps:
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+32]
    bits=fb(c)
    tr=[n-1 for n in range(1,len(work)) if work[n][2]!=work[n-1][2]]
    DS.append(dict(c=c,work=work,bits=bits,tr=tr,
                   sl=[x[1] for x in work], lv=[x[2] for x in work]))
def cumtimes(d,a,b,tau,t0):
    ts=[];cyc=0.0
    sl=d['sl'];lv=d['lv']
    ap=a;bp=b
    for n in range(len(sl)):
        ts.append(t0+cyc*tau)
        k=sl[n]; cyc+=ap[k]+bp[k]*lv[n]
    return ts
def near_edge(mid,bits):
    b0=int(mid//BIT)
    best=None
    for bb in (b0-1,b0,b0+1):
        if bb<0 or bb>=NB: continue
        w=T1H if bits[bb] else T0H
        for e in (bb*BIT, bb*BIT+w):
            dd=abs(e-mid)
            if best is None or dd<best[0]: best=(dd,e)
    return best[1] if best else mid
def assign(d,ts):
    bits=d['bits']
    return [(n,near_edge((ts[n]+ts[n+1])*0.5,bits)) for n in d['tr']]
def hinge(d,asg,ts):
    tot=0.0
    for n,e in asg:
        lo=ts[n]; hi=ts[n+1]
        if e<lo: tot+=lo-e
        elif e>hi: tot+=e-hi
    return tot
def hj(d,a,b,tau,t0,asg=None):
    ts=cumtimes(d,a,b,tau,t0)
    if asg is None: asg=assign(d,ts)
    return hinge(d,asg,ts),asg
a=[3.0,5.5,3.0,5.5,3.0,5.5,5.5,8.5]
b=[0.0]*8
pc=[[62.5,30.0] for _ in DS]
def refit_pc(d,a,b,tau,t0):
    cur,asg=hj(d,a,b,tau,t0)
    for st in (1.0,0.25,0.06,0.015,0.004):
        for _ in range(40):
            imp=False
            for dd in (-st*0.02,st*0.02):
                v,_=hj(d,a,b,tau+dd,t0,asg)
                if v<cur-1e-9: cur=v;tau+=dd;imp=True
            for dd in (-st*10,st*10):
                v,_=hj(d,a,b,tau,t0+dd,asg)
                if v<cur-1e-9: cur=v;t0+=dd;imp=True
            if not imp: break
    cur,asg=hj(d,a,b,tau,t0)
    return cur,tau,t0,asg
for rnd in range(12):
    tot=0.0; asgs=[]
    for i,d in enumerate(DS):
        if rnd==0:
            best=None
            for taui in range(6190,6310,2):
                for t0i in (0,80,160,240):
                    v,_=hj(d,a,b,taui/100.0,float(t0i))
                    if best is None or v<best[0]: best=(v,taui/100.0,float(t0i))
            pc[i]=[best[1],best[2]]
        cur,tau,t0,asg=refit_pc(d,a,b,pc[i][0],pc[i][1])
        pc[i]=[tau,t0]; asgs.append(asg); tot+=cur
    print('rnd',rnd,'hinge',round(tot),'a',[round(x,3) for x in a],'b',[round(x,3) for x in b],flush=True)
    for st in (0.3,0.08,0.02,0.005):
        for k in range(8):
            for arr in (a,b):
                base=arr[k]
                cur=sum(hinge(d,asg,cumtimes(d,a,b,p[0],p[1])) for d,asg,p in zip(DS,asgs,pc))
                for dd in (-st,st):
                    arr[k]=base+dd
                    v=sum(hinge(d,asg,cumtimes(d,a,b,p[0],p[1])) for d,asg,p in zip(DS,asgs,pc))
                    if v<cur-1e-9: cur=v;base=arr[k]
                    else: arr[k]=base
print('a',[round(x,3) for x in a]); print('b',[round(x,3) for x in b])
json.dump({'a':a,'b':b,'pc':pc},open('approaches/dev_missed_zero/dd2.json','w'))
