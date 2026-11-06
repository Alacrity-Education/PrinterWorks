"""FINAL budget-justification table: admission cap x weight cap, both scales,
alias guard on.  This is the table the spec quotes."""
import sys, pathlib, pickle
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21                                             # noqa: E402
D = pathlib.Path(__file__).parent
PROD = pickle.load((D / "prod_cache.pkl").open("rb"))
TEST = pickle.load((D / "e2e_cache.pkl").open("rb"))
STRONG = [round(e, 6) for e in (-0.025, -0.02248, -0.01072, -0.01, 0.0,
                                0.00022, 0.01, 0.01274)]


def run(recs, ND, td, mg, NAD, W, guard, keys=None):
    c = Counter(); tr = []
    for k in (keys or recs):
        rec, truth = recs[k]
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
        if nlow == 0 or nlow > NAD:
            c["refuse"] += 1; continue
        T = 1 + nlow + (nlow * (nlow - 1) // 2 if W >= 2 else 0)
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W, TMAX=T,
                                  ordering="dfirst", fallback=False,
                                  guard=guard)
        tr.append(nt)
        if got is None:
            c["refuse"] += 1
        else:
            c["ok_chase" if got == truth else "CAT"] += 1
    return c, tr


def show(label, recs, ND):
    sk = [k for k in recs if k[0] in STRONG]
    print("=== %s (n=%d, strong band n=%d) ===" % (label, len(recs), len(sk)))
    print("  %-28s %-34s %s" % ("", "ALL eps -8..+8%", "STRONG -2.5..+1.3%"))
    for NAD in (2, 3, 4, 5, 6, 8):
        for W in (1, 2):
            row = []
            for keys in (None, sk):
                c, tr = run(recs, ND, 8, 8, NAD, W, "alias", keys)
                n = len(keys or recs)
                ok = c["ok_direct"] + c["ok_chase"]
                row.append("deliver %4d (%5.1f%%) +chase %3d CAT %d"
                           % (ok, 100.0 * ok / n, c["ok_chase"], c["CAT"]))
            Tmax = 1 + NAD + (NAD * (NAD - 1) // 2 if W >= 2 else 0)
            print("  admit<=%d W<=%d Tmax=%-3d %-34s %s"
                  % (NAD, W, Tmax, row[0], row[1]))
    for keys in (None, sk):
        c, tr = run(recs, ND, 8, -1, 0, 0, "none", keys)
        n = len(keys or recs)
        ok = c["ok_direct"] + c["ok_chase"]
        print("  chase OFF          %s deliver %4d (%5.1f%%) CAT %d"
              % ("ALL " if keys is None else "STRONG", ok, 100.0 * ok / n,
                 c["CAT"]))
    print()


show("PRODUCTION 48 B data / 472-bit frame", PROD, 48)
show("TEST 16 B data / 216-bit frame", TEST, 16)
