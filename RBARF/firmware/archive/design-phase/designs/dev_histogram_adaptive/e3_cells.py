"""Cell decomposition: midpoint edges -> (width u, period d) in bit units.
Adaptive bit-period estimate from the rise-to-rise comb (no fixed ns)."""
import json, math
from collections import Counter, defaultdict
from common import *

meta, caps = load_dataset()
A = json.load(open("align.json"))
f = A["f"]
byk = {(r["pattern"], r["rep"]): r for r in A["rows"]}


def cells_of(samples, T):
    """-> list of dicts with rise/fall midpoint times."""
    ev = []
    prev = samples[0][2]
    if prev:
        ev.append(("R", T[0] - 60.0, 0))
    for j in range(1, len(samples)):
        v = samples[j][2]
        if v != prev:
            mid = 0.5 * (T[j - 1] + T[j])
            ev.append(("R" if v else "F", mid, j))
            prev = v
    cs = []
    i = 0
    while i < len(ev):
        if ev[i][0] != "R":
            i += 1
            continue
        r = ev[i][1]
        fl = ev[i + 1][1] if i + 1 < len(ev) and ev[i + 1][0] == "F" else None
        nr = None
        for k in range(i + 1, len(ev)):
            if ev[k][0] == "R":
                nr = ev[k][1]
                break
        cs.append(dict(rise=r, fall=fl, nrise=nr, jr=ev[i][2]))
        i += 1
    return cs


def comb_fit(periods, p_lo, p_hi, n=4001):
    """Adaptive fundamental: minimize sum (p/P - round(p/P))^2 over P."""
    best = None
    for k in range(n):
        P = p_lo + k * (p_hi - p_lo) / (n - 1)
        e = 0.0
        for p in periods:
            q = p / P
            if q > 4.5:
                continue
            e += (q - round(q)) ** 2
        if best is None or e < best[1]:
            best = (P, e)
    return best[0]


DAT = defaultdict(list)
Pest = []
for c in caps:
    r = byk[(c["pattern"], c["rep"])]
    t0, L = r["t0"], r["L"]
    s = linearize(c["capture"]); bits = frame_bits(c["payload"])
    T = [t0 + (i + f[sl]) * L for i, sl, _ in s]
    cs = cells_of(s, T)
    cs = [x for x in cs if x["fall"] is not None and x["nrise"] is not None]
    per = [x["nrise"] - x["rise"] for x in cs]
    P = comb_fit(per, 1150.0, 1350.0)
    Pest.append((c["pattern"], c["rep"], P))
    for x in cs:
        u = (x["fall"] - x["rise"]) / P
        d = (x["nrise"] - x["rise"]) / P
        # true label: which bits does this cell cover, by TRUE bit index
        k0 = int(round(x["rise"] / BIT))
        k1 = int(round(x["nrise"] / BIT))
        if not (0 <= k0 < 192 and 0 < k1 <= 192):
            continue
        lbl = "".join(str(b) for b in bits[k0:k1])
        DAT[lbl].append((u, d, k1 - k0, c["pattern"]))

print("P estimates: min %.2f max %.2f med %.2f" % (
    min(p for _, _, p in Pest), max(p for _, _, p in Pest),
    sorted(p for _, _, p in Pest)[len(Pest) // 2]))
for p, rep, P in Pest[:6]:
    print("   ", p, rep, round(P, 2))

print("\n=== cell label -> (u width, d period) stats ===")
tot = 0
for lbl in sorted(DAT, key=lambda k: (len(k), k)):
    v = DAT[lbl]
    tot += len(v)
    us = sorted(x[0] for x in v); ds = sorted(x[1] for x in v)
    if len(v) < 4:
        continue
    print(f"{lbl:>6s} n={len(v):5d}  u: "
          f"{us[0]:.3f}/{us[len(us)//20]:.3f}/{us[len(us)//2]:.3f}/"
          f"{us[-1-len(us)//20]:.3f}/{us[-1]:.3f}   d: "
          f"{ds[0]:.3f}/{ds[len(ds)//2]:.3f}/{ds[-1]:.3f}")
print("cells total", tot)
rare = {k: len(v) for k, v in DAT.items() if len(v) < 4}
print("rare labels:", rare)

# separability of u within d==1 cells
print("\n=== d==1 cells: u for '0' vs '1' ===")
z = sorted(x[0] for x in DAT.get("0", []))
o = sorted(x[0] for x in DAT.get("1", []))
print(f"  '0' n={len(z)} p1={z[len(z)//100]:.3f} p50={z[len(z)//2]:.3f} "
      f"p99={z[-1-len(z)//100]:.3f} max={z[-1]:.3f}")
print(f"  '1' n={len(o)} min={o[0]:.3f} p1={o[len(o)//100]:.3f} "
      f"p50={o[len(o)//2]:.3f} p99={o[-1-len(o)//100]:.3f}")
for th in (0.38, 0.40, 0.42, 0.44, 0.46):
    fp = sum(1 for x in z if x > th); fn = sum(1 for x in o if x <= th)
    print(f"  thr u={th}: zeros_called_1={fp} ones_called_0={fn}")
json.dump({"P": [(a, b, c_) for a, b, c_ in Pest]}, open("pest.json", "w"))
