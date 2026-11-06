;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module sim_main2
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _main
	.globl _done
	.globl _ws_decode
	.globl _result
	.globl _payload
	.globl _cap_buf
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_cap_buf::
	.ds 256
_payload::
	.ds 48
_result::
	.ds 1
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
;	sim_main2.c: 8: void done(void) { __asm__("halt"); for (;;) ; }
;	-----------------------------------------
;	 function done
;	-----------------------------------------
_done:
	halt
00103$:
	jra	00103$
	ret
;	sim_main2.c: 9: void main(void)
;	-----------------------------------------
;	 function main
;	-----------------------------------------
_main:
	sub	sp, #4
;	sim_main2.c: 12: for (i = 0; i < 256; i++) cap_buf[i] = test_cap[i];
	ldw	y, #_cap_buf+0
	clrw	x
	ldw	(0x03, sp), x
00102$:
	ldw	x, y
	addw	x, (0x03, sp)
	ldw	(0x01, sp), x
	ldw	x, (0x03, sp)
	ld	a, (_test_cap+0, x)
	ldw	x, (0x01, sp)
	ld	(x), a
	ldw	x, (0x03, sp)
	incw	x
	ldw	(0x03, sp), x
	cpw	x, #0x0100
	jrc	00102$
;	sim_main2.c: 13: g_phases = PHASES;
	mov	_g_phases+0, #0x05
;	sim_main2.c: 14: result = ws_decode(cap_buf, 256, payload);
	ldw	x, y
	push	#<(_payload+0)
	push	#((_payload+0) >> 8)
	push	#0x00
	push	#0x01
	call	_ws_decode
	ld	_result+0, a
;	sim_main2.c: 15: done();
	addw	sp, #4
;	sim_main2.c: 16: }
	jp	_done
	.area CODE
	.area CONST
	.area INITIALIZER
	.area CABS (ABS)
