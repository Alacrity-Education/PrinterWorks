import sys
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize
meta,caps=load_dataset()

def frame_bits(fh):
    return [int(x) for byte in bytes.fromhex(fh) for x in f"{byte:08b}"]

pats = sys.argv[1:] or ['ones','zeros','aa']
for c in caps:
    if c['rep']!=0 or c['pattern'] not in pats: continue
    s=linearize(c['capture'])
    lv=[v for _,_,v in s]
    bits=frame_bits(c['frame'])
    # RLE
    runs=[]
    cur=lv[0]; n=1
    for v in lv[1:]:
        if v==cur: n+=1
        else: runs.append((cur,n)); cur=v; n=1
    runs.append((cur,n))
    # trim trailing zeros run
    while runs and runs[-1][0]==0: runs.pop()
    print(c['pattern'], ''.join(str(b) for b in bits))
    print(' runs:', ' '.join(f"{'H' if v else 'L'}{n}" for v,n in runs))
    print(' nruns', len(runs), 'sum', sum(n for _,n in runs))
    print()
