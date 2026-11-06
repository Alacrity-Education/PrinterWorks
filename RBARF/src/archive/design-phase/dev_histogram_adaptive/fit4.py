import sys, itertools
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()

def frame_bits(frame_hex):
    b = bytes.fromhex(frame_hex)
    return [int(x) for byte in b for x in f"{byte:08b}"]

def ideal(t, bits):
    if t < 0: return 0
    k = int(t // 1250.0)
    if k >= len(bits): return 0
    return 1 if (t - k*1250.0) < (700.0 if bits[k] else 350.0) else 0

def evaluate(levels, slots, bits, G, C, tc, t0, nmax):
    t = t0
    good = 0
    for n in range(nmax):
        v = levels[n]
        if ideal(t, bits) == v: good += 1
        t += (G[slots[n]] + C*v) * tc
    return good

def run(G, C, tcgrid, t0grid, pats=None, verbose=True):
    tots = 0; totn = 0
    out=[]
    for c in caps:
        if c['rep'] != 0: continue
        if pats and c['pattern'] not in pats: continue
        s = linearize(c['capture'])
        levels = [v for _,_,v in s]
        slots = [sl for _,sl,_ in s]
        bits = frame_bits(c['frame'])
        nmax = min(len(levels), 8*100)
        best=None
        for tc in tcgrid:
            for t0 in t0grid:
                g = evaluate(levels, slots, bits, G, C, tc, t0, nmax)
                if best is None or g > best[0]: best=(g,tc,t0)
        tots += best[0]; totn += nmax
        out.append((c['pattern'], best, nmax))
    if verbose:
        for p,b,n in out:
            print(f"  {p:11s} {b[0]}/{n}  tc={b[1]:.3f} t0={b[2]:.1f}")
    return tots, totn

tcgrid=[61.0+i*0.05 for i in range(70)]
t0grid=[i*10.0 for i in range(0,30)]
for C in (0,1,2):
    G=[4,4,4,4,4,6,5,6]
    tt,tn = run(G,C,tcgrid,t0grid,pats={'ones','zeros','aa','rnd1'})
    print("C=",C,"G=",G,"->",tt,"/",tn)
