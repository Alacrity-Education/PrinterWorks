#!/usr/bin/env python3
"""CLK_HSITRIMR trim-sweep analysis: measure eps (relative HSI frequency
error vs nominal 16 MHz) per trim code from data/captures_trim.json.

Two independent estimators per capture:

1. eps_span — robust span-based estimate. The frame spans exactly
   191*1250 + 752 = 239502 ns of wall time between its first rising edge
   and its last falling edge (crystal-exact transmitter, effective T1H).
   Sample (i,s) sits at nominal sampler time A(i,s) = i*LOOP + o[s] +
   sum_j w[j]*C_j(i,s) (the calibrated model, with the data-dependent
   branch term accumulated from the capture's own HIGH reads) and at
   wall time t0 + A/(1+eps). The last high->low transition therefore
   gives 1+eps ~= A_fall / (239502 - t0), with A_fall taken as the
   midpoint between the last HIGH sample and the following LOW one
   (quantization ~ +/-0.1%).

2. eps_align — precise estimate: maximize raw sample agreement between
   the capture and synth._simulate() over the frame window, with only
   (t0, eps) free (same approach as synth._align, but with wide eps
   bounds seeded by eps_span instead of the bench-point-only bounds).

Also per capture: high-pulse count, merged-1 loop count (like
synth._merged_loops), and the swallowed-0 estimate
(192 - pulses - merged; the wire carries exactly 192 high pulses).

Writes dev_trimsweep/results.json and prints the aggregate tables.
"""

import json
import sys
from pathlib import Path
from statistics import mean, pstdev

HERE = Path(__file__).parent
RECON = HERE.parent.parent
sys.path.insert(0, str(RECON))
sys.path.insert(0, str(RECON.parent / "bench"))

import synth  # noqa: E402
from synth import (LOOP_NS, SLOT_OFFSET_NS, BRANCH_COST_NS,  # noqa: E402
                   _simulate, _merged_loops)
from harness import linearize, high_pulses  # noqa: E402
from patterns import frame  # noqa: E402

DATA = RECON.parent / "data" / "captures_trim.json"

TRUE_SPAN_NS = 191 * 1250.0 + 752.0        # 239502: first rise -> last fall
T0_ASSUMED = 385.0                         # mean fitted t0 (synth.py)
FIT_ITER = 102                             # frame window (+ margin) in loops
WIRE_PULSES = 192                          # one high pulse per frame bit


def nominal_A(samples):
    """A(i,s) in nominal ns for every sample, with the data-dependent
    branch cost accumulated from the capture's own HIGH reads."""
    out = []
    wsum = 0.0
    for i, s, v in samples:
        out.append(i * LOOP_NS + SLOT_OFFSET_NS[s] + wsum)
        if v:
            wsum += BRANCH_COST_NS[s]
    return out


def eps_span(samples):
    """Span-based eps estimate (see module docstring)."""
    A = nominal_A(samples)
    last_hi = None
    for k, (_, _, v) in enumerate(samples):
        if v:
            last_hi = k
    if last_hi is None or last_hi + 1 >= len(samples):
        return None
    a_fall = 0.5 * (A[last_hi] + A[last_hi + 1])
    return a_fall / (TRUE_SPAN_NS - T0_ASSUMED) - 1.0


def eps_align(samples, payload, seed_eps):
    """Wide-range (t0, eps) fit by maximizing sample agreement over the
    frame window; seeded around eps_span. Returns (eps, phase, agree)."""
    bits = [int(b) for byte in frame(payload) for b in f"{byte:08b}"]
    ref = [v for _, _, v in samples[:FIT_ITER * 8]]

    def agree(ph, eps):
        syn = _simulate(bits, eps, 0.0, ph, FIT_ITER)
        return sum(1 for (_, _, a), b in zip(syn, ref) if a == b)

    best = (-1, 0.0, 0.0)
    e_lo, e_hi = seed_eps - 0.008, seed_eps + 0.008
    n_e = 33                                        # eps step 5e-4
    for j in range(n_e):
        eps = e_lo + (e_hi - e_lo) * j / (n_e - 1)
        ph = 200.0
        while ph <= 560.0:                          # phase step 10 ns
            a = agree(ph, eps)
            if a > best[0]:
                best = (a, ph, eps)
            ph += 10.0
    a0, ph0, eps0 = best
    sp, se = 8.0, 2.5e-4                            # pattern search, shrink
    while sp > 0.05:
        moved = False
        for dp, de in ((sp, 0.0), (-sp, 0.0), (0.0, se), (0.0, -se),
                       (sp, se), (sp, -se), (-sp, se), (-sp, -se)):
            a = agree(ph0 + dp, eps0 + de)
            if a > a0:
                a0, ph0, eps0 = a, ph0 + dp, eps0 + de
                moved = True
        if not moved:
            sp /= 2.0
            se /= 2.0
    return eps0, ph0, a0 / len(ref)


def main():
    d = json.loads(DATA.read_text())
    results = []
    for n, c in enumerate(d["captures"]):
        samples = linearize(c["capture"])
        payload = bytes.fromhex(c["payload"])
        e_sp = eps_span(samples)
        e_al, ph, agr = eps_align(samples, payload, e_sp)
        n_pulses = len(high_pulses(samples))
        n_merged = _merged_loops(samples)
        results.append({
            "pattern": c["pattern"], "rep": c["rep"], "trim": c["trim"],
            "eps_span": e_sp, "eps_align": e_al, "phase_ns": ph,
            "agree": agr, "pulses": n_pulses, "merged": n_merged,
            "swallowed_est": WIRE_PULSES - n_pulses - n_merged,
            "high_samples": sum(v for _, _, v in samples),
        })
        print(f"[{n + 1:2d}/96] trim {c['trim']} {c['pattern']:6s} "
              f"rep {c['rep']}: eps_span {e_sp * 100:+.3f}%  "
              f"eps_align {e_al * 100:+.4f}%  (agree {agr:.3%}, "
              f"phase {ph:.0f} ns, pulses {n_pulses}, merged {n_merged}, "
              f"swallowed {WIRE_PULSES - n_pulses - n_merged})")
        sys.stdout.flush()

    (HERE / "results.json").write_text(json.dumps(results, indent=1))

    # ---- aggregates -----------------------------------------------------
    print("\n=== trim -> eps (align method, pooled over all patterns) ===")
    by_trim = {}
    for r in results:
        by_trim.setdefault(r["trim"], []).append(r)
    pooled = {}
    for t in sorted(by_trim):
        es = [r["eps_align"] for r in by_trim[t]]
        pooled[t] = (mean(es), pstdev(es), min(es), max(es))
        cross = mean(abs(r["eps_align"] - r["eps_span"]) for r in by_trim[t])
        print(f"trim {t}: eps {mean(es) * 100:+.4f}%  sd {pstdev(es) * 100:.4f}%  "
              f"range [{min(es) * 100:+.4f}, {max(es) * 100:+.4f}]%  "
              f"|align-span| {cross * 100:.3f}%")

    print("\n=== per-pattern eps means ===")
    pats = sorted({r["pattern"] for r in results})
    hdr = "trim  " + "".join(f"{p:>9s}" for p in pats)
    print(hdr)
    for t in sorted(by_trim):
        row = f"{t:4d}  "
        for p in pats:
            es = [r["eps_align"] for r in by_trim[t] if r["pattern"] == p]
            row += f"{mean(es) * 100:+8.3f}%" if es else "        -"
        print(row)

    print("\n=== steps between adjacent codes (align, pooled) ===")
    for t in range(1, 8):
        step = (pooled[t][0] - pooled[t - 1][0]) * 100
        print(f"{t - 1} -> {t}: {step:+.4f}%")

    print("\n=== sampling behavior per trim (mean over captures) ===")
    print("trim   pulses  merged  swallowed  merged(ones)  swallowed(zeros)")
    for t in sorted(by_trim):
        rs = by_trim[t]
        m_p = mean(r["pulses"] for r in rs)
        m_m = mean(r["merged"] for r in rs)
        m_s = mean(r["swallowed_est"] for r in rs)
        m_ones = mean(r["merged"] for r in rs if r["pattern"] == "ones")
        s_zero = mean(r["swallowed_est"] for r in rs
                      if r["pattern"] == "zeros")
        print(f"{t:4d}  {m_p:7.1f} {m_m:7.1f} {m_s:10.1f} {m_ones:13.1f} "
              f"{s_zero:17.1f}")


if __name__ == "__main__":
    main()
