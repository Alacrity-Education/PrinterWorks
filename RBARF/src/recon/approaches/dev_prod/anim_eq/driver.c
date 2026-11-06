/* Anim-engine equivalence driver: ORIGINAL ../anim.c (June build source,
 * 4-curve gamma, on-chip presets) vs the refactored single-gamma
 * src/app/anim.c, both compiled with gcc and driven with
 * identical (48-byte frame, now_ms) inputs.
 *
 * Link: orig.o has anim_render renamed to anim_render_ref (objcopy);
 * both engines share the ws2812_in_buf / ws2812_out_buf globals defined
 * here, so each case runs ref, snapshots the 24 output bytes, runs the
 * refactored engine on the very same input, and memcmps.
 *
 * Equivalence contract proved:
 *  - kept modes (0x00 none, 0x01 blink, 0x02 fade, 0x03 sequence,
 *    unknown): byte-identical output, with the single-gamma mapping
 *    (flags[23] in 1..4 all select the one compiled-in curve, which is
 *    the original's curve #2 = gamma 2.2; 0 and >4 = off in both).
 *  - removed presets (0x04..0x09): ORIGINAL rendering the preset mode ==
 *    REFACTORED rendering the HOST-EXPANDED frame (flags[0] <- 0x03,
 *    flags[7..] <- the preset nibble bytes, everything else untouched) —
 *    this is exactly the host-side expansion contract in docs/ANIMATION_PROTOCOL.md.
 *
 * Sweeps: durations (incl. 0), masks, all 16 feature-bit combos, gamma
 * cfgs 0..5 + 255, six sequence-content shapes (empty / single / plain /
 * pauses+dups / full-32-nibble unterminated / duplicate-heavy) with
 * LCG-randomised padding beyond the terminator, three base-color fills,
 * LCG-randomised alt/bg/mask colors, and now_ms over specials + a stride
 * across 3 full cycles (incl. u16 wrap values).
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* globals both engines reference (old header declares in_buf volatile;
 * linkage is by symbol, the qualifier difference is irrelevant here) */
uint8_t ws2812_in_buf[48];
uint8_t ws2812_out_buf[24];
uint8_t ws2812_in_complete, ws2812_in_during_tx;
uint16_t millis(void) { return 0; }

void anim_render(uint16_t now_ms);       /* refactored (app/anim.c)   */
void anim_render_ref(uint16_t now_ms);   /* original   (../../anim.c) */

/* host-side preset expansion contract (docs/ANIMATION_PROTOCOL.md, byte-exact) */
static const uint8_t P4[] = {0x01, 0x57, 0x62, 0xFF};             /* spin  */
static const uint8_t P5[] = {0x26, 0x75, 0x10, 0xFF};             /* spinR */
static const uint8_t P6[] = {0x34, 0x01, 0x57, 0x62, 0xFF};       /* rain  */
static const uint8_t P7[] = {0x26, 0x75, 0x10, 0x43, 0xFF};       /* rainR */
static const uint8_t P8[] = {0x01, 0x23, 0x45, 0x67, 0xFF};       /* draw  */
static const uint8_t P9[] = {0x76, 0x54, 0x32, 0x10, 0xFF};       /* drawR */
static const struct { const uint8_t *d; uint8_t n; } PRESET[6] = {
    {P4, 4}, {P5, 4}, {P6, 5}, {P7, 5}, {P8, 5}, {P9, 5}
};

static uint32_t lcg_state = 0x12345678u;
static uint8_t lcg(void)
{
    lcg_state = lcg_state * 1664525u + 1013904223u;
    return (uint8_t)(lcg_state >> 24);
}

/* six sequence-content shapes written into flags[7..22]; padding beyond
 * the shape is LCG noise — MUST be dead by construction (terminator) */
static void fill_seq(uint8_t variant, uint8_t *fl)
{
    uint8_t i;
    for (i = 7; i <= 22; i++) fl[i] = lcg();
    switch (variant) {
    case 0: fl[7] = 0xFF; break;                          /* empty        */
    case 1: fl[7] = 0x3F; break;                          /* single led 3 */
    case 2: fl[7] = 0x01; fl[8] = 0x23; fl[9] = 0x45;
            fl[10] = 0x67; fl[11] = 0xFF; break;          /* 0..7         */
    case 3: fl[7] = 0x08; fl[8] = 0x81; fl[9] = 0x18;
            fl[10] = 0x3F; break;                         /* pauses+dups  */
    case 4: for (i = 7; i <= 22; i++) fl[i] = 0x10; break;/* 32 nibbles,
                                                             unterminated */
    case 5: fl[7] = 0x00; fl[8] = 0x00; fl[9] = 0xFF; break; /* dup-heavy */
    }
}

static void fill_base(uint8_t variant)
{
    uint8_t i;
    for (i = 0; i < 24; i++) {
        switch (variant) {
        case 0: ws2812_in_buf[i] = 0x00; break;
        case 1: ws2812_in_buf[i] = 0xFF; break;
        default: ws2812_in_buf[i] = lcg(); break;
        }
    }
}

static unsigned long n_cases, n_fail;
static uint8_t flags_ref[24], flags_new[24];

static void one_case(uint16_t t, const char *what)
{
    uint8_t out_ref[24], i;
    memcpy(ws2812_in_buf + 24, flags_ref, 24);
    memset(ws2812_out_buf, 0xEE, 24);
    anim_render_ref(t);
    memcpy(out_ref, ws2812_out_buf, 24);

    memcpy(ws2812_in_buf + 24, flags_new, 24);
    memset(ws2812_out_buf, 0xEE, 24);
    anim_render(t);

    n_cases++;
    if (memcmp(out_ref, ws2812_out_buf, 24) != 0) {
        if (++n_fail <= 10) {
            printf("MISMATCH %s t=%u\n  flags_ref:", what, t);
            for (i = 0; i < 24; i++) printf(" %02X", flags_ref[i]);
            printf("\n  flags_new:");
            for (i = 0; i < 24; i++) printf(" %02X", flags_new[i]);
            printf("\n  ref:");
            for (i = 0; i < 24; i++) printf(" %02X", out_ref[i]);
            printf("\n  new:");
            for (i = 0; i < 24; i++) printf(" %02X", ws2812_out_buf[i]);
            printf("\n");
        }
    }
}

int main(int argc, char **argv)
{
    static const uint8_t MODES[]  = {0x00, 0x01, 0x02, 0x03, 0x0A, 0xFF,
                                     0x04, 0x05, 0x06, 0x07, 0x08, 0x09};
    static const uint8_t DURS[]   = {0, 1, 3, 40, 255};
    static const uint8_t MASKS[]  = {0x00, 0x80, 0xA5, 0xFF};
    static const uint8_t GAMMAS[] = {0, 1, 2, 3, 4, 5, 255};
    uint8_t negtest = (argc > 1 && strcmp(argv[1], "--negtest") == 0);
    unsigned mi, di, ki, ft, gi, sv, bv;

    for (mi = 0; mi < sizeof MODES; mi++) {
        uint8_t mode = MODES[mi];
        uint8_t preset = (mode >= 0x04 && mode <= 0x09);
        for (di = 0; di < sizeof DURS; di++)
        for (ki = 0; ki < sizeof MASKS; ki++)
        for (ft = 0; ft < 16; ft += (mode == 0x03 || preset) ? 1 : 5)
        for (gi = 0; gi < sizeof GAMMAS; gi++)
        for (sv = 0; sv < 6; sv++)
        for (bv = 0; bv < 3; bv++) {
            uint8_t fl[24], g = GAMMAS[gi];
            uint16_t cyc, t, step, n;
            fill_base(bv);
            memset(fl, 0, 24);
            fl[0] = mode;
            fl[1] = DURS[di];
            fl[2] = MASKS[ki];
            fl[3] = lcg(); fl[4] = lcg(); fl[5] = lcg();  /* alt / bg   */
            fl[6] = (uint8_t)ft;         /* features (seq) / mask-G     */
            fill_seq((uint8_t)sv, fl);   /* seq data / mask-R,B + noise */
            fl[23] = g;

            /* refactored side input */
            memcpy(flags_new, fl, 24);
            if (preset) {                /* host-side expansion         */
                flags_new[0] = 0x03;
                memcpy(flags_new + 7, PRESET[mode - 4].d,
                       PRESET[mode - 4].n);
                if (negtest)             /* prove the harness can fail  */
                    flags_new[7] ^= 0x11;
            }

            /* original side input: identical frame; single-gamma port
             * maps cfg 1..4 onto the one compiled-in curve = original
             * curve 2 (gamma 2.2) */
            memcpy(flags_ref, fl, 24);
            if (g >= 1 && g <= 4)
                flags_ref[23] = 2;

            cyc = (uint16_t)fl[1] * 50u;
            if (cyc == 0) cyc = 50;      /* still sweep a few points    */
            step = (uint16_t)(cyc / 24u + 1u);
            for (t = 0, n = 0; n < 72; n++, t = (uint16_t)(t + step))
                one_case(t, preset ? "preset" : "kept");
            one_case(0xFFFF, "spec");
            one_case(0xFFDC, "spec");
            one_case(0x8000, "spec");
            one_case((uint16_t)(cyc - 1), "spec");
            one_case(cyc, "spec");
            one_case((uint16_t)(cyc + 1), "spec");
        }
    }

    printf("anim equivalence: %lu cases, %lu mismatches -> %s\n",
           n_cases, n_fail, n_fail ? "FAIL" : "PASS");
    return n_fail ? 1 : 0;
}
