#!/usr/bin/env python3
"""TASK 1c -- the CEILING.  Given the geometric candidate class
(MID u DEAD), for every R6/R8 refusal: are the wrong bits inside the
top-N of that class ranked by ascending margin, and is their number
within W_MAX?  A frame is REPAIRABLE-IN-PRINCIPLE iff

    nwrong <= W_MAX (2)  and  every wrong bit is in the ranked prefix

which is a necessary condition for any candidate policy built on this
class -- the CRC16 still has to accept, and the enumeration still has to
reach the flip set inside T_MAX.
"""
import argparse
import collections
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import dwlib                                                   # noqa: E402
from geomclass import classify, TRIM_EPS, ARM_T0               # noqa: E402
from harness import linearize                                  # noqa: E402

_E = None
_L = None


def ref(nd):
    global _E, _L
    if _E is None:
        _E = dwlib.load_ref()
        import v23lib
        _L = v23lib
    if _E.N_DATA != nd:
        _E._configure(nd)
    return _E, _L


def one(nd, data, samples):
    e, _ = ref(nd)
    import crc
    tb = e._bits_of(e.HDR + crc.build_payload_v23(data) + e.TRL)
    out, info = e.decode_ex(samples)
    st = dwlib.analyze(e, samples, tb)
    if st is None:
        return None
    cal = e._calibrate(samples, st["K"], st["tau"])
    geom = []                            # (margin, k) for MID/DEAD bits
    for t in range(e.PP_LO, e.PP_HI):
        so = st["seg_of"][t]
        if so is None:
            continue
        (k0, k1, fam, a_hat, u, v) = so
        off = t - k0
        hb = off * e.BIT_U
        cl = classify(u, v, hb + cal.h0f[fam], hb + cal.h1f[fam])
        if cl in ("MID", "DEAD"):
            geom.append((st["marg"][t], t - e.PP_LO))
    geom.sort()
    order = [k for _m, k in geom]
    wrong = [t - e.PP_LO for t in st["wrong"]]
    ranks = [order.index(k) if k in order else -1 for k in wrong]
    return dict(cause=info["cause"], emitted=(out is not None),
                correct=(out == data), nwrong=len(wrong),
                ngeom=len(geom), ranks=ranks,
                nweak=st["n_weak"],
                mgeom=[m for m, _ in geom[:16]])


def job_real(args):
    fn, cap, payload, nd = args
    ref(nd)
    r = one(nd, bytes.fromhex(payload)[:nd], linearize(cap))
    if r:
        r["src"] = fn
    return r


def job_synth(args):
    name, eps, t0, nd = args
    e, L = ref(nd)
    data = (L.prod_payloads() if nd == 48 else L.test_payloads())[name]
    r = one(nd, data, L.linearize(L.capture(data, eps, t0)))
    if r:
        r.update(src="synth", pat=name)
    return r


def report(rows, title):
    rows = [r for r in rows if r]
    print("\n" + "=" * 78)
    print(title + "  (%d locked)" % len(rows))
    print("=" * 78)
    for cause in ("refuse_nocand", "refuse_chase"):
        grp = [r for r in rows if r["cause"] == cause]
        if not grp:
            continue
        print("\n%s: %d frames" % (cause, len(grp)))
        print("  %-6s %8s %8s %8s %8s  %s"
              % ("prefix", "all-in", "%", "&w<=2", "%", "(w<=2 alone: %d)"
                 % sum(1 for r in grp if 0 < r["nwrong"] <= 2)))
        for N in (3, 5, 8, 11, 16, 10 ** 6):
            allin = [r for r in grp
                     if r["nwrong"] and all(0 <= x < N for x in r["ranks"])]
            both = [r for r in allin if r["nwrong"] <= 2]
            print("  %-6s %8d %7.1f%% %8d %7.1f%%"
                  % (("top%d" % N) if N < 1000 else "any", len(allin),
                     100.0 * len(allin) / len(grp), len(both),
                     100.0 * len(both) / len(grp)))
        ng = sorted(r["ngeom"] for r in grp)
        print("  geometric-class size per frame: p50 %d p90 %d max %d"
              % (ng[len(ng) // 2], ng[int(len(ng) * .9)], ng[-1]))
        rk = collections.Counter(x for r in grp for x in r["ranks"])
        print("  wrong-bit rank histogram (-1 = not in the class):",
              dict(sorted(rk.items())[:14]))
    dl = [r for r in rows if r["correct"]]
    if dl:
        ng = sorted(r["ngeom"] for r in dl)
        print("\nDELIVERED frames: geometric-class size p50 %d p90 %d p99 %d"
              " max %d ; frames with >11: %.2f %%"
              % (ng[len(ng) // 2], ng[int(len(ng) * .9)],
                 ng[int(len(ng) * .99)], ng[-1],
                 100.0 * sum(1 for x in ng if x > 11) / len(ng)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    a = ap.parse_args()
    jobs = []
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        d = json.loads((NEWIMPL / "data" / fn).read_text())
        for c in d["captures"]:
            jobs.append((fn, c["capture"], c["payload"], 16))
    with mp.Pool(a.j) as p:
        rows = p.map(job_real, jobs, chunksize=4)
    report(rows, "REAL SILICON v2.3 (ND=16)")
    e, L = ref(48)
    jobs = [(nm, eps, t0, 48) for nm in L.prod_payloads()
            for eps in TRIM_EPS for t0 in ARM_T0]
    with mp.Pool(a.j) as p:
        rows = p.map(job_synth, jobs, chunksize=8)
    report(rows, "SYNTHETIC production sweep (ND=48)")


if __name__ == "__main__":
    main()
