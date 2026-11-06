/*
 * RBARF capture_trim firmware — CLK_HSITRIMR trim-sweep acquisition.
 *
 * Variant of capture.c: identical WS2812 oversampling via cap_code.s,
 * but each capture runs with a different HSI trim code (CLK_HSITRIMR,
 * 0x50CC).  Default option-byte config = 3-bit trimming, codes 0..7;
 * the firmware cycles 0,1,...,7,0,1,... forever, one capture per code.
 * The code->frequency mapping is deliberately NOT assumed here — the
 * host measures the effect from the captures.
 *
 * UART (9600 baud) derives from HSI, so a large trim would corrupt the
 * dump.  Therefore ALL UART output happens at factory trim
 * (CLK_HSITRIMR = 0x00); the sweep trim is applied only around the
 * capture itself:
 *
 *   print "TRIM:<code>"          (factory trim)
 *   print "READY"                (factory trim)
 *   drain UART shifter (TC)      — last bit fully on the wire
 *   CLK_HSITRIMR = code
 *   cap_code()                   — sampling runs at the trimmed clock
 *   CLK_HSITRIMR = 0x00          (restore factory trim)
 *   print "CAP:<1280 hex>:<2 hex sum>"
 *
 * Everything else matches capture.c exactly: CLK_CKDIVR = 0 (16 MHz),
 * the 5 s pin-8 quiet window BEFORE any UART/GPIO config (mandatory
 * SWIM reflash window — never shorten), CFG_GCR = 0x01 after the
 * window, 640-byte buffer, same dump format.
 *
 * Boot banner: RBARF-CAPTRIM 1
 */

#include <stdint.h>

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

static void uart_drain(void)
{
    /* Wait for Transmission Complete: TXE only says the data register
     * is free; TC says the shifter finished the last stop bit.  Only
     * then is it safe to change the HSI trim (baud source). */
    while (!(UART1_SR & UART1_SR_TC))
        ;
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
    uint8_t trim = 0;

    CLK_CKDIVR = 0x00;          /* HSI 16 MHz, CPU divider 1 */
    CLK_HSITRIMR = 0x00;        /* factory trim (reset value; explicit) */

    delay_ms(5000);             /* SWIM flash window — pin 8 stays quiet */

    CFG_GCR = 0x01;             /* disable SWIM for the rest of the run */

    /* UART1 9600 8N1, TX only: 16 MHz / 9600 = 1667 = 0x683 */
    UART1_BRR2 = 0x03;
    UART1_BRR1 = 0x68;
    UART1_CR2  = UART1_CR2_TEN;

    uart_puts("RBARF-CAPTRIM 1\r\n");

    for (;;) {
        /* --- announce, at factory trim --- */
        uart_puts("TRIM:");
        uart_putc('0' + trim);
        uart_puts("\r\n");
        uart_puts("READY\r\n");
        uart_drain();

        /* --- capture at the sweep trim --- */
        CLK_HSITRIMR = trim;

        __asm
        ldw     x, #_capture_buf
        call    _cap_code
        __endasm;

        CLK_HSITRIMR = 0x00;    /* back to factory trim before any UART */

        /* --- dump, at factory trim --- */
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

        trim++;
        if (trim > 7)
            trim = 0;
    }
}
