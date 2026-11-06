#!/usr/bin/env python3
"""Two confirmations of the t0 cliff (INVESTIGATION ONLY).

A. The cliff is the capture loop's SLOT-2 offset crossing the WS2812 bit
   period:  t0_crit = BIT_NS - SLOT_OFFSET[2]/(1+eps).  Sweep eps and
   check the measured cliff tracks the prediction.
B. Where do the CORPUS captures sit?  data/captures_v23.json was acquired
   with capture.ihx's BLOCKING entry (t0 fitted 254..501 ns in
   MARGIN_INVESTIGATION SS4), not with cap_arm.s.  If the corpus t0 is
   entirely below the cliff, that is the corpus-97.8 % / live-80 % gap.
   (data/captures_val.json is never read.)
"""
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
import armlib as A                                              # noqa: E402
import t0_sweep as T                                            # noqa: E402
import analyze_arm as AA                                        # noqa: E402
from synth import BIT_NS, SLOT_OFFSET_NS                        # noqa: E402


def predict(eps):
    return BIT_NS - SLOT_OFFSET_NS[2] / (1.0 + eps)


def jobA(args):
    name, data, t0, eps = args
    bits = A.frame_bits(data)
    cap = T.pack(A.simulate(bits, eps, t0, n_iter=T.CAP + 1))
    st, out, info, _ = A.decode(cap)
    return (eps, t0, bool(st in (1, 2) and out == data), int(info.cause))


def jobB(c):
    """Fit t0 for one corpus capture (ND=16 test frame: use its own wire
    bits from the corpus metadata)."""
    raw = bytes.fromhex(c["capture"])
    bits = [int(b) for byte in bytes.fromhex(c["frame"]) for b in
            f"{byte:08b}"]
    t0, eps, ag = AA.fit_wide(bits, raw)
    return {"pattern": c.get("pattern"), "rep": c.get("rep"),
            "t0": round(t0, 1), "eps": round(eps, 6), "agree": round(ag, 4)}


def main():
    FR = T.payloads()[:4]
    print("A. CLIFF vs eps  (prediction: t0_crit = %.1f - %.1f/(1+eps))"
          % (BIT_NS, SLOT_OFFSET_NS[2]))
    tasks = []
    epss = (-0.05, -0.03, -0.0107, 0.0, 0.03, 0.06)
    t0s = [float(x) for x in range(560, 781, 5)]
    for eps in epss:
        for (n, d) in FR:
            for t in t0s:
                tasks.append((n, d, t, eps))
    with mp.Pool(20) as p:
        rows = list(p.imap(jobA, tasks, chunksize=16))
    print("   %-8s %-12s %-12s %s" % ("eps", "predicted", "measured",
                                      "match"))
    for eps in epss:
        g = [r for r in rows if r[0] == eps]
        ok = [r[1] for r in g if r[2]]
        r3 = [r[1] for r in g if r[3] == 3]
        meas = min(r3) if r3 else None
        pr = predict(eps)
        print("   %+7.2f%% %8.1f ns   %8s ns   last delivered %s ns   "
              "|err| %s"
              % (eps * 100, pr, meas, max(ok) if ok else "-",
                 ("%.1f ns" % abs(meas - pr)) if meas else "-"))

    print("\nB. CORPUS t0 (capture.ihx blocking entry) vs the production arm")
    caps = json.loads((NEWIMPL / "data" / "captures_v23.json").read_text())
    cc = caps["captures"]
    with mp.Pool(20) as p:
        res = list(p.imap(jobB, cc))
    (SC / "corpus_t0.jsonl").write_text("\n".join(json.dumps(r)
                                                  for r in res))
    t0v = sorted(r["t0"] for r in res)
    n = len(t0v)
    print("   captures_v23.json: n=%d   t0 min %.0f  p10 %.0f  p50 %.0f  "
          "p90 %.0f  max %.0f ns   (mean fit agreement %.4f)"
          % (n, t0v[0], t0v[int(.1 * n)], t0v[n // 2], t0v[int(.9 * n)],
             t0v[-1], sum(r["agree"] for r in res) / n))
    print("   above the %.1f ns cliff: %d of %d = %.1f%%"
          % (predict(-0.0107),
             sum(1 for t in t0v if t >= 690.0), n,
             100.0 * sum(1 for t in t0v if t >= 690.0) / n))


if __name__ == "__main__":
    main()
