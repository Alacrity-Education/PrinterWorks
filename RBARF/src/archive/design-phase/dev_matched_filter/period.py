"""Equivalent-time measurement of slot phases using periodic payloads.

For payloads whose bit pattern is constant (zeros / ones) the waveform in
the payload region is exactly 1250 ns periodic, so each slot's phase can be
measured to ~ns by watching where it crosses the pulse edge as the loop
period beats against the bit period.
"""
import sys
import numpy as np
R = '/home/alex.lucaci/Projects/RBARF/new-implementation/recon'
sys.path.insert(0, R)
from harness import load_dataset, linearize

BIT = 1250.0
meta, allc = load_dataset()
byname = {}
for c in allc:
    byname[(c['pattern'], c['rep'])] = c


def measure(pattern, rep, width, i0=17, i1=79):
    c = byname[(pattern, rep)]
    s = linearize(c['capture'])
    grid = {}
    for it, sl, v in s:
        if i0 <= it <= i1:
            grid[(it, sl)] = v
    its = np.arange(i0, i1 + 1, dtype=np.float64)
    best = None
    for P in np.arange(2470, 2530, 0.01):
        tot = 0
        offs = []
        for sl in range(8):
            v = np.array([grid[(int(i), sl)] for i in its], dtype=np.int8)
            o = np.arange(0, 1250, 1.0)
            ph = (its[None, :] * P + o[:, None]) % BIT
            pred = (ph < width).astype(np.int8)
            g = (pred == v[None, :]).sum(axis=1)
            j = int(np.argmax(g))
            tot += int(g[j]); offs.append(float(o[j]))
        if best is None or tot > best[0]:
            best = (tot, P, offs)
    n = len(its) * 8
    tot, P, offs = best
    # unwrap offsets to be increasing
    base = offs[0]
    un = []
    prev = base
    for k, o in enumerate(offs):
        while o < prev - 1e-9:
            o += BIT
        un.append(o); prev = o
    print(f"{pattern} r{rep}: P={P:.2f} match={tot}/{n} ({tot/n:.2%})")
    print("   offs mod1250:", ' '.join('%7.1f' % o for o in offs))
    print("   unwrapped   :", ' '.join('%7.1f' % o for o in un))
    print("   gaps (cyc@62.5):", ' '.join('%5.2f' % ((un[i+1]-un[i])/62.5) for i in range(7)),
          '| last %5.2f' % ((un[0] + 2 * BIT + (P - 2 * BIT) * 1 - un[7]) / 62.5))
    return P, un


for pat in ('zeros', 'ones'):
    for rep in (0, 1, 2):
        measure(pat, rep, 350.0 if pat == 'zeros' else 700.0)
