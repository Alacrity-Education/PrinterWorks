/*
 * WS2812 bit-bang output — STM8S001J3, SDCC
 *
 * Sends 8 LEDs (192 bits) on PA3 (pin 5) via cycle-counted
 * assembly with interrupts left enabled.
 *
 * If the input capture ISR fires mid-send (~480 us blocking),
 * the output waveform is corrupted.  The caller detects this
 * via ws2812_in_during_tx and re-sends.
 *
 * Each bit is exactly 20 cycles (1.25 us at 16 MHz):
 *   bit 0 → T0H = 6 cy (375 ns), T0L = 14 cy (875 ns)
 *   bit 1 → T1H = 11 cy (688 ns), T1L = 9 cy  (563 ns)
 *
 * Byte-boundary bits stretch to ~25 cycles (1563 ns) due to
 * byte-loading overhead.  This is within the WS2812 spec
 * (max 1850 ns per bit) and well under the 50 us reset threshold.
 */

#include "ws2812_out.h"
#include "ws2812_in.h"

/* Port A */
#define PA_ODR  (*(volatile uint8_t *)0x5000)
#define PA_DDR  (*(volatile uint8_t *)0x5002)
#define PA_CR1  (*(volatile uint8_t *)0x5003)
#define PA_CR2  (*(volatile uint8_t *)0x5004)

/* ---- Globals ---- */

uint8_t ws2812_out_buf[WS2812_OUT_BUF_SIZE];

/* Assembly scratch — must be global so inline asm can reference them */
static volatile uint8_t ws_bit_cnt;
static volatile uint8_t ws_byte_cnt;

/* ---- Init ---- */

void ws2812_out_init(void)
{
    PA_ODR &= ~(1 << 3);           /* PA3 LOW */
    PA_DDR |=  (1 << 3);           /* output */
    PA_CR1 |=  (1 << 3);           /* push-pull */
    PA_CR2 |=  (1 << 3);           /* 10 MHz slew rate */
}

/* ---- Send ---- */

void ws2812_out_send(void)
{
    ws2812_in_during_tx = 0;

    __asm

    ;; ============================================================
    ;; Reset latch: hold PA3 LOW for >50 us before new data.
    ;; 256 iterations x 4 cy = 1024 cy = 64 us.
    ;; ============================================================
    clr  A
00001$:
    nop
    dec  A
    jrne 00001$

    ;; ============================================================
    ;; Bit-bang 24 bytes out of ws2812_out_buf on PA3 (PA_ODR.3).
    ;;
    ;; Register allocation:
    ;;   A  — current byte (shifted out MSB-first via SLL)
    ;;   X  — pointer into ws2812_out_buf
    ;;   _ws_byte_cnt (RAM) — bytes remaining
    ;;   _ws_bit_cnt  (RAM) — bits remaining in current byte
    ;; ============================================================

    ldw  X, #_ws2812_out_buf
    mov  _ws_byte_cnt, #24

    ;; ---- load first byte, then fall into bit loop ----
00010$:                             ; _ws_next_byte
    ld   A, (X)                     ; [1]
    incw X                          ; [1]
    mov  _ws_bit_cnt, #8            ; [1]

00020$:                             ; _ws_bit_loop
    ;; ---- every bit starts here: pin HIGH ----
    bset 0x5000, #3                 ; [1]  pin HIGH  (cycle 0)
    sll  A                          ; [1]  MSB → carry  (cycle 1)
    jrc  00030$                     ; [1/2] bit=1 → taken(2cy), bit=0 → not taken(1cy)

    ;; ============================================================
    ;; BIT = 0   T0H = 6 cy (375 ns)   T0L = 14 cy (875 ns)
    ;; ============================================================
    ;;                                  cycle count from bset:
    nop                             ; [1]  3
    nop                             ; [1]  4
    nop                             ; [1]  5
    bres 0x5000, #3                 ; [1]  6  ← pin LOW
    nop                             ; [1]  7
    nop                             ; [1]  8
    nop                             ; [1]  9
    nop                             ; [1]  10
    nop                             ; [1]  11
    nop                             ; [1]  12
    nop                             ; [1]  13
    nop                             ; [1]  14
    nop                             ; [1]  15
    nop                             ; [1]  16
    dec  _ws_bit_cnt                ; [1]  17
    jrne 00020$                     ; [2]  18-19 taken → 20 cy total ✓
    ;; ---- last bit of byte: jrne not taken (1 cy) ----
    dec  _ws_byte_cnt               ; [1]
    jrne 00010$                     ; [2]  → load next byte
    jra  00050$                     ; [2]  → done (last byte)

00030$:                             ; _ws_bit_one
    ;; ============================================================
    ;; BIT = 1   T1H = 11 cy (688 ns)   T1L = 9 cy (563 ns)
    ;; ============================================================
    ;; jrc was taken: 2 cy → we are at cycle 4 from bset
    nop                             ; [1]  4
    nop                             ; [1]  5
    nop                             ; [1]  6
    nop                             ; [1]  7
    nop                             ; [1]  8
    nop                             ; [1]  9
    nop                             ; [1]  10
    bres 0x5000, #3                 ; [1]  11  ← pin LOW
    nop                             ; [1]  12
    nop                             ; [1]  13
    nop                             ; [1]  14
    nop                             ; [1]  15
    nop                             ; [1]  16
    dec  _ws_bit_cnt                ; [1]  17
    jrne 00020$                     ; [2]  18-19 taken → 20 cy total ✓
    ;; ---- last bit of byte: jrne not taken (1 cy) ----
    dec  _ws_byte_cnt               ; [1]
    jrne 00010$                     ; [2]  → load next byte
    ;; fall through → done

00050$:                             ; _ws_done
    ;; Pin is LOW.  The >50 us reset latch before the NEXT send
    ;; is handled by the delay at the top of this function.

    __endasm;
}
