#include <stdint.h>
extern uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out);
extern const uint8_t test_cap[256];
uint8_t cap_buf[256];
uint8_t payload[48];
volatile uint8_t result;
void done(void) { __asm__("halt"); for (;;) ; }
void main(void)
{
    uint16_t i;
    for (i = 0; i < 256; i++) cap_buf[i] = test_cap[i];
    result = ws_decode(cap_buf, 256, payload);
    done();
}
