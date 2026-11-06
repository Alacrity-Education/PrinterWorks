"""Direct, model-free loop-period measurement using frame start/end."""
from common import *
import numpy as np
meta,caps=load()
print(f"{'pattern':11s} {'rep':>3s} {'i_end':>6s} {'slot':>4s} {'loop_ns':>8s} {'nHi':>4s}")
vals=[]
for c in caps:
    s=linearize(c['capture']); bits=bits_of(bytes.fromhex(c['frame']))
    lv=[v for _,_,v in s]
    last_hi=max(i for i,v in enumerate(lv) if v==1)
    it,sl,_=s[last_hi]
    # last high sample belongs to bit191 whose high ends at 191*1250+750=239500
    # first low sample after it:
    it2,sl2,_=s[last_hi+1]
    # nominal position of last high sample
    pos=it*LOOP_NOM+SLOT_OFF[sl]
    pos2=it2*LOOP_NOM+SLOT_OFF[sl2]
    # true time in (238750, 239500);  and pos2 -> (239500, ...)
    # use the midpoint of the interval for the last-high sample
    lo=191*BIT; hi=191*BIT+750.0
    vals.append((c['pattern'],c['rep'],it,sl,pos,pos2,lo,hi))
    print(f"{c['pattern']:11s} {c['rep']:3d} {it:6d} {sl:4d} {((lo+hi)/2)/pos*LOOP_NOM:8.2f} {sum(1 for a,b in zip(lv,lv[1:]) if b and not a)+lv[0]:4d}")
import statistics
est=[ (( (191*BIT+375.0) )/v[4]*LOOP_NOM) for v in vals]
print("median loop_ns est", statistics.median(est), "min",min(est),"max",max(est))
