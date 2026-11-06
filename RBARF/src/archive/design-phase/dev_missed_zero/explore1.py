import sys, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    # find last high sample
    last=None; first=None
    n_high=0
    for it,sl,v in s:
        if v:
            n_high+=1
            if first is None: first=(it,sl)
            last=(it,sl)
    # count runs
    runs=[]
    prev=s[0][2]; cnt=1
    for it,sl,v in s[1:]:
        if v==prev: cnt+=1
        else: runs.append((prev,cnt)); prev=v; cnt=1
    runs.append((prev,cnt))
    nph=sum(1 for l,_ in runs if l==1)
    print(f"{c['pattern']:11s} first={first} last={last} nhigh={n_high} npulses={nph}")
