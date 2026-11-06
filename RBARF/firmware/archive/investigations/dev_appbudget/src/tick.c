/*
 * TIM4 / millis() 1 ms tick — extracted verbatim from the old firmware's
 * ws2812_in.c (lines 111-141 + the ms_counter global).  Compiled standalone
 * so the animation engine's timebase can be costed on its own: in the old
 * build it is fused into ws2812_in.c, which the new firmware replaces.
 *
 * Nothing in the read-only old tree is modified; this is a scratch copy.
 */
#include <stdint.h>

#define TIM4_CR1   (*(volatile uint8_t *)0x5340)
#define TIM4_IER   (*(volatile uint8_t *)0x5343)
#define TIM4_SR    (*(volatile uint8_t *)0x5344)
#define TIM4_PSCR  (*(volatile uint8_t *)0x5347)
#define TIM4_ARR   (*(volatile uint8_t *)0x5348)
#define CLK_PCKENR1 (*(volatile uint8_t *)0x50C7)

#define UIE (1 << 0)

static volatile uint16_t ms_counter;

void tick_init(void)
{
    CLK_PCKENR1 |= (1 << 4);       /* TIM4 clock */
    TIM4_CR1  = 0x00;
    TIM4_PSCR = 0x07;
    TIM4_ARR  = 124;
    TIM4_SR   = 0x00;
    TIM4_IER  = UIE;
    TIM4_CR1  = 0x01;
    ms_counter = 0;
}

uint16_t millis(void)
{
    uint16_t ms;
    __asm__("sim");
    ms = ms_counter;
    __asm__("rim");
    return ms;
}

void tim4_upd_isr(void) __interrupt(23)
{
    TIM4_SR = (uint8_t)~UIE;
    ms_counter++;
}
