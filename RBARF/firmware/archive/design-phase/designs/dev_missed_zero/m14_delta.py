"""Delta (bracket-dilation) sweep with the BLIND rise-Hough time base."""
from mz_common import *
import numpy as np, importlib.util, sys
from collections import Counter
from harness import linearize
import m4_decode as M

# import m8_v2 without running its module-level sweep
src = open("m8_v2.py").read().split("for mode in (")[0]
mod = type(sys)("v2")
mod.__dict__.update({"__name__": "v2"})
exec(compile(src, "m8_v2.py", "exec"), mod.__dict__)
V = mod

H0, H1 = 350.0, 700.0
meta, caps = load()
CACHE = {}
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
    CACHE[c["pattern"], c["rep"]] = (recs, n, bits_of(bytes.fromhex(c["frame"])),
                                     bytes.fromhex(c["payload"]))

print("%6s %8s %10s %10s %8s %10s %8s" %
      ("delta", "uniq%", "uniq_ok", "amb%", "infeas%", "amb_hit", "EXACT"))
for D in (0.0, 40.0, 80.0, 120.0, 160.0, 200.0):
    c2 = Counter(); ok = 0
    for key, (recs, n, truth, payload) in CACHE.items():
        bits = [0] * NBITS
        for j, r in enumerate(recs):
            nxt = n[j + 1] if j + 1 < len(recs) else NBITS
            maxs = max(1, nxt - n[j])
            u = r["fa"] - n[j] * BIT - D
            v = r["fb"] - n[j] * BIT + D
            feas = [(s, bb) for s in range(1, min(maxs, 4) + 1) for bb in (0, 1)
                    if u < (s - 1) * BIT + (H1 if bb else H0) <= v]
            allc = [(s, bb) for s in range(1, min(maxs, 4) + 1) for bb in (0, 1)]
            mid = (r["fa"] + r["fb"]) / 2 - n[j] * BIT
            pool = feas if feas else allc
            s, bb = min(pool, key=lambda x: abs((x[0] - 1) * BIT + (H1 if x[1] else H0) - mid))
            seg = truth[n[j]:nxt] if 0 <= n[j] < NBITS else []
            ts = 1
            while ts < len(seg) and seg[ts - 1] == 1:
                ts += 1
            tb = seg[ts - 1] if seg else 0
            if len(feas) == 1:
                c2["uniq"] += 1; c2["uniq_ok"] += (feas[0] == (ts, tb))
            elif len(feas) == 0:
                c2["infeas"] += 1; c2["infeas_ok"] += ((s, bb) == (ts, tb))
            else:
                c2["amb"] += 1; c2["amb_hit"] += ((ts, tb) in feas)
            c2["tot"] += 1
            for a in range(s - 1):
                if 0 <= n[j] + a < NBITS:
                    bits[n[j] + a] = 1
            if 0 <= n[j] + s - 1 < NBITS:
                bits[n[j] + s - 1] = bb
        ok += (M.bits_to_bytes(bits)[4:20] == payload)
    print("%6.0f %8.2f %10.4f %10.2f %8.2f %10.4f %6d/54" %
          (D, 100 * c2["uniq"] / c2["tot"], c2["uniq_ok"] / max(1, c2["uniq"]),
           100 * c2["amb"] / c2["tot"], 100 * c2["infeas"] / c2["tot"],
           c2["amb_hit"] / max(1, c2["amb"]), ok))
