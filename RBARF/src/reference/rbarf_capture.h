/*
 * rbarf_capture.h -- public interface of the READABLE reference rendering of
 * the RBARF capture front end (cap_arm.s + caploop.s), wire protocol v2.3.
 *
 * This is a teaching / presentation copy of the code that ships as hand
 * assembly in cap_arm.s and caploop.s.  It is NOT part of the firmware
 * build.  It has two layers, and they answer different questions:
 *
 *   LAYER 1  a line-for-line rendering of the two assembly routines, with
 *            every STM8 instruction and its cycle count in a trailing
 *            comment.  Its job is to be READ (and to be run against a
 *            level oracle, which proves the bit-packing).  Its timing is
 *            NOT reproducible in C -- see the banner in rbarf_capture.c.
 *
 *              stm8_cap_arm()        the armed front end
 *              stm8_cap_loop()       the pinned 40-cycle sampling loop
 *              stm8_cap_capture()    the legacy blocking entry
 *
 *   LAYER 2  a host-executable model of the SAMPLER: give it a wire
 *            waveform, an oscillator error and an arm phase and it returns
 *            the capture bytes the STM8 would have written.  It is proven
 *            byte-for-byte identical to the normative Python sampler
 *            (recon/approaches/dev_prod/v23lib.capture, which is
 *            recon/synth.py's fitted model) by reference/parity_capture.py.
 *
 *              rbarf_capture_v23()   payload bytes -> capture bytes
 *              rbarf_capture()       arbitrary wire -> capture bytes
 *
 * Everything here is deterministic and holds no state between calls.
 */
#ifndef RBARF_CAPTURE_H
#define RBARF_CAPTURE_H

#include <stdint.h>

/* ==========================================================================
 *  Geometry limits of THIS build (the target's are in rbarf_prod.c)
 * ========================================================================== */

/* Largest DATA field: 48 = production (20 LEDs), 16 = the test geometry. */
#define RBARF_CAP_ND_MAX      48
/* frame = HEADER(3) + DATA(nd) + CHECK(6) + TRAILER(3) */
#define RBARF_CAP_FRAME_MAX   (RBARF_CAP_ND_MAX + 12)
#define RBARF_CAP_BITS_MAX    (RBARF_CAP_FRAME_MAX * 8)
/* Two edges (one rise, one fall) per wire bit -- every bit pulses, even a 0. */
#define RBARF_CAP_EDGES_MAX   (RBARF_CAP_BITS_MAX * 2)
/* rbarf_prod.c's CAP_BYTES is 288; capture.ihx uses 640. */
#define RBARF_CAP_BYTES_MAX   1024

/* ==========================================================================
 *  LAYER 1 -- the rendered assembly
 * ========================================================================== */

/*
 * The ONLY thing the rendered assembly is allowed to do with the outside
 * world: read PC3 (PC_IDR bit 3, package pin 7).  Every BTJT in both
 * routines is one call to this.  Returning 0/1 is the whole interface; the
 * oracle decides what "now" means, which is exactly the part C cannot
 * express (see the banner in rbarf_capture.c).
 */
typedef int (*stm8_pc3_read)(void *ctx);

/*
 * What the rendered arm did, for a reader (and for the self-tests).  The
 * cycle counts are the NOMINAL sums of the annotated instruction costs --
 * they are the arithmetic in the comments, made checkable.  Real silicon
 * adds flash-fetch stalls that depend on the code's address; that is the
 * whole subject of cap_arm.s FIX 4 and it is not modelled here.
 */
typedef struct {
    stm8_pc3_read read;        /* in:  the pin oracle                       */
    void         *ctx;         /* in:  passed through to read()             */
    int           entered_loop;/* out: 1 if an edge poll saw HIGH           */
    int           caught_by;   /* out: which edge poll caught it, 1..4      */
    uint8_t       a_at_entry;  /* out: A (the burst counter) at that moment  */
    int           idle_tries;  /* out: idle-gate attempts consumed, 1..8    */
    int           bursts;      /* out: 176 us edge bursts consumed, 0..7    */
    unsigned long nominal_cy;  /* out: nominal cycles spent in the arm      */
    unsigned long polls;       /* out: PC3 reads issued                     */
} stm8_arm_trace;

/*
 * cap_arm.s: idle gate -> bounded edge window -> taken branch into the
 * pinned sampling loop at its R0 poll.  Returns cap_arm's A: 1 = a frame
 * was captured, 0 = no frame / the line stayed busy in this window.
 *
 * `buf` and `y_loops` are the X and Y the caller sets up (rbarf_prod.c's
 * inline asm block); on the capture path they are handed straight to
 * stm8_cap_loop() the way the hardware's fall-through does.
 */
int stm8_cap_arm(uint8_t *buf, uint16_t y_loops, stm8_arm_trace *tr);

/*
 * caploop.s's _cap_loop: the pinned 40-cycle, 8-sample-per-loop body.
 * Writes y_loops bytes to buf and returns A = 1.
 *
 *   a_entry      the value of A on entry.  From _cap_arm this is the burst
 *                counter (documented garbage, see the banner); the blocking
 *                entry leaves it undefined too.
 *   enter_at_r0  1 to enter at CL_R0 = _cap_loop+1, skipping the loop-top
 *                `rlc a` (cap_arm.s FIX 2a); 0 to enter at _cap_loop, which
 *                is what a fall-through from wait_high does.
 */
int stm8_cap_loop(uint8_t *buf, uint16_t y_loops, uint8_t a_entry,
                  int enter_at_r0, stm8_pc3_read read, void *ctx);

/*
 * caploop.s's _cap_capture: the legacy blocking entry (LDW Y,#256 ->
 * wait_low -> wait_high -> fall into _cap_loop).  This is the shape
 * cap_code.s ships in the acquisition image, and the shape the sampler
 * model was fitted against.
 */
int stm8_cap_capture(uint8_t *buf, stm8_pc3_read read, void *ctx);

/* ==========================================================================
 *  LAYER 2 -- the host-executable sampler model
 * ========================================================================== */

/*
 * A wire waveform as a bit sequence.  `bit[k]` is 0 or 1; bit k occupies
 * [k*bit_ns, (k+1)*bit_ns) and its high pulse is [k*bit_ns, k*bit_ns + H)
 * where H is t1h_ns for a 1 and t0h_ns for a 0.  The line is low before
 * bit 0 and after the last bit.
 *
 * The defaults (rbarf_wire_v23) are the FITTED effective widths, not the
 * transmitter's nominal ones: 752 / 377 ns against the PIO's 750 / 375,
 * i.e. a common +2 ns edge shift that the calibration absorbed.
 */
typedef struct {
    const uint8_t *bit;
    uint16_t       nbits;
    double         bit_ns;      /* 1250.0 -- one WS2812 bit slot           */
    double         t1h_ns;      /* 752.0  -- effective high width of a '1' */
    double         t0h_ns;      /* 377.0  -- effective high width of a '0' */
} rbarf_wire;

/*
 * The same waveform as a list of edge times in ns, strictly increasing,
 * starting with a rise: rbarf_wire_edges() builds it and
 * rbarf_wire_level_edges() evaluates it.  The two representations are
 * proven to agree exactly (rbarf_capture_selfcheck).
 */
typedef struct {
    const double *t_ns;
    uint16_t      n;
} rbarf_edges;

/*
 * The sampler's own parameters: everything about the RECEIVER.
 *
 *   eps      relative oscillator frequency error (+ = fast clock).  Sample
 *            spacing in real time scales by 1/(1+eps).  Factory trim on the
 *            bench unit is about -1.07 %, i.e. eps = -0.0107.
 *   t0_ns    the ARM TRIGGER PHASE: where sample (0, 0) lands relative to
 *            the frame's first rising edge.  The single most load-bearing
 *            number in the front end -- there is a hard cliff at ~681 ns.
 *   drift    linear eps ramp across the WIRE span, in the same units as
 *            eps (0 = none).  See the note on drift in rbarf_capture.c.
 *   n_bytes  capture buffer length in bytes = number of sampling loops.
 *   chop     drop the first `chop` bytes and shift left (arm fired late,
 *            the burst's HEAD is missing).
 *   trunc    drop the last `trunc` bytes (buffer ran out, TAIL missing).
 */
typedef struct {
    double   eps;
    double   t0_ns;
    double   drift;
    uint16_t n_bytes;
    uint16_t chop;
    uint16_t trunc;
} rbarf_sampler;

/* Fill in the v2.3 wire defaults (bit_ns / t1h_ns / t0h_ns) around a bit
 * array.  `bit` and `nbits` are stored as given. */
void rbarf_wire_v23(rbarf_wire *w, const uint8_t *bit, uint16_t nbits);

/* Level of the waveform at absolute time t_ns (0 = frame start).  0 or 1. */
int rbarf_wire_level(const rbarf_wire *w, double t_ns);

/* Build the edge list of `w` into `out` (needs 2*nbits entries).  Returns
 * the number of edges written. */
uint16_t rbarf_wire_edges(const rbarf_wire *w, double *out, uint16_t cap);

/* Level of an edge list at t_ns.  Equal to rbarf_wire_level() everywhere. */
int rbarf_wire_level_edges(const rbarf_edges *e, double t_ns);

/*
 * THE MODEL.  Runs the fitted sampler over `w` and writes the capture bytes
 * to `out` in caploop.s's layout.  Returns the number of bytes written
 * (n_bytes, less `trunc`), or 0 if `out_cap` is too small.
 */
uint16_t rbarf_capture(const rbarf_wire *w, const rbarf_sampler *s,
                       uint8_t *out, uint16_t out_cap);

/*
 * The convenience front door, and the entry point the parity harness
 * drives: build the v2.3 frame for `data` (HEADER FF AA 65 || DATA ||
 * (CRC16_HI CRC16_LO) x3 || TRAILER 9A 00 FF), turn it into a wire, and
 * capture it.  Argument order mirrors v23lib.capture() so the two are easy
 * to read side by side.
 */
uint16_t rbarf_capture_v23(const uint8_t *data, uint8_t nd,
                           double eps, double t0_ns, double drift,
                           uint16_t n_bytes, uint16_t chop, uint16_t trunc,
                           uint8_t *out, uint16_t out_cap);

/* Frame construction, exposed because it is worth reading on its own.
 * Returns the frame length (nd + 12), 0 if nd is out of range. */
uint16_t rbarf_build_frame_v23(const uint8_t *data, uint8_t nd,
                               uint8_t *frame_out, uint16_t frame_cap);
/* CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection, xorout 0. */
uint16_t rbarf_crc16(const uint8_t *data, uint16_t len);
/* MSB-first bit expansion: one byte of `bits_out` per wire bit. */
uint16_t rbarf_bytes_to_bits(const uint8_t *bytes, uint16_t nbytes,
                             uint8_t *bits_out, uint16_t cap);

/* ==========================================================================
 *  SELF-CHECKS -- the equivalences this file can actually prove
 * ========================================================================== */

/*
 * Runs every internal consistency check and returns the number of FAILURES
 * (0 = all good).  With verbose != 0 it prints one line per check.  The
 * checks are listed in section 7 of rbarf_capture.c; the two that matter
 * are (a) the rendered sampling loop's RLC bit-packing produces exactly the
 * bytes the model's packer produces, and (b) the four edge-detect BTJT
 * offsets in cap_arm.s really resolve to _cap_loop+1.
 */
int rbarf_capture_selfcheck(int verbose);

#endif /* RBARF_CAPTURE_H */
