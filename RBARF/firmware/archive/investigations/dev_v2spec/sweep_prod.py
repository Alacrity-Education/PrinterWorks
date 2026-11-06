"""Find the catastrophic-zero frontier at production scale (472-bit frame)."""
import sys, pathlib, itertools
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21                                             # noqa: E402
import prod_e2e as P                                   # noqa: E402

recs = P.recs
ND = 48
STRONG = [round(e, 6) for e in (-0.025, -0.02248, -0.01072, -0.01, 0.0,
                                0.00022, 0.01, 0.01274)]


def policy(rec, truth, td, mg, N, W, T):
    """Admission: emit-gate on ties; candidates = bits with mgv <= mg."""
    if rec is None or rec[2]:
        return "refuse", 0
    bits, mgv, _ = rec
    n0 = sum(1 for v in mgv if v == 0)
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
    if path == "direct":
        if n0 > td:
            return "refuse", 0
        return ("ok_direct" if got == truth else "CAT"), 0
    nlow = sum(1 for v in mgv if v <= mg)
    if nlow == 0 or nlow > N:
        # nlow > N: too many weak bits to enumerate honestly -> refuse
        return "refuse", 0
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W, TMAX=T,
                              ordering="dfirst", fallback=False)
    if got is None:
        return "refuse", nt
    return ("ok_chase" if got == truth else "CAT"), nt


def run(keys, td, mg, N, W, T):
    c, tr = Counter(), []
    for k in keys:
        rec, truth = recs[k]
        o, nt = policy(rec, truth, td, mg, N, W, T)
        c[o] += 1
        if nt:
            tr.append(nt)
    return c, tr


def line(tag, c, tr, n):
    ok = c["ok_direct"] + c["ok_chase"]
    print("%-38s n=%4d deliver %4d (%5.1f%%) dir %4d chase %3d refuse %4d "
          "CAT %2d  chases %3d trials mean %5.1f max %2d"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["refuse"], c["CAT"], len(tr), sum(tr) / max(1, len(tr)),
             max(tr) if tr else 0))


allk = list(recs)
sk = [k for k in recs if k[0] in STRONG]
for label, keys in (("ALL eps (n=%d)" % len(allk), allk),
                    ("STRONG band -2.5..+1.3%% (n=%d)" % len(sk), sk)):
    print("=== %s ===" % label)
    for mg in (0, 2, 4, 8, 16, 255):
        for N, W, T in ((4, 1, 5), (4, 2, 11), (6, 2, 22), (8, 2, 37),
                        (8, 1, 9)):
            c, tr = run(keys, 8, mg, N, W, T)
            line("mgv<=%-3d N<=%d W<=%d T=%2d" % (mg, N, W, T), c, tr, len(keys))
    c, tr = run(keys, 8, -1, 0, 0, 1)
    line("chase DISABLED", c, tr, len(keys))
    print()
