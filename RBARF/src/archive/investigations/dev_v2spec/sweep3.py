"""Final policy sweep: ordering variants x admission gates, test + prod scale."""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21, e2e_v2 as E                                # noqa: E402

recs = E.gather(sorted(E.TRIM_EPS.values()) + E.ENV_EPS)
EPSL = sorted(set(k[0] for k in recs))
TRIMSET = [round(e, 6) for e in E.TRIM_EPS.values()]


def run(keys, td, tie, N, W, T, ordering, fallback=True):
    c = Counter(); tr = []
    for k in keys:
        rec, truth = recs[k]
        if rec is None or rec[2]:
            c["refuse"] += 1; continue
        bits, mgv, _ = rec
        n0 = sum(1 for v in mgv if v == 0)
        got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=0, WMAX=0, TMAX=1)
        if path == "direct":
            if n0 > td:
                c["refuse"] += 1; continue
            c["ok_direct" if got == truth else "CAT"] += 1; continue
        if n0 > tie:
            c["refuse"] += 1; continue
        got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=N, WMAX=W, TMAX=T,
                                  ordering=ordering, fallback=fallback)
        tr.append(nt)
        if got is None:
            c["refuse"] += 1
        else:
            c["ok_chase" if got == truth else "CAT"] += 1
    return c, tr


def line(tag, c, tr, n):
    ok = c["ok_direct"] + c["ok_chase"]
    print("%-46s n=%4d deliver %4d (%5.1f%%) dir %4d chase %3d refuse %4d "
          "CAT %d  trials mean %5.1f max %3d"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["refuse"], c["CAT"], sum(tr) / max(1, len(tr)),
             max(tr) if tr else 0))


allk = list(recs); trimk = [k for k in recs if k[0] in TRIMSET]
for name, keys in (("8 REAL trim codes |eps|<=4.4%", trimk),
                   ("all eps incl +/-8% corners", allk)):
    print("=== %s (n=%d) ===" % (name, len(keys)))
    for od in ("wmajor", "dfirst"):
        for fb in (True, False):
            for td, tie, N, W, T in ((255, 3, 8, 2, 37), (8, 3, 8, 2, 37),
                                     (8, 3, 8, 3, 93), (8, 4, 8, 2, 37),
                                     (8, 6, 8, 2, 37), (8, 3, 6, 2, 22)):
                c, tr = run(keys, td, tie, N, W, T, od, fb)
                line("%-7s fb=%d  tdir<=%-3d tie<=%d N=%d W<=%d T=%2d"
                     % (od, fb, td, tie, N, W, T), c, tr, len(keys))
    print()

print("=== per eps, FINAL: dfirst, fb=on, tdir<=8, tie<=3, N=8, W<=2, T=37 ===")
for e in EPSL:
    ks = [k for k in recs if k[0] == e]
    c, tr = run(ks, 8, 3, 8, 2, 37, "dfirst")
    line("eps %+7.3f%%" % (e * 100), c, tr, len(ks))
