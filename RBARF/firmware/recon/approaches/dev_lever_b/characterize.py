#!/usr/bin/env python3
"""TASK 1 -- how much of R6/R8 is DEAD WINDOW?  Host only, no bench.

For every REFUSED frame in
  * data/captures_v23.json + captures_v23_val.json  (real silicon, ND=16)
  * a synthetic sweep on the 10 production payloads (ND=48) over the
    MEASURED arm range 70..658 ns and eps inside the trim band
report: how many payload' bits are wrong, what their margins were, and
whether each wrong bit's DISCRIMINATING INTERVAL received a sample.

The headline number is the fraction of R6/R8 refusals whose wrong bits
are ALL dead-window bits -- that is the ceiling on what Lever B can
recover, and it is stated BEFORE anything is implemented.
"""
import argparse
import collections
import json
import multiprocessing as mp
import statistics
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))

import dwlib                                                   # noqa: E402
from harness import linearize                                  # noqa: E402

TRIM_EPS = [-0.016, -0.014, -0.012, -0.010, -0.008, -0.006, -0.004]
ARM_T0 = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]

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


def truth_bits(e, data):
    import crc
    if e.CHK_LEN == 6:
        pp = crc.build_payload_v23(data)
    else:
        raise SystemExit("only v2.3 geometry characterized")
    return e._bits_of(e.HDR + pp + e.TRL)


def one(nd, data, samples):
    e, _ = ref(nd)
    tb = truth_bits(e, data)
    out, info = e.decode_ex(samples)
    st = dwlib.analyze(e, samples, tb)
    r = dict(cause=info["cause"], path=info["path"],
             n_weak=int(info.get("n_weak", 0) or 0),
             trials=info.get("trials", 0), comps=info.get("comps", 0),
             emitted=(out is not None), correct=(out == data))
    if st is None:
        r.update(nwrong=None)
        return r
    r["n_weak"] = st["n_weak"]
    r["n_tied"] = st["n_tied"]
    r["n_seg"] = st["n_seg"]
    wrong = st["wrong"]
    r["nwrong"] = len(wrong)
    r["viol"] = len(st["wrong_mk"])
    det = []
    for t in wrong:
        det.append(dict(t=t, m=st["marg"][t], br=bool(st["dead_br"][t]),
                        cen=bool(t in st["dead_cen"]),
                        seg=st["seg_of"][t]))
    r["wrongdet"] = det
    r["all_br"] = bool(det) and all(d["br"] for d in det)
    r["any_br"] = any(d["br"] for d in det)
    r["all_cen"] = bool(det) and all(d["cen"] for d in det)
    r["any_cen"] = any(d["cen"] for d in det)
    r["n_dead_br_pp"] = sum(1 for t in range(e.PP_LO, e.PP_HI)
                            if st["dead_br"][t])
    r["n_dead_cen_pp"] = sum(1 for t in range(e.PP_LO, e.PP_HI)
                             if t in st["dead_cen"])
    # agreement of detector A vs detector B over ALL payload' bits
    a = [bool(st["dead_br"][t]) for t in range(e.PP_LO, e.PP_HI)]
    b = [bool(t in st["dead_cen"]) for t in range(e.PP_LO, e.PP_HI)]
    r["agree"] = [sum(1 for x, y in zip(a, b) if x and y),
                  sum(1 for x, y in zip(a, b) if x and not y),
                  sum(1 for x, y in zip(a, b) if (not x) and y),
                  sum(1 for x, y in zip(a, b) if (not x) and (not y))]
    return r


def job_real(args):
    fn, cap, payload, nd = args
    e, _ = ref(nd)
    data = bytes.fromhex(payload)[:nd]
    r = one(nd, data, linearize(cap))
    r["src"] = fn
    r["pat"] = None
    return r


def job_synth(args):
    name, eps, t0, nd = args
    e, L = ref(nd)
    data = (L.prod_payloads() if nd == 48 else L.test_payloads())[name]
    r = one(nd, data, L.linearize(L.capture(data, eps, t0)))
    r["src"] = "synth"
    r["pat"] = name
    r["eps"] = eps
    r["t0"] = t0
    return r


def summarize(rows, title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    n = len(rows)
    em = [r for r in rows if r["emitted"]]
    ok = [r for r in em if r["correct"]]
    wr = [r for r in em if not r["correct"]]
    refused = [r for r in rows if not r["emitted"]]
    print("frames %d | delivered %d (%.2f %%) | WRONG %d | refused %d"
          % (n, len(ok), 100.0 * len(ok) / max(1, n), len(wr), len(refused)))
    cz = collections.Counter(r["cause"] for r in refused)
    print("refusal causes:", dict(cz.most_common()))
    for cause in ("refuse_nocand", "refuse_chase", "refuse_admit"):
        grp = [r for r in refused if r["cause"] == cause]
        if not grp:
            continue
        with_det = [r for r in grp if r.get("nwrong") is not None]
        nw = [r["nwrong"] for r in with_det]
        clean = [r for r in with_det if r["nwrong"] == 0]
        bad = [r for r in with_det if r["nwrong"] > 0]
        print("\n-- %s : %d frames" % (cause, len(grp)))
        if nw:
            print("   wrong payload' bits: mean %.2f  median %d  max %d  "
                  "(0 wrong: %d frames -- the CHECK block was the damage)"
                  % (statistics.mean(nw), statistics.median(nw), max(nw),
                     len(clean)))
        if not bad:
            continue
        allbr = [r for r in bad if r["all_br"]]
        anybr = [r for r in bad if r["any_br"]]
        allcen = [r for r in bad if r["all_cen"]]
        anycen = [r for r in bad if r["any_cen"]]
        print("   frames with >=1 wrong DATA/CHECK bit: %d" % len(bad))
        print("   ALL wrong bits dead-window (bracket rule A): %d "
              "(%.1f %%)   ANY: %d (%.1f %%)"
              % (len(allbr), 100.0 * len(allbr) / len(bad),
                 len(anybr), 100.0 * len(anybr) / len(bad)))
        print("   ALL wrong bits dead-window (sample census B): %d "
              "(%.1f %%)   ANY: %d (%.1f %%)"
              % (len(allcen), 100.0 * len(allcen) / len(bad),
                 len(anycen), 100.0 * len(anycen) / len(bad)))
        mg = [d["m"] for r in bad for d in r["wrongdet"]]
        mgd = [d["m"] for r in bad for d in r["wrongdet"] if d["br"]]
        mgl = [d["m"] for r in bad for d in r["wrongdet"] if not d["br"]]
        if mg:
            print("   wrong-bit margins (TU): n=%d  min %d  p50 %d  p90 %d"
                  "  max %d   <=MG_MAX(8): %d (%.1f %%)"
                  % (len(mg), min(mg), int(statistics.median(mg)),
                     sorted(mg)[int(len(mg) * .9)], max(mg),
                     sum(1 for x in mg if x <= 8),
                     100.0 * sum(1 for x in mg if x <= 8) / len(mg)))
        if mgd:
            print("     dead-window wrong bits  : n=%d  p50 %d  max %d"
                  % (len(mgd), int(statistics.median(mgd)), max(mgd)))
        if mgl:
            print("     live-window  wrong bits : n=%d  p50 %d  max %d"
                  % (len(mgl), int(statistics.median(mgl)), max(mgl)))
        dbr = [r["n_dead_br_pp"] for r in bad]
        print("   dead-window bits per frame (all payload'): p50 %d  max %d"
              % (int(statistics.median(dbr)), max(dbr)))
    det = [r for r in rows if r.get("agree")]
    if det:
        ag = [sum(x) for x in zip(*[r["agree"] for r in det])]
        tot = sum(ag)
        print("\ndetector A (bracket) vs B (sample census) over %d payload'"
              " bits: both %d | A-only %d | B-only %d | neither %d"
              % (tot, ag[0], ag[1], ag[2], ag[3]))
        print("  A precision vs B: %.4f    A recall vs B: %.4f"
              % (ag[0] / max(1, ag[0] + ag[1]), ag[0] / max(1, ag[0] + ag[2])))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=23)
    ap.add_argument("--skip-real", action="store_true")
    ap.add_argument("--skip-synth", action="store_true")
    ap.add_argument("--out", default=str(SC / "task1.jsonl"))
    a = ap.parse_args()
    allrows = []
    if not a.skip_real:
        jobs = []
        for fn in ("captures_v23.json", "captures_v23_val.json"):
            d = json.loads((NEWIMPL / "data" / fn).read_text())
            for c in d["captures"]:
                jobs.append((fn, c["capture"], c["payload"], 16))
        with mp.Pool(a.j) as p:
            rows = p.map(job_real, jobs, chunksize=4)
        allrows += summarize(rows, "REAL SILICON v2.3 corpora (ND=16), "
                             "%d captures" % len(rows))
    if not a.skip_synth:
        e, L = ref(48)
        names = list(L.prod_payloads())
        jobs = [(nm, eps, t0, 48) for nm in names for eps in TRIM_EPS
                for t0 in ARM_T0]
        with mp.Pool(a.j) as p:
            rows = p.map(job_synth, jobs, chunksize=8)
        allrows += summarize(
            rows, "SYNTHETIC production sweep (ND=48): 10 payloads x "
            "%d eps (trim band) x %d arm phases (70..658 ns) = %d"
            % (len(TRIM_EPS), len(ARM_T0), len(jobs)))
        print("\nper-payload refusal breakdown (synthetic):")
        per = collections.defaultdict(collections.Counter)
        for r in rows:
            per[r["pat"]][r["cause"] or ("ok" if r["correct"] else "WRONG")] \
                += 1
        for nm in names:
            print("  %-10s %s" % (nm, dict(per[nm].most_common())))
    with open(a.out, "w") as f:
        for r in allrows:
            r.pop("wrongdet", None)
            f.write(json.dumps(r, default=str) + "\n")
    print("\nwrote", a.out)


if __name__ == "__main__":
    main()
