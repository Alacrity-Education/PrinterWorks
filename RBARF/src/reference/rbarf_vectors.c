/*
 * ============================================================================
 *  rbarf_vectors.c -- the RBARF interrupt vector table, written to be READ
 * ============================================================================
 *
 *  Twenty-five lines of assembly (vectors_prod.s), two live entries, and a
 *  96-byte hole in the middle that the firmware fills with DECODER CODE.
 *  It is the smallest source file in the project and the one that most
 *  clearly shows what an 8 KB budget does to a design.
 *
 *  ---------------------------------------------------------------------------
 *  HOW AN STM8 VECTOR TABLE WORKS, because the trick depends on it
 *  ---------------------------------------------------------------------------
 *  On most architectures a vector table holds ADDRESSES: the CPU reads a
 *  pointer and jumps through it.  On the STM8 it holds INSTRUCTIONS.  Reset
 *  and every interrupt set PC to a fixed slot -- 0x8000 for reset, 0x8004
 *  for TRAP, 0x8008 + 4*n for IRQn -- and simply START EXECUTING THERE.
 *  Each slot is 4 bytes, which is exactly the size of one `INT` instruction:
 *
 *      82 hh mm ll        INT $hhmmll   -- "interrupt jump" to a 24-bit
 *                                         address; the assembler's `int`
 *                                         directive emits it
 *
 *  Two consequences, and the whole file follows from them:
 *
 *    1. A slot for a source that can never fire does not need to contain
 *       anything in particular.  It does not need to contain a valid INT,
 *       or a jump to a trap handler, or zeros.  It can contain ARBITRARY
 *       BYTES -- including, say, a lookup table and three subroutines.
 *
 *    2. If such a source ever DID fire, the CPU would execute those
 *       arbitrary bytes as if they were a vector.  There is no hardware
 *       check.  That is the risk this design takes, and section 3 quantifies
 *       it honestly.
 *
 *  ---------------------------------------------------------------------------
 *  WHAT THE PRODUCTION IMAGE ACTUALLY CONTAINS
 *  ---------------------------------------------------------------------------
 *      0x8000  RESET     82 00 80 6F   INT s_GSINIT   -- the SDCC runtime
 *      0x8004  TRAP      \
 *        ..              |  92 bytes of RELOCATED DECODER CODE
 *      0x805F  IRQ21     /  (decode_asm.s area VGAP -- section 2)
 *      0x8060  IRQ22     FF FF FF FF   unprogrammed: 4 bytes the gap could
 *                                      still absorb
 *      0x8064  IRQ23     82 00 9E FF   INT _tim4_upd_isr  -- the 1 ms tick
 *      0x8068  IRQ24+    the C world begins here (--code-loc 0x8068)
 *
 *  TWO live vectors out of thirty-two.  Everything else in the table is
 *  either code that has nothing to do with interrupts, or the ordinary
 *  program.
 *
 *  ---------------------------------------------------------------------------
 *  THE FILE, IN ORDER
 *  ---------------------------------------------------------------------------
 *    0  the table's geometry, as an enum: every slot, named
 *    1  the two live vectors, and why they are the only two
 *    2  the vector-gap reuse: what is in the hole and what it bought
 *    3  the risk, named and bounded -- including the part vectors_prod.s
 *       does not mention
 *    4  self-checks
 *    5  a demo main()
 *
 *  ---------------------------------------------------------------------------
 *  WHAT IS DELIBERATELY NOT HERE
 *  ---------------------------------------------------------------------------
 *    the ISR itself     app/tick.c's tim4_upd_isr() is two statements; it is
 *                       rendered in rbarf_ws2812_out.c section 5.1 along
 *                       with the rest of the shipped inline assembly.
 *    the SDCC runtime   what s_GSINIT does (zero DATA, copy INITIALIZER,
 *                       call main) is the compiler's business, not the
 *                       firmware's.
 *    the four relocated routines' ALGORITHMS  mediv/mydiv are 32-bit
 *                       division wrappers and hix is a table-row index;
 *                       they belong to the decoder and are described in
 *                       rbarf_decoder.c.  What matters here is only that
 *                       they FIT.
 */

#include <stdint.h>

/* ==========================================================================
 *  SECTION 0 -- THE TABLE'S GEOMETRY
 * ==========================================================================
 *
 *  The STM8S vector map (RM0016).  Reset, then TRAP, then IRQ0..IRQ29:
 *  thirty-two 4-byte slots, 0x8000..0x807F.  The STM8S001J3 is an 8-pin
 *  value-line part and physically has only a handful of these peripherals,
 *  but the ADDRESSES follow the family map, so the table shape is the same
 *  and the slot arithmetic below is the family's.
 *
 *  Slot addresses:  reset = 0x8000, TRAP = 0x8004, IRQn = 0x8008 + 4*n.
 * ========================================================================== */

#define VECT_BASE      0x8000u
#define VECT_SLOT_SIZE 4u
#define VECT_TRAP      0x8004u
#define VECT_IRQ(n)    (0x8008u + VECT_SLOT_SIZE * (unsigned)(n))
#define VECT_N_IRQ     30            /* IRQ0..IRQ29 on STM8S              */

/* The `int` directive's opcode, and the only opcode a vector slot should
 * normally contain. */
#define OP_INT 0x82u

/* What each slot is FOR, and what this firmware does with it.  "reused"
 * means the slot's four bytes hold something that is not a vector at all. */
enum vect_use {
    VECT_LIVE,        /* a real INT to a real handler                     */
    VECT_REUSED,      /* holds relocated code or data (area VGAP)         */
    VECT_SPARE,       /* left as unprogrammed 0xFF -- still available     */
    VECT_PROGRAM      /* below --code-loc: the ordinary program lives here */
};

typedef struct {
    unsigned       addr;
    int            irq;      /* -1 for reset and TRAP                     */
    const char    *source;
    enum vect_use  use;
} vect_slot;

/*
 * The whole table, as the shipped image has it.  The `source` column is the
 * STM8S family's assignment; whether the STM8S001J3 has that peripheral at
 * all is a separate question, and for the reuse argument the answer is
 * mostly "no", which is the point.
 */
static const vect_slot VECTORS[] = {
    { 0x8000u, -1, "RESET",                          VECT_LIVE    },
    { 0x8004u, -1, "TRAP (software interrupt)",      VECT_REUSED  },
    { 0x8008u,  0, "TLI  (top level interrupt)",     VECT_REUSED  },
    { 0x800Cu,  1, "AWU  (auto wake-up from halt)",  VECT_REUSED  },
    { 0x8010u,  2, "CLK  (clock controller)",        VECT_REUSED  },
    { 0x8014u,  3, "EXTI0 (port A)",                 VECT_REUSED  },
    { 0x8018u,  4, "EXTI1 (port B)",                 VECT_REUSED  },
    { 0x801Cu,  5, "EXTI2 (port C)",                 VECT_REUSED  },
    { 0x8020u,  6, "EXTI3 (port D)",                 VECT_REUSED  },
    { 0x8024u,  7, "EXTI4 (port E)",                 VECT_REUSED  },
    { 0x8028u,  8, "beCAN RX",                       VECT_REUSED  },
    { 0x802Cu,  9, "beCAN TX / status",              VECT_REUSED  },
    { 0x8030u, 10, "SPI end of transfer",            VECT_REUSED  },
    { 0x8034u, 11, "TIM1 update / trigger / break",  VECT_REUSED  },
    { 0x8038u, 12, "TIM1 capture / compare",         VECT_REUSED  },
    { 0x803Cu, 13, "TIM2 update / overflow",         VECT_REUSED  },
    { 0x8040u, 14, "TIM2 capture / compare",         VECT_REUSED  },
    { 0x8044u, 15, "TIM3 update / overflow",         VECT_REUSED  },
    { 0x8048u, 16, "TIM3 capture / compare",         VECT_REUSED  },
    { 0x804Cu, 17, "UART1 TX complete",              VECT_REUSED  },
    { 0x8050u, 18, "UART1 RX full",                  VECT_REUSED  },
    { 0x8054u, 19, "I2C",                            VECT_REUSED  },
    { 0x8058u, 20, "UART2/3 TX complete",            VECT_REUSED  },
    { 0x805Cu, 21, "UART2/3 RX full",                VECT_REUSED  },
    { 0x8060u, 22, "ADC1 end of conversion",         VECT_SPARE   },
    { 0x8064u, 23, "TIM4 update / overflow",         VECT_LIVE    },
    { 0x8068u, 24, "FLASH EOP / WR_PG_DIS",          VECT_PROGRAM },
    { 0x806Cu, 25, "(reserved)",                     VECT_PROGRAM },
    { 0x8070u, 26, "(reserved)",                     VECT_PROGRAM },
    { 0x8074u, 27, "(reserved)",                     VECT_PROGRAM },
    { 0x8078u, 28, "(reserved)",                     VECT_PROGRAM },
    { 0x807Cu, 29, "(reserved)",                     VECT_PROGRAM }
};

#define VECT_COUNT (sizeof VECTORS / sizeof VECTORS[0])

/* ==========================================================================
 *  SECTION 1 -- THE TWO LIVE VECTORS
 * ==========================================================================
 *
 *  vectors_prod.s, in full, is these two lines plus the .org directives:
 *
 *      .area VECT (ABS)
 *      .org 0x8000
 *      int s_GSINIT            ; 0x8000  RESET -> runtime init
 *      .org 0x8064
 *      int _tim4_upd_isr       ; 0x8064  IRQ23  TIM4 update = millis tick
 *
 *  and in the linked image those become
 *
 *      0x8000:  82 00 80 6F     INT $00806F   -> s_GSINIT
 *      0x8064:  82 00 9E FF     INT $009EFF   -> _tim4_upd_isr
 *
 *  RESET -> s_GSINIT, not -> main.  s_GSINIT is SDCC's runtime entry: it
 *  zeroes the DATA segment, copies INITIALIZER into RAM and calls main().
 *  Skipping it would leave every uninitialised global holding whatever the
 *  RAM powered up with -- and rbarf_prod.c relies on that zeroing by name
 *  ("ws2812_in_buf is zero-initialised by the SDCC startup"), so the boot
 *  frame is all-dark and mode 0 without a single byte of code to make it so.
 *
 *  Note that reset points DIRECTLY at s_GSINIT (0x806F) and not at SDCC's
 *  own reset stub, which the linker put at 0x8068.  That stub is therefore
 *  dead code -- it is reachable only as IRQ24's vector, which brings us to
 *  section 3.
 *
 *  IRQ23, TIM4 UPDATE, IS THE ONLY INTERRUPT THE FIRMWARE EVER ENABLES.
 *  One source, one enable bit, one line of setup in main():
 *
 *      TIM4_CR1  = 0x00;      // stop while configuring
 *      TIM4_PSCR = 0x07;      // prescaler /128
 *      TIM4_ARR  = 124;       // 16 MHz / 128 / 125 = exactly 1000 Hz
 *      TIM4_SR   = 0x00;      // clear any stale flag
 *      TIM4_IER  = 0x01;      // <-- the only interrupt enable in the image
 *      TIM4_CR1  = 0x01;      // go
 *
 *  16 000 000 / 128 = 125 000 Hz; ARR = 124 means the counter wraps every
 *  125 ticks; 125 000 / 125 = 1000.000 Hz.  Exactly 1 ms, with no
 *  accumulating error -- which matters because millis() drives the 5-second
 *  SWIM window, the 25 Hz render cadence and the bench's frame timing.
 *
 *  WHY THE TICK IS WORTH AN INTERRUPT AT ALL, given that everything else in
 *  this firmware is a single-threaded main loop: because the two things that
 *  must not be interrupted -- the WS2812 send and the armed capture -- are
 *  BOTH long (312 us and up to 1.9 ms) and both mask interrupts for their
 *  duration.  A polled timebase would have to be polled from inside them,
 *  and there is no spare cycle inside either.  With an ISR, the hardware
 *  latches the pending flag and the tick is delivered late instead of lost:
 *  a capture can swallow at most one millisecond per captured frame, and a
 *  send at most one per render.
 *
 *  AND WHY THE ISR LIVES IN ITS OWN MODULE.  app/tick.c holds nothing but
 *  the counter, the ISR and millis().  If the `__interrupt(23)` declaration
 *  sat in the module with main(), SDCC would emit ITS OWN COMPLETE vector
 *  table -- all thirty-two slots -- and that table would land on top of the
 *  92 bytes of decoder code in the gap.  Splitting the ISR into a separate
 *  translation unit is what makes the hand-packed table possible at all.
 * ========================================================================== */

/* The two live entries, as bytes.  These are the actual contents of the
 * shipped image at those addresses (build/rbarf_prod.ihx). */
#define GSINIT_ADDR        0x00806Fu
#define TIM4_UPD_ISR_ADDR  0x009EFFu

static const uint8_t VECT_RESET_BYTES[4] = { 0x82u, 0x00u, 0x80u, 0x6Fu };
static const uint8_t VECT_IRQ23_BYTES[4] = { 0x82u, 0x00u, 0x9Eu, 0xFFu };

/* Build the four bytes of an `int` directive, the way the assembler does. */
static void vect_encode_int(uint32_t target, uint8_t out[4])
{
    out[0] = OP_INT;
    out[1] = (uint8_t)((target >> 16) & 0xFFu);
    out[2] = (uint8_t)((target >> 8) & 0xFFu);
    out[3] = (uint8_t)(target & 0xFFu);
}

/* ...and read it back out. */
static uint32_t vect_decode_int(const uint8_t in[4])
{
    if (in[0] != OP_INT)
        return 0xFFFFFFFFu;          /* not a vector at all */
    return ((uint32_t)in[1] << 16) | ((uint32_t)in[2] << 8) | in[3];
}

/* ==========================================================================
 *  SECTION 2 -- THE VECTOR-GAP REUSE
 * ==========================================================================
 *
 *  Between the TRAP slot and the TIM4 slot there are 24 slots -- TRAP plus
 *  IRQ0..IRQ22 -- occupying 0x8004..0x8063, ninety-six bytes.  In a
 *  conventional image every one of them holds `INT some_dummy_handler` and
 *  none of them is ever executed.  Ninety-six bytes is 1.2 % of this part's
 *  entire flash, and this project spent an entire campaign finding
 *  twenty-byte savings in the decoder.
 *
 *  So decode_asm.s declares an absolute area in the hole:
 *
 *      .area VGAP (ABS)
 *      .org 0x8004
 *
 *  and puts real code and real data there.  As linked:
 *
 *      0x8004..0x800B    8 B   sot   -- O_CY[8], the sampler's slot offsets
 *                                       in cycles: 0, 4, 9, 13, 17, 21,
 *                                       27, 32
 *      0x800C..0x8013    8 B   swt   -- W_CY[8], the data-dependent term as
 *                                       signed bytes: 0, -1, 0, +2, 0, 0,
 *                                       0, +1
 *      0x8014..0x803F   44 B   mediv -- signed 32/16 division wrapper
 *      0x8040..0x8057   24 B   mydiv -- unsigned 32/16 division wrapper
 *      0x8058..0x805F    8 B   hix   -- A in {0,1} -> X = A * 64, the
 *                                       per-family histogram row base
 *      0x8060..0x8063    4 B         -- unprogrammed 0xFF, still available
 *                                -----
 *                       92 B occupied of the 96-byte window
 *
 *  There is a pleasing detail in the first sixteen bytes.  `sot` and `swt`
 *  are the FITTED SAMPLER CONSTANTS -- the eight slot offsets and the eight
 *  data-dependent corrections that rbarf_capture.c section 5 explains, the
 *  numbers that were fitted to 54 real captures.  The receiver's model of
 *  its own instrument lives in the interrupt vector table.  Dump the first
 *  sixteen bytes of the shipped image after the reset vector and you are
 *  reading the calibration:
 *
 *      0x8004:  00 04 09 0D 11 15 1B 20     <- 0, 4, 9, 13, 17, 21, 27, 32
 *      0x800C:  00 FF 00 02 00 00 00 01     <- 0, -1, 0, +2, 0, 0, 0, +1
 *
 *  WHAT IT BOUGHT, measured: 92 bytes of an 8 KB image, against a terse
 *  build that finishes with 34 free bytes.  Without the reuse the image
 *  would not link.  (vectors_prod.s's own header says "worth 88 B"; the
 *  linked area is 92 B -- `VGAP1  0000005C` in build/rbarf_prod.map.  The
 *  smaller figure is a stale count, and it is reported rather than
 *  corrected here because this file does not edit the shipped sources.)
 *
 *  WHAT IT COSTS AT LINK TIME, and this is not free:
 *
 *    * `--code-loc 0x8068` is MANDATORY.  SDCC's relocatable areas must
 *      start above the table, or the linker would place ordinary code at
 *      0x8000 and destroy both live vectors.  guard_prod.py checks that
 *      HOME really starts at or above 0x8068 and refuses the build
 *      otherwise.
 *    * THE LINKER DOES NOT CHECK ABS/REL OVERLAP.  This is the same hazard
 *      that pins the capture loop at the other end of flash, in the same
 *      image, for the same reason: an absolute area and a relocatable area
 *      can be told to occupy the same bytes and sdld will do it silently.
 *      So guard_prod.py also checks that VGAP stays inside 0x8004..0x8063 --
 *      anchored on the exported symbol `sot`, because sdld prints absolute
 *      areas with an address of 0 in its map and the area table alone
 *      cannot answer the question.
 *    * `sot` is `.globl` FOR THE GUARD'S SAKE ALONE.  Nothing links against
 *      it; it exists so the map has an address the guard can anchor on.
 * ========================================================================== */

/* The gap, and what is in it. */
#define VGAP_LO   0x8004u
#define VGAP_HI   0x8063u            /* inclusive */
#define VGAP_USED 92u                /* VGAP1 in build/rbarf_prod.map      */
#define CODE_LOC  0x8068u            /* the mandatory --code-loc           */

typedef struct {
    unsigned    lo, hi;              /* inclusive                          */
    const char *name;
    const char *what;
} vgap_item;

static const vgap_item VGAP[] = {
    { 0x8004u, 0x800Bu, "sot",   "O_CY[8], the sampler's slot offsets (cy)" },
    { 0x800Cu, 0x8013u, "swt",   "W_CY[8], the data-dependent term (s8)"    },
    { 0x8014u, 0x803Fu, "mediv", "signed 32/16 division wrapper"            },
    { 0x8040u, 0x8057u, "mydiv", "unsigned 32/16 division wrapper"          },
    { 0x8058u, 0x805Fu, "hix",   "A in {0,1} -> X = A*64 (histogram row)"   }
};

#define VGAP_COUNT (sizeof VGAP / sizeof VGAP[0])

/* The two fitted tables, exactly as the image holds them.  Cross-checked
 * against rbarf_capture.c's own copies by the self-test. */
static const uint8_t SOT_BYTES[8] = { 0, 4, 9, 13, 17, 21, 27, 32 };
static const int8_t  SWT_BYTES[8] = { 0, -1, 0, 2, 0, 0, 0, 1 };

/* ==========================================================================
 *  SECTION 3 -- THE RISK, NAMED AND BOUNDED
 * ==========================================================================
 *
 *  vectors_prod.s states it plainly, which is the right way to ship a
 *  decision like this:
 *
 *      RISK (documented): a spurious interrupt 0..22 or TRAP would execute
 *      table bytes as a vector -- acceptable because no such source is ever
 *      enabled and TRAP is never executed; revert to a full table if that
 *      changes.
 *
 *  Unpacked, and with the part vectors_prod.s does NOT mention added:
 *
 *  (a) WHAT WOULD HAPPEN.  The CPU would set PC to the slot and execute
 *      whatever is there.  At 0x8004 that is `.db 0, 4, 9, ...`, and 0x00
 *      is NEG (0,X) -- a legal instruction, so not even an illegal-opcode
 *      reset; execution would wander through the tables and into mediv.
 *      The likely outcome is a stack imbalance and then undefined
 *      behaviour, with no diagnostic.  This is genuinely worse than a
 *      trap-and-reset design would be.
 *
 *  (b) WHY IT CANNOT HAPPEN.  Every one of the 24 reused slots belongs to a
 *      peripheral interrupt, and a peripheral interrupt requires its enable
 *      bit to be set.  The firmware sets exactly one interrupt enable in
 *      its entire lifetime (`TIM4_IER = 0x01`).  Most of these peripherals
 *      do not exist on an 8-pin STM8S001J3 at all -- there is no CAN, no
 *      I2C, no second UART, no ADC on a usable pin -- and the ones that do
 *      exist come out of reset with their interrupt enables clear.  The
 *      external-interrupt slots (EXTI0..4) are the closest thing to a live
 *      hazard, since the part does have GPIO: they are enabled per port via
 *      the CR2 registers, and the firmware writes CR2 exactly once, in
 *      ws2812_out_init(), on PORT A -- where it sets the slew-rate bit for
 *      an OUTPUT pin.  On an output, PA_CR2 bit 3 is slew rate, not
 *      interrupt enable; the interrupt meaning applies only to inputs.
 *      PC3, the capture pin, is left as a plain floating input and its CR2
 *      is never touched.
 *
 *  (c) TRAP.  The TRAP slot is only ever reached by executing the `TRAP`
 *      instruction, which appears nowhere in the image.  Unlike the
 *      peripheral slots this needs no argument about enable bits: it is
 *      simply unreachable.
 *
 *  (d) THE PART vectors_prod.s DOES NOT MENTION.  The reuse is not limited
 *      to the documented 0x8004..0x8063 window.  `--code-loc 0x8068` puts
 *      ordinary program bytes on IRQ24 (FLASH end-of-programming) and every
 *      reserved slot above it, IRQ25..IRQ29.  The firmware never writes
 *      flash at runtime and never enables the flash interrupt, so the same
 *      argument covers it -- and there is a small accident in its favour:
 *      the bytes the linker happened to place at 0x8068 are SDCC's own dead
 *      reset stub, `82 00 80 6F` = `INT s_GSINIT`.  A flash interrupt would
 *      therefore restart the runtime rather than execute garbage.  That is
 *      luck, not design, and it is worth writing down precisely because a
 *      future relink would silently take it away.
 *
 *  (e) THE HONEST SUMMARY.  This is a real risk traded for 92 bytes that
 *      the image could not otherwise find, on a part where the alternative
 *      was not shipping.  The trade is defensible because the argument is
 *      about ENABLE BITS -- a small, enumerable, statically checkable set --
 *      and not about probabilities.  It stops being defensible the moment
 *      any second interrupt source is enabled, and the source file says so.
 * ========================================================================== */

/* ==========================================================================
 *  SECTION 4 -- SELF-CHECKS
 * ==========================================================================
 *  Everything in this file is a claim about addresses and bytes, so
 *  everything in it is checkable: the slot arithmetic, the two live
 *  vectors' encodings, the gap's size and the fact that the reused region
 *  ends below the live TIM4 slot.  Plus the nicest one -- that the tables
 *  in the vector gap really are the fitted sampler constants.
 * ========================================================================== */

#ifdef RBARF_VECTORS_MAIN
#include <stdio.h>
#define CHK(...) do { if (verbose) printf(__VA_ARGS__); } while (0)
#else
#define CHK(...) do { } while (0)
#endif

int rbarf_vectors_selfcheck(int verbose)
{
    int fails = 0;
    unsigned i;

#ifndef RBARF_VECTORS_MAIN
    (void)verbose;
#endif

    /* ---- the slot arithmetic ----------------------------------------- */
    {
        int bad = 0;
        if (VECT_COUNT != (unsigned)(2 + VECT_N_IRQ)) {
            bad++;
        }
        if (VECTORS[0].addr != VECT_BASE || VECTORS[1].addr != VECT_TRAP)
            bad++;
        for (i = 2; i < VECT_COUNT; i++)
            if (VECTORS[i].addr != VECT_IRQ(VECTORS[i].irq)
                    || VECTORS[i].irq != (int)(i - 2))
                bad++;
        if (bad) {
            fails++;
            CHK("FAIL  slot arithmetic: %d entries wrong\n", bad);
        } else {
            CHK("ok    32 slots: reset 0x8000, TRAP 0x8004, "
                "IRQn = 0x8008 + 4n, IRQ29 at 0x%04X\n",
                (unsigned)VECT_IRQ(29));
        }
    }

    /* ---- the two live vectors encode and decode ---------------------- */
    {
        uint8_t enc[4];
        vect_encode_int(GSINIT_ADDR, enc);
        if (enc[0] != VECT_RESET_BYTES[0] || enc[1] != VECT_RESET_BYTES[1]
                || enc[2] != VECT_RESET_BYTES[2]
                || enc[3] != VECT_RESET_BYTES[3]
                || vect_decode_int(VECT_RESET_BYTES) != GSINIT_ADDR) {
            fails++;
            CHK("FAIL  reset vector: %02X %02X %02X %02X != image\n",
                enc[0], enc[1], enc[2], enc[3]);
        } else {
            CHK("ok    0x8000 RESET  = %02X %02X %02X %02X = "
                "INT $%06X (s_GSINIT)\n", VECT_RESET_BYTES[0],
                VECT_RESET_BYTES[1], VECT_RESET_BYTES[2],
                VECT_RESET_BYTES[3], (unsigned)GSINIT_ADDR);
        }
        vect_encode_int(TIM4_UPD_ISR_ADDR, enc);
        if (enc[0] != VECT_IRQ23_BYTES[0] || enc[1] != VECT_IRQ23_BYTES[1]
                || enc[2] != VECT_IRQ23_BYTES[2]
                || enc[3] != VECT_IRQ23_BYTES[3]
                || vect_decode_int(VECT_IRQ23_BYTES) != TIM4_UPD_ISR_ADDR) {
            fails++;
            CHK("FAIL  IRQ23 vector: %02X %02X %02X %02X != image\n",
                enc[0], enc[1], enc[2], enc[3]);
        } else {
            CHK("ok    0x8064 IRQ23  = %02X %02X %02X %02X = "
                "INT $%06X (_tim4_upd_isr)\n", VECT_IRQ23_BYTES[0],
                VECT_IRQ23_BYTES[1], VECT_IRQ23_BYTES[2],
                VECT_IRQ23_BYTES[3], (unsigned)TIM4_UPD_ISR_ADDR);
        }
        /* IRQ23's slot must be exactly where 0x8008 + 4*23 says it is --
         * this is the one number vectors_prod.s hardcodes as a .org. */
        if (VECT_IRQ(23) != 0x8064u) {
            fails++;
            CHK("FAIL  IRQ23 slot is 0x%04X, vectors_prod.s .orgs 0x8064\n",
                (unsigned)VECT_IRQ(23));
        }
    }

    /* ---- the gap: 24 slots, 96 bytes, 92 used ------------------------ */
    {
        unsigned n_reused = 0, n_live = 0, n_spare = 0, n_prog = 0;
        unsigned window = VGAP_HI - VGAP_LO + 1u;
        unsigned covered = 0;
        int bad = 0;

        for (i = 0; i < VECT_COUNT; i++) {
            switch (VECTORS[i].use) {
            case VECT_LIVE:    n_live++;   break;
            case VECT_REUSED:  n_reused++; break;
            case VECT_SPARE:   n_spare++;  break;
            case VECT_PROGRAM: n_prog++;   break;
            }
        }
        (void)n_reused; (void)n_spare; (void)n_prog;
        if (n_live != 2) {
            fails++;
            CHK("FAIL  %u live vectors, expected exactly 2\n", n_live);
        } else {
            CHK("ok    exactly 2 live vectors (RESET, IRQ23 TIM4 update); "
                "%u reused, %u spare, %u below --code-loc\n",
                n_reused, n_spare, n_prog);
        }
        if (window != 96u) {
            fails++;
            CHK("FAIL  the gap window is %u bytes, expected 96\n", window);
        }
        /* the reused + spare slots must tile the window exactly */
        for (i = 0; i < VECT_COUNT; i++)
            if (VECTORS[i].use == VECT_REUSED
                    || VECTORS[i].use == VECT_SPARE) {
                if (VECTORS[i].addr < VGAP_LO
                        || VECTORS[i].addr + VECT_SLOT_SIZE - 1u > VGAP_HI)
                    bad++;
                covered += VECT_SLOT_SIZE;
            }
        if (bad || covered != window) {
            fails++;
            CHK("FAIL  reused/spare slots cover %u of %u gap bytes "
                "(%d outside)\n", covered, window, bad);
        } else {
            CHK("ok    TRAP..IRQ22 = %u slots tile 0x%04X..0x%04X exactly "
                "(%u bytes)\n", covered / VECT_SLOT_SIZE,
                VGAP_LO, VGAP_HI, window);
        }
        if (VGAP_USED > window) {
            fails++;
            CHK("FAIL  VGAP uses %u bytes of a %u-byte window\n",
                VGAP_USED, window);
        } else {
            CHK("ok    VGAP occupies %u of %u bytes; %u spare (0x%04X.."
                "0x%04X)\n", VGAP_USED, window, window - VGAP_USED,
                VGAP_LO + VGAP_USED, VGAP_HI);
        }
    }

    /* ---- the VGAP item table is contiguous and adds up to 92 --------- */
    {
        unsigned total = 0;
        int bad = 0;
        for (i = 0; i < VGAP_COUNT; i++) {
            if (VGAP[i].hi < VGAP[i].lo)
                bad++;
            if (i == 0 ? (VGAP[i].lo != VGAP_LO)
                       : (VGAP[i].lo != VGAP[i - 1].hi + 1u))
                bad++;
            total += VGAP[i].hi - VGAP[i].lo + 1u;
        }
        if (bad || total != VGAP_USED) {
            fails++;
            CHK("FAIL  VGAP items: %d gaps/overlaps, %u bytes (want %u)\n",
                bad, total, VGAP_USED);
        } else {
            CHK("ok    VGAP items are contiguous from 0x%04X and total "
                "%u bytes\n", VGAP_LO, total);
        }
        /* and they must all end below the live TIM4 vector */
        if (VGAP[VGAP_COUNT - 1].hi >= 0x8064u) {
            fails++;
            CHK("FAIL  VGAP runs into the IRQ23 vector at 0x8064\n");
        } else {
            CHK("ok    VGAP ends 0x%04X, clear of the live IRQ23 vector at "
                "0x8064\n", VGAP[VGAP_COUNT - 1].hi);
        }
    }

    /* ---- --code-loc is above the whole table ------------------------- */
    if (CODE_LOC <= 0x8064u + VECT_SLOT_SIZE - 1u) {
        fails++;
        CHK("FAIL  --code-loc 0x%04X would clobber the IRQ23 vector\n",
            CODE_LOC);
    } else {
        CHK("ok    --code-loc 0x%04X sits just above the last live vector "
            "(0x8064..0x8067)\n", CODE_LOC);
    }

    /* ---- the tables in the gap ARE the fitted sampler constants ------ */
    {
        /* rbarf_capture.c's copies, in cycles, independently written down */
        static const uint8_t o_cy[8] = { 0, 4, 9, 13, 17, 21, 27, 32 };
        static const int8_t  w_cy[8] = { 0, -1, 0, 2, 0, 0, 0, 1 };
        int bad = 0;
        for (i = 0; i < 8; i++) {
            if (SOT_BYTES[i] != o_cy[i])
                bad++;
            if (SWT_BYTES[i] != w_cy[i])
                bad++;
        }
        /* the cumulative gaps must be [4,5,4,4,4,6,5,8] and sum to 40 */
        {
            static const int gap[8] = { 4, 5, 4, 4, 4, 6, 5, 8 };
            int sum = 0;
            for (i = 0; i < 8; i++) {
                if (SOT_BYTES[i] != (uint8_t)sum)
                    bad++;
                sum += gap[i];
            }
            if (sum != 40)
                bad++;
        }
        if (bad) {
            fails++;
            CHK("FAIL  the vector-gap tables are not the fitted constants "
                "(%d mismatches)\n", bad);
        } else {
            CHK("ok    0x8004 sot = O_CY = cumulative gaps "
                "[4,5,4,4,4,6,5,8] (loop = 40 cy)\n");
            CHK("ok    0x800C swt = W_CY = [0,-1,0,+2,0,0,0,+1] -- the "
                "sampler's calibration, in the vector table\n");
        }
    }

    return fails;
}

/* ==========================================================================
 *  SECTION 5 -- A DEMO main()
 * ==========================================================================
 *  gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_VECTORS_MAIN \
 *      -o rbarf_vectors rbarf_vectors.c
 *  ./rbarf_vectors
 * ========================================================================== */
#ifdef RBARF_VECTORS_MAIN

static const char *use_name(enum vect_use u)
{
    switch (u) {
    case VECT_LIVE:    return "LIVE";
    case VECT_REUSED:  return "reused (VGAP)";
    case VECT_SPARE:   return "spare (0xFF)";
    case VECT_PROGRAM: return "program";
    }
    return "?";
}

int main(void)
{
    unsigned i;
    int fails;

    printf("rbarf_vectors.c -- self-checks\n");
    fails = rbarf_vectors_selfcheck(1);
    printf("%s: %d failure(s)\n\n", fails ? "FAIL" : "PASS", fails);

    printf("the STM8S001J3 vector table as the production image has it\n");
    printf("  addr    slot        source                          use\n");
    for (i = 0; i < VECT_COUNT; i++) {
        char slot[16];
        if (VECTORS[i].irq < 0)
            slot[0] = '\0';
        else
            snprintf(slot, sizeof slot, "IRQ%-2d", VECTORS[i].irq);
        printf("  0x%04X  %-10s  %-30s  %s\n", VECTORS[i].addr,
               VECTORS[i].irq < 0
                 ? (VECTORS[i].addr == VECT_BASE ? "reset" : "TRAP")
                 : slot,
               VECTORS[i].source, use_name(VECTORS[i].use));
    }

    printf("\nwhat is in the gap (decode_asm.s area VGAP)\n");
    for (i = 0; i < VGAP_COUNT; i++)
        printf("  0x%04X..0x%04X  %3u B  %-6s %s\n",
               VGAP[i].lo, VGAP[i].hi, VGAP[i].hi - VGAP[i].lo + 1u,
               VGAP[i].name, VGAP[i].what);
    printf("  0x%04X..0x%04X  %3u B  --     unprogrammed, still available\n",
           VGAP_LO + VGAP_USED, VGAP_HI,
           VGAP_HI - (VGAP_LO + VGAP_USED) + 1u);

    printf("\nthe fitted sampler constants, read out of the vector table\n");
    printf("  0x8004 sot O_CY[8] =");
    for (i = 0; i < 8; i++)
        printf(" %3u", SOT_BYTES[i]);
    printf("   (cycles)\n");
    printf("  0x800C swt W_CY[8] =");
    for (i = 0; i < 8; i++)
        printf(" %3d", SWT_BYTES[i]);
    printf("   (cycles per HIGH read)\n");
    return fails ? 1 : 0;
}

#endif /* RBARF_VECTORS_MAIN */
