"""Bracket (interval) classification of pulse total-high duration on the exact grid.

For a pulse whose FIRST covered bit index is n:
    rise bracket (ra, rb]  must contain n*BIT
    fall bracket (fa, fb]  must contain n*BIT + Htot
where Htot in {h0, h1, BIT+h0, BIT+h1, 2BIT+h0, 2BIT+h1, ...}
(span s, last bit b  ->  Htot = (s-1)*BIT + h_b).
Measure how often the surviving candidate set is a singleton and correct.
"""
from mz_common import *
from collections import Counter
import numpy as np

meta, caps = load()
H0, H1 = 350.0, 700.0
CANDS = [((s, bb), (s - 1) * BIT + (H1 if bb else H0)) for s in (1, 2, 3) for bb in (0, 1)]

for TOL in (0.0, 40.0, 80.0, 120.0):
    cnt = Counter()
    for c in caps:
        P = prepare(c)
        t, lv, bits = P["t"], P["lv"], P["bits"]
        b = np.array(bits)
        N = len(t)
        recs = []
        for i0, i1 in pulse_runs(lv):
            if t[i0] >= NBITS * BIT + 300:
                continue
            ra = t[i0 - 1] if i0 > 0 else t[i0] - 250.0
            fb = t[i1 + 1] if i1 + 1 < N else t[i1] + 250.0
            recs.append(dict(i0=i0, i1=i1, ra=ra, rb=t[i0], fa=t[i1], fb=fb,
                             rmid=(ra + t[i0]) / 2, fmid=(t[i1] + fb) / 2,
                             ns=i1 - i0 + 1))
        if not recs:
            continue
        # absolute grid index from rise midpoint, anchored so first pulse -> bit 0
        n0 = round(recs[0]["rmid"] / BIT)
        for r in recs:
            r["n"] = round(r["rmid"] / BIT)
        # truth: span = #bits covered, from the next pulse's start index and the
        # rule that only 1-bits merge; verify against the real bit string.
        for ri, r in enumerate(recs):
            nn = recs[ri + 1]["n"] if ri + 1 < len(recs) else NBITS
            n = r["n"]
            if not (0 <= n < NBITS):
                cnt["oob"] += 1
                continue
            # true span: largest s<=nn-n such that bits n..n+s-2 are all 1
            s = 1
            while n + s < nn and n + s <= NBITS - 1 and b[n + s - 1] == 1 and s < 3:
                # candidate merge; decide by whether pulse actually covers it:
                # use fall bracket -> covered iff fa >= (n+s)*BIT
                if r["fa"] >= (n + s) * BIT:
                    s += 1
                else:
                    break
            r["span_true"] = s
            r["last_true"] = int(b[n + s - 1])
            u = r["fa"] - n * BIT
            v = r["fb"] - n * BIT
            surv = [k for k, ht in CANDS if (ht > u - TOL) and (ht <= v + TOL)]
            r["surv"] = surv
            truth = (s, int(b[n + s - 1]))
            cnt["tot"] += 1
            cnt["n%d" % len(surv)] += 1
            if truth in surv:
                cnt["contains"] += 1
            if len(surv) == 1:
                cnt["single"] += 1
                if surv[0] == truth:
                    cnt["single_ok"] += 1
            if len(surv) == 0:
                cnt["empty"] += 1
    print("TOL=%5.0f  tot=%d  contains-truth=%d (%.4f)  singleton=%d ok=%d (%.4f)  empty=%d  sizes=%s"
          % (TOL, cnt["tot"], cnt["contains"], cnt["contains"] / cnt["tot"],
             cnt["single"], cnt["single_ok"], cnt["single_ok"] / max(1, cnt["single"]),
             cnt["empty"],
             {k: v for k, v in sorted(cnt.items()) if k.startswith("n")}))
