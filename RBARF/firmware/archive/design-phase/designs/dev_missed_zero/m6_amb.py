"""Intrinsic ambiguity: is there a sample in the decisive window [350,700) of a bit?
Also: swallow / merge geometry vs intra-loop phase.
"""
from mz_common import *
from collections import Counter
import numpy as np
import m4_decode as M
from harness import linearize

meta, caps = load()
H0, H1 = 350.0, 700.0

dec = Counter(); slotgap = Counter(); swal_slot = Counter(); merge_slot = Counter()
phase_dec = Counter()
tot = Counter()
gaps_obs = []

for c in caps:
    P = prepare(c)
    t, lv, sl, bits = P["t"], P["lv"], P["sl"], np.array(P["bits"])
    recs = M.brackets(P["A"], lv)
    # per-bit: decisive sample?
    for n in range(NBITS):
        lo, hi = n * BIT + H0, n * BIT + H1
        idx = np.nonzero((t >= lo) & (t < hi))[0]
        d = len(idx) > 0
        dec[(int(bits[n]), d)] += 1
        tot["bits"] += 1
        # which inter-slot gap contains the T0H window end
        # slot of the last sample before lo
        j = np.searchsorted(t, lo) - 1
        if 0 <= j < len(sl):
            phase_dec[(int(sl[j]), d)] += 1
    # swallowed 0-bits: which slot precedes the vanished high window
    for n in range(NBITS):
        if bits[n]:
            continue
        idx = np.nonzero((t >= n * BIT) & (t < n * BIT + H0))[0]
        if len(idx) == 0 or not lv[idx].any():
            j = np.searchsorted(t, n * BIT) - 1
            if 0 <= j < len(sl):
                swal_slot[int(sl[j])] += 1
            tot["swal"] += 1
    # merged 1-1: bit n=1 and n+1 covered by same run -> the T1L window
    # [n*BIT+700, (n+1)*BIT) has no sample or all-high samples
    for n in range(NBITS - 1):
        if not bits[n]:
            continue
        lo, hi = n * BIT + H1, (n + 1) * BIT
        idx = np.nonzero((t >= lo) & (t < hi))[0]
        if len(idx) == 0:
            j = np.searchsorted(t, lo) - 1
            if 0 <= j < len(sl):
                merge_slot[int(sl[j])] += 1
            tot["merge"] += 1
    # observed inter-sample gaps by slot transition
    for m in range(1, len(t)):
        slotgap[int(sl[m - 1])] += 0
        gaps_obs.append((int(sl[m - 1]), t[m] - t[m - 1]))

print("decisive-sample presence by true bit value: ", dict(sorted(dec.items())))
n_amb = dec[(0, False)] + dec[(1, False)]
print("intrinsically ambiguous bits: %d / %d = %.4f  (%.1f per 192-bit frame)"
      % (n_amb, tot["bits"], n_amb / tot["bits"], n_amb / 54))
print()
print("swallowed 0-bit count %d, by slot index of last sample before bit start:" % tot["swal"])
print("   ", dict(sorted(swal_slot.items())))
print("merged (T1L invisible) count %d, by slot index preceding the T1L window:" % tot["merge"])
print("   ", dict(sorted(merge_slot.items())))
print()
G = {}
for s, g in gaps_obs:
    G.setdefault(s, []).append(g)
print("inter-sample gap after slot s (model time base, ns):")
for s in sorted(G):
    a = np.array(G[s])
    print("   slot %d -> %d : mean %6.1f  std %5.1f  n=%d" % (s, (s + 1) % 8, a.mean(), a.std(), len(a)))
print()
print("decisive-sample presence by preceding slot:")
for s in range(8):
    y = phase_dec[(s, True)]; n = phase_dec[(s, False)]
    print("   slot %d : decisive %5d  ambiguous %5d  (amb rate %.3f)" % (s, y, n, n / max(1, y + n)))
