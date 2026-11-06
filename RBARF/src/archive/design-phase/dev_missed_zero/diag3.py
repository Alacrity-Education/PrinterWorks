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
    d=mz.decode(s,meta)
    tb=fb(c)
    exp=bytes.fromhex(c['payload'])
    db=[(x>>(7-j))&1 for x in d for j in range(8)] if d else [0]*128
    errs=[32+i for i in range(128) if db[i]!=tb[32+i]]
    print(f"{c['pattern']:11s}{c['rep']} err={len(errs):3d} {errs[:16]}")
    tot+=128; ne+=len(errs)
print('payload bit err', round(ne/tot,4), ne, tot)
