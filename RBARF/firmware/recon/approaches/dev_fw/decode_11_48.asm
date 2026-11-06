;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module decode
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _g_CHK
	.globl _g_NPP
	.globl _g_ND8
	.globl _g_ND
	.globl _g_PPHI
	.globl _g_NBm32
	.globl _g_Wu11
	.globl _g_ymid
	.globl _g_yend
	.globl _g_NB
	.globl _ov
	.globl _g_tau
	.globl _g_K
	.globl _dec_info
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_dec_info::
	.ds 20
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
	.dw #0x01d8
	.area CODE
	.area CONST
_g_yend:
	.byte #0x00, #0x03, #0xb2, #0xa4	; 242340
	.area CODE
	.area CONST
_g_ymid:
	.byte #0x00, #0x01, #0xda, #0x00	; 121344
	.area CODE
	.area CONST
_g_Wu11:
	.byte #0x1d, #0x79, #0xa0, #0x00	; 494510080
	.area CODE
	.area CONST
_g_NBm32:
	.dw #0x01b8
	.area CODE
	.area CONST
_g_PPHI:
	.dw #0x01b8
	.area CODE
	.area CONST
_g_ND:
	.dw #0x0030
	.area CODE
	.area CONST
_g_ND8:
	.dw #0x0180
	.area CODE
	.area CONST
_g_NPP:
	.dw #0x0033
	.area CODE
	.area CONST
_g_CHK:
	.db #0x03	; 3
	.area CODE
	.area INITIALIZER
	.area CABS (ABS)
