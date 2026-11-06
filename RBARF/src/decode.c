/*
 * decode.c -- v2.3 PERMISSIVE embedded WS2812 decoder for the STM8S001J3.
 *
 * WIRE v2.3 (owner decision 2026-09-07, supersedes v2.2):
 *   frame  = FF AA 65 || DATA(ND) || (C16_HI C16_LO) x3 || 9A 00 FF
 *            TRAILER[1] = 00, a worst-case-ZEROS calibration probe at
 *            a KNOWN position, in place of the end-of-frame bit-period
 *            ruler (owner decision 2026-09-07: +26.7 pts of delivery on
 *            silicon, 71.1 % -> 97.8 %, paired McNemar 25:1, p<0.001;
 *            the ruler measured no benefit even under drift).
 *   CRC16  = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflect,
 *            xorout 0) over the DATA bytes only; crc16("123456789")
 *            = 0x29B1.  There is NO CRC8 in v2.3.
 *   REF    = INDEPENDENT PER-BYTE majority: ref_HI = maj(C0,C2,C4),
 *            ref_LO = maj(C1,C3,C5).  Three votes admit no tie, so a
 *            position either has a unique >= 2-vote majority or all three
 *            differ; a split position enumerates its three values and the
 *            references are the confidence-ranked cross product
 *            (<= REF_MAX = 9), tried in diagonal order.
 *   The production frame is 3+48+6+3 = 60 bytes = exactly 20 WS2812 LEDs,
 *   and NB is UNCHANGED from v2.2 at both geometries (two marker bytes
 *   traded for two check bytes), so the capture buffer sizing and the pad
 *   law are untouched.
 *   -DCHK_LEN=4 / 3 rebuild the SUPERSEDED v2.2 / v2.1 CRC8 geometries
 *   (4-byte markers, block vote, alias guard, the old gates) for parity
 *   runs against the captures_v2{1,2}*.json corpora.
 *
 * THE OWNER DIRECTIVE: ALMOST ALWAYS EMIT.  A refusal loses the frame
 * (single transmission, rare frames), so refusals are what v2.3
 * minimises; it emits on an imperfect reconstruction PROVIDED the 16-bit
 * check validates the payload.  The 16-bit check is what makes that safe:
 * 2^-16 per residual comparison, so crc.fa_budget(0.2 %, 1 ref) = 131
 * wrong trials are affordable where the 8-bit check afforded none.
 *
 * THE THREE RELAXATIONS (all v2.3-only; the compat modes keep the v2.2
 * gates bit-for-bit so the acquired corpora reproduce exactly):
 *   A  K window 46000..60000 -> 40000..64000, GATE_INFEAS 4 -> 24, and a
 *      NEW explicit s16 range check on tau in seed() (the wide window
 *      makes a short-span capture reachable, and an out-of-range tau
 *      would wrap here while the Python reference asserts -- refusing R1
 *      keeps all three implementations bit-exact by construction).
 *   B  R2 marker validation becomes a THRESHOLD over the 48 known marker
 *      bits: refuse only at violations > MK_TOL (12), and feed the count
 *      forward as confidence (above MK_SOFT it caps the chase's reference
 *      enumeration at 1).  Per owner directive there is NO special case
 *      requiring the first or last frame byte to validate.
 *   C  A_MAX 5 -> 11 with weight <= 2 (1 + 11 + C(11,2) = 67 flip sets),
 *      A_PAIR 3 -> 11, MG_PAIR 4 -> 8, and the hard bound restated as
 *      T_MAX = 131 RESIDUAL COMPARISONS (each 2^-16), so a split
 *      reference pays budget instead of multiplying risk.  R5 (n_tied)
 *      is retired -- measured +798 emissions, 0 wrong, all direct.
 *
 * The SS7.7 ALIAS GUARD IS GONE, with proof: ord(x) mod 0x11021 = 32767,
 * so the 384 production (128 test) data-bit syndromes are all DISTINCT
 * and the v2.2 ambiguity cannot exist.  dec_info.alias_cmp is 0 by
 * construction.  The SS7.4 PARITY GATE stays and stays exact:
 * 0x11021 = (x+1)*0xF01F, so every single-bit syndrome has odd parity.
 *
 * C99/SDCC port of recon/approaches/embedded_v2.py (the validated
 * reference), which is EMBEDDED_V2_SPEC.md on top of the v1 integer
 * pipeline.  Fixed-point idioms reused from the proven v1 port.
 *
 * Input: RAW capture bytes in cap_code.s layout (bit7/6 = BS0/BS1 of the
 * PREVIOUS loop, bits5..0 = R0..R5 of THIS loop); linearization happens
 * inline while streaming.  5 forward-only scans, no pulse array stored.
 *
 * Fixed-point contract (spec SS4, verbatim from the reference; TU =
 * 1250/512 ns = 2.44 ns):
 *   t (receiver time)    u16  CPU cycles
 *   K (clock scale)      u16  Q11 TU/cycle (nominal 52429)
 *   t*K                  u32  <= 27.5k * 64000 < 2^31        ** 32-bit **
 *   y (mapped wire time) s32 computed, clamped >= 0 (matches the Python
 *                        reference literally); frame end ~111k TU test
 *   tau                  s16  TU (range-checked in seed(), see A)
 *   u, v, h*, theta      s16  TU (pulse-relative)
 *   Se / Sy sums         s32/u32                             ** 32-bit **
 *   mgv per-bit margin   u8   TU, saturating at 255; 0 = tie-decided
 *   r / r_base / R       u16  CRC16 residual / chase reference
 *   chk_conf[CHK_LEN]    u16  sum of the 8 bit margins of a check byte
 *                             (reference ranking; a LIVE path in v2.3)
 *
 * The Python reference runs a live assert battery on every one of these
 * ranges; this port relies on that proof plus the phase-3 parity harness
 * (recon/approaches/dev_fw/, dev_prod/parity_v23.py) for bit-exactness.
 *
 * All decoder state is static so the linker map MEASURES the RAM
 * working set.  Scanner selection: USE_ASM_SCAN=1 links scan.s (the
 * hand-assembly hot path); 0 compiles the C scanner (host parity
 * builds, and the codegen baseline the speedup is measured against).
 */

#include "decode.h"

/* USE_ASM_DEC=1 replaces the hand-picked hot functions below with
 * decode_asm.s (size-focused hand assembly; target builds).  0 keeps the
 * portable C versions -- the host-parity build, and the codegen baseline
 * the savings are measured against.  Bit-exactness of the asm side is
 * proven by the ucsim harness against the Python reference. */
#ifndef USE_ASM_DEC
#define USE_ASM_DEC 0
#endif

#if CHECK_EN
#ifndef CHK_LEN
#define CHK_LEN 6        /* v2.3 default; 4 = v2.2, 3 = v2.1 (compat)   */
#endif
#if CHK_LEN != 3 && CHK_LEN != 4 && CHK_LEN != 6
#error "CHK_LEN must be 6 (v2.3), 4 (v2.2 compat) or 3 (v2.1 compat)"
#endif
#else
#undef CHK_LEN
#define CHK_LEN 0
#endif

/* WIRE23: the v2.3 wire (3+3 markers, CRC16 x3, per-byte majority, the
 * three relaxations).  0 selects a superseded CRC8 compat geometry. */
#if CHECK_EN && CHK_LEN == 6
#define WIRE23 1
#define HT_LEN 3                          /* marker bytes per end        */
#else
#define WIRE23 0
#define HT_LEN 4
#endif

#define NPP  (ND_DATA + CHK_LEN)          /* payload' bytes on the wire  */
#define NB   (8 * (2 * HT_LEN + NPP))     /* frame bits                  */
#define NBB  ((NB + 7) / 8)
#define PP_LO (8 * HT_LEN)                /* payload' bit window         */
#define PP_HI (PP_LO + 8 * NPP)
#define N_MK (16 * HT_LEN)                /* known marker bits (48 / 64) */
#define ND8  (8 * ND_DATA)                /* payload'-relative data bits */

/* ---- fitted sampler model (integer cycles) -- v1, unchanged ---------- */
#define LOOP_CY   40
#define BIT_SH    9
#define BIT_U     512
#define BIT_H     256
#define BIAS_U    512
#define TAIL_U    164
#define H0P       154
#define H1P       308
#define KQ        11
#define K_NOM     52429u
#if WIRE23
/* RELAXATION A: eps = (K_NOM - K)/K, so a LOW K is a FAST wire.
 * 40000..64000 = eps +31.07 % .. -18.08 %, i.e. 3x the distance from
 * K_NOM of the widest K that was ever RECOVERABLE in the sweeps
 * (48546..56682), capped u16-safe: 27.5k * 64000 < 2^31.  Measured
 * yield over the old 46000..60000 window: ZERO deliveries -- see the
 * report; it is kept because it costs nothing and the 16-bit check is
 * the safety net, not because it was shown to recover a frame. */
#define K_MIN     40000u
#define K_MAX     64000u
#else
#define K_MIN     46000u                  /* v2.2 historical +-12 %      */
#define K_MAX     60000u
#endif
#define FIRST_BR  4
#define LATCH_RUN 200

/* decision / calibration constants (TU) -- v1, unchanged */
#define INFEAS_U  160
#define LAB_MIN   3
#define LAB_OUT   246
#define H0_LO 112
#define H0_HI 192
#define H1_LO 252
#define H1_HI 376
#define SEP_LO 112
#define SEP_HI 196
#if WIRE23
#define GATE_INFEAS 24                    /* RELAXATION A (was 4)        */
#define MK_TOL      12                    /* RELAXATION B: R2 threshold  */
#define MK_SOFT     4                     /*   above this: refs capped 1 */
#else
#define GATE_INFEAS 4
#define MK_TOL      0                     /* v2.2 all-or-nothing rule    */
#define MK_SOFT     0
#endif
#define GATE_LABERR 6                     /* unchanged in v2.3           */
#define A_CAP 15            /* hypothesis cap; measured max span 2 (v1) */

/* eps analog constants -- v1, unchanged */
#define EPS_ZONE 32
#define EPS_HIST 64
#define EPS_GAP_MIN 5
#define EPS_CLAMP56 24
#define EPS_CLEAR1 18
#define EPS_TOPM 3
#define EPS_SLACK 2
#define EPS_SLACK1 8

/* v2 chase constants (every value justified in EMBEDDED_V2_SPEC.md SS7) */
#define MG_MAX    8         /* a bit is "weak" at margin <= 8 TU        */
/* The test is skipped at off >= DW_OFF_MAX, which keeps it inside s16 on
 * an arbitrarily long merged run: off*BIT_U <= 63*512 = 32256 and h1f is
 * clamped to <= H1_HI + FAM_CLAMP + EPS_CLAMP56 = 424, so hb + h1e <=
 * 32680 < 32768.  It costs NOTHING in behaviour: h0f >= H0_LO -
 * FAM_CLAMP - EPS_CLAMP56 = 64 > 0, so once hb > v the test already
 * returns "healthy" on its own (hb + h0e > v >= u makes ga false and
 * hb + h1e > v makes gb true). */
#define DW_OFF_MAX 64
#if WIRE23
/* RELAXATION C, sized against the 16-bit false-accept table:
 *   flip sets   = 1 + A_MAX + C(A_PAIR,2) = 1 + 11 + 55 = 67
 *   fa_prob(67, 1 ref)                    = 0.1022 %   (CRC8: 23.1 %)
 *   T_MAX residual comparisons            = 131 = fa_budget(0.2 %, 1)
 *   fa_prob(131,1) = 0.1997 % <= 0.2 % < fa_prob(132,1) = 0.2012 %
 * T_MAX counts COMPARISONS, not flip sets, so a trial whose check block
 * has no per-byte majority pays for each extra reference it tries.
 * A_PAIR/MG_PAIR at their MG_MAX/A_MAX ceilings means "pairs come only
 * from ADMITTED weak candidates" -- still a hard bound, and the
 * constants stay so it can be re-tightened without a redesign. */
/* BUILD-TIME chase budget (recon/AMAX_TMAX_SWEEP.md).  The Makefile
 * variables A_MAX / T_MAX are the SINGLE source: they arrive here as
 * -DA_MAX_CFG / -DT_MAX_CFG and reach decode_asm.s as the generated
 * build/.../chase_cfg.inc (gen_chase_cfg.py; sdasstm8 has no -D).  The
 * DEFAULTS BELOW ARE THE SHIPPED LEDGER VALUES -- an unset variable
 * rebuilds the ledger images byte-identically. */
#ifndef A_MAX_CFG
#define A_MAX_CFG 11
#endif
#ifndef T_MAX_CFG
#define T_MAX_CFG 131
#endif
/* Worst-case chase trials are the five-phase enumeration's flip-set count
 * n + C(n,2) = A_MAX*(A_MAX+1)/2, and dec_info.trials is a u8. */
#if (A_MAX_CFG) * ((A_MAX_CFG) + 1) / 2 > 255
#error "A_MAX too large: worst-case trials overflow the u8 dec_info.trials"
#endif
/* ch_comps is a u8 here, a u8 (z_comps) in decode_asm.s and a u8 report
 * field in dec_info.  T_MAX > 255 needs a 16-bit counter in the assembly
 * -- a separate change, deliberately NOT made (the sweep found no
 * delivery beyond T_MAX = 192 at any admissible A_MAX). */
#if (T_MAX_CFG) > 255 || (T_MAX_CFG) < 1
#error "T_MAX outside 1..255: ch_comps/dec_info.comps are u8"
#endif
#define A_MAX     A_MAX_CFG
/* A_PAIR TRACKS A_MAX by construction.  v2.3's _chase23 sets npair = n
 * and never reads A_PAIR (the SS7.10 test is #if'd out below exactly
 * because A_PAIR == A_MAX and MG_PAIR == MG_MAX); pinning it to A_MAX is
 * what keeps that true at every parameter point, so raising A_MAX really
 * does widen the weight-2 phases as 1 + n + C(n,2) says. */
#define A_PAIR    A_MAX_CFG
#define MG_PAIR   8
#ifdef T_MAX_OVR
#define T_MAX     T_MAX_OVR /* dev hook: the ucsim decode-TIME A/B runs
                             * the same capture at T_MAX 131 vs 1 to
                             * isolate the chase's cycle cost.  Never
                             * defined in a shipped build. */
#else
#define T_MAX     T_MAX_CFG
#endif
#define REF_MAX   9         /* 3 HI candidates x 3 LO candidates        */
/* R5 RETIRED in v2.3: a frame whose 16-bit check VALIDATES must emit
 * (owner directive).  Measured: retiring it adds 798 emissions over
 * 63924 decodes, 0 wrong, every one of them a DIRECT accept.  The
 * constant, the test and the n_tied counter all stay -- restoring the
 * gate is a one-constant change and nothing about it is silent.  The
 * retired value is STRUCTURALLY unreachable and says so: the gate would
 * fire only if MORE payload' bits were tie-decided than the payload' HAS
 * (n_tied counts a subset of the 8*NPP payload' bits). */
#define TIE_EMIT  (8 * NPP + 1)
/* LEVER B (SS6.4): DEAD-WINDOW candidates.
 * A payload' bit's DISCRIMINATING INTERVAL is the only wire-time window
 * in which a sample can tell 0 from 1: (base + h0e, base + h1e] after
 * its own rising edge.  The whole observation is the fall bracket (u, v]
 * -- u the last HIGH sample, v the first LOW sample, ADJACENT in the
 * sample comb, so no sample lies strictly between them.  With
 *   ga = (off*BIT_U + h0e) <= u        gb = v < (off*BIT_U + h1e)
 * the HEALTHY case is ga != gb: exactly one candidate fall position sits
 * inside the bracket, i.e. a sample DECIDED the bit.  ga == gb is
 * degenerate and covers both ways that happens -- the bracket inside the
 * window (a transition seen at NEITHER fitted boundary, so the polarity
 * rests on the width fit) or the window inside the bracket (no sample
 * inside it at all).  Measured over 1530 frames: 6.97 % of such bits
 * with margin > MG_MAX are wrong, against 0.09 % for the healthy
 * classes -- which is exactly the R6 "refuse_nocand" mechanism.
 * Such a bit joins the candidate list through the SAME SS6.2 sorted
 * insertion: its margin is > MG_MAX and a weak bit's is <= MG_MAX, so
 * the single ascending key already puts every weak entry ahead of it.
 * R7's completeness invariant is therefore STRUCTURAL (a DW entry can
 * never sort ahead of a weak one) and a full list drops the worst DW
 * entry first.  A_MAX/T_MAX/MG_MAX/MG_PAIR/A_PAIR/TIE_EMIT UNCHANGED:
 * T_MAX alone bounds the false-accept exposure. */
#define DW_EN     1         /* 0 restores the pre-Lever-B behaviour     */
#else
#define A_MAX     5         /* candidate list capacity AND admission cap */
#define A_PAIR    3         /* SS7.10 W2 bound (v2.2)                    */
#define MG_PAIR   4
#define T_MAX     16
#define REF_MAX   1
#define TIE_EMIT  8         /* emit gate: absolute zero-margin count     */
#define DW_EN     0         /* SS6.4 is v2.3-only: the compat geometries */
#endif                      /* stay byte-identical                       */
#define CRC8_POLY  0x07     /* superseded, compat geometries only        */
#define CRC16_POLY 0x1021
#define CRC16_INIT 0xFFFFu

#if !USE_ASM_DEC
#if WIRE23
static const uint8_t HDR[3] = {0xFF, 0xAA, 0x65};
static const uint8_t TRL[3] = {0x9A, 0x00, 0xFF};
#else
static const uint8_t HDR[4] = {0xFF, 0x00, 0xAA, 0x65};
static const uint8_t TRL[4] = {0x9A, 0x55, 0x00, 0xFF};
#endif
#endif /* asm builds carry the HT template in decode_asm.s */

/* ---- v2.3 syndrome base table ----------------------------------------
 * XP8[i] = x^(16 + 8*i) mod 0x11021, i = 0 .. 47.  The single-bit CRC16
 * syndrome of DATA byte p, bit weight b, is XP8[ND-1-p] * x^b, and
 * multiplying by x is ONE shift-and-fold, so syn16() is a u16 table load
 * plus <= 7 folds -- no modular reduction at all (v2.2 needed a %127
 * loop).  ONE table serves both geometries: the index runs from the LAST
 * data byte backwards, so ND = 16 uses XP8[0..15] and ND = 48 uses
 * XP8[0..47].  96 B of flash, against v2.2's XPOW[127]: the table SHRANK
 * by 31 B while the check DOUBLED in width. */
#if CHECK_EN && WIRE23 && !USE_ASM_DEC
static const uint16_t XP8[48] = {
    0x1021, 0x3331, 0x3730, 0x76B4, 0xAA51, 0x45A0, 0xB861, 0x47D3,
    0xEB23, 0x6F45, 0xD849, 0x0375, 0x4563, 0x7B61, 0xAEFC, 0xA824,
    0x10E2, 0xF031, 0xDE1F, 0x35B3, 0xD5F6, 0x6DD8, 0x650B, 0x3703,
    0x45B4, 0xAC61, 0x1566, 0x2494, 0xF0E6, 0x091F, 0x8E29, 0x5946,
    0x8DDC, 0x9C25, 0x6735, 0x2941, 0xF44B, 0xE49B, 0x26AA, 0xEEA4,
    0xB8E0, 0xC6D3, 0x6A8A, 0x47EC, 0xD423, 0xA8F9, 0xCDE2, 0xEAE1
};
#endif

/* XPOW[e] = x^e mod (x^8+x^2+x+1), e = 0..126; ord(x) = 127 so this one
 * flash table covers every frame size (SS7.2).  SUPERSEDED: compiled
 * only for the v2.2/v2.1 CRC8 compat geometries. */
#if CHECK_EN && !WIRE23
static const uint8_t XPOW[127] = {
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x07, 0x0E, 0x1C, 0x38,
    0x70, 0xE0, 0xC7, 0x89, 0x15, 0x2A, 0x54, 0xA8, 0x57, 0xAE, 0x5B, 0xB6,
    0x6B, 0xD6, 0xAB, 0x51, 0xA2, 0x43, 0x86, 0x0B, 0x16, 0x2C, 0x58, 0xB0,
    0x67, 0xCE, 0x9B, 0x31, 0x62, 0xC4, 0x8F, 0x19, 0x32, 0x64, 0xC8, 0x97,
    0x29, 0x52, 0xA4, 0x4F, 0x9E, 0x3B, 0x76, 0xEC, 0xDF, 0xB9, 0x75, 0xEA,
    0xD3, 0xA1, 0x45, 0x8A, 0x13, 0x26, 0x4C, 0x98, 0x37, 0x6E, 0xDC, 0xBF,
    0x79, 0xF2, 0xE3, 0xC1, 0x85, 0x0D, 0x1A, 0x34, 0x68, 0xD0, 0xA7, 0x49,
    0x92, 0x23, 0x46, 0x8C, 0x1F, 0x3E, 0x7C, 0xF8, 0xF7, 0xE9, 0xD5, 0xAD,
    0x5D, 0xBA, 0x73, 0xE6, 0xCB, 0x91, 0x25, 0x4A, 0x94, 0x2F, 0x5E, 0xBC,
    0x7F, 0xFE, 0xFB, 0xF1, 0xE5, 0xCD, 0x9D, 0x3D, 0x7A, 0xF4, 0xEF, 0xD9,
    0xB5, 0x6D, 0xDA, 0xB3, 0x61, 0xC2, 0x83
};
#endif

/* Marker template, BIT-REVERSED per byte, so it can be XORed straight
 * against d_bits (which packs frame bit t at byte t>>3, bit t&7).
 * HEADER then TRAILER.  v2.3: FF AA 65 / 9A 00 FF -> FF 55 A6 / 59 00 FF.
 * (TRAILER[1] = 0x00, the zeros calibration probe, is its own reversal.) */
#if !USE_ASM_DEC
#if WIRE23
static const uint8_t HTR[6] = {0xFF, 0x55, 0xA6, 0x59, 0x00, 0xFF};
#else
static const uint8_t HTR[8] = {0xFF, 0x00, 0x55, 0xA6,
                               0x59, 0xAA, 0x00, 0xFF};
#endif
#endif /* asm builds fold the template into decode_asm.s's XOR immediates */

/* popcount of a byte via a 16-entry nibble table (16 B of flash; the
 * shift-loop form is bigger in code and 8x slower). */
#if !USE_ASM_DEC
static const uint8_t POP4[16] = {0, 1, 1, 2, 1, 2, 2, 3,
                                 1, 2, 2, 3, 2, 3, 3, 4};

static uint8_t popc8(uint8_t x)
{
    return (uint8_t)(POP4[x & 0x0F] + POP4[x >> 4]);
}
#endif /* asm builds count the 6 marker bytes with a shift loop */

/* KNOWN frame template: -1 unknown, 0/1 marker bits (computed, no array) */
#if USE_ASM_DEC
extern int8_t known_bit(uint16_t t);    /* decode_asm.s (same ABI: X->A) */
#else
static int8_t known_bit(uint16_t t)
{
    if (t < 8 * HT_LEN)
        return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
    if (t >= NB - 8 * HT_LEN) {
        uint16_t u = t - (NB - 8 * HT_LEN);
        return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
    }
    return -1;
}
#endif /* !USE_ASM_DEC */

/* ====================================================================== */
/* Sample scanner: linearize + model clock + pulse detection.             */
/* Interface shared by the C fallback and scan.s (globals, no args --     */
/* keeps the hot call free of ABI traffic).                               */
/* ====================================================================== */

#if USE_ASM_SCAN
extern const uint8_t *scan_cap;   /* in scan.s                            */
extern uint16_t scan_len;
extern uint16_t scan_ra, scan_rb, scan_fa, scan_fb;
extern uint8_t  scan_sfa;
extern void    scan_init(void);
extern uint8_t scan_next(void);
#else /* ------------------------- C scanner (v1 ps_next, proven) ------ */

const uint8_t *scan_cap;
uint16_t scan_len;
uint16_t scan_ra, scan_rb, scan_fa, scan_fb;
uint8_t  scan_sfa;

static const uint8_t O_CY[8] = {0, 4, 9, 13, 17, 21, 27, 32};
static const int8_t  W_CY[8] = {0, -1, 0, 2, 0, 0, 0, 1};

static struct {
    uint16_t i;                 /* loop index                             */
    uint8_t  s;                 /* slot 0..7                              */
    uint16_t tbase;             /* i * LOOP_CY                            */
    int16_t  wsum;
    uint16_t t_prev;
    uint8_t  have_prev;
    uint8_t  in_pulse, seen, done;
    uint16_t low_run;
    uint16_t ra, rb, fa;
    uint8_t  sfa;
} ps;

void scan_init(void)
{
    ps.i = 0; ps.s = 0; ps.tbase = 0; ps.wsum = 0;
    ps.t_prev = 0; ps.have_prev = 0;
    ps.in_pulse = 0; ps.seen = 0; ps.done = 0; ps.low_run = 0;
    ps.ra = ps.rb = ps.fa = 0; ps.sfa = 0;
}

/* next pulse -> scan_ra/rb/fa/fb/sfa; returns 1, or 0 at stream end */
uint8_t scan_next(void)
{
    while (!ps.done) {
        uint8_t v, s = ps.s;
        uint16_t t;
        if (ps.i >= scan_len) break;
        if (s == 6 && ps.i + 1 < scan_len) {
            uint8_t bt = scan_cap[ps.i + 1];
            if (bt == 0x00 && !ps.in_pulse) {
                /* whole octet low (BS0,BS1 of loop i + R0..R5 of i+1) */
                ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
                ps.have_prev = 1;
                ps.low_run = (uint16_t)(ps.low_run + 8);
                ps.i++; ps.tbase += LOOP_CY;        /* s stays 6 */
                if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
                continue;
            }
            if (bt == 0xFF && ps.in_pulse) {
                /* whole octet high */
                ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
                ps.wsum += 2;               /* sum of W over the octet */
                ps.sfa = 5;
                ps.low_run = 0;
                ps.seen = 1;
                ps.t_prev = ps.fa;
                ps.have_prev = 1;
                ps.i++; ps.tbase += LOOP_CY;
                continue;
            }
        }
        if (s < 6) {
            v = (uint8_t)((scan_cap[ps.i] >> (5 - s)) & 1);
        } else {
            if (ps.i + 1 >= scan_len) {     /* last loop: BS lost */
                ps.i++; ps.s = 0; ps.tbase += LOOP_CY;
                continue;
            }
            v = (uint8_t)((scan_cap[ps.i + 1] >> (7 - (s - 6))) & 1);
        }
        t = (uint16_t)(ps.tbase + O_CY[s] + ps.wsum);
        if (s == 7) { ps.s = 0; ps.i++; ps.tbase += LOOP_CY; }
        else        { ps.s = (uint8_t)(s + 1); }
        if (v) {
            ps.wsum += W_CY[s];
            if (!ps.in_pulse) {
                ps.in_pulse = 1;
                ps.ra = ps.have_prev ? ps.t_prev
                        : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
                ps.rb = t;
            }
            ps.fa = t;
            ps.sfa = s;
            ps.low_run = 0;
            ps.seen = 1;
        } else {
            if (ps.in_pulse) {
                ps.in_pulse = 0;
                scan_ra = ps.ra; scan_rb = ps.rb;
                scan_fa = ps.fa; scan_fb = t; scan_sfa = ps.sfa;
                ps.t_prev = t; ps.have_prev = 1;
                ps.low_run = 1;
                return 1;
            }
            ps.low_run++;
            if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
        }
        ps.t_prev = t;
        ps.have_prev = 1;
    }
    if (ps.in_pulse) {                      /* capture ended high */
        ps.in_pulse = 0;
        scan_ra = ps.ra; scan_rb = ps.rb;
        scan_fa = ps.fa; scan_fb = (uint16_t)(ps.fa + FIRST_BR);
        scan_sfa = ps.sfa;
        return 1;
    }
    ps.done = 1;
    return 0;
}
#endif /* USE_ASM_SCAN */

/* ---- decoder state (static: the map file measures this) -------------- */

#if USE_ASM_DEC
/* SIZE LEVER (PROD_CLOSURE SS15.0 lever 1): decode_asm.s OWNS dec_info in
 * its ABS zero page, so its ~18 direct accesses each drop one address
 * byte.  The reservation there is `.ds 23`; this static assert is what
 * keeps the two in step (SDCC packs STM8 structs with alignment 1). */
typedef char dec_info_size_check[(sizeof(dec_info_t) == 23) ? 1 : -1];
#else
dec_info_t dec_info;
#endif

/* non-static: decode_asm.s reads these in USE_ASM_DEC builds */
uint16_t g_K;
int16_t  g_tau;

#if USE_ASM_DEC
/* frame geometry for decode_asm.s (sdas has no -D).  v2.3 drops g_ND /
 * g_NPP / g_CHK: the hand-assembled CHASE that read them is gone (the
 * pipeline tail is compiled from this file now -- see the note in
 * decode_asm.s), so only the streaming layer's constants remain. */
const uint16_t g_NB   = NB;
const uint32_t g_yend = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
const uint32_t g_ymid = (uint32_t)BIAS_U + (uint32_t)(NB / 2) * BIT_U;
const uint32_t g_Wu11 = ((uint32_t)(NB - 1) * BIT_U + H1P) << KQ;
const uint16_t g_NBmHT = NB - 8 * HT_LEN;
const uint16_t g_PPHI  = PP_HI;
const uint16_t g_ND8   = ND8;
/* v2.3: the PIPELINE TAIL is hand-assembled again (decode_asm.s), so it
 * needs the three geometry values the C tail spelled as macros.  g_TIEE
 * keeps the RETIRED R5 emit gate a one-constant change on the asm side
 * too -- the test is compiled/assembled, not deleted. */
const uint16_t g_TIEE  = TIE_EMIT;   /* R5 emit gate, still a constant */
const uint16_t g_PPB   = NBB;        /* d_pp   = &ov[NBB]              */
const uint16_t g_PPE   = NBB + ND_DATA;  /* check block = &ov[NBB+ND]  */
const uint16_t g_TRB   = NBB - HT_LEN;   /* trailer bytes in d_bits    */
#endif

/* calibration (label class 0/1 indexes the arrays).  USE_ASM_DEC builds
 * keep this whole layer (and its state) in decode_asm.s. */
#if !USE_ASM_DEC
static int16_t c_lo[2], c_hi[2];
static uint8_t c_n[2];
static int16_t c_h0c, c_h1c;
static int16_t d_h0e, d_h1e;                /* SS6.4: decide()'s fam pair */
static int8_t  c_d56[2];                    /* boundary shift, fams 5,6 */
static int16_t c_labx0[2], c_labx1[2], c_labx0b[2], c_labx1b[2];
static int16_t c_c0[2];
static int16_t c_gap56[2];
#endif

/* SS10.2 overlay, taken: the two 64-byte eps fold histograms are dead
 * once calibrate() returns (theta56 is their last reader), and the
 * decision bitmaps / payload bytes are first written after that
 * (decide_pass zeroes d_bits; chase fills d_pp).  Sharing the storage
 * saves NBB+NPP (112 B at v2.2 production geometry: 60+52 <= 128) of RAM
 * with identical behaviour -- re-proven by the host-parity + ucsim
 * harnesses like any other step. */
union ov_u {
    uint8_t hist[2][64];                    /* calibrate scratch        */
    struct {
        uint8_t bits[NBB];
        uint8_t pp[NPP];
    } d;                                    /* decision + chase state   */
};
union ov_u ov;                              /* non-static: asm writes bits */
#define c_hist (ov.hist)
#define d_bits (ov.d.bits)
#define d_pp   (ov.d.pp)

/* Decision + weak-set state.  In USE_ASM_DEC builds decode_asm.s owns
 * the decision PASS and declares this state itself (the counters in its
 * ABS zero page, the arrays in REL DATA) under exactly these names, so
 * the pipeline tail below -- which is compiled either way -- sees one
 * set of symbols and is bit-exact with the host-parity build by
 * construction. */
#if USE_ASM_DEC
extern uint16_t d_infeas, d_laberr, d_nseg;
extern uint16_t v_cand_t[A_MAX];
extern uint8_t  v_cand_m[A_MAX];
extern uint8_t  v_ncand;
extern uint16_t v_nweak, v_ntied;
#if WIRE23
extern uint16_t v_chkconf[CHK_LEN];
#endif
#else
static uint16_t d_infeas, d_laberr, d_nseg;
static uint16_t d_costs[A_CAP + 1];
static uint16_t d_inter;                    /* interior bitmask over a  */
static int16_t  v_tiepend;                  /* tie mark carried forward  */

/* v2 streaming weak-set accounting (SS6.2) */
static uint16_t v_cand_t[A_MAX];            /* payload' bit index        */
static uint8_t  v_cand_m[A_MAX];            /* margin, (m, index) asc    */
static uint8_t  v_ncand;
static uint16_t v_nweak, v_ntied;
uint16_t v_ndw;             /* SS6.4 count -- decode.h declares it a
                             * linker global so the harnesses can read it
                             * without a dec_info field on the target    */
#if WIRE23
/* per-check-byte confidence = sum of that byte's 8 bit margins (each
 * saturated at 255, so <= 2040).  v2.3 needs it for real: it RANKS the
 * candidates of a check-byte position that has no majority.  v2.2
 * computed it only for the never-enabled SS7.8 fallback. */
static uint16_t v_chkconf[CHK_LEN];
#endif
#endif

/* chase working set: d_pp lives in the overlay union above */

#define BGET(arr, t)  ((arr[(t) >> 3] >> ((t) & 7)) & 1)
#define BSET(arr, t)  (arr[(t) >> 3] |= (uint8_t)(1u << ((t) & 7)))

#if USE_ASM_DEC
extern uint8_t seed(void);          /* decode_asm.s (with map core)     */
#else
/* y = ((t*K) >> KQ) + tau -- signed, exactly as the Python reference    */
static int32_t map_raw(uint16_t t)
{
    return (int32_t)((uint32_t)t * g_K >> KQ) + g_tau;
}

/* ---- P1: endpoint seed ------------------------------------------------ */

static uint8_t seed(void)
{
    uint16_t np = 0;
    uint16_t r0m = 0, flm = 0;
    uint32_t Wu, K;
    scan_init();
    while (scan_next()) {
        if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
        flm = (uint16_t)((scan_fa + scan_fb) >> 1);
        np++;
    }
    if (np < 8 || flm <= r0m) return 0;
    Wu = (uint32_t)(NB - 1) * BIT_U + H1P;
    K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
    if (K < K_MIN || K > K_MAX) return 0;
    g_K = (uint16_t)K;
    {   /* RELAXATION A hardening: tau is an s16 in the contract, and the
         * wide v2.3 K window makes a SHORT-SPAN capture (late first rise
         * + small span) reachable, where BIAS_U - ((r0m*K) >> KQ) leaves
         * s16.  The Python reference asserts there; C and asm would wrap.
         * Refusing R1 on an out-of-range tau keeps all three bit-exact by
         * construction instead of by luck. */
        int32_t tau32 = (int32_t)BIAS_U -
                        (int32_t)((uint32_t)r0m * g_K >> KQ);
        if (tau32 < -32768L || tau32 > 32767L) return 0;
        g_tau = (int16_t)tau32;
    }
    return 1;
}
#endif /* !USE_ASM_DEC */

/* ---- P2: residual-regression refinement (x2) -------------------------- */

#if USE_ASM_DEC
extern void refine(void);           /* decode_asm.s */
#else
static void refine(void)
{
    uint32_t y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
    uint32_t mid_u = (uint32_t)BIAS_U + (uint32_t)(NB / 2) * BIT_U;
    uint16_t n_lo = 0, n_hi = 0;
    int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
    uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
    int32_t me_lo, me_hi, me, dk, dtau, K2;
    uint32_t my_lo, my_hi, my;
    int32_t de, dy;
    scan_init();
    while (scan_next()) {
        int32_t y;
        uint32_t q;
        int16_t e;
        y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
        if (y < 0) y = 0;
        if ((uint32_t)y > y_end) break;
        q = ((uint32_t)y + BIT_H) >> BIT_SH;
        e = (int16_t)(y - (int32_t)(q << BIT_SH));
        if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
        else                     { n_hi++; se_hi += e; sy_hi += (uint32_t)y; }
    }
    if (n_lo < 2 || n_hi < 2) return;
    me_lo = se_lo / (int32_t)n_lo;
    me_hi = se_hi / (int32_t)n_hi;
    my_lo = sy_lo / n_lo;
    my_hi = sy_hi / n_hi;
    de = me_hi - me_lo;
    dy = (int32_t)my_hi - (int32_t)my_lo;
    if (dy <= 0) return;
    dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
    me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
    my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
    dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
    K2 = (int32_t)g_K - dk;
    if (K2 < (int32_t)K_MIN || K2 > (int32_t)K_MAX) return;
    g_K = (uint16_t)K2;
    g_tau = (int16_t)(g_tau + dtau);
}
#endif /* !USE_ASM_DEC */

/* ---- segment stream (gap accounting) ----------------------------------
 * Iterator over (k0, k1, u, v, fam) with same-bit merging (v1, minus the
 * OADJ_U reads -- that table was zero, bit-identical).
 */
typedef struct {
    uint16_t k0, k1;
    int16_t u, v;
    uint8_t fam;
} Seg;

#if USE_ASM_DEC
/* decode_asm.s owns the segment-stream state and iterator, the shared
 * segment record, and the a_bounds worker calibrate uses */
extern void ss_init(void);
extern uint8_t ss_next(Seg *out);
#else
static struct {
    uint32_t y_end;
    uint32_t y_prev;
    uint8_t  have_y;
    uint16_t n;
    uint8_t  pend;
    uint16_t p_k0;
    int16_t  p_u, p_v;
    uint8_t  p_fam;
    uint8_t  src_done;
} ss;

static void ss_init(void)
{
    scan_init();
    ss.y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
    ss.y_prev = 0; ss.have_y = 0; ss.n = 0;
    ss.pend = 0; ss.src_done = 0;
    ss.p_k0 = 0; ss.p_u = 0; ss.p_v = 0; ss.p_fam = 0;
}

static uint8_t ss_next(Seg *out)
{
    while (!ss.src_done) {
        int32_t y, yfa, yfb;
        uint32_t base;
        int32_t d;
        int16_t dn;
        if (!scan_next()) { ss.src_done = 1; break; }
        y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
        if (y < 0) y = 0;
        if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
        if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
        else {
            d = y - (int32_t)ss.y_prev;
            dn = (int16_t)((d + BIT_H) >> BIT_SH);
            if (dn > 0) ss.n = (uint16_t)(ss.n + dn);
        }
        ss.y_prev = (uint32_t)y;
        yfa = map_raw(scan_fa);
        yfb = map_raw(scan_fb);
        if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
            base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
            ss.p_u = (int16_t)(yfa - (int32_t)base);
            ss.p_v = (int16_t)(yfb - (int32_t)base);
            ss.p_fam = scan_sfa;
            continue;
        }
        if (ss.pend) {
            out->k0 = ss.p_k0;
            out->k1 = (ss.n < NB) ? ss.n : NB;
            out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
            if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
            base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
            ss.p_k0 = ss.n;
            ss.p_u = (int16_t)(yfa - (int32_t)base);
            ss.p_v = (int16_t)(yfb - (int32_t)base);
            ss.p_fam = scan_sfa;
            return 1;
        }
        if (ss.n >= NB) { ss.src_done = 1; break; }
        base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
        ss.pend = 1;
        ss.p_k0 = ss.n;
        ss.p_u = (int16_t)(yfa - (int32_t)base);
        ss.p_v = (int16_t)(yfb - (int32_t)base);
        ss.p_fam = scan_sfa;
    }
    if (ss.pend) {
        ss.pend = 0;
        out->k0 = ss.p_k0; out->k1 = NB;
        out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
        return 1;
    }
    return 0;
}
#endif /* !USE_ASM_DEC */

/* ---- marker constraints ----------------------------------------------- */

#if !USE_ASM_DEC
static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
{
    uint16_t t, e = (k1 < NB) ? k1 : NB;
    *amin = 0;
    *amax = (int16_t)(k1 - k0);
    for (t = k0; t < e; t++) {
        int8_t kb = known_bit(t);
        if (kb == 1) {
            int16_t m = (int16_t)(t - k0 + 1);
            if (m > *amin) *amin = m;
        } else if (kb == 0) {
            int16_t m = (int16_t)(t - k0);
            if (m < *amax) *amax = m;
        }
    }
}
#endif /* !USE_ASM_DEC */

/* ---- P3: calibration --------------------------------------------------- */

#if USE_ASM_DEC
extern void calibrate(void);        /* decode_asm.s owns P3 entirely */
#else
static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                             int16_t a, int16_t *lo, int16_t *hi)
{
    int16_t L = (int16_t)(k1 - k0);
    int16_t mid, d0, d1, off;
    int8_t cls;
    if (a == 0) { off = 0; cls = 0; }
    else if (a == L) { off = (int16_t)((L - 1) * BIT_U); cls = 1; }
    else {
        mid = (int16_t)((u + v) >> 1);
        d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
        if (d1 < 0) d1 = (int16_t)-d1;
        d0 = (int16_t)(mid - (a * BIT_U + H0P));
        if (d0 < 0) d0 = (int16_t)-d0;
        if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
        if (d1 <= d0) { off = (int16_t)((a - 1) * BIT_U); cls = 1; }
        else          { off = (int16_t)(a * BIT_U);       cls = 0; }
    }
    *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
    return cls;
}

static void cal_cloud(int16_t u, uint8_t fam)
{
    int16_t d, x;
    uint8_t f;
    if (fam != 5 && fam != 6) return;
    if (u < 0) return;
    f = (uint8_t)(fam - 5);
    x = (int16_t)(u & (BIT_U - 1));
    d = (int16_t)(x - c_c0[f]);
    if (d >= -EPS_HIST && d < EPS_HIST) {
        uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
        if (c_hist[f][b] < 255) c_hist[f][b]++;
    }
}

static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                    uint8_t fam, int16_t a)
{
    int16_t lo, hi;
    int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
    if (cls < 0) return;
    {
        uint8_t ci = (uint8_t)cls;
        if (lo > c_lo[ci]) c_lo[ci] = lo;
        if (hi < c_hi[ci]) c_hi[ci] = hi;
        if (c_n[ci] < 255) c_n[ci]++;
    }
    if ((fam == 5 || fam == 6) && lo >= 0) {
        uint8_t f = (uint8_t)(fam - 5);
        int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
        if (d >= -EPS_HIST && d < EPS_HIST) {
            if (cls == 0) {
                if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
                else if (d > c_labx0b[f]) c_labx0b[f] = d;
            } else {
                if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
                else if (d < c_labx1b[f]) c_labx1b[f] = d;
            }
        }
    }
}

/* largest label-feasible density gap (or clamp) in fold coordinate d */
static uint8_t theta56(uint8_t f, int16_t *theta_out)
{
    int16_t x0 = c_labx0[f], x1 = c_labx1[f];
    uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
    int16_t zlo = (int16_t)(x0 + 1);
    int16_t zhi = x1;
    int16_t theta = 0;
    uint8_t have_theta = 0;
    int16_t top = 0;
    uint8_t have_top = 0, clear1 = 0;
    uint8_t b;
    if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
    if (zhi > EPS_ZONE) zhi = EPS_ZONE;
    if (zlo < zhi) {
        uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
        uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
        int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
        uint8_t nocc = 0;
        for (b = blo; b <= bhi; b++) {
            if (c_hist[f][b]) {
                int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
                int16_t gp = (int16_t)(x - prev);
                if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
                prev = x;
                nocc++;
            }
        }
        {
            int16_t gp = (int16_t)(zhi - prev);
            if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
        }
        if (nocc == 0) {
            if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
        } else {
            uint8_t ok = (bg >= EPS_GAP_MIN);
            if (ok && (uint8_t)(nocc + 1) >= 4) {
                /* s16-safe (assert-guarded in embedded_v2.py _theta56):
                 * bg <= 2*EPS_ZONE = 64, nocc+1 <= 34 -> |lhs| <= 4352,
                 * |rhs| <= 320.  Same values in 16-bit (SDCC) and 32-bit
                 * (host) int, so one expression serves both builds. */
                if (2 * bg * (nocc + 1) < 5 * (zhi - zlo))
                    ok = 0;
            }
            if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
        }
    }
    if (has0 || has1) {
        int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
        if (has0) {
            wlo = (int16_t)(x0 - EPS_SLACK1);
            if (c_labx0b[f] > -0x4000 &&
                (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
                wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
        }
        if (has1) {
            whi = (int16_t)(x1 + EPS_SLACK1);
            if (c_labx1b[f] < 0x3FFF &&
                (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
                whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
        }
        if (wlo > whi) {
            theta = (int16_t)((wlo + whi) >> 1);
            have_theta = 1;
        } else {
            int16_t th = have_theta ? theta : 0;
            if (th < wlo) th = wlo;
            if (th > whi) th = whi;
            theta = th;
            have_theta = 1;
        }
    }
    for (b = 0; b < 64; b++) {
        int16_t d;
        if (!c_hist[f][b]) continue;
        d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
        if (d > EPS_CLEAR1) clear1 = 1;
        else if (d > -EPS_CLAMP56) {
            if (!have_top || d > top) top = d;
            have_top = 1;
        }
    }
    if (!clear1 && have_top) {
        int16_t floor_ = (int16_t)(top + EPS_TOPM);
        if (!have_theta || floor_ > theta) theta = floor_;
        have_theta = 1;
        if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
            theta > (int16_t)(x1 + EPS_SLACK))
            theta = (int16_t)(x1 + EPS_SLACK);
    }
    *theta_out = theta;
    return have_theta;
}

/* interval-intersection width fit for label class ci, prior-clamped */
static int16_t width_fit(uint8_t ci, int16_t prior, int16_t blo, int16_t bhi)
{
    int16_t lo = c_lo[ci], hi = c_hi[ci], h;
    if (c_n[ci] < LAB_MIN) return prior;
    h = (lo > hi) ? (int16_t)((lo + hi) >> 1)
        : (prior < lo ? lo : (prior > hi ? hi : prior));
    return (h >= blo && h <= bhi) ? h : prior;
}

static void calibrate(void)
{
    Seg sg;
    uint8_t f;
    c_lo[0] = c_lo[1] = -0x4000;
    c_hi[0] = c_hi[1] = 0x3FFF;
    c_n[0] = c_n[1] = 0;
    c_h0c = H0P; c_h1c = H1P;
    c_d56[0] = c_d56[1] = 0;
    c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
    c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
    for (f = 0; f < 2; f++) {
        uint8_t b;
        c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
        for (b = 0; b < 64; b++) c_hist[f][b] = 0;
        c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
        c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
    }
    ss_init();
    while (ss_next(&sg)) {
        uint16_t t, e;
        uint8_t known_all = 1;
        int16_t amin, amax;
        cal_cloud(sg.u, sg.fam);
        if (sg.k1 > NB) continue;
        e = (sg.k1 < NB) ? sg.k1 : NB;
        for (t = sg.k0; t < e; t++)
            if (known_bit(t) < 0) { known_all = 0; break; }
        if (!known_all) continue;
        a_bounds(sg.k0, sg.k1, &amin, &amax);
        if (amin == amax)
            cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
    }
    /* width fit: intersection, prior-clamped, guarded */
    {
        int16_t h0 = width_fit(0, H0P, H0_LO, H0_HI);
        int16_t h1 = width_fit(1, H1P, H1_LO, H1_HI);
        if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
        c_h0c = h0; c_h1c = h1;
    }
    for (f = 0; f < 2; f++) {
        int16_t th, cfit, delta;
        if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
        cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
        delta = (int16_t)(th + c_c0[f] - cfit);
        if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
        if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
        c_d56[f] = (int8_t)delta;
    }
}
#endif /* !USE_ASM_DEC */

/* ---- P4: decision ------------------------------------------------------ */

#if USE_ASM_DEC
extern void decide_pass(void);      /* decode_asm.s owns the whole pass */
#else
/* hinge cost, EXACT: u,v,h are s16 but u-h / h-v span up to ~±40.3k
 * (|u|,|v| <= 32767, |h| <= 15*512+400 under the A_CAP cap).  The
 * RELATION is decided on the s16 values (exact); the magnitude is then
 * the u16 wrap of the difference, which equals the exact value whenever
 * the relation holds (0 < diff <= 65534).  This is precisely what the
 * asm port computes (SUBW sets V; JRSGT is overflow-aware; the stored
 * 16-bit difference is the exact magnitude), and what the Python
 * reference's unbounded ints produce.  A previous version compared the
 * s16-WRAPPED difference instead and diverged from both on garbage
 * segments (fuzz_v22 E05). */
static uint16_t hinge(int16_t u, int16_t v, int16_t h)
{
    uint16_t g = 0, d;
    if (u > h) {
        d = (uint16_t)((uint16_t)u - (uint16_t)h);
        if (d > g) g = d;
    }
    if (h > v) {
        d = (uint16_t)((uint16_t)h - (uint16_t)v);
        if (d > g) g = d;
    }
    return g;
}

/* argmin over d_costs[lo..hi], tie-break interior-before-grazing then
 * smallest a -- shared by the free and the marker-forced range */
static int16_t argmin_ab(int16_t lo, int16_t hi)
{
    uint16_t bc = 0xFFFF;
    uint8_t bi = 1;
    int16_t a, best = lo;
    for (a = lo; a <= hi; a++) {
        uint8_t it = (uint8_t)((d_inter >> a) & 1);
        if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
            bc = d_costs[a]; bi = it; best = a;
        }
    }
    return best;
}

/* fills d_costs / d_inter for a in [0..acap]; returns acap */
static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                      uint8_t fam, int16_t *a_hat, int16_t *a_free,
                      int16_t *lo_out, int16_t *hi_out)
{
    int16_t L = (int16_t)(k1 - k0);
    int16_t acap = (L < A_CAP) ? L : A_CAP;
    int16_t h0e = c_h0c, h1e = c_h1c;
    int16_t amin, amax, lo, hi, a;
    if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
    if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
    d_h0e = h0e; d_h1e = h1e;       /* SS6.4 reads them per bit */
    d_inter = 0;
    for (a = 0; a <= acap; a++) {
        uint16_t c;
        uint8_t it;
        if (a == 0) {
            c = hinge(u, v, h0e);
            it = (u < h0e && h0e <= v);
        } else {
            int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
            c = hinge(u, v, h);
            it = (u < h && h <= v);
            if (a < L) {
                int16_t h2 = (int16_t)(a * BIT_U + h0e);
                uint16_t c2 = hinge(u, v, h2);
                if (c2 < c) c = c2;
                if (u < h2 && h2 <= v) it = 1;
            }
        }
        d_costs[a] = c;
        if (it) d_inter |= (uint16_t)(1u << a);
    }
    /* free argmin: (cost, !interior, a) */
    *a_free = argmin_ab(0, acap);
    a_bounds(k0, k1, &amin, &amax);
    lo = (amin > 0) ? amin : 0;
    hi = (amax < acap) ? amax : acap;
    if (lo > hi) { lo = 0; hi = acap; }
    *a_hat = argmin_ab(lo, hi);
    *lo_out = lo; *hi_out = hi;
    return acap;
}

/* sorted top-A_MAX insertion, key (margin, bit index) ascending (SS6.2) */
static void cand_insert(uint16_t k, uint8_t m)
{
    uint8_t i = v_ncand, j;
    while (i > 0 && v_cand_m[i - 1] > m) i--;
    if (i >= A_MAX) return;
    j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
    while (j > i) {
        v_cand_t[j] = v_cand_t[j - 1];
        v_cand_m[j] = v_cand_m[j - 1];
        j--;
    }
    v_cand_t[i] = k;
    v_cand_m[i] = m;
    if (v_ncand < A_MAX) v_ncand++;
}

static void decide_pass(void)
{
    Seg sg;
    uint16_t t;
    for (t = 0; t < NBB; t++) d_bits[t] = 0;
    d_infeas = 0; d_laberr = 0; d_nseg = 0;
    v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1; v_ndw = 0;
#if WIRE23
    for (t = 0; t < CHK_LEN; t++) v_chkconf[t] = 0;
#endif
    ss_init();
    while (ss_next(&sg)) {
        int16_t a_hat, a_free, lo, hi, acap, a;
        int16_t L = (int16_t)(sg.k1 - sg.k0);
        int16_t tie_here = -1, ins0 = -1;
        uint16_t kk1, c_hat;
        uint8_t known_all, dead, nins;
        d_nseg++;
        if (sg.k0 >= NB) continue;
        acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
                      &a_hat, &a_free, &lo, &hi);
        c_hat = d_costs[a_hat];
        if (c_hat > INFEAS_U) d_infeas++;
        kk1 = (sg.k1 < NB) ? sg.k1 : NB;
        known_all = 1;
        for (t = sg.k0; t < kk1; t++)
            if (known_bit(t) < 0) { known_all = 0; break; }
        dead = 0; nins = 0;
        for (a = 0; a <= acap; a++)
            if ((d_inter >> a) & 1) nins++;
        if (nins >= 2) dead = 1;
        if (known_all && lo == hi && a_free != lo && !dead)
            d_laberr++;
        /* dead-window tie inside the allowed range: the tie mark can land
         * one segment ahead (t == k1); a single pending slot replaces the
         * v1 tied[] bitmap -- proven bit-identical in the reference */
        /* The v1 form also required a_hat in {ins0, ins1}, which is
         * ALWAYS TRUE: an interior boundary has hinge cost 0 and
         * argmin_ab's key is (cost, NOT interior, index) ascending, so a
         * non-empty interior set forces a_hat == ins0.  Proven in
         * dev_lever_b/ins0_proof.py over 1 619 577 decided segments of
         * every corpus and both fuzz sets, 0 counterexamples -- so ins1
         * is never read and the test is not made (26 B of assembly). */
        nins = 0;
        for (a = lo; a <= hi; a++) {
            if ((d_inter >> a) & 1) {
                if (nins == 0) ins0 = a;
                nins++;
            }
        }
        if (nins >= 2) {
            uint16_t tt = (uint16_t)(sg.k0 + ins0);
            if (tt < NB) tie_here = (int16_t)tt;
        }
        /* emit bits + stream the margins (SS6) + the SS6.4 geometry test
         * (stateless: hb is a pure function of off) */
        for (t = sg.k0; t < kk1; t++) {
            int16_t off = (int16_t)(t - sg.k0);
            uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
            uint8_t is_dw = 0;
            if (off < DW_OFF_MAX) {
                int16_t hb = (int16_t)(off << BIT_SH);
                is_dw = (uint8_t)(((int16_t)(hb + d_h0e) <= sg.u)
                                  == (sg.v < (int16_t)(hb + d_h1e)));
            }
            if (off < a_hat) BSET(d_bits, t);
            for (a = lo; a <= hi; a++) {
                if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
                else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
            }
            if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
            else {
                int16_t dm = (int16_t)(c0m - c1m);
                if (dm < 0) dm = (int16_t)-dm;
                m = (dm > 255) ? 255 : (uint16_t)dm;
            }
            if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
                m = 0;                       /* decided by tie-break */
            if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
                uint16_t k = t - PP_LO;
#if WIRE23
                if (k >= ND8) v_chkconf[(k - ND8) >> 3] += m;
#endif
                if (m <= MG_MAX) {
                    v_nweak++;
                    if (m == 0) v_ntied++;
                    cand_insert(k, (uint8_t)m);
                } else if (DW_EN && is_dw) {      /* SS6.4 */
                    v_ndw++;
                    cand_insert(k, (uint8_t)m);
                }
            }
        }
        if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
            v_tiepend = -1;                  /* consumed              */
        if (tie_here >= (int16_t)kk1)
            v_tiepend = tie_here;            /* lands in next segment */
    }
}
#endif /* !USE_ASM_DEC */

/* ---- CRC chase (SS7) --------------------------------------------------- */
/* THE PIPELINE TAIL IS HAND-ASSEMBLED AGAIN IN USE_ASM_DEC BUILDS.
 *
 * v2.3 first shipped it as compiled C on the argument that a 16-bit
 * residual, an independent per-byte majority, a confidence-ranked
 * reference CROSS PRODUCT and a residual-comparison budget are the
 * intricate half of the decoder and are bit-exact with embedded_v2.py by
 * construction if they come from this file.  That argument was correct
 * and the flash bill was 1641 B of CODE + 138 B of CONST -- 531 B of the
 * 748 B by which the v2.3 production link overflowed (PROD_CLOSURE
 * SS13.1).  The tail is now assembled in decode_asm.s (crc16 / rank3 /
 * ref_build / ch_match / try_trial / chase_singles / chase_pairs /
 * chase / ws_decode_ex), and EVERYTHING BELOW STAYS as the host-parity
 * reference the assembly is diffed against: dev_prod/parity_v23.py
 * proves this C against embedded_v2.py, dev_prod/ucsim_v23.py proves the
 * assembly against the same reference at both geometries.  Nothing here
 * was deleted or simplified to make room. */

#if !USE_ASM_DEC

#if CHECK_EN

#if WIRE23
/* ---------------------------- v2.3: CRC16 ------------------------------ */

static uint16_t crc16(const uint8_t *d, uint8_t n)
{
    uint16_t r = CRC16_INIT;
    uint8_t i, j;
    for (i = 0; i < n; i++) {
        r ^= (uint16_t)((uint16_t)d[i] << 8);
        for (j = 0; j < 8; j++)
            r = (r & 0x8000u) ? (uint16_t)((uint16_t)(r << 1) ^ CRC16_POLY)
                              : (uint16_t)(r << 1);
    }
    return r;
}

/* Syndrome of payload'-relative DATA bit k = XP8[ND-1-p] * x^b, and
 * multiplying by x is ONE shift-and-fold, so this is a u16 table load
 * plus at most 7 folds -- no modular reduction at all (v2.2 needed a
 * %127 loop on top of its table). */
static uint16_t syn16(uint16_t k)
{
    uint8_t b = (uint8_t)(7 - (k & 7));
    uint16_t r = XP8[ND_DATA - 1 - (uint8_t)(k >> 3)];
    while (b--)
        r = (r & 0x8000u) ? (uint16_t)((uint16_t)(r << 1) ^ CRC16_POLY)
                          : (uint16_t)(r << 1);
    return r;
}

static uint8_t parity16(uint16_t x)
{
    x ^= (uint16_t)(x >> 8);
    x ^= (uint16_t)(x >> 4);
    x ^= (uint16_t)(x >> 2);
    x ^= (uint16_t)(x >> 1);
    return (uint8_t)(x & 1);
}

/* ---- the reference set (SS7.1) ---------------------------------------
 * ch_val[0..2] = HI candidate values, ch_val[3..5] = LO candidates, each
 * position's list best-confidence FIRST: ONE entry when that byte
 * position has a per-byte majority, else its three distinct values.
 * ch_ref[0..ch_nref-1] is the materialised reference set -- the cross
 * product in DIAGONAL order (rank-sum ascending, then HI-rank
 * ascending), truncated to the cap.  Materialising it is what keeps
 * ch_match down to an array scan: every residual comparison walks this
 * list, and it is walked up to T_MAX = 131 times per frame. */
static uint8_t  ch_nhi, ch_nlo, ch_nref;
/* SS10.2 OVERLAY: ch_ref (2*REF_MAX = 18 B) and ch_val (6 B) are
 * CHASE-only, and d_costs[16] (32 B) is decision-pass scratch that is
 * dead the moment decide_pass() returns -- the chase never calls
 * decide().  Sharing the storage saves 24 B of RAM with identical
 * behaviour, the same discipline the eps-histogram/bits+pp overlay
 * already uses.  In USE_ASM_DEC builds d_costs lives in decode_asm.s
 * (same name, same 32 B); either way the two live ranges are disjoint.
 * 2*REF_MAX + 6 = 24 <= 32 is asserted at compile time below. */
#if USE_ASM_DEC
extern uint16_t d_costs[A_CAP + 1];
#endif
#define ch_ref ((uint16_t *)(void *)d_costs)
#define ch_val (((uint8_t *)(void *)d_costs) + 2 * REF_MAX)
typedef char ch_ov_fits[(2 * REF_MAX + 6 <= 2 * (A_CAP + 1)) ? 1 : -1];

/* One byte position.  base = 0 (HI) or 1 (LO); the three copies sit at
 * d_pp[ND + base], +2, +4 and their confidences at v_chkconf[base+0/2/4].
 *
 * Three votes admit NO tie (at most one value can reach two), so the
 * majority test is three compares.  When all three differ, each copy's
 * RANK is the number of copies that beat it -- higher confidence, or
 * equal confidence and an earlier wire position.  That double loop is
 * the whole ordering: no sort, no key array. */
static void rank3(uint8_t base, uint8_t *out, uint8_t *n)
{
    uint8_t v0 = d_pp[ND_DATA + base];
    uint8_t v1 = d_pp[ND_DATA + base + 2];
    uint8_t v2 = d_pp[ND_DATA + base + 4];
    if (v0 == v1 || v0 == v2) { out[0] = v0; *n = 1; return; }
    if (v1 == v2)             { out[0] = v1; *n = 1; return; }
    /* Each copy's RANK is how many copies beat it: higher confidence, or
     * equal confidence and an earlier wire position.  That is exactly
     * the ordering the reference gets from sorted(key=(-conf, index)),
     * with no sort and no key array. */
    {
        uint8_t i, j, r;
        for (j = 0; j < 3; j++) {
            uint16_t cj = v_chkconf[base + 2 * j];
            r = 0;
            for (i = 0; i < 3; i++) {
                uint16_t ci = v_chkconf[base + 2 * i];
                if (ci > cj || (ci == cj && i < j)) r++;
            }
            out[r] = (j == 0) ? v0 : ((j == 1) ? v1 : v2);
        }
    }
    *n = 3;
}

/* cap = REF_MAX normally, 1 on the marker-suspect path (RELAXATION B) */
static void ref_build(uint8_t cap)
{
    uint8_t a, b, sm, q = 0;
    rank3(0, ch_val, &ch_nhi);
    rank3(1, ch_val + 3, &ch_nlo);
    for (sm = 0; sm < 5; sm++)
        for (a = 0; a < ch_nhi; a++) {
            if (a > sm) break;
            b = (uint8_t)(sm - a);
            if (b >= ch_nlo) continue;
            if (q >= cap) { ch_nref = q; return; }
            ch_ref[q++] = (uint16_t)
                (((uint16_t)ch_val[a] << 8) | ch_val[3 + b]);
        }
    ch_nref = q;
}

static uint16_t ch_rbase;                   /* crc16(D)                  */
static uint8_t  ch_n;                       /* candidates in play        */
static uint8_t  ch_comps;                   /* residual comparisons used */
static uint8_t  ch_cap;                     /* reference cap (1 or 9)    */

/* candidate i is a DATA bit (check-block bits sit at >= ND8).
 * Recomputed on demand: measured smaller than both a cached RAM array
 * and a packed bitmask under SDCC's stm8 codegen. */
static uint8_t ch_isd(uint8_t i)
{
    return (uint8_t)(v_cand_t[i] < ND8);
}

/* Residual test against the CURRENT reference set.  1 = accept,
 * 0 = no match, 2 = T_MAX budget exhausted.  Every comparison is one
 * 2^-16 exposure and one unit of budget -- THIS COUNTER IS THE BOUND. */
static uint8_t ch_match(uint16_t r)
{
    uint8_t q;
    for (q = 0; q < ch_nref; q++) {
        if (ch_comps >= T_MAX) return 2;
        ch_comps++;
        if (r == ch_ref[q]) return 1;
    }
    return 0;
}

/* Toggle payload'-relative bit k inside d_pp (data or check byte). */
static void pp_flip(uint16_t k)
{
    d_pp[k >> 3] ^= (uint8_t)(1u << (7 - (k & 7)));
}

/* Evaluate one flip set {i} or {i,j} (j = 0xFF for singles).  1 accept
 * (DATA flips left applied), 0 reject, 2 budget exhausted.
 *
 * Check-block bits are flipped IN PLACE in d_pp and flipped back unless
 * the trial is accepted -- on accept only the DATA bytes are emitted, so
 * the check block's state stops mattering.  That removes both the local
 * copy and the restore buffer v2.2 carried.
 *
 * NO ALIAS GUARD: at 16 bits every data-bit syndrome in a <= 432-bit
 * payload' is DISTINCT (ord(x) mod 0x11021 = 32767), so the v2.2 SS7.7
 * ambiguity cannot exist.  Proven in embedded_v2._selftest(). */
static uint8_t try_trial(uint8_t i, uint8_t j)
{
    uint8_t touched = 0, res;
    uint16_t r = ch_rbase;
    dec_info.trials++;
    if (ch_isd(i)) r ^= syn16(v_cand_t[i]);
    else { pp_flip(v_cand_t[i]); touched = 1; }
    if (j != 0xFF) {
        if (ch_isd(j)) r ^= syn16(v_cand_t[j]);
        else { pp_flip(v_cand_t[j]); touched = 1; }
    }
    if (touched) ref_build(ch_cap);         /* the flips MOVED the ref */
    res = ch_match(r);
    if (res != 1) {
        if (touched) {                      /* undo, restore the base set */
            if (!ch_isd(i)) pp_flip(v_cand_t[i]);
            if (j != 0xFF && !ch_isd(j)) pp_flip(v_cand_t[j]);
            ref_build(ch_cap);
        }
        return res;
    }
    if (ch_isd(i)) pp_flip(v_cand_t[i]);    /* accept: apply DATA flips */
    if (j != 0xFF && ch_isd(j)) pp_flip(v_cand_t[j]);
    return 1;
}

#else /* --------------------- v2.2 / v2.1: CRC8 (compat) --------------- */

static uint8_t crc8(const uint8_t *d, uint8_t n)
{
    uint8_t r = 0, i, j;
    for (i = 0; i < n; i++) {
        r ^= d[i];
        for (j = 0; j < 8; j++)
            r = (r & 0x80) ? (uint8_t)((uint8_t)(r << 1) ^ CRC8_POLY)
                           : (uint8_t)(r << 1);
    }
    return r;
}

/* syndrome of payload'-relative DATA bit k: XPOW[(8*(ND-1-p)+b+8) % 127] */
static uint8_t syn8(uint16_t k)
{
    uint8_t p = (uint8_t)(k >> 3);
    uint8_t b = (uint8_t)(7 - (k & 7));
    uint16_t j = (uint16_t)(8u * (uint16_t)(ND_DATA - 1 - p) + b + 8u);
    while (j >= 127u) j -= 127u;   /* <= 4 iterations at ND = 48 */
    return XPOW[j];
}

static uint8_t bmask(uint16_t k)
{
    return (uint8_t)(1u << (7 - (k & 7)));
}

static uint8_t parity8(uint8_t x)
{
    x ^= (uint8_t)(x >> 4);
    x ^= (uint8_t)(x >> 2);
    x ^= (uint8_t)(x >> 1);
    return (uint8_t)(x & 1);
}

/* Unique >=2-vote byte-equality majority over the CHK_LEN decoded check
 * bytes (the SUPERSEDED block-level vote). */
#if CHK_LEN == 3
static uint8_t maj_n(const uint8_t *c, uint8_t *r)
{
    if (c[0] == c[1] || c[0] == c[2]) { *r = c[0]; return 1; }
    if (c[1] == c[2])                 { *r = c[1]; return 1; }
    return 0;
}
#else
static uint8_t maj_n(const uint8_t *c, uint8_t *r)
{
    uint8_t i, j, cnt, have = 0, best = 0;
    for (i = 0; i < CHK_LEN; i++) {
        cnt = 0;
        for (j = 0; j < CHK_LEN; j++)
            if (c[j] == c[i]) cnt++;
        if (cnt >= 2) {
            if (!have) { best = c[i]; have = 1; }
            else if (c[i] != best) return 0;     /* 2-2 tie */
        }
    }
    if (have) *r = best;
    return have;
}
#endif

static uint8_t ch_rbase;                    /* crc8(D)                   */
static uint8_t ch_n;                        /* candidates in play        */

static uint8_t ch_isd(uint8_t i)
{
    return (uint8_t)(v_cand_t[i] < ND8);
}

static uint8_t try_trial(uint8_t i, uint8_t j)
{
    uint8_t Cp[CHK_LEN];
    uint8_t sel[2];
    uint8_t r = ch_rbase, Rp, m, idx, amb;
    for (m = 0; m < CHK_LEN; m++)
        Cp[m] = d_pp[ND_DATA + m];
    sel[0] = i; sel[1] = j;
    dec_info.trials++;
    for (m = 0; m < 2; m++) {
        uint16_t k;
        idx = sel[m];
        if (idx == 0xFF) break;
        k = v_cand_t[idx];
        if (k < ND8) {
            r ^= syn8(k);
        } else {
            uint16_t kc = k - ND8;
            Cp[kc >> 3] ^= bmask(k);
        }
    }
    if (!maj_n(Cp, &Rp)) return 0;           /* slot burned, no ref */
    if (r != Rp) return 0;
    /* alias guard (SS7.7): NEEDED here -- ord(x) mod 0x107 = 127 < 128 */
    amb = 0;
    for (m = 0; m < 2; m++) {
        uint16_t ki;
        uint8_t si, jj;
        idx = sel[m];
        if (idx == 0xFF) break;
        ki = v_cand_t[idx];
        if (ki >= ND8) continue;
        si = syn8(ki);
        for (jj = 0; jj < ch_n; jj++) {
            if (jj == i || jj == j) continue;
            if (v_cand_t[jj] < ND8) {
                dec_info.alias_cmp++;
                if (syn8(v_cand_t[jj]) == si) amb = 1;
            }
        }
    }
    if (amb) return 0;
    for (m = 0; m < 2; m++) {
        uint16_t k;
        idx = sel[m];
        if (idx == 0xFF) break;
        k = v_cand_t[idx];
        if (k < ND8)
            d_pp[k >> 3] ^= bmask(k);
    }
    return 1;
}

#endif /* WIRE23 */

/* one single-flip phase: candidates whose is-data flag == want, in list
 * (= confidence) order.  1 = accepted, 2 = budget exhausted (v2.3). */
static uint8_t chase_singles(uint8_t want)
{
    uint8_t p, r;
    for (p = 0; p < ch_n; p++)
        if (ch_isd(p) == want) {
            r = try_trial(p, 0xFF);
            if (r) return r;
        }
    return 0;
}

/* one pair phase: p < j lexicographic, filtered by isd[p] + isd[j] ==
 * sum_want (0 = both check, 1 = mixed, 2 = both data) -- exactly the
 * SS7.4 phase-2/4/5 enumeration orders.
 *
 * SS7.10 W2 bound: j (the LARGER index, hence the LARGER margin -- the
 * list is sorted (margin, index) ascending) must be inside the A_PAIR
 * weakest AND at margin <= MG_PAIR.  Both tests are monotone in j, so
 * failing either ends the inner loop.  At v2.3 A_PAIR = A_MAX and
 * MG_PAIR = MG_MAX, so the bound admits every ADMITTED weak pair and the
 * hard budget bound is T_MAX comparisons instead. */
static uint8_t chase_pairs(uint8_t sum_want)
{
    uint8_t p, j, r;
    for (p = 0; p < ch_n; p++)
        for (j = (uint8_t)(p + 1); j < ch_n; j++) {
#if A_PAIR < A_MAX || MG_PAIR < MG_MAX
            if (j >= A_PAIR || v_cand_m[j] > MG_PAIR)
                break;                  /* W2 bound (SS7.10) */
#else
            /* At v2.3 A_PAIR == A_MAX and MG_PAIR == MG_MAX, and
             * cand_insert only ever admits a bit with margin <= MG_MAX,
             * so BOTH tests are provably false for every j < ch_n <=
             * A_MAX: the bound admits exactly the ADMITTED weak pairs
             * and the hard budget bound is T_MAX comparisons instead.
             * The test is compiled out rather than left as dead code --
             * it comes straight back if either constant is tightened. */
#endif
            if ((uint8_t)(ch_isd(p) + ch_isd(j)) == sum_want) {
                r = try_trial(p, j);
                if (r) return r;
            }
        }
    return 0;
}

#endif /* CHECK_EN */

/* C1..C5 + R5..R8 of SS7.9: works entirely on the decoded bit array and
 * the <= A_MAX-entry candidate list -- no capture scan. */
static uint8_t chase(uint8_t *out)
{
    uint8_t p, j;
    /* C1: assemble payload' bytes from the bit array.  PP_LO is a whole
     * number of bytes (8*HT_LEN), and d_bits packs bit t at byte t>>3
     * bit t&7 (LSB first) while the wire byte is MSB first, so payload'
     * byte p is exactly the BIT REVERSAL of d_bits[HT_LEN + p] -- one
     * byte-wide rotate loop instead of a per-bit BGET with a 16-bit
     * index.  Same bytes, a third of the code, and it is what
     * decode_asm.s always did. */
    for (p = 0; p < NPP; p++) {
        uint8_t b = d_bits[HT_LEN + p], val = 0;
        for (j = 0; j < 8; j++) {
            val = (uint8_t)((val << 1) | (uint8_t)(b & 1));
            b = (uint8_t)(b >> 1);
        }
        d_pp[p] = val;
    }
    dec_info.n_weak = v_nweak;
    dec_info.n_tied = v_ntied;
#if !CHECK_EN
    /* legacy v2.0 geometry (dev/bench only): nothing to verify -- emit
     * after the R5 emit gate.  UNVERIFIED path, never in a shipped build. */
    if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
    for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
    return DEC_LEGACY;
#elif WIRE23
    {
        uint8_t res, skip3, skip5, q;
        ch_rbase = crc16(d_pp, ND_DATA);
        ch_comps = 0;
        /* RELAXATION B, the confidence FEED-FORWARD: a marker-suspect
         * frame keeps its per-byte-majority reference but is denied the
         * split enumeration, so it cannot also help itself to 9x the
         * per-comparison exposure.  (violations <= MK_TOL here -- R2
         * already refused anything worse.) */
        ch_cap = (dec_info.violations <= MK_SOFT) ? REF_MAX : 1;
        ref_build(ch_cap);
        dec_info.n_refs = ch_nref;
        dec_info.ref_split = (uint8_t)((ch_nhi > 1) + (ch_nlo > 1));
        /* R5: RETIRED in v2.3 (TIE_EMIT = 8*NPP+1 is unreachable), kept
         * live so the gate can be restored with one constant. */
        if (v_ntied > TIE_EMIT) {
            dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
        /* C2: direct accept -- v2.3 admits a SPLIT check block here too
         * (the emit-always directive); with a per-byte majority at both
         * positions this is bit-identical to the v2.2 single-ref test. */
        if (ch_match(ch_rbase) == 1) {
            dec_info.comps = ch_comps;
            for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
            return DEC_DIRECT;
        }
        /* C3: admission gates.  R6 now also asks the SS6.4 pool -- a
         * frame whose errors carry a LARGE apparent margin has
         * v_nweak == 0, and the DW bits are the only thing that gives
         * the chase anything to try, so R6 is now literally "the list is
         * empty".  That is EQUIVALENT to v_nweak == 0 && v_ndw == 0 --
         * cand_insert bails out only when the insertion index reaches
         * A_MAX, impossible while the list is empty, so the FIRST
         * admitted bit of either class always lands -- and it is a byte
         * cheaper on the target.  R7 is UNCHANGED: it is the WEAK pool's
         * completeness rule, and a DW entry can never sort ahead of a
         * weak one (margin > MG_MAX vs <= MG_MAX), so the guarantee it
         * rests on is untouched. */
        if (v_ncand == 0) { dec_info.cause = CAUSE_NOCAND;
                            dec_info.comps = ch_comps; return DEC_REFUSE; }
        if (v_nweak > A_MAX) { dec_info.cause = CAUSE_ADMIT;
                               dec_info.comps = ch_comps; return DEC_REFUSE; }
        ch_n = v_ncand;
        /* parity gate (still EXACT at 16 bits -- 0x11021 = (x+1)*0xF01F,
         * so every single-bit syndrome has odd parity, and a weight-w
         * data-only flip has syndrome parity w mod 2): skip a data-only
         * phase whose weight parity can match NO admitted reference.
         * With the usual single reference this is v2.2's `par` test. */
        skip3 = 1; skip5 = 1;
        for (q = 0; q < ch_nref; q++) {
            if (parity16((uint16_t)(ch_rbase ^ ch_ref[q]))) skip3 = 0;
            else skip5 = 0;
        }
        dec_info.chased = 1;
        /* C4: bounded, data-minimal, cheapest-first (SS7.4) */
        res = chase_singles(0);             /* phase 1: one check bit  */
        if (res == 1) goto accept;
        if (res == 2) goto budget;
        res = chase_pairs(0);               /* phase 2: two check bits */
        if (res == 1) goto accept;
        if (res == 2) goto budget;
        if (!skip3) {                       /* phase 3: one data bit   */
            res = chase_singles(1);
            if (res == 1) goto accept;
            if (res == 2) goto budget;
        }
        res = chase_pairs(1);               /* phase 4: data + check   */
        if (res == 1) goto accept;
        if (res == 2) goto budget;
        if (!skip5) {                       /* phase 5: two data bits  */
            res = chase_pairs(2);
            if (res == 1) goto accept;
            if (res == 2) goto budget;
        }
budget:
        dec_info.cause = CAUSE_CHASE;       /* R8: exhausted or capped */
        dec_info.comps = ch_comps;
        return DEC_REFUSE;
accept:
        dec_info.comps = ch_comps;
        for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
        return DEC_CHASE;
    }
#else /* superseded CRC8 geometries */
    {
        uint8_t R = 0, have_R, par;
        ch_rbase = crc8(d_pp, ND_DATA);
        have_R = maj_n(&d_pp[ND_DATA], &R);
        if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
        if (have_R && ch_rbase == R) {
            for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
            return DEC_DIRECT;
        }
        if (v_nweak == 0) { dec_info.cause = CAUSE_NOCAND; return DEC_REFUSE; }
        if (v_nweak > A_MAX) { dec_info.cause = CAUSE_ADMIT; return DEC_REFUSE; }
        ch_n = v_ncand;
        par = have_R ? parity8((uint8_t)(ch_rbase ^ R)) : 0xFF;
        dec_info.chased = 1;
        if (chase_singles(0)) goto accept;      /* phase 1 */
        if (chase_pairs(0)) goto accept;        /* phase 2 */
        if (!(have_R && par == 0) &&            /* phase 3 */
            chase_singles(1)) goto accept;
        if (chase_pairs(1)) goto accept;        /* phase 4 */
        if (!(have_R && par == 1) &&            /* phase 5 */
            chase_pairs(2)) goto accept;
        dec_info.cause = CAUSE_CHASE;           /* R8 */
        return DEC_REFUSE;
accept:
        for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
        return DEC_CHASE;
    }
#endif /* CHECK_EN / WIRE23 */
}

/* ---- top level ---------------------------------------------------------- */

uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
{
    uint16_t t;
    uint8_t viol = 0, r;
    /* zero every field (all initial values are 0 / DEC_REFUSE / CAUSE_NONE) */
    for (t = 0; t < sizeof(dec_info); t++)
        ((uint8_t *)&dec_info)[t] = 0;
    scan_cap = cap;
    scan_len = ncap;
    if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
    for (r = 0; r < 2; r++) refine();
    calibrate();
    decide_pass();
    dec_info.K = g_K;
    dec_info.tau = g_tau;
    dec_info.infeasible = d_infeas;
    dec_info.label_err = d_laberr;
    dec_info.n_seg = d_nseg;
    /* Marker mismatch count.  The markers are whole BYTES at both ends
     * (HT_LEN each), so this is 2*HT_LEN byte XORs and their popcounts
     * -- not NB known_bit() calls.  HTR[] is the marker template with
     * every byte BIT-REVERSED, which is exactly d_bits' packing (bit t
     * at byte t>>3, bit t&7, LSB first), so the XOR lines the two up
     * without reversing anything at run time.  Identical count to the
     * reference's per-bit loop, ~20k cycles cheaper. */
    for (t = 0; t < HT_LEN; t++) {
        viol = (uint8_t)(viol + popc8((uint8_t)(d_bits[t] ^ HTR[t])));
        viol = (uint8_t)(viol + popc8((uint8_t)(
                   d_bits[NBB - HT_LEN + t] ^ HTR[HT_LEN + t])));
    }
    dec_info.violations = viol;
    /* R2, RELAXATION B: a THRESHOLD over the N_MK known marker bits.
     * v2.2 refused on any single mismatch; v2.3 accepts up to MK_TOL and
     * feeds the count forward as confidence (chase() caps the reference
     * enumeration above MK_SOFT).  There is NO special case requiring
     * the first or last frame byte to validate -- owner directive, and
     * the threshold is the whole rule.  MK_TOL = 0 in the compat modes
     * reproduces v2.2's all-or-nothing rule exactly. */
    if (viol > MK_TOL)          { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
    if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
    if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
    dec_info.path = chase(out);                                      /* R5..R8 inside */
    return dec_info.path;
}

#endif /* !USE_ASM_DEC -- pipeline tail (decode_asm.s owns it otherwise) */

#if !USE_ASM_DEC
int16_t dec_eps_centi(void)
{
    /* SS11: eps = (K_NOM - K) / K, in centi-percent (x100 of a percent).
     * The subtraction MUST be s32: SDCC int is 16-bit and K may exceed
     * K_NOM (fast clock -> negative eps).  decode_asm.s keeps its own
     * copy (it already has the 32-bit divide). */
    return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
                     / (int32_t)dec_info.K);
}
#endif /* !USE_ASM_DEC (dec_eps_centi: decode_asm.s) */
