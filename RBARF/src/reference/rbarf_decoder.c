/*
 * ============================================================================
 *  rbarf_decoder.c -- the RBARF WS2812 frame decoder, written to be READ
 * ============================================================================
 *
 *  A $0.30 microcontroller (STM8S001J3, 8 KB flash, 1 KB RAM, no crystal)
 *  points a GPIO pin at an 800 kbit/s WS2812 wire and reads it in a tight
 *  assembly loop -- eight samples every 40 CPU cycles, one byte of RAM per
 *  loop, like a very cheap logic analyser.  What lands in memory is a
 *  smeared, warped, occasionally lying picture of the wire: the sampling
 *  clock is an RC oscillator that the datasheet only promises to +-7.5 %,
 *  some 0-bits leave no trace at all (their 375 ns pulse falls into the
 *  loop's bookkeeping dead zone), and adjacent 1-bits can merge into one
 *  long pulse.
 *
 *  This file is the second half of the job: RECONSTRUCTION.  It turns that
 *  picture back into exact bytes, and -- just as important -- says "no"
 *  when it cannot.  Frames are sent exactly once and never repeated, so a
 *  refusal costs a frame; a wrong frame accepted silently is far worse.
 *
 *  It is a readable equivalent of what ships in decode.c / decode_asm.s and
 *  of the normative Python reference recon/approaches/embedded_v2.py.  It is
 *  bit-exact against that reference on every corpus (reference/README.md
 *  says how the proof is run).  Vocabulary and stage names follow
 *  docs/RECONSTRUCTION_PAPER.md and recon/EMBEDDED_V2_SPEC.md.
 *
 *  ---------------------------------------------------------------------------
 *  THE PIPELINE, in the order a frame experiences it
 *  ---------------------------------------------------------------------------
 *    0  the capture buffer, and how it is linearized back into samples
 *    1  sample scan            -> interval-censored rise/fall brackets
 *    2  endpoint seed          -> first guess of (bit period, phase)
 *    3  residual refine        -> the same two numbers, fitted over all edges
 *    4  segmentation           -> gap accounting + the leading-ones reduction
 *    5  calibration            -> per-family pulse-width estimates (theta56)
 *    6  decision pass          -> bits, per-bit margins, candidate list
 *    7  check block            -> CRC-16 x3, per-byte majority, reference set
 *    8  CRC-guided chase       -> flip the suspect bits until the check clicks
 *    9  refusal ladder         -> R1..R8 and the output contract
 *
 *  ---------------------------------------------------------------------------
 *  THE SAME MEMORY AS THE SHIPPED DECODER -- WHAT THAT MEANS AND WHY
 *  ---------------------------------------------------------------------------
 *  The chip has 1 024 bytes of RAM, and the production firmware also has to
 *  fit an animation engine and a WS2812 output driver in there.  The decoder
 *  gets a little over a third of it.  Every table in this file therefore has
 *  the SAME element type, the SAME element count and the SAME meaning as its
 *  counterpart in decode.c / decode_asm.s, and each one carries the shipped
 *  symbol name in a trailing comment (`/`* _v_cand_t *`/` and so on) so a
 *  reader can hold this file beside the zero-page map at the top of
 *  decode_asm.s and check them off one by one.
 *
 *  Three consequences are visible in the code and are worth knowing up front:
 *
 *    * THE DECODED FRAME IS BIT-PACKED.  480 frame bits live in 60 bytes,
 *      not in a 480-byte array, and they are read and written through the
 *      two helpers `get_bit` / `set_bit` in section 0.  Two different bit
 *      orders are load-bearing and both are spelled out where they are used.
 *
 *    * STAGE SCRATCH IS OVERLAID.  Two unions (section 0) let a later stage
 *      re-use storage a finished stage owned.  The stages run strictly in
 *      sequence, so the sharing is safe -- and the banner over each union
 *      carries the LIFETIME TABLE that says which stage owns which member.
 *      Compile with -DRBARF_PARANOID to have every handover poison the
 *      storage it releases; that build must produce identical results, and
 *      that is exactly what makes the overlay a claim rather than a hope.
 *
 *    * WIDTHS ARE THE TARGET'S WIDTHS.  u8 / u16 / s16 / s32 where the
 *      shipped code uses them, the same fixed-point scales, the same
 *      truncating divisions, no float anywhere.  That is not decoration:
 *      it is what makes this file bit-exact rather than merely equivalent.
 *
 *  Measured with `sdcc -mstm8 --std-c99`, this file's decoder state is 364
 *  bytes of statics against decode.c's 356 at the same geometry.  The 8-byte
 *  difference is the runtime geometry cache below -- see WHAT STILL DIFFERS.
 *
 *  ---------------------------------------------------------------------------
 *  WHAT STILL DIFFERS FROM THE SHIPPED DECODER (the honesty list)
 *  ---------------------------------------------------------------------------
 *    * THE HOT PATHS ARE C, NOT HAND ASSEMBLY.  decode_asm.s hand-assembles
 *      the whole decoder for SIZE: it keeps its working set in the STM8's
 *      zero page (1-byte addressing), shares one 16x16 multiply, one 32/32
 *      divide and one map_raw core, and holds what a compiler would put on
 *      the stack in named zero-page bytes instead.  Counting those, the
 *      shipped decoder's statics come to 503 B against this file's 364 --
 *      but 139 B of that is precisely the stack-in-zero-page trade plus a
 *      32-byte suffix-min array the assembly uses and the C computes inline.
 *      Section 9's closing comment itemises the difference byte by byte.
 *    * CODE SIZE IS LARGER, and deliberately so: banners, named helpers and
 *      one function per idea instead of one shared arithmetic core.  8 444 B
 *      CODE + 118 B CONST, against decode.c's 7 318 + 140 and the shipped
 *      assembly's 5 414 + 28.
 *    * `nd` IS A RUNTIME PARAMETER (rbarf_decoder_configure), because the
 *      real-silicon corpus is the nd = 16 test geometry while production is
 *      nd = 48.  The shipped build resolves the geometry at COMPILE time
 *      (-DND_DATA) and its assembly reads the derived constants from flash;
 *      here they are 8 bytes of RAM.  That is the whole 364-vs-356 gap.
 *    * NO BUILD-TIME FEATURE FORKS.  v2.3 only: the superseded v2.1/v2.2
 *      CRC-8 geometries, their alias guard and the retired R5 emit gate are
 *      in decode.c behind `#if`s and are not reproduced here.
 *    * THE MARKER VIOLATION COUNT is still a per-bit loop over the template.
 *      The shipped decoder XORs the two marker byte-runs against a
 *      bit-reversed template and popcounts -- same number, less code, no
 *      RAM either way.
 *    * IT IS NOT PART OF THE FIRMWARE BUILD.  Nothing in the Makefile's
 *      shipping or verify path compiles it; `make ref-parity` is separate
 *      and additive, and the production images are untouched by it.
 *
 *  ---------------------------------------------------------------------------
 *  WHAT IS DELIBERATELY NOT HERE
 *  ---------------------------------------------------------------------------
 *    caploop.s      the 40-cycle 8-sample capture loop itself -- the "cheap
 *                   logic analyser".  Its timing is a property of the linked
 *                   binary (address-phase dependent), not of any C source.
 *    cap_arm.s      the armed front end that waits for the frame's first
 *                   rising edge and jumps into that loop at a pinned address.
 *    cap_code.s     the bring-up acquisition image that dumps raw captures
 *                   over UART; this file only consumes what it produced.
 *    rbarf_prod.c   the application: HSITRIMR auto-trim (each decode measures
 *                   the oscillator against the transmitter's crystal and
 *                   nudges the trim register back to centre), UART reporting.
 *    app/anim.c     the animation engine and the WS2812 output driver -- what
 *                   the decoded bytes are actually for.
 *
 *  ---------------------------------------------------------------------------
 *  THE WIRE (protocol v2.3, docs/PROTOCOL.md)
 *  ---------------------------------------------------------------------------
 *    frame = HEADER(3) || DATA(nd) || (CRC_HI CRC_LO) x3 || TRAILER(3)
 *    HEADER  = FF AA 65     FF = eight 1-bits, the unmissable start flag;
 *                           AA = 10101010, a bit-period ruler;
 *                           65 = an asymmetric byte-alignment marker.
 *    TRAILER = 9A 00 FF     9A = alignment marker; 00 = a worst-case-ZEROS
 *                           calibration probe at a KNOWN position; FF = the
 *                           mirrored end flag (so the last frame bit is a 1,
 *                           which section 2 relies on).
 *    check   = CRC-16/CCITT-FALSE over the DATA bytes only, poly 0x1021,
 *              init 0xFFFF, no reflection, xorout 0 -- written THREE times,
 *              because the check bytes ride the same lossy channel as the
 *              data.
 *    nd = 16  test / bring-up geometry: payload' 22 B, frame 28 B, 224 bits
 *             (this is the geometry of the real-silicon corpus)
 *    nd = 48  production: payload' 54 B, frame 60 B, 480 bits = 20 LEDs
 *
 *  "payload'" (payload-prime) is the project's name for DATA + check block:
 *  the part of the frame that is not marker.  Bit indices called `k` are
 *  payload'-relative; bit indices called `t` are frame-relative.
 *
 *  ---------------------------------------------------------------------------
 *  ARITHMETIC
 *  ---------------------------------------------------------------------------
 *  Integer only, and every quantity has a fixed format because the shipped
 *  decoder has no multiplier worth the name and no floats at all.  The unit
 *  of wire time is the TU ("time unit") = BIT / 512 = 1250/512 ns = 2.44 ns.
 *  Receiver time is measured in CPU cycles.  The clock fit is the pair
 *
 *      bit_period_q  (K)    Q11 TU per receiver cycle, u16, nominal 52429
 *      phase_offset  (tau)  TU, s16
 *
 *  and mapping receiver time to wire time is  y = ((t * K) >> 11) + tau.
 */

#include "rbarf_decoder.h"

#include <string.h>       /* memset / memcpy only -- no stdio in the decoder */

/* ==========================================================================
 *  CONSTANTS
 *  Everything the algorithm is parameterised by, in one place.  The three
 *  budget constants at the bottom are the ones a reviewer should read first.
 * ========================================================================== */

/* ---- the fitted sampler model (measured, not documented) ---------------- */
enum {
    LOOP_CY = 40,        /* one 8-sample loop = 40 CPU cycles = 2500 ns.
                          * The loop's own source comments claimed 37; the
                          * three missing cycles are memory-fetch stalls that
                          * only occur at certain flash addresses, which is
                          * why the production build PINS the loop's address. */
    SAMPLE_SLOTS = 8     /* samples per loop; the gaps between them are NOT
                          * equal -- see SLOT_OFFSET_CY. */
};

/* Cycle offset of each sample inside its loop.  The gaps are 4,5,4,4,4,6,5
 * cycles and then the loop's bookkeeping (store the byte, bump the pointer,
 * branch): that tail is the DEAD ZONE, and it is wider than a 0-bit's entire
 * high pulse.  A 0-bit landing in it leaves no high sample anywhere -- the
 * only evidence it existed is that the surrounding silence is too long. */
static const uint8_t SLOT_OFFSET_CY[SAMPLE_SLOTS] = {0, 4, 9, 13, 17, 21, 27, 32};

/* Data-dependent correction, in cycles, added AFTER a sample that read HIGH.
 * Reading a high level costs a different number of cycles than reading a low
 * one at some points in the loop (instruction prefetch), so the sampler
 * literally speeds up and slows down depending on what it sees.  Tiny, and
 * without it the model cannot reproduce reality. */
static const int8_t SLOT_BRANCH_CY[SAMPLE_SLOTS] = {0, -1, 0, 2, 0, 0, 0, 1};

/* ---- fixed-point scales ------------------------------------------------- */
enum {
    BIT_SH = 9,                 /* one WS2812 bit slot = 512 TU, a power of
                                 * two on purpose: /BIT is a shift. */
    BIT_U = 1 << BIT_SH,        /* 512 TU  = 1250 ns                        */
    BIT_H = BIT_U >> 1,         /* 256 TU  = half a bit slot (rounding)     */
    BIAS_U = BIT_U,             /* wire time of frame bit 0 is BIAS_U       */
    TAIL_U = 164,               /* 400 ns latch tail after the last bit     */
    KQ = 20 - BIT_SH,           /* = 11: K is Q11 TU/cycle                  */
    H0P = 154,                  /* nominal fall position of a 0-bit, TU     */
    H1P = 308                   /* nominal fall position of a 1-bit, TU     */
};
#define K_NOM 52429u            /* 62.5 TU/cycle * 2^11: the nominal clock  */

/* ---- lock window (relaxation A) ---------------------------------------- */
/* eps = (K_NOM - K)/K, so a LOW K means a FAST wire.  This window spans
 * eps +31 % .. -18 %: three times the distance from nominal of the widest
 * clock that was ever recoverable in the sweeps.  It is deliberately loose --
 * the 16-bit check is the safety net, so a distorted fit is PARSED and
 * CHECKED rather than refused. */
#define K_MIN 40000u
#define K_MAX 64000u

enum {
    MIN_PULSES = 8,       /* fewer than 8 pulses is not a frame            */
    FIRST_BR_CY = 4,      /* the very first rise has no preceding sample:
                           * bracket it 4 cycles (250 ns) wide             */
    LATCH_RUN = 200       /* 200 consecutive low samples = the WS2812 latch
                           * gap, i.e. the frame is over                   */
};

/* ---- decision / calibration thresholds (all TU unless noted) ----------- */
enum {
    INFEAS_U = 160,       /* a segment whose best hypothesis costs more than
                           * this is "infeasible": no leading-ones count
                           * explains the observed edge                    */
    LAB_MIN = 3,          /* fewer than 3 labelled examples: keep the prior */
    LAB_OUT = 246,        /* a marker-forced label further than this from
                           * either nominal boundary is an outlier         */
    H0_LO = 112, H0_HI = 192,   /* sanity box for the fitted 0-bit width   */
    H1_LO = 252, H1_HI = 376,   /* ... and for the 1-bit width             */
    SEP_LO = 112, SEP_HI = 196, /* ... and for their separation            */
    A_CAP = 15            /* leading-ones hypotheses per segment, capped.
                           * Real segments span at most 2 bit slots; only
                           * garbage reaches the cap, and the cap is part of
                           * the contract -- the reference truncates the
                           * hypothesis list at exactly the same place.
                           * A_CAP + 1 = 16 is also the element count of the
                           * shipped cost table (u16 d_costs[16]).         */
};

/* The "eps analog": a 64-bin fold histogram per razor family that measures
 * the residual clock error inside this one frame.  It is the single most
 * valuable mechanism in the pipeline (turning it off costs 7 of 54 real
 * captures), and none of its constants were touched since v1. */
enum {
    EPS_ZONE = 32, EPS_HIST = 64, EPS_GAP_MIN = 5, EPS_CLAMP56 = 24,
    EPS_CLEAR1 = 18, EPS_TOPM = 3, EPS_SLACK = 2, EPS_SLACK1 = 8
};

/* ---- refusal thresholds ------------------------------------------------- */
enum {
    MK_TOL = 12,          /* R2: refuse above 12 wrong bits of the 48 known
                           * marker bits.  v2.2 refused on ANY mismatch;
                           * v2.3 makes it a threshold and feeds the count
                           * forward as confidence (see MK_SOFT).          */
    MK_SOFT = 4,          /* above this the frame is "marker-suspect" and the
                           * chase is denied the split-reference
                           * enumeration: a suspect lock must not also help
                           * itself to 9x the per-comparison exposure.     */
    GATE_INFEAS = 24,     /* R3 threshold on infeasible segments           */
    GATE_LABERR = 6       /* R4 threshold on label disagreements           */
};

/* ---- the chase budget: the three numbers that bound the risk ------------ */
enum {
    MG_MAX = 8,           /* a payload' bit is WEAK at margin <= 8 TU
                           * (19.5 ns).  Margin is |cost(0) - cost(1)|.    */
    A_MAX = 11,           /* candidate-list capacity AND the R7 admission
                           * cap.  Bounds (a) how many suspect bits are
                           * remembered, (b) the flip-set enumeration at
                           * 1 + A_MAX + C(A_MAX,2) = 67 sets, and (c) the
                           * completeness rule: if more than A_MAX bits are
                           * weak the list no longer CONTAINS the ambiguity,
                           * and the honest move is to refuse.             */
    W_MAX = 2,            /* bits flipped per trial.  The error model is
                           * "one to three knife-edge bits", not random
                           * noise, so this is a knife-bit repair, not an
                           * error-correcting code.  W_MAX = 3 measured
                           * worse everywhere it was tried.                */
    T_MAX = 131,          /* RESIDUAL COMPARISONS per frame -- and this is
                           * THE false-accept bound.  Each comparison gives
                           * a wrong candidate one 2^-16 chance of passing,
                           * so a frame's whole exposure is
                           *   fa = 1 - (1 - 2^-16)^131 = 0.1997 %
                           * which is the 0.2 % target.  Note it counts
                           * comparisons, not flip sets: a trial whose check
                           * block has no majority tries several references
                           * and PAYS for each one.                        */
    REF_MAX = 9,          /* 3 HI candidates x 3 LO candidates: the whole
                           * cross product of a fully split check block.   */
    DW_OFF_MAX = 64       /* the Lever B geometry test is skipped past this
                           * offset, purely to keep its arithmetic inside
                           * s16 on an arbitrarily long merged run; it
                           * changes no answer (section 6 proves why).     */
};

#define CRC16_POLY 0x1021u
#define CRC16_INIT 0xFFFFu

/* ---- frame layout ------------------------------------------------------- */
enum { HDR_BYTES = 3, TRL_BYTES = 3, CHECK_BYTES = 6 };
static const uint8_t HEADER[HDR_BYTES]  = {0xFF, 0xAA, 0x65};
static const uint8_t TRAILER[TRL_BYTES] = {0x9A, 0x00, 0xFF};

/* payload' bit 0 is frame bit 24: the header is a whole number of bytes, and
 * section 7 leans on that (payload' byte p is one frame byte, not two). */
#define PAYLOAD_LO (8 * HDR_BYTES)

#define NPP_MAX     (RBARF_ND_MAX + CHECK_BYTES)                  /* 54 B  */
#define NB_MAX      (8 * (HDR_BYTES + NPP_MAX + TRL_BYTES))       /* 480   */
#define NBB_MAX     ((NB_MAX + 7) / 8)                            /* 60 B  */

/* CRC-16 syndrome basis, x^(16 + 8*i) mod 0x11021 for i = 0..47.
 *
 * Flipping the TOP bit of DATA byte p changes the CRC by x^(16 + 8*(nd-1-p))
 * -- eight bit positions further from the end of the message per byte, and
 * the message ends 16 zero bits short of the remainder register.  So ONE
 * flash table serves both geometries: the index runs BACKWARDS from the last
 * DATA byte, and nd = 16 uses entries 0..15 while nd = 48 uses 0..47.  The
 * other seven bits of a byte are seven `crc16_times_x` folds away, which is
 * why there is no modular reduction anywhere in section 8.
 *
 * 96 B of flash, 0 B of RAM.  -DRBARF_PARANOID recomputes every entry in
 * rbarf_decoder_configure() and refuses the configuration if one is wrong. */
static const uint16_t SYNDROME_X8[RBARF_ND_MAX] = {  /* XP8[48] */
    0x1021, 0x3331, 0x3730, 0x76B4, 0xAA51, 0x45A0, 0xB861, 0x47D3,
    0xEB23, 0x6F45, 0xD849, 0x0375, 0x4563, 0x7B61, 0xAEFC, 0xA824,
    0x10E2, 0xF031, 0xDE1F, 0x35B3, 0xD5F6, 0x6DD8, 0x650B, 0x3703,
    0x45B4, 0xAC61, 0x1566, 0x2494, 0xF0E6, 0x091F, 0x8E29, 0x5946,
    0x8DDC, 0x9C25, 0x6735, 0x2941, 0xF44B, 0xE49B, 0x26AA, 0xEEA4,
    0xB8E0, 0xC6D3, 0x6A8A, 0x47EC, 0xD423, 0xA8F9, 0xCDE2, 0xEAE1
};

/* ==========================================================================
 *  SMALL PORTABLE HELPERS
 *  The reference decoder is Python, whose >> floors and whose ints never
 *  wrap.  These two helpers say out loud where this file must behave the
 *  same way, so nothing rests on implementation-defined C.
 * ========================================================================== */

/* Arithmetic right shift with FLOOR semantics (>> in Python, and what the
 * STM8/x86 shift instructions do).  Used wherever a signed quantity is
 * divided by a power of two -- rounding must go the same way in all three
 * implementations or the bit lattice slips. */
static int32_t shr_floor(int32_t x, unsigned bits)
{
    if (x >= 0)
        return x >> bits;
    return -(int32_t)(((uint32_t)(-x) + (((uint32_t)1 << bits) - 1u)) >> bits);
}

static int32_t halve_floor(int32_t x) { return shr_floor(x, 1); }

/* Truncate to s16 the way the target's 16-bit registers do.  Only reachable
 * on garbage input (a capture that is not a frame at all); the reference
 * asserts there, the target wraps, and this spells the wrap out so that
 * "garbage in" still means "the same refusal out". */
static int16_t wrap_s16(int32_t x)
{
    uint16_t u = (uint16_t)((uint32_t)x & 0xFFFFu);
    return (u < 0x8000u) ? (int16_t)u : (int16_t)((int32_t)u - 0x10000L);
}

static int32_t abs32(int32_t x) { return x < 0 ? -x : x; }

/* ==========================================================================
 *  THE DECODER'S RAM -- BIT PACKING AND THE TWO STAGE OVERLAYS
 * ==========================================================================
 *
 *  WHY THIS SECTION EXISTS.  The STM8S001J3 has 1 024 bytes of RAM, and the
 *  shipping firmware spends the rest of it on the animation engine, the
 *  WS2812 output driver and 148 bytes of stack region.  The decoder's budget
 *  is a little over a third of the chip.  A byte-per-bit decoded frame alone
 *  would be 480 B -- almost half the RAM for something that fits in 60.
 *
 *  Two mechanisms buy the space back, and this file uses BOTH, exactly as
 *  the shipped decoder does.
 *
 *  ---------------------------------------------------------------------------
 *  (1) THE DECODED FRAME IS BIT-PACKED
 *  ---------------------------------------------------------------------------
 *  Frame bit t lives in byte t >> 3 at bit position t & 7 -- LSB FIRST inside
 *  the byte.  That looks backwards (the wire is MSB first) and it is chosen
 *  on purpose, because it makes two operations free:
 *
 *    * the MARKER TEMPLATE can be XORed against whole bytes: wire bit
 *      7-(t&7) of a template byte IS bit t&7 of its reversal, so the shipped
 *      decoder keeps ONE bit-reversed 6-byte template and compares the
 *      header and trailer with six XORs and six popcounts;
 *    * payload' byte p is EXACTLY THE BIT REVERSAL of frame byte
 *      HDR_BYTES + p (see assemble_payload in section 7) -- one byte-wide
 *      rotate loop, no per-bit indexing with a 16-bit index.
 *
 *  The payload' bytes themselves are stored MSB first, i.e. in wire order,
 *  because that is what the CRC eats; so payload'-relative bit k is
 *  pp_byte[k >> 3] bit 7 - (k & 7).  Two arrays, two bit orders, both
 *  load-bearing.  payload_flip() in section 8 is the only place the second
 *  one appears, and it says so.
 * ========================================================================== */

/* Read frame bit t out of a packed bit array.  See the banner: LSB first. */
static uint8_t get_bit(const uint8_t *packed, uint16_t t)
{
    return (uint8_t)((packed[t >> 3] >> (t & 7u)) & 1u);
}

/* Set frame bit t in a packed bit array.  There is no clear_bit: the array
 * is zeroed once per decode and only ever has 1-bits written into it. */
static void set_bit(uint8_t *packed, uint16_t t)
{
    packed[t >> 3] |= (uint8_t)(1u << (t & 7u));
}

/* ==========================================================================
 *  (2) STAGE SCRATCH IS OVERLAID
 * ==========================================================================
 *
 *  THE ARGUMENT.  The pipeline stages run strictly in sequence and each one
 *  runs to completion before the next begins.  So a stage's scratch is DEAD
 *  the moment it returns, and the storage can be handed to a later stage.
 *  This is not a micro-optimisation: the two overlays below are 160 bytes of
 *  a 364-byte budget, and without them the decoder does not fit beside the
 *  animation engine at all.
 *
 *  THE RULE.  A stage may only touch the union member it OWNS, and it must
 *  initialise that member itself rather than inherit anything.  Both
 *  conditions are checked, not assumed: -DRBARF_PARANOID poisons each union
 *  with 0xA5 at every handover, and a paranoid build that produced different
 *  answers would mean some stage was reading a member it does not own.
 *  (The parity harness is run both ways.)
 *
 *  ---------------------------------------------------------------------------
 *  OVERLAY 1 -- `scratch`, 128 B  (decode.c's `ov`, linker symbol `_ov`)
 *  ---------------------------------------------------------------------------
 *    stage                       member                       bytes
 *    5 calibration               fold_hist[2][64]             128
 *    6 decision pass            \ frame.bit[NBB]               60  (nd = 48)
 *    7 check block, 8 chase     / frame.payload[NPP]           54
 *
 *  WHY IT IS SAFE.  estimate_family_shift() is the LAST reader of the fold
 *  histograms and it runs inside calibrate(); decision_pass() is the FIRST
 *  writer of the packed frame and it zeroes every byte it will use;
 *  assemble_payload() is the first writer of the payload' bytes and writes
 *  all of them.  60 + 54 = 114 <= 128, at both geometries.
 *
 *  ---------------------------------------------------------------------------
 *  OVERLAY 2 -- `dc`, 32 B  (decode.c's `d_costs`, linker symbol `_d_costs`)
 *  ---------------------------------------------------------------------------
 *    stage                       member                       bytes
 *    6 decision pass             hypothesis_cost[16]            32
 *    7 check block, 8 chase     \ refs.value[9]                 18
 *                               / refs.hi[3] + refs.lo[3]        6
 *
 *  WHY IT IS SAFE.  hypothesis_cost is per-SEGMENT scratch, rewritten from
 *  index 0 for every segment and dead when decision_pass() returns; the
 *  chase never builds a hypothesis table.  18 + 6 = 24 <= 32.
 * ========================================================================== */

union stage_scratch {
    /* stage 5 owns this: two 64-bin fold histograms, one per razor family */
    uint8_t fold_hist[2][EPS_HIST];              /* c_hist                 */
    /* stages 6, 7 and 8 own this */
    struct {
        uint8_t bit[NBB_MAX];                    /* d_bits, BIT-PACKED     */
        uint8_t payload[NPP_MAX];                /* d_pp, payload' bytes   */
    } frame;
};
static union stage_scratch scratch;              /* _ov                    */

union decision_chase_scratch {
    /* stage 6 owns this: the per-segment hypothesis costs */
    uint16_t hypothesis_cost[A_CAP + 1];         /* _d_costs               */
    /* stages 7 and 8 own this: the admitted reference set and the ranked
     * candidate values of the two check-byte positions */
    struct {
        uint16_t value[REF_MAX];                 /* ch_ref                 */
        uint8_t  hi[3];                          /* ch_val[0..2]           */
        uint8_t  lo[3];                          /* ch_val[3..5]           */
    } refs;
};
static union decision_chase_scratch dc;

/* Names for the overlay members, so the stages read as if each owned a plain
 * array.  Every one of these is an ALIAS -- the banner above says of what. */
#define fold_hist        scratch.fold_hist
#define frame_bit        scratch.frame.bit
#define pp_byte          scratch.frame.payload
#define hypothesis_cost  dc.hypothesis_cost
#define reference        dc.refs.value
#define hi_values        dc.refs.hi
#define lo_values        dc.refs.lo

/* Hand a union on to its next owner.  A no-op in a normal build; in a
 * paranoid build it destroys the released contents, so that any stage still
 * reading them would give a different (and visibly wrong) answer. */
#ifdef RBARF_PARANOID
#define STAGE_HANDOVER(u)  memset(&(u), 0xA5, sizeof(u))
#else
#define STAGE_HANDOVER(u)  ((void)0)
#endif

/* ==========================================================================
 *  THE DIAGNOSTIC REPORT -- the shipped 23-byte dec_info, field for field
 * ==========================================================================
 *
 *  The shipped decoder accumulates its telemetry in ONE 23-byte struct that
 *  the assembly owns in the zero page (`_dec_info: .ds 23`, and decode.c
 *  static-asserts sizeof(dec_info_t) == 23 against that reservation).  Every
 *  field below is that struct's field, in that struct's order and width; the
 *  public rbarf_result is filled from it at the end of rbarf_decode(), which
 *  is also where the field-by-field parity comparison gets its numbers.
 *
 *  Two fields are here for completeness rather than use, and both say why.
 * ========================================================================== */

static struct dec_report {                  /* _dec_info                    */
    uint8_t  path;         /* +0  enum rbarf_path of the last decode        */
    uint8_t  cause;        /* +1  enum rbarf_cause (RBARF_OK on an emit)    */
    uint8_t  trials;       /* +2  chase flip sets residual-tested (<= 67)   */
    uint8_t  alias_cmp;    /* +3  alias-guard compares -- ALWAYS 0 in v2.3.
                            *     ord(x) mod 0x11021 = 32767, so every
                            *     data-bit syndrome in a <= 432-bit payload'
                            *     is distinct and the CRC-8 era's guard is
                            *     provably inert.  The field stays so the
                            *     struct is the shipped 23 bytes and so the
                            *     compat builds keep their reporting slot.  */
    uint8_t  chased;       /* +4  1 if the trial loop was entered           */
    uint16_t n_weak;       /* +5  payload' bits with margin <= MG_MAX       */
    uint16_t n_tied;       /* +7  payload' bits with margin == 0            */
    uint16_t bit_period_q; /* +9  K, Q11 TU/cycle                           */
    int16_t  phase_offset; /* +11 tau, TU                                   */
    uint8_t  violations;   /* +13 marker bits decoded against the template  */
    uint16_t infeasible;   /* +14 segments with hinge cost > INFEAS_U       */
    uint16_t label_error;  /* +16 forced-label disagreements                */
    uint16_t n_segments;   /* +18 segments streamed in the decision pass    */
    uint8_t  comps;        /* +20 residual comparisons used (<= T_MAX)      */
    uint8_t  n_refs;       /* +21 references in the base set (1..REF_MAX)   */
    uint8_t  ref_split;    /* +22 check-byte positions with NO majority     */
} rep;

/* SDCC packs STM8 structs at alignment 1, so the reservation the assembly
 * makes is exactly sizeof(struct dec_report) there.  A host ABI that aligns
 * u16 pads the same fields to 26; both are accepted, anything else means a
 * field was added, removed or re-widened. */
typedef char dec_report_layout_check[
    (sizeof(struct dec_report) == 23 || sizeof(struct dec_report) == 26)
    ? 1 : -1];
#ifdef __SDCC
typedef char dec_report_is_23_bytes[(sizeof(struct dec_report) == 23) ? 1 : -1];
#endif

/* ==========================================================================
 *  SECTION 0 -- THE CAPTURE BUFFER, AND LINEARIZING IT
 * ==========================================================================
 *
 *  The sampling loop reads the pin eight times and stores ONE byte per loop.
 *  Six of the eight samples fit in that byte; the last two are still in
 *  registers when the byte is written, so they are carried into the NEXT
 *  byte's two top bits.  The layout of capture byte i is therefore
 *
 *      bit 7 : slot 6 of loop i-1        bit 5..0 : slots 0..5 of loop i
 *      bit 6 : slot 7 of loop i-1
 *
 *  Byte 0's two top bits are garbage (there is no loop -1) and the last
 *  loop's slots 6 and 7 are simply lost.  "Linearizing" is undoing that
 *  interleave: walking (loop, slot) in chronological order and pulling each
 *  level out of whichever byte holds it.  This decoder does it inline while
 *  scanning -- there is no intermediate sample array, on the target or here,
 *  and there could not be: 640 loops is 5 120 samples and the chip has 1 KB.
 *
 *  ONE BIT = ONE SAMPLE WORD POSITION -> TIME.  Sample (i, s) was taken at
 *
 *      t = i * 40 + SLOT_OFFSET_CY[s] + branch_sum
 *
 *  receiver cycles, where branch_sum accumulates SLOT_BRANCH_CY for every
 *  sample so far that read HIGH.  That expression is the entire instrument
 *  model, and it was FITTED to 54 real captures (~276 000 samples, 99.96 %
 *  agreement) rather than taken from the loop's documentation, which was
 *  wrong about the loop length, silent about the data dependence, and
 *  silent about the flash-address dependence.
 * ========================================================================== */

/* ==========================================================================
 *  SECTION 1 -- SAMPLE SCAN: PULSES AS INTERVAL-CENSORED EDGE BRACKETS
 * ==========================================================================
 *
 *  A sample never says "the edge was at time T".  It says "the line was high
 *  when I looked at T".  An edge is only ever known to lie BETWEEN two
 *  consecutive looks, and with samples this sparse a midpoint is a guess
 *  dressed up as a fact.  So the scanner reports, for each high pulse, two
 *  BRACKETS rather than two times:
 *
 *      rise_lo, rise_hi   the last low sample before the pulse and the first
 *                         high sample of it: the rise is in (rise_lo, rise_hi]
 *      fall_lo, fall_hi   the last high sample of the pulse and the first low
 *                         sample after it: the fall is in (fall_lo, fall_hi]
 *
 *  The two members of each bracket are ADJACENT in the sample comb, so no
 *  sample lies strictly between them -- a fact section 6 leans on hard.
 *
 *  It also reports the SAMPLE-SLOT FAMILY: the slot index (0..7) of the
 *  pulse's last high sample.  Because the intra-loop gaps differ, a pulse
 *  measured across the wide gap after slot 5 is systematically distorted
 *  differently from one measured after slot 2.  Families 5 and 6 -- the two
 *  widest gaps, hence the "razor" families -- get their own width
 *  calibration in section 5.
 *
 *  MEMORY NOTE.  The pulse is published in ONE shared record rather than
 *  copied into a caller-supplied struct: the shipped decoder publishes it in
 *  five globals (_scan_ra, _scan_rb, _scan_fa, _scan_fb, _scan_sfa) so the
 *  hot call carries no arguments at all.  These are the same nine bytes with
 *  a name on them, and there is exactly one pulse alive at any moment.
 * ========================================================================== */

struct pulse {
    uint16_t rise_lo;            /* _scan_ra   rise is in (rise_lo, rise_hi] */
    uint16_t rise_hi;            /* _scan_rb   ... in receiver cycles        */
    uint16_t fall_lo;            /* _scan_fa   fall is in (fall_lo, fall_hi] */
    uint16_t fall_hi;            /* _scan_fb                                 */
    uint8_t  family;             /* _scan_sfa  slot of the last HIGH sample  */
};

static struct pulse edge;        /* the pulse the scanner just delivered     */

/* The scanner's own state.  Field for field this is decode.c's `ps` struct
 * plus its two capture globals; the trailing comments give the assembly's
 * zero-page names (`p_*`, from the size-focused scanner in decode_asm.s). */
static struct sample_scanner {
    const uint8_t *cap;          /* _scan_cap  the capture buffer            */
    uint16_t cap_len;            /* _scan_len  bytes = sampling loops        */

    uint16_t loop_index;         /* p_i   which capture byte / sampling loop */
    uint16_t loop_base_cy;       /* p_tb  loop_index * LOOP_CY, incremental  */
    int16_t  branch_sum_cy;      /* p_ws  running SLOT_BRANCH_CY correction  */
    uint16_t prev_sample_cy;     /* p_tp  time of the previous sample ...    */
    uint16_t low_run;            /* p_lr  consecutive low samples            */

    uint16_t rise_lo, rise_hi;   /* the pulse under construction: the        */
    uint16_t fall_lo;            /* shipped scanner keeps these in the same  */
                                 /* three words it will publish from         */
    uint8_t  slot;               /* p_s   which of the 8 samples in the loop */
    uint8_t  family;             /* the last high sample's slot              */
    bool     have_prev;          /* p_hp  ... once there IS a previous one   */
    bool     in_pulse;           /* p_ip  currently inside a high run        */
    bool     seen_high;          /* p_se  any high sample yet (arms latch)   */
    bool     finished;           /* p_dn  source exhausted                   */
} scan;

/* bool is one byte in C99 (_Bool) and one byte in SDCC, so every flag above
 * costs exactly the u8 the shipped decoder spends on it. */

static void scan_open(const uint8_t *cap, uint16_t cap_len)
{
    memset(&scan, 0, sizeof(scan));
    scan.cap = cap;
    scan.cap_len = cap_len;
}

/* Level of sample (loop_index, slot), pulled out of the interleaved layout.
 * Returns false when this slot was never stored (slots 6 and 7 of the last
 * loop live in a byte that does not exist). */
static bool scan_level(uint16_t loop_index, uint8_t slot, uint8_t *level)
{
    if (slot < 6) {
        *level = (uint8_t)((scan.cap[loop_index] >> (5 - slot)) & 1u);
        return true;
    }
    if ((uint16_t)(loop_index + 1u) >= scan.cap_len)
        return false;                          /* the boundary samples are lost */
    *level = (uint8_t)((scan.cap[loop_index + 1u] >> (7 - (slot - 6))) & 1u);
    return true;
}

/*
 * Deliver the next high pulse into `edge`, or return false at the end of the
 * frame.
 *
 * The frame ends at the LATCH: 200 consecutive low samples, which on the
 * wire is the WS2812 reset gap.  A capture that ends while still high (the
 * buffer ran out mid-pulse) yields that final pulse with a synthetic fall
 * bracket, so a truncated capture degrades into a bad fit rather than a
 * missing pulse.
 */
static bool scan_next_pulse(void)
{
    while (!scan.finished) {
        uint8_t level;
        uint16_t t;
        uint8_t slot = scan.slot;

        if (scan.loop_index >= scan.cap_len)
            break;
        if (!scan_level(scan.loop_index, slot, &level)) {
            scan.loop_index++;                 /* skip the lost slots 6,7 */
            scan.slot = 0;
            scan.loop_base_cy = (uint16_t)(scan.loop_base_cy + LOOP_CY);
            continue;
        }

        /* the instrument model of section 0, in one line */
        t = (uint16_t)(scan.loop_base_cy + SLOT_OFFSET_CY[slot]
                       + scan.branch_sum_cy);

        if (slot == SAMPLE_SLOTS - 1) {
            scan.slot = 0;
            scan.loop_index++;
            scan.loop_base_cy = (uint16_t)(scan.loop_base_cy + LOOP_CY);
        } else {
            scan.slot = (uint8_t)(slot + 1);
        }

        if (level) {
            scan.branch_sum_cy = (int16_t)(scan.branch_sum_cy
                                           + SLOT_BRANCH_CY[slot]);
            if (!scan.in_pulse) {
                scan.in_pulse = true;
                /* rise bracket: the previous sample, or a synthetic 4-cycle
                 * bracket if this is the very first sample of the capture */
                scan.rise_lo = scan.have_prev
                    ? scan.prev_sample_cy
                    : (uint16_t)(t >= FIRST_BR_CY ? t - FIRST_BR_CY : 0);
                scan.rise_hi = t;
            }
            scan.fall_lo = t;                  /* keeps moving while high  */
            scan.family = slot;
            scan.low_run = 0;
            scan.seen_high = true;
        } else {
            if (scan.in_pulse) {
                scan.in_pulse = false;
                edge.rise_lo = scan.rise_lo;
                edge.rise_hi = scan.rise_hi;
                edge.fall_lo = scan.fall_lo;
                edge.fall_hi = t;              /* first low sample: closes it */
                edge.family = scan.family;
                scan.prev_sample_cy = t;
                scan.have_prev = true;
                scan.low_run = 1;
                return true;
            }
            scan.low_run++;
            if (scan.seen_high && scan.low_run >= LATCH_RUN) {
                scan.finished = true;          /* the latch: frame over */
                break;
            }
        }
        scan.prev_sample_cy = t;
        scan.have_prev = true;
    }

    if (scan.in_pulse) {                       /* capture ended still high */
        scan.in_pulse = false;
        edge.rise_lo = scan.rise_lo;
        edge.rise_hi = scan.rise_hi;
        edge.fall_lo = scan.fall_lo;
        edge.fall_hi = (uint16_t)(scan.fall_lo + FIRST_BR_CY);
        edge.family = scan.family;
        scan.finished = true;
        return true;
    }
    scan.finished = true;
    return false;
}

/* midpoint of a bracket -- the ONLY place a bracket is collapsed to a single
 * time, and only ever for the two endpoint anchors of section 2 and for
 * dating a rise against the bit lattice */
static uint16_t bracket_mid(uint16_t lo, uint16_t hi)
{
    return (uint16_t)((lo + hi) >> 1);
}

/* ==========================================================================
 *  RUNTIME GEOMETRY
 *  nd is a runtime parameter, not a macro: the real-silicon corpus is the
 *  nd = 16 test geometry while production is nd = 48, and this file has to
 *  decode both without being rebuilt.
 *
 *  THESE EIGHT BYTES ARE THE ONE PLACE THIS FILE SPENDS RAM THE SHIPPED
 *  DECODER DOES NOT.  decode.c gets the geometry from -DND_DATA at compile
 *  time and decode_asm.s reads the derived constants out of flash (g_NB,
 *  g_ND8, g_PPHI, g_PPB, g_PPE, g_TRB).  Runtime nd is the promise this
 *  file makes instead, and eight bytes is its whole price.
 * ========================================================================== */

static struct geometry {
    uint16_t data_bits;       /* 8 * nd: payload' bits below this are DATA */
    uint16_t frame_bits;      /* the whole frame, markers included         */
    uint16_t payload_hi;      /* one past the last payload' frame bit      */
    uint8_t  data_bytes;      /* nd                                        */
    uint8_t  payload_bytes;   /* nd + 6 (the payload', DATA + check block) */
} geom;

/* bytes of `frame_bit` this geometry uses (the shipped decoder's NBB) */
static uint16_t frame_bytes(void)
{
    return (uint16_t)((geom.frame_bits + 7u) >> 3);
}

/* Multiply a CRC-16 remainder by x, modulo the generator polynomial. */
static uint16_t crc16_times_x(uint16_t r)
{
    return (uint16_t)((r & 0x8000u) ? (uint16_t)((uint16_t)(r << 1) ^ CRC16_POLY)
                                    : (uint16_t)(r << 1));
}

bool rbarf_decoder_configure(uint8_t nd)
{
    if (nd == 0 || nd > RBARF_ND_MAX)
        return false;

    geom.data_bytes = nd;
    geom.payload_bytes = (uint8_t)(nd + CHECK_BYTES);
    geom.data_bits = (uint16_t)(8u * nd);
    geom.frame_bits = (uint16_t)(8u * (HDR_BYTES + geom.payload_bytes
                                       + TRL_BYTES));
    geom.payload_hi = (uint16_t)(PAYLOAD_LO + 8u * geom.payload_bytes);

#ifdef RBARF_PARANOID
    /* Re-derive the flash syndrome basis and refuse if a byte of it drifted.
     * r walks x^16, x^24, x^32 ... which is what SYNDROME_X8[0..47] holds. */
    {
        uint16_t r = 1u;
        int i, b;
        for (i = 0; i < 16; i++)
            r = crc16_times_x(r);
        for (i = 0; i < RBARF_ND_MAX; i++) {
            if (SYNDROME_X8[i] != r)
                return false;
            for (b = 0; b < 8; b++)
                r = crc16_times_x(r);
        }
    }
#endif
    return true;
}

/* wire time (TU) of the start of frame bit t */
static uint32_t bit_base_tu(uint16_t t)
{
    return (uint32_t)BIAS_U + (uint32_t)t * BIT_U;
}

/* wire time (TU) one latch-tail past the end of the frame */
static uint32_t frame_end_tu(void)
{
    return bit_base_tu(geom.frame_bits) + TAIL_U;
}

/*
 * The marker template.  Returns 0 or 1 for a bit whose value is known a
 * priori (the header and trailer), and -1 for a payload' bit.  Everything
 * that constrains the decode -- the seed's known frame length, the
 * calibration's labelled examples, the leading-ones bounds and the R2 gate
 * -- comes out of this one function.
 */
static int8_t known_frame_bit(uint16_t t)
{
    if (t < PAYLOAD_LO)
        return (int8_t)((HEADER[t >> 3] >> (7 - (t & 7u))) & 1u);
    if (t >= (uint16_t)(geom.frame_bits - 8u * TRL_BYTES)) {
        uint16_t u = (uint16_t)(t - (geom.frame_bits - 8u * TRL_BYTES));
        return (int8_t)((TRAILER[u >> 3] >> (7 - (u & 7u))) & 1u);
    }
    return -1;
}

/* ==========================================================================
 *  SECTION 2 -- ENDPOINT SEED OF THE TWO-PARAMETER CLOCK FIT
 * ==========================================================================
 *
 *  "How fast is my clock really, relative to the transmitter?" must be
 *  answered from THIS frame alone: frames are rare and never repeated, so
 *  there is no previous frame to calibrate against.
 *
 *  The decoder does not TRACK, it FITS.  A software PLL was built and
 *  measured WORSE: within a single frame this oscillator wanders by about
 *  0.001 %, so it is effectively constant, and a tracker with nothing real
 *  to track ends up chasing noise.  Instead two numbers are fitted for the
 *  whole frame:
 *
 *      bit_period_q (K)   how much wire time one receiver cycle buys
 *      phase_offset (tau) where the frame starts in wire time
 *
 *  The seed comes from the two ENDPOINTS, and this is the quiet masterstroke
 *  of the protocol design: the number of bit slots between the first rise and
 *  the last fall is KNOWN EXACTLY.  The frame's first bit is a 1 (HEADER
 *  starts FF) and its last bit is a 1 (TRAILER ends FF), so
 *
 *      wire span = (frame_bits - 1) * BIT_U + H1P   TU, exactly.
 *
 *  Dividing that by the measured receiver span converts "where is each bit?"
 *  from dead reckoning into interpolation between two anchors -- dead
 *  reckoning accumulates error, interpolation does not.  It also pins K to
 *  about 0.1 %, which excludes the one-bit-slip aliases a priori, which is
 *  why no search grid is needed anywhere in this decoder.
 * ========================================================================== */

static struct clock_fit {
    uint16_t bit_period_q;    /* _g_K    K:   Q11 TU per receiver cycle    */
    int16_t  phase_offset;    /* _g_tau  tau: TU                          */
} clk;

/* Map receiver cycles to wire TU.  The product t*K is the one place a 32-bit
 * intermediate is unavoidable (27.5k * 64000 < 2^31), and the shipped
 * decoder spends a shared 16x16->32 multiply routine on exactly this line. */
static int32_t map_to_wire_tu(uint16_t t)
{
    return (int32_t)(((uint32_t)t * clk.bit_period_q) >> KQ) + clk.phase_offset;
}

static bool clock_seed(const uint8_t *cap, uint16_t cap_len)
{
    uint16_t n_pulses = 0;
    uint16_t first_rise_mid = 0, last_fall_mid = 0;
    uint32_t wire_span_tu, k;
    int32_t phase;

    scan_open(cap, cap_len);
    while (scan_next_pulse()) {
        if (n_pulses == 0)
            first_rise_mid = bracket_mid(edge.rise_lo, edge.rise_hi);
        last_fall_mid = bracket_mid(edge.fall_lo, edge.fall_hi);
        n_pulses++;
    }
    /* R1: not enough of a frame to fit anything to */
    if (n_pulses < MIN_PULSES || last_fall_mid <= first_rise_mid)
        return false;

    wire_span_tu = (uint32_t)(geom.frame_bits - 1u) * BIT_U + H1P;
    k = (wire_span_tu << KQ) / (uint32_t)(last_fall_mid - first_rise_mid);
    if (k < K_MIN || k > K_MAX)
        return false;                          /* R1: clock off scale */
    clk.bit_period_q = (uint16_t)k;

    /* tau places frame bit 0 at BIAS_U.  A late-starting, short-span capture
     * can push it outside s16, where the target would wrap silently; refusing
     * here keeps all three implementations identical by construction. */
    phase = (int32_t)BIAS_U
            - (int32_t)(((uint32_t)first_rise_mid * clk.bit_period_q) >> KQ);
    if (phase < -32768L || phase > 32767L)
        return false;                          /* R1 */
    clk.phase_offset = (int16_t)phase;
    return true;
}

/* ==========================================================================
 *  SECTION 3 -- REFINE THE FIT OVER ALL EDGES
 * ==========================================================================
 *
 *  The seed used two edges.  This stage uses every rise in the frame, and it
 *  is a least-squares fit done with integers and no division per sample:
 *
 *    * map every rise to wire time y;
 *    * its RESIDUAL is the signed distance from y to the nearest bit-slot
 *      boundary -- the bit lattice is a grid of 512 TU, so this is a
 *      rounding, not a threshold;
 *    * average the residuals over the first half of the frame and over the
 *      second half.
 *
 *  If the clock estimate were perfect both means would be zero.  A tilt
 *  between them is a bit-period error and a common offset is a phase error,
 *  so the two-half means give the two corrections directly:
 *
 *      dK   = K * (mean_late - mean_early) / (pos_late - pos_early)
 *      dtau = -mean + (mean_late - mean_early) * (pos - tau) / (pos_late - pos_early)
 *
 *  That is the closed-form least-squares slope/intercept update for a
 *  two-group summary, which is all the precision the data supports and about
 *  four divisions instead of one per edge.  Run twice (the caller does), it
 *  converges; there is no feedback loop and no per-bit tracking anywhere.
 *
 *  MEMORY NOTE.  Six 32-bit accumulators live here, and this is the deepest
 *  32-bit arithmetic in the decoder.  They are LOCALS -- the shipped assembly
 *  keeps them in named zero-page bytes instead (r_lo, r_hi, r_de, r_dy, ...,
 *  45 B) and then hands that same storage to the calibration and the chase,
 *  which is the trade the honesty list at the top of the file describes.
 * ========================================================================== */

static void clock_refine(const uint8_t *cap, uint16_t cap_len)
{
    const uint32_t y_end = frame_end_tu();
    const uint32_t y_mid = bit_base_tu((uint16_t)(geom.frame_bits / 2u));
    uint16_t n_early = 0, n_late = 0;
    int32_t sum_err_early = 0, sum_err_late = 0;      /* s32 by contract */
    uint32_t sum_pos_early = 0, sum_pos_late = 0;     /* u32 by contract */
    int32_t mean_err_early, mean_err_late, mean_err;
    uint32_t mean_pos_early, mean_pos_late, mean_pos;
    int32_t tilt, span, d_period, d_phase, period2;

    scan_open(cap, cap_len);
    while (scan_next_pulse()) {
        int32_t y = map_to_wire_tu(bracket_mid(edge.rise_lo, edge.rise_hi));
        uint32_t slot_index;
        int16_t residual;

        if (y < 0)
            y = 0;
        if ((uint32_t)y > y_end)
            break;                             /* past the frame: stop */
        slot_index = ((uint32_t)y + BIT_H) >> BIT_SH;   /* nearest lattice slot */
        residual = (int16_t)(y - (int32_t)(slot_index << BIT_SH));
        if ((uint32_t)y < y_mid) {
            n_early++;
            sum_err_early += residual;
            sum_pos_early += (uint32_t)y;
        } else {
            n_late++;
            sum_err_late += residual;
            sum_pos_late += (uint32_t)y;
        }
    }
    if (n_early < 2 || n_late < 2)
        return;                                /* not enough to fit: keep the seed */

    /* Every division here truncates toward zero, exactly as on the target. */
    mean_err_early = sum_err_early / (int32_t)n_early;
    mean_err_late = sum_err_late / (int32_t)n_late;
    mean_pos_early = sum_pos_early / n_early;
    mean_pos_late = sum_pos_late / n_late;

    tilt = mean_err_late - mean_err_early;
    span = (int32_t)mean_pos_late - (int32_t)mean_pos_early;
    if (span <= 0)
        return;

    d_period = ((int32_t)clk.bit_period_q * tilt) / span;
    mean_err = (sum_err_early + sum_err_late) / (int32_t)(n_early + n_late);
    mean_pos = (sum_pos_early + sum_pos_late) / (uint32_t)(n_early + n_late);
    d_phase = -mean_err + (tilt * ((int32_t)mean_pos - clk.phase_offset)) / span;

    period2 = (int32_t)clk.bit_period_q - d_period;
    if (period2 < (int32_t)K_MIN || period2 > (int32_t)K_MAX)
        return;                                /* the correction left the window */
    clk.bit_period_q = (uint16_t)period2;
    clk.phase_offset = wrap_s16((int32_t)clk.phase_offset + d_phase);
}

/* ==========================================================================
 *  SECTION 4 -- SEGMENTATION, GAP ACCOUNTING, AND THE LEADING-ONES REDUCTION
 * ==========================================================================
 *
 *  With the clock locked, every visible pulse's rise pins it to a bit slot:
 *  every WS2812 bit begins with a rising edge on an exact 1.25 us grid, so
 *  the slot index is a ROUNDING of the mapped rise time, not a fragile
 *  nanosecond threshold.
 *
 *  Then the silences get audited.  SILENCE IS DATA:
 *
 *      a gap of one bit slot  -> normal
 *      a gap of two slots     -> exactly one INVISIBLE 0-bit hid in it
 *      a gap of three slots   -> two invisible 0-bits ... and so on
 *
 *  and the same logic runs in reverse for MERGED pulses: a high run spanning
 *  two bit slots must be two 1-bits whose separating 500 ns low gap fell into
 *  the sampler's dead zone.
 *
 *  A SEGMENT is what comes out: one pulse, the bit slot it starts at
 *  (first_bit), the slot where the next pulse starts (end_bit), its fall
 *  bracket expressed relative to its own bit lattice, and its family.  The
 *  bits between first_bit and end_bit belong to this segment, and here is
 *  the elegant simplification that fell out of the design synthesis:
 *
 *      for deciding the actual bytes, a segment's only real question is
 *      "HOW MANY 1-BITS DOES IT START WITH?"
 *
 *  The different ways a long pulse could split into 1-bits and swallowed
 *  0-bits produce identical bit patterns -- a leading run of `a` ones
 *  followed by zeros.  Whole categories of ambiguity collapse into one small
 *  integer per segment, and the decision problem becomes: pick `a`.
 * ========================================================================== */

/* Nine bytes, and the shipped assembly reserves exactly nine for it
 * (`_g_sg: .ds 9  ; k0(2) k1(2) u(2) v(2) fam(1)`).  decode.c passes it by
 * pointer from a caller's local, which is what this file does too. */
struct segment {
    uint16_t first_bit;      /* k0   frame-bit index this pulse pins to     */
    uint16_t end_bit;        /* k1   where the NEXT pulse starts (<= NB)    */
    int16_t  fall_lo;        /* u    fall bracket, TU relative to the       */
    int16_t  fall_hi;        /* v    segment's own bit-lattice base         */
    uint8_t  family;         /* fam  sample slot of the last high sample    */
};

/* The stream's state.  Field for field this is decode.c's `ss` struct; the
 * PENDING SEGMENT is held as four loose fields rather than a whole `struct
 * segment` because its end_bit is not known yet -- only the NEXT rise dates
 * it -- and the shipped decoder holds exactly these four (q_pk0, q_pu, q_pv,
 * q_pfam). */
static struct segment_stream {
    uint32_t y_end;          /* g_yend  wire time the frame ends at        */
    uint32_t y_prev;         /* q_yprev previous pulse's mapped rise       */
    uint16_t bit_index;      /* q_n     running bit-slot cursor = the gap
                              *         accounting                        */
    uint16_t pend_first_bit; /* q_pk0                                      */
    int16_t  pend_fall_lo;   /* q_pu                                       */
    int16_t  pend_fall_hi;   /* q_pv                                       */
    uint8_t  pend_family;    /* q_pfam                                     */
    bool     have_prev;      /* q_have                                     */
    bool     pending;        /* q_pend  a segment is held back             */
    bool     source_done;    /* q_done                                     */
} segs;

static void segment_open(const uint8_t *cap, uint16_t cap_len)
{
    scan_open(cap, cap_len);
    memset(&segs, 0, sizeof(segs));
    segs.y_end = frame_end_tu();
}

static bool segment_next(struct segment *out)
{
    while (!segs.source_done) {
        int32_t y, y_fall_lo, y_fall_hi;
        uint32_t base;

        if (!scan_next_pulse()) {
            segs.source_done = true;
            break;
        }
        y = map_to_wire_tu(bracket_mid(edge.rise_lo, edge.rise_hi));
        if (y < 0)
            y = 0;
        if ((uint32_t)y > segs.y_end) {
            segs.source_done = true;
            break;                             /* past the frame */
        }

        /* --- gap accounting: how many bit slots since the last rise? --- */
        if (!segs.have_prev) {
            segs.bit_index = 0;                /* hard anchor: the first
                                                * pulse IS frame bit 0     */
            segs.have_prev = true;
        } else {
            int32_t gap = y - (int32_t)segs.y_prev;
            int16_t slots = (int16_t)shr_floor(gap + BIT_H, BIT_SH);
            if (slots > 0)
                segs.bit_index = (uint16_t)(segs.bit_index + slots);
        }
        segs.y_prev = (uint32_t)y;

        y_fall_lo = map_to_wire_tu(edge.fall_lo);
        y_fall_hi = map_to_wire_tu(edge.fall_hi);

        /* Two pulses that round to the SAME bit slot are one pulse the
         * sampler split spuriously; keep the later fall bracket. */
        if (segs.pending && segs.bit_index == segs.pend_first_bit) {
            base = bit_base_tu(segs.pend_first_bit);
            segs.pend_fall_lo = wrap_s16(y_fall_lo - (int32_t)base);
            segs.pend_fall_hi = wrap_s16(y_fall_hi - (int32_t)base);
            segs.pend_family = edge.family;
            continue;
        }

        if (segs.pending) {
            /* this rise dates the previous segment's end: emit it */
            out->first_bit = segs.pend_first_bit;
            out->fall_lo = segs.pend_fall_lo;
            out->fall_hi = segs.pend_fall_hi;
            out->family = segs.pend_family;
            out->end_bit = (segs.bit_index < geom.frame_bits) ? segs.bit_index
                                                              : geom.frame_bits;
            if (segs.bit_index >= geom.frame_bits) {
                segs.pending = false;
                segs.source_done = true;
                return true;
            }
            base = bit_base_tu(segs.bit_index);
            segs.pend_first_bit = segs.bit_index;
            segs.pend_fall_lo = wrap_s16(y_fall_lo - (int32_t)base);
            segs.pend_fall_hi = wrap_s16(y_fall_hi - (int32_t)base);
            segs.pend_family = edge.family;
            return true;
        }

        if (segs.bit_index >= geom.frame_bits) {
            segs.source_done = true;
            break;
        }
        base = bit_base_tu(segs.bit_index);
        segs.pending = true;
        segs.pend_first_bit = segs.bit_index;
        segs.pend_fall_lo = wrap_s16(y_fall_lo - (int32_t)base);
        segs.pend_fall_hi = wrap_s16(y_fall_hi - (int32_t)base);
        segs.pend_family = edge.family;
    }

    if (segs.pending) {                        /* flush the last segment */
        segs.pending = false;
        out->first_bit = segs.pend_first_bit;
        out->fall_lo = segs.pend_fall_lo;
        out->fall_hi = segs.pend_fall_hi;
        out->family = segs.pend_family;
        out->end_bit = geom.frame_bits;
        return true;
    }
    return false;
}

/*
 * How many leading ones the marker template ALLOWS this segment to have.
 * A known 1-bit inside the segment forces at least that many; a known
 * 0-bit forbids more than that many.  This is how the header and trailer
 * constrain the decode without any special-case code.
 */
static void leading_ones_bounds(uint16_t first_bit, uint16_t end_bit,
                                int16_t *min_ones, int16_t *max_ones)
{
    uint16_t t;
    uint16_t last = (end_bit < geom.frame_bits) ? end_bit : geom.frame_bits;

    *min_ones = 0;
    *max_ones = (int16_t)(end_bit - first_bit);
    for (t = first_bit; t < last; t++) {
        int8_t known = known_frame_bit(t);
        if (known == 1) {
            int16_t m = (int16_t)(t - first_bit + 1);
            if (m > *min_ones)
                *min_ones = m;
        } else if (known == 0) {
            int16_t m = (int16_t)(t - first_bit);
            if (m < *max_ones)
                *max_ones = m;
        }
    }
}

/*
 * THE HINGE COST -- how badly a hypothesised fall position contradicts the
 * observed fall bracket.  The bracket is (fall_lo, fall_hi]; the cost is
 * zero for any boundary INSIDE it (the observation is compatible: the edge
 * really could have been there) and otherwise the distance to the nearer
 * end.  This is exactly what "treat samples as intervals" means in code:
 * nothing is scored against a midpoint, only against a bracket.
 *
 * The widest value reachable is |fall| <= 32767 plus |boundary| <= 7896, so
 * a u16 holds it; the shipped decoder relies on that and so does this one.
 */
static uint16_t hinge_cost(int16_t fall_lo, int16_t fall_hi, int16_t boundary)
{
    int32_t too_late = (int32_t)fall_lo - boundary;   /* boundary before the bracket */
    int32_t too_early = (int32_t)boundary - fall_hi;  /* boundary after the bracket  */
    int32_t worst = 0;

    if (too_late > worst)
        worst = too_late;
    if (too_early > worst)
        worst = too_early;
    return (uint16_t)worst;
}

/* ==========================================================================
 *  THE HYPOTHESIS TABLE
 *
 *  For every admissible leading-ones count `a`, the hinge cost of the best
 *  fall position that `a` predicts, and whether any of those positions
 *  actually lands INSIDE the fall bracket ("interior" -- a sample decided
 *  it).  A segment of L bit slots that starts with `a` ones predicts a fall
 *  either
 *    * at (a-1)*BIT_U + width1   -- the last of the leading ones falls, or
 *    * at  a*BIT_U + width0      -- the first following 0-bit falls
 *      (only when a < L, i.e. there IS a following bit in this segment),
 *  and the cheaper of the two is the cost of the hypothesis.
 *
 *  WHERE IT LIVES.  The 16 costs are `hypothesis_cost`, the 32-byte overlay
 *  member the chase later re-uses for its reference set.  The three words
 *  that do not fit an array are the struct below, and the five chosen
 *  indices come back to the caller in a `hypothesis_pick` on its stack --
 *  which is what decode.c does too (`decide()` returns acap and fills four
 *  out-parameters).
 * ========================================================================== */

static struct hypothesis_state {
    uint16_t interior_mask;   /* dq_inter  bit a set: hypothesis a interior */
    int16_t  width0;          /* d_h0e     the family-calibrated boundaries */
    int16_t  width1;          /* d_h1e     ... section 6 reads them per bit */
} hyp;

struct hypothesis_pick {
    int16_t a_cap;            /* highest hypothesis index in play           */
    int16_t a_lo, a_hi;       /* marker-allowed range                       */
    int16_t a_best;           /* argmin inside [a_lo, a_hi]                 */
    int16_t a_free;           /* argmin ignoring the marker constraint      */
};

/* argmin of cost over [lo,hi], preferring an interior hypothesis on a tie,
 * then the smallest index.  Determinism matters: the candidate list this
 * feeds must be a reproducible function of the capture. */
static int16_t hypothesis_argmin(int16_t lo, int16_t hi)
{
    uint16_t best_cost = 0xFFFFu;
    bool best_interior = true;
    int16_t best = lo, a;

    for (a = lo; a <= hi; a++) {
        bool interior = ((hyp.interior_mask >> a) & 1u) != 0u;
        if (hypothesis_cost[a] < best_cost
            || (hypothesis_cost[a] == best_cost && interior && !best_interior)) {
            best_cost = hypothesis_cost[a];
            best_interior = interior;
            best = a;
        }
    }
    return best;
}

/* forward declaration: the calibration this needs is section 5's business */
static void calibrated_widths(uint8_t family, int16_t *width0, int16_t *width1);

static void build_hypotheses(const struct segment *sg,
                             struct hypothesis_pick *pick)
{
    int16_t span = (int16_t)(sg->end_bit - sg->first_bit);
    int16_t min_ones, max_ones, a;

    pick->a_cap = (span < A_CAP) ? span : A_CAP;
    calibrated_widths(sg->family, &hyp.width0, &hyp.width1);
    hyp.interior_mask = 0;
    /* hypothesis_cost is NOT cleared: entries 0..a_cap are all written
     * below and nothing above a_cap is ever read (both argmin ranges are
     * subsets of [0, a_cap]).  The shipped decoder does not clear it either
     * -- 32 bytes of zeroing per segment is not free on an 8-bit core. */

    for (a = 0; a <= pick->a_cap; a++) {
        uint16_t cost;
        bool interior;
        if (a == 0) {
            /* no leading ones: the very first bit of the segment is a 0 */
            cost = hinge_cost(sg->fall_lo, sg->fall_hi, hyp.width0);
            interior = (sg->fall_lo < hyp.width0 && hyp.width0 <= sg->fall_hi);
        } else {
            int16_t fall_of_last_one = (int16_t)((a - 1) * BIT_U + hyp.width1);
            cost = hinge_cost(sg->fall_lo, sg->fall_hi, fall_of_last_one);
            interior = (sg->fall_lo < fall_of_last_one
                        && fall_of_last_one <= sg->fall_hi);
            if (a < span) {
                int16_t fall_of_next_zero = (int16_t)(a * BIT_U + hyp.width0);
                uint16_t alt = hinge_cost(sg->fall_lo, sg->fall_hi,
                                          fall_of_next_zero);
                if (alt < cost)
                    cost = alt;
                if (sg->fall_lo < fall_of_next_zero
                    && fall_of_next_zero <= sg->fall_hi)
                    interior = true;
            }
        }
        hypothesis_cost[a] = cost;
        if (interior)
            hyp.interior_mask |= (uint16_t)(1u << (unsigned)a);
    }

    pick->a_free = hypothesis_argmin(0, pick->a_cap);
    leading_ones_bounds(sg->first_bit, sg->end_bit, &min_ones, &max_ones);
    pick->a_lo = (min_ones > 0) ? min_ones : 0;
    pick->a_hi = (max_ones < pick->a_cap) ? max_ones : pick->a_cap;
    if (pick->a_lo > pick->a_hi) {             /* contradictory constraints */
        pick->a_lo = 0;
        pick->a_hi = pick->a_cap;
    }
    pick->a_best = hypothesis_argmin(pick->a_lo, pick->a_hi);
}

/* ==========================================================================
 *  SECTION 5 -- CALIBRATION: PER-FAMILY PULSE-WIDTH ESTIMATES
 * ==========================================================================
 *
 *  Section 4 needs two numbers to score hypotheses against: where a 0-bit
 *  falls (width0) and where a 1-bit falls (width1), in TU after the bit's
 *  own rise.  The nominal values are H0P/H1P, but the sampler distorts them,
 *  and the distortion depends on the residual clock error AND on which
 *  sample slot last saw the pulse high.
 *
 *  So the decoder measures them on THIS frame, from the segments whose bits
 *  are entirely KNOWN -- the header and trailer.  That is what the protocol
 *  put them there for: 0xFF is a burst of long pulses, 0x00 is the
 *  worst-case zeros probe, 0xAA is a ruler of alternating bits.
 *
 *  Two mechanisms, both interval-censored:
 *
 *  (a) INTERVAL INTERSECTION.  Every known segment with an unambiguous
 *      leading-ones count contributes a bracket for "where a 0 falls" or
 *      "where a 1 falls".  Intersecting the brackets is the fit; the
 *      midpoint is only taken if the intersection is empty (contradictory
 *      evidence), and the result is clamped into a sanity box, so one bad
 *      segment cannot move the calibration far.
 *
 *  (b) THE EPS ANALOG (theta56).  For the two razor families -- 5 and 6, the
 *      slots followed by the widest intra-loop gaps -- the fall position is
 *      additionally shifted by the residual clock error.  The decoder folds
 *      every pulse start modulo the bit period into a 64-bin histogram (2 TU
 *      per bin), then looks for the widest EMPTY BAND inside the region the
 *      labelled examples still allow.  The empty band is where the boundary
 *      must be: the samples that would have landed there are the ones the
 *      dead zone ate.  Turning this off costs 7 of 54 real captures, which
 *      makes it the most valuable single mechanism in the pipeline.
 *
 *  MEMORY NOTE.  Mechanism (b)'s two histograms are 128 of the decoder's 364
 *  bytes -- by far its largest single object -- and they are DEAD the instant
 *  calibrate() returns.  That is overlay 1: the packed frame and the payload'
 *  bytes are the same storage, handed over by rbarf_decode().  Everything
 *  else here is 40 bytes of small fitted numbers.
 * ========================================================================== */

static struct calibration {
    /* (a) interval intersection, per label class: 0 = "a 0-bit fell here",
     *     1 = "a 1-bit fell here" */
    int16_t bracket_lo[2];          /* c_lo     running intersection lo     */
    int16_t bracket_hi[2];          /* c_hi     ... and hi                  */
    int16_t width0;                 /* c_h0c    the fitted fall positions   */
    int16_t width1;                 /* c_h1c                               */

    /* (b) the eps analog, for families 5 and 6 (index 0 and 1 here).  Its
     *     64-bin histograms are `fold_hist`, in overlay 1. */
    int16_t fold_center[2];         /* c_c0     where an undistorted pulse
                                     *          folds to                    */
    int16_t mapped_gap[2];          /* c_gap56  the family's sample gap, TU  */
    int16_t label_max0[2];          /* c_labx0  highest fold offset labelled
                                     *          0 ...                       */
    int16_t label_max0_2nd[2];      /* c_labx0b ... and the runner-up        */
    int16_t label_min1[2];          /* c_labx1  lowest labelled 1 ...        */
    int16_t label_min1_2nd[2];      /* c_labx1b ... and its runner-up        */
    uint8_t n_labelled[2];          /* c_n      examples per label class     */
    int8_t  family_shift[2];        /* c_d56    TU to add to width0/width1   */
} cal;

/* The boundaries build_hypotheses() must use for a segment of this family. */
static void calibrated_widths(uint8_t family, int16_t *width0, int16_t *width1)
{
    *width0 = cal.width0;
    *width1 = cal.width1;
    if (family == 5 || family == 6) {
        int8_t shift = cal.family_shift[family - 5];
        *width0 = (int16_t)(*width0 + shift);
        *width1 = (int16_t)(*width1 + shift);
    }
}

/*
 * Turn one marker-forced hypothesis into a labelled fall bracket.
 *
 * If the segment's leading-ones count is 0 the bracket is a 0-bit's fall,
 * measured from the segment's own base.  If it equals the segment span the
 * bracket is the LAST leading one's fall, measured from that bit's base.  In
 * between, both readings are possible and the nearer of the two nominal
 * boundaries decides which -- unless both are absurdly far away (LAB_OUT),
 * in which case the example is dropped rather than believed.
 *
 * Returns the label class (0 or 1), or -1 for "unusable".
 */
static int8_t label_fall_bracket(uint16_t first_bit, uint16_t end_bit,
                                 int16_t fall_lo, int16_t fall_hi, int16_t a,
                                 int16_t *lo, int16_t *hi)
{
    int16_t span = (int16_t)(end_bit - first_bit);
    int16_t offset;
    int8_t label;

    if (a == 0) {
        offset = 0;
        label = 0;
    } else if (a == span) {
        offset = (int16_t)((span - 1) * BIT_U);
        label = 1;
    } else {
        int16_t mid = (int16_t)halve_floor((int32_t)fall_lo + fall_hi);
        int32_t d1 = abs32((int32_t)mid - ((a - 1) * BIT_U + H1P));
        int32_t d0 = abs32((int32_t)mid - (a * BIT_U + H0P));
        if ((d0 < d1 ? d0 : d1) > LAB_OUT)
            return -1;
        if (d1 <= d0) {
            offset = (int16_t)((a - 1) * BIT_U);
            label = 1;
        } else {
            offset = (int16_t)(a * BIT_U);
            label = 0;
        }
    }
    *lo = wrap_s16((int32_t)fall_lo - offset);
    *hi = wrap_s16((int32_t)fall_hi - offset);
    return label;
}

/* Feed one pulse start into the fold histogram (mechanism b's density). */
static void calibration_add_cloud(int16_t fall_lo, uint8_t family)
{
    int16_t offset, d;
    uint8_t f;

    if ((family != 5 && family != 6) || fall_lo < 0)
        return;
    f = (uint8_t)(family - 5);
    offset = (int16_t)(fall_lo & (BIT_U - 1));      /* fold modulo the bit slot */
    d = (int16_t)(offset - cal.fold_center[f]);
    if (d >= -EPS_HIST && d < EPS_HIST) {
        uint8_t bin = (uint8_t)((d + EPS_HIST) >> 1);
        if (fold_hist[f][bin] < 255)
            fold_hist[f][bin]++;
    }
}

/* Feed one labelled example into both mechanisms. */
static void calibration_add_label(uint16_t first_bit, uint16_t end_bit,
                                  int16_t fall_lo, int16_t fall_hi,
                                  uint8_t family, int16_t a)
{
    int16_t lo, hi;
    int8_t label = label_fall_bracket(first_bit, end_bit, fall_lo, fall_hi, a,
                                      &lo, &hi);
    if (label < 0)
        return;

    /* (a) intersect */
    if (lo > cal.bracket_lo[label])
        cal.bracket_lo[label] = lo;
    if (hi < cal.bracket_hi[label])
        cal.bracket_hi[label] = hi;
    if (cal.n_labelled[label] < 255)
        cal.n_labelled[label]++;

    /* (b) remember how far the labelled examples constrain the fold zone */
    if ((family == 5 || family == 6) && lo >= 0) {
        uint8_t f = (uint8_t)(family - 5);
        int16_t d = (int16_t)((lo & (BIT_U - 1)) - cal.fold_center[f]);
        if (d >= -EPS_HIST && d < EPS_HIST) {
            if (label == 0) {
                if (d > cal.label_max0[f]) {
                    cal.label_max0_2nd[f] = cal.label_max0[f];
                    cal.label_max0[f] = d;
                } else if (d > cal.label_max0_2nd[f]) {
                    cal.label_max0_2nd[f] = d;
                }
            } else {
                if (d < cal.label_min1[f]) {
                    cal.label_min1_2nd[f] = cal.label_min1[f];
                    cal.label_min1[f] = d;
                } else if (d < cal.label_min1_2nd[f]) {
                    cal.label_min1_2nd[f] = d;
                }
            }
        }
    }
}

/*
 * theta56 -- the eps analog for one razor family.
 *
 * Inside the fold zone the labelled examples still allow (above every
 * example labelled 0, below every example labelled 1), find the WIDEST
 * EMPTY BAND in the density histogram and put the boundary in its middle.
 * Guards, in order:
 *
 *   * an empty histogram falls back to the middle of the allowed zone;
 *   * the widest band must be at least EPS_GAP_MIN wide, and (once there are
 *     enough occupied bins) must be a real gap rather than the largest of
 *     many small ones -- that is the 2*gap*ngaps >= 5*zone test;
 *   * the answer is then clamped into the window the labelled examples and
 *     their runner-ups leave open;
 *   * finally, if nothing at all landed above EPS_CLEAR1, the boundary is
 *     pushed just past the highest occupied bin: no evidence of long pulses
 *     means the boundary belongs above everything seen.
 *
 * This is the LAST READER of fold_hist, and therefore the point after which
 * overlay 1 may be handed to the decision pass.
 *
 * Returns false when the family has no usable evidence at all.
 */
static bool estimate_family_shift(uint8_t f, int16_t *theta_out)
{
    int16_t x_max0 = cal.label_max0[f], x_min1 = cal.label_min1[f];
    bool have0 = (x_max0 > -0x4000);
    bool have1 = (x_min1 < 0x3FFF);
    int16_t zone_lo = (int16_t)(x_max0 + 1);
    int16_t zone_hi = x_min1;
    int16_t theta = 0;
    bool have_theta = false;
    int16_t top = 0;
    bool have_top = false, anything_high = false;
    uint8_t bin;

    if (zone_lo < -EPS_ZONE)
        zone_lo = -EPS_ZONE;
    if (zone_hi > EPS_ZONE)
        zone_hi = EPS_ZONE;

    /* --- widest empty band inside (zone_lo, zone_hi] --- */
    if (zone_lo < zone_hi) {
        uint8_t bin_lo = (uint8_t)((zone_lo + EPS_HIST) >> 1);
        uint8_t bin_hi = (uint8_t)((zone_hi - 1 + EPS_HIST) >> 1);
        int16_t prev = zone_lo, band_lo = 0, band_hi = 0, widest = -1;
        uint8_t n_occupied = 0;

        for (bin = bin_lo; bin <= bin_hi; bin++) {
            if (fold_hist[f][bin]) {
                int16_t x = (int16_t)(((int16_t)bin << 1) - EPS_HIST + 1);
                int16_t gap = (int16_t)(x - prev);
                if (gap > widest) {
                    widest = gap;
                    band_lo = prev;
                    band_hi = x;
                }
                prev = x;
                n_occupied++;
            }
        }
        {
            int16_t gap = (int16_t)(zone_hi - prev);
            if (gap > widest) {
                widest = gap;
                band_lo = prev;
                band_hi = zone_hi;
            }
        }
        if (n_occupied == 0) {
            if (have0 && have1) {
                theta = (int16_t)halve_floor((int32_t)zone_lo + zone_hi);
                have_theta = true;
            }
        } else {
            bool ok = (widest >= EPS_GAP_MIN);
            /* n_occupied + 1 gaps; require the winner to dominate them.
             * s16-safe at both geometries (the Python reference asserts the
             * same bound): widest <= 2*EPS_ZONE = 64 and n_occupied+1 <= 34,
             * so the left side is at most 4352 and the right at most 320. */
            if (ok && (uint8_t)(n_occupied + 1u) >= 4u) {
                if (2 * widest * (n_occupied + 1) < 5 * (zone_hi - zone_lo))
                    ok = false;
            }
            if (ok) {
                theta = (int16_t)halve_floor((int32_t)band_lo + band_hi);
                have_theta = true;
            }
        }
    }

    /* --- clamp into the window the labelled examples leave open --- */
    if (have0 || have1) {
        int16_t win_lo = -EPS_ZONE, win_hi = EPS_ZONE;
        if (have0) {
            win_lo = (int16_t)(x_max0 - EPS_SLACK1);
            if (cal.label_max0_2nd[f] > -0x4000
                && (int16_t)(cal.label_max0_2nd[f] - EPS_SLACK) > win_lo)
                win_lo = (int16_t)(cal.label_max0_2nd[f] - EPS_SLACK);
        }
        if (have1) {
            win_hi = (int16_t)(x_min1 + EPS_SLACK1);
            if (cal.label_min1_2nd[f] < 0x3FFF
                && (int16_t)(cal.label_min1_2nd[f] + EPS_SLACK) < win_hi)
                win_hi = (int16_t)(cal.label_min1_2nd[f] + EPS_SLACK);
        }
        if (win_lo > win_hi) {
            theta = (int16_t)halve_floor((int32_t)win_lo + win_hi);
        } else {
            int16_t th = have_theta ? theta : 0;
            if (th < win_lo)
                th = win_lo;
            if (th > win_hi)
                th = win_hi;
            theta = th;
        }
        have_theta = true;
    }

    /* --- nothing high anywhere: the boundary is above everything seen --- */
    for (bin = 0; bin < EPS_HIST; bin++) {
        int16_t d;
        if (!fold_hist[f][bin])
            continue;
        d = (int16_t)(((int16_t)bin << 1) - EPS_HIST + 1);
        if (d > EPS_CLEAR1) {
            anything_high = true;
        } else if (d > -EPS_CLAMP56) {
            if (!have_top || d > top)
                top = d;
            have_top = true;
        }
    }
    if (!anything_high && have_top) {
        int16_t floor_val = (int16_t)(top + EPS_TOPM);
        if (!have_theta || floor_val > theta)
            theta = floor_val;
        have_theta = true;
        if (have1 && (int16_t)(x_min1 + EPS_SLACK) > floor_val
            && theta > (int16_t)(x_min1 + EPS_SLACK))
            theta = (int16_t)(x_min1 + EPS_SLACK);
    }

    *theta_out = theta;
    return have_theta;
}

/* The interval-intersection fit for one label class, clamped to its box. */
static int16_t width_fit(uint8_t label, int16_t prior,
                         int16_t box_lo, int16_t box_hi)
{
    int16_t lo = cal.bracket_lo[label], hi = cal.bracket_hi[label], h;

    if (cal.n_labelled[label] < LAB_MIN)
        return prior;                          /* too little evidence */
    if (lo > hi)
        h = (int16_t)halve_floor((int32_t)lo + hi);  /* empty: split the difference */
    else
        h = (prior < lo) ? lo : (prior > hi ? hi : prior);  /* clamp the prior in */
    return (h >= box_lo && h <= box_hi) ? h : prior;
}

static void calibrate(const uint8_t *cap, uint16_t cap_len)
{
    struct segment sg;
    uint8_t f;

    /* priors: the nominal widths, and no family shift */
    cal.bracket_lo[0] = cal.bracket_lo[1] = -0x4000;
    cal.bracket_hi[0] = cal.bracket_hi[1] = 0x3FFF;
    cal.n_labelled[0] = cal.n_labelled[1] = 0;
    cal.width0 = H0P;
    cal.width1 = H1P;
    /* Families 5 and 6 are followed by 6- and 5-cycle sample gaps; mapping
     * those gaps through the clock fit says how much of the pulse the family
     * cannot see, which is where its fold centre sits. */
    cal.mapped_gap[0] = (int16_t)(((uint32_t)6u * clk.bit_period_q) >> KQ);
    cal.mapped_gap[1] = (int16_t)(((uint32_t)5u * clk.bit_period_q) >> KQ);
    for (f = 0; f < 2; f++) {
        cal.family_shift[f] = 0;
        cal.fold_center[f] = (int16_t)((H0P + H1P - cal.mapped_gap[f]) >> 1);
        /* overlay 1 is OURS from here to the end of this function, and this
         * is where we take ownership: nothing is inherited */
        memset(fold_hist[f], 0, sizeof(fold_hist[f]));
        cal.label_max0[f] = -0x4000;
        cal.label_max0_2nd[f] = -0x4000;
        cal.label_min1[f] = 0x3FFF;
        cal.label_min1_2nd[f] = 0x3FFF;
    }

    segment_open(cap, cap_len);
    while (segment_next(&sg)) {
        uint16_t t, last;
        bool all_known = true;
        int16_t min_ones, max_ones;

        calibration_add_cloud(sg.fall_lo, sg.family);
        if (sg.end_bit > geom.frame_bits)
            continue;
        last = (sg.end_bit < geom.frame_bits) ? sg.end_bit : geom.frame_bits;
        for (t = sg.first_bit; t < last; t++) {
            if (known_frame_bit(t) < 0) {
                all_known = false;
                break;
            }
        }
        if (!all_known)
            continue;                          /* only markers teach here */
        leading_ones_bounds(sg.first_bit, sg.end_bit, &min_ones, &max_ones);
        if (min_ones == max_ones)              /* ... and only unambiguously */
            calibration_add_label(sg.first_bit, sg.end_bit, sg.fall_lo,
                                  sg.fall_hi, sg.family, min_ones);
    }

    /* (a) the global width fit, with a separation sanity check: if the two
     * fitted widths are not a plausible distance apart, distrust both and
     * fall back to nominal. */
    {
        int16_t h0 = width_fit(0, H0P, H0_LO, H0_HI);
        int16_t h1 = width_fit(1, H1P, H1_LO, H1_HI);
        if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) {
            h0 = H0P;
            h1 = H1P;
        }
        cal.width0 = h0;
        cal.width1 = h1;
    }

    /* (b) the per-family shift, clamped: the eps analog may nudge the razor
     * families by at most EPS_CLAMP56 TU. */
    for (f = 0; f < 2; f++) {
        int16_t theta, center_from_fit, delta;
        if (!estimate_family_shift(f, &theta)) {
            cal.family_shift[f] = 0;
            continue;
        }
        center_from_fit = (int16_t)((cal.width0 + cal.width1
                                     - cal.mapped_gap[f]) >> 1);
        delta = (int16_t)(theta + cal.fold_center[f] - center_from_fit);
        if (delta < -EPS_CLAMP56)
            delta = -EPS_CLAMP56;
        if (delta > EPS_CLAMP56)
            delta = EPS_CLAMP56;
        cal.family_shift[f] = (int8_t)delta;
    }
    /* fold_hist is dead from here.  rbarf_decode() performs the handover. */
}

/* ==========================================================================
 *  SECTION 6 -- THE DECISION PASS
 * ==========================================================================
 *
 *  One more streaming pass over the capture. For each segment it picks the
 *  leading-ones count, writes the bits, and -- the part that makes the chase
 *  possible -- SCORES EVERY BIT and remembers which ones were shaky.
 *
 *  THE MARGIN.  For payload' bit t, let c1 be the cheapest hypothesis that
 *  makes t a 1 and c0 the cheapest that makes it a 0.  The margin is
 *  |c0 - c1|, saturated at 255 TU, and it is a genuine per-bit
 *  log-likelihood-ratio analog that the decision already computed and v1
 *  threw away.  Special values:
 *      255  one polarity was impossible (no hypothesis at all)
 *        0  the two cost the same, i.e. the bit was decided by TIE-BREAK,
 *           not by evidence.
 *  Most bits come out with huge margins; a few per frame are knife-edge,
 *  and the decoder knows WHICH ones.
 *
 *  THE CANDIDATE LIST.  A sorted A_MAX-entry insertion list of the weakest
 *  payload' bits, keyed (margin, bit index) ascending -- deterministic, so
 *  the parity harness can compare it.  n_weak counts ALL bits at margin
 *  <= MG_MAX, including any that did not fit, because knowing the list is
 *  INCOMPLETE is what rung R7 of the ladder is made of.
 *
 *  THE DEAD WINDOW (Lever B) -- why a bit whose interval fell between
 *  samples is a candidate even when its margin looks confident:
 *
 *    A bit's DISCRIMINATING INTERVAL is the only wire-time window in which a
 *    sample can tell 0 from 1:
 *        A = off*BIT_U + width0   (where it falls if the bit is 0)
 *        B = off*BIT_U + width1   (where it falls if the bit is 1)
 *    Below A the line is high either way; above B it is low either way.  And
 *    the ENTIRE observation is the fall bracket (fall_lo, fall_hi], whose
 *    ends are ADJACENT samples -- nothing lies strictly between them.  With
 *        ga = (A <= fall_lo)        gb = (fall_hi < B)
 *    the HEALTHY case is ga != gb: exactly one of the two candidate fall
 *    positions lies inside the bracket, i.e. A SAMPLE DECIDED THE BIT.
 *    ga == gb is degenerate, in one of two ways:
 *      MID  (both true)  the bracket lies inside the window: a transition
 *                        was seen, but at NEITHER fitted boundary, so the
 *                        polarity rests on which boundary is nearer -- on
 *                        the width fit, not on a sample.
 *      DEAD (both false) the window lies inside the bracket: NO SAMPLE IN
 *                        IT AT ALL, and both hypotheses are admitted.
 *    Such a bit can carry a large, confident-looking margin and still be a
 *    coin flip.  Measured over 1530 frames: these 1 % of bits carry HALF the
 *    wrong bits (a 91x enrichment), and refusing them was exactly what rung
 *    R6 ("no candidate") used to be made of.  So a degenerate bit whose
 *    margin is > MG_MAX joins the SAME candidate list through the SAME
 *    sorted insertion.  No second pool, no second key: a weak bit's margin
 *    is <= MG_MAX and a dead-window bit's is > MG_MAX, so the single
 *    ascending key already sorts every weak entry ahead of every
 *    dead-window entry.  Two consequences fall out for free -- R7's
 *    completeness rule is untouched, and a full list drops the WORST
 *    (highest-margin, least suspicious) dead-window entry first.
 *
 *    Widening the candidate set does NOT widen the risk, because the risk
 *    bound is T_MAX residual comparisons, not the number of candidates.
 *
 *  MEMORY NOTE.  The decoded frame is the 60-byte packed bit array of
 *  overlay 1 -- one byte per bit would be 480 B, which the chip does not
 *  have.  Everything else here is 66 bytes of counters and the 33-byte
 *  candidate list, and this pass TAKES OWNERSHIP of both overlays: it zeroes
 *  the packed frame before writing it and rewrites hypothesis_cost from
 *  index 0 for every segment.
 * ========================================================================== */

static struct decision_state {
    uint16_t n_segments;              /* _d_nseg                            */
    uint16_t infeasible;              /* _d_infeas  R3 evidence             */
    uint16_t label_error;             /* _d_laberr  R4 evidence             */
    uint16_t n_weak;                  /* _v_nweak   ALL bits margin <= MG_MAX*/
    uint16_t n_tied;                  /* _v_ntied   ALL bits margin == 0    */
    uint16_t n_dw;                    /* _v_ndw     dead-window candidates.
                                       * A LINKER GLOBAL on the target, not
                                       * a dec_info field: the only consumer
                                       * on-chip is the R6 gate, so keeping
                                       * it out of the report costs the
                                       * assembly nothing.                 */
    /* Per-check-byte confidence: the sum of that byte's 8 bit margins (each
     * saturated at 255, so at most 2040).  Used only to RANK the candidate
     * values of a check byte position whose three copies all disagree. */
    uint16_t check_conf[CHECK_BYTES]; /* _v_chkconf                         */
    uint16_t cand_bit[A_MAX];         /* _v_cand_t  payload'-relative index */
    int16_t  tie_pending;             /* w_tiep     a tie mark that lands in
                                       * the NEXT segment; -1 when none.
                                       * ONE slot replaces v1's whole tied[]
                                       * bitmap and is bit-identical.      */
    uint8_t  cand_margin[A_MAX];      /* _v_cand_m  sorted with cand_bit    */
    uint8_t  n_cand;                  /* _v_ncand                           */
} dec;

/* Sorted top-A_MAX insertion, key (margin, bit index) ascending.  Bits
 * arrive in ascending index order, so inserting AFTER equal-margin entries
 * is what makes the tie rule "smaller index first". */
static void candidate_insert(uint16_t k, uint8_t margin)
{
    uint8_t i = dec.n_cand, j;

    while (i > 0 && dec.cand_margin[i - 1] > margin)
        i--;
    if (i >= A_MAX)
        return;                                /* worse than everything held */
    j = (dec.n_cand < A_MAX) ? dec.n_cand : (uint8_t)(A_MAX - 1);
    while (j > i) {
        dec.cand_bit[j] = dec.cand_bit[j - 1];
        dec.cand_margin[j] = dec.cand_margin[j - 1];
        j--;
    }
    dec.cand_bit[i] = k;
    dec.cand_margin[i] = margin;
    if (dec.n_cand < A_MAX)
        dec.n_cand++;
}

static void decision_pass(const uint8_t *cap, uint16_t cap_len)
{
    struct segment sg;
    uint8_t q;

    /* Overlay 1's packed-frame view is OURS from here on, and we start it at
     * zero rather than inheriting anything: set_bit() only ever sets. */
    memset(frame_bit, 0, frame_bytes());
    dec.n_segments = 0;
    dec.infeasible = 0;
    dec.label_error = 0;
    dec.n_cand = 0;
    dec.n_weak = 0;
    dec.n_tied = 0;
    dec.n_dw = 0;
    dec.tie_pending = -1;
    for (q = 0; q < CHECK_BYTES; q++)
        dec.check_conf[q] = 0;

    segment_open(cap, cap_len);
    while (segment_next(&sg)) {
        struct hypothesis_pick pick;
        uint16_t t, last;
        int16_t a;
        int16_t tie_here = -1;
        int16_t first_interior = -1;
        uint8_t n_interior_all = 0, n_interior_allowed = 0;
        bool all_known = true;

        dec.n_segments++;
        if (sg.first_bit >= geom.frame_bits)
            continue;

        build_hypotheses(&sg, &pick);

        /* R3 evidence: not even the best hypothesis explains this pulse. */
        if (hypothesis_cost[pick.a_best] > INFEAS_U)
            dec.infeasible++;

        last = (sg.end_bit < geom.frame_bits) ? sg.end_bit : geom.frame_bits;
        for (t = sg.first_bit; t < last; t++) {
            if (known_frame_bit(t) < 0) {
                all_known = false;
                break;
            }
        }

        for (a = 0; a <= pick.a_cap; a++)
            if ((hyp.interior_mask >> a) & 1u)
                n_interior_all++;

        /* R4 evidence: on a segment whose bits are all KNOWN and whose
         * template leaves exactly one hypothesis, the free argmin should
         * agree.  When two hypotheses are interior the window genuinely
         * cannot tell them apart, and calling that a label error would
         * refuse the whole fast corner wholesale -- so it is excluded. */
        if (all_known && pick.a_lo == pick.a_hi && pick.a_free != pick.a_lo
            && n_interior_all < 2)
            dec.label_error++;

        /* A tie mark: two hypotheses inside the allowed range are BOTH
         * interior, so the bit where they first differ was decided by the
         * tie-break rather than by evidence.  It is marked at the first
         * interior hypothesis, which can be the next segment's first bit --
         * hence tie_pending.
         *
         * v1 also required a_best to be one of the two interior indices,
         * and that test is ALWAYS TRUE: an interior boundary has hinge cost
         * 0 and the argmin key is (cost, NOT interior, index) ascending, so
         * a non-empty interior set forces a_best == first_interior.  Proven
         * over 1 619 577 decided segments of every corpus, 0 counter-
         * examples, so the second index is never even computed. */
        for (a = pick.a_lo; a <= pick.a_hi; a++) {
            if ((hyp.interior_mask >> a) & 1u) {
                if (n_interior_allowed == 0)
                    first_interior = a;
                n_interior_allowed++;
            }
        }
        if (n_interior_allowed >= 2) {
            uint16_t tt = (uint16_t)(sg.first_bit + first_interior);
            if (tt < geom.frame_bits)
                tie_here = (int16_t)tt;
        }

        /* ---- write the bits, score them, collect the candidates ---- */
        for (t = sg.first_bit; t < last; t++) {
            int16_t off = (int16_t)(t - sg.first_bit);
            uint16_t best_zero = 0, best_one = 0;
            bool have_zero = false, have_one = false;
            uint16_t margin;
            bool degenerate = false;

            /* Lever B: is this bit's discriminating interval decided by a
             * sample, or not?  Stateless -- the offset term is a pure
             * function of off, so there is no accumulator and no latch. */
            if (off < DW_OFF_MAX) {
                int16_t base = (int16_t)(off << BIT_SH);
                bool ga = ((int16_t)(base + hyp.width0) <= sg.fall_lo);
                bool gb = (sg.fall_hi < (int16_t)(base + hyp.width1));
                degenerate = (ga == gb);
            }

            if (off < pick.a_best)
                set_bit(frame_bit, t);         /* the leading ones; the rest
                                                * are already 0            */

            for (a = pick.a_lo; a <= pick.a_hi; a++) {
                if (a > off) {                 /* these hypotheses make t a 1 */
                    if (!have_one || hypothesis_cost[a] < best_one) {
                        best_one = hypothesis_cost[a];
                        have_one = true;
                    }
                } else {                       /* ... and these make it a 0 */
                    if (!have_zero || hypothesis_cost[a] < best_zero) {
                        best_zero = hypothesis_cost[a];
                        have_zero = true;
                    }
                }
            }
            if (!have_zero || !have_one) {
                margin = 255;                  /* one polarity impossible */
            } else {
                int32_t d = abs32((int32_t)best_zero - (int32_t)best_one);
                margin = (d > 255) ? 255u : (uint16_t)d;
            }
            if ((int16_t)t == tie_here || (int16_t)t == dec.tie_pending)
                margin = 0;                    /* decided by tie-break */

            if (t >= PAYLOAD_LO && t < geom.payload_hi) {
                uint16_t k = (uint16_t)(t - PAYLOAD_LO);
                if (k >= geom.data_bits) {
                    uint8_t cb = (uint8_t)((k - geom.data_bits) >> 3);
                    dec.check_conf[cb] = (uint16_t)(dec.check_conf[cb] + margin);
                }
                if (margin <= MG_MAX) {
                    dec.n_weak++;
                    if (margin == 0)
                        dec.n_tied++;
                    candidate_insert(k, (uint8_t)margin);
                } else if (degenerate) {
                    dec.n_dw++;
                    candidate_insert(k, (uint8_t)margin);
                }
            }
        }

        if (dec.tie_pending >= 0 && dec.tie_pending < (int16_t)last)
            dec.tie_pending = -1;              /* consumed in this segment */
        if (tie_here >= (int16_t)last)
            dec.tie_pending = tie_here;        /* lands in the next one    */
    }
    /* hypothesis_cost is dead from here.  rbarf_decode() performs the
     * handover of overlay 2 to the check block and the chase. */
}

/* ==========================================================================
 *  SECTION 7 -- THE CHECK BLOCK: CRC-16 x3, PER-BYTE MAJORITY, REFERENCE SET
 * ==========================================================================
 *
 *  The frame carries CRC-16/CCITT-FALSE of the DATA bytes, written three
 *  times as (HI LO)(HI LO)(HI LO).  Why three times?  Because the check
 *  bytes travel the same lossy channel as everything else, and a corrupted
 *  checksum used to be able to sink a perfectly recoverable frame.  On real
 *  silicon, one check byte in five arrived damaged.
 *
 *  The receiver takes the majority PER BYTE POSITION, not per block:
 *
 *      reference_HI = majority(C[0], C[2], C[4])
 *      reference_LO = majority(C[1], C[3], C[5])
 *
 *  With three votes no tie is possible -- a position either has a unique
 *  >= 2-vote winner or all three copies differ.  Independence is the whole
 *  point: two copies damaged in DIFFERENT byte positions destroy any
 *  block-level vote, yet still leave two good votes at each position, so the
 *  exact 16-bit reference comes back.
 *
 *  THE REFERENCE is the value the recomputed CRC must equal.  When a byte
 *  position splits, its three distinct values are all candidates, ranked by
 *  the decoded confidence of the copy carrying them (section 6's per-check-
 *  byte margin sums), and the references are the cross product -- at most
 *  3x3 = 9 -- enumerated in DIAGONAL order (rank-sum ascending), which tries
 *  better references first without sorting anything.  Every extra reference
 *  is extra exposure, so it is paid for out of the T_MAX budget, and a
 *  marker-suspect frame is denied the enumeration altogether.
 *
 *  MEMORY NOTE.  This stage takes ownership of both overlays' second view:
 *  the payload' bytes (54 B, written whole by assemble_payload) and the
 *  reference set plus the two ranked value lists (24 B, written whole by
 *  build_reference_set).  Its own state is the eight bytes below.
 * ========================================================================== */

static uint16_t crc16_ccitt_false(const uint8_t *data, uint8_t n)
{
    uint16_t r = CRC16_INIT;
    uint8_t i, j;

    for (i = 0; i < n; i++) {
        r ^= (uint16_t)((uint16_t)data[i] << 8);
        for (j = 0; j < 8; j++)
            r = crc16_times_x(r);
    }
    return r;
}

static struct check_block {
    uint16_t residual_base;    /* ch_rbase  crc16(DATA) as decoded          */
    uint8_t  n_hi;             /* ch_nhi    1 = the HI position had a       */
    uint8_t  n_lo;             /* ch_nlo        majority, else 3            */
    uint8_t  n_refs;           /* ch_nref   references materialised         */
    uint8_t  ref_cap;          /* ch_cap    REF_MAX, or 1 if marker-suspect */
    uint8_t  n_cand;           /* ch_n      candidates in play              */
    uint8_t  comps;            /* ch_comps  residual comparisons spent.
                                * A u8 in all three implementations, which
                                * is why T_MAX is capped at 255.            */
} chk;

/*
 * Assemble the payload' bytes from the packed decoded frame.
 *
 * PAYLOAD_LO is a whole number of BYTES (8 * HDR_BYTES), so payload' byte p
 * is exactly frame byte HDR_BYTES + p.  The packed frame holds bit t at bit
 * t & 7 -- LSB first -- while the wire byte is MSB first, so the conversion
 * is precisely a BIT REVERSAL: one byte-wide rotate loop, instead of eight
 * get_bit() calls with a 16-bit index.  This is what the shipped assembly
 * has always done, and it is the reason for the packing order.
 */
static void assemble_payload(void)
{
    uint8_t p, j;

    for (p = 0; p < geom.payload_bytes; p++) {
        uint8_t b = frame_bit[HDR_BYTES + p], val = 0;
        for (j = 0; j < 8; j++) {
            val = (uint8_t)((val << 1) | (uint8_t)(b & 1u));
            b = (uint8_t)(b >> 1);
        }
        pp_byte[p] = val;
    }
}

/*
 * Candidate values for ONE check-byte position (base 0 = HI, 1 = LO), best
 * confidence first.  The three copies sit at pp_byte[nd + base], +2, +4 and
 * their confidences at check_conf[base + 0/2/4].
 *
 * A majority collapses the list to a single entry (three votes admit NO
 * tie, so the test is three compares).  When all three differ, each copy's
 * RANK is the number of copies that beat it -- higher confidence, or equal
 * confidence and an earlier position on the wire.  That double loop IS the
 * ordering: no sort, no key array.
 */
static void rank_check_position(uint8_t base, uint8_t *out, uint8_t *n)
{
    const uint8_t *c = &pp_byte[geom.data_bytes];
    uint8_t v0 = c[base], v1 = c[base + 2], v2 = c[base + 4];
    uint8_t i, j;

    if (v0 == v1 || v0 == v2) { out[0] = v0; *n = 1; return; }
    if (v1 == v2)             { out[0] = v1; *n = 1; return; }

    for (j = 0; j < 3; j++) {
        uint16_t conf_j = dec.check_conf[base + 2u * j];
        uint8_t rank = 0;
        for (i = 0; i < 3; i++) {
            uint16_t conf_i = dec.check_conf[base + 2u * i];
            if (conf_i > conf_j || (conf_i == conf_j && i < j))
                rank++;
        }
        out[rank] = (j == 0) ? v0 : ((j == 1) ? v1 : v2);
    }
    *n = 3;
}

/* Build the ordered reference set from the current payload' check bytes.
 * Materialising it is what keeps residual_match() down to an array scan --
 * that scan is walked up to T_MAX = 131 times per frame. */
static void build_reference_set(void)
{
    uint8_t rank_sum, a, b, q = 0;

    rank_check_position(0, hi_values, &chk.n_hi);
    rank_check_position(1, lo_values, &chk.n_lo);

    /* diagonal order: (0,0) (0,1) (1,0) (0,2) (1,1) (2,0) (1,2) (2,1) (2,2) */
    for (rank_sum = 0; rank_sum < 5; rank_sum++) {
        for (a = 0; a < chk.n_hi; a++) {
            if (a > rank_sum)
                break;
            b = (uint8_t)(rank_sum - a);
            if (b >= chk.n_lo)
                continue;
            if (q >= chk.ref_cap) {
                chk.n_refs = q;
                return;
            }
            reference[q++] = (uint16_t)
                (((uint16_t)hi_values[a] << 8) | lo_values[b]);
        }
    }
    chk.n_refs = q;
}

/* ==========================================================================
 *  SECTION 8 -- THE CRC-GUIDED CHASE
 * ==========================================================================
 *
 *  A CRC by itself only DETECTS errors.  Combined with section 6's per-bit
 *  margins it becomes a tiny error corrector: if the check does not match,
 *  take the handful of shakiest bits and try flipping them -- one at a time,
 *  then in pairs -- until the check clicks.  This is classic chase decoding,
 *  and it fits because the error model here is precisely "one to three
 *  knife-edge bits", not random noise.  On the bench about one delivered
 *  frame in eight arrives through such a repair.
 *
 *  SYNDROME ARITHMETIC.  CRC-16 is linear over GF(2) once the init constant
 *  is accounted for: crc(D ^ e) = crc(D) ^ crc0(e).  So no trial ever
 *  recomputes a CRC.  Flipping DATA bit k just XORs a precomputed syndrome
 *  into the residual:
 *
 *      syndrome(k) = x^(16 + 8*(nd-1-p) + b) mod 0x11021,  p = k>>3, b = 7-(k&7)
 *                  = SYNDROME_X8[nd-1-p] shifted b times
 *
 *  Bits inside the CHECK bytes have no syndrome at all -- they are not part
 *  of their own message.  Flipping one changes the REFERENCE, not the
 *  residual, and that asymmetry drives the trial order.
 *
 *  TRIAL ORDER -- data-minimal, cheapest-first, five phases:
 *      1  one check bit          leaves DATA untouched: cannot corrupt it
 *      2  two check bits         ditto
 *      3  one data bit           the classic single knife-bit repair
 *      4  one data + one check
 *      5  two data bits          most invasive, tried last
 *  Preferring "the check block was damaged" over "the payload was damaged"
 *  is the strictly safer error hypothesis: a mismatch explained by check
 *  damage costs the payload nothing.  Within a phase, candidates are taken
 *  in list order, which is ascending margin -- shakiest first.
 *
 *  THE PARITY GATE (free, and exact).  0x11021 = (x+1) * 0xF01F, so every
 *  single-bit syndrome has ODD parity and a weight-w data-only flip set has
 *  syndrome parity w mod 2.  A data-only phase whose parity can match no
 *  admitted reference therefore cannot possibly pass, and is skipped whole.
 *
 *  NO ALIAS GUARD.  The CRC-8 version of this decoder needed one, because
 *  ord(x) mod 0x107 = 127 < 128 data bits, so two positions 127 bits apart
 *  shared a syndrome.  For 0x11021 ord(x) = 32767 and all 384 production
 *  data-bit syndromes are DISTINCT, so the ambiguity cannot arise.  (That is
 *  what the report's always-zero alias_cmp field records.)
 *
 *  THE BUDGET IS THE RISK BOUND.  T_MAX = 131 counts RESIDUAL COMPARISONS,
 *  each of which gives a wrong candidate one 2^-16 chance of passing:
 *
 *      fa = 1 - (1 - 2^-16)^131 = 0.1997 %  per chased frame
 *
 *  That is the honest number, and it is why the enumeration may be wide
 *  (67 flip sets) while the exposure stays fixed: candidates are free,
 *  comparisons are not.  Stop at the first pass.
 *
 *  MEMORY NOTE.  The chase adds NOTHING to the decoder's footprint: it
 *  works in place on the payload' bytes and the reference set it inherited
 *  from section 7, and its per-trial state is registers and stack.  The
 *  shipped assembly goes one step further and aliases even its named
 *  temporaries onto the refine scratch, for the same reason.
 * ========================================================================== */

/* CRC-16 syndrome of payload'-relative DATA bit k: one flash table load and
 * at most seven folds -- no modular reduction at all. */
static uint16_t syndrome_of(uint16_t k)
{
    uint8_t b = (uint8_t)(7u - (k & 7u));
    uint16_t r = SYNDROME_X8[geom.data_bytes - 1u - (uint8_t)(k >> 3)];

    while (b--)
        r = crc16_times_x(r);
    return r;
}

/* Candidate i names a DATA bit; check-block bits sit at index >= data_bits.
 * Recomputed on demand rather than cached: on the target a cached flag array
 * cost 11 B of RAM and a build loop for one comparison. */
static bool candidate_is_data(uint8_t i)
{
    return dec.cand_bit[i] < geom.data_bits;
}

static uint8_t parity16(uint16_t x)
{
    x ^= (uint16_t)(x >> 8);
    x ^= (uint16_t)(x >> 4);
    x ^= (uint16_t)(x >> 2);
    x ^= (uint16_t)(x >> 1);
    return (uint8_t)(x & 1u);
}

/* Toggle payload'-relative bit k inside the payload' bytes.
 *
 * NOTE THE BIT ORDER: the payload' bytes are stored MSB first, in wire
 * order, because that is the order the CRC eats them in -- so bit k is bit
 * 7 - (k & 7), the mirror image of the packed frame's LSB-first order.  This
 * is the only place the second order appears. */
static void payload_flip(uint16_t k)
{
    pp_byte[k >> 3] ^= (uint8_t)(1u << (7u - (k & 7u)));
}

enum trial_outcome {
    TRIAL_NONE = 0,      /* did not match; keep enumerating                */
    TRIAL_ACCEPT = 1,    /* the residual matched an admitted reference     */
    TRIAL_BUDGET = 2     /* T_MAX residual comparisons spent: stop, refuse */
};

/*
 * Compare one residual against the admitted reference set.  EVERY comparison
 * is one unit of the T_MAX budget and one 2^-16 slice of exposure -- this
 * counter is the whole false-accept bound, which is why it lives here and
 * nowhere else.
 */
static enum trial_outcome residual_match(uint16_t residual)
{
    uint8_t q;

    for (q = 0; q < chk.n_refs; q++) {
        if (chk.comps >= T_MAX)
            return TRIAL_BUDGET;
        chk.comps++;
        if (residual == reference[q])
            return TRIAL_ACCEPT;
    }
    return TRIAL_NONE;
}

/*
 * Evaluate one flip set: candidate i, plus candidate j when j != NO_CANDIDATE.
 *
 * A flipped DATA bit XORs its syndrome into the residual.  A flipped CHECK
 * bit is toggled in the payload' bytes and the reference set is rebuilt --
 * the flip MOVED the reference.  On rejection the check bits are toggled
 * back and the base reference set restored; on acceptance the DATA flips are
 * applied and the check block stops mattering (only DATA is emitted), which
 * is what removes both the local copy and the restore buffer the CRC-8
 * version carried.
 */
#define NO_CANDIDATE 0xFFu

static enum trial_outcome try_flip_set(uint8_t i, uint8_t j)
{
    uint16_t residual = chk.residual_base;
    bool touched_check = false;
    enum trial_outcome outcome;

    rep.trials++;
    if (candidate_is_data(i))
        residual ^= syndrome_of(dec.cand_bit[i]);
    else {
        payload_flip(dec.cand_bit[i]);
        touched_check = true;
    }
    if (j != NO_CANDIDATE) {
        if (candidate_is_data(j))
            residual ^= syndrome_of(dec.cand_bit[j]);
        else {
            payload_flip(dec.cand_bit[j]);
            touched_check = true;
        }
    }
    if (touched_check)
        build_reference_set();

    outcome = residual_match(residual);
    if (outcome != TRIAL_ACCEPT) {
        if (touched_check) {
            if (!candidate_is_data(i))
                payload_flip(dec.cand_bit[i]);
            if (j != NO_CANDIDATE && !candidate_is_data(j))
                payload_flip(dec.cand_bit[j]);
            build_reference_set();
        }
        return outcome;
    }

    if (candidate_is_data(i))
        payload_flip(dec.cand_bit[i]);
    if (j != NO_CANDIDATE && candidate_is_data(j))
        payload_flip(dec.cand_bit[j]);
    return TRIAL_ACCEPT;
}

/* One single-flip phase: every candidate of the requested kind, in list
 * (= ascending margin) order. */
static enum trial_outcome chase_singles(bool want_data)
{
    uint8_t p;

    for (p = 0; p < chk.n_cand; p++) {
        if (candidate_is_data(p) == want_data) {
            enum trial_outcome r = try_flip_set(p, NO_CANDIDATE);
            if (r != TRIAL_NONE)
                return r;
        }
    }
    return TRIAL_NONE;
}

/* One pair phase, p < j lexicographic, selected by how many of the two are
 * DATA bits (0 = both check, 1 = mixed, 2 = both data).
 *
 * The spec's W2 bound restricts pair phases to the weakest A_PAIR
 * candidates at margin <= MG_PAIR.  At this parameter point both ceilings
 * equal A_MAX and MG_MAX, so the bound reads "pairs come only from ADMITTED
 * candidates" and every admitted pair is eligible -- the hard bound is
 * T_MAX comparisons instead.  That is why no test appears here. */
static enum trial_outcome chase_pairs(uint8_t data_count)
{
    uint8_t p, j;

    for (p = 0; p < chk.n_cand; p++) {
        for (j = (uint8_t)(p + 1u); j < chk.n_cand; j++) {
            uint8_t n_data = (uint8_t)((candidate_is_data(p) ? 1u : 0u)
                                       + (candidate_is_data(j) ? 1u : 0u));
            if (n_data == data_count) {
                enum trial_outcome r = try_flip_set(p, j);
                if (r != TRIAL_NONE)
                    return r;
            }
        }
    }
    return TRIAL_NONE;
}

/* The five phases, in order.  On acceptance *weight is 1 for a single-bit
 * repair and 2 for a pair -- the shipped decoder reports one DEC_CHASE path
 * for both, and this file's two path codes are the only place they differ.
 * skip_singles / skip_pairs are the parity gate, computed by the caller. */
static enum trial_outcome chase_all_phases(bool skip_data_singles,
                                           bool skip_data_pairs,
                                           uint8_t *weight)
{
    enum trial_outcome r;

    *weight = 1;
    r = chase_singles(false);                  /* phase 1: one check bit   */
    if (r != TRIAL_NONE)
        return r;
    *weight = 2;
    r = chase_pairs(0);                        /* phase 2: two check bits  */
    if (r != TRIAL_NONE)
        return r;
    if (!skip_data_singles) {
        *weight = 1;
        r = chase_singles(true);               /* phase 3: one data bit    */
        if (r != TRIAL_NONE)
            return r;
    }
    *weight = 2;
    r = chase_pairs(1);                        /* phase 4: data + check    */
    if (r != TRIAL_NONE)
        return r;
    if (!skip_data_pairs) {
        r = chase_pairs(2);                    /* phase 5: two data bits   */
        if (r != TRIAL_NONE)
            return r;
    }
    return TRIAL_NONE;
}

/* ==========================================================================
 *  SECTION 9 -- THE REFUSAL LADDER AND THE OUTPUT CONTRACT
 * ==========================================================================
 *
 *  In this system a frame is sent exactly once, so a refusal genuinely costs
 *  the frame.  It is still the right trade: the LEDs keep their previous
 *  colours for another 100 ms, versus displaying garbage with a valid-looking
 *  smile.  "Confidently wrong" is the only unforgivable outcome.
 *
 *      R1  lock            no usable pulses, or the fitted clock is off scale
 *      R2  marker          more than 12 of the 48 known marker bits decoded
 *                          against the template -- the strongest single
 *                          evidence that the lock is wrong.  Below the
 *                          threshold the count is fed FORWARD as confidence
 *                          instead of vetoing (it caps the reference set).
 *      R3  infeasible      more than 24 segments that no hypothesis explains
 *      R4  label error     more than 6 known-bit segments where the free
 *                          argmin disagrees with the template
 *      R6  no candidate    the check failed and the candidate list is EMPTY:
 *                          nothing to chase, and the frame is confidently
 *                          wrong.  (Equivalently n_weak == 0 and n_dw == 0.)
 *      R7  admission       the check failed and more bits are weak than the
 *                          list can hold, so the list no longer CONTAINS the
 *                          ambiguity.  Chasing a subset while paying the full
 *                          exposure is not a bargain; refusing is honest.
 *      R8  chase exhausted every admissible trial was evaluated, or the
 *                          T_MAX comparison budget ran out.
 *
 *  (R5, the n_tied "emit gate", was retired: the 16-bit check makes an
 *  emit-always policy safe, and a gate that refuses frames whose check
 *  VALIDATES contradicts the directive it served.  n_tied is still reported.)
 *
 *  Emit if and only if the ladder is clear AND either crc16(DATA) matched an
 *  admitted reference directly, or a chase trial matched it.  Never on a
 *  mismatch.
 * ========================================================================== */

/* Stages 7 and 8 plus rungs R6..R8.  Returns an RBARF_PATH_* code and, on an
 * emit, writes the nd DATA bytes to out_data. */
static uint8_t chase_stage(uint8_t *out_data)
{
    bool skip_data_singles, skip_data_pairs;
    uint8_t weight = 0, q;
    enum trial_outcome r;

    assemble_payload();

    /* n_weak / n_tied are chase INPUTS and the reference publishes them
     * here, at the chase's front door -- not from the decision pass -- so a
     * frame refused at R2..R4 reports them as zero.  Keeping the same
     * publication point is what makes the parity check exact field by field. */
    rep.n_weak = dec.n_weak;
    rep.n_tied = dec.n_tied;

    chk.residual_base = crc16_ccitt_false(pp_byte, geom.data_bytes);
    chk.comps = 0;

    /* Relaxation B's feed-forward: a marker-suspect frame keeps its per-byte
     * majority reference but is denied the split enumeration, so a suspect
     * lock cannot also buy itself 9x the per-comparison exposure.  (The
     * count is already <= MK_TOL here: R2 refused anything worse.) */
    chk.ref_cap = (rep.violations <= MK_SOFT) ? (uint8_t)REF_MAX : 1u;
    build_reference_set();
    rep.n_refs = chk.n_refs;
    rep.ref_split = (uint8_t)((chk.n_hi > 1 ? 1u : 0u)
                              + (chk.n_lo > 1 ? 1u : 0u));

    /* ---- the direct check ------------------------------------------- */
    if (residual_match(chk.residual_base) == TRIAL_ACCEPT) {
        rep.comps = chk.comps;
        memcpy(out_data, pp_byte, geom.data_bytes);
        return (uint8_t)RBARF_PATH_DIRECT;
    }

    /* ---- admission gates ------------------------------------------- */
    if (dec.n_cand == 0) {                     /* R6 */
        rep.cause = (uint8_t)RBARF_R6_NO_CANDIDATE;
        rep.comps = chk.comps;
        return (uint8_t)RBARF_PATH_NONE;
    }
    if (dec.n_weak > A_MAX) {                  /* R7 */
        rep.cause = (uint8_t)RBARF_R7_ADMISSION;
        rep.comps = chk.comps;
        return (uint8_t)RBARF_PATH_NONE;
    }
    /* Past this point the list provably holds EVERY weak bit: a dead-window
     * entry can never sort ahead of a weak one, so n_weak <= A_MAX means
     * nothing weak was evicted. */
    chk.n_cand = dec.n_cand;

    /* the parity gate: skip a data-only phase that can match no reference */
    skip_data_singles = true;                  /* weight 1 needs odd parity  */
    skip_data_pairs = true;                    /* weight 2 needs even parity */
    for (q = 0; q < chk.n_refs; q++) {
        if (parity16((uint16_t)(chk.residual_base ^ reference[q])))
            skip_data_singles = false;
        else
            skip_data_pairs = false;
    }

    rep.chased = 1;
    r = chase_all_phases(skip_data_singles, skip_data_pairs, &weight);
    rep.comps = chk.comps;
    if (r == TRIAL_ACCEPT) {
        memcpy(out_data, pp_byte, geom.data_bytes);
        return (uint8_t)((weight == 1) ? RBARF_PATH_CHASE_SINGLE
                                       : RBARF_PATH_CHASE_PAIR);
    }
    rep.cause = (uint8_t)RBARF_R8_CHASE_EXHAUSTED;   /* R8 */
    return (uint8_t)RBARF_PATH_NONE;
}

/* The whole pipeline.  Returns an RBARF_PATH_* code; `rep` carries the
 * diagnostics and out_data the emitted DATA bytes.  This is the shipped
 * ws_decode_ex(), stage for stage and rung for rung. */
static uint8_t decode_pipeline(const uint8_t *capture, uint16_t capture_len,
                               uint8_t *out_data)
{
    uint16_t t;
    uint8_t violations = 0;
    int i;

    /* --- stage 2: lock, or R1 ------------------------------------------ */
    if (!clock_seed(capture, capture_len)) {
        rep.cause = (uint8_t)RBARF_R1_LOCK;
        return (uint8_t)RBARF_PATH_NONE;
    }

    /* --- stage 3: refine, twice ---------------------------------------- */
    for (i = 0; i < 2; i++)
        clock_refine(capture, capture_len);

    /* --- stage 5: calibration owns overlay 1's histograms -------------- */
    calibrate(capture, capture_len);
    STAGE_HANDOVER(scratch);          /* fold_hist -> the packed frame     */

    /* --- stage 6: the decision pass owns both overlays' second view ---- */
    decision_pass(capture, capture_len);
    STAGE_HANDOVER(dc);               /* hypothesis_cost -> the references */

    rep.bit_period_q = clk.bit_period_q;
    rep.phase_offset = clk.phase_offset;
    rep.infeasible = dec.infeasible;
    rep.label_error = dec.label_error;
    rep.n_segments = dec.n_segments;

    /* --- the ladder ---------------------------------------------------- */
    /* The marker count: how many of the 48 known bits came out against the
     * template.  The shipped decoder XORs the two marker byte-runs against a
     * bit-reversed 6-byte template and popcounts the result, which is the
     * same number for about a fifth of the code; this loop is kept because
     * it is the definition rather than an encoding of it. */
    for (t = 0; t < geom.frame_bits; t++) {
        int8_t known = known_frame_bit(t);
        if (known >= 0 && get_bit(frame_bit, t) != (uint8_t)known)
            violations++;
    }
    rep.violations = violations;

    if (violations > MK_TOL) {                 /* R2 */
        rep.cause = (uint8_t)RBARF_R2_MARKER;
        return (uint8_t)RBARF_PATH_NONE;
    }
    if (dec.infeasible > GATE_INFEAS) {        /* R3 */
        rep.cause = (uint8_t)RBARF_R3_INFEASIBLE;
        return (uint8_t)RBARF_PATH_NONE;
    }
    if (dec.label_error > GATE_LABERR) {       /* R4 */
        rep.cause = (uint8_t)RBARF_R4_LABEL_ERROR;
        return (uint8_t)RBARF_PATH_NONE;
    }

    /* --- stages 7 and 8, and rungs R6..R8 ------------------------------ */
    return chase_stage(out_data);
}

/*
 * Copy the internal 23-byte report into the caller's rbarf_result.  Keeping
 * the two apart is what lets the internal struct be the shipped dec_info
 * byte for byte while the public API stays a single self-describing struct.
 */
static void publish(rbarf_result *out, uint8_t path)
{
    out->cause = rep.cause;
    out->path = path;
    out->trials = rep.trials;
    out->comps = rep.comps;
    out->n_refs = rep.n_refs;
    out->ref_split = rep.ref_split;
    out->chased = rep.chased;
    out->marker_violations = rep.violations;
    out->n_weak = rep.n_weak;
    out->n_tied = rep.n_tied;
    out->n_segments = rep.n_segments;
    out->infeasible = rep.infeasible;
    out->label_error = rep.label_error;
    out->bit_period_q = rep.bit_period_q;
    out->phase_offset = rep.phase_offset;
    out->n_dw = dec.n_dw;             /* a linker global on the target */
    if (path != (uint8_t)RBARF_PATH_NONE)
        out->data_len = geom.data_bytes;
}

bool rbarf_decode(const uint8_t *capture, uint16_t capture_len,
                  rbarf_result *out)
{
    uint8_t path;

    /* The output contract: everything but data[] is written on every path. */
    memset(out, 0, sizeof(*out));
    out->cause = (uint8_t)RBARF_OK;
    out->path = (uint8_t)RBARF_PATH_NONE;

    /* Deterministic, no state carried between calls: the report is cleared
     * whole (the target memsets its 23 bytes the same way), and so is the
     * one counter that lives OUTSIDE the report -- R1 returns before the
     * decision pass runs, and a stale n_dw would leak across decodes. */
    memset(&rep, 0, sizeof(rep));
    dec.n_dw = 0;

    if (geom.data_bytes == 0)
        rbarf_decoder_configure(16);           /* the default geometry */

    path = decode_pipeline(capture, capture_len, out->data);
    rep.path = path;
    publish(out, path);
    return path != (uint8_t)RBARF_PATH_NONE;
}

/* ==========================================================================
 *  THE RAM LEDGER -- this file against the shipped decoder, byte by byte
 * ==========================================================================
 *
 *  Measured with `sdcc -mstm8 --std-c99` at the production geometry
 *  (nd = 48).  The first two columns are two C implementations of the SAME
 *  representation; the third is what actually ships.
 *
 *    object                            this file   decode.c   shipped symbol
 *    ---------------------------------------------------------------------
 *    overlay 1 (fold_hist | frame)          128        128   _ov
 *    overlay 2 (costs | reference set)       32         32   _d_costs
 *    diagnostic report                       23         23   _dec_info
 *    clock fit                                4          4   _g_K, _g_tau
 *    calibration                             40         40   c_lo .. c_gap56
 *    decision counters + candidate list      60         60   _v_cand_t, _v_cand_m,
 *                                                            _v_nweak, w_tiep, ...
 *    hypothesis state (mask + 2 widths)       6          6   dq_inter, d_h0e,
 *                                                            d_h1e
 *    sample scanner + published pulse        35         35   p_*, _scan_*
 *    segment stream                          20         20   q_*
 *    check-block / chase state                8          8   ch_* (aliased)
 *    runtime geometry cache                   8          0   -- (see below)
 *    ---------------------------------------------------------------------
 *    TOTAL statics                          364        356
 *
 *  decode.c's 356 is the measured `DATA` size of its own object file at
 *  USE_ASM_DEC = 0, i.e. the host-parity build whose layout the assembly
 *  inherited.  The 8-byte difference is the WHOLE of it: `nd` is a RUNTIME
 *  parameter here, so data_bits / frame_bits / payload_hi / data_bytes /
 *  payload_bytes are RAM, while decode.c gets them from -DND_DATA at
 *  compile time and decode_asm.s reads the derived values out of flash
 *  CONST (g_NB, g_ND8, g_PPHI, g_PPB, g_PPE, g_TRB).  Nothing else differs:
 *  same objects, same element types, same element counts.
 *
 *  THE SHIPPED IMAGE counts 503 B for the same decoder -- decode_asm.rel
 *  DZP0 242 + DATA 129, plus decode_prod.rel DATA 132.  The extra 139 B is
 *  not extra STATE; it is 164 B the assembly keeps in the zero page and a C
 *  compiler keeps on the stack, less 25 B this file spends that the
 *  assembly does not:
 *
 *    ASSEMBLY-ONLY, 164 B
 *      32  d_sm[32], a suffix-min array over the hypothesis costs.  The
 *          assembly precomputes the per-bit minima into it; both C versions
 *          find them with two running minima inside the per-bit loop, which
 *          needs no array at all.
 *      70  the shared 16x16 multiply (m_a/m_b/m_p/m_y/m_s, 13 B), the 32/32
 *          divide (m_n/m_d/m_r, 12 B) and the refine regression's six 32-bit
 *          accumulators (r_lo .. r_sgn, 45 B).  Locals and registers here;
 *          zero page there because a zero-page access is one byte shorter --
 *          and the assembly then hands those same 45 bytes on to the
 *          calibration temporaries and after that to the chase's, which is
 *          the alias table at the top of decode_asm.s.
 *      46  the decision pass's named temporaries: dq_amin/amax/acap/lo/hi/
 *          ahat/afree (14), m_h/m_L/m_c/m_c0/m_c1/m_e/m_t/m_off/m_k (18),
 *          w_tieh (2) and the twelve byte-wide indices m_it .. m_m (12).
 *       9  _g_sg, the shared segment record -- a caller's local here and in
 *          decode.c.
 *       6  ss_next's m_out/m_fa/m_fb.
 *       1  m_vi, the marker violation counter (a local here).
 *
 *    THIS FILE ONLY, 25 B
 *       8  the runtime geometry cache above.
 *       8  the check-block / chase state (ch_rbase, ch_nhi, ch_nlo, ch_nref,
 *          ch_cap, ch_n, ch_comps).  The assembly ALIASES all seven onto the
 *          dead refine scratch -- the chase runs strictly after the decision
 *          pass -- so on the target they cost nothing at all.
 *       5  the scanner's in-progress pulse words (rise_lo, rise_hi, fall_lo,
 *          family: 7 B, less the assembly's own p_t sample temp, 2 B).  The
 *          assembly builds each pulse directly in the five bytes it will
 *          publish it from.
 *       4  segs.y_end, which the assembly reads from flash (g_yend).
 *
 *  So the ledger reads: the same 364 bytes of decoder STATE, plus 139 bytes
 *  the shipped decoder chooses to spend in the zero page rather than on the
 *  stack.
 *
 *  AND THE STACK IS THE OTHER HALF OF THAT SENTENCE.  A CFG walk over the
 *  SDCC-generated assembly (the analyser recon/approaches/dev_fw/
 *  stackscan2.py uses, with the callee-cleanup arg counts of SDCC 4.6's
 *  memset/memcpy supplied) puts the deepest chain at
 *
 *    this file   rbarf_decode -> decode_pipeline -> decision_pass ->
 *                build_hypotheses -> leading_ones_bounds       138 B
 *    decode.c    ws_decode_ex -> decide_pass -> decide -> a_bounds  104 B
 *    shipped     _ws_decode_ex subtree, hand assembly              12 B
 *                (13 B static worst case -- PROD_CLOSURE 14.2)
 *
 *  The +34 B over decode.c is this file's shape: more, smaller functions
 *  with explicit out-parameters where decode.c reaches for a shared global.
 *  The 12 B is the whole point of the zero page -- the assembly has almost
 *  no stack frame because its "locals" ARE those 139 bytes of statics.  Add
 *  the two columns up and the totals land within a few bytes of each other
 *  (364 + 138 = 502 against 503 + 12 = 515); the shipped split is the one
 *  that shares a 148-byte stack region with the animation engine, whose own
 *  chain needs 106 B of it.
 *
 *  The production RAM budget those 503 bytes belong to is in
 *  recon/PROD_CLOSURE.md sections 14.2 / 19.3: 875 B of statics, a 115 B
 *  peak stack, 33 B of margin in 1 024.  What actually rules this file out
 *  of a shipping image is not RAM at all -- it is 8 444 B of CODE against a
 *  7 934 B flash budget that also has to hold the capture front end, the
 *  application and the animation engine.  The shipped decoder is 5 414 B of
 *  hand assembly in that budget; decode.c compiles to 7 318 B.  Making THAT
 *  fit is what decode_asm.s is for, and it is the one thing this file does
 *  not attempt.
 * ========================================================================== */

/* ==========================================================================
 *  A DEMONSTRATION MAIN
 *  Build:  gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_DECODER_MAIN \
 *              -o rbarf_decoder rbarf_decoder.c
 *  Run:    ./rbarf_decoder [--nd 16|48] <hex-capture>
 *          ./rbarf_decoder [--nd 16|48] < capture.hex
 * ========================================================================== */
#ifdef RBARF_DECODER_MAIN

#include <stdio.h>
#include <stdlib.h>

static const char *path_name(uint8_t path)
{
    switch (path) {
    case RBARF_PATH_DIRECT:       return "direct";
    case RBARF_PATH_CHASE_SINGLE: return "chase-single";
    case RBARF_PATH_CHASE_PAIR:   return "chase-pair";
    default:                      return "none";
    }
}

static const char *cause_name(uint8_t cause)
{
    switch (cause) {
    case RBARF_OK:                   return "OK";
    case RBARF_R1_LOCK:              return "R1 lock";
    case RBARF_R2_MARKER:            return "R2 marker";
    case RBARF_R3_INFEASIBLE:        return "R3 infeasible";
    case RBARF_R4_LABEL_ERROR:       return "R4 label error";
    case RBARF_R6_NO_CANDIDATE:      return "R6 no candidate";
    case RBARF_R7_ADMISSION:         return "R7 admission";
    case RBARF_R8_CHASE_EXHAUSTED:   return "R8 chase exhausted";
    default:                         return "?";
    }
}

static int hex_nibble(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(int argc, char **argv)
{
    static uint8_t capture[4096];
    rbarf_result result;
    unsigned nd = 16, n_bytes = 0;
    int arg = 1, hi = -1, c;
    const char *hex = NULL;
    bool ok;

    while (arg < argc && argv[arg][0] == '-') {
        if (strcmp(argv[arg], "--nd") == 0 && arg + 1 < argc) {
            nd = (unsigned)atoi(argv[arg + 1]);
            arg += 2;
        } else {
            fprintf(stderr, "usage: %s [--nd 16|48] [hex-capture]\n", argv[0]);
            return 2;
        }
    }
    if (arg < argc)
        hex = argv[arg];

    /* accept the capture as an argument or on stdin; ignore whitespace */
    for (;;) {
        c = hex ? (unsigned char)*hex++ : getchar();
        if (hex && c == 0)
            break;
        if (!hex && c == EOF)
            break;
        if (c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == ':')
            continue;
        {
            int v = hex_nibble(c);
            if (v < 0) {
                fprintf(stderr, "not a hex digit: '%c'\n", c);
                return 2;
            }
            if (hi < 0) {
                hi = v;
            } else {
                if (n_bytes >= sizeof(capture)) {
                    fprintf(stderr, "capture too long\n");
                    return 2;
                }
                capture[n_bytes++] = (uint8_t)((hi << 4) | v);
                hi = -1;
            }
        }
    }
    if (n_bytes == 0) {
        fprintf(stderr, "usage: %s [--nd 16|48] [hex-capture]\n", argv[0]);
        return 2;
    }
    if (!rbarf_decoder_configure((uint8_t)nd)) {
        fprintf(stderr, "bad nd: %u\n", nd);
        return 2;
    }

    ok = rbarf_decode(capture, (uint16_t)n_bytes, &result);

    printf("capture      %u bytes (%u sampling loops)\n", n_bytes, n_bytes);
    printf("geometry     nd=%u  payload'=%u B  frame=%u bits (%u packed B)\n",
           nd, geom.payload_bytes, geom.frame_bits, frame_bytes());
    printf("clock fit    K=%u (Q11 TU/cycle, nominal %u)  tau=%d TU\n",
           result.bit_period_q, K_NOM, result.phase_offset);
    printf("segments     %u   infeasible %u   label errors %u   "
           "marker violations %u\n",
           result.n_segments, result.infeasible, result.label_error,
           result.marker_violations);
    printf("confidence   n_weak %u   n_tied %u   n_dw %u (dead-window)\n",
           result.n_weak, result.n_tied, result.n_dw);
    printf("check block  %u reference%s, %u split position%s\n",
           result.n_refs, result.n_refs == 1 ? "" : "s",
           result.ref_split, result.ref_split == 1 ? "" : "s");
    printf("chase        %s, %u flip set%s, %u/%u residual comparisons\n",
           result.chased ? "ran" : "not entered", result.trials,
           result.trials == 1 ? "" : "s", result.comps, T_MAX);
    printf("result       %s  (%s)\n", ok ? "DELIVERED" : "REFUSED",
           ok ? path_name(result.path) : cause_name(result.cause));
    if (ok) {
        unsigned p;
        printf("data         ");
        for (p = 0; p < result.data_len; p++)
            printf("%02X", result.data[p]);
        printf("\n");
    }
    return ok ? 0 : 1;
}

#endif /* RBARF_DECODER_MAIN */
