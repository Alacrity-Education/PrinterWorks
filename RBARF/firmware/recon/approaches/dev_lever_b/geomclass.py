#!/usr/bin/env python3
"""TASK 1b -- the full geometric taxonomy of a bit's evidence.

For payload' bit t at offset `off` in its segment, the bit's own
DISCRIMINATING INTERVAL in the segment's coordinates is

    A = off*BIT_U + h0c     (the fall position if the bit is 0)
    B = off*BIT_U + h1c     (the fall position if the bit is 1)

and the only observation is the fall bracket (u, v] -- u = last HIGH
sample, v = first LOW sample, adjacent in the sample comb, so no sample
lies strictly between them.  Six mutually exclusive classes:

  DEAD    u < A and B <= v      the bracket CONTAINS the window: no
                                sample inside it -> both hypotheses
                                admitted, decision is a coin flip
  BOTH_I  (same thing, kept as the name for A and B both interior)
  ONLY_A  u < A <= v only       the 0-fall was observed
  ONLY_B  u < B <= v only       the 1-fall was observed
  MID     A <= u and v <= B     the WINDOW contains the bracket: a
                                transition was seen inside the window
                                but at NEITHER fitted boundary -> the
                                polarity rests on which fitted boundary
                                is nearer, i.e. on the width fit, not on
                                a sample
  EARLY   v < A                 bracket entirely before the window
  LATE    B < u                 bracket entirely after the window

EARLY/LATE are the confident bulk (a bit deep inside a ones run or a
zeros run).  This script measures P(wrong | class) and the class
frequency, which is what a candidate policy must be built on.
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

TRIM_EPS = [-0.016, -0.014, -0.012, -0.010, -0.008, -0.006, -0.004]
ARM_T0 = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
CLASSES = ("DEAD", "ONLY_A", "ONLY_B", "MID", "EARLY", "LATE")

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


def classify(u, v, A, B):
    ca = u < A <= v
    cb = u < B <= v
    if ca and cb:
        return "DEAD"
    if ca:
        return "ONLY_A"
    if cb:
        return "ONLY_B"
    if v < A:
        return "EARLY"
    if B < u:
        return "LATE"
    return "MID"


def one(nd, data, samples):
    e, _ = ref(nd)
    import crc
    tb = e._bits_of(e.HDR + crc.build_payload_v23(data) + e.TRL)
    out, info = e.decode_ex(samples)
    st = dwlib.analyze(e, samples, tb)
    if st is None:
        return None
    cal = e._calibrate(samples, st["K"], st["tau"])
    per = collections.Counter()          # (class, wrong) -> n
    mgs = collections.defaultdict(list)
    wrongcls = collections.Counter()
    bitcls = {}
    for t in range(e.PP_LO, e.PP_HI):
        so = st["seg_of"][t]
        if so is None:
            continue
        (k0, k1, fam, a_hat, u, v) = so
        off = t - k0
        hb = off * e.BIT_U
        A = hb + cal.h0f[fam]
        B = hb + cal.h1f[fam]
        cl = classify(u, v, A, B)
        w = st["bits"][t] != tb[t]
        per[(cl, w)] += 1
        mgs[(cl, w)].append(st["marg"][t])
        bitcls[t] = cl
        if w:
            wrongcls[cl] += 1
    return dict(cause=info["cause"], emitted=(out is not None),
                correct=(out == data), per=dict(per),
                mgs={"%s|%d" % k: v for k, v in mgs.items()},
                wrongcls=dict(wrongcls), nwrong=len(st["wrong"]),
                n_weak=st["n_weak"],
                nmid=sum(1 for c in bitcls.values() if c == "MID"),
                ndead=sum(1 for c in bitcls.values() if c == "DEAD"))


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
        r.update(src="synth", pat=name, eps=eps, t0=t0)
    return r


def report(rows, title):
    rows = [r for r in rows if r]
    print("\n" + "=" * 78)
    print(title + "  (%d locked frames)" % len(rows))
    print("=" * 78)
    tot = collections.Counter()
    mg = collections.defaultdict(list)
    for r in rows:
        for k, n in r["per"].items():
            cl, w = (k if isinstance(k, tuple) else eval(k))
            tot[(cl, bool(w))] += n
        for k, v in r["mgs"].items():
            cl, w = k.split("|")
            mg[(cl, w == "1")] += v
    print("%-8s %10s %8s %10s %10s %s"
          % ("class", "bits", "wrong", "P(wrong)", "share", "margin p50/p90 (right | wrong)"))
    grand = sum(tot.values())
    for cl in CLASSES:
        ok = tot[(cl, False)]
        w = tot[(cl, True)]
        n = ok + w
        if not n:
            continue
        mr = sorted(mg[(cl, False)])
        mw = sorted(mg[(cl, True)])
        f = lambda a, q: (a[int(len(a) * q)] if a else -1)      # noqa: E731
        print("%-8s %10d %8d %9.4f%% %9.4f%%  %d/%d | %d/%d"
              % (cl, n, w, 100.0 * w / n, 100.0 * n / grand,
                 f(mr, .5), f(mr, .9), f(mw, .5), f(mw, .9)))
    print("%-8s %10d %8d %9.4f%%" % ("TOTAL", grand,
                                     sum(v for (c, w), v in tot.items() if w),
                                     100.0 * sum(v for (c, w), v in tot.items()
                                                 if w) / grand))
    # per refusal class: are the wrong bits MID?
    for cause in ("refuse_nocand", "refuse_chase", "refuse_admit"):
        grp = [r for r in rows if r["cause"] == cause and r["nwrong"]]
        if not grp:
            continue
        wc = collections.Counter()
        allmid = 0
        anymid = 0
        for r in grp:
            for cl, n in r["wrongcls"].items():
                wc[cl] += n
            tw = sum(r["wrongcls"].values())
            m = r["wrongcls"].get("MID", 0) + r["wrongcls"].get("DEAD", 0)
            if m == tw:
                allmid += 1
            if m:
                anymid += 1
        print("\n%s: %d frames with wrong payload' bits; wrong-bit classes %s"
              % (cause, len(grp), dict(wc.most_common())))
        print("   frames where ALL wrong bits are MID or DEAD: %d (%.1f %%)"
              "   ANY: %d (%.1f %%)"
              % (allmid, 100.0 * allmid / len(grp),
                 anymid, 100.0 * anymid / len(grp)))
        nm = sorted(r["nmid"] + r["ndead"] for r in grp)
        print("   MID+DEAD bits per such frame: p50 %d p90 %d max %d"
              % (nm[len(nm) // 2], nm[int(len(nm) * .9)], nm[-1]))
    dl = [r for r in rows if r["correct"]]
    nm = sorted(r["nmid"] + r["ndead"] for r in dl)
    if nm:
        print("\nMID+DEAD bits per DELIVERED frame: p50 %d p90 %d p99 %d "
              "max %d   (frames with 0: %.1f %%)"
              % (nm[len(nm) // 2], nm[int(len(nm) * .9)],
                 nm[int(len(nm) * .99)], nm[-1],
                 100.0 * sum(1 for x in nm if x == 0) / len(nm)))


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
    report(rows, "REAL SILICON v2.3 corpora (ND=16)")
    e, L = ref(48)
    names = list(L.prod_payloads())
    jobs = [(nm, eps, t0, 48) for nm in names for eps in TRIM_EPS
            for t0 in ARM_T0]
    with mp.Pool(a.j) as p:
        rows = p.map(job_synth, jobs, chunksize=8)
    report(rows, "SYNTHETIC production sweep (ND=48), trim band x arm range")


if __name__ == "__main__":
    main()
