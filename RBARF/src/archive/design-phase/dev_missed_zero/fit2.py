import sys, itertools
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
def frame_bits(c):
    fr=bytes.fromhex(c['frame'])
    return [ (byte>>(7-j))&1 for byte in fr for j in range(8) ]
def widths(bits): return [700.0 if b else 350.0 for b in bits]

data=[]
for c in caps:
    s=linearize(c['capture'])
    w=widths(frame_bits(c))
    # only samples within frame window (+ a bit)
    s=[x for x in s if x[0]<100]
    data.append((c,s,w))
NB=192
def cost(s,w,tau,g,guard=35.0):
    m=0;n=0
    lim=NB*BIT
    for it,sl,v in s:
        t=(40*it+g[sl])*tau
        if t>=lim: 
            if v: m+=1
            continue
        b=int(t/BIT); ph=t-b*BIT; ww=w[b]
        if min(abs(ph),abs(ph-ww),abs(BIT-ph))<guard: continue
        n+=1
        if (1 if ph<ww else 0)!=v: m+=1
    return m,n

def gaps_to_g(G):
    g=[1]
    for j in range(7): g.append(g[-1]+G[j])
    return g

# candidate gap vectors: doc gaps [4,4,4,4,4,6,5,6] + 3 extra cycles distributed
DOC=[4,4,4,4,4,6,5,6]
cands=[]
for extra in itertools.product(range(4),repeat=8):
    if sum(extra)==3:
        cands.append([DOC[j]+extra[j] for j in range(8)])
print('n cands',len(cands))

def fit_tau(s,w,g):
    best=None
    t=62.0
    while t<63.3:
        m,n=cost(s,w,t,g)
        if best is None or m<best[0]: best=(m,t)
        t+=0.005
    return best

g=gaps_to_g(DOC+[0])[:8] if False else gaps_to_g([4,4,4,4,4,6,5,7])
taus=[]
for rnd in range(3):
    taus=[];tot=0
    for c,s,w in data:
        m,t=fit_tau(s,w,g); taus.append(t); tot+=m
    print('rnd',rnd,'g',g,'tot mism',tot,'tau',round(min(taus),3),round(max(taus),3))
    best=None
    for G in cands:
        gg=gaps_to_g(G)
        m=0
        for (c,s,w),t in zip(data,taus): m+=cost(s,w,t,gg)[0]
        if best is None or m<best[0]: best=(m,gg,G)
    print('   best G',best[2],'mism',best[0])
    g=best[1]
