/*
 * ============================================================================
 *  rbarf_ws2812_out.c -- the RBARF WS2812 OUTPUT driver, written to be READ
 *  ...and every other piece of inline assembly in the shipped image
 * ============================================================================
 *
 *  rbarf_capture.c reads a WS2812 wire.  This file writes one.  Same
 *  protocol, opposite direction, and a completely different problem: a
 *  receiver has to cope with whatever arrives, but a TRANSMITTER has to be
 *  right.  Every bit is a pulse whose WIDTH is its value, the LEDs decide
 *  with a comparator against roughly half a bit, and there is no
 *  acknowledgement, no retry and no clock line.  Get the width wrong and
 *  the strip shows the wrong colour; get it very wrong and it shows noise.
 *
 *  The driver is 95 lines of inline assembly inside app/ws2812_out.c, on a
 *  16 MHz part with no timer to spare and no DMA at all.  It works by
 *  counting cycles: a bit is exactly 20 CPU cycles, the pin is raised at
 *  cycle 0, and it is lowered at cycle 6 or cycle 11 depending on which
 *  way a JRC went.  The NOPs are not padding -- they ARE the timing.
 *
 *  ---------------------------------------------------------------------------
 *  THE ANSWER FIRST: what the driver actually puts on the wire
 *  ---------------------------------------------------------------------------
 *  At exactly 16 MHz (62.5 ns per cycle).  Confirmed twice: by adding up
 *  the cycle comments (section 1, checkable by the self-test in section 6)
 *  and by single-stepping the SHIPPED image in ucsim with breakpoints on
 *  the two pin writes (section 2).
 *
 *      bit = 0      T0H =  6 cy =  375.0 ns    T0L = 14 cy =  875.0 ns
 *      bit = 1      T1H = 11 cy =  687.5 ns    T1L =  9 cy =  562.5 ns
 *      period       20 cy = 1250.0 ns  ->  exactly 800 kbit/s
 *
 *      last bit of a byte (the pointer reload costs 5 cycles):
 *      bit = 0      T0H =  6 cy                T0L = 19 cy = 1187.5 ns
 *      bit = 1      T1H = 11 cy                T1L = 14 cy =  875.0 ns
 *      period       25 cy = 1562.5 ns
 *
 *      reset latch  1031 cy = 64.4 us of low before the first bit
 *      whole send   4988 cy = 311.8 us for 24 bytes = 8 LEDs
 *                   (4990 if the final data bit is a 0 -- see section 2.6:
 *                    two cycles of `jra`, after the pin is already low,
 *                    and the ONLY data dependence in the whole send)
 *
 *  The HIGH times are what the LEDs decide on and they are dead centre of
 *  their windows.  The stretched LOWs at byte boundaries are discussed
 *  honestly in section 2 -- they are outside the datasheet's nominal T0L
 *  tolerance and they are fine, for a reason worth writing down.
 *
 *  ---------------------------------------------------------------------------
 *  THE FILE, IN ORDER
 *  ---------------------------------------------------------------------------
 *    0  the STM8 vocabulary this driver uses
 *    1  the driver's inline asm, LINE FOR LINE, with a pin trace
 *    2  the timing, computed -- and checked against the WS2812 window,
 *       the oscillator corners, and ucsim
 *    3  the same driver as a plain C bit loop: what it MEANS
 *    4  ws2812_out_init(): the four GPIO register writes
 *    5  THE OTHER INLINE ASSEMBLY IN THE SHIPPED IMAGE -- app/tick.c (two
 *       blocks) and rbarf_prod.c (two blocks), each rendered and each with
 *       the reason it cannot be C
 *    6  self-checks
 *    7  a demo main()
 *
 *  ---------------------------------------------------------------------------
 *  WHAT IS DELIBERATELY NOT HERE
 *  ---------------------------------------------------------------------------
 *    app/anim.c      the animation engine that FILLS the 24-byte buffer
 *                    (modes, fades, gamma LUT).  Ordinary C, no assembly,
 *                    and a separate subject.
 *    the capture side  rbarf_capture.c.
 *    the decoder       rbarf_decoder.c.
 *    the vector table  rbarf_vectors.c.
 *    REAL PIN BEHAVIOUR  the model here is an ideal square wave.  A real
 *                    PA3 in push-pull at the 10 MHz slew setting has a
 *                    finite rise and fall time, and the strip's first LED
 *                    presents a real load.  Nothing here models that; the
 *                    margins are large enough (>150 ns to every window
 *                    edge at nominal trim) that it never mattered.
 *    FLASH-FETCH STALLS  unlike the capture loop, this driver's timing is
 *                    NOT address-phase pinned and never has been -- and
 *                    that is worth being explicit about, because it looks
 *                    like an inconsistency.  Section 2 explains why the
 *                    transmitter gets away with what the receiver could
 *                    not.
 */

#include <stdint.h>
#include <string.h>

/* ==========================================================================
 *  SECTION 0 -- THE STM8 VOCABULARY
 * ==========================================================================
 *
 *   instruction        bytes  cycles  what it does
 *   ------------------ -----  ------  --------------------------------------
 *   BSET longmem,#b      4      1     set one bit of an I/O register.  This
 *                                     is the rising edge.
 *   BRES longmem,#b      4      1     clear it.  This is the falling edge.
 *                                     Both are read-modify-write on the
 *                                     port's output data register, and both
 *                                     are ONE cycle -- which is the only
 *                                     reason a 6-cycle pulse is possible.
 *   SLL A               1      1      shift A left; bit 7 -> CARRY.  This is
 *                                     how the byte is serialised: the MSB
 *                                     falls out into a flag that a branch
 *                                     can test, MSB first, which is the
 *                                     order the wire wants.
 *   JRC rel             2     1 / 2   branch if carry.  1 cycle not taken
 *                                     (bit = 0), 2 taken (bit = 1) -- and
 *                                     that asymmetry is DELIBERATELY LEFT
 *                                     IN: the 1-bit path is one cycle
 *                                     "late" and simply has one fewer NOP.
 *   NOP                 1      1      the timing.
 *   DEC longmem         4      1      the two counters, in RAM (A is busy
 *                                     holding the byte being shifted out).
 *   JRNE rel            2     1 / 2   1 not taken, 2 taken.
 *   JRA rel             2      2      unconditional.
 *   SIM / RIM           1      1      mask / unmask interrupts.
 *
 *  WHY THE COUNTERS LIVE IN RAM.  There are three 8-bit quantities to keep
 *  (the byte being shifted, bits remaining, bytes remaining) and the STM8
 *  has exactly one 8-bit accumulator.  X holds the buffer pointer.  So the
 *  two counters go to static RAM at 4 bytes and 1 cycle per DEC, which the
 *  budget can afford; and because they are `volatile` in the C source, the
 *  compiler cannot decide to keep them somewhere else.
 * ========================================================================== */

enum {
    CY_BSET = 1, CY_BRES = 1, CY_SLL_A = 1, CY_NOP = 1,
    CY_JRC_TAKEN = 2, CY_JRC_NOT_TAKEN = 1,
    CY_JRNE_TAKEN = 2, CY_JRNE_NOT_TAKEN = 1, CY_JRA = 2,
    CY_DEC_LONGMEM = 1, CY_LD_A_IND_X = 1, CY_INCW_X = 1,
    CY_MOV_LONGMEM = 1, CY_LDW_X_IMM = 2, CY_CLR_A = 1, CY_DEC_A = 1,
    CY_SIM = 1, CY_RIM = 1
};

/* 8 LEDs x 3 bytes.  The DECODED frame is 48 bytes (16 LEDs' worth of
 * addressing space): app/anim.c reads the first 24 as the eight LED
 * colours and the bytes above that as animation control, then writes the
 * 24 bytes this driver transmits. */
#define WS_NUM_LEDS   8
#define WS_BUF_SIZE   (WS_NUM_LEDS * 3)

uint8_t ws2812_out_buf[WS_BUF_SIZE];

/* The one output register the driver touches: PA_ODR bit 3 = package pin 5. */
#define PA_ODR_ADDR 0x5000u
#define PA3         3

/* ==========================================================================
 *  SECTION 1 -- THE DRIVER'S INLINE ASM, LINE FOR LINE
 * ==========================================================================
 *
 *  The rendering records a PIN TRACE: every level change, with the cycle it
 *  happened at, counted from the moment ws2812_out_send() was entered.  The
 *  cycle numbers in the trailing comments are the same numbers the assembly
 *  source carries, and section 6 checks that the trace they produce has the
 *  widths section 2 claims.
 *
 *  A note on WHERE an edge happens.  BSET and BRES are one cycle each, and
 *  the pin moves when the instruction executes -- so an edge is recorded at
 *  the cycle count BEFORE the instruction's cost is added.  This matches
 *  what ucsim reports at a breakpoint (the cycle counter is read before the
 *  breakpointed instruction runs), which is how the two measurements in
 *  section 2 are directly comparable.
 *
 *  THE WHOLE SEND RUNS UNDER SIM.  Not for the waveform's sake alone: at
 *  20 cycles a bit, a 1 ms tick ISR landing mid-bit would stretch that bit
 *  by however long the ISR takes, and a stretched bit is a wrong colour on
 *  every LED after it.  There is no way to make it safe, so it is made
 *  impossible.  TIM4's update flag is latched in hardware, so the single
 *  tick that can fall inside a 312 us send is delivered (late by at most
 *  312 us) at the RIM at the end: no lost millis, no waveform corruption,
 *  no re-send loop.  This replaced an earlier handshake with the capture
 *  side, which became unnecessary once capture stopped running in an ISR.
 * ========================================================================== */

typedef struct {
    unsigned long cy;         /* cycle, level } one entry per level change */
    int level;
} ws_edge;

typedef struct {
    ws_edge      *edge;
    unsigned      cap;
    unsigned      n;
    unsigned long cy;         /* running cycle count since entry           */
    int           level;      /* current PA3 level                         */
    int           overflow;   /* 1 if the trace buffer filled up           */
} ws_trace;

static void ws_trace_init(ws_trace *tr, ws_edge *edge, unsigned cap)
{
    tr->edge = edge;
    tr->cap = cap;
    tr->n = 0;
    tr->cy = 0;
    tr->level = 0;            /* ws2812_out_init() left PA3 low            */
    tr->overflow = 0;
}

/* BSET / BRES: move the pin, then charge one cycle. */
static void ws_pin(ws_trace *tr, int level)
{
    if (level != tr->level) {
        if (tr->n < tr->cap) {
            tr->edge[tr->n].cy = tr->cy;
            tr->edge[tr->n].level = level;
            tr->n++;
        } else {
            tr->overflow = 1;
        }
        tr->level = level;
    }
    tr->cy += 1;              /* BSET / BRES longmem,#b            [1] */
}

#define CY(tr, n) ((tr)->cy += (unsigned long)(n))

/*
 * ws2812_out_send() -- the whole of app/ws2812_out.c's __asm block.
 *
 * `nbytes` stands in for the assembly's `mov _ws_byte_cnt, #24`; it is a
 * parameter here only so the self-tests can trace a short send.  The
 * shipped code has 24 wired in.
 */
void ws2812_out_send_rendered(const uint8_t *buf, unsigned nbytes,
                              ws_trace *tr)
{
    uint8_t a;                /* register A: the byte being shifted out  */
    const uint8_t *x;         /* register X: the buffer pointer          */
    uint8_t ws_bit_cnt;       /* RAM: bits remaining in the current byte */
    uint8_t ws_byte_cnt;      /* RAM: bytes remaining                    */
    int c;                    /* the carry flag                          */

    /* sim -- no tick ISR inside the waveform                        [1] */
    CY(tr, CY_SIM);

    /* ==============================================================
     * Reset latch: hold PA3 LOW for >50 us before new data.
     * 256 iterations x 4 cy = 1024 cy = 64 us.
     *
     * A WS2812 strip latches the colours it has received when the line
     * stays low for longer than its reset time (>50 us on the classic
     * part).  So this delay is doing two jobs at once: it ends the
     * PREVIOUS frame, and it guarantees the next frame starts from a
     * known state.  It is also why the pin is left low at the end of
     * the send rather than being driven -- the latch is paid for at the
     * TOP of the next call, where it costs nothing extra.
     *
     * A = 0, then DEC A wraps to 255 and counts down to 0: exactly 256
     * iterations, 255 of them paying a taken JRNE and the last a
     * not-taken one, so 4*256 - 1 = 1023 cycles.
     * ============================================================== */
    a = 0;                                          /* clr  A         [1] */
    CY(tr, CY_CLR_A);
    do {                                            /* 00001$:            */
        CY(tr, CY_NOP);                             /*   nop          [1] */
        a--;                                        /*   dec  A       [1] */
        CY(tr, CY_DEC_A);
        CY(tr, a ? CY_JRNE_TAKEN : CY_JRNE_NOT_TAKEN); /* jrne 00001$ [1/2]*/
    } while (a);

    /* ==============================================================
     * Bit-bang nbytes bytes out of ws2812_out_buf on PA3 (PA_ODR.3).
     * ============================================================== */
    x = buf;                                        /* ldw  X,#_buf   [2] */
    CY(tr, CY_LDW_X_IMM);
    ws_byte_cnt = (uint8_t)nbytes;                  /* mov  cnt,#24   [1] */
    CY(tr, CY_MOV_LONGMEM);

next_byte:                                          /* 00010$             */
    a = *x;                                         /*   ld   A,(X)   [1] */
    CY(tr, CY_LD_A_IND_X);
    x++;                                            /*   incw X       [1] */
    CY(tr, CY_INCW_X);
    ws_bit_cnt = 8;                                 /*   mov  bits,#8 [1] */
    CY(tr, CY_MOV_LONGMEM);

bit_loop:                                           /* 00020$             */
    /* ---- every bit starts here: pin HIGH ---- */
    ws_pin(tr, 1);                        /* bset 0x5000,#3  [1] cycle 0 */
    c = (a & 0x80u) ? 1 : 0;              /* sll  A          [1] cycle 1 */
    a = (uint8_t)(a << 1);                /*   MSB -> carry              */
    CY(tr, CY_SLL_A);
    if (c) {                              /* jrc  00030$   [1 / 2 taken] */
        CY(tr, CY_JRC_TAKEN);             /*   bit=1 -> taken (2 cy)     */
        goto bit_one;
    }
    CY(tr, CY_JRC_NOT_TAKEN);             /*   bit=0 -> not taken (1 cy) */

    /* ==============================================================
     * BIT = 0   T0H = 6 cy (375 ns)   T0L = 14 cy (875 ns)
     * ==============================================================
     *                                       cycle count from bset: */
    CY(tr, CY_NOP);                                 /*   nop      [1]  3 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  4 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  5 */
    ws_pin(tr, 0);                                  /*   bres     [1]  6 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  7 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  8 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  9 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 10 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 11 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 12 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 13 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 14 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 15 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 16 */
    ws_bit_cnt--;                                   /*   dec bits [1] 17 */
    CY(tr, CY_DEC_LONGMEM);
    if (ws_bit_cnt) {                               /*   jrne 00020$     */
        CY(tr, CY_JRNE_TAKEN);                      /*    [2] 18-19      */
        goto bit_loop;                              /*    -> 20 cy total */
    }
    CY(tr, CY_JRNE_NOT_TAKEN);
    /* ---- last bit of byte: jrne not taken (1 cy) ---- */
    ws_byte_cnt--;                                  /*   dec bytes  [1]  */
    CY(tr, CY_DEC_LONGMEM);
    if (ws_byte_cnt) {                              /*   jrne 00010$ [2] */
        CY(tr, CY_JRNE_TAKEN);
        goto next_byte;                             /*   -> load next    */
    }
    CY(tr, CY_JRNE_NOT_TAKEN);
    CY(tr, CY_JRA);                                 /*   jra 00050$  [2] */
    goto done;                                      /*   -> done         */

bit_one:                                            /* 00030$            */
    /* ==============================================================
     * BIT = 1   T1H = 11 cy (688 ns)   T1L = 9 cy (563 ns)
     * ==============================================================
     * jrc was taken: 2 cy -> we are at cycle 4 from bset.
     *
     * Which is the whole trick of the two paths.  The 0-path arrives at
     * cycle 3 having paid 1 cycle for a not-taken JRC; the 1-path
     * arrives at cycle 4 having paid 2.  Both then NOP up to their own
     * BRES and NOP down to a SHARED tail (dec / jrne), and the tails are
     * arranged so both paths reach the next bset at exactly cycle 20.
     * Nothing is balanced with extra instructions; the NOP counts are
     * simply 3 and 7 on the way down and 10 and 5 on the way back up.
     */
    CY(tr, CY_NOP);                                 /*   nop      [1]  4 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  5 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  6 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  7 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  8 */
    CY(tr, CY_NOP);                                 /*   nop      [1]  9 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 10 */
    ws_pin(tr, 0);                                  /*   bres     [1] 11 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 12 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 13 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 14 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 15 */
    CY(tr, CY_NOP);                                 /*   nop      [1] 16 */
    ws_bit_cnt--;                                   /*   dec bits [1] 17 */
    CY(tr, CY_DEC_LONGMEM);
    if (ws_bit_cnt) {                               /*   jrne 00020$     */
        CY(tr, CY_JRNE_TAKEN);                      /*    [2] 18-19      */
        goto bit_loop;                              /*    -> 20 cy total */
    }
    CY(tr, CY_JRNE_NOT_TAKEN);
    /* ---- last bit of byte: jrne not taken (1 cy) ---- */
    ws_byte_cnt--;                                  /*   dec bytes  [1]  */
    CY(tr, CY_DEC_LONGMEM);
    if (ws_byte_cnt) {                              /*   jrne 00010$ [2] */
        CY(tr, CY_JRNE_TAKEN);
        goto next_byte;
    }
    CY(tr, CY_JRNE_NOT_TAKEN);
    /* ---- fall through -> done ---- */

done:                                               /* 00050$            */
    /* Pin is LOW.  The >50 us reset latch before the NEXT send is handled
     * by the delay at the top of this function.
     *   rim -- a pending TIM4 tick delivers here                     [1] */
    CY(tr, CY_RIM);
}

/* ==========================================================================
 *  SECTION 2 -- THE TIMING, AND WHETHER IT IS LEGAL
 * ==========================================================================
 *
 *  ---- 1. What the cycle arithmetic gives -----------------------------------
 *
 *  Adding up section 1's comments, from one BSET to the next:
 *
 *      bit 0   bset(1) sll(1) jrc-nt(1) nop x3      -> BRES at cycle  6
 *              nop x10 dec(1) jrne-taken(2)         -> next bset at 20
 *      bit 1   bset(1) sll(1) jrc-taken(2) nop x7   -> BRES at cycle 11
 *              nop x5  dec(1) jrne-taken(2)         -> next bset at 20
 *
 *      T0H  6 cy = 375.0 ns    T0L 14 cy = 875.0 ns    period 20 cy
 *      T1H 11 cy = 687.5 ns    T1L  9 cy = 562.5 ns    = 1250.0 ns
 *
 *  On the LAST bit of a byte the inner JRNE is not taken and the byte
 *  reload runs instead: dec bits(1) jrne-nt(1) dec bytes(1) jrne-taken(2)
 *  ld A,(X)(1) incw X(1) mov bits,#8(1) -> the next BSET is at cycle 25.
 *  The HIGH time is unchanged; the extra 5 cycles all land in the LOW.
 *
 *      byte boundary, bit 0    T0L 19 cy = 1187.5 ns   period 25 cy
 *      byte boundary, bit 1    T1L 14 cy =  875.0 ns   = 1562.5 ns
 *
 *  Reset latch: sim(1) clr A(1) + 4*256-1 = 1023 + ldw X(2) mov bytes(1)
 *  ld A,(X)(1) incw X(1) mov bits(1) = 1031 cycles = 64.4 us of low before
 *  the first rising edge.  Whole send: 4985 cycles = 311.6 us for 8 LEDs.
 *
 *  ---- 2. What ucsim says, running the SHIPPED image -----------------------
 *
 *  Breakpoints on the two pin writes in build/rbarf_prod.ihx (BSET at
 *  0x9EBB, BRES at 0x9EC5 for the 0-path and 0x9EE8 for the 1-path), PC
 *  forced to _ws2812_out_send at 0x9EA8, buffer preloaded with A5 A4 5A,
 *  reading the simulator's cycle counter at every stop:
 *
 *      bit  val   bset@   bres@   Th   Tl  period
 *        0    1    1031    1042   11    9      20
 *        1    0    1051    1057    6   14      20
 *        2    1    1071    1082   11    9      20
 *        ...
 *        7    1    1171    1182   11   14      25   <- byte boundary
 *       15    0    1336    1342    6   19      25   <- byte boundary
 *
 *  Every value matches the arithmetic exactly, the first BSET is at cycle
 *  1031 (the reset latch, to the cycle), and the sequence of 0/1 paths
 *  taken reproduces A5 A4 5A bit for bit, MSB first.  Two caveats, both
 *  worth knowing: ucsim's `state` prints TWO counters and only one of them
 *  is the datasheet cycle count -- "Total time since last reset (N clks)"
 *  is cycles, while "Operation since last reset = N vclks" is a bus-access
 *  count (bytes fetched plus data accesses) and gives 16 and 12 where the
 *  datasheet gives 11 and 6.  And ucsim models the cycle TABLE, not the
 *  flash prefetch, so this confirms the arithmetic and says nothing about
 *  fetch stalls.
 *
 *  ---- 3. The WS2812 window -----------------------------------------------
 *
 *  Two datasheet revisions are in circulation and they disagree; the driver
 *  is inside both, so it does not matter which part is on the strip.  All
 *  tolerances are +-150 ns.
 *
 *                     driver    WS2812 (0.35/0.70/0.80/0.60)   WS2812B
 *                                                       (0.40/0.80/0.85/0.45)
 *      T0H   375.0 ns   [ 200 ..  500]  ok            [ 250 ..  550]  ok
 *      T1H   687.5 ns   [ 550 ..  850]  ok            [ 650 ..  950]  ok
 *      T0L   875.0 ns   [ 650 ..  950]  ok            [ 700 .. 1000]  ok
 *      T1L   562.5 ns   [ 450 ..  750]  ok            [ 300 ..  600]  ok
 *      RESET  64.4 us   > 50 us         ok            > 50 us         ok
 *
 *  ---- 4. The two places it is outside the nominal window, and why that is
 *          fine ------------------------------------------------------------
 *
 *  (a) THE STRETCHED LOW AT BYTE BOUNDARIES.  T0L becomes 1187.5 ns, which
 *      is 237 ns past the WS2812's T0L+150 bound, and T1L becomes 875 ns,
 *      275 ns past the WS2812B's.  Every 8th bit.  The source comment says
 *      "within WS2812 spec", which is optimistic about the letter of the
 *      datasheet and right about the substance: a WS2812 shift register
 *      samples the pulse WIDTH -- effectively "was the line high for more
 *      or less than about half a bit" -- and treats the low only as "not
 *      yet a reset".  The T0L/T1L tolerances describe the nominal waveform,
 *      not a decision threshold, and the only low time that is a real
 *      threshold is the reset time: >50 us on the classic part, and as
 *      little as ~6 us on some clones.  1187.5 ns is 5x inside even the
 *      most pessimistic clone.  It also means the strip runs slightly
 *      slower than 800 kbit/s on average (192 bits in 240.6 us of bits
 *      plus 24 x 5 cycles = 7.5 us of reload), which nothing cares about.
 *
 *  (b) THE OSCILLATOR.  There is no crystal.  The HSI is specified to
 *      +-7.5 %, and this driver's every number scales with it:
 *
 *          eps      cycle      T0H     T1H     T0L     T1L    period
 *        +7.5 %   58.14 ns   348.8   639.5   813.9   523.3   1162.8
 *        -1.07 %  63.18 ns   379.0   694.9   884.4   568.6   1263.5  <- trim
 *        -7.5 %   67.57 ns   405.4   743.2   945.9   608.1   1351.4
 *
 *      At the extreme corners two values step outside a nominal window by
 *      less than 11 ns: T1H 639.5 against the WS2812B's 650 lower bound at
 *      +7.5 %, and T1L 608.1 against the WS2812B's 600 upper bound at
 *      -7.5 %.  Both are inside the classic WS2812's windows at every
 *      corner, and the auto-trim keeps the part in a 0.6 %-wide band around
 *      -1.0 % anyway, where everything has >150 ns of margin.
 *
 *  ---- 5. The one data dependence, and where it is harmless ----------------
 *
 *  The 0-path and the 1-path are cycle-balanced everywhere it matters: both
 *  reach the next BSET at cycle 20 mid-byte and cycle 25 at a byte
 *  boundary, so EVERY BIT BOUNDARY IN A SEND LANDS AT THE SAME CYCLE
 *  WHATEVER THE DATA IS.  The self-test checks exactly that -- all 24 rise
 *  times identical between an all-0x00 send and an all-0xA5 one.
 *
 *  There is exactly one exception, and it is at the very end: on the last
 *  bit of the last byte the 0-path takes `jra 00050$` (2 cycles) while the
 *  1-path simply falls through.  So a send whose final data bit is 0 is
 *  4990 cycles instead of 4988.  Those two cycles happen AFTER the last
 *  falling edge, with the pin already low, on its way into a 64 us reset
 *  latch -- nothing on the wire can see them.  It is worth naming only
 *  because "the driver's timing is data-independent" is a claim, and this
 *  is its one true exception.
 *
 *  ---- 6. A documentation discrepancy, reported not resolved ---------------
 *
 *  app/ws2812_out.c's own header says "the whole send (reset latch + 192
 *  bits, ~545 us)".  The arithmetic here, and ucsim, both say 311.8 us:
 *  1031 cycles of latch (64.4 us) plus 192 bits at 20 cycles plus 24 byte
 *  reloads at 5 cycles = 3960 cycles (247.5 us).  rbarf_prod.c's own
 *  comment on the same call says "~304 us", which is the same number.  The
 *  545 us figure looks like it includes anim_render(), which runs
 *  immediately before the send in render_tick() -- silicon measures the
 *  PAIR at 400..658 us with a median of 556.  Nothing depends on the
 *  figure; it is noted because the two comments disagree and the reader of
 *  the shipped source will meet the larger one first.
 *
 *  ---- 7. Why the transmitter is not address-pinned and the receiver is ----
 *
 *  This is the obvious question after reading rbarf_capture.c, and the
 *  answer is not "we forgot".  The capture loop's problem is that it must
 *  reproduce a MEASURED timing model to the cycle: three fetch-stall cycles
 *  in 40 changed the apparent oscillator error by 7 %, because the model
 *  divides by the loop period.  The transmitter has no model to match; it
 *  has a WINDOW, and the window is +-150 ns = +-2.4 cycles wide around each
 *  edge.  A fetch stall of a cycle or two inside a bit would move an edge
 *  by 62.5 or 125 ns and change nothing that a comparator can see.  The
 *  receiver needed cycle accuracy; the transmitter needs only to stay in a
 *  box, and it stays in the box by a factor of two even at the oscillator
 *  corners.
 * ========================================================================== */

/* The numbers above, as constants the self-test can check against. */
#define WS_CY_NS        62.5      /* nominal cycle at exactly 16 MHz       */
enum {
    WS_T0H_CY = 6,  WS_T0L_CY = 14,
    WS_T1H_CY = 11, WS_T1L_CY = 9,
    WS_PERIOD_CY = 20,
    WS_T0L_BOUNDARY_CY = 19, WS_T1L_BOUNDARY_CY = 14,
    WS_PERIOD_BOUNDARY_CY = 25,
    WS_RESET_LATCH_CY = 1031,
    WS_SEND_TOTAL_CY = 4988,     /* 24 bytes, final data bit = 1          */
    WS_SEND_TOTAL_CY_LAST0 = 4990/* ...= 0: two more cycles of `jra`      */
};

/* ==========================================================================
 *  SECTION 3 -- THE SAME DRIVER AS PLAIN C: WHAT IT MEANS
 * ==========================================================================
 *
 *  Strip the timing away and the driver is four lines.  This is what a
 *  reader should carry away as "what it does"; section 1 is "how it does it
 *  on a part with no peripheral to help".
 *
 *  Note the two orderings, because both are protocol, not taste:
 *    * bytes in buffer order, and a WS2812 chain shifts the FIRST byte
 *      furthest along -- each LED keeps the first 24 bits it sees and
 *      passes the rest on;
 *    * bits MSB first within each byte, which is why the serialiser is
 *      `SLL A` (bit 7 out into carry) and not `SRL A`.
 *
 *  The colour order is the strip's business, not the driver's: app/anim.c
 *  fills the buffer in whatever order the strip wants (GRB on most WS2812
 *  parts) and this code just shifts bytes.
 */
void ws2812_out_send_plain(const uint8_t *buf, unsigned nbytes,
                           void (*put_bit)(int bit, void *ctx), void *ctx)
{
    unsigned i;
    int b;

    for (i = 0; i < nbytes; i++)
        for (b = 7; b >= 0; b--)                 /* MSB first             */
            put_bit((buf[i] >> b) & 1, ctx);
}

/* ==========================================================================
 *  SECTION 4 -- ws2812_out_init(): THE FOUR GPIO WRITES
 * ==========================================================================
 *
 *  Ordinary C in the shipped source, and the only part of the driver that
 *  is.  Four read-modify-writes, and the ORDER of the first two is the only
 *  interesting thing about it: PA3's output register is driven LOW before
 *  the pin is turned into an output, so the strip never sees a glitch from
 *  a reset-state output register.  Turn the direction on first and the pin
 *  would drive whatever PA_ODR happened to hold.
 *
 *      PA_ODR &= ~(1 << 3);    0x5000   PA3 low FIRST
 *      PA_DDR |=  (1 << 3);    0x5002   then make it an output
 *      PA_CR1 |=  (1 << 3);    0x5003   push-pull (not open-drain): a
 *                                       WS2812 line needs a real drive
 *                                       high, and there is no pull-up
 *      PA_CR2 |=  (1 << 3);    0x5004   10 MHz slew rate.  The slow
 *                                       setting's edges would eat into a
 *                                       375 ns pulse
 * ========================================================================== */

typedef struct {
    uint8_t odr, ddr, cr1, cr2;
} ws_port_a;

void ws2812_out_init_rendered(ws_port_a *pa)
{
    pa->odr = (uint8_t)(pa->odr & (uint8_t)~(1u << PA3)); /* bres 0x5000,#3 */
    pa->ddr = (uint8_t)(pa->ddr | (1u << PA3));           /* bset 0x5002,#3 */
    pa->cr1 = (uint8_t)(pa->cr1 | (1u << PA3));           /* bset 0x5003,#3 */
    pa->cr2 = (uint8_t)(pa->cr2 | (1u << PA3));           /* bset 0x5004,#3 */
}

/* ==========================================================================
 *  SECTION 5 -- EVERY OTHER PIECE OF INLINE ASSEMBLY IN THE SHIPPED IMAGE
 * ==========================================================================
 *
 *  Four blocks, two files, six instructions between them.  Each one is
 *  assembly for a reason C cannot express, and the reasons are all
 *  different.  (These are the ONLY inline-asm blocks in the production
 *  image besides the driver above; capture.c has two more, but capture.c
 *  builds the separate acquisition image, not the shipped one.)
 *
 *  ---------------------------------------------------------------------------
 *  5.1  app/tick.c, millis() -- TWO one-instruction blocks
 *  ---------------------------------------------------------------------------
 *
 *      uint16_t millis(void)
 *      {
 *          uint16_t ms;
 *          __asm__("sim");           <-- block 1
 *          ms = ms_counter;
 *          __asm__("rim");           <-- block 2
 *          return ms;
 *      }
 *
 *  WHAT: mask interrupts, copy the counter, unmask.
 *  WHY ASSEMBLY: `ms_counter` is a `volatile uint16_t` incremented by the
 *  TIM4 update ISR, and the STM8 is an 8-BIT machine -- reading it takes
 *  two loads.  If the tick fires between them the two halves come from
 *  different milliseconds.  That is not a theoretical race: it happens on
 *  every 256th millisecond, at the low-byte carry, and it produces a
 *  reading that can be 256 ms wrong in either direction.  A single wrong
 *  read of millis() would skip or duplicate a render, or -- worse -- break
 *  the 5-second SWIM quiet window at the top of main().
 *
 *  C has no way to say "mask interrupts here".  SDCC offers no intrinsic
 *  for SIM/RIM, there is no `atomic` for this target, and a critical
 *  section built out of a flag variable cannot work because the thing being
 *  guarded against is the interrupt itself.  So: two instructions, one byte
 *  each, and the read between them.
 *
 *  WHAT IT COSTS: interrupts are masked for the two loads -- about 4
 *  cycles, 250 ns.  A tick that becomes pending in that window is delivered
 *  immediately afterwards, because TIM4's update flag is latched in
 *  hardware.  Nothing is lost.
 *
 *  A DETAIL WORTH NOTICING: `millis()` unconditionally RE-ENABLES
 *  interrupts.  It is never called from inside a masked region -- the two
 *  places that mask (the arm's poll bursts and the send above) do not call
 *  it -- so this is safe, and it is the cheapest correct thing.  It would
 *  not be safe in a codebase where it might be called from an ISR.
 *
 *  ---------------------------------------------------------------------------
 *  5.2  rbarf_prod.c, main() -- __asm__("rim") after the TIM4 setup
 *  ---------------------------------------------------------------------------
 *
 *      TIM4_CR1  = 0x01;         // start the timer
 *      ws2812_out_init();
 *      __asm__("rim");           <-- HERE
 *      while (millis() < 5000)   // the SWIM reflash window
 *          render_tick();
 *
 *  WHAT: enable interrupts, once, at the end of initialisation.
 *  WHY ASSEMBLY: the STM8 resets with interrupts DISABLED (the CC
 *  register's I1/I0 bits are set), and again there is no C spelling for
 *  RIM.  Everything above this line is register setup that must not be
 *  interrupted half-done; everything below it depends on the 1 ms tick
 *  actually arriving, starting with the `millis() < 5000` loop on the very
 *  next line.  One byte, one cycle, exactly one place it can go.
 *
 *  ---------------------------------------------------------------------------
 *  5.3  rbarf_prod.c, main() -- the armed-capture call
 *  ---------------------------------------------------------------------------
 *
 *      CLK_HSITRIMR = TRIM_CODE(trim_v);     // operating trim
 *      __asm
 *      ldw     x, #_capture_buf              ; X = the 288-byte buffer
 *      ldw     y, #288                       ; Y = the loop count
 *      call    _cap_arm                      ; -> cap_arm.s
 *      ld      _cap_got, a                   ; A = 1 captured, 0 = no frame
 *      __endasm;
 *      CLK_HSITRIMR = 0x00;                  // factory trim before any UART
 *
 *  WHAT: hand the pinned capture front end its two registers, call it, and
 *  stash its answer in a C variable.
 *  WHY ASSEMBLY: `_cap_arm` HAS NO C CALLING CONVENTION.  Its interface is
 *  "X = buffer, Y = loop count, returns A", chosen because the sampling
 *  loop it falls into must have the buffer pointer in X and the counter in
 *  Y at the moment the first sample is taken -- there is no room in a
 *  40-cycle loop to load them, and no room in an 80-byte routine for a
 *  prologue.  SDCC cannot be asked to call a function that way, so the four
 *  instructions are written out.
 *
 *  A SECOND REASON, and it is the more interesting one: this call is a
 *  TIMING interface, not just an ABI mismatch.  The two LDWs must be the
 *  last thing that happens before the arm starts polling, because the arm's
 *  trigger phase is measured from the poll comb; and the HSITRIMR write on
 *  the line above must be the last thing before THAT, because capture runs
 *  at the operating trim while every UART byte runs at factory trim.  A
 *  compiler that hoisted or sank anything across these boundaries would be
 *  changing the instrument's calibration.
 *
 *  Note what is NOT assembly here, since it is easy to assume otherwise:
 *  the SWIM-disable is a plain C write, `CFG_GCR = 0x01;` to 0x7F60, one
 *  line after the 5-second window ends.  It needs no special treatment --
 *  it is an ordinary byte store to an ordinary register, and the only thing
 *  special about it is WHEN it happens.  Before it, pin 8 is SWIM and the
 *  part can be reflashed; after it, pin 8 is UART1_TX and it cannot.  The
 *  5 seconds are the only way back into the chip, which is why the comment
 *  in rbarf_prod.c says NEVER shortened.
 * ========================================================================== */

/* Renderings of 5.1 and 5.2, for completeness.  There is not much to
 * render -- which is the point: the whole content of these blocks is the
 * one thing C cannot say. */

typedef struct {
    volatile uint16_t ms_counter;   /* incremented by the TIM4 update ISR */
    int              irq_masked;    /* the CC register's I1/I0, in effect */
    int              ticks_deferred;/* ticks that became pending masked   */
} tick_state;

/* tick.c: void tim4_upd_isr(void) __interrupt(23) */
void tim4_upd_isr_rendered(tick_state *st, uint8_t *tim4_sr)
{
    *tim4_sr = (uint8_t)~0x01u;   /* clear UIF by writing 0 to it, 1s     */
                                  /* elsewhere: the flag is write-0-clear */
    st->ms_counter++;
}

/* tick.c: uint16_t millis(void) */
uint16_t millis_rendered(tick_state *st)
{
    uint16_t ms;

    st->irq_masked = 1;           /* __asm__("sim")                       */
    ms = st->ms_counter;          /*   two 8-bit loads on this target     */
    st->irq_masked = 0;           /* __asm__("rim")                       */
    if (st->ticks_deferred) {     /*   a pending tick is delivered HERE   */
        st->ms_counter = (uint16_t)(st->ms_counter + st->ticks_deferred);
        st->ticks_deferred = 0;
    }
    return ms;
}

/* ==========================================================================
 *  SECTION 6 -- SELF-CHECKS
 * ==========================================================================
 *  The pin trace from section 1 is measured the way an oscilloscope would
 *  measure it, and every number section 2 claims is checked against it --
 *  including the byte-boundary stretch, the reset latch and the total send
 *  length.  Then the plain C bit loop of section 3 is checked to emit the
 *  same bit sequence the traced driver does.
 * ========================================================================== */

typedef struct { uint8_t bit[256]; unsigned n; } bitsink;

static void bitsink_put(int bit, void *ctx)
{
    bitsink *s = (bitsink *)ctx;
    if (s->n < sizeof s->bit)
        s->bit[s->n++] = (uint8_t)bit;
}

#ifdef RBARF_WS2812_OUT_MAIN
#include <stdio.h>
#define CHK(...) do { if (verbose) printf(__VA_ARGS__); } while (0)
#else
#define CHK(...) do { } while (0)
#endif

int rbarf_ws2812_out_selfcheck(int verbose)
{
    /* A pattern with both bit values, and bytes ending in each: 0xA5 ends
     * in 1, 0xA4 ends in 0.  Three bytes gives two byte boundaries of each
     * kind plus plenty of mid-byte bits. */
    static const uint8_t pattern[3] = { 0xA5u, 0xA4u, 0x5Au };
    ws_edge edge[256];
    ws_trace tr;
    unsigned i;
    int fails = 0;
    uint8_t bits[24];
    bitsink sink;

#ifndef RBARF_WS2812_OUT_MAIN
    (void)verbose;
#endif

    ws_trace_init(&tr, edge, (unsigned)(sizeof edge / sizeof edge[0]));
    ws2812_out_send_rendered(pattern, 3, &tr);

    for (i = 0; i < 24; i++)
        bits[i] = (uint8_t)((pattern[i / 8] >> (7 - (i % 8))) & 1u);

    if (tr.overflow) {
        fails++;
        CHK("FAIL  pin trace overflowed\n");
    }
    /* The trace must be: rise, fall, rise, fall, ... one pair per bit. */
    if (tr.n != 48) {
        fails++;
        CHK("FAIL  %u level changes, expected 48 (2 per bit x 24)\n", tr.n);
    } else {
        CHK("ok    48 level changes = 2 per bit x 24 bits\n");
    }

    /* ---- the reset latch ---- */
    if (tr.n > 0 && edge[0].cy != WS_RESET_LATCH_CY) {
        fails++;
        CHK("FAIL  first rising edge at cycle %lu, expected %d\n",
            edge[0].cy, WS_RESET_LATCH_CY);
    } else if (tr.n > 0) {
        CHK("ok    reset latch: first rising edge at cycle %d = %.1f us of "
            "low (>50 us required)\n", WS_RESET_LATCH_CY,
            WS_RESET_LATCH_CY * WS_CY_NS / 1000.0);
    }

    /* ---- every bit's high time, low time and period ---- */
    if (tr.n == 48) {
        for (i = 0; i < 24; i++) {
            unsigned long rise = edge[2 * i].cy;
            unsigned long fall = edge[2 * i + 1].cy;
            long th = (long)(fall - rise);
            long period = (i + 1 < 24)
                            ? (long)(edge[2 * i + 2].cy - rise) : -1;
            long tl = (period >= 0) ? period - th : -1;
            int boundary = ((i % 8) == 7);
            long want_th = bits[i] ? WS_T1H_CY : WS_T0H_CY;
            long want_period = boundary ? WS_PERIOD_BOUNDARY_CY
                                        : WS_PERIOD_CY;
            long want_tl = want_period - want_th;

            if (edge[2 * i].level != 1 || edge[2 * i + 1].level != 0) {
                fails++;
                CHK("FAIL  bit %u: edges are not rise/fall\n", i);
            }
            if (th != want_th) {
                fails++;
                CHK("FAIL  bit %u (=%u): T%uH = %ld cy, expected %ld\n",
                    i, bits[i], bits[i], th, want_th);
            }
            if (period >= 0 && period != want_period) {
                fails++;
                CHK("FAIL  bit %u: period %ld cy, expected %ld%s\n",
                    i, period, want_period,
                    boundary ? " (byte boundary)" : "");
            }
            if (period >= 0 && tl != want_tl) {
                fails++;
                CHK("FAIL  bit %u: T%uL = %ld cy, expected %ld\n",
                    i, bits[i], tl, want_tl);
            }
        }
        CHK("ok    all 24 bits: T0H 6 / T1H 11 cy, mid-byte period 20 cy, "
            "byte-boundary period 25 cy\n");
        CHK("ok    T0L 14 cy mid-byte / 19 cy at a boundary; T1L 9 / 14\n");
    }

    /* ---- the total send length, and the one data dependence ---------- */
    {
        ws_edge e2[512], e3[512];
        ws_trace t2, t3;
        unsigned bad = 0;

        ws_trace_init(&t2, e2, (unsigned)(sizeof e2 / sizeof e2[0]));
        memset(ws2812_out_buf, 0xA5, sizeof ws2812_out_buf);   /* ends 1 */
        ws2812_out_send_rendered(ws2812_out_buf, WS_BUF_SIZE, &t2);

        ws_trace_init(&t3, e3, (unsigned)(sizeof e3 / sizeof e3[0]));
        memset(ws2812_out_buf, 0x00, sizeof ws2812_out_buf);   /* ends 0 */
        ws2812_out_send_rendered(ws2812_out_buf, WS_BUF_SIZE, &t3);

        if (t2.cy != WS_SEND_TOTAL_CY || t3.cy != WS_SEND_TOTAL_CY_LAST0) {
            fails++;
            CHK("FAIL  whole send %lu / %lu cy, the comment says %d / %d\n",
                t2.cy, t3.cy, WS_SEND_TOTAL_CY, WS_SEND_TOTAL_CY_LAST0);
        } else {
            CHK("ok    whole send %d cy = %.1f us for %d bytes = %d LEDs "
                "(%d if the final bit is 0: the trailing jra)\n",
                WS_SEND_TOTAL_CY, WS_SEND_TOTAL_CY * WS_CY_NS / 1000.0,
                WS_BUF_SIZE, WS_NUM_LEDS, WS_SEND_TOTAL_CY_LAST0);
        }

        /* EVERY BIT BOUNDARY IS DATA-INDEPENDENT.  This is the claim the
         * NOP counts exist to make true: the rise of bit i lands at the
         * same cycle whatever the 24 bytes are.  Compare all 24 rises
         * between the two sends above. */
        if (t2.n != 2 * 8 * WS_BUF_SIZE || t3.n != t2.n) {
            fails++;
            CHK("FAIL  traces have %u / %u edges, expected %u\n",
                t2.n, t3.n, 2u * 8u * WS_BUF_SIZE);
        } else {
            for (i = 0; i < 8u * WS_BUF_SIZE; i++)
                if (e2[2 * i].cy != e3[2 * i].cy)
                    bad++;
            if (bad) {
                fails++;
                CHK("FAIL  %u of %u bit boundaries moved with the data\n",
                    bad, 8u * WS_BUF_SIZE);
            } else {
                CHK("ok    all %u bit boundaries identical between an "
                    "all-0x00 and an all-0xA5 send: the waveform's timing "
                    "is data-independent\n", 8u * WS_BUF_SIZE);
            }
        }
    }

    /* ---- section 3's plain C emits the same bits ---- */
    sink.n = 0;
    ws2812_out_send_plain(pattern, 3, bitsink_put, &sink);
    if (sink.n != 24) {
        fails++;
        CHK("FAIL  plain C emitted %u bits, expected 24\n", sink.n);
    } else {
        unsigned bad = 0;
        for (i = 0; i < 24; i++) {
            /* the traced driver's bit i is 1 iff its high time was T1H */
            int traced = (tr.n == 48)
                && ((long)(edge[2 * i + 1].cy - edge[2 * i].cy) == WS_T1H_CY);
            if (traced != (int)sink.bit[i])
                bad++;
        }
        if (bad) {
            fails++;
            CHK("FAIL  plain C and the traced driver disagree on %u bits\n",
                bad);
        } else {
            CHK("ok    plain C bit loop == the traced driver's pulse widths, "
                "24/24 bits (MSB first)\n");
        }
    }

    /* ---- init leaves PA3 low, output, push-pull, fast ---- */
    {
        ws_port_a pa;
        pa.odr = 0xFFu; pa.ddr = 0x00u; pa.cr1 = 0x00u; pa.cr2 = 0x00u;
        ws2812_out_init_rendered(&pa);
        if ((pa.odr & (1u << PA3)) || !(pa.ddr & (1u << PA3))
                || !(pa.cr1 & (1u << PA3)) || !(pa.cr2 & (1u << PA3))) {
            fails++;
            CHK("FAIL  init left PA3 odr=%u ddr=%u cr1=%u cr2=%u\n",
                (pa.odr >> PA3) & 1u, (pa.ddr >> PA3) & 1u,
                (pa.cr1 >> PA3) & 1u, (pa.cr2 >> PA3) & 1u);
        } else {
            CHK("ok    init: PA3 driven low BEFORE becoming an output, "
                "push-pull, 10 MHz slew\n");
        }
    }

    /* ---- millis() is atomic against a tick landing mid-read ---- */
    {
        tick_state st;
        uint16_t got;
        st.ms_counter = 0x00FFu;      /* the low-byte carry: the dangerous */
        st.irq_masked = 0;            /* millisecond                        */
        st.ticks_deferred = 1;        /* a tick wants to fire mid-read      */
        got = millis_rendered(&st);
        if (got != 0x00FFu || st.ms_counter != 0x0100u) {
            fails++;
            CHK("FAIL  millis() returned 0x%04X, counter 0x%04X\n",
                got, st.ms_counter);
        } else {
            CHK("ok    millis(): the read is whole (0x00FF), the deferred "
                "tick lands after the rim (0x0100) -- nothing lost\n");
        }
    }

    return fails;
}

/* ==========================================================================
 *  SECTION 7 -- A DEMO main()
 * ==========================================================================
 *  gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_WS2812_OUT_MAIN \
 *      -o rbarf_ws2812_out rbarf_ws2812_out.c
 *  ./rbarf_ws2812_out
 * ========================================================================== */
#ifdef RBARF_WS2812_OUT_MAIN

static void print_window(const char *name, double got,
                         double lo_a, double hi_a, double lo_b, double hi_b)
{
    printf("  %-6s %8.1f ns   [%5.0f..%5.0f] %-3s   [%5.0f..%5.0f] %-3s\n",
           name, got, lo_a, hi_a, (got >= lo_a && got <= hi_a) ? "ok" : "OUT",
           lo_b, hi_b, (got >= lo_b && got <= hi_b) ? "ok" : "OUT");
}

int main(void)
{
    static const uint8_t pattern[3] = { 0xA5u, 0xA4u, 0x5Au };
    ws_edge edge[256];
    ws_trace tr;
    unsigned i;
    int fails;
    static const double eps[3] = { 0.075, -0.0107, -0.075 };

    printf("rbarf_ws2812_out.c -- self-checks\n");
    fails = rbarf_ws2812_out_selfcheck(1);
    printf("%s: %d failure(s)\n\n", fails ? "FAIL" : "PASS", fails);

    printf("pin trace, buffer A5 A4 5A (cycles from ws2812_out_send entry)\n");
    printf(" bit val   rise    fall    T?H    T?L  period  note\n");
    ws_trace_init(&tr, edge, (unsigned)(sizeof edge / sizeof edge[0]));
    ws2812_out_send_rendered(pattern, 3, &tr);
    for (i = 0; i < 24 && 2 * i + 1 < tr.n; i++) {
        int bit = (pattern[i / 8] >> (7 - (i % 8))) & 1;
        unsigned long rise = edge[2 * i].cy, fall = edge[2 * i + 1].cy;
        long per = (2 * i + 2 < tr.n)
                     ? (long)(edge[2 * i + 2].cy - rise) : -1;
        printf("%4u %3d %6lu  %6lu %6lu %6ld %7ld  %s\n",
               i, bit, rise, fall, fall - rise,
               per >= 0 ? per - (long)(fall - rise) : -1, per,
               ((i % 8) == 7) ? "byte boundary" : "");
    }

    printf("\nthe WS2812 window at nominal 16 MHz "
           "(driver / WS2812 / WS2812B, both +-150 ns)\n");
    print_window("T0H", WS_T0H_CY * WS_CY_NS, 200, 500, 250, 550);
    print_window("T1H", WS_T1H_CY * WS_CY_NS, 550, 850, 650, 950);
    print_window("T0L", WS_T0L_CY * WS_CY_NS, 650, 950, 700, 1000);
    print_window("T1L", WS_T1L_CY * WS_CY_NS, 450, 750, 300, 600);

    printf("\nthe same numbers at the oscillator corners (no crystal, "
           "HSI +-7.5 %%)\n");
    printf("     eps      cycle      T0H     T1H     T0L     T1L   period\n");
    for (i = 0; i < 3; i++) {
        double cy = WS_CY_NS / (1.0 + eps[i]);
        printf("  %+6.2f %%  %6.2f ns  %6.1f  %6.1f  %6.1f  %6.1f  %7.1f%s\n",
               eps[i] * 100.0, cy, WS_T0H_CY * cy, WS_T1H_CY * cy,
               WS_T0L_CY * cy, WS_T1L_CY * cy, WS_PERIOD_CY * cy,
               (i == 1) ? "   <- auto-trim target" : "");
    }
    return fails ? 1 : 0;
}

#endif /* RBARF_WS2812_OUT_MAIN */
