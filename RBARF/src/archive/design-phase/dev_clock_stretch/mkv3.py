src='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py'
dst='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_clock_stretch/cs_v3.py'
s=open(src).read()
s=s.replace("POSTERIOR = False","POSTERIOR = False\nPATH_BITS = True")
# record per-(state,transition) bit choice
s=s.replace("""        # emission[e][d]
        em = [[0.0] * nd for _ in range(ne)]""",
"""        # emission[e][d]
        em = [[0.0] * nd for _ in range(ne)]
        bs = [[0] * nd for _ in range(ne)]""")
s=s.replace("""                if kb is None:
                    e = l1 if l1 > l0 else l0
                else:
                    e = l1 if kb else l0
                em[ei][di] = e + pen0 - DP_RATE_PEN * d * d""",
"""                if kb is None:
                    e = l1 if l1 > l0 else l0
                else:
                    e = l1 if kb else l0
                bs[ei][di] = 1 if l1 > l0 else 0
                em[ei][di] = e + pen0 - DP_RATE_PEN * d * d""")
s=s.replace("""        score = nxt
        back.append(bk)""","""        score = nxt
        back.append(bk)
        bsel.append(bs)""")
s=s.replace("""    score = [NEG] * ne
    score[DP_E] = 0.0
    back = []""","""    score = [NEG] * ne
    score[DP_E] = 0.0
    back = []
    bsel = []""")
s=s.replace("""    return [C[k] + (path[k] - DP_E) * DP_RES for k in range(NBITS + 1)], total""",
"""    pbits = [0] * NBITS
    for k in range(NBITS):
        di = path[k + 1] - path[k] + DP_D
        if 0 <= di < nd:
            pbits[k] = bsel[k][path[k]][di]
    return ([C[k] + (path[k] - DP_E) * DP_RES for k in range(NBITS + 1)],
            total, pbits)""")
s=s.replace("""        C, sc = _dp_track(samples, cyc, C, n_end, by_k)
        if POSTERIOR:""","""        C, sc, pbits = _dp_track(samples, cyc, C, n_end, by_k)
        if PATH_BITS:
            llr = [1.0 if b else -1.0 for b in pbits]
        elif POSTERIOR:""")
open(dst,'w').write(s)
print('ok')
