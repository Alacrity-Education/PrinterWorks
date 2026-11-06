#ifndef WS2812_IN_H
#define WS2812_IN_H

#include <stdint.h>

#define WS2812_IN_NUM_LEDS  16
#define WS2812_IN_BUF_SIZE  (WS2812_IN_NUM_LEDS * 3)

/* The host prepends one "preamble" LED (0xFF 0xFF 0xFE) for byte-level
 * synchronization: a run of 1-bits ending in a single 0-bit delimiter.
 * The receiver skips the 1s and starts reading data right after the 0,
 * so byte alignment no longer depends on catching the very first bit. */

extern volatile uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];
extern volatile uint8_t ws2812_in_complete;
extern volatile uint8_t ws2812_in_during_tx;

void ws2812_in_init(void);
uint16_t millis(void);

#endif
