/*
 * rbarf_bc.c -- BENCH-ONLY breadcrumb variant of rbarf_prod.c.
 *
 * Same pipeline as rbarf_prod.c, plus a stage breadcrumb (crumb.s, ABS
 * RAM at 0x0360 that survives a warm reset) written immediately before
 * each stage.  On the illegal-opcode reset the last-written crumb points
 * at the faulting stage, and is reported at the next boot:
 *
 *     "RBARF-B 1"
 *     "R:<RST_SR> C:<crumb> S:<sub> M:<1 if magic valid>"
 *
 *   crumb  0x10 loop-top/render entry   0x11 anim_render   0x12 ws out
 *          0x13 render done             0x20 pre cap_arm   0x21 post cap_arm
 *          0x22 no-frame continue       0x40 pre decode    0x50 post decode
 *          0x60 report done
 *   sub    cap_got after arm; decode status after decode
 *
 * No capture dump (the crash-capture build rbarf_dbg.c already proved the
 * decoder never faults after a dump).  Banner "RBARF-B 1".
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

extern volatile uint8_t crumb, crumb_sub;
extern volatile uint16_t crumb_magic;

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

/* eps report + auto_trim dropped from THIS build for flash budget: the
 * crash path is capture/arm/decode, not the post-decode report, and the
 * debug build already showed the fault is independent of it.  Factory
 * trim throughout (trim_v stays 0), matching the verbose build's first
 * decode after every reset -- which still reset. */

static uint16_t last_render;

static void render_tick(void)
{
    uint16_t now = millis();
    if ((uint16_t)(now - last_render) >= 10) {
        last_render = now;
        crumb = 0x11; anim_render(now);
        crumb = 0x12; ws2812_out_send();
        crumb = 0x13;
    }
}

void main(void)
{
    uint8_t status;
    uint8_t rst, c0, s0;
    uint16_t m0;

    CLK_CKDIVR = 0x00;
    CLK_HSITRIMR = 0x00;
    trim_v = 0;

    rst = RST_SR;
    RST_SR = 0x1F;
    c0 = crumb; s0 = crumb_sub; m0 = crumb_magic;   /* survivors */
    crumb_magic = 0xC0DE;
    crumb = 0x00; crumb_sub = 0x00;

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
    uart_puts("RBARF-B 1\r\n");
    uart_putc('R'); uart_putc(':'); uart_put_hex(rst);
    uart_putc(' '); uart_putc('C'); uart_putc(':'); uart_put_hex(c0);
    uart_putc(' '); uart_putc('S'); uart_putc(':'); uart_put_hex(s0);
    uart_putc(' '); uart_putc('M'); uart_putc(':');
    uart_putc((m0 == 0xC0DE) ? '1' : '0');
    uart_puts("\r\n");

    for (;;) {
        crumb = 0x10;
        render_tick();

        crumb = 0x20;
        CLK_HSITRIMR = TRIM_CODE(trim_v);
        __asm
        ldw     x, #_capture_buf
        ldw     y, #288
        call    _cap_arm
        ld      _cap_got, a
        __endasm;
        crumb = 0x21; crumb_sub = cap_got;
        CLK_HSITRIMR = 0x00;

        if (!cap_got) {
            crumb = 0x22;
            continue;
        }

        crumb = 0x40;
        status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
        crumb = 0x50; crumb_sub = status;

        uart_putc('D');
        uart_putc(':');
        if (status == DEC_DIRECT)     uart_putc('O');
        else if (status == DEC_CHASE) uart_putc('C');
        else {
            uart_putc('R');
            uart_putc((char)('0' + dec_info.cause));
        }
        uart_puts("\r\n");
        crumb = 0x60;
    }
}
