import sys, json, itertools
sys.path.insert(0,'/home/alex.lucaci/Projects/RBARF/new-implementation/recon')
from harness import load_dataset, linearize

meta, caps = load_dataset()

def frame_bits(frame_hex):
    b = bytes.fromhex(frame_hex)
    return [int(x) for byte in b for x in f"{byte:08b}"]

def ideal_level(t, bits, bit_ns=1250.0):
    if t < 0: return 0
    k = int(t // bit_ns)
    if k >= len(bits): return 0
    off = t - k*bit_ns
    T = 700.0 if bits[k] else 350.0
    return 1 if off < T else 0

def offsets(gaps, tc):
    o=[0.0]
    for g in gaps[:7]:
        o.append(o[-1]+g*tc)
    L = sum(gaps)*tc
    return o, L

def score(samples, bits, gaps, tc, t0, nmax=None):
    o,L = offsets(gaps,tc)
    good=0; tot=0
    for it,sl,v in samples:
        t = it*L + o[sl] + t0
        if t > len(bits)*1250.0 + 2000: break
        tot+=1
        if ideal_level(t,bits)==v: good+=1
    return good, tot

# grid search gaps last value and tc
for c in caps:
    if c['rep']!=0: continue
    if c['pattern'] not in ('ones','zeros','aa','rnd1'): continue
    samples = linearize(c['capture'])
    bits = frame_bits(c['frame'])
    best=None
    for g7 in range(5,13):
      for g6 in range(4,8):
        for g5 in range(4,10):
          gaps=[4,4,4,4,4,g5,g6,g7]
          S=sum(gaps)
          for L in [2500+i*0.5 for i in range(0,60)]:
            tc = L/S
            for t0 in [i*15.0 for i in range(0,22)]:
                g,tot = score(samples,bits,gaps,tc,t0)
                if best is None or g>best[0]:
                    best=(g,tot,gaps[:],round(tc,3),round(L,2),t0)
    print(c['pattern'], best)
