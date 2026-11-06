#!/usr/bin/env python3
"""THE v2.3 WRONG-EMISSION RATE, at the SHIPPED constants.

No parameter overrides: this runs recon/approaches/embedded_v2.py exactly
as _configure(nd) leaves it, which is what decode.c and the target image
compile.  Reports accepted emissions, wrong emissions, the rate, and a
one-sided 95 % Clopper-Pearson upper bound, against the <= 0.2 % target.

Corpus (both geometries, 27 production payloads / 30 bench payloads):
  plateau  eps -2.5 .. +0.1 %  at 0.05 %   -- where deliveries live
  fast     eps  0.0 .. +3.0 %  at 0.05 %   -- where BOTH recorded
                                              catastrophics happened
  envelope eps -8   .. +8   %  at 0.2 %    -- the whole HSI envelope
x 12 arm phases over the MEASURED 375-736 ns spread.
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
import sys
from math import comb
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import v23lib as L                                              # noqa: E402
from relax_ladder import PAY as PROD                            # noqa: E402

# 12 arm phases over the MEASURED t0 spread.  Defaults are the OLD arm's
# 375..736 ns (PROD_CLOSURE SS14.3); the front-end phase re-runs this over
# the NEW arm's measured 102..650 ns (--t0-lo/--t0-hi).
T0_LO, T0_HI = 375.0, 736.0
def _t0():
    return [T0_LO + i * (T0_HI - T0_LO) / 11 for i in range(12)]
T0 = _t0()
SETS = {
    "plateau": [round(-0.025 + i * 0.0005, 6) for i in range(53)],
    "fast":    [round(i * 0.0005, 6) for i in range(61)],
    "envelope": [round(-0.08 + i * 0.002, 6) for i in range(81)],
}
_EV = None
_PAY = {}


def payloads(nd):
    if nd not in _PAY:
        _PAY[nd] = dict(PROD) if nd == 48 else L.test_payloads()
    return _PAY[nd]


def one(job):
    # dw_en travels IN THE JOB: Python 3.14 starts pool workers with
    # forkserver, so a module global set in main() does not reach them.
    nd, st, name, eps, t0, dw_en = job
    global _EV
    if _EV is None:
        _EV = L.load_ref()
    e = _EV
    e._configure(nd)                    # SHIPPED constants, no overrides
    if dw_en is not None:               # SS6.4 A/B only; default = shipped
        e.DW_EN = dw_en
    data = payloads(nd)[name]
    try:
        out, info = e.decode_ex(L.linearize(L.capture(data, eps, t0)))
    except AssertionError as exc:
        return (nd, st, name, eps, t0, "assert", 0, 0, 0, 0, 0, "",
                str(exc)[:40])
    em = out is not None
    ok = em and out == data
    return (nd, st, name, eps, t0, info["cause"] or ("ok" if ok else "WRONG"),
            int(em), int(ok), info.get("trials", 0), info.get("comps", 0),
            info.get("n_refs", 0),
            "chase" if info.get("path") == "chase" else
            ("direct" if info.get("path") == "direct" else ""),
            out.hex() if (em and not ok) else "")


def upper95(k, n):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        m = (lo + hi) / 2
        p = sum(comb(n, i) * m ** i * (1 - m) ** (n - i) for i in range(k + 1))
        if p > 0.05:
            lo = m
        else:
            hi = m
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=23)
    ap.add_argument("--nd", default="48,16")
    ap.add_argument("--out", default=str(SC / "wrong_emission_final.jsonl.gz"))
    ap.add_argument("--t0-lo", type=float, default=None)
    ap.add_argument("--t0-hi", type=float, default=None)
    ap.add_argument("--dw-en", type=int, default=None,
                    help="SS6.4 dead-window candidates: 0 = off (the "
                         "pre-Lever-B behaviour), 1 = on.  Default = "
                         "whatever _configure() ships.")
    a = ap.parse_args()
    global T0, T0_LO, T0_HI
    if a.t0_lo is not None:
        T0_LO = a.t0_lo
    if a.t0_hi is not None:
        T0_HI = a.t0_hi
    T0 = _t0()
    print("arm phases (ns): %s" % ["%.0f" % t for t in T0])
    jobs = []
    for nd in [int(x) for x in a.nd.split(",")]:
        for st, eps_pts in SETS.items():
            for nm in payloads(nd):
                for eps in eps_pts:
                    for t0 in T0:
                        jobs.append((nd, st, nm, eps, t0, a.dw_en))
    print("%d decodes at the SHIPPED constants" % len(jobs))
    with mp.Pool(a.j) as pool:
        rows = pool.map(one, jobs, chunksize=256)
    with gzip.open(a.out, "wt") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        for k in ((r[0], r[1]), (r[0], "ALL"), ("BOTH", "ALL")):
            agg[k][0] += 1
            agg[k][1] += r[6]
            agg[k][2] += r[7]
            agg[k][3] += r[6] - r[7]
    print("%-6s %-9s %9s %9s %9s %7s %9s %s"
          % ("ND", "set", "decodes", "emitted", "correct", "WRONG",
             "wrong%", "95% upper"))
    for k in sorted(agg, key=lambda x: (str(x[0]), x[1])):
        n, em, ok, wr = agg[k]
        ub = 100 * upper95(wr, em) if em else 0.0
        print("%-6s %-9s %9d %9d %9d %7d %8.4f%%  <= %.4f%%"
              % (k[0], k[1], n, em, ok, wr,
                 100.0 * wr / em if em else 0.0, ub))
    ch = [r for r in rows if r[11] == "chase"]
    print("\nchase-repaired emissions: %d of %d (%.1f %%)"
          % (len(ch), agg[("BOTH", "ALL")][1],
             100.0 * len(ch) / max(1, agg[("BOTH", "ALL")][1])))
    for f in (8, 9, 10):
        v = sorted(r[f] for r in rows if r[6])
        nm = {8: "trials", 9: "comps", 10: "n_refs"}[f]
        print("  %-7s over emissions: p50 %d  p90 %d  p99 %d  max %d"
              % (nm, v[len(v) // 2], v[int(len(v) * .9)],
                 v[int(len(v) * .99)], v[-1]))
    v = sorted(r[9] for r in rows if r[8])
    if v:
        print("  comps over CHASED frames: p50 %d p90 %d max %d"
              % (v[len(v) // 2], v[int(len(v) * .9)], v[-1]))
    print("\nWRONG EMISSIONS:")
    for r in rows:
        if r[6] and not r[7]:
            print("  ND=%d %s %s eps=%+.4f t0=%.1f trials=%d comps=%d "
                  "refs=%d" % (r[0], r[1], r[2], r[3] * 100, r[4], r[8],
                               r[9], r[10]))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
