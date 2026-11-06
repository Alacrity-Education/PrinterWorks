"""REAL-SILICON anchor: on the 54-capture bench corpus and the 96-capture
trim corpus, with the votes machinery CUT, how many frames are

  (a) already exact,
  (b) reachable by the chosen v2 chase admission policy
      (n_tied <= 8, weak set = {mgv <= 8}, |weak| <= 5, weight <= 2),
  (c) out of reach (chase would exhaust -> refusal).

These corpora carry v2.0 payloads (no check block), so this measures
containment of the wrong bits, not the CRC arithmetic.
"""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from harness import load_dataset, linearize             # noqa: E402
import ref_marg as ref                                  # noqa: E402
ref.VOTES = False
ref._configure(16)
TIE_EMIT, MG_MAX, A_MAX, W_MAX = 8, 8, 5, 2
EPS = {0: -1.07, 1: -2.25, 2: -3.28, 3: -4.38,
       4: +3.73, 5: +2.49, 6: +1.27, 7: +0.02}


def run(path, label, votes=False):
    ref.VOTES = votes
    meta, caps = load_dataset(path)
    c = Counter(); per = {}
    for cap in caps:
        exp = bytes.fromhex(cap["payload"])
        st = ref.decode_state(linearize(cap["capture"]))
        key = cap.get("trim", "-")
        d = per.setdefault(key, Counter())
        d["n"] += 1
        if st is None:
            c["refuse_hard"] += 1; d["refuse"] += 1; continue
        bits, mgv = st["bits"], st["mgv"]
        if any(ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t]
               for t in range(ref.NB)) or st["infeasible"] > ref.GATE_INFEAS \
                or st["label_err"] > ref.GATE_LABERR:
            c["refuse_hard"] += 1; d["refuse"] += 1; continue
        pm = mgv[32:32 + 128]
        pb = bits[32:32 + 128]
        eb = [(b >> (7 - j)) & 1 for b in exp for j in range(8)]
        wrong = [i for i in range(128) if pb[i] != eb[i]]
        n0 = sum(1 for v in pm if v == 0)
        weak = [i for i in range(128) if pm[i] <= MG_MAX]
        if not wrong:
            c["exact"] += 1; d["exact"] += 1; continue
        if n0 > TIE_EMIT:
            c["refuse_emitgate"] += 1; d["refuse"] += 1; continue
        if len(weak) == 0 or len(weak) > A_MAX:
            c["refuse_admit"] += 1; d["refuse"] += 1; continue
        if len(wrong) <= W_MAX and set(wrong) <= set(weak):
            c["reachable"] += 1; d["reach"] += 1
        else:
            c["out_of_reach"] += 1; d["refuse"] += 1
    n = sum(c.values())
    print("--- %s (n=%d, votes=%s) ---" % (label, n, votes))
    print("  exact pre-CRC        %3d (%5.1f%%)" % (c["exact"], 100.*c["exact"]/n))
    print("  chase-reachable      %3d (%5.1f%%)  -> ceiling %3d (%5.1f%%)"
          % (c["reachable"], 100.*c["reachable"]/n,
             c["exact"] + c["reachable"], 100.*(c["exact"]+c["reachable"])/n))
    print("  refused: hard %d  emit-gate %d  admission %d  out-of-reach %d"
          % (c["refuse_hard"], c["refuse_emitgate"], c["refuse_admit"],
             c["out_of_reach"]))
    if len(per) > 1:
        for k in sorted(per, key=lambda k: EPS.get(k, 0)):
            d = per[k]
            print("    trim %s (eps %+5.2f%%): n=%2d exact %2d reach %2d "
                  "refuse %2d" % (k, EPS.get(k, 0), d["n"], d["exact"],
                                  d["reach"], d["refuse"]))
    return c


def v1_silent(paths):
    """v1 exactly as it ships (votes ON, all refusal gates): how many of
    its emissions on real silicon are silently wrong?"""
    ref.VOTES = True
    print("=== v1 (votes ON, all gates) on every real capture ===")
    tn = te = tw = tr = 0
    for p, lab in paths:
        meta, caps = load_dataset(p)
        n = em = w = 0
        for cap in caps:
            n += 1
            exp = bytes.fromhex(cap["payload"])
            got = ref.decode(linearize(cap["capture"]), meta)
            if got is None:
                continue
            em += 1
            if got != exp:
                w += 1
        print("  %-34s n=%3d emitted %3d exact %3d SILENTLY-WRONG %2d "
              "refused %d" % (lab, n, em, em - w, w, n - em))
        tn += n; te += em; tw += w; tr += n - em
    print("  %-34s n=%3d emitted %3d exact %3d SILENTLY-WRONG %2d "
          "refused %d" % ("TOTAL", tn, te, te - tw, tw, tr))
    ref.VOTES = False


DATA = R.parent / "data"
v1_silent([(str(DATA / "captures.json"), "bench (captures.json)"),
           (str(DATA / "captures_val.json"), "validation (captures_val.json)"),
           (str(DATA / "captures_trim.json"), "trim sweep (captures_trim.json)")])
print()
run(str(DATA / "captures.json"), "bench corpus, 54 real captures")
run(str(DATA / "captures.json"), "bench corpus, v1 baseline WITH votes",
    votes=True)
run(str(DATA / "captures_trim.json"), "trim corpus, 96 real captures")
p = DATA / "captures_val.json"
if p.exists():
    run(str(p), "validation corpus (unseen patterns)")
