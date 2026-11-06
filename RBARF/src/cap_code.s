; cap_code.s — WS2812 GPIO oversampling capture (STM8S001J3, 16 MHz)
;
; Ported from the previous implementation unchanged except the buffer
; length (640 bytes, was 225).
;
; Samples PC3 (PC_IDR bit 3, package pin 7) at 4 cy/sample via
; BTJT/NOP/RLC A.  6 regular + 2 boundary samples per byte = 8 samples,
; 37 cy/byte -> 5120 samples over 1.184 ms.
;
; Boundary samples split the dead zone: max gap between consecutive
; reads is 6 cy (375 ns), down from 9 cy (562.5 ns) with 8 regular.
; BTJT and NOP do not modify Z, so DECW Y's Z flag is preserved
; across BS1 for JRNE.
;
; Sample read positions within each 37-cycle byte period:
;   R0:cy1  R1:cy5  R2:cy9  R3:cy13  R4:cy17  R5:cy21
;   BS0:cy27  BS1:cy32
; Gaps: 4, 4, 4, 4, 4, 6, 5, 6  (max 6)
;
; Stored byte layout (MSB..LSB), derived from the RLC ordering:
;   bit7 = BS0 of the PREVIOUS iteration
;   bit6 = BS1 of the PREVIOUS iteration
;   bit5..bit0 = R0..R5 of THIS iteration
; The first byte's bits 7..6 are garbage (no previous iteration); the
; last iteration's BS0/BS1 are never stored.
;
; Entry: X = capture buffer pointer.  Blocks in wait_low/wait_high
; until a rising edge on PC3 starts the capture.
; Clobbers: A, X, Y, C

    .module cap_code
    .globl _cap_code

    .area CODE

_cap_code:
    ldw     y, #640

00010$:                             ; wait_low
    btjt    0x500B, #3, 00010$
00011$:                             ; wait_high
    btjf    0x500B, #3, 00011$

00012$:                             ; cap_byte
    rlc     a                       ; deposit BS1 from C (prev boundary)

    btjt    0x500B, #3, 00001$      ; R0
    nop
00001$: rlc     a

    btjt    0x500B, #3, 00002$      ; R1
    nop
00002$: rlc     a

    btjt    0x500B, #3, 00003$      ; R2
    nop
00003$: rlc     a

    btjt    0x500B, #3, 00004$      ; R3
    nop
00004$: rlc     a

    btjt    0x500B, #3, 00005$      ; R4
    nop
00005$: rlc     a

    btjt    0x500B, #3, 00006$      ; R5
    nop
00006$: rlc     a

    ld      (x), a                  ; store byte
    incw    x

    btjt    0x500B, #3, 00007$      ; BS0
    nop
00007$: rlc     a

    decw    y                       ; loop counter (sets Z)

    btjt    0x500B, #3, 00008$      ; BS1 — C only, Z preserved
    nop
00008$:

    jrne    00012$                  ; loop (tests Z from decw)

    ret
