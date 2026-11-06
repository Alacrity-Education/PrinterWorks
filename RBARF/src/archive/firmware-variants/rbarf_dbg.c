/*
 * rbarf_dbg.c -- BENCH-ONLY crash-capture variant of rbarf_prod.c.
 *
 * Identical decode/render/arm pipeline (links the same PROD_RELS), plus:
 *   1. boot report  "R:<RST_SR hex>"  right after the banner, so every
 *      reset is attributed (ILLOPF = 04); RST_SR is then cleared.
 *   2. capture dump "B:<576 hex>"     the raw 288-byte capture buffer,
 *      emitted BEFORE ws_decode_ex -- when the decode crashes, the host
 *      already holds the crashing input for ucsim replay.
 *   3. no V: line (flash budget; wrong-emission checking is the VERBOSE
 *      build's job, not this one's).
 *
 * SWIM discipline, 5 s pin-8 quiet window, trim policy: unchanged.
 * Banner "RBARF-D 1" so the driver can tell the images apart.
 */

#include <stdint.h>
#include "decode.h"
#include "ws2812_in.h"
#include "ws2812_out.h"
#include "anim.h"

#define CLK_CKDIVR   (*(volatile uint8_t *)0x50C6)
#define CLK_HSITRIMR (*(volatile uint8_t *)0x50CC)
#define RST_SR       (*(volatile uint8_t *)0x50B3)

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

#define CAP_BYTES 288

uint8_t capture_buf[CAP_BYTES];
uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];

static volatile uint8_t cap_got;
static int8_t trim_v;
#define TRIM_CODE(v)  ((uint8_t)((v) & 0x07))

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

static const char HEX[] = "0123456789ABCDEF";
static void uart_put_hex(uint8_t v)
{
    uart_putc(HEX[v >> 4]);
    uart_putc(HEX[v & 0x0F]);
}

static void uart_put_i16(int16_t v)
{
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

static void auto_trim(int16_t eps_centi)
{
    int8_t v = trim_v;
    if (eps_centi > 60 && v < 3) v++;
    else if (eps_centi < -60 && v > -4) v--;
    trim_v = v;
}

static uint16_t last_render;

static void render_tick(void)
{
    uint16_t now = millis();
    if ((uint16_t)(now - last_render) >= 10) {
        last_render = now;
        anim_render(now);
        ws2812_out_send();
    }
}

void main(void)
{
    uint8_t status;
    int16_t eps;
    uint8_t rst;
    uint16_t i;

    CLK_CKDIVR = 0x00;
    CLK_HSITRIMR = 0x00;
    trim_v = 0;

    rst = RST_SR;                     /* reset cause, reported post-window */
    RST_SR = 0x1F;                    /* clear the sticky flags */

    TIM4_CR1  = 0x00;
    TIM4_PSCR = 0x07;
    TIM4_ARR  = 124;
    TIM4_SR   = 0x00;
    TIM4_IER  = 0x01;
    TIM4_CR1  = 0x01;

    ws2812_out_init();

    __asm__("rim");

    while (millis() < 5000)
        render_tick();

    CFG_GCR = 0x01;

    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;
    uart_puts("RBARF-D 1\r\n");
    uart_putc('R');
    uart_putc(':');
    uart_put_hex(rst);
    uart_puts("\r\n");

    for (;;) {
        render_tick();

        CLK_HSITRIMR = TRIM_CODE(trim_v);
        __asm
        ldw     x, #_capture_buf
        ldw     y, #288
        call    _cap_arm
        ld      _cap_got, a
        __endasm;
        CLK_HSITRIMR = 0x00;

        if (!cap_got)
            continue;

        /* dump the raw capture BEFORE decoding it (crash forensics) */
        uart_putc('B');
        uart_putc(':');
        for (i = 0; i < CAP_BYTES; i++)
            uart_put_hex(capture_buf[i]);
        uart_puts("\r\n");

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
        uart_put_i16(eps);
        uart_puts("\r\n");

        if (status == DEC_DIRECT || status == DEC_CHASE)
            auto_trim(eps);
    }
}
