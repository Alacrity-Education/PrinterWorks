import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('mz','/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py')
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
pat,rep=sys.argv[1],int(sys.argv[2])
bl=[int(x) for x in sys.argv[3].split(',')]
c=[x for x in caps if x['pattern']==pat and x['rep']==rep][0]
s=linearize(c['capture'])
lastn=max(n for n in range(len(s)) if s[n][2])
work=s[:lastn+24]; tb=fb(c)
by_it={}
for it,sl,v in work: by_it.setdefault(it,[]).append((sl,v))
its=sorted(by_it)
P0=mz.FRAME_END/(work[lastn][0]+0.55)
T,dP=mz._viterbi(by_it,its,tb,P0)
print('P0',round(P0,2))
print('loop lens:', [round(dP[i]) for i in its[:40]])
print('loop lens:', [round(dP[i]) for i in its[40:]])
cells=mz._cells_of(by_it,its,T,dP)
for b in bl:
    cl=cells[b]
    p0=sum(mz._pen(ph,v,mz.T0H) for ph,v in cl)
    p1=sum(mz._pen(ph,v,mz.T1H) for ph,v in cl)
    print(f"bit {b} true={tb[b]} p0={p0:7.1f} p1={p1:7.1f} samples={[(round(ph),v) for ph,v in cl]}")
