"""Per-bit visibility using the globally fitted slot model."""
from common import *
import numpy as np, json
from collections import Counter, defaultdict
G=json.load(open('globalfit.json'))
OFF=np.array(G['off']); H0=G['h0']; H1=G['h1']
CAPP={(c['pattern'],c['rep']):c for c in G['caps']}
meta,caps=load()
rows=[];swal_slot=Counter();merge_slot=Counter()
swal_phase=[];vis_phase=[]
merge_kinds=Counter()
runlen_by_class=defaultdict(Counter)
for c in caps:
    s=linearize(c['capture']); bits=bits_of(bytes.fromhex(c['frame']))
    pp=CAPP[(c['pattern'],c['rep'])]; sc,t0=pp['scale'],pp['t0']
    it=np.array([i for i,_,_ in s],float); sl=np.array([x for _,x,_ in s]); lv=np.array([v for _,_,v in s])
    t=t0+sc*(it*LOOP_NOM+OFF[sl])
    nb=len(bits)
    nhi=np.zeros(nb,int); nlo=np.zeros(nb,int)
    for k in range(nb):
        hi=H1 if bits[k] else H0
        a=(t>=k*BIT)&(t<k*BIT+hi); b=(t>=k*BIT+hi)&(t<(k+1)*BIT)
        nhi[k]=int(np.count_nonzero(a&(lv==1))); nlo[k]=int(np.count_nonzero(b))
    z=np.array(bits)==0
    sw0=int(((nhi==0)&z).sum()); sw1=int(((nhi==0)&~z).sum())
    mg=int((nlo[:-1]==0).sum())
    # phase of each bit start within the loop (mod loop)
    for k in range(nb):
        ph=((k*BIT-t0)/sc)%LOOP_NOM
        (swal_phase if nhi[k]==0 else vis_phase).append((ph,bits[k]))
        if nhi[k]==0:
            j=int(np.searchsorted(t,k*BIT)); 
            if 0<j<len(t): swal_slot[(int(sl[j-1]),int(sl[j]),bits[k])]+=1
        if k+1<nb and nlo[k]==0:
            hi=H1 if bits[k] else H0
            j=int(np.searchsorted(t,k*BIT+hi))
            if 0<j<len(t): merge_slot[(int(sl[j-1]),int(sl[j]))]+=1
            merge_kinds[(bits[k],bits[k+1])]+=1
    # run length by true class
    runs=[];cur=None
    for idx in range(len(s)):
        if cur is None or cur[0]!=lv[idx]:
            if cur: runs.append(tuple(cur))
            cur=[lv[idx],idx,idx]
        else: cur[2]=idx
    runs.append(tuple(cur))
    for v,i0,i1 in runs:
        if not v: continue
        # which bits does this run cover?
        ks=set()
        for idx in range(i0,i1+1):
            k=int(t[idx]//BIT)
            if 0<=k<nb: ks.add(k)
        ks=sorted(ks)
        key=tuple(bits[k] for k in ks)
        runlen_by_class[key][i1-i0+1]+=1
    rows.append(dict(pattern=c['pattern'],rep=c['rep'],sw0=sw0,sw1=sw1,mg=mg,
                     n0=int(z.sum()),n1=int((~z).sum())))
print(f"{'pattern':11s} {'rep':>3s} {'sw0':>4s} {'sw1':>4s} {'merge':>5s}")
for r in rows: print(f"{r['pattern']:11s} {r['rep']:3d} {r['sw0']:4d} {r['sw1']:4d} {r['mg']:5d}")
T=lambda k: sum(r[k] for r in rows)
print(f"\nTOTAL n0={T('n0')} n1={T('n1')} swallowed0={T('sw0')} ({100*T('sw0')/T('n0'):.2f}% of zeros) "
      f"swallowed1={T('sw1')} merges={T('mg')}")
print("merge kinds (bit_k,bit_k+1):",dict(merge_kinds))
print("swallow bracketing (prev_slot,next_slot,bit):",dict(sorted(swal_slot.items(),key=lambda x:-x[1])))
print("merge bracketing (prev_slot,next_slot):",dict(sorted(merge_slot.items(),key=lambda x:-x[1])))
print("\nrun-length by covered-bit-class (top):")
for k,v in sorted(runlen_by_class.items(),key=lambda x:-sum(x[1].values()))[:12]:
    print("  ",k,dict(sorted(v.items())),"tot",sum(v.values()))
json.dump(dict(rows=rows,swal_phase=swal_phase),open('measure2.json','w'))
