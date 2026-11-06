import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()
def fb(c):
    fr=bytes.fromhex(c['frame']); return [(b>>(7-j))&1 for b in fr for j in range(8)]
for pat in (sys.argv[1].split(',')):
    c=[x for x in caps if x['pattern']==pat and x['rep']==0][0]
    s=linearize(c['capture']); bits=fb(c)
    print('==',pat,c['payload'])
    for it in range(0,98):
        row=[v for i,sl,v in s if i==it]
        pair=''.join(map(str,bits[2*it:2*it+2])) if 2*it+1<len(bits) else '..'
        print(f"  it{it:3d} b{2*it:3d} {pair}  {''.join(map(str,row))}")
