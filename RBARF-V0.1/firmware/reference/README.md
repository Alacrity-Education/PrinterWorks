# `reference/` — the RBARF firmware, written to be read

Four **presentation-grade** C files that between them cover every component of
the shipped firmware: the decoder, the capture front end, the WS2812 output
driver and the vector table. Same algorithms, same numbers, same instructions —
restructured as one clearly-labelled section per stage, in the order a frame
experiences them, with the reasoning written down beside the code.

| file | covers | lines | proof |
|---|---|---:|---|
| `rbarf_decoder.c` (+`.h`) | the frame decoder: `decode.c`, `decode_asm.s` | 2949 | `make ref-parity` — bit-exact vs `embedded_v2.py`, 20 538 captures |
| `rbarf_capture.c` (+`.h`) | the capture front end: `cap_arm.s`, `caploop.s`, `cap_code.s` | 1521 | `make ref-capture-parity` — byte-exact vs `v23lib.capture()`, 30 940 captures |
| `rbarf_ws2812_out.c` | the output driver and **every** inline-asm block in the shipped image | 1034 | self-checked pin trace; cross-checked in `ucsim` |
| `rbarf_vectors.c` | the vector table and the vector-gap reuse: `vectors_prod.s` | 698 | self-checked table geometry and byte encodings |

They exist because the shipped sources answer a different question. `decode.c`
carries three wire geometries behind `#if` forks, an assembly-shaped shared
state layout, and size tricks that only make sense inside an 8 KB flash budget;
`decode_asm.s`, `cap_arm.s` and `caploop.s` are hand assembly whose *addresses*
are part of their meaning. All of it is correct and none of it is readable at a
whiteboard.

Everything here is **documentation, not firmware**. Nothing in the `Makefile`'s
shipping or verify path compiles any of it; `make ref-parity` and
`make ref-capture-parity` are separate, additive targets, and the production
images are untouched by anything in this directory.

Every file compiles clean (**zero warnings**) with
`gcc -std=c99 -Wall -Wextra -pedantic -O2`, each is one self-contained
translation unit, and each carries a `-D…_MAIN` demo:

```sh
cd reference
gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_DECODER_MAIN     -o d  rbarf_decoder.c
gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_CAPTURE_MAIN     -o c  rbarf_capture.c -lm
gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_WS2812_OUT_MAIN  -o w  rbarf_ws2812_out.c
gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_VECTORS_MAIN     -o v  rbarf_vectors.c
```

`./c`, `./w` and `./v` each run their file's self-checks and then print the
numbers the file's comments claim, so the comments are checkable rather than
merely assertive.

---

# `rbarf_decoder.c` — the frame decoder

## What this is

* **One translation unit, portable C99.** Compiles clean (zero warnings) with
  `gcc -std=c99 -Wall -Wextra -pedantic -O2`.
* **Protocol v2.3 only** — `FF AA 65 | DATA | CRC-16/CCITT-FALSE ×3 | 9A 00 FF`
  — with the CRC-16 check block, Lever B dead-window candidates ON, and the
  budget constants `A_MAX = 11`, `W_MAX = 2`, `T_MAX = 131` named and explained
  where they are defined. No preprocessor feature forks anywhere.
* **`nd` is a runtime parameter** (`rbarf_decoder_configure(16|48)`), because
  the real-silicon corpus is the `nd = 16` test geometry while production is
  `nd = 48` — the one place it spends RAM the shipped decoder does not
  (8 bytes of geometry cache; the shipped build resolves `nd` at compile time).
* **Bit-exact against the normative Python decoder**
  (`recon/approaches/embedded_v2.py`) on every corpus — see *Proof* below.

## What this is not

* **Not a target build — but it has the target's memory layout.** The
  decoder's *data representation is the shipped one*: the decoded frame is
  bit-packed in the same byte and bit order, every state table has the same
  element type, count and meaning (each carries the shipped symbol name in a
  trailing comment), and stage scratch is overlaid through the same two
  unions — the eps fold histograms sharing storage with the packed frame and
  the payload' bytes, and the per-segment hypothesis costs sharing storage
  with the chase's reference set. Compile with `-DRBARF_PARANOID` and every
  handover poisons the storage it releases; that build is bit-identical over
  all 20 538 captures, which is what makes the overlay a proof rather than a
  claim. Measured with `sdcc -mstm8 --std-c99` at the production geometry it
  links to **8 444 B CODE + 118 B CONST + 364 B DATA** (one benign SDCC
  optimizer note, on the same range test `decode.c` gets it on), against
  `decode.c`'s **356 B DATA** at the same geometry. That 8-byte gap is the
  entire difference and it is the price of `nd` being a runtime parameter.
  What still differs is the *code*, not the layout — the hot paths are C
  rather than hand assembly, so the call tree spends on the stack (a 138 B
  deepest chain, against `decode.c`'s 104 B and `decode_asm.s`'s 12 B) what
  `decode_asm.s` keeps in 139 bytes of zero page, and 8 444 B of CODE is
  what actually rules this file out of an 8 KB image. The RAM LEDGER banner
  near the end of the file itemises all of it byte by byte against
  `decode_asm.rel` (DZP0 242 + DATA 129) and `decode_prod.rel` (DATA 132).
* **Not the front end.** The capture loop (`caploop.s`), the armed trigger
  (`cap_arm.s`) and the acquisition image (`cap_code.s`) are `rbarf_capture.c`;
  the output driver and the application's inline assembly are
  `rbarf_ws2812_out.c`; the vector table is `rbarf_vectors.c`. Still outside
  all four: the HSITRIMR auto-trim policy and the animation engine (`app/anim.c`),
  which are ordinary C in the shipped tree and readable as they stand.

## Build and run the decoder demo

```sh
cd reference
gcc -std=c99 -Wall -Wextra -pedantic -O2 -DRBARF_DECODER_MAIN \
    -o rbarf_decoder rbarf_decoder.c

# a real ND=16 capture straight out of the corpus
python3 -c "import json;print(json.load(open('../data/captures_v23.json'))['captures'][3]['capture'])" \
    | ./rbarf_decoder --nd 16
```

```
capture      640 bytes (640 sampling loops)
geometry     nd=16  payload'=22 B  frame=224 bits
clock fit    K=53019 (Q11 TU/cycle, nominal 52429)  tau=726 TU
segments     186   infeasible 0   label errors 0   marker violations 0
confidence   n_weak 0   n_tied 0   n_dw 0 (dead-window)
check block  1 reference, 0 split positions
chase        not entered, 0 flip sets, 1/131 residual comparisons
result       DELIVERED  (direct)
data         FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
```

The hex capture may be an argument or arrive on stdin; whitespace and colons
are ignored. Exit status is 0 on a delivered frame, 1 on a refusal (with the
rung of the ladder that fired), 2 on a usage error.

## Proof: `parity_readable.py`

```sh
make ref-parity                        # or:
python3 reference/parity_readable.py   # ~6 s on 24 cores
python3 reference/parity_readable.py --skip-grid --jobs 1
python3 reference/parity_readable.py --source /path/to/work/rbarf_decoder.c
```

`--source` points the harness at another copy of the decoder (a working copy
under development), building its shared library beside it; a *copy of the
script* run from outside `reference/` also wants `RBARF_TREE=<src>`
so it can still find the corpora. Neither changes what `make ref-parity` does.

It compiles `rbarf_decoder.c` with gcc (refusing to continue on any warning),
loads it through `ctypes`, and diffs it capture by capture against
`embedded_v2.py` **at that module's default parameters** (v2.3 wire,
`A_MAX = 11`, `T_MAX = 131`, `DW_EN = 1`). Sixteen fields are compared:
emitted bytes / refusal, `path`, `cause`, `chased`, `trials`, `comps`,
`n_refs`, `ref_split`, `n_weak`, `n_tied`, `n_dw`, `K`, `tau`, `violations`,
`infeasible`, `label_err`. `data/captures_val.json` is never opened.

| corpus | captures | result |
|---|---:|---|
| `data/captures_v23.json` — real silicon, ND = 16 | 54 | all 16 fields identical |
| `fuzz_v23.cases(16)` — the adversarial set `parity_v23.py` uses | 124 | all 16 fields identical |
| `fuzz_v23.cases(48)` — same, production geometry | 149 | all 16 fields identical |
| `v23lib` synthetic grid, ND = 48: 6 eps × 48 arm phases × 70 payloads | 20 160 | all 16 fields identical |
| degenerate buffers (empty / constant / random / truncated) | 51 | all 16 fields identical |
| **total** | **20 538** | **100 % agreement** |

The grid's eps points are −1.4, −1.05, −0.9, −0.8, −0.6, −0.4 %; the 48 arm
phases span 70…658 ns (the convention `dev_lever_b/geomclass.py` uses, at four
times its resolution); the payloads are the 70 distinct production-geometry
frames of `bench/suite_singleshot.build_suite()`. The harness prints an
outcome census per corpus so the proof is visibly non-vacuous — the corpora
between them exercise every rung of the ladder (R1, R2, R3, R4, R6, R7, R8),
both emit paths, the chase, split check-block references and the dead-window
admission.

## Reading the decoder across the three implementations

| `rbarf_decoder.c` section | `decode.c` | `decode_asm.s` | `embedded_v2.py` |
|---|---|---|---|
| 0 capture buffer / linearize | inline in `scan_next` | `_scan_next` (size-focused scanner, §"Size-focused sample scanner") | `harness.linearize` feeding `_pulse_stream` |
| 1 sample scan → edge brackets | `scan_init`, `scan_next`, `struct ps` | `_scan_init`, `_scan_next` | `_pulse_stream` |
| 2 endpoint seed | `seed`, `map_raw` | `_seed`, `_udiv32` | `_seed`, `_map` |
| 3 residual refine | `refine` | `_refine`, `_mul16`, `_mr16`, `_udiv32` | `_refine` |
| 4 segmentation + leading-ones | `ss_init`, `ss_next`, `a_bounds`, `hinge`, `argmin_ab`, `decide` | `_ss_init`, `_ss_next`, `_known_bit`, `_a_bounds_sg`, `_hcost`, `_itst`, `_argmin`, `_decide` | `_seg_stream`, `_a_bounds`, `_hinge`, `_decide` |
| 5 calibration (theta56) | `label_interval`, `cal_cloud`, `cal_add`, `theta56`, `width_fit`, `calibrate` | `_calibrate` and the P3 cluster | `_label_interval`, `_Calib.cloud/add/finish/_theta56`, `_calibrate` |
| 6 decision pass | `decide_pass`, `cand_insert` (dead-window test inline) | `_decide_pass`, `_cand_insert`, `_dwtst` | `_decide_pass`, `_cand_insert` |
| 7 check block + reference set | `crc16`, `rank3`, `ref_build` | `_crcpp`, `_rank3`, `_refbld`, `_confx`, `_putval` | `_crc16`, `_maj3`, `_ref_bytes`, `_ranked3`, `_ref_candidates` |
| 8 CRC-guided chase | `syn16`, `parity16`, `ch_match`, `try_trial`, `chase_singles`, `chase_pairs` | `_chmat`, `_trial`, `_csing`, `_cpair` (no syndrome table: it recomputes `crc16`, value-identical by GF(2) affinity) | `_syn16`, `_parity16`, `_enum_trials`, `_chase23` |
| 9 refusal ladder + output | `chase`, `ws_decode_ex` | `_chasez`, `_ws_decode_ex` | `_chase`, `decode_ex` |
| THE DECODER'S RAM (bit packing + both overlays) | `union ov_u`, `BGET`/`BSET`, `d_costs`/`ch_ref` overlay | the `.area DZP (ABS)` map and the `m_cp = m_n` / `w_llo = r_lo` alias table | — (Python has no layout) |

Two naming notes for readers moving between the files. The Python and C
reference call the fall bracket `(u, v]`; this file spells it
`fall_lo`/`fall_hi`. The Python's `K`/`tau` are `bit_period_q`/`phase_offset`
here, and `h0c`/`h1c` (with the per-family `h0f`/`h1f`) are `width0`/`width1`
plus `family_shift[]`.

---

# `rbarf_capture.c` — the capture front end

The instrument that takes the picture the decoder reconstructs: `cap_arm.s`
(the armed trigger, 60 B at `0x9F63`) and `caploop.s` (the pinned 40-cycle,
8-samples-per-loop sampling loop, 80 B at `0x9FA1`). **Two layers, kept
strictly apart, because they answer different questions.**

**Layer 1 — the rendering (sections 2–3).** Both routines line for line, one C
statement per STM8 instruction, each carrying the instruction and its cycle
count in a trailing comment, so the 40-cycle loop, the eight sample instants,
the per-slot gaps `[4,5,4,4,4,6,5,8]` and the arm's 11-cycle poll comb can be
added up by hand. It is executable — give it an oracle that answers "what does
PC3 read now?" and it produces capture bytes — but **its timing can never be
right on the STM8, and neither can any other C's**, for three reasons the
banner spells out: a compiler picks its own instructions; the sample instants
are deliberately non-uniform; and **address phase is timing** (linked at the
wrong phase the loop really runs its documented 37 cycles and the measured
oscillator error moves by 7 %).

**Layer 2 — the sampler model (sections 4–6).** Host-executable, portable, and
the layer the parity proof covers. Give it a wire (a bit sequence with
`T0H`/`T1H`/period, **or** a list of edge times in ns — the two are proven
exactly equivalent), an oscillator error `eps` and an arm phase `t0`, and it
returns the bytes the STM8 would have written:

```
A(i,s) = i*LOOP + o[s] + Σ_j w[j]·C_j(i,s)      LOOP = 40 cy = 2500 ns
t(i,s) = t0 + A(i,s) / (1 + eps)                o[] gaps [4,5,4,4,4,6,5,8]
                                                w[] = [0,−1,0,+2,0,0,0,+1] cy
C_j(i,s) = HIGH reads at slot j strictly before (i,s)   T1H 752 / T0H 377 ns
```

It also reproduces the malformations real arms produce — `chop` (head missing),
`trunc` (tail missing) and `drift` (a linear `eps` ramp).

### What the model does NOT claim

Metastability (a pin read exactly at an edge resolves cleanly here and does not
on silicon); oscillator jitter and temperature drift (`eps` is one static
number per capture, plus at most one linear ramp — justified by the fitted
per-capture spread of ±0.014 %, and only over a 600 µs burst); transmitter
imperfection (ideal edges, exact crystal timebase — the fitted +2 ns common
edge shift is the one concession); the arm's own timing (`t0` is an *input*,
because how the arm's fetch stalls produce the distribution `t0` is drawn from
was measured on silicon, not modelled); and byte 0's top two bits, where the
model writes zero and the hardware writes the low two bits of the arm's burst
counter. That last one is the only known byte-level difference from silicon,
it is in the Python reference too, and it is provably unreachable — the
decoder's scanner takes loop *i*'s slots 6 and 7 from byte *i+1*, and forcing
those two bits to all four values over 836 captures changed nothing.

## Proof: `parity_capture.py`

```sh
make ref-capture-parity                 # or:
python3 reference/parity_capture.py     # ~2 s on 24 cores
python3 reference/parity_capture.py --skip-grid --jobs 1
```

It compiles `rbarf_capture.c` with gcc (refusing to continue on any warning),
loads it through `ctypes`, and compares **every byte of every capture** against
`recon/approaches/dev_prod/v23lib.capture()` — the normative Python sampler,
which is `recon/synth.py`'s fitted model. Not a summary statistic and not a
decode outcome: the raw bytes. `data/captures_val.json` is never opened.

| corpus | captures | bytes | result |
|---|---:|---:|---|
| production grid ND = 48: 70 payloads × 6 eps × 48 arm phases | 20 160 | 5 806 080 | byte-identical |
| `drift` ±0.2 %, ±0.6 % (4 variants × 70 payloads × 3 eps × 3 t0) | 2 520 | 725 760 | byte-identical |
| `trunc` 1 / 16 / 64 | 1 890 | 493 290 | byte-identical |
| `chop` 1 / 8 / 40 | 1 890 | 544 320 | byte-identical |
| `chop 3 + trunc 7`, `drift +0.4 % + chop 2 + trunc 5` | 1 260 | 355 320 | byte-identical |
| test geometry ND = 16, 160 B captures (30 payloads × 6 eps × 12 t0) | 2 160 | 345 600 | byte-identical |
| `t0` sweep 0…1300 ns, straight through the 681 ns cliff | 1 060 | 305 280 | byte-identical |
| **total** | **30 940** | **8 575 650** | **100 % agreement** |

The grid's eps points and 48 arm phases are `parity_readable.py`'s, so the two
proofs stack: this one says the C sampler produces the same bytes, that one
says the C decoder turns them into the same answer.

The harness also runs `rbarf_capture.c`'s own **self-checks**, which are the
equivalences a C rendering *can* prove:

1. **The bit packing.** The rendered sampling loop's chain of `RLC A`
   instructions produces exactly the bytes the model's packer produces (64
   bytes of pseudo-random samples). A mis-transcribed rotation, a boundary
   sample in the wrong bit or a misplaced store all fail here. This is the
   strongest statement the file makes about the assembly.
2. **The four hand-assembled poll offsets.** `rel = CL_R0 − (poll_addr + 5)`
   re-derived for all four `BTJT_R0` polls, checked against the bytes the
   assembler emitted (`0x34 0x2F 0x2A 0x24`) and against landing on
   `_cap_loop+1 = 0x9FB0`. This is `guard_prod.py` check 5's arithmetic from
   the other direction — the guard disassembles the linked image, this
   re-derives what the image must contain.
3. **The two wire representations** agree on 86 001 grid points at 0.5 ns
   resolution, which lands *on* every edge.
4. The arm's control flow (the idle gate really needs 8 consecutive lows; the
   window really is bounded at 7 × 256 polls) and its **cycle arithmetic**
   (19 793 nominal cycles = 1.237 ms, from a comb of 11 cycles and bursts of
   176 µs).

## Two things found while writing it, changed in nothing

* **Two different drift models exist in the tree.** `recon/synth.py` ramps as
  `(1+eps)·(1+drift·a/TOTAL)` — normalised to the *capture*'s nominal span,
  starting at `eps`, ending at `eps+drift`. `v23lib.capture()` ramps as
  `eps + drift·(clamp(a/WIRE_span) − 0.5)` — normalised to the *wire* span,
  centred on `eps`, and clamped. Both are "a linear eps ramp"; they differ in
  span, centring and clamping, so a drift figure quoted from one script does
  not transfer to the other. `rbarf_capture.c` implements `v23lib`'s, because
  that is what `capture()` calls and what every v2.3 harness uses.
* **`DECW Y` is annotated `[2]` by the assembler.** `cap_code.s`'s header sums
  the loop to 37 cycles assuming `DECW Y` costs 1; `build/caploop.rst` marks it
  `[2]`, which would make the documented sum 38 and the `BS0→BS1` gap 6 rather
  than 5. Nothing downstream depends on it — the *fitted* gaps are
  `[4,5,4,4,4,6,5,8] = 40`, and the fit puts the extra cycles at `R1→R2` (+1)
  and the end-of-loop wrap (+2), leaving `BS0→BS1` at 5. Recorded because the
  instruction-count arithmetic and the measurement are two different things and
  the file says so out loud.

---

# `rbarf_ws2812_out.c` — the output driver, and every other inline-asm block

The transmitter: `app/ws2812_out.c`'s 95-line `__asm` block, rendered line for
line with a **pin trace** (every level change, with the cycle it happened at),
plus the same driver as a four-line plain C bit loop so the *meaning* is
separable from the cycle counting.

At exactly 16 MHz, 62.5 ns per cycle:

| | high | low | period |
|---|---:|---:|---:|
| bit = 0 | T0H 6 cy = **375.0 ns** | T0L 14 cy = **875.0 ns** | 20 cy = 1250.0 ns |
| bit = 1 | T1H 11 cy = **687.5 ns** | T1L 9 cy = **562.5 ns** | 20 cy = 1250.0 ns |
| bit = 0, last of a byte | T0H 6 cy | T0L 19 cy = 1187.5 ns | 25 cy = 1562.5 ns |
| bit = 1, last of a byte | T1H 11 cy | T1L 14 cy = 875.0 ns | 25 cy = 1562.5 ns |

plus a reset latch of **1031 cy = 64.4 µs** of low before the first bit and a
whole send of **4988 cy = 311.8 µs** for 24 bytes (4990 if the final data bit
is a 0 — two cycles of `jra`, after the pin is already low, and the only data
dependence anywhere in the send; every one of the 192 bit boundaries is
data-independent, which the self-check verifies by comparing an all-`0x00` send
against an all-`0xA5` one).

Against the datasheet window (both revisions in circulation, ±150 ns):

| | driver | WS2812 (0.35/0.70/0.80/0.60) | WS2812B (0.40/0.80/0.85/0.45) |
|---|---:|---|---|
| T0H | 375.0 ns | 200…500 ✅ | 250…550 ✅ |
| T1H | 687.5 ns | 550…850 ✅ | 650…950 ✅ |
| T0L | 875.0 ns | 650…950 ✅ | 700…1000 ✅ |
| T1L | 562.5 ns | 450…750 ✅ | 300…600 ✅ |
| reset | 64.4 µs | > 50 µs ✅ | > 50 µs ✅ |

Two places it is honestly outside a nominal window, both discussed in
section 2.4: the **stretched low at byte boundaries** (1187.5 ns, 237 ns past
the WS2812's `T0L+150` bound, every 8th bit — fine because a WS2812 decides on
pulse *width* and treats the low only as "not yet a reset", and 1187.5 ns is 5×
inside even the most pessimistic clone's reset threshold); and the
**oscillator**, where at ±7.5 % two values step outside a WS2812B window by
under 11 ns (T1H 639.5 vs 650 at the fast corner, T1L 608.1 vs 600 at the slow
one) — inside the classic WS2812's windows at every corner, and the auto-trim
holds the part in a 0.6 %-wide band around −1.0 % where everything has > 150 ns
of margin.

**Confirmed in `ucsim`.** Breakpoints on the two pin writes in the *shipped*
`build/rbarf_prod.ihx` (`BSET` at `0x9EBB`, `BRES` at `0x9EC5` / `0x9EE8`), PC
forced to `_ws2812_out_send` at `0x9EA8`, buffer preloaded `A5 A4 5A`, reading
the simulator's cycle counter at every stop: **every value matches**, the first
rising edge is at cycle 1031 to the cycle, the byte-boundary periods come out
25, and the sequence of 0/1 paths taken reproduces `A5 A4 5A` bit for bit. Two
caveats worth knowing: ucsim's `state` prints two counters and only
*"Total time since last reset (N clks)"* is the datasheet cycle count —
*"Operation since last reset = N vclks"* is a bus-access count and gives 16 and
12 where the datasheet gives 11 and 6; and ucsim models the cycle *table*, not
the flash prefetch, so this confirms the arithmetic and says nothing about
fetch stalls.

Section 5 covers **every remaining inline-asm block in the shipped image** —
there are four, six instructions between them, and each is assembly for a
different reason:

| block | what | why it cannot be C |
|---|---|---|
| `app/tick.c` `millis()`, `sim` + `rim` | mask, read the 16-bit `ms_counter`, unmask | the counter is `volatile uint16_t` on an **8-bit** machine: two loads, and a tick between them yields a reading up to 256 ms wrong. SDCC has no intrinsic for `SIM`/`RIM` and a flag-based critical section cannot guard against the interrupt itself. Cost: ~4 cycles masked; a tick pending in that window is delivered immediately after, because TIM4's flag is latched |
| `rbarf_prod.c` `main()`, `rim` | enable interrupts, once | the STM8 resets with interrupts disabled and there is no C spelling for `RIM`. Everything above the line is register setup that must not be interrupted half-done; the line below it is `while (millis() < 5000)` |
| `rbarf_prod.c` `main()`, the arm call (`ldw x` / `ldw y` / `call _cap_arm` / `ld _cap_got, a`) | hand the pinned front end its registers and stash its answer | `_cap_arm` has **no C calling convention** — its interface is "X = buffer, Y = loop count, returns A", because the loop it falls into needs those registers loaded at the instant the first sample is taken and has no room for a prologue. It is also a **timing** interface: the two `LDW`s must be the last thing before the arm starts polling, and the `HSITRIMR` write on the line above must be the last thing before that |

And what is **not** assembly, since it is easy to assume otherwise: the
SWIM-disable is a plain C write, `CFG_GCR = 0x01;` to `0x7F60`, one line after
the 5-second window closes. Nothing special about the store — only about *when*
it happens, because after it pin 8 is UART TX and the part can no longer be
reflashed.

One documentation discrepancy, reported not resolved: `app/ws2812_out.c`'s
header says the whole send is "~545 µs". The arithmetic and ucsim both say
**311.8 µs**, and `rbarf_prod.c`'s own comment on the same call says "~304 µs".
The 545 figure looks like it includes `anim_render()`, which runs immediately
before the send — silicon measures the *pair* at 400…658 µs, median 556.

---

# `rbarf_vectors.c` — the vector table and the gap reuse

`vectors_prod.s` is 25 lines and has **two live entries out of thirty-two**:

```
0x8000  RESET   82 00 80 6F   INT s_GSINIT        -- the SDCC runtime init
0x8064  IRQ23   82 00 9E FF   INT _tim4_upd_isr   -- TIM4 update, the 1 ms tick
```

TIM4 update is the *only* interrupt the firmware ever enables (one
`TIM4_IER = 0x01`, prescaler /128 and `ARR = 124` giving exactly 1000.000 Hz).
The ISR lives in its own module — `app/tick.c` — precisely so that the module
holding `main()` declares no `__interrupt` handler: if it did, SDCC would emit
its own complete 32-slot table and that table would land on top of the code in
the gap.

**The gap.** On the STM8 a vector slot holds an *instruction*, not a pointer:
reset and every interrupt set PC to a fixed slot and start executing there, and
`82 hh mm ll` = `INT $hhmmll` is exactly 4 bytes. So a slot for a source that
can never fire does not need to contain anything in particular. `TRAP` plus
`IRQ0…IRQ22` is 24 slots = **96 bytes** at `0x8004…0x8063`, and
`decode_asm.s` declares an absolute area there:

| range | size | symbol | what |
|---|---:|---|---|
| `0x8004…0x800B` | 8 B | `sot` | `O_CY[8]` — the sampler's slot offsets in cycles: 0, 4, 9, 13, 17, 21, 27, 32 |
| `0x800C…0x8013` | 8 B | `swt` | `W_CY[8]` — the data-dependent term as signed bytes: 0, −1, 0, +2, 0, 0, 0, +1 |
| `0x8014…0x803F` | 44 B | `mediv` | signed 32/16 division wrapper |
| `0x8040…0x8057` | 24 B | `mydiv` | unsigned 32/16 division wrapper |
| `0x8058…0x805F` | 8 B | `hix` | `A ∈ {0,1} → X = A·64`, the histogram row base |
| `0x8060…0x8063` | 4 B | — | unprogrammed `0xFF`, still available |

**92 bytes** of an 8 KB image, against a terse build that finishes with 34 free
bytes: without the reuse it would not link. (`vectors_prod.s`'s header says
"worth 88 B"; the linked area is 92 — `VGAP1  0000005C` in
`build/rbarf_prod.map`. Reported, not corrected, because this directory does
not edit shipped sources.)

The first sixteen of those bytes are the nicest detail in the firmware: `sot`
and `swt` are the **fitted sampler constants** — the receiver's model of its
own instrument, living in the interrupt vector table. `rbarf_vectors.c`'s
self-check confirms they are exactly `rbarf_capture.c`'s `SLOT_OFFSET_CY` and
`SLOT_BRANCH_CY`, and that the offsets really are the cumulative gaps
`[4,5,4,4,4,6,5,8]` summing to 40.

**The risk, which is real.** A spurious `TRAP` or `IRQ0…22` would execute those
bytes as a vector — with no hardware check, and no illegal-opcode reset either
(`0x00`, the first byte of `sot`, is a legal `NEG (0,X)`), so the likely outcome
is a stack imbalance and then undefined behaviour with no diagnostic. It cannot
happen because **every one of those 24 sources needs an enable bit the firmware
never sets**: most of the peripherals do not exist on an 8-pin STM8S001J3 at
all, the rest come out of reset with their enables clear, `PA_CR2` is written
once for an *output* pin (where bit 3 is slew rate, not interrupt enable), PC3's
`CR2` is never touched, and the `TRAP` instruction appears nowhere in the image.
The argument is about a small, enumerable, statically checkable set — which is
why it is defensible, and why `vectors_prod.s` says to revert to a full table if
a second interrupt source is ever enabled.

Note also — and `vectors_prod.s` does not mention this — the reuse is not
limited to the documented window: `--code-loc 0x8068` puts ordinary program
bytes on `IRQ24` (FLASH end-of-programming) and `IRQ25…IRQ29`. The same
enable-bit argument covers it, with a small accident in its favour: the bytes
the linker happened to place at `0x8068` are SDCC's own dead reset stub,
`82 00 80 6F` = `INT s_GSINIT`, so a flash interrupt would restart the runtime
rather than execute garbage. That is luck, not design, and a future relink would
silently take it away.

Two link-time obligations, both guarded: `--code-loc 0x8068` is **mandatory**
(otherwise the linker places code at `0x8000` and destroys both live vectors),
and **sdld does not check ABS/REL overlap** — the same hazard that pins the
capture loop at the other end of flash, in the same image, for the same reason.
`guard_prod.py` checks that `HOME` starts at or above `0x8068` and that `VGAP`
stays inside `0x8004…0x8063`, anchored on the exported symbol `sot` (which
exists *only* so the map has an address for the guard to anchor on, since sdld
prints absolute areas with an address of 0).

---

# Every assembly source in the shipped image → readable C

| shipped source | what it is | readable C |
|---|---|---|
| `vectors_prod.s` | the vector table, 2 live entries | `rbarf_vectors.c` §0–1 |
| `decode_asm.s` area `VGAP` (`sot`, `swt`, `mediv`, `mydiv`, `hix`) | 92 B relocated into the vector gap | `rbarf_vectors.c` §2; the two tables also in `rbarf_capture.c` §5; the routines in `rbarf_decoder.c` §2–5 |
| `decode_asm.s` areas `CODE`/`DZP` | the whole decoder, hand-assembled | `rbarf_decoder.c` §0–9 (mapping table above) |
| `cap_arm.s` | the armed front end: idle gate, 4-poll comb, the jump | `rbarf_capture.c` §2 (line for line), §1 (the pinned addresses) |
| `caploop.s` `_cap_loop` | the pinned 40-cycle, 8-sample sampling loop | `rbarf_capture.c` §3 (line for line), §5 (the fitted model) |
| `caploop.s` `_cap_capture` | the legacy blocking entry (`wait_low`/`wait_high`) | `rbarf_capture.c` §3, `stm8_cap_capture()` |
| `app/ws2812_out.c` `__asm` block (95 lines) | the bit-banged WS2812 transmitter | `rbarf_ws2812_out.c` §1–3 |
| `app/tick.c` `__asm__("sim")`, `__asm__("rim")` | atomic 16-bit read of `ms_counter` | `rbarf_ws2812_out.c` §5.1 |
| `rbarf_prod.c` `__asm__("rim")` | enable interrupts, once, after setup | `rbarf_ws2812_out.c` §5.2 |
| `rbarf_prod.c` `__asm … __endasm` | the register-ABI call into `_cap_arm` | `rbarf_ws2812_out.c` §5.3 |
| — *(not in the shipped image)* | | |
| `cap_code.s` + `capture.c`'s two `__asm` blocks | the **acquisition** image (`capture.ihx`): the blocking capture entry and a `decw x` delay loop. A ledger artifact — it produced the corpora in `data/` and the timing model was fitted against it | `rbarf_capture.c` §3 (`stm8_cap_capture`, instruction-identical to `_cap_capture` apart from the loop count) |
| `scan.s` | the bench build's speed-unrolled scanner | superseded; not linked into any shipping image |

## Specifications

Specifications, in increasing order of detail: `docs/RECONSTRUCTION_PAPER.md` (the
human-language account), `docs/PROTOCOL.md` (the wire), `recon/EMBEDDED_V2_SPEC.md`
(normative, including §6.4 Lever B and §7 the chase), and
`recon/approaches/embedded_v2.py` (the normative implementation — if this file
and that one ever disagree, that one is right).
