import sys, cmath, math
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
g=[1,5,9,13,17,21,27,32]
for c in caps:
    if c['rep']!=0: continue
    s=[x for x in linearize(c['capture']) if x[0]<100 and x[2]==1]
    best=None
    t=62.0
    while t<63.3:
        z=0j
        for it,sl,v in s:
            tt=(40*it+g[sl])*t
            z+=cmath.exp(2j*math.pi*tt/BIT)
        r=abs(z)/len(s)
        if best is None or r>best[0]: best=(r,t,cmath.phase(z)*BIT/(2*math.pi))
        t+=0.002
    print(f"{c['pattern']:11s} R={best[0]:.3f} tau={best[1]:.4f} loopns={best[1]*40:.1f} meanph={best[2]:.0f}")
