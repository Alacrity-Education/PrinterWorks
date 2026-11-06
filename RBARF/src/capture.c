/*
 * RBARF capture firmware — WS2812 logic-analyzer acquisition.
 *
 * Oversamples the WS2812 test signal on pin 7 (PC3) into RAM using
 * cap_code.s (4 cy/sample @ 16 MHz, 8 samples/byte, 640 bytes =
 * 5120 samples = 1.184 ms), then dumps the raw buffer as hex over
 * UART1 TX (pin 8) at 9600 8N1.  No decoding on-chip: reconstruction
 * happens on the host.
 *
 * UART protocol (all lines \r\n terminated):
 *   RBARF-CAP 1        once at boot (after the 5 s SWIM window)
 *   READY              armed; the next rising edge on pin 7 captures
 *   CAP:<1280 hex>:<2 hex>   capture dump; suffix = sum of the 640
 *                            raw bytes mod 256
 *
 * Pin 8 is shared SWIM/UART1_TX: the first 5 seconds after power-on
 * leave it untouched (SWIM reflash window). Never shorten this.
 */

#include <stdint.h>

#define CLK_CKDIVR   (*(volatile uint8_t *)0x50C6)

#define UART1_SR     (*(volatile uint8_t *)0x5230)
#define UART1_DR     (*(volatile uint8_t *)0x5231)
#define UART1_BRR1   (*(volatile uint8_t *)0x5232)
#define UART1_BRR2   (*(volatile uint8_t *)0x5233)
#define UART1_CR2    (*(volatile uint8_t *)0x5235)

#define UART1_SR_TXE  0x80
#define UART1_CR2_TEN 0x08

#define CFG_GCR      (*(volatile uint8_t *)0x7F60)

#define CAP_BYTES 640

uint8_t capture_buf[CAP_BYTES];

extern void cap_code(void);   /* entry via inline asm, X = buffer */

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

static const char HEX[] = "0123456789ABCDEF";

static void uart_put_hex(uint8_t v)
{
    uart_putc(HEX[v >> 4]);
    uart_putc(HEX[v & 0x0F]);
}

void main(void)
{
    uint16_t i;
    uint8_t sum;

    CLK_CKDIVR = 0x00;          /* HSI 16 MHz, CPU divider 1 */

    delay_ms(5000);             /* SWIM flash window — pin 8 stays quiet */

    CFG_GCR = 0x01;             /* disable SWIM for the rest of the run */

    /* UART1 9600 8N1, TX only: 16 MHz / 9600 = 1667 = 0x683 */
    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;

    uart_puts("RBARF-CAP 1\r\n");

    for (;;) {
        uart_puts("READY\r\n");

        __asm
        ldw     x, #_capture_buf
        call    _cap_code
        __endasm;

        uart_puts("CAP:");
        sum = 0;
        for (i = 0; i < CAP_BYTES; i++) {
            uint8_t b = capture_buf[i];
            sum += b;
            uart_put_hex(b);
        }
        uart_putc(':');
        uart_put_hex(sum);
        uart_puts("\r\n");
    }
}
