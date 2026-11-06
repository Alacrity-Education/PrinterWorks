src='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/clock_stretch.py'
dst='/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_clock_stretch/cs_v4.py'
s=open(src).read()
s=s.replace("""def _cycles(samples):
    return [it * L_CYCLES + SLOT_POS[sl] for it, sl, _ in samples]""",
"""def _cycles(samples):
    if not any(EPS):
        return [it * L_CYCLES + SLOT_POS[sl] for it, sl, _ in samples]
    out = []
    extra = 0.0
    for it, sl, v in samples:
        out.append(it * L_CYCLES + SLOT_POS[sl] + extra)
        if v:
            extra += EPS[sl]
    return out""")
s=s.replace("DP_RATE_PEN = 0.4","EPS = [0.0] * 8\nDP_RATE_PEN = 0.4")
open(dst,'w').write(s)
print('ok')
