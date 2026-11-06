#!/usr/bin/env python3
"""HSI-envelope sweep of embedded_v2 on synthetic v2.1 rev2 frames.

eval_envelope.py cannot run directly (it synthesises 16-byte-payload
v2.0 frames; the v2.1 payload' is 19 bytes), so this is the adapted
sweep the task asks for: synth.synth_capture with 19-byte payload'
(DATA || [CRC8]*3 via bench crc.build_payload), eps over the +/-8%
envelope (the eval_envelope.py points), plus the 8 real trim-code eps
points (reproducing EMBEDDED_V2_SPEC.md SS12.2's test-scale table on
the same 19 clock points x 18 patterns x 3 phases = 1026 decodes) and
eval_envelope.py's within-capture drift case.

Per clock point: delivered (exact) split direct/chase, REFUSALS by
cause, and WRONG EMISSIONS (catastrophic) -- the refusal-vs-wrong
split.  Ground truth is used for scoring only.
"""
import sys
import pathlib
from collections import Counter

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches"))
sys.path.insert(0, str(R.parent / "bench"))
from synth import synth_capture                  # noqa: E402
from patterns import PATTERNS                    # noqa: E402
from crc import build_payload                    # noqa: E402
import embedded_v2 as v2                         # noqa: E402

ND = 16
# eval_envelope.py's sweep points ...
ENV_EPS = [-0.08, -0.075, -0.05, -0.025, -0.01, 0.0,
           0.01, 0.025, 0.05, 0.075, 0.08]
# ... plus the 8 measured trim-code points (TRIM_SWEEP.md), matching the
# spec's SS12.2 test-scale table (19 points, n = 1026)
TRIM_EPS = [-0.04385, -0.03281, -0.02248, -0.01072,
            0.00022, 0.01274, 0.02492, 0.03733]
STRONG = {-0.025, -0.02248, -0.01072, -0.01, 0.0, 0.00022, 0.01, 0.01274}


def sweep_point(eps, drift, reps=3):
    c = Counter()
    tr = Counter(maxtrials=0)
    for name, data in PATTERNS.items():
        pp = build_payload(data)                 # 19-byte payload'
        assert len(pp) == ND + 3
        for rep in range(reps):
            phase = 254.0 + (rep * 83.0) % 250.0
            samples = synth_capture(pp, eps=eps, drift=drift,
                                    phase_ns=phase)
            got, info = v2.decode_ex(samples)
            c["n"] += 1
            if info["chased"]:
                tr["chases"] += 1
                tr["trials"] += info["trials"]
                tr["maxtrials"] = max(tr["maxtrials"], info["trials"])
            if got is None:
                c["refuse"] += 1
                c[info["cause"]] += 1
            elif got == data:
                c["ok"] += 1
                c["ok_" + info["path"]] += 1
            else:
                c["WRONG"] += 1
                print("      !!! CATASTROPHIC eps=%+.3f%% %s rep %d "
                      "via %s: %s" % (eps * 100, name, rep, info["path"],
                                      got.hex()))
    return c, tr


def main():
    v2._configure(ND)                            # v2.1 test build
    pts = sorted(set(ENV_EPS + TRIM_EPS))
    print("=" * 78)
    print("synthetic envelope, v2.1 rev2 frames (19 B payload', 216-bit "
          "frame), 18 patterns x 3 phases per point")
    print("=" * 78)
    print("%-16s %-10s %7s %7s %7s  %-30s %s"
          % ("clock error", "delivered", "direct", "chase", "WRONG",
             "refusals (cause)", ""))
    tot = Counter()
    ttr = Counter(maxtrials=0)
    strong = Counter()
    for eps in pts:
        c, tr = sweep_point(eps, 0.0)
        for k, v_ in c.items():
            tot[k] += v_
            if round(eps, 6) in {round(e, 6) for e in STRONG}:
                strong[k] += v_
        for k in ("chases", "trials"):
            ttr[k] += tr[k]
        ttr["maxtrials"] = max(ttr["maxtrials"], tr["maxtrials"])
        rc = ("emit %d nocand %d admit %d exhaust %d hard %d"
              % (c["refuse_emitgate"], c["refuse_nocand"],
                 c["refuse_admit"], c["refuse_chase"],
                 c["refuse_lock"] + c["refuse_marker"]
                 + c["refuse_infeasible"] + c["refuse_labelerr"]))
        print("eps%+7.3f%%      %3d/%-3d %s %7d %7d %7d  %-30s"
              % (eps * 100, c["ok"], c["n"],
                 "(%5.1f%%)" % (100.0 * c["ok"] / c["n"]),
                 c["ok_direct"], c["ok_chase"], c["WRONG"], rc))
    # eval_envelope.py's within-capture drift case at the slow corner
    c, tr = sweep_point(-0.075, 0.002)
    print("%-16s %3d/%-3d %s %7d %7d %7d  drift +0.2%% ramp"
          % ("eps-7.5%+drift", c["ok"], c["n"],
             "(%5.1f%%)" % (100.0 * c["ok"] / c["n"]),
             c["ok_direct"], c["ok_chase"], c["WRONG"]))
    dr = c
    print("-" * 78)
    n, ok = tot["n"], tot["ok"]
    print("TOTAL (19 static points)  delivered %d/%d (%.1f%%) = direct %d "
          "+ chase %d;  WRONG %d;  refused %d"
          % (ok, n, 100.0 * ok / n, tot["ok_direct"], tot["ok_chase"],
             tot["WRONG"], tot["refuse"]))
    print("  refusal split: emit-gate %d, no-candidate %d, admission %d, "
          "chase-exhausted %d, hard-gates %d"
          % (tot["refuse_emitgate"], tot["refuse_nocand"],
             tot["refuse_admit"], tot["refuse_chase"],
             tot["refuse_lock"] + tot["refuse_marker"]
             + tot["refuse_infeasible"] + tot["refuse_labelerr"]))
    print("  strong band (-2.5..+1.3%%): delivered %d/%d (%.1f%%), WRONG %d"
          % (strong["ok"], strong["n"],
             100.0 * strong["ok"] / max(1, strong["n"]), strong["WRONG"]))
    print("  chases %d, trials total %d (mean %.1f, max %d); a-priori FA "
          "bound %.2f expected, observed %d"
          % (ttr["chases"], ttr["trials"],
             ttr["trials"] / max(1, ttr["chases"]), ttr["maxtrials"],
             ttr["chases"] * (1 - (1 - 1 / 256.0) ** max(1,
                                                         ttr["maxtrials"])),
             tot["WRONG"]))
    print("  spec SS12.2 reference (same 19 points, ref_marg + normative "
          "policy): 520/1026 (50.7%), CAT 0")
    cat = tot["WRONG"] + dr["WRONG"]
    print("VERDICT: catastrophic %d (must be 0) -> %s"
          % (cat, "PASS" if cat == 0 else "FAIL"))
    return 0 if cat == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
