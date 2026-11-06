                                      1 ; cap_arm.s -- production-only armed-capture entry (see the block
                                      2 ; comment below).  Lives in its OWN module so the bench build
                                      3 ; (rbarf_v21), whose CODE runs past 0x9F52, never links it: sdld does
                                      4 ; not check REL/ABS overlaps, so linking this into a build whose REL
                                      5 ; areas cross 0x9F52 corrupts flash silently -- the Makefile prod guard
                                      6 ; checks it.  Branches fall into scan.s's pinned _cap_loop (ABS 0x9FAF).
                                      7 
                                      8     .module cap_arm
                                      9     .globl _cap_arm
                                     10     .globl _cap_loop
                                     11 
                                     12 ; ---------------------------------------------------------------------------
                                     13 ; ROOT-CAUSE FIX (PROD_CLOSURE.md SS7.4): the four edge-detect polls below
                                     14 ; are BTJT branches into caploop.s's pinned sampling loop _cap_loop (ABS
                                     15 ; 0x9FAF), which lives in a DIFFERENT ABS area (CAPLOOP).  Written as the
                                     16 ; obvious `btjt 0x500B,#3,_cap_loop`, sdas defers the 1-byte PC-relative rel
                                     17 ; operand to an sdld "F1" relocation -- and sdld MIS-RELOCATES it: when two
                                     18 ; of these consecutive btjt PCR relocations pack into one .rel T-record,
                                     19 ; the FIRST of the pair is computed two bytes short.  The 3rd of the four
                                     20 ; identical polls linked to rel 0x1D (-> 0x9FAD) instead of 0x1F (-> 0x9FAF)
                                     21 ; while the other three were correct.  0x9FAD is mid-instruction (inside the
                                     22 ; wait_high btjf), so whenever the WS2812 rising edge happened to be caught
                                     23 ; on the 3rd poll (a frame-arrival-phase race, ~1 in 6 captures) the CPU
                                     24 ; branched into the middle of an instruction and took an ILLEGAL-OPCODE
                                     25 ; RESET (RST_SR ILLOPF 0x04).  That -- not the decoder -- is the "reset
                                     26 ; every ~6 decodes".  Bench-localised by a reset-surviving stage breadcrumb
                                     27 ; (all faults at the capture stage, never in decode) and by disassembling
                                     28 ; the linked image.
                                     29 ;
                                     30 ; The fix emits each BTJT as raw bytes with the rel computed ENTIRELY at
                                     31 ; assembly time from same-area quantities (see BTJT_CL below): no F1
                                     32 ; relocation is generated, so sdld never touches the offset and cannot
                                     33 ; corrupt it.  The emitted bytes are byte-identical to a correctly-linked
                                     34 ; `btjt 0x500B,#3,_cap_loop`, so cadence, cycle count and every address are
                                     35 ; unchanged -- the calibrated capture timing is preserved exactly.
                                     36 ;
                                     37 ; _cap_loop is pinned at CL_ENT (0x9FAF) by caploop.s's .org and is now
                                     38 ; guard-enforced EXACTLY (not just mod 16); CAPARM_ORG must equal this
                                     39 ; area's .org.  guard_prod.py additionally disassembles the four polls in
                                     40 ; the linked image and fails the build unless every one targets _cap_loop.
                           009FAF    41 CL_ENT     = 0x9FAF                  ; == _cap_loop (guard-asserted exact)
                           009F66    42 CAPARM_ORG = 0x9F66                  ; == this area's .org (below)
                                     43 
                                     44 ; BTJT_CL: `btjt 0x500B, #3, _cap_loop` with the rel resolved locally.
                                     45 ;   0x72,0x06 = BTJT #3 ; 0x50,0x0B = longmem 0x500B ; then the signed rel.
                                     46 ;   rel = CL_ENT - (PC after this 5-byte insn).  (. - _cap_arm) is a pure
                                     47 ;   in-area offset (constant), so the whole expression reduces to an
                                     48 ;   absolute constant at assembly time -- no relocation record.
                                     49 .macro BTJT_CL
                                     50     .db 0x72, 0x06, 0x50, 0x0B
                                     51     .db (CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1))
                                     52 .endm
                                     53 
                                     54     .area DATA
      000246                         55 s_arm:      .ds 1       ; _cap_arm outer timeout counter
                                     56 
                                     57 ; ======================================================================
                                     58 ; _cap_arm -- production armed capture: wait (bounded) for a rising edge
                                     59 ; on PC3, then fall into the SAME pinned sampling loop (_cap_loop below).
                                     60 ; Entry: X = capture buffer, Y = loop count (288 production).
                                     61 ; Return: A = 1 captured, A = 0 timeout (no frame in the window).
                                     62 ;
                                     63 ; Trigger-phase discipline (the reason this code is shaped this way):
                                     64 ; the fitted model's t0 (edge -> first sample) was measured 254..501 ns
                                     65 ; behind _cap_capture's 3-cy btjf poll.  This arm loop polls at 2 cy
                                     66 ; (btjt not taken), with a 5-cy slot once per 256 polls (inner counter)
                                     67 ; and a 10-cy slot once per 304 us (outer counter + rim/sim window), and
                                     68 ; enters the loop via a taken btjt (3 cy vs the original's 2-cy btjf
                                     69 ; fall-through).  Worst common-case t0 grows by ~3 cy (~190 ns), keeping
                                     70 ; the first FF pulse (T1H_eff 752 ns) inside the first sample at nominal
                                     71 ; trim.  Interrupts are masked per 304-us burst (sim..rim), so the TIM4
                                     72 ; millis tick is never lost while armed; a burst that flows into a
                                     73 ; capture (~720 us at 288 loops) can swallow at most one 1-ms tick per
                                     74 ; captured frame.
                                     75 ;
                                     76 ; Timeout: wait-low phase ~0.4 ms (stuck-high guard), edge wait
                                     77 ; 4 x 304 us = 1.2 ms, then A=0 so the caller can run its 100 Hz render.
                                     78 ; ======================================================================
                                     79     .area CAPARM (ABS)
      009F66                         80     .org CAPARM_ORG
      009F66                         81 _cap_arm:
      009F66 35 02 02 46      [ 1]   82     mov     s_arm, #2
      009F6A 4F               [ 1]   83     clr     a
      009F6B                         84 00060$:                             ; wait for idle low (coarse, ~5 cy)
      009F6B 72 07 50 0B 0B   [ 2]   85     btjf    0x500B, #3, 00062$
      009F70 4A               [ 1]   86     dec     a
      009F71 26 F8            [ 1]   87     jrne    00060$
      009F73 72 5A 02 46      [ 1]   88     dec     s_arm
      009F77 26 F2            [ 1]   89     jrne    00060$
      009F79 4F               [ 1]   90     clr     a                       ; line stuck high: give up
      009F7A 81               [ 4]   91     ret
      009F7B                         92 00062$:
      009F7B 35 07 02 46      [ 1]   93     mov     s_arm, #7               ; edge window: 7 x 176 us = 1.2 ms
      009F7F                         94 00063$:
      009F7F 9B               [ 1]   95     sim                             ; mask one 176-us poll burst
      009F80 4F               [ 1]   96     clr     a
      009F81                         97 00064$:
      009F81                         98     BTJT_CL                         ; 4 polls, 2 cy apart; a taken btjt
      009F81 72 06 50 0B              1     .db 0x72, 0x06, 0x50, 0x0B
      009F85 29                       2     .db (CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1))
      009F86                         99     BTJT_CL                         ; drops straight into the pinned
      009F86 72 06 50 0B              1     .db 0x72, 0x06, 0x50, 0x0B
      009F8A 24                       2     .db (CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1))
      009F8B                        100     BTJT_CL                         ; sampling loop with C = 1 (the bit
      009F8B 72 06 50 0B              1     .db 0x72, 0x06, 0x50, 0x0B
      009F8F 1F                       2     .db (CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1))
      009F90                        101     BTJT_CL                         ; just read) like the original exit
      009F90 72 06 50 0B              1     .db 0x72, 0x06, 0x50, 0x0B
      009F94 1A                       2     .db (CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1))
      009F95 4A               [ 1]  102     dec     a
      009F96 26 E9            [ 1]  103     jrne    00064$
      009F98 9A               [ 1]  104     rim                             ; pending TIM4 tick delivers here
      009F99 72 5A 02 46      [ 1]  105     dec     s_arm
      009F9D 26 E0            [ 1]  106     jrne    00063$
      009F9F 4F               [ 1]  107     clr     a                       ; no frame in the window
      009FA0 81               [ 4]  108     ret
                                    109 
