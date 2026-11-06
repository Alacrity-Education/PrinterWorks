import sys, importlib.util, statistics
R='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,R)
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t,bits,T0=350.,T1=700.):
    if t<0: return 0
    k=int(t/BIT)
    if k>=192: return 0
    return 1 if (t-k*BIT)<(T1 if bits[k] else T0) else 0

# Fine alignment DP with known frame: state = e bucket; free jitter with small pen
def align(levels,bits,P,t0,nmax,Q=6.25,JMAX=8,JPEN=0.05,ERANGE=200):
    NE=2*ERANGE+1; INF=float('inf')
    cost=[INF]*NE
    for ei in range(NE):
        tau=t0+(ei-ERANGE)*Q
        if -80<tau<420: cost[ei]=0.0 if ideal(tau,bits)==levels[0] else 1.0
    par=[]
    for n in range(1,nmax):
        base=t0+n*P; obs=levels[n]
        em=[0.0]*NE
        for ei in range(NE):
            em[ei]=0.0 if ideal(base+(ei-ERANGE)*Q,bits)==obs else 1.0
        nc=[INF]*NE; p=[-1]*NE
        for ei in range(NE):
            c=cost[ei]
            if c==INF: continue
            for j in range(-JMAX,JMAX+1):
                e2=ei+j
                if e2<0 or e2>=NE: continue
                c2=c+JPEN*abs(j)+em[e2]
                if c2<nc[e2]: nc[e2]=c2; p[e2]=ei
        cost=nc; par.append(p)
    bi=min(range(NE),key=lambda i:cost[i])
    path=[bi]
    for n in range(nmax-2,-1,-1):
        bi=par[n][bi]; path.append(bi)
    path.reverse()
    times=[t0+n*P+(path[n]-ERANGE)*Q for n in range(nmax)]
    mm=[n for n in range(nmax) if ideal(times[n],bits)!=levels[n]]
    return times,mm

byslot={s:[] for s in range(8)}
bylev={0:[],1:[]}
bypair={}
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]
    bits=frame_bits(c['frame'])
    last=max(i for i,v in enumerate(levels) if v)
    nmax=last+8
    # estimate P by scanning
    best=None
    for i in range(21):
        P=311.0+i*0.2
        times,mm=align(levels,bits,P,100.0,nmax,Q=12.5,JMAX=4,JPEN=0.1,ERANGE=80)
        if best is None or len(mm)<best[0]: best=(len(mm),P)
    P=best[1]
    times,mm=align(levels,bits,P,100.0,nmax)
    gaps=[times[n+1]-times[n] for n in range(nmax-1)]
    for n in range(nmax-1):
        byslot[slots[n]].append(gaps[n])
        bylev[levels[n]].append(gaps[n])
        key=(slots[n],levels[n])
        bypair.setdefault(key,[]).append(gaps[n])
    mmph=[]
    for n in mm:
        t=times[n]; k=int(t/BIT); mmph.append(round(t-k*BIT))
    print(f"{c['pattern']:11s} P={P:.2f} mism={len(mm):3d} drift={times[nmax-1]-(100.0+(nmax-1)*P):7.1f} mmphases={sorted(mmph)[:24]}")
print()
print('gap by slot:', [round(statistics.mean(byslot[s]),1) for s in range(8)])
print('gap by lev :', [round(statistics.mean(bylev[l]),1) for l in (0,1)], [len(bylev[l]) for l in (0,1)])
for s in range(8):
    print(' slot',s,[ (l, round(statistics.mean(bypair.get((s,l),[0])),1), len(bypair.get((s,l),[]))) for l in (0,1)])
