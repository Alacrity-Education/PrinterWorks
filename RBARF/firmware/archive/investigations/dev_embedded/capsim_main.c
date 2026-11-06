#include <stdint.h>
extern void capsim(void) __naked;
uint8_t buf[64];
void done(void) { __asm__("halt"); for(;;); }
void main(void)
{
    __asm__("ldw x, #_buf");
    __asm__("call _capsim");
    done();
}
