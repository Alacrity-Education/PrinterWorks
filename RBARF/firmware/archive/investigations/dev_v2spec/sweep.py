"""Chase-admission sweep: find (tie gate, N_CAND, W, T) that keeps
catastrophics at 0 while maximising single-shot delivery."""
import sys, pathlib, pickle, itertools
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21                                            # noqa: E402
import e2e_v2 as E                                    # noqa: E402

STRONG = [-0.02248, -0.01072, 0.00022, 0.01274]       # trim codes 1,0,7,6
recs = E.gather(sorted(E.TRIM_EPS.values()))
KEYS = list(recs.keys())


def run(tie_max, N_CAND, W, T, mgv_max=255, keys=None):
    c = Counter()
    keys = keys or KEYS
    for k in keys:
        rec, truth = recs[k]
        if rec is None or rec[2]:
            c["refuse"] += 1; continue
        bits, mgv, _ = rec
        got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=0, WMAX=0, TMAX=1)
        if path == "direct":
            (c.__setitem__("ok_direct", c["ok_direct"] + 1) if got == truth
             else c.__setitem__("CAT_direct", c["CAT_direct"] + 1))
            continue
        n0 = sum(1 for v in mgv if v == 0)
        if n0 > tie_max:
            c["refuse_gate"] += 1; continue
        nc = min(N_CAND, sum(1 for v in mgv if v <= mgv_max))
        got, nt, path = v21.chase(bits, mgv, E.ND, N_CAND=nc, WMAX=W, TMAX=T)
        if got is None:
            c["refuse"] += 1
        elif got == truth:
            c["ok_chase"] += 1
        else:
            c["CAT_chase"] += 1
    return c


def line(tag, c, n):
    ok = c["ok_direct"] + c["ok_chase"]
    cat = c["CAT_direct"] + c["CAT_chase"]
    print("%-40s n=%3d deliver %3d (%5.1f%%) [dir %3d + chase %3d]  "
          "refuse %3d (tiegate %3d)  CATASTROPHIC %d (dir %d)"
          % (tag, n, ok, 100.0 * ok / n, c["ok_direct"], c["ok_chase"],
             c["refuse"] + c["refuse_gate"], c["refuse_gate"], cat,
             c["CAT_direct"]))


sk = [k for k in KEYS if k[0] in [round(e, 6) for e in STRONG]]
print("=== ALL 8 trim codes (n=%d) ===" % len(KEYS))
for tie in (256, 6, 5, 4, 3, 2, 1, 0):
    for N, W, T in ((8, 3, 93), (8, 2, 37), (4, 2, 11)):
        line("tie<=%-3d N=%d W<=%d T=%2d" % (tie, N, W, T),
             run(tie, N, W, T), len(KEYS))
print("\n=== STRONG band only, trim {1,0,7,6} = eps -2.2..+1.3%% (n=%d) ==="
      % len(sk))
for tie in (256, 6, 4, 3, 2, 1, 0):
    for N, W, T in ((8, 3, 93), (8, 2, 37), (4, 2, 11)):
        line("tie<=%-3d N=%d W<=%d T=%2d" % (tie, N, W, T),
             run(tie, N, W, T, keys=sk), len(sk))
print("\n=== margin-cap variants (tie<=3, N=8) ===")
for mm in (255, 64, 32, 16, 8):
    for W, T in ((3, 93), (2, 37)):
        line("mgv<=%-3d W<=%d T=%2d ALL" % (mm, W, T),
             run(3, 8, W, T, mgv_max=mm), len(KEYS))
