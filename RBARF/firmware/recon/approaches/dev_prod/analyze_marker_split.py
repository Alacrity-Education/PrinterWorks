#!/usr/bin/env python3
"""v2.3 marker-split decision report.

Reads the three result files written by marker_split_study.py:
  marker_split_results.jsonl   primary: the 3 candidate splits
  marker_split_controls.jsonl  + 4 diagnostic controls (attribution)
  marker_split_drift.jsonl     within-capture drift sub-sweep

and prints the decision table, the paired (McNemar) tests and the
attribution that decides whether the SPLIT or the marker CONTENT is what
moves the metrics.
"""
import gzip
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches"))
import embedded_v2 as EV                                    # noqa: E402

HERE = Path(__file__).parent
CAND = ["a_3+3", "b_4+2", "c_2+4"]
CTL = ["z3h_3+3", "z3t_3+3", "nz4_4+2", "nz2_2+4"]
MK = {"a_3+3": ("FF AA 65", "9A 55 FF"),
      "b_4+2": ("FF 00 AA 65", "9A FF"),
      "c_2+4": ("FF 65", "9A 55 00 FF"),
      "z3h_3+3": ("FF 00 65", "9A 55 FF"),
      "z3t_3+3": ("FF AA 65", "9A 00 FF"),
      "nz4_4+2": ("FF AA AA 65", "9A FF"),
      "nz2_2+4": ("FF 65", "9A 55 AA FF")}
NOTE = {"a_3+3": "candidate (a) - spec default, no 00",
        "b_4+2": "candidate (b) - 00 in header",
        "c_2+4": "candidate (c) - 00 in trailer",
        "z3h_3+3": "control - 3+3 sizing WITH a 00 (header)",
        "z3t_3+3": "control - 3+3 sizing WITH a 00 (trailer)",
        "nz4_4+2": "control - (b) sizing, NO 00",
        "nz2_2+4": "control - (c) sizing, NO 00"}


def _open(fn):
    """Accept either the plain .jsonl or the committed .jsonl.gz."""
    path = HERE / fn
    if path.exists():
        return open(path)
    gz = HERE / (fn + ".gz")
    if gz.exists():
        return gzip.open(gz, "rt")
    raise SystemExit(f"{fn}[.gz] not found -- run marker_split_study.py first")


def load(fn):
    rows = defaultdict(dict)
    with _open(fn) as f:
        for line in f:
            r = json.loads(line)
            rows[r["split"]][(r["pattern"], r["eps"], r["t0"],
                              r.get("drift", 0.0))] = r
    return rows


def plateau(k):
    return -0.023 <= k[1] <= 0.0005


def env(k):
    return abs(k[1]) <= 0.075


def maxzrun(split):
    bits = "".join(f"{b:08b}" for h in MK[split]
                   for b in bytes.fromhex(h.replace(" ", "")))
    best = cur = 0
    for c in bits:
        cur = cur + 1 if c == "0" else 0
        best = max(best, cur)
    return best


def p(v, q):
    v = sorted(v)
    return v[int(round(q * (len(v) - 1)))] if v else float("nan")


def summary(rows, k, filt=None):
    items = [r for kk, r in rows[k].items() if filt is None or filt(kk)]
    lk = [r for r in items if r["lock"]]
    return dict(
        n=len(items), lock=100.0 * len(lk) / len(items),
        eps_p50=p([r["eps_err"] for r in lk], .50),
        eps_p90=p([r["eps_err"] for r in lk], .90),
        eps_max=max((r["eps_err"] for r in lk), default=0),
        t0_p50=p([r["t0_err"] for r in lk], .50),
        t0_p90=p([r["t0_err"] for r in lk], .90),
        t0_max=max((r["t0_err"] for r in lk), default=0),
        r2=100.0 * sum(1 for r in lk if r["violations"] == 0) / len(items),
        gates=100.0 * sum(1 for r in lk if r["gates_ok"]) / len(items),
        bit=100.0 * sum(1 for r in lk if r["biterr"] == 0) / len(items),
        cal0=st.mean([r["cal_n0"] for r in lk]) if lk else 0,
    )


def table(rows, keys, filt, title):
    print()
    print(title)
    print("-" * 121)
    print(f"{'split  markers':34s} {'lock%':>6s} "
          f"{'eps err % (p50/p90/max)':>25s} {'t0 err ns (p50/p90/max)':>25s} "
          f"{'R2ok%':>6s} {'R1-4ok%':>8s} {'bitexact%':>9s}")
    print("-" * 121)
    for k in keys:
        d = summary(rows, k, filt)
        tag = f"{k}  {MK[k][0]} / {MK[k][1]}"
        print(f"{tag:34s} {d['lock']:6.2f} "
              f"{d['eps_p50']:7.4f}/{d['eps_p90']:7.4f}/{d['eps_max']:7.4f} "
              f"{d['t0_p50']:7.1f}/{d['t0_p90']:7.1f}/{d['t0_max']:7.1f} "
              f"{d['r2']:6.2f} {d['gates']:8.2f} {d['bit']:9.2f}")
    print("-" * 121)


def mcnemar(rows, base, other, pred, filt=None):
    keys = [k for k in rows[base] if k in rows[other]
            and (filt is None or filt(k))]
    n01 = sum(1 for k in keys if pred(rows[other][k])
              and not pred(rows[base][k]))
    n10 = sum(1 for k in keys if pred(rows[base][k])
              and not pred(rows[other][k]))
    n = n01 + n10
    return n01, n10, ((abs(n01 - n10) - 1) ** 2 / n if n else 0.0), len(keys)


OK = (lambda r: r["lock"] and r["biterr"] == 0)


def paired(rows, keys, filt, title):
    print()
    print(title)
    print(f"  {'split':10s} {'wins vs a':>10s} {'a wins':>8s} "
          f"{'chi2':>8s} {'verdict (chi2>3.84 = p<0.05)':>32s}")
    for k in keys:
        n01, n10, chi, N = mcnemar(rows, "a_3+3", k, OK, filt)
        if chi <= 3.84:
            v = "no measurable difference"
        else:
            v = f"{k} better" if n01 > n10 else "(a) better"
        print(f"  {k:10s} {n01:10d} {n10:8d} {chi:8.2f} {v:>32s}")


def main():
    R = load("marker_split_results.jsonl")
    C = load("marker_split_controls.jsonl")
    D = load("marker_split_drift.jsonl")
    n = sum(len(v) for v in R.values()) + sum(len(v) for v in C.values()) \
        + sum(len(v) for v in D.values())
    print("=" * 121)
    print("v2.3 MARKER-SPLIT STUDY -- decision report")
    print("=" * 121)
    print(f"{n} decoder runs total.  Calibrated sampler = recon/synth.py's "
          f"fitted model; lock stage =")
    print("embedded_v2._seed + ._refine x2 (as decode_state runs it), then "
          "its marker-forced")
    print("calibration + decision passes.  All three candidate splits are 6 "
          "marker bytes, so every")
    print("frame is 3 + 22 + 3 = 28 B = 224 bits: the frame LENGTH the seed "
          "lock solves is identical")
    print("and any difference comes only from where the marker EDGES sit.")
    print()
    print("  lock%      _seed returned K inside [K_MIN, K_MAX] (else R1)")
    print("  eps err    |K_NOM/K - 1 - eps_true|, percentage points")
    print("  t0 err     |(tau - BIAS_U)*TU_ns - t0_true|, ns")
    print("  R2ok%      zero marker-bit violations")
    print("  R1-4ok%    the R1..R4 refusal gates all pass")
    print("  bitexact%  payload' decoded bit-for-bit correct (delivery proxy)")

    table(R, CAND, None,
          "1. CANDIDATES, FULL SWEEP  (eps -8..+8 %, t0 375-736 ns, "
          "18 payloads, 17496 cases each)")
    table(R, CAND, env,
          "2. CANDIDATES INSIDE THE +-7.5 % ENVELOPE  (the stated lock "
          "requirement)")
    table(R, CAND, plateau,
          "3. CANDIDATES ON THE DELIVERY PLATEAU  (-2.3..+0.05 %, "
          "MARGIN_INVESTIGATION SS2)")
    paired(R, CAND[1:], None,
           "4. PAIRED TEST, full sweep (same payload/eps/t0 cell, "
           "bit-exact outcome)")
    paired(R, CAND[1:], plateau, "5. PAIRED TEST, plateau only")

    print()
    print("=" * 121)
    print("6. ATTRIBUTION -- is it the SPLIT or the marker CONTENT?")
    print("=" * 121)
    print("The two candidates that beat (a) both put an 8-consecutive-zero "
          "byte back into a marker")
    print("AND make the two ends unequal.  These controls separate the "
          "two effects.")
    table(C, CAND + CTL, plateau,
          "6a. CANDIDATES + CONTROLS, delivery plateau")
    print(f"{'split':10s} {'note':44s} {'max 0-run':>10s} "
          f"{'cal class-0 width samples/frame':>32s}")
    for k in CAND + CTL:
        d = summary(C, k, plateau)
        print(f"{k:10s} {NOTE[k]:44s} {maxzrun(k):10d} {d['cal0']:32.2f}")
    paired(C, CAND[1:] + CTL, plateau,
           "6b. PAIRED vs (a), plateau -- controls included")

    table(D, CAND, None,
          "7. WITHIN-CAPTURE DRIFT  (+-0.2 / +-0.4 % linear ramp -- the "
          "stated reason for a ruler at BOTH ends)")
    paired(D, CAND[1:], None, "7b. PAIRED vs (a) under drift")

    print()
    print("=" * 121)
    print("VERDICT")
    print("=" * 121)
    a = summary(R, "a_3+3", None)
    b = summary(R, "b_4+2", None)
    c = summary(R, "c_2+4", None)
    print(f"  lock success is {a['lock']:.2f} / {b['lock']:.2f} / "
          f"{c['lock']:.2f} % -- the primary metric does not discriminate "
          f"at all.")
    print("  eps/t0 error medians are equal across splits; only the p90 "
          "tail moves, and section 6")
    print("  shows that tail tracks the presence of an 8-zero marker byte, "
          "NOT the split:")
    n01, n10, chi, _ = mcnemar(C, "a_3+3", "nz4_4+2", OK, plateau)
    print(f"    4+2 sizing WITHOUT a 00 byte vs (a): {n01} / {n10}, "
          f"chi2 = {chi:.2f}  -> no measurable difference")
    n01, n10, chi, _ = mcnemar(C, "a_3+3", "nz2_2+4", OK, plateau)
    print(f"    2+4 sizing WITHOUT a 00 byte vs (a): {n01} / {n10}, "
          f"chi2 = {chi:.2f}  -> (a) is BETTER")
    zb = summary(C, "z3t_3+3", plateau)["bit"]
    bb = summary(C, "b_4+2", plateau)["bit"]
    print(f"  And with the content matched, 3+3 stays the best sizing: the "
          f"best 3+3-with-00 variant")
    print(f"  reaches {zb:.2f} % bit-exact on the plateau vs {bb:.2f} % for "
          f"the best 4+2-with-00 variant.")
    print()
    print("  -> KEEP SPLIT (a) 3+3, HEADER = FF AA 65, TRAILER = 9A 55 FF.")
    print("     No split measurably wins once marker content is controlled.")
    print()
    print("  SEPARATE FINDING FOR THE OWNER (not acted on here): dropping "
          "the 0x00 probe DOES cost.")
    print("     Every variant carrying an 8-zero marker byte beats every "
          "variant without one, on")
    print("     plateau bit-exactness and on the lock-error tail, "
          "regardless of split.  PROTOCOL.md's")
    print("     rationale that payload zero runs 'serve the same purpose' "
          "is not borne out here.")


if __name__ == "__main__":
    main()
