import sys
from multiprocessing import Pool
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0; W0=375.0; W1=862.0
O=[0.0, 262.5, 612.5, 862.5, 1175.0, 1337.5, 1800.0, 2100.0]

def fb(fh): return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def lvl(t,bits):
    if t<0 or t>=192*BIT: return 0
    k=int(t/BIT); return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0

def job(c):
    s=linearize(c['capture']); bits=fb(c['frame'])
    per={}; last=-1
    for it,sl,v in s:
        per[(it,sl)]=v
        if v: last=max(last,it*8+sl)
    nit=last//8+2
    best=None
    for a in range(80):
        Lm=2485.0+a*0.75
        sc=Lm/2500.0
        oo=[x*sc for x in O]
        for d in range(-30,31):
            D=d*0.02
            for b in range(24):
                ph=-100.0+b*25.0
                bad=0
                for i in range(nit):
                    base=i*Lm+D*i*i+ph
                    for sl in range(8):
                        v=per.get((i,sl))
                        if v is None: continue
                        if lvl(base+oo[sl],bits)!=v: bad+=1
                if best is None or bad<best[0]: best=(bad,Lm,D,ph)
    return (c['pattern'],c['rep'],best)

if __name__=='__main__':
    sub=[c for c in caps if c['rep'] in (0,1)]
    with Pool(12) as p:
        res=p.map(job,sub)
    tot=0
    for pat,rep,b in res:
        tot+=b[0]
        print(f"{pat:11s} r{rep} bad={b[0]:3d} Lm={b[1]:.2f} D={b[2]:.3f} ph={b[3]:.0f}")
    print('TOTAL',tot,tot/27648)
