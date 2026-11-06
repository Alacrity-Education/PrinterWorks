import sys, importlib.util
R='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,R)
from harness import load_dataset, linearize
spec=importlib.util.spec_from_file_location('ha', R+'/approaches/histogram_adaptive.py')
ha=importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
meta,caps=load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

prm=dict(ha.PARAMS)
for c in caps:
    if c['rep']!=0: continue
    s=linearize(c['capture'])
    levels=[v for _,_,v in s]
    tb=frame_bits(c['frame'])
    full={k:tb[k] for k in range(192)}
    kn=ha._known_bits(meta)
    Pc,last=ha._period_center(levels, prm['t0'])
    nmax=min(len(levels),last+12)
    NP=prm['NP']; span=prm['PSPAN']
    bestF=None; bestK=None
    for i in range(NP):
        P=Pc+(i-(NP-1)/2.0)*(2.0*span/max(1,NP-1))
        bv,cc=ha._viterbi(levels,nmax,P,prm,full)
        if bv is not None and (bestF is None or cc<bestF[0]): bestF=(cc,P,bv)
        bv2,cc2=ha._viterbi(levels,nmax,P,prm,kn)
        if bv2 is not None and (bestK is None or cc2<bestK[0]): bestK=(cc2,P,bv2)
    nbe=sum(1 for k in range(192) if bestK[2].get(k,0)!=tb[k])
    print(f"{c['pattern']:11s} Pc={Pc:.3f} trueP={bestF[1]:.3f} trueCost={bestF[0]:7.2f} | decP={bestK[1]:.3f} decCost={bestK[0]:7.2f} biterr={nbe}")
