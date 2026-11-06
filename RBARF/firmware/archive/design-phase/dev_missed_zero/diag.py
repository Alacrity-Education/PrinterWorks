import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('mz','/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py')
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
tot=0;nerr=0
REP=[int(x) for x in (sys.argv[1] if len(sys.argv)>1 else '0').split(',')]
for c in caps:
    if c['rep'] not in REP: continue
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+32]
    known=mz._known_bits(meta)
    model,cost=mz._calibrate(work,known,lastn)
    bits=mz._bits_from(model,work)
    tb=fb(c)
    errs=[b for b in range(192) if bits[b]!=tb[b]]
    e0=sum(1 for b in errs if tb[b]==0); e1=len(errs)-e0
    # true-model cost
    tcost=mz._objective(model,work,tb)
    print(f"{c['pattern']:11s}{c['rep']} J{cost:7.0f} Jtrue{tcost:7.0f} P={model.P:8.2f} o={[round(x) for x in model.o]} ph={[round(x%1250) for x in model.o]} err={len(errs):3d}(0>1:{e0} 1>0:{e1}) {errs[:14]}")
    tot+=192; nerr+=len(errs)
print('bit err rate', round(nerr/tot,4))
