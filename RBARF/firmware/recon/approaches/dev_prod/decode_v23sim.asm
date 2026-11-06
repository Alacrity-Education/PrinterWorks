;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module decode
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _g_TRB
	.globl _g_PPE
	.globl _g_PPB
	.globl _g_TIEE
	.globl _g_ND8
	.globl _g_PPHI
	.globl _g_NBmHT
	.globl _g_Wu11
	.globl _g_ymid
	.globl _g_yend
	.globl _g_NB
	.globl _ov
	.globl _g_tau
	.globl _g_K
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_g_K::
	.ds 2
_g_tau::
	.ds 2
_ov::
	.ds 128
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
	.area CODE
	.area CONST
	.area CONST
_g_NB:
	.dw #0x01e0
	.area CODE
	.area CONST
_g_yend:
	.byte #0x00, #0x03, #0xc2, #0xa4	; 246436
	.area CODE
	.area CONST
_g_ymid:
	.byte #0x00, #0x01, #0xe2, #0x00	; 123392
	.area CODE
	.area CONST
_g_Wu11:
	.byte #0x1d, #0xf9, #0xa0, #0x00	; 502898688
	.area CODE
	.area CONST
_g_NBmHT:
	.dw #0x01c8
	.area CODE
	.area CONST
_g_PPHI:
	.dw #0x01c8
	.area CODE
	.area CONST
_g_ND8:
	.dw #0x0180
	.area CODE
	.area CONST
_g_TIEE:
	.dw #0x01b1
	.area CODE
	.area CONST
_g_PPB:
	.dw #0x003c
	.area CODE
	.area CONST
_g_PPE:
	.dw #0x006c
	.area CODE
	.area CONST
_g_TRB:
	.dw #0x0039
	.area CODE
	.area INITIALIZER
	.area CABS (ABS)
