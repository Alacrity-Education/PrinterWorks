# Embedded Feasibility — WS2812 reconstruction on the STM8S001J3

Validation of the `combined.py` reconstruction algorithm against the
STM8S001J3's 1 KB RAM / 8 KB flash / 16 MHz 8-bit CPU. **Every number in
this report is measured** — by ablation on the 54-capture dataset, by a
bit-exact integer reference (`approaches/embedded_ref.py`), by a C port
compiled with the project's own SDCC toolchain (`../archive/investigations/dev_embedded/
decoder.c`), and by instruction-level simulation (`ucsim_stm8`) calibrated
against the one loop whose real silicon timing is known exactly.

## Verdict

| Constraint | Verdict | Measured margin |
|---|---|---|
| Accuracy   | **51/54 exact (99.5 % bytes), holdout 18/18** vs host 53/54 (99.7 %) | −2 captures vs host; the host's own miss (rnd2_0) is shared |
| HSI envelope | **On par with the host** (embedded beats it at the fast corners) | both "fail" the ±7.5 % corners — a physical dead-window ceiling, not a porting penalty |
| Capture buffer | **256 B** (224 nominal is NOT enough at the fast HSI corner) | 13 loops (~30 µs) of latch margin at +8 % |
| RAM (1024 B) | **FITS — with one documented overlay** | measured 781 B DATA + 187 B peak stack; ~100 B margin after overlay |
| Flash (8192 B) | **DOES NOT FIT as auto-compiled C** | decoder alone measures 7.8 KB; decoder + app ≈ 10.3 KB (over by ~2.3 KB) |
| Cycles (< 100 ms @16 MHz) | **DOES NOT FIT as auto-compiled C** | measured ~4.4–4.8 M sim ticks ≈ 295–325 ms real; tight-asm projection 60–95 ms is *plausible but unproven* |

Bottom line: the **algorithm** ports to pure 8/16/32-bit integer
arithmetic with a 2-capture accuracy penalty and comfortably fits RAM.
The **implementation cost** does not fit: plain SDCC-compiled C is ~3×
over the flash budget available next to the application and ~3× over the
100 ms cycle budget. Feasibility therefore hinges on hand-optimization
(assembly sample scanner + code compaction) whose targets are quantified
below — or on relaxing the budget (a 0.3 s decode still gives a ~3 Hz
display update against 10 Hz input, since frames latch).

---

## 1. Capture buffer sizing (measured, not just arithmetic)

Production frame: HEADER(4) + 48 B GRB + TRAILER(4) = 56 B = **448 bits**
× 1250 ns = **560 µs** on the wire.

- Sampling loop = 40 cycles (fitted, hardware-exact) = 2500 ns nominal,
  8 samples/loop, 1 capture byte/loop → **224.0 loops = 224 bytes** at
  nominal clock. The prompt's arithmetic is confirmed — *at nominal only*.
- Fast HSI corner (+7.5 %): cycle 58.14 ns → loop 2325.6 ns →
  **240.8 loops**; at the +8 % test point, 243 loops. A 224-byte buffer
  truncates the trailer there.
- **256 bytes** (a power of two, like the current 640) covers +8 % with
  13 loops (~30 µs) of low-tail margin; the slow corner needs only 208.

Proof: the C decoder was fed exactly the **first 256 bytes** of
production-size synthetic captures at bench / −7.5 % / +7.5 % clock, and
produced byte-identical results to the Python reference seeing the full
640-loop capture, on 18/18 cases (`../archive/investigations/dev_embedded/eval_c.py`).

RAM after the buffer: 1024 − 256 = 768 B for decoder state + app + stack
(see §4).

## 2. Stage-by-stage portability audit of combined.py

Ablations measured in-memory on all 54 captures
(`../archive/investigations/dev_embedded/ablate_port.py`; baseline 53/54, misses shown there).

| combined.py stage / mechanism | Class | Measured cost of removal | Embedded treatment |
|---|---|---|---|
| S0 model clock A[m] (G, O[], w[]) | **KEEP** | — | fitted model is *exact integer cycles*: loop 40, O=[0,4,9,13,17,21,27,32], w=[0,−1,0,+2,0,0,0,+1]; per-sample integer adds |
| S1 run → rise/fall brackets | **KEEP** | — | streamed, O(1) state |
| S2 blind Hough (κ,τ) + alias retry | **DROP → replace** | N_ALIAS=1: 53/54 (0) | the production frame's *known length* pins κ to ±0.1 % from the endpoint span — one-bit-slip aliases (±0.5 %) are excluded a priori; a 2-iteration integer residual regression refines. A grid search is unnecessary *and* unaffordable (§6) |
| dual sampler model ("cal"+"fit") arbitration | **DROP** | fit-only: 50/54 (−3); cal-only: 53/54 | embedded ships the integer "fit" geometry. Transplanting cal's sub-cycle slot offsets as a static TU table was measured **harmful** (35/54) — the −3 is a real, unrecoverable architecture loss (nibbles_1-class captures) |
| S3 gap-accounting segmentation | **KEEP** | — | exact in integers; `(Δy+256)>>9` |
| S4 psi[] per-slot offsets | **DROP** | 51/54 (−2) | partially recovered by the eps analog below |
| S4 eps per-family boundary (cloud gap + preg) | **ADAPT** | eps off: 46/54 (**−7**) — the single most valuable mechanism | 64-bin fold histogram (u8) per razor family (5,6)/(6,7): largest label-feasible density gap, two-label-trust clamp (a lone extreme label gets a 20 ns radius, two concurring labels 5 ns), conflict midpoint, pure-zero floor. All integer |
| S4 h0c/h1c interval-censored width fit | **ADAPT** | — | closed-form interval intersection + prior clamp + the host's range guards (no iterative Huber search needed) |
| S5 interval-censored probit | **ADAPT** | — | interval **hinge** (compare-only, no mul) + tie-break: least cost, interior-before-grazing, fewer-ones. The interior rule was measured to decide rnd3_2's last knife bit |
| S5 per-slot probit widths WE[] | **DROP** | WE flat: 53/54 (**0**) | plain hinge |
| S5 dead-window prior + byte-period vote | **ADAPT** | dead vote off: 51/54 (−2) | fewer-ones tie-break + bit-array vote. **Gating fix found at production scale:** the host's dead vote is ungated; on a 448-bit random payload it flipped a dead bit on 3 coincidentally unanimous siblings — the embedded gates it behind the same periodicity proof as the knife vote |
| S5 knife-bit vote + periodicity gate | **ADAPT** | knife vote off: 47/54 (**−6**); both votes off: 45/54 | 1-bit confidence map (margin ≥ 16 TU) replaces float LLRs; knife list ≤ 32 × u16; integer gate `agree×100 ≥ 99×pairs, pairs ≥ 40`. Extended to family (6,7) — measured +1 (dense_0) with no regression |
| S4/5 self-training second pass | **DROP** (in final config) | host: 50/54 (−3); embedded final: **0** on all 54 + 18 production cases | the eps analog + gated votes made it redundant; dropping it removes 2 of 7 capture scans |
| S6 assembly + marker forcing | **KEEP** | — | a_bounds from the 56-byte KNOWN template (flash const) |
| S7 blind Q arbitration across aliases/models | **DROP** | covered by items above | single candidate |
| S8a re-registration, S8b repair retries | **DROP** | repair off: 53/54 (0) — clean captures never enter it | corrupted captures fall through to refusal |
| S8c honest refusal gates | **KEEP (adapted)** | — | violations>0 / infeasible>4 / label_err>6. One adaptation measured *necessary*: a dead marker window (both hypotheses interior — no evidence) must not count as a label error, or the entire +5…+7.5 % corner refuses wholesale |
| all-drop floor (naive port) | | **40–41/54** | the ADAPT work above recovers it to 51/54 |

## 3. The embedded-shaped reference (`approaches/embedded_ref.py`)

Integer-only (8/16/32-bit, asserted on every assignment — zero violations
across all runs), no floats, table lookups only, forward-only streaming
passes (no pulse array is ever stored), deterministic (two full runs
sha256-identical).

Pipeline: P1 endpoint seed → P2 ×2 residual regression (K u16 Q11, τ s16)
→ P3 marker calibration + eps histograms → P4 hinge decision + emit +
1-bit confidence — → gated byte-period votes → refusal gates. 5 scans of
the capture buffer total.

Key design findings (all measured):

- **Time-unit resolution is decisive**: at TU = BIT/128 (9.77 ns) every
  remaining error was a (5,6)-family knife bit lost to quantization; at
  TU = BIT/512 (2.44 ns) the boundary information survives. Cost: mapped
  absolute times become u32 (all products still < 2³¹).
- **Censoring belongs in fits, not gradients**: an interval-censored
  *mean* residual for the lock has no gradient once brackets straddle
  (measured collapse to 21/54); an interval-censored *search* (Hough
  polish) was measured net-negative too (hit plateaus ~5 TU wide). The
  midpoint regression + per-capture calibration absorbing its bias is
  the right integer structure.
- **Selection effects poison means**: a per-family mean-residual offset
  (psi analog) measured *worse than nothing* (38→47/54 when removed);
  only interval/boundary statistics survive labelled-data selection.

Scores (`python3 eval.py approaches/embedded_ref.py`):

| split | embedded_ref | host combined.py |
|---|---|---|
| --all | **51/54, 99.5 % bytes** | 53/54, 99.7 % |
| --holdout | **18/18, 100 %** | 18/18 |
| misses | nibbles_1 (1 byte), rnd3_0 (emits ~3 bytes wrong), rnd2_0 (1–3 bytes) | rnd2_0 |

Miss anatomy (ground truth used as a diagnostic ruler only):
rnd2_0 is the shared information-ceiling miss (1–2 ns knife bits).
nibbles_1's wrong bits are **not linearly separable** in the fitted
geometry (truth-0 at u=150, truth-1 at u=148 in the same capture) — the
host wins it through its second sampler model. rnd3_0 needs a
boundary-vs-position precision (~7·10⁻⁵ tilt) beyond the integer lock.

HSI temperature envelope (`eval_envelope.py`, 54 synthetic decodes per
point — measured for BOTH decoders):

| clock error | embedded exact | host exact |
|---|---|---|
| −8.0 % | **17** | 15 |
| −7.5 % | 12 | **16** |
| −5.0 % | **38** | 36 |
| −2.5 % | 54 | 54 |
| −1.0 % (≈bench) | 53 | 53 |
|  0.0 % | 53 | 54 |
| +1.0 % | 38 | **40** |
| +2.5 % | 32 | **33** |
| +5.0 % | **14** | 0 |
| +7.5 % | **9** | 0 |
| +8.0 % | **14** | 11 |
| −7.5 % + drift | **9** | 6 |

Both decoders sit at the documented physical corner ceiling (at large
|eps| up to half the payload windows are never sampled); the embedded
variant is *not* the weak link on temperature. The real device measures
ε = −1.12 % ± 0.014 %, where both are at/near 100 %.

Production-size behavior (448-bit synthetic frames, fitted sampler, bench
clock): zeros/ones/aa/55/GRB-ramp payloads decode exactly; an adversarial
random payload emits 2–3 knife-bit byte errors (byte-acc ~99.5 %) — the
448-bit analog of rnd2_0. The refusal gates pass such frames (their blind
quality is clean), so the application must tolerate rare wrong bytes or
add a CRC to the wire format (recommended; see Risks).

## 4. Memory budget (measured from the SDCC map, NB=448)

`../archive/investigations/dev_embedded/decoder.c` keeps all state in static globals so the linker
map *is* the RAM measurement: **DATA = 781 B**, peak stack (simulated,
including main) = **187 B**.

| item | bytes | note |
|---|---|---|
| capture buffer | 256 | §1; power of two, covers +8 % |
| bits / conf / tied bitmaps | 3 × 56 = 168 | NB/8, bit-packed |
| eps fold histograms | 2 × 64 = 128 | **overlayable**: used only before the decision pass touches bits/conf/tied |
| knife list (32 × u16) | 64 | 448-bit random payload measures ~24 candidates |
| resolved list (16 × u16) | 32 | dead-vote bookkeeping |
| hypothesis costs (16 × u16) | 32 | A_CAP = 15 |
| label windows / c0 / gaps / widths | ~40 | s16 each |
| lock + stream state, counters | ~53 | K, τ, 6 × 32-bit accumulators, pulse regs |
| payload out | 48 | doubles as the animation's base-color input |
| **decoder total** | **781** | measured (DATA segment) |
| stack | 192 | measured peak 187 (≥128 required) |
| app persistent (ws2812_out buf 48 + timers/flags) | ~80 | old firmware's anim state, minus its 227 B capture area |
| **total with overlay** | **~925** | hist (128) overlaid on decision bitmaps |

**RAM: FITS — 1024 − 925 ≈ 100 B margin**, provided the one overlay
(safe: histograms are dead before the decision arrays are first written).
Without the overlay: 1053 B — over by 29, so the overlay is mandatory.

## 5. Flash budget (measured: SDCC 4.6, -mstm8 --opt-code-size)

Decoder at NB=448 — per function, from the assembler listing:

| function | bytes | | function | bytes |
|---|---|---|---|---|
| votes | 1038 | | cal_add | 277 |
| ps_next (sample scanner) | 798 | | ws_decode | 260 |
| decide_pass | 750 | | label_interval | 219 |
| refine | 697 | | seed | 191 |
| theta56 | 669 | | ps_init / ss_init / a_bounds | 306 |
| calibrate | 649 | | known_bit, cal_cloud, map_y, misc | 293 |
| ss_next | 634 | | decide | 528 |

**Decoder code ≈ 7.37 KB + ~0.35 KB SDCC 32-bit mul/div library + 40 B
const ≈ 7.8 KB.**

Application (recompiled from the old firmware sources with the same
flags): cap_code 77, ws2812_out 105, anim ≈ 2826 (incl. the 1024-B gamma
LUT), main/glue ≈ 161, startup/vectors ≈ 120; debug UART (optional) 422.
Minimum production app ≈ **2.5 KB** (gamma shrunk to 256 B, no debug
UART).

**Flash: DOES NOT FIT — 7.8 + 2.5 ≈ 10.3 KB vs 8.19 KB (over by ~2.3 KB,
28 %).** Quantified paths:

- The accuracy-critical machinery is precisely the bulk: eps analog
  (theta56 + cal_cloud + parts of cal_add/calibrate ≈ 1.3 KB, worth +7
  captures) and the votes (≈ 1.1 KB, worth +8). Dropping both fits
  trivially but lands at ~40–45/54 — not acceptable.
- SDCC's stm8 codegen for this struct-streamed, 32-bit-heavy C is the
  real cost (~10–14 B per source operation). A hand-assembly rewrite of
  the streaming layer (ps_next/ss_next/refine bodies ≈ 2.1 KB of C) plus
  fusing the two vote loops is a realistic −2…−2.5 KB, which *just*
  closes the gap — unproven until done.
- Alternative: the pin-compatible STM8S003/005 (8 KB is the S001's cap;
  an S103K3 or S005 variant with the same core and more flash removes
  the constraint entirely, at a board respin cost).

## 6. Cycle budget (measured by simulation, calibrated against hardware)

Simulator calibration first (STM8_CYCLE_COUNTING.md warns documented
counts are wrong on this silicon): the capture loop — the one code whose
true timing is hardware-verified against the crystal-exact PIO signal
(40.0 cy/loop fitted at 99.96 % sample agreement) — measures **37.4
ticks/loop in ucsim vs 40 real cycles**: ucsim tracks the *documented*
counts and under-reads this chip by ~7 % on this instruction mix.

Measured decode of a production 448-bit frame from a 256-B buffer
(NB=448 build, result verified correct in-sim):

| phase | ucsim ticks |
|---|---|
| P1 endpoint seed (1 scan) | 516 k |
| P2 lock regression (2 scans) | 1259 k |
| P3 calibration (1 scan) | 979 k |
| P4 decision + emit (1 scan) | 1407 k |
| votes (bit arrays only) | 252 k |
| **total (aa48)** | **4.41 M** |
| range across payloads (zeros/aa/rnd) | 4.40–4.82 M |

With the +7 % silicon correction: **≈ 4.7–5.2 M cycles ≈ 295–325 ms at
16 MHz.** Predicted on-target cycle count: **~4.9 M ± 10 %** as compiled.

**Budget verdict: FAILS the 100 ms goal by ~3×** as plain SDCC C. Two
mitigating facts, both measured:

- The op counts are small — worst case 9,960 sample-visits, 2,240
  pulse-visits, 3,595 32-bit multiplies, 17 divisions, 896 hypothesis
  evaluations across 5 scans. Costed at hand-assembly rates (sample ≈ 14
  cy — cap_code.s demonstrates 4 cy/sample is achievable for a *simpler*
  loop — pulse ≈ 40, mul16×16→32 ≈ 60, div ≈ 400, with a 2× adverse
  margin) the same work is **≈ 1.0 M cycles ≈ 62 ms**. The gap is
  entirely SDCC codegen on the streaming layer (~200+ ticks per sample
  visit measured vs ~15–20 attainable).
- Exact byte-level fast paths (all-low / all-high capture bytes) are
  already implemented and verified (−9 % on aa, more on sparse frames);
  dropping the redundant self-train pass already removed 2 of 7 scans at
  zero accuracy cost.

If the 100 ms goal is relaxed: at 10 Hz input the as-compiled decoder
still decodes every ~3rd frame (frames are self-contained and latch), so
the *application* degrades gracefully to a ~3 Hz update rate rather than
failing.

## 7. Files

- `approaches/embedded_ref.py` — the integer-only reference (scored
  above); Q-formats documented in its header; deterministic.
- `../archive/investigations/dev_embedded/decoder.c` — bit-exact C port; **identical
  output to the Python reference on all 54 real captures and all 18
  production-size synthetics** (`eval_c.py`), compiled for host (gcc,
  ctypes) and target (SDCC).
- `../archive/investigations/dev_embedded/ablate_port.py` — the §2 ablation battery.
- `../archive/investigations/dev_embedded/opcount.py` — measured operation counts +
  tight-asm cost model.
- `../archive/investigations/dev_embedded/eval_c.py`, `sim_main*.c`, `capsim.s` —
  parity harness, simulator images, and the ucsim calibration loop.

## 8. Top risks

1. **Flash is the hard wall.** The measured 2.3 KB overrun must come out
   of hand-optimization of exactly the code that carries the accuracy;
   any slip forces the accuracy-vs-size cliff (−6…−11 captures) or a
   part change.
2. **Cycle projection is unproven.** 62–95 ms rests on rewriting the
   sample scanner in assembly; the measured as-compiled number is 3×
   over. Budget real firmware-engineering time, or accept ~3 Hz decode.
3. **Confidently-wrong knife bits at production scale.** A 448-bit
   random payload measures 2–3 wrong bits that pass the refusal gates
   (identical failure class to the host's rnd2_0). The GRB application
   tolerates a rare wrong color byte, but a wire CRC (1–2 bytes in the
   trailer) would convert these to detectable refusals for ~zero decoder
   cost.
4. **Model drift.** The decoder hard-codes the fitted sampler geometry
   (integer cycles). A firmware change to the capture loop (instruction
   alignment moves w[]) silently invalidates it — the fitted-model
   re-verification procedure in `dev_calibration/` must gate any capture
   loop edit.
5. **nibbles_1-class captures** (dual-model-only decodes) are a known −1
   vs host that no single-geometry embedded decoder recovers; confirmed
   not fixable by a static per-slot offset table (measured 35/54).
