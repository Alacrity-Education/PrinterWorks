import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0
W0=375.0; W1=865.0

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

DS=[]
for c in caps:
    if c['rep'] not in (0,1): continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]; slots=[sl for _,sl,_ in s]; its=[i for i,_,_ in s]
    last=max(i for i,v in enumerate(levels) if v)
    nit=last//8+1
    per=[[] for _ in range(nit)]
    for n in range(len(levels)):
        if its[n]<nit: per[its[n]].append((slots[n],levels[n]))
    DS.append((c['pattern'],per,frame_bits(c['frame'])))

def lvl(t,bits,W0,W1):
    if t<0: return 0
    k=int(t/BIT)
    if k>=192: return 0
    return 1 if (t-k*BIT)<(W1 if bits[k] else W0) else 0

def estep(per,bits,o,R,Qr,W0,W1,win=800.0):
    tot=0
    for i in range(len(per)):
        if not per[i]: continue
        lo=R[i]-win; hi=R[i]+win
        bg=None
        t=lo
        while t<=hi:
            bad=0
            for s,v in per[i]:
                if lvl(t+o[s],bits,W0,W1)!=v: bad+=1
            if bg is None or bad<bg[0]: bg=(bad,t)
            t+=Qr
        R[i]=bg[1]; tot+=bg[0]
    return tot

o=[s*312.5 for s in range(8)]
Rs=[[i*2500.0 for i in range(len(per))] for _,per,_ in DS]
Qr=6.25
for it in range(10):
    tot=0
    for di,(pat,per,bits) in enumerate(DS):
        tot+=estep(per,bits,o,Rs[di],Qr,W0,W1, win=800.0 if it==0 else 200.0)
    # M step: pooled slot offsets
    newo=[]
    for s in range(8):
        bg=None
        for d in range(-56,57):
            cand=s*312.5+d*6.25
            bad=0
            for di,(pat,per,bits) in enumerate(DS):
                R=Rs[di]
                for i in range(len(per)):
                    for ss,v in per[i]:
                        if ss!=s: continue
                        if lvl(R[i]+cand,bits,W0,W1)!=v: bad+=1
            if bg is None or bad<bg[0]: bg=(bad,cand)
        newo.append(bg[1])
    o=newo
    ntot=sum(len(x) for _,per,_ in DS for x in per)
    print(f"iter {it}: mism={tot}/{ntot} offs={[round(x,1) for x in o]} cyc={[round(x/62.5,2) for x in o]}")
print('gaps ns', [round(o[i+1]-o[i],1) for i in range(7)])
print('gaps cyc', [round((o[i+1]-o[i])/62.5,2) for i in range(7)])
# final per-capture mismatch
for di,(pat,per,bits) in enumerate(DS[:36]):
    R=Rs[di]
    bad=0; n=0
    for i in range(len(per)):
        for s,v in per[i]:
            n+=1
            if lvl(R[i]+o[s],bits,W0,W1)!=v: bad+=1
    dl=[R[i+1]-R[i] for i in range(len(R)-1)]
    import statistics
    print(f"  {pat:11s} mism={bad:3d}/{n} Lmean={statistics.mean(dl):.1f} Lsd={statistics.pstdev(dl):.1f}")
