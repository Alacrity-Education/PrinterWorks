/*
 * decode.h -- public interface of the v2.3 PERMISSIVE embedded decoder
 * (decode.c = C99/SDCC port of recon/approaches/embedded_v2.py).
 *
 * Build-time configuration (defaults in parentheses):
 *   ND_DATA      DATA bytes on the wire: 16 test (default) / 48 production
 *   CHECK_EN     1 (default) = frame with a repeated-CRC8 check block +
 *                chase; 0 = legacy v2.0 geometry (payload' = DATA, chase
 *                off, UNVERIFIED emit path) -- dev/bench evaluation of the
 *                pre-v2.1 trim corpus ONLY, never a shipped build
 *   CHK_LEN      check bytes on the wire when CHECK_EN=1: 6 (default,
 *                v2.3 -- (C16_HI C16_LO)x3 with INDEPENDENT per-byte
 *                majority and 3+3 markers; the production frame is
 *                60 B = exactly 20 WS2812 LEDs), or the superseded CRC8
 *                compat geometries 4 (v2.2, [CRC8]*4) / 3 (v2.1,
 *                [CRC8]*3), which keep 4+4 markers and the v2.2 gates so
 *                the captures_v2{1,2}*.json corpora reproduce exactly
 *   USE_ASM_SCAN 0 (default) = C sample scanner (host parity builds);
 *                1 = scan.s assembly scanner (STM8 target builds)
 */
#ifndef DECODE_H
#define DECODE_H

#include <stdint.h>

#ifndef ND_DATA
#define ND_DATA 16
#endif
#ifndef CHECK_EN
#define CHECK_EN 1
#endif

/* ws_decode_ex() status (== the spec's SS9.2 emit paths) */
#define DEC_REFUSE  0
#define DEC_DIRECT  1   /* crc16(DATA) matched an admitted reference      */
#define DEC_CHASE   2   /* a chase flip set matched an admitted reference
                         * inside the T_MAX residual-comparison budget    */
#define DEC_LEGACY  3   /* CHECK_EN=0 builds only: unverified emit        */

/* refusal causes (SS9.1 ladder R1..R8) */
#define CAUSE_NONE        0
#define CAUSE_LOCK        1   /* R1 no seed / K outside [K_MIN, K_MAX]    */
#define CAUSE_MARKER      2   /* R2 marker mismatches > MK_TOL (12 of 48) */
#define CAUSE_INFEASIBLE  3   /* R3 infeasible segments > 24 (v2.3)       */
#define CAUSE_LABELERR    4   /* R4 label errors > 6                      */
#define CAUSE_EMITGATE    5   /* R5 n_tied > TIE_EMIT -- RETIRED in v2.3  */
                              /*    (TIE_EMIT beyond reach; live in the   */
                              /*    v2.2/v2.1 compat builds)              */
#define CAUSE_NOCAND      6   /* R6 CRC mismatch, n_weak == 0 AND n_dw == 0*/
#define CAUSE_ADMIT       7   /* R7 CRC mismatch, n_weak > A_MAX (11)     */
#define CAUSE_CHASE       8   /* R8 chase exhausted OR the T_MAX residual-*/
                              /*    comparison budget (131) hit           */

typedef struct {
    uint8_t  path;        /* DEC_* of the last decode                     */
    uint8_t  cause;       /* CAUSE_* (CAUSE_NONE on emit)                 */
    uint8_t  trials;      /* chase flip sets residual-tested (<= 67)      */
    uint8_t  alias_cmp;   /* alias-guard compares -- ALWAYS 0 in v2.3:    */
                          /* ord(x) mod 0x11021 = 32767, so all data-bit  */
                          /* syndromes are distinct and the guard is      */
                          /* provably inert (live in the compat builds)   */
    uint8_t  chased;      /* 1 if the trial loop was entered              */
    uint16_t n_weak;      /* payload' bits with margin <= MG_MAX          */
    uint16_t n_tied;      /* payload' bits with margin == 0               */
    uint16_t K;           /* lock: Q11 TU/cycle                           */
    int16_t  tau;         /* lock offset, TU                              */
    uint8_t  violations;  /* decoded-against-template marker bits         */
    uint16_t infeasible;  /* segments with hinge cost > INFEAS_U          */
    uint16_t label_err;   /* forced-label disagreements                   */
    uint16_t n_seg;       /* segments streamed in the decision pass       */
    /* v2.3 additions (APPENDED: decode_asm.s hard-codes the offsets of
     * every field above, so nothing may be inserted before this point) */
    uint8_t  comps;       /* residual comparisons used (<= T_MAX = 131)   */
    uint8_t  n_refs;      /* references in the base set (1..REF_MAX)      */
    uint8_t  ref_split;   /* check-byte positions with NO majority (0..2) */
} dec_info_t;

/* SS6.4 (LEVER B) candidate count: payload' bits whose evidence geometry
 * is DEGENERATE and whose margin is > MG_MAX.  It is NOT a dec_info
 * field -- the target's only consumer is the R6 gate, so keeping it out
 * of the struct costs the assembly nothing and the harnesses read the
 * counter itself (it is a linker global in every build). */
extern uint16_t v_ndw;

extern dec_info_t dec_info;

/* Full decode of a raw cap_code.s capture buffer.
 * out[] receives ND_DATA bytes on DEC_DIRECT / DEC_CHASE / DEC_LEGACY and
 * is untouched on DEC_REFUSE (the application holds its previous state).
 * Deterministic; no state carried between calls. */
uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out);

/* eps of the last successful lock in centi-percent (percent * 100),
 * from SS11: eps = (K_NOM - K) / K.  Valid when dec_info.K != 0. */
int16_t dec_eps_centi(void);

#endif /* DECODE_H */
