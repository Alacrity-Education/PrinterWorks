"""embedded_ref -- WS2812 reconstruction decoder shaped for the STM8S001J3.

Same decode(samples, meta) contract as combined.py, but restricted to what
the 8-bit target can actually execute:

  * integer arithmetic only (8/16/32-bit; Python ints used AS IF fixed
    point, with range asserts at every load-bearing assignment);
  * no floats, no transcendentals, no numpy;
  * O(n) forward-only streaming passes over the sample stream -- on the
    STM8 each pass is a re-scan of the raw capture buffer; NO pulse list
    is ever materialised (the retained state of every pass is enumerated
    in RAM_BUDGET below, byte by byte);
  * working-set arrays sized by the frame, not the capture.

PIPELINE (KEEP+ADAPT core of combined.py; every DROP was costed by
measured ablation -- see dev_embedded/ablate_port.py output):

  P1  endpoint seed        first-rise / last-fall brackets + the known
                           frame geometry pin the clock scale to ~0.05%,
                           excluding the one-bit-slip aliases a priori
                           (replaces the blind Hough grid, stage 2).
  P2  lock refine (x2)     nearest-lattice residuals of the rise-bracket
                           midpoints; integer two-half-means regression
                           for (K, tau) (replaces the FINE grids).
  P3  marker calibration   forced-label pulses inside header/trailer ->
                           interval-intersection fit of h0c/h1c, plus the
                           eps analog: a per-family boundary for the two
                           razor families (5,6)/(6,7) from a 64-bin fold
                           histogram of the family's pooled (unlabelled)
                           fall phases -- largest label-feasible density
                           gap, two-label-trust clamp, pure-zero floor
                           (ADAPTs the host's psi/eps/preg fits).
  P4  decision + emit      gap-accounting segmentation (KEEP, exact),
                           marker-constrained per-pulse leading-ones
                           argmin by interval hinge with an interior-
                           preferred, fewer-ones tie-break (ADAPTs the
                           probit; per-slot widths WE measured worth 0).
  V   byte-period votes    dead-window + knife-bit votes on the emitted
                           bit array only (no per-bit float LLRs; a
                           1-bit confidence map replaces them), BOTH
                           gated by the per-lag byte-periodicity proof.
  (P5/P6 self-train re-fit exists behind SELF_TRAIN but measured
   REDUNDANT in this final config -- identical output on all 54 real and
   18 production-size synthetic decodes -- so it defaults off and is
   omitted from the C build.)

FIXED-POINT FORMATS (TU = "time unit" = BIT/2^BIT_SH = 1250/512 ns =
2.4414 ns; at the earlier BIT/128 the (5,6) knife boundaries -- a few ns
wide -- were measured lost to quantization):

  quantity              format  range/units
  --------------------- ------  ------------------------------------------
  t (receiver time)     u16     CPU cycles; <= ~27.5k on a 640-loop capture
  K (clock scale)       u16     Q11 TU/cycle; nominal 25.6*2048 = 52429
  t*K product           u32     <= 27.5k * 60000 < 2^31   ** 32-bit **
  y (mapped wire time)  u32     TU; BIAS + NB*512 + TAIL ~ 230k (prod)
  tau (lock offset)     s16     TU
  u, v (fall bracket)   s16     TU, relative to the pulse's bit lattice
  h0c/h1c/theta/eps     s16     TU
  Se (residual sums)    s32     <= 230 pulses * 256 TU    ** 32-bit **
  Sy (position sums)    u32     <= 230 pulses * 230k TU   ** 32-bit **
  K*de, seed dividend   s32     see _seed/_refine          ** 32-bit **

  Every ** 32-bit ** intermediate is flagged; everything pulse-relative
  fits 16 bits.  Divisions: ~10 per decode (lock + calibration).
  All fixed-point ranges are enforced by asserts on every dataset and
  synthetic run (zero violations).

MEASURED ON TARGET (see dev_embedded/decoder.c -- a bit-exact C port,
identical output on all 54 real + 18 production-size synthetic decodes,
compiled with SDCC 4.6 -mstm8 --opt-code-size at NB=448):

  flash  CODE 7.7 KB + CONST 0.3 KB  (decoder alone; DOES NOT co-fit
         with the application in 8 KB without hand-compaction)
  RAM    DATA 781 B = 256 B capture buffer + 48 B payload + 477 B
         decoder state; +187 B measured peak stack
  cycles ~4.4-4.8M ucsim ticks per 448-bit decode (~0.3 s @16 MHz;
         ucsim under-reads this silicon ~7% on the one hardware-
         calibrated loop) -- the 100 ms budget needs the sample scanner
         in assembly + pass fusion (see EMBEDDED_FEASIBILITY.md)

decode(samples, meta) -> 16 payload bytes | None.  Deterministic.
"""

# --------------------------------------------------------------- op counter
# Counts the operations that dominate the STM8 cycle budget.  'sample' =
# one raw sample visited by a pass; 'pulse' = one pulse processed by a
# pass; 'mul' = one 16x16->32 multiply; 'div' = one 16/32-bit division;
# 'cand' = one leading-ones hypothesis evaluated; 'scan' = one pass launch.
OPS = {"sample": 0, "pulse": 0, "mul": 0, "div": 0, "cand": 0, "scan": 0,
       "bit": 0}


def ops_reset():
    for k in OPS:
        OPS[k] = 0


# ------------------------------------------------------- fixed-point guards

def _u16(x):
    assert 0 <= x <= 0xFFFF, ("u16 overflow", x)
    return x


def _s16(x):
    assert -0x8000 <= x <= 0x7FFF, ("s16 overflow", x)
    return x


def _u32(x):
    assert 0 <= x <= 0xFFFFFFFF, ("u32 overflow", x)
    return x


def _s32(x):
    assert -0x80000000 <= x <= 0x7FFFFFFF, ("s32 overflow", x)
    return x


def _idiv(a, b):
    """C-style integer division truncating toward zero."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


# ----------------------------------------------------------- fixed constants
# Sampler model = dev_calibration/fitted_model.json, which is EXACT integer
# cycles: loop 40 cy, slot offsets [0,4,9,13,17,21,27,32] cy, data-dependent
# w = [0,-1,0,+2,0,0,0,+1] cy per HIGH read.  (The 'cal' host model is the
# same clock in a stretched coordinate; a per-slot sub-cycle tweak table
# OADJ_U below lets the embedded build ship either intra-loop geometry --
# measured: the fitted one wins through this pipeline, OADJ stays zero.)
LOOP_CY = 40
O_CY = (0, 4, 9, 13, 17, 21, 27, 32)
W_CY = (0, -1, 0, 2, 0, 0, 0, 1)
OADJ_U = (0, 0, 0, 0, 0, 0, 0, 0)      # optional per-slot TU tweak (s8)

# TU = BIT / 2^BIT_SH.  BIT_SH=9 -> TU = 2.44 ns: fine enough that the
# (5,6)-family boundary information (a few ns) survives quantization --
# measured: at BIT_SH=7 (9.77 ns) every remaining bit error was a (5,6)
# single-bit call lost to rounding.  Mapped absolute times y then need
# ** u32 ** (production frame = 448*512 + tail = 230k TU); everything
# pulse-relative stays s16.
BIT_SH = 9
BIT_U = 1 << BIT_SH                    # 1250 ns in TU (power of two!)
BIT_H = BIT_U >> 1
BIAS_U = BIT_U                         # lattice of bit k at BIAS + k*BIT_U
TAIL_U = 164                           # 400 ns latch tail
H0P = 154                              # 377 ns effective T0H in TU
H1P = 308                              # 752 ns effective T1H in TU
KQ = 20 - BIT_SH                       # K is Q(KQ) TU/cycle
K_NOM = 52429                          # 62.5/TU * 2^KQ (same for any BIT_SH)
K_MIN, K_MAX = 46000, 60000            # +-12% envelope guard (u16 safe)
FIRST_BR_CY = 4                        # first-sample rise bracket: 250 ns
LATCH_RUN = 200                        # consecutive low samples = latch

# decision / calibration constants (all TU unless noted)
INFEAS_U = 160                         # min hinge above this = infeasible
LAB_MIN = 3                            # labels needed to move a width
LAB_OUT = 246                          # label outlier gate (600 ns)
H0_LO, H0_HI = 112, 192                # h0c guard (270..470 ns)
H1_LO, H1_HI = 252, 376                # h1c guard (620..920 ns)
SEP_LO, SEP_HI = 112, 196              # h1c-h0c guard (270..480 ns)
FAM_CLAMP = 24                         # per-family clamp (+-59 ns)
FAM_MIN = 2                            # labels needed per family
CONF_M = 16                            # per-bit confident margin (39 ns)
KNIFE_M = 24                           # knife-bit margin (plateau 16..32)
ST_M = 16                              # self-train label margin
DEAD_VOTE_MIN = 3                      # dead-window vote sources
KNIFE_PAIR_MIN = 40                    # periodicity-proof pair count
KNIFE_AGREE_PCT = 99                   # periodicity-proof agreement %
KNIFE_MAX = 32                         # knife list capacity (RAM cap;
                                       # a 448-bit random payload measures
                                       # ~24 knife candidates)
GATE_INFEAS = 4
GATE_LABERR = 6

HDR = bytes.fromhex("FF00AA65")
TRL = bytes.fromhex("9A5500FF")

SELF_TRAIN = False     # measured in the final config: self-training changes
                       # NOTHING on any of the 54 captures or the 18
                       # production-size synthetics (the eps56 boundary +
                       # gated votes made it redundant) -- dropped from the
                       # C build, saving 2 of 7 capture scans
VOTES = True
FAM_OFFSETS = False    # measured: per-family width intervals are neutral at
                       # best on this dataset (47/54 either way); the code
                       # path stays for the report's measurement record
EPS56 = True           # cloud-gap boundary refinement for families (5,6)
                       # and (6,7) -- the integer analog of the host's eps

# eps analog constants (TU = 2.44 ns unless noted)
EPS_ZONE = 32          # label-free split zone half-width (78 ns; host 80)
EPS_HIST = 64          # histogram half-range (156 ns; 64 bins of 2 TU)
EPS_GAP_MIN = 5        # min density gap to split on (12 ns; host 12 ns)
EPS_CLAMP56 = 24       # boundary shift clamp (59 ns; host 60 ns)
EPS_CLEAR1 = 18        # "clearly a 1-fall" margin (45 ns; host 45 ns)
EPS_TOPM = 3           # pure-zero floor margin (7 ns; host 6 ns)
EPS_SLACK = 2          # slack when two labels concur (5 ns; host 4 ns)
EPS_SLACK1 = 8         # trust radius of a lone extreme label (20 ns)


def _bits_of(bs):
    return [(byte >> (7 - i)) & 1 for byte in bs for i in range(8)]


def _build(npay):
    nb = 8 * (8 + npay)
    known = [-1] * nb
    known[0:32] = _bits_of(HDR)
    known[nb - 32:nb] = _bits_of(TRL)
    return nb, known


N_PAYLOAD = 16                         # dataset payloads; production: 48
NB, KNOWN = _build(N_PAYLOAD)


def _configure(npay):
    """Re-derive frame constants (dev tooling; production compiles them)."""
    global N_PAYLOAD, NB, KNOWN
    N_PAYLOAD = npay
    NB, KNOWN = _build(npay)


# ------------------------------------------------------------ pulse stream

def _pulse_stream(samples):
    """Forward-only pulse generator: (ra, rb, fa, fb, sfa, nh) in receiver
    CPU cycles; sfa = slot of the last high sample (the fall family --
    the first-low slot is always the next sampled slot, so one id
    suffices).  Stops at the latch (LATCH_RUN consecutive lows).

    STM8 equivalent: a re-scan of the raw capture buffer; retained state
    is 6 x u16 + 3 x u8 + the loop counters.
    """
    OPS["scan"] += 1
    t_prev = 0
    have_prev = False
    in_pulse = False
    ra = rb = fa = 0
    sfa = 0
    nh = 0
    low_run = 0
    seen = False
    wsum = 0                                     # s16, data-dependent term
    for (i, s, v) in samples:
        OPS["sample"] += 1
        t = _u16(i * LOOP_CY + O_CY[s] + wsum)   # u16 cycles
        if v:
            wsum += W_CY[s]
            if not in_pulse:
                in_pulse = True
                ra = t_prev if have_prev else (t - FIRST_BR_CY if
                                               t >= FIRST_BR_CY else 0)
                rb = t
                nh = 0
            nh += 1
            fa = t
            sfa = s
            low_run = 0
            seen = True
        else:
            if in_pulse:
                yield (ra, rb, fa, t, sfa, nh)
                in_pulse = False
            low_run += 1
            if seen and low_run >= LATCH_RUN:
                return
        t_prev = t
        have_prev = True
    if in_pulse:
        yield (ra, rb, fa, _u16(fa + FIRST_BR_CY), sfa, nh)


def _map(t, K, tau):
    """Receiver cycles -> wire TU:  y = ((t*K) >> 13) + tau.

    t*K is the ** 32-bit ** intermediate (<= 27.5k * 60k < 2^31); the
    result must land in u16 (the caller stops at Y_END before t can grow
    past that)."""
    OPS["mul"] += 1
    y = (_u32(t * K) >> KQ) + tau
    return y                                      # caller range-checks


# ------------------------------------------------------------- lock (P1+P2)

def _seed(samples):
    """Endpoint seed: K from the known wire span between the frame's first
    rise and last fall; tau anchors bit 0 at BIAS_U."""
    first = None
    last = None
    np_ = 0
    for p in _pulse_stream(samples):
        OPS["pulse"] += 1
        if first is None:
            first = p
        last = p
        np_ += 1
    if np_ < 8:
        return None
    mid_r0 = (first[0] + first[1]) >> 1           # u16 cycles
    mid_fl = (last[2] + last[3]) >> 1
    span = mid_fl - mid_r0
    if span <= 0:
        return None
    w_u = (NB - 1) * BIT_U + H1P                  # exact wire span in TU
    OPS["div"] += 1
    K = _idiv(_u32(w_u << KQ), span)              # ** 32-bit ** dividend
    if not (K_MIN <= K <= K_MAX):
        return None
    tau = _s16(BIAS_U - ((_u32(mid_r0 * K) >> KQ)))
    OPS["mul"] += 1
    return _u16(K), tau, np_


def _refine(samples, K, tau):
    """One residual-regression iteration: nearest-lattice residuals of the
    rise-bracket midpoints, two-half means -> slope + offset correction.

    Retained state: 2x(N u8, Se s32, Sy u32) + K,tau.  All products are
    flagged; no accumulator can exceed 32 bits (Se <= 230*64, Sy <=
    230*57.6k, K*de <= 60k*127)."""
    y_end = BIAS_U + NB * BIT_U + TAIL_U
    mid_u = BIAS_U + (NB // 2) * BIT_U
    n_lo = n_hi = 0
    se_lo = se_hi = 0                             # s32
    sy_lo = sy_hi = 0                             # u32
    for p in _pulse_stream(samples):
        OPS["pulse"] += 1
        y = _map((p[0] + p[1]) >> 1, K, tau)
        if y < 0:
            y = 0
        if y > y_end:
            break
        q = (y + BIT_H) >> BIT_SH                 # nearest lattice index
        e = _s16(y - (q << BIT_SH))               # in [-BIT_H, BIT_H-1]
        # (an interval-censored residual was tried here and MEASURED
        # catastrophic -- once most brackets straddle, the censored mean
        # has no gradient; the censoring belongs in the _polish search)
        if y < mid_u:
            n_lo += 1
            se_lo = _s32(se_lo + e)
            sy_lo = _u32(sy_lo + y)
        else:
            n_hi += 1
            se_hi = _s32(se_hi + e)
            sy_hi = _u32(sy_hi + y)
    if n_lo < 2 or n_hi < 2:
        return K, tau
    OPS["div"] += 4
    me_lo = _idiv(se_lo, n_lo)                    # s16
    me_hi = _idiv(se_hi, n_hi)
    my_lo = _idiv(sy_lo, n_lo)                    # u16
    my_hi = _idiv(sy_hi, n_hi)
    de = _s16(me_hi - me_lo)
    dy = my_hi - my_lo
    if dy <= 0:
        return K, tau
    OPS["mul"] += 1
    OPS["div"] += 1
    dk = _idiv(_s32(K * de), dy)                  # ** 32-bit ** product
    n = n_lo + n_hi
    me = _idiv(_s32(se_lo + se_hi), n)
    my = _idiv(_u32(sy_lo + sy_hi), n)
    OPS["div"] += 2
    OPS["mul"] += 1
    # tau correction evaluated at the mean position (see report):
    # dtau = -mean_e + de*(mean_y - tau)/dy
    OPS["div"] += 1
    dtau = -me + _idiv(_s32(de * (my - tau)), dy)  # ** 32-bit ** product
    K2 = K - dk
    if not (K_MIN <= K2 <= K_MAX):
        return K, tau
    return _u16(K2), _s16(tau + dtau)


# (A third, interval-censored lock stage -- a small (dK, dtau) hit-count
# Hough polish, the host FINE analog -- was built and MEASURED net
# negative here: its hit plateaus are ~5 TU wide and the argmax inside
# them is noise, which perturbs the (5,6) boundary more than the ~2 TU
# tilt it removes.  Removed; see EMBEDDED_FEASIBILITY.md.)

# -------------------------------------------------------- segment streaming

def _seg_stream(samples, K, tau):
    """Forward-only segment generator: (k0, k1, u, v, fam) with
    gap-accounting bit indices, same-bit merges, latch-tail drop.
    u/v = fall bracket in TU relative to the k0 lattice; fam = slot of
    the last high sample.  Retained state: one pending segment."""
    y_end = BIAS_U + NB * BIT_U + TAIL_U
    pend = None                                   # (k0, yfa, yfb, fam)
    n = 0
    y_prev = None
    for p in _pulse_stream(samples):
        OPS["pulse"] += 1
        (ra, rb, fa, fb, sfa, nh) = p
        mid = (ra + rb) >> 1
        y = _map(mid, K, tau)
        if y < 0:
            y = 0
        if y > y_end:
            break
        if y_prev is None:
            n = 0                                 # hard anchor: bit 0
        else:
            d = y - y_prev
            dn = (d + BIT_H) >> BIT_SH
            if dn > 0:
                n += dn
        y_prev = y
        yfa = _map(fa, K, tau) + OADJ_U[sfa]
        yfb = _map(fb, K, tau) + OADJ_U[(sfa + 1) & 7]
        if pend is not None and n == pend[0]:
            pend = (pend[0], yfa, yfb, sfa)       # spurious split: merge
            continue
        if pend is not None:
            k0 = pend[0]
            base = BIAS_U + k0 * BIT_U
            yield (k0, min(n, NB), _s16(pend[1] - base),
                   _s16(pend[2] - base), pend[3])
        if n >= NB:
            pend = None
            break
        pend = (n, yfa, yfb, sfa)
    if pend is not None:
        k0 = pend[0]
        base = BIAS_U + k0 * BIT_U
        yield (k0, NB, _s16(pend[1] - base), _s16(pend[2] - base), pend[3])


def _a_bounds(k0, k1):
    amin, amax = 0, k1 - k0
    for t in range(k0, min(k1, NB)):
        kb = KNOWN[t]
        if kb == 1:
            amin = max(amin, t - k0 + 1)
        elif kb == 0:
            amax = min(amax, t - k0)
    return amin, amax


# --------------------------------------------------------- calibration (P3)

def _label_interval(k0, k1, u, v, a, h0p, h1p):
    """(cls, lo, hi) implied by a labelled pulse, or None (mirrors the
    host's _label_interval, integer TU)."""
    L = k1 - k0
    if a == 0:
        return (0, u, v)
    if a == L:
        off = (L - 1) * BIT_U
        return (1, _s16(u - off), _s16(v - off))
    mid = (u + v) >> 1
    d1 = abs(mid - ((a - 1) * BIT_U + h1p))
    d0 = abs(mid - (a * BIT_U + h0p))
    if min(d0, d1) > LAB_OUT:
        return None
    if d1 <= d0:
        off = (a - 1) * BIT_U
        return (1, _s16(u - off), _s16(v - off))
    off = a * BIT_U
    return (0, _s16(u - off), _s16(v - off))


class _Calib:
    """Interval-intersection width fit, global + per bracket family.

    Censoring-correct: each labelled fall bracket constrains its class
    width to an interval; the family fit is the intersection of the
    family's intervals, clamped to the global fit +- FAM_CLAMP.  (A
    mean-residual per-family offset was tried first and MEASURED worse
    than nothing -- label selection effects bias means; intervals are
    immune, which is the same reason the host uses interval-censored
    fits throughout.)

    RAM: global 4 x s16 + 2 x u8; per family 8 x (4 x s16 + 2 x u8)
    = 90 B total."""

    def __init__(self, gap56=(154, 128)):
        self.lo0, self.hi0 = -0x4000, 0x3FFF
        self.lo1, self.hi1 = -0x4000, 0x3FFF
        self.n0 = self.n1 = 0
        self.flo0 = [-0x4000] * 8                 # s16
        self.fhi0 = [0x3FFF] * 8
        self.flo1 = [-0x4000] * 8
        self.fhi1 = [0x3FFF] * 8
        self.fn0 = [0] * 8                        # u8
        self.fn1 = [0] * 8
        self.h0c, self.h1c = H0P, H1P
        self.h0f = [H0P] * 8
        self.h1f = [H1P] * 8
        # eps analog: fold histograms + labelled zone bounds, fams 5 & 6
        self.gap56 = gap56                        # mapped family gaps (TU)
        self.c0 = {5: (H0P + H1P - gap56[0]) >> 1,
                   6: (H0P + H1P - gap56[1]) >> 1}
        self.hist = {5: [0] * 64, 6: [0] * 64}    # 2-TU bins, u8 counts
        self.labx0 = {5: -0x4000, 6: -0x4000}     # max labelled 0 phase (d)
        self.labx1 = {5: 0x3FFF, 6: 0x3FFF}       # min labelled 1 phase (d)
        self.labx0b = {5: -0x4000, 6: -0x4000}    # 2nd max labelled 0
        self.labx1b = {5: 0x3FFF, 6: 0x3FFF}      # 2nd min labelled 1

    def cloud(self, u, fam):
        """Pooled fold-phase histogram (every pulse of fams 5/6, blind)."""
        if not EPS56 or fam not in (5, 6) or u < 0:
            return
        d = (u & (BIT_U - 1)) - self.c0[fam]      # fold into one bit
        if -EPS_HIST <= d < EPS_HIST:
            b = (d + EPS_HIST) >> 1
            if self.hist[fam][b] < 255:
                self.hist[fam][b] += 1

    def add(self, k0, k1, u, v, fam, a):
        li = _label_interval(k0, k1, u, v, a, H0P, H1P)
        if li is None:
            return
        cls, lo, hi = li
        if cls == 0:
            self.lo0 = max(self.lo0, lo)
            self.hi0 = min(self.hi0, hi)
            self.n0 += 1
            self.flo0[fam] = max(self.flo0[fam], lo)
            self.fhi0[fam] = min(self.fhi0[fam], hi)
            self.fn0[fam] = min(255, self.fn0[fam] + 1)
        else:
            self.lo1 = max(self.lo1, lo)
            self.hi1 = min(self.hi1, hi)
            self.n1 += 1
            self.flo1[fam] = max(self.flo1[fam], lo)
            self.fhi1[fam] = min(self.fhi1[fam], hi)
            self.fn1[fam] = min(255, self.fn1[fam] + 1)
        if EPS56 and fam in (5, 6) and lo >= 0:
            d = (lo & (BIT_U - 1)) - self.c0[fam]
            if -EPS_HIST <= d < EPS_HIST:
                if cls == 0:
                    if d > self.labx0[fam]:
                        self.labx0b[fam] = self.labx0[fam]
                        self.labx0[fam] = d
                    elif d > self.labx0b[fam]:
                        self.labx0b[fam] = d
                else:
                    if d < self.labx1[fam]:
                        self.labx1b[fam] = self.labx1[fam]
                        self.labx1[fam] = d
                    elif d < self.labx1b[fam]:
                        self.labx1b[fam] = d

    def finish(self):
        def fit(n, lo, hi, prior, glo, ghi):
            if n < LAB_MIN:
                return prior
            h = (lo + hi) >> 1 if lo > hi else min(max(prior, lo), hi)
            return h if glo <= h <= ghi else prior
        h0 = fit(self.n0, self.lo0, self.hi0, H0P, H0_LO, H0_HI)
        h1 = fit(self.n1, self.lo1, self.hi1, H1P, H1_LO, H1_HI)
        if not (SEP_LO <= h1 - h0 <= SEP_HI):
            h0, h1 = H0P, H1P
        self.h0c, self.h1c = h0, h1

        def ffit(n, lo, hi, g):
            if not FAM_OFFSETS or n < FAM_MIN or lo > hi:
                return g
            h = min(max(g, lo), hi)               # clamp global into family
            return min(max(h, g - FAM_CLAMP), g + FAM_CLAMP)
        for f in range(8):
            self.h0f[f] = ffit(self.fn0[f], self.flo0[f], self.fhi0[f], h0)
            self.h1f[f] = ffit(self.fn1[f], self.flo1[f], self.fhi1[f], h1)
        if EPS56:
            for i, f in enumerate((5, 6)):
                th = self._theta56(f)
                if th is None:
                    continue
                # translate: theta was found in the prior-centred fold
                # coordinate; the decision tie point uses the fitted h's
                c_fit = (self.h0c + self.h1c - self.gap56[i]) >> 1
                delta = th + self.c0[f] - c_fit
                delta = max(-EPS_CLAMP56, min(EPS_CLAMP56, delta))
                # a family h-shift moves the hinge tie point by delta
                self.h0f[f] = _s16(self.h0f[f] + delta)
                self.h1f[f] = _s16(self.h1f[f] + delta)

    def _theta56(self, f):
        """Largest label-feasible density gap in the family's fold cloud
        (integer _zone_gap_theta + the host's pure-zero-family floor),
        in the prior-centred d coordinate.  Returns None to leave the
        boundary at the model tie point."""
        hist = self.hist[f]
        x0 = self.labx0[f]
        x1 = self.labx1[f]
        has0 = x0 > -0x4000
        has1 = x1 < 0x3FFF
        zlo = max(-EPS_ZONE, x0 + 1)
        zhi = min(EPS_ZONE, x1)
        theta = None
        if zlo < zhi:
            blo = (zlo + EPS_HIST) >> 1
            bhi = (zhi - 1 + EPS_HIST) >> 1
            occ = [b for b in range(blo, bhi + 1) if hist[b]]
            if not occ:
                if has0 and has1:
                    theta = (zlo + zhi) >> 1
            else:
                # sentinel edges + occupied bins; largest empty span
                pts = [zlo] + [((b << 1) - EPS_HIST) + 1 for b in occ] + [zhi]
                bi, bg = 0, -1
                for i in range(len(pts) - 1):
                    g = pts[i + 1] - pts[i]
                    if g > bg:
                        bg, bi = g, i
                ok = bg >= EPS_GAP_MIN
                if ok and len(pts) >= 5:
                    # sweeping-cloud guard: the winning gap must dominate
                    # the typical spacing (host: bg >= 2.5 * median gap)
                    OPS["mul"] += 2
                    ok = 2 * bg * (len(pts) - 1) >= 5 * (zhi - zlo)
                if ok:
                    theta = (pts[bi] + pts[bi + 1]) >> 1
        # label window clamp (host _preg_boundary): the boundary must keep
        # labelled examples on their right side, but a LONE extreme label
        # is soft evidence (38 ns slot-5 sampling noise) and only gets the
        # wide EPS_SLACK1 trust radius; two concurring labels tighten it
        # to EPS_SLACK.  The prior (theta = 0, the model tie point) stands
        # unless the labels or the split push it.  Mutually conflicting
        # label windows pin the boundary at the conflict midpoint.
        if has0 or has1:
            wlo = -EPS_ZONE
            whi = EPS_ZONE
            if has0:
                wlo = x0 - EPS_SLACK1
                if self.labx0b[f] > -0x4000:
                    wlo = max(wlo, self.labx0b[f] - EPS_SLACK)
            if has1:
                whi = x1 + EPS_SLACK1
                if self.labx1b[f] < 0x3FFF:
                    whi = min(whi, self.labx1b[f] + EPS_SLACK)
            if wlo > whi:
                theta = (wlo + whi) >> 1
            else:
                theta = min(max(theta if theta is not None else 0,
                                wlo), whi)
        # pure-zero family: nothing in the clear-1 range -> the cloud top
        # is the h0 edge; the boundary belongs above it
        top = None
        clear1 = False
        for b in range(64):
            if not hist[b]:
                continue
            d = ((b << 1) - EPS_HIST) + 1
            if d > EPS_CLEAR1:
                clear1 = True
            elif d > -EPS_CLAMP56:
                top = d if top is None else max(top, d)
        if not clear1 and top is not None:
            floor = top + EPS_TOPM
            theta = floor if theta is None else max(theta, floor)
            if has1 and x1 + EPS_SLACK > floor:
                # a labelled 1 above the floor caps it; one inside the
                # top cloud is a noise collision -- the cap then yields
                theta = min(theta, x1 + EPS_SLACK)
        return theta


def _calibrate(samples, K, tau, extra=None):
    """P3: stream segments, feed marker-forced labels (plus optional
    self-train labels from a previous decision pass) into _Calib."""
    OPS["mul"] += 2
    gap56 = ((6 * K) >> KQ, (5 * K) >> KQ)     # mapped (5,6)/(6,7) gaps
    cal = _Calib(gap56)
    for (k0, k1, u, v, fam) in _seg_stream(samples, K, tau):
        cal.cloud(u, fam)
        if k1 > NB:
            continue
        known_all = True
        for t in range(k0, min(k1, NB)):
            if KNOWN[t] < 0:
                known_all = False
                break
        if known_all:
            amin, amax = _a_bounds(k0, k1)
            if amin == amax:
                cal.add(k0, k1, u, v, fam, amin)
            continue
        if extra is not None:
            a, m = extra(k0, k1, u, v, fam)
            if a is not None and m >= ST_M:
                cal.add(k0, k1, u, v, fam, a)
    cal.finish()
    return cal


# ----------------------------------------------------------- decision (P4)

def _hinge(u, v, h):
    g = 0
    if u - h > g:
        g = u - h
    if h - v > g:
        g = h - v
    return g


def _decide(k0, k1, u, v, fam, cal):
    """Marker-constrained leading-ones argmin by interval hinge.

    Returns (a_hat, cost, costs, amin, amax, interior_list, a_free).
    Ties break to fewer ones (the measured dead-window prior)."""
    L = k1 - k0
    uu = u
    vv = v
    h0c, h1c = cal.h0f[fam], cal.h1f[fam]
    amin, amax = _a_bounds(k0, k1)
    costs = []
    inter = []
    for a in range(0, L + 1):
        OPS["cand"] += 1
        if a == 0:
            h = h0c
            c = _hinge(uu, vv, h)
            it = uu < h <= vv
        else:
            h = (a - 1) * BIT_U + h1c
            c = _hinge(uu, vv, h)
            it = uu < h <= vv
            if a < L:
                h2 = a * BIT_U + h0c
                c2 = _hinge(uu, vv, h2)
                if c2 < c:
                    c = c2
                if uu < h2 <= vv:
                    it = True
        costs.append(c)
        inter.append(it)
    # tie-break: least cost, then INTERIOR before boundary-grazing (an
    # interior fall is fully explained data, hinge==0 at the bracket edge
    # is a measure-zero graze -- measured: this one rule decides rnd3_2's
    # last knife bit), then fewer ones (the dead-window prior)
    a_free = min(range(L + 1),
                 key=lambda a: (costs[a], not inter[a], a))
    lo = max(0, amin)
    hi = min(L, amax)
    if lo > hi:
        lo, hi = 0, L                             # infeasible constraints
    a_hat = min(range(lo, hi + 1),
                key=lambda a: (costs[a], not inter[a], a))
    return a_hat, costs[a_hat], costs, lo, hi, inter, a_free


def _decide_pass(samples, K, tau, cal):
    """P4/P6: stream segments, decide, emit bits + 1-bit confidence +
    dead-tie marks + knife candidates + blind quality counters.

    RAM: bits/conf/tied bit-arrays (NB/8 each), knife list, counters."""
    bits = [0] * NB
    mgv = [255] * NB
    conf = [0] * NB                               # 1-bit: margin >= CONF_M
    tied = [0] * NB                               # 1-bit: dead-window tie
    knife = []                                    # <= KNIFE_MAX bit idx
    infeasible = 0
    label_err = 0
    n_seg = 0
    first_k0 = None
    for (k0, k1, u, v, fam) in _seg_stream(samples, K, tau):
        n_seg += 1
        if first_k0 is None:
            first_k0 = k0
        if k0 >= NB:
            continue
        a_hat, c_hat, costs, lo, hi, inter, a_free = _decide(
            k0, k1, u, v, fam, cal)
        if c_hat > INFEAS_U:
            infeasible += 1
        known_all = all(KNOWN[t] >= 0 for t in range(k0, min(k1, NB)))
        dead = sum(1 for x in inter if x) >= 2
        if known_all and lo == hi and a_free != lo and not dead:
            # a DEAD marker window (both hypotheses interior) carries no
            # width evidence -- at the fast HSI corner the (7,0) bracket
            # swallows the whole discriminating interval on half the
            # pulses, which is the physical corner ceiling, not a
            # miscalibration; counting those as label errors was measured
            # to refuse the entire +5..+7.5% corner
            label_err += 1
        # dead-window tie: two interior candidates inside the allowed range
        ins = [a for a in range(lo, hi + 1) if inter[a]]
        if len(ins) >= 2 and a_hat in ins[:2]:
            t = k0 + ins[0]
            if t < NB:
                tied[t] = 1
        # emit bits + per-bit margins (prefix/suffix minima of costs)
        kk1 = min(k1, NB)
        for t in range(k0, kk1):
            OPS["bit"] += 1
            off = t - k0
            bits[t] = 1 if off < a_hat else 0
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            if c0 is None or c1 is None:
                m = 255
            else:
                m = min(255, abs(c0 - c1))
            mgv[t] = 0 if tied[t] else m
            if m >= CONF_M and not tied[t]:
                conf[t] = 1
        # knife candidates: single-bit payload pulses in the two razor
        # families -- (5,6), whose 375 ns inter-sample gap equals h1-h0
        # so the 0/1 window is a few ns, and (6,7), measured to carry
        # interleaved classes a threshold cannot split (dense_0 bit 69).
        # The byte-period vote is the only evidence that decides them.
        if fam in (5, 6) and k1 - k0 == 1 and 32 <= k0 < NB - 32:
            mm = min(255, abs(costs[0] - costs[1])) if len(costs) > 1 else 255
            if mm < KNIFE_M and len(knife) < KNIFE_MAX:
                knife.append(k0)
    return dict(bits=bits, mgv=mgv, conf=conf, tied=tied, knife=knife,
                infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, first_k0=first_k0)


# ------------------------------------------------------- byte-period votes

def _votes(st):
    """Dead-window + knife-bit byte-period votes on the emitted arrays.
    Pure bit-array work (no sample re-scan); mirrors the host's gated
    votes with the 1-bit confidence map standing in for LLRs."""
    bits, conf, tied = st["bits"], st["conf"], st["tied"]
    resolved = [0] * NB
    p_lo, p_hi = 32, NB - 32
    # per-lag byte-periodicity proof over confident, non-knife bits.
    # BOTH votes are gated by it: an ungated dead vote was measured (on a
    # production-size 448-bit synthetic random payload) to flip a dead
    # bit on three coincidentally unanimous siblings -- with the gate the
    # fewer-ones prior stands there (measured 82 percent right), while
    # periodic payloads still prove their lag and keep the vote.
    kn = set(st["knife"])
    lag_ok = {}
    for lag in (8, 16):
        n_pair = agree = 0
        for t in range(p_lo, p_hi - lag):
            s = t + lag
            if t in kn or s in kn or tied[t] or tied[s]:
                continue
            if not (conf[t] and conf[s]):
                continue
            n_pair += 1
            agree += 1 if bits[t] == bits[s] else 0
        OPS["mul"] += 2
        lag_ok[lag] = (n_pair >= KNIFE_PAIR_MIN
                       and agree * 100 >= KNIFE_AGREE_PCT * n_pair)
    # dead-window vote: >= DEAD_VOTE_MIN unanimous confident siblings on
    # proven lags
    if lag_ok[8] or lag_ok[16]:
        for t in range(p_lo, p_hi):
            if not tied[t]:
                continue
            votes = []
            for dt in (-16, -8, 8, 16):
                if not lag_ok[abs(dt)]:
                    continue
                s = t + dt
                if p_lo <= s < p_hi and not tied[s] and conf[s]:
                    votes.append(bits[s])
            if len(votes) >= DEAD_VOTE_MIN and len(set(votes)) == 1:
                bits[t] = votes[0]
                resolved[t] = 1
    if lag_ok[8] or lag_ok[16]:
        for t in st["knife"]:
            if resolved[t]:
                continue
            votes = []
            for dt in (-16, -8, 8, 16):
                if not lag_ok[abs(dt)]:
                    continue
                s = t + dt
                if p_lo <= s < p_hi and s not in kn and not tied[s] \
                        and conf[s]:
                    votes.append(bits[s])
            if votes and len(set(votes)) == 1:
                bits[t] = votes[0]


# ------------------------------------------------------------------ decode

def _decode_full(samples):
    seed = _seed(samples)
    if seed is None:
        return None
    K, tau, np_ = seed
    for _ in range(2):                            # P2 x2
        K, tau = _refine(samples, K, tau)
    cal = _calibrate(samples, K, tau)             # P3
    st = _decide_pass(samples, K, tau, cal)       # P4
    if SELF_TRAIN:
        cal1 = cal

        def extra(k0, k1, u, v, fam):
            a_hat, c_hat, costs, lo, hi, inter, a_free = _decide(
                k0, k1, u, v, fam, cal1)
            t = k0 + a_hat - 1 if a_hat > 0 else k0
            t = min(max(t, k0), min(k1, NB) - 1)
            off = t - k0
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            m = 255 if (c0 is None or c1 is None) else min(255, abs(c0 - c1))
            return a_hat, m
        cal = _calibrate(samples, K, tau, extra=extra)   # P5
        st = _decide_pass(samples, K, tau, cal)          # P6
    if VOTES:
        _votes(st)
    return st


def decode_state(samples):
    return _decode_full(samples)


def decode(samples, meta):
    if not samples:
        return None
    st = _decode_full(samples)
    if st is None:
        return None
    bits = st["bits"]
    violations = sum(1 for t in range(NB)
                     if KNOWN[t] >= 0 and bits[t] != KNOWN[t])
    if violations > 0 or st["infeasible"] > GATE_INFEAS \
            or st["label_err"] > GATE_LABERR:
        return None
    payload = bytearray(N_PAYLOAD)
    for i in range(N_PAYLOAD):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[32 + 8 * i + j]
        payload[i] = b
    return bytes(payload)
