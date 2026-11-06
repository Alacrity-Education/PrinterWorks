"""Measure the two accept-guard options against the owner-fixed baseline
(stop at first pass), at production (48 B) and test (16 B) scale."""
import sys, pathlib, pickle
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21                                             # noqa: E402

D = pathlib.Path(__file__).parent
PROD = pickle.load((D / "prod_cache.pkl").open("rb"))
TEST = pickle.load((D / "e2e_cache.pkl").open("rb"))


def run(recs, ND, td, mg, N, W, T, guard):
    c = Counter(); tr = []
    for k, (rec, truth) in recs.items():
        if rec is None or rec[2]:
            c["refuse"] += 1; continue
        bits, mgv, _ = rec
        n0 = sum(1 for v in mgv if v == 0)
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
        if path == "direct":
            if n0 > td:
                c["refuse"] += 1; continue
            c["ok_direct" if got == truth else "CAT"] += 1; continue
        if n0 > td:
            c["refuse"] += 1; continue
        nlow = sum(1 for v in mgv if v <= mg)
        if nlow == 0 or nlow > N:
            c["refuse"] += 1; continue
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W, TMAX=T,
                                  ordering="dfirst", fallback=False,
                                  guard=guard)
        tr.append(nt)
        if got is None:
            c["refuse"] += 1
        else:
            c["ok_chase" if got == truth else "CAT"] += 1
    return c, tr


for label, recs, ND, td, mg in (("PRODUCTION 48 B data (472-bit frame)",
                                 PROD, 48, 8, 8),
                                ("TEST 16 B data (216-bit frame)",
                                 TEST, 16, 8, 8)):
    print("=== %s, n=%d ===" % (label, len(recs)))
    for N, W, T in ((4, 2, 11), (6, 2, 22), (8, 2, 37), (8, 3, 93)):
        for g in ("none", "alias", "unique"):
            c, tr = run(recs, ND, td, mg, N, W, T, g)
            ok = c["ok_direct"] + c["ok_chase"]
            print("  N<=%d W<=%d T=%2d guard=%-6s deliver %4d (%5.1f%%) "
                  "dir %4d chase %3d refuse %4d  CAT %d  trials mean %4.1f "
                  "max %2d"
                  % (N, W, T, g, ok, 100.0 * ok / len(recs), c["ok_direct"],
                     c["ok_chase"], c["refuse"], c["CAT"],
                     sum(tr) / max(1, len(tr)), max(tr) if tr else 0))
    print()
