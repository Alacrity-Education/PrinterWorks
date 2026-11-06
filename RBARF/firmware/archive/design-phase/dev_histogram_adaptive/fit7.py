import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
P=[1,5,9,13,17,21,27,32]

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t,bits):
    if t<0: return 0
    k=int(t//1250.0)
    if k>=len(bits): return 0
    return 1 if (t-k*1250.0)<(700.0 if bits[k] else 350.0) else 0

def m(levels,slots,its,bits,L,tc,ph,nmax):
    off=[p*tc+ph for p in P]
    g=0
    for n in range(nmax):
        if ideal(its[n]*L+off[slots[n]],bits)==levels[n]: g+=1
    return g

for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    bits=frame_bits(c['frame'])
    nmax=768
    best=None
    for iL in range(0,120):
        L=2470.0+iL*0.5
        for itc in range(0,40):
            tc=60.0+itc*0.15
            for iph in range(0,20):
                ph=-100.0+iph*20.0
                g=m(levels,slots,its,bits,L,tc,ph,nmax)
                if best is None or g>best[0]: best=(g,L,tc,ph)
    # refine
    b=best
    for L in [b[1]-0.5+i*0.05 for i in range(21)]:
        for tc in [b[2]-0.15+i*0.02 for i in range(16)]:
            for ph in [b[3]-20+i*4 for i in range(11)]:
                g=m(levels,slots,its,bits,L,tc,ph,nmax)
                if g>best[0]: best=(g,L,tc,ph)
    print(f"{c['pattern']:11s} {best[0]}/{nmax} L={best[1]:.2f} tc={best[2]:.3f} ph={best[3]:.1f} W={best[1]/best[2]:.2f}")
