import sys, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize, SLOT_OFFSET_NS
meta,caps=load_dataset()
BIT=1250.0
def frame_bits(c):
    fr=bytes.fromhex(c['frame'])
    return [ (byte>>(7-j))&1 for byte in fr for j in range(8) ]

def widths(bits): return [700.0 if b else 350.0 for b in bits]

def pred(t,w):
    b=int(t//BIT)
    if b<0 or b>=len(w): return 0
    return 1 if (t-b*BIT)<w[b] else 0

def dist_to_edge(t,w):
    b=int(t//BIT)
    if b<0 or b>=len(w): return 1e9
    ph=t-b*BIT
    return min(abs(ph-0.0),abs(ph-w[b]),abs(ph-BIT))

def mism(samples,w,P,o,guard=0.0):
    m=0;n=0
    for it,sl,v in samples:
        t=it*P+o[sl]
        if t> len(w)*BIT+200: break
        if guard>0 and dist_to_edge(t,w)<guard: continue
        n+=1
        if pred(t,w)!=v: m+=1
    return m,n

data=[]
for c in caps:
    s=linearize(c['capture'])
    w=widths(frame_bits(c))
    data.append((c,s,w))

o=list(SLOT_OFFSET_NS)
def fitP(s,w,o):
    best=None
    P=2480.0
    while P<2545.0:
        m,n=mism(s,w,P,o,guard=40.0)
        if best is None or m<best[0]: best=(m,P)
        P+=0.05
    return best

for it_round in range(4):
    Ps=[]
    tot=0;totn=0
    for c,s,w in data:
        m,P=fitP(s,w,o)
        Ps.append(P); tot+=m
    print('round',it_round,'total mism',tot,'P range',min(Ps),max(Ps))
    # refit o
    for k in range(8):
        best=None
        base=o[k]
        for d in [x*2.0 for x in range(-60,61)]:
            oo=list(o); oo[k]=base+d
            m=0
            for (c,s,w),P in zip(data,Ps):
                mm,nn=mism([x for x in s if x[1]==k],w,P,oo,guard=30.0)
                m+=mm
            if best is None or m<best[0]: best=(m,base+d)
        o[k]=best[1]
    print('  o=',[round(x,1) for x in o])
