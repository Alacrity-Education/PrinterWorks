; vectors_sim.s -- reset vector for the ASMDEC ucsim harness image.
;
; decode_asm.s relocates helpers into the vector-table gap (area VGAP,
; ABS 0x8004..0x8063), so the harness must link with --code-loc 0x8068
; exactly like the production image -- sdld does NOT check REL/ABS
; overlaps, and linking without it puts SDCC's GSINIT at 0x8004 where
; the VGAP bytes clobber it (found 2026-09-06: every ASMDEC sim ran the
; mediv/udiv32 bytes as its own startup, escaped to the zero page, and
; trashed RAM for the rest of the 45 s window -- reads then mismatched).
; With --code-loc 0x8068 SDCC's own vector table sits at 0x8068 and the
; real 0x8000 reset slot would be empty: this module supplies it.
    .module vecsim

    .globl s_GSINIT

    .area VECT (ABS)
    .org 0x8000
    int s_GSINIT            ; RESET -> runtime init (only vector the sim uses)
