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
      0000E4                         75 	.ds 27
      0000FF                         76 _d_infeas:
      0000FF                         77 	.ds 2
      000101                         78 _d_laberr:
      000101                         79 	.ds 2
      000103                         80 _d_nseg:
      000103                         81 	.ds 2
      000105                         82 _d_costs:
      000105                         83 	.ds 32
      000125                         84 _d_inter:
      000125                         85 	.ds 2
      000127                         86 _v_cand_t:
      000127                         87 	.ds 10
      000131                         88 _v_cand_m:
      000131                         89 	.ds 5
      000136                         90 _v_ncand:
      000136                         91 	.ds 1
      000137                         92 _v_nweak:
      000137                         93 	.ds 2
      000139                         94 _v_ntied:
      000139                         95 	.ds 2
      00013B                         96 _v_tiepend:
      00013B                         97 	.ds 2
      00013D                         98 _d_pp:
      00013D                         99 	.ds 19
      000150                        100 _ss:
      000150                        101 	.ds 20
      000164                        102 _ch_rbase:
      000164                        103 	.ds 1
      000165                        104 _ch_n:
      000165                        105 	.ds 1
      000166                        106 _ch_isd:
      000166                        107 	.ds 5
                                    108 ;--------------------------------------------------------
                                    109 ; ram data
                                    110 ;--------------------------------------------------------
                                    111 	.area INITIALIZED
                                    112 ;--------------------------------------------------------
                                    113 ; absolute external ram data
                                    114 ;--------------------------------------------------------
                                    115 	.area DABS (ABS)
                                    116 
                                    117 ; default segment ordering for linker
                                    118 	.area HOME
                                    119 	.area GSINIT
                                    120 	.area GSFINAL
                                    121 	.area CONST
                                    122 	.area INITIALIZER
                                    123 	.area CODE
                                    124 
                                    125 ;--------------------------------------------------------
                                    126 ; global & static initialisations
                                    127 ;--------------------------------------------------------
                                    128 	.area HOME
                                    129 	.area GSINIT
                                    130 	.area GSFINAL
                                    131 	.area GSINIT
                                    132 ;--------------------------------------------------------
                                    133 ; Home
                                    134 ;--------------------------------------------------------
                                    135 	.area HOME
                                    136 	.area HOME
                                    137 ;--------------------------------------------------------
                                    138 ; code
                                    139 ;--------------------------------------------------------
                                    140 	.area CODE
                                    141 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 127: static int8_t known_bit(uint16_t t)
                                    142 ;	-----------------------------------------
                                    143 ;	 function known_bit
                                    144 ;	-----------------------------------------
      0081C6                        145 _known_bit:
      0081C6 88               [ 1]  146 	push	a
                                    147 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 129: if (t < 32)
      0081C7 90 93            [ 1]  148 	ldw	y, x
      0081C9 A3 00 20         [ 2]  149 	cpw	x, #0x0020
      0081CC 24 20            [ 1]  150 	jrnc	00102$
                                    151 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 130: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
      0081CE 93               [ 1]  152 	ldw	x, y
      0081CF 54               [ 2]  153 	srlw	x
      0081D0 54               [ 2]  154 	srlw	x
      0081D1 54               [ 2]  155 	srlw	x
      0081D2 1C 80 2D         [ 2]  156 	addw	x, #(_HDR+0)
      0081D5 F6               [ 1]  157 	ld	a, (x)
      0081D6 97               [ 1]  158 	ld	xl, a
      0081D7 90 9F            [ 1]  159 	ld	a, yl
      0081D9 A4 07            [ 1]  160 	and	a, #0x07
      0081DB 6B 01            [ 1]  161 	ld	(0x01, sp), a
      0081DD A6 07            [ 1]  162 	ld	a, #0x07
      0081DF 10 01            [ 1]  163 	sub	a, (0x01, sp)
      0081E1 27 06            [ 1]  164 	jreq	00125$
      0081E3                        165 00124$:
      0081E3 41               [ 1]  166 	exg	a, xl
      0081E4 44               [ 1]  167 	srl	a
      0081E5 41               [ 1]  168 	exg	a, xl
      0081E6 4A               [ 1]  169 	dec	a
      0081E7 26 FA            [ 1]  170 	jrne	00124$
      0081E9                        171 00125$:
      0081E9 9F               [ 1]  172 	ld	a, xl
      0081EA A4 01            [ 1]  173 	and	a, #0x01
      0081EC 20 2B            [ 2]  174 	jra	00105$
      0081EE                        175 00102$:
                                    176 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 131: if (t >= NB - 32) {
      0081EE 90 A3 00 B8      [ 2]  177 	cpw	y, #0x00b8
      0081F2 25 23            [ 1]  178 	jrc	00104$
                                    179 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 132: uint16_t u = t - (NB - 32);
      0081F4 1D 00 B8         [ 2]  180 	subw	x, #0x00b8
                                    181 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 133: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
      0081F7 90 93            [ 1]  182 	ldw	y, x
      0081F9 54               [ 2]  183 	srlw	x
      0081FA 54               [ 2]  184 	srlw	x
      0081FB 54               [ 2]  185 	srlw	x
      0081FC 1C 80 31         [ 2]  186 	addw	x, #(_TRL+0)
      0081FF F6               [ 1]  187 	ld	a, (x)
      008200 97               [ 1]  188 	ld	xl, a
      008201 90 9F            [ 1]  189 	ld	a, yl
      008203 A4 07            [ 1]  190 	and	a, #0x07
      008205 6B 01            [ 1]  191 	ld	(0x01, sp), a
      008207 A6 07            [ 1]  192 	ld	a, #0x07
      008209 10 01            [ 1]  193 	sub	a, (0x01, sp)
      00820B 27 06            [ 1]  194 	jreq	00128$
      00820D                        195 00127$:
      00820D 41               [ 1]  196 	exg	a, xl
      00820E 44               [ 1]  197 	srl	a
      00820F 41               [ 1]  198 	exg	a, xl
      008210 4A               [ 1]  199 	dec	a
      008211 26 FA            [ 1]  200 	jrne	00127$
      008213                        201 00128$:
      008213 9F               [ 1]  202 	ld	a, xl
      008214 A4 01            [ 1]  203 	and	a, #0x01
                                    204 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 135: return -1;
      008216 C5                     205 	.byte 0xc5
      008217                        206 00104$:
      008217 A6 FF            [ 1]  207 	ld	a, #0xff
      008219                        208 00105$:
                                    209 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 136: }
      008219 5B 01            [ 2]  210 	addw	sp, #1
      00821B 81               [ 4]  211 	ret
                                    212 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 174: void scan_init(void)
                                    213 ;	-----------------------------------------
                                    214 ;	 function scan_init
                                    215 ;	-----------------------------------------
      00821C                        216 _scan_init:
                                    217 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 176: ps.i = 0; ps.s = 0; ps.tbase = 0; ps.wsum = 0;
      00821C AE 00 0E         [ 2]  218 	ldw	x, #(_ps+0)
      00821F 6F 01            [ 1]  219 	clr	(0x1, x)
      008221 7F               [ 1]  220 	clr	(x)
      008222 35 00 00 10      [ 1]  221 	mov	_ps+2, #0x00
      008226 AE 00 11         [ 2]  222 	ldw	x, #(_ps+3)
      008229 6F 01            [ 1]  223 	clr	(0x1, x)
      00822B 7F               [ 1]  224 	clr	(x)
      00822C AE 00 13         [ 2]  225 	ldw	x, #(_ps+5)
      00822F 6F 01            [ 1]  226 	clr	(0x1, x)
      008231 7F               [ 1]  227 	clr	(x)
                                    228 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 177: ps.t_prev = 0; ps.have_prev = 0;
      008232 AE 00 15         [ 2]  229 	ldw	x, #(_ps+7)
      008235 6F 01            [ 1]  230 	clr	(0x1, x)
      008237 7F               [ 1]  231 	clr	(x)
      008238 35 00 00 17      [ 1]  232 	mov	_ps+9, #0x00
                                    233 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 178: ps.in_pulse = 0; ps.seen = 0; ps.done = 0; ps.low_run = 0;
      00823C 35 00 00 18      [ 1]  234 	mov	_ps+10, #0x00
      008240 35 00 00 19      [ 1]  235 	mov	_ps+11, #0x00
      008244 35 00 00 1A      [ 1]  236 	mov	_ps+12, #0x00
      008248 AE 00 1B         [ 2]  237 	ldw	x, #(_ps+13)
      00824B 6F 01            [ 1]  238 	clr	(0x1, x)
      00824D 7F               [ 1]  239 	clr	(x)
                                    240 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 179: ps.ra = ps.rb = ps.fa = 0; ps.sfa = 0;
      00824E AE 00 21         [ 2]  241 	ldw	x, #(_ps+19)
      008251 6F 01            [ 1]  242 	clr	(0x1, x)
      008253 7F               [ 1]  243 	clr	(x)
      008254 AE 00 1F         [ 2]  244 	ldw	x, #(_ps+17)
      008257 6F 01            [ 1]  245 	clr	(0x1, x)
      008259 7F               [ 1]  246 	clr	(x)
      00825A AE 00 1D         [ 2]  247 	ldw	x, #(_ps+15)
      00825D 6F 01            [ 1]  248 	clr	(0x1, x)
      00825F 7F               [ 1]  249 	clr	(x)
      008260 35 00 00 23      [ 1]  250 	mov	_ps+21, #0x00
                                    251 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 180: }
      008264 81               [ 4]  252 	ret
                                    253 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 183: uint8_t scan_next(void)
                                    254 ;	-----------------------------------------
                                    255 ;	 function scan_next
                                    256 ;	-----------------------------------------
      008265                        257 _scan_next:
      008265 52 08            [ 2]  258 	sub	sp, #8
                                    259 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
      008267                        260 00133$:
                                    261 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
                                    262 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
                                    263 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
                                    264 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
                                    265 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
      008267 C6 00 1A         [ 1]  266 	ld	a, _ps+12
      00826A 27 03            [ 1]  267 	jreq	00320$
      00826C CC 84 AD         [ 2]  268 	jp	00135$
      00826F                        269 00320$:
                                    270 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 186: uint8_t v, s = ps.s;
      00826F C6 00 10         [ 1]  271 	ld	a, _ps+2
      008272 6B 01            [ 1]  272 	ld	(0x01, sp), a
                                    273 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 188: if (ps.i >= scan_len) break;
      008274 AE 00 0E         [ 2]  274 	ldw	x, #(_ps+0)
      008277 1F 02            [ 2]  275 	ldw	(0x02, sp), x
      008279 FE               [ 2]  276 	ldw	x, (x)
      00827A 1F 04            [ 2]  277 	ldw	(0x04, sp), x
      00827C C3 00 03         [ 2]  278 	cpw	x, _scan_len+0
      00827F 25 03            [ 1]  279 	jrc	00321$
      008281 CC 84 AD         [ 2]  280 	jp	00135$
      008284                        281 00321$:
                                    282 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
                                    283 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
                                    284 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
      008284 1E 04            [ 2]  285 	ldw	x, (0x04, sp)
      008286 5C               [ 1]  286 	incw	x
      008287 90 93            [ 1]  287 	ldw	y, x
                                    288 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
      008289 72 BB 00 01      [ 2]  289 	addw	x, _scan_cap+0
      00828D 1F 06            [ 2]  290 	ldw	(0x06, sp), x
                                    291 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
      00828F 90 C3 00 03      [ 2]  292 	cpw	y, _scan_len+0
      008293 4F               [ 1]  293 	clr	a
      008294 49               [ 1]  294 	rlc	a
      008295 6B 08            [ 1]  295 	ld	(0x08, sp), a
      008297 7B 01            [ 1]  296 	ld	a, (0x01, sp)
      008299 A1 06            [ 1]  297 	cp	a, #0x06
      00829B 27 03            [ 1]  298 	jreq	00324$
      00829D CC 83 4C         [ 2]  299 	jp	00113$
      0082A0                        300 00324$:
      0082A0 0D 08            [ 1]  301 	tnz	(0x08, sp)
      0082A2 26 03            [ 1]  302 	jrne	00325$
      0082A4 CC 83 4C         [ 2]  303 	jp	00113$
      0082A7                        304 00325$:
                                    305 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
      0082A7 1E 06            [ 2]  306 	ldw	x, (0x06, sp)
      0082A9 F6               [ 1]  307 	ld	a, (x)
      0082AA 97               [ 1]  308 	ld	xl, a
                                    309 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 191: if (bt == 0x00 && !ps.in_pulse) {
      0082AB 4D               [ 1]  310 	tnz	a
      0082AC 26 4F            [ 1]  311 	jrne	00107$
      0082AE C6 00 18         [ 1]  312 	ld	a, _ps+10
      0082B1 26 4A            [ 1]  313 	jrne	00107$
                                    314 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
      0082B3 CE 00 11         [ 2]  315 	ldw	x, _ps+3
      0082B6 1C 00 3D         [ 2]  316 	addw	x, #0x003d
      0082B9 90 CE 00 13      [ 2]  317 	ldw	y, _ps+5
      0082BD 17 07            [ 2]  318 	ldw	(0x07, sp), y
      0082BF 72 FB 07         [ 2]  319 	addw	x, (0x07, sp)
      0082C2 CF 00 15         [ 2]  320 	ldw	_ps+7, x
                                    321 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 194: ps.have_prev = 1;
      0082C5 35 01 00 17      [ 1]  322 	mov	_ps+9, #0x01
                                    323 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
      0082C9 CE 00 1B         [ 2]  324 	ldw	x, _ps+13
      0082CC 1C 00 08         [ 2]  325 	addw	x, #0x0008
      0082CF CF 00 1B         [ 2]  326 	ldw	_ps+13, x
                                    327 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 196: ps.i++; ps.tbase += LOOP_CY;        /* s stays 6 */
      0082D2 1E 02            [ 2]  328 	ldw	x, (0x02, sp)
      0082D4 FE               [ 2]  329 	ldw	x, (x)
      0082D5 5C               [ 1]  330 	incw	x
      0082D6 16 02            [ 2]  331 	ldw	y, (0x02, sp)
      0082D8 90 FF            [ 2]  332 	ldw	(y), x
      0082DA CE 00 11         [ 2]  333 	ldw	x, _ps+3
      0082DD 1C 00 28         [ 2]  334 	addw	x, #0x0028
      0082E0 CF 00 11         [ 2]  335 	ldw	_ps+3, x
                                    336 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 197: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
      0082E3 C6 00 19         [ 1]  337 	ld	a, _ps+11
      0082E6 26 03            [ 1]  338 	jrne	00328$
      0082E8 CC 82 67         [ 2]  339 	jp	00133$
      0082EB                        340 00328$:
      0082EB CE 00 1B         [ 2]  341 	ldw	x, _ps+13
      0082EE A3 00 C8         [ 2]  342 	cpw	x, #0x00c8
      0082F1 24 03            [ 1]  343 	jrnc	00329$
      0082F3 CC 82 67         [ 2]  344 	jp	00133$
      0082F6                        345 00329$:
      0082F6 35 01 00 1A      [ 1]  346 	mov	_ps+12, #0x01
      0082FA CC 84 AD         [ 2]  347 	jp	00135$
                                    348 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 198: continue;
      0082FD                        349 00107$:
                                    350 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 200: if (bt == 0xFF && ps.in_pulse) {
      0082FD 9F               [ 1]  351 	ld	a, xl
      0082FE 4C               [ 1]  352 	inc	a
      0082FF 26 4B            [ 1]  353 	jrne	00113$
      008301 C6 00 18         [ 1]  354 	ld	a, _ps+10
      008304 27 46            [ 1]  355 	jreq	00113$
                                    356 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
      008306 90 CE 00 11      [ 2]  357 	ldw	y, _ps+3
      00830A CE 00 13         [ 2]  358 	ldw	x, _ps+5
      00830D 1C 00 3F         [ 2]  359 	addw	x, #0x003f
      008310 17 07            [ 2]  360 	ldw	(0x07, sp), y
      008312 72 FB 07         [ 2]  361 	addw	x, (0x07, sp)
      008315 CF 00 21         [ 2]  362 	ldw	_ps+19, x
                                    363 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 203: ps.wsum += 2;               /* sum of W over the octet */
      008318 CE 00 13         [ 2]  364 	ldw	x, _ps+5
      00831B 5C               [ 1]  365 	incw	x
      00831C 5C               [ 1]  366 	incw	x
      00831D CF 00 13         [ 2]  367 	ldw	_ps+5, x
                                    368 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
      008320 35 05 00 23      [ 1]  369 	mov	_ps+21, #0x05
                                    370 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 205: ps.low_run = 0;
      008324 AE 00 1B         [ 2]  371 	ldw	x, #(_ps+13)
      008327 6F 01            [ 1]  372 	clr	(0x1, x)
      008329 7F               [ 1]  373 	clr	(x)
                                    374 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 206: ps.seen = 1;
      00832A 35 01 00 19      [ 1]  375 	mov	_ps+11, #0x01
                                    376 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 207: ps.t_prev = ps.fa;
      00832E CE 00 21         [ 2]  377 	ldw	x, _ps+19
      008331 CF 00 15         [ 2]  378 	ldw	_ps+7, x
                                    379 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 208: ps.have_prev = 1;
      008334 35 01 00 17      [ 1]  380 	mov	_ps+9, #0x01
                                    381 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 209: ps.i++; ps.tbase += LOOP_CY;
      008338 1E 02            [ 2]  382 	ldw	x, (0x02, sp)
      00833A FE               [ 2]  383 	ldw	x, (x)
      00833B 5C               [ 1]  384 	incw	x
      00833C 16 02            [ 2]  385 	ldw	y, (0x02, sp)
      00833E 90 FF            [ 2]  386 	ldw	(y), x
      008340 CE 00 11         [ 2]  387 	ldw	x, _ps+3
      008343 1C 00 28         [ 2]  388 	addw	x, #0x0028
      008346 CF 00 11         [ 2]  389 	ldw	_ps+3, x
                                    390 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 210: continue;
      008349 CC 82 67         [ 2]  391 	jp	00133$
      00834C                        392 00113$:
                                    393 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 213: if (s < 6) {
      00834C 7B 01            [ 1]  394 	ld	a, (0x01, sp)
      00834E A1 06            [ 1]  395 	cp	a, #0x06
      008350 24 1B            [ 1]  396 	jrnc	00118$
                                    397 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 214: v = (uint8_t)((scan_cap[ps.i] >> (5 - s)) & 1);
      008352 CE 00 01         [ 2]  398 	ldw	x, _scan_cap+0
      008355 72 FB 04         [ 2]  399 	addw	x, (0x04, sp)
      008358 F6               [ 1]  400 	ld	a, (x)
      008359 97               [ 1]  401 	ld	xl, a
      00835A A6 05            [ 1]  402 	ld	a, #0x05
      00835C 10 01            [ 1]  403 	sub	a, (0x01, sp)
      00835E 27 06            [ 1]  404 	jreq	00336$
      008360                        405 00335$:
      008360 41               [ 1]  406 	exg	a, xl
      008361 44               [ 1]  407 	srl	a
      008362 41               [ 1]  408 	exg	a, xl
      008363 4A               [ 1]  409 	dec	a
      008364 26 FA            [ 1]  410 	jrne	00335$
      008366                        411 00336$:
      008366 9F               [ 1]  412 	ld	a, xl
      008367 A4 01            [ 1]  413 	and	a, #0x01
      008369 6B 04            [ 1]  414 	ld	(0x04, sp), a
      00836B 20 36            [ 2]  415 	jra	00119$
      00836D                        416 00118$:
                                    417 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 216: if (ps.i + 1 >= scan_len) {     /* last loop: BS lost */
      00836D 7B 08            [ 1]  418 	ld	a, (0x08, sp)
      00836F 26 17            [ 1]  419 	jrne	00116$
                                    420 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 217: ps.i++; ps.s = 0; ps.tbase += LOOP_CY;
      008371 1E 04            [ 2]  421 	ldw	x, (0x04, sp)
      008373 5C               [ 1]  422 	incw	x
      008374 16 02            [ 2]  423 	ldw	y, (0x02, sp)
      008376 90 FF            [ 2]  424 	ldw	(y), x
      008378 35 00 00 10      [ 1]  425 	mov	_ps+2, #0x00
      00837C CE 00 11         [ 2]  426 	ldw	x, _ps+3
      00837F 1C 00 28         [ 2]  427 	addw	x, #0x0028
      008382 CF 00 11         [ 2]  428 	ldw	_ps+3, x
                                    429 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 218: continue;
      008385 CC 82 67         [ 2]  430 	jp	00133$
      008388                        431 00116$:
                                    432 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 220: v = (uint8_t)((scan_cap[ps.i + 1] >> (7 - (s - 6))) & 1);
      008388 1E 06            [ 2]  433 	ldw	x, (0x06, sp)
      00838A F6               [ 1]  434 	ld	a, (x)
      00838B 97               [ 1]  435 	ld	xl, a
      00838C 7B 01            [ 1]  436 	ld	a, (0x01, sp)
      00838E A0 06            [ 1]  437 	sub	a, #0x06
      008390 6B 08            [ 1]  438 	ld	(0x08, sp), a
      008392 A6 07            [ 1]  439 	ld	a, #0x07
      008394 10 08            [ 1]  440 	sub	a, (0x08, sp)
      008396 27 06            [ 1]  441 	jreq	00339$
      008398                        442 00338$:
      008398 41               [ 1]  443 	exg	a, xl
      008399 44               [ 1]  444 	srl	a
      00839A 41               [ 1]  445 	exg	a, xl
      00839B 4A               [ 1]  446 	dec	a
      00839C 26 FA            [ 1]  447 	jrne	00338$
      00839E                        448 00339$:
      00839E 9F               [ 1]  449 	ld	a, xl
      00839F A4 01            [ 1]  450 	and	a, #0x01
      0083A1 6B 04            [ 1]  451 	ld	(0x04, sp), a
      0083A3                        452 00119$:
                                    453 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 222: t = (uint16_t)(ps.tbase + O_CY[s] + ps.wsum);
      0083A3 90 CE 00 11      [ 2]  454 	ldw	y, _ps+3
      0083A7 5F               [ 1]  455 	clrw	x
      0083A8 7B 01            [ 1]  456 	ld	a, (0x01, sp)
      0083AA 97               [ 1]  457 	ld	xl, a
      0083AB D6 80 B4         [ 1]  458 	ld	a, (_O_CY+0, x)
      0083AE 6B 08            [ 1]  459 	ld	(0x08, sp), a
      0083B0 0F 07            [ 1]  460 	clr	(0x07, sp)
      0083B2 72 F9 07         [ 2]  461 	addw	y, (0x07, sp)
      0083B5 CE 00 13         [ 2]  462 	ldw	x, _ps+5
      0083B8 17 05            [ 2]  463 	ldw	(0x05, sp), y
      0083BA 72 FB 05         [ 2]  464 	addw	x, (0x05, sp)
      0083BD 1F 07            [ 2]  465 	ldw	(0x07, sp), x
                                    466 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 223: if (s == 7) { ps.s = 0; ps.i++; ps.tbase += LOOP_CY; }
      0083BF 7B 01            [ 1]  467 	ld	a, (0x01, sp)
      0083C1 A1 07            [ 1]  468 	cp	a, #0x07
      0083C3 26 17            [ 1]  469 	jrne	00121$
      0083C5 35 00 00 10      [ 1]  470 	mov	_ps+2, #0x00
      0083C9 1E 02            [ 2]  471 	ldw	x, (0x02, sp)
      0083CB FE               [ 2]  472 	ldw	x, (x)
      0083CC 5C               [ 1]  473 	incw	x
      0083CD 16 02            [ 2]  474 	ldw	y, (0x02, sp)
      0083CF 90 FF            [ 2]  475 	ldw	(y), x
      0083D1 CE 00 11         [ 2]  476 	ldw	x, _ps+3
      0083D4 1C 00 28         [ 2]  477 	addw	x, #0x0028
      0083D7 CF 00 11         [ 2]  478 	ldw	_ps+3, x
      0083DA 20 06            [ 2]  479 	jra	00122$
      0083DC                        480 00121$:
                                    481 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 224: else        { ps.s = (uint8_t)(s + 1); }
      0083DC 7B 01            [ 1]  482 	ld	a, (0x01, sp)
      0083DE 4C               [ 1]  483 	inc	a
      0083DF C7 00 10         [ 1]  484 	ld	_ps+2, a
      0083E2                        485 00122$:
                                    486 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 225: if (v) {
      0083E2 0D 04            [ 1]  487 	tnz	(0x04, sp)
      0083E4 27 65            [ 1]  488 	jreq	00131$
                                    489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 226: ps.wsum += W_CY[s];
      0083E6 90 CE 00 13      [ 2]  490 	ldw	y, _ps+5
      0083EA 5F               [ 1]  491 	clrw	x
      0083EB 7B 01            [ 1]  492 	ld	a, (0x01, sp)
      0083ED 97               [ 1]  493 	ld	xl, a
      0083EE 1C 80 BC         [ 2]  494 	addw	x, #(_W_CY+0)
      0083F1 F6               [ 1]  495 	ld	a, (x)
      0083F2 97               [ 1]  496 	ld	xl, a
      0083F3 49               [ 1]  497 	rlc	a
      0083F4 4F               [ 1]  498 	clr	a
      0083F5 A2 00            [ 1]  499 	sbc	a, #0x00
      0083F7 95               [ 1]  500 	ld	xh, a
      0083F8 17 05            [ 2]  501 	ldw	(0x05, sp), y
      0083FA 72 FB 05         [ 2]  502 	addw	x, (0x05, sp)
      0083FD CF 00 13         [ 2]  503 	ldw	_ps+5, x
                                    504 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 227: if (!ps.in_pulse) {
      008400 C6 00 18         [ 1]  505 	ld	a, _ps+10
      008403 26 2E            [ 1]  506 	jrne	00124$
                                    507 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 228: ps.in_pulse = 1;
      008405 35 01 00 18      [ 1]  508 	mov	_ps+10, #0x01
                                    509 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
      008409 C6 00 17         [ 1]  510 	ld	a, _ps+9
      00840C 27 05            [ 1]  511 	jreq	00140$
      00840E CE 00 15         [ 2]  512 	ldw	x, _ps+7
      008411 20 17            [ 2]  513 	jra	00141$
      008413                        514 00140$:
                                    515 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 230: : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
      008413 16 07            [ 2]  516 	ldw	y, (0x07, sp)
      008415 17 03            [ 2]  517 	ldw	(0x03, sp), y
      008417 93               [ 1]  518 	ldw	x, y
      008418 A3 00 04         [ 2]  519 	cpw	x, #0x0004
      00841B 25 08            [ 1]  520 	jrc	00142$
      00841D 1E 03            [ 2]  521 	ldw	x, (0x03, sp)
      00841F 1D 00 04         [ 2]  522 	subw	x, #0x0004
      008422 1F 05            [ 2]  523 	ldw	(0x05, sp), x
      008424 BC                     524 	.byte 0xbc
      008425                        525 00142$:
      008425 5F               [ 1]  526 	clrw	x
      008426 1F 05            [ 2]  527 	ldw	(0x05, sp), x
      008428                        528 00143$:
      008428 1E 05            [ 2]  529 	ldw	x, (0x05, sp)
      00842A                        530 00141$:
      00842A CF 00 1D         [ 2]  531 	ldw	_ps+15, x
                                    532 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
      00842D AE 00 1F         [ 2]  533 	ldw	x, #(_ps+17)
      008430 16 07            [ 2]  534 	ldw	y, (0x07, sp)
      008432 FF               [ 2]  535 	ldw	(x), y
      008433                        536 00124$:
                                    537 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 233: ps.fa = t;
      008433 AE 00 21         [ 2]  538 	ldw	x, #(_ps+19)
      008436 16 07            [ 2]  539 	ldw	y, (0x07, sp)
      008438 FF               [ 2]  540 	ldw	(x), y
                                    541 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 234: ps.sfa = s;
      008439 AE 00 23         [ 2]  542 	ldw	x, #(_ps+21)
      00843C 7B 01            [ 1]  543 	ld	a, (0x01, sp)
      00843E F7               [ 1]  544 	ld	(x), a
                                    545 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 235: ps.low_run = 0;
      00843F AE 00 1B         [ 2]  546 	ldw	x, #(_ps+13)
      008442 6F 01            [ 1]  547 	clr	(0x1, x)
      008444 7F               [ 1]  548 	clr	(x)
                                    549 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 236: ps.seen = 1;
      008445 35 01 00 19      [ 1]  550 	mov	_ps+11, #0x01
      008449 20 55            [ 2]  551 	jra	00132$
      00844B                        552 00131$:
                                    553 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 238: if (ps.in_pulse) {
      00844B C6 00 18         [ 1]  554 	ld	a, _ps+10
      00844E 27 36            [ 1]  555 	jreq	00126$
                                    556 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 239: ps.in_pulse = 0;
      008450 35 00 00 18      [ 1]  557 	mov	_ps+10, #0x00
                                    558 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 240: scan_ra = ps.ra; scan_rb = ps.rb;
      008454 CE 00 1D         [ 2]  559 	ldw	x, _ps+15
      008457 CF 00 05         [ 2]  560 	ldw	_scan_ra+0, x
      00845A CE 00 1F         [ 2]  561 	ldw	x, _ps+17
      00845D CF 00 07         [ 2]  562 	ldw	_scan_rb+0, x
                                    563 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 241: scan_fa = ps.fa; scan_fb = t; scan_sfa = ps.sfa;
      008460 CE 00 21         [ 2]  564 	ldw	x, _ps+19
      008463 CF 00 09         [ 2]  565 	ldw	_scan_fa+0, x
      008466 1E 07            [ 2]  566 	ldw	x, (0x07, sp)
      008468 CF 00 0B         [ 2]  567 	ldw	_scan_fb+0, x
      00846B 55 00 23 00 0D   [ 1]  568 	mov	_scan_sfa+0, _ps+21
                                    569 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 242: ps.t_prev = t; ps.have_prev = 1;
      008470 AE 00 15         [ 2]  570 	ldw	x, #(_ps+7)
      008473 16 07            [ 2]  571 	ldw	y, (0x07, sp)
      008475 FF               [ 2]  572 	ldw	(x), y
      008476 35 01 00 17      [ 1]  573 	mov	_ps+9, #0x01
                                    574 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 243: ps.low_run = 1;
      00847A 35 01 00 1C      [ 1]  575 	mov	_ps+14, #0x01
      00847E 35 00 00 1B      [ 1]  576 	mov	_ps+13, #0x00
                                    577 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 244: return 1;
      008482 A6 01            [ 1]  578 	ld	a, #0x01
      008484 20 59            [ 2]  579 	jra	00138$
      008486                        580 00126$:
                                    581 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 246: ps.low_run++;
      008486 CE 00 1B         [ 2]  582 	ldw	x, _ps+13
      008489 5C               [ 1]  583 	incw	x
      00848A CF 00 1B         [ 2]  584 	ldw	_ps+13, x
                                    585 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 247: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
      00848D C6 00 19         [ 1]  586 	ld	a, _ps+11
      008490 27 0E            [ 1]  587 	jreq	00132$
      008492 CE 00 1B         [ 2]  588 	ldw	x, _ps+13
      008495 A3 00 C8         [ 2]  589 	cpw	x, #0x00c8
      008498 25 06            [ 1]  590 	jrc	00132$
      00849A 35 01 00 1A      [ 1]  591 	mov	_ps+12, #0x01
      00849E 20 0D            [ 2]  592 	jra	00135$
      0084A0                        593 00132$:
                                    594 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 249: ps.t_prev = t;
      0084A0 AE 00 15         [ 2]  595 	ldw	x, #(_ps+7)
      0084A3 16 07            [ 2]  596 	ldw	y, (0x07, sp)
      0084A5 FF               [ 2]  597 	ldw	(x), y
                                    598 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 250: ps.have_prev = 1;
      0084A6 35 01 00 17      [ 1]  599 	mov	_ps+9, #0x01
      0084AA CC 82 67         [ 2]  600 	jp	00133$
      0084AD                        601 00135$:
                                    602 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 252: if (ps.in_pulse) {                      /* capture ended high */
      0084AD C6 00 18         [ 1]  603 	ld	a, _ps+10
      0084B0 27 28            [ 1]  604 	jreq	00137$
                                    605 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 253: ps.in_pulse = 0;
      0084B2 35 00 00 18      [ 1]  606 	mov	_ps+10, #0x00
                                    607 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 254: scan_ra = ps.ra; scan_rb = ps.rb;
      0084B6 CE 00 1D         [ 2]  608 	ldw	x, _ps+15
      0084B9 CF 00 05         [ 2]  609 	ldw	_scan_ra+0, x
      0084BC CE 00 1F         [ 2]  610 	ldw	x, _ps+17
      0084BF CF 00 07         [ 2]  611 	ldw	_scan_rb+0, x
                                    612 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 255: scan_fa = ps.fa; scan_fb = (uint16_t)(ps.fa + FIRST_BR);
      0084C2 CE 00 21         [ 2]  613 	ldw	x, _ps+19
      0084C5 CF 00 09         [ 2]  614 	ldw	_scan_fa+0, x
      0084C8 CE 00 21         [ 2]  615 	ldw	x, _ps+19
      0084CB 1C 00 04         [ 2]  616 	addw	x, #0x0004
      0084CE CF 00 0B         [ 2]  617 	ldw	_scan_fb+0, x
                                    618 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 256: scan_sfa = ps.sfa;
      0084D1 55 00 23 00 0D   [ 1]  619 	mov	_scan_sfa+0, _ps+21
                                    620 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 257: return 1;
      0084D6 A6 01            [ 1]  621 	ld	a, #0x01
      0084D8 20 05            [ 2]  622 	jra	00138$
      0084DA                        623 00137$:
                                    624 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 259: ps.done = 1;
      0084DA 35 01 00 1A      [ 1]  625 	mov	_ps+12, #0x01
                                    626 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 260: return 0;
      0084DE 4F               [ 1]  627 	clr	a
      0084DF                        628 00138$:
                                    629 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 261: }
      0084DF 5B 08            [ 2]  630 	addw	sp, #8
      0084E1 81               [ 4]  631 	ret
                                    632 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 301: static int32_t map_raw(uint16_t t)
                                    633 ;	-----------------------------------------
                                    634 ;	 function map_raw
                                    635 ;	-----------------------------------------
      0084E2                        636 _map_raw:
      0084E2 52 08            [ 2]  637 	sub	sp, #8
                                    638 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 303: return (int32_t)((uint32_t)t * g_K >> KQ) + g_tau;
      0084E4 90 CE 00 38      [ 2]  639 	ldw	y, _g_K+0
      0084E8 90 89            [ 2]  640 	pushw	y
      0084EA CD 9C 37         [ 4]  641 	call	___muluint2ulong
      0084ED 5B 02            [ 2]  642 	addw	sp, #2
      0084EF 51               [ 1]  643 	exgw	x, y
      0084F0 A6 0B            [ 1]  644 	ld	a, #0x0b
      0084F2                        645 00103$:
      0084F2 54               [ 2]  646 	srlw	x
      0084F3 90 56            [ 2]  647 	rrcw	y
      0084F5 4A               [ 1]  648 	dec	a
      0084F6 26 FA            [ 1]  649 	jrne	00103$
      0084F8 1F 01            [ 2]  650 	ldw	(0x01, sp), x
      0084FA CE 00 3A         [ 2]  651 	ldw	x, _g_tau+0
      0084FD 1F 07            [ 2]  652 	ldw	(0x07, sp), x
      0084FF 5F               [ 1]  653 	clrw	x
      008500 0D 07            [ 1]  654 	tnz	(0x07, sp)
      008502 2A 01            [ 1]  655 	jrpl	00105$
      008504 5A               [ 2]  656 	decw	x
      008505                        657 00105$:
      008505 72 F9 07         [ 2]  658 	addw	y, (0x07, sp)
      008508 9F               [ 1]  659 	ld	a, xl
      008509 19 02            [ 1]  660 	adc	a, (0x02, sp)
      00850B 02               [ 1]  661 	rlwa	x
      00850C 19 01            [ 1]  662 	adc	a, (0x01, sp)
      00850E 95               [ 1]  663 	ld	xh, a
      00850F 51               [ 1]  664 	exgw	x, y
                                    665 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 304: }
      008510 5B 08            [ 2]  666 	addw	sp, #8
      008512 81               [ 4]  667 	ret
                                    668 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 308: static uint8_t seed(void)
                                    669 ;	-----------------------------------------
                                    670 ;	 function seed
                                    671 ;	-----------------------------------------
      008513                        672 _seed:
      008513 52 06            [ 2]  673 	sub	sp, #6
                                    674 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 311: uint16_t r0m = 0, flm = 0;
      008515 5F               [ 1]  675 	clrw	x
      008516 1F 01            [ 2]  676 	ldw	(0x01, sp), x
      008518 5F               [ 1]  677 	clrw	x
                                    678 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 313: scan_init();
      008519 89               [ 2]  679 	pushw	x
      00851A CD 82 1C         [ 4]  680 	call	_scan_init
      00851D 85               [ 2]  681 	popw	x
                                    682 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 314: while (scan_next()) {
      00851E 90 5F            [ 1]  683 	clrw	y
      008520                        684 00103$:
      008520 89               [ 2]  685 	pushw	x
      008521 90 89            [ 2]  686 	pushw	y
      008523 CD 82 65         [ 4]  687 	call	_scan_next
      008526 90 85            [ 2]  688 	popw	y
      008528 85               [ 2]  689 	popw	x
      008529 4D               [ 1]  690 	tnz	a
      00852A 27 1A            [ 1]  691 	jreq	00105$
                                    692 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 315: if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
      00852C 90 5D            [ 2]  693 	tnzw	y
      00852E 26 0A            [ 1]  694 	jrne	00102$
      008530 CE 00 05         [ 2]  695 	ldw	x, _scan_ra+0
      008533 72 BB 00 07      [ 2]  696 	addw	x, _scan_rb+0
      008537 54               [ 2]  697 	srlw	x
      008538 1F 01            [ 2]  698 	ldw	(0x01, sp), x
      00853A                        699 00102$:
                                    700 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 316: flm = (uint16_t)((scan_fa + scan_fb) >> 1);
      00853A CE 00 09         [ 2]  701 	ldw	x, _scan_fa+0
      00853D 72 BB 00 0B      [ 2]  702 	addw	x, _scan_fb+0
      008541 54               [ 2]  703 	srlw	x
                                    704 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 317: np++;
      008542 90 5C            [ 1]  705 	incw	y
      008544 20 DA            [ 2]  706 	jra	00103$
      008546                        707 00105$:
                                    708 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 319: if (np < 8 || flm <= r0m) return 0;
      008546 90 A3 00 08      [ 2]  709 	cpw	y, #0x0008
      00854A 25 04            [ 1]  710 	jrc	00106$
      00854C 13 01            [ 2]  711 	cpw	x, (0x01, sp)
      00854E 22 03            [ 1]  712 	jrugt	00107$
      008550                        713 00106$:
      008550 4F               [ 1]  714 	clr	a
      008551 20 5E            [ 2]  715 	jra	00112$
      008553                        716 00107$:
                                    717 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 321: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
      008553 72 F0 01         [ 2]  718 	subw	x, (0x01, sp)
      008556 90 5F            [ 1]  719 	clrw	y
      008558 89               [ 2]  720 	pushw	x
      008559 90 89            [ 2]  721 	pushw	y
      00855B 4B 00            [ 1]  722 	push	#0x00
      00855D 4B A0            [ 1]  723 	push	#0xa0
      00855F 4B 79            [ 1]  724 	push	#0x79
      008561 4B 0D            [ 1]  725 	push	#0x0d
                                    726 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 322: if (K < K_MIN || K > K_MAX) return 0;
      008563 CD 9C B5         [ 4]  727 	call	__divulong
      008566 5B 08            [ 2]  728 	addw	sp, #8
      008568 1F 05            [ 2]  729 	ldw	(0x05, sp), x
      00856A 17 03            [ 2]  730 	ldw	(0x03, sp), y
      00856C 1E 05            [ 2]  731 	ldw	x, (0x05, sp)
      00856E A3 B3 B0         [ 2]  732 	cpw	x, #0xb3b0
      008571 7B 04            [ 1]  733 	ld	a, (0x04, sp)
      008573 A2 00            [ 1]  734 	sbc	a, #0x00
      008575 7B 03            [ 1]  735 	ld	a, (0x03, sp)
      008577 A2 00            [ 1]  736 	sbc	a, #0x00
      008579 25 0D            [ 1]  737 	jrc	00109$
      00857B AE EA 60         [ 2]  738 	ldw	x, #0xea60
      00857E 13 05            [ 2]  739 	cpw	x, (0x05, sp)
      008580 4F               [ 1]  740 	clr	a
      008581 12 04            [ 1]  741 	sbc	a, (0x04, sp)
      008583 4F               [ 1]  742 	clr	a
      008584 12 03            [ 1]  743 	sbc	a, (0x03, sp)
      008586 24 03            [ 1]  744 	jrnc	00110$
      008588                        745 00109$:
      008588 4F               [ 1]  746 	clr	a
      008589 20 26            [ 2]  747 	jra	00112$
      00858B                        748 00110$:
                                    749 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 323: g_K = (uint16_t)K;
      00858B 1E 05            [ 2]  750 	ldw	x, (0x05, sp)
      00858D CF 00 38         [ 2]  751 	ldw	_g_K+0, x
                                    752 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 324: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
      008590 16 01            [ 2]  753 	ldw	y, (0x01, sp)
      008592 CE 00 38         [ 2]  754 	ldw	x, _g_K+0
      008595 89               [ 2]  755 	pushw	x
      008596 93               [ 1]  756 	ldw	x, y
      008597 CD 9C 37         [ 4]  757 	call	___muluint2ulong
      00859A 5B 02            [ 2]  758 	addw	sp, #2
      00859C A6 0B            [ 1]  759 	ld	a, #0x0b
      00859E                        760 00161$:
      00859E 90 54            [ 2]  761 	srlw	y
      0085A0 56               [ 2]  762 	rrcw	x
      0085A1 4A               [ 1]  763 	dec	a
      0085A2 26 FA            [ 1]  764 	jrne	00161$
      0085A4 1F 05            [ 2]  765 	ldw	(0x05, sp), x
      0085A6 AE 02 00         [ 2]  766 	ldw	x, #0x0200
      0085A9 72 F0 05         [ 2]  767 	subw	x, (0x05, sp)
      0085AC CF 00 3A         [ 2]  768 	ldw	_g_tau+0, x
                                    769 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 325: return 1;
      0085AF A6 01            [ 1]  770 	ld	a, #0x01
      0085B1                        771 00112$:
                                    772 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 326: }
      0085B1 5B 06            [ 2]  773 	addw	sp, #6
      0085B3 81               [ 4]  774 	ret
                                    775 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 330: static void refine(void)
                                    776 ;	-----------------------------------------
                                    777 ;	 function refine
                                    778 ;	-----------------------------------------
      0085B4                        779 _refine:
      0085B4 52 28            [ 2]  780 	sub	sp, #40
                                    781 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 335: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
      0085B6 5F               [ 1]  782 	clrw	x
      0085B7 1F 17            [ 2]  783 	ldw	(0x17, sp), x
      0085B9 1F 15            [ 2]  784 	ldw	(0x15, sp), x
      0085BB 5F               [ 1]  785 	clrw	x
      0085BC 1F 1B            [ 2]  786 	ldw	(0x1b, sp), x
      0085BE 1F 19            [ 2]  787 	ldw	(0x19, sp), x
                                    788 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 336: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
      0085C0 5F               [ 1]  789 	clrw	x
      0085C1 1F 1F            [ 2]  790 	ldw	(0x1f, sp), x
      0085C3 1F 1D            [ 2]  791 	ldw	(0x1d, sp), x
      0085C5 5F               [ 1]  792 	clrw	x
      0085C6 1F 23            [ 2]  793 	ldw	(0x23, sp), x
      0085C8 1F 21            [ 2]  794 	ldw	(0x21, sp), x
                                    795 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 340: scan_init();
      0085CA CD 82 1C         [ 4]  796 	call	_scan_init
                                    797 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 341: while (scan_next()) {
      0085CD 5F               [ 1]  798 	clrw	x
      0085CE 1F 25            [ 2]  799 	ldw	(0x25, sp), x
      0085D0 5F               [ 1]  800 	clrw	x
      0085D1 1F 27            [ 2]  801 	ldw	(0x27, sp), x
      0085D3                        802 00108$:
      0085D3 CD 82 65         [ 4]  803 	call	_scan_next
      0085D6 4D               [ 1]  804 	tnz	a
      0085D7 26 03            [ 1]  805 	jrne	00186$
      0085D9 CC 86 98         [ 2]  806 	jp	00110$
      0085DC                        807 00186$:
                                    808 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 345: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      0085DC CE 00 05         [ 2]  809 	ldw	x, _scan_ra+0
      0085DF 72 BB 00 07      [ 2]  810 	addw	x, _scan_rb+0
      0085E3 54               [ 2]  811 	srlw	x
      0085E4 CD 84 E2         [ 4]  812 	call	_map_raw
      0085E7 1F 0D            [ 2]  813 	ldw	(0x0d, sp), x
      0085E9 17 0B            [ 2]  814 	ldw	(0x0b, sp), y
                                    815 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 346: if (y < 0) y = 0;
      0085EB 0D 0B            [ 1]  816 	tnz	(0x0b, sp)
      0085ED 2A 05            [ 1]  817 	jrpl	00102$
      0085EF 5F               [ 1]  818 	clrw	x
      0085F0 1F 0D            [ 2]  819 	ldw	(0x0d, sp), x
      0085F2 1F 0B            [ 2]  820 	ldw	(0x0b, sp), x
      0085F4                        821 00102$:
                                    822 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 347: if ((uint32_t)y > y_end) break;
      0085F4 16 0D            [ 2]  823 	ldw	y, (0x0d, sp)
      0085F6 17 11            [ 2]  824 	ldw	(0x11, sp), y
      0085F8 16 0B            [ 2]  825 	ldw	y, (0x0b, sp)
      0085FA 17 0F            [ 2]  826 	ldw	(0x0f, sp), y
      0085FC AE B2 A4         [ 2]  827 	ldw	x, #0xb2a4
      0085FF 13 11            [ 2]  828 	cpw	x, (0x11, sp)
      008601 A6 01            [ 1]  829 	ld	a, #0x01
      008603 12 10            [ 1]  830 	sbc	a, (0x10, sp)
      008605 4F               [ 1]  831 	clr	a
      008606 12 0F            [ 1]  832 	sbc	a, (0x0f, sp)
      008608 24 03            [ 1]  833 	jrnc	00188$
      00860A CC 86 98         [ 2]  834 	jp	00110$
      00860D                        835 00188$:
                                    836 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 348: q = ((uint32_t)y + BIT_H) >> BIT_SH;
      00860D 1E 11            [ 2]  837 	ldw	x, (0x11, sp)
      00860F 1C 01 00         [ 2]  838 	addw	x, #0x0100
      008612 16 0F            [ 2]  839 	ldw	y, (0x0f, sp)
      008614 24 02            [ 1]  840 	jrnc	00189$
      008616 90 5C            [ 1]  841 	incw	y
      008618                        842 00189$:
      008618 90 54            [ 2]  843 	srlw	y
      00861A 56               [ 2]  844 	rrcw	x
                                    845 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 349: e = (int16_t)(y - (int32_t)(q << BIT_SH));
      00861B 4F               [ 1]  846 	clr	a
      00861C 97               [ 1]  847 	ld	xl, a
      00861D 58               [ 2]  848 	sllw	x
      00861E 16 0D            [ 2]  849 	ldw	y, (0x0d, sp)
      008620 17 13            [ 2]  850 	ldw	(0x13, sp), y
      008622 50               [ 2]  851 	negw	x
      008623 72 FB 13         [ 2]  852 	addw	x, (0x13, sp)
                                    853 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 350: if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
      008626 51               [ 1]  854 	exgw	x, y
      008627 90 9E            [ 1]  855 	ld	a, yh
      008629 49               [ 1]  856 	rlc	a
      00862A 4F               [ 1]  857 	clr	a
      00862B A2 00            [ 1]  858 	sbc	a, #0x00
      00862D 88               [ 1]  859 	push	a
      00862E 6B 0C            [ 1]  860 	ld	(0x0c, sp), a
      008630 84               [ 1]  861 	pop	a
      008631 1E 11            [ 2]  862 	ldw	x, (0x11, sp)
      008633 A3 DA 00         [ 2]  863 	cpw	x, #0xda00
      008636 88               [ 1]  864 	push	a
      008637 7B 11            [ 1]  865 	ld	a, (0x11, sp)
      008639 A2 00            [ 1]  866 	sbc	a, #0x00
      00863B 7B 10            [ 1]  867 	ld	a, (0x10, sp)
      00863D A2 00            [ 1]  868 	sbc	a, #0x00
      00863F 84               [ 1]  869 	pop	a
      008640 24 2B            [ 1]  870 	jrnc	00106$
      008642 1E 25            [ 2]  871 	ldw	x, (0x25, sp)
      008644 5C               [ 1]  872 	incw	x
      008645 1F 25            [ 2]  873 	ldw	(0x25, sp), x
      008647 93               [ 1]  874 	ldw	x, y
      008648 72 FB 17         [ 2]  875 	addw	x, (0x17, sp)
      00864B 1F 17            [ 2]  876 	ldw	(0x17, sp), x
      00864D 19 16            [ 1]  877 	adc	a, (0x16, sp)
      00864F 6B 16            [ 1]  878 	ld	(0x16, sp), a
      008651 7B 0B            [ 1]  879 	ld	a, (0x0b, sp)
      008653 19 15            [ 1]  880 	adc	a, (0x15, sp)
      008655 6B 15            [ 1]  881 	ld	(0x15, sp), a
      008657 1E 1F            [ 2]  882 	ldw	x, (0x1f, sp)
      008659 72 FB 11         [ 2]  883 	addw	x, (0x11, sp)
      00865C 1F 1F            [ 2]  884 	ldw	(0x1f, sp), x
      00865E 7B 1E            [ 1]  885 	ld	a, (0x1e, sp)
      008660 19 10            [ 1]  886 	adc	a, (0x10, sp)
      008662 6B 1E            [ 1]  887 	ld	(0x1e, sp), a
      008664 7B 1D            [ 1]  888 	ld	a, (0x1d, sp)
      008666 19 0F            [ 1]  889 	adc	a, (0x0f, sp)
      008668 6B 1D            [ 1]  890 	ld	(0x1d, sp), a
      00866A CC 85 D3         [ 2]  891 	jp	00108$
      00866D                        892 00106$:
                                    893 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 351: else                     { n_hi++; se_hi += e; sy_hi += (uint32_t)y; }
      00866D 1E 27            [ 2]  894 	ldw	x, (0x27, sp)
      00866F 5C               [ 1]  895 	incw	x
      008670 1F 27            [ 2]  896 	ldw	(0x27, sp), x
      008672 93               [ 1]  897 	ldw	x, y
      008673 72 FB 1B         [ 2]  898 	addw	x, (0x1b, sp)
      008676 1F 1B            [ 2]  899 	ldw	(0x1b, sp), x
      008678 19 1A            [ 1]  900 	adc	a, (0x1a, sp)
      00867A 6B 1A            [ 1]  901 	ld	(0x1a, sp), a
      00867C 7B 0B            [ 1]  902 	ld	a, (0x0b, sp)
      00867E 19 19            [ 1]  903 	adc	a, (0x19, sp)
      008680 6B 19            [ 1]  904 	ld	(0x19, sp), a
      008682 1E 23            [ 2]  905 	ldw	x, (0x23, sp)
      008684 72 FB 11         [ 2]  906 	addw	x, (0x11, sp)
      008687 1F 23            [ 2]  907 	ldw	(0x23, sp), x
      008689 7B 22            [ 1]  908 	ld	a, (0x22, sp)
      00868B 19 10            [ 1]  909 	adc	a, (0x10, sp)
      00868D 6B 22            [ 1]  910 	ld	(0x22, sp), a
      00868F 7B 21            [ 1]  911 	ld	a, (0x21, sp)
      008691 19 0F            [ 1]  912 	adc	a, (0x0f, sp)
      008693 6B 21            [ 1]  913 	ld	(0x21, sp), a
      008695 CC 85 D3         [ 2]  914 	jp	00108$
      008698                        915 00110$:
                                    916 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 353: if (n_lo < 2 || n_hi < 2) return;
      008698 1E 25            [ 2]  917 	ldw	x, (0x25, sp)
      00869A A3 00 02         [ 2]  918 	cpw	x, #0x0002
      00869D 24 03            [ 1]  919 	jrnc	00193$
      00869F CC 88 40         [ 2]  920 	jp	00119$
      0086A2                        921 00193$:
      0086A2 1E 27            [ 2]  922 	ldw	x, (0x27, sp)
      0086A4 A3 00 02         [ 2]  923 	cpw	x, #0x0002
      0086A7 24 03            [ 1]  924 	jrnc	00112$
      0086A9 CC 88 40         [ 2]  925 	jp	00119$
      0086AC                        926 00112$:
                                    927 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 354: me_lo = se_lo / (int32_t)n_lo;
      0086AC 16 25            [ 2]  928 	ldw	y, (0x25, sp)
      0086AE 5F               [ 1]  929 	clrw	x
      0086AF 90 89            [ 2]  930 	pushw	y
      0086B1 89               [ 2]  931 	pushw	x
      0086B2 1E 1B            [ 2]  932 	ldw	x, (0x1b, sp)
      0086B4 89               [ 2]  933 	pushw	x
      0086B5 1E 1B            [ 2]  934 	ldw	x, (0x1b, sp)
      0086B7 89               [ 2]  935 	pushw	x
                                    936 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 355: me_hi = se_hi / (int32_t)n_hi;
      0086B8 CD 9C 8E         [ 4]  937 	call	__divslong
      0086BB 5B 08            [ 2]  938 	addw	sp, #8
      0086BD 1F 07            [ 2]  939 	ldw	(0x07, sp), x
      0086BF 17 05            [ 2]  940 	ldw	(0x05, sp), y
      0086C1 16 27            [ 2]  941 	ldw	y, (0x27, sp)
      0086C3 5F               [ 1]  942 	clrw	x
      0086C4 90 89            [ 2]  943 	pushw	y
      0086C6 89               [ 2]  944 	pushw	x
      0086C7 1E 1F            [ 2]  945 	ldw	x, (0x1f, sp)
      0086C9 89               [ 2]  946 	pushw	x
      0086CA 1E 1F            [ 2]  947 	ldw	x, (0x1f, sp)
      0086CC 89               [ 2]  948 	pushw	x
                                    949 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 356: my_lo = sy_lo / n_lo;
      0086CD CD 9C 8E         [ 4]  950 	call	__divslong
      0086D0 5B 08            [ 2]  951 	addw	sp, #8
      0086D2 1F 0B            [ 2]  952 	ldw	(0x0b, sp), x
      0086D4 17 09            [ 2]  953 	ldw	(0x09, sp), y
      0086D6 16 25            [ 2]  954 	ldw	y, (0x25, sp)
      0086D8 5F               [ 1]  955 	clrw	x
      0086D9 90 89            [ 2]  956 	pushw	y
      0086DB 89               [ 2]  957 	pushw	x
      0086DC 1E 23            [ 2]  958 	ldw	x, (0x23, sp)
      0086DE 89               [ 2]  959 	pushw	x
      0086DF 1E 23            [ 2]  960 	ldw	x, (0x23, sp)
      0086E1 89               [ 2]  961 	pushw	x
                                    962 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 357: my_hi = sy_hi / n_hi;
      0086E2 CD 9C B5         [ 4]  963 	call	__divulong
      0086E5 5B 08            [ 2]  964 	addw	sp, #8
      0086E7 1F 13            [ 2]  965 	ldw	(0x13, sp), x
      0086E9 17 11            [ 2]  966 	ldw	(0x11, sp), y
      0086EB 16 27            [ 2]  967 	ldw	y, (0x27, sp)
      0086ED 5F               [ 1]  968 	clrw	x
      0086EE 90 89            [ 2]  969 	pushw	y
      0086F0 89               [ 2]  970 	pushw	x
      0086F1 1E 27            [ 2]  971 	ldw	x, (0x27, sp)
      0086F3 89               [ 2]  972 	pushw	x
      0086F4 1E 27            [ 2]  973 	ldw	x, (0x27, sp)
      0086F6 89               [ 2]  974 	pushw	x
                                    975 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 358: de = me_hi - me_lo;
      0086F7 CD 9C B5         [ 4]  976 	call	__divulong
      0086FA 5B 08            [ 2]  977 	addw	sp, #8
      0086FC 17 0D            [ 2]  978 	ldw	(0x0d, sp), y
      0086FE 16 0B            [ 2]  979 	ldw	y, (0x0b, sp)
      008700 72 F2 07         [ 2]  980 	subw	y, (0x07, sp)
      008703 17 03            [ 2]  981 	ldw	(0x03, sp), y
      008705 7B 0A            [ 1]  982 	ld	a, (0x0a, sp)
      008707 12 06            [ 1]  983 	sbc	a, (0x06, sp)
      008709 6B 02            [ 1]  984 	ld	(0x02, sp), a
      00870B 7B 09            [ 1]  985 	ld	a, (0x09, sp)
      00870D 12 05            [ 1]  986 	sbc	a, (0x05, sp)
      00870F 6B 01            [ 1]  987 	ld	(0x01, sp), a
                                    988 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 359: dy = (int32_t)my_hi - (int32_t)my_lo;
      008711 7B 0E            [ 1]  989 	ld	a, (0x0e, sp)
      008713 72 F0 13         [ 2]  990 	subw	x, (0x13, sp)
      008716 1F 07            [ 2]  991 	ldw	(0x07, sp), x
      008718 12 12            [ 1]  992 	sbc	a, (0x12, sp)
      00871A 6B 06            [ 1]  993 	ld	(0x06, sp), a
      00871C 7B 0D            [ 1]  994 	ld	a, (0x0d, sp)
      00871E 12 11            [ 1]  995 	sbc	a, (0x11, sp)
      008720 6B 05            [ 1]  996 	ld	(0x05, sp), a
                                    997 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 360: if (dy <= 0) return;
      008722 5F               [ 1]  998 	clrw	x
      008723 13 07            [ 2]  999 	cpw	x, (0x07, sp)
      008725 4F               [ 1] 1000 	clr	a
      008726 12 06            [ 1] 1001 	sbc	a, (0x06, sp)
      008728 4F               [ 1] 1002 	clr	a
      008729 12 05            [ 1] 1003 	sbc	a, (0x05, sp)
      00872B 2F 03            [ 1] 1004 	jrslt	00115$
      00872D CC 88 40         [ 2] 1005 	jp	00119$
      008730                       1006 00115$:
                                   1007 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 361: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
      008730 CE 00 38         [ 2] 1008 	ldw	x, _g_K+0
      008733 1F 0B            [ 2] 1009 	ldw	(0x0b, sp), x
      008735 0F 0A            [ 1] 1010 	clr	(0x0a, sp)
      008737 0F 09            [ 1] 1011 	clr	(0x09, sp)
      008739 1E 03            [ 2] 1012 	ldw	x, (0x03, sp)
      00873B 89               [ 2] 1013 	pushw	x
      00873C 1E 03            [ 2] 1014 	ldw	x, (0x03, sp)
      00873E 89               [ 2] 1015 	pushw	x
      00873F 1E 0F            [ 2] 1016 	ldw	x, (0x0f, sp)
      008741 89               [ 2] 1017 	pushw	x
      008742 1E 0F            [ 2] 1018 	ldw	x, (0x0f, sp)
      008744 89               [ 2] 1019 	pushw	x
      008745 CD 9D 12         [ 4] 1020 	call	__mullong
      008748 5B 08            [ 2] 1021 	addw	sp, #8
      00874A 1F 13            [ 2] 1022 	ldw	(0x13, sp), x
      00874C 1E 07            [ 2] 1023 	ldw	x, (0x07, sp)
      00874E 89               [ 2] 1024 	pushw	x
      00874F 1E 07            [ 2] 1025 	ldw	x, (0x07, sp)
      008751 89               [ 2] 1026 	pushw	x
      008752 1E 17            [ 2] 1027 	ldw	x, (0x17, sp)
      008754 89               [ 2] 1028 	pushw	x
      008755 90 89            [ 2] 1029 	pushw	y
                                   1030 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 362: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
      008757 CD 9C 8E         [ 4] 1031 	call	__divslong
      00875A 5B 08            [ 2] 1032 	addw	sp, #8
      00875C 1F 0F            [ 2] 1033 	ldw	(0x0f, sp), x
      00875E 17 0D            [ 2] 1034 	ldw	(0x0d, sp), y
      008760 1E 17            [ 2] 1035 	ldw	x, (0x17, sp)
      008762 72 FB 1B         [ 2] 1036 	addw	x, (0x1b, sp)
      008765 1F 13            [ 2] 1037 	ldw	(0x13, sp), x
      008767 7B 16            [ 1] 1038 	ld	a, (0x16, sp)
      008769 19 1A            [ 1] 1039 	adc	a, (0x1a, sp)
      00876B 6B 12            [ 1] 1040 	ld	(0x12, sp), a
      00876D 7B 15            [ 1] 1041 	ld	a, (0x15, sp)
      00876F 19 19            [ 1] 1042 	adc	a, (0x19, sp)
      008771 6B 11            [ 1] 1043 	ld	(0x11, sp), a
      008773 1E 25            [ 2] 1044 	ldw	x, (0x25, sp)
      008775 72 FB 27         [ 2] 1045 	addw	x, (0x27, sp)
      008778 1F 1B            [ 2] 1046 	ldw	(0x1b, sp), x
      00877A 90 93            [ 1] 1047 	ldw	y, x
      00877C 5F               [ 1] 1048 	clrw	x
      00877D 90 89            [ 2] 1049 	pushw	y
      00877F 89               [ 2] 1050 	pushw	x
      008780 1E 17            [ 2] 1051 	ldw	x, (0x17, sp)
      008782 89               [ 2] 1052 	pushw	x
      008783 1E 17            [ 2] 1053 	ldw	x, (0x17, sp)
      008785 89               [ 2] 1054 	pushw	x
                                   1055 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 363: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
      008786 CD 9C 8E         [ 4] 1056 	call	__divslong
      008789 5B 08            [ 2] 1057 	addw	sp, #8
      00878B 1F 19            [ 2] 1058 	ldw	(0x19, sp), x
      00878D 17 17            [ 2] 1059 	ldw	(0x17, sp), y
      00878F 1E 1F            [ 2] 1060 	ldw	x, (0x1f, sp)
      008791 72 FB 23         [ 2] 1061 	addw	x, (0x23, sp)
      008794 1F 27            [ 2] 1062 	ldw	(0x27, sp), x
      008796 7B 1E            [ 1] 1063 	ld	a, (0x1e, sp)
      008798 19 22            [ 1] 1064 	adc	a, (0x22, sp)
      00879A 6B 26            [ 1] 1065 	ld	(0x26, sp), a
      00879C 7B 1D            [ 1] 1066 	ld	a, (0x1d, sp)
      00879E 19 21            [ 1] 1067 	adc	a, (0x21, sp)
      0087A0 6B 25            [ 1] 1068 	ld	(0x25, sp), a
      0087A2 16 1B            [ 2] 1069 	ldw	y, (0x1b, sp)
      0087A4 5F               [ 1] 1070 	clrw	x
      0087A5 90 89            [ 2] 1071 	pushw	y
      0087A7 89               [ 2] 1072 	pushw	x
      0087A8 1E 2B            [ 2] 1073 	ldw	x, (0x2b, sp)
      0087AA 89               [ 2] 1074 	pushw	x
      0087AB 1E 2B            [ 2] 1075 	ldw	x, (0x2b, sp)
      0087AD 89               [ 2] 1076 	pushw	x
                                   1077 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 364: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
      0087AE CD 9C B5         [ 4] 1078 	call	__divulong
      0087B1 5B 08            [ 2] 1079 	addw	sp, #8
      0087B3 51               [ 1] 1080 	exgw	x, y
      0087B4 7B 19            [ 1] 1081 	ld	a, (0x19, sp)
      0087B6 6B 27            [ 1] 1082 	ld	(0x27, sp), a
      0087B8 7B 1A            [ 1] 1083 	ld	a, (0x1a, sp)
      0087BA 40               [ 1] 1084 	neg	a
      0087BB 6B 20            [ 1] 1085 	ld	(0x20, sp), a
      0087BD 4F               [ 1] 1086 	clr	a
      0087BE 12 27            [ 1] 1087 	sbc	a, (0x27, sp)
      0087C0 6B 1F            [ 1] 1088 	ld	(0x1f, sp), a
      0087C2 1F 21            [ 2] 1089 	ldw	(0x21, sp), x
      0087C4 CE 00 3A         [ 2] 1090 	ldw	x, _g_tau+0
      0087C7 1F 27            [ 2] 1091 	ldw	(0x27, sp), x
      0087C9 7B 27            [ 1] 1092 	ld	a, (0x27, sp)
      0087CB 49               [ 1] 1093 	rlc	a
      0087CC 4F               [ 1] 1094 	clr	a
      0087CD A2 00            [ 1] 1095 	sbc	a, #0x00
      0087CF 6B 26            [ 1] 1096 	ld	(0x26, sp), a
      0087D1 6B 25            [ 1] 1097 	ld	(0x25, sp), a
      0087D3 72 F2 27         [ 2] 1098 	subw	y, (0x27, sp)
      0087D6 7B 22            [ 1] 1099 	ld	a, (0x22, sp)
      0087D8 12 26            [ 1] 1100 	sbc	a, (0x26, sp)
      0087DA 97               [ 1] 1101 	ld	xl, a
      0087DB 7B 21            [ 1] 1102 	ld	a, (0x21, sp)
      0087DD 12 25            [ 1] 1103 	sbc	a, (0x25, sp)
      0087DF 95               [ 1] 1104 	ld	xh, a
      0087E0 90 89            [ 2] 1105 	pushw	y
      0087E2 89               [ 2] 1106 	pushw	x
      0087E3 1E 07            [ 2] 1107 	ldw	x, (0x07, sp)
      0087E5 89               [ 2] 1108 	pushw	x
      0087E6 1E 07            [ 2] 1109 	ldw	x, (0x07, sp)
      0087E8 89               [ 2] 1110 	pushw	x
      0087E9 CD 9D 12         [ 4] 1111 	call	__mullong
      0087EC 5B 08            [ 2] 1112 	addw	sp, #8
      0087EE 1F 27            [ 2] 1113 	ldw	(0x27, sp), x
      0087F0 1E 07            [ 2] 1114 	ldw	x, (0x07, sp)
      0087F2 89               [ 2] 1115 	pushw	x
      0087F3 1E 07            [ 2] 1116 	ldw	x, (0x07, sp)
      0087F5 89               [ 2] 1117 	pushw	x
      0087F6 1E 2B            [ 2] 1118 	ldw	x, (0x2b, sp)
      0087F8 89               [ 2] 1119 	pushw	x
      0087F9 90 89            [ 2] 1120 	pushw	y
      0087FB CD 9C 8E         [ 4] 1121 	call	__divslong
      0087FE 5B 08            [ 2] 1122 	addw	sp, #8
      008800 72 FB 1F         [ 2] 1123 	addw	x, (0x1f, sp)
      008803 1F 27            [ 2] 1124 	ldw	(0x27, sp), x
                                   1125 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 365: K2 = (int32_t)g_K - dk;
      008805 1E 0B            [ 2] 1126 	ldw	x, (0x0b, sp)
      008807 72 F0 0F         [ 2] 1127 	subw	x, (0x0f, sp)
      00880A 1F 25            [ 2] 1128 	ldw	(0x25, sp), x
      00880C 4F               [ 1] 1129 	clr	a
      00880D 12 0E            [ 1] 1130 	sbc	a, (0x0e, sp)
      00880F 6B 24            [ 1] 1131 	ld	(0x24, sp), a
      008811 4F               [ 1] 1132 	clr	a
      008812 12 0D            [ 1] 1133 	sbc	a, (0x0d, sp)
      008814 6B 23            [ 1] 1134 	ld	(0x23, sp), a
                                   1135 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 366: if (K2 < (int32_t)K_MIN || K2 > (int32_t)K_MAX) return;
      008816 1E 25            [ 2] 1136 	ldw	x, (0x25, sp)
      008818 A3 B3 B0         [ 2] 1137 	cpw	x, #0xb3b0
      00881B 7B 24            [ 1] 1138 	ld	a, (0x24, sp)
      00881D A2 00            [ 1] 1139 	sbc	a, #0x00
      00881F 7B 23            [ 1] 1140 	ld	a, (0x23, sp)
      008821 A2 00            [ 1] 1141 	sbc	a, #0x00
      008823 2F 1B            [ 1] 1142 	jrslt	00119$
      008825 AE EA 60         [ 2] 1143 	ldw	x, #0xea60
      008828 13 25            [ 2] 1144 	cpw	x, (0x25, sp)
      00882A 4F               [ 1] 1145 	clr	a
      00882B 12 24            [ 1] 1146 	sbc	a, (0x24, sp)
      00882D 4F               [ 1] 1147 	clr	a
      00882E 12 23            [ 1] 1148 	sbc	a, (0x23, sp)
      008830 2F 0E            [ 1] 1149 	jrslt	00119$
                                   1150 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 367: g_K = (uint16_t)K2;
      008832 1E 25            [ 2] 1151 	ldw	x, (0x25, sp)
      008834 CF 00 38         [ 2] 1152 	ldw	_g_K+0, x
                                   1153 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 368: g_tau = (int16_t)(g_tau + dtau);
      008837 CE 00 3A         [ 2] 1154 	ldw	x, _g_tau+0
      00883A 72 FB 27         [ 2] 1155 	addw	x, (0x27, sp)
      00883D CF 00 3A         [ 2] 1156 	ldw	_g_tau+0, x
      008840                       1157 00119$:
                                   1158 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 369: }
      008840 5B 28            [ 2] 1159 	addw	sp, #40
      008842 81               [ 4] 1160 	ret
                                   1161 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 393: static void ss_init(void)
                                   1162 ;	-----------------------------------------
                                   1163 ;	 function ss_init
                                   1164 ;	-----------------------------------------
      008843                       1165 _ss_init:
                                   1166 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 395: scan_init();
      008843 CD 82 1C         [ 4] 1167 	call	_scan_init
                                   1168 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 396: ss.y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
      008846 AE 01 50         [ 2] 1169 	ldw	x, #(_ss+0)
      008849 90 AE B2 A4      [ 2] 1170 	ldw	y, #0xb2a4
      00884D EF 02            [ 2] 1171 	ldw	(0x2, x), y
      00884F 90 AE 00 01      [ 2] 1172 	ldw	y, #0x0001
      008853 FF               [ 2] 1173 	ldw	(x), y
                                   1174 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 397: ss.y_prev = 0; ss.have_y = 0; ss.n = 0;
      008854 AE 01 54         [ 2] 1175 	ldw	x, #(_ss+4)
      008857 90 5F            [ 1] 1176 	clrw	y
      008859 EF 02            [ 2] 1177 	ldw	(0x2, x), y
      00885B FF               [ 2] 1178 	ldw	(x), y
      00885C 35 00 01 58      [ 1] 1179 	mov	_ss+8, #0x00
      008860 AE 01 59         [ 2] 1180 	ldw	x, #(_ss+9)
      008863 6F 01            [ 1] 1181 	clr	(0x1, x)
      008865 7F               [ 1] 1182 	clr	(x)
                                   1183 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 398: ss.pend = 0; ss.src_done = 0;
      008866 35 00 01 5B      [ 1] 1184 	mov	_ss+11, #0x00
      00886A 35 00 01 63      [ 1] 1185 	mov	_ss+19, #0x00
                                   1186 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 399: ss.p_k0 = 0; ss.p_u = 0; ss.p_v = 0; ss.p_fam = 0;
      00886E AE 01 5C         [ 2] 1187 	ldw	x, #(_ss+12)
      008871 6F 01            [ 1] 1188 	clr	(0x1, x)
      008873 7F               [ 1] 1189 	clr	(x)
      008874 AE 01 5E         [ 2] 1190 	ldw	x, #(_ss+14)
      008877 6F 01            [ 1] 1191 	clr	(0x1, x)
      008879 7F               [ 1] 1192 	clr	(x)
      00887A AE 01 60         [ 2] 1193 	ldw	x, #(_ss+16)
      00887D 6F 01            [ 1] 1194 	clr	(0x1, x)
      00887F 7F               [ 1] 1195 	clr	(x)
      008880 35 00 01 62      [ 1] 1196 	mov	_ss+18, #0x00
                                   1197 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 400: }
      008884 81               [ 4] 1198 	ret
                                   1199 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 402: static uint8_t ss_next(Seg *out)
                                   1200 ;	-----------------------------------------
                                   1201 ;	 function ss_next
                                   1202 ;	-----------------------------------------
      008885                       1203 _ss_next:
      008885 52 1C            [ 2] 1204 	sub	sp, #28
      008887 1F 1B            [ 2] 1205 	ldw	(0x1b, sp), x
                                   1206 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      008889                       1207 00121$:
      008889 C6 01 63         [ 1] 1208 	ld	a, _ss+19
                                   1209 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
                                   1210 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
                                   1211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
                                   1212 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
                                   1213 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      00888C 16 1B            [ 2] 1214 	ldw	y, (0x1b, sp)
      00888E 17 01            [ 2] 1215 	ldw	(0x01, sp), y
                                   1216 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      008890 1E 1B            [ 2] 1217 	ldw	x, (0x1b, sp)
      008892 5C               [ 1] 1218 	incw	x
      008893 5C               [ 1] 1219 	incw	x
      008894 1F 03            [ 2] 1220 	ldw	(0x03, sp), x
                                   1221 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      008896 1E 1B            [ 2] 1222 	ldw	x, (0x1b, sp)
      008898 1C 00 04         [ 2] 1223 	addw	x, #0x0004
      00889B 1F 05            [ 2] 1224 	ldw	(0x05, sp), x
      00889D 1E 1B            [ 2] 1225 	ldw	x, (0x1b, sp)
      00889F 1C 00 06         [ 2] 1226 	addw	x, #0x0006
      0088A2 1F 07            [ 2] 1227 	ldw	(0x07, sp), x
      0088A4 1E 1B            [ 2] 1228 	ldw	x, (0x1b, sp)
      0088A6 1C 00 08         [ 2] 1229 	addw	x, #0x0008
      0088A9 1F 09            [ 2] 1230 	ldw	(0x09, sp), x
                                   1231 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      0088AB 4D               [ 1] 1232 	tnz	a
      0088AC 27 03            [ 1] 1233 	jreq	00242$
      0088AE CC 8A 81         [ 2] 1234 	jp	00123$
      0088B1                       1235 00242$:
                                   1236 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 409: if (!scan_next()) { ss.src_done = 1; break; }
      0088B1 CD 82 65         [ 4] 1237 	call	_scan_next
      0088B4 4D               [ 1] 1238 	tnz	a
      0088B5 26 07            [ 1] 1239 	jrne	00102$
      0088B7 35 01 01 63      [ 1] 1240 	mov	_ss+19, #0x01
      0088BB CC 8A 81         [ 2] 1241 	jp	00123$
      0088BE                       1242 00102$:
                                   1243 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 410: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      0088BE CE 00 05         [ 2] 1244 	ldw	x, _scan_ra+0
      0088C1 72 BB 00 07      [ 2] 1245 	addw	x, _scan_rb+0
      0088C5 54               [ 2] 1246 	srlw	x
      0088C6 CD 84 E2         [ 4] 1247 	call	_map_raw
      0088C9 1F 0D            [ 2] 1248 	ldw	(0x0d, sp), x
      0088CB 17 0B            [ 2] 1249 	ldw	(0x0b, sp), y
                                   1250 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 411: if (y < 0) y = 0;
      0088CD 0D 0B            [ 1] 1251 	tnz	(0x0b, sp)
      0088CF 2A 05            [ 1] 1252 	jrpl	00104$
      0088D1 5F               [ 1] 1253 	clrw	x
      0088D2 1F 0D            [ 2] 1254 	ldw	(0x0d, sp), x
      0088D4 1F 0B            [ 2] 1255 	ldw	(0x0b, sp), x
      0088D6                       1256 00104$:
                                   1257 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 412: if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
      0088D6 16 0D            [ 2] 1258 	ldw	y, (0x0d, sp)
      0088D8 17 11            [ 2] 1259 	ldw	(0x11, sp), y
      0088DA 16 0B            [ 2] 1260 	ldw	y, (0x0b, sp)
      0088DC 17 0F            [ 2] 1261 	ldw	(0x0f, sp), y
      0088DE AE 01 50         [ 2] 1262 	ldw	x, #(_ss+0)
      0088E1 90 93            [ 1] 1263 	ldw	y, x
      0088E3 90 EE 02         [ 2] 1264 	ldw	y, (0x2, y)
      0088E6 FE               [ 2] 1265 	ldw	x, (x)
      0088E7 90 9F            [ 1] 1266 	ld	a, yl
      0088E9 11 12            [ 1] 1267 	cp	a, (0x12, sp)
      0088EB 90 9E            [ 1] 1268 	ld	a, yh
      0088ED 12 11            [ 1] 1269 	sbc	a, (0x11, sp)
      0088EF 9F               [ 1] 1270 	ld	a, xl
      0088F0 12 10            [ 1] 1271 	sbc	a, (0x10, sp)
      0088F2 9E               [ 1] 1272 	ld	a, xh
      0088F3 12 0F            [ 1] 1273 	sbc	a, (0x0f, sp)
      0088F5 24 07            [ 1] 1274 	jrnc	00106$
      0088F7 35 01 01 63      [ 1] 1275 	mov	_ss+19, #0x01
      0088FB CC 8A 81         [ 2] 1276 	jp	00123$
      0088FE                       1277 00106$:
                                   1278 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
                                   1279 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
                                   1280 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
      0088FE C6 01 58         [ 1] 1281 	ld	a, _ss+8
      008901 26 0C            [ 1] 1282 	jrne	00110$
      008903 AE 01 59         [ 2] 1283 	ldw	x, #(_ss+9)
      008906 6F 01            [ 1] 1284 	clr	(0x1, x)
      008908 7F               [ 1] 1285 	clr	(x)
      008909 35 01 01 58      [ 1] 1286 	mov	_ss+8, #0x01
      00890D 20 43            [ 2] 1287 	jra	00111$
      00890F                       1288 00110$:
                                   1289 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
      00890F AE 01 54         [ 2] 1290 	ldw	x, #(_ss+4)
      008912 90 93            [ 1] 1291 	ldw	y, x
      008914 90 EE 02         [ 2] 1292 	ldw	y, (0x2, y)
      008917 FE               [ 2] 1293 	ldw	x, (x)
      008918 17 15            [ 2] 1294 	ldw	(0x15, sp), y
      00891A 1F 13            [ 2] 1295 	ldw	(0x13, sp), x
      00891C 16 0D            [ 2] 1296 	ldw	y, (0x0d, sp)
      00891E 72 F2 15         [ 2] 1297 	subw	y, (0x15, sp)
      008921 7B 0C            [ 1] 1298 	ld	a, (0x0c, sp)
      008923 12 14            [ 1] 1299 	sbc	a, (0x14, sp)
      008925 6B 18            [ 1] 1300 	ld	(0x18, sp), a
      008927 7B 0B            [ 1] 1301 	ld	a, (0x0b, sp)
      008929 12 13            [ 1] 1302 	sbc	a, (0x13, sp)
      00892B 6B 17            [ 1] 1303 	ld	(0x17, sp), a
                                   1304 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 416: dn = (int16_t)((d + BIT_H) >> BIT_SH);
      00892D 72 A9 01 00      [ 2] 1305 	addw	y, #0x0100
      008931 1E 17            [ 2] 1306 	ldw	x, (0x17, sp)
      008933 24 01            [ 1] 1307 	jrnc	00247$
      008935 5C               [ 1] 1308 	incw	x
      008936                       1309 00247$:
      008936 4F               [ 1] 1310 	clr	a
      008937 5D               [ 2] 1311 	tnzw	x
      008938 2A 01            [ 1] 1312 	jrpl	00248$
      00893A 4A               [ 1] 1313 	dec	a
      00893B                       1314 00248$:
      00893B 01               [ 1] 1315 	rrwa	x
      00893C 90 01            [ 1] 1316 	rrwa	y
      00893E 57               [ 2] 1317 	sraw	x
      00893F 90 56            [ 2] 1318 	rrcw	y
                                   1319 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 417: if (dn > 0) ss.n = (uint16_t)(ss.n + dn);
      008941 93               [ 1] 1320 	ldw	x, y
      008942 A3 00 00         [ 2] 1321 	cpw	x, #0x0000
      008945 2D 0B            [ 1] 1322 	jrsle	00111$
      008947 CE 01 59         [ 2] 1323 	ldw	x, _ss+9
      00894A 17 19            [ 2] 1324 	ldw	(0x19, sp), y
      00894C 72 FB 19         [ 2] 1325 	addw	x, (0x19, sp)
      00894F CF 01 59         [ 2] 1326 	ldw	_ss+9, x
      008952                       1327 00111$:
                                   1328 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 419: ss.y_prev = (uint32_t)y;
      008952 AE 01 54         [ 2] 1329 	ldw	x, #(_ss+4)
      008955 16 11            [ 2] 1330 	ldw	y, (0x11, sp)
      008957 EF 02            [ 2] 1331 	ldw	(0x2, x), y
      008959 16 0F            [ 2] 1332 	ldw	y, (0x0f, sp)
      00895B FF               [ 2] 1333 	ldw	(x), y
                                   1334 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 420: yfa = map_raw(scan_fa);
      00895C CE 00 09         [ 2] 1335 	ldw	x, _scan_fa+0
      00895F CD 84 E2         [ 4] 1336 	call	_map_raw
      008962 1F 19            [ 2] 1337 	ldw	(0x19, sp), x
      008964 17 17            [ 2] 1338 	ldw	(0x17, sp), y
                                   1339 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 421: yfb = map_raw(scan_fb);
      008966 CE 00 0B         [ 2] 1340 	ldw	x, _scan_fb+0
      008969 CD 84 E2         [ 4] 1341 	call	_map_raw
      00896C 17 11            [ 2] 1342 	ldw	(0x11, sp), y
                                   1343 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      00896E C6 01 5B         [ 1] 1344 	ld	a, _ss+11
                                   1345 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      008971 16 19            [ 2] 1346 	ldw	y, (0x19, sp)
      008973 17 15            [ 2] 1347 	ldw	(0x15, sp), y
                                   1348 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008975 1F 17            [ 2] 1349 	ldw	(0x17, sp), x
                                   1350 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      008977 4D               [ 1] 1351 	tnz	a
      008978 27 3D            [ 1] 1352 	jreq	00113$
      00897A CE 01 59         [ 2] 1353 	ldw	x, _ss+9
      00897D 1F 19            [ 2] 1354 	ldw	(0x19, sp), x
      00897F CE 01 5C         [ 2] 1355 	ldw	x, _ss+12
      008982 13 19            [ 2] 1356 	cpw	x, (0x19, sp)
      008984 26 31            [ 1] 1357 	jrne	00113$
                                   1358 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 423: base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
      008986 90 02            [ 1] 1359 	rlwa	y
      008988 9F               [ 1] 1360 	ld	a, xl
      008989 90 01            [ 1] 1361 	rrwa	y
      00898B 9E               [ 1] 1362 	ld	a, xh
      00898C 5F               [ 1] 1363 	clrw	x
      00898D 61               [ 1] 1364 	exg	a, yl
      00898E 4F               [ 1] 1365 	clr	a
      00898F 61               [ 1] 1366 	exg	a, yl
      008990 90 58            [ 2] 1367 	sllw	y
      008992 49               [ 1] 1368 	rlc	a
      008993 59               [ 2] 1369 	rlcw	x
      008994 72 A9 02 00      [ 2] 1370 	addw	y, #0x0200
      008998 A9 00            [ 1] 1371 	adc	a, #0x00
      00899A 01               [ 1] 1372 	rrwa	x
      00899B A9 00            [ 1] 1373 	adc	a, #0x00
                                   1374 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      00899D 17 19            [ 2] 1375 	ldw	(0x19, sp), y
      00899F 1E 15            [ 2] 1376 	ldw	x, (0x15, sp)
      0089A1 72 F0 19         [ 2] 1377 	subw	x, (0x19, sp)
      0089A4 CF 01 5E         [ 2] 1378 	ldw	_ss+14, x
                                   1379 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      0089A7 1E 17            [ 2] 1380 	ldw	x, (0x17, sp)
      0089A9 72 F0 19         [ 2] 1381 	subw	x, (0x19, sp)
      0089AC CF 01 60         [ 2] 1382 	ldw	_ss+16, x
                                   1383 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
      0089AF 55 00 0D 01 62   [ 1] 1384 	mov	_ss+18, _scan_sfa+0
                                   1385 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 427: continue;
      0089B4 CC 88 89         [ 2] 1386 	jp	00121$
      0089B7                       1387 00113$:
                                   1388 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 429: if (ss.pend) {
      0089B7 4D               [ 1] 1389 	tnz	a
      0089B8 26 03            [ 1] 1390 	jrne	00254$
      0089BA CC 8A 3B         [ 2] 1391 	jp	00118$
      0089BD                       1392 00254$:
                                   1393 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      0089BD CE 01 5C         [ 2] 1394 	ldw	x, _ss+12
      0089C0 16 01            [ 2] 1395 	ldw	y, (0x01, sp)
      0089C2 90 FF            [ 2] 1396 	ldw	(y), x
                                   1397 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      0089C4 CE 01 59         [ 2] 1398 	ldw	x, _ss+9
      0089C7 A3 00 D8         [ 2] 1399 	cpw	x, #0x00d8
      0089CA 24 04            [ 1] 1400 	jrnc	00128$
      0089CC 1F 19            [ 2] 1401 	ldw	(0x19, sp), x
      0089CE 20 05            [ 2] 1402 	jra	00129$
      0089D0                       1403 00128$:
      0089D0 AE 00 D8         [ 2] 1404 	ldw	x, #0x00d8
      0089D3 1F 19            [ 2] 1405 	ldw	(0x19, sp), x
      0089D5                       1406 00129$:
      0089D5 1E 03            [ 2] 1407 	ldw	x, (0x03, sp)
      0089D7 16 19            [ 2] 1408 	ldw	y, (0x19, sp)
      0089D9 FF               [ 2] 1409 	ldw	(x), y
                                   1410 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      0089DA CE 01 5E         [ 2] 1411 	ldw	x, _ss+14
      0089DD 16 05            [ 2] 1412 	ldw	y, (0x05, sp)
      0089DF 90 FF            [ 2] 1413 	ldw	(y), x
      0089E1 CE 01 60         [ 2] 1414 	ldw	x, _ss+16
      0089E4 16 07            [ 2] 1415 	ldw	y, (0x07, sp)
      0089E6 90 FF            [ 2] 1416 	ldw	(y), x
      0089E8 C6 01 62         [ 1] 1417 	ld	a, _ss+18
      0089EB 1E 09            [ 2] 1418 	ldw	x, (0x09, sp)
      0089ED F7               [ 1] 1419 	ld	(x), a
                                   1420 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 433: if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
      0089EE CE 01 59         [ 2] 1421 	ldw	x, _ss+9
      0089F1 1F 19            [ 2] 1422 	ldw	(0x19, sp), x
      0089F3 A3 00 D8         [ 2] 1423 	cpw	x, #0x00d8
      0089F6 25 0D            [ 1] 1424 	jrc	00116$
      0089F8 35 00 01 5B      [ 1] 1425 	mov	_ss+11, #0x00
      0089FC 35 01 01 63      [ 1] 1426 	mov	_ss+19, #0x01
      008A00 A6 01            [ 1] 1427 	ld	a, #0x01
      008A02 CC 8A B0         [ 2] 1428 	jp	00126$
      008A05                       1429 00116$:
                                   1430 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 434: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      008A05 16 19            [ 2] 1431 	ldw	y, (0x19, sp)
      008A07 5F               [ 1] 1432 	clrw	x
      008A08 4F               [ 1] 1433 	clr	a
      008A09 48               [ 1] 1434 	sll	a
      008A0A 90 59            [ 2] 1435 	rlcw	y
      008A0C 59               [ 2] 1436 	rlcw	x
      008A0D 6B 14            [ 1] 1437 	ld	(0x14, sp), a
      008A0F 72 A9 00 02      [ 2] 1438 	addw	y, #0x0002
      008A13 17 12            [ 2] 1439 	ldw	(0x12, sp), y
      008A15 4F               [ 1] 1440 	clr	a
      008A16 A9 00            [ 1] 1441 	adc	a, #0x00
                                   1442 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 435: ss.p_k0 = ss.n;
      008A18 AE 01 5C         [ 2] 1443 	ldw	x, #(_ss+12)
      008A1B 16 19            [ 2] 1444 	ldw	y, (0x19, sp)
      008A1D FF               [ 2] 1445 	ldw	(x), y
                                   1446 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 436: ss.p_u = (int16_t)(yfa - (int32_t)base);
      008A1E 16 13            [ 2] 1447 	ldw	y, (0x13, sp)
      008A20 17 19            [ 2] 1448 	ldw	(0x19, sp), y
      008A22 1E 15            [ 2] 1449 	ldw	x, (0x15, sp)
      008A24 72 F0 19         [ 2] 1450 	subw	x, (0x19, sp)
      008A27 CF 01 5E         [ 2] 1451 	ldw	_ss+14, x
                                   1452 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 437: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008A2A 1E 17            [ 2] 1453 	ldw	x, (0x17, sp)
      008A2C 72 F0 19         [ 2] 1454 	subw	x, (0x19, sp)
      008A2F CF 01 60         [ 2] 1455 	ldw	_ss+16, x
                                   1456 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 438: ss.p_fam = scan_sfa;
      008A32 55 00 0D 01 62   [ 1] 1457 	mov	_ss+18, _scan_sfa+0
                                   1458 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 439: return 1;
      008A37 A6 01            [ 1] 1459 	ld	a, #0x01
      008A39 20 75            [ 2] 1460 	jra	00126$
      008A3B                       1461 00118$:
                                   1462 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 441: if (ss.n >= NB) { ss.src_done = 1; break; }
      008A3B CE 01 59         [ 2] 1463 	ldw	x, _ss+9
      008A3E A3 00 D8         [ 2] 1464 	cpw	x, #0x00d8
      008A41 25 06            [ 1] 1465 	jrc	00120$
      008A43 35 01 01 63      [ 1] 1466 	mov	_ss+19, #0x01
      008A47 20 38            [ 2] 1467 	jra	00123$
      008A49                       1468 00120$:
                                   1469 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 442: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      008A49 90 5F            [ 1] 1470 	clrw	y
      008A4B 4F               [ 1] 1471 	clr	a
      008A4C 48               [ 1] 1472 	sll	a
      008A4D 59               [ 2] 1473 	rlcw	x
      008A4E 61               [ 1] 1474 	exg	a, yl
      008A4F 49               [ 1] 1475 	rlc	a
      008A50 61               [ 1] 1476 	exg	a, yl
      008A51 6B 14            [ 1] 1477 	ld	(0x14, sp), a
      008A53 1C 00 02         [ 2] 1478 	addw	x, #0x0002
      008A56 1F 12            [ 2] 1479 	ldw	(0x12, sp), x
      008A58 4F               [ 1] 1480 	clr	a
      008A59 A9 00            [ 1] 1481 	adc	a, #0x00
                                   1482 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 443: ss.pend = 1;
      008A5B 35 01 01 5B      [ 1] 1483 	mov	_ss+11, #0x01
                                   1484 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 444: ss.p_k0 = ss.n;
      008A5F CE 01 59         [ 2] 1485 	ldw	x, _ss+9
      008A62 CF 01 5C         [ 2] 1486 	ldw	_ss+12, x
                                   1487 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 445: ss.p_u = (int16_t)(yfa - (int32_t)base);
      008A65 16 13            [ 2] 1488 	ldw	y, (0x13, sp)
      008A67 17 19            [ 2] 1489 	ldw	(0x19, sp), y
      008A69 1E 15            [ 2] 1490 	ldw	x, (0x15, sp)
      008A6B 72 F0 19         [ 2] 1491 	subw	x, (0x19, sp)
      008A6E CF 01 5E         [ 2] 1492 	ldw	_ss+14, x
                                   1493 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 446: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008A71 1E 17            [ 2] 1494 	ldw	x, (0x17, sp)
      008A73 72 F0 19         [ 2] 1495 	subw	x, (0x19, sp)
      008A76 CF 01 60         [ 2] 1496 	ldw	_ss+16, x
                                   1497 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 447: ss.p_fam = scan_sfa;
      008A79 55 00 0D 01 62   [ 1] 1498 	mov	_ss+18, _scan_sfa+0
      008A7E CC 88 89         [ 2] 1499 	jp	00121$
      008A81                       1500 00123$:
                                   1501 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 449: if (ss.pend) {
      008A81 C6 01 5B         [ 1] 1502 	ld	a, _ss+11
      008A84 27 29            [ 1] 1503 	jreq	00125$
                                   1504 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 450: ss.pend = 0;
      008A86 35 00 01 5B      [ 1] 1505 	mov	_ss+11, #0x00
                                   1506 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 451: out->k0 = ss.p_k0; out->k1 = NB;
      008A8A CE 01 5C         [ 2] 1507 	ldw	x, _ss+12
      008A8D 16 01            [ 2] 1508 	ldw	y, (0x01, sp)
      008A8F 90 FF            [ 2] 1509 	ldw	(y), x
      008A91 1E 03            [ 2] 1510 	ldw	x, (0x03, sp)
      008A93 90 AE 00 D8      [ 2] 1511 	ldw	y, #0x00d8
      008A97 FF               [ 2] 1512 	ldw	(x), y
                                   1513 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 452: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      008A98 CE 01 5E         [ 2] 1514 	ldw	x, _ss+14
      008A9B 16 05            [ 2] 1515 	ldw	y, (0x05, sp)
      008A9D 90 FF            [ 2] 1516 	ldw	(y), x
      008A9F CE 01 60         [ 2] 1517 	ldw	x, _ss+16
      008AA2 16 07            [ 2] 1518 	ldw	y, (0x07, sp)
      008AA4 90 FF            [ 2] 1519 	ldw	(y), x
      008AA6 C6 01 62         [ 1] 1520 	ld	a, _ss+18
      008AA9 1E 09            [ 2] 1521 	ldw	x, (0x09, sp)
      008AAB F7               [ 1] 1522 	ld	(x), a
                                   1523 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 453: return 1;
      008AAC A6 01            [ 1] 1524 	ld	a, #0x01
                                   1525 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 455: return 0;
      008AAE 21                    1526 	.byte 0x21
      008AAF                       1527 00125$:
      008AAF 4F               [ 1] 1528 	clr	a
      008AB0                       1529 00126$:
                                   1530 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 456: }
      008AB0 5B 1C            [ 2] 1531 	addw	sp, #28
      008AB2 81               [ 4] 1532 	ret
                                   1533 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 460: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
                                   1534 ;	-----------------------------------------
                                   1535 ;	 function a_bounds
                                   1536 ;	-----------------------------------------
      008AB3                       1537 _a_bounds:
      008AB3 52 0C            [ 2] 1538 	sub	sp, #12
      008AB5 1F 09            [ 2] 1539 	ldw	(0x09, sp), x
                                   1540 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 462: uint16_t t, e = (k1 < NB) ? k1 : NB;
      008AB7 1E 0F            [ 2] 1541 	ldw	x, (0x0f, sp)
      008AB9 A3 00 D8         [ 2] 1542 	cpw	x, #0x00d8
      008ABC 25 03            [ 1] 1543 	jrc	00117$
      008ABE AE 00 D8         [ 2] 1544 	ldw	x, #0x00d8
      008AC1                       1545 00117$:
      008AC1 1F 01            [ 2] 1546 	ldw	(0x01, sp), x
                                   1547 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 463: *amin = 0;
      008AC3 16 11            [ 2] 1548 	ldw	y, (0x11, sp)
      008AC5 17 03            [ 2] 1549 	ldw	(0x03, sp), y
      008AC7 93               [ 1] 1550 	ldw	x, y
      008AC8 6F 01            [ 1] 1551 	clr	(0x1, x)
      008ACA 7F               [ 1] 1552 	clr	(x)
                                   1553 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 464: *amax = (int16_t)(k1 - k0);
      008ACB 16 13            [ 2] 1554 	ldw	y, (0x13, sp)
      008ACD 17 05            [ 2] 1555 	ldw	(0x05, sp), y
      008ACF 16 0F            [ 2] 1556 	ldw	y, (0x0f, sp)
      008AD1 72 F2 09         [ 2] 1557 	subw	y, (0x09, sp)
      008AD4 1E 05            [ 2] 1558 	ldw	x, (0x05, sp)
      008AD6 FF               [ 2] 1559 	ldw	(x), y
                                   1560 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      008AD7 16 09            [ 2] 1561 	ldw	y, (0x09, sp)
      008AD9 17 0B            [ 2] 1562 	ldw	(0x0b, sp), y
      008ADB                       1563 00112$:
                                   1564 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 466: int8_t kb = known_bit(t);
      008ADB 1E 0B            [ 2] 1565 	ldw	x, (0x0b, sp)
      008ADD 13 01            [ 2] 1566 	cpw	x, (0x01, sp)
      008ADF 24 35            [ 1] 1567 	jrnc	00114$
      008AE1 CD 81 C6         [ 4] 1568 	call	_known_bit
                                   1569 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      008AE4 1E 0B            [ 2] 1570 	ldw	x, (0x0b, sp)
      008AE6 72 F0 09         [ 2] 1571 	subw	x, (0x09, sp)
                                   1572 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 467: if (kb == 1) {
      008AE9 A1 01            [ 1] 1573 	cp	a, #0x01
      008AEB 26 11            [ 1] 1574 	jrne	00108$
                                   1575 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      008AED 5C               [ 1] 1576 	incw	x
                                   1577 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 469: if (m > *amin) *amin = m;
      008AEE 16 03            [ 2] 1578 	ldw	y, (0x03, sp)
      008AF0 90 FE            [ 2] 1579 	ldw	y, (y)
      008AF2 17 07            [ 2] 1580 	ldw	(0x07, sp), y
      008AF4 13 07            [ 2] 1581 	cpw	x, (0x07, sp)
      008AF6 2D 17            [ 1] 1582 	jrsle	00113$
      008AF8 16 03            [ 2] 1583 	ldw	y, (0x03, sp)
      008AFA 90 FF            [ 2] 1584 	ldw	(y), x
      008AFC 20 11            [ 2] 1585 	jra	00113$
      008AFE                       1586 00108$:
                                   1587 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 470: } else if (kb == 0) {
      008AFE 4D               [ 1] 1588 	tnz	a
      008AFF 26 0E            [ 1] 1589 	jrne	00113$
                                   1590 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 471: int16_t m = (int16_t)(t - k0);
                                   1591 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 472: if (m < *amax) *amax = m;
      008B01 16 05            [ 2] 1592 	ldw	y, (0x05, sp)
      008B03 90 FE            [ 2] 1593 	ldw	y, (y)
      008B05 17 07            [ 2] 1594 	ldw	(0x07, sp), y
      008B07 13 07            [ 2] 1595 	cpw	x, (0x07, sp)
      008B09 2E 04            [ 1] 1596 	jrsge	00113$
      008B0B 16 05            [ 2] 1597 	ldw	y, (0x05, sp)
      008B0D 90 FF            [ 2] 1598 	ldw	(y), x
      008B0F                       1599 00113$:
                                   1600 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      008B0F 1E 0B            [ 2] 1601 	ldw	x, (0x0b, sp)
      008B11 5C               [ 1] 1602 	incw	x
      008B12 1F 0B            [ 2] 1603 	ldw	(0x0b, sp), x
      008B14 20 C5            [ 2] 1604 	jra	00112$
      008B16                       1605 00114$:
                                   1606 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 475: }
      008B16 1E 0D            [ 2] 1607 	ldw	x, (13, sp)
      008B18 5B 14            [ 2] 1608 	addw	sp, #20
      008B1A FC               [ 2] 1609 	jp	(x)
                                   1610 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 479: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1611 ;	-----------------------------------------
                                   1612 ;	 function label_interval
                                   1613 ;	-----------------------------------------
      008B1B                       1614 _label_interval:
      008B1B 52 08            [ 2] 1615 	sub	sp, #8
                                   1616 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 482: int16_t L = (int16_t)(k1 - k0);
      008B1D 50               [ 2] 1617 	negw	x
      008B1E 72 FB 0B         [ 2] 1618 	addw	x, (0x0b, sp)
                                   1619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 485: if (a == 0) { off = 0; cls = 0; }
      008B21 16 11            [ 2] 1620 	ldw	y, (0x11, sp)
      008B23 26 08            [ 1] 1621 	jrne	00114$
      008B25 5F               [ 1] 1622 	clrw	x
      008B26 1F 07            [ 2] 1623 	ldw	(0x07, sp), x
      008B28 0F 06            [ 1] 1624 	clr	(0x06, sp)
      008B2A CC 8B B5         [ 2] 1625 	jp	00115$
      008B2D                       1626 00114$:
                                   1627 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 486: else if (a == L) { off = (int16_t)((L - 1) * BIT_U); cls = 1; }
      008B2D 13 11            [ 2] 1628 	cpw	x, (0x11, sp)
      008B2F 26 0C            [ 1] 1629 	jrne	00111$
      008B31 5A               [ 2] 1630 	decw	x
      008B32 4F               [ 1] 1631 	clr	a
      008B33 02               [ 1] 1632 	rlwa	x
      008B34 58               [ 2] 1633 	sllw	x
      008B35 1F 07            [ 2] 1634 	ldw	(0x07, sp), x
      008B37 A6 01            [ 1] 1635 	ld	a, #0x01
      008B39 6B 06            [ 1] 1636 	ld	(0x06, sp), a
      008B3B 20 78            [ 2] 1637 	jra	00115$
      008B3D                       1638 00111$:
                                   1639 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 488: mid = (int16_t)((u + v) >> 1);
      008B3D 16 0D            [ 2] 1640 	ldw	y, (0x0d, sp)
      008B3F 72 F9 0F         [ 2] 1641 	addw	y, (0x0f, sp)
      008B42 90 57            [ 2] 1642 	sraw	y
                                   1643 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 489: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
      008B44 1E 11            [ 2] 1644 	ldw	x, (0x11, sp)
      008B46 1F 07            [ 2] 1645 	ldw	(0x07, sp), x
      008B48 5A               [ 2] 1646 	decw	x
      008B49 41               [ 1] 1647 	exg	a, xl
      008B4A 6B 01            [ 1] 1648 	ld	(0x01, sp), a
      008B4C 41               [ 1] 1649 	exg	a, xl
      008B4D 0F 02            [ 1] 1650 	clr	(0x02, sp)
      008B4F 08 02            [ 1] 1651 	sll	(0x02, sp)
      008B51 09 01            [ 1] 1652 	rlc	(0x01, sp)
      008B53 1E 01            [ 2] 1653 	ldw	x, (0x01, sp)
      008B55 1C 01 34         [ 2] 1654 	addw	x, #0x0134
      008B58 1F 05            [ 2] 1655 	ldw	(0x05, sp), x
      008B5A 93               [ 1] 1656 	ldw	x, y
      008B5B 72 F0 05         [ 2] 1657 	subw	x, (0x05, sp)
                                   1658 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 490: if (d1 < 0) d1 = (int16_t)-d1;
      008B5E 1F 05            [ 2] 1659 	ldw	(0x05, sp), x
      008B60 5D               [ 2] 1660 	tnzw	x
      008B61 2A 07            [ 1] 1661 	jrpl	00102$
      008B63 00 06            [ 1] 1662 	neg	(0x06, sp)
      008B65 4F               [ 1] 1663 	clr	a
      008B66 12 05            [ 1] 1664 	sbc	a, (0x05, sp)
      008B68 6B 05            [ 1] 1665 	ld	(0x05, sp), a
      008B6A                       1666 00102$:
                                   1667 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 491: d0 = (int16_t)(mid - (a * BIT_U + H0P));
      008B6A 7B 08            [ 1] 1668 	ld	a, (0x08, sp)
      008B6C 6B 03            [ 1] 1669 	ld	(0x03, sp), a
      008B6E 0F 04            [ 1] 1670 	clr	(0x04, sp)
      008B70 08 04            [ 1] 1671 	sll	(0x04, sp)
      008B72 09 03            [ 1] 1672 	rlc	(0x03, sp)
      008B74 1E 03            [ 2] 1673 	ldw	x, (0x03, sp)
      008B76 1C 00 9A         [ 2] 1674 	addw	x, #0x009a
      008B79 1F 07            [ 2] 1675 	ldw	(0x07, sp), x
      008B7B 72 F2 07         [ 2] 1676 	subw	y, (0x07, sp)
                                   1677 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 492: if (d0 < 0) d0 = (int16_t)-d0;
      008B7E 17 07            [ 2] 1678 	ldw	(0x07, sp), y
      008B80 93               [ 1] 1679 	ldw	x, y
      008B81 5D               [ 2] 1680 	tnzw	x
      008B82 2A 07            [ 1] 1681 	jrpl	00104$
      008B84 00 08            [ 1] 1682 	neg	(0x08, sp)
      008B86 4F               [ 1] 1683 	clr	a
      008B87 12 07            [ 1] 1684 	sbc	a, (0x07, sp)
      008B89 6B 07            [ 1] 1685 	ld	(0x07, sp), a
      008B8B                       1686 00104$:
                                   1687 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 493: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
      008B8B 1E 07            [ 2] 1688 	ldw	x, (0x07, sp)
      008B8D 13 05            [ 2] 1689 	cpw	x, (0x05, sp)
      008B8F 2E 03            [ 1] 1690 	jrsge	00118$
      008B91 1E 07            [ 2] 1691 	ldw	x, (0x07, sp)
      008B93 C5                    1692 	.byte 0xc5
      008B94                       1693 00118$:
      008B94 1E 05            [ 2] 1694 	ldw	x, (0x05, sp)
      008B96                       1695 00119$:
      008B96 A3 00 F6         [ 2] 1696 	cpw	x, #0x00f6
      008B99 2D 04            [ 1] 1697 	jrsle	00106$
      008B9B A6 FF            [ 1] 1698 	ld	a, #0xff
      008B9D 20 28            [ 2] 1699 	jra	00116$
      008B9F                       1700 00106$:
                                   1701 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 494: if (d1 <= d0) { off = (int16_t)((a - 1) * BIT_U); cls = 1; }
      008B9F 1E 05            [ 2] 1702 	ldw	x, (0x05, sp)
      008BA1 13 07            [ 2] 1703 	cpw	x, (0x07, sp)
      008BA3 2C 0A            [ 1] 1704 	jrsgt	00108$
      008BA5 16 01            [ 2] 1705 	ldw	y, (0x01, sp)
      008BA7 17 07            [ 2] 1706 	ldw	(0x07, sp), y
      008BA9 A6 01            [ 1] 1707 	ld	a, #0x01
      008BAB 6B 06            [ 1] 1708 	ld	(0x06, sp), a
      008BAD 20 06            [ 2] 1709 	jra	00115$
      008BAF                       1710 00108$:
                                   1711 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 495: else          { off = (int16_t)(a * BIT_U);       cls = 0; }
      008BAF 16 03            [ 2] 1712 	ldw	y, (0x03, sp)
      008BB1 17 07            [ 2] 1713 	ldw	(0x07, sp), y
      008BB3 0F 06            [ 1] 1714 	clr	(0x06, sp)
      008BB5                       1715 00115$:
                                   1716 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 497: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      008BB5 1E 13            [ 2] 1717 	ldw	x, (0x13, sp)
      008BB7 16 0D            [ 2] 1718 	ldw	y, (0x0d, sp)
      008BB9 72 F2 07         [ 2] 1719 	subw	y, (0x07, sp)
      008BBC FF               [ 2] 1720 	ldw	(x), y
      008BBD 1E 15            [ 2] 1721 	ldw	x, (0x15, sp)
      008BBF 16 0F            [ 2] 1722 	ldw	y, (0x0f, sp)
      008BC1 72 F2 07         [ 2] 1723 	subw	y, (0x07, sp)
      008BC4 FF               [ 2] 1724 	ldw	(x), y
                                   1725 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 498: return cls;
      008BC5 7B 06            [ 1] 1726 	ld	a, (0x06, sp)
      008BC7                       1727 00116$:
                                   1728 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 499: }
      008BC7 1E 09            [ 2] 1729 	ldw	x, (9, sp)
      008BC9 5B 16            [ 2] 1730 	addw	sp, #22
      008BCB FC               [ 2] 1731 	jp	(x)
                                   1732 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 501: static void cal_cloud(int16_t u, uint8_t fam)
                                   1733 ;	-----------------------------------------
                                   1734 ;	 function cal_cloud
                                   1735 ;	-----------------------------------------
      008BCC                       1736 _cal_cloud:
      008BCC 89               [ 2] 1737 	pushw	x
                                   1738 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 505: if (fam != 5 && fam != 6) return;
      008BCD A1 05            [ 1] 1739 	cp	a, #0x05
      008BCF 27 04            [ 1] 1740 	jreq	00102$
      008BD1 A1 06            [ 1] 1741 	cp	a, #0x06
      008BD3 26 3C            [ 1] 1742 	jrne	00111$
      008BD5                       1743 00102$:
                                   1744 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 506: if (u < 0) return;
      008BD5 5D               [ 2] 1745 	tnzw	x
      008BD6 2B 39            [ 1] 1746 	jrmi	00111$
                                   1747 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 507: f = (uint8_t)(fam - 5);
      008BD8 A0 05            [ 1] 1748 	sub	a, #0x05
      008BDA 90 97            [ 1] 1749 	ld	yl, a
                                   1750 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 508: x = (int16_t)(u & (BIT_U - 1));
      008BDC 9E               [ 1] 1751 	ld	a, xh
      008BDD A4 01            [ 1] 1752 	and	a, #0x01
      008BDF 95               [ 1] 1753 	ld	xh, a
      008BE0 1F 01            [ 2] 1754 	ldw	(0x01, sp), x
                                   1755 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 509: d = (int16_t)(x - c_c0[f]);
      008BE2 93               [ 1] 1756 	ldw	x, y
      008BE3 4F               [ 1] 1757 	clr	a
      008BE4 95               [ 1] 1758 	ld	xh, a
      008BE5 58               [ 2] 1759 	sllw	x
      008BE6 DE 00 DC         [ 2] 1760 	ldw	x, (_c_c0+0, x)
      008BE9 50               [ 2] 1761 	negw	x
      008BEA 72 FB 01         [ 2] 1762 	addw	x, (0x01, sp)
                                   1763 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 510: if (d >= -EPS_HIST && d < EPS_HIST) {
      008BED A3 FF C0         [ 2] 1764 	cpw	x, #0xffc0
      008BF0 2F 1F            [ 1] 1765 	jrslt	00111$
      008BF2 A3 00 40         [ 2] 1766 	cpw	x, #0x0040
      008BF5 2E 1A            [ 1] 1767 	jrsge	00111$
                                   1768 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 511: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
      008BF7 1C 00 40         [ 2] 1769 	addw	x, #0x0040
      008BFA 57               [ 2] 1770 	sraw	x
                                   1771 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 512: if (c_hist[f][b] < 255) c_hist[f][b]++;
      008BFB A6 40            [ 1] 1772 	ld	a, #0x40
      008BFD 90 42            [ 4] 1773 	mul	y, a
      008BFF 72 A9 00 4C      [ 2] 1774 	addw	y, #(_c_hist+0)
      008C03 17 01            [ 2] 1775 	ldw	(0x01, sp), y
      008C05 4F               [ 1] 1776 	clr	a
      008C06 95               [ 1] 1777 	ld	xh, a
      008C07 72 FB 01         [ 2] 1778 	addw	x, (0x01, sp)
      008C0A F6               [ 1] 1779 	ld	a, (x)
      008C0B A1 FF            [ 1] 1780 	cp	a, #0xff
      008C0D 24 02            [ 1] 1781 	jrnc	00111$
      008C0F 4C               [ 1] 1782 	inc	a
      008C10 F7               [ 1] 1783 	ld	(x), a
      008C11                       1784 00111$:
                                   1785 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 514: }
      008C11 85               [ 2] 1786 	popw	x
      008C12 81               [ 4] 1787 	ret
                                   1788 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 516: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1789 ;	-----------------------------------------
                                   1790 ;	 function cal_add
                                   1791 ;	-----------------------------------------
      008C13                       1792 _cal_add:
      008C13 52 0A            [ 2] 1793 	sub	sp, #10
      008C15 51               [ 1] 1794 	exgw	x, y
                                   1795 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 520: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
      008C16 96               [ 1] 1796 	ldw	x, sp
      008C17 1C 00 03         [ 2] 1797 	addw	x, #3
      008C1A 89               [ 2] 1798 	pushw	x
      008C1B 96               [ 1] 1799 	ldw	x, sp
      008C1C 1C 00 03         [ 2] 1800 	addw	x, #3
      008C1F 89               [ 2] 1801 	pushw	x
      008C20 1E 18            [ 2] 1802 	ldw	x, (0x18, sp)
      008C22 89               [ 2] 1803 	pushw	x
      008C23 1E 17            [ 2] 1804 	ldw	x, (0x17, sp)
      008C25 89               [ 2] 1805 	pushw	x
      008C26 1E 17            [ 2] 1806 	ldw	x, (0x17, sp)
      008C28 89               [ 2] 1807 	pushw	x
      008C29 1E 17            [ 2] 1808 	ldw	x, (0x17, sp)
      008C2B 89               [ 2] 1809 	pushw	x
      008C2C 93               [ 1] 1810 	ldw	x, y
      008C2D CD 8B 1B         [ 4] 1811 	call	_label_interval
                                   1812 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 521: if (cls < 0) return;
      008C30 6B 08            [ 1] 1813 	ld	(0x08, sp), a
      008C32 2A 03            [ 1] 1814 	jrpl	00102$
      008C34 CC 8D 08         [ 2] 1815 	jp	00129$
      008C37                       1816 00102$:
                                   1817 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 523: uint8_t ci = (uint8_t)cls;
      008C37 7B 08            [ 1] 1818 	ld	a, (0x08, sp)
                                   1819 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 524: if (lo > c_lo[ci]) c_lo[ci] = lo;
      008C39 5F               [ 1] 1820 	clrw	x
      008C3A 97               [ 1] 1821 	ld	xl, a
      008C3B 58               [ 2] 1822 	sllw	x
      008C3C 1F 09            [ 2] 1823 	ldw	(0x09, sp), x
      008C3E 90 93            [ 1] 1824 	ldw	y, x
      008C40 72 A9 00 3C      [ 2] 1825 	addw	y, #(_c_lo+0)
      008C44 93               [ 1] 1826 	ldw	x, y
      008C45 FE               [ 2] 1827 	ldw	x, (x)
      008C46 13 01            [ 2] 1828 	cpw	x, (0x01, sp)
      008C48 2E 04            [ 1] 1829 	jrsge	00104$
      008C4A 93               [ 1] 1830 	ldw	x, y
      008C4B 16 01            [ 2] 1831 	ldw	y, (0x01, sp)
      008C4D FF               [ 2] 1832 	ldw	(x), y
      008C4E                       1833 00104$:
                                   1834 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 525: if (hi < c_hi[ci]) c_hi[ci] = hi;
      008C4E 16 09            [ 2] 1835 	ldw	y, (0x09, sp)
      008C50 72 A9 00 40      [ 2] 1836 	addw	y, #(_c_hi+0)
      008C54 93               [ 1] 1837 	ldw	x, y
      008C55 FE               [ 2] 1838 	ldw	x, (x)
      008C56 1F 09            [ 2] 1839 	ldw	(0x09, sp), x
      008C58 1E 03            [ 2] 1840 	ldw	x, (0x03, sp)
      008C5A 13 09            [ 2] 1841 	cpw	x, (0x09, sp)
      008C5C 2E 04            [ 1] 1842 	jrsge	00106$
      008C5E 93               [ 1] 1843 	ldw	x, y
      008C5F 16 03            [ 2] 1844 	ldw	y, (0x03, sp)
      008C61 FF               [ 2] 1845 	ldw	(x), y
      008C62                       1846 00106$:
                                   1847 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 526: if (c_n[ci] < 255) c_n[ci]++;
      008C62 5F               [ 1] 1848 	clrw	x
      008C63 97               [ 1] 1849 	ld	xl, a
      008C64 1C 00 44         [ 2] 1850 	addw	x, #(_c_n+0)
      008C67 F6               [ 1] 1851 	ld	a, (x)
      008C68 A1 FF            [ 1] 1852 	cp	a, #0xff
      008C6A 24 02            [ 1] 1853 	jrnc	00108$
      008C6C 4C               [ 1] 1854 	inc	a
      008C6D F7               [ 1] 1855 	ld	(x), a
      008C6E                       1856 00108$:
                                   1857 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if ((fam == 5 || fam == 6) && lo >= 0) {
      008C6E 7B 13            [ 1] 1858 	ld	a, (0x13, sp)
      008C70 A1 05            [ 1] 1859 	cp	a, #0x05
      008C72 27 09            [ 1] 1860 	jreq	00128$
      008C74 7B 13            [ 1] 1861 	ld	a, (0x13, sp)
      008C76 A1 06            [ 1] 1862 	cp	a, #0x06
      008C78 27 03            [ 1] 1863 	jreq	00244$
      008C7A CC 8D 08         [ 2] 1864 	jp	00129$
      008C7D                       1865 00244$:
      008C7D                       1866 00128$:
      008C7D 1E 01            [ 2] 1867 	ldw	x, (0x01, sp)
      008C7F 2A 03            [ 1] 1868 	jrpl	00245$
      008C81 CC 8D 08         [ 2] 1869 	jp	00129$
      008C84                       1870 00245$:
                                   1871 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: uint8_t f = (uint8_t)(fam - 5);
      008C84 7B 13            [ 1] 1872 	ld	a, (0x13, sp)
      008C86 A0 05            [ 1] 1873 	sub	a, #0x05
                                   1874 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 530: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
      008C88 88               [ 1] 1875 	push	a
      008C89 41               [ 1] 1876 	exg	a, xl
      008C8A 6B 08            [ 1] 1877 	ld	(0x08, sp), a
      008C8C 41               [ 1] 1878 	exg	a, xl
      008C8D 9E               [ 1] 1879 	ld	a, xh
      008C8E A4 01            [ 1] 1880 	and	a, #0x01
      008C90 6B 07            [ 1] 1881 	ld	(0x07, sp), a
      008C92 84               [ 1] 1882 	pop	a
      008C93 5F               [ 1] 1883 	clrw	x
      008C94 97               [ 1] 1884 	ld	xl, a
      008C95 58               [ 2] 1885 	sllw	x
      008C96 90 93            [ 1] 1886 	ldw	y, x
      008C98 DE 00 DC         [ 2] 1887 	ldw	x, (_c_c0+0, x)
      008C9B 1F 09            [ 2] 1888 	ldw	(0x09, sp), x
      008C9D 1E 06            [ 2] 1889 	ldw	x, (0x06, sp)
      008C9F 72 F0 09         [ 2] 1890 	subw	x, (0x09, sp)
                                   1891 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 531: if (d >= -EPS_HIST && d < EPS_HIST) {
      008CA2 1F 05            [ 2] 1892 	ldw	(0x05, sp), x
      008CA4 A3 FF C0         [ 2] 1893 	cpw	x, #0xffc0
      008CA7 2F 5F            [ 1] 1894 	jrslt	00129$
      008CA9 1E 05            [ 2] 1895 	ldw	x, (0x05, sp)
      008CAB A3 00 40         [ 2] 1896 	cpw	x, #0x0040
      008CAE 2E 58            [ 1] 1897 	jrsge	00129$
                                   1898 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 532: if (cls == 0) {
      008CB0 0D 08            [ 1] 1899 	tnz	(0x08, sp)
      008CB2 26 26            [ 1] 1900 	jrne	00120$
                                   1901 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 533: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
      008CB4 93               [ 1] 1902 	ldw	x, y
      008CB5 1C 00 CC         [ 2] 1903 	addw	x, #(_c_labx0+0)
      008CB8 1F 09            [ 2] 1904 	ldw	(0x09, sp), x
      008CBA FE               [ 2] 1905 	ldw	x, (x)
      008CBB 13 05            [ 2] 1906 	cpw	x, (0x05, sp)
      008CBD 2E 0B            [ 1] 1907 	jrsge	00112$
      008CBF 90 DF 00 D4      [ 2] 1908 	ldw	((_c_labx0b+0), y), x
      008CC3 1E 09            [ 2] 1909 	ldw	x, (0x09, sp)
      008CC5 16 05            [ 2] 1910 	ldw	y, (0x05, sp)
      008CC7 FF               [ 2] 1911 	ldw	(x), y
      008CC8 20 3E            [ 2] 1912 	jra	00129$
      008CCA                       1913 00112$:
                                   1914 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 534: else if (d > c_labx0b[f]) c_labx0b[f] = d;
      008CCA 72 A9 00 D4      [ 2] 1915 	addw	y, #(_c_labx0b+0)
      008CCE 93               [ 1] 1916 	ldw	x, y
      008CCF FE               [ 2] 1917 	ldw	x, (x)
      008CD0 13 05            [ 2] 1918 	cpw	x, (0x05, sp)
      008CD2 2E 34            [ 1] 1919 	jrsge	00129$
      008CD4 93               [ 1] 1920 	ldw	x, y
      008CD5 16 05            [ 2] 1921 	ldw	y, (0x05, sp)
      008CD7 FF               [ 2] 1922 	ldw	(x), y
      008CD8 20 2E            [ 2] 1923 	jra	00129$
      008CDA                       1924 00120$:
                                   1925 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 536: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
      008CDA 93               [ 1] 1926 	ldw	x, y
      008CDB 1C 00 D0         [ 2] 1927 	addw	x, #(_c_labx1+0)
      008CDE 1F 07            [ 2] 1928 	ldw	(0x07, sp), x
      008CE0 FE               [ 2] 1929 	ldw	x, (x)
      008CE1 1F 09            [ 2] 1930 	ldw	(0x09, sp), x
      008CE3 1E 05            [ 2] 1931 	ldw	x, (0x05, sp)
      008CE5 13 09            [ 2] 1932 	cpw	x, (0x09, sp)
      008CE7 2E 0D            [ 1] 1933 	jrsge	00117$
      008CE9 93               [ 1] 1934 	ldw	x, y
      008CEA 16 09            [ 2] 1935 	ldw	y, (0x09, sp)
      008CEC DF 00 D8         [ 2] 1936 	ldw	((_c_labx1b+0), x), y
      008CEF 1E 07            [ 2] 1937 	ldw	x, (0x07, sp)
      008CF1 16 05            [ 2] 1938 	ldw	y, (0x05, sp)
      008CF3 FF               [ 2] 1939 	ldw	(x), y
      008CF4 20 12            [ 2] 1940 	jra	00129$
      008CF6                       1941 00117$:
                                   1942 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 537: else if (d < c_labx1b[f]) c_labx1b[f] = d;
      008CF6 72 A9 00 D8      [ 2] 1943 	addw	y, #(_c_labx1b+0)
      008CFA 93               [ 1] 1944 	ldw	x, y
      008CFB FE               [ 2] 1945 	ldw	x, (x)
      008CFC 1F 09            [ 2] 1946 	ldw	(0x09, sp), x
      008CFE 1E 05            [ 2] 1947 	ldw	x, (0x05, sp)
      008D00 13 09            [ 2] 1948 	cpw	x, (0x09, sp)
      008D02 2E 04            [ 1] 1949 	jrsge	00129$
      008D04 93               [ 1] 1950 	ldw	x, y
      008D05 16 05            [ 2] 1951 	ldw	y, (0x05, sp)
      008D07 FF               [ 2] 1952 	ldw	(x), y
      008D08                       1953 00129$:
                                   1954 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 541: }
      008D08 1E 0B            [ 2] 1955 	ldw	x, (11, sp)
      008D0A 5B 15            [ 2] 1956 	addw	sp, #21
      008D0C FC               [ 2] 1957 	jp	(x)
                                   1958 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 544: static uint8_t theta56(uint8_t f, int16_t *theta_out)
                                   1959 ;	-----------------------------------------
                                   1960 ;	 function theta56
                                   1961 ;	-----------------------------------------
      008D0D                       1962 _theta56:
      008D0D 52 28            [ 2] 1963 	sub	sp, #40
      008D0F 1F 25            [ 2] 1964 	ldw	(0x25, sp), x
                                   1965 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 546: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
      008D11 5F               [ 1] 1966 	clrw	x
      008D12 97               [ 1] 1967 	ld	xl, a
      008D13 58               [ 2] 1968 	sllw	x
      008D14 1F 05            [ 2] 1969 	ldw	(0x05, sp), x
      008D16 DE 00 CC         [ 2] 1970 	ldw	x, (_c_labx0+0, x)
      008D19 16 05            [ 2] 1971 	ldw	y, (0x05, sp)
      008D1B 90 DE 00 D0      [ 2] 1972 	ldw	y, (_c_labx1+0, y)
                                   1973 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 547: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
      008D1F 1F 07            [ 2] 1974 	ldw	(0x07, sp), x
      008D21 A3 C0 00         [ 2] 1975 	cpw	x, #0xc000
      008D24 2C 04            [ 1] 1976 	jrsgt	00483$
      008D26 0F 09            [ 1] 1977 	clr	(0x09, sp)
      008D28 20 06            [ 2] 1978 	jra	00484$
      008D2A                       1979 00483$:
      008D2A 88               [ 1] 1980 	push	a
      008D2B A6 01            [ 1] 1981 	ld	a, #0x01
      008D2D 6B 0A            [ 1] 1982 	ld	(0x0a, sp), a
      008D2F 84               [ 1] 1983 	pop	a
      008D30                       1984 00484$:
      008D30 17 0A            [ 2] 1985 	ldw	(0x0a, sp), y
      008D32 93               [ 1] 1986 	ldw	x, y
      008D33 A3 3F FF         [ 2] 1987 	cpw	x, #0x3fff
      008D36 2F 04            [ 1] 1988 	jrslt	00485$
      008D38 0F 0C            [ 1] 1989 	clr	(0x0c, sp)
      008D3A 20 06            [ 2] 1990 	jra	00486$
      008D3C                       1991 00485$:
      008D3C 88               [ 1] 1992 	push	a
      008D3D A6 01            [ 1] 1993 	ld	a, #0x01
      008D3F 6B 0D            [ 1] 1994 	ld	(0x0d, sp), a
      008D41 84               [ 1] 1995 	pop	a
      008D42                       1996 00486$:
                                   1997 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 548: int16_t zlo = (int16_t)(x0 + 1);
      008D42 1E 07            [ 2] 1998 	ldw	x, (0x07, sp)
      008D44 5C               [ 1] 1999 	incw	x
      008D45 1F 0D            [ 2] 2000 	ldw	(0x0d, sp), x
                                   2001 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 549: int16_t zhi = x1;
      008D47 17 0F            [ 2] 2002 	ldw	(0x0f, sp), y
                                   2003 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 550: int16_t theta = 0;
      008D49 5F               [ 1] 2004 	clrw	x
      008D4A 1F 11            [ 2] 2005 	ldw	(0x11, sp), x
                                   2006 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 551: uint8_t have_theta = 0;
      008D4C 0F 13            [ 1] 2007 	clr	(0x13, sp)
                                   2008 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 552: int16_t top = 0;
      008D4E 5F               [ 1] 2009 	clrw	x
      008D4F 1F 14            [ 2] 2010 	ldw	(0x14, sp), x
                                   2011 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 553: uint8_t have_top = 0, clear1 = 0;
      008D51 0F 16            [ 1] 2012 	clr	(0x16, sp)
      008D53 0F 17            [ 1] 2013 	clr	(0x17, sp)
                                   2014 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 555: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
      008D55 AE FF E0         [ 2] 2015 	ldw	x, #0xffe0
      008D58 13 0D            [ 2] 2016 	cpw	x, (0x0d, sp)
      008D5A 2F 02            [ 1] 2017 	jrslt	00102$
      008D5C 1F 0D            [ 2] 2018 	ldw	(0x0d, sp), x
      008D5E                       2019 00102$:
                                   2020 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 556: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
      008D5E 1E 0F            [ 2] 2021 	ldw	x, (0x0f, sp)
      008D60 A3 00 20         [ 2] 2022 	cpw	x, #0x0020
      008D63 2D 05            [ 1] 2023 	jrsle	00104$
      008D65 AE 00 20         [ 2] 2024 	ldw	x, #0x0020
      008D68 1F 0F            [ 2] 2025 	ldw	(0x0f, sp), x
      008D6A                       2026 00104$:
                                   2027 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008D6A 41               [ 1] 2028 	exg	a, xl
      008D6B A6 40            [ 1] 2029 	ld	a, #0x40
      008D6D 41               [ 1] 2030 	exg	a, xl
      008D6E 42               [ 4] 2031 	mul	x, a
      008D6F 1F 18            [ 2] 2032 	ldw	(0x18, sp), x
                                   2033 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 557: if (zlo < zhi) {
      008D71 1E 0D            [ 2] 2034 	ldw	x, (0x0d, sp)
      008D73 13 0F            [ 2] 2035 	cpw	x, (0x0f, sp)
      008D75 2F 03            [ 1] 2036 	jrslt	00489$
      008D77 CC 8E 7F         [ 2] 2037 	jp	00126$
      008D7A                       2038 00489$:
                                   2039 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 558: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
      008D7A 1E 0D            [ 2] 2040 	ldw	x, (0x0d, sp)
      008D7C 1C 00 40         [ 2] 2041 	addw	x, #0x0040
      008D7F 57               [ 2] 2042 	sraw	x
      008D80 41               [ 1] 2043 	exg	a, xl
      008D81 6B 27            [ 1] 2044 	ld	(0x27, sp), a
      008D83 41               [ 1] 2045 	exg	a, xl
                                   2046 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 559: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
      008D84 1E 0F            [ 2] 2047 	ldw	x, (0x0f, sp)
      008D86 1C 00 3F         [ 2] 2048 	addw	x, #0x003f
      008D89 57               [ 2] 2049 	sraw	x
      008D8A 41               [ 1] 2050 	exg	a, xl
      008D8B 6B 1A            [ 1] 2051 	ld	(0x1a, sp), a
      008D8D 41               [ 1] 2052 	exg	a, xl
                                   2053 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 560: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
      008D8E 16 0D            [ 2] 2054 	ldw	y, (0x0d, sp)
      008D90 17 1B            [ 2] 2055 	ldw	(0x1b, sp), y
      008D92 5F               [ 1] 2056 	clrw	x
      008D93 1F 1D            [ 2] 2057 	ldw	(0x1d, sp), x
      008D95 5F               [ 1] 2058 	clrw	x
      008D96 1F 1F            [ 2] 2059 	ldw	(0x1f, sp), x
      008D98 5F               [ 1] 2060 	clrw	x
      008D99 5A               [ 2] 2061 	decw	x
      008D9A 1F 21            [ 2] 2062 	ldw	(0x21, sp), x
                                   2063 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008D9C 1E 18            [ 2] 2064 	ldw	x, (0x18, sp)
      008D9E 1C 00 4C         [ 2] 2065 	addw	x, #(_c_hist+0)
      008DA1 1F 23            [ 2] 2066 	ldw	(0x23, sp), x
      008DA3 0F 28            [ 1] 2067 	clr	(0x28, sp)
      008DA5                       2068 00170$:
      008DA5 7B 27            [ 1] 2069 	ld	a, (0x27, sp)
      008DA7 11 1A            [ 1] 2070 	cp	a, (0x1a, sp)
      008DA9 22 2B            [ 1] 2071 	jrugt	00253$
                                   2072 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 563: if (c_hist[f][b]) {
      008DAB 5F               [ 1] 2073 	clrw	x
      008DAC 7B 27            [ 1] 2074 	ld	a, (0x27, sp)
      008DAE 97               [ 1] 2075 	ld	xl, a
      008DAF 72 FB 23         [ 2] 2076 	addw	x, (0x23, sp)
      008DB2 F6               [ 1] 2077 	ld	a, (x)
      008DB3 27 1D            [ 1] 2078 	jreq	00171$
                                   2079 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 564: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008DB5 7B 27            [ 1] 2080 	ld	a, (0x27, sp)
      008DB7 5F               [ 1] 2081 	clrw	x
      008DB8 97               [ 1] 2082 	ld	xl, a
      008DB9 58               [ 2] 2083 	sllw	x
      008DBA 1C FF C1         [ 2] 2084 	addw	x, #0xffc1
                                   2085 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 565: int16_t gp = (int16_t)(x - prev);
      008DBD 90 93            [ 1] 2086 	ldw	y, x
      008DBF 72 F0 1B         [ 2] 2087 	subw	x, (0x1b, sp)
                                   2088 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 566: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
      008DC2 13 21            [ 2] 2089 	cpw	x, (0x21, sp)
      008DC4 2D 08            [ 1] 2090 	jrsle	00106$
      008DC6 1F 21            [ 2] 2091 	ldw	(0x21, sp), x
      008DC8 1E 1B            [ 2] 2092 	ldw	x, (0x1b, sp)
      008DCA 1F 1D            [ 2] 2093 	ldw	(0x1d, sp), x
      008DCC 17 1F            [ 2] 2094 	ldw	(0x1f, sp), y
      008DCE                       2095 00106$:
                                   2096 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 567: prev = x;
      008DCE 17 1B            [ 2] 2097 	ldw	(0x1b, sp), y
                                   2098 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 568: nocc++;
      008DD0 0C 28            [ 1] 2099 	inc	(0x28, sp)
      008DD2                       2100 00171$:
                                   2101 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
      008DD2 0C 27            [ 1] 2102 	inc	(0x27, sp)
      008DD4 20 CF            [ 2] 2103 	jra	00170$
      008DD6                       2104 00253$:
                                   2105 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 572: int16_t gp = (int16_t)(zhi - prev);
      008DD6 1E 0F            [ 2] 2106 	ldw	x, (0x0f, sp)
      008DD8 72 F0 1B         [ 2] 2107 	subw	x, (0x1b, sp)
                                   2108 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 573: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
      008DDB 13 21            [ 2] 2109 	cpw	x, (0x21, sp)
      008DDD 2D 0A            [ 1] 2110 	jrsle	00111$
      008DDF 1F 21            [ 2] 2111 	ldw	(0x21, sp), x
      008DE1 16 1B            [ 2] 2112 	ldw	y, (0x1b, sp)
      008DE3 17 1D            [ 2] 2113 	ldw	(0x1d, sp), y
      008DE5 16 0F            [ 2] 2114 	ldw	y, (0x0f, sp)
      008DE7 17 1F            [ 2] 2115 	ldw	(0x1f, sp), y
      008DE9                       2116 00111$:
                                   2117 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 575: if (nocc == 0) {
      008DE9 0D 28            [ 1] 2118 	tnz	(0x28, sp)
      008DEB 26 1C            [ 1] 2119 	jrne	00123$
                                   2120 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 576: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
      008DED 0D 09            [ 1] 2121 	tnz	(0x09, sp)
      008DEF 26 03            [ 1] 2122 	jrne	00495$
      008DF1 CC 8E 7F         [ 2] 2123 	jp	00126$
      008DF4                       2124 00495$:
      008DF4 0D 0C            [ 1] 2125 	tnz	(0x0c, sp)
      008DF6 26 03            [ 1] 2126 	jrne	00496$
      008DF8 CC 8E 7F         [ 2] 2127 	jp	00126$
      008DFB                       2128 00496$:
      008DFB 1E 0D            [ 2] 2129 	ldw	x, (0x0d, sp)
      008DFD 72 FB 0F         [ 2] 2130 	addw	x, (0x0f, sp)
      008E00 57               [ 2] 2131 	sraw	x
      008E01 1F 11            [ 2] 2132 	ldw	(0x11, sp), x
      008E03 A6 01            [ 1] 2133 	ld	a, #0x01
      008E05 6B 13            [ 1] 2134 	ld	(0x13, sp), a
      008E07 20 76            [ 2] 2135 	jra	00126$
      008E09                       2136 00123$:
                                   2137 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 578: uint8_t ok = (bg >= EPS_GAP_MIN);
      008E09 1E 21            [ 2] 2138 	ldw	x, (0x21, sp)
      008E0B A3 00 05         [ 2] 2139 	cpw	x, #0x0005
      008E0E 2F 02            [ 1] 2140 	jrslt	00497$
      008E10 4F               [ 1] 2141 	clr	a
      008E11 C5                    2142 	.byte 0xc5
      008E12                       2143 00497$:
      008E12 A6 01            [ 1] 2144 	ld	a, #0x01
      008E14                       2145 00498$:
      008E14 A8 01            [ 1] 2146 	xor	a, #0x01
                                   2147 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 579: if (ok && (uint8_t)(nocc + 1) >= 4) {
      008E16 6B 27            [ 1] 2148 	ld	(0x27, sp), a
      008E18 27 55            [ 1] 2149 	jreq	00118$
      008E1A 7B 28            [ 1] 2150 	ld	a, (0x28, sp)
      008E1C 4C               [ 1] 2151 	inc	a
      008E1D A1 04            [ 1] 2152 	cp	a, #0x04
      008E1F 25 4E            [ 1] 2153 	jrc	00118$
                                   2154 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 580: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
      008E21 16 21            [ 2] 2155 	ldw	y, (0x21, sp)
      008E23 5F               [ 1] 2156 	clrw	x
      008E24 90 5D            [ 2] 2157 	tnzw	y
      008E26 2A 01            [ 1] 2158 	jrpl	00501$
      008E28 5A               [ 2] 2159 	decw	x
      008E29                       2160 00501$:
      008E29 90 58            [ 2] 2161 	sllw	y
      008E2B 59               [ 2] 2162 	rlcw	x
      008E2C 1F 21            [ 2] 2163 	ldw	(0x21, sp), x
      008E2E 7B 28            [ 1] 2164 	ld	a, (0x28, sp)
      008E30 5F               [ 1] 2165 	clrw	x
      008E31 97               [ 1] 2166 	ld	xl, a
      008E32 5C               [ 1] 2167 	incw	x
      008E33 9E               [ 1] 2168 	ld	a, xh
      008E34 49               [ 1] 2169 	rlc	a
      008E35 4F               [ 1] 2170 	clr	a
      008E36 A2 00            [ 1] 2171 	sbc	a, #0x00
      008E38 6B 02            [ 1] 2172 	ld	(0x02, sp), a
      008E3A 6B 01            [ 1] 2173 	ld	(0x01, sp), a
      008E3C 89               [ 2] 2174 	pushw	x
      008E3D 1E 03            [ 2] 2175 	ldw	x, (0x03, sp)
      008E3F 89               [ 2] 2176 	pushw	x
      008E40 90 89            [ 2] 2177 	pushw	y
      008E42 1E 27            [ 2] 2178 	ldw	x, (0x27, sp)
      008E44 89               [ 2] 2179 	pushw	x
      008E45 CD 9D 12         [ 4] 2180 	call	__mullong
      008E48 5B 08            [ 2] 2181 	addw	sp, #8
      008E4A 17 21            [ 2] 2182 	ldw	(0x21, sp), y
      008E4C 16 0F            [ 2] 2183 	ldw	y, (0x0f, sp)
      008E4E 72 F2 0D         [ 2] 2184 	subw	y, (0x0d, sp)
      008E51 89               [ 2] 2185 	pushw	x
      008E52 90 89            [ 2] 2186 	pushw	y
      008E54 AE 00 05         [ 2] 2187 	ldw	x, #0x0005
      008E57 CD 9C 3D         [ 4] 2188 	call	___mulsint2slong
      008E5A 5B 02            [ 2] 2189 	addw	sp, #2
      008E5C 1F 11            [ 2] 2190 	ldw	(0x11, sp), x
      008E5E 17 0F            [ 2] 2191 	ldw	(0x0f, sp), y
      008E60 85               [ 2] 2192 	popw	x
      008E61 13 0F            [ 2] 2193 	cpw	x, (0x0f, sp)
      008E63 7B 22            [ 1] 2194 	ld	a, (0x22, sp)
      008E65 12 0E            [ 1] 2195 	sbc	a, (0x0e, sp)
      008E67 7B 21            [ 1] 2196 	ld	a, (0x21, sp)
      008E69 12 0D            [ 1] 2197 	sbc	a, (0x0d, sp)
      008E6B 2E 02            [ 1] 2198 	jrsge	00118$
                                   2199 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 581: ok = 0;
      008E6D 0F 27            [ 1] 2200 	clr	(0x27, sp)
      008E6F                       2201 00118$:
                                   2202 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 583: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
      008E6F 0D 27            [ 1] 2203 	tnz	(0x27, sp)
      008E71 27 0C            [ 1] 2204 	jreq	00126$
      008E73 1E 1D            [ 2] 2205 	ldw	x, (0x1d, sp)
      008E75 72 FB 1F         [ 2] 2206 	addw	x, (0x1f, sp)
      008E78 57               [ 2] 2207 	sraw	x
      008E79 1F 11            [ 2] 2208 	ldw	(0x11, sp), x
      008E7B A6 01            [ 1] 2209 	ld	a, #0x01
      008E7D 6B 13            [ 1] 2210 	ld	(0x13, sp), a
      008E7F                       2211 00126$:
                                   2212 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 586: if (has0 || has1) {
      008E7F 0D 09            [ 1] 2213 	tnz	(0x09, sp)
      008E81 26 04            [ 1] 2214 	jrne	00144$
      008E83 0D 0C            [ 1] 2215 	tnz	(0x0c, sp)
      008E85 27 77            [ 1] 2216 	jreq	00245$
      008E87                       2217 00144$:
                                   2218 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 587: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
      008E87 AE FF E0         [ 2] 2219 	ldw	x, #0xffe0
      008E8A 1F 23            [ 2] 2220 	ldw	(0x23, sp), x
      008E8C AE 00 20         [ 2] 2221 	ldw	x, #0x0020
      008E8F 1F 27            [ 2] 2222 	ldw	(0x27, sp), x
                                   2223 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 588: if (has0) {
      008E91 0D 09            [ 1] 2224 	tnz	(0x09, sp)
      008E93 27 19            [ 1] 2225 	jreq	00131$
                                   2226 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 589: wlo = (int16_t)(x0 - EPS_SLACK1);
      008E95 1E 07            [ 2] 2227 	ldw	x, (0x07, sp)
      008E97 1D 00 08         [ 2] 2228 	subw	x, #0x0008
      008E9A 1F 23            [ 2] 2229 	ldw	(0x23, sp), x
                                   2230 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 590: if (c_labx0b[f] > -0x4000 &&
      008E9C 1E 05            [ 2] 2231 	ldw	x, (0x05, sp)
      008E9E DE 00 D4         [ 2] 2232 	ldw	x, (_c_labx0b+0, x)
      008EA1 A3 C0 00         [ 2] 2233 	cpw	x, #0xc000
      008EA4 2D 08            [ 1] 2234 	jrsle	00131$
                                   2235 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 591: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
      008EA6 5A               [ 2] 2236 	decw	x
      008EA7 5A               [ 2] 2237 	decw	x
      008EA8 13 23            [ 2] 2238 	cpw	x, (0x23, sp)
      008EAA 2D 02            [ 1] 2239 	jrsle	00131$
                                   2240 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 592: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
      008EAC 1F 23            [ 2] 2241 	ldw	(0x23, sp), x
      008EAE                       2242 00131$:
                                   2243 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 594: if (has1) {
      008EAE 0D 0C            [ 1] 2244 	tnz	(0x0c, sp)
      008EB0 27 19            [ 1] 2245 	jreq	00136$
                                   2246 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 595: whi = (int16_t)(x1 + EPS_SLACK1);
      008EB2 1E 0A            [ 2] 2247 	ldw	x, (0x0a, sp)
      008EB4 1C 00 08         [ 2] 2248 	addw	x, #0x0008
      008EB7 1F 27            [ 2] 2249 	ldw	(0x27, sp), x
                                   2250 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 596: if (c_labx1b[f] < 0x3FFF &&
      008EB9 1E 05            [ 2] 2251 	ldw	x, (0x05, sp)
      008EBB DE 00 D8         [ 2] 2252 	ldw	x, (_c_labx1b+0, x)
      008EBE A3 3F FF         [ 2] 2253 	cpw	x, #0x3fff
      008EC1 2E 08            [ 1] 2254 	jrsge	00136$
                                   2255 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 597: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
      008EC3 5C               [ 1] 2256 	incw	x
      008EC4 5C               [ 1] 2257 	incw	x
      008EC5 13 27            [ 2] 2258 	cpw	x, (0x27, sp)
      008EC7 2E 02            [ 1] 2259 	jrsge	00136$
                                   2260 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 598: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
      008EC9 1F 27            [ 2] 2261 	ldw	(0x27, sp), x
      008ECB                       2262 00136$:
                                   2263 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 600: if (wlo > whi) {
                                   2264 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 601: theta = (int16_t)((wlo + whi) >> 1);
      008ECB 1E 23            [ 2] 2265 	ldw	x, (0x23, sp)
      008ECD 13 27            [ 2] 2266 	cpw	x, (0x27, sp)
      008ECF 2D 0C            [ 1] 2267 	jrsle	00142$
      008ED1 72 FB 27         [ 2] 2268 	addw	x, (0x27, sp)
      008ED4 57               [ 2] 2269 	sraw	x
      008ED5 1F 11            [ 2] 2270 	ldw	(0x11, sp), x
                                   2271 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 602: have_theta = 1;
      008ED7 A6 01            [ 1] 2272 	ld	a, #0x01
      008ED9 6B 13            [ 1] 2273 	ld	(0x13, sp), a
      008EDB 20 21            [ 2] 2274 	jra	00245$
      008EDD                       2275 00142$:
                                   2276 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 604: int16_t th = have_theta ? theta : 0;
      008EDD 0D 13            [ 1] 2277 	tnz	(0x13, sp)
      008EDF 27 08            [ 1] 2278 	jreq	00175$
      008EE1 7B 12            [ 1] 2279 	ld	a, (0x12, sp)
      008EE3 02               [ 1] 2280 	rlwa	x
      008EE4 7B 11            [ 1] 2281 	ld	a, (0x11, sp)
      008EE6 01               [ 1] 2282 	rrwa	x
      008EE7 20 02            [ 2] 2283 	jra	00176$
      008EE9                       2284 00175$:
      008EE9 4F               [ 1] 2285 	clr	a
      008EEA 5F               [ 1] 2286 	clrw	x
      008EEB                       2287 00176$:
      008EEB 97               [ 1] 2288 	ld	xl, a
                                   2289 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 605: if (th < wlo) th = wlo;
      008EEC 13 23            [ 2] 2290 	cpw	x, (0x23, sp)
      008EEE 2E 02            [ 1] 2291 	jrsge	00138$
      008EF0 1E 23            [ 2] 2292 	ldw	x, (0x23, sp)
      008EF2                       2293 00138$:
                                   2294 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 606: if (th > whi) th = whi;
      008EF2 13 27            [ 2] 2295 	cpw	x, (0x27, sp)
      008EF4 2D 02            [ 1] 2296 	jrsle	00140$
      008EF6 1E 27            [ 2] 2297 	ldw	x, (0x27, sp)
      008EF8                       2298 00140$:
                                   2299 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 607: theta = th;
      008EF8 1F 11            [ 2] 2300 	ldw	(0x11, sp), x
                                   2301 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 608: have_theta = 1;
      008EFA A6 01            [ 1] 2302 	ld	a, #0x01
      008EFC 6B 13            [ 1] 2303 	ld	(0x13, sp), a
                                   2304 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
      008EFE                       2305 00245$:
      008EFE 1E 18            [ 2] 2306 	ldw	x, (0x18, sp)
      008F00 1C 00 4C         [ 2] 2307 	addw	x, #(_c_hist+0)
      008F03 1F 23            [ 2] 2308 	ldw	(0x23, sp), x
      008F05 0F 28            [ 1] 2309 	clr	(0x28, sp)
      008F07                       2310 00172$:
                                   2311 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 613: if (!c_hist[f][b]) continue;
      008F07 5F               [ 1] 2312 	clrw	x
      008F08 7B 28            [ 1] 2313 	ld	a, (0x28, sp)
      008F0A 97               [ 1] 2314 	ld	xl, a
      008F0B 72 FB 23         [ 2] 2315 	addw	x, (0x23, sp)
      008F0E F6               [ 1] 2316 	ld	a, (x)
      008F0F 27 2C            [ 1] 2317 	jreq	00157$
                                   2318 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 614: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008F11 5F               [ 1] 2319 	clrw	x
      008F12 7B 28            [ 1] 2320 	ld	a, (0x28, sp)
      008F14 97               [ 1] 2321 	ld	xl, a
      008F15 58               [ 2] 2322 	sllw	x
      008F16 1C 00 C1         [ 2] 2323 	addw	x, #193
      008F19 9F               [ 1] 2324 	ld	a, xl
      008F1A 49               [ 1] 2325 	rlc	a
      008F1B 4F               [ 1] 2326 	clr	a
      008F1C A2 00            [ 1] 2327 	sbc	a, #0x00
      008F1E 95               [ 1] 2328 	ld	xh, a
                                   2329 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 615: if (d > EPS_CLEAR1) clear1 = 1;
      008F1F 9F               [ 1] 2330 	ld	a, xl
      008F20 A1 12            [ 1] 2331 	cp	a, #0x12
      008F22 2D 06            [ 1] 2332 	jrsle	00155$
      008F24 A6 01            [ 1] 2333 	ld	a, #0x01
      008F26 6B 17            [ 1] 2334 	ld	(0x17, sp), a
      008F28 20 13            [ 2] 2335 	jra	00157$
      008F2A                       2336 00155$:
                                   2337 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 616: else if (d > -EPS_CLAMP56) {
      008F2A A3 FF E8         [ 2] 2338 	cpw	x, #0xffe8
      008F2D 2D 0E            [ 1] 2339 	jrsle	00157$
                                   2340 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 617: if (!have_top || d > top) top = d;
      008F2F 0D 16            [ 1] 2341 	tnz	(0x16, sp)
      008F31 27 04            [ 1] 2342 	jreq	00149$
      008F33 13 14            [ 2] 2343 	cpw	x, (0x14, sp)
      008F35 2D 02            [ 1] 2344 	jrsle	00150$
      008F37                       2345 00149$:
      008F37 1F 14            [ 2] 2346 	ldw	(0x14, sp), x
      008F39                       2347 00150$:
                                   2348 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 618: have_top = 1;
      008F39 A6 01            [ 1] 2349 	ld	a, #0x01
      008F3B 6B 16            [ 1] 2350 	ld	(0x16, sp), a
      008F3D                       2351 00157$:
                                   2352 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
      008F3D 0C 28            [ 1] 2353 	inc	(0x28, sp)
      008F3F 7B 28            [ 1] 2354 	ld	a, (0x28, sp)
      008F41 A1 40            [ 1] 2355 	cp	a, #0x40
      008F43 25 C2            [ 1] 2356 	jrc	00172$
                                   2357 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 621: if (!clear1 && have_top) {
      008F45 0D 17            [ 1] 2358 	tnz	(0x17, sp)
      008F47 26 36            [ 1] 2359 	jrne	00167$
      008F49 0D 16            [ 1] 2360 	tnz	(0x16, sp)
      008F4B 27 32            [ 1] 2361 	jreq	00167$
                                   2362 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 622: int16_t floor_ = (int16_t)(top + EPS_TOPM);
      008F4D 7B 15            [ 1] 2363 	ld	a, (0x15, sp)
      008F4F AB 03            [ 1] 2364 	add	a, #0x03
      008F51 97               [ 1] 2365 	ld	xl, a
      008F52 49               [ 1] 2366 	rlc	a
      008F53 4F               [ 1] 2367 	clr	a
      008F54 A2 00            [ 1] 2368 	sbc	a, #0x00
      008F56 95               [ 1] 2369 	ld	xh, a
                                   2370 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 623: if (!have_theta || floor_ > theta) theta = floor_;
      008F57 0D 13            [ 1] 2371 	tnz	(0x13, sp)
      008F59 27 04            [ 1] 2372 	jreq	00159$
      008F5B 13 11            [ 2] 2373 	cpw	x, (0x11, sp)
      008F5D 2D 02            [ 1] 2374 	jrsle	00160$
      008F5F                       2375 00159$:
      008F5F 1F 11            [ 2] 2376 	ldw	(0x11, sp), x
      008F61                       2377 00160$:
                                   2378 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 624: have_theta = 1;
      008F61 A6 01            [ 1] 2379 	ld	a, #0x01
      008F63 6B 13            [ 1] 2380 	ld	(0x13, sp), a
                                   2381 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 625: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
      008F65 0D 0C            [ 1] 2382 	tnz	(0x0c, sp)
      008F67 27 16            [ 1] 2383 	jreq	00167$
      008F69 16 0A            [ 2] 2384 	ldw	y, (0x0a, sp)
      008F6B 72 A9 00 02      [ 2] 2385 	addw	y, #0x0002
      008F6F 17 27            [ 2] 2386 	ldw	(0x27, sp), y
      008F71 13 27            [ 2] 2387 	cpw	x, (0x27, sp)
      008F73 2E 0A            [ 1] 2388 	jrsge	00167$
                                   2389 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 626: theta > (int16_t)(x1 + EPS_SLACK))
      008F75 1E 11            [ 2] 2390 	ldw	x, (0x11, sp)
      008F77 13 27            [ 2] 2391 	cpw	x, (0x27, sp)
      008F79 2D 04            [ 1] 2392 	jrsle	00167$
                                   2393 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 627: theta = (int16_t)(x1 + EPS_SLACK);
      008F7B 16 27            [ 2] 2394 	ldw	y, (0x27, sp)
      008F7D 17 11            [ 2] 2395 	ldw	(0x11, sp), y
      008F7F                       2396 00167$:
                                   2397 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 629: *theta_out = theta;
      008F7F 1E 25            [ 2] 2398 	ldw	x, (0x25, sp)
      008F81 16 11            [ 2] 2399 	ldw	y, (0x11, sp)
      008F83 FF               [ 2] 2400 	ldw	(x), y
                                   2401 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 630: return have_theta;
      008F84 7B 13            [ 1] 2402 	ld	a, (0x13, sp)
                                   2403 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 631: }
      008F86 5B 28            [ 2] 2404 	addw	sp, #40
      008F88 81               [ 4] 2405 	ret
                                   2406 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 634: static int16_t width_fit(uint8_t ci, int16_t prior, int16_t blo, int16_t bhi)
                                   2407 ;	-----------------------------------------
                                   2408 ;	 function width_fit
                                   2409 ;	-----------------------------------------
      008F89                       2410 _width_fit:
      008F89 52 04            [ 2] 2411 	sub	sp, #4
      008F8B 1F 03            [ 2] 2412 	ldw	(0x03, sp), x
                                   2413 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 636: int16_t lo = c_lo[ci], hi = c_hi[ci], h;
      008F8D 5F               [ 1] 2414 	clrw	x
      008F8E 97               [ 1] 2415 	ld	xl, a
      008F8F 58               [ 2] 2416 	sllw	x
      008F90 90 93            [ 1] 2417 	ldw	y, x
      008F92 DE 00 3C         [ 2] 2418 	ldw	x, (_c_lo+0, x)
      008F95 1F 01            [ 2] 2419 	ldw	(0x01, sp), x
      008F97 90 DE 00 40      [ 2] 2420 	ldw	y, (_c_hi+0, y)
                                   2421 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 637: if (c_n[ci] < LAB_MIN) return prior;
      008F9B 5F               [ 1] 2422 	clrw	x
      008F9C 97               [ 1] 2423 	ld	xl, a
      008F9D 1C 00 44         [ 2] 2424 	addw	x, #(_c_n+0)
      008FA0 F6               [ 1] 2425 	ld	a, (x)
      008FA1 A1 03            [ 1] 2426 	cp	a, #0x03
      008FA3 24 04            [ 1] 2427 	jrnc	00102$
      008FA5 1E 03            [ 2] 2428 	ldw	x, (0x03, sp)
      008FA7 20 31            [ 2] 2429 	jra	00103$
      008FA9                       2430 00102$:
                                   2431 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 638: h = (lo > hi) ? (int16_t)((lo + hi) >> 1)
      008FA9 51               [ 1] 2432 	exgw	x, y
      008FAA 13 01            [ 2] 2433 	cpw	x, (0x01, sp)
      008FAC 51               [ 1] 2434 	exgw	x, y
      008FAD 2E 07            [ 1] 2435 	jrsge	00105$
      008FAF 93               [ 1] 2436 	ldw	x, y
      008FB0 72 FB 01         [ 2] 2437 	addw	x, (0x01, sp)
      008FB3 57               [ 2] 2438 	sraw	x
      008FB4 20 1A            [ 2] 2439 	jra	00106$
      008FB6                       2440 00105$:
                                   2441 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 639: : (prior < lo ? lo : (prior > hi ? hi : prior));
      008FB6 1E 03            [ 2] 2442 	ldw	x, (0x03, sp)
      008FB8 13 01            [ 2] 2443 	cpw	x, (0x01, sp)
      008FBA 2E 04            [ 1] 2444 	jrsge	00107$
      008FBC 1E 01            [ 2] 2445 	ldw	x, (0x01, sp)
      008FBE 20 10            [ 2] 2446 	jra	00108$
      008FC0                       2447 00107$:
      008FC0 51               [ 1] 2448 	exgw	x, y
      008FC1 13 03            [ 2] 2449 	cpw	x, (0x03, sp)
      008FC3 51               [ 1] 2450 	exgw	x, y
      008FC4 2E 04            [ 1] 2451 	jrsge	00109$
      008FC6 17 01            [ 2] 2452 	ldw	(0x01, sp), y
      008FC8 20 04            [ 2] 2453 	jra	00110$
      008FCA                       2454 00109$:
      008FCA 16 03            [ 2] 2455 	ldw	y, (0x03, sp)
      008FCC 17 01            [ 2] 2456 	ldw	(0x01, sp), y
      008FCE                       2457 00110$:
      008FCE 1E 01            [ 2] 2458 	ldw	x, (0x01, sp)
      008FD0                       2459 00108$:
      008FD0                       2460 00106$:
                                   2461 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 640: return (h >= blo && h <= bhi) ? h : prior;
      008FD0 13 07            [ 2] 2462 	cpw	x, (0x07, sp)
      008FD2 2F 04            [ 1] 2463 	jrslt	00111$
      008FD4 13 09            [ 2] 2464 	cpw	x, (0x09, sp)
      008FD6 2D 02            [ 1] 2465 	jrsle	00112$
      008FD8                       2466 00111$:
      008FD8 1E 03            [ 2] 2467 	ldw	x, (0x03, sp)
      008FDA                       2468 00112$:
      008FDA                       2469 00103$:
                                   2470 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 641: }
      008FDA 16 05            [ 2] 2471 	ldw	y, (5, sp)
      008FDC 5B 0A            [ 2] 2472 	addw	sp, #10
      008FDE 90 FC            [ 2] 2473 	jp	(y)
                                   2474 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 643: static void calibrate(void)
                                   2475 ;	-----------------------------------------
                                   2476 ;	 function calibrate
                                   2477 ;	-----------------------------------------
      008FE0                       2478 _calibrate:
      008FE0 52 15            [ 2] 2479 	sub	sp, #21
                                   2480 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 647: c_lo[0] = c_lo[1] = -0x4000;
      008FE2 35 00 00 3F      [ 1] 2481 	mov	_c_lo+3, #0x00
      008FE6 35 C0 00 3E      [ 1] 2482 	mov	_c_lo+2, #0xc0
      008FEA 35 00 00 3D      [ 1] 2483 	mov	_c_lo+1, #0x00
      008FEE 35 C0 00 3C      [ 1] 2484 	mov	_c_lo+0, #0xc0
                                   2485 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 648: c_hi[0] = c_hi[1] = 0x3FFF;
      008FF2 35 FF 00 43      [ 1] 2486 	mov	_c_hi+3, #0xff
      008FF6 35 3F 00 42      [ 1] 2487 	mov	_c_hi+2, #0x3f
      008FFA 35 FF 00 41      [ 1] 2488 	mov	_c_hi+1, #0xff
      008FFE 35 3F 00 40      [ 1] 2489 	mov	_c_hi+0, #0x3f
                                   2490 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 649: c_n[0] = c_n[1] = 0;
      009002 35 00 00 45      [ 1] 2491 	mov	_c_n+1, #0x00
      009006 35 00 00 44      [ 1] 2492 	mov	_c_n+0, #0x00
                                   2493 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 650: c_h0c = H0P; c_h1c = H1P;
      00900A AE 00 9A         [ 2] 2494 	ldw	x, #0x009a
      00900D CF 00 46         [ 2] 2495 	ldw	_c_h0c+0, x
      009010 AE 01 34         [ 2] 2496 	ldw	x, #0x0134
      009013 CF 00 48         [ 2] 2497 	ldw	_c_h1c+0, x
                                   2498 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 651: c_d56[0] = c_d56[1] = 0;
      009016 35 00 00 4B      [ 1] 2499 	mov	_c_d56+1, #0x00
      00901A 35 00 00 4A      [ 1] 2500 	mov	_c_d56+0, #0x00
                                   2501 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
      00901E CE 00 38         [ 2] 2502 	ldw	x, _g_K+0
      009021 89               [ 2] 2503 	pushw	x
      009022 AE 00 06         [ 2] 2504 	ldw	x, #0x0006
      009025 CD 9C 37         [ 4] 2505 	call	___muluint2ulong
      009028 5B 02            [ 2] 2506 	addw	sp, #2
      00902A A6 0B            [ 1] 2507 	ld	a, #0x0b
      00902C                       2508 00285$:
      00902C 90 54            [ 2] 2509 	srlw	y
      00902E 56               [ 2] 2510 	rrcw	x
      00902F 4A               [ 1] 2511 	dec	a
      009030 26 FA            [ 1] 2512 	jrne	00285$
      009032 CF 00 E0         [ 2] 2513 	ldw	_c_gap56+0, x
                                   2514 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 653: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
      009035 CE 00 38         [ 2] 2515 	ldw	x, _g_K+0
      009038 89               [ 2] 2516 	pushw	x
      009039 AE 00 05         [ 2] 2517 	ldw	x, #0x0005
      00903C CD 9C 37         [ 4] 2518 	call	___muluint2ulong
      00903F 5B 02            [ 2] 2519 	addw	sp, #2
      009041 A6 0B            [ 1] 2520 	ld	a, #0x0b
      009043                       2521 00287$:
      009043 90 54            [ 2] 2522 	srlw	y
      009045 56               [ 2] 2523 	rrcw	x
      009046 4A               [ 1] 2524 	dec	a
      009047 26 FA            [ 1] 2525 	jrne	00287$
      009049 CF 00 E2         [ 2] 2526 	ldw	_c_gap56+2, x
                                   2527 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
      00904C 0F 15            [ 1] 2528 	clr	(0x15, sp)
      00904E                       2529 00128$:
                                   2530 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 656: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
      00904E 5F               [ 1] 2531 	clrw	x
      00904F 7B 15            [ 1] 2532 	ld	a, (0x15, sp)
      009051 97               [ 1] 2533 	ld	xl, a
      009052 58               [ 2] 2534 	sllw	x
      009053 1F 11            [ 2] 2535 	ldw	(0x11, sp), x
      009055 90 93            [ 1] 2536 	ldw	y, x
      009057 72 A9 00 DC      [ 2] 2537 	addw	y, #(_c_c0+0)
      00905B 1E 11            [ 2] 2538 	ldw	x, (0x11, sp)
      00905D DE 00 E0         [ 2] 2539 	ldw	x, (_c_gap56+0, x)
      009060 1F 13            [ 2] 2540 	ldw	(0x13, sp), x
      009062 AE 01 CE         [ 2] 2541 	ldw	x, #0x01ce
      009065 72 F0 13         [ 2] 2542 	subw	x, (0x13, sp)
      009068 57               [ 2] 2543 	sraw	x
      009069 90 FF            [ 2] 2544 	ldw	(y), x
                                   2545 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 657: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
      00906B 7B 15            [ 1] 2546 	ld	a, (0x15, sp)
      00906D 97               [ 1] 2547 	ld	xl, a
      00906E A6 40            [ 1] 2548 	ld	a, #0x40
      009070 42               [ 4] 2549 	mul	x, a
      009071 1C 00 4C         [ 2] 2550 	addw	x, #(_c_hist+0)
      009074 1F 13            [ 2] 2551 	ldw	(0x13, sp), x
      009076 4F               [ 1] 2552 	clr	a
      009077                       2553 00126$:
      009077 5F               [ 1] 2554 	clrw	x
      009078 97               [ 1] 2555 	ld	xl, a
      009079 72 FB 13         [ 2] 2556 	addw	x, (0x13, sp)
      00907C 7F               [ 1] 2557 	clr	(x)
      00907D 4C               [ 1] 2558 	inc	a
      00907E A1 40            [ 1] 2559 	cp	a, #0x40
      009080 25 F5            [ 1] 2560 	jrc	00126$
                                   2561 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 658: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
      009082 1E 11            [ 2] 2562 	ldw	x, (0x11, sp)
      009084 1C 00 CC         [ 2] 2563 	addw	x, #(_c_labx0+0)
      009087 6F 01            [ 1] 2564 	clr	(0x1, x)
      009089 A6 C0            [ 1] 2565 	ld	a, #0xc0
      00908B F7               [ 1] 2566 	ld	(x), a
      00908C 1E 11            [ 2] 2567 	ldw	x, (0x11, sp)
      00908E 1C 00 D4         [ 2] 2568 	addw	x, #(_c_labx0b+0)
      009091 6F 01            [ 1] 2569 	clr	(0x1, x)
      009093 A6 C0            [ 1] 2570 	ld	a, #0xc0
      009095 F7               [ 1] 2571 	ld	(x), a
                                   2572 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 659: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
      009096 1E 11            [ 2] 2573 	ldw	x, (0x11, sp)
      009098 90 AE 3F FF      [ 2] 2574 	ldw	y, #0x3fff
      00909C DF 00 D0         [ 2] 2575 	ldw	((_c_labx1+0), x), y
      00909F 1E 11            [ 2] 2576 	ldw	x, (0x11, sp)
      0090A1 90 AE 3F FF      [ 2] 2577 	ldw	y, #0x3fff
      0090A5 DF 00 D8         [ 2] 2578 	ldw	((_c_labx1b+0), x), y
                                   2579 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
      0090A8 0C 15            [ 1] 2580 	inc	(0x15, sp)
      0090AA 7B 15            [ 1] 2581 	ld	a, (0x15, sp)
      0090AC A1 02            [ 1] 2582 	cp	a, #0x02
      0090AE 25 9E            [ 1] 2583 	jrc	00128$
                                   2584 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 661: ss_init();
      0090B0 CD 88 43         [ 4] 2585 	call	_ss_init
                                   2586 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 662: while (ss_next(&sg)) {
      0090B3                       2587 00112$:
      0090B3 96               [ 1] 2588 	ldw	x, sp
      0090B4 5C               [ 1] 2589 	incw	x
      0090B5 CD 88 85         [ 4] 2590 	call	_ss_next
      0090B8 4D               [ 1] 2591 	tnz	a
      0090B9 26 03            [ 1] 2592 	jrne	00291$
      0090BB CC 91 40         [ 2] 2593 	jp	00114$
      0090BE                       2594 00291$:
                                   2595 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 664: uint8_t known_all = 1;
      0090BE A6 01            [ 1] 2596 	ld	a, #0x01
      0090C0 6B 13            [ 1] 2597 	ld	(0x13, sp), a
                                   2598 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 666: cal_cloud(sg.u, sg.fam);
      0090C2 7B 09            [ 1] 2599 	ld	a, (0x09, sp)
      0090C4 1E 05            [ 2] 2600 	ldw	x, (0x05, sp)
      0090C6 CD 8B CC         [ 4] 2601 	call	_cal_cloud
                                   2602 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: if (sg.k1 > NB) continue;
      0090C9 1E 03            [ 2] 2603 	ldw	x, (0x03, sp)
      0090CB A3 00 D8         [ 2] 2604 	cpw	x, #0x00d8
      0090CE 22 E3            [ 1] 2605 	jrugt	00112$
                                   2606 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 668: e = (sg.k1 < NB) ? sg.k1 : NB;
      0090D0 A3 00 D8         [ 2] 2607 	cpw	x, #0x00d8
      0090D3 24 03            [ 1] 2608 	jrnc	00136$
      0090D5 9F               [ 1] 2609 	ld	a, xl
      0090D6 20 03            [ 2] 2610 	jra	00137$
      0090D8                       2611 00136$:
      0090D8 A6 D8            [ 1] 2612 	ld	a, #0xd8
      0090DA 5F               [ 1] 2613 	clrw	x
      0090DB                       2614 00137$:
      0090DB 6B 15            [ 1] 2615 	ld	(0x15, sp), a
      0090DD 02               [ 1] 2616 	rlwa	x
      0090DE 6B 14            [ 1] 2617 	ld	(0x14, sp), a
      0090E0 01               [ 1] 2618 	rrwa	x
                                   2619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
      0090E1 96               [ 1] 2620 	ldw	x, sp
      0090E2 5C               [ 1] 2621 	incw	x
      0090E3 1F 0E            [ 2] 2622 	ldw	(0x0e, sp), x
      0090E5 FE               [ 2] 2623 	ldw	x, (x)
      0090E6                       2624 00131$:
      0090E6 13 14            [ 2] 2625 	cpw	x, (0x14, sp)
      0090E8 24 0F            [ 1] 2626 	jrnc	00107$
                                   2627 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 670: if (known_bit(t) < 0) { known_all = 0; break; }
      0090EA 89               [ 2] 2628 	pushw	x
      0090EB CD 81 C6         [ 4] 2629 	call	_known_bit
      0090EE 85               [ 2] 2630 	popw	x
      0090EF 4D               [ 1] 2631 	tnz	a
      0090F0 2A 04            [ 1] 2632 	jrpl	00132$
      0090F2 0F 13            [ 1] 2633 	clr	(0x13, sp)
      0090F4 20 03            [ 2] 2634 	jra	00107$
      0090F6                       2635 00132$:
                                   2636 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
      0090F6 5C               [ 1] 2637 	incw	x
      0090F7 20 ED            [ 2] 2638 	jra	00131$
      0090F9                       2639 00107$:
                                   2640 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 671: if (!known_all) continue;
      0090F9 0D 13            [ 1] 2641 	tnz	(0x13, sp)
      0090FB 27 B6            [ 1] 2642 	jreq	00112$
                                   2643 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 672: a_bounds(sg.k0, sg.k1, &amin, &amax);
      0090FD 16 03            [ 2] 2644 	ldw	y, (0x03, sp)
      0090FF 1E 0E            [ 2] 2645 	ldw	x, (0x0e, sp)
      009101 FE               [ 2] 2646 	ldw	x, (x)
      009102 1F 14            [ 2] 2647 	ldw	(0x14, sp), x
      009104 96               [ 1] 2648 	ldw	x, sp
      009105 1C 00 0C         [ 2] 2649 	addw	x, #12
      009108 89               [ 2] 2650 	pushw	x
      009109 96               [ 1] 2651 	ldw	x, sp
      00910A 1C 00 0C         [ 2] 2652 	addw	x, #12
      00910D 89               [ 2] 2653 	pushw	x
      00910E 90 89            [ 2] 2654 	pushw	y
      009110 1E 1A            [ 2] 2655 	ldw	x, (0x1a, sp)
      009112 CD 8A B3         [ 4] 2656 	call	_a_bounds
                                   2657 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 673: if (amin == amax)
      009115 1E 0A            [ 2] 2658 	ldw	x, (0x0a, sp)
      009117 13 0C            [ 2] 2659 	cpw	x, (0x0c, sp)
      009119 26 98            [ 1] 2660 	jrne	00112$
                                   2661 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 674: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
      00911B 7B 09            [ 1] 2662 	ld	a, (0x09, sp)
      00911D 16 07            [ 2] 2663 	ldw	y, (0x07, sp)
      00911F 17 10            [ 2] 2664 	ldw	(0x10, sp), y
      009121 16 05            [ 2] 2665 	ldw	y, (0x05, sp)
      009123 17 12            [ 2] 2666 	ldw	(0x12, sp), y
      009125 16 03            [ 2] 2667 	ldw	y, (0x03, sp)
      009127 1E 0E            [ 2] 2668 	ldw	x, (0x0e, sp)
      009129 FE               [ 2] 2669 	ldw	x, (x)
      00912A 1F 14            [ 2] 2670 	ldw	(0x14, sp), x
      00912C 1E 0A            [ 2] 2671 	ldw	x, (0x0a, sp)
      00912E 89               [ 2] 2672 	pushw	x
      00912F 88               [ 1] 2673 	push	a
      009130 1E 13            [ 2] 2674 	ldw	x, (0x13, sp)
      009132 89               [ 2] 2675 	pushw	x
      009133 1E 17            [ 2] 2676 	ldw	x, (0x17, sp)
      009135 89               [ 2] 2677 	pushw	x
      009136 90 89            [ 2] 2678 	pushw	y
      009138 1E 1D            [ 2] 2679 	ldw	x, (0x1d, sp)
      00913A CD 8C 13         [ 4] 2680 	call	_cal_add
      00913D CC 90 B3         [ 2] 2681 	jp	00112$
      009140                       2682 00114$:
                                   2683 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 678: int16_t h0 = width_fit(0, H0P, H0_LO, H0_HI);
      009140 4B C0            [ 1] 2684 	push	#0xc0
      009142 4B 00            [ 1] 2685 	push	#0x00
      009144 4B 70            [ 1] 2686 	push	#0x70
      009146 4B 00            [ 1] 2687 	push	#0x00
      009148 AE 00 9A         [ 2] 2688 	ldw	x, #0x009a
      00914B 4F               [ 1] 2689 	clr	a
      00914C CD 8F 89         [ 4] 2690 	call	_width_fit
      00914F 1F 14            [ 2] 2691 	ldw	(0x14, sp), x
                                   2692 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 679: int16_t h1 = width_fit(1, H1P, H1_LO, H1_HI);
      009151 4B 78            [ 1] 2693 	push	#0x78
      009153 4B 01            [ 1] 2694 	push	#0x01
      009155 4B FC            [ 1] 2695 	push	#0xfc
      009157 4B 00            [ 1] 2696 	push	#0x00
      009159 AE 01 34         [ 2] 2697 	ldw	x, #0x0134
      00915C A6 01            [ 1] 2698 	ld	a, #0x01
      00915E CD 8F 89         [ 4] 2699 	call	_width_fit
                                   2700 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 680: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
      009161 90 93            [ 1] 2701 	ldw	y, x
      009163 72 F0 14         [ 2] 2702 	subw	x, (0x14, sp)
      009166 A3 00 70         [ 2] 2703 	cpw	x, #0x0070
      009169 2F 05            [ 1] 2704 	jrslt	00115$
      00916B A3 00 C4         [ 2] 2705 	cpw	x, #0x00c4
      00916E 2D 09            [ 1] 2706 	jrsle	00116$
      009170                       2707 00115$:
      009170 AE 00 9A         [ 2] 2708 	ldw	x, #0x009a
      009173 1F 14            [ 2] 2709 	ldw	(0x14, sp), x
      009175 90 AE 01 34      [ 2] 2710 	ldw	y, #0x0134
      009179                       2711 00116$:
                                   2712 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 681: c_h0c = h0; c_h1c = h1;
      009179 1E 14            [ 2] 2713 	ldw	x, (0x14, sp)
      00917B CF 00 46         [ 2] 2714 	ldw	_c_h0c+0, x
      00917E 90 CF 00 48      [ 2] 2715 	ldw	_c_h1c+0, y
                                   2716 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
      009182 0F 15            [ 1] 2717 	clr	(0x15, sp)
      009184                       2718 00133$:
                                   2719 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 685: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
      009184 96               [ 1] 2720 	ldw	x, sp
      009185 1C 00 0C         [ 2] 2721 	addw	x, #12
      009188 7B 15            [ 1] 2722 	ld	a, (0x15, sp)
      00918A CD 8D 0D         [ 4] 2723 	call	_theta56
      00918D 5F               [ 1] 2724 	clrw	x
      00918E 41               [ 1] 2725 	exg	a, xl
      00918F 7B 15            [ 1] 2726 	ld	a, (0x15, sp)
      009191 41               [ 1] 2727 	exg	a, xl
      009192 1C 00 4A         [ 2] 2728 	addw	x, #(_c_d56+0)
      009195 1F 11            [ 2] 2729 	ldw	(0x11, sp), x
      009197 4D               [ 1] 2730 	tnz	a
      009198 26 05            [ 1] 2731 	jrne	00119$
      00919A 1E 11            [ 2] 2732 	ldw	x, (0x11, sp)
      00919C 7F               [ 1] 2733 	clr	(x)
      00919D 20 3B            [ 2] 2734 	jra	00124$
      00919F                       2735 00119$:
                                   2736 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 686: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
      00919F CE 00 46         [ 2] 2737 	ldw	x, _c_h0c+0
      0091A2 72 BB 00 48      [ 2] 2738 	addw	x, _c_h1c+0
      0091A6 1F 13            [ 2] 2739 	ldw	(0x13, sp), x
      0091A8 5F               [ 1] 2740 	clrw	x
      0091A9 7B 15            [ 1] 2741 	ld	a, (0x15, sp)
      0091AB 97               [ 1] 2742 	ld	xl, a
      0091AC 58               [ 2] 2743 	sllw	x
      0091AD 90 93            [ 1] 2744 	ldw	y, x
      0091AF DE 00 E0         [ 2] 2745 	ldw	x, (_c_gap56+0, x)
      0091B2 50               [ 2] 2746 	negw	x
      0091B3 72 FB 13         [ 2] 2747 	addw	x, (0x13, sp)
      0091B6 57               [ 2] 2748 	sraw	x
      0091B7 1F 13            [ 2] 2749 	ldw	(0x13, sp), x
                                   2750 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 687: delta = (int16_t)(th + c_c0[f] - cfit);
      0091B9 93               [ 1] 2751 	ldw	x, y
      0091BA DE 00 DC         [ 2] 2752 	ldw	x, (_c_c0+0, x)
      0091BD 72 FB 0C         [ 2] 2753 	addw	x, (0x0c, sp)
      0091C0 72 F0 13         [ 2] 2754 	subw	x, (0x13, sp)
                                   2755 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 688: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
      0091C3 A3 FF E8         [ 2] 2756 	cpw	x, #0xffe8
      0091C6 2E 03            [ 1] 2757 	jrsge	00121$
      0091C8 AE FF E8         [ 2] 2758 	ldw	x, #0xffe8
      0091CB                       2759 00121$:
                                   2760 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 689: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
      0091CB 90 93            [ 1] 2761 	ldw	y, x
      0091CD 90 A3 00 18      [ 2] 2762 	cpw	y, #0x0018
      0091D1 2D 03            [ 1] 2763 	jrsle	00123$
      0091D3 AE 00 18         [ 2] 2764 	ldw	x, #0x0018
      0091D6                       2765 00123$:
                                   2766 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: c_d56[f] = (int8_t)delta;
      0091D6 9F               [ 1] 2767 	ld	a, xl
      0091D7 1E 11            [ 2] 2768 	ldw	x, (0x11, sp)
      0091D9 F7               [ 1] 2769 	ld	(x), a
      0091DA                       2770 00124$:
                                   2771 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
      0091DA 0C 15            [ 1] 2772 	inc	(0x15, sp)
      0091DC 7B 15            [ 1] 2773 	ld	a, (0x15, sp)
      0091DE A1 02            [ 1] 2774 	cp	a, #0x02
      0091E0 25 A2            [ 1] 2775 	jrc	00133$
                                   2776 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 692: }
      0091E2 5B 15            [ 2] 2777 	addw	sp, #21
      0091E4 81               [ 4] 2778 	ret
                                   2779 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 696: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
                                   2780 ;	-----------------------------------------
                                   2781 ;	 function hinge
                                   2782 ;	-----------------------------------------
      0091E5                       2783 _hinge:
      0091E5 89               [ 2] 2784 	pushw	x
      0091E6 51               [ 1] 2785 	exgw	x, y
                                   2786 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 698: int16_t g = 0;
      0091E7 5F               [ 1] 2787 	clrw	x
                                   2788 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 699: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
      0091E8 72 F2 07         [ 2] 2789 	subw	y, (0x07, sp)
      0091EB 90 A3 00 00      [ 2] 2790 	cpw	y, #0x0000
      0091EF 2D 01            [ 1] 2791 	jrsle	00102$
      0091F1 93               [ 1] 2792 	ldw	x, y
      0091F2                       2793 00102$:
                                   2794 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 700: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
      0091F2 16 07            [ 2] 2795 	ldw	y, (0x07, sp)
      0091F4 72 F2 05         [ 2] 2796 	subw	y, (0x05, sp)
      0091F7 17 01            [ 2] 2797 	ldw	(0x01, sp), y
      0091F9 13 01            [ 2] 2798 	cpw	x, (0x01, sp)
      0091FB 2E 02            [ 1] 2799 	jrsge	00104$
      0091FD 1E 01            [ 2] 2800 	ldw	x, (0x01, sp)
      0091FF                       2801 00104$:
                                   2802 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 701: return (uint16_t)g;
                                   2803 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 702: }
      0091FF 16 03            [ 2] 2804 	ldw	y, (3, sp)
      009201 5B 08            [ 2] 2805 	addw	sp, #8
      009203 90 FC            [ 2] 2806 	jp	(y)
                                   2807 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 706: static int16_t argmin_ab(int16_t lo, int16_t hi)
                                   2808 ;	-----------------------------------------
                                   2809 ;	 function argmin_ab
                                   2810 ;	-----------------------------------------
      009205                       2811 _argmin_ab:
      009205 52 06            [ 2] 2812 	sub	sp, #6
      009207 51               [ 1] 2813 	exgw	x, y
                                   2814 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 708: uint16_t bc = 0xFFFF;
      009208 5F               [ 1] 2815 	clrw	x
      009209 5A               [ 2] 2816 	decw	x
      00920A 1F 01            [ 2] 2817 	ldw	(0x01, sp), x
                                   2818 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 709: uint8_t bi = 1;
      00920C A6 01            [ 1] 2819 	ld	a, #0x01
      00920E 6B 03            [ 1] 2820 	ld	(0x03, sp), a
                                   2821 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 710: int16_t a, best = lo;
      009210 17 04            [ 2] 2822 	ldw	(0x04, sp), y
                                   2823 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
      009212                       2824 00108$:
      009212 51               [ 1] 2825 	exgw	x, y
      009213 13 09            [ 2] 2826 	cpw	x, (0x09, sp)
      009215 51               [ 1] 2827 	exgw	x, y
      009216 2C 32            [ 1] 2828 	jrsgt	00106$
                                   2829 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 712: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      009218 CE 01 25         [ 2] 2830 	ldw	x, _d_inter+0
      00921B 90 9F            [ 1] 2831 	ld	a, yl
      00921D 4D               [ 1] 2832 	tnz	a
      00921E 27 04            [ 1] 2833 	jreq	00155$
      009220                       2834 00154$:
      009220 54               [ 2] 2835 	srlw	x
      009221 4A               [ 1] 2836 	dec	a
      009222 26 FC            [ 1] 2837 	jrne	00154$
      009224                       2838 00155$:
      009224 9F               [ 1] 2839 	ld	a, xl
      009225 A4 01            [ 1] 2840 	and	a, #0x01
      009227 6B 06            [ 1] 2841 	ld	(0x06, sp), a
                                   2842 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 713: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      009229 93               [ 1] 2843 	ldw	x, y
      00922A 58               [ 2] 2844 	sllw	x
      00922B DE 01 05         [ 2] 2845 	ldw	x, (_d_costs+0, x)
      00922E 13 01            [ 2] 2846 	cpw	x, (0x01, sp)
      009230 25 0C            [ 1] 2847 	jrc	00101$
      009232 13 01            [ 2] 2848 	cpw	x, (0x01, sp)
      009234 26 10            [ 1] 2849 	jrne	00109$
      009236 0D 06            [ 1] 2850 	tnz	(0x06, sp)
      009238 27 0C            [ 1] 2851 	jreq	00109$
      00923A 0D 03            [ 1] 2852 	tnz	(0x03, sp)
      00923C 26 08            [ 1] 2853 	jrne	00109$
      00923E                       2854 00101$:
                                   2855 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 714: bc = d_costs[a]; bi = it; best = a;
      00923E 1F 01            [ 2] 2856 	ldw	(0x01, sp), x
      009240 7B 06            [ 1] 2857 	ld	a, (0x06, sp)
      009242 6B 03            [ 1] 2858 	ld	(0x03, sp), a
      009244 17 04            [ 2] 2859 	ldw	(0x04, sp), y
      009246                       2860 00109$:
                                   2861 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
      009246 90 5C            [ 1] 2862 	incw	y
      009248 20 C8            [ 2] 2863 	jra	00108$
      00924A                       2864 00106$:
                                   2865 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 717: return best;
      00924A 1E 04            [ 2] 2866 	ldw	x, (0x04, sp)
                                   2867 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 718: }
      00924C 5B 06            [ 2] 2868 	addw	sp, #6
      00924E 90 85            [ 2] 2869 	popw	y
      009250 5B 02            [ 2] 2870 	addw	sp, #2
      009252 90 FC            [ 2] 2871 	jp	(y)
                                   2872 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 721: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   2873 ;	-----------------------------------------
                                   2874 ;	 function decide
                                   2875 ;	-----------------------------------------
      009254                       2876 _decide:
      009254 52 18            [ 2] 2877 	sub	sp, #24
      009256 1F 15            [ 2] 2878 	ldw	(0x15, sp), x
                                   2879 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: int16_t L = (int16_t)(k1 - k0);
      009258 1E 1B            [ 2] 2880 	ldw	x, (0x1b, sp)
      00925A 72 F0 15         [ 2] 2881 	subw	x, (0x15, sp)
                                   2882 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 726: int16_t acap = (L < A_CAP) ? L : A_CAP;
      00925D 1F 05            [ 2] 2883 	ldw	(0x05, sp), x
      00925F A3 00 0F         [ 2] 2884 	cpw	x, #0x000f
      009262 2F 03            [ 1] 2885 	jrslt	00126$
      009264 AE 00 0F         [ 2] 2886 	ldw	x, #0x000f
      009267                       2887 00126$:
      009267 1F 07            [ 2] 2888 	ldw	(0x07, sp), x
                                   2889 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 727: int16_t h0e = c_h0c, h1e = c_h1c;
      009269 CE 00 46         [ 2] 2890 	ldw	x, _c_h0c+0
      00926C 1F 09            [ 2] 2891 	ldw	(0x09, sp), x
      00926E CE 00 48         [ 2] 2892 	ldw	x, _c_h1c+0
      009271 1F 0B            [ 2] 2893 	ldw	(0x0b, sp), x
                                   2894 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 729: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
      009273 7B 21            [ 1] 2895 	ld	a, (0x21, sp)
      009275 A1 05            [ 1] 2896 	cp	a, #0x05
      009277 26 19            [ 1] 2897 	jrne	00102$
      009279 C6 00 4A         [ 1] 2898 	ld	a, _c_d56+0
      00927C 6B 18            [ 1] 2899 	ld	(0x18, sp), a
      00927E 49               [ 1] 2900 	rlc	a
      00927F 4F               [ 1] 2901 	clr	a
      009280 A2 00            [ 1] 2902 	sbc	a, #0x00
      009282 6B 17            [ 1] 2903 	ld	(0x17, sp), a
      009284 1E 09            [ 2] 2904 	ldw	x, (0x09, sp)
      009286 72 FB 17         [ 2] 2905 	addw	x, (0x17, sp)
      009289 1F 09            [ 2] 2906 	ldw	(0x09, sp), x
      00928B 1E 0B            [ 2] 2907 	ldw	x, (0x0b, sp)
      00928D 72 FB 17         [ 2] 2908 	addw	x, (0x17, sp)
      009290 1F 0B            [ 2] 2909 	ldw	(0x0b, sp), x
      009292                       2910 00102$:
                                   2911 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 730: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
      009292 7B 21            [ 1] 2912 	ld	a, (0x21, sp)
      009294 A1 06            [ 1] 2913 	cp	a, #0x06
      009296 26 19            [ 1] 2914 	jrne	00104$
      009298 C6 00 4B         [ 1] 2915 	ld	a, _c_d56+1
      00929B 6B 18            [ 1] 2916 	ld	(0x18, sp), a
      00929D 49               [ 1] 2917 	rlc	a
      00929E 4F               [ 1] 2918 	clr	a
      00929F A2 00            [ 1] 2919 	sbc	a, #0x00
      0092A1 6B 17            [ 1] 2920 	ld	(0x17, sp), a
      0092A3 1E 09            [ 2] 2921 	ldw	x, (0x09, sp)
      0092A5 72 FB 17         [ 2] 2922 	addw	x, (0x17, sp)
      0092A8 1F 09            [ 2] 2923 	ldw	(0x09, sp), x
      0092AA 1E 0B            [ 2] 2924 	ldw	x, (0x0b, sp)
      0092AC 72 FB 17         [ 2] 2925 	addw	x, (0x17, sp)
      0092AF 1F 0B            [ 2] 2926 	ldw	(0x0b, sp), x
      0092B1                       2927 00104$:
                                   2928 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 731: d_inter = 0;
      0092B1 5F               [ 1] 2929 	clrw	x
      0092B2 CF 01 25         [ 2] 2930 	ldw	_d_inter+0, x
                                   2931 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
      0092B5 1E 1D            [ 2] 2932 	ldw	x, (0x1d, sp)
      0092B7 13 09            [ 2] 2933 	cpw	x, (0x09, sp)
      0092B9 2F 04            [ 1] 2934 	jrslt	00273$
      0092BB 0F 0D            [ 1] 2935 	clr	(0x0d, sp)
      0092BD 20 04            [ 2] 2936 	jra	00274$
      0092BF                       2937 00273$:
      0092BF A6 01            [ 1] 2938 	ld	a, #0x01
      0092C1 6B 0D            [ 1] 2939 	ld	(0x0d, sp), a
      0092C3                       2940 00274$:
      0092C3 1E 09            [ 2] 2941 	ldw	x, (0x09, sp)
      0092C5 13 1F            [ 2] 2942 	cpw	x, (0x1f, sp)
      0092C7 2C 04            [ 1] 2943 	jrsgt	00275$
      0092C9 0F 0E            [ 1] 2944 	clr	(0x0e, sp)
      0092CB 20 04            [ 2] 2945 	jra	00276$
      0092CD                       2946 00275$:
      0092CD A6 01            [ 1] 2947 	ld	a, #0x01
      0092CF 6B 0E            [ 1] 2948 	ld	(0x0e, sp), a
      0092D1                       2949 00276$:
      0092D1 5F               [ 1] 2950 	clrw	x
      0092D2 1F 17            [ 2] 2951 	ldw	(0x17, sp), x
      0092D4                       2952 00121$:
      0092D4 1E 17            [ 2] 2953 	ldw	x, (0x17, sp)
      0092D6 13 07            [ 2] 2954 	cpw	x, (0x07, sp)
      0092D8 2D 03            [ 1] 2955 	jrsle	00277$
      0092DA CC 93 83         [ 2] 2956 	jp	00117$
      0092DD                       2957 00277$:
                                   2958 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 735: if (a == 0) {
      0092DD 1E 17            [ 2] 2959 	ldw	x, (0x17, sp)
      0092DF 26 1C            [ 1] 2960 	jrne	00113$
                                   2961 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 736: c = hinge(u, v, h0e);
      0092E1 1E 09            [ 2] 2962 	ldw	x, (0x09, sp)
      0092E3 89               [ 2] 2963 	pushw	x
      0092E4 1E 21            [ 2] 2964 	ldw	x, (0x21, sp)
      0092E6 89               [ 2] 2965 	pushw	x
      0092E7 1E 21            [ 2] 2966 	ldw	x, (0x21, sp)
      0092E9 CD 91 E5         [ 4] 2967 	call	_hinge
      0092EC 1F 0F            [ 2] 2968 	ldw	(0x0f, sp), x
                                   2969 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 737: it = (u < h0e && h0e <= v);
      0092EE 0D 0D            [ 1] 2970 	tnz	(0x0d, sp)
      0092F0 27 04            [ 1] 2971 	jreq	00127$
      0092F2 0D 0E            [ 1] 2972 	tnz	(0x0e, sp)
      0092F4 27 03            [ 1] 2973 	jreq	00128$
      0092F6                       2974 00127$:
      0092F6 4F               [ 1] 2975 	clr	a
      0092F7 20 61            [ 2] 2976 	jra	00114$
      0092F9                       2977 00128$:
      0092F9 A6 01            [ 1] 2978 	ld	a, #0x01
      0092FB 20 5D            [ 2] 2979 	jra	00114$
      0092FD                       2980 00113$:
                                   2981 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 739: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
      0092FD 16 17            [ 2] 2982 	ldw	y, (0x17, sp)
      0092FF 17 11            [ 2] 2983 	ldw	(0x11, sp), y
      009301 93               [ 1] 2984 	ldw	x, y
      009302 5A               [ 2] 2985 	decw	x
      009303 4F               [ 1] 2986 	clr	a
      009304 02               [ 1] 2987 	rlwa	x
      009305 58               [ 2] 2988 	sllw	x
      009306 72 FB 0B         [ 2] 2989 	addw	x, (0x0b, sp)
                                   2990 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 740: c = hinge(u, v, h);
      009309 1F 13            [ 2] 2991 	ldw	(0x13, sp), x
      00930B 89               [ 2] 2992 	pushw	x
      00930C 1E 21            [ 2] 2993 	ldw	x, (0x21, sp)
      00930E 89               [ 2] 2994 	pushw	x
      00930F 1E 21            [ 2] 2995 	ldw	x, (0x21, sp)
      009311 CD 91 E5         [ 4] 2996 	call	_hinge
      009314 1F 0F            [ 2] 2997 	ldw	(0x0f, sp), x
                                   2998 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 741: it = (u < h && h <= v);
      009316 1E 1D            [ 2] 2999 	ldw	x, (0x1d, sp)
      009318 13 13            [ 2] 3000 	cpw	x, (0x13, sp)
      00931A 2E 06            [ 1] 3001 	jrsge	00130$
      00931C 1E 13            [ 2] 3002 	ldw	x, (0x13, sp)
      00931E 13 1F            [ 2] 3003 	cpw	x, (0x1f, sp)
      009320 2D 02            [ 1] 3004 	jrsle	00131$
      009322                       3005 00130$:
      009322 4F               [ 1] 3006 	clr	a
      009323 C5                    3007 	.byte 0xc5
      009324                       3008 00131$:
      009324 A6 01            [ 1] 3009 	ld	a, #0x01
      009326                       3010 00132$:
                                   3011 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 742: if (a < L) {
      009326 1E 17            [ 2] 3012 	ldw	x, (0x17, sp)
      009328 13 05            [ 2] 3013 	cpw	x, (0x05, sp)
      00932A 2E 2E            [ 1] 3014 	jrsge	00114$
                                   3015 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 743: int16_t h2 = (int16_t)(a * BIT_U + h0e);
      00932C 02               [ 1] 3016 	rlwa	x
      00932D 7B 12            [ 1] 3017 	ld	a, (0x12, sp)
      00932F 01               [ 1] 3018 	rrwa	x
      009330 41               [ 1] 3019 	exg	a, xl
      009331 4F               [ 1] 3020 	clr	a
      009332 41               [ 1] 3021 	exg	a, xl
      009333 58               [ 2] 3022 	sllw	x
      009334 72 FB 09         [ 2] 3023 	addw	x, (0x09, sp)
      009337 1F 13            [ 2] 3024 	ldw	(0x13, sp), x
                                   3025 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 744: uint16_t c2 = hinge(u, v, h2);
      009339 88               [ 1] 3026 	push	a
      00933A 1E 14            [ 2] 3027 	ldw	x, (0x14, sp)
      00933C 89               [ 2] 3028 	pushw	x
      00933D 1E 22            [ 2] 3029 	ldw	x, (0x22, sp)
      00933F 89               [ 2] 3030 	pushw	x
      009340 1E 22            [ 2] 3031 	ldw	x, (0x22, sp)
      009342 CD 91 E5         [ 4] 3032 	call	_hinge
      009345 84               [ 1] 3033 	pop	a
                                   3034 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 745: if (c2 < c) c = c2;
      009346 13 0F            [ 2] 3035 	cpw	x, (0x0f, sp)
      009348 24 02            [ 1] 3036 	jrnc	00106$
      00934A 1F 0F            [ 2] 3037 	ldw	(0x0f, sp), x
      00934C                       3038 00106$:
                                   3039 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 746: if (u < h2 && h2 <= v) it = 1;
      00934C 1E 1D            [ 2] 3040 	ldw	x, (0x1d, sp)
      00934E 13 13            [ 2] 3041 	cpw	x, (0x13, sp)
      009350 2E 08            [ 1] 3042 	jrsge	00114$
      009352 1E 13            [ 2] 3043 	ldw	x, (0x13, sp)
      009354 13 1F            [ 2] 3044 	cpw	x, (0x1f, sp)
      009356 2C 02            [ 1] 3045 	jrsgt	00114$
      009358 A6 01            [ 1] 3046 	ld	a, #0x01
      00935A                       3047 00114$:
                                   3048 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 749: d_costs[a] = c;
      00935A 1E 17            [ 2] 3049 	ldw	x, (0x17, sp)
      00935C 58               [ 2] 3050 	sllw	x
      00935D 16 0F            [ 2] 3051 	ldw	y, (0x0f, sp)
      00935F DF 01 05         [ 2] 3052 	ldw	((_d_costs+0), x), y
                                   3053 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 750: if (it) d_inter |= (uint16_t)(1u << a);
      009362 4D               [ 1] 3054 	tnz	a
      009363 27 16            [ 1] 3055 	jreq	00122$
      009365 5F               [ 1] 3056 	clrw	x
      009366 5C               [ 1] 3057 	incw	x
      009367 7B 18            [ 1] 3058 	ld	a, (0x18, sp)
      009369 27 04            [ 1] 3059 	jreq	00289$
      00936B                       3060 00288$:
      00936B 58               [ 2] 3061 	sllw	x
      00936C 4A               [ 1] 3062 	dec	a
      00936D 26 FC            [ 1] 3063 	jrne	00288$
      00936F                       3064 00289$:
      00936F 9F               [ 1] 3065 	ld	a, xl
      009370 CA 01 26         [ 1] 3066 	or	a, _d_inter+1
      009373 02               [ 1] 3067 	rlwa	x
      009374 CA 01 25         [ 1] 3068 	or	a, _d_inter+0
      009377 95               [ 1] 3069 	ld	xh, a
      009378 CF 01 25         [ 2] 3070 	ldw	_d_inter+0, x
      00937B                       3071 00122$:
                                   3072 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
      00937B 1E 17            [ 2] 3073 	ldw	x, (0x17, sp)
      00937D 5C               [ 1] 3074 	incw	x
      00937E 1F 17            [ 2] 3075 	ldw	(0x17, sp), x
      009380 CC 92 D4         [ 2] 3076 	jp	00121$
      009383                       3077 00117$:
                                   3078 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 753: *a_free = argmin_ab(0, acap);
      009383 1E 24            [ 2] 3079 	ldw	x, (0x24, sp)
      009385 89               [ 2] 3080 	pushw	x
      009386 16 09            [ 2] 3081 	ldw	y, (0x09, sp)
      009388 90 89            [ 2] 3082 	pushw	y
      00938A 5F               [ 1] 3083 	clrw	x
      00938B CD 92 05         [ 4] 3084 	call	_argmin_ab
      00938E 51               [ 1] 3085 	exgw	x, y
      00938F 85               [ 2] 3086 	popw	x
      009390 FF               [ 2] 3087 	ldw	(x), y
                                   3088 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 754: a_bounds(k0, k1, &amin, &amax);
      009391 96               [ 1] 3089 	ldw	x, sp
      009392 1C 00 03         [ 2] 3090 	addw	x, #3
      009395 89               [ 2] 3091 	pushw	x
      009396 96               [ 1] 3092 	ldw	x, sp
      009397 1C 00 03         [ 2] 3093 	addw	x, #3
      00939A 89               [ 2] 3094 	pushw	x
      00939B 1E 1F            [ 2] 3095 	ldw	x, (0x1f, sp)
      00939D 89               [ 2] 3096 	pushw	x
      00939E 1E 1B            [ 2] 3097 	ldw	x, (0x1b, sp)
      0093A0 CD 8A B3         [ 4] 3098 	call	_a_bounds
                                   3099 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 755: lo = (amin > 0) ? amin : 0;
      0093A3 1E 01            [ 2] 3100 	ldw	x, (0x01, sp)
      0093A5 A3 00 00         [ 2] 3101 	cpw	x, #0x0000
      0093A8 2C 01            [ 1] 3102 	jrsgt	00134$
      0093AA 5F               [ 1] 3103 	clrw	x
      0093AB                       3104 00134$:
      0093AB 1F 13            [ 2] 3105 	ldw	(0x13, sp), x
                                   3106 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 756: hi = (amax < acap) ? amax : acap;
      0093AD 1E 03            [ 2] 3107 	ldw	x, (0x03, sp)
      0093AF 13 07            [ 2] 3108 	cpw	x, (0x07, sp)
      0093B1 2E 03            [ 1] 3109 	jrsge	00135$
      0093B3 1E 03            [ 2] 3110 	ldw	x, (0x03, sp)
      0093B5 C5                    3111 	.byte 0xc5
      0093B6                       3112 00135$:
      0093B6 1E 07            [ 2] 3113 	ldw	x, (0x07, sp)
      0093B8                       3114 00136$:
      0093B8 1F 17            [ 2] 3115 	ldw	(0x17, sp), x
                                   3116 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 757: if (lo > hi) { lo = 0; hi = acap; }
      0093BA 1E 13            [ 2] 3117 	ldw	x, (0x13, sp)
      0093BC 13 17            [ 2] 3118 	cpw	x, (0x17, sp)
      0093BE 2D 07            [ 1] 3119 	jrsle	00119$
      0093C0 5F               [ 1] 3120 	clrw	x
      0093C1 1F 13            [ 2] 3121 	ldw	(0x13, sp), x
      0093C3 16 07            [ 2] 3122 	ldw	y, (0x07, sp)
      0093C5 17 17            [ 2] 3123 	ldw	(0x17, sp), y
      0093C7                       3124 00119$:
                                   3125 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: *a_hat = argmin_ab(lo, hi);
      0093C7 1E 22            [ 2] 3126 	ldw	x, (0x22, sp)
      0093C9 89               [ 2] 3127 	pushw	x
      0093CA 16 19            [ 2] 3128 	ldw	y, (0x19, sp)
      0093CC 90 89            [ 2] 3129 	pushw	y
      0093CE 1E 17            [ 2] 3130 	ldw	x, (0x17, sp)
      0093D0 CD 92 05         [ 4] 3131 	call	_argmin_ab
      0093D3 51               [ 1] 3132 	exgw	x, y
      0093D4 85               [ 2] 3133 	popw	x
      0093D5 FF               [ 2] 3134 	ldw	(x), y
                                   3135 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 759: *lo_out = lo; *hi_out = hi;
      0093D6 1E 26            [ 2] 3136 	ldw	x, (0x26, sp)
      0093D8 16 13            [ 2] 3137 	ldw	y, (0x13, sp)
      0093DA FF               [ 2] 3138 	ldw	(x), y
      0093DB 1E 28            [ 2] 3139 	ldw	x, (0x28, sp)
      0093DD 16 17            [ 2] 3140 	ldw	y, (0x17, sp)
      0093DF FF               [ 2] 3141 	ldw	(x), y
                                   3142 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 760: return acap;
      0093E0 1E 07            [ 2] 3143 	ldw	x, (0x07, sp)
                                   3144 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 761: }
      0093E2 16 19            [ 2] 3145 	ldw	y, (25, sp)
      0093E4 5B 29            [ 2] 3146 	addw	sp, #41
      0093E6 90 FC            [ 2] 3147 	jp	(y)
                                   3148 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 764: static void cand_insert(uint16_t k, uint8_t m)
                                   3149 ;	-----------------------------------------
                                   3150 ;	 function cand_insert
                                   3151 ;	-----------------------------------------
      0093E8                       3152 _cand_insert:
      0093E8 52 07            [ 2] 3153 	sub	sp, #7
      0093EA 1F 05            [ 2] 3154 	ldw	(0x05, sp), x
      0093EC 6B 04            [ 1] 3155 	ld	(0x04, sp), a
                                   3156 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 766: uint8_t i = v_ncand, j;
      0093EE C6 01 36         [ 1] 3157 	ld	a, _v_ncand+0
                                   3158 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 767: while (i > 0 && v_cand_m[i - 1] > m) i--;
      0093F1 6B 07            [ 1] 3159 	ld	(0x07, sp), a
      0093F3                       3160 00102$:
      0093F3 4D               [ 1] 3161 	tnz	a
      0093F4 27 17            [ 1] 3162 	jreq	00132$
      0093F6 97               [ 1] 3163 	ld	xl, a
      0093F7 5A               [ 2] 3164 	decw	x
      0093F8 88               [ 1] 3165 	push	a
      0093F9 9F               [ 1] 3166 	ld	a, xl
      0093FA 49               [ 1] 3167 	rlc	a
      0093FB 4F               [ 1] 3168 	clr	a
      0093FC A2 00            [ 1] 3169 	sbc	a, #0x00
      0093FE 95               [ 1] 3170 	ld	xh, a
      0093FF 84               [ 1] 3171 	pop	a
      009400 1C 01 31         [ 2] 3172 	addw	x, #(_v_cand_m+0)
      009403 88               [ 1] 3173 	push	a
      009404 F6               [ 1] 3174 	ld	a, (x)
      009405 11 05            [ 1] 3175 	cp	a, (0x05, sp)
      009407 84               [ 1] 3176 	pop	a
      009408 23 03            [ 2] 3177 	jrule	00132$
      00940A 4A               [ 1] 3178 	dec	a
      00940B 20 E6            [ 2] 3179 	jra	00102$
      00940D                       3180 00132$:
      00940D 6B 01            [ 1] 3181 	ld	(0x01, sp), a
                                   3182 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 768: if (i >= A_MAX) return;
      00940F A1 05            [ 1] 3183 	cp	a, #0x05
      009411 24 60            [ 1] 3184 	jrnc	00112$
                                   3185 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 769: j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
      009413 C6 01 36         [ 1] 3186 	ld	a, _v_ncand+0
      009416 A1 05            [ 1] 3187 	cp	a, #0x05
      009418 24 03            [ 1] 3188 	jrnc	00114$
      00941A 7B 07            [ 1] 3189 	ld	a, (0x07, sp)
      00941C C5                    3190 	.byte 0xc5
      00941D                       3191 00114$:
      00941D A6 04            [ 1] 3192 	ld	a, #0x04
      00941F                       3193 00115$:
      00941F 6B 07            [ 1] 3194 	ld	(0x07, sp), a
                                   3195 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 770: while (j > i) {
      009421                       3196 00107$:
                                   3197 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 771: v_cand_t[j] = v_cand_t[j - 1];
      009421 7B 07            [ 1] 3198 	ld	a, (0x07, sp)
      009423 11 01            [ 1] 3199 	cp	a, (0x01, sp)
      009425 23 2E            [ 2] 3200 	jrule	00109$
      009427 5F               [ 1] 3201 	clrw	x
      009428 97               [ 1] 3202 	ld	xl, a
      009429 58               [ 2] 3203 	sllw	x
      00942A 1C 01 27         [ 2] 3204 	addw	x, #(_v_cand_t+0)
      00942D 51               [ 1] 3205 	exgw	x, y
      00942E 7B 07            [ 1] 3206 	ld	a, (0x07, sp)
      009430 4A               [ 1] 3207 	dec	a
      009431 6B 03            [ 1] 3208 	ld	(0x03, sp), a
      009433 49               [ 1] 3209 	rlc	a
      009434 4F               [ 1] 3210 	clr	a
      009435 A2 00            [ 1] 3211 	sbc	a, #0x00
      009437 6B 02            [ 1] 3212 	ld	(0x02, sp), a
      009439 1E 02            [ 2] 3213 	ldw	x, (0x02, sp)
      00943B 58               [ 2] 3214 	sllw	x
      00943C DE 01 27         [ 2] 3215 	ldw	x, (_v_cand_t+0, x)
      00943F 90 FF            [ 2] 3216 	ldw	(y), x
                                   3217 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 772: v_cand_m[j] = v_cand_m[j - 1];
      009441 5F               [ 1] 3218 	clrw	x
      009442 7B 07            [ 1] 3219 	ld	a, (0x07, sp)
      009444 97               [ 1] 3220 	ld	xl, a
      009445 1C 01 31         [ 2] 3221 	addw	x, #(_v_cand_m+0)
      009448 16 02            [ 2] 3222 	ldw	y, (0x02, sp)
      00944A 72 A9 01 31      [ 2] 3223 	addw	y, #(_v_cand_m+0)
      00944E 90 F6            [ 1] 3224 	ld	a, (y)
      009450 F7               [ 1] 3225 	ld	(x), a
                                   3226 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 773: j--;
      009451 0A 07            [ 1] 3227 	dec	(0x07, sp)
      009453 20 CC            [ 2] 3228 	jra	00107$
      009455                       3229 00109$:
                                   3230 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 775: v_cand_t[i] = k;
      009455 7B 01            [ 1] 3231 	ld	a, (0x01, sp)
      009457 5F               [ 1] 3232 	clrw	x
      009458 97               [ 1] 3233 	ld	xl, a
      009459 58               [ 2] 3234 	sllw	x
      00945A 16 05            [ 2] 3235 	ldw	y, (0x05, sp)
      00945C DF 01 27         [ 2] 3236 	ldw	((_v_cand_t+0), x), y
                                   3237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 776: v_cand_m[i] = m;
      00945F 5F               [ 1] 3238 	clrw	x
      009460 7B 01            [ 1] 3239 	ld	a, (0x01, sp)
      009462 97               [ 1] 3240 	ld	xl, a
      009463 7B 04            [ 1] 3241 	ld	a, (0x04, sp)
      009465 D7 01 31         [ 1] 3242 	ld	((_v_cand_m+0), x), a
                                   3243 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 777: if (v_ncand < A_MAX) v_ncand++;
      009468 C6 01 36         [ 1] 3244 	ld	a, _v_ncand+0
      00946B A1 05            [ 1] 3245 	cp	a, #0x05
      00946D 24 04            [ 1] 3246 	jrnc	00112$
      00946F 72 5C 01 36      [ 1] 3247 	inc	_v_ncand+0
      009473                       3248 00112$:
                                   3249 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 778: }
      009473 5B 07            [ 2] 3250 	addw	sp, #7
      009475 81               [ 4] 3251 	ret
                                   3252 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 780: static void decide_pass(void)
                                   3253 ;	-----------------------------------------
                                   3254 ;	 function decide_pass
                                   3255 ;	-----------------------------------------
      009476                       3256 _decide_pass:
      009476 52 21            [ 2] 3257 	sub	sp, #33
                                   3258 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 784: for (t = 0; t < NBB; t++) d_bits[t] = 0;
      009478 4F               [ 1] 3259 	clr	a
      009479                       3260 00168$:
      009479 5F               [ 1] 3261 	clrw	x
      00947A 97               [ 1] 3262 	ld	xl, a
      00947B 72 4F 00 E4      [ 1] 3263 	clr	((_d_bits+0), x)
      00947F 4C               [ 1] 3264 	inc	a
      009480 A1 1B            [ 1] 3265 	cp	a, #0x1b
      009482 25 F5            [ 1] 3266 	jrc	00168$
                                   3267 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 785: d_infeas = 0; d_laberr = 0; d_nseg = 0;
      009484 5F               [ 1] 3268 	clrw	x
      009485 CF 00 FF         [ 2] 3269 	ldw	_d_infeas+0, x
      009488 5F               [ 1] 3270 	clrw	x
      009489 CF 01 01         [ 2] 3271 	ldw	_d_laberr+0, x
      00948C 5F               [ 1] 3272 	clrw	x
      00948D CF 01 03         [ 2] 3273 	ldw	_d_nseg+0, x
                                   3274 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 786: v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1;
      009490 72 5F 01 36      [ 1] 3275 	clr	_v_ncand+0
      009494 5F               [ 1] 3276 	clrw	x
      009495 CF 01 37         [ 2] 3277 	ldw	_v_nweak+0, x
      009498 5F               [ 1] 3278 	clrw	x
      009499 CF 01 39         [ 2] 3279 	ldw	_v_ntied+0, x
      00949C 5F               [ 1] 3280 	clrw	x
      00949D 5A               [ 2] 3281 	decw	x
      00949E CF 01 3B         [ 2] 3282 	ldw	_v_tiepend+0, x
                                   3283 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 787: ss_init();
      0094A1 CD 88 43         [ 4] 3284 	call	_ss_init
                                   3285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 788: while (ss_next(&sg)) {
      0094A4                       3286 00165$:
      0094A4 96               [ 1] 3287 	ldw	x, sp
      0094A5 5C               [ 1] 3288 	incw	x
      0094A6 CD 88 85         [ 4] 3289 	call	_ss_next
      0094A9 4D               [ 1] 3290 	tnz	a
      0094AA 26 03            [ 1] 3291 	jrne	00557$
      0094AC CC 96 E0         [ 2] 3292 	jp	00185$
      0094AF                       3293 00557$:
                                   3294 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 791: int16_t tie_here = -1, ins0 = -1, ins1 = -1;
      0094AF 5F               [ 1] 3295 	clrw	x
      0094B0 5A               [ 2] 3296 	decw	x
      0094B1 1F 12            [ 2] 3297 	ldw	(0x12, sp), x
      0094B3 5F               [ 1] 3298 	clrw	x
      0094B4 5A               [ 2] 3299 	decw	x
      0094B5 1F 19            [ 2] 3300 	ldw	(0x19, sp), x
      0094B7 5F               [ 1] 3301 	clrw	x
      0094B8 5A               [ 2] 3302 	decw	x
      0094B9 1F 1B            [ 2] 3303 	ldw	(0x1b, sp), x
                                   3304 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 794: d_nseg++;
      0094BB CE 01 03         [ 2] 3305 	ldw	x, _d_nseg+0
      0094BE 5C               [ 1] 3306 	incw	x
      0094BF CF 01 03         [ 2] 3307 	ldw	_d_nseg+0, x
                                   3308 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
      0094C2 96               [ 1] 3309 	ldw	x, sp
      0094C3 5C               [ 1] 3310 	incw	x
      0094C4 1F 14            [ 2] 3311 	ldw	(0x14, sp), x
      0094C6 FE               [ 2] 3312 	ldw	x, (x)
      0094C7 1F 17            [ 2] 3313 	ldw	(0x17, sp), x
      0094C9 A3 00 D8         [ 2] 3314 	cpw	x, #0x00d8
      0094CC 24 D6            [ 1] 3315 	jrnc	00165$
                                   3316 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 797: &a_hat, &a_free, &lo, &hi);
                                   3317 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 796: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
      0094CE 7B 09            [ 1] 3318 	ld	a, (0x09, sp)
      0094D0 16 07            [ 2] 3319 	ldw	y, (0x07, sp)
      0094D2 17 1E            [ 2] 3320 	ldw	(0x1e, sp), y
      0094D4 16 05            [ 2] 3321 	ldw	y, (0x05, sp)
      0094D6 17 20            [ 2] 3322 	ldw	(0x20, sp), y
      0094D8 16 03            [ 2] 3323 	ldw	y, (0x03, sp)
      0094DA 96               [ 1] 3324 	ldw	x, sp
      0094DB 1C 00 10         [ 2] 3325 	addw	x, #16
      0094DE 89               [ 2] 3326 	pushw	x
      0094DF 96               [ 1] 3327 	ldw	x, sp
      0094E0 1C 00 10         [ 2] 3328 	addw	x, #16
      0094E3 89               [ 2] 3329 	pushw	x
      0094E4 96               [ 1] 3330 	ldw	x, sp
      0094E5 1C 00 10         [ 2] 3331 	addw	x, #16
      0094E8 89               [ 2] 3332 	pushw	x
      0094E9 96               [ 1] 3333 	ldw	x, sp
      0094EA 1C 00 10         [ 2] 3334 	addw	x, #16
      0094ED 89               [ 2] 3335 	pushw	x
      0094EE 88               [ 1] 3336 	push	a
      0094EF 1E 27            [ 2] 3337 	ldw	x, (0x27, sp)
      0094F1 89               [ 2] 3338 	pushw	x
      0094F2 1E 2B            [ 2] 3339 	ldw	x, (0x2b, sp)
      0094F4 89               [ 2] 3340 	pushw	x
      0094F5 90 89            [ 2] 3341 	pushw	y
      0094F7 1E 26            [ 2] 3342 	ldw	x, (0x26, sp)
      0094F9 CD 92 54         [ 4] 3343 	call	_decide
      0094FC 1F 1D            [ 2] 3344 	ldw	(0x1d, sp), x
                                   3345 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 798: c_hat = d_costs[a_hat];
      0094FE 1E 0A            [ 2] 3346 	ldw	x, (0x0a, sp)
      009500 58               [ 2] 3347 	sllw	x
      009501 DE 01 05         [ 2] 3348 	ldw	x, (_d_costs+0, x)
                                   3349 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 799: if (c_hat > INFEAS_U) d_infeas++;
      009504 A3 00 A0         [ 2] 3350 	cpw	x, #0x00a0
      009507 23 07            [ 2] 3351 	jrule	00105$
      009509 CE 00 FF         [ 2] 3352 	ldw	x, _d_infeas+0
      00950C 5C               [ 1] 3353 	incw	x
      00950D CF 00 FF         [ 2] 3354 	ldw	_d_infeas+0, x
      009510                       3355 00105$:
                                   3356 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: kk1 = (sg.k1 < NB) ? sg.k1 : NB;
      009510 1E 03            [ 2] 3357 	ldw	x, (0x03, sp)
      009512 A3 00 D8         [ 2] 3358 	cpw	x, #0x00d8
      009515 24 03            [ 1] 3359 	jrnc	00187$
      009517 9F               [ 1] 3360 	ld	a, xl
      009518 20 03            [ 2] 3361 	jra	00188$
      00951A                       3362 00187$:
      00951A A6 D8            [ 1] 3363 	ld	a, #0xd8
      00951C 5F               [ 1] 3364 	clrw	x
      00951D                       3365 00188$:
      00951D 6B 17            [ 1] 3366 	ld	(0x17, sp), a
      00951F 02               [ 1] 3367 	rlwa	x
      009520 6B 16            [ 1] 3368 	ld	(0x16, sp), a
      009522 01               [ 1] 3369 	rrwa	x
                                   3370 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 801: known_all = 1;
      009523 A6 01            [ 1] 3371 	ld	a, #0x01
      009525 6B 1F            [ 1] 3372 	ld	(0x1f, sp), a
                                   3373 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
      009527 1E 14            [ 2] 3374 	ldw	x, (0x14, sp)
      009529 FE               [ 2] 3375 	ldw	x, (x)
      00952A                       3376 00171$:
      00952A 13 16            [ 2] 3377 	cpw	x, (0x16, sp)
      00952C 24 0F            [ 1] 3378 	jrnc	00108$
                                   3379 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 803: if (known_bit(t) < 0) { known_all = 0; break; }
      00952E 89               [ 2] 3380 	pushw	x
      00952F CD 81 C6         [ 4] 3381 	call	_known_bit
      009532 85               [ 2] 3382 	popw	x
      009533 4D               [ 1] 3383 	tnz	a
      009534 2A 04            [ 1] 3384 	jrpl	00172$
      009536 0F 1F            [ 1] 3385 	clr	(0x1f, sp)
      009538 20 03            [ 2] 3386 	jra	00108$
      00953A                       3387 00172$:
                                   3388 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
      00953A 5C               [ 1] 3389 	incw	x
      00953B 20 ED            [ 2] 3390 	jra	00171$
      00953D                       3391 00108$:
                                   3392 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 804: dead = 0; nins = 0;
      00953D 0F 20            [ 1] 3393 	clr	(0x20, sp)
                                   3394 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
      00953F 0F 21            [ 1] 3395 	clr	(0x21, sp)
      009541 5F               [ 1] 3396 	clrw	x
      009542                       3397 00174$:
      009542 13 1D            [ 2] 3398 	cpw	x, (0x1d, sp)
      009544 2C 16            [ 1] 3399 	jrsgt	00111$
                                   3400 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 806: if ((d_inter >> a) & 1) nins++;
      009546 90 CE 01 25      [ 2] 3401 	ldw	y, _d_inter+0
      00954A 9F               [ 1] 3402 	ld	a, xl
      00954B 4D               [ 1] 3403 	tnz	a
      00954C 27 05            [ 1] 3404 	jreq	00565$
      00954E                       3405 00564$:
      00954E 90 54            [ 2] 3406 	srlw	y
      009550 4A               [ 1] 3407 	dec	a
      009551 26 FB            [ 1] 3408 	jrne	00564$
      009553                       3409 00565$:
      009553 90 54            [ 2] 3410 	srlw	y
      009555 24 02            [ 1] 3411 	jrnc	00175$
      009557 0C 21            [ 1] 3412 	inc	(0x21, sp)
      009559                       3413 00175$:
                                   3414 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
      009559 5C               [ 1] 3415 	incw	x
      00955A 20 E6            [ 2] 3416 	jra	00174$
      00955C                       3417 00111$:
                                   3418 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: if (nins >= 2) dead = 1;
      00955C 7B 21            [ 1] 3419 	ld	a, (0x21, sp)
      00955E A1 02            [ 1] 3420 	cp	a, #0x02
      009560 25 04            [ 1] 3421 	jrc	00113$
      009562 A6 01            [ 1] 3422 	ld	a, #0x01
      009564 6B 20            [ 1] 3423 	ld	(0x20, sp), a
      009566                       3424 00113$:
                                   3425 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 808: if (known_all && lo == hi && a_free != lo && !dead)
      009566 0D 1F            [ 1] 3426 	tnz	(0x1f, sp)
      009568 27 17            [ 1] 3427 	jreq	00115$
      00956A 1E 0E            [ 2] 3428 	ldw	x, (0x0e, sp)
      00956C 13 10            [ 2] 3429 	cpw	x, (0x10, sp)
      00956E 26 11            [ 1] 3430 	jrne	00115$
      009570 1E 0C            [ 2] 3431 	ldw	x, (0x0c, sp)
      009572 13 0E            [ 2] 3432 	cpw	x, (0x0e, sp)
      009574 27 0B            [ 1] 3433 	jreq	00115$
      009576 0D 20            [ 1] 3434 	tnz	(0x20, sp)
      009578 26 07            [ 1] 3435 	jrne	00115$
                                   3436 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 809: d_laberr++;
      00957A CE 01 01         [ 2] 3437 	ldw	x, _d_laberr+0
      00957D 5C               [ 1] 3438 	incw	x
      00957E CF 01 01         [ 2] 3439 	ldw	_d_laberr+0, x
      009581                       3440 00115$:
                                   3441 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
      009581 1E 0E            [ 2] 3442 	ldw	x, (0x0e, sp)
      009583 0F 1F            [ 1] 3443 	clr	(0x1f, sp)
      009585                       3444 00177$:
      009585 13 10            [ 2] 3445 	cpw	x, (0x10, sp)
      009587 2C 25            [ 1] 3446 	jrsgt	00126$
                                   3447 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 815: if ((d_inter >> a) & 1) {
      009589 90 CE 01 25      [ 2] 3448 	ldw	y, _d_inter+0
      00958D 9F               [ 1] 3449 	ld	a, xl
      00958E 4D               [ 1] 3450 	tnz	a
      00958F 27 05            [ 1] 3451 	jreq	00578$
      009591                       3452 00577$:
      009591 90 54            [ 2] 3453 	srlw	y
      009593 4A               [ 1] 3454 	dec	a
      009594 26 FB            [ 1] 3455 	jrne	00577$
      009596                       3456 00578$:
      009596 90 54            [ 2] 3457 	srlw	y
      009598 24 11            [ 1] 3458 	jrnc	00178$
                                   3459 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 816: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
      00959A 0D 1F            [ 1] 3460 	tnz	(0x1f, sp)
      00959C 26 04            [ 1] 3461 	jrne	00122$
      00959E 1F 19            [ 2] 3462 	ldw	(0x19, sp), x
      0095A0 20 07            [ 2] 3463 	jra	00123$
      0095A2                       3464 00122$:
      0095A2 7B 1F            [ 1] 3465 	ld	a, (0x1f, sp)
      0095A4 4A               [ 1] 3466 	dec	a
      0095A5 26 02            [ 1] 3467 	jrne	00123$
      0095A7 1F 1B            [ 2] 3468 	ldw	(0x1b, sp), x
      0095A9                       3469 00123$:
                                   3470 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 817: nins++;
      0095A9 0C 1F            [ 1] 3471 	inc	(0x1f, sp)
      0095AB                       3472 00178$:
                                   3473 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
      0095AB 5C               [ 1] 3474 	incw	x
      0095AC 20 D7            [ 2] 3475 	jra	00177$
      0095AE                       3476 00126$:
                                   3477 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
      0095AE 1E 14            [ 2] 3478 	ldw	x, (0x14, sp)
      0095B0 FE               [ 2] 3479 	ldw	x, (x)
      0095B1 1F 20            [ 2] 3480 	ldw	(0x20, sp), x
                                   3481 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 820: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
      0095B3 7B 1F            [ 1] 3482 	ld	a, (0x1f, sp)
      0095B5 A1 02            [ 1] 3483 	cp	a, #0x02
      0095B7 25 18            [ 1] 3484 	jrc	00130$
      0095B9 1E 0A            [ 2] 3485 	ldw	x, (0x0a, sp)
      0095BB 13 19            [ 2] 3486 	cpw	x, (0x19, sp)
      0095BD 27 06            [ 1] 3487 	jreq	00129$
      0095BF 1E 0A            [ 2] 3488 	ldw	x, (0x0a, sp)
      0095C1 13 1B            [ 2] 3489 	cpw	x, (0x1b, sp)
      0095C3 26 0C            [ 1] 3490 	jrne	00130$
      0095C5                       3491 00129$:
                                   3492 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 821: uint16_t tt = (uint16_t)(sg.k0 + ins0);
      0095C5 1E 19            [ 2] 3493 	ldw	x, (0x19, sp)
      0095C7 72 FB 20         [ 2] 3494 	addw	x, (0x20, sp)
                                   3495 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 822: if (tt < NB) tie_here = (int16_t)tt;
      0095CA A3 00 D8         [ 2] 3496 	cpw	x, #0x00d8
      0095CD 24 02            [ 1] 3497 	jrnc	00130$
      0095CF 1F 12            [ 2] 3498 	ldw	(0x12, sp), x
      0095D1                       3499 00130$:
                                   3500 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
      0095D1 16 20            [ 2] 3501 	ldw	y, (0x20, sp)
      0095D3 17 1E            [ 2] 3502 	ldw	(0x1e, sp), y
      0095D5                       3503 00183$:
      0095D5 1E 1E            [ 2] 3504 	ldw	x, (0x1e, sp)
      0095D7 13 16            [ 2] 3505 	cpw	x, (0x16, sp)
      0095D9 25 03            [ 1] 3506 	jrc	00592$
      0095DB CC 96 B9         [ 2] 3507 	jp	00159$
      0095DE                       3508 00592$:
                                   3509 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 826: int16_t off = (int16_t)(t - sg.k0);
      0095DE 1E 14            [ 2] 3510 	ldw	x, (0x14, sp)
      0095E0 FE               [ 2] 3511 	ldw	x, (x)
      0095E1 50               [ 2] 3512 	negw	x
      0095E2 72 FB 1E         [ 2] 3513 	addw	x, (0x1e, sp)
      0095E5 1F 18            [ 2] 3514 	ldw	(0x18, sp), x
                                   3515 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 827: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
      0095E7 5F               [ 1] 3516 	clrw	x
      0095E8 5A               [ 2] 3517 	decw	x
      0095E9 1F 1A            [ 2] 3518 	ldw	(0x1a, sp), x
      0095EB 5F               [ 1] 3519 	clrw	x
      0095EC 5A               [ 2] 3520 	decw	x
      0095ED 1F 1C            [ 2] 3521 	ldw	(0x1c, sp), x
                                   3522 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 828: if (off < a_hat) BSET(d_bits, t);
      0095EF 1E 18            [ 2] 3523 	ldw	x, (0x18, sp)
      0095F1 13 0A            [ 2] 3524 	cpw	x, (0x0a, sp)
      0095F3 2E 21            [ 1] 3525 	jrsge	00134$
      0095F5 1E 1E            [ 2] 3526 	ldw	x, (0x1e, sp)
      0095F7 54               [ 2] 3527 	srlw	x
      0095F8 54               [ 2] 3528 	srlw	x
      0095F9 54               [ 2] 3529 	srlw	x
      0095FA 1C 00 E4         [ 2] 3530 	addw	x, #(_d_bits+0)
      0095FD F6               [ 1] 3531 	ld	a, (x)
      0095FE 6B 20            [ 1] 3532 	ld	(0x20, sp), a
      009600 7B 1F            [ 1] 3533 	ld	a, (0x1f, sp)
      009602 A4 07            [ 1] 3534 	and	a, #0x07
      009604 6B 21            [ 1] 3535 	ld	(0x21, sp), a
      009606 A6 01            [ 1] 3536 	ld	a, #0x01
      009608 88               [ 1] 3537 	push	a
      009609 7B 22            [ 1] 3538 	ld	a, (0x22, sp)
      00960B 27 05            [ 1] 3539 	jreq	00595$
      00960D                       3540 00594$:
      00960D 08 01            [ 1] 3541 	sll	(1, sp)
      00960F 4A               [ 1] 3542 	dec	a
      009610 26 FB            [ 1] 3543 	jrne	00594$
      009612                       3544 00595$:
      009612 84               [ 1] 3545 	pop	a
      009613 1A 20            [ 1] 3546 	or	a, (0x20, sp)
      009615 F7               [ 1] 3547 	ld	(x), a
      009616                       3548 00134$:
                                   3549 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
      009616 16 0E            [ 2] 3550 	ldw	y, (0x0e, sp)
      009618 17 20            [ 2] 3551 	ldw	(0x20, sp), y
      00961A                       3552 00180$:
      00961A 1E 20            [ 2] 3553 	ldw	x, (0x20, sp)
      00961C 13 10            [ 2] 3554 	cpw	x, (0x10, sp)
      00961E 2C 23            [ 1] 3555 	jrsgt	00142$
                                   3556 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
      009620 1E 20            [ 2] 3557 	ldw	x, (0x20, sp)
      009622 58               [ 2] 3558 	sllw	x
      009623 DE 01 05         [ 2] 3559 	ldw	x, (_d_costs+0, x)
      009626 89               [ 2] 3560 	pushw	x
      009627 1E 22            [ 2] 3561 	ldw	x, (0x22, sp)
      009629 13 1A            [ 2] 3562 	cpw	x, (0x1a, sp)
      00962B 85               [ 2] 3563 	popw	x
      00962C 2D 08            [ 1] 3564 	jrsle	00140$
      00962E 13 1C            [ 2] 3565 	cpw	x, (0x1c, sp)
      009630 24 0A            [ 1] 3566 	jrnc	00181$
      009632 1F 1C            [ 2] 3567 	ldw	(0x1c, sp), x
      009634 20 06            [ 2] 3568 	jra	00181$
      009636                       3569 00140$:
                                   3570 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 831: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
      009636 13 1A            [ 2] 3571 	cpw	x, (0x1a, sp)
      009638 24 02            [ 1] 3572 	jrnc	00181$
      00963A 1F 1A            [ 2] 3573 	ldw	(0x1a, sp), x
      00963C                       3574 00181$:
                                   3575 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
      00963C 1E 20            [ 2] 3576 	ldw	x, (0x20, sp)
      00963E 5C               [ 1] 3577 	incw	x
      00963F 1F 20            [ 2] 3578 	ldw	(0x20, sp), x
      009641 20 D7            [ 2] 3579 	jra	00180$
      009643                       3580 00142$:
                                   3581 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 833: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
      009643 1E 1A            [ 2] 3582 	ldw	x, (0x1a, sp)
      009645 5C               [ 1] 3583 	incw	x
      009646 27 05            [ 1] 3584 	jreq	00145$
      009648 1E 1C            [ 2] 3585 	ldw	x, (0x1c, sp)
      00964A 5C               [ 1] 3586 	incw	x
      00964B 26 07            [ 1] 3587 	jrne	00146$
      00964D                       3588 00145$:
      00964D AE 00 FF         [ 2] 3589 	ldw	x, #0x00ff
      009650 1F 20            [ 2] 3590 	ldw	(0x20, sp), x
      009652 20 1A            [ 2] 3591 	jra	00147$
      009654                       3592 00146$:
                                   3593 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 835: int16_t dm = (int16_t)(c0m - c1m);
      009654 1E 1A            [ 2] 3594 	ldw	x, (0x1a, sp)
      009656 72 F0 1C         [ 2] 3595 	subw	x, (0x1c, sp)
                                   3596 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 836: if (dm < 0) dm = (int16_t)-dm;
      009659 1F 20            [ 2] 3597 	ldw	(0x20, sp), x
      00965B 5D               [ 2] 3598 	tnzw	x
      00965C 2A 07            [ 1] 3599 	jrpl	00144$
      00965E 00 21            [ 1] 3600 	neg	(0x21, sp)
      009660 4F               [ 1] 3601 	clr	a
      009661 12 20            [ 1] 3602 	sbc	a, (0x20, sp)
      009663 6B 20            [ 1] 3603 	ld	(0x20, sp), a
      009665                       3604 00144$:
                                   3605 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 837: m = (dm > 255) ? 255 : (uint16_t)dm;
      009665 AE 00 FF         [ 2] 3606 	ldw	x, #0x00ff
      009668 13 20            [ 2] 3607 	cpw	x, (0x20, sp)
      00966A 2C 02            [ 1] 3608 	jrsgt	00189$
      00966C 1F 20            [ 2] 3609 	ldw	(0x20, sp), x
      00966E                       3610 00189$:
      00966E                       3611 00147$:
                                   3612 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 839: if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
      00966E 1E 1E            [ 2] 3613 	ldw	x, (0x1e, sp)
      009670 13 12            [ 2] 3614 	cpw	x, (0x12, sp)
      009672 27 05            [ 1] 3615 	jreq	00149$
      009674 C3 01 3B         [ 2] 3616 	cpw	x, _v_tiepend+0
      009677 26 03            [ 1] 3617 	jrne	00150$
      009679                       3618 00149$:
                                   3619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 840: m = 0;                       /* decided by tie-break */
      009679 5F               [ 1] 3620 	clrw	x
      00967A 1F 20            [ 2] 3621 	ldw	(0x20, sp), x
      00967C                       3622 00150$:
                                   3623 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 841: if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
      00967C 1E 1E            [ 2] 3624 	ldw	x, (0x1e, sp)
      00967E A3 00 20         [ 2] 3625 	cpw	x, #0x0020
      009681 25 2E            [ 1] 3626 	jrc	00184$
      009683 16 1E            [ 2] 3627 	ldw	y, (0x1e, sp)
      009685 90 A3 00 B8      [ 2] 3628 	cpw	y, #0x00b8
      009689 24 26            [ 1] 3629 	jrnc	00184$
                                   3630 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 842: if (m <= MG_MAX) {
      00968B 16 20            [ 2] 3631 	ldw	y, (0x20, sp)
      00968D 90 A3 00 08      [ 2] 3632 	cpw	y, #0x0008
      009691 22 1E            [ 1] 3633 	jrugt	00184$
                                   3634 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 843: uint16_t k = t - PP_LO;
      009693 1D 00 20         [ 2] 3635 	subw	x, #0x0020
      009696 1F 1C            [ 2] 3636 	ldw	(0x1c, sp), x
                                   3637 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 844: v_nweak++;
      009698 CE 01 37         [ 2] 3638 	ldw	x, _v_nweak+0
      00969B 5C               [ 1] 3639 	incw	x
      00969C CF 01 37         [ 2] 3640 	ldw	_v_nweak+0, x
                                   3641 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 845: if (m == 0) v_ntied++;
      00969F 1E 20            [ 2] 3642 	ldw	x, (0x20, sp)
      0096A1 26 07            [ 1] 3643 	jrne	00153$
      0096A3 CE 01 39         [ 2] 3644 	ldw	x, _v_ntied+0
      0096A6 5C               [ 1] 3645 	incw	x
      0096A7 CF 01 39         [ 2] 3646 	ldw	_v_ntied+0, x
      0096AA                       3647 00153$:
                                   3648 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 846: cand_insert(k, (uint8_t)m);
      0096AA 7B 21            [ 1] 3649 	ld	a, (0x21, sp)
      0096AC 1E 1C            [ 2] 3650 	ldw	x, (0x1c, sp)
      0096AE CD 93 E8         [ 4] 3651 	call	_cand_insert
      0096B1                       3652 00184$:
                                   3653 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
      0096B1 1E 1E            [ 2] 3654 	ldw	x, (0x1e, sp)
      0096B3 5C               [ 1] 3655 	incw	x
      0096B4 1F 1E            [ 2] 3656 	ldw	(0x1e, sp), x
      0096B6 CC 95 D5         [ 2] 3657 	jp	00183$
      0096B9                       3658 00159$:
                                   3659 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 850: if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
      0096B9 CE 01 3B         [ 2] 3660 	ldw	x, _v_tiepend+0
      0096BC 16 16            [ 2] 3661 	ldw	y, (0x16, sp)
      0096BE 17 20            [ 2] 3662 	ldw	(0x20, sp), y
      0096C0 5D               [ 2] 3663 	tnzw	x
      0096C1 2B 0C            [ 1] 3664 	jrmi	00161$
      0096C3 1E 20            [ 2] 3665 	ldw	x, (0x20, sp)
      0096C5 C3 01 3B         [ 2] 3666 	cpw	x, _v_tiepend+0
      0096C8 2D 05            [ 1] 3667 	jrsle	00161$
                                   3668 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 851: v_tiepend = -1;                  /* consumed              */
      0096CA 5F               [ 1] 3669 	clrw	x
      0096CB 5A               [ 2] 3670 	decw	x
      0096CC CF 01 3B         [ 2] 3671 	ldw	_v_tiepend+0, x
      0096CF                       3672 00161$:
                                   3673 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 852: if (tie_here >= (int16_t)kk1)
      0096CF 1E 12            [ 2] 3674 	ldw	x, (0x12, sp)
      0096D1 13 20            [ 2] 3675 	cpw	x, (0x20, sp)
      0096D3 2E 03            [ 1] 3676 	jrsge	00622$
      0096D5 CC 94 A4         [ 2] 3677 	jp	00165$
      0096D8                       3678 00622$:
                                   3679 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 853: v_tiepend = tie_here;            /* lands in next segment */
      0096D8 1E 12            [ 2] 3680 	ldw	x, (0x12, sp)
      0096DA CF 01 3B         [ 2] 3681 	ldw	_v_tiepend+0, x
      0096DD CC 94 A4         [ 2] 3682 	jp	00165$
      0096E0                       3683 00185$:
                                   3684 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 855: }
      0096E0 5B 21            [ 2] 3685 	addw	sp, #33
      0096E2 81               [ 4] 3686 	ret
                                   3687 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 861: static uint8_t crc8(const uint8_t *d, uint8_t n)
                                   3688 ;	-----------------------------------------
                                   3689 ;	 function crc8
                                   3690 ;	-----------------------------------------
      0096E3                       3691 _crc8:
      0096E3 52 04            [ 2] 3692 	sub	sp, #4
      0096E5 1F 02            [ 2] 3693 	ldw	(0x02, sp), x
      0096E7 6B 01            [ 1] 3694 	ld	(0x01, sp), a
                                   3695 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 863: uint8_t r = 0, i, j;
      0096E9 5F               [ 1] 3696 	clrw	x
                                   3697 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 864: for (i = 0; i < n; i++) {
      0096EA 4F               [ 1] 3698 	clr	a
      0096EB 97               [ 1] 3699 	ld	xl, a
      0096EC                       3700 00107$:
      0096EC 9F               [ 1] 3701 	ld	a, xl
      0096ED 11 01            [ 1] 3702 	cp	a, (0x01, sp)
      0096EF 24 24            [ 1] 3703 	jrnc	00102$
                                   3704 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 865: r ^= d[i];
      0096F1 90 5F            [ 1] 3705 	clrw	y
      0096F3 61               [ 1] 3706 	exg	a, yl
      0096F4 9F               [ 1] 3707 	ld	a, xl
      0096F5 61               [ 1] 3708 	exg	a, yl
      0096F6 72 F9 02         [ 2] 3709 	addw	y, (0x02, sp)
      0096F9 90 F6            [ 1] 3710 	ld	a, (y)
      0096FB 89               [ 2] 3711 	pushw	x
      0096FC 18 01            [ 1] 3712 	xor	a, (1, sp)
      0096FE 85               [ 2] 3713 	popw	x
      0096FF 95               [ 1] 3714 	ld	xh, a
                                   3715 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 866: for (j = 0; j < 8; j++)
      009700 A6 08            [ 1] 3716 	ld	a, #0x08
      009702 6B 04            [ 1] 3717 	ld	(0x04, sp), a
      009704                       3718 00105$:
                                   3719 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 867: r = (r & 0x80) ? (uint8_t)((uint8_t)(r << 1) ^ CRC8_POLY)
      009704 9E               [ 1] 3720 	ld	a, xh
      009705 48               [ 1] 3721 	sll	a
      009706 5D               [ 2] 3722 	tnzw	x
      009707 2A 02            [ 1] 3723 	jrpl	00111$
      009709 A8 07            [ 1] 3724 	xor	a, #0x07
                                   3725 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 868: : (uint8_t)(r << 1);
      00970B                       3726 00111$:
      00970B 95               [ 1] 3727 	ld	xh, a
                                   3728 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 866: for (j = 0; j < 8; j++)
      00970C 0A 04            [ 1] 3729 	dec	(0x04, sp)
      00970E 26 F4            [ 1] 3730 	jrne	00105$
                                   3731 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 864: for (i = 0; i < n; i++) {
      009710 9F               [ 1] 3732 	ld	a, xl
      009711 4C               [ 1] 3733 	inc	a
      009712 97               [ 1] 3734 	ld	xl, a
      009713 20 D7            [ 2] 3735 	jra	00107$
      009715                       3736 00102$:
                                   3737 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 870: return r;
      009715 9E               [ 1] 3738 	ld	a, xh
                                   3739 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 871: }
      009716 5B 04            [ 2] 3740 	addw	sp, #4
      009718 81               [ 4] 3741 	ret
                                   3742 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 874: static uint8_t syn8(uint16_t k)
                                   3743 ;	-----------------------------------------
                                   3744 ;	 function syn8
                                   3745 ;	-----------------------------------------
      009719                       3746 _syn8:
      009719 89               [ 2] 3747 	pushw	x
                                   3748 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 876: uint8_t p = (uint8_t)(k >> 3);
      00971A 90 93            [ 1] 3749 	ldw	y, x
      00971C 54               [ 2] 3750 	srlw	x
      00971D 54               [ 2] 3751 	srlw	x
      00971E 54               [ 2] 3752 	srlw	x
                                   3753 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 877: uint8_t b = (uint8_t)(7 - (k & 7));
      00971F 90 9F            [ 1] 3754 	ld	a, yl
      009721 A4 07            [ 1] 3755 	and	a, #0x07
      009723 6B 02            [ 1] 3756 	ld	(0x02, sp), a
      009725 A6 07            [ 1] 3757 	ld	a, #0x07
      009727 10 02            [ 1] 3758 	sub	a, (0x02, sp)
                                   3759 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 878: uint16_t j = (uint16_t)(8u * (uint16_t)(ND_DATA - 1 - p) + b + 8u);
      009729 41               [ 1] 3760 	exg	a, xl
      00972A 6B 02            [ 1] 3761 	ld	(0x02, sp), a
      00972C 41               [ 1] 3762 	exg	a, xl
      00972D 0F 01            [ 1] 3763 	clr	(0x01, sp)
      00972F AE 00 0F         [ 2] 3764 	ldw	x, #0x000f
      009732 72 F0 01         [ 2] 3765 	subw	x, (0x01, sp)
      009735 58               [ 2] 3766 	sllw	x
      009736 58               [ 2] 3767 	sllw	x
      009737 58               [ 2] 3768 	sllw	x
      009738 6B 02            [ 1] 3769 	ld	(0x02, sp), a
      00973A 0F 01            [ 1] 3770 	clr	(0x01, sp)
      00973C 72 FB 01         [ 2] 3771 	addw	x, (0x01, sp)
      00973F 1C 00 08         [ 2] 3772 	addw	x, #0x0008
                                   3773 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 879: while (j >= 127u) j -= 127u;   /* <= 4 iterations at ND = 48 */
      009742                       3774 00101$:
      009742 90 93            [ 1] 3775 	ldw	y, x
      009744 90 A3 00 7F      [ 2] 3776 	cpw	y, #0x007f
      009748 25 06            [ 1] 3777 	jrc	00103$
      00974A 93               [ 1] 3778 	ldw	x, y
      00974B 1D 00 7F         [ 2] 3779 	subw	x, #0x007f
      00974E 20 F2            [ 2] 3780 	jra	00101$
      009750                       3781 00103$:
                                   3782 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 880: return XPOW[j];
      009750 D6 80 35         [ 1] 3783 	ld	a, (_XPOW+0, x)
                                   3784 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 881: }
      009753 85               [ 2] 3785 	popw	x
      009754 81               [ 4] 3786 	ret
                                   3787 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 883: static uint8_t parity8(uint8_t x)
                                   3788 ;	-----------------------------------------
                                   3789 ;	 function parity8
                                   3790 ;	-----------------------------------------
      009755                       3791 _parity8:
                                   3792 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 885: x ^= (uint8_t)(x >> 4);
      009755 88               [ 1] 3793 	push	a
      009756 4E               [ 1] 3794 	swap	a
      009757 A4 0F            [ 1] 3795 	and	a, #0x0f
      009759 18 01            [ 1] 3796 	xor	a, (0x01, sp)
                                   3797 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 886: x ^= (uint8_t)(x >> 2);
      00975B 6B 01            [ 1] 3798 	ld	(0x01, sp), a
      00975D 04 01            [ 1] 3799 	srl	(0x01, sp)
      00975F 04 01            [ 1] 3800 	srl	(0x01, sp)
      009761 18 01            [ 1] 3801 	xor	a, (0x01, sp)
                                   3802 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 887: x ^= (uint8_t)(x >> 1);
      009763 6B 01            [ 1] 3803 	ld	(0x01, sp), a
      009765 04 01            [ 1] 3804 	srl	(0x01, sp)
      009767 18 01            [ 1] 3805 	xor	a, (0x01, sp)
                                   3806 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 888: return (uint8_t)(x & 1);
      009769 A4 01            [ 1] 3807 	and	a, #0x01
                                   3808 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 889: }
      00976B 5B 01            [ 2] 3809 	addw	sp, #1
      00976D 81               [ 4] 3810 	ret
                                   3811 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 892: static uint8_t maj3(uint8_t c0, uint8_t c1, uint8_t c2, uint8_t *r)
                                   3812 ;	-----------------------------------------
                                   3813 ;	 function maj3
                                   3814 ;	-----------------------------------------
      00976E                       3815 _maj3:
                                   3816 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 894: if (c0 == c1 || c0 == c2) { *r = c0; return 1; }
      00976E 1E 05            [ 2] 3817 	ldw	x, (0x05, sp)
      009770 11 03            [ 1] 3818 	cp	a, (0x03, sp)
      009772 27 04            [ 1] 3819 	jreq	00101$
      009774 11 04            [ 1] 3820 	cp	a, (0x04, sp)
      009776 26 05            [ 1] 3821 	jrne	00102$
      009778                       3822 00101$:
      009778 F7               [ 1] 3823 	ld	(x), a
      009779 A6 01            [ 1] 3824 	ld	a, #0x01
      00977B 20 0D            [ 2] 3825 	jra	00106$
      00977D                       3826 00102$:
                                   3827 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 895: if (c1 == c2)             { *r = c1; return 1; }
      00977D 7B 03            [ 1] 3828 	ld	a, (0x03, sp)
      00977F 11 04            [ 1] 3829 	cp	a, (0x04, sp)
      009781 26 06            [ 1] 3830 	jrne	00105$
      009783 7B 03            [ 1] 3831 	ld	a, (0x03, sp)
      009785 F7               [ 1] 3832 	ld	(x), a
      009786 A6 01            [ 1] 3833 	ld	a, #0x01
                                   3834 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 896: return 0;
      009788 21                    3835 	.byte 0x21
      009789                       3836 00105$:
      009789 4F               [ 1] 3837 	clr	a
      00978A                       3838 00106$:
                                   3839 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 897: }
      00978A 1E 01            [ 2] 3840 	ldw	x, (1, sp)
      00978C 5B 06            [ 2] 3841 	addw	sp, #6
      00978E FC               [ 2] 3842 	jp	(x)
                                   3843 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 906: static uint8_t try_trial(uint8_t i, uint8_t j)
                                   3844 ;	-----------------------------------------
                                   3845 ;	 function try_trial
                                   3846 ;	-----------------------------------------
      00978F                       3847 _try_trial:
      00978F 52 0B            [ 2] 3848 	sub	sp, #11
      009791 6B 09            [ 1] 3849 	ld	(0x09, sp), a
                                   3850 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 910: uint8_t r = ch_rbase, Rp, m, idx, amb;
      009793 C6 01 64         [ 1] 3851 	ld	a, _ch_rbase+0
      009796 6B 0A            [ 1] 3852 	ld	(0x0a, sp), a
                                   3853 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 911: Cp[0] = d_pp[ND_DATA]; Cp[1] = d_pp[ND_DATA + 1];
      009798 C6 01 4D         [ 1] 3854 	ld	a, _d_pp+16
      00979B 6B 01            [ 1] 3855 	ld	(0x01, sp), a
      00979D C6 01 4E         [ 1] 3856 	ld	a, _d_pp+17
      0097A0 6B 02            [ 1] 3857 	ld	(0x02, sp), a
                                   3858 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 912: Cp[2] = d_pp[ND_DATA + 2];
      0097A2 C6 01 4F         [ 1] 3859 	ld	a, _d_pp+18
      0097A5 6B 03            [ 1] 3860 	ld	(0x03, sp), a
                                   3861 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 913: sel[0] = i; sel[1] = j;
      0097A7 7B 09            [ 1] 3862 	ld	a, (0x09, sp)
      0097A9 6B 04            [ 1] 3863 	ld	(0x04, sp), a
      0097AB 7B 0E            [ 1] 3864 	ld	a, (0x0e, sp)
      0097AD 6B 05            [ 1] 3865 	ld	(0x05, sp), a
                                   3866 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 914: dec_info.trials++;
      0097AF AE 00 26         [ 2] 3867 	ldw	x, #(_dec_info+0)+2
      0097B2 7C               [ 1] 3868 	inc	(x)
                                   3869 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 915: for (m = 0; m < 2; m++) {
      0097B3 0F 0B            [ 1] 3870 	clr	(0x0b, sp)
      0097B5                       3871 00133$:
                                   3872 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 917: idx = sel[m];
      0097B5 5F               [ 1] 3873 	clrw	x
      0097B6 7B 0B            [ 1] 3874 	ld	a, (0x0b, sp)
      0097B8 97               [ 1] 3875 	ld	xl, a
      0097B9 89               [ 2] 3876 	pushw	x
      0097BA 96               [ 1] 3877 	ldw	x, sp
      0097BB 1C 00 06         [ 2] 3878 	addw	x, #6
      0097BE 72 FB 01         [ 2] 3879 	addw	x, (1, sp)
      0097C1 5B 02            [ 2] 3880 	addw	sp, #2
      0097C3 F6               [ 1] 3881 	ld	a, (x)
                                   3882 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 918: if (idx == 0xFF) break;
      0097C4 A1 FF            [ 1] 3883 	cp	a, #0xff
      0097C6 27 4D            [ 1] 3884 	jreq	00106$
                                   3885 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 919: k = v_cand_t[idx];
      0097C8 5F               [ 1] 3886 	clrw	x
      0097C9 97               [ 1] 3887 	ld	xl, a
      0097CA 58               [ 2] 3888 	sllw	x
      0097CB DE 01 27         [ 2] 3889 	ldw	x, (_v_cand_t+0, x)
      0097CE 90 93            [ 1] 3890 	ldw	y, x
                                   3891 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 920: if (k < ND8) {
      0097D0 90 A3 00 80      [ 2] 3892 	cpw	y, #0x0080
      0097D4 24 0A            [ 1] 3893 	jrnc	00104$
                                   3894 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 921: r ^= syn8(k);                   /* data bit: XOR syndrome    */
      0097D6 93               [ 1] 3895 	ldw	x, y
      0097D7 CD 97 19         [ 4] 3896 	call	_syn8
      0097DA 18 0A            [ 1] 3897 	xor	a, (0x0a, sp)
      0097DC 6B 0A            [ 1] 3898 	ld	(0x0a, sp), a
      0097DE 20 2D            [ 2] 3899 	jra	00134$
      0097E0                       3900 00104$:
                                   3901 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 923: uint16_t kc = k - ND8;          /* check bit: move the ref   */
      0097E0 93               [ 1] 3902 	ldw	x, y
      0097E1 1D 00 80         [ 2] 3903 	subw	x, #0x0080
                                   3904 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 924: Cp[kc >> 3] ^= (uint8_t)(1u << (7 - (k & 7)));
      0097E4 54               [ 2] 3905 	srlw	x
      0097E5 54               [ 2] 3906 	srlw	x
      0097E6 54               [ 2] 3907 	srlw	x
      0097E7 1F 07            [ 2] 3908 	ldw	(0x07, sp), x
      0097E9 96               [ 1] 3909 	ldw	x, sp
      0097EA 5C               [ 1] 3910 	incw	x
      0097EB 72 FB 07         [ 2] 3911 	addw	x, (0x07, sp)
      0097EE F6               [ 1] 3912 	ld	a, (x)
      0097EF 6B 07            [ 1] 3913 	ld	(0x07, sp), a
      0097F1 90 9F            [ 1] 3914 	ld	a, yl
      0097F3 A4 07            [ 1] 3915 	and	a, #0x07
      0097F5 6B 08            [ 1] 3916 	ld	(0x08, sp), a
      0097F7 A6 07            [ 1] 3917 	ld	a, #0x07
      0097F9 10 08            [ 1] 3918 	sub	a, (0x08, sp)
      0097FB 6B 08            [ 1] 3919 	ld	(0x08, sp), a
      0097FD A6 01            [ 1] 3920 	ld	a, #0x01
      0097FF 88               [ 1] 3921 	push	a
      009800 7B 09            [ 1] 3922 	ld	a, (0x09, sp)
      009802 27 05            [ 1] 3923 	jreq	00295$
      009804                       3924 00294$:
      009804 08 01            [ 1] 3925 	sll	(1, sp)
      009806 4A               [ 1] 3926 	dec	a
      009807 26 FB            [ 1] 3927 	jrne	00294$
      009809                       3928 00295$:
      009809 84               [ 1] 3929 	pop	a
      00980A 18 07            [ 1] 3930 	xor	a, (0x07, sp)
      00980C F7               [ 1] 3931 	ld	(x), a
      00980D                       3932 00134$:
                                   3933 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 915: for (m = 0; m < 2; m++) {
      00980D 0C 0B            [ 1] 3934 	inc	(0x0b, sp)
      00980F 7B 0B            [ 1] 3935 	ld	a, (0x0b, sp)
      009811 A1 02            [ 1] 3936 	cp	a, #0x02
      009813 25 A0            [ 1] 3937 	jrc	00133$
      009815                       3938 00106$:
                                   3939 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 927: if (!maj3(Cp[0], Cp[1], Cp[2], &Rp)) return 0; /* slot burned, no ref */
      009815 96               [ 1] 3940 	ldw	x, sp
      009816 1C 00 06         [ 2] 3941 	addw	x, #6
      009819 51               [ 1] 3942 	exgw	x, y
      00981A 7B 03            [ 1] 3943 	ld	a, (0x03, sp)
      00981C 97               [ 1] 3944 	ld	xl, a
      00981D 7B 02            [ 1] 3945 	ld	a, (0x02, sp)
      00981F 95               [ 1] 3946 	ld	xh, a
      009820 7B 01            [ 1] 3947 	ld	a, (0x01, sp)
      009822 6B 0B            [ 1] 3948 	ld	(0x0b, sp), a
      009824 90 89            [ 2] 3949 	pushw	y
      009826 9F               [ 1] 3950 	ld	a, xl
      009827 88               [ 1] 3951 	push	a
      009828 9E               [ 1] 3952 	ld	a, xh
      009829 88               [ 1] 3953 	push	a
      00982A 7B 0F            [ 1] 3954 	ld	a, (0x0f, sp)
      00982C CD 97 6E         [ 4] 3955 	call	_maj3
      00982F 4D               [ 1] 3956 	tnz	a
      009830 26 04            [ 1] 3957 	jrne	00108$
      009832 4F               [ 1] 3958 	clr	a
      009833 CC 99 02         [ 2] 3959 	jp	00140$
      009836                       3960 00108$:
                                   3961 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 928: if (r != Rp) return 0;
      009836 7B 0A            [ 1] 3962 	ld	a, (0x0a, sp)
      009838 11 06            [ 1] 3963 	cp	a, (0x06, sp)
      00983A 27 04            [ 1] 3964 	jreq	00110$
      00983C 4F               [ 1] 3965 	clr	a
      00983D CC 99 02         [ 2] 3966 	jp	00140$
      009840                       3967 00110$:
                                   3968 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 931: amb = 0;
      009840 0F 07            [ 1] 3969 	clr	(0x07, sp)
                                   3970 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 932: for (m = 0; m < 2; m++) {
      009842 0F 0A            [ 1] 3971 	clr	(0x0a, sp)
      009844                       3972 00137$:
                                   3973 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 935: idx = sel[m];
      009844 5F               [ 1] 3974 	clrw	x
      009845 7B 0A            [ 1] 3975 	ld	a, (0x0a, sp)
      009847 97               [ 1] 3976 	ld	xl, a
      009848 89               [ 2] 3977 	pushw	x
      009849 96               [ 1] 3978 	ldw	x, sp
      00984A 1C 00 06         [ 2] 3979 	addw	x, #6
      00984D 72 FB 01         [ 2] 3980 	addw	x, (1, sp)
      009850 5B 02            [ 2] 3981 	addw	sp, #2
      009852 F6               [ 1] 3982 	ld	a, (x)
                                   3983 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 936: if (idx == 0xFF) break;
      009853 A1 FF            [ 1] 3984 	cp	a, #0xff
      009855 27 51            [ 1] 3985 	jreq	00125$
                                   3986 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 937: ki = v_cand_t[idx];
      009857 5F               [ 1] 3987 	clrw	x
      009858 97               [ 1] 3988 	ld	xl, a
      009859 58               [ 2] 3989 	sllw	x
      00985A DE 01 27         [ 2] 3990 	ldw	x, (_v_cand_t+0, x)
                                   3991 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 938: if (ki >= ND8) continue;
      00985D A3 00 80         [ 2] 3992 	cpw	x, #0x0080
      009860 24 3E            [ 1] 3993 	jrnc	00124$
                                   3994 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 939: si = syn8(ki);
      009862 CD 97 19         [ 4] 3995 	call	_syn8
      009865 6B 08            [ 1] 3996 	ld	(0x08, sp), a
                                   3997 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 940: for (jj = 0; jj < ch_n; jj++) {
      009867 0F 0B            [ 1] 3998 	clr	(0x0b, sp)
      009869                       3999 00136$:
      009869 7B 0B            [ 1] 4000 	ld	a, (0x0b, sp)
      00986B C1 01 65         [ 1] 4001 	cp	a, _ch_n+0
      00986E 24 30            [ 1] 4002 	jrnc	00124$
                                   4003 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 941: if (jj == i || jj == j) continue;
      009870 7B 0B            [ 1] 4004 	ld	a, (0x0b, sp)
      009872 11 09            [ 1] 4005 	cp	a, (0x09, sp)
      009874 27 26            [ 1] 4006 	jreq	00122$
      009876 7B 0B            [ 1] 4007 	ld	a, (0x0b, sp)
      009878 11 0E            [ 1] 4008 	cp	a, (0x0e, sp)
      00987A 27 20            [ 1] 4009 	jreq	00122$
                                   4010 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 942: if (v_cand_t[jj] < ND8) {
      00987C 7B 0B            [ 1] 4011 	ld	a, (0x0b, sp)
      00987E 5F               [ 1] 4012 	clrw	x
      00987F 97               [ 1] 4013 	ld	xl, a
      009880 58               [ 2] 4014 	sllw	x
      009881 1C 01 27         [ 2] 4015 	addw	x, #(_v_cand_t+0)
      009884 90 93            [ 1] 4016 	ldw	y, x
      009886 FE               [ 2] 4017 	ldw	x, (x)
      009887 A3 00 80         [ 2] 4018 	cpw	x, #0x0080
      00988A 24 10            [ 1] 4019 	jrnc	00122$
                                   4020 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 943: dec_info.alias_cmp++;
      00988C AE 00 27         [ 2] 4021 	ldw	x, #(_dec_info+0)+3
      00988F 7C               [ 1] 4022 	inc	(x)
                                   4023 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 944: if (syn8(v_cand_t[jj]) == si) amb = 1;
      009890 93               [ 1] 4024 	ldw	x, y
      009891 FE               [ 2] 4025 	ldw	x, (x)
      009892 CD 97 19         [ 4] 4026 	call	_syn8
      009895 10 08            [ 1] 4027 	sub	a, (0x08, sp)
      009897 26 03            [ 1] 4028 	jrne	00122$
      009899 4C               [ 1] 4029 	inc	a
      00989A 6B 07            [ 1] 4030 	ld	(0x07, sp), a
      00989C                       4031 00122$:
                                   4032 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 940: for (jj = 0; jj < ch_n; jj++) {
      00989C 0C 0B            [ 1] 4033 	inc	(0x0b, sp)
      00989E 20 C9            [ 2] 4034 	jra	00136$
      0098A0                       4035 00124$:
                                   4036 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 932: for (m = 0; m < 2; m++) {
      0098A0 0C 0A            [ 1] 4037 	inc	(0x0a, sp)
      0098A2 7B 0A            [ 1] 4038 	ld	a, (0x0a, sp)
      0098A4 A1 02            [ 1] 4039 	cp	a, #0x02
      0098A6 25 9C            [ 1] 4040 	jrc	00137$
      0098A8                       4041 00125$:
                                   4042 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 948: if (amb) return 0;
      0098A8 0D 07            [ 1] 4043 	tnz	(0x07, sp)
      0098AA 27 03            [ 1] 4044 	jreq	00177$
      0098AC 4F               [ 1] 4045 	clr	a
      0098AD 20 53            [ 2] 4046 	jra	00140$
                                   4047 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 950: for (m = 0; m < 2; m++) {
      0098AF                       4048 00177$:
      0098AF 0F 0B            [ 1] 4049 	clr	(0x0b, sp)
      0098B1                       4050 00138$:
                                   4051 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 952: idx = sel[m];
      0098B1 5F               [ 1] 4052 	clrw	x
      0098B2 7B 0B            [ 1] 4053 	ld	a, (0x0b, sp)
      0098B4 97               [ 1] 4054 	ld	xl, a
      0098B5 89               [ 2] 4055 	pushw	x
      0098B6 96               [ 1] 4056 	ldw	x, sp
      0098B7 1C 00 06         [ 2] 4057 	addw	x, #6
      0098BA 72 FB 01         [ 2] 4058 	addw	x, (1, sp)
      0098BD 5B 02            [ 2] 4059 	addw	sp, #2
      0098BF F6               [ 1] 4060 	ld	a, (x)
                                   4061 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 953: if (idx == 0xFF) break;
      0098C0 A1 FF            [ 1] 4062 	cp	a, #0xff
      0098C2 27 3C            [ 1] 4063 	jreq	00132$
                                   4064 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 954: k = v_cand_t[idx];
      0098C4 5F               [ 1] 4065 	clrw	x
      0098C5 97               [ 1] 4066 	ld	xl, a
      0098C6 58               [ 2] 4067 	sllw	x
      0098C7 DE 01 27         [ 2] 4068 	ldw	x, (_v_cand_t+0, x)
      0098CA 90 93            [ 1] 4069 	ldw	y, x
                                   4070 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 955: if (k < ND8)
      0098CC 90 A3 00 80      [ 2] 4071 	cpw	y, #0x0080
      0098D0 24 26            [ 1] 4072 	jrnc	00139$
                                   4073 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 956: d_pp[k >> 3] ^= (uint8_t)(1u << (7 - (k & 7)));
      0098D2 93               [ 1] 4074 	ldw	x, y
      0098D3 54               [ 2] 4075 	srlw	x
      0098D4 54               [ 2] 4076 	srlw	x
      0098D5 54               [ 2] 4077 	srlw	x
      0098D6 1C 01 3D         [ 2] 4078 	addw	x, #(_d_pp+0)
      0098D9 F6               [ 1] 4079 	ld	a, (x)
      0098DA 6B 08            [ 1] 4080 	ld	(0x08, sp), a
      0098DC 90 9F            [ 1] 4081 	ld	a, yl
      0098DE A4 07            [ 1] 4082 	and	a, #0x07
      0098E0 6B 0A            [ 1] 4083 	ld	(0x0a, sp), a
      0098E2 A6 07            [ 1] 4084 	ld	a, #0x07
      0098E4 10 0A            [ 1] 4085 	sub	a, (0x0a, sp)
      0098E6 6B 0A            [ 1] 4086 	ld	(0x0a, sp), a
      0098E8 A6 01            [ 1] 4087 	ld	a, #0x01
      0098EA 88               [ 1] 4088 	push	a
      0098EB 7B 0B            [ 1] 4089 	ld	a, (0x0b, sp)
      0098ED 27 05            [ 1] 4090 	jreq	00323$
      0098EF                       4091 00322$:
      0098EF 08 01            [ 1] 4092 	sll	(1, sp)
      0098F1 4A               [ 1] 4093 	dec	a
      0098F2 26 FB            [ 1] 4094 	jrne	00322$
      0098F4                       4095 00323$:
      0098F4 84               [ 1] 4096 	pop	a
      0098F5 18 08            [ 1] 4097 	xor	a, (0x08, sp)
      0098F7 F7               [ 1] 4098 	ld	(x), a
      0098F8                       4099 00139$:
                                   4100 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 950: for (m = 0; m < 2; m++) {
      0098F8 0C 0B            [ 1] 4101 	inc	(0x0b, sp)
      0098FA 7B 0B            [ 1] 4102 	ld	a, (0x0b, sp)
      0098FC A1 02            [ 1] 4103 	cp	a, #0x02
      0098FE 25 B1            [ 1] 4104 	jrc	00138$
      009900                       4105 00132$:
                                   4106 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 958: return 1;
      009900 A6 01            [ 1] 4107 	ld	a, #0x01
      009902                       4108 00140$:
                                   4109 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 959: }
      009902 5B 0B            [ 2] 4110 	addw	sp, #11
      009904 85               [ 2] 4111 	popw	x
      009905 5B 01            [ 2] 4112 	addw	sp, #1
      009907 FC               [ 2] 4113 	jp	(x)
                                   4114 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 963: static uint8_t chase_singles(uint8_t want)
                                   4115 ;	-----------------------------------------
                                   4116 ;	 function chase_singles
                                   4117 ;	-----------------------------------------
      009908                       4118 _chase_singles:
      009908 89               [ 2] 4119 	pushw	x
      009909 6B 01            [ 1] 4120 	ld	(0x01, sp), a
                                   4121 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 966: for (p = 0; p < ch_n; p++)
      00990B 0F 02            [ 1] 4122 	clr	(0x02, sp)
      00990D                       4123 00106$:
      00990D 7B 02            [ 1] 4124 	ld	a, (0x02, sp)
      00990F C1 01 65         [ 1] 4125 	cp	a, _ch_n+0
      009912 24 1D            [ 1] 4126 	jrnc	00104$
                                   4127 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 967: if (ch_isd[p] == want && try_trial(p, 0xFF)) return 1;
      009914 5F               [ 1] 4128 	clrw	x
      009915 7B 02            [ 1] 4129 	ld	a, (0x02, sp)
      009917 97               [ 1] 4130 	ld	xl, a
      009918 D6 01 66         [ 1] 4131 	ld	a, (_ch_isd+0, x)
      00991B 11 01            [ 1] 4132 	cp	a, (0x01, sp)
      00991D 26 0E            [ 1] 4133 	jrne	00107$
      00991F 4B FF            [ 1] 4134 	push	#0xff
      009921 7B 03            [ 1] 4135 	ld	a, (0x03, sp)
      009923 CD 97 8F         [ 4] 4136 	call	_try_trial
      009926 4D               [ 1] 4137 	tnz	a
      009927 27 04            [ 1] 4138 	jreq	00107$
      009929 A6 01            [ 1] 4139 	ld	a, #0x01
      00992B 20 05            [ 2] 4140 	jra	00108$
      00992D                       4141 00107$:
                                   4142 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 966: for (p = 0; p < ch_n; p++)
      00992D 0C 02            [ 1] 4143 	inc	(0x02, sp)
      00992F 20 DC            [ 2] 4144 	jra	00106$
      009931                       4145 00104$:
                                   4146 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 968: return 0;
      009931 4F               [ 1] 4147 	clr	a
      009932                       4148 00108$:
                                   4149 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 969: }
      009932 85               [ 2] 4150 	popw	x
      009933 81               [ 4] 4151 	ret
                                   4152 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: static uint8_t chase_pairs(uint8_t sum_want)
                                   4153 ;	-----------------------------------------
                                   4154 ;	 function chase_pairs
                                   4155 ;	-----------------------------------------
      009934                       4156 _chase_pairs:
      009934 52 06            [ 2] 4157 	sub	sp, #6
      009936 6B 04            [ 1] 4158 	ld	(0x04, sp), a
                                   4159 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (p = 0; p < ch_n; p++)
      009938 0F 05            [ 1] 4160 	clr	(0x05, sp)
      00993A                       4161 00110$:
      00993A 7B 05            [ 1] 4162 	ld	a, (0x05, sp)
      00993C C1 01 65         [ 1] 4163 	cp	a, _ch_n+0
      00993F 24 3E            [ 1] 4164 	jrnc	00105$
                                   4165 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: for (j = (uint8_t)(p + 1); j < ch_n; j++)
      009941 7B 05            [ 1] 4166 	ld	a, (0x05, sp)
      009943 4C               [ 1] 4167 	inc	a
      009944 6B 06            [ 1] 4168 	ld	(0x06, sp), a
      009946 5F               [ 1] 4169 	clrw	x
      009947 7B 05            [ 1] 4170 	ld	a, (0x05, sp)
      009949 97               [ 1] 4171 	ld	xl, a
      00994A 1C 01 66         [ 2] 4172 	addw	x, #(_ch_isd+0)
      00994D 1F 01            [ 2] 4173 	ldw	(0x01, sp), x
      00994F                       4174 00107$:
      00994F 7B 06            [ 1] 4175 	ld	a, (0x06, sp)
      009951 C1 01 65         [ 1] 4176 	cp	a, _ch_n+0
      009954 24 25            [ 1] 4177 	jrnc	00111$
                                   4178 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 979: if ((uint8_t)(ch_isd[p] + ch_isd[j]) == sum_want &&
      009956 1E 01            [ 2] 4179 	ldw	x, (0x01, sp)
      009958 F6               [ 1] 4180 	ld	a, (x)
      009959 6B 03            [ 1] 4181 	ld	(0x03, sp), a
      00995B 5F               [ 1] 4182 	clrw	x
      00995C 7B 06            [ 1] 4183 	ld	a, (0x06, sp)
      00995E 97               [ 1] 4184 	ld	xl, a
      00995F D6 01 66         [ 1] 4185 	ld	a, (_ch_isd+0, x)
      009962 1B 03            [ 1] 4186 	add	a, (0x03, sp)
      009964 11 04            [ 1] 4187 	cp	a, (0x04, sp)
      009966 26 0F            [ 1] 4188 	jrne	00108$
                                   4189 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 980: try_trial(p, j))
      009968 7B 06            [ 1] 4190 	ld	a, (0x06, sp)
      00996A 88               [ 1] 4191 	push	a
      00996B 7B 06            [ 1] 4192 	ld	a, (0x06, sp)
      00996D CD 97 8F         [ 4] 4193 	call	_try_trial
      009970 4D               [ 1] 4194 	tnz	a
      009971 27 04            [ 1] 4195 	jreq	00108$
                                   4196 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 981: return 1;
      009973 A6 01            [ 1] 4197 	ld	a, #0x01
      009975 20 09            [ 2] 4198 	jra	00112$
      009977                       4199 00108$:
                                   4200 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: for (j = (uint8_t)(p + 1); j < ch_n; j++)
      009977 0C 06            [ 1] 4201 	inc	(0x06, sp)
      009979 20 D4            [ 2] 4202 	jra	00107$
      00997B                       4203 00111$:
                                   4204 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (p = 0; p < ch_n; p++)
      00997B 0C 05            [ 1] 4205 	inc	(0x05, sp)
      00997D 20 BB            [ 2] 4206 	jra	00110$
      00997F                       4207 00105$:
                                   4208 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 982: return 0;
      00997F 4F               [ 1] 4209 	clr	a
      009980                       4210 00112$:
                                   4211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 983: }
      009980 5B 06            [ 2] 4212 	addw	sp, #6
      009982 81               [ 4] 4213 	ret
                                   4214 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 989: static uint8_t chase(uint8_t *out)
                                   4215 ;	-----------------------------------------
                                   4216 ;	 function chase
                                   4217 ;	-----------------------------------------
      009983                       4218 _chase:
      009983 52 08            [ 2] 4219 	sub	sp, #8
      009985 1F 05            [ 2] 4220 	ldw	(0x05, sp), x
                                   4221 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
      009987 0F 07            [ 1] 4222 	clr	(0x07, sp)
      009989                       4223 00132$:
                                   4224 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 994: uint8_t val = 0;
      009989 4F               [ 1] 4225 	clr	a
                                   4226 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 995: uint16_t base = PP_LO + ((uint16_t)p << 3);
      00998A 41               [ 1] 4227 	exg	a, xl
      00998B 7B 07            [ 1] 4228 	ld	a, (0x07, sp)
      00998D 41               [ 1] 4229 	exg	a, xl
      00998E 58               [ 2] 4230 	sllw	x
      00998F 58               [ 2] 4231 	sllw	x
      009990 58               [ 2] 4232 	sllw	x
      009991 1C 00 20         [ 2] 4233 	addw	x, #32
      009994 90 93            [ 1] 4234 	ldw	y, x
                                   4235 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
      009996 0F 08            [ 1] 4236 	clr	(0x08, sp)
      009998                       4237 00130$:
                                   4238 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 997: val = (uint8_t)((val << 1) | BGET(d_bits, base + j));
      009998 48               [ 1] 4239 	sll	a
      009999 6B 02            [ 1] 4240 	ld	(0x02, sp), a
      00999B 7B 08            [ 1] 4241 	ld	a, (0x08, sp)
      00999D 6B 04            [ 1] 4242 	ld	(0x04, sp), a
      00999F 0F 03            [ 1] 4243 	clr	(0x03, sp)
      0099A1 93               [ 1] 4244 	ldw	x, y
      0099A2 4F               [ 1] 4245 	clr	a
      0099A3 95               [ 1] 4246 	ld	xh, a
      0099A4 72 FB 03         [ 2] 4247 	addw	x, (0x03, sp)
      0099A7 54               [ 2] 4248 	srlw	x
      0099A8 54               [ 2] 4249 	srlw	x
      0099A9 54               [ 2] 4250 	srlw	x
      0099AA 1C 00 E4         [ 2] 4251 	addw	x, #(_d_bits+0)
      0099AD F6               [ 1] 4252 	ld	a, (x)
      0099AE 97               [ 1] 4253 	ld	xl, a
      0099AF 90 9F            [ 1] 4254 	ld	a, yl
      0099B1 1B 08            [ 1] 4255 	add	a, (0x08, sp)
      0099B3 A4 07            [ 1] 4256 	and	a, #0x07
      0099B5 27 06            [ 1] 4257 	jreq	00319$
      0099B7                       4258 00318$:
      0099B7 41               [ 1] 4259 	exg	a, xl
      0099B8 44               [ 1] 4260 	srl	a
      0099B9 41               [ 1] 4261 	exg	a, xl
      0099BA 4A               [ 1] 4262 	dec	a
      0099BB 26 FA            [ 1] 4263 	jrne	00318$
      0099BD                       4264 00319$:
      0099BD 9F               [ 1] 4265 	ld	a, xl
      0099BE A4 01            [ 1] 4266 	and	a, #0x01
      0099C0 1A 02            [ 1] 4267 	or	a, (0x02, sp)
                                   4268 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
      0099C2 0C 08            [ 1] 4269 	inc	(0x08, sp)
      0099C4 88               [ 1] 4270 	push	a
      0099C5 7B 09            [ 1] 4271 	ld	a, (0x09, sp)
      0099C7 A1 08            [ 1] 4272 	cp	a, #0x08
      0099C9 84               [ 1] 4273 	pop	a
      0099CA 25 CC            [ 1] 4274 	jrc	00130$
                                   4275 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 998: d_pp[p] = val;
      0099CC 5F               [ 1] 4276 	clrw	x
      0099CD 41               [ 1] 4277 	exg	a, xl
      0099CE 7B 07            [ 1] 4278 	ld	a, (0x07, sp)
      0099D0 41               [ 1] 4279 	exg	a, xl
      0099D1 1C 01 3D         [ 2] 4280 	addw	x, #(_d_pp+0)
      0099D4 F7               [ 1] 4281 	ld	(x), a
                                   4282 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
      0099D5 0C 07            [ 1] 4283 	inc	(0x07, sp)
      0099D7 7B 07            [ 1] 4284 	ld	a, (0x07, sp)
      0099D9 A1 13            [ 1] 4285 	cp	a, #0x13
      0099DB 25 AC            [ 1] 4286 	jrc	00132$
                                   4287 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1000: dec_info.n_weak = v_nweak;
      0099DD 55 01 38 00 2A   [ 1] 4288 	mov	_dec_info+6, _v_nweak+1
      0099E2 55 01 37 00 29   [ 1] 4289 	mov	_dec_info+5, _v_nweak+0
                                   4290 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1001: dec_info.n_tied = v_ntied;
      0099E7 55 01 3A 00 2C   [ 1] 4291 	mov	_dec_info+8, _v_ntied+1
      0099EC 55 01 39 00 2B   [ 1] 4292 	mov	_dec_info+7, _v_ntied+0
                                   4293 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1010: uint8_t R = 0, have_R, par;
      0099F1 0F 01            [ 1] 4294 	clr	(0x01, sp)
                                   4295 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1011: ch_rbase = crc8(d_pp, ND_DATA);
      0099F3 A6 10            [ 1] 4296 	ld	a, #0x10
      0099F5 AE 01 3D         [ 2] 4297 	ldw	x, #(_d_pp+0)
      0099F8 CD 96 E3         [ 4] 4298 	call	_crc8
      0099FB C7 01 64         [ 1] 4299 	ld	_ch_rbase+0, a
                                   4300 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1012: have_R = maj3(d_pp[ND_DATA], d_pp[ND_DATA + 1], d_pp[ND_DATA + 2], &R);
      0099FE 90 96            [ 1] 4301 	ldw	y, sp
      009A00 90 5C            [ 1] 4302 	incw	y
      009A02 C6 01 4F         [ 1] 4303 	ld	a, _d_pp+18
      009A05 6B 08            [ 1] 4304 	ld	(0x08, sp), a
      009A07 C6 01 4E         [ 1] 4305 	ld	a, _d_pp+17
      009A0A 97               [ 1] 4306 	ld	xl, a
      009A0B C6 01 4D         [ 1] 4307 	ld	a, _d_pp+16
      009A0E 95               [ 1] 4308 	ld	xh, a
      009A0F 90 89            [ 2] 4309 	pushw	y
      009A11 7B 0A            [ 1] 4310 	ld	a, (0x0a, sp)
      009A13 88               [ 1] 4311 	push	a
      009A14 9F               [ 1] 4312 	ld	a, xl
      009A15 88               [ 1] 4313 	push	a
      009A16 9E               [ 1] 4314 	ld	a, xh
      009A17 CD 97 6E         [ 4] 4315 	call	_maj3
      009A1A 6B 07            [ 1] 4316 	ld	(0x07, sp), a
                                   4317 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1014: if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
      009A1C CE 01 39         [ 2] 4318 	ldw	x, _v_ntied+0
      009A1F A3 00 08         [ 2] 4319 	cpw	x, #0x0008
      009A22 23 08            [ 2] 4320 	jrule	00104$
      009A24 35 05 00 25      [ 1] 4321 	mov	_dec_info+1, #0x05
      009A28 4F               [ 1] 4322 	clr	a
      009A29 CC 9B 07         [ 2] 4323 	jp	00141$
      009A2C                       4324 00104$:
                                   4325 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1016: if (have_R && ch_rbase == R) {
      009A2C 0D 07            [ 1] 4326 	tnz	(0x07, sp)
      009A2E 27 23            [ 1] 4327 	jreq	00107$
      009A30 7B 01            [ 1] 4328 	ld	a, (0x01, sp)
      009A32 C1 01 64         [ 1] 4329 	cp	a, _ch_rbase+0
      009A35 26 1C            [ 1] 4330 	jrne	00107$
                                   4331 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1017: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
      009A37 4F               [ 1] 4332 	clr	a
      009A38                       4333 00134$:
      009A38 90 5F            [ 1] 4334 	clrw	y
      009A3A 90 97            [ 1] 4335 	ld	yl, a
      009A3C 72 F9 05         [ 2] 4336 	addw	y, (0x05, sp)
      009A3F 5F               [ 1] 4337 	clrw	x
      009A40 97               [ 1] 4338 	ld	xl, a
      009A41 1C 01 3D         [ 2] 4339 	addw	x, #(_d_pp+0)
      009A44 88               [ 1] 4340 	push	a
      009A45 F6               [ 1] 4341 	ld	a, (x)
      009A46 90 F7            [ 1] 4342 	ld	(y), a
      009A48 84               [ 1] 4343 	pop	a
      009A49 4C               [ 1] 4344 	inc	a
      009A4A A1 10            [ 1] 4345 	cp	a, #0x10
      009A4C 25 EA            [ 1] 4346 	jrc	00134$
                                   4347 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1018: return DEC_DIRECT;
      009A4E A6 01            [ 1] 4348 	ld	a, #0x01
      009A50 CC 9B 07         [ 2] 4349 	jp	00141$
      009A53                       4350 00107$:
                                   4351 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1021: if (v_nweak == 0) { dec_info.cause = CAUSE_NOCAND; return DEC_REFUSE; }
      009A53 CE 01 37         [ 2] 4352 	ldw	x, _v_nweak+0
      009A56 26 08            [ 1] 4353 	jrne	00110$
      009A58 35 06 00 25      [ 1] 4354 	mov	_dec_info+1, #0x06
      009A5C 4F               [ 1] 4355 	clr	a
      009A5D CC 9B 07         [ 2] 4356 	jp	00141$
      009A60                       4357 00110$:
                                   4358 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1022: if (v_nweak > A_MAX) { dec_info.cause = CAUSE_ADMIT; return DEC_REFUSE; }
      009A60 CE 01 37         [ 2] 4359 	ldw	x, _v_nweak+0
      009A63 A3 00 05         [ 2] 4360 	cpw	x, #0x0005
      009A66 23 08            [ 2] 4361 	jrule	00112$
      009A68 35 07 00 25      [ 1] 4362 	mov	_dec_info+1, #0x07
      009A6C 4F               [ 1] 4363 	clr	a
      009A6D CC 9B 07         [ 2] 4364 	jp	00141$
      009A70                       4365 00112$:
                                   4366 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1024: ch_n = v_ncand;
      009A70 55 01 36 01 65   [ 1] 4367 	mov	_ch_n+0, _v_ncand+0
                                   4368 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1025: for (p = 0; p < ch_n; p++)
      009A75 0F 08            [ 1] 4369 	clr	(0x08, sp)
      009A77                       4370 00137$:
      009A77 7B 08            [ 1] 4371 	ld	a, (0x08, sp)
      009A79 C1 01 65         [ 1] 4372 	cp	a, _ch_n+0
      009A7C 24 1D            [ 1] 4373 	jrnc	00113$
                                   4374 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1026: ch_isd[p] = (v_cand_t[p] < ND8);
      009A7E 90 5F            [ 1] 4375 	clrw	y
      009A80 7B 08            [ 1] 4376 	ld	a, (0x08, sp)
      009A82 90 97            [ 1] 4377 	ld	yl, a
      009A84 72 A9 01 66      [ 2] 4378 	addw	y, #(_ch_isd+0)
      009A88 7B 08            [ 1] 4379 	ld	a, (0x08, sp)
      009A8A 5F               [ 1] 4380 	clrw	x
      009A8B 97               [ 1] 4381 	ld	xl, a
      009A8C 58               [ 2] 4382 	sllw	x
      009A8D DE 01 27         [ 2] 4383 	ldw	x, (_v_cand_t+0, x)
      009A90 A3 00 80         [ 2] 4384 	cpw	x, #0x0080
      009A93 4F               [ 1] 4385 	clr	a
      009A94 49               [ 1] 4386 	rlc	a
      009A95 90 F7            [ 1] 4387 	ld	(y), a
                                   4388 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1025: for (p = 0; p < ch_n; p++)
      009A97 0C 08            [ 1] 4389 	inc	(0x08, sp)
      009A99 20 DC            [ 2] 4390 	jra	00137$
      009A9B                       4391 00113$:
                                   4392 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1027: par = have_R ? parity8((uint8_t)(ch_rbase ^ R)) : 0xFF;
      009A9B 0D 07            [ 1] 4393 	tnz	(0x07, sp)
      009A9D 27 09            [ 1] 4394 	jreq	00143$
      009A9F 7B 01            [ 1] 4395 	ld	a, (0x01, sp)
      009AA1 C8 01 64         [ 1] 4396 	xor	a, _ch_rbase+0
      009AA4 CD 97 55         [ 4] 4397 	call	_parity8
      009AA7 C5                    4398 	.byte 0xc5
      009AA8                       4399 00143$:
      009AA8 A6 FF            [ 1] 4400 	ld	a, #0xff
      009AAA                       4401 00144$:
      009AAA 6B 08            [ 1] 4402 	ld	(0x08, sp), a
                                   4403 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1028: dec_info.chased = 1;
      009AAC 35 01 00 28      [ 1] 4404 	mov	_dec_info+4, #0x01
                                   4405 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1031: if (chase_singles(0)) goto accept;      /* phase 1: one check bit */
      009AB0 4F               [ 1] 4406 	clr	a
      009AB1 CD 99 08         [ 4] 4407 	call	_chase_singles
      009AB4 4D               [ 1] 4408 	tnz	a
      009AB5 26 37            [ 1] 4409 	jrne	00185$
                                   4410 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1032: if (chase_pairs(0)) goto accept;        /* phase 2: two check bits */
      009AB7 4F               [ 1] 4411 	clr	a
      009AB8 CD 99 34         [ 4] 4412 	call	_chase_pairs
      009ABB 4D               [ 1] 4413 	tnz	a
      009ABC 26 30            [ 1] 4414 	jrne	00185$
                                   4415 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1033: if (!(have_R && par == 0) &&            /* phase 3: one data bit */
      009ABE 0D 07            [ 1] 4416 	tnz	(0x07, sp)
      009AC0 27 04            [ 1] 4417 	jreq	00121$
      009AC2 0D 08            [ 1] 4418 	tnz	(0x08, sp)
      009AC4 27 08            [ 1] 4419 	jreq	00119$
      009AC6                       4420 00121$:
                                   4421 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1034: chase_singles(1)) goto accept;
      009AC6 A6 01            [ 1] 4422 	ld	a, #0x01
      009AC8 CD 99 08         [ 4] 4423 	call	_chase_singles
      009ACB 4D               [ 1] 4424 	tnz	a
      009ACC 26 20            [ 1] 4425 	jrne	00185$
      009ACE                       4426 00119$:
                                   4427 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1035: if (chase_pairs(1)) goto accept;        /* phase 4: data + check */
      009ACE A6 01            [ 1] 4428 	ld	a, #0x01
      009AD0 CD 99 34         [ 4] 4429 	call	_chase_pairs
      009AD3 4D               [ 1] 4430 	tnz	a
      009AD4 26 18            [ 1] 4431 	jrne	00185$
                                   4432 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1036: if (!(have_R && par == 1) &&            /* phase 5: two data bits */
      009AD6 0D 07            [ 1] 4433 	tnz	(0x07, sp)
      009AD8 27 05            [ 1] 4434 	jreq	00127$
      009ADA 7B 08            [ 1] 4435 	ld	a, (0x08, sp)
      009ADC 4A               [ 1] 4436 	dec	a
      009ADD 27 08            [ 1] 4437 	jreq	00125$
      009ADF                       4438 00127$:
                                   4439 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1037: chase_pairs(2)) goto accept;
      009ADF A6 02            [ 1] 4440 	ld	a, #0x02
      009AE1 CD 99 34         [ 4] 4441 	call	_chase_pairs
      009AE4 4D               [ 1] 4442 	tnz	a
      009AE5 26 07            [ 1] 4443 	jrne	00185$
      009AE7                       4444 00125$:
                                   4445 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1038: dec_info.cause = CAUSE_CHASE;           /* R8: the honest end */
      009AE7 35 08 00 25      [ 1] 4446 	mov	_dec_info+1, #0x08
                                   4447 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1039: return DEC_REFUSE;
      009AEB 4F               [ 1] 4448 	clr	a
      009AEC 20 19            [ 2] 4449 	jra	00141$
                                   4450 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1041: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
      009AEE                       4451 00185$:
      009AEE 4F               [ 1] 4452 	clr	a
      009AEF                       4453 00139$:
      009AEF 90 5F            [ 1] 4454 	clrw	y
      009AF1 90 97            [ 1] 4455 	ld	yl, a
      009AF3 72 F9 05         [ 2] 4456 	addw	y, (0x05, sp)
      009AF6 5F               [ 1] 4457 	clrw	x
      009AF7 97               [ 1] 4458 	ld	xl, a
      009AF8 1C 01 3D         [ 2] 4459 	addw	x, #(_d_pp+0)
      009AFB 88               [ 1] 4460 	push	a
      009AFC F6               [ 1] 4461 	ld	a, (x)
      009AFD 90 F7            [ 1] 4462 	ld	(y), a
      009AFF 84               [ 1] 4463 	pop	a
      009B00 4C               [ 1] 4464 	inc	a
      009B01 A1 10            [ 1] 4465 	cp	a, #0x10
      009B03 25 EA            [ 1] 4466 	jrc	00139$
                                   4467 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1042: return DEC_CHASE;
      009B05 A6 02            [ 1] 4468 	ld	a, #0x02
      009B07                       4469 00141$:
                                   4470 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1045: }
      009B07 5B 08            [ 2] 4471 	addw	sp, #8
      009B09 81               [ 4] 4472 	ret
                                   4473 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1049: uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
                                   4474 ;	-----------------------------------------
                                   4475 ;	 function ws_decode_ex
                                   4476 ;	-----------------------------------------
      009B0A                       4477 _ws_decode_ex:
      009B0A 89               [ 2] 4478 	pushw	x
      009B0B 51               [ 1] 4479 	exgw	x, y
                                   4480 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
      009B0C 4F               [ 1] 4481 	clr	a
      009B0D                       4482 00115$:
                                   4483 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1055: ((uint8_t *)&dec_info)[t] = 0;
      009B0D 5F               [ 1] 4484 	clrw	x
      009B0E 97               [ 1] 4485 	ld	xl, a
      009B0F 72 4F 00 24      [ 1] 4486 	clr	((_dec_info+0), x)
                                   4487 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
      009B13 4C               [ 1] 4488 	inc	a
      009B14 A1 14            [ 1] 4489 	cp	a, #0x14
      009B16 25 F5            [ 1] 4490 	jrc	00115$
                                   4491 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1056: scan_cap = cap;
      009B18 90 CF 00 01      [ 2] 4492 	ldw	_scan_cap+0, y
                                   4493 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1057: scan_len = ncap;
      009B1C 1E 05            [ 2] 4494 	ldw	x, (0x05, sp)
      009B1E CF 00 03         [ 2] 4495 	ldw	_scan_len+0, x
                                   4496 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1058: if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
      009B21 CD 85 13         [ 4] 4497 	call	_seed
      009B24 4D               [ 1] 4498 	tnz	a
      009B25 26 08            [ 1] 4499 	jrne	00139$
      009B27 35 01 00 25      [ 1] 4500 	mov	_dec_info+1, #0x01
      009B2B 4F               [ 1] 4501 	clr	a
      009B2C CC 9B E2         [ 2] 4502 	jp	00122$
                                   4503 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1059: for (r = 0; r < 2; r++) refine();
      009B2F                       4504 00139$:
      009B2F A6 02            [ 1] 4505 	ld	a, #0x02
      009B31                       4506 00119$:
      009B31 88               [ 1] 4507 	push	a
      009B32 CD 85 B4         [ 4] 4508 	call	_refine
      009B35 84               [ 1] 4509 	pop	a
      009B36 4A               [ 1] 4510 	dec	a
      009B37 26 F8            [ 1] 4511 	jrne	00119$
                                   4512 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1060: calibrate();
      009B39 CD 8F E0         [ 4] 4513 	call	_calibrate
                                   4514 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1061: decide_pass();
      009B3C CD 94 76         [ 4] 4515 	call	_decide_pass
                                   4516 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1062: dec_info.K = g_K;
      009B3F 55 00 39 00 2E   [ 1] 4517 	mov	_dec_info+10, _g_K+1
      009B44 55 00 38 00 2D   [ 1] 4518 	mov	_dec_info+9, _g_K+0
                                   4519 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1063: dec_info.tau = g_tau;
      009B49 55 00 3B 00 30   [ 1] 4520 	mov	_dec_info+12, _g_tau+1
      009B4E 55 00 3A 00 2F   [ 1] 4521 	mov	_dec_info+11, _g_tau+0
                                   4522 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1064: dec_info.infeasible = d_infeas;
      009B53 55 01 00 00 33   [ 1] 4523 	mov	_dec_info+15, _d_infeas+1
      009B58 55 00 FF 00 32   [ 1] 4524 	mov	_dec_info+14, _d_infeas+0
                                   4525 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1065: dec_info.label_err = d_laberr;
      009B5D 55 01 02 00 35   [ 1] 4526 	mov	_dec_info+17, _d_laberr+1
      009B62 55 01 01 00 34   [ 1] 4527 	mov	_dec_info+16, _d_laberr+0
                                   4528 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1066: dec_info.n_seg = d_nseg;
      009B67 55 01 04 00 37   [ 1] 4529 	mov	_dec_info+19, _d_nseg+1
      009B6C 55 01 03 00 36   [ 1] 4530 	mov	_dec_info+18, _d_nseg+0
                                   4531 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
      009B71 0F 02            [ 1] 4532 	clr	(0x02, sp)
      009B73 5F               [ 1] 4533 	clrw	x
      009B74                       4534 00120$:
                                   4535 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: int8_t kb = known_bit(t);
      009B74 89               [ 2] 4536 	pushw	x
      009B75 CD 81 C6         [ 4] 4537 	call	_known_bit
      009B78 6B 03            [ 1] 4538 	ld	(0x03, sp), a
      009B7A 85               [ 2] 4539 	popw	x
                                   4540 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1069: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
      009B7B 0D 01            [ 1] 4541 	tnz	(0x01, sp)
      009B7D 2B 23            [ 1] 4542 	jrmi	00121$
      009B7F 90 93            [ 1] 4543 	ldw	y, x
      009B81 A6 08            [ 1] 4544 	ld	a, #0x08
      009B83 90 62            [ 2] 4545 	div	y, a
      009B85 72 A9 00 E4      [ 2] 4546 	addw	y, #(_d_bits+0)
      009B89 90 F6            [ 1] 4547 	ld	a, (y)
      009B8B 90 97            [ 1] 4548 	ld	yl, a
      009B8D 9F               [ 1] 4549 	ld	a, xl
      009B8E A4 07            [ 1] 4550 	and	a, #0x07
      009B90 27 06            [ 1] 4551 	jreq	00228$
      009B92                       4552 00227$:
      009B92 61               [ 1] 4553 	exg	a, yl
      009B93 44               [ 1] 4554 	srl	a
      009B94 61               [ 1] 4555 	exg	a, yl
      009B95 4A               [ 1] 4556 	dec	a
      009B96 26 FA            [ 1] 4557 	jrne	00227$
      009B98                       4558 00228$:
      009B98 90 9F            [ 1] 4559 	ld	a, yl
      009B9A A4 01            [ 1] 4560 	and	a, #0x01
      009B9C 11 01            [ 1] 4561 	cp	a, (0x01, sp)
      009B9E 27 02            [ 1] 4562 	jreq	00121$
      009BA0 0C 02            [ 1] 4563 	inc	(0x02, sp)
      009BA2                       4564 00121$:
                                   4565 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
      009BA2 5C               [ 1] 4566 	incw	x
      009BA3 A3 00 D8         [ 2] 4567 	cpw	x, #0x00d8
      009BA6 25 CC            [ 1] 4568 	jrc	00120$
                                   4569 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1071: dec_info.violations = viol;
      009BA8 AE 00 31         [ 2] 4570 	ldw	x, #(_dec_info+13)
      009BAB 7B 02            [ 1] 4571 	ld	a, (0x02, sp)
      009BAD F7               [ 1] 4572 	ld	(x), a
                                   4573 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1072: if (viol > 0)               { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
      009BAE 0D 02            [ 1] 4574 	tnz	(0x02, sp)
      009BB0 27 07            [ 1] 4575 	jreq	00110$
      009BB2 35 02 00 25      [ 1] 4576 	mov	_dec_info+1, #0x02
      009BB6 4F               [ 1] 4577 	clr	a
      009BB7 20 29            [ 2] 4578 	jra	00122$
      009BB9                       4579 00110$:
                                   4580 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1073: if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
      009BB9 CE 00 FF         [ 2] 4581 	ldw	x, _d_infeas+0
      009BBC A3 00 04         [ 2] 4582 	cpw	x, #0x0004
      009BBF 23 07            [ 2] 4583 	jrule	00112$
      009BC1 35 03 00 25      [ 1] 4584 	mov	_dec_info+1, #0x03
      009BC5 4F               [ 1] 4585 	clr	a
      009BC6 20 1A            [ 2] 4586 	jra	00122$
      009BC8                       4587 00112$:
                                   4588 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1074: if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
      009BC8 CE 01 01         [ 2] 4589 	ldw	x, _d_laberr+0
      009BCB A3 00 06         [ 2] 4590 	cpw	x, #0x0006
      009BCE 23 07            [ 2] 4591 	jrule	00114$
      009BD0 35 04 00 25      [ 1] 4592 	mov	_dec_info+1, #0x04
      009BD4 4F               [ 1] 4593 	clr	a
      009BD5 20 0B            [ 2] 4594 	jra	00122$
      009BD7                       4595 00114$:
                                   4596 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1075: dec_info.path = chase(out);                                      /* R5..R8 inside */
      009BD7 AE 00 24         [ 2] 4597 	ldw	x, #(_dec_info+0)
      009BDA 89               [ 2] 4598 	pushw	x
      009BDB 1E 09            [ 2] 4599 	ldw	x, (0x09, sp)
      009BDD CD 99 83         [ 4] 4600 	call	_chase
      009BE0 85               [ 2] 4601 	popw	x
      009BE1 F7               [ 1] 4602 	ld	(x), a
                                   4603 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1076: return dec_info.path;
      009BE2                       4604 00122$:
                                   4605 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1077: }
      009BE2 1E 03            [ 2] 4606 	ldw	x, (3, sp)
      009BE4 5B 08            [ 2] 4607 	addw	sp, #8
      009BE6 FC               [ 2] 4608 	jp	(x)
                                   4609 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1079: int16_t dec_eps_centi(void)
                                   4610 ;	-----------------------------------------
                                   4611 ;	 function dec_eps_centi
                                   4612 ;	-----------------------------------------
      009BE7                       4613 _dec_eps_centi:
      009BE7 52 04            [ 2] 4614 	sub	sp, #4
                                   4615 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1084: return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
      009BE9 CE 00 2D         [ 2] 4616 	ldw	x, _dec_info+9
      009BEC 1F 03            [ 2] 4617 	ldw	(0x03, sp), x
      009BEE 5F               [ 1] 4618 	clrw	x
      009BEF 1F 01            [ 2] 4619 	ldw	(0x01, sp), x
      009BF1 90 AE CC CD      [ 2] 4620 	ldw	y, #0xcccd
      009BF5 72 F2 03         [ 2] 4621 	subw	y, (0x03, sp)
      009BF8 1E 01            [ 2] 4622 	ldw	x, (0x01, sp)
      009BFA 24 01            [ 1] 4623 	jrnc	00103$
      009BFC 5C               [ 1] 4624 	incw	x
      009BFD                       4625 00103$:
      009BFD 50               [ 2] 4626 	negw	x
      009BFE 90 89            [ 2] 4627 	pushw	y
      009C00 89               [ 2] 4628 	pushw	x
      009C01 4B 10            [ 1] 4629 	push	#0x10
      009C03 4B 27            [ 1] 4630 	push	#0x27
      009C05 5F               [ 1] 4631 	clrw	x
      009C06 89               [ 2] 4632 	pushw	x
                                   4633 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1085: / (int32_t)dec_info.K);
      009C07 CD 9D 12         [ 4] 4634 	call	__mullong
      009C0A 5B 08            [ 2] 4635 	addw	sp, #8
      009C0C 7B 04            [ 1] 4636 	ld	a, (0x04, sp)
      009C0E 88               [ 1] 4637 	push	a
      009C0F 7B 04            [ 1] 4638 	ld	a, (0x04, sp)
      009C11 88               [ 1] 4639 	push	a
      009C12 4F               [ 1] 4640 	clr	a
      009C13 88               [ 1] 4641 	push	a
      009C14 4F               [ 1] 4642 	clr	a
      009C15 88               [ 1] 4643 	push	a
      009C16 89               [ 2] 4644 	pushw	x
      009C17 90 89            [ 2] 4645 	pushw	y
      009C19 CD 9C 8E         [ 4] 4646 	call	__divslong
                                   4647 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1086: }
      009C1C 5B 0C            [ 2] 4648 	addw	sp, #12
      009C1E 81               [ 4] 4649 	ret
                                   4650 	.area CODE
                                   4651 	.area CONST
                                   4652 	.area CONST
      00802D                       4653 _HDR:
      00802D FF                    4654 	.db #0xff	; 255
      00802E 00                    4655 	.db #0x00	; 0
      00802F AA                    4656 	.db #0xaa	; 170
      008030 65                    4657 	.db #0x65	; 101	'e'
                                   4658 	.area CODE
                                   4659 	.area CONST
      008031                       4660 _TRL:
      008031 9A                    4661 	.db #0x9a	; 154
      008032 55                    4662 	.db #0x55	; 85	'U'
      008033 00                    4663 	.db #0x00	; 0
      008034 FF                    4664 	.db #0xff	; 255
                                   4665 	.area CODE
                                   4666 	.area CONST
      008035                       4667 _XPOW:
      008035 01                    4668 	.db #0x01	; 1
      008036 02                    4669 	.db #0x02	; 2
      008037 04                    4670 	.db #0x04	; 4
      008038 08                    4671 	.db #0x08	; 8
      008039 10                    4672 	.db #0x10	; 16
      00803A 20                    4673 	.db #0x20	; 32
      00803B 40                    4674 	.db #0x40	; 64
      00803C 80                    4675 	.db #0x80	; 128
      00803D 07                    4676 	.db #0x07	; 7
      00803E 0E                    4677 	.db #0x0e	; 14
      00803F 1C                    4678 	.db #0x1c	; 28
      008040 38                    4679 	.db #0x38	; 56	'8'
      008041 70                    4680 	.db #0x70	; 112	'p'
      008042 E0                    4681 	.db #0xe0	; 224
      008043 C7                    4682 	.db #0xc7	; 199
      008044 89                    4683 	.db #0x89	; 137
      008045 15                    4684 	.db #0x15	; 21
      008046 2A                    4685 	.db #0x2a	; 42
      008047 54                    4686 	.db #0x54	; 84	'T'
      008048 A8                    4687 	.db #0xa8	; 168
      008049 57                    4688 	.db #0x57	; 87	'W'
      00804A AE                    4689 	.db #0xae	; 174
      00804B 5B                    4690 	.db #0x5b	; 91
      00804C B6                    4691 	.db #0xb6	; 182
      00804D 6B                    4692 	.db #0x6b	; 107	'k'
      00804E D6                    4693 	.db #0xd6	; 214
      00804F AB                    4694 	.db #0xab	; 171
      008050 51                    4695 	.db #0x51	; 81	'Q'
      008051 A2                    4696 	.db #0xa2	; 162
      008052 43                    4697 	.db #0x43	; 67	'C'
      008053 86                    4698 	.db #0x86	; 134
      008054 0B                    4699 	.db #0x0b	; 11
      008055 16                    4700 	.db #0x16	; 22
      008056 2C                    4701 	.db #0x2c	; 44
      008057 58                    4702 	.db #0x58	; 88	'X'
      008058 B0                    4703 	.db #0xb0	; 176
      008059 67                    4704 	.db #0x67	; 103	'g'
      00805A CE                    4705 	.db #0xce	; 206
      00805B 9B                    4706 	.db #0x9b	; 155
      00805C 31                    4707 	.db #0x31	; 49	'1'
      00805D 62                    4708 	.db #0x62	; 98	'b'
      00805E C4                    4709 	.db #0xc4	; 196
      00805F 8F                    4710 	.db #0x8f	; 143
      008060 19                    4711 	.db #0x19	; 25
      008061 32                    4712 	.db #0x32	; 50	'2'
      008062 64                    4713 	.db #0x64	; 100	'd'
      008063 C8                    4714 	.db #0xc8	; 200
      008064 97                    4715 	.db #0x97	; 151
      008065 29                    4716 	.db #0x29	; 41
      008066 52                    4717 	.db #0x52	; 82	'R'
      008067 A4                    4718 	.db #0xa4	; 164
      008068 4F                    4719 	.db #0x4f	; 79	'O'
      008069 9E                    4720 	.db #0x9e	; 158
      00806A 3B                    4721 	.db #0x3b	; 59
      00806B 76                    4722 	.db #0x76	; 118	'v'
      00806C EC                    4723 	.db #0xec	; 236
      00806D DF                    4724 	.db #0xdf	; 223
      00806E B9                    4725 	.db #0xb9	; 185
      00806F 75                    4726 	.db #0x75	; 117	'u'
      008070 EA                    4727 	.db #0xea	; 234
      008071 D3                    4728 	.db #0xd3	; 211
      008072 A1                    4729 	.db #0xa1	; 161
      008073 45                    4730 	.db #0x45	; 69	'E'
      008074 8A                    4731 	.db #0x8a	; 138
      008075 13                    4732 	.db #0x13	; 19
      008076 26                    4733 	.db #0x26	; 38
      008077 4C                    4734 	.db #0x4c	; 76	'L'
      008078 98                    4735 	.db #0x98	; 152
      008079 37                    4736 	.db #0x37	; 55	'7'
      00807A 6E                    4737 	.db #0x6e	; 110	'n'
      00807B DC                    4738 	.db #0xdc	; 220
      00807C BF                    4739 	.db #0xbf	; 191
      00807D 79                    4740 	.db #0x79	; 121	'y'
      00807E F2                    4741 	.db #0xf2	; 242
      00807F E3                    4742 	.db #0xe3	; 227
      008080 C1                    4743 	.db #0xc1	; 193
      008081 85                    4744 	.db #0x85	; 133
      008082 0D                    4745 	.db #0x0d	; 13
      008083 1A                    4746 	.db #0x1a	; 26
      008084 34                    4747 	.db #0x34	; 52	'4'
      008085 68                    4748 	.db #0x68	; 104	'h'
      008086 D0                    4749 	.db #0xd0	; 208
      008087 A7                    4750 	.db #0xa7	; 167
      008088 49                    4751 	.db #0x49	; 73	'I'
      008089 92                    4752 	.db #0x92	; 146
      00808A 23                    4753 	.db #0x23	; 35
      00808B 46                    4754 	.db #0x46	; 70	'F'
      00808C 8C                    4755 	.db #0x8c	; 140
      00808D 1F                    4756 	.db #0x1f	; 31
      00808E 3E                    4757 	.db #0x3e	; 62
      00808F 7C                    4758 	.db #0x7c	; 124
      008090 F8                    4759 	.db #0xf8	; 248
      008091 F7                    4760 	.db #0xf7	; 247
      008092 E9                    4761 	.db #0xe9	; 233
      008093 D5                    4762 	.db #0xd5	; 213
      008094 AD                    4763 	.db #0xad	; 173
      008095 5D                    4764 	.db #0x5d	; 93
      008096 BA                    4765 	.db #0xba	; 186
      008097 73                    4766 	.db #0x73	; 115	's'
      008098 E6                    4767 	.db #0xe6	; 230
      008099 CB                    4768 	.db #0xcb	; 203
      00809A 91                    4769 	.db #0x91	; 145
      00809B 25                    4770 	.db #0x25	; 37
      00809C 4A                    4771 	.db #0x4a	; 74	'J'
      00809D 94                    4772 	.db #0x94	; 148
      00809E 2F                    4773 	.db #0x2f	; 47
      00809F 5E                    4774 	.db #0x5e	; 94
      0080A0 BC                    4775 	.db #0xbc	; 188
      0080A1 7F                    4776 	.db #0x7f	; 127
      0080A2 FE                    4777 	.db #0xfe	; 254
      0080A3 FB                    4778 	.db #0xfb	; 251
      0080A4 F1                    4779 	.db #0xf1	; 241
      0080A5 E5                    4780 	.db #0xe5	; 229
      0080A6 CD                    4781 	.db #0xcd	; 205
      0080A7 9D                    4782 	.db #0x9d	; 157
      0080A8 3D                    4783 	.db #0x3d	; 61
      0080A9 7A                    4784 	.db #0x7a	; 122	'z'
      0080AA F4                    4785 	.db #0xf4	; 244
      0080AB EF                    4786 	.db #0xef	; 239
      0080AC D9                    4787 	.db #0xd9	; 217
      0080AD B5                    4788 	.db #0xb5	; 181
      0080AE 6D                    4789 	.db #0x6d	; 109	'm'
      0080AF DA                    4790 	.db #0xda	; 218
      0080B0 B3                    4791 	.db #0xb3	; 179
      0080B1 61                    4792 	.db #0x61	; 97	'a'
      0080B2 C2                    4793 	.db #0xc2	; 194
      0080B3 83                    4794 	.db #0x83	; 131
                                   4795 	.area CODE
                                   4796 	.area CONST
      0080B4                       4797 _O_CY:
      0080B4 00                    4798 	.db #0x00	; 0
      0080B5 04                    4799 	.db #0x04	; 4
      0080B6 09                    4800 	.db #0x09	; 9
      0080B7 0D                    4801 	.db #0x0d	; 13
      0080B8 11                    4802 	.db #0x11	; 17
      0080B9 15                    4803 	.db #0x15	; 21
      0080BA 1B                    4804 	.db #0x1b	; 27
      0080BB 20                    4805 	.db #0x20	; 32
                                   4806 	.area CODE
                                   4807 	.area CONST
      0080BC                       4808 _W_CY:
      0080BC 00                    4809 	.db #0x00	;  0
      0080BD FF                    4810 	.db #0xff	; -1
      0080BE 00                    4811 	.db #0x00	;  0
      0080BF 02                    4812 	.db #0x02	;  2
      0080C0 00                    4813 	.db #0x00	;  0
      0080C1 00                    4814 	.db #0x00	;  0
      0080C2 00                    4815 	.db #0x00	;  0
      0080C3 01                    4816 	.db #0x01	;  1
                                   4817 	.area CODE
                                   4818 	.area INITIALIZER
                                   4819 	.area CABS (ABS)
