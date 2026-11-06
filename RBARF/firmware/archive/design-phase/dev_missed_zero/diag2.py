import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('mz','/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py')
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
REP=[int(x) for x in (sys.argv[1] if len(sys.argv)>1 else '0').split(',')]
ORACLE = len(sys.argv)>2
tot=0;ne=0
for c in caps:
    if c['rep'] not in REP: continue
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+32]
    tb=fb(c)
    known=tb if ORACLE else mz._known_bits(meta)
    P,o=mz._coarse(work,known,lastn)
    cur,P,o=mz._refine(work,known,P,o)
    corr=None
    for _ in range(2):
        corr=mz._viterbi(work,known,P,o)
        cur,P,o=mz._refine(work,known,P,o,corr,steps=(12.,6.,3.,1.5))
    bits=mz._decide(work,known,P,o,corr)
    errs=[b for b in range(32,160) if bits[b]!=tb[b]]
    cvals=[corr[i] for i in sorted(corr)]
    print(f"{c['pattern']:11s}{c['rep']} J{cur:8.0f} P={P:8.2f} perr={len(errs):3d} corr[{min(cvals):5.0f},{max(cvals):5.0f}] {errs[:12]}")
    tot+=128; ne+=len(errs)
print('payload bit err', round(ne/tot,4))
