/* sim_v2.c -- ucsim image: decode one embedded capture, halt.
 *
 * The capture bytes are compiled in as a flash const (cap_data.c,
 * generated per run by ucsim_bitexact.py).  After the decode the result
 * lives in known globals the harness reads back by symbol address:
 *   g_status  DEC_* return code
 *   g_out[16] emitted DATA bytes (valid on status != 0)
 *   dec_info  the full path/cause/counter record (decode.h)
 * halt stops the simulator; the harness reads RAM and diffs vs Python.
 */
#include "decode.h"

extern const uint8_t CAP[];
extern const uint16_t CAP_LEN;

volatile uint8_t g_status;
uint8_t g_out[ND_DATA];

/* NOT static: the harness sets a ucsim breakpoint on _sim_done and stops
 * there, BEFORE the halt executes — deterministic, and immune to any
 * post-halt simulator behaviour.  Every result byte (g_status, g_out,
 * dec_info) is committed before main jumps here. */
void sim_done(void) { __asm__("halt"); for (;;) ; }

void main(void)
{
    g_status = ws_decode_ex(CAP, CAP_LEN, g_out);
    sim_done();
}
