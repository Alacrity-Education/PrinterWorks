/*
 * rbarf_prod.c -- RBARF v2.3 PRODUCTION firmware (STM8S001J3, 16 MHz).
 *
 * Geometry: ND_DATA=48, CHK_LEN=6 (60-byte v2.3 frames, 480 bits =
 * exactly 20 WS2812 LEDs -- no pad byte exists), 288-byte capture
 * buffer (mandatory at the clock corners, spec SS3; 288 loops cover the
 * 600 us frame with ~26 loops of margin at the +8 % HSI corner).
 *
 * Main loop (single-threaded; decode NEVER runs in an ISR):
 *   render the animation at 25 Hz (TIM4 1 ms tick; 100 Hz before -- the
 *   render is a capture hole, see render_tick) -> WS2812 out on
 *   pin 5 -> arm a bounded
 *   capture window (cap_arm.s; ~1.2 ms, then the loop resumes so
 *   rendering stays alive between frames) -> on a captured frame decode
 *   it in the main loop -> on a verified emit apply the 48 DATA bytes to
 *   the anim frame buffer + nudge HSITRIMR one step toward the eps target
 *   band -> terse UART report -> re-arm.
 *
 * A refusal leaves the frame buffer untouched (the decoder only writes
 * out[] on the emit path): the LEDs hold the previous state, per SS9.4.
 *
 * BLIND WINDOW: while decoding (~50-65 ms on silicon) and reporting, no
 * capture is armed; a frame arriving then is lost (single transmission).
 * The report is deliberately terse to shrink that window:
 *     D:<status>:<eps-centi%>\r\n
 * status = O (direct CRC pass), C (chase-repaired), R<cause> (refused,
 * cause = decode.h CAUSE_* digit 1..8).  eps in centi-percent from the
 * decoder's own lock (0 when no lock).  A VERBOSE build (-DVERBOSE=1,
 * bench verification only) adds "V:<96 hex DATA>\r\n" after every
 * verified decode, and emits eps as "x<4 hex>" (raw big-endian int16)
 * instead of decimal -- the 92-B decimal printer does not fit next to
 * the V: line inside the 8 KB image (see uart_put_eps).  The shipping
 * TERSE image is unaffected and still prints decimal.
 *
 * SWIM: pin 8 bonds PD1/SWIM with PD5/UART1_TX.  The first 5 s after
 * power-on leave pin 8 quiet (SWIM reflash window) -- NEVER shortened;
 * rendering already runs during the window (LEDs alive, pin 8 silent).
 *
 * HSITRIMR: capture runs at the operating trim; ALL UART runs at factory
 * trim (TRIM_SWEEP.md discipline).  Trim moves only after a verified
 * decode, one signed step per decode, 0.6 %-wide deadband (spec SS11)
 * centred on eps = -1.0 % (NOT 0 -- see auto_trim(): eps 0 sits on the
 * fast-side emit-gate cliff; MARGIN_INVESTIGATION.md fix #1).
 *
 * millis(): TIM4 ISR (IRQ 23), prescaler 128, ARR 124 = exact 1.000 ms,
 * ported verbatim from the old ws2812_in.c tick.  The tick ISR may
 * preempt decode/render (stack budget includes it); it is masked inside
 * ws2812_out_send and during the armed capture (sim/rim burst discipline
 * in cap_arm.s), where a pending tick delivers late rather than corrupt
 * the waveform/sampling.  A capture can swallow at most one tick.
 */

#include <stdint.h>
#include "decode.h"
#include "ws2812_in.h"      /* app/ shim: frame buffer + millis() */
#include "ws2812_out.h"
#include "anim.h"

#define CLK_CKDIVR   (*(volatile uint8_t *)0x50C6)
#define CLK_HSITRIMR (*(volatile uint8_t *)0x50CC)

#define UART1_SR     (*(volatile uint8_t *)0x5230)
#define UART1_DR     (*(volatile uint8_t *)0x5231)
#define UART1_BRR1   (*(volatile uint8_t *)0x5232)
#define UART1_BRR2   (*(volatile uint8_t *)0x5233)
#define UART1_CR2    (*(volatile uint8_t *)0x5235)
#define UART1_SR_TXE  0x80
#define UART1_SR_TC   0x40
#define UART1_CR2_TEN 0x08

#define CFG_GCR      (*(volatile uint8_t *)0x7F60)

#define TIM4_CR1     (*(volatile uint8_t *)0x5340)
#define TIM4_IER     (*(volatile uint8_t *)0x5343)
#define TIM4_SR      (*(volatile uint8_t *)0x5344)
#define TIM4_PSCR    (*(volatile uint8_t *)0x5347)
#define TIM4_ARR     (*(volatile uint8_t *)0x5348)

#define CAP_BYTES 288                 /* spec SS3: +32 loops at +8 % HSI */

uint8_t capture_buf[CAP_BYTES];
uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];   /* decoded frame -> anim */

static volatile uint8_t cap_got;      /* cap_arm result (inline-asm glue) */
static int8_t trim_v;                 /* current signed 3-bit trim value */
#define TRIM_CODE(v)  ((uint8_t)((v) & 0x07))

/* TIM4 millis tick: app/tick.c (own module so THIS one declares no
 * __interrupt -- vectors_prod.s hand-packs the table) */

/* ---- UART (always at factory trim) ----------------------------------- */

static void uart_putc(char c)
{
    while (!(UART1_SR & UART1_SR_TXE))
        ;
    UART1_DR = (uint8_t)c;
}

static void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

#if VERBOSE
static void uart_put_nib(uint8_t d)
{
    /* table-free: the 17-B "0123..F" CONST table did not fit once the
     * v2.2 majority-of-4 vote grew the decoder (flash ledger) */
    d = (uint8_t)(d + '0');
    if (d > '9')
        d = (uint8_t)(d + ('A' - '0' - 10));
    uart_putc((char)d);
}
static void uart_put_hex(uint8_t v)
{
    uart_put_nib((uint8_t)(v >> 4));
    uart_put_nib((uint8_t)(v & 0x0F));
}
/* eps as 'x' + 4 hex digits (raw two's-complement int16, big-endian).
 * BENCH-IMAGE-ONLY formatting.  The decimal printer below costs 92 B
 * (84 B of code + its 8-B power-of-ten table) and the VERBOSE image has
 * no room for it alongside the V: line -- with it the link ends 0x9F94,
 * 46 B past CAPARM0, i.e. on top of the cycle-calibrated capture block
 * (guard_prod.py refuses it).  Reusing the hex printer the V: line
 * already needs costs 6 B instead.  The 'x' sentinel keeps the two
 * formats unambiguous ("x FF97" vs "-105"); the SHIPPING TERSE image is
 * unchanged and still emits decimal. */
static void uart_put_eps(int16_t v)
{
    uart_putc('x');
    uart_put_hex((uint8_t)((uint16_t)v >> 8));
    uart_put_hex((uint8_t)((uint16_t)v & 0xFFu));
}
#else

static void uart_put_i16(int16_t v)
{
    /* eps range is +-1645 centi-%: subtract-powers decimal emit with
     * leading-zero suppression (no 16-bit div/mod library call) */
    static const uint16_t P[4] = {10000, 1000, 100, 10};
    uint16_t u;
    uint8_t i, d, seen = 0;
    if (v < 0) { uart_putc('-'); u = (uint16_t)(-v); }
    else u = (uint16_t)v;
    for (i = 0; i < 4; i++) {
        d = 0;
        while (u >= P[i]) { u -= P[i]; d++; }
        if (d || seen) { uart_putc((char)('0' + d)); seen = 1; }
    }
    uart_putc((char)('0' + (uint8_t)u));
}
#endif

/* ---- opportunistic HSITRIMR nudge (spec SS11) ------------------------ */

static void auto_trim(int16_t eps_centi)
{
    /* One step toward the TARGET BAND eps in [-1.6 %, -0.4 %] -- centred
     * on -1.0 %, same ~0.6 %-wide deadband as before, just re-centred
     * (MARGIN_INVESTIGATION.md fix #1; constants only, no new code).
     *
     * Centring on eps 0 parked this unit on code 7 (+0.02 % cold,
     * +0.15..+0.33 % warm), i.e. ON the fast-side emit-gate cliff at
     * eps ~ +0.1 %: 14/30 delivered, 7-8 of them chase-repaired.  The
     * delivery plateau is 85-96 % from -0.05 % all the way to -2.2 %,
     * and 1.16 %/step granularity means the only two reachable points
     * near zero are code 0 (-1.07 %) and code 7 (+0.02 %).  Targeting
     * the band picks code 0 -- dead centre of the plateau, ~1.1 % of
     * thermal headroom to the cliff and ~1.2 % to the -2.3 % swallow
     * edge -- measured 24/30 cold and 25/30 warm on this unit, all
     * DIRECT (0-1 chase), which also collapses the chase false-accept
     * surface that lives on the fast side.
     *
     * Unit-agnostic: it targets an eps band, not a trim code.
     * Increasing the signed value SLOWS the clock (eps down). */
    int8_t v = trim_v;
    if (eps_centi > -40 && v < 3) v++;          /* faster than -0.4 % -> slow it */
    else if (eps_centi < -160 && v > -4) v--;   /* slower than -1.6 % -> speed up */
    trim_v = v;                                 /* applied on next arm   */
}

/* ---- render tick: 25 Hz (was 100 Hz) --------------------------------
 *
 * THE RENDER IS A CAPTURE HOLE (ARM_INVESTIGATION.md SS4, SS6 fix #2).
 * anim_render + ws2812_out_send take a measured 400..658 us (p50 556) and
 * the chip is NOT armed for any of it; at the old flat 100 Hz that is a
 * 5.56 % duty cycle, and a frame whose burst STARTS inside the hole is
 * lost: 5.13 % of captures came out head-chopped (spans 11..476 bits of
 * 479), 18 of the 22 mid-render arms refused, and NO chopped burst has
 * ever decoded.  The waveform is uninterruptible (ws2812_out_send
 * bit-bangs 192 bits under sim) so the hole cannot be shortened -- only
 * made rarer, and the loss scales with the duty cycle:
 *
 *      100 Hz  5.56 % duty  ->  5.13 pp of delivery lost   (measured)
 *       50 Hz  2.78 %       ->  2.57 pp
 *   ** 25 Hz   1.39 %       ->  1.28 pp  (RENDER_MS 40, this build)
 *
 * 25 Hz costs nothing in animation quality here: the fastest animation
 * the protocol can ask for is f[1] = 1 -> a 50 ms cycle, but the real
 * production frames run 1000 ms (blink) to 2000 ms (fade) cycles
 * (anim.c: cycle = f[1] * 50 ms), i.e. 25..50 renders per cycle, and
 * WS2812 pixels hold their value between renders (no PWM flicker).
 *
 * NOT TAKEN, and why: skipping the render entirely while the animation is
 * STATIC (modes other than 01/02/03 all fall to anim_none, so re-sending
 * changes nothing) with a 512 ms heartbeat would cut the duty to 1.71 %
 * at 50 Hz -- worth +0.15 pp over this flat 25 Hz on the 10-frame gate
 * mix (4 static / 6 dynamic) and much more in the field, where the strip
 * is usually static.  It costs +23 B of flash (measured: dev_fe/ab.sh),
 * which the 8 KB image does not have (21 B free terse / 25 B verbose)
 * without spending a decoder size lever on 0.15 pp.  It is the next
 * render-hole lever if one is ever needed.
 */
#define RENDER_MS  40

static uint16_t last_render;

static void render_tick(void)
{
    uint16_t now = millis();
    if ((uint16_t)(now - last_render) >= RENDER_MS) {
        last_render = now;
        anim_render(now);
        ws2812_out_send();            /* ~304 us, tick-masked inside */
    }
}

void main(void)
{
    uint8_t status;
    int16_t eps;

    CLK_CKDIVR = 0x00;                /* HSI 16 MHz, dividers 1 */
    CLK_HSITRIMR = 0x00;              /* factory trim (explicit) */
    trim_v = 0;

    TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
    TIM4_PSCR = 0x07;
    TIM4_ARR  = 124;
    TIM4_SR   = 0x00;
    TIM4_IER  = 0x01;
    TIM4_CR1  = 0x01;

    ws2812_out_init();

    /* boot frame state: all dark, mode 0 (host owns the state) */
    /* (ws2812_in_buf is zero-initialised by the SDCC startup)   */

    __asm__("rim");

    /* SWIM reflash window: pin 8 quiet for the first 5 s; the LEDs
     * already render (pin 5 only) */
    while (millis() < 5000)
        render_tick();

    CFG_GCR = 0x01;                   /* activation level: SWIM off */

    /* UART1 9600 8N1, TX only: 16 MHz / 9600 = 0x683 */
    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;
    uart_puts("RBARF-P 1\r\n");

    for (;;) {
        render_tick();

        /* armed capture window (~1.2 ms) at the operating trim */
        CLK_HSITRIMR = TRIM_CODE(trim_v);
        __asm
        ldw     x, #_capture_buf
        ldw     y, #288
        call    _cap_arm
        ld      _cap_got, a
        __endasm;
        CLK_HSITRIMR = 0x00;          /* factory trim before any UART */

        if (!cap_got)
            continue;                 /* no frame: keep rendering */

        /* decode in the main loop (BLIND WINDOW until re-armed).
         * ws2812_in_buf is written ONLY on a verified emit: a refusal
         * holds the previous frame (spec SS9.4). */
        status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
        eps = (dec_info.K != 0) ? dec_eps_centi() : 0;

        uart_putc('D');
        uart_putc(':');
        if (status == DEC_DIRECT)     uart_putc('O');
        else if (status == DEC_CHASE) uart_putc('C');
        else {
            uart_putc('R');
            uart_putc((char)('0' + dec_info.cause));
        }
        uart_putc(':');
#if VERBOSE
        uart_put_eps(eps);
#else
        uart_put_i16(eps);
#endif
        uart_puts("\r\n");

        if (status == DEC_DIRECT || status == DEC_CHASE) {
#if VERBOSE
            uint8_t i;
            uart_putc('V');
            uart_putc(':');
            for (i = 0; i < 48; i++)
                uart_put_hex(ws2812_in_buf[i]);
            uart_puts("\r\n");
#endif
            auto_trim(eps);           /* only after a verified decode */
        }
    }
}
