import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

NB=192
def build_ideal(bits,T0,T1):
    # return function
    def f(t):
        if t<0: return 0
        k=int(t*(1.0/1250.0))
        if k>=NB: return 0
        return 1 if (t-k*1250.0)<(T1 if bits[k] else T0) else 0
    return f

def mismatch(levels,bits,t0,P,T0,T1,nmax,drift=0.0):
    f=build_ideal(bits,T0,T1)
    bad=0
    for n in range(nmax):
        t=t0+n*P+drift*n*n
        if f(t)!=levels[n]: bad+=1
    return bad

res=[]
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]
    bits=frame_bits(c['frame'])
    nmax=790
    best=None
    for iP in range(0,161):
        P=311.0+iP*0.025
        for it0 in range(0,41):
            t0=-100.0+it0*10.0
            b=mismatch(levels,bits,t0,P,350.,700.,nmax)
            if best is None or b<best[0]: best=(b,t0,P)
    b=best
    for t0 in [b[1]-10+i*1.0 for i in range(21)]:
        for P in [b[2]-0.025+i*0.0025 for i in range(21)]:
            m=mismatch(levels,bits,t0,P,350.,700.,nmax)
            if m<best[0]: best=(m,t0,P)
    # now fit T0,T1
    b=best; best2=(b[0],b[1],b[2],350.,700.)
    for T0 in [300+i*10 for i in range(11)]:
        for T1 in [640+i*10 for i in range(13)]:
            for t0 in [b[1]-15+i*3.0 for i in range(11)]:
                for P in [b[2]-0.02+i*0.004 for i in range(11)]:
                    m=mismatch(levels,bits,t0,P,T0,T1,nmax)
                    if m<best2[0]: best2=(m,t0,P,T0,T1)
    print(f"{c['pattern']:11s} lin={best[0]:3d} t0={best[1]:6.1f} P={best[2]:.3f} L={best[2]*8:.1f} | fitT: {best2[0]:3d} t0={best2[1]:.1f} P={best2[2]:.3f} T0={best2[3]} T1={best2[4]}")
    res.append(best2)
print('mean P', sum(r[2] for r in res)/len(res))
