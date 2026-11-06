import sys, importlib.util
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
MP='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/missed_zero.py'
spec=importlib.util.spec_from_file_location('mz',MP)
mz=importlib.util.module_from_spec(spec); spec.loader.exec_module(mz)
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
KN=mz._known_bits(meta)
for pat in sys.argv[1].split(','):
  for rep in (0,1):
    c=[x for x in caps if x['pattern']==pat and x['rep']==rep][0]
    s=linearize(c['capture'])
    lastn=max(n for n in range(len(s)) if s[n][2])
    work=s[:lastn+24]; tb=fb(c)
    by_it={}
    for it,sl,v in work: by_it.setdefault(it,[]).append((sl,v))
    its=sorted(by_it); P0=mz.FRAME_END/(work[lastn][0]+0.55)
    m0,m1=mz._marginals(by_it,its,KN,P0)
    T,dP=mz._viterbi(by_it,its,KN,P0)
    cells=mz._cells_of(by_it,its,T,dP)
    errs=[]
    for b in range(32,160):
        d=0 if m0[b]<=m1[b] else 1
        if d!=tb[b]: errs.append((b,round(m0[b]-m1[b],1),[(round(ph),v) for ph,v in cells[b]]))
    print(f"{pat}{rep} nerr={len(errs)}")
    for e in errs[:8]: print('   ',e)
