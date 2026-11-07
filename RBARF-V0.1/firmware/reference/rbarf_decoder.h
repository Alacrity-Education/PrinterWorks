/*
 * rbarf_decoder.h -- public interface of the READABLE reference decoder
 * for the RBARF WS2812 receiver, wire protocol v2.3.
 *
 * This is a teaching / presentation copy of the algorithm that ships in
 * decode.c + decode_asm.s.  It is NOT part of the firmware build and is
 * proven bit-exact against the normative Python decoder
 * (recon/approaches/embedded_v2.py) by reference/parity_readable.py.
 *
 * WHAT IT SHARES WITH THE SHIPPED DECODER: the DATA REPRESENTATION, exactly.
 * The decoded frame is bit-packed in the shipped byte and bit order; every
 * state table has the shipped element type, count and meaning, and carries
 * the shipped symbol name in a trailing comment; stage scratch is overlaid
 * through the same two unions, with the same lifetimes; the integer widths,
 * the fixed-point scales and the truncating divisions are the target's.
 * Measured with `sdcc -mstm8 --std-c99` the decoder state is 364 B against
 * decode.c's 356 at the same geometry -- see the RAM LEDGER banner near the
 * end of rbarf_decoder.c, which itemises that gap and the shipped image's
 * 503 B byte by byte.
 *
 * WHAT STILL DIFFERS: the hot paths are C, not hand assembly, so the code is
 * bigger (8 444 B CODE + 118 B CONST, against decode.c's 7 318 + 140 and the
 * shipped assembly's 5 414 + 28) and the call tree spends on the stack what
 * decode_asm.s keeps in the zero page (a 138 B deepest chain against the
 * assembly's 12 B); `nd` is a runtime parameter rather than a build-time
 * macro, which is the entire 364-vs-356 difference; there are no build-time
 * feature forks, so the superseded v2.1/v2.2 CRC-8 geometries are absent;
 * and the marker-violation count is a per-bit loop rather than the shipped
 * byte-XOR-and-popcount (same number, no RAM either way).  The top banner of
 * rbarf_decoder.c carries the full list.
 *
 * Two calls make up the whole API:
 *
 *   rbarf_decoder_configure(nd)   pick the frame geometry: nd = 16 (the
 *                                 bring-up / test geometry, which is what
 *                                 the real-silicon corpus uses) or 48
 *                                 (production, 16 RGB LEDs).
 *   rbarf_decode(cap, len, out)   decode one raw capture buffer.
 *
 * The decoder is deterministic and carries no state between calls.
 */
#ifndef RBARF_DECODER_H
#define RBARF_DECODER_H

#include <stdint.h>
#include <stdbool.h>

/* Largest DATA field this build can hold (production geometry). */
#define RBARF_ND_MAX 48

/*
 * How the payload was obtained.  "The frame is delivered" means the
 * bytes in rbarf_result.data were verified against a CRC-16 reference
 * that travelled on the wire -- either straight away (direct) or after
 * the chase flipped one or two suspect bits (chase_single/chase_pair).
 */
enum rbarf_path {
    RBARF_PATH_NONE = 0,      /* refused -- data[] is not written        */
    RBARF_PATH_DIRECT = 1,    /* crc16(DATA) matched the reference       */
    RBARF_PATH_CHASE_SINGLE = 2,  /* one flipped bit made it match       */
    RBARF_PATH_CHASE_PAIR = 3    /* two flipped bits made it match       */
};

/*
 * The refusal ladder (spec SS9.1), evaluated in this order.  The numbers
 * are the project's R-codes and are kept as the enum values so a reader
 * can match them to EMBEDDED_V2_SPEC.md and to decode.h's CAUSE_* list.
 *
 * R5 (the n_tied "emit gate") is deliberately absent: v2.3 retired it,
 * and its threshold (8*NPP + 1 tie-decided payload bits) is larger than
 * the number of payload bits that exist, so the test is unreachable.
 */
enum rbarf_cause {
    RBARF_OK = 0,                 /* a payload was emitted               */
    RBARF_R1_LOCK = 1,            /* no usable pulses / clock off scale  */
    RBARF_R2_MARKER = 2,          /* too many header/trailer bits wrong  */
    RBARF_R3_INFEASIBLE = 3,      /* too many pulses fit no hypothesis   */
    RBARF_R4_LABEL_ERROR = 4,     /* known-bit labels disagree too often */
    RBARF_R6_NO_CANDIDATE = 6,    /* CRC mismatch, nothing to chase      */
    RBARF_R7_ADMISSION = 7,       /* CRC mismatch, weak set incomplete   */
    RBARF_R8_CHASE_EXHAUSTED = 8  /* every admissible trial failed       */
};

/*
 * The output contract.  `data`/`data_len` are written ONLY when
 * rbarf_decode() returns true; on a refusal the application must hold
 * its previous state (a frame is transmitted exactly once, so a refusal
 * is a lost frame -- but a wrong frame accepted silently is worse).
 *
 * Everything after `path` is diagnostics: the same numbers decode.h
 * exposes in dec_info, which the parity harness compares field by field
 * against the Python reference.
 */
typedef struct {
    uint8_t  data[RBARF_ND_MAX]; /* the recovered DATA bytes             */
    uint8_t  data_len;           /* == the configured nd on an emit      */
    uint8_t  cause;              /* enum rbarf_cause                     */
    uint8_t  path;               /* enum rbarf_path                      */
    uint8_t  trials;             /* chase flip sets evaluated (<= 67)    */
    uint8_t  comps;              /* residual comparisons spent (<= 131)  */
    uint8_t  n_refs;             /* references in the base set (1..9)    */
    uint8_t  ref_split;          /* check-byte positions with no majority*/
    uint8_t  chased;             /* 1 if the trial loop was entered      */
    uint8_t  marker_violations;  /* header/trailer bits decoded wrong    */
    uint8_t  reserved;           /* keeps the u16 block 2-byte aligned   */
    uint16_t n_weak;             /* payload bits with margin <= MG_MAX   */
    uint16_t n_tied;             /* payload bits with margin == 0        */
    uint16_t n_dw;              /* dead-window candidates (Lever B)      */
    uint16_t n_segments;         /* pulse segments streamed              */
    uint16_t infeasible;         /* segments whose best hypothesis is bad*/
    uint16_t label_error;        /* known-bit label disagreements        */
    uint16_t bit_period_q;       /* the clock fit: K, Q11 TU per cycle   */
    int16_t  phase_offset;       /* the clock fit: tau, TU               */
} rbarf_result;

/*
 * Select the frame geometry.  Returns false (and changes nothing) for an
 * nd the build cannot hold.  Must be called at least once before
 * rbarf_decode(); the default is the nd = 16 test geometry.
 */
bool rbarf_decoder_configure(uint8_t nd);

/*
 * Decode one raw capture buffer (the bytes the sampling loop wrote, in
 * cap_code.s layout -- see section 0 of rbarf_decoder.c).
 *
 * Returns true when a verified payload was produced, in which case
 * out->data[0 .. out->data_len-1] holds it and out->cause is RBARF_OK.
 * Returns false on a refusal, with out->cause naming the rung of the
 * ladder that fired.  out is always fully written (diagnostics included)
 * except for data[], which is untouched on a refusal.
 */
bool rbarf_decode(const uint8_t *capture, uint16_t capture_len,
                  rbarf_result *out);

#endif /* RBARF_DECODER_H */
