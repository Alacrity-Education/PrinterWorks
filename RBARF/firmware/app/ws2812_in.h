/* app/ws2812_in.h — v2.1 production shim replacing the old capture
 * module's header.  The "input buffer" is now the decoder's 48-byte
 * DATA output (written only on a CRC-verified emit; a refusal leaves the
 * previous frame in place).  It is NOT volatile: decode, frame apply and
 * render all run sequentially in the main loop — nothing writes it
 * concurrently with a render.
 *
 * millis() is the TIM4 1 ms tick, provided by rbarf_prod.c.
 */
#ifndef WS2812_IN_H
#define WS2812_IN_H

#include <stdint.h>

#define WS2812_IN_NUM_LEDS  16
#define WS2812_IN_BUF_SIZE  (WS2812_IN_NUM_LEDS * 3)

extern uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];

uint16_t millis(void);

#endif
