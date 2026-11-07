; vectors_prod.s -- hand-packed STM8S001J3 vector table for the
; PRODUCTION image.  Only two vectors are real: RESET and IRQ23 (TIM4
; update, the millis tick -- the only interrupt source the firmware ever
; enables).  The TRAP..IRQ22 window (0x8004..0x8063, 96 bytes) is dead
; space in a conventional table; here it holds relocated decoder
; routines (decode_asm.s area VGAP), worth 88 B of the flash budget.
; RISK (documented): a spurious interrupt 0..22 or TRAP would execute
; table bytes as a vector -- acceptable because no such source is ever
; enabled and TRAP is never executed; revert to a full table if that
; changes.
;
; Requires --code-loc 0x8068 so SDCC's REL areas start above the table
; (guard_prod.py checks); SDCC's own 4-byte reset stub at 0x8068 is dead.

    .module vecprod

    .globl s_GSINIT
    .globl _tim4_upd_isr

    .area VECT (ABS)
    .org 0x8000
    int s_GSINIT            ; 0x8000  RESET -> runtime init

    .org 0x8064
    int _tim4_upd_isr       ; 0x8064  IRQ23  TIM4 update = millis tick
