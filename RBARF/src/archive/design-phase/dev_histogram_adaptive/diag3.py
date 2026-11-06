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
NL=int(sys.argv[1]) if len(sys.argv)>1 else 21
LSTEP=float(sys.argv[2]) if len(sys.argv)>2 else 1.5
tot_ex=0
for c in caps:
    if c['rep'] not in (0,1): continue
    s=linearize(c['capture'])
    per,nit_all,last=ha._prepare(s)
    tb=frame_bits(c['frame'])
    full=list(tb)
    kn=ha._known_bits(meta)
    nit=min(nit_all,last//8+2)
    li=last//8; ls=last%8
    end=191*1250.0+prm['W1']
    Lc=end/(li+ha.SLOT_FRAC[ls])
    bF=None;bK=None
    for a in range(NL):
        Lm=Lc+(a-(NL-1)//2)*LSTEP
        offs=[f*Lm for f in ha.SLOT_FRAC]
        bv,cc,_=ha._viterbi(per,nit,Lm,prm,full,offs,prm['W0'],prm['W1'])
        if bv is not None and (bF is None or cc<bF[0]): bF=(cc,Lm,bv)
        bv2,cc2,_=ha._viterbi(per,nit,Lm,prm,kn,offs,prm['W0'],prm['W1'])
        if bv2 is not None and (bK is None or cc2<bK[0]): bK=(cc2,Lm,bv2)
    nbe=sum(1 for k in range(192) if bK[2].get(k,0)!=tb[k])
    ok = nbe==0
    tot_ex+=int(ok)
    print(f"{c['pattern']:11s} r{c['rep']} Lc={Lc:.1f} trueL={bF[1]:.1f} trueC={bF[0]:6.2f} | decL={bK[1]:.1f} decC={bK[0]:6.2f} biterr={nbe}")
print('exact', tot_ex, '/36')
