/* app/tick.c -- TIM4 1 ms tick: ms_counter + ISR + millis(), ported
 * verbatim from the old ws2812_in.c timebase (dev_appbudget/src/tick.c
 * measured it at 51 B).  Lives in its OWN module so the module holding
 * main() declares no __interrupt handler: the production image supplies
 * a hand-packed vector table (vectors_prod.s) whose TRAP..IRQ22 window
 * holds relocated code, and SDCC must not emit a full table of its own.
 *
 * TIM4 register setup stays in rbarf_prod.c main() (runs once).
 */
#include <stdint.h>
#include "ws2812_in.h"

#define TIM4_SR (*(volatile uint8_t *)0x5344)

volatile uint16_t ms_counter;

void tim4_upd_isr(void) __interrupt(23)
{
    TIM4_SR = (uint8_t)~0x01;
    ms_counter++;
}

uint16_t millis(void)
{
    uint16_t ms;
    __asm__("sim");
    ms = ms_counter;
    __asm__("rim");
    return ms;
}
