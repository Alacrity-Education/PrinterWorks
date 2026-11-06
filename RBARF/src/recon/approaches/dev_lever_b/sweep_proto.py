#!/usr/bin/env python3
"""Before/after yield of the LEVER B prototype, per corpus and per
payload, plus the trial/comparison pressure against T_MAX.  Host only."""
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
import proto                                                   # noqa: E402
from harness import linearize                                  # noqa: E402

TRIM_EPS = [-0.016, -0.014, -0.012, -0.010, -0.008, -0.006, -0.004]
PLATEAU = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ARM_T0 = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]

_M = {}
_L = None


def mods(nd, gmax, gcap, aextra):
    global _L
    if _L is None:
        import v23lib
        _L = v23lib
    key = (nd, gmax, gcap, aextra)
    if key not in _M:
        base = dwlib.load_ref()
        base._configure(nd)
        lb = proto.load(nd, g_max=gmax, g_cap=gcap, a_extra=aextra)
        _M[key] = (base, lb)
    return _M[key]


def one(job):
    nd, tag, name, data, samples, gmax, gcap, aextra = job
    base, lb = mods(nd, gmax, gcap, aextra)
    o0, i0 = base.decode_ex(samples)
    o1, i1 = lb.decode_ex(samples)
    return dict(nd=nd, tag=tag, pat=name,
                b_ok=(o0 == data), b_em=(o0 is not None),
                b_cause=i0["cause"], b_path=i0["path"],
                b_comps=i0.get("comps", 0), b_trials=i0.get("trials", 0),
                a_ok=(o1 == data), a_em=(o1 is not None),
                a_cause=i1["cause"], a_path=i1["path"],
                a_comps=i1.get("comps", 0), a_trials=i1.get("trials", 0),
                a_ngeom=i1.get("n_geom", 0), a_budget=i1.get("budget_hit"),
                a_emit_wrong=(o1 is not None and o1 != data),
                b_emit_wrong=(o0 is not None and o0 != data))


def report(rows, title):
    print("\n" + "=" * 78)
    print(title + "   n = %d" % len(rows))
    print("=" * 78)
    for tag, key in (("BEFORE", "b"), ("AFTER ", "a")):
        ok = sum(1 for r in rows if r[key + "_ok"])
        wr = sum(1 for r in rows if r[key + "_emit_wrong"])
        cz = collections.Counter(r[key + "_cause"] for r in rows
                                 if not r[key + "_em"])
        pz = collections.Counter(r[key + "_path"] for r in rows
                                 if r[key + "_em"])
        print("%s delivered %4d (%6.2f %%)  WRONG %d   paths %s"
              % (tag, ok, 100.0 * ok / max(1, len(rows)), wr,
                 dict(pz.most_common())))
        print("        refusals %s" % dict(cz.most_common()))
    gained = [r for r in rows if r["a_ok"] and not r["b_ok"]]
    lost = [r for r in rows if r["b_ok"] and not r["a_ok"]]
    newwrong = [r for r in rows if r["a_emit_wrong"] and not r["b_emit_wrong"]]
    print("GAINED %d   LOST %d   NEW WRONG %d" % (len(gained), len(lost),
                                                  len(newwrong)))
    if gained:
        print("  gained from:", dict(collections.Counter(
            r["b_cause"] for r in gained).most_common()))
        print("  gained per payload:", dict(collections.Counter(
            r["pat"] for r in gained).most_common()))
    if lost:
        print("  LOST detail:", [(r["pat"], r["b_path"], r["a_cause"])
                                 for r in lost][:20])
    if newwrong:
        print("  NEW WRONG detail:", [(r["pat"], r["a_path"], r["a_trials"],
                                       r["a_comps"]) for r in newwrong][:20])
    for key, tag in (("b", "BEFORE"), ("a", "AFTER ")):
        c = sorted(r[key + "_comps"] for r in rows)
        t = sorted(r[key + "_trials"] for r in rows)
        ch = [r for r in rows if r[key + "_trials"]]
        cc = sorted(r[key + "_comps"] for r in ch)
        print("%s comps p50 %d p90 %d p99 %d max %d | trials max %d | "
              "chased %d (%.1f %%)%s"
              % (tag, c[len(c) // 2], c[int(len(c) * .9)],
                 c[int(len(c) * .99)], c[-1], t[-1], len(ch),
                 100.0 * len(ch) / len(rows),
                 ("  chased-comps p50 %d p90 %d max %d"
                  % (cc[len(cc) // 2], cc[int(len(cc) * .9)], cc[-1]))
                 if cc else ""))
    bh = [r for r in rows if r["a_budget"]]
    print("T_MAX budget exhausted (AFTER): %d frames (%.2f %%)"
          % (len(bh), 100.0 * len(bh) / len(rows)))
    ng = sorted(r["a_ngeom"] for r in rows)
    print("n_geom: p50 %d p90 %d p99 %d max %d" % (
        ng[len(ng) // 2], ng[int(len(ng) * .9)], ng[int(len(ng) * .99)],
        ng[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    ap.add_argument("--gmax", type=int, default=8)
    ap.add_argument("--gcap", type=int, default=24)
    ap.add_argument("--aextra", type=int, default=0)
    ap.add_argument("--sets", default="real,trim,plateau")
    a = ap.parse_args()
    sets = a.sets.split(",")
    import v23lib as L
    if "real" in sets:
        jobs = []
        for fn in ("captures_v23.json", "captures_v23_val.json"):
            d = json.loads((NEWIMPL / "data" / fn).read_text())
            for c in d["captures"]:
                jobs.append((16, fn, c["pattern"],
                             bytes.fromhex(c["payload"])[:16],
                             linearize(c["capture"]), a.gmax, a.gcap,
                             a.aextra))
        with mp.Pool(a.j) as p:
            rows = p.map(one, jobs, chunksize=4)
        report([r for r in rows if r["tag"] == "captures_v23.json"],
               "REAL captures_v23.json (ND=16)")
        report([r for r in rows if r["tag"] == "captures_v23_val.json"],
               "REAL captures_v23_val.json (ND=16)")
    for nm, eps_pts in (("trim", TRIM_EPS), ("plateau", PLATEAU)):
        if nm not in sets:
            continue
        jobs = []
        for pat, data in L.prod_payloads().items():
            for eps in eps_pts:
                for t0 in ARM_T0:
                    jobs.append((48, nm, pat, data,
                                 L.linearize(L.capture(data, eps, t0)),
                                 a.gmax, a.gcap, a.aextra))
        with mp.Pool(a.j) as p:
            rows = p.map(one, jobs, chunksize=8)
        report(rows, "SYNTH ND=48 %s band x arm 70..658 ns" % nm)
        print("\nper-payload delivered before -> after:")
        for pat in L.prod_payloads():
            g = [r for r in rows if r["pat"] == pat]
            b = sum(1 for r in g if r["b_ok"])
            aa = sum(1 for r in g if r["a_ok"])
            w = sum(1 for r in g if r["a_emit_wrong"])
            print("  %-12s %3d/%3d -> %3d/%3d   %+d%s"
                  % (pat, b, len(g), aa, len(g), aa - b,
                     ("   WRONG %d" % w) if w else ""))


if __name__ == "__main__":
    main()
