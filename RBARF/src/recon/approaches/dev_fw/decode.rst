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
                                     13 	.globl _ws_decode_ex
                                     14 	.globl _dec_eps_centi
                                     15 ;--------------------------------------------------------
                                     16 ; ram data
                                     17 ;--------------------------------------------------------
                                     18 	.area DATA
      000001                         19 _dec_info::
      000001                         20 	.ds 20
      000015                         21 _g_K:
      000015                         22 	.ds 2
      000017                         23 _g_tau:
      000017                         24 	.ds 2
      000019                         25 _c_lo0:
      000019                         26 	.ds 2
      00001B                         27 _c_hi0:
      00001B                         28 	.ds 2
      00001D                         29 _c_lo1:
      00001D                         30 	.ds 2
      00001F                         31 _c_hi1:
      00001F                         32 	.ds 2
      000021                         33 _c_n0:
      000021                         34 	.ds 1
      000022                         35 _c_n1:
      000022                         36 	.ds 1
      000023                         37 _c_h0c:
      000023                         38 	.ds 2
      000025                         39 _c_h1c:
      000025                         40 	.ds 2
      000027                         41 _c_d56:
      000027                         42 	.ds 2
      000029                         43 _c_hist:
      000029                         44 	.ds 128
      0000A9                         45 _c_labx0:
      0000A9                         46 	.ds 4
      0000AD                         47 _c_labx1:
      0000AD                         48 	.ds 4
      0000B1                         49 _c_labx0b:
      0000B1                         50 	.ds 4
      0000B5                         51 _c_labx1b:
      0000B5                         52 	.ds 4
      0000B9                         53 _c_c0:
      0000B9                         54 	.ds 4
      0000BD                         55 _c_gap56:
      0000BD                         56 	.ds 4
      0000C1                         57 _d_bits:
      0000C1                         58 	.ds 24
      0000D9                         59 _d_infeas:
      0000D9                         60 	.ds 2
      0000DB                         61 _d_laberr:
      0000DB                         62 	.ds 2
      0000DD                         63 _d_nseg:
      0000DD                         64 	.ds 2
      0000DF                         65 _d_costs:
      0000DF                         66 	.ds 32
      0000FF                         67 _d_inter:
      0000FF                         68 	.ds 2
      000101                         69 _v_cand_t:
      000101                         70 	.ds 10
      00010B                         71 _v_cand_m:
      00010B                         72 	.ds 5
      000110                         73 _v_ncand:
      000110                         74 	.ds 1
      000111                         75 _v_nweak:
      000111                         76 	.ds 2
      000113                         77 _v_ntied:
      000113                         78 	.ds 2
      000115                         79 _v_tiepend:
      000115                         80 	.ds 2
      000117                         81 _d_pp:
      000117                         82 	.ds 16
      000127                         83 _ss:
      000127                         84 	.ds 20
                                     85 ;--------------------------------------------------------
                                     86 ; ram data
                                     87 ;--------------------------------------------------------
                                     88 	.area INITIALIZED
                                     89 ;--------------------------------------------------------
                                     90 ; absolute external ram data
                                     91 ;--------------------------------------------------------
                                     92 	.area DABS (ABS)
                                     93 
                                     94 ; default segment ordering for linker
                                     95 	.area HOME
                                     96 	.area GSINIT
                                     97 	.area GSFINAL
                                     98 	.area CONST
                                     99 	.area INITIALIZER
                                    100 	.area CODE
                                    101 
                                    102 ;--------------------------------------------------------
                                    103 ; global & static initialisations
                                    104 ;--------------------------------------------------------
                                    105 	.area HOME
                                    106 	.area GSINIT
                                    107 	.area GSFINAL
                                    108 	.area GSINIT
                                    109 ;--------------------------------------------------------
                                    110 ; Home
                                    111 ;--------------------------------------------------------
                                    112 	.area HOME
                                    113 	.area HOME
                                    114 ;--------------------------------------------------------
                                    115 ; code
                                    116 ;--------------------------------------------------------
                                    117 	.area CODE
                                    118 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 127: static int8_t known_bit(uint16_t t)
                                    119 ;	-----------------------------------------
                                    120 ;	 function known_bit
                                    121 ;	-----------------------------------------
      008137                        122 _known_bit:
      008137 88               [ 1]  123 	push	a
                                    124 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 129: if (t < 32)
      008138 90 93            [ 1]  125 	ldw	y, x
      00813A A3 00 20         [ 2]  126 	cpw	x, #0x0020
      00813D 24 20            [ 1]  127 	jrnc	00102$
                                    128 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 130: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
      00813F 93               [ 1]  129 	ldw	x, y
      008140 54               [ 2]  130 	srlw	x
      008141 54               [ 2]  131 	srlw	x
      008142 54               [ 2]  132 	srlw	x
      008143 1C 80 2D         [ 2]  133 	addw	x, #(_HDR+0)
      008146 F6               [ 1]  134 	ld	a, (x)
      008147 97               [ 1]  135 	ld	xl, a
      008148 90 9F            [ 1]  136 	ld	a, yl
      00814A A4 07            [ 1]  137 	and	a, #0x07
      00814C 6B 01            [ 1]  138 	ld	(0x01, sp), a
      00814E A6 07            [ 1]  139 	ld	a, #0x07
      008150 10 01            [ 1]  140 	sub	a, (0x01, sp)
      008152 27 06            [ 1]  141 	jreq	00125$
      008154                        142 00124$:
      008154 41               [ 1]  143 	exg	a, xl
      008155 44               [ 1]  144 	srl	a
      008156 41               [ 1]  145 	exg	a, xl
      008157 4A               [ 1]  146 	dec	a
      008158 26 FA            [ 1]  147 	jrne	00124$
      00815A                        148 00125$:
      00815A 9F               [ 1]  149 	ld	a, xl
      00815B A4 01            [ 1]  150 	and	a, #0x01
      00815D 20 2B            [ 2]  151 	jra	00105$
      00815F                        152 00102$:
                                    153 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 131: if (t >= NB - 32) {
      00815F 90 A3 00 A0      [ 2]  154 	cpw	y, #0x00a0
      008163 25 23            [ 1]  155 	jrc	00104$
                                    156 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 132: uint16_t u = t - (NB - 32);
      008165 1D 00 A0         [ 2]  157 	subw	x, #0x00a0
                                    158 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 133: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
      008168 90 93            [ 1]  159 	ldw	y, x
      00816A 54               [ 2]  160 	srlw	x
      00816B 54               [ 2]  161 	srlw	x
      00816C 54               [ 2]  162 	srlw	x
      00816D 1C 80 31         [ 2]  163 	addw	x, #(_TRL+0)
      008170 F6               [ 1]  164 	ld	a, (x)
      008171 97               [ 1]  165 	ld	xl, a
      008172 90 9F            [ 1]  166 	ld	a, yl
      008174 A4 07            [ 1]  167 	and	a, #0x07
      008176 6B 01            [ 1]  168 	ld	(0x01, sp), a
      008178 A6 07            [ 1]  169 	ld	a, #0x07
      00817A 10 01            [ 1]  170 	sub	a, (0x01, sp)
      00817C 27 06            [ 1]  171 	jreq	00128$
      00817E                        172 00127$:
      00817E 41               [ 1]  173 	exg	a, xl
      00817F 44               [ 1]  174 	srl	a
      008180 41               [ 1]  175 	exg	a, xl
      008181 4A               [ 1]  176 	dec	a
      008182 26 FA            [ 1]  177 	jrne	00127$
      008184                        178 00128$:
      008184 9F               [ 1]  179 	ld	a, xl
      008185 A4 01            [ 1]  180 	and	a, #0x01
                                    181 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 135: return -1;
      008187 C5                     182 	.byte 0xc5
      008188                        183 00104$:
      008188 A6 FF            [ 1]  184 	ld	a, #0xff
      00818A                        185 00105$:
                                    186 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 136: }
      00818A 5B 01            [ 2]  187 	addw	sp, #1
      00818C 81               [ 4]  188 	ret
                                    189 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 301: static int32_t map_raw(uint16_t t)
                                    190 ;	-----------------------------------------
                                    191 ;	 function map_raw
                                    192 ;	-----------------------------------------
      00818D                        193 _map_raw:
      00818D 52 08            [ 2]  194 	sub	sp, #8
                                    195 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 303: return (int32_t)((uint32_t)t * g_K >> KQ) + g_tau;
      00818F 90 CE 00 15      [ 2]  196 	ldw	y, _g_K+0
      008193 90 89            [ 2]  197 	pushw	y
      008195 CD 9A 4E         [ 4]  198 	call	___muluint2ulong
      008198 5B 02            [ 2]  199 	addw	sp, #2
      00819A 51               [ 1]  200 	exgw	x, y
      00819B A6 0B            [ 1]  201 	ld	a, #0x0b
      00819D                        202 00103$:
      00819D 54               [ 2]  203 	srlw	x
      00819E 90 56            [ 2]  204 	rrcw	y
      0081A0 4A               [ 1]  205 	dec	a
      0081A1 26 FA            [ 1]  206 	jrne	00103$
      0081A3 1F 01            [ 2]  207 	ldw	(0x01, sp), x
      0081A5 CE 00 17         [ 2]  208 	ldw	x, _g_tau+0
      0081A8 1F 07            [ 2]  209 	ldw	(0x07, sp), x
      0081AA 5F               [ 1]  210 	clrw	x
      0081AB 0D 07            [ 1]  211 	tnz	(0x07, sp)
      0081AD 2A 01            [ 1]  212 	jrpl	00105$
      0081AF 5A               [ 2]  213 	decw	x
      0081B0                        214 00105$:
      0081B0 72 F9 07         [ 2]  215 	addw	y, (0x07, sp)
      0081B3 9F               [ 1]  216 	ld	a, xl
      0081B4 19 02            [ 1]  217 	adc	a, (0x02, sp)
      0081B6 02               [ 1]  218 	rlwa	x
      0081B7 19 01            [ 1]  219 	adc	a, (0x01, sp)
      0081B9 95               [ 1]  220 	ld	xh, a
      0081BA 51               [ 1]  221 	exgw	x, y
                                    222 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 304: }
      0081BB 5B 08            [ 2]  223 	addw	sp, #8
      0081BD 81               [ 4]  224 	ret
                                    225 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 308: static uint8_t seed(void)
                                    226 ;	-----------------------------------------
                                    227 ;	 function seed
                                    228 ;	-----------------------------------------
      0081BE                        229 _seed:
      0081BE 52 06            [ 2]  230 	sub	sp, #6
                                    231 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 311: uint16_t r0m = 0, flm = 0;
      0081C0 5F               [ 1]  232 	clrw	x
      0081C1 1F 01            [ 2]  233 	ldw	(0x01, sp), x
      0081C3 5F               [ 1]  234 	clrw	x
      0081C4 1F 03            [ 2]  235 	ldw	(0x03, sp), x
                                    236 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 313: scan_init();
      0081C6 CD 96 7D         [ 4]  237 	call	_scan_init
                                    238 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 314: while (scan_next()) {
      0081C9 5F               [ 1]  239 	clrw	x
      0081CA 1F 05            [ 2]  240 	ldw	(0x05, sp), x
      0081CC                        241 00103$:
      0081CC CD 96 A6         [ 4]  242 	call	_scan_next
      0081CF 4D               [ 1]  243 	tnz	a
      0081D0 27 1F            [ 1]  244 	jreq	00105$
                                    245 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 315: if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
      0081D2 1E 05            [ 2]  246 	ldw	x, (0x05, sp)
      0081D4 26 0A            [ 1]  247 	jrne	00102$
      0081D6 CE 01 50         [ 2]  248 	ldw	x, _scan_ra+0
      0081D9 72 BB 01 52      [ 2]  249 	addw	x, _scan_rb+0
      0081DD 54               [ 2]  250 	srlw	x
      0081DE 1F 01            [ 2]  251 	ldw	(0x01, sp), x
      0081E0                        252 00102$:
                                    253 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 316: flm = (uint16_t)((scan_fa + scan_fb) >> 1);
      0081E0 CE 01 54         [ 2]  254 	ldw	x, _scan_fa+0
      0081E3 72 BB 01 56      [ 2]  255 	addw	x, _scan_fb+0
      0081E7 54               [ 2]  256 	srlw	x
      0081E8 1F 03            [ 2]  257 	ldw	(0x03, sp), x
                                    258 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 317: np++;
      0081EA 1E 05            [ 2]  259 	ldw	x, (0x05, sp)
      0081EC 5C               [ 1]  260 	incw	x
      0081ED 1F 05            [ 2]  261 	ldw	(0x05, sp), x
      0081EF 20 DB            [ 2]  262 	jra	00103$
      0081F1                        263 00105$:
                                    264 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 319: if (np < 8 || flm <= r0m) return 0;
      0081F1 1E 05            [ 2]  265 	ldw	x, (0x05, sp)
      0081F3 A3 00 08         [ 2]  266 	cpw	x, #0x0008
      0081F6 25 06            [ 1]  267 	jrc	00106$
      0081F8 1E 03            [ 2]  268 	ldw	x, (0x03, sp)
      0081FA 13 01            [ 2]  269 	cpw	x, (0x01, sp)
      0081FC 22 03            [ 1]  270 	jrugt	00107$
      0081FE                        271 00106$:
      0081FE 4F               [ 1]  272 	clr	a
      0081FF 20 60            [ 2]  273 	jra	00112$
      008201                        274 00107$:
                                    275 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 321: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
      008201 16 03            [ 2]  276 	ldw	y, (0x03, sp)
      008203 72 F2 01         [ 2]  277 	subw	y, (0x01, sp)
      008206 5F               [ 1]  278 	clrw	x
      008207 90 89            [ 2]  279 	pushw	y
      008209 89               [ 2]  280 	pushw	x
      00820A 4B 00            [ 1]  281 	push	#0x00
      00820C 4B A0            [ 1]  282 	push	#0xa0
      00820E 4B F9            [ 1]  283 	push	#0xf9
      008210 4B 0B            [ 1]  284 	push	#0x0b
                                    285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 322: if (K < K_MIN || K > K_MAX) return 0;
      008212 CD 9A CC         [ 4]  286 	call	__divulong
      008215 5B 08            [ 2]  287 	addw	sp, #8
      008217 1F 05            [ 2]  288 	ldw	(0x05, sp), x
      008219 17 03            [ 2]  289 	ldw	(0x03, sp), y
      00821B 1E 05            [ 2]  290 	ldw	x, (0x05, sp)
      00821D A3 B3 B0         [ 2]  291 	cpw	x, #0xb3b0
      008220 7B 04            [ 1]  292 	ld	a, (0x04, sp)
      008222 A2 00            [ 1]  293 	sbc	a, #0x00
      008224 7B 03            [ 1]  294 	ld	a, (0x03, sp)
      008226 A2 00            [ 1]  295 	sbc	a, #0x00
      008228 25 0D            [ 1]  296 	jrc	00109$
      00822A AE EA 60         [ 2]  297 	ldw	x, #0xea60
      00822D 13 05            [ 2]  298 	cpw	x, (0x05, sp)
      00822F 4F               [ 1]  299 	clr	a
      008230 12 04            [ 1]  300 	sbc	a, (0x04, sp)
      008232 4F               [ 1]  301 	clr	a
      008233 12 03            [ 1]  302 	sbc	a, (0x03, sp)
      008235 24 03            [ 1]  303 	jrnc	00110$
      008237                        304 00109$:
      008237 4F               [ 1]  305 	clr	a
      008238 20 27            [ 2]  306 	jra	00112$
      00823A                        307 00110$:
                                    308 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 323: g_K = (uint16_t)K;
      00823A 1E 05            [ 2]  309 	ldw	x, (0x05, sp)
      00823C CF 00 15         [ 2]  310 	ldw	_g_K+0, x
                                    311 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 324: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
      00823F 16 01            [ 2]  312 	ldw	y, (0x01, sp)
      008241 CE 00 15         [ 2]  313 	ldw	x, _g_K+0
      008244 89               [ 2]  314 	pushw	x
      008245 93               [ 1]  315 	ldw	x, y
      008246 CD 9A 4E         [ 4]  316 	call	___muluint2ulong
      008249 5B 02            [ 2]  317 	addw	sp, #2
      00824B 51               [ 1]  318 	exgw	x, y
      00824C A6 0B            [ 1]  319 	ld	a, #0x0b
      00824E                        320 00162$:
      00824E 54               [ 2]  321 	srlw	x
      00824F 90 56            [ 2]  322 	rrcw	y
      008251 4A               [ 1]  323 	dec	a
      008252 26 FA            [ 1]  324 	jrne	00162$
      008254 17 05            [ 2]  325 	ldw	(0x05, sp), y
      008256 AE 02 00         [ 2]  326 	ldw	x, #0x0200
      008259 72 F0 05         [ 2]  327 	subw	x, (0x05, sp)
      00825C CF 00 17         [ 2]  328 	ldw	_g_tau+0, x
                                    329 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 325: return 1;
      00825F A6 01            [ 1]  330 	ld	a, #0x01
      008261                        331 00112$:
                                    332 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 326: }
      008261 5B 06            [ 2]  333 	addw	sp, #6
      008263 81               [ 4]  334 	ret
                                    335 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 330: static void refine(void)
                                    336 ;	-----------------------------------------
                                    337 ;	 function refine
                                    338 ;	-----------------------------------------
      008264                        339 _refine:
      008264 52 28            [ 2]  340 	sub	sp, #40
                                    341 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 335: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
      008266 5F               [ 1]  342 	clrw	x
      008267 1F 17            [ 2]  343 	ldw	(0x17, sp), x
      008269 1F 15            [ 2]  344 	ldw	(0x15, sp), x
      00826B 5F               [ 1]  345 	clrw	x
      00826C 1F 1B            [ 2]  346 	ldw	(0x1b, sp), x
      00826E 1F 19            [ 2]  347 	ldw	(0x19, sp), x
                                    348 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 336: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
      008270 5F               [ 1]  349 	clrw	x
      008271 1F 1F            [ 2]  350 	ldw	(0x1f, sp), x
      008273 1F 1D            [ 2]  351 	ldw	(0x1d, sp), x
      008275 5F               [ 1]  352 	clrw	x
      008276 1F 23            [ 2]  353 	ldw	(0x23, sp), x
      008278 1F 21            [ 2]  354 	ldw	(0x21, sp), x
                                    355 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 340: scan_init();
      00827A CD 96 7D         [ 4]  356 	call	_scan_init
                                    357 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 341: while (scan_next()) {
      00827D 5F               [ 1]  358 	clrw	x
      00827E 1F 25            [ 2]  359 	ldw	(0x25, sp), x
      008280 5F               [ 1]  360 	clrw	x
      008281 1F 27            [ 2]  361 	ldw	(0x27, sp), x
      008283                        362 00108$:
      008283 CD 96 A6         [ 4]  363 	call	_scan_next
      008286 6B 14            [ 1]  364 	ld	(0x14, sp), a
      008288 26 03            [ 1]  365 	jrne	00186$
      00828A CC 83 4B         [ 2]  366 	jp	00110$
      00828D                        367 00186$:
                                    368 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 345: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      00828D CE 01 50         [ 2]  369 	ldw	x, _scan_ra+0
      008290 72 BB 01 52      [ 2]  370 	addw	x, _scan_rb+0
      008294 54               [ 2]  371 	srlw	x
      008295 CD 81 8D         [ 4]  372 	call	_map_raw
      008298 1F 0D            [ 2]  373 	ldw	(0x0d, sp), x
      00829A 17 0B            [ 2]  374 	ldw	(0x0b, sp), y
                                    375 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 346: if (y < 0) y = 0;
      00829C 0D 0B            [ 1]  376 	tnz	(0x0b, sp)
      00829E 2A 05            [ 1]  377 	jrpl	00102$
      0082A0 5F               [ 1]  378 	clrw	x
      0082A1 1F 0D            [ 2]  379 	ldw	(0x0d, sp), x
      0082A3 1F 0B            [ 2]  380 	ldw	(0x0b, sp), x
      0082A5                        381 00102$:
                                    382 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 347: if ((uint32_t)y > y_end) break;
      0082A5 16 0D            [ 2]  383 	ldw	y, (0x0d, sp)
      0082A7 17 11            [ 2]  384 	ldw	(0x11, sp), y
      0082A9 16 0B            [ 2]  385 	ldw	y, (0x0b, sp)
      0082AB 17 0F            [ 2]  386 	ldw	(0x0f, sp), y
      0082AD AE 82 A4         [ 2]  387 	ldw	x, #0x82a4
      0082B0 13 11            [ 2]  388 	cpw	x, (0x11, sp)
      0082B2 A6 01            [ 1]  389 	ld	a, #0x01
      0082B4 12 10            [ 1]  390 	sbc	a, (0x10, sp)
      0082B6 4F               [ 1]  391 	clr	a
      0082B7 12 0F            [ 1]  392 	sbc	a, (0x0f, sp)
      0082B9 24 03            [ 1]  393 	jrnc	00188$
      0082BB CC 83 4B         [ 2]  394 	jp	00110$
      0082BE                        395 00188$:
                                    396 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 348: q = ((uint32_t)y + BIT_H) >> BIT_SH;
      0082BE 7B 11            [ 1]  397 	ld	a, (0x11, sp)
      0082C0 AB 01            [ 1]  398 	add	a, #0x01
      0082C2 1E 0F            [ 2]  399 	ldw	x, (0x0f, sp)
      0082C4 24 01            [ 1]  400 	jrnc	00189$
      0082C6 5C               [ 1]  401 	incw	x
      0082C7                        402 00189$:
      0082C7 02               [ 1]  403 	rlwa	x
      0082C8 0F 07            [ 1]  404 	clr	(0x07, sp)
      0082CA 44               [ 1]  405 	srl	a
      0082CB 56               [ 2]  406 	rrcw	x
                                    407 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 349: e = (int16_t)(y - (int32_t)(q << BIT_SH));
      0082CC 4F               [ 1]  408 	clr	a
      0082CD 02               [ 1]  409 	rlwa	x
      0082CE 58               [ 2]  410 	sllw	x
      0082CF 16 0D            [ 2]  411 	ldw	y, (0x0d, sp)
      0082D1 17 13            [ 2]  412 	ldw	(0x13, sp), y
      0082D3 50               [ 2]  413 	negw	x
      0082D4 72 FB 13         [ 2]  414 	addw	x, (0x13, sp)
                                    415 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 350: if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
      0082D7 1F 0D            [ 2]  416 	ldw	(0x0d, sp), x
      0082D9 5F               [ 1]  417 	clrw	x
      0082DA 0D 0D            [ 1]  418 	tnz	(0x0d, sp)
      0082DC 2A 01            [ 1]  419 	jrpl	00190$
      0082DE 5A               [ 2]  420 	decw	x
      0082DF                        421 00190$:
      0082DF 7B 12            [ 1]  422 	ld	a, (0x12, sp)
      0082E1 A1 00            [ 1]  423 	cp	a, #0x00
      0082E3 7B 11            [ 1]  424 	ld	a, (0x11, sp)
      0082E5 A2 C2            [ 1]  425 	sbc	a, #0xc2
      0082E7 7B 10            [ 1]  426 	ld	a, (0x10, sp)
      0082E9 A2 00            [ 1]  427 	sbc	a, #0x00
      0082EB 7B 0F            [ 1]  428 	ld	a, (0x0f, sp)
      0082ED A2 00            [ 1]  429 	sbc	a, #0x00
      0082EF 24 2D            [ 1]  430 	jrnc	00106$
      0082F1 16 25            [ 2]  431 	ldw	y, (0x25, sp)
      0082F3 90 5C            [ 1]  432 	incw	y
      0082F5 17 25            [ 2]  433 	ldw	(0x25, sp), y
      0082F7 16 0D            [ 2]  434 	ldw	y, (0x0d, sp)
      0082F9 72 F9 17         [ 2]  435 	addw	y, (0x17, sp)
      0082FC 17 17            [ 2]  436 	ldw	(0x17, sp), y
      0082FE 9F               [ 1]  437 	ld	a, xl
      0082FF 19 16            [ 1]  438 	adc	a, (0x16, sp)
      008301 6B 16            [ 1]  439 	ld	(0x16, sp), a
      008303 9E               [ 1]  440 	ld	a, xh
      008304 19 15            [ 1]  441 	adc	a, (0x15, sp)
      008306 6B 15            [ 1]  442 	ld	(0x15, sp), a
      008308 1E 1F            [ 2]  443 	ldw	x, (0x1f, sp)
      00830A 72 FB 11         [ 2]  444 	addw	x, (0x11, sp)
      00830D 1F 1F            [ 2]  445 	ldw	(0x1f, sp), x
      00830F 7B 1E            [ 1]  446 	ld	a, (0x1e, sp)
      008311 19 10            [ 1]  447 	adc	a, (0x10, sp)
      008313 6B 1E            [ 1]  448 	ld	(0x1e, sp), a
      008315 7B 1D            [ 1]  449 	ld	a, (0x1d, sp)
      008317 19 0F            [ 1]  450 	adc	a, (0x0f, sp)
      008319 6B 1D            [ 1]  451 	ld	(0x1d, sp), a
      00831B CC 82 83         [ 2]  452 	jp	00108$
      00831E                        453 00106$:
                                    454 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 351: else                     { n_hi++; se_hi += e; sy_hi += (uint32_t)y; }
      00831E 16 27            [ 2]  455 	ldw	y, (0x27, sp)
      008320 90 5C            [ 1]  456 	incw	y
      008322 17 27            [ 2]  457 	ldw	(0x27, sp), y
      008324 16 0D            [ 2]  458 	ldw	y, (0x0d, sp)
      008326 72 F9 1B         [ 2]  459 	addw	y, (0x1b, sp)
      008329 17 1B            [ 2]  460 	ldw	(0x1b, sp), y
      00832B 9F               [ 1]  461 	ld	a, xl
      00832C 19 1A            [ 1]  462 	adc	a, (0x1a, sp)
      00832E 6B 1A            [ 1]  463 	ld	(0x1a, sp), a
      008330 9E               [ 1]  464 	ld	a, xh
      008331 19 19            [ 1]  465 	adc	a, (0x19, sp)
      008333 6B 19            [ 1]  466 	ld	(0x19, sp), a
      008335 1E 23            [ 2]  467 	ldw	x, (0x23, sp)
      008337 72 FB 11         [ 2]  468 	addw	x, (0x11, sp)
      00833A 1F 23            [ 2]  469 	ldw	(0x23, sp), x
      00833C 7B 22            [ 1]  470 	ld	a, (0x22, sp)
      00833E 19 10            [ 1]  471 	adc	a, (0x10, sp)
      008340 6B 22            [ 1]  472 	ld	(0x22, sp), a
      008342 7B 21            [ 1]  473 	ld	a, (0x21, sp)
      008344 19 0F            [ 1]  474 	adc	a, (0x0f, sp)
      008346 6B 21            [ 1]  475 	ld	(0x21, sp), a
      008348 CC 82 83         [ 2]  476 	jp	00108$
      00834B                        477 00110$:
                                    478 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 353: if (n_lo < 2 || n_hi < 2) return;
      00834B 1E 25            [ 2]  479 	ldw	x, (0x25, sp)
      00834D A3 00 02         [ 2]  480 	cpw	x, #0x0002
      008350 24 03            [ 1]  481 	jrnc	00192$
      008352 CC 84 F8         [ 2]  482 	jp	00119$
      008355                        483 00192$:
      008355 1E 27            [ 2]  484 	ldw	x, (0x27, sp)
      008357 A3 00 02         [ 2]  485 	cpw	x, #0x0002
      00835A 24 03            [ 1]  486 	jrnc	00112$
      00835C CC 84 F8         [ 2]  487 	jp	00119$
      00835F                        488 00112$:
                                    489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 354: me_lo = se_lo / (int32_t)n_lo;
      00835F 16 25            [ 2]  490 	ldw	y, (0x25, sp)
      008361 5F               [ 1]  491 	clrw	x
      008362 90 89            [ 2]  492 	pushw	y
      008364 89               [ 2]  493 	pushw	x
      008365 1E 1B            [ 2]  494 	ldw	x, (0x1b, sp)
      008367 89               [ 2]  495 	pushw	x
      008368 1E 1B            [ 2]  496 	ldw	x, (0x1b, sp)
      00836A 89               [ 2]  497 	pushw	x
                                    498 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 355: me_hi = se_hi / (int32_t)n_hi;
      00836B CD 9A A5         [ 4]  499 	call	__divslong
      00836E 5B 08            [ 2]  500 	addw	sp, #8
      008370 1F 07            [ 2]  501 	ldw	(0x07, sp), x
      008372 17 05            [ 2]  502 	ldw	(0x05, sp), y
      008374 16 27            [ 2]  503 	ldw	y, (0x27, sp)
      008376 5F               [ 1]  504 	clrw	x
      008377 90 89            [ 2]  505 	pushw	y
      008379 89               [ 2]  506 	pushw	x
      00837A 1E 1F            [ 2]  507 	ldw	x, (0x1f, sp)
      00837C 89               [ 2]  508 	pushw	x
      00837D 1E 1F            [ 2]  509 	ldw	x, (0x1f, sp)
      00837F 89               [ 2]  510 	pushw	x
                                    511 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 356: my_lo = sy_lo / n_lo;
      008380 CD 9A A5         [ 4]  512 	call	__divslong
      008383 5B 08            [ 2]  513 	addw	sp, #8
      008385 1F 0B            [ 2]  514 	ldw	(0x0b, sp), x
      008387 17 09            [ 2]  515 	ldw	(0x09, sp), y
      008389 16 25            [ 2]  516 	ldw	y, (0x25, sp)
      00838B 5F               [ 1]  517 	clrw	x
      00838C 90 89            [ 2]  518 	pushw	y
      00838E 89               [ 2]  519 	pushw	x
      00838F 1E 23            [ 2]  520 	ldw	x, (0x23, sp)
      008391 89               [ 2]  521 	pushw	x
      008392 1E 23            [ 2]  522 	ldw	x, (0x23, sp)
      008394 89               [ 2]  523 	pushw	x
                                    524 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 357: my_hi = sy_hi / n_hi;
      008395 CD 9A CC         [ 4]  525 	call	__divulong
      008398 5B 08            [ 2]  526 	addw	sp, #8
      00839A 1F 13            [ 2]  527 	ldw	(0x13, sp), x
      00839C 17 11            [ 2]  528 	ldw	(0x11, sp), y
      00839E 16 27            [ 2]  529 	ldw	y, (0x27, sp)
      0083A0 5F               [ 1]  530 	clrw	x
      0083A1 90 89            [ 2]  531 	pushw	y
      0083A3 89               [ 2]  532 	pushw	x
      0083A4 1E 27            [ 2]  533 	ldw	x, (0x27, sp)
      0083A6 89               [ 2]  534 	pushw	x
      0083A7 1E 27            [ 2]  535 	ldw	x, (0x27, sp)
      0083A9 89               [ 2]  536 	pushw	x
                                    537 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 358: de = me_hi - me_lo;
      0083AA CD 9A CC         [ 4]  538 	call	__divulong
      0083AD 5B 08            [ 2]  539 	addw	sp, #8
      0083AF 1F 0F            [ 2]  540 	ldw	(0x0f, sp), x
      0083B1 17 0D            [ 2]  541 	ldw	(0x0d, sp), y
      0083B3 1E 0B            [ 2]  542 	ldw	x, (0x0b, sp)
      0083B5 72 F0 07         [ 2]  543 	subw	x, (0x07, sp)
      0083B8 1F 03            [ 2]  544 	ldw	(0x03, sp), x
      0083BA 7B 0A            [ 1]  545 	ld	a, (0x0a, sp)
      0083BC 12 06            [ 1]  546 	sbc	a, (0x06, sp)
      0083BE 6B 02            [ 1]  547 	ld	(0x02, sp), a
      0083C0 7B 09            [ 1]  548 	ld	a, (0x09, sp)
      0083C2 12 05            [ 1]  549 	sbc	a, (0x05, sp)
      0083C4 6B 01            [ 1]  550 	ld	(0x01, sp), a
                                    551 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 359: dy = (int32_t)my_hi - (int32_t)my_lo;
      0083C6 1E 0F            [ 2]  552 	ldw	x, (0x0f, sp)
      0083C8 72 F0 13         [ 2]  553 	subw	x, (0x13, sp)
      0083CB 1F 07            [ 2]  554 	ldw	(0x07, sp), x
      0083CD 7B 0E            [ 1]  555 	ld	a, (0x0e, sp)
      0083CF 12 12            [ 1]  556 	sbc	a, (0x12, sp)
      0083D1 6B 06            [ 1]  557 	ld	(0x06, sp), a
      0083D3 7B 0D            [ 1]  558 	ld	a, (0x0d, sp)
      0083D5 12 11            [ 1]  559 	sbc	a, (0x11, sp)
      0083D7 6B 05            [ 1]  560 	ld	(0x05, sp), a
                                    561 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 360: if (dy <= 0) return;
      0083D9 5F               [ 1]  562 	clrw	x
      0083DA 13 07            [ 2]  563 	cpw	x, (0x07, sp)
      0083DC 4F               [ 1]  564 	clr	a
      0083DD 12 06            [ 1]  565 	sbc	a, (0x06, sp)
      0083DF 4F               [ 1]  566 	clr	a
      0083E0 12 05            [ 1]  567 	sbc	a, (0x05, sp)
      0083E2 2F 03            [ 1]  568 	jrslt	00115$
      0083E4 CC 84 F8         [ 2]  569 	jp	00119$
      0083E7                        570 00115$:
                                    571 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 361: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
      0083E7 CE 00 15         [ 2]  572 	ldw	x, _g_K+0
      0083EA 1F 0B            [ 2]  573 	ldw	(0x0b, sp), x
      0083EC 0F 0A            [ 1]  574 	clr	(0x0a, sp)
      0083EE 0F 09            [ 1]  575 	clr	(0x09, sp)
      0083F0 1E 03            [ 2]  576 	ldw	x, (0x03, sp)
      0083F2 89               [ 2]  577 	pushw	x
      0083F3 1E 03            [ 2]  578 	ldw	x, (0x03, sp)
      0083F5 89               [ 2]  579 	pushw	x
      0083F6 1E 0F            [ 2]  580 	ldw	x, (0x0f, sp)
      0083F8 89               [ 2]  581 	pushw	x
      0083F9 1E 0F            [ 2]  582 	ldw	x, (0x0f, sp)
      0083FB 89               [ 2]  583 	pushw	x
      0083FC CD 9B 29         [ 4]  584 	call	__mullong
      0083FF 5B 08            [ 2]  585 	addw	sp, #8
      008401 1F 13            [ 2]  586 	ldw	(0x13, sp), x
      008403 1E 07            [ 2]  587 	ldw	x, (0x07, sp)
      008405 89               [ 2]  588 	pushw	x
      008406 1E 07            [ 2]  589 	ldw	x, (0x07, sp)
      008408 89               [ 2]  590 	pushw	x
      008409 1E 17            [ 2]  591 	ldw	x, (0x17, sp)
      00840B 89               [ 2]  592 	pushw	x
      00840C 90 89            [ 2]  593 	pushw	y
                                    594 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 362: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
      00840E CD 9A A5         [ 4]  595 	call	__divslong
      008411 5B 08            [ 2]  596 	addw	sp, #8
      008413 1F 0F            [ 2]  597 	ldw	(0x0f, sp), x
      008415 17 0D            [ 2]  598 	ldw	(0x0d, sp), y
      008417 1E 17            [ 2]  599 	ldw	x, (0x17, sp)
      008419 72 FB 1B         [ 2]  600 	addw	x, (0x1b, sp)
      00841C 1F 13            [ 2]  601 	ldw	(0x13, sp), x
      00841E 7B 16            [ 1]  602 	ld	a, (0x16, sp)
      008420 19 1A            [ 1]  603 	adc	a, (0x1a, sp)
      008422 6B 12            [ 1]  604 	ld	(0x12, sp), a
      008424 7B 15            [ 1]  605 	ld	a, (0x15, sp)
      008426 19 19            [ 1]  606 	adc	a, (0x19, sp)
      008428 6B 11            [ 1]  607 	ld	(0x11, sp), a
      00842A 1E 25            [ 2]  608 	ldw	x, (0x25, sp)
      00842C 72 FB 27         [ 2]  609 	addw	x, (0x27, sp)
      00842F 1F 1B            [ 2]  610 	ldw	(0x1b, sp), x
      008431 90 93            [ 1]  611 	ldw	y, x
      008433 5F               [ 1]  612 	clrw	x
      008434 90 89            [ 2]  613 	pushw	y
      008436 89               [ 2]  614 	pushw	x
      008437 1E 17            [ 2]  615 	ldw	x, (0x17, sp)
      008439 89               [ 2]  616 	pushw	x
      00843A 1E 17            [ 2]  617 	ldw	x, (0x17, sp)
      00843C 89               [ 2]  618 	pushw	x
                                    619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 363: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
      00843D CD 9A A5         [ 4]  620 	call	__divslong
      008440 5B 08            [ 2]  621 	addw	sp, #8
      008442 1F 19            [ 2]  622 	ldw	(0x19, sp), x
      008444 17 17            [ 2]  623 	ldw	(0x17, sp), y
      008446 1E 1F            [ 2]  624 	ldw	x, (0x1f, sp)
      008448 72 FB 23         [ 2]  625 	addw	x, (0x23, sp)
      00844B 1F 27            [ 2]  626 	ldw	(0x27, sp), x
      00844D 7B 1E            [ 1]  627 	ld	a, (0x1e, sp)
      00844F 19 22            [ 1]  628 	adc	a, (0x22, sp)
      008451 6B 26            [ 1]  629 	ld	(0x26, sp), a
      008453 7B 1D            [ 1]  630 	ld	a, (0x1d, sp)
      008455 19 21            [ 1]  631 	adc	a, (0x21, sp)
      008457 6B 25            [ 1]  632 	ld	(0x25, sp), a
      008459 16 1B            [ 2]  633 	ldw	y, (0x1b, sp)
      00845B 5F               [ 1]  634 	clrw	x
      00845C 90 89            [ 2]  635 	pushw	y
      00845E 89               [ 2]  636 	pushw	x
      00845F 1E 2B            [ 2]  637 	ldw	x, (0x2b, sp)
      008461 89               [ 2]  638 	pushw	x
      008462 1E 2B            [ 2]  639 	ldw	x, (0x2b, sp)
      008464 89               [ 2]  640 	pushw	x
                                    641 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 364: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
      008465 CD 9A CC         [ 4]  642 	call	__divulong
      008468 5B 08            [ 2]  643 	addw	sp, #8
      00846A 51               [ 1]  644 	exgw	x, y
      00846B 7B 19            [ 1]  645 	ld	a, (0x19, sp)
      00846D 6B 27            [ 1]  646 	ld	(0x27, sp), a
      00846F 7B 1A            [ 1]  647 	ld	a, (0x1a, sp)
      008471 40               [ 1]  648 	neg	a
      008472 6B 20            [ 1]  649 	ld	(0x20, sp), a
      008474 4F               [ 1]  650 	clr	a
      008475 12 27            [ 1]  651 	sbc	a, (0x27, sp)
      008477 6B 1F            [ 1]  652 	ld	(0x1f, sp), a
      008479 02               [ 1]  653 	rlwa	x
      00847A 6B 21            [ 1]  654 	ld	(0x21, sp), a
      00847C 01               [ 1]  655 	rrwa	x
      00847D 9F               [ 1]  656 	ld	a, xl
      00847E CE 00 17         [ 2]  657 	ldw	x, _g_tau+0
      008481 1F 27            [ 2]  658 	ldw	(0x27, sp), x
      008483 5F               [ 1]  659 	clrw	x
      008484 0D 27            [ 1]  660 	tnz	(0x27, sp)
      008486 2A 01            [ 1]  661 	jrpl	00195$
      008488 5A               [ 2]  662 	decw	x
      008489                        663 00195$:
      008489 72 F2 27         [ 2]  664 	subw	y, (0x27, sp)
      00848C 89               [ 2]  665 	pushw	x
      00848D 12 02            [ 1]  666 	sbc	a, (2, sp)
      00848F 85               [ 2]  667 	popw	x
      008490 97               [ 1]  668 	ld	xl, a
      008491 7B 21            [ 1]  669 	ld	a, (0x21, sp)
      008493 89               [ 2]  670 	pushw	x
      008494 12 01            [ 1]  671 	sbc	a, (1, sp)
      008496 85               [ 2]  672 	popw	x
      008497 95               [ 1]  673 	ld	xh, a
      008498 90 89            [ 2]  674 	pushw	y
      00849A 89               [ 2]  675 	pushw	x
      00849B 1E 07            [ 2]  676 	ldw	x, (0x07, sp)
      00849D 89               [ 2]  677 	pushw	x
      00849E 1E 07            [ 2]  678 	ldw	x, (0x07, sp)
      0084A0 89               [ 2]  679 	pushw	x
      0084A1 CD 9B 29         [ 4]  680 	call	__mullong
      0084A4 5B 08            [ 2]  681 	addw	sp, #8
      0084A6 1F 27            [ 2]  682 	ldw	(0x27, sp), x
      0084A8 1E 07            [ 2]  683 	ldw	x, (0x07, sp)
      0084AA 89               [ 2]  684 	pushw	x
      0084AB 1E 07            [ 2]  685 	ldw	x, (0x07, sp)
      0084AD 89               [ 2]  686 	pushw	x
      0084AE 1E 2B            [ 2]  687 	ldw	x, (0x2b, sp)
      0084B0 89               [ 2]  688 	pushw	x
      0084B1 90 89            [ 2]  689 	pushw	y
      0084B3 CD 9A A5         [ 4]  690 	call	__divslong
      0084B6 5B 08            [ 2]  691 	addw	sp, #8
      0084B8 72 FB 1F         [ 2]  692 	addw	x, (0x1f, sp)
      0084BB 1F 27            [ 2]  693 	ldw	(0x27, sp), x
                                    694 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 365: K2 = (int32_t)g_K - dk;
      0084BD 1E 0B            [ 2]  695 	ldw	x, (0x0b, sp)
      0084BF 72 F0 0F         [ 2]  696 	subw	x, (0x0f, sp)
      0084C2 1F 25            [ 2]  697 	ldw	(0x25, sp), x
      0084C4 4F               [ 1]  698 	clr	a
      0084C5 12 0E            [ 1]  699 	sbc	a, (0x0e, sp)
      0084C7 6B 24            [ 1]  700 	ld	(0x24, sp), a
      0084C9 4F               [ 1]  701 	clr	a
      0084CA 12 0D            [ 1]  702 	sbc	a, (0x0d, sp)
      0084CC 6B 23            [ 1]  703 	ld	(0x23, sp), a
                                    704 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 366: if (K2 < (int32_t)K_MIN || K2 > (int32_t)K_MAX) return;
      0084CE 1E 25            [ 2]  705 	ldw	x, (0x25, sp)
      0084D0 A3 B3 B0         [ 2]  706 	cpw	x, #0xb3b0
      0084D3 7B 24            [ 1]  707 	ld	a, (0x24, sp)
      0084D5 A2 00            [ 1]  708 	sbc	a, #0x00
      0084D7 7B 23            [ 1]  709 	ld	a, (0x23, sp)
      0084D9 A2 00            [ 1]  710 	sbc	a, #0x00
      0084DB 2F 1B            [ 1]  711 	jrslt	00119$
      0084DD AE EA 60         [ 2]  712 	ldw	x, #0xea60
      0084E0 13 25            [ 2]  713 	cpw	x, (0x25, sp)
      0084E2 4F               [ 1]  714 	clr	a
      0084E3 12 24            [ 1]  715 	sbc	a, (0x24, sp)
      0084E5 4F               [ 1]  716 	clr	a
      0084E6 12 23            [ 1]  717 	sbc	a, (0x23, sp)
      0084E8 2F 0E            [ 1]  718 	jrslt	00119$
                                    719 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 367: g_K = (uint16_t)K2;
      0084EA 1E 25            [ 2]  720 	ldw	x, (0x25, sp)
      0084EC CF 00 15         [ 2]  721 	ldw	_g_K+0, x
                                    722 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 368: g_tau = (int16_t)(g_tau + dtau);
      0084EF CE 00 17         [ 2]  723 	ldw	x, _g_tau+0
      0084F2 72 FB 27         [ 2]  724 	addw	x, (0x27, sp)
      0084F5 CF 00 17         [ 2]  725 	ldw	_g_tau+0, x
      0084F8                        726 00119$:
                                    727 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 369: }
      0084F8 5B 28            [ 2]  728 	addw	sp, #40
      0084FA 81               [ 4]  729 	ret
                                    730 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 393: static void ss_init(void)
                                    731 ;	-----------------------------------------
                                    732 ;	 function ss_init
                                    733 ;	-----------------------------------------
      0084FB                        734 _ss_init:
                                    735 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 395: scan_init();
      0084FB CD 96 7D         [ 4]  736 	call	_scan_init
                                    737 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 396: ss.y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
      0084FE AE 01 27         [ 2]  738 	ldw	x, #(_ss+0)
      008501 90 AE 82 A4      [ 2]  739 	ldw	y, #0x82a4
      008505 EF 02            [ 2]  740 	ldw	(0x2, x), y
      008507 90 AE 00 01      [ 2]  741 	ldw	y, #0x0001
      00850B FF               [ 2]  742 	ldw	(x), y
                                    743 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 397: ss.y_prev = 0; ss.have_y = 0; ss.n = 0;
      00850C AE 01 2B         [ 2]  744 	ldw	x, #(_ss+4)
      00850F 90 5F            [ 1]  745 	clrw	y
      008511 EF 02            [ 2]  746 	ldw	(0x2, x), y
      008513 FF               [ 2]  747 	ldw	(x), y
      008514 35 00 01 2F      [ 1]  748 	mov	_ss+8, #0x00
      008518 AE 01 30         [ 2]  749 	ldw	x, #(_ss+9)
      00851B 6F 01            [ 1]  750 	clr	(0x1, x)
      00851D 7F               [ 1]  751 	clr	(x)
                                    752 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 398: ss.pend = 0; ss.src_done = 0;
      00851E 35 00 01 32      [ 1]  753 	mov	_ss+11, #0x00
      008522 35 00 01 3A      [ 1]  754 	mov	_ss+19, #0x00
                                    755 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 399: ss.p_k0 = 0; ss.p_u = 0; ss.p_v = 0; ss.p_fam = 0;
      008526 AE 01 33         [ 2]  756 	ldw	x, #(_ss+12)
      008529 6F 01            [ 1]  757 	clr	(0x1, x)
      00852B 7F               [ 1]  758 	clr	(x)
      00852C AE 01 35         [ 2]  759 	ldw	x, #(_ss+14)
      00852F 6F 01            [ 1]  760 	clr	(0x1, x)
      008531 7F               [ 1]  761 	clr	(x)
      008532 AE 01 37         [ 2]  762 	ldw	x, #(_ss+16)
      008535 6F 01            [ 1]  763 	clr	(0x1, x)
      008537 7F               [ 1]  764 	clr	(x)
      008538 35 00 01 39      [ 1]  765 	mov	_ss+18, #0x00
                                    766 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 400: }
      00853C 81               [ 4]  767 	ret
                                    768 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 402: static uint8_t ss_next(Seg *out)
                                    769 ;	-----------------------------------------
                                    770 ;	 function ss_next
                                    771 ;	-----------------------------------------
      00853D                        772 _ss_next:
      00853D 52 1F            [ 2]  773 	sub	sp, #31
      00853F 1F 1E            [ 2]  774 	ldw	(0x1e, sp), x
                                    775 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      008541                        776 00121$:
      008541 C6 01 3A         [ 1]  777 	ld	a, _ss+19
                                    778 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
                                    779 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
                                    780 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
                                    781 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
                                    782 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      008544 16 1E            [ 2]  783 	ldw	y, (0x1e, sp)
      008546 17 0D            [ 2]  784 	ldw	(0x0d, sp), y
                                    785 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      008548 1E 1E            [ 2]  786 	ldw	x, (0x1e, sp)
      00854A 5C               [ 1]  787 	incw	x
      00854B 5C               [ 1]  788 	incw	x
      00854C 1F 0F            [ 2]  789 	ldw	(0x0f, sp), x
                                    790 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      00854E 1E 1E            [ 2]  791 	ldw	x, (0x1e, sp)
      008550 1C 00 04         [ 2]  792 	addw	x, #0x0004
      008553 1F 11            [ 2]  793 	ldw	(0x11, sp), x
      008555 1E 1E            [ 2]  794 	ldw	x, (0x1e, sp)
      008557 1C 00 06         [ 2]  795 	addw	x, #0x0006
      00855A 1F 13            [ 2]  796 	ldw	(0x13, sp), x
      00855C 1E 1E            [ 2]  797 	ldw	x, (0x1e, sp)
      00855E 1C 00 08         [ 2]  798 	addw	x, #0x0008
      008561 1F 15            [ 2]  799 	ldw	(0x15, sp), x
                                    800 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
      008563 4D               [ 1]  801 	tnz	a
      008564 27 03            [ 1]  802 	jreq	00242$
      008566 CC 87 45         [ 2]  803 	jp	00123$
      008569                        804 00242$:
                                    805 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 409: if (!scan_next()) { ss.src_done = 1; break; }
      008569 CD 96 A6         [ 4]  806 	call	_scan_next
      00856C 4D               [ 1]  807 	tnz	a
      00856D 26 07            [ 1]  808 	jrne	00102$
      00856F 35 01 01 3A      [ 1]  809 	mov	_ss+19, #0x01
      008573 CC 87 45         [ 2]  810 	jp	00123$
      008576                        811 00102$:
                                    812 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 410: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
      008576 CE 01 50         [ 2]  813 	ldw	x, _scan_ra+0
      008579 72 BB 01 52      [ 2]  814 	addw	x, _scan_rb+0
      00857D 54               [ 2]  815 	srlw	x
      00857E CD 81 8D         [ 4]  816 	call	_map_raw
      008581 1F 03            [ 2]  817 	ldw	(0x03, sp), x
      008583 17 01            [ 2]  818 	ldw	(0x01, sp), y
                                    819 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 411: if (y < 0) y = 0;
      008585 0D 01            [ 1]  820 	tnz	(0x01, sp)
      008587 2A 05            [ 1]  821 	jrpl	00104$
      008589 5F               [ 1]  822 	clrw	x
      00858A 1F 03            [ 2]  823 	ldw	(0x03, sp), x
      00858C 1F 01            [ 2]  824 	ldw	(0x01, sp), x
      00858E                        825 00104$:
                                    826 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 412: if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
      00858E 16 03            [ 2]  827 	ldw	y, (0x03, sp)
      008590 17 07            [ 2]  828 	ldw	(0x07, sp), y
      008592 16 01            [ 2]  829 	ldw	y, (0x01, sp)
      008594 17 05            [ 2]  830 	ldw	(0x05, sp), y
      008596 AE 01 27         [ 2]  831 	ldw	x, #(_ss+0)
      008599 90 93            [ 1]  832 	ldw	y, x
      00859B 90 EE 02         [ 2]  833 	ldw	y, (0x2, y)
      00859E FE               [ 2]  834 	ldw	x, (x)
      00859F 90 9F            [ 1]  835 	ld	a, yl
      0085A1 11 08            [ 1]  836 	cp	a, (0x08, sp)
      0085A3 90 9E            [ 1]  837 	ld	a, yh
      0085A5 12 07            [ 1]  838 	sbc	a, (0x07, sp)
      0085A7 9F               [ 1]  839 	ld	a, xl
      0085A8 12 06            [ 1]  840 	sbc	a, (0x06, sp)
      0085AA 9E               [ 1]  841 	ld	a, xh
      0085AB 12 05            [ 1]  842 	sbc	a, (0x05, sp)
      0085AD 24 07            [ 1]  843 	jrnc	00106$
      0085AF 35 01 01 3A      [ 1]  844 	mov	_ss+19, #0x01
      0085B3 CC 87 45         [ 2]  845 	jp	00123$
      0085B6                        846 00106$:
                                    847 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
                                    848 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
                                    849 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
      0085B6 C6 01 2F         [ 1]  850 	ld	a, _ss+8
      0085B9 26 0C            [ 1]  851 	jrne	00110$
      0085BB AE 01 30         [ 2]  852 	ldw	x, #(_ss+9)
      0085BE 6F 01            [ 1]  853 	clr	(0x1, x)
      0085C0 7F               [ 1]  854 	clr	(x)
      0085C1 35 01 01 2F      [ 1]  855 	mov	_ss+8, #0x01
      0085C5 20 43            [ 2]  856 	jra	00111$
      0085C7                        857 00110$:
                                    858 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
      0085C7 AE 01 2B         [ 2]  859 	ldw	x, #(_ss+4)
      0085CA 90 93            [ 1]  860 	ldw	y, x
      0085CC 90 EE 02         [ 2]  861 	ldw	y, (0x2, y)
      0085CF FE               [ 2]  862 	ldw	x, (x)
      0085D0 17 0B            [ 2]  863 	ldw	(0x0b, sp), y
      0085D2 1F 09            [ 2]  864 	ldw	(0x09, sp), x
      0085D4 16 03            [ 2]  865 	ldw	y, (0x03, sp)
      0085D6 72 F2 0B         [ 2]  866 	subw	y, (0x0b, sp)
      0085D9 7B 02            [ 1]  867 	ld	a, (0x02, sp)
      0085DB 12 0A            [ 1]  868 	sbc	a, (0x0a, sp)
      0085DD 6B 1B            [ 1]  869 	ld	(0x1b, sp), a
      0085DF 7B 01            [ 1]  870 	ld	a, (0x01, sp)
      0085E1 12 09            [ 1]  871 	sbc	a, (0x09, sp)
      0085E3 6B 1A            [ 1]  872 	ld	(0x1a, sp), a
                                    873 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 416: dn = (int16_t)((d + BIT_H) >> BIT_SH);
      0085E5 72 A9 01 00      [ 2]  874 	addw	y, #0x0100
      0085E9 1E 1A            [ 2]  875 	ldw	x, (0x1a, sp)
      0085EB 24 01            [ 1]  876 	jrnc	00247$
      0085ED 5C               [ 1]  877 	incw	x
      0085EE                        878 00247$:
      0085EE 4F               [ 1]  879 	clr	a
      0085EF 5D               [ 2]  880 	tnzw	x
      0085F0 2A 01            [ 1]  881 	jrpl	00248$
      0085F2 4A               [ 1]  882 	dec	a
      0085F3                        883 00248$:
      0085F3 01               [ 1]  884 	rrwa	x
      0085F4 90 01            [ 1]  885 	rrwa	y
      0085F6 57               [ 2]  886 	sraw	x
      0085F7 90 56            [ 2]  887 	rrcw	y
                                    888 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 417: if (dn > 0) ss.n = (uint16_t)(ss.n + dn);
      0085F9 93               [ 1]  889 	ldw	x, y
      0085FA A3 00 00         [ 2]  890 	cpw	x, #0x0000
      0085FD 2D 0B            [ 1]  891 	jrsle	00111$
      0085FF CE 01 30         [ 2]  892 	ldw	x, _ss+9
      008602 17 1C            [ 2]  893 	ldw	(0x1c, sp), y
      008604 72 FB 1C         [ 2]  894 	addw	x, (0x1c, sp)
      008607 CF 01 30         [ 2]  895 	ldw	_ss+9, x
      00860A                        896 00111$:
                                    897 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 419: ss.y_prev = (uint32_t)y;
      00860A AE 01 2B         [ 2]  898 	ldw	x, #(_ss+4)
      00860D 16 07            [ 2]  899 	ldw	y, (0x07, sp)
      00860F EF 02            [ 2]  900 	ldw	(0x2, x), y
      008611 16 05            [ 2]  901 	ldw	y, (0x05, sp)
      008613 FF               [ 2]  902 	ldw	(x), y
                                    903 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 420: yfa = map_raw(scan_fa);
      008614 CE 01 54         [ 2]  904 	ldw	x, _scan_fa+0
      008617 CD 81 8D         [ 4]  905 	call	_map_raw
      00861A 1F 1C            [ 2]  906 	ldw	(0x1c, sp), x
      00861C 17 1A            [ 2]  907 	ldw	(0x1a, sp), y
                                    908 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 421: yfb = map_raw(scan_fb);
      00861E CE 01 56         [ 2]  909 	ldw	x, _scan_fb+0
      008621 CD 81 8D         [ 4]  910 	call	_map_raw
      008624 17 09            [ 2]  911 	ldw	(0x09, sp), y
                                    912 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      008626 C6 01 32         [ 1]  913 	ld	a, _ss+11
      008629 6B 17            [ 1]  914 	ld	(0x17, sp), a
                                    915 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      00862B 16 1C            [ 2]  916 	ldw	y, (0x1c, sp)
      00862D 17 18            [ 2]  917 	ldw	(0x18, sp), y
                                    918 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      00862F 1F 1A            [ 2]  919 	ldw	(0x1a, sp), x
                                    920 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
      008631 0D 17            [ 1]  921 	tnz	(0x17, sp)
      008633 27 3E            [ 1]  922 	jreq	00113$
      008635 90 CE 01 30      [ 2]  923 	ldw	y, _ss+9
      008639 CE 01 33         [ 2]  924 	ldw	x, _ss+12
      00863C 1F 1C            [ 2]  925 	ldw	(0x1c, sp), x
      00863E 93               [ 1]  926 	ldw	x, y
      00863F 13 1C            [ 2]  927 	cpw	x, (0x1c, sp)
      008641 26 30            [ 1]  928 	jrne	00113$
                                    929 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 423: base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
      008643 1E 1C            [ 2]  930 	ldw	x, (0x1c, sp)
      008645 5E               [ 1]  931 	swapw	x
      008646 4F               [ 1]  932 	clr	a
      008647 0F 14            [ 1]  933 	clr	(0x14, sp)
      008649 41               [ 1]  934 	exg	a, xl
      00864A 6B 11            [ 1]  935 	ld	(0x11, sp), a
      00864C 41               [ 1]  936 	exg	a, xl
      00864D 6B 10            [ 1]  937 	ld	(0x10, sp), a
      00864F 4F               [ 1]  938 	clr	a
      008650 97               [ 1]  939 	ld	xl, a
      008651 58               [ 2]  940 	sllw	x
      008652 09 11            [ 1]  941 	rlc	(0x11, sp)
      008654 09 10            [ 1]  942 	rlc	(0x10, sp)
      008656 1C 02 00         [ 2]  943 	addw	x, #0x0200
                                    944 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
      008659 1F 1C            [ 2]  945 	ldw	(0x1c, sp), x
      00865B 1E 18            [ 2]  946 	ldw	x, (0x18, sp)
      00865D 72 F0 1C         [ 2]  947 	subw	x, (0x1c, sp)
      008660 CF 01 35         [ 2]  948 	ldw	_ss+14, x
                                    949 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008663 1E 1A            [ 2]  950 	ldw	x, (0x1a, sp)
      008665 72 F0 1C         [ 2]  951 	subw	x, (0x1c, sp)
      008668 CF 01 37         [ 2]  952 	ldw	_ss+16, x
                                    953 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
      00866B 55 01 58 01 39   [ 1]  954 	mov	_ss+18, _scan_sfa+0
                                    955 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 427: continue;
      008670 CC 85 41         [ 2]  956 	jp	00121$
      008673                        957 00113$:
                                    958 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 429: if (ss.pend) {
      008673 0D 17            [ 1]  959 	tnz	(0x17, sp)
      008675 26 03            [ 1]  960 	jrne	00255$
      008677 CC 86 F9         [ 2]  961 	jp	00118$
      00867A                        962 00255$:
                                    963 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
      00867A CE 01 33         [ 2]  964 	ldw	x, _ss+12
      00867D 16 0D            [ 2]  965 	ldw	y, (0x0d, sp)
      00867F 90 FF            [ 2]  966 	ldw	(y), x
                                    967 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
      008681 CE 01 30         [ 2]  968 	ldw	x, _ss+9
      008684 A3 00 C0         [ 2]  969 	cpw	x, #0x00c0
      008687 24 04            [ 1]  970 	jrnc	00128$
      008689 1F 1C            [ 2]  971 	ldw	(0x1c, sp), x
      00868B 20 05            [ 2]  972 	jra	00129$
      00868D                        973 00128$:
      00868D AE 00 C0         [ 2]  974 	ldw	x, #0x00c0
      008690 1F 1C            [ 2]  975 	ldw	(0x1c, sp), x
      008692                        976 00129$:
      008692 1E 0F            [ 2]  977 	ldw	x, (0x0f, sp)
      008694 16 1C            [ 2]  978 	ldw	y, (0x1c, sp)
      008696 FF               [ 2]  979 	ldw	(x), y
                                    980 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      008697 CE 01 35         [ 2]  981 	ldw	x, _ss+14
      00869A 16 11            [ 2]  982 	ldw	y, (0x11, sp)
      00869C 90 FF            [ 2]  983 	ldw	(y), x
      00869E CE 01 37         [ 2]  984 	ldw	x, _ss+16
      0086A1 16 13            [ 2]  985 	ldw	y, (0x13, sp)
      0086A3 90 FF            [ 2]  986 	ldw	(y), x
      0086A5 C6 01 39         [ 1]  987 	ld	a, _ss+18
      0086A8 1E 15            [ 2]  988 	ldw	x, (0x15, sp)
      0086AA F7               [ 1]  989 	ld	(x), a
                                    990 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 433: if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
      0086AB CE 01 30         [ 2]  991 	ldw	x, _ss+9
      0086AE 1F 1C            [ 2]  992 	ldw	(0x1c, sp), x
      0086B0 A3 00 C0         [ 2]  993 	cpw	x, #0x00c0
      0086B3 25 0D            [ 1]  994 	jrc	00116$
      0086B5 35 00 01 32      [ 1]  995 	mov	_ss+11, #0x00
      0086B9 35 01 01 3A      [ 1]  996 	mov	_ss+19, #0x01
      0086BD A6 01            [ 1]  997 	ld	a, #0x01
      0086BF CC 87 74         [ 2]  998 	jp	00126$
      0086C2                        999 00116$:
                                   1000 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 434: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      0086C2 1E 1C            [ 2] 1001 	ldw	x, (0x1c, sp)
      0086C4 90 5F            [ 1] 1002 	clrw	y
      0086C6 4F               [ 1] 1003 	clr	a
      0086C7 48               [ 1] 1004 	sll	a
      0086C8 59               [ 2] 1005 	rlcw	x
      0086C9 61               [ 1] 1006 	exg	a, yl
      0086CA 49               [ 1] 1007 	rlc	a
      0086CB 61               [ 1] 1008 	exg	a, yl
      0086CC 6B 17            [ 1] 1009 	ld	(0x17, sp), a
      0086CE 1C 00 02         [ 2] 1010 	addw	x, #0x0002
      0086D1 1F 15            [ 2] 1011 	ldw	(0x15, sp), x
      0086D3 4F               [ 1] 1012 	clr	a
      0086D4 A9 00            [ 1] 1013 	adc	a, #0x00
                                   1014 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 435: ss.p_k0 = ss.n;
      0086D6 AE 01 33         [ 2] 1015 	ldw	x, #(_ss+12)
      0086D9 16 1C            [ 2] 1016 	ldw	y, (0x1c, sp)
      0086DB FF               [ 2] 1017 	ldw	(x), y
                                   1018 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 436: ss.p_u = (int16_t)(yfa - (int32_t)base);
      0086DC 16 16            [ 2] 1019 	ldw	y, (0x16, sp)
      0086DE 17 1C            [ 2] 1020 	ldw	(0x1c, sp), y
      0086E0 1E 18            [ 2] 1021 	ldw	x, (0x18, sp)
      0086E2 72 F0 1C         [ 2] 1022 	subw	x, (0x1c, sp)
      0086E5 CF 01 35         [ 2] 1023 	ldw	_ss+14, x
                                   1024 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 437: ss.p_v = (int16_t)(yfb - (int32_t)base);
      0086E8 1E 1A            [ 2] 1025 	ldw	x, (0x1a, sp)
      0086EA 72 F0 1C         [ 2] 1026 	subw	x, (0x1c, sp)
      0086ED CF 01 37         [ 2] 1027 	ldw	_ss+16, x
                                   1028 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 438: ss.p_fam = scan_sfa;
      0086F0 55 01 58 01 39   [ 1] 1029 	mov	_ss+18, _scan_sfa+0
                                   1030 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 439: return 1;
      0086F5 A6 01            [ 1] 1031 	ld	a, #0x01
      0086F7 20 7B            [ 2] 1032 	jra	00126$
      0086F9                       1033 00118$:
                                   1034 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 441: if (ss.n >= NB) { ss.src_done = 1; break; }
      0086F9 CE 01 30         [ 2] 1035 	ldw	x, _ss+9
      0086FC 1F 1C            [ 2] 1036 	ldw	(0x1c, sp), x
      0086FE A3 00 C0         [ 2] 1037 	cpw	x, #0x00c0
      008701 25 06            [ 1] 1038 	jrc	00120$
      008703 35 01 01 3A      [ 1] 1039 	mov	_ss+19, #0x01
      008707 20 3C            [ 2] 1040 	jra	00123$
      008709                       1041 00120$:
                                   1042 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 442: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
      008709 7B 1D            [ 1] 1043 	ld	a, (0x1d, sp)
      00870B 90 95            [ 1] 1044 	ld	yh, a
      00870D 4F               [ 1] 1045 	clr	a
      00870E 5F               [ 1] 1046 	clrw	x
      00870F 61               [ 1] 1047 	exg	a, yl
      008710 4F               [ 1] 1048 	clr	a
      008711 61               [ 1] 1049 	exg	a, yl
      008712 90 58            [ 2] 1050 	sllw	y
      008714 49               [ 1] 1051 	rlc	a
      008715 59               [ 2] 1052 	rlcw	x
      008716 72 A9 02 00      [ 2] 1053 	addw	y, #0x0200
      00871A A9 00            [ 1] 1054 	adc	a, #0x00
      00871C 6B 15            [ 1] 1055 	ld	(0x15, sp), a
      00871E 4F               [ 1] 1056 	clr	a
      00871F A9 00            [ 1] 1057 	adc	a, #0x00
                                   1058 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 443: ss.pend = 1;
      008721 35 01 01 32      [ 1] 1059 	mov	_ss+11, #0x01
                                   1060 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 444: ss.p_k0 = ss.n;
      008725 CE 01 30         [ 2] 1061 	ldw	x, _ss+9
      008728 CF 01 33         [ 2] 1062 	ldw	_ss+12, x
                                   1063 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 445: ss.p_u = (int16_t)(yfa - (int32_t)base);
      00872B 17 1C            [ 2] 1064 	ldw	(0x1c, sp), y
      00872D 1E 18            [ 2] 1065 	ldw	x, (0x18, sp)
      00872F 72 F0 1C         [ 2] 1066 	subw	x, (0x1c, sp)
      008732 CF 01 35         [ 2] 1067 	ldw	_ss+14, x
                                   1068 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 446: ss.p_v = (int16_t)(yfb - (int32_t)base);
      008735 1E 1A            [ 2] 1069 	ldw	x, (0x1a, sp)
      008737 72 F0 1C         [ 2] 1070 	subw	x, (0x1c, sp)
      00873A CF 01 37         [ 2] 1071 	ldw	_ss+16, x
                                   1072 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 447: ss.p_fam = scan_sfa;
      00873D 55 01 58 01 39   [ 1] 1073 	mov	_ss+18, _scan_sfa+0
      008742 CC 85 41         [ 2] 1074 	jp	00121$
      008745                       1075 00123$:
                                   1076 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 449: if (ss.pend) {
      008745 C6 01 32         [ 1] 1077 	ld	a, _ss+11
      008748 27 29            [ 1] 1078 	jreq	00125$
                                   1079 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 450: ss.pend = 0;
      00874A 35 00 01 32      [ 1] 1080 	mov	_ss+11, #0x00
                                   1081 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 451: out->k0 = ss.p_k0; out->k1 = NB;
      00874E CE 01 33         [ 2] 1082 	ldw	x, _ss+12
      008751 16 0D            [ 2] 1083 	ldw	y, (0x0d, sp)
      008753 90 FF            [ 2] 1084 	ldw	(y), x
      008755 1E 0F            [ 2] 1085 	ldw	x, (0x0f, sp)
      008757 90 AE 00 C0      [ 2] 1086 	ldw	y, #0x00c0
      00875B FF               [ 2] 1087 	ldw	(x), y
                                   1088 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 452: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
      00875C CE 01 35         [ 2] 1089 	ldw	x, _ss+14
      00875F 16 11            [ 2] 1090 	ldw	y, (0x11, sp)
      008761 90 FF            [ 2] 1091 	ldw	(y), x
      008763 CE 01 37         [ 2] 1092 	ldw	x, _ss+16
      008766 16 13            [ 2] 1093 	ldw	y, (0x13, sp)
      008768 90 FF            [ 2] 1094 	ldw	(y), x
      00876A C6 01 39         [ 1] 1095 	ld	a, _ss+18
      00876D 1E 15            [ 2] 1096 	ldw	x, (0x15, sp)
      00876F F7               [ 1] 1097 	ld	(x), a
                                   1098 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 453: return 1;
      008770 A6 01            [ 1] 1099 	ld	a, #0x01
                                   1100 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 455: return 0;
      008772 21                    1101 	.byte 0x21
      008773                       1102 00125$:
      008773 4F               [ 1] 1103 	clr	a
      008774                       1104 00126$:
                                   1105 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 456: }
      008774 5B 1F            [ 2] 1106 	addw	sp, #31
      008776 81               [ 4] 1107 	ret
                                   1108 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 460: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
                                   1109 ;	-----------------------------------------
                                   1110 ;	 function a_bounds
                                   1111 ;	-----------------------------------------
      008777                       1112 _a_bounds:
      008777 52 0C            [ 2] 1113 	sub	sp, #12
      008779 1F 09            [ 2] 1114 	ldw	(0x09, sp), x
                                   1115 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 462: uint16_t t, e = (k1 < NB) ? k1 : NB;
      00877B 1E 0F            [ 2] 1116 	ldw	x, (0x0f, sp)
      00877D A3 00 C0         [ 2] 1117 	cpw	x, #0x00c0
      008780 25 03            [ 1] 1118 	jrc	00117$
      008782 AE 00 C0         [ 2] 1119 	ldw	x, #0x00c0
      008785                       1120 00117$:
      008785 1F 01            [ 2] 1121 	ldw	(0x01, sp), x
                                   1122 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 463: *amin = 0;
      008787 16 11            [ 2] 1123 	ldw	y, (0x11, sp)
      008789 17 03            [ 2] 1124 	ldw	(0x03, sp), y
      00878B 93               [ 1] 1125 	ldw	x, y
      00878C 6F 01            [ 1] 1126 	clr	(0x1, x)
      00878E 7F               [ 1] 1127 	clr	(x)
                                   1128 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 464: *amax = (int16_t)(k1 - k0);
      00878F 16 13            [ 2] 1129 	ldw	y, (0x13, sp)
      008791 17 05            [ 2] 1130 	ldw	(0x05, sp), y
      008793 16 0F            [ 2] 1131 	ldw	y, (0x0f, sp)
      008795 72 F2 09         [ 2] 1132 	subw	y, (0x09, sp)
      008798 1E 05            [ 2] 1133 	ldw	x, (0x05, sp)
      00879A FF               [ 2] 1134 	ldw	(x), y
                                   1135 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      00879B 16 09            [ 2] 1136 	ldw	y, (0x09, sp)
      00879D 17 0B            [ 2] 1137 	ldw	(0x0b, sp), y
      00879F                       1138 00112$:
                                   1139 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 466: int8_t kb = known_bit(t);
      00879F 1E 0B            [ 2] 1140 	ldw	x, (0x0b, sp)
      0087A1 13 01            [ 2] 1141 	cpw	x, (0x01, sp)
      0087A3 24 38            [ 1] 1142 	jrnc	00114$
      0087A5 CD 81 37         [ 4] 1143 	call	_known_bit
                                   1144 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      0087A8 16 0B            [ 2] 1145 	ldw	y, (0x0b, sp)
      0087AA 72 F2 09         [ 2] 1146 	subw	y, (0x09, sp)
                                   1147 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 467: if (kb == 1) {
      0087AD A1 01            [ 1] 1148 	cp	a, #0x01
      0087AF 26 14            [ 1] 1149 	jrne	00108$
                                   1150 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
      0087B1 17 07            [ 2] 1151 	ldw	(0x07, sp), y
      0087B3 93               [ 1] 1152 	ldw	x, y
      0087B4 5C               [ 1] 1153 	incw	x
                                   1154 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 469: if (m > *amin) *amin = m;
      0087B5 16 03            [ 2] 1155 	ldw	y, (0x03, sp)
      0087B7 90 FE            [ 2] 1156 	ldw	y, (y)
      0087B9 17 07            [ 2] 1157 	ldw	(0x07, sp), y
      0087BB 13 07            [ 2] 1158 	cpw	x, (0x07, sp)
      0087BD 2D 17            [ 1] 1159 	jrsle	00113$
      0087BF 16 03            [ 2] 1160 	ldw	y, (0x03, sp)
      0087C1 90 FF            [ 2] 1161 	ldw	(y), x
      0087C3 20 11            [ 2] 1162 	jra	00113$
      0087C5                       1163 00108$:
                                   1164 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 470: } else if (kb == 0) {
      0087C5 4D               [ 1] 1165 	tnz	a
      0087C6 26 0E            [ 1] 1166 	jrne	00113$
                                   1167 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 471: int16_t m = (int16_t)(t - k0);
                                   1168 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 472: if (m < *amax) *amax = m;
      0087C8 1E 05            [ 2] 1169 	ldw	x, (0x05, sp)
      0087CA FE               [ 2] 1170 	ldw	x, (x)
      0087CB 1F 07            [ 2] 1171 	ldw	(0x07, sp), x
      0087CD 51               [ 1] 1172 	exgw	x, y
      0087CE 13 07            [ 2] 1173 	cpw	x, (0x07, sp)
      0087D0 51               [ 1] 1174 	exgw	x, y
      0087D1 2E 03            [ 1] 1175 	jrsge	00113$
      0087D3 1E 05            [ 2] 1176 	ldw	x, (0x05, sp)
      0087D5 FF               [ 2] 1177 	ldw	(x), y
      0087D6                       1178 00113$:
                                   1179 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
      0087D6 1E 0B            [ 2] 1180 	ldw	x, (0x0b, sp)
      0087D8 5C               [ 1] 1181 	incw	x
      0087D9 1F 0B            [ 2] 1182 	ldw	(0x0b, sp), x
      0087DB 20 C2            [ 2] 1183 	jra	00112$
      0087DD                       1184 00114$:
                                   1185 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 475: }
      0087DD 1E 0D            [ 2] 1186 	ldw	x, (13, sp)
      0087DF 5B 14            [ 2] 1187 	addw	sp, #20
      0087E1 FC               [ 2] 1188 	jp	(x)
                                   1189 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 479: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1190 ;	-----------------------------------------
                                   1191 ;	 function label_interval
                                   1192 ;	-----------------------------------------
      0087E2                       1193 _label_interval:
      0087E2 52 0A            [ 2] 1194 	sub	sp, #10
                                   1195 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 482: int16_t L = (int16_t)(k1 - k0);
      0087E4 50               [ 2] 1196 	negw	x
      0087E5 72 FB 0D         [ 2] 1197 	addw	x, (0x0d, sp)
      0087E8 1F 09            [ 2] 1198 	ldw	(0x09, sp), x
                                   1199 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 484: if (a == 0) { *lo = u; *hi = v; return 0; }
      0087EA 16 17            [ 2] 1200 	ldw	y, (0x17, sp)
      0087EC 17 01            [ 2] 1201 	ldw	(0x01, sp), y
      0087EE 1E 13            [ 2] 1202 	ldw	x, (0x13, sp)
      0087F0 26 0E            [ 1] 1203 	jrne	00102$
      0087F2 1E 15            [ 2] 1204 	ldw	x, (0x15, sp)
      0087F4 16 0F            [ 2] 1205 	ldw	y, (0x0f, sp)
      0087F6 FF               [ 2] 1206 	ldw	(x), y
      0087F7 1E 01            [ 2] 1207 	ldw	x, (0x01, sp)
      0087F9 16 11            [ 2] 1208 	ldw	y, (0x11, sp)
      0087FB FF               [ 2] 1209 	ldw	(x), y
      0087FC 4F               [ 1] 1210 	clr	a
      0087FD CC 88 B8         [ 2] 1211 	jp	00113$
      008800                       1212 00102$:
                                   1213 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 485: if (a == L) {
      008800 1E 13            [ 2] 1214 	ldw	x, (0x13, sp)
      008802 13 09            [ 2] 1215 	cpw	x, (0x09, sp)
      008804 26 1D            [ 1] 1216 	jrne	00104$
                                   1217 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 486: off = (int16_t)((L - 1) * BIT_U);
      008806 1E 09            [ 2] 1218 	ldw	x, (0x09, sp)
      008808 5A               [ 2] 1219 	decw	x
      008809 4F               [ 1] 1220 	clr	a
      00880A 02               [ 1] 1221 	rlwa	x
      00880B 58               [ 2] 1222 	sllw	x
      00880C 1F 09            [ 2] 1223 	ldw	(0x09, sp), x
                                   1224 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 487: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      00880E 16 0F            [ 2] 1225 	ldw	y, (0x0f, sp)
      008810 72 F2 09         [ 2] 1226 	subw	y, (0x09, sp)
      008813 1E 15            [ 2] 1227 	ldw	x, (0x15, sp)
      008815 FF               [ 2] 1228 	ldw	(x), y
      008816 16 11            [ 2] 1229 	ldw	y, (0x11, sp)
      008818 72 F2 09         [ 2] 1230 	subw	y, (0x09, sp)
      00881B 1E 01            [ 2] 1231 	ldw	x, (0x01, sp)
      00881D FF               [ 2] 1232 	ldw	(x), y
                                   1233 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 488: return 1;
      00881E A6 01            [ 1] 1234 	ld	a, #0x01
      008820 CC 88 B8         [ 2] 1235 	jp	00113$
      008823                       1236 00104$:
                                   1237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 490: mid = (int16_t)((u + v) >> 1);
      008823 16 0F            [ 2] 1238 	ldw	y, (0x0f, sp)
      008825 72 F9 11         [ 2] 1239 	addw	y, (0x11, sp)
      008828 90 57            [ 2] 1240 	sraw	y
                                   1241 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 491: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
      00882A 1E 13            [ 2] 1242 	ldw	x, (0x13, sp)
      00882C 1F 09            [ 2] 1243 	ldw	(0x09, sp), x
      00882E 5A               [ 2] 1244 	decw	x
      00882F 41               [ 1] 1245 	exg	a, xl
      008830 6B 03            [ 1] 1246 	ld	(0x03, sp), a
      008832 41               [ 1] 1247 	exg	a, xl
      008833 0F 04            [ 1] 1248 	clr	(0x04, sp)
      008835 08 04            [ 1] 1249 	sll	(0x04, sp)
      008837 09 03            [ 1] 1250 	rlc	(0x03, sp)
      008839 1E 03            [ 2] 1251 	ldw	x, (0x03, sp)
      00883B 1C 01 34         [ 2] 1252 	addw	x, #0x0134
      00883E 1F 07            [ 2] 1253 	ldw	(0x07, sp), x
      008840 93               [ 1] 1254 	ldw	x, y
      008841 72 F0 07         [ 2] 1255 	subw	x, (0x07, sp)
                                   1256 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 492: if (d1 < 0) d1 = (int16_t)-d1;
      008844 1F 07            [ 2] 1257 	ldw	(0x07, sp), x
      008846 5D               [ 2] 1258 	tnzw	x
      008847 2A 07            [ 1] 1259 	jrpl	00106$
      008849 00 08            [ 1] 1260 	neg	(0x08, sp)
      00884B 4F               [ 1] 1261 	clr	a
      00884C 12 07            [ 1] 1262 	sbc	a, (0x07, sp)
      00884E 6B 07            [ 1] 1263 	ld	(0x07, sp), a
      008850                       1264 00106$:
                                   1265 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 493: d0 = (int16_t)(mid - (a * BIT_U + H0P));
      008850 7B 0A            [ 1] 1266 	ld	a, (0x0a, sp)
      008852 6B 05            [ 1] 1267 	ld	(0x05, sp), a
      008854 0F 06            [ 1] 1268 	clr	(0x06, sp)
      008856 08 06            [ 1] 1269 	sll	(0x06, sp)
      008858 09 05            [ 1] 1270 	rlc	(0x05, sp)
      00885A 1E 05            [ 2] 1271 	ldw	x, (0x05, sp)
      00885C 1C 00 9A         [ 2] 1272 	addw	x, #0x009a
      00885F 1F 09            [ 2] 1273 	ldw	(0x09, sp), x
      008861 72 F2 09         [ 2] 1274 	subw	y, (0x09, sp)
                                   1275 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 494: if (d0 < 0) d0 = (int16_t)-d0;
      008864 17 09            [ 2] 1276 	ldw	(0x09, sp), y
      008866 93               [ 1] 1277 	ldw	x, y
      008867 5D               [ 2] 1278 	tnzw	x
      008868 2A 07            [ 1] 1279 	jrpl	00108$
      00886A 00 0A            [ 1] 1280 	neg	(0x0a, sp)
      00886C 4F               [ 1] 1281 	clr	a
      00886D 12 09            [ 1] 1282 	sbc	a, (0x09, sp)
      00886F 6B 09            [ 1] 1283 	ld	(0x09, sp), a
      008871                       1284 00108$:
                                   1285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 495: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
      008871 1E 09            [ 2] 1286 	ldw	x, (0x09, sp)
      008873 13 07            [ 2] 1287 	cpw	x, (0x07, sp)
      008875 2E 03            [ 1] 1288 	jrsge	00115$
      008877 1E 09            [ 2] 1289 	ldw	x, (0x09, sp)
      008879 C5                    1290 	.byte 0xc5
      00887A                       1291 00115$:
      00887A 1E 07            [ 2] 1292 	ldw	x, (0x07, sp)
      00887C                       1293 00116$:
      00887C A3 00 F6         [ 2] 1294 	cpw	x, #0x00f6
      00887F 2D 04            [ 1] 1295 	jrsle	00110$
      008881 A6 FF            [ 1] 1296 	ld	a, #0xff
      008883 20 33            [ 2] 1297 	jra	00113$
      008885                       1298 00110$:
                                   1299 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 496: if (d1 <= d0) {
      008885 1E 07            [ 2] 1300 	ldw	x, (0x07, sp)
      008887 13 09            [ 2] 1301 	cpw	x, (0x09, sp)
      008889 2C 18            [ 1] 1302 	jrsgt	00112$
                                   1303 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 497: off = (int16_t)((a - 1) * BIT_U);
      00888B 16 03            [ 2] 1304 	ldw	y, (0x03, sp)
      00888D 17 09            [ 2] 1305 	ldw	(0x09, sp), y
                                   1306 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 498: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      00888F 16 0F            [ 2] 1307 	ldw	y, (0x0f, sp)
      008891 72 F2 09         [ 2] 1308 	subw	y, (0x09, sp)
      008894 1E 15            [ 2] 1309 	ldw	x, (0x15, sp)
      008896 FF               [ 2] 1310 	ldw	(x), y
      008897 16 11            [ 2] 1311 	ldw	y, (0x11, sp)
      008899 72 F2 09         [ 2] 1312 	subw	y, (0x09, sp)
      00889C 1E 01            [ 2] 1313 	ldw	x, (0x01, sp)
      00889E FF               [ 2] 1314 	ldw	(x), y
                                   1315 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 499: return 1;
      00889F A6 01            [ 1] 1316 	ld	a, #0x01
      0088A1 20 15            [ 2] 1317 	jra	00113$
      0088A3                       1318 00112$:
                                   1319 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 501: off = (int16_t)(a * BIT_U);
      0088A3 16 05            [ 2] 1320 	ldw	y, (0x05, sp)
      0088A5 17 09            [ 2] 1321 	ldw	(0x09, sp), y
                                   1322 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 502: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      0088A7 16 0F            [ 2] 1323 	ldw	y, (0x0f, sp)
      0088A9 72 F2 09         [ 2] 1324 	subw	y, (0x09, sp)
      0088AC 1E 15            [ 2] 1325 	ldw	x, (0x15, sp)
      0088AE FF               [ 2] 1326 	ldw	(x), y
      0088AF 16 11            [ 2] 1327 	ldw	y, (0x11, sp)
      0088B1 72 F2 09         [ 2] 1328 	subw	y, (0x09, sp)
      0088B4 1E 01            [ 2] 1329 	ldw	x, (0x01, sp)
      0088B6 FF               [ 2] 1330 	ldw	(x), y
                                   1331 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 503: return 0;
      0088B7 4F               [ 1] 1332 	clr	a
      0088B8                       1333 00113$:
                                   1334 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 504: }
      0088B8 1E 0B            [ 2] 1335 	ldw	x, (11, sp)
      0088BA 5B 18            [ 2] 1336 	addw	sp, #24
      0088BC FC               [ 2] 1337 	jp	(x)
                                   1338 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 506: static void cal_cloud(int16_t u, uint8_t fam)
                                   1339 ;	-----------------------------------------
                                   1340 ;	 function cal_cloud
                                   1341 ;	-----------------------------------------
      0088BD                       1342 _cal_cloud:
      0088BD 89               [ 2] 1343 	pushw	x
                                   1344 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 510: if (fam != 5 && fam != 6) return;
      0088BE A1 05            [ 1] 1345 	cp	a, #0x05
      0088C0 27 04            [ 1] 1346 	jreq	00102$
      0088C2 A1 06            [ 1] 1347 	cp	a, #0x06
      0088C4 26 3C            [ 1] 1348 	jrne	00111$
      0088C6                       1349 00102$:
                                   1350 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 511: if (u < 0) return;
      0088C6 5D               [ 2] 1351 	tnzw	x
      0088C7 2B 39            [ 1] 1352 	jrmi	00111$
                                   1353 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 512: f = (uint8_t)(fam - 5);
      0088C9 A0 05            [ 1] 1354 	sub	a, #0x05
      0088CB 90 97            [ 1] 1355 	ld	yl, a
                                   1356 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 513: x = (int16_t)(u & (BIT_U - 1));
      0088CD 9E               [ 1] 1357 	ld	a, xh
      0088CE A4 01            [ 1] 1358 	and	a, #0x01
      0088D0 95               [ 1] 1359 	ld	xh, a
      0088D1 1F 01            [ 2] 1360 	ldw	(0x01, sp), x
                                   1361 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 514: d = (int16_t)(x - c_c0[f]);
      0088D3 93               [ 1] 1362 	ldw	x, y
      0088D4 4F               [ 1] 1363 	clr	a
      0088D5 95               [ 1] 1364 	ld	xh, a
      0088D6 58               [ 2] 1365 	sllw	x
      0088D7 DE 00 B9         [ 2] 1366 	ldw	x, (_c_c0+0, x)
      0088DA 50               [ 2] 1367 	negw	x
      0088DB 72 FB 01         [ 2] 1368 	addw	x, (0x01, sp)
                                   1369 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 515: if (d >= -EPS_HIST && d < EPS_HIST) {
      0088DE A3 FF C0         [ 2] 1370 	cpw	x, #0xffc0
      0088E1 2F 1F            [ 1] 1371 	jrslt	00111$
      0088E3 A3 00 40         [ 2] 1372 	cpw	x, #0x0040
      0088E6 2E 1A            [ 1] 1373 	jrsge	00111$
                                   1374 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 516: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
      0088E8 1C 00 40         [ 2] 1375 	addw	x, #0x0040
      0088EB 57               [ 2] 1376 	sraw	x
                                   1377 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 517: if (c_hist[f][b] < 255) c_hist[f][b]++;
      0088EC A6 40            [ 1] 1378 	ld	a, #0x40
      0088EE 90 42            [ 4] 1379 	mul	y, a
      0088F0 72 A9 00 29      [ 2] 1380 	addw	y, #(_c_hist+0)
      0088F4 17 01            [ 2] 1381 	ldw	(0x01, sp), y
      0088F6 4F               [ 1] 1382 	clr	a
      0088F7 95               [ 1] 1383 	ld	xh, a
      0088F8 72 FB 01         [ 2] 1384 	addw	x, (0x01, sp)
      0088FB F6               [ 1] 1385 	ld	a, (x)
      0088FC A1 FF            [ 1] 1386 	cp	a, #0xff
      0088FE 24 02            [ 1] 1387 	jrnc	00111$
      008900 4C               [ 1] 1388 	inc	a
      008901 F7               [ 1] 1389 	ld	(x), a
      008902                       1390 00111$:
                                   1391 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 519: }
      008902 85               [ 2] 1392 	popw	x
      008903 81               [ 4] 1393 	ret
                                   1394 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 521: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1395 ;	-----------------------------------------
                                   1396 ;	 function cal_add
                                   1397 ;	-----------------------------------------
      008904                       1398 _cal_add:
      008904 52 0C            [ 2] 1399 	sub	sp, #12
      008906 51               [ 1] 1400 	exgw	x, y
                                   1401 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 525: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
      008907 96               [ 1] 1402 	ldw	x, sp
      008908 1C 00 03         [ 2] 1403 	addw	x, #3
      00890B 89               [ 2] 1404 	pushw	x
      00890C 96               [ 1] 1405 	ldw	x, sp
      00890D 1C 00 03         [ 2] 1406 	addw	x, #3
      008910 89               [ 2] 1407 	pushw	x
      008911 1E 1A            [ 2] 1408 	ldw	x, (0x1a, sp)
      008913 89               [ 2] 1409 	pushw	x
      008914 1E 19            [ 2] 1410 	ldw	x, (0x19, sp)
      008916 89               [ 2] 1411 	pushw	x
      008917 1E 19            [ 2] 1412 	ldw	x, (0x19, sp)
      008919 89               [ 2] 1413 	pushw	x
      00891A 1E 19            [ 2] 1414 	ldw	x, (0x19, sp)
      00891C 89               [ 2] 1415 	pushw	x
      00891D 93               [ 1] 1416 	ldw	x, y
      00891E CD 87 E2         [ 4] 1417 	call	_label_interval
                                   1418 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 526: if (cls < 0) return;
      008921 6B 0A            [ 1] 1419 	ld	(0x0a, sp), a
      008923 2A 03            [ 1] 1420 	jrpl	00102$
      008925 CC 8A 14         [ 2] 1421 	jp	00138$
      008928                       1422 00102$:
                                   1423 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if (lo > c_lo0) c_lo0 = lo;
      008928 1E 01            [ 2] 1424 	ldw	x, (0x01, sp)
                                   1425 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: if (hi < c_hi0) c_hi0 = hi;
      00892A 16 03            [ 2] 1426 	ldw	y, (0x03, sp)
                                   1427 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 527: if (cls == 0) {
      00892C 0D 0A            [ 1] 1428 	tnz	(0x0a, sp)
      00892E 26 24            [ 1] 1429 	jrne	00116$
                                   1430 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if (lo > c_lo0) c_lo0 = lo;
      008930 89               [ 2] 1431 	pushw	x
      008931 1E 03            [ 2] 1432 	ldw	x, (0x03, sp)
      008933 C3 00 19         [ 2] 1433 	cpw	x, _c_lo0+0
      008936 85               [ 2] 1434 	popw	x
      008937 2D 03            [ 1] 1435 	jrsle	00104$
      008939 CF 00 19         [ 2] 1436 	ldw	_c_lo0+0, x
      00893C                       1437 00104$:
                                   1438 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: if (hi < c_hi0) c_hi0 = hi;
      00893C 1E 03            [ 2] 1439 	ldw	x, (0x03, sp)
      00893E C3 00 1B         [ 2] 1440 	cpw	x, _c_hi0+0
      008941 2E 04            [ 1] 1441 	jrsge	00106$
      008943 90 CF 00 1B      [ 2] 1442 	ldw	_c_hi0+0, y
      008947                       1443 00106$:
                                   1444 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 530: if (c_n0 < 255) c_n0++;
      008947 C6 00 21         [ 1] 1445 	ld	a, _c_n0+0
      00894A A1 FF            [ 1] 1446 	cp	a, #0xff
      00894C 24 28            [ 1] 1447 	jrnc	00117$
      00894E 72 5C 00 21      [ 1] 1448 	inc	_c_n0+0
      008952 20 22            [ 2] 1449 	jra	00117$
      008954                       1450 00116$:
                                   1451 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 532: if (lo > c_lo1) c_lo1 = lo;
      008954 89               [ 2] 1452 	pushw	x
      008955 1E 03            [ 2] 1453 	ldw	x, (0x03, sp)
      008957 C3 00 1D         [ 2] 1454 	cpw	x, _c_lo1+0
      00895A 85               [ 2] 1455 	popw	x
      00895B 2D 03            [ 1] 1456 	jrsle	00110$
      00895D CF 00 1D         [ 2] 1457 	ldw	_c_lo1+0, x
      008960                       1458 00110$:
                                   1459 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 533: if (hi < c_hi1) c_hi1 = hi;
      008960 1E 03            [ 2] 1460 	ldw	x, (0x03, sp)
      008962 C3 00 1F         [ 2] 1461 	cpw	x, _c_hi1+0
      008965 2E 04            [ 1] 1462 	jrsge	00112$
      008967 90 CF 00 1F      [ 2] 1463 	ldw	_c_hi1+0, y
      00896B                       1464 00112$:
                                   1465 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 534: if (c_n1 < 255) c_n1++;
      00896B C6 00 22         [ 1] 1466 	ld	a, _c_n1+0
      00896E A1 FF            [ 1] 1467 	cp	a, #0xff
      008970 24 04            [ 1] 1468 	jrnc	00117$
      008972 72 5C 00 22      [ 1] 1469 	inc	_c_n1+0
      008976                       1470 00117$:
                                   1471 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 536: if ((fam == 5 || fam == 6) && lo >= 0) {
      008976 7B 15            [ 1] 1472 	ld	a, (0x15, sp)
      008978 A1 05            [ 1] 1473 	cp	a, #0x05
      00897A 27 09            [ 1] 1474 	jreq	00137$
      00897C 7B 15            [ 1] 1475 	ld	a, (0x15, sp)
      00897E A1 06            [ 1] 1476 	cp	a, #0x06
      008980 27 03            [ 1] 1477 	jreq	00289$
      008982 CC 8A 14         [ 2] 1478 	jp	00138$
      008985                       1479 00289$:
      008985                       1480 00137$:
      008985 16 01            [ 2] 1481 	ldw	y, (0x01, sp)
      008987 2A 03            [ 1] 1482 	jrpl	00290$
      008989 CC 8A 14         [ 2] 1483 	jp	00138$
      00898C                       1484 00290$:
                                   1485 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 537: uint8_t f = (uint8_t)(fam - 5);
      00898C 7B 15            [ 1] 1486 	ld	a, (0x15, sp)
      00898E A0 05            [ 1] 1487 	sub	a, #0x05
      008990 97               [ 1] 1488 	ld	xl, a
                                   1489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 538: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
      008991 90 9E            [ 1] 1490 	ld	a, yh
      008993 A4 01            [ 1] 1491 	and	a, #0x01
      008995 90 95            [ 1] 1492 	ld	yh, a
      008997 4F               [ 1] 1493 	clr	a
      008998 95               [ 1] 1494 	ld	xh, a
      008999 58               [ 2] 1495 	sllw	x
      00899A 1F 05            [ 2] 1496 	ldw	(0x05, sp), x
      00899C DE 00 B9         [ 2] 1497 	ldw	x, (_c_c0+0, x)
      00899F 1F 0B            [ 2] 1498 	ldw	(0x0b, sp), x
      0089A1 93               [ 1] 1499 	ldw	x, y
      0089A2 72 F0 0B         [ 2] 1500 	subw	x, (0x0b, sp)
                                   1501 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 539: if (d >= -EPS_HIST && d < EPS_HIST) {
      0089A5 1F 07            [ 2] 1502 	ldw	(0x07, sp), x
      0089A7 A3 FF C0         [ 2] 1503 	cpw	x, #0xffc0
      0089AA 2F 68            [ 1] 1504 	jrslt	00138$
      0089AC 1E 07            [ 2] 1505 	ldw	x, (0x07, sp)
      0089AE A3 00 40         [ 2] 1506 	cpw	x, #0x0040
      0089B1 2E 61            [ 1] 1507 	jrsge	00138$
                                   1508 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 540: if (cls == 0) {
      0089B3 0D 0A            [ 1] 1509 	tnz	(0x0a, sp)
      0089B5 26 2B            [ 1] 1510 	jrne	00129$
                                   1511 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 541: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
      0089B7 1E 05            [ 2] 1512 	ldw	x, (0x05, sp)
      0089B9 1C 00 A9         [ 2] 1513 	addw	x, #(_c_labx0+0)
      0089BC 1F 0B            [ 2] 1514 	ldw	(0x0b, sp), x
      0089BE FE               [ 2] 1515 	ldw	x, (x)
      0089BF 13 07            [ 2] 1516 	cpw	x, (0x07, sp)
      0089C1 2E 0D            [ 1] 1517 	jrsge	00121$
      0089C3 16 05            [ 2] 1518 	ldw	y, (0x05, sp)
      0089C5 90 DF 00 B1      [ 2] 1519 	ldw	((_c_labx0b+0), y), x
      0089C9 1E 0B            [ 2] 1520 	ldw	x, (0x0b, sp)
      0089CB 16 07            [ 2] 1521 	ldw	y, (0x07, sp)
      0089CD FF               [ 2] 1522 	ldw	(x), y
      0089CE 20 44            [ 2] 1523 	jra	00138$
      0089D0                       1524 00121$:
                                   1525 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 542: else if (d > c_labx0b[f]) c_labx0b[f] = d;
      0089D0 16 05            [ 2] 1526 	ldw	y, (0x05, sp)
      0089D2 72 A9 00 B1      [ 2] 1527 	addw	y, #(_c_labx0b+0)
      0089D6 93               [ 1] 1528 	ldw	x, y
      0089D7 FE               [ 2] 1529 	ldw	x, (x)
      0089D8 13 07            [ 2] 1530 	cpw	x, (0x07, sp)
      0089DA 2E 38            [ 1] 1531 	jrsge	00138$
      0089DC 93               [ 1] 1532 	ldw	x, y
      0089DD 16 07            [ 2] 1533 	ldw	y, (0x07, sp)
      0089DF FF               [ 2] 1534 	ldw	(x), y
      0089E0 20 32            [ 2] 1535 	jra	00138$
      0089E2                       1536 00129$:
                                   1537 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 544: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
      0089E2 1E 05            [ 2] 1538 	ldw	x, (0x05, sp)
      0089E4 1C 00 AD         [ 2] 1539 	addw	x, #(_c_labx1+0)
      0089E7 1F 09            [ 2] 1540 	ldw	(0x09, sp), x
      0089E9 FE               [ 2] 1541 	ldw	x, (x)
      0089EA 1F 0B            [ 2] 1542 	ldw	(0x0b, sp), x
      0089EC 1E 07            [ 2] 1543 	ldw	x, (0x07, sp)
      0089EE 13 0B            [ 2] 1544 	cpw	x, (0x0b, sp)
      0089F0 2E 0E            [ 1] 1545 	jrsge	00126$
      0089F2 1E 05            [ 2] 1546 	ldw	x, (0x05, sp)
      0089F4 16 0B            [ 2] 1547 	ldw	y, (0x0b, sp)
      0089F6 DF 00 B5         [ 2] 1548 	ldw	((_c_labx1b+0), x), y
      0089F9 1E 09            [ 2] 1549 	ldw	x, (0x09, sp)
      0089FB 16 07            [ 2] 1550 	ldw	y, (0x07, sp)
      0089FD FF               [ 2] 1551 	ldw	(x), y
      0089FE 20 14            [ 2] 1552 	jra	00138$
      008A00                       1553 00126$:
                                   1554 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 545: else if (d < c_labx1b[f]) c_labx1b[f] = d;
      008A00 16 05            [ 2] 1555 	ldw	y, (0x05, sp)
      008A02 72 A9 00 B5      [ 2] 1556 	addw	y, #(_c_labx1b+0)
      008A06 93               [ 1] 1557 	ldw	x, y
      008A07 FE               [ 2] 1558 	ldw	x, (x)
      008A08 1F 0B            [ 2] 1559 	ldw	(0x0b, sp), x
      008A0A 1E 07            [ 2] 1560 	ldw	x, (0x07, sp)
      008A0C 13 0B            [ 2] 1561 	cpw	x, (0x0b, sp)
      008A0E 2E 04            [ 1] 1562 	jrsge	00138$
      008A10 93               [ 1] 1563 	ldw	x, y
      008A11 16 07            [ 2] 1564 	ldw	y, (0x07, sp)
      008A13 FF               [ 2] 1565 	ldw	(x), y
      008A14                       1566 00138$:
                                   1567 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 549: }
      008A14 1E 0D            [ 2] 1568 	ldw	x, (13, sp)
      008A16 5B 17            [ 2] 1569 	addw	sp, #23
      008A18 FC               [ 2] 1570 	jp	(x)
                                   1571 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 552: static uint8_t theta56(uint8_t f, int16_t *theta_out)
                                   1572 ;	-----------------------------------------
                                   1573 ;	 function theta56
                                   1574 ;	-----------------------------------------
      008A19                       1575 _theta56:
      008A19 52 26            [ 2] 1576 	sub	sp, #38
      008A1B 1F 23            [ 2] 1577 	ldw	(0x23, sp), x
                                   1578 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 554: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
      008A1D 5F               [ 1] 1579 	clrw	x
      008A1E 97               [ 1] 1580 	ld	xl, a
      008A1F 58               [ 2] 1581 	sllw	x
      008A20 1F 01            [ 2] 1582 	ldw	(0x01, sp), x
      008A22 DE 00 A9         [ 2] 1583 	ldw	x, (_c_labx0+0, x)
      008A25 16 01            [ 2] 1584 	ldw	y, (0x01, sp)
      008A27 90 DE 00 AD      [ 2] 1585 	ldw	y, (_c_labx1+0, y)
                                   1586 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 555: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
      008A2B 1F 03            [ 2] 1587 	ldw	(0x03, sp), x
      008A2D A3 C0 00         [ 2] 1588 	cpw	x, #0xc000
      008A30 2C 04            [ 1] 1589 	jrsgt	00483$
      008A32 0F 05            [ 1] 1590 	clr	(0x05, sp)
      008A34 20 06            [ 2] 1591 	jra	00484$
      008A36                       1592 00483$:
      008A36 88               [ 1] 1593 	push	a
      008A37 A6 01            [ 1] 1594 	ld	a, #0x01
      008A39 6B 06            [ 1] 1595 	ld	(0x06, sp), a
      008A3B 84               [ 1] 1596 	pop	a
      008A3C                       1597 00484$:
      008A3C 17 06            [ 2] 1598 	ldw	(0x06, sp), y
      008A3E 93               [ 1] 1599 	ldw	x, y
      008A3F A3 3F FF         [ 2] 1600 	cpw	x, #0x3fff
      008A42 2F 04            [ 1] 1601 	jrslt	00485$
      008A44 0F 08            [ 1] 1602 	clr	(0x08, sp)
      008A46 20 06            [ 2] 1603 	jra	00486$
      008A48                       1604 00485$:
      008A48 88               [ 1] 1605 	push	a
      008A49 A6 01            [ 1] 1606 	ld	a, #0x01
      008A4B 6B 09            [ 1] 1607 	ld	(0x09, sp), a
      008A4D 84               [ 1] 1608 	pop	a
      008A4E                       1609 00486$:
                                   1610 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 556: int16_t zlo = (int16_t)(x0 + 1);
      008A4E 1E 03            [ 2] 1611 	ldw	x, (0x03, sp)
      008A50 5C               [ 1] 1612 	incw	x
      008A51 1F 09            [ 2] 1613 	ldw	(0x09, sp), x
                                   1614 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 557: int16_t zhi = x1;
      008A53 17 0B            [ 2] 1615 	ldw	(0x0b, sp), y
                                   1616 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 558: int16_t theta = 0;
      008A55 5F               [ 1] 1617 	clrw	x
      008A56 1F 0D            [ 2] 1618 	ldw	(0x0d, sp), x
                                   1619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 559: uint8_t have_theta = 0;
      008A58 0F 0F            [ 1] 1620 	clr	(0x0f, sp)
                                   1621 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 560: int16_t top = 0;
      008A5A 5F               [ 1] 1622 	clrw	x
      008A5B 1F 10            [ 2] 1623 	ldw	(0x10, sp), x
                                   1624 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 561: uint8_t have_top = 0, clear1 = 0;
      008A5D 0F 12            [ 1] 1625 	clr	(0x12, sp)
      008A5F 0F 13            [ 1] 1626 	clr	(0x13, sp)
                                   1627 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 563: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
      008A61 AE FF E0         [ 2] 1628 	ldw	x, #0xffe0
      008A64 13 09            [ 2] 1629 	cpw	x, (0x09, sp)
      008A66 2F 02            [ 1] 1630 	jrslt	00102$
      008A68 1F 09            [ 2] 1631 	ldw	(0x09, sp), x
      008A6A                       1632 00102$:
                                   1633 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 564: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
      008A6A 1E 0B            [ 2] 1634 	ldw	x, (0x0b, sp)
      008A6C A3 00 20         [ 2] 1635 	cpw	x, #0x0020
      008A6F 2D 05            [ 1] 1636 	jrsle	00104$
      008A71 AE 00 20         [ 2] 1637 	ldw	x, #0x0020
      008A74 1F 0B            [ 2] 1638 	ldw	(0x0b, sp), x
      008A76                       1639 00104$:
                                   1640 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
      008A76 41               [ 1] 1641 	exg	a, xl
      008A77 A6 40            [ 1] 1642 	ld	a, #0x40
      008A79 41               [ 1] 1643 	exg	a, xl
      008A7A 42               [ 4] 1644 	mul	x, a
      008A7B 1F 14            [ 2] 1645 	ldw	(0x14, sp), x
                                   1646 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 565: if (zlo < zhi) {
      008A7D 1E 09            [ 2] 1647 	ldw	x, (0x09, sp)
      008A7F 13 0B            [ 2] 1648 	cpw	x, (0x0b, sp)
      008A81 2F 03            [ 1] 1649 	jrslt	00489$
      008A83 CC 8B 9C         [ 2] 1650 	jp	00126$
      008A86                       1651 00489$:
                                   1652 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 566: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
      008A86 1E 09            [ 2] 1653 	ldw	x, (0x09, sp)
      008A88 1C 00 40         [ 2] 1654 	addw	x, #0x0040
      008A8B 57               [ 2] 1655 	sraw	x
      008A8C 41               [ 1] 1656 	exg	a, xl
      008A8D 6B 25            [ 1] 1657 	ld	(0x25, sp), a
      008A8F 41               [ 1] 1658 	exg	a, xl
                                   1659 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 567: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
      008A90 1E 0B            [ 2] 1660 	ldw	x, (0x0b, sp)
      008A92 1C 00 3F         [ 2] 1661 	addw	x, #0x003f
      008A95 57               [ 2] 1662 	sraw	x
      008A96 41               [ 1] 1663 	exg	a, xl
      008A97 6B 16            [ 1] 1664 	ld	(0x16, sp), a
      008A99 41               [ 1] 1665 	exg	a, xl
                                   1666 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 568: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
      008A9A 16 09            [ 2] 1667 	ldw	y, (0x09, sp)
      008A9C 17 17            [ 2] 1668 	ldw	(0x17, sp), y
      008A9E 5F               [ 1] 1669 	clrw	x
      008A9F 1F 19            [ 2] 1670 	ldw	(0x19, sp), x
      008AA1 5F               [ 1] 1671 	clrw	x
      008AA2 1F 1B            [ 2] 1672 	ldw	(0x1b, sp), x
      008AA4 5F               [ 1] 1673 	clrw	x
      008AA5 5A               [ 2] 1674 	decw	x
      008AA6 1F 1D            [ 2] 1675 	ldw	(0x1d, sp), x
                                   1676 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
      008AA8 1E 14            [ 2] 1677 	ldw	x, (0x14, sp)
      008AAA 1C 00 29         [ 2] 1678 	addw	x, #(_c_hist+0)
      008AAD 1F 1F            [ 2] 1679 	ldw	(0x1f, sp), x
      008AAF 0F 26            [ 1] 1680 	clr	(0x26, sp)
      008AB1                       1681 00170$:
      008AB1 7B 25            [ 1] 1682 	ld	a, (0x25, sp)
      008AB3 11 16            [ 1] 1683 	cp	a, (0x16, sp)
      008AB5 22 2F            [ 1] 1684 	jrugt	00253$
                                   1685 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 571: if (c_hist[f][b]) {
      008AB7 5F               [ 1] 1686 	clrw	x
      008AB8 7B 25            [ 1] 1687 	ld	a, (0x25, sp)
      008ABA 97               [ 1] 1688 	ld	xl, a
      008ABB 72 FB 1F         [ 2] 1689 	addw	x, (0x1f, sp)
      008ABE F6               [ 1] 1690 	ld	a, (x)
      008ABF 27 21            [ 1] 1691 	jreq	00171$
                                   1692 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 572: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008AC1 7B 25            [ 1] 1693 	ld	a, (0x25, sp)
      008AC3 5F               [ 1] 1694 	clrw	x
      008AC4 97               [ 1] 1695 	ld	xl, a
      008AC5 58               [ 2] 1696 	sllw	x
      008AC6 1C FF C1         [ 2] 1697 	addw	x, #0xffc1
                                   1698 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 573: int16_t gp = (int16_t)(x - prev);
      008AC9 1F 21            [ 2] 1699 	ldw	(0x21, sp), x
      008ACB 72 F0 17         [ 2] 1700 	subw	x, (0x17, sp)
                                   1701 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 574: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
      008ACE 13 1D            [ 2] 1702 	cpw	x, (0x1d, sp)
      008AD0 2D 0A            [ 1] 1703 	jrsle	00106$
      008AD2 1F 1D            [ 2] 1704 	ldw	(0x1d, sp), x
      008AD4 16 17            [ 2] 1705 	ldw	y, (0x17, sp)
      008AD6 17 19            [ 2] 1706 	ldw	(0x19, sp), y
      008AD8 16 21            [ 2] 1707 	ldw	y, (0x21, sp)
      008ADA 17 1B            [ 2] 1708 	ldw	(0x1b, sp), y
      008ADC                       1709 00106$:
                                   1710 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 575: prev = x;
      008ADC 16 21            [ 2] 1711 	ldw	y, (0x21, sp)
      008ADE 17 17            [ 2] 1712 	ldw	(0x17, sp), y
                                   1713 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 576: nocc++;
      008AE0 0C 26            [ 1] 1714 	inc	(0x26, sp)
      008AE2                       1715 00171$:
                                   1716 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
      008AE2 0C 25            [ 1] 1717 	inc	(0x25, sp)
      008AE4 20 CB            [ 2] 1718 	jra	00170$
      008AE6                       1719 00253$:
      008AE6 7B 26            [ 1] 1720 	ld	a, (0x26, sp)
      008AE8 97               [ 1] 1721 	ld	xl, a
                                   1722 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 580: int16_t gp = (int16_t)(zhi - prev);
      008AE9 16 0B            [ 2] 1723 	ldw	y, (0x0b, sp)
      008AEB 72 F2 17         [ 2] 1724 	subw	y, (0x17, sp)
                                   1725 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 581: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
      008AEE 51               [ 1] 1726 	exgw	x, y
      008AEF 13 1D            [ 2] 1727 	cpw	x, (0x1d, sp)
      008AF1 51               [ 1] 1728 	exgw	x, y
      008AF2 2D 0A            [ 1] 1729 	jrsle	00111$
      008AF4 17 1D            [ 2] 1730 	ldw	(0x1d, sp), y
      008AF6 16 17            [ 2] 1731 	ldw	y, (0x17, sp)
      008AF8 17 19            [ 2] 1732 	ldw	(0x19, sp), y
      008AFA 16 0B            [ 2] 1733 	ldw	y, (0x0b, sp)
      008AFC 17 1B            [ 2] 1734 	ldw	(0x1b, sp), y
      008AFE                       1735 00111$:
                                   1736 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 583: if (nocc == 0) {
      008AFE 9F               [ 1] 1737 	ld	a, xl
      008AFF 4D               [ 1] 1738 	tnz	a
      008B00 26 1D            [ 1] 1739 	jrne	00123$
                                   1740 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 584: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
      008B02 0D 05            [ 1] 1741 	tnz	(0x05, sp)
      008B04 26 03            [ 1] 1742 	jrne	00495$
      008B06 CC 8B 9C         [ 2] 1743 	jp	00126$
      008B09                       1744 00495$:
      008B09 0D 08            [ 1] 1745 	tnz	(0x08, sp)
      008B0B 26 03            [ 1] 1746 	jrne	00496$
      008B0D CC 8B 9C         [ 2] 1747 	jp	00126$
      008B10                       1748 00496$:
      008B10 1E 09            [ 2] 1749 	ldw	x, (0x09, sp)
      008B12 72 FB 0B         [ 2] 1750 	addw	x, (0x0b, sp)
      008B15 57               [ 2] 1751 	sraw	x
      008B16 1F 0D            [ 2] 1752 	ldw	(0x0d, sp), x
      008B18 A6 01            [ 1] 1753 	ld	a, #0x01
      008B1A 6B 0F            [ 1] 1754 	ld	(0x0f, sp), a
      008B1C CC 8B 9C         [ 2] 1755 	jp	00126$
      008B1F                       1756 00123$:
                                   1757 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 586: uint8_t ok = (bg >= EPS_GAP_MIN);
      008B1F 16 1D            [ 2] 1758 	ldw	y, (0x1d, sp)
      008B21 90 A3 00 05      [ 2] 1759 	cpw	y, #0x0005
      008B25 2F 02            [ 1] 1760 	jrslt	00497$
      008B27 4F               [ 1] 1761 	clr	a
      008B28 C5                    1762 	.byte 0xc5
      008B29                       1763 00497$:
      008B29 A6 01            [ 1] 1764 	ld	a, #0x01
      008B2B                       1765 00498$:
      008B2B A8 01            [ 1] 1766 	xor	a, #0x01
                                   1767 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 587: if (ok && (uint8_t)(nocc + 1) >= 4) {
      008B2D 6B 26            [ 1] 1768 	ld	(0x26, sp), a
      008B2F 27 5B            [ 1] 1769 	jreq	00118$
      008B31 9F               [ 1] 1770 	ld	a, xl
      008B32 4C               [ 1] 1771 	inc	a
      008B33 A1 04            [ 1] 1772 	cp	a, #0x04
      008B35 25 55            [ 1] 1773 	jrc	00118$
                                   1774 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 588: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
      008B37 16 1D            [ 2] 1775 	ldw	y, (0x1d, sp)
      008B39 90 9E            [ 1] 1776 	ld	a, yh
      008B3B 49               [ 1] 1777 	rlc	a
      008B3C 4F               [ 1] 1778 	clr	a
      008B3D A2 00            [ 1] 1779 	sbc	a, #0x00
      008B3F 95               [ 1] 1780 	ld	xh, a
      008B40 02               [ 1] 1781 	rlwa	x
      008B41 6B 20            [ 1] 1782 	ld	(0x20, sp), a
      008B43 01               [ 1] 1783 	rrwa	x
      008B44 6B 1F            [ 1] 1784 	ld	(0x1f, sp), a
      008B46 90 58            [ 2] 1785 	sllw	y
      008B48 09 20            [ 1] 1786 	rlc	(0x20, sp)
      008B4A 09 1F            [ 1] 1787 	rlc	(0x1f, sp)
      008B4C 17 21            [ 2] 1788 	ldw	(0x21, sp), y
      008B4E 4F               [ 1] 1789 	clr	a
      008B4F 95               [ 1] 1790 	ld	xh, a
      008B50 5C               [ 1] 1791 	incw	x
      008B51 90 5F            [ 1] 1792 	clrw	y
      008B53 5D               [ 2] 1793 	tnzw	x
      008B54 2A 02            [ 1] 1794 	jrpl	00501$
      008B56 90 5A            [ 2] 1795 	decw	y
      008B58                       1796 00501$:
      008B58 89               [ 2] 1797 	pushw	x
      008B59 90 89            [ 2] 1798 	pushw	y
      008B5B 1E 25            [ 2] 1799 	ldw	x, (0x25, sp)
      008B5D 89               [ 2] 1800 	pushw	x
      008B5E 1E 25            [ 2] 1801 	ldw	x, (0x25, sp)
      008B60 89               [ 2] 1802 	pushw	x
      008B61 CD 9B 29         [ 4] 1803 	call	__mullong
      008B64 5B 08            [ 2] 1804 	addw	sp, #8
      008B66 1F 21            [ 2] 1805 	ldw	(0x21, sp), x
      008B68 17 1F            [ 2] 1806 	ldw	(0x1f, sp), y
      008B6A 1E 0B            [ 2] 1807 	ldw	x, (0x0b, sp)
      008B6C 72 F0 09         [ 2] 1808 	subw	x, (0x09, sp)
      008B6F 89               [ 2] 1809 	pushw	x
      008B70 AE 00 05         [ 2] 1810 	ldw	x, #0x0005
      008B73 CD 9A 54         [ 4] 1811 	call	___mulsint2slong
      008B76 5B 02            [ 2] 1812 	addw	sp, #2
      008B78 1F 0B            [ 2] 1813 	ldw	(0x0b, sp), x
      008B7A 17 09            [ 2] 1814 	ldw	(0x09, sp), y
      008B7C 1E 21            [ 2] 1815 	ldw	x, (0x21, sp)
      008B7E 13 0B            [ 2] 1816 	cpw	x, (0x0b, sp)
      008B80 7B 20            [ 1] 1817 	ld	a, (0x20, sp)
      008B82 12 0A            [ 1] 1818 	sbc	a, (0x0a, sp)
      008B84 7B 1F            [ 1] 1819 	ld	a, (0x1f, sp)
      008B86 12 09            [ 1] 1820 	sbc	a, (0x09, sp)
      008B88 2E 02            [ 1] 1821 	jrsge	00118$
                                   1822 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 589: ok = 0;
      008B8A 0F 26            [ 1] 1823 	clr	(0x26, sp)
      008B8C                       1824 00118$:
                                   1825 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 591: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
      008B8C 0D 26            [ 1] 1826 	tnz	(0x26, sp)
      008B8E 27 0C            [ 1] 1827 	jreq	00126$
      008B90 1E 19            [ 2] 1828 	ldw	x, (0x19, sp)
      008B92 72 FB 1B         [ 2] 1829 	addw	x, (0x1b, sp)
      008B95 57               [ 2] 1830 	sraw	x
      008B96 1F 0D            [ 2] 1831 	ldw	(0x0d, sp), x
      008B98 A6 01            [ 1] 1832 	ld	a, #0x01
      008B9A 6B 0F            [ 1] 1833 	ld	(0x0f, sp), a
      008B9C                       1834 00126$:
                                   1835 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 594: if (has0 || has1) {
      008B9C 0D 05            [ 1] 1836 	tnz	(0x05, sp)
      008B9E 26 07            [ 1] 1837 	jrne	00144$
      008BA0 0D 08            [ 1] 1838 	tnz	(0x08, sp)
      008BA2 26 03            [ 1] 1839 	jrne	00505$
      008BA4 CC 8C 25         [ 2] 1840 	jp	00245$
      008BA7                       1841 00505$:
      008BA7                       1842 00144$:
                                   1843 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 595: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
      008BA7 AE FF E0         [ 2] 1844 	ldw	x, #0xffe0
      008BAA 1F 21            [ 2] 1845 	ldw	(0x21, sp), x
      008BAC AE 00 20         [ 2] 1846 	ldw	x, #0x0020
      008BAF 1F 25            [ 2] 1847 	ldw	(0x25, sp), x
                                   1848 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 596: if (has0) {
      008BB1 0D 05            [ 1] 1849 	tnz	(0x05, sp)
      008BB3 27 19            [ 1] 1850 	jreq	00131$
                                   1851 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 597: wlo = (int16_t)(x0 - EPS_SLACK1);
      008BB5 1E 03            [ 2] 1852 	ldw	x, (0x03, sp)
      008BB7 1D 00 08         [ 2] 1853 	subw	x, #0x0008
      008BBA 1F 21            [ 2] 1854 	ldw	(0x21, sp), x
                                   1855 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 598: if (c_labx0b[f] > -0x4000 &&
      008BBC 1E 01            [ 2] 1856 	ldw	x, (0x01, sp)
      008BBE DE 00 B1         [ 2] 1857 	ldw	x, (_c_labx0b+0, x)
      008BC1 A3 C0 00         [ 2] 1858 	cpw	x, #0xc000
      008BC4 2D 08            [ 1] 1859 	jrsle	00131$
                                   1860 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 599: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
      008BC6 5A               [ 2] 1861 	decw	x
      008BC7 5A               [ 2] 1862 	decw	x
      008BC8 13 21            [ 2] 1863 	cpw	x, (0x21, sp)
      008BCA 2D 02            [ 1] 1864 	jrsle	00131$
                                   1865 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 600: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
      008BCC 1F 21            [ 2] 1866 	ldw	(0x21, sp), x
      008BCE                       1867 00131$:
                                   1868 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 602: if (has1) {
      008BCE 0D 08            [ 1] 1869 	tnz	(0x08, sp)
      008BD0 27 19            [ 1] 1870 	jreq	00136$
                                   1871 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 603: whi = (int16_t)(x1 + EPS_SLACK1);
      008BD2 1E 06            [ 2] 1872 	ldw	x, (0x06, sp)
      008BD4 1C 00 08         [ 2] 1873 	addw	x, #0x0008
      008BD7 1F 25            [ 2] 1874 	ldw	(0x25, sp), x
                                   1875 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 604: if (c_labx1b[f] < 0x3FFF &&
      008BD9 1E 01            [ 2] 1876 	ldw	x, (0x01, sp)
      008BDB DE 00 B5         [ 2] 1877 	ldw	x, (_c_labx1b+0, x)
      008BDE A3 3F FF         [ 2] 1878 	cpw	x, #0x3fff
      008BE1 2E 08            [ 1] 1879 	jrsge	00136$
                                   1880 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 605: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
      008BE3 5C               [ 1] 1881 	incw	x
      008BE4 5C               [ 1] 1882 	incw	x
      008BE5 13 25            [ 2] 1883 	cpw	x, (0x25, sp)
      008BE7 2E 02            [ 1] 1884 	jrsge	00136$
                                   1885 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 606: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
      008BE9 1F 25            [ 2] 1886 	ldw	(0x25, sp), x
      008BEB                       1887 00136$:
                                   1888 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 608: if (wlo > whi) {
                                   1889 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 609: theta = (int16_t)((wlo + whi) >> 1);
      008BEB 1E 21            [ 2] 1890 	ldw	x, (0x21, sp)
      008BED 13 25            [ 2] 1891 	cpw	x, (0x25, sp)
      008BEF 2D 0C            [ 1] 1892 	jrsle	00142$
      008BF1 72 FB 25         [ 2] 1893 	addw	x, (0x25, sp)
      008BF4 57               [ 2] 1894 	sraw	x
      008BF5 1F 0D            [ 2] 1895 	ldw	(0x0d, sp), x
                                   1896 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 610: have_theta = 1;
      008BF7 A6 01            [ 1] 1897 	ld	a, #0x01
      008BF9 6B 0F            [ 1] 1898 	ld	(0x0f, sp), a
      008BFB 20 28            [ 2] 1899 	jra	00245$
      008BFD                       1900 00142$:
                                   1901 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 612: int16_t th = have_theta ? theta : 0;
      008BFD 0D 0F            [ 1] 1902 	tnz	(0x0f, sp)
      008BFF 27 05            [ 1] 1903 	jreq	00175$
      008C01 16 0D            [ 2] 1904 	ldw	y, (0x0d, sp)
      008C03 17 1F            [ 2] 1905 	ldw	(0x1f, sp), y
      008C05 BC                    1906 	.byte 0xbc
      008C06                       1907 00175$:
      008C06 5F               [ 1] 1908 	clrw	x
      008C07 1F 1F            [ 2] 1909 	ldw	(0x1f, sp), x
      008C09                       1910 00176$:
                                   1911 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 613: if (th < wlo) th = wlo;
      008C09 1E 1F            [ 2] 1912 	ldw	x, (0x1f, sp)
      008C0B 13 21            [ 2] 1913 	cpw	x, (0x21, sp)
      008C0D 2E 04            [ 1] 1914 	jrsge	00138$
      008C0F 16 21            [ 2] 1915 	ldw	y, (0x21, sp)
      008C11 17 1F            [ 2] 1916 	ldw	(0x1f, sp), y
      008C13                       1917 00138$:
                                   1918 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 614: if (th > whi) th = whi;
      008C13 1E 1F            [ 2] 1919 	ldw	x, (0x1f, sp)
      008C15 13 25            [ 2] 1920 	cpw	x, (0x25, sp)
      008C17 2D 04            [ 1] 1921 	jrsle	00140$
      008C19 16 25            [ 2] 1922 	ldw	y, (0x25, sp)
      008C1B 17 1F            [ 2] 1923 	ldw	(0x1f, sp), y
      008C1D                       1924 00140$:
                                   1925 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 615: theta = th;
      008C1D 16 1F            [ 2] 1926 	ldw	y, (0x1f, sp)
      008C1F 17 0D            [ 2] 1927 	ldw	(0x0d, sp), y
                                   1928 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 616: have_theta = 1;
      008C21 A6 01            [ 1] 1929 	ld	a, #0x01
      008C23 6B 0F            [ 1] 1930 	ld	(0x0f, sp), a
                                   1931 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 619: for (b = 0; b < 64; b++) {
      008C25                       1932 00245$:
      008C25 1E 14            [ 2] 1933 	ldw	x, (0x14, sp)
      008C27 1C 00 29         [ 2] 1934 	addw	x, #(_c_hist+0)
      008C2A 1F 21            [ 2] 1935 	ldw	(0x21, sp), x
      008C2C 0F 26            [ 1] 1936 	clr	(0x26, sp)
      008C2E                       1937 00172$:
                                   1938 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 621: if (!c_hist[f][b]) continue;
      008C2E 5F               [ 1] 1939 	clrw	x
      008C2F 7B 26            [ 1] 1940 	ld	a, (0x26, sp)
      008C31 97               [ 1] 1941 	ld	xl, a
      008C32 72 FB 21         [ 2] 1942 	addw	x, (0x21, sp)
      008C35 F6               [ 1] 1943 	ld	a, (x)
      008C36 27 34            [ 1] 1944 	jreq	00157$
                                   1945 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 622: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008C38 7B 26            [ 1] 1946 	ld	a, (0x26, sp)
      008C3A 5F               [ 1] 1947 	clrw	x
      008C3B 48               [ 1] 1948 	sll	a
      008C3C 59               [ 2] 1949 	rlcw	x
      008C3D AB C1            [ 1] 1950 	add	a, #0xc1
      008C3F 6B 20            [ 1] 1951 	ld	(0x20, sp), a
      008C41 49               [ 1] 1952 	rlc	a
      008C42 4F               [ 1] 1953 	clr	a
      008C43 A2 00            [ 1] 1954 	sbc	a, #0x00
      008C45 6B 1F            [ 1] 1955 	ld	(0x1f, sp), a
                                   1956 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 623: if (d > EPS_CLEAR1) clear1 = 1;
      008C47 7B 20            [ 1] 1957 	ld	a, (0x20, sp)
      008C49 A1 12            [ 1] 1958 	cp	a, #0x12
      008C4B 2D 06            [ 1] 1959 	jrsle	00155$
      008C4D A6 01            [ 1] 1960 	ld	a, #0x01
      008C4F 6B 13            [ 1] 1961 	ld	(0x13, sp), a
      008C51 20 19            [ 2] 1962 	jra	00157$
      008C53                       1963 00155$:
                                   1964 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 624: else if (d > -EPS_CLAMP56) {
      008C53 1E 1F            [ 2] 1965 	ldw	x, (0x1f, sp)
      008C55 A3 FF E8         [ 2] 1966 	cpw	x, #0xffe8
      008C58 2D 12            [ 1] 1967 	jrsle	00157$
                                   1968 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 625: if (!have_top || d > top) top = d;
      008C5A 0D 12            [ 1] 1969 	tnz	(0x12, sp)
      008C5C 27 06            [ 1] 1970 	jreq	00149$
      008C5E 1E 1F            [ 2] 1971 	ldw	x, (0x1f, sp)
      008C60 13 10            [ 2] 1972 	cpw	x, (0x10, sp)
      008C62 2D 04            [ 1] 1973 	jrsle	00150$
      008C64                       1974 00149$:
      008C64 16 1F            [ 2] 1975 	ldw	y, (0x1f, sp)
      008C66 17 10            [ 2] 1976 	ldw	(0x10, sp), y
      008C68                       1977 00150$:
                                   1978 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 626: have_top = 1;
      008C68 A6 01            [ 1] 1979 	ld	a, #0x01
      008C6A 6B 12            [ 1] 1980 	ld	(0x12, sp), a
      008C6C                       1981 00157$:
                                   1982 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 619: for (b = 0; b < 64; b++) {
      008C6C 0C 26            [ 1] 1983 	inc	(0x26, sp)
      008C6E 7B 26            [ 1] 1984 	ld	a, (0x26, sp)
      008C70 A1 40            [ 1] 1985 	cp	a, #0x40
      008C72 25 BA            [ 1] 1986 	jrc	00172$
                                   1987 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 629: if (!clear1 && have_top) {
      008C74 0D 13            [ 1] 1988 	tnz	(0x13, sp)
      008C76 26 34            [ 1] 1989 	jrne	00167$
      008C78 0D 12            [ 1] 1990 	tnz	(0x12, sp)
      008C7A 27 30            [ 1] 1991 	jreq	00167$
                                   1992 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 630: int16_t floor_ = (int16_t)(top + EPS_TOPM);
      008C7C 7B 11            [ 1] 1993 	ld	a, (0x11, sp)
      008C7E AB 03            [ 1] 1994 	add	a, #0x03
      008C80 6B 26            [ 1] 1995 	ld	(0x26, sp), a
      008C82 49               [ 1] 1996 	rlc	a
      008C83 4F               [ 1] 1997 	clr	a
      008C84 A2 00            [ 1] 1998 	sbc	a, #0x00
      008C86 6B 25            [ 1] 1999 	ld	(0x25, sp), a
                                   2000 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 631: if (!have_theta || floor_ > theta) theta = floor_;
      008C88 0D 0F            [ 1] 2001 	tnz	(0x0f, sp)
      008C8A 27 06            [ 1] 2002 	jreq	00159$
      008C8C 1E 25            [ 2] 2003 	ldw	x, (0x25, sp)
      008C8E 13 0D            [ 2] 2004 	cpw	x, (0x0d, sp)
      008C90 2D 04            [ 1] 2005 	jrsle	00160$
      008C92                       2006 00159$:
      008C92 16 25            [ 2] 2007 	ldw	y, (0x25, sp)
      008C94 17 0D            [ 2] 2008 	ldw	(0x0d, sp), y
      008C96                       2009 00160$:
                                   2010 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 632: have_theta = 1;
      008C96 A6 01            [ 1] 2011 	ld	a, #0x01
      008C98 6B 0F            [ 1] 2012 	ld	(0x0f, sp), a
                                   2013 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 633: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
      008C9A 0D 08            [ 1] 2014 	tnz	(0x08, sp)
      008C9C 27 0E            [ 1] 2015 	jreq	00167$
      008C9E 1E 06            [ 2] 2016 	ldw	x, (0x06, sp)
      008CA0 5C               [ 1] 2017 	incw	x
      008CA1 5C               [ 1] 2018 	incw	x
      008CA2 13 25            [ 2] 2019 	cpw	x, (0x25, sp)
      008CA4 2D 06            [ 1] 2020 	jrsle	00167$
                                   2021 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 634: theta > (int16_t)(x1 + EPS_SLACK))
      008CA6 13 0D            [ 2] 2022 	cpw	x, (0x0d, sp)
      008CA8 2E 02            [ 1] 2023 	jrsge	00167$
                                   2024 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 635: theta = (int16_t)(x1 + EPS_SLACK);
      008CAA 1F 0D            [ 2] 2025 	ldw	(0x0d, sp), x
      008CAC                       2026 00167$:
                                   2027 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 637: *theta_out = theta;
      008CAC 1E 23            [ 2] 2028 	ldw	x, (0x23, sp)
      008CAE 16 0D            [ 2] 2029 	ldw	y, (0x0d, sp)
      008CB0 FF               [ 2] 2030 	ldw	(x), y
                                   2031 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 638: return have_theta;
      008CB1 7B 0F            [ 1] 2032 	ld	a, (0x0f, sp)
                                   2033 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 639: }
      008CB3 5B 26            [ 2] 2034 	addw	sp, #38
      008CB5 81               [ 4] 2035 	ret
                                   2036 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 641: static void calibrate(void)
                                   2037 ;	-----------------------------------------
                                   2038 ;	 function calibrate
                                   2039 ;	-----------------------------------------
      008CB6                       2040 _calibrate:
      008CB6 52 15            [ 2] 2041 	sub	sp, #21
                                   2042 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 645: c_lo0 = c_lo1 = -0x4000;
      008CB8 AE C0 00         [ 2] 2043 	ldw	x, #0xc000
      008CBB CF 00 1D         [ 2] 2044 	ldw	_c_lo1+0, x
      008CBE AE C0 00         [ 2] 2045 	ldw	x, #0xc000
      008CC1 CF 00 19         [ 2] 2046 	ldw	_c_lo0+0, x
                                   2047 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 646: c_hi0 = c_hi1 = 0x3FFF;
      008CC4 AE 3F FF         [ 2] 2048 	ldw	x, #0x3fff
      008CC7 CF 00 1F         [ 2] 2049 	ldw	_c_hi1+0, x
      008CCA AE 3F FF         [ 2] 2050 	ldw	x, #0x3fff
      008CCD CF 00 1B         [ 2] 2051 	ldw	_c_hi0+0, x
                                   2052 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 647: c_n0 = c_n1 = 0;
      008CD0 72 5F 00 22      [ 1] 2053 	clr	_c_n1+0
      008CD4 72 5F 00 21      [ 1] 2054 	clr	_c_n0+0
                                   2055 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 648: c_h0c = H0P; c_h1c = H1P;
      008CD8 AE 00 9A         [ 2] 2056 	ldw	x, #0x009a
      008CDB CF 00 23         [ 2] 2057 	ldw	_c_h0c+0, x
      008CDE AE 01 34         [ 2] 2058 	ldw	x, #0x0134
      008CE1 CF 00 25         [ 2] 2059 	ldw	_c_h1c+0, x
                                   2060 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 649: c_d56[0] = c_d56[1] = 0;
      008CE4 35 00 00 28      [ 1] 2061 	mov	_c_d56+1, #0x00
      008CE8 35 00 00 27      [ 1] 2062 	mov	_c_d56+0, #0x00
                                   2063 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 650: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
      008CEC CE 00 15         [ 2] 2064 	ldw	x, _g_K+0
      008CEF 89               [ 2] 2065 	pushw	x
      008CF0 AE 00 06         [ 2] 2066 	ldw	x, #0x0006
      008CF3 CD 9A 4E         [ 4] 2067 	call	___muluint2ulong
      008CF6 5B 02            [ 2] 2068 	addw	sp, #2
      008CF8 A6 0B            [ 1] 2069 	ld	a, #0x0b
      008CFA                       2070 00403$:
      008CFA 90 54            [ 2] 2071 	srlw	y
      008CFC 56               [ 2] 2072 	rrcw	x
      008CFD 4A               [ 1] 2073 	dec	a
      008CFE 26 FA            [ 1] 2074 	jrne	00403$
      008D00 CF 00 BD         [ 2] 2075 	ldw	_c_gap56+0, x
                                   2076 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 651: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
      008D03 CE 00 15         [ 2] 2077 	ldw	x, _g_K+0
      008D06 89               [ 2] 2078 	pushw	x
      008D07 AE 00 05         [ 2] 2079 	ldw	x, #0x0005
      008D0A CD 9A 4E         [ 4] 2080 	call	___muluint2ulong
      008D0D 5B 02            [ 2] 2081 	addw	sp, #2
      008D0F A6 0B            [ 1] 2082 	ld	a, #0x0b
      008D11                       2083 00405$:
      008D11 90 54            [ 2] 2084 	srlw	y
      008D13 56               [ 2] 2085 	rrcw	x
      008D14 4A               [ 1] 2086 	dec	a
      008D15 26 FA            [ 1] 2087 	jrne	00405$
      008D17 CF 00 BF         [ 2] 2088 	ldw	_c_gap56+2, x
                                   2089 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: for (f = 0; f < 2; f++) {
      008D1A 0F 15            [ 1] 2090 	clr	(0x15, sp)
      008D1C                       2091 00138$:
                                   2092 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
      008D1C 5F               [ 1] 2093 	clrw	x
      008D1D 7B 15            [ 1] 2094 	ld	a, (0x15, sp)
      008D1F 97               [ 1] 2095 	ld	xl, a
      008D20 58               [ 2] 2096 	sllw	x
      008D21 1F 11            [ 2] 2097 	ldw	(0x11, sp), x
      008D23 90 93            [ 1] 2098 	ldw	y, x
      008D25 72 A9 00 B9      [ 2] 2099 	addw	y, #(_c_c0+0)
      008D29 1E 11            [ 2] 2100 	ldw	x, (0x11, sp)
      008D2B DE 00 BD         [ 2] 2101 	ldw	x, (_c_gap56+0, x)
      008D2E 1F 13            [ 2] 2102 	ldw	(0x13, sp), x
      008D30 AE 01 CE         [ 2] 2103 	ldw	x, #0x01ce
      008D33 72 F0 13         [ 2] 2104 	subw	x, (0x13, sp)
      008D36 57               [ 2] 2105 	sraw	x
      008D37 90 FF            [ 2] 2106 	ldw	(y), x
                                   2107 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 655: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
      008D39 7B 15            [ 1] 2108 	ld	a, (0x15, sp)
      008D3B 97               [ 1] 2109 	ld	xl, a
      008D3C A6 40            [ 1] 2110 	ld	a, #0x40
      008D3E 42               [ 4] 2111 	mul	x, a
      008D3F 1C 00 29         [ 2] 2112 	addw	x, #(_c_hist+0)
      008D42 1F 13            [ 2] 2113 	ldw	(0x13, sp), x
      008D44 4F               [ 1] 2114 	clr	a
      008D45                       2115 00136$:
      008D45 5F               [ 1] 2116 	clrw	x
      008D46 97               [ 1] 2117 	ld	xl, a
      008D47 72 FB 13         [ 2] 2118 	addw	x, (0x13, sp)
      008D4A 7F               [ 1] 2119 	clr	(x)
      008D4B 4C               [ 1] 2120 	inc	a
      008D4C A1 40            [ 1] 2121 	cp	a, #0x40
      008D4E 25 F5            [ 1] 2122 	jrc	00136$
                                   2123 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 656: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
      008D50 1E 11            [ 2] 2124 	ldw	x, (0x11, sp)
      008D52 1C 00 A9         [ 2] 2125 	addw	x, #(_c_labx0+0)
      008D55 6F 01            [ 1] 2126 	clr	(0x1, x)
      008D57 A6 C0            [ 1] 2127 	ld	a, #0xc0
      008D59 F7               [ 1] 2128 	ld	(x), a
      008D5A 1E 11            [ 2] 2129 	ldw	x, (0x11, sp)
      008D5C 1C 00 B1         [ 2] 2130 	addw	x, #(_c_labx0b+0)
      008D5F 6F 01            [ 1] 2131 	clr	(0x1, x)
      008D61 A6 C0            [ 1] 2132 	ld	a, #0xc0
      008D63 F7               [ 1] 2133 	ld	(x), a
                                   2134 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 657: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
      008D64 1E 11            [ 2] 2135 	ldw	x, (0x11, sp)
      008D66 90 AE 3F FF      [ 2] 2136 	ldw	y, #0x3fff
      008D6A DF 00 AD         [ 2] 2137 	ldw	((_c_labx1+0), x), y
      008D6D 1E 11            [ 2] 2138 	ldw	x, (0x11, sp)
      008D6F 90 AE 3F FF      [ 2] 2139 	ldw	y, #0x3fff
      008D73 DF 00 B5         [ 2] 2140 	ldw	((_c_labx1b+0), x), y
                                   2141 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: for (f = 0; f < 2; f++) {
      008D76 0C 15            [ 1] 2142 	inc	(0x15, sp)
      008D78 7B 15            [ 1] 2143 	ld	a, (0x15, sp)
      008D7A A1 02            [ 1] 2144 	cp	a, #0x02
      008D7C 25 9E            [ 1] 2145 	jrc	00138$
                                   2146 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 659: ss_init();
      008D7E CD 84 FB         [ 4] 2147 	call	_ss_init
                                   2148 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 660: while (ss_next(&sg)) {
      008D81                       2149 00112$:
      008D81 96               [ 1] 2150 	ldw	x, sp
      008D82 5C               [ 1] 2151 	incw	x
      008D83 CD 85 3D         [ 4] 2152 	call	_ss_next
      008D86 6B 15            [ 1] 2153 	ld	(0x15, sp), a
      008D88 26 03            [ 1] 2154 	jrne	00409$
      008D8A CC 8E 16         [ 2] 2155 	jp	00114$
      008D8D                       2156 00409$:
                                   2157 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 662: uint8_t known_all = 1;
      008D8D A6 01            [ 1] 2158 	ld	a, #0x01
      008D8F 6B 11            [ 1] 2159 	ld	(0x11, sp), a
                                   2160 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 664: cal_cloud(sg.u, sg.fam);
      008D91 7B 09            [ 1] 2161 	ld	a, (0x09, sp)
      008D93 1E 05            [ 2] 2162 	ldw	x, (0x05, sp)
      008D95 CD 88 BD         [ 4] 2163 	call	_cal_cloud
                                   2164 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 665: if (sg.k1 > NB) continue;
      008D98 1E 03            [ 2] 2165 	ldw	x, (0x03, sp)
      008D9A A3 00 C0         [ 2] 2166 	cpw	x, #0x00c0
      008D9D 22 E2            [ 1] 2167 	jrugt	00112$
                                   2168 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 666: e = (sg.k1 < NB) ? sg.k1 : NB;
      008D9F A3 00 C0         [ 2] 2169 	cpw	x, #0x00c0
      008DA2 24 04            [ 1] 2170 	jrnc	00146$
      008DA4 1F 14            [ 2] 2171 	ldw	(0x14, sp), x
      008DA6 20 05            [ 2] 2172 	jra	00147$
      008DA8                       2173 00146$:
      008DA8 AE 00 C0         [ 2] 2174 	ldw	x, #0x00c0
      008DAB 1F 14            [ 2] 2175 	ldw	(0x14, sp), x
      008DAD                       2176 00147$:
      008DAD 16 14            [ 2] 2177 	ldw	y, (0x14, sp)
      008DAF 17 12            [ 2] 2178 	ldw	(0x12, sp), y
                                   2179 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: for (t = sg.k0; t < e; t++)
      008DB1 96               [ 1] 2180 	ldw	x, sp
      008DB2 5C               [ 1] 2181 	incw	x
      008DB3 1F 0E            [ 2] 2182 	ldw	(0x0e, sp), x
      008DB5 FE               [ 2] 2183 	ldw	x, (x)
      008DB6 1F 14            [ 2] 2184 	ldw	(0x14, sp), x
      008DB8                       2185 00141$:
                                   2186 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 668: if (known_bit(t) < 0) { known_all = 0; break; }
      008DB8 1E 14            [ 2] 2187 	ldw	x, (0x14, sp)
      008DBA 13 12            [ 2] 2188 	cpw	x, (0x12, sp)
      008DBC 24 11            [ 1] 2189 	jrnc	00107$
      008DBE CD 81 37         [ 4] 2190 	call	_known_bit
      008DC1 4D               [ 1] 2191 	tnz	a
      008DC2 2A 04            [ 1] 2192 	jrpl	00142$
      008DC4 0F 11            [ 1] 2193 	clr	(0x11, sp)
      008DC6 20 07            [ 2] 2194 	jra	00107$
      008DC8                       2195 00142$:
                                   2196 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: for (t = sg.k0; t < e; t++)
      008DC8 1E 14            [ 2] 2197 	ldw	x, (0x14, sp)
      008DCA 5C               [ 1] 2198 	incw	x
      008DCB 1F 14            [ 2] 2199 	ldw	(0x14, sp), x
      008DCD 20 E9            [ 2] 2200 	jra	00141$
      008DCF                       2201 00107$:
                                   2202 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: if (!known_all) continue;
      008DCF 0D 11            [ 1] 2203 	tnz	(0x11, sp)
      008DD1 27 AE            [ 1] 2204 	jreq	00112$
                                   2205 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 670: a_bounds(sg.k0, sg.k1, &amin, &amax);
      008DD3 16 03            [ 2] 2206 	ldw	y, (0x03, sp)
      008DD5 1E 0E            [ 2] 2207 	ldw	x, (0x0e, sp)
      008DD7 FE               [ 2] 2208 	ldw	x, (x)
      008DD8 1F 14            [ 2] 2209 	ldw	(0x14, sp), x
      008DDA 96               [ 1] 2210 	ldw	x, sp
      008DDB 1C 00 0C         [ 2] 2211 	addw	x, #12
      008DDE 89               [ 2] 2212 	pushw	x
      008DDF 96               [ 1] 2213 	ldw	x, sp
      008DE0 1C 00 0C         [ 2] 2214 	addw	x, #12
      008DE3 89               [ 2] 2215 	pushw	x
      008DE4 90 89            [ 2] 2216 	pushw	y
      008DE6 1E 1A            [ 2] 2217 	ldw	x, (0x1a, sp)
      008DE8 CD 87 77         [ 4] 2218 	call	_a_bounds
                                   2219 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 671: if (amin == amax)
      008DEB 1E 0A            [ 2] 2220 	ldw	x, (0x0a, sp)
      008DED 13 0C            [ 2] 2221 	cpw	x, (0x0c, sp)
      008DEF 26 90            [ 1] 2222 	jrne	00112$
                                   2223 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 672: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
      008DF1 7B 09            [ 1] 2224 	ld	a, (0x09, sp)
      008DF3 16 07            [ 2] 2225 	ldw	y, (0x07, sp)
      008DF5 17 10            [ 2] 2226 	ldw	(0x10, sp), y
      008DF7 16 05            [ 2] 2227 	ldw	y, (0x05, sp)
      008DF9 17 12            [ 2] 2228 	ldw	(0x12, sp), y
      008DFB 16 03            [ 2] 2229 	ldw	y, (0x03, sp)
      008DFD 1E 0E            [ 2] 2230 	ldw	x, (0x0e, sp)
      008DFF FE               [ 2] 2231 	ldw	x, (x)
      008E00 1F 14            [ 2] 2232 	ldw	(0x14, sp), x
      008E02 1E 0A            [ 2] 2233 	ldw	x, (0x0a, sp)
      008E04 89               [ 2] 2234 	pushw	x
      008E05 88               [ 1] 2235 	push	a
      008E06 1E 13            [ 2] 2236 	ldw	x, (0x13, sp)
      008E08 89               [ 2] 2237 	pushw	x
      008E09 1E 17            [ 2] 2238 	ldw	x, (0x17, sp)
      008E0B 89               [ 2] 2239 	pushw	x
      008E0C 90 89            [ 2] 2240 	pushw	y
      008E0E 1E 1D            [ 2] 2241 	ldw	x, (0x1d, sp)
      008E10 CD 89 04         [ 4] 2242 	call	_cal_add
      008E13 CC 8D 81         [ 2] 2243 	jp	00112$
      008E16                       2244 00114$:
                                   2245 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 676: int16_t h0 = H0P, h1 = H1P;
      008E16 AE 00 9A         [ 2] 2246 	ldw	x, #0x009a
      008E19 1F 10            [ 2] 2247 	ldw	(0x10, sp), x
      008E1B AE 01 34         [ 2] 2248 	ldw	x, #0x0134
      008E1E 1F 12            [ 2] 2249 	ldw	(0x12, sp), x
                                   2250 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 677: if (c_n0 >= LAB_MIN) {
      008E20 C6 00 21         [ 1] 2251 	ld	a, _c_n0+0
      008E23 A1 03            [ 1] 2252 	cp	a, #0x03
      008E25 25 3E            [ 1] 2253 	jrc	00119$
                                   2254 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 678: int16_t h = (c_lo0 > c_hi0) ? (int16_t)((c_lo0 + c_hi0) >> 1)
      008E27 CE 00 1B         [ 2] 2255 	ldw	x, _c_hi0+0
      008E2A C3 00 19         [ 2] 2256 	cpw	x, _c_lo0+0
      008E2D 2E 0A            [ 1] 2257 	jrsge	00148$
      008E2F CE 00 19         [ 2] 2258 	ldw	x, _c_lo0+0
      008E32 72 BB 00 1B      [ 2] 2259 	addw	x, _c_hi0+0
      008E36 57               [ 2] 2260 	sraw	x
      008E37 20 1E            [ 2] 2261 	jra	00149$
      008E39                       2262 00148$:
      008E39 CE 00 19         [ 2] 2263 	ldw	x, _c_lo0+0
      008E3C A3 00 9A         [ 2] 2264 	cpw	x, #0x009a
      008E3F 2C 16            [ 1] 2265 	jrsgt	00151$
      008E41 CE 00 1B         [ 2] 2266 	ldw	x, _c_hi0+0
      008E44 A3 00 9A         [ 2] 2267 	cpw	x, #0x009a
      008E47 2E 07            [ 1] 2268 	jrsge	00152$
      008E49 CE 00 1B         [ 2] 2269 	ldw	x, _c_hi0+0
      008E4C 1F 14            [ 2] 2270 	ldw	(0x14, sp), x
      008E4E 20 05            [ 2] 2271 	jra	00153$
      008E50                       2272 00152$:
      008E50 AE 00 9A         [ 2] 2273 	ldw	x, #0x009a
      008E53 1F 14            [ 2] 2274 	ldw	(0x14, sp), x
      008E55                       2275 00153$:
      008E55 1E 14            [ 2] 2276 	ldw	x, (0x14, sp)
      008E57                       2277 00151$:
      008E57                       2278 00149$:
                                   2279 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 680: if (h >= H0_LO && h <= H0_HI) h0 = h;
      008E57 90 93            [ 1] 2280 	ldw	y, x
      008E59 A3 00 70         [ 2] 2281 	cpw	x, #0x0070
      008E5C 2F 07            [ 1] 2282 	jrslt	00119$
      008E5E A3 00 C0         [ 2] 2283 	cpw	x, #0x00c0
      008E61 2C 02            [ 1] 2284 	jrsgt	00119$
      008E63 17 10            [ 2] 2285 	ldw	(0x10, sp), y
      008E65                       2286 00119$:
                                   2287 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 682: if (c_n1 >= LAB_MIN) {
      008E65 C6 00 22         [ 1] 2288 	ld	a, _c_n1+0
      008E68 A1 03            [ 1] 2289 	cp	a, #0x03
      008E6A 25 3E            [ 1] 2290 	jrc	00124$
                                   2291 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: int16_t h = (c_lo1 > c_hi1) ? (int16_t)((c_lo1 + c_hi1) >> 1)
      008E6C CE 00 1F         [ 2] 2292 	ldw	x, _c_hi1+0
      008E6F C3 00 1D         [ 2] 2293 	cpw	x, _c_lo1+0
      008E72 2E 0A            [ 1] 2294 	jrsge	00154$
      008E74 CE 00 1D         [ 2] 2295 	ldw	x, _c_lo1+0
      008E77 72 BB 00 1F      [ 2] 2296 	addw	x, _c_hi1+0
      008E7B 57               [ 2] 2297 	sraw	x
      008E7C 20 1E            [ 2] 2298 	jra	00155$
      008E7E                       2299 00154$:
      008E7E CE 00 1D         [ 2] 2300 	ldw	x, _c_lo1+0
      008E81 A3 01 34         [ 2] 2301 	cpw	x, #0x0134
      008E84 2C 16            [ 1] 2302 	jrsgt	00157$
      008E86 CE 00 1F         [ 2] 2303 	ldw	x, _c_hi1+0
      008E89 A3 01 34         [ 2] 2304 	cpw	x, #0x0134
      008E8C 2E 07            [ 1] 2305 	jrsge	00158$
      008E8E CE 00 1F         [ 2] 2306 	ldw	x, _c_hi1+0
      008E91 1F 14            [ 2] 2307 	ldw	(0x14, sp), x
      008E93 20 05            [ 2] 2308 	jra	00159$
      008E95                       2309 00158$:
      008E95 AE 01 34         [ 2] 2310 	ldw	x, #0x0134
      008E98 1F 14            [ 2] 2311 	ldw	(0x14, sp), x
      008E9A                       2312 00159$:
      008E9A 1E 14            [ 2] 2313 	ldw	x, (0x14, sp)
      008E9C                       2314 00157$:
      008E9C                       2315 00155$:
                                   2316 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 685: if (h >= H1_LO && h <= H1_HI) h1 = h;
      008E9C 90 93            [ 1] 2317 	ldw	y, x
      008E9E A3 00 FC         [ 2] 2318 	cpw	x, #0x00fc
      008EA1 2F 07            [ 1] 2319 	jrslt	00124$
      008EA3 A3 01 78         [ 2] 2320 	cpw	x, #0x0178
      008EA6 2C 02            [ 1] 2321 	jrsgt	00124$
      008EA8 17 12            [ 2] 2322 	ldw	(0x12, sp), y
      008EAA                       2323 00124$:
                                   2324 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 687: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
      008EAA 1E 12            [ 2] 2325 	ldw	x, (0x12, sp)
      008EAC 72 F0 10         [ 2] 2326 	subw	x, (0x10, sp)
      008EAF A3 00 70         [ 2] 2327 	cpw	x, #0x0070
      008EB2 2F 05            [ 1] 2328 	jrslt	00125$
      008EB4 A3 00 C4         [ 2] 2329 	cpw	x, #0x00c4
      008EB7 2D 0A            [ 1] 2330 	jrsle	00126$
      008EB9                       2331 00125$:
      008EB9 AE 00 9A         [ 2] 2332 	ldw	x, #0x009a
      008EBC 1F 10            [ 2] 2333 	ldw	(0x10, sp), x
      008EBE AE 01 34         [ 2] 2334 	ldw	x, #0x0134
      008EC1 1F 12            [ 2] 2335 	ldw	(0x12, sp), x
      008EC3                       2336 00126$:
                                   2337 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 688: c_h0c = h0; c_h1c = h1;
      008EC3 1E 10            [ 2] 2338 	ldw	x, (0x10, sp)
      008EC5 CF 00 23         [ 2] 2339 	ldw	_c_h0c+0, x
      008EC8 1E 12            [ 2] 2340 	ldw	x, (0x12, sp)
      008ECA CF 00 25         [ 2] 2341 	ldw	_c_h1c+0, x
                                   2342 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: for (f = 0; f < 2; f++) {
      008ECD 0F 15            [ 1] 2343 	clr	(0x15, sp)
      008ECF                       2344 00143$:
                                   2345 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 692: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
      008ECF 96               [ 1] 2346 	ldw	x, sp
      008ED0 1C 00 0C         [ 2] 2347 	addw	x, #12
      008ED3 7B 15            [ 1] 2348 	ld	a, (0x15, sp)
      008ED5 CD 8A 19         [ 4] 2349 	call	_theta56
      008ED8 6B 14            [ 1] 2350 	ld	(0x14, sp), a
      008EDA 5F               [ 1] 2351 	clrw	x
      008EDB 7B 15            [ 1] 2352 	ld	a, (0x15, sp)
      008EDD 97               [ 1] 2353 	ld	xl, a
      008EDE 1C 00 27         [ 2] 2354 	addw	x, #(_c_d56+0)
      008EE1 1F 11            [ 2] 2355 	ldw	(0x11, sp), x
      008EE3 0D 14            [ 1] 2356 	tnz	(0x14, sp)
      008EE5 26 05            [ 1] 2357 	jrne	00129$
      008EE7 1E 11            [ 2] 2358 	ldw	x, (0x11, sp)
      008EE9 7F               [ 1] 2359 	clr	(x)
      008EEA 20 3B            [ 2] 2360 	jra	00134$
      008EEC                       2361 00129$:
                                   2362 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 693: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
      008EEC CE 00 23         [ 2] 2363 	ldw	x, _c_h0c+0
      008EEF 72 BB 00 25      [ 2] 2364 	addw	x, _c_h1c+0
      008EF3 1F 13            [ 2] 2365 	ldw	(0x13, sp), x
      008EF5 5F               [ 1] 2366 	clrw	x
      008EF6 7B 15            [ 1] 2367 	ld	a, (0x15, sp)
      008EF8 97               [ 1] 2368 	ld	xl, a
      008EF9 58               [ 2] 2369 	sllw	x
      008EFA 90 93            [ 1] 2370 	ldw	y, x
      008EFC DE 00 BD         [ 2] 2371 	ldw	x, (_c_gap56+0, x)
      008EFF 50               [ 2] 2372 	negw	x
      008F00 72 FB 13         [ 2] 2373 	addw	x, (0x13, sp)
      008F03 57               [ 2] 2374 	sraw	x
      008F04 1F 13            [ 2] 2375 	ldw	(0x13, sp), x
                                   2376 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 694: delta = (int16_t)(th + c_c0[f] - cfit);
      008F06 93               [ 1] 2377 	ldw	x, y
      008F07 DE 00 B9         [ 2] 2378 	ldw	x, (_c_c0+0, x)
      008F0A 72 FB 0C         [ 2] 2379 	addw	x, (0x0c, sp)
      008F0D 72 F0 13         [ 2] 2380 	subw	x, (0x13, sp)
                                   2381 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 695: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
      008F10 A3 FF E8         [ 2] 2382 	cpw	x, #0xffe8
      008F13 2E 03            [ 1] 2383 	jrsge	00131$
      008F15 AE FF E8         [ 2] 2384 	ldw	x, #0xffe8
      008F18                       2385 00131$:
                                   2386 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 696: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
      008F18 90 93            [ 1] 2387 	ldw	y, x
      008F1A 90 A3 00 18      [ 2] 2388 	cpw	y, #0x0018
      008F1E 2D 03            [ 1] 2389 	jrsle	00133$
      008F20 AE 00 18         [ 2] 2390 	ldw	x, #0x0018
      008F23                       2391 00133$:
                                   2392 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 697: c_d56[f] = (int8_t)delta;
      008F23 9F               [ 1] 2393 	ld	a, xl
      008F24 1E 11            [ 2] 2394 	ldw	x, (0x11, sp)
      008F26 F7               [ 1] 2395 	ld	(x), a
      008F27                       2396 00134$:
                                   2397 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: for (f = 0; f < 2; f++) {
      008F27 0C 15            [ 1] 2398 	inc	(0x15, sp)
      008F29 7B 15            [ 1] 2399 	ld	a, (0x15, sp)
      008F2B A1 02            [ 1] 2400 	cp	a, #0x02
      008F2D 25 A0            [ 1] 2401 	jrc	00143$
                                   2402 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 699: }
      008F2F 5B 15            [ 2] 2403 	addw	sp, #21
      008F31 81               [ 4] 2404 	ret
                                   2405 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 703: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
                                   2406 ;	-----------------------------------------
                                   2407 ;	 function hinge
                                   2408 ;	-----------------------------------------
      008F32                       2409 _hinge:
      008F32 89               [ 2] 2410 	pushw	x
      008F33 51               [ 1] 2411 	exgw	x, y
                                   2412 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 705: int16_t g = 0;
      008F34 5F               [ 1] 2413 	clrw	x
                                   2414 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 706: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
      008F35 72 F2 07         [ 2] 2415 	subw	y, (0x07, sp)
      008F38 90 A3 00 00      [ 2] 2416 	cpw	y, #0x0000
      008F3C 2D 01            [ 1] 2417 	jrsle	00102$
      008F3E 93               [ 1] 2418 	ldw	x, y
      008F3F                       2419 00102$:
                                   2420 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 707: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
      008F3F 16 07            [ 2] 2421 	ldw	y, (0x07, sp)
      008F41 72 F2 05         [ 2] 2422 	subw	y, (0x05, sp)
      008F44 17 01            [ 2] 2423 	ldw	(0x01, sp), y
      008F46 13 01            [ 2] 2424 	cpw	x, (0x01, sp)
      008F48 2E 02            [ 1] 2425 	jrsge	00104$
      008F4A 1E 01            [ 2] 2426 	ldw	x, (0x01, sp)
      008F4C                       2427 00104$:
                                   2428 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 708: return (uint16_t)g;
                                   2429 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 709: }
      008F4C 16 03            [ 2] 2430 	ldw	y, (3, sp)
      008F4E 5B 08            [ 2] 2431 	addw	sp, #8
      008F50 90 FC            [ 2] 2432 	jp	(y)
                                   2433 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 712: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   2434 ;	-----------------------------------------
                                   2435 ;	 function decide
                                   2436 ;	-----------------------------------------
      008F52                       2437 _decide:
      008F52 52 18            [ 2] 2438 	sub	sp, #24
      008F54 1F 15            [ 2] 2439 	ldw	(0x15, sp), x
                                   2440 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 716: int16_t L = (int16_t)(k1 - k0);
      008F56 1E 1B            [ 2] 2441 	ldw	x, (0x1b, sp)
      008F58 72 F0 15         [ 2] 2442 	subw	x, (0x15, sp)
                                   2443 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 717: int16_t acap = (L < A_CAP) ? L : A_CAP;
      008F5B 1F 05            [ 2] 2444 	ldw	(0x05, sp), x
      008F5D A3 00 0F         [ 2] 2445 	cpw	x, #0x000f
      008F60 2F 03            [ 1] 2446 	jrslt	00144$
      008F62 AE 00 0F         [ 2] 2447 	ldw	x, #0x000f
      008F65                       2448 00144$:
      008F65 1F 07            [ 2] 2449 	ldw	(0x07, sp), x
                                   2450 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 718: int16_t h0e = c_h0c, h1e = c_h1c;
      008F67 CE 00 23         [ 2] 2451 	ldw	x, _c_h0c+0
      008F6A 1F 09            [ 2] 2452 	ldw	(0x09, sp), x
      008F6C CE 00 25         [ 2] 2453 	ldw	x, _c_h1c+0
      008F6F 1F 0B            [ 2] 2454 	ldw	(0x0b, sp), x
                                   2455 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 722: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
      008F71 7B 21            [ 1] 2456 	ld	a, (0x21, sp)
      008F73 A1 05            [ 1] 2457 	cp	a, #0x05
      008F75 26 19            [ 1] 2458 	jrne	00102$
      008F77 C6 00 27         [ 1] 2459 	ld	a, _c_d56+0
      008F7A 6B 18            [ 1] 2460 	ld	(0x18, sp), a
      008F7C 49               [ 1] 2461 	rlc	a
      008F7D 4F               [ 1] 2462 	clr	a
      008F7E A2 00            [ 1] 2463 	sbc	a, #0x00
      008F80 6B 17            [ 1] 2464 	ld	(0x17, sp), a
      008F82 1E 09            [ 2] 2465 	ldw	x, (0x09, sp)
      008F84 72 FB 17         [ 2] 2466 	addw	x, (0x17, sp)
      008F87 1F 09            [ 2] 2467 	ldw	(0x09, sp), x
      008F89 1E 0B            [ 2] 2468 	ldw	x, (0x0b, sp)
      008F8B 72 FB 17         [ 2] 2469 	addw	x, (0x17, sp)
      008F8E 1F 0B            [ 2] 2470 	ldw	(0x0b, sp), x
      008F90                       2471 00102$:
                                   2472 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 723: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
      008F90 7B 21            [ 1] 2473 	ld	a, (0x21, sp)
      008F92 A1 06            [ 1] 2474 	cp	a, #0x06
      008F94 26 19            [ 1] 2475 	jrne	00104$
      008F96 C6 00 28         [ 1] 2476 	ld	a, _c_d56+1
      008F99 6B 18            [ 1] 2477 	ld	(0x18, sp), a
      008F9B 49               [ 1] 2478 	rlc	a
      008F9C 4F               [ 1] 2479 	clr	a
      008F9D A2 00            [ 1] 2480 	sbc	a, #0x00
      008F9F 6B 17            [ 1] 2481 	ld	(0x17, sp), a
      008FA1 1E 09            [ 2] 2482 	ldw	x, (0x09, sp)
      008FA3 72 FB 17         [ 2] 2483 	addw	x, (0x17, sp)
      008FA6 1F 09            [ 2] 2484 	ldw	(0x09, sp), x
      008FA8 1E 0B            [ 2] 2485 	ldw	x, (0x0b, sp)
      008FAA 72 FB 17         [ 2] 2486 	addw	x, (0x17, sp)
      008FAD 1F 0B            [ 2] 2487 	ldw	(0x0b, sp), x
      008FAF                       2488 00104$:
                                   2489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 724: d_inter = 0;
      008FAF 5F               [ 1] 2490 	clrw	x
      008FB0 CF 00 FF         [ 2] 2491 	ldw	_d_inter+0, x
                                   2492 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: for (a = 0; a <= acap; a++) {
      008FB3 1E 1D            [ 2] 2493 	ldw	x, (0x1d, sp)
      008FB5 13 09            [ 2] 2494 	cpw	x, (0x09, sp)
      008FB7 2F 04            [ 1] 2495 	jrslt	00373$
      008FB9 0F 0D            [ 1] 2496 	clr	(0x0d, sp)
      008FBB 20 04            [ 2] 2497 	jra	00374$
      008FBD                       2498 00373$:
      008FBD A6 01            [ 1] 2499 	ld	a, #0x01
      008FBF 6B 0D            [ 1] 2500 	ld	(0x0d, sp), a
      008FC1                       2501 00374$:
      008FC1 1E 09            [ 2] 2502 	ldw	x, (0x09, sp)
      008FC3 13 1F            [ 2] 2503 	cpw	x, (0x1f, sp)
      008FC5 2C 04            [ 1] 2504 	jrsgt	00375$
      008FC7 0F 0E            [ 1] 2505 	clr	(0x0e, sp)
      008FC9 20 04            [ 2] 2506 	jra	00376$
      008FCB                       2507 00375$:
      008FCB A6 01            [ 1] 2508 	ld	a, #0x01
      008FCD 6B 0E            [ 1] 2509 	ld	(0x0e, sp), a
      008FCF                       2510 00376$:
      008FCF 5F               [ 1] 2511 	clrw	x
      008FD0 1F 17            [ 2] 2512 	ldw	(0x17, sp), x
      008FD2                       2513 00133$:
      008FD2 1E 17            [ 2] 2514 	ldw	x, (0x17, sp)
      008FD4 13 07            [ 2] 2515 	cpw	x, (0x07, sp)
      008FD6 2D 03            [ 1] 2516 	jrsle	00377$
      008FD8 CC 90 81         [ 2] 2517 	jp	00117$
      008FDB                       2518 00377$:
                                   2519 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 728: if (a == 0) {
      008FDB 1E 17            [ 2] 2520 	ldw	x, (0x17, sp)
      008FDD 26 1C            [ 1] 2521 	jrne	00113$
                                   2522 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 729: c = hinge(u, v, h0e);
      008FDF 1E 09            [ 2] 2523 	ldw	x, (0x09, sp)
      008FE1 89               [ 2] 2524 	pushw	x
      008FE2 1E 21            [ 2] 2525 	ldw	x, (0x21, sp)
      008FE4 89               [ 2] 2526 	pushw	x
      008FE5 1E 21            [ 2] 2527 	ldw	x, (0x21, sp)
      008FE7 CD 8F 32         [ 4] 2528 	call	_hinge
      008FEA 1F 0F            [ 2] 2529 	ldw	(0x0f, sp), x
                                   2530 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 730: it = (u < h0e && h0e <= v);
      008FEC 0D 0D            [ 1] 2531 	tnz	(0x0d, sp)
      008FEE 27 04            [ 1] 2532 	jreq	00145$
      008FF0 0D 0E            [ 1] 2533 	tnz	(0x0e, sp)
      008FF2 27 03            [ 1] 2534 	jreq	00146$
      008FF4                       2535 00145$:
      008FF4 4F               [ 1] 2536 	clr	a
      008FF5 20 61            [ 2] 2537 	jra	00114$
      008FF7                       2538 00146$:
      008FF7 A6 01            [ 1] 2539 	ld	a, #0x01
      008FF9 20 5D            [ 2] 2540 	jra	00114$
      008FFB                       2541 00113$:
                                   2542 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
      008FFB 16 17            [ 2] 2543 	ldw	y, (0x17, sp)
      008FFD 17 11            [ 2] 2544 	ldw	(0x11, sp), y
      008FFF 93               [ 1] 2545 	ldw	x, y
      009000 5A               [ 2] 2546 	decw	x
      009001 4F               [ 1] 2547 	clr	a
      009002 02               [ 1] 2548 	rlwa	x
      009003 58               [ 2] 2549 	sllw	x
      009004 72 FB 0B         [ 2] 2550 	addw	x, (0x0b, sp)
                                   2551 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 733: c = hinge(u, v, h);
      009007 1F 13            [ 2] 2552 	ldw	(0x13, sp), x
      009009 89               [ 2] 2553 	pushw	x
      00900A 1E 21            [ 2] 2554 	ldw	x, (0x21, sp)
      00900C 89               [ 2] 2555 	pushw	x
      00900D 1E 21            [ 2] 2556 	ldw	x, (0x21, sp)
      00900F CD 8F 32         [ 4] 2557 	call	_hinge
      009012 1F 0F            [ 2] 2558 	ldw	(0x0f, sp), x
                                   2559 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 734: it = (u < h && h <= v);
      009014 1E 1D            [ 2] 2560 	ldw	x, (0x1d, sp)
      009016 13 13            [ 2] 2561 	cpw	x, (0x13, sp)
      009018 2E 06            [ 1] 2562 	jrsge	00148$
      00901A 1E 13            [ 2] 2563 	ldw	x, (0x13, sp)
      00901C 13 1F            [ 2] 2564 	cpw	x, (0x1f, sp)
      00901E 2D 02            [ 1] 2565 	jrsle	00149$
      009020                       2566 00148$:
      009020 4F               [ 1] 2567 	clr	a
      009021 C5                    2568 	.byte 0xc5
      009022                       2569 00149$:
      009022 A6 01            [ 1] 2570 	ld	a, #0x01
      009024                       2571 00150$:
                                   2572 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 735: if (a < L) {
      009024 1E 17            [ 2] 2573 	ldw	x, (0x17, sp)
      009026 13 05            [ 2] 2574 	cpw	x, (0x05, sp)
      009028 2E 2E            [ 1] 2575 	jrsge	00114$
                                   2576 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 736: int16_t h2 = (int16_t)(a * BIT_U + h0e);
      00902A 02               [ 1] 2577 	rlwa	x
      00902B 7B 12            [ 1] 2578 	ld	a, (0x12, sp)
      00902D 01               [ 1] 2579 	rrwa	x
      00902E 41               [ 1] 2580 	exg	a, xl
      00902F 4F               [ 1] 2581 	clr	a
      009030 41               [ 1] 2582 	exg	a, xl
      009031 58               [ 2] 2583 	sllw	x
      009032 72 FB 09         [ 2] 2584 	addw	x, (0x09, sp)
      009035 1F 13            [ 2] 2585 	ldw	(0x13, sp), x
                                   2586 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 737: uint16_t c2 = hinge(u, v, h2);
      009037 88               [ 1] 2587 	push	a
      009038 1E 14            [ 2] 2588 	ldw	x, (0x14, sp)
      00903A 89               [ 2] 2589 	pushw	x
      00903B 1E 22            [ 2] 2590 	ldw	x, (0x22, sp)
      00903D 89               [ 2] 2591 	pushw	x
      00903E 1E 22            [ 2] 2592 	ldw	x, (0x22, sp)
      009040 CD 8F 32         [ 4] 2593 	call	_hinge
      009043 84               [ 1] 2594 	pop	a
                                   2595 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 738: if (c2 < c) c = c2;
      009044 13 0F            [ 2] 2596 	cpw	x, (0x0f, sp)
      009046 24 02            [ 1] 2597 	jrnc	00106$
      009048 1F 0F            [ 2] 2598 	ldw	(0x0f, sp), x
      00904A                       2599 00106$:
                                   2600 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 739: if (u < h2 && h2 <= v) it = 1;
      00904A 1E 1D            [ 2] 2601 	ldw	x, (0x1d, sp)
      00904C 13 13            [ 2] 2602 	cpw	x, (0x13, sp)
      00904E 2E 08            [ 1] 2603 	jrsge	00114$
      009050 1E 13            [ 2] 2604 	ldw	x, (0x13, sp)
      009052 13 1F            [ 2] 2605 	cpw	x, (0x1f, sp)
      009054 2C 02            [ 1] 2606 	jrsgt	00114$
      009056 A6 01            [ 1] 2607 	ld	a, #0x01
      009058                       2608 00114$:
                                   2609 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 742: d_costs[a] = c;
      009058 1E 17            [ 2] 2610 	ldw	x, (0x17, sp)
      00905A 58               [ 2] 2611 	sllw	x
      00905B 16 0F            [ 2] 2612 	ldw	y, (0x0f, sp)
      00905D DF 00 DF         [ 2] 2613 	ldw	((_d_costs+0), x), y
                                   2614 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 743: if (it) d_inter |= (uint16_t)(1u << a);
      009060 4D               [ 1] 2615 	tnz	a
      009061 27 16            [ 1] 2616 	jreq	00134$
      009063 5F               [ 1] 2617 	clrw	x
      009064 5C               [ 1] 2618 	incw	x
      009065 7B 18            [ 1] 2619 	ld	a, (0x18, sp)
      009067 27 04            [ 1] 2620 	jreq	00389$
      009069                       2621 00388$:
      009069 58               [ 2] 2622 	sllw	x
      00906A 4A               [ 1] 2623 	dec	a
      00906B 26 FC            [ 1] 2624 	jrne	00388$
      00906D                       2625 00389$:
      00906D 9F               [ 1] 2626 	ld	a, xl
      00906E CA 01 00         [ 1] 2627 	or	a, _d_inter+1
      009071 02               [ 1] 2628 	rlwa	x
      009072 CA 00 FF         [ 1] 2629 	or	a, _d_inter+0
      009075 95               [ 1] 2630 	ld	xh, a
      009076 CF 00 FF         [ 2] 2631 	ldw	_d_inter+0, x
      009079                       2632 00134$:
                                   2633 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: for (a = 0; a <= acap; a++) {
      009079 1E 17            [ 2] 2634 	ldw	x, (0x17, sp)
      00907B 5C               [ 1] 2635 	incw	x
      00907C 1F 17            [ 2] 2636 	ldw	(0x17, sp), x
      00907E CC 8F D2         [ 2] 2637 	jp	00133$
      009081                       2638 00117$:
                                   2639 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 746: bc = 0xFFFF; bi = 1; *a_free = 0;
      009081 5F               [ 1] 2640 	clrw	x
      009082 5A               [ 2] 2641 	decw	x
      009083 1F 10            [ 2] 2642 	ldw	(0x10, sp), x
      009085 A6 01            [ 1] 2643 	ld	a, #0x01
      009087 6B 12            [ 1] 2644 	ld	(0x12, sp), a
      009089 16 24            [ 2] 2645 	ldw	y, (0x24, sp)
      00908B 17 13            [ 2] 2646 	ldw	(0x13, sp), y
      00908D 93               [ 1] 2647 	ldw	x, y
      00908E 6F 01            [ 1] 2648 	clr	(0x1, x)
      009090 7F               [ 1] 2649 	clr	(x)
                                   2650 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 747: for (a = 0; a <= acap; a++) {
      009091 5F               [ 1] 2651 	clrw	x
      009092 1F 17            [ 2] 2652 	ldw	(0x17, sp), x
      009094                       2653 00136$:
      009094 1E 17            [ 2] 2654 	ldw	x, (0x17, sp)
      009096 13 07            [ 2] 2655 	cpw	x, (0x07, sp)
      009098 2C 33            [ 1] 2656 	jrsgt	00123$
                                   2657 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 748: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      00909A CE 00 FF         [ 2] 2658 	ldw	x, _d_inter+0
      00909D 7B 18            [ 1] 2659 	ld	a, (0x18, sp)
      00909F 27 04            [ 1] 2660 	jreq	00393$
      0090A1                       2661 00392$:
      0090A1 54               [ 2] 2662 	srlw	x
      0090A2 4A               [ 1] 2663 	dec	a
      0090A3 26 FC            [ 1] 2664 	jrne	00392$
      0090A5                       2665 00393$:
      0090A5 9F               [ 1] 2666 	ld	a, xl
      0090A6 A4 01            [ 1] 2667 	and	a, #0x01
                                   2668 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 749: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      0090A8 1E 17            [ 2] 2669 	ldw	x, (0x17, sp)
      0090AA 58               [ 2] 2670 	sllw	x
      0090AB DE 00 DF         [ 2] 2671 	ldw	x, (_d_costs+0, x)
      0090AE 13 10            [ 2] 2672 	cpw	x, (0x10, sp)
      0090B0 25 0B            [ 1] 2673 	jrc	00118$
      0090B2 13 10            [ 2] 2674 	cpw	x, (0x10, sp)
      0090B4 26 10            [ 1] 2675 	jrne	00137$
      0090B6 4D               [ 1] 2676 	tnz	a
      0090B7 27 0D            [ 1] 2677 	jreq	00137$
      0090B9 0D 12            [ 1] 2678 	tnz	(0x12, sp)
      0090BB 26 09            [ 1] 2679 	jrne	00137$
      0090BD                       2680 00118$:
                                   2681 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 750: bc = d_costs[a]; bi = it; *a_free = a;
      0090BD 1F 10            [ 2] 2682 	ldw	(0x10, sp), x
      0090BF 6B 12            [ 1] 2683 	ld	(0x12, sp), a
      0090C1 1E 13            [ 2] 2684 	ldw	x, (0x13, sp)
      0090C3 16 17            [ 2] 2685 	ldw	y, (0x17, sp)
      0090C5 FF               [ 2] 2686 	ldw	(x), y
      0090C6                       2687 00137$:
                                   2688 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 747: for (a = 0; a <= acap; a++) {
      0090C6 1E 17            [ 2] 2689 	ldw	x, (0x17, sp)
      0090C8 5C               [ 1] 2690 	incw	x
      0090C9 1F 17            [ 2] 2691 	ldw	(0x17, sp), x
      0090CB 20 C7            [ 2] 2692 	jra	00136$
      0090CD                       2693 00123$:
                                   2694 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 753: a_bounds(k0, k1, &amin, &amax);
      0090CD 96               [ 1] 2695 	ldw	x, sp
      0090CE 1C 00 03         [ 2] 2696 	addw	x, #3
      0090D1 89               [ 2] 2697 	pushw	x
      0090D2 96               [ 1] 2698 	ldw	x, sp
      0090D3 1C 00 03         [ 2] 2699 	addw	x, #3
      0090D6 89               [ 2] 2700 	pushw	x
      0090D7 1E 1F            [ 2] 2701 	ldw	x, (0x1f, sp)
      0090D9 89               [ 2] 2702 	pushw	x
      0090DA 1E 1B            [ 2] 2703 	ldw	x, (0x1b, sp)
      0090DC CD 87 77         [ 4] 2704 	call	_a_bounds
                                   2705 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 754: lo = (amin > 0) ? amin : 0;
      0090DF 1E 01            [ 2] 2706 	ldw	x, (0x01, sp)
      0090E1 A3 00 00         [ 2] 2707 	cpw	x, #0x0000
      0090E4 2C 01            [ 1] 2708 	jrsgt	00152$
      0090E6 5F               [ 1] 2709 	clrw	x
      0090E7                       2710 00152$:
      0090E7 1F 0C            [ 2] 2711 	ldw	(0x0c, sp), x
                                   2712 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 755: hi = (amax < acap) ? amax : acap;
      0090E9 1E 03            [ 2] 2713 	ldw	x, (0x03, sp)
      0090EB 13 07            [ 2] 2714 	cpw	x, (0x07, sp)
      0090ED 2E 03            [ 1] 2715 	jrsge	00153$
      0090EF 1E 03            [ 2] 2716 	ldw	x, (0x03, sp)
      0090F1 C5                    2717 	.byte 0xc5
      0090F2                       2718 00153$:
      0090F2 1E 07            [ 2] 2719 	ldw	x, (0x07, sp)
      0090F4                       2720 00154$:
      0090F4 1F 0E            [ 2] 2721 	ldw	(0x0e, sp), x
                                   2722 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 756: if (lo > hi) { lo = 0; hi = acap; }
      0090F6 1E 0C            [ 2] 2723 	ldw	x, (0x0c, sp)
      0090F8 13 0E            [ 2] 2724 	cpw	x, (0x0e, sp)
      0090FA 2D 07            [ 1] 2725 	jrsle	00125$
      0090FC 5F               [ 1] 2726 	clrw	x
      0090FD 1F 0C            [ 2] 2727 	ldw	(0x0c, sp), x
      0090FF 16 07            [ 2] 2728 	ldw	y, (0x07, sp)
      009101 17 0E            [ 2] 2729 	ldw	(0x0e, sp), y
      009103                       2730 00125$:
                                   2731 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 757: bc = 0xFFFF; bi = 1; *a_hat = lo;
      009103 5F               [ 1] 2732 	clrw	x
      009104 5A               [ 2] 2733 	decw	x
      009105 1F 10            [ 2] 2734 	ldw	(0x10, sp), x
      009107 A6 01            [ 1] 2735 	ld	a, #0x01
      009109 6B 12            [ 1] 2736 	ld	(0x12, sp), a
      00910B 16 22            [ 2] 2737 	ldw	y, (0x22, sp)
      00910D 17 13            [ 2] 2738 	ldw	(0x13, sp), y
      00910F 93               [ 1] 2739 	ldw	x, y
      009110 16 0C            [ 2] 2740 	ldw	y, (0x0c, sp)
      009112 FF               [ 2] 2741 	ldw	(x), y
                                   2742 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: for (a = lo; a <= hi; a++) {
      009113 16 0C            [ 2] 2743 	ldw	y, (0x0c, sp)
      009115 17 17            [ 2] 2744 	ldw	(0x17, sp), y
      009117                       2745 00139$:
      009117 1E 17            [ 2] 2746 	ldw	x, (0x17, sp)
      009119 13 0E            [ 2] 2747 	cpw	x, (0x0e, sp)
      00911B 2C 33            [ 1] 2748 	jrsgt	00131$
                                   2749 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 759: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      00911D CE 00 FF         [ 2] 2750 	ldw	x, _d_inter+0
      009120 7B 18            [ 1] 2751 	ld	a, (0x18, sp)
      009122 27 04            [ 1] 2752 	jreq	00406$
      009124                       2753 00405$:
      009124 54               [ 2] 2754 	srlw	x
      009125 4A               [ 1] 2755 	dec	a
      009126 26 FC            [ 1] 2756 	jrne	00405$
      009128                       2757 00406$:
      009128 9F               [ 1] 2758 	ld	a, xl
      009129 A4 01            [ 1] 2759 	and	a, #0x01
                                   2760 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 760: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      00912B 1E 17            [ 2] 2761 	ldw	x, (0x17, sp)
      00912D 58               [ 2] 2762 	sllw	x
      00912E DE 00 DF         [ 2] 2763 	ldw	x, (_d_costs+0, x)
      009131 13 10            [ 2] 2764 	cpw	x, (0x10, sp)
      009133 25 0B            [ 1] 2765 	jrc	00126$
      009135 13 10            [ 2] 2766 	cpw	x, (0x10, sp)
      009137 26 10            [ 1] 2767 	jrne	00140$
      009139 4D               [ 1] 2768 	tnz	a
      00913A 27 0D            [ 1] 2769 	jreq	00140$
      00913C 0D 12            [ 1] 2770 	tnz	(0x12, sp)
      00913E 26 09            [ 1] 2771 	jrne	00140$
      009140                       2772 00126$:
                                   2773 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 761: bc = d_costs[a]; bi = it; *a_hat = a;
      009140 1F 10            [ 2] 2774 	ldw	(0x10, sp), x
      009142 6B 12            [ 1] 2775 	ld	(0x12, sp), a
      009144 1E 13            [ 2] 2776 	ldw	x, (0x13, sp)
      009146 16 17            [ 2] 2777 	ldw	y, (0x17, sp)
      009148 FF               [ 2] 2778 	ldw	(x), y
      009149                       2779 00140$:
                                   2780 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: for (a = lo; a <= hi; a++) {
      009149 1E 17            [ 2] 2781 	ldw	x, (0x17, sp)
      00914B 5C               [ 1] 2782 	incw	x
      00914C 1F 17            [ 2] 2783 	ldw	(0x17, sp), x
      00914E 20 C7            [ 2] 2784 	jra	00139$
      009150                       2785 00131$:
                                   2786 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 764: *lo_out = lo; *hi_out = hi;
      009150 1E 26            [ 2] 2787 	ldw	x, (0x26, sp)
      009152 16 0C            [ 2] 2788 	ldw	y, (0x0c, sp)
      009154 FF               [ 2] 2789 	ldw	(x), y
      009155 1E 28            [ 2] 2790 	ldw	x, (0x28, sp)
      009157 16 0E            [ 2] 2791 	ldw	y, (0x0e, sp)
      009159 FF               [ 2] 2792 	ldw	(x), y
                                   2793 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 765: return acap;
      00915A 1E 07            [ 2] 2794 	ldw	x, (0x07, sp)
                                   2795 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 766: }
      00915C 16 19            [ 2] 2796 	ldw	y, (25, sp)
      00915E 5B 29            [ 2] 2797 	addw	sp, #41
      009160 90 FC            [ 2] 2798 	jp	(y)
                                   2799 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 769: static void cand_insert(uint16_t k, uint8_t m)
                                   2800 ;	-----------------------------------------
                                   2801 ;	 function cand_insert
                                   2802 ;	-----------------------------------------
      009162                       2803 _cand_insert:
      009162 52 07            [ 2] 2804 	sub	sp, #7
      009164 1F 05            [ 2] 2805 	ldw	(0x05, sp), x
      009166 6B 04            [ 1] 2806 	ld	(0x04, sp), a
                                   2807 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 771: uint8_t i = v_ncand, j;
      009168 C6 01 10         [ 1] 2808 	ld	a, _v_ncand+0
                                   2809 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 772: while (i > 0 && v_cand_m[i - 1] > m) i--;
      00916B 6B 03            [ 1] 2810 	ld	(0x03, sp), a
      00916D 6B 07            [ 1] 2811 	ld	(0x07, sp), a
      00916F                       2812 00102$:
      00916F 0D 07            [ 1] 2813 	tnz	(0x07, sp)
      009171 27 14            [ 1] 2814 	jreq	00132$
      009173 7B 07            [ 1] 2815 	ld	a, (0x07, sp)
      009175 4A               [ 1] 2816 	dec	a
      009176 97               [ 1] 2817 	ld	xl, a
      009177 49               [ 1] 2818 	rlc	a
      009178 4F               [ 1] 2819 	clr	a
      009179 A2 00            [ 1] 2820 	sbc	a, #0x00
      00917B 95               [ 1] 2821 	ld	xh, a
      00917C D6 01 0B         [ 1] 2822 	ld	a, (_v_cand_m+0, x)
      00917F 11 04            [ 1] 2823 	cp	a, (0x04, sp)
      009181 23 04            [ 2] 2824 	jrule	00132$
      009183 0A 07            [ 1] 2825 	dec	(0x07, sp)
      009185 20 E8            [ 2] 2826 	jra	00102$
      009187                       2827 00132$:
                                   2828 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 773: if (i >= A_MAX) return;
      009187 7B 07            [ 1] 2829 	ld	a, (0x07, sp)
      009189 6B 01            [ 1] 2830 	ld	(0x01, sp), a
      00918B A1 05            [ 1] 2831 	cp	a, #0x05
      00918D 24 60            [ 1] 2832 	jrnc	00112$
                                   2833 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 774: j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
      00918F C6 01 10         [ 1] 2834 	ld	a, _v_ncand+0
      009192 A1 05            [ 1] 2835 	cp	a, #0x05
      009194 24 03            [ 1] 2836 	jrnc	00114$
      009196 7B 03            [ 1] 2837 	ld	a, (0x03, sp)
      009198 C5                    2838 	.byte 0xc5
      009199                       2839 00114$:
      009199 A6 04            [ 1] 2840 	ld	a, #0x04
      00919B                       2841 00115$:
      00919B 6B 07            [ 1] 2842 	ld	(0x07, sp), a
                                   2843 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 775: while (j > i) {
      00919D                       2844 00107$:
                                   2845 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 776: v_cand_t[j] = v_cand_t[j - 1];
      00919D 7B 07            [ 1] 2846 	ld	a, (0x07, sp)
      00919F 11 01            [ 1] 2847 	cp	a, (0x01, sp)
      0091A1 23 2E            [ 2] 2848 	jrule	00109$
      0091A3 5F               [ 1] 2849 	clrw	x
      0091A4 97               [ 1] 2850 	ld	xl, a
      0091A5 58               [ 2] 2851 	sllw	x
      0091A6 1C 01 01         [ 2] 2852 	addw	x, #(_v_cand_t+0)
      0091A9 51               [ 1] 2853 	exgw	x, y
      0091AA 7B 07            [ 1] 2854 	ld	a, (0x07, sp)
      0091AC 4A               [ 1] 2855 	dec	a
      0091AD 6B 03            [ 1] 2856 	ld	(0x03, sp), a
      0091AF 49               [ 1] 2857 	rlc	a
      0091B0 4F               [ 1] 2858 	clr	a
      0091B1 A2 00            [ 1] 2859 	sbc	a, #0x00
      0091B3 6B 02            [ 1] 2860 	ld	(0x02, sp), a
      0091B5 1E 02            [ 2] 2861 	ldw	x, (0x02, sp)
      0091B7 58               [ 2] 2862 	sllw	x
      0091B8 DE 01 01         [ 2] 2863 	ldw	x, (_v_cand_t+0, x)
      0091BB 90 FF            [ 2] 2864 	ldw	(y), x
                                   2865 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 777: v_cand_m[j] = v_cand_m[j - 1];
      0091BD 5F               [ 1] 2866 	clrw	x
      0091BE 7B 07            [ 1] 2867 	ld	a, (0x07, sp)
      0091C0 97               [ 1] 2868 	ld	xl, a
      0091C1 1C 01 0B         [ 2] 2869 	addw	x, #(_v_cand_m+0)
      0091C4 16 02            [ 2] 2870 	ldw	y, (0x02, sp)
      0091C6 72 A9 01 0B      [ 2] 2871 	addw	y, #(_v_cand_m+0)
      0091CA 90 F6            [ 1] 2872 	ld	a, (y)
      0091CC F7               [ 1] 2873 	ld	(x), a
                                   2874 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 778: j--;
      0091CD 0A 07            [ 1] 2875 	dec	(0x07, sp)
      0091CF 20 CC            [ 2] 2876 	jra	00107$
      0091D1                       2877 00109$:
                                   2878 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 780: v_cand_t[i] = k;
      0091D1 7B 01            [ 1] 2879 	ld	a, (0x01, sp)
      0091D3 5F               [ 1] 2880 	clrw	x
      0091D4 97               [ 1] 2881 	ld	xl, a
      0091D5 58               [ 2] 2882 	sllw	x
      0091D6 16 05            [ 2] 2883 	ldw	y, (0x05, sp)
      0091D8 DF 01 01         [ 2] 2884 	ldw	((_v_cand_t+0), x), y
                                   2885 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 781: v_cand_m[i] = m;
      0091DB 5F               [ 1] 2886 	clrw	x
      0091DC 7B 01            [ 1] 2887 	ld	a, (0x01, sp)
      0091DE 97               [ 1] 2888 	ld	xl, a
      0091DF 7B 04            [ 1] 2889 	ld	a, (0x04, sp)
      0091E1 D7 01 0B         [ 1] 2890 	ld	((_v_cand_m+0), x), a
                                   2891 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 782: if (v_ncand < A_MAX) v_ncand++;
      0091E4 C6 01 10         [ 1] 2892 	ld	a, _v_ncand+0
      0091E7 A1 05            [ 1] 2893 	cp	a, #0x05
      0091E9 24 04            [ 1] 2894 	jrnc	00112$
      0091EB 72 5C 01 10      [ 1] 2895 	inc	_v_ncand+0
      0091EF                       2896 00112$:
                                   2897 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 783: }
      0091EF 5B 07            [ 2] 2898 	addw	sp, #7
      0091F1 81               [ 4] 2899 	ret
                                   2900 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 785: static void decide_pass(void)
                                   2901 ;	-----------------------------------------
                                   2902 ;	 function decide_pass
                                   2903 ;	-----------------------------------------
      0091F2                       2904 _decide_pass:
      0091F2 52 21            [ 2] 2905 	sub	sp, #33
                                   2906 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 789: for (t = 0; t < NBB; t++) d_bits[t] = 0;
      0091F4 4F               [ 1] 2907 	clr	a
      0091F5                       2908 00168$:
      0091F5 5F               [ 1] 2909 	clrw	x
      0091F6 97               [ 1] 2910 	ld	xl, a
      0091F7 72 4F 00 C1      [ 1] 2911 	clr	((_d_bits+0), x)
      0091FB 4C               [ 1] 2912 	inc	a
      0091FC A1 18            [ 1] 2913 	cp	a, #0x18
      0091FE 25 F5            [ 1] 2914 	jrc	00168$
                                   2915 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 790: d_infeas = 0; d_laberr = 0; d_nseg = 0;
      009200 5F               [ 1] 2916 	clrw	x
      009201 CF 00 D9         [ 2] 2917 	ldw	_d_infeas+0, x
      009204 5F               [ 1] 2918 	clrw	x
      009205 CF 00 DB         [ 2] 2919 	ldw	_d_laberr+0, x
      009208 5F               [ 1] 2920 	clrw	x
      009209 CF 00 DD         [ 2] 2921 	ldw	_d_nseg+0, x
                                   2922 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 791: v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1;
      00920C 72 5F 01 10      [ 1] 2923 	clr	_v_ncand+0
      009210 5F               [ 1] 2924 	clrw	x
      009211 CF 01 11         [ 2] 2925 	ldw	_v_nweak+0, x
      009214 5F               [ 1] 2926 	clrw	x
      009215 CF 01 13         [ 2] 2927 	ldw	_v_ntied+0, x
      009218 5F               [ 1] 2928 	clrw	x
      009219 5A               [ 2] 2929 	decw	x
      00921A CF 01 15         [ 2] 2930 	ldw	_v_tiepend+0, x
                                   2931 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 792: ss_init();
      00921D CD 84 FB         [ 4] 2932 	call	_ss_init
                                   2933 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 793: while (ss_next(&sg)) {
      009220                       2934 00165$:
      009220 96               [ 1] 2935 	ldw	x, sp
      009221 5C               [ 1] 2936 	incw	x
      009222 CD 85 3D         [ 4] 2937 	call	_ss_next
      009225 4D               [ 1] 2938 	tnz	a
      009226 26 03            [ 1] 2939 	jrne	00557$
      009228 CC 94 73         [ 2] 2940 	jp	00185$
      00922B                       2941 00557$:
                                   2942 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 796: int16_t tie_here = -1, ins0 = -1, ins1 = -1;
      00922B 5F               [ 1] 2943 	clrw	x
      00922C 5A               [ 2] 2944 	decw	x
      00922D 1F 12            [ 2] 2945 	ldw	(0x12, sp), x
      00922F 5F               [ 1] 2946 	clrw	x
      009230 5A               [ 2] 2947 	decw	x
      009231 1F 18            [ 2] 2948 	ldw	(0x18, sp), x
      009233 5F               [ 1] 2949 	clrw	x
      009234 5A               [ 2] 2950 	decw	x
      009235 1F 1A            [ 2] 2951 	ldw	(0x1a, sp), x
                                   2952 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 799: d_nseg++;
      009237 CE 00 DD         [ 2] 2953 	ldw	x, _d_nseg+0
      00923A 5C               [ 1] 2954 	incw	x
      00923B CF 00 DD         [ 2] 2955 	ldw	_d_nseg+0, x
                                   2956 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: if (sg.k0 >= NB) continue;
      00923E 96               [ 1] 2957 	ldw	x, sp
      00923F 5C               [ 1] 2958 	incw	x
      009240 1F 14            [ 2] 2959 	ldw	(0x14, sp), x
      009242 FE               [ 2] 2960 	ldw	x, (x)
      009243 1F 1C            [ 2] 2961 	ldw	(0x1c, sp), x
      009245 A3 00 C0         [ 2] 2962 	cpw	x, #0x00c0
      009248 24 D6            [ 1] 2963 	jrnc	00165$
                                   2964 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: &a_hat, &a_free, &lo, &hi);
                                   2965 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 801: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
      00924A 7B 09            [ 1] 2966 	ld	a, (0x09, sp)
      00924C 16 07            [ 2] 2967 	ldw	y, (0x07, sp)
      00924E 1E 05            [ 2] 2968 	ldw	x, (0x05, sp)
      009250 1F 1E            [ 2] 2969 	ldw	(0x1e, sp), x
      009252 1E 03            [ 2] 2970 	ldw	x, (0x03, sp)
      009254 1F 20            [ 2] 2971 	ldw	(0x20, sp), x
      009256 96               [ 1] 2972 	ldw	x, sp
      009257 1C 00 10         [ 2] 2973 	addw	x, #16
      00925A 89               [ 2] 2974 	pushw	x
      00925B 96               [ 1] 2975 	ldw	x, sp
      00925C 1C 00 10         [ 2] 2976 	addw	x, #16
      00925F 89               [ 2] 2977 	pushw	x
      009260 96               [ 1] 2978 	ldw	x, sp
      009261 1C 00 10         [ 2] 2979 	addw	x, #16
      009264 89               [ 2] 2980 	pushw	x
      009265 96               [ 1] 2981 	ldw	x, sp
      009266 1C 00 10         [ 2] 2982 	addw	x, #16
      009269 89               [ 2] 2983 	pushw	x
      00926A 88               [ 1] 2984 	push	a
      00926B 90 89            [ 2] 2985 	pushw	y
      00926D 1E 29            [ 2] 2986 	ldw	x, (0x29, sp)
      00926F 89               [ 2] 2987 	pushw	x
      009270 1E 2D            [ 2] 2988 	ldw	x, (0x2d, sp)
      009272 89               [ 2] 2989 	pushw	x
      009273 1E 2B            [ 2] 2990 	ldw	x, (0x2b, sp)
      009275 CD 8F 52         [ 4] 2991 	call	_decide
      009278 1F 1C            [ 2] 2992 	ldw	(0x1c, sp), x
                                   2993 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 803: c_hat = d_costs[a_hat];
      00927A 1E 0A            [ 2] 2994 	ldw	x, (0x0a, sp)
      00927C 58               [ 2] 2995 	sllw	x
      00927D DE 00 DF         [ 2] 2996 	ldw	x, (_d_costs+0, x)
                                   2997 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 804: if (c_hat > INFEAS_U) d_infeas++;
      009280 A3 00 A0         [ 2] 2998 	cpw	x, #0x00a0
      009283 23 07            [ 2] 2999 	jrule	00105$
      009285 CE 00 D9         [ 2] 3000 	ldw	x, _d_infeas+0
      009288 5C               [ 1] 3001 	incw	x
      009289 CF 00 D9         [ 2] 3002 	ldw	_d_infeas+0, x
      00928C                       3003 00105$:
                                   3004 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: kk1 = (sg.k1 < NB) ? sg.k1 : NB;
      00928C 1E 03            [ 2] 3005 	ldw	x, (0x03, sp)
      00928E A3 00 C0         [ 2] 3006 	cpw	x, #0x00c0
      009291 24 07            [ 1] 3007 	jrnc	00187$
      009293 41               [ 1] 3008 	exg	a, xl
      009294 6B 21            [ 1] 3009 	ld	(0x21, sp), a
      009296 41               [ 1] 3010 	exg	a, xl
      009297 4F               [ 1] 3011 	clr	a
      009298 20 05            [ 2] 3012 	jra	00188$
      00929A                       3013 00187$:
      00929A A6 C0            [ 1] 3014 	ld	a, #0xc0
      00929C 6B 21            [ 1] 3015 	ld	(0x21, sp), a
      00929E 4F               [ 1] 3016 	clr	a
      00929F                       3017 00188$:
      00929F 6B 16            [ 1] 3018 	ld	(0x16, sp), a
      0092A1 7B 21            [ 1] 3019 	ld	a, (0x21, sp)
      0092A3 6B 17            [ 1] 3020 	ld	(0x17, sp), a
                                   3021 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 806: known_all = 1;
      0092A5 A6 01            [ 1] 3022 	ld	a, #0x01
      0092A7 6B 1E            [ 1] 3023 	ld	(0x1e, sp), a
                                   3024 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: for (t = sg.k0; t < kk1; t++)
      0092A9 1E 14            [ 2] 3025 	ldw	x, (0x14, sp)
      0092AB FE               [ 2] 3026 	ldw	x, (x)
      0092AC 1F 20            [ 2] 3027 	ldw	(0x20, sp), x
      0092AE                       3028 00171$:
                                   3029 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 808: if (known_bit(t) < 0) { known_all = 0; break; }
      0092AE 1E 20            [ 2] 3030 	ldw	x, (0x20, sp)
      0092B0 13 16            [ 2] 3031 	cpw	x, (0x16, sp)
      0092B2 24 11            [ 1] 3032 	jrnc	00108$
      0092B4 CD 81 37         [ 4] 3033 	call	_known_bit
      0092B7 4D               [ 1] 3034 	tnz	a
      0092B8 2A 04            [ 1] 3035 	jrpl	00172$
      0092BA 0F 1E            [ 1] 3036 	clr	(0x1e, sp)
      0092BC 20 07            [ 2] 3037 	jra	00108$
      0092BE                       3038 00172$:
                                   3039 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: for (t = sg.k0; t < kk1; t++)
      0092BE 1E 20            [ 2] 3040 	ldw	x, (0x20, sp)
      0092C0 5C               [ 1] 3041 	incw	x
      0092C1 1F 20            [ 2] 3042 	ldw	(0x20, sp), x
      0092C3 20 E9            [ 2] 3043 	jra	00171$
      0092C5                       3044 00108$:
                                   3045 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 809: dead = 0; nins = 0;
      0092C5 0F 1F            [ 1] 3046 	clr	(0x1f, sp)
                                   3047 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 810: for (a = 0; a <= acap; a++)
      0092C7 4F               [ 1] 3048 	clr	a
      0092C8 5F               [ 1] 3049 	clrw	x
      0092C9 1F 20            [ 2] 3050 	ldw	(0x20, sp), x
      0092CB                       3051 00174$:
      0092CB 1E 20            [ 2] 3052 	ldw	x, (0x20, sp)
      0092CD 13 1C            [ 2] 3053 	cpw	x, (0x1c, sp)
      0092CF 2C 18            [ 1] 3054 	jrsgt	00111$
                                   3055 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 811: if ((d_inter >> a) & 1) nins++;
      0092D1 88               [ 1] 3056 	push	a
      0092D2 CE 00 FF         [ 2] 3057 	ldw	x, _d_inter+0
      0092D5 7B 22            [ 1] 3058 	ld	a, (0x22, sp)
      0092D7 27 04            [ 1] 3059 	jreq	00566$
      0092D9                       3060 00565$:
      0092D9 54               [ 2] 3061 	srlw	x
      0092DA 4A               [ 1] 3062 	dec	a
      0092DB 26 FC            [ 1] 3063 	jrne	00565$
      0092DD                       3064 00566$:
      0092DD 84               [ 1] 3065 	pop	a
      0092DE 54               [ 2] 3066 	srlw	x
      0092DF 24 01            [ 1] 3067 	jrnc	00175$
      0092E1 4C               [ 1] 3068 	inc	a
      0092E2                       3069 00175$:
                                   3070 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 810: for (a = 0; a <= acap; a++)
      0092E2 1E 20            [ 2] 3071 	ldw	x, (0x20, sp)
      0092E4 5C               [ 1] 3072 	incw	x
      0092E5 1F 20            [ 2] 3073 	ldw	(0x20, sp), x
      0092E7 20 E2            [ 2] 3074 	jra	00174$
      0092E9                       3075 00111$:
                                   3076 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 812: if (nins >= 2) dead = 1;
      0092E9 A1 02            [ 1] 3077 	cp	a, #0x02
      0092EB 25 04            [ 1] 3078 	jrc	00113$
      0092ED A6 01            [ 1] 3079 	ld	a, #0x01
      0092EF 6B 1F            [ 1] 3080 	ld	(0x1f, sp), a
      0092F1                       3081 00113$:
                                   3082 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 813: if (known_all && lo == hi && a_free != lo && !dead)
      0092F1 0D 1E            [ 1] 3083 	tnz	(0x1e, sp)
      0092F3 27 17            [ 1] 3084 	jreq	00115$
      0092F5 1E 0E            [ 2] 3085 	ldw	x, (0x0e, sp)
      0092F7 13 10            [ 2] 3086 	cpw	x, (0x10, sp)
      0092F9 26 11            [ 1] 3087 	jrne	00115$
      0092FB 1E 0C            [ 2] 3088 	ldw	x, (0x0c, sp)
      0092FD 13 0E            [ 2] 3089 	cpw	x, (0x0e, sp)
      0092FF 27 0B            [ 1] 3090 	jreq	00115$
      009301 0D 1F            [ 1] 3091 	tnz	(0x1f, sp)
      009303 26 07            [ 1] 3092 	jrne	00115$
                                   3093 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: d_laberr++;
      009305 CE 00 DB         [ 2] 3094 	ldw	x, _d_laberr+0
      009308 5C               [ 1] 3095 	incw	x
      009309 CF 00 DB         [ 2] 3096 	ldw	_d_laberr+0, x
      00930C                       3097 00115$:
                                   3098 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 819: for (a = lo; a <= hi; a++) {
      00930C 1E 0E            [ 2] 3099 	ldw	x, (0x0e, sp)
      00930E 4F               [ 1] 3100 	clr	a
      00930F 1F 20            [ 2] 3101 	ldw	(0x20, sp), x
      009311                       3102 00177$:
      009311 1E 20            [ 2] 3103 	ldw	x, (0x20, sp)
      009313 13 10            [ 2] 3104 	cpw	x, (0x10, sp)
      009315 2C 29            [ 1] 3105 	jrsgt	00126$
                                   3106 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 820: if ((d_inter >> a) & 1) {
      009317 88               [ 1] 3107 	push	a
      009318 CE 00 FF         [ 2] 3108 	ldw	x, _d_inter+0
      00931B 7B 22            [ 1] 3109 	ld	a, (0x22, sp)
      00931D 27 04            [ 1] 3110 	jreq	00580$
      00931F                       3111 00579$:
      00931F 54               [ 2] 3112 	srlw	x
      009320 4A               [ 1] 3113 	dec	a
      009321 26 FC            [ 1] 3114 	jrne	00579$
      009323                       3115 00580$:
      009323 84               [ 1] 3116 	pop	a
      009324 54               [ 2] 3117 	srlw	x
      009325 24 12            [ 1] 3118 	jrnc	00178$
                                   3119 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 821: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
      009327 4D               [ 1] 3120 	tnz	a
      009328 26 06            [ 1] 3121 	jrne	00122$
      00932A 16 20            [ 2] 3122 	ldw	y, (0x20, sp)
      00932C 17 18            [ 2] 3123 	ldw	(0x18, sp), y
      00932E 20 08            [ 2] 3124 	jra	00123$
      009330                       3125 00122$:
      009330 A1 01            [ 1] 3126 	cp	a, #0x01
      009332 26 04            [ 1] 3127 	jrne	00123$
      009334 16 20            [ 2] 3128 	ldw	y, (0x20, sp)
      009336 17 1A            [ 2] 3129 	ldw	(0x1a, sp), y
      009338                       3130 00123$:
                                   3131 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 822: nins++;
      009338 4C               [ 1] 3132 	inc	a
      009339                       3133 00178$:
                                   3134 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 819: for (a = lo; a <= hi; a++) {
      009339 1E 20            [ 2] 3135 	ldw	x, (0x20, sp)
      00933B 5C               [ 1] 3136 	incw	x
      00933C 1F 20            [ 2] 3137 	ldw	(0x20, sp), x
      00933E 20 D1            [ 2] 3138 	jra	00177$
      009340                       3139 00126$:
                                   3140 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: if (sg.k0 >= NB) continue;
      009340 1E 14            [ 2] 3141 	ldw	x, (0x14, sp)
      009342 FE               [ 2] 3142 	ldw	x, (x)
      009343 1F 20            [ 2] 3143 	ldw	(0x20, sp), x
                                   3144 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
      009345 A1 02            [ 1] 3145 	cp	a, #0x02
      009347 25 18            [ 1] 3146 	jrc	00130$
      009349 1E 0A            [ 2] 3147 	ldw	x, (0x0a, sp)
      00934B 13 18            [ 2] 3148 	cpw	x, (0x18, sp)
      00934D 27 06            [ 1] 3149 	jreq	00129$
      00934F 1E 0A            [ 2] 3150 	ldw	x, (0x0a, sp)
      009351 13 1A            [ 2] 3151 	cpw	x, (0x1a, sp)
      009353 26 0C            [ 1] 3152 	jrne	00130$
      009355                       3153 00129$:
                                   3154 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 826: uint16_t tt = (uint16_t)(sg.k0 + ins0);
      009355 1E 18            [ 2] 3155 	ldw	x, (0x18, sp)
      009357 72 FB 20         [ 2] 3156 	addw	x, (0x20, sp)
                                   3157 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 827: if (tt < NB) tie_here = (int16_t)tt;
      00935A A3 00 C0         [ 2] 3158 	cpw	x, #0x00c0
      00935D 24 02            [ 1] 3159 	jrnc	00130$
      00935F 1F 12            [ 2] 3160 	ldw	(0x12, sp), x
      009361                       3161 00130$:
                                   3162 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: for (t = sg.k0; t < kk1; t++) {
      009361 16 20            [ 2] 3163 	ldw	y, (0x20, sp)
      009363 17 1E            [ 2] 3164 	ldw	(0x1e, sp), y
      009365                       3165 00183$:
      009365 1E 1E            [ 2] 3166 	ldw	x, (0x1e, sp)
      009367 13 16            [ 2] 3167 	cpw	x, (0x16, sp)
      009369 25 03            [ 1] 3168 	jrc	00595$
      00936B CC 94 4C         [ 2] 3169 	jp	00159$
      00936E                       3170 00595$:
                                   3171 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 831: int16_t off = (int16_t)(t - sg.k0);
      00936E 1E 14            [ 2] 3172 	ldw	x, (0x14, sp)
      009370 FE               [ 2] 3173 	ldw	x, (x)
      009371 50               [ 2] 3174 	negw	x
      009372 72 FB 1E         [ 2] 3175 	addw	x, (0x1e, sp)
      009375 1F 18            [ 2] 3176 	ldw	(0x18, sp), x
                                   3177 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 832: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
      009377 5F               [ 1] 3178 	clrw	x
      009378 5A               [ 2] 3179 	decw	x
      009379 1F 1A            [ 2] 3180 	ldw	(0x1a, sp), x
      00937B 5F               [ 1] 3181 	clrw	x
      00937C 5A               [ 2] 3182 	decw	x
      00937D 1F 1C            [ 2] 3183 	ldw	(0x1c, sp), x
                                   3184 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 833: if (off < a_hat) BSET(d_bits, t);
      00937F 1E 18            [ 2] 3185 	ldw	x, (0x18, sp)
      009381 13 0A            [ 2] 3186 	cpw	x, (0x0a, sp)
      009383 2E 21            [ 1] 3187 	jrsge	00134$
      009385 1E 1E            [ 2] 3188 	ldw	x, (0x1e, sp)
      009387 54               [ 2] 3189 	srlw	x
      009388 54               [ 2] 3190 	srlw	x
      009389 54               [ 2] 3191 	srlw	x
      00938A 1C 00 C1         [ 2] 3192 	addw	x, #(_d_bits+0)
      00938D F6               [ 1] 3193 	ld	a, (x)
      00938E 6B 20            [ 1] 3194 	ld	(0x20, sp), a
      009390 7B 1F            [ 1] 3195 	ld	a, (0x1f, sp)
      009392 A4 07            [ 1] 3196 	and	a, #0x07
      009394 6B 21            [ 1] 3197 	ld	(0x21, sp), a
      009396 A6 01            [ 1] 3198 	ld	a, #0x01
      009398 88               [ 1] 3199 	push	a
      009399 7B 22            [ 1] 3200 	ld	a, (0x22, sp)
      00939B 27 05            [ 1] 3201 	jreq	00598$
      00939D                       3202 00597$:
      00939D 08 01            [ 1] 3203 	sll	(1, sp)
      00939F 4A               [ 1] 3204 	dec	a
      0093A0 26 FB            [ 1] 3205 	jrne	00597$
      0093A2                       3206 00598$:
      0093A2 84               [ 1] 3207 	pop	a
      0093A3 1A 20            [ 1] 3208 	or	a, (0x20, sp)
      0093A5 F7               [ 1] 3209 	ld	(x), a
      0093A6                       3210 00134$:
                                   3211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 834: for (a = lo; a <= hi; a++) {
      0093A6 16 0E            [ 2] 3212 	ldw	y, (0x0e, sp)
      0093A8 17 20            [ 2] 3213 	ldw	(0x20, sp), y
      0093AA                       3214 00180$:
      0093AA 1E 20            [ 2] 3215 	ldw	x, (0x20, sp)
      0093AC 13 10            [ 2] 3216 	cpw	x, (0x10, sp)
      0093AE 2C 23            [ 1] 3217 	jrsgt	00142$
                                   3218 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 835: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
      0093B0 1E 20            [ 2] 3219 	ldw	x, (0x20, sp)
      0093B2 58               [ 2] 3220 	sllw	x
      0093B3 DE 00 DF         [ 2] 3221 	ldw	x, (_d_costs+0, x)
      0093B6 89               [ 2] 3222 	pushw	x
      0093B7 1E 22            [ 2] 3223 	ldw	x, (0x22, sp)
      0093B9 13 1A            [ 2] 3224 	cpw	x, (0x1a, sp)
      0093BB 85               [ 2] 3225 	popw	x
      0093BC 2D 08            [ 1] 3226 	jrsle	00140$
      0093BE 13 1C            [ 2] 3227 	cpw	x, (0x1c, sp)
      0093C0 24 0A            [ 1] 3228 	jrnc	00181$
      0093C2 1F 1C            [ 2] 3229 	ldw	(0x1c, sp), x
      0093C4 20 06            [ 2] 3230 	jra	00181$
      0093C6                       3231 00140$:
                                   3232 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 836: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
      0093C6 13 1A            [ 2] 3233 	cpw	x, (0x1a, sp)
      0093C8 24 02            [ 1] 3234 	jrnc	00181$
      0093CA 1F 1A            [ 2] 3235 	ldw	(0x1a, sp), x
      0093CC                       3236 00181$:
                                   3237 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 834: for (a = lo; a <= hi; a++) {
      0093CC 1E 20            [ 2] 3238 	ldw	x, (0x20, sp)
      0093CE 5C               [ 1] 3239 	incw	x
      0093CF 1F 20            [ 2] 3240 	ldw	(0x20, sp), x
      0093D1 20 D7            [ 2] 3241 	jra	00180$
      0093D3                       3242 00142$:
                                   3243 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 838: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
      0093D3 1E 1A            [ 2] 3244 	ldw	x, (0x1a, sp)
      0093D5 5C               [ 1] 3245 	incw	x
      0093D6 27 05            [ 1] 3246 	jreq	00145$
      0093D8 1E 1C            [ 2] 3247 	ldw	x, (0x1c, sp)
      0093DA 5C               [ 1] 3248 	incw	x
      0093DB 26 07            [ 1] 3249 	jrne	00146$
      0093DD                       3250 00145$:
      0093DD AE 00 FF         [ 2] 3251 	ldw	x, #0x00ff
      0093E0 1F 20            [ 2] 3252 	ldw	(0x20, sp), x
      0093E2 20 1A            [ 2] 3253 	jra	00147$
      0093E4                       3254 00146$:
                                   3255 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 840: int16_t dm = (int16_t)(c0m - c1m);
      0093E4 1E 1A            [ 2] 3256 	ldw	x, (0x1a, sp)
      0093E6 72 F0 1C         [ 2] 3257 	subw	x, (0x1c, sp)
                                   3258 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 841: if (dm < 0) dm = (int16_t)-dm;
      0093E9 1F 20            [ 2] 3259 	ldw	(0x20, sp), x
      0093EB 5D               [ 2] 3260 	tnzw	x
      0093EC 2A 07            [ 1] 3261 	jrpl	00144$
      0093EE 00 21            [ 1] 3262 	neg	(0x21, sp)
      0093F0 4F               [ 1] 3263 	clr	a
      0093F1 12 20            [ 1] 3264 	sbc	a, (0x20, sp)
      0093F3 6B 20            [ 1] 3265 	ld	(0x20, sp), a
      0093F5                       3266 00144$:
                                   3267 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 842: m = (dm > 255) ? 255 : (uint16_t)dm;
      0093F5 AE 00 FF         [ 2] 3268 	ldw	x, #0x00ff
      0093F8 13 20            [ 2] 3269 	cpw	x, (0x20, sp)
      0093FA 2C 02            [ 1] 3270 	jrsgt	00189$
      0093FC 1F 20            [ 2] 3271 	ldw	(0x20, sp), x
      0093FE                       3272 00189$:
      0093FE                       3273 00147$:
                                   3274 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 844: if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
      0093FE 1E 1E            [ 2] 3275 	ldw	x, (0x1e, sp)
      009400 13 12            [ 2] 3276 	cpw	x, (0x12, sp)
      009402 27 05            [ 1] 3277 	jreq	00149$
      009404 C3 01 15         [ 2] 3278 	cpw	x, _v_tiepend+0
      009407 26 03            [ 1] 3279 	jrne	00150$
      009409                       3280 00149$:
                                   3281 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 845: m = 0;                       /* decided by tie-break */
      009409 5F               [ 1] 3282 	clrw	x
      00940A 1F 20            [ 2] 3283 	ldw	(0x20, sp), x
      00940C                       3284 00150$:
                                   3285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 846: if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
      00940C 16 1E            [ 2] 3286 	ldw	y, (0x1e, sp)
      00940E 17 1C            [ 2] 3287 	ldw	(0x1c, sp), y
      009410 93               [ 1] 3288 	ldw	x, y
      009411 A3 00 20         [ 2] 3289 	cpw	x, #0x0020
      009414 25 2E            [ 1] 3290 	jrc	00184$
      009416 1E 1E            [ 2] 3291 	ldw	x, (0x1e, sp)
      009418 A3 00 A0         [ 2] 3292 	cpw	x, #0x00a0
      00941B 24 27            [ 1] 3293 	jrnc	00184$
                                   3294 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 847: if (m <= MG_MAX) {
      00941D 1E 20            [ 2] 3295 	ldw	x, (0x20, sp)
      00941F A3 00 08         [ 2] 3296 	cpw	x, #0x0008
      009422 22 20            [ 1] 3297 	jrugt	00184$
                                   3298 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 848: uint16_t k = t - PP_LO;
      009424 1E 1C            [ 2] 3299 	ldw	x, (0x1c, sp)
      009426 1D 00 20         [ 2] 3300 	subw	x, #0x0020
      009429 1F 1C            [ 2] 3301 	ldw	(0x1c, sp), x
                                   3302 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 849: v_nweak++;
      00942B CE 01 11         [ 2] 3303 	ldw	x, _v_nweak+0
      00942E 5C               [ 1] 3304 	incw	x
      00942F CF 01 11         [ 2] 3305 	ldw	_v_nweak+0, x
                                   3306 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 850: if (m == 0) v_ntied++;
      009432 1E 20            [ 2] 3307 	ldw	x, (0x20, sp)
      009434 26 07            [ 1] 3308 	jrne	00153$
      009436 CE 01 13         [ 2] 3309 	ldw	x, _v_ntied+0
      009439 5C               [ 1] 3310 	incw	x
      00943A CF 01 13         [ 2] 3311 	ldw	_v_ntied+0, x
      00943D                       3312 00153$:
                                   3313 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 851: cand_insert(k, (uint8_t)m);
      00943D 7B 21            [ 1] 3314 	ld	a, (0x21, sp)
      00943F 1E 1C            [ 2] 3315 	ldw	x, (0x1c, sp)
      009441 CD 91 62         [ 4] 3316 	call	_cand_insert
      009444                       3317 00184$:
                                   3318 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: for (t = sg.k0; t < kk1; t++) {
      009444 1E 1E            [ 2] 3319 	ldw	x, (0x1e, sp)
      009446 5C               [ 1] 3320 	incw	x
      009447 1F 1E            [ 2] 3321 	ldw	(0x1e, sp), x
      009449 CC 93 65         [ 2] 3322 	jp	00183$
      00944C                       3323 00159$:
                                   3324 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 855: if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
      00944C CE 01 15         [ 2] 3325 	ldw	x, _v_tiepend+0
      00944F 16 16            [ 2] 3326 	ldw	y, (0x16, sp)
      009451 17 20            [ 2] 3327 	ldw	(0x20, sp), y
      009453 5D               [ 2] 3328 	tnzw	x
      009454 2B 0C            [ 1] 3329 	jrmi	00161$
      009456 1E 20            [ 2] 3330 	ldw	x, (0x20, sp)
      009458 C3 01 15         [ 2] 3331 	cpw	x, _v_tiepend+0
      00945B 2D 05            [ 1] 3332 	jrsle	00161$
                                   3333 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 856: v_tiepend = -1;                  /* consumed              */
      00945D 5F               [ 1] 3334 	clrw	x
      00945E 5A               [ 2] 3335 	decw	x
      00945F CF 01 15         [ 2] 3336 	ldw	_v_tiepend+0, x
      009462                       3337 00161$:
                                   3338 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 857: if (tie_here >= (int16_t)kk1)
      009462 1E 12            [ 2] 3339 	ldw	x, (0x12, sp)
      009464 13 20            [ 2] 3340 	cpw	x, (0x20, sp)
      009466 2E 03            [ 1] 3341 	jrsge	00625$
      009468 CC 92 20         [ 2] 3342 	jp	00165$
      00946B                       3343 00625$:
                                   3344 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 858: v_tiepend = tie_here;            /* lands in next segment */
      00946B 1E 12            [ 2] 3345 	ldw	x, (0x12, sp)
      00946D CF 01 15         [ 2] 3346 	ldw	_v_tiepend+0, x
      009470 CC 92 20         [ 2] 3347 	jp	00165$
      009473                       3348 00185$:
                                   3349 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 860: }
      009473 5B 21            [ 2] 3350 	addw	sp, #33
      009475 81               [ 4] 3351 	ret
                                   3352 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 970: static uint8_t chase(uint8_t *out)
                                   3353 ;	-----------------------------------------
                                   3354 ;	 function chase
                                   3355 ;	-----------------------------------------
      009476                       3356 _chase:
      009476 52 07            [ 2] 3357 	sub	sp, #7
      009478 1F 04            [ 2] 3358 	ldw	(0x04, sp), x
                                   3359 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: for (p = 0; p < NPP; p++) {
      00947A 0F 06            [ 1] 3360 	clr	(0x06, sp)
      00947C                       3361 00108$:
                                   3362 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 975: uint8_t val = 0;
      00947C 0F 03            [ 1] 3363 	clr	(0x03, sp)
                                   3364 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 976: uint16_t base = PP_LO + ((uint16_t)p << 3);
      00947E 7B 06            [ 1] 3365 	ld	a, (0x06, sp)
      009480 48               [ 1] 3366 	sll	a
      009481 48               [ 1] 3367 	sll	a
      009482 48               [ 1] 3368 	sll	a
      009483 AB 20            [ 1] 3369 	add	a, #0x20
      009485 90 97            [ 1] 3370 	ld	yl, a
                                   3371 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (j = 0; j < 8; j++)
      009487 0F 07            [ 1] 3372 	clr	(0x07, sp)
      009489                       3373 00106$:
                                   3374 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: val = (uint8_t)((val << 1) | BGET(d_bits, base + j));
      009489 7B 03            [ 1] 3375 	ld	a, (0x03, sp)
      00948B 48               [ 1] 3376 	sll	a
      00948C 6B 01            [ 1] 3377 	ld	(0x01, sp), a
      00948E 7B 07            [ 1] 3378 	ld	a, (0x07, sp)
      009490 6B 03            [ 1] 3379 	ld	(0x03, sp), a
      009492 0F 02            [ 1] 3380 	clr	(0x02, sp)
      009494 93               [ 1] 3381 	ldw	x, y
      009495 4F               [ 1] 3382 	clr	a
      009496 95               [ 1] 3383 	ld	xh, a
      009497 72 FB 02         [ 2] 3384 	addw	x, (0x02, sp)
      00949A 54               [ 2] 3385 	srlw	x
      00949B 54               [ 2] 3386 	srlw	x
      00949C 54               [ 2] 3387 	srlw	x
      00949D 1C 00 C1         [ 2] 3388 	addw	x, #(_d_bits+0)
      0094A0 F6               [ 1] 3389 	ld	a, (x)
      0094A1 97               [ 1] 3390 	ld	xl, a
      0094A2 90 9F            [ 1] 3391 	ld	a, yl
      0094A4 1B 07            [ 1] 3392 	add	a, (0x07, sp)
      0094A6 A4 07            [ 1] 3393 	and	a, #0x07
      0094A8 27 06            [ 1] 3394 	jreq	00174$
      0094AA                       3395 00173$:
      0094AA 41               [ 1] 3396 	exg	a, xl
      0094AB 44               [ 1] 3397 	srl	a
      0094AC 41               [ 1] 3398 	exg	a, xl
      0094AD 4A               [ 1] 3399 	dec	a
      0094AE 26 FA            [ 1] 3400 	jrne	00173$
      0094B0                       3401 00174$:
      0094B0 9F               [ 1] 3402 	ld	a, xl
      0094B1 A4 01            [ 1] 3403 	and	a, #0x01
      0094B3 1A 01            [ 1] 3404 	or	a, (0x01, sp)
      0094B5 6B 03            [ 1] 3405 	ld	(0x03, sp), a
                                   3406 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (j = 0; j < 8; j++)
      0094B7 0C 07            [ 1] 3407 	inc	(0x07, sp)
      0094B9 7B 07            [ 1] 3408 	ld	a, (0x07, sp)
      0094BB A1 08            [ 1] 3409 	cp	a, #0x08
      0094BD 25 CA            [ 1] 3410 	jrc	00106$
                                   3411 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 979: d_pp[p] = val;
      0094BF 5F               [ 1] 3412 	clrw	x
      0094C0 7B 06            [ 1] 3413 	ld	a, (0x06, sp)
      0094C2 97               [ 1] 3414 	ld	xl, a
      0094C3 7B 03            [ 1] 3415 	ld	a, (0x03, sp)
      0094C5 D7 01 17         [ 1] 3416 	ld	((_d_pp+0), x), a
                                   3417 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: for (p = 0; p < NPP; p++) {
      0094C8 0C 06            [ 1] 3418 	inc	(0x06, sp)
      0094CA 7B 06            [ 1] 3419 	ld	a, (0x06, sp)
      0094CC A1 10            [ 1] 3420 	cp	a, #0x10
      0094CE 25 AC            [ 1] 3421 	jrc	00108$
                                   3422 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 981: dec_info.n_weak = v_nweak;
      0094D0 55 01 12 00 07   [ 1] 3423 	mov	_dec_info+6, _v_nweak+1
      0094D5 55 01 11 00 06   [ 1] 3424 	mov	_dec_info+5, _v_nweak+0
                                   3425 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 982: dec_info.n_tied = v_ntied;
      0094DA 55 01 14 00 09   [ 1] 3426 	mov	_dec_info+8, _v_ntied+1
      0094DF 55 01 13 00 08   [ 1] 3427 	mov	_dec_info+7, _v_ntied+0
                                   3428 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 986: if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
      0094E4 CE 01 13         [ 2] 3429 	ldw	x, _v_ntied+0
      0094E7 A3 00 08         [ 2] 3430 	cpw	x, #0x0008
      0094EA 23 07            [ 2] 3431 	jrule	00126$
      0094EC 35 05 00 02      [ 1] 3432 	mov	_dec_info+1, #0x05
      0094F0 4F               [ 1] 3433 	clr	a
      0094F1 20 19            [ 2] 3434 	jra	00112$
                                   3435 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 987: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
      0094F3                       3436 00126$:
      0094F3 4F               [ 1] 3437 	clr	a
      0094F4                       3438 00110$:
      0094F4 90 5F            [ 1] 3439 	clrw	y
      0094F6 90 97            [ 1] 3440 	ld	yl, a
      0094F8 72 F9 04         [ 2] 3441 	addw	y, (0x04, sp)
      0094FB 5F               [ 1] 3442 	clrw	x
      0094FC 97               [ 1] 3443 	ld	xl, a
      0094FD 1C 01 17         [ 2] 3444 	addw	x, #(_d_pp+0)
      009500 88               [ 1] 3445 	push	a
      009501 F6               [ 1] 3446 	ld	a, (x)
      009502 90 F7            [ 1] 3447 	ld	(y), a
      009504 84               [ 1] 3448 	pop	a
      009505 4C               [ 1] 3449 	inc	a
      009506 A1 10            [ 1] 3450 	cp	a, #0x10
      009508 25 EA            [ 1] 3451 	jrc	00110$
                                   3452 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 988: return DEC_LEGACY;
      00950A A6 03            [ 1] 3453 	ld	a, #0x03
      00950C                       3454 00112$:
                                   3455 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1036: }
      00950C 5B 07            [ 2] 3456 	addw	sp, #7
      00950E 81               [ 4] 3457 	ret
                                   3458 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1040: uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
                                   3459 ;	-----------------------------------------
                                   3460 ;	 function ws_decode_ex
                                   3461 ;	-----------------------------------------
      00950F                       3462 _ws_decode_ex:
      00950F 52 06            [ 2] 3463 	sub	sp, #6
      009511 51               [ 1] 3464 	exgw	x, y
                                   3465 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1044: dec_info.path = DEC_REFUSE;
      009512 AE 00 01         [ 2] 3466 	ldw	x, #(_dec_info+0)
      009515 1F 01            [ 2] 3467 	ldw	(0x01, sp), x
      009517 7F               [ 1] 3468 	clr	(x)
                                   3469 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1045: dec_info.cause = CAUSE_NONE;
      009518 35 00 00 02      [ 1] 3470 	mov	_dec_info+1, #0x00
                                   3471 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1046: dec_info.trials = 0;
      00951C 35 00 00 03      [ 1] 3472 	mov	_dec_info+2, #0x00
                                   3473 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1047: dec_info.alias_cmp = 0;
      009520 35 00 00 04      [ 1] 3474 	mov	_dec_info+3, #0x00
                                   3475 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1048: dec_info.chased = 0;
      009524 35 00 00 05      [ 1] 3476 	mov	_dec_info+4, #0x00
                                   3477 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1049: dec_info.n_weak = 0;
      009528 AE 00 06         [ 2] 3478 	ldw	x, #(_dec_info+5)
      00952B 6F 01            [ 1] 3479 	clr	(0x1, x)
      00952D 7F               [ 1] 3480 	clr	(x)
                                   3481 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1050: dec_info.n_tied = 0;
      00952E AE 00 08         [ 2] 3482 	ldw	x, #(_dec_info+7)
      009531 6F 01            [ 1] 3483 	clr	(0x1, x)
      009533 7F               [ 1] 3484 	clr	(x)
                                   3485 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1051: dec_info.K = 0;
      009534 AE 00 0A         [ 2] 3486 	ldw	x, #(_dec_info+9)
      009537 6F 01            [ 1] 3487 	clr	(0x1, x)
      009539 7F               [ 1] 3488 	clr	(x)
                                   3489 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1052: dec_info.tau = 0;
      00953A AE 00 0C         [ 2] 3490 	ldw	x, #(_dec_info+11)
      00953D 6F 01            [ 1] 3491 	clr	(0x1, x)
      00953F 7F               [ 1] 3492 	clr	(x)
                                   3493 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1053: dec_info.violations = 0;
      009540 35 00 00 0E      [ 1] 3494 	mov	_dec_info+13, #0x00
                                   3495 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: dec_info.infeasible = 0;
      009544 AE 00 0F         [ 2] 3496 	ldw	x, #(_dec_info+14)
      009547 6F 01            [ 1] 3497 	clr	(0x1, x)
      009549 7F               [ 1] 3498 	clr	(x)
                                   3499 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1055: dec_info.label_err = 0;
      00954A AE 00 11         [ 2] 3500 	ldw	x, #(_dec_info+16)
      00954D 6F 01            [ 1] 3501 	clr	(0x1, x)
      00954F 7F               [ 1] 3502 	clr	(x)
                                   3503 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1056: dec_info.n_seg = 0;
      009550 AE 00 13         [ 2] 3504 	ldw	x, #(_dec_info+18)
      009553 6F 01            [ 1] 3505 	clr	(0x1, x)
      009555 7F               [ 1] 3506 	clr	(x)
                                   3507 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1057: scan_cap = cap;
      009556 90 CF 01 4C      [ 2] 3508 	ldw	_scan_cap+0, y
                                   3509 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1058: scan_len = ncap;
      00955A 1E 09            [ 2] 3510 	ldw	x, (0x09, sp)
      00955C CF 01 4E         [ 2] 3511 	ldw	_scan_len+0, x
                                   3512 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1059: if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
      00955F CD 81 BE         [ 4] 3513 	call	_seed
      009562 4D               [ 1] 3514 	tnz	a
      009563 26 08            [ 1] 3515 	jrne	00132$
      009565 35 01 00 02      [ 1] 3516 	mov	_dec_info+1, #0x01
      009569 4F               [ 1] 3517 	clr	a
      00956A CC 96 1D         [ 2] 3518 	jp	00119$
                                   3519 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1060: for (r = 0; r < 2; r++) refine();
      00956D                       3520 00132$:
      00956D A6 02            [ 1] 3521 	ld	a, #0x02
      00956F                       3522 00116$:
      00956F 88               [ 1] 3523 	push	a
      009570 CD 82 64         [ 4] 3524 	call	_refine
      009573 84               [ 1] 3525 	pop	a
      009574 4A               [ 1] 3526 	dec	a
      009575 26 F8            [ 1] 3527 	jrne	00116$
                                   3528 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1061: calibrate();
      009577 CD 8C B6         [ 4] 3529 	call	_calibrate
                                   3530 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1062: decide_pass();
      00957A CD 91 F2         [ 4] 3531 	call	_decide_pass
                                   3532 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1063: dec_info.K = g_K;
      00957D 55 00 16 00 0B   [ 1] 3533 	mov	_dec_info+10, _g_K+1
      009582 55 00 15 00 0A   [ 1] 3534 	mov	_dec_info+9, _g_K+0
                                   3535 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1064: dec_info.tau = g_tau;
      009587 55 00 18 00 0D   [ 1] 3536 	mov	_dec_info+12, _g_tau+1
      00958C 55 00 17 00 0C   [ 1] 3537 	mov	_dec_info+11, _g_tau+0
                                   3538 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1065: dec_info.infeasible = d_infeas;
      009591 55 00 DA 00 10   [ 1] 3539 	mov	_dec_info+15, _d_infeas+1
      009596 55 00 D9 00 0F   [ 1] 3540 	mov	_dec_info+14, _d_infeas+0
                                   3541 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1066: dec_info.label_err = d_laberr;
      00959B 55 00 DC 00 12   [ 1] 3542 	mov	_dec_info+17, _d_laberr+1
      0095A0 55 00 DB 00 11   [ 1] 3543 	mov	_dec_info+16, _d_laberr+0
                                   3544 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: dec_info.n_seg = d_nseg;
      0095A5 55 00 DE 00 14   [ 1] 3545 	mov	_dec_info+19, _d_nseg+1
      0095AA 55 00 DD 00 13   [ 1] 3546 	mov	_dec_info+18, _d_nseg+0
                                   3547 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: for (t = 0; t < NB; t++) {
      0095AF 0F 04            [ 1] 3548 	clr	(0x04, sp)
      0095B1 5F               [ 1] 3549 	clrw	x
      0095B2 1F 05            [ 2] 3550 	ldw	(0x05, sp), x
      0095B4                       3551 00117$:
                                   3552 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1069: int8_t kb = known_bit(t);
      0095B4 1E 05            [ 2] 3553 	ldw	x, (0x05, sp)
      0095B6 CD 81 37         [ 4] 3554 	call	_known_bit
                                   3555 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1070: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
      0095B9 6B 03            [ 1] 3556 	ld	(0x03, sp), a
      0095BB 2B 1F            [ 1] 3557 	jrmi	00118$
      0095BD 1E 05            [ 2] 3558 	ldw	x, (0x05, sp)
      0095BF 54               [ 2] 3559 	srlw	x
      0095C0 54               [ 2] 3560 	srlw	x
      0095C1 54               [ 2] 3561 	srlw	x
      0095C2 1C 00 C1         [ 2] 3562 	addw	x, #(_d_bits+0)
      0095C5 F6               [ 1] 3563 	ld	a, (x)
      0095C6 97               [ 1] 3564 	ld	xl, a
      0095C7 7B 06            [ 1] 3565 	ld	a, (0x06, sp)
      0095C9 A4 07            [ 1] 3566 	and	a, #0x07
      0095CB 27 06            [ 1] 3567 	jreq	00207$
      0095CD                       3568 00206$:
      0095CD 41               [ 1] 3569 	exg	a, xl
      0095CE 44               [ 1] 3570 	srl	a
      0095CF 41               [ 1] 3571 	exg	a, xl
      0095D0 4A               [ 1] 3572 	dec	a
      0095D1 26 FA            [ 1] 3573 	jrne	00206$
      0095D3                       3574 00207$:
      0095D3 9F               [ 1] 3575 	ld	a, xl
      0095D4 A4 01            [ 1] 3576 	and	a, #0x01
      0095D6 11 03            [ 1] 3577 	cp	a, (0x03, sp)
      0095D8 27 02            [ 1] 3578 	jreq	00118$
      0095DA 0C 04            [ 1] 3579 	inc	(0x04, sp)
      0095DC                       3580 00118$:
                                   3581 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: for (t = 0; t < NB; t++) {
      0095DC 1E 05            [ 2] 3582 	ldw	x, (0x05, sp)
      0095DE 5C               [ 1] 3583 	incw	x
      0095DF 1F 05            [ 2] 3584 	ldw	(0x05, sp), x
      0095E1 A3 00 C0         [ 2] 3585 	cpw	x, #0x00c0
      0095E4 25 CE            [ 1] 3586 	jrc	00117$
                                   3587 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1072: dec_info.violations = viol;
      0095E6 AE 00 0E         [ 2] 3588 	ldw	x, #(_dec_info+13)
      0095E9 7B 04            [ 1] 3589 	ld	a, (0x04, sp)
      0095EB F7               [ 1] 3590 	ld	(x), a
                                   3591 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1073: if (viol > 0)               { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
      0095EC 0D 04            [ 1] 3592 	tnz	(0x04, sp)
      0095EE 27 07            [ 1] 3593 	jreq	00109$
      0095F0 35 02 00 02      [ 1] 3594 	mov	_dec_info+1, #0x02
      0095F4 4F               [ 1] 3595 	clr	a
      0095F5 20 26            [ 2] 3596 	jra	00119$
      0095F7                       3597 00109$:
                                   3598 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1074: if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
      0095F7 CE 00 D9         [ 2] 3599 	ldw	x, _d_infeas+0
      0095FA A3 00 04         [ 2] 3600 	cpw	x, #0x0004
      0095FD 23 07            [ 2] 3601 	jrule	00111$
      0095FF 35 03 00 02      [ 1] 3602 	mov	_dec_info+1, #0x03
      009603 4F               [ 1] 3603 	clr	a
      009604 20 17            [ 2] 3604 	jra	00119$
      009606                       3605 00111$:
                                   3606 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1075: if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
      009606 CE 00 DB         [ 2] 3607 	ldw	x, _d_laberr+0
      009609 A3 00 06         [ 2] 3608 	cpw	x, #0x0006
      00960C 23 07            [ 2] 3609 	jrule	00113$
      00960E 35 04 00 02      [ 1] 3610 	mov	_dec_info+1, #0x04
      009612 4F               [ 1] 3611 	clr	a
      009613 20 08            [ 2] 3612 	jra	00119$
      009615                       3613 00113$:
                                   3614 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1076: dec_info.path = chase(out);                                      /* R5..R8 inside */
      009615 1E 0B            [ 2] 3615 	ldw	x, (0x0b, sp)
      009617 CD 94 76         [ 4] 3616 	call	_chase
      00961A 1E 01            [ 2] 3617 	ldw	x, (0x01, sp)
      00961C F7               [ 1] 3618 	ld	(x), a
                                   3619 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1077: return dec_info.path;
      00961D                       3620 00119$:
                                   3621 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1078: }
      00961D 1E 07            [ 2] 3622 	ldw	x, (7, sp)
      00961F 5B 0C            [ 2] 3623 	addw	sp, #12
      009621 FC               [ 2] 3624 	jp	(x)
                                   3625 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1080: int16_t dec_eps_centi(void)
                                   3626 ;	-----------------------------------------
                                   3627 ;	 function dec_eps_centi
                                   3628 ;	-----------------------------------------
      009622                       3629 _dec_eps_centi:
      009622 52 08            [ 2] 3630 	sub	sp, #8
                                   3631 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1085: return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
      009624 CE 00 0A         [ 2] 3632 	ldw	x, _dec_info+9
      009627 1F 03            [ 2] 3633 	ldw	(0x03, sp), x
      009629 90 5F            [ 1] 3634 	clrw	y
      00962B A6 CD            [ 1] 3635 	ld	a, #0xcd
      00962D 10 04            [ 1] 3636 	sub	a, (0x04, sp)
      00962F 6B 08            [ 1] 3637 	ld	(0x08, sp), a
      009631 A6 CC            [ 1] 3638 	ld	a, #0xcc
      009633 12 03            [ 1] 3639 	sbc	a, (0x03, sp)
      009635 6B 07            [ 1] 3640 	ld	(0x07, sp), a
      009637 5F               [ 1] 3641 	clrw	x
      009638 24 01            [ 1] 3642 	jrnc	00103$
      00963A 5A               [ 2] 3643 	decw	x
      00963B                       3644 00103$:
      00963B 90 89            [ 2] 3645 	pushw	y
      00963D 7B 0A            [ 1] 3646 	ld	a, (0x0a, sp)
      00963F 88               [ 1] 3647 	push	a
      009640 7B 0A            [ 1] 3648 	ld	a, (0x0a, sp)
      009642 88               [ 1] 3649 	push	a
      009643 89               [ 2] 3650 	pushw	x
      009644 4B 10            [ 1] 3651 	push	#0x10
      009646 4B 27            [ 1] 3652 	push	#0x27
      009648 5F               [ 1] 3653 	clrw	x
      009649 89               [ 2] 3654 	pushw	x
                                   3655 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1086: / (int32_t)dec_info.K);
      00964A CD 9B 29         [ 4] 3656 	call	__mullong
      00964D 5B 08            [ 2] 3657 	addw	sp, #8
      00964F 17 07            [ 2] 3658 	ldw	(0x07, sp), y
      009651 90 85            [ 2] 3659 	popw	y
      009653 7B 04            [ 1] 3660 	ld	a, (0x04, sp)
      009655 88               [ 1] 3661 	push	a
      009656 7B 04            [ 1] 3662 	ld	a, (0x04, sp)
      009658 88               [ 1] 3663 	push	a
      009659 90 89            [ 2] 3664 	pushw	y
      00965B 89               [ 2] 3665 	pushw	x
      00965C 1E 0B            [ 2] 3666 	ldw	x, (0x0b, sp)
      00965E 89               [ 2] 3667 	pushw	x
      00965F CD 9A A5         [ 4] 3668 	call	__divslong
                                   3669 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1087: }
      009662 5B 10            [ 2] 3670 	addw	sp, #16
      009664 81               [ 4] 3671 	ret
                                   3672 	.area CODE
                                   3673 	.area CONST
                                   3674 	.area CONST
      00802D                       3675 _HDR:
      00802D FF                    3676 	.db #0xff	; 255
      00802E 00                    3677 	.db #0x00	; 0
      00802F AA                    3678 	.db #0xaa	; 170
      008030 65                    3679 	.db #0x65	; 101	'e'
                                   3680 	.area CODE
                                   3681 	.area CONST
      008031                       3682 _TRL:
      008031 9A                    3683 	.db #0x9a	; 154
      008032 55                    3684 	.db #0x55	; 85	'U'
      008033 00                    3685 	.db #0x00	; 0
      008034 FF                    3686 	.db #0xff	; 255
                                   3687 	.area CODE
                                   3688 	.area INITIALIZER
                                   3689 	.area CABS (ABS)
