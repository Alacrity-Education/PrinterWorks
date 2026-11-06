"""Rise-edge phase tracking: residual (rmid - n*BIT) vs bit index; local refinement."""
from mz_common import *
import numpy as np
from collections import Counter
import m4_decode as M
from harness import linearize

meta, caps = load()
res_all = []
slope = []
for c in caps:
    P = prepare(c)
    t, lv = P["t"], P["lv"]
    recs = M.brackets(P["A"], lv)
    for r in recs:
        for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
            r[kk] = P["t0"] + P["k"] * r[kk]
    recs = [r for r in recs if r["rmid"] < NBITS * BIT + 400]
    n = [int(round(recs[0]["rmid"] / BIT))]
    for j in range(1, len(recs)):
        n.append(n[-1] + int(round((recs[j]["rmid"] - recs[j - 1]["rmid"]) / BIT)))
    n = np.array(n, float)
    rm = np.array([r["rmid"] for r in recs])
    ra = np.array([r["ra"] for r in recs])
    rb = np.array([r["rb"] for r in recs])
    res = rm - n * BIT
    res_all.append((c["pattern"], c["rep"], res, n, ra - n * BIT, rb - n * BIT))
    A = np.polyfit(n, res, 1)
    slope.append(A[0])
    # how much does a linear detrend reduce spread?
    r0 = res - res.mean()
    r1 = res - np.polyval(A, n)
    print("%-11s %d  res mean %7.1f std %5.1f | detrended std %5.1f  slope %+6.3f ns/bit"
          % (c["pattern"], c["rep"], res.mean(), res.std(), r1.std(), A[0]))

sl = np.array(slope)
print("\nslope across captures: mean %+.4f ns/bit  std %.4f  min %+.3f max %+.3f"
      % (sl.mean(), sl.std(), sl.min(), sl.max()))
print("  -> equivalent residual clock error after blind/GT scale fit: %.4f%% .. %.4f%%"
      % (100 * sl.min() / BIT, 100 * sl.max() / BIT))

# bracket half-width statistics (how tightly a single rise pins the grid)
RA = np.concatenate([x[4] for x in res_all])
RB = np.concatenate([x[5] for x in res_all])
print("\nrise bracket relative to n*BIT: ra mean %.1f (p5 %.1f)  rb mean %.1f (p95 %.1f)"
      % (RA.mean(), np.percentile(RA, 5), RB.mean(), np.percentile(RB, 95)))
print("bracket width mean %.1f ns, p90 %.1f" % ((RB - RA).mean(), np.percentile(RB - RA, 90)))
print("grid point inside bracket: %.4f" % np.mean((RA <= 0) & (RB >= 0)))
