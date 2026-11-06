                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module decode
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _scan_next
                                     11 	.globl _scan_init
                                     12 	.globl _dec_info
                                     13 	.globl _scan_sfa
                                     14 	.globl _scan_fb
                                     15 	.globl _scan_fa
                                     16 	.globl _scan_rb
                                     17 	.globl _scan_ra
                                     18 	.globl _scan_len
                                     19 	.globl _scan_cap
                                     20 	.globl _ws_decode_ex
                                     21 	.globl _dec_eps_centi
                                     22 ;--------------------------------------------------------
                                     23 ; ram data
                                     24 ;--------------------------------------------------------
                                     25 	.area DATA
      000001                         26 _scan_cap::
      000001                         27 	.ds 2
      000003                         28 _scan_len::
      000003                         29 	.ds 2
      000005                         30 _scan_ra::
      000005                         31 	.ds 2
      000007                         32 _scan_rb::
      000007                         33 	.ds 2
      000009                         34 _scan_fa::
      000009                         35 	.ds 2
      00000B                         36 _scan_fb::
      00000B                         37 	.ds 2
      00000D                         38 _scan_sfa::
      00000D                         39 	.ds 1
      00000E                         40 _ps:
      00000E                         41 	.ds 22
      000024                         42 _dec_info::
      000024                         43 	.ds 20
      000038                         44 _g_K:
      000038                         45 	.ds 2
      00003A                         46 _g_tau:
      00003A                         47 	.ds 2
      00003C                         48 _c_lo:
      00003C                         49 	.ds 4
      000040                         50 _c_hi:
      000040                         51 	.ds 4
      000044                         52 _c_n:
      000044                         53 	.ds 2
      000046                         54 _c_h0c:
      000046                         55 	.ds 2
      000048                         56 _c_h1c:
      000048                         57 	.ds 2
      00004A                         58 _c_d56:
      00004A                         59 	.ds 2
      00004C                         60 _c_hist:
      00004C                         61 	.ds 128
      0000CC                         62 _c_labx0:
      0000CC                         63 	.ds 4
      0000D0                         64 _c_labx1:
      0000D0                         65 	.ds 4
      0000D4                         66 _c_labx0b:
      0000D4                         67 	.ds 4
      0000D8                         68 _c_labx1b:
      0000D8                         69 	.ds 4
      0000DC                         70 _c_c0:
      0000DC                         71 	.ds 4
      0000E0                         72 _c_gap56:
      0000E0                         73 	.ds 4
      0000E4                         74 _d_bits:
      0000E4                         75 	.ds 24
      0000FC                         76 _d_infeas:
      0000FC                         77 	.ds 2
      0000FE                         78 _d_laberr:
      0000FE                         79 	.ds 2
      000100                         80 _d_nseg:
      000100                         81 	.ds 2
      000102                         82 _d_costs:
      000102                         83 	.ds 32
      000122                         84 _d_inter:
      000122                         85 	.ds 2
      000124                         86 _v_cand_t:
      000124                         87 	.ds 10
      00012E                         88 _v_cand_m:
      00012E                         89 	.ds 5
      000133                         90 _v_ncand:
      000133                         91 	.ds 1
      000134                         92 _v_nweak:
      000134                         93 	.ds 2
      000136                         94 _v_ntied:
      000136                         95 	.ds 2
      000138                         96 _v_tiepend:
      000138                         97 	.ds 2
      00013A                         98 _d_pp:
      00013A                         99 	.ds 16
      00014A                        100 _ss:
      00014A                        101 	.ds 20
                                    102 ;--------------------------------------------------------
                                    103 ; ram data
                                    104 ;--------------------------------------------------------
                                    105 	.area INITIALIZED
                                    106 ;--------------------------------------------------------
                                    107 ; absolute external ram data
                                    108 ;--------------------------------------------------------
                                    109 	.area DABS (ABS)
                                    110 
                                    111 ; default segment ordering for linker
                                    112 	.area HOME
                                    113 	.area GSINIT
                                    114 	.area GSFINAL
                                    115 	.area CONST
                                    116 	.area INITIALIZER
                                    117 	.area CODE
                                    118 
                                    119 ;--------------------------------------------------------
                                    120 ; global & static initialisations
                                    121 ;--------------------------------------------------------
                                    122 	.area HOME
                                    123 	.area GSINIT
                                    124 	.area GSFINAL
                                    125 	.area GSINIT
                                    126 ;--------------------------------------------------------
                                    127 ; Home
                                    128 ;--------------------------------------------------------
                                    129 	.area HOME
                                    130 	.area HOME
                                    131 ;--------------------------------------------------------
                                    132 ; code
                                    133 ;--------------------------------------------------------
                                    134 	.area CODE
                                    135 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 127: static int8_t known_bit(uint16_t t)
                                    136 ;	-----------------------------------------
                                    137 ;	 function known_bit
                                    138 ;	-----------------------------------------
      008147                        139 _known_bit:
      008147 88               [ 1]  140 	push	a
                                    141 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 129: if (t < 32)
      008148 90 93            [ 1]  142 	ldw	y, x
      00814A A3 00 20         [ 2]  143 	cpw	x, #0x0020
      00814D 24 20            [ 1]  144 	jrnc	00102$
                                    145 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 130: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
      00814F 93               [ 1]  146 	ldw	x, y
      008150 54               [ 2]  147 	srlw	x
      008151 54               [ 2]  148 	srlw	x
      008152 54               [ 2]  149 	srlw	x
      008153 1C 80 2D         [ 2]  150 	addw	x, #(_HDR+0)
      008156 F6               [ 1]  151 	ld	a, (x)
      008157 97               [ 1]  152 	ld	xl, a
      008158 90 9F            [ 1]  153 	ld	a, yl
      00815A A4 07            [ 1]  154 	and	a, #0x07
      00815C 6B 01            [ 1]  155 	ld	(0x01, sp), a
      00815E A6 07            [ 1]  156 	ld	a, #0x07
      008160 10 01            [ 1]  157 	sub	a, (0x01, sp)
      008162 27 06            [ 1]  158 	jreq	00125$
      008164                        159 00124$:
      008164 41               [ 1]  160 	exg	a, xl
      008165 44               [ 1]  161 	srl	a
      008166 41               [ 1]  162 	exg	a, xl
      008167 4A               [ 1]  163 	dec	a
      008168 26 FA            [ 1]  164 	jrne	00124$
      00816A                        165 00125$:
      00816A 9F               [ 1]  166 	ld	a, xl
      00816B A4 01            [ 1]  167 	and	a, #0x01
      00816D 20 2B            [ 2]  168 	jra	00105$
      00816F                        169 00102$:
                                    170 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 131: if (t >= NB - 32) {
      00816F 90 A3 00 A0      [ 2]  171 	cpw	y, #0x00a0
      008173 25 23            [ 1]  172 	jrc	00104$
                                    173 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 132: uint16_t u = t - (NB - 32);
      008175 1D 00 A0         [ 2]  174 	subw	x, #0x00a0
                                    175 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 133: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
      008178 90 93            [ 1]  176 	ldw	y, x
      00817A 54               [ 2]  177 	srlw	x
      00817B 54               [ 2]  178 	srlw	x
      00817C 54               [ 2]  179 	srlw	x
      00817D 1C 80 31         [ 2]  180 	addw	x, #(_TRL+0)
      008180 F6               [ 1]  181 	ld	a, (x)
      008181 97               [ 1]  182 	ld	xl, a
      008182 90 9F            [ 1]  183 	ld	a, yl
      008184 A4 07            [ 1]  184 	and	a, #0x07
      008186 6B 01            [ 1]  185 	ld	(0x01, sp), a
      008188 A6 07            [ 1]  186 	ld	a, #0x07
      00818A 10 01            [ 1]  187 	sub	a, (0x01, sp)
      00818C 27 06            [ 1]  188 	jreq	00128$
      00818E                        189 00127$:
      00818E 41               [ 1]  190 	exg	a, xl
      00818F 44               [ 1]  191 	srl	a
      008190 41               [ 1]  192 	exg	a, xl
      008191 4A               [ 1]  193 	dec	a
      008192 26 FA            [ 1]  194 	jrne	00127$
      008194                        195 00128$:
      008194 9F               [ 1]  196 	ld	a, xl
      008195 A4 01            [ 1]  197 	and	a, #0x01
                                    198 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 135: return -1;
      008197 C5                     199 	.byte 0xc5
      008198                        200 00104$:
      008198 A6 FF            [ 1]  201 	ld	a, #0xff
      00819A                        202 00105$:
                                    203 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 136: }
      00819A 5B 01            [ 2]  204 	addw	sp, #1
      00819C 81               [ 4]  205 	ret
                                    206 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 174: void scan_init(void)
                                    207 ;	-----------------------------------------
                                    208 ;	 function scan_init
                                    209 ;	-----------------------------------------
      00819D                        210 _scan_init:
                                    211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 176: ps.i = 0; ps.s = 0; ps.tbase = 0; ps.wsum = 0;
      00819D AE 00 0E         [ 2]  212 	ldw	x, #(_ps+0)
      0081A0 6F 01            [ 1]  213 	clr	(0x1, x)
      0081A2 7F               [ 1]  214 	clr	(x)
      0081A3 35 00 00 10      [ 1]  215 	mov	_ps+2, #0x00
      0081A7 AE 00 11         [ 2]  216 	ldw	x, #(_ps+3)
      0081AA 6F 01            [ 1]  217 	clr	(0x1, x)
      0081AC 7F               [ 1]  218 	clr	(x)
      0081AD AE 00 13         [ 2]  219 	ldw	x, #(_ps+5)
      0081B0 6F 01            [ 1]  220 	clr	(0x1, x)
      0081B2 7F               [ 1]  221 	clr	(x)
                                    222 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 177: ps.t_prev = 0; ps.have_prev = 0;
      0081B3 AE 00 15         [ 2]  223 	ldw	x, #(_ps+7)
      0081B6 6F 01            [ 1]  224 	clr	(0x1, x)
      0081B8 7F               [ 1]  225 	clr	(x)
      0081B9 35 00 00 17      [ 1]  226 	mov	_ps+9, #0x00
                                    227 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 178: ps.in_pulse = 0; ps.seen = 0; ps.done = 0; ps.low_run = 0;
      0081BD 35 00 00 18      [ 1]  228 	mov	_ps+10, #0x00
      0081C1 35 00 00 19      [ 1]  229 	mov	_ps+11, #0x00
      0081C5 35 00 00 1A      [ 1]  230 	mov	_ps+12, #0x00
      0081C9 AE 00 1B         [ 2]  231 	ldw	x, #(_ps+13)
      0081CC 6F 01            [ 1]  232 	clr	(0x1, x)
      0081CE 7F               [ 1]  233 	clr	(x)
                                    234 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 179: ps.ra = ps.rb = ps.fa = 0; ps.sfa = 0;
      0081CF AE 00 21         [ 2]  235 	ldw	x, #(_ps+19)
      0081D2 6F 01            [ 1]  236 	clr	(0x1, x)
      0081D4 7F               [ 1]  237 	clr	(x)
      0081D5 AE 00 1F         [ 2]  238 	ldw	x, #(_ps+17)
      0081D8 6F 01            [ 1]  239 	clr	(0x1, x)
      0081DA 7F               [ 1]  240 	clr	(x)
      0081DB AE 00 1D         [ 2]  241 	ldw	x, #(_ps+15)
      0081DE 6F 01            [ 1]  242 	clr	(0x1, x)
      0081E0 7F               [ 1]  243 	clr	(x)
      0081E1 35 00 00 23      [ 1]  244 	mov	_ps+21, #0x00
                                    245 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 180: }
      0081E5 81               [ 4]  246 	ret
                                    247 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 183: uint8_t scan_next(void)
                                    248 ;	-----------------------------------------
                                    249 ;	 function scan_next
                                    250 ;	-----------------------------------------
      0081E6                        251 _scan_next:
      0081E6 52 08            [ 2]  252 	sub	sp, #8
                                    253 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
      0081E8                        254 00133$:
                                    255 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
                                    256 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
                                    257 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
                                    258 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
                                    259 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
      0081E8 C6 00 1A         [ 1]  260 	ld	a, _ps+12
      0081EB 27 03            [ 1]  261 	jreq	00320$
      0081ED CC 84 2E         [ 2]  262 	jp	00135$
      0081F0                        263 00320$:
                                    264 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 186: uint8_t v, s = ps.s;
      0081F0 C6 00 10         [ 1]  265 	ld	a, _ps+2
      0081F3 6B 01            [ 1]  266 	ld	(0x01, sp), a
                                    267 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 188: if (ps.i >= scan_len) break;
      0081F5 AE 00 0E         [ 2]  268 	ldw	x, #(_ps+0)
      0081F8 1F 02            [ 2]  269 	ldw	(0x02, sp), x
      0081FA FE               [ 2]  270 	ldw	x, (x)
      0081FB 1F 04            [ 2]  271 	ldw	(0x04, sp), x
      0081FD C3 00 03         [ 2]  272 	cpw	x, _scan_len+0
      008200 25 03            [ 1]  273 	jrc	00321$
      008202 CC 84 2E         [ 2]  274 	jp	00135$
      008205                        275 00321$:
                                    276 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
                                    277 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
                                    278 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
      008205 1E 04            [ 2]  279 	ldw	x, (0x04, sp)
      008207 5C               [ 1]  280 	incw	x
      008208 90 93            [ 1]  281 	ldw	y, x
                                    282 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
      00820A 72 BB 00 01      [ 2]  283 	addw	x, _scan_cap+0
      00820E 1F 06            [ 2]  284 	ldw	(0x06, sp), x
                                    285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
      008210 90 C3 00 03      [ 2]  286 	cpw	y, _scan_len+0
      008214 4F               [ 1]  287 	clr	a
      008215 49               [ 1]  288 	rlc	a
      008216 6B 08            [ 1]  289 	ld	(0x08, sp), a
      008218 7B 01            [ 1]  290 	ld	a, (0x01, sp)
      00821A A1 06            [ 1]  291 	cp	a, #0x06
      00821C 27 03            [ 1]  292 	jreq	00324$
      00821E CC 82 CD         [ 2]  293 	jp	00113$
      008221                        294 00324$:
      008221 0D 08            [ 1]  295 	tnz	(0x08, sp)
      008223 26 03            [ 1]  296 	jrne	00325$
      008225 CC 82 CD         [ 2]  297 	jp	00113$
      008228                        298 00325$:
                                    299 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
      008228 1E 06            [ 2]  300 	ldw	x, (0x06, sp)
      00822A F6               [ 1]  301 	ld	a, (x)
      00822B 97               [ 1]  302 	ld	xl, a
                                    303 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 191: if (bt == 0x00 && !ps.in_pulse) {
      00822C 4D               [ 1]  304 	tnz	a
      00822D 26 4F            [ 1]  305 	jrne	00107$
      00822F C6 00 18         [ 1]  306 	ld	a, _ps+10
      008232 26 4A            [ 1]  307 	jrne	00107$
                                    308 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
      008234 CE 00 11         [ 2]  309 	ldw	x, _ps+3
      008237 1C 00 3D         [ 2]  310 	addw	x, #0x003d
      00823A 90 CE 00 13      [ 2]  311 	ldw	y, _ps+5
      00823E 17 07            [ 2]  312 	ldw	(0x07, sp), y
      008240 72 FB 07         [ 2]  313 	addw	x, (0x07, sp)
      008243 CF 00 15         [ 2]  314 	ldw	_ps+7, x
                                    315 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 194: ps.have_prev = 1;
      008246 35 01 00 17      [ 1]  316 	mov	_ps+9, #0x01
                                    317 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
      00824A CE 00 1B         [ 2]  318 	ldw	x, _ps+13
      00824D 1C 00 08         [ 2]  319 	addw	x, #0x0008
      008250 CF 00 1B         [ 2]  320 	ldw	_ps+13, x
                                    321 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 196: ps.i++; ps.tbase += LOOP_CY;        /* s stays 6 */
      008253 1E 02            [ 2]  322 	ldw	x, (0x02, sp)
      008255 FE               [ 2]  323 	ldw	x, (x)
      008256 5C               [ 1]  324 	incw	x
      008257 16 02            [ 2]  325 	ldw	y, (0x02, sp)
      008259 90 FF            [ 2]  326 	ldw	(y), x
      00825B CE 00 11         [ 2]  327 	ldw	x, _ps+3
      00825E 1C 00 28         [ 2]  328 	addw	x, #0x0028
      008261 CF 00 11         [ 2]  329 	ldw	_ps+3, x
                                    330 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 197: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
      008264 C6 00 19         [ 1]  331 	ld	a, _ps+11
      008267 26 03            [ 1]  332 	jrne	00328$
      008269 CC 81 E8         [ 2]  333 	jp	00133$
      00826C                        334 00328$:
      00826C CE 00 1B         [ 2]  335 	ldw	x, _ps+13
      00826F A3 00 C8         [ 2]  336 	cpw	x, #0x00c8
      008272 24 03            [ 1]  337 	jrnc	00329$
      008274 CC 81 E8         [ 2]  338 	jp	00133$
      008277                        339 00329$:
      008277 35 01 00 1A      [ 1]  340 	mov	_ps+12, #0x01
      00827B CC 84 2E         [ 2]  341 	jp	00135$
                                    342 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 198: continue;
      00827E                        343 00107$:
                                    344 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 200: if (bt == 0xFF && ps.in_pulse) {
      00827E 9F               [ 1]  345 	ld	a, xl
      00827F 4C               [ 1]  346 	inc	a
      008280 26 4B            [ 1]  347 	jrne	00113$
      008282 C6 00 18         [ 1]  348 	ld	a, _ps+10
      008285 27 46            [ 1]  349 	jreq	00113$
                                    350 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
      008287 90 CE 00 11      [ 2]  351 	ldw	y, _ps+3
      00828B CE 00 13         [ 2]  352 	ldw	x, _ps+5
      00828E 1C 00 3F         [ 2]  353 	addw	x, #0x003f
      008291 17 07            [ 2]  354 	ldw	(0x07, sp), y
      008293 72 FB 07         [ 2]  355 	addw	x, (0x07, sp)
      008296 CF 00 21         [ 2]  356 	ldw	_ps+19, x
                                    357 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 203: ps.wsum += 2;               /* sum of W over the octet */
      008299 CE 00 13         [ 2]  358 	ldw	x, _ps+5
      00829C 5C               [ 1]  359 	incw	x
      00829D 5C               [ 1]  360 	incw	x
      00829E CF 00 13         [ 2]  361 	ldw	_ps+5, x
                                    362 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
      0082A1 35 05 00 23      [ 1]  363 	mov	_ps+21, #0x05
                                    364 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 205: ps.low_run = 0;
      0082A5 AE 00 1B         [ 2]  365 	ldw	x, #(_ps+13)
      0082A8 6F 01            [ 1]  366 	clr	(0x1, x)
      0082AA 7F               [ 1]  367 	clr	(x)
                                    368 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 206: ps.seen = 1;
      0082AB 35 01 00 19      [ 1]  369 	mov	_ps+11, #0x01
                                    370 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 207: ps.t_prev = ps.fa;
      0082AF CE 00 21         [ 2]  371 	ldw	x, _ps+19
      0082B2 CF 00 15         [ 2]  372 	ldw	_ps+7, x
                                    373 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 208: ps.have_prev = 1;
      0082B5 35 01 00 17      [ 1]  374 	mov	_ps+9, #0x01
                                    375 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 209: ps.i++; ps.tbase += LOOP_CY;
      0082B9 1E 02            [ 2]  376 	ldw	x, (0x02, sp)
      0082BB FE               [ 2]  377 	ldw	x, (x)
      0082BC 5C               [ 1]  378 	incw	x
      0082BD 16 02            [ 2]  379 	ldw	y, (0x02, sp)
      0082BF 90 FF            [ 2]  380 	ldw	(y), x
      0082C1 CE 00 11         [ 2]  381 	ldw	x, _ps+3
      0082C4 1C 00 28         [ 2]  382 	addw	x, #0x0028
      0082C7 CF 00 11         [ 2]  383 	ldw	_ps+3, x
                                    384 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 210: continue;
      0082CA CC 81 E8         [ 2]  385 	jp	00133$
      0082CD                        386 00113$:
                                    387 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 213: if (s < 6) {
      0082CD 7B 01            [ 1]  388 	ld	a, (0x01, sp)
      0082CF A1 06            [ 1]  389 	cp	a, #0x06
      0082D1 24 1B            [ 1]  390 	jrnc	00118$
                                    391 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 214: v = (uint8_t)((scan_cap[ps.i] >> (5 - s)) & 1);
      0082D3 CE 00 01         [ 2]  392 	ldw	x, _scan_cap+0
      0082D6 72 FB 04         [ 2]  393 	addw	x, (0x04, sp)
      0082D9 F6               [ 1]  394 	ld	a, (x)
      0082DA 97               [ 1]  395 	ld	xl, a
      0082DB A6 05            [ 1]  396 	ld	a, #0x05
      0082DD 10 01            [ 1]  397 	sub	a, (0x01, sp)
      0082DF 27 06            [ 1]  398 	jreq	00336$
      0082E1                        399 00335$:
      0082E1 41               [ 1]  400 	exg	a, xl
      0082E2 44               [ 1]  401 	srl	a
      0082E3 41               [ 1]  402 	exg	a, xl
      0082E4 4A               [ 1]  403 	dec	a
      0082E5 26 FA            [ 1]  404 	jrne	00335$
      0082E7                        405 00336$:
      0082E7 9F               [ 1]  406 	ld	a, xl
      0082E8 A4 01            [ 1]  407 	and	a, #0x01
      0082EA 6B 04            [ 1]  408 	ld	(0x04, sp), a
      0082EC 20 36            [ 2]  409 	jra	00119$
      0082EE                        410 00118$:
                                    411 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 216: if (ps.i + 1 >= scan_len) {     /* last loop: BS lost */
      0082EE 7B 08            [ 1]  412 	ld	a, (0x08, sp)
      0082F0 26 17            [ 1]  413 	jrne	00116$
                                    414 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 217: ps.i++; ps.s = 0; ps.tbase += LOOP_CY;
      0082F2 1E 04            [ 2]  415 	ldw	x, (0x04, sp)
      0082F4 5C               [ 1]  416 	incw	x
      0082F5 16 02            [ 2]  417 	ldw	y, (0x02, sp)
      0082F7 90 FF            [ 2]  418 	ldw	(y), x
      0082F9 35 00 00 10      [ 1]  419 	mov	_ps+2, #0x00
      0082FD CE 00 11         [ 2]  420 	ldw	x, _ps+3
      008300 1C 00 28         [ 2]  421 	addw	x, #0x0028
      008303 CF 00 11         [ 2]  422 	ldw	_ps+3, x
                                    423 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 218: continue;
      008306 CC 81 E8         [ 2]  424 	jp	00133$
      008309                        425 00116$:
                                    426 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 220: v = (uint8_t)((scan_cap[ps.i + 1] >> (7 - (s - 6))) & 1);
      008309 1E 06            [ 2]  427 	ldw	x, (0x06, sp)
      00830B F6               [ 1]  428 	ld	a, (x)
      00830C 97               [ 1]  429 	ld	xl, a
      00830D 7B 01            [ 1]  430 	ld	a, (0x01, sp)
      00830F A0 06            [ 1]  431 	sub	a, #0x06
      008311 6B 08            [ 1]  432 	ld	(0x08, sp), a
      008313 A6 07            [ 1]  433 	ld	a, #0x07
      008315 10 08            [ 1]  434 	sub	a, (0x08, sp)
      008317 27 06            [ 1]  435 	jreq	00339$
      008319                        436 00338$:
      008319 41               [ 1]  437 	exg	a, xl
      00831A 44               [ 1]  438 	srl	a
      00831B 41               [ 1]  439 	exg	a, xl
      00831C 4A               [ 1]  440 	dec	a
      00831D 26 FA            [ 1]  441 	jrne	00338$
      00831F                        442 00339$:
      00831F 9F               [ 1]  443 	ld	a, xl
      008320 A4 01            [ 1]  444 	and	a, #0x01
      008322 6B 04            [ 1]  445 	ld	(0x04, sp), a
      008324                        446 00119$:
                                    447 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 222: t = (uint16_t)(ps.tbase + O_CY[s] + ps.wsum);
      008324 90 CE 00 11      [ 2]  448 	ldw	y, _ps+3
      008328 5F               [ 1]  449 	clrw	x
      008329 7B 01            [ 1]  450 	ld	a, (0x01, sp)
      00832B 97               [ 1]  451 	ld	xl, a
      00832C D6 80 35         [ 1]  452 	ld	a, (_O_CY+0, x)
      00832F 6B 08            [ 1]  453 	ld	(0x08, sp), a
      008331 0F 07            [ 1]  454 	clr	(0x07, sp)
      008333 72 F9 07         [ 2]  455 	addw	y, (0x07, sp)
      008336 CE 00 13         [ 2]  456 	ldw	x, _ps+5
      008339 17 05            [ 2]  457 	ldw	(0x05, sp), y
      00833B 72 FB 05         [ 2]  458 	addw	x, (0x05, sp)
      00833E 1F 07            [ 2]  459 	ldw	(0x07, sp), x
                                    460 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 223: if (s == 7) { ps.s = 0; ps.i++; ps.tbase += LOOP_CY; }
      008340 7B 01            [ 1]  461 	ld	a, (0x01, sp)
      008342 A1 07            [ 1]  462 	cp	a, #0x07
      008344 26 17            [ 1]  463 	jrne	00121$
      008346 35 00 00 10      [ 1]  464 	mov	_ps+2, #0x00
      00834A 1E 02            [ 2]  465 	ldw	x, (0x02, sp)
      00834C FE               [ 2]  466 	ldw	x, (x)
      00834D 5C               [ 1]  467 	incw	x
      00834E 16 02            [ 2]  468 	ldw	y, (0x02, sp)
      008350 90 FF            [ 2]  469 	ldw	(y), x
      008352 CE 00 11         [ 2]  470 	ldw	x, _ps+3
      008355 1C 00 28         [ 2]  471 	addw	x, #0x0028
      008358 CF 00 11         [ 2]  472 	ldw	_ps+3, x
      00835B 20 06            [ 2]  473 	jra	00122$
      00835D                        474 00121$:
                                    475 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 224: else        { ps.s = (uint8_t)(s + 1); }
      00835D 7B 01            [ 1]  476 	ld	a, (0x01, sp)
      00835F 4C               [ 1]  477 	inc	a
      008360 C7 00 10         [ 1]  478 	ld	_ps+2, a
      008363                        479 00122$:
                                    480 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 225: if (v) {
      008363 0D 04            [ 1]  481 	tnz	(0x04, sp)
      008365 27 65            [ 1]  482 	jreq	00131$
                                    483 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 226: ps.wsum += W_CY[s];
      008367 90 CE 00 13      [ 2]  484 	ldw	y, _ps+5
      00836B 5F               [ 1]  485 	clrw	x
      00836C 7B 01            [ 1]  486 	ld	a, (0x01, sp)
      00836E 97               [ 1]  487 	ld	xl, a
      00836F 1C 80 3D         [ 2]  488 	addw	x, #(_W_CY+0)
      008372 F6               [ 1]  489 	ld	a, (x)
      008373 97               [ 1]  490 	ld	xl, a
      008374 49               [ 1]  491 	rlc	a
      008375 4F               [ 1]  492 	clr	a
      008376 A2 00            [ 1]  493 	sbc	a, #0x00
      008378 95               [ 1]  494 	ld	xh, a
      008379 17 05            [ 2]  495 	ldw	(0x05, sp), y
      00837B 72 FB 05         [ 2]  496 	addw	x, (0x05, sp)
      00837E CF 00 13         [ 2]  497 	ldw	_ps+5, x
                                    498 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 227: if (!ps.in_pulse) {
      008381 C6 00 18         [ 1]  499 	ld	a, _ps+10
      008384 26 2E            [ 1]  500 	jrne	00124$
                                    501 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 228: ps.in_pulse = 1;
      008386 35 01 00 18      [ 1]  502 	mov	_ps+10, #0x01
                                    503 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
      00838A C6 00 17         [ 1]  504 	ld	a, _ps+9
      00838D 27 05            [ 1]  505 	jreq	00140$
      00838F CE 00 15         [ 2]  506 	ldw	x, _ps+7
      008392 20 17            [ 2]  507 	jra	00141$
      008394                        508 00140$:
                                    509 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 230: : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
      008394 16 07            [ 2]  510 	ldw	y, (0x07, sp)
      008396 17 03            [ 2]  511 	ldw	(0x03, sp), y
      008398 93               [ 1]  512 	ldw	x, y
      008399 A3 00 04         [ 2]  513 	cpw	x, #0x0004
      00839C 25 08            [ 1]  514 	jrc	00142$
      00839E 1E 03            [ 2]  515 	ldw	x, (0x03, sp)
      0083A0 1D 00 04         [ 2]  516 	subw	x, #0x0004
      0083A3 1F 05            [ 2]  517 	ldw	(0x05, sp), x
      0083A5 BC                     518 	.byte 0xbc
      0083A6                        519 00142$:
      0083A6 5F               [ 1]  520 	clrw	x
      0083A7 1F 05            [ 2]  521 	ldw	(0x05, sp), x
      0083A9                        522 00143$:
      0083A9 1E 05            [ 2]  523 	ldw	x, (0x05, sp)
      0083AB                        524 00141$:
      0083AB CF 00 1D         [ 2]  525 	ldw	_ps+15, x
                                    526 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
      0083AE AE 00 1F         [ 2]  527 	ldw	x, #(_ps+17)
      0083B1 16 07            [ 2]  528 	ldw	y, (0x07, sp)
      0083B3 FF               [ 2]  529 	ldw	(x), y
      0083B4                        530 00124$:
                                    531 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 233: ps.fa = t;
      0083B4 AE 00 21         [ 2]  532 	ldw	x, #(_ps+19)
      0083B7 16 07            [ 2]  533 	ldw	y, (0x07, sp)
      0083B9 FF               [ 2]  534 	ldw	(x), y
                                    535 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 234: ps.sfa = s;
      0083BA AE 00 23         [ 2]  536 	ldw	x, #(_ps+21)
      0083BD 7B 01            [ 1]  537 	ld	a, (0x01, sp)
      0083BF F7               [ 1]  538 	ld	(x), a
                                    539 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 235: ps.low_run = 0;
      0083C0 AE 00 1B         [ 2]  540 	ldw	x, #(_ps+13)
      0083C3 6F 01            [ 1]  541 	clr	(0x1, x)
      0083C5 7F               [ 1]  542 	clr	(x)
                                    543 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 236: ps.seen = 1;
      0083C6 35 01 00 19      [ 1]  544 	mov	_ps+11, #0x01
      0083CA 20 55            [ 2]  545 	jra	00132$
      0083CC                        546 00131$:
                                    547 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 238: if (ps.in_pulse) {
      0083CC C6 00 18         [ 1]  548 	ld	a, _ps+10
      0083CF 27 36            [ 1]  549 	jreq	00126$
                                    550 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 239: ps.in_pulse = 0;
      0083D1 35 00 00 18      [ 1]  551 	mov	_ps+10, #0x00
                                    552 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 240: scan_ra = ps.ra; scan_rb = ps.rb;
      0083D5 CE 00 1D         [ 2]  553 	ldw	x, _ps+15
      0083D8 CF 00 05         [ 2]  554 	ldw	_scan_ra+0, x
      0083DB CE 00 1F         [ 2]  555 	ldw	x, _ps+17
      0083DE CF 00 07         [ 2]  556 	ldw	_scan_rb+0, x
                                    557 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 241: scan_fa = ps.fa; scan_fb = t; scan_sfa = ps.sfa;
      0083E1 CE 00 21         [ 2]  558 	ldw	x, _ps+19
      0083E4 CF 00 09         [ 2]  559 	ldw	_scan_fa+0, x
      0083E7 1E 07            [ 2]  560 	ldw	x, (0x07, sp)
      0083E9 CF 00 0B         [ 2]  561 	ldw	_scan_fb+0, x
      0083EC 55 00 23 00 0D   [ 1]  562 	mov	_scan_sfa+0, _ps+21
                                    563 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 242: ps.t_prev = t; ps.have_prev = 1;
      0083F1 AE 00 15         [ 2]  564 	ldw	x, #(_ps+7)
      0083F4 16 07            [ 2]  565 	ldw	y, (0x07, sp)
      0083F6 FF               [ 2]  566 	ldw	(x), y
      0083F7 35 01 00 17      [ 1]  567 	mov	_ps+9, #0x01
                                    568 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 243: ps.low_run = 1;
      0083FB 35 01 00 1C      [ 1]  569 	mov	_ps+14, #0x01
      0083FF 35 00 00 1B      [ 1]  570 	mov	_ps+13, #0x00
                                    571 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 244: return 1;
      008403 A6 01            [ 1]  572 	ld	a, #0x01
      008405 20 59            [ 2]  573 	jra	00138$
      008407                        574 00126$:
                                    575 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 246: ps.low_run++;
      008407 CE 00 1B         [ 2]  576 	ldw	x, _ps+13
      00840A 5C               [ 1]  577 	incw	x
      00840B CF 00 1B         [ 2]  578 	ldw	_ps+13, x
                                    579 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 247: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
      00840E C6 00 19         [ 1]  580 	ld	a, _ps+11
      008411 27 0E            [ 1]  581 	jreq	00132$
      008413 CE 00 1B         [ 2]  582 	ldw	x, _ps+13
      008416 A3 00 C8         [ 2]  583 	cpw	x, #0x00c8
      008419 25 06            [ 1]  584 	jrc	00132$
      00841B 35 01 00 1A      [ 1]  585 	mov	_ps+12, #0x01
      00841F 20 0D            [ 2]  586 	jra	00135$
      008421                        587 00132$:
                                    588 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 249: ps.t_prev = t;
      008421 AE 00 15         [ 2]  589 	ldw	x, #(_ps+7)
      008424 16 07            [ 2]  590 	ldw	y, (0x07, sp)
      008426 FF               [ 2]  591 	ldw	(x), y
                                    592 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 250: ps.have_prev = 1;
      008427 35 01 00 17      [ 1]  593 	mov	_ps+9, #0x01
      00842B CC 81 E8         [ 2]  594 	jp	00133$
      00842E                        595 00135$:
                                    596 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 252: if (ps.in_pulse) {                      /* capture ended high */
      00842E C6 00 18         [ 1]  597 	ld	a, _ps+10
      008431 27 28            [ 1]  598 	jreq	00137$
                                    599 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 253: ps.in_pulse = 0;
      008433 35 00 00 18      [ 1]  600 	mov	_ps+10, #0x00
                                    601 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 254: scan_ra = ps.ra; scan_rb = ps.rb;
      008437 CE 00 1D         [ 2]  602 	ldw	x, _ps+15
      00843A CF 00 05         [ 2]  603 	ldw	_scan_ra+0, x
      00843D CE 00 1F         [ 2]  604 	ldw	x, _ps+17
      008440 CF 00 07         [ 2]  605 	ldw	_scan_rb+0, x
                                    606 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 255: scan_fa = ps.fa; scan_fb = (uint16_t)(ps.fa + FIRST_BR);
      008443 CE 00 21         [ 2]  607 	ldw	x, _ps+19
      008446 CF 00 09         [ 2]  608 	ldw	_scan_fa+0, x
      008449 CE 00 21         [ 2]  609 	ldw	x, _ps+19
      00844C 1C 00 04         [ 2]  610 	addw	x, #0x0004
      00844F CF 00 0B         [ 2]  611 	ldw	_scan_fb+0, x
                                    612 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 256: scan_sfa = ps.sfa;
      008452 55 00 23 00 0D   [ 1]  613 	mov	_scan_sfa+0, _ps+21
                                    614 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 257: return 1;
      008457 A6 01            [ 1]  615 	ld	a, #0x01
      008459 20 05            [ 2]  616 	jra	00138$
      00845B                        617 00137$:
                                    618 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 259: ps.done = 1;
      00845B 35 01 00 1A      [ 1]  619 	mov	_ps+12, #0x01
                                    620 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 260: return 0;
      00845F 4F               [ 1]  621 	clr	a
      008460                        622 00138$:
                                    623 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 261: }
      008460 5B 08            [ 2]  624 	addw	sp, #8
      008462 81               [ 4]  625 	ret
                                    626 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 301: static int32_t map_raw(uint16_t t)
                                    627 ;	-----------------------------------------
                                    628 ;	 function map_raw
                                    629 ;	-----------------------------------------
      008463                        630 _map_raw:
      008463 52 08            [ 2]  631 	sub	sp, #8
                                    632 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 303: return (int32_t)((uint32_t)t * g_K >> KQ) + g_tau;
      008465 90 CE 00 38      [ 2]  633 	ldw	y, _g_K+0
      008469 90 89            [ 2]  634 	pushw	y
      00846B CD 98 2A         [ 4]  635 	call	___muluint2ulong
      00846E 5B 02            [ 2]  636 	addw	sp, #2
      008470 51               [ 1]  637 	exgw	x, y
      008471 A6 0B            [ 1]  638 	ld	a, #0x0b
      008473                        639 00103$:
      008473 54               [ 2]  640 	srlw	x
      008474 90 56            [ 2]  641 	rrcw	y
      008476 4A               [ 1]  642 	dec	a
      008477 26 FA            [ 1]  643 	jrne	00103$
      008479 1F 01            [ 2]  644 	ldw	(0x01, sp), x
      00847B CE 00 3A         [ 2]  645 	ldw	x, _g_tau+0
      00847E 1F 07            [ 2]  646 	ldw	(0x07, sp), x
      008480 5F               [ 1]  647 	clrw	x
      008481 0D 07            [ 1]  648 	tnz	(0x07, sp)
      008483 2A 01            [ 1]  649 	jrpl	00105$
      008485 5A               [ 2]  650 	decw	x
      008486                        651 00105$:
      008486 72 F9 07         [ 2]  652 	addw	y, (0x07, sp)
      008489 9F               [ 1]  653 	ld	a, xl
      00848A 19 02            [ 1]  654 	adc	a, (0x02, sp)
      00848C 02               [ 1]  655 	rlwa	x
      00848D 19 01            [ 1]  656 	adc	a, (0x01, sp)
      00848F 95               [ 1]  657 	ld	xh, a
      008490 51               [ 1]  658 	exgw	x, y
                                    659 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 304: }
      008491 5B 08            [ 2]  660 	addw	sp, #8
      008493 81               [ 4]  661 	ret
                                    662 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 308: static uint8_t seed(void)
                                    663 ;	-----------------------------------------
                                    664 ;	 function seed
                                    665 ;	-----------------------------------------
      008494                        666 _seed:
      008494 52 06            [ 2]  667 	sub	sp, #6
                                    668 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 311: uint16_t r0m = 0, flm = 0;
      008496 5F               [ 1]  669 	clrw	x
      008497 1F 01            [ 2]  670 	ldw	(0x01, sp), x
      008499 5F               [ 1]  671 	clrw	x
                                    672 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 313: scan_init();
      00849A 89               [ 2]  673 	pushw	x
      00849B CD 81 9D         [ 4]  674 	call	_scan_init
      00849E 85               [ 2]  675 	popw	x
                                    676 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 314: while (scan_next()) {
      00849F 90 5F            [ 1]  677 	clrw	y
      0084A1                        678 00103$:
      0084A1 89               [ 2]  679 	pushw	x
      0084A2 90 89            [ 2]  680 	pushw	y
      0084A4 CD 81 E6         [ 4]  681 	call	_scan_next
      0084A7 90 85            [ 2]  682 	popw	y
      0084A9 85               [ 2]  683 	popw	x
      0084AA 4D               [ 1]  684 	tnz	a
      0084AB 27 1A            [ 1]  685 	jreq	00105$
                                    686 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 315: if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
      0084AD 90 5D            [ 2]  687 	tnzw	y
      0084AF 26 0A            [ 1]  688 	jrne	00102$
      0084B1 CE 00 05         [ 2]  689 	ldw	x, _scan_ra+0
      0084B4 72 BB 00 07      [ 2]  690 	addw	x, _scan_rb+0
      0084B8 54               [ 2]  691 	srlw	x
      0084B9 1F 01            [ 2]  692 	ldw	(0x01, sp), x
      0084BB                        693 00102$:
                                    694 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 316: flm = (uint16_t)((scan_fa + scan_fb) >> 1);
      0084BB CE 00 09         [ 2]  695 	ldw	x, _scan_fa+0
      0084BE 72 BB 00 0B      [ 2]  696 	addw	x, _scan_fb+0
      0084C2 54               [ 2]  697 	srlw	x
                                    698 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 317: np++;
      0084C3 90 5C            [ 1]  699 	incw	y
      0084C5 20 DA            [ 2]  700 	jra	00103$
      0084C7                        701 00105$:
                                    702 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 319: if (np < 8 || flm <= r0m) return 0;
      0084C7 90 A3 00 08      [ 2]  703 	cpw	y, #0x0008
      0084CB 25 04            [ 1]  704 	jrc	00106$
      0084CD 13 01            [ 2]  705 	cpw	x, (0x01, sp)
      0084CF 22 03            [ 1]  706 	jrugt	00107$
      0084D1                        707 00106$:
      0084D1 4F               [ 1]  708 	clr	a
      0084D2 20 5E            [ 2]  709 	jra	00112$
      0084D4                        710 00107$:
                                    711 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 321: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
      0084D4 72 F0 01         [ 2]  712 	subw	x, (0x01, sp)
      0084D7 90 5F            [ 1]  713 	clrw	y
      0084D9 89               [ 2]  714 	pushw	x
      0084DA 90 89            [ 2]  715 	pushw	y
      0084DC 4B 00            [ 1]  716 	push	#0x00
      0084DE 4B A0            [ 1]  717 	push	#0xa0
      0084E0 4B F9            [ 1]  718 	push	#0xf9
      0084E2 4B 0B            [ 1]  719 	push	#0x0b
                                    720 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 322: if (K < K_MIN || K > K_MAX) return 0;
      0084E4 CD 98 A8         [ 4]  721 	call	__divulong
      0084E7 5B 08            [ 2]  722 	addw	sp, #8
      0084E9 1F 05            [ 2]  723 	ldw	(0x05, sp), x
      0084EB 17 03            [ 2]  724 	ldw	(0x03, sp), y
      0084ED 1E 05            [ 2]  725 	ldw	x, (0x05, sp)
      0084EF A3 B3 B0         [ 2]  726 	cpw	x, #0xb3b0
      0084F2 7B 04            [ 1]  727 	ld	a, (0x04, sp)
      0084F4 A2 00            [ 1]  728 	sbc	a, #0x00
      0084F6 7B 03            [ 1]  729 	ld	a, (0x03, sp)
      0084F8 A2 00            [ 1]  730 	sbc	a, #0x00
      0084FA 25 0D            [ 1]  731 	jrc	00109$
      0084FC AE EA 60         [ 2]  732 	ldw	x, #0xea60
      0084FF 13 05            [ 2]  733 	cpw	x, (0x05, sp)
      008501 4F               [ 1]  734 	clr	a
      008502 12 04            [ 1]  735 	sbc	a, (0x04, sp)
      008504 4F               [ 1]  736 	clr	a
      008505 12 03            [ 1]  737 	sbc	a, (0x03, sp)
      008507 24 03            [ 1]  738 	jrnc	00110$
      008509                        739 00109$:
      008509 4F               [ 1]  740 	clr	a
      00850A 20 26            [ 2]  741 	jra	00112$
      00850C                        742 00110$:
                                    743 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 323: g_K = (uint16_t)K;
      00850C 1E 05            [ 2]  744 	ldw	x, (0x05, sp)
      00850E CF 00 38         [ 2]  745 	ldw	_g_K+0, x
                                    746 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 324: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
      008511 16 01            [ 2]  747 	ldw	y, (0x01, sp)
      008513 CE 00 38         [ 2]  748 	ldw	x, _g_K+0
      008516 89               [ 2]  749 	pushw	x
      008517 93               [ 1]  750 	ldw	x, y
      008518 CD 98 2A         [ 4]  751 	call	___muluint2ulong
      00851B 5B 02            [ 2]  752 	addw	sp, #2
      00851D A6 0B            [ 1]  753 	ld	a, #0x0b
      00851F                        754 00161$:
      00851F 90 54            [ 2]  755 	srlw	y
      008521 56               [ 2]  756 	rrcw	x
      008522 4A               [ 1]  757 	dec	a
      008523 26 FA            [ 1]  758 	jrne	00161$
      008525 1F 05            [ 2]  759 	ldw	(0x05, sp), x
      008527 AE 02 00         [ 2]  760 	ldw	x, #0x0200
      00852A 72 F0 05         [ 2]  761 	subw	x, (0x05, sp)
      00852D CF 00 3A         [ 2]  762 	ldw	_g_tau+0, x
                                    763 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 325: return 1;
      008530 A6 01            [ 1]  764 	ld	a, #0x01
      008532                        765 00112$:
                                    766 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 326: }
      008532 5B 06            [ 2]  767 	addw	sp, #6
      008534 81               [ 4]  768 	ret
                                    769 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 330: static void refine(void)
                                    770 ;	-----------------------------------------
                                    771 ;	 function refine
                                    772 ;	-----------------------------------------
      008535                        773 _refine:
      008535 52 28            [ 2]  774 	sub	sp, #40
                                    775 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 335: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
      008537 5F               [ 1]  776 	clrw	x
      008538 1F 17            [ 2]  777 	ldw	(0x17, sp), x
      00853A 1F 15            [ 2]  778 	ldw	(0x15, sp), x
      00853C 5F               [ 1]  779 	clrw	x
      00853D 1F 1B            [ 2]  780 	ldw	(0x1b, sp), x
      00853F 1F 19            [ 2]  781 	ldw	(0x19, sp), x
                                    782 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 336: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
      008541 5F               [ 1]  783 	clrw	x
      008542 1F 1F            [ 2]  784 	ldw	(0x1f, sp), x
      008544 1F 1D            [ 2]  785 	ldw	(0x1d, sp), x
      008546 5F               [ 1]  786 	clrw	x
      008547 1F 23            [ 2]  787 	ldw	(0x23, sp), x
      008549 1F 21            [ 2]  788 	ldw	(0x21, sp), x
                                    789 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 340: scan_init();
      00854B CD 81 9D         [ 4]  790 	call	_scan_init
                                    791 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 341: while (scan_next()) {
      00854E 5F               [ 1]  792 	clrw	x
      00854F 1F 25            [ 2]  793 	ldw	(0x25, sp), x
      008551 5F               [ 1]  794 	clrw	x
      008552 1F 27            [ 2]  795 	ldw	(0x27, sp), x
      008554                        796 00108$:
      008554 CD 81 E6         [ 4]  797 	call	_scan_next
      008557 4D               [ 1]  798 	tnz	a
      008558 26 03            [ 1]  799 	jrne	00186$
      00855A CC 86 19         [ 2]  800 	jp	00110$
      00855D                        801 00186$:
                                    802 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 345: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      00855D CE 00 05         [ 2]  803 	ldw	x, _scan_ra+0
      008560 72 BB 00 07      [ 2]  804 	addw	x, _scan_rb+0
      008564 54               [ 2]  805 	srlw	x
      008565 CD 84 63         [ 4]  806 	call	_map_raw
      008568 1F 0D            [ 2]  807 	ldw	(0x0d, sp), x
      00856A 17 0B            [ 2]  808 	ldw	(0x0b, sp), y
                                    809 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 346: if (y < 0) y = 0;
      00856C 0D 0B            [ 1]  810 	tnz	(0x0b, sp)
      00856E 2A 05            [ 1]  811 	jrpl	00102$
      008570 5F               [ 1]  812 	clrw	x
      008571 1F 0D            [ 2]  813 	ldw	(0x0d, sp), x
      008573 1F 0B            [ 2]  814 	ldw	(0x0b, sp), x
      008575                        815 00102$:
                                    816 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 347: if ((uint32_t)y > y_end) break;
      008575 16 0D            [ 2]  817 	ldw	y, (0x0d, sp)
      008577 17 11            [ 2]  818 	ldw	(0x11, sp), y
      008579 16 0B            [ 2]  819 	ldw	y, (0x0b, sp)
      00857B 17 0F            [ 2]  820 	ldw	(0x0f, sp), y
      00857D AE 82 A4         [ 2]  821 	ldw	x, #0x82a4
      008580 13 11            [ 2]  822 	cpw	x, (0x11, sp)
      008582 A6 01            [ 1]  823 	ld	a, #0x01
      008584 12 10            [ 1]  824 	sbc	a, (0x10, sp)
      008586 4F               [ 1]  825 	clr	a
      008587 12 0F            [ 1]  826 	sbc	a, (0x0f, sp)
      008589 24 03            [ 1]  827 	jrnc	00188$
      00858B CC 86 19         [ 2]  828 	jp	00110$
      00858E                        829 00188$:
                                    830 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 348: q = ((uint32_t)y + BIT_H) >> BIT_SH;
      00858E 1E 11            [ 2]  831 	ldw	x, (0x11, sp)
      008590 1C 01 00         [ 2]  832 	addw	x, #0x0100
      008593 16 0F            [ 2]  833 	ldw	y, (0x0f, sp)
      008595 24 02            [ 1]  834 	jrnc	00189$
      008597 90 5C            [ 1]  835 	incw	y
      008599                        836 00189$:
      008599 90 54            [ 2]  837 	srlw	y
      00859B 56               [ 2]  838 	rrcw	x
                                    839 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 349: e = (int16_t)(y - (int32_t)(q << BIT_SH));
      00859C 4F               [ 1]  840 	clr	a
      00859D 97               [ 1]  841 	ld	xl, a
      00859E 58               [ 2]  842 	sllw	x
      00859F 16 0D            [ 2]  843 	ldw	y, (0x0d, sp)
      0085A1 17 13            [ 2]  844 	ldw	(0x13, sp), y
      0085A3 50               [ 2]  845 	negw	x
      0085A4 72 FB 13         [ 2]  846 	addw	x, (0x13, sp)
                                    847 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 350: if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
      0085A7 51               [ 1]  848 	exgw	x, y
      0085A8 90 9E            [ 1]  849 	ld	a, yh
      0085AA 49               [ 1]  850 	rlc	a
      0085AB 4F               [ 1]  851 	clr	a
      0085AC A2 00            [ 1]  852 	sbc	a, #0x00
      0085AE 88               [ 1]  853 	push	a
      0085AF 6B 0C            [ 1]  854 	ld	(0x0c, sp), a
      0085B1 84               [ 1]  855 	pop	a
      0085B2 1E 11            [ 2]  856 	ldw	x, (0x11, sp)
      0085B4 A3 C2 00         [ 2]  857 	cpw	x, #0xc200
      0085B7 88               [ 1]  858 	push	a
      0085B8 7B 11            [ 1]  859 	ld	a, (0x11, sp)
      0085BA A2 00            [ 1]  860 	sbc	a, #0x00
      0085BC 7B 10            [ 1]  861 	ld	a, (0x10, sp)
      0085BE A2 00            [ 1]  862 	sbc	a, #0x00
      0085C0 84               [ 1]  863 	pop	a
      0085C1 24 2B            [ 1]  864 	jrnc	00106$
      0085C3 1E 25            [ 2]  865 	ldw	x, (0x25, sp)
      0085C5 5C               [ 1]  866 	incw	x
      0085C6 1F 25            [ 2]  867 	ldw	(0x25, sp), x
      0085C8 93               [ 1]  868 	ldw	x, y
      0085C9 72 FB 17         [ 2]  869 	addw	x, (0x17, sp)
      0085CC 1F 17            [ 2]  870 	ldw	(0x17, sp), x
      0085CE 19 16            [ 1]  871 	adc	a, (0x16, sp)
      0085D0 6B 16            [ 1]  872 	ld	(0x16, sp), a
      0085D2 7B 0B            [ 1]  873 	ld	a, (0x0b, sp)
      0085D4 19 15            [ 1]  874 	adc	a, (0x15, sp)
      0085D6 6B 15            [ 1]  875 	ld	(0x15, sp), a
      0085D8 1E 1F            [ 2]  876 	ldw	x, (0x1f, sp)
      0085DA 72 FB 11         [ 2]  877 	addw	x, (0x11, sp)
      0085DD 1F 1F            [ 2]  878 	ldw	(0x1f, sp), x
      0085DF 7B 1E            [ 1]  879 	ld	a, (0x1e, sp)
      0085E1 19 10            [ 1]  880 	adc	a, (0x10, sp)
      0085E3 6B 1E            [ 1]  881 	ld	(0x1e, sp), a
      0085E5 7B 1D            [ 1]  882 	ld	a, (0x1d, sp)
      0085E7 19 0F            [ 1]  883 	adc	a, (0x0f, sp)
      0085E9 6B 1D            [ 1]  884 	ld	(0x1d, sp), a
      0085EB CC 85 54         [ 2]  885 	jp	00108$
      0085EE                        886 00106$:
                                    887 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 351: else                     { n_hi++; se_hi += e; sy_hi += (uint32_t)y; }
      0085EE 1E 27            [ 2]  888 	ldw	x, (0x27, sp)
      0085F0 5C               [ 1]  889 	incw	x
      0085F1 1F 27            [ 2]  890 	ldw	(0x27, sp), x
      0085F3 93               [ 1]  891 	ldw	x, y
      0085F4 72 FB 1B         [ 2]  892 	addw	x, (0x1b, sp)
      0085F7 1F 1B            [ 2]  893 	ldw	(0x1b, sp), x
      0085F9 19 1A            [ 1]  894 	adc	a, (0x1a, sp)
      0085FB 6B 1A            [ 1]  895 	ld	(0x1a, sp), a
      0085FD 7B 0B            [ 1]  896 	ld	a, (0x0b, sp)
      0085FF 19 19            [ 1]  897 	adc	a, (0x19, sp)
      008601 6B 19            [ 1]  898 	ld	(0x19, sp), a
      008603 1E 23            [ 2]  899 	ldw	x, (0x23, sp)
      008605 72 FB 11         [ 2]  900 	addw	x, (0x11, sp)
      008608 1F 23            [ 2]  901 	ldw	(0x23, sp), x
      00860A 7B 22            [ 1]  902 	ld	a, (0x22, sp)
      00860C 19 10            [ 1]  903 	adc	a, (0x10, sp)
      00860E 6B 22            [ 1]  904 	ld	(0x22, sp), a
      008610 7B 21            [ 1]  905 	ld	a, (0x21, sp)
      008612 19 0F            [ 1]  906 	adc	a, (0x0f, sp)
      008614 6B 21            [ 1]  907 	ld	(0x21, sp), a
      008616 CC 85 54         [ 2]  908 	jp	00108$
      008619                        909 00110$:
                                    910 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 353: if (n_lo < 2 || n_hi < 2) return;
      008619 1E 25            [ 2]  911 	ldw	x, (0x25, sp)
      00861B A3 00 02         [ 2]  912 	cpw	x, #0x0002
      00861E 24 03            [ 1]  913 	jrnc	00193$
      008620 CC 87 C1         [ 2]  914 	jp	00119$
      008623                        915 00193$:
      008623 1E 27            [ 2]  916 	ldw	x, (0x27, sp)
      008625 A3 00 02         [ 2]  917 	cpw	x, #0x0002
      008628 24 03            [ 1]  918 	jrnc	00112$
      00862A CC 87 C1         [ 2]  919 	jp	00119$
      00862D                        920 00112$:
                                    921 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 354: me_lo = se_lo / (int32_t)n_lo;
      00862D 16 25            [ 2]  922 	ldw	y, (0x25, sp)
      00862F 5F               [ 1]  923 	clrw	x
      008630 90 89            [ 2]  924 	pushw	y
      008632 89               [ 2]  925 	pushw	x
      008633 1E 1B            [ 2]  926 	ldw	x, (0x1b, sp)
      008635 89               [ 2]  927 	pushw	x
      008636 1E 1B            [ 2]  928 	ldw	x, (0x1b, sp)
      008638 89               [ 2]  929 	pushw	x
                                    930 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 355: me_hi = se_hi / (int32_t)n_hi;
      008639 CD 98 81         [ 4]  931 	call	__divslong
      00863C 5B 08            [ 2]  932 	addw	sp, #8
      00863E 1F 07            [ 2]  933 	ldw	(0x07, sp), x
      008640 17 05            [ 2]  934 	ldw	(0x05, sp), y
      008642 16 27            [ 2]  935 	ldw	y, (0x27, sp)
      008644 5F               [ 1]  936 	clrw	x
      008645 90 89            [ 2]  937 	pushw	y
      008647 89               [ 2]  938 	pushw	x
      008648 1E 1F            [ 2]  939 	ldw	x, (0x1f, sp)
      00864A 89               [ 2]  940 	pushw	x
      00864B 1E 1F            [ 2]  941 	ldw	x, (0x1f, sp)
      00864D 89               [ 2]  942 	pushw	x
                                    943 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 356: my_lo = sy_lo / n_lo;
      00864E CD 98 81         [ 4]  944 	call	__divslong
      008651 5B 08            [ 2]  945 	addw	sp, #8
      008653 1F 0B            [ 2]  946 	ldw	(0x0b, sp), x
      008655 17 09            [ 2]  947 	ldw	(0x09, sp), y
      008657 16 25            [ 2]  948 	ldw	y, (0x25, sp)
      008659 5F               [ 1]  949 	clrw	x
      00865A 90 89            [ 2]  950 	pushw	y
      00865C 89               [ 2]  951 	pushw	x
      00865D 1E 23            [ 2]  952 	ldw	x, (0x23, sp)
      00865F 89               [ 2]  953 	pushw	x
      008660 1E 23            [ 2]  954 	ldw	x, (0x23, sp)
      008662 89               [ 2]  955 	pushw	x
                                    956 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 357: my_hi = sy_hi / n_hi;
      008663 CD 98 A8         [ 4]  957 	call	__divulong
      008666 5B 08            [ 2]  958 	addw	sp, #8
      008668 1F 13            [ 2]  959 	ldw	(0x13, sp), x
      00866A 17 11            [ 2]  960 	ldw	(0x11, sp), y
      00866C 16 27            [ 2]  961 	ldw	y, (0x27, sp)
      00866E 5F               [ 1]  962 	clrw	x
      00866F 90 89            [ 2]  963 	pushw	y
      008671 89               [ 2]  964 	pushw	x
      008672 1E 27            [ 2]  965 	ldw	x, (0x27, sp)
      008674 89               [ 2]  966 	pushw	x
      008675 1E 27            [ 2]  967 	ldw	x, (0x27, sp)
      008677 89               [ 2]  968 	pushw	x
                                    969 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 358: de = me_hi - me_lo;
      008678 CD 98 A8         [ 4]  970 	call	__divulong
      00867B 5B 08            [ 2]  971 	addw	sp, #8
      00867D 17 0D            [ 2]  972 	ldw	(0x0d, sp), y
      00867F 16 0B            [ 2]  973 	ldw	y, (0x0b, sp)
      008681 72 F2 07         [ 2]  974 	subw	y, (0x07, sp)
      008684 17 03            [ 2]  975 	ldw	(0x03, sp), y
      008686 7B 0A            [ 1]  976 	ld	a, (0x0a, sp)
      008688 12 06            [ 1]  977 	sbc	a, (0x06, sp)
      00868A 6B 02            [ 1]  978 	ld	(0x02, sp), a
      00868C 7B 09            [ 1]  979 	ld	a, (0x09, sp)
      00868E 12 05            [ 1]  980 	sbc	a, (0x05, sp)
      008690 6B 01            [ 1]  981 	ld	(0x01, sp), a
                                    982 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 359: dy = (int32_t)my_hi - (int32_t)my_lo;
      008692 7B 0E            [ 1]  983 	ld	a, (0x0e, sp)
      008694 72 F0 13         [ 2]  984 	subw	x, (0x13, sp)
      008697 1F 07            [ 2]  985 	ldw	(0x07, sp), x
      008699 12 12            [ 1]  986 	sbc	a, (0x12, sp)
      00869B 6B 06            [ 1]  987 	ld	(0x06, sp), a
      00869D 7B 0D            [ 1]  988 	ld	a, (0x0d, sp)
      00869F 12 11            [ 1]  989 	sbc	a, (0x11, sp)
      0086A1 6B 05            [ 1]  990 	ld	(0x05, sp), a
                                    991 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 360: if (dy <= 0) return;
      0086A3 5F               [ 1]  992 	clrw	x
      0086A4 13 07            [ 2]  993 	cpw	x, (0x07, sp)
      0086A6 4F               [ 1]  994 	clr	a
      0086A7 12 06            [ 1]  995 	sbc	a, (0x06, sp)
      0086A9 4F               [ 1]  996 	clr	a
      0086AA 12 05            [ 1]  997 	sbc	a, (0x05, sp)
      0086AC 2F 03            [ 1]  998 	jrslt	00115$
      0086AE CC 87 C1         [ 2]  999 	jp	00119$
      0086B1                       1000 00115$:
                                   1001 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 361: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
      0086B1 CE 00 38         [ 2] 1002 	ldw	x, _g_K+0
      0086B4 1F 0B            [ 2] 1003 	ldw	(0x0b, sp), x
      0086B6 0F 0A            [ 1] 1004 	clr	(0x0a, sp)
      0086B8 0F 09            [ 1] 1005 	clr	(0x09, sp)
      0086BA 1E 03            [ 2] 1006 	ldw	x, (0x03, sp)
      0086BC 89               [ 2] 1007 	pushw	x
      0086BD 1E 03            [ 2] 1008 	ldw	x, (0x03, sp)
      0086BF 89               [ 2] 1009 	pushw	x
      0086C0 1E 0F            [ 2] 1010 	ldw	x, (0x0f, sp)
      0086C2 89               [ 2] 1011 	pushw	x
      0086C3 1E 0F            [ 2] 1012 	ldw	x, (0x0f, sp)
      0086C5 89               [ 2] 1013 	pushw	x
      0086C6 CD 99 05         [ 4] 1014 	call	__mullong
      0086C9 5B 08            [ 2] 1015 	addw	sp, #8
      0086CB 1F 13            [ 2] 1016 	ldw	(0x13, sp), x
      0086CD 1E 07            [ 2] 1017 	ldw	x, (0x07, sp)
      0086CF 89               [ 2] 1018 	pushw	x
      0086D0 1E 07            [ 2] 1019 	ldw	x, (0x07, sp)
      0086D2 89               [ 2] 1020 	pushw	x
      0086D3 1E 17            [ 2] 1021 	ldw	x, (0x17, sp)
      0086D5 89               [ 2] 1022 	pushw	x
      0086D6 90 89            [ 2] 1023 	pushw	y
                                   1024 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 362: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
      0086D8 CD 98 81         [ 4] 1025 	call	__divslong
      0086DB 5B 08            [ 2] 1026 	addw	sp, #8
      0086DD 1F 0F            [ 2] 1027 	ldw	(0x0f, sp), x
      0086DF 17 0D            [ 2] 1028 	ldw	(0x0d, sp), y
      0086E1 1E 17            [ 2] 1029 	ldw	x, (0x17, sp)
      0086E3 72 FB 1B         [ 2] 1030 	addw	x, (0x1b, sp)
      0086E6 1F 13            [ 2] 1031 	ldw	(0x13, sp), x
      0086E8 7B 16            [ 1] 1032 	ld	a, (0x16, sp)
      0086EA 19 1A            [ 1] 1033 	adc	a, (0x1a, sp)
      0086EC 6B 12            [ 1] 1034 	ld	(0x12, sp), a
      0086EE 7B 15            [ 1] 1035 	ld	a, (0x15, sp)
      0086F0 19 19            [ 1] 1036 	adc	a, (0x19, sp)
      0086F2 6B 11            [ 1] 1037 	ld	(0x11, sp), a
      0086F4 1E 25            [ 2] 1038 	ldw	x, (0x25, sp)
      0086F6 72 FB 27         [ 2] 1039 	addw	x, (0x27, sp)
      0086F9 1F 1B            [ 2] 1040 	ldw	(0x1b, sp), x
      0086FB 90 93            [ 1] 1041 	ldw	y, x
      0086FD 5F               [ 1] 1042 	clrw	x
      0086FE 90 89            [ 2] 1043 	pushw	y
      008700 89               [ 2] 1044 	pushw	x
      008701 1E 17            [ 2] 1045 	ldw	x, (0x17, sp)
      008703 89               [ 2] 1046 	pushw	x
      008704 1E 17            [ 2] 1047 	ldw	x, (0x17, sp)
      008706 89               [ 2] 1048 	pushw	x
                                   1049 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 363: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
      008707 CD 98 81         [ 4] 1050 	call	__divslong
      00870A 5B 08            [ 2] 1051 	addw	sp, #8
      00870C 1F 19            [ 2] 1052 	ldw	(0x19, sp), x
      00870E 17 17            [ 2] 1053 	ldw	(0x17, sp), y
      008710 1E 1F            [ 2] 1054 	ldw	x, (0x1f, sp)
      008712 72 FB 23         [ 2] 1055 	addw	x, (0x23, sp)
      008715 1F 27            [ 2] 1056 	ldw	(0x27, sp), x
      008717 7B 1E            [ 1] 1057 	ld	a, (0x1e, sp)
      008719 19 22            [ 1] 1058 	adc	a, (0x22, sp)
      00871B 6B 26            [ 1] 1059 	ld	(0x26, sp), a
      00871D 7B 1D            [ 1] 1060 	ld	a, (0x1d, sp)
      00871F 19 21            [ 1] 1061 	adc	a, (0x21, sp)
      008721 6B 25            [ 1] 1062 	ld	(0x25, sp), a
      008723 16 1B            [ 2] 1063 	ldw	y, (0x1b, sp)
      008725 5F               [ 1] 1064 	clrw	x
      008726 90 89            [ 2] 1065 	pushw	y
      008728 89               [ 2] 1066 	pushw	x
      008729 1E 2B            [ 2] 1067 	ldw	x, (0x2b, sp)
      00872B 89               [ 2] 1068 	pushw	x
      00872C 1E 2B            [ 2] 1069 	ldw	x, (0x2b, sp)
      00872E 89               [ 2] 1070 	pushw	x
                                   1071 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 364: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
      00872F CD 98 A8         [ 4] 1072 	call	__divulong
      008732 5B 08            [ 2] 1073 	addw	sp, #8
      008734 51               [ 1] 1074 	exgw	x, y
      008735 7B 19            [ 1] 1075 	ld	a, (0x19, sp)
      008737 6B 27            [ 1] 1076 	ld	(0x27, sp), a
      008739 7B 1A            [ 1] 1077 	ld	a, (0x1a, sp)
      00873B 40               [ 1] 1078 	neg	a
      00873C 6B 20            [ 1] 1079 	ld	(0x20, sp), a
      00873E 4F               [ 1] 1080 	clr	a
      00873F 12 27            [ 1] 1081 	sbc	a, (0x27, sp)
      008741 6B 1F            [ 1] 1082 	ld	(0x1f, sp), a
      008743 1F 21            [ 2] 1083 	ldw	(0x21, sp), x
      008745 CE 00 3A         [ 2] 1084 	ldw	x, _g_tau+0
      008748 1F 27            [ 2] 1085 	ldw	(0x27, sp), x
      00874A 7B 27            [ 1] 1086 	ld	a, (0x27, sp)
      00874C 49               [ 1] 1087 	rlc	a
      00874D 4F               [ 1] 1088 	clr	a
      00874E A2 00            [ 1] 1089 	sbc	a, #0x00
      008750 6B 26            [ 1] 1090 	ld	(0x26, sp), a
      008752 6B 25            [ 1] 1091 	ld	(0x25, sp), a
      008754 72 F2 27         [ 2] 1092 	subw	y, (0x27, sp)
      008757 7B 22            [ 1] 1093 	ld	a, (0x22, sp)
      008759 12 26            [ 1] 1094 	sbc	a, (0x26, sp)
      00875B 97               [ 1] 1095 	ld	xl, a
      00875C 7B 21            [ 1] 1096 	ld	a, (0x21, sp)
      00875E 12 25            [ 1] 1097 	sbc	a, (0x25, sp)
      008760 95               [ 1] 1098 	ld	xh, a
      008761 90 89            [ 2] 1099 	pushw	y
      008763 89               [ 2] 1100 	pushw	x
      008764 1E 07            [ 2] 1101 	ldw	x, (0x07, sp)
      008766 89               [ 2] 1102 	pushw	x
      008767 1E 07            [ 2] 1103 	ldw	x, (0x07, sp)
      008769 89               [ 2] 1104 	pushw	x
      00876A CD 99 05         [ 4] 1105 	call	__mullong
      00876D 5B 08            [ 2] 1106 	addw	sp, #8
      00876F 1F 27            [ 2] 1107 	ldw	(0x27, sp), x
      008771 1E 07            [ 2] 1108 	ldw	x, (0x07, sp)
      008773 89               [ 2] 1109 	pushw	x
      008774 1E 07            [ 2] 1110 	ldw	x, (0x07, sp)
      008776 89               [ 2] 1111 	pushw	x
      008777 1E 2B            [ 2] 1112 	ldw	x, (0x2b, sp)
      008779 89               [ 2] 1113 	pushw	x
      00877A 90 89            [ 2] 1114 	pushw	y
      00877C CD 98 81         [ 4] 1115 	call	__divslong
      00877F 5B 08            [ 2] 1116 	addw	sp, #8
      008781 72 FB 1F         [ 2] 1117 	addw	x, (0x1f, sp)
      008784 1F 27            [ 2] 1118 	ldw	(0x27, sp), x
                                   1119 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 365: K2 = (int32_t)g_K - dk;
      008786 1E 0B            [ 2] 1120 	ldw	x, (0x0b, sp)
      008788 72 F0 0F         [ 2] 1121 	subw	x, (0x0f, sp)
      00878B 1F 25            [ 2] 1122 	ldw	(0x25, sp), x
      00878D 4F               [ 1] 1123 	clr	a
      00878E 12 0E            [ 1] 1124 	sbc	a, (0x0e, sp)
      008790 6B 24            [ 1] 1125 	ld	(0x24, sp), a
      008792 4F               [ 1] 1126 	clr	a
      008793 12 0D            [ 1] 1127 	sbc	a, (0x0d, sp)
      008795 6B 23            [ 1] 1128 	ld	(0x23, sp), a
                                   1129 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 366: if (K2 < (int32_t)K_MIN || K2 > (int32_t)K_MAX) return;
      008797 1E 25            [ 2] 1130 	ldw	x, (0x25, sp)
      008799 A3 B3 B0         [ 2] 1131 	cpw	x, #0xb3b0
      00879C 7B 24            [ 1] 1132 	ld	a, (0x24, sp)
      00879E A2 00            [ 1] 1133 	sbc	a, #0x00
      0087A0 7B 23            [ 1] 1134 	ld	a, (0x23, sp)
      0087A2 A2 00            [ 1] 1135 	sbc	a, #0x00
      0087A4 2F 1B            [ 1] 1136 	jrslt	00119$
      0087A6 AE EA 60         [ 2] 1137 	ldw	x, #0xea60
      0087A9 13 25            [ 2] 1138 	cpw	x, (0x25, sp)
      0087AB 4F               [ 1] 1139 	clr	a
      0087AC 12 24            [ 1] 1140 	sbc	a, (0x24, sp)
      0087AE 4F               [ 1] 1141 	clr	a
      0087AF 12 23            [ 1] 1142 	sbc	a, (0x23, sp)
      0087B1 2F 0E            [ 1] 1143 	jrslt	00119$
                                   1144 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 367: g_K = (uint16_t)K2;
      0087B3 1E 25            [ 2] 1145 	ldw	x, (0x25, sp)
      0087B5 CF 00 38         [ 2] 1146 	ldw	_g_K+0, x
                                   1147 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 368: g_tau = (int16_t)(g_tau + dtau);
      0087B8 CE 00 3A         [ 2] 1148 	ldw	x, _g_tau+0
      0087BB 72 FB 27         [ 2] 1149 	addw	x, (0x27, sp)
      0087BE CF 00 3A         [ 2] 1150 	ldw	_g_tau+0, x
      0087C1                       1151 00119$:
                                   1152 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 369: }
      0087C1 5B 28            [ 2] 1153 	addw	sp, #40
      0087C3 81               [ 4] 1154 	ret
                                   1155 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 393: static void ss_init(void)
                                   1156 ;	-----------------------------------------
                                   1157 ;	 function ss_init
                                   1158 ;	-----------------------------------------
      0087C4                       1159 _ss_init:
                                   1160 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 395: scan_init();
      0087C4 CD 81 9D         [ 4] 1161 	call	_scan_init
                                   1162 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 396: ss.y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
      0087C7 AE 01 4A         [ 2] 1163 	ldw	x, #(_ss+0)
      0087CA 90 AE 82 A4      [ 2] 1164 	ldw	y, #0x82a4
      0087CE EF 02            [ 2] 1165 	ldw	(0x2, x), y
      0087D0 90 AE 00 01      [ 2] 1166 	ldw	y, #0x0001
      0087D4 FF               [ 2] 1167 	ldw	(x), y
                                   1168 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 397: ss.y_prev = 0; ss.have_y = 0; ss.n = 0;
      0087D5 AE 01 4E         [ 2] 1169 	ldw	x, #(_ss+4)
      0087D8 90 5F            [ 1] 1170 	clrw	y
      0087DA EF 02            [ 2] 1171 	ldw	(0x2, x), y
      0087DC FF               [ 2] 1172 	ldw	(x), y
      0087DD 35 00 01 52      [ 1] 1173 	mov	_ss+8, #0x00
      0087E1 AE 01 53         [ 2] 1174 	ldw	x, #(_ss+9)
      0087E4 6F 01            [ 1] 1175 	clr	(0x1, x)
      0087E6 7F               [ 1] 1176 	clr	(x)
                                   1177 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 398: ss.pend = 0; ss.src_done = 0;
      0087E7 35 00 01 55      [ 1] 1178 	mov	_ss+11, #0x00
      0087EB 35 00 01 5D      [ 1] 1179 	mov	_ss+19, #0x00
                                   1180 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 399: ss.p_k0 = 0; ss.p_u = 0; ss.p_v = 0; ss.p_fam = 0;
      0087EF AE 01 56         [ 2] 1181 	ldw	x, #(_ss+12)
      0087F2 6F 01            [ 1] 1182 	clr	(0x1, x)
      0087F4 7F               [ 1] 1183 	clr	(x)
      0087F5 AE 01 58         [ 2] 1184 	ldw	x, #(_ss+14)
      0087F8 6F 01            [ 1] 1185 	clr	(0x1, x)
      0087FA 7F               [ 1] 1186 	clr	(x)
      0087FB AE 01 5A         [ 2] 1187 	ldw	x, #(_ss+16)
      0087FE 6F 01            [ 1] 1188 	clr	(0x1, x)
      008800 7F               [ 1] 1189 	clr	(x)
      008801 35 00 01 5C      [ 1] 1190 	mov	_ss+18, #0x00
                                   1191 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 400: }
      008805 81               [ 4] 1192 	ret
                                   1193 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 402: static uint8_t ss_next(Seg *out)
                                   1194 ;	-----------------------------------------
                                   1195 ;	 function ss_next
                                   1196 ;	-----------------------------------------
      008806                       1197 _ss_next:
      008806 52 1C            [ 2] 1198 	sub	sp, #28
      008808 1F 1B            [ 2] 1199 	ldw	(0x1b, sp), x
                                   1200 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      00880A                       1201 00121$:
      00880A C6 01 5D         [ 1] 1202 	ld	a, _ss+19
                                   1203 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
                                   1204 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
                                   1205 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
                                   1206 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
                                   1207 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      00880D 16 1B            [ 2] 1208 	ldw	y, (0x1b, sp)
      00880F 17 01            [ 2] 1209 	ldw	(0x01, sp), y
                                   1210 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      008811 1E 1B            [ 2] 1211 	ldw	x, (0x1b, sp)
      008813 5C               [ 1] 1212 	incw	x
      008814 5C               [ 1] 1213 	incw	x
      008815 1F 03            [ 2] 1214 	ldw	(0x03, sp), x
                                   1215 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      008817 1E 1B            [ 2] 1216 	ldw	x, (0x1b, sp)
      008819 1C 00 04         [ 2] 1217 	addw	x, #0x0004
      00881C 1F 05            [ 2] 1218 	ldw	(0x05, sp), x
      00881E 1E 1B            [ 2] 1219 	ldw	x, (0x1b, sp)
      008820 1C 00 06         [ 2] 1220 	addw	x, #0x0006
      008823 1F 07            [ 2] 1221 	ldw	(0x07, sp), x
      008825 1E 1B            [ 2] 1222 	ldw	x, (0x1b, sp)
      008827 1C 00 08         [ 2] 1223 	addw	x, #0x0008
      00882A 1F 09            [ 2] 1224 	ldw	(0x09, sp), x
                                   1225 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      00882C 4D               [ 1] 1226 	tnz	a
      00882D 27 03            [ 1] 1227 	jreq	00242$
      00882F CC 8A 02         [ 2] 1228 	jp	00123$
      008832                       1229 00242$:
                                   1230 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 409: if (!scan_next()) { ss.src_done = 1; break; }
      008832 CD 81 E6         [ 4] 1231 	call	_scan_next
      008835 4D               [ 1] 1232 	tnz	a
      008836 26 07            [ 1] 1233 	jrne	00102$
      008838 35 01 01 5D      [ 1] 1234 	mov	_ss+19, #0x01
      00883C CC 8A 02         [ 2] 1235 	jp	00123$
      00883F                       1236 00102$:
                                   1237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 410: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      00883F CE 00 05         [ 2] 1238 	ldw	x, _scan_ra+0
      008842 72 BB 00 07      [ 2] 1239 	addw	x, _scan_rb+0
      008846 54               [ 2] 1240 	srlw	x
      008847 CD 84 63         [ 4] 1241 	call	_map_raw
      00884A 1F 0D            [ 2] 1242 	ldw	(0x0d, sp), x
      00884C 17 0B            [ 2] 1243 	ldw	(0x0b, sp), y
                                   1244 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 411: if (y < 0) y = 0;
      00884E 0D 0B            [ 1] 1245 	tnz	(0x0b, sp)
      008850 2A 05            [ 1] 1246 	jrpl	00104$
      008852 5F               [ 1] 1247 	clrw	x
      008853 1F 0D            [ 2] 1248 	ldw	(0x0d, sp), x
      008855 1F 0B            [ 2] 1249 	ldw	(0x0b, sp), x
      008857                       1250 00104$:
                                   1251 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 412: if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
      008857 16 0D            [ 2] 1252 	ldw	y, (0x0d, sp)
      008859 17 11            [ 2] 1253 	ldw	(0x11, sp), y
      00885B 16 0B            [ 2] 1254 	ldw	y, (0x0b, sp)
      00885D 17 0F            [ 2] 1255 	ldw	(0x0f, sp), y
      00885F AE 01 4A         [ 2] 1256 	ldw	x, #(_ss+0)
      008862 90 93            [ 1] 1257 	ldw	y, x
      008864 90 EE 02         [ 2] 1258 	ldw	y, (0x2, y)
      008867 FE               [ 2] 1259 	ldw	x, (x)
      008868 90 9F            [ 1] 1260 	ld	a, yl
      00886A 11 12            [ 1] 1261 	cp	a, (0x12, sp)
      00886C 90 9E            [ 1] 1262 	ld	a, yh
      00886E 12 11            [ 1] 1263 	sbc	a, (0x11, sp)
      008870 9F               [ 1] 1264 	ld	a, xl
      008871 12 10            [ 1] 1265 	sbc	a, (0x10, sp)
      008873 9E               [ 1] 1266 	ld	a, xh
      008874 12 0F            [ 1] 1267 	sbc	a, (0x0f, sp)
      008876 24 07            [ 1] 1268 	jrnc	00106$
      008878 35 01 01 5D      [ 1] 1269 	mov	_ss+19, #0x01
      00887C CC 8A 02         [ 2] 1270 	jp	00123$
      00887F                       1271 00106$:
                                   1272 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
                                   1273 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
                                   1274 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
      00887F C6 01 52         [ 1] 1275 	ld	a, _ss+8
      008882 26 0C            [ 1] 1276 	jrne	00110$
      008884 AE 01 53         [ 2] 1277 	ldw	x, #(_ss+9)
      008887 6F 01            [ 1] 1278 	clr	(0x1, x)
      008889 7F               [ 1] 1279 	clr	(x)
      00888A 35 01 01 52      [ 1] 1280 	mov	_ss+8, #0x01
      00888E 20 43            [ 2] 1281 	jra	00111$
      008890                       1282 00110$:
                                   1283 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
      008890 AE 01 4E         [ 2] 1284 	ldw	x, #(_ss+4)
      008893 90 93            [ 1] 1285 	ldw	y, x
      008895 90 EE 02         [ 2] 1286 	ldw	y, (0x2, y)
      008898 FE               [ 2] 1287 	ldw	x, (x)
      008899 17 15            [ 2] 1288 	ldw	(0x15, sp), y
      00889B 1F 13            [ 2] 1289 	ldw	(0x13, sp), x
      00889D 16 0D            [ 2] 1290 	ldw	y, (0x0d, sp)
      00889F 72 F2 15         [ 2] 1291 	subw	y, (0x15, sp)
      0088A2 7B 0C            [ 1] 1292 	ld	a, (0x0c, sp)
      0088A4 12 14            [ 1] 1293 	sbc	a, (0x14, sp)
      0088A6 6B 18            [ 1] 1294 	ld	(0x18, sp), a
      0088A8 7B 0B            [ 1] 1295 	ld	a, (0x0b, sp)
      0088AA 12 13            [ 1] 1296 	sbc	a, (0x13, sp)
      0088AC 6B 17            [ 1] 1297 	ld	(0x17, sp), a
                                   1298 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 416: dn = (int16_t)((d + BIT_H) >> BIT_SH);
      0088AE 72 A9 01 00      [ 2] 1299 	addw	y, #0x0100
      0088B2 1E 17            [ 2] 1300 	ldw	x, (0x17, sp)
      0088B4 24 01            [ 1] 1301 	jrnc	00247$
      0088B6 5C               [ 1] 1302 	incw	x
      0088B7                       1303 00247$:
      0088B7 4F               [ 1] 1304 	clr	a
      0088B8 5D               [ 2] 1305 	tnzw	x
      0088B9 2A 01            [ 1] 1306 	jrpl	00248$
      0088BB 4A               [ 1] 1307 	dec	a
      0088BC                       1308 00248$:
      0088BC 01               [ 1] 1309 	rrwa	x
      0088BD 90 01            [ 1] 1310 	rrwa	y
      0088BF 57               [ 2] 1311 	sraw	x
      0088C0 90 56            [ 2] 1312 	rrcw	y
                                   1313 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 417: if (dn > 0) ss.n = (uint16_t)(ss.n + dn);
      0088C2 93               [ 1] 1314 	ldw	x, y
      0088C3 A3 00 00         [ 2] 1315 	cpw	x, #0x0000
      0088C6 2D 0B            [ 1] 1316 	jrsle	00111$
      0088C8 CE 01 53         [ 2] 1317 	ldw	x, _ss+9
      0088CB 17 19            [ 2] 1318 	ldw	(0x19, sp), y
      0088CD 72 FB 19         [ 2] 1319 	addw	x, (0x19, sp)
      0088D0 CF 01 53         [ 2] 1320 	ldw	_ss+9, x
      0088D3                       1321 00111$:
                                   1322 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 419: ss.y_prev = (uint32_t)y;
      0088D3 AE 01 4E         [ 2] 1323 	ldw	x, #(_ss+4)
      0088D6 16 11            [ 2] 1324 	ldw	y, (0x11, sp)
      0088D8 EF 02            [ 2] 1325 	ldw	(0x2, x), y
      0088DA 16 0F            [ 2] 1326 	ldw	y, (0x0f, sp)
      0088DC FF               [ 2] 1327 	ldw	(x), y
                                   1328 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 420: yfa = map_raw(scan_fa);
      0088DD CE 00 09         [ 2] 1329 	ldw	x, _scan_fa+0
      0088E0 CD 84 63         [ 4] 1330 	call	_map_raw
      0088E3 1F 19            [ 2] 1331 	ldw	(0x19, sp), x
      0088E5 17 17            [ 2] 1332 	ldw	(0x17, sp), y
                                   1333 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 421: yfb = map_raw(scan_fb);
      0088E7 CE 00 0B         [ 2] 1334 	ldw	x, _scan_fb+0
      0088EA CD 84 63         [ 4] 1335 	call	_map_raw
      0088ED 17 11            [ 2] 1336 	ldw	(0x11, sp), y
                                   1337 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      0088EF C6 01 55         [ 1] 1338 	ld	a, _ss+11
                                   1339 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      0088F2 16 19            [ 2] 1340 	ldw	y, (0x19, sp)
      0088F4 17 15            [ 2] 1341 	ldw	(0x15, sp), y
                                   1342 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      0088F6 1F 17            [ 2] 1343 	ldw	(0x17, sp), x
                                   1344 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      0088F8 4D               [ 1] 1345 	tnz	a
      0088F9 27 3D            [ 1] 1346 	jreq	00113$
      0088FB CE 01 53         [ 2] 1347 	ldw	x, _ss+9
      0088FE 1F 19            [ 2] 1348 	ldw	(0x19, sp), x
      008900 CE 01 56         [ 2] 1349 	ldw	x, _ss+12
      008903 13 19            [ 2] 1350 	cpw	x, (0x19, sp)
      008905 26 31            [ 1] 1351 	jrne	00113$
                                   1352 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 423: base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
      008907 90 02            [ 1] 1353 	rlwa	y
      008909 9F               [ 1] 1354 	ld	a, xl
      00890A 90 01            [ 1] 1355 	rrwa	y
      00890C 9E               [ 1] 1356 	ld	a, xh
      00890D 5F               [ 1] 1357 	clrw	x
      00890E 61               [ 1] 1358 	exg	a, yl
      00890F 4F               [ 1] 1359 	clr	a
      008910 61               [ 1] 1360 	exg	a, yl
      008911 90 58            [ 2] 1361 	sllw	y
      008913 49               [ 1] 1362 	rlc	a
      008914 59               [ 2] 1363 	rlcw	x
      008915 72 A9 02 00      [ 2] 1364 	addw	y, #0x0200
      008919 A9 00            [ 1] 1365 	adc	a, #0x00
      00891B 01               [ 1] 1366 	rrwa	x
      00891C A9 00            [ 1] 1367 	adc	a, #0x00
                                   1368 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      00891E 17 19            [ 2] 1369 	ldw	(0x19, sp), y
      008920 1E 15            [ 2] 1370 	ldw	x, (0x15, sp)
      008922 72 F0 19         [ 2] 1371 	subw	x, (0x19, sp)
      008925 CF 01 58         [ 2] 1372 	ldw	_ss+14, x
                                   1373 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008928 1E 17            [ 2] 1374 	ldw	x, (0x17, sp)
      00892A 72 F0 19         [ 2] 1375 	subw	x, (0x19, sp)
      00892D CF 01 5A         [ 2] 1376 	ldw	_ss+16, x
                                   1377 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
      008930 55 00 0D 01 5C   [ 1] 1378 	mov	_ss+18, _scan_sfa+0
                                   1379 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 427: continue;
      008935 CC 88 0A         [ 2] 1380 	jp	00121$
      008938                       1381 00113$:
                                   1382 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 429: if (ss.pend) {
      008938 4D               [ 1] 1383 	tnz	a
      008939 26 03            [ 1] 1384 	jrne	00254$
      00893B CC 89 BC         [ 2] 1385 	jp	00118$
      00893E                       1386 00254$:
                                   1387 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      00893E CE 01 56         [ 2] 1388 	ldw	x, _ss+12
      008941 16 01            [ 2] 1389 	ldw	y, (0x01, sp)
      008943 90 FF            [ 2] 1390 	ldw	(y), x
                                   1391 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      008945 CE 01 53         [ 2] 1392 	ldw	x, _ss+9
      008948 A3 00 C0         [ 2] 1393 	cpw	x, #0x00c0
      00894B 24 04            [ 1] 1394 	jrnc	00128$
      00894D 1F 19            [ 2] 1395 	ldw	(0x19, sp), x
      00894F 20 05            [ 2] 1396 	jra	00129$
      008951                       1397 00128$:
      008951 AE 00 C0         [ 2] 1398 	ldw	x, #0x00c0
      008954 1F 19            [ 2] 1399 	ldw	(0x19, sp), x
      008956                       1400 00129$:
      008956 1E 03            [ 2] 1401 	ldw	x, (0x03, sp)
      008958 16 19            [ 2] 1402 	ldw	y, (0x19, sp)
      00895A FF               [ 2] 1403 	ldw	(x), y
                                   1404 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      00895B CE 01 58         [ 2] 1405 	ldw	x, _ss+14
      00895E 16 05            [ 2] 1406 	ldw	y, (0x05, sp)
      008960 90 FF            [ 2] 1407 	ldw	(y), x
      008962 CE 01 5A         [ 2] 1408 	ldw	x, _ss+16
      008965 16 07            [ 2] 1409 	ldw	y, (0x07, sp)
      008967 90 FF            [ 2] 1410 	ldw	(y), x
      008969 C6 01 5C         [ 1] 1411 	ld	a, _ss+18
      00896C 1E 09            [ 2] 1412 	ldw	x, (0x09, sp)
      00896E F7               [ 1] 1413 	ld	(x), a
                                   1414 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 433: if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
      00896F CE 01 53         [ 2] 1415 	ldw	x, _ss+9
      008972 1F 19            [ 2] 1416 	ldw	(0x19, sp), x
      008974 A3 00 C0         [ 2] 1417 	cpw	x, #0x00c0
      008977 25 0D            [ 1] 1418 	jrc	00116$
      008979 35 00 01 55      [ 1] 1419 	mov	_ss+11, #0x00
      00897D 35 01 01 5D      [ 1] 1420 	mov	_ss+19, #0x01
      008981 A6 01            [ 1] 1421 	ld	a, #0x01
      008983 CC 8A 31         [ 2] 1422 	jp	00126$
      008986                       1423 00116$:
                                   1424 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 434: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      008986 16 19            [ 2] 1425 	ldw	y, (0x19, sp)
      008988 5F               [ 1] 1426 	clrw	x
      008989 4F               [ 1] 1427 	clr	a
      00898A 48               [ 1] 1428 	sll	a
      00898B 90 59            [ 2] 1429 	rlcw	y
      00898D 59               [ 2] 1430 	rlcw	x
      00898E 6B 14            [ 1] 1431 	ld	(0x14, sp), a
      008990 72 A9 00 02      [ 2] 1432 	addw	y, #0x0002
      008994 17 12            [ 2] 1433 	ldw	(0x12, sp), y
      008996 4F               [ 1] 1434 	clr	a
      008997 A9 00            [ 1] 1435 	adc	a, #0x00
                                   1436 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 435: ss.p_k0 = ss.n;
      008999 AE 01 56         [ 2] 1437 	ldw	x, #(_ss+12)
      00899C 16 19            [ 2] 1438 	ldw	y, (0x19, sp)
      00899E FF               [ 2] 1439 	ldw	(x), y
                                   1440 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 436: ss.p_u = (int16_t)(yfa - (int32_t)base);
      00899F 16 13            [ 2] 1441 	ldw	y, (0x13, sp)
      0089A1 17 19            [ 2] 1442 	ldw	(0x19, sp), y
      0089A3 1E 15            [ 2] 1443 	ldw	x, (0x15, sp)
      0089A5 72 F0 19         [ 2] 1444 	subw	x, (0x19, sp)
      0089A8 CF 01 58         [ 2] 1445 	ldw	_ss+14, x
                                   1446 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 437: ss.p_v = (int16_t)(yfb - (int32_t)base);
      0089AB 1E 17            [ 2] 1447 	ldw	x, (0x17, sp)
      0089AD 72 F0 19         [ 2] 1448 	subw	x, (0x19, sp)
      0089B0 CF 01 5A         [ 2] 1449 	ldw	_ss+16, x
                                   1450 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 438: ss.p_fam = scan_sfa;
      0089B3 55 00 0D 01 5C   [ 1] 1451 	mov	_ss+18, _scan_sfa+0
                                   1452 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 439: return 1;
      0089B8 A6 01            [ 1] 1453 	ld	a, #0x01
      0089BA 20 75            [ 2] 1454 	jra	00126$
      0089BC                       1455 00118$:
                                   1456 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 441: if (ss.n >= NB) { ss.src_done = 1; break; }
      0089BC CE 01 53         [ 2] 1457 	ldw	x, _ss+9
      0089BF A3 00 C0         [ 2] 1458 	cpw	x, #0x00c0
      0089C2 25 06            [ 1] 1459 	jrc	00120$
      0089C4 35 01 01 5D      [ 1] 1460 	mov	_ss+19, #0x01
      0089C8 20 38            [ 2] 1461 	jra	00123$
      0089CA                       1462 00120$:
                                   1463 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 442: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      0089CA 90 5F            [ 1] 1464 	clrw	y
      0089CC 4F               [ 1] 1465 	clr	a
      0089CD 48               [ 1] 1466 	sll	a
      0089CE 59               [ 2] 1467 	rlcw	x
      0089CF 61               [ 1] 1468 	exg	a, yl
      0089D0 49               [ 1] 1469 	rlc	a
      0089D1 61               [ 1] 1470 	exg	a, yl
      0089D2 6B 14            [ 1] 1471 	ld	(0x14, sp), a
      0089D4 1C 00 02         [ 2] 1472 	addw	x, #0x0002
      0089D7 1F 12            [ 2] 1473 	ldw	(0x12, sp), x
      0089D9 4F               [ 1] 1474 	clr	a
      0089DA A9 00            [ 1] 1475 	adc	a, #0x00
                                   1476 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 443: ss.pend = 1;
      0089DC 35 01 01 55      [ 1] 1477 	mov	_ss+11, #0x01
                                   1478 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 444: ss.p_k0 = ss.n;
      0089E0 CE 01 53         [ 2] 1479 	ldw	x, _ss+9
      0089E3 CF 01 56         [ 2] 1480 	ldw	_ss+12, x
                                   1481 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 445: ss.p_u = (int16_t)(yfa - (int32_t)base);
      0089E6 16 13            [ 2] 1482 	ldw	y, (0x13, sp)
      0089E8 17 19            [ 2] 1483 	ldw	(0x19, sp), y
      0089EA 1E 15            [ 2] 1484 	ldw	x, (0x15, sp)
      0089EC 72 F0 19         [ 2] 1485 	subw	x, (0x19, sp)
      0089EF CF 01 58         [ 2] 1486 	ldw	_ss+14, x
                                   1487 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 446: ss.p_v = (int16_t)(yfb - (int32_t)base);
      0089F2 1E 17            [ 2] 1488 	ldw	x, (0x17, sp)
      0089F4 72 F0 19         [ 2] 1489 	subw	x, (0x19, sp)
      0089F7 CF 01 5A         [ 2] 1490 	ldw	_ss+16, x
                                   1491 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 447: ss.p_fam = scan_sfa;
      0089FA 55 00 0D 01 5C   [ 1] 1492 	mov	_ss+18, _scan_sfa+0
      0089FF CC 88 0A         [ 2] 1493 	jp	00121$
      008A02                       1494 00123$:
                                   1495 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 449: if (ss.pend) {
      008A02 C6 01 55         [ 1] 1496 	ld	a, _ss+11
      008A05 27 29            [ 1] 1497 	jreq	00125$
                                   1498 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 450: ss.pend = 0;
      008A07 35 00 01 55      [ 1] 1499 	mov	_ss+11, #0x00
                                   1500 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 451: out->k0 = ss.p_k0; out->k1 = NB;
      008A0B CE 01 56         [ 2] 1501 	ldw	x, _ss+12
      008A0E 16 01            [ 2] 1502 	ldw	y, (0x01, sp)
      008A10 90 FF            [ 2] 1503 	ldw	(y), x
      008A12 1E 03            [ 2] 1504 	ldw	x, (0x03, sp)
      008A14 90 AE 00 C0      [ 2] 1505 	ldw	y, #0x00c0
      008A18 FF               [ 2] 1506 	ldw	(x), y
                                   1507 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 452: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      008A19 CE 01 58         [ 2] 1508 	ldw	x, _ss+14
      008A1C 16 05            [ 2] 1509 	ldw	y, (0x05, sp)
      008A1E 90 FF            [ 2] 1510 	ldw	(y), x
      008A20 CE 01 5A         [ 2] 1511 	ldw	x, _ss+16
      008A23 16 07            [ 2] 1512 	ldw	y, (0x07, sp)
      008A25 90 FF            [ 2] 1513 	ldw	(y), x
      008A27 C6 01 5C         [ 1] 1514 	ld	a, _ss+18
      008A2A 1E 09            [ 2] 1515 	ldw	x, (0x09, sp)
      008A2C F7               [ 1] 1516 	ld	(x), a
                                   1517 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 453: return 1;
      008A2D A6 01            [ 1] 1518 	ld	a, #0x01
                                   1519 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 455: return 0;
      008A2F 21                    1520 	.byte 0x21
      008A30                       1521 00125$:
      008A30 4F               [ 1] 1522 	clr	a
      008A31                       1523 00126$:
                                   1524 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 456: }
      008A31 5B 1C            [ 2] 1525 	addw	sp, #28
      008A33 81               [ 4] 1526 	ret
                                   1527 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 460: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
                                   1528 ;	-----------------------------------------
                                   1529 ;	 function a_bounds
                                   1530 ;	-----------------------------------------
      008A34                       1531 _a_bounds:
      008A34 52 0C            [ 2] 1532 	sub	sp, #12
      008A36 1F 09            [ 2] 1533 	ldw	(0x09, sp), x
                                   1534 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 462: uint16_t t, e = (k1 < NB) ? k1 : NB;
      008A38 1E 0F            [ 2] 1535 	ldw	x, (0x0f, sp)
      008A3A A3 00 C0         [ 2] 1536 	cpw	x, #0x00c0
      008A3D 25 03            [ 1] 1537 	jrc	00117$
      008A3F AE 00 C0         [ 2] 1538 	ldw	x, #0x00c0
      008A42                       1539 00117$:
      008A42 1F 01            [ 2] 1540 	ldw	(0x01, sp), x
                                   1541 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 463: *amin = 0;
      008A44 16 11            [ 2] 1542 	ldw	y, (0x11, sp)
      008A46 17 03            [ 2] 1543 	ldw	(0x03, sp), y
      008A48 93               [ 1] 1544 	ldw	x, y
      008A49 6F 01            [ 1] 1545 	clr	(0x1, x)
      008A4B 7F               [ 1] 1546 	clr	(x)
                                   1547 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 464: *amax = (int16_t)(k1 - k0);
      008A4C 16 13            [ 2] 1548 	ldw	y, (0x13, sp)
      008A4E 17 05            [ 2] 1549 	ldw	(0x05, sp), y
      008A50 16 0F            [ 2] 1550 	ldw	y, (0x0f, sp)
      008A52 72 F2 09         [ 2] 1551 	subw	y, (0x09, sp)
      008A55 1E 05            [ 2] 1552 	ldw	x, (0x05, sp)
      008A57 FF               [ 2] 1553 	ldw	(x), y
                                   1554 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      008A58 16 09            [ 2] 1555 	ldw	y, (0x09, sp)
      008A5A 17 0B            [ 2] 1556 	ldw	(0x0b, sp), y
      008A5C                       1557 00112$:
                                   1558 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 466: int8_t kb = known_bit(t);
      008A5C 1E 0B            [ 2] 1559 	ldw	x, (0x0b, sp)
      008A5E 13 01            [ 2] 1560 	cpw	x, (0x01, sp)
      008A60 24 35            [ 1] 1561 	jrnc	00114$
      008A62 CD 81 47         [ 4] 1562 	call	_known_bit
                                   1563 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      008A65 1E 0B            [ 2] 1564 	ldw	x, (0x0b, sp)
      008A67 72 F0 09         [ 2] 1565 	subw	x, (0x09, sp)
                                   1566 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 467: if (kb == 1) {
      008A6A A1 01            [ 1] 1567 	cp	a, #0x01
      008A6C 26 11            [ 1] 1568 	jrne	00108$
                                   1569 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      008A6E 5C               [ 1] 1570 	incw	x
                                   1571 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 469: if (m > *amin) *amin = m;
      008A6F 16 03            [ 2] 1572 	ldw	y, (0x03, sp)
      008A71 90 FE            [ 2] 1573 	ldw	y, (y)
      008A73 17 07            [ 2] 1574 	ldw	(0x07, sp), y
      008A75 13 07            [ 2] 1575 	cpw	x, (0x07, sp)
      008A77 2D 17            [ 1] 1576 	jrsle	00113$
      008A79 16 03            [ 2] 1577 	ldw	y, (0x03, sp)
      008A7B 90 FF            [ 2] 1578 	ldw	(y), x
      008A7D 20 11            [ 2] 1579 	jra	00113$
      008A7F                       1580 00108$:
                                   1581 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 470: } else if (kb == 0) {
      008A7F 4D               [ 1] 1582 	tnz	a
      008A80 26 0E            [ 1] 1583 	jrne	00113$
                                   1584 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 471: int16_t m = (int16_t)(t - k0);
                                   1585 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 472: if (m < *amax) *amax = m;
      008A82 16 05            [ 2] 1586 	ldw	y, (0x05, sp)
      008A84 90 FE            [ 2] 1587 	ldw	y, (y)
      008A86 17 07            [ 2] 1588 	ldw	(0x07, sp), y
      008A88 13 07            [ 2] 1589 	cpw	x, (0x07, sp)
      008A8A 2E 04            [ 1] 1590 	jrsge	00113$
      008A8C 16 05            [ 2] 1591 	ldw	y, (0x05, sp)
      008A8E 90 FF            [ 2] 1592 	ldw	(y), x
      008A90                       1593 00113$:
                                   1594 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      008A90 1E 0B            [ 2] 1595 	ldw	x, (0x0b, sp)
      008A92 5C               [ 1] 1596 	incw	x
      008A93 1F 0B            [ 2] 1597 	ldw	(0x0b, sp), x
      008A95 20 C5            [ 2] 1598 	jra	00112$
      008A97                       1599 00114$:
                                   1600 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 475: }
      008A97 1E 0D            [ 2] 1601 	ldw	x, (13, sp)
      008A99 5B 14            [ 2] 1602 	addw	sp, #20
      008A9B FC               [ 2] 1603 	jp	(x)
                                   1604 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 479: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1605 ;	-----------------------------------------
                                   1606 ;	 function label_interval
                                   1607 ;	-----------------------------------------
      008A9C                       1608 _label_interval:
      008A9C 52 08            [ 2] 1609 	sub	sp, #8
                                   1610 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 482: int16_t L = (int16_t)(k1 - k0);
      008A9E 50               [ 2] 1611 	negw	x
      008A9F 72 FB 0B         [ 2] 1612 	addw	x, (0x0b, sp)
                                   1613 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 485: if (a == 0) { off = 0; cls = 0; }
      008AA2 16 11            [ 2] 1614 	ldw	y, (0x11, sp)
      008AA4 26 08            [ 1] 1615 	jrne	00114$
      008AA6 5F               [ 1] 1616 	clrw	x
      008AA7 1F 07            [ 2] 1617 	ldw	(0x07, sp), x
      008AA9 0F 06            [ 1] 1618 	clr	(0x06, sp)
      008AAB CC 8B 36         [ 2] 1619 	jp	00115$
      008AAE                       1620 00114$:
                                   1621 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 486: else if (a == L) { off = (int16_t)((L - 1) * BIT_U); cls = 1; }
      008AAE 13 11            [ 2] 1622 	cpw	x, (0x11, sp)
      008AB0 26 0C            [ 1] 1623 	jrne	00111$
      008AB2 5A               [ 2] 1624 	decw	x
      008AB3 4F               [ 1] 1625 	clr	a
      008AB4 02               [ 1] 1626 	rlwa	x
      008AB5 58               [ 2] 1627 	sllw	x
      008AB6 1F 07            [ 2] 1628 	ldw	(0x07, sp), x
      008AB8 A6 01            [ 1] 1629 	ld	a, #0x01
      008ABA 6B 06            [ 1] 1630 	ld	(0x06, sp), a
      008ABC 20 78            [ 2] 1631 	jra	00115$
      008ABE                       1632 00111$:
                                   1633 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 488: mid = (int16_t)((u + v) >> 1);
      008ABE 16 0D            [ 2] 1634 	ldw	y, (0x0d, sp)
      008AC0 72 F9 0F         [ 2] 1635 	addw	y, (0x0f, sp)
      008AC3 90 57            [ 2] 1636 	sraw	y
                                   1637 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 489: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
      008AC5 1E 11            [ 2] 1638 	ldw	x, (0x11, sp)
      008AC7 1F 07            [ 2] 1639 	ldw	(0x07, sp), x
      008AC9 5A               [ 2] 1640 	decw	x
      008ACA 41               [ 1] 1641 	exg	a, xl
      008ACB 6B 01            [ 1] 1642 	ld	(0x01, sp), a
      008ACD 41               [ 1] 1643 	exg	a, xl
      008ACE 0F 02            [ 1] 1644 	clr	(0x02, sp)
      008AD0 08 02            [ 1] 1645 	sll	(0x02, sp)
      008AD2 09 01            [ 1] 1646 	rlc	(0x01, sp)
      008AD4 1E 01            [ 2] 1647 	ldw	x, (0x01, sp)
      008AD6 1C 01 34         [ 2] 1648 	addw	x, #0x0134
      008AD9 1F 05            [ 2] 1649 	ldw	(0x05, sp), x
      008ADB 93               [ 1] 1650 	ldw	x, y
      008ADC 72 F0 05         [ 2] 1651 	subw	x, (0x05, sp)
                                   1652 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 490: if (d1 < 0) d1 = (int16_t)-d1;
      008ADF 1F 05            [ 2] 1653 	ldw	(0x05, sp), x
      008AE1 5D               [ 2] 1654 	tnzw	x
      008AE2 2A 07            [ 1] 1655 	jrpl	00102$
      008AE4 00 06            [ 1] 1656 	neg	(0x06, sp)
      008AE6 4F               [ 1] 1657 	clr	a
      008AE7 12 05            [ 1] 1658 	sbc	a, (0x05, sp)
      008AE9 6B 05            [ 1] 1659 	ld	(0x05, sp), a
      008AEB                       1660 00102$:
                                   1661 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 491: d0 = (int16_t)(mid - (a * BIT_U + H0P));
      008AEB 7B 08            [ 1] 1662 	ld	a, (0x08, sp)
      008AED 6B 03            [ 1] 1663 	ld	(0x03, sp), a
      008AEF 0F 04            [ 1] 1664 	clr	(0x04, sp)
      008AF1 08 04            [ 1] 1665 	sll	(0x04, sp)
      008AF3 09 03            [ 1] 1666 	rlc	(0x03, sp)
      008AF5 1E 03            [ 2] 1667 	ldw	x, (0x03, sp)
      008AF7 1C 00 9A         [ 2] 1668 	addw	x, #0x009a
      008AFA 1F 07            [ 2] 1669 	ldw	(0x07, sp), x
      008AFC 72 F2 07         [ 2] 1670 	subw	y, (0x07, sp)
                                   1671 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 492: if (d0 < 0) d0 = (int16_t)-d0;
      008AFF 17 07            [ 2] 1672 	ldw	(0x07, sp), y
      008B01 93               [ 1] 1673 	ldw	x, y
      008B02 5D               [ 2] 1674 	tnzw	x
      008B03 2A 07            [ 1] 1675 	jrpl	00104$
      008B05 00 08            [ 1] 1676 	neg	(0x08, sp)
      008B07 4F               [ 1] 1677 	clr	a
      008B08 12 07            [ 1] 1678 	sbc	a, (0x07, sp)
      008B0A 6B 07            [ 1] 1679 	ld	(0x07, sp), a
      008B0C                       1680 00104$:
                                   1681 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 493: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
      008B0C 1E 07            [ 2] 1682 	ldw	x, (0x07, sp)
      008B0E 13 05            [ 2] 1683 	cpw	x, (0x05, sp)
      008B10 2E 03            [ 1] 1684 	jrsge	00118$
      008B12 1E 07            [ 2] 1685 	ldw	x, (0x07, sp)
      008B14 C5                    1686 	.byte 0xc5
      008B15                       1687 00118$:
      008B15 1E 05            [ 2] 1688 	ldw	x, (0x05, sp)
      008B17                       1689 00119$:
      008B17 A3 00 F6         [ 2] 1690 	cpw	x, #0x00f6
      008B1A 2D 04            [ 1] 1691 	jrsle	00106$
      008B1C A6 FF            [ 1] 1692 	ld	a, #0xff
      008B1E 20 28            [ 2] 1693 	jra	00116$
      008B20                       1694 00106$:
                                   1695 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 494: if (d1 <= d0) { off = (int16_t)((a - 1) * BIT_U); cls = 1; }
      008B20 1E 05            [ 2] 1696 	ldw	x, (0x05, sp)
      008B22 13 07            [ 2] 1697 	cpw	x, (0x07, sp)
      008B24 2C 0A            [ 1] 1698 	jrsgt	00108$
      008B26 16 01            [ 2] 1699 	ldw	y, (0x01, sp)
      008B28 17 07            [ 2] 1700 	ldw	(0x07, sp), y
      008B2A A6 01            [ 1] 1701 	ld	a, #0x01
      008B2C 6B 06            [ 1] 1702 	ld	(0x06, sp), a
      008B2E 20 06            [ 2] 1703 	jra	00115$
      008B30                       1704 00108$:
                                   1705 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 495: else          { off = (int16_t)(a * BIT_U);       cls = 0; }
      008B30 16 03            [ 2] 1706 	ldw	y, (0x03, sp)
      008B32 17 07            [ 2] 1707 	ldw	(0x07, sp), y
      008B34 0F 06            [ 1] 1708 	clr	(0x06, sp)
      008B36                       1709 00115$:
                                   1710 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 497: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      008B36 1E 13            [ 2] 1711 	ldw	x, (0x13, sp)
      008B38 16 0D            [ 2] 1712 	ldw	y, (0x0d, sp)
      008B3A 72 F2 07         [ 2] 1713 	subw	y, (0x07, sp)
      008B3D FF               [ 2] 1714 	ldw	(x), y
      008B3E 1E 15            [ 2] 1715 	ldw	x, (0x15, sp)
      008B40 16 0F            [ 2] 1716 	ldw	y, (0x0f, sp)
      008B42 72 F2 07         [ 2] 1717 	subw	y, (0x07, sp)
      008B45 FF               [ 2] 1718 	ldw	(x), y
                                   1719 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 498: return cls;
      008B46 7B 06            [ 1] 1720 	ld	a, (0x06, sp)
      008B48                       1721 00116$:
                                   1722 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 499: }
      008B48 1E 09            [ 2] 1723 	ldw	x, (9, sp)
      008B4A 5B 16            [ 2] 1724 	addw	sp, #22
      008B4C FC               [ 2] 1725 	jp	(x)
                                   1726 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 501: static void cal_cloud(int16_t u, uint8_t fam)
                                   1727 ;	-----------------------------------------
                                   1728 ;	 function cal_cloud
                                   1729 ;	-----------------------------------------
      008B4D                       1730 _cal_cloud:
      008B4D 89               [ 2] 1731 	pushw	x
                                   1732 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 505: if (fam != 5 && fam != 6) return;
      008B4E A1 05            [ 1] 1733 	cp	a, #0x05
      008B50 27 04            [ 1] 1734 	jreq	00102$
      008B52 A1 06            [ 1] 1735 	cp	a, #0x06
      008B54 26 3C            [ 1] 1736 	jrne	00111$
      008B56                       1737 00102$:
                                   1738 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 506: if (u < 0) return;
      008B56 5D               [ 2] 1739 	tnzw	x
      008B57 2B 39            [ 1] 1740 	jrmi	00111$
                                   1741 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 507: f = (uint8_t)(fam - 5);
      008B59 A0 05            [ 1] 1742 	sub	a, #0x05
      008B5B 90 97            [ 1] 1743 	ld	yl, a
                                   1744 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 508: x = (int16_t)(u & (BIT_U - 1));
      008B5D 9E               [ 1] 1745 	ld	a, xh
      008B5E A4 01            [ 1] 1746 	and	a, #0x01
      008B60 95               [ 1] 1747 	ld	xh, a
      008B61 1F 01            [ 2] 1748 	ldw	(0x01, sp), x
                                   1749 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 509: d = (int16_t)(x - c_c0[f]);
      008B63 93               [ 1] 1750 	ldw	x, y
      008B64 4F               [ 1] 1751 	clr	a
      008B65 95               [ 1] 1752 	ld	xh, a
      008B66 58               [ 2] 1753 	sllw	x
      008B67 DE 00 DC         [ 2] 1754 	ldw	x, (_c_c0+0, x)
      008B6A 50               [ 2] 1755 	negw	x
      008B6B 72 FB 01         [ 2] 1756 	addw	x, (0x01, sp)
                                   1757 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 510: if (d >= -EPS_HIST && d < EPS_HIST) {
      008B6E A3 FF C0         [ 2] 1758 	cpw	x, #0xffc0
      008B71 2F 1F            [ 1] 1759 	jrslt	00111$
      008B73 A3 00 40         [ 2] 1760 	cpw	x, #0x0040
      008B76 2E 1A            [ 1] 1761 	jrsge	00111$
                                   1762 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 511: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
      008B78 1C 00 40         [ 2] 1763 	addw	x, #0x0040
      008B7B 57               [ 2] 1764 	sraw	x
                                   1765 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 512: if (c_hist[f][b] < 255) c_hist[f][b]++;
      008B7C A6 40            [ 1] 1766 	ld	a, #0x40
      008B7E 90 42            [ 4] 1767 	mul	y, a
      008B80 72 A9 00 4C      [ 2] 1768 	addw	y, #(_c_hist+0)
      008B84 17 01            [ 2] 1769 	ldw	(0x01, sp), y
      008B86 4F               [ 1] 1770 	clr	a
      008B87 95               [ 1] 1771 	ld	xh, a
      008B88 72 FB 01         [ 2] 1772 	addw	x, (0x01, sp)
      008B8B F6               [ 1] 1773 	ld	a, (x)
      008B8C A1 FF            [ 1] 1774 	cp	a, #0xff
      008B8E 24 02            [ 1] 1775 	jrnc	00111$
      008B90 4C               [ 1] 1776 	inc	a
      008B91 F7               [ 1] 1777 	ld	(x), a
      008B92                       1778 00111$:
                                   1779 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 514: }
      008B92 85               [ 2] 1780 	popw	x
      008B93 81               [ 4] 1781 	ret
                                   1782 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 516: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1783 ;	-----------------------------------------
                                   1784 ;	 function cal_add
                                   1785 ;	-----------------------------------------
      008B94                       1786 _cal_add:
      008B94 52 0A            [ 2] 1787 	sub	sp, #10
      008B96 51               [ 1] 1788 	exgw	x, y
                                   1789 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 520: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
      008B97 96               [ 1] 1790 	ldw	x, sp
      008B98 1C 00 03         [ 2] 1791 	addw	x, #3
      008B9B 89               [ 2] 1792 	pushw	x
      008B9C 96               [ 1] 1793 	ldw	x, sp
      008B9D 1C 00 03         [ 2] 1794 	addw	x, #3
      008BA0 89               [ 2] 1795 	pushw	x
      008BA1 1E 18            [ 2] 1796 	ldw	x, (0x18, sp)
      008BA3 89               [ 2] 1797 	pushw	x
      008BA4 1E 17            [ 2] 1798 	ldw	x, (0x17, sp)
      008BA6 89               [ 2] 1799 	pushw	x
      008BA7 1E 17            [ 2] 1800 	ldw	x, (0x17, sp)
      008BA9 89               [ 2] 1801 	pushw	x
      008BAA 1E 17            [ 2] 1802 	ldw	x, (0x17, sp)
      008BAC 89               [ 2] 1803 	pushw	x
      008BAD 93               [ 1] 1804 	ldw	x, y
      008BAE CD 8A 9C         [ 4] 1805 	call	_label_interval
                                   1806 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 521: if (cls < 0) return;
      008BB1 6B 08            [ 1] 1807 	ld	(0x08, sp), a
      008BB3 2A 03            [ 1] 1808 	jrpl	00102$
      008BB5 CC 8C 89         [ 2] 1809 	jp	00129$
      008BB8                       1810 00102$:
                                   1811 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 523: uint8_t ci = (uint8_t)cls;
      008BB8 7B 08            [ 1] 1812 	ld	a, (0x08, sp)
                                   1813 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 524: if (lo > c_lo[ci]) c_lo[ci] = lo;
      008BBA 5F               [ 1] 1814 	clrw	x
      008BBB 97               [ 1] 1815 	ld	xl, a
      008BBC 58               [ 2] 1816 	sllw	x
      008BBD 1F 09            [ 2] 1817 	ldw	(0x09, sp), x
      008BBF 90 93            [ 1] 1818 	ldw	y, x
      008BC1 72 A9 00 3C      [ 2] 1819 	addw	y, #(_c_lo+0)
      008BC5 93               [ 1] 1820 	ldw	x, y
      008BC6 FE               [ 2] 1821 	ldw	x, (x)
      008BC7 13 01            [ 2] 1822 	cpw	x, (0x01, sp)
      008BC9 2E 04            [ 1] 1823 	jrsge	00104$
      008BCB 93               [ 1] 1824 	ldw	x, y
      008BCC 16 01            [ 2] 1825 	ldw	y, (0x01, sp)
      008BCE FF               [ 2] 1826 	ldw	(x), y
      008BCF                       1827 00104$:
                                   1828 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 525: if (hi < c_hi[ci]) c_hi[ci] = hi;
      008BCF 16 09            [ 2] 1829 	ldw	y, (0x09, sp)
      008BD1 72 A9 00 40      [ 2] 1830 	addw	y, #(_c_hi+0)
      008BD5 93               [ 1] 1831 	ldw	x, y
      008BD6 FE               [ 2] 1832 	ldw	x, (x)
      008BD7 1F 09            [ 2] 1833 	ldw	(0x09, sp), x
      008BD9 1E 03            [ 2] 1834 	ldw	x, (0x03, sp)
      008BDB 13 09            [ 2] 1835 	cpw	x, (0x09, sp)
      008BDD 2E 04            [ 1] 1836 	jrsge	00106$
      008BDF 93               [ 1] 1837 	ldw	x, y
      008BE0 16 03            [ 2] 1838 	ldw	y, (0x03, sp)
      008BE2 FF               [ 2] 1839 	ldw	(x), y
      008BE3                       1840 00106$:
                                   1841 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 526: if (c_n[ci] < 255) c_n[ci]++;
      008BE3 5F               [ 1] 1842 	clrw	x
      008BE4 97               [ 1] 1843 	ld	xl, a
      008BE5 1C 00 44         [ 2] 1844 	addw	x, #(_c_n+0)
      008BE8 F6               [ 1] 1845 	ld	a, (x)
      008BE9 A1 FF            [ 1] 1846 	cp	a, #0xff
      008BEB 24 02            [ 1] 1847 	jrnc	00108$
      008BED 4C               [ 1] 1848 	inc	a
      008BEE F7               [ 1] 1849 	ld	(x), a
      008BEF                       1850 00108$:
                                   1851 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if ((fam == 5 || fam == 6) && lo >= 0) {
      008BEF 7B 13            [ 1] 1852 	ld	a, (0x13, sp)
      008BF1 A1 05            [ 1] 1853 	cp	a, #0x05
      008BF3 27 09            [ 1] 1854 	jreq	00128$
      008BF5 7B 13            [ 1] 1855 	ld	a, (0x13, sp)
      008BF7 A1 06            [ 1] 1856 	cp	a, #0x06
      008BF9 27 03            [ 1] 1857 	jreq	00244$
      008BFB CC 8C 89         [ 2] 1858 	jp	00129$
      008BFE                       1859 00244$:
      008BFE                       1860 00128$:
      008BFE 1E 01            [ 2] 1861 	ldw	x, (0x01, sp)
      008C00 2A 03            [ 1] 1862 	jrpl	00245$
      008C02 CC 8C 89         [ 2] 1863 	jp	00129$
      008C05                       1864 00245$:
                                   1865 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: uint8_t f = (uint8_t)(fam - 5);
      008C05 7B 13            [ 1] 1866 	ld	a, (0x13, sp)
      008C07 A0 05            [ 1] 1867 	sub	a, #0x05
                                   1868 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 530: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
      008C09 88               [ 1] 1869 	push	a
      008C0A 41               [ 1] 1870 	exg	a, xl
      008C0B 6B 08            [ 1] 1871 	ld	(0x08, sp), a
      008C0D 41               [ 1] 1872 	exg	a, xl
      008C0E 9E               [ 1] 1873 	ld	a, xh
      008C0F A4 01            [ 1] 1874 	and	a, #0x01
      008C11 6B 07            [ 1] 1875 	ld	(0x07, sp), a
      008C13 84               [ 1] 1876 	pop	a
      008C14 5F               [ 1] 1877 	clrw	x
      008C15 97               [ 1] 1878 	ld	xl, a
      008C16 58               [ 2] 1879 	sllw	x
      008C17 90 93            [ 1] 1880 	ldw	y, x
      008C19 DE 00 DC         [ 2] 1881 	ldw	x, (_c_c0+0, x)
      008C1C 1F 09            [ 2] 1882 	ldw	(0x09, sp), x
      008C1E 1E 06            [ 2] 1883 	ldw	x, (0x06, sp)
      008C20 72 F0 09         [ 2] 1884 	subw	x, (0x09, sp)
                                   1885 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 531: if (d >= -EPS_HIST && d < EPS_HIST) {
      008C23 1F 05            [ 2] 1886 	ldw	(0x05, sp), x
      008C25 A3 FF C0         [ 2] 1887 	cpw	x, #0xffc0
      008C28 2F 5F            [ 1] 1888 	jrslt	00129$
      008C2A 1E 05            [ 2] 1889 	ldw	x, (0x05, sp)
      008C2C A3 00 40         [ 2] 1890 	cpw	x, #0x0040
      008C2F 2E 58            [ 1] 1891 	jrsge	00129$
                                   1892 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 532: if (cls == 0) {
      008C31 0D 08            [ 1] 1893 	tnz	(0x08, sp)
      008C33 26 26            [ 1] 1894 	jrne	00120$
                                   1895 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 533: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
      008C35 93               [ 1] 1896 	ldw	x, y
      008C36 1C 00 CC         [ 2] 1897 	addw	x, #(_c_labx0+0)
      008C39 1F 09            [ 2] 1898 	ldw	(0x09, sp), x
      008C3B FE               [ 2] 1899 	ldw	x, (x)
      008C3C 13 05            [ 2] 1900 	cpw	x, (0x05, sp)
      008C3E 2E 0B            [ 1] 1901 	jrsge	00112$
      008C40 90 DF 00 D4      [ 2] 1902 	ldw	((_c_labx0b+0), y), x
      008C44 1E 09            [ 2] 1903 	ldw	x, (0x09, sp)
      008C46 16 05            [ 2] 1904 	ldw	y, (0x05, sp)
      008C48 FF               [ 2] 1905 	ldw	(x), y
      008C49 20 3E            [ 2] 1906 	jra	00129$
      008C4B                       1907 00112$:
                                   1908 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 534: else if (d > c_labx0b[f]) c_labx0b[f] = d;
      008C4B 72 A9 00 D4      [ 2] 1909 	addw	y, #(_c_labx0b+0)
      008C4F 93               [ 1] 1910 	ldw	x, y
      008C50 FE               [ 2] 1911 	ldw	x, (x)
      008C51 13 05            [ 2] 1912 	cpw	x, (0x05, sp)
      008C53 2E 34            [ 1] 1913 	jrsge	00129$
      008C55 93               [ 1] 1914 	ldw	x, y
      008C56 16 05            [ 2] 1915 	ldw	y, (0x05, sp)
      008C58 FF               [ 2] 1916 	ldw	(x), y
      008C59 20 2E            [ 2] 1917 	jra	00129$
      008C5B                       1918 00120$:
                                   1919 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 536: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
      008C5B 93               [ 1] 1920 	ldw	x, y
      008C5C 1C 00 D0         [ 2] 1921 	addw	x, #(_c_labx1+0)
      008C5F 1F 07            [ 2] 1922 	ldw	(0x07, sp), x
      008C61 FE               [ 2] 1923 	ldw	x, (x)
      008C62 1F 09            [ 2] 1924 	ldw	(0x09, sp), x
      008C64 1E 05            [ 2] 1925 	ldw	x, (0x05, sp)
      008C66 13 09            [ 2] 1926 	cpw	x, (0x09, sp)
      008C68 2E 0D            [ 1] 1927 	jrsge	00117$
      008C6A 93               [ 1] 1928 	ldw	x, y
      008C6B 16 09            [ 2] 1929 	ldw	y, (0x09, sp)
      008C6D DF 00 D8         [ 2] 1930 	ldw	((_c_labx1b+0), x), y
      008C70 1E 07            [ 2] 1931 	ldw	x, (0x07, sp)
      008C72 16 05            [ 2] 1932 	ldw	y, (0x05, sp)
      008C74 FF               [ 2] 1933 	ldw	(x), y
      008C75 20 12            [ 2] 1934 	jra	00129$
      008C77                       1935 00117$:
                                   1936 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 537: else if (d < c_labx1b[f]) c_labx1b[f] = d;
      008C77 72 A9 00 D8      [ 2] 1937 	addw	y, #(_c_labx1b+0)
      008C7B 93               [ 1] 1938 	ldw	x, y
      008C7C FE               [ 2] 1939 	ldw	x, (x)
      008C7D 1F 09            [ 2] 1940 	ldw	(0x09, sp), x
      008C7F 1E 05            [ 2] 1941 	ldw	x, (0x05, sp)
      008C81 13 09            [ 2] 1942 	cpw	x, (0x09, sp)
      008C83 2E 04            [ 1] 1943 	jrsge	00129$
      008C85 93               [ 1] 1944 	ldw	x, y
      008C86 16 05            [ 2] 1945 	ldw	y, (0x05, sp)
      008C88 FF               [ 2] 1946 	ldw	(x), y
      008C89                       1947 00129$:
                                   1948 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 541: }
      008C89 1E 0B            [ 2] 1949 	ldw	x, (11, sp)
      008C8B 5B 15            [ 2] 1950 	addw	sp, #21
      008C8D FC               [ 2] 1951 	jp	(x)
                                   1952 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 544: static uint8_t theta56(uint8_t f, int16_t *theta_out)
                                   1953 ;	-----------------------------------------
                                   1954 ;	 function theta56
                                   1955 ;	-----------------------------------------
      008C8E                       1956 _theta56:
      008C8E 52 28            [ 2] 1957 	sub	sp, #40
      008C90 1F 25            [ 2] 1958 	ldw	(0x25, sp), x
                                   1959 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 546: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
      008C92 5F               [ 1] 1960 	clrw	x
      008C93 97               [ 1] 1961 	ld	xl, a
      008C94 58               [ 2] 1962 	sllw	x
      008C95 1F 05            [ 2] 1963 	ldw	(0x05, sp), x
      008C97 DE 00 CC         [ 2] 1964 	ldw	x, (_c_labx0+0, x)
      008C9A 16 05            [ 2] 1965 	ldw	y, (0x05, sp)
      008C9C 90 DE 00 D0      [ 2] 1966 	ldw	y, (_c_labx1+0, y)
                                   1967 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 547: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
      008CA0 1F 07            [ 2] 1968 	ldw	(0x07, sp), x
      008CA2 A3 C0 00         [ 2] 1969 	cpw	x, #0xc000
      008CA5 2C 04            [ 1] 1970 	jrsgt	00483$
      008CA7 0F 09            [ 1] 1971 	clr	(0x09, sp)
      008CA9 20 06            [ 2] 1972 	jra	00484$
      008CAB                       1973 00483$:
      008CAB 88               [ 1] 1974 	push	a
      008CAC A6 01            [ 1] 1975 	ld	a, #0x01
      008CAE 6B 0A            [ 1] 1976 	ld	(0x0a, sp), a
      008CB0 84               [ 1] 1977 	pop	a
      008CB1                       1978 00484$:
      008CB1 17 0A            [ 2] 1979 	ldw	(0x0a, sp), y
      008CB3 93               [ 1] 1980 	ldw	x, y
      008CB4 A3 3F FF         [ 2] 1981 	cpw	x, #0x3fff
      008CB7 2F 04            [ 1] 1982 	jrslt	00485$
      008CB9 0F 0C            [ 1] 1983 	clr	(0x0c, sp)
      008CBB 20 06            [ 2] 1984 	jra	00486$
      008CBD                       1985 00485$:
      008CBD 88               [ 1] 1986 	push	a
      008CBE A6 01            [ 1] 1987 	ld	a, #0x01
      008CC0 6B 0D            [ 1] 1988 	ld	(0x0d, sp), a
      008CC2 84               [ 1] 1989 	pop	a
      008CC3                       1990 00486$:
                                   1991 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 548: int16_t zlo = (int16_t)(x0 + 1);
      008CC3 1E 07            [ 2] 1992 	ldw	x, (0x07, sp)
      008CC5 5C               [ 1] 1993 	incw	x
      008CC6 1F 0D            [ 2] 1994 	ldw	(0x0d, sp), x
                                   1995 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 549: int16_t zhi = x1;
      008CC8 17 0F            [ 2] 1996 	ldw	(0x0f, sp), y
                                   1997 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 550: int16_t theta = 0;
      008CCA 5F               [ 1] 1998 	clrw	x
      008CCB 1F 11            [ 2] 1999 	ldw	(0x11, sp), x
                                   2000 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 551: uint8_t have_theta = 0;
      008CCD 0F 13            [ 1] 2001 	clr	(0x13, sp)
                                   2002 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 552: int16_t top = 0;
      008CCF 5F               [ 1] 2003 	clrw	x
      008CD0 1F 14            [ 2] 2004 	ldw	(0x14, sp), x
                                   2005 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 553: uint8_t have_top = 0, clear1 = 0;
      008CD2 0F 16            [ 1] 2006 	clr	(0x16, sp)
      008CD4 0F 17            [ 1] 2007 	clr	(0x17, sp)
                                   2008 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 555: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
      008CD6 AE FF E0         [ 2] 2009 	ldw	x, #0xffe0
      008CD9 13 0D            [ 2] 2010 	cpw	x, (0x0d, sp)
      008CDB 2F 02            [ 1] 2011 	jrslt	00102$
      008CDD 1F 0D            [ 2] 2012 	ldw	(0x0d, sp), x
      008CDF                       2013 00102$:
                                   2014 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 556: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
      008CDF 1E 0F            [ 2] 2015 	ldw	x, (0x0f, sp)
      008CE1 A3 00 20         [ 2] 2016 	cpw	x, #0x0020
      008CE4 2D 05            [ 1] 2017 	jrsle	00104$
      008CE6 AE 00 20         [ 2] 2018 	ldw	x, #0x0020
      008CE9 1F 0F            [ 2] 2019 	ldw	(0x0f, sp), x
      008CEB                       2020 00104$:
                                   2021 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008CEB 41               [ 1] 2022 	exg	a, xl
      008CEC A6 40            [ 1] 2023 	ld	a, #0x40
      008CEE 41               [ 1] 2024 	exg	a, xl
      008CEF 42               [ 4] 2025 	mul	x, a
      008CF0 1F 18            [ 2] 2026 	ldw	(0x18, sp), x
                                   2027 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 557: if (zlo < zhi) {
      008CF2 1E 0D            [ 2] 2028 	ldw	x, (0x0d, sp)
      008CF4 13 0F            [ 2] 2029 	cpw	x, (0x0f, sp)
      008CF6 2F 03            [ 1] 2030 	jrslt	00489$
      008CF8 CC 8E 00         [ 2] 2031 	jp	00126$
      008CFB                       2032 00489$:
                                   2033 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 558: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
      008CFB 1E 0D            [ 2] 2034 	ldw	x, (0x0d, sp)
      008CFD 1C 00 40         [ 2] 2035 	addw	x, #0x0040
      008D00 57               [ 2] 2036 	sraw	x
      008D01 41               [ 1] 2037 	exg	a, xl
      008D02 6B 27            [ 1] 2038 	ld	(0x27, sp), a
      008D04 41               [ 1] 2039 	exg	a, xl
                                   2040 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 559: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
      008D05 1E 0F            [ 2] 2041 	ldw	x, (0x0f, sp)
      008D07 1C 00 3F         [ 2] 2042 	addw	x, #0x003f
      008D0A 57               [ 2] 2043 	sraw	x
      008D0B 41               [ 1] 2044 	exg	a, xl
      008D0C 6B 1A            [ 1] 2045 	ld	(0x1a, sp), a
      008D0E 41               [ 1] 2046 	exg	a, xl
                                   2047 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 560: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
      008D0F 16 0D            [ 2] 2048 	ldw	y, (0x0d, sp)
      008D11 17 1B            [ 2] 2049 	ldw	(0x1b, sp), y
      008D13 5F               [ 1] 2050 	clrw	x
      008D14 1F 1D            [ 2] 2051 	ldw	(0x1d, sp), x
      008D16 5F               [ 1] 2052 	clrw	x
      008D17 1F 1F            [ 2] 2053 	ldw	(0x1f, sp), x
      008D19 5F               [ 1] 2054 	clrw	x
      008D1A 5A               [ 2] 2055 	decw	x
      008D1B 1F 21            [ 2] 2056 	ldw	(0x21, sp), x
                                   2057 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008D1D 1E 18            [ 2] 2058 	ldw	x, (0x18, sp)
      008D1F 1C 00 4C         [ 2] 2059 	addw	x, #(_c_hist+0)
      008D22 1F 23            [ 2] 2060 	ldw	(0x23, sp), x
      008D24 0F 28            [ 1] 2061 	clr	(0x28, sp)
      008D26                       2062 00170$:
      008D26 7B 27            [ 1] 2063 	ld	a, (0x27, sp)
      008D28 11 1A            [ 1] 2064 	cp	a, (0x1a, sp)
      008D2A 22 2B            [ 1] 2065 	jrugt	00253$
                                   2066 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 563: if (c_hist[f][b]) {
      008D2C 5F               [ 1] 2067 	clrw	x
      008D2D 7B 27            [ 1] 2068 	ld	a, (0x27, sp)
      008D2F 97               [ 1] 2069 	ld	xl, a
      008D30 72 FB 23         [ 2] 2070 	addw	x, (0x23, sp)
      008D33 F6               [ 1] 2071 	ld	a, (x)
      008D34 27 1D            [ 1] 2072 	jreq	00171$
                                   2073 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 564: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008D36 7B 27            [ 1] 2074 	ld	a, (0x27, sp)
      008D38 5F               [ 1] 2075 	clrw	x
      008D39 97               [ 1] 2076 	ld	xl, a
      008D3A 58               [ 2] 2077 	sllw	x
      008D3B 1C FF C1         [ 2] 2078 	addw	x, #0xffc1
                                   2079 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 565: int16_t gp = (int16_t)(x - prev);
      008D3E 90 93            [ 1] 2080 	ldw	y, x
      008D40 72 F0 1B         [ 2] 2081 	subw	x, (0x1b, sp)
                                   2082 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 566: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
      008D43 13 21            [ 2] 2083 	cpw	x, (0x21, sp)
      008D45 2D 08            [ 1] 2084 	jrsle	00106$
      008D47 1F 21            [ 2] 2085 	ldw	(0x21, sp), x
      008D49 1E 1B            [ 2] 2086 	ldw	x, (0x1b, sp)
      008D4B 1F 1D            [ 2] 2087 	ldw	(0x1d, sp), x
      008D4D 17 1F            [ 2] 2088 	ldw	(0x1f, sp), y
      008D4F                       2089 00106$:
                                   2090 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 567: prev = x;
      008D4F 17 1B            [ 2] 2091 	ldw	(0x1b, sp), y
                                   2092 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 568: nocc++;
      008D51 0C 28            [ 1] 2093 	inc	(0x28, sp)
      008D53                       2094 00171$:
                                   2095 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008D53 0C 27            [ 1] 2096 	inc	(0x27, sp)
      008D55 20 CF            [ 2] 2097 	jra	00170$
      008D57                       2098 00253$:
                                   2099 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 572: int16_t gp = (int16_t)(zhi - prev);
      008D57 1E 0F            [ 2] 2100 	ldw	x, (0x0f, sp)
      008D59 72 F0 1B         [ 2] 2101 	subw	x, (0x1b, sp)
                                   2102 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 573: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
      008D5C 13 21            [ 2] 2103 	cpw	x, (0x21, sp)
      008D5E 2D 0A            [ 1] 2104 	jrsle	00111$
      008D60 1F 21            [ 2] 2105 	ldw	(0x21, sp), x
      008D62 16 1B            [ 2] 2106 	ldw	y, (0x1b, sp)
      008D64 17 1D            [ 2] 2107 	ldw	(0x1d, sp), y
      008D66 16 0F            [ 2] 2108 	ldw	y, (0x0f, sp)
      008D68 17 1F            [ 2] 2109 	ldw	(0x1f, sp), y
      008D6A                       2110 00111$:
                                   2111 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 575: if (nocc == 0) {
      008D6A 0D 28            [ 1] 2112 	tnz	(0x28, sp)
      008D6C 26 1C            [ 1] 2113 	jrne	00123$
                                   2114 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 576: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
      008D6E 0D 09            [ 1] 2115 	tnz	(0x09, sp)
      008D70 26 03            [ 1] 2116 	jrne	00495$
      008D72 CC 8E 00         [ 2] 2117 	jp	00126$
      008D75                       2118 00495$:
      008D75 0D 0C            [ 1] 2119 	tnz	(0x0c, sp)
      008D77 26 03            [ 1] 2120 	jrne	00496$
      008D79 CC 8E 00         [ 2] 2121 	jp	00126$
      008D7C                       2122 00496$:
      008D7C 1E 0D            [ 2] 2123 	ldw	x, (0x0d, sp)
      008D7E 72 FB 0F         [ 2] 2124 	addw	x, (0x0f, sp)
      008D81 57               [ 2] 2125 	sraw	x
      008D82 1F 11            [ 2] 2126 	ldw	(0x11, sp), x
      008D84 A6 01            [ 1] 2127 	ld	a, #0x01
      008D86 6B 13            [ 1] 2128 	ld	(0x13, sp), a
      008D88 20 76            [ 2] 2129 	jra	00126$
      008D8A                       2130 00123$:
                                   2131 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 578: uint8_t ok = (bg >= EPS_GAP_MIN);
      008D8A 1E 21            [ 2] 2132 	ldw	x, (0x21, sp)
      008D8C A3 00 05         [ 2] 2133 	cpw	x, #0x0005
      008D8F 2F 02            [ 1] 2134 	jrslt	00497$
      008D91 4F               [ 1] 2135 	clr	a
      008D92 C5                    2136 	.byte 0xc5
      008D93                       2137 00497$:
      008D93 A6 01            [ 1] 2138 	ld	a, #0x01
      008D95                       2139 00498$:
      008D95 A8 01            [ 1] 2140 	xor	a, #0x01
                                   2141 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 579: if (ok && (uint8_t)(nocc + 1) >= 4) {
      008D97 6B 27            [ 1] 2142 	ld	(0x27, sp), a
      008D99 27 55            [ 1] 2143 	jreq	00118$
      008D9B 7B 28            [ 1] 2144 	ld	a, (0x28, sp)
      008D9D 4C               [ 1] 2145 	inc	a
      008D9E A1 04            [ 1] 2146 	cp	a, #0x04
      008DA0 25 4E            [ 1] 2147 	jrc	00118$
                                   2148 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 580: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
      008DA2 16 21            [ 2] 2149 	ldw	y, (0x21, sp)
      008DA4 5F               [ 1] 2150 	clrw	x
      008DA5 90 5D            [ 2] 2151 	tnzw	y
      008DA7 2A 01            [ 1] 2152 	jrpl	00501$
      008DA9 5A               [ 2] 2153 	decw	x
      008DAA                       2154 00501$:
      008DAA 90 58            [ 2] 2155 	sllw	y
      008DAC 59               [ 2] 2156 	rlcw	x
      008DAD 1F 21            [ 2] 2157 	ldw	(0x21, sp), x
      008DAF 7B 28            [ 1] 2158 	ld	a, (0x28, sp)
      008DB1 5F               [ 1] 2159 	clrw	x
      008DB2 97               [ 1] 2160 	ld	xl, a
      008DB3 5C               [ 1] 2161 	incw	x
      008DB4 9E               [ 1] 2162 	ld	a, xh
      008DB5 49               [ 1] 2163 	rlc	a
      008DB6 4F               [ 1] 2164 	clr	a
      008DB7 A2 00            [ 1] 2165 	sbc	a, #0x00
      008DB9 6B 02            [ 1] 2166 	ld	(0x02, sp), a
      008DBB 6B 01            [ 1] 2167 	ld	(0x01, sp), a
      008DBD 89               [ 2] 2168 	pushw	x
      008DBE 1E 03            [ 2] 2169 	ldw	x, (0x03, sp)
      008DC0 89               [ 2] 2170 	pushw	x
      008DC1 90 89            [ 2] 2171 	pushw	y
      008DC3 1E 27            [ 2] 2172 	ldw	x, (0x27, sp)
      008DC5 89               [ 2] 2173 	pushw	x
      008DC6 CD 99 05         [ 4] 2174 	call	__mullong
      008DC9 5B 08            [ 2] 2175 	addw	sp, #8
      008DCB 17 21            [ 2] 2176 	ldw	(0x21, sp), y
      008DCD 16 0F            [ 2] 2177 	ldw	y, (0x0f, sp)
      008DCF 72 F2 0D         [ 2] 2178 	subw	y, (0x0d, sp)
      008DD2 89               [ 2] 2179 	pushw	x
      008DD3 90 89            [ 2] 2180 	pushw	y
      008DD5 AE 00 05         [ 2] 2181 	ldw	x, #0x0005
      008DD8 CD 98 30         [ 4] 2182 	call	___mulsint2slong
      008DDB 5B 02            [ 2] 2183 	addw	sp, #2
      008DDD 1F 11            [ 2] 2184 	ldw	(0x11, sp), x
      008DDF 17 0F            [ 2] 2185 	ldw	(0x0f, sp), y
      008DE1 85               [ 2] 2186 	popw	x
      008DE2 13 0F            [ 2] 2187 	cpw	x, (0x0f, sp)
      008DE4 7B 22            [ 1] 2188 	ld	a, (0x22, sp)
      008DE6 12 0E            [ 1] 2189 	sbc	a, (0x0e, sp)
      008DE8 7B 21            [ 1] 2190 	ld	a, (0x21, sp)
      008DEA 12 0D            [ 1] 2191 	sbc	a, (0x0d, sp)
      008DEC 2E 02            [ 1] 2192 	jrsge	00118$
                                   2193 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 581: ok = 0;
      008DEE 0F 27            [ 1] 2194 	clr	(0x27, sp)
      008DF0                       2195 00118$:
                                   2196 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 583: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
      008DF0 0D 27            [ 1] 2197 	tnz	(0x27, sp)
      008DF2 27 0C            [ 1] 2198 	jreq	00126$
      008DF4 1E 1D            [ 2] 2199 	ldw	x, (0x1d, sp)
      008DF6 72 FB 1F         [ 2] 2200 	addw	x, (0x1f, sp)
      008DF9 57               [ 2] 2201 	sraw	x
      008DFA 1F 11            [ 2] 2202 	ldw	(0x11, sp), x
      008DFC A6 01            [ 1] 2203 	ld	a, #0x01
      008DFE 6B 13            [ 1] 2204 	ld	(0x13, sp), a
      008E00                       2205 00126$:
                                   2206 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 586: if (has0 || has1) {
      008E00 0D 09            [ 1] 2207 	tnz	(0x09, sp)
      008E02 26 04            [ 1] 2208 	jrne	00144$
      008E04 0D 0C            [ 1] 2209 	tnz	(0x0c, sp)
      008E06 27 77            [ 1] 2210 	jreq	00245$
      008E08                       2211 00144$:
                                   2212 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 587: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
      008E08 AE FF E0         [ 2] 2213 	ldw	x, #0xffe0
      008E0B 1F 23            [ 2] 2214 	ldw	(0x23, sp), x
      008E0D AE 00 20         [ 2] 2215 	ldw	x, #0x0020
      008E10 1F 27            [ 2] 2216 	ldw	(0x27, sp), x
                                   2217 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 588: if (has0) {
      008E12 0D 09            [ 1] 2218 	tnz	(0x09, sp)
      008E14 27 19            [ 1] 2219 	jreq	00131$
                                   2220 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 589: wlo = (int16_t)(x0 - EPS_SLACK1);
      008E16 1E 07            [ 2] 2221 	ldw	x, (0x07, sp)
      008E18 1D 00 08         [ 2] 2222 	subw	x, #0x0008
      008E1B 1F 23            [ 2] 2223 	ldw	(0x23, sp), x
                                   2224 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 590: if (c_labx0b[f] > -0x4000 &&
      008E1D 1E 05            [ 2] 2225 	ldw	x, (0x05, sp)
      008E1F DE 00 D4         [ 2] 2226 	ldw	x, (_c_labx0b+0, x)
      008E22 A3 C0 00         [ 2] 2227 	cpw	x, #0xc000
      008E25 2D 08            [ 1] 2228 	jrsle	00131$
                                   2229 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 591: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
      008E27 5A               [ 2] 2230 	decw	x
      008E28 5A               [ 2] 2231 	decw	x
      008E29 13 23            [ 2] 2232 	cpw	x, (0x23, sp)
      008E2B 2D 02            [ 1] 2233 	jrsle	00131$
                                   2234 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 592: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
      008E2D 1F 23            [ 2] 2235 	ldw	(0x23, sp), x
      008E2F                       2236 00131$:
                                   2237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 594: if (has1) {
      008E2F 0D 0C            [ 1] 2238 	tnz	(0x0c, sp)
      008E31 27 19            [ 1] 2239 	jreq	00136$
                                   2240 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 595: whi = (int16_t)(x1 + EPS_SLACK1);
      008E33 1E 0A            [ 2] 2241 	ldw	x, (0x0a, sp)
      008E35 1C 00 08         [ 2] 2242 	addw	x, #0x0008
      008E38 1F 27            [ 2] 2243 	ldw	(0x27, sp), x
                                   2244 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 596: if (c_labx1b[f] < 0x3FFF &&
      008E3A 1E 05            [ 2] 2245 	ldw	x, (0x05, sp)
      008E3C DE 00 D8         [ 2] 2246 	ldw	x, (_c_labx1b+0, x)
      008E3F A3 3F FF         [ 2] 2247 	cpw	x, #0x3fff
      008E42 2E 08            [ 1] 2248 	jrsge	00136$
                                   2249 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 597: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
      008E44 5C               [ 1] 2250 	incw	x
      008E45 5C               [ 1] 2251 	incw	x
      008E46 13 27            [ 2] 2252 	cpw	x, (0x27, sp)
      008E48 2E 02            [ 1] 2253 	jrsge	00136$
                                   2254 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 598: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
      008E4A 1F 27            [ 2] 2255 	ldw	(0x27, sp), x
      008E4C                       2256 00136$:
                                   2257 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 600: if (wlo > whi) {
                                   2258 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 601: theta = (int16_t)((wlo + whi) >> 1);
      008E4C 1E 23            [ 2] 2259 	ldw	x, (0x23, sp)
      008E4E 13 27            [ 2] 2260 	cpw	x, (0x27, sp)
      008E50 2D 0C            [ 1] 2261 	jrsle	00142$
      008E52 72 FB 27         [ 2] 2262 	addw	x, (0x27, sp)
      008E55 57               [ 2] 2263 	sraw	x
      008E56 1F 11            [ 2] 2264 	ldw	(0x11, sp), x
                                   2265 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 602: have_theta = 1;
      008E58 A6 01            [ 1] 2266 	ld	a, #0x01
      008E5A 6B 13            [ 1] 2267 	ld	(0x13, sp), a
      008E5C 20 21            [ 2] 2268 	jra	00245$
      008E5E                       2269 00142$:
                                   2270 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 604: int16_t th = have_theta ? theta : 0;
      008E5E 0D 13            [ 1] 2271 	tnz	(0x13, sp)
      008E60 27 08            [ 1] 2272 	jreq	00175$
      008E62 7B 12            [ 1] 2273 	ld	a, (0x12, sp)
      008E64 02               [ 1] 2274 	rlwa	x
      008E65 7B 11            [ 1] 2275 	ld	a, (0x11, sp)
      008E67 01               [ 1] 2276 	rrwa	x
      008E68 20 02            [ 2] 2277 	jra	00176$
      008E6A                       2278 00175$:
      008E6A 4F               [ 1] 2279 	clr	a
      008E6B 5F               [ 1] 2280 	clrw	x
      008E6C                       2281 00176$:
      008E6C 97               [ 1] 2282 	ld	xl, a
                                   2283 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 605: if (th < wlo) th = wlo;
      008E6D 13 23            [ 2] 2284 	cpw	x, (0x23, sp)
      008E6F 2E 02            [ 1] 2285 	jrsge	00138$
      008E71 1E 23            [ 2] 2286 	ldw	x, (0x23, sp)
      008E73                       2287 00138$:
                                   2288 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 606: if (th > whi) th = whi;
      008E73 13 27            [ 2] 2289 	cpw	x, (0x27, sp)
      008E75 2D 02            [ 1] 2290 	jrsle	00140$
      008E77 1E 27            [ 2] 2291 	ldw	x, (0x27, sp)
      008E79                       2292 00140$:
                                   2293 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 607: theta = th;
      008E79 1F 11            [ 2] 2294 	ldw	(0x11, sp), x
                                   2295 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 608: have_theta = 1;
      008E7B A6 01            [ 1] 2296 	ld	a, #0x01
      008E7D 6B 13            [ 1] 2297 	ld	(0x13, sp), a
                                   2298 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
      008E7F                       2299 00245$:
      008E7F 1E 18            [ 2] 2300 	ldw	x, (0x18, sp)
      008E81 1C 00 4C         [ 2] 2301 	addw	x, #(_c_hist+0)
      008E84 1F 23            [ 2] 2302 	ldw	(0x23, sp), x
      008E86 0F 28            [ 1] 2303 	clr	(0x28, sp)
      008E88                       2304 00172$:
                                   2305 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 613: if (!c_hist[f][b]) continue;
      008E88 5F               [ 1] 2306 	clrw	x
      008E89 7B 28            [ 1] 2307 	ld	a, (0x28, sp)
      008E8B 97               [ 1] 2308 	ld	xl, a
      008E8C 72 FB 23         [ 2] 2309 	addw	x, (0x23, sp)
      008E8F F6               [ 1] 2310 	ld	a, (x)
      008E90 27 2C            [ 1] 2311 	jreq	00157$
                                   2312 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 614: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008E92 5F               [ 1] 2313 	clrw	x
      008E93 7B 28            [ 1] 2314 	ld	a, (0x28, sp)
      008E95 97               [ 1] 2315 	ld	xl, a
      008E96 58               [ 2] 2316 	sllw	x
      008E97 1C 00 C1         [ 2] 2317 	addw	x, #193
      008E9A 9F               [ 1] 2318 	ld	a, xl
      008E9B 49               [ 1] 2319 	rlc	a
      008E9C 4F               [ 1] 2320 	clr	a
      008E9D A2 00            [ 1] 2321 	sbc	a, #0x00
      008E9F 95               [ 1] 2322 	ld	xh, a
                                   2323 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 615: if (d > EPS_CLEAR1) clear1 = 1;
      008EA0 9F               [ 1] 2324 	ld	a, xl
      008EA1 A1 12            [ 1] 2325 	cp	a, #0x12
      008EA3 2D 06            [ 1] 2326 	jrsle	00155$
      008EA5 A6 01            [ 1] 2327 	ld	a, #0x01
      008EA7 6B 17            [ 1] 2328 	ld	(0x17, sp), a
      008EA9 20 13            [ 2] 2329 	jra	00157$
      008EAB                       2330 00155$:
                                   2331 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 616: else if (d > -EPS_CLAMP56) {
      008EAB A3 FF E8         [ 2] 2332 	cpw	x, #0xffe8
      008EAE 2D 0E            [ 1] 2333 	jrsle	00157$
                                   2334 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 617: if (!have_top || d > top) top = d;
      008EB0 0D 16            [ 1] 2335 	tnz	(0x16, sp)
      008EB2 27 04            [ 1] 2336 	jreq	00149$
      008EB4 13 14            [ 2] 2337 	cpw	x, (0x14, sp)
      008EB6 2D 02            [ 1] 2338 	jrsle	00150$
      008EB8                       2339 00149$:
      008EB8 1F 14            [ 2] 2340 	ldw	(0x14, sp), x
      008EBA                       2341 00150$:
                                   2342 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 618: have_top = 1;
      008EBA A6 01            [ 1] 2343 	ld	a, #0x01
      008EBC 6B 16            [ 1] 2344 	ld	(0x16, sp), a
      008EBE                       2345 00157$:
                                   2346 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
      008EBE 0C 28            [ 1] 2347 	inc	(0x28, sp)
      008EC0 7B 28            [ 1] 2348 	ld	a, (0x28, sp)
      008EC2 A1 40            [ 1] 2349 	cp	a, #0x40
      008EC4 25 C2            [ 1] 2350 	jrc	00172$
                                   2351 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 621: if (!clear1 && have_top) {
      008EC6 0D 17            [ 1] 2352 	tnz	(0x17, sp)
      008EC8 26 36            [ 1] 2353 	jrne	00167$
      008ECA 0D 16            [ 1] 2354 	tnz	(0x16, sp)
      008ECC 27 32            [ 1] 2355 	jreq	00167$
                                   2356 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 622: int16_t floor_ = (int16_t)(top + EPS_TOPM);
      008ECE 7B 15            [ 1] 2357 	ld	a, (0x15, sp)
      008ED0 AB 03            [ 1] 2358 	add	a, #0x03
      008ED2 97               [ 1] 2359 	ld	xl, a
      008ED3 49               [ 1] 2360 	rlc	a
      008ED4 4F               [ 1] 2361 	clr	a
      008ED5 A2 00            [ 1] 2362 	sbc	a, #0x00
      008ED7 95               [ 1] 2363 	ld	xh, a
                                   2364 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 623: if (!have_theta || floor_ > theta) theta = floor_;
      008ED8 0D 13            [ 1] 2365 	tnz	(0x13, sp)
      008EDA 27 04            [ 1] 2366 	jreq	00159$
      008EDC 13 11            [ 2] 2367 	cpw	x, (0x11, sp)
      008EDE 2D 02            [ 1] 2368 	jrsle	00160$
      008EE0                       2369 00159$:
      008EE0 1F 11            [ 2] 2370 	ldw	(0x11, sp), x
      008EE2                       2371 00160$:
                                   2372 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 624: have_theta = 1;
      008EE2 A6 01            [ 1] 2373 	ld	a, #0x01
      008EE4 6B 13            [ 1] 2374 	ld	(0x13, sp), a
                                   2375 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 625: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
      008EE6 0D 0C            [ 1] 2376 	tnz	(0x0c, sp)
      008EE8 27 16            [ 1] 2377 	jreq	00167$
      008EEA 16 0A            [ 2] 2378 	ldw	y, (0x0a, sp)
      008EEC 72 A9 00 02      [ 2] 2379 	addw	y, #0x0002
      008EF0 17 27            [ 2] 2380 	ldw	(0x27, sp), y
      008EF2 13 27            [ 2] 2381 	cpw	x, (0x27, sp)
      008EF4 2E 0A            [ 1] 2382 	jrsge	00167$
                                   2383 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 626: theta > (int16_t)(x1 + EPS_SLACK))
      008EF6 1E 11            [ 2] 2384 	ldw	x, (0x11, sp)
      008EF8 13 27            [ 2] 2385 	cpw	x, (0x27, sp)
      008EFA 2D 04            [ 1] 2386 	jrsle	00167$
                                   2387 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 627: theta = (int16_t)(x1 + EPS_SLACK);
      008EFC 16 27            [ 2] 2388 	ldw	y, (0x27, sp)
      008EFE 17 11            [ 2] 2389 	ldw	(0x11, sp), y
      008F00                       2390 00167$:
                                   2391 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 629: *theta_out = theta;
      008F00 1E 25            [ 2] 2392 	ldw	x, (0x25, sp)
      008F02 16 11            [ 2] 2393 	ldw	y, (0x11, sp)
      008F04 FF               [ 2] 2394 	ldw	(x), y
                                   2395 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 630: return have_theta;
      008F05 7B 13            [ 1] 2396 	ld	a, (0x13, sp)
                                   2397 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 631: }
      008F07 5B 28            [ 2] 2398 	addw	sp, #40
      008F09 81               [ 4] 2399 	ret
                                   2400 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 634: static int16_t width_fit(uint8_t ci, int16_t prior, int16_t blo, int16_t bhi)
                                   2401 ;	-----------------------------------------
                                   2402 ;	 function width_fit
                                   2403 ;	-----------------------------------------
      008F0A                       2404 _width_fit:
      008F0A 52 04            [ 2] 2405 	sub	sp, #4
      008F0C 1F 03            [ 2] 2406 	ldw	(0x03, sp), x
                                   2407 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 636: int16_t lo = c_lo[ci], hi = c_hi[ci], h;
      008F0E 5F               [ 1] 2408 	clrw	x
      008F0F 97               [ 1] 2409 	ld	xl, a
      008F10 58               [ 2] 2410 	sllw	x
      008F11 90 93            [ 1] 2411 	ldw	y, x
      008F13 DE 00 3C         [ 2] 2412 	ldw	x, (_c_lo+0, x)
      008F16 1F 01            [ 2] 2413 	ldw	(0x01, sp), x
      008F18 90 DE 00 40      [ 2] 2414 	ldw	y, (_c_hi+0, y)
                                   2415 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 637: if (c_n[ci] < LAB_MIN) return prior;
      008F1C 5F               [ 1] 2416 	clrw	x
      008F1D 97               [ 1] 2417 	ld	xl, a
      008F1E 1C 00 44         [ 2] 2418 	addw	x, #(_c_n+0)
      008F21 F6               [ 1] 2419 	ld	a, (x)
      008F22 A1 03            [ 1] 2420 	cp	a, #0x03
      008F24 24 04            [ 1] 2421 	jrnc	00102$
      008F26 1E 03            [ 2] 2422 	ldw	x, (0x03, sp)
      008F28 20 31            [ 2] 2423 	jra	00103$
      008F2A                       2424 00102$:
                                   2425 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 638: h = (lo > hi) ? (int16_t)((lo + hi) >> 1)
      008F2A 51               [ 1] 2426 	exgw	x, y
      008F2B 13 01            [ 2] 2427 	cpw	x, (0x01, sp)
      008F2D 51               [ 1] 2428 	exgw	x, y
      008F2E 2E 07            [ 1] 2429 	jrsge	00105$
      008F30 93               [ 1] 2430 	ldw	x, y
      008F31 72 FB 01         [ 2] 2431 	addw	x, (0x01, sp)
      008F34 57               [ 2] 2432 	sraw	x
      008F35 20 1A            [ 2] 2433 	jra	00106$
      008F37                       2434 00105$:
                                   2435 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 639: : (prior < lo ? lo : (prior > hi ? hi : prior));
      008F37 1E 03            [ 2] 2436 	ldw	x, (0x03, sp)
      008F39 13 01            [ 2] 2437 	cpw	x, (0x01, sp)
      008F3B 2E 04            [ 1] 2438 	jrsge	00107$
      008F3D 1E 01            [ 2] 2439 	ldw	x, (0x01, sp)
      008F3F 20 10            [ 2] 2440 	jra	00108$
      008F41                       2441 00107$:
      008F41 51               [ 1] 2442 	exgw	x, y
      008F42 13 03            [ 2] 2443 	cpw	x, (0x03, sp)
      008F44 51               [ 1] 2444 	exgw	x, y
      008F45 2E 04            [ 1] 2445 	jrsge	00109$
      008F47 17 01            [ 2] 2446 	ldw	(0x01, sp), y
      008F49 20 04            [ 2] 2447 	jra	00110$
      008F4B                       2448 00109$:
      008F4B 16 03            [ 2] 2449 	ldw	y, (0x03, sp)
      008F4D 17 01            [ 2] 2450 	ldw	(0x01, sp), y
      008F4F                       2451 00110$:
      008F4F 1E 01            [ 2] 2452 	ldw	x, (0x01, sp)
      008F51                       2453 00108$:
      008F51                       2454 00106$:
                                   2455 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 640: return (h >= blo && h <= bhi) ? h : prior;
      008F51 13 07            [ 2] 2456 	cpw	x, (0x07, sp)
      008F53 2F 04            [ 1] 2457 	jrslt	00111$
      008F55 13 09            [ 2] 2458 	cpw	x, (0x09, sp)
      008F57 2D 02            [ 1] 2459 	jrsle	00112$
      008F59                       2460 00111$:
      008F59 1E 03            [ 2] 2461 	ldw	x, (0x03, sp)
      008F5B                       2462 00112$:
      008F5B                       2463 00103$:
                                   2464 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 641: }
      008F5B 16 05            [ 2] 2465 	ldw	y, (5, sp)
      008F5D 5B 0A            [ 2] 2466 	addw	sp, #10
      008F5F 90 FC            [ 2] 2467 	jp	(y)
                                   2468 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 643: static void calibrate(void)
                                   2469 ;	-----------------------------------------
                                   2470 ;	 function calibrate
                                   2471 ;	-----------------------------------------
      008F61                       2472 _calibrate:
      008F61 52 15            [ 2] 2473 	sub	sp, #21
                                   2474 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 647: c_lo[0] = c_lo[1] = -0x4000;
      008F63 35 00 00 3F      [ 1] 2475 	mov	_c_lo+3, #0x00
      008F67 35 C0 00 3E      [ 1] 2476 	mov	_c_lo+2, #0xc0
      008F6B 35 00 00 3D      [ 1] 2477 	mov	_c_lo+1, #0x00
      008F6F 35 C0 00 3C      [ 1] 2478 	mov	_c_lo+0, #0xc0
                                   2479 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 648: c_hi[0] = c_hi[1] = 0x3FFF;
      008F73 35 FF 00 43      [ 1] 2480 	mov	_c_hi+3, #0xff
      008F77 35 3F 00 42      [ 1] 2481 	mov	_c_hi+2, #0x3f
      008F7B 35 FF 00 41      [ 1] 2482 	mov	_c_hi+1, #0xff
      008F7F 35 3F 00 40      [ 1] 2483 	mov	_c_hi+0, #0x3f
                                   2484 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 649: c_n[0] = c_n[1] = 0;
      008F83 35 00 00 45      [ 1] 2485 	mov	_c_n+1, #0x00
      008F87 35 00 00 44      [ 1] 2486 	mov	_c_n+0, #0x00
                                   2487 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 650: c_h0c = H0P; c_h1c = H1P;
      008F8B AE 00 9A         [ 2] 2488 	ldw	x, #0x009a
      008F8E CF 00 46         [ 2] 2489 	ldw	_c_h0c+0, x
      008F91 AE 01 34         [ 2] 2490 	ldw	x, #0x0134
      008F94 CF 00 48         [ 2] 2491 	ldw	_c_h1c+0, x
                                   2492 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 651: c_d56[0] = c_d56[1] = 0;
      008F97 35 00 00 4B      [ 1] 2493 	mov	_c_d56+1, #0x00
      008F9B 35 00 00 4A      [ 1] 2494 	mov	_c_d56+0, #0x00
                                   2495 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
      008F9F CE 00 38         [ 2] 2496 	ldw	x, _g_K+0
      008FA2 89               [ 2] 2497 	pushw	x
      008FA3 AE 00 06         [ 2] 2498 	ldw	x, #0x0006
      008FA6 CD 98 2A         [ 4] 2499 	call	___muluint2ulong
      008FA9 5B 02            [ 2] 2500 	addw	sp, #2
      008FAB A6 0B            [ 1] 2501 	ld	a, #0x0b
      008FAD                       2502 00285$:
      008FAD 90 54            [ 2] 2503 	srlw	y
      008FAF 56               [ 2] 2504 	rrcw	x
      008FB0 4A               [ 1] 2505 	dec	a
      008FB1 26 FA            [ 1] 2506 	jrne	00285$
      008FB3 CF 00 E0         [ 2] 2507 	ldw	_c_gap56+0, x
                                   2508 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 653: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
      008FB6 CE 00 38         [ 2] 2509 	ldw	x, _g_K+0
      008FB9 89               [ 2] 2510 	pushw	x
      008FBA AE 00 05         [ 2] 2511 	ldw	x, #0x0005
      008FBD CD 98 2A         [ 4] 2512 	call	___muluint2ulong
      008FC0 5B 02            [ 2] 2513 	addw	sp, #2
      008FC2 A6 0B            [ 1] 2514 	ld	a, #0x0b
      008FC4                       2515 00287$:
      008FC4 90 54            [ 2] 2516 	srlw	y
      008FC6 56               [ 2] 2517 	rrcw	x
      008FC7 4A               [ 1] 2518 	dec	a
      008FC8 26 FA            [ 1] 2519 	jrne	00287$
      008FCA CF 00 E2         [ 2] 2520 	ldw	_c_gap56+2, x
                                   2521 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
      008FCD 0F 15            [ 1] 2522 	clr	(0x15, sp)
      008FCF                       2523 00128$:
                                   2524 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 656: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
      008FCF 5F               [ 1] 2525 	clrw	x
      008FD0 7B 15            [ 1] 2526 	ld	a, (0x15, sp)
      008FD2 97               [ 1] 2527 	ld	xl, a
      008FD3 58               [ 2] 2528 	sllw	x
      008FD4 1F 11            [ 2] 2529 	ldw	(0x11, sp), x
      008FD6 90 93            [ 1] 2530 	ldw	y, x
      008FD8 72 A9 00 DC      [ 2] 2531 	addw	y, #(_c_c0+0)
      008FDC 1E 11            [ 2] 2532 	ldw	x, (0x11, sp)
      008FDE DE 00 E0         [ 2] 2533 	ldw	x, (_c_gap56+0, x)
      008FE1 1F 13            [ 2] 2534 	ldw	(0x13, sp), x
      008FE3 AE 01 CE         [ 2] 2535 	ldw	x, #0x01ce
      008FE6 72 F0 13         [ 2] 2536 	subw	x, (0x13, sp)
      008FE9 57               [ 2] 2537 	sraw	x
      008FEA 90 FF            [ 2] 2538 	ldw	(y), x
                                   2539 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 657: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
      008FEC 7B 15            [ 1] 2540 	ld	a, (0x15, sp)
      008FEE 97               [ 1] 2541 	ld	xl, a
      008FEF A6 40            [ 1] 2542 	ld	a, #0x40
      008FF1 42               [ 4] 2543 	mul	x, a
      008FF2 1C 00 4C         [ 2] 2544 	addw	x, #(_c_hist+0)
      008FF5 1F 13            [ 2] 2545 	ldw	(0x13, sp), x
      008FF7 4F               [ 1] 2546 	clr	a
      008FF8                       2547 00126$:
      008FF8 5F               [ 1] 2548 	clrw	x
      008FF9 97               [ 1] 2549 	ld	xl, a
      008FFA 72 FB 13         [ 2] 2550 	addw	x, (0x13, sp)
      008FFD 7F               [ 1] 2551 	clr	(x)
      008FFE 4C               [ 1] 2552 	inc	a
      008FFF A1 40            [ 1] 2553 	cp	a, #0x40
      009001 25 F5            [ 1] 2554 	jrc	00126$
                                   2555 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 658: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
      009003 1E 11            [ 2] 2556 	ldw	x, (0x11, sp)
      009005 1C 00 CC         [ 2] 2557 	addw	x, #(_c_labx0+0)
      009008 6F 01            [ 1] 2558 	clr	(0x1, x)
      00900A A6 C0            [ 1] 2559 	ld	a, #0xc0
      00900C F7               [ 1] 2560 	ld	(x), a
      00900D 1E 11            [ 2] 2561 	ldw	x, (0x11, sp)
      00900F 1C 00 D4         [ 2] 2562 	addw	x, #(_c_labx0b+0)
      009012 6F 01            [ 1] 2563 	clr	(0x1, x)
      009014 A6 C0            [ 1] 2564 	ld	a, #0xc0
      009016 F7               [ 1] 2565 	ld	(x), a
                                   2566 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 659: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
      009017 1E 11            [ 2] 2567 	ldw	x, (0x11, sp)
      009019 90 AE 3F FF      [ 2] 2568 	ldw	y, #0x3fff
      00901D DF 00 D0         [ 2] 2569 	ldw	((_c_labx1+0), x), y
      009020 1E 11            [ 2] 2570 	ldw	x, (0x11, sp)
      009022 90 AE 3F FF      [ 2] 2571 	ldw	y, #0x3fff
      009026 DF 00 D8         [ 2] 2572 	ldw	((_c_labx1b+0), x), y
                                   2573 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
      009029 0C 15            [ 1] 2574 	inc	(0x15, sp)
      00902B 7B 15            [ 1] 2575 	ld	a, (0x15, sp)
      00902D A1 02            [ 1] 2576 	cp	a, #0x02
      00902F 25 9E            [ 1] 2577 	jrc	00128$
                                   2578 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 661: ss_init();
      009031 CD 87 C4         [ 4] 2579 	call	_ss_init
                                   2580 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 662: while (ss_next(&sg)) {
      009034                       2581 00112$:
      009034 96               [ 1] 2582 	ldw	x, sp
      009035 5C               [ 1] 2583 	incw	x
      009036 CD 88 06         [ 4] 2584 	call	_ss_next
      009039 4D               [ 1] 2585 	tnz	a
      00903A 26 03            [ 1] 2586 	jrne	00291$
      00903C CC 90 C1         [ 2] 2587 	jp	00114$
      00903F                       2588 00291$:
                                   2589 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 664: uint8_t known_all = 1;
      00903F A6 01            [ 1] 2590 	ld	a, #0x01
      009041 6B 13            [ 1] 2591 	ld	(0x13, sp), a
                                   2592 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 666: cal_cloud(sg.u, sg.fam);
      009043 7B 09            [ 1] 2593 	ld	a, (0x09, sp)
      009045 1E 05            [ 2] 2594 	ldw	x, (0x05, sp)
      009047 CD 8B 4D         [ 4] 2595 	call	_cal_cloud
                                   2596 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: if (sg.k1 > NB) continue;
      00904A 1E 03            [ 2] 2597 	ldw	x, (0x03, sp)
      00904C A3 00 C0         [ 2] 2598 	cpw	x, #0x00c0
      00904F 22 E3            [ 1] 2599 	jrugt	00112$
                                   2600 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 668: e = (sg.k1 < NB) ? sg.k1 : NB;
      009051 A3 00 C0         [ 2] 2601 	cpw	x, #0x00c0
      009054 24 03            [ 1] 2602 	jrnc	00136$
      009056 9F               [ 1] 2603 	ld	a, xl
      009057 20 03            [ 2] 2604 	jra	00137$
      009059                       2605 00136$:
      009059 A6 C0            [ 1] 2606 	ld	a, #0xc0
      00905B 5F               [ 1] 2607 	clrw	x
      00905C                       2608 00137$:
      00905C 6B 15            [ 1] 2609 	ld	(0x15, sp), a
      00905E 02               [ 1] 2610 	rlwa	x
      00905F 6B 14            [ 1] 2611 	ld	(0x14, sp), a
      009061 01               [ 1] 2612 	rrwa	x
                                   2613 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
      009062 96               [ 1] 2614 	ldw	x, sp
      009063 5C               [ 1] 2615 	incw	x
      009064 1F 0E            [ 2] 2616 	ldw	(0x0e, sp), x
      009066 FE               [ 2] 2617 	ldw	x, (x)
      009067                       2618 00131$:
      009067 13 14            [ 2] 2619 	cpw	x, (0x14, sp)
      009069 24 0F            [ 1] 2620 	jrnc	00107$
                                   2621 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 670: if (known_bit(t) < 0) { known_all = 0; break; }
      00906B 89               [ 2] 2622 	pushw	x
      00906C CD 81 47         [ 4] 2623 	call	_known_bit
      00906F 85               [ 2] 2624 	popw	x
      009070 4D               [ 1] 2625 	tnz	a
      009071 2A 04            [ 1] 2626 	jrpl	00132$
      009073 0F 13            [ 1] 2627 	clr	(0x13, sp)
      009075 20 03            [ 2] 2628 	jra	00107$
      009077                       2629 00132$:
                                   2630 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
      009077 5C               [ 1] 2631 	incw	x
      009078 20 ED            [ 2] 2632 	jra	00131$
      00907A                       2633 00107$:
                                   2634 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 671: if (!known_all) continue;
      00907A 0D 13            [ 1] 2635 	tnz	(0x13, sp)
      00907C 27 B6            [ 1] 2636 	jreq	00112$
                                   2637 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 672: a_bounds(sg.k0, sg.k1, &amin, &amax);
      00907E 16 03            [ 2] 2638 	ldw	y, (0x03, sp)
      009080 1E 0E            [ 2] 2639 	ldw	x, (0x0e, sp)
      009082 FE               [ 2] 2640 	ldw	x, (x)
      009083 1F 14            [ 2] 2641 	ldw	(0x14, sp), x
      009085 96               [ 1] 2642 	ldw	x, sp
      009086 1C 00 0C         [ 2] 2643 	addw	x, #12
      009089 89               [ 2] 2644 	pushw	x
      00908A 96               [ 1] 2645 	ldw	x, sp
      00908B 1C 00 0C         [ 2] 2646 	addw	x, #12
      00908E 89               [ 2] 2647 	pushw	x
      00908F 90 89            [ 2] 2648 	pushw	y
      009091 1E 1A            [ 2] 2649 	ldw	x, (0x1a, sp)
      009093 CD 8A 34         [ 4] 2650 	call	_a_bounds
                                   2651 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 673: if (amin == amax)
      009096 1E 0A            [ 2] 2652 	ldw	x, (0x0a, sp)
      009098 13 0C            [ 2] 2653 	cpw	x, (0x0c, sp)
      00909A 26 98            [ 1] 2654 	jrne	00112$
                                   2655 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 674: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
      00909C 7B 09            [ 1] 2656 	ld	a, (0x09, sp)
      00909E 16 07            [ 2] 2657 	ldw	y, (0x07, sp)
      0090A0 17 10            [ 2] 2658 	ldw	(0x10, sp), y
      0090A2 16 05            [ 2] 2659 	ldw	y, (0x05, sp)
      0090A4 17 12            [ 2] 2660 	ldw	(0x12, sp), y
      0090A6 16 03            [ 2] 2661 	ldw	y, (0x03, sp)
      0090A8 1E 0E            [ 2] 2662 	ldw	x, (0x0e, sp)
      0090AA FE               [ 2] 2663 	ldw	x, (x)
      0090AB 1F 14            [ 2] 2664 	ldw	(0x14, sp), x
      0090AD 1E 0A            [ 2] 2665 	ldw	x, (0x0a, sp)
      0090AF 89               [ 2] 2666 	pushw	x
      0090B0 88               [ 1] 2667 	push	a
      0090B1 1E 13            [ 2] 2668 	ldw	x, (0x13, sp)
      0090B3 89               [ 2] 2669 	pushw	x
      0090B4 1E 17            [ 2] 2670 	ldw	x, (0x17, sp)
      0090B6 89               [ 2] 2671 	pushw	x
      0090B7 90 89            [ 2] 2672 	pushw	y
      0090B9 1E 1D            [ 2] 2673 	ldw	x, (0x1d, sp)
      0090BB CD 8B 94         [ 4] 2674 	call	_cal_add
      0090BE CC 90 34         [ 2] 2675 	jp	00112$
      0090C1                       2676 00114$:
                                   2677 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 678: int16_t h0 = width_fit(0, H0P, H0_LO, H0_HI);
      0090C1 4B C0            [ 1] 2678 	push	#0xc0
      0090C3 4B 00            [ 1] 2679 	push	#0x00
      0090C5 4B 70            [ 1] 2680 	push	#0x70
      0090C7 4B 00            [ 1] 2681 	push	#0x00
      0090C9 AE 00 9A         [ 2] 2682 	ldw	x, #0x009a
      0090CC 4F               [ 1] 2683 	clr	a
      0090CD CD 8F 0A         [ 4] 2684 	call	_width_fit
      0090D0 1F 14            [ 2] 2685 	ldw	(0x14, sp), x
                                   2686 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 679: int16_t h1 = width_fit(1, H1P, H1_LO, H1_HI);
      0090D2 4B 78            [ 1] 2687 	push	#0x78
      0090D4 4B 01            [ 1] 2688 	push	#0x01
      0090D6 4B FC            [ 1] 2689 	push	#0xfc
      0090D8 4B 00            [ 1] 2690 	push	#0x00
      0090DA AE 01 34         [ 2] 2691 	ldw	x, #0x0134
      0090DD A6 01            [ 1] 2692 	ld	a, #0x01
      0090DF CD 8F 0A         [ 4] 2693 	call	_width_fit
                                   2694 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 680: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
      0090E2 90 93            [ 1] 2695 	ldw	y, x
      0090E4 72 F0 14         [ 2] 2696 	subw	x, (0x14, sp)
      0090E7 A3 00 70         [ 2] 2697 	cpw	x, #0x0070
      0090EA 2F 05            [ 1] 2698 	jrslt	00115$
      0090EC A3 00 C4         [ 2] 2699 	cpw	x, #0x00c4
      0090EF 2D 09            [ 1] 2700 	jrsle	00116$
      0090F1                       2701 00115$:
      0090F1 AE 00 9A         [ 2] 2702 	ldw	x, #0x009a
      0090F4 1F 14            [ 2] 2703 	ldw	(0x14, sp), x
      0090F6 90 AE 01 34      [ 2] 2704 	ldw	y, #0x0134
      0090FA                       2705 00116$:
                                   2706 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 681: c_h0c = h0; c_h1c = h1;
      0090FA 1E 14            [ 2] 2707 	ldw	x, (0x14, sp)
      0090FC CF 00 46         [ 2] 2708 	ldw	_c_h0c+0, x
      0090FF 90 CF 00 48      [ 2] 2709 	ldw	_c_h1c+0, y
                                   2710 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
      009103 0F 15            [ 1] 2711 	clr	(0x15, sp)
      009105                       2712 00133$:
                                   2713 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 685: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
      009105 96               [ 1] 2714 	ldw	x, sp
      009106 1C 00 0C         [ 2] 2715 	addw	x, #12
      009109 7B 15            [ 1] 2716 	ld	a, (0x15, sp)
      00910B CD 8C 8E         [ 4] 2717 	call	_theta56
      00910E 5F               [ 1] 2718 	clrw	x
      00910F 41               [ 1] 2719 	exg	a, xl
      009110 7B 15            [ 1] 2720 	ld	a, (0x15, sp)
      009112 41               [ 1] 2721 	exg	a, xl
      009113 1C 00 4A         [ 2] 2722 	addw	x, #(_c_d56+0)
      009116 1F 11            [ 2] 2723 	ldw	(0x11, sp), x
      009118 4D               [ 1] 2724 	tnz	a
      009119 26 05            [ 1] 2725 	jrne	00119$
      00911B 1E 11            [ 2] 2726 	ldw	x, (0x11, sp)
      00911D 7F               [ 1] 2727 	clr	(x)
      00911E 20 3B            [ 2] 2728 	jra	00124$
      009120                       2729 00119$:
                                   2730 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 686: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
      009120 CE 00 46         [ 2] 2731 	ldw	x, _c_h0c+0
      009123 72 BB 00 48      [ 2] 2732 	addw	x, _c_h1c+0
      009127 1F 13            [ 2] 2733 	ldw	(0x13, sp), x
      009129 5F               [ 1] 2734 	clrw	x
      00912A 7B 15            [ 1] 2735 	ld	a, (0x15, sp)
      00912C 97               [ 1] 2736 	ld	xl, a
      00912D 58               [ 2] 2737 	sllw	x
      00912E 90 93            [ 1] 2738 	ldw	y, x
      009130 DE 00 E0         [ 2] 2739 	ldw	x, (_c_gap56+0, x)
      009133 50               [ 2] 2740 	negw	x
      009134 72 FB 13         [ 2] 2741 	addw	x, (0x13, sp)
      009137 57               [ 2] 2742 	sraw	x
      009138 1F 13            [ 2] 2743 	ldw	(0x13, sp), x
                                   2744 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 687: delta = (int16_t)(th + c_c0[f] - cfit);
      00913A 93               [ 1] 2745 	ldw	x, y
      00913B DE 00 DC         [ 2] 2746 	ldw	x, (_c_c0+0, x)
      00913E 72 FB 0C         [ 2] 2747 	addw	x, (0x0c, sp)
      009141 72 F0 13         [ 2] 2748 	subw	x, (0x13, sp)
                                   2749 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 688: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
      009144 A3 FF E8         [ 2] 2750 	cpw	x, #0xffe8
      009147 2E 03            [ 1] 2751 	jrsge	00121$
      009149 AE FF E8         [ 2] 2752 	ldw	x, #0xffe8
      00914C                       2753 00121$:
                                   2754 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 689: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
      00914C 90 93            [ 1] 2755 	ldw	y, x
      00914E 90 A3 00 18      [ 2] 2756 	cpw	y, #0x0018
      009152 2D 03            [ 1] 2757 	jrsle	00123$
      009154 AE 00 18         [ 2] 2758 	ldw	x, #0x0018
      009157                       2759 00123$:
                                   2760 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: c_d56[f] = (int8_t)delta;
      009157 9F               [ 1] 2761 	ld	a, xl
      009158 1E 11            [ 2] 2762 	ldw	x, (0x11, sp)
      00915A F7               [ 1] 2763 	ld	(x), a
      00915B                       2764 00124$:
                                   2765 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
      00915B 0C 15            [ 1] 2766 	inc	(0x15, sp)
      00915D 7B 15            [ 1] 2767 	ld	a, (0x15, sp)
      00915F A1 02            [ 1] 2768 	cp	a, #0x02
      009161 25 A2            [ 1] 2769 	jrc	00133$
                                   2770 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 692: }
      009163 5B 15            [ 2] 2771 	addw	sp, #21
      009165 81               [ 4] 2772 	ret
                                   2773 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 696: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
                                   2774 ;	-----------------------------------------
                                   2775 ;	 function hinge
                                   2776 ;	-----------------------------------------
      009166                       2777 _hinge:
      009166 89               [ 2] 2778 	pushw	x
      009167 51               [ 1] 2779 	exgw	x, y
                                   2780 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 698: int16_t g = 0;
      009168 5F               [ 1] 2781 	clrw	x
                                   2782 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 699: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
      009169 72 F2 07         [ 2] 2783 	subw	y, (0x07, sp)
      00916C 90 A3 00 00      [ 2] 2784 	cpw	y, #0x0000
      009170 2D 01            [ 1] 2785 	jrsle	00102$
      009172 93               [ 1] 2786 	ldw	x, y
      009173                       2787 00102$:
                                   2788 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 700: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
      009173 16 07            [ 2] 2789 	ldw	y, (0x07, sp)
      009175 72 F2 05         [ 2] 2790 	subw	y, (0x05, sp)
      009178 17 01            [ 2] 2791 	ldw	(0x01, sp), y
      00917A 13 01            [ 2] 2792 	cpw	x, (0x01, sp)
      00917C 2E 02            [ 1] 2793 	jrsge	00104$
      00917E 1E 01            [ 2] 2794 	ldw	x, (0x01, sp)
      009180                       2795 00104$:
                                   2796 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 701: return (uint16_t)g;
                                   2797 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 702: }
      009180 16 03            [ 2] 2798 	ldw	y, (3, sp)
      009182 5B 08            [ 2] 2799 	addw	sp, #8
      009184 90 FC            [ 2] 2800 	jp	(y)
                                   2801 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 706: static int16_t argmin_ab(int16_t lo, int16_t hi)
                                   2802 ;	-----------------------------------------
                                   2803 ;	 function argmin_ab
                                   2804 ;	-----------------------------------------
      009186                       2805 _argmin_ab:
      009186 52 06            [ 2] 2806 	sub	sp, #6
      009188 51               [ 1] 2807 	exgw	x, y
                                   2808 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 708: uint16_t bc = 0xFFFF;
      009189 5F               [ 1] 2809 	clrw	x
      00918A 5A               [ 2] 2810 	decw	x
      00918B 1F 01            [ 2] 2811 	ldw	(0x01, sp), x
                                   2812 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 709: uint8_t bi = 1;
      00918D A6 01            [ 1] 2813 	ld	a, #0x01
      00918F 6B 03            [ 1] 2814 	ld	(0x03, sp), a
                                   2815 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 710: int16_t a, best = lo;
      009191 17 04            [ 2] 2816 	ldw	(0x04, sp), y
                                   2817 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
      009193                       2818 00108$:
      009193 51               [ 1] 2819 	exgw	x, y
      009194 13 09            [ 2] 2820 	cpw	x, (0x09, sp)
      009196 51               [ 1] 2821 	exgw	x, y
      009197 2C 32            [ 1] 2822 	jrsgt	00106$
                                   2823 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 712: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      009199 CE 01 22         [ 2] 2824 	ldw	x, _d_inter+0
      00919C 90 9F            [ 1] 2825 	ld	a, yl
      00919E 4D               [ 1] 2826 	tnz	a
      00919F 27 04            [ 1] 2827 	jreq	00155$
      0091A1                       2828 00154$:
      0091A1 54               [ 2] 2829 	srlw	x
      0091A2 4A               [ 1] 2830 	dec	a
      0091A3 26 FC            [ 1] 2831 	jrne	00154$
      0091A5                       2832 00155$:
      0091A5 9F               [ 1] 2833 	ld	a, xl
      0091A6 A4 01            [ 1] 2834 	and	a, #0x01
      0091A8 6B 06            [ 1] 2835 	ld	(0x06, sp), a
                                   2836 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 713: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      0091AA 93               [ 1] 2837 	ldw	x, y
      0091AB 58               [ 2] 2838 	sllw	x
      0091AC DE 01 02         [ 2] 2839 	ldw	x, (_d_costs+0, x)
      0091AF 13 01            [ 2] 2840 	cpw	x, (0x01, sp)
      0091B1 25 0C            [ 1] 2841 	jrc	00101$
      0091B3 13 01            [ 2] 2842 	cpw	x, (0x01, sp)
      0091B5 26 10            [ 1] 2843 	jrne	00109$
      0091B7 0D 06            [ 1] 2844 	tnz	(0x06, sp)
      0091B9 27 0C            [ 1] 2845 	jreq	00109$
      0091BB 0D 03            [ 1] 2846 	tnz	(0x03, sp)
      0091BD 26 08            [ 1] 2847 	jrne	00109$
      0091BF                       2848 00101$:
                                   2849 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 714: bc = d_costs[a]; bi = it; best = a;
      0091BF 1F 01            [ 2] 2850 	ldw	(0x01, sp), x
      0091C1 7B 06            [ 1] 2851 	ld	a, (0x06, sp)
      0091C3 6B 03            [ 1] 2852 	ld	(0x03, sp), a
      0091C5 17 04            [ 2] 2853 	ldw	(0x04, sp), y
      0091C7                       2854 00109$:
                                   2855 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
      0091C7 90 5C            [ 1] 2856 	incw	y
      0091C9 20 C8            [ 2] 2857 	jra	00108$
      0091CB                       2858 00106$:
                                   2859 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 717: return best;
      0091CB 1E 04            [ 2] 2860 	ldw	x, (0x04, sp)
                                   2861 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 718: }
      0091CD 5B 06            [ 2] 2862 	addw	sp, #6
      0091CF 90 85            [ 2] 2863 	popw	y
      0091D1 5B 02            [ 2] 2864 	addw	sp, #2
      0091D3 90 FC            [ 2] 2865 	jp	(y)
                                   2866 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 721: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   2867 ;	-----------------------------------------
                                   2868 ;	 function decide
                                   2869 ;	-----------------------------------------
      0091D5                       2870 _decide:
      0091D5 52 18            [ 2] 2871 	sub	sp, #24
      0091D7 1F 15            [ 2] 2872 	ldw	(0x15, sp), x
                                   2873 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: int16_t L = (int16_t)(k1 - k0);
      0091D9 1E 1B            [ 2] 2874 	ldw	x, (0x1b, sp)
      0091DB 72 F0 15         [ 2] 2875 	subw	x, (0x15, sp)
                                   2876 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 726: int16_t acap = (L < A_CAP) ? L : A_CAP;
      0091DE 1F 05            [ 2] 2877 	ldw	(0x05, sp), x
      0091E0 A3 00 0F         [ 2] 2878 	cpw	x, #0x000f
      0091E3 2F 03            [ 1] 2879 	jrslt	00126$
      0091E5 AE 00 0F         [ 2] 2880 	ldw	x, #0x000f
      0091E8                       2881 00126$:
      0091E8 1F 07            [ 2] 2882 	ldw	(0x07, sp), x
                                   2883 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 727: int16_t h0e = c_h0c, h1e = c_h1c;
      0091EA CE 00 46         [ 2] 2884 	ldw	x, _c_h0c+0
      0091ED 1F 09            [ 2] 2885 	ldw	(0x09, sp), x
      0091EF CE 00 48         [ 2] 2886 	ldw	x, _c_h1c+0
      0091F2 1F 0B            [ 2] 2887 	ldw	(0x0b, sp), x
                                   2888 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 729: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
      0091F4 7B 21            [ 1] 2889 	ld	a, (0x21, sp)
      0091F6 A1 05            [ 1] 2890 	cp	a, #0x05
      0091F8 26 19            [ 1] 2891 	jrne	00102$
      0091FA C6 00 4A         [ 1] 2892 	ld	a, _c_d56+0
      0091FD 6B 18            [ 1] 2893 	ld	(0x18, sp), a
      0091FF 49               [ 1] 2894 	rlc	a
      009200 4F               [ 1] 2895 	clr	a
      009201 A2 00            [ 1] 2896 	sbc	a, #0x00
      009203 6B 17            [ 1] 2897 	ld	(0x17, sp), a
      009205 1E 09            [ 2] 2898 	ldw	x, (0x09, sp)
      009207 72 FB 17         [ 2] 2899 	addw	x, (0x17, sp)
      00920A 1F 09            [ 2] 2900 	ldw	(0x09, sp), x
      00920C 1E 0B            [ 2] 2901 	ldw	x, (0x0b, sp)
      00920E 72 FB 17         [ 2] 2902 	addw	x, (0x17, sp)
      009211 1F 0B            [ 2] 2903 	ldw	(0x0b, sp), x
      009213                       2904 00102$:
                                   2905 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 730: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
      009213 7B 21            [ 1] 2906 	ld	a, (0x21, sp)
      009215 A1 06            [ 1] 2907 	cp	a, #0x06
      009217 26 19            [ 1] 2908 	jrne	00104$
      009219 C6 00 4B         [ 1] 2909 	ld	a, _c_d56+1
      00921C 6B 18            [ 1] 2910 	ld	(0x18, sp), a
      00921E 49               [ 1] 2911 	rlc	a
      00921F 4F               [ 1] 2912 	clr	a
      009220 A2 00            [ 1] 2913 	sbc	a, #0x00
      009222 6B 17            [ 1] 2914 	ld	(0x17, sp), a
      009224 1E 09            [ 2] 2915 	ldw	x, (0x09, sp)
      009226 72 FB 17         [ 2] 2916 	addw	x, (0x17, sp)
      009229 1F 09            [ 2] 2917 	ldw	(0x09, sp), x
      00922B 1E 0B            [ 2] 2918 	ldw	x, (0x0b, sp)
      00922D 72 FB 17         [ 2] 2919 	addw	x, (0x17, sp)
      009230 1F 0B            [ 2] 2920 	ldw	(0x0b, sp), x
      009232                       2921 00104$:
                                   2922 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 731: d_inter = 0;
      009232 5F               [ 1] 2923 	clrw	x
      009233 CF 01 22         [ 2] 2924 	ldw	_d_inter+0, x
                                   2925 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
      009236 1E 1D            [ 2] 2926 	ldw	x, (0x1d, sp)
      009238 13 09            [ 2] 2927 	cpw	x, (0x09, sp)
      00923A 2F 04            [ 1] 2928 	jrslt	00273$
      00923C 0F 0D            [ 1] 2929 	clr	(0x0d, sp)
      00923E 20 04            [ 2] 2930 	jra	00274$
      009240                       2931 00273$:
      009240 A6 01            [ 1] 2932 	ld	a, #0x01
      009242 6B 0D            [ 1] 2933 	ld	(0x0d, sp), a
      009244                       2934 00274$:
      009244 1E 09            [ 2] 2935 	ldw	x, (0x09, sp)
      009246 13 1F            [ 2] 2936 	cpw	x, (0x1f, sp)
      009248 2C 04            [ 1] 2937 	jrsgt	00275$
      00924A 0F 0E            [ 1] 2938 	clr	(0x0e, sp)
      00924C 20 04            [ 2] 2939 	jra	00276$
      00924E                       2940 00275$:
      00924E A6 01            [ 1] 2941 	ld	a, #0x01
      009250 6B 0E            [ 1] 2942 	ld	(0x0e, sp), a
      009252                       2943 00276$:
      009252 5F               [ 1] 2944 	clrw	x
      009253 1F 17            [ 2] 2945 	ldw	(0x17, sp), x
      009255                       2946 00121$:
      009255 1E 17            [ 2] 2947 	ldw	x, (0x17, sp)
      009257 13 07            [ 2] 2948 	cpw	x, (0x07, sp)
      009259 2D 03            [ 1] 2949 	jrsle	00277$
      00925B CC 93 04         [ 2] 2950 	jp	00117$
      00925E                       2951 00277$:
                                   2952 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 735: if (a == 0) {
      00925E 1E 17            [ 2] 2953 	ldw	x, (0x17, sp)
      009260 26 1C            [ 1] 2954 	jrne	00113$
                                   2955 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 736: c = hinge(u, v, h0e);
      009262 1E 09            [ 2] 2956 	ldw	x, (0x09, sp)
      009264 89               [ 2] 2957 	pushw	x
      009265 1E 21            [ 2] 2958 	ldw	x, (0x21, sp)
      009267 89               [ 2] 2959 	pushw	x
      009268 1E 21            [ 2] 2960 	ldw	x, (0x21, sp)
      00926A CD 91 66         [ 4] 2961 	call	_hinge
      00926D 1F 0F            [ 2] 2962 	ldw	(0x0f, sp), x
                                   2963 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 737: it = (u < h0e && h0e <= v);
      00926F 0D 0D            [ 1] 2964 	tnz	(0x0d, sp)
      009271 27 04            [ 1] 2965 	jreq	00127$
      009273 0D 0E            [ 1] 2966 	tnz	(0x0e, sp)
      009275 27 03            [ 1] 2967 	jreq	00128$
      009277                       2968 00127$:
      009277 4F               [ 1] 2969 	clr	a
      009278 20 61            [ 2] 2970 	jra	00114$
      00927A                       2971 00128$:
      00927A A6 01            [ 1] 2972 	ld	a, #0x01
      00927C 20 5D            [ 2] 2973 	jra	00114$
      00927E                       2974 00113$:
                                   2975 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 739: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
      00927E 16 17            [ 2] 2976 	ldw	y, (0x17, sp)
      009280 17 11            [ 2] 2977 	ldw	(0x11, sp), y
      009282 93               [ 1] 2978 	ldw	x, y
      009283 5A               [ 2] 2979 	decw	x
      009284 4F               [ 1] 2980 	clr	a
      009285 02               [ 1] 2981 	rlwa	x
      009286 58               [ 2] 2982 	sllw	x
      009287 72 FB 0B         [ 2] 2983 	addw	x, (0x0b, sp)
                                   2984 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 740: c = hinge(u, v, h);
      00928A 1F 13            [ 2] 2985 	ldw	(0x13, sp), x
      00928C 89               [ 2] 2986 	pushw	x
      00928D 1E 21            [ 2] 2987 	ldw	x, (0x21, sp)
      00928F 89               [ 2] 2988 	pushw	x
      009290 1E 21            [ 2] 2989 	ldw	x, (0x21, sp)
      009292 CD 91 66         [ 4] 2990 	call	_hinge
      009295 1F 0F            [ 2] 2991 	ldw	(0x0f, sp), x
                                   2992 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 741: it = (u < h && h <= v);
      009297 1E 1D            [ 2] 2993 	ldw	x, (0x1d, sp)
      009299 13 13            [ 2] 2994 	cpw	x, (0x13, sp)
      00929B 2E 06            [ 1] 2995 	jrsge	00130$
      00929D 1E 13            [ 2] 2996 	ldw	x, (0x13, sp)
      00929F 13 1F            [ 2] 2997 	cpw	x, (0x1f, sp)
      0092A1 2D 02            [ 1] 2998 	jrsle	00131$
      0092A3                       2999 00130$:
      0092A3 4F               [ 1] 3000 	clr	a
      0092A4 C5                    3001 	.byte 0xc5
      0092A5                       3002 00131$:
      0092A5 A6 01            [ 1] 3003 	ld	a, #0x01
      0092A7                       3004 00132$:
                                   3005 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 742: if (a < L) {
      0092A7 1E 17            [ 2] 3006 	ldw	x, (0x17, sp)
      0092A9 13 05            [ 2] 3007 	cpw	x, (0x05, sp)
      0092AB 2E 2E            [ 1] 3008 	jrsge	00114$
                                   3009 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 743: int16_t h2 = (int16_t)(a * BIT_U + h0e);
      0092AD 02               [ 1] 3010 	rlwa	x
      0092AE 7B 12            [ 1] 3011 	ld	a, (0x12, sp)
      0092B0 01               [ 1] 3012 	rrwa	x
      0092B1 41               [ 1] 3013 	exg	a, xl
      0092B2 4F               [ 1] 3014 	clr	a
      0092B3 41               [ 1] 3015 	exg	a, xl
      0092B4 58               [ 2] 3016 	sllw	x
      0092B5 72 FB 09         [ 2] 3017 	addw	x, (0x09, sp)
      0092B8 1F 13            [ 2] 3018 	ldw	(0x13, sp), x
                                   3019 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 744: uint16_t c2 = hinge(u, v, h2);
      0092BA 88               [ 1] 3020 	push	a
      0092BB 1E 14            [ 2] 3021 	ldw	x, (0x14, sp)
      0092BD 89               [ 2] 3022 	pushw	x
      0092BE 1E 22            [ 2] 3023 	ldw	x, (0x22, sp)
      0092C0 89               [ 2] 3024 	pushw	x
      0092C1 1E 22            [ 2] 3025 	ldw	x, (0x22, sp)
      0092C3 CD 91 66         [ 4] 3026 	call	_hinge
      0092C6 84               [ 1] 3027 	pop	a
                                   3028 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 745: if (c2 < c) c = c2;
      0092C7 13 0F            [ 2] 3029 	cpw	x, (0x0f, sp)
      0092C9 24 02            [ 1] 3030 	jrnc	00106$
      0092CB 1F 0F            [ 2] 3031 	ldw	(0x0f, sp), x
      0092CD                       3032 00106$:
                                   3033 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 746: if (u < h2 && h2 <= v) it = 1;
      0092CD 1E 1D            [ 2] 3034 	ldw	x, (0x1d, sp)
      0092CF 13 13            [ 2] 3035 	cpw	x, (0x13, sp)
      0092D1 2E 08            [ 1] 3036 	jrsge	00114$
      0092D3 1E 13            [ 2] 3037 	ldw	x, (0x13, sp)
      0092D5 13 1F            [ 2] 3038 	cpw	x, (0x1f, sp)
      0092D7 2C 02            [ 1] 3039 	jrsgt	00114$
      0092D9 A6 01            [ 1] 3040 	ld	a, #0x01
      0092DB                       3041 00114$:
                                   3042 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 749: d_costs[a] = c;
      0092DB 1E 17            [ 2] 3043 	ldw	x, (0x17, sp)
      0092DD 58               [ 2] 3044 	sllw	x
      0092DE 16 0F            [ 2] 3045 	ldw	y, (0x0f, sp)
      0092E0 DF 01 02         [ 2] 3046 	ldw	((_d_costs+0), x), y
                                   3047 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 750: if (it) d_inter |= (uint16_t)(1u << a);
      0092E3 4D               [ 1] 3048 	tnz	a
      0092E4 27 16            [ 1] 3049 	jreq	00122$
      0092E6 5F               [ 1] 3050 	clrw	x
      0092E7 5C               [ 1] 3051 	incw	x
      0092E8 7B 18            [ 1] 3052 	ld	a, (0x18, sp)
      0092EA 27 04            [ 1] 3053 	jreq	00289$
      0092EC                       3054 00288$:
      0092EC 58               [ 2] 3055 	sllw	x
      0092ED 4A               [ 1] 3056 	dec	a
      0092EE 26 FC            [ 1] 3057 	jrne	00288$
      0092F0                       3058 00289$:
      0092F0 9F               [ 1] 3059 	ld	a, xl
      0092F1 CA 01 23         [ 1] 3060 	or	a, _d_inter+1
      0092F4 02               [ 1] 3061 	rlwa	x
      0092F5 CA 01 22         [ 1] 3062 	or	a, _d_inter+0
      0092F8 95               [ 1] 3063 	ld	xh, a
      0092F9 CF 01 22         [ 2] 3064 	ldw	_d_inter+0, x
      0092FC                       3065 00122$:
                                   3066 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
      0092FC 1E 17            [ 2] 3067 	ldw	x, (0x17, sp)
      0092FE 5C               [ 1] 3068 	incw	x
      0092FF 1F 17            [ 2] 3069 	ldw	(0x17, sp), x
      009301 CC 92 55         [ 2] 3070 	jp	00121$
      009304                       3071 00117$:
                                   3072 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 753: *a_free = argmin_ab(0, acap);
      009304 1E 24            [ 2] 3073 	ldw	x, (0x24, sp)
      009306 89               [ 2] 3074 	pushw	x
      009307 16 09            [ 2] 3075 	ldw	y, (0x09, sp)
      009309 90 89            [ 2] 3076 	pushw	y
      00930B 5F               [ 1] 3077 	clrw	x
      00930C CD 91 86         [ 4] 3078 	call	_argmin_ab
      00930F 51               [ 1] 3079 	exgw	x, y
      009310 85               [ 2] 3080 	popw	x
      009311 FF               [ 2] 3081 	ldw	(x), y
                                   3082 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 754: a_bounds(k0, k1, &amin, &amax);
      009312 96               [ 1] 3083 	ldw	x, sp
      009313 1C 00 03         [ 2] 3084 	addw	x, #3
      009316 89               [ 2] 3085 	pushw	x
      009317 96               [ 1] 3086 	ldw	x, sp
      009318 1C 00 03         [ 2] 3087 	addw	x, #3
      00931B 89               [ 2] 3088 	pushw	x
      00931C 1E 1F            [ 2] 3089 	ldw	x, (0x1f, sp)
      00931E 89               [ 2] 3090 	pushw	x
      00931F 1E 1B            [ 2] 3091 	ldw	x, (0x1b, sp)
      009321 CD 8A 34         [ 4] 3092 	call	_a_bounds
                                   3093 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 755: lo = (amin > 0) ? amin : 0;
      009324 1E 01            [ 2] 3094 	ldw	x, (0x01, sp)
      009326 A3 00 00         [ 2] 3095 	cpw	x, #0x0000
      009329 2C 01            [ 1] 3096 	jrsgt	00134$
      00932B 5F               [ 1] 3097 	clrw	x
      00932C                       3098 00134$:
      00932C 1F 13            [ 2] 3099 	ldw	(0x13, sp), x
                                   3100 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 756: hi = (amax < acap) ? amax : acap;
      00932E 1E 03            [ 2] 3101 	ldw	x, (0x03, sp)
      009330 13 07            [ 2] 3102 	cpw	x, (0x07, sp)
      009332 2E 03            [ 1] 3103 	jrsge	00135$
      009334 1E 03            [ 2] 3104 	ldw	x, (0x03, sp)
      009336 C5                    3105 	.byte 0xc5
      009337                       3106 00135$:
      009337 1E 07            [ 2] 3107 	ldw	x, (0x07, sp)
      009339                       3108 00136$:
      009339 1F 17            [ 2] 3109 	ldw	(0x17, sp), x
                                   3110 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 757: if (lo > hi) { lo = 0; hi = acap; }
      00933B 1E 13            [ 2] 3111 	ldw	x, (0x13, sp)
      00933D 13 17            [ 2] 3112 	cpw	x, (0x17, sp)
      00933F 2D 07            [ 1] 3113 	jrsle	00119$
      009341 5F               [ 1] 3114 	clrw	x
      009342 1F 13            [ 2] 3115 	ldw	(0x13, sp), x
      009344 16 07            [ 2] 3116 	ldw	y, (0x07, sp)
      009346 17 17            [ 2] 3117 	ldw	(0x17, sp), y
      009348                       3118 00119$:
                                   3119 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: *a_hat = argmin_ab(lo, hi);
      009348 1E 22            [ 2] 3120 	ldw	x, (0x22, sp)
      00934A 89               [ 2] 3121 	pushw	x
      00934B 16 19            [ 2] 3122 	ldw	y, (0x19, sp)
      00934D 90 89            [ 2] 3123 	pushw	y
      00934F 1E 17            [ 2] 3124 	ldw	x, (0x17, sp)
      009351 CD 91 86         [ 4] 3125 	call	_argmin_ab
      009354 51               [ 1] 3126 	exgw	x, y
      009355 85               [ 2] 3127 	popw	x
      009356 FF               [ 2] 3128 	ldw	(x), y
                                   3129 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 759: *lo_out = lo; *hi_out = hi;
      009357 1E 26            [ 2] 3130 	ldw	x, (0x26, sp)
      009359 16 13            [ 2] 3131 	ldw	y, (0x13, sp)
      00935B FF               [ 2] 3132 	ldw	(x), y
      00935C 1E 28            [ 2] 3133 	ldw	x, (0x28, sp)
      00935E 16 17            [ 2] 3134 	ldw	y, (0x17, sp)
      009360 FF               [ 2] 3135 	ldw	(x), y
                                   3136 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 760: return acap;
      009361 1E 07            [ 2] 3137 	ldw	x, (0x07, sp)
                                   3138 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 761: }
      009363 16 19            [ 2] 3139 	ldw	y, (25, sp)
      009365 5B 29            [ 2] 3140 	addw	sp, #41
      009367 90 FC            [ 2] 3141 	jp	(y)
                                   3142 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 764: static void cand_insert(uint16_t k, uint8_t m)
                                   3143 ;	-----------------------------------------
                                   3144 ;	 function cand_insert
                                   3145 ;	-----------------------------------------
      009369                       3146 _cand_insert:
      009369 52 07            [ 2] 3147 	sub	sp, #7
      00936B 1F 05            [ 2] 3148 	ldw	(0x05, sp), x
      00936D 6B 04            [ 1] 3149 	ld	(0x04, sp), a
                                   3150 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 766: uint8_t i = v_ncand, j;
      00936F C6 01 33         [ 1] 3151 	ld	a, _v_ncand+0
                                   3152 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 767: while (i > 0 && v_cand_m[i - 1] > m) i--;
      009372 6B 07            [ 1] 3153 	ld	(0x07, sp), a
      009374                       3154 00102$:
      009374 4D               [ 1] 3155 	tnz	a
      009375 27 17            [ 1] 3156 	jreq	00132$
      009377 97               [ 1] 3157 	ld	xl, a
      009378 5A               [ 2] 3158 	decw	x
      009379 88               [ 1] 3159 	push	a
      00937A 9F               [ 1] 3160 	ld	a, xl
      00937B 49               [ 1] 3161 	rlc	a
      00937C 4F               [ 1] 3162 	clr	a
      00937D A2 00            [ 1] 3163 	sbc	a, #0x00
      00937F 95               [ 1] 3164 	ld	xh, a
      009380 84               [ 1] 3165 	pop	a
      009381 1C 01 2E         [ 2] 3166 	addw	x, #(_v_cand_m+0)
      009384 88               [ 1] 3167 	push	a
      009385 F6               [ 1] 3168 	ld	a, (x)
      009386 11 05            [ 1] 3169 	cp	a, (0x05, sp)
      009388 84               [ 1] 3170 	pop	a
      009389 23 03            [ 2] 3171 	jrule	00132$
      00938B 4A               [ 1] 3172 	dec	a
      00938C 20 E6            [ 2] 3173 	jra	00102$
      00938E                       3174 00132$:
      00938E 6B 01            [ 1] 3175 	ld	(0x01, sp), a
                                   3176 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 768: if (i >= A_MAX) return;
      009390 A1 05            [ 1] 3177 	cp	a, #0x05
      009392 24 60            [ 1] 3178 	jrnc	00112$
                                   3179 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 769: j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
      009394 C6 01 33         [ 1] 3180 	ld	a, _v_ncand+0
      009397 A1 05            [ 1] 3181 	cp	a, #0x05
      009399 24 03            [ 1] 3182 	jrnc	00114$
      00939B 7B 07            [ 1] 3183 	ld	a, (0x07, sp)
      00939D C5                    3184 	.byte 0xc5
      00939E                       3185 00114$:
      00939E A6 04            [ 1] 3186 	ld	a, #0x04
      0093A0                       3187 00115$:
      0093A0 6B 07            [ 1] 3188 	ld	(0x07, sp), a
                                   3189 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 770: while (j > i) {
      0093A2                       3190 00107$:
                                   3191 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 771: v_cand_t[j] = v_cand_t[j - 1];
      0093A2 7B 07            [ 1] 3192 	ld	a, (0x07, sp)
      0093A4 11 01            [ 1] 3193 	cp	a, (0x01, sp)
      0093A6 23 2E            [ 2] 3194 	jrule	00109$
      0093A8 5F               [ 1] 3195 	clrw	x
      0093A9 97               [ 1] 3196 	ld	xl, a
      0093AA 58               [ 2] 3197 	sllw	x
      0093AB 1C 01 24         [ 2] 3198 	addw	x, #(_v_cand_t+0)
      0093AE 51               [ 1] 3199 	exgw	x, y
      0093AF 7B 07            [ 1] 3200 	ld	a, (0x07, sp)
      0093B1 4A               [ 1] 3201 	dec	a
      0093B2 6B 03            [ 1] 3202 	ld	(0x03, sp), a
      0093B4 49               [ 1] 3203 	rlc	a
      0093B5 4F               [ 1] 3204 	clr	a
      0093B6 A2 00            [ 1] 3205 	sbc	a, #0x00
      0093B8 6B 02            [ 1] 3206 	ld	(0x02, sp), a
      0093BA 1E 02            [ 2] 3207 	ldw	x, (0x02, sp)
      0093BC 58               [ 2] 3208 	sllw	x
      0093BD DE 01 24         [ 2] 3209 	ldw	x, (_v_cand_t+0, x)
      0093C0 90 FF            [ 2] 3210 	ldw	(y), x
                                   3211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 772: v_cand_m[j] = v_cand_m[j - 1];
      0093C2 5F               [ 1] 3212 	clrw	x
      0093C3 7B 07            [ 1] 3213 	ld	a, (0x07, sp)
      0093C5 97               [ 1] 3214 	ld	xl, a
      0093C6 1C 01 2E         [ 2] 3215 	addw	x, #(_v_cand_m+0)
      0093C9 16 02            [ 2] 3216 	ldw	y, (0x02, sp)
      0093CB 72 A9 01 2E      [ 2] 3217 	addw	y, #(_v_cand_m+0)
      0093CF 90 F6            [ 1] 3218 	ld	a, (y)
      0093D1 F7               [ 1] 3219 	ld	(x), a
                                   3220 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 773: j--;
      0093D2 0A 07            [ 1] 3221 	dec	(0x07, sp)
      0093D4 20 CC            [ 2] 3222 	jra	00107$
      0093D6                       3223 00109$:
                                   3224 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 775: v_cand_t[i] = k;
      0093D6 7B 01            [ 1] 3225 	ld	a, (0x01, sp)
      0093D8 5F               [ 1] 3226 	clrw	x
      0093D9 97               [ 1] 3227 	ld	xl, a
      0093DA 58               [ 2] 3228 	sllw	x
      0093DB 16 05            [ 2] 3229 	ldw	y, (0x05, sp)
      0093DD DF 01 24         [ 2] 3230 	ldw	((_v_cand_t+0), x), y
                                   3231 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 776: v_cand_m[i] = m;
      0093E0 5F               [ 1] 3232 	clrw	x
      0093E1 7B 01            [ 1] 3233 	ld	a, (0x01, sp)
      0093E3 97               [ 1] 3234 	ld	xl, a
      0093E4 7B 04            [ 1] 3235 	ld	a, (0x04, sp)
      0093E6 D7 01 2E         [ 1] 3236 	ld	((_v_cand_m+0), x), a
                                   3237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 777: if (v_ncand < A_MAX) v_ncand++;
      0093E9 C6 01 33         [ 1] 3238 	ld	a, _v_ncand+0
      0093EC A1 05            [ 1] 3239 	cp	a, #0x05
      0093EE 24 04            [ 1] 3240 	jrnc	00112$
      0093F0 72 5C 01 33      [ 1] 3241 	inc	_v_ncand+0
      0093F4                       3242 00112$:
                                   3243 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 778: }
      0093F4 5B 07            [ 2] 3244 	addw	sp, #7
      0093F6 81               [ 4] 3245 	ret
                                   3246 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 780: static void decide_pass(void)
                                   3247 ;	-----------------------------------------
                                   3248 ;	 function decide_pass
                                   3249 ;	-----------------------------------------
      0093F7                       3250 _decide_pass:
      0093F7 52 21            [ 2] 3251 	sub	sp, #33
                                   3252 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 784: for (t = 0; t < NBB; t++) d_bits[t] = 0;
      0093F9 4F               [ 1] 3253 	clr	a
      0093FA                       3254 00168$:
      0093FA 5F               [ 1] 3255 	clrw	x
      0093FB 97               [ 1] 3256 	ld	xl, a
      0093FC 72 4F 00 E4      [ 1] 3257 	clr	((_d_bits+0), x)
      009400 4C               [ 1] 3258 	inc	a
      009401 A1 18            [ 1] 3259 	cp	a, #0x18
      009403 25 F5            [ 1] 3260 	jrc	00168$
                                   3261 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 785: d_infeas = 0; d_laberr = 0; d_nseg = 0;
      009405 5F               [ 1] 3262 	clrw	x
      009406 CF 00 FC         [ 2] 3263 	ldw	_d_infeas+0, x
      009409 5F               [ 1] 3264 	clrw	x
      00940A CF 00 FE         [ 2] 3265 	ldw	_d_laberr+0, x
      00940D 5F               [ 1] 3266 	clrw	x
      00940E CF 01 00         [ 2] 3267 	ldw	_d_nseg+0, x
                                   3268 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 786: v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1;
      009411 72 5F 01 33      [ 1] 3269 	clr	_v_ncand+0
      009415 5F               [ 1] 3270 	clrw	x
      009416 CF 01 34         [ 2] 3271 	ldw	_v_nweak+0, x
      009419 5F               [ 1] 3272 	clrw	x
      00941A CF 01 36         [ 2] 3273 	ldw	_v_ntied+0, x
      00941D 5F               [ 1] 3274 	clrw	x
      00941E 5A               [ 2] 3275 	decw	x
      00941F CF 01 38         [ 2] 3276 	ldw	_v_tiepend+0, x
                                   3277 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 787: ss_init();
      009422 CD 87 C4         [ 4] 3278 	call	_ss_init
                                   3279 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 788: while (ss_next(&sg)) {
      009425                       3280 00165$:
      009425 96               [ 1] 3281 	ldw	x, sp
      009426 5C               [ 1] 3282 	incw	x
      009427 CD 88 06         [ 4] 3283 	call	_ss_next
      00942A 4D               [ 1] 3284 	tnz	a
      00942B 26 03            [ 1] 3285 	jrne	00557$
      00942D CC 96 61         [ 2] 3286 	jp	00185$
      009430                       3287 00557$:
                                   3288 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 791: int16_t tie_here = -1, ins0 = -1, ins1 = -1;
      009430 5F               [ 1] 3289 	clrw	x
      009431 5A               [ 2] 3290 	decw	x
      009432 1F 12            [ 2] 3291 	ldw	(0x12, sp), x
      009434 5F               [ 1] 3292 	clrw	x
      009435 5A               [ 2] 3293 	decw	x
      009436 1F 19            [ 2] 3294 	ldw	(0x19, sp), x
      009438 5F               [ 1] 3295 	clrw	x
      009439 5A               [ 2] 3296 	decw	x
      00943A 1F 1B            [ 2] 3297 	ldw	(0x1b, sp), x
                                   3298 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 794: d_nseg++;
      00943C CE 01 00         [ 2] 3299 	ldw	x, _d_nseg+0
      00943F 5C               [ 1] 3300 	incw	x
      009440 CF 01 00         [ 2] 3301 	ldw	_d_nseg+0, x
                                   3302 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
      009443 96               [ 1] 3303 	ldw	x, sp
      009444 5C               [ 1] 3304 	incw	x
      009445 1F 14            [ 2] 3305 	ldw	(0x14, sp), x
      009447 FE               [ 2] 3306 	ldw	x, (x)
      009448 1F 17            [ 2] 3307 	ldw	(0x17, sp), x
      00944A A3 00 C0         [ 2] 3308 	cpw	x, #0x00c0
      00944D 24 D6            [ 1] 3309 	jrnc	00165$
                                   3310 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 797: &a_hat, &a_free, &lo, &hi);
                                   3311 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 796: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
      00944F 7B 09            [ 1] 3312 	ld	a, (0x09, sp)
      009451 16 07            [ 2] 3313 	ldw	y, (0x07, sp)
      009453 17 1E            [ 2] 3314 	ldw	(0x1e, sp), y
      009455 16 05            [ 2] 3315 	ldw	y, (0x05, sp)
      009457 17 20            [ 2] 3316 	ldw	(0x20, sp), y
      009459 16 03            [ 2] 3317 	ldw	y, (0x03, sp)
      00945B 96               [ 1] 3318 	ldw	x, sp
      00945C 1C 00 10         [ 2] 3319 	addw	x, #16
      00945F 89               [ 2] 3320 	pushw	x
      009460 96               [ 1] 3321 	ldw	x, sp
      009461 1C 00 10         [ 2] 3322 	addw	x, #16
      009464 89               [ 2] 3323 	pushw	x
      009465 96               [ 1] 3324 	ldw	x, sp
      009466 1C 00 10         [ 2] 3325 	addw	x, #16
      009469 89               [ 2] 3326 	pushw	x
      00946A 96               [ 1] 3327 	ldw	x, sp
      00946B 1C 00 10         [ 2] 3328 	addw	x, #16
      00946E 89               [ 2] 3329 	pushw	x
      00946F 88               [ 1] 3330 	push	a
      009470 1E 27            [ 2] 3331 	ldw	x, (0x27, sp)
      009472 89               [ 2] 3332 	pushw	x
      009473 1E 2B            [ 2] 3333 	ldw	x, (0x2b, sp)
      009475 89               [ 2] 3334 	pushw	x
      009476 90 89            [ 2] 3335 	pushw	y
      009478 1E 26            [ 2] 3336 	ldw	x, (0x26, sp)
      00947A CD 91 D5         [ 4] 3337 	call	_decide
      00947D 1F 1D            [ 2] 3338 	ldw	(0x1d, sp), x
                                   3339 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 798: c_hat = d_costs[a_hat];
      00947F 1E 0A            [ 2] 3340 	ldw	x, (0x0a, sp)
      009481 58               [ 2] 3341 	sllw	x
      009482 DE 01 02         [ 2] 3342 	ldw	x, (_d_costs+0, x)
                                   3343 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 799: if (c_hat > INFEAS_U) d_infeas++;
      009485 A3 00 A0         [ 2] 3344 	cpw	x, #0x00a0
      009488 23 07            [ 2] 3345 	jrule	00105$
      00948A CE 00 FC         [ 2] 3346 	ldw	x, _d_infeas+0
      00948D 5C               [ 1] 3347 	incw	x
      00948E CF 00 FC         [ 2] 3348 	ldw	_d_infeas+0, x
      009491                       3349 00105$:
                                   3350 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: kk1 = (sg.k1 < NB) ? sg.k1 : NB;
      009491 1E 03            [ 2] 3351 	ldw	x, (0x03, sp)
      009493 A3 00 C0         [ 2] 3352 	cpw	x, #0x00c0
      009496 24 03            [ 1] 3353 	jrnc	00187$
      009498 9F               [ 1] 3354 	ld	a, xl
      009499 20 03            [ 2] 3355 	jra	00188$
      00949B                       3356 00187$:
      00949B A6 C0            [ 1] 3357 	ld	a, #0xc0
      00949D 5F               [ 1] 3358 	clrw	x
      00949E                       3359 00188$:
      00949E 6B 17            [ 1] 3360 	ld	(0x17, sp), a
      0094A0 02               [ 1] 3361 	rlwa	x
      0094A1 6B 16            [ 1] 3362 	ld	(0x16, sp), a
      0094A3 01               [ 1] 3363 	rrwa	x
                                   3364 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 801: known_all = 1;
      0094A4 A6 01            [ 1] 3365 	ld	a, #0x01
      0094A6 6B 1F            [ 1] 3366 	ld	(0x1f, sp), a
                                   3367 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
      0094A8 1E 14            [ 2] 3368 	ldw	x, (0x14, sp)
      0094AA FE               [ 2] 3369 	ldw	x, (x)
      0094AB                       3370 00171$:
      0094AB 13 16            [ 2] 3371 	cpw	x, (0x16, sp)
      0094AD 24 0F            [ 1] 3372 	jrnc	00108$
                                   3373 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 803: if (known_bit(t) < 0) { known_all = 0; break; }
      0094AF 89               [ 2] 3374 	pushw	x
      0094B0 CD 81 47         [ 4] 3375 	call	_known_bit
      0094B3 85               [ 2] 3376 	popw	x
      0094B4 4D               [ 1] 3377 	tnz	a
      0094B5 2A 04            [ 1] 3378 	jrpl	00172$
      0094B7 0F 1F            [ 1] 3379 	clr	(0x1f, sp)
      0094B9 20 03            [ 2] 3380 	jra	00108$
      0094BB                       3381 00172$:
                                   3382 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
      0094BB 5C               [ 1] 3383 	incw	x
      0094BC 20 ED            [ 2] 3384 	jra	00171$
      0094BE                       3385 00108$:
                                   3386 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 804: dead = 0; nins = 0;
      0094BE 0F 20            [ 1] 3387 	clr	(0x20, sp)
                                   3388 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
      0094C0 0F 21            [ 1] 3389 	clr	(0x21, sp)
      0094C2 5F               [ 1] 3390 	clrw	x
      0094C3                       3391 00174$:
      0094C3 13 1D            [ 2] 3392 	cpw	x, (0x1d, sp)
      0094C5 2C 16            [ 1] 3393 	jrsgt	00111$
                                   3394 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 806: if ((d_inter >> a) & 1) nins++;
      0094C7 90 CE 01 22      [ 2] 3395 	ldw	y, _d_inter+0
      0094CB 9F               [ 1] 3396 	ld	a, xl
      0094CC 4D               [ 1] 3397 	tnz	a
      0094CD 27 05            [ 1] 3398 	jreq	00565$
      0094CF                       3399 00564$:
      0094CF 90 54            [ 2] 3400 	srlw	y
      0094D1 4A               [ 1] 3401 	dec	a
      0094D2 26 FB            [ 1] 3402 	jrne	00564$
      0094D4                       3403 00565$:
      0094D4 90 54            [ 2] 3404 	srlw	y
      0094D6 24 02            [ 1] 3405 	jrnc	00175$
      0094D8 0C 21            [ 1] 3406 	inc	(0x21, sp)
      0094DA                       3407 00175$:
                                   3408 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
      0094DA 5C               [ 1] 3409 	incw	x
      0094DB 20 E6            [ 2] 3410 	jra	00174$
      0094DD                       3411 00111$:
                                   3412 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: if (nins >= 2) dead = 1;
      0094DD 7B 21            [ 1] 3413 	ld	a, (0x21, sp)
      0094DF A1 02            [ 1] 3414 	cp	a, #0x02
      0094E1 25 04            [ 1] 3415 	jrc	00113$
      0094E3 A6 01            [ 1] 3416 	ld	a, #0x01
      0094E5 6B 20            [ 1] 3417 	ld	(0x20, sp), a
      0094E7                       3418 00113$:
                                   3419 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 808: if (known_all && lo == hi && a_free != lo && !dead)
      0094E7 0D 1F            [ 1] 3420 	tnz	(0x1f, sp)
      0094E9 27 17            [ 1] 3421 	jreq	00115$
      0094EB 1E 0E            [ 2] 3422 	ldw	x, (0x0e, sp)
      0094ED 13 10            [ 2] 3423 	cpw	x, (0x10, sp)
      0094EF 26 11            [ 1] 3424 	jrne	00115$
      0094F1 1E 0C            [ 2] 3425 	ldw	x, (0x0c, sp)
      0094F3 13 0E            [ 2] 3426 	cpw	x, (0x0e, sp)
      0094F5 27 0B            [ 1] 3427 	jreq	00115$
      0094F7 0D 20            [ 1] 3428 	tnz	(0x20, sp)
      0094F9 26 07            [ 1] 3429 	jrne	00115$
                                   3430 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 809: d_laberr++;
      0094FB CE 00 FE         [ 2] 3431 	ldw	x, _d_laberr+0
      0094FE 5C               [ 1] 3432 	incw	x
      0094FF CF 00 FE         [ 2] 3433 	ldw	_d_laberr+0, x
      009502                       3434 00115$:
                                   3435 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
      009502 1E 0E            [ 2] 3436 	ldw	x, (0x0e, sp)
      009504 0F 1F            [ 1] 3437 	clr	(0x1f, sp)
      009506                       3438 00177$:
      009506 13 10            [ 2] 3439 	cpw	x, (0x10, sp)
      009508 2C 25            [ 1] 3440 	jrsgt	00126$
                                   3441 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 815: if ((d_inter >> a) & 1) {
      00950A 90 CE 01 22      [ 2] 3442 	ldw	y, _d_inter+0
      00950E 9F               [ 1] 3443 	ld	a, xl
      00950F 4D               [ 1] 3444 	tnz	a
      009510 27 05            [ 1] 3445 	jreq	00578$
      009512                       3446 00577$:
      009512 90 54            [ 2] 3447 	srlw	y
      009514 4A               [ 1] 3448 	dec	a
      009515 26 FB            [ 1] 3449 	jrne	00577$
      009517                       3450 00578$:
      009517 90 54            [ 2] 3451 	srlw	y
      009519 24 11            [ 1] 3452 	jrnc	00178$
                                   3453 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 816: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
      00951B 0D 1F            [ 1] 3454 	tnz	(0x1f, sp)
      00951D 26 04            [ 1] 3455 	jrne	00122$
      00951F 1F 19            [ 2] 3456 	ldw	(0x19, sp), x
      009521 20 07            [ 2] 3457 	jra	00123$
      009523                       3458 00122$:
      009523 7B 1F            [ 1] 3459 	ld	a, (0x1f, sp)
      009525 4A               [ 1] 3460 	dec	a
      009526 26 02            [ 1] 3461 	jrne	00123$
      009528 1F 1B            [ 2] 3462 	ldw	(0x1b, sp), x
      00952A                       3463 00123$:
                                   3464 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 817: nins++;
      00952A 0C 1F            [ 1] 3465 	inc	(0x1f, sp)
      00952C                       3466 00178$:
                                   3467 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
      00952C 5C               [ 1] 3468 	incw	x
      00952D 20 D7            [ 2] 3469 	jra	00177$
      00952F                       3470 00126$:
                                   3471 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
      00952F 1E 14            [ 2] 3472 	ldw	x, (0x14, sp)
      009531 FE               [ 2] 3473 	ldw	x, (x)
      009532 1F 20            [ 2] 3474 	ldw	(0x20, sp), x
                                   3475 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 820: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
      009534 7B 1F            [ 1] 3476 	ld	a, (0x1f, sp)
      009536 A1 02            [ 1] 3477 	cp	a, #0x02
      009538 25 18            [ 1] 3478 	jrc	00130$
      00953A 1E 0A            [ 2] 3479 	ldw	x, (0x0a, sp)
      00953C 13 19            [ 2] 3480 	cpw	x, (0x19, sp)
      00953E 27 06            [ 1] 3481 	jreq	00129$
      009540 1E 0A            [ 2] 3482 	ldw	x, (0x0a, sp)
      009542 13 1B            [ 2] 3483 	cpw	x, (0x1b, sp)
      009544 26 0C            [ 1] 3484 	jrne	00130$
      009546                       3485 00129$:
                                   3486 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 821: uint16_t tt = (uint16_t)(sg.k0 + ins0);
      009546 1E 19            [ 2] 3487 	ldw	x, (0x19, sp)
      009548 72 FB 20         [ 2] 3488 	addw	x, (0x20, sp)
                                   3489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 822: if (tt < NB) tie_here = (int16_t)tt;
      00954B A3 00 C0         [ 2] 3490 	cpw	x, #0x00c0
      00954E 24 02            [ 1] 3491 	jrnc	00130$
      009550 1F 12            [ 2] 3492 	ldw	(0x12, sp), x
      009552                       3493 00130$:
                                   3494 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
      009552 16 20            [ 2] 3495 	ldw	y, (0x20, sp)
      009554 17 1E            [ 2] 3496 	ldw	(0x1e, sp), y
      009556                       3497 00183$:
      009556 1E 1E            [ 2] 3498 	ldw	x, (0x1e, sp)
      009558 13 16            [ 2] 3499 	cpw	x, (0x16, sp)
      00955A 25 03            [ 1] 3500 	jrc	00592$
      00955C CC 96 3A         [ 2] 3501 	jp	00159$
      00955F                       3502 00592$:
                                   3503 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 826: int16_t off = (int16_t)(t - sg.k0);
      00955F 1E 14            [ 2] 3504 	ldw	x, (0x14, sp)
      009561 FE               [ 2] 3505 	ldw	x, (x)
      009562 50               [ 2] 3506 	negw	x
      009563 72 FB 1E         [ 2] 3507 	addw	x, (0x1e, sp)
      009566 1F 18            [ 2] 3508 	ldw	(0x18, sp), x
                                   3509 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 827: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
      009568 5F               [ 1] 3510 	clrw	x
      009569 5A               [ 2] 3511 	decw	x
      00956A 1F 1A            [ 2] 3512 	ldw	(0x1a, sp), x
      00956C 5F               [ 1] 3513 	clrw	x
      00956D 5A               [ 2] 3514 	decw	x
      00956E 1F 1C            [ 2] 3515 	ldw	(0x1c, sp), x
                                   3516 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 828: if (off < a_hat) BSET(d_bits, t);
      009570 1E 18            [ 2] 3517 	ldw	x, (0x18, sp)
      009572 13 0A            [ 2] 3518 	cpw	x, (0x0a, sp)
      009574 2E 21            [ 1] 3519 	jrsge	00134$
      009576 1E 1E            [ 2] 3520 	ldw	x, (0x1e, sp)
      009578 54               [ 2] 3521 	srlw	x
      009579 54               [ 2] 3522 	srlw	x
      00957A 54               [ 2] 3523 	srlw	x
      00957B 1C 00 E4         [ 2] 3524 	addw	x, #(_d_bits+0)
      00957E F6               [ 1] 3525 	ld	a, (x)
      00957F 6B 20            [ 1] 3526 	ld	(0x20, sp), a
      009581 7B 1F            [ 1] 3527 	ld	a, (0x1f, sp)
      009583 A4 07            [ 1] 3528 	and	a, #0x07
      009585 6B 21            [ 1] 3529 	ld	(0x21, sp), a
      009587 A6 01            [ 1] 3530 	ld	a, #0x01
      009589 88               [ 1] 3531 	push	a
      00958A 7B 22            [ 1] 3532 	ld	a, (0x22, sp)
      00958C 27 05            [ 1] 3533 	jreq	00595$
      00958E                       3534 00594$:
      00958E 08 01            [ 1] 3535 	sll	(1, sp)
      009590 4A               [ 1] 3536 	dec	a
      009591 26 FB            [ 1] 3537 	jrne	00594$
      009593                       3538 00595$:
      009593 84               [ 1] 3539 	pop	a
      009594 1A 20            [ 1] 3540 	or	a, (0x20, sp)
      009596 F7               [ 1] 3541 	ld	(x), a
      009597                       3542 00134$:
                                   3543 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
      009597 16 0E            [ 2] 3544 	ldw	y, (0x0e, sp)
      009599 17 20            [ 2] 3545 	ldw	(0x20, sp), y
      00959B                       3546 00180$:
      00959B 1E 20            [ 2] 3547 	ldw	x, (0x20, sp)
      00959D 13 10            [ 2] 3548 	cpw	x, (0x10, sp)
      00959F 2C 23            [ 1] 3549 	jrsgt	00142$
                                   3550 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
      0095A1 1E 20            [ 2] 3551 	ldw	x, (0x20, sp)
      0095A3 58               [ 2] 3552 	sllw	x
      0095A4 DE 01 02         [ 2] 3553 	ldw	x, (_d_costs+0, x)
      0095A7 89               [ 2] 3554 	pushw	x
      0095A8 1E 22            [ 2] 3555 	ldw	x, (0x22, sp)
      0095AA 13 1A            [ 2] 3556 	cpw	x, (0x1a, sp)
      0095AC 85               [ 2] 3557 	popw	x
      0095AD 2D 08            [ 1] 3558 	jrsle	00140$
      0095AF 13 1C            [ 2] 3559 	cpw	x, (0x1c, sp)
      0095B1 24 0A            [ 1] 3560 	jrnc	00181$
      0095B3 1F 1C            [ 2] 3561 	ldw	(0x1c, sp), x
      0095B5 20 06            [ 2] 3562 	jra	00181$
      0095B7                       3563 00140$:
                                   3564 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 831: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
      0095B7 13 1A            [ 2] 3565 	cpw	x, (0x1a, sp)
      0095B9 24 02            [ 1] 3566 	jrnc	00181$
      0095BB 1F 1A            [ 2] 3567 	ldw	(0x1a, sp), x
      0095BD                       3568 00181$:
                                   3569 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
      0095BD 1E 20            [ 2] 3570 	ldw	x, (0x20, sp)
      0095BF 5C               [ 1] 3571 	incw	x
      0095C0 1F 20            [ 2] 3572 	ldw	(0x20, sp), x
      0095C2 20 D7            [ 2] 3573 	jra	00180$
      0095C4                       3574 00142$:
                                   3575 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 833: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
      0095C4 1E 1A            [ 2] 3576 	ldw	x, (0x1a, sp)
      0095C6 5C               [ 1] 3577 	incw	x
      0095C7 27 05            [ 1] 3578 	jreq	00145$
      0095C9 1E 1C            [ 2] 3579 	ldw	x, (0x1c, sp)
      0095CB 5C               [ 1] 3580 	incw	x
      0095CC 26 07            [ 1] 3581 	jrne	00146$
      0095CE                       3582 00145$:
      0095CE AE 00 FF         [ 2] 3583 	ldw	x, #0x00ff
      0095D1 1F 20            [ 2] 3584 	ldw	(0x20, sp), x
      0095D3 20 1A            [ 2] 3585 	jra	00147$
      0095D5                       3586 00146$:
                                   3587 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 835: int16_t dm = (int16_t)(c0m - c1m);
      0095D5 1E 1A            [ 2] 3588 	ldw	x, (0x1a, sp)
      0095D7 72 F0 1C         [ 2] 3589 	subw	x, (0x1c, sp)
                                   3590 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 836: if (dm < 0) dm = (int16_t)-dm;
      0095DA 1F 20            [ 2] 3591 	ldw	(0x20, sp), x
      0095DC 5D               [ 2] 3592 	tnzw	x
      0095DD 2A 07            [ 1] 3593 	jrpl	00144$
      0095DF 00 21            [ 1] 3594 	neg	(0x21, sp)
      0095E1 4F               [ 1] 3595 	clr	a
      0095E2 12 20            [ 1] 3596 	sbc	a, (0x20, sp)
      0095E4 6B 20            [ 1] 3597 	ld	(0x20, sp), a
      0095E6                       3598 00144$:
                                   3599 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 837: m = (dm > 255) ? 255 : (uint16_t)dm;
      0095E6 AE 00 FF         [ 2] 3600 	ldw	x, #0x00ff
      0095E9 13 20            [ 2] 3601 	cpw	x, (0x20, sp)
      0095EB 2C 02            [ 1] 3602 	jrsgt	00189$
      0095ED 1F 20            [ 2] 3603 	ldw	(0x20, sp), x
      0095EF                       3604 00189$:
      0095EF                       3605 00147$:
                                   3606 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 839: if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
      0095EF 1E 1E            [ 2] 3607 	ldw	x, (0x1e, sp)
      0095F1 13 12            [ 2] 3608 	cpw	x, (0x12, sp)
      0095F3 27 05            [ 1] 3609 	jreq	00149$
      0095F5 C3 01 38         [ 2] 3610 	cpw	x, _v_tiepend+0
      0095F8 26 03            [ 1] 3611 	jrne	00150$
      0095FA                       3612 00149$:
                                   3613 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 840: m = 0;                       /* decided by tie-break */
      0095FA 5F               [ 1] 3614 	clrw	x
      0095FB 1F 20            [ 2] 3615 	ldw	(0x20, sp), x
      0095FD                       3616 00150$:
                                   3617 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 841: if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
      0095FD 1E 1E            [ 2] 3618 	ldw	x, (0x1e, sp)
      0095FF A3 00 20         [ 2] 3619 	cpw	x, #0x0020
      009602 25 2E            [ 1] 3620 	jrc	00184$
      009604 16 1E            [ 2] 3621 	ldw	y, (0x1e, sp)
      009606 90 A3 00 A0      [ 2] 3622 	cpw	y, #0x00a0
      00960A 24 26            [ 1] 3623 	jrnc	00184$
                                   3624 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 842: if (m <= MG_MAX) {
      00960C 16 20            [ 2] 3625 	ldw	y, (0x20, sp)
      00960E 90 A3 00 08      [ 2] 3626 	cpw	y, #0x0008
      009612 22 1E            [ 1] 3627 	jrugt	00184$
                                   3628 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 843: uint16_t k = t - PP_LO;
      009614 1D 00 20         [ 2] 3629 	subw	x, #0x0020
      009617 1F 1C            [ 2] 3630 	ldw	(0x1c, sp), x
                                   3631 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 844: v_nweak++;
      009619 CE 01 34         [ 2] 3632 	ldw	x, _v_nweak+0
      00961C 5C               [ 1] 3633 	incw	x
      00961D CF 01 34         [ 2] 3634 	ldw	_v_nweak+0, x
                                   3635 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 845: if (m == 0) v_ntied++;
      009620 1E 20            [ 2] 3636 	ldw	x, (0x20, sp)
      009622 26 07            [ 1] 3637 	jrne	00153$
      009624 CE 01 36         [ 2] 3638 	ldw	x, _v_ntied+0
      009627 5C               [ 1] 3639 	incw	x
      009628 CF 01 36         [ 2] 3640 	ldw	_v_ntied+0, x
      00962B                       3641 00153$:
                                   3642 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 846: cand_insert(k, (uint8_t)m);
      00962B 7B 21            [ 1] 3643 	ld	a, (0x21, sp)
      00962D 1E 1C            [ 2] 3644 	ldw	x, (0x1c, sp)
      00962F CD 93 69         [ 4] 3645 	call	_cand_insert
      009632                       3646 00184$:
                                   3647 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
      009632 1E 1E            [ 2] 3648 	ldw	x, (0x1e, sp)
      009634 5C               [ 1] 3649 	incw	x
      009635 1F 1E            [ 2] 3650 	ldw	(0x1e, sp), x
      009637 CC 95 56         [ 2] 3651 	jp	00183$
      00963A                       3652 00159$:
                                   3653 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 850: if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
      00963A CE 01 38         [ 2] 3654 	ldw	x, _v_tiepend+0
      00963D 16 16            [ 2] 3655 	ldw	y, (0x16, sp)
      00963F 17 20            [ 2] 3656 	ldw	(0x20, sp), y
      009641 5D               [ 2] 3657 	tnzw	x
      009642 2B 0C            [ 1] 3658 	jrmi	00161$
      009644 1E 20            [ 2] 3659 	ldw	x, (0x20, sp)
      009646 C3 01 38         [ 2] 3660 	cpw	x, _v_tiepend+0
      009649 2D 05            [ 1] 3661 	jrsle	00161$
                                   3662 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 851: v_tiepend = -1;                  /* consumed              */
      00964B 5F               [ 1] 3663 	clrw	x
      00964C 5A               [ 2] 3664 	decw	x
      00964D CF 01 38         [ 2] 3665 	ldw	_v_tiepend+0, x
      009650                       3666 00161$:
                                   3667 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 852: if (tie_here >= (int16_t)kk1)
      009650 1E 12            [ 2] 3668 	ldw	x, (0x12, sp)
      009652 13 20            [ 2] 3669 	cpw	x, (0x20, sp)
      009654 2E 03            [ 1] 3670 	jrsge	00622$
      009656 CC 94 25         [ 2] 3671 	jp	00165$
      009659                       3672 00622$:
                                   3673 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 853: v_tiepend = tie_here;            /* lands in next segment */
      009659 1E 12            [ 2] 3674 	ldw	x, (0x12, sp)
      00965B CF 01 38         [ 2] 3675 	ldw	_v_tiepend+0, x
      00965E CC 94 25         [ 2] 3676 	jp	00165$
      009661                       3677 00185$:
                                   3678 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 855: }
      009661 5B 21            [ 2] 3679 	addw	sp, #33
      009663 81               [ 4] 3680 	ret
                                   3681 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 989: static uint8_t chase(uint8_t *out)
                                   3682 ;	-----------------------------------------
                                   3683 ;	 function chase
                                   3684 ;	-----------------------------------------
      009664                       3685 _chase:
      009664 52 07            [ 2] 3686 	sub	sp, #7
      009666 1F 04            [ 2] 3687 	ldw	(0x04, sp), x
                                   3688 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
      009668 0F 06            [ 1] 3689 	clr	(0x06, sp)
      00966A                       3690 00108$:
                                   3691 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 994: uint8_t val = 0;
      00966A 4F               [ 1] 3692 	clr	a
                                   3693 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 995: uint16_t base = PP_LO + ((uint16_t)p << 3);
      00966B 41               [ 1] 3694 	exg	a, xl
      00966C 7B 06            [ 1] 3695 	ld	a, (0x06, sp)
      00966E 41               [ 1] 3696 	exg	a, xl
      00966F 58               [ 2] 3697 	sllw	x
      009670 58               [ 2] 3698 	sllw	x
      009671 58               [ 2] 3699 	sllw	x
      009672 1C 00 20         [ 2] 3700 	addw	x, #32
      009675 90 93            [ 1] 3701 	ldw	y, x
                                   3702 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
      009677 0F 07            [ 1] 3703 	clr	(0x07, sp)
      009679                       3704 00106$:
                                   3705 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 997: val = (uint8_t)((val << 1) | BGET(d_bits, base + j));
      009679 48               [ 1] 3706 	sll	a
      00967A 6B 01            [ 1] 3707 	ld	(0x01, sp), a
      00967C 7B 07            [ 1] 3708 	ld	a, (0x07, sp)
      00967E 6B 03            [ 1] 3709 	ld	(0x03, sp), a
      009680 0F 02            [ 1] 3710 	clr	(0x02, sp)
      009682 93               [ 1] 3711 	ldw	x, y
      009683 4F               [ 1] 3712 	clr	a
      009684 95               [ 1] 3713 	ld	xh, a
      009685 72 FB 02         [ 2] 3714 	addw	x, (0x02, sp)
      009688 54               [ 2] 3715 	srlw	x
      009689 54               [ 2] 3716 	srlw	x
      00968A 54               [ 2] 3717 	srlw	x
      00968B 1C 00 E4         [ 2] 3718 	addw	x, #(_d_bits+0)
      00968E F6               [ 1] 3719 	ld	a, (x)
      00968F 97               [ 1] 3720 	ld	xl, a
      009690 90 9F            [ 1] 3721 	ld	a, yl
      009692 1B 07            [ 1] 3722 	add	a, (0x07, sp)
      009694 A4 07            [ 1] 3723 	and	a, #0x07
      009696 27 06            [ 1] 3724 	jreq	00174$
      009698                       3725 00173$:
      009698 41               [ 1] 3726 	exg	a, xl
      009699 44               [ 1] 3727 	srl	a
      00969A 41               [ 1] 3728 	exg	a, xl
      00969B 4A               [ 1] 3729 	dec	a
      00969C 26 FA            [ 1] 3730 	jrne	00173$
      00969E                       3731 00174$:
      00969E 9F               [ 1] 3732 	ld	a, xl
      00969F A4 01            [ 1] 3733 	and	a, #0x01
      0096A1 1A 01            [ 1] 3734 	or	a, (0x01, sp)
                                   3735 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
      0096A3 0C 07            [ 1] 3736 	inc	(0x07, sp)
      0096A5 88               [ 1] 3737 	push	a
      0096A6 7B 08            [ 1] 3738 	ld	a, (0x08, sp)
      0096A8 A1 08            [ 1] 3739 	cp	a, #0x08
      0096AA 84               [ 1] 3740 	pop	a
      0096AB 25 CC            [ 1] 3741 	jrc	00106$
                                   3742 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 998: d_pp[p] = val;
      0096AD 5F               [ 1] 3743 	clrw	x
      0096AE 41               [ 1] 3744 	exg	a, xl
      0096AF 7B 06            [ 1] 3745 	ld	a, (0x06, sp)
      0096B1 41               [ 1] 3746 	exg	a, xl
      0096B2 1C 01 3A         [ 2] 3747 	addw	x, #(_d_pp+0)
      0096B5 F7               [ 1] 3748 	ld	(x), a
                                   3749 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
      0096B6 0C 06            [ 1] 3750 	inc	(0x06, sp)
      0096B8 7B 06            [ 1] 3751 	ld	a, (0x06, sp)
      0096BA A1 10            [ 1] 3752 	cp	a, #0x10
      0096BC 25 AC            [ 1] 3753 	jrc	00108$
                                   3754 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1000: dec_info.n_weak = v_nweak;
      0096BE 55 01 35 00 2A   [ 1] 3755 	mov	_dec_info+6, _v_nweak+1
      0096C3 55 01 34 00 29   [ 1] 3756 	mov	_dec_info+5, _v_nweak+0
                                   3757 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1001: dec_info.n_tied = v_ntied;
      0096C8 55 01 37 00 2C   [ 1] 3758 	mov	_dec_info+8, _v_ntied+1
      0096CD 55 01 36 00 2B   [ 1] 3759 	mov	_dec_info+7, _v_ntied+0
                                   3760 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1005: if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
      0096D2 CE 01 36         [ 2] 3761 	ldw	x, _v_ntied+0
      0096D5 A3 00 08         [ 2] 3762 	cpw	x, #0x0008
      0096D8 23 07            [ 2] 3763 	jrule	00126$
      0096DA 35 05 00 25      [ 1] 3764 	mov	_dec_info+1, #0x05
      0096DE 4F               [ 1] 3765 	clr	a
      0096DF 20 19            [ 2] 3766 	jra	00112$
                                   3767 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1006: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
      0096E1                       3768 00126$:
      0096E1 4F               [ 1] 3769 	clr	a
      0096E2                       3770 00110$:
      0096E2 90 5F            [ 1] 3771 	clrw	y
      0096E4 90 97            [ 1] 3772 	ld	yl, a
      0096E6 72 F9 04         [ 2] 3773 	addw	y, (0x04, sp)
      0096E9 5F               [ 1] 3774 	clrw	x
      0096EA 97               [ 1] 3775 	ld	xl, a
      0096EB 1C 01 3A         [ 2] 3776 	addw	x, #(_d_pp+0)
      0096EE 88               [ 1] 3777 	push	a
      0096EF F6               [ 1] 3778 	ld	a, (x)
      0096F0 90 F7            [ 1] 3779 	ld	(y), a
      0096F2 84               [ 1] 3780 	pop	a
      0096F3 4C               [ 1] 3781 	inc	a
      0096F4 A1 10            [ 1] 3782 	cp	a, #0x10
      0096F6 25 EA            [ 1] 3783 	jrc	00110$
                                   3784 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1007: return DEC_LEGACY;
      0096F8 A6 03            [ 1] 3785 	ld	a, #0x03
      0096FA                       3786 00112$:
                                   3787 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1045: }
      0096FA 5B 07            [ 2] 3788 	addw	sp, #7
      0096FC 81               [ 4] 3789 	ret
                                   3790 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1049: uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
                                   3791 ;	-----------------------------------------
                                   3792 ;	 function ws_decode_ex
                                   3793 ;	-----------------------------------------
      0096FD                       3794 _ws_decode_ex:
      0096FD 89               [ 2] 3795 	pushw	x
      0096FE 51               [ 1] 3796 	exgw	x, y
                                   3797 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
      0096FF 4F               [ 1] 3798 	clr	a
      009700                       3799 00115$:
                                   3800 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1055: ((uint8_t *)&dec_info)[t] = 0;
      009700 5F               [ 1] 3801 	clrw	x
      009701 97               [ 1] 3802 	ld	xl, a
      009702 72 4F 00 24      [ 1] 3803 	clr	((_dec_info+0), x)
                                   3804 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
      009706 4C               [ 1] 3805 	inc	a
      009707 A1 14            [ 1] 3806 	cp	a, #0x14
      009709 25 F5            [ 1] 3807 	jrc	00115$
                                   3808 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1056: scan_cap = cap;
      00970B 90 CF 00 01      [ 2] 3809 	ldw	_scan_cap+0, y
                                   3810 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1057: scan_len = ncap;
      00970F 1E 05            [ 2] 3811 	ldw	x, (0x05, sp)
      009711 CF 00 03         [ 2] 3812 	ldw	_scan_len+0, x
                                   3813 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1058: if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
      009714 CD 84 94         [ 4] 3814 	call	_seed
      009717 4D               [ 1] 3815 	tnz	a
      009718 26 08            [ 1] 3816 	jrne	00139$
      00971A 35 01 00 25      [ 1] 3817 	mov	_dec_info+1, #0x01
      00971E 4F               [ 1] 3818 	clr	a
      00971F CC 97 D5         [ 2] 3819 	jp	00122$
                                   3820 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1059: for (r = 0; r < 2; r++) refine();
      009722                       3821 00139$:
      009722 A6 02            [ 1] 3822 	ld	a, #0x02
      009724                       3823 00119$:
      009724 88               [ 1] 3824 	push	a
      009725 CD 85 35         [ 4] 3825 	call	_refine
      009728 84               [ 1] 3826 	pop	a
      009729 4A               [ 1] 3827 	dec	a
      00972A 26 F8            [ 1] 3828 	jrne	00119$
                                   3829 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1060: calibrate();
      00972C CD 8F 61         [ 4] 3830 	call	_calibrate
                                   3831 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1061: decide_pass();
      00972F CD 93 F7         [ 4] 3832 	call	_decide_pass
                                   3833 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1062: dec_info.K = g_K;
      009732 55 00 39 00 2E   [ 1] 3834 	mov	_dec_info+10, _g_K+1
      009737 55 00 38 00 2D   [ 1] 3835 	mov	_dec_info+9, _g_K+0
                                   3836 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1063: dec_info.tau = g_tau;
      00973C 55 00 3B 00 30   [ 1] 3837 	mov	_dec_info+12, _g_tau+1
      009741 55 00 3A 00 2F   [ 1] 3838 	mov	_dec_info+11, _g_tau+0
                                   3839 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1064: dec_info.infeasible = d_infeas;
      009746 55 00 FD 00 33   [ 1] 3840 	mov	_dec_info+15, _d_infeas+1
      00974B 55 00 FC 00 32   [ 1] 3841 	mov	_dec_info+14, _d_infeas+0
                                   3842 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1065: dec_info.label_err = d_laberr;
      009750 55 00 FF 00 35   [ 1] 3843 	mov	_dec_info+17, _d_laberr+1
      009755 55 00 FE 00 34   [ 1] 3844 	mov	_dec_info+16, _d_laberr+0
                                   3845 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1066: dec_info.n_seg = d_nseg;
      00975A 55 01 01 00 37   [ 1] 3846 	mov	_dec_info+19, _d_nseg+1
      00975F 55 01 00 00 36   [ 1] 3847 	mov	_dec_info+18, _d_nseg+0
                                   3848 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
      009764 0F 02            [ 1] 3849 	clr	(0x02, sp)
      009766 5F               [ 1] 3850 	clrw	x
      009767                       3851 00120$:
                                   3852 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: int8_t kb = known_bit(t);
      009767 89               [ 2] 3853 	pushw	x
      009768 CD 81 47         [ 4] 3854 	call	_known_bit
      00976B 6B 03            [ 1] 3855 	ld	(0x03, sp), a
      00976D 85               [ 2] 3856 	popw	x
                                   3857 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1069: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
      00976E 0D 01            [ 1] 3858 	tnz	(0x01, sp)
      009770 2B 23            [ 1] 3859 	jrmi	00121$
      009772 90 93            [ 1] 3860 	ldw	y, x
      009774 A6 08            [ 1] 3861 	ld	a, #0x08
      009776 90 62            [ 2] 3862 	div	y, a
      009778 72 A9 00 E4      [ 2] 3863 	addw	y, #(_d_bits+0)
      00977C 90 F6            [ 1] 3864 	ld	a, (y)
      00977E 90 97            [ 1] 3865 	ld	yl, a
      009780 9F               [ 1] 3866 	ld	a, xl
      009781 A4 07            [ 1] 3867 	and	a, #0x07
      009783 27 06            [ 1] 3868 	jreq	00228$
      009785                       3869 00227$:
      009785 61               [ 1] 3870 	exg	a, yl
      009786 44               [ 1] 3871 	srl	a
      009787 61               [ 1] 3872 	exg	a, yl
      009788 4A               [ 1] 3873 	dec	a
      009789 26 FA            [ 1] 3874 	jrne	00227$
      00978B                       3875 00228$:
      00978B 90 9F            [ 1] 3876 	ld	a, yl
      00978D A4 01            [ 1] 3877 	and	a, #0x01
      00978F 11 01            [ 1] 3878 	cp	a, (0x01, sp)
      009791 27 02            [ 1] 3879 	jreq	00121$
      009793 0C 02            [ 1] 3880 	inc	(0x02, sp)
      009795                       3881 00121$:
                                   3882 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
      009795 5C               [ 1] 3883 	incw	x
      009796 A3 00 C0         [ 2] 3884 	cpw	x, #0x00c0
      009799 25 CC            [ 1] 3885 	jrc	00120$
                                   3886 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1071: dec_info.violations = viol;
      00979B AE 00 31         [ 2] 3887 	ldw	x, #(_dec_info+13)
      00979E 7B 02            [ 1] 3888 	ld	a, (0x02, sp)
      0097A0 F7               [ 1] 3889 	ld	(x), a
                                   3890 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1072: if (viol > 0)               { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
      0097A1 0D 02            [ 1] 3891 	tnz	(0x02, sp)
      0097A3 27 07            [ 1] 3892 	jreq	00110$
      0097A5 35 02 00 25      [ 1] 3893 	mov	_dec_info+1, #0x02
      0097A9 4F               [ 1] 3894 	clr	a
      0097AA 20 29            [ 2] 3895 	jra	00122$
      0097AC                       3896 00110$:
                                   3897 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1073: if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
      0097AC CE 00 FC         [ 2] 3898 	ldw	x, _d_infeas+0
      0097AF A3 00 04         [ 2] 3899 	cpw	x, #0x0004
      0097B2 23 07            [ 2] 3900 	jrule	00112$
      0097B4 35 03 00 25      [ 1] 3901 	mov	_dec_info+1, #0x03
      0097B8 4F               [ 1] 3902 	clr	a
      0097B9 20 1A            [ 2] 3903 	jra	00122$
      0097BB                       3904 00112$:
                                   3905 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1074: if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
      0097BB CE 00 FE         [ 2] 3906 	ldw	x, _d_laberr+0
      0097BE A3 00 06         [ 2] 3907 	cpw	x, #0x0006
      0097C1 23 07            [ 2] 3908 	jrule	00114$
      0097C3 35 04 00 25      [ 1] 3909 	mov	_dec_info+1, #0x04
      0097C7 4F               [ 1] 3910 	clr	a
      0097C8 20 0B            [ 2] 3911 	jra	00122$
      0097CA                       3912 00114$:
                                   3913 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1075: dec_info.path = chase(out);                                      /* R5..R8 inside */
      0097CA AE 00 24         [ 2] 3914 	ldw	x, #(_dec_info+0)
      0097CD 89               [ 2] 3915 	pushw	x
      0097CE 1E 09            [ 2] 3916 	ldw	x, (0x09, sp)
      0097D0 CD 96 64         [ 4] 3917 	call	_chase
      0097D3 85               [ 2] 3918 	popw	x
      0097D4 F7               [ 1] 3919 	ld	(x), a
                                   3920 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1076: return dec_info.path;
      0097D5                       3921 00122$:
                                   3922 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1077: }
      0097D5 1E 03            [ 2] 3923 	ldw	x, (3, sp)
      0097D7 5B 08            [ 2] 3924 	addw	sp, #8
      0097D9 FC               [ 2] 3925 	jp	(x)
                                   3926 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1079: int16_t dec_eps_centi(void)
                                   3927 ;	-----------------------------------------
                                   3928 ;	 function dec_eps_centi
                                   3929 ;	-----------------------------------------
      0097DA                       3930 _dec_eps_centi:
      0097DA 52 04            [ 2] 3931 	sub	sp, #4
                                   3932 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1084: return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
      0097DC CE 00 2D         [ 2] 3933 	ldw	x, _dec_info+9
      0097DF 1F 03            [ 2] 3934 	ldw	(0x03, sp), x
      0097E1 5F               [ 1] 3935 	clrw	x
      0097E2 1F 01            [ 2] 3936 	ldw	(0x01, sp), x
      0097E4 90 AE CC CD      [ 2] 3937 	ldw	y, #0xcccd
      0097E8 72 F2 03         [ 2] 3938 	subw	y, (0x03, sp)
      0097EB 1E 01            [ 2] 3939 	ldw	x, (0x01, sp)
      0097ED 24 01            [ 1] 3940 	jrnc	00103$
      0097EF 5C               [ 1] 3941 	incw	x
      0097F0                       3942 00103$:
      0097F0 50               [ 2] 3943 	negw	x
      0097F1 90 89            [ 2] 3944 	pushw	y
      0097F3 89               [ 2] 3945 	pushw	x
      0097F4 4B 10            [ 1] 3946 	push	#0x10
      0097F6 4B 27            [ 1] 3947 	push	#0x27
      0097F8 5F               [ 1] 3948 	clrw	x
      0097F9 89               [ 2] 3949 	pushw	x
                                   3950 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1085: / (int32_t)dec_info.K);
      0097FA CD 99 05         [ 4] 3951 	call	__mullong
      0097FD 5B 08            [ 2] 3952 	addw	sp, #8
      0097FF 7B 04            [ 1] 3953 	ld	a, (0x04, sp)
      009801 88               [ 1] 3954 	push	a
      009802 7B 04            [ 1] 3955 	ld	a, (0x04, sp)
      009804 88               [ 1] 3956 	push	a
      009805 4F               [ 1] 3957 	clr	a
      009806 88               [ 1] 3958 	push	a
      009807 4F               [ 1] 3959 	clr	a
      009808 88               [ 1] 3960 	push	a
      009809 89               [ 2] 3961 	pushw	x
      00980A 90 89            [ 2] 3962 	pushw	y
      00980C CD 98 81         [ 4] 3963 	call	__divslong
                                   3964 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1086: }
      00980F 5B 0C            [ 2] 3965 	addw	sp, #12
      009811 81               [ 4] 3966 	ret
                                   3967 	.area CODE
                                   3968 	.area CONST
                                   3969 	.area CONST
      00802D                       3970 _HDR:
      00802D FF                    3971 	.db #0xff	; 255
      00802E 00                    3972 	.db #0x00	; 0
      00802F AA                    3973 	.db #0xaa	; 170
      008030 65                    3974 	.db #0x65	; 101	'e'
                                   3975 	.area CODE
                                   3976 	.area CONST
      008031                       3977 _TRL:
      008031 9A                    3978 	.db #0x9a	; 154
      008032 55                    3979 	.db #0x55	; 85	'U'
      008033 00                    3980 	.db #0x00	; 0
      008034 FF                    3981 	.db #0xff	; 255
                                   3982 	.area CODE
                                   3983 	.area CONST
      008035                       3984 _O_CY:
      008035 00                    3985 	.db #0x00	; 0
      008036 04                    3986 	.db #0x04	; 4
      008037 09                    3987 	.db #0x09	; 9
      008038 0D                    3988 	.db #0x0d	; 13
      008039 11                    3989 	.db #0x11	; 17
      00803A 15                    3990 	.db #0x15	; 21
      00803B 1B                    3991 	.db #0x1b	; 27
      00803C 20                    3992 	.db #0x20	; 32
                                   3993 	.area CODE
                                   3994 	.area CONST
      00803D                       3995 _W_CY:
      00803D 00                    3996 	.db #0x00	;  0
      00803E FF                    3997 	.db #0xff	; -1
      00803F 00                    3998 	.db #0x00	;  0
      008040 02                    3999 	.db #0x02	;  2
      008041 00                    4000 	.db #0x00	;  0
      008042 00                    4001 	.db #0x00	;  0
      008043 00                    4002 	.db #0x00	;  0
      008044 01                    4003 	.db #0x01	;  1
                                   4004 	.area CODE
                                   4005 	.area INITIALIZER
                                   4006 	.area CABS (ABS)
