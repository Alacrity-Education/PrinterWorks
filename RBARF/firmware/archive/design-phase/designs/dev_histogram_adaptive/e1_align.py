"""Fit a global slot geometry + per-capture (t0,L); report residuals."""
import json
from common import *

meta, caps = load_dataset()

# Stage A: fit shared fractional slot offsets on a few captures, then apply.
f = [p / 40.0 for p in (1, 5, 9, 13, 17, 21, 27, 32)]
sub = [c for c in caps if c["rep"] == 0][:6]
pre = []
for c in sub:
    s = linearize(c["capture"]); b = frame_bits(c["payload"])
    t0, L, _, m = fit_timebase(s, b, f0=f, n_l=61, n_t=61)
    pre.append([c, s, b, t0, L])

def total(f, pre):
    return sum(mismatch(s, b, t0, L, f) for _, s, b, t0, L in pre)

m = total(f, pre)
for r in range(7):
    step = (40.0 / (2 ** r)) / 2500.0
    imp = True
    while imp:
        imp = False
        for si in range(8):
            for d in (-step, step):
                g = list(f); g[si] += d
                mm = total(g, pre)
                if mm < m:
                    m, f = mm, g; imp = True
        for k, (c, s, b, t0, L) in enumerate(pre):
            for dT in (-20.0, 20.0):
                if mismatch(s, b, t0 + dT, L, f) < mismatch(s, b, t0, L, f):
                    pre[k][3] = t0 + dT
            for dL in (-1.0, 1.0):
                if mismatch(s, b, pre[k][3], L + dL, f) < mismatch(s, b, pre[k][3], L, f):
                    pre[k][4] = L + dL
        m = total(f, pre)
print("shared slot offsets (loop units):", [round(x, 5) for x in f])
print("shared slot offsets (ns @2507.3):", [round(x * 2507.3, 1) for x in f])
print("gaps ns:", [round((f[i + 1] - f[i]) * 2507.3, 1) for i in range(7)],
      "wrap:", round((1 + f[0] - f[7]) * 2507.3, 1))
print("fit mismatch on 6 caps:", m)

rows = []
for c in caps:
    s = linearize(c["capture"]); b = frame_bits(c["payload"])
    t0, L, _, mm = fit_timebase(s, b, f0=f, n_l=81, n_t=81)
    # refine only t0,L (keep shared f)
    for r in range(8):
        sT = 30.0 / (2 ** r); sL = 4.0 / (2 ** r)
        imp = True
        while imp:
            imp = False
            for dT in (-sT, sT):
                v = mismatch(s, b, t0 + dT, L, f)
                if v < mm: mm, t0 = v, t0 + dT; imp = True
            for dL in (-sL, sL):
                v = mismatch(s, b, t0, L + dL, f)
                if v < mm: mm, L = v, L + dL; imp = True
    rows.append(dict(pattern=c["pattern"], rep=c["rep"], t0=t0, L=L,
                     mis=mm, n=len(s)))
    print(f"{c['pattern']:11s} r{c['rep']} t0={t0:8.1f} L={L:8.2f} "
          f"mis={mm:4d}/{len(s)}")
Ls = [r["L"] for r in rows]
print("L range", min(Ls), max(Ls), "mean", sum(Ls) / len(Ls))
print("total mismatch", sum(r["mis"] for r in rows), "of", sum(r["n"] for r in rows))
json.dump({"f": f, "rows": rows}, open("align.json", "w"), indent=1)
