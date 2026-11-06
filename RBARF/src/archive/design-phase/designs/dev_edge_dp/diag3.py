"""Structure of the residuals under the best global linear model.

For every in-frame sample compute predicted within-bit phase u and the
bit value; tabulate observed level. If timing were perfect the tables
would be step functions at 375 (bit0) / 750 (bit1).
"""
import json
from collections import defaultdict
import model as M
from fit_slots import FRAME_NS

fit = json.load(open("slotfit.json"))
O = fit["o"]
meta, D = M.load()

BW = 62.5
tab = {0: defaultdict(lambda: [0, 0]), 1: defaultdict(lambda: [0, 0])}
tab_slot = defaultdict(lambda: [0, 0])
for d, (phi, k) in zip(D, fit["nuis"]):
    bits = d["bits"]
    for (i, s), v in zip(d["idx"], d["obs"]):
        t = phi + k * (i * M.L_NOM + O[s])
        if not (0 <= t < FRAME_NS):
            continue
        kk = int(t // M.BIT); u = t - kk * M.BIT
        b = bits[kk]
        c = tab[b][int(u // BW)]
        c[0] += 1; c[1] += v
        pred = M.level_at(bits, t)
        e = tab_slot[s]
        e[0] += 1; e[1] += (pred != v)

print("bit=0: bin(ns)  n   P(high)     | bit=1: n   P(high)")
for j in range(20):
    a = tab[0][j]; b = tab[1][j]
    pa = a[1] / a[0] if a[0] else float('nan')
    pb = b[1] / b[0] if b[0] else float('nan')
    print(f"  {j*BW:6.0f}-{(j+1)*BW:6.0f}  {a[0]:5d} {pa:6.3f}   |  {b[0]:5d} {pb:6.3f}")

print("\nmismatch rate by slot:")
for s in range(8):
    n, m = tab_slot[s]
    print(f"  slot {s}: {m}/{n} = {m/n:.3f}")
