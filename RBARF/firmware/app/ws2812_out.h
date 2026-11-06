#ifndef WS2812_OUT_H
#define WS2812_OUT_H

#include <stdint.h>

#define WS2812_OUT_NUM_LEDS  8
#define WS2812_OUT_BUF_SIZE  (WS2812_OUT_NUM_LEDS * 3)

extern uint8_t ws2812_out_buf[WS2812_OUT_BUF_SIZE];

void ws2812_out_init(void);
void ws2812_out_send(void);

#endif
