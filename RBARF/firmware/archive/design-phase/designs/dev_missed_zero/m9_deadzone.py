"""Dead-zone schedule: predict per-bit swallow / merge / decisive from sample times
alone (no bit knowledge), then check against truth.  Also merge-run structure."""
from mz_common import *
import numpy as np
from collections import Counter
import m4_decode as M
from harness import linearize

meta, caps = load()
H0, H1 = 350.0, 700.0
cm_sw = Counter(); cm_mg = Counter(); cm_dc = Counter()
runlens = Counter(); merge_it_gap = Counter()
per = []
for c in caps:
    P = prepare(c)
    t, lv, sl, it = P["t"], P["lv"], P["sl"], P["it"]
    b = np.array(P["bits"])
    for n in range(NBITS):
        s0 = np.nonzero((t >= n * BIT) & (t < n * BIT + H0))[0]
        sd = np.nonzero((t >= n * BIT + H0) & (t < n * BIT + H1))[0]
        sm = np.nonzero((t >= n * BIT + H1) & (t < (n + 1) * BIT))[0]
        pred_sw = (len(s0) == 0)                      # 0-bit would vanish
        pred_mg = (len(sm) == 0)                      # T1L would vanish
        pred_dc = (len(sd) > 0)
        true_sw = (len(s0) == 0) or (not lv[s0].any())
        true_mg = (len(sm) == 0) or (lv[sm].all())
        cm_dc[(pred_dc,)] += 1
        if b[n] == 0:
            cm_sw[(pred_sw, true_sw)] += 1
        if b[n] == 1 and n + 1 < NBITS:
            cm_mg[(pred_mg, true_mg)] += 1
    # merge run structure over loop index
    mg_iters = []
    for n in range(NBITS - 1):
        if b[n] != 1:
            continue
        sm = np.nonzero((t >= n * BIT + H1) & (t < (n + 1) * BIT))[0]
        if len(sm) == 0 or lv[sm].all():
            j = np.searchsorted(t, n * BIT + H1) - 1
            mg_iters.append(int(it[j]) if 0 <= j < len(it) else -1)
    mg_iters = sorted(set(mg_iters))
    if mg_iters:
        r = 1
        for a, bb in zip(mg_iters, mg_iters[1:]):
            merge_it_gap[bb - a] += 1
            if bb - a <= 2:
                r += 1
            else:
                runlens[r] += 1
                r = 1
        runlens[r] += 1
    per.append((c["pattern"], c["rep"], mg_iters[:6], len(mg_iters)))

print("swallow prediction (0-bits): (pred,true) ->", dict(sorted(cm_sw.items())))
tp = cm_sw[(True, True)]; fp = cm_sw[(True, False)]; fn = cm_sw[(False, True)]
print("   precision %.3f recall %.3f" % (tp / max(1, tp + fp), tp / max(1, tp + fn)))
print("merge prediction (1-bits): (pred,true) ->", dict(sorted(cm_mg.items())))
tp = cm_mg[(True, True)]; fp = cm_mg[(True, False)]; fn = cm_mg[(False, True)]
print("   precision %.3f recall %.3f" % (tp / max(1, tp + fp), tp / max(1, tp + fn)))
print("decisive-window occupancy:", dict(cm_dc))
print()
print("merge run lengths (consecutive loop indices):", dict(sorted(runlens.items())))
print("gap in loop index between successive merge events:",
      dict(sorted(merge_it_gap.items())[:14]))
print()
for p in per[:8]:
    print("%-11s %d merges=%3d first loops %s" % (p[0], p[1], p[3], p[2]))
