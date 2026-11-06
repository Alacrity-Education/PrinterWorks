;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module rbarf_arm
	
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
_tl:
	.ds 14
_nok:
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 95: static void uart_putc(char c)
;	-----------------------------------------
;	 function uart_putc
;	-----------------------------------------
_uart_putc:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 97: while (!(UART1_SR & UART1_SR_TXE))
00101$:
	ldw	x, #0x5230
	push	a
	ld	a, (x)
	ld	xh, a
	pop	a
	tnzw	x
	jrpl	00101$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 99: UART1_DR = (uint8_t)c;
	ld	0x5231, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 100: }
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 102: static void uart_puts(const char *s)
;	-----------------------------------------
;	 function uart_puts
;	-----------------------------------------
_uart_puts:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 104: while (*s)
00101$:
	ld	a, (x)
	jrne	00123$
	ret
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 105: uart_putc(*s++);
	incw	x
	pushw	x
	call	_uart_putc
	popw	x
	jra	00101$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 106: }
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 108: static void uart_nib(uint8_t d)
;	-----------------------------------------
;	 function uart_nib
;	-----------------------------------------
_uart_nib:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 110: d = (uint8_t)(d + '0');
	add	a, #0x30
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 111: if (d > '9')
	cp	a, #0x39
	jrugt	00113$
	jp	_uart_putc
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 112: d = (uint8_t)(d + 7);         /* 'A' - '0' - 10 */
	add	a, #0x07
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 113: uart_putc((char)d);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 114: }
	jp	_uart_putc
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 116: static void uart_blk(const uint8_t *p, uint16_t n)
;	-----------------------------------------
;	 function uart_blk
;	-----------------------------------------
_uart_blk:
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 118: while (n--) {
00101$:
	ldw	y, (0x05, sp)
	ldw	(0x01, sp), y
	ldw	y, (0x05, sp)
	decw	y
	ldw	(0x05, sp), y
	ldw	y, (0x01, sp)
	jreq	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 119: uart_nib((uint8_t)(*p >> 4));
	ld	a, (x)
	swap	a
	and	a, #0x0f
	pushw	x
	call	_uart_nib
	popw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 120: uart_nib((uint8_t)(*p & 0x0F));
	ld	a, (x)
	and	a, #0x0f
	pushw	x
	call	_uart_nib
	popw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 121: p++;
	incw	x
	jra	00101$
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 123: }
	ldw	x, (3, sp)
	addw	sp, #6
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 126: static void stamp(uint8_t i)
;	-----------------------------------------
;	 function stamp
;	-----------------------------------------
_stamp:
	push	a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 128: tl[i] = TIM2_CNTRH;
	clrw	x
	ld	a, (0x01, sp)
	ld	xl, a
	addw	x, #(_tl+0)
	ld	a, 0x530c
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 129: tl[i + 1] = TIM2_CNTRL;
	ld	a, (0x01, sp)
	inc	a
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	ld	a, 0x530d
	ld	((_tl+0), x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 130: }
	pop	a
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 136: static void render_tick(void)
;	-----------------------------------------
;	 function render_tick
;	-----------------------------------------
_render_tick:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 138: uint16_t now = millis();
	call	_millis
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 139: if ((uint16_t)(now - last_render) >= 10) {
	ldw	y, x
	subw	y, _last_render+0
	cpw	y, #0x000a
	jrnc	00113$
	ret
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 140: last_render = now;
	ldw	_last_render+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 141: stamp(7);                     /* render START */
	pushw	x
	ld	a, #0x07
	call	_stamp
	popw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 142: anim_render(now);
	call	_anim_render
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 143: ws2812_out_send();            /* ~545 us, tick-masked inside */
	call	_ws2812_out_send
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 144: stamp(9);                     /* render END */
	ld	a, #0x09
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 146: }
	jp	_stamp
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 148: void main(void)
;	-----------------------------------------
;	 function main
;	-----------------------------------------
_main:
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 153: CLK_CKDIVR = 0x00;
	mov	0x50c6+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 154: CLK_HSITRIMR = 0x00;              /* factory == operating trim (code 0) */
	mov	0x50cc+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 156: TIM4_CR1  = 0x00;                 /* millis: /128, ARR 124 = 1 ms */
	mov	0x5340+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 157: TIM4_PSCR = 0x07;
	mov	0x5347+0, #0x07
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 158: TIM4_ARR  = 124;
	mov	0x5348+0, #0x7c
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 159: TIM4_SR   = 0x00;
	mov	0x5344+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 160: TIM4_IER  = 0x01;
	mov	0x5343+0, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 161: TIM4_CR1  = 0x01;
	mov	0x5340+0, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 163: TIM2_CR1  = 0x00;                 /* us timebase: /16 = 1 MHz, free run */
	mov	0x5300+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 164: TIM2_PSCR = 0x04;
	mov	0x530e+0, #0x04
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 165: TIM2_ARRH = 0xFF;
	mov	0x530f+0, #0xff
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 166: TIM2_ARRL = 0xFF;
	mov	0x5310+0, #0xff
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 167: TIM2_CR1  = 0x01;
	mov	0x5300+0, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 169: ws2812_out_init();
	call	_ws2812_out_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 171: __asm__("rim");
	rim
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 173: while (millis() < 5000)           /* SWIM reflash window: pin 8 quiet */
00101$:
	call	_millis
	cpw	x, #0x1388
	jrnc	00103$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 174: render_tick();
	call	_render_tick
	jra	00101$
00103$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 176: CFG_GCR = 0x01;
	mov	0x7f60+0, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 178: UART1_BRR2 = 0x01;                /* 38400: 16 MHz / 38400 = 0x1A1 */
	mov	0x5233+0, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 179: UART1_BRR1 = 0x1A;
	mov	0x5232+0, #0x1a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 180: UART1_CR2  = UART1_CR2_TEN;
	mov	0x5235+0, #0x08
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 181: uart_puts("RBARF-A 1\r\n");
	ldw	x, #(___str_0+0)
	call	_uart_puts
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 184: tl[12] = tl[5];               /* PREVIOUS arm return -> the unarmed */
	mov	_tl+12, _tl+5
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 185: tl[13] = tl[6];               /* gap ends at this arm's entry stamp */
	mov	_tl+13, _tl+6
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 186: render_tick();
	call	_render_tick
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 188: stamp(3);                     /* ARM ENTRY */
	ld	a, #0x03
	call	_stamp
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 194: __endasm;
	ldw x, #_capture_buf
	ldw y, #288
	call _cap_arm
	ld _cap_got, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 195: stamp(5);                     /* ARM RETURN */
	ld	a, #0x05
	call	_stamp
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 197: if (!cap_got) {
	ld	a, _cap_got+0
	jrne	00107$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 198: if (tl[11] != 0xFF)
	ldw	x, #(_tl+0)+11
	ld	a, (x)
	cp	a, #0xff
	jreq	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 199: tl[11]++;
	inc	a
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 200: continue;
	jra	00113$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 203: status = ws_decode_ex(capture_buf, CAP_BYTES, ws2812_in_buf);
	push	#<(_ws2812_in_buf+0)
	push	#((_ws2812_in_buf+0) >> 8)
	push	#0x20
	push	#0x01
	ldw	x, #(_capture_buf+0)
	call	_ws_decode_ex
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 204: eps = (dec_info.K != 0) ? dec_eps_centi() : 0;
	ldw	x, _dec_info+9
	tnzw	x
	jreq	00116$
	call	_dec_eps_centi
	.byte 0x21
00116$:
	clrw	x
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 205: tl[0] = (uint8_t)(((uint8_t)(status << 4)) | dec_info.cause);
	ld	a, (0x01, sp)
	swap	a
	and	a, #0xf0
	ld	(0x02, sp), a
	ld	a, _dec_info+1
	or	a, (0x02, sp)
	ld	_tl+0, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 206: tl[1] = (uint8_t)((uint16_t)eps >> 8);
	ld	a, xh
	ld	_tl+1, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 207: tl[2] = (uint8_t)((uint16_t)eps & 0xFFu);
	ld	a, xl
	ld	_tl+2, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 209: uart_putc('A');
	ld	a, #0x41
	call	_uart_putc
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 210: uart_blk(tl, 14);
	push	#0x0e
	push	#0x00
	ldw	x, #(_tl+0)
	call	_uart_blk
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 211: uart_puts("\r\n");
	ldw	x, #(___str_1+0)
	call	_uart_puts
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 213: nok++;
	inc	_nok+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 214: if (status == DEC_REFUSE || (nok & 3) == 0) {
	tnz	(0x01, sp)
	jreq	00108$
	ld	a, _nok+0
	bcp	a, #0x03
	jrne	00109$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 215: uart_putc('B');
	ld	a, #0x42
	call	_uart_putc
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 216: uart_blk(capture_buf, CAP_BYTES);
	push	#0x20
	push	#0x01
	ldw	x, #(_capture_buf+0)
	call	_uart_blk
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 217: uart_puts("\r\n");
	ldw	x, #(___str_1+0)
	call	_uart_puts
00109$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 219: tl[11] = 0;
	mov	_tl+11, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_arm/rbarf_arm.c: 221: }
	jp	00113$
	.area CODE
	.area CONST
	.area CONST
___str_0:
	.ascii "RBARF-A 1"
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
