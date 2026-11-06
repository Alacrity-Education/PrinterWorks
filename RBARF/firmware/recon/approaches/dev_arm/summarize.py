#!/usr/bin/env python3
"""Pooled numbers for ARM_INVESTIGATION.md (INVESTIGATION ONLY)."""
import json
import statistics as S
import sys
from collections import Counter
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import armlib as A                                              # noqa: E402

CLIFF = 690.0          # measured: first R3 at t0 = 690 ns, safe <= 680 ns
GEOM = 681.4           # BIT_NS - SLOT_OFFSET[2]/(1+eps), eps = -1.07 %


def load(p):
    return [json.loads(l) for l in open(SC / p)]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


runs = {"A (250 ms + dither)": load("arm_run_a_analysis.jsonl"),
        "B (strict 250 ms)": load("arm_run_b_analysis.jsonl")}
allr = [o for rs in runs.values() for o in rs]

print("=" * 78)
print("1. DELIVERY AND REFUSAL MIX")
for k, rs in list(runs.items()) + [("POOLED", allr)]:
    dv = sum(1 for o in rs if o["chip_status"] in (1, 2))
    cz = Counter(A.CAUSE[o["chip_cause"]] for o in rs if o["chip_status"] == 0)
    print("   %-22s captured %3d  delivered %3d (%.1f%%)  refused %3d  %s"
          % (k, len(rs), dv, 100.0 * dv / len(rs), len(rs) - dv, dict(cz)))

d = [o for o in allr if o.get("has_dump")]
nref = sum(1 for o in allr if o["chip_status"] == 0)
nsuc = len(allr) - nref
dref = sum(1 for o in d if o["chip_status"] == 0)
dsuc = len(d) - dref
w = nsuc / dsuc
print("\n   dump sampling: every refusal (%d/%d) + every 4th capture "
      "(%d successes dumped of %d) -> success weight %.3f"
      % (dref, nref, dsuc, nsuc, w))


def wsum(rows, pred):
    return sum((1.0 if o["chip_status"] == 0 else w)
               for o in rows if pred(o))


print("\n2. PARTIAL-BURST TEST (all %d dumps)" % len(d))
chop = [o for o in d if o["chop_bits"] >= 1]
comp = [o for o in d if o["chop_bits"] == 0]
print("   COMPLETE bursts (t0 < 1 bit, span ~478.5 bits): %d" % len(comp))
print("   PARTIAL  bursts (head-chopped >= 1 bit):        %d" % len(chop))
print("   chopped: %s" % dict(Counter(A.CAUSE[o["chip_cause"]] if
                                      o["chip_status"] == 0 else "DELIV"
                                      for o in chop)))
print("   chopped span_bits: %s" % sorted(round(o["span_bits"]) for o in chop))
print("   any DELIVERED frame with a chopped burst? %s"
      % any(o["chip_status"] in (1, 2) for o in chop))
print("   partial-burst rate over captured frames: %.1f of %d = %.2f%%"
      % (wsum(d, lambda o: o["chop_bits"] >= 1), len(allr),
         100.0 * wsum(d, lambda o: o["chop_bits"] >= 1) / len(allr)))

print("\n3. THE R3 VERDICT")
r3 = [o for o in d if o["chip_cause"] == 3]
r3c = [o for o in r3 if o["chop_bits"] == 0]
r3p = [o for o in r3 if o["chop_bits"] >= 1]
print("   R3 dumps: %d   COMPLETE burst %d (%.0f%%)   PARTIAL burst %d (%.0f%%)"
      % (len(r3), len(r3c), 100.0 * len(r3c) / len(r3), len(r3p),
         100.0 * len(r3p) / len(r3)))
print("   complete-burst R3: K median %d (window 40000..64000), eps median "
      "%+.2f%%, marker violations median %d of 48, infeasible median %d of "
      "%d segments"
      % (S.median([o["K"] for o in r3c]),
         S.median([o["chip_eps"] for o in r3c]) / 100.0,
         S.median([o["viol"] for o in r3c]),
         S.median([o["infeas"] for o in r3c]),
         S.median([o["n_seg"] for o in r3c])))
dl = [o for o in d if o["chip_status"] in (1, 2)]
print("   t0 (ns):  delivered  p10 %.0f p50 %.0f p90 %.0f max %.0f   (n=%d)"
      % (pct([o["t0_ns"] for o in dl], .1), pct([o["t0_ns"] for o in dl], .5),
         pct([o["t0_ns"] for o in dl], .9), max(o["t0_ns"] for o in dl),
         len(dl)))
print("             R3 complete p10 %.0f p50 %.0f p90 %.0f max %.0f   (n=%d)"
      % (pct([o["t0_ns"] for o in r3c], .1), pct([o["t0_ns"] for o in r3c], .5),
         pct([o["t0_ns"] for o in r3c], .9), max(o["t0_ns"] for o in r3c),
         len(r3c)))
print("   separation: every delivered dump has t0 <= %.0f ns; every "
      "complete-burst R3 has t0 >= %.0f ns  (host sweep: safe <= 680, "
      "first R3 690, 100%% R3 >= 720; geometric cliff %.1f ns)"
      % (max(o["t0_ns"] for o in dl), min(o["t0_ns"] for o in r3c), GEOM))
mis = [o for o in dl if o["t0_ns"] >= CLIFF] + \
      [o for o in r3c if o["t0_ns"] < 680.0]
print("   rows on the wrong side of the cliff: %d of %d dumps"
      % (len(mis), len(dl) + len(r3c)))

print("\n4. ARM CHARACTERISATION")
print("   unarmed gap between consecutive arm windows (us): p50 %d p90 %d "
      "max %d   (~2 us of it is diagnostic-only stamping)"
      % (pct([o["gap_unarmed"] for o in allr], .5),
         pct([o["gap_unarmed"] for o in allr], .9),
         max(o["gap_unarmed"] for o in allr)))
small = [o for o in allr if o["gap_unarmed"] <= 100]
bigg = [o for o in allr if o["gap_unarmed"] > 100]
print("   captures whose arm window opened  <=100 us after the previous: "
      "%d (%.1f%%) -> chip continuously armed" % (len(small),
                                                  100.0 * len(small) / len(allr)))
print("   captures whose arm window opened  >100 us after the previous: "
      "%d (%.1f%%) -> a RENDER ran in the gap" % (len(bigg),
                                                  100.0 * len(bigg) / len(allr)))
print("   render length measured on silicon (us): p10 %d p50 %d p90 %d max %d"
      % (pct([o["render_len"] for o in allr], .1),
         pct([o["render_len"] for o in allr], .5),
         pct([o["render_len"] for o in allr], .9),
         max(o["render_len"] for o in allr)))
print("   render duty cycle at the 100 Hz tick: %.2f%% of wall time"
      % (100.0 * S.median([o["render_len"] for o in allr]) / 10000.0))
print("   arm wait (edge - arm entry, us): p10 %d p50 %d p90 %d max %d "
      "-> arm window ~%d us, uniformly used"
      % (pct([o["arm_wait"] for o in allr], .1),
         pct([o["arm_wait"] for o in allr], .5),
         pct([o["arm_wait"] for o in allr], .9),
         max(o["arm_wait"] for o in allr),
         max(o["arm_wait"] for o in allr)))
mr = [o for o in bigg if o["arm_wait"] < 50]
print("   MID-RENDER ARRIVAL signature (gap >100 us AND edge caught <50 us "
      "into the arm): %d captures; of those %d refused, causes %s"
      % (len(mr), sum(1 for o in mr if o["chip_status"] == 0),
         dict(Counter(A.CAUSE[o["chip_cause"]] for o in mr
                      if o["chip_status"] == 0))))
mrd = [o for o in mr if o.get("chop_bits") is not None]
print("   of the mid-render captures that were dumped, %d/%d are "
      "head-chopped partial bursts"
      % (sum(1 for o in mrd if o["chop_bits"] >= 1), len(mrd)))
noc = [o for o in allr if o["arm_wait"] < 50 and o["gap_unarmed"] <= 100]
print("   frames NOT captured at all (no report): %d of %d sent (%.2f%%)"
      % (2, 450, 100.0 * 2 / 450))

print("\n5. WHICH POLL CAUGHT THE EDGE (t0 comb; the 4 BTJT polls are 2 cy "
      "= 125 ns apart, the 4th is followed by a 5 cy slot)")
h = Counter(int((o["t0_ns"] - 300) // 62.5) for o in comp)
for k in sorted(h):
    print("   t0 in %4.0f..%4.0f ns (entry + %d cy): %5.1f captures "
          "(weighted)" % (300 + k * 62.5, 300 + (k + 1) * 62.5, k,
                          wsum([o for o in comp
                                if int((o["t0_ns"] - 300) // 62.5) == k],
                               lambda o: True)))

print("\n6. FIX SIZING (weighted to all %d captured frames; 30-frame gate "
      "equivalent)" % len(allr))
base_dv = sum(1 for o in allr if o["chip_status"] in (1, 2))
tot = len(allr)
m1 = wsum(comp, lambda o: o["t0_ns"] >= CLIFF and o["chip_status"] == 0)
m2 = wsum(d, lambda o: o["chop_bits"] >= 1)
print("   baseline delivery                     %3d/%3d = %.1f%%  "
      "(%.1f/30)" % (base_dv, tot, 100.0 * base_dv / tot,
                     30.0 * base_dv / tot))
print("   M1  t0 tail above the %.0f ns cliff    %.1f frames = %.2f%%  "
      "(+%.1f/30)" % (CLIFF, m1, 100.0 * m1 / tot, 30.0 * m1 / tot))
print("   M2  mid-render partial bursts         %.1f frames = %.2f%%  "
      "(+%.1f/30)" % (m2, 100.0 * m2 / tot, 30.0 * m2 / tot))
print("   fix M1 only  -> %.1f%% (%.1f/30);  fix M1+M2 -> %.1f%% (%.1f/30)"
      % (100.0 * (base_dv + m1) / tot, 30.0 * (base_dv + m1) / tot,
         100.0 * (base_dv + m1 + m2) / tot, 30.0 * (base_dv + m1 + m2) / tot))
res = wsum(allr, lambda o: o["chip_status"] == 0) - m1 - m2
print("   residual (content: R6/R7/R8/R4 at a safe t0 on a complete burst) "
      "%.1f frames = %.2f%%" % (res, 100.0 * res / tot))
print("\n7. CONTENT CONCENTRATION (pooled, captured frames)")
for pat in sorted({o["pattern"] for o in allr}):
    g = [o for o in allr if o["pattern"] == pat]
    dv = sum(1 for o in g if o["chip_status"] in (1, 2))
    cz = Counter(A.CAUSE[o["chip_cause"]] for o in g if o["chip_status"] == 0)
    print("   %-13s %2d/%2d (%5.1f%%)  %s"
          % (pat, dv, len(g), 100.0 * dv / len(g), dict(cz) or ""))
print("\n8. DIVERGENCE: chip-vs-host parity %d/%d dumps; host delivers %d, "
      "chip refused %d of those; host WRONG %d"
      % (sum(1 for o in d if o["parity"]), len(d),
         sum(1 for o in d if o["host_delivered"]),
         sum(1 for o in d if o["host_delivered"] and o["chip_status"] == 0),
         sum(1 for o in d if o["host_wrong"])))
