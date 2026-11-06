import sys, numpy as np
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
import tfit
res=[]
tots=[]
for c in tfit.allc:
    if c['rep'] not in (0,1): continue
    o,T,tot = tfit.run(c['pattern'], c['rep'], verbose=False)
    d=np.diff(T)[:95]
    res.append(o); tots.append(tot)
    print(f"{c['pattern']:11s} r{c['rep']} match={tot}/800 dTmean={d.mean():.1f} dTstd={d.std():.1f} o="+' '.join('%6.1f'%x for x in o), flush=True)
A=np.array(res)
print("median o:", np.round(np.median(A,axis=0),1).tolist())
print("mean   o:", np.round(A.mean(axis=0),1).tolist())
print("std    o:", np.round(A.std(axis=0),1).tolist())
print("mean match", np.mean(tots))
