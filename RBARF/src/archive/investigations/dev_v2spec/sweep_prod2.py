"""Where do the production-scale catastrophics live, and what kills them?"""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21, pickle                                     # noqa: E402
recs = pickle.load(pathlib.Path(__file__).with_name("prod_cache.pkl").open("rb"))
ND = 48
EPSL = sorted(set(k[0] for k in recs))


def policy(rec, truth, td, mg, N, W, T, verbose=None):
    if rec is None or rec[2]:
        return "refuse", 0
    bits, mgv, _ = rec
    n0 = sum(1 for v in mgv if v == 0)
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
    if path == "direct":
        if n0 > td:
            return "refuse", 0
        if got != truth and verbose is not None:
            verbose.append(("DIRECT", n0))
        return ("ok_direct" if got == truth else "CAT"), 0
    if n0 > td:
        return "refuse", 0
    nlow = sum(1 for v in mgv if v <= mg)
    if nlow == 0 or nlow > N:
        return "refuse", 0
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W, TMAX=T,
                              ordering="dfirst", fallback=False)
    if got is None:
        return "refuse", nt
    if got != truth and verbose is not None:
        eb = [(b >> (7 - j)) & 1 for b in truth for j in range(8)]
        nw = sum(1 for i in range(ND * 8) if bits[i] != eb[i])
        verbose.append(("CHASE", n0, nlow, nt, nw))
    return ("ok_chase" if got == truth else "CAT"), nt


def run(keys, td, mg, N, W, T, v=None):
    c = Counter()
    for k in keys:
        o, nt = policy(*recs[k], td, mg, N, W, T, v)
        c[o] += 1
    return c


allk = list(recs)
print("=== emit-gate (tie count over 408 payload' bits) sweep, "
      "chase mgv<=8 N<=4 W<=2 T=11 ===")
for td in (408, 40, 24, 16, 12, 8, 6, 4, 2):
    c = run(allk, td, 8, 4, 2, 11)
    ok = c["ok_direct"] + c["ok_chase"]
    print("  n_tied<=%-3d deliver %4d (%5.1f%%) dir %4d chase %3d  CAT %d"
          % (td, ok, 100.0 * ok / len(allk), c["ok_direct"], c["ok_chase"],
             c["CAT"]))
print("\n=== same, chase mgv<=0 N<=4 W<=2 T=11 ===")
for td in (408, 24, 16, 12, 8, 4):
    c = run(allk, td, 0, 4, 2, 11)
    ok = c["ok_direct"] + c["ok_chase"]
    print("  n_tied<=%-3d deliver %4d (%5.1f%%) dir %4d chase %3d  CAT %d"
          % (td, ok, 100.0 * ok / len(allk), c["ok_direct"], c["ok_chase"],
             c["CAT"]))
print("\n=== CAT anatomy at n_tied<=8, mgv<=8, N<=4, W<=2, T=11, per eps ===")
tot = Counter()
for e in EPSL:
    ks = [k for k in recs if k[0] == e]
    v = []
    c = run(ks, 8, 8, 4, 2, 11, v)
    tot.update(c)
    ok = c["ok_direct"] + c["ok_chase"]
    print("  eps %+7.3f%%  n=%3d deliver %3d (%5.1f%%) dir %3d chase %2d "
          "refuse %3d  CAT %d %s"
          % (e * 100, len(ks), ok, 100.0 * ok / len(ks), c["ok_direct"],
             c["ok_chase"], c["refuse"], c["CAT"], v if v else ""))
ok = tot["ok_direct"] + tot["ok_chase"]
print("  TOTAL n=%d deliver %d (%.1f%%) CAT %d" % (len(allk), ok,
                                                   100.0 * ok / len(allk),
                                                   tot["CAT"]))
