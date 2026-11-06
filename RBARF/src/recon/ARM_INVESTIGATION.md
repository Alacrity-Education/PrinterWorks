# RBARF capture-arm investigation — R3 is an arm-PHASE failure on COMPLETE bursts

**Date** 2026-09-07 · **Scope** §1-§8 investigation (no shipping file
changed); **§9 the fix, implemented and measured** · **Bench** one
STM8S001J3, RP2040 test probe, 448 + 299 production frames · **Scratch**
`recon/approaches/dev_arm/` (diagnosis), `recon/approaches/dev_fe/` (fix)

---

## TL;DR

1. **The R3 verdict: NO. R3 is not a partial burst.** 42 of 48 dumped `R3`
   refusals (88 %) are **complete bursts** — full 478.5-bit span, `K`
   comfortably inside the window, `eps` in the tight −0.9…−1.1 % cluster,
   marker violations 2 of 48 — that fail in the **decision stage**
   (infeasible **459 of 461** segments, against **0** for every delivered
   frame). The other 6 are partial (the R1 mechanism, one stage earlier).

2. **The cause is the arm's trigger phase `t0`, and it is a hard cliff at
   `t0 = 681 ns`.** Sweeping *only* `t0` with the shipped decoder:
   `t0 ≤ 680 ns` → **0 R3** over 10 payloads; `t0 = 690 ns` → first R3;
   `t0 ≥ 720 ns` → **100 % R3, every payload, every point to 1300 ns**.
   The cliff is the capture loop's **slot-2 offset crossing the WS2812 bit
   period**: `t0_crit = BIT_NS − SLOT_OFFSET[2]/(1+eps)`. Swept over
   `eps = −5 %…+6 %` the measured cliff tracks that formula to **0.7–4.9 ns**.

3. **No decoder change can recover it.** Over the whole fatal band,
   `GATE_INFEAS` relaxed from 24 to 60/120/240/480 recovers **0 of 280**
   (the refusal just migrates R3 → R4), and re-anchoring the leading
   unbracketed pulse recovers **0 of 280**. 0 wrong emissions either way.
   The information the decoder needs was never sampled. **This must be
   fixed in `cap_arm.s`.**

4. **This is also the corpus-vs-live gap.** The 54 `captures_v23.json`
   captures — taken with `capture.ihx`'s *blocking* entry — fit
   `t0 = 89…628 ns`, **0 of 54 above the cliff**. The production arm sits
   at `t0 = 288…862 ns` (p50 472) with **9.7 % above it**, and every one of
   those that is not fit-boundary noise refuses R3. The corpus scores 97.8 %
   because its trigger phase never reaches the cliff.

5. **R1 is confirmed as the render collision.** All 16 `R1` dumps are
   head-chopped partial bursts (span 11…303 bits of 479); every one has
   the mid-render signature (a render ran in the unarmed gap **and** the
   edge was caught < 50 µs into the arm). Rate **5.13 %** of captures,
   against a **measured 5.56 %** render duty cycle. No delivered frame
   ever had a chopped burst.

6. **Three of the five candidate fixes are worth zero, measured.**
   Lock-retry (the deferred margin-report fix #2) **0 frames**; arm-window
   widening **≤ 0.44 %**; tick masking **0** (already done, gap is 5 µs);
   host cadence guard-band **0** (78.5 % strict vs 80.6 % dithered, n.s.).
   The two that pay are the arm's `t0` (**+7.4 pp**) and the render hole
   (**+5.1 pp**).

7. **No host-vs-chip divergence.** 177/177 dumps: chip and host agree on
   status *and* cause. 0 wrong emissions.

8. **§9: THE FIX IS BUILT, AND IT LANDED.** Three edits worth **one byte
   of flash** — enter the pinned loop at `_cap_loop+1` (word-aligned, one
   cycle earlier), retime the poll comb, require a sustained low before
   arming — plus the render at 25 Hz. `t0` **288…862 ns → 102…650 ns**,
   **0 of 79** dumped complete bursts above the cliff, complete-burst
   `R3` **31 → 0**. Production gate **26/30 → 28/30 cold** and
   **22/30 → 29/30 warm**, `R1`+`R3` **75.1 % → 3.1 %** of refusals,
   **0 wrong emissions in 1 855 accepted emissions**, 0 resets.

---

## 1. The diagnostic image

`recon/approaches/dev_arm/rbarf_arm.c` — bench-only, linked against the
**unmodified** production `.rel` set (`decode_asm.s`, `decode.c`,
`caploop.s`, `cap_arm.s`, `anim.c`, `ws2812_out.c`, `tick.c`,
`vectors_prod.s`) by `dev_arm/build.sh`.

For **every captured frame**:

```
A<28 hex>     14 telemetry bytes
   [0]     (status<<4)|cause          status 0=refuse 1=direct 2=chase
   [1..2]  eps, centi-%, int16 BE
   [3..4]  TIM2 µs stamp, ARM ENTRY   (new: TIM2 free-running at 1 MHz)
   [5..6]  TIM2 µs stamp, ARM RETURN
   [7..8]  TIM2 µs stamp, last RENDER START
   [9..10] TIM2 µs stamp, last RENDER END
   [11]    cap_arm calls that TIMED OUT since the last capture (saturating)
   [12..13] TIM2 µs stamp, PREVIOUS arm RETURN
B<576 hex>    the raw 288-byte capture: every REFUSAL + every 4th capture
```

`[3..4] − [12..13]` is the **unarmed gap** before this capture's window;
`[5..6] − [3..4] − 720` is the **arm wait** (edge minus arm entry; the
capture itself is 288 × 40 cy = 720 µs). The frame window is **240 of the
288 loops**, not the 96–120 in the phase brief (that is the 216-bit v2.1
geometry); the whole 288 B is dumped.

**Derived host-side at zero flash cost** — the pulse count, the burst
span, head chop / tail truncation / buffer overrun, `(t0, eps)` by fit
against the calibrated sampler, and hence *which of the four BTJT polls
caught the edge* (they are 2 cy = 125 ns apart and the `t0` fit resolves
better than that: **0.0 ns error** on synthetic captures of known `t0`).
Instrumenting the poll itself was rejected — it would have added cycles
between the poll and `_cap_loop`, i.e. perturbed the very quantity under
measurement.

### The flash squeeze, and the levers taken

The verbose production image has **41 B** free and its REL end is 26 B
below `CAPARM0`. Four levers paid for the 288-byte dump *and* the
telemetry, and the diagnostic image ends up **smaller** than the shipping
verbose one:

| lever | saved |
|---|---|
| eps as raw hex inside the block — the §15.0 lever; `uart_put_i16` + its power-of-ten table drop out | 92 B |
| no `V:` line — the dump plus the bit-exact host decoder recover the emitted bytes | ~25 B |
| no status/cause/`:` character formatting — **one** `uart_blk()` loop emits the whole fixed-width block | ~25 B |
| no `auto_trim()` — §15.2 measured `trim_v` == code 0 for **1634/1634** verified decodes, so `CLK_HSITRIMR` stays `0x00` and the operating point is bit-identical | 29 B |

UART runs at **38400** rather than 9600, so a 288-byte dump costs 150 ms
instead of 600 ms. Dump integrity is checked the same way the phase needs
anyway — the host re-decodes every dump and compares the verdict with the
chip's (177/177 agree).

| | value |
|---|---|
| guard | **`prod guard OK: REL end 0x9F46 <= CAPARM 0x9F66; _cap_loop 0x9FAF phase 0xF; flash free 47 B`** |
| `CAPLOOP` `0x9FA1..0x9FF0` | `273e269f41527530fd4a0261eb70f8a0` — **byte-identical to the ledger** |
| `0x9FF1..0x9FFF` | `9ddd02276e5c30436e3b530eba05ad6a` — **byte-identical** |
| `CAPARM0` `0x9F66..0x9FA0` | **4 bytes differ** from the shipping image, all of them the `s_arm` operand (`0x034C` → `0x0358`, the 12-byte telemetry array shifting REL DATA) — the same accepted difference class as §14. Every other byte, including all four `72 06 50 0B <rel>` polls with rels `29 24 1F 1A`, is identical, so the arm is cycle-for-cycle the shipping arm |
| RAM | DATA +12 B → stack space 136 B (was 148); measured peak 115 B → **21 B margin**. 0 resets over 450 frames |
| image | 8 177 B written, banner `RBARF-A 1` at **5.06 s** — SWIM window respected |

A ucsim boot test (`dev_arm/ucsim_boot.py`, `setsid timeout -k` + pkill
sweep, zero strays) reaches the post-init `rim` at `0x828B`; ucsim's
STM8S208 model simulates neither TIM4 nor TIM2, so the timebase was
validated on silicon instead (first telemetry line).

**Fidelity caveat.** The two TIM2 stamps sit inside the unarmed gap by
construction and inflate it by ≈ 2 µs; the measured gap is 5 µs p50, so
the production gap is ≈ 3 µs. Neither figure is capable of producing a
6 % refusal rate, so the inflation does not affect any conclusion.

---

## 2. The bench runs

`dev_arm/drive_arm.py`, the 10 production payloads as 60-byte v2.3 wire
frames (`bench/drive_prod.py` `FRAMES` imported from the file; the bench
sources are not modified), each on the wire **exactly once**.

| run | schedule | sent | captured | delivered | refused | dumps | resets |
|---|---|---:|---:|---:|---:|---:|---:|
| **A** | 250 ms + uniform 0…12 ms dither + drain | 300 | 299 (99.7 %) | **241 (80.6 %)** | 58 | 116 | 0 |
| **B** | **strict 250.0 ms**, no dither | 150 | 149 (99.3 %) | **117 (78.5 %)** | 32 | 61 | 0 |
| pooled | | 450 | 448 (99.6 %) | **358 (79.9 %)** | 90 | 177 | 0 |

Pooled refusal mix: `R3` **48 (53 %)**, `R1` **16 (18 %)**, `R6` 11,
`R8` 8, `R4` 4, `R7` 2, `R2` 1. §15.3's ordering is reproduced — `R3`
dominant, `R3`+`R1` = **71 %** of refusals, i.e. the front end.

Dumping is biased by design (every refusal, every 4th capture), so every
rate quoted per *frame* is reweighted: 90 refusals dumped of 90 (w = 1),
87 successes dumped of 358 (w = 4.115).

---

## 3. Attribution — is it a partial burst?

`dev_arm/analyze_arm.py` per dump: burst geometry, host re-decode at the
shipped constants, and a `(t0, eps)` fit with `t0` searched over
0…4000 ns so that a head chop shows up as `t0 ≥ 1250 ns` (one bit).

| | dumps | verdict |
|---|---:|---|
| **complete** bursts (`t0` < 1 bit, span ≈ 478.5 bits) | **154** | |
| **partial** bursts (head-chopped ≥ 1 bit) | **23** | `R1` × 16, `R3` × 6, `R2` × 1 |
| delivered frames with a chopped burst | **0** | a chop is always fatal |

Chopped spans, bits of 479: `11 31 89 129 178 187 188 218 220 222 235 258
262 296 303 383 403 454 472 474 474 476 476`. The 178–303 cluster is
§13's 102–302 pulses, reproduced; the four 454–476 spans are the small
chops that squeeze inside the `K` window and land in `R3` instead of `R1`.
Partial-burst rate over captured frames: **23.0 / 448 = 5.13 %**.

### The R3 verdict, with numbers

| | complete-burst R3 (n = 42) | delivered (n = 87) |
|---|---:|---:|
| burst span, bits of 479 | **478.4** (median) | 478.5 |
| `K` (window 40 000…64 000) | **52 911** | 52 900 |
| `eps` reported by the chip | **−0.91 %** | −1.05 % |
| marker violations, of 48 | **2** | 0 |
| **infeasible segments** | **459 of 461** | **0 of 466** |
| label errors | 18 | 0 |
| **fitted `t0`** p10 / p50 / p90 / max | **652 / 716 / 784 / 860 ns** | **363 / 457 / 620 / 740 ns** |

**88 % of R3 refusals are complete bursts with a perfect lock.** The
clock fit is *not* failing: `K`, `eps`, the span and the markers are all
normal. What fails is the decision stage, wholesale — 459 of 461 segments
at once — and the only quantity that separates the two populations is the
**arm trigger phase**.

### The cliff, isolated causally

`dev_arm/t0_sweep.py` synthesises captures with the calibrated sampler at
`eps = −1.07 %` and decodes them with the shipped decoder, sweeping **only
`t0`**:

| `t0` (ns) | n | delivered | R3 | median infeasible |
|---|---:|---:|---:|---:|
| 0…640 | 640 | 587 | **0** | 0 |
| 640…680 | 40 | 33 | **0** | 0 |
| 680…720 | 40 | 8 | **30** | — |
| 720…1300 | 580 | **0** | **580** | 194 |

Safe window **0…680 ns**, first R3 at **690 ns**, saturated by 720 ns,
**payload-independent** (every one of the 10 payloads: last delivered
620–680 ns, first R3 690–700 ns). Below 680 ns there is no `t0`
dependence at all — the residual misses there are content-driven `R6`/`R8`.

### Why the cliff is where it is

The capture loop's eight sample slots sit at
`[0, 250, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000] ns`. Slot 2 leaves
the first bit period when `t0 + 562.5/(1+eps) ≥ 1250`:

```
t0 = 680 : s0→bit0 H   s1→bit0 L   s2→bit0 L   s3→bit1 H     (delivers)
t0 = 690 : s0→bit0 H   s1→bit0 L   s2→bit1 H   s3→bit1 H     (R3)
```

At that phase the sample comb re-partitions across **every** bit pair in
the frame, the segment stream's hinge costs all shift off their predicted
boundaries, and the infeasibility count goes from 0 to ~460 in one step.

`t0_crit = BIT_NS − SLOT_OFFSET[2]/(1+eps)`, tested over a 61-ns range of
predicted cliff (`dev_arm/cliff_proof.py`):

| `eps` | predicted | measured first R3 | error |
|---|---:|---:|---:|
| −5.00 % | 657.9 ns | 660 ns | 2.1 ns |
| −3.00 % | 670.1 ns | 675 ns | 4.9 ns |
| **−1.07 %** | **681.4 ns** | **685 ns** | **3.6 ns** |
| 0.00 % | 687.5 ns | 690 ns | 2.5 ns |
| +3.00 % | 703.9 ns | 705 ns | 1.1 ns |
| +6.00 % | 719.3 ns | 720 ns | 0.7 ns |

The mechanism is proven, not inferred. Note the cliff moves with `eps`
only 6 ns between 0 % and −1.07 %, so the auto-trim target is not a lever.

### It cannot be repaired in the decoder

Over the fatal band (10 payloads × 28 points = 280 cases):

| repair | delivered | WRONG | residual causes |
|---|---:|---:|---|
| shipped (`GATE_INFEAS` 24) | 0/280 | 0 | R3 × 280 |
| ignore the leading unbracketed pulse | 0/280 | 0 | R3 × 280 |
| `GATE_INFEAS` 60 / 120 | 0/280 | 0 | R3 × 280 |
| `GATE_INFEAS` 240 | 0/280 | 0 | R3 × 30, **R4 × 250** |
| `GATE_INFEAS` 480 (20× shipped) | 0/280 | 0 | **R4 × 280** |

Relaxing the feasibility gate is *useless* (and, usefully, *harmless* —
0 wrong emissions at 20× the shipped threshold). `FIRST_BR` 4→20 cy
changes nothing at all. **The fix has to move `t0`.**

### The corpus-vs-live gap, closed

§15.3 left "the corpora deliver 97.8 % while the live gate delivers 80 %"
unexplained. Fitting `t0` on the 54 `data/captures_v23.json` captures,
which were acquired with `capture.ihx`'s **blocking** entry (mean fit
agreement 0.9914):

| source | `t0` min / p10 / p50 / p90 / max | above the 681 ns cliff |
|---|---|---:|
| `captures_v23.json` (blocking entry) | 89 / 270 / **384** / 472 / 628 ns | **0 of 54 (0 %)** |
| production arm (`cap_arm.s`), weighted over complete-burst captures | 288 / 369 / **472** / 680 / 862 ns | **9.7 %** by fitted `t0`, of which **7.4 pp** are refusals (the other 2 dumps are fit-boundary noise, §7) |

`cap_arm.s`'s own header notes the design "grows worst common-case t0 by
~3 cy (~190 ns)" and justifies it against the wrong bound — the first
pulse's `T1H_eff` of **752 ns**. The binding bound is slot 2 at **681 ns**,
and the design spent exactly the margin that separates them.

---

## 4. Arm characterisation

| quantity | measured (448 captures) |
|---|---|
| unarmed gap between consecutive arm windows | **p50 5 µs**, p90 561 µs, max 665 µs (≈ 2 µs is diagnostic stamping) |
| captures with gap ≤ 100 µs (chip continuously armed) | **355 (79.2 %)** |
| captures with gap > 100 µs (a render ran in the gap) | **93 (20.8 %)** |
| render length on silicon | p10 400, **p50 556**, p90 655, max 658 µs |
| **render duty cycle** at the 100 Hz tick | **5.56 %** of wall time |
| arm wait (edge − arm entry) | p10 131, p50 816, p90 1525, **max 1684 µs** → the window is ~1.68 ms and uniformly used |
| frames never captured (no report at all) | **2 of 450 = 0.44 %** |
| MCU resets | **0** |

**Arm-entry phase / which poll caught the edge** (weighted to all
captures; the four BTJT polls are 2 cy = 125 ns apart and the fourth is
followed by a 5-cy `dec a; jrne` slot):

| `t0` band | entry + | captures (weighted) |
|---|---:|---:|
| 238…300 ns | −1 cy | 4.1 |
| 300…362 | 0 | 28.8 |
| **362…425** | **1** | **93.5** |
| **425…488** | **2** | **87.3** |
| 488…550 | 3 | 56.5 |
| 550…612 | 4 | 61.5 |
| 612…675 | 5 | 49.0 |
| **675…738** | **6** | **25.1** ← above the cliff |
| **738…800** | **7** | **17.1** ← above the cliff |
| **800…862** | **8** | **2.0** ← above the cliff |

The distribution spans ≈ 9 cy, wider than the 5-cy poll slot alone —
consistent with the address-phase-dependent flash fetch stalls that make
the *capture* loop run 40 cy instead of its documented 37. The top three
bins, **7.4 % of captured frames**, are the entire complete-burst `R3`
population.

**Is the render stealing the arm window? Yes, and exactly at its duty
cycle.** The mid-render signature — a render in the unarmed gap **and**
the edge caught < 50 µs into the arm, i.e. the line was already toggling
when the window opened — occurs on **22 captures**; 19 refuse
(`R1` × 16, `R3` × 2, `R2` × 1) and **18 of the 22 dumps are head-chopped
partial bursts**. Rate 5.13 % of captures against a 5.56 % render duty
cycle. The enabling defect is that `cap_arm`'s wait-low phase accepts a
**single** low sample as "idle", so a window that opens mid-frame triggers
on the next mid-frame rising edge instead of waiting for the ≥ 50 µs
WS2812 reset gap.

**The tick ISR is not a factor** — it is already masked per 176-µs burst
and the measured inter-window gap is 5 µs. **The host cadence is not a
factor** — strict 250 ms (78.5 %) versus 250 ms + dither (80.6 %) over
n = 149 / 299 is inside binomial noise.

---

## 5. Divergence check — none

| | |
|---|---|
| dumps where chip and host agree on **status and cause** | **177 / 177** |
| dumps the host DELIVERS that the chip REFUSED | **0** |
| host wrong emissions over all dumps | **0** |

No decoder/firmware divergence. This also validates dump integrity at
38400 baud.

---

## 6. Ranked fixes, sized

Baseline: **358/448 = 79.9 %**, i.e. **24.0 / 30**.

| # | fix | predicted recovery | evidence | flash / RAM / time | touches calibrated timing? |
|---|---|---|---|---|---|
| **1** | **Bring the arm's `t0` upper tail below 681 ns.** First attempt is **zero-flash**: re-phase `CAPARM_ORG` (23 legal addresses `0x9F50…0x9F66`, all 16 residues mod 16 reachable) to shed the poll loop's fetch-stall cycles. Fallback: unroll the poll loop 4 → 16 polls per `dec a`, so the 5-cy slot covers 3 of 35 cycles instead of 3 of 11 | **+33.0 frames = +7.4 pp → 87.3 % (26.2/30)**. A 3-cy shift removes the population entirely (8.5 % → **0.0 %**); 1 cy → 1.8 %; 2 cy → 0.4 %. Unrolling alone ≈ +5 pp | t0 sweep (0 R3 ≤ 680 ns, 100 % ≥ 720), the cliff-vs-`eps` law to ±5 ns, the measured comb, the corpus at 0/54 | re-phasing **0 B**; unrolling **+60 B in `CAPARM0`, which is 100 % full** (59 B, flush to `_cap_capture`) so the shipping image must free ≈ 38 B first. RAM 0. Time 0 | **YES — arm timing.** Not the pinned loop: `CAPLOOP` stays byte-identical. Needs the `t0` instrument from this phase to re-verify, plus guard green |
| **2** | **Shrink the render hole.** Render at 50 Hz (`>= 10` → `>= 20`), or only when the animation frame actually changes | **+11.5 frames = +2.6 pp → 82.5 % (24.8/30)** at 50 Hz; the full 5.13 % (+1.5/30) only if the hole goes to zero, which `ws2812_out_send` cannot do — the waveform is uninterruptible | 5.13 % chopped captures vs a 5.56 % measured duty cycle; 18/22 mid-render captures are chopped; 0 chopped capture ever delivered | **0 B**, 0 RAM. Costs animation smoothness | no |
| **3** | **Reject mid-frame arms:** require a sustained low (≥ 40 µs, the WS2812 reset gap) in `cap_arm`'s wait-low phase before accepting a rising edge | **0 frames** — it cannot un-lose a frame that is already half gone. It converts 16 `R1` + 2 `R3` + 1 `R2` refusals into clean no-reports and stops a doomed capture consuming a decode window. Worth doing **with** #1/#2 as hygiene, not for delivery | the 22 mid-render captures; R1 aborts in 3–11 ms so the reclaimed time is small | ≈ +8 B in a **full** area (see #1); 0 RAM | **YES — arm timing** |
| **4** | **Lock-retry / re-arm on a bad lock** (deferred margin-report fix #2) | **0 frames. Drop it.** | Single transmission: all 16 `R1`s are partial bursts of a frame that had already ended when the lock failed. There is nothing left on the wire to re-capture | — | — |
| **5** | **Arm-window widening** | **≤ +2 frames of 450 = 0.44 %** | The arm already runs 1.68 ms windows with a 5-µs gap and captures 448/450; only 2 frames produced no report at all | — | — |
| **6** | **Masking the tick ISR during arm** | **0 — already done** | `sim`/`rim` per 176-µs burst; measured inter-window gap 5 µs p50, no capture shows an ISR-sized hole | — | — |
| **7** | **Host cadence guard-band** | **0** | Strict 250 ms 117/149 = 78.5 % vs dithered 241/299 = 80.6 %; 2.1 pp over these n, not significant | — | — |
| **8** | Content margin (`R6`/`R7`/`R8`/`R4`) — a decoder phase, not this one | **+34.0 frames = 7.6 pp** available, but **24 of the 45 losses are the single payload `full`** (all-`0xFF`, 19/45 = 42.2 % delivered) | all these refusals have a safe `t0` on a complete burst; `full` is the merged-1 stress case | — | no |

**#1 + #2 → 92.4 % = 27.7 / 30**, and #1 alone lifts the 30-frame gate
from 24.0 to **26.2**. Neither reaches ≥ 28/30 on its own: the remaining
gap is #8, which is content, concentrated in one payload, and is where the
`R6`/`R8` confidence work §15.9 deferred actually belongs.

Per-payload delivery, pooled: `colors` 90.9 %, `preset_rainR` 90.9 %,
`dark` 88.9 %, `seq_pause` 88.9 %, `blink` 84.4 %, `fade` 82.2 %,
`seq_plain` 80.0 %, `preset_spin` 80.0 %, `rnd` 71.1 %, **`full` 42.2 %**.

---

## 7. What this phase did NOT establish

* **One unit, one temperature.** Both runs are the same STM8S001J3 at
  code 0, room temperature, ≈ 10 minutes of running. The `t0` distribution
  is a property of this die's flash-fetch timing at this `CAPARM` address;
  another unit or another temperature could sit further above or below the
  cliff. The cliff itself is a model/geometry constant and is not
  unit-dependent.
* **No fix was built or flashed.** Every recovery figure is the measured
  population above the cliff, not a demonstrated delivery. #1's zero-flash
  variant (re-phasing `CAPARM_ORG`) is a hypothesis about fetch stalls; it
  is cheap to test with this instrument (one flash + one 300-frame run per
  candidate address) but it is untested.
* **The fitted `t0` on real silicon carries residual error.** The
  estimator is exact on synthetic captures (0.0 ns) but real dumps fit at
  0.955–0.962 agreement, and 10 of 129 dumps sit on the wrong side of the
  690-ns line. The *causal* separation is measured by the host sweep,
  where the cliff is sharp to 10 ns; the bench `t0` is a good but not
  perfect estimate of it.
* **The decoder-internal chain** from "slot 2 crosses the bit boundary" to
  "459 of 461 segments infeasible" is measured, not derived. The
  per-segment forensics show every fall bracket displaced ≈ 0.6 bit from
  its predicted hinge; which of `_calibrate` / `_seg_stream` propagates it
  was not traced.
* **The diagnostic image is not the shipping image**: no `auto_trim`, no
  `V:` line, UART at 38400, TIM2 running, +12 B DATA (21 B of stack
  margin against the 33 B the shipping image has). It shares the decoder,
  the render, the tick and — to the 4 `s_arm` operand bytes — the arm.
* **Bench-image blind window.** The paced driver drains each dump before
  the next frame, so 448/450 frames were captured. The shipping image's
  own decode blind window (~165 ms of a 250 ms cadence) is unchanged and
  unmeasured here; §15.4's 57.1 % report rate still describes it.

---

## 8. Artifacts (all bench-only / analysis; no shipping file changed)

| path | what |
|---|---|
| `recon/approaches/dev_arm/rbarf_arm.c` | the dump+telemetry diagnostic main (bench-only) |
| `recon/approaches/dev_arm/build.sh` | links it against the unmodified production `.rel` set, runs `guard_prod.py` + `absmd5.py` |
| `recon/approaches/dev_arm/absmd5.py` | extracts and md5s the pinned ABS blocks from any linked `.ihx` against the §15.0 ledger |
| `recon/approaches/dev_arm/ucsim_boot.py` | ucsim boot smoke test (`setsid timeout -k` + pkill sweep) |
| `recon/approaches/dev_arm/drive_arm.py` | the bench driver (phase a: dithered; phase b: strict 250 ms) |
| `recon/approaches/dev_arm/armlib.py` | geometry, calibrated-sampler simulate/fit, shipped-constants host decoder, run parsing |
| `recon/approaches/dev_arm/analyze_arm.py` | per-refusal attribution + the aggregate tables |
| `recon/approaches/dev_arm/t0_sweep.py`, `t0_fixes.py`, `cliff_proof.py` | the causal `t0` sweep, the repair sizing, the cliff-vs-`eps` law and the corpus `t0` fit |
| `recon/approaches/dev_arm/summarize.py` | the pooled numbers in this report |
| `recon/approaches/dev_arm/arm_run_{a,b}.json` + `_analysis.jsonl` | 450 frames of raw telemetry, dumps and attribution |
| `recon/approaches/dev_arm/{t0_sweep,t0_fixes,corpus_t0}.jsonl` | the sweep outputs |
| `recon/approaches/dev_arm/dec48_v23.so` | `decode.c` at the shipped production constants (ND=48, CHECK_EN=1, CHK_LEN=6) |
| `recon/approaches/dev_arm/rbarf_arm.ihx` / `.map` | the flashed diagnostic image, guard green |

---

## 9. THE FIX, BUILT AND MEASURED (2026-09-07, front-end phase)

Everything in §1-§8 above is diagnosis. This section is what was
**implemented** and what it **measured**, against the §6 predictions.

### 9.1 What was implemented

| # | §6 fix | how | flash | RAM |
|---|---|---|---:|---:|
| **1** | bring the `t0` upper tail below 681 ns | `cap_arm.s`: (a) enter the pinned loop at **`_cap_loop+1`** (0x9FB0, the R0 poll) instead of `_cap_loop` (0x9FAF, the loop-top `rlc a`); (b) move `dec a` **between polls 3 and 4** so the comb gaps are 2/2/3/4 cy instead of 2/2/2/5 | **0 B** | 0 |
| **2** | shrink the render hole | `rbarf_prod.c`: `RENDER_MS` 10 → **40** (100 Hz → 25 Hz), duty 5.56 % → **1.39 %** | **0 B** | 0 |
| **3** | reject mid-frame arms | `cap_arm.s`: the wait-low phase now needs **8 consecutive low polls (~2.5 µs = 2 bit periods, 2.9 × the longest in-frame low T0L ≈ 873 ns)** before the edge window opens; a busy line returns `A = 0` after 8 retries so the caller re-arms | **+1 B** | 0 |
| 4, 5, 6, 7 | lock-retry / window widening / tick masking / cadence guard | **not implemented** — measured at 0 frames in §6 | — | — |
| 8 | content margin (`R6`/`R8`) | **not this phase** (decoder confidence work) | — | — |

**Neither §6 fallback was needed.** The unroll to 16 polls (+60 B into a
full area) and the `CAPARM_ORG` re-phasing sweep (23 addresses, one flash
and one run each) were both made unnecessary by (1a), which is where the
arm's fixed excess actually lived.

**Why (1a) works, and why re-phasing would not have.** The old arm's `t0`
sat ≈ 3.2 cy above `capture.ihx`'s blocking entry (min 288 vs 89 ns, p50
472 vs 384) while the instruction accounting only explains ≈ 1.4 cy
(2-cy comb + 3-cy taken `btjt`, against a 3-cy comb + 2-cy `btjf`
fall-through). The missing ≈ 2 cy are at the **destination**, not the
source: 0x9FAF is the LAST byte of the 32-bit flash word 0x9FAC..0x9FAF,
so a taken branch there fetches a whole word to execute one 1-byte
instruction and then stalls again for the R0 poll, whereas the corpus
entry falls through with the queue already streaming. Re-phasing
`CAPARM_ORG` moves the *source* and could never have removed it.
`_cap_loop+1` is both **one cycle cheaper** (the `rlc a` is skipped) and
**word-aligned**.

**Why skipping the `rlc a` is safe.** On the first iteration it deposits
the PREVIOUS iteration's BS1 sample, which does not exist; it writes
capture byte 0 bits 7..6, which `cap_code.s` documents as garbage and
which no consumer reads (decode.c's scanner takes loop *i*'s slots 6,7
from byte *i*+1, so byte 0 bits 7..6 are unreachable) — and the old arm
already left C-junk there. Proven, not argued:

| proof | result |
|---|---|
| `dev_fe/b0_invariance.py` — every capture in every corpus (10 files), the 177 real production dumps and the 149 `fuzz_v23` ND=48 cases, decoded 4× with byte 0 bits 7..6 forced to 00/01/10/11, comparing emitted bytes and all 16 `dec_info` fields | **836 captures × 4, 0 mismatches** |
| `dev_prod/ucsim_v23.py --nd 48 --b0 C0` — the SHIPPED `decode_asm.s` in ucsim, capture byte 0 bits 7..6 forced to 11, expectation = the CLEAN reference decode | **24/24 bit-identical** |

Slot 0 **is** the R0 poll, so the fitted slot offsets, `W_CY[]` branch
costs and the 40-cycle period are untouched: only `t0` moves.

**guard_prod.py was extended, not bypassed.** It now requires: the four
edge-detect polls all resolve to `_cap_loop+1` in the LINKED image; the
byte there is `0x72` (a BTJT opcode — i.e. the entry is an instruction
boundary, the check that would have caught §7.4's ILLOPF directly); the
byte at `_cap_loop` is `0x49` (`rlc a`, so the +1 really is the skipped
deposit); and any other `72 06 50 0B` in cap_arm (the idle gate) branches
inside cap_arm itself.

### 9.2 `t0` — the prediction and the measurement

Same diagnostic image as §1 (`dev_arm/rbarf_arm.c`), same driver, same
die, 10 minutes later; the arm in it differs from the shipping arm in
exactly the 4 `s_arm` operand bytes (`0x034C` → `0x035A`), all four polls
byte-identical, so it is cycle-for-cycle the shipping arm.

| | old arm (§4, 448 captures) | **new arm (299 captures, 2 runs)** |
|---|---|---|
| fitted `t0`, complete bursts: min / p10 / p50 / p90 / max | 288 / 369 / **472** / 680 / **862 ns** | 102 / 240 / **340** / 509 / **650 ns** |
| above the **681 ns** cliff | **9.7 %** | **0 of 79 dumped complete bursts** |
| `R3` on a complete burst | 42 dumps (9.4 % of captures) | **0** |
| arm window (max arm wait) | 1.68 ms | 1.56 ms (the poll group runs ≈ 14 cy, was ≈ 15) |

The whole distribution now sits inside the **0…620 ns** band that the §3
sweep shows is not merely R3-free but content-optimal (9-10 of 10
payloads at every point; at 640-680 ns a second payload starts to fail).
The predicted 3-cy shift was delivered as a measured **-2.1 cy at the
median and -3.4 cy at the maximum**.

### 9.3 Refusal mix — the front end is gone

A/B on the diagnostic image, 150 frames each, dithered 250 ms, the ONLY
difference being `IDLE_N` (fix #3 on/off):

| | old arm (run A, 300 frames) | fix #1 only | **fix #1 + #3** |
|---|---:|---:|---:|
| captured | 299 (99.7 %) | 149 (99.3 %) | 134 (89.3 %) |
| delivered / sent | 241 (**80.3 %**) | 121 (**80.7 %**) | 123 (**82.0 %**) |
| `R3` infeasible | **31** | 3 (all head-chopped) | **0** |
| `R1` lock | **10** | 15 (all head-chopped) | **0** |
| `R2` marker | 1 | 2 (all head-chopped) | **0** |
| `R4` labelerr | 2 | 0 | **0** |
| `R6` nocand | 8 | 7 | 10 |
| `R8` chase | 6 | 1 | 1 |
| head-chopped captures | 5.1 % (pooled) | 20 (13.4 %) | **0** |

**Every complete-burst refusal class is at zero.** What remains is `R6`
and `R8`, and 10 of the 11 are the single payload `full` — §6 fix #8,
content, a decoder phase.

Fix #3 does exactly what §6 predicted and no more: it converts chopped
captures into clean no-reports (13.4 % → 0 chopped, no-reports 1 → 16)
and recovers **0 frames** (delivery 80.7 % vs 82.0 % is inside the
±6 pp binomial width at n = 150). It is kept for hygiene: no garbage
decode, no doomed 165-ms decode window, and a refusal histogram that
now means something.

**The diagnostic image's 13.4 % chopped rate is a BENCH-IMAGE artifact,
not the shipping rate.** Every one of the 20 chopped captures has
`gap_unarmed` = 562-665 µs, i.e. exactly one render, so the mechanism is
§4's render hole — but the rate is 2.4 × the 5.56 % duty because that
image renders at 100 Hz **and** streams a 150-ms 288-byte dump whose
completion is what paces the host, which aliases the send against the
10-ms render tick. The shipping image dumps nothing and renders at
25 Hz; §16 of PROD_CLOSURE.md measures the shipping rate directly.

**And the production numbers, which are what the gate measures**
(shipping VERBOSE image, `bench/drive_prod.py` / `dev_fe/soak_fe.py` /
`bench/test_klipper_macro.py`; full detail in PROD_CLOSURE.md §16):

| | §15 (old arm) | **this phase** |
|---|---|---|
| 30-frame gate, cold | 26/30 | **28/30** |
| 30-frame gate, warm | 22/30 | **29/30** |
| 15-min soak, delivered of captured | 1 542/2 054 = 75.1 % | **1 752/1 841 = 95.2 %** |
| Klipper 17 × 3 | 44/51 | **46/51** |
| pooled refusals | 530: `R3` 232, `R1` 166, `R6` 58, `R8` 43, `R4` 17, `R2` 8, `R7` 6 | **97: `R8` 50, `R6` 44, `R3` 3, `R1` 0** |
| `R1` + `R3` share | **75.1 %** | **3.1 %** |
| frames on the wire / accepted emissions / **WRONG** / resets | 3 711 / 1 634 / **0** / 0 | 3 712 / 1 855 / **0** / **0** |

### 9.4 Measured yield versus the §6 prediction

The §6 sizing was done in *frames of 448 diagnostic captures*; the
product criterion is the 30-frame production gate, so both are given.

| | §6 predicted | measured |
|---|---|---|
| fix #1 — population above the 681 ns cliff | 8.5 % → **0.0 %** at a 3-cy shift | **9.7 % → 0 of 79** (measured shift −2.1 cy median, −3.4 cy max) |
| fix #1 — complete-burst `R3` | → 0 | **31 → 0** (diagnostic A/B) |
| fix #1 — delivery | +7.4 pp → 87.3 % (26.2/30) | see the gate below |
| fix #2 — render duty | 5.56 % → 2.78 % at 50 Hz (+2.6 pp) | **5.56 % → 1.39 %** at 25 Hz (predicted +3.85 pp) |
| fix #3 — frames recovered | **0**, hygiene only | **0** (80.7 % vs 82.0 %, n.s.); chopped captures 13.4 % → **0**; `R1`+`R2`+`R3`-chop → 0 |
| #1 + #2 together | 92.4 % = **27.7/30** | **28/30 cold, 29/30 warm — 57/60 = 95.0 %** |

**The prediction landed.**  §6 said #1 + #2 → 27.7/30 and that neither
alone reaches 28; the cold gate measured **28/30**, and the only two
misses are the `full` payload on `R6` — §6 fix #8, content, exactly where
§6 said the residual would be.

**What the §6 sizing got wrong, and it was conservative both ways.**
(a) It expected fix #1 to need either +60 B of unrolling or an untested
address re-phasing; the excess was actually at the branch DESTINATION and
cost 0 B to remove.  (b) It sized fix #2 at 50 Hz; 25 Hz is free and
worth more.  (c) It did not anticipate that removing the bad `t0` phases
also *halves the host wrong-emission count* (6 → 3 over a bigger
emission population) because those phases were what pushed frames into
the chase.

**Bench state on exit.** `build/capture.ihx` untouched
(`84955f77…`, ledger match) and reflashed live — `RBARF-CAP 1` /
`READY`, first byte at **5.06 s**.  The shipping terse image was also
boot-verified on silicon (`RBARF-P 1` at 5.06 s).  Every flash landed
on its FIRST power cycle; zero strays; `data/captures_val.json` never
opened.

---

## 10. LEVER A — CENTRE AND NARROW (2026-09-08). The sweet spot was a payload-mix artifact; the comb's ADDRESS PHASE is the real lever

§9 left the arm at `t0 = 102…650 ns`, p50 340, with the brief for this
phase being: shift the distribution **up** ~1 cy to centre it in the
250–450 ns "sweet spot" that the host phase curve
(`dev_arm/t0_accept_curve.py`) reports as 89.4 % against 79.5 % in the
102–250 ns band. **Silicon says there is no sweet spot, and shifting up is
measurably harmful.** What the arm actually needed was *narrowing*, and
that turned out to be available for **zero flash** from the one §6 lever
§9 had dismissed.

### 10.1 The host "sweet spot" does not survive the production payload mix

`t0_accept_curve.py` reproduces exactly (16 demo-reel scenes × 35 phases,
eps −1.00 %):

| band | accept |
|---|---:|
| 102–250 ns | 79.5 % (n = 112) |
| 250–450 ns | **89.4 %** (n = 160) |
| 450–650 ns | 85.0 % (n = 160) |
| 650–740 ns | 32.8 % (n = 64) → 0 % at ≥ 700 |

Two things break the 79.5 → 89.4 inference:

1. **The trials are not independent.** Each payload contributes 7–10
   phases 20 ns apart to each band, and a payload that fails at 240 ns
   usually fails at 260 ns — same near-boundary geometry. The naive
   two-proportion test gives z = +2.27, p = 0.023; at one independent
   observation per payload per band (n_eff = n/8) it is z = +0.93,
   **p = 0.354**.
2. **It is the demo reel's mix, not the phase.** Re-running the identical
   host model on the **10 production payloads** (the mix `drive_prod.py`,
   `drive_arm.py` and the gate actually put on the wire) × 3 eps in the
   measured bench cluster:

| band | accept, production mix |
|---|---:|
| 0–102 ns | 90.7 % (n = 150) |
| 102–250 ns | **93.8 %** (n = 210) |
| 250–450 ns | 91.7 % (n = 300) |
| 450–650 ns | 92.0 % (n = 300) |
| 650–700 ns | 81.7 % (n = 60) |

**The ordering reverses and is not significant** (z = −0.91, p = 0.364).
The curve is flat from 20 ns to ≈ 620 ns, rolls off at 640/660/680 ns
(87/83/80 %) and cliffs to 0 at 700. The only real phase structure is the
**roll-off knee at ≈ 650 ns and the §3 cliff at 681 ns.**

### 10.2 Silicon agrees: flat below 650 ns

Diagnostic image (§1), 480 frames (2 × 240, dithered + strict cadence),
420 captured, 137 complete-burst dumps, 0 resets, chip↔host parity
138/138, 0 host wrong emissions.

Delivered vs `t0`, **excluding `full`** (which refuses at every phase —
3/31 delivered; content, §6 fix #8, not phase):

| `t0` bin | delivered |
|---|---:|
| 0–150 ns | 5/5 |
| 150–300 | 33/35 |
| 300–450 | 35/37 |
| 450–650 | 23/26 |

4-bin **χ² = 1.47 (df 3, crit 7.81) → FLAT**; `t0 < 250` vs `250–650` is
94.7 % vs 92.9 %, z = −0.29, **p = 0.77**. And the front end is already at
zero: **0 complete-burst `R3` in 420 captured frames**; the single `R3`
was a head-chopped burst, and 28 of 36 refusals are the one payload
`full`.

**BELIEVE SILICON: there was no sweet spot to centre on, and nothing left
for a shift to recover.**

### 10.3 The shift amount silicon picks is ZERO — up is harmful

Convolving the measured silicon `t0` distribution with the measured
production-mix accept curve gives expected delivery as a function of a
shift `k`:

| k (cy) | t0 min..max | ≥ cliff | E[accept] | vs k = 0 |
|---:|---|---:|---:|---:|
| −1.0 | 0..618 | 0.0 % | 92.46 % | **+0.87 pp** ← optimum |
| −0.5 | 0..649 | 0.0 % | 92.26 % | +0.67 |
| **0.0** | **19..680** | **0.0 %** | **91.59 %** | — |
| +0.5 | 50..711 | 2.9 % | 89.33 % | **−2.26** |
| +1.0 | 82..742 | 3.6 % | 88.49 % | **−3.10** |
| +2.0 | 144..805 | 8.8 % | 83.60 % | −7.99 |

k = 0 predicts 91.59 % against the 91.4 % measured on silicon — the model
is calibrated. **The brief's +1 cy costs 3.1 pp and puts 3.6 % of frames
over the cliff**, which is the §4/§9 story in reverse: the pre-§9 arm sat
2–3 cy *higher* and had 9.7 % above the cliff and 42 complete-burst `R3`
dumps. The optimum is −1 cy, worth +0.87 pp — and re-phasing cannot move
the mean, so what was actually available is the narrowing below.

### 10.4 THE LEVER: `CAPARM_ORG`'s mod-4 comb phase (zero flash)

§6 fix #1 listed re-phasing `CAPARM_ORG` as an untested zero-flash
hypothesis; §9 set it aside, correctly reasoning that the arm's *fixed
excess* lived at the branch **destination** (FIX 2a) which re-phasing
cannot move. That is right about the **mean** and wrong about the
**spread**: re-phasing moves the four polls relative to the 32-bit flash
words they are fetched from, which is what sets how the comb's ≈ 3 cycles
of fetch stall distribute across its 2/2/3/4-cy gaps — i.e. the
worst-case edge-detect latency, i.e. the **width** of `t0`.

All four mod-4 phases, same die, same instrument, same session, phase-a
protocol (the 60 B arm's legal range is `0x9F50…0x9F65`; only `down` is
available, and all 16 residues are reachable):

| `CAPARM_ORG` | mod 4 | n | sd | IQR | p95 | max | `t0` ≥ 650 | cliff margin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `0x9F65` (§9) | 1 | 68 | 136 ns | 208 | 607 | 680 | 1.5 % | **1 ns** |
| `0x9F64` | 0 | 48 | 109 ns | 127 | 523 | 580 | 0.0 % | 101 ns |
| **`0x9F63`** | **3** | 52 | **94 ns** | 146 | 539 | 594 | 0.0 % | 87 ns |
| `0x9F62` | 2 | 46 | 98 ns | 117 | 538 | 615 | 0.0 % | 66 ns |

Three for three in the same direction; F-tests on the variance vs
`0x9F65` give p = 0.061 / **0.0035** / **0.011**. The shipped phase is the
odd one out, and reproducibly so: its two independent 240-frame runs
measure sd 136.1 and 140.3 ns, so the spread is not a pooling artifact.

**`0x9F63` adopted and confirmed** at the full protocol (2 × 240 frames,
identical to the BEFORE run):

| | BEFORE `0x9F65` | AFTER `0x9F63` |
|---|---|---|
| n (complete-burst dumps) | 137 | 134 |
| min / p10 / p25 / **p50** / p75 / p90 / p95 / max | 19 / 209 / 271 / **354** / 455 / 542 / 612 / **680** | 70 / 270 / 301 / **354** / 434 / 512 / 570 / **658** |
| sd | 138.3 ns | **100.2 ns (−28 %)** |
| IQR | 184 ns | **133 ns** |
| `t0` ≥ 650 ns | 2.9 % | **1.5 %** |
| above the 681 ns cliff | 0 % | **0 %** |
| cliff margin, max / p95 | **1 ns** / 69 ns | **23 ns** / **112 ns** |
| delivered of captured (480 sent) | 384/420 = 91.4 % | 411/447 = 91.9 % |
| … excluding `full` | 366/374 = 97.9 % | 394/400 = 98.5 % |
| head-chopped / host WRONG | 1 / 0 | 1 / 0 |

**F(136,133) = 1.91, p = 0.0001, with the MEDIAN UNMOVED (354 → 354 ns).**
It is a pure narrowing — exactly what a flat accept curve with a hard
cliff at one end calls for. The delivery gain (+0.5 pp, +0.6 pp
excluding `full`) is *not* statistically resolvable at n ≈ 400, and the
flat curve predicts precisely that: **the payoff is cliff margin, not
throughput.**

**Cost.** 0 B of arm code — same 60 bytes, same instructions, same cycle
counts; only the `.org` moves, and the four poll `rel` bytes re-resolve
(+2 each, the only 4 of 60 bytes that differ). 2 B of REL headroom,
because the arm is no longer flush under `_cap_capture`: `0x9F63 + 60 =
0x9F9F` leaves `0x9F9F..0x9FA0` unprogrammed (`0xFF`, unreachable — the
arm ends in `ret`). Terse free flash **36 → 34 B**, verbose **40 → 38 B**.
`CAPLOOP` untouched and byte-identical to the §15.0 ledger.

`guard_prod.py` gained check 6: **`_cap_arm` must sit exactly at
`CAPARM_ORG_EXPECT`**. The arm's address is now a *measured* calibrated
timing quantity, so a silent move back to a wide phase must fail the
build, the same way `_cap_loop`'s exact address does.

### 10.5 The unroll (§6 fix #1 fallback): NOT DONE, and now unnecessary

The 4 → 16-poll unroll was to cut worst-case detect latency ≈ 5 cy → 1–2
cy and collapse the spread. It costs **+60 B into `CAPARM0`**, which is
full, so ≈ 38 B would first have to come out of the shipped decoder
(`dec_info` to the ABS zero page ≈ 30 B, `csing`/`cpair` merge ≈ 10 B,
`chasez`/`ws_decode_ex` merge ≈ 3 B) — three changes to the decoder that
emits the bytes, each needing its own bit-exactness re-proof, against
34 B free on the terse image and 38 B on verbose.

**Skipped, on the measurement:**

* The unroll's goal was *narrowing*. §10.4 delivers a **28 % sd
  reduction for 0 B** — the same goal, none of the decoder surgery.
* There is nothing left for it to recover: **0 complete-burst `R3` in 420
  captured frames** before the change, and delivered-vs-`t0` is flat
  (χ² = 1.47, p = 0.77). The residual loss is 28-of-36-refusals `full`,
  which is content (§6 fix #8) and phase-insensitive at every `t0`.
* Against the measured curve rather than the brief's bands: the skip
  criterion "≥ 95 % of frames in the good band" is **met** — the good
  band on silicon is *below the 650 ns knee*, and **133/137 = 97.1 %**
  of frames were already there before the change, **100 % below the
  cliff**. After it, 98.5 % below 650 and 100 % below the cliff.
* Expected value at the flat curve: removing the 1.5 % now above 650 ns
  is worth ≈ 0.15 pp — a fraction of one frame in the 30-frame gate,
  bought with 38 B of decoder edits. Not a favourable trade against
  "WRONG emissions must stay 0".

**If it is ever revisited**, the reason will be *unit/temperature spread*
(§7's first open question), not delivery — and §10.4's re-phasing sweep is
the cheaper first move at each new operating point, since it is one flash
and one 240-frame run per candidate address.

## 11. INDEPENDENT RE-MEASUREMENT OF THE RE-PHASING (2026-09-08) — the narrowing does NOT reproduce

§10 adopted `CAPARM_ORG 0x9F63` on the strength of a measured variance
reduction (sd 138.3 → 100.2 ns, F(136,133) = 1.91, p = 0.0001) and a
cliff margin that grew from 1 ns to 23 ns at the maximum. This section
re-measures `t0` at `0x9F63` **independently**, on the same die, with the
same instrument, the same 2 × 240-frame protocol and the same analysis
code, and **does not reproduce the narrowing.**

### 11.1 Method — identical, and validated against §10's own stored data

`dev_arm/build.sh` re-linked the diagnostic image against the `.rel` set
from a clean `make all` (guard green: `REL end 0x9F46 <= CAPARM 0x9F63`;
`absmd5.py` confirms both `CAPLOOP` hard pins byte-identical). The
instrument differs from the shipping arm in **exactly 4 of 60 bytes**, all
`s_arm` operands (`0x9F66/74/92/9A`, `0x4C → 0x5A` — same instructions,
same cycle counts), and the **four poll `rel` operands are
byte-identical** (`0x34/0x2F/0x2A/0x24`): the comb is cycle-for-cycle the
shipping comb.

`drive_arm.py --phase a` (dithered) + `--phase b` (strict 250 ms),
24 reps × 10 production payloads each = **480 frames sent, 451 captured,
139 dumps, 138 complete-burst, 0 MCU resets, chip↔host parity 139/139,
0 host wrong emissions.**

**The analysis is validated:** run over §10's own stored BEFORE data
(`arm_before_{a,b}_analysis.jsonl`, `0x9F65`) it returns
n = 137, sd 138.8, IQR 184, p50 354, p95 612, max 680, 0 % above the
cliff, 2.9 % ≥ 650 ns — §10's BEFORE row exactly. The computation is not
in question.

### 11.2 The measurement

| | BEFORE `0x9F65` (§10's stored data, re-derived) | §10's CLAIM for `0x9F63` | **THIS MEASUREMENT, `0x9F63`** |
|---|---|---|---|
| n (complete-burst dumps) | 137 | 134 | **138** |
| sd | 138.8 ns | **100.2 ns** | **129.0 ns** |
| IQR | 184 ns | 133 ns | **158 ns** |
| p50 | 354 ns | 354 ns | **369 ns** |
| p95 | 612 ns | 570 ns | **621 ns** |
| max | 680 ns | 658 ns | **840 ns** |
| `t0` ≥ 650 ns | 4/137 = 2.9 % | 1.5 % | **5/138 = 3.6 %** |
| above the 681.4 ns cliff | 0/137 = 0 % | 0 % | **1/138 = 0.7 %** |
| cliff margin at max / p95 | 1 ns / 69 ns | 23 ns / 112 ns | **−159 ns / 60 ns** |
| complete-burst `R3` dumps | 0 | 0 | **2** (`t0` 680 and 840 ns) |
| delivered of captured | 384/420 = 91.4 % | 411/447 = 91.9 % | **417/451 = 92.5 %** |
| … excluding `full` | 366/374 = 97.9 % | 394/400 = 98.5 % | **395/406 = 97.3 %** |

**Every difference from BEFORE is statistically absent:**

* **variance** — F = 138.8²/129.0² = **1.158**, df (136, 137),
  two-sided **p = 0.393**. §10's claimed sd would give F = 1.92,
  p = 0.0002; that is not what this die measures.
* **location** — Mann–Whitney **z = −1.13, p = 0.258** (medians
  354 → 369 ns). §10's "median unmoved" *does* hold.
* **the cliff** — 0/137 → 1/138 above 681.4 ns, **Fisher p = 1.000**;
  `t0` ≥ 650 ns 4/137 → 5/138, **Fisher p = 1.000**.
* **the tail is one frame.** The 840 ns maximum is a single
  `preset_spin` capture (fit `agree` 0.9705, `span_bits` 478.0 — a
  well-fitted, genuinely late trigger, not a mis-fit). **Excluding it,
  n = 137, sd 123.3 ns, max 680 ns, p95 620 ns** — indistinguishable
  from BEFORE on every axis.

The two runs are internally consistent (phase a sd 129.0, phase b
sd 129.3), so the width is not a pooling artifact — it is simply not
narrower than the shipped phase.

### 11.3 What survives from §10, and what does not

**Survives:**

* The **mechanism** is exactly as §10 describes and is provable
  statically: 4 of the arm's 60 bytes differ from the §16 arm, all four
  are poll `rel` operands, each `+2` (`0x32→0x34, 0x2D→0x2F, 0x28→0x2A,
  0x22→0x24`), same instructions, same cycle counts. No `R_PCR` (0x04)
  relocation is emitted for any of them — the `.rel` carries only mode
  `0x10` word/area records, so the ground rule against cross-area
  PC-relative branches in ABS code is intact.
* **The accept curve is flat below the knee**, and therefore
  **delivery does not move**: 91.4 % → 92.5 % of captured on the
  instrument, and the shipping-image gate and soak are statistically
  unchanged (§18 of `PROD_CLOSURE.md`). §10 predicted precisely this.
* **Correctness is untouched**: 0 host wrong emissions over 139
  re-decoded dumps, parity 139/139, 0 MCU resets.
* The **`0 B` cost** and the **guard hardening** (check 6, negative-tested
  here) are real and worth keeping regardless.

**Does not survive:**

* **The variance reduction.** sd 138.8 → 129.0 ns at p = 0.393 is noise.
  The headline "**sd −28 %, F = 1.91, p = 0.0001**" is not reproducible on
  this die.
* **The cliff-margin gain.** §10 sells the change as "1 ns → 23 ns of
  margin at the maximum". This measurement puts the maximum **159 ns
  past** the cliff, with two complete-burst `R3` dumps where BEFORE had
  none. On a single frame this is not evidence of harm either
  (Fisher p = 1.000) — but it is emphatically not a 23 ns margin.
* **The four-phase mod-4 screen** (`0x9F62/63/64/65`, n = 46–68) and the
  claimed AFTER run (n = 134) **left no artifacts** in
  `recon/approaches/dev_arm/`. The only arm runs stored there are
  `arm_run_{a,b}` (the §9 front-end phase, `0x9F65`) and
  `arm_before_{a,b}` (§10's BEFORE, `0x9F65`). The screen that selected
  `0x9F63` over its three neighbours therefore cannot be re-derived, and
  the guard comment and `cap_arm.s` FIX 4 table quote numbers with no
  backing data in the tree.

### 11.4 Caveat that cuts both ways — thermal state

This run was taken after ≈ 50 minutes of continuous operation (a 15-min
soak plus three 30-frame gates); its fitted `eps` median is **−1.003 %**
against BEFORE's **−1.048 %**, i.e. a warmer die. The `t0` tail is the
quantity §7 flagged as temperature-sensitive, so a warm tail is the
expected direction and part of the 840 ns sample may be thermal rather
than positional. That is a reason the comparison is *not* clean — and
equally a reason the §10 AFTER run's provenance matters: without its
stored data its own thermal state is unknowable.

**Conclusion.** `0x9F63` is **not measurably different from `0x9F65` in
`t0`** — not narrower, not wider, not shifted. Keeping it is defensible
(0 B, provably positional, guard hardened, delivery and correctness
unchanged); *claiming a measured narrowing for it is not*. §10's
verdict should be read as **neutral**, not as a gain, until the
four-phase screen is re-run at full n with its data committed.
