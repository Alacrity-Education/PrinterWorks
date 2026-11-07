/* Host shim for the parity test: provides the globals the original
 * src/app/anim.c links against and a buffer-in/buffer-out entry point. */
#include <stdint.h>
#include <string.h>
#include "anim.h"
#include "ws2812_in.h"
#include "ws2812_out.h"

uint8_t ws2812_in_buf[WS2812_IN_BUF_SIZE];
uint8_t ws2812_out_buf[WS2812_OUT_BUF_SIZE];

uint16_t millis(void) { return 0; }

void rbarf_c_anim_render(const uint8_t *frame, uint16_t now_ms, uint8_t *out)
{
    memcpy(ws2812_in_buf, frame, WS2812_IN_BUF_SIZE);
    /* poison the output so a C path that forgets a byte is visible */
    memset(ws2812_out_buf, 0xA5, WS2812_OUT_BUF_SIZE);
    anim_render(now_ms);
    memcpy(out, ws2812_out_buf, WS2812_OUT_BUF_SIZE);
}
