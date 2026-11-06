import sys, itertools
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
NB=192
def cost(s,w,tau,g,phi,guard=35.0):
    m=0;n=0;lim=NB*BIT
    for it,sl,v in s:
        t=(40*it+g[sl])*tau+phi
        if t>=lim or t<0:
            if v: m+=1
            continue
        b=int(t/BIT); ph=t-b*BIT; ww=w[b]
        if min(abs(ph),abs(ph-ww),abs(BIT-ph))<guard: continue
        n+=1
        if (1 if ph<ww else 0)!=v: m+=1
    return m,n
g=[1,5,9,13,17,21,27,32]
for pat in ['zeros','ones','aa']:
    c=[x for x in caps if x['pattern']==pat and x['rep']==0][0]
    s=[x for x in linearize(c['capture']) if x[0]<100]
    w=[700.0 if b else 350.0 for b in fb(c)]
    best=None
    t=62.0
    while t<63.3:
        phi=-100.0
        while phi<300.0:
            m,n=cost(s,w,t,g,phi)
            if best is None or m<best[0]: best=(m,t,phi,n)
            phi+=5.0
        t+=0.005
    print(pat,best)
