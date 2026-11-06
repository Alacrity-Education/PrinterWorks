import sys, statistics
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
Q=12.5; ER=48
W0=float(sys.argv[1]) if len(sys.argv)>1 else 375.0
W1=float(sys.argv[2]) if len(sys.argv)>2 else 862.0
LAM=float(sys.argv[3]) if len(sys.argv)>3 else 0.10

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
    k=int(t*0.0008)
    if k>=192: return 0
    return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0

NE=2*ER+1
def dp(per,bits,o,Lm,lam=LAM):
    nit=len(per); INF=float('inf')
    sc=Lm/2500.0
    oo=[x*sc for x in o]
    def emis(i,R):
        bad=0; pi=per[i]
        for s in range(8):
            v=pi[s]
            if v is None: continue
            if lvl(R+oo[s],bits)!=v: bad+=1
        return bad
    cost=[INF]*NE
    for ei in range(NE):
        e=(ei-ER)*Q
        if -300<e<300: cost[ei]=emis(0,e)+abs(e)*0.001
    par=[]
    for i in range(1,nit):
        base=i*Lm
        em=[emis(i,base+(ei-ER)*Q) for ei in range(NE)]
        nc=[INF]*NE; p=[-1]*NE
        for ei in range(NE):
            cc=cost[ei]
            if cc==INF: continue
            for e2 in range(max(0,ei-16),min(NE,ei+17)):
                c2=cc+lam*abs(e2-ei)+em[e2]
                if c2<nc[e2]: nc[e2]=c2; p[e2]=ei
        cost=nc; par.append(p)
    bi=min(range(NE),key=lambda x:cost[x])
    path=[bi]
    for i in range(nit-2,-1,-1):
        bi=par[i][bi]; path.append(bi)
    path.reverse()
    R=[i*Lm+(path[i]-ER)*Q for i in range(nit)]
    return R,sum(emis(i,R[i]) for i in range(nit)),oo

def best_align(per,bits,o):
    best=None
    for i in range(31):
        Lm=2484.0+i*1.5
        R,m,oo=dp(per,bits,o,Lm)
        if best is None or m<best[1]: best=(R,m,oo,Lm)
    return best

if __name__=='__main__':
    o=[0.0, 262.5, 612.5, 862.5, 1175.0, 1337.5, 1800.0, 2125.0]
    for rnd in range(4):
        res=[best_align(per,bits,o) for pat,rep,per,bits in DS]
        tot=sum(r[1] for r in res)
        print(f"round {rnd}: mism={tot}/27648 ({tot/27648:.3%}) o={[round(x,1) for x in o]}")
        newo=[]
        for s in range(8):
            bg=None
            for d in range(-28,29):
                cand=o[s]+d*6.25
                bad=0
                for di,(pat,rep,per,bits) in enumerate(DS):
                    R,m,oo,Lm=res[di]
                    sc=Lm/2500.0
                    for i in range(len(per)):
                        v=per[i][s]
                        if v is None: continue
                        if lvl(R[i]+cand*sc,bits)!=v: bad+=1
                if bg is None or bad<bg[0]: bg=(bad,cand)
            newo.append(bg[1]); print(f"   slot{s} {bg[1]:8.1f} bad={bg[0]} ({bg[0]/3456:.2%})")
        sh=newo[0]; o=[x-sh for x in newo]
    res=[best_align(per,bits,o) for pat,rep,per,bits in DS]
    tot=sum(r[1] for r in res)
    print(f"FINAL mism={tot}/27648 ({tot/27648:.3%}) o={[round(x,1) for x in o]} W0={W0} W1={W1}")
    print('Lm:', sorted(round(r[3],1) for r in res))
