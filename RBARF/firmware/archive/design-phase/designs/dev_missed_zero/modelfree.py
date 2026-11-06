"""Model-free run statistics: high-run count vs 192 bits."""
from common import *
from collections import Counter
meta, caps = load()
print(f"{'pattern':11s} {'rep':>3s} {'nHi':>4s} {'n1':>4s} {'n0':>4s} {'deficit':>7s}  hi-run-len hist(samples)")
tot=Counter(); hilen=Counter(); lolen=Counter()
for c in caps:
    s = linearize(c['capture'])
    bits = bits_of(bytes.fromhex(c['frame']))
    # runs
    rl=[]; cur=None
    for i,sl,v in s:
        if cur is None or cur[0]!=v: 
            if cur is not None: rl.append(tuple(cur))
            cur=[v,1]
        else: cur[1]+=1
    rl.append(tuple(cur))
    hi=[n for v,n in rl if v==1]; lo=[n for v,n in rl if v==0]
    n1=sum(bits); n0=len(bits)-n1
    print(f"{c['pattern']:11s} {c['rep']:3d} {len(hi):4d} {n1:4d} {n0:4d} {192-len(hi):7d}  "
          f"{dict(sorted(Counter(hi).items()))}")
    tot['nhi']+=len(hi); tot['deficit']+=192-len(hi)
    hilen.update(hi); lolen.update(lo)
print()
print("total high runs", tot['nhi'], "expected 54*192 =", 54*192, "deficit", tot['deficit'])
print("high-run length hist (samples):", dict(sorted(hilen.items())))
print("low-run  length hist (samples):", dict(sorted(lolen.items())))
