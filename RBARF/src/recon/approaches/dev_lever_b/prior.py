#!/usr/bin/env python3
"""TASK 2c -- is there a usable PRIOR on the geometric class?

The v1 audit (archive/investigations/dev_audit) found a global
"fewer-ones" prior on dead windows (82/18 toward 0) that is WRONG for
some slot families -- family (last-high slot 7, first-low slot 0) was
193 ones vs 33 zeros.  In the v2.3 architecture a candidate is FLIPPED
and CRC-verified, so a prior cannot change which polarity is "guessed";
it can only PRE-SELECT which geometric bits are worth admitting, which
is what reduces trials.  This measures:

  * the truth distribution of GEO bits, globally and per slot family
  * the truth distribution conditioned on the DECODED value -- i.e. how
    often admitting the bit is even useful (decoded != truth)
  * whether restricting admission to one decoded polarity keeps the
    yield while halving the candidate count
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
from harness import linearize                                  # noqa: E402

EPS = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_E = None


def ref(nd):
    global _E
    if _E is None:
        _E = dwlib.load_ref()
    if _E.N_DATA != nd:
        _E._configure(nd)
    return _E


def one(job):
    nd, pat, data, samples = job
    e = ref(nd)
    import crc
    tb = e._bits_of(e.HDR + crc.build_payload_v23(data) + e.TRL)
    st = dwlib.analyze(e, samples, tb)
    if st is None:
        return []
    cal = e._calibrate(samples, st["K"], st["tau"])
    rows = []
    for t in range(e.PP_LO, e.PP_HI):
        so = st["seg_of"][t]
        if so is None:
            continue
        (k0, k1, fam, a_hat, u, v) = so
        off = t - k0
        hb = off * e.BIT_U
        if hb > v:
            continue
        ga = (hb + cal.h0f[fam]) <= u
        gb = v < (hb + cal.h1f[fam])
        if ga != gb:
            continue                              # healthy: not GEO
        m = st["marg"][t]
        rows.append((fam, "MID" if ga else "DEAD", int(m > e.MG_MAX),
                     st["bits"][t], tb[t], min(m, 255), off == 0,
                     k1 - k0))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    a = ap.parse_args()
    import v23lib as L
    jobs = []
    for pat, data in L.prod_payloads().items():
        for eps in EPS:
            for t0 in ARM:
                jobs.append((48, pat, data,
                             L.linearize(L.capture(data, eps, t0))))
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        for c in json.loads((NEWIMPL / "data" / fn).read_text())["captures"]:
            jobs.append((16, c["pattern"], bytes.fromhex(c["payload"])[:16],
                         linearize(c["capture"])))
    with mp.Pool(a.j) as p:
        out = p.map(one, jobs, chunksize=8)
    rows = [r for g in out for r in g]
    print("GEO bits (ga == gb) over %d frames: %d" % (len(jobs), len(rows)))
    for sub in ("MID", "DEAD"):
        g = [r for r in rows if r[1] == sub]
        nw = [r for r in g if r[2]]              # margin > MG_MAX = ADMITTED
        wr = [r for r in g if r[3] != r[4]]
        wrnw = [r for r in nw if r[3] != r[4]]
        print("\n%-5s total %6d   of which margin>MG_MAX (the ADMITTED "
              "pool) %6d" % (sub, len(g), len(nw)))
        if not g:
            continue
        print("      wrong %d (%.2f %%) | wrong among admitted %d (%.2f %%)"
              % (len(wr), 100.0 * len(wr) / len(g), len(wrnw),
                 100.0 * len(wrnw) / max(1, len(nw))))
        print("      truth 1-share %.3f | decoded 1-share %.3f"
              % (sum(r[4] for r in g) / len(g),
                 sum(r[3] for r in g) / len(g)))
        if nw:
            d1 = [r for r in nw if r[3] == 1]
            d0 = [r for r in nw if r[3] == 0]
            print("      ADMITTED, decoded=1: %d, of which wrong %d "
                  "(%.2f %%)" % (len(d1), sum(1 for r in d1 if r[4] != 1),
                                 100.0 * sum(1 for r in d1 if r[4] != 1)
                                 / max(1, len(d1))))
            print("      ADMITTED, decoded=0: %d, of which wrong %d "
                  "(%.2f %%)" % (len(d0), sum(1 for r in d0 if r[4] != 0),
                                 100.0 * sum(1 for r in d0 if r[4] != 0)
                                 / max(1, len(d0))))
    print("\nper-family, ADMITTED pool (margin > MG_MAX), MID+DEAD:")
    print("%-5s %8s %8s %8s %10s %10s" % ("fam", "n", "truth1", "dec1",
                                          "wrong", "P(wrong)"))
    byf = collections.defaultdict(list)
    for r in rows:
        if r[2]:
            byf[r[0]].append(r)
    for fam in sorted(byf):
        g = byf[fam]
        w = sum(1 for r in g if r[3] != r[4])
        print("%-5d %8d %8.3f %8.3f %10d %9.2f%%"
              % (fam, len(g), sum(r[4] for r in g) / len(g),
                 sum(r[3] for r in g) / len(g), w, 100.0 * w / len(g)))
    print("\nADMITTED pool split by decoded value AND family "
          "(the audit's per-family question):")
    print("%-5s %10s %10s %10s %10s" % ("fam", "dec1 n", "dec1 wrong",
                                        "dec0 n", "dec0 wrong"))
    for fam in sorted(byf):
        g = byf[fam]
        d1 = [r for r in g if r[3] == 1]
        d0 = [r for r in g if r[3] == 0]
        print("%-5d %10d %10d %10d %10d"
              % (fam, len(d1), sum(1 for r in d1 if r[4] != 1),
                 len(d0), sum(1 for r in d0 if r[4] != 0)))


if __name__ == "__main__":
    main()
