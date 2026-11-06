import sys, importlib.util, itertools, os
from multiprocessing import Pool
R='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,R)
from harness import load_dataset, linearize

spec=importlib.util.spec_from_file_location('ha', R+'/approaches/histogram_adaptive.py')
ha=importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
meta,caps=load_dataset()
SPLIT=os.environ.get('SPLIT','train')
sub=[c for c in caps if (c['rep'] in (0,1) if SPLIT=='train' else c['rep']==2)]

def fb(fh): return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]
DATA=[(c['pattern'],c['rep'],linearize(c['capture']),bytes.fromhex(c['payload']),fb(c['frame'])) for c in sub]

def job(args):
    prm,idx=args
    pat,rep,s,exp,tb=DATA[idx]
    bv,info=ha._run(s,meta,prm)
    if bv is None: return (pat,rep,False,0.0,128)
    got=ha._assemble(bv)
    nbe=sum(1 for k in range(192) if bv.get(k,0)!=tb[k])
    acc=sum(1 for a,b in zip(got,exp) if a==b)/16.0
    return (pat,rep,got==exp,acc,nbe)

def run(prm,pool,verbose=False):
    res=pool.map(job,[(prm,i) for i in range(len(DATA))])
    ex=sum(1 for r in res if r[2]); acc=sum(r[3] for r in res)/len(res)
    nbe=sum(r[4] for r in res)
    if verbose:
        for r in sorted(res,key=lambda x:-x[4]): print(f"   {r[0]:11s} r{r[1]} exact={r[2]} biterr={r[4]}")
    return ex,acc,nbe

if __name__=='__main__':
    pool=Pool(int(os.environ.get('NPROC','8')))
    base=dict(ha.PARAMS)
    grid=[]
    for jp1 in (0.8,1.2,1.8,2.5):
        for jpr in (0.3,0.5,0.8):
            p=dict(base); p['JP1']=jp1; p['JPR']=jpr; grid.append(p)
    best=None
    for p in grid:
        ex,acc,nbe=run(p,pool)
        print(f"JP1={p['JP1']} JPR={p['JPR']} -> exact {ex}/{len(DATA)} acc={acc:.3f} biterr={nbe}", flush=True)
        if best is None or (ex,-nbe)>(best[0],-best[2]): best=(ex,acc,nbe,p)
    print('BEST',best[0],best[2],{k:best[3][k] for k in ('JP1','JPR')})
