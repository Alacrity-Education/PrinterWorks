"""embedded_v2 -- v2.3 STM8-shaped WS2812 decoder: CRC16 chase, PERMISSIVE.

Implements EMBEDDED_V2_SPEC.md on top of the v1 integer pipeline
(approaches/embedded_ref.py).  Same decode(samples, meta) contract and the
same target constraints:

  * integer arithmetic only (8/16/32-bit; Python ints used AS IF fixed
    point, with range asserts at every load-bearing assignment);
  * no floats, no transcendentals, no numpy;
  * O(n) forward-only streaming passes over the sample stream (5 scans,
    unchanged from v1 -- the chase adds NO pass over the capture buffer);
  * working-set arrays sized by the frame, not the capture; every retained
    byte enumerated below.

WIRE v2.3 (owner decision 2026-09-07; supersedes v2.2's 4-byte markers
and [CRC8]*4 check block):

  frame    = HEADER(3) || DATA(ND) || (C16_HI C16_LO) x3 || TRAILER(3)
  HEADER   = FF AA 65        TRAILER = 9A 00 FF        (48 known bits)
             TRAILER[1] = 00 is the worst-case-ZEROS calibration probe
             (owner decision 2026-09-07, traded for the end-of-frame
             bit-period ruler: +26.7 points of delivery on silicon).
  CRC16    = CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection,
             xorout 0x0000, over the DATA bytes only.
             crc16("123456789") = 0x29B1.
  test     : ND=16 -> payload' 22 B, frame 28 B = 224 bits (this default)
  production: ND=48 -> payload' 54 B, frame 60 B = 480 bits (_configure(48))
             = EXACTLY 20 WS2812 LEDs.  NB is UNCHANGED from v2.2 at both
             geometries (2 marker bytes traded for 2 check bytes), so the
             capture buffer sizing and the pad law are untouched.

  REFERENCE = INDEPENDENT PER-BYTE MAJORITY over the three copies:
     ref_HI = majority(C[0], C[2], C[4]),  ref_LO = majority(C[1], C[3], C[5])
  With 3 votes no tie is possible: a byte position either has a unique
  >= 2-vote majority or all three votes differ.  Two copies damaged in
  DIFFERENT byte positions -- which destroys any block-level vote --
  still leaves 2 good votes at each position, so the exact 16-bit
  reference comes back.  When a position splits, its distinct values are
  enumerated as candidates and the references are the cross product
  (<= REF_MAX = 9), ranked by decoded per-byte confidence.

  SINGLE TRANSMISSION: one copy per logical frame, no repeats, no sequence
  numbers.  A refusal IS a missed frame.

THE OWNER DIRECTIVE THAT SHAPES v2.3: **ALMOST ALWAYS EMIT.**  Refusals
are now the thing to minimise; emit even on an imperfect reconstruction
PROVIDED the 16-bit check validates the payload.  The 16-bit check is
what makes that safe -- 256x stronger per trial than v2.2's CRC8 -- so a
wide search is affordable where it previously was not:

    fa_budget(0.2 %) = 131 wrong trials at 1 reference   (16-bit check)
                     =   0 wrong trials                  (8-bit check)

THE THREE RELAXATIONS (v2.3, owner-directed; v2.2/v2.1 compat modes keep
the old gates bit-for-bit, so the acquired corpora reproduce exactly):

  A. CLOCK RANGE (kills R1 + most R3).  K_MIN/K_MAX widened and
     GATE_INFEAS raised so distorted fits are PARSED and CHECKED instead
     of refused.  Bounds picked empirically (dev_prod/relax_sweep.py).
       K window   46000..60000  ->  40000..64000  (eps +31 % .. -18 %)
       GATE_INFEAS         4    ->  24
  B. MARKER THRESHOLD (kills R2).  All-or-nothing marker validation
     becomes a threshold over the 48 known marker bits: refuse only at
     mismatches > MK_TOL, and feed the mismatch count FORWARD as
     confidence (it caps the reference enumeration) instead of vetoing.
     Per owner directive the first and last frame byte are NOT required
     to validate -- there is no special case for them anywhere.
       R2 rule    violations > 0  ->  violations > MK_TOL (= 12 of 48)
  C. CHASE WIDTH (kills R7 + most R8).  A_MAX 5 -> 11 with weight <= 2
     enumeration: 1 + 11 + C(11,2) = 67 flip sets.  The v2.2 SS7.10 W2
     bound was sized for an 8-bit check and is RE-SIZED here against the
     16-bit table; the hard bound is now a cap on RESIDUAL COMPARISONS
     (each one 2^-16 of exposure), so a split reference costs budget
     rather than silently multiplying risk:
       A_MAX 5 -> 11,  A_PAIR 3 -> 11,  MG_PAIR 4 -> 8,
       T_MAX (residual comparisons) = 131  [= crc.fa_budget(0.002, 1)]
       R7 fires at n_weak > 11; R5 (n_tied) is RETIRED -- measured
       +798 emissions over 63 924 production decodes, 0 of them wrong,
       every one a DIRECT accept.  A gate that refuses frames whose
       16-bit check VALIDATES contradicts the directive it serves.

  ALIAS GUARD REMOVED, WITH PROOF.  v2.2's guard existed because
  ord(x) mod 0x107 = 127 < 128 data bits, so two data positions 127 bits
  apart shared a syndrome.  For 0x11021, ord(x) = 32767 and the 384
  production data-bit syndromes (128 test) are ALL DISTINCT -- asserted
  exhaustively in _selftest().  The guard can never fire, so it is not
  computed; info["alias_cmp"] is 0 by construction in all three
  implementations.

  PARITY GATE KEPT, AND IT IS STILL EXACT.  x^16+x^12+x^5+1 has four
  terms, so P(1) = 0 and 0x11021 IS divisible by (x+1)
  (0x11021 = (x+1) * 0xF01F, cofactor primitive, ord 32767).  Every
  single-bit syndrome therefore has ODD parity and a weight-w data-only
  flip has syndrome parity w mod 2 -- the free phase skip carries over
  verbatim from v2.2, and odd-weight errors are structurally detected.
  (bench/crc.py's prose claimed the opposite; corrected, see _selftest.)

WHAT CHANGED vs v2.2 (spec section in parens):

  CHANGED  frame geometry (SS2): 3+3 markers, 6-byte check block, PP_LO
           24; NB identical at both geometries.
  CHANGED  check (SS7.1): CRC-16/CCITT-FALSE replaces CRC-8/SMBUS.
           _crc16 bitwise; XS[] syndrome table (u16 per DATA byte) +
           <= 7 xtime folds replaces XPOW[127] + a %127 reduction.
  CHANGED  reference (SS7.1): independent per-byte majority + ranked
           cross-product enumeration replaces the block-level
           >= 2-of-4 vote.
  CHANGED  budget accounting (SS7.6/7.10): T_MAX counts RESIDUAL
           COMPARISONS, not flip sets, so multi-reference trials pay for
           what they expose.
  REMOVED  the alias guard (SS7.7) -- provably inert at 16 bits.
  KEPT     the votes removal (SS5.2), OADJ_U closure (SS5.3), no
           self-train (SS5.4), the margin stream + top-A_MAX candidate
           list (SS6), the 5-phase data-minimal enumeration and its
           parity gate (SS7.4).

FIXED-POINT FORMATS -- v1 contract carried forward verbatim (SS4), plus:

  quantity               format  range/units
  ---------------------  ------  ---------------------------------------
  mgv per-bit margin     u8      TU, saturating at 255; 0 = tie-decided
  r / r_base / R         u16     CRC16 residual / chase reference
  cand_t[A_MAX]          u16     payload' bit index (< 8*NPP <= 432)
  cand_m[A_MAX]          u8      the margin, list sorted (m, index) asc
  n_weak, n_tied         u16     counts over all payload' bits
  chk_conf[CHK_LEN]      u16     sum of 8 u8 margins per check byte
                                 (reference ranking when a position
                                 splits -- now a LIVE path, not a flag)
  XS[ND]                 u16[]   flash const: x^(16 + 8*(ND-1-p))

REFUSAL POLICY (SS9.1, evaluated in this order; v2.3 thresholds):
  R1 hard lock failure          no seed / K outside [K_MIN, K_MAX]
  R2 marker threshold           violations > MK_TOL (12 of 48)
  R3 infeasible                 infeasible > GATE_INFEAS (24)
  R4 label error > 6            v1, unchanged (dead-window adaptation)
  R5 emit gate                  n_tied > TIE_EMIT (11)
  R6 no candidate               CRC mismatch and n_weak == 0
  R7 admission                  CRC mismatch and n_weak > A_MAX (11)
  R8 chase exhausted            all ADMISSIBLE trials evaluated, none
                                passed, or the T_MAX comparison cap hit

decode(samples, meta) -> ND DATA bytes (check block stripped) | None.
Deterministic.  decode_ex() additionally returns the per-decode path /
refusal-cause / trial-count record the phase-3 parity harness checks.

Dev tooling: _configure(nd) re-derives the frame constants (production
compiles them); _configure(nd, chk=4) / chk=3 rebuild the SUPERSEDED
v2.2 / v2.1 CRC8 geometries (4-byte markers, block-vote majority, alias
guard on, the old A_MAX=5 gates) so captures_v2{1,2}*.json keep decoding
bit-exactly; _configure(nd, check=False) builds the legacy v2.0 frame
geometry (no check block, chase OFF) for the trim-sweep corpus.
"""


# --------------------------------------------------------------- op counter
# 'sample' = raw sample visited; 'pulse' = pulse processed; 'mul' = 16x16
# multiply; 'div' = division; 'cand' = leading-ones hypothesis; 'scan' =
# pass launch; 'bit' = payload bit emitted; 'trial' = chase flip set
# residual-tested; 'acmp' = alias-guard syndrome compare.
OPS = {"sample": 0, "pulse": 0, "mul": 0, "div": 0, "cand": 0, "scan": 0,
       "bit": 0, "trial": 0, "acmp": 0}


def ops_reset():
    for k in OPS:
        OPS[k] = 0


# ------------------------------------------------------- fixed-point guards

def _u8(x):
    assert 0 <= x <= 0xFF, ("u8 overflow", x)
    return x


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
# Sampler model = dev_calibration/fitted_model.json (EXACT integer cycles);
# unchanged from v1.  The OADJ_U per-slot tweak table is gone (SS5.3): the
# embedded build ships the single fitted geometry.
LOOP_CY = 40
O_CY = (0, 4, 9, 13, 17, 21, 27, 32)
W_CY = (0, -1, 0, 2, 0, 0, 0, 1)

BIT_SH = 9
BIT_U = 1 << BIT_SH                    # 1250 ns in TU (power of two!)
BIT_H = BIT_U >> 1
BIAS_U = BIT_U                         # lattice of bit k at BIAS + k*BIT_U
TAIL_U = 164                           # 400 ns latch tail
H0P = 154                              # 377 ns effective T0H in TU
H1P = 308                              # 752 ns effective T1H in TU
KQ = 20 - BIT_SH                       # K is Q(KQ) TU/cycle
K_NOM = 52429                          # 62.5/TU * 2^KQ
# RELAXATION A -- the accepted lock window.  These are MUTATED by
# _configure(): v2.3 uses the wide (permissive) pair, the v2.2/v2.1/v2.0
# compat modes restore the historical +-12 % guard so the acquired corpora
# reproduce bit-for-bit.  eps = (K_NOM - K)/K, so a LOW K is a FAST wire.
K_MIN_V22, K_MAX_V22 = 46000, 60000    # v2.2: eps +13.97 % .. -12.62 %
K_MIN_V23, K_MAX_V23 = 40000, 64000    # v2.3: eps +31.07 % .. -18.08 %
K_MIN, K_MAX = K_MIN_V23, K_MAX_V23    # (u16 safe: 27.5k * 64000 < 2^31)
# The v2.3 pair is 3x the distance from K_NOM of the widest K that was
# ever RECOVERABLE in the sweeps (48546..56682), capped by the u16 K
# field and the t*K < 2^31 product bound.  MEASURED yield over the v2.2
# window: ZERO deliveries -- see the report.  It is kept because it
# costs nothing and the 16-bit check is the safety net, not because it
# was shown to recover a frame.
FIRST_BR_CY = 4                        # first-sample rise bracket: 250 ns
LATCH_RUN = 200                        # consecutive low samples = latch

# decision / calibration constants (all TU unless noted) -- v1, unchanged
INFEAS_U = 160
LAB_MIN = 3
LAB_OUT = 246
H0_LO, H0_HI = 112, 192
H1_LO, H1_HI = 252, 376
SEP_LO, SEP_HI = 112, 196
FAM_CLAMP = 24
FAM_MIN = 2
# RELAXATION A -- feasibility gate.  Also mutated by _configure().
GATE_INFEAS_V22 = 4                    # v2.2 historical
GATE_INFEAS_V23 = 24                   # v2.3 permissive (measured, SS9.1)
GATE_INFEAS = GATE_INFEAS_V23
GATE_LABERR = 6                        # unchanged in v2.3

# RELAXATION B -- marker threshold over the 48 known v2.3 marker bits
# (64 in the v2.2 compat geometry).  R2 fires at violations > MK_TOL.
# MK_TOL = 0 reproduces v2.2's all-or-nothing rule exactly.
# Per owner directive there is NO special case requiring the first or the
# last frame byte to validate: the threshold is the whole rule.
MK_TOL_V22 = 0
MK_TOL_V23 = 12                        # of 48 known marker bits
MK_TOL = MK_TOL_V23
# ... and the mismatch count fed FORWARD as confidence: above MK_SOFT the
# frame is marker-suspect and the reference enumeration collapses to the
# per-byte majority alone (REF_MAX -> 1), so a suspect lock cannot also
# buy itself 9x the per-comparison exposure.
MK_SOFT = 4

# v2.3 markers (3+3, owner-fixed; the marker-split study kept this split).
# TRAILER[1] is a worst-case-ZEROS calibration probe, not a second
# bit-period ruler: owner decision 2026-09-07 traded 0x55 for 0x00 on the
# study's own controls (+7.0 pts plateau bit-exact reconstruction and a
# t0-p90 tail cut on the model) and the Gate phase's real-silicon A/B
# (+26.7 pts delivery, 71.1 % -> 97.8 %, paired McNemar 25:1, chi2 20.35,
# p<0.001, 0 wrong either way).  Frame sizing is unchanged (3 + N + 6 + 3)
# and the 48 known marker bits are unchanged.
HDR_V23 = bytes.fromhex("FFAA65")
TRL_V23 = bytes.fromhex("9A00FF")
# superseded v2.2/v2.1/v2.0 markers (4+4) -- compat modes only
HDR_V22 = bytes.fromhex("FF00AA65")
TRL_V22 = bytes.fromhex("9A5500FF")
HDR, TRL = HDR_V23, TRL_V23

FAM_OFFSETS = False
EPS56 = True

# eps analog constants -- v1, unchanged (the single most valuable mechanism
# in the pipeline: turning it off was measured at -7 captures)
EPS_ZONE = 32
EPS_HIST = 64
EPS_GAP_MIN = 5
EPS_CLAMP56 = 24
EPS_CLEAR1 = 18
EPS_TOPM = 3
EPS_SLACK = 2
EPS_SLACK1 = 8

# ---- v2.3 chase constants (SS7 as re-sized against the 16-bit table) ----
# Every one of these is MUTATED by _configure() for the compat modes; the
# values below are v2.3 (permissive).
CHK_LEN = 6            # v2.3 check block: (C16_HI, C16_LO) x3
                       # (4 = superseded v2.2 [CRC8]*4, 3 = v2.1 [CRC8]*3)
A_CAP = 15             # leading-ones hypothesis cap -- NORMATIVE, part of
                       # the embedded contract (d_costs[16] RAM bound in
                       # decode.c/decode_asm.s).  Real segments span <= 2
                       # bits; only garbage inputs ever reach the cap, and
                       # the reference must truncate exactly like the
                       # implementations (fuzz_v22 D00 found the gap).
MG_MAX = 8             # TU: a bit is "weak" at margin <= 8 (19.5 ns)

# RELAXATION C -- chase width.  A_MAX 5 -> 11 with weight <= 2:
#   flip sets = 1 + A_MAX + C(A_PAIR, 2) = 1 + 11 + 55 = 67
# at 1 reference that is crc.fa_prob(67, 1) = 0.1022 %, inside the 0.2 %
# wrong-emission target; under CRC8 the same 67 would have been 23.1 %.
A_MAX_V22, A_MAX_V23 = 5, 11
A_PAIR_V22, A_PAIR_V23 = 3, 11
MG_PAIR_V22, MG_PAIR_V23 = 4, 8
# R5 RETIRED in v2.3.  The owner directive is that a frame whose 16-bit
# check VALIDATES must emit; an n_tied veto refuses exactly such frames.
# Measured (dev_prod/wrong_emission.py, 63 924 production decodes):
# retiring the gate adds 798 emissions, 0 of them wrong, and EVERY one is
# a DIRECT accept -- the chase mix does not move at all.  The constant,
# the test and the n_tied counter all stay so restoring it is a
# one-constant change; the retired value is STRUCTURALLY unreachable and
# says so (n_tied counts a subset of the 8*NPP payload' bits, so
# "> 8*NPP + 1" can never hold).  Set by _configure().
TIE_EMIT_V22 = 8
TIE_EMIT_V23 = 8 * (16 + 6) + 1
A_MAX = A_MAX_V23      # candidate list capacity AND admission cap
W_MAX = 2              # max bits flipped per trial (knife-bit repair)
A_PAIR = A_PAIR_V23    # a WEIGHT-2 trial may only combine candidates from
                       # the A_PAIR weakest ...
MG_PAIR = MG_PAIR_V23  # ... and only ones at margin <= MG_PAIR TU.
                       # cand_m is non-decreasing, so the pair-eligible
                       # set is the PREFIX cand[0 .. npair-1] and the test
                       # reduces to one comparison on the LARGER index.
                       # At v2.3 both equal their MG_MAX/A_MAX ceilings:
                       # the bound is now "pairs come only from ADMITTED
                       # weak candidates", and the hard budget bound moved
                       # to T_MAX below (which is what actually caps risk).
TIE_EMIT = TIE_EMIT_V23  # emit gate: absolute count of zero-margin bits

# RELAXATION C -- the hard bound, re-expressed for a 16-bit check.
# T_MAX counts RESIDUAL COMPARISONS (one (r, reference) test, exposure
# 2^-16 each), not flip sets, so a trial whose check block has no per-byte
# majority pays for every extra reference it tries instead of silently
# multiplying the risk.  131 = crc.fa_budget(0.002, 1):
#   fa_prob(131, 1) = 0.1997 % <= 0.2 % < fa_prob(132, 1) = 0.2012 %
# The 67-flip-set enumeration reaches 131 comparisons only when references
# split, which is exactly when the extra exposure is real.
T_MAX_V22, T_MAX_V23 = 16, 131
T_MAX = T_MAX_V23

# ---- LEVER B: DEAD-WINDOW candidates (SS6.4) --------------------------
# A payload' bit's DISCRIMINATING INTERVAL is the only wire-time window
# in which a sample can tell 0 from 1: (base + h0c, base + h1c] after its
# own rising edge, where h0c/h1c are the family-calibrated fall positions
# for a 0 and for a 1.  The whole observation is the fall bracket (u, v]
# -- u the last HIGH sample, v the first LOW sample, ADJACENT in the
# sample comb, so no sample lies strictly between them.  Writing
#     ga = (off*BIT_U + h0c) <= u        gb = v < (off*BIT_U + h1c)
# the HEALTHY case is ga != gb: exactly one of the two candidate fall
# positions lies inside the bracket, i.e. a sample DECIDED the bit.
# ga == gb is degenerate, and covers both ways that can happen:
#   MID  (ga = gb = 1)  the bracket lies INSIDE the window -- a
#         transition was seen, but at NEITHER fitted boundary, so the
#         polarity rests on which boundary is nearer, i.e. on the width
#         fit rather than on a sample
#   DEAD (ga = gb = 0)  the window lies INSIDE the bracket -- no sample
#         inside it at all, both hypotheses admitted
# A DW candidate is such a bit with margin > MG_MAX: degenerate geometry
# carrying a CONFIDENT apparent margin, which is exactly the R6
# "refuse_nocand" mechanism.  Measured over 1 530 frames (8 547 such
# bits): 6.97 % of them are wrong, against 0.09 % for the healthy
# classes and 0.0000 % for EARLY/LATE (dev_lever_b/geomclass.py).
#
# The DW bits join the SAME A_MAX candidate list through the SAME SS6.2
# sorted insertion, with no second pool and no second key: a weak bit has
# margin <= MG_MAX and a DW bit margin > MG_MAX, so the single ascending
# margin key already places every weak entry ahead of every DW entry.
# That makes R7's completeness invariant STRUCTURAL -- if n_weak <=
# A_MAX the list still holds every weak bit, because a DW entry can
# never sort ahead of one -- and truncation drops the WORST DW entry
# first.  Measured against a two-ended layout that ranks the DW pool
# FIRST (dev_lever_b/order.py, 3 483 frames): identical outcome on 3 482
# of them and a DELIVERY instead of a T_MAX refusal on the last, for
# ~80 B less flash.
#
# A_MAX, T_MAX, MG_MAX, MG_PAIR, A_PAIR and TIE_EMIT are all UNCHANGED.
# T_MAX alone bounds the false-accept exposure (131 residual comparisons
# = 0.1997 %), which is why widening the candidate set does not widen
# the per-frame risk.
DW_EN_V22, DW_EN_V23 = 0, 1
DW_EN = DW_EN_V23      # 0 restores the pre-Lever-B behaviour exactly
DW_OFF_MAX = 64        # the test is skipped at off >= 64, which is what
                       # keeps it inside s16 on an arbitrarily long merged
                       # run: off*BIT_U <= 63*512 = 32256 and h1f is
                       # clamped to <= H1_HI + FAM_CLAMP + EPS_CLAMP56 =
                       # 424, so hb + h1c <= 32680 < 32768.  It costs
                       # NOTHING in behaviour: h0f >= H0_LO - FAM_CLAMP -
                       # EPS_CLAMP56 = 64 > 0, so once hb > v the test
                       # already returns "healthy" of its own accord
                       # (hb + h0c > v >= u makes ga false and
                       # hb + h1c > v makes gb true), and hb > v holds
                       # for every off >= 64 that a real segment reaches.
                       # PROVEN bit-identical to a latched running-hb
                       # form over every corpus + fuzz set.
REF_MAX = 9            # 3 HI candidates x 3 LO candidates, the geometric
                       # maximum of the 3-copy cross product
CRC8_POLY = 0x07       # CRC-8/SMBUS  (superseded, compat modes only)
CRC16_POLY = 0x1021    # CRC-16/CCITT-FALSE
CRC16_INIT = 0xFFFF
CHASE_SPLIT_VOTE = 1   # v2.3: the split-reference path is LIVE (the
                       # emit-always directive; under CRC8 it was measured
                       # +0 deliveries at 3x the exposure and shipped OFF).
                       # 0 restores the v2.2 behaviour.
ALIAS_GUARD = 0        # v2.3: PROVABLY inert (ord(x) mod 0x11021 = 32767
                       # and all <= 384 data-bit syndromes are distinct --
                       # asserted in _selftest), so it is not computed.
                       # 1 restores the v2.2 guard for the compat modes.


def _crc8(data):
    """CRC-8/SMBUS, bitwise (table-free -- what the STM8 runs per SS7.1)."""
    r = 0
    for b in data:
        r = _u8(r ^ b)
        for _ in range(8):
            r = ((r << 1) ^ CRC8_POLY) & 0xFF if r & 0x80 else (r << 1) & 0xFF
    return r


def _crc16(data):
    """CRC-16/CCITT-FALSE, bitwise (table-free -- what the STM8 runs).

    poly 0x1021, init 0xFFFF, no reflection, xorout 0.  Check value
    crc16(b"123456789") == 0x29B1 (asserted in _selftest)."""
    r = CRC16_INIT
    for b in data:
        r = _u16(r ^ ((b & 0xFF) << 8))
        for _ in range(8):
            r = ((r << 1) ^ CRC16_POLY) & 0xFFFF if r & 0x8000 \
                else (r << 1) & 0xFFFF
    return _u16(r)


def _xs_table(nd):
    """XS[p] = x^(16 + 8*(ND-1-p)) mod 0x11021, p = 0 .. ND-1.

    The u16 syndrome BASE of DATA byte p: the single-bit syndrome of bit
    weight b inside that byte is XS[p] * x^b, and multiplying by x is one
    shift-and-fold, so _syn16 is a table load plus <= 7 folds (SS7.2).

    Flash: 2*ND bytes -- 96 B at production geometry, against v2.2's
    XPOW[127] + a %127 reduction loop, so the table SHRANK by 31 B while
    the check doubled in width."""
    t = [0] * nd
    r = 1
    for _ in range(16):                    # r = x^16 mod P
        r = ((r << 1) ^ CRC16_POLY) & 0xFFFF if r & 0x8000 \
            else (r << 1) & 0xFFFF
    for p in range(nd - 1, -1, -1):        # p descending = exponent ascending
        t[p] = r
        for _ in range(8):
            r = ((r << 1) ^ CRC16_POLY) & 0xFFFF if r & 0x8000 \
                else (r << 1) & 0xFFFF
    return tuple(t)


XS = _xs_table(16)                     # rebuilt by _configure(nd)


def _syn16(k):
    """CRC16 syndrome of payload'-relative DATA bit k (MSB-first byte
    p = k>>3, bit weight b = 7-(k&7)):

        syn16 = x^(16 + 8*(ND-1-p) + b) mod 0x11021 = XS[p] * x^b

    <= 7 shift-and-fold steps after one u16 table load.  Check bits have
    NO syndrome -- they move the reference, not the residual (SS7.2)."""
    p = k >> 3
    b = 7 - (k & 7)
    assert p < N_DATA, ("syn16 on a check bit", k)
    r = XS[p]
    for _ in range(b):
        r = ((r << 1) ^ CRC16_POLY) & 0xFFFF if r & 0x8000 \
            else (r << 1) & 0xFFFF
    return _u16(r)


def _maj3(a, b, c):
    """The value holding >= 2 of three votes, else None.

    With three votes at most one value can reach two, so there is NO tie
    case: either a unique majority exists or all three differ.  One
    three-compare counting loop, run once per BYTE POSITION instead of
    once per block -- that independence is the whole v2.3 policy."""
    if a == b or a == c:
        return a
    if b == c:
        return b
    return None


def _ref_bytes(C):
    """(ref_HI, ref_LO) by INDEPENDENT per-byte majority over the three
    copies of a 6-byte v2.3 check block.  Either element is None when all
    three copies differ at that position (SS7.1)."""
    return (_maj3(C[0], C[2], C[4]), _maj3(C[1], C[3], C[5]))


def _ranked3(C, idx, conf):
    """Candidate values for ONE byte position, best-confidence first.

    A majority collapses the list to one entry.  Otherwise every distinct
    value is a candidate, ordered by the confidence of the copy carrying
    it (descending; ties keep wire order).  All three differ in that
    case, so no de-duplication is needed -- exactly three candidates."""
    votes = [C[i] for i in idx]
    m = _maj3(*votes)
    if m is not None:
        return [m]
    order = sorted(range(3), key=lambda q: (-conf[idx[q]], q))
    return [votes[q] for q in order]


def _ref_candidates(C, conf, cap):
    """Ordered 16-bit chase references for a v2.3 check block (SS7.1).

    Both positions have a majority (the normal case) -> the single
    reference (HI << 8) | LO, i.e. p_trial = 1/65536.  A split position
    contributes its three distinct values confidence-ranked, and the
    references are the CROSS PRODUCT enumerated in DIAGONAL order --
    rank-sum ascending, then HI-rank ascending:

        (0,0) (0,1) (1,0) (0,2) (1,1) (2,0) (1,2) (2,1) (2,2)

    Each list is already confidence-descending, so the diagonal order is
    monotone in both coordinates: it tries better references first
    without sorting the 9 pairs, which is what makes it affordable on
    target (two nested loops, no sort, no u16 key array).  Truncated to
    `cap`; cap = 1 is the strict per-byte-majority-only policy the
    marker-suspect path (RELAXATION B) falls back to.

    (bench/crc.reference_candidates_v23 sorts the same ranked lists by
    exact confidence SUM -- host tooling for frame verification.  The two
    agree on the single-reference case, which is every frame whose check
    block has a per-byte majority, and can differ only in the ORDER of a
    split enumeration, never in its membership.)"""
    his = _ranked3(C, (0, 2, 4), conf)
    los = _ranked3(C, (1, 3, 5), conf)
    out = []
    for sm in range(len(his) + len(los) - 1):
        for a in range(len(his)):
            b = sm - a
            if 0 <= b < len(los):
                out.append(_u16((his[a] << 8) | los[b]))
                if len(out) >= cap:
                    return out
    return out


def _xpow_table():
    """XPOW[e] = x^e mod (x^8+x^2+x+1), e = 0..126.  ord(x) = 127, so a
    127-entry flash table covers every frame size (SS7.2)."""
    t = []
    r = 1
    for _ in range(127):
        t.append(r)
        r = ((r << 1) ^ CRC8_POLY) & 0xFF if r & 0x80 else (r << 1) & 0xFF
    return tuple(t)


XPOW = _xpow_table()                   # 127 B flash const (exact)
assert XPOW[8] == 0x07 and XPOW[14] == 0xC7 and XPOW[15] == 0x89


def _syn8(k):
    """Single-bit CRC8 syndrome of payload'-relative DATA bit k (MSB-first
    byte p = k>>3, bit-value weight b = 7-(k&7)):

        syn8 = x^(8*(ND-1-p) + b + 8) mod 0x107 = XPOW[j % 127]

    The %127 is a subtract-while->= loop on target (<= 4 iterations at
    ND = 48).  Check bits have NO syndrome -- they move the reference,
    not the residual (SS7.2)."""
    p = k >> 3
    b = 7 - (k & 7)
    assert p < N_DATA, ("syn8 on a check bit", k)
    return XPOW[(8 * (N_DATA - 1 - p) + b + 8) % 127]


def _majn(cs):
    """Unique >=2-vote byte-equality majority over the CHK_LEN decoded
    check bytes (SS7.1).  None when no value reaches 2 votes (full split)
    or when TWO distinct values do (the 2-2 tie, possible at CHK_LEN=4).
    At CHK_LEN=3 this is exactly the old 2-of-3 rule (a tie needs 4
    votes).  The STM8 port is the same counting loop over g_CHK bytes."""
    win = None
    for v in cs:
        cnt = 0
        for w in cs:
            if w == v:
                cnt += 1
        if cnt >= 2:
            if win is None:
                win = v
            elif v != win:
                return None
    return win


def _parity8(x):
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


def _bits_of(bs):
    return [(byte >> (7 - i)) & 1 for byte in bs for i in range(8)]


def _build(npp):
    """Frame bit count + marker template for the CURRENT HDR/TRL.

    v2.3 markers are 3+3 (48 known bits at PP_LO = 24); the compat modes
    keep 4+4 (64 known bits at PP_LO = 32).  NB happens to be identical
    between v2.3 and v2.2 at both geometries -- two marker bytes were
    traded for two check bytes -- so the capture buffer sizing and the
    pad law are untouched by the wire change."""
    hb, tb = _bits_of(HDR), _bits_of(TRL)
    nb = 8 * (len(HDR) + npp + len(TRL))
    known = [-1] * nb
    known[0:len(hb)] = hb
    known[nb - len(tb):nb] = tb
    return nb, known


# Frame geometry (test build default; production compiles ND = 48).
N_DATA = 16                            # DATA bytes (16 test / 48 prod)
NPP = N_DATA + CHK_LEN                 # payload' bytes on the wire
NB, KNOWN = _build(NPP)                # frame bits, marker template
PP_LO, PP_HI = 24, 24 + 8 * NPP        # payload' bit window in frame bits
N_MK = 48                              # known marker bits (RELAXATION B)
CHASE_EN = True
WIRE = 23                              # 23 / 22 / 21 / 20 (legacy)


def _configure(nd, check=True, chk=6):
    """Re-derive frame constants AND the version-dependent gates.

    chk selects the wire version:
      6 = v2.3 (default)  -- 3+3 markers, CRC16 x3, per-byte majority,
                             and the three owner-directed relaxations
      4 = v2.2 (compat)   -- 4+4 markers, [CRC8]*4, block-vote majority,
                             historical gates; keeps captures_v22*.json
      3 = v2.1 (compat)   -- 4+4 markers, [CRC8]*3; keeps captures_v21*
    check=False builds the legacy v2.0 geometry (payload' = DATA, no
    check block, chase disabled) with the v2.2 markers and gates --
    bench evaluation of lock+segmentation on the trim corpus ONLY.

    Every relaxation is scoped here so the acquired corpora reproduce
    bit-for-bit under the compat modes: a parity or regression failure
    can never be blamed on a v2.3 threshold leaking backwards."""
    global N_DATA, NPP, NB, KNOWN, PP_LO, PP_HI, CHASE_EN, CHK_LEN
    global HDR, TRL, WIRE, N_MK, XS
    global K_MIN, K_MAX, GATE_INFEAS, MK_TOL
    global A_MAX, A_PAIR, MG_PAIR, TIE_EMIT, T_MAX
    global CHASE_SPLIT_VOTE, ALIAS_GUARD, DW_EN
    if chk not in (3, 4, 6):
        raise ValueError("chk must be 6 (v2.3), 4 (v2.2) or 3 (v2.1)")
    v23 = (chk == 6) and check
    WIRE = 23 if v23 else (22 if chk == 4 else 21) if check else 20
    N_DATA = nd
    CHK_LEN = chk
    CHASE_EN = bool(check)
    NPP = nd + CHK_LEN if check else nd
    HDR, TRL = (HDR_V23, TRL_V23) if v23 else (HDR_V22, TRL_V22)
    NB, KNOWN = _build(NPP)
    PP_LO = 8 * len(HDR)
    PP_HI = PP_LO + 8 * NPP
    N_MK = 8 * (len(HDR) + len(TRL))
    XS = _xs_table(nd)
    if v23:
        K_MIN, K_MAX = K_MIN_V23, K_MAX_V23
        GATE_INFEAS = GATE_INFEAS_V23
        MK_TOL = MK_TOL_V23
        A_MAX, A_PAIR = A_MAX_V23, A_PAIR_V23
        MG_PAIR, TIE_EMIT = MG_PAIR_V23, 8 * NPP + 1
        T_MAX = T_MAX_V23
        CHASE_SPLIT_VOTE, ALIAS_GUARD = 1, 0
        DW_EN = DW_EN_V23
    else:
        K_MIN, K_MAX = K_MIN_V22, K_MAX_V22
        GATE_INFEAS = GATE_INFEAS_V22
        MK_TOL = MK_TOL_V22
        A_MAX, A_PAIR = A_MAX_V22, A_PAIR_V22
        MG_PAIR, TIE_EMIT = MG_PAIR_V22, TIE_EMIT_V22
        T_MAX = T_MAX_V22
        CHASE_SPLIT_VOTE, ALIAS_GUARD = 0, 1
        DW_EN = DW_EN_V22


def set_chase_budget(a_max=A_MAX_V23, t_max=T_MAX_V23):
    """Set the BUILD-TIME chase budget, the same two parameters the
    firmware takes (Makefile A_MAX / T_MAX -> decode.c -DA_MAX_CFG /
    -DT_MAX_CFG -> decode_asm.s chase_cfg.inc).  Call AFTER _configure(),
    which resets both to the wire version's defaults.

      A_MAX  candidate-list capacity AND the R7 admission cap.  Flip sets
             = 1 + A_MAX + C(A_MAX,2) at W_MAX = 2.
      T_MAX  residual comparisons; it IS the per-frame false-accept bound
             fa = 1 - (1 - 2^-16)^T_MAX.

    A_PAIR TRACKS A_MAX, exactly as decode.c's `#define A_PAIR A_MAX_CFG`
    does: _chase23 sets npair = n and never reads A_PAIR (the SS7.10 test
    is #if'd out in the C precisely because A_PAIR == A_MAX and
    MG_PAIR == MG_MAX), so pinning them together is what keeps the three
    implementations bit-identical at every parameter point.  MG_MAX,
    MG_PAIR, TIE_EMIT, W_MAX and DW_EN are UNTOUCHED.

    The target's counters are 8-bit: dec_info.trials caps A_MAX at 22
    (A_MAX*(A_MAX+1)/2 <= 255) and z_comps/dec_info.comps cap T_MAX at
    255.  This function does NOT enforce those -- the host sweep has to be
    able to explore past them (recon/AMAX_TMAX_SWEEP.md sweeps A_MAX to 40
    and T_MAX to 1048); gen_chase_cfg.py, decode.c's #error pair and
    guard_prod.py check 7 refuse a BUILD outside them."""
    global A_MAX, A_PAIR, T_MAX
    A_MAX = A_PAIR = int(a_max)
    T_MAX = int(t_max)


# ------------------------------------------------------------ pulse stream
# (v1, unchanged)

def _pulse_stream(samples):
    """Forward-only pulse generator: (ra, rb, fa, fb, sfa, nh) in receiver
    CPU cycles; sfa = slot of the last high sample.  Stops at the latch.

    STM8 equivalent: a re-scan of the raw capture buffer; retained state
    is 6 x u16 + 3 x u8 + the loop counters."""
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
    """Receiver cycles -> wire TU:  y = ((t*K) >> KQ) + tau.
    t*K is the ** 32-bit ** intermediate."""
    OPS["mul"] += 1
    y = (_u32(t * K) >> KQ) + tau
    return y


# ------------------------------------------------------------- lock (P1+P2)
# (v1, unchanged -- the known frame length pins K to ~0.1%, single-shot,
# wide-band, no prior: this is the SS13.4 lock mechanism)

def _seed(samples):
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
    # RELAXATION A hardening: tau is an s16 by contract, and the WIDE
    # v2.3 window makes a late-first-rise / short-span capture reachable
    # where BIAS_U - ((mid_r0*K) >> KQ) leaves s16.  This module used to
    # ASSERT there while decode.c / decode_asm.s would silently wrap;
    # refusing R1 instead keeps all three bit-exact BY CONSTRUCTION.
    tau = BIAS_U - ((_u32(mid_r0 * K) >> KQ))
    OPS["mul"] += 1
    if not (-0x8000 <= tau <= 0x7FFF):
        return None
    return _u16(K), _s16(tau), np_


def _refine(samples, K, tau):
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
    OPS["div"] += 1
    dtau = -me + _idiv(_s32(de * (my - tau)), dy)  # ** 32-bit ** product
    K2 = K - dk
    if not (K_MIN <= K2 <= K_MAX):
        return K, tau
    return _u16(K2), _s16(tau + dtau)


# -------------------------------------------------------- segment streaming
# (v1 minus the OADJ_U reads -- SS5.3 formal closure; the table was zero,
# so this is bit-identical to the v1 build)

def _seg_stream(samples, K, tau):
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
        yfa = _map(fa, K, tau)
        yfb = _map(fb, K, tau)
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
# (v1, unchanged)

def _label_interval(k0, k1, u, v, a, h0p, h1p):
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
    """Interval-intersection width fit, global + per bracket family, plus
    the eps analog (v1, unchanged).  RAM: 90 B + 2x64 B histograms (the
    histograms are dead before bits[] is first written -> overlay)."""

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
        self.gap56 = gap56                        # mapped family gaps (TU)
        self.c0 = {5: (H0P + H1P - gap56[0]) >> 1,
                   6: (H0P + H1P - gap56[1]) >> 1}
        self.hist = {5: [0] * 64, 6: [0] * 64}    # 2-TU bins, u8 counts
        self.labx0 = {5: -0x4000, 6: -0x4000}
        self.labx1 = {5: 0x3FFF, 6: 0x3FFF}
        self.labx0b = {5: -0x4000, 6: -0x4000}
        self.labx1b = {5: 0x3FFF, 6: 0x3FFF}

    def cloud(self, u, fam):
        if not EPS56 or fam not in (5, 6) or u < 0:
            return
        d = (u & (BIT_U - 1)) - self.c0[fam]
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
            h = min(max(g, lo), hi)
            return min(max(h, g - FAM_CLAMP), g + FAM_CLAMP)
        for f in range(8):
            self.h0f[f] = ffit(self.fn0[f], self.flo0[f], self.fhi0[f], h0)
            self.h1f[f] = ffit(self.fn1[f], self.flo1[f], self.fhi1[f], h1)
        if EPS56:
            for i, f in enumerate((5, 6)):
                th = self._theta56(f)
                if th is None:
                    continue
                c_fit = (self.h0c + self.h1c - self.gap56[i]) >> 1
                delta = th + self.c0[f] - c_fit
                delta = max(-EPS_CLAMP56, min(EPS_CLAMP56, delta))
                self.h0f[f] = _s16(self.h0f[f] + delta)
                self.h1f[f] = _s16(self.h1f[f] + delta)

    def _theta56(self, f):
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
                pts = [zlo] + [((b << 1) - EPS_HIST) + 1 for b in occ] + [zhi]
                bi, bg = 0, -1
                for i in range(len(pts) - 1):
                    g = pts[i + 1] - pts[i]
                    if g > bg:
                        bg, bi = g, i
                ok = bg >= EPS_GAP_MIN
                if ok and len(pts) >= 5:
                    OPS["mul"] += 2
                    # s16 narrowing proof (embedded port drops the s32
                    # cast here): bg <= zhi-zlo <= 2*EPS_ZONE = 64 and
                    # len(pts)-1 <= bins+1 <= 34, so both sides fit s16.
                    assert 0 <= bg <= 2 * EPS_ZONE, bg
                    assert 2 <= len(pts) <= 36, len(pts)
                    assert -32768 <= 2 * bg * (len(pts) - 1) <= 32767
                    assert -32768 <= 5 * (zhi - zlo) <= 32767
                    ok = 2 * bg * (len(pts) - 1) >= 5 * (zhi - zlo)
                if ok:
                    theta = (pts[bi] + pts[bi + 1]) >> 1
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
                theta = min(theta, x1 + EPS_SLACK)
        return theta


def _calibrate(samples, K, tau):
    """P3: stream segments, feed marker-forced labels into _Calib.
    (v1 minus the self-train extra() hook -- SS5.4.)"""
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
    """Marker-constrained leading-ones argmin by interval hinge (v1),
    truncated at the A_CAP hypothesis cap exactly like the embedded
    implementations (d_costs[16]); the per-bit margin it computes is
    RETURNED, SS6.1."""
    L = k1 - k0
    acap = L if L < A_CAP else A_CAP
    uu = u
    vv = v
    h0c, h1c = cal.h0f[fam], cal.h1f[fam]
    amin, amax = _a_bounds(k0, k1)
    costs = []
    inter = []
    for a in range(0, acap + 1):
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
    a_free = min(range(acap + 1),
                 key=lambda a: (costs[a], not inter[a], a))
    lo = max(0, amin)
    hi = min(acap, amax)
    if lo > hi:
        lo, hi = 0, acap                          # infeasible constraints
    a_hat = min(range(lo, hi + 1),
                key=lambda a: (costs[a], not inter[a], a))
    return a_hat, costs[a_hat], costs, lo, hi, inter, a_free


def _cand_insert(cand_t, cand_m, k, m):
    """Sorted top-A_MAX insertion, key (margin, bit index) ascending.
    Bits arrive in ascending index order, so inserting after equal-margin
    entries keeps the deterministic SS6.2 tie rule.  RAM: A_MAX x (u16 +
    u8) + 2 counters = 18 B.

    UNCHANGED by Lever B: SS6.4's DW bits go through this same routine.
    Their margin is > MG_MAX by definition and a weak bit's is <= MG_MAX,
    so the single ascending key sorts every weak entry ahead of every DW
    entry -- weak completeness (R7) needs no extra rule and no eviction
    logic, and a full list drops the worst DW entry first."""
    i = len(cand_t)
    while i > 0 and cand_m[i - 1] > m:
        i -= 1
    if i >= A_MAX:
        return
    cand_t.insert(i, k)
    cand_m.insert(i, m)
    if len(cand_t) > A_MAX:
        cand_t.pop()
        cand_m.pop()


def _decide_pass(samples, K, tau, cal):
    """P4: stream segments, decide, emit bits + the v2 margin stream.

    Replaces v1's conf[]/tied[] bitmaps + knife list with (SS6.2):
      cand_t/cand_m  streaming top-A_MAX weakest payload' bits
      n_weak         count of ALL payload' bits with margin <= MG_MAX
      n_tied         count of ALL payload' bits with margin == 0
      chk_conf[CHK_LEN]  per-check-byte margin sums (SS7.8 order only)

    The dead-window tie mark can land one segment ahead (at t == k1, the
    next segment's first bit); a single pending slot replaces the tied[]
    bitmap -- verified bit-identical to the array form.

    SS6.4 (LEVER B) adds the per-bit DEGENERATE-GEOMETRY test, whose
    whole cost is a shift and two s16 compares per bit:
      hb = off << BIT_SH   (off < DW_OFF_MAX, else the bit is healthy)
      ga = (hb + h0c) <= u ,  gb = v < (hb + h1c) ,  DW iff ga == gb
    It is stateless -- no running accumulator, no latch -- because hb is
    a pure function of off."""
    bits = [0] * NB
    infeasible = 0
    label_err = 0
    n_seg = 0
    cand_t = []                       # payload'-relative bit index (u16)
    cand_m = []                       # margin (u8)
    n_weak = 0                        # u16
    n_tied = 0                        # u16
    n_dw = 0                          # u16 -- ALL DW bits (SS6.4)
    chk_conf = [0] * CHK_LEN          # u16 each
    tie_pend = -1                     # tie mark carried into next segment
    nd8 = 8 * N_DATA
    for (k0, k1, u, v, fam) in _seg_stream(samples, K, tau):
        n_seg += 1
        if k0 >= NB:
            continue
        a_hat, c_hat, costs, lo, hi, inter, a_free = _decide(
            k0, k1, u, v, fam, cal)
        if c_hat > INFEAS_U:
            infeasible += 1
        known_all = all(KNOWN[t] >= 0 for t in range(k0, min(k1, NB)))
        dead = sum(1 for x in inter if x) >= 2
        if known_all and lo == hi and a_free != lo and not dead:
            label_err += 1
        # dead-window tie: two interior candidates inside the allowed range
        tie_here = -1
        # The v1 form also required `a_hat in ins[:2]`, which is ALWAYS
        # TRUE and cost 26 B of assembly: an interior boundary has hinge
        # cost 0, and argmin's key is (cost, NOT interior, index)
        # ascending, so a non-empty ins forces a_hat == ins[0].  Proven
        # in dev_lever_b/ins0_proof.py over 1 619 577 decided segments of
        # every corpus and both fuzz sets: 0 counterexamples.  ins[1] is
        # therefore never read and is not computed.
        ins0 = -1
        nins = 0
        for a in range(lo, hi + 1):
            if inter[a]:
                nins += 1
                if ins0 < 0:
                    ins0 = a
        if nins >= 2:
            t = k0 + ins0
            if t < NB:
                tie_here = t
        h0c, h1c = cal.h0f[fam], cal.h1f[fam]
        kk1 = min(k1, NB)
        for t in range(k0, kk1):
            OPS["bit"] += 1
            off = t - k0
            bits[t] = 1 if off < a_hat else 0
            is_dw = False                         # SS6.4
            if off < DW_OFF_MAX:
                hb = off << BIT_SH                # = off * BIT_U, s16-safe
                is_dw = (hb + h0c <= u) == (v < hb + h1c)
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            if c0 is None or c1 is None:
                m = 255
            else:
                m = min(255, abs(c0 - c1))
            if t == tie_here or t == tie_pend:
                m = 0                             # decided by tie-break
            if PP_LO <= t < PP_HI:                # payload' bits only
                k = t - PP_LO
                if k >= nd8:
                    chk_conf[(k - nd8) >> 3] = _u16(
                        chk_conf[(k - nd8) >> 3] + m)
                if m <= MG_MAX:
                    n_weak = _u16(n_weak + 1)
                    if m == 0:
                        n_tied = _u16(n_tied + 1)
                    _cand_insert(cand_t, cand_m, _u16(k), _u8(m))
                elif is_dw and DW_EN:             # SS6.4
                    n_dw = _u16(n_dw + 1)
                    _cand_insert(cand_t, cand_m, _u16(k), _u8(m))
        if tie_pend >= 0 and tie_pend < kk1:
            tie_pend = -1                         # consumed
        if tie_here >= kk1:
            tie_pend = tie_here                   # lands in next segment
    return dict(bits=bits, infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, cand_t=cand_t, cand_m=cand_m,
                n_weak=n_weak, n_tied=n_tied, n_dw=n_dw,
                chk_conf=chk_conf)


# ---------------------------------------------- CRC chase (C1-C5), v2.3
# v2.3: the residual test is 16-bit and the reference may be a SET (a
# split check-byte position enumerates candidates), so the hard bound is
# a cap on RESIDUAL COMPARISONS rather than on flip sets -- see T_MAX.

def _enum_trials(isd, skip3, skip5, npair):
    """Normative five-phase, data-minimal, cheapest-first enumeration
    (SS7.4).  isd[i] = candidate i is a DATA bit.  Candidate indices are
    already ascending in (margin, bit index); within a phase iteration is
    index-ascending (measured byte-identical to the exact summed-margin
    sort).

    Phases 3/5 carry the parity gate (free, exact, and it SURVIVES the
    move to CRC16): 0x11021 = (x+1) * 0xF01F, so every single-bit
    syndrome has odd parity and a weight-w data-only flip has syndrome
    parity w mod 2.  A data-only phase whose parity can match NO admitted
    reference is skipped whole -- the caller passes skip3 / skip5 after
    OR-reducing the parities of every reference in play (with the usual
    single reference that is exactly v2.2's `par` test).

    SS7.10 W2 bound: every WEIGHT-2 phase (2, 4, 5) is restricted to the
    candidate prefix [0, npair) -- see _npair().  Each such phase yields
    (smaller, larger), so the single test `larger < npair` implements it;
    the surviving trials are a SUBSEQUENCE of the unbounded enumeration in
    the same order, so the first passing trial is unchanged whenever it is
    itself admissible."""
    n = len(isd)
    chk = [i for i in range(n) if not isd[i]]
    dat = [i for i in range(n) if isd[i]]
    for i in chk:                                 # phase 1: one check bit
        yield (i,)
    for a in range(len(chk)):                     # phase 2: two check bits
        for b in range(a + 1, len(chk)):
            if chk[b] < npair:
                yield (chk[a], chk[b])
    if not skip3:                                 # phase 3: one data bit
        for i in dat:
            yield (i,)
    for i in range(n):                            # phase 4: data + check
        for j in range(i + 1, n):
            if isd[i] != isd[j] and j < npair:
                yield (i, j)
    if not skip5:                                 # phase 5: two data bits
        for a in range(len(dat)):
            for b in range(a + 1, len(dat)):
                if dat[b] < npair:
                    yield (dat[a], dat[b])


def _npair(cand_m, n):
    """SS7.10: how many leading candidates a weight-2 trial may draw from.

    cand_m is non-decreasing (SS6.2 insertion), so {i : i < A_PAIR and
    cand_m[i] <= MG_PAIR} is a prefix and its length is the bound.  The
    implementations test `j < A_PAIR and cand_m[j] <= MG_PAIR` on the
    larger member instead of materialising npair -- identical by the same
    monotonicity.

    At v2.3 A_PAIR = A_MAX and MG_PAIR = MG_MAX, so npair == n and the
    bound reduces to "pairs come only from ADMITTED weak candidates"; the
    constants stay live (and stay in the implementations) because the
    bound is what re-tightens if a future corpus asks for it, and because
    the compat modes still need the 3/4 values."""
    p = 0
    while p < n and p < A_PAIR and cand_m[p] <= MG_PAIR:
        p += 1
    return p


def _parity16(x):
    x ^= x >> 8
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1


def _chase(st, info):
    """C1..C5 + R5..R8 of SS7.9.  Works entirely on the decoded bit array
    and the <= A_MAX-entry candidate list -- no capture scan.  Returns the
    DATA bytes or None; info records path / cause / trial counts."""
    bits = st["bits"]
    nd8 = 8 * N_DATA
    # ---- C1: assemble payload' bytes ------------------------------------
    P = []
    for p in range(NPP):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[PP_LO + 8 * p + j]
        P.append(_u8(val))
    D = P[:N_DATA]
    info["n_weak"] = st["n_weak"]
    info["n_tied"] = st["n_tied"]
    if not CHASE_EN:
        # legacy v2.0 geometry (dev/bench only): no check block on the
        # wire, nothing to verify -- emit after the R5 emit gate.
        if st["n_tied"] > TIE_EMIT:
            info["cause"] = "refuse_emitgate"
            return None
        info["path"] = "legacy_unverified"
        return bytes(D)
    C = P[N_DATA:]
    info["check"] = tuple(C)
    if WIRE == 23:
        return _chase23(st, info, D, C, nd8)
    return _chase22(st, info, D, C, nd8)


def _chase23(st, info, D, C, nd8):
    """v2.3 chase: CRC16 residual, per-byte-majority reference set, no
    alias guard (provably inert), T_MAX residual comparisons."""
    conf = st["chk_conf"]
    r_base = _crc16(bytes(D))
    hi, lo = _ref_bytes(C)
    have_R = hi is not None and lo is not None
    info["r_base"] = r_base
    info["majority"] = ((hi << 8) | lo) if have_R else None
    info["ref_split"] = (hi is None) + (lo is None)
    # ---- RELAXATION B, the confidence FEED-FORWARD ----------------------
    # The marker mismatch count is evidence about the whole lock.  A
    # marker-suspect frame keeps its per-byte-majority reference but is
    # denied the split enumeration, so it cannot also help itself to 9x
    # the per-comparison exposure.  (violations <= MK_TOL here -- R2
    # already refused anything worse.)
    cap = REF_MAX if (CHASE_SPLIT_VOTE and info["violations"] <= MK_SOFT) \
        else 1
    info["ref_cap"] = cap
    refs = _ref_candidates(C, conf, cap)
    info["n_refs"] = len(refs)
    # ---- R5: emit gate (BOTH paths -- measured, SS7.5) -------------------
    if st["n_tied"] > TIE_EMIT:
        info["cause"] = "refuse_emitgate"
        return None
    comps = [0]

    def match(r, rset):
        """Residual test against a reference set; each comparison is one
        2^-16 exposure and one unit of the T_MAX budget.  Returns
        True (accept), False (no match), or None (budget exhausted)."""
        for R in rset:
            if comps[0] >= T_MAX:
                return None
            comps[0] += 1
            if r == R:
                return True
        return False

    # ---- C2: direct accept ----------------------------------------------
    # v2.3 admits a SPLIT check block here too (the emit-always
    # directive): with a per-byte majority at both positions refs is the
    # single v2.2-equivalent reference, and the test is identical.
    m = match(r_base, refs)
    if m:
        info["path"] = "direct"
        info["comps"] = comps[0]
        return bytes(D)
    # ---- C3: admission gates --------------------------------------------
    # R6 now also asks the SS6.4 pool: a frame whose errors carry a LARGE
    # apparent margin has n_weak == 0, and the DW bits are the only thing
    # that gives the chase anything to try.  R7 is UNCHANGED -- it is the
    # WEAK pool's completeness rule, and a DW entry can never sort ahead
    # of a weak one (margin > MG_MAX vs <= MG_MAX), so the guarantee it
    # rests on is untouched.
    n_dw = st.get("n_dw", 0)
    cand_t = st["cand_t"]
    n = len(cand_t)
    # R6 is now literally "nothing to chase": the list is empty.  That is
    # EQUIVALENT to n_weak == 0 and n_dw == 0 -- _cand_insert returns
    # early only when the insertion index reaches A_MAX, which cannot
    # happen while the list is empty, so the FIRST admitted bit of either
    # class always lands -- and it is one byte cheaper on the target.
    if n == 0:
        info["cause"] = "refuse_nocand"
        info["comps"] = comps[0]
        return None
    assert (st["n_weak"] == 0 and n_dw == 0) == (n == 0)
    if st["n_weak"] > A_MAX:
        info["cause"] = "refuse_admit"
        info["comps"] = comps[0]
        return None
    # candidate list now provably holds ALL weak bits (n_weak <= A_MAX)
    assert n == min(st["n_weak"] + n_dw, A_MAX)
    assert st["n_weak"] == sum(1 for x in st["cand_m"] if x <= MG_MAX)
    isd = [cand_t[i] < nd8 for i in range(n)]
    # parity gate: skip a data-only phase whose weight parity can match
    # NO admitted reference (exact -- see _enum_trials)
    pars = [_parity16(r_base ^ R) for R in refs]
    skip3 = all(q == 0 for q in pars)             # w = 1 needs odd
    skip5 = all(q == 1 for q in pars)             # w = 2 needs even
    info["chased"] = True
    # ---- C4: bounded, data-minimal, cheapest-first trial loop ------------
    # SS7.10 W2 bound.  At v2.3 A_PAIR = A_MAX and MG_PAIR = MG_MAX, so
    # the bound already reads "pairs come only from ADMITTED candidates"
    # -- and SS6.4's DW bits ARE admitted candidates (their margin is
    # exactly what the geometry says nothing about).  npair = n is
    # therefore the v2.3 form, bit-identical to _npair() whenever no DW
    # bit is admitted, and it is what decode.c compiles (the A_PAIR /
    # MG_PAIR test is #if'd out at these constants) and what
    # decode_asm.s assembles (no test at all).  _npair stays live for
    # the v2.2 compat chase below, where A_PAIR = 3 and MG_PAIR = 4.
    npair = n
    info["npair"] = npair
    trials = 0
    for S in _enum_trials(isd, skip3, skip5, npair):
        trials += 1
        OPS["trial"] += 1
        Cp = list(C)
        r = r_base
        touched_chk = False
        for i in S:
            k = cand_t[i]
            if k < nd8:
                r = _u16(r ^ _syn16(k))           # data bit: XOR syndrome
            else:
                q = (k - nd8) >> 3                # check bit: move the ref
                Cp[q] = _u8(Cp[q] ^ (1 << (7 - (k & 7))))
                touched_chk = True
        rset = _ref_candidates(Cp, conf, cap) if touched_chk else refs
        m = match(r, rset)
        if m is None:                             # T_MAX budget exhausted
            info["trials"] = trials
            info["comps"] = comps[0]
            info["budget_hit"] = True
            info["cause"] = "refuse_chase"        # R8
            return None
        if not m:
            continue
        # accept: apply the DATA flips, emit.  No alias guard: at 16 bits
        # every data-bit syndrome in a <= 432-bit payload' is DISTINCT
        # (ord(x) = 32767), so the v2.2 SS7.7 ambiguity cannot exist.
        D2 = bytearray(D)
        for i in S:
            k = cand_t[i]
            if k < nd8:
                D2[k >> 3] ^= 1 << (7 - (k & 7))
        info["path"] = "chase"
        info["trials"] = trials
        info["comps"] = comps[0]
        info["flips"] = tuple(cand_t[i] for i in S)
        return bytes(D2)
    info["trials"] = trials
    info["comps"] = comps[0]
    info["cause"] = "refuse_chase"                # R8: the honest end
    return None


def _chase22(st, info, D, C, nd8):
    """SUPERSEDED v2.2 / v2.1 chase, kept verbatim so captures_v2{1,2}*.json
    reproduce bit-for-bit: CRC8 residual, block-level unique->=2-vote
    majority, the SS7.7 alias guard (which those geometries DO need --
    ord(x) mod 0x107 = 127 < 128 data bits), A_MAX = 5, T <= 16 flip
    sets.  Reached only via _configure(nd, chk=4) / chk=3."""
    r_base = _crc8(bytes(D))
    R = _majn(C)
    have_R = R is not None
    info["r_base"] = r_base
    info["majority"] = R
    # ---- R5: emit gate (BOTH paths -- measured, SS7.5) -------------------
    if st["n_tied"] > TIE_EMIT:
        info["cause"] = "refuse_emitgate"
        return None
    # ---- C2: direct accept ----------------------------------------------
    if have_R and r_base == R:
        info["path"] = "direct"
        return bytes(D)
    # ---- C3: admission gates --------------------------------------------
    if st["n_weak"] == 0:
        info["cause"] = "refuse_nocand"
        return None
    if st["n_weak"] > A_MAX:
        info["cause"] = "refuse_admit"
        return None
    cand_t = st["cand_t"]
    n = len(cand_t)
    assert n == st["n_weak"] <= A_MAX
    isd = [cand_t[i] < nd8 for i in range(n)]
    par = _parity8(r_base ^ R) if have_R else -1
    info["chased"] = True
    npair = _npair(st["cand_m"], n)               # SS7.10 W2 bound
    info["npair"] = npair
    trials = 0
    acmp = 0
    skip3 = bool(have_R and par == 0)
    skip5 = bool(have_R and par == 1)
    for S in _enum_trials(isd, skip3, skip5, npair):
        trials += 1
        OPS["trial"] += 1
        Cp = list(C)
        r = r_base
        for i in S:
            k = cand_t[i]
            if k < nd8:
                r = _u8(r ^ _syn8(k))             # data bit: XOR syndrome
            else:
                q = (k - nd8) >> 3                # check bit: move the ref
                Cp[q] = _u8(Cp[q] ^ (1 << (7 - (k & 7))))
        Rp = _majn(Cp)
        if Rp is None:
            continue                              # slot consumed, no ref
        if r != Rp:
            continue
        # ---- C5: alias guard (SS7.7) ------------------------------------
        amb = False
        for i in S:
            ki = cand_t[i]
            if ki >= nd8:
                continue
            si = _syn8(ki)
            for j in range(n):
                if j in S:
                    continue
                if cand_t[j] < nd8:
                    acmp += 1
                    OPS["acmp"] += 1
                    if _syn8(cand_t[j]) == si:
                        amb = True
        if amb:
            continue
        D2 = bytearray(D)
        for i in S:
            k = cand_t[i]
            if k < nd8:
                D2[k >> 3] ^= 1 << (7 - (k & 7))
        info["path"] = "chase"
        info["trials"] = trials
        info["alias_cmp"] = acmp
        info["flips"] = tuple(cand_t[i] for i in S)
        return bytes(D2)
    info["trials"] = trials
    info["alias_cmp"] = acmp
    info["cause"] = "refuse_chase"                # R8: the honest end
    return None


# ------------------------------------------------------------------ decode

def decode_state(samples):
    """P1..P4 only (no gates, no chase) -- dev tooling for lock/containment
    analysis.  Returns the raw state dict + (K, tau), or None when the
    endpoint seed fails."""
    seed = _seed(samples)
    if seed is None:
        return None
    K, tau, np_ = seed
    for _ in range(2):                            # P2 x2
        K, tau = _refine(samples, K, tau)
    cal = _calibrate(samples, K, tau)             # P3
    st = _decide_pass(samples, K, tau, cal)       # P4
    st["K"] = K
    st["tau"] = tau
    st["n_pulse"] = np_
    return st


def decode_ex(samples):
    """Full v2 decode.  Returns (data_bytes | None, info) where info gives
    the SS9.1 path / refusal cause and the chase accounting the phase-3
    parity harness (B1) and the evaluation wrappers consume."""
    info = {"path": None, "cause": None, "trials": 0, "alias_cmp": 0,
            "chased": False, "flips": (), "comps": 0, "n_refs": 0,
            "ref_split": 0, "ref_cap": 0, "budget_hit": False}
    if not samples:
        info["cause"] = "refuse_lock"             # R1
        return None, info
    st = decode_state(samples)
    if st is None:
        info["cause"] = "refuse_lock"             # R1
        return None, info
    info["K"] = st["K"]
    info["tau"] = st["tau"]
    bits = st["bits"]
    violations = sum(1 for t in range(NB)
                     if KNOWN[t] >= 0 and bits[t] != KNOWN[t])
    info["violations"] = violations
    info["infeasible"] = st["infeasible"]
    # SS6.4: reported from the decision pass, exactly where decode.c and
    # decode_asm.s maintain it -- so it is comparable on every path that
    # ran a decision pass (R2..R8 and both emit paths).  After an R1 lock
    # failure no pass ran and the counter is meaningless in all three
    # implementations (like n_weak / n_cand, it is reset by the pass).
    info["n_dw"] = st.get("n_dw", 0)
    info["label_err"] = st["label_err"]
    # ---- R2, RELAXATION B: a THRESHOLD over the known marker bits ------
    # v2.2 refused on any single mismatch.  v2.3 accepts up to MK_TOL of
    # the N_MK (48) known bits and feeds the count forward as confidence
    # (it caps the chase's reference enumeration -- see _chase23).  There
    # is NO special case requiring the first or last frame byte to
    # validate: owner directive, and the threshold is the whole rule.
    if violations > MK_TOL:
        info["cause"] = "refuse_marker"           # R2
        return None, info
    if st["infeasible"] > GATE_INFEAS:
        info["cause"] = "refuse_infeasible"       # R3
        return None, info
    if st["label_err"] > GATE_LABERR:
        info["cause"] = "refuse_labelerr"         # R4
        return None, info
    data = _chase(st, info)                       # R5..R8 inside
    if data is not None:
        info["cause"] = None
    return data, info


def decode(samples, meta):
    """ND DATA bytes (check block stripped) or None.  Deterministic."""
    data, _ = decode_ex(samples)
    return data


# ------------------------------------------------------------- self-test
# B7/B8-style vectors (SS13.3): CRC check value, the SS2.4 frame vectors,
# XPOW vs direct CRC of every unit error vector, GF(2) linearity.

def _selftest():
    # ---------------------------------------------------------- v2.3 core
    assert _crc16(b"123456789") == 0x29B1          # the standard check value
    d16 = bytes(range(16))
    c16 = _crc16(d16)
    hi, lo = c16 >> 8, c16 & 0xFF
    pp = d16 + bytes([hi, lo] * 3)
    fr = HDR_V23 + pp + TRL_V23
    assert len(fr) == 28 and len(fr) * 8 == 224 == NB
    assert fr[:3] == b"\xff\xaa\x65" and fr[-3:] == b"\x9a\x00\xff"
    # TRAILER[1] is the ZEROS calibration probe (owner 2026-09-07),
    # so the frame ends with 8 known zero bits before the latch.
    assert TRL_V23[1] == 0x00 and _bits_of(TRL_V23)[8:16] == [0] * 8
    # production vector: 60 bytes = exactly 20 WS2812 LEDs, and NB is
    # UNCHANGED from v2.2 at both geometries
    d48 = bytes((i * 5) & 0xFF for i in range(48))
    c48 = _crc16(d48)
    assert len(HDR_V23 + d48 + bytes([c48 >> 8, c48 & 0xFF] * 3)
               + TRL_V23) == 60 == 20 * 3
    _configure(48)
    assert NB == 480 and NPP == 54 and PP_LO == 24 and N_MK == 48
    _configure(16, chk=4)
    assert NB == 224 and NPP == 20 and PP_LO == 32 and N_MK == 64
    _configure(48, chk=4)
    assert NB == 480 and NPP == 52
    _configure(16)
    assert NB == 224 and NPP == 22 and CHK_LEN == 6

    # ---- the two structural facts the v2.3 chase is BUILT on -----------
    # (1) ord(x) mod 0x11021 = 32767, so every data-bit syndrome in a
    #     384-bit (production) or 128-bit (test) DATA field is DISTINCT.
    #     THIS is why the SS7.7 alias guard is not computed in v2.3.
    r, order = 1, 0
    while True:
        r = ((r << 1) ^ CRC16_POLY) & 0xFFFF if r & 0x8000 \
            else (r << 1) & 0xFFFF
        order += 1
        if r == 1:
            break
    assert order == 32767, order
    keep = N_DATA
    for nd in (16, 48):
        _configure(nd)
        syn = [_syn16(k) for k in range(8 * nd)]
        assert len(set(syn)) == 8 * nd, ("ALIASING at nd=%d" % nd)
        # (2) 0x11021 = (x+1) * 0xF01F, so every single-bit syndrome has
        #     ODD parity -> a weight-w data-only flip has syndrome parity
        #     w mod 2, and the SS7.4 phase 3/5 gate stays EXACT.
        assert all(_parity16(v) == 1 for v in syn)
        for a in range(0, 8 * nd, 37):
            for b in range(a + 1, 8 * nd, 53):
                assert _parity16(syn[a] ^ syn[b]) == 0
        # XS/_syn16 against a direct CRC16 of every unit error vector
        for k in range(8 * nd):
            e = bytearray(nd)
            e[k >> 3] ^= 1 << (7 - (k & 7))
            assert _crc16(bytes(e)) == (_crc16(bytes(nd)) ^ _syn16(k)), (nd, k)
    # the (x+1) factorisation itself, by division
    num, den, q = 0x11021, 0b11, 0
    while num.bit_length() > 1 and num:
        sh = num.bit_length() - 2
        q ^= 1 << sh
        num ^= den << sh
    assert num == 0 and q == 0xF01F, (hex(q), num)
    # GF(2) affinity of CRC16 at init 0xFFFF: crc(D^e) = crc(D) ^ crc0(e)
    x = 0x2468
    for nd in (16, 48):
        _configure(nd)
        base = bytes(((i * 37) ^ 0x5A) & 0xFF for i in range(nd))
        rb = _crc16(base)
        z = _crc16(bytes(nd))
        for _ in range(200):
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
            k1 = (x >> 8) % (8 * nd)
            k2 = (x >> 19) % (8 * nd)
            e = bytearray(nd)
            e[k1 >> 3] ^= 1 << (7 - (k1 & 7))
            e[k2 >> 3] ^= 1 << (7 - (k2 & 7))
            m = bytes(a ^ b for a, b in zip(base, e))
            assert _crc16(m) == rb ^ (_crc16(bytes(e)) ^ z)
    _configure(keep)

    # ---- per-byte majority: the headline v2.3 property ------------------
    assert _maj3(1, 1, 1) == 1 and _maj3(1, 1, 2) == 1
    assert _maj3(1, 2, 1) == 1 and _maj3(2, 1, 1) == 1
    assert _maj3(1, 2, 3) is None
    from itertools import product
    for cs in product(range(4), repeat=3):
        twos = sorted({v for v in cs if cs.count(v) >= 2})
        assert _maj3(*cs) == (twos[0] if twos else None), cs
    # TWO copies damaged in DIFFERENT byte positions -- no block-level
    # majority exists at all, yet the per-byte reference is exact.
    for (ia, ib) in ((0, 1), (0, 2), (1, 2), (1, 0), (2, 0), (2, 1)):
        C = bytearray([hi, lo] * 3)
        C[2 * ia] ^= 0x5A                          # copy ia's HI
        C[2 * ib + 1] ^= 0xA5                      # copy ib's LO
        blocks = {(C[2 * q] << 8) | C[2 * q + 1] for q in range(3)}
        assert len(blocks) == 3                    # block vote has nothing
        assert _ref_bytes(C) == (hi, lo), (ia, ib)
        assert _ref_candidates(C, [0] * 6, REF_MAX) == [(hi << 8) | lo]
    # a split position -> exactly 3 references, truth among them, ranked
    C = bytearray([hi, lo] * 3)
    C[0] ^= 0x11
    C[2] ^= 0x22
    assert _ref_bytes(C)[0] is None and _ref_bytes(C)[1] == lo
    refs = _ref_candidates(C, [0, 0, 0, 0, 9, 0], REF_MAX)
    assert len(refs) == 3 and (hi << 8) | lo in refs
    assert refs[0] == ((hi << 8) | lo)             # the intact copy ranks 1st
    # both positions split -> the full 3x3 cross product, all distinct
    C = bytearray([hi, lo] * 3)
    C[0] ^= 0x11; C[2] ^= 0x22; C[1] ^= 0x33; C[3] ^= 0x44
    assert _ref_bytes(C) == (None, None)
    refs = _ref_candidates(C, [0] * 6, REF_MAX)
    assert len(refs) == 9 == len(set(refs)) and (hi << 8) | lo in refs
    assert len(_ref_candidates(C, [0] * 6, 1)) == 1   # marker-suspect cap

    # ---- budget arithmetic, stated not assumed --------------------------
    # unbounded weight-<=2 flip sets at v2.3
    assert 1 + A_MAX_V23 + A_PAIR_V23 * (A_PAIR_V23 - 1) // 2 == 67
    assert 1 + A_MAX_V22 + A_PAIR_V22 * (A_PAIR_V22 - 1) // 2 == 9
    # T_MAX is exactly the 0.2 %-target budget at one reference
    fa = lambda t, R: 1.0 - (1.0 - R / 65536.0) ** t     # noqa: E731
    assert fa(T_MAX_V23, 1) <= 0.002 < fa(T_MAX_V23 + 1, 1)
    assert abs(fa(67, 1) - 0.0010217) < 1e-6            # the 67-set figure
    assert fa(T_MAX_V23, REF_MAX) > 0.002               # why comps, not sets
    # ... and the 256x-per-trial claim against the superseded 8-bit check
    assert abs(fa(1, 1) * 256 - (1.0 - (1.0 - 1 / 256.0))) < 1e-12
    # _npair is a prefix length under BOTH parameter sets
    for (ap, mp, cms) in ((A_PAIR_V22, MG_PAIR_V22,
                           ((0, 0, 0, 0, 0), (0, 1, 4, 5, 8), (5, 6, 7, 8, 8),
                            (0, 4, 4, 4, 4), (2, 2, 5, 6, 7))),
                          (A_PAIR_V23, MG_PAIR_V23,
                           ((0,) * 11, tuple(range(11)),
                            (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 8)))):
        gap, gmp = A_PAIR, MG_PAIR
        globals()["A_PAIR"], globals()["MG_PAIR"] = ap, mp
        for cm in cms:
            npc = _npair(list(cm), len(cm))
            for a in range(len(cm)):
                for b in range(a + 1, len(cm)):
                    both = (b < ap and max(cm[a], cm[b]) <= mp)
                    assert both == (b < npc), (ap, mp, cm, a, b)
        globals()["A_PAIR"], globals()["MG_PAIR"] = gap, gmp

    # ---- superseded CRC8 paths still work (compat regression) ----------
    assert _crc8(b"123456789") == 0xF4
    assert _crc8(bytes(range(16))) == 0x41
    _configure(16, chk=4)
    assert _majn([1, 1, 1, 1]) == 1 and _majn([1, 1, 2, 2]) is None
    assert _majn([1, 2, 3, 4]) is None and _majn([2, 3, 1, 1]) == 1
    _configure(16, chk=3)
    assert NB == 216 and _majn([1, 2, 1]) == 1 and _majn([1, 2, 3]) is None
    for nvals in (3, 4):
        for cs in product(range(4), repeat=nvals):
            twos = sorted({v for v in cs if cs.count(v) >= 2})
            want = twos[0] if len(twos) == 1 else None
            assert _majn(list(cs)) == want, cs
    for nd in (16, 48):
        _configure(nd, chk=4)
        for k in range(8 * nd):
            e = bytearray(nd)
            e[k >> 3] ^= 1 << (7 - (k & 7))
            assert _crc8(e) == _syn8(k), (nd, k)
    assert XPOW[8] == 0x07 and XPOW[14] == 0xC7 and XPOW[15] == 0x89
    _configure(16)

    print("embedded_v2 v2.3 self-test OK  (CRC16 0x29B1; frame 28/60 B, NB "
          "224/480 unchanged; ord(x) = 32767 -> all 128+384 data-bit "
          "syndromes DISTINCT, alias guard provably inert; 0x11021 = "
          "(x+1)*0xF01F -> parity gate exact; per-byte majority survives "
          "two differently-damaged copies (all 6 rotations); T_MAX = 131 "
          "= fa_budget(0.2 %%, 1 ref), 67 flip sets = %.4f %%; v2.2/v2.1 "
          "CRC8 compat paths regression-clean)"
          % (100 * (1 - (1 - 1 / 65536.0) ** 67)))


if __name__ == "__main__":
    _selftest()
