; cap_arm.s -- production-only armed-capture entry (see the block
; comment below).  Lives in its OWN module so the bench build
; (rbarf_v21), whose CODE runs past 0x9F52, never links it: sdld does
; not check REL/ABS overlaps, so linking this into a build whose REL
; areas cross 0x9F52 corrupts flash silently -- the Makefile prod guard
; checks it.  Branches fall into scan.s's pinned _cap_loop (ABS 0x9FAF).

    .module cap_arm
    .globl _cap_arm
    .globl _cap_loop

; ---------------------------------------------------------------------------
; ROOT-CAUSE FIX 1 (PROD_CLOSURE.md SS7.4): the edge-detect polls below
; are BTJT branches into caploop.s's pinned sampling loop (ABS area
; CAPLOOP), which is a DIFFERENT ABS area from this one.  Written as the
; obvious `btjt 0x500B,#3,_cap_loop`, sdas defers the 1-byte PC-relative rel
; operand to an sdld "F1" relocation -- and sdld MIS-RELOCATES it: when two
; of these consecutive btjt PCR relocations pack into one .rel T-record,
; the FIRST of the pair is computed two bytes short.  The 3rd of the four
; identical polls linked to rel 0x1D (-> 0x9FAD) instead of 0x1F (-> 0x9FAF)
; while the other three were correct.  0x9FAD is mid-instruction (inside the
; wait_high btjf), so whenever the WS2812 rising edge happened to be caught
; on the 3rd poll (a frame-arrival-phase race, ~1 in 6 captures) the CPU
; branched into the middle of an instruction and took an ILLEGAL-OPCODE
; RESET (RST_SR ILLOPF 0x04).  That -- not the decoder -- is the "reset
; every ~6 decodes".  Bench-localised by a reset-surviving stage breadcrumb
; (all faults at the capture stage, never in decode) and by disassembling
; the linked image.
;
; The fix emits each BTJT as raw bytes with the rel computed ENTIRELY at
; assembly time from same-area quantities (see BTJT_CL below): no F1
; relocation is generated, so sdld never touches the offset and cannot
; corrupt it.  guard_prod.py additionally disassembles every poll in the
; linked image and fails the build unless each one lands exactly on the
; documented loop entry AND on an instruction boundary there.
;
; ---------------------------------------------------------------------------
; ROOT-CAUSE FIX 2 -- THE TRIGGER-PHASE CLIFF (ARM_INVESTIGATION.md SS3).
; The v2.3 production arm delivered 79.9 % against the capture firmware's
; 97.8 % on the same decoder, and 53 % of the refusals were `R3
; infeasible` on COMPLETE bursts with a perfect clock lock.  Measured
; cause: the fitted arm trigger phase t0 (rising edge -> first sample).
; The 8 sample slots of the pinned 40-cycle loop sit at
; [0, 250, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000] ns and the loop
; period is exactly 2 WS2812 bits, so the comb is phase-locked to bit
; PAIRS.  Slot 2 leaves the first bit period when
;     t0 >= BIT_NS - SLOT_OFFSET[2]/(1+eps)  =  681 ns at eps = -1.07 %,
; and at that instant the comb re-partitions across EVERY bit pair in the
; frame: the segment stream's hinge costs all shift off their boundaries
; and 459 of 461 segments go infeasible at once.  Swept on the host with
; t0 as the only variable (dev_arm/t0_sweep.py, shipped decoder):
; t0 <= 680 ns -> 0 R3 over 10 payloads; 690 ns -> first R3; >= 720 ns ->
; 100 % R3 at every payload out to 1300 ns.  No decoder change recovers
; it (GATE_INFEAS relaxed 20x recovers 0 of 280 cases) -- the information
; is never sampled.  The old arm measured t0 = 288..862 ns (p50 472) with
; 9.7 % of captures above the cliff; capture.ihx's blocking entry, which
; scores 97.8 %, measures 89..628 ns with 0 of 54 above it.
;
; Two zero-flash changes bring the tail back under the cliff:
;
;  (a) ENTER THE LOOP AT _cap_loop+1 (CL_R0), not _cap_loop.  The byte at
;      _cap_loop is the loop-top `rlc a` (0x49) that deposits the PREVIOUS
;      iteration's BS1 sample from C.  On the FIRST iteration there is no
;      previous iteration: byte 0 bits 7..6 of the capture are documented
;      garbage (cap_code.s) and no consumer reads them -- decode.c's
;      scanner takes loop i's slots 6,7 from byte i+1, so byte 0 bits 7..6
;      are unreachable, and the old arm already left C-junk there.
;      Skipping it costs one cycle less of t0 AND lands the branch on
;      0x9FB0, the first byte of a 32-bit flash word, instead of 0x9FAF,
;      the LAST byte of one: a taken branch to 0x9FAF fetches the word
;      0x9FAC..0x9FAF for a single 1-byte instruction and then stalls
;      again for the R0 poll, which is where the old arm's ~2 cycles of
;      fixed excess over the fall-through entry came from.  Slot 0 IS the
;      R0 poll, so the fitted slot offsets, W_CY[] branch costs and the
;      40-cycle period are all untouched: only t0 moves.
;
;  (b) RETIME THE POLL COMB.  The four polls are 2 cy apart and the loop
;      counter used to sit after the last of them, so the wrap gap was
;      2 (btjt) + 1 (dec) + 2 (jrne) = 5 cy: an edge landing there waited
;      up to 5 cy.  Moving `dec a` BETWEEN polls 3 and 4 splits that into
;      gaps of 2, 2, 3, 4 cy -- same instructions, same 11-cy period, same
;      59 bytes, one cycle less worst-case latency.  `dec` does not touch
;      C (the polls' flag) and BTJT does not touch Z (the counter's), so
;      the interleave is flag-safe; caploop.s depends on the same property.
;
; CAPLOOP itself is NOT touched: it stays byte-identical to the SS15.0
; ledger (md5 273e269f... / 9ddd0227...) and _cap_loop stays pinned at
; 0x9FAF, guard-asserted exactly.
;
; ---------------------------------------------------------------------------
; FIX 3 -- THE IDLE GATE (ARM_INVESTIGATION.md SS4, SS6 fix #3).  The old
; wait-low phase accepted a SINGLE low sample as "line idle", so an arm
; window that opened in the middle of a burst (the 5.56 %-duty render hole)
; triggered on the next MID-FRAME rising edge and captured a head-chopped
; partial burst: all 16 measured R1 refusals, plus 2 R3 and 1 R2, were
; chopped bursts of 11..476 bits of 479, and no chopped burst has ever
; decoded.  The gate below requires the line to read low for IDLE_N
; consecutive 5-cycle polls = 40 cy = 2.5 us, i.e. 2 full bit periods and
; ~2.9x the longest low inside a frame (T0L ~ 873 ns), before the edge
; window opens.  It recovers no frame -- a half-gone frame cannot be
; un-lost -- but it turns a doomed capture plus its decode window into a
; clean no-report.  Cost: 1 byte, and a 2.5-us blind slot per arm entry
; (0.2 % of the 1.2-ms arm cycle) in which an arriving edge is missed
; instead of being captured chopped: the same lost frame either way.
;
; ---------------------------------------------------------------------------
; FIX 4 -- THE COMB'S ADDRESS PHASE (ARM_INVESTIGATION.md SS10, the Lever-A
; phase).  SS6 fix #1 listed "re-phase CAPARM_ORG to shed the poll loop's
; fetch-stall cycles" as an UNTESTED zero-flash hypothesis, and SS9 set it
; aside because the arm's fixed excess turned out to live at the branch
; DESTINATION (FIX 2a), which re-phasing cannot move.  That reasoning is
; correct about the MEAN and wrong about the SPREAD: re-phasing moves the
; four polls relative to the 32-bit flash words they are fetched from, and
; that is what sets how the comb's ~3 cycles of fetch stall distribute
; across its 2/2/3/4-cy gaps -- i.e. the worst-case edge-detect latency,
; i.e. the WIDTH of the t0 distribution.
;
; Measured on silicon with the SS1 diagnostic image (dev_arm/rbarf_arm.c,
; which differs from this arm in exactly the 4 s_arm operand bytes), all
; four mod-4 comb phases, identical protocol (2 runs x 240 frames of the
; 10 production payloads, dithered + strict cadence):
;
;   CAPARM_ORG  mod4   n    sd     IQR    p95    max   t0>=650   cliff margin
;   0x9F65 (old)  1  137  138 ns  184 ns  612    680     2.9 %      1 ns
;   0x9F64        0   48  109 ns  127 ns  523    580     0.0 %    101 ns
;   0x9F63 (this) 3  134  100 ns  133 ns  570    658     1.5 %     23 ns
;   0x9F62        2   46   98 ns  117 ns  538    615     0.0 %     66 ns
;
; 0x9F63 confirmed at full n against the old address, same session, same
; die: sd 138.3 -> 100.2 ns, -28 %, F(136,133) = 1.91, p = 0.0001, with the
; MEDIAN UNMOVED (354 -> 354 ns).  It is a pure narrowing, which is what
; the arm needed: the accept-rate-vs-t0 curve measured on the production
; payload mix is FLAT from 20 ns to ~620 ns (90.7 / 93.8 / 91.7 / 92.0 % in
; the 0-102 / 102-250 / 250-450 / 450-650 ns bands) and then rolls off into
; the 681 ns cliff, so there is no phase "sweet spot" to centre on and the
; only thing worth buying is DISTANCE FROM THE CLIFF.  Narrowing bought it:
; cliff margin at the observed max 1 ns -> 23 ns, at p95 69 -> 112 ns.
;
; DO NOT "centre" this distribution upward.  Shifting t0 UP is measurably
; harmful: convolving the measured silicon t0 distribution with the
; measured accept curve gives -2.3 pp at +0.5 cy and -3.1 pp at +1 cy
; (3.6 % of frames land above the cliff), and the pre-SS9 arm -- which sat
; ~2-3 cy higher -- had 9.7 % above the cliff and 42 complete-burst R3
; refusals.  The optimum is at -1 cy; re-phasing cannot shift the mean, so
; the narrowing is what is available at zero flash cost.
;
; COST: 0 bytes of arm code (same 60 B, same instructions, same cycle
; counts -- only the .org moves) and 2 bytes of REL headroom, because the
; arm no longer sits flush under _cap_capture: 0x9F63 + 60 = 0x9F9F leaves
; 0x9F9F..0x9FA0 unprogrammed (0xFF, unreachable -- the arm's last
; instruction is `ret`).  Terse image free flash 36 -> 34 B, verbose
; 40 -> 38 B.  CAPLOOP is untouched and byte-identical to the SS15.0
; ledger.  CAPARM_ORG IS NOW A CALIBRATED TIMING QUANTITY, not a free
; placement choice: guard_prod.py pins it exactly, like _cap_loop.
;
; CL_ENT is pinned by caploop.s's .org and guard-enforced EXACTLY (not just
; mod 16); CAPARM_ORG must equal this area's .org.
CL_ENT     = 0x9FAF                  ; == _cap_loop  (guard-asserted exact)
CL_R0      = 0x9FB0                  ; == _cap_loop+1, the R0 poll: THE
                                     ; entry (see FIX 2a); guard-asserted
CAPARM_ORG = 0x9F63                  ; == this area's .org (below);
                                     ; CALIBRATED (FIX 4) -- mod-4
                                     ; comb phase 3, guard-pinned
IDLE_N     = 8                       ; low polls required: 8 x 5 cy = 2.5 us

; BTJT_R0: `btjt 0x500B, #3, CL_R0` with the rel resolved locally.
;   0x72,0x06 = BTJT #3 ; 0x50,0x0B = longmem 0x500B ; then the signed rel.
;   rel = CL_R0 - (PC after this 5-byte insn).  (. - _cap_arm) is a pure
;   in-area offset (constant), so the whole expression reduces to an
;   absolute constant at assembly time -- no relocation record.
.macro BTJT_R0
    .db 0x72, 0x06, 0x50, 0x0B
    .db (CL_R0 - (CAPARM_ORG + (. - _cap_arm) + 1))
.endm

    .area DATA
s_arm:      .ds 1       ; _cap_arm outer timeout counter

; ======================================================================
; _cap_arm -- production armed capture: wait (bounded) for the line to be
; IDLE, then (bounded) for a rising edge on PC3, then fall into the SAME
; pinned sampling loop at its R0 poll (CL_R0).
; Entry: X = capture buffer, Y = loop count (288 production).
; Return: A = 1 captured, A = 0 no frame / line busy in this window.
; Preserves X and Y for the sampling loop; clobbers A and C.
;
; Trigger-phase discipline (the reason this code is shaped this way):
; see FIX 2 above.  The poll comb runs at 2 cy with gaps 2/2/3/4 cy and
; enters the loop through a taken btjt onto the word-aligned R0 poll.
; Interrupts are masked per 176-us burst (sim..rim), so the TIM4 millis
; tick is never lost while armed; a burst that flows into a capture
; (~720 us at 288 loops) can swallow at most one 1-ms tick per captured
; frame.
;
; Timeout: idle gate 8 x ~5 cy per try x 8 tries (~5 us, then the caller
; re-arms), edge wait 7 x 176 us = 1.23 ms, then A=0 so the caller can run
; its render.
; ======================================================================
    .area CAPARM (ABS)
    .org CAPARM_ORG
_cap_arm:
    mov     s_arm, #8               ; busy-line retry budget
00060$:                             ; ---- idle gate: IDLE_N lows ----
    ld      a, #IDLE_N
00061$:
    btjt    0x500B, #3, 00065$      ; HIGH -> line busy (mid-burst)
    dec     a                       ; 5 cy per low poll
    jrne    00061$
                                    ; ---- line idle: open the window ----
    mov     s_arm, #7               ; edge window: 7 x 176 us = 1.23 ms
00063$:
    sim                             ; mask one 176-us poll burst
    clr     a
00064$:
    BTJT_R0                         ; poll 1   gap to poll 2: 2 cy
    BTJT_R0                         ; poll 2   gap to poll 3: 2 cy
    BTJT_R0                         ; poll 3   gap to poll 4: 3 cy
    dec     a                       ; counter INSIDE the comb (FIX 2b)
    BTJT_R0                         ; poll 4   gap to poll 1: 4 cy
    jrne    00064$                  ; 256 x 11 cy = 176 us
    rim                             ; pending TIM4 tick delivers here
    dec     s_arm
    jrne    00063$
    clr     a                       ; no frame in the window
    ret
00065$:                             ; line busy: retry the idle gate
    dec     s_arm
    jrne    00060$
    clr     a                       ; still busy: let the caller re-arm
    ret
