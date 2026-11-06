                                      1 ; scan.s -- hand-assembly sample scanner for the v2.1 decoder hot path
                                      2 ; (STM8S001J3, SDCC calling convention, sdcccall(1): result in A;
                                      3 ;  A/X/Y caller-saved).
                                      4 ;
                                      5 ; Replaces decode.c's C scanner (v1 ps_next measured 798 B flash and
                                      6 ; ~200 ucsim ticks per sample visit -- EMBEDDED_FEASIBILITY.md SS6).
                                      7 ; This is the "tight assembly" projection of that report: documented
                                      8 ; cycle counts are annotated per block below; real silicon runs ~7%
                                      9 ; slower than the documented/ucsim numbers on this instruction mix
                                     10 ; (calibrated against the crystal-exact capture loop), and the on-chip
                                     11 ; TIM1 measurement in rbarf_v21.c (TIM:<ticks> line, 16 us/tick) is the
                                     12 ; authoritative figure.
                                     13 ;
                                     14 ; CONTRACT (bit-exact vs recon/approaches/embedded_v2.py _pulse_stream,
                                     15 ; proven by recon/approaches/dev_fw/ ucsim parity):
                                     16 ;   scan_cap/scan_len  in : capture buffer (cap_code.s byte layout), bytes
                                     17 ;   scan_init()             reset stream state
                                     18 ;   scan_next() -> A=1      pulse out: scan_ra/rb/fa/fb (u16 cycles),
                                     19 ;                           scan_sfa (slot of last high sample)
                                     20 ;                A=0        stream end (latch run seen, or data exhausted)
                                     21 ;
                                     22 ; Capture byte layout (DATASET.md): byte i bits5..0 = R0..R5 of loop i,
                                     23 ; byte i+1 bits7..6 = BS0,BS1 of loop i.  The scanner composes one
                                     24 ; loop-aligned octet A = (byte[i]<<2)|(byte[i+1]>>6), MSB-first
                                     25 ; chronological = R0,R1,R2,R3,R4,R5,BS0,BS1, and walks it with an
                                     26 ; unrolled 8-slot state machine, two modes (low/high).
                                     27 ;
                                     28 ; Fitted sampler model (integer cycles, dev_calibration/fitted_model):
                                     29 ;   slot offsets O = [0,4,9,13,17,21,27,32], loop = 40 cy
                                     30 ;   inter-sample gaps  GAP  = [4,5,4,4,4,6,5,8]      (slot j -> j+1)
                                     31 ;   +data-dependent    W    = [0,-1,0,+2,0,0,0,+1]   (added when HIGH)
                                     32 ;   high-sample gaps   GAPW = [4,4,4,6,4,6,5,9]      (GAP+W)
                                     33 ; Time t is carried incrementally in X (u16 CPU cycles): no multiplies.
                                     34 ; ra of a rise = t - GAP[prev slot] (previous sample was low); fa/sfa of
                                     35 ; a fall = derived from t - GAPW[prev slot] (previous sample was high):
                                     36 ; the hot loops store NOTHING per sample.
                                     37 ;
                                     38 ; Latch: 200 consecutive low samples end the stream (down-counter; the
                                     39 ; whole-octet fast path subtracts 8 -- an intra-octet trigger returns at
                                     40 ; the octet end, which is observably identical: no pulses in between).
                                     41 ; The Python reference arms the latch only after the first pulse ("seen");
                                     42 ; the capture is edge-triggered so a 200-low run before the first pulse
                                     43 ; cannot occur (measured: max leading-low run over all 240 real captures
                                     44 ; = 0 samples), and this scanner omits the flag.  Guard: scan_len >= 2
                                     45 ; (decode is always called with a 256..640-byte buffer).
                                     46 ;
                                     47 ; Whole-octet fast paths (exact, same accounting as v1 decoder.c):
                                     48 ;   octet 0x00 in low mode:  t += 40, latch -= 8      (idle / latch tail)
                                     49 ;   octet 0xFF in high mode: t += 42 (40 + W-sum 2)   (long pulses)
                                     50 ;
                                     51 ; DISPATCH: scan_next resumes mid-octet after each emitted pulse via a
                                     52 ; 9-entry jump table indexed by s_res: 0=fetch, 1..7=low slot, 8=done.
                                     53 ; (Falls resume in low mode by construction; entry 6 checks the 6-bit
                                     54 ; tail octet's end.)
                                     55 
                                     56     .module scan
                                     57     .globl _scan_cap
                                     58     .globl _scan_len
                                     59     .globl _scan_ra
                                     60     .globl _scan_rb
                                     61     .globl _scan_fa
                                     62     .globl _scan_fb
                                     63     .globl _scan_sfa
                                     64     .globl _scan_init
                                     65     .globl _scan_next
                                     66     .globl _cap_capture
                                     67     .globl _cap_loop
                                     68 
                                     69 ; ---------------------------------------------------------------- state
                                     70     .area DATA
                                     71 
      000191                         72 _scan_cap:  .ds 2       ; in: capture pointer
      000193                         73 _scan_len:  .ds 2       ; in: capture bytes (= loops)
      000195                         74 _scan_ra:   .ds 2       ; out: rise bracket lo (cycles)
      000197                         75 _scan_rb:   .ds 2       ; out: rise bracket hi
      000199                         76 _scan_fa:   .ds 2       ; out: last-high time
      00019B                         77 _scan_fb:   .ds 2       ; out: fall bracket hi
      00019D                         78 _scan_sfa:  .ds 1       ; out: slot of last high sample (family id)
      00019E                         79 s_ptr:      .ds 2       ; next R-byte
      0001A0                         80 s_left:     .ds 2       ; full octets remaining after the current one
      0001A2                         81 s_t:        .ds 2       ; saved t between calls
      0001A4                         82 s_oct:      .ds 1       ; saved octet shift register
      0001A5                         83 s_res:      .ds 1       ; resume index 0..8
      0001A6                         84 s_latch:    .ds 1       ; latch down-counter (200 low samples)
      0001A7                         85 s_tail:     .ds 1       ; processing the final 6-sample octet
                                     86 
                                     87     .area CODE
                                     88 
                                     89 ; ---------------------------------------------------------------- init
      0081E7                         90 _scan_init:
      0081E7 CE 01 91         [ 2]   91     ldw     x, _scan_cap
      0081EA CF 01 9E         [ 2]   92     ldw     s_ptr, x
      0081ED 72 5F 01 A7      [ 1]   93     clr     s_tail
      0081F1 72 5F 01 A4      [ 1]   94     clr     s_oct
      0081F5 35 C8 01 A6      [ 1]   95     mov     s_latch, #200
      0081F9 5F               [ 1]   96     clrw    x
      0081FA CF 01 A2         [ 2]   97     ldw     s_t, x
      0081FD CE 01 93         [ 2]   98     ldw     x, _scan_len
      008200 27 09            [ 1]   99     jreq    00001$              ; len == 0 -> immediately done
      008202 5A               [ 2]  100     decw    x
      008203 CF 01 A0         [ 2]  101     ldw     s_left, x           ; octets with a following BS byte
      008206 35 00 01 A5      [ 1]  102     mov     s_res, #0
      00820A 81               [ 4]  103     ret
      00820B                        104 00001$:
      00820B 35 08 01 A5      [ 1]  105     mov     s_res, #8
      00820F 81               [ 4]  106     ret
                                    107 
                                    108 ; ------------------------------------------------------------- dispatch
                                    109 ; call(4) + 9 cy documented to reach the resume point
      008210                        110 _scan_next:
      008210 5F               [ 1]  111     clrw    x
      008211 C6 01 A5         [ 1]  112     ld      a, s_res
      008214 48               [ 1]  113     sll     a
      008215 97               [ 1]  114     ld      xl, a
      008216 DE 82 23         [ 2]  115     ldw     x, (jtab, x)
      008219 90 93            [ 1]  116     ldw     y, x
      00821B CE 01 A2         [ 2]  117     ldw     x, s_t              ; X = t
      00821E C6 01 A4         [ 1]  118     ld      a, s_oct            ; A = octet register
      008221 90 FC            [ 2]  119     jp      (y)
                                    120 
      008223                        121 jtab:
      008223 82 5B                  122     .dw     fetch_low           ; 0: octet boundary, low
      008225 82 90                  123     .dw     low1                ; 1..7: resume at low slot J
      008227 82 9C                  124     .dw     low2
      008229 82 A8                  125     .dw     low3
      00822B 82 B4                  126     .dw     low4
      00822D 82 C0                  127     .dw     low5
      00822F 82 37                  128     .dw     resume6             ; 6: guarded (tail octet has no slot 6)
      008231 82 DE                  129     .dw     low7
      008233 82 35                  130     .dw     done_e              ; 8: stream ended
                                    131 
      008235                        132 done_e:
      008235 4F               [ 1]  133     clr     a
      008236 81               [ 4]  134     ret
                                    135 
      008237                        136 resume6:
      008237 72 5D 01 A7      [ 1]  137     tnz     s_tail
      00823B 27 03            [ 1]  138     jreq    00002$
      00823D CC 85 48         [ 2]  139     jp      end_low_tail
      008240                        140 00002$:
      008240 CC 82 D2         [ 2]  141     jp      low6
                                    142 
                                    143 ; ------------------------------------- low mode: octet fetch + fast path
      008243                        144 tl_low:
      008243 CC 85 2A         [ 2]  145     jp      tail_low
                                    146 
                                    147 ; all-low octet: 8 samples skipped -- 9 cy documented
      008246                        148 fast_low0:
      008246 1C 00 28         [ 2]  149     addw    x, #40              ; t += LOOP_CY (no W: all low)
      008249 C6 01 A6         [ 1]  150     ld      a, s_latch
      00824C A0 08            [ 1]  151     sub     a, #8
      00824E C7 01 A6         [ 1]  152     ld      s_latch, a
      008251 23 02            [ 2]  153     jrule   00003$              ; latch run complete (seen: see header)
      008253 20 06            [ 2]  154     jra     fetch_low
      008255                        155 00003$:
      008255 35 08 01 A5      [ 1]  156     mov     s_res, #8
      008259 4F               [ 1]  157     clr     a
      00825A 81               [ 4]  158     ret
                                    159 
                                    160 ; compose next octet -- 22 cy documented (2.75 cy/sample)
      00825B                        161 fetch_low:
      00825B 90 CE 01 A0      [ 2]  162     ldw     y, s_left
      00825F 27 E2            [ 1]  163     jreq    tl_low              ; no BS byte left -> 6-bit tail
      008261 90 5A            [ 2]  164     decw    y
      008263 90 CF 01 A0      [ 2]  165     ldw     s_left, y
      008267 90 CE 01 9E      [ 2]  166     ldw     y, s_ptr
      00826B 90 F6            [ 1]  167     ld      a, (y)              ; byte i  (R0..R5 in bits 5..0)
      00826D 90 5C            [ 1]  168     incw    y
      00826F 90 CF 01 9E      [ 2]  169     ldw     s_ptr, y
      008273 48               [ 1]  170     sll     a
      008274 48               [ 1]  171     sll     a
      008275 C7 01 A4         [ 1]  172     ld      s_oct, a
      008278 90 F6            [ 1]  173     ld      a, (y)              ; byte i+1 (BS0,BS1 in bits 7..6)
      00827A 4E               [ 1]  174     swap    a
      00827B 44               [ 1]  175     srl     a
      00827C 44               [ 1]  176     srl     a
      00827D A4 03            [ 1]  177     and     a, #0x03
      00827F CA 01 A4         [ 1]  178     or      a, s_oct            ; A = R0..R5,BS0,BS1 MSB-first
      008282 27 C2            [ 1]  179     jreq    fast_low0
                                    180     ; fallthrough -> low0
                                    181 
                                    182 ; ------------------------------------------------- low mode, slots 0..7
                                    183 ; per low sample: sll(1) jrc(1) addw(2) dec(1) jreq(1) = 6 cy documented
      008284                        184 low0:
      008284 48               [ 1]  185     sll     a
      008285 25 66            [ 1]  186     jrc     rt0
      008287 1C 00 04         [ 2]  187     addw    x, #4
      00828A 72 5A 01 A6      [ 1]  188     dec     s_latch
      00828E 27 75            [ 1]  189     jreq    latch_end
      008290                        190 low1:
      008290 48               [ 1]  191     sll     a
      008291 25 5D            [ 1]  192     jrc     rt1
      008293 1C 00 05         [ 2]  193     addw    x, #5
      008296 72 5A 01 A6      [ 1]  194     dec     s_latch
      00829A 27 69            [ 1]  195     jreq    latch_end
      00829C                        196 low2:
      00829C 48               [ 1]  197     sll     a
      00829D 25 54            [ 1]  198     jrc     rt2
      00829F 1C 00 04         [ 2]  199     addw    x, #4
      0082A2 72 5A 01 A6      [ 1]  200     dec     s_latch
      0082A6 27 5D            [ 1]  201     jreq    latch_end
      0082A8                        202 low3:
      0082A8 48               [ 1]  203     sll     a
      0082A9 25 4B            [ 1]  204     jrc     rt3
      0082AB 1C 00 04         [ 2]  205     addw    x, #4
      0082AE 72 5A 01 A6      [ 1]  206     dec     s_latch
      0082B2 27 51            [ 1]  207     jreq    latch_end
      0082B4                        208 low4:
      0082B4 48               [ 1]  209     sll     a
      0082B5 25 42            [ 1]  210     jrc     rt4
      0082B7 1C 00 04         [ 2]  211     addw    x, #4
      0082BA 72 5A 01 A6      [ 1]  212     dec     s_latch
      0082BE 27 45            [ 1]  213     jreq    latch_end
      0082C0                        214 low5:
      0082C0 48               [ 1]  215     sll     a
      0082C1 25 39            [ 1]  216     jrc     rt5
      0082C3 1C 00 06         [ 2]  217     addw    x, #6
      0082C6 72 5A 01 A6      [ 1]  218     dec     s_latch
      0082CA 27 39            [ 1]  219     jreq    latch_end
      0082CC 72 5D 01 A7      [ 1]  220     tnz     s_tail              ; tail octet ends after slot 5
      0082D0 26 39            [ 1]  221     jrne    el_t
      0082D2                        222 low6:
      0082D2 48               [ 1]  223     sll     a
      0082D3 25 2A            [ 1]  224     jrc     rt6
      0082D5 1C 00 05         [ 2]  225     addw    x, #5
      0082D8 72 5A 01 A6      [ 1]  226     dec     s_latch
      0082DC 27 27            [ 1]  227     jreq    latch_end
      0082DE                        228 low7:
      0082DE 48               [ 1]  229     sll     a
      0082DF 25 21            [ 1]  230     jrc     rt7
      0082E1 1C 00 08         [ 2]  231     addw    x, #8
      0082E4 72 5A 01 A6      [ 1]  232     dec     s_latch
      0082E8 27 1B            [ 1]  233     jreq    latch_end
      0082EA CC 82 5B         [ 2]  234     jp      fetch_low
                                    235 
                                    236 ; rise trampolines (keep the jrc targets in relative range)
      0082ED CC 83 0E         [ 2]  237 rt0: jp     rise0
      0082F0 CC 83 29         [ 2]  238 rt1: jp     rise1
      0082F3 CC 83 40         [ 2]  239 rt2: jp     rise2
      0082F6 CC 83 57         [ 2]  240 rt3: jp     rise3
      0082F9 CC 83 6E         [ 2]  241 rt4: jp     rise4
      0082FC CC 83 85         [ 2]  242 rt5: jp     rise5
      0082FF CC 83 9C         [ 2]  243 rt6: jp     rise6
      008302 CC 83 B3         [ 2]  244 rt7: jp     rise7
                                    245 
      008305                        246 latch_end:                      ; 200 consecutive lows: stream over
      008305 35 08 01 A5      [ 1]  247     mov     s_res, #8
      008309 4F               [ 1]  248     clr     a
      00830A 81               [ 4]  249     ret
                                    250 
      00830B                        251 el_t:
      00830B CC 85 48         [ 2]  252     jp      end_low_tail
                                    253 
                                    254 ; --------------------------------------------------------- rise sites
                                    255 ; sample at slot J is the first high of a pulse (low mode, C=1):
                                    256 ;   ra = t - GAP[J-1]  (previous sample was low), rb = t, latch reset,
                                    257 ;   t += GAPW[J], continue in high mode at slot J+1.   ~12 cy documented
      00830E                        258 rise0:
      00830E 90 93            [ 1]  259     ldw     y, x
      008310 72 A2 00 08      [ 2]  260     subw    y, #8               ; GAP[7]
      008314 24 02            [ 1]  261     jrnc    00004$
      008316 90 5F            [ 1]  262     clrw    y                   ; first sample of the capture (t = 0):
      008318                        263 00004$:                         ; ra = max(t - FIRST_BR, 0) = 0
      008318 90 CF 01 95      [ 2]  264     ldw     _scan_ra, y
      00831C CF 01 97         [ 2]  265     ldw     _scan_rb, x
      00831F 35 C8 01 A6      [ 1]  266     mov     s_latch, #200
      008323 1C 00 04         [ 2]  267     addw    x, #4               ; GAPW[0]
      008326 CC 84 03         [ 2]  268     jp      hi1
      008329                        269 rise1:
      008329 90 93            [ 1]  270     ldw     y, x
      00832B 72 A2 00 04      [ 2]  271     subw    y, #4               ; GAP[0]
      00832F 90 CF 01 95      [ 2]  272     ldw     _scan_ra, y
      008333 CF 01 97         [ 2]  273     ldw     _scan_rb, x
      008336 35 C8 01 A6      [ 1]  274     mov     s_latch, #200
      00833A 1C 00 04         [ 2]  275     addw    x, #4               ; GAPW[1]
      00833D CC 84 09         [ 2]  276     jp      hi2
      008340                        277 rise2:
      008340 90 93            [ 1]  278     ldw     y, x
      008342 72 A2 00 05      [ 2]  279     subw    y, #5               ; GAP[1]
      008346 90 CF 01 95      [ 2]  280     ldw     _scan_ra, y
      00834A CF 01 97         [ 2]  281     ldw     _scan_rb, x
      00834D 35 C8 01 A6      [ 1]  282     mov     s_latch, #200
      008351 1C 00 04         [ 2]  283     addw    x, #4               ; GAPW[2]
      008354 CC 84 0F         [ 2]  284     jp      hi3
      008357                        285 rise3:
      008357 90 93            [ 1]  286     ldw     y, x
      008359 72 A2 00 04      [ 2]  287     subw    y, #4               ; GAP[2]
      00835D 90 CF 01 95      [ 2]  288     ldw     _scan_ra, y
      008361 CF 01 97         [ 2]  289     ldw     _scan_rb, x
      008364 35 C8 01 A6      [ 1]  290     mov     s_latch, #200
      008368 1C 00 06         [ 2]  291     addw    x, #6               ; GAPW[3]
      00836B CC 84 15         [ 2]  292     jp      hi4
      00836E                        293 rise4:
      00836E 90 93            [ 1]  294     ldw     y, x
      008370 72 A2 00 04      [ 2]  295     subw    y, #4               ; GAP[3]
      008374 90 CF 01 95      [ 2]  296     ldw     _scan_ra, y
      008378 CF 01 97         [ 2]  297     ldw     _scan_rb, x
      00837B 35 C8 01 A6      [ 1]  298     mov     s_latch, #200
      00837F 1C 00 04         [ 2]  299     addw    x, #4               ; GAPW[4]
      008382 CC 84 1B         [ 2]  300     jp      hi5
      008385                        301 rise5:
      008385 90 93            [ 1]  302     ldw     y, x
      008387 72 A2 00 04      [ 2]  303     subw    y, #4               ; GAP[4]
      00838B 90 CF 01 95      [ 2]  304     ldw     _scan_ra, y
      00838F CF 01 97         [ 2]  305     ldw     _scan_rb, x
      008392 35 C8 01 A6      [ 1]  306     mov     s_latch, #200
      008396 1C 00 06         [ 2]  307     addw    x, #6               ; GAPW[5]
      008399 CC 84 27         [ 2]  308     jp      hi6
      00839C                        309 rise6:
      00839C 90 93            [ 1]  310     ldw     y, x
      00839E 72 A2 00 06      [ 2]  311     subw    y, #6               ; GAP[5]
      0083A2 90 CF 01 95      [ 2]  312     ldw     _scan_ra, y
      0083A6 CF 01 97         [ 2]  313     ldw     _scan_rb, x
      0083A9 35 C8 01 A6      [ 1]  314     mov     s_latch, #200
      0083AD 1C 00 05         [ 2]  315     addw    x, #5               ; GAPW[6]
      0083B0 CC 84 2D         [ 2]  316     jp      hi7
      0083B3                        317 rise7:
      0083B3 90 93            [ 1]  318     ldw     y, x
      0083B5 72 A2 00 05      [ 2]  319     subw    y, #5               ; GAP[6]
      0083B9 90 CF 01 95      [ 2]  320     ldw     _scan_ra, y
      0083BD CF 01 97         [ 2]  321     ldw     _scan_rb, x
      0083C0 35 C8 01 A6      [ 1]  322     mov     s_latch, #200
      0083C4 1C 00 09         [ 2]  323     addw    x, #9               ; GAPW[7]
      0083C7 CC 83 D2         [ 2]  324     jp      fetch_high
                                    325 
                                    326 ; ------------------------------------ high mode: octet fetch + fast path
      0083CA                        327 th_high:
      0083CA CC 85 39         [ 2]  328     jp      tail_high
                                    329 
                                    330 ; all-high octet: 8 samples skipped -- 4 cy documented
      0083CD                        331 fast_high:
      0083CD 1C 00 2A         [ 2]  332     addw    x, #42              ; t += LOOP_CY + W-sum(2)
      0083D0 20 00            [ 2]  333     jra     fetch_high
                                    334 
      0083D2                        335 fetch_high:
      0083D2 90 CE 01 A0      [ 2]  336     ldw     y, s_left
      0083D6 27 F2            [ 1]  337     jreq    th_high
      0083D8 90 5A            [ 2]  338     decw    y
      0083DA 90 CF 01 A0      [ 2]  339     ldw     s_left, y
      0083DE 90 CE 01 9E      [ 2]  340     ldw     y, s_ptr
      0083E2 90 F6            [ 1]  341     ld      a, (y)
      0083E4 90 5C            [ 1]  342     incw    y
      0083E6 90 CF 01 9E      [ 2]  343     ldw     s_ptr, y
      0083EA 48               [ 1]  344     sll     a
      0083EB 48               [ 1]  345     sll     a
      0083EC C7 01 A4         [ 1]  346     ld      s_oct, a
      0083EF 90 F6            [ 1]  347     ld      a, (y)
      0083F1 4E               [ 1]  348     swap    a
      0083F2 44               [ 1]  349     srl     a
      0083F3 44               [ 1]  350     srl     a
      0083F4 A4 03            [ 1]  351     and     a, #0x03
      0083F6 CA 01 A4         [ 1]  352     or      a, s_oct
      0083F9 A1 FF            [ 1]  353     cp      a, #0xFF
      0083FB 27 D0            [ 1]  354     jreq    fast_high
                                    355     ; fallthrough -> hi0
                                    356 
                                    357 ; ------------------------------------------------- high mode, slots 0..7
                                    358 ; per high sample: sll(1) jrnc(1) addw(2) = 4 cy documented
      0083FD                        359 hi0:
      0083FD 48               [ 1]  360     sll     a
      0083FE 24 36            [ 1]  361     jrnc    ft0
      008400 1C 00 04         [ 2]  362     addw    x, #4
      008403                        363 hi1:
      008403 48               [ 1]  364     sll     a
      008404 24 33            [ 1]  365     jrnc    ft1
      008406 1C 00 04         [ 2]  366     addw    x, #4
      008409                        367 hi2:
      008409 48               [ 1]  368     sll     a
      00840A 24 30            [ 1]  369     jrnc    ft2
      00840C 1C 00 04         [ 2]  370     addw    x, #4
      00840F                        371 hi3:
      00840F 48               [ 1]  372     sll     a
      008410 24 2D            [ 1]  373     jrnc    ft3
      008412 1C 00 06         [ 2]  374     addw    x, #6
      008415                        375 hi4:
      008415 48               [ 1]  376     sll     a
      008416 24 2A            [ 1]  377     jrnc    ft4
      008418 1C 00 04         [ 2]  378     addw    x, #4
      00841B                        379 hi5:
      00841B 48               [ 1]  380     sll     a
      00841C 24 27            [ 1]  381     jrnc    ft5
      00841E 1C 00 06         [ 2]  382     addw    x, #6
      008421 72 5D 01 A7      [ 1]  383     tnz     s_tail              ; tail octet ends after slot 5
      008425 26 27            [ 1]  384     jrne    eh_t
      008427                        385 hi6:
      008427 48               [ 1]  386     sll     a
      008428 24 1E            [ 1]  387     jrnc    ft6
      00842A 1C 00 05         [ 2]  388     addw    x, #5
      00842D                        389 hi7:
      00842D 48               [ 1]  390     sll     a
      00842E 24 1B            [ 1]  391     jrnc    ft7
      008430 1C 00 09         [ 2]  392     addw    x, #9
      008433 CC 83 D2         [ 2]  393     jp      fetch_high
                                    394 
                                    395 ; fall trampolines
      008436 CC 84 51         [ 2]  396 ft0: jp     fall0
      008439 CC 84 6A         [ 2]  397 ft1: jp     fall1
      00843C CC 84 83         [ 2]  398 ft2: jp     fall2
      00843F CC 84 9C         [ 2]  399 ft3: jp     fall3
      008442 CC 84 B5         [ 2]  400 ft4: jp     fall4
      008445 CC 84 CE         [ 2]  401 ft5: jp     fall5
      008448 CC 84 E7         [ 2]  402 ft6: jp     fall6
      00844B CC 85 00         [ 2]  403 ft7: jp     fall7
                                    404 
      00844E                        405 eh_t:
      00844E CC 85 4E         [ 2]  406     jp      end_high_tail
                                    407 
                                    408 ; ---------------------------------------------------------- fall sites
                                    409 ; sample at slot J is low, ending the pulse (high mode, C=0):
                                    410 ;   fa = t - GAPW[J-1], sfa = J-1 (previous sample was the last high),
                                    411 ;   fb = t, t += GAP[J], low_run = 1 (latch 199), save state, return 1.
                                    412 ;   ~22 cy documented incl. the shared epilogue
      008451                        413 fall0:
      008451 90 93            [ 1]  414     ldw     y, x
      008453 72 A2 00 09      [ 2]  415     subw    y, #9               ; GAPW[7]
      008457 90 CF 01 99      [ 2]  416     ldw     _scan_fa, y
      00845B CF 01 9B         [ 2]  417     ldw     _scan_fb, x
      00845E 35 07 01 9D      [ 1]  418     mov     _scan_sfa, #7
      008462 1C 00 04         [ 2]  419     addw    x, #4               ; GAP[0]
      008465 4B 01            [ 1]  420     push    #1                  ; resume at low1
      008467 CC 85 19         [ 2]  421     jp      fall_common
      00846A                        422 fall1:
      00846A 90 93            [ 1]  423     ldw     y, x
      00846C 72 A2 00 04      [ 2]  424     subw    y, #4               ; GAPW[0]
      008470 90 CF 01 99      [ 2]  425     ldw     _scan_fa, y
      008474 CF 01 9B         [ 2]  426     ldw     _scan_fb, x
      008477 35 00 01 9D      [ 1]  427     mov     _scan_sfa, #0
      00847B 1C 00 05         [ 2]  428     addw    x, #5               ; GAP[1]
      00847E 4B 02            [ 1]  429     push    #2
      008480 CC 85 19         [ 2]  430     jp      fall_common
      008483                        431 fall2:
      008483 90 93            [ 1]  432     ldw     y, x
      008485 72 A2 00 04      [ 2]  433     subw    y, #4               ; GAPW[1]
      008489 90 CF 01 99      [ 2]  434     ldw     _scan_fa, y
      00848D CF 01 9B         [ 2]  435     ldw     _scan_fb, x
      008490 35 01 01 9D      [ 1]  436     mov     _scan_sfa, #1
      008494 1C 00 04         [ 2]  437     addw    x, #4               ; GAP[2]
      008497 4B 03            [ 1]  438     push    #3
      008499 CC 85 19         [ 2]  439     jp      fall_common
      00849C                        440 fall3:
      00849C 90 93            [ 1]  441     ldw     y, x
      00849E 72 A2 00 04      [ 2]  442     subw    y, #4               ; GAPW[2]
      0084A2 90 CF 01 99      [ 2]  443     ldw     _scan_fa, y
      0084A6 CF 01 9B         [ 2]  444     ldw     _scan_fb, x
      0084A9 35 02 01 9D      [ 1]  445     mov     _scan_sfa, #2
      0084AD 1C 00 04         [ 2]  446     addw    x, #4               ; GAP[3]
      0084B0 4B 04            [ 1]  447     push    #4
      0084B2 CC 85 19         [ 2]  448     jp      fall_common
      0084B5                        449 fall4:
      0084B5 90 93            [ 1]  450     ldw     y, x
      0084B7 72 A2 00 06      [ 2]  451     subw    y, #6               ; GAPW[3]
      0084BB 90 CF 01 99      [ 2]  452     ldw     _scan_fa, y
      0084BF CF 01 9B         [ 2]  453     ldw     _scan_fb, x
      0084C2 35 03 01 9D      [ 1]  454     mov     _scan_sfa, #3
      0084C6 1C 00 04         [ 2]  455     addw    x, #4               ; GAP[4]
      0084C9 4B 05            [ 1]  456     push    #5
      0084CB CC 85 19         [ 2]  457     jp      fall_common
      0084CE                        458 fall5:
      0084CE 90 93            [ 1]  459     ldw     y, x
      0084D0 72 A2 00 04      [ 2]  460     subw    y, #4               ; GAPW[4]
      0084D4 90 CF 01 99      [ 2]  461     ldw     _scan_fa, y
      0084D8 CF 01 9B         [ 2]  462     ldw     _scan_fb, x
      0084DB 35 04 01 9D      [ 1]  463     mov     _scan_sfa, #4
      0084DF 1C 00 06         [ 2]  464     addw    x, #6               ; GAP[5]
      0084E2 4B 06            [ 1]  465     push    #6
      0084E4 CC 85 19         [ 2]  466     jp      fall_common
      0084E7                        467 fall6:
      0084E7 90 93            [ 1]  468     ldw     y, x
      0084E9 72 A2 00 06      [ 2]  469     subw    y, #6               ; GAPW[5]
      0084ED 90 CF 01 99      [ 2]  470     ldw     _scan_fa, y
      0084F1 CF 01 9B         [ 2]  471     ldw     _scan_fb, x
      0084F4 35 05 01 9D      [ 1]  472     mov     _scan_sfa, #5
      0084F8 1C 00 05         [ 2]  473     addw    x, #5               ; GAP[6]
      0084FB 4B 07            [ 1]  474     push    #7
      0084FD CC 85 19         [ 2]  475     jp      fall_common
      008500                        476 fall7:
      008500 90 93            [ 1]  477     ldw     y, x
      008502 72 A2 00 05      [ 2]  478     subw    y, #5               ; GAPW[6]
      008506 90 CF 01 99      [ 2]  479     ldw     _scan_fa, y
      00850A CF 01 9B         [ 2]  480     ldw     _scan_fb, x
      00850D 35 06 01 9D      [ 1]  481     mov     _scan_sfa, #6
      008511 1C 00 08         [ 2]  482     addw    x, #8               ; GAP[7]
      008514 4B 00            [ 1]  483     push    #0                  ; slot 7 resumes at the next octet fetch
      008516 CC 85 19         [ 2]  484     jp      fall_common
                                    485 
      008519                        486 fall_common:                    ; stack: resume index; A = octet, X = t
      008519 C7 01 A4         [ 1]  487     ld      s_oct, a
      00851C CF 01 A2         [ 2]  488     ldw     s_t, x
      00851F 35 C7 01 A6      [ 1]  489     mov     s_latch, #199       ; the fall sample itself counts (low_run=1)
      008523 84               [ 1]  490     pop     a
      008524 C7 01 A5         [ 1]  491     ld      s_res, a
      008527 A6 01            [ 1]  492     ld      a, #1
      008529 81               [ 4]  493     ret
                                    494 
                                    495 ; ------------------------------------------------------- 6-bit tail octet
                                    496 ; loop len-1 has no following byte: only R0..R5 exist (harness linearize
                                    497 ; drops BS0/BS1 of the last loop).  In practice the latch fires ~100
                                    498 ; loops earlier; this path exists for bit-exactness on arbitrary input.
      00852A                        499 tail_low:
      00852A 90 CE 01 9E      [ 2]  500     ldw     y, s_ptr
      00852E 90 F6            [ 1]  501     ld      a, (y)
      008530 48               [ 1]  502     sll     a
      008531 48               [ 1]  503     sll     a
      008532 35 01 01 A7      [ 1]  504     mov     s_tail, #1
      008536 CC 82 84         [ 2]  505     jp      low0
                                    506 
      008539                        507 tail_high:
      008539 90 CE 01 9E      [ 2]  508     ldw     y, s_ptr
      00853D 90 F6            [ 1]  509     ld      a, (y)
      00853F 48               [ 1]  510     sll     a
      008540 48               [ 1]  511     sll     a
      008541 35 01 01 A7      [ 1]  512     mov     s_tail, #1
      008545 CC 83 FD         [ 2]  513     jp      hi0
                                    514 
      008548                        515 end_low_tail:                   ; data exhausted, no pulse pending
      008548 35 08 01 A5      [ 1]  516     mov     s_res, #8
      00854C 4F               [ 1]  517     clr     a
      00854D 81               [ 4]  518     ret
                                    519 
      00854E                        520 end_high_tail:                  ; data exhausted mid-pulse: final pulse,
      00854E 90 93            [ 1]  521     ldw     y, x                ; fb = fa + FIRST_BR (4)
      008550 72 A2 00 06      [ 2]  522     subw    y, #6               ; GAPW[5]: X is past tail slot 5
      008554 90 CF 01 99      [ 2]  523     ldw     _scan_fa, y
      008558 72 A9 00 04      [ 2]  524     addw    y, #4
      00855C 90 CF 01 9B      [ 2]  525     ldw     _scan_fb, y
      008560 35 05 01 9D      [ 1]  526     mov     _scan_sfa, #5
      008564 35 08 01 A5      [ 1]  527     mov     s_res, #8
      008568 A6 01            [ 1]  528     ld      a, #1
      00856A 81               [ 4]  529     ret
                                    530 
                                    531 ; ======================================================================
                                    532 ; _cap_capture -- 256-loop WS2812 oversampling capture.
                                    533 ; Instruction-for-instruction identical to cap_code.s (the fitted sampler
                                    534 ; model is calibrated to THIS exact loop; any edit invalidates W_CY[] --
                                    535 ; EMBEDDED_V2_SPEC.md SS14 risk 7) except the loop count: 256 loops ->
                                    536 ; 256 bytes = 2048 samples = 592 us nominal, sized for the 216-bit v2.1
                                    537 ; test frame (117.7 loops at +8% incl. slack, spec SS3) plus the 200-low
                                    538 ; latch tail (25 loops) with >5x margin.
                                    539 ;
                                    540 ; ALIGNMENT IS PART OF THE FITTED MODEL (measured on this bench,
                                    541 ; 2026-09-06): the loop's real timing includes flash-fetch stalls that
                                    542 ; depend on the code's address phase.  capture.ihx (the image the
                                    543 ; 40-cycle model was fitted against) has _cap_code at 0x8111; linking
                                    544 ; this routine as ordinary relocatable CODE landed it at 0x9E1E (phase 0
                                    545 ; mod 4 instead of 1) and every bench decode then measured eps at
                                    546 ; +6.2..+7.5% instead of this unit's -1.07% -- i.e. at that phase the
                                    547 ; loop really runs ~37 cycles, the DOCUMENTED count, with no stalls.
                                    548 ; 0.9893 * 40/37 - 1 = +6.95%: the observed shift, exactly.  So the
                                    549 ; routine lives in an ABS area at 0x9FA1 = 0x8111 (mod 16), restoring
                                    550 ; the fitted stall pattern.  The Makefile guards against CODE growing
                                    551 ; into it (sdld does not check REL/ABS overlaps).
                                    552 ; Entry: X = capture buffer pointer.  Clobbers: A, X, Y, C.
                                    553 ; ======================================================================
                                    554     .area CAPLOOP (ABS)
      009FA1                        555     .org 0x9FA1
      009FA1                        556 _cap_capture:
      009FA1 90 AE 01 00      [ 2]  557     ldw     y, #256
                                    558 
      009FA5                        559 00010$:                             ; wait_low
      009FA5 72 06 50 0B FB   [ 2]  560     btjt    0x500B, #3, 00010$
      009FAA                        561 00011$:                             ; wait_high
      009FAA 72 07 50 0B FB   [ 2]  562     btjf    0x500B, #3, 00011$
                                    563 
      009FAF                        564 _cap_loop:                          ; sampling loop, address-phase pinned:
      009FAF                        565 00012$:                             ; MUST stay == 0x811F (mod 16); label
                                    566                                     ; adds no bytes -- cap_byte
      009FAF 49               [ 1]  567     rlc     a                       ; deposit BS1 from C (prev boundary)
                                    568 
      009FB0 72 06 50 0B 01   [ 2]  569     btjt    0x500B, #3, 00013$      ; R0
      009FB5 9D               [ 1]  570     nop
      009FB6 49               [ 1]  571 00013$: rlc     a
                                    572 
      009FB7 72 06 50 0B 01   [ 2]  573     btjt    0x500B, #3, 00014$      ; R1
      009FBC 9D               [ 1]  574     nop
      009FBD 49               [ 1]  575 00014$: rlc     a
                                    576 
      009FBE 72 06 50 0B 01   [ 2]  577     btjt    0x500B, #3, 00015$      ; R2
      009FC3 9D               [ 1]  578     nop
      009FC4 49               [ 1]  579 00015$: rlc     a
                                    580 
      009FC5 72 06 50 0B 01   [ 2]  581     btjt    0x500B, #3, 00016$      ; R3
      009FCA 9D               [ 1]  582     nop
      009FCB 49               [ 1]  583 00016$: rlc     a
                                    584 
      009FCC 72 06 50 0B 01   [ 2]  585     btjt    0x500B, #3, 00017$      ; R4
      009FD1 9D               [ 1]  586     nop
      009FD2 49               [ 1]  587 00017$: rlc     a
                                    588 
      009FD3 72 06 50 0B 01   [ 2]  589     btjt    0x500B, #3, 00018$      ; R5
      009FD8 9D               [ 1]  590     nop
      009FD9 49               [ 1]  591 00018$: rlc     a
                                    592 
      009FDA F7               [ 1]  593     ld      (x), a                  ; store byte
      009FDB 5C               [ 1]  594     incw    x
                                    595 
      009FDC 72 06 50 0B 01   [ 2]  596     btjt    0x500B, #3, 00019$      ; BS0
      009FE1 9D               [ 1]  597     nop
      009FE2 49               [ 1]  598 00019$: rlc     a
                                    599 
      009FE3 90 5A            [ 2]  600     decw    y                       ; loop counter (sets Z)
                                    601 
      009FE5 72 06 50 0B 01   [ 2]  602     btjt    0x500B, #3, 00020$      ; BS1 -- C only, Z preserved
      009FEA 9D               [ 1]  603     nop
      009FEB                        604 00020$:
                                    605 
      009FEB 26 C2            [ 1]  606     jrne    00012$                  ; loop (tests Z from decw)
                                    607 
      009FED 9A               [ 1]  608     rim                             ; post-loop: timing-irrelevant.  For a
      009FEE A6 01            [ 1]  609     ld      a, #1                   ; _cap_arm entry this re-enables the
      009FF0 81               [ 4]  610     ret                             ; tick and flags "captured" (A=1);
                                    611                                     ; harmless for the legacy bench entry
                                    612                                     ; (no interrupt sources enabled there)
