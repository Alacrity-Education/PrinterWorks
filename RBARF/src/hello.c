/*
 * RBARF — UART hello world for STM8S001J3 (SO8N).
 *
 * Package pin 8 bonds PD1/SWIM together with PD5/UART1_TX (and PD3, PC6).
 * The first 5 seconds after power-on leave the pin untouched so the
 * ST-LINK can perform SWIM entry to reflash; only after that window is
 * UART1 TX enabled on the shared pin. Never shorten this window.
 *
 * Output: "RBARF hello #<n>" at 9600 8N1, one line every ~500 ms.
 */

#include <stdint.h>

/* Clock */
#define CLK_CKDIVR   (*(volatile uint8_t *)0x50C6)

/* UART1 */
#define UART1_SR     (*(volatile uint8_t *)0x5230)
#define UART1_DR     (*(volatile uint8_t *)0x5231)
#define UART1_BRR1   (*(volatile uint8_t *)0x5232)
#define UART1_BRR2   (*(volatile uint8_t *)0x5233)
#define UART1_CR1    (*(volatile uint8_t *)0x5234)
#define UART1_CR2    (*(volatile uint8_t *)0x5235)

#define UART1_SR_TXE  0x80
#define UART1_CR2_TEN 0x08

/* Global configuration register: bit0 SWD disables SWIM on PD1 */
#define CFG_GCR      (*(volatile uint8_t *)0x7F60)

/* ~1 ms at 16 MHz: 5333 iterations x 3 cycles (decw 1 + jrne taken 2). */
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

static void uart_put_u16(uint16_t v)
{
    char buf[5];
    uint8_t i = 0;
    do {
        buf[i++] = '0' + (v % 10);
        v /= 10;
    } while (v);
    while (i)
        uart_putc(buf[--i]);
}

void main(void)
{
    uint16_t seq = 0;

    CLK_CKDIVR = 0x00;          /* HSI 16 MHz, CPU divider 1 */

    delay_ms(5000);             /* SWIM flash window — pin 8 stays quiet */

    CFG_GCR = 0x01;             /* window over: disable SWIM so UART edges
                                   on the shared pin can't disturb it (a
                                   power-on reset re-enables SWIM) */

    /* UART1 9600 8N1, TX only. 16 MHz / 9600 = 1667 = 0x683
       -> BRR2 = 0x03 first, then BRR1 = 0x68. */
    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;

    uart_puts("RBARF hello boot\r\n");

    for (;;) {
        uart_puts("RBARF hello #");
        uart_put_u16(seq++);
        uart_puts("\r\n");
        delay_ms(500);
    }
}
