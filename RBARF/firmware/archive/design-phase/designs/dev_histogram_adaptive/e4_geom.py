"""Clean alternating fit: global slot offsets o[0..7] (ns within loop) +
per-capture (t0, L). Per-slot step is an exact 1-D grid argmin."""
import json, math
from collections import Counter
from common import *

meta, caps = load_dataset()
GRID = 2.0          # ns resolution for the per-slot 1-D scan
SPAN = 3000.0


def prep(c):
    s = linearize(c["capture"])
    b = frame_bits(c["payload"])
    return s, b


def fit_tL(s, b, o, t0, L, rounds=9):
    def mis(t0, L):
        return sum(1 for i, sl, v in s
                   if level_at(b, t0 + i * L + o[sl]) != v)
    m = mis(t0, L)
    for r in range(rounds):
        sT = 60.0 / (2 ** r); sL = 6.0 / (2 ** r)
        imp = True
        while imp:
            imp = False
            for dT in (-sT, sT):
                v = mis(t0 + dT, L)
                if v < m: m, t0 = v, t0 + dT; imp = True
            for dL in (-sL, sL):
                v = mis(t0, L + dL)
                if v < m: m, L = v, L + dL; imp = True
    return t0, L, m


def coarse_tL(s, b, o):
    best = None
    for li in range(81):
        L = 2480.0 + li * 50.0 / 80
        for ti in range(121):
            t0 = -600.0 + ti * 1200.0 / 120
            m = sum(1 for i, sl, v in s
                    if level_at(b, t0 + i * L + o[sl]) != v)
            if best is None or m < best[2]:
                best = (t0, L, m)
    return best


o = [p * 2500.0 / 40.0 for p in (1, 5, 9, 13, 17, 21, 27, 32)]
work = []
for c in caps:
    s, b = prep(c)
    work.append([c, s, b, 0.0, 2500.0])

for it in range(5):
    # per-capture t0,L
    tot = 0
    for w in work:
        c, s, b, t0, L = w
        if it == 0:
            t0, L, m = coarse_tL(s, b, o)
        t0, L, m = fit_tL(s, b, o, t0, L)
        w[3], w[4] = t0, L
        tot += m
    print(f"iter {it} after tL: mismatch {tot}")
    # per-slot 1-D argmin over all captures
    newo = list(o)
    for sl in range(8):
        cost = [0] * int(SPAN / GRID)
        for c, s, b, t0, L in work:
            for i, ss, v in s:
                if ss != sl:
                    continue
                x = t0 + i * L
                for gi in range(len(cost)):
                    pass
                break
        # vectorised-ish: build per-capture x lists then scan grid
        xs = []
        for c, s, b, t0, L in work:
            xl = [(t0 + i * L, v) for i, ss, v in s if ss == sl]
            xs.append((b, xl))
        best = None
        gi = 0
        while gi * GRID < SPAN:
            off = gi * GRID
            m = 0
            for b, xl in xs:
                for x, v in xl:
                    if level_at(b, x + off) != v:
                        m += 1
            if best is None or m < best[1]:
                best = (off, m)
            gi += 1
        newo[sl] = best[0]
    o = newo
    print("  o =", [round(x, 1) for x in o],
          "gaps", [round(o[i + 1] - o[i], 1) for i in range(7)])

tot = 0
rows = []
for w in work:
    c, s, b, t0, L = w
    t0, L, m = fit_tL(s, b, o, t0, L)
    w[3], w[4] = t0, L
    tot += m
    rows.append(dict(pattern=c["pattern"], rep=c["rep"], t0=t0, L=L, mis=m))
print("final mismatch", tot, "of", sum(len(w[1]) for w in work))
Ls = [r["L"] for r in rows]
print("L min/med/max", min(Ls), sorted(Ls)[len(Ls) // 2], max(Ls))
for r in sorted(rows, key=lambda r: -r["mis"])[:10]:
    print("  worst:", r["pattern"], r["rep"], r["mis"], round(r["L"], 2))
json.dump({"o": o, "rows": rows}, open("geom.json", "w"), indent=1)
