import sys, itertools
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()
PATS = ['zeros','ones','aa','rnd1','edges','blocks','dense','count']

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def ideal(t, bits):
    if t < 0: return 0
    k = int(t // 1250.0)
    if k >= len(bits): return 0
    return 1 if (t - k*1250.0) < (700.0 if bits[k] else 350.0) else 0

DATA=[]
for c in caps:
    if c['rep']!=0 or c['pattern'] not in PATS: continue
    s=linearize(c['capture'])
    DATA.append((c['pattern'],[v for _,_,v in s],[sl for _,sl,_ in s],frame_bits(c['frame'])))

def ev(levels,slots,bits,G,C,tc,t0,nmax,mode):
    t=t0; good=0; prev=0
    for n in range(nmax):
        v=levels[n]
        if ideal(t,bits)==v: good+=1
        d = v if mode==0 else prev
        t += (G[slots[n]] + C*d)*tc
        prev=v
    return good

TCG=[61.0+i*0.1 for i in range(35)]
T0G=[i*20.0 for i in range(0,16)]

def total(G,C,mode=0,refine=False,verbose=False):
    tt=0;tn=0;det=[]
    for pat,levels,slots,bits in DATA:
        nmax=min(len(levels),800)
        best=None
        for tc in TCG:
            for t0 in T0G:
                g=ev(levels,slots,bits,G,C,tc,t0,nmax,mode)
                if best is None or g>best[0]: best=(g,tc,t0)
        if refine:
            b=best
            for tc in [b[1]-0.1+i*0.01 for i in range(21)]:
                for t0 in [b[2]-20+i*4 for i in range(11)]:
                    g=ev(levels,slots,bits,G,C,tc,t0,nmax,mode)
                    if g>best[0]: best=(g,tc,t0)
        tt+=best[0]; tn+=nmax; det.append((pat,best,nmax))
    if verbose:
        for p,b,n in det: print(f"    {p:11s} {b[0]}/{n} tc={b[1]:.3f} t0={b[2]:.1f}")
    return tt,tn

best_G=[4,4,4,4,4,6,5,6]; best_C=1; best_mode=0
bt,_=total(best_G,best_C,best_mode)
print("start",bt)
improved=True
it=0
while improved and it<12:
    improved=False; it+=1
    for s in range(8):
        for d in (-2,-1,1,2,3):
            G=best_G[:]; G[s]+=d
            if G[s]<2 or G[s]>14: continue
            for C in (0,1,2):
                for mode in (0,1):
                    tt,_=total(G,C,mode)
                    if tt>bt:
                        bt=tt; best_G=G[:]; best_C=C; best_mode=mode; improved=True
                        print("  ->",bt,best_G,best_C,best_mode)
print("FINAL",bt,best_G,best_C,best_mode)
tt,tn=total(best_G,best_C,best_mode,refine=True,verbose=True)
print(tt,tn,tt/tn)
