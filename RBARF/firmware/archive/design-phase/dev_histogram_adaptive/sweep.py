import sys, importlib.util, itertools, json, time
R='/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0,R)
from harness import load_dataset, linearize

spec=importlib.util.spec_from_file_location('ha', R+'/approaches/histogram_adaptive.py')
ha=importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)

meta,caps=load_dataset()
SPLIT=sys.argv[1] if len(sys.argv)>1 else 'train'
sub=[c for c in caps if (c['rep'] in (0,1) if SPLIT=='train' else c['rep']==2)]

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

def evaluate(prm, verbose=False):
    ex=0; bacc=0.0; det=[]
    for c in sub:
        s=linearize(c['capture'])
        levels=[v for _,_,v in s]
        bv,info=ha._run(levels, meta, prm)
        exp=bytes.fromhex(c['payload'])
        if bv is None:
            det.append((c['pattern'],c['rep'],None,128)); continue
        got=ha._assemble(bv)
        tb=frame_bits(c['frame'])
        nbe=sum(1 for k in range(192) if bv.get(k,0)!=tb[k])
        e = got==exp
        ex+=int(e)
        bacc+=sum(1 for a,b in zip(got,exp) if a==b)/16.0
        det.append((c['pattern'],c['rep'],e,nbe))
    if verbose:
        for d in sorted(det,key=lambda x:-x[3]):
            print(f"   {d[0]:11s} r{d[1]} exact={d[2]} biterr={d[3]}")
    return ex, bacc/len(sub), det

if __name__=='__main__':
    prm=dict(ha.PARAMS)
    t=time.time()
    ex,ba,det=evaluate(prm, verbose=True)
    print(f"base: {ex}/{len(sub)} byteacc={ba:.3f}  ({time.time()-t:.0f}s)")
