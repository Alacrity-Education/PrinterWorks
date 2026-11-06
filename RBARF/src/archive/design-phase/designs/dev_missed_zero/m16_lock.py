"""Phase-locking: the data-dependent loop term makes the sampler phase track the
bit grid.  Compare in-frame vs idle-tail loop period, and the phase crawl rate."""
from mz_common import *
import numpy as np
from collections import Counter

meta, caps = load()
print("%-11s %3s %10s %10s %10s %9s %7s" %
      ("pattern", "rep", "loop_frame", "loop_tail", "crawl/loop", "amb_bits", "swal"))
tot = Counter(); cr = []
for c in caps:
    P = prepare(c)
    t, sl, lv, it = P["t"], P["sl"], P["lv"], P["it"]
    b = np.array(P["bits"])
    # loop period in-frame: use slot-0 samples with t in [0, 240us]
    m0 = (sl == 0)
    t0s = t[m0]; i0s = it[m0]
    inf = (t0s >= 0) & (t0s < NBITS * BIT)
    tail = t0s > NBITS * BIT + 50000
    lf = np.polyfit(i0s[inf], t0s[inf], 1)[0] if inf.sum() > 5 else float("nan")
    lt = np.polyfit(i0s[tail], t0s[tail], 1)[0] if tail.sum() > 5 else float("nan")
    # phase crawl: offset of slot-0 sample within its bit, in-frame
    ph = t0s[inf] - np.round(t0s[inf] / BIT) * BIT
    crawl = np.polyfit(i0s[inf], ph, 1)[0] if inf.sum() > 5 else float("nan")
    cr.append(crawl)
    amb = sum(1 for n in range(NBITS)
              if not ((t >= n * BIT + 350) & (t < n * BIT + 700)).any())
    sw = 0
    for n in range(NBITS):
        s0 = np.nonzero((t >= n * BIT) & (t < n * BIT + 350))[0]
        if b[n] == 0 and (len(s0) == 0 or not lv[s0].any()):
            sw += 1
    tot["amb"] += amb; tot["sw"] += sw
    print("%-11s %3d %10.2f %10.2f %+10.3f %9d %7d"
          % (c["pattern"], c["rep"], lf, lt, crawl, amb, sw))
cr = np.array(cr)
print("\nmean in-frame crawl %+.3f ns/loop (|.| median %.3f, max %.3f)"
      % (cr.mean(), np.median(np.abs(cr)), np.abs(cr).max()))
print("total intrinsically ambiguous bits %d/10368, swallowed %d" % (tot["amb"], tot["sw"]))
