import sys, importlib.util, json, itertools
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
    DS.append((c,by_it,sorted(by_it),mz.FRAME_END/(work[lastn][0]+0.55),fb(c)))
KN=mz._known_bits(meta)
def run(frac):
    mz.FRAC=list(frac)
    ne=0; exact=0
    for c,by_it,its,P0,tb in DS:
        r=mz._viterbi(by_it,its,KN,P0)
        if r is None: ne+=128; continue
        T,dP=r
        bits=mz._decide(mz._cells_of(by_it,its,T,dP))
        for _ in range(2):
            soft=list(bits)
            for b in range(32): soft[b]=KN[b]
            for b in range(160,192): soft[b]=KN[b]
            r=mz._viterbi(by_it,its,soft,P0)
            if r is None: break
            T,dP=r
            nb=mz._decide(mz._cells_of(by_it,its,T,dP))
            if nb==bits: break
            bits=nb
        e=sum(1 for b in range(32,160) if bits[b]!=tb[b])
        ne+=e; exact+= (e==0)
    return ne,exact
frac=list(mz.FRAC)
best=run(frac)
print('init',[round(x,4) for x in frac],best,flush=True)
for st in (0.03,0.015,0.008,0.004,0.002):
    improved=True
    it=0
    while improved and it<6:
        it+=1; improved=False
        for k in range(1,8):
            base=frac[k]
            for d in (-st,st):
                cand=list(frac); cand[k]=base+d
                if cand[k]<=cand[k-1]+0.01: continue
                if k<7 and cand[k]>=cand[k+1]-0.01: continue
                if cand[7]>=0.98: continue
                v=run(cand)
                if v[0]<best[0] or (v[0]==best[0] and v[1]>best[1]):
                    best=v; frac=cand; improved=True
                    print('  ->',[round(x,4) for x in frac],best,flush=True)
print('FINAL',[round(x,4) for x in frac],best)
json.dump(frac,open('/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_missed_zero/frac_real.json','w'))
