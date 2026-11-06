import sys, statistics
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
Q=12.5; ER=60; LM=2497.0; LAM=0.10
W={ (0,0):375.,(0,1):375.,(1,0):865.,(1,1):865. }
o=[0.0, 256.2, 618.7, 868.8, 1181.2, 1337.5, 1806.2, 2118.8]

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

def lvl(t,bits,W):
    if t<0: return 0
    k=int(t/BIT)
    if k>=192: return 0
    pb=bits[k-1] if k>0 else 0
    return 1 if (t-k*BIT)<W[(bits[k],pb)] else 0

NE=2*ER+1
def dp(per,bits,o,W,Lm=LM,lam=LAM):
    nit=len(per); INF=float('inf')
    def emis(i,R):
        bad=0
        for s,v in per[i]:
            if lvl(R+o[s],bits,W)!=v: bad+=1
        return bad
    cost=[INF]*NE
    for ei in range(NE):
        e=(ei-ER)*Q
        if -260<e<260: cost[ei]=emis(0,e)+abs(e)*0.002
    par=[]
    for i in range(1,nit):
        base=i*Lm
        em=[emis(i,base+(ei-ER)*Q) for ei in range(NE)]
        nc=[INF]*NE; p=[-1]*NE
        for ei in range(NE):
            c=cost[ei]
            if c==INF: continue
            for e2 in range(max(0,ei-24),min(NE,ei+25)):
                c2=c+lam*abs(e2-ei)+em[e2]
                if c2<nc[e2]: nc[e2]=c2; p[e2]=ei
        cost=nc; par.append(p)
    bi=min(range(NE),key=lambda x:cost[x])
    path=[bi]
    for i in range(nit-2,-1,-1):
        bi=par[i][bi]; path.append(bi)
    path.reverse()
    R=[i*Lm+(path[i]-ER)*Q for i in range(nit)]
    return R,sum(emis(i,R[i]) for i in range(nit))

NBIN=100
hist={k:[[0,0] for _ in range(NBIN)] for k in [(0,0),(0,1),(1,0),(1,1)]}
tot=0
for di,(pat,rep,per,bits) in enumerate(DS):
    R,m=dp(per,bits,o,W); tot+=m
    for i in range(len(per)):
        for s,v in per[i]:
            t=R[i]+o[s]
            if t<0: continue
            k=int(t/BIT)
            if k>=192: continue
            ph=t-k*BIT
            pb=bits[k-1] if k>0 else 0
            bi=int(ph/BIT*NBIN)
            if 0<=bi<NBIN: hist[(bits[k],pb)][bi][v]+=1
print('total mism',tot)
print(' phase      (cur,prev)=(0,0)      (0,1)          (1,0)          (1,1)')
for b in range(NBIN):
    row=f"{b*12.5:6.0f} "
    for k in [(0,0),(0,1),(1,0),(1,1)]:
        a=hist[k][b]; n=a[0]+a[1]
        row+= f"  {a[1]/n:4.2f}({n:4d})" if n else "     -      "
    print(row)
