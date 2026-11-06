import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
W0=375.0; W1=865.0

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def em(levels,slots,its,bits,niter=8,Qr=6.25,W0=W0,W1=W1):
    nit=max(its)+1
    # group samples per iteration
    per=[[] for _ in range(nit)]
    for n in range(len(levels)):
        per[its[n]].append((slots[n],levels[n]))
    o=[s*312.5 for s in range(8)]
    # absolute loop-start guess: T_i = i*2500 (2 bits/loop)  -> we allow free R_i
    R=[0.0]*nit           # absolute loop start time
    for i in range(nit): R[i]=i*2500.0
    NR=int(240000.0/Qr)
    def lvl(t,b_at):
        if t<0: return 0
        k=int(t/BIT)
        if k>=192: return 0
        return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0
    for _ in range(niter):
        # E: per-iteration absolute loop start, searched near previous estimate
        tot=0
        for i in range(nit):
            if not per[i]: continue
            lo=R[i]-700.0; hi=R[i]+700.0
            if i>0 and R[i-1] is not None: lo=max(lo,R[i-1]+1500.0)
            bg=None
            t=lo
            while t<=hi:
                bad=0
                for s,v in per[i]:
                    if lvl(t+o[s],None)!=v: bad+=1
                if bg is None or bad<bg[0]: bg=(bad,t)
                t+=Qr
            R[i]=bg[1]; tot+=bg[0]
        # M: slot offsets
        for s in range(8):
            bg=None
            for d in range(-40,41):
                cand=s*312.5+d*6.25
                bad=0
                for i in range(nit):
                    for ss,v in per[i]:
                        if ss!=s: continue
                        if lvl(R[i]+cand,None)!=v: bad+=1
                if bg is None or bad<bg[0]: bg=(bad,cand)
            o[s]=bg[1]
    tot=0
    for i in range(nit):
        for s,v in per[i]:
            if lvl(R[i]+o[s],None)!=v: tot+=1
    return R,o,tot

for c in caps:
    if c['rep']!=0: continue
    if c['pattern'] not in ('zeros','ones','aa','rnd2','nibbles','blocks'): continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    last=max(i for i,v in enumerate(levels) if v)
    nit=last//8+1
    keep=[n for n in range(len(levels)) if its[n]<nit]
    levels=[levels[n] for n in keep]; slots=[slots[n] for n in keep]; its=[its[n] for n in keep]
    bits=frame_bits(c['frame'])
    R,o,tot=em(levels,slots,its,bits)
    print(f"=== {c['pattern']}  mism={tot}/{len(levels)}  offs={[round(x) for x in o]} gaps={[round(o[i+1]-o[i]) for i in range(7)]}")
    dl=[R[i+1]-R[i] for i in range(len(R)-1)]
    print('   L per loop:', ' '.join(f"{x:.0f}" for x in dl[:48]))
    print('   L per loop:', ' '.join(f"{x:.0f}" for x in dl[48:]))
