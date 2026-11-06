;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module sim_v2
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _main
	.globl _ws_decode_ex
	.globl _g_out
	.globl _g_status
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_g_status::
	.ds 1
_g_out::
	.ds 16
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 19: static void sim_done(void) { __asm__("halt"); for (;;) ; }
;	-----------------------------------------
;	 function sim_done
;	-----------------------------------------
_sim_done:
	halt
00103$:
	jra	00103$
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 21: void main(void)
;	-----------------------------------------
;	 function main
;	-----------------------------------------
_main:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 23: g_status = ws_decode_ex(CAP, CAP_LEN, g_out);
	ldw	x, _CAP_LEN+0
	push	#<(_g_out+0)
	push	#((_g_out+0) >> 8)
	pushw	x
	ldw	x, #(_CAP+0)
	call	_ws_decode_ex
	ld	_g_status+0, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 24: sim_done();
;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 25: }
	jp	_sim_done
	.area CODE
	.area CONST
	.area INITIALIZER
	.area CABS (ABS)
