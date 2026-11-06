import sys, importlib.util, json
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
MP='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py'
spec=importlib.util.spec_from_file_location('mz',MP)
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
REPS=(0,1)
DS=[]
for c in caps:
    if c['rep'] not in REPS: continue
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+24]
    by_it={}
    for it,sl,v in work: by_it.setdefault(it,[]).append((sl,v))
    its=sorted(by_it)
    DS.append((c,by_it,its,mz.FRAME_END/(work[lastn][0]+0.55),fb(c)))
def score(frac,oracle=True,known0=None):
    mz.FRAC=list(frac)
    ne=0; J=0.0
    for c,by_it,its,P0,tb in DS:
        kn = tb if oracle else mz._known_bits(meta)
        r=mz._viterbi(by_it,its,kn,P0)
        if r is None: ne+=128; continue
        T,dP=r
        cells=mz._cells_of(by_it,its,T,dP)
        bits=mz._decide(cells)
        ne+=sum(1 for b in range(32,160) if bits[b]!=tb[b])
    return ne
frac=list(mz.FRAC)
best=score(frac)
print('init',frac,'err',best,flush=True)
for st in (0.02,0.01,0.005,0.0025):
    improved=True
    while improved:
        improved=False
        for k in range(1,8):
            base=frac[k]
            for d in (-st,st):
                cand=list(frac); cand[k]=base+d
                if k>0 and cand[k]<=cand[k-1]: continue
                if k<7 and cand[k]>=cand[k+1]: continue
                if cand[7]>=1.0: continue
                v=score(cand)
                if v<best:
                    best=v; frac=cand; improved=True
                    print('  ->',[round(x,4) for x in frac],'err',best,flush=True)
print('FINAL',[round(x,4) for x in frac],'oracle err',best)
json.dump(frac,open('approaches/dev_missed_zero/frac.json','w'))
