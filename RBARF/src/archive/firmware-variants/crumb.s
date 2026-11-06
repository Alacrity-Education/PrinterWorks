; crumb.s -- bench-only breadcrumb + reset-cause survival cells.
; ABS RAM area at 0x0360 (just above DATA end 0x035E, at the DEEP end of
; the stack region 0x0360..0x03FF -- 46+ B below the measured stack
; low-water 0x038E, so a normal run never touches it).  NOT the DATA
; area, so SDCC crt0's DATA clear loop leaves it intact across a warm
; (illegal-opcode) reset -- the value written last before the fault
; survives to be reported at the next boot.
    .module crumb
    .globl _crumb
    .globl _crumb_sub
    .globl _crumb_magic

    .area CRUMB (ABS)
    .org 0x0360
_crumb:       .ds 1      ; coarse stage code (0x10 render .. 0x50 post-decode)
_crumb_sub:   .ds 1      ; fine sub-stage / cap_got / cause
_crumb_magic: .ds 2      ; 0xC0DE once the firmware has run at least once
