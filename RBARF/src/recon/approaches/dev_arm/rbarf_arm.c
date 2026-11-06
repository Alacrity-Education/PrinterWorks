/*
 * rbarf_arm.c -- BENCH-ONLY arm-diagnostic image (ARM_INVESTIGATION.md).
 * NOT A SHIPPING FILE.  Lives in recon/approaches/dev_arm/ and is linked
 * against the UNMODIFIED production .rel set (decode_asm.s, decode.c,
 * caploop.s, cap_arm.s, anim.c, ws2812_out.c, tick.c, vectors_prod.s).
 *
 * = rbarf_prod.c's main loop with (a) a fixed-format hex telemetry line
 * for EVERY captured frame and (b) the raw 288-byte capture dumped for
 * every REFUSAL plus every 4th capture (success controls).
 *
 *   A<28 hex>      14 telemetry bytes, always
 *        [0] (status<<4)|cause     status 0=refuse 1=direct 2=chase
 *        [1..2] eps, centi-%, big-endian int16 (0 when no lock)
 *        [3..4] TIM2 us stamp at ARM ENTRY      (1 MHz, wraps 65.536 ms)
 *        [5..6] TIM2 us stamp at ARM RETURN
 *        [7..8] TIM2 us stamp at the last RENDER START
 *        [9..10] TIM2 us stamp at the last RENDER END
 *        [11]   cap_arm calls that TIMED OUT since the last capture (sat.)
 *        [12..13] TIM2 us stamp at the PREVIOUS arm RETURN, so
 *               [3..4]-[12..13] = the UNARMED gap right before this
 *               capture's arm window (render_tick + any render inside it)
 *   B<576 hex>     the raw capture_buf, refusals + every 4th capture
 *
 * Derived host-side (zero flash): pulse count, head/tail chop, t0 and eps
 * fit, and hence which of the 4 BTJT polls caught the edge (they are 2 cy
 * = 125 ns apart, and the t0 fit resolves better than that).
 *
 * FLASH LEVERS taken to fit next to the 288-byte dump (26 B of REL slack
 * below CAPARM0 in the verbose image):
 *   1. eps as raw hex inside the telemetry block -- the SS15.0 lever, the
 *      92 B decimal printer (uart_put_i16 + its table) drops out;
 *   2. no `V:` DATA line: the dump + the bit-exact host decoder recover the
 *      emitted bytes, so the 48-byte hex loop is unnecessary here;
 *   3. no status/cause/':' character formatting -- ONE uart_blk() loop
 *      emits the whole fixed-width block;
 *   4. no auto_trim(): SS15.2 measured trim_v == code 0 for 1634/1634
 *      verified decodes (the retargeted deadband makes factory trim a
 *      fixed point on this unit), so CLK_HSITRIMR stays 0x00 and the
 *      operating point is bit-identical to the shipping image's.
 * UART runs at 38400 (not 9600) so a 288-byte dump costs 150 ms instead
 * of 600 ms; the host re-decodes every dump and compares the verdict with
 * the chip's, which is also the dump-integrity check.
 *
 * UNCHANGED from rbarf_prod.c: the 5 s pin-8 SWIM quiet window, TIM4 1 ms
 * tick + 100 Hz render + ws2812_out_send, the armed capture call
 * (X=capture_buf, Y=288, call _cap_arm), the decoder, the operating trim.
 * TIM2 is added as a free-running 1 MHz timestamp source (no interrupt).
 */

#include <stdint.h>
#include "decode.h"
#include "ws2812_in.h"
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
#define UART1_CR2_TEN 0x08

#define CFG_GCR      (*(volatile uint8_t *)0x7F60)

#define TIM4_CR1     (*(volatile uint8_t *)0x5340)
#define TIM4_IER     (*(volatile uint8_t *)0x5343)
#define TIM4_SR      (*(volatile uint8_t *)0x5344)
#define TIM4_PSCR    (*(volatile uint8_t *)0x5347)
#define TIM4_ARR     (*(volatile uint8_t *)0x5348)

/* TIM2: free-running 16-bit us timebase, no interrupt, never read by the
 * capture path (the pinned block is untouched) */
#define TIM2_CR1     (*(volatile uint8_t *)0x5300)
#define TIM2_CNTRH   (*(volatile uint8_t *)0x530C)
#define TIM2_CNTRL   (*(volatile uint8_t *)0x530D)
#define TIM2_PSCR    (*(volatile uint8_t *)0x530E)
#define TIM2_ARRH    (*(volatile uint8_t *)0x530F)
#define TIM2_ARRL    (*(volatile uint8_t *)0x5310)

#define CAP_BYTES 288

uint8_t capture_buf[CAP_BYTES];
uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];

static volatile uint8_t cap_got;
static uint8_t tl[14];                /* telemetry block (hex-emitted) */
static uint8_t nok;                   /* captures, for success sampling */

/* ---- UART (factory trim throughout; == the operating trim on this unit) */

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

static void uart_nib(uint8_t d)
{
    d = (uint8_t)(d + '0');
    if (d > '9')
        d = (uint8_t)(d + 7);         /* 'A' - '0' - 10 */
    uart_putc((char)d);
}

static void uart_blk(const uint8_t *p, uint16_t n)
{
    while (n--) {
        uart_nib((uint8_t)(*p >> 4));
        uart_nib((uint8_t)(*p & 0x0F));
        p++;
    }
}

/* TIM2 read: CNTRH first (it latches CNTRL in hardware), then CNTRL */
static void stamp(uint8_t i)
{
    tl[i] = TIM2_CNTRH;
    tl[i + 1] = TIM2_CNTRL;
}

/* ---- 100 Hz render tick, stamped ------------------------------------- */

static uint16_t last_render;

static void render_tick(void)
{
    uint16_t now = millis();
    if ((uint16_t)(now - last_render) >= 10) {
        last_render = now;
        stamp(7);                     /* render START */
        anim_render(now);
        ws2812_out_send();            /* ~545 us, tick-masked inside */
        stamp(9);                     /* render END */
    }
}

void main(void)
{
    uint8_t status;
    int16_t eps;

    CLK_CKDIVR = 0x00;
    CLK_HSITRIMR = 0x00;              /* factory == operating trim (code 0) */

    TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
    TIM4_PSCR = 0x07;
    TIM4_ARR  = 124;
    TIM4_SR   = 0x00;
    TIM4_IER  = 0x01;
    TIM4_CR1  = 0x01;

    TIM2_CR1  = 0x00;                 /* us timebase: /16 = 1 MHz, free run */
    TIM2_PSCR = 0x04;
    TIM2_ARRH = 0xFF;
    TIM2_ARRL = 0xFF;
    TIM2_CR1  = 0x01;

    ws2812_out_init();

    __asm__("rim");

    while (millis() < 5000)           /* SWIM reflash window: pin 8 quiet */
        render_tick();

    CFG_GCR = 0x01;

    UART1_BRR2 = 0x01;                /* 38400: 16 MHz / 38400 = 0x1A1 */
    UART1_BRR1 = 0x1A;
    UART1_CR2  = UART1_CR2_TEN;
    uart_puts("RBARF-A 1\r\n");

    for (;;) {
        tl[12] = tl[5];               /* PREVIOUS arm return -> the unarmed */
        tl[13] = tl[6];               /* gap ends at this arm's entry stamp */
        render_tick();

        stamp(3);                     /* ARM ENTRY */
        __asm
        ldw     x, #_capture_buf
        ldw     y, #288
        call    _cap_arm
        ld      _cap_got, a
        __endasm;
        stamp(5);                     /* ARM RETURN */

        if (!cap_got) {
            if (tl[11] != 0xFF)
                tl[11]++;
            continue;
        }

        status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
        eps = (dec_info.K != 0) ? dec_eps_centi() : 0;
        tl[0] = (uint8_t)(((uint8_t)(status << 4)) | dec_info.cause);
        tl[1] = (uint8_t)((uint16_t)eps >> 8);
        tl[2] = (uint8_t)((uint16_t)eps & 0xFFu);

        uart_putc('A');
        uart_blk(tl, 14);
        uart_puts("\r\n");

        nok++;
        if (status == DEC_REFUSE || (nok & 3) == 0) {
            uart_putc('B');
            uart_blk(capture_buf, CAP_BYTES);
            uart_puts("\r\n");
        }
        tl[11] = 0;
    }
}
