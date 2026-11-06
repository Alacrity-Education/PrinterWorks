                                      1 ; decode_asm.s -- size-focused hand assembly of the v2.2 decoder's
                                      2 ; streaming layer (USE_ASM_DEC=1 target builds; decode.c keeps the
                                      3 ; portable C versions for the host-parity build).
                                      4 ;
                                      5 ; CONTRACT: bit-exact vs decode.c's C versions / embedded_v2.py --
                                      6 ; proven per step by recon/approaches/dev_fw/ucsim_bitexact.py --asmdec
                                      7 ; (emitted bytes + path + cause per capture vs the Python reference).
                                      8 ;
                                      9 ; v2.2a: cpair carries the SS7.10 W2 bound (A_PAIR=3 / MG_PAIR=4) that
                                     10 ; closes the 2026-09-07 CRC-8 chase false-accepts (PROD_CLOSURE 11.4).
                                     11 ;
                                     12 ; Check-block geometry comes from the C consts (_g_CHK = CHK_LEN, 4 in
                                     13 ; v2.2 builds, 3 in the superseded v2.1 parity builds): the chase copies
                                     14 ; and the majority vote loop over g_CHK bytes, so ONE assembly serves
                                     15 ; both geometries.  The majority rule is the unique >=2-vote value
                                     16 ; (majz); at CHK 3 that is exactly the old 2-of-3 rule, at CHK 4 a 2-2
                                     17 ; tie or full split refuses the reference.
                                     18 ;
                                     19 ; Unlike scan.s (unrolled for SPEED), everything here is rolled for
                                     20 ; SIZE: SDCC's stm8 codegen spends 10-14 bytes per source op on the
                                     21 ; 16/32-bit expressions below; these routines share one 16x16->32
                                     22 ; multiply, one 32/32 divide and one map_raw core.
                                     23 ;
                                     24 ; SDCC sdcccall(1) ABI (matches build/decode.asm's call sites):
                                     25 ;   8-bit arg in A, 16-bit arg in X; returns A (8), X (16), Y:X (32);
                                     26 ;   A/X/Y caller-saved.
                                     27 ;
                                     28 ; Fixed-point notes used throughout (ranges proven by the reference's
                                     29 ; assert battery at both geometries):
                                     30 ;   t <= ~25.7k cy, K <= 60000  ->  t*K < 2^31, y = (t*K>>11)+tau < 2^20
                                     31 ;   p_u/p_v = yf - (BIAS + k*512) fits s16  ->  computed in low-16 only
                                     32 ;   d = y - y_prev >= 0 (y is non-decreasing after the >=0 clamp)
                                     33 
                                     34     .module decode_asm
                                     35 
                                     36     .globl _ss_init
                                     37     .globl _ss_next
                                     38     ; C-side state / constants (decode.c)
                                     39     .globl _g_K
                                     40     .globl _g_tau
                                     41     .globl _g_NB
                                     42     .globl _g_yend
                                     43     ; sample scanner (defined below -- prod builds do not link scan.s)
                                     44     .globl _scan_cap
                                     45     .globl _scan_len
                                     46     .globl _scan_init
                                     47     .globl _scan_next
                                     48     .globl _scan_ra
                                     49     .globl _scan_rb
                                     50     .globl _scan_fa
                                     51     .globl _scan_fb
                                     52     .globl _scan_sfa
                                     53 
                                     54 ; ------------------------------------------------------------------ state
                                     55 ; ZERO PAGE (ABS): every access below assembles to the SHORT (1-byte
                                     56 ; address) forms -- the whole point of hand assembly on STM8.  The link
                                     57 ; must push REL DATA above this block: --data-loc (Makefile PRODFLAGS /
                                     58 ; the ucsim harness) and guard_prod.py enforce it.
                                     59     .area DZP (ABS)
      000001                         60     .org 0x0001
                                     61 
      000001                         62 m_a:    .ds 2       ; mul16 operand A
      000003                         63 m_b:    .ds 2       ; mul16 operand B / setp base temp
      000005                         64 m_p:    .ds 4       ; mul16 product
      000009                         65 m_y:    .ds 4       ; mr16 result (s32 y)
      00000D                         66 m_s:    .ds 1       ; sign-extension byte temp
                                     67 
      00000E                         68 q_yprev: .ds 4      ; ss: previous pulse y (u32, clamped)
      000012                         69 q_n:     .ds 2      ; ss: bit index accumulator
      000014                         70 q_have:  .ds 1      ; ss: have_y
      000015                         71 q_pend:  .ds 1      ; ss: pending segment present
      000016                         72 q_pk0:   .ds 2      ; ss: pending k0
      000018                         73 q_pu:    .ds 2      ; ss: pending u (s16)
      00001A                         74 q_pv:    .ds 2      ; ss: pending v (s16)
      00001C                         75 q_pfam:  .ds 1      ; ss: pending family (slot of last high)
      00001D                         76 q_done:  .ds 1      ; ss: source exhausted
      00001E                         77 m_out:   .ds 2      ; ss_next: caller's Seg*
      000020                         78 m_fa:    .ds 2      ; low16 of map_raw(scan_fa)
      000022                         79 m_fb:    .ds 2      ; low16 of map_raw(scan_fb)
                                     80 
      000024                         81 m_n:    .ds 4       ; udiv32 dividend -> quotient
      000028                         82 m_d:    .ds 4       ; udiv32 divisor (preserved)
      00002C                         83 m_r:    .ds 4       ; udiv32 remainder
      000030                         84 r_lo:   .ds 10      ; refine lower-half block:  se(4) sy(4) n(2)
      00003A                         85 r_hi:   .ds 10      ; refine upper-half block
      000044                         86 r_melo: .ds 2
      000046                         87 r_mehi: .ds 2
      000048                         88 r_de:   .ds 2
      00004A                         89 r_dy:   .ds 4
      00004E                         90 r_dk:   .ds 4
      000052                         91 r_me:   .ds 2
      000054                         92 r_mylo: .ds 4
      000058                         93 r_myhi: .ds 4
      00005C                         94 r_sgn:  .ds 1
                                     95 
      00005D                         96 _g_sg:   .ds 9      ; shared Seg: k0(2) k1(2) u(2) v(2) fam(1)
      000066                         97 _dq_amin: .ds 2
      000068                         98 _dq_amax: .ds 2
      00006A                         99 dq_inter: .ds 2     ; interior bitmask
      00006C                        100 dq_acap: .ds 2
      00006E                        101 dq_lo:   .ds 2
      000070                        102 dq_hi:   .ds 2
      000072                        103 dq_ahat: .ds 2
      000074                        104 dq_afree: .ds 2
      000076                        105 m_h0:    .ds 2      ; effective h0/h1 for this segment
      000078                        106 m_h1:    .ds 2
      00007A                        107 m_h:     .ds 2      ; hinge h temp
      00007C                        108 m_L:     .ds 2
      00007E                        109 m_c:     .ds 2      ; scratch cost / argmin bc
      000080                        110 m_c0:    .ds 2      ; online prefix min
      000082                        111 m_c1:    .ds 2
      000084                        112 m_e:     .ds 2      ; kk1 / a_bounds end
      000086                        113 m_t:     .ds 2      ; t iterator
      000088                        114 m_off:   .ds 2
      00008A                        115 m_k:     .ds 2      ; cand_insert k
      00008C                        116 w_tiep:  .ds 2      ; v_tiepend (asm-owned)
      00008E                        117 w_tieh:  .ds 2      ; tie_here
      000090                        118 m_it:    .ds 1
      000091                        119 m_ai:    .ds 1
      000092                        120 m_ai2:   .ds 1
      000093                        121 m_alo:   .ds 1
      000094                        122 m_ahi:   .ds 1
      000095                        123 m_best:  .ds 1
      000096                        124 m_ka:    .ds 1      ; known_all
      000097                        125 m_n1:    .ds 1      ; inter-bit counter
      000098                        126 m_i0:    .ds 1      ; ins0 (0xFF = none)
      000099                        127 m_i1:    .ds 1
      00009A                        128 m_i:     .ds 1      ; cand_insert i
      00009B                        129 m_j:     .ds 1
      00009C                        130 m_m:     .ds 1      ; margin byte
      00009D                        131 w_inf:   .ds 2      ; d_infeas   (dec_info copy at decode end)
      00009F                        132 w_lab:   .ds 2      ; d_laberr
      0000A1                        133 w_nseg:  .ds 2      ; d_nseg
      0000A3                        134 zc_n:    .ds 1      ; v_ncand
      0000A4                        135 w_nweak: .ds 2      ; v_nweak
      0000A6                        136 w_ntied: .ds 2      ; v_ntied
      0000A8                        137 m_pp:    .ds 2      ; &d_pp = _ov + NBB (chase)
      0000AA                        138 m_outp:  .ds 2      ; ws_decode_ex out pointer
      0000AC                        139 m_R:     .ds 1      ; majority reference
      0000AD                        140 m_vi:    .ds 1      ; violations counter
      0000AE                        141 m_ti:    .ds 1      ; trial candidate i
      0000AF                        142 m_tj:    .ds 1      ; trial candidate j (0xFF none)
      0000B0                        143 m_rr:    .ds 1      ; trial residual r
      0000B1                        144 m_si:    .ds 1      ; alias-guard syndrome
      0000B2                        145 m_par:   .ds 1      ; parity of rbase^R (0xFF = no ref)
      0000B3                        146 m_hR:    .ds 1      ; have_R
      0000B4                        147 m_rb:    .ds 1      ; ch_rbase
      0000B5                        148 m_cn:    .ds 1      ; ch_n
      0000B6                        149 m_ww:    .ds 1      ; chase want/sum
                                    150 
                                    151 ; ---- size-focused sample scanner state (replaces scan.s in prod) ----
      0000B7                        152 _scan_cap: .ds 2    ; in: capture pointer
      0000B9                        153 _scan_len: .ds 2    ; in: capture bytes (= loops)
      0000BB                        154 _scan_ra:  .ds 2    ; out: rise bracket lo (cycles)
      0000BD                        155 _scan_rb:  .ds 2    ; out: rise bracket hi
      0000BF                        156 _scan_fa:  .ds 2    ; out: last-high time
      0000C1                        157 _scan_fb:  .ds 2    ; out: fall bracket hi
      0000C3                        158 _scan_sfa: .ds 1    ; out: slot of last high sample (family id)
      0000C4                        159 p_i:       .ds 2    ; loop index
      0000C6                        160 p_tb:      .ds 2    ; tbase = i * 40
      0000C8                        161 p_ws:      .ds 2    ; wsum (s16)
      0000CA                        162 p_tp:      .ds 2    ; t_prev
      0000CC                        163 p_t:       .ds 2    ; current sample time
      0000CE                        164 p_s:       .ds 1    ; slot 0..7
      0000CF                        165 p_hp:      .ds 1    ; have_prev
      0000D0                        166 p_ip:      .ds 1    ; in_pulse
      0000D1                        167 p_se:      .ds 1    ; seen
      0000D2                        168 p_dn:      .ds 1    ; done
      0000D3                        169 p_lr:      .ds 2    ; low_run
      0000D5                        170 c_lo:    .ds 4      ; calibration state (was decode.c statics)
      0000D9                        171 c_hi:    .ds 4
      0000DD                        172 c_n:     .ds 2
      0000DF                        173 zh0c:    .ds 2      ; c_h0c
      0000E1                        174 zh1c:    .ds 2      ; c_h1c
      0000E3                        175 zd56:    .ds 2      ; c_d56[2] (s8 each)
      0000E5                        176 labx0:   .ds 4
      0000E9                        177 labx1:   .ds 4
      0000ED                        178 labx0b:  .ds 4
      0000F1                        179 labx1b:  .ds 4
      0000F5                        180 c_c0:    .ds 4
      0000F9                        181 zgap:    .ds 4      ; c_gap56[2]
                                    182 ; calibration temps ALIAS the refine scratch (r_*): refine returns before
                                    183 ; calibrate runs and nothing else touches r_* -- zero extra zero-page.
                           000030   184 w_llo   =    r_lo        ; label_interval lo out (2)  [r_lo+0..1]
                           000032   185 w_lhi   =    r_lo+2      ; label_interval hi out (2)  [r_lo+2..3]
                           000034   186 m_la    =    r_lo+4      ; cal 'a' argument (2)       [r_lo+4..5]
                           000036   187 m_f     =    r_lo+6      ; family index (1)           [r_lo+6]
                           000037   188 m_x0    =    r_lo+7      ; theta56 x0 (2)             [r_lo+7..8]
                           00003A   189 m_x1    =    r_hi        ; theta56 x1 (2)             [r_hi+0..1]
                           00003C   190 m_zlo   =    r_hi+2      ; (2)                        [r_hi+2..3]
                           00003E   191 m_zhi   =    r_hi+4      ; (2)                        [r_hi+4..5]
                           000040   192 m_th    =    r_hi+6      ; theta (2)                  [r_hi+6..7]
                           000042   193 m_hv    =    r_hi+8      ; have_theta (1)             [r_hi+8]
                           00004B   194 m_prev  =    r_dy+1      ; (2)                        [r_dy+1..2]
                           000044   195 m_blo2  =    r_melo      ; best_lo (2)
                           000046   196 m_bhi2  =    r_mehi      ; best_hi (2)
                                    197 ; chase temps ALIAS dead scratch the same way: m_cp lives in the udiv32
                                    198 ; dividend m_n, whose only users are seed/refine/mediv (all returned
                                    199 ; before the chase) and dec_eps_centi (called only after ws_decode_ex
                                    200 ; returns, when the chase is over) -- zero extra zero-page for the v2.2
                                    201 ; 4-byte check block.
                           000024   202 m_cp    =    m_n         ; chase C' bytes (4; g_CHK = 3 or 4 used)
                                    203                          ;                            [m_n+0..3]
                           000048   204 m_bg    =    r_de        ; (2)
                           00004A   205 m_no    =    r_dy        ; nocc (1)                   [r_dy+0]
                           00004E   206 m_wlo   =    r_dk        ; (2)                        [r_dk+0..1]
                           000050   207 m_whi   =    r_dk+2      ; (2)                        [r_dk+2..3]
                           000058   208 m_top   =    r_myhi      ; (2)                        [r_myhi+0..1]
                           000052   209 m_htp   =    r_me        ; have_top (1)
                           000053   210 m_cl1   =    r_me+1      ; clear1 (1)
                           000054   211 m_bb    =    r_mylo      ; hist bin iterator (1)      [r_mylo+0]
                           000055   212 m_hx    =    r_mylo+1    ; hist/labx index base (2)   [r_mylo+1..2]
                                    213 
                                    214 ; indexed-only arrays: no short-form benefit, so they live in REL DATA
                                    215 ; (keeps the zero page under 255 B)
                                    216     .area DATA
      0001C9                        217 d_costs: .ds 32     ; u16 costs[16]
      0001E9                        218 d_sm:    .ds 32     ; u16 suffix-min over [lo,hi]
      000209                        219 zc_t:    .ds 10     ; v_cand_t[5]
      000213                        220 zc_m:    .ds 5      ; v_cand_m[5]
      000218                        221 zc_d:    .ds 5      ; ch_isd[5]
                                    222 
                                    223     .area DZP
                                    224 
                                    225     .area CODE
                                    226 
                                    227 ; ---------------------------------------------------------------- mul16
                                    228 ; m_a * m_b (u16 x u16) -> m_p (u32).  Clobbers A, X.
      0081E8                        229 mul16:
      0081E8 B6 02            [ 1]  230     ld      a, *m_a+1
      0081EA 97               [ 1]  231     ld      xl, a
      0081EB B6 04            [ 1]  232     ld      a, *m_b+1
      0081ED 42               [ 4]  233     mul     x, a                ; aL*bL
      0081EE BF 07            [ 2]  234     ldw     *m_p+2, x
      0081F0 B6 01            [ 1]  235     ld      a, *m_a
      0081F2 97               [ 1]  236     ld      xl, a
      0081F3 B6 03            [ 1]  237     ld      a, *m_b
      0081F5 42               [ 4]  238     mul     x, a                ; aH*bH
      0081F6 BF 05            [ 2]  239     ldw     *m_p, x
      0081F8 B6 02            [ 1]  240     ld      a, *m_a+1
      0081FA 97               [ 1]  241     ld      xl, a
      0081FB B6 03            [ 1]  242     ld      a, *m_b
      0081FD 42               [ 4]  243     mul     x, a                ; aL*bH
      0081FE CD 82 07         [ 4]  244     call    mulacc
      008201 B6 01            [ 1]  245     ld      a, *m_a
      008203 97               [ 1]  246     ld      xl, a
      008204 B6 04            [ 1]  247     ld      a, *m_b+1
      008206 42               [ 4]  248     mul     x, a                ; aH*bL
      008207                        249 mulacc:                         ; m_p[0..2] += X<<8 (fall-through reuse)
      008207 89               [ 2]  250     pushw   x                   ; (1,sp) = XH, (2,sp) = XL
      008208 B6 07            [ 1]  251     ld      a, *m_p+2
      00820A 1B 02            [ 1]  252     add     a, (2, sp)
      00820C B7 07            [ 1]  253     ld      *m_p+2, a
      00820E B6 06            [ 1]  254     ld      a, *m_p+1
      008210 19 01            [ 1]  255     adc     a, (1, sp)
      008212 B7 06            [ 1]  256     ld      *m_p+1, a
      008214 B6 05            [ 1]  257     ld      a, *m_p
      008216 A9 00            [ 1]  258     adc     a, #0
      008218 B7 05            [ 1]  259     ld      *m_p, a
      00821A 85               [ 2]  260     popw    x
      00821B 81               [ 4]  261     ret
                                    262 
                                    263 ; ---------------------------------------------------------------- mr16
                                    264 ; X = t (u16 cycles) -> m_y = Y:X = ((u32)t * g_K >> 11) + g_tau  (s32),
                                    265 ; exactly decode.c map_raw().  Clobbers A, X, Y.
      00821C                        266 mr16:
      00821C BF 01            [ 2]  267     ldw     *m_a, x
      00821E CE 01 14         [ 2]  268     ldw     x, _g_K
      008221 BF 03            [ 2]  269     ldw     *m_b, x
      008223 CD 81 E8         [ 4]  270     call    mul16               ; m_p = t*K  (< 2^31)
      008226 CD 86 7E         [ 4]  271     call    shp11               ; A:X = m_p >> 11 (< 2^20)
      008229 3F 09            [ 1]  272     clr     *m_y
      00822B B7 0A            [ 1]  273     ld      *m_y+1, a
      00822D BF 0B            [ 2]  274     ldw     *m_y+2, x
                                    275     ; m_y += sext(g_tau)
      00822F C6 01 16         [ 1]  276     ld      a, _g_tau
      008232 48               [ 1]  277     sll     a                       ; C = sign bit
      008233 4F               [ 1]  278     clr     a
      008234 A2 00            [ 1]  279     sbc     a, #0                   ; A = 0xFF if tau < 0 else 0
      008236 B7 0D            [ 1]  280     ld      *m_s, a
      008238 B6 0C            [ 1]  281     ld      a, *m_y+3
      00823A CB 01 17         [ 1]  282     add     a, _g_tau+1
      00823D B7 0C            [ 1]  283     ld      *m_y+3, a
      00823F B6 0B            [ 1]  284     ld      a, *m_y+2
      008241 C9 01 16         [ 1]  285     adc     a, _g_tau
      008244 B7 0B            [ 1]  286     ld      *m_y+2, a
      008246 B6 0A            [ 1]  287     ld      a, *m_y+1
      008248 B9 0D            [ 1]  288     adc     a, *m_s
      00824A B7 0A            [ 1]  289     ld      *m_y+1, a
      00824C B6 09            [ 1]  290     ld      a, *m_y
      00824E B9 0D            [ 1]  291     adc     a, *m_s
      008250 B7 09            [ 1]  292     ld      *m_y, a
      008252 90 BE 09         [ 2]  293     ldw     y, *m_y
      008255 BE 0B            [ 2]  294     ldw     x, *m_y+2
      008257 81               [ 4]  295     ret
                                    296 
                                    297 ; ---------------------------------------------------------------- ss_init
      008258                        298 _ss_init:
      008258 CD 95 3F         [ 4]  299     call    _scan_init
      00825B 5F               [ 1]  300     clrw    x
      00825C BF 0E            [ 2]  301     ldw     *q_yprev, x
      00825E BF 10            [ 2]  302     ldw     *q_yprev+2, x
      008260 BF 12            [ 2]  303     ldw     *q_n, x
      008262 BF 16            [ 2]  304     ldw     *q_pk0, x
      008264 BF 18            [ 2]  305     ldw     *q_pu, x
      008266 BF 1A            [ 2]  306     ldw     *q_pv, x
      008268 3F 1C            [ 1]  307     clr     *q_pfam
      00826A 3F 14            [ 1]  308     clr     *q_have
      00826C 3F 15            [ 1]  309     clr     *q_pend
      00826E 3F 1D            [ 1]  310     clr     *q_done
      008270 81               [ 4]  311     ret
                                    312 
                                    313 ; ---------------------------------------------------------------- helpers
                                    314 ; emit$: X = k1 candidate (uncapped n); writes caller's Seg from the
                                    315 ; pending slot with k1 = min(X, NB).  Clobbers A, X, Y.
      008271                        316 emit:
      008271 C3 80 95         [ 2]  317     cpw     x, _g_NB
      008274 25 03            [ 1]  318     jrc     00001$
      008276 CE 80 95         [ 2]  319     ldw     x, _g_NB
      008279                        320 00001$:
      008279 90 BE 1E         [ 2]  321     ldw     y, *m_out
      00827C 90 EF 02         [ 2]  322     ldw     (2, y), x               ; k1
      00827F BE 16            [ 2]  323     ldw     x, *q_pk0
      008281 90 FF            [ 2]  324     ldw     (y), x                  ; k0
      008283 BE 18            [ 2]  325     ldw     x, *q_pu
      008285 90 EF 04         [ 2]  326     ldw     (4, y), x               ; u
      008288 BE 1A            [ 2]  327     ldw     x, *q_pv
      00828A 90 EF 06         [ 2]  328     ldw     (6, y), x               ; v
      00828D B6 1C            [ 1]  329     ld      a, *q_pfam
      00828F 90 E7 08         [ 1]  330     ld      (8, y), a               ; fam
      008292 81               [ 4]  331     ret
                                    332 
                                    333 ; setp$: X = k; pending <- (k, u = yfa - base, v = yfb - base, sfa) with
                                    334 ; base = BIAS + k*512 = (k+1)<<9, all in low-16 (s16 result by contract).
      008293                        335 setp:
      008293 BF 16            [ 2]  336     ldw     *q_pk0, x
      008295 5C               [ 1]  337     incw    x
      008296 9F               [ 1]  338     ld      a, xl
      008297 5F               [ 1]  339     clrw    x
      008298 95               [ 1]  340     ld      xh, a
      008299 58               [ 2]  341     sllw    x                   ; X = low16((k+1) << 9)
      00829A BF 03            [ 2]  342     ldw     *m_b, x
      00829C BE 20            [ 2]  343     ldw     x, *m_fa
      00829E 72 B0 00 03      [ 2]  344     subw    x, m_b
      0082A2 BF 18            [ 2]  345     ldw     *q_pu, x
      0082A4 BE 22            [ 2]  346     ldw     x, *m_fb
      0082A6 72 B0 00 03      [ 2]  347     subw    x, m_b
      0082AA BF 1A            [ 2]  348     ldw     *q_pv, x
      0082AC C6 00 C3         [ 1]  349     ld      a, _scan_sfa
      0082AF B7 1C            [ 1]  350     ld      *q_pfam, a
      0082B1 81               [ 4]  351     ret
                                    352 
                                    353 ; ---------------------------------------------------------------- ss_next
                                    354 ; X = Seg* out -> A = 1 (segment written) / 0 (stream end).
      0082B2                        355 _ss_next:
      0082B2 BF 1E            [ 2]  356     ldw     *m_out, x
      0082B4                        357 00010$:                         ; while (!src_done)
      0082B4 3D 1D            [ 1]  358     tnz     *q_done
      0082B6 27 03            [ 1]  359     jreq    00040$
      0082B8 CC 83 84         [ 2]  360     jp      00030$
      0082BB                        361 00040$:
      0082BB CD 95 5B         [ 4]  362     call    _scan_next
      0082BE 4D               [ 1]  363     tnz     a
      0082BF 26 07            [ 1]  364     jrne    00011$
      0082C1 35 01 00 1D      [ 1]  365     mov     q_done, #1
      0082C5 CC 83 84         [ 2]  366     jp      00030$
      0082C8                        367 00011$:
                                    368     ; y = clamp0(map_raw((ra+rb)>>1))
      0082C8 CE 00 BB         [ 2]  369     ldw     x, _scan_ra
      0082CB 72 BB 00 BD      [ 2]  370     addw    x, _scan_rb
      0082CF 54               [ 2]  371     srlw    x
      0082D0 CD 82 1C         [ 4]  372     call    mr16
      0082D3 3D 09            [ 1]  373     tnz     *m_y
      0082D5 2A 05            [ 1]  374     jrpl    00012$
      0082D7 5F               [ 1]  375     clrw    x                   ; y < 0 -> 0
      0082D8 BF 09            [ 2]  376     ldw     *m_y, x
      0082DA BF 0B            [ 2]  377     ldw     *m_y+2, x
      0082DC                        378 00012$:
                                    379     ; if ((u32)y > y_end) { done; break; }   (C set iff yend < y)
      0082DC C6 80 9A         [ 1]  380     ld      a, _g_yend+3
      0082DF B0 0C            [ 1]  381     sub     a, *m_y+3
      0082E1 C6 80 99         [ 1]  382     ld      a, _g_yend+2
      0082E4 B2 0B            [ 1]  383     sbc     a, *m_y+2
      0082E6 C6 80 98         [ 1]  384     ld      a, _g_yend+1
      0082E9 B2 0A            [ 1]  385     sbc     a, *m_y+1
      0082EB C6 80 97         [ 1]  386     ld      a, _g_yend
      0082EE B2 09            [ 1]  387     sbc     a, *m_y
      0082F0 24 07            [ 1]  388     jrnc    00013$
      0082F2 35 01 00 1D      [ 1]  389     mov     q_done, #1
      0082F6 CC 83 84         [ 2]  390     jp      00030$
      0082F9                        391 00013$:
                                    392     ; have_y / gap accounting
      0082F9 3D 14            [ 1]  393     tnz     *q_have
      0082FB 26 09            [ 1]  394     jrne    00014$
      0082FD 5F               [ 1]  395     clrw    x
      0082FE BF 12            [ 2]  396     ldw     *q_n, x
      008300 35 01 00 14      [ 1]  397     mov     q_have, #1
      008304 20 1A            [ 2]  398     jra     00015$
      008306                        399 00014$:
                                    400     ; d = y - y_prev (>= 0, < 2^20); dn = (d + 256) >> 9; n += dn
      008306 BE 0B            [ 2]  401     ldw     x, *m_y+2
      008308 72 B0 00 10      [ 2]  402     subw    x, q_yprev+2
      00830C B6 0A            [ 1]  403     ld      a, *m_y+1
      00830E B2 0F            [ 1]  404     sbc     a, *q_yprev+1           ; A:X = d (24-bit, byte0 of both is 0)
      008310 1C 01 00         [ 2]  405     addw    x, #0x0100
      008313 A9 00            [ 1]  406     adc     a, #0
      008315 5E               [ 1]  407     swapw   x                   ; XL = old XH
      008316 95               [ 1]  408     ld      xh, a                   ; X = (A:XH_old) = (d+256) >> 8
      008317 54               [ 2]  409     srlw    x                   ; X = dn
      008318 27 06            [ 1]  410     jreq    00015$
      00831A 72 BB 00 12      [ 2]  411     addw    x, q_n
      00831E BF 12            [ 2]  412     ldw     *q_n, x
      008320                        413 00015$:
                                    414     ; y_prev = y; yfa/yfb low16
      008320 BE 09            [ 2]  415     ldw     x, *m_y
      008322 BF 0E            [ 2]  416     ldw     *q_yprev, x
      008324 BE 0B            [ 2]  417     ldw     x, *m_y+2
      008326 BF 10            [ 2]  418     ldw     *q_yprev+2, x
      008328 CE 00 BF         [ 2]  419     ldw     x, _scan_fa
      00832B CD 82 1C         [ 4]  420     call    mr16
      00832E BE 0B            [ 2]  421     ldw     x, *m_y+2
      008330 BF 20            [ 2]  422     ldw     *m_fa, x
      008332 CE 00 C1         [ 2]  423     ldw     x, _scan_fb
      008335 CD 82 1C         [ 4]  424     call    mr16
      008338 BE 0B            [ 2]  425     ldw     x, *m_y+2
      00833A BF 22            [ 2]  426     ldw     *m_fb, x
                                    427     ; dispatch on pend / n
      00833C 3D 15            [ 1]  428     tnz     *q_pend
      00833E 27 2B            [ 1]  429     jreq    00020$
      008340 BE 12            [ 2]  430     ldw     x, *q_n
      008342 B3 16            [ 2]  431     cpw     x, *q_pk0
      008344 26 08            [ 1]  432     jrne    00016$
                                    433     ; spurious split: refresh the pending slot in place
      008346 BE 16            [ 2]  434     ldw     x, *q_pk0
      008348 CD 82 93         [ 4]  435     call    setp
      00834B CC 82 B4         [ 2]  436     jp      00010$
      00834E                        437 00016$:
                                    438     ; emit pending; k1 = min(n, NB)
      00834E BE 12            [ 2]  439     ldw     x, *q_n
      008350 CD 82 71         [ 4]  440     call    emit
      008353 BE 12            [ 2]  441     ldw     x, *q_n
      008355 C3 80 95         [ 2]  442     cpw     x, _g_NB
      008358 25 09            [ 1]  443     jrc     00017$
      00835A 3F 15            [ 1]  444     clr     *q_pend
      00835C 35 01 00 1D      [ 1]  445     mov     q_done, #1
      008360 A6 01            [ 1]  446     ld      a, #1
      008362 81               [ 4]  447     ret
      008363                        448 00017$:
      008363 BE 12            [ 2]  449     ldw     x, *q_n                 ; roll pending to n (pend stays 1)
      008365 CD 82 93         [ 4]  450     call    setp
      008368 A6 01            [ 1]  451     ld      a, #1
      00836A 81               [ 4]  452     ret
      00836B                        453 00020$:
                                    454     ; no pending segment yet
      00836B BE 12            [ 2]  455     ldw     x, *q_n
      00836D C3 80 95         [ 2]  456     cpw     x, _g_NB
      008370 25 06            [ 1]  457     jrc     00021$
      008372 35 01 00 1D      [ 1]  458     mov     q_done, #1
      008376 20 0C            [ 2]  459     jra     00030$
      008378                        460 00021$:
      008378 BE 12            [ 2]  461     ldw     x, *q_n
      00837A CD 82 93         [ 4]  462     call    setp
      00837D 35 01 00 15      [ 1]  463     mov     q_pend, #1
      008381 CC 82 B4         [ 2]  464     jp      00010$
                                    465 
      008384                        466 00030$:                         ; stream end: flush the pending segment
      008384 3D 15            [ 1]  467     tnz     *q_pend
      008386 27 0B            [ 1]  468     jreq    00031$
      008388 3F 15            [ 1]  469     clr     *q_pend
      00838A CE 80 95         [ 2]  470     ldw     x, _g_NB                ; tail k1 = NB
      00838D CD 82 71         [ 4]  471     call    emit
      008390 A6 01            [ 1]  472     ld      a, #1
      008392 81               [ 4]  473     ret
      008393                        474 00031$:
      008393 4F               [ 1]  475     clr     a
      008394 81               [ 4]  476     ret
                                    477 
                                    478 ; ======================================================================
                                    479 ; refine() -- P2 residual-regression lock refinement, bit-exact port of
                                    480 ; decode.c's C version.  Uses mr16/mul16 above plus udiv32 below.
                                    481 ; Range notes (reference assert battery): e in [-256,255]; |me| <= 256 so
                                    482 ; de fits s16; sy sums < 2^27; my quotients < 2^20; K*de < 2^25;
                                    483 ; |de*(my-tau)| < 2^31 (asserted); dtau/tau commits are exact in low-16
                                    484 ; (C truncates to int16_t).
                                    485 ; ======================================================================
                                    486 
                                    487     .globl _refine
                                    488     .globl _g_ymid
                                    489 
                                    490     .area CODE
                                    491 
                                    492 ; ---------------------------------------------------------------- udiv32
                                    493 ; m_n / m_d -> quotient in m_n, remainder in m_r.  m_d preserved.
                                    494 ; Clobbers A, X, Y, m_s.
      008395                        495 udiv32:
      008395 3F 2C            [ 1]  496     clr     *m_r
      008397 3F 2D            [ 1]  497     clr     *m_r+1
      008399 3F 2E            [ 1]  498     clr     *m_r+2
      00839B 3F 2F            [ 1]  499     clr     *m_r+3
      00839D 35 20 00 0D      [ 1]  500     mov     m_s, #32
      0083A1                        501 00050$:
      0083A1 38 27            [ 1]  502     sll     *m_n+3                  ; N <<= 1, MSB -> C
      0083A3 39 26            [ 1]  503     rlc     *m_n+2
      0083A5 39 25            [ 1]  504     rlc     *m_n+1
      0083A7 39 24            [ 1]  505     rlc     *m_n
      0083A9 39 2F            [ 1]  506     rlc     *m_r+3                  ; C -> R
      0083AB 39 2E            [ 1]  507     rlc     *m_r+2
      0083AD 39 2D            [ 1]  508     rlc     *m_r+1
      0083AF 39 2C            [ 1]  509     rlc     *m_r
      0083B1 B6 2F            [ 1]  510     ld      a, *m_r+3               ; R - D (trial)
      0083B3 B0 2B            [ 1]  511     sub     a, *m_d+3
      0083B5 97               [ 1]  512     ld      xl, a
      0083B6 B6 2E            [ 1]  513     ld      a, *m_r+2
      0083B8 B2 2A            [ 1]  514     sbc     a, *m_d+2
      0083BA 95               [ 1]  515     ld      xh, a
      0083BB B6 2D            [ 1]  516     ld      a, *m_r+1
      0083BD B2 29            [ 1]  517     sbc     a, *m_d+1
      0083BF 90 97            [ 1]  518     ld      yl, a
      0083C1 B6 2C            [ 1]  519     ld      a, *m_r
      0083C3 B2 28            [ 1]  520     sbc     a, *m_d
      0083C5 25 0A            [ 1]  521     jrc     00051$              ; R < D: restore (keep old R)
      0083C7 B7 2C            [ 1]  522     ld      *m_r, a
      0083C9 90 9F            [ 1]  523     ld      a, yl
      0083CB B7 2D            [ 1]  524     ld      *m_r+1, a
      0083CD BF 2E            [ 2]  525     ldw     *m_r+2, x
      0083CF 3C 27            [ 1]  526     inc     *m_n+3                  ; quotient bit (bit0 is 0 after sll)
      0083D1                        527 00051$:
      0083D1 3A 0D            [ 1]  528     dec     *m_s
      0083D3 26 CC            [ 1]  529     jrne    00050$
      0083D5 81               [ 4]  530     ret
                                    531 
                                    532 ; negmn: m_n = -m_n (32-bit two's complement)
      0083D6                        533 negmn:
      0083D6 4F               [ 1]  534     clr     a
      0083D7 B0 27            [ 1]  535     sub     a, *m_n+3
      0083D9 B7 27            [ 1]  536     ld      *m_n+3, a
      0083DB 4F               [ 1]  537     clr     a
      0083DC B2 26            [ 1]  538     sbc     a, *m_n+2
      0083DE B7 26            [ 1]  539     ld      *m_n+2, a
      0083E0 4F               [ 1]  540     clr     a
      0083E1 B2 25            [ 1]  541     sbc     a, *m_n+1
      0083E3 B7 25            [ 1]  542     ld      *m_n+1, a
      0083E5 4F               [ 1]  543     clr     a
      0083E6 B2 24            [ 1]  544     sbc     a, *m_n
      0083E8 B7 24            [ 1]  545     ld      *m_n, a
      0083EA 81               [ 4]  546     ret
                                    547 
                                    548 ; accum: Y = block (r_lo/r_hi), X = e (s16), m_y = y (u32 clamped):
                                    549 ;   se += sext(e); sy += y; n++
      0083EB                        550 accum:
      0083EB 9E               [ 1]  551     ld      a, xh
      0083EC 48               [ 1]  552     sll     a
      0083ED 4F               [ 1]  553     clr     a
      0083EE A2 00            [ 1]  554     sbc     a, #0
      0083F0 B7 0D            [ 1]  555     ld      *m_s, a                 ; sign byte of e
      0083F2 89               [ 2]  556     pushw   x                   ; (1,sp)=eH (2,sp)=eL
      0083F3 90 E6 03         [ 1]  557     ld      a, (3, y)
      0083F6 1B 02            [ 1]  558     add     a, (2, sp)
      0083F8 90 E7 03         [ 1]  559     ld      (3, y), a
      0083FB 90 E6 02         [ 1]  560     ld      a, (2, y)
      0083FE 19 01            [ 1]  561     adc     a, (1, sp)
      008400 90 E7 02         [ 1]  562     ld      (2, y), a
      008403 90 E6 01         [ 1]  563     ld      a, (1, y)
      008406 B9 0D            [ 1]  564     adc     a, *m_s
      008408 90 E7 01         [ 1]  565     ld      (1, y), a
      00840B 90 F6            [ 1]  566     ld      a, (y)
      00840D B9 0D            [ 1]  567     adc     a, *m_s
      00840F 90 F7            [ 1]  568     ld      (y), a
      008411 85               [ 2]  569     popw    x
      008412 90 E6 07         [ 1]  570     ld      a, (7, y)
      008415 BB 0C            [ 1]  571     add     a, *m_y+3
      008417 90 E7 07         [ 1]  572     ld      (7, y), a
      00841A 90 E6 06         [ 1]  573     ld      a, (6, y)
      00841D B9 0B            [ 1]  574     adc     a, *m_y+2
      00841F 90 E7 06         [ 1]  575     ld      (6, y), a
      008422 90 E6 05         [ 1]  576     ld      a, (5, y)
      008425 B9 0A            [ 1]  577     adc     a, *m_y+1
      008427 90 E7 05         [ 1]  578     ld      (5, y), a
      00842A 90 E6 04         [ 1]  579     ld      a, (4, y)
      00842D B9 09            [ 1]  580     adc     a, *m_y
      00842F 90 E7 04         [ 1]  581     ld      (4, y), a
      008432 90 E6 09         [ 1]  582     ld      a, (9, y)               ; n++ (16-bit, byte-wise: no LDW X,(o,Y))
      008435 AB 01            [ 1]  583     add     a, #1
      008437 90 E7 09         [ 1]  584     ld      (9, y), a
      00843A 90 E6 08         [ 1]  585     ld      a, (8, y)
      00843D A9 00            [ 1]  586     adc     a, #0
      00843F 90 E7 08         [ 1]  587     ld      (8, y), a
      008442 81               [ 4]  588     ret
                                    589 
                                    590 
                                    591 ; ---- relocated into the vector-table gap (vectors_prod.s): 0x8004..0x8063
                                    592     .area VGAP (ABS)
      008004                        593     .org 0x8004
                                    594 
                                    595     .globl sot                  ; exported ONLY as the guard_prod.py anchor
                                    596                                 ; for the VGAP window check (ABS areas
                                    597                                 ; print addr 0 in sdld maps)
      008004 00 04 09 0D 11 15 1B   598 sot: .db 0, 4, 9, 13, 17, 21, 27, 32       ; O_CY[8]
             20
      00800C 00 FF 00 02 00 00 00   599 swt: .db 0, 0xFF, 0, 2, 0, 0, 0, 1         ; W_CY[8] (s8)
             01
                                    600 
                                    601 ; mediv: X = block -> X = se/n as s16 (C truncation; |result| <= 256)
      008014                        602 mediv:
      008014 89               [ 2]  603     pushw   x                   ; block ptr at (1,sp)
      008015 FE               [ 2]  604     ldw     x, (x)
      008016 BF 24            [ 2]  605     ldw     *m_n, x
      008018 1E 01            [ 2]  606     ldw     x, (1, sp)
      00801A EE 02            [ 2]  607     ldw     x, (2, x)
      00801C BF 26            [ 2]  608     ldw     *m_n+2, x
      00801E 5F               [ 1]  609     clrw    x
      00801F BF 28            [ 2]  610     ldw     *m_d, x
      008021 1E 01            [ 2]  611     ldw     x, (1, sp)
      008023 EE 08            [ 2]  612     ldw     x, (8, x)
      008025 BF 2A            [ 2]  613     ldw     *m_d+2, x
      008027 85               [ 2]  614     popw    x
      008028 3F 5C            [ 1]  615     clr     *r_sgn
      00802A 3D 24            [ 1]  616     tnz     *m_n
      00802C 2A 07            [ 1]  617     jrpl    00055$
      00802E 35 01 00 5C      [ 1]  618     mov     r_sgn, #1
      008032 CD 83 D6         [ 4]  619     call    negmn
      008035                        620 00055$:
      008035 CD 83 95         [ 4]  621     call    udiv32
      008038 BE 26            [ 2]  622     ldw     x, *m_n+2
      00803A 3D 5C            [ 1]  623     tnz     *r_sgn
      00803C 27 01            [ 1]  624     jreq    00056$
      00803E 50               [ 2]  625     negw    x
      00803F                        626 00056$:
      00803F 81               [ 4]  627     ret
                                    628 
                                    629 ; mydiv: X = block -> m_n = sy/n (u32)
      008040                        630 mydiv:
      008040 89               [ 2]  631     pushw   x
      008041 EE 04            [ 2]  632     ldw     x, (4, x)
      008043 BF 24            [ 2]  633     ldw     *m_n, x
      008045 1E 01            [ 2]  634     ldw     x, (1, sp)
      008047 EE 06            [ 2]  635     ldw     x, (6, x)
      008049 BF 26            [ 2]  636     ldw     *m_n+2, x
      00804B 5F               [ 1]  637     clrw    x
      00804C BF 28            [ 2]  638     ldw     *m_d, x
      00804E 1E 01            [ 2]  639     ldw     x, (1, sp)
      008050 EE 08            [ 2]  640     ldw     x, (8, x)
      008052 BF 2A            [ 2]  641     ldw     *m_d+2, x
      008054 85               [ 2]  642     popw    x
      008055 CC 83 95         [ 2]  643     jp      udiv32
                                    644 
                                    645 ; hix: A = f (0/1) -> X = f*64 (c_hist row base within ov.hist).
                                    646 ; Lives in the vector gap: 7 bytes that the REL side no longer pays for.
      008058                        647 hix:
      008058 5F               [ 1]  648     clrw    x
      008059 4D               [ 1]  649     tnz     a
      00805A 27 03            [ 1]  650     jreq    00510$
      00805C AE 00 40         [ 2]  651     ldw     x, #64
      00805F                        652 00510$:
      00805F 81               [ 4]  653     ret
                                    654 
                                    655 
                                    656     .area CODE
                                    657 
                                    658 ; ---------------------------------------------------------------- refine
      008443                        659 _refine:
      008443 AE 00 14         [ 2]  660     ldw     x, #20                  ; zero r_lo + r_hi (adjacent)
      008446                        661 00060$:
      008446 72 4F 00 2F      [ 1]  662     clr     (r_lo-1, x)
      00844A 5A               [ 2]  663     decw    x
      00844B 26 F9            [ 1]  664     jrne    00060$
      00844D CD 95 3F         [ 4]  665     call    _scan_init
      008450                        666 00061$:                         ; pulse loop
      008450 CD 95 5B         [ 4]  667     call    _scan_next
      008453 4D               [ 1]  668     tnz     a
      008454 27 6A            [ 1]  669     jreq    00070$
      008456 CE 00 BB         [ 2]  670     ldw     x, _scan_ra
      008459 72 BB 00 BD      [ 2]  671     addw    x, _scan_rb
      00845D 54               [ 2]  672     srlw    x
      00845E CD 82 1C         [ 4]  673     call    mr16
      008461 3D 09            [ 1]  674     tnz     *m_y
      008463 2A 05            [ 1]  675     jrpl    00062$
      008465 5F               [ 1]  676     clrw    x                   ; clamp y >= 0
      008466 BF 09            [ 2]  677     ldw     *m_y, x
      008468 BF 0B            [ 2]  678     ldw     *m_y+2, x
      00846A                        679 00062$:
      00846A C6 80 9A         [ 1]  680     ld      a, _g_yend+3            ; if y > y_end: stop accumulating
      00846D B0 0C            [ 1]  681     sub     a, *m_y+3
      00846F C6 80 99         [ 1]  682     ld      a, _g_yend+2
      008472 B2 0B            [ 1]  683     sbc     a, *m_y+2
      008474 C6 80 98         [ 1]  684     ld      a, _g_yend+1
      008477 B2 0A            [ 1]  685     sbc     a, *m_y+1
      008479 C6 80 97         [ 1]  686     ld      a, _g_yend
      00847C B2 09            [ 1]  687     sbc     a, *m_y
      00847E 25 40            [ 1]  688     jrc     00070$
                                    689     ; q = (y + 256) >> 9 ; e = low16(y) - low16(q << 9)
      008480 BE 0B            [ 2]  690     ldw     x, *m_y+2
      008482 B6 0A            [ 1]  691     ld      a, *m_y+1
      008484 1C 01 00         [ 2]  692     addw    x, #0x0100
      008487 A9 00            [ 1]  693     adc     a, #0
      008489 5E               [ 1]  694     swapw   x
      00848A 95               [ 1]  695     ld      xh, a
      00848B 54               [ 2]  696     srlw    x                   ; X = q
      00848C 9F               [ 1]  697     ld      a, xl
      00848D 5F               [ 1]  698     clrw    x
      00848E 95               [ 1]  699     ld      xh, a
      00848F 58               [ 2]  700     sllw    x                   ; X = low16(q << 9)
      008490 BF 03            [ 2]  701     ldw     *m_b, x
      008492 BE 0B            [ 2]  702     ldw     x, *m_y+2
      008494 72 B0 00 03      [ 2]  703     subw    x, m_b              ; X = e (s16 exact)
                                    704     ; block = (y < mid_u) ? r_lo : r_hi
      008498 B6 0C            [ 1]  705     ld      a, *m_y+3
      00849A C0 80 9E         [ 1]  706     sub     a, _g_ymid+3
      00849D B6 0B            [ 1]  707     ld      a, *m_y+2
      00849F C2 80 9D         [ 1]  708     sbc     a, _g_ymid+2
      0084A2 B6 0A            [ 1]  709     ld      a, *m_y+1
      0084A4 C2 80 9C         [ 1]  710     sbc     a, _g_ymid+1
      0084A7 B6 09            [ 1]  711     ld      a, *m_y
      0084A9 C2 80 9B         [ 1]  712     sbc     a, _g_ymid
      0084AC 25 06            [ 1]  713     jrc     00063$
      0084AE 90 AE 00 3A      [ 2]  714     ldw     y, #r_hi
      0084B2 20 04            [ 2]  715     jra     00064$
      0084B4                        716 00063$:
      0084B4 90 AE 00 30      [ 2]  717     ldw     y, #r_lo
      0084B8                        718 00064$:
      0084B8 CD 83 EB         [ 4]  719     call    accum
      0084BB 20 93            [ 2]  720     jra     00061$
                                    721 
      0084BD                        722 00069$:
      0084BD CC 86 7D         [ 2]  723     jp      00099$              ; short-branch trampoline to the ret
      0084C0                        724 00070$:                         ; stats
      0084C0 BE 38            [ 2]  725     ldw     x, *r_lo+8
      0084C2 A3 00 02         [ 2]  726     cpw     x, #2
      0084C5 25 F6            [ 1]  727     jrc     00069$
      0084C7 BE 42            [ 2]  728     ldw     x, *r_hi+8
      0084C9 A3 00 02         [ 2]  729     cpw     x, #2
      0084CC 25 EF            [ 1]  730     jrc     00069$
      0084CE AE 00 30         [ 2]  731     ldw     x, #r_lo
      0084D1 CD 80 14         [ 4]  732     call    mediv
      0084D4 BF 44            [ 2]  733     ldw     *r_melo, x
      0084D6 AE 00 3A         [ 2]  734     ldw     x, #r_hi
      0084D9 CD 80 14         [ 4]  735     call    mediv
      0084DC BF 46            [ 2]  736     ldw     *r_mehi, x
      0084DE AE 00 30         [ 2]  737     ldw     x, #r_lo
      0084E1 CD 80 40         [ 4]  738     call    mydiv
      0084E4 BE 24            [ 2]  739     ldw     x, *m_n
      0084E6 BF 54            [ 2]  740     ldw     *r_mylo, x
      0084E8 BE 26            [ 2]  741     ldw     x, *m_n+2
      0084EA BF 56            [ 2]  742     ldw     *r_mylo+2, x
      0084EC AE 00 3A         [ 2]  743     ldw     x, #r_hi
      0084EF CD 80 40         [ 4]  744     call    mydiv
      0084F2 BE 24            [ 2]  745     ldw     x, *m_n
      0084F4 BF 58            [ 2]  746     ldw     *r_myhi, x
      0084F6 BE 26            [ 2]  747     ldw     x, *m_n+2
      0084F8 BF 5A            [ 2]  748     ldw     *r_myhi+2, x
      0084FA BE 46            [ 2]  749     ldw     x, *r_mehi              ; de = me_hi - me_lo (s16, |de| <= 512)
      0084FC 72 B0 00 44      [ 2]  750     subw    x, r_melo
      008500 BF 48            [ 2]  751     ldw     *r_de, x
      008502 B6 5B            [ 1]  752     ld      a, *r_myhi+3            ; dy = my_hi - my_lo (s32)
      008504 B0 57            [ 1]  753     sub     a, *r_mylo+3
      008506 B7 4D            [ 1]  754     ld      *r_dy+3, a
      008508 B6 5A            [ 1]  755     ld      a, *r_myhi+2
      00850A B2 56            [ 1]  756     sbc     a, *r_mylo+2
      00850C B7 4C            [ 1]  757     ld      *r_dy+2, a
      00850E B6 59            [ 1]  758     ld      a, *r_myhi+1
      008510 B2 55            [ 1]  759     sbc     a, *r_mylo+1
      008512 B7 4B            [ 1]  760     ld      *r_dy+1, a
      008514 B6 58            [ 1]  761     ld      a, *r_myhi
      008516 B2 54            [ 1]  762     sbc     a, *r_mylo
      008518 B7 4A            [ 1]  763     ld      *r_dy, a
      00851A 2A 03            [ 1]  764     jrpl    00067$
      00851C CC 86 7D         [ 2]  765     jp      00099$              ; dy < 0
      00851F                        766 00067$:
      00851F B6 4A            [ 1]  767     ld      a, *r_dy
      008521 BA 4B            [ 1]  768     or      a, *r_dy+1
      008523 BA 4C            [ 1]  769     or      a, *r_dy+2
      008525 BA 4D            [ 1]  770     or      a, *r_dy+3
      008527 26 03            [ 1]  771     jrne    00068$
      008529 CC 86 7D         [ 2]  772     jp      00099$              ; dy == 0
      00852C                        773 00068$:
                                    774     ; dk = (K * de) / dy  (sign of de; dy > 0)
      00852C BE 48            [ 2]  775     ldw     x, *r_de
      00852E 3F 5C            [ 1]  776     clr     *r_sgn
      008530 5D               [ 2]  777     tnzw    x
      008531 2A 05            [ 1]  778     jrpl    00071$
      008533 50               [ 2]  779     negw    x
      008534 35 01 00 5C      [ 1]  780     mov     r_sgn, #1
      008538                        781 00071$:
      008538 BF 01            [ 2]  782     ldw     *m_a, x
      00853A CE 01 14         [ 2]  783     ldw     x, _g_K
      00853D BF 03            [ 2]  784     ldw     *m_b, x
      00853F CD 81 E8         [ 4]  785     call    mul16               ; m_p = K * |de| (< 2^25)
      008542 BE 05            [ 2]  786     ldw     x, *m_p
      008544 BF 24            [ 2]  787     ldw     *m_n, x
      008546 BE 07            [ 2]  788     ldw     x, *m_p+2
      008548 BF 26            [ 2]  789     ldw     *m_n+2, x
      00854A BE 4A            [ 2]  790     ldw     x, *r_dy
      00854C BF 28            [ 2]  791     ldw     *m_d, x
      00854E BE 4C            [ 2]  792     ldw     x, *r_dy+2
      008550 BF 2A            [ 2]  793     ldw     *m_d+2, x
      008552 CD 83 95         [ 4]  794     call    udiv32
      008555 3D 5C            [ 1]  795     tnz     *r_sgn
      008557 27 03            [ 1]  796     jreq    00072$
      008559 CD 83 D6         [ 4]  797     call    negmn
      00855C                        798 00072$:
      00855C BE 24            [ 2]  799     ldw     x, *m_n                 ; r_dk = signed dk
      00855E BF 4E            [ 2]  800     ldw     *r_dk, x
      008560 BE 26            [ 2]  801     ldw     x, *m_n+2
      008562 BF 50            [ 2]  802     ldw     *r_dk+2, x
                                    803     ; me = (se_lo + se_hi) / (n_lo + n_hi) -> r_me (s16 exact)
      008564 B6 33            [ 1]  804     ld      a, *r_lo+3
      008566 BB 3D            [ 1]  805     add     a, *r_hi+3
      008568 B7 27            [ 1]  806     ld      *m_n+3, a
      00856A B6 32            [ 1]  807     ld      a, *r_lo+2
      00856C B9 3C            [ 1]  808     adc     a, *r_hi+2
      00856E B7 26            [ 1]  809     ld      *m_n+2, a
      008570 B6 31            [ 1]  810     ld      a, *r_lo+1
      008572 B9 3B            [ 1]  811     adc     a, *r_hi+1
      008574 B7 25            [ 1]  812     ld      *m_n+1, a
      008576 B6 30            [ 1]  813     ld      a, *r_lo
      008578 B9 3A            [ 1]  814     adc     a, *r_hi
      00857A B7 24            [ 1]  815     ld      *m_n, a
      00857C 5F               [ 1]  816     clrw    x
      00857D BF 28            [ 2]  817     ldw     *m_d, x
      00857F BE 38            [ 2]  818     ldw     x, *r_lo+8
      008581 72 BB 00 42      [ 2]  819     addw    x, r_hi+8
      008585 BF 2A            [ 2]  820     ldw     *m_d+2, x
      008587 3F 5C            [ 1]  821     clr     *r_sgn
      008589 3D 24            [ 1]  822     tnz     *m_n
      00858B 2A 07            [ 1]  823     jrpl    00073$
      00858D 35 01 00 5C      [ 1]  824     mov     r_sgn, #1
      008591 CD 83 D6         [ 4]  825     call    negmn
      008594                        826 00073$:
      008594 CD 83 95         [ 4]  827     call    udiv32
      008597 BE 26            [ 2]  828     ldw     x, *m_n+2
      008599 3D 5C            [ 1]  829     tnz     *r_sgn
      00859B 27 01            [ 1]  830     jreq    00074$
      00859D 50               [ 2]  831     negw    x
      00859E                        832 00074$:
      00859E BF 52            [ 2]  833     ldw     *r_me, x
                                    834     ; my = (sy_lo + sy_hi) / n_tot (m_d still holds n_tot)
      0085A0 B6 37            [ 1]  835     ld      a, *r_lo+7
      0085A2 BB 41            [ 1]  836     add     a, *r_hi+7
      0085A4 B7 27            [ 1]  837     ld      *m_n+3, a
      0085A6 B6 36            [ 1]  838     ld      a, *r_lo+6
      0085A8 B9 40            [ 1]  839     adc     a, *r_hi+6
      0085AA B7 26            [ 1]  840     ld      *m_n+2, a
      0085AC B6 35            [ 1]  841     ld      a, *r_lo+5
      0085AE B9 3F            [ 1]  842     adc     a, *r_hi+5
      0085B0 B7 25            [ 1]  843     ld      *m_n+1, a
      0085B2 B6 34            [ 1]  844     ld      a, *r_lo+4
      0085B4 B9 3E            [ 1]  845     adc     a, *r_hi+4
      0085B6 B7 24            [ 1]  846     ld      *m_n, a
      0085B8 CD 83 95         [ 4]  847     call    udiv32              ; m_n = my (u32)
                                    848     ; m2 = my - sext(g_tau)  (s32)
      0085BB C6 01 16         [ 1]  849     ld      a, _g_tau
      0085BE 48               [ 1]  850     sll     a
      0085BF 4F               [ 1]  851     clr     a
      0085C0 A2 00            [ 1]  852     sbc     a, #0
      0085C2 B7 0D            [ 1]  853     ld      *m_s, a
      0085C4 B6 27            [ 1]  854     ld      a, *m_n+3
      0085C6 C0 01 17         [ 1]  855     sub     a, _g_tau+1
      0085C9 B7 27            [ 1]  856     ld      *m_n+3, a
      0085CB B6 26            [ 1]  857     ld      a, *m_n+2
      0085CD C2 01 16         [ 1]  858     sbc     a, _g_tau
      0085D0 B7 26            [ 1]  859     ld      *m_n+2, a
      0085D2 B6 25            [ 1]  860     ld      a, *m_n+1
      0085D4 B2 0D            [ 1]  861     sbc     a, *m_s
      0085D6 B7 25            [ 1]  862     ld      *m_n+1, a
      0085D8 B6 24            [ 1]  863     ld      a, *m_n
      0085DA B2 0D            [ 1]  864     sbc     a, *m_s
      0085DC B7 24            [ 1]  865     ld      *m_n, a
                                    866     ; p_sign = sign(m2) ^ sign(de); |m2| (u24), |de|
      0085DE 3F 5C            [ 1]  867     clr     *r_sgn
      0085E0 3D 24            [ 1]  868     tnz     *m_n
      0085E2 2A 07            [ 1]  869     jrpl    00075$
      0085E4 35 01 00 5C      [ 1]  870     mov     r_sgn, #1
      0085E8 CD 83 D6         [ 4]  871     call    negmn
      0085EB                        872 00075$:
      0085EB BE 48            [ 2]  873     ldw     x, *r_de
      0085ED 5D               [ 2]  874     tnzw    x
      0085EE 2A 07            [ 1]  875     jrpl    00076$
      0085F0 50               [ 2]  876     negw    x
      0085F1 B6 5C            [ 1]  877     ld      a, *r_sgn
      0085F3 A8 01            [ 1]  878     xor     a, #1
      0085F5 B7 5C            [ 1]  879     ld      *r_sgn, a
      0085F7                        880 00076$:
                                    881     ; P = |de| * |m2|  = mul16(|de|, m2_lo16) + (m2_b1 * |de|) << 16
      0085F7 BF 01            [ 2]  882     ldw     *m_a, x                 ; |de|
      0085F9 BE 26            [ 2]  883     ldw     x, *m_n+2
      0085FB BF 03            [ 2]  884     ldw     *m_b, x                 ; m2 low16
      0085FD B6 25            [ 1]  885     ld      a, *m_n+1               ; m2 byte1 (<= 7)
      0085FF 88               [ 1]  886     push    a
      008600 CD 81 E8         [ 4]  887     call    mul16               ; m_p = |de| * lo16
      008603 BE 05            [ 2]  888     ldw     x, *m_p
      008605 BF 24            [ 2]  889     ldw     *m_n, x
      008607 BE 07            [ 2]  890     ldw     x, *m_p+2
      008609 BF 26            [ 2]  891     ldw     *m_n+2, x
      00860B 84               [ 1]  892     pop     a
      00860C 4D               [ 1]  893     tnz     a
      00860D 27 20            [ 1]  894     jreq    00078$
      00860F 88               [ 1]  895     push    a
      008610 97               [ 1]  896     ld      xl, a
      008611 B6 02            [ 1]  897     ld      a, *m_a+1               ; |de| low byte
      008613 42               [ 4]  898     mul     x, a
      008614 89               [ 2]  899     pushw   x                   ; high-word add: m_n[0..1] += mh*deL
      008615 B6 25            [ 1]  900     ld      a, *m_n+1
      008617 1B 02            [ 1]  901     add     a, (2, sp)
      008619 B7 25            [ 1]  902     ld      *m_n+1, a
      00861B B6 24            [ 1]  903     ld      a, *m_n
      00861D 19 01            [ 1]  904     adc     a, (1, sp)
      00861F B7 24            [ 1]  905     ld      *m_n, a
      008621 85               [ 2]  906     popw    x
      008622 84               [ 1]  907     pop     a
      008623 97               [ 1]  908     ld      xl, a
      008624 B6 01            [ 1]  909     ld      a, *m_a                 ; |de| high byte (<= 2)
      008626 42               [ 4]  910     mul     x, a                ; <= 14
      008627 89               [ 2]  911     pushw   x
      008628 B6 24            [ 1]  912     ld      a, *m_n
      00862A 1B 02            [ 1]  913     add     a, (2, sp)
      00862C B7 24            [ 1]  914     ld      *m_n, a
      00862E 85               [ 2]  915     popw    x
      00862F                        916 00078$:
                                    917     ; Q = P / dy
      00862F BE 4A            [ 2]  918     ldw     x, *r_dy
      008631 BF 28            [ 2]  919     ldw     *m_d, x
      008633 BE 4C            [ 2]  920     ldw     x, *r_dy+2
      008635 BF 2A            [ 2]  921     ldw     *m_d+2, x
      008637 CD 83 95         [ 4]  922     call    udiv32
      00863A BE 26            [ 2]  923     ldw     x, *m_n+2               ; low16 of |Q|
      00863C 3D 5C            [ 1]  924     tnz     *r_sgn
      00863E 27 01            [ 1]  925     jreq    00079$
      008640 50               [ 2]  926     negw    x
      008641                        927 00079$:
      008641 72 B0 00 52      [ 2]  928     subw    x, r_me             ; dtau16 = Q - me
                                    929     ; K2 = zext(g_K) - dk; commit iff 46000 <= K2 <= 60000
      008645 89               [ 2]  930     pushw   x
      008646 C6 01 15         [ 1]  931     ld      a, _g_K+1
      008649 B0 51            [ 1]  932     sub     a, *r_dk+3
      00864B B7 27            [ 1]  933     ld      *m_n+3, a
      00864D C6 01 14         [ 1]  934     ld      a, _g_K
      008650 B2 50            [ 1]  935     sbc     a, *r_dk+2
      008652 B7 26            [ 1]  936     ld      *m_n+2, a
      008654 4F               [ 1]  937     clr     a
      008655 B2 4F            [ 1]  938     sbc     a, *r_dk+1
      008657 B7 25            [ 1]  939     ld      *m_n+1, a
      008659 4F               [ 1]  940     clr     a
      00865A B2 4E            [ 1]  941     sbc     a, *r_dk
      00865C B7 24            [ 1]  942     ld      *m_n, a
      00865E B6 24            [ 1]  943     ld      a, *m_n
      008660 BA 25            [ 1]  944     or      a, *m_n+1
      008662 26 18            [ 1]  945     jrne    00098$              ; negative or >= 65536
      008664 BE 26            [ 2]  946     ldw     x, *m_n+2
      008666 A3 B3 B0         [ 2]  947     cpw     x, #46000
      008669 25 11            [ 1]  948     jrc     00098$
      00866B A3 EA 61         [ 2]  949     cpw     x, #60001
      00866E 24 0C            [ 1]  950     jrnc    00098$
      008670 CF 01 14         [ 2]  951     ldw     _g_K, x
      008673 85               [ 2]  952     popw    x
      008674 72 BB 01 16      [ 2]  953     addw    x, _g_tau
      008678 CF 01 16         [ 2]  954     ldw     _g_tau, x
      00867B 81               [ 4]  955     ret
      00867C                        956 00098$:
      00867C 85               [ 2]  957     popw    x
      00867D                        958 00099$:
      00867D 81               [ 4]  959     ret
                                    960 
                                    961 ; ======================================================================
                                    962 ; seed() / dec_eps_centi() / set_gap56() -- the remaining 32-bit users,
                                    963 ; ported so USE_ASM_DEC builds link NO SDCC 32-bit library at all.
                                    964 ; ======================================================================
                                    965 
                                    966     .globl _seed
                                    967     .globl _dec_eps_centi
                                    968     .globl _set_gap56
                                    969     .globl _g_Wu11
                                    970     .globl _dec_info
                                    971 
                                    972     .area CODE
                                    973 
                                    974 ; shp11: A:X = m_p >> 11 (m_p < 2^31).  Shared by mr16/seed/set_gap56.
      00867E                        975 shp11:
      00867E BE 06            [ 2]  976     ldw     x, *m_p+1               ; (p >> 8) low16
      008680 B6 05            [ 1]  977     ld      a, *m_p                 ; (p >> 8) high8
      008682 44               [ 1]  978     srl     a
      008683 56               [ 2]  979     rrcw    x
      008684 44               [ 1]  980     srl     a
      008685 56               [ 2]  981     rrcw    x
      008686 44               [ 1]  982     srl     a
      008687 56               [ 2]  983     rrcw    x
      008688 81               [ 4]  984     ret
                                    985 
                                    986 ; ---------------------------------------------------------------- seed
                                    987 ; P1 endpoint seed: first-rise / last-fall brackets pin K and tau.
                                    988 ; np reuses r_melo, flm r_mehi, r0m r_de (refine scratch, disjoint use).
      008689                        989 _seed:
      008689 5F               [ 1]  990     clrw    x
      00868A BF 44            [ 2]  991     ldw     *r_melo, x              ; np = 0
      00868C CD 95 3F         [ 4]  992     call    _scan_init
      00868F                        993 00100$:
      00868F CD 95 5B         [ 4]  994     call    _scan_next
      008692 4D               [ 1]  995     tnz     a
      008693 27 1F            [ 1]  996     jreq    00104$
      008695 CE 00 BF         [ 2]  997     ldw     x, _scan_fa             ; flm = (fa + fb) >> 1 (every pulse)
      008698 72 BB 00 C1      [ 2]  998     addw    x, _scan_fb
      00869C 54               [ 2]  999     srlw    x
      00869D BF 46            [ 2] 1000     ldw     *r_mehi, x
      00869F BE 44            [ 2] 1001     ldw     x, *r_melo
      0086A1 26 0A            [ 1] 1002     jrne    00102$
      0086A3 CE 00 BB         [ 2] 1003     ldw     x, _scan_ra             ; first pulse: r0m = (ra + rb) >> 1
      0086A6 72 BB 00 BD      [ 2] 1004     addw    x, _scan_rb
      0086AA 54               [ 2] 1005     srlw    x
      0086AB BF 48            [ 2] 1006     ldw     *r_de, x
      0086AD                       1007 00102$:
      0086AD BE 44            [ 2] 1008     ldw     x, *r_melo
      0086AF 5C               [ 1] 1009     incw    x
      0086B0 BF 44            [ 2] 1010     ldw     *r_melo, x
      0086B2 20 DB            [ 2] 1011     jra     00100$
      0086B4                       1012 00104$:
      0086B4 BE 44            [ 2] 1013     ldw     x, *r_melo              ; np < 8 -> fail
      0086B6 A3 00 08         [ 2] 1014     cpw     x, #8
      0086B9 25 45            [ 1] 1015     jrc     00109$
      0086BB BE 46            [ 2] 1016     ldw     x, *r_mehi              ; flm <= r0m -> fail
      0086BD 72 B0 00 48      [ 2] 1017     subw    x, r_de
      0086C1 25 3D            [ 1] 1018     jrc     00109$
      0086C3 27 3B            [ 1] 1019     jreq    00109$
      0086C5 BF 2A            [ 2] 1020     ldw     *m_d+2, x               ; K = g_Wu11 / (flm - r0m)
      0086C7 5F               [ 1] 1021     clrw    x
      0086C8 BF 28            [ 2] 1022     ldw     *m_d, x
      0086CA CE 80 9F         [ 2] 1023     ldw     x, _g_Wu11
      0086CD BF 24            [ 2] 1024     ldw     *m_n, x
      0086CF CE 80 A1         [ 2] 1025     ldw     x, _g_Wu11+2
      0086D2 BF 26            [ 2] 1026     ldw     *m_n+2, x
      0086D4 CD 83 95         [ 4] 1027     call    udiv32
      0086D7 BE 24            [ 2] 1028     ldw     x, *m_n                 ; K_MIN <= K <= K_MAX else fail
      0086D9 26 25            [ 1] 1029     jrne    00109$
      0086DB BE 26            [ 2] 1030     ldw     x, *m_n+2
      0086DD A3 B3 B0         [ 2] 1031     cpw     x, #46000
      0086E0 25 1E            [ 1] 1032     jrc     00109$
      0086E2 A3 EA 61         [ 2] 1033     cpw     x, #60001
      0086E5 24 19            [ 1] 1034     jrnc    00109$
      0086E7 CF 01 14         [ 2] 1035     ldw     _g_K, x
      0086EA BF 01            [ 2] 1036     ldw     *m_a, x                 ; tau = 512 - low16((r0m * K) >> 11)
      0086EC BE 48            [ 2] 1037     ldw     x, *r_de
      0086EE BF 03            [ 2] 1038     ldw     *m_b, x
      0086F0 CD 81 E8         [ 4] 1039     call    mul16
      0086F3 CD 86 7E         [ 4] 1040     call    shp11
      0086F6 50               [ 2] 1041     negw    x
      0086F7 1C 02 00         [ 2] 1042     addw    x, #512
      0086FA CF 01 16         [ 2] 1043     ldw     _g_tau, x
      0086FD A6 01            [ 1] 1044     ld      a, #1
      0086FF 81               [ 4] 1045     ret
      008700                       1046 00109$:
      008700 4F               [ 1] 1047     clr     a
      008701 81               [ 4] 1048     ret
                                   1049 
                                   1050 ; ---------------------------------------------------------- dec_eps_centi
                                   1051 ; ((K_NOM - dec_info.K) * 10000) / dec_info.K, s16.  dec_info.K is at
                                   1052 ; offset 9 (decode.h layout: 5 u8 fields + n_weak + n_tied before it).
      008702                       1053 _dec_eps_centi:
      008702 AE CC CD         [ 2] 1054     ldw     x, #52429
      008705 72 B0 01 09      [ 2] 1055     subw    x, _dec_info+9
      008709 3F 5C            [ 1] 1056     clr     *r_sgn
      00870B 5D               [ 2] 1057     tnzw    x
      00870C 2A 05            [ 1] 1058     jrpl    00110$
      00870E 50               [ 2] 1059     negw    x
      00870F 35 01 00 5C      [ 1] 1060     mov     r_sgn, #1
      008713                       1061 00110$:
      008713 BF 01            [ 2] 1062     ldw     *m_a, x
      008715 AE 27 10         [ 2] 1063     ldw     x, #10000
      008718 BF 03            [ 2] 1064     ldw     *m_b, x
      00871A CD 81 E8         [ 4] 1065     call    mul16               ; <= 75.7M
      00871D BE 05            [ 2] 1066     ldw     x, *m_p
      00871F BF 24            [ 2] 1067     ldw     *m_n, x
      008721 BE 07            [ 2] 1068     ldw     x, *m_p+2
      008723 BF 26            [ 2] 1069     ldw     *m_n+2, x
      008725 5F               [ 1] 1070     clrw    x
      008726 BF 28            [ 2] 1071     ldw     *m_d, x
      008728 CE 01 09         [ 2] 1072     ldw     x, _dec_info+9
      00872B BF 2A            [ 2] 1073     ldw     *m_d+2, x
      00872D CD 83 95         [ 4] 1074     call    udiv32
      008730 BE 26            [ 2] 1075     ldw     x, *m_n+2
      008732 3D 5C            [ 1] 1076     tnz     *r_sgn
      008734 27 01            [ 1] 1077     jreq    00111$
      008736 50               [ 2] 1078     negw    x
      008737                       1079 00111$:
      008737 81               [ 4] 1080     ret
                                   1081 
                                   1082 ; ---------------------------------------------------------- set_gap56
                                   1083 ; c_gap56[0] = (6*K)>>11, c_gap56[1] = (5*K)>>11 (both <= 175)
      008738                       1084 _set_gap56:
      008738 A6 06            [ 1] 1085     ld      a, #6
      00873A CD 87 47         [ 4] 1086     call    gap1
      00873D BF F9            [ 2] 1087     ldw     *zgap, x
      00873F A6 05            [ 1] 1088     ld      a, #5
      008741 CD 87 47         [ 4] 1089     call    gap1
      008744 BF FB            [ 2] 1090     ldw     *zgap+2, x
      008746 81               [ 4] 1091     ret
      008747                       1092 gap1:
      008747 5F               [ 1] 1093     clrw    x
      008748 97               [ 1] 1094     ld      xl, a
      008749 BF 01            [ 2] 1095     ldw     *m_a, x
      00874B CE 01 14         [ 2] 1096     ldw     x, _g_K
      00874E BF 03            [ 2] 1097     ldw     *m_b, x
      008750 CD 81 E8         [ 4] 1098     call    mul16
      008753 CD 86 7E         [ 4] 1099     call    shp11
      008756 81               [ 4] 1100     ret
                                   1101 
                                   1102 ; ======================================================================
                                   1103 ; P4 decision cluster: known_bit / a_bounds / hinge / argmin / decide /
                                   1104 ; cand_insert / decide_pass.  Replaces ~1470 B of SDCC output.
                                   1105 ; The per-bit margin scan uses an exactly-equivalent prefix-min (online)
                                   1106 ; + suffix-min (precomputed d_sm[]) formulation of the C's inner loops:
                                   1107 ;   c0m(off) = min costs[a in lo..min(off,hi)]   (empty -> 0xFFFF)
                                   1108 ;   c1m(off) = min costs[a in max(lo,off+1)..hi] (empty -> 0xFFFF)
                                   1109 ; identical values, O(L+W) instead of O(L*W).
                                   1110 ; ======================================================================
                                   1111 
                                   1112     .globl _decide_pass
                                   1113     .globl _known_bit
                                   1114     .globl _a_bounds_sg
                                   1115     .globl _g_sg
                                   1116     .globl _dq_amin
                                   1117     .globl _dq_amax
                                   1118     .globl _g_NBm32
                                   1119     .globl _g_PPHI
                                   1120 
                                   1121     .globl _ov
                                   1122 
                                   1123     .area CODE
                                   1124 
                                   1125 ; -------------------------------------------------------------- known_bit
                                   1126 ; X = t -> A = 0 / 1 / 0xFF(-1).  C-ABI compatible (calibrate and
                                   1127 ; ws_decode_ex call this directly).
      008757                       1128 _known_bit:
      008757 A3 00 20         [ 2] 1129     cpw     x, #32
      00875A 25 09            [ 1] 1130     jrc     00130$              ; header bits 0..31
      00875C 72 B0 80 A3      [ 2] 1131     subw    x, _g_NBm32
      008760 25 17            [ 1] 1132     jrc     00132$              ; interior
      008762 1C 00 20         [ 2] 1133     addw    x, #32              ; trailer bits at HT[32..63]
      008765                       1134 00130$:
      008765 9F               [ 1] 1135     ld      a, xl
      008766 A4 07            [ 1] 1136     and     a, #7
      008768 4C               [ 1] 1137     inc     a
      008769 B7 0D            [ 1] 1138     ld      *m_s, a                 ; shift count = (t&7)+1
      00876B 54               [ 2] 1139     srlw    x
      00876C 54               [ 2] 1140     srlw    x
      00876D 54               [ 2] 1141     srlw    x
      00876E D6 87 7C         [ 1] 1142     ld      a, (HT, x)
      008771                       1143 00131$:
      008771 48               [ 1] 1144     sll     a
      008772 3A 0D            [ 1] 1145     dec     *m_s
      008774 26 FB            [ 1] 1146     jrne    00131$
      008776 4F               [ 1] 1147     clr     a
      008777 49               [ 1] 1148     rlc     a                       ; A = the bit
      008778 81               [ 4] 1149     ret
      008779                       1150 00132$:
      008779 A6 FF            [ 1] 1151     ld      a, #0xFF
      00877B 81               [ 4] 1152     ret
      00877C FF 00 AA 65 9A 55 00  1153 HT: .db 0xFF,0x00,0xAA,0x65,0x9A,0x55,0x00,0xFF
             FF
                                   1154 
                                   1155 ; ------------------------------------------------------------ a_bounds_sg
                                   1156 ; a_bounds over g_sg -> dq_amin/dq_amax (C calibrate uses this too).
      008784                       1157 _a_bounds_sg:
      008784 5F               [ 1] 1158     clrw    x
      008785 BF 66            [ 2] 1159     ldw     *_dq_amin, x
      008787 BE 5F            [ 2] 1160     ldw     x, *_g_sg+2
      008789 72 B0 00 5D      [ 2] 1161     subw    x, _g_sg
      00878D BF 68            [ 2] 1162     ldw     *_dq_amax, x
      00878F BE 5F            [ 2] 1163     ldw     x, *_g_sg+2             ; e = min(k1, NB)
      008791 C3 80 95         [ 2] 1164     cpw     x, _g_NB
      008794 25 03            [ 1] 1165     jrc     00140$
      008796 CE 80 95         [ 2] 1166     ldw     x, _g_NB
      008799                       1167 00140$:
      008799 BF 84            [ 2] 1168     ldw     *m_e, x
      00879B BE 5D            [ 2] 1169     ldw     x, *_g_sg
      00879D BF 86            [ 2] 1170     ldw     *m_t, x
      00879F                       1171 00141$:
      00879F BE 86            [ 2] 1172     ldw     x, *m_t
      0087A1 B3 84            [ 2] 1173     cpw     x, *m_e
      0087A3 24 2C            [ 1] 1174     jrnc    00149$
      0087A5 CD 87 57         [ 4] 1175     call    _known_bit
      0087A8 A1 01            [ 1] 1176     cp      a, #1
      0087AA 26 0F            [ 1] 1177     jrne    00142$
      0087AC BE 86            [ 2] 1178     ldw     x, *m_t                 ; kb == 1: amin = max(amin, t-k0+1)
      0087AE 72 B0 00 5D      [ 2] 1179     subw    x, _g_sg
      0087B2 5C               [ 1] 1180     incw    x
      0087B3 B3 66            [ 2] 1181     cpw     x, *_dq_amin
      0087B5 23 13            [ 2] 1182     jrule   00144$
      0087B7 BF 66            [ 2] 1183     ldw     *_dq_amin, x
      0087B9 20 0F            [ 2] 1184     jra     00144$
      0087BB                       1185 00142$:
      0087BB 4D               [ 1] 1186     tnz     a
      0087BC 26 0C            [ 1] 1187     jrne    00144$              ; -1: nothing
      0087BE BE 86            [ 2] 1188     ldw     x, *m_t                 ; kb == 0: amax = min(amax, t-k0)
      0087C0 72 B0 00 5D      [ 2] 1189     subw    x, _g_sg
      0087C4 B3 68            [ 2] 1190     cpw     x, *_dq_amax
      0087C6 24 02            [ 1] 1191     jrnc    00144$
      0087C8 BF 68            [ 2] 1192     ldw     *_dq_amax, x
      0087CA                       1193 00144$:
      0087CA BE 86            [ 2] 1194     ldw     x, *m_t
      0087CC 5C               [ 1] 1195     incw    x
      0087CD BF 86            [ 2] 1196     ldw     *m_t, x
      0087CF 20 CE            [ 2] 1197     jra     00141$
      0087D1                       1198 00149$:
      0087D1 81               [ 4] 1199     ret
                                   1200 
                                   1201 ; ---------------------------------------------------------------- hcost
                                   1202 ; X = h -> X = hinge(u, v, h) = max(0, u-h, h-v); g_sg.u/.v.  Keeps m_h.
      0087D2                       1203 hcost:
      0087D2 BF 7A            [ 2] 1204     ldw     *m_h, x
      0087D4 BE 61            [ 2] 1205     ldw     x, *_g_sg+4
      0087D6 72 B0 00 7A      [ 2] 1206     subw    x, m_h              ; u - h (s16)
      0087DA 2C 01            [ 1] 1207     jrsgt   00150$
      0087DC 5F               [ 1] 1208     clrw    x
      0087DD                       1209 00150$:
      0087DD 90 93            [ 1] 1210     ldw     y, x                    ; Y = g so far
      0087DF BE 7A            [ 2] 1211     ldw     x, *m_h
      0087E1 72 B0 00 63      [ 2] 1212     subw    x, _g_sg+6          ; h - v (s16)
      0087E5 2C 02            [ 1] 1213     jrsgt   00151$
      0087E7 93               [ 1] 1214     ldw     x, y
      0087E8 81               [ 4] 1215     ret
      0087E9                       1216 00151$:
      0087E9 90 89            [ 2] 1217     pushw   y                   ; g
      0087EB 13 01            [ 2] 1218     cpw     x, (1, sp)
      0087ED 90 85            [ 2] 1219     popw    y
      0087EF 22 01            [ 1] 1220     jrugt   00152$
      0087F1 93               [ 1] 1221     ldw     x, y
      0087F2                       1222 00152$:
      0087F2 81               [ 4] 1223     ret
                                   1224 
                                   1225 ; ----------------------------------------------------------------- itst
                                   1226 ; A = (u < m_h && m_h <= v), signed.
      0087F3                       1227 itst:
      0087F3 BE 61            [ 2] 1228     ldw     x, *_g_sg+4
      0087F5 B3 7A            [ 2] 1229     cpw     x, *m_h
      0087F7 2F 02            [ 1] 1230     jrslt   00153$
      0087F9 4F               [ 1] 1231     clr     a
      0087FA 81               [ 4] 1232     ret
      0087FB                       1233 00153$:
      0087FB BE 7A            [ 2] 1234     ldw     x, *m_h
      0087FD B3 63            [ 2] 1235     cpw     x, *_g_sg+6
      0087FF 2D 02            [ 1] 1236     jrsle   00154$
      008801 4F               [ 1] 1237     clr     a
      008802 81               [ 4] 1238     ret
      008803                       1239 00154$:
      008803 A6 01            [ 1] 1240     ld      a, #1
      008805 81               [ 4] 1241     ret
                                   1242 
                                   1243 ; --------------------------------------------------------------- setbit
                                   1244 ; dq_inter |= 1 << m_ai
      008806                       1245 setbit:
      008806 B6 91            [ 1] 1246     ld      a, *m_ai
      008808 A4 07            [ 1] 1247     and     a, #7
      00880A B7 0D            [ 1] 1248     ld      *m_s, a
      00880C A6 01            [ 1] 1249     ld      a, #1
      00880E 3D 0D            [ 1] 1250     tnz     *m_s
      008810 27 05            [ 1] 1251     jreq    00156$
      008812                       1252 00155$:
      008812 48               [ 1] 1253     sll     a
      008813 3A 0D            [ 1] 1254     dec     *m_s
      008815 26 FB            [ 1] 1255     jrne    00155$
      008817                       1256 00156$:
      008817 88               [ 1] 1257     push    a
      008818 B6 91            [ 1] 1258     ld      a, *m_ai
      00881A A1 08            [ 1] 1259     cp      a, #8
      00881C 84               [ 1] 1260     pop     a
      00881D 25 05            [ 1] 1261     jrc     00157$
      00881F BA 6A            [ 1] 1262     or      a, *dq_inter            ; bits 8..15 live in the high byte
      008821 B7 6A            [ 1] 1263     ld      *dq_inter, a
      008823 81               [ 4] 1264     ret
      008824                       1265 00157$:
      008824 BA 6B            [ 1] 1266     or      a, *dq_inter+1
      008826 B7 6B            [ 1] 1267     ld      *dq_inter+1, a
      008828 81               [ 4] 1268     ret
                                   1269 
                                   1270 ; --------------------------------------------------------------- getbit
                                   1271 ; A = (dq_inter >> m_ai2) & 1
      008829                       1272 getbit:
      008829 B6 92            [ 1] 1273     ld      a, *m_ai2
      00882B A4 07            [ 1] 1274     and     a, #7
      00882D 4C               [ 1] 1275     inc     a
      00882E B7 0D            [ 1] 1276     ld      *m_s, a
      008830 B6 92            [ 1] 1277     ld      a, *m_ai2
      008832 A1 08            [ 1] 1278     cp      a, #8
      008834 25 04            [ 1] 1279     jrc     00158$
      008836 B6 6A            [ 1] 1280     ld      a, *dq_inter
      008838 20 02            [ 2] 1281     jra     00159$
      00883A                       1282 00158$:
      00883A B6 6B            [ 1] 1283     ld      a, *dq_inter+1
      00883C                       1284 00159$:
      00883C 44               [ 1] 1285     srl     a
      00883D 3A 0D            [ 1] 1286     dec     *m_s
      00883F 26 FB            [ 1] 1287     jrne    00159$
      008841 4F               [ 1] 1288     clr     a
      008842 49               [ 1] 1289     rlc     a
      008843 81               [ 4] 1290     ret
                                   1291 
                                   1292 ; --------------------------------------------------------------- argmin
                                   1293 ; over [m_alo..m_ahi]: (cost, interior-preferred-on-tie, smallest a).
                                   1294 ; -> X = best.  Mirrors C argmin_ab exactly (bc=0xFFFF, bi=1 initial).
      008844                       1295 argmin:
      008844 AE FF FF         [ 2] 1296     ldw     x, #0xFFFF
      008847 BF 7E            [ 2] 1297     ldw     *m_c, x
      008849 35 01 00 90      [ 1] 1298     mov     m_it, #1
      00884D B6 93            [ 1] 1299     ld      a, *m_alo
      00884F B7 95            [ 1] 1300     ld      *m_best, a
      008851 B7 92            [ 1] 1301     ld      *m_ai2, a
      008853                       1302 00160$:
      008853 B6 92            [ 1] 1303     ld      a, *m_ai2
      008855 48               [ 1] 1304     sll     a
      008856 5F               [ 1] 1305     clrw    x
      008857 97               [ 1] 1306     ld      xl, a
      008858 DE 01 C9         [ 2] 1307     ldw     x, (d_costs, x)
      00885B B3 7E            [ 2] 1308     cpw     x, *m_c
      00885D 25 16            [ 1] 1309     jrc     00161$              ; strictly better
      00885F 26 1F            [ 1] 1310     jrne    00163$              ; worse
      008861 CD 88 29         [ 4] 1311     call    getbit              ; equal: take iff it && !bi
      008864 4D               [ 1] 1312     tnz     a
      008865 27 19            [ 1] 1313     jreq    00163$
      008867 3D 90            [ 1] 1314     tnz     *m_it
      008869 26 15            [ 1] 1315     jrne    00163$
      00886B 35 01 00 90      [ 1] 1316     mov     m_it, #1
      00886F B6 92            [ 1] 1317     ld      a, *m_ai2
      008871 B7 95            [ 1] 1318     ld      *m_best, a
      008873 20 0B            [ 2] 1319     jra     00163$
      008875                       1320 00161$:
      008875 BF 7E            [ 2] 1321     ldw     *m_c, x
      008877 CD 88 29         [ 4] 1322     call    getbit
      00887A B7 90            [ 1] 1323     ld      *m_it, a
      00887C B6 92            [ 1] 1324     ld      a, *m_ai2
      00887E B7 95            [ 1] 1325     ld      *m_best, a
      008880                       1326 00163$:
      008880 B6 92            [ 1] 1327     ld      a, *m_ai2
      008882 4C               [ 1] 1328     inc     a
      008883 B7 92            [ 1] 1329     ld      *m_ai2, a
      008885 B1 94            [ 1] 1330     cp      a, *m_ahi
      008887 23 CA            [ 2] 1331     jrule   00160$
      008889 5F               [ 1] 1332     clrw    x
      00888A B6 95            [ 1] 1333     ld      a, *m_best
      00888C 97               [ 1] 1334     ld      xl, a
      00888D 81               [ 4] 1335     ret
                                   1336 
                                   1337 ; --------------------------------------------------------------- addd56
                                   1338 ; m_h0 += sext(A); m_h1 += sext(A)
      00888E                       1339 addd56:
      00888E 5F               [ 1] 1340     clrw    x
      00888F 97               [ 1] 1341     ld      xl, a
      008890 4D               [ 1] 1342     tnz     a
      008891 2A 03            [ 1] 1343     jrpl    00165$
      008893 1C FF 00         [ 2] 1344     addw    x, #0xFF00
      008896                       1345 00165$:
      008896 BF 7A            [ 2] 1346     ldw     *m_h, x
      008898 BE 76            [ 2] 1347     ldw     x, *m_h0
      00889A 72 BB 00 7A      [ 2] 1348     addw    x, m_h
      00889E BF 76            [ 2] 1349     ldw     *m_h0, x
      0088A0 BE 78            [ 2] 1350     ldw     x, *m_h1
      0088A2 72 BB 00 7A      [ 2] 1351     addw    x, m_h
      0088A6 BF 78            [ 2] 1352     ldw     *m_h1, x
      0088A8 81               [ 4] 1353     ret
                                   1354 
                                   1355 ; ---------------------------------------------------------------- decide
                                   1356 ; g_sg -> d_costs[0..acap], dq_inter, dq_acap/afree/lo/hi/ahat.
      0088A9                       1357 dq_decide:
      0088A9 BE 5F            [ 2] 1358     ldw     x, *_g_sg+2
      0088AB 72 B0 00 5D      [ 2] 1359     subw    x, _g_sg
      0088AF BF 7C            [ 2] 1360     ldw     *m_L, x                 ; L = k1-k0 (>= 1)
      0088B1 A3 00 10         [ 2] 1361     cpw     x, #16
      0088B4 25 03            [ 1] 1362     jrc     00170$
      0088B6 AE 00 0F         [ 2] 1363     ldw     x, #15
      0088B9                       1364 00170$:
      0088B9 BF 6C            [ 2] 1365     ldw     *dq_acap, x
      0088BB BE DF            [ 2] 1366     ldw     x, *zh0c
      0088BD BF 76            [ 2] 1367     ldw     *m_h0, x
      0088BF BE E1            [ 2] 1368     ldw     x, *zh1c
      0088C1 BF 78            [ 2] 1369     ldw     *m_h1, x
      0088C3 B6 65            [ 1] 1370     ld      a, *_g_sg+8             ; fam
      0088C5 A1 05            [ 1] 1371     cp      a, #5
      0088C7 26 07            [ 1] 1372     jrne    00171$
      0088C9 B6 E3            [ 1] 1373     ld      a, *zd56
      0088CB CD 88 8E         [ 4] 1374     call    addd56
      0088CE 20 09            [ 2] 1375     jra     00172$
      0088D0                       1376 00171$:
      0088D0 A1 06            [ 1] 1377     cp      a, #6
      0088D2 26 05            [ 1] 1378     jrne    00172$
      0088D4 B6 E4            [ 1] 1379     ld      a, *zd56+1
      0088D6 CD 88 8E         [ 4] 1380     call    addd56
      0088D9                       1381 00172$:
      0088D9 5F               [ 1] 1382     clrw    x
      0088DA BF 6A            [ 2] 1383     ldw     *dq_inter, x
      0088DC 3F 91            [ 1] 1384     clr     *m_ai
      0088DE                       1385 00173$:                         ; per hypothesis a
      0088DE B6 91            [ 1] 1386     ld      a, *m_ai
      0088E0 26 0E            [ 1] 1387     jrne    00174$
      0088E2 BE 76            [ 2] 1388     ldw     x, *m_h0                ; a == 0
      0088E4 CD 87 D2         [ 4] 1389     call    hcost
      0088E7 BF 7E            [ 2] 1390     ldw     *m_c, x
      0088E9 CD 87 F3         [ 4] 1391     call    itst
      0088EC B7 90            [ 1] 1392     ld      *m_it, a
      0088EE 20 38            [ 2] 1393     jra     00177$
      0088F0                       1394 00174$:
      0088F0 4A               [ 1] 1395     dec     a                       ; a >= 1: h = (a-1)*512 + h1e
      0088F1 48               [ 1] 1396     sll     a
      0088F2 5F               [ 1] 1397     clrw    x
      0088F3 95               [ 1] 1398     ld      xh, a
      0088F4 72 BB 00 78      [ 2] 1399     addw    x, m_h1
      0088F8 CD 87 D2         [ 4] 1400     call    hcost
      0088FB BF 7E            [ 2] 1401     ldw     *m_c, x
      0088FD CD 87 F3         [ 4] 1402     call    itst
      008900 B7 90            [ 1] 1403     ld      *m_it, a
      008902 B6 91            [ 1] 1404     ld      a, *m_ai                ; if a < L: h2 = a*512 + h0e
      008904 5F               [ 1] 1405     clrw    x
      008905 97               [ 1] 1406     ld      xl, a
      008906 B3 7C            [ 2] 1407     cpw     x, *m_L
      008908 24 1E            [ 1] 1408     jrnc    00177$
      00890A B6 91            [ 1] 1409     ld      a, *m_ai
      00890C 48               [ 1] 1410     sll     a
      00890D 5F               [ 1] 1411     clrw    x
      00890E 95               [ 1] 1412     ld      xh, a
      00890F 72 BB 00 76      [ 2] 1413     addw    x, m_h0
      008913 CD 87 D2         [ 4] 1414     call    hcost
      008916 89               [ 2] 1415     pushw   x
      008917 CD 87 F3         [ 4] 1416     call    itst
      00891A 4D               [ 1] 1417     tnz     a
      00891B 27 04            [ 1] 1418     jreq    00175$
      00891D 35 01 00 90      [ 1] 1419     mov     m_it, #1
      008921                       1420 00175$:
      008921 85               [ 2] 1421     popw    x
      008922 B3 7E            [ 2] 1422     cpw     x, *m_c
      008924 24 02            [ 1] 1423     jrnc    00177$
      008926 BF 7E            [ 2] 1424     ldw     *m_c, x
      008928                       1425 00177$:                         ; store costs[a] + interior bit
      008928 B6 91            [ 1] 1426     ld      a, *m_ai
      00892A 48               [ 1] 1427     sll     a
      00892B 5F               [ 1] 1428     clrw    x
      00892C 97               [ 1] 1429     ld      xl, a
      00892D 90 BE 7E         [ 2] 1430     ldw     y, *m_c
      008930 DF 01 C9         [ 2] 1431     ldw     (d_costs, x), y
      008933 3D 90            [ 1] 1432     tnz     *m_it
      008935 27 03            [ 1] 1433     jreq    00178$
      008937 CD 88 06         [ 4] 1434     call    setbit
      00893A                       1435 00178$:
      00893A B6 91            [ 1] 1436     ld      a, *m_ai
      00893C 4C               [ 1] 1437     inc     a
      00893D B7 91            [ 1] 1438     ld      *m_ai, a
      00893F B1 6D            [ 1] 1439     cp      a, *dq_acap+1
      008941 23 9B            [ 2] 1440     jrule   00173$
                                   1441     ; a_free = argmin(0, acap)
      008943 3F 93            [ 1] 1442     clr     *m_alo
      008945 B6 6D            [ 1] 1443     ld      a, *dq_acap+1
      008947 B7 94            [ 1] 1444     ld      *m_ahi, a
      008949 CD 88 44         [ 4] 1445     call    argmin
      00894C BF 74            [ 2] 1446     ldw     *dq_afree, x
      00894E CD 87 84         [ 4] 1447     call    _a_bounds_sg
      008951 BE 66            [ 2] 1448     ldw     x, *_dq_amin            ; lo = amin (>= 0)
      008953 BF 6E            [ 2] 1449     ldw     *dq_lo, x
      008955 BE 68            [ 2] 1450     ldw     x, *_dq_amax            ; hi = min(amax, acap)
      008957 B3 6C            [ 2] 1451     cpw     x, *dq_acap
      008959 25 02            [ 1] 1452     jrc     00179$
      00895B BE 6C            [ 2] 1453     ldw     x, *dq_acap
      00895D                       1454 00179$:
      00895D BF 70            [ 2] 1455     ldw     *dq_hi, x
      00895F BE 6E            [ 2] 1456     ldw     x, *dq_lo
      008961 B3 70            [ 2] 1457     cpw     x, *dq_hi
      008963 23 07            [ 2] 1458     jrule   00180$
      008965 5F               [ 1] 1459     clrw    x                   ; lo > hi: full range
      008966 BF 6E            [ 2] 1460     ldw     *dq_lo, x
      008968 BE 6C            [ 2] 1461     ldw     x, *dq_acap
      00896A BF 70            [ 2] 1462     ldw     *dq_hi, x
      00896C                       1463 00180$:
      00896C B6 6F            [ 1] 1464     ld      a, *dq_lo+1
      00896E B7 93            [ 1] 1465     ld      *m_alo, a
      008970 B6 71            [ 1] 1466     ld      a, *dq_hi+1
      008972 B7 94            [ 1] 1467     ld      *m_ahi, a
      008974 CD 88 44         [ 4] 1468     call    argmin
      008977 BF 72            [ 2] 1469     ldw     *dq_ahat, x
      008979 81               [ 4] 1470     ret
                                   1471 
                                   1472 ; ------------------------------------------------------------ cand_insert
                                   1473 ; X = payload' bit index k, A = margin m: sorted top-5 insert
                                   1474 ; (key: margin then index, ascending) -- exactly C cand_insert.
      00897A                       1475 candi:
      00897A B7 9C            [ 1] 1476     ld      *m_m, a
      00897C BF 8A            [ 2] 1477     ldw     *m_k, x
      00897E B6 A3            [ 1] 1478     ld      a, *zc_n
      008980 B7 9A            [ 1] 1479     ld      *m_i, a
      008982                       1480 00185$:                         ; while (i > 0 && cand_m[i-1] > m) i--
      008982 3D 9A            [ 1] 1481     tnz     *m_i
      008984 27 10            [ 1] 1482     jreq    00186$
      008986 B6 9A            [ 1] 1483     ld      a, *m_i
      008988 4A               [ 1] 1484     dec     a
      008989 5F               [ 1] 1485     clrw    x
      00898A 97               [ 1] 1486     ld      xl, a
      00898B D6 02 13         [ 1] 1487     ld      a, (zc_m, x)
      00898E B1 9C            [ 1] 1488     cp      a, *m_m
      008990 23 04            [ 2] 1489     jrule   00186$
      008992 3A 9A            [ 1] 1490     dec     *m_i
      008994 20 EC            [ 2] 1491     jra     00185$
      008996                       1492 00186$:
      008996 B6 9A            [ 1] 1493     ld      a, *m_i
      008998 A1 05            [ 1] 1494     cp      a, #5
      00899A 25 01            [ 1] 1495     jrc     00187$
      00899C 81               [ 4] 1496     ret                         ; list full below this margin
      00899D                       1497 00187$:
      00899D B6 A3            [ 1] 1498     ld      a, *zc_n             ; j = min(ncand, 4)
      00899F A1 05            [ 1] 1499     cp      a, #5
      0089A1 25 02            [ 1] 1500     jrc     00188$
      0089A3 A6 04            [ 1] 1501     ld      a, #4
      0089A5                       1502 00188$:
      0089A5 B7 9B            [ 1] 1503     ld      *m_j, a
      0089A7                       1504 00189$:                         ; shift [i..j-1] up
      0089A7 B6 9B            [ 1] 1505     ld      a, *m_j
      0089A9 B1 9A            [ 1] 1506     cp      a, *m_i
      0089AB 23 1D            [ 2] 1507     jrule   00190$
      0089AD B6 9B            [ 1] 1508     ld      a, *m_j
      0089AF 48               [ 1] 1509     sll     a
      0089B0 5F               [ 1] 1510     clrw    x
      0089B1 97               [ 1] 1511     ld      xl, a
      0089B2 89               [ 2] 1512     pushw   x
      0089B3 DE 02 07         [ 2] 1513     ldw     x, (zc_t-2, x)
      0089B6 90 93            [ 1] 1514     ldw     y, x
      0089B8 85               [ 2] 1515     popw    x
      0089B9 DF 02 09         [ 2] 1516     ldw     (zc_t, x), y
      0089BC B6 9B            [ 1] 1517     ld      a, *m_j
      0089BE 5F               [ 1] 1518     clrw    x
      0089BF 97               [ 1] 1519     ld      xl, a
      0089C0 D6 02 12         [ 1] 1520     ld      a, (zc_m-1, x)
      0089C3 D7 02 13         [ 1] 1521     ld      (zc_m, x), a
      0089C6 3A 9B            [ 1] 1522     dec     *m_j
      0089C8 20 DD            [ 2] 1523     jra     00189$
      0089CA                       1524 00190$:
      0089CA B6 9A            [ 1] 1525     ld      a, *m_i
      0089CC 48               [ 1] 1526     sll     a
      0089CD 5F               [ 1] 1527     clrw    x
      0089CE 97               [ 1] 1528     ld      xl, a
      0089CF 90 BE 8A         [ 2] 1529     ldw     y, *m_k
      0089D2 DF 02 09         [ 2] 1530     ldw     (zc_t, x), y
      0089D5 B6 9A            [ 1] 1531     ld      a, *m_i
      0089D7 5F               [ 1] 1532     clrw    x
      0089D8 97               [ 1] 1533     ld      xl, a
      0089D9 B6 9C            [ 1] 1534     ld      a, *m_m
      0089DB D7 02 13         [ 1] 1535     ld      (zc_m, x), a
      0089DE B6 A3            [ 1] 1536     ld      a, *zc_n
      0089E0 A1 05            [ 1] 1537     cp      a, #5
      0089E2 24 03            [ 1] 1538     jrnc    00191$
      0089E4 4C               [ 1] 1539     inc     a
      0089E5 B7 A3            [ 1] 1540     ld      *zc_n, a
      0089E7                       1541 00191$:
      0089E7 81               [ 4] 1542     ret
                                   1543 
                                   1544 ; ------------------------------------------------------------ decide_pass
      0089E8                       1545 _decide_pass:
      0089E8 CE 80 95         [ 2] 1546     ldw     x, _g_NB                ; zero d_bits[0..NBB-1] (NBB = NB/8)
      0089EB 54               [ 2] 1547     srlw    x
      0089EC 54               [ 2] 1548     srlw    x
      0089ED 54               [ 2] 1549     srlw    x
      0089EE                       1550 00200$:
      0089EE 72 4F 01 17      [ 1] 1551     clr     (_ov-1, x)
      0089F2 5A               [ 2] 1552     decw    x
      0089F3 26 F9            [ 1] 1553     jrne    00200$
      0089F5 5F               [ 1] 1554     clrw    x
      0089F6 BF 9D            [ 2] 1555     ldw     *w_inf, x
      0089F8 BF 9F            [ 2] 1556     ldw     *w_lab, x
      0089FA BF A1            [ 2] 1557     ldw     *w_nseg, x
      0089FC BF A4            [ 2] 1558     ldw     *w_nweak, x
      0089FE BF A6            [ 2] 1559     ldw     *w_ntied, x
      008A00 3F A3            [ 1] 1560     clr     *zc_n
      008A02 AE FF FF         [ 2] 1561     ldw     x, #0xFFFF
      008A05 BF 8C            [ 2] 1562     ldw     *w_tiep, x              ; v_tiepend = -1
      008A07 CD 82 58         [ 4] 1563     call    _ss_init
      008A0A                       1564 00201$:                         ; segment loop
      008A0A AE 00 5D         [ 2] 1565     ldw     x, #_g_sg
      008A0D CD 82 B2         [ 4] 1566     call    _ss_next
      008A10 4D               [ 1] 1567     tnz     a
      008A11 26 01            [ 1] 1568     jrne    00202$
      008A13 81               [ 4] 1569     ret
      008A14                       1570 00202$:
      008A14 BE A1            [ 2] 1571     ldw     x, *w_nseg
      008A16 5C               [ 1] 1572     incw    x
      008A17 BF A1            [ 2] 1573     ldw     *w_nseg, x
      008A19 BE 5D            [ 2] 1574     ldw     x, *_g_sg               ; if (k0 >= NB) continue
      008A1B C3 80 95         [ 2] 1575     cpw     x, _g_NB
      008A1E 25 02            [ 1] 1576     jrc     00203$
      008A20 20 E8            [ 2] 1577     jra     00201$
      008A22                       1578 00203$:
      008A22 CD 88 A9         [ 4] 1579     call    dq_decide
      008A25 B6 73            [ 1] 1580     ld      a, *dq_ahat+1           ; c_hat = costs[ahat]
      008A27 48               [ 1] 1581     sll     a
      008A28 5F               [ 1] 1582     clrw    x
      008A29 97               [ 1] 1583     ld      xl, a
      008A2A DE 01 C9         [ 2] 1584     ldw     x, (d_costs, x)
      008A2D A3 00 A0         [ 2] 1585     cpw     x, #160
      008A30 23 05            [ 2] 1586     jrule   00204$
      008A32 BE 9D            [ 2] 1587     ldw     x, *w_inf
      008A34 5C               [ 1] 1588     incw    x
      008A35 BF 9D            [ 2] 1589     ldw     *w_inf, x
      008A37                       1590 00204$:
      008A37 BE 5F            [ 2] 1591     ldw     x, *_g_sg+2             ; kk1 = min(k1, NB)
      008A39 C3 80 95         [ 2] 1592     cpw     x, _g_NB
      008A3C 25 03            [ 1] 1593     jrc     00205$
      008A3E CE 80 95         [ 2] 1594     ldw     x, _g_NB
      008A41                       1595 00205$:
      008A41 BF 84            [ 2] 1596     ldw     *m_e, x
      008A43 35 01 00 96      [ 1] 1597     mov     m_ka, #1            ; known_all over [k0, kk1)
      008A47 BE 5D            [ 2] 1598     ldw     x, *_g_sg
      008A49 BF 86            [ 2] 1599     ldw     *m_t, x
      008A4B                       1600 00206$:
      008A4B BE 86            [ 2] 1601     ldw     x, *m_t
      008A4D B3 84            [ 2] 1602     cpw     x, *m_e
      008A4F 24 11            [ 1] 1603     jrnc    00208$
      008A51 CD 87 57         [ 4] 1604     call    _known_bit
      008A54 4D               [ 1] 1605     tnz     a
      008A55 2A 04            [ 1] 1606     jrpl    00207$
      008A57 3F 96            [ 1] 1607     clr     *m_ka
      008A59 20 07            [ 2] 1608     jra     00208$
      008A5B                       1609 00207$:
      008A5B BE 86            [ 2] 1610     ldw     x, *m_t
      008A5D 5C               [ 1] 1611     incw    x
      008A5E BF 86            [ 2] 1612     ldw     *m_t, x
      008A60 20 E9            [ 2] 1613     jra     00206$
      008A62                       1614 00208$:
      008A62 3F 97            [ 1] 1615     clr     *m_n1                   ; nins over 0..acap (dead detector)
      008A64 3F 92            [ 1] 1616     clr     *m_ai2
      008A66                       1617 00209$:
      008A66 CD 88 29         [ 4] 1618     call    getbit
      008A69 4D               [ 1] 1619     tnz     a
      008A6A 27 02            [ 1] 1620     jreq    00210$
      008A6C 3C 97            [ 1] 1621     inc     *m_n1
      008A6E                       1622 00210$:
      008A6E B6 92            [ 1] 1623     ld      a, *m_ai2
      008A70 4C               [ 1] 1624     inc     a
      008A71 B7 92            [ 1] 1625     ld      *m_ai2, a
      008A73 B1 6D            [ 1] 1626     cp      a, *dq_acap+1
      008A75 23 EF            [ 2] 1627     jrule   00209$
      008A77 3D 96            [ 1] 1628     tnz     *m_ka                   ; laberr: known_all && lo==hi &&
      008A79 27 17            [ 1] 1629     jreq    00212$              ;         afree != lo && !dead
      008A7B B6 97            [ 1] 1630     ld      a, *m_n1
      008A7D A1 02            [ 1] 1631     cp      a, #2
      008A7F 24 11            [ 1] 1632     jrnc    00212$
      008A81 BE 6E            [ 2] 1633     ldw     x, *dq_lo
      008A83 B3 70            [ 2] 1634     cpw     x, *dq_hi
      008A85 26 0B            [ 1] 1635     jrne    00212$
      008A87 BE 74            [ 2] 1636     ldw     x, *dq_afree
      008A89 B3 6E            [ 2] 1637     cpw     x, *dq_lo
      008A8B 27 05            [ 1] 1638     jreq    00212$
      008A8D BE 9F            [ 2] 1639     ldw     x, *w_lab
      008A8F 5C               [ 1] 1640     incw    x
      008A90 BF 9F            [ 2] 1641     ldw     *w_lab, x
      008A92                       1642 00212$:
      008A92 35 FF 00 98      [ 1] 1643     mov     m_i0, #0xFF         ; ins0/ins1 over [lo,hi]
      008A96 35 FF 00 99      [ 1] 1644     mov     m_i1, #0xFF
      008A9A 3F 97            [ 1] 1645     clr     *m_n1
      008A9C B6 6F            [ 1] 1646     ld      a, *dq_lo+1
      008A9E B7 92            [ 1] 1647     ld      *m_ai2, a
      008AA0                       1648 00213$:
      008AA0 CD 88 29         [ 4] 1649     call    getbit
      008AA3 4D               [ 1] 1650     tnz     a
      008AA4 27 18            [ 1] 1651     jreq    00215$
      008AA6 3C 97            [ 1] 1652     inc     *m_n1
      008AA8 B6 98            [ 1] 1653     ld      a, *m_i0
      008AAA A1 FF            [ 1] 1654     cp      a, #0xFF
      008AAC 26 06            [ 1] 1655     jrne    00214$
      008AAE B6 92            [ 1] 1656     ld      a, *m_ai2
      008AB0 B7 98            [ 1] 1657     ld      *m_i0, a
      008AB2 20 0A            [ 2] 1658     jra     00215$
      008AB4                       1659 00214$:
      008AB4 B6 99            [ 1] 1660     ld      a, *m_i1
      008AB6 A1 FF            [ 1] 1661     cp      a, #0xFF
      008AB8 26 04            [ 1] 1662     jrne    00215$
      008ABA B6 92            [ 1] 1663     ld      a, *m_ai2
      008ABC B7 99            [ 1] 1664     ld      *m_i1, a
      008ABE                       1665 00215$:
      008ABE B6 92            [ 1] 1666     ld      a, *m_ai2
      008AC0 4C               [ 1] 1667     inc     a
      008AC1 B7 92            [ 1] 1668     ld      *m_ai2, a
      008AC3 B1 71            [ 1] 1669     cp      a, *dq_hi+1
      008AC5 23 D9            [ 2] 1670     jrule   00213$
      008AC7 AE FF FF         [ 2] 1671     ldw     x, #0xFFFF              ; tie_here = -1
      008ACA BF 8E            [ 2] 1672     ldw     *w_tieh, x
      008ACC B6 97            [ 1] 1673     ld      a, *m_n1
      008ACE A1 02            [ 1] 1674     cp      a, #2
      008AD0 25 19            [ 1] 1675     jrc     00218$
      008AD2 B6 73            [ 1] 1676     ld      a, *dq_ahat+1
      008AD4 B1 98            [ 1] 1677     cp      a, *m_i0
      008AD6 27 04            [ 1] 1678     jreq    00216$
      008AD8 B1 99            [ 1] 1679     cp      a, *m_i1
      008ADA 26 0F            [ 1] 1680     jrne    00218$
      008ADC                       1681 00216$:
      008ADC 5F               [ 1] 1682     clrw    x                   ; tt = k0 + ins0; if (tt < NB) tie
      008ADD B6 98            [ 1] 1683     ld      a, *m_i0
      008ADF 97               [ 1] 1684     ld      xl, a
      008AE0 72 BB 00 5D      [ 2] 1685     addw    x, _g_sg
      008AE4 C3 80 95         [ 2] 1686     cpw     x, _g_NB
      008AE7 24 02            [ 1] 1687     jrnc    00218$
      008AE9 BF 8E            [ 2] 1688     ldw     *w_tieh, x
      008AEB                       1689 00218$:
      008AEB AE FF FF         [ 2] 1690     ldw     x, #0xFFFF              ; suffix-min d_sm over [lo..hi]
      008AEE BF 7E            [ 2] 1691     ldw     *m_c, x
      008AF0 B6 71            [ 1] 1692     ld      a, *dq_hi+1
      008AF2 B7 92            [ 1] 1693     ld      *m_ai2, a
      008AF4                       1694 00219$:
      008AF4 B6 92            [ 1] 1695     ld      a, *m_ai2
      008AF6 48               [ 1] 1696     sll     a
      008AF7 5F               [ 1] 1697     clrw    x
      008AF8 97               [ 1] 1698     ld      xl, a
      008AF9 DE 01 C9         [ 2] 1699     ldw     x, (d_costs, x)
      008AFC B3 7E            [ 2] 1700     cpw     x, *m_c
      008AFE 24 02            [ 1] 1701     jrnc    00220$
      008B00 BF 7E            [ 2] 1702     ldw     *m_c, x
      008B02                       1703 00220$:
      008B02 B6 92            [ 1] 1704     ld      a, *m_ai2
      008B04 48               [ 1] 1705     sll     a
      008B05 5F               [ 1] 1706     clrw    x
      008B06 97               [ 1] 1707     ld      xl, a
      008B07 90 BE 7E         [ 2] 1708     ldw     y, *m_c
      008B0A DF 01 E9         [ 2] 1709     ldw     (d_sm, x), y
      008B0D B6 92            [ 1] 1710     ld      a, *m_ai2
      008B0F B1 6F            [ 1] 1711     cp      a, *dq_lo+1
      008B11 27 04            [ 1] 1712     jreq    00221$
      008B13 3A 92            [ 1] 1713     dec     *m_ai2
      008B15 20 DD            [ 2] 1714     jra     00219$
      008B17                       1715 00221$:
      008B17 AE FF FF         [ 2] 1716     ldw     x, #0xFFFF              ; c0m online
      008B1A BF 80            [ 2] 1717     ldw     *m_c0, x
      008B1C BE 5D            [ 2] 1718     ldw     x, *_g_sg
      008B1E BF 86            [ 2] 1719     ldw     *m_t, x
      008B20                       1720 00222$:                         ; per-bit loop
      008B20 BE 86            [ 2] 1721     ldw     x, *m_t
      008B22 B3 84            [ 2] 1722     cpw     x, *m_e
      008B24 25 03            [ 1] 1723     jrc     00223$
      008B26 CC 8B E3         [ 2] 1724     jp      00240$
      008B29                       1725 00223$:
      008B29 BE 86            [ 2] 1726     ldw     x, *m_t
      008B2B 72 B0 00 5D      [ 2] 1727     subw    x, _g_sg
      008B2F BF 88            [ 2] 1728     ldw     *m_off, x
      008B31 B3 72            [ 2] 1729     cpw     x, *dq_ahat             ; bit: off < ahat
      008B33 24 1B            [ 1] 1730     jrnc    00226$
      008B35 BE 86            [ 2] 1731     ldw     x, *m_t                 ; BSET(d_bits, t): LSB-first in byte
      008B37 9F               [ 1] 1732     ld      a, xl
      008B38 A4 07            [ 1] 1733     and     a, #7
      008B3A B7 0D            [ 1] 1734     ld      *m_s, a
      008B3C 54               [ 2] 1735     srlw    x
      008B3D 54               [ 2] 1736     srlw    x
      008B3E 54               [ 2] 1737     srlw    x
      008B3F A6 01            [ 1] 1738     ld      a, #1
      008B41 3D 0D            [ 1] 1739     tnz     *m_s
      008B43 27 05            [ 1] 1740     jreq    00225$
      008B45                       1741 00224$:
      008B45 48               [ 1] 1742     sll     a
      008B46 3A 0D            [ 1] 1743     dec     *m_s
      008B48 26 FB            [ 1] 1744     jrne    00224$
      008B4A                       1745 00225$:
      008B4A DA 01 18         [ 1] 1746     or      a, (_ov, x)
      008B4D D7 01 18         [ 1] 1747     ld      (_ov, x), a
      008B50                       1748 00226$:
      008B50 BE 88            [ 2] 1749     ldw     x, *m_off               ; c0m: lo <= off <= hi
      008B52 B3 6E            [ 2] 1750     cpw     x, *dq_lo
      008B54 25 12            [ 1] 1751     jrc     00228$
      008B56 B3 70            [ 2] 1752     cpw     x, *dq_hi
      008B58 22 0E            [ 1] 1753     jrugt   00228$
      008B5A B6 89            [ 1] 1754     ld      a, *m_off+1
      008B5C 48               [ 1] 1755     sll     a
      008B5D 5F               [ 1] 1756     clrw    x
      008B5E 97               [ 1] 1757     ld      xl, a
      008B5F DE 01 C9         [ 2] 1758     ldw     x, (d_costs, x)
      008B62 B3 80            [ 2] 1759     cpw     x, *m_c0
      008B64 24 02            [ 1] 1760     jrnc    00228$
      008B66 BF 80            [ 2] 1761     ldw     *m_c0, x
      008B68                       1762 00228$:
      008B68 BE 88            [ 2] 1763     ldw     x, *m_off               ; c1m = sm[max(lo, off+1)] or 0xFFFF
      008B6A 5C               [ 1] 1764     incw    x
      008B6B B3 6E            [ 2] 1765     cpw     x, *dq_lo
      008B6D 24 02            [ 1] 1766     jrnc    00229$
      008B6F BE 6E            [ 2] 1767     ldw     x, *dq_lo
      008B71                       1768 00229$:
      008B71 B3 70            [ 2] 1769     cpw     x, *dq_hi
      008B73 23 05            [ 2] 1770     jrule   00230$
      008B75 AE FF FF         [ 2] 1771     ldw     x, #0xFFFF
      008B78 20 07            [ 2] 1772     jra     00231$
      008B7A                       1773 00230$:
      008B7A 9F               [ 1] 1774     ld      a, xl
      008B7B 48               [ 1] 1775     sll     a
      008B7C 5F               [ 1] 1776     clrw    x
      008B7D 97               [ 1] 1777     ld      xl, a
      008B7E DE 01 E9         [ 2] 1778     ldw     x, (d_sm, x)
      008B81                       1779 00231$:
      008B81 BF 82            [ 2] 1780     ldw     *m_c1, x
      008B83 BE 80            [ 2] 1781     ldw     x, *m_c0                ; m = 255 | min(255, |c0m - c1m|)
      008B85 A3 FF FF         [ 2] 1782     cpw     x, #0xFFFF
      008B88 27 15            [ 1] 1783     jreq    00233$
      008B8A BE 82            [ 2] 1784     ldw     x, *m_c1
      008B8C A3 FF FF         [ 2] 1785     cpw     x, #0xFFFF
      008B8F 27 0E            [ 1] 1786     jreq    00233$
      008B91 BE 80            [ 2] 1787     ldw     x, *m_c0
      008B93 72 B0 00 82      [ 2] 1788     subw    x, m_c1
      008B97 2A 01            [ 1] 1789     jrpl    00232$
      008B99 50               [ 2] 1790     negw    x
      008B9A                       1791 00232$:
      008B9A A3 00 FF         [ 2] 1792     cpw     x, #255
      008B9D 25 03            [ 1] 1793     jrc     00234$
      008B9F                       1794 00233$:
      008B9F AE 00 FF         [ 2] 1795     ldw     x, #255
      008BA2                       1796 00234$:
      008BA2 9F               [ 1] 1797     ld      a, xl
      008BA3 B7 9C            [ 1] 1798     ld      *m_m, a
      008BA5 BE 86            [ 2] 1799     ldw     x, *m_t                 ; tie overrides -> m = 0
      008BA7 B3 8E            [ 2] 1800     cpw     x, *w_tieh
      008BA9 27 04            [ 1] 1801     jreq    00235$
      008BAB B3 8C            [ 2] 1802     cpw     x, *w_tiep
      008BAD 26 02            [ 1] 1803     jrne    00236$
      008BAF                       1804 00235$:
      008BAF 3F 9C            [ 1] 1805     clr     *m_m
      008BB1                       1806 00236$:
      008BB1 BE 86            [ 2] 1807     ldw     x, *m_t                 ; payload' window
      008BB3 A3 00 20         [ 2] 1808     cpw     x, #32
      008BB6 25 23            [ 1] 1809     jrc     00239$
      008BB8 C3 80 A5         [ 2] 1810     cpw     x, _g_PPHI
      008BBB 24 1E            [ 1] 1811     jrnc    00239$
      008BBD B6 9C            [ 1] 1812     ld      a, *m_m                 ; weak?
      008BBF A1 08            [ 1] 1813     cp      a, #8
      008BC1 22 18            [ 1] 1814     jrugt   00239$
      008BC3 BE A4            [ 2] 1815     ldw     x, *w_nweak
      008BC5 5C               [ 1] 1816     incw    x
      008BC6 BF A4            [ 2] 1817     ldw     *w_nweak, x
      008BC8 3D 9C            [ 1] 1818     tnz     *m_m
      008BCA 26 05            [ 1] 1819     jrne    00237$
      008BCC BE A6            [ 2] 1820     ldw     x, *w_ntied
      008BCE 5C               [ 1] 1821     incw    x
      008BCF BF A6            [ 2] 1822     ldw     *w_ntied, x
      008BD1                       1823 00237$:
      008BD1 BE 86            [ 2] 1824     ldw     x, *m_t
      008BD3 1D 00 20         [ 2] 1825     subw    x, #32
      008BD6 B6 9C            [ 1] 1826     ld      a, *m_m
      008BD8 CD 89 7A         [ 4] 1827     call    candi
      008BDB                       1828 00239$:
      008BDB BE 86            [ 2] 1829     ldw     x, *m_t
      008BDD 5C               [ 1] 1830     incw    x
      008BDE BF 86            [ 2] 1831     ldw     *m_t, x
      008BE0 CC 8B 20         [ 2] 1832     jp      00222$
      008BE3                       1833 00240$:                         ; segment epilogue: tiepend consume/set
      008BE3 BE 8C            [ 2] 1834     ldw     x, *w_tiep
      008BE5 2B 09            [ 1] 1835     jrmi    00241$
      008BE7 B3 84            [ 2] 1836     cpw     x, *m_e
      008BE9 24 05            [ 1] 1837     jrnc    00241$
      008BEB AE FF FF         [ 2] 1838     ldw     x, #0xFFFF
      008BEE BF 8C            [ 2] 1839     ldw     *w_tiep, x
      008BF0                       1840 00241$:
      008BF0 BE 8E            [ 2] 1841     ldw     x, *w_tieh
      008BF2 2B 06            [ 1] 1842     jrmi    00242$
      008BF4 B3 84            [ 2] 1843     cpw     x, *m_e
      008BF6 25 02            [ 1] 1844     jrc     00242$
      008BF8 BF 8C            [ 2] 1845     ldw     *w_tiep, x
      008BFA                       1846 00242$:
      008BFA CC 8A 0A         [ 2] 1847     jp      00201$
                                   1848 
                                   1849 ; ======================================================================
                                   1850 ; CRC8 confidence chase (spec SS7) + ws_decode_ex -- the pipeline tail.
                                   1851 ; Bit-exact port of decode.c's C versions (which remain the host-parity
                                   1852 ; reference under !USE_ASM_DEC).
                                   1853 ; ======================================================================
                                   1854 
                                   1855     .globl _ws_decode_ex
                                   1856     .globl _g_ND
                                   1857     .globl _g_ND8
                                   1858     .globl _g_NPP
                                   1859     .globl _g_CHK
                                   1860 
                                   1861     .area CODE
                                   1862 
                                   1863 ; syn8: X = payload'-relative DATA bit k -> A = x^((ND8+7-k) % 127) in
                                   1864 ; GF(2^8) mod x^8+x^2+x+1.  (8*(ND-1-p)+b+8 algebraically = ND8+7-k.)
                                   1865 ; Computed by repeated xtime instead of the 127-B XPOW flash table --
                                   1866 ; identical values (ord(x) = 127); ~7 cy per step, <= 126 steps, and
                                   1867 ; syn8 runs only on chase trials (~60 calls worst case).
      008BFD                       1868 syn8k:
      008BFD 50               [ 2] 1869     negw    x
      008BFE 72 BB 80 A9      [ 2] 1870     addw    x, _g_ND8
      008C02 1C 00 07         [ 2] 1871     addw    x, #7
      008C05                       1872 00300$:
      008C05 A3 00 7F         [ 2] 1873     cpw     x, #127
      008C08 25 05            [ 1] 1874     jrc     00301$
      008C0A 1D 00 7F         [ 2] 1875     subw    x, #127
      008C0D 20 F6            [ 2] 1876     jra     00300$
      008C0F                       1877 00301$:
      008C0F A6 01            [ 1] 1878     ld      a, #1
      008C11                       1879 00302$:
      008C11 5D               [ 2] 1880     tnzw    x
      008C12 27 08            [ 1] 1881     jreq    00303$
      008C14 48               [ 1] 1882     sll     a                   ; a = xtime(a)
      008C15 24 02            [ 1] 1883     jrnc    00304$
      008C17 A8 07            [ 1] 1884     xor     a, #0x07
      008C19                       1885 00304$:
      008C19 5A               [ 2] 1886     decw    x
      008C1A 20 F5            [ 2] 1887     jra     00302$
      008C1C                       1888 00303$:
      008C1C 81               [ 4] 1889     ret
                                   1890 
                                   1891 ; crc8 over d_pp[0..ND-1] -> A  (bitwise, poly 0x07)
      008C1D                       1892 crc8pp:
      008C1D 4F               [ 1] 1893     clr     a
      008C1E 5F               [ 1] 1894     clrw    x
      008C1F                       1895 00305$:
      008C1F 72 D8 00 A8      [ 4] 1896     xor     a, ([m_pp], x)
      008C23 35 08 00 0D      [ 1] 1897     mov     *m_s, #8
      008C27                       1898 00306$:
      008C27 48               [ 1] 1899     sll     a
      008C28 24 02            [ 1] 1900     jrnc    00307$
      008C2A A8 07            [ 1] 1901     xor     a, #0x07
      008C2C                       1902 00307$:
      008C2C 3A 0D            [ 1] 1903     dec     *m_s
      008C2E 26 F7            [ 1] 1904     jrne    00306$
      008C30 5C               [ 1] 1905     incw    x
      008C31 C3 80 A7         [ 2] 1906     cpw     x, _g_ND
      008C34 25 E9            [ 1] 1907     jrc     00305$
      008C36 81               [ 4] 1908     ret
                                   1909 
                                   1910 ; majz: unique >=2-vote majority over m_cp[0..g_CHK-1] -> A = have_R,
                                   1911 ; *m_R = reference.  No >=2-vote value (full split) or two DISTINCT such
                                   1912 ; values (the 2-2 tie, possible at g_CHK = 4) -> A = 0.  At g_CHK = 3
                                   1913 ; this is exactly the old 2-of-3 rule.  Mirrors decode.c maj_n /
                                   1914 ; embedded_v2._majn (same counting loop).
                                   1915 ; Clobbers A, X, m_s, m_i, m_j, m_m -- all dead at both call sites
                                   1916 ; (m_i/m_j are talias-local, m_m/m_s are earlier-pass scratch).
      008C37                       1917 majz:
      008C37 3F 9C            [ 1] 1918     clr     *m_m                ; have = 0
      008C39 3F 9A            [ 1] 1919     clr     *m_i
      008C3B                       1920 00800$:                         ; outer: candidate = m_cp[i]
      008C3B B6 9A            [ 1] 1921     ld      a, *m_i
      008C3D C1 80 AD         [ 1] 1922     cp      a, _g_CHK
      008C40 24 3C            [ 1] 1923     jrnc    00806$
      008C42 5F               [ 1] 1924     clrw    x
      008C43 97               [ 1] 1925     ld      xl, a
      008C44 D6 00 24         [ 1] 1926     ld      a, (m_cp, x)
      008C47 B7 0D            [ 1] 1927     ld      *m_s, a             ; candidate value
      008C49 3F 9B            [ 1] 1928     clr     *m_j                ; count its votes
      008C4B 4B 00            [ 1] 1929     push    #0
      008C4D                       1930 00801$:
      008C4D B6 9B            [ 1] 1931     ld      a, *m_j
      008C4F C1 80 AD         [ 1] 1932     cp      a, _g_CHK
      008C52 24 0F            [ 1] 1933     jrnc    00802$
      008C54 5F               [ 1] 1934     clrw    x
      008C55 97               [ 1] 1935     ld      xl, a
      008C56 D6 00 24         [ 1] 1936     ld      a, (m_cp, x)
      008C59 B1 0D            [ 1] 1937     cp      a, *m_s
      008C5B 26 02            [ 1] 1938     jrne    00803$
      008C5D 0C 01            [ 1] 1939     inc     (1, sp)
      008C5F                       1940 00803$:
      008C5F 3C 9B            [ 1] 1941     inc     *m_j
      008C61 20 EA            [ 2] 1942     jra     00801$
      008C63                       1943 00802$:
      008C63 84               [ 1] 1944     pop     a                   ; votes for m_cp[i]
      008C64 A1 02            [ 1] 1945     cp      a, #2
      008C66 25 12            [ 1] 1946     jrc     00805$              ; < 2 votes: not a winner
      008C68 3D 9C            [ 1] 1947     tnz     *m_m
      008C6A 27 08            [ 1] 1948     jreq    00804$              ; first >=2-vote value
      008C6C B6 0D            [ 1] 1949     ld      a, *m_s
      008C6E B1 AC            [ 1] 1950     cp      a, *m_R
      008C70 27 08            [ 1] 1951     jreq    00805$              ; the same winner again
      008C72 4F               [ 1] 1952     clr     a                   ; second DISTINCT winner: 2-2 tie
      008C73 81               [ 4] 1953     ret
      008C74                       1954 00804$:
      008C74 B7 9C            [ 1] 1955     ld      *m_m, a             ; have = votes (>= 2, so truthy)
      008C76 B6 0D            [ 1] 1956     ld      a, *m_s
      008C78 B7 AC            [ 1] 1957     ld      *m_R, a
      008C7A                       1958 00805$:
      008C7A 3C 9A            [ 1] 1959     inc     *m_i
      008C7C 20 BD            [ 2] 1960     jra     00800$
      008C7E                       1961 00806$:
      008C7E B6 9C            [ 1] 1962     ld      a, *m_m
      008C80 81               [ 4] 1963     ret
                                   1964 
                                   1965 ; ldcpz: m_cp[0..g_CHK-1] = d_pp[ND..ND+g_CHK-1] (the decoded check
                                   1966 ; block).  At g_CHK = 3 the stale m_cp[3] is never read: majz counts and
                                   1967 ; cpflip indexes strictly below g_CHK.  Clobbers A, X.
      008C81                       1968 ldcpz:
      008C81 BE A8            [ 2] 1969     ldw     x, *m_pp
      008C83 72 BB 80 A7      [ 2] 1970     addw    x, _g_ND
      008C87 F6               [ 1] 1971     ld      a, (x)
      008C88 B7 24            [ 1] 1972     ld      *m_cp+0, a
      008C8A E6 01            [ 1] 1973     ld      a, (1, x)
      008C8C B7 25            [ 1] 1974     ld      *m_cp+1, a
      008C8E E6 02            [ 1] 1975     ld      a, (2, x)
      008C90 B7 26            [ 1] 1976     ld      *m_cp+2, a
      008C92 C6 80 AD         [ 1] 1977     ld      a, _g_CHK
      008C95 A1 04            [ 1] 1978     cp      a, #4
      008C97 26 04            [ 1] 1979     jrne    00810$
      008C99 E6 03            [ 1] 1980     ld      a, (3, x)
      008C9B B7 27            [ 1] 1981     ld      *m_cp+3, a
      008C9D                       1982 00810$:
      008C9D 81               [ 4] 1983     ret
                                   1984 
                                   1985 ; parity of A -> A (0/1)
      008C9E                       1986 par8:
      008C9E B7 0D            [ 1] 1987     ld      *m_s, a
      008CA0 4F               [ 1] 1988     clr     a
      008CA1 4B 08            [ 1] 1989     push    #8
      008CA3                       1990 00315$:
      008CA3 34 0D            [ 1] 1991     srl     *m_s
      008CA5 24 01            [ 1] 1992     jrnc    00316$
      008CA7 4C               [ 1] 1993     inc     a
      008CA8                       1994 00316$:
      008CA8 0A 01            [ 1] 1995     dec     (1, sp)
      008CAA 26 F7            [ 1] 1996     jrne    00315$
      008CAC 5B 01            [ 2] 1997     addw    sp, #1
      008CAE A4 01            [ 1] 1998     and     a, #1
      008CB0 81               [ 4] 1999     ret
                                   2000 
                                   2001 ; cand bit index for trial slot A -> X = zc_t[A]
      008CB1                       2002 candk:
      008CB1 48               [ 1] 2003     sll     a
      008CB2 5F               [ 1] 2004     clrw    x
      008CB3 97               [ 1] 2005     ld      xl, a
      008CB4 DE 02 09         [ 2] 2006     ldw     x, (zc_t, x)
      008CB7 81               [ 4] 2007     ret
                                   2008 
                                   2009 ; try_trial: *m_ti, *m_tj (0xFF = none) -> A = 1 accepted (flips applied)
      008CB8                       2010 trial:
      008CB8 B6 B4            [ 1] 2011     ld      a, *m_rb
      008CBA B7 B0            [ 1] 2012     ld      *m_rr, a            ; r = rbase
      008CBC CD 8C 81         [ 4] 2013     call    ldcpz               ; Cp[] = d_pp[ND..ND+g_CHK-1]
      008CBF 72 5C 01 02      [ 1] 2014     inc     _dec_info+2         ; trials++
      008CC3 B6 AE            [ 1] 2015     ld      a, *m_ti            ; flip set members
      008CC5 CD 8C FC         [ 4] 2016     call    tflip
      008CC8 B6 AF            [ 1] 2017     ld      a, *m_tj
      008CCA CD 8C FC         [ 4] 2018     call    tflip
      008CCD CD 8C 37         [ 4] 2019     call    majz                ; R' majority (may be created/destroyed)
      008CD0 4D               [ 1] 2020     tnz     a
      008CD1 26 02            [ 1] 2021     jrne    00320$
      008CD3 4F               [ 1] 2022     clr     a
      008CD4 81               [ 4] 2023     ret                         ; slot burned, no reference
      008CD5                       2024 00320$:
      008CD5 B6 B0            [ 1] 2025     ld      a, *m_rr
      008CD7 B1 AC            [ 1] 2026     cp      a, *m_R
      008CD9 27 02            [ 1] 2027     jreq    00321$
      008CDB 4F               [ 1] 2028     clr     a
      008CDC 81               [ 4] 2029     ret
      008CDD                       2030 00321$:
                                   2031     ; alias guard: any flipped DATA bit sharing a syndrome with an
                                   2032     ; out-of-set data candidate rejects the trial (SS7.7)
      008CDD B6 AE            [ 1] 2033     ld      a, *m_ti
      008CDF CD 8D 38         [ 4] 2034     call    talias
      008CE2 4D               [ 1] 2035     tnz     a
      008CE3 26 08            [ 1] 2036     jrne    00322$
      008CE5 B6 AF            [ 1] 2037     ld      a, *m_tj
      008CE7 CD 8D 38         [ 4] 2038     call    talias
      008CEA 4D               [ 1] 2039     tnz     a
      008CEB 27 02            [ 1] 2040     jreq    00323$
      008CED                       2041 00322$:
      008CED 4F               [ 1] 2042     clr     a
      008CEE 81               [ 4] 2043     ret                         ; ambiguous
      008CEF                       2044 00323$:
                                   2045     ; accept: apply DATA flips
      008CEF B6 AE            [ 1] 2046     ld      a, *m_ti
      008CF1 CD 8D 7D         [ 4] 2047     call    tapply
      008CF4 B6 AF            [ 1] 2048     ld      a, *m_tj
      008CF6 CD 8D 7D         [ 4] 2049     call    tapply
      008CF9 A6 01            [ 1] 2050     ld      a, #1
      008CFB 81               [ 4] 2051     ret
                                   2052 
                                   2053 ; tflip: candidate slot A (0xFF = none): data bit -> r ^= syn8;
                                   2054 ; check bit -> toggle Cp
      008CFC                       2055 tflip:
      008CFC A1 FF            [ 1] 2056     cp      a, #0xFF
      008CFE 26 01            [ 1] 2057     jrne    00330$
      008D00 81               [ 4] 2058     ret
      008D01                       2059 00330$:
      008D01 CD 8C B1         [ 4] 2060     call    candk               ; X = k
      008D04 C3 80 A9         [ 2] 2061     cpw     x, _g_ND8
      008D07 24 08            [ 1] 2062     jrnc    00331$
      008D09 CD 8B FD         [ 4] 2063     call    syn8k               ; data bit
      008D0C B8 B0            [ 1] 2064     xor     a, *m_rr
      008D0E B7 B0            [ 1] 2065     ld      *m_rr, a
      008D10 81               [ 4] 2066     ret
      008D11                       2067 00331$:
      008D11 CC 8D 25         [ 2] 2068     jp      cpflip
                                   2069 ; bitmz: X = payload'-relative bit index k -> A = 0x80 >> (k & 7), the
                                   2070 ; MSB-first mask of bit k inside its byte; X is PRESERVED so the caller
                                   2071 ; can go on to derive the byte offset.  Factored out of cpflip and
                                   2072 ; tapply (which held byte-identical copies of this shifter) to pay for
                                   2073 ; the SS7.10 W2 bound in cpair without growing the image.
      008D14                       2074 bitmz:
      008D14 9F               [ 1] 2075     ld      a, xl
      008D15 A4 07            [ 1] 2076     and     a, #7
      008D17 B7 0D            [ 1] 2077     ld      *m_s, a
      008D19 A6 80            [ 1] 2078     ld      a, #0x80            ; 1 << (7-(k&7)) = 0x80 >> (k&7)
      008D1B 3D 0D            [ 1] 2079     tnz     *m_s
      008D1D 27 05            [ 1] 2080     jreq    00333$
      008D1F                       2081 00332$:
      008D1F 44               [ 1] 2082     srl     a
      008D20 3A 0D            [ 1] 2083     dec     *m_s
      008D22 26 FB            [ 1] 2084     jrne    00332$
      008D24                       2085 00333$:
      008D24 81               [ 4] 2086     ret
                                   2087 
                                   2088 ; toggle check-block bit k (X >= ND8): Cp[(k-ND8)>>3] ^= 1 << (7-(k&7))
      008D25                       2089 cpflip:
      008D25 CD 8D 14         [ 4] 2090     call    bitmz
      008D28 88               [ 1] 2091     push    a
      008D29 72 B0 80 A9      [ 2] 2092     subw    x, _g_ND8
      008D2D 54               [ 2] 2093     srlw    x
      008D2E 54               [ 2] 2094     srlw    x
      008D2F 54               [ 2] 2095     srlw    x                   ; X = kc>>3 (0..2)
      008D30 84               [ 1] 2096     pop     a
      008D31 D8 00 24         [ 1] 2097     xor     a, (m_cp, x)
      008D34 D7 00 24         [ 1] 2098     ld      (m_cp, x), a
      008D37 81               [ 4] 2099     ret
                                   2100 
                                   2101 ; talias: candidate slot A (data bits only): A = 1 if its syndrome
                                   2102 ; collides with any out-of-set data candidate (counts alias_cmp)
      008D38                       2103 talias:
      008D38 A1 FF            [ 1] 2104     cp      a, #0xFF
      008D3A 26 02            [ 1] 2105     jrne    00340$
      008D3C 4F               [ 1] 2106     clr     a
      008D3D 81               [ 4] 2107     ret
      008D3E                       2108 00340$:
      008D3E B7 9A            [ 1] 2109     ld      *m_i, a
      008D40 CD 8C B1         [ 4] 2110     call    candk
      008D43 C3 80 A9         [ 2] 2111     cpw     x, _g_ND8
      008D46 25 02            [ 1] 2112     jrc     00341$
      008D48 4F               [ 1] 2113     clr     a                   ; check bit: no syndrome
      008D49 81               [ 4] 2114     ret
      008D4A                       2115 00341$:
      008D4A CD 8B FD         [ 4] 2116     call    syn8k
      008D4D B7 B1            [ 1] 2117     ld      *m_si, a
      008D4F 3F 9B            [ 1] 2118     clr     *m_j                ; jj loop
      008D51                       2119 00342$:
      008D51 B6 9B            [ 1] 2120     ld      a, *m_j
      008D53 B1 B5            [ 1] 2121     cp      a, *m_cn
      008D55 24 24            [ 1] 2122     jrnc    00347$              ; done, no collision
      008D57 B1 AE            [ 1] 2123     cp      a, *m_ti
      008D59 27 1C            [ 1] 2124     jreq    00346$
      008D5B B1 AF            [ 1] 2125     cp      a, *m_tj
      008D5D 27 18            [ 1] 2126     jreq    00346$
      008D5F B6 9B            [ 1] 2127     ld      a, *m_j
      008D61 CD 8C B1         [ 4] 2128     call    candk
      008D64 C3 80 A9         [ 2] 2129     cpw     x, _g_ND8
      008D67 24 0E            [ 1] 2130     jrnc    00346$              ; not a data bit
      008D69 72 5C 01 03      [ 1] 2131     inc     _dec_info+3         ; alias_cmp++
      008D6D CD 8B FD         [ 4] 2132     call    syn8k
      008D70 B1 B1            [ 1] 2133     cp      a, *m_si
      008D72 26 03            [ 1] 2134     jrne    00346$
      008D74 A6 01            [ 1] 2135     ld      a, #1
      008D76 81               [ 4] 2136     ret
      008D77                       2137 00346$:
      008D77 3C 9B            [ 1] 2138     inc     *m_j
      008D79 20 D6            [ 2] 2139     jra     00342$
      008D7B                       2140 00347$:
      008D7B 4F               [ 1] 2141     clr     a
      008D7C 81               [ 4] 2142     ret
                                   2143 
                                   2144 ; tapply: candidate slot A: flip the DATA bit in d_pp (check bits no-op)
      008D7D                       2145 tapply:
      008D7D A1 FF            [ 1] 2146     cp      a, #0xFF
      008D7F 26 01            [ 1] 2147     jrne    00350$
      008D81 81               [ 4] 2148     ret
      008D82                       2149 00350$:
      008D82 CD 8C B1         [ 4] 2150     call    candk
      008D85 C3 80 A9         [ 2] 2151     cpw     x, _g_ND8
      008D88 25 01            [ 1] 2152     jrc     00351$
      008D8A 81               [ 4] 2153     ret
      008D8B                       2154 00351$:
      008D8B CD 8D 14         [ 4] 2155     call    bitmz
      008D8E 88               [ 1] 2156     push    a
      008D8F 54               [ 2] 2157     srlw    x
      008D90 54               [ 2] 2158     srlw    x
      008D91 54               [ 2] 2159     srlw    x
      008D92 84               [ 1] 2160     pop     a
      008D93 72 D8 00 A8      [ 4] 2161     xor     a, ([m_pp], x)
      008D97 72 D7 00 A8      [ 4] 2162     ld      ([m_pp], x), a
      008D9B 81               [ 4] 2163     ret
                                   2164 
                                   2165 ; chase phase engines: singles (want in *m_ww) / pairs (sum in *m_ww);
                                   2166 ; the pair engine also enforces the SS7.10 W2 bound (see 00371$)
      008D9C                       2167 csing:
      008D9C 3F AE            [ 1] 2168     clr     *m_ti
      008D9E                       2169 00360$:
      008D9E B6 AE            [ 1] 2170     ld      a, *m_ti
      008DA0 B1 B5            [ 1] 2171     cp      a, *m_cn
      008DA2 24 17            [ 1] 2172     jrnc    00362$
      008DA4 5F               [ 1] 2173     clrw    x
      008DA5 97               [ 1] 2174     ld      xl, a
      008DA6 D6 02 18         [ 1] 2175     ld      a, (zc_d, x)
      008DA9 B1 B6            [ 1] 2176     cp      a, *m_ww
      008DAB 26 0A            [ 1] 2177     jrne    00361$
      008DAD 35 FF 00 AF      [ 1] 2178     mov     *m_tj, #0xFF
      008DB1 CD 8C B8         [ 4] 2179     call    trial
      008DB4 4D               [ 1] 2180     tnz     a
      008DB5 26 05            [ 1] 2181     jrne    00363$
      008DB7                       2182 00361$:
      008DB7 3C AE            [ 1] 2183     inc     *m_ti
      008DB9 20 E3            [ 2] 2184     jra     00360$
      008DBB                       2185 00362$:
      008DBB 4F               [ 1] 2186     clr     a
      008DBC                       2187 00363$:
      008DBC 81               [ 4] 2188     ret
                                   2189 
      008DBD                       2190 cpair:
      008DBD 3F AE            [ 1] 2191     clr     *m_ti
      008DBF                       2192 00370$:
      008DBF B6 AE            [ 1] 2193     ld      a, *m_ti
      008DC1 4C               [ 1] 2194     inc     a
      008DC2 B7 AF            [ 1] 2195     ld      *m_tj, a
      008DC4                       2196 00371$:
      008DC4 B6 AF            [ 1] 2197     ld      a, *m_tj
      008DC6 B1 B5            [ 1] 2198     cp      a, *m_cn
      008DC8 24 2D            [ 1] 2199     jrnc    00374$
                                   2200     ; SS7.10 W2 bound: a weight-2 trial may only combine candidates from
                                   2201     ; the A_PAIR (3) weakest AND at margin <= MG_PAIR (4).  zc_m is
                                   2202     ; non-decreasing and tj > ti, so tj carries BOTH maxima -- one test.
                                   2203     ; Both conditions are monotone in tj, so failing either ends the
                                   2204     ; inner loop (jrnc 00374$), exactly like decode.c's `break`.
      008DCA A1 03            [ 1] 2205     cp      a, #3               ; tj < A_PAIR ?
      008DCC 24 29            [ 1] 2206     jrnc    00374$
      008DCE 5F               [ 1] 2207     clrw    x
      008DCF 97               [ 1] 2208     ld      xl, a
      008DD0 D6 02 13         [ 1] 2209     ld      a, (zc_m, x)
      008DD3 A1 05            [ 1] 2210     cp      a, #5               ; zc_m[tj] <= MG_PAIR ?
      008DD5 24 20            [ 1] 2211     jrnc    00374$
                                   2212     ; isd[i] + isd[j] == sum?
      008DD7 B6 AE            [ 1] 2213     ld      a, *m_ti
      008DD9 5F               [ 1] 2214     clrw    x
      008DDA 97               [ 1] 2215     ld      xl, a
      008DDB D6 02 18         [ 1] 2216     ld      a, (zc_d, x)
      008DDE B7 0D            [ 1] 2217     ld      *m_s, a
      008DE0 B6 AF            [ 1] 2218     ld      a, *m_tj
      008DE2 5F               [ 1] 2219     clrw    x
      008DE3 97               [ 1] 2220     ld      xl, a
      008DE4 D6 02 18         [ 1] 2221     ld      a, (zc_d, x)
      008DE7 BB 0D            [ 1] 2222     add     a, *m_s
      008DE9 B1 B6            [ 1] 2223     cp      a, *m_ww
      008DEB 26 06            [ 1] 2224     jrne    00372$
      008DED CD 8C B8         [ 4] 2225     call    trial
      008DF0 4D               [ 1] 2226     tnz     a
      008DF1 26 12            [ 1] 2227     jrne    00376$
      008DF3                       2228 00372$:
      008DF3 3C AF            [ 1] 2229     inc     *m_tj
      008DF5 20 CD            [ 2] 2230     jra     00371$
      008DF7                       2231 00374$:
      008DF7 B6 AE            [ 1] 2232     ld      a, *m_ti
      008DF9 4C               [ 1] 2233     inc     a
      008DFA B7 AE            [ 1] 2234     ld      *m_ti, a
      008DFC 4C               [ 1] 2235     inc     a                   ; need ti+1 < cn for a pair to exist
      008DFD B1 B5            [ 1] 2236     cp      a, *m_cn
      008DFF 25 BE            [ 1] 2237     jrc     00370$
      008E01 27 BC            [ 1] 2238     jreq    00370$
      008E03 4F               [ 1] 2239     clr     a
      008E04 81               [ 4] 2240     ret
      008E05                       2241 00376$:
      008E05 A6 01            [ 1] 2242     ld      a, #1
      008E07 81               [ 4] 2243     ret
                                   2244 
                                   2245 ; copy d_pp[0..ND-1] to *out
      008E08                       2246 ppout:
      008E08 5F               [ 1] 2247     clrw    x
      008E09                       2248 00380$:
      008E09 72 D6 00 A8      [ 4] 2249     ld      a, ([m_pp], x)
      008E0D 72 D7 00 AA      [ 4] 2250     ld      ([m_outp], x), a
      008E11 5C               [ 1] 2251     incw    x
      008E12 C3 80 A7         [ 2] 2252     cpw     x, _g_ND
      008E15 25 F2            [ 1] 2253     jrc     00380$
      008E17 81               [ 4] 2254     ret
                                   2255 
                                   2256 ; ---------------------------------------------------------------- chase
                                   2257 ; -> A = DEC_* path; dec_info.cause set on refusals.
      008E18                       2258 chasez:
      008E18 CE 80 95         [ 2] 2259     ldw     x, _g_NB            ; m_pp = _ov + NBB
      008E1B 54               [ 2] 2260     srlw    x
      008E1C 54               [ 2] 2261     srlw    x
      008E1D 54               [ 2] 2262     srlw    x
      008E1E 1C 01 18         [ 2] 2263     addw    x, #_ov
      008E21 BF A8            [ 2] 2264     ldw     *m_pp, x
                                   2265     ; C1: d_pp[p] = bitrev(d_bits[4+p]), p = 0..NPP-1 (PP_LO = bit 32)
      008E23 5F               [ 1] 2266     clrw    x
      008E24                       2267 00400$:
      008E24 D6 01 1C         [ 1] 2268     ld      a, (_ov+4, x)
      008E27 4B 08            [ 1] 2269     push    #8
      008E29                       2270 00401$:
      008E29 44               [ 1] 2271     srl     a
      008E2A 39 0D            [ 1] 2272     rlc     *m_s
      008E2C 0A 01            [ 1] 2273     dec     (1, sp)
      008E2E 26 F9            [ 1] 2274     jrne    00401$
      008E30 5B 01            [ 2] 2275     addw    sp, #1
      008E32 B6 0D            [ 1] 2276     ld      a, *m_s
      008E34 72 D7 00 A8      [ 4] 2277     ld      ([m_pp], x), a
      008E38 5C               [ 1] 2278     incw    x
      008E39 C3 80 AB         [ 2] 2279     cpw     x, _g_NPP
      008E3C 25 E6            [ 1] 2280     jrc     00400$
                                   2281     ; dec_info.n_weak / n_tied
      008E3E BE A4            [ 2] 2282     ldw     x, *w_nweak
      008E40 CF 01 05         [ 2] 2283     ldw     _dec_info+5, x
      008E43 BE A6            [ 2] 2284     ldw     x, *w_ntied
      008E45 CF 01 07         [ 2] 2285     ldw     _dec_info+7, x
                                   2286     ; legacy geometry (CHECK_EN=0)?
      008E48 72 5D 80 AD      [ 1] 2287     tnz     _g_CHK
      008E4C 26 13            [ 1] 2288     jrne    00403$
      008E4E BE A6            [ 2] 2289     ldw     x, *w_ntied         ; R5 emit gate
      008E50 A3 00 08         [ 2] 2290     cpw     x, #8
      008E53 23 06            [ 2] 2291     jrule   00402$
      008E55 35 05 01 01      [ 1] 2292     mov     _dec_info+1, #5
      008E59 4F               [ 1] 2293     clr     a
      008E5A 81               [ 4] 2294     ret
      008E5B                       2295 00402$:
      008E5B CD 8E 08         [ 4] 2296     call    ppout
      008E5E A6 03            [ 1] 2297     ld      a, #3               ; DEC_LEGACY
      008E60 81               [ 4] 2298     ret
      008E61                       2299 00403$:
      008E61 CD 8C 1D         [ 4] 2300     call    crc8pp
      008E64 B7 B4            [ 1] 2301     ld      *m_rb, a
      008E66 CD 8C 81         [ 4] 2302     call    ldcpz               ; majority of the decoded check block
      008E69 CD 8C 37         [ 4] 2303     call    majz
      008E6C B7 B3            [ 1] 2304     ld      *m_hR, a
      008E6E BE A6            [ 2] 2305     ldw     x, *w_ntied         ; R5 emit gate (both paths)
      008E70 A3 00 08         [ 2] 2306     cpw     x, #8
      008E73 23 06            [ 2] 2307     jrule   00404$
      008E75 35 05 01 01      [ 1] 2308     mov     _dec_info+1, #5
      008E79 4F               [ 1] 2309     clr     a
      008E7A 81               [ 4] 2310     ret
      008E7B                       2311 00404$:
      008E7B 3D B3            [ 1] 2312     tnz     *m_hR               ; C2 direct accept
      008E7D 27 0C            [ 1] 2313     jreq    00405$
      008E7F B6 B4            [ 1] 2314     ld      a, *m_rb
      008E81 B1 AC            [ 1] 2315     cp      a, *m_R
      008E83 26 06            [ 1] 2316     jrne    00405$
      008E85 CD 8E 08         [ 4] 2317     call    ppout
      008E88 A6 01            [ 1] 2318     ld      a, #1               ; DEC_DIRECT
      008E8A 81               [ 4] 2319     ret
      008E8B                       2320 00405$:
      008E8B BE A4            [ 2] 2321     ldw     x, *w_nweak         ; C3 admission gates
      008E8D 26 06            [ 1] 2322     jrne    00406$
      008E8F 35 06 01 01      [ 1] 2323     mov     _dec_info+1, #6     ; R6 no candidate
      008E93 4F               [ 1] 2324     clr     a
      008E94 81               [ 4] 2325     ret
      008E95                       2326 00406$:
      008E95 A3 00 05         [ 2] 2327     cpw     x, #5
      008E98 23 06            [ 2] 2328     jrule   00407$
      008E9A 35 07 01 01      [ 1] 2329     mov     _dec_info+1, #7     ; R7 admission
      008E9E 4F               [ 1] 2330     clr     a
      008E9F 81               [ 4] 2331     ret
      008EA0                       2332 00407$:
      008EA0 B6 A3            [ 1] 2333     ld      a, *zc_n            ; ch_n = ncand; isd[] = (k < ND8)
      008EA2 B7 B5            [ 1] 2334     ld      *m_cn, a
      008EA4 3F 9A            [ 1] 2335     clr     *m_i
      008EA6                       2336 00408$:
      008EA6 B6 9A            [ 1] 2337     ld      a, *m_i
      008EA8 B1 B5            [ 1] 2338     cp      a, *m_cn
      008EAA 24 15            [ 1] 2339     jrnc    00410$
      008EAC CD 8C B1         [ 4] 2340     call    candk               ; X = zc_t[i]
      008EAF C3 80 A9         [ 2] 2341     cpw     x, _g_ND8           ; C = 1 iff zc_t[i] < ND8, i.e. a DATA bit
      008EB2 4F               [ 1] 2342     clr     a                   ; CLR touches N/Z only -- C survives
      008EB3 49               [ 1] 2343     rlc     a                   ; A = C = isd[i]  (saves the jrc/jra pair)
      008EB4 88               [ 1] 2344     push    a
      008EB5 B6 9A            [ 1] 2345     ld      a, *m_i
      008EB7 5F               [ 1] 2346     clrw    x
      008EB8 97               [ 1] 2347     ld      xl, a
      008EB9 84               [ 1] 2348     pop     a
      008EBA D7 02 18         [ 1] 2349     ld      (zc_d, x), a
      008EBD 3C 9A            [ 1] 2350     inc     *m_i
      008EBF 20 E5            [ 2] 2351     jra     00408$
      008EC1                       2352 00410$:
      008EC1 35 FF 00 B2      [ 1] 2353     mov     *m_par, #0xFF       ; parity gate value (0xFF = no ref)
      008EC5 3D B3            [ 1] 2354     tnz     *m_hR
      008EC7 27 09            [ 1] 2355     jreq    00411$
      008EC9 B6 B4            [ 1] 2356     ld      a, *m_rb
      008ECB B8 AC            [ 1] 2357     xor     a, *m_R
      008ECD CD 8C 9E         [ 4] 2358     call    par8
      008ED0 B7 B2            [ 1] 2359     ld      *m_par, a
      008ED2                       2360 00411$:
      008ED2 35 01 01 04      [ 1] 2361     mov     _dec_info+4, #1     ; chased = 1
                                   2362     ; C4: five phases, data-minimal, cheapest-first; parity gate skips
                                   2363     ; the data phase that provably cannot pass
      008ED6 3F B6            [ 1] 2364     clr     *m_ww               ; phase 1: one check bit
      008ED8 CD 8D 9C         [ 4] 2365     call    csing
      008EDB 4D               [ 1] 2366     tnz     a
      008EDC 26 36            [ 1] 2367     jrne    00420$
      008EDE 3F B6            [ 1] 2368     clr     *m_ww               ; phase 2: two check bits
      008EE0 CD 8D BD         [ 4] 2369     call    cpair
      008EE3 4D               [ 1] 2370     tnz     a
      008EE4 26 2E            [ 1] 2371     jrne    00420$
      008EE6 3D B2            [ 1] 2372     tnz     *m_par              ; phase 3: one data bit unless par == 0
      008EE8 27 0A            [ 1] 2373     jreq    00413$
      008EEA 35 01 00 B6      [ 1] 2374     mov     *m_ww, #1
      008EEE CD 8D 9C         [ 4] 2375     call    csing
      008EF1 4D               [ 1] 2376     tnz     a
      008EF2 26 20            [ 1] 2377     jrne    00420$
      008EF4                       2378 00413$:
      008EF4 35 01 00 B6      [ 1] 2379     mov     *m_ww, #1           ; phase 4: data + check
      008EF8 CD 8D BD         [ 4] 2380     call    cpair
      008EFB 4D               [ 1] 2381     tnz     a
      008EFC 26 16            [ 1] 2382     jrne    00420$
      008EFE B6 B2            [ 1] 2383     ld      a, *m_par           ; phase 5: two data bits unless par == 1
      008F00 A1 01            [ 1] 2384     cp      a, #1
      008F02 27 0A            [ 1] 2385     jreq    00414$
      008F04 35 02 00 B6      [ 1] 2386     mov     *m_ww, #2
      008F08 CD 8D BD         [ 4] 2387     call    cpair
      008F0B 4D               [ 1] 2388     tnz     a
      008F0C 26 06            [ 1] 2389     jrne    00420$
      008F0E                       2390 00414$:
      008F0E 35 08 01 01      [ 1] 2391     mov     _dec_info+1, #8     ; R8 chase exhausted
      008F12 4F               [ 1] 2392     clr     a
      008F13 81               [ 4] 2393     ret
      008F14                       2394 00420$:
      008F14 CD 8E 08         [ 4] 2395     call    ppout
      008F17 A6 02            [ 1] 2396     ld      a, #2               ; DEC_CHASE
      008F19 81               [ 4] 2397     ret
                                   2398 
                                   2399 ; ------------------------------------------------------------ ws_decode_ex
                                   2400 ; C ABI: X = cap; stack args (callee-pops): (3,sp) ncap, (5,sp) out.
                                   2401 ; Returns A = DEC_* (== dec_info.path).
      008F1A                       2402 _ws_decode_ex:
      008F1A CF 00 B7         [ 2] 2403     ldw     _scan_cap, x
      008F1D 1E 03            [ 2] 2404     ldw     x, (3, sp)
      008F1F CF 00 B9         [ 2] 2405     ldw     _scan_len, x
      008F22 1E 05            [ 2] 2406     ldw     x, (5, sp)
      008F24 BF AA            [ 2] 2407     ldw     *m_outp, x
      008F26 AE 00 14         [ 2] 2408     ldw     x, #20              ; zero dec_info (20 B struct)
      008F29                       2409 00430$:
      008F29 72 4F 00 FF      [ 1] 2410     clr     (_dec_info-1, x)
      008F2D 5A               [ 2] 2411     decw    x
      008F2E 26 F9            [ 1] 2412     jrne    00430$
      008F30 CD 86 89         [ 4] 2413     call    _seed
      008F33 4D               [ 1] 2414     tnz     a
      008F34 26 08            [ 1] 2415     jrne    00431$
      008F36 35 01 01 01      [ 1] 2416     mov     _dec_info+1, #1     ; R1 lock
      008F3A 4F               [ 1] 2417     clr     a
      008F3B CC 8F CA         [ 2] 2418     jp      00439$
      008F3E                       2419 00431$:
      008F3E CD 84 43         [ 4] 2420     call    _refine
      008F41 CD 84 43         [ 4] 2421     call    _refine
      008F44 CD 93 D0         [ 4] 2422     call    _calibrate
      008F47 CD 89 E8         [ 4] 2423     call    _decide_pass
      008F4A CE 01 14         [ 2] 2424     ldw     x, _g_K
      008F4D CF 01 09         [ 2] 2425     ldw     _dec_info+9, x
      008F50 CE 01 16         [ 2] 2426     ldw     x, _g_tau
      008F53 CF 01 0B         [ 2] 2427     ldw     _dec_info+11, x
      008F56 BE 9D            [ 2] 2428     ldw     x, *w_inf
      008F58 CF 01 0E         [ 2] 2429     ldw     _dec_info+14, x
      008F5B BE 9F            [ 2] 2430     ldw     x, *w_lab
      008F5D CF 01 10         [ 2] 2431     ldw     _dec_info+16, x
      008F60 BE A1            [ 2] 2432     ldw     x, *w_nseg
      008F62 CF 01 12         [ 2] 2433     ldw     _dec_info+18, x
                                   2434     ; violations: decoded-against-template marker bits
      008F65 3F AD            [ 1] 2435     clr     *m_vi
      008F67 5F               [ 1] 2436     clrw    x
      008F68 BF 86            [ 2] 2437     ldw     *m_t, x
      008F6A                       2438 00432$:
      008F6A BE 86            [ 2] 2439     ldw     x, *m_t
      008F6C C3 80 95         [ 2] 2440     cpw     x, _g_NB
      008F6F 24 2B            [ 1] 2441     jrnc    00435$
      008F71 CD 87 57         [ 4] 2442     call    _known_bit
      008F74 A1 FF            [ 1] 2443     cp      a, #0xFF
      008F76 27 1D            [ 1] 2444     jreq    00434$
      008F78 B7 9C            [ 1] 2445     ld      *m_m, a             ; expected bit
      008F7A BE 86            [ 2] 2446     ldw     x, *m_t             ; BGET(d_bits, t)
      008F7C 9F               [ 1] 2447     ld      a, xl
      008F7D A4 07            [ 1] 2448     and     a, #7
      008F7F 4C               [ 1] 2449     inc     a
      008F80 B7 0D            [ 1] 2450     ld      *m_s, a
      008F82 54               [ 2] 2451     srlw    x
      008F83 54               [ 2] 2452     srlw    x
      008F84 54               [ 2] 2453     srlw    x
      008F85 D6 01 18         [ 1] 2454     ld      a, (_ov, x)
      008F88                       2455 00433$:
      008F88 44               [ 1] 2456     srl     a
      008F89 3A 0D            [ 1] 2457     dec     *m_s
      008F8B 26 FB            [ 1] 2458     jrne    00433$
      008F8D 4F               [ 1] 2459     clr     a
      008F8E 49               [ 1] 2460     rlc     a
      008F8F B1 9C            [ 1] 2461     cp      a, *m_m
      008F91 27 02            [ 1] 2462     jreq    00434$
      008F93 3C AD            [ 1] 2463     inc     *m_vi
      008F95                       2464 00434$:
      008F95 BE 86            [ 2] 2465     ldw     x, *m_t
      008F97 5C               [ 1] 2466     incw    x
      008F98 BF 86            [ 2] 2467     ldw     *m_t, x
      008F9A 20 CE            [ 2] 2468     jra     00432$
      008F9C                       2469 00435$:
      008F9C B6 AD            [ 1] 2470     ld      a, *m_vi
      008F9E C7 01 0D         [ 1] 2471     ld      _dec_info+13, a
      008FA1 4D               [ 1] 2472     tnz     a
      008FA2 27 07            [ 1] 2473     jreq    00436$
      008FA4 35 02 01 01      [ 1] 2474     mov     _dec_info+1, #2     ; R2 marker
      008FA8 4F               [ 1] 2475     clr     a
      008FA9 20 1F            [ 2] 2476     jra     00439$
      008FAB                       2477 00436$:
      008FAB BE 9D            [ 2] 2478     ldw     x, *w_inf
      008FAD A3 00 04         [ 2] 2479     cpw     x, #4
      008FB0 23 07            [ 2] 2480     jrule   00437$
      008FB2 35 03 01 01      [ 1] 2481     mov     _dec_info+1, #3     ; R3 infeasible
      008FB6 4F               [ 1] 2482     clr     a
      008FB7 20 11            [ 2] 2483     jra     00439$
      008FB9                       2484 00437$:
      008FB9 BE 9F            [ 2] 2485     ldw     x, *w_lab
      008FBB A3 00 06         [ 2] 2486     cpw     x, #6
      008FBE 23 07            [ 2] 2487     jrule   00438$
      008FC0 35 04 01 01      [ 1] 2488     mov     _dec_info+1, #4     ; R4 label error
      008FC4 4F               [ 1] 2489     clr     a
      008FC5 20 03            [ 2] 2490     jra     00439$
      008FC7                       2491 00438$:
      008FC7 CD 8E 18         [ 4] 2492     call    chasez              ; R5..R8 / emit inside
      008FCA                       2493 00439$:
      008FCA C7 01 00         [ 1] 2494     ld      _dec_info+0, a      ; path
      008FCD 1E 01            [ 2] 2495     ldw     x, (1, sp)          ; callee-pops epilogue (4 arg bytes)
      008FCF 5B 06            [ 2] 2496     addw    sp, #6
      008FD1 FC               [ 2] 2497     jp      (x)
                                   2498 
                                   2499 ; ======================================================================
                                   2500 ; P3 calibration cluster: label_interval / cal_cloud / cal_add /
                                   2501 ; width_fit / theta56 / calibrate -- the last C in the target decoder.
                                   2502 ; Bit-exact ports; state in the zero page; c_hist = ov.hist (indexed).
                                   2503 ; ======================================================================
                                   2504 
                                   2505     .area CODE
                                   2506 
                                   2507 ; la_int: X = a (s16); g_sg.u/.v, m_L = k1-k0 -> A = cls (0/1/0xFF),
                                   2508 ; *w_llo = u-off, *w_lhi = v-off.  Exactly label_interval().
      008FD2                       2509 la_int:
      008FD2 BF 34            [ 2] 2510     ldw     *m_la, x
      008FD4 5D               [ 2] 2511     tnzw    x
      008FD5 26 05            [ 1] 2512     jrne    00500$
      008FD7 5F               [ 1] 2513     clrw    x                   ; a == 0: off = 0, cls = 0
      008FD8 4F               [ 1] 2514     clr     a
      008FD9 CC 90 37         [ 2] 2515     jp      00507$
      008FDC                       2516 00500$:
      008FDC B3 7C            [ 2] 2517     cpw     x, *m_L
      008FDE 27 46            [ 1] 2518     jreq    00509$              ; a == L: off = (L-1)*512, cls = 1 --
                                   2519                                 ; shares the d1<=d0 tail (m_la == L here)
      008FE0                       2520 00501$:
                                   2521     ; mid = (u+v)>>1 (arithmetic)
      008FE0 CE 00 61         [ 2] 2522     ldw     x, _g_sg+4
      008FE3 72 BB 00 63      [ 2] 2523     addw    x, _g_sg+6
      008FE7 57               [ 2] 2524     sraw    x
      008FE8 BF 7A            [ 2] 2525     ldw     *m_h, x             ; mid
                                   2526     ; d1 = |mid - ((a-1)*512 + 308)|
      008FEA BE 34            [ 2] 2527     ldw     x, *m_la
      008FEC 5A               [ 2] 2528     decw    x
      008FED 9F               [ 1] 2529     ld      a, xl
      008FEE 5F               [ 1] 2530     clrw    x
      008FEF 95               [ 1] 2531     ld      xh, a
      008FF0 58               [ 2] 2532     sllw    x
      008FF1 1C 01 34         [ 2] 2533     addw    x, #308
      008FF4 50               [ 2] 2534     negw    x
      008FF5 72 BB 00 7A      [ 2] 2535     addw    x, *m_h             ; mid - h1pos
      008FF9 2A 01            [ 1] 2536     jrpl    00502$
      008FFB 50               [ 2] 2537     negw    x
      008FFC                       2538 00502$:
      008FFC BF 7E            [ 2] 2539     ldw     *m_c, x             ; d1
                                   2540     ; d0 = |mid - (a*512 + 154)|
      008FFE B6 35            [ 1] 2541     ld      a, *m_la+1
      009000 5F               [ 1] 2542     clrw    x
      009001 95               [ 1] 2543     ld      xh, a
      009002 58               [ 2] 2544     sllw    x
      009003 1C 00 9A         [ 2] 2545     addw    x, #154
      009006 50               [ 2] 2546     negw    x
      009007 72 BB 00 7A      [ 2] 2547     addw    x, *m_h
      00900B 2A 01            [ 1] 2548     jrpl    00503$
      00900D 50               [ 2] 2549     negw    x
      00900E                       2550 00503$:
      00900E BF 82            [ 2] 2551     ldw     *m_c1, x            ; d0
                                   2552     ; if (min(d0,d1) > 246) return -1
      009010 B3 7E            [ 2] 2553     cpw     x, *m_c
      009012 2C 02            [ 1] 2554     jrsgt   00504$
                                   2555     ; d0 <= d1: min = d0 (in X)
      009014 20 02            [ 2] 2556     jra     00505$
      009016                       2557 00504$:
      009016 BE 7E            [ 2] 2558     ldw     x, *m_c             ; min = d1
      009018                       2559 00505$:
      009018 A3 00 F6         [ 2] 2560     cpw     x, #246
      00901B 2D 03            [ 1] 2561     jrsle   00506$
      00901D A6 FF            [ 1] 2562     ld      a, #0xFF
      00901F 81               [ 4] 2563     ret
      009020                       2564 00506$:
                                   2565     ; if (d1 <= d0) off=(a-1)*512, cls=1 else off=a*512, cls=0
      009020 BE 7E            [ 2] 2566     ldw     x, *m_c             ; d1
      009022 B3 82            [ 2] 2567     cpw     x, *m_c1            ; vs d0
      009024 2C 0B            [ 1] 2568     jrsgt   00508$
      009026                       2569 00509$:
      009026 BE 34            [ 2] 2570     ldw     x, *m_la            ; d1 <= d0 (and the a == L entry)
      009028 5A               [ 2] 2571     decw    x
      009029 9F               [ 1] 2572     ld      a, xl
      00902A 5F               [ 1] 2573     clrw    x
      00902B 95               [ 1] 2574     ld      xh, a
      00902C 58               [ 2] 2575     sllw    x
      00902D A6 01            [ 1] 2576     ld      a, #1
      00902F 20 06            [ 2] 2577     jra     00507$
      009031                       2578 00508$:
      009031 B6 35            [ 1] 2579     ld      a, *m_la+1
      009033 5F               [ 1] 2580     clrw    x
      009034 95               [ 1] 2581     ld      xh, a
      009035 58               [ 2] 2582     sllw    x
      009036 4F               [ 1] 2583     clr     a
      009037                       2584 00507$:                         ; X = off, A = cls
      009037 88               [ 1] 2585     push    a
      009038 BF 7A            [ 2] 2586     ldw     *m_h, x
      00903A CE 00 61         [ 2] 2587     ldw     x, _g_sg+4
      00903D 72 B0 00 7A      [ 2] 2588     subw    x, *m_h
      009041 BF 30            [ 2] 2589     ldw     *w_llo, x
      009043 CE 00 63         [ 2] 2590     ldw     x, _g_sg+6
      009046 72 B0 00 7A      [ 2] 2591     subw    x, *m_h
      00904A BF 32            [ 2] 2592     ldw     *w_lhi, x
      00904C 84               [ 1] 2593     pop     a
      00904D 81               [ 4] 2594     ret
                                   2595 
                                   2596 ; (hix moved into the VGAP block above -- vector-gap bytes are free)
                                   2597 
                                   2598 ; cal_cloud: g_sg.u/.fam; hist fold histogram
      00904E                       2599 ccloud:
      00904E C6 00 65         [ 1] 2600     ld      a, _g_sg+8
      009051 A1 05            [ 1] 2601     cp      a, #5
      009053 27 05            [ 1] 2602     jreq    00520$
      009055 A1 06            [ 1] 2603     cp      a, #6
      009057 27 01            [ 1] 2604     jreq    00520$
      009059 81               [ 4] 2605     ret
      00905A                       2606 00520$:
      00905A CE 00 61         [ 2] 2607     ldw     x, _g_sg+4          ; u < 0 -> out
      00905D 2B 3A            [ 1] 2608     jrmi    00529$
      00905F A0 05            [ 1] 2609     sub     a, #5
      009061 B7 36            [ 1] 2610     ld      *m_f, a
                                   2611     ; d = (u & 511) - c_c0[f]
      009063 CE 00 61         [ 2] 2612     ldw     x, _g_sg+4
      009066 9E               [ 1] 2613     ld      a, xh
      009067 A4 01            [ 1] 2614     and     a, #1
      009069 95               [ 1] 2615     ld      xh, a               ; x = u & 511
      00906A 89               [ 2] 2616     pushw   x
      00906B B6 36            [ 1] 2617     ld      a, *m_f
      00906D 48               [ 1] 2618     sll     a
      00906E 5F               [ 1] 2619     clrw    x
      00906F 97               [ 1] 2620     ld      xl, a
      009070 DE 00 F5         [ 2] 2621     ldw     x, (c_c0, x)
      009073 BF 7A            [ 2] 2622     ldw     *m_h, x
      009075 85               [ 2] 2623     popw    x
      009076 72 B0 00 7A      [ 2] 2624     subw    x, *m_h             ; d
                                   2625     ; if (-64 <= d < 64): b = (d+64)>>1; hist[f][b]++ (sat 255)
      00907A 1C 00 40         [ 2] 2626     addw    x, #64              ; d+64 in [0,128)
      00907D 2B 1A            [ 1] 2627     jrmi    00529$
      00907F A3 00 80         [ 2] 2628     cpw     x, #128
      009082 24 15            [ 1] 2629     jrnc    00529$
      009084 54               [ 2] 2630     srlw    x                   ; b
      009085 89               [ 2] 2631     pushw   x
      009086 B6 36            [ 1] 2632     ld      a, *m_f
      009088 CD 80 58         [ 4] 2633     call    hix
      00908B 72 FB 01         [ 2] 2634     addw    x, (1, sp)
      00908E 5B 02            [ 2] 2635     addw    sp, #2
      009090 D6 01 18         [ 1] 2636     ld      a, (_ov, x)
      009093 4C               [ 1] 2637     inc     a
      009094 27 03            [ 1] 2638     jreq    00529$              ; was 255: saturate
      009096 D7 01 18         [ 1] 2639     ld      (_ov, x), a
      009099                       2640 00529$:
      009099 81               [ 4] 2641     ret
                                   2642 
                                   2643 ; cal_add: X = a; g_sg -> interval intersection + labx extremes
      00909A                       2644 cadd:
      00909A CD 8F D2         [ 4] 2645     call    la_int
      00909D A1 FF            [ 1] 2646     cp      a, #0xFF
      00909F 26 01            [ 1] 2647     jrne    00530$
      0090A1 81               [ 4] 2648     ret
      0090A2                       2649 00530$:
      0090A2 B7 9A            [ 1] 2650     ld      *m_i, a             ; ci
      0090A4 48               [ 1] 2651     sll     a
      0090A5 5F               [ 1] 2652     clrw    x
      0090A6 97               [ 1] 2653     ld      xl, a
      0090A7 89               [ 2] 2654     pushw   x                   ; 2*ci
                                   2655     ; if (lo > c_lo[ci]) c_lo = lo
      0090A8 DE 00 D5         [ 2] 2656     ldw     x, (c_lo, x)
      0090AB B3 30            [ 2] 2657     cpw     x, *w_llo
      0090AD 2E 08            [ 1] 2658     jrsge   00531$
      0090AF 1E 01            [ 2] 2659     ldw     x, (1, sp)
      0090B1 90 BE 30         [ 2] 2660     ldw     y, *w_llo
      0090B4 DF 00 D5         [ 2] 2661     ldw     (c_lo, x), y
      0090B7                       2662 00531$:
      0090B7 1E 01            [ 2] 2663     ldw     x, (1, sp)
      0090B9 DE 00 D9         [ 2] 2664     ldw     x, (c_hi, x)
      0090BC B3 32            [ 2] 2665     cpw     x, *w_lhi
      0090BE 2D 08            [ 1] 2666     jrsle   00532$
      0090C0 1E 01            [ 2] 2667     ldw     x, (1, sp)
      0090C2 90 BE 32         [ 2] 2668     ldw     y, *w_lhi
      0090C5 DF 00 D9         [ 2] 2669     ldw     (c_hi, x), y
      0090C8                       2670 00532$:
                                   2671     ; if (c_n[ci] < 255) c_n[ci]++
      0090C8 B6 9A            [ 1] 2672     ld      a, *m_i
      0090CA 5F               [ 1] 2673     clrw    x
      0090CB 97               [ 1] 2674     ld      xl, a
      0090CC D6 00 DD         [ 1] 2675     ld      a, (c_n, x)
      0090CF 4C               [ 1] 2676     inc     a
      0090D0 27 03            [ 1] 2677     jreq    00533$
      0090D2 D7 00 DD         [ 1] 2678     ld      (c_n, x), a
      0090D5                       2679 00533$:
      0090D5 5B 02            [ 2] 2680     addw    sp, #2
                                   2681     ; fams 5/6 with lo >= 0: labx extremes of the fold coordinate
      0090D7 C6 00 65         [ 1] 2682     ld      a, _g_sg+8
      0090DA A1 05            [ 1] 2683     cp      a, #5
      0090DC 27 05            [ 1] 2684     jreq    00534$
      0090DE A1 06            [ 1] 2685     cp      a, #6
      0090E0 27 01            [ 1] 2686     jreq    00534$
      0090E2 81               [ 4] 2687     ret
      0090E3                       2688 00534$:
      0090E3 BE 30            [ 2] 2689     ldw     x, *w_llo
      0090E5 2A 03            [ 1] 2690     jrpl    00535$
      0090E7 CC 91 6A         [ 2] 2691     jp      00549$              ; lo < 0: no fold sample
      0090EA                       2692 00535$:
      0090EA A0 05            [ 1] 2693     sub     a, #5
      0090EC B7 36            [ 1] 2694     ld      *m_f, a
      0090EE 9E               [ 1] 2695     ld      a, xh               ; d = (lo & 511) - c_c0[f]
      0090EF A4 01            [ 1] 2696     and     a, #1
      0090F1 95               [ 1] 2697     ld      xh, a
      0090F2 89               [ 2] 2698     pushw   x
      0090F3 B6 36            [ 1] 2699     ld      a, *m_f
      0090F5 48               [ 1] 2700     sll     a
      0090F6 5F               [ 1] 2701     clrw    x
      0090F7 97               [ 1] 2702     ld      xl, a
      0090F8 DE 00 F5         [ 2] 2703     ldw     x, (c_c0, x)
      0090FB BF 7A            [ 2] 2704     ldw     *m_h, x
      0090FD 85               [ 2] 2705     popw    x
      0090FE 72 B0 00 7A      [ 2] 2706     subw    x, *m_h
      009102 BF 7E            [ 2] 2707     ldw     *m_c, x             ; d
      009104 A3 FF C0         [ 2] 2708     cpw     x, #-64
      009107 2F 61            [ 1] 2709     jrslt   00549$
      009109 A3 00 40         [ 2] 2710     cpw     x, #64
      00910C 2E 5C            [ 1] 2711     jrsge   00549$
      00910E B6 36            [ 1] 2712     ld      a, *m_f
      009110 48               [ 1] 2713     sll     a
      009111 5F               [ 1] 2714     clrw    x
      009112 97               [ 1] 2715     ld      xl, a
      009113 BF 55            [ 2] 2716     ldw     *m_hx, x            ; 2*f (index into labx arrays)
      009115 3D 9A            [ 1] 2717     tnz     *m_i                ; cls?
      009117 26 29            [ 1] 2718     jrne    00540$
                                   2719     ; cls 0: if (d > labx0) { labx0b = labx0; labx0 = d; }
                                   2720     ;        else if (d > labx0b) labx0b = d
      009119 BE 55            [ 2] 2721     ldw     x, *m_hx
      00911B DE 00 E5         [ 2] 2722     ldw     x, (labx0, x)
      00911E B3 7E            [ 2] 2723     cpw     x, *m_c
      009120 2E 0E            [ 1] 2724     jrsge   00536$
      009122 90 93            [ 1] 2725     ldw     y, x                ; old labx0
      009124 BE 55            [ 2] 2726     ldw     x, *m_hx
      009126 DF 00 ED         [ 2] 2727     ldw     (labx0b, x), y
      009129 90 BE 7E         [ 2] 2728     ldw     y, *m_c
      00912C DF 00 E5         [ 2] 2729     ldw     (labx0, x), y
      00912F 81               [ 4] 2730     ret
      009130                       2731 00536$:
      009130 BE 55            [ 2] 2732     ldw     x, *m_hx
      009132 DE 00 ED         [ 2] 2733     ldw     x, (labx0b, x)
      009135 B3 7E            [ 2] 2734     cpw     x, *m_c
      009137 2E 31            [ 1] 2735     jrsge   00549$
      009139 BE 55            [ 2] 2736     ldw     x, *m_hx
      00913B 90 BE 7E         [ 2] 2737     ldw     y, *m_c
      00913E DF 00 ED         [ 2] 2738     ldw     (labx0b, x), y
      009141 81               [ 4] 2739     ret
      009142                       2740 00540$:
                                   2741     ; cls 1: if (d < labx1) { labx1b = labx1; labx1 = d; }
                                   2742     ;        else if (d < labx1b) labx1b = d
      009142 BE 55            [ 2] 2743     ldw     x, *m_hx
      009144 DE 00 E9         [ 2] 2744     ldw     x, (labx1, x)
      009147 B3 7E            [ 2] 2745     cpw     x, *m_c
      009149 2D 0E            [ 1] 2746     jrsle   00542$
      00914B 90 93            [ 1] 2747     ldw     y, x
      00914D BE 55            [ 2] 2748     ldw     x, *m_hx
      00914F DF 00 F1         [ 2] 2749     ldw     (labx1b, x), y
      009152 90 BE 7E         [ 2] 2750     ldw     y, *m_c
      009155 DF 00 E9         [ 2] 2751     ldw     (labx1, x), y
      009158 81               [ 4] 2752     ret
      009159                       2753 00542$:
      009159 BE 55            [ 2] 2754     ldw     x, *m_hx
      00915B DE 00 F1         [ 2] 2755     ldw     x, (labx1b, x)
      00915E B3 7E            [ 2] 2756     cpw     x, *m_c
      009160 2D 08            [ 1] 2757     jrsle   00549$
      009162 BE 55            [ 2] 2758     ldw     x, *m_hx
      009164 90 BE 7E         [ 2] 2759     ldw     y, *m_c
      009167 DF 00 F1         [ 2] 2760     ldw     (labx1b, x), y
      00916A                       2761 00549$:
      00916A 81               [ 4] 2762     ret
                                   2763 
                                   2764 ; wfit: A = ci; X = prior; *m_c = blo, *m_c1 = bhi -> X = width fit
      00916B                       2765 wfit:
      00916B BF 7A            [ 2] 2766     ldw     *m_h, x             ; prior
      00916D 5F               [ 1] 2767     clrw    x
      00916E 97               [ 1] 2768     ld      xl, a
      00916F D6 00 DD         [ 1] 2769     ld      a, (c_n, x)
      009172 A1 03            [ 1] 2770     cp      a, #3
      009174 25 37            [ 1] 2771     jrc     00559$              ; c_n < LAB_MIN -> prior
      009176 9F               [ 1] 2772     ld      a, xl
      009177 48               [ 1] 2773     sll     a
      009178 5F               [ 1] 2774     clrw    x
      009179 97               [ 1] 2775     ld      xl, a
      00917A 90 93            [ 1] 2776     ldw     y, x
      00917C DE 00 D5         [ 2] 2777     ldw     x, (c_lo, x)        ; lo
      00917F BF 84            [ 2] 2778     ldw     *m_e, x
      009181 93               [ 1] 2779     ldw     x, y
      009182 DE 00 D9         [ 2] 2780     ldw     x, (c_hi, x)        ; hi
      009185 BF 86            [ 2] 2781     ldw     *m_t, x
      009187 BE 84            [ 2] 2782     ldw     x, *m_e
      009189 B3 86            [ 2] 2783     cpw     x, *m_t
      00918B 2D 07            [ 1] 2784     jrsle   00551$
      00918D 72 BB 00 86      [ 2] 2785     addw    x, *m_t             ; lo > hi: h = (lo+hi)>>1
      009191 57               [ 2] 2786     sraw    x
      009192 20 10            [ 2] 2787     jra     00553$
      009194                       2788 00551$:
      009194 BE 7A            [ 2] 2789     ldw     x, *m_h             ; h = clamp(prior, lo, hi)
      009196 B3 84            [ 2] 2790     cpw     x, *m_e
      009198 2E 04            [ 1] 2791     jrsge   00552$
      00919A BE 84            [ 2] 2792     ldw     x, *m_e
      00919C 20 06            [ 2] 2793     jra     00553$
      00919E                       2794 00552$:
      00919E B3 86            [ 2] 2795     cpw     x, *m_t
      0091A0 2D 02            [ 1] 2796     jrsle   00553$
      0091A2 BE 86            [ 2] 2797     ldw     x, *m_t
      0091A4                       2798 00553$:
      0091A4 B3 7E            [ 2] 2799     cpw     x, *m_c             ; in [blo, bhi] else prior
      0091A6 2F 05            [ 1] 2800     jrslt   00559$
      0091A8 B3 82            [ 2] 2801     cpw     x, *m_c1
      0091AA 2C 01            [ 1] 2802     jrsgt   00559$
      0091AC 81               [ 4] 2803     ret
      0091AD                       2804 00559$:
      0091AD BE 7A            [ 2] 2805     ldw     x, *m_h
      0091AF 81               [ 4] 2806     ret
                                   2807 
                                   2808 ; theta56: A = f -> A = have_theta, *m_th = theta
      0091B0                       2809 th56:
      0091B0 B7 36            [ 1] 2810     ld      *m_f, a
      0091B2 48               [ 1] 2811     sll     a
      0091B3 5F               [ 1] 2812     clrw    x
      0091B4 97               [ 1] 2813     ld      xl, a
      0091B5 BF 55            [ 2] 2814     ldw     *m_hx, x            ; 2*f
      0091B7 DE 00 E5         [ 2] 2815     ldw     x, (labx0, x)
      0091BA BF 37            [ 2] 2816     ldw     *m_x0, x
      0091BC BE 55            [ 2] 2817     ldw     x, *m_hx
      0091BE DE 00 E9         [ 2] 2818     ldw     x, (labx1, x)
      0091C1 BF 3A            [ 2] 2819     ldw     *m_x1, x
                                   2820     ; zlo = max(-32, x0+1); zhi = min(32, x1)
      0091C3 BE 37            [ 2] 2821     ldw     x, *m_x0
      0091C5 5C               [ 1] 2822     incw    x
      0091C6 A3 FF E0         [ 2] 2823     cpw     x, #-32
      0091C9 2E 03            [ 1] 2824     jrsge   00560$
      0091CB AE FF E0         [ 2] 2825     ldw     x, #-32
      0091CE                       2826 00560$:
      0091CE BF 3C            [ 2] 2827     ldw     *m_zlo, x
      0091D0 BE 3A            [ 2] 2828     ldw     x, *m_x1
      0091D2 A3 00 20         [ 2] 2829     cpw     x, #32
      0091D5 2D 03            [ 1] 2830     jrsle   00561$
      0091D7 AE 00 20         [ 2] 2831     ldw     x, #32
      0091DA                       2832 00561$:
      0091DA BF 3E            [ 2] 2833     ldw     *m_zhi, x
      0091DC 5F               [ 1] 2834     clrw    x
      0091DD BF 40            [ 2] 2835     ldw     *m_th, x
      0091DF 3F 42            [ 1] 2836     clr     *m_hv
                                   2837     ; m_e := f*64 (hist row base) for the WHOLE function -- the density
                                   2838     ; search AND the top/clear1 scan (hoisted: a stale row here cost one
                                   2839     ; capture in validation)
      0091E1 B6 36            [ 1] 2840     ld      a, *m_f
      0091E3 CD 80 58         [ 4] 2841     call    hix
      0091E6 BF 84            [ 2] 2842     ldw     *m_e, x
                                   2843     ; density-gap search inside (zlo, zhi)
      0091E8 BE 3C            [ 2] 2844     ldw     x, *m_zlo
      0091EA B3 3E            [ 2] 2845     cpw     x, *m_zhi
      0091EC 2F 03            [ 1] 2846     jrslt   00562$
      0091EE CC 92 B7         [ 2] 2847     jp      00570$              ; window empty
      0091F1                       2848 00562$:
      0091F1 BE 3C            [ 2] 2849     ldw     x, *m_zlo           ; blo = (zlo+64)>>1
      0091F3 1C 00 40         [ 2] 2850     addw    x, #64
      0091F6 54               [ 2] 2851     srlw    x
      0091F7 9F               [ 1] 2852     ld      a, xl
      0091F8 B7 54            [ 1] 2853     ld      *m_bb, a
      0091FA BE 3E            [ 2] 2854     ldw     x, *m_zhi           ; bhi = (zhi-1+64)>>1
      0091FC 5A               [ 2] 2855     decw    x
      0091FD 1C 00 40         [ 2] 2856     addw    x, #64
      009200 54               [ 2] 2857     srlw    x
      009201 9F               [ 1] 2858     ld      a, xl
      009202 B7 9B            [ 1] 2859     ld      *m_j, a             ; bhi
      009204 BE 3C            [ 2] 2860     ldw     x, *m_zlo
      009206 BF 4B            [ 2] 2861     ldw     *m_prev, x
      009208 5F               [ 1] 2862     clrw    x
      009209 BF 44            [ 2] 2863     ldw     *m_blo2, x
      00920B BF 46            [ 2] 2864     ldw     *m_bhi2, x
      00920D AE FF FF         [ 2] 2865     ldw     x, #-1
      009210 BF 48            [ 2] 2866     ldw     *m_bg, x
      009212 3F 4A            [ 1] 2867     clr     *m_no
      009214                       2868 00563$:
      009214 B6 54            [ 1] 2869     ld      a, *m_bb
      009216 B1 9B            [ 1] 2870     cp      a, *m_j
      009218 22 32            [ 1] 2871     jrugt   00566$
      00921A 5F               [ 1] 2872     clrw    x                   ; hist[f][b]?
      00921B 97               [ 1] 2873     ld      xl, a
      00921C 72 BB 00 84      [ 2] 2874     addw    x, *m_e
      009220 D6 01 18         [ 1] 2875     ld      a, (_ov, x)
      009223 4D               [ 1] 2876     tnz     a
      009224 27 22            [ 1] 2877     jreq    00565$
                                   2878     ; x = (b<<1) - 64 + 1 ; gp = x - prev
      009226 B6 54            [ 1] 2879     ld      a, *m_bb
      009228 48               [ 1] 2880     sll     a                   ; b <= 48 -> fits
      009229 5F               [ 1] 2881     clrw    x
      00922A 97               [ 1] 2882     ld      xl, a
      00922B 1D 00 3F         [ 2] 2883     subw    x, #63
      00922E BF 7E            [ 2] 2884     ldw     *m_c, x             ; x coord
      009230 72 B0 00 4B      [ 2] 2885     subw    x, *m_prev
      009234 B3 48            [ 2] 2886     cpw     x, *m_bg
      009236 2D 0A            [ 1] 2887     jrsle   00564$
      009238 BF 48            [ 2] 2888     ldw     *m_bg, x
      00923A BE 4B            [ 2] 2889     ldw     x, *m_prev
      00923C BF 44            [ 2] 2890     ldw     *m_blo2, x
      00923E BE 7E            [ 2] 2891     ldw     x, *m_c
      009240 BF 46            [ 2] 2892     ldw     *m_bhi2, x
      009242                       2893 00564$:
      009242 BE 7E            [ 2] 2894     ldw     x, *m_c
      009244 BF 4B            [ 2] 2895     ldw     *m_prev, x
      009246 3C 4A            [ 1] 2896     inc     *m_no
      009248                       2897 00565$:
      009248 3C 54            [ 1] 2898     inc     *m_bb
      00924A 20 C8            [ 2] 2899     jra     00563$
      00924C                       2900 00566$:
      00924C BE 3E            [ 2] 2901     ldw     x, *m_zhi           ; trailing gap to zhi
      00924E 72 B0 00 4B      [ 2] 2902     subw    x, *m_prev
      009252 B3 48            [ 2] 2903     cpw     x, *m_bg
      009254 2D 0A            [ 1] 2904     jrsle   00567$
      009256 BF 48            [ 2] 2905     ldw     *m_bg, x
      009258 BE 4B            [ 2] 2906     ldw     x, *m_prev
      00925A BF 44            [ 2] 2907     ldw     *m_blo2, x
      00925C BE 3E            [ 2] 2908     ldw     x, *m_zhi
      00925E BF 46            [ 2] 2909     ldw     *m_bhi2, x
      009260                       2910 00567$:
      009260 3D 4A            [ 1] 2911     tnz     *m_no
      009262 26 16            [ 1] 2912     jrne    00568$
                                   2913     ; nocc == 0: theta = (zlo+zhi)>>1 iff has0 && has1
      009264 CD 93 BC         [ 4] 2914     call    has01
      009267 A1 03            [ 1] 2915     cp      a, #3
      009269 26 4C            [ 1] 2916     jrne    00570$
      00926B BE 3C            [ 2] 2917     ldw     x, *m_zlo
      00926D 72 BB 00 3E      [ 2] 2918     addw    x, *m_zhi
      009271 57               [ 2] 2919     sraw    x
      009272 BF 40            [ 2] 2920     ldw     *m_th, x
      009274 35 01 00 42      [ 1] 2921     mov     *m_hv, #1
      009278 20 3D            [ 2] 2922     jra     00570$
      00927A                       2923 00568$:
                                   2924     ; ok = bg >= 5; if (ok && nocc+1 >= 4) density test
      00927A BE 48            [ 2] 2925     ldw     x, *m_bg
      00927C A3 00 05         [ 2] 2926     cpw     x, #5
      00927F 2F 36            [ 1] 2927     jrslt   00570$
      009281 B6 4A            [ 1] 2928     ld      a, *m_no
      009283 4C               [ 1] 2929     inc     a
      009284 A1 04            [ 1] 2930     cp      a, #4
      009286 25 22            [ 1] 2931     jrc     00569$
                                   2932     ; 2*bg*(nocc+1) < 5*(zhi-zlo) -> not ok   (s16-safe, proven)
      009288 B6 49            [ 1] 2933     ld      a, *m_bg+1          ; bg <= 64
      00928A 48               [ 1] 2934     sll     a                   ; 2*bg <= 128
      00928B 5F               [ 1] 2935     clrw    x
      00928C 97               [ 1] 2936     ld      xl, a
      00928D B6 4A            [ 1] 2937     ld      a, *m_no
      00928F 4C               [ 1] 2938     inc     a                   ; nocc+1 <= 34
      009290 42               [ 4] 2939     mul     x, a                ; 2*bg*(nocc+1) <= 4352
      009291 BF 7E            [ 2] 2940     ldw     *m_c, x
      009293 BE 3E            [ 2] 2941     ldw     x, *m_zhi
      009295 72 B0 00 3C      [ 2] 2942     subw    x, *m_zlo           ; (zhi-zlo) in (0,64]
      009299 90 93            [ 1] 2943     ldw     y, x
      00929B 58               [ 2] 2944     sllw    x
      00929C 58               [ 2] 2945     sllw    x                   ; *4
      00929D 90 89            [ 2] 2946     pushw   y
      00929F 72 FB 01         [ 2] 2947     addw    x, (1, sp)          ; *5
      0092A2 5B 02            [ 2] 2948     addw    sp, #2
      0092A4 B3 7E            [ 2] 2949     cpw     x, *m_c
      0092A6 2D 02            [ 1] 2950     jrsle   00569$              ; 5*(zhi-zlo) <= lhs -> ok stays
      0092A8 20 0D            [ 2] 2951     jra     00570$              ; lhs < rhs -> not ok
      0092AA                       2952 00569$:
      0092AA BE 44            [ 2] 2953     ldw     x, *m_blo2          ; theta = (best_lo + best_hi) >> 1
      0092AC 72 BB 00 46      [ 2] 2954     addw    x, *m_bhi2
      0092B0 57               [ 2] 2955     sraw    x
      0092B1 BF 40            [ 2] 2956     ldw     *m_th, x
      0092B3 35 01 00 42      [ 1] 2957     mov     *m_hv, #1
      0092B7                       2958 00570$:
                                   2959     ; label-extreme window [wlo, whi]
      0092B7 CD 93 BC         [ 4] 2960     call    has01
      0092BA 4D               [ 1] 2961     tnz     a
      0092BB 26 03            [ 1] 2962     jrne    00571$
      0092BD CC 93 38         [ 2] 2963     jp      00580$              ; neither label seen
      0092C0                       2964 00571$:
      0092C0 88               [ 1] 2965     push    a
      0092C1 AE FF E0         [ 2] 2966     ldw     x, #-32
      0092C4 BF 4E            [ 2] 2967     ldw     *m_wlo, x
      0092C6 AE 00 20         [ 2] 2968     ldw     x, #32
      0092C9 BF 50            [ 2] 2969     ldw     *m_whi, x
      0092CB 84               [ 1] 2970     pop     a
      0092CC 88               [ 1] 2971     push    a
      0092CD A4 01            [ 1] 2972     and     a, #1               ; has0
      0092CF 27 1A            [ 1] 2973     jreq    00573$
      0092D1 BE 37            [ 2] 2974     ldw     x, *m_x0
      0092D3 1D 00 08         [ 2] 2975     subw    x, #8
      0092D6 BF 4E            [ 2] 2976     ldw     *m_wlo, x
      0092D8 BE 55            [ 2] 2977     ldw     x, *m_hx            ; labx0b > -0x4000?
      0092DA DE 00 ED         [ 2] 2978     ldw     x, (labx0b, x)
      0092DD A3 C0 00         [ 2] 2979     cpw     x, #-0x4000
      0092E0 2D 09            [ 1] 2980     jrsle   00573$
      0092E2 1D 00 02         [ 2] 2981     subw    x, #2
      0092E5 B3 4E            [ 2] 2982     cpw     x, *m_wlo
      0092E7 2D 02            [ 1] 2983     jrsle   00573$
      0092E9 BF 4E            [ 2] 2984     ldw     *m_wlo, x
      0092EB                       2985 00573$:
      0092EB 84               [ 1] 2986     pop     a
      0092EC A4 02            [ 1] 2987     and     a, #2               ; has1
      0092EE 27 1A            [ 1] 2988     jreq    00575$
      0092F0 BE 3A            [ 2] 2989     ldw     x, *m_x1
      0092F2 1C 00 08         [ 2] 2990     addw    x, #8
      0092F5 BF 50            [ 2] 2991     ldw     *m_whi, x
      0092F7 BE 55            [ 2] 2992     ldw     x, *m_hx
      0092F9 DE 00 F1         [ 2] 2993     ldw     x, (labx1b, x)
      0092FC A3 3F FF         [ 2] 2994     cpw     x, #0x3FFF
      0092FF 2E 09            [ 1] 2995     jrsge   00575$
      009301 1C 00 02         [ 2] 2996     addw    x, #2
      009304 B3 50            [ 2] 2997     cpw     x, *m_whi
      009306 2E 02            [ 1] 2998     jrsge   00575$
      009308 BF 50            [ 2] 2999     ldw     *m_whi, x
      00930A                       3000 00575$:
      00930A BE 4E            [ 2] 3001     ldw     x, *m_wlo
      00930C B3 50            [ 2] 3002     cpw     x, *m_whi
      00930E 2D 0D            [ 1] 3003     jrsle   00576$
      009310 72 BB 00 50      [ 2] 3004     addw    x, *m_whi           ; wlo > whi: theta = (wlo+whi)>>1
      009314 57               [ 2] 3005     sraw    x
      009315 BF 40            [ 2] 3006     ldw     *m_th, x
      009317 35 01 00 42      [ 1] 3007     mov     *m_hv, #1
      00931B 20 1B            [ 2] 3008     jra     00580$
      00931D                       3009 00576$:
                                   3010     ; th = clamp(have ? theta : 0, wlo, whi); have = 1
      00931D 3D 42            [ 1] 3011     tnz     *m_hv
      00931F 26 03            [ 1] 3012     jrne    00577$
      009321 5F               [ 1] 3013     clrw    x
      009322 BF 40            [ 2] 3014     ldw     *m_th, x
      009324                       3015 00577$:
      009324 BE 40            [ 2] 3016     ldw     x, *m_th
      009326 B3 4E            [ 2] 3017     cpw     x, *m_wlo
      009328 2E 02            [ 1] 3018     jrsge   00578$
      00932A BE 4E            [ 2] 3019     ldw     x, *m_wlo
      00932C                       3020 00578$:
      00932C B3 50            [ 2] 3021     cpw     x, *m_whi
      00932E 2D 02            [ 1] 3022     jrsle   00579$
      009330 BE 50            [ 2] 3023     ldw     x, *m_whi
      009332                       3024 00579$:
      009332 BF 40            [ 2] 3025     ldw     *m_th, x
      009334 35 01 00 42      [ 1] 3026     mov     *m_hv, #1
      009338                       3027 00580$:
                                   3028     ; top / clear1 scan over all 64 bins
      009338 3F 53            [ 1] 3029     clr     *m_cl1
      00933A 3F 52            [ 1] 3030     clr     *m_htp
      00933C 5F               [ 1] 3031     clrw    x
      00933D BF 58            [ 2] 3032     ldw     *m_top, x
      00933F 3F 54            [ 1] 3033     clr     *m_bb
      009341                       3034 00581$:
      009341 B6 54            [ 1] 3035     ld      a, *m_bb
      009343 A1 40            [ 1] 3036     cp      a, #64
      009345 24 36            [ 1] 3037     jrnc    00585$
      009347 5F               [ 1] 3038     clrw    x
      009348 97               [ 1] 3039     ld      xl, a
      009349 72 BB 00 84      [ 2] 3040     addw    x, *m_e
      00934D D6 01 18         [ 1] 3041     ld      a, (_ov, x)
      009350 4D               [ 1] 3042     tnz     a
      009351 27 26            [ 1] 3043     jreq    00584$
      009353 B6 54            [ 1] 3044     ld      a, *m_bb              ; d = (b<<1) - 63
      009355 48               [ 1] 3045     sll     a
      009356 5F               [ 1] 3046     clrw    x
      009357 97               [ 1] 3047     ld      xl, a
      009358 1D 00 3F         [ 2] 3048     subw    x, #63
      00935B A3 00 12         [ 2] 3049     cpw     x, #18
      00935E 2D 06            [ 1] 3050     jrsle   00582$
      009360 35 01 00 53      [ 1] 3051     mov     *m_cl1, #1
      009364 20 13            [ 2] 3052     jra     00584$
      009366                       3053 00582$:
      009366 A3 FF E8         [ 2] 3054     cpw     x, #-24
      009369 2D 0E            [ 1] 3055     jrsle   00584$
      00936B 3D 52            [ 1] 3056     tnz     *m_htp
      00936D 27 04            [ 1] 3057     jreq    00583$
      00936F B3 58            [ 2] 3058     cpw     x, *m_top
      009371 2D 06            [ 1] 3059     jrsle   00584$
      009373                       3060 00583$:
      009373 BF 58            [ 2] 3061     ldw     *m_top, x
      009375 35 01 00 52      [ 1] 3062     mov     *m_htp, #1
      009379                       3063 00584$:
      009379 3C 54            [ 1] 3064     inc     *m_bb
      00937B 20 C4            [ 2] 3065     jra     00581$
      00937D                       3066 00585$:
      00937D 3D 53            [ 1] 3067     tnz     *m_cl1
      00937F 26 38            [ 1] 3068     jrne    00589$
      009381 3D 52            [ 1] 3069     tnz     *m_htp
      009383 27 34            [ 1] 3070     jreq    00589$
                                   3071     ; floor = top + 3
      009385 BE 58            [ 2] 3072     ldw     x, *m_top
      009387 1C 00 03         [ 2] 3073     addw    x, #3
      00938A BF 7E            [ 2] 3074     ldw     *m_c, x             ; floor
      00938C 3D 42            [ 1] 3075     tnz     *m_hv
      00938E 27 04            [ 1] 3076     jreq    00586$
      009390 B3 40            [ 2] 3077     cpw     x, *m_th
      009392 2D 02            [ 1] 3078     jrsle   00587$
      009394                       3079 00586$:
      009394 BF 40            [ 2] 3080     ldw     *m_th, x            ; theta = floor
      009396                       3081 00587$:
      009396 35 01 00 42      [ 1] 3082     mov     *m_hv, #1
                                   3083     ; if (has1 && x1+2 > floor && theta > x1+2) theta = x1+2
      00939A CD 93 BC         [ 4] 3084     call    has01
      00939D A4 02            [ 1] 3085     and     a, #2
      00939F 27 18            [ 1] 3086     jreq    00589$
      0093A1 BE 3A            [ 2] 3087     ldw     x, *m_x1
      0093A3 1C 00 02         [ 2] 3088     addw    x, #2
      0093A6 B3 7E            [ 2] 3089     cpw     x, *m_c
      0093A8 2D 0F            [ 1] 3090     jrsle   00589$
      0093AA 90 93            [ 1] 3091     ldw     y, x
      0093AC BE 40            [ 2] 3092     ldw     x, *m_th
      0093AE 90 89            [ 2] 3093     pushw   y
      0093B0 13 01            [ 2] 3094     cpw     x, (1, sp)
      0093B2 90 85            [ 2] 3095     popw    y
      0093B4 2D 03            [ 1] 3096     jrsle   00589$
      0093B6 90 BF 40         [ 2] 3097     ldw     *m_th, y
      0093B9                       3098 00589$:
      0093B9 B6 42            [ 1] 3099     ld      a, *m_hv
      0093BB 81               [ 4] 3100     ret
                                   3101 
                                   3102 ; has01: A = has0 | (has1 << 1) for family *m_f (x0/x1 already loaded)
      0093BC                       3103 has01:
      0093BC 4F               [ 1] 3104     clr     a
      0093BD BE 37            [ 2] 3105     ldw     x, *m_x0
      0093BF A3 C0 00         [ 2] 3106     cpw     x, #-0x4000
      0093C2 2D 02            [ 1] 3107     jrsle   00590$
      0093C4 AA 01            [ 1] 3108     or      a, #1
      0093C6                       3109 00590$:
      0093C6 BE 3A            [ 2] 3110     ldw     x, *m_x1
      0093C8 A3 3F FF         [ 2] 3111     cpw     x, #0x3FFF
      0093CB 2E 02            [ 1] 3112     jrsge   00591$
      0093CD AA 02            [ 1] 3113     or      a, #2
      0093CF                       3114 00591$:
      0093CF 81               [ 4] 3115     ret
                                   3116 
                                   3117 ; ---------------------------------------------------------------- calibrate
      0093D0                       3118 _calibrate:
                                   3119     ; init: c_lo = -0x4000, c_hi = 0x3FFF, c_n = 0, h0c/h1c = priors
      0093D0 AE C0 00         [ 2] 3120     ldw     x, #-0x4000
      0093D3 BF D5            [ 2] 3121     ldw     *c_lo, x
      0093D5 BF D7            [ 2] 3122     ldw     *c_lo+2, x
      0093D7 AE 3F FF         [ 2] 3123     ldw     x, #0x3FFF
      0093DA BF D9            [ 2] 3124     ldw     *c_hi, x
      0093DC BF DB            [ 2] 3125     ldw     *c_hi+2, x
      0093DE 5F               [ 1] 3126     clrw    x
      0093DF BF DD            [ 2] 3127     ldw     *c_n, x
      0093E1 BF E3            [ 2] 3128     ldw     *zd56, x
      0093E3 AE 00 9A         [ 2] 3129     ldw     x, #154
      0093E6 BF DF            [ 2] 3130     ldw     *zh0c, x
      0093E8 AE 01 34         [ 2] 3131     ldw     x, #308
      0093EB BF E1            [ 2] 3132     ldw     *zh1c, x
      0093ED CD 87 38         [ 4] 3133     call    _set_gap56
                                   3134     ; per family: c_c0 = (154+308-gap)>>1; hist rows zeroed; labx init
      0093F0 3F 36            [ 1] 3135     clr     *m_f
      0093F2                       3136 00600$:
      0093F2 B6 36            [ 1] 3137     ld      a, *m_f
      0093F4 48               [ 1] 3138     sll     a
      0093F5 5F               [ 1] 3139     clrw    x
      0093F6 97               [ 1] 3140     ld      xl, a
      0093F7 BF 55            [ 2] 3141     ldw     *m_hx, x
      0093F9 DE 00 F9         [ 2] 3142     ldw     x, (zgap, x)
      0093FC 50               [ 2] 3143     negw    x
      0093FD 1C 01 CE         [ 2] 3144     addw    x, #462             ; 154+308-gap
      009400 57               [ 2] 3145     sraw    x
      009401 90 93            [ 1] 3146     ldw     y, x
      009403 BE 55            [ 2] 3147     ldw     x, *m_hx
      009405 DF 00 F5         [ 2] 3148     ldw     (c_c0, x), y
      009408 AE C0 00         [ 2] 3149     ldw     x, #-0x4000
      00940B 90 93            [ 1] 3150     ldw     y, x
      00940D BE 55            [ 2] 3151     ldw     x, *m_hx
      00940F DF 00 E5         [ 2] 3152     ldw     (labx0, x), y
      009412 DF 00 ED         [ 2] 3153     ldw     (labx0b, x), y
      009415 AE 3F FF         [ 2] 3154     ldw     x, #0x3FFF
      009418 90 93            [ 1] 3155     ldw     y, x
      00941A BE 55            [ 2] 3156     ldw     x, *m_hx
      00941C DF 00 E9         [ 2] 3157     ldw     (labx1, x), y
      00941F DF 00 F1         [ 2] 3158     ldw     (labx1b, x), y
      009422 B6 36            [ 1] 3159     ld      a, *m_f
      009424 CD 80 58         [ 4] 3160     call    hix
      009427 BF 84            [ 2] 3161     ldw     *m_e, x
      009429 3F 54            [ 1] 3162     clr     *m_bb
      00942B                       3163 00601$:
      00942B B6 54            [ 1] 3164     ld      a, *m_bb
      00942D A1 40            [ 1] 3165     cp      a, #64
      00942F 24 0E            [ 1] 3166     jrnc    00602$
      009431 5F               [ 1] 3167     clrw    x
      009432 97               [ 1] 3168     ld      xl, a
      009433 72 BB 00 84      [ 2] 3169     addw    x, *m_e
      009437 4F               [ 1] 3170     clr     a
      009438 D7 01 18         [ 1] 3171     ld      (_ov, x), a
      00943B 3C 54            [ 1] 3172     inc     *m_bb
      00943D 20 EC            [ 2] 3173     jra     00601$
      00943F                       3174 00602$:
      00943F 3C 36            [ 1] 3175     inc     *m_f
      009441 B6 36            [ 1] 3176     ld      a, *m_f
      009443 A1 02            [ 1] 3177     cp      a, #2
      009445 25 AB            [ 1] 3178     jrc     00600$
                                   3179     ; segment loop
      009447 CD 82 58         [ 4] 3180     call    _ss_init
      00944A                       3181 00603$:
      00944A AE 00 5D         [ 2] 3182     ldw     x, #_g_sg
      00944D CD 82 B2         [ 4] 3183     call    _ss_next
      009450 4D               [ 1] 3184     tnz     a
      009451 26 03            [ 1] 3185     jrne    00604$
      009453 CC 94 9B         [ 2] 3186     jp      00610$
      009456                       3187 00604$:
      009456 CD 90 4E         [ 4] 3188     call    ccloud
      009459 CE 00 5F         [ 2] 3189     ldw     x, _g_sg+2          ; if (k1 > NB) continue
      00945C C3 80 95         [ 2] 3190     cpw     x, _g_NB
      00945F 23 02            [ 2] 3191     jrule   00605$
      009461 20 E7            [ 2] 3192     jra     00603$
      009463                       3193 00605$:
                                   3194     ; known_all over [k0, min(k1,NB))  (k1 <= NB here)
      009463 CE 00 5F         [ 2] 3195     ldw     x, _g_sg+2
      009466 BF 84            [ 2] 3196     ldw     *m_e, x
      009468 CE 00 5D         [ 2] 3197     ldw     x, _g_sg
      00946B BF 86            [ 2] 3198     ldw     *m_t, x
      00946D                       3199 00606$:
      00946D BE 86            [ 2] 3200     ldw     x, *m_t
      00946F B3 84            [ 2] 3201     cpw     x, *m_e
      009471 24 10            [ 1] 3202     jrnc    00608$
      009473 CD 87 57         [ 4] 3203     call    _known_bit
      009476 A1 FF            [ 1] 3204     cp      a, #0xFF
      009478 26 02            [ 1] 3205     jrne    00607$
      00947A 20 CE            [ 2] 3206     jra     00603$              ; unknown bit -> next segment
      00947C                       3207 00607$:
      00947C BE 86            [ 2] 3208     ldw     x, *m_t
      00947E 5C               [ 1] 3209     incw    x
      00947F BF 86            [ 2] 3210     ldw     *m_t, x
      009481 20 EA            [ 2] 3211     jra     00606$
      009483                       3212 00608$:
      009483 CD 87 84         [ 4] 3213     call    _a_bounds_sg
      009486 CE 00 5F         [ 2] 3214     ldw     x, _g_sg+2          ; m_L = k1-k0 (la_int's a==L test; P4's
      009489 72 B0 00 5D      [ 2] 3215     subw    x, _g_sg            ; dq_decide sets it for itself, but HERE
      00948D BF 7C            [ 2] 3216     ldw     *m_L, x             ; it was stale -- fuzz_v22 E05 root cause)
      00948F BE 66            [ 2] 3217     ldw     x, *_dq_amin
      009491 B3 68            [ 2] 3218     cpw     x, *_dq_amax
      009493 26 B5            [ 1] 3219     jrne    00603$
      009495 CD 90 9A         [ 4] 3220     call    cadd                ; X = amin
      009498 CC 94 4A         [ 2] 3221     jp      00603$
      00949B                       3222 00610$:
                                   3223     ; width fit + separation guard
      00949B AE 00 70         [ 2] 3224     ldw     x, #112
      00949E BF 7E            [ 2] 3225     ldw     *m_c, x
      0094A0 AE 00 C0         [ 2] 3226     ldw     x, #192
      0094A3 BF 82            [ 2] 3227     ldw     *m_c1, x
      0094A5 4F               [ 1] 3228     clr     a
      0094A6 AE 00 9A         [ 2] 3229     ldw     x, #154
      0094A9 CD 91 6B         [ 4] 3230     call    wfit
      0094AC BF 76            [ 2] 3231     ldw     *m_h0, x            ; h0 (reuse decide temp)
      0094AE AE 00 FC         [ 2] 3232     ldw     x, #252
      0094B1 BF 7E            [ 2] 3233     ldw     *m_c, x
      0094B3 AE 01 78         [ 2] 3234     ldw     x, #376
      0094B6 BF 82            [ 2] 3235     ldw     *m_c1, x
      0094B8 A6 01            [ 1] 3236     ld      a, #1
      0094BA AE 01 34         [ 2] 3237     ldw     x, #308
      0094BD CD 91 6B         [ 4] 3238     call    wfit                ; h1
      0094C0 BF 78            [ 2] 3239     ldw     *m_h1, x
      0094C2 72 B0 00 76      [ 2] 3240     subw    x, *m_h0
      0094C6 A3 00 70         [ 2] 3241     cpw     x, #112
      0094C9 2F 0F            [ 1] 3242     jrslt   00611$
      0094CB A3 00 C4         [ 2] 3243     cpw     x, #196
      0094CE 2C 0A            [ 1] 3244     jrsgt   00611$
      0094D0 BE 76            [ 2] 3245     ldw     x, *m_h0
      0094D2 BF DF            [ 2] 3246     ldw     *zh0c, x
      0094D4 BE 78            [ 2] 3247     ldw     x, *m_h1
      0094D6 BF E1            [ 2] 3248     ldw     *zh1c, x
      0094D8 20 0A            [ 2] 3249     jra     00612$
      0094DA                       3250 00611$:
      0094DA AE 00 9A         [ 2] 3251     ldw     x, #154
      0094DD BF DF            [ 2] 3252     ldw     *zh0c, x
      0094DF AE 01 34         [ 2] 3253     ldw     x, #308
      0094E2 BF E1            [ 2] 3254     ldw     *zh1c, x
      0094E4                       3255 00612$:
                                   3256     ; per family: theta -> d56 clamp
      0094E4 3F 36            [ 1] 3257     clr     *m_f
      0094E6                       3258 00613$:
      0094E6 B6 36            [ 1] 3259     ld      a, *m_f
      0094E8 CD 91 B0         [ 4] 3260     call    th56
      0094EB 4D               [ 1] 3261     tnz     a
      0094EC 26 0A            [ 1] 3262     jrne    00614$
      0094EE B6 36            [ 1] 3263     ld      a, *m_f             ; no theta: d56 = 0
      0094F0 5F               [ 1] 3264     clrw    x
      0094F1 97               [ 1] 3265     ld      xl, a
      0094F2 4F               [ 1] 3266     clr     a
      0094F3 D7 00 E3         [ 1] 3267     ld      (zd56, x), a
      0094F6 20 3E            [ 2] 3268     jra     00616$
      0094F8                       3269 00614$:
                                   3270     ; delta = th + c_c0[f] - ((h0c + h1c - gap56[f]) >> 1), clamp +-24
      0094F8 B6 36            [ 1] 3271     ld      a, *m_f
      0094FA 48               [ 1] 3272     sll     a
      0094FB 5F               [ 1] 3273     clrw    x
      0094FC 97               [ 1] 3274     ld      xl, a
      0094FD 89               [ 2] 3275     pushw   x
      0094FE DE 00 F9         [ 2] 3276     ldw     x, (zgap, x)
      009501 BF 7E            [ 2] 3277     ldw     *m_c, x
      009503 BE DF            [ 2] 3278     ldw     x, *zh0c
      009505 72 BB 00 E1      [ 2] 3279     addw    x, *zh1c
      009509 72 B0 00 7E      [ 2] 3280     subw    x, *m_c
      00950D 57               [ 2] 3281     sraw    x
      00950E BF 7E            [ 2] 3282     ldw     *m_c, x             ; cfit
      009510 85               [ 2] 3283     popw    x
      009511 DE 00 F5         [ 2] 3284     ldw     x, (c_c0, x)
      009514 72 BB 00 40      [ 2] 3285     addw    x, *m_th
      009518 72 B0 00 7E      [ 2] 3286     subw    x, *m_c             ; delta
      00951C A3 FF E8         [ 2] 3287     cpw     x, #-24
      00951F 2E 03            [ 1] 3288     jrsge   00615$
      009521 AE FF E8         [ 2] 3289     ldw     x, #-24
      009524                       3290 00615$:
      009524 A3 00 18         [ 2] 3291     cpw     x, #24
      009527 2D 03            [ 1] 3292     jrsle   00617$
      009529 AE 00 18         [ 2] 3293     ldw     x, #24
      00952C                       3294 00617$:
      00952C 9F               [ 1] 3295     ld      a, xl
      00952D 88               [ 1] 3296     push    a
      00952E B6 36            [ 1] 3297     ld      a, *m_f
      009530 5F               [ 1] 3298     clrw    x
      009531 97               [ 1] 3299     ld      xl, a
      009532 84               [ 1] 3300     pop     a
      009533 D7 00 E3         [ 1] 3301     ld      (zd56, x), a
      009536                       3302 00616$:
      009536 3C 36            [ 1] 3303     inc     *m_f
      009538 B6 36            [ 1] 3304     ld      a, *m_f
      00953A A1 02            [ 1] 3305     cp      a, #2
      00953C 25 A8            [ 1] 3306     jrc     00613$
      00953E 81               [ 4] 3307     ret
                                   3308 
                                   3309 ; ======================================================================
                                   3310 ; Size-focused sample scanner: a rolled, bit-exact port of decode.c's
                                   3311 ; C scanner (the proven v1 ps_next semantics), ~350 B against scan.s's
                                   3312 ; speed-unrolled 900 B.  Slower per sample (~30 cy vs ~8); at ~11.5k
                                   3313 ; sample visits per decode that costs ~+10-15 ms on a production decode
                                   3314 ; -- traded for flash, which is the binding constraint.
                                   3315 ; ======================================================================
                                   3316 
                                   3317     .area CODE
                                   3318 
      00953F                       3319 _scan_init:
      00953F 5F               [ 1] 3320     clrw    x
      009540 BF C4            [ 2] 3321     ldw     *p_i, x
      009542 BF C6            [ 2] 3322     ldw     *p_tb, x
      009544 BF C8            [ 2] 3323     ldw     *p_ws, x
      009546 BF CA            [ 2] 3324     ldw     *p_tp, x
      009548 BF D3            [ 2] 3325     ldw     *p_lr, x
      00954A 3F CE            [ 1] 3326     clr     *p_s
      00954C 3F CF            [ 1] 3327     clr     *p_hp
      00954E 3F D0            [ 1] 3328     clr     *p_ip
      009550 3F D1            [ 1] 3329     clr     *p_se
      009552 3F D2            [ 1] 3330     clr     *p_dn
      009554 81               [ 4] 3331     ret
                                   3332 
                                   3333 ; A = cap[i + A(0/1)] helper: X = p_i (+carry offset in A) -> A = byte
      009555                       3334 capat:                          ; X = index -> A = cap[X]
      009555 72 BB 00 B7      [ 2] 3335     addw    x, *_scan_cap
      009559 F6               [ 1] 3336     ld      a, (x)
      00955A 81               [ 4] 3337     ret
                                   3338 
      00955B                       3339 _scan_next:
      00955B                       3340 00700$:                         ; while (!done)
      00955B 3D D2            [ 1] 3341     tnz     *p_dn
      00955D 27 03            [ 1] 3342     jreq    00701$
      00955F CC 96 C0         [ 2] 3343     jp      00790$
      009562                       3344 00701$:
      009562 BE C4            [ 2] 3345     ldw     x, *p_i             ; if (i >= len) break
      009564 B3 B9            [ 2] 3346     cpw     x, *_scan_len
      009566 25 03            [ 1] 3347     jrc     00702$
      009568 CC 96 C0         [ 2] 3348     jp      00780$
      00956B                       3349 00702$:
      00956B B6 CE            [ 1] 3350     ld      a, *p_s
      00956D A1 06            [ 1] 3351     cp      a, #6
      00956F 26 6C            [ 1] 3352     jrne    00710$
      009571 BE C4            [ 2] 3353     ldw     x, *p_i             ; s == 6: whole-octet fast paths need i+1 < len
      009573 5C               [ 1] 3354     incw    x
      009574 B3 B9            [ 2] 3355     cpw     x, *_scan_len
      009576 24 65            [ 1] 3356     jrnc    00710$
      009578 CD 95 55         [ 4] 3357     call    capat               ; bt = cap[i+1]
      00957B 4D               [ 1] 3358     tnz     a
      00957C 26 2F            [ 1] 3359     jrne    00703$
      00957E 3D D0            [ 1] 3360     tnz     *p_ip               ; bt == 0x00 && !in_pulse
      009580 26 5B            [ 1] 3361     jrne    00710$
      009582 BE C6            [ 2] 3362     ldw     x, *p_tb            ; t_prev = tb + 61 + ws; have_prev = 1
      009584 1C 00 3D         [ 2] 3363     addw    x, #61
      009587 72 BB 00 C8      [ 2] 3364     addw    x, *p_ws
      00958B BF CA            [ 2] 3365     ldw     *p_tp, x
      00958D 35 01 00 CF      [ 1] 3366     mov     *p_hp, #1
      009591 BE D3            [ 2] 3367     ldw     x, *p_lr            ; low_run += 8
      009593 1C 00 08         [ 2] 3368     addw    x, #8
      009596 BF D3            [ 2] 3369     ldw     *p_lr, x
      009598 CD 96 D6         [ 4] 3370     call    stepi               ; i++; tb += 40 (s stays 6)
      00959B 3D D1            [ 1] 3371     tnz     *p_se               ; seen && low_run >= 200 -> done
      00959D 27 BC            [ 1] 3372     jreq    00700$
      00959F BE D3            [ 2] 3373     ldw     x, *p_lr
      0095A1 A3 00 C8         [ 2] 3374     cpw     x, #200
      0095A4 25 B5            [ 1] 3375     jrc     00700$
      0095A6 35 01 00 D2      [ 1] 3376     mov     *p_dn, #1
      0095AA CC 96 C0         [ 2] 3377     jp      00790$
      0095AD                       3378 00703$:
      0095AD A1 FF            [ 1] 3379     cp      a, #0xFF            ; bt == 0xFF && in_pulse
      0095AF 26 2C            [ 1] 3380     jrne    00710$
      0095B1 3D D0            [ 1] 3381     tnz     *p_ip
      0095B3 27 28            [ 1] 3382     jreq    00710$
      0095B5 BE C6            [ 2] 3383     ldw     x, *p_tb            ; fa = tb + 63 + ws; ws += 2
      0095B7 1C 00 3F         [ 2] 3384     addw    x, #63
      0095BA 72 BB 00 C8      [ 2] 3385     addw    x, *p_ws
      0095BE BF BF            [ 2] 3386     ldw     *_scan_fa, x
      0095C0 BF CA            [ 2] 3387     ldw     *p_tp, x            ; t_prev = fa; have_prev = 1
      0095C2 35 01 00 CF      [ 1] 3388     mov     *p_hp, #1
      0095C6 BE C8            [ 2] 3389     ldw     x, *p_ws
      0095C8 5C               [ 1] 3390     incw    x
      0095C9 5C               [ 1] 3391     incw    x
      0095CA BF C8            [ 2] 3392     ldw     *p_ws, x
      0095CC 35 05 00 C3      [ 1] 3393     mov     *_scan_sfa, #5
      0095D0 5F               [ 1] 3394     clrw    x
      0095D1 BF D3            [ 2] 3395     ldw     *p_lr, x
      0095D3 35 01 00 D1      [ 1] 3396     mov     *p_se, #1
      0095D7 CD 96 D6         [ 4] 3397     call    stepi
      0095DA CC 95 5B         [ 2] 3398     jp      00700$
      0095DD                       3399 00710$:
                                   3400     ; ordinary sample: v = bit of cap[i] (s<6) or cap[i+1] (s>=6)
      0095DD B6 CE            [ 1] 3401     ld      a, *p_s
      0095DF A1 06            [ 1] 3402     cp      a, #6
      0095E1 24 0F            [ 1] 3403     jrnc    00711$
      0095E3 BE C4            [ 2] 3404     ldw     x, *p_i             ; v = (cap[i] >> (5-s)) & 1
      0095E5 CD 95 55         [ 4] 3405     call    capat
      0095E8 B7 0D            [ 1] 3406     ld      *m_s, a
      0095EA B6 CE            [ 1] 3407     ld      a, *p_s
      0095EC AB 03            [ 1] 3408     add     a, #3               ; bit (5-s) -> 8-(5-s) = s+3 shifts
      0095EE B7 AD            [ 1] 3409     ld      *m_vi, a
      0095F0 20 1A            [ 2] 3410     jra     00713$
      0095F2                       3411 00711$:
      0095F2 BE C4            [ 2] 3412     ldw     x, *p_i             ; s >= 6: boundary bits live in cap[i+1]
      0095F4 5C               [ 1] 3413     incw    x
      0095F5 B3 B9            [ 2] 3414     cpw     x, *_scan_len
      0095F7 25 08            [ 1] 3415     jrc     00712$
      0095F9 CD 96 D6         [ 4] 3416     call    stepi               ; last loop: BS lost; s = 0; continue
      0095FC 3F CE            [ 1] 3417     clr     *p_s
      0095FE CC 95 5B         [ 2] 3418     jp      00700$
      009601                       3419 00712$:
      009601 CD 95 55         [ 4] 3420     call    capat               ; v = (cap[i+1] >> (7-(s-6))) & 1
      009604 B7 0D            [ 1] 3421     ld      *m_s, a
      009606 B6 CE            [ 1] 3422     ld      a, *p_s
      009608 A0 05            [ 1] 3423     sub     a, #5               ; bit (13-s) -> 8-(13-s) = s-5 shifts
      00960A B7 AD            [ 1] 3424     ld      *m_vi, a
      00960C                       3425 00713$:
      00960C B6 0D            [ 1] 3426     ld      a, *m_s
      00960E                       3427 00714$:
      00960E 48               [ 1] 3428     sll     a
      00960F 3A AD            [ 1] 3429     dec     *m_vi
      009611 26 FB            [ 1] 3430     jrne    00714$
      009613 4F               [ 1] 3431     clr     a
      009614 49               [ 1] 3432     rlc     a
      009615 B7 AD            [ 1] 3433     ld      *m_vi, a            ; v
                                   3434     ; t = tb + O[s] + ws
      009617 5F               [ 1] 3435     clrw    x
      009618 B6 CE            [ 1] 3436     ld      a, *p_s
      00961A 97               [ 1] 3437     ld      xl, a
      00961B D6 80 04         [ 1] 3438     ld      a, (sot, x)
      00961E 5F               [ 1] 3439     clrw    x
      00961F 97               [ 1] 3440     ld      xl, a
      009620 72 BB 00 C6      [ 2] 3441     addw    x, *p_tb
      009624 72 BB 00 C8      [ 2] 3442     addw    x, *p_ws
      009628 BF CC            [ 2] 3443     ldw     *p_t, x
                                   3444     ; slot/loop advance
      00962A B6 CE            [ 1] 3445     ld      a, *p_s
      00962C A1 07            [ 1] 3446     cp      a, #7
      00962E 26 07            [ 1] 3447     jrne    00715$
      009630 CD 96 D6         [ 4] 3448     call    stepi
      009633 3F CE            [ 1] 3449     clr     *p_s
      009635 20 02            [ 2] 3450     jra     00716$
      009637                       3451 00715$:
      009637 3C CE            [ 1] 3452     inc     *p_s
      009639                       3453 00716$:
      009639 3D AD            [ 1] 3454     tnz     *m_vi
      00963B 27 4C            [ 1] 3455     jreq    00730$
                                   3456     ; ---- HIGH sample ----
      00963D B6 CE            [ 1] 3457     ld      a, *p_s             ; ws += W[s]  (s was advanced: use s-1 mod 8)
      00963F 4A               [ 1] 3458     dec     a
      009640 A4 07            [ 1] 3459     and     a, #7
      009642 5F               [ 1] 3460     clrw    x
      009643 97               [ 1] 3461     ld      xl, a
      009644 D6 80 0C         [ 1] 3462     ld      a, (swt, x)
      009647 88               [ 1] 3463     push    a                   ; sign-extend s8 into X
      009648 5F               [ 1] 3464     clrw    x
      009649 97               [ 1] 3465     ld      xl, a
      00964A 84               [ 1] 3466     pop     a
      00964B 4D               [ 1] 3467     tnz     a
      00964C 2A 03            [ 1] 3468     jrpl    00717$
      00964E 1C FF 00         [ 2] 3469     addw    x, #0xFF00
      009651                       3470 00717$:
      009651 72 BB 00 C8      [ 2] 3471     addw    x, *p_ws
      009655 BF C8            [ 2] 3472     ldw     *p_ws, x
      009657 3D D0            [ 1] 3473     tnz     *p_ip
      009659 26 1A            [ 1] 3474     jrne    00718$
      00965B 35 01 00 D0      [ 1] 3475     mov     *p_ip, #1           ; pulse starts
      00965F 3D CF            [ 1] 3476     tnz     *p_hp
      009661 27 04            [ 1] 3477     jreq    00719$
      009663 BE CA            [ 2] 3478     ldw     x, *p_tp            ; ra = t_prev
      009665 20 08            [ 2] 3479     jra     00720$
      009667                       3480 00719$:
      009667 BE CC            [ 2] 3481     ldw     x, *p_t             ; ra = max(t-4, 0)
      009669 1D 00 04         [ 2] 3482     subw    x, #4
      00966C 24 01            [ 1] 3483     jrnc    00720$
      00966E 5F               [ 1] 3484     clrw    x
      00966F                       3485 00720$:
      00966F BF BB            [ 2] 3486     ldw     *_scan_ra, x
      009671 BE CC            [ 2] 3487     ldw     x, *p_t
      009673 BF BD            [ 2] 3488     ldw     *_scan_rb, x
      009675                       3489 00718$:
      009675 BE CC            [ 2] 3490     ldw     x, *p_t             ; fa = t; sfa = s(orig); low_run = 0; seen = 1
      009677 BF BF            [ 2] 3491     ldw     *_scan_fa, x
      009679 B6 CE            [ 1] 3492     ld      a, *p_s
      00967B 4A               [ 1] 3493     dec     a
      00967C A4 07            [ 1] 3494     and     a, #7
      00967E B7 C3            [ 1] 3495     ld      *_scan_sfa, a
      009680 5F               [ 1] 3496     clrw    x
      009681 BF D3            [ 2] 3497     ldw     *p_lr, x
      009683 35 01 00 D1      [ 1] 3498     mov     *p_se, #1
      009687 20 2C            [ 2] 3499     jra     00740$
      009689                       3500 00730$:
                                   3501     ; ---- LOW sample ----
      009689 3D D0            [ 1] 3502     tnz     *p_ip
      00968B 27 14            [ 1] 3503     jreq    00731$
      00968D 3F D0            [ 1] 3504     clr     *p_ip               ; pulse ends: emit
      00968F BE CC            [ 2] 3505     ldw     x, *p_t
      009691 BF C1            [ 2] 3506     ldw     *_scan_fb, x
      009693 BF CA            [ 2] 3507     ldw     *p_tp, x            ; t_prev = t; have_prev = 1
      009695 35 01 00 CF      [ 1] 3508     mov     *p_hp, #1
      009699 AE 00 01         [ 2] 3509     ldw     x, #1
      00969C BF D3            [ 2] 3510     ldw     *p_lr, x
      00969E A6 01            [ 1] 3511     ld      a, #1
      0096A0 81               [ 4] 3512     ret
      0096A1                       3513 00731$:
      0096A1 BE D3            [ 2] 3514     ldw     x, *p_lr            ; low_run++
      0096A3 5C               [ 1] 3515     incw    x
      0096A4 BF D3            [ 2] 3516     ldw     *p_lr, x
      0096A6 3D D1            [ 1] 3517     tnz     *p_se
      0096A8 27 0B            [ 1] 3518     jreq    00740$
      0096AA A3 00 C8         [ 2] 3519     cpw     x, #200
      0096AD 25 06            [ 1] 3520     jrc     00740$
      0096AF 35 01 00 D2      [ 1] 3521     mov     *p_dn, #1
      0096B3 20 0B            [ 2] 3522     jra     00790$
      0096B5                       3523 00740$:
      0096B5 BE CC            [ 2] 3524     ldw     x, *p_t             ; loop bottom: t_prev = t; have_prev = 1
      0096B7 BF CA            [ 2] 3525     ldw     *p_tp, x
      0096B9 35 01 00 CF      [ 1] 3526     mov     *p_hp, #1
      0096BD CC 95 5B         [ 2] 3527     jp      00700$
                                   3528 
      0096C0                       3529 00780$:                         ; data exhausted
      0096C0                       3530 00790$:                         ; done / latch: flush a pulse in flight
      0096C0 3D D0            [ 1] 3531     tnz     *p_ip
      0096C2 27 0C            [ 1] 3532     jreq    00791$
      0096C4 3F D0            [ 1] 3533     clr     *p_ip
      0096C6 BE BF            [ 2] 3534     ldw     x, *_scan_fa        ; fb = fa + 4
      0096C8 1C 00 04         [ 2] 3535     addw    x, #4
      0096CB BF C1            [ 2] 3536     ldw     *_scan_fb, x
      0096CD A6 01            [ 1] 3537     ld      a, #1
      0096CF 81               [ 4] 3538     ret
      0096D0                       3539 00791$:
      0096D0 35 01 00 D2      [ 1] 3540     mov     *p_dn, #1
      0096D4 4F               [ 1] 3541     clr     a
      0096D5 81               [ 4] 3542     ret
                                   3543 
                                   3544 ; stepi: i++; tb += 40
      0096D6                       3545 stepi:
      0096D6 BE C4            [ 2] 3546     ldw     x, *p_i
      0096D8 5C               [ 1] 3547     incw    x
      0096D9 BF C4            [ 2] 3548     ldw     *p_i, x
      0096DB BE C6            [ 2] 3549     ldw     x, *p_tb
      0096DD 1C 00 28         [ 2] 3550     addw    x, #40
      0096E0 BF C6            [ 2] 3551     ldw     *p_tb, x
      0096E2 81               [ 4] 3552     ret
