"""Final constants for the design doc."""
from mz_common import *
import numpy as np
from collections import Counter
import m4_decode as M
from harness import linearize

meta, caps = load()
print("slot offsets o =", [round(x, 3) for x in O], " G =", round(G, 3))
gaps = [O[i + 1] - O[i] for i in range(7)] + [G + O[0] - O[7]]
print("inter-slot gaps ns:", [round(g, 2) for g in gaps])
print("inter-slot gaps cy:", [round(g / 62.5, 3) for g in gaps])
print("sum cy:", round(sum(gaps) / 62.5, 3))
print("w =", W.tolist(), " (ns added per HIGH read at that slot, cumulative)")
print()

sw_by_pat = Counter(); mg_by_pat = Counter(); npat = Counter()
strict_runs = Counter()
hid_hist = Counter()
ns_hist = Counter()
for c in caps:
    P = prepare(c)
    t, lv, it = P["t"], P["lv"], P["it"]
    b = np.array(P["bits"])
    sw = 0; mgs = []
    for n in range(NBITS):
        s0 = np.nonzero((t >= n * BIT) & (t < n * BIT + 350))[0]
        if b[n] == 0 and (len(s0) == 0 or not lv[s0].any()):
            sw += 1
        if b[n] == 1 and n + 1 < NBITS:
            sm = np.nonzero((t >= n * BIT + 700) & (t < (n + 1) * BIT))[0]
            if len(sm) == 0 or lv[sm].all():
                j = np.searchsorted(t, n * BIT + 700) - 1
                mgs.append(int(it[j]))
    sw_by_pat[c["pattern"]] += sw
    mg_by_pat[c["pattern"]] += len(mgs)
    npat[c["pattern"]] += 1
    u = sorted(set(mgs))
    if u:
        r = 1
        for a, bb in zip(u, u[1:]):
            if bb - a == 1:
                r += 1
            else:
                strict_runs[r] += 1; r = 1
        strict_runs[r] += 1
    for i0, i1 in pulse_runs(lv):
        if t[i0] < NBITS * BIT:
            ns_hist[i1 - i0 + 1] += 1

print("per-pattern swallowed 0-bits / merged 1-bits (sum over 3 reps):")
for p in npat:
    print("   %-11s swallowed %3d   merges %3d" % (p, sw_by_pat[p], mg_by_pat[p]))
print()
print("strict consecutive-loop merge run lengths:", dict(sorted(strict_runs.items())))
print("pulse sample-count histogram:", dict(sorted(ns_hist.items())))
