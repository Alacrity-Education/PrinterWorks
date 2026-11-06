"""combined -- WS2812 reconstruction decoder composed from the six technique designs.

ARCHITECTURE (pipeline; the design each stage is taken from is in [brackets])

  0. Sampler model clock A[m]                     [missed_zero / edge_dp / dev_calibration]
       A[m] = i*G + o[slot] + sum_j w[j]*highs_so_far[j] -- a pure function of the
       observed data with exactly two per-capture unknowns (scale kappa, offset
       tau).  TWO global model configs are decoded and arbitrated blindly:
       "cal" = dev_calibration's earlier final.json fit (G=2525.89, fitted o[],
       the data-dependent w feedback), which measures as the better *width-call*
       model on the real bench captures, and "fit" = the shipped
       dev_calibration/fitted_model.json (loaded from disk; integer-cycle
       geometry, 99.96 percent sample agreement), which is exact for synth.py
       and carries the envelope.  Model choice is per capture, on decision-
       quality statistics only (below) -- never on raw fit scores, which are
       not comparable across coordinate systems.
  1. High-runs -> rise/fall brackets              [missed_zero]
       Edges are intervals, never midpoints (midpoints inject the pattern-
       correlated bias measured by clock_stretch E1 and boundary_model -- and,
       measured here, midpoint residuals actively PREFER the 43/40 rational
       alias at the fast HSI corner).
  2. Blind edge-bracket lock over (kappa, tau)    [missed_zero's rise Hough +
       clock_stretch stage 2a interval-censored cost, alias retry from its stage 5]
       Every WS2812 bit begins with a rise on the exact 1250 ns lattice; falls
       aim at k*BIT + {h0, h1}.  Score = (#rise brackets straddling a lattice
       point, then -sum of clipped hinge^2 violations of rises and falls).  The
       fall term is what breaks lattice-commensurate false locks.  Coarse grid
       kappa in [0.88, 1.12] (past +-8 percent HSI); top coarse peaks kept as
       alias candidates (one-bit-slip aliases are only ~0.5 percent away).
  3. Gap-accounting segmentation                  [missed_zero -- measured 100 percent
       exact on real data and across the +-8 percent synthetic envelope]
       n[j] = cumulative round(delta_rise/1250).  Merge-prefix bits are 1 (T0L
       exceeds every dead zone in the envelope, so a 0-bit never merges), hidden
       bits are 0 (a 1-bit is never fully swallowed: 0/4863 measured).  KEY
       SIMPLIFICATION found while composing: hypotheses (s,b)=(a,1) and (a+1,0)
       emit IDENTICAL bit patterns 1^a 0^*, so the only payload-relevant decision
       per pulse is a = its number of leading 1-bits; the generator ambiguity is
       priced by taking the min cost over both generators.
  4. Marker forcing + hierarchical per-capture calibration
                                                  [histogram_adaptive S7 supervised
       refit; matched_filter's "anchors are overdetermined" evidence]
       Pulses fully inside the known header/trailer have a FORCED leading-ones
       count -- ~60 labelled fall brackets per capture.  Fitted per capture, all
       interval-censored with shrinkage to the model priors: effective high
       widths h0c/h1c (absorbs the wire-vs-sampler template question without
       ground truth), one phase-like offset psi[s] per slot (slots couple across
       bracket families: slot 6 is the v-side of family (5,6) and the u-side of
       (6,7)), and a per-bracket-family boundary shift eps_f from the largest
       label-feasible gap in the family's pooled fall-bit phases (guarded
       against crawling-phase sweeps that fill the zone uniformly).  A second
       pass adds confident payload pulses as labels (self-training).
  5. Per-pulse scoring: interval-censored probit  [edge_dp emission model with
       per-slot fall widths WE[s]; boundary_model's slot-reliability evidence]
       cost(a) = -log Phi((H-u)/W_a) - log Phi((v-H)/W_b) where (u,v] is the
       fall bracket, H the hypothesised high duration, W_x = per-slot fall
       probit width (slot 7 wide = its measured one-sided early-low bias) plus
       a small common-mode term.  Inside the bracket the cost is ~0 (interval
       censoring); the tails only arbitrate near-ties.  DEAD WINDOWS -- both
       widths strictly inside the bracket, i.e. the discriminating interval was
       never sampled -- get a fewer-ones prior instead of trusting tail noise
       (measured: ~82 percent of dead bits are 0, histogram_adaptive 40/49),
       then a byte-period vote of the confident bits at t +- 8, 16 may
       overrule the prior.  KNIFE BITS -- (5,6)-family single-bit pulses
       whose probit margin is sub-KNIFE_LLR, i.e. inside the few-ns boundary
       uncertainty -- likewise defer to the byte-period vote, but only per
       lag whose periodicity the capture's own confident payload PROVES at
       >= 0.99 agreement (periodic test patterns measure exactly 1.000 on
       their lag; random payloads 0.40-0.55, so the gate abstains there).
  6. Assembly under hard constraints + per-bit LLRs
                                                  [missed_zero + histogram_adaptive
       constraint set: exactly 192 bits, header FF 00 AA 65, trailer 9A 55 00 FF
       forced; merge-prefix/hidden bits pinned]
  7. Blind validation, alias retry, model arbitration   [clock_stretch stage 5]
       Within a model: Q = (marker violations, infeasible pulses, label errors,
       psi-clamp hits, -hough hits, total cost) ranks the alias candidates
       (a psi pinned at the +-PSI_SPAN search edge marks a degenerate slot
       fit and demotes the alias; no clean winner pins one).  Across models:
       switch only on clear improvement of (violations, infeasible), a label-
       error margin >= 2, or (label errors within 1) a dead-window count lower
       by >= 4 -- the count of never-sampled windows is the tell of a warped
       time base whose markers happen to look clean.  (A bit-wise cross-model
       override was tried and measured net-negative -- the two models' marginal
       errors do not decorrelate favourably -- and removed.)
  8. Corruption handling (audit hardening)
       a. Bit-index RE-REGISTRATION: the first surviving pulse keeps its
          absolute lattice index (slip0) instead of being pinned to bit 0, so
          a capture whose leading loops are missing still decodes; header bits
          before the first pulse are reconstructed from KNOWN (they carry no
          payload) and excluded from the violation count.
       b. Bounded REPAIR RETRIES when the blind quality stats blow up: merge a
          pulse split by a single flipped-low sample (the fragments are joined
          across an exactly-one-sample low gap whose second rise is off the
          bit lattice), drop an isolated one-sample pulse with both edges off
          the lattice (a flipped-high sample), and re-register with a small
          positive integer bit shift (a renumbered/truncated capture whose
          marker constraints land off the pulses).  Every candidate repair is
          accepted only if the blind Q strictly improves; at most
          REPAIR_MAX_ROUNDS greedy rounds.
       c. HONEST REFUSAL: decode() returns None instead of a confident wrong
          payload when the winner still violates the markers, has payload bits
          before the first surviving pulse, or exceeds the calibrated gates on
          infeasible pulses / marker label errors (clean captures measure
          infeasible = 0 and label_err <= 2; corrupted ones measure 15-185 and
          11-31 -- the gates sit between with wide margins on both sides).
          A TRUNCATED capture (bits reconstructed before the first surviving
          pulse) additionally refuses when any (5,6) knife-zone payload bit
          was left unresolved by the byte-period vote with margin below
          TRUNC_KNIFE_LLR: truncation depletes the marker labels and swings
          the fitted boundary ~10 ns, so such bits are coin flips there
          (measured: a dropped loop flips them at |llr| 1.0-1.4 while every
          truncation-decodable capture's are 1.7+ or vote-resolved).  Clean
          captures always have cover0 = 0 and never hit this gate.

WHAT WAS REJECTED, AND WHY
  - edge_dp's full (phase x slope) trellis: its own diagnosis shows 0 search
    failures and 30 model failures -- the trellis needs external evidence, not a
    better search.  With missed_zero's exact segmentation the per-bit decisions
    decouple given the time base, so the trellis reduces to the per-pulse argmin
    used here; its emission model (per-slot probit widths) is kept.  Its slope
    state was measured by its own author to buy nothing (29 vs 30 / 54) at 5x cost.
  - clock_stretch's Kalman tracker / PLL, and any local phase tracker: E2 shows
    within-capture wander is 0.0012 percent and a loop filter tracks slot-mix
    bias, not clock.  Confirmed here the hard way: a windowed rise-residual
    drift tracker moved train from 25/36 to 21/36 and was removed.  The global
    2-parameter interval-censored fit is the ML answer.
  - edge_dp's per-slot fall time OFFSETS as constants (WD): calibrated to its
    own time base, they overshoot this one (measured swing from truth=0-family
    errors to truth=1-family errors).  Replaced by the per-capture psi[s] /
    eps_f fits from marker labels, which are blind and self-consistent.
  - matched_filter's global (t0,kappa) anchor correlation as the time base: on
    real captures it is grid-limited (15 percent BER decidable with the best
    affine grid); the edge-bracket lock needs no slot calibration beyond the
    model clock.  Its per-cell template scoring is subsumed by the fall-bracket
    probit (the bracket is the sufficient statistic for the fall given the
    monotone run structure); its erasure concept survives as the dead-window
    prior, and its "impossible-sample" veto as the infeasible-pulse count.
  - histogram_adaptive's local 7-cell tracker (chases level-dependent loop
    stretching in a nominal coordinate; the model clock carries that feedback
    explicitly as w) and its 192-bit repair DP (unnecessary once n[] is exact --
    the count constraint holds by construction).  Kept: its supervised
    threshold refit, per-capture adaptivity, hard marker constraints, and the
    decorrelated-second-opinion role, realised here as the second sampler model.
  - boundary_model's per-loop free phase (needs rising edges exactly where
    merges remove them; subsumed by w + the affine fit).  Kept: its
    slot-reliability story (via WE), and its "no gap can hide a whole bit"
    bound which gap-accounting segmentation relies on.
  - Any use of harness.LOOP_NS = 2507.3 as a time base (all six designs measured
    it high), bracket midpoints as phase references, per-capture slot-offset
    fitting from scratch (exactly degenerate at L = 2*BIT, clock_stretch E4),
    and decision-directed sample-agreement refits (missed_zero: 26 -> 24/54).

KNOWN LIMITS (measured): the decoder is at the information ceiling of dead
windows and knife bits.  At the bench point ~0.4 percent of bits are genuinely
unobserved in the discriminating interval; the one remaining tuning-set miss
(rnd2_0) is two knife bits whose truth-consistent boundary window is ~1-2 ns
wide -- far below the 38 ns slot-5 sampling noise -- and squeezed against one
of the capture's own marker-labelled 1-falls, in an aperiodic payload the
vote's periodicity gate rightly refuses to guess about.  On the synthetic
envelope the fitted sampler's data-dependent feedback creates a period-2
attractor at large |eps| where up to half the payload windows are never
sampled; those bits are irrecoverable coin flips for any decoder, so corner
exact rates are ceiling-bound while byte accuracy stays high.

decode(samples, meta) -> 16 payload bytes | None.   Deterministic, no ground truth.
"""

import math

try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

BIT = 1250.0
NB = 192
TAIL_NS = 400.0        # drop pulses whose rise maps past NB*BIT + this (latch tail)
S_CAP = 12             # max bits one pulse may span (measured max 2; generous cap)
INFEAS_NATS = 8.0      # min pulse cost above this => "infeasible pulse" (quality)
TB_NS = 12.0           # common-mode time-base jitter, added in quadrature to WE
SIG_FIT = 45.0         # interval-censored h fit: hinge scale (missed_zero sigma)
SHRINK_NS = 60.0       # h fit shrinkage toward the model prior
CLIP_FIT = 150.0       # h fit hinge clip (robustness to a mislabel)
BIG = 50.0             # LLR saturation
DEAD_PRIOR_NATS = 0.45  # fallback prior against extra ones on a dead window
                        # (stands only when the byte-period vote abstains)

# --- honest-refusal gates (decode -> None), calibrated on the 54-capture
# --- set: clean winners measure violations=0, infeasible=0, label_err<=2;
# --- corrupted inputs measure infeasible 15-185, label_err 11-31.
GATE_VIOL = 0           # any marker violation after leading-mask -> refuse
GATE_INFEAS = 4         # max infeasible pulses accepted (clean max: 0)
GATE_LABERR = 6         # max marker label errors accepted (clean max: 2)
GATE_COVER = 32         # first pulse past bit 32 -> payload truncated -> refuse

# --- bounded repair retries (only attempted when blind Q is already bad:
# --- clean captures never reach them)
REPAIR_Q_INFEAS = 1     # repair triggers above this infeasible count
REPAIR_Q_LABERR = 3     # ... or above this label-error count (clean max: 2)
REPAIR_MAX_ROUNDS = 4   # greedy repair rounds (>= flips we can unwind)
REPAIR_TOP = 2          # merge/drop candidates tried per round
SHIFT_MAX = 6           # re-registration shifts tried (integer bits)

HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")


def _bits_of(bs):
    return [(byte >> (7 - i)) & 1 for byte in bs for i in range(8)]


KNOWN = [-1] * NB
KNOWN[0:32] = _bits_of(HDR)
KNOWN[160:192] = _bits_of(TRL)

# Per-slot fall probit widths (ns), fitted by the edge_dp design (d_edge.py).
# (Its per-slot fall *offsets* were tried and rejected: they are calibrated to
# edge_dp's time base and overshoot this one -- the per-capture per-family
# width fits below supply the offsets instead, blind, from the marker labels.)
WE = (32.0, 24.0, 28.0, 18.0, 12.0, 38.0, 26.0, 46.0)

# Near-tie window (audit hardening): 0.0 -- ties flow through the fitted
# per-family boundary (eps / the (5,6) probit regression), the knife-bit
# byte-period vote, and, on dead windows, the explicit dead-window prior +
# byte-period vote, instead of a blanket fewer-ones margin.  The former
# 0.15-nat fewer-ones window was a knife-edge coincidence: it blunted the
# fitted boundary by ~5-7 ns (0.15 nats at the probit tie slope),
# overriding boundary calls it should not.  Measured after the hardening:
# every value in [0.0, 0.15] scores identically (the mechanisms above now
# carry those bits) and 0.2+ regresses random payloads -- 0.0 is the
# plateau point farthest from the cliff and the only non-arbitrary one.
TIE_NATS = 0.0

# Hierarchical width fit: global (all labels) then per bracket-family
# (slot-of-last-high, slot-of-first-low), shrunk toward the global fit.
FAM_SHRINK_NS = 45.0
FAM_MIN_LAB = 2

# Sampler model configs.  The primary model is dev_calibration's
# fitted_model.json (99.963 percent sample agreement on the real captures;
# loaded from disk when present, hard-coded mirror otherwise).  Its loop
# folds the bench HSI point, so per-capture kappa comes out ~1.0 on real
# data.  A second, older calibration (final.json) is kept as a fallback
# hypothesis: the blind quality score picks per capture.
_FITTED = dict(
    name="fit",
    G=2500.0,
    O=(0.0, 250.0, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0),
    W=(0.0, -62.5, 0.0, 125.0, 0.0, 0.0, 0.0, 62.5),
    H0=377.0, H1=752.0)


def _load_fitted():
    try:
        import json
        from pathlib import Path
        p = (Path(__file__).parent / "dev_calibration" /
             "fitted_model.json")
        d = json.loads(p.read_text())
        return dict(name="fit",
                    G=float(d["loop_ns"]),
                    O=tuple(float(x) for x in d["slot_offsets_ns"]),
                    W=tuple(float(x) for x in d["branch_cost_ns"]),
                    H0=float(d["eff_high_0_ns"]),
                    H1=float(d["eff_high_1_ns"]))
    except Exception:
        return dict(_FITTED)


MODELS = (
    dict(name="cal",
         G=2525.893636592406,
         O=(61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0, 1727.0, 2000.0),
         W=(0.0, -62.5, 0.0, 125.0, 0.0, 0.0, 0.0, 62.5),
         H0=339.25, H1=737.25),
    _load_fitted(),
)

# Hough search (kappa relative to the model grain; covers past +-8 percent HSI).
K_LO, K_HI, K_STEP = 0.88, 1.12, 5e-4
TAU_LO, TAU_HI, TAU_STEP = -400.0, 620.0, 20.0
FINE = ((5e-4, 41, 60.0, 31), (1e-4, 41, 12.0, 31), (2e-5, 41, 3.0, 31))
N_ALIAS = 3

_SQRT2 = math.sqrt(2.0)
_LOG_SQRT_2PI = 0.9189385332046727


def _log_ndtr(z):
    """log of the standard normal CDF, stable for large |z|."""
    if z > 8.0:
        return 0.0
    if z > -20.0:
        return math.log(0.5 * math.erfc(-z / _SQRT2))
    return -0.5 * z * z - math.log(-z) - _LOG_SQRT_2PI


# ---------------------------------------------------------------- stage 0+1

def _model_clock_pulses(samples, model):
    """Model clock A[m] plus high-run pulse brackets.

    Returns list of pulses:
      (ra, rb, fa, fb, slot_fa, slot_fb, n_high, slot_ra, slot_rb, m0, m1)
    with ra/rb the rise bracket and fa/fb the fall bracket in model-ns and
    m0/m1 the sample indices of the first/last high sample (repair retries
    need them to find one-sample low gaps).
    """
    G = model["G"]
    O = model["O"]
    W = model["W"]
    widx = [j for j in range(8) if W[j] != 0.0]
    run = [0] * 8
    A = []
    lv = []
    sl = []
    for (i, s, v) in samples:
        a = i * G + O[s]
        for j in widx:
            a += W[j] * run[j]
        A.append(a)
        lv.append(v)
        sl.append(s)
        run[s] += v
    pulses = []
    M = len(A)
    m = 0
    while m < M:
        if lv[m]:
            m0 = m
            while m + 1 < M and lv[m + 1]:
                m += 1
            m1 = m
            ra = A[m0 - 1] if m0 > 0 else A[0] - 250.0
            sra = sl[m0 - 1] if m0 > 0 else sl[0]
            rb = A[m0]
            fa = A[m1]
            if m1 + 1 < M:
                fb = A[m1 + 1]
                sfb = sl[m1 + 1]
            else:
                fb = A[m1] + 250.0
                sfb = sl[m1]
            pulses.append((ra, rb, fa, fb, sl[m1], sfb, m1 - m0 + 1,
                           sra, sl[m0], m0, m1))
        m += 1
    return pulses


# ------------------------------------------------------------------ stage 2

HINGE_CLIP = 562.5      # 0.45 * BIT, per clock_stretch
W_FALL = 0.5            # weight of the fall-hinge term vs the rise term


def _hough_candidates(pulses, h0p, h1p):
    """Blind (kappa, tau) fit on the edge brackets; returns up to N_ALIAS
    refined candidates [(kappa, tau, hits, cost)] best-first.

    Objective (clock_stretch stage 2a): interval-censored -- a bracket
    costs nothing while its lattice target lies anywhere inside it; the
    residual is the CLEARANCE VIOLATION, never a midpoint distance
    (midpoints are biased and actually prefer the 43/40 rational alias at
    the fast HSI corner).  Falls aim at k*BIT + {h0, h1}, which is what
    breaks lattice-commensurate false locks."""
    ra = [p[0] for p in pulses]
    rb = [p[1] for p in pulses]
    fa = [p[2] for p in pulses]
    fb = [p[3] for p in pulses]
    if _np is not None:
        return _hough_np(_np.asarray(ra), _np.asarray(rb),
                         _np.asarray(fa), _np.asarray(fb), h0p, h1p)
    return _hough_py(ra, rb, fa, fb, h0p, h1p)


def _cost_np(ra, rb, fa, fb, h0p, h1p, k, ts):
    """(hits, cost) arrays over the tau vector ts, one kappa."""
    lo = k * ra[None, :] + ts[:, None]
    hi = k * rb[None, :] + ts[:, None]
    rm = (lo + hi) * 0.5
    mask = rm < NB * BIT + TAIL_NS
    g = _np.round(rm / BIT) * BIT
    hinge = _np.maximum(0.0, _np.maximum(lo - g, g - hi))
    hit = (hinge == 0.0) & mask
    hits = hit.sum(axis=1)
    _np.minimum(hinge, HINGE_CLIP, out=hinge)
    cost = ((hinge * hinge) * mask).sum(axis=1)
    flo = k * fa[None, :] + ts[:, None]
    fhi = k * fb[None, :] + ts[:, None]
    fm = (flo + fhi) * 0.5
    fh = None
    for t in (h0p, h1p):
        gt = _np.round((fm - t) / BIT) * BIT + t
        h1_ = _np.maximum(0.0, _np.maximum(flo - gt, gt - fhi))
        fh = h1_ if fh is None else _np.minimum(fh, h1_)
    _np.minimum(fh, HINGE_CLIP, out=fh)
    cost += W_FALL * ((fh * fh) * mask).sum(axis=1)
    return hits, cost


def _hough_np(ra, rb, fa, fb, h0p, h1p):
    kappas = _np.arange(K_LO, K_HI + 1e-12, K_STEP)
    taus = _np.arange(TAU_LO, TAU_HI + 1e-9, TAU_STEP)
    prof = []
    for k in kappas:
        hits, cost = _cost_np(ra, rb, fa, fb, h0p, h1p, float(k), taus)
        idx = int(_np.argmax(hits * 1e12 - cost))
        prof.append((int(hits[idx]), float(cost[idx]), float(taus[idx])))
    hits_arr = [p[0] for p in prof]
    # peak picking with exclusion window (aliases are ~5e-3 apart in kappa)
    order = []
    taken = [False] * len(kappas)
    win = max(1, int(round(0.0025 / K_STEP)))
    scored = sorted(range(len(kappas)),
                    key=lambda i: (hits_arr[i], -prof[i][1]), reverse=True)
    for i in scored:
        if taken[i]:
            continue
        order.append(i)
        for j in range(max(0, i - win), min(len(kappas), i + win + 1)):
            taken[j] = True
        if len(order) >= N_ALIAS + 1:
            break

    def refine(k0, t0):
        k, t = k0, t0
        hits, cost = -1, 0.0
        for dk, nk, dt, nt in FINE:
            ks = _np.linspace(k - dk, k + dk, nk)
            ts = _np.linspace(t - dt, t + dt, nt)
            bestv = None
            for kk in ks:
                h, c = _cost_np(ra, rb, fa, fb, h0p, h1p, float(kk), ts)
                idx = int(_np.argmax(h * 1e12 - c))
                v = (int(h[idx]), -float(c[idx]), float(ts[idx]), float(kk))
                if bestv is None or v[:2] > bestv[:2]:
                    bestv = v
            hits, nc, t, k = bestv
            cost = -nc
        return k, t, hits, cost

    cands = []
    for i in order:
        k, t, h, c = refine(float(kappas[i]), prof[i][2])
        dup = False
        for (k2, t2, h2, c2) in cands:
            if abs(k2 - k) < 2e-4 and abs(t2 - t) < 40.0:
                dup = True
                break
        if not dup:
            cands.append((k, t, h, c))
    cands.sort(key=lambda cd: (-cd[2], cd[3]))
    return cands[:N_ALIAS]


def _hough_py(ra, rb, fa, fb, h0p, h1p):  # pragma: no cover - slow fallback
    P = len(ra)

    def score(k, t):
        hits = 0
        cost = 0.0
        for j in range(P):
            lo = k * ra[j] + t
            hi = k * rb[j] + t
            rm = (lo + hi) * 0.5
            if rm >= NB * BIT + TAIL_NS:
                continue
            g = round(rm / BIT) * BIT
            hg = max(0.0, lo - g, g - hi)
            if hg == 0.0:
                hits += 1
            cost += min(hg, HINGE_CLIP) ** 2
            flo = k * fa[j] + t
            fhi = k * fb[j] + t
            fm = (flo + fhi) * 0.5
            fh = None
            for tt in (h0p, h1p):
                gt = round((fm - tt) / BIT) * BIT + tt
                hh = max(0.0, flo - gt, gt - fhi)
                fh = hh if fh is None else min(fh, hh)
            cost += W_FALL * min(fh, HINGE_CLIP) ** 2
        return hits, cost

    best = None
    k = K_LO
    while k <= K_HI:
        t = TAU_LO
        while t <= TAU_HI:
            h, c = score(k, t)
            v = (h, -c, k, t)
            if best is None or v[:2] > best[:2]:
                best = v
            t += TAU_STEP * 1.25
        k += K_STEP * 2
    k, t = best[2], best[3]
    for dk, nk, dt, nt in FINE:
        bb = None
        for ik in range(nk):
            kk = k - dk + 2 * dk * ik / (nk - 1)
            for it in range(nt):
                tt = t - dt + 2 * dt * it / (nt - 1)
                h, c = score(kk, tt)
                v = (h, -c, kk, tt)
                if bb is None or v[:2] > bb[:2]:
                    bb = v
        k, t = bb[2], bb[3]
    h, c = score(k, t)
    return [(k, t, h, c)]


# ------------------------------------------------------------------ stage 3

def _segment(pulses, kappa, tau, shift=0):
    """Map pulses to wire time, drop the latch tail, assign bit indices.

    Returns list of dicts: k0, k1, u, v, sfa, sfb, nhigh, rise info
      u/v: fall bracket relative to k0*BIT (i.e. total high duration bracket)
    or None if nothing survives.

    RE-REGISTRATION (audit fix 1): the first surviving pulse keeps its
    absolute lattice index slip0 = round(rm/BIT) instead of being pinned to
    bit 0.  On a clean capture slip0 == 0 (the capture triggers on the
    frame's first rise and |tau| < BIT/2 covers the jitter); when leading
    loops are missing the surviving pulses land at their true bit indices
    and the known header bits before them are reconstructed downstream.
    `shift` adds an extra integer bit offset -- a repair retry for captures
    whose sample indices were renumbered so the timing itself carries no
    trace of the truncation (only the marker constraints do)."""
    mapped = []
    for (ra, rb, fa, fb, sfa, sfb, nh, sra, srb, m0, m1) in pulses:
        rm = kappa * (ra + rb) * 0.5 + tau
        if rm >= NB * BIT + TAIL_NS:
            continue
        mapped.append([rm, kappa * fa + tau, kappa * fb + tau, sfa, sfb, nh,
                       (sra, srb)])
    if not mapped:
        return None, 0
    # cumulative integer bit indices (gap accounting; measured 100% exact)
    slip0 = int(round(mapped[0][0] / BIT))
    n = [max(0, slip0)]
    for j in range(1, len(mapped)):
        d = int(round((mapped[j][0] - mapped[j - 1][0]) / BIT))
        n.append(n[-1] + max(0, d))
    # merge pulses that landed on the same bit (a spurious low split a run).
    # `shift` relabels bit indices only (k0/k1/KNOWN); the pulse geometry
    # (u/v/rm_off) stays in the mapped time frame, i.e. against n[j]*BIT.
    out = []
    for j, mp in enumerate(mapped):
        kk = n[j] + shift
        if out and kk == out[-1]["k0"]:
            out[-1]["fw_a"] = mp[1]
            out[-1]["fw_b"] = mp[2]
            out[-1]["sfa"] = mp[3]
            out[-1]["sfb"] = mp[4]
            out[-1]["nhigh"] += mp[5]
            continue
        if kk >= NB:
            continue
        out.append(dict(k0=kk, fw_a=mp[1], fw_b=mp[2],
                        sfa=mp[3], sfb=mp[4], nhigh=mp[5],
                        rm_off=mp[0] - n[j] * BIT, rfam=mp[6]))
    if not out:
        return None, slip0
    for j, p in enumerate(out):
        p["k1"] = out[j + 1]["k0"] if j + 1 < len(out) else NB
        p["u"] = p["fw_a"] - (p["k0"] - shift) * BIT
        p["v"] = p["fw_b"] - (p["k0"] - shift) * BIT
    return out, slip0


# ------------------------------------------------------------------ stage 4

def _a_bounds(k0, k1):
    """Allowed range of a (leading 1-bits) under the KNOWN header/trailer."""
    amin, amax = 0, k1 - k0
    for t in range(k0, min(k1, NB)):
        kb = KNOWN[t]
        if kb == 1:
            amin = max(amin, t - k0 + 1)
        elif kb == 0:
            amax = min(amax, t - k0)
    return amin, amax


def _fit_h(intervals, prior, shrink=SHRINK_NS, min_lab=3, span=130.0):
    """Interval-censored 1-D fit of an effective high width with shrinkage."""
    if len(intervals) < min_lab:
        return prior
    best_h, best_c = prior, None
    h = prior - span
    while h <= prior + span:
        c = ((h - prior) / shrink) ** 2
        for (lo, hi) in intervals:
            hinge = 0.0
            if lo - h > 0.0:
                hinge = lo - h
            if h - hi > hinge:
                hinge = h - hi
            if hinge > CLIP_FIT:
                hinge = CLIP_FIT
            c += (hinge / SIG_FIT) ** 2
        if best_c is None or c < best_c:
            best_c, best_h = c, h
        h += 1.0
    return best_h


# ------------------------------------------------------------------ stage 5

def _cost_a(a, L, u, v, wa, wb, h0c, h1c):
    """(-log P(fall bracket | a leading ones), interior?) over generators.

    interior means the generator's fall lies strictly inside the bracket:
    the observation is then fully explained and any residual cost is the
    probit's soft tail, not data."""
    best = None
    inside = False
    if a == 0:
        H = h0c
        best = -_log_ndtr((H - u) / wa) - _log_ndtr((v - H) / wb)
        inside = u < H <= v
    else:
        H = (a - 1) * BIT + h1c
        best = -_log_ndtr((H - u) / wa) - _log_ndtr((v - H) / wb)
        inside = u < H <= v
        if a < L:
            H = a * BIT + h0c
            c = -_log_ndtr((H - u) / wa) - _log_ndtr((v - H) / wb)
            if c < best:
                best = c
            if u < H <= v:
                inside = True
    return best, inside


def _label_interval(p, a, h0p, h1p):
    """(class, lo, hi) interval for the effective width implied by a labelled
    pulse (a = its known leading-ones count), or None.

    For 0 < a < L both generators (a,1) and (a+1,0) emit the same bits; which
    occurred is decided by the fall bracket (their widths differ by ~875 ns,
    the bracket is < 720 ns wide)."""
    L = p["k1"] - p["k0"]
    u, v = p["u"], p["v"]
    if a == 0:
        return (0, u, v)
    if a == L:
        return (1, u - (L - 1) * BIT, v - (L - 1) * BIT)
    mid = (u + v) * 0.5
    d1 = abs(mid - ((a - 1) * BIT + h1p))
    d0 = abs(mid - (a * BIT + h0p))
    if min(d0, d1) > 600.0:
        return None                       # gross outlier; do not label
    if d1 <= d0:
        return (1, u - (a - 1) * BIT, v - (a - 1) * BIT)
    return (0, u - a * BIT, v - a * BIT)


# DEAD-WINDOW TIE-BREAK (audit fix 3).  The audit proposed a per-family
# prior from the capture's own marker-labelled pulses; MEASURED on all 54
# captures (dev_harden/deadprior_probe*.py) that pool carries no signal:
# every capture's labelled/confident (7,0) pulses are 1-heavy (the
# observable u-slice [h1-gap, h1) only 1-bits can occupy -- a selection
# effect), while the dead-slice truth varies by payload (msb1 u=216 is a
# 1, zeros u=217 is a 0: observationally identical).  The only same-capture
# evidence that separates them is payload STRUCTURE: a dead window is
# resolved by a unanimous byte-period vote over confidently decoded payload
# bits at t +- 8, 16 (>= DEAD_VOTE_MIN sources, |LLR| >= DEAD_VOTE_LLR,
# never other tied bits); when the vote abstains the measured global
# fewer-ones prior stands.  A wrong unanimous vote needs a payload whose
# byte periodicity breaks exactly at the unobserved bit and nowhere near
# it -- and random payloads simply abstain.
DEAD_VOTE_LLR = 1.0     # |LLR| a payload bit needs to become a vote source
DEAD_VOTE_MIN = 3       # sources required (out of 4: t-16, t-8, t+8, t+16)
DEAD_VOTE_SET = 0.9     # |LLR| given to a vote-resolved bit (< ST_LLR:
                        # pattern priors must not become training labels)

# KNIFE-BIT byte-period vote (audit fix 4, final form).  The (5,6)-family
# L=1 misses are knife-edge bits: the per-capture 0/1 window they need is
# 1-7 ns wide (measured against ground truth), narrower than any blind
# boundary estimate -- the probit llr at such a bit is sub-KNIFE_LLR noise,
# and 11 of the original 13 misses are exactly these bits.  The sampler
# phase SWEEPS ~14 ns/bit, so the same payload bit position in
# neighbouring bytes lands well clear of the boundary and is decoded
# confidently.  A knife bit therefore defers to the byte-period vote of
# its t +- 8, 16 siblings -- but ONLY per lag whose byte-periodicity the
# capture itself PROVES first: over all confidently decoded payload bit
# pairs (t, t+lag), the agreement must reach KNIFE_PERIOD_MIN (measured:
# every periodic test pattern scores exactly 1.000 on its lag -- lag 16
# covers the two-byte patterns where lag 8 reads 0.00-0.75 -- while
# random payloads score 0.40-0.55, count 0.78-0.81, impulse 0.87; the
# 0.99 gate sits in a >= 0.12 margin on both sides).  With the gate
# proven, a single confident gated sibling decides (KNIFE_VOTE_MIN = 1:
# near the frame edges and for lag-16-only patterns exactly one sibling
# is in range; an ungated 2-of-2 rule was measured to flip random-payload
# bits wrongly -- the gate, not the count, is what carries the safety).
# Unlike the dead-window vote this also covers dead-TIED (5,6) bits the
# 3-source dead vote left unresolved (a frame-edge dead bit has only 2
# siblings).  Measured on the 54-capture set: 19 knife votes fire, all 19
# agree with ground truth, none fire on the aperiodic payloads.
KNIFE_LLR = 0.9         # |LLR| below which a (5,6) L=1 bit is a knife bit
KNIFE_VOTE_MIN = 1      # gated unanimous siblings required
KNIFE_PERIOD_MIN = 0.99  # per-lag payload periodicity proof threshold
KNIFE_PERIOD_N = 40     # min confident pairs behind the proof
TRUNC_KNIFE_LLR = 2.0   # on a TRUNCATED capture (cover0 > 0) any un-voted
                        # (5,6) L=1 payload bit below this margin refuses
                        # the decode: truncation shifts the fitted boundary
                        # by ~10 ns (~0.5-1.5 nats), so bits inside that
                        # swing are coin flips there (measured: a dropped
                        # loop flipped bits at |llr| 1.0-1.4 while every
                        # truncation-decodable capture's bits sit at 1.7+
                        # or are vote-resolved)

PSI_SHRINK = 45.0       # per-slot offset shrinkage (ns)
PSI_SPAN = 80.0         # per-slot offset search range (ns)
ST_LLR = 1.0            # |LLR| above which a payload pulse self-labels


def _fit_model(labelled, h0p, h1p):
    """Joint per-capture fit: effective widths h0c/h1c plus one phase offset
    psi[s] per slot, from labelled fall brackets.

    A label of class c with generator offset already removed constrains
      h_c  in  ( lo - psi[sa],  hi - psi[sb] ]
    so slots couple across bracket families (slot 6 is the v-side of family
    (5,6) and the u-side of family (6,7)).  Interval-censored Huber loss,
    coordinate descent, shrinkage toward 0 / the model priors."""
    labs = []            # (sa, sb, lo, hi, cls)
    for (p, a) in labelled:
        li = _label_interval(p, a, h0p, h1p)
        if li is None:
            continue
        cls, lo, hi = li
        labs.append((p["sfa"], p["sfb"], lo, hi, cls))
    psi = [0.0] * 8
    h0c, h1c = h0p, h1p

    def hinge(sa, sb, lo, hi, H):
        g = 0.0
        d = (lo - psi[sa]) - H
        if d > g:
            g = d
        d = H - (hi - psi[sb])
        if d > g:
            g = d
        if g > CLIP_FIT:
            g = CLIP_FIT
        return (g / SIG_FIT) ** 2

    for _ in range(3):
        # widths given psi
        i0 = [(lo - psi[sa], hi - psi[sb]) for sa, sb, lo, hi, c in labs
              if c == 0]
        i1 = [(lo - psi[sa], hi - psi[sb]) for sa, sb, lo, hi, c in labs
              if c == 1]
        h0c = _fit_h(i0, h0p)
        h1c = _fit_h(i1, h1p)
        if not (270.0 <= h0c <= 470.0):
            h0c = h0p
        if not (620.0 <= h1c <= 920.0):
            h1c = h1p
        if not (270.0 <= (h1c - h0c) <= 480.0):
            h0c, h1c = h0p, h1p
        # per-slot offsets given widths (coordinate descent, 1 sweep/round)
        for s in range(8):
            touch = [(sa, sb, lo, hi, c) for sa, sb, lo, hi, c in labs
                     if sa == s or sb == s]
            if len(touch) < 2:
                psi[s] = 0.0
                continue
            best_v, best_c = psi[s], None
            v = -PSI_SPAN
            while v <= PSI_SPAN:
                old = psi[s]
                psi[s] = v
                c = (v / PSI_SHRINK) ** 2
                for sa, sb, lo, hi, cls in touch:
                    c += hinge(sa, sb, lo, hi, h0c if cls == 0 else h1c)
                psi[s] = old
                if best_c is None or c < best_c:
                    best_c, best_v = c, v
                v += 2.0
            psi[s] = best_v
    return h0c, h1c, psi


EPS_CLAMP = 60.0        # max per-family boundary shift from the cloud split
ZONE_HALF = 80.0        # label-free zone half-width around the prior boundary
SEP_MIN = 8.0           # labelled classes must separate by this to classify


def _probit_boundary(gap, wa, wb, h0c, h1c):
    """x (fall-bit phase of the last-high sample) at which a single-bit
    pulse's 0/1 probit costs tie, for a family with bracket width gap."""
    lo = min(h0c, h1c - gap) - 150.0
    hi = max(h0c, h1c - gap) + 150.0
    x = lo
    prev = None
    while x <= hi:
        c0 = -_log_ndtr((h0c - x) / wa) - _log_ndtr((x + gap - h0c) / wb)
        c1 = -_log_ndtr((h1c - x) / wa) - _log_ndtr((x + gap - h1c) / wb)
        d = c1 - c0
        if prev is not None and prev > 0.0 >= d:
            return x - 1.0
        prev = d
        x += 2.0
    return (h0c + h1c - gap) * 0.5


PREG_ZONE = 100.0       # labelled points within this of b enter the fit
PREG_PRIOR_W = 1.0      # weight of the prior pulling theta toward b
PREG_SLACK = 4.0        # max ns a labelled example may sit on the wrong side
PREG_CLEAR1 = 45.0      # x beyond b by this much cannot be a 0-fall
PREG_TOP_MARGIN = 6.0   # pure-zero family: boundary this far above the
                        # cloud top (> the ~3 ns per-pulse tie-point slop
                        # from bracket-width variation around the median)


def _preg_boundary(b, pts0, pts1, sig, span=EPS_CLAMP):
    """1-D probit regression: the ML boundary given labelled points whose
    x measurements carry Gaussian noise sig (the slot sampling noise --
    WE[5] is 38 ns, so labelled extremes are soft evidence, not walls;
    hard clipping to max(x0)/min(x1) chases realized noise and conflicting
    labels would otherwise force a skip).  A quadratic prior keeps theta
    at the h-model boundary b when labels are few or balanced.

    A final clamp keeps every labelled example within PREG_SLACK of the
    right side: when one class is thinly labelled (a truncated capture may
    keep a single cls1 label) the opposing mass plus the prior can push
    theta 10+ ns past a known example, which is never right -- with
    mutually conflicting labels the midpoint of the conflict is used."""
    best_t, best_c = b, None
    t = b - span
    while t <= b + span:
        c = PREG_PRIOR_W * ((t - b) / sig) ** 2
        for x in pts0:
            c += -_log_ndtr((t - x) / sig)
        for x in pts1:
            c += -_log_ndtr((x - t) / sig)
        if best_c is None or c < best_c:
            best_c, best_t = c, t
        t += 1.0
    lo = max(pts0) - PREG_SLACK if pts0 else b - span
    hi = min(pts1) + PREG_SLACK if pts1 else b + span
    if lo > hi:
        if pts0 and pts1:
            return (max(pts0) + min(pts1)) * 0.5
        return best_t
    return min(max(best_t, lo), hi)


def _fit_family_eps(seg, labelled, h0c, h1c, psi):
    """Per-family boundary refinement from the whole capture's pulse cloud.

    The class mix of a bracket family varies 0..100 percent per capture, so
    the boundary must come from the capture itself: within the zone the
    labels leave open, place it at the midpoint of the largest gap in the
    family's pooled fall-bit phases (payload included, no classes needed --
    a class edge is a density gap, a single class is a cloud to stay outside
    of).  Families whose labelled classes do not separate (dead-window
    families have byte-identical x for both classes) are left alone.

    Family (5,6) -- the 339 ns bracket whose 0/1 boundary zone
    [h0, h1-gap] is only ~20-35 ns wide, narrower than the slot-5 sampling
    noise -- is refined by probit regression on the labelled points instead
    (audit fix 4): the gap heuristic chases realized noise there, and its
    sweep-dominance guard used to suppress refinement in most of the
    failing captures."""
    fam_x = {}
    fam_gap = {}
    for p in seg:
        fam = (p["sfa"], p["sfb"])
        fam_gap.setdefault(fam, []).append(p["v"] - p["u"])
    bnd = {}
    gmed = {}
    for fam, gaps in fam_gap.items():
        g = sorted(gaps)[len(gaps) // 2]
        gmed[fam] = g
        wa = math.hypot(WE[fam[0]], TB_NS)
        wb = math.hypot(WE[fam[1]], TB_NS)
        bnd[fam] = _probit_boundary(g, wa, wb, h0c, h1c)
    for p in seg:
        fam = (p["sfa"], p["sfb"])
        up = p["u"] - psi[fam[0]]
        x = up - BIT * round((up - bnd[fam]) / BIT)
        fam_x.setdefault(fam, []).append(x)
    lab_x = {}
    h0p_ = h0c
    h1p_ = h1c
    for (p, a) in labelled:
        li = _label_interval(p, a, h0p_, h1p_)
        if li is None:
            continue
        cls, lo, hi = li
        fam = (p["sfa"], p["sfb"])
        lab_x.setdefault(fam, []).append((lo - psi[fam[0]], cls))
    eps = {}
    for fam, labs in lab_x.items():
        x0 = [x for x, c in labs if c == 0]
        x1 = [x for x, c in labs if c == 1]
        b = bnd[fam]
        if fam == (5, 6):
            sig = math.hypot(WE[fam[0]], TB_NS)
            pts0 = [x for x in x0 if abs(x - b) < PREG_ZONE]
            pts1 = [x for x in x1 if abs(x - b) < PREG_ZONE]
            cloud = fam_x.get(fam, ())
            if pts1:
                # both classes labelled near the zone: probit regression
                theta = _preg_boundary(b, pts0, pts1, sig)
            else:
                # no labelled 1s: the one-sided regression is unidentified
                # above the labelled 0s (its 0-tail pull drifts 20+ ns
                # high) -- the guarded largest-gap split of the cloud
                # decides instead, staying at the model boundary when the
                # sweep-dominance guard fires.  (The split can still land
                # above a true 1 in byte-periodic payloads -- sparse -- but
                # there the knife vote overrules it; the split is kept for
                # the APERIODIC payloads the vote's gate excludes, where it
                # measures correct: count.)
                theta = _zone_gap_theta(b, x0, x1, cloud)
                if theta is None:
                    theta = b
            if not any(x > b + PREG_CLEAR1 for x in cloud):
                # a pure-zero family: nothing anywhere in the clear-1
                # range, so the cloud top IS the h0 edge and the boundary
                # belongs above it (labels alone cannot see the dense
                # unlabelled 0s crowding the zone from below).  A labelled
                # 1 INSIDE that top cloud is a noise collision -- the cap
                # yields to the floor then.
                top = [x for x in cloud
                       if b - EPS_CLAMP < x <= b + PREG_CLEAR1]
                if top:
                    floor = max(top) + PREG_TOP_MARGIN
                    theta = max(theta, floor)
                    if pts1 and min(pts1) + PREG_SLACK > floor:
                        theta = min(theta, min(pts1) + PREG_SLACK)
                elif pts1:
                    theta = min(theta, min(pts1) + PREG_SLACK)
            eps[fam] = max(-EPS_CLAMP, min(EPS_CLAMP, theta - b))
            continue
        if x0 and x1 and (min(x1) - max(x0)) < SEP_MIN:
            continue                       # dead / conflicting family
        theta = _zone_gap_theta(b, x0, x1, fam_x.get(fam, ()))
        if theta is None:
            continue
        e = theta - b
        eps[fam] = max(-EPS_CLAMP, min(EPS_CLAMP, e))
    return eps


def _zone_gap_theta(b, x0, x1, cloud):
    """Largest label-feasible density gap around b, or None to leave the
    boundary at b.  (The pre-hardening per-family estimator, still used for
    every family but (5,6) and as the one-sided-(5,6) fallback.)"""
    zone_lo = max(x0) if x0 else b - ZONE_HALF
    zone_hi = min(x1) if x1 else b + ZONE_HALF
    zone_lo = max(zone_lo, b - ZONE_HALF)
    zone_hi = min(zone_hi, b + ZONE_HALF)
    if zone_lo >= zone_hi:
        return None
    pts = sorted(x for x in cloud if zone_lo < x < zone_hi)
    if not pts:
        if not (x0 and x1):
            return None                    # no cloud, one-sided labels
        return (zone_lo + zone_hi) * 0.5
    seqs = [zone_lo] + pts + [zone_hi]
    gaps_z = [seqs[i + 1] - seqs[i] for i in range(len(seqs) - 1)]
    bi = max(range(len(gaps_z)), key=lambda i: gaps_z[i])
    bg = gaps_z[bi]
    # a sweeping (crawling-phase) cloud fills the zone with evenly spaced
    # points: a split there is meaningless -- require the gap to dominate
    # the local spacing as well as an absolute minimum
    if bg < 12.0:
        return None
    if len(gaps_z) >= 4:
        srt = sorted(gaps_z)
        med_sp = srt[len(srt) // 2]
        if bg < 2.5 * med_sp:
            return None
    return (seqs[bi] + seqs[bi + 1]) * 0.5


def _try_decode(seg, model, self_train=True):
    """Decide every pulse's leading-ones count under the marker constraints.

    Returns dict with bits, payload, and the blind quality components."""
    h0p, h1p = model["H0"], model["H1"]

    # ---- marker-forced pulses (labels + hard constraints) -----------------
    forced = []          # (pulse, a_forced)
    for p in seg:
        k0, k1 = p["k0"], p["k1"]
        if k1 > NB:
            continue
        if any(KNOWN[t] < 0 for t in range(k0, k1)):
            continue
        amin, amax = _a_bounds(k0, k1)
        if amin != amax:
            continue                      # cannot happen on fully-known bits
        forced.append((p, amin))
    forced_ids = {id(p): a for (p, a) in forced}

    h0c, h1c, psi = _fit_model(forced, h0p, h1p)
    eps = _fit_family_eps(seg, forced, h0c, h1c, psi)

    def _score_all(h0c, h1c, psi, eps):
        bits = [0] * NB
        llr = [0.0] * NB     # >0 favours 1; hidden/merged bits saturate
        total_cost = 0.0
        infeasible = 0
        label_err = 0
        lab_unc = 0          # forced labels in the uncertain zone
        dead_ct = 0          # pulses whose window was never observed
        dead_ties = []       # unforced dead windows: (pulse, a_lo, a_hi)
        for p in seg:
            k0, k1 = p["k0"], p["k1"]
            L = k1 - k0
            ef = eps.get((p["sfa"], p["sfb"]), 0.0)
            u = p["u"] - psi[p["sfa"]] - ef
            v = p["v"] - psi[p["sfb"]] - ef
            h0f, h1f = h0c, h1c
            wa = math.hypot(WE[p["sfa"]], TB_NS)
            wb = math.hypot(WE[p["sfb"]], TB_NS)
            amin, amax = _a_bounds(k0, k1)
            cap = min(L, S_CAP + 2)
            costs = {}
            interior = {}
            for a in range(0, L + 1):
                if a > cap and a < L:
                    continue
                costs[a], interior[a] = _cost_a(a, L, u, v, wa, wb,
                                                h0f, h1f)
            # both hypotheses fully inside the bracket = a dead window: the
            # discriminating interval was never sampled and the probit tails
            # are model artifacts, not data -- apply the fallback fewer-ones
            # prior now; the byte-period vote below may overrule it once the
            # confident payload bits are known
            ins = sorted(a for a in costs if interior[a])
            if len(ins) >= 2:
                dead_ct += 1
                for a in ins[1:]:
                    costs[a] += DEAD_PRIOR_NATS
            # unconstrained argmin (label-error accounting); near-ties prefer
            # the fewer-ones hypothesis (see TIE_NATS)
            cmin_free = min(costs.values())
            a_free = min(a for a in costs if costs[a] <= cmin_free + TIE_NATS)
            if id(p) in forced_ids:
                if a_free != forced_ids[id(p)]:
                    label_err += 1
                else:
                    second = min((costs[a] for a in costs if a != a_free),
                                 default=None)
                    if second is not None and second - cmin_free < 0.4:
                        lab_unc += 1
            # constrained argmin
            allowed = [a for a in costs if amin <= a <= amax]
            if not allowed:
                allowed = list(costs)
            cmin = min(costs[a] for a in allowed)
            a_hat = min(a for a in allowed if costs[a] <= cmin + TIE_NATS)
            c_hat = costs[a_hat]
            if c_hat > INFEAS_NATS:
                infeasible += 1
            total_cost += min(c_hat, 4.0 * INFEAS_NATS)
            p["a_hat"] = a_hat
            p["cost"] = c_hat
            if len(ins) >= 2 and amin <= ins[0] and ins[1] <= amax \
                    and a_hat in (ins[0], ins[1]):
                dead_ties.append((p, ins[0], ins[1]))
            # emit bits and per-bit LLRs
            for t in range(k0, min(k1, NB)):
                off = t - k0
                if off < a_hat:
                    bits[t] = 1
                c1 = min((costs[a] for a in allowed if a > off), default=None)
                c0 = min((costs[a] for a in allowed if a <= off), default=None)
                if c1 is None:
                    llr[t] = -BIG
                elif c0 is None:
                    llr[t] = BIG
                else:
                    llr[t] = max(-BIG, min(BIG, c0 - c1))
        # ---- dead-window arbitration, pass 2: byte-period payload vote ----
        # (see the DEAD-WINDOW TIE-BREAK note above: the tied bit was never
        # sampled, families carry no per-capture class signal, but the test
        # frames are byte-periodic -- a unanimous vote of the confidently
        # decoded bits one and two bytes away resolves it; abstain otherwise)
        resolved = set()     # bits a byte-period vote decided (trustworthy)
        tied_bits = set(p["k0"] + a_lo for (p, a_lo, _a) in dead_ties)
        for (p, a_lo, a_hi) in dead_ties:
            t = p["k0"] + a_lo
            if not (32 <= t < 160):
                continue
            votes = []
            for dt in (-16, -8, 8, 16):
                s = t + dt
                if 32 <= s < 160 and s not in tied_bits \
                        and abs(llr[s]) >= DEAD_VOTE_LLR:
                    votes.append(bits[s])
            if len(votes) < DEAD_VOTE_MIN or len(set(votes)) != 1:
                continue
            a_new = a_hi if votes[0] == 1 else a_lo
            if a_new != p["a_hat"]:
                p["a_hat"] = a_new
                k0, k1 = p["k0"], p["k1"]
                for tt in range(k0, min(k1, NB)):
                    bits[tt] = 1 if (tt - k0) < a_new else 0
            llr[t] = DEAD_VOTE_SET if votes[0] == 1 else -DEAD_VOTE_SET
            resolved.add(t)
        # ---- knife-bit arbitration: byte-period vote on (5,6) L=1 bits ----
        # (see the KNIFE-BIT note above; sub-KNIFE_LLR probit margins on
        # this family are boundary-estimate noise, not evidence.  A bit the
        # dead vote already resolved carries |llr| == DEAD_VOTE_SET ==
        # KNIFE_LLR and is excluded by the strict <; a dead-TIED bit the
        # dead vote left unresolved stays eligible here.)
        knife = []
        for p in seg:
            if (p["sfa"], p["sfb"]) != (5, 6):
                continue
            if p["k1"] - p["k0"] != 1:
                continue
            t = p["k0"]
            if not (32 <= t < 160):
                continue
            if abs(llr[t]) < KNIFE_LLR:
                knife.append(p)
        knife_bits = set(p["k0"] for p in knife)
        # per-lag byte-periodicity proof over confident, non-knife bits
        lag_ok = {}
        for lag in (8, 16):
            n_pair = agree = 0
            for t in range(32, 160 - lag):
                s = t + lag
                if t in knife_bits or s in knife_bits \
                        or t in tied_bits or s in tied_bits:
                    continue
                if abs(llr[t]) < DEAD_VOTE_LLR or abs(llr[s]) < DEAD_VOTE_LLR:
                    continue
                n_pair += 1
                agree += (bits[t] == bits[s])
            lag_ok[lag] = (n_pair >= KNIFE_PERIOD_N
                           and agree >= KNIFE_PERIOD_MIN * n_pair)
        if lag_ok[8] or lag_ok[16]:
            for p in knife:
                t = p["k0"]
                votes = []
                for dt in (-16, -8, 8, 16):
                    if not lag_ok[abs(dt)]:
                        continue
                    s = t + dt
                    if 32 <= s < 160 and s not in tied_bits \
                            and s not in knife_bits \
                            and abs(llr[s]) >= DEAD_VOTE_LLR:
                        votes.append(bits[s])
                if len(votes) < KNIFE_VOTE_MIN or len(set(votes)) != 1:
                    continue
                a_new = 1 if votes[0] == 1 else 0
                if a_new != p["a_hat"]:
                    p["a_hat"] = a_new
                    bits[t] = a_new
                llr[t] = DEAD_VOTE_SET if votes[0] == 1 else -DEAD_VOTE_SET
                resolved.add(t)
        # (5,6) L=1 payload bits no byte-period vote decided and whose own
        # margin is below the boundary swing a truncation can cause:
        # decode() refuses when such a bit coexists with truncation
        # evidence (depleted marker labels make the few-ns boundary these
        # bits hang on untrustworthy there).
        knife_open = 0
        for p in seg:
            if (p["sfa"], p["sfb"]) != (5, 6) or p["k1"] - p["k0"] != 1:
                continue
            t = p["k0"]
            if 32 <= t < 160 and t not in resolved \
                    and abs(llr[t]) < TRUNC_KNIFE_LLR:
                knife_open += 1
        return (bits, llr, total_cost, infeasible, label_err, lab_unc,
                dead_ct, knife_open)

    (bits, llr, total_cost, infeasible, label_err, lab_unc, dead_ct,
     knife_open) = _score_all(h0c, h1c, psi, eps)

    # ---- self-training pass: confident payload pulses become labels -------
    if self_train:
        extra = list(forced)
        for p in seg:
            if id(p) in forced_ids:
                continue
            k0, k1 = p["k0"], p["k1"]
            t = k0 + p["a_hat"] - 1 if p["a_hat"] > 0 else k0
            t = min(max(t, k0), min(k1, NB) - 1)
            if abs(llr[t]) >= ST_LLR:
                extra.append((p, p["a_hat"]))
        if len(extra) > len(forced):
            h0c, h1c, psi = _fit_model(extra, h0p, h1p)
            # the eps refit keeps the self-trained labels too: measured
            # 48/54 with them vs 44/54 marker-only -- the flood of correct
            # confident labels sharpens the boundary regression far more
            # than a rare knife-edge mislabel (soft evidence anyway) hurts
            eps = _fit_family_eps(seg, extra, h0c, h1c, psi)
            (bits, llr, total_cost, infeasible, label_err, lab_unc,
             dead_ct, knife_open) = _score_all(h0c, h1c, psi, eps)

    # ---- leading reconstruction + violations ------------------------------
    # bits before the first surviving pulse are unobserved; when they sit
    # inside the known header they carry no payload and are reconstructed
    # from KNOWN instead of being counted as violations (re-registered
    # truncated captures land here).  A first pulse past bit 32 means
    # payload bits are missing: decode() refuses via GATE_COVER.
    cover0 = seg[0]["k0"]
    for t in range(min(cover0, NB)):
        if KNOWN[t] == 1:
            bits[t] = 1
    violations = 0
    for t in range(NB):
        if KNOWN[t] >= 0 and bits[t] != KNOWN[t]:
            violations += 1

    payload = bytearray(16)
    for i in range(16):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[32 + 8 * i + j]
        payload[i] = b

    # a psi pinned at the +-PSI_SPAN search edge is a degenerate fit (the
    # coordinate descent ran away instead of converging); the arbitration
    # treats it as a dead-window-grade warning (audit note: an earlier
    # build's impulse_lo fit pinned psi[5]/psi[6] and merely happened to
    # decode).  Measured on the current build: no winning fit pins.
    psi_clamped = sum(1 for v in psi if abs(v) >= PSI_SPAN - 1e-9)

    return dict(bits=bits, llr=llr, payload=bytes(payload),
                violations=violations, infeasible=infeasible,
                label_err=label_err, lab_unc=lab_unc, dead_ct=dead_ct,
                knife_open=knife_open, psi_clamped=psi_clamped,
                total_cost=total_cost, cover0=cover0,
                h0c=h0c, h1c=h1c, n_forced=len(forced), seg=seg)


# ----------------------------------------------------- repair retries (8b)

def _rise_dist(p, kappa, tau):
    """Clearance of a pulse's mapped rise bracket from the bit lattice."""
    lo = kappa * p[0] + tau
    hi = kappa * p[1] + tau
    g = round((lo + hi) * 0.5 / BIT) * BIT
    return max(0.0, lo - g, g - hi)


def _fall_dist(p, kappa, tau, h0p, h1p):
    """Clearance of a pulse's mapped fall bracket from the h0/h1 templates."""
    lo = kappa * p[2] + tau
    hi = kappa * p[3] + tau
    mid = (lo + hi) * 0.5
    d = None
    for tt in (h0p, h1p):
        g = round((mid - tt) / BIT) * BIT + tt
        dd = max(0.0, lo - g, g - hi)
        d = dd if d is None else min(d, dd)
    return d


def _repair_candidates(pl, kappa, tau, h0p, h1p):
    """Sample indices worth flipping, most suspicious first.

    hole m: pulses j and j+1 are separated by EXACTLY one low sample (index
    m) -- the signature of a single 1->0 sample flip splitting a pulse --
    ranked by how far pulse j+1's rise bracket sits off the bit lattice
    (every genuine bit rise straddles it).
    spike m: a one-sample pulse whose rise and fall brackets are BOTH well
    off the lattice/templates -- the signature of a single 0->1 flip inside
    a low run.

    The repair FLIPS the sample and re-runs the whole pipeline: a flipped
    sample also corrupts the data-dependent clock feedback (W terms), so
    every later sample time is off until the level is restored -- merely
    merging the pulse brackets cannot heal that."""
    holes = []
    for j in range(len(pl) - 1):
        if pl[j + 1][9] - pl[j][10] == 2:
            holes.append((_rise_dist(pl[j + 1], kappa, tau), pl[j][10] + 1))
    holes.sort(key=lambda t: (-t[0], t[1]))
    spikes = []
    for p in pl:
        if p[6] == 1:
            d = min(_rise_dist(p, kappa, tau),
                    _fall_dist(p, kappa, tau, h0p, h1p))
            if d > 60.0:
                spikes.append((d, p[9]))
    spikes.sort(key=lambda t: (-t[0], t[1]))
    return [m for _, m in holes], [m for _, m in spikes]


def _flip_sample(samples, m):
    i, s, v = samples[m]
    return samples[:m] + [(i, s, 1 - v)] + samples[m + 1:]


def _q_bad(q):
    return (q[0] > GATE_VIOL or q[1] > REPAIR_Q_INFEAS
            or q[2] > REPAIR_Q_LABERR)


# ---------------------------------------------------------------- top level

def _decode_model(samples, model):
    """Best (result, quality) under one sampler model, with bounded repair
    retries when the blind quality statistics show corruption.  Clean
    captures never enter the repair loop (their Q is already good)."""

    def attempt(smp, shift=0, cands=None, pulses=None):
        if pulses is None:
            pulses = _model_clock_pulses(smp, model)
        if len(pulses) < 8:
            return None, None, None, pulses
        if cands is None:
            cands = _hough_candidates(pulses, model["H0"], model["H1"])
        mb = mq = None
        for ci, (kappa, tau, hits, cost) in enumerate(cands):
            seg, slip0 = _segment(pulses, kappa, tau, shift)
            if seg is None:
                continue
            res = _try_decode(seg, model)
            q = (res["violations"], res["infeasible"], res["label_err"],
                 res["psi_clamped"], -hits, round(res["total_cost"], 3))
            res.update(model=model["name"], kappa=kappa, tau=tau, hits=hits,
                       slip0=slip0, alias=ci, shift=shift)
            if mq is None or q < mq:
                mb, mq = res, q
            if q[0] == 0 and q[1] == 0 and q[2] == 0 and q[3] == 0:
                break         # clean under this model, fit non-degenerate
        return mb, mq, cands, pulses

    best, bq, cands0, pulses0 = attempt(samples)
    if best is None:
        return None, None
    # the walk metric is a badness SUM (then cost): healing one of several
    # corruptions can transiently RAISE violations while slashing the
    # infeasible count, which the lexicographic Q would refuse; the
    # lexicographic Q still picks what is finally returned.
    ret_best, ret_q = best, bq

    def rq(q):
        return (q[0] + q[1] + q[2], q[5])

    wq = rq(bq)
    cur, cur_cands, cur_pulses = samples, cands0, pulses0
    for _ in range(REPAIR_MAX_ROUNDS):
        if not _q_bad(bq):
            break
        trials = []
        if best["shift"] == 0:
            trials += [("shift", s) for s in range(1, SHIFT_MAX + 1)]
        holes, spikes = _repair_candidates(cur_pulses, best["kappa"],
                                           best["tau"],
                                           model["H0"], model["H1"])
        trials += [("flip", m) for m in holes[:REPAIR_TOP]]
        trials += [("flip", m) for m in spikes[:REPAIR_TOP]]
        stepped = None
        for kind, arg in trials:
            if kind == "shift":
                r, q, cd, pl = attempt(cur, shift=arg, cands=cur_cands,
                                       pulses=cur_pulses)
                nsmp = cur
            else:
                nsmp = _flip_sample(cur, arg)
                r, q, cd, pl = attempt(nsmp)
            if r is None:
                continue
            if q < ret_q:
                ret_best, ret_q = r, q
            if rq(q) < wq and (stepped is None or rq(q) < rq(stepped[0])):
                stepped = (q, r, nsmp, cd, pl)
        if stepped is None:
            break                          # no strict improvement: stop
        bq, best, cur, cur_cands, cur_pulses = stepped
        wq = rq(bq)
    return ret_best, ret_q


def _decode_full(samples, meta=None):
    """Full decode with diagnostics; returns (best_result, best_quality)."""
    if not samples:
        return None, None
    best = None            # overall winner (across models)
    best_q1 = None
    for model in MODELS:
        mbest, _mq = _decode_model(samples, model)
        if mbest is None:
            continue
        # across models: switch only on a clear improvement of the
        # decision-quality triple (hits/cost live in different coordinates);
        # a 1-count label_err difference is noise, demand >= 2
        q1 = (mbest["violations"], mbest["infeasible"], mbest["label_err"],
              mbest["dead_ct"])
        if best is None:
            best, best_q1 = mbest, q1
        elif (q1[0], q1[1]) < (best_q1[0], best_q1[1]) or \
                ((q1[0], q1[1]) == (best_q1[0], best_q1[1])
                 and q1[2] + 1 < best_q1[2]) or \
                ((q1[0], q1[1]) == (best_q1[0], best_q1[1])
                 and abs(q1[2] - best_q1[2]) <= 1
                 and q1[3] + 3 < best_q1[3]):
            best, best_q1 = mbest, q1
    return best, best_q1


def decode(samples, meta):
    best, _ = _decode_full(samples, meta)
    if best is None:
        return None
    # honest refusal (audit fix 2): return a payload only when the blind
    # quality statistics sit inside the calibrated clean envelope.  Clean
    # captures measure violations=0, infeasible=0, label_err<=2; corrupted
    # ones measure infeasible 15-185 and label_err 11-31, so the gates
    # separate with wide margins on both sides.
    if (best["violations"] > GATE_VIOL or best["infeasible"] > GATE_INFEAS
            or best["label_err"] > GATE_LABERR
            or best["cover0"] > GATE_COVER):
        return None
    # truncation + open knife bits: bits before the first surviving pulse
    # were reconstructed (leading loops were lost), so marker labels are
    # depleted and the few-ns (5,6) boundary is less trustworthy -- if any
    # knife bit remained unresolved (the byte-period vote abstained), its
    # call is a coin flip on a damaged capture: refuse rather than guess.
    # Clean captures always have cover0 == 0, so this gate cannot touch
    # them (measured: unresolved knife bits occur on intact aperiodic
    # captures too, and there the calibrated boundary decides them).
    if best["cover0"] > 0 and best["knife_open"] > 0:
        return None
    return best["payload"]
