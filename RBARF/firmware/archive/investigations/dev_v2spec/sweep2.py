"""Fine sweep around the operating point + per-eps table + envelope."""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21, e2e_v2 as E                                # noqa: E402

ALL_EPS = sorted(set([round(e, 6) for e in E.TRIM_EPS.values()]
                     + [round(e, 6) for e in E.ENV_EPS]))
recs = E.gather(sorted(E.TRIM_EPS.values()) + E.ENV_EPS)


def policy(rec, truth, tie_max, N, W, T):
    if rec is None or rec[2]:
        return "refuse", 0
    bits, mgv, _ = rec
    got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=0, WMAX=0, TMAX=1)
    if path == "direct":
        return ("ok_direct" if got == truth else "CAT_direct"), 0
    if sum(1 for v in mgv if v == 0) > tie_max:
        return "refuse", 0
    got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=N, WMAX=W, TMAX=T)
    if got is None:
        return "refuse", nt
    return ("ok_chase" if got == truth else "CAT_chase"), nt


def run(keys, tie, N, W, T):
    c, tr = Counter(), []
    for k in keys:
        rec, truth = recs[k]
        o, nt = policy(rec, truth, tie, N, W, T)
        c[o] += 1; tr.append(nt)
    return c, tr


def line(tag, c, tr, n):
    ok = c["ok_direct"] + c["ok_chase"]; cat = c["CAT_direct"] + c["CAT_chase"]
    print("%-30s n=%3d deliver %3d (%5.1f%%) dir %3d chase %2d  refuse %3d"
          "  CAT %d  trials mean %5.1f max %3d"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["refuse"], cat, sum(tr) / len(tr), max(tr)))


trimk = [k for k in recs if k[0] in [round(e, 6) for e in E.TRIM_EPS.values()]]
print("=== fine sweep over the 8 REAL trim codes (n=%d) ===" % len(trimk))
for tie in (2, 3, 4):
    for N, W, T in ((4, 2, 11), (6, 2, 22), (8, 2, 37), (8, 3, 93),
                    (10, 2, 56), (12, 2, 79)):
        c, tr = run(trimk, tie, N, W, T)
        line("tie<=%d N=%2d W<=%d T=%2d" % (tie, N, W, T), c, tr, len(trimk))

print("\n=== chosen policy tie<=3 N=8 W<=2 T=37: per eps ===")
for e in ALL_EPS:
    ks = [k for k in recs if k[0] == e]
    if not ks:
        continue
    c, tr = run(ks, 3, 8, 2, 37)
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))

print("\n=== same, W<=3 T=93 ===")
for e in ALL_EPS:
    ks = [k for k in recs if k[0] == e]
    if not ks:
        continue
    c, tr = run(ks, 3, 8, 3, 93)
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))

print("\n=== direct-only baseline (chase disabled) per eps ===")
for e in ALL_EPS:
    ks = [k for k in recs if k[0] == e]
    if not ks:
        continue
    c, tr = run(ks, -1, 0, 0, 1)
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))
