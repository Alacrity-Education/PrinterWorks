/*
 * ============================================================================
 *  rbarf_capture.c -- the RBARF capture FRONT END, written to be READ
 * ============================================================================
 *
 *  rbarf_decoder.c is the second half of the job: it turns a smeared,
 *  warped picture of a WS2812 wire back into exact bytes.  This file is
 *  the FIRST half -- the instrument that takes the picture.
 *
 *  There is not much of it.  Two hand-written assembly routines, 140 bytes
 *  of flash between them, pinned to fixed addresses at the very top of an
 *  8 KB part:
 *
 *      cap_arm.s   0x9F63..0x9F9E   60 B  wait for the line to be idle,
 *                                         then for a rising edge, then jump
 *      caploop.s   0x9FA1..0x9FF0   80 B  read the pin 8 times every 40
 *                                         cycles and store one byte a loop
 *
 *  and yet almost every hard-won number in the project is a property of
 *  these 140 bytes: the 40-cycle loop period, the eight sample instants,
 *  the dead zone that swallows 0-bits, the 681 ns trigger-phase cliff, and
 *  a data-dependent term that makes the sampler literally speed up and slow
 *  down depending on what it is looking at.  Two of the project's three
 *  worst bugs lived here (an illegal-opcode reset every ~6 decodes, and a
 *  7 % clock-measurement error) and both were caused by MOVING CODE.
 *
 *  ---------------------------------------------------------------------------
 *  THE TWO LAYERS IN THIS FILE, AND WHY THERE HAVE TO BE TWO
 *  ---------------------------------------------------------------------------
 *
 *  LAYER 1, sections 2 and 3: a LINE-FOR-LINE rendering of the two assembly
 *  routines.  One C statement per STM8 instruction, each carrying the
 *  instruction and its cycle count in a trailing comment, so a reader can
 *  add the numbers up and see the 40-cycle loop, the eight sample instants,
 *  the per-slot gaps and the arm's 11-cycle poll comb for themselves.  It is
 *  executable -- give it an oracle that answers "what does PC3 read now?"
 *  and it produces capture bytes -- which is what lets section 7 PROVE that
 *  the loop's chain of RLC A instructions packs its eight samples into
 *  memory exactly the way the model's packer says it does.
 *
 *  LAYER 2, sections 4 to 6: a host-executable model of the SAMPLER AS AN
 *  INSTRUMENT.  Feed it a wire waveform, an oscillator error and an arm
 *  phase; it returns the bytes the STM8 would have written.  This is the
 *  layer that is proven byte-for-byte against the normative Python sampler
 *  (reference/parity_capture.py).
 *
 *  THE REASON THEY CANNOT BE ONE LAYER, and the single most important fact
 *  in this file: **this C can never run on the STM8 with the right timing,
 *  and neither can any other C.**  Three independent reasons, in increasing
 *  order of how much trouble they caused:
 *
 *    1. A compiler picks its own instructions.  The loop's timing is not a
 *       property of an algorithm, it is a property of a specific 80-byte
 *       instruction sequence.  `for (s = 0; s < 8; s++) sample();` is
 *       already a different program.
 *
 *    2. The sampling instants are not uniform, and the non-uniformity is
 *       load-bearing.  Eight samples per loop at gaps of 4, 5, 4, 4, 4, 6,
 *       5 and 8 cycles -- because six of them are cheap (BTJT/NOP/RLC A)
 *       and two of them straddle the loop's bookkeeping.  A reader who
 *       assumes "eight evenly spaced samples" gets the decoder's
 *       segmentation stage wrong by a whole bit.
 *
 *    3. **ADDRESS PHASE IS TIMING.**  The loop's real period includes
 *       flash-fetch stalls that depend on where in flash the instructions
 *       sit.  This is measured, not theorised: linked as ordinary
 *       relocatable code the loop landed at 0x9E1E -- phase 0 mod 4 instead
 *       of 1 -- and there it really ran the DOCUMENTED ~37 cycles with no
 *       stalls, so every bench decode measured the oscillator error at
 *       +6.2..+7.5 % instead of this unit's -1.07 %.  0.9893 * 40/37 - 1 =
 *       +6.95 %: the observed shift, exactly.  So the loop lives in an
 *       absolute area at 0x9FA1 == 0x8111 (mod 16), reproducing the address
 *       phase of the acquisition image the model was FITTED against, and
 *       guard_prod.py fails the build if it ever moves.  The same effect,
 *       one level down, is why cap_arm.s's own .org is a calibrated
 *       constant: its mod-4 phase decides how the poll comb's ~3 cycles of
 *       fetch stall distribute across the comb's 2/2/3/4-cycle gaps, which
 *       sets the WIDTH of the arm's trigger-phase distribution.
 *
 *  So layer 1 is a rendering to read, not a program to run on the target,
 *  and layer 2 is a model of an instrument that was MEASURED, not derived.
 *  The 40 cycles are not an instruction-count sum -- the instruction-count
 *  sum is 37 and it is wrong.  They were fitted to 54 real captures.
 *
 *  ---------------------------------------------------------------------------
 *  THE FILE, IN ORDER
 *  ---------------------------------------------------------------------------
 *    0  the STM8 vocabulary: the eight instructions both routines use
 *    1  the pinned addresses, and what each one is calibrated to
 *    2  LAYER 1: cap_arm.s, line for line     (idle gate, poll comb, jump)
 *    3  LAYER 1: caploop.s, line for line     (the 40-cycle sampling loop)
 *    4  LAYER 2: the wire        (bits + T0H/T1H/period, or an edge list)
 *    5  LAYER 2: the fitted sampler, and the capture byte layout
 *    6  LAYER 2: the malformations that real arms produce (chop/trunc/drift)
 *    7  the self-checks: the equivalences this file can actually prove
 *    8  a demo main()
 *
 *  ---------------------------------------------------------------------------
 *  WHAT IS DELIBERATELY NOT HERE
 *  ---------------------------------------------------------------------------
 *    the decoder            rbarf_decoder.c, which CONSUMES these bytes.
 *    the output driver      rbarf_ws2812_out.c (the bit-banged transmitter,
 *                           the other end of the same wire).
 *    the vector table       rbarf_vectors.c.
 *    METASTABILITY          a GPIO input read exactly at an edge.  The
 *                           model resolves every sample to a clean 0 or 1
 *                           from the ideal waveform; silicon has a window
 *                           of a few hundred picoseconds in which the
 *                           latched value is genuinely undefined.  Sample
 *                           agreement against real captures is 99.96 %, so
 *                           whatever this costs is inside that 0.04 %.
 *    OSCILLATOR JITTER      `eps` is a single static number per capture
 *                           plus, optionally, one linear ramp.  A real RC
 *                           oscillator has cycle-to-cycle jitter and a
 *                           temperature coefficient; the fit found the
 *                           per-capture spread across the corpus to be only
 *                           +-0.014 %, so a static eps per capture is a
 *                           very good approximation over 600 us and a bad
 *                           one over minutes.
 *    TRANSMITTER IMPERFECTION  the wire is treated as exact: a crystal
 *                           timebase, instant edges, no ringing, no
 *                           transmission-line effects.  The fitted +2 ns
 *                           common edge shift (752/377 instead of 750/375)
 *                           is the one place reality was allowed in.
 *    INTERRUPTS DURING CAPTURE  cannot happen -- the arm masks them
 *                           (sim..rim) for the whole burst -- so there is
 *                           nothing to model.
 *    THE ARM'S OWN TIMING   layer 2 starts at the first sample: `t0_ns` IS
 *                           the arm's contribution, as one input number.
 *                           How the arm's fetch stalls produce the
 *                           distribution that t0 is drawn from is measured
 *                           on silicon, not modelled here.
 *    byte 0's top two bits  the model writes 0; the hardware writes the low
 *                           two bits of the arm's burst counter there.
 *                           Section 5 explains why that is provably
 *                           harmless, and it is the ONE known byte-level
 *                           difference between this model and silicon.
 */

#include "rbarf_capture.h"

#include <math.h>       /* fmod -- see the note in section 5 on why        */
#include <string.h>     /* memcpy / memmove / memset only                 */

/* ==========================================================================
 *  SECTION 0 -- THE STM8 VOCABULARY
 * ==========================================================================
 *
 *  Between them, cap_arm.s and caploop.s use nine instructions.  That is
 *  the whole language, and the cycle costs below are the ones the two
 *  routines' own comments do their arithmetic with.
 *
 *   instruction          bytes  cycles  what it does
 *   -------------------- -----  ------  ------------------------------------
 *   BTJT longmem,#b,rel    5     2 / 3  Bit Test and Jump if True.  Reads
 *                                       the byte, copies bit b INTO CARRY,
 *                                       and branches if it was 1.  2 cycles
 *                                       not taken, 3 taken.  **The carry
 *                                       side effect is the whole trick**:
 *                                       it is how a sample gets from the
 *                                       pin into a register.  BTJT does not
 *                                       touch Z.
 *   BTJF longmem,#b,rel    5     2 / 3  same, branch if the bit was 0.
 *   RLC A                  1       1    rotate A left THROUGH carry:
 *                                       A = (A<<1) | C, C = old bit 7.
 *                                       Shifts the sample just latched by
 *                                       BTJT into the byte being built.
 *   NOP                    1       1    cycle balance, nothing else.
 *   LD (X),A               1       1    store the finished byte.
 *   INCW X                 1       1    advance the buffer pointer.
 *   DECW Y                 2       1    loop counter; sets Z.
 *   DEC A / DEC longmem  1 / 4     1    counters.  DEC does not touch C.
 *   JRNE rel               2     1 / 2  1 cycle not taken, 2 taken.
 *   MOV longmem,#imm       4       1    set a RAM counter.
 *   SIM / RIM              1       1    mask / unmask interrupts.
 *   RET                    1       4    return.
 *
 *  TWO FLAG FACTS CARRY THE WHOLE DESIGN, and both routines depend on them:
 *
 *    * BTJT / BTJF write C and leave Z alone.
 *    * DEC / DECW write Z and leave C alone.
 *
 *  That is why the sampling loop can interleave its pin polls (which live
 *  in C) with its loop counter (which lives in Z) and still have JRNE at
 *  the bottom test the DECW from six instructions earlier; and it is why
 *  cap_arm.s can put `dec a` in the MIDDLE of its four-poll comb to even
 *  out the gaps.  Neither routine has a spare cycle to save a flag in.
 *
 *  A BALANCED SAMPLE COSTS THE SAME WHATEVER IT READS -- by construction.
 *  Each sample site is
 *
 *        BTJT PC_IDR, #3, skip     ; 2 cy not taken, 3 taken
 *        NOP                       ; 1 cy -- SKIPPED when taken
 *   skip: RLC A                    ; 1 cy
 *
 *  so a LOW read costs 2+1+1 = 4 cycles and a HIGH read costs 3+0+1 = 4.
 *  The NOP exists for exactly that reason.  Which makes the fitted
 *  data-dependent term in section 5 all the more interesting: the sequence
 *  is level-balanced in ARCHITECTURAL cycles, so every cycle of measured
 *  data dependence is pure instruction-fetch behaviour.
 *
 *  A NOTE ON DECW Y, kept because it is exactly the kind of thing that
 *  matters here.  The table above says 1 cycle, which is what cap_code.s's
 *  header assumes when it sums the loop to 37.  The assembler's own listing
 *  (build/caploop.rst) annotates `decw y` as [2], which would make the
 *  documented sum 38.  Nothing downstream depends on resolving it: the
 *  fitted gaps are [4,5,4,4,4,6,5,8] = 40 and the fit places the extra
 *  cycles at R1->R2 (+1) and at the end-of-loop wrap (+2) relative to the
 *  37-cycle claim, leaving the BS0->BS1 gap at 5.  The instruction-count
 *  arithmetic is not the measurement and never was.
 * ========================================================================== */

enum {
    CY_BTJT_NOT_TAKEN = 2,
    CY_BTJT_TAKEN     = 3,
    CY_BTJF_NOT_TAKEN = 2,
    CY_RLC_A          = 1,
    CY_NOP            = 1,
    CY_LD_IND_X_A     = 1,
    CY_INCW_X         = 1,
    CY_DECW_Y         = 1,   /* see the note above */
    CY_DEC_A          = 1,
    CY_DEC_LONGMEM    = 1,
    CY_JRNE_TAKEN     = 2,
    CY_JRNE_NOT_TAKEN = 1,
    CY_MOV_LONGMEM    = 1,
    CY_LD_A_IMM       = 1,
    CY_CLR_A          = 1,
    CY_SIM            = 1,
    CY_RIM            = 1,
    CY_LDW_Y_IMM      = 2,
    CY_RET            = 4
};

/* ==========================================================================
 *  SECTION 1 -- THE PINNED ADDRESSES
 * ==========================================================================
 *
 *  Every constant here is a CALIBRATED TIMING QUANTITY, checked in the
 *  linked image by guard_prod.py on every build.  They are reproduced in C
 *  because section 2 needs them to do the same arithmetic the assembler
 *  does -- and because writing them down is the clearest way to say that
 *  they are not free placement choices.
 *
 *   0x8000        RESET vector          -> the SDCC runtime init
 *   0x8004..805F  92 B of relocated decoder code IN THE VECTOR GAP
 *                 (rbarf_vectors.c -- and the first 16 of those bytes are
 *                 this file's own fitted sampler constants, O_CY and W_CY)
 *   0x8064        IRQ23, TIM4 update    -> the 1 ms millis tick
 *   0x8068..9F50  the C world: runtime, constants, decoder, application
 *   0x9F63..9F9E  CAPARM  -- cap_arm.s, 60 bytes.  The .org is calibrated:
 *                 mod-4 phase 3.  Re-phasing it moves the four edge polls
 *                 relative to the 32-bit flash words they are fetched from,
 *                 which redistributes ~3 cycles of fetch stall across the
 *                 comb's 2/2/3/4-cycle gaps, which sets the WIDTH of the
 *                 trigger-phase distribution.  guard_prod.py pins it
 *                 exactly.  (Read the caveat in PROD_CLOSURE.md section 18:
 *                 an independent re-measurement did NOT reproduce the -28 %
 *                 narrowing.  The change is 0 bytes and kept for its guard
 *                 hardening; treat the narrowing as unproven.)
 *   0x9F9F..9FA0  2 bytes of unprogrammed 0xFF.  Unreachable -- the arm's
 *                 last instruction is RET.  This gap is the entire cost of
 *                 the re-phasing above.
 *   0x9FA1        _cap_capture -- the legacy blocking entry.  == 0x8111
 *                 (mod 16): the address phase of capture.ihx, the image the
 *                 40-cycle model was fitted against.
 *   0x9FAF        _cap_loop -- the sampling loop's top `rlc a`.  == 0x811F
 *                 (mod 16), and pinned EXACTLY because cap_arm.s's four
 *                 poll offsets are computed against it at assembly time.
 *   0x9FB0        CL_R0 -- the R0 poll.  **This** is where the arm jumps.
 *   0x9FF1..9FFF  15 bytes of unprogrammed flash: the end of the part.
 * ========================================================================== */

#define CAPARM_ORG   0x9F63u   /* cap_arm.s: this area's .org             */
#define CAP_CAPTURE  0x9FA1u   /* caploop.s: the blocking entry            */
#define CL_ENT       0x9FAFu   /* == _cap_loop, the loop-top `rlc a`       */
#define CL_R0        0x9FB0u   /* == _cap_loop+1, the R0 poll: THE entry   */
#define PC_IDR       0x500Bu   /* port C input data register; PC3 = pin 7  */
#define PC3          3

/* The addresses of cap_arm.s's five BTJT instructions in the linked image.
 * The first is the idle gate (it branches inside cap_arm); the other four
 * are the edge-detect poll comb (they branch into CAPLOOP).  Section 7
 * re-derives every `rel` byte from these and checks the four against the
 * bytes the assembler actually emitted. */
#define ARM_IDLE_POLL_ADDR   0x9F69u
static const uint16_t ARM_EDGE_POLL_ADDR[4] = {
    0x9F77u, 0x9F7Cu, 0x9F81u, 0x9F87u
};
/* ...and the rel bytes sdas emitted for them (build/cap_arm.rst).  Having
 * these written down is the point: the whole reason cap_arm.s hand-assembles
 * its polls is that when the LINKER computed these bytes, it got one of
 * them wrong by two -- and two bytes landed the branch mid-instruction and
 * reset the chip. */
static const uint8_t ARM_EDGE_POLL_REL[4] = { 0x34u, 0x2Fu, 0x2Au, 0x24u };

enum { ARM_IDLE_N = 8 };       /* consecutive LOW polls that mean "idle"   */
enum { ARM_BUSY_TRIES = 8 };   /* idle-gate attempts before giving up      */
enum { ARM_BURSTS = 7 };       /* 176 us edge bursts = 1.23 ms of window   */
enum { ARM_BURST_POLLS = 256 };/* comb iterations per burst                */

/* ==========================================================================
 *  SECTION 2 -- LAYER 1: cap_arm.s, LINE FOR LINE
 * ==========================================================================
 *
 *  The arm has one job and it is not the obvious one.  "Catch the rising
 *  edge" is easy; what the arm must actually do is CATCH THE EDGE IN A
 *  PHASE THE SAMPLER MODEL COVERS.  There is a hard cliff:
 *
 *      t0_crit = BIT_NS - SLOT_OFFSET[2] / (1 + eps)  =  681 ns at -1.07 %
 *
 *  The eight sample slots span 2000 ns inside a 2500 ns loop, and the loop
 *  period is exactly two WS2812 bit slots -- so the sample comb is
 *  phase-locked to bit PAIRS for the whole frame.  When t0 crosses that
 *  threshold, slot 2 falls out of the first bit period and the comb
 *  re-partitions across EVERY bit pair in the frame at once: measured, 459
 *  of 461 segments go infeasible in a single 10 ns step of t0.  Swept on
 *  the host with t0 as the only variable: 0 refusals at t0 <= 680 ns, the
 *  first at 690 ns, 100 % out to 1300 ns.  No decoder change recovers it --
 *  relaxing the feasibility gate 20x recovers 0 of 280 cases -- because the
 *  information was never sampled.  The predicted cliff matches the measured
 *  one to within 1..5 ns over a 61 ns range of predictions.
 *
 *  So every design choice below is about the trigger phase:
 *
 *   FIX 2a  ENTER AT _cap_loop+1, NOT _cap_loop.  The byte at _cap_loop is
 *           the loop-top `rlc a` that deposits the PREVIOUS iteration's
 *           BS1 sample -- and on the first iteration there is no previous
 *           iteration.  Skipping it costs one cycle less of t0 AND lands
 *           the branch on 0x9FB0, the FIRST byte of a 32-bit flash word,
 *           instead of 0x9FAF, the LAST byte of one.  A taken branch to
 *           0x9FAF fetches the whole word 0x9FAC..0x9FAF to execute a
 *           single 1-byte instruction and then stalls again for the R0
 *           poll; that was where the old arm's ~2 cycles of fixed excess
 *           over the blocking entry came from.  Slot 0 IS the R0 poll, so
 *           the fitted slot offsets, the data-dependent term and the
 *           40-cycle period are all untouched: only t0 moves.
 *
 *   FIX 2b  PUT THE COUNTER INSIDE THE COMB.  With `dec a` after the last
 *           poll the wrap gap was btjt(2) + dec(1) + jrne(2) = 5 cycles, so
 *           an edge landing there waited up to 5.  Moving `dec a` between
 *           polls 3 and 4 splits the wrap into gaps of 2, 2, 3, 4 -- same
 *           instructions, same 11-cycle period, same 60 bytes, one cycle
 *           less worst-case latency.  Flag-safe by the two facts in
 *           section 0.
 *
 *   FIX 3   THE IDLE GATE.  The old wait-low phase accepted a SINGLE low
 *           sample as "the line is idle", so an arm window that opened in
 *           the middle of a burst triggered on the next MID-FRAME rising
 *           edge and captured a head-chopped partial frame.  Every one of
 *           16 measured R1 refusals plus 2 R3 and 1 R2 were chopped bursts
 *           of 11..476 bits of 479, and no chopped burst has ever decoded.
 *           The gate requires IDLE_N = 8 consecutive LOW polls at 5 cycles
 *           each = 40 cycles = 2.5 us: two full bit periods, and ~2.9x the
 *           longest low that occurs INSIDE a frame (T0L ~ 873 ns).  It
 *           recovers no frame -- a half-gone frame cannot be un-lost -- it
 *           converts a doomed capture plus its ~50 ms decode window into a
 *           clean no-report.  Measured A/B: head-chopped captures 13.4 % ->
 *           0.  Cost: one byte of flash and a 2.5 us blind slot per arm
 *           entry, 0.2 % of the 1.23 ms cycle.
 *
 *   FIX 1   HAND-ASSEMBLE THE FOUR POLLS.  Written the obvious way,
 *           `btjt 0x500B, #3, _cap_loop`, the 1-byte PC-relative operand
 *           crosses an absolute-area boundary, so the assembler defers it
 *           to a linker relocation -- and the linker MIS-COMPUTES it: when
 *           two of these consecutive PC-relative relocations pack into one
 *           object-file record, the first of the pair comes out two bytes
 *           short.  The third of four identical polls linked to 0x9FAD
 *           instead of 0x9FAF.  0x9FAD is mid-instruction; its first byte
 *           is not a valid opcode.  So whenever the rising edge happened to
 *           be caught by the third poll -- a frame-arrival-phase race,
 *           about 1 capture in 6 -- the CPU branched into the middle of an
 *           instruction and took an ILLEGAL-OPCODE RESET.  That, and not
 *           the decoder, was the notorious "reset every ~6 decodes".
 *
 *           The fix emits each poll as five raw bytes with the rel computed
 *           ENTIRELY at assembly time from same-area quantities, so no
 *           relocation record is generated and the linker never touches the
 *           offset.  arm_poll_rel() below is that arithmetic in C, and
 *           section 7 checks it against the bytes in the shipped image.
 *
 *  Cycle budget, which is the part worth adding up:
 *
 *      idle poll   btjt(2) + dec a(1) + jrne taken(2)          =  5 cy
 *      idle gate   8 idle polls                                = 40 cy = 2.5 us
 *      comb        poll1 -2- poll2 -2- poll3 -3- poll4 -4- poll1
 *                  = btjt+btjt+(btjt+dec)+(btjt+jrne)          = 11 cy
 *      burst       256 comb iterations                    = 2816 cy = 176 us
 *      window      7 bursts                                        = 1.23 ms
 *
 *  Worst-case edge-detect latency is therefore 4 cycles = 250 ns, and that
 *  number is one of the two terms of t0 (the other is the fixed cost of the
 *  taken branch into the loop plus whatever fetch stalls the comb's address
 *  phase produces).
 * ========================================================================== */

/*
 * The BTJT_R0 macro's arithmetic, in C.
 *
 * The assembler source is
 *
 *      .db 0x72, 0x06, 0x50, 0x0B                 ; BTJT #3, longmem 0x500B
 *      .db (CL_R0 - (CAPARM_ORG + (. - _cap_arm) + 1))
 *
 * `. - _cap_arm` is a pure in-area offset -- a constant, not a relocatable
 * expression -- so the whole thing reduces to an absolute constant at
 * assembly time.  `.` at that point is the address of the rel byte itself,
 * i.e. poll_addr + 4, so the expression is CL_R0 - (poll_addr + 5): the
 * displacement from the END of the 5-byte instruction to the target, which
 * is what a PC-relative branch wants.
 */
static int arm_poll_rel(uint16_t poll_addr)
{
    return (int)CL_R0 - (int)(poll_addr + 5u);
}

/* Where a BTJT at `poll_addr` with rel byte `rel` actually lands. */
static uint16_t arm_poll_target(uint16_t poll_addr, uint8_t rel)
{
    int s = (rel >= 0x80u) ? (int)rel - 256 : (int)rel;   /* sign-extend */
    return (uint16_t)((int)poll_addr + 5 + s);
}

/*
 * _cap_arm -- production armed capture.
 *
 * Entry:  X = capture buffer, Y = loop count (288 in production).
 * Return: A = 1 captured, A = 0 no frame / line busy in this window.
 * Preserves X and Y for the sampling loop; clobbers A and C.
 *
 * The `goto`s are deliberate: they are the assembly's own labels, and a
 * structured rewrite would hide the one property the file exists to show --
 * that control flow leaves this routine by falling into a DIFFERENT
 * routine's middle, and never comes back.
 */
int stm8_cap_arm(uint8_t *buf, uint16_t y_loops, stm8_arm_trace *tr)
{
    uint8_t s_arm;          /* the one byte of RAM the arm owns (0x034C)   */
    uint8_t a;              /* register A                                  */
    int c;                  /* the carry flag, which is where samples live */
    int poll;

    tr->entered_loop = 0;
    tr->caught_by = 0;
    tr->a_at_entry = 0;
    tr->idle_tries = 0;
    tr->bursts = 0;
    tr->nominal_cy = 0;
    tr->polls = 0;

    s_arm = 8;                                  /* MOV s_arm,#8       [1] */
    tr->nominal_cy += CY_MOV_LONGMEM;

L00060:                                     /* ---- idle gate: IDLE_N lows */
    tr->idle_tries++;
    a = ARM_IDLE_N;                             /* LD A,#IDLE_N       [1] */
    tr->nominal_cy += CY_LD_A_IMM;

L00061:
    c = tr->read(tr->ctx);                      /* BTJT 0x500B,#3,L00065  */
    tr->polls++;                                /*   C <- PC3; 2 cy, 3 if */
    if (c) {                                    /*   taken                */
        tr->nominal_cy += CY_BTJT_TAKEN;        /*                    [3] */
        goto L00065;                            /* HIGH -> line busy      */
    }
    tr->nominal_cy += CY_BTJT_NOT_TAKEN;        /*                    [2] */
    a--;                                        /* DEC A              [1] */
    tr->nominal_cy += CY_DEC_A;                 /*   5 cy per low poll    */
    if (a != 0) {                               /* JRNE L00061      [1/2] */
        tr->nominal_cy += CY_JRNE_TAKEN;
        goto L00061;
    }
    tr->nominal_cy += CY_JRNE_NOT_TAKEN;

                                    /* ---- line idle: open the window --- */
    s_arm = ARM_BURSTS;                         /* MOV s_arm,#7       [1] */
    tr->nominal_cy += CY_MOV_LONGMEM;           /*   7 x 176 us = 1.23 ms */

L00063:
    tr->bursts++;
    /* SIM [1] -- mask ONE 176 us poll burst.  The TIM4 update flag is
     * latched in hardware, so a tick that falls inside the burst is
     * DELIVERED LATE at the RIM below rather than lost.  A burst that flows
     * into a capture (~720 us at 288 loops) can swallow at most one tick
     * per captured frame. */
    tr->nominal_cy += CY_SIM;
    a = 0;                                      /* CLR A              [1] */
    tr->nominal_cy += CY_CLR_A;                 /*   256 comb iterations  */

L00064:
    /* ---- the poll comb: four identical hand-assembled BTJTs ----------
     * Each is `72 06 50 0B <rel>` with <rel> computed at assembly time, and
     * each branches to CL_R0 = _cap_loop+1.  Gaps between the pin reads,
     * reading down: 2, 2, 3, 4 cycles; total period 11. */
    for (poll = 1; poll <= 4; poll++) {
        c = tr->read(tr->ctx);                  /* BTJT_R0            [2] */
        tr->polls++;
        if (c) {                                /*   ...or [3] if taken   */
            tr->nominal_cy += CY_BTJT_TAKEN;
            tr->entered_loop = 1;
            tr->caught_by = poll;
            tr->a_at_entry = a;
            /* THE JUMP.  Control leaves cap_arm here and lands inside
             * caploop.s at its R0 poll.  It never returns: the sampling
             * loop's own RET returns to _cap_arm's CALLER with A = 1.
             * Nothing in cap_arm runs again.  (The carry the poll just
             * latched is discarded -- the R0 poll overwrites it
             * immediately, which is exactly why entering at the poll and
             * not at the loop-top `rlc a` is safe.) */
            return stm8_cap_loop(buf, y_loops, a, 1, tr->read, tr->ctx);
        }
        tr->nominal_cy += CY_BTJT_NOT_TAKEN;
        if (poll == 3) {
            a--;                                /* DEC A              [1] */
            tr->nominal_cy += CY_DEC_A;         /*   counter INSIDE the   */
        }                                       /*   comb -- FIX 2b       */
    }
    if (a != 0) {                               /* JRNE L00064      [1/2] */
        tr->nominal_cy += CY_JRNE_TAKEN;
        goto L00064;                            /*   256 x 11 cy = 176 us */
    }
    tr->nominal_cy += CY_JRNE_NOT_TAKEN;

    /* RIM [1] -- a TIM4 tick that became pending during the burst is
     * delivered HERE, one instruction after the comb. */
    tr->nominal_cy += CY_RIM;
    s_arm--;                                    /* DEC s_arm          [1] */
    tr->nominal_cy += CY_DEC_LONGMEM;
    if (s_arm != 0) {                           /* JRNE L00063      [1/2] */
        tr->nominal_cy += CY_JRNE_TAKEN;
        goto L00063;
    }
    tr->nominal_cy += CY_JRNE_NOT_TAKEN;
    a = 0;                                      /* CLR A              [1] */
    tr->nominal_cy += CY_CLR_A + CY_RET;        /* RET                [4] */
    return a;                                   /*   no frame in window   */

L00065:                                 /* ---- line busy: retry the gate  */
    s_arm--;                                    /* DEC s_arm          [1] */
    tr->nominal_cy += CY_DEC_LONGMEM;
    if (s_arm != 0) {                           /* JRNE L00060      [1/2] */
        tr->nominal_cy += CY_JRNE_TAKEN;
        goto L00060;
    }
    tr->nominal_cy += CY_JRNE_NOT_TAKEN;
    a = 0;                                      /* CLR A              [1] */
    tr->nominal_cy += CY_CLR_A + CY_RET;        /* RET                [4] */
    return a;                                   /*   still busy: re-arm   */
}

/* ==========================================================================
 *  SECTION 3 -- LAYER 1: caploop.s, LINE FOR LINE
 * ==========================================================================
 *
 *  Eighty bytes of flash, and the instrument the entire project is built
 *  on.  It reads one GPIO pin eight times per 40-cycle loop and stores one
 *  byte per loop -- a very cheap logic analyser with a 2.5 us frame and an
 *  8-sample comb inside it.
 *
 *  THE 40 CYCLES, AND THE EIGHT SAMPLE INSTANTS.  Reading down the loop,
 *  each sample is one BTJT; the gap to the next sample is everything
 *  between the two BTJTs inclusive of the first:
 *
 *     instruction              cy   cumulative   gap to next sample
 *     ----------------------  ---  -----------   ------------------
 *     rlc a  (loop top)         1        --      deposits the PREVIOUS
 *                                               iteration's BS1 sample
 *     BTJT R0  / nop / rlc a  2+1+1     0 cy  \   4
 *     BTJT R1  / nop / rlc a  2+1+1     4 cy  /   4  (fitted: 5)
 *     BTJT R2  / nop / rlc a  2+1+1     9 cy      4
 *     BTJT R3  / nop / rlc a  2+1+1    13 cy      4
 *     BTJT R4  / nop / rlc a  2+1+1    17 cy      4
 *     BTJT R5  / nop / rlc a  2+1+1    21 cy      6   <- + ld (x),a, incw x
 *     ld (x),a                  1
 *     incw x                    1
 *     BTJT BS0 / nop / rlc a  2+1+1    27 cy      5   <- + decw y
 *     decw y                    1
 *     BTJT BS1 / nop          2+1      32 cy      6   <- + jrne, rlc a
 *     jrne (top)                2
 *                            -----
 *     documented total         37 cy      gaps  [4,4,4,4,4,6,5,6]
 *     FITTED total             40 cy      gaps  [4,5,4,4,4,6,5,8]
 *
 *  The fitted layout differs from the documented one by +1 cycle in the
 *  R1->R2 gap and +2 cycles in the end-of-loop wrap.  Those three cycles
 *  are flash-fetch stalls, they exist only at this address phase, and they
 *  are why the loop is pinned.
 *
 *  WHY SIX PLUS TWO AND NOT EIGHT.  Eight evenly spaced samples inside a
 *  37-cycle loop would leave a 9-cycle (562 ns) hole at the loop's
 *  bookkeeping, and a 0-bit's entire high pulse is 375 ns -- it would
 *  vanish whenever it landed there.  Splitting the two "boundary samples"
 *  BS0 and BS1 around the store and the counter cuts the worst gap to 6
 *  cycles (375 ns).  A 0-bit can still be swallowed whole -- the end-of-loop
 *  gap is a FITTED 8 cycles = 500 ns, wider than the pulse -- but rarely,
 *  and the decoder is built to notice that the surrounding silence is too
 *  long.  That is what "the dead zone" means in the decoder's vocabulary.
 *
 *  THE BYTE, AND WHY IT IS SHAPED THAT WAY.  There are eight samples and
 *  eight bits, but the byte has to be STORED before the last two samples
 *  are taken -- the store IS one of the two things that create the gap the
 *  boundary samples are splitting.  So the chain of `rlc a` instructions
 *  carries BS0 and BS1 into the NEXT byte's top two bits:
 *
 *      capture byte i:  bit 7 = BS0 of loop i-1     bits 5..0 = R0..R5
 *                       bit 6 = BS1 of loop i-1                 of loop i
 *
 *  Byte 0's top two bits are garbage (there is no loop -1) and the last
 *  loop's BS0/BS1 are simply never stored.  Section 7 PROVES that the RLC
 *  chain really produces this layout, by running the rendering below
 *  against a known sample stream and comparing with the model's packer.
 *
 *  ONE MORE FLAG SUBTLETY.  `decw y` sits between BS0 and BS1 and sets Z;
 *  the BS1 BTJT after it writes C and leaves Z alone; the JRNE at the
 *  bottom tests that Z.  So the loop counter is decremented five
 *  instructions before it is tested, with a pin sample in between.  There
 *  is nowhere else to put it.
 * ========================================================================== */

/* One sample site: BTJT PC_IDR,#3,skip / NOP / RLC A.  Reads the pin into
 * C, then rotates C into A.  4 cycles either way (section 0). */
#define SAMPLE_INTO_A(a_, read_, ctx_, level_)                                \
    do {                                                                      \
        (level_) = (read_)(ctx_);   /* BTJT 0x500B,#3,skip  [2 / 3 taken] */  \
                                    /* NOP                  [1, skipped]  */  \
        (a_) = (uint8_t)(((a_) << 1) | ((level_) ? 1u : 0u)); /* RLC A [1] */ \
    } while (0)

int stm8_cap_loop(uint8_t *buf, uint16_t y_loops, uint8_t a_entry,
                  int enter_at_r0, stm8_pc3_read read, void *ctx)
{
    uint8_t a = a_entry;            /* register A: the byte being built     */
    uint16_t y = y_loops;           /* register Y: the loop counter         */
    uint8_t *x = buf;               /* register X: the buffer pointer       */
    int c = 0;                      /* the carry flag                       */
    int first = 1;
    int lvl;

    for (;;) {
        /* --- 00012$ / _cap_loop = 0x9FAF ------------------------------- */
        if (!(first && enter_at_r0)) {
            a = (uint8_t)((a << 1) | (c ? 1u : 0u));  /* RLC A         [1] */
        }                           /*   deposit BS1 from C (prev boundary) */
        /* FIX 2a: entering at CL_R0 = 0x9FB0 skips exactly that one
         * instruction on the first iteration, because there IS no previous
         * iteration.  Its consequence is that byte 0's bits 7..6 hold two
         * bits of whatever the arm left in A instead of a previous BS0/BS1.
         * No consumer reads them: the decoder's scanner takes loop i's
         * slots 6 and 7 from byte i+1, so byte 0 bits 7..6 are unreachable.
         * Proved twice rather than argued -- 836 captures decoded four
         * times each with those two bits forced to 00/01/10/11, 0
         * mismatches, plus the shipped assembly run in a simulator with
         * them forced to 11, 24/24 bit-identical. */
        first = 0;

        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R0  -- slot 0, cycle  0     */
        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R1  -- slot 1, cycle  4     */
        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R2  -- slot 2, cycle  9     */
        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R3  -- slot 3, cycle 13     */
        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R4  -- slot 4, cycle 17     */
        SAMPLE_INTO_A(a, read, ctx, lvl);   /* R5  -- slot 5, cycle 21     */

        *x = a;                             /* LD (X),A               [1] */
        x++;                                /* INCW X                 [1] */

        SAMPLE_INTO_A(a, read, ctx, lvl);   /* BS0 -- slot 6, cycle 27     */

        y--;                                /* DECW Y                 [1] */
                                            /*   sets Z; C untouched      */

        c = read(ctx);                      /* BTJT BS1               [2] */
                                            /* NOP                    [1] */
        /* BS1 -- slot 7, cycle 32.  C ONLY: there is no `rlc a` here.  The
         * sample stays in the carry flag until the top of the NEXT
         * iteration deposits it.  BTJT does not touch Z, so the JRNE below
         * still sees the DECW's result. */

        if (y == 0) {                       /* JRNE 00012$          [1/2] */
            break;
        }
    }

    /* Post-loop, and timing-irrelevant -- the frame is over.
     *   RIM        [1]  re-enable the millis tick the arm masked
     *   LD A,#1    [1]  A = 1 -> "captured", which is what rbarf_prod.c's
     *                   inline asm stores into cap_got
     *   RET        [4]  returns to _cap_arm's CALLER, not to _cap_arm */
    (void)c;
    return 1;
}

/*
 * _cap_capture -- the LEGACY BLOCKING ENTRY, 14 bytes ahead of the loop.
 *
 * This is the shape cap_code.s ships in the acquisition image (capture.ihx)
 * and it matters out of all proportion to its size: it is the front end the
 * sampler model was FITTED against, and it is the front end that scores
 * 97.8 % delivery.  Its trigger phase, fitted over the 54-capture corpus,
 * is 89..628 ns with 0 of 54 above the 681 ns cliff, against the armed
 * front end's 102..650 ns.  When the arm is judged, this is the yardstick.
 *
 * It blocks forever if no frame arrives, which is exactly why production
 * cannot use it: the chip has an animation to render.
 */
int stm8_cap_capture(uint8_t *buf, stm8_pc3_read read, void *ctx)
{
    uint16_t y = 256;                       /* LDW Y,#256             [2] */
    (void)y;
    while (read(ctx))                       /* 00010$ wait_low:           */
        ;                                   /*   BTJT 0x500B,#3,00010$[2] */
    while (!read(ctx))                      /* 00011$ wait_high:          */
        ;                                   /*   BTJF 0x500B,#3,00011$[2] */
    /* Falls through into _cap_loop AT THE TOP -- at the `rlc a`, not at
     * the R0 poll.  A fall-through costs no branch and no fetch stall, so
     * this entry is a cycle or two EARLIER than a taken branch would be;
     * that difference is the whole of cap_arm.s FIX 2a. */
    return stm8_cap_loop(buf, 256, 0, 0, read, ctx);
}

/* ==========================================================================
 *  SECTION 4 -- LAYER 2: THE WIRE
 * ==========================================================================
 *
 *  What the sampler is looking at.  A WS2812 bit is a fixed-period pulse
 *  whose WIDTH carries the value:
 *
 *      bit slot   1250 ns   (800 kbit/s)
 *      a '1'      high for T1H, then low     T1H = 752 ns effective
 *      a '0'      high for T0H, then low     T0H = 377 ns effective
 *
 *  "Effective" because those are the FITTED widths, not the transmitter's
 *  nominal 750 / 375: the calibration found a common +2 ns edge shift and
 *  kept it.  Two nanoseconds sounds like nothing next to a 62.5 ns sample
 *  clock, and it is -- until a sample lands within 2 ns of an edge, which
 *  over 276 000 real samples happens often enough to matter to the fit.
 *
 *  Two representations, because both are natural and they had better agree:
 *
 *    BIT SEQUENCE + widths   what a transmitter thinks in.  This is the one
 *                            the model uses, and the one the Python sampler
 *                            uses, so it is the one parity is proven on.
 *    EDGE TIMES              what an oscilloscope hands you.  Level at time
 *                            t = "odd number of edges at or before t",
 *                            starting from low.
 *
 *  They are exactly equivalent, not approximately: a rise sits at
 *  k*1250 and its fall at k*1250 + T, both exactly representable in
 *  binary floating point (every value is a multiple of 0.5), and
 *  `(t - k*1250) < T` and `t < k*1250 + T` are the same comparison on
 *  exact operands.  rbarf_capture_selfcheck() checks it on a dense grid
 *  rather than taking the argument's word for it.
 * ========================================================================== */

void rbarf_wire_v23(rbarf_wire *w, const uint8_t *bit, uint16_t nbits)
{
    w->bit    = bit;
    w->nbits  = nbits;
    w->bit_ns = 1250.0;      /* one WS2812 bit slot at 800 kbit/s          */
    w->t1h_ns =  752.0;      /* fitted: 750 wire + 2 ns common edge shift  */
    w->t0h_ns =  377.0;      /* fitted: 375 wire + 2 ns                    */
}

/*
 * Which bit slot does time t fall in?
 *
 * This is written the long way ON PURPOSE.  The obvious `(long)floor(t /
 * bit_ns)` can round the division UP to exactly k when t is a hair below
 * k*bit_ns, and then floor() returns k instead of k-1 -- one wire bit of
 * error at exactly the boundaries where the answer matters most.  The
 * remainder-first form is exact for every t >= 0: fmod() is exact, t - mod
 * is exactly k*bit_ns (a representable value, so IEEE subtraction returns
 * it), and dividing an exact multiple gives exactly k.
 *
 * It is also, and not by accident, precisely what CPython's float `//`
 * does internally -- which is how the parity proof gets to be byte-exact
 * against a Python reference rather than "equal to within rounding".
 */
static long wire_slot_of(double t_ns, double bit_ns, double *within)
{
    double mod = fmod(t_ns, bit_ns);
    double base = t_ns - mod;
    long k = (long)(base / bit_ns);
    *within = t_ns - (double)k * bit_ns;
    return k;
}

int rbarf_wire_level(const rbarf_wire *w, double t_ns)
{
    double within;
    long k;

    if (t_ns < 0.0)
        return 0;                       /* before the frame: idle low      */
    k = wire_slot_of(t_ns, w->bit_ns, &within);
    if (k < 0 || (unsigned long)k >= (unsigned long)w->nbits)
        return 0;                       /* after the frame: idle low       */
    return within < (w->bit[k] ? w->t1h_ns : w->t0h_ns) ? 1 : 0;
}

uint16_t rbarf_wire_edges(const rbarf_wire *w, double *out, uint16_t cap)
{
    uint16_t n = 0;
    uint16_t k;

    for (k = 0; k < w->nbits; k++) {
        double base = (double)k * w->bit_ns;
        if ((uint16_t)(n + 2) > cap)
            return 0;
        out[n++] = base;                                        /* rise */
        out[n++] = base + (w->bit[k] ? w->t1h_ns : w->t0h_ns);  /* fall */
    }
    return n;
}

int rbarf_wire_level_edges(const rbarf_edges *e, double t_ns)
{
    /* Count edges at or before t_ns; odd means high.  Binary search,
     * because a 480-bit frame has 960 edges and the sampler asks 2300
     * times per capture. */
    uint16_t lo = 0, hi = e->n;

    while (lo < hi) {
        uint16_t mid = (uint16_t)(lo + (hi - lo) / 2u);
        if (e->t_ns[mid] <= t_ns)
            lo = (uint16_t)(mid + 1u);
        else
            hi = mid;
    }
    return (int)(lo & 1u);
}

/* ==========================================================================
 *  SECTION 5 -- LAYER 2: THE FITTED SAMPLER
 * ==========================================================================
 *
 *  The whole instrument, in two lines:
 *
 *      A(i,s) = i*LOOP + o[s] + SUM_j w[j] * C_j(i,s)     (nominal cycles)
 *      t(i,s) = t0 + A(i,s) / (1 + eps)                   (real time, ns)
 *
 *  where C_j(i,s) counts HIGH reads at slot j strictly BEFORE sample (i,s).
 *
 *  Read that second term again, because it is the surprising one.  The
 *  sampler's own progress depends on WHAT IT HAS SEEN: every sample that
 *  reads HIGH shifts all later samples by a whole number of cycles.  The
 *  term is CAUSAL -- it depends only on samples already taken -- so it
 *  simulates one sample at a time with a single running accumulator, which
 *  is the only reason it is tractable at all (and the reason the decoder
 *  can carry the same correction while decoding).
 *
 *  THE FITTED CONSTANTS.  Every one of these was fitted to the 54 real
 *  captures with only two per-capture nuisance parameters free (t0 and
 *  eps); no sampler constant was allowed to vary per capture.
 *
 *      LOOP  = 40 cycles = 2500.0 ns          (documented: 37 -- wrong)
 *      o[]   = 0, 250, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000 ns
 *              i.e. cycle gaps [4,5,4,4,4,6,5,8]
 *      w[]   = [0, -1, 0, +2, 0, 0, 0, +1] cycles per HIGH read
 *      T1H   = 752 ns, T0H = 377 ns
 *
 *  Agreement: 99.9627 % of all 276 372 real samples, 99.7616 % inside the
 *  active frame window, 8 of 54 captures at 100.000 %; the merged-loop
 *  counts on the all-ones pattern come out 35/36/38 against a real 37/36/39
 *  over the same loop spans, and the swallowed-zero counts reproduce
 *  exactly on 14 of 15 checked captures.
 *
 *  WHY w[] EXISTS.  Section 0 showed the sample site is level-balanced in
 *  architectural cycles: 4 either way, by construction, with the NOP paying
 *  for the taken branch.  So w[] is not the branch -- it is what the
 *  instruction PREFETCH does differently on the two paths at each
 *  particular site, and it is a per-site constant because it depends on
 *  where that site's bytes sit relative to the 32-bit flash words.  Without
 *  w[] the sampler's period-2 loop-length alternation cannot be reproduced
 *  at all and agreement caps around 85..95 % in the frame window; merged
 *  1-bits come out as one long block instead of the observed runs of one or
 *  two loops.
 *
 *  AND IT PRODUCES A FEEDBACK LOOP, which is the nicest thing in the whole
 *  model.  w[3] = +2 cycles fires only when slot 3 reads HIGH, and slot 3
 *  sits late in the bit -- so it fires when the sampling phase has drifted
 *  EARLY, and pushes it back.  Negative feedback.  In-frame loop period
 *  measures 2494.7..2513.4 ns (bimodal) against an idle-tail 2525.1..2528.5,
 *  and the residual in-frame phase crawl is only -0.2..-5.6 ns per loop.
 *  That is why intrinsically ambiguous bits are 42 in 10 368 = 0.41 %,
 *  where a rigid geometry predicts 9.4 %.
 *
 *  THE END-OF-LOOP GAP IS THE MERGE MECHANISM.  Slot 7 to the next slot 0
 *  is 8 fitted cycles = 500 ns after a LOW read at BS1, and 9 cycles =
 *  562.5 ns after a HIGH one (that is w[7] = +1).  T1L -- the low time
 *  after a 1-bit -- is about 498 ns.  The gap and the gap it has to see
 *  through are the SAME SIZE, so two adjacent 1-bits merge into one long
 *  pulse whenever the phase is unlucky, and the merge resonance sits at
 *  eps ~ 0.  Which is one of the two reasons the auto-trim targets
 *  eps = -1.0 % instead of 0.
 *
 *  THE CAPTURE BYTE LAYOUT is section 3's RLC chain, viewed from the other
 *  side:
 *
 *      byte i:  bit 7 = slot 6 of loop i-1     bits 5..0 = slots 0..5
 *               bit 6 = slot 7 of loop i-1                 of loop i
 *
 *  and byte 0's bits 7..6 are written as ZERO here.  On silicon they hold
 *  the low two bits of the arm's burst counter at the instant the edge was
 *  caught (see section 2's FIX 2a).  This is the ONE known byte-level
 *  difference between this model and the hardware, it is in the Python
 *  reference too, and it is provably harmless: the decoder's scanner takes
 *  loop i's slots 6 and 7 from byte i+1, so byte 0 bits 7..6 are
 *  unreachable, and forcing them to all four values over 836 captures
 *  changed nothing.
 * ========================================================================== */

enum { SAMPLE_SLOTS = 8 };

/* The nominal CPU cycle at exactly 16 MHz. */
#define CY_NS 62.5

/* o[]: cycle offset of each sample inside its loop, as ns.  Gaps
 * [4,5,4,4,4,6,5,8]; the loop period is LOOP_NS = 2500 ns = 40 cycles, so
 * slot 7 -> next slot 0 is the remaining 8 cycles.  These EXACT eight
 * numbers also live in the shipped image, in the vector-table gap, as the
 * table `sot` at 0x8004 -- see rbarf_vectors.c. */
static const double SLOT_OFFSET_NS[SAMPLE_SLOTS] = {
    0.0, 250.0, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000.0
};

/* w[]: cycles added AFTER a sample at this slot read HIGH.  In the image
 * this is the table `swt` at 0x800C: 00 FF 00 02 00 00 00 01. */
static const double BRANCH_COST_NS[SAMPLE_SLOTS] = {
    0.0, -62.5, 0.0, 125.0, 0.0, 0.0, 0.0, 62.5
};

#define LOOP_NS 2500.0           /* 40 cycles -- FITTED, not counted       */

uint16_t rbarf_capture(const rbarf_wire *w, const rbarf_sampler *s,
                       uint8_t *out, uint16_t out_cap)
{
    double wsum = 0.0;           /* SUM_j w[j]*C_j, accumulated causally   */
    double span;                 /* the WIRE's span, for the drift ramp    */
    uint16_t i, len;
    uint8_t prev6 = 0, prev7 = 0;

    if (s->n_bytes == 0 || s->n_bytes > out_cap)
        return 0;
    if (s->chop >= s->n_bytes || s->trunc >= s->n_bytes)
        return 0;                /* see section 6 on why these are refused */

    span = (double)w->nbits * w->bit_ns;

    /* One iteration per SAMPLING LOOP.  n_bytes+1 loops are simulated and
     * n_bytes bytes are stored: the last loop's BS0/BS1 have nowhere to go,
     * exactly as on the hardware, where the loop exits before storing
     * them. */
    for (i = 0; i <= s->n_bytes; i++) {
        double base = (double)i * LOOP_NS;
        int lvl[SAMPLE_SLOTS];
        int slot;

        for (slot = 0; slot < SAMPLE_SLOTS; slot++) {
            /* A(i,s) in nominal cycles, expressed in ns */
            double a = base + SLOT_OFFSET_NS[slot] + wsum;
            double e = s->eps;
            double t;

            if (s->drift != 0.0) {
                /* Linear eps ramp across the WIRE span, centred so that
                 * eps is the mid-burst value: -drift/2 at the start,
                 * +drift/2 at the end, clamped outside. */
                double frac = a / span;
                if (frac < 0.0) frac = 0.0;
                if (frac > 1.0) frac = 1.0;
                e = s->eps + s->drift * (frac - 0.5);
            }
            t = s->t0_ns + a / (1.0 + e);
            lvl[slot] = rbarf_wire_level(w, t);
            if (lvl[slot])
                wsum += BRANCH_COST_NS[slot];   /* the causal term */
        }

        if (i < s->n_bytes) {
            uint8_t b = 0;
            if (i > 0) {                        /* byte 0: no loop -1     */
                b = (uint8_t)(b | (uint8_t)(prev6 << 7));
                b = (uint8_t)(b | (uint8_t)(prev7 << 6));
            }
            for (slot = 0; slot < 6; slot++)
                b = (uint8_t)(b | (uint8_t)(lvl[slot] << (5 - slot)));
            out[i] = b;
        }
        prev6 = (uint8_t)lvl[6];
        prev7 = (uint8_t)lvl[7];
    }

    /* ---- section 6: the malformations, applied in this order ---------- */
    len = s->n_bytes;
    if (s->chop) {                              /* HEAD missing            */
        memmove(out, out + s->chop, (size_t)(len - s->chop));
        memset(out + (len - s->chop), 0, (size_t)s->chop);
    }
    if (s->trunc)                               /* TAIL missing            */
        len = (uint16_t)(len - s->trunc);
    return len;
}

/* ==========================================================================
 *  SECTION 6 -- LAYER 2: THE MALFORMATIONS
 * ==========================================================================
 *
 *  A model that only produces well-formed captures is a model of a
 *  laboratory.  About 6 % of frames mis-arm on silicon, and the two shapes
 *  that mis-arming produces are worth reproducing on the host because they
 *  are where the R1 and R2 refusal classes actually come from:
 *
 *    chop   the arm fired LATE and the burst's HEAD is missing: drop the
 *           first `chop` bytes, shift left, zero-fill the tail.  This is
 *           what a mid-frame trigger looks like, and it is precisely what
 *           the idle gate (section 2, FIX 3) exists to prevent -- measured
 *           spans of 11..476 bits of 479, and no chopped burst has ever
 *           decoded.  The endpoint seed sees a short span and the clock fit
 *           has nothing to lock to.
 *
 *    trunc  the buffer ran out and the burst's TAIL is missing: keep the
 *           first n_bytes - trunc bytes.  A truncated trailer destroys the
 *           lock, which is the reason the production capture buffer is 288
 *           bytes and not 256: at the fast oscillator corner 256 lands
 *           EXACTLY on the truncation boundary.
 *
 *    drift  the oscillator's frequency moves DURING the capture: eps is
 *           replaced by a linear ramp across the wire span, centred so that
 *           `eps` remains the mid-burst value.  600 us is short enough that
 *           the fit found no drift it could resolve (per-capture spread
 *           +-0.014 %), so this is a robustness knob rather than a measured
 *           phenomenon.
 *
 *  chop >= n_bytes and trunc >= n_bytes are refused (return 0) rather than
 *  given a meaning.  In the Python reference those inputs produce a buffer
 *  whose LENGTH depends on `chop`, which is a slicing artefact and not a
 *  physical shape.  This is a deliberate, documented difference, and the
 *  parity harness stays inside the range where the two agree.
 *
 *  ONE HONEST NOTE ON THE DRIFT MODEL, since two exist in the tree and
 *  they are NOT the same function.  recon/synth.py ramps as
 *  (1+eps)*(1+drift*a/TOTAL) -- normalised to the CAPTURE's nominal span,
 *  starting at eps and ending at eps+drift.  v23lib's capture(), the one
 *  every v2.3 harness uses and the one proven against here, ramps as
 *  eps + drift*(clamp(a/WIRE_span) - 0.5) -- normalised to the WIRE span,
 *  centred on eps, and clamped.  Both are "a linear eps ramp"; neither is
 *  wrong; they differ in span, centring and clamping, so a drift figure
 *  quoted from one script does not transfer to the other.  This file
 *  implements v23lib's, because that is what capture() calls.
 * ========================================================================== */

uint16_t rbarf_crc16(const uint8_t *data, uint16_t len)
{
    /* CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, xorout
     * 0.  Check value for "123456789" is 0x29B1.  Bitwise on purpose --
     * this is the shape the on-chip chase loop mirrors and the shape the
     * Klipper Jinja macro has to port (Jinja has no bitwise operators). */
    uint16_t crc = 0xFFFFu;
    uint16_t i;

    for (i = 0; i < len; i++) {
        int b;
        crc = (uint16_t)(crc ^ (uint16_t)((uint16_t)data[i] << 8));
        for (b = 0; b < 8; b++)
            crc = (crc & 0x8000u)
                    ? (uint16_t)((uint16_t)(crc << 1) ^ 0x1021u)
                    : (uint16_t)(crc << 1);
    }
    return crc;
}

uint16_t rbarf_build_frame_v23(const uint8_t *data, uint8_t nd,
                               uint8_t *frame_out, uint16_t frame_cap)
{
    /* frame = FF AA 65 | DATA | (CRC_HI CRC_LO) x3 | 9A 00 FF
     *
     * FF  eight 1-bits: the unmissable start flag
     * AA  10101010: a bit-period ruler
     * 65  an asymmetric byte-alignment marker
     * 9A  alignment marker
     * 00  a worst-case-ZEROS calibration probe at a KNOWN position
     * FF  the mirrored end flag, so the last frame bit is a 1
     *
     * The check block is written THREE times because the check bytes ride
     * the same lossy channel as the data. */
    uint16_t crc, n = 0;
    int rep;

    if (nd == 0 || nd > RBARF_CAP_ND_MAX)
        return 0;
    if ((uint16_t)(nd + 12) > frame_cap)
        return 0;

    frame_out[n++] = 0xFFu;
    frame_out[n++] = 0xAAu;
    frame_out[n++] = 0x65u;
    memcpy(frame_out + n, data, (size_t)nd);
    n = (uint16_t)(n + nd);
    crc = rbarf_crc16(data, nd);
    for (rep = 0; rep < 3; rep++) {
        frame_out[n++] = (uint8_t)(crc >> 8);
        frame_out[n++] = (uint8_t)(crc & 0xFFu);
    }
    frame_out[n++] = 0x9Au;
    frame_out[n++] = 0x00u;
    frame_out[n++] = 0xFFu;
    return n;
}

uint16_t rbarf_bytes_to_bits(const uint8_t *bytes, uint16_t nbytes,
                             uint8_t *bits_out, uint16_t cap)
{
    uint16_t n = 0, i;
    int b;

    if ((uint16_t)(nbytes * 8u) > cap)
        return 0;
    for (i = 0; i < nbytes; i++)
        for (b = 7; b >= 0; b--)              /* MSB first, like the wire */
            bits_out[n++] = (uint8_t)((bytes[i] >> b) & 1u);
    return n;
}

uint16_t rbarf_capture_v23(const uint8_t *data, uint8_t nd,
                           double eps, double t0_ns, double drift,
                           uint16_t n_bytes, uint16_t chop, uint16_t trunc,
                           uint8_t *out, uint16_t out_cap)
{
    uint8_t frame[RBARF_CAP_FRAME_MAX];
    uint8_t bits[RBARF_CAP_BITS_MAX];
    rbarf_wire w;
    rbarf_sampler s;
    uint16_t nframe, nbits;

    nframe = rbarf_build_frame_v23(data, nd, frame, (uint16_t)sizeof frame);
    if (nframe == 0)
        return 0;
    nbits = rbarf_bytes_to_bits(frame, nframe, bits, (uint16_t)sizeof bits);
    if (nbits == 0)
        return 0;

    rbarf_wire_v23(&w, bits, nbits);
    s.eps = eps;
    s.t0_ns = t0_ns;
    s.drift = drift;
    s.n_bytes = n_bytes;
    s.chop = chop;
    s.trunc = trunc;
    return rbarf_capture(&w, &s, out, out_cap);
}

/* ==========================================================================
 *  SECTION 7 -- THE SELF-CHECKS
 * ==========================================================================
 *
 *  Layer 1 cannot be proven equivalent to layer 2 in the thing that matters
 *  most -- timing -- because the timing is a property of a linked binary.
 *  But three real equivalences ARE provable here, and they are the three
 *  places a reader is most likely to suspect a transcription error:
 *
 *   1  THE BIT PACKING.  Run the rendered sampling loop (section 3, an RLC
 *      chain) against a known pseudo-random sample stream and compare with
 *      the model's packer (section 5, a shift-and-or expression).  If the
 *      RLC chain has been mis-transcribed -- one rotation too many, the
 *      boundary samples in the wrong bits, the store in the wrong place --
 *      this fails.  It is the strongest statement this file can make about
 *      the assembly.
 *
 *   2  THE FOUR POLL OFFSETS.  Recompute the BTJT_R0 macro's rel byte from
 *      the shipped poll addresses and check (a) that it matches the byte
 *      the assembler emitted and (b) that it lands exactly on CL_R0 =
 *      _cap_loop+1.  This is guard_prod.py check 5's arithmetic, done from
 *      the other direction: the guard disassembles the linked image, this
 *      re-derives what the image should contain.
 *
 *   3  THE TWO WIRE REPRESENTATIONS.  Bit sequence versus edge list, on a
 *      dense grid straddling every edge.
 *
 *  Plus two cheap sanity checks on the arm's control flow (the idle gate
 *  really needs eight consecutive lows; the window really is bounded), and
 *  the cycle arithmetic the comments claim.
 * ========================================================================== */

/* --- a level oracle that replays a fixed sample stream ------------------- */
typedef struct {
    const uint8_t *level;
    uint16_t n;
    uint16_t pos;
} replay_ctx;

static int replay_read(void *ctx)
{
    replay_ctx *r = (replay_ctx *)ctx;
    if (r->pos >= r->n)
        return 0;
    return r->level[r->pos++];
}

/* --- an oracle that is low for `lows` polls, then high forever ---------- */
typedef struct { int lows; int polls; } gate_ctx;

static int gate_read(void *ctx)
{
    gate_ctx *g = (gate_ctx *)ctx;
    g->polls++;
    return (g->polls > g->lows) ? 1 : 0;
}

/* --- an oracle that is low forever -------------------------------------- */
static int low_read(void *ctx)
{
    (void)ctx;
    return 0;
}

#ifdef RBARF_CAPTURE_MAIN
#include <stdio.h>
#define CHK_PRINT(...) do { if (verbose) printf(__VA_ARGS__); } while (0)
#else
#define CHK_PRINT(...) do { } while (0)
#endif

int rbarf_capture_selfcheck(int verbose)
{
    int fails = 0;
    int i;

#ifndef RBARF_CAPTURE_MAIN
    (void)verbose;
#endif

    /* ---- 1: the RLC chain packs exactly like the model's packer ------- */
    {
        enum { NB = 64 };
        uint8_t levels[(NB + 1) * SAMPLE_SLOTS];
        uint8_t from_asm[NB], from_pack[NB];
        replay_ctx r;
        uint32_t x = 0x1234u;
        uint16_t n, b;
        int bad = 0;

        for (n = 0; n < (uint16_t)sizeof levels; n++) {
            x = (x * 1103515245u + 12345u) & 0x7FFFFFFFu;
            levels[n] = (uint8_t)((x >> 16) & 1u);
        }
        /* (a) the rendered assembly, entered the way the arm enters it */
        r.level = levels;
        r.n = (uint16_t)sizeof levels;
        r.pos = 0;
        memset(from_asm, 0xAA, sizeof from_asm);
        stm8_cap_loop(from_asm, NB, 0, 1, replay_read, &r);
        /* (b) the model's packer over the same stream.  Note the shift by
         * one sample: entering at CL_R0 means the loop's very first
         * instruction is the R0 poll, so sample 0 of the stream is
         * (loop 0, slot 0) -- which is exactly the model's convention. */
        for (b = 0; b < NB; b++) {
            uint8_t v = 0;
            int s;
            if (b > 0) {
                v = (uint8_t)(v | (uint8_t)(levels[(b - 1) * 8 + 6] << 7));
                v = (uint8_t)(v | (uint8_t)(levels[(b - 1) * 8 + 7] << 6));
            }
            for (s = 0; s < 6; s++)
                v = (uint8_t)(v | (uint8_t)(levels[b * 8 + s] << (5 - s)));
            from_pack[b] = v;
        }
        for (b = 0; b < NB; b++)
            if (from_asm[b] != from_pack[b])
                bad++;
        if (bad) {
            fails++;
            CHK_PRINT("FAIL  rendered RLC chain vs model packer: %u of %u "
                      "bytes differ\n", (unsigned)bad, (unsigned)NB);
        } else {
            CHK_PRINT("ok    rendered RLC chain == model packer, %u bytes "
                      "(the capture byte layout is proven, not asserted)\n",
                      (unsigned)NB);
        }
    }

    /* ---- 2: the four edge-detect poll offsets ------------------------- */
    for (i = 0; i < 4; i++) {
        int rel = arm_poll_rel(ARM_EDGE_POLL_ADDR[i]);
        uint16_t dst = arm_poll_target(ARM_EDGE_POLL_ADDR[i],
                                       ARM_EDGE_POLL_REL[i]);
        int ok = (rel == (int)ARM_EDGE_POLL_REL[i]) && (dst == CL_R0);
        if (!ok) {
            fails++;
            CHK_PRINT("FAIL  poll %d @0x%04X: computed rel 0x%02X, image "
                      "0x%02X, lands 0x%04X (want 0x%04X)\n",
                      i + 1, (unsigned)ARM_EDGE_POLL_ADDR[i],
                      (unsigned)(rel & 0xFF), (unsigned)ARM_EDGE_POLL_REL[i],
                      (unsigned)dst, (unsigned)CL_R0);
        } else {
            CHK_PRINT("ok    poll %d @0x%04X rel 0x%02X -> 0x%04X = "
                      "_cap_loop+1\n", i + 1,
                      (unsigned)ARM_EDGE_POLL_ADDR[i],
                      (unsigned)ARM_EDGE_POLL_REL[i], (unsigned)dst);
        }
    }
    /* ...and the idle gate's poll must branch INSIDE cap_arm (0x9F97),
     * which is the other half of guard check 5: exactly four polls leave
     * the area and exactly one does not. */
    {
        uint16_t dst = arm_poll_target(ARM_IDLE_POLL_ADDR, 0x29u);
        if (!(dst > CAPARM_ORG && dst < CAP_CAPTURE)) {
            fails++;
            CHK_PRINT("FAIL  idle-gate poll lands 0x%04X, outside cap_arm\n",
                      (unsigned)dst);
        } else {
            CHK_PRINT("ok    idle-gate poll @0x%04X rel 0x29 -> 0x%04X, "
                      "inside cap_arm\n", (unsigned)ARM_IDLE_POLL_ADDR,
                      (unsigned)dst);
        }
    }

    /* ---- 3: bit sequence == edge list, on a dense grid ---------------- */
    {
        uint8_t bits[32];
        double edges[64];
        rbarf_wire w;
        rbarf_edges e;
        uint32_t x = 0xBEEFu;
        int bad = 0;
        long step;

        for (i = 0; i < 32; i++) {
            x = (x * 1103515245u + 12345u) & 0x7FFFFFFFu;
            bits[i] = (uint8_t)((x >> 16) & 1u);
        }
        rbarf_wire_v23(&w, bits, 32);
        e.t_ns = edges;
        e.n = rbarf_wire_edges(&w, edges, 64);
        if (e.n != 64) {
            fails++;
            CHK_PRINT("FAIL  edge list came out %u edges, want 64\n",
                      (unsigned)e.n);
        }
        /* -1000 .. +42000 ns in 0.5 ns steps: every edge is a multiple of
         * 0.5, so this grid lands ON every one of them. */
        for (step = -2000; step <= 84000; step++) {
            double t = (double)step * 0.5;
            if (rbarf_wire_level(&w, t) != rbarf_wire_level_edges(&e, t))
                bad++;
        }
        if (bad) {
            fails++;
            CHK_PRINT("FAIL  bit-sequence vs edge-list level: %d of 86001 "
                      "grid points differ\n", bad);
        } else {
            CHK_PRINT("ok    bit-sequence level == edge-list level, 86001 "
                      "grid points incl. every edge\n");
        }
    }

    /* ---- 4: the idle gate really needs IDLE_N consecutive lows -------- */
    {
        stm8_arm_trace tr;
        uint8_t buf[8];
        gate_ctx g;
        int r;

        /* 7 lows then high forever: never idle, so the gate must burn all
         * 8 retries and return 0 without ever entering the loop. */
        g.lows = 7; g.polls = 0;
        tr.read = gate_read; tr.ctx = &g;
        r = stm8_cap_arm(buf, 4, &tr);
        if (r != 0 || tr.entered_loop || tr.idle_tries != ARM_BUSY_TRIES) {
            fails++;
            CHK_PRINT("FAIL  idle gate accepted 7 lows (r=%d entered=%d "
                      "tries=%d)\n", r, tr.entered_loop, tr.idle_tries);
        } else {
            CHK_PRINT("ok    idle gate rejects 7 consecutive lows, burns "
                      "all %d retries, returns 0\n", ARM_BUSY_TRIES);
        }

        /* 8 lows then high: idle, then the very first edge poll fires. */
        g.lows = 8; g.polls = 0;
        tr.read = gate_read; tr.ctx = &g;
        r = stm8_cap_arm(buf, 4, &tr);
        if (r != 1 || !tr.entered_loop || tr.caught_by != 1) {
            fails++;
            CHK_PRINT("FAIL  8 lows then high: r=%d entered=%d poll=%d\n",
                      r, tr.entered_loop, tr.caught_by);
        } else {
            CHK_PRINT("ok    8 lows then HIGH -> poll 1 catches it, loop "
                      "entered, A=1\n");
        }
    }

    /* ---- 5: the window is bounded, and the cycle arithmetic adds up --- */
    {
        stm8_arm_trace tr;
        uint8_t buf[8];
        unsigned long want_polls, want_cy;
        int r;

        tr.read = low_read; tr.ctx = NULL;
        r = stm8_cap_arm(buf, 4, &tr);
        /* Line low forever: the gate passes on the first try, then all 7
         * bursts of 256 comb iterations run out. */
        want_polls = (unsigned long)ARM_IDLE_N
                   + (unsigned long)ARM_BURSTS * ARM_BURST_POLLS * 4u;
        /* The comments' arithmetic, spelled out.  A JRNE is 2 cycles
         * taken and 1 not taken, so every counted loop pays (n-1)*2 + 1
         * for its branches rather than n*2.
         *
         *   mov s_arm,#8                                        1
         *   ld a,#8                                             1
         *   idle gate   8 x (btjt 2 + dec 1) + 7 x jrne 2 + 1   39   } 40 cy
         *   mov s_arm,#7                                        1    } = 2.5 us
         *   7 bursts    each  sim 1 + clr 1
         *                     + 256 comb iterations             2815
         *                       (4 x btjt 2 + dec 1 = 9, plus
         *                        255 x jrne 2 + 1  = 511
         *                        == 256 x 11 - 1)
         *                     + rim 1 + dec s_arm 1             2819
         *               plus 6 x jrne 2 + 1                     13
         *   clr a + ret                                         5
         *                                                   -------
         *                                                     19793 cy
         *                                    = 1.237 ms at 16 MHz  */
        want_cy = CY_MOV_LONGMEM + CY_LD_A_IMM
                + ((unsigned long)ARM_IDLE_N
                   * (CY_BTJT_NOT_TAKEN + CY_DEC_A)
                   + (unsigned long)(ARM_IDLE_N - 1) * CY_JRNE_TAKEN
                   + CY_JRNE_NOT_TAKEN)
                + CY_MOV_LONGMEM
                + (unsigned long)ARM_BURSTS
                  * (CY_SIM + CY_CLR_A
                     + ((unsigned long)ARM_BURST_POLLS * 11u - 1u)
                     + CY_RIM + CY_DEC_LONGMEM)
                + ((unsigned long)(ARM_BURSTS - 1) * CY_JRNE_TAKEN
                   + CY_JRNE_NOT_TAKEN)
                + CY_CLR_A + CY_RET;
        if (r != 0 || tr.entered_loop || tr.bursts != ARM_BURSTS
                || tr.polls != want_polls) {
            fails++;
            CHK_PRINT("FAIL  bounded window: r=%d bursts=%d polls=%lu "
                      "(want %lu)\n", r, tr.bursts, tr.polls, want_polls);
        } else {
            CHK_PRINT("ok    line low forever -> %lu polls, %d bursts, "
                      "returns 0 (bounded)\n", tr.polls, tr.bursts);
        }
        if (tr.nominal_cy != want_cy) {
            fails++;
            CHK_PRINT("FAIL  arm nominal cycles %lu, comment arithmetic "
                      "says %lu\n", tr.nominal_cy, want_cy);
        } else {
            CHK_PRINT("ok    arm nominal cycles %lu = %.2f ms at 16 MHz "
                      "(comb 11 cy, burst 176 us, window 1.23 ms)\n",
                      tr.nominal_cy, (double)tr.nominal_cy * CY_NS / 1e6);
        }
    }

    /* ---- 6: the loop's fitted geometry, as the comments claim it ------ */
    {
        static const int gap_cy[SAMPLE_SLOTS] = {4, 5, 4, 4, 4, 6, 5, 8};
        int sum = 0;
        int bad = 0;
        for (i = 0; i < SAMPLE_SLOTS; i++) {
            double want = (double)sum * CY_NS;
            if (SLOT_OFFSET_NS[i] != want)
                bad++;
            sum += gap_cy[i];
        }
        if (sum != 40 || bad) {
            fails++;
            CHK_PRINT("FAIL  slot offsets do not match gaps "
                      "[4,5,4,4,4,6,5,8] (sum %d, %d bad)\n", sum, bad);
        } else {
            CHK_PRINT("ok    slot offsets == cumulative gaps "
                      "[4,5,4,4,4,6,5,8], loop = 40 cy = %.1f ns\n",
                      LOOP_NS);
        }
    }

    return fails;
}

/* ==========================================================================
 *  SECTION 8 -- A DEMO main()
 * ==========================================================================
 *  gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_CAPTURE_MAIN \
 *      -o rbarf_capture rbarf_capture.c -lm
 *  ./rbarf_capture                 # self-checks, then a sample capture
 * ========================================================================== */
#ifdef RBARF_CAPTURE_MAIN

int main(void)
{
    uint8_t data[48];
    uint8_t cap[288];
    int i, fails;
    uint16_t n;

    printf("rbarf_capture.c -- self-checks\n");
    fails = rbarf_capture_selfcheck(1);
    printf("%s: %d failure(s)\n\n", fails ? "FAIL" : "PASS", fails);

    for (i = 0; i < 48; i++)
        data[i] = (uint8_t)(i * 5 + 1);

    n = rbarf_capture_v23(data, 48, -0.0107, 385.0, 0.0, 288, 0, 0,
                          cap, (uint16_t)sizeof cap);
    printf("one production capture: nd=48, eps=-1.07 %%, t0=385 ns, "
           "%u bytes\n", (unsigned)n);
    for (i = 0; i < 32; i++)
        printf("%02X%s", cap[i], (i % 16 == 15) ? "\n" : " ");
    printf("...\n\n");

    printf("the trigger-phase cliff, computed the way cap_arm.s does:\n");
    for (i = 0; i < 5; i++) {
        static const double eps[5] = {-0.05, -0.03, -0.0107, 0.0, 0.06};
        printf("  eps %+6.2f %%   t0_crit = 1250 - 562.5/(1+eps) = "
               "%6.1f ns\n", eps[i] * 100.0, 1250.0 - 562.5 / (1.0 + eps[i]));
    }
    return fails ? 1 : 0;
}

#endif /* RBARF_CAPTURE_MAIN */
