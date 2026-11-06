; cap_code.s inner loop, verbatim instruction mix, reading a RAM address
; (0x0100) instead of PC_IDR; 640 iterations then halt.
    .module capsim
    .globl _capsim
    .area CODE
_capsim:
    ldw     y, #640
00012$:
    rlc     a
    btjt    0x0100, #3, 00001$
    nop
00001$: rlc     a
    btjt    0x0100, #3, 00002$
    nop
00002$: rlc     a
    btjt    0x0100, #3, 00003$
    nop
00003$: rlc     a
    btjt    0x0100, #3, 00004$
    nop
00004$: rlc     a
    btjt    0x0100, #3, 00005$
    nop
00005$: rlc     a
    btjt    0x0100, #3, 00006$
    nop
00006$: rlc     a
    ld      (x), a
    incw    x
    btjt    0x0100, #3, 00007$
    nop
00007$: rlc     a
    decw    y
    btjt    0x0100, #3, 00008$
    nop
00008$:
    jrne    00012$
    ret
