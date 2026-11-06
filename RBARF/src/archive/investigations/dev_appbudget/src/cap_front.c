/*
 * Capture front-end only: TIM1 CH3 rising-edge trigger + the ISR that runs
 * cap_code.s and raises a "buffer full" flag.  Extracted from the old
 * ws2812_in.c with decode_capture() and the TIM4/millis tick removed (the
 * new firmware supplies its own decoder and costs the tick separately).
 *
 * This is the flash the new firmware must spend to *acquire* a frame,
 * outside the decoder proper.  Scratch copy; the old tree is untouched.
 */
#include <stdint.h>

#define PC_DDR   (*(volatile uint8_t *)0x500C)
#define PC_CR1   (*(volatile uint8_t *)0x500D)
#define PC_CR2   (*(volatile uint8_t *)0x500E)

#define TIM1_CR1   (*(volatile uint8_t *)0x5250)
#define TIM1_IER   (*(volatile uint8_t *)0x5254)
#define TIM1_SR1   (*(volatile uint8_t *)0x5255)
#define TIM1_SR2   (*(volatile uint8_t *)0x5256)
#define TIM1_CCMR3 (*(volatile uint8_t *)0x525A)
#define TIM1_CCER2 (*(volatile uint8_t *)0x525D)
#define TIM1_PSCRH (*(volatile uint8_t *)0x5260)
#define TIM1_PSCRL (*(volatile uint8_t *)0x5261)
#define TIM1_ARRH  (*(volatile uint8_t *)0x5262)
#define TIM1_ARRL  (*(volatile uint8_t *)0x5263)
#define TIM1_CCR3L (*(volatile uint8_t *)0x526A)
#define CLK_PCKENR1 (*(volatile uint8_t *)0x50C7)

#define PC3_MASK (1 << 3)
#define CC3IE    (1 << 3)

#define CAP_BUF_SIZE 256

uint8_t capture_buf[CAP_BUF_SIZE];
volatile uint8_t capture_ready;
volatile uint8_t capture_during_tx;

void cap_front_init(void)
{
    CLK_PCKENR1 |= (1 << 7);
    TIM1_CR1 = 0x00;
    TIM1_PSCRH = 0x00;
    TIM1_PSCRL = 0x00;
    TIM1_ARRH  = 0xFF;
    TIM1_ARRL  = 0xFF;
    PC_DDR &= ~PC3_MASK;
    PC_CR1 &= ~PC3_MASK;
    PC_CR2 &= ~PC3_MASK;
    TIM1_CCMR3 = 0x01;
    TIM1_CCER2 = 0x01;
    TIM1_SR1 = 0x00;
    TIM1_SR2 = 0x00;
    TIM1_IER = CC3IE;
    TIM1_CR1 = 0x01;
    capture_ready = 0;
    capture_during_tx = 0;
}

void cap_front_isr(void) __interrupt(12)
{
    (void)TIM1_CCR3L;

    __asm
        ldw     x, #_capture_buf
        call    _cap_code
    __endasm;

    capture_ready = 1;
    capture_during_tx = 1;
    TIM1_SR1 = (uint8_t)~CC3IE;
    TIM1_IER |= CC3IE;
}
