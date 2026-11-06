                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module rbarf_arm
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _main
                                     11 	.globl _anim_render
                                     12 	.globl _ws2812_out_send
                                     13 	.globl _ws2812_out_init
                                     14 	.globl _millis
                                     15 	.globl _dec_eps_centi
                                     16 	.globl _ws_decode_ex
                                     17 	.globl _ws2812_in_buf
                                     18 	.globl _capture_buf
                                     19 ;--------------------------------------------------------
                                     20 ; ram data
                                     21 ;--------------------------------------------------------
                                     22 	.area DATA
      0000F0                         23 _capture_buf::
      0000F0                         24 	.ds 288
      000210                         25 _ws2812_in_buf::
      000210                         26 	.ds 48
      000240                         27 _cap_got:
      000240                         28 	.ds 1
      000241                         29 _tl:
      000241                         30 	.ds 14
      00024F                         31 _nok:
      00024F                         32 	.ds 1
      000250                         33 _last_render:
      000250                         34 	.ds 2
                                     35 ;--------------------------------------------------------
                                     36 ; ram data
                                     37 ;--------------------------------------------------------
                                     38 	.area INITIALIZED
                                     39 ;--------------------------------------------------------
                                     40 ; Stack segment in internal ram
                                     41 ;--------------------------------------------------------
                                     42 	.area SSEG
      000379                         43 __start__stack:
      000379                         44 	.ds	1
                                     45 
                                     46 ;--------------------------------------------------------
                                     47 ; absolute external ram data
                                     48 ;--------------------------------------------------------
                                     49 	.area DABS (ABS)
                                     50 
                                     51 ; default segment ordering for linker
                                     52 	.area HOME
                                     53 	.area GSINIT
                                     54 	.area GSFINAL
                                     55 	.area CONST
                                     56 	.area INITIALIZER
                                     57 	.area CODE
                                     58 
                                     59 ;--------------------------------------------------------
                                     60 ; interrupt vector
                                     61 ;--------------------------------------------------------
                                     62 	.area HOME
      008068                         63 __interrupt_vect:
      008068 82 00 80 6F             64 	int s_GSINIT ; reset
                                     65 ;--------------------------------------------------------
                                     66 ; global & static initialisations
                                     67 ;--------------------------------------------------------
                                     68 	.area HOME
                                     69 	.area GSINIT
                                     70 	.area GSFINAL
                                     71 	.area GSINIT
      00806F CD 9F 2C         [ 4]   72 	call	___sdcc_external_startup
      008072 4D               [ 1]   73 	tnz	a
      008073 27 03            [ 1]   74 	jreq	__sdcc_init_data
      008075 CC 80 6C         [ 2]   75 	jp	__sdcc_program_startup
      008078                         76 __sdcc_init_data:
                                     77 ; stm8_genXINIT() start
      008078 AE 02 89         [ 2]   78 	ldw x, #l_DATA
      00807B 27 07            [ 1]   79 	jreq	00002$
      00807D                         80 00001$:
      00807D 72 4F 00 EF      [ 1]   81 	clr (s_DATA - 1, x)
      008081 5A               [ 2]   82 	decw x
      008082 26 F9            [ 1]   83 	jrne	00001$
      008084                         84 00002$:
      008084 AE 00 00         [ 2]   85 	ldw	x, #l_INITIALIZER
      008087 27 09            [ 1]   86 	jreq	00004$
      008089                         87 00003$:
      008089 D6 81 BF         [ 1]   88 	ld	a, (s_INITIALIZER - 1, x)
      00808C D7 03 78         [ 1]   89 	ld	(s_INITIALIZED - 1, x), a
      00808F 5A               [ 2]   90 	decw	x
      008090 26 F7            [ 1]   91 	jrne	00003$
      008092                         92 00004$:
                                     93 ; stm8_genXINIT() end
                                     94 	.area GSFINAL
      008092 CC 80 6C         [ 2]   95 	jp	__sdcc_program_startup
                                     96 ;--------------------------------------------------------
                                     97 ; Home
                                     98 ;--------------------------------------------------------
                                     99 	.area HOME
                                    100 	.area HOME
      00806C                        101 __sdcc_program_startup:
      00806C CC 82 53         [ 2]  102 	jp	_main
                                    103 ;	return from main will return to caller
                                    104 ;--------------------------------------------------------
                                    105 ; code
                                    106 ;--------------------------------------------------------
                                    107 	.area CODE
                                    108 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 95: static void uart_putc(char c)
                                    109 ;	-----------------------------------------
                                    110 ;	 function uart_putc
                                    111 ;	-----------------------------------------
      0081C0                        112 _uart_putc:
                                    113 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 97: while (!(UART1_SR & UART1_SR_TXE))
      0081C0                        114 00101$:
      0081C0 AE 52 30         [ 2]  115 	ldw	x, #0x5230
      0081C3 88               [ 1]  116 	push	a
      0081C4 F6               [ 1]  117 	ld	a, (x)
      0081C5 95               [ 1]  118 	ld	xh, a
      0081C6 84               [ 1]  119 	pop	a
      0081C7 5D               [ 2]  120 	tnzw	x
      0081C8 2A F6            [ 1]  121 	jrpl	00101$
                                    122 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 99: UART1_DR = (uint8_t)c;
      0081CA C7 52 31         [ 1]  123 	ld	0x5231, a
                                    124 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 100: }
      0081CD 81               [ 4]  125 	ret
                                    126 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 102: static void uart_puts(const char *s)
                                    127 ;	-----------------------------------------
                                    128 ;	 function uart_puts
                                    129 ;	-----------------------------------------
      0081CE                        130 _uart_puts:
                                    131 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 104: while (*s)
      0081CE                        132 00101$:
      0081CE F6               [ 1]  133 	ld	a, (x)
      0081CF 26 01            [ 1]  134 	jrne	00123$
      0081D1 81               [ 4]  135 	ret
      0081D2                        136 00123$:
                                    137 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 105: uart_putc(*s++);
      0081D2 5C               [ 1]  138 	incw	x
      0081D3 89               [ 2]  139 	pushw	x
      0081D4 CD 81 C0         [ 4]  140 	call	_uart_putc
      0081D7 85               [ 2]  141 	popw	x
      0081D8 20 F4            [ 2]  142 	jra	00101$
                                    143 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 106: }
      0081DA 81               [ 4]  144 	ret
                                    145 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 108: static void uart_nib(uint8_t d)
                                    146 ;	-----------------------------------------
                                    147 ;	 function uart_nib
                                    148 ;	-----------------------------------------
      0081DB                        149 _uart_nib:
                                    150 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 110: d = (uint8_t)(d + '0');
      0081DB AB 30            [ 1]  151 	add	a, #0x30
                                    152 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 111: if (d > '9')
      0081DD A1 39            [ 1]  153 	cp	a, #0x39
      0081DF 22 03            [ 1]  154 	jrugt	00113$
      0081E1 CC 81 C0         [ 2]  155 	jp	_uart_putc
      0081E4                        156 00113$:
                                    157 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 112: d = (uint8_t)(d + 7);         /* 'A' - '0' - 10 */
      0081E4 AB 07            [ 1]  158 	add	a, #0x07
                                    159 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 113: uart_putc((char)d);
                                    160 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 114: }
      0081E6 CC 81 C0         [ 2]  161 	jp	_uart_putc
                                    162 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 116: static void uart_blk(const uint8_t *p, uint16_t n)
                                    163 ;	-----------------------------------------
                                    164 ;	 function uart_blk
                                    165 ;	-----------------------------------------
      0081E9                        166 _uart_blk:
      0081E9 89               [ 2]  167 	pushw	x
                                    168 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 118: while (n--) {
      0081EA                        169 00101$:
      0081EA 16 05            [ 2]  170 	ldw	y, (0x05, sp)
      0081EC 17 01            [ 2]  171 	ldw	(0x01, sp), y
      0081EE 16 05            [ 2]  172 	ldw	y, (0x05, sp)
      0081F0 90 5A            [ 2]  173 	decw	y
      0081F2 17 05            [ 2]  174 	ldw	(0x05, sp), y
      0081F4 16 01            [ 2]  175 	ldw	y, (0x01, sp)
      0081F6 27 14            [ 1]  176 	jreq	00104$
                                    177 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 119: uart_nib((uint8_t)(*p >> 4));
      0081F8 F6               [ 1]  178 	ld	a, (x)
      0081F9 4E               [ 1]  179 	swap	a
      0081FA A4 0F            [ 1]  180 	and	a, #0x0f
      0081FC 89               [ 2]  181 	pushw	x
      0081FD CD 81 DB         [ 4]  182 	call	_uart_nib
      008200 85               [ 2]  183 	popw	x
                                    184 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 120: uart_nib((uint8_t)(*p & 0x0F));
      008201 F6               [ 1]  185 	ld	a, (x)
      008202 A4 0F            [ 1]  186 	and	a, #0x0f
      008204 89               [ 2]  187 	pushw	x
      008205 CD 81 DB         [ 4]  188 	call	_uart_nib
      008208 85               [ 2]  189 	popw	x
                                    190 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 121: p++;
      008209 5C               [ 1]  191 	incw	x
      00820A 20 DE            [ 2]  192 	jra	00101$
      00820C                        193 00104$:
                                    194 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 123: }
      00820C 1E 03            [ 2]  195 	ldw	x, (3, sp)
      00820E 5B 06            [ 2]  196 	addw	sp, #6
      008210 FC               [ 2]  197 	jp	(x)
                                    198 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 126: static void stamp(uint8_t i)
                                    199 ;	-----------------------------------------
                                    200 ;	 function stamp
                                    201 ;	-----------------------------------------
      008211                        202 _stamp:
      008211 88               [ 1]  203 	push	a
                                    204 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 128: tl[i] = TIM2_CNTRH;
      008212 5F               [ 1]  205 	clrw	x
      008213 7B 01            [ 1]  206 	ld	a, (0x01, sp)
      008215 97               [ 1]  207 	ld	xl, a
      008216 1C 02 41         [ 2]  208 	addw	x, #(_tl+0)
      008219 C6 53 0C         [ 1]  209 	ld	a, 0x530c
      00821C F7               [ 1]  210 	ld	(x), a
                                    211 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 129: tl[i + 1] = TIM2_CNTRL;
      00821D 7B 01            [ 1]  212 	ld	a, (0x01, sp)
      00821F 4C               [ 1]  213 	inc	a
      008220 97               [ 1]  214 	ld	xl, a
      008221 49               [ 1]  215 	rlc	a
      008222 4F               [ 1]  216 	clr	a
      008223 A2 00            [ 1]  217 	sbc	a, #0x00
      008225 95               [ 1]  218 	ld	xh, a
      008226 C6 53 0D         [ 1]  219 	ld	a, 0x530d
      008229 D7 02 41         [ 1]  220 	ld	((_tl+0), x), a
                                    221 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 130: }
      00822C 84               [ 1]  222 	pop	a
      00822D 81               [ 4]  223 	ret
                                    224 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 136: static void render_tick(void)
                                    225 ;	-----------------------------------------
                                    226 ;	 function render_tick
                                    227 ;	-----------------------------------------
      00822E                        228 _render_tick:
                                    229 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 138: uint16_t now = millis();
      00822E CD 9F 09         [ 4]  230 	call	_millis
                                    231 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 139: if ((uint16_t)(now - last_render) >= 10) {
      008231 90 93            [ 1]  232 	ldw	y, x
      008233 72 B2 02 50      [ 2]  233 	subw	y, _last_render+0
      008237 90 A3 00 0A      [ 2]  234 	cpw	y, #0x000a
      00823B 24 01            [ 1]  235 	jrnc	00113$
      00823D 81               [ 4]  236 	ret
      00823E                        237 00113$:
                                    238 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 140: last_render = now;
      00823E CF 02 50         [ 2]  239 	ldw	_last_render+0, x
                                    240 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 141: stamp(7);                     /* render START */
      008241 89               [ 2]  241 	pushw	x
      008242 A6 07            [ 1]  242 	ld	a, #0x07
      008244 CD 82 11         [ 4]  243 	call	_stamp
      008247 85               [ 2]  244 	popw	x
                                    245 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 142: anim_render(now);
      008248 CD 9D BF         [ 4]  246 	call	_anim_render
                                    247 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 143: ws2812_out_send();            /* ~545 us, tick-masked inside */
      00824B CD 9E A6         [ 4]  248 	call	_ws2812_out_send
                                    249 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 144: stamp(9);                     /* render END */
      00824E A6 09            [ 1]  250 	ld	a, #0x09
                                    251 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 146: }
      008250 CC 82 11         [ 2]  252 	jp	_stamp
                                    253 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 148: void main(void)
                                    254 ;	-----------------------------------------
                                    255 ;	 function main
                                    256 ;	-----------------------------------------
      008253                        257 _main:
      008253 89               [ 2]  258 	pushw	x
                                    259 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 153: CLK_CKDIVR = 0x00;
      008254 35 00 50 C6      [ 1]  260 	mov	0x50c6+0, #0x00
                                    261 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 154: CLK_HSITRIMR = 0x00;              /* factory == operating trim (code 0) */
      008258 35 00 50 CC      [ 1]  262 	mov	0x50cc+0, #0x00
                                    263 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 156: TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
      00825C 35 00 53 40      [ 1]  264 	mov	0x5340+0, #0x00
                                    265 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 157: TIM4_PSCR = 0x07;
      008260 35 07 53 47      [ 1]  266 	mov	0x5347+0, #0x07
                                    267 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 158: TIM4_ARR  = 124;
      008264 35 7C 53 48      [ 1]  268 	mov	0x5348+0, #0x7c
                                    269 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 159: TIM4_SR   = 0x00;
      008268 35 00 53 44      [ 1]  270 	mov	0x5344+0, #0x00
                                    271 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 160: TIM4_IER  = 0x01;
      00826C 35 01 53 43      [ 1]  272 	mov	0x5343+0, #0x01
                                    273 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 161: TIM4_CR1  = 0x01;
      008270 35 01 53 40      [ 1]  274 	mov	0x5340+0, #0x01
                                    275 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 163: TIM2_CR1  = 0x00;                 /* us timebase: /16 = 1 MHz, free run */
      008274 35 00 53 00      [ 1]  276 	mov	0x5300+0, #0x00
                                    277 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 164: TIM2_PSCR = 0x04;
      008278 35 04 53 0E      [ 1]  278 	mov	0x530e+0, #0x04
                                    279 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 165: TIM2_ARRH = 0xFF;
      00827C 35 FF 53 0F      [ 1]  280 	mov	0x530f+0, #0xff
                                    281 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 166: TIM2_ARRL = 0xFF;
      008280 35 FF 53 10      [ 1]  282 	mov	0x5310+0, #0xff
                                    283 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 167: TIM2_CR1  = 0x01;
      008284 35 01 53 00      [ 1]  284 	mov	0x5300+0, #0x01
                                    285 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 169: ws2812_out_init();
      008288 CD 9E 95         [ 4]  286 	call	_ws2812_out_init
                                    287 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 171: __asm__("rim");
      00828B 9A               [ 1]  288 	rim
                                    289 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 173: while (millis() < 5000)           /* SWIM reflash window: pin 8 quiet */
      00828C                        290 00101$:
      00828C CD 9F 09         [ 4]  291 	call	_millis
      00828F A3 13 88         [ 2]  292 	cpw	x, #0x1388
      008292 24 05            [ 1]  293 	jrnc	00103$
                                    294 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 174: render_tick();
      008294 CD 82 2E         [ 4]  295 	call	_render_tick
      008297 20 F3            [ 2]  296 	jra	00101$
      008299                        297 00103$:
                                    298 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 176: CFG_GCR = 0x01;
      008299 35 01 7F 60      [ 1]  299 	mov	0x7f60+0, #0x01
                                    300 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 178: UART1_BRR2 = 0x01;                /* 38400: 16 MHz / 38400 = 0x1A1 */
      00829D 35 01 52 33      [ 1]  301 	mov	0x5233+0, #0x01
                                    302 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 179: UART1_BRR1 = 0x1A;
      0082A1 35 1A 52 32      [ 1]  303 	mov	0x5232+0, #0x1a
                                    304 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 180: UART1_CR2  = UART1_CR2_TEN;
      0082A5 35 08 52 35      [ 1]  305 	mov	0x5235+0, #0x08
                                    306 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 181: uart_puts("RBARF-A 1\r\n");
      0082A9 AE 80 95         [ 2]  307 	ldw	x, #(___str_0+0)
      0082AC CD 81 CE         [ 4]  308 	call	_uart_puts
      0082AF                        309 00113$:
                                    310 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 184: tl[12] = tl[5];               /* PREVIOUS arm return -> the unarmed */
      0082AF 55 02 46 02 4D   [ 1]  311 	mov	_tl+12, _tl+5
                                    312 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 185: tl[13] = tl[6];               /* gap ends at this arm's entry stamp */
      0082B4 55 02 47 02 4E   [ 1]  313 	mov	_tl+13, _tl+6
                                    314 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 186: render_tick();
      0082B9 CD 82 2E         [ 4]  315 	call	_render_tick
                                    316 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 188: stamp(3);                     /* ARM ENTRY */
      0082BC A6 03            [ 1]  317 	ld	a, #0x03
      0082BE CD 82 11         [ 4]  318 	call	_stamp
                                    319 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 194: __endasm;
      0082C1 AE 00 F0         [ 2]  320 	ldw x, #_capture_buf
      0082C4 90 AE 01 20      [ 2]  321 	ldw y, #288
      0082C8 CD 9F 63         [ 4]  322 	call _cap_arm
      0082CB C7 02 40         [ 1]  323 	ld _cap_got, a
                                    324 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 195: stamp(5);                     /* ARM RETURN */
      0082CE A6 05            [ 1]  325 	ld	a, #0x05
      0082D0 CD 82 11         [ 4]  326 	call	_stamp
                                    327 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 197: if (!cap_got) {
      0082D3 C6 02 40         [ 1]  328 	ld	a, _cap_got+0
      0082D6 26 0C            [ 1]  329 	jrne	00107$
                                    330 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 198: if (tl[11] != 0xFF)
      0082D8 AE 02 4C         [ 2]  331 	ldw	x, #(_tl+0)+11
      0082DB F6               [ 1]  332 	ld	a, (x)
      0082DC A1 FF            [ 1]  333 	cp	a, #0xff
      0082DE 27 CF            [ 1]  334 	jreq	00113$
                                    335 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 199: tl[11]++;
      0082E0 4C               [ 1]  336 	inc	a
      0082E1 F7               [ 1]  337 	ld	(x), a
                                    338 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 200: continue;
      0082E2 20 CB            [ 2]  339 	jra	00113$
      0082E4                        340 00107$:
                                    341 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 203: status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
      0082E4 4B 10            [ 1]  342 	push	#<(_ws2812_in_buf+0)
      0082E6 4B 02            [ 1]  343 	push	#((_ws2812_in_buf+0) >> 8)
      0082E8 4B 20            [ 1]  344 	push	#0x20
      0082EA 4B 01            [ 1]  345 	push	#0x01
      0082EC AE 00 F0         [ 2]  346 	ldw	x, #(_capture_buf+0)
      0082EF CD 97 E0         [ 4]  347 	call	_ws_decode_ex
      0082F2 6B 01            [ 1]  348 	ld	(0x01, sp), a
                                    349 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 204: eps = (dec_info.K != 0) ? dec_eps_centi() : 0;
      0082F4 CE 02 5B         [ 2]  350 	ldw	x, _dec_info+9
      0082F7 5D               [ 2]  351 	tnzw	x
      0082F8 27 04            [ 1]  352 	jreq	00116$
      0082FA CD 88 7B         [ 4]  353 	call	_dec_eps_centi
      0082FD 21                     354 	.byte 0x21
      0082FE                        355 00116$:
      0082FE 5F               [ 1]  356 	clrw	x
      0082FF                        357 00117$:
                                    358 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 205: tl[0] = (uint8_t)(((uint8_t)(status << 4)) | dec_info.cause);
      0082FF 7B 01            [ 1]  359 	ld	a, (0x01, sp)
      008301 4E               [ 1]  360 	swap	a
      008302 A4 F0            [ 1]  361 	and	a, #0xf0
      008304 6B 02            [ 1]  362 	ld	(0x02, sp), a
      008306 C6 02 53         [ 1]  363 	ld	a, _dec_info+1
      008309 1A 02            [ 1]  364 	or	a, (0x02, sp)
      00830B C7 02 41         [ 1]  365 	ld	_tl+0, a
                                    366 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 206: tl[1] = (uint8_t)((uint16_t)eps >> 8);
      00830E 9E               [ 1]  367 	ld	a, xh
      00830F C7 02 42         [ 1]  368 	ld	_tl+1, a
                                    369 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 207: tl[2] = (uint8_t)((uint16_t)eps & 0xFFu);
      008312 9F               [ 1]  370 	ld	a, xl
      008313 C7 02 43         [ 1]  371 	ld	_tl+2, a
                                    372 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 209: uart_putc('A');
      008316 A6 41            [ 1]  373 	ld	a, #0x41
      008318 CD 81 C0         [ 4]  374 	call	_uart_putc
                                    375 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 210: uart_blk(tl, 14);
      00831B 4B 0E            [ 1]  376 	push	#0x0e
      00831D 4B 00            [ 1]  377 	push	#0x00
      00831F AE 02 41         [ 2]  378 	ldw	x, #(_tl+0)
      008322 CD 81 E9         [ 4]  379 	call	_uart_blk
                                    380 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 211: uart_puts("\r\n");
      008325 AE 80 A1         [ 2]  381 	ldw	x, #(___str_1+0)
      008328 CD 81 CE         [ 4]  382 	call	_uart_puts
                                    383 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 213: nok++;
      00832B 72 5C 02 4F      [ 1]  384 	inc	_nok+0
                                    385 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 214: if (status == DEC_REFUSE || (nok & 3) == 0) {
      00832F 0D 01            [ 1]  386 	tnz	(0x01, sp)
      008331 27 07            [ 1]  387 	jreq	00108$
      008333 C6 02 4F         [ 1]  388 	ld	a, _nok+0
      008336 A5 03            [ 1]  389 	bcp	a, #0x03
      008338 26 15            [ 1]  390 	jrne	00109$
      00833A                        391 00108$:
                                    392 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 215: uart_putc('B');
      00833A A6 42            [ 1]  393 	ld	a, #0x42
      00833C CD 81 C0         [ 4]  394 	call	_uart_putc
                                    395 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 216: uart_blk(capture_buf, CAP_BYTES);
      00833F 4B 20            [ 1]  396 	push	#0x20
      008341 4B 01            [ 1]  397 	push	#0x01
      008343 AE 00 F0         [ 2]  398 	ldw	x, #(_capture_buf+0)
      008346 CD 81 E9         [ 4]  399 	call	_uart_blk
                                    400 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 217: uart_puts("\r\n");
      008349 AE 80 A1         [ 2]  401 	ldw	x, #(___str_1+0)
      00834C CD 81 CE         [ 4]  402 	call	_uart_puts
      00834F                        403 00109$:
                                    404 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 219: tl[11] = 0;
      00834F 35 00 02 4C      [ 1]  405 	mov	_tl+11, #0x00
                                    406 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 221: }
      008353 CC 82 AF         [ 2]  407 	jp	00113$
                                    408 	.area CODE
                                    409 	.area CONST
                                    410 	.area CONST
      008095                        411 ___str_0:
      008095 52 42 41 52 46 2D 41   412 	.ascii "RBARF-A 1"
             20 31
      00809E 0D                     413 	.db 0x0d
      00809F 0A                     414 	.db 0x0a
      0080A0 00                     415 	.db 0x00
                                    416 	.area CODE
                                    417 	.area CONST
      0080A1                        418 ___str_1:
      0080A1 0D                     419 	.db 0x0d
      0080A2 0A                     420 	.db 0x0a
      0080A3 00                     421 	.db 0x00
                                    422 	.area CODE
                                    423 	.area INITIALIZER
                                    424 	.area CABS (ABS)
