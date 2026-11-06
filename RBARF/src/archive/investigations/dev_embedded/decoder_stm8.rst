                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module decoder
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _ws_decode
                                     11 	.globl _g_phases
                                     12 ;--------------------------------------------------------
                                     13 ; ram data
                                     14 ;--------------------------------------------------------
                                     15 	.area DATA
      000132                         16 _g_K:
      000132                         17 	.ds 2
      000134                         18 _g_tau:
      000134                         19 	.ds 2
      000136                         20 _c_lo0:
      000136                         21 	.ds 2
      000138                         22 _c_hi0:
      000138                         23 	.ds 2
      00013A                         24 _c_lo1:
      00013A                         25 	.ds 2
      00013C                         26 _c_hi1:
      00013C                         27 	.ds 2
      00013E                         28 _c_n0:
      00013E                         29 	.ds 1
      00013F                         30 _c_n1:
      00013F                         31 	.ds 1
      000140                         32 _c_h0c:
      000140                         33 	.ds 2
      000142                         34 _c_h1c:
      000142                         35 	.ds 2
      000144                         36 _c_d56:
      000144                         37 	.ds 2
      000146                         38 _c_hist:
      000146                         39 	.ds 128
      0001C6                         40 _c_labx0:
      0001C6                         41 	.ds 4
      0001CA                         42 _c_labx1:
      0001CA                         43 	.ds 4
      0001CE                         44 _c_labx0b:
      0001CE                         45 	.ds 4
      0001D2                         46 _c_labx1b:
      0001D2                         47 	.ds 4
      0001D6                         48 _c_c0:
      0001D6                         49 	.ds 4
      0001DA                         50 _c_gap56:
      0001DA                         51 	.ds 4
      0001DE                         52 _d_bits:
      0001DE                         53 	.ds 56
      000216                         54 _d_conf:
      000216                         55 	.ds 56
      00024E                         56 _d_tied:
      00024E                         57 	.ds 56
      000286                         58 _d_knife:
      000286                         59 	.ds 64
      0002C6                         60 _d_nknife:
      0002C6                         61 	.ds 1
      0002C7                         62 _d_resolved:
      0002C7                         63 	.ds 32
      0002E7                         64 _d_nres:
      0002E7                         65 	.ds 1
      0002E8                         66 _d_infeas:
      0002E8                         67 	.ds 1
      0002E9                         68 _d_laberr:
      0002E9                         69 	.ds 1
      0002EA                         70 _d_nseg:
      0002EA                         71 	.ds 2
      0002EC                         72 _d_costs:
      0002EC                         73 	.ds 32
      00030C                         74 _d_inter:
      00030C                         75 	.ds 2
                                     76 ;--------------------------------------------------------
                                     77 ; ram data
                                     78 ;--------------------------------------------------------
                                     79 	.area INITIALIZED
      00030E                         80 _g_phases::
      00030E                         81 	.ds 1
                                     82 ;--------------------------------------------------------
                                     83 ; absolute external ram data
                                     84 ;--------------------------------------------------------
                                     85 	.area DABS (ABS)
                                     86 
                                     87 ; default segment ordering for linker
                                     88 	.area HOME
                                     89 	.area GSINIT
                                     90 	.area GSFINAL
                                     91 	.area CONST
                                     92 	.area INITIALIZER
                                     93 	.area CODE
                                     94 
                                     95 ;--------------------------------------------------------
                                     96 ; global & static initialisations
                                     97 ;--------------------------------------------------------
                                     98 	.area HOME
                                     99 	.area GSINIT
                                    100 	.area GSFINAL
                                    101 	.area GSINIT
                                    102 ;--------------------------------------------------------
                                    103 ; Home
                                    104 ;--------------------------------------------------------
                                    105 	.area HOME
                                    106 	.area HOME
                                    107 ;--------------------------------------------------------
                                    108 ; code
                                    109 ;--------------------------------------------------------
                                    110 	.area CODE
                                    111 ;	decoder.c: 87: static int8_t known_bit(uint16_t t)
                                    112 ;	-----------------------------------------
                                    113 ;	 function known_bit
                                    114 ;	-----------------------------------------
      008193                        115 _known_bit:
      008193 88               [ 1]  116 	push	a
                                    117 ;	decoder.c: 89: if (t < 32)
      008194 90 93            [ 1]  118 	ldw	y, x
      008196 A3 00 20         [ 2]  119 	cpw	x, #0x0020
      008199 24 20            [ 1]  120 	jrnc	00102$
                                    121 ;	decoder.c: 90: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
      00819B 93               [ 1]  122 	ldw	x, y
      00819C 54               [ 2]  123 	srlw	x
      00819D 54               [ 2]  124 	srlw	x
      00819E 54               [ 2]  125 	srlw	x
      00819F 1C 80 3D         [ 2]  126 	addw	x, #(_HDR+0)
      0081A2 F6               [ 1]  127 	ld	a, (x)
      0081A3 97               [ 1]  128 	ld	xl, a
      0081A4 90 9F            [ 1]  129 	ld	a, yl
      0081A6 A4 07            [ 1]  130 	and	a, #0x07
      0081A8 6B 01            [ 1]  131 	ld	(0x01, sp), a
      0081AA A6 07            [ 1]  132 	ld	a, #0x07
      0081AC 10 01            [ 1]  133 	sub	a, (0x01, sp)
      0081AE 27 06            [ 1]  134 	jreq	00125$
      0081B0                        135 00124$:
      0081B0 41               [ 1]  136 	exg	a, xl
      0081B1 44               [ 1]  137 	srl	a
      0081B2 41               [ 1]  138 	exg	a, xl
      0081B3 4A               [ 1]  139 	dec	a
      0081B4 26 FA            [ 1]  140 	jrne	00124$
      0081B6                        141 00125$:
      0081B6 9F               [ 1]  142 	ld	a, xl
      0081B7 A4 01            [ 1]  143 	and	a, #0x01
      0081B9 20 2A            [ 2]  144 	jra	00105$
      0081BB                        145 00102$:
                                    146 ;	decoder.c: 91: if (t >= NB - 32) {
      0081BB A3 01 A0         [ 2]  147 	cpw	x, #0x01a0
      0081BE 25 23            [ 1]  148 	jrc	00104$
                                    149 ;	decoder.c: 92: uint16_t u = t - (NB - 32);
      0081C0 1D 01 A0         [ 2]  150 	subw	x, #0x01a0
                                    151 ;	decoder.c: 93: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
      0081C3 90 93            [ 1]  152 	ldw	y, x
      0081C5 54               [ 2]  153 	srlw	x
      0081C6 54               [ 2]  154 	srlw	x
      0081C7 54               [ 2]  155 	srlw	x
      0081C8 1C 80 41         [ 2]  156 	addw	x, #(_TRL+0)
      0081CB F6               [ 1]  157 	ld	a, (x)
      0081CC 97               [ 1]  158 	ld	xl, a
      0081CD 90 9F            [ 1]  159 	ld	a, yl
      0081CF A4 07            [ 1]  160 	and	a, #0x07
      0081D1 6B 01            [ 1]  161 	ld	(0x01, sp), a
      0081D3 A6 07            [ 1]  162 	ld	a, #0x07
      0081D5 10 01            [ 1]  163 	sub	a, (0x01, sp)
      0081D7 27 06            [ 1]  164 	jreq	00128$
      0081D9                        165 00127$:
      0081D9 41               [ 1]  166 	exg	a, xl
      0081DA 44               [ 1]  167 	srl	a
      0081DB 41               [ 1]  168 	exg	a, xl
      0081DC 4A               [ 1]  169 	dec	a
      0081DD 26 FA            [ 1]  170 	jrne	00127$
      0081DF                        171 00128$:
      0081DF 9F               [ 1]  172 	ld	a, xl
      0081E0 A4 01            [ 1]  173 	and	a, #0x01
                                    174 ;	decoder.c: 95: return -1;
      0081E2 C5                     175 	.byte 0xc5
      0081E3                        176 00104$:
      0081E3 A6 FF            [ 1]  177 	ld	a, #0xff
      0081E5                        178 00105$:
                                    179 ;	decoder.c: 96: }
      0081E5 5B 01            [ 2]  180 	addw	sp, #1
      0081E7 81               [ 4]  181 	ret
                                    182 ;	decoder.c: 120: static void ps_init(PStream *p, const uint8_t *cap, uint16_t ncap)
                                    183 ;	-----------------------------------------
                                    184 ;	 function ps_init
                                    185 ;	-----------------------------------------
      0081E8                        186 _ps_init:
      0081E8 52 04            [ 2]  187 	sub	sp, #4
                                    188 ;	decoder.c: 122: p->cap = cap; p->ncap = ncap;
      0081EA 90 93            [ 1]  189 	ldw	y, x
      0081EC 7B 08            [ 1]  190 	ld	a, (0x08, sp)
      0081EE E7 01            [ 1]  191 	ld	(0x1, x), a
      0081F0 7B 07            [ 1]  192 	ld	a, (0x07, sp)
      0081F2 F7               [ 1]  193 	ld	(x), a
      0081F3 93               [ 1]  194 	ldw	x, y
      0081F4 5C               [ 1]  195 	incw	x
      0081F5 5C               [ 1]  196 	incw	x
      0081F6 7B 0A            [ 1]  197 	ld	a, (0x0a, sp)
      0081F8 E7 01            [ 1]  198 	ld	(0x1, x), a
      0081FA 7B 09            [ 1]  199 	ld	a, (0x09, sp)
      0081FC F7               [ 1]  200 	ld	(x), a
                                    201 ;	decoder.c: 123: p->i = 0; p->s = 0; p->tbase = 0; p->wsum = 0;
      0081FD 93               [ 1]  202 	ldw	x, y
      0081FE 1C 00 04         [ 2]  203 	addw	x, #0x0004
      008201 6F 01            [ 1]  204 	clr	(0x1, x)
      008203 7F               [ 1]  205 	clr	(x)
      008204 93               [ 1]  206 	ldw	x, y
      008205 6F 06            [ 1]  207 	clr	(0x0006, x)
      008207 93               [ 1]  208 	ldw	x, y
      008208 1C 00 07         [ 2]  209 	addw	x, #0x0007
      00820B 6F 01            [ 1]  210 	clr	(0x1, x)
      00820D 7F               [ 1]  211 	clr	(x)
      00820E 93               [ 1]  212 	ldw	x, y
      00820F 1C 00 09         [ 2]  213 	addw	x, #0x0009
      008212 6F 01            [ 1]  214 	clr	(0x1, x)
      008214 7F               [ 1]  215 	clr	(x)
                                    216 ;	decoder.c: 124: p->t_prev = 0; p->have_prev = 0;
      008215 93               [ 1]  217 	ldw	x, y
      008216 1C 00 0B         [ 2]  218 	addw	x, #0x000b
      008219 6F 01            [ 1]  219 	clr	(0x1, x)
      00821B 7F               [ 1]  220 	clr	(x)
      00821C 93               [ 1]  221 	ldw	x, y
      00821D 6F 0D            [ 1]  222 	clr	(0x000d, x)
                                    223 ;	decoder.c: 125: p->in_pulse = 0; p->seen = 0; p->done = 0; p->low_run = 0;
      00821F 93               [ 1]  224 	ldw	x, y
      008220 6F 0E            [ 1]  225 	clr	(0x000e, x)
      008222 93               [ 1]  226 	ldw	x, y
      008223 6F 0F            [ 1]  227 	clr	(0x000f, x)
      008225 93               [ 1]  228 	ldw	x, y
      008226 6F 10            [ 1]  229 	clr	(0x0010, x)
      008228 93               [ 1]  230 	ldw	x, y
      008229 1C 00 11         [ 2]  231 	addw	x, #0x0011
      00822C 6F 01            [ 1]  232 	clr	(0x1, x)
      00822E 7F               [ 1]  233 	clr	(x)
                                    234 ;	decoder.c: 126: p->ra = p->rb = p->fa = 0; p->sfa = 0;
      00822F 93               [ 1]  235 	ldw	x, y
      008230 1C 00 13         [ 2]  236 	addw	x, #0x0013
      008233 1F 01            [ 2]  237 	ldw	(0x01, sp), x
      008235 93               [ 1]  238 	ldw	x, y
      008236 1C 00 15         [ 2]  239 	addw	x, #0x0015
      008239 1F 03            [ 2]  240 	ldw	(0x03, sp), x
      00823B 93               [ 1]  241 	ldw	x, y
      00823C 1C 00 17         [ 2]  242 	addw	x, #0x0017
      00823F 6F 01            [ 1]  243 	clr	(0x1, x)
      008241 7F               [ 1]  244 	clr	(x)
      008242 1E 03            [ 2]  245 	ldw	x, (0x03, sp)
      008244 6F 01            [ 1]  246 	clr	(0x1, x)
      008246 7F               [ 1]  247 	clr	(x)
      008247 1E 01            [ 2]  248 	ldw	x, (0x01, sp)
      008249 6F 01            [ 1]  249 	clr	(0x1, x)
      00824B 7F               [ 1]  250 	clr	(x)
      00824C 93               [ 1]  251 	ldw	x, y
      00824D 6F 19            [ 1]  252 	clr	(0x0019, x)
                                    253 ;	decoder.c: 127: }
      00824F 1E 05            [ 2]  254 	ldw	x, (5, sp)
      008251 5B 0A            [ 2]  255 	addw	sp, #10
      008253 FC               [ 2]  256 	jp	(x)
                                    257 ;	decoder.c: 130: static uint8_t ps_next(PStream *p, Pulse *out)
                                    258 ;	-----------------------------------------
                                    259 ;	 function ps_next
                                    260 ;	-----------------------------------------
      008254                        261 _ps_next:
      008254 52 35            [ 2]  262 	sub	sp, #53
                                    263 ;	decoder.c: 132: while (!p->done) {
      008256 1F 34            [ 2]  264 	ldw	(0x34, sp), x
      008258 1C 00 0E         [ 2]  265 	addw	x, #0x000e
      00825B 1F 03            [ 2]  266 	ldw	(0x03, sp), x
      00825D 1E 34            [ 2]  267 	ldw	x, (0x34, sp)
      00825F 1C 00 09         [ 2]  268 	addw	x, #0x0009
      008262 1F 05            [ 2]  269 	ldw	(0x05, sp), x
      008264 1E 34            [ 2]  270 	ldw	x, (0x34, sp)
      008266 1C 00 0F         [ 2]  271 	addw	x, #0x000f
      008269 1F 07            [ 2]  272 	ldw	(0x07, sp), x
      00826B 1E 34            [ 2]  273 	ldw	x, (0x34, sp)
      00826D 1C 00 10         [ 2]  274 	addw	x, #0x0010
      008270 1F 09            [ 2]  275 	ldw	(0x09, sp), x
      008272 1E 34            [ 2]  276 	ldw	x, (0x34, sp)
      008274 1C 00 0D         [ 2]  277 	addw	x, #0x000d
      008277 1F 0B            [ 2]  278 	ldw	(0x0b, sp), x
      008279 1E 34            [ 2]  279 	ldw	x, (0x34, sp)
      00827B 1C 00 0B         [ 2]  280 	addw	x, #0x000b
      00827E 1F 0D            [ 2]  281 	ldw	(0x0d, sp), x
      008280 16 07            [ 2]  282 	ldw	y, (0x07, sp)
      008282 17 0F            [ 2]  283 	ldw	(0x0f, sp), y
      008284                        284 00133$:
      008284 1E 09            [ 2]  285 	ldw	x, (0x09, sp)
      008286 F6               [ 1]  286 	ld	a, (x)
                                    287 ;	decoder.c: 147: p->fa = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum + 2);
      008287 1E 34            [ 2]  288 	ldw	x, (0x34, sp)
      008289 1C 00 17         [ 2]  289 	addw	x, #0x0017
      00828C 1F 11            [ 2]  290 	ldw	(0x11, sp), x
                                    291 ;	decoder.c: 149: p->sfa = 5;
      00828E 1E 34            [ 2]  292 	ldw	x, (0x34, sp)
      008290 1C 00 19         [ 2]  293 	addw	x, #0x0019
      008293 1F 13            [ 2]  294 	ldw	(0x13, sp), x
                                    295 ;	decoder.c: 175: p->ra = p->have_prev ? p->t_prev
      008295 1E 34            [ 2]  296 	ldw	x, (0x34, sp)
      008297 1C 00 13         [ 2]  297 	addw	x, #0x0013
      00829A 1F 15            [ 2]  298 	ldw	(0x15, sp), x
                                    299 ;	decoder.c: 177: p->rb = t;
      00829C 1E 34            [ 2]  300 	ldw	x, (0x34, sp)
      00829E 1C 00 15         [ 2]  301 	addw	x, #0x0015
      0082A1 1F 17            [ 2]  302 	ldw	(0x17, sp), x
                                    303 ;	decoder.c: 186: out->ra = p->ra; out->rb = p->rb;
      0082A3 16 38            [ 2]  304 	ldw	y, (0x38, sp)
      0082A5 17 19            [ 2]  305 	ldw	(0x19, sp), y
      0082A7 93               [ 1]  306 	ldw	x, y
      0082A8 5C               [ 1]  307 	incw	x
      0082A9 5C               [ 1]  308 	incw	x
      0082AA 1F 1B            [ 2]  309 	ldw	(0x1b, sp), x
                                    310 ;	decoder.c: 187: out->fa = p->fa; out->fb = t; out->sfa = p->sfa;
      0082AC 93               [ 1]  311 	ldw	x, y
      0082AD 1C 00 04         [ 2]  312 	addw	x, #0x0004
      0082B0 1F 1D            [ 2]  313 	ldw	(0x1d, sp), x
      0082B2 93               [ 1]  314 	ldw	x, y
      0082B3 1C 00 06         [ 2]  315 	addw	x, #0x0006
      0082B6 1F 1F            [ 2]  316 	ldw	(0x1f, sp), x
      0082B8 93               [ 1]  317 	ldw	x, y
      0082B9 1C 00 08         [ 2]  318 	addw	x, #0x0008
      0082BC 1F 21            [ 2]  319 	ldw	(0x21, sp), x
                                    320 ;	decoder.c: 132: while (!p->done) {
      0082BE 4D               [ 1]  321 	tnz	a
      0082BF 27 03            [ 1]  322 	jreq	00320$
      0082C1 CC 85 37         [ 2]  323 	jp	00135$
      0082C4                        324 00320$:
                                    325 ;	decoder.c: 133: uint8_t v, s = p->s;
      0082C4 1E 34            [ 2]  326 	ldw	x, (0x34, sp)
      0082C6 1C 00 06         [ 2]  327 	addw	x, #0x0006
      0082C9 1F 23            [ 2]  328 	ldw	(0x23, sp), x
      0082CB F6               [ 1]  329 	ld	a, (x)
      0082CC 6B 25            [ 1]  330 	ld	(0x25, sp), a
                                    331 ;	decoder.c: 135: if (p->i >= p->ncap) break;
      0082CE 1E 34            [ 2]  332 	ldw	x, (0x34, sp)
      0082D0 1C 00 04         [ 2]  333 	addw	x, #0x0004
      0082D3 1F 26            [ 2]  334 	ldw	(0x26, sp), x
      0082D5 FE               [ 2]  335 	ldw	x, (x)
      0082D6 1F 28            [ 2]  336 	ldw	(0x28, sp), x
      0082D8 1E 34            [ 2]  337 	ldw	x, (0x34, sp)
      0082DA EE 02            [ 2]  338 	ldw	x, (0x2, x)
      0082DC 1F 01            [ 2]  339 	ldw	(0x01, sp), x
      0082DE 1E 28            [ 2]  340 	ldw	x, (0x28, sp)
      0082E0 13 01            [ 2]  341 	cpw	x, (0x01, sp)
      0082E2 25 03            [ 1]  342 	jrc	00321$
      0082E4 CC 85 37         [ 2]  343 	jp	00135$
      0082E7                        344 00321$:
                                    345 ;	decoder.c: 137: uint8_t bt = p->cap[p->i + 1];
      0082E7 16 34            [ 2]  346 	ldw	y, (0x34, sp)
      0082E9 17 2A            [ 2]  347 	ldw	(0x2a, sp), y
                                    348 ;	decoder.c: 139: p->t_prev = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum);
      0082EB 1E 34            [ 2]  349 	ldw	x, (0x34, sp)
      0082ED 1C 00 07         [ 2]  350 	addw	x, #0x0007
      0082F0 1F 2C            [ 2]  351 	ldw	(0x2c, sp), x
                                    352 ;	decoder.c: 141: p->low_run = (uint16_t)(p->low_run + 8);
      0082F2 1E 34            [ 2]  353 	ldw	x, (0x34, sp)
      0082F4 1C 00 11         [ 2]  354 	addw	x, #0x0011
      0082F7 1F 2E            [ 2]  355 	ldw	(0x2e, sp), x
                                    356 ;	decoder.c: 136: if (s == 6 && p->i + 1 < p->ncap) {
      0082F9 1E 28            [ 2]  357 	ldw	x, (0x28, sp)
      0082FB 5C               [ 1]  358 	incw	x
      0082FC 1F 30            [ 2]  359 	ldw	(0x30, sp), x
      0082FE 13 01            [ 2]  360 	cpw	x, (0x01, sp)
      008300 4F               [ 1]  361 	clr	a
      008301 49               [ 1]  362 	rlc	a
      008302 6B 32            [ 1]  363 	ld	(0x32, sp), a
      008304 7B 25            [ 1]  364 	ld	a, (0x25, sp)
      008306 A1 06            [ 1]  365 	cp	a, #0x06
      008308 27 03            [ 1]  366 	jreq	00324$
      00830A CC 83 CA         [ 2]  367 	jp	00113$
      00830D                        368 00324$:
      00830D 0D 32            [ 1]  369 	tnz	(0x32, sp)
      00830F 26 03            [ 1]  370 	jrne	00325$
      008311 CC 83 CA         [ 2]  371 	jp	00113$
      008314                        372 00325$:
                                    373 ;	decoder.c: 137: uint8_t bt = p->cap[p->i + 1];
      008314 1E 2A            [ 2]  374 	ldw	x, (0x2a, sp)
      008316 FE               [ 2]  375 	ldw	x, (x)
      008317 72 FB 30         [ 2]  376 	addw	x, (0x30, sp)
      00831A F6               [ 1]  377 	ld	a, (x)
                                    378 ;	decoder.c: 138: if (bt == 0x00 && !p->in_pulse) {
      00831B 6B 33            [ 1]  379 	ld	(0x33, sp), a
      00831D 26 55            [ 1]  380 	jrne	00107$
      00831F 1E 03            [ 2]  381 	ldw	x, (0x03, sp)
      008321 F6               [ 1]  382 	ld	a, (x)
      008322 26 50            [ 1]  383 	jrne	00107$
                                    384 ;	decoder.c: 139: p->t_prev = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum);
      008324 1E 2C            [ 2]  385 	ldw	x, (0x2c, sp)
      008326 FE               [ 2]  386 	ldw	x, (x)
      008327 1C 00 3D         [ 2]  387 	addw	x, #0x003d
      00832A 16 05            [ 2]  388 	ldw	y, (0x05, sp)
      00832C 90 FE            [ 2]  389 	ldw	y, (y)
      00832E 1F 32            [ 2]  390 	ldw	(0x32, sp), x
      008330 72 F9 32         [ 2]  391 	addw	y, (0x32, sp)
      008333 1E 0D            [ 2]  392 	ldw	x, (0x0d, sp)
      008335 FF               [ 2]  393 	ldw	(x), y
                                    394 ;	decoder.c: 140: p->have_prev = 1;
      008336 1E 0B            [ 2]  395 	ldw	x, (0x0b, sp)
      008338 A6 01            [ 1]  396 	ld	a, #0x01
      00833A F7               [ 1]  397 	ld	(x), a
                                    398 ;	decoder.c: 141: p->low_run = (uint16_t)(p->low_run + 8);
      00833B 1E 2E            [ 2]  399 	ldw	x, (0x2e, sp)
      00833D FE               [ 2]  400 	ldw	x, (x)
      00833E 1C 00 08         [ 2]  401 	addw	x, #0x0008
      008341 16 2E            [ 2]  402 	ldw	y, (0x2e, sp)
      008343 90 FF            [ 2]  403 	ldw	(y), x
                                    404 ;	decoder.c: 142: p->i++; p->tbase += LOOP_CY;    /* s stays 6 */
      008345 1E 26            [ 2]  405 	ldw	x, (0x26, sp)
      008347 FE               [ 2]  406 	ldw	x, (x)
      008348 5C               [ 1]  407 	incw	x
      008349 16 26            [ 2]  408 	ldw	y, (0x26, sp)
      00834B 90 FF            [ 2]  409 	ldw	(y), x
      00834D 1E 2C            [ 2]  410 	ldw	x, (0x2c, sp)
      00834F FE               [ 2]  411 	ldw	x, (x)
      008350 1C 00 28         [ 2]  412 	addw	x, #0x0028
      008353 16 2C            [ 2]  413 	ldw	y, (0x2c, sp)
      008355 90 FF            [ 2]  414 	ldw	(y), x
                                    415 ;	decoder.c: 143: if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
      008357 1E 07            [ 2]  416 	ldw	x, (0x07, sp)
      008359 F6               [ 1]  417 	ld	a, (x)
      00835A 6B 33            [ 1]  418 	ld	(0x33, sp), a
      00835C 26 03            [ 1]  419 	jrne	00328$
      00835E CC 82 84         [ 2]  420 	jp	00133$
      008361                        421 00328$:
      008361 1E 2E            [ 2]  422 	ldw	x, (0x2e, sp)
      008363 FE               [ 2]  423 	ldw	x, (x)
      008364 A3 00 C8         [ 2]  424 	cpw	x, #0x00c8
      008367 24 03            [ 1]  425 	jrnc	00329$
      008369 CC 82 84         [ 2]  426 	jp	00133$
      00836C                        427 00329$:
      00836C 1E 09            [ 2]  428 	ldw	x, (0x09, sp)
      00836E A6 01            [ 1]  429 	ld	a, #0x01
      008370 F7               [ 1]  430 	ld	(x), a
      008371 CC 85 37         [ 2]  431 	jp	00135$
                                    432 ;	decoder.c: 144: continue;
      008374                        433 00107$:
                                    434 ;	decoder.c: 146: if (bt == 0xFF && p->in_pulse) {
      008374 7B 33            [ 1]  435 	ld	a, (0x33, sp)
      008376 4C               [ 1]  436 	inc	a
      008377 26 51            [ 1]  437 	jrne	00113$
      008379 1E 03            [ 2]  438 	ldw	x, (0x03, sp)
      00837B F6               [ 1]  439 	ld	a, (x)
      00837C 27 4C            [ 1]  440 	jreq	00113$
                                    441 ;	decoder.c: 147: p->fa = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum + 2);
      00837E 1E 2C            [ 2]  442 	ldw	x, (0x2c, sp)
      008380 FE               [ 2]  443 	ldw	x, (x)
      008381 16 05            [ 2]  444 	ldw	y, (0x05, sp)
      008383 90 FE            [ 2]  445 	ldw	y, (y)
      008385 72 A9 00 3F      [ 2]  446 	addw	y, #0x003f
      008389 1F 32            [ 2]  447 	ldw	(0x32, sp), x
      00838B 72 F9 32         [ 2]  448 	addw	y, (0x32, sp)
      00838E 1E 11            [ 2]  449 	ldw	x, (0x11, sp)
      008390 FF               [ 2]  450 	ldw	(x), y
                                    451 ;	decoder.c: 148: p->wsum += 2;                   /* sum of W over the octet */
      008391 1E 05            [ 2]  452 	ldw	x, (0x05, sp)
      008393 FE               [ 2]  453 	ldw	x, (x)
      008394 5C               [ 1]  454 	incw	x
      008395 5C               [ 1]  455 	incw	x
      008396 51               [ 1]  456 	exgw	x, y
      008397 1E 05            [ 2]  457 	ldw	x, (0x05, sp)
      008399 FF               [ 2]  458 	ldw	(x), y
                                    459 ;	decoder.c: 149: p->sfa = 5;
      00839A 1E 13            [ 2]  460 	ldw	x, (0x13, sp)
      00839C A6 05            [ 1]  461 	ld	a, #0x05
      00839E F7               [ 1]  462 	ld	(x), a
                                    463 ;	decoder.c: 150: p->low_run = 0;
      00839F 1E 2E            [ 2]  464 	ldw	x, (0x2e, sp)
      0083A1 6F 01            [ 1]  465 	clr	(0x1, x)
      0083A3 7F               [ 1]  466 	clr	(x)
                                    467 ;	decoder.c: 151: p->seen = 1;
      0083A4 1E 07            [ 2]  468 	ldw	x, (0x07, sp)
      0083A6 A6 01            [ 1]  469 	ld	a, #0x01
      0083A8 F7               [ 1]  470 	ld	(x), a
                                    471 ;	decoder.c: 152: p->t_prev = p->fa;
      0083A9 1E 11            [ 2]  472 	ldw	x, (0x11, sp)
      0083AB FE               [ 2]  473 	ldw	x, (x)
      0083AC 16 0D            [ 2]  474 	ldw	y, (0x0d, sp)
      0083AE 90 FF            [ 2]  475 	ldw	(y), x
                                    476 ;	decoder.c: 153: p->have_prev = 1;
      0083B0 1E 0B            [ 2]  477 	ldw	x, (0x0b, sp)
      0083B2 A6 01            [ 1]  478 	ld	a, #0x01
      0083B4 F7               [ 1]  479 	ld	(x), a
                                    480 ;	decoder.c: 154: p->i++; p->tbase += LOOP_CY;
      0083B5 1E 26            [ 2]  481 	ldw	x, (0x26, sp)
      0083B7 FE               [ 2]  482 	ldw	x, (x)
      0083B8 5C               [ 1]  483 	incw	x
      0083B9 16 26            [ 2]  484 	ldw	y, (0x26, sp)
      0083BB 90 FF            [ 2]  485 	ldw	(y), x
      0083BD 1E 2C            [ 2]  486 	ldw	x, (0x2c, sp)
      0083BF FE               [ 2]  487 	ldw	x, (x)
      0083C0 1C 00 28         [ 2]  488 	addw	x, #0x0028
      0083C3 16 2C            [ 2]  489 	ldw	y, (0x2c, sp)
      0083C5 90 FF            [ 2]  490 	ldw	(y), x
                                    491 ;	decoder.c: 155: continue;
      0083C7 CC 82 84         [ 2]  492 	jp	00133$
      0083CA                        493 00113$:
                                    494 ;	decoder.c: 158: if (s < 6) {
      0083CA 7B 25            [ 1]  495 	ld	a, (0x25, sp)
      0083CC A1 06            [ 1]  496 	cp	a, #0x06
      0083CE 24 1B            [ 1]  497 	jrnc	00118$
                                    498 ;	decoder.c: 159: v = (uint8_t)((p->cap[p->i] >> (5 - s)) & 1);
      0083D0 1E 2A            [ 2]  499 	ldw	x, (0x2a, sp)
      0083D2 FE               [ 2]  500 	ldw	x, (x)
      0083D3 72 FB 28         [ 2]  501 	addw	x, (0x28, sp)
      0083D6 F6               [ 1]  502 	ld	a, (x)
      0083D7 97               [ 1]  503 	ld	xl, a
      0083D8 A6 05            [ 1]  504 	ld	a, #0x05
      0083DA 10 25            [ 1]  505 	sub	a, (0x25, sp)
      0083DC 27 06            [ 1]  506 	jreq	00336$
      0083DE                        507 00335$:
      0083DE 41               [ 1]  508 	exg	a, xl
      0083DF 44               [ 1]  509 	srl	a
      0083E0 41               [ 1]  510 	exg	a, xl
      0083E1 4A               [ 1]  511 	dec	a
      0083E2 26 FA            [ 1]  512 	jrne	00335$
      0083E4                        513 00336$:
      0083E4 9F               [ 1]  514 	ld	a, xl
      0083E5 A4 01            [ 1]  515 	and	a, #0x01
      0083E7 6B 29            [ 1]  516 	ld	(0x29, sp), a
      0083E9 20 3A            [ 2]  517 	jra	00119$
      0083EB                        518 00118$:
                                    519 ;	decoder.c: 161: if (p->i + 1 >= p->ncap) {      /* last loop: BS lost */
      0083EB 7B 32            [ 1]  520 	ld	a, (0x32, sp)
      0083ED 26 17            [ 1]  521 	jrne	00116$
                                    522 ;	decoder.c: 162: p->i++; p->s = 0; p->tbase += LOOP_CY;
      0083EF 1E 28            [ 2]  523 	ldw	x, (0x28, sp)
      0083F1 5C               [ 1]  524 	incw	x
      0083F2 16 26            [ 2]  525 	ldw	y, (0x26, sp)
      0083F4 90 FF            [ 2]  526 	ldw	(y), x
      0083F6 1E 23            [ 2]  527 	ldw	x, (0x23, sp)
      0083F8 7F               [ 1]  528 	clr	(x)
      0083F9 1E 2C            [ 2]  529 	ldw	x, (0x2c, sp)
      0083FB FE               [ 2]  530 	ldw	x, (x)
      0083FC 1C 00 28         [ 2]  531 	addw	x, #0x0028
      0083FF 16 2C            [ 2]  532 	ldw	y, (0x2c, sp)
      008401 90 FF            [ 2]  533 	ldw	(y), x
                                    534 ;	decoder.c: 163: continue;
      008403 CC 82 84         [ 2]  535 	jp	00133$
      008406                        536 00116$:
                                    537 ;	decoder.c: 165: v = (uint8_t)((p->cap[p->i + 1] >> (7 - (s - 6))) & 1);
      008406 1E 2A            [ 2]  538 	ldw	x, (0x2a, sp)
      008408 FE               [ 2]  539 	ldw	x, (x)
      008409 72 FB 30         [ 2]  540 	addw	x, (0x30, sp)
      00840C F6               [ 1]  541 	ld	a, (x)
      00840D 97               [ 1]  542 	ld	xl, a
      00840E 7B 25            [ 1]  543 	ld	a, (0x25, sp)
      008410 A0 06            [ 1]  544 	sub	a, #0x06
      008412 6B 33            [ 1]  545 	ld	(0x33, sp), a
      008414 A6 07            [ 1]  546 	ld	a, #0x07
      008416 10 33            [ 1]  547 	sub	a, (0x33, sp)
      008418 27 06            [ 1]  548 	jreq	00339$
      00841A                        549 00338$:
      00841A 41               [ 1]  550 	exg	a, xl
      00841B 44               [ 1]  551 	srl	a
      00841C 41               [ 1]  552 	exg	a, xl
      00841D 4A               [ 1]  553 	dec	a
      00841E 26 FA            [ 1]  554 	jrne	00338$
      008420                        555 00339$:
      008420 9F               [ 1]  556 	ld	a, xl
      008421 A4 01            [ 1]  557 	and	a, #0x01
      008423 6B 29            [ 1]  558 	ld	(0x29, sp), a
      008425                        559 00119$:
                                    560 ;	decoder.c: 167: t = (uint16_t)(p->tbase + O_CY[s] + p->wsum);
      008425 1E 2C            [ 2]  561 	ldw	x, (0x2c, sp)
      008427 FE               [ 2]  562 	ldw	x, (x)
      008428 90 93            [ 1]  563 	ldw	y, x
      00842A 5F               [ 1]  564 	clrw	x
      00842B 7B 25            [ 1]  565 	ld	a, (0x25, sp)
      00842D 97               [ 1]  566 	ld	xl, a
      00842E D6 80 2D         [ 1]  567 	ld	a, (_O_CY+0, x)
      008431 6B 33            [ 1]  568 	ld	(0x33, sp), a
      008433 0F 32            [ 1]  569 	clr	(0x32, sp)
      008435 72 F9 32         [ 2]  570 	addw	y, (0x32, sp)
      008438 1E 05            [ 2]  571 	ldw	x, (0x05, sp)
      00843A 1F 2A            [ 2]  572 	ldw	(0x2a, sp), x
      00843C 1E 05            [ 2]  573 	ldw	x, (0x05, sp)
      00843E FE               [ 2]  574 	ldw	x, (x)
      00843F 17 30            [ 2]  575 	ldw	(0x30, sp), y
      008441 72 FB 30         [ 2]  576 	addw	x, (0x30, sp)
      008444 1F 32            [ 2]  577 	ldw	(0x32, sp), x
                                    578 ;	decoder.c: 169: if (s == 7) { p->s = 0; p->i++; p->tbase += LOOP_CY; }
      008446 7B 25            [ 1]  579 	ld	a, (0x25, sp)
      008448 A1 07            [ 1]  580 	cp	a, #0x07
      00844A 26 17            [ 1]  581 	jrne	00121$
      00844C 1E 23            [ 2]  582 	ldw	x, (0x23, sp)
      00844E 7F               [ 1]  583 	clr	(x)
      00844F 1E 26            [ 2]  584 	ldw	x, (0x26, sp)
      008451 FE               [ 2]  585 	ldw	x, (x)
      008452 5C               [ 1]  586 	incw	x
      008453 16 26            [ 2]  587 	ldw	y, (0x26, sp)
      008455 90 FF            [ 2]  588 	ldw	(y), x
      008457 1E 2C            [ 2]  589 	ldw	x, (0x2c, sp)
      008459 FE               [ 2]  590 	ldw	x, (x)
      00845A 1C 00 28         [ 2]  591 	addw	x, #0x0028
      00845D 16 2C            [ 2]  592 	ldw	y, (0x2c, sp)
      00845F 90 FF            [ 2]  593 	ldw	(y), x
      008461 20 06            [ 2]  594 	jra	00122$
      008463                        595 00121$:
                                    596 ;	decoder.c: 170: else        { p->s = (uint8_t)(s + 1); }
      008463 7B 25            [ 1]  597 	ld	a, (0x25, sp)
      008465 4C               [ 1]  598 	inc	a
      008466 1E 23            [ 2]  599 	ldw	x, (0x23, sp)
      008468 F7               [ 1]  600 	ld	(x), a
      008469                        601 00122$:
                                    602 ;	decoder.c: 171: if (v) {
      008469 0D 29            [ 1]  603 	tnz	(0x29, sp)
      00846B 27 64            [ 1]  604 	jreq	00131$
                                    605 ;	decoder.c: 172: p->wsum += W_CY[s];
      00846D 1E 2A            [ 2]  606 	ldw	x, (0x2a, sp)
      00846F FE               [ 2]  607 	ldw	x, (x)
      008470 90 93            [ 1]  608 	ldw	y, x
      008472 5F               [ 1]  609 	clrw	x
      008473 7B 25            [ 1]  610 	ld	a, (0x25, sp)
      008475 97               [ 1]  611 	ld	xl, a
      008476 1C 80 35         [ 2]  612 	addw	x, #(_W_CY+0)
      008479 F6               [ 1]  613 	ld	a, (x)
      00847A 6B 31            [ 1]  614 	ld	(0x31, sp), a
      00847C 49               [ 1]  615 	rlc	a
      00847D 4F               [ 1]  616 	clr	a
      00847E A2 00            [ 1]  617 	sbc	a, #0x00
      008480 6B 30            [ 1]  618 	ld	(0x30, sp), a
      008482 72 F9 30         [ 2]  619 	addw	y, (0x30, sp)
      008485 1E 2A            [ 2]  620 	ldw	x, (0x2a, sp)
      008487 FF               [ 2]  621 	ldw	(x), y
                                    622 ;	decoder.c: 173: if (!p->in_pulse) {
      008488 1E 03            [ 2]  623 	ldw	x, (0x03, sp)
      00848A F6               [ 1]  624 	ld	a, (x)
      00848B 26 2E            [ 1]  625 	jrne	00124$
                                    626 ;	decoder.c: 174: p->in_pulse = 1;
      00848D 1E 03            [ 2]  627 	ldw	x, (0x03, sp)
      00848F A6 01            [ 1]  628 	ld	a, #0x01
      008491 F7               [ 1]  629 	ld	(x), a
                                    630 ;	decoder.c: 175: p->ra = p->have_prev ? p->t_prev
      008492 1E 0B            [ 2]  631 	ldw	x, (0x0b, sp)
      008494 F6               [ 1]  632 	ld	a, (x)
      008495 27 07            [ 1]  633 	jreq	00140$
      008497 1E 0D            [ 2]  634 	ldw	x, (0x0d, sp)
      008499 FE               [ 2]  635 	ldw	x, (x)
      00849A 1F 30            [ 2]  636 	ldw	(0x30, sp), x
      00849C 20 13            [ 2]  637 	jra	00141$
      00849E                        638 00140$:
                                    639 ;	decoder.c: 176: : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
      00849E 16 32            [ 2]  640 	ldw	y, (0x32, sp)
      0084A0 17 30            [ 2]  641 	ldw	(0x30, sp), y
      0084A2 93               [ 1]  642 	ldw	x, y
      0084A3 A3 00 04         [ 2]  643 	cpw	x, #0x0004
      0084A6 25 06            [ 1]  644 	jrc	00142$
      0084A8 1E 30            [ 2]  645 	ldw	x, (0x30, sp)
      0084AA 1D 00 04         [ 2]  646 	subw	x, #0x0004
      0084AD 21                     647 	.byte 0x21
      0084AE                        648 00142$:
      0084AE 5F               [ 1]  649 	clrw	x
      0084AF                        650 00143$:
      0084AF 1F 30            [ 2]  651 	ldw	(0x30, sp), x
      0084B1                        652 00141$:
      0084B1 16 30            [ 2]  653 	ldw	y, (0x30, sp)
      0084B3 1E 15            [ 2]  654 	ldw	x, (0x15, sp)
      0084B5 FF               [ 2]  655 	ldw	(x), y
                                    656 ;	decoder.c: 177: p->rb = t;
      0084B6 1E 17            [ 2]  657 	ldw	x, (0x17, sp)
      0084B8 16 32            [ 2]  658 	ldw	y, (0x32, sp)
      0084BA FF               [ 2]  659 	ldw	(x), y
      0084BB                        660 00124$:
                                    661 ;	decoder.c: 179: p->fa = t;
      0084BB 1E 11            [ 2]  662 	ldw	x, (0x11, sp)
      0084BD 16 32            [ 2]  663 	ldw	y, (0x32, sp)
      0084BF FF               [ 2]  664 	ldw	(x), y
                                    665 ;	decoder.c: 180: p->sfa = s;
      0084C0 1E 13            [ 2]  666 	ldw	x, (0x13, sp)
      0084C2 7B 25            [ 1]  667 	ld	a, (0x25, sp)
      0084C4 F7               [ 1]  668 	ld	(x), a
                                    669 ;	decoder.c: 181: p->low_run = 0;
      0084C5 1E 2E            [ 2]  670 	ldw	x, (0x2e, sp)
      0084C7 6F 01            [ 1]  671 	clr	(0x1, x)
      0084C9 7F               [ 1]  672 	clr	(x)
                                    673 ;	decoder.c: 182: p->seen = 1;
      0084CA 1E 07            [ 2]  674 	ldw	x, (0x07, sp)
      0084CC A6 01            [ 1]  675 	ld	a, #0x01
      0084CE F7               [ 1]  676 	ld	(x), a
      0084CF 20 59            [ 2]  677 	jra	00132$
      0084D1                        678 00131$:
                                    679 ;	decoder.c: 184: if (p->in_pulse) {
      0084D1 1E 03            [ 2]  680 	ldw	x, (0x03, sp)
      0084D3 F6               [ 1]  681 	ld	a, (x)
      0084D4 27 38            [ 1]  682 	jreq	00126$
                                    683 ;	decoder.c: 185: p->in_pulse = 0;
      0084D6 1E 03            [ 2]  684 	ldw	x, (0x03, sp)
      0084D8 7F               [ 1]  685 	clr	(x)
                                    686 ;	decoder.c: 186: out->ra = p->ra; out->rb = p->rb;
      0084D9 1E 15            [ 2]  687 	ldw	x, (0x15, sp)
      0084DB FE               [ 2]  688 	ldw	x, (x)
      0084DC 16 19            [ 2]  689 	ldw	y, (0x19, sp)
      0084DE 90 FF            [ 2]  690 	ldw	(y), x
      0084E0 1E 17            [ 2]  691 	ldw	x, (0x17, sp)
      0084E2 FE               [ 2]  692 	ldw	x, (x)
      0084E3 16 1B            [ 2]  693 	ldw	y, (0x1b, sp)
      0084E5 90 FF            [ 2]  694 	ldw	(y), x
                                    695 ;	decoder.c: 187: out->fa = p->fa; out->fb = t; out->sfa = p->sfa;
      0084E7 1E 11            [ 2]  696 	ldw	x, (0x11, sp)
      0084E9 FE               [ 2]  697 	ldw	x, (x)
      0084EA 16 1D            [ 2]  698 	ldw	y, (0x1d, sp)
      0084EC 90 FF            [ 2]  699 	ldw	(y), x
      0084EE 1E 1F            [ 2]  700 	ldw	x, (0x1f, sp)
      0084F0 16 32            [ 2]  701 	ldw	y, (0x32, sp)
      0084F2 FF               [ 2]  702 	ldw	(x), y
      0084F3 1E 13            [ 2]  703 	ldw	x, (0x13, sp)
      0084F5 F6               [ 1]  704 	ld	a, (x)
      0084F6 1E 21            [ 2]  705 	ldw	x, (0x21, sp)
      0084F8 F7               [ 1]  706 	ld	(x), a
                                    707 ;	decoder.c: 188: p->t_prev = t; p->have_prev = 1;
      0084F9 1E 0D            [ 2]  708 	ldw	x, (0x0d, sp)
      0084FB 16 32            [ 2]  709 	ldw	y, (0x32, sp)
      0084FD FF               [ 2]  710 	ldw	(x), y
      0084FE 1E 0B            [ 2]  711 	ldw	x, (0x0b, sp)
      008500 A6 01            [ 1]  712 	ld	a, #0x01
      008502 F7               [ 1]  713 	ld	(x), a
                                    714 ;	decoder.c: 189: p->low_run = 1;
      008503 1E 2E            [ 2]  715 	ldw	x, (0x2e, sp)
      008505 90 AE 00 01      [ 2]  716 	ldw	y, #0x0001
      008509 FF               [ 2]  717 	ldw	(x), y
                                    718 ;	decoder.c: 190: return 1;
      00850A A6 01            [ 1]  719 	ld	a, #0x01
      00850C 20 60            [ 2]  720 	jra	00138$
      00850E                        721 00126$:
                                    722 ;	decoder.c: 192: p->low_run++;
      00850E 1E 2E            [ 2]  723 	ldw	x, (0x2e, sp)
      008510 FE               [ 2]  724 	ldw	x, (x)
      008511 5C               [ 1]  725 	incw	x
      008512 16 2E            [ 2]  726 	ldw	y, (0x2e, sp)
      008514 90 FF            [ 2]  727 	ldw	(y), x
                                    728 ;	decoder.c: 193: if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
      008516 1E 0F            [ 2]  729 	ldw	x, (0x0f, sp)
      008518 F6               [ 1]  730 	ld	a, (x)
      008519 27 0F            [ 1]  731 	jreq	00132$
      00851B 1E 2E            [ 2]  732 	ldw	x, (0x2e, sp)
      00851D FE               [ 2]  733 	ldw	x, (x)
      00851E A3 00 C8         [ 2]  734 	cpw	x, #0x00c8
      008521 25 07            [ 1]  735 	jrc	00132$
      008523 1E 09            [ 2]  736 	ldw	x, (0x09, sp)
      008525 A6 01            [ 1]  737 	ld	a, #0x01
      008527 F7               [ 1]  738 	ld	(x), a
      008528 20 0D            [ 2]  739 	jra	00135$
      00852A                        740 00132$:
                                    741 ;	decoder.c: 195: p->t_prev = t;
      00852A 1E 0D            [ 2]  742 	ldw	x, (0x0d, sp)
      00852C 16 32            [ 2]  743 	ldw	y, (0x32, sp)
      00852E FF               [ 2]  744 	ldw	(x), y
                                    745 ;	decoder.c: 196: p->have_prev = 1;
      00852F 1E 0B            [ 2]  746 	ldw	x, (0x0b, sp)
      008531 A6 01            [ 1]  747 	ld	a, #0x01
      008533 F7               [ 1]  748 	ld	(x), a
      008534 CC 82 84         [ 2]  749 	jp	00133$
      008537                        750 00135$:
                                    751 ;	decoder.c: 198: if (p->in_pulse) {                       /* capture ended high */
      008537 1E 03            [ 2]  752 	ldw	x, (0x03, sp)
      008539 F6               [ 1]  753 	ld	a, (x)
      00853A 27 2C            [ 1]  754 	jreq	00137$
                                    755 ;	decoder.c: 199: p->in_pulse = 0;
      00853C 1E 03            [ 2]  756 	ldw	x, (0x03, sp)
      00853E 7F               [ 1]  757 	clr	(x)
                                    758 ;	decoder.c: 200: out->ra = p->ra; out->rb = p->rb;
      00853F 1E 15            [ 2]  759 	ldw	x, (0x15, sp)
      008541 FE               [ 2]  760 	ldw	x, (x)
      008542 16 19            [ 2]  761 	ldw	y, (0x19, sp)
      008544 90 FF            [ 2]  762 	ldw	(y), x
      008546 1E 17            [ 2]  763 	ldw	x, (0x17, sp)
      008548 FE               [ 2]  764 	ldw	x, (x)
      008549 16 1B            [ 2]  765 	ldw	y, (0x1b, sp)
      00854B 90 FF            [ 2]  766 	ldw	(y), x
                                    767 ;	decoder.c: 201: out->fa = p->fa; out->fb = (uint16_t)(p->fa + FIRST_BR);
      00854D 1E 11            [ 2]  768 	ldw	x, (0x11, sp)
      00854F FE               [ 2]  769 	ldw	x, (x)
      008550 16 1D            [ 2]  770 	ldw	y, (0x1d, sp)
      008552 90 FF            [ 2]  771 	ldw	(y), x
      008554 1E 11            [ 2]  772 	ldw	x, (0x11, sp)
      008556 FE               [ 2]  773 	ldw	x, (x)
      008557 1C 00 04         [ 2]  774 	addw	x, #0x0004
      00855A 16 1F            [ 2]  775 	ldw	y, (0x1f, sp)
      00855C 90 FF            [ 2]  776 	ldw	(y), x
                                    777 ;	decoder.c: 202: out->sfa = p->sfa;
      00855E 1E 13            [ 2]  778 	ldw	x, (0x13, sp)
      008560 F6               [ 1]  779 	ld	a, (x)
      008561 1E 21            [ 2]  780 	ldw	x, (0x21, sp)
      008563 F7               [ 1]  781 	ld	(x), a
                                    782 ;	decoder.c: 203: return 1;
      008564 A6 01            [ 1]  783 	ld	a, #0x01
      008566 20 06            [ 2]  784 	jra	00138$
      008568                        785 00137$:
                                    786 ;	decoder.c: 205: p->done = 1;
      008568 1E 09            [ 2]  787 	ldw	x, (0x09, sp)
      00856A A6 01            [ 1]  788 	ld	a, #0x01
      00856C F7               [ 1]  789 	ld	(x), a
                                    790 ;	decoder.c: 206: return 0;
      00856D 4F               [ 1]  791 	clr	a
      00856E                        792 00138$:
                                    793 ;	decoder.c: 207: }
      00856E 1E 36            [ 2]  794 	ldw	x, (54, sp)
      008570 5B 39            [ 2]  795 	addw	sp, #57
      008572 FC               [ 2]  796 	jp	(x)
                                    797 ;	decoder.c: 239: static uint32_t map_y(uint16_t t)
                                    798 ;	-----------------------------------------
                                    799 ;	 function map_y
                                    800 ;	-----------------------------------------
      008573                        801 _map_y:
      008573 52 08            [ 2]  802 	sub	sp, #8
                                    803 ;	decoder.c: 241: return (uint32_t)((uint32_t)t * g_K >> KQ) + (uint32_t)(int32_t)g_tau;
      008575 90 CE 01 32      [ 2]  804 	ldw	y, _g_K+0
      008579 90 89            [ 2]  805 	pushw	y
      00857B CD 9E 2B         [ 4]  806 	call	___muluint2ulong
      00857E 5B 02            [ 2]  807 	addw	sp, #2
      008580 51               [ 1]  808 	exgw	x, y
      008581 A6 0B            [ 1]  809 	ld	a, #0x0b
      008583                        810 00103$:
      008583 54               [ 2]  811 	srlw	x
      008584 90 56            [ 2]  812 	rrcw	y
      008586 4A               [ 1]  813 	dec	a
      008587 26 FA            [ 1]  814 	jrne	00103$
      008589 1F 01            [ 2]  815 	ldw	(0x01, sp), x
      00858B CE 01 34         [ 2]  816 	ldw	x, _g_tau+0
      00858E 9E               [ 1]  817 	ld	a, xh
      00858F 49               [ 1]  818 	rlc	a
      008590 4F               [ 1]  819 	clr	a
      008591 A2 00            [ 1]  820 	sbc	a, #0x00
      008593 1F 07            [ 2]  821 	ldw	(0x07, sp), x
      008595 97               [ 1]  822 	ld	xl, a
      008596 49               [ 1]  823 	rlc	a
      008597 4F               [ 1]  824 	clr	a
      008598 A2 00            [ 1]  825 	sbc	a, #0x00
      00859A 72 F9 07         [ 2]  826 	addw	y, (0x07, sp)
      00859D 88               [ 1]  827 	push	a
      00859E 9F               [ 1]  828 	ld	a, xl
      00859F 19 03            [ 1]  829 	adc	a, (0x03, sp)
      0085A1 97               [ 1]  830 	ld	xl, a
      0085A2 84               [ 1]  831 	pop	a
      0085A3 19 01            [ 1]  832 	adc	a, (0x01, sp)
      0085A5 95               [ 1]  833 	ld	xh, a
      0085A6 51               [ 1]  834 	exgw	x, y
                                    835 ;	decoder.c: 243: }
      0085A7 5B 08            [ 2]  836 	addw	sp, #8
      0085A9 81               [ 4]  837 	ret
                                    838 ;	decoder.c: 247: static uint8_t seed(const uint8_t *cap, uint16_t ncap)
                                    839 ;	-----------------------------------------
                                    840 ;	 function seed
                                    841 ;	-----------------------------------------
      0085AA                        842 _seed:
      0085AA 52 29            [ 2]  843 	sub	sp, #41
      0085AC 51               [ 1]  844 	exgw	x, y
                                    845 ;	decoder.c: 252: uint16_t r0m = 0, flm = 0;
      0085AD 5F               [ 1]  846 	clrw	x
      0085AE 1F 24            [ 2]  847 	ldw	(0x24, sp), x
      0085B0 5F               [ 1]  848 	clrw	x
      0085B1 1F 26            [ 2]  849 	ldw	(0x26, sp), x
                                    850 ;	decoder.c: 254: ps_init(&ps, cap, ncap);
      0085B3 1E 2C            [ 2]  851 	ldw	x, (0x2c, sp)
      0085B5 89               [ 2]  852 	pushw	x
      0085B6 90 89            [ 2]  853 	pushw	y
      0085B8 96               [ 1]  854 	ldw	x, sp
      0085B9 1C 00 05         [ 2]  855 	addw	x, #5
      0085BC CD 81 E8         [ 4]  856 	call	_ps_init
                                    857 ;	decoder.c: 255: while (ps_next(&ps, &p)) {
      0085BF 5F               [ 1]  858 	clrw	x
      0085C0 1F 28            [ 2]  859 	ldw	(0x28, sp), x
      0085C2                        860 00103$:
      0085C2 96               [ 1]  861 	ldw	x, sp
      0085C3 1C 00 1B         [ 2]  862 	addw	x, #27
      0085C6 89               [ 2]  863 	pushw	x
      0085C7 96               [ 1]  864 	ldw	x, sp
      0085C8 1C 00 03         [ 2]  865 	addw	x, #3
      0085CB CD 82 54         [ 4]  866 	call	_ps_next
      0085CE 4D               [ 1]  867 	tnz	a
      0085CF 27 23            [ 1]  868 	jreq	00105$
                                    869 ;	decoder.c: 256: if (np == 0) r0m = (uint16_t)((p.ra + p.rb) >> 1);
      0085D1 1E 28            [ 2]  870 	ldw	x, (0x28, sp)
      0085D3 26 0C            [ 1]  871 	jrne	00102$
      0085D5 1E 1B            [ 2]  872 	ldw	x, (0x1b, sp)
      0085D7 16 1D            [ 2]  873 	ldw	y, (0x1d, sp)
      0085D9 17 26            [ 2]  874 	ldw	(0x26, sp), y
      0085DB 72 FB 26         [ 2]  875 	addw	x, (0x26, sp)
      0085DE 54               [ 2]  876 	srlw	x
      0085DF 1F 24            [ 2]  877 	ldw	(0x24, sp), x
      0085E1                        878 00102$:
                                    879 ;	decoder.c: 257: flm = (uint16_t)((p.fa + p.fb) >> 1);
      0085E1 16 1F            [ 2]  880 	ldw	y, (0x1f, sp)
      0085E3 17 26            [ 2]  881 	ldw	(0x26, sp), y
      0085E5 1E 21            [ 2]  882 	ldw	x, (0x21, sp)
      0085E7 72 FB 26         [ 2]  883 	addw	x, (0x26, sp)
      0085EA 54               [ 2]  884 	srlw	x
      0085EB 1F 26            [ 2]  885 	ldw	(0x26, sp), x
                                    886 ;	decoder.c: 258: np++;
      0085ED 1E 28            [ 2]  887 	ldw	x, (0x28, sp)
      0085EF 5C               [ 1]  888 	incw	x
      0085F0 1F 28            [ 2]  889 	ldw	(0x28, sp), x
      0085F2 20 CE            [ 2]  890 	jra	00103$
      0085F4                        891 00105$:
                                    892 ;	decoder.c: 260: if (np < 8 || flm <= r0m) return 0;
      0085F4 1E 28            [ 2]  893 	ldw	x, (0x28, sp)
      0085F6 A3 00 08         [ 2]  894 	cpw	x, #0x0008
      0085F9 25 06            [ 1]  895 	jrc	00106$
      0085FB 1E 26            [ 2]  896 	ldw	x, (0x26, sp)
      0085FD 13 24            [ 2]  897 	cpw	x, (0x24, sp)
      0085FF 22 03            [ 1]  898 	jrugt	00107$
      008601                        899 00106$:
      008601 4F               [ 1]  900 	clr	a
      008602 20 60            [ 2]  901 	jra	00112$
      008604                        902 00107$:
                                    903 ;	decoder.c: 262: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
      008604 16 26            [ 2]  904 	ldw	y, (0x26, sp)
      008606 72 F2 24         [ 2]  905 	subw	y, (0x24, sp)
      008609 5F               [ 1]  906 	clrw	x
      00860A 90 89            [ 2]  907 	pushw	y
      00860C 89               [ 2]  908 	pushw	x
      00860D 4B 00            [ 1]  909 	push	#0x00
      00860F 4B A0            [ 1]  910 	push	#0xa0
      008611 4B F9            [ 1]  911 	push	#0xf9
      008613 4B 1B            [ 1]  912 	push	#0x1b
                                    913 ;	decoder.c: 263: if (K < K_MIN || K > K_MAX) return 0;
      008615 CD 9E A9         [ 4]  914 	call	__divulong
      008618 5B 08            [ 2]  915 	addw	sp, #8
      00861A 1F 28            [ 2]  916 	ldw	(0x28, sp), x
      00861C 17 26            [ 2]  917 	ldw	(0x26, sp), y
      00861E 1E 28            [ 2]  918 	ldw	x, (0x28, sp)
      008620 A3 B3 B0         [ 2]  919 	cpw	x, #0xb3b0
      008623 7B 27            [ 1]  920 	ld	a, (0x27, sp)
      008625 A2 00            [ 1]  921 	sbc	a, #0x00
      008627 7B 26            [ 1]  922 	ld	a, (0x26, sp)
      008629 A2 00            [ 1]  923 	sbc	a, #0x00
      00862B 25 0D            [ 1]  924 	jrc	00109$
      00862D AE EA 60         [ 2]  925 	ldw	x, #0xea60
      008630 13 28            [ 2]  926 	cpw	x, (0x28, sp)
      008632 4F               [ 1]  927 	clr	a
      008633 12 27            [ 1]  928 	sbc	a, (0x27, sp)
      008635 4F               [ 1]  929 	clr	a
      008636 12 26            [ 1]  930 	sbc	a, (0x26, sp)
      008638 24 03            [ 1]  931 	jrnc	00110$
      00863A                        932 00109$:
      00863A 4F               [ 1]  933 	clr	a
      00863B 20 27            [ 2]  934 	jra	00112$
      00863D                        935 00110$:
                                    936 ;	decoder.c: 264: g_K = (uint16_t)K;
      00863D 1E 28            [ 2]  937 	ldw	x, (0x28, sp)
      00863F CF 01 32         [ 2]  938 	ldw	_g_K+0, x
                                    939 ;	decoder.c: 265: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
      008642 16 24            [ 2]  940 	ldw	y, (0x24, sp)
      008644 CE 01 32         [ 2]  941 	ldw	x, _g_K+0
      008647 89               [ 2]  942 	pushw	x
      008648 93               [ 1]  943 	ldw	x, y
      008649 CD 9E 2B         [ 4]  944 	call	___muluint2ulong
      00864C 5B 02            [ 2]  945 	addw	sp, #2
      00864E 51               [ 1]  946 	exgw	x, y
      00864F A6 0B            [ 1]  947 	ld	a, #0x0b
      008651                        948 00162$:
      008651 54               [ 2]  949 	srlw	x
      008652 90 56            [ 2]  950 	rrcw	y
      008654 4A               [ 1]  951 	dec	a
      008655 26 FA            [ 1]  952 	jrne	00162$
      008657 17 28            [ 2]  953 	ldw	(0x28, sp), y
      008659 AE 02 00         [ 2]  954 	ldw	x, #0x0200
      00865C 72 F0 28         [ 2]  955 	subw	x, (0x28, sp)
      00865F CF 01 34         [ 2]  956 	ldw	_g_tau+0, x
                                    957 ;	decoder.c: 266: return 1;
      008662 A6 01            [ 1]  958 	ld	a, #0x01
      008664                        959 00112$:
                                    960 ;	decoder.c: 267: }
      008664 1E 2A            [ 2]  961 	ldw	x, (42, sp)
      008666 5B 2D            [ 2]  962 	addw	sp, #45
      008668 FC               [ 2]  963 	jp	(x)
                                    964 ;	decoder.c: 271: static void refine(const uint8_t *cap, uint16_t ncap)
                                    965 ;	-----------------------------------------
                                    966 ;	 function refine
                                    967 ;	-----------------------------------------
      008669                        968 _refine:
      008669 52 4B            [ 2]  969 	sub	sp, #75
      00866B 51               [ 1]  970 	exgw	x, y
                                    971 ;	decoder.c: 278: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
      00866C 5F               [ 1]  972 	clrw	x
      00866D 1F 3A            [ 2]  973 	ldw	(0x3a, sp), x
      00866F 1F 38            [ 2]  974 	ldw	(0x38, sp), x
      008671 5F               [ 1]  975 	clrw	x
      008672 1F 3E            [ 2]  976 	ldw	(0x3e, sp), x
      008674 1F 3C            [ 2]  977 	ldw	(0x3c, sp), x
                                    978 ;	decoder.c: 279: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
      008676 5F               [ 1]  979 	clrw	x
      008677 1F 42            [ 2]  980 	ldw	(0x42, sp), x
      008679 1F 40            [ 2]  981 	ldw	(0x40, sp), x
      00867B 5F               [ 1]  982 	clrw	x
      00867C 1F 46            [ 2]  983 	ldw	(0x46, sp), x
      00867E 1F 44            [ 2]  984 	ldw	(0x44, sp), x
                                    985 ;	decoder.c: 283: ps_init(&ps, cap, ncap);
      008680 1E 4E            [ 2]  986 	ldw	x, (0x4e, sp)
      008682 89               [ 2]  987 	pushw	x
      008683 90 89            [ 2]  988 	pushw	y
      008685 96               [ 1]  989 	ldw	x, sp
      008686 1C 00 05         [ 2]  990 	addw	x, #5
      008689 CD 81 E8         [ 4]  991 	call	_ps_init
                                    992 ;	decoder.c: 284: while (ps_next(&ps, &p)) {
      00868C 5F               [ 1]  993 	clrw	x
      00868D 1F 48            [ 2]  994 	ldw	(0x48, sp), x
      00868F 5F               [ 1]  995 	clrw	x
      008690 1F 4A            [ 2]  996 	ldw	(0x4a, sp), x
      008692                        997 00106$:
      008692 96               [ 1]  998 	ldw	x, sp
      008693 1C 00 1B         [ 2]  999 	addw	x, #27
      008696 89               [ 2] 1000 	pushw	x
      008697 96               [ 1] 1001 	ldw	x, sp
      008698 1C 00 03         [ 2] 1002 	addw	x, #3
      00869B CD 82 54         [ 4] 1003 	call	_ps_next
      00869E 6B 37            [ 1] 1004 	ld	(0x37, sp), a
      0086A0 26 03            [ 1] 1005 	jrne	00176$
      0086A2 CC 87 54         [ 2] 1006 	jp	00108$
      0086A5                       1007 00176$:
                                   1008 ;	decoder.c: 287: y = map_y((uint16_t)((p.ra + p.rb) >> 1));
      0086A5 1E 1B            [ 2] 1009 	ldw	x, (0x1b, sp)
      0086A7 16 1D            [ 2] 1010 	ldw	y, (0x1d, sp)
      0086A9 17 36            [ 2] 1011 	ldw	(0x36, sp), y
      0086AB 72 FB 36         [ 2] 1012 	addw	x, (0x36, sp)
      0086AE 54               [ 2] 1013 	srlw	x
      0086AF CD 85 73         [ 4] 1014 	call	_map_y
      0086B2 1F 32            [ 2] 1015 	ldw	(0x32, sp), x
      0086B4 17 30            [ 2] 1016 	ldw	(0x30, sp), y
                                   1017 ;	decoder.c: 288: if (y > y_end) break;
      0086B6 AE 82 A4         [ 2] 1018 	ldw	x, #0x82a4
      0086B9 13 32            [ 2] 1019 	cpw	x, (0x32, sp)
      0086BB A6 03            [ 1] 1020 	ld	a, #0x03
      0086BD 12 31            [ 1] 1021 	sbc	a, (0x31, sp)
      0086BF 4F               [ 1] 1022 	clr	a
      0086C0 12 30            [ 1] 1023 	sbc	a, (0x30, sp)
      0086C2 24 03            [ 1] 1024 	jrnc	00177$
      0086C4 CC 87 54         [ 2] 1025 	jp	00108$
      0086C7                       1026 00177$:
                                   1027 ;	decoder.c: 289: q = (y + BIT_H) >> BIT_SH;
      0086C7 7B 32            [ 1] 1028 	ld	a, (0x32, sp)
      0086C9 AB 01            [ 1] 1029 	add	a, #0x01
      0086CB 1E 30            [ 2] 1030 	ldw	x, (0x30, sp)
      0086CD 24 01            [ 1] 1031 	jrnc	00178$
      0086CF 5C               [ 1] 1032 	incw	x
      0086D0                       1033 00178$:
      0086D0 02               [ 1] 1034 	rlwa	x
      0086D1 0F 34            [ 1] 1035 	clr	(0x34, sp)
      0086D3 44               [ 1] 1036 	srl	a
      0086D4 56               [ 2] 1037 	rrcw	x
                                   1038 ;	decoder.c: 290: e = (int16_t)((int32_t)y - (int32_t)(q << BIT_SH));
      0086D5 16 32            [ 2] 1039 	ldw	y, (0x32, sp)
      0086D7 17 36            [ 2] 1040 	ldw	(0x36, sp), y
      0086D9 4F               [ 1] 1041 	clr	a
      0086DA 02               [ 1] 1042 	rlwa	x
      0086DB 58               [ 2] 1043 	sllw	x
      0086DC 50               [ 2] 1044 	negw	x
      0086DD 72 FB 36         [ 2] 1045 	addw	x, (0x36, sp)
                                   1046 ;	decoder.c: 291: if (y < mid_u) { n_lo++; se_lo += e; sy_lo += y; }
      0086E0 1F 36            [ 2] 1047 	ldw	(0x36, sp), x
      0086E2 5F               [ 1] 1048 	clrw	x
      0086E3 0D 36            [ 1] 1049 	tnz	(0x36, sp)
      0086E5 2A 01            [ 1] 1050 	jrpl	00179$
      0086E7 5A               [ 2] 1051 	decw	x
      0086E8                       1052 00179$:
      0086E8 7B 33            [ 1] 1053 	ld	a, (0x33, sp)
      0086EA A1 00            [ 1] 1054 	cp	a, #0x00
      0086EC 7B 32            [ 1] 1055 	ld	a, (0x32, sp)
      0086EE A2 C2            [ 1] 1056 	sbc	a, #0xc2
      0086F0 7B 31            [ 1] 1057 	ld	a, (0x31, sp)
      0086F2 A2 01            [ 1] 1058 	sbc	a, #0x01
      0086F4 7B 30            [ 1] 1059 	ld	a, (0x30, sp)
      0086F6 A2 00            [ 1] 1060 	sbc	a, #0x00
      0086F8 24 2D            [ 1] 1061 	jrnc	00104$
      0086FA 16 48            [ 2] 1062 	ldw	y, (0x48, sp)
      0086FC 90 5C            [ 1] 1063 	incw	y
      0086FE 17 48            [ 2] 1064 	ldw	(0x48, sp), y
      008700 16 36            [ 2] 1065 	ldw	y, (0x36, sp)
      008702 72 F9 3A         [ 2] 1066 	addw	y, (0x3a, sp)
      008705 17 3A            [ 2] 1067 	ldw	(0x3a, sp), y
      008707 9F               [ 1] 1068 	ld	a, xl
      008708 19 39            [ 1] 1069 	adc	a, (0x39, sp)
      00870A 6B 39            [ 1] 1070 	ld	(0x39, sp), a
      00870C 9E               [ 1] 1071 	ld	a, xh
      00870D 19 38            [ 1] 1072 	adc	a, (0x38, sp)
      00870F 6B 38            [ 1] 1073 	ld	(0x38, sp), a
      008711 1E 42            [ 2] 1074 	ldw	x, (0x42, sp)
      008713 72 FB 32         [ 2] 1075 	addw	x, (0x32, sp)
      008716 1F 42            [ 2] 1076 	ldw	(0x42, sp), x
      008718 7B 41            [ 1] 1077 	ld	a, (0x41, sp)
      00871A 19 31            [ 1] 1078 	adc	a, (0x31, sp)
      00871C 6B 41            [ 1] 1079 	ld	(0x41, sp), a
      00871E 7B 40            [ 1] 1080 	ld	a, (0x40, sp)
      008720 19 30            [ 1] 1081 	adc	a, (0x30, sp)
      008722 6B 40            [ 1] 1082 	ld	(0x40, sp), a
      008724 CC 86 92         [ 2] 1083 	jp	00106$
      008727                       1084 00104$:
                                   1085 ;	decoder.c: 292: else           { n_hi++; se_hi += e; sy_hi += y; }
      008727 16 4A            [ 2] 1086 	ldw	y, (0x4a, sp)
      008729 90 5C            [ 1] 1087 	incw	y
      00872B 17 4A            [ 2] 1088 	ldw	(0x4a, sp), y
      00872D 16 36            [ 2] 1089 	ldw	y, (0x36, sp)
      00872F 72 F9 3E         [ 2] 1090 	addw	y, (0x3e, sp)
      008732 17 3E            [ 2] 1091 	ldw	(0x3e, sp), y
      008734 9F               [ 1] 1092 	ld	a, xl
      008735 19 3D            [ 1] 1093 	adc	a, (0x3d, sp)
      008737 6B 3D            [ 1] 1094 	ld	(0x3d, sp), a
      008739 9E               [ 1] 1095 	ld	a, xh
      00873A 19 3C            [ 1] 1096 	adc	a, (0x3c, sp)
      00873C 6B 3C            [ 1] 1097 	ld	(0x3c, sp), a
      00873E 1E 46            [ 2] 1098 	ldw	x, (0x46, sp)
      008740 72 FB 32         [ 2] 1099 	addw	x, (0x32, sp)
      008743 1F 46            [ 2] 1100 	ldw	(0x46, sp), x
      008745 7B 45            [ 1] 1101 	ld	a, (0x45, sp)
      008747 19 31            [ 1] 1102 	adc	a, (0x31, sp)
      008749 6B 45            [ 1] 1103 	ld	(0x45, sp), a
      00874B 7B 44            [ 1] 1104 	ld	a, (0x44, sp)
      00874D 19 30            [ 1] 1105 	adc	a, (0x30, sp)
      00874F 6B 44            [ 1] 1106 	ld	(0x44, sp), a
      008751 CC 86 92         [ 2] 1107 	jp	00106$
      008754                       1108 00108$:
                                   1109 ;	decoder.c: 294: if (n_lo < 2 || n_hi < 2) return;
      008754 1E 48            [ 2] 1110 	ldw	x, (0x48, sp)
      008756 A3 00 02         [ 2] 1111 	cpw	x, #0x0002
      008759 24 03            [ 1] 1112 	jrnc	00181$
      00875B CC 89 1D         [ 2] 1113 	jp	00117$
      00875E                       1114 00181$:
      00875E 1E 4A            [ 2] 1115 	ldw	x, (0x4a, sp)
      008760 A3 00 02         [ 2] 1116 	cpw	x, #0x0002
      008763 24 03            [ 1] 1117 	jrnc	00110$
      008765 CC 89 1D         [ 2] 1118 	jp	00117$
      008768                       1119 00110$:
                                   1120 ;	decoder.c: 295: me_lo = se_lo / (int32_t)n_lo;
      008768 16 48            [ 2] 1121 	ldw	y, (0x48, sp)
      00876A 5F               [ 1] 1122 	clrw	x
      00876B 90 89            [ 2] 1123 	pushw	y
      00876D 89               [ 2] 1124 	pushw	x
      00876E 1E 3E            [ 2] 1125 	ldw	x, (0x3e, sp)
      008770 89               [ 2] 1126 	pushw	x
      008771 1E 3E            [ 2] 1127 	ldw	x, (0x3e, sp)
      008773 89               [ 2] 1128 	pushw	x
                                   1129 ;	decoder.c: 296: me_hi = se_hi / (int32_t)n_hi;
      008774 CD 9E 82         [ 4] 1130 	call	__divslong
      008777 5B 08            [ 2] 1131 	addw	sp, #8
      008779 1F 2A            [ 2] 1132 	ldw	(0x2a, sp), x
      00877B 17 28            [ 2] 1133 	ldw	(0x28, sp), y
      00877D 16 4A            [ 2] 1134 	ldw	y, (0x4a, sp)
      00877F 5F               [ 1] 1135 	clrw	x
      008780 90 89            [ 2] 1136 	pushw	y
      008782 89               [ 2] 1137 	pushw	x
      008783 1E 42            [ 2] 1138 	ldw	x, (0x42, sp)
      008785 89               [ 2] 1139 	pushw	x
      008786 1E 42            [ 2] 1140 	ldw	x, (0x42, sp)
      008788 89               [ 2] 1141 	pushw	x
                                   1142 ;	decoder.c: 297: my_lo = sy_lo / n_lo;
      008789 CD 9E 82         [ 4] 1143 	call	__divslong
      00878C 5B 08            [ 2] 1144 	addw	sp, #8
      00878E 1F 2E            [ 2] 1145 	ldw	(0x2e, sp), x
      008790 17 2C            [ 2] 1146 	ldw	(0x2c, sp), y
      008792 16 48            [ 2] 1147 	ldw	y, (0x48, sp)
      008794 5F               [ 1] 1148 	clrw	x
      008795 90 89            [ 2] 1149 	pushw	y
      008797 89               [ 2] 1150 	pushw	x
      008798 1E 46            [ 2] 1151 	ldw	x, (0x46, sp)
      00879A 89               [ 2] 1152 	pushw	x
      00879B 1E 46            [ 2] 1153 	ldw	x, (0x46, sp)
      00879D 89               [ 2] 1154 	pushw	x
                                   1155 ;	decoder.c: 298: my_hi = sy_hi / n_hi;
      00879E CD 9E A9         [ 4] 1156 	call	__divulong
      0087A1 5B 08            [ 2] 1157 	addw	sp, #8
      0087A3 1F 36            [ 2] 1158 	ldw	(0x36, sp), x
      0087A5 17 34            [ 2] 1159 	ldw	(0x34, sp), y
      0087A7 16 4A            [ 2] 1160 	ldw	y, (0x4a, sp)
      0087A9 5F               [ 1] 1161 	clrw	x
      0087AA 90 89            [ 2] 1162 	pushw	y
      0087AC 89               [ 2] 1163 	pushw	x
      0087AD 1E 4A            [ 2] 1164 	ldw	x, (0x4a, sp)
      0087AF 89               [ 2] 1165 	pushw	x
      0087B0 1E 4A            [ 2] 1166 	ldw	x, (0x4a, sp)
      0087B2 89               [ 2] 1167 	pushw	x
                                   1168 ;	decoder.c: 299: de = me_hi - me_lo;
      0087B3 CD 9E A9         [ 4] 1169 	call	__divulong
      0087B6 5B 08            [ 2] 1170 	addw	sp, #8
      0087B8 1F 32            [ 2] 1171 	ldw	(0x32, sp), x
      0087BA 17 30            [ 2] 1172 	ldw	(0x30, sp), y
      0087BC 1E 2E            [ 2] 1173 	ldw	x, (0x2e, sp)
      0087BE 72 F0 2A         [ 2] 1174 	subw	x, (0x2a, sp)
      0087C1 1F 26            [ 2] 1175 	ldw	(0x26, sp), x
      0087C3 7B 2D            [ 1] 1176 	ld	a, (0x2d, sp)
      0087C5 12 29            [ 1] 1177 	sbc	a, (0x29, sp)
      0087C7 6B 25            [ 1] 1178 	ld	(0x25, sp), a
      0087C9 7B 2C            [ 1] 1179 	ld	a, (0x2c, sp)
      0087CB 12 28            [ 1] 1180 	sbc	a, (0x28, sp)
      0087CD 6B 24            [ 1] 1181 	ld	(0x24, sp), a
                                   1182 ;	decoder.c: 300: dy = (int32_t)my_hi - (int32_t)my_lo;
      0087CF 1E 32            [ 2] 1183 	ldw	x, (0x32, sp)
      0087D1 72 F0 36         [ 2] 1184 	subw	x, (0x36, sp)
      0087D4 1F 2A            [ 2] 1185 	ldw	(0x2a, sp), x
      0087D6 7B 31            [ 1] 1186 	ld	a, (0x31, sp)
      0087D8 12 35            [ 1] 1187 	sbc	a, (0x35, sp)
      0087DA 6B 29            [ 1] 1188 	ld	(0x29, sp), a
      0087DC 7B 30            [ 1] 1189 	ld	a, (0x30, sp)
      0087DE 12 34            [ 1] 1190 	sbc	a, (0x34, sp)
      0087E0 6B 28            [ 1] 1191 	ld	(0x28, sp), a
                                   1192 ;	decoder.c: 301: if (dy <= 0) return;
      0087E2 5F               [ 1] 1193 	clrw	x
      0087E3 13 2A            [ 2] 1194 	cpw	x, (0x2a, sp)
      0087E5 4F               [ 1] 1195 	clr	a
      0087E6 12 29            [ 1] 1196 	sbc	a, (0x29, sp)
      0087E8 4F               [ 1] 1197 	clr	a
      0087E9 12 28            [ 1] 1198 	sbc	a, (0x28, sp)
      0087EB 2F 03            [ 1] 1199 	jrslt	00113$
      0087ED CC 89 1D         [ 2] 1200 	jp	00117$
      0087F0                       1201 00113$:
                                   1202 ;	decoder.c: 302: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
      0087F0 CE 01 32         [ 2] 1203 	ldw	x, _g_K+0
      0087F3 1F 2E            [ 2] 1204 	ldw	(0x2e, sp), x
      0087F5 4F               [ 1] 1205 	clr	a
      0087F6 0F 2C            [ 1] 1206 	clr	(0x2c, sp)
      0087F8 88               [ 1] 1207 	push	a
      0087F9 1E 27            [ 2] 1208 	ldw	x, (0x27, sp)
      0087FB 89               [ 2] 1209 	pushw	x
      0087FC 1E 27            [ 2] 1210 	ldw	x, (0x27, sp)
      0087FE 89               [ 2] 1211 	pushw	x
      0087FF 1E 33            [ 2] 1212 	ldw	x, (0x33, sp)
      008801 89               [ 2] 1213 	pushw	x
      008802 97               [ 1] 1214 	ld	xl, a
      008803 02               [ 1] 1215 	rlwa	x
      008804 4F               [ 1] 1216 	clr	a
      008805 01               [ 1] 1217 	rrwa	x
      008806 89               [ 2] 1218 	pushw	x
      008807 CD 9F 06         [ 4] 1219 	call	__mullong
      00880A 5B 08            [ 2] 1220 	addw	sp, #8
      00880C 1F 37            [ 2] 1221 	ldw	(0x37, sp), x
      00880E 1E 2B            [ 2] 1222 	ldw	x, (0x2b, sp)
      008810 89               [ 2] 1223 	pushw	x
      008811 1E 2B            [ 2] 1224 	ldw	x, (0x2b, sp)
      008813 89               [ 2] 1225 	pushw	x
      008814 1E 3B            [ 2] 1226 	ldw	x, (0x3b, sp)
      008816 89               [ 2] 1227 	pushw	x
      008817 90 89            [ 2] 1228 	pushw	y
                                   1229 ;	decoder.c: 303: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
      008819 CD 9E 82         [ 4] 1230 	call	__divslong
      00881C 5B 08            [ 2] 1231 	addw	sp, #8
      00881E 1F 33            [ 2] 1232 	ldw	(0x33, sp), x
      008820 17 31            [ 2] 1233 	ldw	(0x31, sp), y
      008822 84               [ 1] 1234 	pop	a
      008823 1E 3A            [ 2] 1235 	ldw	x, (0x3a, sp)
      008825 72 FB 3E         [ 2] 1236 	addw	x, (0x3e, sp)
      008828 1F 36            [ 2] 1237 	ldw	(0x36, sp), x
      00882A 16 38            [ 2] 1238 	ldw	y, (0x38, sp)
      00882C 24 02            [ 1] 1239 	jrnc	00184$
      00882E 90 5C            [ 1] 1240 	incw	y
      008830                       1241 00184$:
      008830 72 F9 3C         [ 2] 1242 	addw	y, (0x3c, sp)
      008833 1E 48            [ 2] 1243 	ldw	x, (0x48, sp)
      008835 72 FB 4A         [ 2] 1244 	addw	x, (0x4a, sp)
      008838 1F 3E            [ 2] 1245 	ldw	(0x3e, sp), x
      00883A 1F 4A            [ 2] 1246 	ldw	(0x4a, sp), x
      00883C 5F               [ 1] 1247 	clrw	x
      00883D 1F 48            [ 2] 1248 	ldw	(0x48, sp), x
      00883F 88               [ 1] 1249 	push	a
      008840 1E 4B            [ 2] 1250 	ldw	x, (0x4b, sp)
      008842 89               [ 2] 1251 	pushw	x
      008843 1E 4B            [ 2] 1252 	ldw	x, (0x4b, sp)
      008845 89               [ 2] 1253 	pushw	x
      008846 1E 3B            [ 2] 1254 	ldw	x, (0x3b, sp)
      008848 89               [ 2] 1255 	pushw	x
      008849 90 89            [ 2] 1256 	pushw	y
                                   1257 ;	decoder.c: 304: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
      00884B CD 9E 82         [ 4] 1258 	call	__divslong
      00884E 5B 08            [ 2] 1259 	addw	sp, #8
      008850 1F 3D            [ 2] 1260 	ldw	(0x3d, sp), x
      008852 17 3B            [ 2] 1261 	ldw	(0x3b, sp), y
      008854 84               [ 1] 1262 	pop	a
      008855 1E 42            [ 2] 1263 	ldw	x, (0x42, sp)
      008857 72 FB 46         [ 2] 1264 	addw	x, (0x46, sp)
      00885A 1F 4A            [ 2] 1265 	ldw	(0x4a, sp), x
      00885C 16 40            [ 2] 1266 	ldw	y, (0x40, sp)
      00885E 24 02            [ 1] 1267 	jrnc	00185$
      008860 90 5C            [ 1] 1268 	incw	y
      008862                       1269 00185$:
      008862 72 F9 44         [ 2] 1270 	addw	y, (0x44, sp)
      008865 1E 3E            [ 2] 1271 	ldw	x, (0x3e, sp)
      008867 1F 46            [ 2] 1272 	ldw	(0x46, sp), x
      008869 5F               [ 1] 1273 	clrw	x
      00886A 1F 44            [ 2] 1274 	ldw	(0x44, sp), x
      00886C 88               [ 1] 1275 	push	a
      00886D 1E 47            [ 2] 1276 	ldw	x, (0x47, sp)
      00886F 89               [ 2] 1277 	pushw	x
      008870 1E 47            [ 2] 1278 	ldw	x, (0x47, sp)
      008872 89               [ 2] 1279 	pushw	x
      008873 1E 4F            [ 2] 1280 	ldw	x, (0x4f, sp)
      008875 89               [ 2] 1281 	pushw	x
      008876 90 89            [ 2] 1282 	pushw	y
                                   1283 ;	decoder.c: 305: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
      008878 CD 9E A9         [ 4] 1284 	call	__divulong
      00887B 5B 08            [ 2] 1285 	addw	sp, #8
      00887D 17 49            [ 2] 1286 	ldw	(0x49, sp), y
      00887F 84               [ 1] 1287 	pop	a
      008880 16 3C            [ 2] 1288 	ldw	y, (0x3c, sp)
      008882 17 46            [ 2] 1289 	ldw	(0x46, sp), y
      008884 88               [ 1] 1290 	push	a
      008885 7B 48            [ 1] 1291 	ld	a, (0x48, sp)
      008887 40               [ 1] 1292 	neg	a
      008888 6B 40            [ 1] 1293 	ld	(0x40, sp), a
      00888A 4F               [ 1] 1294 	clr	a
      00888B 12 47            [ 1] 1295 	sbc	a, (0x47, sp)
      00888D 6B 3F            [ 1] 1296 	ld	(0x3f, sp), a
      00888F 84               [ 1] 1297 	pop	a
      008890 16 48            [ 2] 1298 	ldw	y, (0x48, sp)
      008892 17 40            [ 2] 1299 	ldw	(0x40, sp), y
      008894 90 CE 01 34      [ 2] 1300 	ldw	y, _g_tau+0
      008898 17 46            [ 2] 1301 	ldw	(0x46, sp), y
      00889A 88               [ 1] 1302 	push	a
      00889B 7B 47            [ 1] 1303 	ld	a, (0x47, sp)
      00889D 49               [ 1] 1304 	rlc	a
      00889E 4F               [ 1] 1305 	clr	a
      00889F A2 00            [ 1] 1306 	sbc	a, #0x00
      0088A1 6B 46            [ 1] 1307 	ld	(0x46, sp), a
      0088A3 6B 45            [ 1] 1308 	ld	(0x45, sp), a
      0088A5 84               [ 1] 1309 	pop	a
      0088A6 72 F0 46         [ 2] 1310 	subw	x, (0x46, sp)
      0088A9 88               [ 1] 1311 	push	a
      0088AA 7B 42            [ 1] 1312 	ld	a, (0x42, sp)
      0088AC 12 46            [ 1] 1313 	sbc	a, (0x46, sp)
      0088AE 6B 4A            [ 1] 1314 	ld	(0x4a, sp), a
      0088B0 7B 41            [ 1] 1315 	ld	a, (0x41, sp)
      0088B2 12 45            [ 1] 1316 	sbc	a, (0x45, sp)
      0088B4 6B 49            [ 1] 1317 	ld	(0x49, sp), a
      0088B6 89               [ 2] 1318 	pushw	x
      0088B7 1E 4B            [ 2] 1319 	ldw	x, (0x4b, sp)
      0088B9 89               [ 2] 1320 	pushw	x
      0088BA 1E 2B            [ 2] 1321 	ldw	x, (0x2b, sp)
      0088BC 89               [ 2] 1322 	pushw	x
      0088BD 1E 2B            [ 2] 1323 	ldw	x, (0x2b, sp)
      0088BF 89               [ 2] 1324 	pushw	x
      0088C0 CD 9F 06         [ 4] 1325 	call	__mullong
      0088C3 5B 08            [ 2] 1326 	addw	sp, #8
      0088C5 1F 4B            [ 2] 1327 	ldw	(0x4b, sp), x
      0088C7 1E 2B            [ 2] 1328 	ldw	x, (0x2b, sp)
      0088C9 89               [ 2] 1329 	pushw	x
      0088CA 1E 2B            [ 2] 1330 	ldw	x, (0x2b, sp)
      0088CC 89               [ 2] 1331 	pushw	x
      0088CD 1E 4F            [ 2] 1332 	ldw	x, (0x4f, sp)
      0088CF 89               [ 2] 1333 	pushw	x
      0088D0 90 89            [ 2] 1334 	pushw	y
      0088D2 CD 9E 82         [ 4] 1335 	call	__divslong
      0088D5 5B 09            [ 2] 1336 	addw	sp, #9
      0088D7 72 FB 3E         [ 2] 1337 	addw	x, (0x3e, sp)
      0088DA 1F 4A            [ 2] 1338 	ldw	(0x4a, sp), x
                                   1339 ;	decoder.c: 306: if ((uint32_t)((int32_t)g_K - dk) < K_MIN ||
      0088DC 16 2E            [ 2] 1340 	ldw	y, (0x2e, sp)
      0088DE 72 F2 32         [ 2] 1341 	subw	y, (0x32, sp)
      0088E1 1E 30            [ 2] 1342 	ldw	x, (0x30, sp)
      0088E3 24 01            [ 1] 1343 	jrnc	00186$
      0088E5 5C               [ 1] 1344 	incw	x
      0088E6                       1345 00186$:
      0088E6 50               [ 2] 1346 	negw	x
      0088E7 17 48            [ 2] 1347 	ldw	(0x48, sp), y
      0088E9 1F 46            [ 2] 1348 	ldw	(0x46, sp), x
      0088EB 1E 48            [ 2] 1349 	ldw	x, (0x48, sp)
      0088ED A3 B3 B0         [ 2] 1350 	cpw	x, #0xb3b0
      0088F0 7B 47            [ 1] 1351 	ld	a, (0x47, sp)
      0088F2 A2 00            [ 1] 1352 	sbc	a, #0x00
      0088F4 7B 46            [ 1] 1353 	ld	a, (0x46, sp)
      0088F6 A2 00            [ 1] 1354 	sbc	a, #0x00
      0088F8 25 23            [ 1] 1355 	jrc	00117$
                                   1356 ;	decoder.c: 307: (uint32_t)((int32_t)g_K - dk) > K_MAX) return;
      0088FA AE EA 60         [ 2] 1357 	ldw	x, #0xea60
      0088FD 13 48            [ 2] 1358 	cpw	x, (0x48, sp)
      0088FF 4F               [ 1] 1359 	clr	a
      008900 12 47            [ 1] 1360 	sbc	a, (0x47, sp)
      008902 4F               [ 1] 1361 	clr	a
      008903 12 46            [ 1] 1362 	sbc	a, (0x46, sp)
      008905 25 16            [ 1] 1363 	jrc	00117$
                                   1364 ;	decoder.c: 308: g_K = (uint16_t)((int32_t)g_K - dk);
      008907 CE 01 32         [ 2] 1365 	ldw	x, _g_K+0
      00890A 16 32            [ 2] 1366 	ldw	y, (0x32, sp)
      00890C 17 48            [ 2] 1367 	ldw	(0x48, sp), y
      00890E 72 F0 48         [ 2] 1368 	subw	x, (0x48, sp)
      008911 CF 01 32         [ 2] 1369 	ldw	_g_K+0, x
                                   1370 ;	decoder.c: 309: g_tau = (int16_t)(g_tau + dtau);
      008914 CE 01 34         [ 2] 1371 	ldw	x, _g_tau+0
      008917 72 FB 4A         [ 2] 1372 	addw	x, (0x4a, sp)
      00891A CF 01 34         [ 2] 1373 	ldw	_g_tau+0, x
      00891D                       1374 00117$:
                                   1375 ;	decoder.c: 310: }
      00891D 1E 4C            [ 2] 1376 	ldw	x, (76, sp)
      00891F 5B 4F            [ 2] 1377 	addw	sp, #79
      008921 FC               [ 2] 1378 	jp	(x)
                                   1379 ;	decoder.c: 335: static void ss_init(SStream *s, const uint8_t *cap, uint16_t ncap)
                                   1380 ;	-----------------------------------------
                                   1381 ;	 function ss_init
                                   1382 ;	-----------------------------------------
      008922                       1383 _ss_init:
      008922 89               [ 2] 1384 	pushw	x
      008923 51               [ 1] 1385 	exgw	x, y
                                   1386 ;	decoder.c: 337: ps_init(&s->ps, cap, ncap);
      008924 17 01            [ 2] 1387 	ldw	(0x01, sp), y
      008926 90 89            [ 2] 1388 	pushw	y
      008928 1E 09            [ 2] 1389 	ldw	x, (0x09, sp)
      00892A 89               [ 2] 1390 	pushw	x
      00892B 1E 09            [ 2] 1391 	ldw	x, (0x09, sp)
      00892D 89               [ 2] 1392 	pushw	x
      00892E 1E 07            [ 2] 1393 	ldw	x, (0x07, sp)
      008930 CD 81 E8         [ 4] 1394 	call	_ps_init
      008933 90 85            [ 2] 1395 	popw	y
                                   1396 ;	decoder.c: 338: s->y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
      008935 93               [ 1] 1397 	ldw	x, y
      008936 1C 00 1A         [ 2] 1398 	addw	x, #0x001a
      008939 A6 A4            [ 1] 1399 	ld	a, #0xa4
      00893B E7 03            [ 1] 1400 	ld	(0x3, x), a
      00893D A6 82            [ 1] 1401 	ld	a, #0x82
      00893F E7 02            [ 1] 1402 	ld	(0x2, x), a
      008941 A6 03            [ 1] 1403 	ld	a, #0x03
      008943 E7 01            [ 1] 1404 	ld	(0x1, x), a
      008945 7F               [ 1] 1405 	clr	(x)
                                   1406 ;	decoder.c: 339: s->y_prev = 0; s->have_y = 0; s->n = 0;
      008946 93               [ 1] 1407 	ldw	x, y
      008947 1C 00 1E         [ 2] 1408 	addw	x, #0x001e
      00894A 6F 03            [ 1] 1409 	clr	(0x3, x)
      00894C 6F 02            [ 1] 1410 	clr	(0x2, x)
      00894E 6F 01            [ 1] 1411 	clr	(0x1, x)
      008950 7F               [ 1] 1412 	clr	(x)
      008951 93               [ 1] 1413 	ldw	x, y
      008952 6F 22            [ 1] 1414 	clr	(0x0022, x)
      008954 93               [ 1] 1415 	ldw	x, y
      008955 1C 00 23         [ 2] 1416 	addw	x, #0x0023
      008958 6F 01            [ 1] 1417 	clr	(0x1, x)
      00895A 7F               [ 1] 1418 	clr	(x)
                                   1419 ;	decoder.c: 340: s->pend = 0; s->src_done = 0;
      00895B 93               [ 1] 1420 	ldw	x, y
      00895C 6F 25            [ 1] 1421 	clr	(0x0025, x)
      00895E 93               [ 1] 1422 	ldw	x, y
      00895F 6F 2D            [ 1] 1423 	clr	(0x002d, x)
                                   1424 ;	decoder.c: 341: s->p_k0 = 0; s->p_u = 0; s->p_v = 0; s->p_fam = 0;
      008961 93               [ 1] 1425 	ldw	x, y
      008962 1C 00 26         [ 2] 1426 	addw	x, #0x0026
      008965 6F 01            [ 1] 1427 	clr	(0x1, x)
      008967 7F               [ 1] 1428 	clr	(x)
      008968 93               [ 1] 1429 	ldw	x, y
      008969 1C 00 28         [ 2] 1430 	addw	x, #0x0028
      00896C 6F 01            [ 1] 1431 	clr	(0x1, x)
      00896E 7F               [ 1] 1432 	clr	(x)
      00896F 93               [ 1] 1433 	ldw	x, y
      008970 1C 00 2A         [ 2] 1434 	addw	x, #0x002a
      008973 6F 01            [ 1] 1435 	clr	(0x1, x)
      008975 7F               [ 1] 1436 	clr	(x)
      008976 93               [ 1] 1437 	ldw	x, y
      008977 6F 2C            [ 1] 1438 	clr	(0x002c, x)
                                   1439 ;	decoder.c: 342: }
      008979 1E 03            [ 2] 1440 	ldw	x, (3, sp)
      00897B 5B 08            [ 2] 1441 	addw	sp, #8
      00897D FC               [ 2] 1442 	jp	(x)
                                   1443 ;	decoder.c: 344: static uint8_t ss_next(SStream *s, Seg *out)
                                   1444 ;	-----------------------------------------
                                   1445 ;	 function ss_next
                                   1446 ;	-----------------------------------------
      00897E                       1447 _ss_next:
      00897E 52 3A            [ 2] 1448 	sub	sp, #58
                                   1449 ;	decoder.c: 347: while (!s->src_done) {
      008980 1F 39            [ 2] 1450 	ldw	(0x39, sp), x
      008982 1F 16            [ 2] 1451 	ldw	(0x16, sp), x
      008984 1E 39            [ 2] 1452 	ldw	x, (0x39, sp)
      008986 1C 00 1E         [ 2] 1453 	addw	x, #0x001e
      008989 1F 18            [ 2] 1454 	ldw	(0x18, sp), x
      00898B 1E 39            [ 2] 1455 	ldw	x, (0x39, sp)
      00898D 1C 00 23         [ 2] 1456 	addw	x, #0x0023
      008990 1F 1A            [ 2] 1457 	ldw	(0x1a, sp), x
      008992 1E 39            [ 2] 1458 	ldw	x, (0x39, sp)
      008994 1C 00 26         [ 2] 1459 	addw	x, #0x0026
      008997 1F 1C            [ 2] 1460 	ldw	(0x1c, sp), x
      008999 1E 39            [ 2] 1461 	ldw	x, (0x39, sp)
      00899B 1C 00 2D         [ 2] 1462 	addw	x, #0x002d
      00899E 1F 1E            [ 2] 1463 	ldw	(0x1e, sp), x
      0089A0                       1464 00119$:
      0089A0 1E 1E            [ 2] 1465 	ldw	x, (0x1e, sp)
      0089A2 F6               [ 1] 1466 	ld	a, (x)
                                   1467 ;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
      0089A3 1E 39            [ 2] 1468 	ldw	x, (0x39, sp)
      0089A5 1C 00 25         [ 2] 1469 	addw	x, #0x0025
      0089A8 1F 20            [ 2] 1470 	ldw	(0x20, sp), x
                                   1471 ;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
      0089AA 1E 39            [ 2] 1472 	ldw	x, (0x39, sp)
      0089AC 1C 00 28         [ 2] 1473 	addw	x, #0x0028
      0089AF 1F 22            [ 2] 1474 	ldw	(0x22, sp), x
                                   1475 ;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
      0089B1 1E 39            [ 2] 1476 	ldw	x, (0x39, sp)
      0089B3 1C 00 2A         [ 2] 1477 	addw	x, #0x002a
      0089B6 1F 24            [ 2] 1478 	ldw	(0x24, sp), x
                                   1479 ;	decoder.c: 367: s->p_fam = p.sfa;
      0089B8 1E 39            [ 2] 1480 	ldw	x, (0x39, sp)
      0089BA 1C 00 2C         [ 2] 1481 	addw	x, #0x002c
      0089BD 1F 26            [ 2] 1482 	ldw	(0x26, sp), x
                                   1483 ;	decoder.c: 371: out->k0 = s->p_k0;
      0089BF 16 3D            [ 2] 1484 	ldw	y, (0x3d, sp)
      0089C1 17 28            [ 2] 1485 	ldw	(0x28, sp), y
                                   1486 ;	decoder.c: 372: out->k1 = (s->n < NB) ? s->n : NB;
      0089C3 93               [ 1] 1487 	ldw	x, y
      0089C4 5C               [ 1] 1488 	incw	x
      0089C5 5C               [ 1] 1489 	incw	x
      0089C6 1F 2A            [ 2] 1490 	ldw	(0x2a, sp), x
                                   1491 ;	decoder.c: 373: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
      0089C8 93               [ 1] 1492 	ldw	x, y
      0089C9 1C 00 04         [ 2] 1493 	addw	x, #0x0004
      0089CC 1F 2C            [ 2] 1494 	ldw	(0x2c, sp), x
      0089CE 93               [ 1] 1495 	ldw	x, y
      0089CF 1C 00 06         [ 2] 1496 	addw	x, #0x0006
      0089D2 1F 2E            [ 2] 1497 	ldw	(0x2e, sp), x
      0089D4 93               [ 1] 1498 	ldw	x, y
      0089D5 1C 00 08         [ 2] 1499 	addw	x, #0x0008
      0089D8 1F 30            [ 2] 1500 	ldw	(0x30, sp), x
                                   1501 ;	decoder.c: 347: while (!s->src_done) {
      0089DA 4D               [ 1] 1502 	tnz	a
      0089DB 27 03            [ 1] 1503 	jreq	00232$
      0089DD CC 8B C5         [ 2] 1504 	jp	00121$
      0089E0                       1505 00232$:
                                   1506 ;	decoder.c: 351: if (!ps_next(&s->ps, &p)) { s->src_done = 1; break; }
      0089E0 96               [ 1] 1507 	ldw	x, sp
      0089E1 1C 00 0D         [ 2] 1508 	addw	x, #13
      0089E4 16 39            [ 2] 1509 	ldw	y, (0x39, sp)
      0089E6 89               [ 2] 1510 	pushw	x
      0089E7 93               [ 1] 1511 	ldw	x, y
      0089E8 CD 82 54         [ 4] 1512 	call	_ps_next
      0089EB 4D               [ 1] 1513 	tnz	a
      0089EC 26 08            [ 1] 1514 	jrne	00102$
      0089EE 1E 1E            [ 2] 1515 	ldw	x, (0x1e, sp)
      0089F0 A6 01            [ 1] 1516 	ld	a, #0x01
      0089F2 F7               [ 1] 1517 	ld	(x), a
      0089F3 CC 8B C5         [ 2] 1518 	jp	00121$
      0089F6                       1519 00102$:
                                   1520 ;	decoder.c: 352: y = map_y((uint16_t)((p.ra + p.rb) >> 1));
      0089F6 16 0D            [ 2] 1521 	ldw	y, (0x0d, sp)
      0089F8 17 37            [ 2] 1522 	ldw	(0x37, sp), y
      0089FA 1E 0F            [ 2] 1523 	ldw	x, (0x0f, sp)
      0089FC 72 FB 37         [ 2] 1524 	addw	x, (0x37, sp)
      0089FF 54               [ 2] 1525 	srlw	x
      008A00 CD 85 73         [ 4] 1526 	call	_map_y
      008A03 1F 03            [ 2] 1527 	ldw	(0x03, sp), x
      008A05 17 01            [ 2] 1528 	ldw	(0x01, sp), y
                                   1529 ;	decoder.c: 353: if (y > s->y_end) { s->src_done = 1; break; }
      008A07 1E 16            [ 2] 1530 	ldw	x, (0x16, sp)
      008A09 90 93            [ 1] 1531 	ldw	y, x
      008A0B 90 EE 1C         [ 2] 1532 	ldw	y, (0x1c, y)
      008A0E EE 1A            [ 2] 1533 	ldw	x, (0x1a, x)
      008A10 90 9F            [ 1] 1534 	ld	a, yl
      008A12 11 04            [ 1] 1535 	cp	a, (0x04, sp)
      008A14 90 9E            [ 1] 1536 	ld	a, yh
      008A16 12 03            [ 1] 1537 	sbc	a, (0x03, sp)
      008A18 9F               [ 1] 1538 	ld	a, xl
      008A19 12 02            [ 1] 1539 	sbc	a, (0x02, sp)
      008A1B 9E               [ 1] 1540 	ld	a, xh
      008A1C 12 01            [ 1] 1541 	sbc	a, (0x01, sp)
      008A1E 24 08            [ 1] 1542 	jrnc	00104$
      008A20 1E 1E            [ 2] 1543 	ldw	x, (0x1e, sp)
      008A22 A6 01            [ 1] 1544 	ld	a, #0x01
      008A24 F7               [ 1] 1545 	ld	(x), a
      008A25 CC 8B C5         [ 2] 1546 	jp	00121$
      008A28                       1547 00104$:
                                   1548 ;	decoder.c: 354: if (!s->have_y) { s->n = 0; s->have_y = 1; }
      008A28 1E 39            [ 2] 1549 	ldw	x, (0x39, sp)
      008A2A 1C 00 22         [ 2] 1550 	addw	x, #0x0022
      008A2D F6               [ 1] 1551 	ld	a, (x)
      008A2E 6B 38            [ 1] 1552 	ld	(0x38, sp), a
      008A30 26 0C            [ 1] 1553 	jrne	00108$
      008A32 16 1A            [ 2] 1554 	ldw	y, (0x1a, sp)
      008A34 90 6F 01         [ 1] 1555 	clr	(0x1, y)
      008A37 90 7F            [ 1] 1556 	clr	(y)
      008A39 A6 01            [ 1] 1557 	ld	a, #0x01
      008A3B F7               [ 1] 1558 	ld	(x), a
      008A3C 20 4A            [ 2] 1559 	jra	00109$
      008A3E                       1560 00108$:
                                   1561 ;	decoder.c: 356: d = (int32_t)y - (int32_t)s->y_prev;
      008A3E 16 03            [ 2] 1562 	ldw	y, (0x03, sp)
      008A40 17 07            [ 2] 1563 	ldw	(0x07, sp), y
      008A42 7B 01            [ 1] 1564 	ld	a, (0x01, sp)
      008A44 6B 05            [ 1] 1565 	ld	(0x05, sp), a
      008A46 7B 02            [ 1] 1566 	ld	a, (0x02, sp)
      008A48 1E 18            [ 2] 1567 	ldw	x, (0x18, sp)
      008A4A 90 93            [ 1] 1568 	ldw	y, x
      008A4C 90 EE 02         [ 2] 1569 	ldw	y, (0x2, y)
      008A4F FE               [ 2] 1570 	ldw	x, (x)
      008A50 17 0B            [ 2] 1571 	ldw	(0x0b, sp), y
      008A52 1F 09            [ 2] 1572 	ldw	(0x09, sp), x
      008A54 16 07            [ 2] 1573 	ldw	y, (0x07, sp)
      008A56 72 F2 0B         [ 2] 1574 	subw	y, (0x0b, sp)
      008A59 12 0A            [ 1] 1575 	sbc	a, (0x0a, sp)
      008A5B 6B 36            [ 1] 1576 	ld	(0x36, sp), a
      008A5D 7B 05            [ 1] 1577 	ld	a, (0x05, sp)
      008A5F 12 09            [ 1] 1578 	sbc	a, (0x09, sp)
      008A61 6B 35            [ 1] 1579 	ld	(0x35, sp), a
                                   1580 ;	decoder.c: 357: dn = (int16_t)((d + BIT_H) >> BIT_SH);
      008A63 72 A9 01 00      [ 2] 1581 	addw	y, #0x0100
      008A67 1E 35            [ 2] 1582 	ldw	x, (0x35, sp)
      008A69 24 01            [ 1] 1583 	jrnc	00236$
      008A6B 5C               [ 1] 1584 	incw	x
      008A6C                       1585 00236$:
      008A6C 4F               [ 1] 1586 	clr	a
      008A6D 5D               [ 2] 1587 	tnzw	x
      008A6E 2A 01            [ 1] 1588 	jrpl	00237$
      008A70 4A               [ 1] 1589 	dec	a
      008A71                       1590 00237$:
      008A71 01               [ 1] 1591 	rrwa	x
      008A72 90 01            [ 1] 1592 	rrwa	y
      008A74 57               [ 2] 1593 	sraw	x
      008A75 90 56            [ 2] 1594 	rrcw	y
                                   1595 ;	decoder.c: 358: if (dn > 0) s->n = (uint16_t)(s->n + dn);
      008A77 93               [ 1] 1596 	ldw	x, y
      008A78 A3 00 00         [ 2] 1597 	cpw	x, #0x0000
      008A7B 2D 0B            [ 1] 1598 	jrsle	00109$
      008A7D 1E 1A            [ 2] 1599 	ldw	x, (0x1a, sp)
      008A7F FE               [ 2] 1600 	ldw	x, (x)
      008A80 1F 37            [ 2] 1601 	ldw	(0x37, sp), x
      008A82 72 F9 37         [ 2] 1602 	addw	y, (0x37, sp)
      008A85 1E 1A            [ 2] 1603 	ldw	x, (0x1a, sp)
      008A87 FF               [ 2] 1604 	ldw	(x), y
      008A88                       1605 00109$:
                                   1606 ;	decoder.c: 360: s->y_prev = y;
      008A88 1E 18            [ 2] 1607 	ldw	x, (0x18, sp)
      008A8A 16 03            [ 2] 1608 	ldw	y, (0x03, sp)
      008A8C EF 02            [ 2] 1609 	ldw	(0x2, x), y
      008A8E 16 01            [ 2] 1610 	ldw	y, (0x01, sp)
      008A90 FF               [ 2] 1611 	ldw	(x), y
                                   1612 ;	decoder.c: 361: yfa = map_y(p.fa);
      008A91 1E 11            [ 2] 1613 	ldw	x, (0x11, sp)
      008A93 CD 85 73         [ 4] 1614 	call	_map_y
      008A96 1F 37            [ 2] 1615 	ldw	(0x37, sp), x
      008A98 17 35            [ 2] 1616 	ldw	(0x35, sp), y
                                   1617 ;	decoder.c: 362: yfb = map_y(p.fb);
      008A9A 1E 13            [ 2] 1618 	ldw	x, (0x13, sp)
      008A9C CD 85 73         [ 4] 1619 	call	_map_y
      008A9F 17 09            [ 2] 1620 	ldw	(0x09, sp), y
                                   1621 ;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
      008AA1 16 20            [ 2] 1622 	ldw	y, (0x20, sp)
      008AA3 90 F6            [ 1] 1623 	ld	a, (y)
      008AA5 6B 32            [ 1] 1624 	ld	(0x32, sp), a
                                   1625 ;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
      008AA7 16 37            [ 2] 1626 	ldw	y, (0x37, sp)
      008AA9 17 33            [ 2] 1627 	ldw	(0x33, sp), y
                                   1628 ;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
      008AAB 1F 35            [ 2] 1629 	ldw	(0x35, sp), x
                                   1630 ;	decoder.c: 367: s->p_fam = p.sfa;
                                   1631 ;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
      008AAD 0D 32            [ 1] 1632 	tnz	(0x32, sp)
      008AAF 27 3D            [ 1] 1633 	jreq	00111$
      008AB1 1E 1A            [ 2] 1634 	ldw	x, (0x1a, sp)
      008AB3 FE               [ 2] 1635 	ldw	x, (x)
      008AB4 16 1C            [ 2] 1636 	ldw	y, (0x1c, sp)
      008AB6 90 FE            [ 2] 1637 	ldw	y, (y)
      008AB8 17 37            [ 2] 1638 	ldw	(0x37, sp), y
      008ABA 13 37            [ 2] 1639 	cpw	x, (0x37, sp)
      008ABC 26 30            [ 1] 1640 	jrne	00111$
                                   1641 ;	decoder.c: 364: base = (uint32_t)BIAS_U + (uint32_t)s->p_k0 * BIT_U;
      008ABE 1E 37            [ 2] 1642 	ldw	x, (0x37, sp)
      008AC0 5E               [ 1] 1643 	swapw	x
      008AC1 4F               [ 1] 1644 	clr	a
      008AC2 0F 2F            [ 1] 1645 	clr	(0x2f, sp)
      008AC4 41               [ 1] 1646 	exg	a, xl
      008AC5 6B 2C            [ 1] 1647 	ld	(0x2c, sp), a
      008AC7 41               [ 1] 1648 	exg	a, xl
      008AC8 6B 2B            [ 1] 1649 	ld	(0x2b, sp), a
      008ACA 4F               [ 1] 1650 	clr	a
      008ACB 97               [ 1] 1651 	ld	xl, a
      008ACC 58               [ 2] 1652 	sllw	x
      008ACD 09 2C            [ 1] 1653 	rlc	(0x2c, sp)
      008ACF 09 2B            [ 1] 1654 	rlc	(0x2b, sp)
      008AD1 1C 02 00         [ 2] 1655 	addw	x, #0x0200
                                   1656 ;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
      008AD4 1F 37            [ 2] 1657 	ldw	(0x37, sp), x
      008AD6 16 33            [ 2] 1658 	ldw	y, (0x33, sp)
      008AD8 72 F2 37         [ 2] 1659 	subw	y, (0x37, sp)
      008ADB 1E 22            [ 2] 1660 	ldw	x, (0x22, sp)
      008ADD FF               [ 2] 1661 	ldw	(x), y
                                   1662 ;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
      008ADE 16 35            [ 2] 1663 	ldw	y, (0x35, sp)
      008AE0 72 F2 37         [ 2] 1664 	subw	y, (0x37, sp)
      008AE3 1E 24            [ 2] 1665 	ldw	x, (0x24, sp)
      008AE5 FF               [ 2] 1666 	ldw	(x), y
                                   1667 ;	decoder.c: 367: s->p_fam = p.sfa;
      008AE6 7B 15            [ 1] 1668 	ld	a, (0x15, sp)
      008AE8 1E 26            [ 2] 1669 	ldw	x, (0x26, sp)
      008AEA F7               [ 1] 1670 	ld	(x), a
                                   1671 ;	decoder.c: 368: continue;
      008AEB CC 89 A0         [ 2] 1672 	jp	00119$
      008AEE                       1673 00111$:
                                   1674 ;	decoder.c: 370: if (s->pend) {
      008AEE 0D 32            [ 1] 1675 	tnz	(0x32, sp)
      008AF0 26 03            [ 1] 1676 	jrne	00244$
      008AF2 CC 8B 77         [ 2] 1677 	jp	00116$
      008AF5                       1678 00244$:
                                   1679 ;	decoder.c: 371: out->k0 = s->p_k0;
      008AF5 16 1C            [ 2] 1680 	ldw	y, (0x1c, sp)
      008AF7 17 37            [ 2] 1681 	ldw	(0x37, sp), y
      008AF9 1E 1C            [ 2] 1682 	ldw	x, (0x1c, sp)
      008AFB FE               [ 2] 1683 	ldw	x, (x)
      008AFC 16 28            [ 2] 1684 	ldw	y, (0x28, sp)
      008AFE 90 FF            [ 2] 1685 	ldw	(y), x
                                   1686 ;	decoder.c: 372: out->k1 = (s->n < NB) ? s->n : NB;
      008B00 16 1A            [ 2] 1687 	ldw	y, (0x1a, sp)
      008B02 17 28            [ 2] 1688 	ldw	(0x28, sp), y
      008B04 1E 1A            [ 2] 1689 	ldw	x, (0x1a, sp)
      008B06 FE               [ 2] 1690 	ldw	x, (x)
      008B07 1F 1C            [ 2] 1691 	ldw	(0x1c, sp), x
      008B09 A3 01 C0         [ 2] 1692 	cpw	x, #0x01c0
      008B0C 25 05            [ 1] 1693 	jrc	00127$
      008B0E AE 01 C0         [ 2] 1694 	ldw	x, #0x01c0
      008B11 1F 1C            [ 2] 1695 	ldw	(0x1c, sp), x
      008B13                       1696 00127$:
      008B13 16 1C            [ 2] 1697 	ldw	y, (0x1c, sp)
      008B15 1E 2A            [ 2] 1698 	ldw	x, (0x2a, sp)
      008B17 FF               [ 2] 1699 	ldw	(x), y
                                   1700 ;	decoder.c: 373: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
      008B18 1E 22            [ 2] 1701 	ldw	x, (0x22, sp)
      008B1A FE               [ 2] 1702 	ldw	x, (x)
      008B1B 16 2C            [ 2] 1703 	ldw	y, (0x2c, sp)
      008B1D 90 FF            [ 2] 1704 	ldw	(y), x
      008B1F 1E 24            [ 2] 1705 	ldw	x, (0x24, sp)
      008B21 FE               [ 2] 1706 	ldw	x, (x)
      008B22 16 2E            [ 2] 1707 	ldw	y, (0x2e, sp)
      008B24 90 FF            [ 2] 1708 	ldw	(y), x
      008B26 1E 26            [ 2] 1709 	ldw	x, (0x26, sp)
      008B28 F6               [ 1] 1710 	ld	a, (x)
      008B29 1E 30            [ 2] 1711 	ldw	x, (0x30, sp)
      008B2B F7               [ 1] 1712 	ld	(x), a
                                   1713 ;	decoder.c: 375: if (s->n >= NB) { s->pend = 0; s->src_done = 1; return 1; }
      008B2C 1E 28            [ 2] 1714 	ldw	x, (0x28, sp)
      008B2E FE               [ 2] 1715 	ldw	x, (x)
      008B2F 1F 31            [ 2] 1716 	ldw	(0x31, sp), x
      008B31 A3 01 C0         [ 2] 1717 	cpw	x, #0x01c0
      008B34 25 0B            [ 1] 1718 	jrc	00114$
      008B36 1E 20            [ 2] 1719 	ldw	x, (0x20, sp)
      008B38 7F               [ 1] 1720 	clr	(x)
      008B39 1E 1E            [ 2] 1721 	ldw	x, (0x1e, sp)
      008B3B A6 01            [ 1] 1722 	ld	a, #0x01
      008B3D F7               [ 1] 1723 	ld	(x), a
      008B3E CC 8B F3         [ 2] 1724 	jp	00124$
      008B41                       1725 00114$:
                                   1726 ;	decoder.c: 376: base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
      008B41 16 31            [ 2] 1727 	ldw	y, (0x31, sp)
      008B43 5F               [ 1] 1728 	clrw	x
      008B44 4F               [ 1] 1729 	clr	a
      008B45 48               [ 1] 1730 	sll	a
      008B46 90 59            [ 2] 1731 	rlcw	y
      008B48 59               [ 2] 1732 	rlcw	x
      008B49 6B 30            [ 1] 1733 	ld	(0x30, sp), a
      008B4B 72 A9 00 02      [ 2] 1734 	addw	y, #0x0002
      008B4F 17 2E            [ 2] 1735 	ldw	(0x2e, sp), y
      008B51 9F               [ 1] 1736 	ld	a, xl
      008B52 A9 00            [ 1] 1737 	adc	a, #0x00
                                   1738 ;	decoder.c: 377: s->p_k0 = s->n;
      008B54 1E 37            [ 2] 1739 	ldw	x, (0x37, sp)
      008B56 16 31            [ 2] 1740 	ldw	y, (0x31, sp)
      008B58 FF               [ 2] 1741 	ldw	(x), y
                                   1742 ;	decoder.c: 378: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
      008B59 16 2F            [ 2] 1743 	ldw	y, (0x2f, sp)
      008B5B 17 37            [ 2] 1744 	ldw	(0x37, sp), y
      008B5D 16 33            [ 2] 1745 	ldw	y, (0x33, sp)
      008B5F 72 F2 37         [ 2] 1746 	subw	y, (0x37, sp)
      008B62 1E 22            [ 2] 1747 	ldw	x, (0x22, sp)
      008B64 FF               [ 2] 1748 	ldw	(x), y
                                   1749 ;	decoder.c: 379: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
      008B65 16 35            [ 2] 1750 	ldw	y, (0x35, sp)
      008B67 72 F2 37         [ 2] 1751 	subw	y, (0x37, sp)
      008B6A 1E 24            [ 2] 1752 	ldw	x, (0x24, sp)
      008B6C FF               [ 2] 1753 	ldw	(x), y
                                   1754 ;	decoder.c: 380: s->p_fam = p.sfa;
      008B6D 7B 15            [ 1] 1755 	ld	a, (0x15, sp)
      008B6F 1E 26            [ 2] 1756 	ldw	x, (0x26, sp)
      008B71 F7               [ 1] 1757 	ld	(x), a
                                   1758 ;	decoder.c: 381: return 1;
      008B72 A6 01            [ 1] 1759 	ld	a, #0x01
      008B74 CC 8B F3         [ 2] 1760 	jp	00124$
      008B77                       1761 00116$:
                                   1762 ;	decoder.c: 383: if (s->n >= NB) { s->src_done = 1; break; }
      008B77 1E 1A            [ 2] 1763 	ldw	x, (0x1a, sp)
      008B79 FE               [ 2] 1764 	ldw	x, (x)
      008B7A 1F 37            [ 2] 1765 	ldw	(0x37, sp), x
      008B7C A3 01 C0         [ 2] 1766 	cpw	x, #0x01c0
      008B7F 25 07            [ 1] 1767 	jrc	00118$
      008B81 1E 1E            [ 2] 1768 	ldw	x, (0x1e, sp)
      008B83 A6 01            [ 1] 1769 	ld	a, #0x01
      008B85 F7               [ 1] 1770 	ld	(x), a
      008B86 20 3D            [ 2] 1771 	jra	00121$
      008B88                       1772 00118$:
                                   1773 ;	decoder.c: 384: base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
      008B88 16 37            [ 2] 1774 	ldw	y, (0x37, sp)
      008B8A 5F               [ 1] 1775 	clrw	x
      008B8B 4F               [ 1] 1776 	clr	a
      008B8C 48               [ 1] 1777 	sll	a
      008B8D 90 59            [ 2] 1778 	rlcw	y
      008B8F 59               [ 2] 1779 	rlcw	x
      008B90 6B 32            [ 1] 1780 	ld	(0x32, sp), a
      008B92 72 A9 00 02      [ 2] 1781 	addw	y, #0x0002
      008B96 17 30            [ 2] 1782 	ldw	(0x30, sp), y
      008B98 9F               [ 1] 1783 	ld	a, xl
      008B99 A9 00            [ 1] 1784 	adc	a, #0x00
      008B9B 6B 2F            [ 1] 1785 	ld	(0x2f, sp), a
                                   1786 ;	decoder.c: 385: s->pend = 1;
      008B9D 1E 20            [ 2] 1787 	ldw	x, (0x20, sp)
      008B9F A6 01            [ 1] 1788 	ld	a, #0x01
      008BA1 F7               [ 1] 1789 	ld	(x), a
                                   1790 ;	decoder.c: 386: s->p_k0 = s->n;
      008BA2 1E 1A            [ 2] 1791 	ldw	x, (0x1a, sp)
      008BA4 FE               [ 2] 1792 	ldw	x, (x)
      008BA5 16 1C            [ 2] 1793 	ldw	y, (0x1c, sp)
      008BA7 90 FF            [ 2] 1794 	ldw	(y), x
                                   1795 ;	decoder.c: 387: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
      008BA9 16 31            [ 2] 1796 	ldw	y, (0x31, sp)
      008BAB 17 37            [ 2] 1797 	ldw	(0x37, sp), y
      008BAD 16 33            [ 2] 1798 	ldw	y, (0x33, sp)
      008BAF 72 F2 37         [ 2] 1799 	subw	y, (0x37, sp)
      008BB2 1E 22            [ 2] 1800 	ldw	x, (0x22, sp)
      008BB4 FF               [ 2] 1801 	ldw	(x), y
                                   1802 ;	decoder.c: 388: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
      008BB5 16 35            [ 2] 1803 	ldw	y, (0x35, sp)
      008BB7 72 F2 37         [ 2] 1804 	subw	y, (0x37, sp)
      008BBA 1E 24            [ 2] 1805 	ldw	x, (0x24, sp)
      008BBC FF               [ 2] 1806 	ldw	(x), y
                                   1807 ;	decoder.c: 389: s->p_fam = p.sfa;
      008BBD 7B 15            [ 1] 1808 	ld	a, (0x15, sp)
      008BBF 1E 26            [ 2] 1809 	ldw	x, (0x26, sp)
      008BC1 F7               [ 1] 1810 	ld	(x), a
      008BC2 CC 89 A0         [ 2] 1811 	jp	00119$
      008BC5                       1812 00121$:
                                   1813 ;	decoder.c: 391: if (s->pend) {
      008BC5 1E 20            [ 2] 1814 	ldw	x, (0x20, sp)
      008BC7 F6               [ 1] 1815 	ld	a, (x)
      008BC8 27 28            [ 1] 1816 	jreq	00123$
                                   1817 ;	decoder.c: 392: s->pend = 0;
      008BCA 1E 20            [ 2] 1818 	ldw	x, (0x20, sp)
      008BCC 7F               [ 1] 1819 	clr	(x)
                                   1820 ;	decoder.c: 393: out->k0 = s->p_k0; out->k1 = NB;
      008BCD 1E 1C            [ 2] 1821 	ldw	x, (0x1c, sp)
      008BCF FE               [ 2] 1822 	ldw	x, (x)
      008BD0 16 28            [ 2] 1823 	ldw	y, (0x28, sp)
      008BD2 90 FF            [ 2] 1824 	ldw	(y), x
      008BD4 1E 2A            [ 2] 1825 	ldw	x, (0x2a, sp)
      008BD6 90 AE 01 C0      [ 2] 1826 	ldw	y, #0x01c0
      008BDA FF               [ 2] 1827 	ldw	(x), y
                                   1828 ;	decoder.c: 394: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
      008BDB 1E 22            [ 2] 1829 	ldw	x, (0x22, sp)
      008BDD FE               [ 2] 1830 	ldw	x, (x)
      008BDE 16 2C            [ 2] 1831 	ldw	y, (0x2c, sp)
      008BE0 90 FF            [ 2] 1832 	ldw	(y), x
      008BE2 1E 24            [ 2] 1833 	ldw	x, (0x24, sp)
      008BE4 FE               [ 2] 1834 	ldw	x, (x)
      008BE5 16 2E            [ 2] 1835 	ldw	y, (0x2e, sp)
      008BE7 90 FF            [ 2] 1836 	ldw	(y), x
      008BE9 1E 26            [ 2] 1837 	ldw	x, (0x26, sp)
      008BEB F6               [ 1] 1838 	ld	a, (x)
      008BEC 1E 30            [ 2] 1839 	ldw	x, (0x30, sp)
      008BEE F7               [ 1] 1840 	ld	(x), a
                                   1841 ;	decoder.c: 395: return 1;
      008BEF A6 01            [ 1] 1842 	ld	a, #0x01
                                   1843 ;	decoder.c: 397: return 0;
      008BF1 21                    1844 	.byte 0x21
      008BF2                       1845 00123$:
      008BF2 4F               [ 1] 1846 	clr	a
      008BF3                       1847 00124$:
                                   1848 ;	decoder.c: 398: }
      008BF3 1E 3B            [ 2] 1849 	ldw	x, (59, sp)
      008BF5 5B 3E            [ 2] 1850 	addw	sp, #62
      008BF7 FC               [ 2] 1851 	jp	(x)
                                   1852 ;	decoder.c: 402: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
                                   1853 ;	-----------------------------------------
                                   1854 ;	 function a_bounds
                                   1855 ;	-----------------------------------------
      008BF8                       1856 _a_bounds:
      008BF8 52 0C            [ 2] 1857 	sub	sp, #12
      008BFA 1F 09            [ 2] 1858 	ldw	(0x09, sp), x
                                   1859 ;	decoder.c: 404: uint16_t t, e = (k1 < NB) ? k1 : NB;
      008BFC 1E 0F            [ 2] 1860 	ldw	x, (0x0f, sp)
      008BFE A3 01 C0         [ 2] 1861 	cpw	x, #0x01c0
      008C01 25 03            [ 1] 1862 	jrc	00117$
      008C03 AE 01 C0         [ 2] 1863 	ldw	x, #0x01c0
      008C06                       1864 00117$:
      008C06 1F 01            [ 2] 1865 	ldw	(0x01, sp), x
                                   1866 ;	decoder.c: 405: *amin = 0;
      008C08 16 11            [ 2] 1867 	ldw	y, (0x11, sp)
      008C0A 17 03            [ 2] 1868 	ldw	(0x03, sp), y
      008C0C 93               [ 1] 1869 	ldw	x, y
      008C0D 6F 01            [ 1] 1870 	clr	(0x1, x)
      008C0F 7F               [ 1] 1871 	clr	(x)
                                   1872 ;	decoder.c: 406: *amax = (int16_t)(k1 - k0);
      008C10 16 13            [ 2] 1873 	ldw	y, (0x13, sp)
      008C12 17 05            [ 2] 1874 	ldw	(0x05, sp), y
      008C14 16 0F            [ 2] 1875 	ldw	y, (0x0f, sp)
      008C16 72 F2 09         [ 2] 1876 	subw	y, (0x09, sp)
      008C19 1E 05            [ 2] 1877 	ldw	x, (0x05, sp)
      008C1B FF               [ 2] 1878 	ldw	(x), y
                                   1879 ;	decoder.c: 407: for (t = k0; t < e; t++) {
      008C1C 16 09            [ 2] 1880 	ldw	y, (0x09, sp)
      008C1E 17 0B            [ 2] 1881 	ldw	(0x0b, sp), y
      008C20                       1882 00112$:
                                   1883 ;	decoder.c: 408: int8_t kb = known_bit(t);
      008C20 1E 0B            [ 2] 1884 	ldw	x, (0x0b, sp)
      008C22 13 01            [ 2] 1885 	cpw	x, (0x01, sp)
      008C24 24 38            [ 1] 1886 	jrnc	00114$
      008C26 CD 81 93         [ 4] 1887 	call	_known_bit
                                   1888 ;	decoder.c: 410: int16_t m = (int16_t)(t - k0 + 1);
      008C29 16 0B            [ 2] 1889 	ldw	y, (0x0b, sp)
      008C2B 72 F2 09         [ 2] 1890 	subw	y, (0x09, sp)
                                   1891 ;	decoder.c: 409: if (kb == 1) {
      008C2E A1 01            [ 1] 1892 	cp	a, #0x01
      008C30 26 14            [ 1] 1893 	jrne	00108$
                                   1894 ;	decoder.c: 410: int16_t m = (int16_t)(t - k0 + 1);
      008C32 17 07            [ 2] 1895 	ldw	(0x07, sp), y
      008C34 93               [ 1] 1896 	ldw	x, y
      008C35 5C               [ 1] 1897 	incw	x
                                   1898 ;	decoder.c: 411: if (m > *amin) *amin = m;
      008C36 16 03            [ 2] 1899 	ldw	y, (0x03, sp)
      008C38 90 FE            [ 2] 1900 	ldw	y, (y)
      008C3A 17 07            [ 2] 1901 	ldw	(0x07, sp), y
      008C3C 13 07            [ 2] 1902 	cpw	x, (0x07, sp)
      008C3E 2D 17            [ 1] 1903 	jrsle	00113$
      008C40 16 03            [ 2] 1904 	ldw	y, (0x03, sp)
      008C42 90 FF            [ 2] 1905 	ldw	(y), x
      008C44 20 11            [ 2] 1906 	jra	00113$
      008C46                       1907 00108$:
                                   1908 ;	decoder.c: 412: } else if (kb == 0) {
      008C46 4D               [ 1] 1909 	tnz	a
      008C47 26 0E            [ 1] 1910 	jrne	00113$
                                   1911 ;	decoder.c: 413: int16_t m = (int16_t)(t - k0);
                                   1912 ;	decoder.c: 414: if (m < *amax) *amax = m;
      008C49 1E 05            [ 2] 1913 	ldw	x, (0x05, sp)
      008C4B FE               [ 2] 1914 	ldw	x, (x)
      008C4C 1F 07            [ 2] 1915 	ldw	(0x07, sp), x
      008C4E 51               [ 1] 1916 	exgw	x, y
      008C4F 13 07            [ 2] 1917 	cpw	x, (0x07, sp)
      008C51 51               [ 1] 1918 	exgw	x, y
      008C52 2E 03            [ 1] 1919 	jrsge	00113$
      008C54 1E 05            [ 2] 1920 	ldw	x, (0x05, sp)
      008C56 FF               [ 2] 1921 	ldw	(x), y
      008C57                       1922 00113$:
                                   1923 ;	decoder.c: 407: for (t = k0; t < e; t++) {
      008C57 1E 0B            [ 2] 1924 	ldw	x, (0x0b, sp)
      008C59 5C               [ 1] 1925 	incw	x
      008C5A 1F 0B            [ 2] 1926 	ldw	(0x0b, sp), x
      008C5C 20 C2            [ 2] 1927 	jra	00112$
      008C5E                       1928 00114$:
                                   1929 ;	decoder.c: 417: }
      008C5E 1E 0D            [ 2] 1930 	ldw	x, (13, sp)
      008C60 5B 14            [ 2] 1931 	addw	sp, #20
      008C62 FC               [ 2] 1932 	jp	(x)
                                   1933 ;	decoder.c: 422: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   1934 ;	-----------------------------------------
                                   1935 ;	 function label_interval
                                   1936 ;	-----------------------------------------
      008C63                       1937 _label_interval:
      008C63 52 0A            [ 2] 1938 	sub	sp, #10
                                   1939 ;	decoder.c: 425: int16_t L = (int16_t)(k1 - k0);
      008C65 50               [ 2] 1940 	negw	x
      008C66 72 FB 0D         [ 2] 1941 	addw	x, (0x0d, sp)
      008C69 1F 09            [ 2] 1942 	ldw	(0x09, sp), x
                                   1943 ;	decoder.c: 427: if (a == 0) { *lo = u; *hi = v; return 0; }
      008C6B 16 17            [ 2] 1944 	ldw	y, (0x17, sp)
      008C6D 17 01            [ 2] 1945 	ldw	(0x01, sp), y
      008C6F 1E 13            [ 2] 1946 	ldw	x, (0x13, sp)
      008C71 26 0E            [ 1] 1947 	jrne	00102$
      008C73 1E 15            [ 2] 1948 	ldw	x, (0x15, sp)
      008C75 16 0F            [ 2] 1949 	ldw	y, (0x0f, sp)
      008C77 FF               [ 2] 1950 	ldw	(x), y
      008C78 1E 01            [ 2] 1951 	ldw	x, (0x01, sp)
      008C7A 16 11            [ 2] 1952 	ldw	y, (0x11, sp)
      008C7C FF               [ 2] 1953 	ldw	(x), y
      008C7D 4F               [ 1] 1954 	clr	a
      008C7E CC 8D 39         [ 2] 1955 	jp	00113$
      008C81                       1956 00102$:
                                   1957 ;	decoder.c: 428: if (a == L) {
      008C81 1E 13            [ 2] 1958 	ldw	x, (0x13, sp)
      008C83 13 09            [ 2] 1959 	cpw	x, (0x09, sp)
      008C85 26 1D            [ 1] 1960 	jrne	00104$
                                   1961 ;	decoder.c: 429: off = (int16_t)((L - 1) * BIT_U);
      008C87 1E 09            [ 2] 1962 	ldw	x, (0x09, sp)
      008C89 5A               [ 2] 1963 	decw	x
      008C8A 4F               [ 1] 1964 	clr	a
      008C8B 02               [ 1] 1965 	rlwa	x
      008C8C 58               [ 2] 1966 	sllw	x
      008C8D 1F 09            [ 2] 1967 	ldw	(0x09, sp), x
                                   1968 ;	decoder.c: 430: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      008C8F 16 0F            [ 2] 1969 	ldw	y, (0x0f, sp)
      008C91 72 F2 09         [ 2] 1970 	subw	y, (0x09, sp)
      008C94 1E 15            [ 2] 1971 	ldw	x, (0x15, sp)
      008C96 FF               [ 2] 1972 	ldw	(x), y
      008C97 16 11            [ 2] 1973 	ldw	y, (0x11, sp)
      008C99 72 F2 09         [ 2] 1974 	subw	y, (0x09, sp)
      008C9C 1E 01            [ 2] 1975 	ldw	x, (0x01, sp)
      008C9E FF               [ 2] 1976 	ldw	(x), y
                                   1977 ;	decoder.c: 431: return 1;
      008C9F A6 01            [ 1] 1978 	ld	a, #0x01
      008CA1 CC 8D 39         [ 2] 1979 	jp	00113$
      008CA4                       1980 00104$:
                                   1981 ;	decoder.c: 433: mid = (int16_t)((u + v) >> 1);
      008CA4 16 0F            [ 2] 1982 	ldw	y, (0x0f, sp)
      008CA6 72 F9 11         [ 2] 1983 	addw	y, (0x11, sp)
      008CA9 90 57            [ 2] 1984 	sraw	y
                                   1985 ;	decoder.c: 434: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
      008CAB 1E 13            [ 2] 1986 	ldw	x, (0x13, sp)
      008CAD 1F 09            [ 2] 1987 	ldw	(0x09, sp), x
      008CAF 5A               [ 2] 1988 	decw	x
      008CB0 41               [ 1] 1989 	exg	a, xl
      008CB1 6B 03            [ 1] 1990 	ld	(0x03, sp), a
      008CB3 41               [ 1] 1991 	exg	a, xl
      008CB4 0F 04            [ 1] 1992 	clr	(0x04, sp)
      008CB6 08 04            [ 1] 1993 	sll	(0x04, sp)
      008CB8 09 03            [ 1] 1994 	rlc	(0x03, sp)
      008CBA 1E 03            [ 2] 1995 	ldw	x, (0x03, sp)
      008CBC 1C 01 34         [ 2] 1996 	addw	x, #0x0134
      008CBF 1F 07            [ 2] 1997 	ldw	(0x07, sp), x
      008CC1 93               [ 1] 1998 	ldw	x, y
      008CC2 72 F0 07         [ 2] 1999 	subw	x, (0x07, sp)
                                   2000 ;	decoder.c: 435: if (d1 < 0) d1 = (int16_t)-d1;
      008CC5 1F 07            [ 2] 2001 	ldw	(0x07, sp), x
      008CC7 5D               [ 2] 2002 	tnzw	x
      008CC8 2A 07            [ 1] 2003 	jrpl	00106$
      008CCA 00 08            [ 1] 2004 	neg	(0x08, sp)
      008CCC 4F               [ 1] 2005 	clr	a
      008CCD 12 07            [ 1] 2006 	sbc	a, (0x07, sp)
      008CCF 6B 07            [ 1] 2007 	ld	(0x07, sp), a
      008CD1                       2008 00106$:
                                   2009 ;	decoder.c: 436: d0 = (int16_t)(mid - (a * BIT_U + H0P));
      008CD1 7B 0A            [ 1] 2010 	ld	a, (0x0a, sp)
      008CD3 6B 05            [ 1] 2011 	ld	(0x05, sp), a
      008CD5 0F 06            [ 1] 2012 	clr	(0x06, sp)
      008CD7 08 06            [ 1] 2013 	sll	(0x06, sp)
      008CD9 09 05            [ 1] 2014 	rlc	(0x05, sp)
      008CDB 1E 05            [ 2] 2015 	ldw	x, (0x05, sp)
      008CDD 1C 00 9A         [ 2] 2016 	addw	x, #0x009a
      008CE0 1F 09            [ 2] 2017 	ldw	(0x09, sp), x
      008CE2 72 F2 09         [ 2] 2018 	subw	y, (0x09, sp)
                                   2019 ;	decoder.c: 437: if (d0 < 0) d0 = (int16_t)-d0;
      008CE5 17 09            [ 2] 2020 	ldw	(0x09, sp), y
      008CE7 93               [ 1] 2021 	ldw	x, y
      008CE8 5D               [ 2] 2022 	tnzw	x
      008CE9 2A 07            [ 1] 2023 	jrpl	00108$
      008CEB 00 0A            [ 1] 2024 	neg	(0x0a, sp)
      008CED 4F               [ 1] 2025 	clr	a
      008CEE 12 09            [ 1] 2026 	sbc	a, (0x09, sp)
      008CF0 6B 09            [ 1] 2027 	ld	(0x09, sp), a
      008CF2                       2028 00108$:
                                   2029 ;	decoder.c: 438: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
      008CF2 1E 09            [ 2] 2030 	ldw	x, (0x09, sp)
      008CF4 13 07            [ 2] 2031 	cpw	x, (0x07, sp)
      008CF6 2E 03            [ 1] 2032 	jrsge	00115$
      008CF8 1E 09            [ 2] 2033 	ldw	x, (0x09, sp)
      008CFA C5                    2034 	.byte 0xc5
      008CFB                       2035 00115$:
      008CFB 1E 07            [ 2] 2036 	ldw	x, (0x07, sp)
      008CFD                       2037 00116$:
      008CFD A3 00 F6         [ 2] 2038 	cpw	x, #0x00f6
      008D00 2D 04            [ 1] 2039 	jrsle	00110$
      008D02 A6 FF            [ 1] 2040 	ld	a, #0xff
      008D04 20 33            [ 2] 2041 	jra	00113$
      008D06                       2042 00110$:
                                   2043 ;	decoder.c: 439: if (d1 <= d0) {
      008D06 1E 07            [ 2] 2044 	ldw	x, (0x07, sp)
      008D08 13 09            [ 2] 2045 	cpw	x, (0x09, sp)
      008D0A 2C 18            [ 1] 2046 	jrsgt	00112$
                                   2047 ;	decoder.c: 440: off = (int16_t)((a - 1) * BIT_U);
      008D0C 16 03            [ 2] 2048 	ldw	y, (0x03, sp)
      008D0E 17 09            [ 2] 2049 	ldw	(0x09, sp), y
                                   2050 ;	decoder.c: 441: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      008D10 16 0F            [ 2] 2051 	ldw	y, (0x0f, sp)
      008D12 72 F2 09         [ 2] 2052 	subw	y, (0x09, sp)
      008D15 1E 15            [ 2] 2053 	ldw	x, (0x15, sp)
      008D17 FF               [ 2] 2054 	ldw	(x), y
      008D18 16 11            [ 2] 2055 	ldw	y, (0x11, sp)
      008D1A 72 F2 09         [ 2] 2056 	subw	y, (0x09, sp)
      008D1D 1E 01            [ 2] 2057 	ldw	x, (0x01, sp)
      008D1F FF               [ 2] 2058 	ldw	(x), y
                                   2059 ;	decoder.c: 442: return 1;
      008D20 A6 01            [ 1] 2060 	ld	a, #0x01
      008D22 20 15            [ 2] 2061 	jra	00113$
      008D24                       2062 00112$:
                                   2063 ;	decoder.c: 444: off = (int16_t)(a * BIT_U);
      008D24 16 05            [ 2] 2064 	ldw	y, (0x05, sp)
      008D26 17 09            [ 2] 2065 	ldw	(0x09, sp), y
                                   2066 ;	decoder.c: 445: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
      008D28 16 0F            [ 2] 2067 	ldw	y, (0x0f, sp)
      008D2A 72 F2 09         [ 2] 2068 	subw	y, (0x09, sp)
      008D2D 1E 15            [ 2] 2069 	ldw	x, (0x15, sp)
      008D2F FF               [ 2] 2070 	ldw	(x), y
      008D30 16 11            [ 2] 2071 	ldw	y, (0x11, sp)
      008D32 72 F2 09         [ 2] 2072 	subw	y, (0x09, sp)
      008D35 1E 01            [ 2] 2073 	ldw	x, (0x01, sp)
      008D37 FF               [ 2] 2074 	ldw	(x), y
                                   2075 ;	decoder.c: 446: return 0;
      008D38 4F               [ 1] 2076 	clr	a
      008D39                       2077 00113$:
                                   2078 ;	decoder.c: 447: }
      008D39 1E 0B            [ 2] 2079 	ldw	x, (11, sp)
      008D3B 5B 18            [ 2] 2080 	addw	sp, #24
      008D3D FC               [ 2] 2081 	jp	(x)
                                   2082 ;	decoder.c: 449: static void cal_cloud(int16_t u, uint8_t fam)
                                   2083 ;	-----------------------------------------
                                   2084 ;	 function cal_cloud
                                   2085 ;	-----------------------------------------
      008D3E                       2086 _cal_cloud:
      008D3E 89               [ 2] 2087 	pushw	x
                                   2088 ;	decoder.c: 453: if (fam != 5 && fam != 6) return;
      008D3F A1 05            [ 1] 2089 	cp	a, #0x05
      008D41 27 04            [ 1] 2090 	jreq	00102$
      008D43 A1 06            [ 1] 2091 	cp	a, #0x06
      008D45 26 3C            [ 1] 2092 	jrne	00111$
      008D47                       2093 00102$:
                                   2094 ;	decoder.c: 454: if (u < 0) return;
      008D47 5D               [ 2] 2095 	tnzw	x
      008D48 2B 39            [ 1] 2096 	jrmi	00111$
                                   2097 ;	decoder.c: 455: f = (uint8_t)(fam - 5);
      008D4A A0 05            [ 1] 2098 	sub	a, #0x05
      008D4C 90 97            [ 1] 2099 	ld	yl, a
                                   2100 ;	decoder.c: 456: x = (int16_t)(u & (BIT_U - 1));
      008D4E 9E               [ 1] 2101 	ld	a, xh
      008D4F A4 01            [ 1] 2102 	and	a, #0x01
      008D51 95               [ 1] 2103 	ld	xh, a
      008D52 1F 01            [ 2] 2104 	ldw	(0x01, sp), x
                                   2105 ;	decoder.c: 457: d = (int16_t)(x - c_c0[f]);
      008D54 93               [ 1] 2106 	ldw	x, y
      008D55 4F               [ 1] 2107 	clr	a
      008D56 95               [ 1] 2108 	ld	xh, a
      008D57 58               [ 2] 2109 	sllw	x
      008D58 DE 01 D6         [ 2] 2110 	ldw	x, (_c_c0+0, x)
      008D5B 50               [ 2] 2111 	negw	x
      008D5C 72 FB 01         [ 2] 2112 	addw	x, (0x01, sp)
                                   2113 ;	decoder.c: 458: if (d >= -EPS_HIST && d < EPS_HIST) {
      008D5F A3 FF C0         [ 2] 2114 	cpw	x, #0xffc0
      008D62 2F 1F            [ 1] 2115 	jrslt	00111$
      008D64 A3 00 40         [ 2] 2116 	cpw	x, #0x0040
      008D67 2E 1A            [ 1] 2117 	jrsge	00111$
                                   2118 ;	decoder.c: 459: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
      008D69 1C 00 40         [ 2] 2119 	addw	x, #0x0040
      008D6C 57               [ 2] 2120 	sraw	x
                                   2121 ;	decoder.c: 460: if (c_hist[f][b] < 255) c_hist[f][b]++;
      008D6D A6 40            [ 1] 2122 	ld	a, #0x40
      008D6F 90 42            [ 4] 2123 	mul	y, a
      008D71 72 A9 01 46      [ 2] 2124 	addw	y, #(_c_hist+0)
      008D75 17 01            [ 2] 2125 	ldw	(0x01, sp), y
      008D77 4F               [ 1] 2126 	clr	a
      008D78 95               [ 1] 2127 	ld	xh, a
      008D79 72 FB 01         [ 2] 2128 	addw	x, (0x01, sp)
      008D7C F6               [ 1] 2129 	ld	a, (x)
      008D7D A1 FF            [ 1] 2130 	cp	a, #0xff
      008D7F 24 02            [ 1] 2131 	jrnc	00111$
      008D81 4C               [ 1] 2132 	inc	a
      008D82 F7               [ 1] 2133 	ld	(x), a
      008D83                       2134 00111$:
                                   2135 ;	decoder.c: 462: }
      008D83 85               [ 2] 2136 	popw	x
      008D84 81               [ 4] 2137 	ret
                                   2138 ;	decoder.c: 464: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   2139 ;	-----------------------------------------
                                   2140 ;	 function cal_add
                                   2141 ;	-----------------------------------------
      008D85                       2142 _cal_add:
      008D85 52 0C            [ 2] 2143 	sub	sp, #12
      008D87 51               [ 1] 2144 	exgw	x, y
                                   2145 ;	decoder.c: 468: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
      008D88 96               [ 1] 2146 	ldw	x, sp
      008D89 1C 00 03         [ 2] 2147 	addw	x, #3
      008D8C 89               [ 2] 2148 	pushw	x
      008D8D 96               [ 1] 2149 	ldw	x, sp
      008D8E 1C 00 03         [ 2] 2150 	addw	x, #3
      008D91 89               [ 2] 2151 	pushw	x
      008D92 1E 1A            [ 2] 2152 	ldw	x, (0x1a, sp)
      008D94 89               [ 2] 2153 	pushw	x
      008D95 1E 19            [ 2] 2154 	ldw	x, (0x19, sp)
      008D97 89               [ 2] 2155 	pushw	x
      008D98 1E 19            [ 2] 2156 	ldw	x, (0x19, sp)
      008D9A 89               [ 2] 2157 	pushw	x
      008D9B 1E 19            [ 2] 2158 	ldw	x, (0x19, sp)
      008D9D 89               [ 2] 2159 	pushw	x
      008D9E 93               [ 1] 2160 	ldw	x, y
      008D9F CD 8C 63         [ 4] 2161 	call	_label_interval
                                   2162 ;	decoder.c: 469: if (cls < 0) return;
      008DA2 6B 0A            [ 1] 2163 	ld	(0x0a, sp), a
      008DA4 2A 03            [ 1] 2164 	jrpl	00102$
      008DA6 CC 8E 95         [ 2] 2165 	jp	00138$
      008DA9                       2166 00102$:
                                   2167 ;	decoder.c: 471: if (lo > c_lo0) c_lo0 = lo;
      008DA9 1E 01            [ 2] 2168 	ldw	x, (0x01, sp)
                                   2169 ;	decoder.c: 472: if (hi < c_hi0) c_hi0 = hi;
      008DAB 16 03            [ 2] 2170 	ldw	y, (0x03, sp)
                                   2171 ;	decoder.c: 470: if (cls == 0) {
      008DAD 0D 0A            [ 1] 2172 	tnz	(0x0a, sp)
      008DAF 26 24            [ 1] 2173 	jrne	00116$
                                   2174 ;	decoder.c: 471: if (lo > c_lo0) c_lo0 = lo;
      008DB1 89               [ 2] 2175 	pushw	x
      008DB2 1E 03            [ 2] 2176 	ldw	x, (0x03, sp)
      008DB4 C3 01 36         [ 2] 2177 	cpw	x, _c_lo0+0
      008DB7 85               [ 2] 2178 	popw	x
      008DB8 2D 03            [ 1] 2179 	jrsle	00104$
      008DBA CF 01 36         [ 2] 2180 	ldw	_c_lo0+0, x
      008DBD                       2181 00104$:
                                   2182 ;	decoder.c: 472: if (hi < c_hi0) c_hi0 = hi;
      008DBD 1E 03            [ 2] 2183 	ldw	x, (0x03, sp)
      008DBF C3 01 38         [ 2] 2184 	cpw	x, _c_hi0+0
      008DC2 2E 04            [ 1] 2185 	jrsge	00106$
      008DC4 90 CF 01 38      [ 2] 2186 	ldw	_c_hi0+0, y
      008DC8                       2187 00106$:
                                   2188 ;	decoder.c: 473: if (c_n0 < 255) c_n0++;
      008DC8 C6 01 3E         [ 1] 2189 	ld	a, _c_n0+0
      008DCB A1 FF            [ 1] 2190 	cp	a, #0xff
      008DCD 24 28            [ 1] 2191 	jrnc	00117$
      008DCF 72 5C 01 3E      [ 1] 2192 	inc	_c_n0+0
      008DD3 20 22            [ 2] 2193 	jra	00117$
      008DD5                       2194 00116$:
                                   2195 ;	decoder.c: 475: if (lo > c_lo1) c_lo1 = lo;
      008DD5 89               [ 2] 2196 	pushw	x
      008DD6 1E 03            [ 2] 2197 	ldw	x, (0x03, sp)
      008DD8 C3 01 3A         [ 2] 2198 	cpw	x, _c_lo1+0
      008DDB 85               [ 2] 2199 	popw	x
      008DDC 2D 03            [ 1] 2200 	jrsle	00110$
      008DDE CF 01 3A         [ 2] 2201 	ldw	_c_lo1+0, x
      008DE1                       2202 00110$:
                                   2203 ;	decoder.c: 476: if (hi < c_hi1) c_hi1 = hi;
      008DE1 1E 03            [ 2] 2204 	ldw	x, (0x03, sp)
      008DE3 C3 01 3C         [ 2] 2205 	cpw	x, _c_hi1+0
      008DE6 2E 04            [ 1] 2206 	jrsge	00112$
      008DE8 90 CF 01 3C      [ 2] 2207 	ldw	_c_hi1+0, y
      008DEC                       2208 00112$:
                                   2209 ;	decoder.c: 477: if (c_n1 < 255) c_n1++;
      008DEC C6 01 3F         [ 1] 2210 	ld	a, _c_n1+0
      008DEF A1 FF            [ 1] 2211 	cp	a, #0xff
      008DF1 24 04            [ 1] 2212 	jrnc	00117$
      008DF3 72 5C 01 3F      [ 1] 2213 	inc	_c_n1+0
      008DF7                       2214 00117$:
                                   2215 ;	decoder.c: 479: if ((fam == 5 || fam == 6) && lo >= 0) {
      008DF7 7B 15            [ 1] 2216 	ld	a, (0x15, sp)
      008DF9 A1 05            [ 1] 2217 	cp	a, #0x05
      008DFB 27 09            [ 1] 2218 	jreq	00137$
      008DFD 7B 15            [ 1] 2219 	ld	a, (0x15, sp)
      008DFF A1 06            [ 1] 2220 	cp	a, #0x06
      008E01 27 03            [ 1] 2221 	jreq	00289$
      008E03 CC 8E 95         [ 2] 2222 	jp	00138$
      008E06                       2223 00289$:
      008E06                       2224 00137$:
      008E06 16 01            [ 2] 2225 	ldw	y, (0x01, sp)
      008E08 2A 03            [ 1] 2226 	jrpl	00290$
      008E0A CC 8E 95         [ 2] 2227 	jp	00138$
      008E0D                       2228 00290$:
                                   2229 ;	decoder.c: 480: uint8_t f = (uint8_t)(fam - 5);
      008E0D 7B 15            [ 1] 2230 	ld	a, (0x15, sp)
      008E0F A0 05            [ 1] 2231 	sub	a, #0x05
      008E11 97               [ 1] 2232 	ld	xl, a
                                   2233 ;	decoder.c: 481: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
      008E12 90 9E            [ 1] 2234 	ld	a, yh
      008E14 A4 01            [ 1] 2235 	and	a, #0x01
      008E16 90 95            [ 1] 2236 	ld	yh, a
      008E18 4F               [ 1] 2237 	clr	a
      008E19 95               [ 1] 2238 	ld	xh, a
      008E1A 58               [ 2] 2239 	sllw	x
      008E1B 1F 05            [ 2] 2240 	ldw	(0x05, sp), x
      008E1D DE 01 D6         [ 2] 2241 	ldw	x, (_c_c0+0, x)
      008E20 1F 0B            [ 2] 2242 	ldw	(0x0b, sp), x
      008E22 93               [ 1] 2243 	ldw	x, y
      008E23 72 F0 0B         [ 2] 2244 	subw	x, (0x0b, sp)
                                   2245 ;	decoder.c: 482: if (d >= -EPS_HIST && d < EPS_HIST) {
      008E26 1F 07            [ 2] 2246 	ldw	(0x07, sp), x
      008E28 A3 FF C0         [ 2] 2247 	cpw	x, #0xffc0
      008E2B 2F 68            [ 1] 2248 	jrslt	00138$
      008E2D 1E 07            [ 2] 2249 	ldw	x, (0x07, sp)
      008E2F A3 00 40         [ 2] 2250 	cpw	x, #0x0040
      008E32 2E 61            [ 1] 2251 	jrsge	00138$
                                   2252 ;	decoder.c: 483: if (cls == 0) {
      008E34 0D 0A            [ 1] 2253 	tnz	(0x0a, sp)
      008E36 26 2B            [ 1] 2254 	jrne	00129$
                                   2255 ;	decoder.c: 484: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
      008E38 1E 05            [ 2] 2256 	ldw	x, (0x05, sp)
      008E3A 1C 01 C6         [ 2] 2257 	addw	x, #(_c_labx0+0)
      008E3D 1F 0B            [ 2] 2258 	ldw	(0x0b, sp), x
      008E3F FE               [ 2] 2259 	ldw	x, (x)
      008E40 13 07            [ 2] 2260 	cpw	x, (0x07, sp)
      008E42 2E 0D            [ 1] 2261 	jrsge	00121$
      008E44 16 05            [ 2] 2262 	ldw	y, (0x05, sp)
      008E46 90 DF 01 CE      [ 2] 2263 	ldw	((_c_labx0b+0), y), x
      008E4A 1E 0B            [ 2] 2264 	ldw	x, (0x0b, sp)
      008E4C 16 07            [ 2] 2265 	ldw	y, (0x07, sp)
      008E4E FF               [ 2] 2266 	ldw	(x), y
      008E4F 20 44            [ 2] 2267 	jra	00138$
      008E51                       2268 00121$:
                                   2269 ;	decoder.c: 485: else if (d > c_labx0b[f]) c_labx0b[f] = d;
      008E51 16 05            [ 2] 2270 	ldw	y, (0x05, sp)
      008E53 72 A9 01 CE      [ 2] 2271 	addw	y, #(_c_labx0b+0)
      008E57 93               [ 1] 2272 	ldw	x, y
      008E58 FE               [ 2] 2273 	ldw	x, (x)
      008E59 13 07            [ 2] 2274 	cpw	x, (0x07, sp)
      008E5B 2E 38            [ 1] 2275 	jrsge	00138$
      008E5D 93               [ 1] 2276 	ldw	x, y
      008E5E 16 07            [ 2] 2277 	ldw	y, (0x07, sp)
      008E60 FF               [ 2] 2278 	ldw	(x), y
      008E61 20 32            [ 2] 2279 	jra	00138$
      008E63                       2280 00129$:
                                   2281 ;	decoder.c: 487: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
      008E63 1E 05            [ 2] 2282 	ldw	x, (0x05, sp)
      008E65 1C 01 CA         [ 2] 2283 	addw	x, #(_c_labx1+0)
      008E68 1F 09            [ 2] 2284 	ldw	(0x09, sp), x
      008E6A FE               [ 2] 2285 	ldw	x, (x)
      008E6B 1F 0B            [ 2] 2286 	ldw	(0x0b, sp), x
      008E6D 1E 07            [ 2] 2287 	ldw	x, (0x07, sp)
      008E6F 13 0B            [ 2] 2288 	cpw	x, (0x0b, sp)
      008E71 2E 0E            [ 1] 2289 	jrsge	00126$
      008E73 1E 05            [ 2] 2290 	ldw	x, (0x05, sp)
      008E75 16 0B            [ 2] 2291 	ldw	y, (0x0b, sp)
      008E77 DF 01 D2         [ 2] 2292 	ldw	((_c_labx1b+0), x), y
      008E7A 1E 09            [ 2] 2293 	ldw	x, (0x09, sp)
      008E7C 16 07            [ 2] 2294 	ldw	y, (0x07, sp)
      008E7E FF               [ 2] 2295 	ldw	(x), y
      008E7F 20 14            [ 2] 2296 	jra	00138$
      008E81                       2297 00126$:
                                   2298 ;	decoder.c: 488: else if (d < c_labx1b[f]) c_labx1b[f] = d;
      008E81 16 05            [ 2] 2299 	ldw	y, (0x05, sp)
      008E83 72 A9 01 D2      [ 2] 2300 	addw	y, #(_c_labx1b+0)
      008E87 93               [ 1] 2301 	ldw	x, y
      008E88 FE               [ 2] 2302 	ldw	x, (x)
      008E89 1F 0B            [ 2] 2303 	ldw	(0x0b, sp), x
      008E8B 1E 07            [ 2] 2304 	ldw	x, (0x07, sp)
      008E8D 13 0B            [ 2] 2305 	cpw	x, (0x0b, sp)
      008E8F 2E 04            [ 1] 2306 	jrsge	00138$
      008E91 93               [ 1] 2307 	ldw	x, y
      008E92 16 07            [ 2] 2308 	ldw	y, (0x07, sp)
      008E94 FF               [ 2] 2309 	ldw	(x), y
      008E95                       2310 00138$:
                                   2311 ;	decoder.c: 492: }
      008E95 1E 0D            [ 2] 2312 	ldw	x, (13, sp)
      008E97 5B 17            [ 2] 2313 	addw	sp, #23
      008E99 FC               [ 2] 2314 	jp	(x)
                                   2315 ;	decoder.c: 495: static uint8_t theta56(uint8_t f, int16_t *theta_out)
                                   2316 ;	-----------------------------------------
                                   2317 ;	 function theta56
                                   2318 ;	-----------------------------------------
      008E9A                       2319 _theta56:
      008E9A 52 26            [ 2] 2320 	sub	sp, #38
      008E9C 1F 23            [ 2] 2321 	ldw	(0x23, sp), x
                                   2322 ;	decoder.c: 497: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
      008E9E 5F               [ 1] 2323 	clrw	x
      008E9F 97               [ 1] 2324 	ld	xl, a
      008EA0 58               [ 2] 2325 	sllw	x
      008EA1 1F 01            [ 2] 2326 	ldw	(0x01, sp), x
      008EA3 DE 01 C6         [ 2] 2327 	ldw	x, (_c_labx0+0, x)
      008EA6 16 01            [ 2] 2328 	ldw	y, (0x01, sp)
      008EA8 90 DE 01 CA      [ 2] 2329 	ldw	y, (_c_labx1+0, y)
                                   2330 ;	decoder.c: 498: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
      008EAC 1F 03            [ 2] 2331 	ldw	(0x03, sp), x
      008EAE A3 C0 00         [ 2] 2332 	cpw	x, #0xc000
      008EB1 2C 04            [ 1] 2333 	jrsgt	00483$
      008EB3 0F 05            [ 1] 2334 	clr	(0x05, sp)
      008EB5 20 06            [ 2] 2335 	jra	00484$
      008EB7                       2336 00483$:
      008EB7 88               [ 1] 2337 	push	a
      008EB8 A6 01            [ 1] 2338 	ld	a, #0x01
      008EBA 6B 06            [ 1] 2339 	ld	(0x06, sp), a
      008EBC 84               [ 1] 2340 	pop	a
      008EBD                       2341 00484$:
      008EBD 17 06            [ 2] 2342 	ldw	(0x06, sp), y
      008EBF 93               [ 1] 2343 	ldw	x, y
      008EC0 A3 3F FF         [ 2] 2344 	cpw	x, #0x3fff
      008EC3 2F 04            [ 1] 2345 	jrslt	00485$
      008EC5 0F 08            [ 1] 2346 	clr	(0x08, sp)
      008EC7 20 06            [ 2] 2347 	jra	00486$
      008EC9                       2348 00485$:
      008EC9 88               [ 1] 2349 	push	a
      008ECA A6 01            [ 1] 2350 	ld	a, #0x01
      008ECC 6B 09            [ 1] 2351 	ld	(0x09, sp), a
      008ECE 84               [ 1] 2352 	pop	a
      008ECF                       2353 00486$:
                                   2354 ;	decoder.c: 499: int16_t zlo = (int16_t)(x0 + 1);
      008ECF 1E 03            [ 2] 2355 	ldw	x, (0x03, sp)
      008ED1 5C               [ 1] 2356 	incw	x
      008ED2 1F 09            [ 2] 2357 	ldw	(0x09, sp), x
                                   2358 ;	decoder.c: 500: int16_t zhi = x1;
      008ED4 17 0B            [ 2] 2359 	ldw	(0x0b, sp), y
                                   2360 ;	decoder.c: 501: int16_t theta = 0;
      008ED6 5F               [ 1] 2361 	clrw	x
      008ED7 1F 0D            [ 2] 2362 	ldw	(0x0d, sp), x
                                   2363 ;	decoder.c: 502: uint8_t have_theta = 0;
      008ED9 0F 0F            [ 1] 2364 	clr	(0x0f, sp)
                                   2365 ;	decoder.c: 503: int16_t top = 0;
      008EDB 5F               [ 1] 2366 	clrw	x
      008EDC 1F 10            [ 2] 2367 	ldw	(0x10, sp), x
                                   2368 ;	decoder.c: 504: uint8_t have_top = 0, clear1 = 0;
      008EDE 0F 12            [ 1] 2369 	clr	(0x12, sp)
      008EE0 0F 13            [ 1] 2370 	clr	(0x13, sp)
                                   2371 ;	decoder.c: 506: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
      008EE2 AE FF E0         [ 2] 2372 	ldw	x, #0xffe0
      008EE5 13 09            [ 2] 2373 	cpw	x, (0x09, sp)
      008EE7 2F 02            [ 1] 2374 	jrslt	00102$
      008EE9 1F 09            [ 2] 2375 	ldw	(0x09, sp), x
      008EEB                       2376 00102$:
                                   2377 ;	decoder.c: 507: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
      008EEB 1E 0B            [ 2] 2378 	ldw	x, (0x0b, sp)
      008EED A3 00 20         [ 2] 2379 	cpw	x, #0x0020
      008EF0 2D 05            [ 1] 2380 	jrsle	00104$
      008EF2 AE 00 20         [ 2] 2381 	ldw	x, #0x0020
      008EF5 1F 0B            [ 2] 2382 	ldw	(0x0b, sp), x
      008EF7                       2383 00104$:
                                   2384 ;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
      008EF7 41               [ 1] 2385 	exg	a, xl
      008EF8 A6 40            [ 1] 2386 	ld	a, #0x40
      008EFA 41               [ 1] 2387 	exg	a, xl
      008EFB 42               [ 4] 2388 	mul	x, a
      008EFC 1F 14            [ 2] 2389 	ldw	(0x14, sp), x
                                   2390 ;	decoder.c: 508: if (zlo < zhi) {
      008EFE 1E 09            [ 2] 2391 	ldw	x, (0x09, sp)
      008F00 13 0B            [ 2] 2392 	cpw	x, (0x0b, sp)
      008F02 2F 03            [ 1] 2393 	jrslt	00489$
      008F04 CC 90 1D         [ 2] 2394 	jp	00126$
      008F07                       2395 00489$:
                                   2396 ;	decoder.c: 509: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
      008F07 1E 09            [ 2] 2397 	ldw	x, (0x09, sp)
      008F09 1C 00 40         [ 2] 2398 	addw	x, #0x0040
      008F0C 57               [ 2] 2399 	sraw	x
      008F0D 41               [ 1] 2400 	exg	a, xl
      008F0E 6B 25            [ 1] 2401 	ld	(0x25, sp), a
      008F10 41               [ 1] 2402 	exg	a, xl
                                   2403 ;	decoder.c: 510: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
      008F11 1E 0B            [ 2] 2404 	ldw	x, (0x0b, sp)
      008F13 1C 00 3F         [ 2] 2405 	addw	x, #0x003f
      008F16 57               [ 2] 2406 	sraw	x
      008F17 41               [ 1] 2407 	exg	a, xl
      008F18 6B 16            [ 1] 2408 	ld	(0x16, sp), a
      008F1A 41               [ 1] 2409 	exg	a, xl
                                   2410 ;	decoder.c: 512: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
      008F1B 16 09            [ 2] 2411 	ldw	y, (0x09, sp)
      008F1D 17 17            [ 2] 2412 	ldw	(0x17, sp), y
      008F1F 5F               [ 1] 2413 	clrw	x
      008F20 1F 19            [ 2] 2414 	ldw	(0x19, sp), x
      008F22 5F               [ 1] 2415 	clrw	x
      008F23 1F 1B            [ 2] 2416 	ldw	(0x1b, sp), x
      008F25 5F               [ 1] 2417 	clrw	x
      008F26 5A               [ 2] 2418 	decw	x
      008F27 1F 1D            [ 2] 2419 	ldw	(0x1d, sp), x
                                   2420 ;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
      008F29 1E 14            [ 2] 2421 	ldw	x, (0x14, sp)
      008F2B 1C 01 46         [ 2] 2422 	addw	x, #(_c_hist+0)
      008F2E 1F 1F            [ 2] 2423 	ldw	(0x1f, sp), x
      008F30 0F 26            [ 1] 2424 	clr	(0x26, sp)
      008F32                       2425 00170$:
      008F32 7B 25            [ 1] 2426 	ld	a, (0x25, sp)
      008F34 11 16            [ 1] 2427 	cp	a, (0x16, sp)
      008F36 22 2F            [ 1] 2428 	jrugt	00253$
                                   2429 ;	decoder.c: 515: if (c_hist[f][b]) {
      008F38 5F               [ 1] 2430 	clrw	x
      008F39 7B 25            [ 1] 2431 	ld	a, (0x25, sp)
      008F3B 97               [ 1] 2432 	ld	xl, a
      008F3C 72 FB 1F         [ 2] 2433 	addw	x, (0x1f, sp)
      008F3F F6               [ 1] 2434 	ld	a, (x)
      008F40 27 21            [ 1] 2435 	jreq	00171$
                                   2436 ;	decoder.c: 516: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      008F42 7B 25            [ 1] 2437 	ld	a, (0x25, sp)
      008F44 5F               [ 1] 2438 	clrw	x
      008F45 97               [ 1] 2439 	ld	xl, a
      008F46 58               [ 2] 2440 	sllw	x
      008F47 1C FF C1         [ 2] 2441 	addw	x, #0xffc1
                                   2442 ;	decoder.c: 517: int16_t gp = (int16_t)(x - prev);
      008F4A 1F 21            [ 2] 2443 	ldw	(0x21, sp), x
      008F4C 72 F0 17         [ 2] 2444 	subw	x, (0x17, sp)
                                   2445 ;	decoder.c: 518: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
      008F4F 13 1D            [ 2] 2446 	cpw	x, (0x1d, sp)
      008F51 2D 0A            [ 1] 2447 	jrsle	00106$
      008F53 1F 1D            [ 2] 2448 	ldw	(0x1d, sp), x
      008F55 16 17            [ 2] 2449 	ldw	y, (0x17, sp)
      008F57 17 19            [ 2] 2450 	ldw	(0x19, sp), y
      008F59 16 21            [ 2] 2451 	ldw	y, (0x21, sp)
      008F5B 17 1B            [ 2] 2452 	ldw	(0x1b, sp), y
      008F5D                       2453 00106$:
                                   2454 ;	decoder.c: 519: prev = x;
      008F5D 16 21            [ 2] 2455 	ldw	y, (0x21, sp)
      008F5F 17 17            [ 2] 2456 	ldw	(0x17, sp), y
                                   2457 ;	decoder.c: 520: nocc++;
      008F61 0C 26            [ 1] 2458 	inc	(0x26, sp)
      008F63                       2459 00171$:
                                   2460 ;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
      008F63 0C 25            [ 1] 2461 	inc	(0x25, sp)
      008F65 20 CB            [ 2] 2462 	jra	00170$
      008F67                       2463 00253$:
      008F67 7B 26            [ 1] 2464 	ld	a, (0x26, sp)
      008F69 97               [ 1] 2465 	ld	xl, a
                                   2466 ;	decoder.c: 524: int16_t gp = (int16_t)(zhi - prev);
      008F6A 16 0B            [ 2] 2467 	ldw	y, (0x0b, sp)
      008F6C 72 F2 17         [ 2] 2468 	subw	y, (0x17, sp)
                                   2469 ;	decoder.c: 525: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
      008F6F 51               [ 1] 2470 	exgw	x, y
      008F70 13 1D            [ 2] 2471 	cpw	x, (0x1d, sp)
      008F72 51               [ 1] 2472 	exgw	x, y
      008F73 2D 0A            [ 1] 2473 	jrsle	00111$
      008F75 17 1D            [ 2] 2474 	ldw	(0x1d, sp), y
      008F77 16 17            [ 2] 2475 	ldw	y, (0x17, sp)
      008F79 17 19            [ 2] 2476 	ldw	(0x19, sp), y
      008F7B 16 0B            [ 2] 2477 	ldw	y, (0x0b, sp)
      008F7D 17 1B            [ 2] 2478 	ldw	(0x1b, sp), y
      008F7F                       2479 00111$:
                                   2480 ;	decoder.c: 527: if (nocc == 0) {
      008F7F 9F               [ 1] 2481 	ld	a, xl
      008F80 4D               [ 1] 2482 	tnz	a
      008F81 26 1D            [ 1] 2483 	jrne	00123$
                                   2484 ;	decoder.c: 528: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
      008F83 0D 05            [ 1] 2485 	tnz	(0x05, sp)
      008F85 26 03            [ 1] 2486 	jrne	00495$
      008F87 CC 90 1D         [ 2] 2487 	jp	00126$
      008F8A                       2488 00495$:
      008F8A 0D 08            [ 1] 2489 	tnz	(0x08, sp)
      008F8C 26 03            [ 1] 2490 	jrne	00496$
      008F8E CC 90 1D         [ 2] 2491 	jp	00126$
      008F91                       2492 00496$:
      008F91 1E 09            [ 2] 2493 	ldw	x, (0x09, sp)
      008F93 72 FB 0B         [ 2] 2494 	addw	x, (0x0b, sp)
      008F96 57               [ 2] 2495 	sraw	x
      008F97 1F 0D            [ 2] 2496 	ldw	(0x0d, sp), x
      008F99 A6 01            [ 1] 2497 	ld	a, #0x01
      008F9B 6B 0F            [ 1] 2498 	ld	(0x0f, sp), a
      008F9D CC 90 1D         [ 2] 2499 	jp	00126$
      008FA0                       2500 00123$:
                                   2501 ;	decoder.c: 530: uint8_t ok = (bg >= EPS_GAP_MIN);
      008FA0 16 1D            [ 2] 2502 	ldw	y, (0x1d, sp)
      008FA2 90 A3 00 05      [ 2] 2503 	cpw	y, #0x0005
      008FA6 2F 02            [ 1] 2504 	jrslt	00497$
      008FA8 4F               [ 1] 2505 	clr	a
      008FA9 C5                    2506 	.byte 0xc5
      008FAA                       2507 00497$:
      008FAA A6 01            [ 1] 2508 	ld	a, #0x01
      008FAC                       2509 00498$:
      008FAC A8 01            [ 1] 2510 	xor	a, #0x01
                                   2511 ;	decoder.c: 531: if (ok && (uint8_t)(nocc + 1) >= 4) {
      008FAE 6B 26            [ 1] 2512 	ld	(0x26, sp), a
      008FB0 27 5B            [ 1] 2513 	jreq	00118$
      008FB2 9F               [ 1] 2514 	ld	a, xl
      008FB3 4C               [ 1] 2515 	inc	a
      008FB4 A1 04            [ 1] 2516 	cp	a, #0x04
      008FB6 25 55            [ 1] 2517 	jrc	00118$
                                   2518 ;	decoder.c: 533: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
      008FB8 16 1D            [ 2] 2519 	ldw	y, (0x1d, sp)
      008FBA 90 9E            [ 1] 2520 	ld	a, yh
      008FBC 49               [ 1] 2521 	rlc	a
      008FBD 4F               [ 1] 2522 	clr	a
      008FBE A2 00            [ 1] 2523 	sbc	a, #0x00
      008FC0 95               [ 1] 2524 	ld	xh, a
      008FC1 02               [ 1] 2525 	rlwa	x
      008FC2 6B 20            [ 1] 2526 	ld	(0x20, sp), a
      008FC4 01               [ 1] 2527 	rrwa	x
      008FC5 6B 1F            [ 1] 2528 	ld	(0x1f, sp), a
      008FC7 90 58            [ 2] 2529 	sllw	y
      008FC9 09 20            [ 1] 2530 	rlc	(0x20, sp)
      008FCB 09 1F            [ 1] 2531 	rlc	(0x1f, sp)
      008FCD 17 21            [ 2] 2532 	ldw	(0x21, sp), y
      008FCF 4F               [ 1] 2533 	clr	a
      008FD0 95               [ 1] 2534 	ld	xh, a
      008FD1 5C               [ 1] 2535 	incw	x
      008FD2 90 5F            [ 1] 2536 	clrw	y
      008FD4 5D               [ 2] 2537 	tnzw	x
      008FD5 2A 02            [ 1] 2538 	jrpl	00501$
      008FD7 90 5A            [ 2] 2539 	decw	y
      008FD9                       2540 00501$:
      008FD9 89               [ 2] 2541 	pushw	x
      008FDA 90 89            [ 2] 2542 	pushw	y
      008FDC 1E 25            [ 2] 2543 	ldw	x, (0x25, sp)
      008FDE 89               [ 2] 2544 	pushw	x
      008FDF 1E 25            [ 2] 2545 	ldw	x, (0x25, sp)
      008FE1 89               [ 2] 2546 	pushw	x
      008FE2 CD 9F 06         [ 4] 2547 	call	__mullong
      008FE5 5B 08            [ 2] 2548 	addw	sp, #8
      008FE7 1F 21            [ 2] 2549 	ldw	(0x21, sp), x
      008FE9 17 1F            [ 2] 2550 	ldw	(0x1f, sp), y
      008FEB 1E 0B            [ 2] 2551 	ldw	x, (0x0b, sp)
      008FED 72 F0 09         [ 2] 2552 	subw	x, (0x09, sp)
      008FF0 89               [ 2] 2553 	pushw	x
      008FF1 AE 00 05         [ 2] 2554 	ldw	x, #0x0005
      008FF4 CD 9E 31         [ 4] 2555 	call	___mulsint2slong
      008FF7 5B 02            [ 2] 2556 	addw	sp, #2
      008FF9 1F 0B            [ 2] 2557 	ldw	(0x0b, sp), x
      008FFB 17 09            [ 2] 2558 	ldw	(0x09, sp), y
      008FFD 1E 21            [ 2] 2559 	ldw	x, (0x21, sp)
      008FFF 13 0B            [ 2] 2560 	cpw	x, (0x0b, sp)
      009001 7B 20            [ 1] 2561 	ld	a, (0x20, sp)
      009003 12 0A            [ 1] 2562 	sbc	a, (0x0a, sp)
      009005 7B 1F            [ 1] 2563 	ld	a, (0x1f, sp)
      009007 12 09            [ 1] 2564 	sbc	a, (0x09, sp)
      009009 2E 02            [ 1] 2565 	jrsge	00118$
                                   2566 ;	decoder.c: 534: ok = 0;
      00900B 0F 26            [ 1] 2567 	clr	(0x26, sp)
      00900D                       2568 00118$:
                                   2569 ;	decoder.c: 536: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
      00900D 0D 26            [ 1] 2570 	tnz	(0x26, sp)
      00900F 27 0C            [ 1] 2571 	jreq	00126$
      009011 1E 19            [ 2] 2572 	ldw	x, (0x19, sp)
      009013 72 FB 1B         [ 2] 2573 	addw	x, (0x1b, sp)
      009016 57               [ 2] 2574 	sraw	x
      009017 1F 0D            [ 2] 2575 	ldw	(0x0d, sp), x
      009019 A6 01            [ 1] 2576 	ld	a, #0x01
      00901B 6B 0F            [ 1] 2577 	ld	(0x0f, sp), a
      00901D                       2578 00126$:
                                   2579 ;	decoder.c: 539: if (has0 || has1) {
      00901D 0D 05            [ 1] 2580 	tnz	(0x05, sp)
      00901F 26 07            [ 1] 2581 	jrne	00144$
      009021 0D 08            [ 1] 2582 	tnz	(0x08, sp)
      009023 26 03            [ 1] 2583 	jrne	00505$
      009025 CC 90 A6         [ 2] 2584 	jp	00245$
      009028                       2585 00505$:
      009028                       2586 00144$:
                                   2587 ;	decoder.c: 540: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
      009028 AE FF E0         [ 2] 2588 	ldw	x, #0xffe0
      00902B 1F 21            [ 2] 2589 	ldw	(0x21, sp), x
      00902D AE 00 20         [ 2] 2590 	ldw	x, #0x0020
      009030 1F 25            [ 2] 2591 	ldw	(0x25, sp), x
                                   2592 ;	decoder.c: 541: if (has0) {
      009032 0D 05            [ 1] 2593 	tnz	(0x05, sp)
      009034 27 19            [ 1] 2594 	jreq	00131$
                                   2595 ;	decoder.c: 542: wlo = (int16_t)(x0 - EPS_SLACK1);
      009036 1E 03            [ 2] 2596 	ldw	x, (0x03, sp)
      009038 1D 00 08         [ 2] 2597 	subw	x, #0x0008
      00903B 1F 21            [ 2] 2598 	ldw	(0x21, sp), x
                                   2599 ;	decoder.c: 543: if (c_labx0b[f] > -0x4000 &&
      00903D 1E 01            [ 2] 2600 	ldw	x, (0x01, sp)
      00903F DE 01 CE         [ 2] 2601 	ldw	x, (_c_labx0b+0, x)
      009042 A3 C0 00         [ 2] 2602 	cpw	x, #0xc000
      009045 2D 08            [ 1] 2603 	jrsle	00131$
                                   2604 ;	decoder.c: 544: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
      009047 5A               [ 2] 2605 	decw	x
      009048 5A               [ 2] 2606 	decw	x
      009049 13 21            [ 2] 2607 	cpw	x, (0x21, sp)
      00904B 2D 02            [ 1] 2608 	jrsle	00131$
                                   2609 ;	decoder.c: 545: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
      00904D 1F 21            [ 2] 2610 	ldw	(0x21, sp), x
      00904F                       2611 00131$:
                                   2612 ;	decoder.c: 547: if (has1) {
      00904F 0D 08            [ 1] 2613 	tnz	(0x08, sp)
      009051 27 19            [ 1] 2614 	jreq	00136$
                                   2615 ;	decoder.c: 548: whi = (int16_t)(x1 + EPS_SLACK1);
      009053 1E 06            [ 2] 2616 	ldw	x, (0x06, sp)
      009055 1C 00 08         [ 2] 2617 	addw	x, #0x0008
      009058 1F 25            [ 2] 2618 	ldw	(0x25, sp), x
                                   2619 ;	decoder.c: 549: if (c_labx1b[f] < 0x3FFF &&
      00905A 1E 01            [ 2] 2620 	ldw	x, (0x01, sp)
      00905C DE 01 D2         [ 2] 2621 	ldw	x, (_c_labx1b+0, x)
      00905F A3 3F FF         [ 2] 2622 	cpw	x, #0x3fff
      009062 2E 08            [ 1] 2623 	jrsge	00136$
                                   2624 ;	decoder.c: 550: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
      009064 5C               [ 1] 2625 	incw	x
      009065 5C               [ 1] 2626 	incw	x
      009066 13 25            [ 2] 2627 	cpw	x, (0x25, sp)
      009068 2E 02            [ 1] 2628 	jrsge	00136$
                                   2629 ;	decoder.c: 551: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
      00906A 1F 25            [ 2] 2630 	ldw	(0x25, sp), x
      00906C                       2631 00136$:
                                   2632 ;	decoder.c: 553: if (wlo > whi) {
                                   2633 ;	decoder.c: 554: theta = (int16_t)((wlo + whi) >> 1);
      00906C 1E 21            [ 2] 2634 	ldw	x, (0x21, sp)
      00906E 13 25            [ 2] 2635 	cpw	x, (0x25, sp)
      009070 2D 0C            [ 1] 2636 	jrsle	00142$
      009072 72 FB 25         [ 2] 2637 	addw	x, (0x25, sp)
      009075 57               [ 2] 2638 	sraw	x
      009076 1F 0D            [ 2] 2639 	ldw	(0x0d, sp), x
                                   2640 ;	decoder.c: 555: have_theta = 1;
      009078 A6 01            [ 1] 2641 	ld	a, #0x01
      00907A 6B 0F            [ 1] 2642 	ld	(0x0f, sp), a
      00907C 20 28            [ 2] 2643 	jra	00245$
      00907E                       2644 00142$:
                                   2645 ;	decoder.c: 557: int16_t th = have_theta ? theta : 0;
      00907E 0D 0F            [ 1] 2646 	tnz	(0x0f, sp)
      009080 27 05            [ 1] 2647 	jreq	00175$
      009082 16 0D            [ 2] 2648 	ldw	y, (0x0d, sp)
      009084 17 1F            [ 2] 2649 	ldw	(0x1f, sp), y
      009086 BC                    2650 	.byte 0xbc
      009087                       2651 00175$:
      009087 5F               [ 1] 2652 	clrw	x
      009088 1F 1F            [ 2] 2653 	ldw	(0x1f, sp), x
      00908A                       2654 00176$:
                                   2655 ;	decoder.c: 558: if (th < wlo) th = wlo;
      00908A 1E 1F            [ 2] 2656 	ldw	x, (0x1f, sp)
      00908C 13 21            [ 2] 2657 	cpw	x, (0x21, sp)
      00908E 2E 04            [ 1] 2658 	jrsge	00138$
      009090 16 21            [ 2] 2659 	ldw	y, (0x21, sp)
      009092 17 1F            [ 2] 2660 	ldw	(0x1f, sp), y
      009094                       2661 00138$:
                                   2662 ;	decoder.c: 559: if (th > whi) th = whi;
      009094 1E 1F            [ 2] 2663 	ldw	x, (0x1f, sp)
      009096 13 25            [ 2] 2664 	cpw	x, (0x25, sp)
      009098 2D 04            [ 1] 2665 	jrsle	00140$
      00909A 16 25            [ 2] 2666 	ldw	y, (0x25, sp)
      00909C 17 1F            [ 2] 2667 	ldw	(0x1f, sp), y
      00909E                       2668 00140$:
                                   2669 ;	decoder.c: 560: theta = th;
      00909E 16 1F            [ 2] 2670 	ldw	y, (0x1f, sp)
      0090A0 17 0D            [ 2] 2671 	ldw	(0x0d, sp), y
                                   2672 ;	decoder.c: 561: have_theta = 1;
      0090A2 A6 01            [ 1] 2673 	ld	a, #0x01
      0090A4 6B 0F            [ 1] 2674 	ld	(0x0f, sp), a
                                   2675 ;	decoder.c: 564: for (b = 0; b < 64; b++) {
      0090A6                       2676 00245$:
      0090A6 1E 14            [ 2] 2677 	ldw	x, (0x14, sp)
      0090A8 1C 01 46         [ 2] 2678 	addw	x, #(_c_hist+0)
      0090AB 1F 21            [ 2] 2679 	ldw	(0x21, sp), x
      0090AD 0F 26            [ 1] 2680 	clr	(0x26, sp)
      0090AF                       2681 00172$:
                                   2682 ;	decoder.c: 566: if (!c_hist[f][b]) continue;
      0090AF 5F               [ 1] 2683 	clrw	x
      0090B0 7B 26            [ 1] 2684 	ld	a, (0x26, sp)
      0090B2 97               [ 1] 2685 	ld	xl, a
      0090B3 72 FB 21         [ 2] 2686 	addw	x, (0x21, sp)
      0090B6 F6               [ 1] 2687 	ld	a, (x)
      0090B7 27 34            [ 1] 2688 	jreq	00157$
                                   2689 ;	decoder.c: 567: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
      0090B9 7B 26            [ 1] 2690 	ld	a, (0x26, sp)
      0090BB 5F               [ 1] 2691 	clrw	x
      0090BC 48               [ 1] 2692 	sll	a
      0090BD 59               [ 2] 2693 	rlcw	x
      0090BE AB C1            [ 1] 2694 	add	a, #0xc1
      0090C0 6B 20            [ 1] 2695 	ld	(0x20, sp), a
      0090C2 49               [ 1] 2696 	rlc	a
      0090C3 4F               [ 1] 2697 	clr	a
      0090C4 A2 00            [ 1] 2698 	sbc	a, #0x00
      0090C6 6B 1F            [ 1] 2699 	ld	(0x1f, sp), a
                                   2700 ;	decoder.c: 568: if (d > EPS_CLEAR1) clear1 = 1;
      0090C8 7B 20            [ 1] 2701 	ld	a, (0x20, sp)
      0090CA A1 12            [ 1] 2702 	cp	a, #0x12
      0090CC 2D 06            [ 1] 2703 	jrsle	00155$
      0090CE A6 01            [ 1] 2704 	ld	a, #0x01
      0090D0 6B 13            [ 1] 2705 	ld	(0x13, sp), a
      0090D2 20 19            [ 2] 2706 	jra	00157$
      0090D4                       2707 00155$:
                                   2708 ;	decoder.c: 569: else if (d > -EPS_CLAMP56) {
      0090D4 1E 1F            [ 2] 2709 	ldw	x, (0x1f, sp)
      0090D6 A3 FF E8         [ 2] 2710 	cpw	x, #0xffe8
      0090D9 2D 12            [ 1] 2711 	jrsle	00157$
                                   2712 ;	decoder.c: 570: if (!have_top || d > top) top = d;
      0090DB 0D 12            [ 1] 2713 	tnz	(0x12, sp)
      0090DD 27 06            [ 1] 2714 	jreq	00149$
      0090DF 1E 1F            [ 2] 2715 	ldw	x, (0x1f, sp)
      0090E1 13 10            [ 2] 2716 	cpw	x, (0x10, sp)
      0090E3 2D 04            [ 1] 2717 	jrsle	00150$
      0090E5                       2718 00149$:
      0090E5 16 1F            [ 2] 2719 	ldw	y, (0x1f, sp)
      0090E7 17 10            [ 2] 2720 	ldw	(0x10, sp), y
      0090E9                       2721 00150$:
                                   2722 ;	decoder.c: 571: have_top = 1;
      0090E9 A6 01            [ 1] 2723 	ld	a, #0x01
      0090EB 6B 12            [ 1] 2724 	ld	(0x12, sp), a
      0090ED                       2725 00157$:
                                   2726 ;	decoder.c: 564: for (b = 0; b < 64; b++) {
      0090ED 0C 26            [ 1] 2727 	inc	(0x26, sp)
      0090EF 7B 26            [ 1] 2728 	ld	a, (0x26, sp)
      0090F1 A1 40            [ 1] 2729 	cp	a, #0x40
      0090F3 25 BA            [ 1] 2730 	jrc	00172$
                                   2731 ;	decoder.c: 574: if (!clear1 && have_top) {
      0090F5 0D 13            [ 1] 2732 	tnz	(0x13, sp)
      0090F7 26 34            [ 1] 2733 	jrne	00167$
      0090F9 0D 12            [ 1] 2734 	tnz	(0x12, sp)
      0090FB 27 30            [ 1] 2735 	jreq	00167$
                                   2736 ;	decoder.c: 575: int16_t floor_ = (int16_t)(top + EPS_TOPM);
      0090FD 7B 11            [ 1] 2737 	ld	a, (0x11, sp)
      0090FF AB 03            [ 1] 2738 	add	a, #0x03
      009101 6B 26            [ 1] 2739 	ld	(0x26, sp), a
      009103 49               [ 1] 2740 	rlc	a
      009104 4F               [ 1] 2741 	clr	a
      009105 A2 00            [ 1] 2742 	sbc	a, #0x00
      009107 6B 25            [ 1] 2743 	ld	(0x25, sp), a
                                   2744 ;	decoder.c: 576: if (!have_theta || floor_ > theta) theta = floor_;
      009109 0D 0F            [ 1] 2745 	tnz	(0x0f, sp)
      00910B 27 06            [ 1] 2746 	jreq	00159$
      00910D 1E 25            [ 2] 2747 	ldw	x, (0x25, sp)
      00910F 13 0D            [ 2] 2748 	cpw	x, (0x0d, sp)
      009111 2D 04            [ 1] 2749 	jrsle	00160$
      009113                       2750 00159$:
      009113 16 25            [ 2] 2751 	ldw	y, (0x25, sp)
      009115 17 0D            [ 2] 2752 	ldw	(0x0d, sp), y
      009117                       2753 00160$:
                                   2754 ;	decoder.c: 577: have_theta = 1;
      009117 A6 01            [ 1] 2755 	ld	a, #0x01
      009119 6B 0F            [ 1] 2756 	ld	(0x0f, sp), a
                                   2757 ;	decoder.c: 578: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
      00911B 0D 08            [ 1] 2758 	tnz	(0x08, sp)
      00911D 27 0E            [ 1] 2759 	jreq	00167$
      00911F 1E 06            [ 2] 2760 	ldw	x, (0x06, sp)
      009121 5C               [ 1] 2761 	incw	x
      009122 5C               [ 1] 2762 	incw	x
      009123 13 25            [ 2] 2763 	cpw	x, (0x25, sp)
      009125 2D 06            [ 1] 2764 	jrsle	00167$
                                   2765 ;	decoder.c: 579: theta > (int16_t)(x1 + EPS_SLACK))
      009127 13 0D            [ 2] 2766 	cpw	x, (0x0d, sp)
      009129 2E 02            [ 1] 2767 	jrsge	00167$
                                   2768 ;	decoder.c: 580: theta = (int16_t)(x1 + EPS_SLACK);
      00912B 1F 0D            [ 2] 2769 	ldw	(0x0d, sp), x
      00912D                       2770 00167$:
                                   2771 ;	decoder.c: 582: *theta_out = theta;
      00912D 1E 23            [ 2] 2772 	ldw	x, (0x23, sp)
      00912F 16 0D            [ 2] 2773 	ldw	y, (0x0d, sp)
      009131 FF               [ 2] 2774 	ldw	(x), y
                                   2775 ;	decoder.c: 583: return have_theta;
      009132 7B 0F            [ 1] 2776 	ld	a, (0x0f, sp)
                                   2777 ;	decoder.c: 584: }
      009134 5B 26            [ 2] 2778 	addw	sp, #38
      009136 81               [ 4] 2779 	ret
                                   2780 ;	decoder.c: 586: static void calibrate(const uint8_t *cap, uint16_t ncap)
                                   2781 ;	-----------------------------------------
                                   2782 ;	 function calibrate
                                   2783 ;	-----------------------------------------
      009137                       2784 _calibrate:
      009137 52 45            [ 2] 2785 	sub	sp, #69
      009139 1F 44            [ 2] 2786 	ldw	(0x44, sp), x
                                   2787 ;	decoder.c: 591: c_lo0 = c_lo1 = -0x4000;
      00913B AE C0 00         [ 2] 2788 	ldw	x, #0xc000
      00913E CF 01 3A         [ 2] 2789 	ldw	_c_lo1+0, x
      009141 AE C0 00         [ 2] 2790 	ldw	x, #0xc000
      009144 CF 01 36         [ 2] 2791 	ldw	_c_lo0+0, x
                                   2792 ;	decoder.c: 592: c_hi0 = c_hi1 = 0x3FFF;
      009147 AE 3F FF         [ 2] 2793 	ldw	x, #0x3fff
      00914A CF 01 3C         [ 2] 2794 	ldw	_c_hi1+0, x
      00914D AE 3F FF         [ 2] 2795 	ldw	x, #0x3fff
      009150 CF 01 38         [ 2] 2796 	ldw	_c_hi0+0, x
                                   2797 ;	decoder.c: 593: c_n0 = c_n1 = 0;
      009153 72 5F 01 3F      [ 1] 2798 	clr	_c_n1+0
      009157 72 5F 01 3E      [ 1] 2799 	clr	_c_n0+0
                                   2800 ;	decoder.c: 594: c_h0c = H0P; c_h1c = H1P;
      00915B AE 00 9A         [ 2] 2801 	ldw	x, #0x009a
      00915E CF 01 40         [ 2] 2802 	ldw	_c_h0c+0, x
      009161 AE 01 34         [ 2] 2803 	ldw	x, #0x0134
      009164 CF 01 42         [ 2] 2804 	ldw	_c_h1c+0, x
                                   2805 ;	decoder.c: 595: c_d56[0] = c_d56[1] = 0;
      009167 35 00 01 45      [ 1] 2806 	mov	_c_d56+1, #0x00
      00916B 35 00 01 44      [ 1] 2807 	mov	_c_d56+0, #0x00
                                   2808 ;	decoder.c: 596: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
      00916F CE 01 32         [ 2] 2809 	ldw	x, _g_K+0
      009172 89               [ 2] 2810 	pushw	x
      009173 AE 00 06         [ 2] 2811 	ldw	x, #0x0006
      009176 CD 9E 2B         [ 4] 2812 	call	___muluint2ulong
      009179 5B 02            [ 2] 2813 	addw	sp, #2
      00917B A6 0B            [ 1] 2814 	ld	a, #0x0b
      00917D                       2815 00403$:
      00917D 90 54            [ 2] 2816 	srlw	y
      00917F 56               [ 2] 2817 	rrcw	x
      009180 4A               [ 1] 2818 	dec	a
      009181 26 FA            [ 1] 2819 	jrne	00403$
      009183 CF 01 DA         [ 2] 2820 	ldw	_c_gap56+0, x
                                   2821 ;	decoder.c: 597: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
      009186 CE 01 32         [ 2] 2822 	ldw	x, _g_K+0
      009189 89               [ 2] 2823 	pushw	x
      00918A AE 00 05         [ 2] 2824 	ldw	x, #0x0005
      00918D CD 9E 2B         [ 4] 2825 	call	___muluint2ulong
      009190 5B 02            [ 2] 2826 	addw	sp, #2
      009192 A6 0B            [ 1] 2827 	ld	a, #0x0b
      009194                       2828 00405$:
      009194 90 54            [ 2] 2829 	srlw	y
      009196 56               [ 2] 2830 	rrcw	x
      009197 4A               [ 1] 2831 	dec	a
      009198 26 FA            [ 1] 2832 	jrne	00405$
      00919A CF 01 DC         [ 2] 2833 	ldw	_c_gap56+2, x
                                   2834 ;	decoder.c: 598: for (f = 0; f < 2; f++) {
      00919D 0F 43            [ 1] 2835 	clr	(0x43, sp)
      00919F                       2836 00138$:
                                   2837 ;	decoder.c: 600: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
      00919F 5F               [ 1] 2838 	clrw	x
      0091A0 7B 43            [ 1] 2839 	ld	a, (0x43, sp)
      0091A2 97               [ 1] 2840 	ld	xl, a
      0091A3 58               [ 2] 2841 	sllw	x
      0091A4 1F 3F            [ 2] 2842 	ldw	(0x3f, sp), x
      0091A6 90 93            [ 1] 2843 	ldw	y, x
      0091A8 72 A9 01 D6      [ 2] 2844 	addw	y, #(_c_c0+0)
      0091AC 1E 3F            [ 2] 2845 	ldw	x, (0x3f, sp)
      0091AE DE 01 DA         [ 2] 2846 	ldw	x, (_c_gap56+0, x)
      0091B1 1F 41            [ 2] 2847 	ldw	(0x41, sp), x
      0091B3 AE 01 CE         [ 2] 2848 	ldw	x, #0x01ce
      0091B6 72 F0 41         [ 2] 2849 	subw	x, (0x41, sp)
      0091B9 57               [ 2] 2850 	sraw	x
      0091BA 90 FF            [ 2] 2851 	ldw	(y), x
                                   2852 ;	decoder.c: 601: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
      0091BC 7B 43            [ 1] 2853 	ld	a, (0x43, sp)
      0091BE 97               [ 1] 2854 	ld	xl, a
      0091BF A6 40            [ 1] 2855 	ld	a, #0x40
      0091C1 42               [ 4] 2856 	mul	x, a
      0091C2 1C 01 46         [ 2] 2857 	addw	x, #(_c_hist+0)
      0091C5 1F 41            [ 2] 2858 	ldw	(0x41, sp), x
      0091C7 4F               [ 1] 2859 	clr	a
      0091C8                       2860 00136$:
      0091C8 5F               [ 1] 2861 	clrw	x
      0091C9 97               [ 1] 2862 	ld	xl, a
      0091CA 72 FB 41         [ 2] 2863 	addw	x, (0x41, sp)
      0091CD 7F               [ 1] 2864 	clr	(x)
      0091CE 4C               [ 1] 2865 	inc	a
      0091CF A1 40            [ 1] 2866 	cp	a, #0x40
      0091D1 25 F5            [ 1] 2867 	jrc	00136$
                                   2868 ;	decoder.c: 602: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
      0091D3 1E 3F            [ 2] 2869 	ldw	x, (0x3f, sp)
      0091D5 1C 01 C6         [ 2] 2870 	addw	x, #(_c_labx0+0)
      0091D8 6F 01            [ 1] 2871 	clr	(0x1, x)
      0091DA A6 C0            [ 1] 2872 	ld	a, #0xc0
      0091DC F7               [ 1] 2873 	ld	(x), a
      0091DD 1E 3F            [ 2] 2874 	ldw	x, (0x3f, sp)
      0091DF 1C 01 CE         [ 2] 2875 	addw	x, #(_c_labx0b+0)
      0091E2 6F 01            [ 1] 2876 	clr	(0x1, x)
      0091E4 A6 C0            [ 1] 2877 	ld	a, #0xc0
      0091E6 F7               [ 1] 2878 	ld	(x), a
                                   2879 ;	decoder.c: 603: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
      0091E7 1E 3F            [ 2] 2880 	ldw	x, (0x3f, sp)
      0091E9 90 AE 3F FF      [ 2] 2881 	ldw	y, #0x3fff
      0091ED DF 01 CA         [ 2] 2882 	ldw	((_c_labx1+0), x), y
      0091F0 1E 3F            [ 2] 2883 	ldw	x, (0x3f, sp)
      0091F2 90 AE 3F FF      [ 2] 2884 	ldw	y, #0x3fff
      0091F6 DF 01 D2         [ 2] 2885 	ldw	((_c_labx1b+0), x), y
                                   2886 ;	decoder.c: 598: for (f = 0; f < 2; f++) {
      0091F9 0C 43            [ 1] 2887 	inc	(0x43, sp)
      0091FB 7B 43            [ 1] 2888 	ld	a, (0x43, sp)
      0091FD A1 02            [ 1] 2889 	cp	a, #0x02
      0091FF 25 9E            [ 1] 2890 	jrc	00138$
                                   2891 ;	decoder.c: 605: ss_init(&ss, cap, ncap);
      009201 1E 48            [ 2] 2892 	ldw	x, (0x48, sp)
      009203 89               [ 2] 2893 	pushw	x
      009204 1E 46            [ 2] 2894 	ldw	x, (0x46, sp)
      009206 89               [ 2] 2895 	pushw	x
      009207 96               [ 1] 2896 	ldw	x, sp
      009208 1C 00 05         [ 2] 2897 	addw	x, #5
      00920B CD 89 22         [ 4] 2898 	call	_ss_init
                                   2899 ;	decoder.c: 606: while (ss_next(&ss, &sg)) {
      00920E                       2900 00112$:
      00920E 96               [ 1] 2901 	ldw	x, sp
      00920F 1C 00 2F         [ 2] 2902 	addw	x, #47
      009212 89               [ 2] 2903 	pushw	x
      009213 96               [ 1] 2904 	ldw	x, sp
      009214 1C 00 03         [ 2] 2905 	addw	x, #3
      009217 CD 89 7E         [ 4] 2906 	call	_ss_next
      00921A 6B 43            [ 1] 2907 	ld	(0x43, sp), a
      00921C 26 03            [ 1] 2908 	jrne	00409$
      00921E CC 92 A2         [ 2] 2909 	jp	00114$
      009221                       2910 00409$:
                                   2911 ;	decoder.c: 608: uint8_t known_all = 1;
      009221 A6 01            [ 1] 2912 	ld	a, #0x01
      009223 6B 41            [ 1] 2913 	ld	(0x41, sp), a
                                   2914 ;	decoder.c: 610: cal_cloud(sg.u, sg.fam);
      009225 7B 37            [ 1] 2915 	ld	a, (0x37, sp)
      009227 1E 33            [ 2] 2916 	ldw	x, (0x33, sp)
      009229 CD 8D 3E         [ 4] 2917 	call	_cal_cloud
                                   2918 ;	decoder.c: 611: if (sg.k1 > NB) continue;
      00922C 1E 31            [ 2] 2919 	ldw	x, (0x31, sp)
      00922E A3 01 C0         [ 2] 2920 	cpw	x, #0x01c0
      009231 22 DB            [ 1] 2921 	jrugt	00112$
                                   2922 ;	decoder.c: 612: e = (sg.k1 < NB) ? sg.k1 : NB;
      009233 A3 01 C0         [ 2] 2923 	cpw	x, #0x01c0
      009236 24 04            [ 1] 2924 	jrnc	00146$
      009238 1F 42            [ 2] 2925 	ldw	(0x42, sp), x
      00923A 20 05            [ 2] 2926 	jra	00147$
      00923C                       2927 00146$:
      00923C AE 01 C0         [ 2] 2928 	ldw	x, #0x01c0
      00923F 1F 42            [ 2] 2929 	ldw	(0x42, sp), x
      009241                       2930 00147$:
                                   2931 ;	decoder.c: 613: for (t = sg.k0; t < e; t++)
      009241 96               [ 1] 2932 	ldw	x, sp
      009242 1C 00 2F         [ 2] 2933 	addw	x, #47
      009245 1F 3C            [ 2] 2934 	ldw	(0x3c, sp), x
      009247 FE               [ 2] 2935 	ldw	x, (x)
      009248                       2936 00141$:
      009248 13 42            [ 2] 2937 	cpw	x, (0x42, sp)
      00924A 24 0F            [ 1] 2938 	jrnc	00107$
                                   2939 ;	decoder.c: 614: if (known_bit(t) < 0) { known_all = 0; break; }
      00924C 89               [ 2] 2940 	pushw	x
      00924D CD 81 93         [ 4] 2941 	call	_known_bit
      009250 85               [ 2] 2942 	popw	x
      009251 4D               [ 1] 2943 	tnz	a
      009252 2A 04            [ 1] 2944 	jrpl	00142$
      009254 0F 41            [ 1] 2945 	clr	(0x41, sp)
      009256 20 03            [ 2] 2946 	jra	00107$
      009258                       2947 00142$:
                                   2948 ;	decoder.c: 613: for (t = sg.k0; t < e; t++)
      009258 5C               [ 1] 2949 	incw	x
      009259 20 ED            [ 2] 2950 	jra	00141$
      00925B                       2951 00107$:
                                   2952 ;	decoder.c: 615: if (!known_all) continue;
      00925B 0D 41            [ 1] 2953 	tnz	(0x41, sp)
      00925D 27 AF            [ 1] 2954 	jreq	00112$
                                   2955 ;	decoder.c: 616: a_bounds(sg.k0, sg.k1, &amin, &amax);
      00925F 16 31            [ 2] 2956 	ldw	y, (0x31, sp)
      009261 1E 3C            [ 2] 2957 	ldw	x, (0x3c, sp)
      009263 FE               [ 2] 2958 	ldw	x, (x)
      009264 1F 42            [ 2] 2959 	ldw	(0x42, sp), x
      009266 96               [ 1] 2960 	ldw	x, sp
      009267 1C 00 3A         [ 2] 2961 	addw	x, #58
      00926A 89               [ 2] 2962 	pushw	x
      00926B 96               [ 1] 2963 	ldw	x, sp
      00926C 1C 00 3A         [ 2] 2964 	addw	x, #58
      00926F 89               [ 2] 2965 	pushw	x
      009270 90 89            [ 2] 2966 	pushw	y
      009272 1E 48            [ 2] 2967 	ldw	x, (0x48, sp)
      009274 CD 8B F8         [ 4] 2968 	call	_a_bounds
                                   2969 ;	decoder.c: 617: if (amin == amax)
      009277 1E 38            [ 2] 2970 	ldw	x, (0x38, sp)
      009279 13 3A            [ 2] 2971 	cpw	x, (0x3a, sp)
      00927B 26 91            [ 1] 2972 	jrne	00112$
                                   2973 ;	decoder.c: 618: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
      00927D 7B 37            [ 1] 2974 	ld	a, (0x37, sp)
      00927F 16 35            [ 2] 2975 	ldw	y, (0x35, sp)
      009281 17 3E            [ 2] 2976 	ldw	(0x3e, sp), y
      009283 16 33            [ 2] 2977 	ldw	y, (0x33, sp)
      009285 17 40            [ 2] 2978 	ldw	(0x40, sp), y
      009287 16 31            [ 2] 2979 	ldw	y, (0x31, sp)
      009289 1E 3C            [ 2] 2980 	ldw	x, (0x3c, sp)
      00928B FE               [ 2] 2981 	ldw	x, (x)
      00928C 1F 42            [ 2] 2982 	ldw	(0x42, sp), x
      00928E 1E 38            [ 2] 2983 	ldw	x, (0x38, sp)
      009290 89               [ 2] 2984 	pushw	x
      009291 88               [ 1] 2985 	push	a
      009292 1E 41            [ 2] 2986 	ldw	x, (0x41, sp)
      009294 89               [ 2] 2987 	pushw	x
      009295 1E 45            [ 2] 2988 	ldw	x, (0x45, sp)
      009297 89               [ 2] 2989 	pushw	x
      009298 90 89            [ 2] 2990 	pushw	y
      00929A 1E 4B            [ 2] 2991 	ldw	x, (0x4b, sp)
      00929C CD 8D 85         [ 4] 2992 	call	_cal_add
      00929F CC 92 0E         [ 2] 2993 	jp	00112$
      0092A2                       2994 00114$:
                                   2995 ;	decoder.c: 622: int16_t h0 = H0P, h1 = H1P;
      0092A2 AE 00 9A         [ 2] 2996 	ldw	x, #0x009a
      0092A5 1F 3E            [ 2] 2997 	ldw	(0x3e, sp), x
      0092A7 AE 01 34         [ 2] 2998 	ldw	x, #0x0134
      0092AA 1F 40            [ 2] 2999 	ldw	(0x40, sp), x
                                   3000 ;	decoder.c: 623: if (c_n0 >= LAB_MIN) {
      0092AC C6 01 3E         [ 1] 3001 	ld	a, _c_n0+0
      0092AF A1 03            [ 1] 3002 	cp	a, #0x03
      0092B1 25 3E            [ 1] 3003 	jrc	00119$
                                   3004 ;	decoder.c: 624: int16_t h = (c_lo0 > c_hi0) ? (int16_t)((c_lo0 + c_hi0) >> 1)
      0092B3 CE 01 38         [ 2] 3005 	ldw	x, _c_hi0+0
      0092B6 C3 01 36         [ 2] 3006 	cpw	x, _c_lo0+0
      0092B9 2E 0A            [ 1] 3007 	jrsge	00148$
      0092BB CE 01 36         [ 2] 3008 	ldw	x, _c_lo0+0
      0092BE 72 BB 01 38      [ 2] 3009 	addw	x, _c_hi0+0
      0092C2 57               [ 2] 3010 	sraw	x
      0092C3 20 1E            [ 2] 3011 	jra	00149$
      0092C5                       3012 00148$:
      0092C5 CE 01 36         [ 2] 3013 	ldw	x, _c_lo0+0
      0092C8 A3 00 9A         [ 2] 3014 	cpw	x, #0x009a
      0092CB 2C 16            [ 1] 3015 	jrsgt	00151$
      0092CD CE 01 38         [ 2] 3016 	ldw	x, _c_hi0+0
      0092D0 A3 00 9A         [ 2] 3017 	cpw	x, #0x009a
      0092D3 2E 07            [ 1] 3018 	jrsge	00152$
      0092D5 CE 01 38         [ 2] 3019 	ldw	x, _c_hi0+0
      0092D8 1F 42            [ 2] 3020 	ldw	(0x42, sp), x
      0092DA 20 05            [ 2] 3021 	jra	00153$
      0092DC                       3022 00152$:
      0092DC AE 00 9A         [ 2] 3023 	ldw	x, #0x009a
      0092DF 1F 42            [ 2] 3024 	ldw	(0x42, sp), x
      0092E1                       3025 00153$:
      0092E1 1E 42            [ 2] 3026 	ldw	x, (0x42, sp)
      0092E3                       3027 00151$:
      0092E3                       3028 00149$:
                                   3029 ;	decoder.c: 626: if (h >= H0_LO && h <= H0_HI) h0 = h;
      0092E3 90 93            [ 1] 3030 	ldw	y, x
      0092E5 A3 00 70         [ 2] 3031 	cpw	x, #0x0070
      0092E8 2F 07            [ 1] 3032 	jrslt	00119$
      0092EA A3 00 C0         [ 2] 3033 	cpw	x, #0x00c0
      0092ED 2C 02            [ 1] 3034 	jrsgt	00119$
      0092EF 17 3E            [ 2] 3035 	ldw	(0x3e, sp), y
      0092F1                       3036 00119$:
                                   3037 ;	decoder.c: 628: if (c_n1 >= LAB_MIN) {
      0092F1 C6 01 3F         [ 1] 3038 	ld	a, _c_n1+0
      0092F4 A1 03            [ 1] 3039 	cp	a, #0x03
      0092F6 25 3E            [ 1] 3040 	jrc	00124$
                                   3041 ;	decoder.c: 629: int16_t h = (c_lo1 > c_hi1) ? (int16_t)((c_lo1 + c_hi1) >> 1)
      0092F8 CE 01 3C         [ 2] 3042 	ldw	x, _c_hi1+0
      0092FB C3 01 3A         [ 2] 3043 	cpw	x, _c_lo1+0
      0092FE 2E 0A            [ 1] 3044 	jrsge	00154$
      009300 CE 01 3A         [ 2] 3045 	ldw	x, _c_lo1+0
      009303 72 BB 01 3C      [ 2] 3046 	addw	x, _c_hi1+0
      009307 57               [ 2] 3047 	sraw	x
      009308 20 1E            [ 2] 3048 	jra	00155$
      00930A                       3049 00154$:
      00930A CE 01 3A         [ 2] 3050 	ldw	x, _c_lo1+0
      00930D A3 01 34         [ 2] 3051 	cpw	x, #0x0134
      009310 2C 16            [ 1] 3052 	jrsgt	00157$
      009312 CE 01 3C         [ 2] 3053 	ldw	x, _c_hi1+0
      009315 A3 01 34         [ 2] 3054 	cpw	x, #0x0134
      009318 2E 07            [ 1] 3055 	jrsge	00158$
      00931A CE 01 3C         [ 2] 3056 	ldw	x, _c_hi1+0
      00931D 1F 42            [ 2] 3057 	ldw	(0x42, sp), x
      00931F 20 05            [ 2] 3058 	jra	00159$
      009321                       3059 00158$:
      009321 AE 01 34         [ 2] 3060 	ldw	x, #0x0134
      009324 1F 42            [ 2] 3061 	ldw	(0x42, sp), x
      009326                       3062 00159$:
      009326 1E 42            [ 2] 3063 	ldw	x, (0x42, sp)
      009328                       3064 00157$:
      009328                       3065 00155$:
                                   3066 ;	decoder.c: 631: if (h >= H1_LO && h <= H1_HI) h1 = h;
      009328 90 93            [ 1] 3067 	ldw	y, x
      00932A A3 00 FC         [ 2] 3068 	cpw	x, #0x00fc
      00932D 2F 07            [ 1] 3069 	jrslt	00124$
      00932F A3 01 78         [ 2] 3070 	cpw	x, #0x0178
      009332 2C 02            [ 1] 3071 	jrsgt	00124$
      009334 17 40            [ 2] 3072 	ldw	(0x40, sp), y
      009336                       3073 00124$:
                                   3074 ;	decoder.c: 633: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
      009336 1E 40            [ 2] 3075 	ldw	x, (0x40, sp)
      009338 72 F0 3E         [ 2] 3076 	subw	x, (0x3e, sp)
      00933B A3 00 70         [ 2] 3077 	cpw	x, #0x0070
      00933E 2F 05            [ 1] 3078 	jrslt	00125$
      009340 A3 00 C4         [ 2] 3079 	cpw	x, #0x00c4
      009343 2D 0A            [ 1] 3080 	jrsle	00126$
      009345                       3081 00125$:
      009345 AE 00 9A         [ 2] 3082 	ldw	x, #0x009a
      009348 1F 3E            [ 2] 3083 	ldw	(0x3e, sp), x
      00934A AE 01 34         [ 2] 3084 	ldw	x, #0x0134
      00934D 1F 40            [ 2] 3085 	ldw	(0x40, sp), x
      00934F                       3086 00126$:
                                   3087 ;	decoder.c: 634: c_h0c = h0; c_h1c = h1;
      00934F 1E 3E            [ 2] 3088 	ldw	x, (0x3e, sp)
      009351 CF 01 40         [ 2] 3089 	ldw	_c_h0c+0, x
      009354 1E 40            [ 2] 3090 	ldw	x, (0x40, sp)
      009356 CF 01 42         [ 2] 3091 	ldw	_c_h1c+0, x
                                   3092 ;	decoder.c: 636: for (f = 0; f < 2; f++) {
      009359 0F 43            [ 1] 3093 	clr	(0x43, sp)
      00935B                       3094 00143$:
                                   3095 ;	decoder.c: 638: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
      00935B 96               [ 1] 3096 	ldw	x, sp
      00935C 1C 00 3A         [ 2] 3097 	addw	x, #58
      00935F 7B 43            [ 1] 3098 	ld	a, (0x43, sp)
      009361 CD 8E 9A         [ 4] 3099 	call	_theta56
      009364 6B 42            [ 1] 3100 	ld	(0x42, sp), a
      009366 5F               [ 1] 3101 	clrw	x
      009367 7B 43            [ 1] 3102 	ld	a, (0x43, sp)
      009369 97               [ 1] 3103 	ld	xl, a
      00936A 1C 01 44         [ 2] 3104 	addw	x, #(_c_d56+0)
      00936D 1F 3F            [ 2] 3105 	ldw	(0x3f, sp), x
      00936F 0D 42            [ 1] 3106 	tnz	(0x42, sp)
      009371 26 05            [ 1] 3107 	jrne	00129$
      009373 1E 3F            [ 2] 3108 	ldw	x, (0x3f, sp)
      009375 7F               [ 1] 3109 	clr	(x)
      009376 20 3B            [ 2] 3110 	jra	00134$
      009378                       3111 00129$:
                                   3112 ;	decoder.c: 639: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
      009378 CE 01 40         [ 2] 3113 	ldw	x, _c_h0c+0
      00937B 72 BB 01 42      [ 2] 3114 	addw	x, _c_h1c+0
      00937F 1F 41            [ 2] 3115 	ldw	(0x41, sp), x
      009381 5F               [ 1] 3116 	clrw	x
      009382 7B 43            [ 1] 3117 	ld	a, (0x43, sp)
      009384 97               [ 1] 3118 	ld	xl, a
      009385 58               [ 2] 3119 	sllw	x
      009386 90 93            [ 1] 3120 	ldw	y, x
      009388 DE 01 DA         [ 2] 3121 	ldw	x, (_c_gap56+0, x)
      00938B 50               [ 2] 3122 	negw	x
      00938C 72 FB 41         [ 2] 3123 	addw	x, (0x41, sp)
      00938F 57               [ 2] 3124 	sraw	x
      009390 1F 41            [ 2] 3125 	ldw	(0x41, sp), x
                                   3126 ;	decoder.c: 640: delta = (int16_t)(th + c_c0[f] - cfit);
      009392 93               [ 1] 3127 	ldw	x, y
      009393 DE 01 D6         [ 2] 3128 	ldw	x, (_c_c0+0, x)
      009396 72 FB 3A         [ 2] 3129 	addw	x, (0x3a, sp)
      009399 72 F0 41         [ 2] 3130 	subw	x, (0x41, sp)
                                   3131 ;	decoder.c: 641: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
      00939C A3 FF E8         [ 2] 3132 	cpw	x, #0xffe8
      00939F 2E 03            [ 1] 3133 	jrsge	00131$
      0093A1 AE FF E8         [ 2] 3134 	ldw	x, #0xffe8
      0093A4                       3135 00131$:
                                   3136 ;	decoder.c: 642: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
      0093A4 90 93            [ 1] 3137 	ldw	y, x
      0093A6 90 A3 00 18      [ 2] 3138 	cpw	y, #0x0018
      0093AA 2D 03            [ 1] 3139 	jrsle	00133$
      0093AC AE 00 18         [ 2] 3140 	ldw	x, #0x0018
      0093AF                       3141 00133$:
                                   3142 ;	decoder.c: 643: c_d56[f] = (int8_t)delta;
      0093AF 9F               [ 1] 3143 	ld	a, xl
      0093B0 1E 3F            [ 2] 3144 	ldw	x, (0x3f, sp)
      0093B2 F7               [ 1] 3145 	ld	(x), a
      0093B3                       3146 00134$:
                                   3147 ;	decoder.c: 636: for (f = 0; f < 2; f++) {
      0093B3 0C 43            [ 1] 3148 	inc	(0x43, sp)
      0093B5 7B 43            [ 1] 3149 	ld	a, (0x43, sp)
      0093B7 A1 02            [ 1] 3150 	cp	a, #0x02
      0093B9 25 A0            [ 1] 3151 	jrc	00143$
                                   3152 ;	decoder.c: 645: }
      0093BB 1E 46            [ 2] 3153 	ldw	x, (70, sp)
      0093BD 5B 49            [ 2] 3154 	addw	sp, #73
      0093BF FC               [ 2] 3155 	jp	(x)
                                   3156 ;	decoder.c: 649: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
                                   3157 ;	-----------------------------------------
                                   3158 ;	 function hinge
                                   3159 ;	-----------------------------------------
      0093C0                       3160 _hinge:
      0093C0 89               [ 2] 3161 	pushw	x
      0093C1 51               [ 1] 3162 	exgw	x, y
                                   3163 ;	decoder.c: 651: int16_t g = 0;
      0093C2 5F               [ 1] 3164 	clrw	x
                                   3165 ;	decoder.c: 652: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
      0093C3 72 F2 07         [ 2] 3166 	subw	y, (0x07, sp)
      0093C6 90 A3 00 00      [ 2] 3167 	cpw	y, #0x0000
      0093CA 2D 01            [ 1] 3168 	jrsle	00102$
      0093CC 93               [ 1] 3169 	ldw	x, y
      0093CD                       3170 00102$:
                                   3171 ;	decoder.c: 653: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
      0093CD 16 07            [ 2] 3172 	ldw	y, (0x07, sp)
      0093CF 72 F2 05         [ 2] 3173 	subw	y, (0x05, sp)
      0093D2 17 01            [ 2] 3174 	ldw	(0x01, sp), y
      0093D4 13 01            [ 2] 3175 	cpw	x, (0x01, sp)
      0093D6 2E 02            [ 1] 3176 	jrsge	00104$
      0093D8 1E 01            [ 2] 3177 	ldw	x, (0x01, sp)
      0093DA                       3178 00104$:
                                   3179 ;	decoder.c: 654: return (uint16_t)g;
                                   3180 ;	decoder.c: 655: }
      0093DA 16 03            [ 2] 3181 	ldw	y, (3, sp)
      0093DC 5B 08            [ 2] 3182 	addw	sp, #8
      0093DE 90 FC            [ 2] 3183 	jp	(y)
                                   3184 ;	decoder.c: 658: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                                   3185 ;	-----------------------------------------
                                   3186 ;	 function decide
                                   3187 ;	-----------------------------------------
      0093E0                       3188 _decide:
      0093E0 52 18            [ 2] 3189 	sub	sp, #24
      0093E2 1F 15            [ 2] 3190 	ldw	(0x15, sp), x
                                   3191 ;	decoder.c: 662: int16_t L = (int16_t)(k1 - k0);
      0093E4 1E 1B            [ 2] 3192 	ldw	x, (0x1b, sp)
      0093E6 72 F0 15         [ 2] 3193 	subw	x, (0x15, sp)
                                   3194 ;	decoder.c: 663: int16_t acap = (L < A_CAP) ? L : A_CAP;
      0093E9 1F 05            [ 2] 3195 	ldw	(0x05, sp), x
      0093EB A3 00 0F         [ 2] 3196 	cpw	x, #0x000f
      0093EE 2F 03            [ 1] 3197 	jrslt	00144$
      0093F0 AE 00 0F         [ 2] 3198 	ldw	x, #0x000f
      0093F3                       3199 00144$:
      0093F3 1F 07            [ 2] 3200 	ldw	(0x07, sp), x
                                   3201 ;	decoder.c: 664: int16_t h0e = c_h0c, h1e = c_h1c;
      0093F5 CE 01 40         [ 2] 3202 	ldw	x, _c_h0c+0
      0093F8 1F 09            [ 2] 3203 	ldw	(0x09, sp), x
      0093FA CE 01 42         [ 2] 3204 	ldw	x, _c_h1c+0
      0093FD 1F 0B            [ 2] 3205 	ldw	(0x0b, sp), x
                                   3206 ;	decoder.c: 668: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
      0093FF 7B 21            [ 1] 3207 	ld	a, (0x21, sp)
      009401 A1 05            [ 1] 3208 	cp	a, #0x05
      009403 26 19            [ 1] 3209 	jrne	00102$
      009405 C6 01 44         [ 1] 3210 	ld	a, _c_d56+0
      009408 6B 18            [ 1] 3211 	ld	(0x18, sp), a
      00940A 49               [ 1] 3212 	rlc	a
      00940B 4F               [ 1] 3213 	clr	a
      00940C A2 00            [ 1] 3214 	sbc	a, #0x00
      00940E 6B 17            [ 1] 3215 	ld	(0x17, sp), a
      009410 1E 09            [ 2] 3216 	ldw	x, (0x09, sp)
      009412 72 FB 17         [ 2] 3217 	addw	x, (0x17, sp)
      009415 1F 09            [ 2] 3218 	ldw	(0x09, sp), x
      009417 1E 0B            [ 2] 3219 	ldw	x, (0x0b, sp)
      009419 72 FB 17         [ 2] 3220 	addw	x, (0x17, sp)
      00941C 1F 0B            [ 2] 3221 	ldw	(0x0b, sp), x
      00941E                       3222 00102$:
                                   3223 ;	decoder.c: 669: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
      00941E 7B 21            [ 1] 3224 	ld	a, (0x21, sp)
      009420 A1 06            [ 1] 3225 	cp	a, #0x06
      009422 26 19            [ 1] 3226 	jrne	00104$
      009424 C6 01 45         [ 1] 3227 	ld	a, _c_d56+1
      009427 6B 18            [ 1] 3228 	ld	(0x18, sp), a
      009429 49               [ 1] 3229 	rlc	a
      00942A 4F               [ 1] 3230 	clr	a
      00942B A2 00            [ 1] 3231 	sbc	a, #0x00
      00942D 6B 17            [ 1] 3232 	ld	(0x17, sp), a
      00942F 1E 09            [ 2] 3233 	ldw	x, (0x09, sp)
      009431 72 FB 17         [ 2] 3234 	addw	x, (0x17, sp)
      009434 1F 09            [ 2] 3235 	ldw	(0x09, sp), x
      009436 1E 0B            [ 2] 3236 	ldw	x, (0x0b, sp)
      009438 72 FB 17         [ 2] 3237 	addw	x, (0x17, sp)
      00943B 1F 0B            [ 2] 3238 	ldw	(0x0b, sp), x
      00943D                       3239 00104$:
                                   3240 ;	decoder.c: 670: d_inter = 0;
      00943D 5F               [ 1] 3241 	clrw	x
      00943E CF 03 0C         [ 2] 3242 	ldw	_d_inter+0, x
                                   3243 ;	decoder.c: 671: for (a = 0; a <= acap; a++) {
      009441 1E 1D            [ 2] 3244 	ldw	x, (0x1d, sp)
      009443 13 09            [ 2] 3245 	cpw	x, (0x09, sp)
      009445 2F 04            [ 1] 3246 	jrslt	00373$
      009447 0F 0D            [ 1] 3247 	clr	(0x0d, sp)
      009449 20 04            [ 2] 3248 	jra	00374$
      00944B                       3249 00373$:
      00944B A6 01            [ 1] 3250 	ld	a, #0x01
      00944D 6B 0D            [ 1] 3251 	ld	(0x0d, sp), a
      00944F                       3252 00374$:
      00944F 1E 09            [ 2] 3253 	ldw	x, (0x09, sp)
      009451 13 1F            [ 2] 3254 	cpw	x, (0x1f, sp)
      009453 2C 04            [ 1] 3255 	jrsgt	00375$
      009455 0F 0E            [ 1] 3256 	clr	(0x0e, sp)
      009457 20 04            [ 2] 3257 	jra	00376$
      009459                       3258 00375$:
      009459 A6 01            [ 1] 3259 	ld	a, #0x01
      00945B 6B 0E            [ 1] 3260 	ld	(0x0e, sp), a
      00945D                       3261 00376$:
      00945D 5F               [ 1] 3262 	clrw	x
      00945E 1F 17            [ 2] 3263 	ldw	(0x17, sp), x
      009460                       3264 00133$:
      009460 1E 17            [ 2] 3265 	ldw	x, (0x17, sp)
      009462 13 07            [ 2] 3266 	cpw	x, (0x07, sp)
      009464 2D 03            [ 1] 3267 	jrsle	00377$
      009466 CC 95 0F         [ 2] 3268 	jp	00117$
      009469                       3269 00377$:
                                   3270 ;	decoder.c: 674: if (a == 0) {
      009469 1E 17            [ 2] 3271 	ldw	x, (0x17, sp)
      00946B 26 1C            [ 1] 3272 	jrne	00113$
                                   3273 ;	decoder.c: 675: c = hinge(u, v, h0e);
      00946D 1E 09            [ 2] 3274 	ldw	x, (0x09, sp)
      00946F 89               [ 2] 3275 	pushw	x
      009470 1E 21            [ 2] 3276 	ldw	x, (0x21, sp)
      009472 89               [ 2] 3277 	pushw	x
      009473 1E 21            [ 2] 3278 	ldw	x, (0x21, sp)
      009475 CD 93 C0         [ 4] 3279 	call	_hinge
      009478 1F 0F            [ 2] 3280 	ldw	(0x0f, sp), x
                                   3281 ;	decoder.c: 676: it = (u < h0e && h0e <= v);
      00947A 0D 0D            [ 1] 3282 	tnz	(0x0d, sp)
      00947C 27 04            [ 1] 3283 	jreq	00145$
      00947E 0D 0E            [ 1] 3284 	tnz	(0x0e, sp)
      009480 27 03            [ 1] 3285 	jreq	00146$
      009482                       3286 00145$:
      009482 4F               [ 1] 3287 	clr	a
      009483 20 61            [ 2] 3288 	jra	00114$
      009485                       3289 00146$:
      009485 A6 01            [ 1] 3290 	ld	a, #0x01
      009487 20 5D            [ 2] 3291 	jra	00114$
      009489                       3292 00113$:
                                   3293 ;	decoder.c: 678: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
      009489 16 17            [ 2] 3294 	ldw	y, (0x17, sp)
      00948B 17 11            [ 2] 3295 	ldw	(0x11, sp), y
      00948D 93               [ 1] 3296 	ldw	x, y
      00948E 5A               [ 2] 3297 	decw	x
      00948F 4F               [ 1] 3298 	clr	a
      009490 02               [ 1] 3299 	rlwa	x
      009491 58               [ 2] 3300 	sllw	x
      009492 72 FB 0B         [ 2] 3301 	addw	x, (0x0b, sp)
                                   3302 ;	decoder.c: 679: c = hinge(u, v, h);
      009495 1F 13            [ 2] 3303 	ldw	(0x13, sp), x
      009497 89               [ 2] 3304 	pushw	x
      009498 1E 21            [ 2] 3305 	ldw	x, (0x21, sp)
      00949A 89               [ 2] 3306 	pushw	x
      00949B 1E 21            [ 2] 3307 	ldw	x, (0x21, sp)
      00949D CD 93 C0         [ 4] 3308 	call	_hinge
      0094A0 1F 0F            [ 2] 3309 	ldw	(0x0f, sp), x
                                   3310 ;	decoder.c: 680: it = (u < h && h <= v);
      0094A2 1E 1D            [ 2] 3311 	ldw	x, (0x1d, sp)
      0094A4 13 13            [ 2] 3312 	cpw	x, (0x13, sp)
      0094A6 2E 06            [ 1] 3313 	jrsge	00148$
      0094A8 1E 13            [ 2] 3314 	ldw	x, (0x13, sp)
      0094AA 13 1F            [ 2] 3315 	cpw	x, (0x1f, sp)
      0094AC 2D 02            [ 1] 3316 	jrsle	00149$
      0094AE                       3317 00148$:
      0094AE 4F               [ 1] 3318 	clr	a
      0094AF C5                    3319 	.byte 0xc5
      0094B0                       3320 00149$:
      0094B0 A6 01            [ 1] 3321 	ld	a, #0x01
      0094B2                       3322 00150$:
                                   3323 ;	decoder.c: 681: if (a < L) {
      0094B2 1E 17            [ 2] 3324 	ldw	x, (0x17, sp)
      0094B4 13 05            [ 2] 3325 	cpw	x, (0x05, sp)
      0094B6 2E 2E            [ 1] 3326 	jrsge	00114$
                                   3327 ;	decoder.c: 682: int16_t h2 = (int16_t)(a * BIT_U + h0e);
      0094B8 02               [ 1] 3328 	rlwa	x
      0094B9 7B 12            [ 1] 3329 	ld	a, (0x12, sp)
      0094BB 01               [ 1] 3330 	rrwa	x
      0094BC 41               [ 1] 3331 	exg	a, xl
      0094BD 4F               [ 1] 3332 	clr	a
      0094BE 41               [ 1] 3333 	exg	a, xl
      0094BF 58               [ 2] 3334 	sllw	x
      0094C0 72 FB 09         [ 2] 3335 	addw	x, (0x09, sp)
      0094C3 1F 13            [ 2] 3336 	ldw	(0x13, sp), x
                                   3337 ;	decoder.c: 683: uint16_t c2 = hinge(u, v, h2);
      0094C5 88               [ 1] 3338 	push	a
      0094C6 1E 14            [ 2] 3339 	ldw	x, (0x14, sp)
      0094C8 89               [ 2] 3340 	pushw	x
      0094C9 1E 22            [ 2] 3341 	ldw	x, (0x22, sp)
      0094CB 89               [ 2] 3342 	pushw	x
      0094CC 1E 22            [ 2] 3343 	ldw	x, (0x22, sp)
      0094CE CD 93 C0         [ 4] 3344 	call	_hinge
      0094D1 84               [ 1] 3345 	pop	a
                                   3346 ;	decoder.c: 684: if (c2 < c) c = c2;
      0094D2 13 0F            [ 2] 3347 	cpw	x, (0x0f, sp)
      0094D4 24 02            [ 1] 3348 	jrnc	00106$
      0094D6 1F 0F            [ 2] 3349 	ldw	(0x0f, sp), x
      0094D8                       3350 00106$:
                                   3351 ;	decoder.c: 685: if (u < h2 && h2 <= v) it = 1;
      0094D8 1E 1D            [ 2] 3352 	ldw	x, (0x1d, sp)
      0094DA 13 13            [ 2] 3353 	cpw	x, (0x13, sp)
      0094DC 2E 08            [ 1] 3354 	jrsge	00114$
      0094DE 1E 13            [ 2] 3355 	ldw	x, (0x13, sp)
      0094E0 13 1F            [ 2] 3356 	cpw	x, (0x1f, sp)
      0094E2 2C 02            [ 1] 3357 	jrsgt	00114$
      0094E4 A6 01            [ 1] 3358 	ld	a, #0x01
      0094E6                       3359 00114$:
                                   3360 ;	decoder.c: 688: d_costs[a] = c;
      0094E6 1E 17            [ 2] 3361 	ldw	x, (0x17, sp)
      0094E8 58               [ 2] 3362 	sllw	x
      0094E9 16 0F            [ 2] 3363 	ldw	y, (0x0f, sp)
      0094EB DF 02 EC         [ 2] 3364 	ldw	((_d_costs+0), x), y
                                   3365 ;	decoder.c: 689: if (it) d_inter |= (uint16_t)(1u << a);
      0094EE 4D               [ 1] 3366 	tnz	a
      0094EF 27 16            [ 1] 3367 	jreq	00134$
      0094F1 5F               [ 1] 3368 	clrw	x
      0094F2 5C               [ 1] 3369 	incw	x
      0094F3 7B 18            [ 1] 3370 	ld	a, (0x18, sp)
      0094F5 27 04            [ 1] 3371 	jreq	00389$
      0094F7                       3372 00388$:
      0094F7 58               [ 2] 3373 	sllw	x
      0094F8 4A               [ 1] 3374 	dec	a
      0094F9 26 FC            [ 1] 3375 	jrne	00388$
      0094FB                       3376 00389$:
      0094FB 9F               [ 1] 3377 	ld	a, xl
      0094FC CA 03 0D         [ 1] 3378 	or	a, _d_inter+1
      0094FF 02               [ 1] 3379 	rlwa	x
      009500 CA 03 0C         [ 1] 3380 	or	a, _d_inter+0
      009503 95               [ 1] 3381 	ld	xh, a
      009504 CF 03 0C         [ 2] 3382 	ldw	_d_inter+0, x
      009507                       3383 00134$:
                                   3384 ;	decoder.c: 671: for (a = 0; a <= acap; a++) {
      009507 1E 17            [ 2] 3385 	ldw	x, (0x17, sp)
      009509 5C               [ 1] 3386 	incw	x
      00950A 1F 17            [ 2] 3387 	ldw	(0x17, sp), x
      00950C CC 94 60         [ 2] 3388 	jp	00133$
      00950F                       3389 00117$:
                                   3390 ;	decoder.c: 692: bc = 0xFFFF; bi = 1; *a_free = 0;
      00950F 5F               [ 1] 3391 	clrw	x
      009510 5A               [ 2] 3392 	decw	x
      009511 1F 10            [ 2] 3393 	ldw	(0x10, sp), x
      009513 A6 01            [ 1] 3394 	ld	a, #0x01
      009515 6B 12            [ 1] 3395 	ld	(0x12, sp), a
      009517 16 24            [ 2] 3396 	ldw	y, (0x24, sp)
      009519 17 13            [ 2] 3397 	ldw	(0x13, sp), y
      00951B 93               [ 1] 3398 	ldw	x, y
      00951C 6F 01            [ 1] 3399 	clr	(0x1, x)
      00951E 7F               [ 1] 3400 	clr	(x)
                                   3401 ;	decoder.c: 693: for (a = 0; a <= acap; a++) {
      00951F 5F               [ 1] 3402 	clrw	x
      009520 1F 17            [ 2] 3403 	ldw	(0x17, sp), x
      009522                       3404 00136$:
      009522 1E 17            [ 2] 3405 	ldw	x, (0x17, sp)
      009524 13 07            [ 2] 3406 	cpw	x, (0x07, sp)
      009526 2C 33            [ 1] 3407 	jrsgt	00123$
                                   3408 ;	decoder.c: 694: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      009528 CE 03 0C         [ 2] 3409 	ldw	x, _d_inter+0
      00952B 7B 18            [ 1] 3410 	ld	a, (0x18, sp)
      00952D 27 04            [ 1] 3411 	jreq	00393$
      00952F                       3412 00392$:
      00952F 54               [ 2] 3413 	srlw	x
      009530 4A               [ 1] 3414 	dec	a
      009531 26 FC            [ 1] 3415 	jrne	00392$
      009533                       3416 00393$:
      009533 9F               [ 1] 3417 	ld	a, xl
      009534 A4 01            [ 1] 3418 	and	a, #0x01
                                   3419 ;	decoder.c: 695: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      009536 1E 17            [ 2] 3420 	ldw	x, (0x17, sp)
      009538 58               [ 2] 3421 	sllw	x
      009539 DE 02 EC         [ 2] 3422 	ldw	x, (_d_costs+0, x)
      00953C 13 10            [ 2] 3423 	cpw	x, (0x10, sp)
      00953E 25 0B            [ 1] 3424 	jrc	00118$
      009540 13 10            [ 2] 3425 	cpw	x, (0x10, sp)
      009542 26 10            [ 1] 3426 	jrne	00137$
      009544 4D               [ 1] 3427 	tnz	a
      009545 27 0D            [ 1] 3428 	jreq	00137$
      009547 0D 12            [ 1] 3429 	tnz	(0x12, sp)
      009549 26 09            [ 1] 3430 	jrne	00137$
      00954B                       3431 00118$:
                                   3432 ;	decoder.c: 696: bc = d_costs[a]; bi = it; *a_free = a;
      00954B 1F 10            [ 2] 3433 	ldw	(0x10, sp), x
      00954D 6B 12            [ 1] 3434 	ld	(0x12, sp), a
      00954F 1E 13            [ 2] 3435 	ldw	x, (0x13, sp)
      009551 16 17            [ 2] 3436 	ldw	y, (0x17, sp)
      009553 FF               [ 2] 3437 	ldw	(x), y
      009554                       3438 00137$:
                                   3439 ;	decoder.c: 693: for (a = 0; a <= acap; a++) {
      009554 1E 17            [ 2] 3440 	ldw	x, (0x17, sp)
      009556 5C               [ 1] 3441 	incw	x
      009557 1F 17            [ 2] 3442 	ldw	(0x17, sp), x
      009559 20 C7            [ 2] 3443 	jra	00136$
      00955B                       3444 00123$:
                                   3445 ;	decoder.c: 699: a_bounds(k0, k1, &amin, &amax);
      00955B 96               [ 1] 3446 	ldw	x, sp
      00955C 1C 00 03         [ 2] 3447 	addw	x, #3
      00955F 89               [ 2] 3448 	pushw	x
      009560 96               [ 1] 3449 	ldw	x, sp
      009561 1C 00 03         [ 2] 3450 	addw	x, #3
      009564 89               [ 2] 3451 	pushw	x
      009565 1E 1F            [ 2] 3452 	ldw	x, (0x1f, sp)
      009567 89               [ 2] 3453 	pushw	x
      009568 1E 1B            [ 2] 3454 	ldw	x, (0x1b, sp)
      00956A CD 8B F8         [ 4] 3455 	call	_a_bounds
                                   3456 ;	decoder.c: 700: lo = (amin > 0) ? amin : 0;
      00956D 1E 01            [ 2] 3457 	ldw	x, (0x01, sp)
      00956F A3 00 00         [ 2] 3458 	cpw	x, #0x0000
      009572 2C 01            [ 1] 3459 	jrsgt	00152$
      009574 5F               [ 1] 3460 	clrw	x
      009575                       3461 00152$:
      009575 1F 0C            [ 2] 3462 	ldw	(0x0c, sp), x
                                   3463 ;	decoder.c: 701: hi = (amax < acap) ? amax : acap;
      009577 1E 03            [ 2] 3464 	ldw	x, (0x03, sp)
      009579 13 07            [ 2] 3465 	cpw	x, (0x07, sp)
      00957B 2E 03            [ 1] 3466 	jrsge	00153$
      00957D 1E 03            [ 2] 3467 	ldw	x, (0x03, sp)
      00957F C5                    3468 	.byte 0xc5
      009580                       3469 00153$:
      009580 1E 07            [ 2] 3470 	ldw	x, (0x07, sp)
      009582                       3471 00154$:
      009582 1F 0E            [ 2] 3472 	ldw	(0x0e, sp), x
                                   3473 ;	decoder.c: 702: if (lo > hi) { lo = 0; hi = acap; }
      009584 1E 0C            [ 2] 3474 	ldw	x, (0x0c, sp)
      009586 13 0E            [ 2] 3475 	cpw	x, (0x0e, sp)
      009588 2D 07            [ 1] 3476 	jrsle	00125$
      00958A 5F               [ 1] 3477 	clrw	x
      00958B 1F 0C            [ 2] 3478 	ldw	(0x0c, sp), x
      00958D 16 07            [ 2] 3479 	ldw	y, (0x07, sp)
      00958F 17 0E            [ 2] 3480 	ldw	(0x0e, sp), y
      009591                       3481 00125$:
                                   3482 ;	decoder.c: 703: bc = 0xFFFF; bi = 1; *a_hat = lo;
      009591 5F               [ 1] 3483 	clrw	x
      009592 5A               [ 2] 3484 	decw	x
      009593 1F 10            [ 2] 3485 	ldw	(0x10, sp), x
      009595 A6 01            [ 1] 3486 	ld	a, #0x01
      009597 6B 12            [ 1] 3487 	ld	(0x12, sp), a
      009599 16 22            [ 2] 3488 	ldw	y, (0x22, sp)
      00959B 17 13            [ 2] 3489 	ldw	(0x13, sp), y
      00959D 93               [ 1] 3490 	ldw	x, y
      00959E 16 0C            [ 2] 3491 	ldw	y, (0x0c, sp)
      0095A0 FF               [ 2] 3492 	ldw	(x), y
                                   3493 ;	decoder.c: 704: for (a = lo; a <= hi; a++) {
      0095A1 16 0C            [ 2] 3494 	ldw	y, (0x0c, sp)
      0095A3 17 17            [ 2] 3495 	ldw	(0x17, sp), y
      0095A5                       3496 00139$:
      0095A5 1E 17            [ 2] 3497 	ldw	x, (0x17, sp)
      0095A7 13 0E            [ 2] 3498 	cpw	x, (0x0e, sp)
      0095A9 2C 33            [ 1] 3499 	jrsgt	00131$
                                   3500 ;	decoder.c: 705: uint8_t it = (uint8_t)((d_inter >> a) & 1);
      0095AB CE 03 0C         [ 2] 3501 	ldw	x, _d_inter+0
      0095AE 7B 18            [ 1] 3502 	ld	a, (0x18, sp)
      0095B0 27 04            [ 1] 3503 	jreq	00406$
      0095B2                       3504 00405$:
      0095B2 54               [ 2] 3505 	srlw	x
      0095B3 4A               [ 1] 3506 	dec	a
      0095B4 26 FC            [ 1] 3507 	jrne	00405$
      0095B6                       3508 00406$:
      0095B6 9F               [ 1] 3509 	ld	a, xl
      0095B7 A4 01            [ 1] 3510 	and	a, #0x01
                                   3511 ;	decoder.c: 706: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
      0095B9 1E 17            [ 2] 3512 	ldw	x, (0x17, sp)
      0095BB 58               [ 2] 3513 	sllw	x
      0095BC DE 02 EC         [ 2] 3514 	ldw	x, (_d_costs+0, x)
      0095BF 13 10            [ 2] 3515 	cpw	x, (0x10, sp)
      0095C1 25 0B            [ 1] 3516 	jrc	00126$
      0095C3 13 10            [ 2] 3517 	cpw	x, (0x10, sp)
      0095C5 26 10            [ 1] 3518 	jrne	00140$
      0095C7 4D               [ 1] 3519 	tnz	a
      0095C8 27 0D            [ 1] 3520 	jreq	00140$
      0095CA 0D 12            [ 1] 3521 	tnz	(0x12, sp)
      0095CC 26 09            [ 1] 3522 	jrne	00140$
      0095CE                       3523 00126$:
                                   3524 ;	decoder.c: 707: bc = d_costs[a]; bi = it; *a_hat = a;
      0095CE 1F 10            [ 2] 3525 	ldw	(0x10, sp), x
      0095D0 6B 12            [ 1] 3526 	ld	(0x12, sp), a
      0095D2 1E 13            [ 2] 3527 	ldw	x, (0x13, sp)
      0095D4 16 17            [ 2] 3528 	ldw	y, (0x17, sp)
      0095D6 FF               [ 2] 3529 	ldw	(x), y
      0095D7                       3530 00140$:
                                   3531 ;	decoder.c: 704: for (a = lo; a <= hi; a++) {
      0095D7 1E 17            [ 2] 3532 	ldw	x, (0x17, sp)
      0095D9 5C               [ 1] 3533 	incw	x
      0095DA 1F 17            [ 2] 3534 	ldw	(0x17, sp), x
      0095DC 20 C7            [ 2] 3535 	jra	00139$
      0095DE                       3536 00131$:
                                   3537 ;	decoder.c: 710: *lo_out = lo; *hi_out = hi;
      0095DE 1E 26            [ 2] 3538 	ldw	x, (0x26, sp)
      0095E0 16 0C            [ 2] 3539 	ldw	y, (0x0c, sp)
      0095E2 FF               [ 2] 3540 	ldw	(x), y
      0095E3 1E 28            [ 2] 3541 	ldw	x, (0x28, sp)
      0095E5 16 0E            [ 2] 3542 	ldw	y, (0x0e, sp)
      0095E7 FF               [ 2] 3543 	ldw	(x), y
                                   3544 ;	decoder.c: 711: return acap;
      0095E8 1E 07            [ 2] 3545 	ldw	x, (0x07, sp)
                                   3546 ;	decoder.c: 712: }
      0095EA 16 19            [ 2] 3547 	ldw	y, (25, sp)
      0095EC 5B 29            [ 2] 3548 	addw	sp, #41
      0095EE 90 FC            [ 2] 3549 	jp	(y)
                                   3550 ;	decoder.c: 714: static void decide_pass(const uint8_t *cap, uint16_t ncap)
                                   3551 ;	-----------------------------------------
                                   3552 ;	 function decide_pass
                                   3553 ;	-----------------------------------------
      0095F0                       3554 _decide_pass:
      0095F0 52 55            [ 2] 3555 	sub	sp, #85
      0095F2 1F 50            [ 2] 3556 	ldw	(0x50, sp), x
                                   3557 ;	decoder.c: 719: for (t = 0; t < NBB; t++) { d_bits[t] = 0; d_conf[t] = 0; d_tied[t] = 0; }
      0095F4 90 5F            [ 1] 3558 	clrw	y
      0095F6                       3559 00171$:
      0095F6 93               [ 1] 3560 	ldw	x, y
      0095F7 72 4F 01 DE      [ 1] 3561 	clr	((_d_bits+0), x)
      0095FB 93               [ 1] 3562 	ldw	x, y
      0095FC 72 4F 02 16      [ 1] 3563 	clr	((_d_conf+0), x)
      009600 93               [ 1] 3564 	ldw	x, y
      009601 72 4F 02 4E      [ 1] 3565 	clr	((_d_tied+0), x)
      009605 90 5C            [ 1] 3566 	incw	y
      009607 90 A3 00 38      [ 2] 3567 	cpw	y, #0x0038
      00960B 25 E9            [ 1] 3568 	jrc	00171$
                                   3569 ;	decoder.c: 720: d_nknife = 0; d_nres = 0;
      00960D 72 5F 02 C6      [ 1] 3570 	clr	_d_nknife+0
      009611 72 5F 02 E7      [ 1] 3571 	clr	_d_nres+0
                                   3572 ;	decoder.c: 721: d_infeas = 0; d_laberr = 0; d_nseg = 0;
      009615 72 5F 02 E8      [ 1] 3573 	clr	_d_infeas+0
      009619 72 5F 02 E9      [ 1] 3574 	clr	_d_laberr+0
      00961D 5F               [ 1] 3575 	clrw	x
      00961E CF 02 EA         [ 2] 3576 	ldw	_d_nseg+0, x
                                   3577 ;	decoder.c: 722: ss_init(&ss, cap, ncap);
      009621 1E 58            [ 2] 3578 	ldw	x, (0x58, sp)
      009623 89               [ 2] 3579 	pushw	x
      009624 1E 52            [ 2] 3580 	ldw	x, (0x52, sp)
      009626 89               [ 2] 3581 	pushw	x
      009627 96               [ 1] 3582 	ldw	x, sp
      009628 1C 00 05         [ 2] 3583 	addw	x, #5
      00962B CD 89 22         [ 4] 3584 	call	_ss_init
                                   3585 ;	decoder.c: 723: while (ss_next(&ss, &sg)) {
      00962E                       3586 00168$:
      00962E 96               [ 1] 3587 	ldw	x, sp
      00962F 1C 00 2F         [ 2] 3588 	addw	x, #47
      009632 89               [ 2] 3589 	pushw	x
      009633 96               [ 1] 3590 	ldw	x, sp
      009634 1C 00 03         [ 2] 3591 	addw	x, #3
      009637 CD 89 7E         [ 4] 3592 	call	_ss_next
      00963A 6B 55            [ 1] 3593 	ld	(0x55, sp), a
      00963C 26 03            [ 1] 3594 	jrne	00592$
      00963E CC 98 D9         [ 2] 3595 	jp	00188$
      009641                       3596 00592$:
                                   3597 ;	decoder.c: 725: int16_t L = (int16_t)(sg.k1 - sg.k0);
      009641 16 31            [ 2] 3598 	ldw	y, (0x31, sp)
      009643 96               [ 1] 3599 	ldw	x, sp
      009644 1C 00 2F         [ 2] 3600 	addw	x, #47
      009647 1F 40            [ 2] 3601 	ldw	(0x40, sp), x
      009649 FE               [ 2] 3602 	ldw	x, (x)
      00964A 1F 54            [ 2] 3603 	ldw	(0x54, sp), x
      00964C 72 F2 54         [ 2] 3604 	subw	y, (0x54, sp)
      00964F 17 42            [ 2] 3605 	ldw	(0x42, sp), y
                                   3606 ;	decoder.c: 728: int16_t ins0 = -1, ins1 = -1;
      009651 5F               [ 1] 3607 	clrw	x
      009652 5A               [ 2] 3608 	decw	x
      009653 1F 4A            [ 2] 3609 	ldw	(0x4a, sp), x
      009655 5F               [ 1] 3610 	clrw	x
      009656 5A               [ 2] 3611 	decw	x
      009657 1F 4C            [ 2] 3612 	ldw	(0x4c, sp), x
                                   3613 ;	decoder.c: 729: d_nseg++;
      009659 CE 02 EA         [ 2] 3614 	ldw	x, _d_nseg+0
      00965C 5C               [ 1] 3615 	incw	x
      00965D CF 02 EA         [ 2] 3616 	ldw	_d_nseg+0, x
                                   3617 ;	decoder.c: 730: if (sg.k0 >= NB) continue;
      009660 1E 40            [ 2] 3618 	ldw	x, (0x40, sp)
      009662 FE               [ 2] 3619 	ldw	x, (x)
      009663 1F 4E            [ 2] 3620 	ldw	(0x4e, sp), x
      009665 A3 01 C0         [ 2] 3621 	cpw	x, #0x01c0
      009668 24 C4            [ 1] 3622 	jrnc	00168$
                                   3623 ;	decoder.c: 732: &a_hat, &a_free, &lo, &hi);
                                   3624 ;	decoder.c: 731: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
      00966A 7B 37            [ 1] 3625 	ld	a, (0x37, sp)
      00966C 16 35            [ 2] 3626 	ldw	y, (0x35, sp)
      00966E 1E 33            [ 2] 3627 	ldw	x, (0x33, sp)
      009670 1F 52            [ 2] 3628 	ldw	(0x52, sp), x
      009672 1E 31            [ 2] 3629 	ldw	x, (0x31, sp)
      009674 1F 54            [ 2] 3630 	ldw	(0x54, sp), x
      009676 96               [ 1] 3631 	ldw	x, sp
      009677 1C 00 3E         [ 2] 3632 	addw	x, #62
      00967A 89               [ 2] 3633 	pushw	x
      00967B 96               [ 1] 3634 	ldw	x, sp
      00967C 1C 00 3E         [ 2] 3635 	addw	x, #62
      00967F 89               [ 2] 3636 	pushw	x
      009680 96               [ 1] 3637 	ldw	x, sp
      009681 1C 00 3E         [ 2] 3638 	addw	x, #62
      009684 89               [ 2] 3639 	pushw	x
      009685 96               [ 1] 3640 	ldw	x, sp
      009686 1C 00 3E         [ 2] 3641 	addw	x, #62
      009689 89               [ 2] 3642 	pushw	x
      00968A 88               [ 1] 3643 	push	a
      00968B 90 89            [ 2] 3644 	pushw	y
      00968D 1E 5D            [ 2] 3645 	ldw	x, (0x5d, sp)
      00968F 89               [ 2] 3646 	pushw	x
      009690 1E 61            [ 2] 3647 	ldw	x, (0x61, sp)
      009692 89               [ 2] 3648 	pushw	x
      009693 1E 5D            [ 2] 3649 	ldw	x, (0x5d, sp)
      009695 CD 93 E0         [ 4] 3650 	call	_decide
      009698 1F 4E            [ 2] 3651 	ldw	(0x4e, sp), x
                                   3652 ;	decoder.c: 733: c_hat = d_costs[a_hat];
      00969A 1E 38            [ 2] 3653 	ldw	x, (0x38, sp)
      00969C 58               [ 2] 3654 	sllw	x
      00969D DE 02 EC         [ 2] 3655 	ldw	x, (_d_costs+0, x)
                                   3656 ;	decoder.c: 734: if (c_hat > INFEAS_U && d_infeas < 255) d_infeas++;
      0096A0 A3 00 A0         [ 2] 3657 	cpw	x, #0x00a0
      0096A3 23 0B            [ 2] 3658 	jrule	00105$
      0096A5 C6 02 E8         [ 1] 3659 	ld	a, _d_infeas+0
      0096A8 A1 FF            [ 1] 3660 	cp	a, #0xff
      0096AA 24 04            [ 1] 3661 	jrnc	00105$
      0096AC 72 5C 02 E8      [ 1] 3662 	inc	_d_infeas+0
      0096B0                       3663 00105$:
                                   3664 ;	decoder.c: 735: e = (sg.k1 < NB) ? sg.k1 : NB;
      0096B0 1E 31            [ 2] 3665 	ldw	x, (0x31, sp)
      0096B2 A3 01 C0         [ 2] 3666 	cpw	x, #0x01c0
      0096B5 24 04            [ 1] 3667 	jrnc	00190$
      0096B7 1F 54            [ 2] 3668 	ldw	(0x54, sp), x
      0096B9 20 05            [ 2] 3669 	jra	00191$
      0096BB                       3670 00190$:
      0096BB AE 01 C0         [ 2] 3671 	ldw	x, #0x01c0
      0096BE 1F 54            [ 2] 3672 	ldw	(0x54, sp), x
      0096C0                       3673 00191$:
      0096C0 16 54            [ 2] 3674 	ldw	y, (0x54, sp)
      0096C2 17 44            [ 2] 3675 	ldw	(0x44, sp), y
                                   3676 ;	decoder.c: 736: known_all = 1;
      0096C4 A6 01            [ 1] 3677 	ld	a, #0x01
      0096C6 6B 52            [ 1] 3678 	ld	(0x52, sp), a
                                   3679 ;	decoder.c: 737: for (t = sg.k0; t < e; t++)
      0096C8 1E 40            [ 2] 3680 	ldw	x, (0x40, sp)
      0096CA FE               [ 2] 3681 	ldw	x, (x)
      0096CB 1F 54            [ 2] 3682 	ldw	(0x54, sp), x
      0096CD                       3683 00174$:
                                   3684 ;	decoder.c: 738: if (known_bit(t) < 0) { known_all = 0; break; }
      0096CD 1E 54            [ 2] 3685 	ldw	x, (0x54, sp)
      0096CF 13 44            [ 2] 3686 	cpw	x, (0x44, sp)
      0096D1 24 11            [ 1] 3687 	jrnc	00109$
      0096D3 CD 81 93         [ 4] 3688 	call	_known_bit
      0096D6 4D               [ 1] 3689 	tnz	a
      0096D7 2A 04            [ 1] 3690 	jrpl	00175$
      0096D9 0F 52            [ 1] 3691 	clr	(0x52, sp)
      0096DB 20 07            [ 2] 3692 	jra	00109$
      0096DD                       3693 00175$:
                                   3694 ;	decoder.c: 737: for (t = sg.k0; t < e; t++)
      0096DD 1E 54            [ 2] 3695 	ldw	x, (0x54, sp)
      0096DF 5C               [ 1] 3696 	incw	x
      0096E0 1F 54            [ 2] 3697 	ldw	(0x54, sp), x
      0096E2 20 E9            [ 2] 3698 	jra	00174$
      0096E4                       3699 00109$:
                                   3700 ;	decoder.c: 739: dead = 0; nins = 0;
      0096E4 0F 53            [ 1] 3701 	clr	(0x53, sp)
                                   3702 ;	decoder.c: 740: for (a = 0; a <= acap; a++)
      0096E6 4F               [ 1] 3703 	clr	a
      0096E7 5F               [ 1] 3704 	clrw	x
      0096E8 1F 54            [ 2] 3705 	ldw	(0x54, sp), x
      0096EA                       3706 00177$:
      0096EA 1E 54            [ 2] 3707 	ldw	x, (0x54, sp)
      0096EC 13 4E            [ 2] 3708 	cpw	x, (0x4e, sp)
      0096EE 2C 18            [ 1] 3709 	jrsgt	00112$
                                   3710 ;	decoder.c: 741: if ((d_inter >> a) & 1) nins++;
      0096F0 88               [ 1] 3711 	push	a
      0096F1 CE 03 0C         [ 2] 3712 	ldw	x, _d_inter+0
      0096F4 7B 56            [ 1] 3713 	ld	a, (0x56, sp)
      0096F6 27 04            [ 1] 3714 	jreq	00602$
      0096F8                       3715 00601$:
      0096F8 54               [ 2] 3716 	srlw	x
      0096F9 4A               [ 1] 3717 	dec	a
      0096FA 26 FC            [ 1] 3718 	jrne	00601$
      0096FC                       3719 00602$:
      0096FC 84               [ 1] 3720 	pop	a
      0096FD 54               [ 2] 3721 	srlw	x
      0096FE 24 01            [ 1] 3722 	jrnc	00178$
      009700 4C               [ 1] 3723 	inc	a
      009701                       3724 00178$:
                                   3725 ;	decoder.c: 740: for (a = 0; a <= acap; a++)
      009701 1E 54            [ 2] 3726 	ldw	x, (0x54, sp)
      009703 5C               [ 1] 3727 	incw	x
      009704 1F 54            [ 2] 3728 	ldw	(0x54, sp), x
      009706 20 E2            [ 2] 3729 	jra	00177$
      009708                       3730 00112$:
                                   3731 ;	decoder.c: 742: if (nins >= 2) dead = 1;
      009708 A1 02            [ 1] 3732 	cp	a, #0x02
      00970A 25 04            [ 1] 3733 	jrc	00114$
      00970C A6 01            [ 1] 3734 	ld	a, #0x01
      00970E 6B 53            [ 1] 3735 	ld	(0x53, sp), a
      009710                       3736 00114$:
                                   3737 ;	decoder.c: 743: if (known_all && lo == hi && a_free != lo && !dead && d_laberr < 255)
      009710 0D 52            [ 1] 3738 	tnz	(0x52, sp)
      009712 27 1B            [ 1] 3739 	jreq	00116$
      009714 1E 3C            [ 2] 3740 	ldw	x, (0x3c, sp)
      009716 13 3E            [ 2] 3741 	cpw	x, (0x3e, sp)
      009718 26 15            [ 1] 3742 	jrne	00116$
      00971A 1E 3A            [ 2] 3743 	ldw	x, (0x3a, sp)
      00971C 13 3C            [ 2] 3744 	cpw	x, (0x3c, sp)
      00971E 27 0F            [ 1] 3745 	jreq	00116$
      009720 0D 53            [ 1] 3746 	tnz	(0x53, sp)
      009722 26 0B            [ 1] 3747 	jrne	00116$
      009724 C6 02 E9         [ 1] 3748 	ld	a, _d_laberr+0
      009727 A1 FF            [ 1] 3749 	cp	a, #0xff
      009729 24 04            [ 1] 3750 	jrnc	00116$
                                   3751 ;	decoder.c: 744: d_laberr++;
      00972B 72 5C 02 E9      [ 1] 3752 	inc	_d_laberr+0
      00972F                       3753 00116$:
                                   3754 ;	decoder.c: 747: for (a = lo; a <= hi; a++) {
      00972F 1E 3C            [ 2] 3755 	ldw	x, (0x3c, sp)
      009731 4F               [ 1] 3756 	clr	a
      009732 1F 54            [ 2] 3757 	ldw	(0x54, sp), x
      009734                       3758 00180$:
      009734 1E 54            [ 2] 3759 	ldw	x, (0x54, sp)
      009736 13 3E            [ 2] 3760 	cpw	x, (0x3e, sp)
      009738 2C 29            [ 1] 3761 	jrsgt	00128$
                                   3762 ;	decoder.c: 748: if ((d_inter >> a) & 1) {
      00973A 88               [ 1] 3763 	push	a
      00973B CE 03 0C         [ 2] 3764 	ldw	x, _d_inter+0
      00973E 7B 56            [ 1] 3765 	ld	a, (0x56, sp)
      009740 27 04            [ 1] 3766 	jreq	00617$
      009742                       3767 00616$:
      009742 54               [ 2] 3768 	srlw	x
      009743 4A               [ 1] 3769 	dec	a
      009744 26 FC            [ 1] 3770 	jrne	00616$
      009746                       3771 00617$:
      009746 84               [ 1] 3772 	pop	a
      009747 54               [ 2] 3773 	srlw	x
      009748 24 12            [ 1] 3774 	jrnc	00181$
                                   3775 ;	decoder.c: 749: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
      00974A 4D               [ 1] 3776 	tnz	a
      00974B 26 06            [ 1] 3777 	jrne	00124$
      00974D 16 54            [ 2] 3778 	ldw	y, (0x54, sp)
      00974F 17 4A            [ 2] 3779 	ldw	(0x4a, sp), y
      009751 20 08            [ 2] 3780 	jra	00125$
      009753                       3781 00124$:
      009753 A1 01            [ 1] 3782 	cp	a, #0x01
      009755 26 04            [ 1] 3783 	jrne	00125$
      009757 16 54            [ 2] 3784 	ldw	y, (0x54, sp)
      009759 17 4C            [ 2] 3785 	ldw	(0x4c, sp), y
      00975B                       3786 00125$:
                                   3787 ;	decoder.c: 750: nins++;
      00975B 4C               [ 1] 3788 	inc	a
      00975C                       3789 00181$:
                                   3790 ;	decoder.c: 747: for (a = lo; a <= hi; a++) {
      00975C 1E 54            [ 2] 3791 	ldw	x, (0x54, sp)
      00975E 5C               [ 1] 3792 	incw	x
      00975F 1F 54            [ 2] 3793 	ldw	(0x54, sp), x
      009761 20 D1            [ 2] 3794 	jra	00180$
      009763                       3795 00128$:
                                   3796 ;	decoder.c: 753: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
      009763 A1 02            [ 1] 3797 	cp	a, #0x02
      009765 25 3B            [ 1] 3798 	jrc	00132$
      009767 1E 38            [ 2] 3799 	ldw	x, (0x38, sp)
      009769 13 4A            [ 2] 3800 	cpw	x, (0x4a, sp)
      00976B 27 06            [ 1] 3801 	jreq	00131$
      00976D 1E 38            [ 2] 3802 	ldw	x, (0x38, sp)
      00976F 13 4C            [ 2] 3803 	cpw	x, (0x4c, sp)
      009771 26 2F            [ 1] 3804 	jrne	00132$
      009773                       3805 00131$:
                                   3806 ;	decoder.c: 754: uint16_t tt = (uint16_t)(sg.k0 + ins0);
      009773 1E 40            [ 2] 3807 	ldw	x, (0x40, sp)
      009775 FE               [ 2] 3808 	ldw	x, (x)
      009776 1F 54            [ 2] 3809 	ldw	(0x54, sp), x
      009778 16 4A            [ 2] 3810 	ldw	y, (0x4a, sp)
      00977A 72 F9 54         [ 2] 3811 	addw	y, (0x54, sp)
                                   3812 ;	decoder.c: 755: if (tt < NB) BSET(d_tied, tt);
      00977D 93               [ 1] 3813 	ldw	x, y
      00977E A3 01 C0         [ 2] 3814 	cpw	x, #0x01c0
      009781 24 1F            [ 1] 3815 	jrnc	00132$
      009783 54               [ 2] 3816 	srlw	x
      009784 54               [ 2] 3817 	srlw	x
      009785 54               [ 2] 3818 	srlw	x
      009786 1C 02 4E         [ 2] 3819 	addw	x, #(_d_tied+0)
      009789 F6               [ 1] 3820 	ld	a, (x)
      00978A 6B 54            [ 1] 3821 	ld	(0x54, sp), a
      00978C 90 9F            [ 1] 3822 	ld	a, yl
      00978E A4 07            [ 1] 3823 	and	a, #0x07
      009790 6B 55            [ 1] 3824 	ld	(0x55, sp), a
      009792 A6 01            [ 1] 3825 	ld	a, #0x01
      009794 88               [ 1] 3826 	push	a
      009795 7B 56            [ 1] 3827 	ld	a, (0x56, sp)
      009797 27 05            [ 1] 3828 	jreq	00633$
      009799                       3829 00632$:
      009799 08 01            [ 1] 3830 	sll	(1, sp)
      00979B 4A               [ 1] 3831 	dec	a
      00979C 26 FB            [ 1] 3832 	jrne	00632$
      00979E                       3833 00633$:
      00979E 84               [ 1] 3834 	pop	a
      00979F 1A 54            [ 1] 3835 	or	a, (0x54, sp)
      0097A1 F7               [ 1] 3836 	ld	(x), a
      0097A2                       3837 00132$:
                                   3838 ;	decoder.c: 758: for (t = sg.k0; t < e; t++) {
      0097A2 1E 40            [ 2] 3839 	ldw	x, (0x40, sp)
      0097A4 FE               [ 2] 3840 	ldw	x, (x)
      0097A5 1F 52            [ 2] 3841 	ldw	(0x52, sp), x
      0097A7                       3842 00186$:
      0097A7 1E 52            [ 2] 3843 	ldw	x, (0x52, sp)
      0097A9 13 44            [ 2] 3844 	cpw	x, (0x44, sp)
      0097AB 25 03            [ 1] 3845 	jrc	00634$
      0097AD CC 98 6D         [ 2] 3846 	jp	00154$
      0097B0                       3847 00634$:
                                   3848 ;	decoder.c: 759: int16_t off = (int16_t)(t - sg.k0);
      0097B0 1E 40            [ 2] 3849 	ldw	x, (0x40, sp)
      0097B2 FE               [ 2] 3850 	ldw	x, (x)
      0097B3 50               [ 2] 3851 	negw	x
      0097B4 72 FB 52         [ 2] 3852 	addw	x, (0x52, sp)
      0097B7 1F 46            [ 2] 3853 	ldw	(0x46, sp), x
                                   3854 ;	decoder.c: 760: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
      0097B9 5F               [ 1] 3855 	clrw	x
      0097BA 5A               [ 2] 3856 	decw	x
      0097BB 1F 48            [ 2] 3857 	ldw	(0x48, sp), x
      0097BD 5F               [ 1] 3858 	clrw	x
      0097BE 5A               [ 2] 3859 	decw	x
      0097BF 1F 4A            [ 2] 3860 	ldw	(0x4a, sp), x
                                   3861 ;	decoder.c: 761: if (off < a_hat) BSET(d_bits, t);
      0097C1 1E 52            [ 2] 3862 	ldw	x, (0x52, sp)
      0097C3 54               [ 2] 3863 	srlw	x
      0097C4 54               [ 2] 3864 	srlw	x
      0097C5 54               [ 2] 3865 	srlw	x
      0097C6 1F 4C            [ 2] 3866 	ldw	(0x4c, sp), x
      0097C8 7B 53            [ 1] 3867 	ld	a, (0x53, sp)
      0097CA A4 07            [ 1] 3868 	and	a, #0x07
      0097CC 6B 4E            [ 1] 3869 	ld	(0x4e, sp), a
      0097CE A6 01            [ 1] 3870 	ld	a, #0x01
      0097D0 6B 4F            [ 1] 3871 	ld	(0x4f, sp), a
      0097D2 7B 4E            [ 1] 3872 	ld	a, (0x4e, sp)
      0097D4 27 05            [ 1] 3873 	jreq	00636$
      0097D6                       3874 00635$:
      0097D6 08 4F            [ 1] 3875 	sll	(0x4f, sp)
      0097D8 4A               [ 1] 3876 	dec	a
      0097D9 26 FB            [ 1] 3877 	jrne	00635$
      0097DB                       3878 00636$:
      0097DB 1E 46            [ 2] 3879 	ldw	x, (0x46, sp)
      0097DD 13 38            [ 2] 3880 	cpw	x, (0x38, sp)
      0097DF 2E 09            [ 1] 3881 	jrsge	00136$
      0097E1 1E 4C            [ 2] 3882 	ldw	x, (0x4c, sp)
      0097E3 1C 01 DE         [ 2] 3883 	addw	x, #(_d_bits+0)
      0097E6 F6               [ 1] 3884 	ld	a, (x)
      0097E7 1A 4F            [ 1] 3885 	or	a, (0x4f, sp)
      0097E9 F7               [ 1] 3886 	ld	(x), a
      0097EA                       3887 00136$:
                                   3888 ;	decoder.c: 762: for (a = lo; a <= hi; a++) {
      0097EA 16 3C            [ 2] 3889 	ldw	y, (0x3c, sp)
      0097EC 17 54            [ 2] 3890 	ldw	(0x54, sp), y
      0097EE                       3891 00183$:
      0097EE 1E 54            [ 2] 3892 	ldw	x, (0x54, sp)
      0097F0 13 3E            [ 2] 3893 	cpw	x, (0x3e, sp)
      0097F2 2C 23            [ 1] 3894 	jrsgt	00144$
                                   3895 ;	decoder.c: 763: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
      0097F4 1E 54            [ 2] 3896 	ldw	x, (0x54, sp)
      0097F6 58               [ 2] 3897 	sllw	x
      0097F7 DE 02 EC         [ 2] 3898 	ldw	x, (_d_costs+0, x)
      0097FA 89               [ 2] 3899 	pushw	x
      0097FB 1E 56            [ 2] 3900 	ldw	x, (0x56, sp)
      0097FD 13 48            [ 2] 3901 	cpw	x, (0x48, sp)
      0097FF 85               [ 2] 3902 	popw	x
      009800 2D 08            [ 1] 3903 	jrsle	00142$
      009802 13 4A            [ 2] 3904 	cpw	x, (0x4a, sp)
      009804 24 0A            [ 1] 3905 	jrnc	00184$
      009806 1F 4A            [ 2] 3906 	ldw	(0x4a, sp), x
      009808 20 06            [ 2] 3907 	jra	00184$
      00980A                       3908 00142$:
                                   3909 ;	decoder.c: 764: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
      00980A 13 48            [ 2] 3910 	cpw	x, (0x48, sp)
      00980C 24 02            [ 1] 3911 	jrnc	00184$
      00980E 1F 48            [ 2] 3912 	ldw	(0x48, sp), x
      009810                       3913 00184$:
                                   3914 ;	decoder.c: 762: for (a = lo; a <= hi; a++) {
      009810 1E 54            [ 2] 3915 	ldw	x, (0x54, sp)
      009812 5C               [ 1] 3916 	incw	x
      009813 1F 54            [ 2] 3917 	ldw	(0x54, sp), x
      009815 20 D7            [ 2] 3918 	jra	00183$
      009817                       3919 00144$:
                                   3920 ;	decoder.c: 766: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
      009817 1E 48            [ 2] 3921 	ldw	x, (0x48, sp)
      009819 5C               [ 1] 3922 	incw	x
      00981A 27 05            [ 1] 3923 	jreq	00147$
      00981C 1E 4A            [ 2] 3924 	ldw	x, (0x4a, sp)
      00981E 5C               [ 1] 3925 	incw	x
      00981F 26 07            [ 1] 3926 	jrne	00148$
      009821                       3927 00147$:
      009821 AE 00 FF         [ 2] 3928 	ldw	x, #0x00ff
      009824 1F 54            [ 2] 3929 	ldw	(0x54, sp), x
      009826 20 1A            [ 2] 3930 	jra	00149$
      009828                       3931 00148$:
                                   3932 ;	decoder.c: 768: int16_t dm = (int16_t)(c0m - c1m);
      009828 1E 48            [ 2] 3933 	ldw	x, (0x48, sp)
      00982A 72 F0 4A         [ 2] 3934 	subw	x, (0x4a, sp)
                                   3935 ;	decoder.c: 769: if (dm < 0) dm = (int16_t)-dm;
      00982D 1F 54            [ 2] 3936 	ldw	(0x54, sp), x
      00982F 5D               [ 2] 3937 	tnzw	x
      009830 2A 07            [ 1] 3938 	jrpl	00146$
      009832 00 55            [ 1] 3939 	neg	(0x55, sp)
      009834 4F               [ 1] 3940 	clr	a
      009835 12 54            [ 1] 3941 	sbc	a, (0x54, sp)
      009837 6B 54            [ 1] 3942 	ld	(0x54, sp), a
      009839                       3943 00146$:
                                   3944 ;	decoder.c: 770: m = (dm > 255) ? 255 : (uint16_t)dm;
      009839 AE 00 FF         [ 2] 3945 	ldw	x, #0x00ff
      00983C 13 54            [ 2] 3946 	cpw	x, (0x54, sp)
      00983E 2C 02            [ 1] 3947 	jrsgt	00192$
      009840 1F 54            [ 2] 3948 	ldw	(0x54, sp), x
      009842                       3949 00192$:
      009842                       3950 00149$:
                                   3951 ;	decoder.c: 772: if (m >= CONF_M && !BGET(d_tied, t)) BSET(d_conf, t);
      009842 1E 54            [ 2] 3952 	ldw	x, (0x54, sp)
      009844 A3 00 10         [ 2] 3953 	cpw	x, #0x0010
      009847 25 1C            [ 1] 3954 	jrc	00187$
      009849 1E 4C            [ 2] 3955 	ldw	x, (0x4c, sp)
      00984B D6 02 4E         [ 1] 3956 	ld	a, (_d_tied+0, x)
      00984E 88               [ 1] 3957 	push	a
      00984F 7B 4F            [ 1] 3958 	ld	a, (0x4f, sp)
      009851 27 05            [ 1] 3959 	jreq	00653$
      009853                       3960 00652$:
      009853 04 01            [ 1] 3961 	srl	(1, sp)
      009855 4A               [ 1] 3962 	dec	a
      009856 26 FB            [ 1] 3963 	jrne	00652$
      009858                       3964 00653$:
      009858 84               [ 1] 3965 	pop	a
      009859 44               [ 1] 3966 	srl	a
      00985A 25 09            [ 1] 3967 	jrc	00187$
      00985C 1E 4C            [ 2] 3968 	ldw	x, (0x4c, sp)
      00985E 1C 02 16         [ 2] 3969 	addw	x, #(_d_conf+0)
      009861 F6               [ 1] 3970 	ld	a, (x)
      009862 1A 4F            [ 1] 3971 	or	a, (0x4f, sp)
      009864 F7               [ 1] 3972 	ld	(x), a
      009865                       3973 00187$:
                                   3974 ;	decoder.c: 758: for (t = sg.k0; t < e; t++) {
      009865 1E 52            [ 2] 3975 	ldw	x, (0x52, sp)
      009867 5C               [ 1] 3976 	incw	x
      009868 1F 52            [ 2] 3977 	ldw	(0x52, sp), x
      00986A CC 97 A7         [ 2] 3978 	jp	00186$
      00986D                       3979 00154$:
                                   3980 ;	decoder.c: 775: if ((sg.fam == 5 || sg.fam == 6) && L == 1 &&
      00986D 7B 37            [ 1] 3981 	ld	a, (0x37, sp)
      00986F A1 05            [ 1] 3982 	cp	a, #0x05
      009871 27 07            [ 1] 3983 	jreq	00165$
      009873 A1 06            [ 1] 3984 	cp	a, #0x06
      009875 27 03            [ 1] 3985 	jreq	00661$
      009877 CC 96 2E         [ 2] 3986 	jp	00168$
      00987A                       3987 00661$:
      00987A                       3988 00165$:
      00987A 1E 42            [ 2] 3989 	ldw	x, (0x42, sp)
      00987C 5A               [ 2] 3990 	decw	x
      00987D 27 03            [ 1] 3991 	jreq	00664$
      00987F CC 96 2E         [ 2] 3992 	jp	00168$
      009882                       3993 00664$:
                                   3994 ;	decoder.c: 776: sg.k0 >= 32 && sg.k0 < NB - 32) {
      009882 1E 40            [ 2] 3995 	ldw	x, (0x40, sp)
      009884 FE               [ 2] 3996 	ldw	x, (x)
      009885 A3 00 20         [ 2] 3997 	cpw	x, #0x0020
      009888 24 03            [ 1] 3998 	jrnc	00665$
      00988A CC 96 2E         [ 2] 3999 	jp	00168$
      00988D                       4000 00665$:
      00988D A3 01 A0         [ 2] 4001 	cpw	x, #0x01a0
      009890 25 03            [ 1] 4002 	jrc	00666$
      009892 CC 96 2E         [ 2] 4003 	jp	00168$
      009895                       4004 00666$:
                                   4005 ;	decoder.c: 777: int16_t dm = (int16_t)(d_costs[0] - d_costs[1]);
      009895 90 CE 02 EC      [ 2] 4006 	ldw	y, _d_costs+0
      009899 CE 02 EE         [ 2] 4007 	ldw	x, _d_costs+2
      00989C 1F 54            [ 2] 4008 	ldw	(0x54, sp), x
      00989E 72 F2 54         [ 2] 4009 	subw	y, (0x54, sp)
                                   4010 ;	decoder.c: 778: if (dm < 0) dm = (int16_t)-dm;
      0098A1 93               [ 1] 4011 	ldw	x, y
      0098A2 5D               [ 2] 4012 	tnzw	x
      0098A3 2A 02            [ 1] 4013 	jrpl	00156$
      0098A5 90 50            [ 2] 4014 	negw	y
      0098A7                       4015 00156$:
                                   4016 ;	decoder.c: 779: if (dm > 255) dm = 255;
      0098A7 93               [ 1] 4017 	ldw	x, y
      0098A8 A3 00 FF         [ 2] 4018 	cpw	x, #0x00ff
      0098AB 2D 04            [ 1] 4019 	jrsle	00158$
      0098AD 90 AE 00 FF      [ 2] 4020 	ldw	y, #0x00ff
      0098B1                       4021 00158$:
                                   4022 ;	decoder.c: 780: if (dm < KNIFE_M && d_nknife < KNIFE_MAX)
      0098B1 93               [ 1] 4023 	ldw	x, y
      0098B2 A3 00 18         [ 2] 4024 	cpw	x, #0x0018
      0098B5 2F 03            [ 1] 4025 	jrslt	00669$
      0098B7 CC 96 2E         [ 2] 4026 	jp	00168$
      0098BA                       4027 00669$:
      0098BA C6 02 C6         [ 1] 4028 	ld	a, _d_nknife+0
      0098BD A1 20            [ 1] 4029 	cp	a, #0x20
      0098BF 25 03            [ 1] 4030 	jrc	00670$
      0098C1 CC 96 2E         [ 2] 4031 	jp	00168$
      0098C4                       4032 00670$:
                                   4033 ;	decoder.c: 781: d_knife[d_nknife++] = sg.k0;
      0098C4 C6 02 C6         [ 1] 4034 	ld	a, _d_nknife+0
      0098C7 72 5C 02 C6      [ 1] 4035 	inc	_d_nknife+0
      0098CB 5F               [ 1] 4036 	clrw	x
      0098CC 97               [ 1] 4037 	ld	xl, a
      0098CD 58               [ 2] 4038 	sllw	x
      0098CE 1C 02 86         [ 2] 4039 	addw	x, #(_d_knife+0)
      0098D1 16 40            [ 2] 4040 	ldw	y, (0x40, sp)
      0098D3 90 FE            [ 2] 4041 	ldw	y, (y)
      0098D5 FF               [ 2] 4042 	ldw	(x), y
      0098D6 CC 96 2E         [ 2] 4043 	jp	00168$
      0098D9                       4044 00188$:
                                   4045 ;	decoder.c: 784: }
      0098D9 1E 56            [ 2] 4046 	ldw	x, (86, sp)
      0098DB 5B 59            [ 2] 4047 	addw	sp, #89
      0098DD FC               [ 2] 4048 	jp	(x)
                                   4049 ;	decoder.c: 788: static uint8_t is_knife(uint16_t t)
                                   4050 ;	-----------------------------------------
                                   4051 ;	 function is_knife
                                   4052 ;	-----------------------------------------
      0098DE                       4053 _is_knife:
      0098DE 89               [ 2] 4054 	pushw	x
      0098DF 1F 01            [ 2] 4055 	ldw	(0x01, sp), x
                                   4056 ;	decoder.c: 791: for (i = 0; i < d_nknife; i++)
      0098E1 4F               [ 1] 4057 	clr	a
      0098E2                       4058 00105$:
      0098E2 C1 02 C6         [ 1] 4059 	cp	a, _d_nknife+0
      0098E5 24 11            [ 1] 4060 	jrnc	00103$
                                   4061 ;	decoder.c: 792: if (d_knife[i] == t) return 1;
      0098E7 5F               [ 1] 4062 	clrw	x
      0098E8 97               [ 1] 4063 	ld	xl, a
      0098E9 58               [ 2] 4064 	sllw	x
      0098EA DE 02 86         [ 2] 4065 	ldw	x, (_d_knife+0, x)
      0098ED 13 01            [ 2] 4066 	cpw	x, (0x01, sp)
      0098EF 26 04            [ 1] 4067 	jrne	00106$
      0098F1 A6 01            [ 1] 4068 	ld	a, #0x01
      0098F3 20 04            [ 2] 4069 	jra	00107$
      0098F5                       4070 00106$:
                                   4071 ;	decoder.c: 791: for (i = 0; i < d_nknife; i++)
      0098F5 4C               [ 1] 4072 	inc	a
      0098F6 20 EA            [ 2] 4073 	jra	00105$
      0098F8                       4074 00103$:
                                   4075 ;	decoder.c: 793: return 0;
      0098F8 4F               [ 1] 4076 	clr	a
      0098F9                       4077 00107$:
                                   4078 ;	decoder.c: 794: }
      0098F9 85               [ 2] 4079 	popw	x
      0098FA 81               [ 4] 4080 	ret
                                   4081 ;	decoder.c: 796: static uint8_t is_resolved(uint16_t t)
                                   4082 ;	-----------------------------------------
                                   4083 ;	 function is_resolved
                                   4084 ;	-----------------------------------------
      0098FB                       4085 _is_resolved:
      0098FB 89               [ 2] 4086 	pushw	x
      0098FC 1F 01            [ 2] 4087 	ldw	(0x01, sp), x
                                   4088 ;	decoder.c: 799: for (i = 0; i < d_nres; i++)
      0098FE 4F               [ 1] 4089 	clr	a
      0098FF                       4090 00105$:
      0098FF C1 02 E7         [ 1] 4091 	cp	a, _d_nres+0
      009902 24 11            [ 1] 4092 	jrnc	00103$
                                   4093 ;	decoder.c: 800: if (d_resolved[i] == t) return 1;
      009904 5F               [ 1] 4094 	clrw	x
      009905 97               [ 1] 4095 	ld	xl, a
      009906 58               [ 2] 4096 	sllw	x
      009907 DE 02 C7         [ 2] 4097 	ldw	x, (_d_resolved+0, x)
      00990A 13 01            [ 2] 4098 	cpw	x, (0x01, sp)
      00990C 26 04            [ 1] 4099 	jrne	00106$
      00990E A6 01            [ 1] 4100 	ld	a, #0x01
      009910 20 04            [ 2] 4101 	jra	00107$
      009912                       4102 00106$:
                                   4103 ;	decoder.c: 799: for (i = 0; i < d_nres; i++)
      009912 4C               [ 1] 4104 	inc	a
      009913 20 EA            [ 2] 4105 	jra	00105$
      009915                       4106 00103$:
                                   4107 ;	decoder.c: 801: return 0;
      009915 4F               [ 1] 4108 	clr	a
      009916                       4109 00107$:
                                   4110 ;	decoder.c: 802: }
      009916 85               [ 2] 4111 	popw	x
      009917 81               [ 4] 4112 	ret
                                   4113 ;	decoder.c: 804: static void votes(void)
                                   4114 ;	-----------------------------------------
                                   4115 ;	 function votes
                                   4116 ;	-----------------------------------------
      009918                       4117 _votes:
      009918 52 19            [ 2] 4118 	sub	sp, #25
                                   4119 ;	decoder.c: 806: uint8_t lag_ok[2] = {0, 0};
      00991A 0F 01            [ 1] 4120 	clr	(0x01, sp)
      00991C 0F 02            [ 1] 4121 	clr	(0x02, sp)
                                   4122 ;	decoder.c: 809: for (li = 0; li < 2; li++) {
      00991E 0F 13            [ 1] 4123 	clr	(0x13, sp)
      009920                       4124 00174$:
                                   4125 ;	decoder.c: 810: uint16_t lag = li ? 16 : 8;
      009920 0D 13            [ 1] 4126 	tnz	(0x13, sp)
      009922 27 06            [ 1] 4127 	jreq	00183$
      009924 A6 10            [ 1] 4128 	ld	a, #0x10
      009926 6B 19            [ 1] 4129 	ld	(0x19, sp), a
      009928 20 04            [ 2] 4130 	jra	00184$
      00992A                       4131 00183$:
      00992A A6 08            [ 1] 4132 	ld	a, #0x08
      00992C 6B 19            [ 1] 4133 	ld	(0x19, sp), a
      00992E                       4134 00184$:
      00992E 7B 19            [ 1] 4135 	ld	a, (0x19, sp)
      009930 6B 0E            [ 1] 4136 	ld	(0x0e, sp), a
      009932 0F 0D            [ 1] 4137 	clr	(0x0d, sp)
                                   4138 ;	decoder.c: 812: for (t = 32; t + lag < (uint16_t)(NB - 32); t++) {
      009934 5F               [ 1] 4139 	clrw	x
      009935 1F 14            [ 2] 4140 	ldw	(0x14, sp), x
      009937 5F               [ 1] 4141 	clrw	x
      009938 1F 16            [ 2] 4142 	ldw	(0x16, sp), x
      00993A AE 00 20         [ 2] 4143 	ldw	x, #0x0020
      00993D 1F 18            [ 2] 4144 	ldw	(0x18, sp), x
      00993F                       4145 00173$:
      00993F 1E 18            [ 2] 4146 	ldw	x, (0x18, sp)
      009941 72 FB 0D         [ 2] 4147 	addw	x, (0x0d, sp)
      009944 A3 01 A0         [ 2] 4148 	cpw	x, #0x01a0
      009947 25 03            [ 1] 4149 	jrc	00591$
      009949 CC 99 FE         [ 2] 4150 	jp	00113$
      00994C                       4151 00591$:
                                   4152 ;	decoder.c: 813: uint16_t s = (uint16_t)(t + lag);
      00994C 1F 0B            [ 2] 4153 	ldw	(0x0b, sp), x
                                   4154 ;	decoder.c: 814: if (is_knife(t) || is_knife(s)) continue;
      00994E 1E 18            [ 2] 4155 	ldw	x, (0x18, sp)
      009950 CD 98 DE         [ 4] 4156 	call	_is_knife
      009953 4D               [ 1] 4157 	tnz	a
      009954 27 03            [ 1] 4158 	jreq	00592$
      009956 CC 99 F6         [ 2] 4159 	jp	00112$
      009959                       4160 00592$:
      009959 1E 0B            [ 2] 4161 	ldw	x, (0x0b, sp)
      00995B CD 98 DE         [ 4] 4162 	call	_is_knife
      00995E 4D               [ 1] 4163 	tnz	a
      00995F 27 03            [ 1] 4164 	jreq	00593$
      009961 CC 99 F6         [ 2] 4165 	jp	00112$
      009964                       4166 00593$:
                                   4167 ;	decoder.c: 815: if (BGET(d_tied, t) || BGET(d_tied, s)) continue;
      009964 1E 18            [ 2] 4168 	ldw	x, (0x18, sp)
      009966 54               [ 2] 4169 	srlw	x
      009967 54               [ 2] 4170 	srlw	x
      009968 54               [ 2] 4171 	srlw	x
      009969 1F 0F            [ 2] 4172 	ldw	(0x0f, sp), x
      00996B 1C 02 4E         [ 2] 4173 	addw	x, #(_d_tied+0)
      00996E F6               [ 1] 4174 	ld	a, (x)
      00996F 97               [ 1] 4175 	ld	xl, a
      009970 7B 19            [ 1] 4176 	ld	a, (0x19, sp)
      009972 A4 07            [ 1] 4177 	and	a, #0x07
      009974 6B 11            [ 1] 4178 	ld	(0x11, sp), a
      009976 27 06            [ 1] 4179 	jreq	00595$
      009978                       4180 00594$:
      009978 41               [ 1] 4181 	exg	a, xl
      009979 44               [ 1] 4182 	srl	a
      00997A 41               [ 1] 4183 	exg	a, xl
      00997B 4A               [ 1] 4184 	dec	a
      00997C 26 FA            [ 1] 4185 	jrne	00594$
      00997E                       4186 00595$:
      00997E 54               [ 2] 4187 	srlw	x
      00997F 25 75            [ 1] 4188 	jrc	00112$
      009981 16 0B            [ 2] 4189 	ldw	y, (0x0b, sp)
      009983 A6 08            [ 1] 4190 	ld	a, #0x08
      009985 90 62            [ 2] 4191 	div	y, a
      009987 93               [ 1] 4192 	ldw	x, y
      009988 1C 02 4E         [ 2] 4193 	addw	x, #(_d_tied+0)
      00998B F6               [ 1] 4194 	ld	a, (x)
      00998C 97               [ 1] 4195 	ld	xl, a
      00998D 7B 0C            [ 1] 4196 	ld	a, (0x0c, sp)
      00998F A4 07            [ 1] 4197 	and	a, #0x07
      009991 6B 12            [ 1] 4198 	ld	(0x12, sp), a
      009993 27 06            [ 1] 4199 	jreq	00598$
      009995                       4200 00597$:
      009995 41               [ 1] 4201 	exg	a, xl
      009996 44               [ 1] 4202 	srl	a
      009997 41               [ 1] 4203 	exg	a, xl
      009998 4A               [ 1] 4204 	dec	a
      009999 26 FA            [ 1] 4205 	jrne	00597$
      00999B                       4206 00598$:
      00999B 54               [ 2] 4207 	srlw	x
      00999C 25 58            [ 1] 4208 	jrc	00112$
                                   4209 ;	decoder.c: 816: if (!BGET(d_conf, t) || !BGET(d_conf, s)) continue;
      00999E 1E 0F            [ 2] 4210 	ldw	x, (0x0f, sp)
      0099A0 D6 02 16         [ 1] 4211 	ld	a, (_d_conf+0, x)
      0099A3 88               [ 1] 4212 	push	a
      0099A4 7B 12            [ 1] 4213 	ld	a, (0x12, sp)
      0099A6 27 05            [ 1] 4214 	jreq	00601$
      0099A8                       4215 00600$:
      0099A8 04 01            [ 1] 4216 	srl	(1, sp)
      0099AA 4A               [ 1] 4217 	dec	a
      0099AB 26 FB            [ 1] 4218 	jrne	00600$
      0099AD                       4219 00601$:
      0099AD 84               [ 1] 4220 	pop	a
      0099AE 44               [ 1] 4221 	srl	a
      0099AF 24 45            [ 1] 4222 	jrnc	00112$
      0099B1 93               [ 1] 4223 	ldw	x, y
      0099B2 D6 02 16         [ 1] 4224 	ld	a, (_d_conf+0, x)
      0099B5 88               [ 1] 4225 	push	a
      0099B6 7B 13            [ 1] 4226 	ld	a, (0x13, sp)
      0099B8 27 05            [ 1] 4227 	jreq	00604$
      0099BA                       4228 00603$:
      0099BA 04 01            [ 1] 4229 	srl	(1, sp)
      0099BC 4A               [ 1] 4230 	dec	a
      0099BD 26 FB            [ 1] 4231 	jrne	00603$
      0099BF                       4232 00604$:
      0099BF 84               [ 1] 4233 	pop	a
      0099C0 44               [ 1] 4234 	srl	a
      0099C1 24 33            [ 1] 4235 	jrnc	00112$
                                   4236 ;	decoder.c: 817: n_pair++;
      0099C3 1E 16            [ 2] 4237 	ldw	x, (0x16, sp)
      0099C5 5C               [ 1] 4238 	incw	x
      0099C6 1F 16            [ 2] 4239 	ldw	(0x16, sp), x
                                   4240 ;	decoder.c: 818: if (BGET(d_bits, t) == BGET(d_bits, s)) agree++;
      0099C8 1E 0F            [ 2] 4241 	ldw	x, (0x0f, sp)
      0099CA D6 01 DE         [ 1] 4242 	ld	a, (_d_bits+0, x)
      0099CD 88               [ 1] 4243 	push	a
      0099CE 7B 12            [ 1] 4244 	ld	a, (0x12, sp)
      0099D0 27 05            [ 1] 4245 	jreq	00608$
      0099D2                       4246 00607$:
      0099D2 04 01            [ 1] 4247 	srl	(1, sp)
      0099D4 4A               [ 1] 4248 	dec	a
      0099D5 26 FB            [ 1] 4249 	jrne	00607$
      0099D7                       4250 00608$:
      0099D7 84               [ 1] 4251 	pop	a
      0099D8 A4 01            [ 1] 4252 	and	a, #0x01
      0099DA 6B 11            [ 1] 4253 	ld	(0x11, sp), a
      0099DC 93               [ 1] 4254 	ldw	x, y
      0099DD D6 01 DE         [ 1] 4255 	ld	a, (_d_bits+0, x)
      0099E0 88               [ 1] 4256 	push	a
      0099E1 7B 13            [ 1] 4257 	ld	a, (0x13, sp)
      0099E3 27 05            [ 1] 4258 	jreq	00610$
      0099E5                       4259 00609$:
      0099E5 04 01            [ 1] 4260 	srl	(1, sp)
      0099E7 4A               [ 1] 4261 	dec	a
      0099E8 26 FB            [ 1] 4262 	jrne	00609$
      0099EA                       4263 00610$:
      0099EA 84               [ 1] 4264 	pop	a
      0099EB A4 01            [ 1] 4265 	and	a, #0x01
      0099ED 11 11            [ 1] 4266 	cp	a, (0x11, sp)
      0099EF 26 05            [ 1] 4267 	jrne	00112$
      0099F1 1E 14            [ 2] 4268 	ldw	x, (0x14, sp)
      0099F3 5C               [ 1] 4269 	incw	x
      0099F4 1F 14            [ 2] 4270 	ldw	(0x14, sp), x
      0099F6                       4271 00112$:
                                   4272 ;	decoder.c: 812: for (t = 32; t + lag < (uint16_t)(NB - 32); t++) {
      0099F6 1E 18            [ 2] 4273 	ldw	x, (0x18, sp)
      0099F8 5C               [ 1] 4274 	incw	x
      0099F9 1F 18            [ 2] 4275 	ldw	(0x18, sp), x
      0099FB CC 99 3F         [ 2] 4276 	jp	00173$
      0099FE                       4277 00113$:
                                   4278 ;	decoder.c: 820: lag_ok[li] = (n_pair >= KNIFE_PAIR_MIN &&
      0099FE 5F               [ 1] 4279 	clrw	x
      0099FF 7B 13            [ 1] 4280 	ld	a, (0x13, sp)
      009A01 97               [ 1] 4281 	ld	xl, a
      009A02 89               [ 2] 4282 	pushw	x
      009A03 96               [ 1] 4283 	ldw	x, sp
      009A04 1C 00 03         [ 2] 4284 	addw	x, #3
      009A07 72 FB 01         [ 2] 4285 	addw	x, (1, sp)
      009A0A 1F 1A            [ 2] 4286 	ldw	(0x1a, sp), x
      009A0C 85               [ 2] 4287 	popw	x
      009A0D 1E 16            [ 2] 4288 	ldw	x, (0x16, sp)
      009A0F A3 00 28         [ 2] 4289 	cpw	x, #0x0028
      009A12 25 2C            [ 1] 4290 	jrc	00185$
                                   4291 ;	decoder.c: 821: (uint32_t)agree * 100 >=
      009A14 1E 14            [ 2] 4292 	ldw	x, (0x14, sp)
      009A16 89               [ 2] 4293 	pushw	x
      009A17 AE 00 64         [ 2] 4294 	ldw	x, #0x0064
                                   4295 ;	decoder.c: 822: (uint32_t)KNIFE_AGREE_PCT * n_pair);
      009A1A CD 9E 2B         [ 4] 4296 	call	___muluint2ulong
      009A1D 5B 02            [ 2] 4297 	addw	sp, #2
      009A1F 1F 11            [ 2] 4298 	ldw	(0x11, sp), x
      009A21 17 0F            [ 2] 4299 	ldw	(0x0f, sp), y
      009A23 1E 16            [ 2] 4300 	ldw	x, (0x16, sp)
      009A25 89               [ 2] 4301 	pushw	x
      009A26 AE 00 63         [ 2] 4302 	ldw	x, #0x0063
      009A29 CD 9E 2B         [ 4] 4303 	call	___muluint2ulong
      009A2C 5B 02            [ 2] 4304 	addw	sp, #2
      009A2E 1F 16            [ 2] 4305 	ldw	(0x16, sp), x
      009A30 17 14            [ 2] 4306 	ldw	(0x14, sp), y
      009A32 1E 11            [ 2] 4307 	ldw	x, (0x11, sp)
      009A34 13 16            [ 2] 4308 	cpw	x, (0x16, sp)
      009A36 7B 10            [ 1] 4309 	ld	a, (0x10, sp)
      009A38 12 15            [ 1] 4310 	sbc	a, (0x15, sp)
      009A3A 7B 0F            [ 1] 4311 	ld	a, (0x0f, sp)
      009A3C 12 14            [ 1] 4312 	sbc	a, (0x14, sp)
      009A3E 24 02            [ 1] 4313 	jrnc	00186$
      009A40                       4314 00185$:
      009A40 4F               [ 1] 4315 	clr	a
      009A41 C5                    4316 	.byte 0xc5
      009A42                       4317 00186$:
      009A42 A6 01            [ 1] 4318 	ld	a, #0x01
      009A44                       4319 00187$:
      009A44 1E 18            [ 2] 4320 	ldw	x, (0x18, sp)
      009A46 F7               [ 1] 4321 	ld	(x), a
                                   4322 ;	decoder.c: 809: for (li = 0; li < 2; li++) {
      009A47 0C 13            [ 1] 4323 	inc	(0x13, sp)
      009A49 7B 13            [ 1] 4324 	ld	a, (0x13, sp)
      009A4B A1 02            [ 1] 4325 	cp	a, #0x02
      009A4D 24 03            [ 1] 4326 	jrnc	00618$
      009A4F CC 99 20         [ 2] 4327 	jp	00174$
      009A52                       4328 00618$:
                                   4329 ;	decoder.c: 824: if (!lag_ok[0] && !lag_ok[1]) return;
      009A52 7B 01            [ 1] 4330 	ld	a, (0x01, sp)
      009A54 26 09            [ 1] 4331 	jrne	00271$
      009A56 7B 02            [ 1] 4332 	ld	a, (0x02, sp)
      009A58 6B 19            [ 1] 4333 	ld	(0x19, sp), a
      009A5A 26 03            [ 1] 4334 	jrne	00271$
      009A5C CC 9D 23         [ 2] 4335 	jp	00181$
                                   4336 ;	decoder.c: 826: for (t = 32; t < (uint16_t)(NB - 32); t++) {
      009A5F                       4337 00271$:
      009A5F AE 00 20         [ 2] 4338 	ldw	x, #0x0020
      009A62 1F 16            [ 2] 4339 	ldw	(0x16, sp), x
      009A64                       4340 00177$:
                                   4341 ;	decoder.c: 827: uint8_t nv = 0, val = 0, mixed = 0;
      009A64 0F 03            [ 1] 4342 	clr	(0x03, sp)
      009A66 0F 04            [ 1] 4343 	clr	(0x04, sp)
                                   4344 ;	decoder.c: 830: if (!BGET(d_tied, t)) continue;
      009A68 1E 16            [ 2] 4345 	ldw	x, (0x16, sp)
      009A6A 54               [ 2] 4346 	srlw	x
      009A6B 54               [ 2] 4347 	srlw	x
      009A6C 54               [ 2] 4348 	srlw	x
      009A6D 1F 05            [ 2] 4349 	ldw	(0x05, sp), x
      009A6F 1C 02 4E         [ 2] 4350 	addw	x, #(_d_tied+0)
      009A72 F6               [ 1] 4351 	ld	a, (x)
      009A73 97               [ 1] 4352 	ld	xl, a
      009A74 7B 17            [ 1] 4353 	ld	a, (0x17, sp)
      009A76 A4 07            [ 1] 4354 	and	a, #0x07
      009A78 6B 07            [ 1] 4355 	ld	(0x07, sp), a
      009A7A 27 06            [ 1] 4356 	jreq	00622$
      009A7C                       4357 00621$:
      009A7C 41               [ 1] 4358 	exg	a, xl
      009A7D 44               [ 1] 4359 	srl	a
      009A7E 41               [ 1] 4360 	exg	a, xl
      009A7F 4A               [ 1] 4361 	dec	a
      009A80 26 FA            [ 1] 4362 	jrne	00621$
      009A82                       4363 00622$:
      009A82 54               [ 2] 4364 	srlw	x
      009A83 25 03            [ 1] 4365 	jrc	00623$
      009A85 CC 9B C1         [ 2] 4366 	jp	00143$
      009A88                       4367 00623$:
                                   4368 ;	decoder.c: 831: for (j = 0; j < 4; j++) {
      009A88 0F 18            [ 1] 4369 	clr	(0x18, sp)
      009A8A 0F 19            [ 1] 4370 	clr	(0x19, sp)
      009A8C                       4371 00176$:
                                   4372 ;	decoder.c: 832: int16_t dt = DTS[j];
      009A8C 7B 19            [ 1] 4373 	ld	a, (0x19, sp)
      009A8E 97               [ 1] 4374 	ld	xl, a
      009A8F 49               [ 1] 4375 	rlc	a
      009A90 4F               [ 1] 4376 	clr	a
      009A91 A2 00            [ 1] 4377 	sbc	a, #0x00
      009A93 95               [ 1] 4378 	ld	xh, a
      009A94 58               [ 2] 4379 	sllw	x
      009A95 DE 80 45         [ 2] 4380 	ldw	x, (_votes_DTS_30000_301+0, x)
      009A98 1F 08            [ 2] 4381 	ldw	(0x08, sp), x
                                   4382 ;	decoder.c: 833: int32_t s = (int32_t)t + dt;
      009A9A 16 16            [ 2] 4383 	ldw	y, (0x16, sp)
      009A9C 5F               [ 1] 4384 	clrw	x
      009A9D 1F 0A            [ 2] 4385 	ldw	(0x0a, sp), x
      009A9F 1E 08            [ 2] 4386 	ldw	x, (0x08, sp)
      009AA1 1F 10            [ 2] 4387 	ldw	(0x10, sp), x
      009AA3 5F               [ 1] 4388 	clrw	x
      009AA4 0D 10            [ 1] 4389 	tnz	(0x10, sp)
      009AA6 2A 01            [ 1] 4390 	jrpl	00624$
      009AA8 5A               [ 2] 4391 	decw	x
      009AA9                       4392 00624$:
      009AA9 72 F9 10         [ 2] 4393 	addw	y, (0x10, sp)
      009AAC 17 14            [ 2] 4394 	ldw	(0x14, sp), y
      009AAE 9F               [ 1] 4395 	ld	a, xl
      009AAF 19 0B            [ 1] 4396 	adc	a, (0x0b, sp)
      009AB1 6B 13            [ 1] 4397 	ld	(0x13, sp), a
      009AB3 9E               [ 1] 4398 	ld	a, xh
      009AB4 19 0A            [ 1] 4399 	adc	a, (0x0a, sp)
      009AB6 6B 12            [ 1] 4400 	ld	(0x12, sp), a
                                   4401 ;	decoder.c: 834: uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
      009AB8 1E 08            [ 2] 4402 	ldw	x, (0x08, sp)
      009ABA 2A 09            [ 1] 4403 	jrpl	00188$
      009ABC 7B 09            [ 1] 4404 	ld	a, (0x09, sp)
      009ABE 40               [ 1] 4405 	neg	a
      009ABF 97               [ 1] 4406 	ld	xl, a
      009AC0 4F               [ 1] 4407 	clr	a
      009AC1 12 08            [ 1] 4408 	sbc	a, (0x08, sp)
      009AC3 20 05            [ 2] 4409 	jra	00189$
      009AC5                       4410 00188$:
      009AC5 7B 09            [ 1] 4411 	ld	a, (0x09, sp)
      009AC7 97               [ 1] 4412 	ld	xl, a
      009AC8 7B 08            [ 1] 4413 	ld	a, (0x08, sp)
      009ACA                       4414 00189$:
                                   4415 ;	decoder.c: 835: if (!lag_ok[lag == 16]) continue;
      009ACA 95               [ 1] 4416 	ld	xh, a
      009ACB A3 00 10         [ 2] 4417 	cpw	x, #0x0010
      009ACE 26 03            [ 1] 4418 	jrne	00627$
      009AD0 A6 01            [ 1] 4419 	ld	a, #0x01
      009AD2 21                    4420 	.byte 0x21
      009AD3                       4421 00627$:
      009AD3 4F               [ 1] 4422 	clr	a
      009AD4                       4423 00628$:
      009AD4 96               [ 1] 4424 	ldw	x, sp
      009AD5 5C               [ 1] 4425 	incw	x
      009AD6 89               [ 2] 4426 	pushw	x
      009AD7 5F               [ 1] 4427 	clrw	x
      009AD8 97               [ 1] 4428 	ld	xl, a
      009AD9 72 FB 01         [ 2] 4429 	addw	x, (1, sp)
      009ADC 5B 02            [ 2] 4430 	addw	sp, #2
      009ADE F6               [ 1] 4431 	ld	a, (x)
      009ADF 26 03            [ 1] 4432 	jrne	00629$
      009AE1 CC 9B 6C         [ 2] 4433 	jp	00133$
      009AE4                       4434 00629$:
                                   4435 ;	decoder.c: 836: if (s < 32 || s >= NB - 32) continue;
      009AE4 1E 14            [ 2] 4436 	ldw	x, (0x14, sp)
      009AE6 A3 00 20         [ 2] 4437 	cpw	x, #0x0020
      009AE9 7B 13            [ 1] 4438 	ld	a, (0x13, sp)
      009AEB A2 00            [ 1] 4439 	sbc	a, #0x00
      009AED 7B 12            [ 1] 4440 	ld	a, (0x12, sp)
      009AEF A2 00            [ 1] 4441 	sbc	a, #0x00
      009AF1 2F 79            [ 1] 4442 	jrslt	00133$
      009AF3 1E 14            [ 2] 4443 	ldw	x, (0x14, sp)
      009AF5 A3 01 A0         [ 2] 4444 	cpw	x, #0x01a0
      009AF8 7B 13            [ 1] 4445 	ld	a, (0x13, sp)
      009AFA A2 00            [ 1] 4446 	sbc	a, #0x00
      009AFC 7B 12            [ 1] 4447 	ld	a, (0x12, sp)
      009AFE A2 00            [ 1] 4448 	sbc	a, #0x00
      009B00 2E 6A            [ 1] 4449 	jrsge	00133$
                                   4450 ;	decoder.c: 837: if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
      009B02 1E 14            [ 2] 4451 	ldw	x, (0x14, sp)
      009B04 54               [ 2] 4452 	srlw	x
      009B05 54               [ 2] 4453 	srlw	x
      009B06 54               [ 2] 4454 	srlw	x
      009B07 1F 10            [ 2] 4455 	ldw	(0x10, sp), x
      009B09 1C 02 4E         [ 2] 4456 	addw	x, #(_d_tied+0)
      009B0C F6               [ 1] 4457 	ld	a, (x)
      009B0D 97               [ 1] 4458 	ld	xl, a
      009B0E 7B 15            [ 1] 4459 	ld	a, (0x15, sp)
      009B10 A4 07            [ 1] 4460 	and	a, #0x07
      009B12 6B 15            [ 1] 4461 	ld	(0x15, sp), a
      009B14 27 06            [ 1] 4462 	jreq	00633$
      009B16                       4463 00632$:
      009B16 41               [ 1] 4464 	exg	a, xl
      009B17 44               [ 1] 4465 	srl	a
      009B18 41               [ 1] 4466 	exg	a, xl
      009B19 4A               [ 1] 4467 	dec	a
      009B1A 26 FA            [ 1] 4468 	jrne	00632$
      009B1C                       4469 00633$:
      009B1C 54               [ 2] 4470 	srlw	x
      009B1D 25 4D            [ 1] 4471 	jrc	00133$
      009B1F 1E 10            [ 2] 4472 	ldw	x, (0x10, sp)
      009B21 D6 02 16         [ 1] 4473 	ld	a, (_d_conf+0, x)
      009B24 88               [ 1] 4474 	push	a
      009B25 7B 16            [ 1] 4475 	ld	a, (0x16, sp)
      009B27 27 05            [ 1] 4476 	jreq	00636$
      009B29                       4477 00635$:
      009B29 04 01            [ 1] 4478 	srl	(1, sp)
      009B2B 4A               [ 1] 4479 	dec	a
      009B2C 26 FB            [ 1] 4480 	jrne	00635$
      009B2E                       4481 00636$:
      009B2E 84               [ 1] 4482 	pop	a
      009B2F 44               [ 1] 4483 	srl	a
      009B30 24 3A            [ 1] 4484 	jrnc	00133$
                                   4485 ;	decoder.c: 839: if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
      009B32 0D 18            [ 1] 4486 	tnz	(0x18, sp)
      009B34 26 16            [ 1] 4487 	jrne	00131$
      009B36 1E 10            [ 2] 4488 	ldw	x, (0x10, sp)
      009B38 D6 01 DE         [ 1] 4489 	ld	a, (_d_bits+0, x)
      009B3B 88               [ 1] 4490 	push	a
      009B3C 7B 16            [ 1] 4491 	ld	a, (0x16, sp)
      009B3E 27 05            [ 1] 4492 	jreq	00640$
      009B40                       4493 00639$:
      009B40 04 01            [ 1] 4494 	srl	(1, sp)
      009B42 4A               [ 1] 4495 	dec	a
      009B43 26 FB            [ 1] 4496 	jrne	00639$
      009B45                       4497 00640$:
      009B45 84               [ 1] 4498 	pop	a
      009B46 A4 01            [ 1] 4499 	and	a, #0x01
      009B48 6B 03            [ 1] 4500 	ld	(0x03, sp), a
      009B4A 20 1E            [ 2] 4501 	jra	00132$
      009B4C                       4502 00131$:
                                   4503 ;	decoder.c: 840: else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
      009B4C 1E 10            [ 2] 4504 	ldw	x, (0x10, sp)
      009B4E D6 01 DE         [ 1] 4505 	ld	a, (_d_bits+0, x)
      009B51 88               [ 1] 4506 	push	a
      009B52 7B 16            [ 1] 4507 	ld	a, (0x16, sp)
      009B54 27 05            [ 1] 4508 	jreq	00642$
      009B56                       4509 00641$:
      009B56 04 01            [ 1] 4510 	srl	(1, sp)
      009B58 4A               [ 1] 4511 	dec	a
      009B59 26 FB            [ 1] 4512 	jrne	00641$
      009B5B                       4513 00642$:
      009B5B 84               [ 1] 4514 	pop	a
      009B5C A4 01            [ 1] 4515 	and	a, #0x01
      009B5E 6B 15            [ 1] 4516 	ld	(0x15, sp), a
      009B60 7B 03            [ 1] 4517 	ld	a, (0x03, sp)
      009B62 11 15            [ 1] 4518 	cp	a, (0x15, sp)
      009B64 27 04            [ 1] 4519 	jreq	00132$
      009B66 A6 01            [ 1] 4520 	ld	a, #0x01
      009B68 6B 04            [ 1] 4521 	ld	(0x04, sp), a
      009B6A                       4522 00132$:
                                   4523 ;	decoder.c: 841: nv++;
      009B6A 0C 18            [ 1] 4524 	inc	(0x18, sp)
      009B6C                       4525 00133$:
                                   4526 ;	decoder.c: 831: for (j = 0; j < 4; j++) {
      009B6C 0C 19            [ 1] 4527 	inc	(0x19, sp)
      009B6E 7B 19            [ 1] 4528 	ld	a, (0x19, sp)
      009B70 A1 04            [ 1] 4529 	cp	a, #0x04
      009B72 2E 03            [ 1] 4530 	jrsge	00646$
      009B74 CC 9A 8C         [ 2] 4531 	jp	00176$
      009B77                       4532 00646$:
                                   4533 ;	decoder.c: 843: if (nv >= DEAD_VOTE_MIN && !mixed) {
      009B77 7B 18            [ 1] 4534 	ld	a, (0x18, sp)
      009B79 A1 03            [ 1] 4535 	cp	a, #0x03
      009B7B 25 44            [ 1] 4536 	jrc	00143$
      009B7D 0D 04            [ 1] 4537 	tnz	(0x04, sp)
      009B7F 26 40            [ 1] 4538 	jrne	00143$
                                   4539 ;	decoder.c: 844: if (val) BSET(d_bits, t); else BCLR(d_bits, t);
      009B81 A6 01            [ 1] 4540 	ld	a, #0x01
      009B83 6B 19            [ 1] 4541 	ld	(0x19, sp), a
      009B85 7B 07            [ 1] 4542 	ld	a, (0x07, sp)
      009B87 27 05            [ 1] 4543 	jreq	00650$
      009B89                       4544 00649$:
      009B89 08 19            [ 1] 4545 	sll	(0x19, sp)
      009B8B 4A               [ 1] 4546 	dec	a
      009B8C 26 FB            [ 1] 4547 	jrne	00649$
      009B8E                       4548 00650$:
      009B8E 0D 03            [ 1] 4549 	tnz	(0x03, sp)
      009B90 27 0B            [ 1] 4550 	jreq	00136$
      009B92 1E 05            [ 2] 4551 	ldw	x, (0x05, sp)
      009B94 1C 01 DE         [ 2] 4552 	addw	x, #(_d_bits+0)
      009B97 F6               [ 1] 4553 	ld	a, (x)
      009B98 1A 19            [ 1] 4554 	or	a, (0x19, sp)
      009B9A F7               [ 1] 4555 	ld	(x), a
      009B9B 20 0E            [ 2] 4556 	jra	00137$
      009B9D                       4557 00136$:
      009B9D 1E 05            [ 2] 4558 	ldw	x, (0x05, sp)
      009B9F 1C 01 DE         [ 2] 4559 	addw	x, #(_d_bits+0)
      009BA2 F6               [ 1] 4560 	ld	a, (x)
      009BA3 6B 18            [ 1] 4561 	ld	(0x18, sp), a
      009BA5 7B 19            [ 1] 4562 	ld	a, (0x19, sp)
      009BA7 43               [ 1] 4563 	cpl	a
      009BA8 14 18            [ 1] 4564 	and	a, (0x18, sp)
      009BAA F7               [ 1] 4565 	ld	(x), a
      009BAB                       4566 00137$:
                                   4567 ;	decoder.c: 845: if (d_nres < RESOLVED_MAX) d_resolved[d_nres++] = t;
      009BAB C6 02 E7         [ 1] 4568 	ld	a, _d_nres+0
      009BAE A1 10            [ 1] 4569 	cp	a, #0x10
      009BB0 24 0F            [ 1] 4570 	jrnc	00143$
      009BB2 C6 02 E7         [ 1] 4571 	ld	a, _d_nres+0
      009BB5 72 5C 02 E7      [ 1] 4572 	inc	_d_nres+0
      009BB9 5F               [ 1] 4573 	clrw	x
      009BBA 97               [ 1] 4574 	ld	xl, a
      009BBB 58               [ 2] 4575 	sllw	x
      009BBC 16 16            [ 2] 4576 	ldw	y, (0x16, sp)
      009BBE DF 02 C7         [ 2] 4577 	ldw	((_d_resolved+0), x), y
      009BC1                       4578 00143$:
                                   4579 ;	decoder.c: 826: for (t = 32; t < (uint16_t)(NB - 32); t++) {
      009BC1 1E 16            [ 2] 4580 	ldw	x, (0x16, sp)
      009BC3 5C               [ 1] 4581 	incw	x
      009BC4 1F 16            [ 2] 4582 	ldw	(0x16, sp), x
      009BC6 A3 01 A0         [ 2] 4583 	cpw	x, #0x01a0
      009BC9 24 03            [ 1] 4584 	jrnc	00654$
      009BCB CC 9A 64         [ 2] 4585 	jp	00177$
      009BCE                       4586 00654$:
                                   4587 ;	decoder.c: 851: for (i = 0; i < d_nknife; i++) {
      009BCE 0F 17            [ 1] 4588 	clr	(0x17, sp)
      009BD0                       4589 00180$:
      009BD0 7B 17            [ 1] 4590 	ld	a, (0x17, sp)
      009BD2 C1 02 C6         [ 1] 4591 	cp	a, _d_nknife+0
      009BD5 25 03            [ 1] 4592 	jrc	00655$
      009BD7 CC 9D 23         [ 2] 4593 	jp	00181$
      009BDA                       4594 00655$:
                                   4595 ;	decoder.c: 852: uint16_t tk = d_knife[i];
      009BDA 7B 17            [ 1] 4596 	ld	a, (0x17, sp)
      009BDC 5F               [ 1] 4597 	clrw	x
      009BDD 97               [ 1] 4598 	ld	xl, a
      009BDE 58               [ 2] 4599 	sllw	x
      009BDF DE 02 86         [ 2] 4600 	ldw	x, (_d_knife+0, x)
      009BE2 1F 08            [ 2] 4601 	ldw	(0x08, sp), x
                                   4602 ;	decoder.c: 853: uint8_t nv = 0, val = 0, mixed = 0;
      009BE4 0F 0A            [ 1] 4603 	clr	(0x0a, sp)
      009BE6 0F 0B            [ 1] 4604 	clr	(0x0b, sp)
                                   4605 ;	decoder.c: 856: if (is_resolved(tk)) continue;
      009BE8 1E 08            [ 2] 4606 	ldw	x, (0x08, sp)
      009BEA CD 98 FB         [ 4] 4607 	call	_is_resolved
      009BED 4D               [ 1] 4608 	tnz	a
      009BEE 27 03            [ 1] 4609 	jreq	00656$
      009BF0 CC 9D 1E         [ 2] 4610 	jp	00170$
      009BF3                       4611 00656$:
                                   4612 ;	decoder.c: 857: for (j = 0; j < 4; j++) {
      009BF3 0F 18            [ 1] 4613 	clr	(0x18, sp)
      009BF5 0F 19            [ 1] 4614 	clr	(0x19, sp)
      009BF7                       4615 00178$:
                                   4616 ;	decoder.c: 858: int16_t dt = DTS[j];
      009BF7 7B 19            [ 1] 4617 	ld	a, (0x19, sp)
      009BF9 97               [ 1] 4618 	ld	xl, a
      009BFA 49               [ 1] 4619 	rlc	a
      009BFB 4F               [ 1] 4620 	clr	a
      009BFC A2 00            [ 1] 4621 	sbc	a, #0x00
      009BFE 95               [ 1] 4622 	ld	xh, a
      009BFF 58               [ 2] 4623 	sllw	x
      009C00 1C 80 4D         [ 2] 4624 	addw	x, #(_votes_DTS_40000_316+0)
      009C03 FE               [ 2] 4625 	ldw	x, (x)
      009C04 1F 0C            [ 2] 4626 	ldw	(0x0c, sp), x
                                   4627 ;	decoder.c: 859: int32_t s = (int32_t)tk + dt;
      009C06 16 08            [ 2] 4628 	ldw	y, (0x08, sp)
      009C08 0F 14            [ 1] 4629 	clr	(0x14, sp)
      009C0A 1E 0C            [ 2] 4630 	ldw	x, (0x0c, sp)
      009C0C 9E               [ 1] 4631 	ld	a, xh
      009C0D 49               [ 1] 4632 	rlc	a
      009C0E 4F               [ 1] 4633 	clr	a
      009C0F A2 00            [ 1] 4634 	sbc	a, #0x00
      009C11 6B 0E            [ 1] 4635 	ld	(0x0e, sp), a
      009C13 17 12            [ 2] 4636 	ldw	(0x12, sp), y
      009C15 4F               [ 1] 4637 	clr	a
      009C16 72 FB 12         [ 2] 4638 	addw	x, (0x12, sp)
      009C19 1F 15            [ 2] 4639 	ldw	(0x15, sp), x
      009C1B 19 0E            [ 1] 4640 	adc	a, (0x0e, sp)
      009C1D 6B 14            [ 1] 4641 	ld	(0x14, sp), a
                                   4642 ;	decoder.c: 860: uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
      009C1F 1E 0C            [ 2] 4643 	ldw	x, (0x0c, sp)
      009C21 2A 0B            [ 1] 4644 	jrpl	00190$
      009C23 7B 0D            [ 1] 4645 	ld	a, (0x0d, sp)
      009C25 40               [ 1] 4646 	neg	a
      009C26 88               [ 1] 4647 	push	a
      009C27 4F               [ 1] 4648 	clr	a
      009C28 12 0D            [ 1] 4649 	sbc	a, (0x0d, sp)
      009C2A 95               [ 1] 4650 	ld	xh, a
      009C2B 84               [ 1] 4651 	pop	a
      009C2C 20 06            [ 2] 4652 	jra	00191$
      009C2E                       4653 00190$:
      009C2E 7B 0D            [ 1] 4654 	ld	a, (0x0d, sp)
      009C30 02               [ 1] 4655 	rlwa	x
      009C31 7B 0C            [ 1] 4656 	ld	a, (0x0c, sp)
      009C33 01               [ 1] 4657 	rrwa	x
      009C34                       4658 00191$:
                                   4659 ;	decoder.c: 861: if (!lag_ok[lag == 16]) continue;
      009C34 97               [ 1] 4660 	ld	xl, a
      009C35 A3 00 10         [ 2] 4661 	cpw	x, #0x0010
      009C38 26 03            [ 1] 4662 	jrne	00659$
      009C3A A6 01            [ 1] 4663 	ld	a, #0x01
      009C3C 21                    4664 	.byte 0x21
      009C3D                       4665 00659$:
      009C3D 4F               [ 1] 4666 	clr	a
      009C3E                       4667 00660$:
      009C3E 96               [ 1] 4668 	ldw	x, sp
      009C3F 5C               [ 1] 4669 	incw	x
      009C40 89               [ 2] 4670 	pushw	x
      009C41 5F               [ 1] 4671 	clrw	x
      009C42 97               [ 1] 4672 	ld	xl, a
      009C43 72 FB 01         [ 2] 4673 	addw	x, (1, sp)
      009C46 5B 02            [ 2] 4674 	addw	sp, #2
      009C48 F6               [ 1] 4675 	ld	a, (x)
      009C49 26 03            [ 1] 4676 	jrne	00661$
      009C4B CC 9C D9         [ 2] 4677 	jp	00162$
      009C4E                       4678 00661$:
                                   4679 ;	decoder.c: 862: if (s < 32 || s >= NB - 32) continue;
      009C4E 1E 15            [ 2] 4680 	ldw	x, (0x15, sp)
      009C50 A3 00 20         [ 2] 4681 	cpw	x, #0x0020
      009C53 7B 14            [ 1] 4682 	ld	a, (0x14, sp)
      009C55 A2 00            [ 1] 4683 	sbc	a, #0x00
      009C57 2E 03            [ 1] 4684 	jrsge	00662$
      009C59 CC 9C D9         [ 2] 4685 	jp	00162$
      009C5C                       4686 00662$:
      009C5C 1E 15            [ 2] 4687 	ldw	x, (0x15, sp)
      009C5E A3 01 A0         [ 2] 4688 	cpw	x, #0x01a0
      009C61 7B 14            [ 1] 4689 	ld	a, (0x14, sp)
      009C63 A2 00            [ 1] 4690 	sbc	a, #0x00
      009C65 2E 72            [ 1] 4691 	jrsge	00162$
                                   4692 ;	decoder.c: 863: if (is_knife((uint16_t)s)) continue;
      009C67 1E 15            [ 2] 4693 	ldw	x, (0x15, sp)
      009C69 89               [ 2] 4694 	pushw	x
      009C6A CD 98 DE         [ 4] 4695 	call	_is_knife
      009C6D 85               [ 2] 4696 	popw	x
      009C6E 4D               [ 1] 4697 	tnz	a
      009C6F 26 68            [ 1] 4698 	jrne	00162$
                                   4699 ;	decoder.c: 864: if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
      009C71 54               [ 2] 4700 	srlw	x
      009C72 54               [ 2] 4701 	srlw	x
      009C73 54               [ 2] 4702 	srlw	x
      009C74 1F 12            [ 2] 4703 	ldw	(0x12, sp), x
      009C76 1C 02 4E         [ 2] 4704 	addw	x, #(_d_tied+0)
      009C79 F6               [ 1] 4705 	ld	a, (x)
      009C7A 97               [ 1] 4706 	ld	xl, a
      009C7B 7B 16            [ 1] 4707 	ld	a, (0x16, sp)
      009C7D A4 07            [ 1] 4708 	and	a, #0x07
      009C7F 6B 16            [ 1] 4709 	ld	(0x16, sp), a
      009C81 27 06            [ 1] 4710 	jreq	00666$
      009C83                       4711 00665$:
      009C83 41               [ 1] 4712 	exg	a, xl
      009C84 44               [ 1] 4713 	srl	a
      009C85 41               [ 1] 4714 	exg	a, xl
      009C86 4A               [ 1] 4715 	dec	a
      009C87 26 FA            [ 1] 4716 	jrne	00665$
      009C89                       4717 00666$:
      009C89 54               [ 2] 4718 	srlw	x
      009C8A 25 4D            [ 1] 4719 	jrc	00162$
      009C8C 1E 12            [ 2] 4720 	ldw	x, (0x12, sp)
      009C8E D6 02 16         [ 1] 4721 	ld	a, (_d_conf+0, x)
      009C91 88               [ 1] 4722 	push	a
      009C92 7B 17            [ 1] 4723 	ld	a, (0x17, sp)
      009C94 27 05            [ 1] 4724 	jreq	00669$
      009C96                       4725 00668$:
      009C96 04 01            [ 1] 4726 	srl	(1, sp)
      009C98 4A               [ 1] 4727 	dec	a
      009C99 26 FB            [ 1] 4728 	jrne	00668$
      009C9B                       4729 00669$:
      009C9B 84               [ 1] 4730 	pop	a
      009C9C 44               [ 1] 4731 	srl	a
      009C9D 24 3A            [ 1] 4732 	jrnc	00162$
                                   4733 ;	decoder.c: 866: if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
      009C9F 0D 18            [ 1] 4734 	tnz	(0x18, sp)
      009CA1 26 16            [ 1] 4735 	jrne	00160$
      009CA3 1E 12            [ 2] 4736 	ldw	x, (0x12, sp)
      009CA5 D6 01 DE         [ 1] 4737 	ld	a, (_d_bits+0, x)
      009CA8 88               [ 1] 4738 	push	a
      009CA9 7B 17            [ 1] 4739 	ld	a, (0x17, sp)
      009CAB 27 05            [ 1] 4740 	jreq	00673$
      009CAD                       4741 00672$:
      009CAD 04 01            [ 1] 4742 	srl	(1, sp)
      009CAF 4A               [ 1] 4743 	dec	a
      009CB0 26 FB            [ 1] 4744 	jrne	00672$
      009CB2                       4745 00673$:
      009CB2 84               [ 1] 4746 	pop	a
      009CB3 A4 01            [ 1] 4747 	and	a, #0x01
      009CB5 6B 0A            [ 1] 4748 	ld	(0x0a, sp), a
      009CB7 20 1E            [ 2] 4749 	jra	00161$
      009CB9                       4750 00160$:
                                   4751 ;	decoder.c: 867: else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
      009CB9 1E 12            [ 2] 4752 	ldw	x, (0x12, sp)
      009CBB D6 01 DE         [ 1] 4753 	ld	a, (_d_bits+0, x)
      009CBE 88               [ 1] 4754 	push	a
      009CBF 7B 17            [ 1] 4755 	ld	a, (0x17, sp)
      009CC1 27 05            [ 1] 4756 	jreq	00675$
      009CC3                       4757 00674$:
      009CC3 04 01            [ 1] 4758 	srl	(1, sp)
      009CC5 4A               [ 1] 4759 	dec	a
      009CC6 26 FB            [ 1] 4760 	jrne	00674$
      009CC8                       4761 00675$:
      009CC8 84               [ 1] 4762 	pop	a
      009CC9 A4 01            [ 1] 4763 	and	a, #0x01
      009CCB 6B 16            [ 1] 4764 	ld	(0x16, sp), a
      009CCD 7B 0A            [ 1] 4765 	ld	a, (0x0a, sp)
      009CCF 11 16            [ 1] 4766 	cp	a, (0x16, sp)
      009CD1 27 04            [ 1] 4767 	jreq	00161$
      009CD3 A6 01            [ 1] 4768 	ld	a, #0x01
      009CD5 6B 0B            [ 1] 4769 	ld	(0x0b, sp), a
      009CD7                       4770 00161$:
                                   4771 ;	decoder.c: 868: nv++;
      009CD7 0C 18            [ 1] 4772 	inc	(0x18, sp)
      009CD9                       4773 00162$:
                                   4774 ;	decoder.c: 857: for (j = 0; j < 4; j++) {
      009CD9 0C 19            [ 1] 4775 	inc	(0x19, sp)
      009CDB 7B 19            [ 1] 4776 	ld	a, (0x19, sp)
      009CDD A1 04            [ 1] 4777 	cp	a, #0x04
      009CDF 2E 03            [ 1] 4778 	jrsge	00679$
      009CE1 CC 9B F7         [ 2] 4779 	jp	00178$
      009CE4                       4780 00679$:
                                   4781 ;	decoder.c: 870: if (nv >= 1 && !mixed) {
      009CE4 7B 18            [ 1] 4782 	ld	a, (0x18, sp)
      009CE6 A1 01            [ 1] 4783 	cp	a, #0x01
      009CE8 25 34            [ 1] 4784 	jrc	00170$
      009CEA 0D 0B            [ 1] 4785 	tnz	(0x0b, sp)
      009CEC 26 30            [ 1] 4786 	jrne	00170$
                                   4787 ;	decoder.c: 871: if (val) BSET(d_bits, tk); else BCLR(d_bits, tk);
      009CEE 1E 08            [ 2] 4788 	ldw	x, (0x08, sp)
      009CF0 54               [ 2] 4789 	srlw	x
      009CF1 54               [ 2] 4790 	srlw	x
      009CF2 54               [ 2] 4791 	srlw	x
      009CF3 7B 09            [ 1] 4792 	ld	a, (0x09, sp)
      009CF5 A4 07            [ 1] 4793 	and	a, #0x07
      009CF7 88               [ 1] 4794 	push	a
      009CF8 A6 01            [ 1] 4795 	ld	a, #0x01
      009CFA 6B 1A            [ 1] 4796 	ld	(0x1a, sp), a
      009CFC 84               [ 1] 4797 	pop	a
      009CFD 4D               [ 1] 4798 	tnz	a
      009CFE 27 05            [ 1] 4799 	jreq	00683$
      009D00                       4800 00682$:
      009D00 08 19            [ 1] 4801 	sll	(0x19, sp)
      009D02 4A               [ 1] 4802 	dec	a
      009D03 26 FB            [ 1] 4803 	jrne	00682$
      009D05                       4804 00683$:
      009D05 0D 0A            [ 1] 4805 	tnz	(0x0a, sp)
      009D07 27 09            [ 1] 4806 	jreq	00165$
      009D09 1C 01 DE         [ 2] 4807 	addw	x, #(_d_bits+0)
      009D0C F6               [ 1] 4808 	ld	a, (x)
      009D0D 1A 19            [ 1] 4809 	or	a, (0x19, sp)
      009D0F F7               [ 1] 4810 	ld	(x), a
      009D10 20 0C            [ 2] 4811 	jra	00170$
      009D12                       4812 00165$:
      009D12 1C 01 DE         [ 2] 4813 	addw	x, #(_d_bits+0)
      009D15 F6               [ 1] 4814 	ld	a, (x)
      009D16 6B 18            [ 1] 4815 	ld	(0x18, sp), a
      009D18 7B 19            [ 1] 4816 	ld	a, (0x19, sp)
      009D1A 43               [ 1] 4817 	cpl	a
      009D1B 14 18            [ 1] 4818 	and	a, (0x18, sp)
      009D1D F7               [ 1] 4819 	ld	(x), a
      009D1E                       4820 00170$:
                                   4821 ;	decoder.c: 851: for (i = 0; i < d_nknife; i++) {
      009D1E 0C 17            [ 1] 4822 	inc	(0x17, sp)
      009D20 CC 9B D0         [ 2] 4823 	jp	00180$
      009D23                       4824 00181$:
                                   4825 ;	decoder.c: 875: }
      009D23 5B 19            [ 2] 4826 	addw	sp, #25
      009D25 81               [ 4] 4827 	ret
                                   4828 ;	decoder.c: 882: uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out)
                                   4829 ;	-----------------------------------------
                                   4830 ;	 function ws_decode
                                   4831 ;	-----------------------------------------
      009D26                       4832 _ws_decode:
      009D26 52 06            [ 2] 4833 	sub	sp, #6
      009D28 1F 04            [ 2] 4834 	ldw	(0x04, sp), x
                                   4835 ;	decoder.c: 886: if (!seed(cap, ncap)) return 0;
      009D2A 1E 09            [ 2] 4836 	ldw	x, (0x09, sp)
      009D2C 89               [ 2] 4837 	pushw	x
      009D2D 1E 06            [ 2] 4838 	ldw	x, (0x06, sp)
      009D2F CD 85 AA         [ 4] 4839 	call	_seed
      009D32 4D               [ 1] 4840 	tnz	a
      009D33 26 04            [ 1] 4841 	jrne	00102$
      009D35 4F               [ 1] 4842 	clr	a
      009D36 CC 9E 26         [ 2] 4843 	jp	00130$
      009D39                       4844 00102$:
                                   4845 ;	decoder.c: 887: if (g_phases < 2) return 0;
      009D39 C6 03 0E         [ 1] 4846 	ld	a, _g_phases+0
      009D3C A1 02            [ 1] 4847 	cp	a, #0x02
      009D3E 24 04            [ 1] 4848 	jrnc	00151$
      009D40 4F               [ 1] 4849 	clr	a
      009D41 CC 9E 26         [ 2] 4850 	jp	00130$
                                   4851 ;	decoder.c: 888: for (r = 0; r < 2; r++) refine(cap, ncap);
      009D44                       4852 00151$:
      009D44 4F               [ 1] 4853 	clr	a
      009D45                       4854 00122$:
      009D45 88               [ 1] 4855 	push	a
      009D46 1E 0A            [ 2] 4856 	ldw	x, (0x0a, sp)
      009D48 89               [ 2] 4857 	pushw	x
      009D49 1E 07            [ 2] 4858 	ldw	x, (0x07, sp)
      009D4B CD 86 69         [ 4] 4859 	call	_refine
      009D4E 84               [ 1] 4860 	pop	a
      009D4F 4C               [ 1] 4861 	inc	a
      009D50 A1 02            [ 1] 4862 	cp	a, #0x02
      009D52 25 F1            [ 1] 4863 	jrc	00122$
                                   4864 ;	decoder.c: 889: if (g_phases < 3) return 0;
      009D54 C6 03 0E         [ 1] 4865 	ld	a, _g_phases+0
      009D57 A1 03            [ 1] 4866 	cp	a, #0x03
      009D59 24 04            [ 1] 4867 	jrnc	00107$
      009D5B 4F               [ 1] 4868 	clr	a
      009D5C CC 9E 26         [ 2] 4869 	jp	00130$
      009D5F                       4870 00107$:
                                   4871 ;	decoder.c: 890: calibrate(cap, ncap);
      009D5F 1E 09            [ 2] 4872 	ldw	x, (0x09, sp)
      009D61 89               [ 2] 4873 	pushw	x
      009D62 1E 06            [ 2] 4874 	ldw	x, (0x06, sp)
      009D64 CD 91 37         [ 4] 4875 	call	_calibrate
                                   4876 ;	decoder.c: 891: if (g_phases < 4) return 0;
      009D67 C6 03 0E         [ 1] 4877 	ld	a, _g_phases+0
      009D6A A1 04            [ 1] 4878 	cp	a, #0x04
      009D6C 24 04            [ 1] 4879 	jrnc	00109$
      009D6E 4F               [ 1] 4880 	clr	a
      009D6F CC 9E 26         [ 2] 4881 	jp	00130$
      009D72                       4882 00109$:
                                   4883 ;	decoder.c: 892: decide_pass(cap, ncap);
      009D72 1E 09            [ 2] 4884 	ldw	x, (0x09, sp)
      009D74 89               [ 2] 4885 	pushw	x
      009D75 1E 06            [ 2] 4886 	ldw	x, (0x06, sp)
      009D77 CD 95 F0         [ 4] 4887 	call	_decide_pass
                                   4888 ;	decoder.c: 893: if (g_phases < 5) return 0;
      009D7A C6 03 0E         [ 1] 4889 	ld	a, _g_phases+0
      009D7D A1 05            [ 1] 4890 	cp	a, #0x05
      009D7F 24 04            [ 1] 4891 	jrnc	00111$
      009D81 4F               [ 1] 4892 	clr	a
      009D82 CC 9E 26         [ 2] 4893 	jp	00130$
      009D85                       4894 00111$:
                                   4895 ;	decoder.c: 894: votes();
      009D85 CD 99 18         [ 4] 4896 	call	_votes
                                   4897 ;	decoder.c: 895: for (t = 0; t < NB; t++) {
      009D88 0F 06            [ 1] 4898 	clr	(0x06, sp)
      009D8A 90 5F            [ 1] 4899 	clrw	y
      009D8C                       4900 00124$:
                                   4901 ;	decoder.c: 896: int8_t kb = known_bit(t);
      009D8C 90 89            [ 2] 4902 	pushw	y
      009D8E 93               [ 1] 4903 	ldw	x, y
      009D8F CD 81 93         [ 4] 4904 	call	_known_bit
      009D92 6B 05            [ 1] 4905 	ld	(0x05, sp), a
      009D94 90 85            [ 2] 4906 	popw	y
                                   4907 ;	decoder.c: 897: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
      009D96 0D 03            [ 1] 4908 	tnz	(0x03, sp)
      009D98 2B 1E            [ 1] 4909 	jrmi	00125$
      009D9A 93               [ 1] 4910 	ldw	x, y
      009D9B 54               [ 2] 4911 	srlw	x
      009D9C 54               [ 2] 4912 	srlw	x
      009D9D 54               [ 2] 4913 	srlw	x
      009D9E 1C 01 DE         [ 2] 4914 	addw	x, #(_d_bits+0)
      009DA1 F6               [ 1] 4915 	ld	a, (x)
      009DA2 97               [ 1] 4916 	ld	xl, a
      009DA3 90 9F            [ 1] 4917 	ld	a, yl
      009DA5 A4 07            [ 1] 4918 	and	a, #0x07
      009DA7 27 06            [ 1] 4919 	jreq	00280$
      009DA9                       4920 00279$:
      009DA9 41               [ 1] 4921 	exg	a, xl
      009DAA 44               [ 1] 4922 	srl	a
      009DAB 41               [ 1] 4923 	exg	a, xl
      009DAC 4A               [ 1] 4924 	dec	a
      009DAD 26 FA            [ 1] 4925 	jrne	00279$
      009DAF                       4926 00280$:
      009DAF 9F               [ 1] 4927 	ld	a, xl
      009DB0 A4 01            [ 1] 4928 	and	a, #0x01
      009DB2 11 03            [ 1] 4929 	cp	a, (0x03, sp)
      009DB4 27 02            [ 1] 4930 	jreq	00125$
      009DB6 0C 06            [ 1] 4931 	inc	(0x06, sp)
      009DB8                       4932 00125$:
                                   4933 ;	decoder.c: 895: for (t = 0; t < NB; t++) {
      009DB8 90 5C            [ 1] 4934 	incw	y
      009DBA 93               [ 1] 4935 	ldw	x, y
      009DBB A3 01 C0         [ 2] 4936 	cpw	x, #0x01c0
      009DBE 25 CC            [ 1] 4937 	jrc	00124$
                                   4938 ;	decoder.c: 899: if (viol > 0 || d_infeas > GATE_INFEAS || d_laberr > GATE_LABERR)
      009DC0 0D 06            [ 1] 4939 	tnz	(0x06, sp)
      009DC2 26 0E            [ 1] 4940 	jrne	00116$
      009DC4 C6 02 E8         [ 1] 4941 	ld	a, _d_infeas+0
      009DC7 A1 04            [ 1] 4942 	cp	a, #0x04
      009DC9 22 07            [ 1] 4943 	jrugt	00116$
      009DCB C6 02 E9         [ 1] 4944 	ld	a, _d_laberr+0
      009DCE A1 06            [ 1] 4945 	cp	a, #0x06
      009DD0 23 03            [ 2] 4946 	jrule	00164$
      009DD2                       4947 00116$:
                                   4948 ;	decoder.c: 900: return 0;
      009DD2 4F               [ 1] 4949 	clr	a
      009DD3 20 51            [ 2] 4950 	jra	00130$
                                   4951 ;	decoder.c: 901: for (t = 0; t < NB_PAYLOAD; t++) {
      009DD5                       4952 00164$:
      009DD5 90 5F            [ 1] 4953 	clrw	y
      009DD7                       4954 00128$:
                                   4955 ;	decoder.c: 902: uint8_t b = 0, j;
      009DD7 4F               [ 1] 4956 	clr	a
                                   4957 ;	decoder.c: 903: for (j = 0; j < 8; j++)
      009DD8 0F 06            [ 1] 4958 	clr	(0x06, sp)
      009DDA                       4959 00126$:
                                   4960 ;	decoder.c: 904: b = (uint8_t)((b << 1) | BGET(d_bits, 32 + 8 * t + j));
      009DDA 48               [ 1] 4961 	sll	a
      009DDB 6B 01            [ 1] 4962 	ld	(0x01, sp), a
      009DDD 93               [ 1] 4963 	ldw	x, y
      009DDE 58               [ 2] 4964 	sllw	x
      009DDF 58               [ 2] 4965 	sllw	x
      009DE0 58               [ 2] 4966 	sllw	x
      009DE1 1C 00 20         [ 2] 4967 	addw	x, #0x0020
      009DE4 7B 06            [ 1] 4968 	ld	a, (0x06, sp)
      009DE6 6B 03            [ 1] 4969 	ld	(0x03, sp), a
      009DE8 0F 02            [ 1] 4970 	clr	(0x02, sp)
      009DEA 72 FB 02         [ 2] 4971 	addw	x, (0x02, sp)
      009DED 54               [ 2] 4972 	srlw	x
      009DEE 54               [ 2] 4973 	srlw	x
      009DEF 54               [ 2] 4974 	srlw	x
      009DF0 1C 01 DE         [ 2] 4975 	addw	x, #(_d_bits+0)
      009DF3 F6               [ 1] 4976 	ld	a, (x)
      009DF4 97               [ 1] 4977 	ld	xl, a
      009DF5 90 9F            [ 1] 4978 	ld	a, yl
      009DF7 48               [ 1] 4979 	sll	a
      009DF8 48               [ 1] 4980 	sll	a
      009DF9 48               [ 1] 4981 	sll	a
      009DFA AB 20            [ 1] 4982 	add	a, #0x20
      009DFC 1B 06            [ 1] 4983 	add	a, (0x06, sp)
      009DFE A4 07            [ 1] 4984 	and	a, #0x07
      009E00 27 06            [ 1] 4985 	jreq	00289$
      009E02                       4986 00288$:
      009E02 41               [ 1] 4987 	exg	a, xl
      009E03 44               [ 1] 4988 	srl	a
      009E04 41               [ 1] 4989 	exg	a, xl
      009E05 4A               [ 1] 4990 	dec	a
      009E06 26 FA            [ 1] 4991 	jrne	00288$
      009E08                       4992 00289$:
      009E08 9F               [ 1] 4993 	ld	a, xl
      009E09 A4 01            [ 1] 4994 	and	a, #0x01
      009E0B 1A 01            [ 1] 4995 	or	a, (0x01, sp)
                                   4996 ;	decoder.c: 903: for (j = 0; j < 8; j++)
      009E0D 0C 06            [ 1] 4997 	inc	(0x06, sp)
      009E0F 88               [ 1] 4998 	push	a
      009E10 7B 07            [ 1] 4999 	ld	a, (0x07, sp)
      009E12 A1 08            [ 1] 5000 	cp	a, #0x08
      009E14 84               [ 1] 5001 	pop	a
      009E15 25 C3            [ 1] 5002 	jrc	00126$
                                   5003 ;	decoder.c: 905: out[t] = b;
      009E17 93               [ 1] 5004 	ldw	x, y
      009E18 72 FB 0B         [ 2] 5005 	addw	x, (0x0b, sp)
      009E1B F7               [ 1] 5006 	ld	(x), a
                                   5007 ;	decoder.c: 901: for (t = 0; t < NB_PAYLOAD; t++) {
      009E1C 90 5C            [ 1] 5008 	incw	y
      009E1E 93               [ 1] 5009 	ldw	x, y
      009E1F A3 00 30         [ 2] 5010 	cpw	x, #0x0030
      009E22 25 B3            [ 1] 5011 	jrc	00128$
                                   5012 ;	decoder.c: 907: return 1;
      009E24 A6 01            [ 1] 5013 	ld	a, #0x01
      009E26                       5014 00130$:
                                   5015 ;	decoder.c: 908: }
      009E26 1E 07            [ 2] 5016 	ldw	x, (7, sp)
      009E28 5B 0C            [ 2] 5017 	addw	sp, #12
      009E2A FC               [ 2] 5018 	jp	(x)
                                   5019 	.area CODE
                                   5020 	.area CONST
                                   5021 	.area CONST
      00802D                       5022 _O_CY:
      00802D 00                    5023 	.db #0x00	; 0
      00802E 04                    5024 	.db #0x04	; 4
      00802F 09                    5025 	.db #0x09	; 9
      008030 0D                    5026 	.db #0x0d	; 13
      008031 11                    5027 	.db #0x11	; 17
      008032 15                    5028 	.db #0x15	; 21
      008033 1B                    5029 	.db #0x1b	; 27
      008034 20                    5030 	.db #0x20	; 32
                                   5031 	.area CODE
                                   5032 	.area CONST
      008035                       5033 _W_CY:
      008035 00                    5034 	.db #0x00	;  0
      008036 FF                    5035 	.db #0xff	; -1
      008037 00                    5036 	.db #0x00	;  0
      008038 02                    5037 	.db #0x02	;  2
      008039 00                    5038 	.db #0x00	;  0
      00803A 00                    5039 	.db #0x00	;  0
      00803B 00                    5040 	.db #0x00	;  0
      00803C 01                    5041 	.db #0x01	;  1
                                   5042 	.area CODE
                                   5043 	.area CONST
      00803D                       5044 _HDR:
      00803D FF                    5045 	.db #0xff	; 255
      00803E 00                    5046 	.db #0x00	; 0
      00803F AA                    5047 	.db #0xaa	; 170
      008040 65                    5048 	.db #0x65	; 101	'e'
                                   5049 	.area CODE
                                   5050 	.area CONST
      008041                       5051 _TRL:
      008041 9A                    5052 	.db #0x9a	; 154
      008042 55                    5053 	.db #0x55	; 85	'U'
      008043 00                    5054 	.db #0x00	; 0
      008044 FF                    5055 	.db #0xff	; 255
                                   5056 	.area CODE
                                   5057 	.area CONST
      008045                       5058 _votes_DTS_30000_301:
      008045 FF F0                 5059 	.dw #0xfff0
      008047 FF F8                 5060 	.dw #0xfff8
      008049 00 08                 5061 	.dw #0x0008
      00804B 00 10                 5062 	.dw #0x0010
                                   5063 	.area CODE
                                   5064 	.area CONST
      00804D                       5065 _votes_DTS_40000_316:
      00804D FF F0                 5066 	.dw #0xfff0
      00804F FF F8                 5067 	.dw #0xfff8
      008051 00 08                 5068 	.dw #0x0008
      008053 00 10                 5069 	.dw #0x0010
                                   5070 	.area CODE
                                   5071 	.area INITIALIZER
      008155                       5072 __xinit__g_phases:
      008155 05                    5073 	.db #0x05	; 5
                                   5074 	.area CABS (ABS)
