"""Synthetic capture generator for HSI temperature-envelope evaluation.

Simulates the STM8 sampler reading a crystal-exact WS2812 frame, with a
parameterized receiver clock error (static scale + optional linear
within-capture drift). Output matches harness.linearize() format:
chronological (iteration, slot, level) triples.

Sampler model
-------------
The timing model is the one fitted to the 54 real captures by the
calibration work in ``approaches/dev_calibration`` (constants mirrored
below from ``dev_calibration/fitted_model.json``; that fit reproduces
99.963% of all 276372 real samples, 99.762% inside the frame window):

    A(i,s) = i*LOOP + o[s] + sum_j w[j] * C_j(i,s)
    t(i,s) = t0 + A(i,s) / (1 + eps)

  - LOOP = 40 CPU cycles = 2500.0 ns at exactly 16 MHz;
  - o[] are the intra-loop sample offsets, integer cycle gaps
    [4,5,4,4,4,6,5,8] (the documented [4,4,4,4,4,6,5,6] = 37 cycles plus
    1 cycle in the R1->R2 gap and 2 cycles in the end-of-loop gap);
  - w[] = [0,-1,0,+2,0,0,0,+1] cycles is the *data-dependent* term: each
    sample is `BTJT PC_IDR,#3,skip / NOP / RLC A`, and the taken-branch
    (HIGH read) path costs a different whole number of cycles per sample
    site because of STM8 prefetch/alignment. C_j(i,s) counts HIGH reads
    at slot j strictly before sample (i,s), so the model is causal and
    can be evaluated sample by sample while simulating.
    Without w[] the sampler's period-2 loop-length alternation is
    unreproducible and 1-bit merging comes out as one long block instead
    of the observed runs of 1-2 loops.
  - wire high widths are the exact PIO values plus a common +2 ns edge
    shift: 752 ns for a '1', 377 ns for a '0' (bit period 1250 ns).

``phase_ns`` is t0: where sample (0,0) lands after the frame's first
rising edge. Real captures fit t0 in 254..501 ns (mean ~385 ns).

The bench operating point is eps = -0.01118 (HSI ~1.1% slow), with a
spread of only +/-0.014% across all 54 captures. Run ``python3 synth.py``
to check the synthetic pulse statistics against the real captures there.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "bench"))
from patterns import PATTERNS, frame  # noqa: E402

CY_NS = 62.5                     # nominal CPU cycle at exactly 16 MHz
N_ITER = 640

# --- fitted sampler constants (dev_calibration/fitted_model.json) ------
LOOP_NS = 2500.0                                  # 40 cycles
SLOT_OFFSET_NS = [0.0, 250.0, 562.5, 812.5,       # gaps [4,5,4,4,4,6,5,8] cy
                  1062.5, 1312.5, 1687.5, 2000.0]
BRANCH_COST_NS = [0.0, -62.5, 0.0, 125.0,         # w[] = [0,-1,0,2,0,0,0,1] cy
                  0.0, 0.0, 0.0, 62.5]

BIT_NS = 1250.0
T1H_NS = 752.0                   # effective high width of a '1' bit
T0H_NS = 377.0                   # effective high width of a '0' bit

# Same thing in integer CPU cycles, kept for older scripts that imported
# these names (the values are now the fitted ones, not the hand guess).
LOOP_CY = int(round(LOOP_NS / CY_NS))                       # 40
SLOT_POS_CY = [int(round(o / CY_NS)) for o in SLOT_OFFSET_NS]
# -> [0, 4, 9, 13, 17, 21, 27, 32]; gaps [4,5,4,4,4,6,5,8]

# Bench operating point recovered by the fit (mean over the 54 captures).
BENCH_EPS = -0.01118
BENCH_PHASE_NS = 385.0

# Total nominal span of a capture, used to normalize the drift ramp.
_TOTAL_NS = (N_ITER - 1) * LOOP_NS + SLOT_OFFSET_NS[-1]


def _frame_level(bits, t_ns: float) -> int:
    """Waveform level at absolute time t (t=0 is frame start)."""
    if t_ns < 0:
        return 0
    k = int(t_ns // BIT_NS)
    if k >= len(bits):
        return 0
    within = t_ns - k * BIT_NS
    return 1 if within < (T1H_NS if bits[k] else T0H_NS) else 0


def synth_capture(payload: bytes, eps: float = 0.0, drift: float = 0.0,
                  phase_ns: float = BENCH_PHASE_NS):
    """Simulate one capture.

    eps:      static relative HSI frequency error (+ = fast clock).
              Sample spacing in real time scales by 1/(1+eps).
    drift:    additional relative frequency change from capture start to
              capture end (linear ramp), e.g. 0.002 = +0.2%.
    phase_ns: where the first slot-0 sample lands relative to the frame's
              first rising edge (the fitted t0; real captures 254..501).
    Returns chronological [(iteration, slot, level)] like linearize().
    """
    fr = frame(payload)
    bits = [int(b) for byte in fr for b in f"{byte:08b}"]
    return _simulate(bits, eps, drift, phase_ns, N_ITER)


def _simulate(bits, eps, drift, phase_ns, n_iter):
    """Core sampler simulation; n_iter lets callers stop early (all
    samples past the frame window are low anyway)."""
    out = []
    wsum = 0.0            # sum_j w[j]*C_j, updated incrementally
    for i in range(n_iter):
        base = i * LOOP_NS
        for s in range(8):
            if i == N_ITER - 1 and s >= 6:
                break                      # last boundary samples lost
            a = base + SLOT_OFFSET_NS[s] + wsum
            f_rel = (1.0 + eps) * (1.0 + drift * (a / _TOTAL_NS))
            lvl = _frame_level(bits, phase_ns + a / f_rel)
            if lvl:
                wsum += BRANCH_COST_NS[s]
            out.append((i, s, lvl))
    return out


def envelope_cases(reps: int = 3):
    """Yield (case_name, pattern_name, payload, eps, drift, phase_ns).

    Sweep: one point past each guaranteed corner of the +/-7.5% envelope,
    plus a within-capture drift case at the hard (slow) corner.
    Phases vary deterministically per rep, spanning the t0 range the fit
    recovered from the real captures (254..501 ns).
    """
    eps_points = [-0.08, -0.075, -0.05, -0.025, -0.01, 0.0,
                  0.01, 0.025, 0.05, 0.075, 0.08]
    for eps in eps_points:
        for name, payload in PATTERNS.items():
            for r in range(reps):
                phase = 254.0 + (r * 83.0) % 250.0
                yield (f"eps{eps:+.3f}", name, payload, eps, 0.0, phase)
    # within-capture drift at the slow corner
    for name, payload in PATTERNS.items():
        for r in range(reps):
            phase = 254.0 + (r * 83.0) % 250.0
            yield ("eps-0.075+drift", name, payload, -0.075, 0.002, phase)


# ------------------------------------------------------------------ checks

def _merged_loops(samples) -> int:
    """Loops whose slot-7 sample and the next loop's slot-0 sample are
    both HIGH, i.e. the inter-bit low swallowed by the end-of-loop gap.
    This is the '1-bit merging' statistic the calibration reports."""
    lut = {(i, s): v for i, s, v in samples}
    return sum(1 for (i, s), v in lut.items()
               if s == 7 and v and lut.get((i + 1, 0)) == 1)


def _stats(samples):
    from harness import high_pulses
    return (len(high_pulses(samples)),          # high pulses seen
            _merged_loops(samples),             # merged (1-bit) loops
            sum(v for _, _, v in samples))      # HIGH samples


# Per-capture nuisance ranges: t0 and eps as recovered by the calibration
# fit over the 54 real captures (t0 254..501 ns, eps -1.147%..-1.096%).
_PHASE_LO, _PHASE_HI = 200.0, 560.0
_EPS_LO, _EPS_HI = -0.01150, -0.01090


_FIT_ITER = 100          # frame = 192 bits = 240 us ~= 96 loops

PULSE_TOL = 3.0          # pass band on the mean high-pulse count per pattern
MERGE_TOL = 0.20         # pass band on the mean merged-loop count (relative)


def _align(real_levels, payload):
    """Recover (phase_ns, eps) for one real capture by maximizing raw
    sample agreement over the frame window. Only the two nuisance
    parameters the brief allows (t0, eps) are free; every sampler
    constant stays fixed."""
    fr = frame(payload)
    bits = [int(b) for byte in fr for b in f"{byte:08b}"]
    ref = real_levels[:_FIT_ITER * 8]

    def agree(ph, eps):
        syn = _simulate(bits, eps, 0.0, ph, _FIT_ITER)
        return sum(1 for (_, _, a), b in zip(syn, ref) if a == b)

    best = (-1, 0.0, 0.0)
    for j in range(13):                                   # eps step 5e-5
        eps = _EPS_LO + (_EPS_HI - _EPS_LO) * j / 12.0
        ph = _PHASE_LO
        while ph <= _PHASE_HI:                            # phase step 10 ns
            a = agree(ph, eps)
            if a > best[0]:
                best = (a, ph, eps)
            ph += 10.0
    # pattern search with shrinking steps
    a0, ph0, eps0 = best
    sp, se = 8.0, 4e-5
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
    n_win = len(ref)
    syn = _simulate(bits, eps0, 0.0, ph0, N_ITER)
    full = sum(1 for (_, _, a), b in zip(syn, real_levels) if a == b)
    return ph0, eps0, full, a0 / n_win


def validate():
    """Rebuild every real capture with the fitted sampler model and
    compare pulse statistics, at the bench operating point.

    For each real capture only the two per-capture nuisance parameters
    the task brief allows (t0 = phase_ns, eps) are recovered by maximizing
    raw sample agreement; all sampler constants above are held fixed.

    A pattern passes when the mean synthetic high-pulse count is within
    PULSE_TOL of the mean real one, and - where the pattern actually
    merges 1-bits - the mean merged-loop count is within MERGE_TOL.
    dmax (worst single capture) is printed alongside so a pattern that
    passes on the mean but has one poorly reproduced capture is visible.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from harness import load_dataset, linearize

    _, caps = load_dataset()
    by_pat = {}
    for c in caps:
        by_pat.setdefault(c["pattern"], []).append(c)

    print("Synthetic sampler model vs the 54 real captures "
          "(bench point, per-capture t0/eps only)")
    print(f"  loop {LOOP_NS:.1f} ns, slots {SLOT_OFFSET_NS}")
    print(f"  branch cost {BRANCH_COST_NS}, T1H {T1H_NS:.0f} ns, "
          f"T0H {T0H_NS:.0f} ns")
    print()
    print(f"{'pattern':11s} {'pulses real':>12s} {'synth':>9s} {'dmean':>6s} "
          f"{'dmax':>5s}  {'merged real':>12s} {'synth':>9s}  {'agree':>7s}  "
          f"verdict")
    print("-" * 92)

    n_ok = n_tot = 0
    worst_d = 0
    worst_dm = 0.0
    worst_agree = worst_wagree = 1.0
    agree_num = 0.0
    agree_den = 0
    ones_real = ones_syn = None
    for pat in PATTERNS:
        reps = by_pat.get(pat, [])
        if not reps:
            continue
        r_np, r_mg, s_np, s_mg, agrs, wagrs = [], [], [], [], [], []
        for c in reps:
            real = linearize(c["capture"])
            payload = bytes.fromhex(c["payload"])
            lv = [v for _, _, v in real]
            ph, eps, na, wrate = _align(lv, payload)
            syn = synth_capture(payload, eps=eps, phase_ns=ph)
            rs, ss = _stats(real), _stats(syn)
            r_np.append(rs[0]); r_mg.append(rs[1])
            s_np.append(ss[0]); s_mg.append(ss[1])
            agrs.append(na / len(lv)); wagrs.append(wrate)
        dmax = max(abs(a - b) for a, b in zip(r_np, s_np))
        dmean = abs(sum(r_np) - sum(s_np)) / len(r_np)
        ok = dmean <= PULSE_TOL
        note = "" if ok else f" (pulse count off by {dmean:.1f})"
        merge_ref = sum(r_mg) / len(r_mg)
        if merge_ref >= 5.0:              # only meaningful where 1-bits merge
            mdev = abs(sum(r_mg) - sum(s_mg)) / len(r_mg) / merge_ref
            if mdev > MERGE_TOL:
                ok = False
                note += f" (merged off by {mdev:.0%})"
        if pat == "ones":
            ones_real, ones_syn = r_mg, s_mg
        n_ok += int(ok); n_tot += 1
        worst_d = max(worst_d, dmax)
        worst_dm = max(worst_dm, dmean)
        worst_agree = min(worst_agree, min(agrs))
        worst_wagree = min(worst_wagree, min(wagrs))
        agree_num += sum(agrs); agree_den += len(agrs)
        print(f"{pat:11s} {_rng(r_np):>12s} {_rng(s_np):>9s} {dmean:6.1f} "
              f"{dmax:5d}  {_rng(r_mg):>12s} {_rng(s_mg):>9s}  "
              f"{min(agrs):6.2%}  {'MATCH' if ok else 'MISMATCH'}{note}")

    print("-" * 92)
    print(f"{n_ok}/{n_tot} patterns match  (mean pulse count within "
          f"{PULSE_TOL:g}; merged-loop count within {MERGE_TOL:.0%})")
    print(f"worst per-pattern mean pulse deviation  : {worst_dm:.1f}")
    print(f"worst single-capture pulse deviation    : {worst_d}")
    print(f"mean sample agreement (all samples)     : "
          f"{agree_num / agree_den:.4%}")
    print(f"worst per-capture agreement (all)       : {worst_agree:.3%}")
    print(f"worst per-capture agreement (frame win) : {worst_wagree:.3%}")
    print(f"'ones' merged loops  real {ones_real} -> synth {ones_syn}")
    verdict = "MODEL VALIDATED" if n_ok == n_tot else "MODEL MISMATCH"
    print(f"-> {verdict}")
    return n_ok == n_tot


def _rng(vals):
    lo, hi = min(vals), max(vals)
    return f"{lo}" if lo == hi else f"{lo}-{hi}"


if __name__ == "__main__":
    raise SystemExit(0 if validate() else 1)
