"""Soft-output contract: RESOLVED / HARD / INFEASIBLE classes and their accuracy."""
from mz_common import *
import numpy as np
from collections import Counter
from harness import linearize
import m4_decode as M
import m8_v2 as V

meta, caps = load()
H0, H1 = 350.0, 700.0
cnt = Counter()
tolslack = 120.0
for c in caps:
    samples = linearize(c["capture"])
    it, sl, lv, A = V.build(samples)
    recs = M.brackets(A, lv)
    k, t0 = V.blind(recs)
    for r in recs:
        for kk in ("ra", "rb", "fa", "fb", "rmid", "fmid"):
            r[kk] = t0 + k * r[kk]
    recs = [r for r in recs if r["rmid"] < NBITS * BIT + 400]
    n = V.index(recs)
    truth = bits_of(bytes.fromhex(c["frame"]))
    for j, r in enumerate(recs):
        nxt = n[j + 1] if j + 1 < len(recs) else NBITS
        maxs = max(1, nxt - n[j])
        u = r["fa"] - n[j] * BIT
        v = r["fb"] - n[j] * BIT
        feas = []
        for s in range(1, min(maxs, 4) + 1):
            for bb in (0, 1):
                ht = (s - 1) * BIT + (H1 if bb else H0)
                if u < ht <= v:
                    feas.append((s, bb))
        # truth for this pulse: span = bits until next pulse that are 1 + last
        seg = truth[n[j]:nxt] if 0 <= n[j] < NBITS else []
        ts = 1
        while ts < len(seg) and seg[ts - 1] == 1:
            ts += 1
        tb = seg[ts - 1] if seg else 0
        if len(feas) == 1:
            cls = "RESOLVED"
            good = feas[0] == (ts, tb)
        elif len(feas) == 0:
            cls = "INFEASIBLE"
            # fall back: nearest candidate with slack
            best = min(((s, bb, abs((s - 1) * BIT + (H1 if bb else H0) - (u + v) / 2))
                        for s in range(1, min(maxs, 4) + 1) for bb in (0, 1)),
                       key=lambda x: x[2])
            good = (best[0], best[1]) == (ts, tb)
        else:
            cls = "HARD"
            best = min(((s, bb, abs((s - 1) * BIT + (H1 if bb else H0) - (u + v) / 2))
                        for s, bb in feas), key=lambda x: x[2])
            good = (best[0], best[1]) == (ts, tb)
            cnt["hard_contains_truth"] += ((ts, tb) in feas)
        cnt[cls] += 1
        cnt[cls + "_ok"] += good
        cnt["tot"] += 1

for cls in ("RESOLVED", "HARD", "INFEASIBLE"):
    n_ = cnt[cls]
    print("%-11s %5d (%5.2f%%)  correct %5d = %.4f" %
          (cls, n_, 100 * n_ / cnt["tot"], cnt[cls + "_ok"], cnt[cls + "_ok"] / max(1, n_)))
print("HARD sets containing truth: %d/%d" % (cnt["hard_contains_truth"], cnt["HARD"]))
print("per capture: RESOLVED %.1f HARD %.1f INFEASIBLE %.1f" %
      (cnt["RESOLVED"] / 54, cnt["HARD"] / 54, cnt["INFEASIBLE"] / 54))
