;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module nodec
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _ws_decode
	.globl _g_phases
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_g_phases::
	.ds 1
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area INITIALIZED
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
; global & static initialisations
;--------------------------------------------------------
	.area HOME
	.area GSINIT
	.area GSFINAL
	.area GSINIT
;--------------------------------------------------------
; Home
;--------------------------------------------------------
	.area HOME
	.area HOME
;--------------------------------------------------------
; code
;--------------------------------------------------------
	.area CODE
;	nodec.c: 3: uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out)
;	-----------------------------------------
;	 function ws_decode
;	-----------------------------------------
_ws_decode:
;	nodec.c: 4: { (void)cap; (void)ncap; (void)out; return 0; }
	clr	a
	ldw	x, (1, sp)
	addw	sp, #6
	jp	(x)
	.area CODE
	.area CONST
	.area INITIALIZER
	.area CABS (ABS)
