                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module base_prod
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
      000241                         29 _trim_v:
      000241                         30 	.ds 1
      000242                         31 _last_render:
      000242                         32 	.ds 2
                                     33 ;--------------------------------------------------------
                                     34 ; ram data
                                     35 ;--------------------------------------------------------
                                     36 	.area INITIALIZED
                                     37 ;--------------------------------------------------------
                                     38 ; Stack segment in internal ram
                                     39 ;--------------------------------------------------------
                                     40 	.area SSEG
      00036B                         41 __start__stack:
      00036B                         42 	.ds	1
                                     43 
                                     44 ;--------------------------------------------------------
                                     45 ; absolute external ram data
                                     46 ;--------------------------------------------------------
                                     47 	.area DABS (ABS)
                                     48 
                                     49 ; default segment ordering for linker
                                     50 	.area HOME
                                     51 	.area GSINIT
                                     52 	.area GSFINAL
                                     53 	.area CONST
                                     54 	.area INITIALIZER
                                     55 	.area CODE
                                     56 
                                     57 ;--------------------------------------------------------
                                     58 ; interrupt vector
                                     59 ;--------------------------------------------------------
                                     60 	.area HOME
      008068                         61 __interrupt_vect:
      008068 82 00 80 6F             62 	int s_GSINIT ; reset
                                     63 ;--------------------------------------------------------
                                     64 ; global & static initialisations
                                     65 ;--------------------------------------------------------
                                     66 	.area HOME
                                     67 	.area GSINIT
                                     68 	.area GSFINAL
                                     69 	.area GSINIT
      00806F CD 9F 36         [ 4]   70 	call	___sdcc_external_startup
      008072 4D               [ 1]   71 	tnz	a
      008073 27 03            [ 1]   72 	jreq	__sdcc_init_data
      008075 CC 80 6C         [ 2]   73 	jp	__sdcc_program_startup
      008078                         74 __sdcc_init_data:
                                     75 ; stm8_genXINIT() start
      008078 AE 02 7B         [ 2]   76 	ldw x, #l_DATA
      00807B 27 07            [ 1]   77 	jreq	00002$
      00807D                         78 00001$:
      00807D 72 4F 00 EF      [ 1]   79 	clr (s_DATA - 1, x)
      008081 5A               [ 2]   80 	decw x
      008082 26 F9            [ 1]   81 	jrne	00001$
      008084                         82 00002$:
      008084 AE 00 00         [ 2]   83 	ldw	x, #l_INITIALIZER
      008087 27 09            [ 1]   84 	jreq	00004$
      008089                         85 00003$:
      008089 D6 81 C7         [ 1]   86 	ld	a, (s_INITIALIZER - 1, x)
      00808C D7 03 6A         [ 1]   87 	ld	(s_INITIALIZED - 1, x), a
      00808F 5A               [ 2]   88 	decw	x
      008090 26 F7            [ 1]   89 	jrne	00003$
      008092                         90 00004$:
                                     91 ; stm8_genXINIT() end
                                     92 	.area GSFINAL
      008092 CC 80 6C         [ 2]   93 	jp	__sdcc_program_startup
                                     94 ;--------------------------------------------------------
                                     95 ; Home
                                     96 ;--------------------------------------------------------
                                     97 	.area HOME
                                     98 	.area HOME
      00806C                         99 __sdcc_program_startup:
      00806C CC 82 6D         [ 2]  100 	jp	_main
                                    101 ;	return from main will return to caller
                                    102 ;--------------------------------------------------------
                                    103 ; code
                                    104 ;--------------------------------------------------------
                                    105 	.area CODE
                                    106 ;	recon/approaches/dev_fe/base_prod.c: 91: static void uart_putc(char c)
                                    107 ;	-----------------------------------------
                                    108 ;	 function uart_putc
                                    109 ;	-----------------------------------------
      0081C8                        110 _uart_putc:
                                    111 ;	recon/approaches/dev_fe/base_prod.c: 93: while (!(UART1_SR & UART1_SR_TXE))
      0081C8                        112 00101$:
      0081C8 AE 52 30         [ 2]  113 	ldw	x, #0x5230
      0081CB 88               [ 1]  114 	push	a
      0081CC F6               [ 1]  115 	ld	a, (x)
      0081CD 95               [ 1]  116 	ld	xh, a
      0081CE 84               [ 1]  117 	pop	a
      0081CF 5D               [ 2]  118 	tnzw	x
      0081D0 2A F6            [ 1]  119 	jrpl	00101$
                                    120 ;	recon/approaches/dev_fe/base_prod.c: 95: UART1_DR = (uint8_t)c;
      0081D2 C7 52 31         [ 1]  121 	ld	0x5231, a
                                    122 ;	recon/approaches/dev_fe/base_prod.c: 96: }
      0081D5 81               [ 4]  123 	ret
                                    124 ;	recon/approaches/dev_fe/base_prod.c: 98: static void uart_puts(const char *s)
                                    125 ;	-----------------------------------------
                                    126 ;	 function uart_puts
                                    127 ;	-----------------------------------------
      0081D6                        128 _uart_puts:
                                    129 ;	recon/approaches/dev_fe/base_prod.c: 100: while (*s)
      0081D6                        130 00101$:
      0081D6 F6               [ 1]  131 	ld	a, (x)
      0081D7 26 01            [ 1]  132 	jrne	00123$
      0081D9 81               [ 4]  133 	ret
      0081DA                        134 00123$:
                                    135 ;	recon/approaches/dev_fe/base_prod.c: 101: uart_putc(*s++);
      0081DA 5C               [ 1]  136 	incw	x
      0081DB 89               [ 2]  137 	pushw	x
      0081DC CD 81 C8         [ 4]  138 	call	_uart_putc
      0081DF 85               [ 2]  139 	popw	x
      0081E0 20 F4            [ 2]  140 	jra	00101$
                                    141 ;	recon/approaches/dev_fe/base_prod.c: 102: }
      0081E2 81               [ 4]  142 	ret
                                    143 ;	recon/approaches/dev_fe/base_prod.c: 136: static void uart_put_i16(int16_t v)
                                    144 ;	-----------------------------------------
                                    145 ;	 function uart_put_i16
                                    146 ;	-----------------------------------------
      0081E3                        147 _uart_put_i16:
      0081E3 52 05            [ 2]  148 	sub	sp, #5
                                    149 ;	recon/approaches/dev_fe/base_prod.c: 142: uint8_t i, d, seen = 0;
      0081E5 0F 01            [ 1]  150 	clr	(0x01, sp)
                                    151 ;	recon/approaches/dev_fe/base_prod.c: 143: if (v < 0) { uart_putc('-'); u = (uint16_t)(-v); }
      0081E7 1F 04            [ 2]  152 	ldw	(0x04, sp), x
      0081E9 0D 04            [ 1]  153 	tnz	(0x04, sp)
      0081EB 2A 08            [ 1]  154 	jrpl	00102$
      0081ED 89               [ 2]  155 	pushw	x
      0081EE A6 2D            [ 1]  156 	ld	a, #0x2d
      0081F0 CD 81 C8         [ 4]  157 	call	_uart_putc
      0081F3 85               [ 2]  158 	popw	x
      0081F4 50               [ 2]  159 	negw	x
                                    160 ;	recon/approaches/dev_fe/base_prod.c: 144: else u = (uint16_t)v;
                                    161 ;	recon/approaches/dev_fe/base_prod.c: 145: for (i = 0; i < 4; i++) {
      0081F5                        162 00102$:
      0081F5 0F 04            [ 1]  163 	clr	(0x04, sp)
                                    164 ;	recon/approaches/dev_fe/base_prod.c: 147: while (u >= P[i]) { u -= P[i]; d++; }
      0081F7                        165 00123$:
      0081F7 0F 05            [ 1]  166 	clr	(0x05, sp)
      0081F9                        167 00104$:
      0081F9 7B 04            [ 1]  168 	ld	a, (0x04, sp)
      0081FB 90 5F            [ 1]  169 	clrw	y
      0081FD 90 97            [ 1]  170 	ld	yl, a
      0081FF 90 58            [ 2]  171 	sllw	y
      008201 90 DE 80 95      [ 2]  172 	ldw	y, (_uart_put_i16_P_10000_12+0, y)
      008205 17 02            [ 2]  173 	ldw	(0x02, sp), y
      008207 13 02            [ 2]  174 	cpw	x, (0x02, sp)
      008209 25 07            [ 1]  175 	jrc	00127$
      00820B 72 F0 02         [ 2]  176 	subw	x, (0x02, sp)
      00820E 0C 05            [ 1]  177 	inc	(0x05, sp)
      008210 20 E7            [ 2]  178 	jra	00104$
      008212                        179 00127$:
      008212 7B 05            [ 1]  180 	ld	a, (0x05, sp)
                                    181 ;	recon/approaches/dev_fe/base_prod.c: 148: if (d || seen) { uart_putc((char)('0' + d)); seen = 1; }
      008214 0D 05            [ 1]  182 	tnz	(0x05, sp)
      008216 26 04            [ 1]  183 	jrne	00107$
      008218 0D 01            [ 1]  184 	tnz	(0x01, sp)
      00821A 27 0B            [ 1]  185 	jreq	00112$
      00821C                        186 00107$:
      00821C AB 30            [ 1]  187 	add	a, #0x30
      00821E 89               [ 2]  188 	pushw	x
      00821F CD 81 C8         [ 4]  189 	call	_uart_putc
      008222 85               [ 2]  190 	popw	x
      008223 A6 01            [ 1]  191 	ld	a, #0x01
      008225 6B 01            [ 1]  192 	ld	(0x01, sp), a
      008227                        193 00112$:
                                    194 ;	recon/approaches/dev_fe/base_prod.c: 145: for (i = 0; i < 4; i++) {
      008227 0C 04            [ 1]  195 	inc	(0x04, sp)
      008229 7B 04            [ 1]  196 	ld	a, (0x04, sp)
      00822B A1 04            [ 1]  197 	cp	a, #0x04
      00822D 25 C8            [ 1]  198 	jrc	00123$
                                    199 ;	recon/approaches/dev_fe/base_prod.c: 150: uart_putc((char)('0' + (uint8_t)u));
      00822F 9F               [ 1]  200 	ld	a, xl
      008230 AB 30            [ 1]  201 	add	a, #0x30
      008232 5B 05            [ 2]  202 	addw	sp, #5
                                    203 ;	recon/approaches/dev_fe/base_prod.c: 151: }
      008234 CC 81 C8         [ 2]  204 	jp	_uart_putc
                                    205 ;	recon/approaches/dev_fe/base_prod.c: 156: static void auto_trim(int16_t eps_centi)
                                    206 ;	-----------------------------------------
                                    207 ;	 function auto_trim
                                    208 ;	-----------------------------------------
      008237                        209 _auto_trim:
                                    210 ;	recon/approaches/dev_fe/base_prod.c: 176: int8_t v = trim_v;
      008237 C6 02 41         [ 1]  211 	ld	a, _trim_v+0
                                    212 ;	recon/approaches/dev_fe/base_prod.c: 177: if (eps_centi > -40 && v < 3) v++;          /* faster than -0.4 % -> slow it */
      00823A A3 FF D8         [ 2]  213 	cpw	x, #0xffd8
      00823D 2D 07            [ 1]  214 	jrsle	00105$
      00823F A1 03            [ 1]  215 	cp	a, #0x03
      008241 2E 03            [ 1]  216 	jrsge	00105$
      008243 4C               [ 1]  217 	inc	a
      008244 20 0A            [ 2]  218 	jra	00106$
      008246                        219 00105$:
                                    220 ;	recon/approaches/dev_fe/base_prod.c: 178: else if (eps_centi < -160 && v > -4) v--;   /* slower than -1.6 % -> speed up */
      008246 A3 FF 60         [ 2]  221 	cpw	x, #0xff60
      008249 2E 05            [ 1]  222 	jrsge	00106$
      00824B A1 FC            [ 1]  223 	cp	a, #0xfc
      00824D 2D 01            [ 1]  224 	jrsle	00106$
      00824F 4A               [ 1]  225 	dec	a
      008250                        226 00106$:
                                    227 ;	recon/approaches/dev_fe/base_prod.c: 179: trim_v = v;                                 /* applied on next arm   */
      008250 C7 02 41         [ 1]  228 	ld	_trim_v+0, a
                                    229 ;	recon/approaches/dev_fe/base_prod.c: 180: }
      008253 81               [ 4]  230 	ret
                                    231 ;	recon/approaches/dev_fe/base_prod.c: 186: static void render_tick(void)
                                    232 ;	-----------------------------------------
                                    233 ;	 function render_tick
                                    234 ;	-----------------------------------------
      008254                        235 _render_tick:
                                    236 ;	recon/approaches/dev_fe/base_prod.c: 188: uint16_t now = millis();
      008254 CD 9F 13         [ 4]  237 	call	_millis
                                    238 ;	recon/approaches/dev_fe/base_prod.c: 189: if ((uint16_t)(now - last_render) >= 10) {
      008257 90 93            [ 1]  239 	ldw	y, x
      008259 72 B2 02 42      [ 2]  240 	subw	y, _last_render+0
      00825D 90 A3 00 0A      [ 2]  241 	cpw	y, #0x000a
      008261 24 01            [ 1]  242 	jrnc	00113$
      008263 81               [ 4]  243 	ret
      008264                        244 00113$:
                                    245 ;	recon/approaches/dev_fe/base_prod.c: 190: last_render = now;
      008264 CF 02 42         [ 2]  246 	ldw	_last_render+0, x
                                    247 ;	recon/approaches/dev_fe/base_prod.c: 191: anim_render(now);
      008267 CD 9D C9         [ 4]  248 	call	_anim_render
                                    249 ;	recon/approaches/dev_fe/base_prod.c: 192: ws2812_out_send();            /* ~545 us, tick-masked inside */
                                    250 ;	recon/approaches/dev_fe/base_prod.c: 194: }
      00826A CC 9E B0         [ 2]  251 	jp	_ws2812_out_send
                                    252 ;	recon/approaches/dev_fe/base_prod.c: 196: void main(void)
                                    253 ;	-----------------------------------------
                                    254 ;	 function main
                                    255 ;	-----------------------------------------
      00826D                        256 _main:
      00826D 52 04            [ 2]  257 	sub	sp, #4
                                    258 ;	recon/approaches/dev_fe/base_prod.c: 201: CLK_CKDIVR = 0x00;                /* HSI 16 MHz, dividers 1 */
      00826F 35 00 50 C6      [ 1]  259 	mov	0x50c6+0, #0x00
                                    260 ;	recon/approaches/dev_fe/base_prod.c: 202: CLK_HSITRIMR = 0x00;              /* factory trim (explicit) */
      008273 35 00 50 CC      [ 1]  261 	mov	0x50cc+0, #0x00
                                    262 ;	recon/approaches/dev_fe/base_prod.c: 203: trim_v = 0;
      008277 72 5F 02 41      [ 1]  263 	clr	_trim_v+0
                                    264 ;	recon/approaches/dev_fe/base_prod.c: 205: TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
      00827B 35 00 53 40      [ 1]  265 	mov	0x5340+0, #0x00
                                    266 ;	recon/approaches/dev_fe/base_prod.c: 206: TIM4_PSCR = 0x07;
      00827F 35 07 53 47      [ 1]  267 	mov	0x5347+0, #0x07
                                    268 ;	recon/approaches/dev_fe/base_prod.c: 207: TIM4_ARR  = 124;
      008283 35 7C 53 48      [ 1]  269 	mov	0x5348+0, #0x7c
                                    270 ;	recon/approaches/dev_fe/base_prod.c: 208: TIM4_SR   = 0x00;
      008287 35 00 53 44      [ 1]  271 	mov	0x5344+0, #0x00
                                    272 ;	recon/approaches/dev_fe/base_prod.c: 209: TIM4_IER  = 0x01;
      00828B 35 01 53 43      [ 1]  273 	mov	0x5343+0, #0x01
                                    274 ;	recon/approaches/dev_fe/base_prod.c: 210: TIM4_CR1  = 0x01;
      00828F 35 01 53 40      [ 1]  275 	mov	0x5340+0, #0x01
                                    276 ;	recon/approaches/dev_fe/base_prod.c: 212: ws2812_out_init();
      008293 CD 9E 9F         [ 4]  277 	call	_ws2812_out_init
                                    278 ;	recon/approaches/dev_fe/base_prod.c: 217: __asm__("rim");
      008296 9A               [ 1]  279 	rim
                                    280 ;	recon/approaches/dev_fe/base_prod.c: 221: while (millis() < 5000)
      008297                        281 00101$:
      008297 CD 9F 13         [ 4]  282 	call	_millis
      00829A A3 13 88         [ 2]  283 	cpw	x, #0x1388
      00829D 24 05            [ 1]  284 	jrnc	00103$
                                    285 ;	recon/approaches/dev_fe/base_prod.c: 222: render_tick();
      00829F CD 82 54         [ 4]  286 	call	_render_tick
      0082A2 20 F3            [ 2]  287 	jra	00101$
      0082A4                        288 00103$:
                                    289 ;	recon/approaches/dev_fe/base_prod.c: 224: CFG_GCR = 0x01;                   /* activation level: SWIM off */
      0082A4 35 01 7F 60      [ 1]  290 	mov	0x7f60+0, #0x01
                                    291 ;	recon/approaches/dev_fe/base_prod.c: 227: UART1_BRR2 = 0x03;
      0082A8 35 03 52 33      [ 1]  292 	mov	0x5233+0, #0x03
                                    293 ;	recon/approaches/dev_fe/base_prod.c: 228: UART1_BRR1 = 0x68;
      0082AC 35 68 52 32      [ 1]  294 	mov	0x5232+0, #0x68
                                    295 ;	recon/approaches/dev_fe/base_prod.c: 229: UART1_CR2  = UART1_CR2_TEN;
      0082B0 35 08 52 35      [ 1]  296 	mov	0x5235+0, #0x08
                                    297 ;	recon/approaches/dev_fe/base_prod.c: 230: uart_puts("RBARF-P 1\r\n");
      0082B4 AE 80 9D         [ 2]  298 	ldw	x, #(___str_0+0)
      0082B7 CD 81 D6         [ 4]  299 	call	_uart_puts
      0082BA                        300 00117$:
                                    301 ;	recon/approaches/dev_fe/base_prod.c: 233: render_tick();
      0082BA CD 82 54         [ 4]  302 	call	_render_tick
                                    303 ;	recon/approaches/dev_fe/base_prod.c: 236: CLK_HSITRIMR = TRIM_CODE(trim_v);
      0082BD C6 02 41         [ 1]  304 	ld	a, _trim_v+0
      0082C0 A4 07            [ 1]  305 	and	a, #0x07
      0082C2 C7 50 CC         [ 1]  306 	ld	0x50cc, a
                                    307 ;	recon/approaches/dev_fe/base_prod.c: 242: __endasm;
      0082C5 AE 00 F0         [ 2]  308 	ldw x, #_capture_buf
      0082C8 90 AE 01 20      [ 2]  309 	ldw y, #288
      0082CC CD 9F 65         [ 4]  310 	call _cap_arm
      0082CF C7 02 40         [ 1]  311 	ld _cap_got, a
                                    312 ;	recon/approaches/dev_fe/base_prod.c: 243: CLK_HSITRIMR = 0x00;          /* factory trim before any UART */
      0082D2 35 00 50 CC      [ 1]  313 	mov	0x50cc+0, #0x00
                                    314 ;	recon/approaches/dev_fe/base_prod.c: 245: if (!cap_got)
      0082D6 C6 02 40         [ 1]  315 	ld	a, _cap_got+0
      0082D9 27 DF            [ 1]  316 	jreq	00117$
                                    317 ;	recon/approaches/dev_fe/base_prod.c: 251: status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
      0082DB 4B 10            [ 1]  318 	push	#<(_ws2812_in_buf+0)
      0082DD 4B 02            [ 1]  319 	push	#((_ws2812_in_buf+0) >> 8)
      0082DF 4B 20            [ 1]  320 	push	#0x20
      0082E1 4B 01            [ 1]  321 	push	#0x01
      0082E3 AE 00 F0         [ 2]  322 	ldw	x, #(_capture_buf+0)
      0082E6 CD 97 EA         [ 4]  323 	call	_ws_decode_ex
      0082E9 6B 04            [ 1]  324 	ld	(0x04, sp), a
                                    325 ;	recon/approaches/dev_fe/base_prod.c: 252: eps = (dec_info.K != 0) ? dec_eps_centi() : 0;
      0082EB CE 02 4E         [ 2]  326 	ldw	x, _dec_info+9
      0082EE 5D               [ 2]  327 	tnzw	x
      0082EF 27 04            [ 1]  328 	jreq	00120$
      0082F1 CD 88 85         [ 4]  329 	call	_dec_eps_centi
      0082F4 21                     330 	.byte 0x21
      0082F5                        331 00120$:
      0082F5 5F               [ 1]  332 	clrw	x
      0082F6                        333 00121$:
      0082F6 1F 01            [ 2]  334 	ldw	(0x01, sp), x
                                    335 ;	recon/approaches/dev_fe/base_prod.c: 254: uart_putc('D');
      0082F8 A6 44            [ 1]  336 	ld	a, #0x44
      0082FA CD 81 C8         [ 4]  337 	call	_uart_putc
                                    338 ;	recon/approaches/dev_fe/base_prod.c: 255: uart_putc(':');
      0082FD A6 3A            [ 1]  339 	ld	a, #0x3a
      0082FF CD 81 C8         [ 4]  340 	call	_uart_putc
                                    341 ;	recon/approaches/dev_fe/base_prod.c: 256: if (status == DEC_DIRECT)     uart_putc('O');
      008302 7B 04            [ 1]  342 	ld	a, (0x04, sp)
      008304 4A               [ 1]  343 	dec	a
      008305 26 05            [ 1]  344 	jrne	00190$
      008307 A6 01            [ 1]  345 	ld	a, #0x01
      008309 6B 03            [ 1]  346 	ld	(0x03, sp), a
      00830B C5                     347 	.byte 0xc5
      00830C                        348 00190$:
      00830C 0F 03            [ 1]  349 	clr	(0x03, sp)
      00830E                        350 00191$:
                                    351 ;	recon/approaches/dev_fe/base_prod.c: 257: else if (status == DEC_CHASE) uart_putc('C');
      00830E 7B 04            [ 1]  352 	ld	a, (0x04, sp)
      008310 A0 02            [ 1]  353 	sub	a, #0x02
      008312 26 04            [ 1]  354 	jrne	00193$
      008314 4C               [ 1]  355 	inc	a
      008315 6B 04            [ 1]  356 	ld	(0x04, sp), a
      008317 C5                     357 	.byte 0xc5
      008318                        358 00193$:
      008318 0F 04            [ 1]  359 	clr	(0x04, sp)
      00831A                        360 00194$:
                                    361 ;	recon/approaches/dev_fe/base_prod.c: 256: if (status == DEC_DIRECT)     uart_putc('O');
      00831A 0D 03            [ 1]  362 	tnz	(0x03, sp)
      00831C 27 07            [ 1]  363 	jreq	00110$
      00831E A6 4F            [ 1]  364 	ld	a, #0x4f
      008320 CD 81 C8         [ 4]  365 	call	_uart_putc
      008323 20 18            [ 2]  366 	jra	00111$
      008325                        367 00110$:
                                    368 ;	recon/approaches/dev_fe/base_prod.c: 257: else if (status == DEC_CHASE) uart_putc('C');
      008325 0D 04            [ 1]  369 	tnz	(0x04, sp)
      008327 27 07            [ 1]  370 	jreq	00107$
      008329 A6 43            [ 1]  371 	ld	a, #0x43
      00832B CD 81 C8         [ 4]  372 	call	_uart_putc
      00832E 20 0D            [ 2]  373 	jra	00111$
      008330                        374 00107$:
                                    375 ;	recon/approaches/dev_fe/base_prod.c: 259: uart_putc('R');
      008330 A6 52            [ 1]  376 	ld	a, #0x52
      008332 CD 81 C8         [ 4]  377 	call	_uart_putc
                                    378 ;	recon/approaches/dev_fe/base_prod.c: 260: uart_putc((char)('0' + dec_info.cause));
      008335 C6 02 46         [ 1]  379 	ld	a, _dec_info+1
      008338 AB 30            [ 1]  380 	add	a, #0x30
      00833A CD 81 C8         [ 4]  381 	call	_uart_putc
      00833D                        382 00111$:
                                    383 ;	recon/approaches/dev_fe/base_prod.c: 262: uart_putc(':');
      00833D A6 3A            [ 1]  384 	ld	a, #0x3a
      00833F CD 81 C8         [ 4]  385 	call	_uart_putc
                                    386 ;	recon/approaches/dev_fe/base_prod.c: 266: uart_put_i16(eps);
      008342 1E 01            [ 2]  387 	ldw	x, (0x01, sp)
      008344 CD 81 E3         [ 4]  388 	call	_uart_put_i16
                                    389 ;	recon/approaches/dev_fe/base_prod.c: 268: uart_puts("\r\n");
      008347 AE 80 A9         [ 2]  390 	ldw	x, #(___str_1+0)
      00834A CD 81 D6         [ 4]  391 	call	_uart_puts
                                    392 ;	recon/approaches/dev_fe/base_prod.c: 270: if (status == DEC_DIRECT || status == DEC_CHASE) {
      00834D 0D 03            [ 1]  393 	tnz	(0x03, sp)
      00834F 26 07            [ 1]  394 	jrne	00112$
      008351 0D 04            [ 1]  395 	tnz	(0x04, sp)
      008353 26 03            [ 1]  396 	jrne	00198$
      008355 CC 82 BA         [ 2]  397 	jp	00117$
      008358                        398 00198$:
      008358                        399 00112$:
                                    400 ;	recon/approaches/dev_fe/base_prod.c: 279: auto_trim(eps);           /* only after a verified decode */
      008358 1E 01            [ 2]  401 	ldw	x, (0x01, sp)
      00835A CD 82 37         [ 4]  402 	call	_auto_trim
                                    403 ;	recon/approaches/dev_fe/base_prod.c: 282: }
      00835D CC 82 BA         [ 2]  404 	jp	00117$
                                    405 	.area CODE
                                    406 	.area CONST
                                    407 	.area CONST
      008095                        408 _uart_put_i16_P_10000_12:
      008095 27 10                  409 	.dw #0x2710
      008097 03 E8                  410 	.dw #0x03e8
      008099 00 64                  411 	.dw #0x0064
      00809B 00 0A                  412 	.dw #0x000a
                                    413 	.area CODE
                                    414 	.area CONST
      00809D                        415 ___str_0:
      00809D 52 42 41 52 46 2D 50   416 	.ascii "RBARF-P 1"
             20 31
      0080A6 0D                     417 	.db 0x0d
      0080A7 0A                     418 	.db 0x0a
      0080A8 00                     419 	.db 0x00
                                    420 	.area CODE
                                    421 	.area CONST
      0080A9                        422 ___str_1:
      0080A9 0D                     423 	.db 0x0d
      0080AA 0A                     424 	.db 0x0a
      0080AB 00                     425 	.db 0x00
                                    426 	.area CODE
                                    427 	.area INITIALIZER
                                    428 	.area CABS (ABS)
