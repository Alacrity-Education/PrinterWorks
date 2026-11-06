import sys, os, json, importlib.util, itertools
from multiprocessing import Pool
ROOT='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,ROOT)
MP=ROOT+'/approaches/missed_zero.py'
from harness import load_dataset, linearize
meta,caps=load_dataset()
REPS=(0,1)
DATA=[]
for c in caps:
    if c['rep'] not in REPS: continue
    DATA.append((c['pattern'],c['rep'],linearize(c['capture']),bytes.fromhex(c['payload'])))
def load():
    spec=importlib.util.spec_from_file_location('mz',MP)
    mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
    return mz
def evaluate(cfg):
    mz=load()
    for k,v in cfg.items(): setattr(mz,k,v)
    ex=0; ne=0; det=[]
    for pat,rep,s,exp in DATA:
        try: d=mz.decode(s,meta)
        except Exception as e: d=None
        tbb=[(x>>(7-j))&1 for x in exp for j in range(8)]
        if d is None: e=128
        else:
            db=[(x>>(7-j))&1 for x in d for j in range(8)]
            e=sum(1 for i in range(128) if db[i]!=tbb[i])
        ne+=e; ex+=(e==0)
        if e: det.append((pat,rep,e))
    return (ex,ne,cfg,det)
if __name__=='__main__':
    cfgs=json.load(open(sys.argv[1]))
    with Pool(min(24,len(cfgs))) as p:
        res=p.map(evaluate,cfgs)
    res.sort(key=lambda r:(-r[0],r[1]))
    for ex,ne,cfg,det in res:
        print(f"exact {ex:2d}/36 biterr {ne:4d}  {cfg}")
    print('BEST detail:',res[0][3])
