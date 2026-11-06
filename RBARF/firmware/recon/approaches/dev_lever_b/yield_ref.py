#!/usr/bin/env python3
"""Lever B yield of the NORMATIVE reference (embedded_v2.py as shipped)
against the pre-Lever-B behaviour (DW_EN = 0, which is a one-constant
revert), per corpus and per payload."""
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
from harness import linearize                                  # noqa: E402

TRIM = [-0.016, -0.014, -0.012, -0.010, -0.008, -0.006, -0.004]
PLATEAU = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ENVELOPE = [round(-0.08 + i * 0.004, 6) for i in range(41)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_M = {}


def mods(nd):
    if nd not in _M:
        off = dwlib.load_ref()
        off._configure(nd)
        off.DW_EN = 0
        on = dwlib.load_ref()
        on._configure(nd)
        _M[nd] = (off, on)
    return _M[nd]


def one(job):
    nd, tag, pat, data, samples = job
    off, on = mods(nd)
    o0, i0 = off.decode_ex(samples)
    o1, i1 = on.decode_ex(samples)
    return dict(nd=nd, tag=tag, pat=pat,
                b_ok=(o0 == data), b_em=o0 is not None, b_cause=i0["cause"],
                b_path=i0["path"], b_comps=i0.get("comps", 0),
                b_tr=i0.get("trials", 0),
                a_ok=(o1 == data), a_em=o1 is not None, a_cause=i1["cause"],
                a_path=i1["path"], a_comps=i1.get("comps", 0),
                a_tr=i1.get("trials", 0), a_ndw=i1.get("n_dw", 0),
                a_bh=bool(i1.get("budget_hit")),
                b_wrong=(o0 is not None and o0 != data),
                a_wrong=(o1 is not None and o1 != data))


def report(rows, title, per_payload=False):
    print("\n" + "=" * 78)
    print(title + "   n = %d" % len(rows))
    print("=" * 78)
    for tag, k in (("BEFORE (DW_EN=0)", "b"), ("AFTER  (shipped)", "a")):
        ok = sum(1 for r in rows if r[k + "_ok"])
        wr = sum(1 for r in rows if r[k + "_wrong"])
        em = sum(1 for r in rows if r[k + "_em"])
        cz = collections.Counter(r[k + "_cause"] for r in rows
                                 if not r[k + "_em"])
        pz = collections.Counter(r[k + "_path"] for r in rows
                                 if r[k + "_em"])
        print("%s  delivered %5d (%6.2f %%)  emitted %5d  WRONG %d"
              % (tag, ok, 100.0 * ok / max(1, len(rows)), em, wr))
        print("   paths %s" % dict(pz.most_common()))
        print("   refusals %s" % dict(cz.most_common()))
    g = [r for r in rows if r["a_ok"] and not r["b_ok"]]
    l = [r for r in rows if r["b_ok"] and not r["a_ok"]]
    nw = [r for r in rows if r["a_wrong"] and not r["b_wrong"]]
    print("GAINED %d   LOST %d   NEW WRONG %d" % (len(g), len(l), len(nw)))
    if g:
        print("   gained from %s" % dict(collections.Counter(
            r["b_cause"] for r in g).most_common()))
    if l:
        print("   LOST %s" % [(r["pat"], r["b_path"], r["a_cause"])
                              for r in l][:20])
    if nw:
        print("   NEW WRONG %s" % [(r["pat"], r["a_path"], r["a_tr"],
                                   r["a_comps"]) for r in nw][:20])
    for k, tag in (("b", "BEFORE"), ("a", "AFTER ")):
        ch = [r for r in rows if r[k + "_tr"]]
        c = sorted(r[k + "_comps"] for r in ch) or [0]
        print("%s chased %d (%.2f %%)  comps over chased p50 %d p90 %d "
              "p99 %d max %d  (T_MAX 131)"
              % (tag, len(ch), 100.0 * len(ch) / len(rows),
                 c[len(c) // 2], c[int(len(c) * .9)], c[int(len(c) * .99)],
                 c[-1]))
    print("T_MAX exhausted (AFTER): %d (%.3f %%)"
          % (sum(1 for r in rows if r["a_bh"]),
             100.0 * sum(1 for r in rows if r["a_bh"]) / len(rows)))
    nd = sorted(r["a_ndw"] for r in rows)
    print("n_dw: p50 %d p90 %d p99 %d max %d"
          % (nd[len(nd) // 2], nd[int(len(nd) * .9)],
             nd[int(len(nd) * .99)], nd[-1]))
    if per_payload:
        print("per payload  before -> after:")
        for pat in sorted({r["pat"] for r in rows}):
            gg = [r for r in rows if r["pat"] == pat]
            b = sum(1 for r in gg if r["b_ok"])
            aa = sum(1 for r in gg if r["a_ok"])
            w = sum(1 for r in gg if r["a_wrong"])
            print("   %-14s %4d/%4d -> %4d/%4d  %+d%s"
                  % (pat, b, len(gg), aa, len(gg), aa - b,
                     "   WRONG %d" % w if w else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    ap.add_argument("--sets", default="real,trim,plateau")
    a = ap.parse_args()
    import v23lib as L
    sets = a.sets.split(",")
    if "real" in sets:
        jobs = []
        for fn in ("captures_v23.json", "captures_v23_val.json"):
            for c in json.loads((NEWIMPL / "data" / fn).read_text())[
                    "captures"]:
                jobs.append((16, fn, c["pattern"],
                             bytes.fromhex(c["payload"])[:16],
                             linearize(c["capture"])))
        with mp.Pool(a.j) as p:
            rows = p.map(one, jobs, chunksize=4)
        for fn in ("captures_v23.json", "captures_v23_val.json"):
            report([r for r in rows if r["tag"] == fn], "REAL %s" % fn,
                   per_payload=True)
    for nm, pts in (("trim", TRIM), ("plateau", PLATEAU),
                    ("envelope", ENVELOPE)):
        if nm not in sets:
            continue
        jobs = [(48, nm, pat, data, L.linearize(L.capture(data, eps, t0)))
                for pat, data in L.prod_payloads().items()
                for eps in pts for t0 in ARM]
        with mp.Pool(a.j) as p:
            rows = p.map(one, jobs, chunksize=8)
        report(rows, "SYNTH ND=48 %s x arm 70..658 ns" % nm,
               per_payload=True)


if __name__ == "__main__":
    main()
