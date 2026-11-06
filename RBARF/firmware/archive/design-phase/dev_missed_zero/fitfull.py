import sys, importlib.util, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
BIT=1250.0; T0H=350.0; T1H=700.0; NB=192; FE=191*BIT+T1H
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
def pen(ph,v,W):
    p=1 if ph<W else 0
    if p==v: return 0.0
    return ph if ph<W else min(ph-W,BIT-ph)
def obj(P,o,samples,bits,cap=400.0):
    tot=0.0
    for it,sl,v in samples:
        tt=it*P+o[sl]
        b=int(tt//BIT)
        if b<0 or b>=NB:
            if v: tot+=60.0
            continue
        W=T1H if bits[b] else T0H
        tot+=min(cap,pen(tt-b*BIT,v,W))
    return tot
doc=[1,5,9,13,17,21,27,32]
res={}
for c in caps:
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+32]
    bits=fb(c)
    il,sll=work[lastn][0],work[lastn][1]
    best=None
    # multi-start
    for shi in range(0,640,20):
        for Pi in range(24800,25401,3):
            P=Pi/10.0
            o=[shi+g*P/40.0 for g in doc]
            t1=il*P+o[sll]
            if not (FE-420.0 <= t1 <= FE+30.0): continue
            v=obj(P,o,work,bits)
            if best is None or v<best[0]: best=(v,P,o)
    cur,P,o=best[0],best[1],list(best[2])
    for st in (64.,32.,16.,8.,4.,2.,1.,0.5,0.25):
        for _ in range(20):
            imp=False
            for k in range(8):
                base=o[k]
                for d in (-st,st):
                    o[k]=base+d
                    v=obj(P,o,work,bits)
                    if v<cur-1e-9: cur=v; base=o[k]; imp=True
                    else: o[k]=base
            base=P
            for d in (-st/96.,st/96.,-st/24.,st/24.):
                P=base+d
                v=obj(P,o,work,bits)
                if v<cur-1e-9: cur=v; base=P; imp=True
                else: P=base
            if not imp: break
    tau=P/40.0
    cyc=[round(x/tau,2) for x in o]
    print(f"{c['pattern']:11s}{c['rep']} J{cur:8.1f} P={P:8.2f} cyc={cyc} gaps={[round(cyc[i+1]-cyc[i],2) for i in range(7)]}")
    res[c['pattern']+str(c['rep'])]=(cur,P,o)
json.dump(res,open('approaches/dev_missed_zero/fitfull.json','w'))
