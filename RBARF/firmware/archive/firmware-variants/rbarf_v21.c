/*
 * rbarf_v21.c -- RBARF v2.1 receiver firmware (STM8S001J3, 16 MHz).
 *
 * Production-shaped decode firmware: oversample a WS2812 v2.1 frame into
 * a 256-byte buffer (scan.s _cap_capture, the cap_code.s sampler at 256
 * loops), decode it on-chip (decode.c, the bit-exact port of
 * recon/approaches/embedded_v2.py), report the result over UART, then
 * re-arm.  Test geometry: ND_DATA = 16 -> 216-bit v2.1 frame, so the
 * report carries 32 hex data chars (this is the bench build; a
 * production build sets ND_DATA=48 and CAP_BYTES=288, spec SS3).
 *
 * UART protocol (9600 8N1, TX only on pin 8, all \r\n):
 *   RBARF-V21 1                          once at boot
 *   READY                                armed; next rising edge captures
 *   DEC:<32 hex data>:<eps>:<status>     decode report, one per frame
 *       data   16 DATA bytes (32 hex); 32 zeros on REFUSE
 *       eps    lock clock error in centi-percent (signed, e.g. -107)
 *       status OK (direct) | CHASED (CRC8 chase) | REFUSE (missed frame)
 *   TIM:<ticks>                          ws_decode_ex duration, on-chip
 *       TIM1 @ f_CPU/256: 1 tick = 16 us at nominal 16 MHz (bench
 *       diagnostic line; the DEC format above stays exactly as specified)
 *
 * DECODE TIME IS A BLIND WINDOW: while decoding, no capture is armed, so
 * a frame arriving during the decode is silently lost (single
 * transmission -- no repeats cover it).  The host must respect a minimum
 * inter-frame gap >= decode time + report time; task-5 measures it.
 *
 * SWIM: pin 8 bonds PD1/SWIM with PD5/UART1_TX.  The first 5 s after
 * power-on leave pin 8 quiet (SWIM reflash window) -- NEVER shortened.
 *
 * HSITRIMR opportunistic auto-trim (spec SS11): after a verified (OK or
 * CHASED) decode only, nudge CLK_HSITRIMR one step toward eps 0 from the
 * decoder's own clock measurement.  UART always runs at factory trim
 * (0x00); the operating trim is applied only around the capture, exactly
 * as the trim-sweep firmware did (TRIM_SWEEP.md: 96/96 dumps clean).
 * Never trim on a refusal (the eps came from a lock the decoder
 * declined).  Signed 3-bit two's-complement code, -1.16 %/step, deadband
 * 0.6 %, one step per decode (the "hysteresis of one step").
 */

#include <stdint.h>
#include "decode.h"

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

/* TIM1 (same register map on every STM8S variant) times the decode:
 * prescaler /256 -> 16 us/tick at 16 MHz, 16-bit range 1.05 s. */
#define TIM1_CR1     (*(volatile uint8_t *)0x5250)
#define TIM1_EGR     (*(volatile uint8_t *)0x5257)
#define TIM1_CNTRH   (*(volatile uint8_t *)0x525E)
#define TIM1_CNTRL   (*(volatile uint8_t *)0x525F)
#define TIM1_PSCRH   (*(volatile uint8_t *)0x5260)
#define TIM1_PSCRL   (*(volatile uint8_t *)0x5261)

#define CAP_BYTES 256                 /* task-specified bench buffer */

uint8_t capture_buf[CAP_BYTES];
static uint8_t data_out[ND_DATA];

extern void cap_capture(void);        /* scan.s: X = buffer, 256 loops */

/* ---- HSITRIMR auto-trim state (SS11) --------------------------------- */
static int8_t trim_v;                 /* current signed 3-bit trim value */

/* signed value -> CLK_HSITRIMR code (3-bit two's complement) */
#define TRIM_CODE(v)  ((uint8_t)((v) & 0x07))

/* ---- timing ---------------------------------------------------------- */
static void delay_1ms(void)
{
    __asm
    pushw   x
    ldw     x, #5333
0001$:
    decw    x
    jrne    0001$
    popw    x
    __endasm;
}

static void delay_ms(uint16_t ms)
{
    while (ms--)
        delay_1ms();
}

/* ---- UART (all at factory trim) ------------------------------------- */
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

static void uart_drain(void)
{
    /* TC = shifter empty; only then is it safe to change the HSI trim
     * (the UART baud source) without corrupting the last byte. */
    while (!(UART1_SR & UART1_SR_TC))
        ;
}

static const char HEX[] = "0123456789ABCDEF";

static void uart_put_hex(uint8_t v)
{
    uart_putc(HEX[v >> 4]);
    uart_putc(HEX[v & 0x0F]);
}

static void uart_put_i16(int16_t v)
{
    char buf[6];
    uint8_t i = 0;
    uint16_t u;
    if (v < 0) { uart_putc('-'); u = (uint16_t)(-v); }
    else u = (uint16_t)v;
    do {
        buf[i++] = (char)('0' + (u % 10));
        u /= 10;
    } while (u);
    while (i)
        uart_putc(buf[--i]);
}

/* ---- opportunistic HSITRIMR nudge (SS11) ---------------------------- */
static void auto_trim(int16_t eps_centi)
{
    /* one step toward eps 0; 1.16 %/step = 116 centi-%, deadband 0.6 %
     * = 60 centi-%.  Increasing the signed trim value SLOWS the clock
     * (eps down); decreasing it speeds it up (eps up). */
    int8_t v = trim_v;
    if (eps_centi > 60 && v < 3) v++;         /* clock fast -> slow it  */
    else if (eps_centi < -60 && v > -4) v--;  /* clock slow -> speed up */
    trim_v = v;                                /* applied next capture   */
}

void main(void)
{
    uint16_t i;
    uint8_t status;
    int16_t eps;
    uint16_t ticks;

    CLK_CKDIVR = 0x00;              /* HSI 16 MHz, CPU divider 1 */
    CLK_HSITRIMR = 0x00;           /* factory trim (explicit) */
    trim_v = 0;

    delay_ms(5000);                /* SWIM flash window -- pin 8 quiet */

    CFG_GCR = 0x01;                /* disable SWIM for the rest of the run */

    /* TIM1 decode stopwatch: /256 prescaler, force-loaded by UG (the
     * prescaler registers are preloaded and only transfer on an update
     * event), counter left stopped between decodes. */
    TIM1_CR1 = 0x00;
    TIM1_PSCRH = 0x00;
    TIM1_PSCRL = 0xFF;             /* f_CPU / (255 + 1) */
    TIM1_EGR = 0x01;               /* UG: load PSCR, reset counter */

    /* UART1 9600 8N1, TX only: 16 MHz / 9600 = 1667 = 0x683 */
    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;

    uart_puts("RBARF-V21 1\r\n");

    for (;;) {
        uart_puts("READY\r\n");
        uart_drain();              /* last bit fully on the wire */

        /* capture at the operating trim */
        CLK_HSITRIMR = TRIM_CODE(trim_v);
        __asm
        ldw     x, #_capture_buf
        call    _cap_capture
        __endasm;
        CLK_HSITRIMR = 0x00;       /* restore factory trim before any UART */

        /* decode (BLIND WINDOW: no capture armed until the next READY) */
        TIM1_EGR = 0x01;           /* reset counter (reloads PSCR too) */
        TIM1_CR1 = 0x01;           /* CEN */
        status = ws_decode_ex(capture_buf, CAP_BYTES, data_out);
        TIM1_CR1 = 0x00;           /* stop before reading (no tearing) */
        ticks = (uint16_t)(((uint16_t)TIM1_CNTRH << 8) | TIM1_CNTRL);
        eps = (dec_info.K != 0) ? dec_eps_centi() : 0;

        uart_puts("DEC:");
        if (status == DEC_DIRECT || status == DEC_CHASE) {
            for (i = 0; i < ND_DATA; i++)
                uart_put_hex(data_out[i]);
        } else {
            for (i = 0; i < ND_DATA; i++)
                uart_puts("00");
        }
        uart_putc(':');
        uart_put_i16(eps);
        uart_putc(':');
        if (status == DEC_DIRECT)      uart_puts("OK");
        else if (status == DEC_CHASE)  uart_puts("CHASED");
        else                           uart_puts("REFUSE");
        uart_puts("\r\n");

        uart_puts("TIM:");
        uart_put_i16((int16_t)ticks); /* decode < 1.05 s: sign bit unused */
        uart_puts("\r\n");

        /* nudge only after a CRC-verified decode (SS11) */
        if (status == DEC_DIRECT || status == DEC_CHASE)
            auto_trim(eps);
    }
}
