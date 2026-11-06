/*
 * Main-loop glue as the NEW firmware would carry it: clock init, module init,
 * 100 Hz render tick, WS2812 re-send retry.  Derived from the old main.c with
 * the debug-UART beacon/report and the DISABLE_INPUT test-pattern block
 * removed (neither survives into the new firmware).
 *
 * Scratch copy — the old tree is untouched.
 */
#include <stdint.h>
#include "ws2812_in.h"
#include "ws2812_out.h"
#include "anim.h"

#define CLK_CKDIVR (*(volatile uint8_t *)0x50C6)

extern void tick_init(void);

static void clock_init(void)
{
    CLK_CKDIVR = 0x00;
}

int main(void)
{
    clock_init();
    tick_init();
    ws2812_in_init();          /* stands in for the new capture/decoder init */
    ws2812_out_init();

    __asm__("rim");

    uint16_t last_frame = millis();

    for (;;) {
        if (ws2812_in_complete)
            ws2812_in_complete = 0;

        uint16_t now = millis();
        if ((uint16_t)(now - last_frame) >= 10) {
            last_frame = now;
            anim_render(now);
            do {
                ws2812_in_during_tx = 0;
                ws2812_out_send();
            } while (ws2812_in_during_tx);
        }
    }
}
