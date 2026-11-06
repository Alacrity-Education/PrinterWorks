                                      1 ; decode_asm.s -- size-focused hand assembly of the WHOLE v2.3 decoder:
                                      2 ; the streaming layer AND the pipeline tail (USE_ASM_DEC=1 target
                                      3 ; builds; decode.c keeps the portable C versions of every one of these
                                      4 ; functions as the host-parity reference).
                                      5 ;
                                      6 ; CONTRACT: bit-exact vs decode.c's C versions / embedded_v2.py --
                                      7 ; proven per step by recon/approaches/dev_prod/ucsim_v23.py (emitted
                                      8 ; bytes + path + cause + trials + comps + n_refs + n_weak per capture vs
                                      9 ; the Python reference) at BOTH geometries, ND = 16 and ND = 48.
                                     10 ;
                                     11 ; v2.3 geometry ONLY: 3+3 markers (48 known bits, HTR below), a 6-byte
                                     12 ; check block = one CRC-16/CCITT-FALSE written three times, the
                                     13 ; INDEPENDENT per-byte majority with its confidence-ranked reference
                                     14 ; cross product, and RELAXATIONS A/B/C.  The superseded v2.2/v2.1 CRC8
                                     15 ; geometries live only in decode.c's C (USE_ASM_DEC=0 parity builds);
                                     16 ; nothing here reads a CHK_LEN.
                                     17 ;
                                     18 ; v2.3b (2026-09-07): the pipeline tail came BACK to hand assembly --
                                     19 ; 986 B against the compiled C's 1641 B CODE + 110 B CONST, which is
                                     20 ; what closed the 748 B production-link overflow of PROD_CLOSURE SS13.1.
                                     21 ;
                                     22 ; Unlike scan.s (unrolled for SPEED), everything here is rolled for
                                     23 ; SIZE: SDCC's stm8 codegen spends 10-14 bytes per source op on the
                                     24 ; 16/32-bit expressions below; these routines share one 16x16->32
                                     25 ; multiply, one 32/32 divide and one map_raw core.
                                     26 ;
                                     27 ; SDCC sdcccall(1) ABI (matches build/decode.asm's call sites):
                                     28 ;   8-bit arg in A, 16-bit arg in X; returns A (8), X (16), Y:X (32);
                                     29 ;   A/X/Y caller-saved.
                                     30 ;
                                     31 ; Fixed-point notes used throughout (ranges proven by the reference's
                                     32 ; assert battery at both geometries):
                                     33 ;   t <= ~25.7k cy, K <= 60000  ->  t*K < 2^31, y = (t*K>>11)+tau < 2^20
                                     34 ;   p_u/p_v = yf - (BIAS + k*512) fits s16  ->  computed in low-16 only
                                     35 ;   d = y - y_prev >= 0 (y is non-decreasing after the >=0 clamp)
                                     36 
                                     37     .module decode_asm
                                     38 
                                     39     .globl _ss_init
                                     40     .globl _ss_next
                                     41     ; C-side state / constants (decode.c)
                                     42     .globl _g_K
                                     43     .globl _g_tau
                                     44     .globl _g_NB
                                     45     .globl _g_yend
                                     46     ; sample scanner (defined below -- prod builds do not link scan.s)
                                     47     .globl _scan_cap
                                     48     .globl _scan_len
                                     49     .globl _scan_init
                                     50     .globl _scan_next
                                     51     .globl _scan_ra
                                     52     .globl _scan_rb
                                     53     .globl _scan_fa
                                     54     .globl _scan_fb
                                     55     .globl _scan_sfa
                                     56 
                                     57 ; ------------------------------------------------------------------ state
                                     58 ; ZERO PAGE (ABS): every access below assembles to the SHORT (1-byte
                                     59 ; address) forms -- the whole point of hand assembly on STM8.  The link
                                     60 ; must push REL DATA above this block: --data-loc (Makefile PRODFLAGS /
                                     61 ; the ucsim harness) and guard_prod.py enforce it.
                                     62     .area DZP (ABS)
      000001                         63     .org 0x0001
                                     64 
      000001                         65 m_a:    .ds 2       ; mul16 operand A
      000003                         66 m_b:    .ds 2       ; mul16 operand B / setp base temp
      000005                         67 m_p:    .ds 4       ; mul16 product
      000009                         68 m_y:    .ds 4       ; mr16 result (s32 y)
      00000D                         69 m_s:    .ds 1       ; sign-extension byte temp
                                     70 
      00000E                         71 q_yprev: .ds 4      ; ss: previous pulse y (u32, clamped)
      000012                         72 q_n:     .ds 2      ; ss: bit index accumulator
      000014                         73 q_have:  .ds 1      ; ss: have_y
      000015                         74 q_pend:  .ds 1      ; ss: pending segment present
      000016                         75 q_pk0:   .ds 2      ; ss: pending k0
      000018                         76 q_pu:    .ds 2      ; ss: pending u (s16)
      00001A                         77 q_pv:    .ds 2      ; ss: pending v (s16)
      00001C                         78 q_pfam:  .ds 1      ; ss: pending family (slot of last high)
      00001D                         79 q_done:  .ds 1      ; ss: source exhausted
      00001E                         80 m_out:   .ds 2      ; ss_next: caller's Seg*
      000020                         81 m_fa:    .ds 2      ; low16 of map_raw(scan_fa)
      000022                         82 m_fb:    .ds 2      ; low16 of map_raw(scan_fb)
                                     83 
      000024                         84 m_n:    .ds 4       ; udiv32 dividend -> quotient
      000028                         85 m_d:    .ds 4       ; udiv32 divisor (preserved)
      00002C                         86 m_r:    .ds 4       ; udiv32 remainder
      000030                         87 r_lo:   .ds 10      ; refine lower-half block:  se(4) sy(4) n(2)
      00003A                         88 r_hi:   .ds 10      ; refine upper-half block
      000044                         89 r_melo: .ds 2
      000046                         90 r_mehi: .ds 2
      000048                         91 r_de:   .ds 2
      00004A                         92 r_dy:   .ds 4
      00004E                         93 r_dk:   .ds 4
      000052                         94 r_me:   .ds 2
      000054                         95 r_mylo: .ds 4
      000058                         96 r_myhi: .ds 4
      00005C                         97 r_sgn:  .ds 1
                                     98 
      00005D                         99 _g_sg:   .ds 9      ; shared Seg: k0(2) k1(2) u(2) v(2) fam(1)
      000066                        100 _dq_amin: .ds 2
      000068                        101 _dq_amax: .ds 2
      00006A                        102 dq_inter: .ds 2     ; interior bitmask
      00006C                        103 dq_acap: .ds 2
      00006E                        104 dq_lo:   .ds 2
      000070                        105 dq_hi:   .ds 2
      000072                        106 dq_ahat: .ds 2
      000074                        107 dq_afree: .ds 2
      000076                        108 m_h0:    .ds 2      ; effective h0/h1 for this segment
      000078                        109 m_h1:    .ds 2
      00007A                        110 m_h:     .ds 2      ; hinge h temp
      00007C                        111 m_L:     .ds 2
      00007E                        112 m_c:     .ds 2      ; scratch cost / argmin bc
      000080                        113 m_c0:    .ds 2      ; online prefix min
      000082                        114 m_c1:    .ds 2
      000084                        115 m_e:     .ds 2      ; kk1 / a_bounds end
      000086                        116 m_t:     .ds 2      ; t iterator
      000088                        117 m_off:   .ds 2
      00008A                        118 m_k:     .ds 2      ; cand_insert k
      00008C                        119 w_tiep:  .ds 2      ; v_tiepend (asm-owned)
      00008E                        120 w_tieh:  .ds 2      ; tie_here
      000090                        121 m_it:    .ds 1
      000091                        122 m_ai:    .ds 1
      000092                        123 m_ai2:   .ds 1
      000093                        124 m_alo:   .ds 1
      000094                        125 m_ahi:   .ds 1
      000095                        126 m_best:  .ds 1
      000096                        127 m_ka:    .ds 1      ; known_all
      000097                        128 m_n1:    .ds 1      ; inter-bit counter
      000098                        129 m_i0:    .ds 1      ; ins0 (0xFF = none)
                                    130 ; m_i1 is GONE: the SS6 ins1 size lever proved it dead (see SS6.4's
                                    131 ; merged interior loop below), and its byte is what keeps the REL DATA
                                    132 ; base where cap_arm.s's s_arm needs it -- see the --data-loc note.
      000099                        133 m_i:     .ds 1      ; cand_insert i
      00009A                        134 m_j:     .ds 1
      00009B                        135 m_m:     .ds 1      ; margin byte
                                    136 ; ---- decision-pass state SHARED with the C pipeline tail --------------
                                    137 ; These live in the ABS zero page (this file's hot loops address them
                                    138 ; short-form) and are exported under their decode.c names, so the C tail
                                    139 ; -- and the host-parity build of the same C -- see one set of symbols.
      00009C                        140 _d_infeas: .ds 2    ; d_infeas   (R3 counter)
      00009E                        141 _d_laberr: .ds 2    ; d_laberr   (R4 counter)
      0000A0                        142 _d_nseg:   .ds 2    ; d_nseg
      0000A2                        143 _v_ncand:  .ds 1    ; v_ncand
      0000A3                        144 _v_nweak:  .ds 2    ; v_nweak    (SS6.2)
      0000A5                        145 _v_ntied:  .ds 2    ; v_ntied    (SS6.2)
      0000A7                        146 _v_ndw:    .ds 2    ; v_ndw      (SS6.4 dead-window candidates)
      0000A9                        147 m_vi:    .ds 1      ; violations counter
                                    148 
                                    149 ; ---- size-focused sample scanner state (replaces scan.s in prod) ----
      0000AA                        150 _scan_cap: .ds 2    ; in: capture pointer
      0000AC                        151 _scan_len: .ds 2    ; in: capture bytes (= loops)
      0000AE                        152 _scan_ra:  .ds 2    ; out: rise bracket lo (cycles)
      0000B0                        153 _scan_rb:  .ds 2    ; out: rise bracket hi
      0000B2                        154 _scan_fa:  .ds 2    ; out: last-high time
      0000B4                        155 _scan_fb:  .ds 2    ; out: fall bracket hi
      0000B6                        156 _scan_sfa: .ds 1    ; out: slot of last high sample (family id)
      0000B7                        157 p_i:       .ds 2    ; loop index
      0000B9                        158 p_tb:      .ds 2    ; tbase = i * 40
      0000BB                        159 p_ws:      .ds 2    ; wsum (s16)
      0000BD                        160 p_tp:      .ds 2    ; t_prev
      0000BF                        161 p_t:       .ds 2    ; current sample time
      0000C1                        162 p_s:       .ds 1    ; slot 0..7
      0000C2                        163 p_hp:      .ds 1    ; have_prev
      0000C3                        164 p_ip:      .ds 1    ; in_pulse
      0000C4                        165 p_se:      .ds 1    ; seen
      0000C5                        166 p_dn:      .ds 1    ; done
      0000C6                        167 p_lr:      .ds 2    ; low_run
      0000C8                        168 c_lo:    .ds 4      ; calibration state (was decode.c statics)
      0000CC                        169 c_hi:    .ds 4
      0000D0                        170 c_n:     .ds 2
      0000D2                        171 zh0c:    .ds 2      ; c_h0c
      0000D4                        172 zh1c:    .ds 2      ; c_h1c
      0000D6                        173 zd56:    .ds 2      ; c_d56[2] (s8 each)
      0000D8                        174 zgap:    .ds 4      ; c_gap56[2]
                                    175 ; ---- SIZE LEVER (PROD_CLOSURE SS15.0 lever 1), taken for SS6.4 -------
                                    176 ; dec_info is OWNED HERE, in the ABS zero page: its ~18 DIRECT accesses
                                    177 ; each drop one address byte (short instead of long form) and `inc` drops
                                    178 ; two.  It is a SWAP, not growth -- labx0/labx1/labx0b/labx1b/c_c0 (20 B)
                                    179 ; move out to REL DATA below, and they are INDEXED-ONLY: sdasstm8 emits
                                    180 ; the 16-bit-offset form (0xDE/0xDF) for `(sym, x)` regardless of area,
                                    181 ; so those 25 accesses cost exactly the same there.
                                    182 ; decode.c declares it `extern` in USE_ASM_DEC builds and static-asserts
                                    183 ; sizeof(dec_info_t) == 23 against this reservation.
      0000DC                        184 _dec_info: .ds 23
                                    185 ; calibration temps ALIAS the refine scratch (r_*): refine returns before
                                    186 ; calibrate runs and nothing else touches r_* -- zero extra zero-page.
                           000030   187 w_llo   =    r_lo        ; label_interval lo out (2)  [r_lo+0..1]
                           000032   188 w_lhi   =    r_lo+2      ; label_interval hi out (2)  [r_lo+2..3]
                           000034   189 m_la    =    r_lo+4      ; cal 'a' argument (2)       [r_lo+4..5]
                           000036   190 m_f     =    r_lo+6      ; family index (1)           [r_lo+6]
                           000037   191 m_x0    =    r_lo+7      ; theta56 x0 (2)             [r_lo+7..8]
                           00003A   192 m_x1    =    r_hi        ; theta56 x1 (2)             [r_hi+0..1]
                           00003C   193 m_zlo   =    r_hi+2      ; (2)                        [r_hi+2..3]
                           00003E   194 m_zhi   =    r_hi+4      ; (2)                        [r_hi+4..5]
                           000040   195 m_th    =    r_hi+6      ; theta (2)                  [r_hi+6..7]
                           000042   196 m_hv    =    r_hi+8      ; have_theta (1)             [r_hi+8]
                           00004B   197 m_prev  =    r_dy+1      ; (2)                        [r_dy+1..2]
                           000044   198 m_blo2  =    r_melo      ; best_lo (2)
                           000046   199 m_bhi2  =    r_mehi      ; best_hi (2)
                                    200 ; chase temps ALIAS dead scratch the same way: m_cp lives in the udiv32
                                    201 ; dividend m_n, whose only users are seed/refine/mediv (all returned
                                    202 ; before the chase) and dec_eps_centi (called only after ws_decode_ex
                                    203 ; returns, when the chase is over) -- zero extra zero-page for the v2.2
                                    204 ; 4-byte check block.
                           000024   205 m_cp    =    m_n         ; chase C' bytes (4; g_CHK = 3 or 4 used)
                                    206                          ;                            [m_n+0..3]
                           000048   207 m_bg    =    r_de        ; (2)
                           00004A   208 m_no    =    r_dy        ; nocc (1)                   [r_dy+0]
                           00004E   209 m_wlo   =    r_dk        ; (2)                        [r_dk+0..1]
                           000050   210 m_whi   =    r_dk+2      ; (2)                        [r_dk+2..3]
                           000058   211 m_top   =    r_myhi      ; (2)                        [r_myhi+0..1]
                           000052   212 m_htp   =    r_me        ; have_top (1)
                           000053   213 m_cl1   =    r_me+1      ; clear1 (1)
                           000054   214 m_bb    =    r_mylo      ; hist bin iterator (1)      [r_mylo+0]
                           000055   215 m_hx    =    r_mylo+1    ; hist/labx index base (2)   [r_mylo+1..2]
                                    216 
                                    217 ; indexed-only arrays: no short-form benefit, so they live in REL DATA
                                    218 ; (keeps the zero page under 255 B)
                                    219     .area DATA
                                    220     ; d_costs is EXPORTED from v2.3 on: the C pipeline tail overlays its
                                    221     ; chase reference scratch (ch_ref / ch_val, 24 B) on it under the
                                    222     ; SS10.2 overlay rule -- d_costs is decision-pass scratch and the
                                    223     ; chase never calls decide(), so the two live ranges are disjoint.
                                    224     .globl _d_costs
      0001A8                        225 _d_costs: .ds 32    ; u16 costs[16]
      0001C8                        226 d_sm:    .ds 32     ; u16 suffix-min over [lo,hi]
                                    227 ; RELAXATION C: the candidate list is A_MAX = 11 entries (was 5).
                                    228 ; ch_isd[] is GONE -- the C tail recomputes it as (v_cand_t[i] < ND8),
                                    229 ; which is what decode.c always did; the cached copy cost 11 B of RAM
                                    230 ; and a build loop for one comparison.
                                    231     ; SS15.0 lever 1: indexed-only calibration state, moved out of the
                                    232     ; zero page to make room for dec_info.  `(labx0, x)` and friends
                                    233     ; assemble to the same 3 bytes here as they did there.
      0001E8                        234 labx0:   .ds 4
      0001EC                        235 labx1:   .ds 4
      0001F0                        236 labx0b:  .ds 4
      0001F4                        237 labx1b:  .ds 4
      0001F8                        238 c_c0:    .ds 4
      0001FC                        239 _v_cand_t: .ds 22   ; v_cand_t[11], payload' bit index (u16)
      000212                        240 _v_cand_m: .ds 11   ; v_cand_m[11], margin, (m, index) ascending
      00021D                        241 _v_chkconf: .ds 12  ; v_chkconf[6] (u16): sum of a check byte's 8 bit
                                    242                     ; margins.  v2.3 RANKS the candidates of a check-byte
                                    243                     ; position that has no per-byte majority with these.
                                    244 
                                    245     .area DZP
                                    246 
                                    247     .area CODE
                                    248 
                                    249 ; ---------------------------------------------------------------- mul16
                                    250 ; m_a * m_b (u16 x u16) -> m_p (u32).  Clobbers A, X.
      0081EB                        251 mul16:
      0081EB B6 02            [ 1]  252     ld      a, *m_a+1
      0081ED 97               [ 1]  253     ld      xl, a
      0081EE B6 04            [ 1]  254     ld      a, *m_b+1
      0081F0 42               [ 4]  255     mul     x, a                ; aL*bL
      0081F1 BF 07            [ 2]  256     ldw     *m_p+2, x
      0081F3 B6 01            [ 1]  257     ld      a, *m_a
      0081F5 97               [ 1]  258     ld      xl, a
      0081F6 B6 03            [ 1]  259     ld      a, *m_b
      0081F8 42               [ 4]  260     mul     x, a                ; aH*bH
      0081F9 BF 05            [ 2]  261     ldw     *m_p, x
      0081FB B6 02            [ 1]  262     ld      a, *m_a+1
      0081FD 97               [ 1]  263     ld      xl, a
      0081FE B6 03            [ 1]  264     ld      a, *m_b
      008200 42               [ 4]  265     mul     x, a                ; aL*bH
      008201 CD 82 0A         [ 4]  266     call    mulacc
      008204 B6 01            [ 1]  267     ld      a, *m_a
      008206 97               [ 1]  268     ld      xl, a
      008207 B6 04            [ 1]  269     ld      a, *m_b+1
      008209 42               [ 4]  270     mul     x, a                ; aH*bL
      00820A                        271 mulacc:                         ; m_p[0..2] += X<<8 (fall-through reuse)
      00820A 89               [ 2]  272     pushw   x                   ; (1,sp) = XH, (2,sp) = XL
      00820B B6 07            [ 1]  273     ld      a, *m_p+2
      00820D 1B 02            [ 1]  274     add     a, (2, sp)
      00820F B7 07            [ 1]  275     ld      *m_p+2, a
      008211 B6 06            [ 1]  276     ld      a, *m_p+1
      008213 19 01            [ 1]  277     adc     a, (1, sp)
      008215 B7 06            [ 1]  278     ld      *m_p+1, a
      008217 B6 05            [ 1]  279     ld      a, *m_p
      008219 A9 00            [ 1]  280     adc     a, #0
      00821B B7 05            [ 1]  281     ld      *m_p, a
      00821D 85               [ 2]  282     popw    x
      00821E 81               [ 4]  283     ret
                                    284 
                                    285 ; ---------------------------------------------------------------- mr16
                                    286 ; X = t (u16 cycles) -> m_y = Y:X = ((u32)t * g_K >> 11) + g_tau  (s32),
                                    287 ; exactly decode.c map_raw().  Clobbers A, X, Y.
      00821F                        288 mr16:
      00821F BF 01            [ 2]  289     ldw     *m_a, x
      008221 CE 00 F3         [ 2]  290     ldw     x, _g_K
      008224 BF 03            [ 2]  291     ldw     *m_b, x
      008226 CD 81 EB         [ 4]  292     call    mul16               ; m_p = t*K  (< 2^31)
      008229 CD 86 81         [ 4]  293     call    shp11               ; A:X = m_p >> 11 (< 2^20)
      00822C 3F 09            [ 1]  294     clr     *m_y
      00822E B7 0A            [ 1]  295     ld      *m_y+1, a
      008230 BF 0B            [ 2]  296     ldw     *m_y+2, x
                                    297     ; m_y += sext(g_tau)
      008232 C6 00 F5         [ 1]  298     ld      a, _g_tau
      008235 48               [ 1]  299     sll     a                       ; C = sign bit
      008236 4F               [ 1]  300     clr     a
      008237 A2 00            [ 1]  301     sbc     a, #0                   ; A = 0xFF if tau < 0 else 0
      008239 B7 0D            [ 1]  302     ld      *m_s, a
      00823B B6 0C            [ 1]  303     ld      a, *m_y+3
      00823D CB 00 F6         [ 1]  304     add     a, _g_tau+1
      008240 B7 0C            [ 1]  305     ld      *m_y+3, a
      008242 B6 0B            [ 1]  306     ld      a, *m_y+2
      008244 C9 00 F5         [ 1]  307     adc     a, _g_tau
      008247 B7 0B            [ 1]  308     ld      *m_y+2, a
      008249 B6 0A            [ 1]  309     ld      a, *m_y+1
      00824B B9 0D            [ 1]  310     adc     a, *m_s
      00824D B7 0A            [ 1]  311     ld      *m_y+1, a
      00824F B6 09            [ 1]  312     ld      a, *m_y
      008251 B9 0D            [ 1]  313     adc     a, *m_s
      008253 B7 09            [ 1]  314     ld      *m_y, a
      008255 90 BE 09         [ 2]  315     ldw     y, *m_y
      008258 BE 0B            [ 2]  316     ldw     x, *m_y+2
      00825A 81               [ 4]  317     ret
                                    318 
                                    319 ; ---------------------------------------------------------------- ss_init
      00825B                        320 _ss_init:
      00825B CD 91 9F         [ 4]  321     call    _scan_init
      00825E 5F               [ 1]  322     clrw    x
      00825F BF 0E            [ 2]  323     ldw     *q_yprev, x
      008261 BF 10            [ 2]  324     ldw     *q_yprev+2, x
      008263 BF 12            [ 2]  325     ldw     *q_n, x
      008265 BF 16            [ 2]  326     ldw     *q_pk0, x
      008267 BF 18            [ 2]  327     ldw     *q_pu, x
      008269 BF 1A            [ 2]  328     ldw     *q_pv, x
      00826B 3F 1C            [ 1]  329     clr     *q_pfam
      00826D 3F 14            [ 1]  330     clr     *q_have
      00826F 3F 15            [ 1]  331     clr     *q_pend
      008271 3F 1D            [ 1]  332     clr     *q_done
      008273 81               [ 4]  333     ret
                                    334 
                                    335 ; ---------------------------------------------------------------- helpers
                                    336 ; emit$: X = k1 candidate (uncapped n); writes caller's Seg from the
                                    337 ; pending slot with k1 = min(X, NB).  Clobbers A, X, Y.
      008274                        338 emit:
      008274 C3 80 95         [ 2]  339     cpw     x, _g_NB
      008277 25 03            [ 1]  340     jrc     00001$
      008279 CE 80 95         [ 2]  341     ldw     x, _g_NB
      00827C                        342 00001$:
      00827C 90 BE 1E         [ 2]  343     ldw     y, *m_out
      00827F 90 EF 02         [ 2]  344     ldw     (2, y), x               ; k1
      008282 BE 16            [ 2]  345     ldw     x, *q_pk0
      008284 90 FF            [ 2]  346     ldw     (y), x                  ; k0
      008286 BE 18            [ 2]  347     ldw     x, *q_pu
      008288 90 EF 04         [ 2]  348     ldw     (4, y), x               ; u
      00828B BE 1A            [ 2]  349     ldw     x, *q_pv
      00828D 90 EF 06         [ 2]  350     ldw     (6, y), x               ; v
      008290 B6 1C            [ 1]  351     ld      a, *q_pfam
      008292 90 E7 08         [ 1]  352     ld      (8, y), a               ; fam
      008295 81               [ 4]  353     ret
                                    354 
                                    355 ; setp$: X = k; pending <- (k, u = yfa - base, v = yfb - base, sfa) with
                                    356 ; base = BIAS + k*512 = (k+1)<<9, all in low-16 (s16 result by contract).
      008296                        357 setp:
      008296 BF 16            [ 2]  358     ldw     *q_pk0, x
      008298 5C               [ 1]  359     incw    x
      008299 9F               [ 1]  360     ld      a, xl
      00829A 5F               [ 1]  361     clrw    x
      00829B 95               [ 1]  362     ld      xh, a
      00829C 58               [ 2]  363     sllw    x                   ; X = low16((k+1) << 9)
      00829D BF 03            [ 2]  364     ldw     *m_b, x
      00829F BE 20            [ 2]  365     ldw     x, *m_fa
      0082A1 72 B0 00 03      [ 2]  366     subw    x, m_b
      0082A5 BF 18            [ 2]  367     ldw     *q_pu, x
      0082A7 BE 22            [ 2]  368     ldw     x, *m_fb
      0082A9 72 B0 00 03      [ 2]  369     subw    x, m_b
      0082AD BF 1A            [ 2]  370     ldw     *q_pv, x
      0082AF C6 00 B6         [ 1]  371     ld      a, _scan_sfa
      0082B2 B7 1C            [ 1]  372     ld      *q_pfam, a
      0082B4 81               [ 4]  373     ret
                                    374 
                                    375 ; ---------------------------------------------------------------- ss_next
                                    376 ; X = Seg* out -> A = 1 (segment written) / 0 (stream end).
      0082B5                        377 _ss_next:
      0082B5 BF 1E            [ 2]  378     ldw     *m_out, x
      0082B7                        379 00010$:                         ; while (!src_done)
      0082B7 3D 1D            [ 1]  380     tnz     *q_done
      0082B9 27 03            [ 1]  381     jreq    00040$
      0082BB CC 83 87         [ 2]  382     jp      00030$
      0082BE                        383 00040$:
      0082BE CD 91 BB         [ 4]  384     call    _scan_next
      0082C1 4D               [ 1]  385     tnz     a
      0082C2 26 07            [ 1]  386     jrne    00011$
      0082C4 35 01 00 1D      [ 1]  387     mov     q_done, #1
      0082C8 CC 83 87         [ 2]  388     jp      00030$
      0082CB                        389 00011$:
                                    390     ; y = clamp0(map_raw((ra+rb)>>1))
      0082CB CE 00 AE         [ 2]  391     ldw     x, _scan_ra
      0082CE 72 BB 00 B0      [ 2]  392     addw    x, _scan_rb
      0082D2 54               [ 2]  393     srlw    x
      0082D3 CD 82 1F         [ 4]  394     call    mr16
      0082D6 3D 09            [ 1]  395     tnz     *m_y
      0082D8 2A 05            [ 1]  396     jrpl    00012$
      0082DA 5F               [ 1]  397     clrw    x                   ; y < 0 -> 0
      0082DB BF 09            [ 2]  398     ldw     *m_y, x
      0082DD BF 0B            [ 2]  399     ldw     *m_y+2, x
      0082DF                        400 00012$:
                                    401     ; if ((u32)y > y_end) { done; break; }   (C set iff yend < y)
      0082DF C6 80 9A         [ 1]  402     ld      a, _g_yend+3
      0082E2 B0 0C            [ 1]  403     sub     a, *m_y+3
      0082E4 C6 80 99         [ 1]  404     ld      a, _g_yend+2
      0082E7 B2 0B            [ 1]  405     sbc     a, *m_y+2
      0082E9 C6 80 98         [ 1]  406     ld      a, _g_yend+1
      0082EC B2 0A            [ 1]  407     sbc     a, *m_y+1
      0082EE C6 80 97         [ 1]  408     ld      a, _g_yend
      0082F1 B2 09            [ 1]  409     sbc     a, *m_y
      0082F3 24 07            [ 1]  410     jrnc    00013$
      0082F5 35 01 00 1D      [ 1]  411     mov     q_done, #1
      0082F9 CC 83 87         [ 2]  412     jp      00030$
      0082FC                        413 00013$:
                                    414     ; have_y / gap accounting
      0082FC 3D 14            [ 1]  415     tnz     *q_have
      0082FE 26 09            [ 1]  416     jrne    00014$
      008300 5F               [ 1]  417     clrw    x
      008301 BF 12            [ 2]  418     ldw     *q_n, x
      008303 35 01 00 14      [ 1]  419     mov     q_have, #1
      008307 20 1A            [ 2]  420     jra     00015$
      008309                        421 00014$:
                                    422     ; d = y - y_prev (>= 0, < 2^20); dn = (d + 256) >> 9; n += dn
      008309 BE 0B            [ 2]  423     ldw     x, *m_y+2
      00830B 72 B0 00 10      [ 2]  424     subw    x, q_yprev+2
      00830F B6 0A            [ 1]  425     ld      a, *m_y+1
      008311 B2 0F            [ 1]  426     sbc     a, *q_yprev+1           ; A:X = d (24-bit, byte0 of both is 0)
      008313 1C 01 00         [ 2]  427     addw    x, #0x0100
      008316 A9 00            [ 1]  428     adc     a, #0
      008318 5E               [ 1]  429     swapw   x                   ; XL = old XH
      008319 95               [ 1]  430     ld      xh, a                   ; X = (A:XH_old) = (d+256) >> 8
      00831A 54               [ 2]  431     srlw    x                   ; X = dn
      00831B 27 06            [ 1]  432     jreq    00015$
      00831D 72 BB 00 12      [ 2]  433     addw    x, q_n
      008321 BF 12            [ 2]  434     ldw     *q_n, x
      008323                        435 00015$:
                                    436     ; y_prev = y; yfa/yfb low16
      008323 BE 09            [ 2]  437     ldw     x, *m_y
      008325 BF 0E            [ 2]  438     ldw     *q_yprev, x
      008327 BE 0B            [ 2]  439     ldw     x, *m_y+2
      008329 BF 10            [ 2]  440     ldw     *q_yprev+2, x
      00832B CE 00 B2         [ 2]  441     ldw     x, _scan_fa
      00832E CD 82 1F         [ 4]  442     call    mr16
      008331 BE 0B            [ 2]  443     ldw     x, *m_y+2
      008333 BF 20            [ 2]  444     ldw     *m_fa, x
      008335 CE 00 B4         [ 2]  445     ldw     x, _scan_fb
      008338 CD 82 1F         [ 4]  446     call    mr16
      00833B BE 0B            [ 2]  447     ldw     x, *m_y+2
      00833D BF 22            [ 2]  448     ldw     *m_fb, x
                                    449     ; dispatch on pend / n
      00833F 3D 15            [ 1]  450     tnz     *q_pend
      008341 27 2B            [ 1]  451     jreq    00020$
      008343 BE 12            [ 2]  452     ldw     x, *q_n
      008345 B3 16            [ 2]  453     cpw     x, *q_pk0
      008347 26 08            [ 1]  454     jrne    00016$
                                    455     ; spurious split: refresh the pending slot in place
      008349 BE 16            [ 2]  456     ldw     x, *q_pk0
      00834B CD 82 96         [ 4]  457     call    setp
      00834E CC 82 B7         [ 2]  458     jp      00010$
      008351                        459 00016$:
                                    460     ; emit pending; k1 = min(n, NB)
      008351 BE 12            [ 2]  461     ldw     x, *q_n
      008353 CD 82 74         [ 4]  462     call    emit
      008356 BE 12            [ 2]  463     ldw     x, *q_n
      008358 C3 80 95         [ 2]  464     cpw     x, _g_NB
      00835B 25 09            [ 1]  465     jrc     00017$
      00835D 3F 15            [ 1]  466     clr     *q_pend
      00835F 35 01 00 1D      [ 1]  467     mov     q_done, #1
      008363 A6 01            [ 1]  468     ld      a, #1
      008365 81               [ 4]  469     ret
      008366                        470 00017$:
      008366 BE 12            [ 2]  471     ldw     x, *q_n                 ; roll pending to n (pend stays 1)
      008368 CD 82 96         [ 4]  472     call    setp
      00836B A6 01            [ 1]  473     ld      a, #1
      00836D 81               [ 4]  474     ret
      00836E                        475 00020$:
                                    476     ; no pending segment yet
      00836E BE 12            [ 2]  477     ldw     x, *q_n
      008370 C3 80 95         [ 2]  478     cpw     x, _g_NB
      008373 25 06            [ 1]  479     jrc     00021$
      008375 35 01 00 1D      [ 1]  480     mov     q_done, #1
      008379 20 0C            [ 2]  481     jra     00030$
      00837B                        482 00021$:
      00837B BE 12            [ 2]  483     ldw     x, *q_n
      00837D CD 82 96         [ 4]  484     call    setp
      008380 35 01 00 15      [ 1]  485     mov     q_pend, #1
      008384 CC 82 B7         [ 2]  486     jp      00010$
                                    487 
      008387                        488 00030$:                         ; stream end: flush the pending segment
      008387 3D 15            [ 1]  489     tnz     *q_pend
      008389 27 0B            [ 1]  490     jreq    00031$
      00838B 3F 15            [ 1]  491     clr     *q_pend
      00838D CE 80 95         [ 2]  492     ldw     x, _g_NB                ; tail k1 = NB
      008390 CD 82 74         [ 4]  493     call    emit
      008393 A6 01            [ 1]  494     ld      a, #1
      008395 81               [ 4]  495     ret
      008396                        496 00031$:
      008396 4F               [ 1]  497     clr     a
      008397 81               [ 4]  498     ret
                                    499 
                                    500 ; ======================================================================
                                    501 ; refine() -- P2 residual-regression lock refinement, bit-exact port of
                                    502 ; decode.c's C version.  Uses mr16/mul16 above plus udiv32 below.
                                    503 ; Range notes (reference assert battery): e in [-256,255]; |me| <= 256 so
                                    504 ; de fits s16; sy sums < 2^27; my quotients < 2^20; K*de < 2^25;
                                    505 ; |de*(my-tau)| < 2^31 (asserted); dtau/tau commits are exact in low-16
                                    506 ; (C truncates to int16_t).
                                    507 ; ======================================================================
                                    508 
                                    509     .globl _refine
                                    510     .globl _g_ymid
                                    511 
                                    512     .area CODE
                                    513 
                                    514 ; ---------------------------------------------------------------- udiv32
                                    515 ; m_n / m_d -> quotient in m_n, remainder in m_r.  m_d preserved.
                                    516 ; Clobbers A, X, Y, m_s.
      008398                        517 udiv32:
      008398 3F 2C            [ 1]  518     clr     *m_r
      00839A 3F 2D            [ 1]  519     clr     *m_r+1
      00839C 3F 2E            [ 1]  520     clr     *m_r+2
      00839E 3F 2F            [ 1]  521     clr     *m_r+3
      0083A0 35 20 00 0D      [ 1]  522     mov     m_s, #32
      0083A4                        523 00050$:
      0083A4 38 27            [ 1]  524     sll     *m_n+3                  ; N <<= 1, MSB -> C
      0083A6 39 26            [ 1]  525     rlc     *m_n+2
      0083A8 39 25            [ 1]  526     rlc     *m_n+1
      0083AA 39 24            [ 1]  527     rlc     *m_n
      0083AC 39 2F            [ 1]  528     rlc     *m_r+3                  ; C -> R
      0083AE 39 2E            [ 1]  529     rlc     *m_r+2
      0083B0 39 2D            [ 1]  530     rlc     *m_r+1
      0083B2 39 2C            [ 1]  531     rlc     *m_r
      0083B4 B6 2F            [ 1]  532     ld      a, *m_r+3               ; R - D (trial)
      0083B6 B0 2B            [ 1]  533     sub     a, *m_d+3
      0083B8 97               [ 1]  534     ld      xl, a
      0083B9 B6 2E            [ 1]  535     ld      a, *m_r+2
      0083BB B2 2A            [ 1]  536     sbc     a, *m_d+2
      0083BD 95               [ 1]  537     ld      xh, a
      0083BE B6 2D            [ 1]  538     ld      a, *m_r+1
      0083C0 B2 29            [ 1]  539     sbc     a, *m_d+1
      0083C2 90 97            [ 1]  540     ld      yl, a
      0083C4 B6 2C            [ 1]  541     ld      a, *m_r
      0083C6 B2 28            [ 1]  542     sbc     a, *m_d
      0083C8 25 0A            [ 1]  543     jrc     00051$              ; R < D: restore (keep old R)
      0083CA B7 2C            [ 1]  544     ld      *m_r, a
      0083CC 90 9F            [ 1]  545     ld      a, yl
      0083CE B7 2D            [ 1]  546     ld      *m_r+1, a
      0083D0 BF 2E            [ 2]  547     ldw     *m_r+2, x
      0083D2 3C 27            [ 1]  548     inc     *m_n+3                  ; quotient bit (bit0 is 0 after sll)
      0083D4                        549 00051$:
      0083D4 3A 0D            [ 1]  550     dec     *m_s
      0083D6 26 CC            [ 1]  551     jrne    00050$
      0083D8 81               [ 4]  552     ret
                                    553 
                                    554 ; negmn: m_n = -m_n (32-bit two's complement)
      0083D9                        555 negmn:
      0083D9 4F               [ 1]  556     clr     a
      0083DA B0 27            [ 1]  557     sub     a, *m_n+3
      0083DC B7 27            [ 1]  558     ld      *m_n+3, a
      0083DE 4F               [ 1]  559     clr     a
      0083DF B2 26            [ 1]  560     sbc     a, *m_n+2
      0083E1 B7 26            [ 1]  561     ld      *m_n+2, a
      0083E3 4F               [ 1]  562     clr     a
      0083E4 B2 25            [ 1]  563     sbc     a, *m_n+1
      0083E6 B7 25            [ 1]  564     ld      *m_n+1, a
      0083E8 4F               [ 1]  565     clr     a
      0083E9 B2 24            [ 1]  566     sbc     a, *m_n
      0083EB B7 24            [ 1]  567     ld      *m_n, a
      0083ED 81               [ 4]  568     ret
                                    569 
                                    570 ; accum: Y = block (r_lo/r_hi), X = e (s16), m_y = y (u32 clamped):
                                    571 ;   se += sext(e); sy += y; n++
      0083EE                        572 accum:
      0083EE 9E               [ 1]  573     ld      a, xh
      0083EF 48               [ 1]  574     sll     a
      0083F0 4F               [ 1]  575     clr     a
      0083F1 A2 00            [ 1]  576     sbc     a, #0
      0083F3 B7 0D            [ 1]  577     ld      *m_s, a                 ; sign byte of e
      0083F5 89               [ 2]  578     pushw   x                   ; (1,sp)=eH (2,sp)=eL
      0083F6 90 E6 03         [ 1]  579     ld      a, (3, y)
      0083F9 1B 02            [ 1]  580     add     a, (2, sp)
      0083FB 90 E7 03         [ 1]  581     ld      (3, y), a
      0083FE 90 E6 02         [ 1]  582     ld      a, (2, y)
      008401 19 01            [ 1]  583     adc     a, (1, sp)
      008403 90 E7 02         [ 1]  584     ld      (2, y), a
      008406 90 E6 01         [ 1]  585     ld      a, (1, y)
      008409 B9 0D            [ 1]  586     adc     a, *m_s
      00840B 90 E7 01         [ 1]  587     ld      (1, y), a
      00840E 90 F6            [ 1]  588     ld      a, (y)
      008410 B9 0D            [ 1]  589     adc     a, *m_s
      008412 90 F7            [ 1]  590     ld      (y), a
      008414 85               [ 2]  591     popw    x
      008415 90 E6 07         [ 1]  592     ld      a, (7, y)
      008418 BB 0C            [ 1]  593     add     a, *m_y+3
      00841A 90 E7 07         [ 1]  594     ld      (7, y), a
      00841D 90 E6 06         [ 1]  595     ld      a, (6, y)
      008420 B9 0B            [ 1]  596     adc     a, *m_y+2
      008422 90 E7 06         [ 1]  597     ld      (6, y), a
      008425 90 E6 05         [ 1]  598     ld      a, (5, y)
      008428 B9 0A            [ 1]  599     adc     a, *m_y+1
      00842A 90 E7 05         [ 1]  600     ld      (5, y), a
      00842D 90 E6 04         [ 1]  601     ld      a, (4, y)
      008430 B9 09            [ 1]  602     adc     a, *m_y
      008432 90 E7 04         [ 1]  603     ld      (4, y), a
      008435 90 E6 09         [ 1]  604     ld      a, (9, y)               ; n++ (16-bit, byte-wise: no LDW X,(o,Y))
      008438 AB 01            [ 1]  605     add     a, #1
      00843A 90 E7 09         [ 1]  606     ld      (9, y), a
      00843D 90 E6 08         [ 1]  607     ld      a, (8, y)
      008440 A9 00            [ 1]  608     adc     a, #0
      008442 90 E7 08         [ 1]  609     ld      (8, y), a
      008445 81               [ 4]  610     ret
                                    611 
                                    612 
                                    613 ; ---- relocated into the vector-table gap (vectors_prod.s): 0x8004..0x8063
                                    614     .area VGAP (ABS)
      008004                        615     .org 0x8004
                                    616 
                                    617     .globl sot                  ; exported ONLY as the guard_prod.py anchor
                                    618                                 ; for the VGAP window check (ABS areas
                                    619                                 ; print addr 0 in sdld maps)
      008004 00 04 09 0D 11 15 1B   620 sot: .db 0, 4, 9, 13, 17, 21, 27, 32       ; O_CY[8]
             20
      00800C 00 FF 00 02 00 00 00   621 swt: .db 0, 0xFF, 0, 2, 0, 0, 0, 1         ; W_CY[8] (s8)
             01
                                    622 
                                    623 ; mediv: X = block -> X = se/n as s16 (C truncation; |result| <= 256)
      008014                        624 mediv:
      008014 89               [ 2]  625     pushw   x                   ; block ptr at (1,sp)
      008015 FE               [ 2]  626     ldw     x, (x)
      008016 BF 24            [ 2]  627     ldw     *m_n, x
      008018 1E 01            [ 2]  628     ldw     x, (1, sp)
      00801A EE 02            [ 2]  629     ldw     x, (2, x)
      00801C BF 26            [ 2]  630     ldw     *m_n+2, x
      00801E 5F               [ 1]  631     clrw    x
      00801F BF 28            [ 2]  632     ldw     *m_d, x
      008021 1E 01            [ 2]  633     ldw     x, (1, sp)
      008023 EE 08            [ 2]  634     ldw     x, (8, x)
      008025 BF 2A            [ 2]  635     ldw     *m_d+2, x
      008027 85               [ 2]  636     popw    x
      008028 3F 5C            [ 1]  637     clr     *r_sgn
      00802A 3D 24            [ 1]  638     tnz     *m_n
      00802C 2A 07            [ 1]  639     jrpl    00055$
      00802E 35 01 00 5C      [ 1]  640     mov     r_sgn, #1
      008032 CD 83 D9         [ 4]  641     call    negmn
      008035                        642 00055$:
      008035 CD 83 98         [ 4]  643     call    udiv32
      008038 BE 26            [ 2]  644     ldw     x, *m_n+2
      00803A 3D 5C            [ 1]  645     tnz     *r_sgn
      00803C 27 01            [ 1]  646     jreq    00056$
      00803E 50               [ 2]  647     negw    x
      00803F                        648 00056$:
      00803F 81               [ 4]  649     ret
                                    650 
                                    651 ; mydiv: X = block -> m_n = sy/n (u32)
      008040                        652 mydiv:
      008040 89               [ 2]  653     pushw   x
      008041 EE 04            [ 2]  654     ldw     x, (4, x)
      008043 BF 24            [ 2]  655     ldw     *m_n, x
      008045 1E 01            [ 2]  656     ldw     x, (1, sp)
      008047 EE 06            [ 2]  657     ldw     x, (6, x)
      008049 BF 26            [ 2]  658     ldw     *m_n+2, x
      00804B 5F               [ 1]  659     clrw    x
      00804C BF 28            [ 2]  660     ldw     *m_d, x
      00804E 1E 01            [ 2]  661     ldw     x, (1, sp)
      008050 EE 08            [ 2]  662     ldw     x, (8, x)
      008052 BF 2A            [ 2]  663     ldw     *m_d+2, x
      008054 85               [ 2]  664     popw    x
      008055 CC 83 98         [ 2]  665     jp      udiv32
                                    666 
                                    667 ; hix: A = f (0/1) -> X = f*64 (c_hist row base within ov.hist).
                                    668 ; Lives in the vector gap: 7 bytes that the REL side no longer pays for.
      008058                        669 hix:
      008058 5F               [ 1]  670     clrw    x
      008059 4D               [ 1]  671     tnz     a
      00805A 27 03            [ 1]  672     jreq    00510$
      00805C AE 00 40         [ 2]  673     ldw     x, #64
      00805F                        674 00510$:
      00805F 81               [ 4]  675     ret
                                    676 
                                    677 
                                    678     .area CODE
                                    679 
                                    680 ; ---------------------------------------------------------------- refine
      008446                        681 _refine:
      008446 AE 00 14         [ 2]  682     ldw     x, #20                  ; zero r_lo + r_hi (adjacent)
      008449                        683 00060$:
      008449 72 4F 00 2F      [ 1]  684     clr     (r_lo-1, x)
      00844D 5A               [ 2]  685     decw    x
      00844E 26 F9            [ 1]  686     jrne    00060$
      008450 CD 91 9F         [ 4]  687     call    _scan_init
      008453                        688 00061$:                         ; pulse loop
      008453 CD 91 BB         [ 4]  689     call    _scan_next
      008456 4D               [ 1]  690     tnz     a
      008457 27 6A            [ 1]  691     jreq    00070$
      008459 CE 00 AE         [ 2]  692     ldw     x, _scan_ra
      00845C 72 BB 00 B0      [ 2]  693     addw    x, _scan_rb
      008460 54               [ 2]  694     srlw    x
      008461 CD 82 1F         [ 4]  695     call    mr16
      008464 3D 09            [ 1]  696     tnz     *m_y
      008466 2A 05            [ 1]  697     jrpl    00062$
      008468 5F               [ 1]  698     clrw    x                   ; clamp y >= 0
      008469 BF 09            [ 2]  699     ldw     *m_y, x
      00846B BF 0B            [ 2]  700     ldw     *m_y+2, x
      00846D                        701 00062$:
      00846D C6 80 9A         [ 1]  702     ld      a, _g_yend+3            ; if y > y_end: stop accumulating
      008470 B0 0C            [ 1]  703     sub     a, *m_y+3
      008472 C6 80 99         [ 1]  704     ld      a, _g_yend+2
      008475 B2 0B            [ 1]  705     sbc     a, *m_y+2
      008477 C6 80 98         [ 1]  706     ld      a, _g_yend+1
      00847A B2 0A            [ 1]  707     sbc     a, *m_y+1
      00847C C6 80 97         [ 1]  708     ld      a, _g_yend
      00847F B2 09            [ 1]  709     sbc     a, *m_y
      008481 25 40            [ 1]  710     jrc     00070$
                                    711     ; q = (y + 256) >> 9 ; e = low16(y) - low16(q << 9)
      008483 BE 0B            [ 2]  712     ldw     x, *m_y+2
      008485 B6 0A            [ 1]  713     ld      a, *m_y+1
      008487 1C 01 00         [ 2]  714     addw    x, #0x0100
      00848A A9 00            [ 1]  715     adc     a, #0
      00848C 5E               [ 1]  716     swapw   x
      00848D 95               [ 1]  717     ld      xh, a
      00848E 54               [ 2]  718     srlw    x                   ; X = q
      00848F 9F               [ 1]  719     ld      a, xl
      008490 5F               [ 1]  720     clrw    x
      008491 95               [ 1]  721     ld      xh, a
      008492 58               [ 2]  722     sllw    x                   ; X = low16(q << 9)
      008493 BF 03            [ 2]  723     ldw     *m_b, x
      008495 BE 0B            [ 2]  724     ldw     x, *m_y+2
      008497 72 B0 00 03      [ 2]  725     subw    x, m_b              ; X = e (s16 exact)
                                    726     ; block = (y < mid_u) ? r_lo : r_hi
      00849B B6 0C            [ 1]  727     ld      a, *m_y+3
      00849D C0 80 9E         [ 1]  728     sub     a, _g_ymid+3
      0084A0 B6 0B            [ 1]  729     ld      a, *m_y+2
      0084A2 C2 80 9D         [ 1]  730     sbc     a, _g_ymid+2
      0084A5 B6 0A            [ 1]  731     ld      a, *m_y+1
      0084A7 C2 80 9C         [ 1]  732     sbc     a, _g_ymid+1
      0084AA B6 09            [ 1]  733     ld      a, *m_y
      0084AC C2 80 9B         [ 1]  734     sbc     a, _g_ymid
      0084AF 25 06            [ 1]  735     jrc     00063$
      0084B1 90 AE 00 3A      [ 2]  736     ldw     y, #r_hi
      0084B5 20 04            [ 2]  737     jra     00064$
      0084B7                        738 00063$:
      0084B7 90 AE 00 30      [ 2]  739     ldw     y, #r_lo
      0084BB                        740 00064$:
      0084BB CD 83 EE         [ 4]  741     call    accum
      0084BE 20 93            [ 2]  742     jra     00061$
                                    743 
      0084C0                        744 00069$:
      0084C0 CC 86 80         [ 2]  745     jp      00099$              ; short-branch trampoline to the ret
      0084C3                        746 00070$:                         ; stats
      0084C3 BE 38            [ 2]  747     ldw     x, *r_lo+8
      0084C5 A3 00 02         [ 2]  748     cpw     x, #2
      0084C8 25 F6            [ 1]  749     jrc     00069$
      0084CA BE 42            [ 2]  750     ldw     x, *r_hi+8
      0084CC A3 00 02         [ 2]  751     cpw     x, #2
      0084CF 25 EF            [ 1]  752     jrc     00069$
      0084D1 AE 00 30         [ 2]  753     ldw     x, #r_lo
      0084D4 CD 80 14         [ 4]  754     call    mediv
      0084D7 BF 44            [ 2]  755     ldw     *r_melo, x
      0084D9 AE 00 3A         [ 2]  756     ldw     x, #r_hi
      0084DC CD 80 14         [ 4]  757     call    mediv
      0084DF BF 46            [ 2]  758     ldw     *r_mehi, x
      0084E1 AE 00 30         [ 2]  759     ldw     x, #r_lo
      0084E4 CD 80 40         [ 4]  760     call    mydiv
      0084E7 BE 24            [ 2]  761     ldw     x, *m_n
      0084E9 BF 54            [ 2]  762     ldw     *r_mylo, x
      0084EB BE 26            [ 2]  763     ldw     x, *m_n+2
      0084ED BF 56            [ 2]  764     ldw     *r_mylo+2, x
      0084EF AE 00 3A         [ 2]  765     ldw     x, #r_hi
      0084F2 CD 80 40         [ 4]  766     call    mydiv
      0084F5 BE 24            [ 2]  767     ldw     x, *m_n
      0084F7 BF 58            [ 2]  768     ldw     *r_myhi, x
      0084F9 BE 26            [ 2]  769     ldw     x, *m_n+2
      0084FB BF 5A            [ 2]  770     ldw     *r_myhi+2, x
      0084FD BE 46            [ 2]  771     ldw     x, *r_mehi              ; de = me_hi - me_lo (s16, |de| <= 512)
      0084FF 72 B0 00 44      [ 2]  772     subw    x, r_melo
      008503 BF 48            [ 2]  773     ldw     *r_de, x
      008505 B6 5B            [ 1]  774     ld      a, *r_myhi+3            ; dy = my_hi - my_lo (s32)
      008507 B0 57            [ 1]  775     sub     a, *r_mylo+3
      008509 B7 4D            [ 1]  776     ld      *r_dy+3, a
      00850B B6 5A            [ 1]  777     ld      a, *r_myhi+2
      00850D B2 56            [ 1]  778     sbc     a, *r_mylo+2
      00850F B7 4C            [ 1]  779     ld      *r_dy+2, a
      008511 B6 59            [ 1]  780     ld      a, *r_myhi+1
      008513 B2 55            [ 1]  781     sbc     a, *r_mylo+1
      008515 B7 4B            [ 1]  782     ld      *r_dy+1, a
      008517 B6 58            [ 1]  783     ld      a, *r_myhi
      008519 B2 54            [ 1]  784     sbc     a, *r_mylo
      00851B B7 4A            [ 1]  785     ld      *r_dy, a
      00851D 2A 03            [ 1]  786     jrpl    00067$
      00851F CC 86 80         [ 2]  787     jp      00099$              ; dy < 0
      008522                        788 00067$:
      008522 B6 4A            [ 1]  789     ld      a, *r_dy
      008524 BA 4B            [ 1]  790     or      a, *r_dy+1
      008526 BA 4C            [ 1]  791     or      a, *r_dy+2
      008528 BA 4D            [ 1]  792     or      a, *r_dy+3
      00852A 26 03            [ 1]  793     jrne    00068$
      00852C CC 86 80         [ 2]  794     jp      00099$              ; dy == 0
      00852F                        795 00068$:
                                    796     ; dk = (K * de) / dy  (sign of de; dy > 0)
      00852F BE 48            [ 2]  797     ldw     x, *r_de
      008531 3F 5C            [ 1]  798     clr     *r_sgn
      008533 5D               [ 2]  799     tnzw    x
      008534 2A 05            [ 1]  800     jrpl    00071$
      008536 50               [ 2]  801     negw    x
      008537 35 01 00 5C      [ 1]  802     mov     r_sgn, #1
      00853B                        803 00071$:
      00853B BF 01            [ 2]  804     ldw     *m_a, x
      00853D CE 00 F3         [ 2]  805     ldw     x, _g_K
      008540 BF 03            [ 2]  806     ldw     *m_b, x
      008542 CD 81 EB         [ 4]  807     call    mul16               ; m_p = K * |de| (< 2^25)
      008545 BE 05            [ 2]  808     ldw     x, *m_p
      008547 BF 24            [ 2]  809     ldw     *m_n, x
      008549 BE 07            [ 2]  810     ldw     x, *m_p+2
      00854B BF 26            [ 2]  811     ldw     *m_n+2, x
      00854D BE 4A            [ 2]  812     ldw     x, *r_dy
      00854F BF 28            [ 2]  813     ldw     *m_d, x
      008551 BE 4C            [ 2]  814     ldw     x, *r_dy+2
      008553 BF 2A            [ 2]  815     ldw     *m_d+2, x
      008555 CD 83 98         [ 4]  816     call    udiv32
      008558 3D 5C            [ 1]  817     tnz     *r_sgn
      00855A 27 03            [ 1]  818     jreq    00072$
      00855C CD 83 D9         [ 4]  819     call    negmn
      00855F                        820 00072$:
      00855F BE 24            [ 2]  821     ldw     x, *m_n                 ; r_dk = signed dk
      008561 BF 4E            [ 2]  822     ldw     *r_dk, x
      008563 BE 26            [ 2]  823     ldw     x, *m_n+2
      008565 BF 50            [ 2]  824     ldw     *r_dk+2, x
                                    825     ; me = (se_lo + se_hi) / (n_lo + n_hi) -> r_me (s16 exact)
      008567 B6 33            [ 1]  826     ld      a, *r_lo+3
      008569 BB 3D            [ 1]  827     add     a, *r_hi+3
      00856B B7 27            [ 1]  828     ld      *m_n+3, a
      00856D B6 32            [ 1]  829     ld      a, *r_lo+2
      00856F B9 3C            [ 1]  830     adc     a, *r_hi+2
      008571 B7 26            [ 1]  831     ld      *m_n+2, a
      008573 B6 31            [ 1]  832     ld      a, *r_lo+1
      008575 B9 3B            [ 1]  833     adc     a, *r_hi+1
      008577 B7 25            [ 1]  834     ld      *m_n+1, a
      008579 B6 30            [ 1]  835     ld      a, *r_lo
      00857B B9 3A            [ 1]  836     adc     a, *r_hi
      00857D B7 24            [ 1]  837     ld      *m_n, a
      00857F 5F               [ 1]  838     clrw    x
      008580 BF 28            [ 2]  839     ldw     *m_d, x
      008582 BE 38            [ 2]  840     ldw     x, *r_lo+8
      008584 72 BB 00 42      [ 2]  841     addw    x, r_hi+8
      008588 BF 2A            [ 2]  842     ldw     *m_d+2, x
      00858A 3F 5C            [ 1]  843     clr     *r_sgn
      00858C 3D 24            [ 1]  844     tnz     *m_n
      00858E 2A 07            [ 1]  845     jrpl    00073$
      008590 35 01 00 5C      [ 1]  846     mov     r_sgn, #1
      008594 CD 83 D9         [ 4]  847     call    negmn
      008597                        848 00073$:
      008597 CD 83 98         [ 4]  849     call    udiv32
      00859A BE 26            [ 2]  850     ldw     x, *m_n+2
      00859C 3D 5C            [ 1]  851     tnz     *r_sgn
      00859E 27 01            [ 1]  852     jreq    00074$
      0085A0 50               [ 2]  853     negw    x
      0085A1                        854 00074$:
      0085A1 BF 52            [ 2]  855     ldw     *r_me, x
                                    856     ; my = (sy_lo + sy_hi) / n_tot (m_d still holds n_tot)
      0085A3 B6 37            [ 1]  857     ld      a, *r_lo+7
      0085A5 BB 41            [ 1]  858     add     a, *r_hi+7
      0085A7 B7 27            [ 1]  859     ld      *m_n+3, a
      0085A9 B6 36            [ 1]  860     ld      a, *r_lo+6
      0085AB B9 40            [ 1]  861     adc     a, *r_hi+6
      0085AD B7 26            [ 1]  862     ld      *m_n+2, a
      0085AF B6 35            [ 1]  863     ld      a, *r_lo+5
      0085B1 B9 3F            [ 1]  864     adc     a, *r_hi+5
      0085B3 B7 25            [ 1]  865     ld      *m_n+1, a
      0085B5 B6 34            [ 1]  866     ld      a, *r_lo+4
      0085B7 B9 3E            [ 1]  867     adc     a, *r_hi+4
      0085B9 B7 24            [ 1]  868     ld      *m_n, a
      0085BB CD 83 98         [ 4]  869     call    udiv32              ; m_n = my (u32)
                                    870     ; m2 = my - sext(g_tau)  (s32)
      0085BE C6 00 F5         [ 1]  871     ld      a, _g_tau
      0085C1 48               [ 1]  872     sll     a
      0085C2 4F               [ 1]  873     clr     a
      0085C3 A2 00            [ 1]  874     sbc     a, #0
      0085C5 B7 0D            [ 1]  875     ld      *m_s, a
      0085C7 B6 27            [ 1]  876     ld      a, *m_n+3
      0085C9 C0 00 F6         [ 1]  877     sub     a, _g_tau+1
      0085CC B7 27            [ 1]  878     ld      *m_n+3, a
      0085CE B6 26            [ 1]  879     ld      a, *m_n+2
      0085D0 C2 00 F5         [ 1]  880     sbc     a, _g_tau
      0085D3 B7 26            [ 1]  881     ld      *m_n+2, a
      0085D5 B6 25            [ 1]  882     ld      a, *m_n+1
      0085D7 B2 0D            [ 1]  883     sbc     a, *m_s
      0085D9 B7 25            [ 1]  884     ld      *m_n+1, a
      0085DB B6 24            [ 1]  885     ld      a, *m_n
      0085DD B2 0D            [ 1]  886     sbc     a, *m_s
      0085DF B7 24            [ 1]  887     ld      *m_n, a
                                    888     ; p_sign = sign(m2) ^ sign(de); |m2| (u24), |de|
      0085E1 3F 5C            [ 1]  889     clr     *r_sgn
      0085E3 3D 24            [ 1]  890     tnz     *m_n
      0085E5 2A 07            [ 1]  891     jrpl    00075$
      0085E7 35 01 00 5C      [ 1]  892     mov     r_sgn, #1
      0085EB CD 83 D9         [ 4]  893     call    negmn
      0085EE                        894 00075$:
      0085EE BE 48            [ 2]  895     ldw     x, *r_de
      0085F0 5D               [ 2]  896     tnzw    x
      0085F1 2A 07            [ 1]  897     jrpl    00076$
      0085F3 50               [ 2]  898     negw    x
      0085F4 B6 5C            [ 1]  899     ld      a, *r_sgn
      0085F6 A8 01            [ 1]  900     xor     a, #1
      0085F8 B7 5C            [ 1]  901     ld      *r_sgn, a
      0085FA                        902 00076$:
                                    903     ; P = |de| * |m2|  = mul16(|de|, m2_lo16) + (m2_b1 * |de|) << 16
      0085FA BF 01            [ 2]  904     ldw     *m_a, x                 ; |de|
      0085FC BE 26            [ 2]  905     ldw     x, *m_n+2
      0085FE BF 03            [ 2]  906     ldw     *m_b, x                 ; m2 low16
      008600 B6 25            [ 1]  907     ld      a, *m_n+1               ; m2 byte1 (<= 7)
      008602 88               [ 1]  908     push    a
      008603 CD 81 EB         [ 4]  909     call    mul16               ; m_p = |de| * lo16
      008606 BE 05            [ 2]  910     ldw     x, *m_p
      008608 BF 24            [ 2]  911     ldw     *m_n, x
      00860A BE 07            [ 2]  912     ldw     x, *m_p+2
      00860C BF 26            [ 2]  913     ldw     *m_n+2, x
      00860E 84               [ 1]  914     pop     a
      00860F 4D               [ 1]  915     tnz     a
      008610 27 20            [ 1]  916     jreq    00078$
      008612 88               [ 1]  917     push    a
      008613 97               [ 1]  918     ld      xl, a
      008614 B6 02            [ 1]  919     ld      a, *m_a+1               ; |de| low byte
      008616 42               [ 4]  920     mul     x, a
      008617 89               [ 2]  921     pushw   x                   ; high-word add: m_n[0..1] += mh*deL
      008618 B6 25            [ 1]  922     ld      a, *m_n+1
      00861A 1B 02            [ 1]  923     add     a, (2, sp)
      00861C B7 25            [ 1]  924     ld      *m_n+1, a
      00861E B6 24            [ 1]  925     ld      a, *m_n
      008620 19 01            [ 1]  926     adc     a, (1, sp)
      008622 B7 24            [ 1]  927     ld      *m_n, a
      008624 85               [ 2]  928     popw    x
      008625 84               [ 1]  929     pop     a
      008626 97               [ 1]  930     ld      xl, a
      008627 B6 01            [ 1]  931     ld      a, *m_a                 ; |de| high byte (<= 2)
      008629 42               [ 4]  932     mul     x, a                ; <= 14
      00862A 89               [ 2]  933     pushw   x
      00862B B6 24            [ 1]  934     ld      a, *m_n
      00862D 1B 02            [ 1]  935     add     a, (2, sp)
      00862F B7 24            [ 1]  936     ld      *m_n, a
      008631 85               [ 2]  937     popw    x
      008632                        938 00078$:
                                    939     ; Q = P / dy
      008632 BE 4A            [ 2]  940     ldw     x, *r_dy
      008634 BF 28            [ 2]  941     ldw     *m_d, x
      008636 BE 4C            [ 2]  942     ldw     x, *r_dy+2
      008638 BF 2A            [ 2]  943     ldw     *m_d+2, x
      00863A CD 83 98         [ 4]  944     call    udiv32
      00863D BE 26            [ 2]  945     ldw     x, *m_n+2               ; low16 of |Q|
      00863F 3D 5C            [ 1]  946     tnz     *r_sgn
      008641 27 01            [ 1]  947     jreq    00079$
      008643 50               [ 2]  948     negw    x
      008644                        949 00079$:
      008644 72 B0 00 52      [ 2]  950     subw    x, r_me             ; dtau16 = Q - me
                                    951     ; K2 = zext(g_K) - dk; commit iff 46000 <= K2 <= 60000
      008648 89               [ 2]  952     pushw   x
      008649 C6 00 F4         [ 1]  953     ld      a, _g_K+1
      00864C B0 51            [ 1]  954     sub     a, *r_dk+3
      00864E B7 27            [ 1]  955     ld      *m_n+3, a
      008650 C6 00 F3         [ 1]  956     ld      a, _g_K
      008653 B2 50            [ 1]  957     sbc     a, *r_dk+2
      008655 B7 26            [ 1]  958     ld      *m_n+2, a
      008657 4F               [ 1]  959     clr     a
      008658 B2 4F            [ 1]  960     sbc     a, *r_dk+1
      00865A B7 25            [ 1]  961     ld      *m_n+1, a
      00865C 4F               [ 1]  962     clr     a
      00865D B2 4E            [ 1]  963     sbc     a, *r_dk
      00865F B7 24            [ 1]  964     ld      *m_n, a
      008661 B6 24            [ 1]  965     ld      a, *m_n
      008663 BA 25            [ 1]  966     or      a, *m_n+1
      008665 26 18            [ 1]  967     jrne    00098$              ; negative or >= 65536
      008667 BE 26            [ 2]  968     ldw     x, *m_n+2
      008669 A3 B3 B0         [ 2]  969     cpw     x, #46000
      00866C 25 11            [ 1]  970     jrc     00098$
      00866E A3 EA 61         [ 2]  971     cpw     x, #60001
      008671 24 0C            [ 1]  972     jrnc    00098$
      008673 CF 00 F3         [ 2]  973     ldw     _g_K, x
      008676 85               [ 2]  974     popw    x
      008677 72 BB 00 F5      [ 2]  975     addw    x, _g_tau
      00867B CF 00 F5         [ 2]  976     ldw     _g_tau, x
      00867E 81               [ 4]  977     ret
      00867F                        978 00098$:
      00867F 85               [ 2]  979     popw    x
      008680                        980 00099$:
      008680 81               [ 4]  981     ret
                                    982 
                                    983 ; ======================================================================
                                    984 ; seed() / dec_eps_centi() / set_gap56() -- the remaining 32-bit users,
                                    985 ; ported so USE_ASM_DEC builds link NO SDCC 32-bit library at all.
                                    986 ; ======================================================================
                                    987 
                                    988     .globl _seed
                                    989     .globl _dec_eps_centi
                                    990     .globl _set_gap56
                                    991     .globl _g_Wu11
                                    992     .globl _dec_info
                                    993 
                                    994     .area CODE
                                    995 
                                    996 ; shp11: A:X = m_p >> 11 (m_p < 2^31).  Shared by mr16/seed/set_gap56.
      008681                        997 shp11:
      008681 BE 06            [ 2]  998     ldw     x, *m_p+1               ; (p >> 8) low16
      008683 B6 05            [ 1]  999     ld      a, *m_p                 ; (p >> 8) high8
      008685 44               [ 1] 1000     srl     a
      008686 56               [ 2] 1001     rrcw    x
      008687 44               [ 1] 1002     srl     a
      008688 56               [ 2] 1003     rrcw    x
      008689 44               [ 1] 1004     srl     a
      00868A 56               [ 2] 1005     rrcw    x
      00868B 81               [ 4] 1006     ret
                                   1007 
                                   1008 ; ---------------------------------------------------------------- seed
                                   1009 ; P1 endpoint seed: first-rise / last-fall brackets pin K and tau.
                                   1010 ; np reuses r_melo, flm r_mehi, r0m r_de (refine scratch, disjoint use).
      00868C                       1011 _seed:
      00868C 5F               [ 1] 1012     clrw    x
      00868D BF 44            [ 2] 1013     ldw     *r_melo, x              ; np = 0
      00868F CD 91 9F         [ 4] 1014     call    _scan_init
      008692                       1015 00100$:
      008692 CD 91 BB         [ 4] 1016     call    _scan_next
      008695 4D               [ 1] 1017     tnz     a
      008696 27 1F            [ 1] 1018     jreq    00104$
      008698 CE 00 B2         [ 2] 1019     ldw     x, _scan_fa             ; flm = (fa + fb) >> 1 (every pulse)
      00869B 72 BB 00 B4      [ 2] 1020     addw    x, _scan_fb
      00869F 54               [ 2] 1021     srlw    x
      0086A0 BF 46            [ 2] 1022     ldw     *r_mehi, x
      0086A2 BE 44            [ 2] 1023     ldw     x, *r_melo
      0086A4 26 0A            [ 1] 1024     jrne    00102$
      0086A6 CE 00 AE         [ 2] 1025     ldw     x, _scan_ra             ; first pulse: r0m = (ra + rb) >> 1
      0086A9 72 BB 00 B0      [ 2] 1026     addw    x, _scan_rb
      0086AD 54               [ 2] 1027     srlw    x
      0086AE BF 48            [ 2] 1028     ldw     *r_de, x
      0086B0                       1029 00102$:
      0086B0 BE 44            [ 2] 1030     ldw     x, *r_melo
      0086B2 5C               [ 1] 1031     incw    x
      0086B3 BF 44            [ 2] 1032     ldw     *r_melo, x
      0086B5 20 DB            [ 2] 1033     jra     00100$
      0086B7                       1034 00104$:
      0086B7 BE 44            [ 2] 1035     ldw     x, *r_melo              ; np < 8 -> fail
      0086B9 A3 00 08         [ 2] 1036     cpw     x, #8
      0086BC 25 50            [ 1] 1037     jrc     00109$
      0086BE BE 46            [ 2] 1038     ldw     x, *r_mehi              ; flm <= r0m -> fail
      0086C0 72 B0 00 48      [ 2] 1039     subw    x, r_de
      0086C4 25 48            [ 1] 1040     jrc     00109$
      0086C6 27 46            [ 1] 1041     jreq    00109$
      0086C8 BF 2A            [ 2] 1042     ldw     *m_d+2, x               ; K = g_Wu11 / (flm - r0m)
      0086CA 5F               [ 1] 1043     clrw    x
      0086CB BF 28            [ 2] 1044     ldw     *m_d, x
      0086CD CE 80 9F         [ 2] 1045     ldw     x, _g_Wu11
      0086D0 BF 24            [ 2] 1046     ldw     *m_n, x
      0086D2 CE 80 A1         [ 2] 1047     ldw     x, _g_Wu11+2
      0086D5 BF 26            [ 2] 1048     ldw     *m_n+2, x
      0086D7 CD 83 98         [ 4] 1049     call    udiv32
      0086DA BE 24            [ 2] 1050     ldw     x, *m_n                 ; K_MIN <= K <= K_MAX else fail
      0086DC 26 30            [ 1] 1051     jrne    00109$
      0086DE BE 26            [ 2] 1052     ldw     x, *m_n+2
      0086E0 A3 9C 40         [ 2] 1053     cpw     x, #40000               ; RELAXATION A: v2.3 window
      0086E3 25 29            [ 1] 1054     jrc     00109$
      0086E5 A3 FA 01         [ 2] 1055     cpw     x, #64001               ; (was 46000 .. 60000)
      0086E8 24 24            [ 1] 1056     jrnc    00109$
      0086EA CF 00 F3         [ 2] 1057     ldw     _g_K, x
      0086ED BF 01            [ 2] 1058     ldw     *m_a, x                 ; tau = 512 - ((r0m * K) >> 11)
      0086EF BE 48            [ 2] 1059     ldw     x, *r_de
      0086F1 BF 03            [ 2] 1060     ldw     *m_b, x
      0086F3 CD 81 EB         [ 4] 1061     call    mul16
                                   1062     ; RELAXATION A hardening: tau is an s16 by contract, and the WIDE
                                   1063     ; window makes a late-first-rise / short-span capture reachable where
                                   1064     ; 512 - ((r0m*K) >> 11) leaves s16.  The Python reference ASSERTS
                                   1065     ; there; C and asm would silently wrap.  Refusing R1 instead keeps
                                   1066     ; all three implementations bit-exact by construction.
                                   1067     ; (p >> 11) must be <= 512 + 32767 = 33279, which also forces its
                                   1068     ; high word to 0 -- shp11 returns only the low word, so test the
                                   1069     ; high half of the product first: p >> 27 != 0 fails immediately.
      0086F6 B6 05            [ 1] 1070     ld      a, *m_p                 ; p bits 31..24
      0086F8 A4 F8            [ 1] 1071     and     a, #0xF8                ; bits 31..27 -> nonzero means > 2^27
      0086FA 26 12            [ 1] 1072     jrne    00109$
      0086FC CD 86 81         [ 4] 1073     call    shp11
      0086FF A3 82 00         [ 2] 1074     cpw     x, #33280
      008702 24 0A            [ 1] 1075     jrnc    00109$
      008704 50               [ 2] 1076     negw    x
      008705 1C 02 00         [ 2] 1077     addw    x, #512
      008708 CF 00 F5         [ 2] 1078     ldw     _g_tau, x
      00870B A6 01            [ 1] 1079     ld      a, #1
      00870D 81               [ 4] 1080     ret
      00870E                       1081 00109$:
      00870E 4F               [ 1] 1082     clr     a
      00870F 81               [ 4] 1083     ret
                                   1084 
                                   1085 ; ---------------------------------------------------------- dec_eps_centi
                                   1086 ; ((K_NOM - dec_info.K) * 10000) / dec_info.K, s16.  dec_info.K is at
                                   1087 ; offset 9 (decode.h layout: 5 u8 fields + n_weak + n_tied before it).
      008710                       1088 _dec_eps_centi:
      008710 AE CC CD         [ 2] 1089     ldw     x, #52429
      008713 72 B0 00 E5      [ 2] 1090     subw    x, _dec_info+9
      008717 3F 5C            [ 1] 1091     clr     *r_sgn
      008719 5D               [ 2] 1092     tnzw    x
      00871A 2A 05            [ 1] 1093     jrpl    00110$
      00871C 50               [ 2] 1094     negw    x
      00871D 35 01 00 5C      [ 1] 1095     mov     r_sgn, #1
      008721                       1096 00110$:
      008721 BF 01            [ 2] 1097     ldw     *m_a, x
      008723 AE 27 10         [ 2] 1098     ldw     x, #10000
      008726 BF 03            [ 2] 1099     ldw     *m_b, x
      008728 CD 81 EB         [ 4] 1100     call    mul16               ; <= 75.7M
      00872B BE 05            [ 2] 1101     ldw     x, *m_p
      00872D BF 24            [ 2] 1102     ldw     *m_n, x
      00872F BE 07            [ 2] 1103     ldw     x, *m_p+2
      008731 BF 26            [ 2] 1104     ldw     *m_n+2, x
      008733 5F               [ 1] 1105     clrw    x
      008734 BF 28            [ 2] 1106     ldw     *m_d, x
      008736 BE E5            [ 2] 1107     ldw     x, *_dec_info+9
      008738 BF 2A            [ 2] 1108     ldw     *m_d+2, x
      00873A CD 83 98         [ 4] 1109     call    udiv32
      00873D BE 26            [ 2] 1110     ldw     x, *m_n+2
      00873F 3D 5C            [ 1] 1111     tnz     *r_sgn
      008741 27 01            [ 1] 1112     jreq    00111$
      008743 50               [ 2] 1113     negw    x
      008744                       1114 00111$:
      008744 81               [ 4] 1115     ret
                                   1116 
                                   1117 ; ---------------------------------------------------------- set_gap56
                                   1118 ; c_gap56[0] = (6*K)>>11, c_gap56[1] = (5*K)>>11 (both <= 175)
      008745                       1119 _set_gap56:
      008745 A6 06            [ 1] 1120     ld      a, #6
      008747 CD 87 54         [ 4] 1121     call    gap1
      00874A BF D8            [ 2] 1122     ldw     *zgap, x
      00874C A6 05            [ 1] 1123     ld      a, #5
      00874E CD 87 54         [ 4] 1124     call    gap1
      008751 BF DA            [ 2] 1125     ldw     *zgap+2, x
      008753 81               [ 4] 1126     ret
      008754                       1127 gap1:
      008754 5F               [ 1] 1128     clrw    x
      008755 97               [ 1] 1129     ld      xl, a
      008756 BF 01            [ 2] 1130     ldw     *m_a, x
      008758 CE 00 F3         [ 2] 1131     ldw     x, _g_K
      00875B BF 03            [ 2] 1132     ldw     *m_b, x
      00875D CD 81 EB         [ 4] 1133     call    mul16
      008760 CD 86 81         [ 4] 1134     call    shp11
      008763 81               [ 4] 1135     ret
                                   1136 
                                   1137 ; ======================================================================
                                   1138 ; P4 decision cluster: known_bit / a_bounds / hinge / argmin / decide /
                                   1139 ; cand_insert / decide_pass.  Replaces ~1470 B of SDCC output.
                                   1140 ; The per-bit margin scan uses an exactly-equivalent prefix-min (online)
                                   1141 ; + suffix-min (precomputed d_sm[]) formulation of the C's inner loops:
                                   1142 ;   c0m(off) = min costs[a in lo..min(off,hi)]   (empty -> 0xFFFF)
                                   1143 ;   c1m(off) = min costs[a in max(lo,off+1)..hi] (empty -> 0xFFFF)
                                   1144 ; identical values, O(L+W) instead of O(L*W).
                                   1145 ; ======================================================================
                                   1146 
                                   1147     .globl _decide_pass
                                   1148     .globl _known_bit
                                   1149     .globl _a_bounds_sg
                                   1150     .globl _g_sg
                                   1151     .globl _dq_amin
                                   1152     .globl _dq_amax
                                   1153     .globl _g_NBmHT
                                   1154     .globl _g_PPHI
                                   1155     .globl _g_ND8
                                   1156 
                                   1157     .globl _ov
                                   1158     ; decision-pass state the C pipeline tail reads (see the v2.3 note
                                   1159     ; where the hand-assembled chase used to be)
                                   1160     .globl _v_cand_t
                                   1161     .globl _v_cand_m
                                   1162     .globl _v_ncand
                                   1163     .globl _v_nweak
                                   1164     .globl _v_ndw
                                   1165     .globl _v_ntied
                                   1166     .globl _v_chkconf
                                   1167     .globl _d_infeas
                                   1168     .globl _d_laberr
                                   1169     .globl _d_nseg
                                   1170 
                                   1171     .area CODE
                                   1172 
                                   1173 ; -------------------------------------------------------------- known_bit
                                   1174 ; X = t -> A = 0 / 1 / 0xFF(-1).  C-ABI compatible (calibrate calls it).
                                   1175 ; v2.3 markers are 3+3: 24 header bits, 24 trailer bits.  The template
                                   1176 ; comes from HTR -- the BIT-REVERSED marker bytes the pipeline tail's
                                   1177 ; violation popcount also uses: wire bit (7-(t&7)) of the plain byte IS
                                   1178 ; bit (t&7) of the reversed one, so this shifts RIGHT where the old
                                   1179 ; MSB-first HT table shifted left, and ONE 6-byte table serves both.
      008764                       1180 _known_bit:
      008764 A3 00 18         [ 2] 1181     cpw     x, #24
      008767 25 09            [ 1] 1182     jrc     00130$              ; header bits 0..23
      008769 72 B0 80 A3      [ 2] 1183     subw    x, _g_NBmHT
      00876D 25 17            [ 1] 1184     jrc     00132$              ; interior
      00876F 1C 00 18         [ 2] 1185     addw    x, #24              ; trailer bits at HT[24..47]
      008772                       1186 00130$:
      008772 9F               [ 1] 1187     ld      a, xl
      008773 A4 07            [ 1] 1188     and     a, #7
      008775 4C               [ 1] 1189     inc     a
      008776 B7 0D            [ 1] 1190     ld      *m_s, a                 ; shift count = (t&7)+1
      008778 54               [ 2] 1191     srlw    x
      008779 54               [ 2] 1192     srlw    x
      00877A 54               [ 2] 1193     srlw    x
      00877B D6 96 6C         [ 1] 1194     ld      a, (HTR, x)
      00877E                       1195 00131$:
      00877E 44               [ 1] 1196     srl     a
      00877F 3A 0D            [ 1] 1197     dec     *m_s
      008781 26 FB            [ 1] 1198     jrne    00131$
      008783 4F               [ 1] 1199     clr     a
      008784 49               [ 1] 1200     rlc     a                       ; A = the bit
      008785 81               [ 4] 1201     ret
      008786                       1202 00132$:
      008786 A6 FF            [ 1] 1203     ld      a, #0xFF
      008788 81               [ 4] 1204     ret
                                   1205 
                                   1206 ; ------------------------------------------------------------ a_bounds_sg
                                   1207 ; a_bounds over g_sg -> dq_amin/dq_amax (C calibrate uses this too).
      008789                       1208 _a_bounds_sg:
      008789 5F               [ 1] 1209     clrw    x
      00878A BF 66            [ 2] 1210     ldw     *_dq_amin, x
      00878C BE 5F            [ 2] 1211     ldw     x, *_g_sg+2
      00878E 72 B0 00 5D      [ 2] 1212     subw    x, _g_sg
      008792 BF 68            [ 2] 1213     ldw     *_dq_amax, x
      008794 BE 5F            [ 2] 1214     ldw     x, *_g_sg+2             ; e = min(k1, NB)
      008796 C3 80 95         [ 2] 1215     cpw     x, _g_NB
      008799 25 03            [ 1] 1216     jrc     00140$
      00879B CE 80 95         [ 2] 1217     ldw     x, _g_NB
      00879E                       1218 00140$:
      00879E BF 84            [ 2] 1219     ldw     *m_e, x
      0087A0 BE 5D            [ 2] 1220     ldw     x, *_g_sg
      0087A2 BF 86            [ 2] 1221     ldw     *m_t, x
      0087A4                       1222 00141$:
      0087A4 BE 86            [ 2] 1223     ldw     x, *m_t
      0087A6 B3 84            [ 2] 1224     cpw     x, *m_e
      0087A8 24 2C            [ 1] 1225     jrnc    00149$
      0087AA CD 87 64         [ 4] 1226     call    _known_bit
      0087AD A1 01            [ 1] 1227     cp      a, #1
      0087AF 26 0F            [ 1] 1228     jrne    00142$
      0087B1 BE 86            [ 2] 1229     ldw     x, *m_t                 ; kb == 1: amin = max(amin, t-k0+1)
      0087B3 72 B0 00 5D      [ 2] 1230     subw    x, _g_sg
      0087B7 5C               [ 1] 1231     incw    x
      0087B8 B3 66            [ 2] 1232     cpw     x, *_dq_amin
      0087BA 23 13            [ 2] 1233     jrule   00144$
      0087BC BF 66            [ 2] 1234     ldw     *_dq_amin, x
      0087BE 20 0F            [ 2] 1235     jra     00144$
      0087C0                       1236 00142$:
      0087C0 4D               [ 1] 1237     tnz     a
      0087C1 26 0C            [ 1] 1238     jrne    00144$              ; -1: nothing
      0087C3 BE 86            [ 2] 1239     ldw     x, *m_t                 ; kb == 0: amax = min(amax, t-k0)
      0087C5 72 B0 00 5D      [ 2] 1240     subw    x, _g_sg
      0087C9 B3 68            [ 2] 1241     cpw     x, *_dq_amax
      0087CB 24 02            [ 1] 1242     jrnc    00144$
      0087CD BF 68            [ 2] 1243     ldw     *_dq_amax, x
      0087CF                       1244 00144$:
      0087CF BE 86            [ 2] 1245     ldw     x, *m_t
      0087D1 5C               [ 1] 1246     incw    x
      0087D2 BF 86            [ 2] 1247     ldw     *m_t, x
      0087D4 20 CE            [ 2] 1248     jra     00141$
      0087D6                       1249 00149$:
      0087D6 81               [ 4] 1250     ret
                                   1251 
                                   1252 ; ---------------------------------------------------------------- hcost
                                   1253 ; X = h -> X = hinge(u, v, h) = max(0, u-h, h-v); g_sg.u/.v.  Keeps m_h.
      0087D7                       1254 hcost:
      0087D7 BF 7A            [ 2] 1255     ldw     *m_h, x
      0087D9 BE 61            [ 2] 1256     ldw     x, *_g_sg+4
      0087DB 72 B0 00 7A      [ 2] 1257     subw    x, m_h              ; u - h (s16)
      0087DF 2C 01            [ 1] 1258     jrsgt   00150$
      0087E1 5F               [ 1] 1259     clrw    x
      0087E2                       1260 00150$:
      0087E2 90 93            [ 1] 1261     ldw     y, x                    ; Y = g so far
      0087E4 BE 7A            [ 2] 1262     ldw     x, *m_h
      0087E6 72 B0 00 63      [ 2] 1263     subw    x, _g_sg+6          ; h - v (s16)
      0087EA 2C 02            [ 1] 1264     jrsgt   00151$
      0087EC 93               [ 1] 1265     ldw     x, y
      0087ED 81               [ 4] 1266     ret
      0087EE                       1267 00151$:
      0087EE 90 89            [ 2] 1268     pushw   y                   ; g
      0087F0 13 01            [ 2] 1269     cpw     x, (1, sp)
      0087F2 90 85            [ 2] 1270     popw    y
      0087F4 22 01            [ 1] 1271     jrugt   00152$
      0087F6 93               [ 1] 1272     ldw     x, y
      0087F7                       1273 00152$:
      0087F7 81               [ 4] 1274     ret
                                   1275 
                                   1276 ; ----------------------------------------------------------------- itst
                                   1277 ; A = (u < m_h && m_h <= v), signed.
      0087F8                       1278 itst:
      0087F8 BE 61            [ 2] 1279     ldw     x, *_g_sg+4
      0087FA B3 7A            [ 2] 1280     cpw     x, *m_h
      0087FC 2F 02            [ 1] 1281     jrslt   00153$
      0087FE 4F               [ 1] 1282     clr     a
      0087FF 81               [ 4] 1283     ret
      008800                       1284 00153$:
      008800 BE 7A            [ 2] 1285     ldw     x, *m_h
      008802 B3 63            [ 2] 1286     cpw     x, *_g_sg+6
      008804 2D 02            [ 1] 1287     jrsle   00154$
      008806 4F               [ 1] 1288     clr     a
      008807 81               [ 4] 1289     ret
      008808                       1290 00154$:
      008808 A6 01            [ 1] 1291     ld      a, #1
      00880A 81               [ 4] 1292     ret
                                   1293 
                                   1294 ; --------------------------------------------------------------- setbit
                                   1295 ; dq_inter |= 1 << m_ai
      00880B                       1296 setbit:
      00880B B6 91            [ 1] 1297     ld      a, *m_ai
      00880D A4 07            [ 1] 1298     and     a, #7
      00880F B7 0D            [ 1] 1299     ld      *m_s, a
      008811 A6 01            [ 1] 1300     ld      a, #1
      008813 3D 0D            [ 1] 1301     tnz     *m_s
      008815 27 05            [ 1] 1302     jreq    00156$
      008817                       1303 00155$:
      008817 48               [ 1] 1304     sll     a
      008818 3A 0D            [ 1] 1305     dec     *m_s
      00881A 26 FB            [ 1] 1306     jrne    00155$
      00881C                       1307 00156$:
      00881C 88               [ 1] 1308     push    a
      00881D B6 91            [ 1] 1309     ld      a, *m_ai
      00881F A1 08            [ 1] 1310     cp      a, #8
      008821 84               [ 1] 1311     pop     a
      008822 25 05            [ 1] 1312     jrc     00157$
      008824 BA 6A            [ 1] 1313     or      a, *dq_inter            ; bits 8..15 live in the high byte
      008826 B7 6A            [ 1] 1314     ld      *dq_inter, a
      008828 81               [ 4] 1315     ret
      008829                       1316 00157$:
      008829 BA 6B            [ 1] 1317     or      a, *dq_inter+1
      00882B B7 6B            [ 1] 1318     ld      *dq_inter+1, a
      00882D 81               [ 4] 1319     ret
                                   1320 
                                   1321 ; --------------------------------------------------------------- getbit
                                   1322 ; A = (dq_inter >> m_ai2) & 1
      00882E                       1323 getbit:
      00882E B6 92            [ 1] 1324     ld      a, *m_ai2
      008830 A4 07            [ 1] 1325     and     a, #7
      008832 4C               [ 1] 1326     inc     a
      008833 B7 0D            [ 1] 1327     ld      *m_s, a
      008835 B6 92            [ 1] 1328     ld      a, *m_ai2
      008837 A1 08            [ 1] 1329     cp      a, #8
      008839 25 04            [ 1] 1330     jrc     00158$
      00883B B6 6A            [ 1] 1331     ld      a, *dq_inter
      00883D 20 02            [ 2] 1332     jra     00159$
      00883F                       1333 00158$:
      00883F B6 6B            [ 1] 1334     ld      a, *dq_inter+1
      008841                       1335 00159$:
      008841 44               [ 1] 1336     srl     a
      008842 3A 0D            [ 1] 1337     dec     *m_s
      008844 26 FB            [ 1] 1338     jrne    00159$
      008846 4F               [ 1] 1339     clr     a
      008847 49               [ 1] 1340     rlc     a
      008848 81               [ 4] 1341     ret
                                   1342 
                                   1343 ; --------------------------------------------------------------- argmin
                                   1344 ; over [m_alo..m_ahi]: (cost, interior-preferred-on-tie, smallest a).
                                   1345 ; -> X = best.  Mirrors C argmin_ab exactly (bc=0xFFFF, bi=1 initial).
      008849                       1346 argmin:
      008849 AE FF FF         [ 2] 1347     ldw     x, #0xFFFF
      00884C BF 7E            [ 2] 1348     ldw     *m_c, x
      00884E 35 01 00 90      [ 1] 1349     mov     m_it, #1
      008852 B6 93            [ 1] 1350     ld      a, *m_alo
      008854 B7 95            [ 1] 1351     ld      *m_best, a
      008856 B7 92            [ 1] 1352     ld      *m_ai2, a
      008858                       1353 00160$:
      008858 B6 92            [ 1] 1354     ld      a, *m_ai2
      00885A 48               [ 1] 1355     sll     a
      00885B 5F               [ 1] 1356     clrw    x
      00885C 97               [ 1] 1357     ld      xl, a
      00885D DE 01 A8         [ 2] 1358     ldw     x, (_d_costs, x)
      008860 B3 7E            [ 2] 1359     cpw     x, *m_c
      008862 25 16            [ 1] 1360     jrc     00161$              ; strictly better
      008864 26 1F            [ 1] 1361     jrne    00163$              ; worse
      008866 CD 88 2E         [ 4] 1362     call    getbit              ; equal: take iff it && !bi
      008869 4D               [ 1] 1363     tnz     a
      00886A 27 19            [ 1] 1364     jreq    00163$
      00886C 3D 90            [ 1] 1365     tnz     *m_it
      00886E 26 15            [ 1] 1366     jrne    00163$
      008870 35 01 00 90      [ 1] 1367     mov     m_it, #1
      008874 B6 92            [ 1] 1368     ld      a, *m_ai2
      008876 B7 95            [ 1] 1369     ld      *m_best, a
      008878 20 0B            [ 2] 1370     jra     00163$
      00887A                       1371 00161$:
      00887A BF 7E            [ 2] 1372     ldw     *m_c, x
      00887C CD 88 2E         [ 4] 1373     call    getbit
      00887F B7 90            [ 1] 1374     ld      *m_it, a
      008881 B6 92            [ 1] 1375     ld      a, *m_ai2
      008883 B7 95            [ 1] 1376     ld      *m_best, a
      008885                       1377 00163$:
      008885 B6 92            [ 1] 1378     ld      a, *m_ai2
      008887 4C               [ 1] 1379     inc     a
      008888 B7 92            [ 1] 1380     ld      *m_ai2, a
      00888A B1 94            [ 1] 1381     cp      a, *m_ahi
      00888C 23 CA            [ 2] 1382     jrule   00160$
      00888E 5F               [ 1] 1383     clrw    x
      00888F B6 95            [ 1] 1384     ld      a, *m_best
      008891 97               [ 1] 1385     ld      xl, a
      008892 81               [ 4] 1386     ret
                                   1387 
                                   1388 ; --------------------------------------------------------------- addd56
                                   1389 ; m_h0 += sext(A); m_h1 += sext(A)
      008893                       1390 addd56:
      008893 5F               [ 1] 1391     clrw    x
      008894 97               [ 1] 1392     ld      xl, a
      008895 4D               [ 1] 1393     tnz     a
      008896 2A 03            [ 1] 1394     jrpl    00165$
      008898 1C FF 00         [ 2] 1395     addw    x, #0xFF00
      00889B                       1396 00165$:
      00889B BF 7A            [ 2] 1397     ldw     *m_h, x
      00889D BE 76            [ 2] 1398     ldw     x, *m_h0
      00889F 72 BB 00 7A      [ 2] 1399     addw    x, m_h
      0088A3 BF 76            [ 2] 1400     ldw     *m_h0, x
      0088A5 BE 78            [ 2] 1401     ldw     x, *m_h1
      0088A7 72 BB 00 7A      [ 2] 1402     addw    x, m_h
      0088AB BF 78            [ 2] 1403     ldw     *m_h1, x
      0088AD 81               [ 4] 1404     ret
                                   1405 
                                   1406 ; ---------------------------------------------------------------- decide
                                   1407 ; g_sg -> d_costs[0..acap], dq_inter, dq_acap/afree/lo/hi/ahat.
      0088AE                       1408 dq_decide:
      0088AE BE 5F            [ 2] 1409     ldw     x, *_g_sg+2
      0088B0 72 B0 00 5D      [ 2] 1410     subw    x, _g_sg
      0088B4 BF 7C            [ 2] 1411     ldw     *m_L, x                 ; L = k1-k0 (>= 1)
      0088B6 A3 00 10         [ 2] 1412     cpw     x, #16
      0088B9 25 03            [ 1] 1413     jrc     00170$
      0088BB AE 00 0F         [ 2] 1414     ldw     x, #15
      0088BE                       1415 00170$:
      0088BE BF 6C            [ 2] 1416     ldw     *dq_acap, x
      0088C0 BE D2            [ 2] 1417     ldw     x, *zh0c
      0088C2 BF 76            [ 2] 1418     ldw     *m_h0, x
      0088C4 BE D4            [ 2] 1419     ldw     x, *zh1c
      0088C6 BF 78            [ 2] 1420     ldw     *m_h1, x
      0088C8 B6 65            [ 1] 1421     ld      a, *_g_sg+8             ; fam
      0088CA A1 05            [ 1] 1422     cp      a, #5
      0088CC 26 07            [ 1] 1423     jrne    00171$
      0088CE B6 D6            [ 1] 1424     ld      a, *zd56
      0088D0 CD 88 93         [ 4] 1425     call    addd56
      0088D3 20 09            [ 2] 1426     jra     00172$
      0088D5                       1427 00171$:
      0088D5 A1 06            [ 1] 1428     cp      a, #6
      0088D7 26 05            [ 1] 1429     jrne    00172$
      0088D9 B6 D7            [ 1] 1430     ld      a, *zd56+1
      0088DB CD 88 93         [ 4] 1431     call    addd56
      0088DE                       1432 00172$:
      0088DE 5F               [ 1] 1433     clrw    x
      0088DF BF 6A            [ 2] 1434     ldw     *dq_inter, x
      0088E1 3F 91            [ 1] 1435     clr     *m_ai
      0088E3                       1436 00173$:                         ; per hypothesis a
      0088E3 B6 91            [ 1] 1437     ld      a, *m_ai
      0088E5 26 0E            [ 1] 1438     jrne    00174$
      0088E7 BE 76            [ 2] 1439     ldw     x, *m_h0                ; a == 0
      0088E9 CD 87 D7         [ 4] 1440     call    hcost
      0088EC BF 7E            [ 2] 1441     ldw     *m_c, x
      0088EE CD 87 F8         [ 4] 1442     call    itst
      0088F1 B7 90            [ 1] 1443     ld      *m_it, a
      0088F3 20 38            [ 2] 1444     jra     00177$
      0088F5                       1445 00174$:
      0088F5 4A               [ 1] 1446     dec     a                       ; a >= 1: h = (a-1)*512 + h1e
      0088F6 48               [ 1] 1447     sll     a
      0088F7 5F               [ 1] 1448     clrw    x
      0088F8 95               [ 1] 1449     ld      xh, a
      0088F9 72 BB 00 78      [ 2] 1450     addw    x, m_h1
      0088FD CD 87 D7         [ 4] 1451     call    hcost
      008900 BF 7E            [ 2] 1452     ldw     *m_c, x
      008902 CD 87 F8         [ 4] 1453     call    itst
      008905 B7 90            [ 1] 1454     ld      *m_it, a
      008907 B6 91            [ 1] 1455     ld      a, *m_ai                ; if a < L: h2 = a*512 + h0e
      008909 5F               [ 1] 1456     clrw    x
      00890A 97               [ 1] 1457     ld      xl, a
      00890B B3 7C            [ 2] 1458     cpw     x, *m_L
      00890D 24 1E            [ 1] 1459     jrnc    00177$
      00890F B6 91            [ 1] 1460     ld      a, *m_ai
      008911 48               [ 1] 1461     sll     a
      008912 5F               [ 1] 1462     clrw    x
      008913 95               [ 1] 1463     ld      xh, a
      008914 72 BB 00 76      [ 2] 1464     addw    x, m_h0
      008918 CD 87 D7         [ 4] 1465     call    hcost
      00891B 89               [ 2] 1466     pushw   x
      00891C CD 87 F8         [ 4] 1467     call    itst
      00891F 4D               [ 1] 1468     tnz     a
      008920 27 04            [ 1] 1469     jreq    00175$
      008922 35 01 00 90      [ 1] 1470     mov     m_it, #1
      008926                       1471 00175$:
      008926 85               [ 2] 1472     popw    x
      008927 B3 7E            [ 2] 1473     cpw     x, *m_c
      008929 24 02            [ 1] 1474     jrnc    00177$
      00892B BF 7E            [ 2] 1475     ldw     *m_c, x
      00892D                       1476 00177$:                         ; store costs[a] + interior bit
      00892D B6 91            [ 1] 1477     ld      a, *m_ai
      00892F 48               [ 1] 1478     sll     a
      008930 5F               [ 1] 1479     clrw    x
      008931 97               [ 1] 1480     ld      xl, a
      008932 90 BE 7E         [ 2] 1481     ldw     y, *m_c
      008935 DF 01 A8         [ 2] 1482     ldw     (_d_costs, x), y
      008938 3D 90            [ 1] 1483     tnz     *m_it
      00893A 27 03            [ 1] 1484     jreq    00178$
      00893C CD 88 0B         [ 4] 1485     call    setbit
      00893F                       1486 00178$:
      00893F B6 91            [ 1] 1487     ld      a, *m_ai
      008941 4C               [ 1] 1488     inc     a
      008942 B7 91            [ 1] 1489     ld      *m_ai, a
      008944 B1 6D            [ 1] 1490     cp      a, *dq_acap+1
      008946 23 9B            [ 2] 1491     jrule   00173$
                                   1492     ; a_free = argmin(0, acap)
      008948 3F 93            [ 1] 1493     clr     *m_alo
      00894A B6 6D            [ 1] 1494     ld      a, *dq_acap+1
      00894C B7 94            [ 1] 1495     ld      *m_ahi, a
      00894E CD 88 49         [ 4] 1496     call    argmin
      008951 BF 74            [ 2] 1497     ldw     *dq_afree, x
      008953 CD 87 89         [ 4] 1498     call    _a_bounds_sg
      008956 BE 66            [ 2] 1499     ldw     x, *_dq_amin            ; lo = amin (>= 0)
      008958 BF 6E            [ 2] 1500     ldw     *dq_lo, x
      00895A BE 68            [ 2] 1501     ldw     x, *_dq_amax            ; hi = min(amax, acap)
      00895C B3 6C            [ 2] 1502     cpw     x, *dq_acap
      00895E 25 02            [ 1] 1503     jrc     00179$
      008960 BE 6C            [ 2] 1504     ldw     x, *dq_acap
      008962                       1505 00179$:
      008962 BF 70            [ 2] 1506     ldw     *dq_hi, x
      008964 BE 6E            [ 2] 1507     ldw     x, *dq_lo
      008966 B3 70            [ 2] 1508     cpw     x, *dq_hi
      008968 23 07            [ 2] 1509     jrule   00180$
      00896A 5F               [ 1] 1510     clrw    x                   ; lo > hi: full range
      00896B BF 6E            [ 2] 1511     ldw     *dq_lo, x
      00896D BE 6C            [ 2] 1512     ldw     x, *dq_acap
      00896F BF 70            [ 2] 1513     ldw     *dq_hi, x
      008971                       1514 00180$:
      008971 B6 6F            [ 1] 1515     ld      a, *dq_lo+1
      008973 B7 93            [ 1] 1516     ld      *m_alo, a
      008975 B6 71            [ 1] 1517     ld      a, *dq_hi+1
      008977 B7 94            [ 1] 1518     ld      *m_ahi, a
      008979 CD 88 49         [ 4] 1519     call    argmin
      00897C BF 72            [ 2] 1520     ldw     *dq_ahat, x
      00897E 81               [ 4] 1521     ret
                                   1522 
                                   1523 ; ------------------------------------------------------------ cand_insert
                                   1524 ; X = payload' bit index k, A = margin m: sorted top-5 insert
                                   1525 ; (key: margin then index, ascending) -- exactly C cand_insert.
      00897F                       1526 candi:
      00897F B7 9B            [ 1] 1527     ld      *m_m, a
      008981 BF 8A            [ 2] 1528     ldw     *m_k, x
      008983 B6 A2            [ 1] 1529     ld      a, *_v_ncand
      008985 B7 99            [ 1] 1530     ld      *m_i, a
      008987                       1531 00185$:                         ; while (i > 0 && cand_m[i-1] > m) i--
      008987 3D 99            [ 1] 1532     tnz     *m_i
      008989 27 10            [ 1] 1533     jreq    00186$
      00898B B6 99            [ 1] 1534     ld      a, *m_i
      00898D 4A               [ 1] 1535     dec     a
      00898E 5F               [ 1] 1536     clrw    x
      00898F 97               [ 1] 1537     ld      xl, a
      008990 D6 02 12         [ 1] 1538     ld      a, (_v_cand_m, x)
      008993 B1 9B            [ 1] 1539     cp      a, *m_m
      008995 23 04            [ 2] 1540     jrule   00186$
      008997 3A 99            [ 1] 1541     dec     *m_i
      008999 20 EC            [ 2] 1542     jra     00185$
      00899B                       1543 00186$:
      00899B B6 99            [ 1] 1544     ld      a, *m_i
      00899D A1 0B            [ 1] 1545     cp      a, #11                  ; A_MAX = 11 (RELAXATION C)
      00899F 25 01            [ 1] 1546     jrc     00187$
      0089A1 81               [ 4] 1547     ret                         ; list full below this margin
      0089A2                       1548 00187$:
      0089A2 B6 A2            [ 1] 1549     ld      a, *_v_ncand             ; j = min(ncand, A_MAX-1)
      0089A4 A1 0B            [ 1] 1550     cp      a, #11
      0089A6 25 02            [ 1] 1551     jrc     00188$
      0089A8 A6 0A            [ 1] 1552     ld      a, #10
      0089AA                       1553 00188$:
      0089AA B7 9A            [ 1] 1554     ld      *m_j, a
      0089AC                       1555 00189$:                         ; shift [i..j-1] up
      0089AC B6 9A            [ 1] 1556     ld      a, *m_j
      0089AE B1 99            [ 1] 1557     cp      a, *m_i
      0089B0 23 1D            [ 2] 1558     jrule   00190$
      0089B2 B6 9A            [ 1] 1559     ld      a, *m_j
      0089B4 48               [ 1] 1560     sll     a
      0089B5 5F               [ 1] 1561     clrw    x
      0089B6 97               [ 1] 1562     ld      xl, a
      0089B7 89               [ 2] 1563     pushw   x
      0089B8 DE 01 FA         [ 2] 1564     ldw     x, (_v_cand_t-2, x)
      0089BB 90 93            [ 1] 1565     ldw     y, x
      0089BD 85               [ 2] 1566     popw    x
      0089BE DF 01 FC         [ 2] 1567     ldw     (_v_cand_t, x), y
      0089C1 B6 9A            [ 1] 1568     ld      a, *m_j
      0089C3 5F               [ 1] 1569     clrw    x
      0089C4 97               [ 1] 1570     ld      xl, a
      0089C5 D6 02 11         [ 1] 1571     ld      a, (_v_cand_m-1, x)
      0089C8 D7 02 12         [ 1] 1572     ld      (_v_cand_m, x), a
      0089CB 3A 9A            [ 1] 1573     dec     *m_j
      0089CD 20 DD            [ 2] 1574     jra     00189$
      0089CF                       1575 00190$:
      0089CF B6 99            [ 1] 1576     ld      a, *m_i
      0089D1 48               [ 1] 1577     sll     a
      0089D2 5F               [ 1] 1578     clrw    x
      0089D3 97               [ 1] 1579     ld      xl, a
      0089D4 90 BE 8A         [ 2] 1580     ldw     y, *m_k
      0089D7 DF 01 FC         [ 2] 1581     ldw     (_v_cand_t, x), y
      0089DA B6 99            [ 1] 1582     ld      a, *m_i
      0089DC 5F               [ 1] 1583     clrw    x
      0089DD 97               [ 1] 1584     ld      xl, a
      0089DE B6 9B            [ 1] 1585     ld      a, *m_m
      0089E0 D7 02 12         [ 1] 1586     ld      (_v_cand_m, x), a
      0089E3 B6 A2            [ 1] 1587     ld      a, *_v_ncand
      0089E5 A1 0B            [ 1] 1588     cp      a, #11                  ; A_MAX
      0089E7 24 03            [ 1] 1589     jrnc    00191$
      0089E9 4C               [ 1] 1590     inc     a
      0089EA B7 A2            [ 1] 1591     ld      *_v_ncand, a
      0089EC                       1592 00191$:
      0089EC 81               [ 4] 1593     ret
                                   1594 
                                   1595 ; ---------------------------------------------------------------- dwtst
                                   1596 ; SS6.4 DEAD-WINDOW test for the bit at offset m_off inside the current
                                   1597 ; segment -> A = 1 if the bit is a DW candidate, else 0.
                                   1598 ;
                                   1599 ; The bit's DISCRIMINATING INTERVAL is (hb + h0e, hb + h1e] with
                                   1600 ; hb = off * BIT_U; the whole observation is the fall bracket (u, v],
                                   1601 ; whose ends are ADJACENT samples.  With
                                   1602 ;     ga = (hb + h0e) <= u        gb = v < (hb + h1e)
                                   1603 ; ga != gb is the healthy case (exactly one candidate fall position is
                                   1604 ; inside the bracket, i.e. a sample DECIDED the bit) and ga == gb is
                                   1605 ; degenerate -- the bracket inside the window (a transition at NEITHER
                                   1606 ; fitted boundary) or the window inside the bracket (no sample in it).
                                   1607 ;
                                   1608 ; A accumulates +1 for ga and -1 for gb, so A == 0 iff ga == gb, and the
                                   1609 ; routine RETURNS WITH Z SET IFF the bit is a DW candidate (RET does not
                                   1610 ; touch the flags, and LD A,#imm does -- so the early exit is honest).
                                   1611 ; off >= DW_OFF_MAX (64) is not a candidate: hb would leave s16
                                   1612 ; (63*512 + h1e <= 32680 < 32768 is the bound), and it changes nothing
                                   1613 ; because h0e >= 64, so once hb > v the test already answers "healthy" of
                                   1614 ; its own accord.  Y is free here -- the bit loop uses only A and X.
      0089ED                       1615 dwtst:
      0089ED BE 88            [ 2] 1616     ldw     x, *m_off
      0089EF A3 00 40         [ 2] 1617     cpw     x, #64                  ; DW_OFF_MAX
      0089F2 25 03            [ 1] 1618     jrc     00193$
      0089F4 A6 01            [ 1] 1619     ld      a, #1                   ; off >= 64: healthy (Z clear)
      0089F6 81               [ 4] 1620     ret
      0089F7                       1621 00193$:
      0089F7 B6 89            [ 1] 1622     ld      a, *m_off+1             ; off < 64, so hb = off << 9 is
      0089F9 48               [ 1] 1623     sll     a                       ; hb_hi = off*2, hb_lo = 0
      0089FA 95               [ 1] 1624     ld      xh, a
      0089FB 4F               [ 1] 1625     clr     a
      0089FC 97               [ 1] 1626     ld      xl, a                   ; X = hb
      0089FD 90 93            [ 1] 1627     ldw     y, x
      0089FF 72 BB 00 76      [ 2] 1628     addw    x, m_h0
      008A03 4F               [ 1] 1629     clr     a                       ; BEFORE the compare: CLR touches N/Z,
                                   1630                                     ; which the SIGNED branch below reads
      008A04 B3 61            [ 2] 1631     cpw     x, *_g_sg+4             ; u  (short form: _g_sg is ABS zero
                                   1632                                     ; page, so 2 B instead of 3)
      008A06 2C 01            [ 1] 1633     jrsgt   00194$
      008A08 4C               [ 1] 1634     inc     a                       ; ga: (hb + h0e) <= u
      008A09                       1635 00194$:
      008A09 93               [ 1] 1636     ldw     x, y
      008A0A 72 BB 00 78      [ 2] 1637     addw    x, m_h1
      008A0E B3 63            [ 2] 1638     cpw     x, *_g_sg+6             ; v
      008A10 2D 01            [ 1] 1639     jrsle   00195$
      008A12 4A               [ 1] 1640     dec     a                       ; gb: v < (hb + h1e)
      008A13                       1641 00195$:
      008A13 4D               [ 1] 1642     tnz     a                       ; Z iff ga == gb
      008A14 81               [ 4] 1643     ret
                                   1644 
                                   1645 ; ------------------------------------------------------------ decide_pass
      008A15                       1646 _decide_pass:
      008A15 CE 80 95         [ 2] 1647     ldw     x, _g_NB                ; zero d_bits[0..NBB-1] (NBB = NB/8)
      008A18 54               [ 2] 1648     srlw    x
      008A19 54               [ 2] 1649     srlw    x
      008A1A 54               [ 2] 1650     srlw    x
      008A1B                       1651 00200$:
      008A1B 72 4F 00 F6      [ 1] 1652     clr     (_ov-1, x)
      008A1F 5A               [ 2] 1653     decw    x
      008A20 26 F9            [ 1] 1654     jrne    00200$
      008A22 5F               [ 1] 1655     clrw    x
      008A23 BF 9C            [ 2] 1656     ldw     *_d_infeas, x
      008A25 BF 9E            [ 2] 1657     ldw     *_d_laberr, x
      008A27 BF A0            [ 2] 1658     ldw     *_d_nseg, x
      008A29 BF A3            [ 2] 1659     ldw     *_v_nweak, x
      008A2B BF A5            [ 2] 1660     ldw     *_v_ntied, x
      008A2D BF A7            [ 2] 1661     ldw     *_v_ndw, x
      008A2F 3F A2            [ 1] 1662     clr     *_v_ncand
      008A31 AE 00 0C         [ 2] 1663     ldw     x, #12                  ; v_chkconf[6] = 0  (v2.3)
      008A34                       1664 00199$:
      008A34 5A               [ 2] 1665     decw    x
      008A35 72 4F 02 1D      [ 1] 1666     clr     (_v_chkconf, x)
      008A39 26 F9            [ 1] 1667     jrne    00199$
      008A3B AE FF FF         [ 2] 1668     ldw     x, #0xFFFF
      008A3E BF 8C            [ 2] 1669     ldw     *w_tiep, x              ; v_tiepend = -1
      008A40 CD 82 5B         [ 4] 1670     call    _ss_init
      008A43                       1671 00201$:                         ; segment loop
      008A43 AE 00 5D         [ 2] 1672     ldw     x, #_g_sg
      008A46 CD 82 B5         [ 4] 1673     call    _ss_next
      008A49 4D               [ 1] 1674     tnz     a
      008A4A 26 01            [ 1] 1675     jrne    00202$
      008A4C 81               [ 4] 1676     ret
      008A4D                       1677 00202$:
      008A4D BE A0            [ 2] 1678     ldw     x, *_d_nseg
      008A4F 5C               [ 1] 1679     incw    x
      008A50 BF A0            [ 2] 1680     ldw     *_d_nseg, x
      008A52 BE 5D            [ 2] 1681     ldw     x, *_g_sg               ; if (k0 >= NB) continue
      008A54 C3 80 95         [ 2] 1682     cpw     x, _g_NB
      008A57 25 02            [ 1] 1683     jrc     00203$
      008A59 20 E8            [ 2] 1684     jra     00201$
      008A5B                       1685 00203$:
      008A5B CD 88 AE         [ 4] 1686     call    dq_decide
      008A5E B6 73            [ 1] 1687     ld      a, *dq_ahat+1           ; c_hat = costs[ahat]
      008A60 48               [ 1] 1688     sll     a
      008A61 5F               [ 1] 1689     clrw    x
      008A62 97               [ 1] 1690     ld      xl, a
      008A63 DE 01 A8         [ 2] 1691     ldw     x, (_d_costs, x)
      008A66 A3 00 A0         [ 2] 1692     cpw     x, #160
      008A69 23 05            [ 2] 1693     jrule   00204$
      008A6B BE 9C            [ 2] 1694     ldw     x, *_d_infeas
      008A6D 5C               [ 1] 1695     incw    x
      008A6E BF 9C            [ 2] 1696     ldw     *_d_infeas, x
      008A70                       1697 00204$:
      008A70 BE 5F            [ 2] 1698     ldw     x, *_g_sg+2             ; kk1 = min(k1, NB)
      008A72 C3 80 95         [ 2] 1699     cpw     x, _g_NB
      008A75 25 03            [ 1] 1700     jrc     00205$
      008A77 CE 80 95         [ 2] 1701     ldw     x, _g_NB
      008A7A                       1702 00205$:
      008A7A BF 84            [ 2] 1703     ldw     *m_e, x
      008A7C 35 01 00 96      [ 1] 1704     mov     m_ka, #1            ; known_all over [k0, kk1)
      008A80 BE 5D            [ 2] 1705     ldw     x, *_g_sg
      008A82 BF 86            [ 2] 1706     ldw     *m_t, x
      008A84                       1707 00206$:
      008A84 BE 86            [ 2] 1708     ldw     x, *m_t
      008A86 B3 84            [ 2] 1709     cpw     x, *m_e
      008A88 24 11            [ 1] 1710     jrnc    00208$
      008A8A CD 87 64         [ 4] 1711     call    _known_bit
      008A8D 4D               [ 1] 1712     tnz     a
      008A8E 2A 04            [ 1] 1713     jrpl    00207$
      008A90 3F 96            [ 1] 1714     clr     *m_ka
      008A92 20 07            [ 2] 1715     jra     00208$
      008A94                       1716 00207$:
      008A94 BE 86            [ 2] 1717     ldw     x, *m_t
      008A96 5C               [ 1] 1718     incw    x
      008A97 BF 86            [ 2] 1719     ldw     *m_t, x
      008A99 20 E9            [ 2] 1720     jra     00206$
                                   1721     ; SIZE LEVER: ONE pass over a = 0..acap now yields both interior
                                   1722     ; counts -- m_n1 over the WHOLE hypothesis range (the `dead` detector
                                   1723     ; that suppresses a label error inside a dead marker window) and,
                                   1724     ; restricted to [lo, hi], m_best = nins plus m_i0 = ins0 (the tie
                                   1725     ; mark).  The two loops were 60 B; merged they are 49 B, and the
                                   1726     ; values are identical by construction -- the second loop's range is
                                   1727     ; a SUBSET of the first's, and lo/hi are in 0..15 so the low byte of
                                   1728     ; each is the whole comparison (as the old loops already assumed).
      008A9B                       1729 00208$:
      008A9B 35 FF 00 98      [ 1] 1730     mov     m_i0, #0xFF             ; ins0 = none
      008A9F 3F 97            [ 1] 1731     clr     *m_n1                   ; interior over 0..acap  (dead)
      008AA1 3F 95            [ 1] 1732     clr     *m_best                 ; interior over [lo,hi]  (nins)
      008AA3 3F 92            [ 1] 1733     clr     *m_ai2
      008AA5                       1734 00209$:
      008AA5 CD 88 2E         [ 4] 1735     call    getbit
      008AA8 4D               [ 1] 1736     tnz     a
      008AA9 27 18            [ 1] 1737     jreq    00210$
      008AAB 3C 97            [ 1] 1738     inc     *m_n1
      008AAD B6 92            [ 1] 1739     ld      a, *m_ai2               ; lo <= a <= hi ?
      008AAF B1 6F            [ 1] 1740     cp      a, *dq_lo+1
      008AB1 25 10            [ 1] 1741     jrc     00210$
      008AB3 B1 71            [ 1] 1742     cp      a, *dq_hi+1
      008AB5 22 0C            [ 1] 1743     jrugt   00210$
      008AB7 3C 95            [ 1] 1744     inc     *m_best
      008AB9 B6 98            [ 1] 1745     ld      a, *m_i0
      008ABB A1 FF            [ 1] 1746     cp      a, #0xFF
      008ABD 26 04            [ 1] 1747     jrne    00210$
      008ABF B6 92            [ 1] 1748     ld      a, *m_ai2
      008AC1 B7 98            [ 1] 1749     ld      *m_i0, a
      008AC3                       1750 00210$:
      008AC3 B6 92            [ 1] 1751     ld      a, *m_ai2
      008AC5 4C               [ 1] 1752     inc     a
      008AC6 B7 92            [ 1] 1753     ld      *m_ai2, a
      008AC8 B1 6D            [ 1] 1754     cp      a, *dq_acap+1
      008ACA 23 D9            [ 2] 1755     jrule   00209$
      008ACC 3D 96            [ 1] 1756     tnz     *m_ka                   ; laberr: known_all && lo==hi &&
      008ACE 27 17            [ 1] 1757     jreq    00212$              ;         afree != lo && !dead
      008AD0 B6 97            [ 1] 1758     ld      a, *m_n1
      008AD2 A1 02            [ 1] 1759     cp      a, #2
      008AD4 24 11            [ 1] 1760     jrnc    00212$
      008AD6 BE 6E            [ 2] 1761     ldw     x, *dq_lo
      008AD8 B3 70            [ 2] 1762     cpw     x, *dq_hi
      008ADA 26 0B            [ 1] 1763     jrne    00212$
      008ADC BE 74            [ 2] 1764     ldw     x, *dq_afree
      008ADE B3 6E            [ 2] 1765     cpw     x, *dq_lo
      008AE0 27 05            [ 1] 1766     jreq    00212$
      008AE2 BE 9E            [ 2] 1767     ldw     x, *_d_laberr
      008AE4 5C               [ 1] 1768     incw    x
      008AE5 BF 9E            [ 2] 1769     ldw     *_d_laberr, x
      008AE7                       1770 00212$:
      008AE7 AE FF FF         [ 2] 1771     ldw     x, #0xFFFF              ; tie_here = -1
      008AEA BF 8E            [ 2] 1772     ldw     *w_tieh, x
      008AEC B6 95            [ 1] 1773     ld      a, *m_best
      008AEE A1 02            [ 1] 1774     cp      a, #2
      008AF0 25 0F            [ 1] 1775     jrc     00218$
                                   1776     ; SIZE LEVER: the v1 form also tested `a_hat in {ins0, ins1}`, which
                                   1777     ; is ALWAYS TRUE -- an interior boundary has hinge cost 0 and argmin's
                                   1778     ; key is (cost, NOT interior, index) ascending, so a non-empty
                                   1779     ; interior set forces a_hat == ins0.  Proven in
                                   1780     ; dev_lever_b/ins0_proof.py over 1 619 577 decided segments of every
                                   1781     ; corpus and both fuzz sets, 0 counterexamples.  ins1 and the test
                                   1782     ; are gone; m_i1 is now unused.
      008AF2 5F               [ 1] 1783     clrw    x                   ; tt = k0 + ins0; if (tt < NB) tie
      008AF3 B6 98            [ 1] 1784     ld      a, *m_i0
      008AF5 97               [ 1] 1785     ld      xl, a
      008AF6 72 BB 00 5D      [ 2] 1786     addw    x, _g_sg
      008AFA C3 80 95         [ 2] 1787     cpw     x, _g_NB
      008AFD 24 02            [ 1] 1788     jrnc    00218$
      008AFF BF 8E            [ 2] 1789     ldw     *w_tieh, x
      008B01                       1790 00218$:
      008B01 AE FF FF         [ 2] 1791     ldw     x, #0xFFFF              ; suffix-min d_sm over [lo..hi]
      008B04 BF 7E            [ 2] 1792     ldw     *m_c, x
      008B06 B6 71            [ 1] 1793     ld      a, *dq_hi+1
      008B08 B7 92            [ 1] 1794     ld      *m_ai2, a
      008B0A                       1795 00219$:
      008B0A B6 92            [ 1] 1796     ld      a, *m_ai2
      008B0C 48               [ 1] 1797     sll     a
      008B0D 5F               [ 1] 1798     clrw    x
      008B0E 97               [ 1] 1799     ld      xl, a
      008B0F DE 01 A8         [ 2] 1800     ldw     x, (_d_costs, x)
      008B12 B3 7E            [ 2] 1801     cpw     x, *m_c
      008B14 24 02            [ 1] 1802     jrnc    00220$
      008B16 BF 7E            [ 2] 1803     ldw     *m_c, x
      008B18                       1804 00220$:
      008B18 B6 92            [ 1] 1805     ld      a, *m_ai2
      008B1A 48               [ 1] 1806     sll     a
      008B1B 5F               [ 1] 1807     clrw    x
      008B1C 97               [ 1] 1808     ld      xl, a
      008B1D 90 BE 7E         [ 2] 1809     ldw     y, *m_c
      008B20 DF 01 C8         [ 2] 1810     ldw     (d_sm, x), y
      008B23 B6 92            [ 1] 1811     ld      a, *m_ai2
      008B25 B1 6F            [ 1] 1812     cp      a, *dq_lo+1
      008B27 27 04            [ 1] 1813     jreq    00221$
      008B29 3A 92            [ 1] 1814     dec     *m_ai2
      008B2B 20 DD            [ 2] 1815     jra     00219$
      008B2D                       1816 00221$:
      008B2D AE FF FF         [ 2] 1817     ldw     x, #0xFFFF              ; c0m online
      008B30 BF 80            [ 2] 1818     ldw     *m_c0, x
      008B32 BE 5D            [ 2] 1819     ldw     x, *_g_sg
      008B34 BF 86            [ 2] 1820     ldw     *m_t, x
      008B36                       1821 00222$:                         ; per-bit loop
      008B36 BE 86            [ 2] 1822     ldw     x, *m_t
      008B38 B3 84            [ 2] 1823     cpw     x, *m_e
      008B3A 25 03            [ 1] 1824     jrc     00223$
      008B3C CC 8C 23         [ 2] 1825     jp      00240$
      008B3F                       1826 00223$:
      008B3F BE 86            [ 2] 1827     ldw     x, *m_t
      008B41 72 B0 00 5D      [ 2] 1828     subw    x, _g_sg
      008B45 BF 88            [ 2] 1829     ldw     *m_off, x
      008B47 B3 72            [ 2] 1830     cpw     x, *dq_ahat             ; bit: off < ahat
      008B49 24 1B            [ 1] 1831     jrnc    00226$
      008B4B BE 86            [ 2] 1832     ldw     x, *m_t                 ; BSET(d_bits, t): LSB-first in byte
      008B4D 9F               [ 1] 1833     ld      a, xl
      008B4E A4 07            [ 1] 1834     and     a, #7
      008B50 B7 0D            [ 1] 1835     ld      *m_s, a
      008B52 54               [ 2] 1836     srlw    x
      008B53 54               [ 2] 1837     srlw    x
      008B54 54               [ 2] 1838     srlw    x
      008B55 A6 01            [ 1] 1839     ld      a, #1
      008B57 3D 0D            [ 1] 1840     tnz     *m_s
      008B59 27 05            [ 1] 1841     jreq    00225$
      008B5B                       1842 00224$:
      008B5B 48               [ 1] 1843     sll     a
      008B5C 3A 0D            [ 1] 1844     dec     *m_s
      008B5E 26 FB            [ 1] 1845     jrne    00224$
      008B60                       1846 00225$:
      008B60 DA 00 F7         [ 1] 1847     or      a, (_ov, x)
      008B63 D7 00 F7         [ 1] 1848     ld      (_ov, x), a
      008B66                       1849 00226$:
      008B66 BE 88            [ 2] 1850     ldw     x, *m_off               ; c0m: lo <= off <= hi
      008B68 B3 6E            [ 2] 1851     cpw     x, *dq_lo
      008B6A 25 12            [ 1] 1852     jrc     00228$
      008B6C B3 70            [ 2] 1853     cpw     x, *dq_hi
      008B6E 22 0E            [ 1] 1854     jrugt   00228$
      008B70 B6 89            [ 1] 1855     ld      a, *m_off+1
      008B72 48               [ 1] 1856     sll     a
      008B73 5F               [ 1] 1857     clrw    x
      008B74 97               [ 1] 1858     ld      xl, a
      008B75 DE 01 A8         [ 2] 1859     ldw     x, (_d_costs, x)
      008B78 B3 80            [ 2] 1860     cpw     x, *m_c0
      008B7A 24 02            [ 1] 1861     jrnc    00228$
      008B7C BF 80            [ 2] 1862     ldw     *m_c0, x
      008B7E                       1863 00228$:
      008B7E BE 88            [ 2] 1864     ldw     x, *m_off               ; c1m = sm[max(lo, off+1)] or 0xFFFF
      008B80 5C               [ 1] 1865     incw    x
      008B81 B3 6E            [ 2] 1866     cpw     x, *dq_lo
      008B83 24 02            [ 1] 1867     jrnc    00229$
      008B85 BE 6E            [ 2] 1868     ldw     x, *dq_lo
      008B87                       1869 00229$:
      008B87 B3 70            [ 2] 1870     cpw     x, *dq_hi
      008B89 23 05            [ 2] 1871     jrule   00230$
      008B8B AE FF FF         [ 2] 1872     ldw     x, #0xFFFF
      008B8E 20 07            [ 2] 1873     jra     00231$
      008B90                       1874 00230$:
      008B90 9F               [ 1] 1875     ld      a, xl
      008B91 48               [ 1] 1876     sll     a
      008B92 5F               [ 1] 1877     clrw    x
      008B93 97               [ 1] 1878     ld      xl, a
      008B94 DE 01 C8         [ 2] 1879     ldw     x, (d_sm, x)
      008B97                       1880 00231$:
      008B97 BF 82            [ 2] 1881     ldw     *m_c1, x
      008B99 BE 80            [ 2] 1882     ldw     x, *m_c0                ; m = 255 | min(255, |c0m - c1m|)
      008B9B A3 FF FF         [ 2] 1883     cpw     x, #0xFFFF
      008B9E 27 15            [ 1] 1884     jreq    00233$
      008BA0 BE 82            [ 2] 1885     ldw     x, *m_c1
      008BA2 A3 FF FF         [ 2] 1886     cpw     x, #0xFFFF
      008BA5 27 0E            [ 1] 1887     jreq    00233$
      008BA7 BE 80            [ 2] 1888     ldw     x, *m_c0
      008BA9 72 B0 00 82      [ 2] 1889     subw    x, m_c1
      008BAD 2A 01            [ 1] 1890     jrpl    00232$
      008BAF 50               [ 2] 1891     negw    x
      008BB0                       1892 00232$:
      008BB0 A3 00 FF         [ 2] 1893     cpw     x, #255
      008BB3 25 03            [ 1] 1894     jrc     00234$
      008BB5                       1895 00233$:
      008BB5 AE 00 FF         [ 2] 1896     ldw     x, #255
      008BB8                       1897 00234$:
      008BB8 9F               [ 1] 1898     ld      a, xl
      008BB9 B7 9B            [ 1] 1899     ld      *m_m, a
      008BBB BE 86            [ 2] 1900     ldw     x, *m_t                 ; tie overrides -> m = 0
      008BBD B3 8E            [ 2] 1901     cpw     x, *w_tieh
      008BBF 27 04            [ 1] 1902     jreq    00235$
      008BC1 B3 8C            [ 2] 1903     cpw     x, *w_tiep
      008BC3 26 02            [ 1] 1904     jrne    00236$
      008BC5                       1905 00235$:
      008BC5 3F 9B            [ 1] 1906     clr     *m_m
      008BC7                       1907 00236$:
      008BC7 BE 86            [ 2] 1908     ldw     x, *m_t                 ; payload' window (PP_LO = 24)
      008BC9 A3 00 18         [ 2] 1909     cpw     x, #24
      008BCC 25 4D            [ 1] 1910     jrc     00239$
      008BCE C3 80 A5         [ 2] 1911     cpw     x, _g_PPHI
      008BD1 24 48            [ 1] 1912     jrnc    00239$
                                   1913     ; ---- v2.3 chk_conf: k = t - 24; when k >= ND8 this is a CHECK bit,
                                   1914     ; so add its margin to v_chkconf[(k - ND8) >> 3] (u16, big-endian
                                   1915     ; like every other ldw-stored word here).  Only the 48 check bits
                                   1916     ; reach the add; the C pipeline tail RANKS the candidates of a
                                   1917     ; split check-byte position with these sums.
      008BD3 1D 00 18         [ 2] 1918     subw    x, #24                  ; X = k
      008BD6 C3 80 A7         [ 2] 1919     cpw     x, _g_ND8
      008BD9 25 16            [ 1] 1920     jrc     00238$
      008BDB 72 B0 80 A7      [ 2] 1921     subw    x, _g_ND8
      008BDF 54               [ 2] 1922     srlw    x
      008BE0 54               [ 2] 1923     srlw    x
      008BE1 54               [ 2] 1924     srlw    x                       ; X = (k - ND8) >> 3   (0..5)
      008BE2 58               [ 2] 1925     sllw    x                       ; X = word offset (0,2,..,10)
      008BE3 D6 02 1E         [ 1] 1926     ld      a, (_v_chkconf+1, x)    ; low byte += m
      008BE6 BB 9B            [ 1] 1927     add     a, *m_m
      008BE8 D7 02 1E         [ 1] 1928     ld      (_v_chkconf+1, x), a
      008BEB 24 04            [ 1] 1929     jrnc    00238$
      008BED 72 4C 02 1D      [ 1] 1930     inc     (_v_chkconf, x)         ; carry into the high byte
      008BF1                       1931 00238$:
      008BF1 B6 9B            [ 1] 1932     ld      a, *m_m                 ; weak?  (margin <= MG_MAX)
      008BF3 A1 08            [ 1] 1933     cp      a, #8
      008BF5 22 10            [ 1] 1934     jrugt   00243$
      008BF7 BE A3            [ 2] 1935     ldw     x, *_v_nweak
      008BF9 5C               [ 1] 1936     incw    x
      008BFA BF A3            [ 2] 1937     ldw     *_v_nweak, x
      008BFC 3D 9B            [ 1] 1938     tnz     *m_m
      008BFE 26 05            [ 1] 1939     jrne    00237$
      008C00 BE A5            [ 2] 1940     ldw     x, *_v_ntied
      008C02 5C               [ 1] 1941     incw    x
      008C03 BF A5            [ 2] 1942     ldw     *_v_ntied, x
      008C05                       1943 00237$:
      008C05 20 0A            [ 2] 1944     jra     00244$
      008C07                       1945 00243$:                         ; SS6.4: margin > MG_MAX -- degenerate
      008C07 CD 89 ED         [ 4] 1946     call    dwtst               ; geometry admits it anyway (Z = DW)
      008C0A 26 0F            [ 1] 1947     jrne    00239$
      008C0C BE A7            [ 2] 1948     ldw     x, *_v_ndw
      008C0E 5C               [ 1] 1949     incw    x
      008C0F BF A7            [ 2] 1950     ldw     *_v_ndw, x
      008C11                       1951 00244$:
      008C11 BE 86            [ 2] 1952     ldw     x, *m_t
      008C13 1D 00 18         [ 2] 1953     subw    x, #24
      008C16 B6 9B            [ 1] 1954     ld      a, *m_m
      008C18 CD 89 7F         [ 4] 1955     call    candi
      008C1B                       1956 00239$:
      008C1B BE 86            [ 2] 1957     ldw     x, *m_t
      008C1D 5C               [ 1] 1958     incw    x
      008C1E BF 86            [ 2] 1959     ldw     *m_t, x
      008C20 CC 8B 36         [ 2] 1960     jp      00222$
      008C23                       1961 00240$:                         ; segment epilogue: tiepend consume/set
      008C23 BE 8C            [ 2] 1962     ldw     x, *w_tiep
      008C25 2B 09            [ 1] 1963     jrmi    00241$
      008C27 B3 84            [ 2] 1964     cpw     x, *m_e
      008C29 24 05            [ 1] 1965     jrnc    00241$
      008C2B AE FF FF         [ 2] 1966     ldw     x, #0xFFFF
      008C2E BF 8C            [ 2] 1967     ldw     *w_tiep, x
      008C30                       1968 00241$:
      008C30 BE 8E            [ 2] 1969     ldw     x, *w_tieh
      008C32 2B 06            [ 1] 1970     jrmi    00242$
      008C34 B3 84            [ 2] 1971     cpw     x, *m_e
      008C36 25 02            [ 1] 1972     jrc     00242$
      008C38 BF 8C            [ 2] 1973     ldw     *w_tiep, x
      008C3A                       1974 00242$:
      008C3A CC 8A 43         [ 2] 1975     jp      00201$
                                   1976 
                                   1977 ; ======================================================================
                                   1978 ; v2.3 pipeline tail -- NOT here any more, and deliberately so.
                                   1979 ;
                                   1980 ; v2.2 hand-assembled the CRC8 chase and ws_decode_ex in this file.  v2.3
                                   1981 ; keeps the STREAMING LAYER in assembly (that is where the ~1470 B of
                                   1982 ; SDCC codegen savings live: scan / seed / refine / ss_next / decide /
                                   1983 ; decide_pass / calibrate, all 16- and 32-bit expression heavy) and
                                   1984 ; compiles the pipeline TAIL from decode.c even in USE_ASM_DEC builds:
                                   1985 ;
                                   1986 ;   crc16 / syn16 / maj3 / rank3 / ref_build / ref_at / ch_match /
                                   1987 ;   try_trial / chase_singles / chase_pairs / chase / ws_decode_ex
                                   1988 ;
                                   1989 ; WHY: the v2.3 tail is the intricate part -- a 16-bit residual, an
                                   1990 ; independent per-byte majority, a confidence-ranked reference CROSS
                                   1991 ; PRODUCT and a residual-comparison BUDGET.  Compiling it from the same
                                   1992 ; source the host-parity build uses makes it bit-exact with
                                   1993 ; embedded_v2.py BY CONSTRUCTION rather than by a second hand-audit, and
                                   1994 ; it is straight-line byte code that SDCC compiles about as tightly as
                                   1995 ; hand assembly would.  The streaming layer, which is where hand
                                   1996 ; assembly actually pays, is untouched.
                                   1997 ;
                                   1998 ; This file therefore exports the decision-pass state the C tail reads:
                                   1999 ;   _v_cand_t / _v_cand_m / _v_ncand   the candidate list
                                   2000 ;   _v_nweak / _v_ntied                the SS6.2 counters
                                   2001 ;   _v_ndw                             the SS6.4 counter
                                   2002 ;   _v_chkconf                         per-check-byte confidence (v2.3)
                                   2003 ;   _d_infeas / _d_laberr / _d_nseg    the R3/R4 counters
                                   2004 ; plus _g_K / _g_tau / _ov / _known_bit, which it already exported.
                                   2005 ; ======================================================================
                                   2006 
                                   2007 ; ======================================================================
                                   2008 ; P3 calibration cluster: label_interval / cal_cloud / cal_add /
                                   2009 ; width_fit / theta56 / calibrate.
                                   2010 ; Bit-exact ports; state in the zero page; c_hist = ov.hist (indexed).
                                   2011 ; _calibrate is exported from v2.3 on: the C pipeline tail
                                   2012 ; (ws_decode_ex) drives the four passes now that the hand-assembled
                                   2013 ; ws_decode_ex is gone.
                                   2014 ; ======================================================================
                                   2015 
                                   2016     .globl _calibrate
                                   2017 
                                   2018     .area CODE
                                   2019 
                                   2020 ; la_int: X = a (s16); g_sg.u/.v, m_L = k1-k0 -> A = cls (0/1/0xFF),
                                   2021 ; *w_llo = u-off, *w_lhi = v-off.  Exactly label_interval().
      008C3D                       2022 la_int:
      008C3D BF 34            [ 2] 2023     ldw     *m_la, x
      008C3F 5D               [ 2] 2024     tnzw    x
      008C40 26 05            [ 1] 2025     jrne    00500$
      008C42 5F               [ 1] 2026     clrw    x                   ; a == 0: off = 0, cls = 0
      008C43 4F               [ 1] 2027     clr     a
      008C44 CC 8C A1         [ 2] 2028     jp      00507$
      008C47                       2029 00500$:
      008C47 B3 7C            [ 2] 2030     cpw     x, *m_L
      008C49 27 45            [ 1] 2031     jreq    00509$              ; a == L: off = (L-1)*512, cls = 1 --
                                   2032                                 ; shares the d1<=d0 tail (m_la == L here)
      008C4B                       2033 00501$:
                                   2034     ; mid = (u+v)>>1 (arithmetic)
      008C4B BE 61            [ 2] 2035     ldw     x, *_g_sg+4
      008C4D 72 BB 00 63      [ 2] 2036     addw    x, _g_sg+6
      008C51 57               [ 2] 2037     sraw    x
      008C52 BF 7A            [ 2] 2038     ldw     *m_h, x             ; mid
                                   2039     ; d1 = |mid - ((a-1)*512 + 308)|
      008C54 BE 34            [ 2] 2040     ldw     x, *m_la
      008C56 5A               [ 2] 2041     decw    x
      008C57 9F               [ 1] 2042     ld      a, xl
      008C58 5F               [ 1] 2043     clrw    x
      008C59 95               [ 1] 2044     ld      xh, a
      008C5A 58               [ 2] 2045     sllw    x
      008C5B 1C 01 34         [ 2] 2046     addw    x, #308
      008C5E 50               [ 2] 2047     negw    x
      008C5F 72 BB 00 7A      [ 2] 2048     addw    x, *m_h             ; mid - h1pos
      008C63 2A 01            [ 1] 2049     jrpl    00502$
      008C65 50               [ 2] 2050     negw    x
      008C66                       2051 00502$:
      008C66 BF 7E            [ 2] 2052     ldw     *m_c, x             ; d1
                                   2053     ; d0 = |mid - (a*512 + 154)|
      008C68 B6 35            [ 1] 2054     ld      a, *m_la+1
      008C6A 5F               [ 1] 2055     clrw    x
      008C6B 95               [ 1] 2056     ld      xh, a
      008C6C 58               [ 2] 2057     sllw    x
      008C6D 1C 00 9A         [ 2] 2058     addw    x, #154
      008C70 50               [ 2] 2059     negw    x
      008C71 72 BB 00 7A      [ 2] 2060     addw    x, *m_h
      008C75 2A 01            [ 1] 2061     jrpl    00503$
      008C77 50               [ 2] 2062     negw    x
      008C78                       2063 00503$:
      008C78 BF 82            [ 2] 2064     ldw     *m_c1, x            ; d0
                                   2065     ; if (min(d0,d1) > 246) return -1
      008C7A B3 7E            [ 2] 2066     cpw     x, *m_c
      008C7C 2C 02            [ 1] 2067     jrsgt   00504$
                                   2068     ; d0 <= d1: min = d0 (in X)
      008C7E 20 02            [ 2] 2069     jra     00505$
      008C80                       2070 00504$:
      008C80 BE 7E            [ 2] 2071     ldw     x, *m_c             ; min = d1
      008C82                       2072 00505$:
      008C82 A3 00 F6         [ 2] 2073     cpw     x, #246
      008C85 2D 03            [ 1] 2074     jrsle   00506$
      008C87 A6 FF            [ 1] 2075     ld      a, #0xFF
      008C89 81               [ 4] 2076     ret
      008C8A                       2077 00506$:
                                   2078     ; if (d1 <= d0) off=(a-1)*512, cls=1 else off=a*512, cls=0
      008C8A BE 7E            [ 2] 2079     ldw     x, *m_c             ; d1
      008C8C B3 82            [ 2] 2080     cpw     x, *m_c1            ; vs d0
      008C8E 2C 0B            [ 1] 2081     jrsgt   00508$
      008C90                       2082 00509$:
      008C90 BE 34            [ 2] 2083     ldw     x, *m_la            ; d1 <= d0 (and the a == L entry)
      008C92 5A               [ 2] 2084     decw    x
      008C93 9F               [ 1] 2085     ld      a, xl
      008C94 5F               [ 1] 2086     clrw    x
      008C95 95               [ 1] 2087     ld      xh, a
      008C96 58               [ 2] 2088     sllw    x
      008C97 A6 01            [ 1] 2089     ld      a, #1
      008C99 20 06            [ 2] 2090     jra     00507$
      008C9B                       2091 00508$:
      008C9B B6 35            [ 1] 2092     ld      a, *m_la+1
      008C9D 5F               [ 1] 2093     clrw    x
      008C9E 95               [ 1] 2094     ld      xh, a
      008C9F 58               [ 2] 2095     sllw    x
      008CA0 4F               [ 1] 2096     clr     a
      008CA1                       2097 00507$:                         ; X = off, A = cls
      008CA1 88               [ 1] 2098     push    a
      008CA2 BF 7A            [ 2] 2099     ldw     *m_h, x
      008CA4 BE 61            [ 2] 2100     ldw     x, *_g_sg+4
      008CA6 72 B0 00 7A      [ 2] 2101     subw    x, *m_h
      008CAA BF 30            [ 2] 2102     ldw     *w_llo, x
      008CAC BE 63            [ 2] 2103     ldw     x, *_g_sg+6
      008CAE 72 B0 00 7A      [ 2] 2104     subw    x, *m_h
      008CB2 BF 32            [ 2] 2105     ldw     *w_lhi, x
      008CB4 84               [ 1] 2106     pop     a
      008CB5 81               [ 4] 2107     ret
                                   2108 
                                   2109 ; (hix moved into the VGAP block above -- vector-gap bytes are free)
                                   2110 
                                   2111 ; cal_cloud: g_sg.u/.fam; hist fold histogram
      008CB6                       2112 ccloud:
      008CB6 B6 65            [ 1] 2113     ld      a, *_g_sg+8
      008CB8 A1 05            [ 1] 2114     cp      a, #5
      008CBA 27 05            [ 1] 2115     jreq    00520$
      008CBC A1 06            [ 1] 2116     cp      a, #6
      008CBE 27 01            [ 1] 2117     jreq    00520$
      008CC0 81               [ 4] 2118     ret
      008CC1                       2119 00520$:
      008CC1 BE 61            [ 2] 2120     ldw     x, *_g_sg+4          ; u < 0 -> out
      008CC3 2B 39            [ 1] 2121     jrmi    00529$
      008CC5 A0 05            [ 1] 2122     sub     a, #5
      008CC7 B7 36            [ 1] 2123     ld      *m_f, a
                                   2124     ; d = (u & 511) - c_c0[f]
      008CC9 BE 61            [ 2] 2125     ldw     x, *_g_sg+4
      008CCB 9E               [ 1] 2126     ld      a, xh
      008CCC A4 01            [ 1] 2127     and     a, #1
      008CCE 95               [ 1] 2128     ld      xh, a               ; x = u & 511
      008CCF 89               [ 2] 2129     pushw   x
      008CD0 B6 36            [ 1] 2130     ld      a, *m_f
      008CD2 48               [ 1] 2131     sll     a
      008CD3 5F               [ 1] 2132     clrw    x
      008CD4 97               [ 1] 2133     ld      xl, a
      008CD5 DE 01 F8         [ 2] 2134     ldw     x, (c_c0, x)
      008CD8 BF 7A            [ 2] 2135     ldw     *m_h, x
      008CDA 85               [ 2] 2136     popw    x
      008CDB 72 B0 00 7A      [ 2] 2137     subw    x, *m_h             ; d
                                   2138     ; if (-64 <= d < 64): b = (d+64)>>1; hist[f][b]++ (sat 255)
      008CDF 1C 00 40         [ 2] 2139     addw    x, #64              ; d+64 in [0,128)
      008CE2 2B 1A            [ 1] 2140     jrmi    00529$
      008CE4 A3 00 80         [ 2] 2141     cpw     x, #128
      008CE7 24 15            [ 1] 2142     jrnc    00529$
      008CE9 54               [ 2] 2143     srlw    x                   ; b
      008CEA 89               [ 2] 2144     pushw   x
      008CEB B6 36            [ 1] 2145     ld      a, *m_f
      008CED CD 80 58         [ 4] 2146     call    hix
      008CF0 72 FB 01         [ 2] 2147     addw    x, (1, sp)
      008CF3 5B 02            [ 2] 2148     addw    sp, #2
      008CF5 D6 00 F7         [ 1] 2149     ld      a, (_ov, x)
      008CF8 4C               [ 1] 2150     inc     a
      008CF9 27 03            [ 1] 2151     jreq    00529$              ; was 255: saturate
      008CFB D7 00 F7         [ 1] 2152     ld      (_ov, x), a
      008CFE                       2153 00529$:
      008CFE 81               [ 4] 2154     ret
                                   2155 
                                   2156 ; cal_add: X = a; g_sg -> interval intersection + labx extremes
      008CFF                       2157 cadd:
      008CFF CD 8C 3D         [ 4] 2158     call    la_int
      008D02 A1 FF            [ 1] 2159     cp      a, #0xFF
      008D04 26 01            [ 1] 2160     jrne    00530$
      008D06 81               [ 4] 2161     ret
      008D07                       2162 00530$:
      008D07 B7 99            [ 1] 2163     ld      *m_i, a             ; ci
      008D09 48               [ 1] 2164     sll     a
      008D0A 5F               [ 1] 2165     clrw    x
      008D0B 97               [ 1] 2166     ld      xl, a
      008D0C 89               [ 2] 2167     pushw   x                   ; 2*ci
                                   2168     ; if (lo > c_lo[ci]) c_lo = lo
      008D0D DE 00 C8         [ 2] 2169     ldw     x, (c_lo, x)
      008D10 B3 30            [ 2] 2170     cpw     x, *w_llo
      008D12 2E 08            [ 1] 2171     jrsge   00531$
      008D14 1E 01            [ 2] 2172     ldw     x, (1, sp)
      008D16 90 BE 30         [ 2] 2173     ldw     y, *w_llo
      008D19 DF 00 C8         [ 2] 2174     ldw     (c_lo, x), y
      008D1C                       2175 00531$:
      008D1C 1E 01            [ 2] 2176     ldw     x, (1, sp)
      008D1E DE 00 CC         [ 2] 2177     ldw     x, (c_hi, x)
      008D21 B3 32            [ 2] 2178     cpw     x, *w_lhi
      008D23 2D 08            [ 1] 2179     jrsle   00532$
      008D25 1E 01            [ 2] 2180     ldw     x, (1, sp)
      008D27 90 BE 32         [ 2] 2181     ldw     y, *w_lhi
      008D2A DF 00 CC         [ 2] 2182     ldw     (c_hi, x), y
      008D2D                       2183 00532$:
                                   2184     ; if (c_n[ci] < 255) c_n[ci]++
      008D2D B6 99            [ 1] 2185     ld      a, *m_i
      008D2F 5F               [ 1] 2186     clrw    x
      008D30 97               [ 1] 2187     ld      xl, a
      008D31 D6 00 D0         [ 1] 2188     ld      a, (c_n, x)
      008D34 4C               [ 1] 2189     inc     a
      008D35 27 03            [ 1] 2190     jreq    00533$
      008D37 D7 00 D0         [ 1] 2191     ld      (c_n, x), a
      008D3A                       2192 00533$:
      008D3A 5B 02            [ 2] 2193     addw    sp, #2
                                   2194     ; fams 5/6 with lo >= 0: labx extremes of the fold coordinate
      008D3C B6 65            [ 1] 2195     ld      a, *_g_sg+8
      008D3E A1 05            [ 1] 2196     cp      a, #5
      008D40 27 05            [ 1] 2197     jreq    00534$
      008D42 A1 06            [ 1] 2198     cp      a, #6
      008D44 27 01            [ 1] 2199     jreq    00534$
      008D46 81               [ 4] 2200     ret
      008D47                       2201 00534$:
      008D47 BE 30            [ 2] 2202     ldw     x, *w_llo
      008D49 2A 03            [ 1] 2203     jrpl    00535$
      008D4B CC 8D CE         [ 2] 2204     jp      00549$              ; lo < 0: no fold sample
      008D4E                       2205 00535$:
      008D4E A0 05            [ 1] 2206     sub     a, #5
      008D50 B7 36            [ 1] 2207     ld      *m_f, a
      008D52 9E               [ 1] 2208     ld      a, xh               ; d = (lo & 511) - c_c0[f]
      008D53 A4 01            [ 1] 2209     and     a, #1
      008D55 95               [ 1] 2210     ld      xh, a
      008D56 89               [ 2] 2211     pushw   x
      008D57 B6 36            [ 1] 2212     ld      a, *m_f
      008D59 48               [ 1] 2213     sll     a
      008D5A 5F               [ 1] 2214     clrw    x
      008D5B 97               [ 1] 2215     ld      xl, a
      008D5C DE 01 F8         [ 2] 2216     ldw     x, (c_c0, x)
      008D5F BF 7A            [ 2] 2217     ldw     *m_h, x
      008D61 85               [ 2] 2218     popw    x
      008D62 72 B0 00 7A      [ 2] 2219     subw    x, *m_h
      008D66 BF 7E            [ 2] 2220     ldw     *m_c, x             ; d
      008D68 A3 FF C0         [ 2] 2221     cpw     x, #-64
      008D6B 2F 61            [ 1] 2222     jrslt   00549$
      008D6D A3 00 40         [ 2] 2223     cpw     x, #64
      008D70 2E 5C            [ 1] 2224     jrsge   00549$
      008D72 B6 36            [ 1] 2225     ld      a, *m_f
      008D74 48               [ 1] 2226     sll     a
      008D75 5F               [ 1] 2227     clrw    x
      008D76 97               [ 1] 2228     ld      xl, a
      008D77 BF 55            [ 2] 2229     ldw     *m_hx, x            ; 2*f (index into labx arrays)
      008D79 3D 99            [ 1] 2230     tnz     *m_i                ; cls?
      008D7B 26 29            [ 1] 2231     jrne    00540$
                                   2232     ; cls 0: if (d > labx0) { labx0b = labx0; labx0 = d; }
                                   2233     ;        else if (d > labx0b) labx0b = d
      008D7D BE 55            [ 2] 2234     ldw     x, *m_hx
      008D7F DE 01 E8         [ 2] 2235     ldw     x, (labx0, x)
      008D82 B3 7E            [ 2] 2236     cpw     x, *m_c
      008D84 2E 0E            [ 1] 2237     jrsge   00536$
      008D86 90 93            [ 1] 2238     ldw     y, x                ; old labx0
      008D88 BE 55            [ 2] 2239     ldw     x, *m_hx
      008D8A DF 01 F0         [ 2] 2240     ldw     (labx0b, x), y
      008D8D 90 BE 7E         [ 2] 2241     ldw     y, *m_c
      008D90 DF 01 E8         [ 2] 2242     ldw     (labx0, x), y
      008D93 81               [ 4] 2243     ret
      008D94                       2244 00536$:
      008D94 BE 55            [ 2] 2245     ldw     x, *m_hx
      008D96 DE 01 F0         [ 2] 2246     ldw     x, (labx0b, x)
      008D99 B3 7E            [ 2] 2247     cpw     x, *m_c
      008D9B 2E 31            [ 1] 2248     jrsge   00549$
      008D9D BE 55            [ 2] 2249     ldw     x, *m_hx
      008D9F 90 BE 7E         [ 2] 2250     ldw     y, *m_c
      008DA2 DF 01 F0         [ 2] 2251     ldw     (labx0b, x), y
      008DA5 81               [ 4] 2252     ret
      008DA6                       2253 00540$:
                                   2254     ; cls 1: if (d < labx1) { labx1b = labx1; labx1 = d; }
                                   2255     ;        else if (d < labx1b) labx1b = d
      008DA6 BE 55            [ 2] 2256     ldw     x, *m_hx
      008DA8 DE 01 EC         [ 2] 2257     ldw     x, (labx1, x)
      008DAB B3 7E            [ 2] 2258     cpw     x, *m_c
      008DAD 2D 0E            [ 1] 2259     jrsle   00542$
      008DAF 90 93            [ 1] 2260     ldw     y, x
      008DB1 BE 55            [ 2] 2261     ldw     x, *m_hx
      008DB3 DF 01 F4         [ 2] 2262     ldw     (labx1b, x), y
      008DB6 90 BE 7E         [ 2] 2263     ldw     y, *m_c
      008DB9 DF 01 EC         [ 2] 2264     ldw     (labx1, x), y
      008DBC 81               [ 4] 2265     ret
      008DBD                       2266 00542$:
      008DBD BE 55            [ 2] 2267     ldw     x, *m_hx
      008DBF DE 01 F4         [ 2] 2268     ldw     x, (labx1b, x)
      008DC2 B3 7E            [ 2] 2269     cpw     x, *m_c
      008DC4 2D 08            [ 1] 2270     jrsle   00549$
      008DC6 BE 55            [ 2] 2271     ldw     x, *m_hx
      008DC8 90 BE 7E         [ 2] 2272     ldw     y, *m_c
      008DCB DF 01 F4         [ 2] 2273     ldw     (labx1b, x), y
      008DCE                       2274 00549$:
      008DCE 81               [ 4] 2275     ret
                                   2276 
                                   2277 ; wfit: A = ci; X = prior; *m_c = blo, *m_c1 = bhi -> X = width fit
      008DCF                       2278 wfit:
      008DCF BF 7A            [ 2] 2279     ldw     *m_h, x             ; prior
      008DD1 5F               [ 1] 2280     clrw    x
      008DD2 97               [ 1] 2281     ld      xl, a
      008DD3 D6 00 D0         [ 1] 2282     ld      a, (c_n, x)
      008DD6 A1 03            [ 1] 2283     cp      a, #3
      008DD8 25 37            [ 1] 2284     jrc     00559$              ; c_n < LAB_MIN -> prior
      008DDA 9F               [ 1] 2285     ld      a, xl
      008DDB 48               [ 1] 2286     sll     a
      008DDC 5F               [ 1] 2287     clrw    x
      008DDD 97               [ 1] 2288     ld      xl, a
      008DDE 90 93            [ 1] 2289     ldw     y, x
      008DE0 DE 00 C8         [ 2] 2290     ldw     x, (c_lo, x)        ; lo
      008DE3 BF 84            [ 2] 2291     ldw     *m_e, x
      008DE5 93               [ 1] 2292     ldw     x, y
      008DE6 DE 00 CC         [ 2] 2293     ldw     x, (c_hi, x)        ; hi
      008DE9 BF 86            [ 2] 2294     ldw     *m_t, x
      008DEB BE 84            [ 2] 2295     ldw     x, *m_e
      008DED B3 86            [ 2] 2296     cpw     x, *m_t
      008DEF 2D 07            [ 1] 2297     jrsle   00551$
      008DF1 72 BB 00 86      [ 2] 2298     addw    x, *m_t             ; lo > hi: h = (lo+hi)>>1
      008DF5 57               [ 2] 2299     sraw    x
      008DF6 20 10            [ 2] 2300     jra     00553$
      008DF8                       2301 00551$:
      008DF8 BE 7A            [ 2] 2302     ldw     x, *m_h             ; h = clamp(prior, lo, hi)
      008DFA B3 84            [ 2] 2303     cpw     x, *m_e
      008DFC 2E 04            [ 1] 2304     jrsge   00552$
      008DFE BE 84            [ 2] 2305     ldw     x, *m_e
      008E00 20 06            [ 2] 2306     jra     00553$
      008E02                       2307 00552$:
      008E02 B3 86            [ 2] 2308     cpw     x, *m_t
      008E04 2D 02            [ 1] 2309     jrsle   00553$
      008E06 BE 86            [ 2] 2310     ldw     x, *m_t
      008E08                       2311 00553$:
      008E08 B3 7E            [ 2] 2312     cpw     x, *m_c             ; in [blo, bhi] else prior
      008E0A 2F 05            [ 1] 2313     jrslt   00559$
      008E0C B3 82            [ 2] 2314     cpw     x, *m_c1
      008E0E 2C 01            [ 1] 2315     jrsgt   00559$
      008E10 81               [ 4] 2316     ret
      008E11                       2317 00559$:
      008E11 BE 7A            [ 2] 2318     ldw     x, *m_h
      008E13 81               [ 4] 2319     ret
                                   2320 
                                   2321 ; theta56: A = f -> A = have_theta, *m_th = theta
      008E14                       2322 th56:
      008E14 B7 36            [ 1] 2323     ld      *m_f, a
      008E16 48               [ 1] 2324     sll     a
      008E17 5F               [ 1] 2325     clrw    x
      008E18 97               [ 1] 2326     ld      xl, a
      008E19 BF 55            [ 2] 2327     ldw     *m_hx, x            ; 2*f
      008E1B DE 01 E8         [ 2] 2328     ldw     x, (labx0, x)
      008E1E BF 37            [ 2] 2329     ldw     *m_x0, x
      008E20 BE 55            [ 2] 2330     ldw     x, *m_hx
      008E22 DE 01 EC         [ 2] 2331     ldw     x, (labx1, x)
      008E25 BF 3A            [ 2] 2332     ldw     *m_x1, x
                                   2333     ; zlo = max(-32, x0+1); zhi = min(32, x1)
      008E27 BE 37            [ 2] 2334     ldw     x, *m_x0
      008E29 5C               [ 1] 2335     incw    x
      008E2A A3 FF E0         [ 2] 2336     cpw     x, #-32
      008E2D 2E 03            [ 1] 2337     jrsge   00560$
      008E2F AE FF E0         [ 2] 2338     ldw     x, #-32
      008E32                       2339 00560$:
      008E32 BF 3C            [ 2] 2340     ldw     *m_zlo, x
      008E34 BE 3A            [ 2] 2341     ldw     x, *m_x1
      008E36 A3 00 20         [ 2] 2342     cpw     x, #32
      008E39 2D 03            [ 1] 2343     jrsle   00561$
      008E3B AE 00 20         [ 2] 2344     ldw     x, #32
      008E3E                       2345 00561$:
      008E3E BF 3E            [ 2] 2346     ldw     *m_zhi, x
      008E40 5F               [ 1] 2347     clrw    x
      008E41 BF 40            [ 2] 2348     ldw     *m_th, x
      008E43 3F 42            [ 1] 2349     clr     *m_hv
                                   2350     ; m_e := f*64 (hist row base) for the WHOLE function -- the density
                                   2351     ; search AND the top/clear1 scan (hoisted: a stale row here cost one
                                   2352     ; capture in validation)
      008E45 B6 36            [ 1] 2353     ld      a, *m_f
      008E47 CD 80 58         [ 4] 2354     call    hix
      008E4A BF 84            [ 2] 2355     ldw     *m_e, x
                                   2356     ; density-gap search inside (zlo, zhi)
      008E4C BE 3C            [ 2] 2357     ldw     x, *m_zlo
      008E4E B3 3E            [ 2] 2358     cpw     x, *m_zhi
      008E50 2F 03            [ 1] 2359     jrslt   00562$
      008E52 CC 8F 1B         [ 2] 2360     jp      00570$              ; window empty
      008E55                       2361 00562$:
      008E55 BE 3C            [ 2] 2362     ldw     x, *m_zlo           ; blo = (zlo+64)>>1
      008E57 1C 00 40         [ 2] 2363     addw    x, #64
      008E5A 54               [ 2] 2364     srlw    x
      008E5B 9F               [ 1] 2365     ld      a, xl
      008E5C B7 54            [ 1] 2366     ld      *m_bb, a
      008E5E BE 3E            [ 2] 2367     ldw     x, *m_zhi           ; bhi = (zhi-1+64)>>1
      008E60 5A               [ 2] 2368     decw    x
      008E61 1C 00 40         [ 2] 2369     addw    x, #64
      008E64 54               [ 2] 2370     srlw    x
      008E65 9F               [ 1] 2371     ld      a, xl
      008E66 B7 9A            [ 1] 2372     ld      *m_j, a             ; bhi
      008E68 BE 3C            [ 2] 2373     ldw     x, *m_zlo
      008E6A BF 4B            [ 2] 2374     ldw     *m_prev, x
      008E6C 5F               [ 1] 2375     clrw    x
      008E6D BF 44            [ 2] 2376     ldw     *m_blo2, x
      008E6F BF 46            [ 2] 2377     ldw     *m_bhi2, x
      008E71 AE FF FF         [ 2] 2378     ldw     x, #-1
      008E74 BF 48            [ 2] 2379     ldw     *m_bg, x
      008E76 3F 4A            [ 1] 2380     clr     *m_no
      008E78                       2381 00563$:
      008E78 B6 54            [ 1] 2382     ld      a, *m_bb
      008E7A B1 9A            [ 1] 2383     cp      a, *m_j
      008E7C 22 32            [ 1] 2384     jrugt   00566$
      008E7E 5F               [ 1] 2385     clrw    x                   ; hist[f][b]?
      008E7F 97               [ 1] 2386     ld      xl, a
      008E80 72 BB 00 84      [ 2] 2387     addw    x, *m_e
      008E84 D6 00 F7         [ 1] 2388     ld      a, (_ov, x)
      008E87 4D               [ 1] 2389     tnz     a
      008E88 27 22            [ 1] 2390     jreq    00565$
                                   2391     ; x = (b<<1) - 64 + 1 ; gp = x - prev
      008E8A B6 54            [ 1] 2392     ld      a, *m_bb
      008E8C 48               [ 1] 2393     sll     a                   ; b <= 48 -> fits
      008E8D 5F               [ 1] 2394     clrw    x
      008E8E 97               [ 1] 2395     ld      xl, a
      008E8F 1D 00 3F         [ 2] 2396     subw    x, #63
      008E92 BF 7E            [ 2] 2397     ldw     *m_c, x             ; x coord
      008E94 72 B0 00 4B      [ 2] 2398     subw    x, *m_prev
      008E98 B3 48            [ 2] 2399     cpw     x, *m_bg
      008E9A 2D 0A            [ 1] 2400     jrsle   00564$
      008E9C BF 48            [ 2] 2401     ldw     *m_bg, x
      008E9E BE 4B            [ 2] 2402     ldw     x, *m_prev
      008EA0 BF 44            [ 2] 2403     ldw     *m_blo2, x
      008EA2 BE 7E            [ 2] 2404     ldw     x, *m_c
      008EA4 BF 46            [ 2] 2405     ldw     *m_bhi2, x
      008EA6                       2406 00564$:
      008EA6 BE 7E            [ 2] 2407     ldw     x, *m_c
      008EA8 BF 4B            [ 2] 2408     ldw     *m_prev, x
      008EAA 3C 4A            [ 1] 2409     inc     *m_no
      008EAC                       2410 00565$:
      008EAC 3C 54            [ 1] 2411     inc     *m_bb
      008EAE 20 C8            [ 2] 2412     jra     00563$
      008EB0                       2413 00566$:
      008EB0 BE 3E            [ 2] 2414     ldw     x, *m_zhi           ; trailing gap to zhi
      008EB2 72 B0 00 4B      [ 2] 2415     subw    x, *m_prev
      008EB6 B3 48            [ 2] 2416     cpw     x, *m_bg
      008EB8 2D 0A            [ 1] 2417     jrsle   00567$
      008EBA BF 48            [ 2] 2418     ldw     *m_bg, x
      008EBC BE 4B            [ 2] 2419     ldw     x, *m_prev
      008EBE BF 44            [ 2] 2420     ldw     *m_blo2, x
      008EC0 BE 3E            [ 2] 2421     ldw     x, *m_zhi
      008EC2 BF 46            [ 2] 2422     ldw     *m_bhi2, x
      008EC4                       2423 00567$:
      008EC4 3D 4A            [ 1] 2424     tnz     *m_no
      008EC6 26 16            [ 1] 2425     jrne    00568$
                                   2426     ; nocc == 0: theta = (zlo+zhi)>>1 iff has0 && has1
      008EC8 CD 90 20         [ 4] 2427     call    has01
      008ECB A1 03            [ 1] 2428     cp      a, #3
      008ECD 26 4C            [ 1] 2429     jrne    00570$
      008ECF BE 3C            [ 2] 2430     ldw     x, *m_zlo
      008ED1 72 BB 00 3E      [ 2] 2431     addw    x, *m_zhi
      008ED5 57               [ 2] 2432     sraw    x
      008ED6 BF 40            [ 2] 2433     ldw     *m_th, x
      008ED8 35 01 00 42      [ 1] 2434     mov     *m_hv, #1
      008EDC 20 3D            [ 2] 2435     jra     00570$
      008EDE                       2436 00568$:
                                   2437     ; ok = bg >= 5; if (ok && nocc+1 >= 4) density test
      008EDE BE 48            [ 2] 2438     ldw     x, *m_bg
      008EE0 A3 00 05         [ 2] 2439     cpw     x, #5
      008EE3 2F 36            [ 1] 2440     jrslt   00570$
      008EE5 B6 4A            [ 1] 2441     ld      a, *m_no
      008EE7 4C               [ 1] 2442     inc     a
      008EE8 A1 04            [ 1] 2443     cp      a, #4
      008EEA 25 22            [ 1] 2444     jrc     00569$
                                   2445     ; 2*bg*(nocc+1) < 5*(zhi-zlo) -> not ok   (s16-safe, proven)
      008EEC B6 49            [ 1] 2446     ld      a, *m_bg+1          ; bg <= 64
      008EEE 48               [ 1] 2447     sll     a                   ; 2*bg <= 128
      008EEF 5F               [ 1] 2448     clrw    x
      008EF0 97               [ 1] 2449     ld      xl, a
      008EF1 B6 4A            [ 1] 2450     ld      a, *m_no
      008EF3 4C               [ 1] 2451     inc     a                   ; nocc+1 <= 34
      008EF4 42               [ 4] 2452     mul     x, a                ; 2*bg*(nocc+1) <= 4352
      008EF5 BF 7E            [ 2] 2453     ldw     *m_c, x
      008EF7 BE 3E            [ 2] 2454     ldw     x, *m_zhi
      008EF9 72 B0 00 3C      [ 2] 2455     subw    x, *m_zlo           ; (zhi-zlo) in (0,64]
      008EFD 90 93            [ 1] 2456     ldw     y, x
      008EFF 58               [ 2] 2457     sllw    x
      008F00 58               [ 2] 2458     sllw    x                   ; *4
      008F01 90 89            [ 2] 2459     pushw   y
      008F03 72 FB 01         [ 2] 2460     addw    x, (1, sp)          ; *5
      008F06 5B 02            [ 2] 2461     addw    sp, #2
      008F08 B3 7E            [ 2] 2462     cpw     x, *m_c
      008F0A 2D 02            [ 1] 2463     jrsle   00569$              ; 5*(zhi-zlo) <= lhs -> ok stays
      008F0C 20 0D            [ 2] 2464     jra     00570$              ; lhs < rhs -> not ok
      008F0E                       2465 00569$:
      008F0E BE 44            [ 2] 2466     ldw     x, *m_blo2          ; theta = (best_lo + best_hi) >> 1
      008F10 72 BB 00 46      [ 2] 2467     addw    x, *m_bhi2
      008F14 57               [ 2] 2468     sraw    x
      008F15 BF 40            [ 2] 2469     ldw     *m_th, x
      008F17 35 01 00 42      [ 1] 2470     mov     *m_hv, #1
      008F1B                       2471 00570$:
                                   2472     ; label-extreme window [wlo, whi]
      008F1B CD 90 20         [ 4] 2473     call    has01
      008F1E 4D               [ 1] 2474     tnz     a
      008F1F 26 03            [ 1] 2475     jrne    00571$
      008F21 CC 8F 9C         [ 2] 2476     jp      00580$              ; neither label seen
      008F24                       2477 00571$:
      008F24 88               [ 1] 2478     push    a
      008F25 AE FF E0         [ 2] 2479     ldw     x, #-32
      008F28 BF 4E            [ 2] 2480     ldw     *m_wlo, x
      008F2A AE 00 20         [ 2] 2481     ldw     x, #32
      008F2D BF 50            [ 2] 2482     ldw     *m_whi, x
      008F2F 84               [ 1] 2483     pop     a
      008F30 88               [ 1] 2484     push    a
      008F31 A4 01            [ 1] 2485     and     a, #1               ; has0
      008F33 27 1A            [ 1] 2486     jreq    00573$
      008F35 BE 37            [ 2] 2487     ldw     x, *m_x0
      008F37 1D 00 08         [ 2] 2488     subw    x, #8
      008F3A BF 4E            [ 2] 2489     ldw     *m_wlo, x
      008F3C BE 55            [ 2] 2490     ldw     x, *m_hx            ; labx0b > -0x4000?
      008F3E DE 01 F0         [ 2] 2491     ldw     x, (labx0b, x)
      008F41 A3 C0 00         [ 2] 2492     cpw     x, #-0x4000
      008F44 2D 09            [ 1] 2493     jrsle   00573$
      008F46 1D 00 02         [ 2] 2494     subw    x, #2
      008F49 B3 4E            [ 2] 2495     cpw     x, *m_wlo
      008F4B 2D 02            [ 1] 2496     jrsle   00573$
      008F4D BF 4E            [ 2] 2497     ldw     *m_wlo, x
      008F4F                       2498 00573$:
      008F4F 84               [ 1] 2499     pop     a
      008F50 A4 02            [ 1] 2500     and     a, #2               ; has1
      008F52 27 1A            [ 1] 2501     jreq    00575$
      008F54 BE 3A            [ 2] 2502     ldw     x, *m_x1
      008F56 1C 00 08         [ 2] 2503     addw    x, #8
      008F59 BF 50            [ 2] 2504     ldw     *m_whi, x
      008F5B BE 55            [ 2] 2505     ldw     x, *m_hx
      008F5D DE 01 F4         [ 2] 2506     ldw     x, (labx1b, x)
      008F60 A3 3F FF         [ 2] 2507     cpw     x, #0x3FFF
      008F63 2E 09            [ 1] 2508     jrsge   00575$
      008F65 1C 00 02         [ 2] 2509     addw    x, #2
      008F68 B3 50            [ 2] 2510     cpw     x, *m_whi
      008F6A 2E 02            [ 1] 2511     jrsge   00575$
      008F6C BF 50            [ 2] 2512     ldw     *m_whi, x
      008F6E                       2513 00575$:
      008F6E BE 4E            [ 2] 2514     ldw     x, *m_wlo
      008F70 B3 50            [ 2] 2515     cpw     x, *m_whi
      008F72 2D 0D            [ 1] 2516     jrsle   00576$
      008F74 72 BB 00 50      [ 2] 2517     addw    x, *m_whi           ; wlo > whi: theta = (wlo+whi)>>1
      008F78 57               [ 2] 2518     sraw    x
      008F79 BF 40            [ 2] 2519     ldw     *m_th, x
      008F7B 35 01 00 42      [ 1] 2520     mov     *m_hv, #1
      008F7F 20 1B            [ 2] 2521     jra     00580$
      008F81                       2522 00576$:
                                   2523     ; th = clamp(have ? theta : 0, wlo, whi); have = 1
      008F81 3D 42            [ 1] 2524     tnz     *m_hv
      008F83 26 03            [ 1] 2525     jrne    00577$
      008F85 5F               [ 1] 2526     clrw    x
      008F86 BF 40            [ 2] 2527     ldw     *m_th, x
      008F88                       2528 00577$:
      008F88 BE 40            [ 2] 2529     ldw     x, *m_th
      008F8A B3 4E            [ 2] 2530     cpw     x, *m_wlo
      008F8C 2E 02            [ 1] 2531     jrsge   00578$
      008F8E BE 4E            [ 2] 2532     ldw     x, *m_wlo
      008F90                       2533 00578$:
      008F90 B3 50            [ 2] 2534     cpw     x, *m_whi
      008F92 2D 02            [ 1] 2535     jrsle   00579$
      008F94 BE 50            [ 2] 2536     ldw     x, *m_whi
      008F96                       2537 00579$:
      008F96 BF 40            [ 2] 2538     ldw     *m_th, x
      008F98 35 01 00 42      [ 1] 2539     mov     *m_hv, #1
      008F9C                       2540 00580$:
                                   2541     ; top / clear1 scan over all 64 bins
      008F9C 3F 53            [ 1] 2542     clr     *m_cl1
      008F9E 3F 52            [ 1] 2543     clr     *m_htp
      008FA0 5F               [ 1] 2544     clrw    x
      008FA1 BF 58            [ 2] 2545     ldw     *m_top, x
      008FA3 3F 54            [ 1] 2546     clr     *m_bb
      008FA5                       2547 00581$:
      008FA5 B6 54            [ 1] 2548     ld      a, *m_bb
      008FA7 A1 40            [ 1] 2549     cp      a, #64
      008FA9 24 36            [ 1] 2550     jrnc    00585$
      008FAB 5F               [ 1] 2551     clrw    x
      008FAC 97               [ 1] 2552     ld      xl, a
      008FAD 72 BB 00 84      [ 2] 2553     addw    x, *m_e
      008FB1 D6 00 F7         [ 1] 2554     ld      a, (_ov, x)
      008FB4 4D               [ 1] 2555     tnz     a
      008FB5 27 26            [ 1] 2556     jreq    00584$
      008FB7 B6 54            [ 1] 2557     ld      a, *m_bb              ; d = (b<<1) - 63
      008FB9 48               [ 1] 2558     sll     a
      008FBA 5F               [ 1] 2559     clrw    x
      008FBB 97               [ 1] 2560     ld      xl, a
      008FBC 1D 00 3F         [ 2] 2561     subw    x, #63
      008FBF A3 00 12         [ 2] 2562     cpw     x, #18
      008FC2 2D 06            [ 1] 2563     jrsle   00582$
      008FC4 35 01 00 53      [ 1] 2564     mov     *m_cl1, #1
      008FC8 20 13            [ 2] 2565     jra     00584$
      008FCA                       2566 00582$:
      008FCA A3 FF E8         [ 2] 2567     cpw     x, #-24
      008FCD 2D 0E            [ 1] 2568     jrsle   00584$
      008FCF 3D 52            [ 1] 2569     tnz     *m_htp
      008FD1 27 04            [ 1] 2570     jreq    00583$
      008FD3 B3 58            [ 2] 2571     cpw     x, *m_top
      008FD5 2D 06            [ 1] 2572     jrsle   00584$
      008FD7                       2573 00583$:
      008FD7 BF 58            [ 2] 2574     ldw     *m_top, x
      008FD9 35 01 00 52      [ 1] 2575     mov     *m_htp, #1
      008FDD                       2576 00584$:
      008FDD 3C 54            [ 1] 2577     inc     *m_bb
      008FDF 20 C4            [ 2] 2578     jra     00581$
      008FE1                       2579 00585$:
      008FE1 3D 53            [ 1] 2580     tnz     *m_cl1
      008FE3 26 38            [ 1] 2581     jrne    00589$
      008FE5 3D 52            [ 1] 2582     tnz     *m_htp
      008FE7 27 34            [ 1] 2583     jreq    00589$
                                   2584     ; floor = top + 3
      008FE9 BE 58            [ 2] 2585     ldw     x, *m_top
      008FEB 1C 00 03         [ 2] 2586     addw    x, #3
      008FEE BF 7E            [ 2] 2587     ldw     *m_c, x             ; floor
      008FF0 3D 42            [ 1] 2588     tnz     *m_hv
      008FF2 27 04            [ 1] 2589     jreq    00586$
      008FF4 B3 40            [ 2] 2590     cpw     x, *m_th
      008FF6 2D 02            [ 1] 2591     jrsle   00587$
      008FF8                       2592 00586$:
      008FF8 BF 40            [ 2] 2593     ldw     *m_th, x            ; theta = floor
      008FFA                       2594 00587$:
      008FFA 35 01 00 42      [ 1] 2595     mov     *m_hv, #1
                                   2596     ; if (has1 && x1+2 > floor && theta > x1+2) theta = x1+2
      008FFE CD 90 20         [ 4] 2597     call    has01
      009001 A4 02            [ 1] 2598     and     a, #2
      009003 27 18            [ 1] 2599     jreq    00589$
      009005 BE 3A            [ 2] 2600     ldw     x, *m_x1
      009007 1C 00 02         [ 2] 2601     addw    x, #2
      00900A B3 7E            [ 2] 2602     cpw     x, *m_c
      00900C 2D 0F            [ 1] 2603     jrsle   00589$
      00900E 90 93            [ 1] 2604     ldw     y, x
      009010 BE 40            [ 2] 2605     ldw     x, *m_th
      009012 90 89            [ 2] 2606     pushw   y
      009014 13 01            [ 2] 2607     cpw     x, (1, sp)
      009016 90 85            [ 2] 2608     popw    y
      009018 2D 03            [ 1] 2609     jrsle   00589$
      00901A 90 BF 40         [ 2] 2610     ldw     *m_th, y
      00901D                       2611 00589$:
      00901D B6 42            [ 1] 2612     ld      a, *m_hv
      00901F 81               [ 4] 2613     ret
                                   2614 
                                   2615 ; has01: A = has0 | (has1 << 1) for family *m_f (x0/x1 already loaded)
      009020                       2616 has01:
      009020 4F               [ 1] 2617     clr     a
      009021 BE 37            [ 2] 2618     ldw     x, *m_x0
      009023 A3 C0 00         [ 2] 2619     cpw     x, #-0x4000
      009026 2D 02            [ 1] 2620     jrsle   00590$
      009028 AA 01            [ 1] 2621     or      a, #1
      00902A                       2622 00590$:
      00902A BE 3A            [ 2] 2623     ldw     x, *m_x1
      00902C A3 3F FF         [ 2] 2624     cpw     x, #0x3FFF
      00902F 2E 02            [ 1] 2625     jrsge   00591$
      009031 AA 02            [ 1] 2626     or      a, #2
      009033                       2627 00591$:
      009033 81               [ 4] 2628     ret
                                   2629 
                                   2630 ; ---------------------------------------------------------------- calibrate
      009034                       2631 _calibrate:
                                   2632     ; init: c_lo = -0x4000, c_hi = 0x3FFF, c_n = 0, h0c/h1c = priors
      009034 AE C0 00         [ 2] 2633     ldw     x, #-0x4000
      009037 BF C8            [ 2] 2634     ldw     *c_lo, x
      009039 BF CA            [ 2] 2635     ldw     *c_lo+2, x
      00903B AE 3F FF         [ 2] 2636     ldw     x, #0x3FFF
      00903E BF CC            [ 2] 2637     ldw     *c_hi, x
      009040 BF CE            [ 2] 2638     ldw     *c_hi+2, x
      009042 5F               [ 1] 2639     clrw    x
      009043 BF D0            [ 2] 2640     ldw     *c_n, x
      009045 BF D6            [ 2] 2641     ldw     *zd56, x
      009047 AE 00 9A         [ 2] 2642     ldw     x, #154
      00904A BF D2            [ 2] 2643     ldw     *zh0c, x
      00904C AE 01 34         [ 2] 2644     ldw     x, #308
      00904F BF D4            [ 2] 2645     ldw     *zh1c, x
      009051 CD 87 45         [ 4] 2646     call    _set_gap56
                                   2647     ; per family: c_c0 = (154+308-gap)>>1; hist rows zeroed; labx init
      009054 3F 36            [ 1] 2648     clr     *m_f
      009056                       2649 00600$:
      009056 B6 36            [ 1] 2650     ld      a, *m_f
      009058 48               [ 1] 2651     sll     a
      009059 5F               [ 1] 2652     clrw    x
      00905A 97               [ 1] 2653     ld      xl, a
      00905B BF 55            [ 2] 2654     ldw     *m_hx, x
      00905D DE 00 D8         [ 2] 2655     ldw     x, (zgap, x)
      009060 50               [ 2] 2656     negw    x
      009061 1C 01 CE         [ 2] 2657     addw    x, #462             ; 154+308-gap
      009064 57               [ 2] 2658     sraw    x
      009065 90 93            [ 1] 2659     ldw     y, x
      009067 BE 55            [ 2] 2660     ldw     x, *m_hx
      009069 DF 01 F8         [ 2] 2661     ldw     (c_c0, x), y
      00906C AE C0 00         [ 2] 2662     ldw     x, #-0x4000
      00906F 90 93            [ 1] 2663     ldw     y, x
      009071 BE 55            [ 2] 2664     ldw     x, *m_hx
      009073 DF 01 E8         [ 2] 2665     ldw     (labx0, x), y
      009076 DF 01 F0         [ 2] 2666     ldw     (labx0b, x), y
      009079 AE 3F FF         [ 2] 2667     ldw     x, #0x3FFF
      00907C 90 93            [ 1] 2668     ldw     y, x
      00907E BE 55            [ 2] 2669     ldw     x, *m_hx
      009080 DF 01 EC         [ 2] 2670     ldw     (labx1, x), y
      009083 DF 01 F4         [ 2] 2671     ldw     (labx1b, x), y
      009086 B6 36            [ 1] 2672     ld      a, *m_f
      009088 CD 80 58         [ 4] 2673     call    hix
      00908B BF 84            [ 2] 2674     ldw     *m_e, x
      00908D 3F 54            [ 1] 2675     clr     *m_bb
      00908F                       2676 00601$:
      00908F B6 54            [ 1] 2677     ld      a, *m_bb
      009091 A1 40            [ 1] 2678     cp      a, #64
      009093 24 0E            [ 1] 2679     jrnc    00602$
      009095 5F               [ 1] 2680     clrw    x
      009096 97               [ 1] 2681     ld      xl, a
      009097 72 BB 00 84      [ 2] 2682     addw    x, *m_e
      00909B 4F               [ 1] 2683     clr     a
      00909C D7 00 F7         [ 1] 2684     ld      (_ov, x), a
      00909F 3C 54            [ 1] 2685     inc     *m_bb
      0090A1 20 EC            [ 2] 2686     jra     00601$
      0090A3                       2687 00602$:
      0090A3 3C 36            [ 1] 2688     inc     *m_f
      0090A5 B6 36            [ 1] 2689     ld      a, *m_f
      0090A7 A1 02            [ 1] 2690     cp      a, #2
      0090A9 25 AB            [ 1] 2691     jrc     00600$
                                   2692     ; segment loop
      0090AB CD 82 5B         [ 4] 2693     call    _ss_init
      0090AE                       2694 00603$:
      0090AE AE 00 5D         [ 2] 2695     ldw     x, #_g_sg
      0090B1 CD 82 B5         [ 4] 2696     call    _ss_next
      0090B4 4D               [ 1] 2697     tnz     a
      0090B5 26 03            [ 1] 2698     jrne    00604$
      0090B7 CC 90 FB         [ 2] 2699     jp      00610$
      0090BA                       2700 00604$:
      0090BA CD 8C B6         [ 4] 2701     call    ccloud
      0090BD BE 5F            [ 2] 2702     ldw     x, *_g_sg+2          ; if (k1 > NB) continue
      0090BF C3 80 95         [ 2] 2703     cpw     x, _g_NB
      0090C2 23 02            [ 2] 2704     jrule   00605$
      0090C4 20 E8            [ 2] 2705     jra     00603$
      0090C6                       2706 00605$:
                                   2707     ; known_all over [k0, min(k1,NB))  (k1 <= NB here)
      0090C6 BE 5F            [ 2] 2708     ldw     x, *_g_sg+2
      0090C8 BF 84            [ 2] 2709     ldw     *m_e, x
      0090CA BE 5D            [ 2] 2710     ldw     x, *_g_sg
      0090CC BF 86            [ 2] 2711     ldw     *m_t, x
      0090CE                       2712 00606$:
      0090CE BE 86            [ 2] 2713     ldw     x, *m_t
      0090D0 B3 84            [ 2] 2714     cpw     x, *m_e
      0090D2 24 10            [ 1] 2715     jrnc    00608$
      0090D4 CD 87 64         [ 4] 2716     call    _known_bit
      0090D7 A1 FF            [ 1] 2717     cp      a, #0xFF
      0090D9 26 02            [ 1] 2718     jrne    00607$
      0090DB 20 D1            [ 2] 2719     jra     00603$              ; unknown bit -> next segment
      0090DD                       2720 00607$:
      0090DD BE 86            [ 2] 2721     ldw     x, *m_t
      0090DF 5C               [ 1] 2722     incw    x
      0090E0 BF 86            [ 2] 2723     ldw     *m_t, x
      0090E2 20 EA            [ 2] 2724     jra     00606$
      0090E4                       2725 00608$:
      0090E4 CD 87 89         [ 4] 2726     call    _a_bounds_sg
      0090E7 BE 5F            [ 2] 2727     ldw     x, *_g_sg+2          ; m_L = k1-k0 (la_int's a==L test; P4's
      0090E9 72 B0 00 5D      [ 2] 2728     subw    x, _g_sg            ; dq_decide sets it for itself, but HERE
      0090ED BF 7C            [ 2] 2729     ldw     *m_L, x             ; it was stale -- fuzz_v22 E05 root cause)
      0090EF BE 66            [ 2] 2730     ldw     x, *_dq_amin
      0090F1 B3 68            [ 2] 2731     cpw     x, *_dq_amax
      0090F3 26 B9            [ 1] 2732     jrne    00603$
      0090F5 CD 8C FF         [ 4] 2733     call    cadd                ; X = amin
      0090F8 CC 90 AE         [ 2] 2734     jp      00603$
      0090FB                       2735 00610$:
                                   2736     ; width fit + separation guard
      0090FB AE 00 70         [ 2] 2737     ldw     x, #112
      0090FE BF 7E            [ 2] 2738     ldw     *m_c, x
      009100 AE 00 C0         [ 2] 2739     ldw     x, #192
      009103 BF 82            [ 2] 2740     ldw     *m_c1, x
      009105 4F               [ 1] 2741     clr     a
      009106 AE 00 9A         [ 2] 2742     ldw     x, #154
      009109 CD 8D CF         [ 4] 2743     call    wfit
      00910C BF 76            [ 2] 2744     ldw     *m_h0, x            ; h0 (reuse decide temp)
      00910E AE 00 FC         [ 2] 2745     ldw     x, #252
      009111 BF 7E            [ 2] 2746     ldw     *m_c, x
      009113 AE 01 78         [ 2] 2747     ldw     x, #376
      009116 BF 82            [ 2] 2748     ldw     *m_c1, x
      009118 A6 01            [ 1] 2749     ld      a, #1
      00911A AE 01 34         [ 2] 2750     ldw     x, #308
      00911D CD 8D CF         [ 4] 2751     call    wfit                ; h1
      009120 BF 78            [ 2] 2752     ldw     *m_h1, x
      009122 72 B0 00 76      [ 2] 2753     subw    x, *m_h0
      009126 A3 00 70         [ 2] 2754     cpw     x, #112
      009129 2F 0F            [ 1] 2755     jrslt   00611$
      00912B A3 00 C4         [ 2] 2756     cpw     x, #196
      00912E 2C 0A            [ 1] 2757     jrsgt   00611$
      009130 BE 76            [ 2] 2758     ldw     x, *m_h0
      009132 BF D2            [ 2] 2759     ldw     *zh0c, x
      009134 BE 78            [ 2] 2760     ldw     x, *m_h1
      009136 BF D4            [ 2] 2761     ldw     *zh1c, x
      009138 20 0A            [ 2] 2762     jra     00612$
      00913A                       2763 00611$:
      00913A AE 00 9A         [ 2] 2764     ldw     x, #154
      00913D BF D2            [ 2] 2765     ldw     *zh0c, x
      00913F AE 01 34         [ 2] 2766     ldw     x, #308
      009142 BF D4            [ 2] 2767     ldw     *zh1c, x
      009144                       2768 00612$:
                                   2769     ; per family: theta -> d56 clamp
      009144 3F 36            [ 1] 2770     clr     *m_f
      009146                       2771 00613$:
      009146 B6 36            [ 1] 2772     ld      a, *m_f
      009148 CD 8E 14         [ 4] 2773     call    th56
      00914B 4D               [ 1] 2774     tnz     a
      00914C 26 0A            [ 1] 2775     jrne    00614$
      00914E B6 36            [ 1] 2776     ld      a, *m_f             ; no theta: d56 = 0
      009150 5F               [ 1] 2777     clrw    x
      009151 97               [ 1] 2778     ld      xl, a
      009152 4F               [ 1] 2779     clr     a
      009153 D7 00 D6         [ 1] 2780     ld      (zd56, x), a
      009156 20 3E            [ 2] 2781     jra     00616$
      009158                       2782 00614$:
                                   2783     ; delta = th + c_c0[f] - ((h0c + h1c - gap56[f]) >> 1), clamp +-24
      009158 B6 36            [ 1] 2784     ld      a, *m_f
      00915A 48               [ 1] 2785     sll     a
      00915B 5F               [ 1] 2786     clrw    x
      00915C 97               [ 1] 2787     ld      xl, a
      00915D 89               [ 2] 2788     pushw   x
      00915E DE 00 D8         [ 2] 2789     ldw     x, (zgap, x)
      009161 BF 7E            [ 2] 2790     ldw     *m_c, x
      009163 BE D2            [ 2] 2791     ldw     x, *zh0c
      009165 72 BB 00 D4      [ 2] 2792     addw    x, *zh1c
      009169 72 B0 00 7E      [ 2] 2793     subw    x, *m_c
      00916D 57               [ 2] 2794     sraw    x
      00916E BF 7E            [ 2] 2795     ldw     *m_c, x             ; cfit
      009170 85               [ 2] 2796     popw    x
      009171 DE 01 F8         [ 2] 2797     ldw     x, (c_c0, x)
      009174 72 BB 00 40      [ 2] 2798     addw    x, *m_th
      009178 72 B0 00 7E      [ 2] 2799     subw    x, *m_c             ; delta
      00917C A3 FF E8         [ 2] 2800     cpw     x, #-24
      00917F 2E 03            [ 1] 2801     jrsge   00615$
      009181 AE FF E8         [ 2] 2802     ldw     x, #-24
      009184                       2803 00615$:
      009184 A3 00 18         [ 2] 2804     cpw     x, #24
      009187 2D 03            [ 1] 2805     jrsle   00617$
      009189 AE 00 18         [ 2] 2806     ldw     x, #24
      00918C                       2807 00617$:
      00918C 9F               [ 1] 2808     ld      a, xl
      00918D 88               [ 1] 2809     push    a
      00918E B6 36            [ 1] 2810     ld      a, *m_f
      009190 5F               [ 1] 2811     clrw    x
      009191 97               [ 1] 2812     ld      xl, a
      009192 84               [ 1] 2813     pop     a
      009193 D7 00 D6         [ 1] 2814     ld      (zd56, x), a
      009196                       2815 00616$:
      009196 3C 36            [ 1] 2816     inc     *m_f
      009198 B6 36            [ 1] 2817     ld      a, *m_f
      00919A A1 02            [ 1] 2818     cp      a, #2
      00919C 25 A8            [ 1] 2819     jrc     00613$
      00919E 81               [ 4] 2820     ret
                                   2821 
                                   2822 ; ======================================================================
                                   2823 ; Size-focused sample scanner: a rolled, bit-exact port of decode.c's
                                   2824 ; C scanner (the proven v1 ps_next semantics), ~350 B against scan.s's
                                   2825 ; speed-unrolled 900 B.  Slower per sample (~30 cy vs ~8); at ~11.5k
                                   2826 ; sample visits per decode that costs ~+10-15 ms on a production decode
                                   2827 ; -- traded for flash, which is the binding constraint.
                                   2828 ; ======================================================================
                                   2829 
                                   2830     .area CODE
                                   2831 
      00919F                       2832 _scan_init:
      00919F 5F               [ 1] 2833     clrw    x
      0091A0 BF B7            [ 2] 2834     ldw     *p_i, x
      0091A2 BF B9            [ 2] 2835     ldw     *p_tb, x
      0091A4 BF BB            [ 2] 2836     ldw     *p_ws, x
      0091A6 BF BD            [ 2] 2837     ldw     *p_tp, x
      0091A8 BF C6            [ 2] 2838     ldw     *p_lr, x
      0091AA 3F C1            [ 1] 2839     clr     *p_s
      0091AC 3F C2            [ 1] 2840     clr     *p_hp
      0091AE 3F C3            [ 1] 2841     clr     *p_ip
      0091B0 3F C4            [ 1] 2842     clr     *p_se
      0091B2 3F C5            [ 1] 2843     clr     *p_dn
      0091B4 81               [ 4] 2844     ret
                                   2845 
                                   2846 ; A = cap[i + A(0/1)] helper: X = p_i (+carry offset in A) -> A = byte
      0091B5                       2847 capat:                          ; X = index -> A = cap[X]
      0091B5 72 BB 00 AA      [ 2] 2848     addw    x, *_scan_cap
      0091B9 F6               [ 1] 2849     ld      a, (x)
      0091BA 81               [ 4] 2850     ret
                                   2851 
      0091BB                       2852 _scan_next:
      0091BB                       2853 00700$:                         ; while (!done)
      0091BB 3D C5            [ 1] 2854     tnz     *p_dn
      0091BD 27 03            [ 1] 2855     jreq    00701$
      0091BF CC 93 20         [ 2] 2856     jp      00790$
      0091C2                       2857 00701$:
      0091C2 BE B7            [ 2] 2858     ldw     x, *p_i             ; if (i >= len) break
      0091C4 B3 AC            [ 2] 2859     cpw     x, *_scan_len
      0091C6 25 03            [ 1] 2860     jrc     00702$
      0091C8 CC 93 20         [ 2] 2861     jp      00780$
      0091CB                       2862 00702$:
      0091CB B6 C1            [ 1] 2863     ld      a, *p_s
      0091CD A1 06            [ 1] 2864     cp      a, #6
      0091CF 26 6C            [ 1] 2865     jrne    00710$
      0091D1 BE B7            [ 2] 2866     ldw     x, *p_i             ; s == 6: whole-octet fast paths need i+1 < len
      0091D3 5C               [ 1] 2867     incw    x
      0091D4 B3 AC            [ 2] 2868     cpw     x, *_scan_len
      0091D6 24 65            [ 1] 2869     jrnc    00710$
      0091D8 CD 91 B5         [ 4] 2870     call    capat               ; bt = cap[i+1]
      0091DB 4D               [ 1] 2871     tnz     a
      0091DC 26 2F            [ 1] 2872     jrne    00703$
      0091DE 3D C3            [ 1] 2873     tnz     *p_ip               ; bt == 0x00 && !in_pulse
      0091E0 26 5B            [ 1] 2874     jrne    00710$
      0091E2 BE B9            [ 2] 2875     ldw     x, *p_tb            ; t_prev = tb + 61 + ws; have_prev = 1
      0091E4 1C 00 3D         [ 2] 2876     addw    x, #61
      0091E7 72 BB 00 BB      [ 2] 2877     addw    x, *p_ws
      0091EB BF BD            [ 2] 2878     ldw     *p_tp, x
      0091ED 35 01 00 C2      [ 1] 2879     mov     *p_hp, #1
      0091F1 BE C6            [ 2] 2880     ldw     x, *p_lr            ; low_run += 8
      0091F3 1C 00 08         [ 2] 2881     addw    x, #8
      0091F6 BF C6            [ 2] 2882     ldw     *p_lr, x
      0091F8 CD 93 36         [ 4] 2883     call    stepi               ; i++; tb += 40 (s stays 6)
      0091FB 3D C4            [ 1] 2884     tnz     *p_se               ; seen && low_run >= 200 -> done
      0091FD 27 BC            [ 1] 2885     jreq    00700$
      0091FF BE C6            [ 2] 2886     ldw     x, *p_lr
      009201 A3 00 C8         [ 2] 2887     cpw     x, #200
      009204 25 B5            [ 1] 2888     jrc     00700$
      009206 35 01 00 C5      [ 1] 2889     mov     *p_dn, #1
      00920A CC 93 20         [ 2] 2890     jp      00790$
      00920D                       2891 00703$:
      00920D A1 FF            [ 1] 2892     cp      a, #0xFF            ; bt == 0xFF && in_pulse
      00920F 26 2C            [ 1] 2893     jrne    00710$
      009211 3D C3            [ 1] 2894     tnz     *p_ip
      009213 27 28            [ 1] 2895     jreq    00710$
      009215 BE B9            [ 2] 2896     ldw     x, *p_tb            ; fa = tb + 63 + ws; ws += 2
      009217 1C 00 3F         [ 2] 2897     addw    x, #63
      00921A 72 BB 00 BB      [ 2] 2898     addw    x, *p_ws
      00921E BF B2            [ 2] 2899     ldw     *_scan_fa, x
      009220 BF BD            [ 2] 2900     ldw     *p_tp, x            ; t_prev = fa; have_prev = 1
      009222 35 01 00 C2      [ 1] 2901     mov     *p_hp, #1
      009226 BE BB            [ 2] 2902     ldw     x, *p_ws
      009228 5C               [ 1] 2903     incw    x
      009229 5C               [ 1] 2904     incw    x
      00922A BF BB            [ 2] 2905     ldw     *p_ws, x
      00922C 35 05 00 B6      [ 1] 2906     mov     *_scan_sfa, #5
      009230 5F               [ 1] 2907     clrw    x
      009231 BF C6            [ 2] 2908     ldw     *p_lr, x
      009233 35 01 00 C4      [ 1] 2909     mov     *p_se, #1
      009237 CD 93 36         [ 4] 2910     call    stepi
      00923A CC 91 BB         [ 2] 2911     jp      00700$
      00923D                       2912 00710$:
                                   2913     ; ordinary sample: v = bit of cap[i] (s<6) or cap[i+1] (s>=6)
      00923D B6 C1            [ 1] 2914     ld      a, *p_s
      00923F A1 06            [ 1] 2915     cp      a, #6
      009241 24 0F            [ 1] 2916     jrnc    00711$
      009243 BE B7            [ 2] 2917     ldw     x, *p_i             ; v = (cap[i] >> (5-s)) & 1
      009245 CD 91 B5         [ 4] 2918     call    capat
      009248 B7 0D            [ 1] 2919     ld      *m_s, a
      00924A B6 C1            [ 1] 2920     ld      a, *p_s
      00924C AB 03            [ 1] 2921     add     a, #3               ; bit (5-s) -> 8-(5-s) = s+3 shifts
      00924E B7 A9            [ 1] 2922     ld      *m_vi, a
      009250 20 1A            [ 2] 2923     jra     00713$
      009252                       2924 00711$:
      009252 BE B7            [ 2] 2925     ldw     x, *p_i             ; s >= 6: boundary bits live in cap[i+1]
      009254 5C               [ 1] 2926     incw    x
      009255 B3 AC            [ 2] 2927     cpw     x, *_scan_len
      009257 25 08            [ 1] 2928     jrc     00712$
      009259 CD 93 36         [ 4] 2929     call    stepi               ; last loop: BS lost; s = 0; continue
      00925C 3F C1            [ 1] 2930     clr     *p_s
      00925E CC 91 BB         [ 2] 2931     jp      00700$
      009261                       2932 00712$:
      009261 CD 91 B5         [ 4] 2933     call    capat               ; v = (cap[i+1] >> (7-(s-6))) & 1
      009264 B7 0D            [ 1] 2934     ld      *m_s, a
      009266 B6 C1            [ 1] 2935     ld      a, *p_s
      009268 A0 05            [ 1] 2936     sub     a, #5               ; bit (13-s) -> 8-(13-s) = s-5 shifts
      00926A B7 A9            [ 1] 2937     ld      *m_vi, a
      00926C                       2938 00713$:
      00926C B6 0D            [ 1] 2939     ld      a, *m_s
      00926E                       2940 00714$:
      00926E 48               [ 1] 2941     sll     a
      00926F 3A A9            [ 1] 2942     dec     *m_vi
      009271 26 FB            [ 1] 2943     jrne    00714$
      009273 4F               [ 1] 2944     clr     a
      009274 49               [ 1] 2945     rlc     a
      009275 B7 A9            [ 1] 2946     ld      *m_vi, a            ; v
                                   2947     ; t = tb + O[s] + ws
      009277 5F               [ 1] 2948     clrw    x
      009278 B6 C1            [ 1] 2949     ld      a, *p_s
      00927A 97               [ 1] 2950     ld      xl, a
      00927B D6 80 04         [ 1] 2951     ld      a, (sot, x)
      00927E 5F               [ 1] 2952     clrw    x
      00927F 97               [ 1] 2953     ld      xl, a
      009280 72 BB 00 B9      [ 2] 2954     addw    x, *p_tb
      009284 72 BB 00 BB      [ 2] 2955     addw    x, *p_ws
      009288 BF BF            [ 2] 2956     ldw     *p_t, x
                                   2957     ; slot/loop advance
      00928A B6 C1            [ 1] 2958     ld      a, *p_s
      00928C A1 07            [ 1] 2959     cp      a, #7
      00928E 26 07            [ 1] 2960     jrne    00715$
      009290 CD 93 36         [ 4] 2961     call    stepi
      009293 3F C1            [ 1] 2962     clr     *p_s
      009295 20 02            [ 2] 2963     jra     00716$
      009297                       2964 00715$:
      009297 3C C1            [ 1] 2965     inc     *p_s
      009299                       2966 00716$:
      009299 3D A9            [ 1] 2967     tnz     *m_vi
      00929B 27 4C            [ 1] 2968     jreq    00730$
                                   2969     ; ---- HIGH sample ----
      00929D B6 C1            [ 1] 2970     ld      a, *p_s             ; ws += W[s]  (s was advanced: use s-1 mod 8)
      00929F 4A               [ 1] 2971     dec     a
      0092A0 A4 07            [ 1] 2972     and     a, #7
      0092A2 5F               [ 1] 2973     clrw    x
      0092A3 97               [ 1] 2974     ld      xl, a
      0092A4 D6 80 0C         [ 1] 2975     ld      a, (swt, x)
      0092A7 88               [ 1] 2976     push    a                   ; sign-extend s8 into X
      0092A8 5F               [ 1] 2977     clrw    x
      0092A9 97               [ 1] 2978     ld      xl, a
      0092AA 84               [ 1] 2979     pop     a
      0092AB 4D               [ 1] 2980     tnz     a
      0092AC 2A 03            [ 1] 2981     jrpl    00717$
      0092AE 1C FF 00         [ 2] 2982     addw    x, #0xFF00
      0092B1                       2983 00717$:
      0092B1 72 BB 00 BB      [ 2] 2984     addw    x, *p_ws
      0092B5 BF BB            [ 2] 2985     ldw     *p_ws, x
      0092B7 3D C3            [ 1] 2986     tnz     *p_ip
      0092B9 26 1A            [ 1] 2987     jrne    00718$
      0092BB 35 01 00 C3      [ 1] 2988     mov     *p_ip, #1           ; pulse starts
      0092BF 3D C2            [ 1] 2989     tnz     *p_hp
      0092C1 27 04            [ 1] 2990     jreq    00719$
      0092C3 BE BD            [ 2] 2991     ldw     x, *p_tp            ; ra = t_prev
      0092C5 20 08            [ 2] 2992     jra     00720$
      0092C7                       2993 00719$:
      0092C7 BE BF            [ 2] 2994     ldw     x, *p_t             ; ra = max(t-4, 0)
      0092C9 1D 00 04         [ 2] 2995     subw    x, #4
      0092CC 24 01            [ 1] 2996     jrnc    00720$
      0092CE 5F               [ 1] 2997     clrw    x
      0092CF                       2998 00720$:
      0092CF BF AE            [ 2] 2999     ldw     *_scan_ra, x
      0092D1 BE BF            [ 2] 3000     ldw     x, *p_t
      0092D3 BF B0            [ 2] 3001     ldw     *_scan_rb, x
      0092D5                       3002 00718$:
      0092D5 BE BF            [ 2] 3003     ldw     x, *p_t             ; fa = t; sfa = s(orig); low_run = 0; seen = 1
      0092D7 BF B2            [ 2] 3004     ldw     *_scan_fa, x
      0092D9 B6 C1            [ 1] 3005     ld      a, *p_s
      0092DB 4A               [ 1] 3006     dec     a
      0092DC A4 07            [ 1] 3007     and     a, #7
      0092DE B7 B6            [ 1] 3008     ld      *_scan_sfa, a
      0092E0 5F               [ 1] 3009     clrw    x
      0092E1 BF C6            [ 2] 3010     ldw     *p_lr, x
      0092E3 35 01 00 C4      [ 1] 3011     mov     *p_se, #1
      0092E7 20 2C            [ 2] 3012     jra     00740$
      0092E9                       3013 00730$:
                                   3014     ; ---- LOW sample ----
      0092E9 3D C3            [ 1] 3015     tnz     *p_ip
      0092EB 27 14            [ 1] 3016     jreq    00731$
      0092ED 3F C3            [ 1] 3017     clr     *p_ip               ; pulse ends: emit
      0092EF BE BF            [ 2] 3018     ldw     x, *p_t
      0092F1 BF B4            [ 2] 3019     ldw     *_scan_fb, x
      0092F3 BF BD            [ 2] 3020     ldw     *p_tp, x            ; t_prev = t; have_prev = 1
      0092F5 35 01 00 C2      [ 1] 3021     mov     *p_hp, #1
      0092F9 AE 00 01         [ 2] 3022     ldw     x, #1
      0092FC BF C6            [ 2] 3023     ldw     *p_lr, x
      0092FE A6 01            [ 1] 3024     ld      a, #1
      009300 81               [ 4] 3025     ret
      009301                       3026 00731$:
      009301 BE C6            [ 2] 3027     ldw     x, *p_lr            ; low_run++
      009303 5C               [ 1] 3028     incw    x
      009304 BF C6            [ 2] 3029     ldw     *p_lr, x
      009306 3D C4            [ 1] 3030     tnz     *p_se
      009308 27 0B            [ 1] 3031     jreq    00740$
      00930A A3 00 C8         [ 2] 3032     cpw     x, #200
      00930D 25 06            [ 1] 3033     jrc     00740$
      00930F 35 01 00 C5      [ 1] 3034     mov     *p_dn, #1
      009313 20 0B            [ 2] 3035     jra     00790$
      009315                       3036 00740$:
      009315 BE BF            [ 2] 3037     ldw     x, *p_t             ; loop bottom: t_prev = t; have_prev = 1
      009317 BF BD            [ 2] 3038     ldw     *p_tp, x
      009319 35 01 00 C2      [ 1] 3039     mov     *p_hp, #1
      00931D CC 91 BB         [ 2] 3040     jp      00700$
                                   3041 
      009320                       3042 00780$:                         ; data exhausted
      009320                       3043 00790$:                         ; done / latch: flush a pulse in flight
      009320 3D C3            [ 1] 3044     tnz     *p_ip
      009322 27 0C            [ 1] 3045     jreq    00791$
      009324 3F C3            [ 1] 3046     clr     *p_ip
      009326 BE B2            [ 2] 3047     ldw     x, *_scan_fa        ; fb = fa + 4
      009328 1C 00 04         [ 2] 3048     addw    x, #4
      00932B BF B4            [ 2] 3049     ldw     *_scan_fb, x
      00932D A6 01            [ 1] 3050     ld      a, #1
      00932F 81               [ 4] 3051     ret
      009330                       3052 00791$:
      009330 35 01 00 C5      [ 1] 3053     mov     *p_dn, #1
      009334 4F               [ 1] 3054     clr     a
      009335 81               [ 4] 3055     ret
                                   3056 
                                   3057 ; stepi: i++; tb += 40
      009336                       3058 stepi:
      009336 BE B7            [ 2] 3059     ldw     x, *p_i
      009338 5C               [ 1] 3060     incw    x
      009339 BF B7            [ 2] 3061     ldw     *p_i, x
      00933B BE B9            [ 2] 3062     ldw     x, *p_tb
      00933D 1C 00 28         [ 2] 3063     addw    x, #40
      009340 BF B9            [ 2] 3064     ldw     *p_tb, x
      009342 81               [ 4] 3065     ret
                                   3066 
                                   3067 ; ======================================================================
                                   3068 ; P5/P6: v2.3 PIPELINE TAIL -- CRC16 confidence chase (SS7) + the
                                   3069 ; ws_decode_ex top level.  Hand assembly again, as in v2.2.
                                   3070 ;
                                   3071 ; The v2.3 tail first shipped as compiled C (decode.c, which REMAINS the
                                   3072 ; host-parity reference under !USE_ASM_DEC) and cost 1641 B of CODE plus
                                   3073 ; 112 B of CONST -- 531 B of the 748 B by which the production link
                                   3074 ; overflowed (PROD_CLOSURE SS13.1).  Everything below is a BIT-EXACT
                                   3075 ; port of those same C functions: crc16 / rank3 / ref_build / ch_match /
                                   3076 ; try_trial / chase_singles / chase_pairs / chase / ws_decode_ex.
                                   3077 ; Proven per step by dev_prod/ucsim_v23.py (emitted bytes + path + cause
                                   3078 ; + trials + comps + n_refs + n_weak per capture vs embedded_v2.py) at
                                   3079 ; BOTH geometries, ND = 16 and ND = 48.  No gate, relaxation, counter or
                                   3080 ; enumeration order was dropped to make room.
                                   3081 ;
                                   3082 ; TWO implementation substitutions, both value-identical (the same
                                   3083 ; discipline as v2.2's syn8-by-xtime instead of its XPOW table):
                                   3084 ;
                                   3085 ;  1. NO SYNDROME TABLE.  decode.c computes a trial residual as
                                   3086 ;     r_base ^ syn16(k) off a 48-entry x^(16+8i) table (96 B of CONST).
                                   3087 ;     Here a trial flips its bits in d_pp and recomputes
                                   3088 ;     crc16(d_pp[0..ND-1]).  CRC-16 is affine over GF(2), so the two are
                                   3089 ;     the SAME 16-bit value -- embedded_v2._selftest() asserts exactly
                                   3090 ;     that linearity -- and a CHECK-bit flip cannot move the residual
                                   3091 ;     because the check block sits outside the CRC's byte range, which is
                                   3092 ;     why decode.c's `touched` bookkeeping carries over unchanged.  Costs
                                   3093 ;     one 8*ND-step CRC per trial (<= 67 trials) and drops 96 B of table
                                   3094 ;     plus syn16() itself.
                                   3095 ;  2. The marker template lives here as HTR (6 B, each byte BIT-REVERSED
                                   3096 ;     so it XORs straight against d_bits' packing) and the popcount is a
                                   3097 ;     shift loop instead of decode.c's 16-B nibble table.
                                   3098 ;
                                   3099 ; Chase temps ALIAS the refine/calibrate scratch (r_* / m_n / m_d / m_r):
                                   3100 ; the chase runs strictly after decide_pass, refine and calibrate have
                                   3101 ; both returned, and dec_eps_centi's udiv32 runs only after
                                   3102 ; ws_decode_ex returns -- zero extra zero page for the whole tail, the
                                   3103 ; same rule the v2.2 tail used.  NOTE the ordering constraint that comes
                                   3104 ; with it: z_out is loaded AFTER decide_pass, because seed/refine own
                                   3105 ; m_n while they run.
                                   3106 ; ======================================================================
                                   3107 
                                   3108     .globl _ws_decode_ex
                                   3109     .globl _g_TIEE
                                   3110     .globl _g_PPB
                                   3111     .globl _g_PPE
                                   3112     .globl _g_TRB
                                   3113 
                           000024  3114 z_out   =   m_n         ; (2) caller's out[]
                           000026  3115 z_rb    =   m_n+2       ; (2) ch_rbase = crc16(D) of the unflipped payload
                           000028  3116 z_rr    =   m_d         ; (2) trial residual
                           00002C  3117 z_cj    =   m_r         ; (2) rank3 conf[j]
                           00002E  3118 z_nhi   =   m_r+2       ; (1) ch_nhi
                           00002F  3119 z_nlo   =   m_r+3       ; (1) ch_nlo
                           000030  3120 z_nref  =   r_lo        ; (1) ch_nref
                           000031  3121 z_comps =   r_lo+1      ; (1) ch_comps -- THE T_MAX BOUND
                           000032  3122 z_cap   =   r_lo+2      ; (1) ch_cap (REF_MAX or 1)
                           000033  3123 z_cn    =   r_lo+3      ; (1) ch_n
                           000034  3124 z_ti    =   r_lo+4      ; (1) trial member i
                           000035  3125 z_tj    =   r_lo+5      ; (1) trial member j (0xFF = single)
                           000036  3126 z_ww    =   r_lo+6      ; (1) phase want / sum
                           000037  3127 z_tch   =   r_lo+7      ; (1) touched: a CHECK bit moved the reference
                           000038  3128 z_sk3   =   r_lo+8      ; (1) parity gate skip3
                           000039  3129 z_sk5   =   r_lo+9      ; (1) parity gate skip5
                           00003A  3130 z_q     =   r_hi        ; (1) generic index (refs, ranks)
                           00003B  3131 z_v0    =   r_hi+1      ; (1) rank3 votes -- MUST stay contiguous
                           00003C  3132 z_v1    =   r_hi+2      ; (1)
                           00003D  3133 z_v2    =   r_hi+3      ; (1)
                           00003E  3134 z_bs    =   r_hi+4      ; (1) rank3 base: 0 = HI, 1 = LO
                           00003F  3135 z_ob    =   r_hi+5      ; (1) 3*base, ch_val write offset
                           000040  3136 z_ri    =   r_hi+6      ; (1)
                           000041  3137 z_rj    =   r_hi+7      ; (1)
                           000042  3138 z_a     =   r_hi+8      ; (1) ref_build HI rank
                           000043  3139 z_sm    =   r_hi+9      ; (1) ref_build diagonal (rank sum)
                           000044  3140 z_bb    =   r_melo      ; (1) ref_build LO rank
                                   3141 
                                   3142 ; SS10.2 OVERLAY: ch_ref (9 u16 = 18 B) and ch_val (6 B) share d_costs,
                                   3143 ; which is decision-pass scratch and dead the moment decide_pass returns
                                   3144 ; (the chase never calls decide()).  Exactly the cast decode.c's tail
                                   3145 ; made; 2*REF_MAX + 6 = 24 <= 32.
                           000000  3146 CH_REF  =   _d_costs
                           000012  3147 CH_VAL  =   _d_costs+18
                                   3148 
                                   3149     .area CODE
                                   3150 
                                   3151 ; --------------------------------------------------------------- crcpp
                                   3152 ; X = crc16(d_pp[0 .. ND-1]) -- CRC-16/CCITT-FALSE, init 0xFFFF, poly
                                   3153 ; 0x1021, MSB first, over the DATA bytes only.  d_pp is ov[g_PPB ..
                                   3154 ; g_PPE-1]; the check block starts at g_PPE and is NOT covered.
      009343                       3155 crcpp:
      009343 AE FF FF         [ 2] 3156     ldw     x, #0xFFFF
      009346 90 CE 80 AB      [ 2] 3157     ldw     y, _g_PPB
      00934A                       3158 01102$:
      00934A 90 D6 00 F7      [ 1] 3159     ld      a, (_ov, y)
      00934E B7 0D            [ 1] 3160     ld      *m_s, a
      009350 9E               [ 1] 3161     ld      a, xh
      009351 B8 0D            [ 1] 3162     xor     a, *m_s
      009353 95               [ 1] 3163     ld      xh, a
      009354 4B 08            [ 1] 3164     push    #8
      009356                       3165 01103$:                         ; X = (X<<1) ^ 0x1021 on carry out
      009356 58               [ 2] 3166     sllw    x
      009357 24 08            [ 1] 3167     jrnc    01104$
      009359 9E               [ 1] 3168     ld      a, xh
      00935A A8 10            [ 1] 3169     xor     a, #0x10
      00935C 95               [ 1] 3170     ld      xh, a
      00935D 9F               [ 1] 3171     ld      a, xl
      00935E A8 21            [ 1] 3172     xor     a, #0x21
      009360 97               [ 1] 3173     ld      xl, a
      009361                       3174 01104$:
      009361 0A 01            [ 1] 3175     dec     (1, sp)
      009363 26 F1            [ 1] 3176     jrne    01103$
      009365 84               [ 1] 3177     pop     a
      009366 90 5C            [ 1] 3178     incw    y
      009368 90 C3 80 AD      [ 2] 3179     cpw     y, _g_PPE
      00936C 25 DC            [ 1] 3180     jrult   01102$
      00936E 81               [ 4] 3181     ret
                                   3182 
                                   3183 ; --------------------------------------------------------------- chisd
                                   3184 ; A = candidate slot -> A = 1 if it is a DATA bit (v_cand_t[A] < ND8),
                                   3185 ; else 0.  Recomputed on demand, exactly like decode.c ch_isd().
                                   3186 ; candk: A = candidate slot -> X = v_cand_t[A], and C = 1 iff it is a
                                   3187 ; DATA bit (k < ND8).  RET leaves the flags alone, so both callers read C.
      00936F                       3188 candk:
      00936F 48               [ 1] 3189     sll     a
      009370 5F               [ 1] 3190     clrw    x
      009371 97               [ 1] 3191     ld      xl, a
      009372 DE 01 FC         [ 2] 3192     ldw     x, (_v_cand_t, x)
      009375 C3 80 A7         [ 2] 3193     cpw     x, _g_ND8
      009378 81               [ 4] 3194     ret
                                   3195 
      009379                       3196 chisd:
      009379 CD 93 6F         [ 4] 3197     call    candk
      00937C 4F               [ 1] 3198     clr     a                   ; CLR touches N/Z only -- C survives
      00937D 49               [ 1] 3199     rlc     a
      00937E 81               [ 4] 3200     ret
                                   3201 
                                   3202 ; ---------------------------------------------------------------- fl1
                                   3203 ; A = candidate slot (0xFF = none): toggle its payload' bit in d_pp and,
                                   3204 ; if it is a CHECK bit, mark z_tch -- the flip MOVED the reference set.
      00937F                       3205 fl1:
      00937F A1 FF            [ 1] 3206     cp      a, #0xFF
      009381 27 26            [ 1] 3207     jreq    01111$
      009383 CD 93 6F         [ 4] 3208     call    candk
      009386 25 04            [ 1] 3209     jrc     01110$
      009388 A6 01            [ 1] 3210     ld      a, #1
      00938A B7 37            [ 1] 3211     ld      *z_tch, a
      00938C                       3212 01110$:
                                   3213     ; toggle payload' bit X inside d_pp.  Wire bytes are MSB first, so
                                   3214     ; the mask is 1 << (7 - (k & 7)) = 0x80 >> (k & 7).
      00938C 9F               [ 1] 3215     ld      a, xl
      00938D A4 07            [ 1] 3216     and     a, #7
      00938F B7 0D            [ 1] 3217     ld      *m_s, a
      009391 54               [ 2] 3218     srlw    x
      009392 54               [ 2] 3219     srlw    x
      009393 54               [ 2] 3220     srlw    x
      009394 72 BB 80 AB      [ 2] 3221     addw    x, _g_PPB
      009398 A6 80            [ 1] 3222     ld      a, #0x80
      00939A                       3223 01107$:
      00939A 3D 0D            [ 1] 3224     tnz     *m_s
      00939C 27 05            [ 1] 3225     jreq    01108$
      00939E 44               [ 1] 3226     srl     a
      00939F 3A 0D            [ 1] 3227     dec     *m_s
      0093A1 20 F7            [ 2] 3228     jra     01107$
      0093A3                       3229 01108$:
      0093A3 D8 00 F7         [ 1] 3230     xor     a, (_ov, x)
      0093A6 D7 00 F7         [ 1] 3231     ld      (_ov, x), a
      0093A9                       3232 01111$:
      0093A9 81               [ 4] 3233     ret
                                   3234 
                                   3235 ; -------------------------------------------------------------- flipij
                                   3236 ; Toggle both members of the current flip set.  A flip is its own
                                   3237 ; inverse, so trial() calls this twice: once to apply, once to undo.
      0093AA                       3238 flipij:
      0093AA 3F 37            [ 1] 3239     clr     *z_tch
      0093AC B6 34            [ 1] 3240     ld      a, *z_ti
      0093AE CD 93 7F         [ 4] 3241     call    fl1
      0093B1 B6 35            [ 1] 3242     ld      a, *z_tj
      0093B3 CC 93 7F         [ 2] 3243     jp      fl1
                                   3244 
                                   3245 ; -------------------------------------------------------------- chmat
                                   3246 ; X = residual -> A = 1 accept / 0 no match / 2 T_MAX budget exhausted.
                                   3247 ; Every comparison is one 2^-16 exposure and one unit of budget: THIS
                                   3248 ; COUNTER IS THE BOUND (T_MAX = 131 = fa_budget(0.2 %, 1 ref)).
      0093B6                       3249 chmat:                          ; the residual under test is in *z_rr
      0093B6 3F 3A            [ 1] 3250     clr     *z_q
      0093B8                       3251 01115$:
      0093B8 B6 3A            [ 1] 3252     ld      a, *z_q
      0093BA B1 30            [ 1] 3253     cp      a, *z_nref
      0093BC 24 1B            [ 1] 3254     jrnc    01117$
      0093BE B6 31            [ 1] 3255     ld      a, *z_comps
      0093C0 A1 83            [ 1] 3256     cp      a, #131
      0093C2 24 17            [ 1] 3257     jrnc    01118$
      0093C4 3C 31            [ 1] 3258     inc     *z_comps
      0093C6 B6 3A            [ 1] 3259     ld      a, *z_q
      0093C8 48               [ 1] 3260     sll     a
      0093C9 5F               [ 1] 3261     clrw    x
      0093CA 97               [ 1] 3262     ld      xl, a
      0093CB DE 01 A8         [ 2] 3263     ldw     x, (CH_REF, x)
      0093CE B3 28            [ 2] 3264     cpw     x, *z_rr
      0093D0 27 04            [ 1] 3265     jreq    01116$
      0093D2 3C 3A            [ 1] 3266     inc     *z_q
      0093D4 20 E2            [ 2] 3267     jra     01115$
      0093D6                       3268 01116$:
      0093D6 A6 01            [ 1] 3269     ld      a, #1
      0093D8 81               [ 4] 3270     ret
      0093D9                       3271 01117$:
      0093D9 4F               [ 1] 3272     clr     a
      0093DA 81               [ 4] 3273     ret
      0093DB                       3274 01118$:
      0093DB A6 02            [ 1] 3275     ld      a, #2
      0093DD 81               [ 4] 3276     ret
                                   3277 
                                   3278 ; --------------------------------------------------------------- confx
                                   3279 ; A = copy index 0..2 -> X = v_chkconf[z_bs + 2*A] (u16, big endian, as
                                   3280 ; decide_pass writes it).
      0093DE                       3281 confx:
      0093DE 48               [ 1] 3282     sll     a
      0093DF 48               [ 1] 3283     sll     a
      0093E0 BB 3E            [ 1] 3284     add     a, *z_bs
      0093E2 BB 3E            [ 1] 3285     add     a, *z_bs
      0093E4 5F               [ 1] 3286     clrw    x
      0093E5 97               [ 1] 3287     ld      xl, a
      0093E6 DE 02 1D         [ 2] 3288     ldw     x, (_v_chkconf, x)
      0093E9 81               [ 4] 3289     ret
                                   3290 
                                   3291 ; -------------------------------------------------------------- putval
                                   3292 ; A = value, *z_q = rank r -> ch_val[3*z_bs + r] = A
      0093EA                       3293 putval:
      0093EA B7 0D            [ 1] 3294     ld      *m_s, a
      0093EC B6 3E            [ 1] 3295     ld      a, *z_bs
      0093EE B7 99            [ 1] 3296     ld      *m_i, a
      0093F0 48               [ 1] 3297     sll     a
      0093F1 BB 99            [ 1] 3298     add     a, *m_i
      0093F3 BB 3A            [ 1] 3299     add     a, *z_q
      0093F5 5F               [ 1] 3300     clrw    x
      0093F6 97               [ 1] 3301     ld      xl, a
      0093F7 B6 0D            [ 1] 3302     ld      a, *m_s
      0093F9 D7 01 BA         [ 1] 3303     ld      (CH_VAL, x), a
      0093FC 81               [ 4] 3304     ret
                                   3305 
                                   3306 ; --------------------------------------------------------------- rank3
                                   3307 ; A = base (0 = HI, 1 = LO).  Candidate values for ONE check-byte
                                   3308 ; position, best-confidence FIRST, into ch_val[3*base ...]; the count
                                   3309 ; goes to z_nhi / z_nlo.  Three votes admit NO tie, so the position
                                   3310 ; either has a unique >=2-vote majority (one candidate) or all three
                                   3311 ; differ (three candidates, confidence-ranked, ties keeping wire order).
                                   3312 ; Each copy's RANK is the number of copies that beat it -- that double
                                   3313 ; loop IS the ordering: no sort, no key array.  decode.c rank3() /
                                   3314 ; embedded_v2._ranked3().
      0093FD                       3315 rank3:
      0093FD B7 3E            [ 1] 3316     ld      *z_bs, a
      0093FF 5F               [ 1] 3317     clrw    x
      009400 97               [ 1] 3318     ld      xl, a               ; A still holds base
      009401 72 BB 80 AD      [ 2] 3319     addw    x, _g_PPE           ; &C[base] inside ov
      009405 D6 00 F7         [ 1] 3320     ld      a, (_ov, x)         ; C[base]
      009408 B7 3B            [ 1] 3321     ld      *z_v0, a
      00940A D6 00 F9         [ 1] 3322     ld      a, (_ov+2, x)       ; C[base+2]
      00940D B7 3C            [ 1] 3323     ld      *z_v1, a
      00940F D6 00 FB         [ 1] 3324     ld      a, (_ov+4, x)       ; C[base+4]
      009412 B7 3D            [ 1] 3325     ld      *z_v2, a
      009414 B6 3B            [ 1] 3326     ld      a, *z_v0
      009416 B1 3C            [ 1] 3327     cp      a, *z_v1
      009418 27 0A            [ 1] 3328     jreq    01120$
      00941A B1 3D            [ 1] 3329     cp      a, *z_v2
      00941C 27 06            [ 1] 3330     jreq    01120$
      00941E B6 3C            [ 1] 3331     ld      a, *z_v1
      009420 B1 3D            [ 1] 3332     cp      a, *z_v2
      009422 26 09            [ 1] 3333     jrne    01122$
      009424                       3334 01120$:                         ; A = the unique >=2-vote value
      009424 3F 3A            [ 1] 3335     clr     *z_q
      009426 CD 93 EA         [ 4] 3336     call    putval
      009429 A6 01            [ 1] 3337     ld      a, #1
      00942B 20 3C            [ 2] 3338     jra     01129$
      00942D                       3339 01122$:                         ; all three differ: rank by (-conf, index)
      00942D 3F 41            [ 1] 3340     clr     *z_rj
      00942F                       3341 01123$:
      00942F B6 41            [ 1] 3342     ld      a, *z_rj
      009431 A1 03            [ 1] 3343     cp      a, #3
      009433 24 32            [ 1] 3344     jrnc    01128$
      009435 CD 93 DE         [ 4] 3345     call    confx
      009438 BF 2C            [ 2] 3346     ldw     *z_cj, x
      00943A 3F 3A            [ 1] 3347     clr     *z_q                ; r = how many copies beat j
      00943C 3F 40            [ 1] 3348     clr     *z_ri
      00943E                       3349 01124$:
      00943E B6 40            [ 1] 3350     ld      a, *z_ri
      009440 A1 03            [ 1] 3351     cp      a, #3
      009442 24 15            [ 1] 3352     jrnc    01127$
      009444 CD 93 DE         [ 4] 3353     call    confx
      009447 B3 2C            [ 2] 3354     cpw     x, *z_cj
      009449 22 08            [ 1] 3355     jrugt   01125$              ; conf[i] > conf[j]
      00944B 26 08            [ 1] 3356     jrne    01126$
      00944D B6 40            [ 1] 3357     ld      a, *z_ri
      00944F B1 41            [ 1] 3358     cp      a, *z_rj
      009451 24 02            [ 1] 3359     jrnc    01126$              ; equal conf: the earlier copy wins
      009453                       3360 01125$:
      009453 3C 3A            [ 1] 3361     inc     *z_q
      009455                       3362 01126$:
      009455 3C 40            [ 1] 3363     inc     *z_ri
      009457 20 E5            [ 2] 3364     jra     01124$
      009459                       3365 01127$:
      009459 5F               [ 1] 3366     clrw    x
      00945A B6 41            [ 1] 3367     ld      a, *z_rj
      00945C 97               [ 1] 3368     ld      xl, a
      00945D D6 00 3B         [ 1] 3369     ld      a, (z_v0, x)
      009460 CD 93 EA         [ 4] 3370     call    putval
      009463 3C 41            [ 1] 3371     inc     *z_rj
      009465 20 C8            [ 2] 3372     jra     01123$
      009467                       3373 01128$:
      009467 A6 03            [ 1] 3374     ld      a, #3
      009469                       3375 01129$:
      009469 3D 3E            [ 1] 3376     tnz     *z_bs
      00946B 26 03            [ 1] 3377     jrne    01130$
      00946D B7 2E            [ 1] 3378     ld      *z_nhi, a
      00946F 81               [ 4] 3379     ret
      009470                       3380 01130$:
      009470 B7 2F            [ 1] 3381     ld      *z_nlo, a
      009472 81               [ 4] 3382     ret
                                   3383 
                                   3384 ; -------------------------------------------------------------- refbld
                                   3385 ; Materialise the reference set: rank3 for both byte positions, then
                                   3386 ; their CROSS PRODUCT in DIAGONAL order (rank-sum ascending, then
                                   3387 ; HI-rank ascending), truncated to z_cap.  Both lists are already
                                   3388 ; confidence-descending, so the diagonal tries better references first
                                   3389 ; without sorting the 9 pairs.  decode.c ref_build() /
                                   3390 ; embedded_v2._ref_candidates().
      009473                       3391 refbld:
      009473 4F               [ 1] 3392     clr     a
      009474 CD 93 FD         [ 4] 3393     call    rank3
      009477 A6 01            [ 1] 3394     ld      a, #1
      009479 CD 93 FD         [ 4] 3395     call    rank3
      00947C 3F 3A            [ 1] 3396     clr     *z_q
      00947E 3F 43            [ 1] 3397     clr     *z_sm
      009480 5F               [ 1] 3398     clrw    x                   ; XH stays 0 for the whole loop below:
                                   3399                                 ; nothing here writes it back
      009481                       3400 01135$:
      009481 B6 43            [ 1] 3401     ld      a, *z_sm
      009483 A1 05            [ 1] 3402     cp      a, #5
      009485 24 3C            [ 1] 3403     jrnc    01140$
      009487 3F 42            [ 1] 3404     clr     *z_a
      009489                       3405 01136$:
      009489 B6 42            [ 1] 3406     ld      a, *z_a
      00948B B1 2E            [ 1] 3407     cp      a, *z_nhi
      00948D 24 30            [ 1] 3408     jrnc    01139$              ; a >= nhi: next diagonal
      00948F B1 43            [ 1] 3409     cp      a, *z_sm
      009491 22 2C            [ 1] 3410     jrugt   01139$              ; a > sm: b would be negative -- break
      009493 40               [ 1] 3411     neg     a                   ; A still holds z_a
      009494 BB 43            [ 1] 3412     add     a, *z_sm
      009496 B7 44            [ 1] 3413     ld      *z_bb, a            ; b = sm - a
      009498 B1 2F            [ 1] 3414     cp      a, *z_nlo
      00949A 24 1F            [ 1] 3415     jrnc    01138$              ; b >= nlo: continue
      00949C B6 3A            [ 1] 3416     ld      a, *z_q
      00949E B1 32            [ 1] 3417     cp      a, *z_cap
      0094A0 24 21            [ 1] 3418     jrnc    01140$              ; q >= cap: stop with nref = q
      0094A2 B6 42            [ 1] 3419     ld      a, *z_a
      0094A4 97               [ 1] 3420     ld      xl, a
      0094A5 D6 01 BA         [ 1] 3421     ld      a, (CH_VAL, x)
      0094A8 90 95            [ 1] 3422     ld      yh, a
      0094AA B6 44            [ 1] 3423     ld      a, *z_bb
      0094AC 97               [ 1] 3424     ld      xl, a
      0094AD D6 01 BD         [ 1] 3425     ld      a, (CH_VAL+3, x)
      0094B0 90 97            [ 1] 3426     ld      yl, a
      0094B2 B6 3A            [ 1] 3427     ld      a, *z_q
      0094B4 48               [ 1] 3428     sll     a
      0094B5 97               [ 1] 3429     ld      xl, a
      0094B6 DF 01 A8         [ 2] 3430     ldw     (CH_REF, x), y
      0094B9 3C 3A            [ 1] 3431     inc     *z_q
      0094BB                       3432 01138$:
      0094BB 3C 42            [ 1] 3433     inc     *z_a
      0094BD 20 CA            [ 2] 3434     jra     01136$
      0094BF                       3435 01139$:
      0094BF 3C 43            [ 1] 3436     inc     *z_sm
      0094C1 20 BE            [ 2] 3437     jra     01135$
      0094C3                       3438 01140$:
      0094C3 B6 3A            [ 1] 3439     ld      a, *z_q
      0094C5 B7 30            [ 1] 3440     ld      *z_nref, a
      0094C7 81               [ 4] 3441     ret
                                   3442 
                                   3443 ; --------------------------------------------------------------- trial
                                   3444 ; Evaluate the current flip set -> A = 1 accept (the flips stay applied:
                                   3445 ; only the DATA bytes are emitted, so the check block's state stops
                                   3446 ; mattering), 0 reject, 2 T_MAX budget exhausted.  decode.c try_trial().
      0094C8                       3447 trial:
      0094C8 3C DE            [ 1] 3448     inc     *_dec_info+2         ; trials++
      0094CA CD 93 AA         [ 4] 3449     call    flipij
      0094CD CD 93 43         [ 4] 3450     call    crcpp
      0094D0 BF 28            [ 2] 3451     ldw     *z_rr, x
      0094D2 3D 37            [ 1] 3452     tnz     *z_tch
      0094D4 27 03            [ 1] 3453     jreq    01145$
      0094D6 CD 94 73         [ 4] 3454     call    refbld              ; the flips MOVED the reference set
      0094D9                       3455 01145$:
      0094D9 CD 93 B6         [ 4] 3456     call    chmat
      0094DC A1 01            [ 1] 3457     cp      a, #1
      0094DE 27 0C            [ 1] 3458     jreq    01147$              ; accept: A is already 1
      0094E0 88               [ 1] 3459     push    a
      0094E1 CD 93 AA         [ 4] 3460     call    flipij              ; undo, then restore the base set
      0094E4 3D 37            [ 1] 3461     tnz     *z_tch
      0094E6 27 03            [ 1] 3462     jreq    01146$
      0094E8 CD 94 73         [ 4] 3463     call    refbld
      0094EB                       3464 01146$:
      0094EB 84               [ 1] 3465     pop     a
      0094EC                       3466 01147$:
      0094EC 81               [ 4] 3467     ret
                                   3468 
                                   3469 ; --------------------------------------------------------------- csing
                                   3470 ; One single-flip phase: candidates whose is-data flag == z_ww, in list
                                   3471 ; (= confidence) order.  A = 0 none / 1 accepted / 2 budget.
      0094ED                       3472 csing:
      0094ED 3F 34            [ 1] 3473     clr     *z_ti
      0094EF                       3474 01150$:
      0094EF B6 34            [ 1] 3475     ld      a, *z_ti
      0094F1 B1 33            [ 1] 3476     cp      a, *z_cn
      0094F3 24 16            [ 1] 3477     jrnc    01153$
      0094F5 CD 93 79         [ 4] 3478     call    chisd               ; A still holds z_ti
      0094F8 B1 36            [ 1] 3479     cp      a, *z_ww
      0094FA 26 0A            [ 1] 3480     jrne    01151$
      0094FC A6 FF            [ 1] 3481     ld      a, #0xFF
      0094FE B7 35            [ 1] 3482     ld      *z_tj, a
      009500 CD 94 C8         [ 4] 3483     call    trial
      009503 4D               [ 1] 3484     tnz     a
      009504 26 04            [ 1] 3485     jrne    01152$
      009506                       3486 01151$:
      009506 3C 34            [ 1] 3487     inc     *z_ti
      009508 20 E5            [ 2] 3488     jra     01150$
      00950A                       3489 01152$:
      00950A 81               [ 4] 3490     ret
      00950B                       3491 01153$:
      00950B 4F               [ 1] 3492     clr     a
      00950C 81               [ 4] 3493     ret
                                   3494 
                                   3495 ; --------------------------------------------------------------- cpair
                                   3496 ; One pair phase: i < j lexicographic, filtered by isd[i] + isd[j] ==
                                   3497 ; z_ww -- exactly the SS7.4 phase-2/4/5 enumeration orders.
                                   3498 ;
                                   3499 ; SS7.10 W2 bound: at v2.3 A_PAIR = A_MAX (11) and MG_PAIR = MG_MAX (8),
                                   3500 ; and cand_insert admits nothing above MG_MAX, so `j < A_PAIR &&
                                   3501 ; v_cand_m[j] <= MG_PAIR` is provably TRUE for every j < ch_n <= A_MAX.
                                   3502 ; decode.c compiles the two monotone tests out for exactly that reason;
                                   3503 ; tightening either constant brings them back in both places.  The hard
                                   3504 ; bound meanwhile is T_MAX comparisons, counted in chmat.
      00950D                       3505 cpair:
      00950D 3F 34            [ 1] 3506     clr     *z_ti
      00950F                       3507 01155$:
      00950F B6 34            [ 1] 3508     ld      a, *z_ti
      009511 B1 33            [ 1] 3509     cp      a, *z_cn
      009513 24 29            [ 1] 3510     jrnc    01159$
      009515 4C               [ 1] 3511     inc     a
      009516 B7 35            [ 1] 3512     ld      *z_tj, a
      009518                       3513 01156$:
      009518 B6 35            [ 1] 3514     ld      a, *z_tj
      00951A B1 33            [ 1] 3515     cp      a, *z_cn
      00951C 24 1C            [ 1] 3516     jrnc    01158$
      00951E B6 34            [ 1] 3517     ld      a, *z_ti
      009520 CD 93 79         [ 4] 3518     call    chisd
      009523 B7 0D            [ 1] 3519     ld      *m_s, a
      009525 B6 35            [ 1] 3520     ld      a, *z_tj
      009527 CD 93 79         [ 4] 3521     call    chisd
      00952A BB 0D            [ 1] 3522     add     a, *m_s
      00952C B1 36            [ 1] 3523     cp      a, *z_ww
      00952E 26 06            [ 1] 3524     jrne    01157$
      009530 CD 94 C8         [ 4] 3525     call    trial
      009533 4D               [ 1] 3526     tnz     a
      009534 26 09            [ 1] 3527     jrne    01160$
      009536                       3528 01157$:
      009536 3C 35            [ 1] 3529     inc     *z_tj
      009538 20 DE            [ 2] 3530     jra     01156$
      00953A                       3531 01158$:
      00953A 3C 34            [ 1] 3532     inc     *z_ti
      00953C 20 D1            [ 2] 3533     jra     01155$
      00953E                       3534 01159$:
      00953E 4F               [ 1] 3535     clr     a
      00953F                       3536 01160$:
      00953F 81               [ 4] 3537     ret
                                   3538 
                                   3539 ; --------------------------------------------------------------- chasez
                                   3540 ; C1..C5 + R5..R8 of SS7.9 -> A = DEC_* path, dec_info.cause on refusal.
                                   3541 ; Works entirely on the decoded bit array and the <= A_MAX candidate
                                   3542 ; list -- no capture scan.  decode.c chase().
      009540                       3543 chasez:
                                   3544     ; C1: payload' byte p is the BIT REVERSAL of d_bits[HT_LEN + p]
                                   3545     ; (d_bits packs frame bit t at byte t>>3, bit t&7 LSB first, the wire
                                   3546     ; byte is MSB first, and PP_LO = 8*HT_LEN is a whole byte count).
      009540 AE 00 03         [ 2] 3547     ldw     x, #3
      009543 90 CE 80 AB      [ 2] 3548     ldw     y, _g_PPB
      009547                       3549 01170$:
      009547 D6 00 F7         [ 1] 3550     ld      a, (_ov, x)
      00954A 4B 08            [ 1] 3551     push    #8
      00954C                       3552 01171$:
      00954C 44               [ 1] 3553     srl     a
      00954D 39 0D            [ 1] 3554     rlc     *m_s
      00954F 0A 01            [ 1] 3555     dec     (1, sp)
      009551 26 F9            [ 1] 3556     jrne    01171$
      009553 84               [ 1] 3557     pop     a
      009554 B6 0D            [ 1] 3558     ld      a, *m_s
      009556 90 D7 00 F7      [ 1] 3559     ld      (_ov, y), a
      00955A 90 5C            [ 1] 3560     incw    y
      00955C 5C               [ 1] 3561     incw    x
      00955D C3 80 AF         [ 2] 3562     cpw     x, _g_TRB
      009560 25 E5            [ 1] 3563     jrult   01170$
      009562 BE A3            [ 2] 3564     ldw     x, *_v_nweak
      009564 BF E1            [ 2] 3565     ldw     *_dec_info+5, x
      009566 BE A5            [ 2] 3566     ldw     x, *_v_ntied
      009568 BF E3            [ 2] 3567     ldw     *_dec_info+7, x
      00956A CD 93 43         [ 4] 3568     call    crcpp
      00956D BF 26            [ 2] 3569     ldw     *z_rb, x
      00956F 3F 31            [ 1] 3570     clr     *z_comps
                                   3571     ; RELAXATION B feed-forward: a marker-suspect frame keeps its
                                   3572     ; per-byte-majority reference but is denied the split enumeration, so
                                   3573     ; it cannot also help itself to 9x the per-comparison exposure.
                                   3574     ; (violations <= MK_TOL here -- R2 already refused anything worse.)
      009571 B6 E9            [ 1] 3575     ld      a, *_dec_info+13
      009573 A1 05            [ 1] 3576     cp      a, #5               ; violations > MK_SOFT (4)?
      009575 A6 01            [ 1] 3577     ld      a, #1               ; LD A,#imm leaves C alone
      009577 24 02            [ 1] 3578     jrnc    01173$
      009579 A6 09            [ 1] 3579     ld      a, #9               ; REF_MAX
      00957B                       3580 01173$:
      00957B B7 32            [ 1] 3581     ld      *z_cap, a
      00957D CD 94 73         [ 4] 3582     call    refbld
      009580 B6 30            [ 1] 3583     ld      a, *z_nref
      009582 B7 F1            [ 1] 3584     ld      *_dec_info+21, a
                                   3585     ; ref_split = (nhi > 1) + (nlo > 1).  rank3 returns 1 or 3 and
                                   3586     ; nothing else, so nhi+nlo is 2, 4 or 6 and the count is
                                   3587     ; (nhi+nlo)/2 - 1 -- same three values, four instructions.
      009584 B6 2E            [ 1] 3588     ld      a, *z_nhi
      009586 BB 2F            [ 1] 3589     add     a, *z_nlo
      009588 44               [ 1] 3590     srl     a
      009589 4A               [ 1] 3591     dec     a
      00958A B7 F2            [ 1] 3592     ld      *_dec_info+22, a
                                   3593     ; R5: RETIRED in v2.3 (TIE_EMIT = 8*NPP+1 is structurally
                                   3594     ; unreachable -- n_tied counts a subset of the 8*NPP payload' bits).
                                   3595     ; Assembled, not deleted: restoring the gate stays one constant.
      00958C BE A5            [ 2] 3596     ldw     x, *_v_ntied
      00958E C3 80 A9         [ 2] 3597     cpw     x, _g_TIEE
      009591 23 05            [ 2] 3598     jrule   01174$
      009593 A6 05            [ 1] 3599     ld      a, #5
      009595 CC 96 68         [ 2] 3600     jp      01192$
      009598                       3601 01174$:
                                   3602     ; C2: direct accept.  v2.3 admits a SPLIT check block here too (the
                                   3603     ; emit-always directive); with a majority at both positions this is
                                   3604     ; bit-identical to v2.2's single-reference test.
      009598 BE 26            [ 2] 3605     ldw     x, *z_rb
      00959A BF 28            [ 2] 3606     ldw     *z_rr, x
      00959C CD 93 B6         [ 4] 3607     call    chmat
      00959F A1 01            [ 1] 3608     cp      a, #1
      0095A1 26 05            [ 1] 3609     jrne    01175$
      0095A3 A6 01            [ 1] 3610     ld      a, #1               ; DEC_DIRECT
      0095A5 CC 96 44         [ 2] 3611     jp      01182$
      0095A8                       3612 01175$:
      0095A8 3D A2            [ 1] 3613     tnz     *_v_ncand           ; C3: R6 -- nothing at all to flip.
      0095AA 26 05            [ 1] 3614     jrne    01176$              ; EQUIVALENT to n_weak == 0 && n_dw == 0:
      0095AC A6 06            [ 1] 3615     ld      a, #6               ; candi bails out only when the insertion
      0095AE CC 96 60         [ 2] 3616     jp      01191$              ; index reaches A_MAX, impossible while
      0095B1                       3617 01176$:                         ; the list is empty, so the first admitted
      0095B1 BE A3            [ 2] 3618     ldw     x, *_v_nweak        ; bit of either class always lands.
      0095B3 A3 00 0B         [ 2] 3619     cpw     x, #11              ; A_MAX -- R7 is the WEAK pool's
      0095B6 23 05            [ 2] 3620     jrule   01177$              ; completeness rule and is UNCHANGED (a DW
      0095B8 A6 07            [ 1] 3621     ld      a, #7               ; entry can never sort ahead of a weak
      0095BA CC 96 60         [ 2] 3622     jp      01191$              ; one, margin > MG_MAX vs <= MG_MAX)
      0095BD                       3623 01177$:
      0095BD 45 A2 33         [ 1] 3624     mov     *z_cn, *_v_ncand
                                   3625     ; Parity gate (EXACT at 16 bits: 0x11021 = (x+1)*0xF01F, so every
                                   3626     ; single-bit syndrome has odd parity and a weight-w data-only flip
                                   3627     ; has syndrome parity w mod 2).  Skip a data-only phase whose weight
                                   3628     ; parity can match NO admitted reference.
      0095C0 A6 01            [ 1] 3629     ld      a, #1
      0095C2 B7 38            [ 1] 3630     ld      *z_sk3, a
      0095C4 B7 39            [ 1] 3631     ld      *z_sk5, a
      0095C6 3F 3A            [ 1] 3632     clr     *z_q
      0095C8                       3633 01178$:
      0095C8 B6 3A            [ 1] 3634     ld      a, *z_q
      0095CA B1 30            [ 1] 3635     cp      a, *z_nref
      0095CC 24 32            [ 1] 3636     jrnc    01181$
      0095CE 48               [ 1] 3637     sll     a
      0095CF 5F               [ 1] 3638     clrw    x
      0095D0 97               [ 1] 3639     ld      xl, a
      0095D1 DE 01 A8         [ 2] 3640     ldw     x, (CH_REF, x)
      0095D4 9E               [ 1] 3641     ld      a, xh
      0095D5 B8 26            [ 1] 3642     xor     a, *z_rb
      0095D7 95               [ 1] 3643     ld      xh, a
      0095D8 9F               [ 1] 3644     ld      a, xl
      0095D9 B8 27            [ 1] 3645     xor     a, *z_rb+1
      0095DB 97               [ 1] 3646     ld      xl, a
                                   3647     ; parity16(X): x ^= x>>8; x ^= x>>4; x ^= x>>2; x ^= x>>1; & 1.
                                   3648     ; The nibble fold uses SWAP, whose HIGH half differs from a plain
                                   3649     ; >>4 -- bit 0, the only bit ever read, is identical.
      0095DC 9F               [ 1] 3650     ld      a, xl
      0095DD B7 0D            [ 1] 3651     ld      *m_s, a
      0095DF 9E               [ 1] 3652     ld      a, xh
      0095E0 B8 0D            [ 1] 3653     xor     a, *m_s
      0095E2 B7 0D            [ 1] 3654     ld      *m_s, a
      0095E4 4E               [ 1] 3655     swap    a
      0095E5 B8 0D            [ 1] 3656     xor     a, *m_s
      0095E7 B7 0D            [ 1] 3657     ld      *m_s, a
      0095E9 44               [ 1] 3658     srl     a
      0095EA 44               [ 1] 3659     srl     a
      0095EB B8 0D            [ 1] 3660     xor     a, *m_s
      0095ED B7 0D            [ 1] 3661     ld      *m_s, a
      0095EF 44               [ 1] 3662     srl     a
      0095F0 B8 0D            [ 1] 3663     xor     a, *m_s
      0095F2 A4 01            [ 1] 3664     and     a, #1
      0095F4 27 04            [ 1] 3665     jreq    01179$
      0095F6 3F 38            [ 1] 3666     clr     *z_sk3
      0095F8 20 02            [ 2] 3667     jra     01180$
      0095FA                       3668 01179$:
      0095FA 3F 39            [ 1] 3669     clr     *z_sk5
      0095FC                       3670 01180$:
      0095FC 3C 3A            [ 1] 3671     inc     *z_q
      0095FE 20 C8            [ 2] 3672     jra     01178$
      009600                       3673 01181$:
      009600 35 01 00 E0      [ 1] 3674     mov     *_dec_info+4, #1     ; chased = 1
                                   3675     ; C4: bounded, data-minimal, cheapest-first (SS7.4)
      009604 3F 36            [ 1] 3676     clr     *z_ww               ; phase 1: one check bit
      009606 CD 94 ED         [ 4] 3677     call    csing
      009609 4D               [ 1] 3678     tnz     a
      00960A 26 32            [ 1] 3679     jrne    01189$
      00960C 3F 36            [ 1] 3680     clr     *z_ww               ; phase 2: two check bits
      00960E CD 95 0D         [ 4] 3681     call    cpair
      009611 4D               [ 1] 3682     tnz     a
      009612 26 2A            [ 1] 3683     jrne    01189$
      009614 3D 38            [ 1] 3684     tnz     *z_sk3
      009616 26 0A            [ 1] 3685     jrne    01185$
      009618 A6 01            [ 1] 3686     ld      a, #1               ; phase 3: one data bit
      00961A B7 36            [ 1] 3687     ld      *z_ww, a
      00961C CD 94 ED         [ 4] 3688     call    csing
      00961F 4D               [ 1] 3689     tnz     a
      009620 26 1C            [ 1] 3690     jrne    01189$
      009622                       3691 01185$:
      009622 A6 01            [ 1] 3692     ld      a, #1               ; phase 4: data + check
      009624 B7 36            [ 1] 3693     ld      *z_ww, a
      009626 CD 95 0D         [ 4] 3694     call    cpair
      009629 4D               [ 1] 3695     tnz     a
      00962A 26 12            [ 1] 3696     jrne    01189$
      00962C 3D 39            [ 1] 3697     tnz     *z_sk5
      00962E 26 0A            [ 1] 3698     jrne    01187$
      009630 A6 02            [ 1] 3699     ld      a, #2               ; phase 5: two data bits
      009632 B7 36            [ 1] 3700     ld      *z_ww, a
      009634 CD 95 0D         [ 4] 3701     call    cpair
      009637 4D               [ 1] 3702     tnz     a
      009638 26 04            [ 1] 3703     jrne    01189$
      00963A                       3704 01187$:
      00963A A6 08            [ 1] 3705     ld      a, #8               ; R8: chase exhausted -- the honest end
      00963C 20 22            [ 2] 3706     jra     01191$
      00963E                       3707 01189$:                         ; a phase returned 1 (accept) or 2 (budget)
      00963E A1 02            [ 1] 3708     cp      a, #2
      009640 27 F8            [ 1] 3709     jreq    01187$              ; T_MAX budget hit -- R8 as well
      009642 A6 02            [ 1] 3710     ld      a, #2               ; DEC_CHASE
      009644                       3711 01182$:                         ; shared emit tail: A = DEC_* path
      009644 B7 0D            [ 1] 3712     ld      *m_s, a
      009646 B6 31            [ 1] 3713     ld      a, *z_comps
      009648 B7 F0            [ 1] 3714     ld      *_dec_info+20, a
      00964A CE 80 AB         [ 2] 3715     ldw     x, _g_PPB           ; out[0..ND-1] = d_pp[0..ND-1]
      00964D 90 5F            [ 1] 3716     clrw    y
      00964F                       3717 01105$:
      00964F D6 00 F7         [ 1] 3718     ld      a, (_ov, x)
      009652 91 D7 24         [ 4] 3719     ld      ([z_out], y), a
      009655 90 5C            [ 1] 3720     incw    y
      009657 5C               [ 1] 3721     incw    x
      009658 C3 80 AD         [ 2] 3722     cpw     x, _g_PPE
      00965B 25 F2            [ 1] 3723     jrult   01105$
      00965D B6 0D            [ 1] 3724     ld      a, *m_s
      00965F 81               [ 4] 3725     ret
      009660                       3726 01191$:
      009660 B7 0D            [ 1] 3727     ld      *m_s, a
      009662 B6 31            [ 1] 3728     ld      a, *z_comps
      009664 B7 F0            [ 1] 3729     ld      *_dec_info+20, a
      009666 B6 0D            [ 1] 3730     ld      a, *m_s
      009668                       3731 01192$:
      009668 B7 DD            [ 1] 3732     ld      *_dec_info+1, a      ; cause
      00966A 4F               [ 1] 3733     clr     a
      00966B 81               [ 4] 3734     ret
                                   3735 
                                   3736 ; Marker template, BIT-REVERSED per byte so it XORs straight against
                                   3737 ; d_bits.  v2.3: FF AA 65 / 9A 00 FF -> FF 55 A6 / 59 00 FF (the 0x00
                                   3738 ; zeros probe is its own reversal).
      00966C FF 55 A6 59 00 FF     3739 HTR: .db 0xFF,0x55,0xA6,0x59,0x00,0xFF
                                   3740 
                                   3741 ; -------------------------------------------------------- ws_decode_ex
                                   3742 ; C ABI (sdcccall(1), callee-pops): X = cap, (3,sp) = ncap, (5,sp) = out,
                                   3743 ; return address at (1,sp).  Returns A = DEC_* (== dec_info.path).
      009672                       3744 _ws_decode_ex:
      009672 CF 00 AA         [ 2] 3745     ldw     _scan_cap, x
      009675 1E 03            [ 2] 3746     ldw     x, (3, sp)
      009677 CF 00 AC         [ 2] 3747     ldw     _scan_len, x
      00967A AE 00 17         [ 2] 3748     ldw     x, #23              ; zero every dec_info field
      00967D                       3749 01195$:
      00967D 72 4F 00 DB      [ 1] 3750     clr     (_dec_info-1, x)
      009681 5A               [ 2] 3751     decw    x
      009682 26 F9            [ 1] 3752     jrne    01195$
      009684 CD 86 8C         [ 4] 3753     call    _seed
      009687 4D               [ 1] 3754     tnz     a
      009688 26 04            [ 1] 3755     jrne    01196$
      00968A A6 01            [ 1] 3756     ld      a, #1               ; R1 no seed / K outside the window
      00968C 20 79            [ 2] 3757     jra     01204$
      00968E                       3758 01196$:
      00968E CD 84 46         [ 4] 3759     call    _refine
      009691 CD 84 46         [ 4] 3760     call    _refine
      009694 CD 90 34         [ 4] 3761     call    _calibrate
      009697 CD 8A 15         [ 4] 3762     call    _decide_pass
                                   3763     ; out[] only NOW: z_out aliases m_n, which seed/refine own.
      00969A 1E 05            [ 2] 3764     ldw     x, (5, sp)
      00969C BF 24            [ 2] 3765     ldw     *z_out, x
      00969E CE 00 F3         [ 2] 3766     ldw     x, _g_K
      0096A1 BF E5            [ 2] 3767     ldw     *_dec_info+9, x
      0096A3 CE 00 F5         [ 2] 3768     ldw     x, _g_tau
      0096A6 BF E7            [ 2] 3769     ldw     *_dec_info+11, x
                                   3770     ; d_infeas / d_laberr / d_nseg are three consecutive zero-page words
                                   3771     ; and dec_info's infeasible / label_err / n_seg are consecutive too,
                                   3772     ; so one 6-byte copy does all three.
      0096A8 AE 00 06         [ 2] 3773     ldw     x, #6
      0096AB                       3774 01194$:
      0096AB D6 00 9B         [ 1] 3775     ld      a, (_d_infeas-1, x)
      0096AE D7 00 E9         [ 1] 3776     ld      (_dec_info+13, x), a
      0096B1 5A               [ 2] 3777     decw    x
      0096B2 26 F7            [ 1] 3778     jrne    01194$
                                   3779     ; Marker mismatches: the markers are whole BYTES at both ends, so
                                   3780     ; this is 2*HT_LEN byte XORs against the bit-reversed template and
                                   3781     ; their popcounts -- not NB known_bit() calls.  Identical count.
                                   3782     ; One loop over t = 0..5: HTR[t] pairs with d_bits[t] for t < 3 and
                                   3783     ; with d_bits[NBB-6+t] (= g_TRB - 3 + t) for the trailer bytes.
      0096B4 3F A9            [ 1] 3784     clr     *m_vi
      0096B6 90 5F            [ 1] 3785     clrw    y
      0096B8                       3786 01197$:
      0096B8 93               [ 1] 3787     ldw     x, y
      0096B9 A3 00 03         [ 2] 3788     cpw     x, #3
      0096BC 25 07            [ 1] 3789     jrult   01193$
      0096BE 72 BB 80 AF      [ 2] 3790     addw    x, _g_TRB
      0096C2 1D 00 03         [ 2] 3791     subw    x, #3
      0096C5                       3792 01193$:
      0096C5 D6 00 F7         [ 1] 3793     ld      a, (_ov, x)
      0096C8 93               [ 1] 3794     ldw     x, y
      0096C9 D8 96 6C         [ 1] 3795     xor     a, (HTR, x)
      0096CC 4B 08            [ 1] 3796     push    #8                  ; m_vi += popcount(A): six bytes per
      0096CE                       3797 01165$:                         ; frame, so decode.c's nibble table
      0096CE 44               [ 1] 3798     srl     a                   ; does not pay for itself here
      0096CF 24 02            [ 1] 3799     jrnc    01166$
      0096D1 3C A9            [ 1] 3800     inc     *m_vi
      0096D3                       3801 01166$:
      0096D3 0A 01            [ 1] 3802     dec     (1, sp)
      0096D5 26 F7            [ 1] 3803     jrne    01165$
      0096D7 84               [ 1] 3804     pop     a
      0096D8 90 5C            [ 1] 3805     incw    y
      0096DA 90 A3 00 06      [ 2] 3806     cpw     y, #6
      0096DE 25 D8            [ 1] 3807     jrult   01197$
      0096E0 B6 A9            [ 1] 3808     ld      a, *m_vi
      0096E2 B7 E9            [ 1] 3809     ld      *_dec_info+13, a
                                   3810     ; R2, RELAXATION B: a THRESHOLD over the N_MK (48) known marker
                                   3811     ; bits.  v2.2 refused on any single mismatch; v2.3 accepts up to
                                   3812     ; MK_TOL and feeds the count forward as confidence (chasez caps the
                                   3813     ; reference enumeration above MK_SOFT).  There is NO first/last-byte
                                   3814     ; special case -- the threshold is the whole rule.
      0096E4 A1 0D            [ 1] 3815     cp      a, #13              ; violations > MK_TOL (12)?
      0096E6 25 04            [ 1] 3816     jrc     01198$
      0096E8 A6 02            [ 1] 3817     ld      a, #2
      0096EA 20 1B            [ 2] 3818     jra     01204$
      0096EC                       3819 01198$:
      0096EC BE 9C            [ 2] 3820     ldw     x, *_d_infeas
      0096EE A3 00 18         [ 2] 3821     cpw     x, #24              ; GATE_INFEAS (RELAXATION A)
      0096F1 23 04            [ 2] 3822     jrule   01199$
      0096F3 A6 03            [ 1] 3823     ld      a, #3
      0096F5 20 10            [ 2] 3824     jra     01204$
      0096F7                       3825 01199$:
      0096F7 BE 9E            [ 2] 3826     ldw     x, *_d_laberr
      0096F9 A3 00 06         [ 2] 3827     cpw     x, #6               ; GATE_LABERR
      0096FC 23 04            [ 2] 3828     jrule   01200$
      0096FE A6 04            [ 1] 3829     ld      a, #4
      009700 20 05            [ 2] 3830     jra     01204$
      009702                       3831 01200$:
      009702 CD 95 40         [ 4] 3832     call    chasez              ; R5..R8 / emit inside
      009705 20 03            [ 2] 3833     jra     01205$
      009707                       3834 01204$:
      009707 B7 DD            [ 1] 3835     ld      *_dec_info+1, a      ; cause
      009709 4F               [ 1] 3836     clr     a
      00970A                       3837 01205$:
      00970A B7 DC            [ 1] 3838     ld      *_dec_info+0, a      ; path
      00970C 1E 01            [ 2] 3839     ldw     x, (1, sp)          ; callee-pops epilogue (4 arg bytes)
      00970E 5B 06            [ 2] 3840     addw    sp, #6
      009710 FC               [ 2] 3841     jp      (x)
