"""LEVER B characterization library -- DEAD-WINDOW census, host only.

A bit's DISCRIMINATING INTERVAL is the wire-time window
    ( base_t + T0H_eff , base_t + T1H_eff ]
after its own rising edge (base_t = BIAS_U + t*BIT_U).  It is the only
place a sample can tell 0 from 1: below it the line is high either way,
above it low either way.  When no sample lands there the width bracket
admits BOTH hypotheses and the decision is a coin flip -- yet the
per-bit margin (distance of the fall bracket from the 0/1 boundary) can
be arbitrarily large, which is the R6 "confidently wrong" mechanism.

Two detectors, measured against each other:

  A) BRACKET rule (O(1) per bit, integer, no rescan) -- inside the
     decision pass, with the segment's own fall bracket (u, v] and the
     family-calibrated boundaries h0c/h1c:
         dead(off)  <=>  u < off*BIT_U + h0c   AND   off*BIT_U + h1c <= v
     i.e. the bracket strictly CONTAINS the whole discriminating
     interval, so no sample can be inside it (fa/fb are adjacent
     samples).

  B) SAMPLE CENSUS (O(samples), reference only) -- map every capture
     sample to wire TU with the decoder's own (K, tau) and ask whether
     any lands in the interval.  This is sweeplib.bit_visibility's
     concept, done in the decoder's integer frame instead of the
     simulator's float one.

Nothing here is shipped; it exists to produce the TASK-1 bound.
"""
import importlib.util
import sys
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "bench"))


def load_ref():
    spec = importlib.util.spec_from_file_location(
        "embedded_v2_dw", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sample_times(e, samples, K, tau):
    """[(bit_index, within_bit_offset_TU, level)] for every capture sample,
    in the decoder's own integer frame.  wsum reproduces _pulse_stream's
    data-dependent branch-cost accumulation EXACTLY (same order, same
    saturation), so the times are the ones the decoder would compute."""
    out = []
    wsum = 0
    for (i, s, v) in samples:
        t = e._u16(i * e.LOOP_CY + e.O_CY[s] + wsum)
        if v:
            wsum += e.W_CY[s]
        y = e._map(t, K, tau) - e.BIAS_U
        if y < 0:
            out.append((-1, 0, v))
            continue
        out.append((y >> e.BIT_SH, y & (e.BIT_U - 1), v))
    return out


def census_dead(e, samples, K, tau, nb, h0=None, h1=None):
    """Detector B: set of bit indices whose discriminating interval got no
    sample.  h0/h1 default to the NOMINAL H0P/H1P (377/752 ns)."""
    h0 = e.H0P if h0 is None else h0
    h1 = e.H1P if h1 is None else h1
    seen = bytearray(nb)
    for (k, off, _v) in sample_times(e, samples, K, tau):
        if 0 <= k < nb and h0 < off <= h1:
            seen[k] = 1
    return {k for k in range(nb) if not seen[k]}


def decide_pass_instrumented(e, samples, K, tau, cal):
    """_decide_pass (SS6.2, verbatim logic) + per-bit instrumentation.

    Returns the ordinary state dict plus:
      marg[t]      per-bit margin as the decoder computes it (u8)
      dead_br[t]   detector A, the O(1) bracket rule
      seg_of[t]    (k0, k1, fam, a_hat, u, v) of the segment owning t
      nsamp[t]     samples inside t's discriminating interval (audit)
    """
    NB = e.NB
    bits = [0] * NB
    marg = [None] * NB
    dead_br = [False] * NB
    seg_of = [None] * NB
    infeasible = 0
    label_err = 0
    n_seg = 0
    cand_t, cand_m = [], []
    n_weak = n_tied = 0
    chk_conf = [0] * e.CHK_LEN
    tie_pend = -1
    nd8 = 8 * e.N_DATA
    for (k0, k1, u, v, fam) in e._seg_stream(samples, K, tau):
        n_seg += 1
        if k0 >= NB:
            continue
        a_hat, c_hat, costs, lo, hi, inter, a_free = e._decide(
            k0, k1, u, v, fam, cal)
        if c_hat > e.INFEAS_U:
            infeasible += 1
        known_all = all(e.KNOWN[t] >= 0 for t in range(k0, min(k1, NB)))
        dead = sum(1 for x in inter if x) >= 2
        if known_all and lo == hi and a_free != lo and not dead:
            label_err += 1
        tie_here = -1
        ins = [a for a in range(lo, hi + 1) if inter[a]]
        if len(ins) >= 2 and a_hat in ins[:2]:
            t = k0 + ins[0]
            if t < NB:
                tie_here = t
        h0c, h1c = cal.h0f[fam], cal.h1f[fam]
        kk1 = min(k1, NB)
        for t in range(k0, kk1):
            off = t - k0
            bits[t] = 1 if off < a_hat else 0
            hb = off * e.BIT_U
            dead_br[t] = (u < hb + h0c) and (hb + h1c <= v)
            seg_of[t] = (k0, k1, fam, a_hat, u, v)
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            if c0 is None or c1 is None:
                m = 255
            else:
                m = min(255, abs(c0 - c1))
            if t == tie_here or t == tie_pend:
                m = 0
            marg[t] = m
            if e.PP_LO <= t < e.PP_HI:
                k = t - e.PP_LO
                if k >= nd8:
                    chk_conf[(k - nd8) >> 3] = e._u16(
                        chk_conf[(k - nd8) >> 3] + m)
                if m <= e.MG_MAX:
                    n_weak = e._u16(n_weak + 1)
                    if m == 0:
                        n_tied = e._u16(n_tied + 1)
                    e._cand_insert(cand_t, cand_m, e._u16(k), e._u8(m))
        if tie_pend >= 0 and tie_pend < kk1:
            tie_pend = -1
        if tie_here >= kk1:
            tie_pend = tie_here
    return dict(bits=bits, infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, cand_t=cand_t, cand_m=cand_m,
                n_weak=n_weak, n_tied=n_tied, chk_conf=chk_conf,
                marg=marg, dead_br=dead_br, seg_of=seg_of)


def analyze(e, samples, truth_bits):
    """Full decode + per-bit census.  Returns None if the lock fails."""
    seed = e._seed(samples)
    if seed is None:
        return None
    K, tau, np_ = seed
    for _ in range(2):
        K, tau = e._refine(samples, K, tau)
    cal = e._calibrate(samples, K, tau)
    st = decide_pass_instrumented(e, samples, K, tau, cal)
    st["K"], st["tau"] = K, tau
    st["dead_cen"] = census_dead(e, samples, K, tau, e.NB)
    bits = st["bits"]
    wrong = [t for t in range(e.PP_LO, e.PP_HI) if bits[t] != truth_bits[t]]
    st["wrong"] = wrong
    st["wrong_mk"] = [t for t in range(e.NB)
                      if e.KNOWN[t] >= 0 and bits[t] != e.KNOWN[t]]
    return st
