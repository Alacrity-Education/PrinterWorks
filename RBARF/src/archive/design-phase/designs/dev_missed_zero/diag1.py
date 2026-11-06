from common import *
import numpy as np
meta,caps=load()
c=[x for x in caps if x['pattern']=='ones' and x['rep']==0][0]
s=linearize(c['capture']); bits=np.array(bits_of(bytes.fromhex(c['frame'])),np.int8)
it=np.array([i for i,_,_ in s],float); sl=np.array([x for _,x,_ in s]); lv=np.array([v for _,_,v in s],bool)
OFF=np.array(SLOT_OFF)
H0,H1=375.0,750.0
def sc_ag(scale,t0):
    t=t0+scale*(it*LOOP_NOM+OFF[sl])
    k=np.floor(t/BIT).astype(np.int64); ok=(k>=0)&(k<len(bits)); kc=np.clip(k,0,len(bits)-1)
    hi=np.where(bits[kc]==1,H1,H0)
    return int(np.count_nonzero((((t-k*BIT)<hi)&ok)==lv))
best=[]
for scale in np.linspace(0.995,1.010,1501):
    for t0 in np.arange(-100,400,5.0):
        best.append((sc_ag(scale,t0),scale,t0))
best.sort(reverse=True)
print("top optima:")
seen=[]
for a,s_,t_ in best:
    if any(abs(s_-x)<3e-4 for x in seen): continue
    seen.append(s_); print(f"  agree={a}/{len(lv)} loop={s_*2500:.2f} t0={t_:.0f}")
    if len(seen)>=6: break
