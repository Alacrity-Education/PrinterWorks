;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module base_prod
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _main
	.globl _anim_render
	.globl _ws2812_out_send
	.globl _ws2812_out_init
	.globl _millis
	.globl _dec_eps_centi
	.globl _ws_decode_ex
	.globl _ws2812_in_buf
	.globl _capture_buf
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_capture_buf::
	.ds 288
_ws2812_in_buf::
	.ds 48
_cap_got:
	.ds 1
_trim_v:
	.ds 1
_last_render:
	.ds 2
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area INITIALIZED
;--------------------------------------------------------
; Stack segment in internal ram
;--------------------------------------------------------
	.area SSEG
__start__stack:
	.ds	1

;--------------------------------------------------------
; absolute external ram data
;--------------------------------------------------------
	.area DABS (ABS)

; default segment ordering for linker
	.area HOME
	.area GSINIT
	.area GSFINAL
	.area CONST
	.area INITIALIZER
	.area CODE

;--------------------------------------------------------
; interrupt vector
;--------------------------------------------------------
	.area HOME
__interrupt_vect:
	int s_GSINIT ; reset
;--------------------------------------------------------
; global & static initialisations
;--------------------------------------------------------
	.area HOME
	.area GSINIT
	.area GSFINAL
	.area GSINIT
	call	___sdcc_external_startup
	tnz	a
	jreq	__sdcc_init_data
	jp	__sdcc_program_startup
__sdcc_init_data:
; stm8_genXINIT() start
	ldw x, #l_DATA
	jreq	00002$
00001$:
	clr (s_DATA - 1, x)
	decw x
	jrne	00001$
00002$:
	ldw	x, #l_INITIALIZER
	jreq	00004$
00003$:
	ld	a, (s_INITIALIZER - 1, x)
	ld	(s_INITIALIZED - 1, x), a
	decw	x
	jrne	00003$
00004$:
; stm8_genXINIT() end
	.area GSFINAL
	jp	__sdcc_program_startup
;--------------------------------------------------------
; Home
;--------------------------------------------------------
	.area HOME
	.area HOME
__sdcc_program_startup:
	jp	_main
;	return from main will return to caller
;--------------------------------------------------------
; code
;--------------------------------------------------------
	.area CODE
;	recon/approaches/dev_fe/base_prod.c: 91: static void uart_putc(char c)
;	-----------------------------------------
;	 function uart_putc
;	-----------------------------------------
_uart_putc:
;	recon/approaches/dev_fe/base_prod.c: 93: while (!(UART1_SR & UART1_SR_TXE))
00101$:
	ldw	x, #0x5230
	push	a
	ld	a, (x)
	ld	xh, a
	pop	a
	tnzw	x
	jrpl	00101$
;	recon/approaches/dev_fe/base_prod.c: 95: UART1_DR = (uint8_t)c;
	ld	0x5231, a
;	recon/approaches/dev_fe/base_prod.c: 96: }
	ret
;	recon/approaches/dev_fe/base_prod.c: 98: static void uart_puts(const char *s)
;	-----------------------------------------
;	 function uart_puts
;	-----------------------------------------
_uart_puts:
;	recon/approaches/dev_fe/base_prod.c: 100: while (*s)
00101$:
	ld	a, (x)
	jrne	00123$
	ret
00123$:
;	recon/approaches/dev_fe/base_prod.c: 101: uart_putc(*s++);
	incw	x
	pushw	x
	call	_uart_putc
	popw	x
	jra	00101$
;	recon/approaches/dev_fe/base_prod.c: 102: }
	ret
;	recon/approaches/dev_fe/base_prod.c: 136: static void uart_put_i16(int16_t v)
;	-----------------------------------------
;	 function uart_put_i16
;	-----------------------------------------
_uart_put_i16:
	sub	sp, #5
;	recon/approaches/dev_fe/base_prod.c: 142: uint8_t i, d, seen = 0;
	clr	(0x01, sp)
;	recon/approaches/dev_fe/base_prod.c: 143: if (v < 0) { uart_putc('-'); u = (uint16_t)(-v); }
	ldw	(0x04, sp), x
	tnz	(0x04, sp)
	jrpl	00102$
	pushw	x
	ld	a, #0x2d
	call	_uart_putc
	popw	x
	negw	x
;	recon/approaches/dev_fe/base_prod.c: 144: else u = (uint16_t)v;
;	recon/approaches/dev_fe/base_prod.c: 145: for (i = 0; i < 4; i++) {
00102$:
	clr	(0x04, sp)
;	recon/approaches/dev_fe/base_prod.c: 147: while (u >= P[i]) { u -= P[i]; d++; }
00123$:
	clr	(0x05, sp)
00104$:
	ld	a, (0x04, sp)
	clrw	y
	ld	yl, a
	sllw	y
	ldw	y, (_uart_put_i16_P_10000_12+0, y)
	ldw	(0x02, sp), y
	cpw	x, (0x02, sp)
	jrc	00127$
	subw	x, (0x02, sp)
	inc	(0x05, sp)
	jra	00104$
00127$:
	ld	a, (0x05, sp)
;	recon/approaches/dev_fe/base_prod.c: 148: if (d || seen) { uart_putc((char)('0' + d)); seen = 1; }
	tnz	(0x05, sp)
	jrne	00107$
	tnz	(0x01, sp)
	jreq	00112$
00107$:
	add	a, #0x30
	pushw	x
	call	_uart_putc
	popw	x
	ld	a, #0x01
	ld	(0x01, sp), a
00112$:
;	recon/approaches/dev_fe/base_prod.c: 145: for (i = 0; i < 4; i++) {
	inc	(0x04, sp)
	ld	a, (0x04, sp)
	cp	a, #0x04
	jrc	00123$
;	recon/approaches/dev_fe/base_prod.c: 150: uart_putc((char)('0' + (uint8_t)u));
	ld	a, xl
	add	a, #0x30
	addw	sp, #5
;	recon/approaches/dev_fe/base_prod.c: 151: }
	jp	_uart_putc
;	recon/approaches/dev_fe/base_prod.c: 156: static void auto_trim(int16_t eps_centi)
;	-----------------------------------------
;	 function auto_trim
;	-----------------------------------------
_auto_trim:
;	recon/approaches/dev_fe/base_prod.c: 176: int8_t v = trim_v;
	ld	a, _trim_v+0
;	recon/approaches/dev_fe/base_prod.c: 177: if (eps_centi > -40 && v < 3) v++;          /* faster than -0.4 % -> slow it */
	cpw	x, #0xffd8
	jrsle	00105$
	cp	a, #0x03
	jrsge	00105$
	inc	a
	jra	00106$
00105$:
;	recon/approaches/dev_fe/base_prod.c: 178: else if (eps_centi < -160 && v > -4) v--;   /* slower than -1.6 % -> speed up */
	cpw	x, #0xff60
	jrsge	00106$
	cp	a, #0xfc
	jrsle	00106$
	dec	a
00106$:
;	recon/approaches/dev_fe/base_prod.c: 179: trim_v = v;                                 /* applied on next arm   */
	ld	_trim_v+0, a
;	recon/approaches/dev_fe/base_prod.c: 180: }
	ret
;	recon/approaches/dev_fe/base_prod.c: 186: static void render_tick(void)
;	-----------------------------------------
;	 function render_tick
;	-----------------------------------------
_render_tick:
;	recon/approaches/dev_fe/base_prod.c: 188: uint16_t now = millis();
	call	_millis
;	recon/approaches/dev_fe/base_prod.c: 189: if ((uint16_t)(now - last_render) >= 10) {
	ldw	y, x
	subw	y, _last_render+0
	cpw	y, #0x000a
	jrnc	00113$
	ret
00113$:
;	recon/approaches/dev_fe/base_prod.c: 190: last_render = now;
	ldw	_last_render+0, x
;	recon/approaches/dev_fe/base_prod.c: 191: anim_render(now);
	call	_anim_render
;	recon/approaches/dev_fe/base_prod.c: 192: ws2812_out_send();            /* ~545 us, tick-masked inside */
;	recon/approaches/dev_fe/base_prod.c: 194: }
	jp	_ws2812_out_send
;	recon/approaches/dev_fe/base_prod.c: 196: void main(void)
;	-----------------------------------------
;	 function main
;	-----------------------------------------
_main:
	sub	sp, #4
;	recon/approaches/dev_fe/base_prod.c: 201: CLK_CKDIVR = 0x00;                /* HSI 16 MHz, dividers 1 */
	mov	0x50c6+0, #0x00
;	recon/approaches/dev_fe/base_prod.c: 202: CLK_HSITRIMR = 0x00;              /* factory trim (explicit) */
	mov	0x50cc+0, #0x00
;	recon/approaches/dev_fe/base_prod.c: 203: trim_v = 0;
	clr	_trim_v+0
;	recon/approaches/dev_fe/base_prod.c: 205: TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
	mov	0x5340+0, #0x00
;	recon/approaches/dev_fe/base_prod.c: 206: TIM4_PSCR = 0x07;
	mov	0x5347+0, #0x07
;	recon/approaches/dev_fe/base_prod.c: 207: TIM4_ARR  = 124;
	mov	0x5348+0, #0x7c
;	recon/approaches/dev_fe/base_prod.c: 208: TIM4_SR   = 0x00;
	mov	0x5344+0, #0x00
;	recon/approaches/dev_fe/base_prod.c: 209: TIM4_IER  = 0x01;
	mov	0x5343+0, #0x01
;	recon/approaches/dev_fe/base_prod.c: 210: TIM4_CR1  = 0x01;
	mov	0x5340+0, #0x01
;	recon/approaches/dev_fe/base_prod.c: 212: ws2812_out_init();
	call	_ws2812_out_init
;	recon/approaches/dev_fe/base_prod.c: 217: __asm__("rim");
	rim
;	recon/approaches/dev_fe/base_prod.c: 221: while (millis() < 5000)
00101$:
	call	_millis
	cpw	x, #0x1388
	jrnc	00103$
;	recon/approaches/dev_fe/base_prod.c: 222: render_tick();
	call	_render_tick
	jra	00101$
00103$:
;	recon/approaches/dev_fe/base_prod.c: 224: CFG_GCR = 0x01;                   /* activation level: SWIM off */
	mov	0x7f60+0, #0x01
;	recon/approaches/dev_fe/base_prod.c: 227: UART1_BRR2 = 0x03;
	mov	0x5233+0, #0x03
;	recon/approaches/dev_fe/base_prod.c: 228: UART1_BRR1 = 0x68;
	mov	0x5232+0, #0x68
;	recon/approaches/dev_fe/base_prod.c: 229: UART1_CR2  = UART1_CR2_TEN;
	mov	0x5235+0, #0x08
;	recon/approaches/dev_fe/base_prod.c: 230: uart_puts("RBARF-P 1\r\n");
	ldw	x, #(___str_0+0)
	call	_uart_puts
00117$:
;	recon/approaches/dev_fe/base_prod.c: 233: render_tick();
	call	_render_tick
;	recon/approaches/dev_fe/base_prod.c: 236: CLK_HSITRIMR = TRIM_CODE(trim_v);
	ld	a, _trim_v+0
	and	a, #0x07
	ld	0x50cc, a
;	recon/approaches/dev_fe/base_prod.c: 242: __endasm;
	ldw x, #_capture_buf
	ldw y, #288
	call _cap_arm
	ld _cap_got, a
;	recon/approaches/dev_fe/base_prod.c: 243: CLK_HSITRIMR = 0x00;          /* factory trim before any UART */
	mov	0x50cc+0, #0x00
;	recon/approaches/dev_fe/base_prod.c: 245: if (!cap_got)
	ld	a, _cap_got+0
	jreq	00117$
;	recon/approaches/dev_fe/base_prod.c: 251: status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
	push	#<(_ws2812_in_buf+0)
	push	#((_ws2812_in_buf+0) >> 8)
	push	#0x20
	push	#0x01
	ldw	x, #(_capture_buf+0)
	call	_ws_decode_ex
	ld	(0x04, sp), a
;	recon/approaches/dev_fe/base_prod.c: 252: eps = (dec_info.K != 0) ? dec_eps_centi() : 0;
	ldw	x, _dec_info+9
	tnzw	x
	jreq	00120$
	call	_dec_eps_centi
	.byte 0x21
00120$:
	clrw	x
00121$:
	ldw	(0x01, sp), x
;	recon/approaches/dev_fe/base_prod.c: 254: uart_putc('D');
	ld	a, #0x44
	call	_uart_putc
;	recon/approaches/dev_fe/base_prod.c: 255: uart_putc(':');
	ld	a, #0x3a
	call	_uart_putc
;	recon/approaches/dev_fe/base_prod.c: 256: if (status == DEC_DIRECT)     uart_putc('O');
	ld	a, (0x04, sp)
	dec	a
	jrne	00190$
	ld	a, #0x01
	ld	(0x03, sp), a
	.byte 0xc5
00190$:
	clr	(0x03, sp)
00191$:
;	recon/approaches/dev_fe/base_prod.c: 257: else if (status == DEC_CHASE) uart_putc('C');
	ld	a, (0x04, sp)
	sub	a, #0x02
	jrne	00193$
	inc	a
	ld	(0x04, sp), a
	.byte 0xc5
00193$:
	clr	(0x04, sp)
00194$:
;	recon/approaches/dev_fe/base_prod.c: 256: if (status == DEC_DIRECT)     uart_putc('O');
	tnz	(0x03, sp)
	jreq	00110$
	ld	a, #0x4f
	call	_uart_putc
	jra	00111$
00110$:
;	recon/approaches/dev_fe/base_prod.c: 257: else if (status == DEC_CHASE) uart_putc('C');
	tnz	(0x04, sp)
	jreq	00107$
	ld	a, #0x43
	call	_uart_putc
	jra	00111$
00107$:
;	recon/approaches/dev_fe/base_prod.c: 259: uart_putc('R');
	ld	a, #0x52
	call	_uart_putc
;	recon/approaches/dev_fe/base_prod.c: 260: uart_putc((char)('0' + dec_info.cause));
	ld	a, _dec_info+1
	add	a, #0x30
	call	_uart_putc
00111$:
;	recon/approaches/dev_fe/base_prod.c: 262: uart_putc(':');
	ld	a, #0x3a
	call	_uart_putc
;	recon/approaches/dev_fe/base_prod.c: 266: uart_put_i16(eps);
	ldw	x, (0x01, sp)
	call	_uart_put_i16
;	recon/approaches/dev_fe/base_prod.c: 268: uart_puts("\r\n");
	ldw	x, #(___str_1+0)
	call	_uart_puts
;	recon/approaches/dev_fe/base_prod.c: 270: if (status == DEC_DIRECT || status == DEC_CHASE) {
	tnz	(0x03, sp)
	jrne	00112$
	tnz	(0x04, sp)
	jrne	00198$
	jp	00117$
00198$:
00112$:
;	recon/approaches/dev_fe/base_prod.c: 279: auto_trim(eps);           /* only after a verified decode */
	ldw	x, (0x01, sp)
	call	_auto_trim
;	recon/approaches/dev_fe/base_prod.c: 282: }
	jp	00117$
	.area CODE
	.area CONST
	.area CONST
_uart_put_i16_P_10000_12:
	.dw #0x2710
	.dw #0x03e8
	.dw #0x0064
	.dw #0x000a
	.area CODE
	.area CONST
___str_0:
	.ascii "RBARF-P 1"
	.db 0x0d
	.db 0x0a
	.db 0x00
	.area CODE
	.area CONST
___str_1:
	.db 0x0d
	.db 0x0a
	.db 0x00
	.area CODE
	.area INITIALIZER
	.area CABS (ABS)
