"""Model-light probe of the END-OF-LOOP gap width.

The 'ones' pattern puts a 550 ns LOW between every pair of 700 ns HIGHs.
Whenever a 550 ns low leaves no low sample the two highs merge.  Counting
merges, and the SLOT at which each merge occurs, measures the inter-slot
gap widths without needing any fitted time base: a gap can swallow a
550 ns low only if the gap is wider than 550 ns.

Likewise 'zeros' puts a 350 ns HIGH every 1250 ns; a missing high pulse
means a gap wider than 350 ns.
"""
import numpy as np
from collections import Counter
from common import load_caps

meta, caps = load_caps()
NB = 192


def runs(cap):
    o = np.lexsort((cap.sl, cap.it))
    it, sl, lv = cap.it[o].astype(int), cap.sl[o], cap.lev[o]
    out = []
    st = 0
    for k in range(1, len(lv) + 1):
        if k == len(lv) or lv[k] != lv[st]:
            out.append((int(lv[st]), it[st], int(sl[st]), it[k - 1], int(sl[k - 1]),
                        k - st))
            st = k
    return out


for pat in ("ones", "zeros", "p55", "aa"):
    for cap in caps:
        if cap.pattern != pat or cap.rep != 0:
            continue
        r = runs(cap)
        nb1 = sum(cap.bits)
        # count HIGH runs inside the frame (loops 0..99)
        hi = [x for x in r if x[0] == 1 and x[1] < 100]
        lo = [x for x in r if x[0] == 0 and x[1] < 100]
        print(f"{cap.name}: {sum(cap.bits)} one-bits, {192-sum(cap.bits)} zero-bits;"
              f" {len(hi)} high runs, {len(lo)} low runs in loops<100")
        print("   high-run sample-count histogram:",
              dict(sorted(Counter(x[5] for x in hi).items())))
        print("   low-run  sample-count histogram:",
              dict(sorted(Counter(x[5] for x in lo).items())))
        # gap at which each low run *ends* (i.e. the slot of its last sample)
        print("   slot of last sample of each 1-sample LOW run:",
              dict(sorted(Counter(x[4] for x in lo if x[5] == 1).items())))
        # for 'ones': merged highs = high runs longer than a single bit
        if pat == "ones":
            print("   slot BEFORE each merge (i.e. the gap that ate a T1L):")
            c = Counter()
            for a, b in zip(hi, hi[1:]):
                pass
            # a merge shows up as a long high run; find the gap index by
            # locating which slot boundary sits inside the missing low
            for x in hi:
                if x[5] >= 6:                      # >= 6 samples ~ merged
                    c[(x[2], x[4], x[5])] += 1
            print("   long high runs (startslot,endslot,nsamp):",
                  dict(sorted(c.items())))
        print()
