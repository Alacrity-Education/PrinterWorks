import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('mz','/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py')
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
REP=[int(x) for x in (sys.argv[1] if len(sys.argv)>1 else '0,1').split(',')]
tot=0;ne=0
for c in caps:
    if c['rep'] not in REP: continue
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+24]
    tb=fb(c)
    by_it={}
    for it,sl,v in work: by_it.setdefault(it,[]).append((sl,v))
    its=sorted(by_it)
    it_last=work[lastn][0]
    P0=mz.FRAME_END/(it_last+0.55)
    T,dP=mz._viterbi(by_it,its,tb,P0)   # ORACLE
    cells=mz._cells_of(by_it,its,T,dP)
    bits=mz._decide(cells)
    errs=[b for b in range(32,160) if bits[b]!=tb[b]]
    print(f"{c['pattern']:11s}{c['rep']} err={len(errs):3d} {errs[:16]}")
    tot+=128; ne+=len(errs)
print('ORACLE payload bit err', round(ne/tot,4), ne, tot)
