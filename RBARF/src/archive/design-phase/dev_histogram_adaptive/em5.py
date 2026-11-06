import sys, statistics
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
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
def dp(per,bits,o,c,Lm,lam=LAM):
    nit=len(per); INF=float('inf')
    # per-iteration slot time offsets including data-dependent shift
    off=[]; Ladd=[]
    for i in range(nit):
        h=0; oo=[]
        for s in range(8):
            oo.append(o[s]+c*h)
            v=per[i][s]
            if v: h+=1
        off.append(oo); Ladd.append(c*h)
    def emis(i,R):
        bad=0; oo=off[i]; pi=per[i]
        for s in range(8):
            v=pi[s]
            if v is None: continue
            if lvl(R+oo[s],bits)!=v: bad+=1
        return bad
    cost=[INF]*NE
    for ei in range(NE):
        e=(ei-ER)*Q
        if -260<e<260: cost[ei]=emis(0,e)+abs(e)*0.002
    par=[]; bases=[0.0]
    for i in range(1,nit):
        bases.append(bases[-1]+Lm+Ladd[i-1])
    for i in range(1,nit):
        base=bases[i]
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
    R=[bases[i]+(path[i]-ER)*Q for i in range(nit)]
    return R,sum(emis(i,R[i]) for i in range(nit)),off

base_o=[0.0, 256.2, 618.7, 868.8, 1181.2, 1337.5, 1806.2, 2118.8]
for c in (0.0, 31.25, 62.5, -31.25, -62.5):
    o=list(base_o)
    for Lmb in (2497.0,):
        Lm=Lmb-c*3.4
        tot=0
        # 3 EM rounds refitting o
        for rnd in range(4):
            Rs=[]; tot=0
            for di,(pat,rep,per,bits) in enumerate(DS):
                R,m,off=dp(per,bits,o,c,Lm); Rs.append((R,off)); tot+=m
            newo=[]
            for s in range(8):
                bg=None
                for d in range(-32,33):
                    cand=o[s]+d*6.25
                    bad=0
                    for di,(pat,rep,per,bits) in enumerate(DS):
                        R,off=Rs[di]
                        for i in range(len(per)):
                            v=per[i][s]
                            if v is None: continue
                            sh=off[i][s]-o[s]
                            if lvl(R[i]+cand+sh,bits)!=v: bad+=1
                    if bg is None or bad<bg[0]: bg=(bad,cand)
                newo.append(bg[1])
            sh=newo[0]; o=[x-sh for x in newo]
        print(f"c={c:7.2f} Lm={Lm:.1f} mism={tot}/27648 ({tot/27648:.3%}) o={[round(x,1) for x in o]}")
