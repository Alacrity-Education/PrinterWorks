"""Accept rate vs arm phase t0, pooled over the demo-reel payloads.

Measures the PHASE LOTTERY: single-shot accept rate as a function of the
capture arm's trigger phase t0, at the bench operating point, using the
calibrated sampler (recon/synth.py via dev_prod/v23lib.py) and the host
build of the shipped decoder.

Result (2026-09-08, 16 payloads x 35 phases, eps -1.00 %):
    102-250 ns   79.5 %      <- the post-arm-fix distribution's low tail
    250-450 ns   89.4 %      <- sweet spot
    450-650 ns   85.0 %
    650-740 ns   32.8 %  ->  0 % at >= 700 ns (the t0 = 681 ns geometric
                             cliff, ARM_INVESTIGATION.md SS3: 100 %
                             refuse_infeasible above it)

Per-payload phase maps show the failures are a payload x phase
INTERACTION, not a payload property: `breathe` survives every phase,
`sunset` about a third, and bit-structure metrics correlate only weakly
with the rate (best |r| = 0.45). Two failure classes: refuse_chase
(1-4 weak candidates, no flip passes CRC-16) and refuse_nocand
(n_weak = 0 -- the decoder flags nothing, i.e. wrong bits decided at
full confidence; the geometry-aware-confidence lever targets these).

Host model, not silicon: it reproduces the bench ranking (sunset/matrix
worst, breathe/twinsweep perfect) but any gain from re-centring the arm
must be confirmed on hardware.
"""
import sys, collections
from pathlib import Path
D = Path('/home/alex.lucaci/Projects/RBARF/src/recon/approaches/dev_prod')
sys.path.insert(0, str(D))
from v23lib import load_ref, capture, linearize

NI = Path('/home/alex.lucaci/Projects/RBARF/src')
src=open(NI/'bench/demo.py').read().split('class Lines:')[0]
ns={'__name__':'x','__file__':str(NI/'bench/demo.py')}; exec(compile(src,'d','exec'),ns)
REEL=ns['REEL']
ev=load_ref(); ev._configure(48, check=True, chk=6)
EPS=-0.0100
T0S=[60 + i*20 for i in range(35)]        # 60 .. 740 ns in 20 ns steps

acc=collections.Counter(); tot=collections.Counter(); cause=collections.defaultdict(collections.Counter)
for name,desc,data in REEL:
    for t0 in T0S:
        out,info = ev.decode_ex(linearize(capture(data, EPS, t0)))
        tot[t0]+=1
        if out==data: acc[t0]+=1
        elif out is None: cause[t0][info['cause']]+=1
        else: cause[t0]['WRONG']+=1

print("accept rate vs arm phase t0 (16 scenes each)\n")
print(f"{'t0 ns':>6s} {'acc':>7s}  bar")
for t0 in T0S:
    a=100*acc[t0]/tot[t0]
    top = ", ".join(f"{k.replace('refuse_','')}x{v}" for k,v in cause[t0].most_common(2))
    print(f"{t0:6d} {a:6.0f}%  {'#'*int(a/3):34s} {top}")

# where does the production arm actually land? (measured distribution,
# ARM_INVESTIGATION: 102..650 ns, p50 340, post-fix)
band = [(102,250),(250,450),(450,650),(650,740)]
print("\npooled by band:")
for lo,hi in band:
    ks=[t for t in T0S if lo<=t<hi]
    if not ks: continue
    a=sum(acc[t] for t in ks); n=sum(tot[t] for t in ks)
    print(f"  {lo:3d}-{hi:3d} ns : {100*a/n:5.1f}%   (n={n})")
