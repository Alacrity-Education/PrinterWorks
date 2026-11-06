; decode_asm.s -- size-focused hand assembly of the WHOLE v2.3 decoder:
; the streaming layer AND the pipeline tail (USE_ASM_DEC=1 target
; builds; decode.c keeps the portable C versions of every one of these
; functions as the host-parity reference).
;
; CONTRACT: bit-exact vs decode.c's C versions / embedded_v2.py --
; proven per step by recon/approaches/dev_prod/ucsim_v23.py (emitted
; bytes + path + cause + trials + comps + n_refs + n_weak per capture vs
; the Python reference) at BOTH geometries, ND = 16 and ND = 48.
;
; v2.3 geometry ONLY: 3+3 markers (48 known bits, HTR below), a 6-byte
; check block = one CRC-16/CCITT-FALSE written three times, the
; INDEPENDENT per-byte majority with its confidence-ranked reference
; cross product, and RELAXATIONS A/B/C.  The superseded v2.2/v2.1 CRC8
; geometries live only in decode.c's C (USE_ASM_DEC=0 parity builds);
; nothing here reads a CHK_LEN.
;
; v2.3b (2026-09-07): the pipeline tail came BACK to hand assembly --
; 986 B against the compiled C's 1641 B CODE + 110 B CONST, which is
; what closed the 748 B production-link overflow of PROD_CLOSURE SS13.1.
;
; Unlike scan.s (unrolled for SPEED), everything here is rolled for
; SIZE: SDCC's stm8 codegen spends 10-14 bytes per source op on the
; 16/32-bit expressions below; these routines share one 16x16->32
; multiply, one 32/32 divide and one map_raw core.
;
; SDCC sdcccall(1) ABI (matches build/decode.asm's call sites):
;   8-bit arg in A, 16-bit arg in X; returns A (8), X (16), Y:X (32);
;   A/X/Y caller-saved.
;
; Fixed-point notes used throughout (ranges proven by the reference's
; assert battery at both geometries):
;   t <= ~25.7k cy, K <= 60000  ->  t*K < 2^31, y = (t*K>>11)+tau < 2^20
;   p_u/p_v = yf - (BIAS + k*512) fits s16  ->  computed in low-16 only
;   d = y - y_prev >= 0 (y is non-decreasing after the >=0 clamp)

    .module decode_asm

    .globl _ss_init
    .globl _ss_next
    ; C-side state / constants (decode.c)
    .globl _g_K
    .globl _g_tau
    .globl _g_NB
    .globl _g_yend
    ; sample scanner (defined below -- prod builds do not link scan.s)
    .globl _scan_cap
    .globl _scan_len
    .globl _scan_init
    .globl _scan_next
    .globl _scan_ra
    .globl _scan_rb
    .globl _scan_fa
    .globl _scan_fb
    .globl _scan_sfa

; ------------------------------------------------- build-time parameters
; sdasstm8 has no -D, so the two chase-budget constants arrive through a
; GENERATED include (gen_chase_cfg.py, driven by the Makefile's A_MAX /
; T_MAX variables -- the SINGLE source, shared with decode.c's
; -DA_MAX_CFG / -DT_MAX_CFG).  Defaults 11 / 131 = the shipped ledger, so
; an unset variable assembles byte-identically to the ledger image.
;   A_MAX_CFG  candidate-list capacity AND the R7 admission cap
;   A_MAX_M1 / A_MAX_X2   A_MAX-1 and 2*A_MAX, written out by the
;              generator so nothing rests on the assembler's expression
;              parser
;   T_MAX_CFG  residual-comparison budget == the per-frame false-accept
;              bound; z_comps is a u8, so 1..255 (gen_chase_cfg.py and
;              decode.c both refuse anything else)
    .include "chase_cfg.inc"

; ------------------------------------------------------------------ state
; ZERO PAGE (ABS): every access below assembles to the SHORT (1-byte
; address) forms -- the whole point of hand assembly on STM8.  The link
; must push REL DATA above this block: --data-loc (Makefile PRODFLAGS /
; the ucsim harness) and guard_prod.py enforce it.
    .area DZP (ABS)
    .org 0x0001

m_a:    .ds 2       ; mul16 operand A
m_b:    .ds 2       ; mul16 operand B / setp base temp
m_p:    .ds 4       ; mul16 product
m_y:    .ds 4       ; mr16 result (s32 y)
m_s:    .ds 1       ; sign-extension byte temp

q_yprev: .ds 4      ; ss: previous pulse y (u32, clamped)
q_n:     .ds 2      ; ss: bit index accumulator
q_have:  .ds 1      ; ss: have_y
q_pend:  .ds 1      ; ss: pending segment present
q_pk0:   .ds 2      ; ss: pending k0
q_pu:    .ds 2      ; ss: pending u (s16)
q_pv:    .ds 2      ; ss: pending v (s16)
q_pfam:  .ds 1      ; ss: pending family (slot of last high)
q_done:  .ds 1      ; ss: source exhausted
m_out:   .ds 2      ; ss_next: caller's Seg*
m_fa:    .ds 2      ; low16 of map_raw(scan_fa)
m_fb:    .ds 2      ; low16 of map_raw(scan_fb)

m_n:    .ds 4       ; udiv32 dividend -> quotient
m_d:    .ds 4       ; udiv32 divisor (preserved)
m_r:    .ds 4       ; udiv32 remainder
r_lo:   .ds 10      ; refine lower-half block:  se(4) sy(4) n(2)
r_hi:   .ds 10      ; refine upper-half block
r_melo: .ds 2
r_mehi: .ds 2
r_de:   .ds 2
r_dy:   .ds 4
r_dk:   .ds 4
r_me:   .ds 2
r_mylo: .ds 4
r_myhi: .ds 4
r_sgn:  .ds 1

_g_sg:   .ds 9      ; shared Seg: k0(2) k1(2) u(2) v(2) fam(1)
_dq_amin: .ds 2
_dq_amax: .ds 2
dq_inter: .ds 2     ; interior bitmask
dq_acap: .ds 2
dq_lo:   .ds 2
dq_hi:   .ds 2
dq_ahat: .ds 2
dq_afree: .ds 2
m_h0:    .ds 2      ; effective h0/h1 for this segment
m_h1:    .ds 2
m_h:     .ds 2      ; hinge h temp
m_L:     .ds 2
m_c:     .ds 2      ; scratch cost / argmin bc
m_c0:    .ds 2      ; online prefix min
m_c1:    .ds 2
m_e:     .ds 2      ; kk1 / a_bounds end
m_t:     .ds 2      ; t iterator
m_off:   .ds 2
m_k:     .ds 2      ; cand_insert k
w_tiep:  .ds 2      ; v_tiepend (asm-owned)
w_tieh:  .ds 2      ; tie_here
m_it:    .ds 1
m_ai:    .ds 1
m_ai2:   .ds 1
m_alo:   .ds 1
m_ahi:   .ds 1
m_best:  .ds 1
m_ka:    .ds 1      ; known_all
m_n1:    .ds 1      ; inter-bit counter
m_i0:    .ds 1      ; ins0 (0xFF = none)
; m_i1 is GONE: the SS6 ins1 size lever proved it dead (see SS6.4's
; merged interior loop below), and its byte is what keeps the REL DATA
; base where cap_arm.s's s_arm needs it -- see the --data-loc note.
m_i:     .ds 1      ; cand_insert i
m_j:     .ds 1
m_m:     .ds 1      ; margin byte
; ---- decision-pass state SHARED with the C pipeline tail --------------
; These live in the ABS zero page (this file's hot loops address them
; short-form) and are exported under their decode.c names, so the C tail
; -- and the host-parity build of the same C -- see one set of symbols.
_d_infeas: .ds 2    ; d_infeas   (R3 counter)
_d_laberr: .ds 2    ; d_laberr   (R4 counter)
_d_nseg:   .ds 2    ; d_nseg
_v_ncand:  .ds 1    ; v_ncand
_v_nweak:  .ds 2    ; v_nweak    (SS6.2)
_v_ntied:  .ds 2    ; v_ntied    (SS6.2)
_v_ndw:    .ds 2    ; v_ndw      (SS6.4 dead-window candidates)
m_vi:    .ds 1      ; violations counter

; ---- size-focused sample scanner state (replaces scan.s in prod) ----
_scan_cap: .ds 2    ; in: capture pointer
_scan_len: .ds 2    ; in: capture bytes (= loops)
_scan_ra:  .ds 2    ; out: rise bracket lo (cycles)
_scan_rb:  .ds 2    ; out: rise bracket hi
_scan_fa:  .ds 2    ; out: last-high time
_scan_fb:  .ds 2    ; out: fall bracket hi
_scan_sfa: .ds 1    ; out: slot of last high sample (family id)
p_i:       .ds 2    ; loop index
p_tb:      .ds 2    ; tbase = i * 40
p_ws:      .ds 2    ; wsum (s16)
p_tp:      .ds 2    ; t_prev
p_t:       .ds 2    ; current sample time
p_s:       .ds 1    ; slot 0..7
p_hp:      .ds 1    ; have_prev
p_ip:      .ds 1    ; in_pulse
p_se:      .ds 1    ; seen
p_dn:      .ds 1    ; done
p_lr:      .ds 2    ; low_run
c_lo:    .ds 4      ; calibration state (was decode.c statics)
c_hi:    .ds 4
c_n:     .ds 2
zh0c:    .ds 2      ; c_h0c
zh1c:    .ds 2      ; c_h1c
zd56:    .ds 2      ; c_d56[2] (s8 each)
zgap:    .ds 4      ; c_gap56[2]
; ---- SIZE LEVER (PROD_CLOSURE SS15.0 lever 1), taken for SS6.4 -------
; dec_info is OWNED HERE, in the ABS zero page: its ~18 DIRECT accesses
; each drop one address byte (short instead of long form) and `inc` drops
; two.  It is a SWAP, not growth -- labx0/labx1/labx0b/labx1b/c_c0 (20 B)
; move out to REL DATA below, and they are INDEXED-ONLY: sdasstm8 emits
; the 16-bit-offset form (0xDE/0xDF) for `(sym, x)` regardless of area,
; so those 25 accesses cost exactly the same there.
; decode.c declares it `extern` in USE_ASM_DEC builds and static-asserts
; sizeof(dec_info_t) == 23 against this reservation.
_dec_info: .ds 23
; calibration temps ALIAS the refine scratch (r_*): refine returns before
; calibrate runs and nothing else touches r_* -- zero extra zero-page.
w_llo   =    r_lo        ; label_interval lo out (2)  [r_lo+0..1]
w_lhi   =    r_lo+2      ; label_interval hi out (2)  [r_lo+2..3]
m_la    =    r_lo+4      ; cal 'a' argument (2)       [r_lo+4..5]
m_f     =    r_lo+6      ; family index (1)           [r_lo+6]
m_x0    =    r_lo+7      ; theta56 x0 (2)             [r_lo+7..8]
m_x1    =    r_hi        ; theta56 x1 (2)             [r_hi+0..1]
m_zlo   =    r_hi+2      ; (2)                        [r_hi+2..3]
m_zhi   =    r_hi+4      ; (2)                        [r_hi+4..5]
m_th    =    r_hi+6      ; theta (2)                  [r_hi+6..7]
m_hv    =    r_hi+8      ; have_theta (1)             [r_hi+8]
m_prev  =    r_dy+1      ; (2)                        [r_dy+1..2]
m_blo2  =    r_melo      ; best_lo (2)
m_bhi2  =    r_mehi      ; best_hi (2)
; chase temps ALIAS dead scratch the same way: m_cp lives in the udiv32
; dividend m_n, whose only users are seed/refine/mediv (all returned
; before the chase) and dec_eps_centi (called only after ws_decode_ex
; returns, when the chase is over) -- zero extra zero-page for the v2.2
; 4-byte check block.
m_cp    =    m_n         ; chase C' bytes (4; g_CHK = 3 or 4 used)
                         ;                            [m_n+0..3]
m_bg    =    r_de        ; (2)
m_no    =    r_dy        ; nocc (1)                   [r_dy+0]
m_wlo   =    r_dk        ; (2)                        [r_dk+0..1]
m_whi   =    r_dk+2      ; (2)                        [r_dk+2..3]
m_top   =    r_myhi      ; (2)                        [r_myhi+0..1]
m_htp   =    r_me        ; have_top (1)
m_cl1   =    r_me+1      ; clear1 (1)
m_bb    =    r_mylo      ; hist bin iterator (1)      [r_mylo+0]
m_hx    =    r_mylo+1    ; hist/labx index base (2)   [r_mylo+1..2]

; indexed-only arrays: no short-form benefit, so they live in REL DATA
; (keeps the zero page under 255 B)
    .area DATA
    ; d_costs is EXPORTED from v2.3 on: the C pipeline tail overlays its
    ; chase reference scratch (ch_ref / ch_val, 24 B) on it under the
    ; SS10.2 overlay rule -- d_costs is decision-pass scratch and the
    ; chase never calls decide(), so the two live ranges are disjoint.
    .globl _d_costs
_d_costs: .ds 32    ; u16 costs[16]
d_sm:    .ds 32     ; u16 suffix-min over [lo,hi]
; RELAXATION C: the candidate list is A_MAX_CFG entries (5 at v2.2, 11 at
; the v2.3 ledger, a Makefile variable since recon/AMAX_TMAX_SWEEP.md).
; It is REL DATA, not zero page, so growing it grows DATA and shrinks the
; stack region by 3 B per entry -- guard_prod.py checks both.
; ch_isd[] is GONE -- the C tail recomputes it as (v_cand_t[i] < ND8),
; which is what decode.c always did; the cached copy cost 11 B of RAM
; and a build loop for one comparison.
    ; SS15.0 lever 1: indexed-only calibration state, moved out of the
    ; zero page to make room for dec_info.  `(labx0, x)` and friends
    ; assemble to the same 3 bytes here as they did there.
labx0:   .ds 4
labx1:   .ds 4
labx0b:  .ds 4
labx1b:  .ds 4
c_c0:    .ds 4
_v_cand_t: .ds A_MAX_X2   ; v_cand_t[A_MAX], payload' bit index (u16)
_v_cand_m: .ds A_MAX_CFG  ; v_cand_m[A_MAX], margin, (m, index) ascending
_v_chkconf: .ds 12  ; v_chkconf[6] (u16): sum of a check byte's 8 bit
                    ; margins.  v2.3 RANKS the candidates of a check-byte
                    ; position that has no per-byte majority with these.

    .area DZP

    .area CODE

; ---------------------------------------------------------------- mul16
; m_a * m_b (u16 x u16) -> m_p (u32).  Clobbers A, X.
mul16:
    ld      a, *m_a+1
    ld      xl, a
    ld      a, *m_b+1
    mul     x, a                ; aL*bL
    ldw     *m_p+2, x
    ld      a, *m_a
    ld      xl, a
    ld      a, *m_b
    mul     x, a                ; aH*bH
    ldw     *m_p, x
    ld      a, *m_a+1
    ld      xl, a
    ld      a, *m_b
    mul     x, a                ; aL*bH
    call    mulacc
    ld      a, *m_a
    ld      xl, a
    ld      a, *m_b+1
    mul     x, a                ; aH*bL
mulacc:                         ; m_p[0..2] += X<<8 (fall-through reuse)
    pushw   x                   ; (1,sp) = XH, (2,sp) = XL
    ld      a, *m_p+2
    add     a, (2, sp)
    ld      *m_p+2, a
    ld      a, *m_p+1
    adc     a, (1, sp)
    ld      *m_p+1, a
    ld      a, *m_p
    adc     a, #0
    ld      *m_p, a
    popw    x
    ret

; ---------------------------------------------------------------- mr16
; X = t (u16 cycles) -> m_y = Y:X = ((u32)t * g_K >> 11) + g_tau  (s32),
; exactly decode.c map_raw().  Clobbers A, X, Y.
mr16:
    ldw     *m_a, x
    ldw     x, _g_K
    ldw     *m_b, x
    call    mul16               ; m_p = t*K  (< 2^31)
    call    shp11               ; A:X = m_p >> 11 (< 2^20)
    clr     *m_y
    ld      *m_y+1, a
    ldw     *m_y+2, x
    ; m_y += sext(g_tau)
    ld      a, _g_tau
    sll     a                       ; C = sign bit
    clr     a
    sbc     a, #0                   ; A = 0xFF if tau < 0 else 0
    ld      *m_s, a
    ld      a, *m_y+3
    add     a, _g_tau+1
    ld      *m_y+3, a
    ld      a, *m_y+2
    adc     a, _g_tau
    ld      *m_y+2, a
    ld      a, *m_y+1
    adc     a, *m_s
    ld      *m_y+1, a
    ld      a, *m_y
    adc     a, *m_s
    ld      *m_y, a
    ldw     y, *m_y
    ldw     x, *m_y+2
    ret

; ---------------------------------------------------------------- ss_init
_ss_init:
    call    _scan_init
    clrw    x
    ldw     *q_yprev, x
    ldw     *q_yprev+2, x
    ldw     *q_n, x
    ldw     *q_pk0, x
    ldw     *q_pu, x
    ldw     *q_pv, x
    clr     *q_pfam
    clr     *q_have
    clr     *q_pend
    clr     *q_done
    ret

; ---------------------------------------------------------------- helpers
; emit$: X = k1 candidate (uncapped n); writes caller's Seg from the
; pending slot with k1 = min(X, NB).  Clobbers A, X, Y.
emit:
    cpw     x, _g_NB
    jrc     00001$
    ldw     x, _g_NB
00001$:
    ldw     y, *m_out
    ldw     (2, y), x               ; k1
    ldw     x, *q_pk0
    ldw     (y), x                  ; k0
    ldw     x, *q_pu
    ldw     (4, y), x               ; u
    ldw     x, *q_pv
    ldw     (6, y), x               ; v
    ld      a, *q_pfam
    ld      (8, y), a               ; fam
    ret

; setp$: X = k; pending <- (k, u = yfa - base, v = yfb - base, sfa) with
; base = BIAS + k*512 = (k+1)<<9, all in low-16 (s16 result by contract).
setp:
    ldw     *q_pk0, x
    incw    x
    ld      a, xl
    clrw    x
    ld      xh, a
    sllw    x                   ; X = low16((k+1) << 9)
    ldw     *m_b, x
    ldw     x, *m_fa
    subw    x, m_b
    ldw     *q_pu, x
    ldw     x, *m_fb
    subw    x, m_b
    ldw     *q_pv, x
    ld      a, _scan_sfa
    ld      *q_pfam, a
    ret

; ---------------------------------------------------------------- ss_next
; X = Seg* out -> A = 1 (segment written) / 0 (stream end).
_ss_next:
    ldw     *m_out, x
00010$:                         ; while (!src_done)
    tnz     *q_done
    jreq    00040$
    jp      00030$
00040$:
    call    _scan_next
    tnz     a
    jrne    00011$
    mov     q_done, #1
    jp      00030$
00011$:
    ; y = clamp0(map_raw((ra+rb)>>1))
    ldw     x, _scan_ra
    addw    x, _scan_rb
    srlw    x
    call    mr16
    tnz     *m_y
    jrpl    00012$
    clrw    x                   ; y < 0 -> 0
    ldw     *m_y, x
    ldw     *m_y+2, x
00012$:
    ; if ((u32)y > y_end) { done; break; }   (C set iff yend < y)
    ld      a, _g_yend+3
    sub     a, *m_y+3
    ld      a, _g_yend+2
    sbc     a, *m_y+2
    ld      a, _g_yend+1
    sbc     a, *m_y+1
    ld      a, _g_yend
    sbc     a, *m_y
    jrnc    00013$
    mov     q_done, #1
    jp      00030$
00013$:
    ; have_y / gap accounting
    tnz     *q_have
    jrne    00014$
    clrw    x
    ldw     *q_n, x
    mov     q_have, #1
    jra     00015$
00014$:
    ; d = y - y_prev (>= 0, < 2^20); dn = (d + 256) >> 9; n += dn
    ldw     x, *m_y+2
    subw    x, q_yprev+2
    ld      a, *m_y+1
    sbc     a, *q_yprev+1           ; A:X = d (24-bit, byte0 of both is 0)
    addw    x, #0x0100
    adc     a, #0
    swapw   x                   ; XL = old XH
    ld      xh, a                   ; X = (A:XH_old) = (d+256) >> 8
    srlw    x                   ; X = dn
    jreq    00015$
    addw    x, q_n
    ldw     *q_n, x
00015$:
    ; y_prev = y; yfa/yfb low16
    ldw     x, *m_y
    ldw     *q_yprev, x
    ldw     x, *m_y+2
    ldw     *q_yprev+2, x
    ldw     x, _scan_fa
    call    mr16
    ldw     x, *m_y+2
    ldw     *m_fa, x
    ldw     x, _scan_fb
    call    mr16
    ldw     x, *m_y+2
    ldw     *m_fb, x
    ; dispatch on pend / n
    tnz     *q_pend
    jreq    00020$
    ldw     x, *q_n
    cpw     x, *q_pk0
    jrne    00016$
    ; spurious split: refresh the pending slot in place
    ldw     x, *q_pk0
    call    setp
    jp      00010$
00016$:
    ; emit pending; k1 = min(n, NB)
    ldw     x, *q_n
    call    emit
    ldw     x, *q_n
    cpw     x, _g_NB
    jrc     00017$
    clr     *q_pend
    mov     q_done, #1
    ld      a, #1
    ret
00017$:
    ldw     x, *q_n                 ; roll pending to n (pend stays 1)
    call    setp
    ld      a, #1
    ret
00020$:
    ; no pending segment yet
    ldw     x, *q_n
    cpw     x, _g_NB
    jrc     00021$
    mov     q_done, #1
    jra     00030$
00021$:
    ldw     x, *q_n
    call    setp
    mov     q_pend, #1
    jp      00010$

00030$:                         ; stream end: flush the pending segment
    tnz     *q_pend
    jreq    00031$
    clr     *q_pend
    ldw     x, _g_NB                ; tail k1 = NB
    call    emit
    ld      a, #1
    ret
00031$:
    clr     a
    ret

; ======================================================================
; refine() -- P2 residual-regression lock refinement, bit-exact port of
; decode.c's C version.  Uses mr16/mul16 above plus udiv32 below.
; Range notes (reference assert battery): e in [-256,255]; |me| <= 256 so
; de fits s16; sy sums < 2^27; my quotients < 2^20; K*de < 2^25;
; |de*(my-tau)| < 2^31 (asserted); dtau/tau commits are exact in low-16
; (C truncates to int16_t).
; ======================================================================

    .globl _refine
    .globl _g_ymid

    .area CODE

; ---------------------------------------------------------------- udiv32
; m_n / m_d -> quotient in m_n, remainder in m_r.  m_d preserved.
; Clobbers A, X, Y, m_s.
udiv32:
    clr     *m_r
    clr     *m_r+1
    clr     *m_r+2
    clr     *m_r+3
    mov     m_s, #32
00050$:
    sll     *m_n+3                  ; N <<= 1, MSB -> C
    rlc     *m_n+2
    rlc     *m_n+1
    rlc     *m_n
    rlc     *m_r+3                  ; C -> R
    rlc     *m_r+2
    rlc     *m_r+1
    rlc     *m_r
    ld      a, *m_r+3               ; R - D (trial)
    sub     a, *m_d+3
    ld      xl, a
    ld      a, *m_r+2
    sbc     a, *m_d+2
    ld      xh, a
    ld      a, *m_r+1
    sbc     a, *m_d+1
    ld      yl, a
    ld      a, *m_r
    sbc     a, *m_d
    jrc     00051$              ; R < D: restore (keep old R)
    ld      *m_r, a
    ld      a, yl
    ld      *m_r+1, a
    ldw     *m_r+2, x
    inc     *m_n+3                  ; quotient bit (bit0 is 0 after sll)
00051$:
    dec     *m_s
    jrne    00050$
    ret

; negmn: m_n = -m_n (32-bit two's complement)
negmn:
    clr     a
    sub     a, *m_n+3
    ld      *m_n+3, a
    clr     a
    sbc     a, *m_n+2
    ld      *m_n+2, a
    clr     a
    sbc     a, *m_n+1
    ld      *m_n+1, a
    clr     a
    sbc     a, *m_n
    ld      *m_n, a
    ret

; accum: Y = block (r_lo/r_hi), X = e (s16), m_y = y (u32 clamped):
;   se += sext(e); sy += y; n++
accum:
    ld      a, xh
    sll     a
    clr     a
    sbc     a, #0
    ld      *m_s, a                 ; sign byte of e
    pushw   x                   ; (1,sp)=eH (2,sp)=eL
    ld      a, (3, y)
    add     a, (2, sp)
    ld      (3, y), a
    ld      a, (2, y)
    adc     a, (1, sp)
    ld      (2, y), a
    ld      a, (1, y)
    adc     a, *m_s
    ld      (1, y), a
    ld      a, (y)
    adc     a, *m_s
    ld      (y), a
    popw    x
    ld      a, (7, y)
    add     a, *m_y+3
    ld      (7, y), a
    ld      a, (6, y)
    adc     a, *m_y+2
    ld      (6, y), a
    ld      a, (5, y)
    adc     a, *m_y+1
    ld      (5, y), a
    ld      a, (4, y)
    adc     a, *m_y
    ld      (4, y), a
    ld      a, (9, y)               ; n++ (16-bit, byte-wise: no LDW X,(o,Y))
    add     a, #1
    ld      (9, y), a
    ld      a, (8, y)
    adc     a, #0
    ld      (8, y), a
    ret


; ---- relocated into the vector-table gap (vectors_prod.s): 0x8004..0x8063
    .area VGAP (ABS)
    .org 0x8004

    .globl sot                  ; exported ONLY as the guard_prod.py anchor
                                ; for the VGAP window check (ABS areas
                                ; print addr 0 in sdld maps)
sot: .db 0, 4, 9, 13, 17, 21, 27, 32       ; O_CY[8]
swt: .db 0, 0xFF, 0, 2, 0, 0, 0, 1         ; W_CY[8] (s8)

; mediv: X = block -> X = se/n as s16 (C truncation; |result| <= 256)
mediv:
    pushw   x                   ; block ptr at (1,sp)
    ldw     x, (x)
    ldw     *m_n, x
    ldw     x, (1, sp)
    ldw     x, (2, x)
    ldw     *m_n+2, x
    clrw    x
    ldw     *m_d, x
    ldw     x, (1, sp)
    ldw     x, (8, x)
    ldw     *m_d+2, x
    popw    x
    clr     *r_sgn
    tnz     *m_n
    jrpl    00055$
    mov     r_sgn, #1
    call    negmn
00055$:
    call    udiv32
    ldw     x, *m_n+2
    tnz     *r_sgn
    jreq    00056$
    negw    x
00056$:
    ret

; mydiv: X = block -> m_n = sy/n (u32)
mydiv:
    pushw   x
    ldw     x, (4, x)
    ldw     *m_n, x
    ldw     x, (1, sp)
    ldw     x, (6, x)
    ldw     *m_n+2, x
    clrw    x
    ldw     *m_d, x
    ldw     x, (1, sp)
    ldw     x, (8, x)
    ldw     *m_d+2, x
    popw    x
    jp      udiv32

; hix: A = f (0/1) -> X = f*64 (c_hist row base within ov.hist).
; Lives in the vector gap: 7 bytes that the REL side no longer pays for.
hix:
    clrw    x
    tnz     a
    jreq    00510$
    ldw     x, #64
00510$:
    ret


    .area CODE

; ---------------------------------------------------------------- refine
_refine:
    ldw     x, #20                  ; zero r_lo + r_hi (adjacent)
00060$:
    clr     (r_lo-1, x)
    decw    x
    jrne    00060$
    call    _scan_init
00061$:                         ; pulse loop
    call    _scan_next
    tnz     a
    jreq    00070$
    ldw     x, _scan_ra
    addw    x, _scan_rb
    srlw    x
    call    mr16
    tnz     *m_y
    jrpl    00062$
    clrw    x                   ; clamp y >= 0
    ldw     *m_y, x
    ldw     *m_y+2, x
00062$:
    ld      a, _g_yend+3            ; if y > y_end: stop accumulating
    sub     a, *m_y+3
    ld      a, _g_yend+2
    sbc     a, *m_y+2
    ld      a, _g_yend+1
    sbc     a, *m_y+1
    ld      a, _g_yend
    sbc     a, *m_y
    jrc     00070$
    ; q = (y + 256) >> 9 ; e = low16(y) - low16(q << 9)
    ldw     x, *m_y+2
    ld      a, *m_y+1
    addw    x, #0x0100
    adc     a, #0
    swapw   x
    ld      xh, a
    srlw    x                   ; X = q
    ld      a, xl
    clrw    x
    ld      xh, a
    sllw    x                   ; X = low16(q << 9)
    ldw     *m_b, x
    ldw     x, *m_y+2
    subw    x, m_b              ; X = e (s16 exact)
    ; block = (y < mid_u) ? r_lo : r_hi
    ld      a, *m_y+3
    sub     a, _g_ymid+3
    ld      a, *m_y+2
    sbc     a, _g_ymid+2
    ld      a, *m_y+1
    sbc     a, _g_ymid+1
    ld      a, *m_y
    sbc     a, _g_ymid
    jrc     00063$
    ldw     y, #r_hi
    jra     00064$
00063$:
    ldw     y, #r_lo
00064$:
    call    accum
    jra     00061$

00069$:
    jp      00099$              ; short-branch trampoline to the ret
00070$:                         ; stats
    ldw     x, *r_lo+8
    cpw     x, #2
    jrc     00069$
    ldw     x, *r_hi+8
    cpw     x, #2
    jrc     00069$
    ldw     x, #r_lo
    call    mediv
    ldw     *r_melo, x
    ldw     x, #r_hi
    call    mediv
    ldw     *r_mehi, x
    ldw     x, #r_lo
    call    mydiv
    ldw     x, *m_n
    ldw     *r_mylo, x
    ldw     x, *m_n+2
    ldw     *r_mylo+2, x
    ldw     x, #r_hi
    call    mydiv
    ldw     x, *m_n
    ldw     *r_myhi, x
    ldw     x, *m_n+2
    ldw     *r_myhi+2, x
    ldw     x, *r_mehi              ; de = me_hi - me_lo (s16, |de| <= 512)
    subw    x, r_melo
    ldw     *r_de, x
    ld      a, *r_myhi+3            ; dy = my_hi - my_lo (s32)
    sub     a, *r_mylo+3
    ld      *r_dy+3, a
    ld      a, *r_myhi+2
    sbc     a, *r_mylo+2
    ld      *r_dy+2, a
    ld      a, *r_myhi+1
    sbc     a, *r_mylo+1
    ld      *r_dy+1, a
    ld      a, *r_myhi
    sbc     a, *r_mylo
    ld      *r_dy, a
    jrpl    00067$
    jp      00099$              ; dy < 0
00067$:
    ld      a, *r_dy
    or      a, *r_dy+1
    or      a, *r_dy+2
    or      a, *r_dy+3
    jrne    00068$
    jp      00099$              ; dy == 0
00068$:
    ; dk = (K * de) / dy  (sign of de; dy > 0)
    ldw     x, *r_de
    clr     *r_sgn
    tnzw    x
    jrpl    00071$
    negw    x
    mov     r_sgn, #1
00071$:
    ldw     *m_a, x
    ldw     x, _g_K
    ldw     *m_b, x
    call    mul16               ; m_p = K * |de| (< 2^25)
    ldw     x, *m_p
    ldw     *m_n, x
    ldw     x, *m_p+2
    ldw     *m_n+2, x
    ldw     x, *r_dy
    ldw     *m_d, x
    ldw     x, *r_dy+2
    ldw     *m_d+2, x
    call    udiv32
    tnz     *r_sgn
    jreq    00072$
    call    negmn
00072$:
    ldw     x, *m_n                 ; r_dk = signed dk
    ldw     *r_dk, x
    ldw     x, *m_n+2
    ldw     *r_dk+2, x
    ; me = (se_lo + se_hi) / (n_lo + n_hi) -> r_me (s16 exact)
    ld      a, *r_lo+3
    add     a, *r_hi+3
    ld      *m_n+3, a
    ld      a, *r_lo+2
    adc     a, *r_hi+2
    ld      *m_n+2, a
    ld      a, *r_lo+1
    adc     a, *r_hi+1
    ld      *m_n+1, a
    ld      a, *r_lo
    adc     a, *r_hi
    ld      *m_n, a
    clrw    x
    ldw     *m_d, x
    ldw     x, *r_lo+8
    addw    x, r_hi+8
    ldw     *m_d+2, x
    clr     *r_sgn
    tnz     *m_n
    jrpl    00073$
    mov     r_sgn, #1
    call    negmn
00073$:
    call    udiv32
    ldw     x, *m_n+2
    tnz     *r_sgn
    jreq    00074$
    negw    x
00074$:
    ldw     *r_me, x
    ; my = (sy_lo + sy_hi) / n_tot (m_d still holds n_tot)
    ld      a, *r_lo+7
    add     a, *r_hi+7
    ld      *m_n+3, a
    ld      a, *r_lo+6
    adc     a, *r_hi+6
    ld      *m_n+2, a
    ld      a, *r_lo+5
    adc     a, *r_hi+5
    ld      *m_n+1, a
    ld      a, *r_lo+4
    adc     a, *r_hi+4
    ld      *m_n, a
    call    udiv32              ; m_n = my (u32)
    ; m2 = my - sext(g_tau)  (s32)
    ld      a, _g_tau
    sll     a
    clr     a
    sbc     a, #0
    ld      *m_s, a
    ld      a, *m_n+3
    sub     a, _g_tau+1
    ld      *m_n+3, a
    ld      a, *m_n+2
    sbc     a, _g_tau
    ld      *m_n+2, a
    ld      a, *m_n+1
    sbc     a, *m_s
    ld      *m_n+1, a
    ld      a, *m_n
    sbc     a, *m_s
    ld      *m_n, a
    ; p_sign = sign(m2) ^ sign(de); |m2| (u24), |de|
    clr     *r_sgn
    tnz     *m_n
    jrpl    00075$
    mov     r_sgn, #1
    call    negmn
00075$:
    ldw     x, *r_de
    tnzw    x
    jrpl    00076$
    negw    x
    ld      a, *r_sgn
    xor     a, #1
    ld      *r_sgn, a
00076$:
    ; P = |de| * |m2|  = mul16(|de|, m2_lo16) + (m2_b1 * |de|) << 16
    ldw     *m_a, x                 ; |de|
    ldw     x, *m_n+2
    ldw     *m_b, x                 ; m2 low16
    ld      a, *m_n+1               ; m2 byte1 (<= 7)
    push    a
    call    mul16               ; m_p = |de| * lo16
    ldw     x, *m_p
    ldw     *m_n, x
    ldw     x, *m_p+2
    ldw     *m_n+2, x
    pop     a
    tnz     a
    jreq    00078$
    push    a
    ld      xl, a
    ld      a, *m_a+1               ; |de| low byte
    mul     x, a
    pushw   x                   ; high-word add: m_n[0..1] += mh*deL
    ld      a, *m_n+1
    add     a, (2, sp)
    ld      *m_n+1, a
    ld      a, *m_n
    adc     a, (1, sp)
    ld      *m_n, a
    popw    x
    pop     a
    ld      xl, a
    ld      a, *m_a                 ; |de| high byte (<= 2)
    mul     x, a                ; <= 14
    pushw   x
    ld      a, *m_n
    add     a, (2, sp)
    ld      *m_n, a
    popw    x
00078$:
    ; Q = P / dy
    ldw     x, *r_dy
    ldw     *m_d, x
    ldw     x, *r_dy+2
    ldw     *m_d+2, x
    call    udiv32
    ldw     x, *m_n+2               ; low16 of |Q|
    tnz     *r_sgn
    jreq    00079$
    negw    x
00079$:
    subw    x, r_me             ; dtau16 = Q - me
    ; K2 = zext(g_K) - dk; commit iff 46000 <= K2 <= 60000
    pushw   x
    ld      a, _g_K+1
    sub     a, *r_dk+3
    ld      *m_n+3, a
    ld      a, _g_K
    sbc     a, *r_dk+2
    ld      *m_n+2, a
    clr     a
    sbc     a, *r_dk+1
    ld      *m_n+1, a
    clr     a
    sbc     a, *r_dk
    ld      *m_n, a
    ld      a, *m_n
    or      a, *m_n+1
    jrne    00098$              ; negative or >= 65536
    ldw     x, *m_n+2
    cpw     x, #46000
    jrc     00098$
    cpw     x, #60001
    jrnc    00098$
    ldw     _g_K, x
    popw    x
    addw    x, _g_tau
    ldw     _g_tau, x
    ret
00098$:
    popw    x
00099$:
    ret

; ======================================================================
; seed() / dec_eps_centi() / set_gap56() -- the remaining 32-bit users,
; ported so USE_ASM_DEC builds link NO SDCC 32-bit library at all.
; ======================================================================

    .globl _seed
    .globl _dec_eps_centi
    .globl _set_gap56
    .globl _g_Wu11
    .globl _dec_info

    .area CODE

; shp11: A:X = m_p >> 11 (m_p < 2^31).  Shared by mr16/seed/set_gap56.
shp11:
    ldw     x, *m_p+1               ; (p >> 8) low16
    ld      a, *m_p                 ; (p >> 8) high8
    srl     a
    rrcw    x
    srl     a
    rrcw    x
    srl     a
    rrcw    x
    ret

; ---------------------------------------------------------------- seed
; P1 endpoint seed: first-rise / last-fall brackets pin K and tau.
; np reuses r_melo, flm r_mehi, r0m r_de (refine scratch, disjoint use).
_seed:
    clrw    x
    ldw     *r_melo, x              ; np = 0
    call    _scan_init
00100$:
    call    _scan_next
    tnz     a
    jreq    00104$
    ldw     x, _scan_fa             ; flm = (fa + fb) >> 1 (every pulse)
    addw    x, _scan_fb
    srlw    x
    ldw     *r_mehi, x
    ldw     x, *r_melo
    jrne    00102$
    ldw     x, _scan_ra             ; first pulse: r0m = (ra + rb) >> 1
    addw    x, _scan_rb
    srlw    x
    ldw     *r_de, x
00102$:
    ldw     x, *r_melo
    incw    x
    ldw     *r_melo, x
    jra     00100$
00104$:
    ldw     x, *r_melo              ; np < 8 -> fail
    cpw     x, #8
    jrc     00109$
    ldw     x, *r_mehi              ; flm <= r0m -> fail
    subw    x, r_de
    jrc     00109$
    jreq    00109$
    ldw     *m_d+2, x               ; K = g_Wu11 / (flm - r0m)
    clrw    x
    ldw     *m_d, x
    ldw     x, _g_Wu11
    ldw     *m_n, x
    ldw     x, _g_Wu11+2
    ldw     *m_n+2, x
    call    udiv32
    ldw     x, *m_n                 ; K_MIN <= K <= K_MAX else fail
    jrne    00109$
    ldw     x, *m_n+2
    cpw     x, #40000               ; RELAXATION A: v2.3 window
    jrc     00109$
    cpw     x, #64001               ; (was 46000 .. 60000)
    jrnc    00109$
    ldw     _g_K, x
    ldw     *m_a, x                 ; tau = 512 - ((r0m * K) >> 11)
    ldw     x, *r_de
    ldw     *m_b, x
    call    mul16
    ; RELAXATION A hardening: tau is an s16 by contract, and the WIDE
    ; window makes a late-first-rise / short-span capture reachable where
    ; 512 - ((r0m*K) >> 11) leaves s16.  The Python reference ASSERTS
    ; there; C and asm would silently wrap.  Refusing R1 instead keeps
    ; all three implementations bit-exact by construction.
    ; (p >> 11) must be <= 512 + 32767 = 33279, which also forces its
    ; high word to 0 -- shp11 returns only the low word, so test the
    ; high half of the product first: p >> 27 != 0 fails immediately.
    ld      a, *m_p                 ; p bits 31..24
    and     a, #0xF8                ; bits 31..27 -> nonzero means > 2^27
    jrne    00109$
    call    shp11
    cpw     x, #33280
    jrnc    00109$
    negw    x
    addw    x, #512
    ldw     _g_tau, x
    ld      a, #1
    ret
00109$:
    clr     a
    ret

; ---------------------------------------------------------- dec_eps_centi
; ((K_NOM - dec_info.K) * 10000) / dec_info.K, s16.  dec_info.K is at
; offset 9 (decode.h layout: 5 u8 fields + n_weak + n_tied before it).
_dec_eps_centi:
    ldw     x, #52429
    subw    x, _dec_info+9
    clr     *r_sgn
    tnzw    x
    jrpl    00110$
    negw    x
    mov     r_sgn, #1
00110$:
    ldw     *m_a, x
    ldw     x, #10000
    ldw     *m_b, x
    call    mul16               ; <= 75.7M
    ldw     x, *m_p
    ldw     *m_n, x
    ldw     x, *m_p+2
    ldw     *m_n+2, x
    clrw    x
    ldw     *m_d, x
    ldw     x, *_dec_info+9
    ldw     *m_d+2, x
    call    udiv32
    ldw     x, *m_n+2
    tnz     *r_sgn
    jreq    00111$
    negw    x
00111$:
    ret

; ---------------------------------------------------------- set_gap56
; c_gap56[0] = (6*K)>>11, c_gap56[1] = (5*K)>>11 (both <= 175)
_set_gap56:
    ld      a, #6
    call    gap1
    ldw     *zgap, x
    ld      a, #5
    call    gap1
    ldw     *zgap+2, x
    ret
gap1:
    clrw    x
    ld      xl, a
    ldw     *m_a, x
    ldw     x, _g_K
    ldw     *m_b, x
    call    mul16
    call    shp11
    ret

; ======================================================================
; P4 decision cluster: known_bit / a_bounds / hinge / argmin / decide /
; cand_insert / decide_pass.  Replaces ~1470 B of SDCC output.
; The per-bit margin scan uses an exactly-equivalent prefix-min (online)
; + suffix-min (precomputed d_sm[]) formulation of the C's inner loops:
;   c0m(off) = min costs[a in lo..min(off,hi)]   (empty -> 0xFFFF)
;   c1m(off) = min costs[a in max(lo,off+1)..hi] (empty -> 0xFFFF)
; identical values, O(L+W) instead of O(L*W).
; ======================================================================

    .globl _decide_pass
    .globl _known_bit
    .globl _a_bounds_sg
    .globl _g_sg
    .globl _dq_amin
    .globl _dq_amax
    .globl _g_NBmHT
    .globl _g_PPHI
    .globl _g_ND8

    .globl _ov
    ; decision-pass state the C pipeline tail reads (see the v2.3 note
    ; where the hand-assembled chase used to be)
    .globl _v_cand_t
    .globl _v_cand_m
    .globl _v_ncand
    .globl _v_nweak
    .globl _v_ndw
    .globl _v_ntied
    .globl _v_chkconf
    .globl _d_infeas
    .globl _d_laberr
    .globl _d_nseg

    .area CODE

; -------------------------------------------------------------- known_bit
; X = t -> A = 0 / 1 / 0xFF(-1).  C-ABI compatible (calibrate calls it).
; v2.3 markers are 3+3: 24 header bits, 24 trailer bits.  The template
; comes from HTR -- the BIT-REVERSED marker bytes the pipeline tail's
; violation popcount also uses: wire bit (7-(t&7)) of the plain byte IS
; bit (t&7) of the reversed one, so this shifts RIGHT where the old
; MSB-first HT table shifted left, and ONE 6-byte table serves both.
_known_bit:
    cpw     x, #24
    jrc     00130$              ; header bits 0..23
    subw    x, _g_NBmHT
    jrc     00132$              ; interior
    addw    x, #24              ; trailer bits at HT[24..47]
00130$:
    ld      a, xl
    and     a, #7
    inc     a
    ld      *m_s, a                 ; shift count = (t&7)+1
    srlw    x
    srlw    x
    srlw    x
    ld      a, (HTR, x)
00131$:
    srl     a
    dec     *m_s
    jrne    00131$
    clr     a
    rlc     a                       ; A = the bit
    ret
00132$:
    ld      a, #0xFF
    ret

; ------------------------------------------------------------ a_bounds_sg
; a_bounds over g_sg -> dq_amin/dq_amax (C calibrate uses this too).
_a_bounds_sg:
    clrw    x
    ldw     *_dq_amin, x
    ldw     x, *_g_sg+2
    subw    x, _g_sg
    ldw     *_dq_amax, x
    ldw     x, *_g_sg+2             ; e = min(k1, NB)
    cpw     x, _g_NB
    jrc     00140$
    ldw     x, _g_NB
00140$:
    ldw     *m_e, x
    ldw     x, *_g_sg
    ldw     *m_t, x
00141$:
    ldw     x, *m_t
    cpw     x, *m_e
    jrnc    00149$
    call    _known_bit
    cp      a, #1
    jrne    00142$
    ldw     x, *m_t                 ; kb == 1: amin = max(amin, t-k0+1)
    subw    x, _g_sg
    incw    x
    cpw     x, *_dq_amin
    jrule   00144$
    ldw     *_dq_amin, x
    jra     00144$
00142$:
    tnz     a
    jrne    00144$              ; -1: nothing
    ldw     x, *m_t                 ; kb == 0: amax = min(amax, t-k0)
    subw    x, _g_sg
    cpw     x, *_dq_amax
    jrnc    00144$
    ldw     *_dq_amax, x
00144$:
    ldw     x, *m_t
    incw    x
    ldw     *m_t, x
    jra     00141$
00149$:
    ret

; ---------------------------------------------------------------- hcost
; X = h -> X = hinge(u, v, h) = max(0, u-h, h-v); g_sg.u/.v.  Keeps m_h.
hcost:
    ldw     *m_h, x
    ldw     x, *_g_sg+4
    subw    x, m_h              ; u - h (s16)
    jrsgt   00150$
    clrw    x
00150$:
    ldw     y, x                    ; Y = g so far
    ldw     x, *m_h
    subw    x, _g_sg+6          ; h - v (s16)
    jrsgt   00151$
    ldw     x, y
    ret
00151$:
    pushw   y                   ; g
    cpw     x, (1, sp)
    popw    y
    jrugt   00152$
    ldw     x, y
00152$:
    ret

; ----------------------------------------------------------------- itst
; A = (u < m_h && m_h <= v), signed.
itst:
    ldw     x, *_g_sg+4
    cpw     x, *m_h
    jrslt   00153$
    clr     a
    ret
00153$:
    ldw     x, *m_h
    cpw     x, *_g_sg+6
    jrsle   00154$
    clr     a
    ret
00154$:
    ld      a, #1
    ret

; --------------------------------------------------------------- setbit
; dq_inter |= 1 << m_ai
setbit:
    ld      a, *m_ai
    and     a, #7
    ld      *m_s, a
    ld      a, #1
    tnz     *m_s
    jreq    00156$
00155$:
    sll     a
    dec     *m_s
    jrne    00155$
00156$:
    push    a
    ld      a, *m_ai
    cp      a, #8
    pop     a
    jrc     00157$
    or      a, *dq_inter            ; bits 8..15 live in the high byte
    ld      *dq_inter, a
    ret
00157$:
    or      a, *dq_inter+1
    ld      *dq_inter+1, a
    ret

; --------------------------------------------------------------- getbit
; A = (dq_inter >> m_ai2) & 1
getbit:
    ld      a, *m_ai2
    and     a, #7
    inc     a
    ld      *m_s, a
    ld      a, *m_ai2
    cp      a, #8
    jrc     00158$
    ld      a, *dq_inter
    jra     00159$
00158$:
    ld      a, *dq_inter+1
00159$:
    srl     a
    dec     *m_s
    jrne    00159$
    clr     a
    rlc     a
    ret

; --------------------------------------------------------------- argmin
; over [m_alo..m_ahi]: (cost, interior-preferred-on-tie, smallest a).
; -> X = best.  Mirrors C argmin_ab exactly (bc=0xFFFF, bi=1 initial).
argmin:
    ldw     x, #0xFFFF
    ldw     *m_c, x
    mov     m_it, #1
    ld      a, *m_alo
    ld      *m_best, a
    ld      *m_ai2, a
00160$:
    ld      a, *m_ai2
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (_d_costs, x)
    cpw     x, *m_c
    jrc     00161$              ; strictly better
    jrne    00163$              ; worse
    call    getbit              ; equal: take iff it && !bi
    tnz     a
    jreq    00163$
    tnz     *m_it
    jrne    00163$
    mov     m_it, #1
    ld      a, *m_ai2
    ld      *m_best, a
    jra     00163$
00161$:
    ldw     *m_c, x
    call    getbit
    ld      *m_it, a
    ld      a, *m_ai2
    ld      *m_best, a
00163$:
    ld      a, *m_ai2
    inc     a
    ld      *m_ai2, a
    cp      a, *m_ahi
    jrule   00160$
    clrw    x
    ld      a, *m_best
    ld      xl, a
    ret

; --------------------------------------------------------------- addd56
; m_h0 += sext(A); m_h1 += sext(A)
addd56:
    clrw    x
    ld      xl, a
    tnz     a
    jrpl    00165$
    addw    x, #0xFF00
00165$:
    ldw     *m_h, x
    ldw     x, *m_h0
    addw    x, m_h
    ldw     *m_h0, x
    ldw     x, *m_h1
    addw    x, m_h
    ldw     *m_h1, x
    ret

; ---------------------------------------------------------------- decide
; g_sg -> d_costs[0..acap], dq_inter, dq_acap/afree/lo/hi/ahat.
dq_decide:
    ldw     x, *_g_sg+2
    subw    x, _g_sg
    ldw     *m_L, x                 ; L = k1-k0 (>= 1)
    cpw     x, #16
    jrc     00170$
    ldw     x, #15
00170$:
    ldw     *dq_acap, x
    ldw     x, *zh0c
    ldw     *m_h0, x
    ldw     x, *zh1c
    ldw     *m_h1, x
    ld      a, *_g_sg+8             ; fam
    cp      a, #5
    jrne    00171$
    ld      a, *zd56
    call    addd56
    jra     00172$
00171$:
    cp      a, #6
    jrne    00172$
    ld      a, *zd56+1
    call    addd56
00172$:
    clrw    x
    ldw     *dq_inter, x
    clr     *m_ai
00173$:                         ; per hypothesis a
    ld      a, *m_ai
    jrne    00174$
    ldw     x, *m_h0                ; a == 0
    call    hcost
    ldw     *m_c, x
    call    itst
    ld      *m_it, a
    jra     00177$
00174$:
    dec     a                       ; a >= 1: h = (a-1)*512 + h1e
    sll     a
    clrw    x
    ld      xh, a
    addw    x, m_h1
    call    hcost
    ldw     *m_c, x
    call    itst
    ld      *m_it, a
    ld      a, *m_ai                ; if a < L: h2 = a*512 + h0e
    clrw    x
    ld      xl, a
    cpw     x, *m_L
    jrnc    00177$
    ld      a, *m_ai
    sll     a
    clrw    x
    ld      xh, a
    addw    x, m_h0
    call    hcost
    pushw   x
    call    itst
    tnz     a
    jreq    00175$
    mov     m_it, #1
00175$:
    popw    x
    cpw     x, *m_c
    jrnc    00177$
    ldw     *m_c, x
00177$:                         ; store costs[a] + interior bit
    ld      a, *m_ai
    sll     a
    clrw    x
    ld      xl, a
    ldw     y, *m_c
    ldw     (_d_costs, x), y
    tnz     *m_it
    jreq    00178$
    call    setbit
00178$:
    ld      a, *m_ai
    inc     a
    ld      *m_ai, a
    cp      a, *dq_acap+1
    jrule   00173$
    ; a_free = argmin(0, acap)
    clr     *m_alo
    ld      a, *dq_acap+1
    ld      *m_ahi, a
    call    argmin
    ldw     *dq_afree, x
    call    _a_bounds_sg
    ldw     x, *_dq_amin            ; lo = amin (>= 0)
    ldw     *dq_lo, x
    ldw     x, *_dq_amax            ; hi = min(amax, acap)
    cpw     x, *dq_acap
    jrc     00179$
    ldw     x, *dq_acap
00179$:
    ldw     *dq_hi, x
    ldw     x, *dq_lo
    cpw     x, *dq_hi
    jrule   00180$
    clrw    x                   ; lo > hi: full range
    ldw     *dq_lo, x
    ldw     x, *dq_acap
    ldw     *dq_hi, x
00180$:
    ld      a, *dq_lo+1
    ld      *m_alo, a
    ld      a, *dq_hi+1
    ld      *m_ahi, a
    call    argmin
    ldw     *dq_ahat, x
    ret

; ------------------------------------------------------------ cand_insert
; X = payload' bit index k, A = margin m: sorted top-5 insert
; (key: margin then index, ascending) -- exactly C cand_insert.
candi:
    ld      *m_m, a
    ldw     *m_k, x
    ld      a, *_v_ncand
    ld      *m_i, a
00185$:                         ; while (i > 0 && cand_m[i-1] > m) i--
    tnz     *m_i
    jreq    00186$
    ld      a, *m_i
    dec     a
    clrw    x
    ld      xl, a
    ld      a, (_v_cand_m, x)
    cp      a, *m_m
    jrule   00186$
    dec     *m_i
    jra     00185$
00186$:
    ld      a, *m_i
    cp      a, #A_MAX_CFG           ; A_MAX (RELAXATION C)
    jrc     00187$
    ret                         ; list full below this margin
00187$:
    ld      a, *_v_ncand             ; j = min(ncand, A_MAX-1)
    cp      a, #A_MAX_CFG
    jrc     00188$
    ld      a, #A_MAX_M1
00188$:
    ld      *m_j, a
00189$:                         ; shift [i..j-1] up
    ld      a, *m_j
    cp      a, *m_i
    jrule   00190$
    ld      a, *m_j
    sll     a
    clrw    x
    ld      xl, a
    pushw   x
    ldw     x, (_v_cand_t-2, x)
    ldw     y, x
    popw    x
    ldw     (_v_cand_t, x), y
    ld      a, *m_j
    clrw    x
    ld      xl, a
    ld      a, (_v_cand_m-1, x)
    ld      (_v_cand_m, x), a
    dec     *m_j
    jra     00189$
00190$:
    ld      a, *m_i
    sll     a
    clrw    x
    ld      xl, a
    ldw     y, *m_k
    ldw     (_v_cand_t, x), y
    ld      a, *m_i
    clrw    x
    ld      xl, a
    ld      a, *m_m
    ld      (_v_cand_m, x), a
    ld      a, *_v_ncand
    cp      a, #A_MAX_CFG           ; A_MAX
    jrnc    00191$
    inc     a
    ld      *_v_ncand, a
00191$:
    ret

; ---------------------------------------------------------------- dwtst
; SS6.4 DEAD-WINDOW test for the bit at offset m_off inside the current
; segment -> A = 1 if the bit is a DW candidate, else 0.
;
; The bit's DISCRIMINATING INTERVAL is (hb + h0e, hb + h1e] with
; hb = off * BIT_U; the whole observation is the fall bracket (u, v],
; whose ends are ADJACENT samples.  With
;     ga = (hb + h0e) <= u        gb = v < (hb + h1e)
; ga != gb is the healthy case (exactly one candidate fall position is
; inside the bracket, i.e. a sample DECIDED the bit) and ga == gb is
; degenerate -- the bracket inside the window (a transition at NEITHER
; fitted boundary) or the window inside the bracket (no sample in it).
;
; A accumulates +1 for ga and -1 for gb, so A == 0 iff ga == gb, and the
; routine RETURNS WITH Z SET IFF the bit is a DW candidate (RET does not
; touch the flags, and LD A,#imm does -- so the early exit is honest).
; off >= DW_OFF_MAX (64) is not a candidate: hb would leave s16
; (63*512 + h1e <= 32680 < 32768 is the bound), and it changes nothing
; because h0e >= 64, so once hb > v the test already answers "healthy" of
; its own accord.  Y is free here -- the bit loop uses only A and X.
dwtst:
    ldw     x, *m_off
    cpw     x, #64                  ; DW_OFF_MAX
    jrc     00193$
    ld      a, #1                   ; off >= 64: healthy (Z clear)
    ret
00193$:
    ld      a, *m_off+1             ; off < 64, so hb = off << 9 is
    sll     a                       ; hb_hi = off*2, hb_lo = 0
    ld      xh, a
    clr     a
    ld      xl, a                   ; X = hb
    ldw     y, x
    addw    x, m_h0
    clr     a                       ; BEFORE the compare: CLR touches N/Z,
                                    ; which the SIGNED branch below reads
    cpw     x, *_g_sg+4             ; u  (short form: _g_sg is ABS zero
                                    ; page, so 2 B instead of 3)
    jrsgt   00194$
    inc     a                       ; ga: (hb + h0e) <= u
00194$:
    ldw     x, y
    addw    x, m_h1
    cpw     x, *_g_sg+6             ; v
    jrsle   00195$
    dec     a                       ; gb: v < (hb + h1e)
00195$:
    tnz     a                       ; Z iff ga == gb
    ret

; ------------------------------------------------------------ decide_pass
_decide_pass:
    ldw     x, _g_NB                ; zero d_bits[0..NBB-1] (NBB = NB/8)
    srlw    x
    srlw    x
    srlw    x
00200$:
    clr     (_ov-1, x)
    decw    x
    jrne    00200$
    clrw    x
    ldw     *_d_infeas, x
    ldw     *_d_laberr, x
    ldw     *_d_nseg, x
    ldw     *_v_nweak, x
    ldw     *_v_ntied, x
    ldw     *_v_ndw, x
    clr     *_v_ncand
    ldw     x, #12                  ; v_chkconf[6] = 0  (v2.3)
00199$:
    decw    x
    clr     (_v_chkconf, x)
    jrne    00199$
    ldw     x, #0xFFFF
    ldw     *w_tiep, x              ; v_tiepend = -1
    call    _ss_init
00201$:                         ; segment loop
    ldw     x, #_g_sg
    call    _ss_next
    tnz     a
    jrne    00202$
    ret
00202$:
    ldw     x, *_d_nseg
    incw    x
    ldw     *_d_nseg, x
    ldw     x, *_g_sg               ; if (k0 >= NB) continue
    cpw     x, _g_NB
    jrc     00203$
    jra     00201$
00203$:
    call    dq_decide
    ld      a, *dq_ahat+1           ; c_hat = costs[ahat]
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (_d_costs, x)
    cpw     x, #160
    jrule   00204$
    ldw     x, *_d_infeas
    incw    x
    ldw     *_d_infeas, x
00204$:
    ldw     x, *_g_sg+2             ; kk1 = min(k1, NB)
    cpw     x, _g_NB
    jrc     00205$
    ldw     x, _g_NB
00205$:
    ldw     *m_e, x
    mov     m_ka, #1            ; known_all over [k0, kk1)
    ldw     x, *_g_sg
    ldw     *m_t, x
00206$:
    ldw     x, *m_t
    cpw     x, *m_e
    jrnc    00208$
    call    _known_bit
    tnz     a
    jrpl    00207$
    clr     *m_ka
    jra     00208$
00207$:
    ldw     x, *m_t
    incw    x
    ldw     *m_t, x
    jra     00206$
    ; SIZE LEVER: ONE pass over a = 0..acap now yields both interior
    ; counts -- m_n1 over the WHOLE hypothesis range (the `dead` detector
    ; that suppresses a label error inside a dead marker window) and,
    ; restricted to [lo, hi], m_best = nins plus m_i0 = ins0 (the tie
    ; mark).  The two loops were 60 B; merged they are 49 B, and the
    ; values are identical by construction -- the second loop's range is
    ; a SUBSET of the first's, and lo/hi are in 0..15 so the low byte of
    ; each is the whole comparison (as the old loops already assumed).
00208$:
    mov     m_i0, #0xFF             ; ins0 = none
    clr     *m_n1                   ; interior over 0..acap  (dead)
    clr     *m_best                 ; interior over [lo,hi]  (nins)
    clr     *m_ai2
00209$:
    call    getbit
    tnz     a
    jreq    00210$
    inc     *m_n1
    ld      a, *m_ai2               ; lo <= a <= hi ?
    cp      a, *dq_lo+1
    jrc     00210$
    cp      a, *dq_hi+1
    jrugt   00210$
    inc     *m_best
    ld      a, *m_i0
    cp      a, #0xFF
    jrne    00210$
    ld      a, *m_ai2
    ld      *m_i0, a
00210$:
    ld      a, *m_ai2
    inc     a
    ld      *m_ai2, a
    cp      a, *dq_acap+1
    jrule   00209$
    tnz     *m_ka                   ; laberr: known_all && lo==hi &&
    jreq    00212$              ;         afree != lo && !dead
    ld      a, *m_n1
    cp      a, #2
    jrnc    00212$
    ldw     x, *dq_lo
    cpw     x, *dq_hi
    jrne    00212$
    ldw     x, *dq_afree
    cpw     x, *dq_lo
    jreq    00212$
    ldw     x, *_d_laberr
    incw    x
    ldw     *_d_laberr, x
00212$:
    ldw     x, #0xFFFF              ; tie_here = -1
    ldw     *w_tieh, x
    ld      a, *m_best
    cp      a, #2
    jrc     00218$
    ; SIZE LEVER: the v1 form also tested `a_hat in {ins0, ins1}`, which
    ; is ALWAYS TRUE -- an interior boundary has hinge cost 0 and argmin's
    ; key is (cost, NOT interior, index) ascending, so a non-empty
    ; interior set forces a_hat == ins0.  Proven in
    ; dev_lever_b/ins0_proof.py over 1 619 577 decided segments of every
    ; corpus and both fuzz sets, 0 counterexamples.  ins1 and the test
    ; are gone; m_i1 is now unused.
    clrw    x                   ; tt = k0 + ins0; if (tt < NB) tie
    ld      a, *m_i0
    ld      xl, a
    addw    x, _g_sg
    cpw     x, _g_NB
    jrnc    00218$
    ldw     *w_tieh, x
00218$:
    ldw     x, #0xFFFF              ; suffix-min d_sm over [lo..hi]
    ldw     *m_c, x
    ld      a, *dq_hi+1
    ld      *m_ai2, a
00219$:
    ld      a, *m_ai2
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (_d_costs, x)
    cpw     x, *m_c
    jrnc    00220$
    ldw     *m_c, x
00220$:
    ld      a, *m_ai2
    sll     a
    clrw    x
    ld      xl, a
    ldw     y, *m_c
    ldw     (d_sm, x), y
    ld      a, *m_ai2
    cp      a, *dq_lo+1
    jreq    00221$
    dec     *m_ai2
    jra     00219$
00221$:
    ldw     x, #0xFFFF              ; c0m online
    ldw     *m_c0, x
    ldw     x, *_g_sg
    ldw     *m_t, x
00222$:                         ; per-bit loop
    ldw     x, *m_t
    cpw     x, *m_e
    jrc     00223$
    jp      00240$
00223$:
    ldw     x, *m_t
    subw    x, _g_sg
    ldw     *m_off, x
    cpw     x, *dq_ahat             ; bit: off < ahat
    jrnc    00226$
    ldw     x, *m_t                 ; BSET(d_bits, t): LSB-first in byte
    ld      a, xl
    and     a, #7
    ld      *m_s, a
    srlw    x
    srlw    x
    srlw    x
    ld      a, #1
    tnz     *m_s
    jreq    00225$
00224$:
    sll     a
    dec     *m_s
    jrne    00224$
00225$:
    or      a, (_ov, x)
    ld      (_ov, x), a
00226$:
    ldw     x, *m_off               ; c0m: lo <= off <= hi
    cpw     x, *dq_lo
    jrc     00228$
    cpw     x, *dq_hi
    jrugt   00228$
    ld      a, *m_off+1
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (_d_costs, x)
    cpw     x, *m_c0
    jrnc    00228$
    ldw     *m_c0, x
00228$:
    ldw     x, *m_off               ; c1m = sm[max(lo, off+1)] or 0xFFFF
    incw    x
    cpw     x, *dq_lo
    jrnc    00229$
    ldw     x, *dq_lo
00229$:
    cpw     x, *dq_hi
    jrule   00230$
    ldw     x, #0xFFFF
    jra     00231$
00230$:
    ld      a, xl
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (d_sm, x)
00231$:
    ldw     *m_c1, x
    ldw     x, *m_c0                ; m = 255 | min(255, |c0m - c1m|)
    cpw     x, #0xFFFF
    jreq    00233$
    ldw     x, *m_c1
    cpw     x, #0xFFFF
    jreq    00233$
    ldw     x, *m_c0
    subw    x, m_c1
    jrpl    00232$
    negw    x
00232$:
    cpw     x, #255
    jrc     00234$
00233$:
    ldw     x, #255
00234$:
    ld      a, xl
    ld      *m_m, a
    ldw     x, *m_t                 ; tie overrides -> m = 0
    cpw     x, *w_tieh
    jreq    00235$
    cpw     x, *w_tiep
    jrne    00236$
00235$:
    clr     *m_m
00236$:
    ldw     x, *m_t                 ; payload' window (PP_LO = 24)
    cpw     x, #24
    jrc     00239$
    cpw     x, _g_PPHI
    jrnc    00239$
    ; ---- v2.3 chk_conf: k = t - 24; when k >= ND8 this is a CHECK bit,
    ; so add its margin to v_chkconf[(k - ND8) >> 3] (u16, big-endian
    ; like every other ldw-stored word here).  Only the 48 check bits
    ; reach the add; the C pipeline tail RANKS the candidates of a
    ; split check-byte position with these sums.
    subw    x, #24                  ; X = k
    cpw     x, _g_ND8
    jrc     00238$
    subw    x, _g_ND8
    srlw    x
    srlw    x
    srlw    x                       ; X = (k - ND8) >> 3   (0..5)
    sllw    x                       ; X = word offset (0,2,..,10)
    ld      a, (_v_chkconf+1, x)    ; low byte += m
    add     a, *m_m
    ld      (_v_chkconf+1, x), a
    jrnc    00238$
    inc     (_v_chkconf, x)         ; carry into the high byte
00238$:
    ld      a, *m_m                 ; weak?  (margin <= MG_MAX)
    cp      a, #8
    jrugt   00243$
    ldw     x, *_v_nweak
    incw    x
    ldw     *_v_nweak, x
    tnz     *m_m
    jrne    00237$
    ldw     x, *_v_ntied
    incw    x
    ldw     *_v_ntied, x
00237$:
    jra     00244$
00243$:                         ; SS6.4: margin > MG_MAX -- degenerate
    call    dwtst               ; geometry admits it anyway (Z = DW)
    jrne    00239$
    ldw     x, *_v_ndw
    incw    x
    ldw     *_v_ndw, x
00244$:
    ldw     x, *m_t
    subw    x, #24
    ld      a, *m_m
    call    candi
00239$:
    ldw     x, *m_t
    incw    x
    ldw     *m_t, x
    jp      00222$
00240$:                         ; segment epilogue: tiepend consume/set
    ldw     x, *w_tiep
    jrmi    00241$
    cpw     x, *m_e
    jrnc    00241$
    ldw     x, #0xFFFF
    ldw     *w_tiep, x
00241$:
    ldw     x, *w_tieh
    jrmi    00242$
    cpw     x, *m_e
    jrc     00242$
    ldw     *w_tiep, x
00242$:
    jp      00201$

; ======================================================================
; v2.3 pipeline tail -- NOT here any more, and deliberately so.
;
; v2.2 hand-assembled the CRC8 chase and ws_decode_ex in this file.  v2.3
; keeps the STREAMING LAYER in assembly (that is where the ~1470 B of
; SDCC codegen savings live: scan / seed / refine / ss_next / decide /
; decide_pass / calibrate, all 16- and 32-bit expression heavy) and
; compiles the pipeline TAIL from decode.c even in USE_ASM_DEC builds:
;
;   crc16 / syn16 / maj3 / rank3 / ref_build / ref_at / ch_match /
;   try_trial / chase_singles / chase_pairs / chase / ws_decode_ex
;
; WHY: the v2.3 tail is the intricate part -- a 16-bit residual, an
; independent per-byte majority, a confidence-ranked reference CROSS
; PRODUCT and a residual-comparison BUDGET.  Compiling it from the same
; source the host-parity build uses makes it bit-exact with
; embedded_v2.py BY CONSTRUCTION rather than by a second hand-audit, and
; it is straight-line byte code that SDCC compiles about as tightly as
; hand assembly would.  The streaming layer, which is where hand
; assembly actually pays, is untouched.
;
; This file therefore exports the decision-pass state the C tail reads:
;   _v_cand_t / _v_cand_m / _v_ncand   the candidate list
;   _v_nweak / _v_ntied                the SS6.2 counters
;   _v_ndw                             the SS6.4 counter
;   _v_chkconf                         per-check-byte confidence (v2.3)
;   _d_infeas / _d_laberr / _d_nseg    the R3/R4 counters
; plus _g_K / _g_tau / _ov / _known_bit, which it already exported.
; ======================================================================

; ======================================================================
; P3 calibration cluster: label_interval / cal_cloud / cal_add /
; width_fit / theta56 / calibrate.
; Bit-exact ports; state in the zero page; c_hist = ov.hist (indexed).
; _calibrate is exported from v2.3 on: the C pipeline tail
; (ws_decode_ex) drives the four passes now that the hand-assembled
; ws_decode_ex is gone.
; ======================================================================

    .globl _calibrate

    .area CODE

; la_int: X = a (s16); g_sg.u/.v, m_L = k1-k0 -> A = cls (0/1/0xFF),
; *w_llo = u-off, *w_lhi = v-off.  Exactly label_interval().
la_int:
    ldw     *m_la, x
    tnzw    x
    jrne    00500$
    clrw    x                   ; a == 0: off = 0, cls = 0
    clr     a
    jp      00507$
00500$:
    cpw     x, *m_L
    jreq    00509$              ; a == L: off = (L-1)*512, cls = 1 --
                                ; shares the d1<=d0 tail (m_la == L here)
00501$:
    ; mid = (u+v)>>1 (arithmetic)
    ldw     x, *_g_sg+4
    addw    x, _g_sg+6
    sraw    x
    ldw     *m_h, x             ; mid
    ; d1 = |mid - ((a-1)*512 + 308)|
    ldw     x, *m_la
    decw    x
    ld      a, xl
    clrw    x
    ld      xh, a
    sllw    x
    addw    x, #308
    negw    x
    addw    x, *m_h             ; mid - h1pos
    jrpl    00502$
    negw    x
00502$:
    ldw     *m_c, x             ; d1
    ; d0 = |mid - (a*512 + 154)|
    ld      a, *m_la+1
    clrw    x
    ld      xh, a
    sllw    x
    addw    x, #154
    negw    x
    addw    x, *m_h
    jrpl    00503$
    negw    x
00503$:
    ldw     *m_c1, x            ; d0
    ; if (min(d0,d1) > 246) return -1
    cpw     x, *m_c
    jrsgt   00504$
    ; d0 <= d1: min = d0 (in X)
    jra     00505$
00504$:
    ldw     x, *m_c             ; min = d1
00505$:
    cpw     x, #246
    jrsle   00506$
    ld      a, #0xFF
    ret
00506$:
    ; if (d1 <= d0) off=(a-1)*512, cls=1 else off=a*512, cls=0
    ldw     x, *m_c             ; d1
    cpw     x, *m_c1            ; vs d0
    jrsgt   00508$
00509$:
    ldw     x, *m_la            ; d1 <= d0 (and the a == L entry)
    decw    x
    ld      a, xl
    clrw    x
    ld      xh, a
    sllw    x
    ld      a, #1
    jra     00507$
00508$:
    ld      a, *m_la+1
    clrw    x
    ld      xh, a
    sllw    x
    clr     a
00507$:                         ; X = off, A = cls
    push    a
    ldw     *m_h, x
    ldw     x, *_g_sg+4
    subw    x, *m_h
    ldw     *w_llo, x
    ldw     x, *_g_sg+6
    subw    x, *m_h
    ldw     *w_lhi, x
    pop     a
    ret

; (hix moved into the VGAP block above -- vector-gap bytes are free)

; cal_cloud: g_sg.u/.fam; hist fold histogram
ccloud:
    ld      a, *_g_sg+8
    cp      a, #5
    jreq    00520$
    cp      a, #6
    jreq    00520$
    ret
00520$:
    ldw     x, *_g_sg+4          ; u < 0 -> out
    jrmi    00529$
    sub     a, #5
    ld      *m_f, a
    ; d = (u & 511) - c_c0[f]
    ldw     x, *_g_sg+4
    ld      a, xh
    and     a, #1
    ld      xh, a               ; x = u & 511
    pushw   x
    ld      a, *m_f
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (c_c0, x)
    ldw     *m_h, x
    popw    x
    subw    x, *m_h             ; d
    ; if (-64 <= d < 64): b = (d+64)>>1; hist[f][b]++ (sat 255)
    addw    x, #64              ; d+64 in [0,128)
    jrmi    00529$
    cpw     x, #128
    jrnc    00529$
    srlw    x                   ; b
    pushw   x
    ld      a, *m_f
    call    hix
    addw    x, (1, sp)
    addw    sp, #2
    ld      a, (_ov, x)
    inc     a
    jreq    00529$              ; was 255: saturate
    ld      (_ov, x), a
00529$:
    ret

; cal_add: X = a; g_sg -> interval intersection + labx extremes
cadd:
    call    la_int
    cp      a, #0xFF
    jrne    00530$
    ret
00530$:
    ld      *m_i, a             ; ci
    sll     a
    clrw    x
    ld      xl, a
    pushw   x                   ; 2*ci
    ; if (lo > c_lo[ci]) c_lo = lo
    ldw     x, (c_lo, x)
    cpw     x, *w_llo
    jrsge   00531$
    ldw     x, (1, sp)
    ldw     y, *w_llo
    ldw     (c_lo, x), y
00531$:
    ldw     x, (1, sp)
    ldw     x, (c_hi, x)
    cpw     x, *w_lhi
    jrsle   00532$
    ldw     x, (1, sp)
    ldw     y, *w_lhi
    ldw     (c_hi, x), y
00532$:
    ; if (c_n[ci] < 255) c_n[ci]++
    ld      a, *m_i
    clrw    x
    ld      xl, a
    ld      a, (c_n, x)
    inc     a
    jreq    00533$
    ld      (c_n, x), a
00533$:
    addw    sp, #2
    ; fams 5/6 with lo >= 0: labx extremes of the fold coordinate
    ld      a, *_g_sg+8
    cp      a, #5
    jreq    00534$
    cp      a, #6
    jreq    00534$
    ret
00534$:
    ldw     x, *w_llo
    jrpl    00535$
    jp      00549$              ; lo < 0: no fold sample
00535$:
    sub     a, #5
    ld      *m_f, a
    ld      a, xh               ; d = (lo & 511) - c_c0[f]
    and     a, #1
    ld      xh, a
    pushw   x
    ld      a, *m_f
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (c_c0, x)
    ldw     *m_h, x
    popw    x
    subw    x, *m_h
    ldw     *m_c, x             ; d
    cpw     x, #-64
    jrslt   00549$
    cpw     x, #64
    jrsge   00549$
    ld      a, *m_f
    sll     a
    clrw    x
    ld      xl, a
    ldw     *m_hx, x            ; 2*f (index into labx arrays)
    tnz     *m_i                ; cls?
    jrne    00540$
    ; cls 0: if (d > labx0) { labx0b = labx0; labx0 = d; }
    ;        else if (d > labx0b) labx0b = d
    ldw     x, *m_hx
    ldw     x, (labx0, x)
    cpw     x, *m_c
    jrsge   00536$
    ldw     y, x                ; old labx0
    ldw     x, *m_hx
    ldw     (labx0b, x), y
    ldw     y, *m_c
    ldw     (labx0, x), y
    ret
00536$:
    ldw     x, *m_hx
    ldw     x, (labx0b, x)
    cpw     x, *m_c
    jrsge   00549$
    ldw     x, *m_hx
    ldw     y, *m_c
    ldw     (labx0b, x), y
    ret
00540$:
    ; cls 1: if (d < labx1) { labx1b = labx1; labx1 = d; }
    ;        else if (d < labx1b) labx1b = d
    ldw     x, *m_hx
    ldw     x, (labx1, x)
    cpw     x, *m_c
    jrsle   00542$
    ldw     y, x
    ldw     x, *m_hx
    ldw     (labx1b, x), y
    ldw     y, *m_c
    ldw     (labx1, x), y
    ret
00542$:
    ldw     x, *m_hx
    ldw     x, (labx1b, x)
    cpw     x, *m_c
    jrsle   00549$
    ldw     x, *m_hx
    ldw     y, *m_c
    ldw     (labx1b, x), y
00549$:
    ret

; wfit: A = ci; X = prior; *m_c = blo, *m_c1 = bhi -> X = width fit
wfit:
    ldw     *m_h, x             ; prior
    clrw    x
    ld      xl, a
    ld      a, (c_n, x)
    cp      a, #3
    jrc     00559$              ; c_n < LAB_MIN -> prior
    ld      a, xl
    sll     a
    clrw    x
    ld      xl, a
    ldw     y, x
    ldw     x, (c_lo, x)        ; lo
    ldw     *m_e, x
    ldw     x, y
    ldw     x, (c_hi, x)        ; hi
    ldw     *m_t, x
    ldw     x, *m_e
    cpw     x, *m_t
    jrsle   00551$
    addw    x, *m_t             ; lo > hi: h = (lo+hi)>>1
    sraw    x
    jra     00553$
00551$:
    ldw     x, *m_h             ; h = clamp(prior, lo, hi)
    cpw     x, *m_e
    jrsge   00552$
    ldw     x, *m_e
    jra     00553$
00552$:
    cpw     x, *m_t
    jrsle   00553$
    ldw     x, *m_t
00553$:
    cpw     x, *m_c             ; in [blo, bhi] else prior
    jrslt   00559$
    cpw     x, *m_c1
    jrsgt   00559$
    ret
00559$:
    ldw     x, *m_h
    ret

; theta56: A = f -> A = have_theta, *m_th = theta
th56:
    ld      *m_f, a
    sll     a
    clrw    x
    ld      xl, a
    ldw     *m_hx, x            ; 2*f
    ldw     x, (labx0, x)
    ldw     *m_x0, x
    ldw     x, *m_hx
    ldw     x, (labx1, x)
    ldw     *m_x1, x
    ; zlo = max(-32, x0+1); zhi = min(32, x1)
    ldw     x, *m_x0
    incw    x
    cpw     x, #-32
    jrsge   00560$
    ldw     x, #-32
00560$:
    ldw     *m_zlo, x
    ldw     x, *m_x1
    cpw     x, #32
    jrsle   00561$
    ldw     x, #32
00561$:
    ldw     *m_zhi, x
    clrw    x
    ldw     *m_th, x
    clr     *m_hv
    ; m_e := f*64 (hist row base) for the WHOLE function -- the density
    ; search AND the top/clear1 scan (hoisted: a stale row here cost one
    ; capture in validation)
    ld      a, *m_f
    call    hix
    ldw     *m_e, x
    ; density-gap search inside (zlo, zhi)
    ldw     x, *m_zlo
    cpw     x, *m_zhi
    jrslt   00562$
    jp      00570$              ; window empty
00562$:
    ldw     x, *m_zlo           ; blo = (zlo+64)>>1
    addw    x, #64
    srlw    x
    ld      a, xl
    ld      *m_bb, a
    ldw     x, *m_zhi           ; bhi = (zhi-1+64)>>1
    decw    x
    addw    x, #64
    srlw    x
    ld      a, xl
    ld      *m_j, a             ; bhi
    ldw     x, *m_zlo
    ldw     *m_prev, x
    clrw    x
    ldw     *m_blo2, x
    ldw     *m_bhi2, x
    ldw     x, #-1
    ldw     *m_bg, x
    clr     *m_no
00563$:
    ld      a, *m_bb
    cp      a, *m_j
    jrugt   00566$
    clrw    x                   ; hist[f][b]?
    ld      xl, a
    addw    x, *m_e
    ld      a, (_ov, x)
    tnz     a
    jreq    00565$
    ; x = (b<<1) - 64 + 1 ; gp = x - prev
    ld      a, *m_bb
    sll     a                   ; b <= 48 -> fits
    clrw    x
    ld      xl, a
    subw    x, #63
    ldw     *m_c, x             ; x coord
    subw    x, *m_prev
    cpw     x, *m_bg
    jrsle   00564$
    ldw     *m_bg, x
    ldw     x, *m_prev
    ldw     *m_blo2, x
    ldw     x, *m_c
    ldw     *m_bhi2, x
00564$:
    ldw     x, *m_c
    ldw     *m_prev, x
    inc     *m_no
00565$:
    inc     *m_bb
    jra     00563$
00566$:
    ldw     x, *m_zhi           ; trailing gap to zhi
    subw    x, *m_prev
    cpw     x, *m_bg
    jrsle   00567$
    ldw     *m_bg, x
    ldw     x, *m_prev
    ldw     *m_blo2, x
    ldw     x, *m_zhi
    ldw     *m_bhi2, x
00567$:
    tnz     *m_no
    jrne    00568$
    ; nocc == 0: theta = (zlo+zhi)>>1 iff has0 && has1
    call    has01
    cp      a, #3
    jrne    00570$
    ldw     x, *m_zlo
    addw    x, *m_zhi
    sraw    x
    ldw     *m_th, x
    mov     *m_hv, #1
    jra     00570$
00568$:
    ; ok = bg >= 5; if (ok && nocc+1 >= 4) density test
    ldw     x, *m_bg
    cpw     x, #5
    jrslt   00570$
    ld      a, *m_no
    inc     a
    cp      a, #4
    jrc     00569$
    ; 2*bg*(nocc+1) < 5*(zhi-zlo) -> not ok   (s16-safe, proven)
    ld      a, *m_bg+1          ; bg <= 64
    sll     a                   ; 2*bg <= 128
    clrw    x
    ld      xl, a
    ld      a, *m_no
    inc     a                   ; nocc+1 <= 34
    mul     x, a                ; 2*bg*(nocc+1) <= 4352
    ldw     *m_c, x
    ldw     x, *m_zhi
    subw    x, *m_zlo           ; (zhi-zlo) in (0,64]
    ldw     y, x
    sllw    x
    sllw    x                   ; *4
    pushw   y
    addw    x, (1, sp)          ; *5
    addw    sp, #2
    cpw     x, *m_c
    jrsle   00569$              ; 5*(zhi-zlo) <= lhs -> ok stays
    jra     00570$              ; lhs < rhs -> not ok
00569$:
    ldw     x, *m_blo2          ; theta = (best_lo + best_hi) >> 1
    addw    x, *m_bhi2
    sraw    x
    ldw     *m_th, x
    mov     *m_hv, #1
00570$:
    ; label-extreme window [wlo, whi]
    call    has01
    tnz     a
    jrne    00571$
    jp      00580$              ; neither label seen
00571$:
    push    a
    ldw     x, #-32
    ldw     *m_wlo, x
    ldw     x, #32
    ldw     *m_whi, x
    pop     a
    push    a
    and     a, #1               ; has0
    jreq    00573$
    ldw     x, *m_x0
    subw    x, #8
    ldw     *m_wlo, x
    ldw     x, *m_hx            ; labx0b > -0x4000?
    ldw     x, (labx0b, x)
    cpw     x, #-0x4000
    jrsle   00573$
    subw    x, #2
    cpw     x, *m_wlo
    jrsle   00573$
    ldw     *m_wlo, x
00573$:
    pop     a
    and     a, #2               ; has1
    jreq    00575$
    ldw     x, *m_x1
    addw    x, #8
    ldw     *m_whi, x
    ldw     x, *m_hx
    ldw     x, (labx1b, x)
    cpw     x, #0x3FFF
    jrsge   00575$
    addw    x, #2
    cpw     x, *m_whi
    jrsge   00575$
    ldw     *m_whi, x
00575$:
    ldw     x, *m_wlo
    cpw     x, *m_whi
    jrsle   00576$
    addw    x, *m_whi           ; wlo > whi: theta = (wlo+whi)>>1
    sraw    x
    ldw     *m_th, x
    mov     *m_hv, #1
    jra     00580$
00576$:
    ; th = clamp(have ? theta : 0, wlo, whi); have = 1
    tnz     *m_hv
    jrne    00577$
    clrw    x
    ldw     *m_th, x
00577$:
    ldw     x, *m_th
    cpw     x, *m_wlo
    jrsge   00578$
    ldw     x, *m_wlo
00578$:
    cpw     x, *m_whi
    jrsle   00579$
    ldw     x, *m_whi
00579$:
    ldw     *m_th, x
    mov     *m_hv, #1
00580$:
    ; top / clear1 scan over all 64 bins
    clr     *m_cl1
    clr     *m_htp
    clrw    x
    ldw     *m_top, x
    clr     *m_bb
00581$:
    ld      a, *m_bb
    cp      a, #64
    jrnc    00585$
    clrw    x
    ld      xl, a
    addw    x, *m_e
    ld      a, (_ov, x)
    tnz     a
    jreq    00584$
    ld      a, *m_bb              ; d = (b<<1) - 63
    sll     a
    clrw    x
    ld      xl, a
    subw    x, #63
    cpw     x, #18
    jrsle   00582$
    mov     *m_cl1, #1
    jra     00584$
00582$:
    cpw     x, #-24
    jrsle   00584$
    tnz     *m_htp
    jreq    00583$
    cpw     x, *m_top
    jrsle   00584$
00583$:
    ldw     *m_top, x
    mov     *m_htp, #1
00584$:
    inc     *m_bb
    jra     00581$
00585$:
    tnz     *m_cl1
    jrne    00589$
    tnz     *m_htp
    jreq    00589$
    ; floor = top + 3
    ldw     x, *m_top
    addw    x, #3
    ldw     *m_c, x             ; floor
    tnz     *m_hv
    jreq    00586$
    cpw     x, *m_th
    jrsle   00587$
00586$:
    ldw     *m_th, x            ; theta = floor
00587$:
    mov     *m_hv, #1
    ; if (has1 && x1+2 > floor && theta > x1+2) theta = x1+2
    call    has01
    and     a, #2
    jreq    00589$
    ldw     x, *m_x1
    addw    x, #2
    cpw     x, *m_c
    jrsle   00589$
    ldw     y, x
    ldw     x, *m_th
    pushw   y
    cpw     x, (1, sp)
    popw    y
    jrsle   00589$
    ldw     *m_th, y
00589$:
    ld      a, *m_hv
    ret

; has01: A = has0 | (has1 << 1) for family *m_f (x0/x1 already loaded)
has01:
    clr     a
    ldw     x, *m_x0
    cpw     x, #-0x4000
    jrsle   00590$
    or      a, #1
00590$:
    ldw     x, *m_x1
    cpw     x, #0x3FFF
    jrsge   00591$
    or      a, #2
00591$:
    ret

; ---------------------------------------------------------------- calibrate
_calibrate:
    ; init: c_lo = -0x4000, c_hi = 0x3FFF, c_n = 0, h0c/h1c = priors
    ldw     x, #-0x4000
    ldw     *c_lo, x
    ldw     *c_lo+2, x
    ldw     x, #0x3FFF
    ldw     *c_hi, x
    ldw     *c_hi+2, x
    clrw    x
    ldw     *c_n, x
    ldw     *zd56, x
    ldw     x, #154
    ldw     *zh0c, x
    ldw     x, #308
    ldw     *zh1c, x
    call    _set_gap56
    ; per family: c_c0 = (154+308-gap)>>1; hist rows zeroed; labx init
    clr     *m_f
00600$:
    ld      a, *m_f
    sll     a
    clrw    x
    ld      xl, a
    ldw     *m_hx, x
    ldw     x, (zgap, x)
    negw    x
    addw    x, #462             ; 154+308-gap
    sraw    x
    ldw     y, x
    ldw     x, *m_hx
    ldw     (c_c0, x), y
    ldw     x, #-0x4000
    ldw     y, x
    ldw     x, *m_hx
    ldw     (labx0, x), y
    ldw     (labx0b, x), y
    ldw     x, #0x3FFF
    ldw     y, x
    ldw     x, *m_hx
    ldw     (labx1, x), y
    ldw     (labx1b, x), y
    ld      a, *m_f
    call    hix
    ldw     *m_e, x
    clr     *m_bb
00601$:
    ld      a, *m_bb
    cp      a, #64
    jrnc    00602$
    clrw    x
    ld      xl, a
    addw    x, *m_e
    clr     a
    ld      (_ov, x), a
    inc     *m_bb
    jra     00601$
00602$:
    inc     *m_f
    ld      a, *m_f
    cp      a, #2
    jrc     00600$
    ; segment loop
    call    _ss_init
00603$:
    ldw     x, #_g_sg
    call    _ss_next
    tnz     a
    jrne    00604$
    jp      00610$
00604$:
    call    ccloud
    ldw     x, *_g_sg+2          ; if (k1 > NB) continue
    cpw     x, _g_NB
    jrule   00605$
    jra     00603$
00605$:
    ; known_all over [k0, min(k1,NB))  (k1 <= NB here)
    ldw     x, *_g_sg+2
    ldw     *m_e, x
    ldw     x, *_g_sg
    ldw     *m_t, x
00606$:
    ldw     x, *m_t
    cpw     x, *m_e
    jrnc    00608$
    call    _known_bit
    cp      a, #0xFF
    jrne    00607$
    jra     00603$              ; unknown bit -> next segment
00607$:
    ldw     x, *m_t
    incw    x
    ldw     *m_t, x
    jra     00606$
00608$:
    call    _a_bounds_sg
    ldw     x, *_g_sg+2          ; m_L = k1-k0 (la_int's a==L test; P4's
    subw    x, _g_sg            ; dq_decide sets it for itself, but HERE
    ldw     *m_L, x             ; it was stale -- fuzz_v22 E05 root cause)
    ldw     x, *_dq_amin
    cpw     x, *_dq_amax
    jrne    00603$
    call    cadd                ; X = amin
    jp      00603$
00610$:
    ; width fit + separation guard
    ldw     x, #112
    ldw     *m_c, x
    ldw     x, #192
    ldw     *m_c1, x
    clr     a
    ldw     x, #154
    call    wfit
    ldw     *m_h0, x            ; h0 (reuse decide temp)
    ldw     x, #252
    ldw     *m_c, x
    ldw     x, #376
    ldw     *m_c1, x
    ld      a, #1
    ldw     x, #308
    call    wfit                ; h1
    ldw     *m_h1, x
    subw    x, *m_h0
    cpw     x, #112
    jrslt   00611$
    cpw     x, #196
    jrsgt   00611$
    ldw     x, *m_h0
    ldw     *zh0c, x
    ldw     x, *m_h1
    ldw     *zh1c, x
    jra     00612$
00611$:
    ldw     x, #154
    ldw     *zh0c, x
    ldw     x, #308
    ldw     *zh1c, x
00612$:
    ; per family: theta -> d56 clamp
    clr     *m_f
00613$:
    ld      a, *m_f
    call    th56
    tnz     a
    jrne    00614$
    ld      a, *m_f             ; no theta: d56 = 0
    clrw    x
    ld      xl, a
    clr     a
    ld      (zd56, x), a
    jra     00616$
00614$:
    ; delta = th + c_c0[f] - ((h0c + h1c - gap56[f]) >> 1), clamp +-24
    ld      a, *m_f
    sll     a
    clrw    x
    ld      xl, a
    pushw   x
    ldw     x, (zgap, x)
    ldw     *m_c, x
    ldw     x, *zh0c
    addw    x, *zh1c
    subw    x, *m_c
    sraw    x
    ldw     *m_c, x             ; cfit
    popw    x
    ldw     x, (c_c0, x)
    addw    x, *m_th
    subw    x, *m_c             ; delta
    cpw     x, #-24
    jrsge   00615$
    ldw     x, #-24
00615$:
    cpw     x, #24
    jrsle   00617$
    ldw     x, #24
00617$:
    ld      a, xl
    push    a
    ld      a, *m_f
    clrw    x
    ld      xl, a
    pop     a
    ld      (zd56, x), a
00616$:
    inc     *m_f
    ld      a, *m_f
    cp      a, #2
    jrc     00613$
    ret

; ======================================================================
; Size-focused sample scanner: a rolled, bit-exact port of decode.c's
; C scanner (the proven v1 ps_next semantics), ~350 B against scan.s's
; speed-unrolled 900 B.  Slower per sample (~30 cy vs ~8); at ~11.5k
; sample visits per decode that costs ~+10-15 ms on a production decode
; -- traded for flash, which is the binding constraint.
; ======================================================================

    .area CODE

_scan_init:
    clrw    x
    ldw     *p_i, x
    ldw     *p_tb, x
    ldw     *p_ws, x
    ldw     *p_tp, x
    ldw     *p_lr, x
    clr     *p_s
    clr     *p_hp
    clr     *p_ip
    clr     *p_se
    clr     *p_dn
    ret

; A = cap[i + A(0/1)] helper: X = p_i (+carry offset in A) -> A = byte
capat:                          ; X = index -> A = cap[X]
    addw    x, *_scan_cap
    ld      a, (x)
    ret

_scan_next:
00700$:                         ; while (!done)
    tnz     *p_dn
    jreq    00701$
    jp      00790$
00701$:
    ldw     x, *p_i             ; if (i >= len) break
    cpw     x, *_scan_len
    jrc     00702$
    jp      00780$
00702$:
    ld      a, *p_s
    cp      a, #6
    jrne    00710$
    ldw     x, *p_i             ; s == 6: whole-octet fast paths need i+1 < len
    incw    x
    cpw     x, *_scan_len
    jrnc    00710$
    call    capat               ; bt = cap[i+1]
    tnz     a
    jrne    00703$
    tnz     *p_ip               ; bt == 0x00 && !in_pulse
    jrne    00710$
    ldw     x, *p_tb            ; t_prev = tb + 61 + ws; have_prev = 1
    addw    x, #61
    addw    x, *p_ws
    ldw     *p_tp, x
    mov     *p_hp, #1
    ldw     x, *p_lr            ; low_run += 8
    addw    x, #8
    ldw     *p_lr, x
    call    stepi               ; i++; tb += 40 (s stays 6)
    tnz     *p_se               ; seen && low_run >= 200 -> done
    jreq    00700$
    ldw     x, *p_lr
    cpw     x, #200
    jrc     00700$
    mov     *p_dn, #1
    jp      00790$
00703$:
    cp      a, #0xFF            ; bt == 0xFF && in_pulse
    jrne    00710$
    tnz     *p_ip
    jreq    00710$
    ldw     x, *p_tb            ; fa = tb + 63 + ws; ws += 2
    addw    x, #63
    addw    x, *p_ws
    ldw     *_scan_fa, x
    ldw     *p_tp, x            ; t_prev = fa; have_prev = 1
    mov     *p_hp, #1
    ldw     x, *p_ws
    incw    x
    incw    x
    ldw     *p_ws, x
    mov     *_scan_sfa, #5
    clrw    x
    ldw     *p_lr, x
    mov     *p_se, #1
    call    stepi
    jp      00700$
00710$:
    ; ordinary sample: v = bit of cap[i] (s<6) or cap[i+1] (s>=6)
    ld      a, *p_s
    cp      a, #6
    jrnc    00711$
    ldw     x, *p_i             ; v = (cap[i] >> (5-s)) & 1
    call    capat
    ld      *m_s, a
    ld      a, *p_s
    add     a, #3               ; bit (5-s) -> 8-(5-s) = s+3 shifts
    ld      *m_vi, a
    jra     00713$
00711$:
    ldw     x, *p_i             ; s >= 6: boundary bits live in cap[i+1]
    incw    x
    cpw     x, *_scan_len
    jrc     00712$
    call    stepi               ; last loop: BS lost; s = 0; continue
    clr     *p_s
    jp      00700$
00712$:
    call    capat               ; v = (cap[i+1] >> (7-(s-6))) & 1
    ld      *m_s, a
    ld      a, *p_s
    sub     a, #5               ; bit (13-s) -> 8-(13-s) = s-5 shifts
    ld      *m_vi, a
00713$:
    ld      a, *m_s
00714$:
    sll     a
    dec     *m_vi
    jrne    00714$
    clr     a
    rlc     a
    ld      *m_vi, a            ; v
    ; t = tb + O[s] + ws
    clrw    x
    ld      a, *p_s
    ld      xl, a
    ld      a, (sot, x)
    clrw    x
    ld      xl, a
    addw    x, *p_tb
    addw    x, *p_ws
    ldw     *p_t, x
    ; slot/loop advance
    ld      a, *p_s
    cp      a, #7
    jrne    00715$
    call    stepi
    clr     *p_s
    jra     00716$
00715$:
    inc     *p_s
00716$:
    tnz     *m_vi
    jreq    00730$
    ; ---- HIGH sample ----
    ld      a, *p_s             ; ws += W[s]  (s was advanced: use s-1 mod 8)
    dec     a
    and     a, #7
    clrw    x
    ld      xl, a
    ld      a, (swt, x)
    push    a                   ; sign-extend s8 into X
    clrw    x
    ld      xl, a
    pop     a
    tnz     a
    jrpl    00717$
    addw    x, #0xFF00
00717$:
    addw    x, *p_ws
    ldw     *p_ws, x
    tnz     *p_ip
    jrne    00718$
    mov     *p_ip, #1           ; pulse starts
    tnz     *p_hp
    jreq    00719$
    ldw     x, *p_tp            ; ra = t_prev
    jra     00720$
00719$:
    ldw     x, *p_t             ; ra = max(t-4, 0)
    subw    x, #4
    jrnc    00720$
    clrw    x
00720$:
    ldw     *_scan_ra, x
    ldw     x, *p_t
    ldw     *_scan_rb, x
00718$:
    ldw     x, *p_t             ; fa = t; sfa = s(orig); low_run = 0; seen = 1
    ldw     *_scan_fa, x
    ld      a, *p_s
    dec     a
    and     a, #7
    ld      *_scan_sfa, a
    clrw    x
    ldw     *p_lr, x
    mov     *p_se, #1
    jra     00740$
00730$:
    ; ---- LOW sample ----
    tnz     *p_ip
    jreq    00731$
    clr     *p_ip               ; pulse ends: emit
    ldw     x, *p_t
    ldw     *_scan_fb, x
    ldw     *p_tp, x            ; t_prev = t; have_prev = 1
    mov     *p_hp, #1
    ldw     x, #1
    ldw     *p_lr, x
    ld      a, #1
    ret
00731$:
    ldw     x, *p_lr            ; low_run++
    incw    x
    ldw     *p_lr, x
    tnz     *p_se
    jreq    00740$
    cpw     x, #200
    jrc     00740$
    mov     *p_dn, #1
    jra     00790$
00740$:
    ldw     x, *p_t             ; loop bottom: t_prev = t; have_prev = 1
    ldw     *p_tp, x
    mov     *p_hp, #1
    jp      00700$

00780$:                         ; data exhausted
00790$:                         ; done / latch: flush a pulse in flight
    tnz     *p_ip
    jreq    00791$
    clr     *p_ip
    ldw     x, *_scan_fa        ; fb = fa + 4
    addw    x, #4
    ldw     *_scan_fb, x
    ld      a, #1
    ret
00791$:
    mov     *p_dn, #1
    clr     a
    ret

; stepi: i++; tb += 40
stepi:
    ldw     x, *p_i
    incw    x
    ldw     *p_i, x
    ldw     x, *p_tb
    addw    x, #40
    ldw     *p_tb, x
    ret

; ======================================================================
; P5/P6: v2.3 PIPELINE TAIL -- CRC16 confidence chase (SS7) + the
; ws_decode_ex top level.  Hand assembly again, as in v2.2.
;
; The v2.3 tail first shipped as compiled C (decode.c, which REMAINS the
; host-parity reference under !USE_ASM_DEC) and cost 1641 B of CODE plus
; 112 B of CONST -- 531 B of the 748 B by which the production link
; overflowed (PROD_CLOSURE SS13.1).  Everything below is a BIT-EXACT
; port of those same C functions: crc16 / rank3 / ref_build / ch_match /
; try_trial / chase_singles / chase_pairs / chase / ws_decode_ex.
; Proven per step by dev_prod/ucsim_v23.py (emitted bytes + path + cause
; + trials + comps + n_refs + n_weak per capture vs embedded_v2.py) at
; BOTH geometries, ND = 16 and ND = 48.  No gate, relaxation, counter or
; enumeration order was dropped to make room.
;
; TWO implementation substitutions, both value-identical (the same
; discipline as v2.2's syn8-by-xtime instead of its XPOW table):
;
;  1. NO SYNDROME TABLE.  decode.c computes a trial residual as
;     r_base ^ syn16(k) off a 48-entry x^(16+8i) table (96 B of CONST).
;     Here a trial flips its bits in d_pp and recomputes
;     crc16(d_pp[0..ND-1]).  CRC-16 is affine over GF(2), so the two are
;     the SAME 16-bit value -- embedded_v2._selftest() asserts exactly
;     that linearity -- and a CHECK-bit flip cannot move the residual
;     because the check block sits outside the CRC's byte range, which is
;     why decode.c's `touched` bookkeeping carries over unchanged.  Costs
;     one 8*ND-step CRC per trial (<= 67 trials) and drops 96 B of table
;     plus syn16() itself.
;  2. The marker template lives here as HTR (6 B, each byte BIT-REVERSED
;     so it XORs straight against d_bits' packing) and the popcount is a
;     shift loop instead of decode.c's 16-B nibble table.
;
; Chase temps ALIAS the refine/calibrate scratch (r_* / m_n / m_d / m_r):
; the chase runs strictly after decide_pass, refine and calibrate have
; both returned, and dec_eps_centi's udiv32 runs only after
; ws_decode_ex returns -- zero extra zero page for the whole tail, the
; same rule the v2.2 tail used.  NOTE the ordering constraint that comes
; with it: z_out is loaded AFTER decide_pass, because seed/refine own
; m_n while they run.
; ======================================================================

    .globl _ws_decode_ex
    .globl _g_TIEE
    .globl _g_PPB
    .globl _g_PPE
    .globl _g_TRB

z_out   =   m_n         ; (2) caller's out[]
z_rb    =   m_n+2       ; (2) ch_rbase = crc16(D) of the unflipped payload
z_rr    =   m_d         ; (2) trial residual
z_cj    =   m_r         ; (2) rank3 conf[j]
z_nhi   =   m_r+2       ; (1) ch_nhi
z_nlo   =   m_r+3       ; (1) ch_nlo
z_nref  =   r_lo        ; (1) ch_nref
z_comps =   r_lo+1      ; (1) ch_comps -- THE T_MAX BOUND
z_cap   =   r_lo+2      ; (1) ch_cap (REF_MAX or 1)
z_cn    =   r_lo+3      ; (1) ch_n
z_ti    =   r_lo+4      ; (1) trial member i
z_tj    =   r_lo+5      ; (1) trial member j (0xFF = single)
z_ww    =   r_lo+6      ; (1) phase want / sum
z_tch   =   r_lo+7      ; (1) touched: a CHECK bit moved the reference
z_sk3   =   r_lo+8      ; (1) parity gate skip3
z_sk5   =   r_lo+9      ; (1) parity gate skip5
z_q     =   r_hi        ; (1) generic index (refs, ranks)
z_v0    =   r_hi+1      ; (1) rank3 votes -- MUST stay contiguous
z_v1    =   r_hi+2      ; (1)
z_v2    =   r_hi+3      ; (1)
z_bs    =   r_hi+4      ; (1) rank3 base: 0 = HI, 1 = LO
z_ob    =   r_hi+5      ; (1) 3*base, ch_val write offset
z_ri    =   r_hi+6      ; (1)
z_rj    =   r_hi+7      ; (1)
z_a     =   r_hi+8      ; (1) ref_build HI rank
z_sm    =   r_hi+9      ; (1) ref_build diagonal (rank sum)
z_bb    =   r_melo      ; (1) ref_build LO rank

; SS10.2 OVERLAY: ch_ref (9 u16 = 18 B) and ch_val (6 B) share d_costs,
; which is decision-pass scratch and dead the moment decide_pass returns
; (the chase never calls decide()).  Exactly the cast decode.c's tail
; made; 2*REF_MAX + 6 = 24 <= 32.
CH_REF  =   _d_costs
CH_VAL  =   _d_costs+18

    .area CODE

; --------------------------------------------------------------- crcpp
; X = crc16(d_pp[0 .. ND-1]) -- CRC-16/CCITT-FALSE, init 0xFFFF, poly
; 0x1021, MSB first, over the DATA bytes only.  d_pp is ov[g_PPB ..
; g_PPE-1]; the check block starts at g_PPE and is NOT covered.
crcpp:
    ldw     x, #0xFFFF
    ldw     y, _g_PPB
01102$:
    ld      a, (_ov, y)
    ld      *m_s, a
    ld      a, xh
    xor     a, *m_s
    ld      xh, a
    push    #8
01103$:                         ; X = (X<<1) ^ 0x1021 on carry out
    sllw    x
    jrnc    01104$
    ld      a, xh
    xor     a, #0x10
    ld      xh, a
    ld      a, xl
    xor     a, #0x21
    ld      xl, a
01104$:
    dec     (1, sp)
    jrne    01103$
    pop     a
    incw    y
    cpw     y, _g_PPE
    jrult   01102$
    ret

; --------------------------------------------------------------- chisd
; A = candidate slot -> A = 1 if it is a DATA bit (v_cand_t[A] < ND8),
; else 0.  Recomputed on demand, exactly like decode.c ch_isd().
; candk: A = candidate slot -> X = v_cand_t[A], and C = 1 iff it is a
; DATA bit (k < ND8).  RET leaves the flags alone, so both callers read C.
candk:
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (_v_cand_t, x)
    cpw     x, _g_ND8
    ret

chisd:
    call    candk
    clr     a                   ; CLR touches N/Z only -- C survives
    rlc     a
    ret

; ---------------------------------------------------------------- fl1
; A = candidate slot (0xFF = none): toggle its payload' bit in d_pp and,
; if it is a CHECK bit, mark z_tch -- the flip MOVED the reference set.
fl1:
    cp      a, #0xFF
    jreq    01111$
    call    candk
    jrc     01110$
    ld      a, #1
    ld      *z_tch, a
01110$:
    ; toggle payload' bit X inside d_pp.  Wire bytes are MSB first, so
    ; the mask is 1 << (7 - (k & 7)) = 0x80 >> (k & 7).
    ld      a, xl
    and     a, #7
    ld      *m_s, a
    srlw    x
    srlw    x
    srlw    x
    addw    x, _g_PPB
    ld      a, #0x80
01107$:
    tnz     *m_s
    jreq    01108$
    srl     a
    dec     *m_s
    jra     01107$
01108$:
    xor     a, (_ov, x)
    ld      (_ov, x), a
01111$:
    ret

; -------------------------------------------------------------- flipij
; Toggle both members of the current flip set.  A flip is its own
; inverse, so trial() calls this twice: once to apply, once to undo.
flipij:
    clr     *z_tch
    ld      a, *z_ti
    call    fl1
    ld      a, *z_tj
    jp      fl1

; -------------------------------------------------------------- chmat
; X = residual -> A = 1 accept / 0 no match / 2 T_MAX budget exhausted.
; Every comparison is one 2^-16 exposure and one unit of budget: THIS
; COUNTER IS THE BOUND (T_MAX_CFG; the ledger value 131 = fa_budget(0.2 %,
; 1 ref)).  z_comps is ONE BYTE, which is why T_MAX_CFG <= 255.
chmat:                          ; the residual under test is in *z_rr
    clr     *z_q
01115$:
    ld      a, *z_q
    cp      a, *z_nref
    jrnc    01117$
    ld      a, *z_comps
    cp      a, #T_MAX_CFG
    jrnc    01118$
    inc     *z_comps
    ld      a, *z_q
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (CH_REF, x)
    cpw     x, *z_rr
    jreq    01116$
    inc     *z_q
    jra     01115$
01116$:
    ld      a, #1
    ret
01117$:
    clr     a
    ret
01118$:
    ld      a, #2
    ret

; --------------------------------------------------------------- confx
; A = copy index 0..2 -> X = v_chkconf[z_bs + 2*A] (u16, big endian, as
; decide_pass writes it).
confx:
    sll     a
    sll     a
    add     a, *z_bs
    add     a, *z_bs
    clrw    x
    ld      xl, a
    ldw     x, (_v_chkconf, x)
    ret

; -------------------------------------------------------------- putval
; A = value, *z_q = rank r -> ch_val[3*z_bs + r] = A
putval:
    ld      *m_s, a
    ld      a, *z_bs
    ld      *m_i, a
    sll     a
    add     a, *m_i
    add     a, *z_q
    clrw    x
    ld      xl, a
    ld      a, *m_s
    ld      (CH_VAL, x), a
    ret

; --------------------------------------------------------------- rank3
; A = base (0 = HI, 1 = LO).  Candidate values for ONE check-byte
; position, best-confidence FIRST, into ch_val[3*base ...]; the count
; goes to z_nhi / z_nlo.  Three votes admit NO tie, so the position
; either has a unique >=2-vote majority (one candidate) or all three
; differ (three candidates, confidence-ranked, ties keeping wire order).
; Each copy's RANK is the number of copies that beat it -- that double
; loop IS the ordering: no sort, no key array.  decode.c rank3() /
; embedded_v2._ranked3().
rank3:
    ld      *z_bs, a
    clrw    x
    ld      xl, a               ; A still holds base
    addw    x, _g_PPE           ; &C[base] inside ov
    ld      a, (_ov, x)         ; C[base]
    ld      *z_v0, a
    ld      a, (_ov+2, x)       ; C[base+2]
    ld      *z_v1, a
    ld      a, (_ov+4, x)       ; C[base+4]
    ld      *z_v2, a
    ld      a, *z_v0
    cp      a, *z_v1
    jreq    01120$
    cp      a, *z_v2
    jreq    01120$
    ld      a, *z_v1
    cp      a, *z_v2
    jrne    01122$
01120$:                         ; A = the unique >=2-vote value
    clr     *z_q
    call    putval
    ld      a, #1
    jra     01129$
01122$:                         ; all three differ: rank by (-conf, index)
    clr     *z_rj
01123$:
    ld      a, *z_rj
    cp      a, #3
    jrnc    01128$
    call    confx
    ldw     *z_cj, x
    clr     *z_q                ; r = how many copies beat j
    clr     *z_ri
01124$:
    ld      a, *z_ri
    cp      a, #3
    jrnc    01127$
    call    confx
    cpw     x, *z_cj
    jrugt   01125$              ; conf[i] > conf[j]
    jrne    01126$
    ld      a, *z_ri
    cp      a, *z_rj
    jrnc    01126$              ; equal conf: the earlier copy wins
01125$:
    inc     *z_q
01126$:
    inc     *z_ri
    jra     01124$
01127$:
    clrw    x
    ld      a, *z_rj
    ld      xl, a
    ld      a, (z_v0, x)
    call    putval
    inc     *z_rj
    jra     01123$
01128$:
    ld      a, #3
01129$:
    tnz     *z_bs
    jrne    01130$
    ld      *z_nhi, a
    ret
01130$:
    ld      *z_nlo, a
    ret

; -------------------------------------------------------------- refbld
; Materialise the reference set: rank3 for both byte positions, then
; their CROSS PRODUCT in DIAGONAL order (rank-sum ascending, then
; HI-rank ascending), truncated to z_cap.  Both lists are already
; confidence-descending, so the diagonal tries better references first
; without sorting the 9 pairs.  decode.c ref_build() /
; embedded_v2._ref_candidates().
refbld:
    clr     a
    call    rank3
    ld      a, #1
    call    rank3
    clr     *z_q
    clr     *z_sm
    clrw    x                   ; XH stays 0 for the whole loop below:
                                ; nothing here writes it back
01135$:
    ld      a, *z_sm
    cp      a, #5
    jrnc    01140$
    clr     *z_a
01136$:
    ld      a, *z_a
    cp      a, *z_nhi
    jrnc    01139$              ; a >= nhi: next diagonal
    cp      a, *z_sm
    jrugt   01139$              ; a > sm: b would be negative -- break
    neg     a                   ; A still holds z_a
    add     a, *z_sm
    ld      *z_bb, a            ; b = sm - a
    cp      a, *z_nlo
    jrnc    01138$              ; b >= nlo: continue
    ld      a, *z_q
    cp      a, *z_cap
    jrnc    01140$              ; q >= cap: stop with nref = q
    ld      a, *z_a
    ld      xl, a
    ld      a, (CH_VAL, x)
    ld      yh, a
    ld      a, *z_bb
    ld      xl, a
    ld      a, (CH_VAL+3, x)
    ld      yl, a
    ld      a, *z_q
    sll     a
    ld      xl, a
    ldw     (CH_REF, x), y
    inc     *z_q
01138$:
    inc     *z_a
    jra     01136$
01139$:
    inc     *z_sm
    jra     01135$
01140$:
    ld      a, *z_q
    ld      *z_nref, a
    ret

; --------------------------------------------------------------- trial
; Evaluate the current flip set -> A = 1 accept (the flips stay applied:
; only the DATA bytes are emitted, so the check block's state stops
; mattering), 0 reject, 2 T_MAX budget exhausted.  decode.c try_trial().
trial:
    inc     *_dec_info+2         ; trials++
    call    flipij
    call    crcpp
    ldw     *z_rr, x
    tnz     *z_tch
    jreq    01145$
    call    refbld              ; the flips MOVED the reference set
01145$:
    call    chmat
    cp      a, #1
    jreq    01147$              ; accept: A is already 1
    push    a
    call    flipij              ; undo, then restore the base set
    tnz     *z_tch
    jreq    01146$
    call    refbld
01146$:
    pop     a
01147$:
    ret

; --------------------------------------------------------------- csing
; One single-flip phase: candidates whose is-data flag == z_ww, in list
; (= confidence) order.  A = 0 none / 1 accepted / 2 budget.
csing:
    clr     *z_ti
01150$:
    ld      a, *z_ti
    cp      a, *z_cn
    jrnc    01153$
    call    chisd               ; A still holds z_ti
    cp      a, *z_ww
    jrne    01151$
    ld      a, #0xFF
    ld      *z_tj, a
    call    trial
    tnz     a
    jrne    01152$
01151$:
    inc     *z_ti
    jra     01150$
01152$:
    ret
01153$:
    clr     a
    ret

; --------------------------------------------------------------- cpair
; One pair phase: i < j lexicographic, filtered by isd[i] + isd[j] ==
; z_ww -- exactly the SS7.4 phase-2/4/5 enumeration orders.
;
; SS7.10 W2 bound: at v2.3 A_PAIR = A_MAX (11) and MG_PAIR = MG_MAX (8),
; and cand_insert admits nothing above MG_MAX, so `j < A_PAIR &&
; v_cand_m[j] <= MG_PAIR` is provably TRUE for every j < ch_n <= A_MAX.
; decode.c compiles the two monotone tests out for exactly that reason;
; tightening either constant brings them back in both places.  The hard
; bound meanwhile is T_MAX comparisons, counted in chmat.
cpair:
    clr     *z_ti
01155$:
    ld      a, *z_ti
    cp      a, *z_cn
    jrnc    01159$
    inc     a
    ld      *z_tj, a
01156$:
    ld      a, *z_tj
    cp      a, *z_cn
    jrnc    01158$
    ld      a, *z_ti
    call    chisd
    ld      *m_s, a
    ld      a, *z_tj
    call    chisd
    add     a, *m_s
    cp      a, *z_ww
    jrne    01157$
    call    trial
    tnz     a
    jrne    01160$
01157$:
    inc     *z_tj
    jra     01156$
01158$:
    inc     *z_ti
    jra     01155$
01159$:
    clr     a
01160$:
    ret

; --------------------------------------------------------------- chasez
; C1..C5 + R5..R8 of SS7.9 -> A = DEC_* path, dec_info.cause on refusal.
; Works entirely on the decoded bit array and the <= A_MAX candidate
; list -- no capture scan.  decode.c chase().
chasez:
    ; C1: payload' byte p is the BIT REVERSAL of d_bits[HT_LEN + p]
    ; (d_bits packs frame bit t at byte t>>3, bit t&7 LSB first, the wire
    ; byte is MSB first, and PP_LO = 8*HT_LEN is a whole byte count).
    ldw     x, #3
    ldw     y, _g_PPB
01170$:
    ld      a, (_ov, x)
    push    #8
01171$:
    srl     a
    rlc     *m_s
    dec     (1, sp)
    jrne    01171$
    pop     a
    ld      a, *m_s
    ld      (_ov, y), a
    incw    y
    incw    x
    cpw     x, _g_TRB
    jrult   01170$
    ldw     x, *_v_nweak
    ldw     *_dec_info+5, x
    ldw     x, *_v_ntied
    ldw     *_dec_info+7, x
    call    crcpp
    ldw     *z_rb, x
    clr     *z_comps
    ; RELAXATION B feed-forward: a marker-suspect frame keeps its
    ; per-byte-majority reference but is denied the split enumeration, so
    ; it cannot also help itself to 9x the per-comparison exposure.
    ; (violations <= MK_TOL here -- R2 already refused anything worse.)
    ld      a, *_dec_info+13
    cp      a, #5               ; violations > MK_SOFT (4)?
    ld      a, #1               ; LD A,#imm leaves C alone
    jrnc    01173$
    ld      a, #9               ; REF_MAX
01173$:
    ld      *z_cap, a
    call    refbld
    ld      a, *z_nref
    ld      *_dec_info+21, a
    ; ref_split = (nhi > 1) + (nlo > 1).  rank3 returns 1 or 3 and
    ; nothing else, so nhi+nlo is 2, 4 or 6 and the count is
    ; (nhi+nlo)/2 - 1 -- same three values, four instructions.
    ld      a, *z_nhi
    add     a, *z_nlo
    srl     a
    dec     a
    ld      *_dec_info+22, a
    ; R5: RETIRED in v2.3 (TIE_EMIT = 8*NPP+1 is structurally
    ; unreachable -- n_tied counts a subset of the 8*NPP payload' bits).
    ; Assembled, not deleted: restoring the gate stays one constant.
    ldw     x, *_v_ntied
    cpw     x, _g_TIEE
    jrule   01174$
    ld      a, #5
    jp      01192$
01174$:
    ; C2: direct accept.  v2.3 admits a SPLIT check block here too (the
    ; emit-always directive); with a majority at both positions this is
    ; bit-identical to v2.2's single-reference test.
    ldw     x, *z_rb
    ldw     *z_rr, x
    call    chmat
    cp      a, #1
    jrne    01175$
    ld      a, #1               ; DEC_DIRECT
    jp      01182$
01175$:
    tnz     *_v_ncand           ; C3: R6 -- nothing at all to flip.
    jrne    01176$              ; EQUIVALENT to n_weak == 0 && n_dw == 0:
    ld      a, #6               ; candi bails out only when the insertion
    jp      01191$              ; index reaches A_MAX, impossible while
01176$:                         ; the list is empty, so the first admitted
    ldw     x, *_v_nweak        ; bit of either class always lands.
    cpw     x, #A_MAX_CFG       ; A_MAX -- R7 is the WEAK pool's
    jrule   01177$              ; completeness rule and is UNCHANGED (a DW
    ld      a, #7               ; entry can never sort ahead of a weak
    jp      01191$              ; one, margin > MG_MAX vs <= MG_MAX)
01177$:
    mov     *z_cn, *_v_ncand
    ; Parity gate (EXACT at 16 bits: 0x11021 = (x+1)*0xF01F, so every
    ; single-bit syndrome has odd parity and a weight-w data-only flip
    ; has syndrome parity w mod 2).  Skip a data-only phase whose weight
    ; parity can match NO admitted reference.
    ld      a, #1
    ld      *z_sk3, a
    ld      *z_sk5, a
    clr     *z_q
01178$:
    ld      a, *z_q
    cp      a, *z_nref
    jrnc    01181$
    sll     a
    clrw    x
    ld      xl, a
    ldw     x, (CH_REF, x)
    ld      a, xh
    xor     a, *z_rb
    ld      xh, a
    ld      a, xl
    xor     a, *z_rb+1
    ld      xl, a
    ; parity16(X): x ^= x>>8; x ^= x>>4; x ^= x>>2; x ^= x>>1; & 1.
    ; The nibble fold uses SWAP, whose HIGH half differs from a plain
    ; >>4 -- bit 0, the only bit ever read, is identical.
    ld      a, xl
    ld      *m_s, a
    ld      a, xh
    xor     a, *m_s
    ld      *m_s, a
    swap    a
    xor     a, *m_s
    ld      *m_s, a
    srl     a
    srl     a
    xor     a, *m_s
    ld      *m_s, a
    srl     a
    xor     a, *m_s
    and     a, #1
    jreq    01179$
    clr     *z_sk3
    jra     01180$
01179$:
    clr     *z_sk5
01180$:
    inc     *z_q
    jra     01178$
01181$:
    mov     *_dec_info+4, #1     ; chased = 1
    ; C4: bounded, data-minimal, cheapest-first (SS7.4)
    clr     *z_ww               ; phase 1: one check bit
    call    csing
    tnz     a
    jrne    01189$
    clr     *z_ww               ; phase 2: two check bits
    call    cpair
    tnz     a
    jrne    01189$
    tnz     *z_sk3
    jrne    01185$
    ld      a, #1               ; phase 3: one data bit
    ld      *z_ww, a
    call    csing
    tnz     a
    jrne    01189$
01185$:
    ld      a, #1               ; phase 4: data + check
    ld      *z_ww, a
    call    cpair
    tnz     a
    jrne    01189$
    tnz     *z_sk5
    jrne    01187$
    ld      a, #2               ; phase 5: two data bits
    ld      *z_ww, a
    call    cpair
    tnz     a
    jrne    01189$
01187$:
    ld      a, #8               ; R8: chase exhausted -- the honest end
    jra     01191$
01189$:                         ; a phase returned 1 (accept) or 2 (budget)
    cp      a, #2
    jreq    01187$              ; T_MAX budget hit -- R8 as well
    ld      a, #2               ; DEC_CHASE
01182$:                         ; shared emit tail: A = DEC_* path
    ld      *m_s, a
    ld      a, *z_comps
    ld      *_dec_info+20, a
    ldw     x, _g_PPB           ; out[0..ND-1] = d_pp[0..ND-1]
    clrw    y
01105$:
    ld      a, (_ov, x)
    ld      ([z_out], y), a
    incw    y
    incw    x
    cpw     x, _g_PPE
    jrult   01105$
    ld      a, *m_s
    ret
01191$:
    ld      *m_s, a
    ld      a, *z_comps
    ld      *_dec_info+20, a
    ld      a, *m_s
01192$:
    ld      *_dec_info+1, a      ; cause
    clr     a
    ret

; Marker template, BIT-REVERSED per byte so it XORs straight against
; d_bits.  v2.3: FF AA 65 / 9A 00 FF -> FF 55 A6 / 59 00 FF (the 0x00
; zeros probe is its own reversal).
HTR: .db 0xFF,0x55,0xA6,0x59,0x00,0xFF

; -------------------------------------------------------- ws_decode_ex
; C ABI (sdcccall(1), callee-pops): X = cap, (3,sp) = ncap, (5,sp) = out,
; return address at (1,sp).  Returns A = DEC_* (== dec_info.path).
_ws_decode_ex:
    ldw     _scan_cap, x
    ldw     x, (3, sp)
    ldw     _scan_len, x
    ldw     x, #23              ; zero every dec_info field
01195$:
    clr     (_dec_info-1, x)
    decw    x
    jrne    01195$
    call    _seed
    tnz     a
    jrne    01196$
    ld      a, #1               ; R1 no seed / K outside the window
    jra     01204$
01196$:
    call    _refine
    call    _refine
    call    _calibrate
    call    _decide_pass
    ; out[] only NOW: z_out aliases m_n, which seed/refine own.
    ldw     x, (5, sp)
    ldw     *z_out, x
    ldw     x, _g_K
    ldw     *_dec_info+9, x
    ldw     x, _g_tau
    ldw     *_dec_info+11, x
    ; d_infeas / d_laberr / d_nseg are three consecutive zero-page words
    ; and dec_info's infeasible / label_err / n_seg are consecutive too,
    ; so one 6-byte copy does all three.
    ldw     x, #6
01194$:
    ld      a, (_d_infeas-1, x)
    ld      (_dec_info+13, x), a
    decw    x
    jrne    01194$
    ; Marker mismatches: the markers are whole BYTES at both ends, so
    ; this is 2*HT_LEN byte XORs against the bit-reversed template and
    ; their popcounts -- not NB known_bit() calls.  Identical count.
    ; One loop over t = 0..5: HTR[t] pairs with d_bits[t] for t < 3 and
    ; with d_bits[NBB-6+t] (= g_TRB - 3 + t) for the trailer bytes.
    clr     *m_vi
    clrw    y
01197$:
    ldw     x, y
    cpw     x, #3
    jrult   01193$
    addw    x, _g_TRB
    subw    x, #3
01193$:
    ld      a, (_ov, x)
    ldw     x, y
    xor     a, (HTR, x)
    push    #8                  ; m_vi += popcount(A): six bytes per
01165$:                         ; frame, so decode.c's nibble table
    srl     a                   ; does not pay for itself here
    jrnc    01166$
    inc     *m_vi
01166$:
    dec     (1, sp)
    jrne    01165$
    pop     a
    incw    y
    cpw     y, #6
    jrult   01197$
    ld      a, *m_vi
    ld      *_dec_info+13, a
    ; R2, RELAXATION B: a THRESHOLD over the N_MK (48) known marker
    ; bits.  v2.2 refused on any single mismatch; v2.3 accepts up to
    ; MK_TOL and feeds the count forward as confidence (chasez caps the
    ; reference enumeration above MK_SOFT).  There is NO first/last-byte
    ; special case -- the threshold is the whole rule.
    cp      a, #13              ; violations > MK_TOL (12)?
    jrc     01198$
    ld      a, #2
    jra     01204$
01198$:
    ldw     x, *_d_infeas
    cpw     x, #24              ; GATE_INFEAS (RELAXATION A)
    jrule   01199$
    ld      a, #3
    jra     01204$
01199$:
    ldw     x, *_d_laberr
    cpw     x, #6               ; GATE_LABERR
    jrule   01200$
    ld      a, #4
    jra     01204$
01200$:
    call    chasez              ; R5..R8 / emit inside
    jra     01205$
01204$:
    ld      *_dec_info+1, a      ; cause
    clr     a
01205$:
    ld      *_dec_info+0, a      ; path
    ldw     x, (1, sp)          ; callee-pops epilogue (4 arg bytes)
    addw    sp, #6
    jp      (x)
