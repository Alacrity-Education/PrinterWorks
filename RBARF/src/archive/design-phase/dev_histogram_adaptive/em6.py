import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_histogram_adaptive')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0; W0=375.0; W1=862.0
Q=12.5; ER=60; LAM=0.10

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

DS=[]
for c in caps:
    if c['rep'] not in (0,1): continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    last=max(i for i,v in enumerate(levels) if v)
    nit=last//8+1
    per=[[None]*8 for _ in range(nit)]
    for n in range(len(levels)):
        if its[n]<nit: per[its[n]][slots[n]]=levels[n]
    DS.append((c['pattern'],c['rep'],per,frame_bits(c['frame'])))

def lvl(t,bits):
    if t<0: return 0
    k=int(t/BIT)
    if k>=192: return 0
    return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0

NE=2*ER+1
def dp(per,bits,o,Lm,lam=LAM):
    nit=len(per); INF=float('inf')
    def emis(i,R):
        bad=0; pi=per[i]
        for s in range(8):
            v=pi[s]
            if v is None: continue
            if lvl(R+o[s],bits)!=v: bad+=1
        return bad
    cost=[INF]*NE
    for ei in range(NE):
        e=(ei-ER)*Q
        if -400<e<400: cost[ei]=emis(0,e)+abs(e)*0.001
    par=[]
    for i in range(1,nit):
        base=i*Lm
        em=[emis(i,base+(ei-ER)*Q) for ei in range(NE)]
        nc=[INF]*NE; p=[-1]*NE
        for ei in range(NE):
            cc=cost[ei]
            if cc==INF: continue
            for e2 in range(max(0,ei-24),min(NE,ei+25)):
                c2=cc+lam*abs(e2-ei)+em[e2]
                if c2<nc[e2]: nc[e2]=c2; p[e2]=ei
        cost=nc; par.append(p)
    bi=min(range(NE),key=lambda x:cost[x])
    path=[bi]
    for i in range(nit-2,-1,-1):
        bi=par[i][bi]; path.append(bi)
    path.reverse()
    R=[i*Lm+(path[i]-ER)*Q for i in range(nit)]
    return R,sum(emis(i,R[i]) for i in range(nit))

def mstep_global(Rs,o,lo=-1300.0,hi=2600.0,step=12.5):
    newo=[]
    for s in range(8):
        bg=None
        t=lo
        while t<=hi:
            bad=0
            for di,(pat,rep,per,bits) in enumerate(DS):
                R=Rs[di]
                for i in range(len(per)):
                    v=per[i][s]
                    if v is None: continue
                    if lvl(R[i]+t,bits)!=v: bad+=1
            if bg is None or bad<bg[0]: bg=(bad,t)
            t+=step
        newo.append(bg[1])
        print(f"   slot{s}: best off {bg[1]:8.1f}  bad={bg[0]}/3456 ({bg[0]/3456:.2%})")
    return newo

o=[0.0, 256.2, 618.7, 868.8, 1181.2, 1337.5, 1806.2, 2118.8]
Lm=2497.0
for rnd in range(5):
    Rs=[]; tot=0
    for di,(pat,rep,per,bits) in enumerate(DS):
        R,m=dp(per,bits,o,Lm); Rs.append(R); tot+=m
    print(f"round {rnd}: mism={tot}/27648 ({tot/27648:.3%}) o={[round(x,1) for x in o]}")
    o=mstep_global(Rs,o)
    sh=o[0]; o=[x-sh for x in o]
print('final o',[round(x,1) for x in o])
