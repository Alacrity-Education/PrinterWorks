import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()
NB = 192
FRAME_END = NB*1250.0
NOM = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0]

def frame_bits(frame_hex):
    b = bytes.fromhex(frame_hex)
    return [int(x) for byte in b for x in f"{byte:08b}"]

def ideal(t, bits):
    if t < 0: return 0
    k = int(t // 1250.0)
    if k >= len(bits): return 0
    return 1 if (t - k*1250.0) < (700.0 if bits[k] else 350.0) else 0

def fit(samples, bits, Lgrid, win, ostep):
    byslot = [[] for _ in range(8)]
    for it,sl,v in samples:
        byslot[sl].append((it,v))
    best=None
    for L in Lgrid:
        nit = int(FRAME_END/L)+2
        tot=0; offs=[]; detail=[]
        for s in range(8):
            data=[(it,v) for it,v in byslot[s] if it<=nit]
            bg=-1; bo=None
            n=int(2*win/ostep)+1
            for j in range(n):
                o=NOM[s]-win+j*ostep
                g=0
                for it,v in data:
                    if ideal(it*L+o,bits)==v: g+=1
                if g>bg: bg,bo=g,o
            tot+=bg; offs.append(bo); detail.append((bg,len(data)))
        if best is None or tot>best[0]:
            best=(tot,L,offs,detail)
    return best

res={}
for c in caps:
    if c['rep']!=0: continue
    samples = linearize(c['capture'])
    bits = frame_bits(c['frame'])
    Lg=[2495+i*0.5 for i in range(75)]
    b=fit(samples,bits,Lg,300.0,10.0)
    Lg2=[b[1]-0.5+i*0.05 for i in range(21)]
    b=fit(samples,bits,Lg2,300.0,5.0)
    tot=sum(d[1] for d in b[3])
    print(f"{c['pattern']:11s} m={b[0]}/{tot} L={b[1]:.2f} offs={[round(x,1) for x in b[2]]} per={[d[0] for d in b[3]]} n={[d[1] for d in b[3]]}")
    res[c['pattern']]=b
