from common import *
import numpy as np
meta,caps=load()
c=[x for x in caps if x['pattern']=='ones' and x['rep']==0][0]
s=linearize(c['capture']); bits=bits_of(bytes.fromhex(c['frame']))
bn=np.array(bits,np.int8)
it=np.array([i for i,_,_ in s],float); sl=np.array([x for _,x,_ in s]); lv=np.array([v for _,_,v in s],bool)
OFF=np.array(SLOT_OFF); H0,H1=375.0,750.0
scale,t0=2497.53/2500.0,275.0
t=t0+scale*(it*LOOP_NOM+OFF[sl])
nb=len(bits)
S=0;M=0
print(" k b  #hi #lo   window                samples(t,lvl)")
for k in range(nb):
    hi=H1 if bits[k] else H0
    a=np.where((t>=k*BIT)&(t<k*BIT+hi))[0]
    b=np.where((t>=k*BIT+hi)&(t<(k+1)*BIT))[0]
    nh=int(np.count_nonzero(lv[a])); nl=len(b)
    if nh==0: S+=1
    if k+1<nb and nl==0: M+=1
    if k<30:
        print(f"{k:3d} {bits[k]} {nh:4d} {nl:4d}  [{k*BIT:8.0f},{k*BIT+hi:8.0f})  ",
              " ".join(f"{t[j]:.0f}/{int(lv[j])}" for j in list(a)+list(b)))
print("S=",S,"M=",M,"S+M=",S+M,"runs should be",192-S-M)
nr=sum(1 for x,y in zip(lv,lv[1:]) if y and not x)+int(lv[0])
print("actual high runs",nr)
