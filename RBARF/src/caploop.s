; caploop.s -- THE cycle-calibrated 40-cycle capture sampling loop, split
; out of scan.s so the production image can link a size-focused scanner
; while bench builds keep scan.s's speed-unrolled one.  ONE source for
; the pinned block: the fitted model is calibrated to THESE instruction
; bytes at THIS address phase (see the block comment below).

    .module caploop
    .globl _cap_capture
    .globl _cap_loop

; ======================================================================
; _cap_capture -- 256-loop WS2812 oversampling capture.
; Instruction-for-instruction identical to cap_code.s (the fitted sampler
; model is calibrated to THIS exact loop; any edit invalidates W_CY[] --
; EMBEDDED_V2_SPEC.md SS14 risk 7) except the loop count: 256 loops ->
; 256 bytes = 2048 samples = 592 us nominal, sized for the 216-bit v2.1
; test frame (117.7 loops at +8% incl. slack, spec SS3) plus the 200-low
; latch tail (25 loops) with >5x margin.
;
; ALIGNMENT IS PART OF THE FITTED MODEL (measured on this bench,
; 2026-09-06): the loop's real timing includes flash-fetch stalls that
; depend on the code's address phase.  capture.ihx (the image the
; 40-cycle model was fitted against) has _cap_code at 0x8111; linking
; this routine as ordinary relocatable CODE landed it at 0x9E1E (phase 0
; mod 4 instead of 1) and every bench decode then measured eps at
; +6.2..+7.5% instead of this unit's -1.07% -- i.e. at that phase the
; loop really runs ~37 cycles, the DOCUMENTED count, with no stalls.
; 0.9893 * 40/37 - 1 = +6.95%: the observed shift, exactly.  So the
; routine lives in an ABS area at 0x9FA1 = 0x8111 (mod 16), restoring
; the fitted stall pattern.  The Makefile guards against CODE growing
; into it (sdld does not check REL/ABS overlaps).
; Entry: X = capture buffer pointer.  Clobbers: A, X, Y, C.
; ======================================================================
    .area CAPLOOP (ABS)
    .org 0x9FA1
_cap_capture:
    ldw     y, #256

00010$:                             ; wait_low
    btjt    0x500B, #3, 00010$
00011$:                             ; wait_high
    btjf    0x500B, #3, 00011$

_cap_loop:                          ; sampling loop, address-phase pinned:
00012$:                             ; MUST stay == 0x811F (mod 16); label
                                    ; adds no bytes -- cap_byte
    rlc     a                       ; deposit BS1 from C (prev boundary)

    btjt    0x500B, #3, 00013$      ; R0
    nop
00013$: rlc     a

    btjt    0x500B, #3, 00014$      ; R1
    nop
00014$: rlc     a

    btjt    0x500B, #3, 00015$      ; R2
    nop
00015$: rlc     a

    btjt    0x500B, #3, 00016$      ; R3
    nop
00016$: rlc     a

    btjt    0x500B, #3, 00017$      ; R4
    nop
00017$: rlc     a

    btjt    0x500B, #3, 00018$      ; R5
    nop
00018$: rlc     a

    ld      (x), a                  ; store byte
    incw    x

    btjt    0x500B, #3, 00019$      ; BS0
    nop
00019$: rlc     a

    decw    y                       ; loop counter (sets Z)

    btjt    0x500B, #3, 00020$      ; BS1 -- C only, Z preserved
    nop
00020$:

    jrne    00012$                  ; loop (tests Z from decw)

    rim                             ; post-loop: timing-irrelevant.  For a
    ld      a, #1                   ; _cap_arm entry this re-enables the
    ret                             ; tick and flags "captured" (A=1);
                                    ; harmless for the legacy bench entry
                                    ; (no interrupt sources enabled there)
