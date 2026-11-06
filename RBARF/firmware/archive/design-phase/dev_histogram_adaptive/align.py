import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t,bits):
    if t<0: return 0
    k=int(t//1250.0)
    if k>=len(bits): return 0
    return 1 if (t-k*1250.0)<(700.0 if bits[k] else 350.0) else 0

Q=12.5
JIT=[-3,-2,-1,0,1,2,3]      # in units of Q
JPEN=0.30

def align(levels,slots,bits,G,nmax,erange=120):
    # state: e index (offset from nominal n*G), value in Q units
    NE=2*erange+1
    INF=1e18
    cost=[INF]*NE
    par=[None]*NE
    for ei in range(NE):
        e=(ei-erange)*Q
        t=0.0+e
        if -200<t<200:
            cost[ei]=(0 if ideal(t,bits)==levels[0] else 1)
    for n in range(1,nmax):
        s=slots[n-1]
        base=G[s]
        nc=[INF]*NE; np_=[None]*NE
        tn=n*sum(G)/8.0
        for ei in range(NE):
            c=cost[ei]
            if c>=INF: continue
            for j in JIT:
                # e' = e + (base - Gmean) + j*Q
                de=base-sum(G)/8.0+j*Q
                ei2=ei+int(round(de/Q))
                if ei2<0 or ei2>=NE: continue
                t=tn+(ei2-erange)*Q
                c2=c+(0 if ideal(t,bits)==levels[n] else 1)+JPEN*abs(j)
                if c2<nc[ei2]:
                    nc[ei2]=c2; np_[ei2]=ei
        cost=nc; par=np_
        yield None
    return

def run(levels,slots,bits,G,nmax,erange=120):
    Q_=Q
    NE=2*erange+1
    INF=1e18
    Gmean=sum(G)/8.0
    cost=[INF]*NE
    parents=[]
    for ei in range(NE):
        t=(ei-erange)*Q_
        if -250<t<250:
            cost[ei]=(0 if ideal(t,bits)==levels[0] else 1)
    for n in range(1,nmax):
        s=slots[n-1]
        de_base=G[s]-Gmean
        nc=[INF]*NE; par=[-1]*NE
        tn=n*Gmean
        for ei in range(NE):
            c=cost[ei]
            if c>=INF: continue
            for j in JIT:
                ei2=ei+int(round((de_base+j*Q_)/Q_))
                if ei2<0 or ei2>=NE: continue
                t=tn+(ei2-erange)*Q_
                c2=c+(0 if ideal(t,bits)==levels[n] else 1)+JPEN*abs(j)
                if c2<nc[ei2]:
                    nc[ei2]=c2; par[ei2]=ei
        cost=nc; parents.append(par)
    best=min(range(NE),key=lambda i:cost[i])
    path=[best]
    for n in range(nmax-2,-1,-1):
        best=parents[n][best]
        path.append(best)
    path.reverse()
    times=[n*Gmean+(path[n]-erange)*Q_ for n in range(nmax)]
    mism=sum(1 for n in range(nmax) if ideal(times[n],bits)!=levels[n])
    return times,mism,cost

import statistics
allgaps={s:[] for s in range(8)}
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]
    bits=frame_bits(c['frame'])
    nmax=780
    G=[313.0]*8
    times,mism,_=run(levels,slots,bits,G,nmax)
    gaps={x:[] for x in range(8)}
    for n in range(nmax-1):
        gaps[slots[n]].append(times[n+1]-times[n])
    med=[statistics.median(gaps[x]) for x in range(8)]
    for x in range(8): allgaps[x].extend(gaps[x])
    print(f"{c['pattern']:11s} mism={mism:3d} t0={times[0]:7.1f} L={sum(med):7.1f} gaps={[round(v) for v in med]}")
print('POOLED med', [round(statistics.median(allgaps[x])) for x in range(8)],
      'mean', [round(statistics.mean(allgaps[x]),1) for x in range(8)])
