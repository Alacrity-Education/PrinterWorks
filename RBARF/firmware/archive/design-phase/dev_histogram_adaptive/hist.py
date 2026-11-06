import sys, importlib.util
R='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,R)
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('ha', R+'/approaches/histogram_adaptive.py')
ha=importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
meta,caps=load_dataset()
BIT=1250.0

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

# Alignment DP with known frame; returns times.
def align(levels,bits,P,t0,nmax,T0,T1,Q=6.25,JMAX=8,JPEN=0.06,ERANGE=240):
    NE=2*ERANGE+1; INF=float('inf')
    def idl(t,k):
        if t<0 or k>=192: return 0
        return 1 if (t-k*BIT)<(T1 if bits[k] else T0) else 0
    cost=[INF]*NE
    for ei in range(NE):
        tau=t0+(ei-ERANGE)*Q
        if -80<tau<420:
            k=int(tau/BIT) if tau>=0 else -1
            cost[ei]=0.0 if idl(tau,k)==levels[0] else 1.0
    par=[]
    for n in range(1,nmax):
        base=t0+n*P; obs=levels[n]
        em=[0.0]*NE
        for ei in range(NE):
            t=base+(ei-ERANGE)*Q
            k=int(t/BIT) if t>=0 else -1
            em[ei]=0.0 if idl(t,k)==obs else 1.0
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
    return [t0+n*P+(path[n]-ERANGE)*Q for n in range(nmax)], cost[min(range(NE),key=lambda i:cost[i])]

NBIN=50
h={0:[[0,0] for _ in range(NBIN)],1:[[0,0] for _ in range(NBIN)]}
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]
    bits=frame_bits(c['frame'])
    last=max(i for i,v in enumerate(levels) if v)
    nmax=last+8
    best=None
    for i in range(25):
        P=311.0+i*0.2
        t,cc=align(levels,bits,P,100.0,nmax,375.,865.,Q=12.5,JMAX=4,JPEN=0.12,ERANGE=90)
        if best is None or cc<best[0]: best=(cc,P)
    times,_=align(levels,bits,best[1],100.0,nmax,375.,865.)
    for n in range(nmax):
        t=times[n]
        if t<0: continue
        k=int(t/BIT)
        if k>=192: continue
        ph=t-k*BIT
        b=bits[k]
        bi=int(ph/BIT*NBIN)
        if 0<=bi<NBIN: h[b][bi][levels[n]]+=1
print('phase-bin (25ns each) : frac high  [bit=0] [bit=1]')
for i in range(NBIN):
    a=h[0][i]; bb=h[1][i]
    f0=a[1]/max(1,a[0]+a[1]); f1=bb[1]/max(1,bb[0]+bb[1])
    print(f"{i*25:5d}-{i*25+25:5d}  0:{f0:5.2f}({a[0]+a[1]:4d})  1:{f1:5.2f}({bb[0]+bb[1]:4d})")
