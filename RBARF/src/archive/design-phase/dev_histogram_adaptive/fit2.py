import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()
NB = 192
FRAME_END = NB*1250.0

def frame_bits(frame_hex):
    b = bytes.fromhex(frame_hex)
    return [int(x) for byte in b for x in f"{byte:08b}"]

def ideal(t, bits):
    if t < 0: return 0
    k = int(t // 1250.0)
    if k >= len(bits): return 0
    return 1 if (t - k*1250.0) < (700.0 if bits[k] else 350.0) else 0

def fit(samples, bits, Lgrid, ogrid_lo, ogrid_hi, ostep):
    # per-slot sample lists
    byslot = [[] for _ in range(8)]
    for it,sl,v in samples:
        byslot[sl].append((it,v))
    best=None
    for L in Lgrid:
        nit = int(FRAME_END/L)+2
        tot=0; offs=[]
        for s in range(8):
            data=[(it,v) for it,v in byslot[s] if it<=nit]
            bg=-1; bo=None
            o=ogrid_lo
            while o<ogrid_hi:
                g=0
                for it,v in data:
                    if ideal(it*L+o,bits)==v: g+=1
                if g>bg: bg,bo=g,o
                o+=ostep
            tot+=bg; offs.append(bo)
        if best is None or tot>best[0]:
            best=(tot,L,offs,sum(1 for it,sl,v in samples if it<=nit))
    return best

for c in caps:
    if c['rep']!=0: continue
    samples = linearize(c['capture'])
    bits = frame_bits(c['frame'])
    Lg=[2490+i*1.0 for i in range(45)]
    b=fit(samples,bits,Lg,0.0,2600.0,10.0)
    # refine
    Lg2=[b[1]-1.0+i*0.1 for i in range(21)]
    b=fit(samples,bits,Lg2,0.0,2600.0,5.0)
    print(f"{c['pattern']:11s} match={b[0]}/{b[3]} L={b[1]:.2f} offs={[round(x,1) for x in b[2]]}")
