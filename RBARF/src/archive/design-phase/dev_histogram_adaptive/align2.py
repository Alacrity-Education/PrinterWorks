import sys, statistics
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t,bits,T0,T1):
    if t<0: return 0
    k=int(t//1250.0)
    if k>=len(bits): return 0
    return 1 if (t-k*1250.0)<(T1 if bits[k] else T0) else 0

def run(levels,slots,bits,G,nmax,Q=12.5,JMAX=6,JPEN=0.25,erange=200,T0=350.,T1=700.):
    NE=2*erange+1; INF=1e18
    Gmean=sum(G)/8.0
    JIT=list(range(-JMAX,JMAX+1))
    cost=[INF]*NE
    for ei in range(NE):
        t=(ei-erange)*Q
        if -250<t<250: cost[ei]=(0 if ideal(t,bits,T0,T1)==levels[0] else 1)
    parents=[]
    for n in range(1,nmax):
        s=slots[n-1]
        shift=int(round((G[s]-Gmean)/Q))
        nc=[INF]*NE; par=[-1]*NE
        tn=n*Gmean
        for ei in range(NE):
            c=cost[ei]
            if c>=INF: continue
            for j in JIT:
                ei2=ei+shift+j
                if ei2<0 or ei2>=NE: continue
                t=tn+(ei2-erange)*Q
                c2=c+(0 if ideal(t,bits,T0,T1)==levels[n] else 1)+JPEN*abs(j)
                if c2<nc[ei2]: nc[ei2]=c2; par[ei2]=ei
        cost=nc; parents.append(par)
    best=min(range(NE),key=lambda i:cost[i])
    path=[best]
    for n in range(nmax-2,-1,-1):
        best=parents[n][best]; path.append(best)
    path.reverse()
    times=[n*Gmean+(path[n]-erange)*Q for n in range(nmax)]
    mm=[n for n in range(nmax) if ideal(times[n],bits,T0,T1)!=levels[n]]
    return times,mm

for JPEN in (0.1,0.25):
  print("=== JPEN",JPEN)
  tot=0
  for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]
    bits=frame_bits(c['frame'])
    nmax=780
    G=[313.0]*8
    times,mm=run(levels,slots,bits,G,nmax,JPEN=JPEN)
    tot+=len(mm)
    res=[times[n]-n*313.0 for n in range(nmax)]
    print(f"{c['pattern']:11s} mism={len(mm):3d} res: "+' '.join(f"{res[i]:.0f}" for i in range(0,nmax,60)))
  print("TOTAL",tot)
