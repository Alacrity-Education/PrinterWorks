import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
MP='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py'
spec=importlib.util.spec_from_file_location('mz',MP)
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
import json
fr=json.loads(sys.argv[1])
mz.FRAC=fr
ne=0;ex=0;n=0
for c in caps:
    if c['rep'] not in (0,1): continue
    s=linearize(c['capture'])
    d=mz.decode(s,meta)
    exp=bytes.fromhex(c['payload'])
    tbb=[(x>>(7-j))&1 for x in exp for j in range(8)]
    db=[(x>>(7-j))&1 for x in d for j in range(8)] if d else [1-x for x in tbb]
    e=sum(1 for i in range(128) if db[i]!=tbb[i])
    ne+=e; ex+= (e==0); n+=1
    if e: print(f"  {c['pattern']:11s}{c['rep']} err {e}")
print('FRAC',fr,'-> exact',ex,'/',n,'biterr',ne)
