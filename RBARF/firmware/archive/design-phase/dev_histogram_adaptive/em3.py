import sys, statistics
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
W0=375.0; W1=865.0
Q=12.5
ER=60
LM=2497.0
LAM=float(sys.argv[1]) if len(sys.argv)>1 else 0.10

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

DS=[]
for c in caps:
    if c['rep'] not in (0,1): continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    last=max(i for i,v in enumerate(levels) if v)
    nit=last//8+1
    per=[[] for _ in range(nit)]
    for n in range(len(levels)):
        if its[n]<nit: per[its[n]].append((slots[n],levels[n]))
    DS.append((c['pattern'],c['rep'],per,frame_bits(c['frame'])))

def lvl(t,bits):
    if t<0: return 0
    k=int(t/BIT)
    if k>=192: return 0
    return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0

NE=2*ER+1
def dp(per,bits,o,Lm=LM,lam=LAM):
    nit=len(per)
    INF=float('inf')
    # emission table
    def emis(i,R):
        bad=0
        for s,v in per[i]:
            if lvl(R+o[s],bits)!=v: bad+=1
        return bad
    cost=[INF]*NE
    for ei in range(NE):
        e=(ei-ER)*Q
        if -260<e<260:
            cost[ei]=emis(0,0.0+e)+abs(e)*0.002
    par=[]
    for i in range(1,nit):
        base=i*Lm
        em=[emis(i,base+(ei-ER)*Q) for ei in range(NE)]
        nc=[INF]*NE; p=[-1]*NE
        for ei in range(NE):
            c=cost[ei]
            if c==INF: continue
            for e2 in range(NE):
                d=abs(e2-ei)
                if d>24: continue
                c2=c+lam*d+em[e2]
                if c2<nc[e2]: nc[e2]=c2; p[e2]=ei
        cost=nc; par.append(p)
    bi=min(range(NE),key=lambda x:cost[x])
    path=[bi]
    for i in range(nit-2,-1,-1):
        bi=par[i][bi]; path.append(bi)
    path.reverse()
    R=[i*Lm+(path[i]-ER)*Q for i in range(nit)]
    mism=sum(emis(i,R[i]) for i in range(nit))
    return R,mism

o=[312.5+s*312.5 for s in range(8)]
o=[0.0,250.0,556.2,868.8,1181.2,1493.8,1806.2,2118.8]
Rs=[None]*len(DS)
for it in range(6):
    tot=0; ntot=0
    for di,(pat,rep,per,bits) in enumerate(DS):
        R,m=dp(per,bits,o)
        Rs[di]=R; tot+=m; ntot+=sum(len(x) for x in per)
    # M step pooled
    newo=[]
    for s in range(8):
        bg=None
        for d in range(-40,41):
            cand=o[s]+d*6.25
            bad=0
            for di,(pat,rep,per,bits) in enumerate(DS):
                R=Rs[di]
                for i in range(len(per)):
                    for ss,v in per[i]:
                        if ss==s and lvl(R[i]+cand,bits)!=v: bad+=1
            if bg is None or bad<bg[0]: bg=(bad,cand)
        newo.append(bg[1])
    shift=newo[0]
    o=[x-shift for x in newo]
    print(f"it{it}: mism={tot}/{ntot} ({tot/ntot:.3%}) o={[round(x,1) for x in o]} gaps={[round(o[i+1]-o[i],1) for i in range(7)]}")
tot=0
for di,(pat,rep,per,bits) in enumerate(DS):
    R,m=dp(per,bits,o); Rs[di]=R
    dl=[R[i+1]-R[i] for i in range(len(R)-1)]
    print(f"  {pat:11s} r{rep} mism={m:3d} Lmean={statistics.mean(dl):.1f} Lsd={statistics.pstdev(dl):.1f}")
    tot+=m
print('TOTAL',tot,'lam',LAM)
