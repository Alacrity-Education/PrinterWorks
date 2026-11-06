import sys
src='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py'
dst='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_clock_stretch/cs_v2.py'
s=open(src).read()
s=s.replace("DP_RATE_PEN = 0.4","DP_PASSES = 1\nFIT_MU = 0.004\nUSE_REFINE = True\nIDLE_COST = True\nDP_RATE_PEN = 0.4")
s=s.replace("def _fit(C, anchors, lam=0.6, mu=0.004, iters=260, step=0.05):",
            "def _fit(C, anchors, lam=0.6, mu=None, iters=260, step=0.05):\n    if mu is None:\n        mu = FIT_MU")
s=s.replace("""        C, sc = _refine_ml(samples, cyc, C, n_end, anchors, KNOT_SETS)
        C, sc = _dp_track(samples, cyc, C, n_end, by_k)""",
"""        if USE_REFINE:
            C, sc = _refine_ml(samples, cyc, C, n_end, anchors, KNOT_SETS)
        for _p in range(DP_PASSES):
            C, sc = _dp_track(samples, cyc, C, n_end, by_k)""")
s=s.replace("""    bestj = max(range(ne), key=lambda x: score[x])""",
"""    if IDLE_COST:
        for ej in range(ne):
            if score[ej] <= NEG / 2:
                continue
            end = C[NBITS] + (ej - DP_E) * DP_RES
            pen = 0.0
            for i in range(n - 1, -1, -1):
                if cyc[i] <= end:
                    break
                if samples[i][2]:
                    pen += _LIDLE
            score[ej] += pen
    bestj = max(range(ne), key=lambda x: score[x])""")
open(dst,'w').write(s)
print('ok', 'IDLE_COST' in s, 'DP_PASSES' in s)
