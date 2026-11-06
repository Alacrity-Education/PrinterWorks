"""Verify the generative CELL model on real data.

Cell = rise -> next rise.  Claim: a cell covering n bits has the form
    [1]*(m-1) + [b] + [0]*(n-m)
i.e. m-1 merged 1-bits, one bit b whose fall is the observed fall, then
n-m swallowed 0-bits.  Measure how often that holds, and tabulate the
cell census per pattern.
"""
from collections import Counter, defaultdict

import numpy as np

from g0_common import *

meta, caps = load_all()

cellcensus = Counter()
violations = Counter()
per_cap = []
nlast = Counter()

for c in caps:
    lv, tt, bits = c["lv"], c["ttrue"], c["bits"]
    ev = edge_list(lv)
    rises = [e for e in ev if e[0] == "R"]
    falls = [e for e in ev if e[0] == "F"]
    # capture starts high (edge triggered) -> synthesize rise at index 0
    assert lv[0] == 1, c["key"]
    R0 = [("R", -1, 0)] + rises
    # pair each rise with the next fall
    cells = []
    for qi, (_, a, b) in enumerate(R0):
        f = next((x for x in falls if x[2] > b), None)
        nr = R0[qi + 1] if qi + 1 < len(R0) else None
        cells.append((b, f, nr[2] if nr else None))
    nb = 0
    for (jr, f, jnr) in cells:
        # true bit range covered
        k0 = int(np.floor(tt[jr] / BIT))
        if jnr is None:
            k1 = 192
        else:
            k1 = int(np.floor(tt[jnr] / BIT))
        if k0 < 0:
            k0 = 0
        if not (0 <= k0 < 192):
            continue
        k1 = min(max(k1, k0 + 1), 192)
        sub = bits[k0:k1]
        n = k1 - k0
        # model: m-1 ones, then b, then zeros
        s = "".join(str(int(x)) for x in sub)
        cellcensus[s] += 1
        nb += n
        # check structural claim: after the first 0 everything is 0
        z = s.find("0")
        ok = (z < 0) or set(s[z:]) == {"0"}
        if not ok:
            violations[s] += 1
    per_cap.append((c["key"], len(cells), nb))

print("=== cell census (true bit substring covered by one rise->rise cell) ===")
tot = sum(cellcensus.values())
for s, n in sorted(cellcensus.items(), key=lambda kv: (len(kv[0]), kv[0])):
    print(f"  {s:<8s} {n:6d}  {100*n/tot:5.2f}%")
print("total cells", tot)
print("\nstructural violations (non-monotone 1*0*):", dict(violations))
print("\nper-capture cells / bits-covered:")
for k, nc, nb in per_cap:
    print(f"  {k:14s} cells={nc:4d} bits={nb:4d}")
