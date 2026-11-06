"""Measure swallowed-0 / merged-1 statistics on the fitted time base."""
from common import *
import numpy as np, json, statistics
from collections import Counter, defaultdict

meta, caps = load()
rows = []
allstats = Counter()
gap_by_k = defaultdict(list)
pulse_by_span = defaultdict(list)
slot_of_swallow = Counter()
slot_of_merge = Counter()
per_pattern = defaultdict(Counter)

for c in caps:
    p = prepare(c)
    f, bits = p['f'], p['bits']
    nb = len(bits)
    times = np.array([f(i, s) for i, s, _ in p['samples']])
    lev = np.array([v for _, _, v in p['samples']])
    slots = np.array([s for _, s, _ in p['samples']])
    iters = np.array([i for i, _, _ in p['samples']])
    # samples inside each bit's high window
    nhigh_win = []
    for k in range(nb):
        hi = T1H if bits[k] else T0H
        m = (times >= k*BIT) & (times < k*BIT+hi)
        nhigh_win.append(int(np.count_nonzero(m & (lev==1))))
    nhigh_win = np.array(nhigh_win)
    # samples inside each bit's LOW window (after high, before next bit)
    nlow_win = []
    for k in range(nb):
        hi = T1H if bits[k] else T0H
        m = (times >= k*BIT+hi) & (times < (k+1)*BIT)
        nlow_win.append(int(np.count_nonzero(m)))
    nlow_win = np.array(nlow_win)

    z = np.array([b==0 for b in bits]); o = ~z
    st = dict(pattern=c['pattern'], rep=c['rep'],
              n0=int(z.sum()), n1=int(o.sum()),
              swallow0=int(((nhigh_win==0)&z).sum()),
              swallow1=int(((nhigh_win==0)&o).sum()),
              merge=int((nlow_win[:-1]==0).sum()))
    # which slot-gap swallowed each zero
    for k in range(nb):
        if nhigh_win[k]==0 and bits[k]==0:
            # find bracketing samples
            j = int(np.searchsorted(times, k*BIT))
            if 0 < j < len(times):
                slot_of_swallow[(int(slots[j-1]), int(slots[j]))] += 1
        if k+1 < nb and nlow_win[k]==0:
            hi = T1H if bits[k] else T0H
            j = int(np.searchsorted(times, k*BIT+hi))
            if 0 < j < len(times):
                slot_of_merge[(int(slots[j-1]), int(slots[j]), bits[k], bits[k+1])] += 1
    rows.append(st)
    per_pattern[c['pattern']]['swallow0'] += st['swallow0']
    per_pattern[c['pattern']]['merge'] += st['merge']
    per_pattern[c['pattern']]['n0'] += st['n0']
    per_pattern[c['pattern']]['n1'] += st['n1']

print(f"{'pattern':11s} {'rep':>3s} {'n0':>4s} {'n1':>4s} {'swal0':>5s} {'swal1':>5s} {'merge':>5s}")
for r in rows:
    print(f"{r['pattern']:11s} {r['rep']:3d} {r['n0']:4d} {r['n1']:4d} "
          f"{r['swallow0']:5d} {r['swallow1']:5d} {r['merge']:5d}")
print()
print("TOTALS: n0=%d n1=%d swallowed0=%d (%.2f%%) swallowed1=%d merges=%d (%.2f%% of adjacent pairs)" % (
    sum(r['n0'] for r in rows), sum(r['n1'] for r in rows),
    sum(r['swallow0'] for r in rows), 100*sum(r['swallow0'] for r in rows)/sum(r['n0'] for r in rows),
    sum(r['swallow1'] for r in rows), sum(r['merge'] for r in rows),
    100*sum(r['merge'] for r in rows)/(54*191)))
print()
print("swallowed-0 bracketing slot pair (prev_slot -> next_slot):", dict(sorted(slot_of_swallow.items(), key=lambda x:-x[1])))
print()
print("merge bracketing (prev_slot,next_slot,bit_k,bit_k+1):")
for kk,v in sorted(slot_of_merge.items(), key=lambda x:-x[1])[:20]:
    print("  ", kk, v)
json.dump(rows, open('measure_rows.json','w'), indent=1)
