import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t, bits):
    if t < 0: return 0
    k = int(t // 1250.0)
    if k >= len(bits): return 0
    return 1 if (t - k*1250.0) < (700.0 if bits[k] else 350.0) else 0

def match(levels, slots, its, bits, L, offs, nmax):
    good=0
    for n in range(nmax):
        t = its[n]*L + offs[slots[n]]
        if ideal(t,bits)==levels[n]: good+=1
    return good

INIT_OFF=[280.,530.,780.,1030.,1280.,1530.,1906.,2219.]
INIT_L=2504.0

def fit(levels,slots,its,bits,nmax):
    off=INIT_OFF[:]; L=INIT_L
    best=match(levels,slots,its,bits,L,off,nmax)
    steps=[80.,40.,20.,10.,5.,2.,1.]
    for st in steps:
        improved=True
        while improved:
            improved=False
            for d in (-st,st):
                Lc=L+d/40.0
                g=match(levels,slots,its,bits,Lc,off,nmax)
                if g>best: best=g; L=Lc; improved=True
            for s in range(8):
                for d in (-st,st):
                    o2=off[:]; o2[s]+=d
                    g=match(levels,slots,its,bits,L,o2,nmax)
                    if g>best: best=g; off=o2; improved=True
    return best,L,off

for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    bits=frame_bits(c['frame'])
    nmax=min(len(levels),780)
    b,L,off=fit(levels,slots,its,bits,nmax)
    print(f"{c['pattern']:11s} {b}/{nmax} L={L:.2f} off={[round(x) for x in off]} gaps={[round(off[i+1]-off[i]) for i in range(7)]+[round(L-off[7]+off[0])]}")
