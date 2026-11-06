; scan.s -- hand-assembly sample scanner for the v2.1 decoder hot path
; (STM8S001J3, SDCC calling convention, sdcccall(1): result in A;
;  A/X/Y caller-saved).
;
; Replaces decode.c's C scanner (v1 ps_next measured 798 B flash and
; ~200 ucsim ticks per sample visit -- EMBEDDED_FEASIBILITY.md SS6).
; This is the "tight assembly" projection of that report: documented
; cycle counts are annotated per block below; real silicon runs ~7%
; slower than the documented/ucsim numbers on this instruction mix
; (calibrated against the crystal-exact capture loop), and the on-chip
; TIM1 measurement in rbarf_v21.c (TIM:<ticks> line, 16 us/tick) is the
; authoritative figure.
;
; CONTRACT (bit-exact vs recon/approaches/embedded_v2.py _pulse_stream,
; proven by recon/approaches/dev_fw/ ucsim parity):
;   scan_cap/scan_len  in : capture buffer (cap_code.s byte layout), bytes
;   scan_init()             reset stream state
;   scan_next() -> A=1      pulse out: scan_ra/rb/fa/fb (u16 cycles),
;                           scan_sfa (slot of last high sample)
;                A=0        stream end (latch run seen, or data exhausted)
;
; Capture byte layout (DATASET.md): byte i bits5..0 = R0..R5 of loop i,
; byte i+1 bits7..6 = BS0,BS1 of loop i.  The scanner composes one
; loop-aligned octet A = (byte[i]<<2)|(byte[i+1]>>6), MSB-first
; chronological = R0,R1,R2,R3,R4,R5,BS0,BS1, and walks it with an
; unrolled 8-slot state machine, two modes (low/high).
;
; Fitted sampler model (integer cycles, dev_calibration/fitted_model):
;   slot offsets O = [0,4,9,13,17,21,27,32], loop = 40 cy
;   inter-sample gaps  GAP  = [4,5,4,4,4,6,5,8]      (slot j -> j+1)
;   +data-dependent    W    = [0,-1,0,+2,0,0,0,+1]   (added when HIGH)
;   high-sample gaps   GAPW = [4,4,4,6,4,6,5,9]      (GAP+W)
; Time t is carried incrementally in X (u16 CPU cycles): no multiplies.
; ra of a rise = t - GAP[prev slot] (previous sample was low); fa/sfa of
; a fall = derived from t - GAPW[prev slot] (previous sample was high):
; the hot loops store NOTHING per sample.
;
; Latch: 200 consecutive low samples end the stream (down-counter; the
; whole-octet fast path subtracts 8 -- an intra-octet trigger returns at
; the octet end, which is observably identical: no pulses in between).
; The Python reference arms the latch only after the first pulse ("seen");
; the capture is edge-triggered so a 200-low run before the first pulse
; cannot occur (measured: max leading-low run over all 240 real captures
; = 0 samples), and this scanner omits the flag.  Guard: scan_len >= 2
; (decode is always called with a 256..640-byte buffer).
;
; Whole-octet fast paths (exact, same accounting as v1 decoder.c):
;   octet 0x00 in low mode:  t += 40, latch -= 8      (idle / latch tail)
;   octet 0xFF in high mode: t += 42 (40 + W-sum 2)   (long pulses)
;
; DISPATCH: scan_next resumes mid-octet after each emitted pulse via a
; 9-entry jump table indexed by s_res: 0=fetch, 1..7=low slot, 8=done.
; (Falls resume in low mode by construction; entry 6 checks the 6-bit
; tail octet's end.)

    .module scan
    .globl _scan_cap
    .globl _scan_len
    .globl _scan_ra
    .globl _scan_rb
    .globl _scan_fa
    .globl _scan_fb
    .globl _scan_sfa
    .globl _scan_init
    .globl _scan_next

; ---------------------------------------------------------------- state
    .area DATA

_scan_cap:  .ds 2       ; in: capture pointer
_scan_len:  .ds 2       ; in: capture bytes (= loops)
_scan_ra:   .ds 2       ; out: rise bracket lo (cycles)
_scan_rb:   .ds 2       ; out: rise bracket hi
_scan_fa:   .ds 2       ; out: last-high time
_scan_fb:   .ds 2       ; out: fall bracket hi
_scan_sfa:  .ds 1       ; out: slot of last high sample (family id)
s_ptr:      .ds 2       ; next R-byte
s_left:     .ds 2       ; full octets remaining after the current one
s_t:        .ds 2       ; saved t between calls
s_oct:      .ds 1       ; saved octet shift register
s_res:      .ds 1       ; resume index 0..8
s_latch:    .ds 1       ; latch down-counter (200 low samples)
s_tail:     .ds 1       ; processing the final 6-sample octet

    .area CODE

; ---------------------------------------------------------------- init
_scan_init:
    ldw     x, _scan_cap
    ldw     s_ptr, x
    clr     s_tail
    clr     s_oct
    mov     s_latch, #200
    clrw    x
    ldw     s_t, x
    ldw     x, _scan_len
    jreq    00001$              ; len == 0 -> immediately done
    decw    x
    ldw     s_left, x           ; octets with a following BS byte
    mov     s_res, #0
    ret
00001$:
    mov     s_res, #8
    ret

; ------------------------------------------------------------- dispatch
; call(4) + 9 cy documented to reach the resume point
_scan_next:
    clrw    x
    ld      a, s_res
    sll     a
    ld      xl, a
    ldw     x, (jtab, x)
    ldw     y, x
    ldw     x, s_t              ; X = t
    ld      a, s_oct            ; A = octet register
    jp      (y)

jtab:
    .dw     fetch_low           ; 0: octet boundary, low
    .dw     low1                ; 1..7: resume at low slot J
    .dw     low2
    .dw     low3
    .dw     low4
    .dw     low5
    .dw     resume6             ; 6: guarded (tail octet has no slot 6)
    .dw     low7
    .dw     done_e              ; 8: stream ended

done_e:
    clr     a
    ret

resume6:
    tnz     s_tail
    jreq    00002$
    jp      end_low_tail
00002$:
    jp      low6

; ------------------------------------- low mode: octet fetch + fast path
tl_low:
    jp      tail_low

; all-low octet: 8 samples skipped -- 9 cy documented
fast_low0:
    addw    x, #40              ; t += LOOP_CY (no W: all low)
    ld      a, s_latch
    sub     a, #8
    ld      s_latch, a
    jrule   00003$              ; latch run complete (seen: see header)
    jra     fetch_low
00003$:
    mov     s_res, #8
    clr     a
    ret

; compose next octet -- 22 cy documented (2.75 cy/sample)
fetch_low:
    ldw     y, s_left
    jreq    tl_low              ; no BS byte left -> 6-bit tail
    decw    y
    ldw     s_left, y
    ldw     y, s_ptr
    ld      a, (y)              ; byte i  (R0..R5 in bits 5..0)
    incw    y
    ldw     s_ptr, y
    sll     a
    sll     a
    ld      s_oct, a
    ld      a, (y)              ; byte i+1 (BS0,BS1 in bits 7..6)
    swap    a
    srl     a
    srl     a
    and     a, #0x03
    or      a, s_oct            ; A = R0..R5,BS0,BS1 MSB-first
    jreq    fast_low0
    ; fallthrough -> low0

; ------------------------------------------------- low mode, slots 0..7
; per low sample: sll(1) jrc(1) addw(2) dec(1) jreq(1) = 6 cy documented
low0:
    sll     a
    jrc     rt0
    addw    x, #4
    dec     s_latch
    jreq    latch_end
low1:
    sll     a
    jrc     rt1
    addw    x, #5
    dec     s_latch
    jreq    latch_end
low2:
    sll     a
    jrc     rt2
    addw    x, #4
    dec     s_latch
    jreq    latch_end
low3:
    sll     a
    jrc     rt3
    addw    x, #4
    dec     s_latch
    jreq    latch_end
low4:
    sll     a
    jrc     rt4
    addw    x, #4
    dec     s_latch
    jreq    latch_end
low5:
    sll     a
    jrc     rt5
    addw    x, #6
    dec     s_latch
    jreq    latch_end
    tnz     s_tail              ; tail octet ends after slot 5
    jrne    el_t
low6:
    sll     a
    jrc     rt6
    addw    x, #5
    dec     s_latch
    jreq    latch_end
low7:
    sll     a
    jrc     rt7
    addw    x, #8
    dec     s_latch
    jreq    latch_end
    jp      fetch_low

; rise trampolines (keep the jrc targets in relative range)
rt0: jp     rise0
rt1: jp     rise1
rt2: jp     rise2
rt3: jp     rise3
rt4: jp     rise4
rt5: jp     rise5
rt6: jp     rise6
rt7: jp     rise7

latch_end:                      ; 200 consecutive lows: stream over
    mov     s_res, #8
    clr     a
    ret

el_t:
    jp      end_low_tail

; --------------------------------------------------------- rise sites
; sample at slot J is the first high of a pulse (low mode, C=1):
;   ra = t - GAP[J-1]  (previous sample was low), rb = t, latch reset,
;   t += GAPW[J], continue in high mode at slot J+1.   ~12 cy documented
rise0:
    ldw     y, x
    subw    y, #8               ; GAP[7]
    jrnc    00004$
    clrw    y                   ; first sample of the capture (t = 0):
00004$:                         ; ra = max(t - FIRST_BR, 0) = 0
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #4               ; GAPW[0]
    jp      hi1
rise1:
    ldw     y, x
    subw    y, #4               ; GAP[0]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #4               ; GAPW[1]
    jp      hi2
rise2:
    ldw     y, x
    subw    y, #5               ; GAP[1]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #4               ; GAPW[2]
    jp      hi3
rise3:
    ldw     y, x
    subw    y, #4               ; GAP[2]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #6               ; GAPW[3]
    jp      hi4
rise4:
    ldw     y, x
    subw    y, #4               ; GAP[3]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #4               ; GAPW[4]
    jp      hi5
rise5:
    ldw     y, x
    subw    y, #4               ; GAP[4]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #6               ; GAPW[5]
    jp      hi6
rise6:
    ldw     y, x
    subw    y, #6               ; GAP[5]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #5               ; GAPW[6]
    jp      hi7
rise7:
    ldw     y, x
    subw    y, #5               ; GAP[6]
    ldw     _scan_ra, y
    ldw     _scan_rb, x
    mov     s_latch, #200
    addw    x, #9               ; GAPW[7]
    jp      fetch_high

; ------------------------------------ high mode: octet fetch + fast path
th_high:
    jp      tail_high

; all-high octet: 8 samples skipped -- 4 cy documented
fast_high:
    addw    x, #42              ; t += LOOP_CY + W-sum(2)
    jra     fetch_high

fetch_high:
    ldw     y, s_left
    jreq    th_high
    decw    y
    ldw     s_left, y
    ldw     y, s_ptr
    ld      a, (y)
    incw    y
    ldw     s_ptr, y
    sll     a
    sll     a
    ld      s_oct, a
    ld      a, (y)
    swap    a
    srl     a
    srl     a
    and     a, #0x03
    or      a, s_oct
    cp      a, #0xFF
    jreq    fast_high
    ; fallthrough -> hi0

; ------------------------------------------------- high mode, slots 0..7
; per high sample: sll(1) jrnc(1) addw(2) = 4 cy documented
hi0:
    sll     a
    jrnc    ft0
    addw    x, #4
hi1:
    sll     a
    jrnc    ft1
    addw    x, #4
hi2:
    sll     a
    jrnc    ft2
    addw    x, #4
hi3:
    sll     a
    jrnc    ft3
    addw    x, #6
hi4:
    sll     a
    jrnc    ft4
    addw    x, #4
hi5:
    sll     a
    jrnc    ft5
    addw    x, #6
    tnz     s_tail              ; tail octet ends after slot 5
    jrne    eh_t
hi6:
    sll     a
    jrnc    ft6
    addw    x, #5
hi7:
    sll     a
    jrnc    ft7
    addw    x, #9
    jp      fetch_high

; fall trampolines
ft0: jp     fall0
ft1: jp     fall1
ft2: jp     fall2
ft3: jp     fall3
ft4: jp     fall4
ft5: jp     fall5
ft6: jp     fall6
ft7: jp     fall7

eh_t:
    jp      end_high_tail

; ---------------------------------------------------------- fall sites
; sample at slot J is low, ending the pulse (high mode, C=0):
;   fa = t - GAPW[J-1], sfa = J-1 (previous sample was the last high),
;   fb = t, t += GAP[J], low_run = 1 (latch 199), save state, return 1.
;   ~22 cy documented incl. the shared epilogue
fall0:
    ldw     y, x
    subw    y, #9               ; GAPW[7]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #7
    addw    x, #4               ; GAP[0]
    push    #1                  ; resume at low1
    jp      fall_common
fall1:
    ldw     y, x
    subw    y, #4               ; GAPW[0]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #0
    addw    x, #5               ; GAP[1]
    push    #2
    jp      fall_common
fall2:
    ldw     y, x
    subw    y, #4               ; GAPW[1]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #1
    addw    x, #4               ; GAP[2]
    push    #3
    jp      fall_common
fall3:
    ldw     y, x
    subw    y, #4               ; GAPW[2]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #2
    addw    x, #4               ; GAP[3]
    push    #4
    jp      fall_common
fall4:
    ldw     y, x
    subw    y, #6               ; GAPW[3]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #3
    addw    x, #4               ; GAP[4]
    push    #5
    jp      fall_common
fall5:
    ldw     y, x
    subw    y, #4               ; GAPW[4]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #4
    addw    x, #6               ; GAP[5]
    push    #6
    jp      fall_common
fall6:
    ldw     y, x
    subw    y, #6               ; GAPW[5]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #5
    addw    x, #5               ; GAP[6]
    push    #7
    jp      fall_common
fall7:
    ldw     y, x
    subw    y, #5               ; GAPW[6]
    ldw     _scan_fa, y
    ldw     _scan_fb, x
    mov     _scan_sfa, #6
    addw    x, #8               ; GAP[7]
    push    #0                  ; slot 7 resumes at the next octet fetch
    jp      fall_common

fall_common:                    ; stack: resume index; A = octet, X = t
    ld      s_oct, a
    ldw     s_t, x
    mov     s_latch, #199       ; the fall sample itself counts (low_run=1)
    pop     a
    ld      s_res, a
    ld      a, #1
    ret

; ------------------------------------------------------- 6-bit tail octet
; loop len-1 has no following byte: only R0..R5 exist (harness linearize
; drops BS0/BS1 of the last loop).  In practice the latch fires ~100
; loops earlier; this path exists for bit-exactness on arbitrary input.
tail_low:
    ldw     y, s_ptr
    ld      a, (y)
    sll     a
    sll     a
    mov     s_tail, #1
    jp      low0

tail_high:
    ldw     y, s_ptr
    ld      a, (y)
    sll     a
    sll     a
    mov     s_tail, #1
    jp      hi0

end_low_tail:                   ; data exhausted, no pulse pending
    mov     s_res, #8
    clr     a
    ret

end_high_tail:                  ; data exhausted mid-pulse: final pulse,
    ldw     y, x                ; fb = fa + FIRST_BR (4)
    subw    y, #6               ; GAPW[5]: X is past tail slot 5
    ldw     _scan_fa, y
    addw    y, #4
    ldw     _scan_fb, y
    mov     _scan_sfa, #5
    mov     s_res, #8
    ld      a, #1
    ret
