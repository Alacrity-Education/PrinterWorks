import sys, cmath, math
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
G=[1,5,9,13,17,21,27,32]
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
def periodo(s):
    best=None; t=62.0
    while t<63.3:
        z=0j
        for it,sl,v in s: z+=cmath.exp(2j*math.pi*(40*it+G[sl])*t/BIT)
        r=abs(z)
        if best is None or r>best[0]: best=(r,t)
        t+=0.001
    return best[1]
data=[]
for c in caps:
    s=[x for x in linearize(c['capture']) if x[0]<100]
    hs=[x for x in s if x[2]==1]
    tau=periodo(hs)
    w=[700.0 if b else 350.0 for b in fb(c)]
    data.append((c,s,w,tau))
    if c['rep']==0: pass

# now sweep o[k] with P = 40*tau
def sweep(k,o,guard=30.0):
    res=[]
    for cand in range(0,2600,10):
        m=0;n=0
        for c,s,w,tau in data:
            P=40*tau
            for it,sl,v in s:
                if sl!=k: continue
                t=it*P+cand*tau/62.44*1.0 if False else it*P+cand
                if t>=192*BIT: 
                    if v: m+=1
                    continue
                b=int(t/BIT); ph=t-b*BIT; ww=w[b]
                if min(abs(ph),abs(ph-ww),abs(BIT-ph))<guard: continue
                n+=1
                if (1 if ph<ww else 0)!=v: m+=1
        res.append((m,cand,n))
    res.sort()
    return res[:5]
for k in range(8):
    print(k, 'doc=',round(G[k]*62.44,1), sweep(k,None))
