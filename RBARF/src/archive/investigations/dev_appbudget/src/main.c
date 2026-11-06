#include <stdint.h>
#include "ws2812_in.h"
#include "ws2812_out.h"
#include "anim.h"
#include "debug_uart.h"

#define CLK_CKDIVR (*(volatile uint8_t *)0x50C6)

static void clock_init(void)
{
    CLK_CKDIVR = 0x00;
}

/* ================================================================
 * TEST PATTERNS — only compiled when DISABLE_INPUT is defined.
 *
 * Uncomment exactly ONE test define to select the animation mode.
 * The test code fills ws2812_in_buf with base colors and flags.
 * ================================================================ */

// #define DISABLE_INPUT

#ifdef DISABLE_INPUT

/* Uncomment ONE: */
// #define TEST_BLINK
// #define TEST_FADE
#define TEST_SEQUENCE
// #define TEST_SEQUENCE_2LED_FADE
// #define TEST_SEQUENCE_NO_FADE
// #define TEST_SPIN
// #define TEST_SPIN_REV
// #define TEST_RAIN
// #define TEST_RAIN_REV
// #define TEST_DRAW
// #define TEST_DRAW_REV
// #define TEST_NONE

static void setup_test(void)
{
    uint8_t i;
    volatile uint8_t *buf = ws2812_in_buf;

    /* default base: red (GRB) for all 8 LEDs */
    for (i = 0; i < 8; i++) {
        buf[i * 3]     = 0x00;  /* G */
        buf[i * 3 + 1] = 0x40;  /* R */
        buf[i * 3 + 2] = 0x00;  /* B */
    }
    /* clear flags */
    for (i = 24; i < 48; i++)
        buf[i] = 0x00;

#if defined(TEST_BLINK)
    /* Blink red <-> blue, 500ms cycle */
    buf[24 + 0] = 0x01;   /* mode: blink */
    buf[24 + 1] = 10;     /* 500ms cycle (10 * 50ms) */
    buf[24 + 3] = 0x00;   /* alt G */
    buf[24 + 4] = 0x00;   /* alt R */
    buf[24 + 5] = 0x40;   /* alt B */

#elif defined(TEST_FADE)
    /* Fade red <-> green, 1s cycle */
    buf[24 + 0] = 0x02;   /* mode: fade */
    buf[24 + 1] = 20;     /* 1000ms cycle */
    buf[24 + 3] = 0x40;   /* alt G */
    buf[24 + 4] = 0x00;   /* alt R */
    buf[24 + 5] = 0x00;   /* alt B */

#elif defined(TEST_SEQUENCE)
    /* Sequence 0-1-2-3-4-5-6-7 with 3-LED fading, 2s cycle */
    buf[24 + 0] = 0x03;   /* mode: sequence */
    buf[24 + 1] = 40;     /* 2000ms cycle */
    buf[24 + 2] = 0x00;   /* mask: no fixed LEDs */
    buf[24 + 3] = 0x00;   /* bg G */
    buf[24 + 4] = 0x00;   /* bg R */
    buf[24 + 5] = 0x00;   /* bg B */
    buf[24 + 6] = 0x02;   /* features: 2-fading */
    buf[24 + 7]  = 0x01;  /* seq: LED 0, LED 1 */
    buf[24 + 8]  = 0x23;  /* seq: LED 2, LED 3 */
    buf[24 + 9]  = 0x45;  /* seq: LED 4, LED 5 */
    buf[24 + 10] = 0x67;  /* seq: LED 6, LED 7 */
    buf[24 + 11] = 0xFF;  /* terminate */

#elif defined(TEST_SEQUENCE_2LED_FADE)
    /* Sequence with 2-LED crossfade, 2s cycle */
    buf[24 + 0] = 0x03;
    buf[24 + 1] = 40;
    buf[24 + 2] = 0x00;
    buf[24 + 6] = 0x02;   /* features: two-led fading */
    buf[24 + 7]  = 0x01;
    buf[24 + 8]  = 0x23;
    buf[24 + 9]  = 0x45;
    buf[24 + 10] = 0x67;
    buf[24 + 11] = 0xFF;

#elif defined(TEST_SEQUENCE_NO_FADE)
    /* Sequence without fading, 2-LED group, 1s cycle */
    buf[24 + 0] = 0x03;
    buf[24 + 1] = 20;
    buf[24 + 2] = 0x00;
    buf[24 + 6] = 0x04;   /* features: two-led grouping */
    buf[24 + 7]  = 0x01;
    buf[24 + 8]  = 0x23;
    buf[24 + 9]  = 0x45;
    buf[24 + 10] = 0x67;
    buf[24 + 11] = 0xFF;

#elif defined(TEST_SPIN)
    /* Spin with fading, 1s cycle */
    buf[24 + 0] = 0x04;   /* mode: spin */
    buf[24 + 1] = 20;     /* 1000ms cycle */
    buf[24 + 6] = 0x01;   /* features: fading */

#elif defined(TEST_SPIN_REV)
    buf[24 + 0] = 0x05;   /* mode: spin reverse */
    buf[24 + 1] = 20;
    buf[24 + 6] = 0x01;

#elif defined(TEST_RAIN)
    /* Rain with fading, 1.5s cycle */
    buf[24 + 0] = 0x06;   /* mode: rain */
    buf[24 + 1] = 30;     /* 1500ms cycle */
    buf[24 + 6] = 0x01;

#elif defined(TEST_RAIN_REV)
    buf[24 + 0] = 0x07;   /* mode: rain reverse */
    buf[24 + 1] = 30;
    buf[24 + 6] = 0x01;

#elif defined(TEST_DRAW)
    /* Draw with fading, 2s cycle */
    buf[24 + 0] = 0x08;   /* mode: draw */
    buf[24 + 1] = 40;     /* 2000ms cycle */
    buf[24 + 6] = 0x01;

#elif defined(TEST_DRAW_REV)
    buf[24 + 0] = 0x09;   /* mode: draw reverse */
    buf[24 + 1] = 40;
    buf[24 + 6] = 0x01;

#elif defined(TEST_NONE)
    /* Static: just show base color */
    buf[24 + 0] = 0x00;

#endif
}

#endif /* DISABLE_INPUT */

int main(void)
{
    clock_init();
    ws2812_in_init();
    ws2812_out_init();
    debug_uart_init();

    __asm__("rim");

    {
        uint8_t i;
        volatile uint8_t *buf = ws2812_in_buf;
        for (i = 0; i < 8; i++) {
            buf[i * 3]     = 0x00;
            buf[i * 3 + 1] = 0x00;
            buf[i * 3 + 2] = 0x40;
        }
        for (i = 24; i < 48; i++)
            buf[i] = 0x00;
        buf[24 + 0] = 0x02;
        buf[24 + 1] = 40;
        buf[24 + 2] = 0xE7;
    }

#ifdef DISABLE_INPUT
    setup_test();
#endif

    uint16_t last_frame = millis();

    for (;;) {
#ifndef DISABLE_INPUT
        if (ws2812_in_complete) {
            ws2812_in_complete = 0;
            debug_uart_send_report();
        }
#endif

        /* periodic debug beacon every ~500ms */
        {
            static uint16_t last_beacon;
            uint16_t nb = millis();
            if ((uint16_t)(nb - last_beacon) >= 500) {
                last_beacon = nb;
                debug_uart_byte('.');
            }
        }

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
