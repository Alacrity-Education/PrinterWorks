# RBARF production closure — independent verification & bench proof

> **Relocation note (housekeeping 2026-09-08).** The bench-only diagnostic
> mains named in §7.7 — `rbarf_dbg.c`, `rbarf_bc.c`, `rbarf_bc_gate.c`,
> `crumb.s` — and the superseded `rbarf_v21.c` now live in
> `../archive/firmware-variants/`. None was in a shipping target. Every
> artifact path in the tables below is unchanged except the scratch dirs
> moved to `../archive/`, listed in `../archive/README.md`.

**Date:** 2026-09-06 · **Unit:** STM8S001J3 on the [rbarf-test-bench] rig ·
**Images under test:** `build/rbarf_prod.ihx`, `build/rbarf_prod_verbose.ihx`
(clean rebuild from `src/`, SDCC 4.6.0)

Everything below was **re-measured in this session**. No number is carried
over from the closure report; where a claim was reproduced exactly it is
marked ✅, where it needed qualification the qualification is stated.

**VERDICT (updated 2026-09-06, later session): the ILLOPF blocker is FIXED.**
The static artifact is sound and every closure claim about it reproduces
byte-exactly. The firmware *had* taken an **illegal-opcode reset roughly
every 6 decodes** on silicon — **root-caused to an sdld PC-relative
relocation bug in `cap_arm.s`'s edge-detect branch (NOT the decoder) and
fixed**; a 240-frame bench soak now runs **0 resets, 0 wrong emissions**.
Full root cause, fix and re-proof in
[§7](#7-blocker-illegal-opcode-reset-every-6-decodes). One residual,
pre-existing and *not* caused by the fix: raw delivery rate on silicon
(27 %) trails the synthetic model (89–96 %) — a decode-margin matter for
separate follow-up ([§7.6](#76-bench-soak--the-crash-is-gone)), not a
crash regression.

**RE-GATE (2026-09-06, later session) — [§9](#9-re-gate-applied-rate-ceiling-and-klipper-end-to-end):**
590 frames, **0 resets and 0 wrong emissions**, `no-report` 9/30 → **0/30**;
the applied-frame-rate ceiling is measured for the first time at **5.6 Hz /
180 ms** on the shipping image. The gate's delivery criterion is still
missed (18/30 vs ≥26/30). The Klipper macro ran end to end for the first
time and is **bytes-correct but undecodable**: the WS2812 pad byte is fatal,
and the reason is now proven — **every surplus byte on the wire inflates the
decoder's fitted clock by ≈1.6 % (1/59), leading or trailing alike**, and
one byte is enough to force a refusal ([§9.4](#94-pad-byte-verdict-fatal-and-it-is-not-about-the-trailer)).
Verdict: **NO-GO**, with the blocker moved from stability to (1) the
one-byte Klipper defect and (2) low-entropy decode margin.

**INDEPENDENT RE-GATE (2026-09-08) — [§18](#18-independent-re-gate--caparm_org-0x9f63-2026-09-08--go-on-the-image-17s-t0-claim-not-confirmed): GO on the image, lever A's benefit NOT CONFIRMED.**
Re-measured from a clean tree on the same die: ledger byte-exact twice,
`capture.ihx` unchanged, guards green (check 6 negative-tested), `CAPLOOP`
byte-identical, 4/1 polls resolved, no `R_PCR` relocation. **WRONG
EMISSIONS ZERO on every axis** — 84 gate + 1 745 soak + 47 Klipper
emissions, 139/139 chip↔host parity, 0 resets in ~5 000 frames; host grid
0.0126 % (≤ 0.0227 %, target ≤ 0.2 %) with **0 of 13 828** in the shipped
geometry inside the trim band. Gate 27/30 cold, 29/30 cold-2, 28/30 warm
(pooled 84/90); soak 3 601 frames, 1 745 delivered, eps sd **0.0211 pp**,
1 745/1 745 in band; Klipper **47/51, 0 catastrophic**. **But `t0` does not
narrow** (sd 138.8 → 129.0 ns, p = 0.393; max past the cliff), so lever A's
predicted gain did not materialise — see §18.7 and `ARM_INVESTIGATION.md` §11.

---

## 1. Flash ledger — verified byte-exact

`make clean && make all rbarf-prod`, then occupancy computed independently
from the Intel-HEX records (not from the map):

| Image | Used | Free | Free-space breakdown |
|---|---:|---:|---|
| `rbarf_prod.ihx` | **8052 / 8192** | **140** | 113 B @ `0x9EF5-0x9F65` + 15 B @ `0x9FF1-0x9FFF` + 12 B @ `0x8058-0x8063` |
| `rbarf_prod_verbose.ihx` | **8133 / 8192** | **59** | 32 B @ `0x9F46-0x9F65` + 15 B tail + 12 B vector-gap |

✅ Exact match to the closure report, including the three-way split.

> **Reconciliation note.** `guard_prod.py` prints `flash free 128` / `47`.
> That is not a disagreement: the guard counts only the two REL-side gaps and
> ignores the 12 B of vector-gap slack, which is real but only usable by ABS
> code placed inside the `0x8004-0x8063` window. 128 + 12 = 140. Both numbers
> are correct against their own definition; quote 140 for "free flash" and 128
> for "free contiguous REL headroom".

**Goal ≥ 256 B free: NOT met** (140 B, short by 116 B). ✅ as reported.

**Reproducibility.** After `make clean`, all three images rebuilt
**byte-identical** to the pre-clean artifacts — including
`build/capture.ihx` (`md5 84955f77…`), the calibrated baseline. ✅

---

## 2. Address-phase pinning — verified, statically and live

| Symbol | Address | mod 16 | Required | |
|---|---|---|---|---|
| `_cap_capture` | `0x9FA1` | `0x1` | `0x8111` → `0x1` | ✅ |
| `_cap_loop` | `0x9FAF` | `0xF` | `0x811F` → `0xF` | ✅ |
| `_cap_arm` | `0x9F66` | — | flush below CAPLOOP | ✅ |
| `sot` (VGAP anchor) | `0x8004` | — | inside `0x8004-0x8063` | ✅ |

**Byte-level proof against the calibrated image.** The 62-byte sampling loop
was extracted from both linked images and compared:

```
capture.ihx  @0x811F +62  497206500b019d…497206500b019d26c2
rbarf_prod   @0x9FAF +62  497206500b019d…497206500b019d26c2   IDENTICAL
```

Both at phase `0xF`. The 14-byte prologue differs **only** in the `ldw y,#N`
loop-count immediate (640 in `capture.ihx`, 256 in the production
`_cap_capture` entry; production actually enters via `_cap_arm` with Y=288).
The epilogue differs as designed (`rim; ld a,#1; ret` vs `ret`). ✅

**Live confirmation.** On the bench the decoder measured eps
**−1.02 … −1.09 %** at factory trim — this unit's documented −1.07 %. Had the
phase been broken the loop would run the documented ~37 cy and eps would read
**≈ +6.9 %**. The fitted 40-cycle model is confirmed *in the shipping link*,
not merely asserted.

---

## 3. Link guard — negative-tested with real relinks

The closure report negative-tested `guard_prod.py` with doctored map files. I
re-tested it the stronger way: **actually breaking the build** in a scratch
copy of the tree and relinking. All seven cases fail the guard *and* abort
`make` (`Error 1`); the restored copy then relinks byte-identical to the
project build.

| # | Injected defect | Guard output |
|---|---|---|
| A | `caploop.s .org 0x9FA1 → 0x9FA0` | both PHASE checks + CAPARM/CAPLOOP OVERLAP |
| B | `.org 0x9FA5` (phase broken, no overlap) | both PHASE checks, **in isolation** |
| C | 1-byte pad before `_cap_loop` only | `PHASE: _cap_loop 0x9FB0` alone — the two phase checks are genuinely independent |
| D | +400 B const in `rbarf_prod.c` | `OVERLAP: CODE ends 0xA087 > CAPARM0 0x9F66` |
| E | 16-byte pad inside the VGAP block | `VGAP 0x8014..0x8077 outside the TRAP..IRQ22 window` |
| F | `--data-loc 0x80` | `OVERLAP: REL DATA 0x80 below DZP end 0x100` |
| G | `.globl sot` removed | `VGAP present but 'sot' anchor symbol missing` |
| — | **positive control** (all restored) | `prod guard OK … phase 0xF; flash free 128 B` |

✅ The guard is real, and the VGAP-window check that was previously dead is
now genuinely armed.

---

## 4. Bit-exactness — all harnesses re-run from the final sources

### 4.1 Host parity (`recon/approaches/dev_fw/parity_host.py`)

```
captures_v21.json           54/ 54 bit-identical (bytes+path+cause+counters)
captures_v21_val.json       36/ 36 bit-identical
captures_trim.json          96/ 96 bit-identical (legacy v2.0, CHECK_EN=0)
HOST PARITY: PASS
```

**186/186** ✅ — `decode.c` (gcc/ctypes) == `recon/approaches/embedded_v2.py`
on emitted bytes, path label, refusal cause and all nine counters.
`data/captures_val.json` is never opened (verified by reading the source).

### 4.2 ucsim, production decoder image (`ucsim_bitexact.py --asmdec --scan asm`)

```
captures_v21.json   24/24 bit-identical      captures_trim.json  12/12
decode ticks: min 1 766 842  max 2 084 050  mean 1 969 225  (36 decodes, ND16)
TASK 1 UCSIM VALIDATION: PASS
```

**36/36** ✅ — the SDCC-built `decode_asm.s` image, executed
instruction-by-instruction, agrees with the Python reference.

### 4.3 ucsim at production geometry (`dev_prod/smoke48.py`, ND_DATA=48)

**10/10** ✅ — 8 `direct` deliveries across eps ∈ {0, −1.072, +1.274, −1, +1,
−2.248, −2.5 %} and varied phases/payloads, plus 2 corner refusals
(`refuse_emitgate` at ±7.5 %), all bit-identical on bytes + path + cause +
counters, with the delivered payloads checked against ground truth.

> **Simulator hygiene.** Every `ucsim_stm8` invocation ran under
> `setsid timeout -k`, with an explicit `pkill` sweep and a `pgrep` check after
> each run. **Zero stray simulators** at every checkpoint and at session end.

---

## 5. Animation equivalence — re-run, and its coverage audited

`recon/approaches/dev_prod/anim_eq/run_eq.sh` (original `../anim.c` vs
refactored `app/anim.c`, identical 48-byte frame + `now_ms`, 24-byte outputs
`memcmp`'d):

```
anim equivalence: 25945920 cases, 0 mismatches -> PASS
--negtest:        25945920 cases, 5764790 mismatches -> FAIL   (harness has teeth)
```

✅ Both figures match the closure report exactly, including the 5 764 790
negative-test detections.

**Coverage audit** (read from `driver.c`, then reconciled arithmetically):

* modes `0x00-0x03` + unknown `0x0A`/`0xFF` + presets `0x04-0x09` — present
* durations {0, 1, 3, 40, 255}; masks {`00`, `80`, `A5`, `FF`} — present
* gamma cfgs {0…5, 255}; 6 sequence shapes incl. **empty, single, plain,
  pauses+dups, full-32-nibble unterminated, dup-heavy**, each padded with LCG
  noise past the terminator — present
* 3 base fills, LCG alt/bg/mask colours, 72 phase points across 3+ cycles plus
  6 u16 wrap/boundary specials — present
* case count reproduces **exactly**: 5 non-seq modes × 5 × 4 × 4 × 7 × 6 × 3 ×
  78 = 3 931 200, plus 7 seq/preset modes × 5 × 4 × **16** × 7 × 6 × 3 × 78 =
  22 014 720 → **25 945 920** ✅

**One qualification on "all 16 feature-bit combos".** The full 16-way sweep of
`flags[6]` runs for mode `0x03` and the presets only; for modes
`0x00`/`0x01`/`0x02`/unknown the sweep is `ft ∈ {0, 5, 10, 15}`. That is not a
gap: in those modes `flags[6]` is not a feature byte at all — it is the
mask-colour G byte (`p[0] = f[6]`), and mask colours are independently
LCG-randomised across every case. The claim is sound where it is meaningful.

---

## 6. Bench proof — 10 production frames × 3 reps, single transmission

Image: **`build/rbarf_prod_verbose.ihx`** (8177 B written at `0x8000`).
Driver: **`bench/drive_prod.py`** (new; the v21 driver speaks the old
`READY`/`DEC:`/`TIM:` protocol and cannot drive this firmware).
Banner `RBARF-P 1` at **5.06 s** after power-on — SWIM quiet window respected.

The ten frames are real 48-byte application payloads (8 base-colour LEDs + 8
flag LEDs), CRC-wrapped with `bench/crc.py build_payload` into 59-byte v2.1
rev2 wire frames: `colors`, `dark` (degenerate all-zero DATA — worst-case
swallowed-0), `full` (all-`FF` — worst-case merged-1), `blink` (mask `A5`),
`fade`, `seq_plain` (`01 23 45 67 FF`), `seq_pause` (pauses + duplicates +
early terminator), `preset_spin` and `preset_rainR` (**host-expanded** preset
equivalents per docs/ANIMATION_PROTOCOL.md), and `rnd` (LCG). Each was put on the wire
**exactly once**.

### 6.1 Result

```
17/30 delivered correct (8 OK + 9 CHASED), 4 refused, 9 no-report,
0 CATASTROPHIC, 0 protocol errors
MCU RESETS observed during the 30-frame run: 3
```

* **0 wrong emissions.** Every `V:` line matched the transmitted 48 DATA bytes
  byte-for-byte — in this run and across every exploratory run today
  (≈200 deliveries in total). **The safety-critical property holds on silicon.**
* **All 9 no-reports are attributable to the 3 resets.** At the run's ~1.75 s
  per frame, each ~5 s reset dead window swallows ~3 frames; 3 × 3 = 9.
  Excluding the reset windows: **17 delivered of 21 frames that reached an
  armed receiver (81 %), with 4 refusals** — consistent with the pre-flight
  synthetic model (89 % at eps ≈ 0, 96 % at factory trim, 0 catastrophic over
  140 model cases).
* **Refusal mix:** `R8 chase`, `R6 nocand`, `R2 marker` ×2. All refusals, never
  a wrong emission — the intended ordering (correct > refusal > catastrophic).

### 6.2 HSITRIMR auto-trim — works exactly as specified

First decode after boot reads **−1.09 %** (factory trim, code 0); `auto_trim`
takes one signed step to code 7; every subsequent decode reads **+0.06 … +0.10 %**
and stays inside the 0.6 % deadband. This reproduces the documented
"settles to code 7, eps +0.03…+0.11 %" behaviour precisely. The isolated
mid-run −1.02/−1.04 % readings are the **first decode after each reset**, where
the converged trim has been lost — a symptom of §5, not of the trim logic.

### 6.3 Timing

| Quantity | Measured |
|---|---|
| Decode window (latency − frame tx − capture − UART transit) | **159.4 – 170.9 ms, mean 168.6 ms** |
| Host latency, frame start → `D:` line complete | 168.0 – 181.6 ms, mean 178.2 ms |
| VERBOSE `V:` line (99 chars @ 9600) | ≈ +103 ms |
| **Blind window, production (terse)** | **≈ 178 ms → arithmetic ceiling ≈ 5.6 Hz** |
| Blind window, VERBOSE bench build | ≈ 280 ms |

The closure report estimated ~190 ms decode and a 4–5 Hz ceiling: slightly
pessimistic, directionally right. ucsim predicted 4.28 M vclks = 268 ms;
silicon ran it in 168.6 ms — **~37 % faster than ucsim's documented counts**
(the capture-pipeline note said ~30 %).

**The applied-frame-rate probe could not be measured.** At every offered rate
(10/5/4/2 Hz) the achieved rate collapsed to ~0.2 frames/s because reset dead
time, not the blind window, dominates. This number is only obtainable once §5
is fixed.

---

## 7. BLOCKER: illegal-opcode reset every ~6 decodes

**The production firmware does not stay running.** Four independent stress
runs, three different builds:

| Build | Decodes | Resets | Mean decodes/reset |
|---|---:|---:|---:|
| `rbarf_prod_verbose.ihx` (shipping) | 144 | 25 | 5.8 |
| diagnostic (RST_SR + canary) | 92 | 13 | 7.1 |
| diagnostic (canary count) | 88 | 11 | 8.0 |
| full-vector-table variant | 90 | 17 | 5.3 |

Each reset costs a ~5 s dead window (the pin-8 SWIM quiet window is correctly
re-entered — the firmware is *well-behaved* about resetting) plus the loss of
the converged HSITRIMR trim.

### 7.1 What was established

All diagnosis used **separate diagnostic images**; the production image itself
was never modified, and the project sources are byte-for-byte unchanged
(re-verified: post-session rebuild is byte-identical to the pre-session one).

1. **It is in the FRAME-TRIGGERED path** (originally read as "the decode
   path"; corrected in [§7.4](#74-root-cause-found-and-fixed) — it is the
   *capture* path, not the decoder). 120 s of idle running (100 Hz render +
   WS2812 out + armed-capture loop, **no frames on the wire**) → **zero
   resets**. The tell was there in hindsight: with no frames, `cap_arm`
   never detects an edge and so **never enters `_cap_loop`** — exactly the
   transition that faults. Rendering, the TIM4 tick and the SWIM discipline
   are all stable.
2. **It is an illegal opcode.** `RST_SR` (`0x50B3`) read at boot is **`0x04`
   = ILLOPF** on *every* reset, and `0x00` on power-on. Not a watchdog (none
   enabled), not EMC, not SWIM.
3. **It is NOT stack overflow.** A 64-byte canary painted at
   `0x0360-0x039F` and scanned after every decode leaves **47–63 bytes
   intact** → stack low-water `0x038F-0x039F`, **peak depth 97–113 B** in the
   160 B region, **~47 B headroom**. This *confirms the closure report's RAM
   ledger on silicon* (113 B peak, 47 B headroom) and rules the stack out.
4. **It is NOT the vector-gap relocation (closure risk 6 — exonerated).** A
   diagnostic build that moves `decode_asm.s`'s VGAP block into ordinary
   `CODE` and installs a **full 32-entry vector table** (RESET → GSINIT,
   IRQ23 → `tim4_upd_isr`, all other 30 vectors → an `IRET` stub) **resets at
   the same rate** (17 / 90 decodes). Note the guard still passed and the loop
   phase was preserved in that build.

### 7.2 The decoder is EXONERATED (the original suspect was wrong)

The closure-session hypothesis blamed `decode_asm.s`. It is wrong. A bench
build that dumps the raw 288-byte capture over UART **before** calling
`ws_decode_ex` (`rbarf_dbg.c`, [§7.3](#73-how-it-was-localised)) decoded
**184/184 dumped captures with zero faults**; every reset happened on a
frame that produced **no dump at all** — i.e. before the decoder ever ran.
The decoder is a pure function of `capture_buf` and would fault identically
with or without the dump; it never did. The ucsim decoder corpora
(186/186 host, 36/36 asm, 10/10 ND48, plus a new 66-case refusal/chase
fuzz, [§7.5](#75-re-proof)) are all bit-exact. The ILLOPF is upstream of
the decoder, in the capture arm.

### 7.3 How it was localised

Three bench instruments, each a separate diagnostic image (the production
sources were untouched until the fix):

1. **`rbarf_dbg.c` — dump-before-decode.** 184 dumped captures, 0 decode
   faults; 33 resets, all on *un-dumped* frames. → not the decoder.
2. **`rbarf_bc.c` + `crumb.s` — a stage breadcrumb** in an ABS RAM cell at
   `0x0360` that survives a warm reset (it is outside the crt0-cleared DATA
   area). It is written immediately before each pipeline stage and read
   back at the next boot alongside `RST_SR`. **Every one of 8 resets
   reported `RST_SR=0x04` (ILLOPF) with the crumb frozen at `0x20` — the
   `call _cap_arm` window** (99 decodes between them). Not render, not
   decode: the capture.
3. **Disassembly of the linked image.** The four edge-detect polls in
   `cap_arm` are `btjt 0x500B,#3,_cap_loop`. Three link correctly to
   `_cap_loop` (`0x9FAF`); **the 3rd links to `0x9FAD`** — two bytes short,
   **mid-instruction** (inside the `wait_high` btjf), whose first byte
   `0x0B` is not a valid opcode.

Gating the TIM4 update interrupt across the whole capture did **not** stop
the resets, confirming (with §7.1 pt 4's full-vector-table result) that it
is a genuine illegal-opcode fetch from a wild branch, not an interrupt or
vector artefact.

### 7.4 Root cause (found and fixed)

**An sdld relocation bug.** `cap_arm` (area `CAPARM`, ABS) branches into
`_cap_loop` (area `CAPLOOP`, ABS) — a **cross-ABS-area PC-relative** `btjt`
whose 1-byte `rel` operand sdas defers to an sdld "F1" relocation. When two
of these consecutive `btjt` PCR relocations pack into one `.rel` T-record,
sdld computes the **first of the pair two bytes short**. Of the four
identical polls, the 3rd linked to `rel 0x1D` (→ `0x9FAD`) instead of
`0x1F` (→ `0x9FAF`); the other three were correct.

The four polls exist for the trigger-phase (t0) discipline: whichever poll
first sees the WS2812 rising edge branches into the sampler. **Which poll
catches the edge depends on the frame's arrival phase** — roughly uniform
across the four. So on ~1 capture in 4–6 the edge was caught by the **3rd**
poll, the CPU branched into the middle of an instruction, and took an
**ILLOPF reset**. That — entirely in the capture arm, nothing to do with
the decoder — is "the reset every ~6 decodes." (The idle test saw zero
resets precisely because idle never presents an edge, so the 3rd poll never
fires.)

**Fix (`cap_arm.s`).** Emit each poll's five `btjt` bytes with the `rel`
computed **at assembly time** from same-area quantities (macro `BTJT_CL`:
`rel = CL_ENT - (CAPARM_ORG + (. - _cap_arm) + 1)`), so **no relocation
record is generated** and sdld never touches the offset. The emitted bytes
are byte-identical to a correctly-linked `btjt 0x500B,#3,_cap_loop`, so
cadence, cycle counts and every address are unchanged — the calibrated
capture timing is preserved exactly; the only byte that changes in the
whole image is the 3rd poll's `rel`, `0x1D → 0x1F`. `_cap_loop` is now
pinned **exactly** at `0x9FAF` by `guard_prod.py`, which additionally
disassembles all four polls in the linked `.ihx` and fails the build unless
each targets `_cap_loop` — the check that would have caught this at link
time (`sdld` checks neither the overlap nor the relocation).

### 7.5 Re-proof

| Harness | Result |
|---|---|
| `parity_host.py` (gcc `decode.c` vs `embedded_v2.py`) | **186/186** ✅ |
| `ucsim_bitexact.py --asmdec --scan asm` | **36/36** ✅ |
| `dev_prod/smoke48.py` (ND48) | **10/10** ✅ |
| `dev_prod/fuzz48.py` in-envelope (eps ±7.5 %, corrupted checks, split votes, chase, noise) | **66/66** ✅ |
| `fuzz48.py` mid-frame-start torture (out of envelope) | 2 cases differ in **counters only** (both `refuse_marker`; bytes+path+cause agree) — a pre-existing `decode_asm`/`embedded_v2` discrepancy on truncated input, **unaffected by this fix** (the decoder is byte-unchanged) |
| Linked-image check: 4 `cap_arm` polls → `_cap_loop` | **4/4 → 0x9FAF** ✅ (was 3/4) |

Flash unchanged (the fix is byte-neutral): `rbarf_prod.ihx`
**8052 / 8192**, `rbarf_prod_verbose.ihx` **8133 / 8192**; guard OK; the
calibrated `build/capture.ihx` baseline is byte-identical (`md5 84955f77…`).

### 7.6 Bench soak — the crash is gone

Fixed `rbarf_prod_verbose.ihx`, `bench/drive_prod.py --reps 24`, **240
single-transmission frames**, banner at 5.06 s (SWIM window respected):

```
delivered 65 (39 O + 26 C), refused 175, no-report 0,
CATASTROPHIC 0, protocol-errors 0
MCU RESETS: 0        (RST_SR clean throughout; converged eps +0.04..+0.09 %)
decode window mean 166.9 ms
```

* **0 resets across 240 frames** (240 armed decodes with no dead windows) —
  against a pre-fix rate of ~1 reset per 6. **The blocker is cleared.**
* **0 wrong emissions** — every one of the 65 `V:` lines matched the sent
  DATA byte-for-byte. The safety-critical property holds.
* **0 no-report** — with resets gone, no frame is lost to a 5 s dead window.

**One caveat, and it is *not* a regression of this fix.** Raw delivery is
65/240 = 27 % (dominated by `R7`/`R5`/`R8` weak/tied/chase refusals),
below the synthetic model's 89–96 %. The gap predates the fix: the buggy
diagnostic build delivered 49 % on this same bench, and both are far under
the model — the synthetic sampler over-predicts silicon decode margin,
especially for low-transition frames (`rnd` delivers 24/24, all-zero `dark`
0/24; content-correlated, i.e. a decode-margin signature, not a
capture-timing one). Crucially, **the fix can only convert a formerly
*crashing* (3rd-poll) capture into a normal decode that then delivers *or
safely refuses* — it never turns a delivery into a refusal.** It therefore
cannot reduce the absolute number of delivered frames; it lowers the
*percentage* only by adding those former crashes (now safe refusals,
last frame held per SS9.4) to the denominator. Net behaviour is strictly
better: never resets, never emits wrong, holds the last frame when the
capture margin is poor. Raising the delivery *rate* is a separate
decode-margin/arm-t0-spread investigation (would touch calibrated capture
timing and needs its own validation campaign); it is **out of scope for the
crash fix** and does not gate it.

### 7.7 Diagnostic artifacts (bench-only, not shipped)

`rbarf_dbg.c` (dump-before-decode), `rbarf_bc.c` + `crumb.s` (reset-surviving
stage breadcrumb), `rbarf_bc_gate.c` (TIM4-gated control), and the drivers
`bench/crashcap.py` / `bench/bcdrive.py`, plus `dev_prod/fuzz48.py`. None are
in the default `make`/shipping targets.

---

## 8. Residual risks and things this session did **not** verify

1. **Animation output on pin 5 is NOT bench-observable — visually unverified.**
   The probe has no capture channel on the STM8's WS2812 output pin; the bench
   only sees pin 8 (UART). On-silicon animation correctness therefore rests
   entirely on (a) the 25.9 M-case host equivalence proof under **gcc**
   semantics and (b) the bench-verified fact that the 48-byte frame reaching
   `ws2812_in_buf` is byte-exact. **SDCC-compiled `anim.c` output was never
   diffed against the gcc reference** (closure risk 8 stands, unchanged).
2. **Flash goal missed:** 140 B free vs the ≥256 B goal, gap 116 B. Confirmed.
3. **Strict RAM reading not met:** statics 863 + peak 113 + 128 > 1024, short
   by ~80 B. The *measured* peak and 47 B headroom are now confirmed on
   silicon, so the allowance-based reading holds and the strict one does not.
4. **Latent defect, free to fix:** `rbarf_prod.c` writes `CLK_HSITRIMR`
   immediately after the last `uart_putc`, which waits only for **TXE**, not
   **TC**. The final character of every report is still in the shift register
   when the baud clock changes. `rbarf_v21.c` has a `uart_drain()` (waits for
   TC) for exactly this reason and production dropped it. No corrupted line was
   seen in ~200 reports — the affected character is the `\n` — but it should be
   restored.
5. ~~**Applied-frame-rate ceiling unmeasured**~~ — **measured, §9.2**: the
   shipping terse image stays 100 % armed down to a **180 ms** inter-frame
   period (5.6 Hz), exactly the arithmetic estimate.
6. Gamma 2.2 remains a placeholder LUT pending owner curve selection (data
   swap only). Unchanged.
7. Single unit, single ambient. Temperature-corner behaviour is unverified.

---

## 9. Re-gate, applied-rate ceiling, and Klipper end-to-end

Run on the fixed images (`rbarf_prod_verbose.ihx` md5 `1d89989c…` for every
byte-checked run, shipping `rbarf_prod.ihx` md5 `45ed9a8f…` for the terse
rate sweep), guard green on both, flashed with
`flash.py --ihx … flash-only`. **590 frames were put on the wire across the
six runs below: 0 MCU resets, 0 catastrophic emissions.**

### 9.1 The 30-frame gate — 2 of 3 criteria met

`bench/drive_prod.py --reps 3 --rate-probe`, same 10 payloads × 3, single
transmission. Banner `RBARF-P 1` at 5.06 s (SWIM window respected).

```
18/30 delivered correct (10 O + 8 C), 12 refused, 0 no-report,
0 CATASTROPHIC, 0 protocol errors
MCU RESETS observed during the 30-frame run: 0
decode window  min 157.8  mean 168.1  max 170.8 ms
```

| Criterion | Required | Measured | |
|---|---|---|---|
| MCU resets (RST_SR-attributed) | 0 | **0** | ✅ |
| Catastrophic (wrong emission) | 0 | **0** | ✅ |
| Delivered | ≥ 26/30 | **18/30** | ❌ |

The crash fix is confirmed a second time and from a new angle: **no-report
fell 9 → 0**. Every one of the 30 frames reached an armed receiver and
produced a report; the previous run's 9 dead frames were purely the three
reset windows. Decode window and auto-trim are unchanged (first decode
−1.08 % at factory trim, then +0.05…+0.13 % on code 7).

The delivery shortfall is the **pre-existing decode-margin gap** (§7.6), and
it is content-correlated exactly as the soak predicted:

| payload | rnd | blink | seq_plain | seq_pause | full | preset_rainR | preset_spin | colors | fade | dark |
|---|---|---|---|---|---|---|---|---|---|---|
| delivered | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 2/3 | 1/3 | 1/3 | 0/3 | 0/3 |

High-entropy payloads deliver perfectly; low-entropy ones (`dark` all-zero,
`fade` and `colors` with long identical runs) are where the margin is lost.
Refusals only — never a wrong emission.

### 9.2 Applied-frame-rate ceiling — measured at last

`drive_prod.py --rate-probe` still cannot measure this: it drives
`FRAMES[0]` = `colors`, a 1/3-margin payload, so its "applied frames/s"
collapses to ≈0 for reasons that have nothing to do with timing. The new
**`bench/rate_probe.py`** fixes that by sweeping the inter-frame period with
a payload that is not margin-limited (`rnd`, 3/3 above, 24/24 in the soak)
and by separating *armed* (a report came back at all) from *delivered*.

Shipping terse image, `rnd`, 12 frames per period, free-running:

| period | rate | armed | delivered | applied |
|---:|---:|---:|---:|---:|
| 400 ms | 2.5 Hz | 12/12 | 12 | 2.50 f/s |
| 300 ms | 3.3 Hz | 12/12 | 11 | 3.06 f/s |
| 250 ms | 4.0 Hz | 12/12 | 10 | 3.33 f/s |
| **220 ms** | **4.5 Hz** | **12/12** | **12** | **4.55 f/s** |
| 200 ms | 5.0 Hz | 12/12 | 11 | 4.58 f/s |
| **180 ms** | **5.6 Hz** | **12/12** | 11 | **5.09 f/s** |
| 160 ms | 6.2 Hz | 7/12 | 4 | 2.08 f/s |
| 140 ms | 7.1 Hz | 6/12 | 6 | 3.57 f/s |
| 120 ms | 8.3 Hz | 6/12 | 6 | 4.17 f/s |
| 100 ms | 10 Hz | 6/12 | 6 | 5.00 f/s |

**Ceiling: 5.6 Hz (180 ms).** Below 180 ms the armed fraction falls off a
cliff to ~50 % — the receiver is blind for one whole frame period — which
pins the blind window at **≈178 ms**, matching §6.3's arithmetic estimate to
the millisecond. Peak delivered throughput is **5.1 frames/s**; the highest
rate that loses nothing is **220 ms / 4.5 Hz**.

The VERBOSE bench image measures **300 ms / 3.3 Hz armed, 400 ms for 12/12**
— the ~103 ms of `V:` transmission, exactly as predicted. Quote the terse
numbers for anything shipping. 0 catastrophic and 0 resets across all 266
sweep frames.

### 9.3 Klipper end-to-end — the macro is bytes-correct and the device refuses it

`bench/test_klipper_macro.py --bench-is-free --reps 3` (first execution
ever). All 15 cases render through the Klipper emulation and match
`klipper/verify_macro.py` ground truth byte-for-byte before anything
touches the wire — **the macro itself is vindicated**. On the device:

```
3/90 delivered (1 direct + 2 chased), 87 refused, 0 CATASTROPHIC, 0 silent
   bare  (59 B): 3/45 delivered, eps mean +0.24 %
   padded(60 B): 0/45 delivered, eps mean +1.79 %, 43/45 refuse R3 infeasible
```

Two separate failures, and the pad byte is the sharper one.

### 9.4 PAD-BYTE VERDICT: fatal, and it is not about the trailer

Every 60-byte transmission read **+1.55 % higher eps** than the same frame
sent bare — a clean, reproducible offset that toggles with the variant.
Moving the pad to the **front** of the chain (`--variants bare,lead,padded`,
`klipper/bench_klipper_padplacement.json`) changed nothing: 0/30 delivered,
eps +1.85 %. So the pad is not disturbing the trailer scan or the byte
alignment — it is **stretching the fitted bit period**, because `K` is
fitted over the whole captured burst.

`bench/pad_law.py` isolates it on a payload with no margin problem:

| wire | pad | eps mean | offset vs 59 B | predicted `n/59` | delivered |
|---:|---:|---:|---:|---:|---:|
| 59 B | 0 | −0.50 % | — | — | **4/4** |
| 60 B | +1 trail | +1.01 % | +1.51 % | +1.69 % | 0/4 |
| 60 B | +1 lead | +0.97 % | +1.47 % | +1.69 % | 0/4 |
| 61 B | +2 trail | +2.68 % | +3.18 % | +3.39 % | 0/4 |
| 61 B | +2 lead | +2.64 % | +3.14 % | +3.39 % | 0/4 |
| 62 B | +3 trail | +4.36 % | +4.86 % | +5.08 % | 0/4 |
| 62 B | +3 lead | +4.32 % | +4.82 % | +5.08 % | 0/4 |

**The law: each extra WS2812 byte on the wire inflates measured eps by
≈ +1.6 % (≈ 1/59), leading or trailing, and one byte is enough to refuse.**
The clock estimate is driven off the burst's total extent against an assumed
bit count, so surplus bytes are indistinguishable from a slow clock. At
+1.6 % the fit lands outside the feasibility gate → `R3 infeasible`
(a leading pad shifts alignment as well → `R2 marker`). 4/4 → 0/24 the
moment a single byte is added. Deterministic, not marginal.

**Consequence for Klipper.** The frame is 59 bytes; a `neopixel` chain is
configured in 3-byte LEDs, so the shortest chain that can carry it is 20
LEDs = **60 bytes**. The stock neopixel driver therefore *cannot* clock 59
bytes, and the macro as written can never be decoded. Three ways out, none
of them a macro tweak:

1. **Make the wire frame 60 bytes** (one defined byte added to the protocol,
   e.g. a second trailer byte) so a 20-LED chain is exact. Protocol + firmware
   + macro change; the cleanest fix, and it costs no decode margin.
2. **Make the clock fit tolerant of surplus bytes** — fit `K` over the
   header→trailer span only, rather than the whole burst extent. Firmware
   change in the seed/refine/calibrate path; the most general fix.
3. **Drive the line from something other than the neopixel driver** (a
   host-side `[output_pin]`/MCU command that clocks exactly 59 bytes).

Even with the pad resolved, `bare` only reached 3/45: the macro's payloads
are almost all low-entropy (eight identical LEDs plus a mostly-zero flag
block), i.e. the worst corner of §9.1's content correlation. **The Klipper
path needs the pad fix *and* the decode-margin work before it can ship.**

---

## 10. Go / no-go

> **SUPERSEDED. The current verdict is §12** (final production gate,
> 2026-09-07). History of this document's verdicts:
> §10 pad-byte blocker → fixed and proven fixed (§11.2). §11.4 raised a
> catastrophic-emission blocker → **CLOSED** in §12 (0 wrong emissions
> across 1759 accepted emissions, including a direct replay of the two
> offending frames). One criterion has never been met and still is not:
> **delivery ≥26/30** (§12.7 — 27/30 cold, 25/30 warm, pooled 83.3 %).
> **§12 verdict: NO-GO on delivery margin alone.**

**The ILLOPF blocker is CLEARED. Remaining gate is delivery-rate margin, not
stability.**

Every static claim reproduces: flash ledger byte-exact, phase pinning
byte-exact and guard-enforced (now including an exact-address pin on
`_cap_loop` and a linked-image disassembly check on the four `cap_arm`
polls), host parity 186/186, ucsim 36/36 + 10/10 + 66-case fuzz, animation
equivalence over 25 945 920 cases, and — the property that must never fail —
**zero wrong emissions**, across every frame ever driven including the
240-frame post-fix soak.

The illegal-opcode reset is **fixed**: it was an sdld PC-relative
relocation bug that mis-linked the 3rd of `cap_arm`'s four edge-detect
`btjt` polls two bytes short (into mid-instruction → ILLOPF) whenever the
frame edge was caught on that poll — a capture-arm defect, **not** the
decoder, the stack, or the vector-gap relocation (§7.4). The 240-frame soak
runs **0 resets, 0 catastrophic, 0 no-report**.

**Re-gate met:** 0 resets, 0 catastrophic — now over **590 frames** in one
session (§9), with `no-report` down from 9/30 to **0/30**. The
applied-frame-rate ceiling, previously unmeasurable, is **5.6 Hz / 180 ms**
on the shipping image (§9.2).

**Not met:** delivery rate — 18/30 against the required 26/30. The gap is
pre-existing, content-correlated (3/3 on high-entropy payloads, 0/3 on
all-zero) and independent of the crash fix, which provably cannot lower
absolute deliveries (§7.6).

**NO-GO, and the blocker has moved.** Stability is settled; two delivery
issues remain, one of them newly identified and much easier than the other:

1. **Klipper is blocked by a one-byte defect, not by margin** (§9.4). Any
   surplus WS2812 byte inflates the fitted clock by ≈1.6 % and forces a
   refusal — and a Klipper `neopixel` chain cannot clock fewer than 60 bytes
   for a 59-byte frame. Deterministic, root-caused, and fixable three
   different ways (60-byte frame / span-limited clock fit / non-neopixel
   driver). **This is the highest-value next fix**: it is a clean win, not a
   margin grind, and it gates the entire Klipper feature.
2. **Decode margin on low-entropy payloads** remains the general gate for
   ≥26/30 — unchanged from §7.6, and the harder of the two.

Residual risks §8 (anim SDCC diff, flash/RAM goals, `uart_drain`,
temperature corner) stand unchanged, less the frame-rate item now measured.

---

## 11. Protocol v2.2 bench re-gate (2026-09-07)

Protocol v2.2 grew the check block from `CRC8 x3` to `CRC8 x4`, making the
frame **60 bytes = exactly 20 WS2812 LEDs**, so no pad byte can exist.
This section re-gates the device on that protocol and closes §9.4.

Build: `make clean` + full rebuild, guard green on both links
(`prod` 87 B free, `verbose` 19 B free). All three images came back
**byte-identical** to the ledgered ones (`capture.ihx` md5
`84955f77…`, `rbarf_prod.ihx` `9baabefe…`, `rbarf_prod_verbose.ihx`
`bcf83129…`), i.e. the build is reproducible. Independent Intel-HEX
accounting: prod **8101/8192** (91 B free), verbose **8169/8192** (23 B
free). Flashed `rbarf_prod_verbose.ihx` via
`flash.py --ihx … flash-only`, first attempt, banner `RBARF-P 1` at
**5.06 s** (SWIM window intact). **151 frames driven, 0 MCU resets.**

### 11.1 The 30-frame gate — run twice

`bench/drive_prod.py --reps 3`, 10 payloads × 3, single transmission.

| Criterion | Required | Cold run | Warm re-run | |
|---|---|---|---|---|
| MCU resets | 0 | **0** | **0** | ✅ |
| Catastrophic | 0 | **0** | **0** | ✅ |
| Delivered | ≥ 26/30 | **14/30** | **14/30** | ❌ |

Cold: 14/30 (6 O + 8 C), 15 refused, 1 no-report. Warm: 14/30 (7 O + 7 C),
16 refused, 0 no-report. Per-payload, both runs pooled (n = 6 each):

| payload | rnd | seq_pause | colors | full | blink | seq_plain | preset_spin | preset_rainR | fade | dark |
|---|---|---|---|---|---|---|---|---|---|---|
| delivered | 5/6 | 5/6 | 3/6 | 3/6 | 3/6 | 3/6 | 3/6 | 3/6 | 0/6 | 0/6 |

The content correlation of §9.1 reproduces exactly: high-entropy payloads
deliver, the all-zero `dark` and long-run `fade` never do.

**Do not read 14/30 against §9.1's 18/30 as a v2.2 regression.** §11.3
shows delivery on this unit swings by ~8× with die temperature alone, and
the two campaigns were not temperature-controlled. The comparison is
confounded; a like-for-like re-measurement is owed to the Margin phase.

### 11.2 PAD VERDICT: the one-byte defect is FIXED — proven

`bench/test_klipper_macro.py --bench-is-free`, now testing the **exact**
60-byte stream Klipper clocks out (v2.1's bare/padded split is gone; the
stream *is* the frame). All 17 cases match `verify_macro.py` ground truth
before anything reaches the wire.

The paired control is unambiguous — same 4 cases, same session, 5 reps:

| variant | wire | eps mean | delivered | refusals |
|---|---:|---:|---:|---|
| `frame` (what Klipper emits) | 60 B | **+0.31 %** | **1/20** | mixed causes |
| `pad1` (one surplus 0x00) | 61 B | **+1.85 %** | **0/20** | **20/20 `R3 infeasible`** |

One surplus byte still inflates the fitted clock by **+1.50 pp**
(predicted `1/60` = +1.67 %) and refuses deterministically — the pad law
of §9.4 holds, unchanged. What changed is that **v2.2's frame no longer
contains that surplus byte.**

Against the v2.1 baseline, on what Klipper actually clocks out:

| protocol | Klipper's real output | delivered |
|---|---|---:|
| v2.1 | 59-byte frame + 1 pad = 60 B | **0/30** (`bench_klipper_padplacement.json`) |
| v2.2 | 60-byte frame, exact | **5/51**, and 8/20 cold (§11.3) |

Under v2.1 the macro's real output was **undecodable, always**. Under v2.2
it decodes, byte-for-byte correct against ground truth. **The pad defect
is designed out and bench-confirmed.** §9.4's blocker 1 is closed.

### 11.3 Delivery is strongly temperature-dependent — new finding

`eps` climbed monotonically across the session as the die warmed, and
delivery tracked it. Same 4 Klipper cases, same variant, same 5 reps:

| condition | eps mean | delivered |
|---|---:|---:|
| hot (end of a ~40 min run of campaigns) | +0.31 % | **1/20 (5 %)** |
| cold (after ~5 min powered off) | +0.15 % | **8/20 (40 %)** |

`sequence_pause` went **0/5 hot → 5/5 cold**. Session-wide eps means:
drive cold +0.04 %, drive warm +0.11 %, Klipper hot +0.20 %, control
+0.31 %; a 5-minute power-off returned it to +0.05 %, so the drift is
thermal and **reversible**, not a wear or calibration effect.

This makes temperature at least as large a lever on the margin gap as
payload entropy, and it is not in §8's residual-risk list as a
*delivery* factor. **The Margin phase should treat eps drift as a
first-class target** (periodic re-trim, or a clock fit that tolerates
larger |eps|), and every future gate number needs a stated thermal state
to be comparable.

### 11.4 BLOCKER: two catastrophic emissions — the chase false-accepted

The Klipper run produced the **first wrong emissions ever recorded on
this project** (§10 previously claimed zero across 590 frames):

```
klipper main run: 51 frames -> 5 delivered, 44 refused, 2 CATASTROPHIC
   of the 7 frames the device ACCEPTED, 2 carried wrong data (29 %)
   direct (O) decodes: 5/5 correct      chase (C) decodes: 0/2 correct
```

Root cause, established from the recorded frames — **it is not the v2.2
majority vote**:

| evidence | `preset_rain` r0 | `preset_rain_rev` r0 |
|---|---|---|
| transmitted check block | `F7F7F7F7` | `73737373` |
| check block damaged? | **no — unanimous** | **no — unanimous** |
| `crc8(truth)` | `F7` | `73` |
| `crc8(wrong bytes emitted)` | **`F7`** | **`73`** |
| corruption | 4 bits, all 0→1 | 4 bits, all 0→1 |
| location | flag bytes 29,42,44,47 | flag bytes 28,39,42,46 |

Both check blocks were **unanimous**, so the majority vote returned a
single correct reference and the 4-vote scheme is exonerated. The failure
is the **chase**: it searched bit-repairs across the payload's long zero
runs (these frames carry ≥96-bit all-zero spans) and found a 4-flip
candidate whose **CRC-8 collides with the true CRC-8**. An 8-bit check
cannot survive that many candidates — `bench/crc.py`'s own false-accept
table predicts it (64 trials → 22 %, 256 trials → 63 % for a single
reference), and this is that prediction landing on hardware.

Why it never showed before: every prior corpus was `drive_prod`-style,
whose worst zero run is far shorter. The Klipper corpus is the first with
100+ bit zero spans, because the macro's DATA is 8 base colours plus a
mostly-unused 24-byte flag block. **The exposure is inherent to the
Klipper payload shape, so it ships with the Klipper feature.**

This is a **hard blocker and outranks the margin gap**: a refusal leaves
the previous animation running, but a false accept drives the LEDs with
wrong data and the receiver cannot tell. Candidate fixes, none of them a
macro tweak:

1. **Widen the check** (CRC-16 over DATA) — kills the collision
   probability outright; costs 2 wire bytes and breaks the exact 20-LED
   tiling that v2.2 just bought (a 62-byte frame needs a 21-LED chain,
   reopening §9.4). The tension between these two is now the central
   protocol trade-off.
2. **Bound the chase** — cap candidate count and/or edit distance, and
   refuse instead of accepting a repair whose evidence is one byte of
   CRC. Firmware-only, cheap, and strictly safer; costs some of the
   chase-repaired deliveries (7–8 per 30 in §11.1).
3. **Gate the chase on payload structure** — refuse to chase inside long
   uniform runs, where candidate density is highest.

### 11.5 Rate spot-check — clean pass

`bench/rate_spot.py --bench-is-free --spacing-ms 250 --frames 12`, `rnd`
payload, cold unit:

```
ARMED (saw the frame): 12/12   [pass criterion]
of those: 12 delivered, 0 refused, 0 CATASTROPHIC
eps: first -1.12 % (factory trim) then +0.04 … +0.07 %
```

**12/12 armed and 12/12 delivered.** 250 ms spacing is comfortable, and
on a cold unit with a high-entropy payload the path is *perfect* — which
is the cleanest evidence that §11.1's shortfall is margin and thermal,
not framing or timing.

### 11.6 v2.2 verdict

| item | state |
|---|---|
| Pad-byte defect (§9.4 blocker 1) | ✅ **CLOSED** — proven fixed on hardware |
| MCU stability | ✅ 0 resets in 151 frames |
| Rate at 250 ms | ✅ 12/12 armed, 12/12 delivered |
| Catastrophic emissions | ❌ **NEW BLOCKER** — 2, chase CRC-8 collision (§11.4) |
| Delivery ≥ 26/30 | ❌ 14/30; thermally confounded (§11.3) |

**Still NO-GO, and the blocker has moved again.** Klipper's framing is
fixed and no longer gates the feature; correctness of chase-repaired
decodes now does. Fix the false-accept (§11.4) before any further margin
grind — margin work that raises the accept rate without widening the
check would *increase* the rate of wrong emissions.

> **UPDATE (§12, 2026-09-07):** both rows marked ❌ above were acted on.
> The catastrophic row is **CLOSED** — 0 wrong emissions over 1759
> accepted emissions, and the two frames in §11.4 were re-driven and
> delivered correct. Delivery rose 14/30 → **27/30 cold / 25/30 warm**,
> which is a large gain but still short of ≥26/30 reliably. The
> thermal confound in §11.3 is also resolved: it was the operating point,
> and at code 0 warm drift is only +0.105 pp with 0.98 pp of cliff
> headroom (§12.1).

---

## 12. FINAL PRODUCTION GATE — auto-trim retarget + bounded chase (2026-09-07)

Gate of the two margin-report fixes on real silicon. Images rebuilt from a
**`make clean`** tree and byte-identical to the ledgered ones:

| image | md5 | free |
|---|---|---:|
| `build/rbarf_prod.ihx` | `e022cd75…` | 91 B |
| `build/rbarf_prod_verbose.ihx` (flashed) | `63629508…` | 23 B |
| `build/capture.ihx` | `84955f77…` — reproduced from source, unchanged | — |

`guard_prod.py` green on both maps before flashing (REL end 0x9F1A / 0x9F5E
≤ CAPARM 0x9F66, `_cap_loop` 0x9FAF phase 0xF, all four `cap_arm` BTJT poll
targets disassembled from the linked image). Host parity re-run
independently: **276/276** bit-identical across all five corpora
(`data/captures_val.json` never opened). Flash succeeded on the **first**
power cycle; **0 of the 3-failed-cycle budget consumed** all session.

### 12.1 Fix #1 verified LIVE — the trim parks in band, in zero steps

`trim_v` initialises to 0 and `auto_trim()` steps only outside
[−1.6 %, −0.4 %], so factory code 0 is a **fixed point**: the retarget is
verified by the unit never leaving the band, not by watching it walk.

| run | n verified decodes | mean eps | range | in band |
|---|---:|---:|---|---:|
| gate cold | 27 | −1.055 % | −1.11 … −1.01 | 27/27 |
| gate extended (60) | 48 | −1.077 % | −1.10 … −1.04 | 48/48 |
| 15-min soak | 1612 | **−0.950 %** | −1.02 … −0.88 | **1612/1612** |
| gate warm (post-soak) | 25 | −0.958 % | −0.98 … −0.92 | 25/25 |

**1712/1712 verified decodes in band**, σ = 0.022 pp over the soak. Warm
drift is **+0.105 pp** (−1.055 % cold → −0.950 % warm), leaving **0.98 pp**
of headroom to the +0.1 % emit-gate cliff. Under the old rule this unit
parked at code 7 (+0.02 % cold, +0.15…+0.33 % warm) — *on* the cliff.
The old failure mode is structurally gone: eps on a refusal is a garbage
clock fit (soak range −11.68 %…0.00 %) and is **not** a measurement.

### 12.2 Zero wrong emissions — the property that must never fail

| run | delivered | of | CATASTROPHIC | resets |
|---|---:|---:|---:|---:|
| gate cold | 27 | 30 | 0 | 0 |
| gate extended | 48 | 60 | 0 | 0 |
| gate warm (post 15-min soak) | 25 | 30 | 0 | 0 |
| 15-min soak (3600 sent, 1981 captured) | 1612 | 1981 | **0** | **0** |
| catastrophic replay (§12.3) | 8 | 10 | 0 | 0 |
| Klipper end-to-end 17×3 | 39 | 51 | 0 | 0 |
| **total** | **1759** | **2162** | **0** | **0** |

**3931 frames on the wire, 1759 accepted emissions, 0 wrong, 0 MCU resets.**

### 12.3 Catastrophic replay — the two recorded false-accepts

The exact frames from §11.4, re-rendered through `rbarf.cfg` and validated
against `verify_macro.py` before touching the wire, 5 reps each:

```
preset_rain      4/5 delivered CORRECT (1 chase-repaired), 1 refused R2   eps -1.06…-1.10 %
preset_rain_rev  4/5 delivered CORRECT (1 chase-repaired), 1 refused R2   eps -1.05…-1.26 %
                 -> 8/10 delivered, 2 refused, 0 WRONG EMISSIONS
```

Both originally false-accepted at **eps +0.23 % / +0.26 %** — the old code-7
warm operating point. Fix #1 vacates that regime and fix #2 bounds the
accept inside it; two chase repairs still fired here and both were
**correct**.

### 12.4 Fix #2 is live on silicon and observable

The flashed image runs `decode_asm.s` (`USE_ASM_DEC=1`), whose `cpair`
carries the §7.10 bound (`cp a,#3` = `A_PAIR`, `cp a,#5` = `MG_PAIR ≤ 4`).
Its behavioural signature is on the bench: **4 `R8` chase refusals in 120
gate frames and 5 in the 51 Klipper frames** — the decoder declining to
enumerate weight-2 repairs on exactly the long-zero-run payload shape that
produced the two catastrophics.

**Honest limit:** this run cannot attribute those `R8` refusals to the
bound. `R8` also fires pre-fix when the chase finds no passing trial, and
no raw captures were dumped this session, so the delivery *cost* of the
bound at the new operating point is **not measured on silicon** — only the
fixes report's synthetic/replay figures (1 synthetic delivery, −1 on the 80
real dumps) speak to it.

### 12.5 Klipper end-to-end — functional, and the predicted jump landed

`bench/test_klipper_macro.py --bench-is-free`, all 17 cases × 3, 60-byte
`frame` variant. All 17 render byte-exact against ground truth first.

| | delivered | catastrophic |
|---|---:|---:|
| §11.4 baseline (code 7, warm) | 5/51 (9.8 %) | **2** |
| this run (code 0) | **39/51 (76.5 %)** | **0** |

Refusals 12: `R2` marker 6, `R8` chase 5, `R3` infeasible 1. Every case
delivers at least 1/3; 4 cases go 3/3. The pre-fix run is preserved at
`klipper/bench_klipper_macro_results.prefix_baseline.json` because it holds
the only two recorded catastrophic rows.

The jump is **fix #1's** (operating point), not fix #2's; the zero is both
(fix #1 vacates the regime, fix #2 bounds the accept inside it).

### 12.6 Soak — 15 minutes, strict 250 ms cadence

3600 frames at a hard 250 ms schedule (harsher than the gate's ~435 ms):
1981 reports, **1612 delivered, 369 refused, 0 catastrophic, 0 resets**.
Delivery is **81.4 % of frames actually captured**; the 1619 no-reports are
the verbose image's own blind window — D: + the 98-char V: line take
≈ 287 ms, longer than the 250 ms cadence, so roughly every other frame
arrives unarmed. That is a property of the **VERBOSE bench** image, not of
the shipping terse one. Scoring cross-checked two independent ways
(payload must match a known frame **and** its temporal attribution;
0 unattributable reports).

### 12.7 Delivery — the gate criterion is NOT met

| run | delivered | ≥26/30? |
|---|---:|---|
| gate **cold** | **27/30 (90.0 %)** | ✅ PASS |
| gate **warm**, post 15-min soak | **25/30 (83.3 %)** | ❌ FAIL by 1 |
| gate extended (60) | 48/60 (80.0 %) | ❌ (80 %) |
| pooled, gate protocol | **100/120 = 83.3 %** | ❌ (95 % CI 76.7–90.0 %) |

A 4th 30-frame gate taken after a 32 s soak while validating the harness
read 24/30; including it the pooled figure is 124/150 = 82.7 %.

**The ≥26/30 bar sits above the point estimate and only 1 of 4 gate runs
cleared it.** This is not a thermal regression — it is the pre-existing
delivery margin the margin report already predicted for code 0 (24/30 cold,
25/30 warm, ceiling ≈28/30). We measured slightly better cold and exactly
on prediction warm.

Refusal causes over the 120 gate frames: `lock` 5, `marker` 5,
`infeasible` 5, `chase` 4, `admit` 1. The **5 lock (`R1`) refusals
= 4.2 %** are the capture-arm mis-triggers, matching the ~6 % estimate and
the ≈28/30 ceiling — and they are exactly what the **deferred lock-retry**
(margin report fix #2) targets.

### 12.8 Verdict

| criterion | required | measured | |
|---|---|---|---|
| Catastrophic emissions | 0 everywhere | **0 / 1759 emissions** | ✅ |
| MCU resets | 0 | **0 / 3931 frames** | ✅ |
| Trim parks in [−1.6, −0.4] % | yes | **1712/1712 decodes** | ✅ |
| Klipper functional | yes | **39/51, 0 catastrophic** | ✅ |
| Delivery | ≥26/30 | 27/30 cold, **25/30 warm** | ❌ |

> ## VERDICT: NO-GO — on delivery margin alone.

Both margin-report fixes did exactly what they were designed to do, and the
§11.4 blocker is **CLOSED**: the catastrophic-emission surface is gone
across 1759 accepted emissions, including a direct replay of the two frames
that caused it. Stability and correctness are settled. What remains is the
**one original, pre-existing criterion** — delivery ≥26/30 — which the
retarget lifted from 14/30 to 25–27/30 but not reliably past the bar.

The next lever is known, is not a grind, and was deliberately deferred out
of this phase: the **lock-retry** for the ~4–6 % capture-arm mis-triggers
(worth ~2 frames, ceiling ≈28/30). It touches calibrated arm timing and
needs its own validation phase — see §12.9.

### 12.9 Residual risks

1. **Delivery ≥26/30 not met** (§12.7). Pooled 83.3 %. Next lever is the
   deferred lock-retry (~2 frames, ceiling **≈28/30** — note the ceiling
   itself leaves no room for a 30/30 requirement, so if the bar must be
   met with margin the arm-timing path needs rework, not a retry).
2. **Animation output on pin 5 is still NOT bench-observable.** The probe
   has no capture channel on the STM8's WS2812 output; the bench sees only
   pin 8 (UART). Everything above verifies that the *frame reaching*
   `ws2812_in_buf` is byte-exact — **not one LED was observed this
   session.** SDCC-compiled `anim.c` has still never been diffed against
   the gcc reference (risk §8.1, unchanged).
3. **The bound's on-silicon delivery cost is unmeasured** (§12.4). Fix by
   dumping raw captures at code 0 (`dump_tf.py`) and replaying both
   decoders over them.
4. **The two recorded catastrophics were never captured raw**, so §12.3 is
   a statistical replay, not a bit-exact one (PROD_CLOSURE §3 note). The
   phase-2 ask from the fixes report stands: `dump_tf.py` those two frames.
5. **Single unit, single ambient, one 15-min warm point.** The full
   ±7.5 % HSI envelope is still unverified; at warm we measured 0.98 pp of
   headroom to the +0.1 % cliff, which is comfortable but is one unit.
6. `uart_drain()` still missing (§8.4) — `CLK_HSITRIMR` is written while
   the last `\n` is in the shift register. No corrupted line in ~2000
   reports this session, but it should be restored.
7. Flash/RAM goals (§8.2/8.3) and the placeholder gamma LUT (§8.6) stand.
   The **verbose** image has only 23 B free and is the binding constraint
   on any further decoder growth.

---

### Artifacts produced

| Path | Contents |
|---|---|
| `bench/drive_prod.py` | production-protocol bench driver (10 frames × N reps, ground-truth scoring, reset attribution, rate probe) |
| `recon/approaches/dev_prod/bench_prod_results.json` | full 30-frame run: per-frame verdict, status, eps, timing, reset flags |
| `bench/rate_probe.py` | **new** — inter-frame period sweep on a margin-free payload; separates *armed* from *delivered* (§9.2) |
| `bench/pad_law.py` | **new** — isolates the surplus-byte → eps law with 0…3 pad bytes, leading and trailing (§9.4) |
| `recon/approaches/dev_prod/bench_prod_regate.json` | the re-gate 30-frame run (§9.1) |
| `recon/approaches/dev_prod/rate_probe_results.json` / `rate_probe_terse.json` | verbose / shipping rate sweeps (§9.2) |
| `recon/approaches/dev_prod/pad_law_results.json` | pad-byte law measurements (§9.4) |
| `klipper/bench_klipper_macro_results.json` | Klipper end-to-end, bare vs padded × 3 (§9.3) |
| `klipper/bench_klipper_padplacement.json` | Klipper bare vs **lead** vs padded (§9.4) |
| `bench/rate_spot.py` | **new (v2.2)** — fixed-spacing rate probe; pass criterion is *armed*, delivery reported separately (§11.5) |
| `bench/test_klipper_macro.py` | v2.2: tests the exact 60-byte stream; `--cases` added for paired frame-vs-`pad1` controls; 2 high-entropy `rnd_colors` cases added (§11.2) |
| `klipper/bench_klipper_macro_results.json` | v2.2 Klipper end-to-end, 17 cases × 3 — **contains the 2 catastrophic rows** (§11.4) |
| `recon/approaches/dev_prod/bench_prod_gate_cold.json` | **new (§12)** — cold 30-frame gate, post-fix (27/30) |
| `recon/approaches/dev_prod/bench_prod_gate_extended60.json` | **new (§12)** — 60-frame delivery estimate (48/60) |
| `recon/approaches/dev_prod/bench_prod_soak_warm.json` | **new (§12)** — 15-min 250 ms soak (3600 frames) + the warm 30-frame gate, one power session |
| `recon/approaches/dev_prod/bench_klipper_catreplay.json` | **new (§12)** — replay of the two §11.4 catastrophic frames, 5 reps each |
| `klipper/bench_klipper_macro_results.prefix_baseline.json` | **new (§12)** — the pre-fix Klipper run, preserved because it holds the only two recorded catastrophic rows |
| `klipper/bench_klipper_macro_results.json` | re-run post-fix (39/51, **0 catastrophic**) |
| `recon/PROD_CLOSURE.md` | this document |

## 13. Protocol v2.3 bench validation — **NO-GO** (2026-09-07)

The v2.3 host stack and reference decoder are complete and parity-proven,
but this phase **could not validate v2.3 on silicon**, and the one axis it
*could* measure came back the wrong way. Two findings, both blocking.

### 13.1 BLOCKER 1 — there is no v2.3 firmware image, and there cannot be one today

Clean rebuild from source (`make clean && make all && make rbarf-prod`),
production flags `CHK_LEN=6`, `--data-loc 0xF0`, `--code-loc 0x8068`:

| link | CODE ends | CAPARM0 | over by |
|---|---|---|---|
| `rbarf_prod.ihx` (terse)   | `0xA252` | `0x9F66` | **748 B** |
| `rbarf_prod_verbose.ihx`   | `0xA296` | `0x9F66` | **816 B** |

`guard_prod.py` **FAILED both links and was not bypassed.** The overflow is
not marginal and not only an address-arithmetic complaint:

* the image's top byte is at **`0xA295`, past the end of flash (`0xA000`)** —
  662 B of it has nowhere to live;
* it **physically overwrites all 139 bytes of the pinned ABS block**
  `0x9F66..0x9FFF`, i.e. `cap_arm`, `_cap_capture` (`0x9FA1`) and `_cap_loop`
  (`0x9FAF`). Verified byte-for-byte against the ledger image: at `0x9F66`
  the ledger reads `35 02 03 40 4F 72 07 50 0B …`, the v2.3 link
  `51 85 85 90 F6 F7 5C 0C 15 …`. That is why the guard's second complaint
  is "expected 4 edge-detect BTJT polls in cap_arm, found 0" — the polls it
  scans for are gone from the hex.

Flashing that image would have destroyed the cycle-calibrated capture loop
and the arm sequence. **It was never sent to the programmer.** The failed
link's outputs were discarded and `build/rbarf_prod{,_verbose}.ihx` restored
to the §12 ledger images (md5 `e022cd75…` / `63629508…`).

Attribution, measured by re-linking this same tree at the v2.2 check length
(`CHK_LEN=4`, everything else identical): CODE ends `0xA179`, still **531 B
over**. So the two extra check bytes account for ~285 B of the overflow and
the **v2.3 pipeline architecture itself for ~531 B** — the C-compiled tail is
the dominant cost, not the wider check block. For reference the v2.2 ledger
verbose image tops out at `0x9F5D`, **9 B below** `CAPARM0`: v2.2 shipped with
essentially zero flash headroom, so v2.3 was never going to fit by trimming.

**Consequence: tasks 2, 3, 4 and 5 are not merely unmeasured, they are
unmeasurable.** No 30-frame gate (cold or warm), no auto-trim band check, no
Klipper end-to-end, no 150-frame soak, and still **no measured on-silicon
wrong-emission rate for v2.3**. Nothing was substituted or estimated in their
place, and no feature was silently cut to make room.

### 13.2 Task 1 — fresh v2.3 corpora acquired, and v2.3 *loses* to v2.2 on silicon

`capture.ihx` (md5 `84955f77…`, reproduced byte-identically by the clean
rebuild) was flashed on **attempt 1/3** and both corpora acquired clean —
**0 of the 3-failed-power-cycle budget consumed**:

* `data/captures_v23.json` — 18 patterns × 3 reps = **54** captures
* `data/captures_v23_val.json` — 12 held-out patterns × 3 reps = **36** captures

Scored with `recon/approaches/embedded_v2.py` at the shipped v2.3 constants,
no overrides (`v23bench_score_v23_real.py`). The **first real-silicon v2.3
numbers in the project**, beside the same scoring run over the acquired
CRC8 corpora:

| corpus | n | delivered | refused | **WRONG** |
|---|---|---|---|---|
| `captures_v21.json` (v2.1) | 54 | 50 (92.6 %) | 4 | **0** |
| `captures_v21_val.json` | 36 | 32 (88.9 %) | 4 | **0** |
| `captures_v22.json` (v2.2) | 54 | 51 (94.4 %) | 3 | **0** |
| `captures_v22_val.json` | 36 | 33 (91.7 %) | 3 | **0** |
| **`captures_v23.json`** | 54 | **39 (72.2 %)** | 15 | **0** |
| **`captures_v23_val.json`** | 36 | **22 (61.1 %)** | 14 | **0** |

**Wrong emissions: 0 of 61 v2.3 emissions (0.0000 %), target ≤ 0.2 % — met.**
One-sided 95 % Clopper-Pearson upper bound on 0/61 is **≤ 4.79 %**, so 90
captures are nowhere near enough to *demonstrate* a 0.2 % target; the zero is
real but it bounds almost nothing. That is the honest state of the
wrong-emission axis on silicon.

**Delivery is the failure.** v2.3 delivers **67.8 %** pooled (61/90) against
v2.2's **93.3 %** (84/90) on the same bench, same firmware, same 28-byte frame
geometry — a **≈25-point regression**, in the exact opposite direction from
the emit-always directive the relaxations were built to serve. The synthetic
work predicted +7.6 % *more* emissions.

The refusal histogram says which gates fire, and it is not the ones that were
relaxed:

| cause | v23 | v23val | note |
|---|---|---|---|
| R1 `refuse_lock` | 0 | 0 | relaxation A: never fires |
| R2 `refuse_marker` | 0 | 0 | relaxation B: never fires |
| R3 `refuse_infeasible` | 0 | 0 | never fires |
| R7 `refuse_admit` | 0 | 0 | never fires |
| **R6 `refuse_nocand`** | **8** | **10** | no weak candidate to flip |
| **R8 `refuse_chase`** | **7** | **4** | chase exhausted |

Relaxations A and B are confirmed to yield **zero** on silicon, exactly as
the host phase measured. Every refusal is R6/R8 — the check never validated.

### 13.3 Root cause — the dropped `0x00` calibration probe, measured on silicon

Reconstruction quality, same captures (`v23bench_diag_recon.py`), lock stage
only:

| corpus | frame′ bit-exact | mean bit errors | mean `n_weak` | K median |
|---|---|---|---|---|
| `captures_v22.json` | 45/54 (83.3 %) | 0.26 | 0.91 | 53008 |
| `captures_v23.json` | 31/54 (57.4 %) | **0.81** | **0.48** | 53013 |
| `captures_v22_val.json` | 29/36 (80.6 %) | 0.36 | 1.31 | 53009 |
| `captures_v23_val.json` | 16/36 (44.4 %) | **1.19** | **0.33** | 53007 |

The **lock is fine** — K and τ medians agree to ~5 counts and ~5 ns across
versions, and marker violations are 0 everywhere. What degrades is **class
calibration**: v2.3 carries ~3× the reconstruction bit errors *while flagging
fewer bits weak*. The decoder is **confidently wrong**, so the errors sit
outside the chase's reach — it has no weak candidate to flip (R6) or runs out
(R8). Widening `A_MAX` to 11 cannot help when `n_weak` is 0.

Mechanism: v2.2's markers `FF 00 AA 65` / `9A 55 00 FF` carry an `0x00` byte
at **each** end — 8 consecutive zero bits at a *known* position, which the
marker-forced `_calibrate` pass uses as class-0 width samples. v2.3's
`FF AA 65` / `9A 55 FF` carry **none** (max 0-run 2). This is precisely the
cost §"The marker trim (8 bytes → 6), and what it cost" flagged as *live and
unresolved* — the synthetic study put it at +4.5…+7.1 points of plateau
bit-exactness. **On silicon it is worth an order of magnitude more.**

**Same-session real-silicon A/B** (`bench_v23_marker_ab.json`): four 3+3
variants, identical DATA, identical CRC16 check block, identical 28-byte
frame — **only the marker bytes differ** — interleaved per pattern/rep so
thermal drift loads all four equally. 18 patterns × 3 reps × 4 variants = 216
captures:

| variant | header | trailer | delivered | frame′ bit-exact | WRONG | paired vs V0 |
|---|---|---|---|---|---|---|
| **V0** spec | `FF AA 65` | `9A 55 FF` | 42/54 (77.8 %) | 51.9 % | 0 | — |
| V1 | `FF 00 65` | `9A 55 FF` | 43/54 (79.6 %) | 59.3 % | 0 | 7:6, χ²=0.00 n.s. |
| **V2** | `FF AA 65` | **`9A 00 FF`** | **54/54 (100 %)** | **92.6 %** | 0 | **12:0, χ²=10.08** |
| V3 | `FF 00 65` | `9A 00 FF` | 48/54 (88.9 %) | 77.8 % | 0 | 9:3, χ²=2.08 n.s. |

Held-out confirmation (12 val patterns × 3 reps, V0 vs V2): V0 **22/36
(61.1 %)** — reproducing `captures_v23_val.json`'s 61.1 % across sessions —
against V2 **34/36 (94.4 %)**, 0 wrong.

**Pooled (90 paired cells): V0 64/90 = 71.1 % → V2 88/90 = 97.8 % delivered,
0 wrong either way; paired McNemar 25:1, χ² = 20.35, p < 0.001.**

One byte — replacing the trailer's `55` ruler with `00`, entirely **inside the
owner's 3+3 sizing** — recovers the whole regression and then some. V2 was
also the best of the seven variants in the host phase's synthetic study
(71.05 % plateau bit-exact, χ² 191.56); silicon agrees on the winner and only
disagrees about the size of the prize. It does trade away the end-of-frame
bit-period ruler, which is why it is **recommended, not applied**: it is an
owner-level byte choice and `docs/PROTOCOL.md` still specifies `9A 55 FF`.

### 13.4 v2.3 verdict — **NO-GO**

Neither acceptance axis is satisfiable as things stand.

| axis | target | measured | verdict |
|---|---|---|---|
| Delivery, 30-frame gate cold/warm | ≥ 28/30 | **not runnable** (no image) | **BLOCKED** |
| Delivery, host-scored silicon corpora | — | 61/90 = 67.8 % (v2.2: 93.3 %) | **FAIL — regression** |
| Wrong emissions | 0 | **0** of 61 emissions | pass, but bound ≤ 4.79 % only |
| Klipper end-to-end | ≥ v2.2's 39/51 | **not runnable** | **BLOCKED** |
| Soak ≥ 150 frames, 0 resets | 0 resets | **not runnable** | **BLOCKED** |
| Auto-trim parks in [−1.6 %, −0.4 %] | in band | **not runnable** | **BLOCKED** |

Two things must land before a v2.3 gate is worth attempting, in this order:

1. **Decide the trailer byte.** `9A 55 FF` → `9A 00 FF` is worth +26.7 points
   of delivery on silicon (71.1 % → 97.8 %, p < 0.001) at the cost of the
   end-of-frame bit-period ruler. Owner call. Gating v2.3 on the current
   markers would gate a protocol that is measurably worse than the one it
   replaces.
2. **Make room in flash.** 816 B for the verbose image. The measured lever is
   gamma off-chip (300 B, real link); hand-assembling the v2.3 tail is
   estimated ~600 B; dropping sequence mode and moving LED ordering to the
   host are unmeasured. All are owner-level feature/wire decisions and none
   was taken here.

Note the two interact: the whole point of the relaxations was delivery, and
on silicon they buy nothing (A and B fire zero times, R6/R8 dominate) while
the marker trim that paid for the wider check block is what actually costs
delivery. A v2.3 that keeps `9A 55 FF` spends 816 B of flash it does not have
to end up 25 points *behind* v2.2.

### 13.5 What this phase could not observe

* **No on-silicon v2.3 decode, at all.** Every v2.3 number above is the host
  reference decoder run over real captures. That is real silicon *signal*, but
  the on-chip decoder path — its timing, its RAM peak, the projected
  `chase → try_trial → ref_build → rank3` stack depth flagged in the host
  phase — remains unexecuted on hardware.
* **No v2.3 wrong-emission rate worth quoting.** 0/61 bounds the rate at
  ≤ 4.79 % (95 %), a factor of 24 short of the 0.2 % target. The §12 v2.2
  corpus (1759 accepted, 0 wrong) is still the only bench evidence at
  target-relevant scale.
* **Temperature.** All acquisitions were a single cold-to-warm session with no
  soak. §11.3 established delivery is strongly temperature-dependent; the
  V0→V2 A/B is drift-controlled by interleaving, but the absolute rates are
  not temperature-characterised.
* **The V2 marker is measured over 90 frames on one part.** It is a strong
  signal (p < 0.001, paired) but it is one device, one session, ND=16 test
  geometry only — **not** the 60-byte production geometry, which no image can
  currently decode.
* The pre-existing ucsim-vs-bench ≈1.6× timing discrepancy was not
  investigated; no `ucsim`/`sstm8` ran this phase.

### 13.6 Artifacts (§13)

| file | what |
|---|---|
| `data/captures_v23.json` | **new** — 54 real v2.3 captures, 18 patterns × 3 |
| `data/captures_v23_val.json` | **new** — 36 real v2.3 captures, 12 held-out × 3 |
| `recon/approaches/dev_prod/bench_v23_marker_ab.json` | **new** — the 288-capture same-session marker A/B (216 main + 72 held-out) with full metadata |
| `recon/approaches/dev_prod/v23bench_acq_variants.py` | **new** — variant acquisition (interleaved, scratch-output) |
| `recon/approaches/dev_prod/v23bench_score_variants.py` | **new** — per-variant scoring + paired McNemar |
| `recon/approaches/dev_prod/v23bench_score_v23_real.py` | **new** — delivered/refused/WRONG + cause histogram on the real corpora |
| `recon/approaches/dev_prod/v23bench_diag_recon.py` | **new** — lock/reconstruction quality diff, v2.2 vs v2.3 |

Bench state on exit (§13, 2026-09-07): `build/capture.ihx` **restored and
verified** — md5 `84955f77…`, reproduced byte-identically from source by the
clean rebuild; banner `RBARF-CAP 1` + `READY`, first byte **5.07 s** after
power-on. `build/rbarf_prod{,_verbose}.ihx` restored to the §12 v2.2 ledger
images (`e022cd75…` / `63629508…`); the over-size v2.3 link was discarded and
never flashed. **0 of the 3-failed-power-cycle budget consumed**; no
`ucsim`/`sstm8` run and no strays at exit; `data/captures_val.json` never
opened (atime still 2026-09-05 06:34:02).


Bench state on exit (§12 final gate, 2026-09-07): **`build/capture.ihx`
restored and verified** — md5 `84955f77…` (reproduced byte-identically from
source by the clean rebuild, never modified), banner `RBARF-CAP 1` +
`READY`, first byte at **5.07 s** after power-on. Flashing consumed **0 of
the 3-failed-power-cycle budget**; no `ucsim`/`sstm8` strays at exit;
`data/captures_val.json` never opened.

## 14. Protocol v2.3 close-out — trailer byte applied, terse image FITS (2026-09-07)

Owner-fixed inputs for this phase, implemented and not re-litigated:
`TRAILER_V23 = 9A 00 FF` (the trailer's `55` bit-period ruler traded for
a worst-case-**zeros** calibration probe) and **all three relaxations
stay in**. No bench access: everything below is a host or `ucsim`
measurement on the final sources.

### 14.1 Task 1 — the trailer byte, applied everywhere

`9A 55 FF` → **`9A 00 FF`**, sizing untouched (3 + N + 6 + 3; production
60 B = exactly 20 LEDs; test 28 B; 48 known marker bits; `NB` unchanged
at both geometries).

| file | change |
|---|---|
| `bench/patterns.py` | `TRAILER_V23`, its round-trip assert, the marker-jobs comment, the docstring |
| `bench/acquire.py` | `META_V23["trailer"]` (derived) + a new `marker_bytes` metadata field carrying the decision and its measurements, and flagging pre-decision corpora as compat |
| `bench/crc.py` | no change needed — it never hardcoded a marker |
| `recon/approaches/embedded_v2.py` | `TRL_V23`, the header block, `_selftest()` (now also asserts the 8 trailer bits are all 0) |
| `decode.c` | `TRL[3]`, `HTR[6]` (bit-reversed template → `FF 55 A6 / 59 00 FF`), file header |
| `decode_asm.s` | the marker template; `HT` and `HTR` **merged into one 6-byte table** (see §14.2) |
| `klipper/rbarf.cfg` | frame literal `154, 0, 255`, the framing block's rationale |
| `klipper/verify_macro.py` | trailer assert + the trailer lint |
| `docs/PROTOCOL.md` | marker-jobs table, the "what the trim cost" section **replaced by the resolved decision**, the "why 3+3" verdict, the worked-example frame, version history |
| `docs/ANIMATION_PROTOCOL.md` | framing paragraph + the marker-split bullet |
| `klipper/README.md`, `recon/EMBEDDED_V2_SPEC.md` | the pending-decision notes replaced with the decision |

The study files (`marker_split_study.py`, `analyze_marker_split.py`,
`v23bench_acq_variants.py`) are **left byte-exact** — they are the record
of which variants were measured, and `9A 55 FF` is the control every
paired test ran against.

Host self-tests, all green on the final sources:

| harness | result |
|---|---|
| `python3 bench/patterns.py` | 30 patterns round-trip, payload 22 B / frame 28 B, production 54/60 = 20 LEDs |
| `python3 bench/crc.py` | check value `0x29B1`, fa-table intact |
| `python3 recon/approaches/embedded_v2.py` | self-test OK (frame 28/60, `NB` 224/480 unchanged, syndromes distinct, parity gate exact, per-byte majority survives all 6 rotations, `T_MAX = 131`) |
| `python3 klipper/verify_macro.py` | **93 passed, 0 failed**; every wire frame byte-matches `bench/crc.py` + `bench/patterns.py` |

### 14.2 Task 2 — the pipeline tail is hand assembly again, and the terse image fits

Reproduced §13.1 exactly first (clean rebuild, `CHK_LEN=6`,
`--data-loc 0xF0`, `--code-loc 0x8068`): terse CODE ends `0xA252`
(**748 B over**), verbose `0xA296` (**816 B over**), guard fails both.

The tail — `crc16` / `syn16` / `rank3` / `ref_build` / `ch_match` /
`try_trial` / `chase_singles` / `chase_pairs` / `chase` /
`ws_decode_ex` — is now assembled in `decode_asm.s`. **`decode.c` keeps
every one of those functions**, fenced `#if !USE_ASM_DEC`, as the
host-parity reference the assembly is diffed against. No gate,
relaxation, counter, enumeration order or telemetry field was dropped.

Two implementation substitutions, both **value-identical** (the same
discipline as v2.2's syn8-by-`xtime` instead of its `XPOW` table):

1. **No syndrome table.** `decode.c` computes a trial residual as
   `r_base ^ syn16(k)` off the 48-entry `XP8` table (96 B of CONST).
   The assembly flips the trial's bits in `d_pp` and recomputes
   `crc16(d_pp[0..ND-1])`. CRC-16 is affine over GF(2) — so it is the
   **same 16-bit value**, and `embedded_v2._selftest()` asserts exactly
   that linearity — and a CHECK-bit flip cannot move the residual
   because the check block sits outside the CRC's byte range, so
   `decode.c`'s `touched` bookkeeping carries over unchanged. Drops
   `XP8` (96 B) and `syn16` (66 B in C). **Price: one 8·N-step CRC per
   trial** — measured below.
2. **Marker popcount and template.** A shift loop replaces the 16-B
   `POP4` nibble table, and `known_bit` now reads the **bit-reversed**
   `HTR` table instead of an MSB-first `HT` (wire bit `7-(t&7)` of a
   byte IS bit `t&7` of its reversal, so it shifts right where the old
   code shifted left) — one 6-byte table now serves both readers.

Chase temps **alias the refine/calibrate scratch** (`r_*` / `m_n` /
`m_d` / `m_r`): the chase runs strictly after `decide_pass`, and
`dec_eps_centi`'s `udiv32` runs only after `ws_decode_ex` returns — so
the whole tail costs **zero extra zero page**, the v2.2 rule. (One
ordering constraint came with it and is commented at the source: `z_out`
is loaded *after* `decide_pass`, because `seed`/`refine` own `m_n` while
they run.)

**Flash ledger — terse production image, `guard_prod.py` GREEN**

```
prod guard OK: REL end 0x9F50 <= CAPARM 0x9F66; _cap_loop 0x9FAF phase 0xF; flash free 37 B
```

| area | addr | size |
|---|---|---|
| HOME | `0x8068` | 7 B |
| GSINIT | `0x806F` | 35 B |
| GSFINAL | `0x8092` | 3 B |
| CONST | `0x8095` | 307 B |
| CODE | `0x81C8` | 7 560 B |
| **REL flash total** | `0x8068..0x9F4F` | **7 912 B of the 7 934 B budget** |
| VGAP1 (ABS, vector gap) | `0x8004` | 92 B of 96 |
| CAPARM0 (ABS, pinned) | `0x9F66` | 59 B |
| CAPLOOP0 (ABS, pinned) | `0x9FA1` | 80 B |

* **image occupied 8 151 / 8 192 B → 41 B free** (22 B contiguous below
  `CAPARM0`, 15 B above `CAPLOOP0`, 4 B of VGAP slack);
* `guard_prod.py`'s own metric: **37 B free**;
* **the ≥ 64 B goal is NOT met — 41 B, i.e. 23 B short.** Reported as
  measured, not rounded up.

Per-module deltas, C tail → asm tail:

| module | before | after | delta |
|---|---|---|---|
| `decode_prod.rel` CODE (the C tail) | 1 641 B | **0 B** | **−1 641** |
| `decode_prod.rel` CONST (`XP8` 96 + `HTR` 6 + `POP4` 16 + `g_*` 20) | 138 B | 28 B (`g_*` only, +8 B of new geometry consts) | **−110** |
| `decode_asm.rel` CODE | 4 441 B | 5 422 B | **+981** |
| **net REL flash** | | | **−770 B** |
| `decode_prod.rel` DATA (the `ch_*` statics went away) | 163 B | 155 B | −8 B RAM |

The asm tail itself is **986 B** (the +981 is net of the 6-byte `HT`
table the `HTR` merge removed from the streaming layer):

| routine | B | | routine | B |
|---|---:|---|---|---:|
| `chasez` (incl. inlined `ppout`, `setcmp`, `par16`) | 306 | | `refbld` | 85 |
| `_ws_decode_ex` (incl. inlined popcount) | 163 | | `cpair` | 51 |
| `rank3` | 118 | | `crcpp` | 44 |
| `fl1` (incl. inlined `ppflip`) | 43 | | `chmat` | 40 |
| `trial` | 39 | | `csing` | 32 |
| `putval` | 19 | | `flipij` / `confx` / `candk` / `chisd` | 12/12/10/6 |
| `HTR` table | 6 | | | |

**The pinned ABS capture block, extracted from the linked hex and
compared byte-for-byte against the §12 ledger image:**

| block | range | result |
|---|---|---|
| `CAPLOOP0` — `_cap_capture` `0x9FA1`, `_cap_loop` `0x9FAF` | `0x9FA1..0x9FF0` | **BYTE-IDENTICAL** (md5 `273e269f41…`) |
| `0x9FF1..0x9FFF` | | **BYTE-IDENTICAL** |
| `CAPARM0` (`_cap_arm`) | `0x9F66..0x9FA0` | 4 bytes differ — **all four are the low byte of the same operand address**, `MOV 0x034C,#2` vs the ledger's `MOV 0x0340,#2`: cap_arm's single RAM byte `s_arm` relocated because REL DATA shrank by 8 B. Instruction stream, lengths and cycle counts identical; the guard's 4 edge-detect `BTJT` polls all resolve to `_cap_loop` |

`_cap_loop` phase `0xF` ≡ `0x811F (mod 16)` — the address-phase pin
holds. `build/capture.ihx` reproduced byte-identically from source by
`make clean && make all`: md5 **`84955f77…`**, unchanged.

**The VERBOSE bench variant still does NOT fit: CODE ends `0x9F94`,
46 B over.** Its +68 B is `uart_put_nib`/`uart_put_hex` plus the 48-byte
hex line after every verified decode — the telemetry §12's gate was run
with. The over-size link was **discarded, never flashed** (no bench this
phase), and `build/rbarf_prod_verbose.ihx` is absent rather than left
lying around as if it were shippable. `make rbarf-prod` therefore still
exits non-zero after producing a green terse image.

**Residual gap, and the ordered levers.** 46 B for the verbose variant,
plus 23 B to reach the ≥ 64 B goal on the terse one — call it **~70 B**
to satisfy both. In cost order, cheapest first:

1. **`dec_info` into the ABS zero page — ~30 B, no feature or wire
   change.** Every one of the ~30 asm accesses and the C side's accesses
   drop one byte (short instead of long addressing). It is a *swap*, not
   growth: the ~23 B of calibration state that would move out to REL
   DATA is indexed-only (`(c_lo, x)` is 3 B either way), so total
   statics and the stack region are unchanged. Not taken here: it
   perturbs every DZP address in the file, and the phase's remaining
   budget went to re-proving the tail.
2. **Merge `csing`/`cpair` into one phase engine — ~10 B.** Measured by
   construction (78 B merged vs 83 B for the pair). Not taken: it
   touches the SS7.4 enumeration order, the single most delicate thing
   in the chase, for 10 B.
3. **Merge `chasez` into `ws_decode_ex` — ~3 B.**
4. **Gamma off-chip — ~300 B, but an owner-level WIRE decision** (the
   host pre-gammas the colours it already computes). `anim.c`'s CONST is
   exactly the 256-byte gamma-2.2 LUT plus `_apply_gamma` (39 B).
   `docs/APP_BUDGET.md` §8 lever 2, unchanged and still the biggest single
   zero-code-risk item.
5. **LED ordering on the host — ~150-250 B and ~48 B of stack**, also a
   wire decision (`docs/APP_BUDGET.md` "Beyond the cut list").
6. **Drop the built-in spin/rain/draw presets (~240 B) or sequence mode
   (~1 972 B)** — feature cuts, owner-level, and none was taken.

Levers 1-3 are ~43 B of pure size refactor inside the decoder and would
close the verbose gap on their own. **None of the guard checks was
bypassed and no feature was cut.**

**RAM ledger** (measured; `dev_prod/stackprobe_v23.py`, new — paints the
RAM below the live SP with a sentinel, runs one decode in `ucsim` to the
`sim_done` breakpoint and reads the low-water mark, plus the SP at the
`ws_decode_ex` entry so the decoder's own subtree separates from the
harness's frame):

| item | B |
|---|---|
| DZP0 (ABS zero page, `0x0001..0x00EE`) | 238 |
| REL DATA (`0x00F0..0x036A`) | 635 |
| SSEG (`0x036B`) | 1 |
| **statics, top of the last one at `0x036B`** | **876 of 1 024** |
| stack region `0x036C..0x03FF` | **148 B** (≥ 128 B allowance met, 20 B to spare) |
| `ws_decode_ex` subtree below its entry SP — **measured** over 6 cases incl. the two heaviest chases (55 trials / 72 comps) | **12 B** (static worst case 13 B: `chasez`→`cpair`→`trial`→push→`refbld`→`rank3`→`putval`) |
| decode path from reset SP: `call _main` 2 + main locals 4 + arg pushes 4 + `call _ws_decode_ex` 2 + subtree 12 | 24 B |
| **deepest path overall**: `call _main` 2 + main locals 4 + `call _render_tick` 2 + `render_tick`'s chain 98 (`anim_render`→`anim_sequence`→`seq_edge`→`lerp`→`__mulint`, CFG walk by `dev_fw/stackscan2.py`) | **106 B** |
| + TIM4 update ISR context, which can fire on top of any of them (PC 3 + Y 2 + X 2 + A 1 + CC 1; the ISR itself has no frame and makes no call) | 9 B |
| **peak stack** | **115 B** |
| **worst-case RAM** | **991 / 1 024 → 33 B margin**, 33 B of the 148 B stack region unused |

The asm tail is **shallower** than the C tail it replaced, and the
decode path is nowhere near the binding constraint — the animation
engine's `anim_sequence`→`seq_edge`→`lerp` chain is, at 4.4× the
decoder's depth. The host phase projected 27 B of headroom with the
compiled tail; the measured figure with the assembly is **33 B**, 8 B of
it from the `ch_*` statics disappearing and the rest from the shorter
call chain (12 B measured / 13 B static worst case, against the C tail's
projected `chase`→`try_trial`→`ref_build`→`rank3` frame chain).

`_main`'s row in `stackscan2.py`'s output (401/500 B) is **wrong and was
not used**: the analyser cannot see that the external asm
`ws_decode_ex` is callee-pops, so it never releases the 4 arg bytes
inside `main`'s loop. `main`'s frame is `sub sp,#4` plus the 4 pushed
args at that one call site; the anim chain, which is all C and which the
analyser does walk correctly, is what sets the peak.

### 14.3 Task 3 — re-proved on the final sources

**Host parity, `decode.c` ↔ `embedded_v2.py`** (`dev_prod/parity_v23.py`;
diffs emitted bytes, path, cause, `trials`, `alias_cmp`, `comps`,
`n_refs`, `ref_split`, `n_weak`, `n_tied`, `K`, `tau`, `violations`,
`infeasible`, `label_err`):

| corpus | mode | result |
|---|---|---|
| `captures_v21{,_val}.json` | CHK_LEN=3 (v2.1 compat) | 54/54, 36/36 |
| `captures_v22{,_val}.json` | CHK_LEN=4 (v2.2 compat) | 54/54, 36/36 |
| `captures_trim.json` | CHECK_EN=0 (legacy v2.0) | 96/96 |
| `fuzz_v23` ND=16 / ND=48 | v2.3 | 124/124, 149/149 |
| **total** | | **549/549 bit-identical — PASS** |

**ucsim, the SHIPPED `decode_asm.s`, at BOTH geometries**
(`dev_prod/ucsim_v23.py`; production-identical flags, `--data-loc 0xF0`,
`--code-loc 0x8068`, the harness's own VGAP link guard; every child under
`setsid timeout -k` with a `pkill` sweep):

| geometry | cases | result | decode ticks min / p50 / max | at 16 MHz |
|---|---|---|---|---|
| ND = 48 (production) | 24 | **24/24 bit-identical** | 4 141 357 / 4 460 899 / 4 811 722 | 258.8 / 278.8 / **300.7 ms** |
| ND = 16 (test) | 24 | **24/24 bit-identical** | 1 922 878 / 2 086 693 / 2 219 165 | 120.2 / 130.4 / **138.7 ms** |

Cases were picked one per distinct (path, cause) plus the heaviest
chases, so both runs include `direct`, `chase` and every refusal cause
R1-R8 that the fuzz corpus reaches, the 55-trial chases, the
`all 6 check bytes damaged` case (72 comparisons), `BOTH positions
SPLIT`, and marker damage in the first and last frame byte. **0 strays
at exit** on every run.

**Decode time is the one axis the asm tail made worse, and it is
quantified.** The two `trials = 55` production cases cost 4.81 M and
4.79 M ticks against ~4.2-4.4 M for `trials = 0` at comparable operating
points: **≈ 8.6 k ticks (0.54 ms) per chase trial**, of which the
recomputed 384-step CRC is ~4.5 k. That is the price of not carrying
`XP8`. Against the project's established silicon/ucsim ratio for the
decode mix (silicon ≈ 0.70 × ucsim's documented counts; §6.3/§7) the
worst production case projects to **≈ 210 ms on silicon** against
v2.2's measured 168 ms. **This is a Gate-phase item**: it must be
measured against the re-arm blind window and the 250 ms cadence on real
hardware, and if it does not hold, lever 1 above frees the flash to put
the syndrome table back.

**v2.3 fuzz set** (`dev_prod/fuzz_v23.py --report`; damage injected on
the wire, refusal-class biased — the classes the relaxations open):

| geometry | cases | emitted | correct | WRONG |
|---|---:|---:|---:|---:|
| ND = 16 | 124 | 67 | 67 | **0** |
| ND = 48 | 149 | 46 | 46 | **0** |
| **both** | **273** | **113** | **113** | **0 (0.0000 %)** |

Cause histograms cover `refuse_marker`, `refuse_infeasible`,
`refuse_labelerr`, `refuse_nocand`, `refuse_admit` and `refuse_chase` at
both geometries — ≥ 80 cases per geometry as required.

**WRONG-EMISSION RATE at the shipped constants**
(`dev_prod/wrong_emission_final.py`, no overrides — `embedded_v2.py`
exactly as `_configure(nd)` leaves it; plateau −2.5…+0.1 %, fast
0…+3 %, envelope ±8 %, × 12 arm phases over the measured 375-736 ns
spread, both geometries):

| geometry | decodes | emissions | WRONG | rate | 95 % upper |
|---|---:|---:|---:|---:|---:|
| ND = 16 | 70 200 | 34 700 | 5 | 0.0144 % | ≤ 0.0303 % |
| ND = 48 | 63 180 | 17 441 | 1 | 0.0057 % | ≤ 0.0272 % |
| **pooled** | **133 380** | **52 141** | **6** | **0.0115 %** | **≤ 0.0227 %** |

**Target ≤ 0.2 % — met, with the 95 % upper bound itself 8.8× inside
it.** Against the previous phase's run at `9A 55 FF` (6/49 567 =
0.0121 %): the same **6** wrong emissions, **+2 574 more emissions
(+5.2 %)**, so the trailer change bought delivery at zero cost in wrong
emissions. All six sit at `eps` ≥ +2.4 % — outside the delivery plateau
and outside the auto-trim band — and every one is an undetectable
CRC-16 codeword, as the fa-table math predicts. Chase-repaired
emissions: 6 885 of 52 141 (13.2 %); `comps` p50 1 / p90 2 / p99 21 /
max 129 against the `T_MAX = 131` bound.

**The existing real corpora, re-scored — and they are now a COMPAT
corpus.** `data/captures_v23{,_val}.json` were acquired by §13 with the
**old** trailer `9A 55 FF`; the shipped decoder's template says
`9A 00 FF`, so the wire and the template disagree in 4 of the 48 known
marker bits on every single capture. Scored with the host reference at
the shipped constants (`dev_prod/v23bench_score_v23_real.py`):

| corpus | n | delivered | refused | WRONG | §13.2 (matching old template) |
|---|---:|---:|---:|---:|---|
| `captures_v23.json` | 54 | **44 (81.5 %)** | 10 | **0** | 39 (72.2 %) |
| `captures_v23_val.json` | 36 | **27 (75.0 %)** | 9 | **0** | 22 (61.1 %) |

**Say it plainly: neither number measures the shipped wire.** They are
mismatched-marker decodes, and the fact that they came out *higher* than
§13.2's matching-template scores is not evidence for the trailer change
— the forced class-0 calibration samples land on `0x55`'s alternating
bits, four of the eight forced labels are wrong (`label_err` absorbs
them under `GATE_LABERR = 6`), and 90 captures cannot resolve a 9-point
move. The real-silicon evidence for `9A 00 FF` remains §13.3's
drift-interleaved paired A/B (71.1 % → 97.8 %, McNemar 25:1, p < 0.001).
**The Gate phase must acquire fresh corpora with `9A 00 FF`**;
`bench/acquire.py --set v23` now stamps the trailer and a compat note
into the metadata so this cannot be confused again.

### 14.4 What this phase did NOT establish

* **No silicon, at all.** No bench access by directive: no flash, no
  30-frame gate, no auto-trim band check, no Klipper end-to-end, no
  soak, and still **no on-silicon v2.3 wrong-emission rate**. Every
  number in §14.3 is host or `ucsim`.
* **The VERBOSE image does not exist.** §12's gate protocol needs it
  (it is what verifies emitted bytes against ground truth), so the Gate
  phase cannot start until one of the levers in §14.2 lands.
* **Decode time is projected, not measured.** ≈ 210 ms on silicon at the
  worst production chase is an extrapolation from a ratio measured on
  the v2.2 code mix; it is the number most likely to be wrong, and it
  interacts with the re-arm blind window.
* **`make rbarf-v21` does not link** — CODE ends `0x9FAD`, 12 B over
  `CAPLOOP`. This is **pre-existing and not caused by this phase**:
  `decode.c` has grown 605 B of CODE and 151 B of CONST since the v2.1
  bench build (compare `dev_fw/decode.rel`, 2026-09-06: CODE `0x152E`
  vs today's `0x178B` at the same `V21FLAGS`), and every edit this
  phase made to `decode.c` is either inside `#if USE_ASM_DEC`
  (not compiled at `V21FLAGS`) or inside `#if WIRE23` (not compiled at
  `CHK_LEN=3`), so the USE_ASM_DEC=0 output is byte-identical. The v2.1
  reproduction target needs its own link fix; it is not a shipped
  artifact.
* **`ucsim_bitexact.py --asmdec` is no longer applicable** at
  `CHK_LEN=3/4`: `decode_asm.s` is v2.3-geometry only (it already was
  before this phase — `known_bit` hardcodes 24 header bits). The v2.3
  on-target harness is `dev_prod/ucsim_v23.py`. The `--asmdec`-less
  (pure C) modes of `ucsim_bitexact.py` are unaffected.

### 14.5 Artifacts (§14)

| file | what |
|---|---|
| `decode_asm.s` | **+986 B** — the v2.3 pipeline tail in hand assembly; `HT`/`HTR` merged; header rewritten |
| `decode.c` | the tail fenced `#if !USE_ASM_DEC` (kept verbatim as the host-parity reference); `g_TIEE` / `g_PPB` / `g_PPE` / `g_TRB` added for the assembly; `TRL` / `HTR` = the new trailer |
| `recon/approaches/dev_prod/stackprobe_v23.py` | **new** — sentinel/low-water stack probe at the v2.3 production link, reporting both the total peak and the `ws_decode_ex` subtree |
| `recon/approaches/dev_prod/ucsim_v23.py` | exports `_ws_decode_ex` from the sim map (for the probe's entry-SP read) |
| `recon/approaches/dev_prod/wrong_emission_final.jsonl.gz` | re-run at the shipped constants incl. the new trailer |
| `guard_prod.py` | docstring: `CAPARM0`'s start is read from `_cap_arm`, not the stale `0x9F52` |
| `build/rbarf_prod.ihx` | **new v2.3 production image, 8 151/8 192 B, guard green** |
| `build/rbarf_prod_verbose.ihx` | **absent** — the 46-B-over link was discarded |

Bench state on exit (§14, 2026-09-07): **no bench access, no flash, no
power cycle** — 0 of the 3-failed-power-cycle budget consumed.
`build/capture.ihx` reproduced byte-identically from source by
`make clean && make all` and left in place, md5 **`84955f77…`**. No
`sstm8` run; `ucsim_stm8` ran only under `setsid timeout -k` with a
`pkill` sweep after every batch and **0 strays at exit** (asserted by
each harness). `data/captures_val.json` never opened.

---

## 15. Protocol v2.3 SILICON GATE — correctness closed, delivery short (2026-09-07)

First bench session in which a **v2.3 production image ran on silicon**.
The two owner decisions (trailer probe `9A 00 FF`, relaxations A/B kept)
were implemented and not re-litigated.

| criterion | required | measured | |
|---|---|---|---|
| WRONG EMISSIONS | **0** | **0** of 1 634 accepted emissions | ✅ **PASS** |
| MCU resets | 0 | **0** over 3 711 frames | ✅ PASS |
| auto-trim parks in [−1.6 %, −0.4 %] | all | **1 634 / 1 634** verified decodes | ✅ PASS |
| fresh real corpora (host reference) | beat v2.2's 93.3 % | **97.78 %** (88/90) | ✅ PASS |
| Klipper end-to-end | beat v2.2's 39/51 | **44/51 (86.3 %)**, 0 wrong | ✅ PASS |
| 30-frame gate delivery | **≥ 28/30** | **26/30 cold, 22/30 warm** | ❌ **FAIL** |

**VERDICT: NO-GO on delivery. Correctness is closed.**

### 15.0 Unblocking the gate — the VERBOSE image now fits (46 B recovered)

§14.4 left the gate blocked: the gate protocol needs the VERBOSE image
(the `V:` line is the only thing that makes a wrong emission observable)
and that link ended `0x9F94`, **46 B past `CAPARM0`**, i.e. on top of the
cycle-calibrated capture block.  None of §14.2's levers 1–3 were taken.
A cheaper, decoder-free lever closed it instead:

* In VERBOSE builds only, eps is emitted as **`x` + 4 hex digits** (raw
  big-endian two's-complement int16, same centi-percent units) using the
  hex printer the `V:` line already carries, instead of the decimal
  printer.  `uart_put_i16` (**84 B**) and its power-of-ten table
  (**8 B**) drop out; `uart_put_eps` costs **6 B**.
* Net: verbose REL end **`0x9F4C`**, **4 B below the terse image's**
  `0x9F50`.  `guard_prod.py` green on both maps; all four `cap_arm`
  edge-detect BTJT polls found and resolving to `_cap_loop`.

| image | REL end | guard | image bytes | md5 |
|---|---|---|---:|---|
| `build/rbarf_prod.ihx` (**shipping, terse**) | `0x9F50` | OK, 37 B free | 8 151 / 8 192 | `b79f4324ee0005b4b3f642d6c4a332c4` — **byte-identical to the §14 ledger** |
| `build/rbarf_prod_verbose.ihx` (**bench, flashed**) | `0x9F4C` | OK, 41 B free | 8 147 / 8 192 | `7dec475ab30e195cf678784c2a3af30f` |
| `build/capture.ihx` | — | — | 352 | `84955f771ef8ad41a36fc16187afca38` — reproduced from source, restored at exit |

The **shipping image did not change**: the only source edit is inside
`#if VERBOSE` / `#else` in `rbarf_prod.c`, and the terse md5 is the
ledgered one.  The decoder, the wire, RAM layout and the capture loop are
untouched — the pinned ABS block is **byte-identical in both images and
to the §12/§14 ledger**: `CAPLOOP0 0x9FA1..0x9FF0` md5
`273e269f41527530fd4a0261eb70f8a0`, `0x9FF1..0x9FFF` md5
`9ddd02276e5c30436e3b530eba05ad6a`, `0x9F66..0x9FFF` md5
`c90a5bf952912e6c04606dc3c85290dc`, **0 differing bytes**.  (§14's
report of 4 differing bytes in `CAPARM0` versus the *§12* image stands —
that was the `s_arm` operand relocation; terse and verbose *of this
build* are identical throughout the block.)

`bench/epsfmt.py` (new, self-tested over the full int16 range) parses
both encodings; `drive_prod.py`, `test_klipper_macro.py` and
`rate_spot.py` use it, so **every pre-v2.3 decimal bench log still
parses**.  The `x` sentinel makes the two formats unambiguous.

The **≥ 64 B free goal is still NOT met** (41 B verbose / 37 B terse) and
§14.2's levers 1–6 remain untaken and unchanged in their ordering.

### 15.1 Task 1 — fresh v2.3 corpora, acquired with `9A 00 FF`

`bench/acquire.py --set v23 --reps 3` and `--set v23val --reps 3` with the
restored `capture.ihx`.  Both write `trailer = 9A00FF` and the
`marker_bytes` decision note into their metadata.  The §13 corpora are
preserved as `data/captures_v23_compat9A55FF.json` /
`captures_v23_val_compat9A55FF.json` — they are the mismatched-marker
COMPAT corpora and must not be quoted as v2.3 wire results.

Scored by the Python reference at the **shipped** constants, no overrides
(`dev_prod/v23bench_score_v23_real.py`):

| corpus | wire | delivered | refused (cause) | WRONG |
|---|---|---|---|---:|
| `captures_v23.json` (fresh) | `9A 00 FF` | **53/54 = 98.15 %** | 1 × `refuse_chase` | **0** |
| `captures_v23_val.json` (fresh) | `9A 00 FF` | **35/36 = 97.22 %** | 1 × `refuse_nocand` | **0** |
| **pooled** | | **88/90 = 97.78 %** | 1 R8 + 1 R6 | **0** |
| v2.2 corpora (§11) | `9A 55 00 FF` | 84/90 = 93.3 % | | 0 |
| compat corpora (§14) | `9A 55 FF` | 71/90 = 78.9 % | 14 × chase, 5 × nocand | 0 |

**97.78 % is the predicted 97.8 %, hit on the nose**, and it beats v2.2's
93.3 % by 4.4 points.  Paths: 82 direct, 6 chase-repaired.

Paired by `(pattern, rep)` cell across the compat and fresh corpora
(same 90 cells, same decoder, only the wire's trailer byte differs):
**both delivered 69, fresh-only 19, compat-only 2, neither 0** →
McNemar **19:2**, χ²(cc) = **12.19**, exact two-sided binomial
**p = 2.2 × 10⁻⁴**.  *Caveat:* these are two different acquisition
sessions, so the pairing is by cell and not by physical capture; it
conflates the trailer with any between-session drift.  §13.3's
drift-interleaved A/B (71.1 % → 97.8 %, 25:1, p < 0.001) remains the
cleaner causal evidence.  Both agree in direction and magnitude.

### 15.2 Task 2 — flashed, and the auto-trim parks in band with zero steps

`guard_prod.py` green on **both** maps immediately before the flash;
`build/rbarf_prod_verbose.ihx` written on the **first** power cycle
(8 177 B).  Banner `RBARF-P 1` at **5.05–5.06 s** after power-on in every
session — SWIM quiet window respected.

| run | verified decodes | mean eps | range | in band [−1.6, −0.4] |
|---|---:|---:|---|---:|
| gate cold | 26 | **−1.102 %** | −1.13 … −1.08 | **26/26** |
| 15-min soak | 1 542 | **−1.017 %** | −1.08 … −0.83 | **1 542/1 542** |
| gate warm (post-soak) | 22 | **−1.029 %** | −1.06 … −1.00 | **22/22** |
| Klipper end-to-end | 44 | **−0.940 %** | −0.99 … −0.89 | **44/44** |
| **total** | **1 634** | | | **1 634/1 634** |

σ = **0.039 pp** over the soak.  `trim_v` never left code 0 — the
retargeted deadband makes the factory trim a fixed point, exactly as
§12.1 designed.  Warm drift is **small and in the safe direction**: the
soak's first quarter means −0.975 % and its last quarter −1.024 %
(**−0.049 pp**), and cold → warm gate is +0.073 pp.  Headroom to the
**+0.1 % emit-gate cliff is ≈ 1.13 pp** at every operating point
observed.

### 15.3 Task 3 — the 30-frame gate, cold and after a 15-minute warm soak

| run | delivered | direct | chase | refused | no-report | **WRONG** | resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| **cold** | **26/30 (86.7 %)** | 24 | 2 | 4 | 0 | **0** | 0 |
| **warm** (post 15-min soak) | **22/30 (73.3 %)** | 22 | 0 | 7 | 1 | **0** | 0 |
| pooled | **48/60 (80.0 %)** | 46 | 2 | 11 | 1 | **0** | 0 |

**The ≥ 28/30 bar is not met in either run.**  This is the same
pre-existing delivery margin §12.7 measured for the code-0 operating
point (27/30 cold, 25/30 warm, pooled 83.3 %); v2.3 lands 3.3 points
lower pooled, inside the ±9 pp width of a 30-frame binomial CI, so the
two are **not distinguishable at this sample size** — v2.3 has neither
demonstrably fixed nor demonstrably worsened live delivery.

**REFUSAL-CAUSE HISTOGRAM — and it overturns §13.4's finding.**  The
previous phase concluded every remaining refusal was `R6` (no weak
candidate admitted) or `R8` (chase exhausted), i.e. that the residual
loss was *confidence calibration, not search width*.  On silicon it is
neither:

| cause | cold | warm | soak | Klipper | total | share |
|---|---:|---:|---:|---:|---:|---:|
| `R3` infeasible | 1 | 4 | 222 | 5 | **232** | **43.8 %** |
| `R1` lock | 1 | 1 | 163 | 1 | **166** | **31.3 %** |
| `R6` nocand | 2 | 1 | 55 | 0 | **58** | 10.9 % |
| `R8` chase | 0 | 0 | 42 | 1 | **43** | 8.1 % |
| `R4` labelerr | 0 | 1 | 16 | 0 | 17 | 3.2 % |
| `R2` marker | 0 | 0 | 8 | 0 | 8 | 1.5 % |
| `R7` admit | 0 | 0 | 6 | 0 | 6 | 1.1 % |
| **total** | 4 | 7 | 512 | 7 | **530** | |

**The R6/R8 split asked for is 58 : 43 — together only 19.0 % of
refusals.**  Three quarters of the loss (`R1` + `R3` = 75.1 %) sits in
the **capture front end**, not in the decoder's confidence or its search
width.  §13 established that `R1` refusals are **partial bursts**
(102–302 of ~480 pulses) from capture-arm mis-triggers, which no clock
window can admit; `R3` (feasibility gate) is very plausibly the same
pathology presenting one stage later, and its share rose from 4.2 % of
§12's gate refusals to 43.8 % here.  **This session cannot attribute it:
no raw captures were dumped**, so the reversal is a measurement, not yet
a diagnosis.  It does redirect the next lever: the deferred **lock-retry**
(margin report fix #2) targets exactly this, and the R6/R8 confidence
work is worth ~19 % of the loss at most.

Note also that the corpora deliver 97.8 % while the live gate delivers
80 %.  The corpus path removes precisely the front-end losses — a corpus
capture exists only when `capture.ihx` armed and dumped successfully —
which is consistent with the histogram above and with the ≈ 28/30 live
ceiling §12.7 derived.

### 15.4 Task 5 — soak: 3 600 frames at a strict 250 ms cadence

| | |
|---|---|
| duration / cadence | **901.5 s**, hard 250 ms schedule |
| frames sent | **3 600** (single transmission each) |
| reports (`D:`) | 2 054 (57.1 % — the VERBOSE image's own blind window: `D:` + the 98-char `V:` line ≈ 287 ms > 250 ms, so roughly every other frame arrives unarmed; a property of the **bench** image, not the shipping terse one) |
| **delivered CORRECT** | **1 542** = 75.1 % of frames actually captured |
| **WRONG emissions** | **0** |
| unattributable | **0** |
| refused | 512 (histogram above) |
| **MCU resets** | **0** |
| eps stability | 1 542/1 542 in band, mean −1.017 %, σ 0.039 pp, drift −0.049 pp over the session |

Scoring is the §12.6 double check: the emitted payload must match a known
frame **and** its temporal attribution; a payload matching a known frame
but not the attributed one is counted separately (0 occurred).
§12.6's comparable figure was 1 612/1 981 = 81.4 %.

### 15.5 Task 4 — Klipper end-to-end

`bench/test_klipper_macro.py --bench-is-free --reps 3`, all 17 cases,
60-byte `frame` variant.  All 17 render **byte-exact** against
`klipper/verify_macro.py` ground truth first, with v2.3 framing
(`FF AA 65` … `9A 00 FF`) and CRC-16 × 3.

| run | delivered | catastrophic |
|---|---:|---:|
| §11.4 baseline (code 7, warm, v2.2) | 5/51 (9.8 %) | **2** |
| §12.5 (code 0, v2.2) | 39/51 (76.5 %) | 0 |
| **this run (v2.3, warm)** | **44/51 (86.3 %)** | **0** |

41 direct + 3 chase-repaired, 7 refused (`R3` × 5, `R1` × 1, `R8` × 1),
0 protocol errors, 0 silent.  13 of 17 cases go 3/3; the worst is
`preset_rain_rev` at 1/3.  **Both frames that produced the only two
catastrophic emissions in this project's history** (`preset_rain`,
`preset_rain_rev`) ran clean: `preset_rain` 3/3 correct, and every
`preset_rain_rev` emission correct.  This was run warm, immediately after
the soak — the harsher condition, and still +5 frames over v2.2.

### 15.6 Wrong emissions — the number that matters

| run | frames on the wire | accepted emissions | **WRONG** |
|---|---:|---:|---:|
| gate cold | 30 | 26 | **0** |
| 15-min soak | 3 600 | 1 542 | **0** |
| gate warm | 30 | 22 | **0** |
| Klipper 17 × 3 | 51 | 44 | **0** |
| **total** | **3 711** | **1 634** | **0** |

Plus, host-side at the shipped constants: 0 of 88 emissions on the fresh
real corpora, 0 of 113 on the 273-case adversarial fuzz set, and the
§14.3 synthetic figure of 6 wrong in 52 141 emissions
(0.0115 %, one-sided 95 % upper bound 0.0227 %, target ≤ 0.2 %).

**This is the first on-silicon v2.3 wrong-emission measurement, and it is
zero.**  The 95 % one-sided upper bound from 1 634 clean emissions is
0.18 % — which is *just* inside the ≤ 0.2 % target, so silicon alone does
not yet certify the target; the synthetic bound is what carries it.

### 15.7 Decode time — the flagged risk did not materialise

§14.2 projected ≈ 210 ms on silicon at the worst production chase
(55 trials), against v2.2's measured 168 ms, because the assembly
recomputes a 384-step CRC per chase trial instead of carrying the 96-B
`XP8` syndrome table.  Measured, from the host-side latency decomposition
(`latency − frame tx − capture window − UART transit`):

| run | min | mean | max |
|---|---:|---:|---:|
| gate cold (delivered) | 164.8 | 165.3 | **172.9 ms** |
| gate warm (delivered) | ~164 | 164.8 | **172.6 ms** |

Worst observed **172.9 ms**, i.e. **+4.9 ms (2.9 %) over v2.2's 168 ms**,
not +42 ms.  End-to-end latency (frame start → `D:` line complete) peaked
at **185.7 ms**, comfortably inside the 250 ms cadence, and the re-arm
blind window is unchanged in character.  **Caveat:** the bench never
produced a deep chase — only 2 chase-repaired frames in the cold gate and
3 in Klipper — so the *worst-case* 55-trial chase remains unmeasured on
silicon.  At ~8.6 k ticks (0.54 ms) per trial, 55 trials over the
observed baseline projects to ~195 ms, still inside the cadence.  **Lever 1
(`dec_info` to the ABS zero page, ~30 B) is not needed for time**, and the
syndrome table need not come back.

### 15.8 What this session did NOT establish

* **The ≥ 28/30 delivery bar is not met** and this session did not close
  it.  26/30 cold, 22/30 warm.
* **The R1/R3 reversal is not diagnosed.**  No raw captures were dumped,
  so the 232 `R3` refusals cannot be attributed to partial bursts (the
  hypothesis) rather than to genuine clock-fit failures.  A dump-enabled
  run is the next diagnostic step, and it is what the lock-retry fix
  needs in order to be sized.
* **No stack canary on silicon.**  It is **not feasible with the shipping
  firmware**: `rbarf_prod.c` sets `CFG_GCR = 0x01` (SWIM off) after the
  5 s window to free pin 8 for UART, so `stm8flash -s ram -r` cannot read
  the stack region after a soak, and a power cycle destroys it.
  Observing it needs a diagnostic image that paints a sentinel and
  reports the low-water mark over UART (§7's approach) — a new image, a
  new flash and its own validation, which this session did not have the
  budget for.  What stands instead: `dev_prod/stackprobe_v23.py`'s
  ucsim measurement (peak 115 B, worst-case RAM 991/1 024, **33 B
  margin**), §7.1's *silicon* canary on the v2.2 image (peak 97–113 B,
  stack ruled out) — which still bounds this image, because the change
  moved only the **decode subtree** (12 B measured, 4.4× shallower than
  the anim chain that sets the peak) while `anim.c`, `tick.c` and
  `ws2812_out.c` were not touched this phase — and **0 resets over
  3 711 frames**.
* **The WS2812 output on pin 5 has still never been observed by any
  instrument in this project.**  Every "delivered" verdict in this
  section means *the decoder recovered the right 48 bytes and said so on
  the UART*.  That the LEDs are then driven correctly rests entirely on
  `anim.c` + `ws2812_out.c` equivalence proofs (§5, 25.9 M cases) and on
  nothing electrical.
* **One unit, one temperature profile.**  All of it is the same
  STM8S001J3 at ≈ −1.07 % factory trim, room temperature warming to
  whatever 15 minutes of self-heating gives.  Relaxations A and B are
  kept as margin for other units and temperatures and, as in every
  previous phase, **yielded exactly zero here** — 0 refusals recovered by
  either.
* **`make rbarf-v21` still does not link** (pre-existing, §14.4), and the
  v2.3 `--asmdec` restriction on `ucsim_bitexact.py` is unchanged.

### 15.9 Verdict and the one thing to do next

**NO-GO**, on delivery alone.

Everything that protects the user is closed: **0 wrong emissions in
1 634 silicon emissions and 0 in every host corpus**, 0 resets in 3 711
frames, the auto-trim parked in band 1 634/1 634 times with a measured
warm drift of −0.05 pp, the Klipper path at 86.3 % with the two historic
false-accept frames clean, and the fresh corpora at **97.78 %** — the
predicted number, 4.4 points over v2.2.  The trailer decision is
vindicated on real silicon twice over.

What blocks GO is live delivery, 26/30 cold and 22/30 warm against
≥ 28/30, and the histogram says where to spend the next phase: **75 % of
refusals are `R1` + `R3`, in the capture front end, not in the decoder.**
The single highest-value next action is a **dump-enabled bench run** that
records the raw capture behind every `R3`, to confirm the partial-burst
hypothesis and size the deferred lock-retry.  Decoder-confidence work
(`R6`/`R8`) is worth at most 19 % of the loss and should wait.

### 15.10 Artifacts (§15)

| file | what |
|---|---|
| `rbarf_prod.c` | `uart_put_eps` (VERBOSE-only hex eps, 6 B) replaces the 92 B decimal printer in verbose builds; `uart_put_i16` fenced `#else`. **Terse output unchanged** |
| `bench/epsfmt.py` | **new** — `parse_eps`, accepts decimal and `x<4hex>`; self-tested over the full int16 range |
| `bench/drive_prod.py` | v2.3 framing (`HEADER_V23`/`TRAILER_V23`, `build_payload_v23`, 3+48+6+3) and `parse_eps` |
| `bench/rate_spot.py` | same v2.3 framing + `parse_eps` update |
| `bench/test_klipper_macro.py` | `parse_eps` |
| `recon/approaches/dev_prod/v23gate_soak.py` | **new** — one-session soak (strict cadence, double-checked attribution) + warm 30-frame gate |
| `recon/approaches/dev_prod/bench_v23_gate_cold.json` | cold gate, 30 frames |
| `recon/approaches/dev_prod/bench_v23_soak_warm.json` | 15-min soak + warm gate |
| `recon/approaches/dev_prod/bench_v23_klipper.json` | Klipper 17 × 3 |
| `data/captures_v23.json`, `data/captures_v23_val.json` | **fresh, `9A 00 FF`** — the first real v2.3 wire corpora |
| `data/captures_v23_compat9A55FF.json`, `data/captures_v23_val_compat9A55FF.json` | the §13 compat corpora, preserved |
| `build/rbarf_prod_verbose.ihx` | **exists again**, guard green, `7dec475a…` |

Bench state on exit (§15, 2026-09-07): `capture.ihx` reflashed from the
byte-identical rebuild (`84955f77…`) and verified live — `RBARF-CAP 1` /
`READY` with the first byte at **5.06 s** after power-on.  Every flash
succeeded on its **first** attempt: **0 of the 3-failed-power-cycle
budget consumed**.  `guard_prod.py` run after every relink and before
every flash, never bypassed.  No `sstm8`, no `ucsim_stm8` this session
(so no strays possible); every bench child ran under `setsid timeout -k`.
`data/captures_val.json` **never opened** — atime still
2026-09-05 06:34:02.

---

## 16. CAPTURE FRONT-END FIX + RE-GATE (2026-09-07) — **GO**

§15 closed correctness and left delivery short: **26/30 cold, 22/30
warm**, with `R3` infeasible (43.8 %) and `R1` lock (31.3 %) making up
**75 %** of 530 refusals, i.e. the loss was in the capture front end, not
in the decoder.  `ARM_INVESTIGATION.md` then proved the mechanism: the
arm's trigger phase `t0` crossing a hard geometric cliff at **681 ns**
(slot 2 of the 40-cycle sample comb leaving the first WS2812 bit period),
plus the 100 Hz render's 5.56 %-duty capture hole.  This section is the
fix and its gate.

### 16.1 What changed — three edits, one byte of flash

| file | change | flash | touches calibrated timing? |
|---|---|---:|---|
| `cap_arm.s` | **FIX 2a** — the four edge-detect polls now branch to **`_cap_loop+1`** (0x9FB0, the R0 poll) instead of `_cap_loop` (0x9FAF, the loop-top `rlc a`). One cycle cheaper, and the taken branch lands on the FIRST byte of a 32-bit flash word instead of the last byte of one, which is where the arm's ~2 cy of fixed excess over `capture.ihx`'s fall-through entry lived | 0 B | **yes, the arm.** `CAPLOOP` byte-identical |
| `cap_arm.s` | **FIX 2b** — `dec a` moved between polls 3 and 4: comb gaps 2/2/3/4 cy instead of 2/2/2/5, worst-case latency 5 → 4 cy, same instruction count, same nominal 11-cy period (measured 14 cy with fetch stalls; the arm window went 1.68 → 1.56 ms) | 0 B | **yes, the arm** |
| `cap_arm.s` | **FIX 3** — the wait-low phase now needs **8 consecutive low polls (~2.5 µs = 2 bit periods, 2.9 × the longest in-frame low)** before the edge window opens, instead of a single low sample; a busy line returns `A = 0` after 8 retries and the caller re-arms | **+1 B** | **yes, the arm** |
| `rbarf_prod.c` | **FIX 2 (render)** — `RENDER_MS` 10 → **40**: 100 Hz → 25 Hz, render duty 5.56 % → **1.39 %** | 0 B | no |
| `guard_prod.py` | the poll check now pins the target to `_cap_loop+1`, asserts the byte there is `0x72` (a BTJT opcode — an instruction boundary, the check that would have caught §7.4's ILLOPF directly) and the byte at `_cap_loop` is `0x49` (`rlc a`), and requires the idle gate's own BTJT to branch inside cap_arm | — | — |

`decode.c`, `decode_asm.s`, `caploop.s`, `cap_code.s`, `decode.h`,
`anim.c`, `ws2812_out.c`, `tick.c`, `vectors_prod.s`, `Makefile`,
`docs/PROTOCOL.md`, `klipper/rbarf.cfg` and `klipper/verify_macro.py` are
**unchanged** (md5s recorded in `dev_fe/`).  **No correctness gate was
relaxed** — no decoder constant moved at all.  The only bench edit is a
comment: `bench/drive_prod.py`'s docstring described a 100 Hz render.
Two investigation tools gained optional flags with unchanged defaults
(`dev_prod/ucsim_v23.py --b0`, `dev_prod/wrong_emission_final.py
--t0-lo/--t0-hi`).

**The §6 fallbacks were not needed.** Unrolling the poll loop 4 → 16
(+60 B into a 100 %-full area, requiring a decoder size lever first) and
the `CAPARM_ORG` re-phasing sweep are both superseded by FIX 2a, which
removes the excess at its actual source — the branch destination's word
alignment, not the poll loop's address phase.  **No size lever was
spent**: the terse image has **36 B free** below `CAPARM` and the verbose
image **40 B** (`CAPARM` grew 1 B downward, 0x9F66 → 0x9F65).

**Pinning, verified in the linked images** (`dev_arm/absmd5.py`):

| block | md5 | |
|---|---|---|
| `CAPLOOP` 0x9FA1..0x9FF0 | `273e269f41527530fd4a0261eb70f8a0` | **byte-identical to the §15.0 ledger** |
| 0x9FF1..0x9FFF | `9ddd02276e5c30436e3b530eba05ad6a` | **byte-identical** |
| `CAPARM` 0x9F65..0x9FA0 (new) | `239d708c5eea8b0008272f058ae058e2` | the fix; 60 B, flush to `_cap_capture` |
| 0x9F65..0x9FFF (new ledger line) | `1ebfc7b3a8a0b567dbd6b07486228e47` | terse and verbose identical here |

`prod guard OK: REL end 0x9F50 <= CAPARM 0x9F65; _cap_loop 0x9FAF phase
0xF; flash free 36 B` (terse) and `REL end 0x9F4C … 40 B` (verbose).
New image md5s: `rbarf_prod.ihx` **`32e8057d1896417e6580f0e1e8155cec`**,
`rbarf_prod_verbose.ihx` **`6871bd7e25eec8ea10b4c099cc008785`**;
`capture.ihx` untouched at `84955f771ef8ad41a36fc16187afca38`.

### 16.2 Why skipping the loop-top `rlc a` is safe — proven twice

The instruction at `_cap_loop` deposits the PREVIOUS iteration's BS1
sample from C.  On the first iteration there is no previous iteration: it
writes capture **byte 0 bits 7..6**, which `cap_code.s` documents as
garbage, which `decode.c`'s scanner cannot reach (loop *i* takes slots
6,7 from byte *i*+1), and which the OLD arm already filled with C-junk.

| proof | result |
|---|---|
| `dev_fe/b0_invariance.py` — every capture in all 10 corpora, the 177 real production dumps from the arm phase and the 149 `fuzz_v23` ND=48 cases, each decoded 4× with byte 0 bits 7..6 forced to 00/01/10/11, comparing emitted bytes and all 16 `dec_info` fields | **836 captures × 4 decodes, 0 mismatches** |
| `dev_prod/ucsim_v23.py --nd 48 --b0 C0` — the SHIPPED `decode_asm.s` in ucsim with those bits forced to 11, expectation = the CLEAN reference decode | **24/24 bit-identical** |

Slot 0 **is** the R0 poll, so the fitted slot offsets, the `W_CY[]`
branch costs and the 40-cycle period are untouched — only `t0` moves.

### 16.3 `t0` on silicon — the cliff is cleared

Measured with the arm phase's diagnostic image (`dev_arm/rbarf_arm.c`,
which differs from the shipping arm in exactly the 4 `s_arm` operand
bytes; all four polls byte-identical), 299 captures over two 150-frame
runs:

| | old arm (448 captures) | **new arm (299 captures)** |
|---|---|---|
| fitted `t0`, complete bursts min / p10 / p50 / p90 / max | 288 / 369 / **472** / 680 / **862 ns** | **102 / 240 / 340 / 509 / 650 ns** |
| above the 681 ns cliff | **9.7 %** | **0 of 79 dumped complete bursts** |
| complete-burst `R3` | 42 dumps | **0** |

The distribution now lies wholly inside the **0…620 ns** band that the
§3 host sweep shows is not merely R3-free but content-optimal.  Predicted
3 cy of shift; measured **-2.1 cy at the median, -3.4 cy at the max**.

### 16.4 Re-proof — nothing in the decoder moved, and it is re-proved anyway

| proof | tool | result | vs §14.3 |
|---|---|---|---|
| host parity `decode.c` ↔ `embedded_v2.py` over `captures_v21{,_val}` (CHK3), `captures_v22{,_val}` (CHK4), `captures_trim` (CHECK_EN=0), `fuzz_v23` ND=16/48 | `dev_prod/parity_v23.py` | **549/549 bit-identical** | identical |
| ucsim, the SHIPPED `decode_asm.s`, production geometry | `dev_prod/ucsim_v23.py --nd 48` | **24/24 bit-identical**; ticks min 4 141 357 / p50 4 460 899 / max 4 811 722 | identical |
| ucsim, test geometry | `--nd 16` | **24/24 bit-identical** | identical |
| ucsim, production geometry, **capture byte 0 bits 7..6 forced to 11** against the CLEAN expectation | `--nd 48 --b0 C0` | **24/24 bit-identical** | new — the FIX 2a on-target proof |
| byte-0 invariance across every corpus + real dumps + fuzz | `dev_fe/b0_invariance.py` | **836 captures × 4, 0 mismatches** | new |
| v2.3 fuzz set, damage on the wire, refusal-class biased | `dev_prod/fuzz_v23.py --report` | **273 cases, 113 emitted, 113 correct, 0 WRONG** | identical |
| the fresh real v2.3 corpora, host reference at the shipped constants | `dev_prod/v23bench_score_v23_real.py` | `captures_v23` **53/54 (98.15 %)**, `captures_v23_val` **35/36 (97.22 %)** = **88/90 (97.78 %)**, **0 WRONG** | identical (the decoder did not move) |

**WRONG-EMISSION RATE at the shipped constants, re-run over the NEW arm's
measured `t0` spread** (`dev_prod/wrong_emission_final.py --t0-lo 102
--t0-hi 650`; 12 arm phases, plateau/fast/envelope eps sets, both
geometries — the tool gained the two CLI options, its defaults are
unchanged):

| geometry | decodes | emissions | WRONG | rate | 95 % upper |
|---|---:|---:|---:|---:|---:|
| ND = 48 (production) | 63 180 | 20 930 | **0** | 0.0000 % | ≤ 0.0143 % |
| ND = 16 (test) | 70 200 | 42 774 | 3 | 0.0070 % | ≤ 0.0181 % |
| **pooled** | **133 380** | **63 704** | **3** | **0.0047 %** | **≤ 0.0122 %** |

**Target ≤ 0.2 %: met, with the 95 % upper bound 16 × inside it.**
Against §14.3 at the old 375-736 ns spread (52 141 emissions, 6 wrong,
0.0115 %, ≤ 0.0227 %): the front-end fix bought **+11 563 emissions
(+22.2 %)** and **halved the wrong count**, because the phases it
removed were the ones that pushed frames into the chase.  All three
residual wrong emissions are the same character as §14.3's six — one
payload (`val_vprime`), ND = 16 only, at **eps +2.40 % and +2.55 %**,
i.e. far outside the delivery plateau (-2.5…+0.1 %) and far outside the
auto-trim band (-1.6…-0.4 %), every one an undetectable CRC-16 codeword
reached through a 40-43-trial chase.  `comps` max **130** against the
`T_MAX = 131` bound.

### 16.5 THE 30-FRAME GATE — cold and warm

`bench/drive_prod.py --reps 3` on the VERBOSE image, 10 production
payloads × 3, each on the wire exactly once, scored against ground truth
from the `V:` line.  Warm = straight after the 15-minute soak in §16.6.

| run | delivered | direct | chase | refused | no-report | **WRONG** | resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| §15.3 cold (old arm) | 26/30 (86.7 %) | 24 | 2 | 4 | 0 | 0 | 0 |
| §15.3 warm (old arm) | 22/30 (73.3 %) | 22 | 0 | 7 | 1 | 0 | 0 |
| **this cold** | **28/30 (93.3 %)** | 27 | 1 | 2 | **0** | **0** | **0** |
| **this warm** | **29/30 (96.7 %)** | 28 | 1 | 1 | **0** | **0** | **0** |
| **pooled** | **57/60 (95.0 %)** | 55 | 2 | 3 | **0** | **0** | **0** |

**The ≥ 28/30 delivery bar is MET in both conditions — 28/30 cold and
29/30 warm — and WRONG EMISSIONS ARE ZERO, the headline axis.**  §15's
warm run was the weak one (22/30); it is now the STRONGER of the two,
which is what the fix predicts: the cliff moves only 6 ns between
eps 0 and -1.07 %, so a warmer die no longer walks the trigger phase
into it.

**REFUSAL-CAUSE HISTOGRAM — the front end is gone.**  §15.3's question
was whether the fix moves `R1`/`R3`; pooled over every production frame
this phase put on the wire (cold gate, warm gate, 15-min soak, Klipper
e2e):

| cause | §15 share of 530 refusals | **this phase** | share |
|---|---:|---:|---:|
| `R3` infeasible | **232 (43.8 %)** | **3** | **3.1 %** |
| `R1` lock | **166 (31.3 %)** | **0** | **0 %** |
| `R6` nocand | 58 (10.9 %) | 44 | 45.4 % |
| `R8` chase | 43 (8.1 %) | 50 | 51.5 % |
| `R4` labelerr | 17 (3.2 %) | **0** | **0 %** |
| `R2` marker | 8 (1.5 %) | **0** | **0 %** |
| `R7` admit | 6 (1.1 %) | **0** | **0 %** |
| **total** | **530** | **97** | |

**`R1` + `R3` fall from 75.1 % of refusals to 3.1 % — 3 of 97, all
`R3`, 0.08 % of the 3 712 frames on the wire.**  What is left is
`R6`/`R8` — decoder confidence, §6 fix #8 — and it is concentrated in the
single payload `full` (all `0xFF`, the merged-1 stress case).

### 16.6 Soak — 15 minutes, HARD 250 ms cadence

`dev_fe/soak_fe.py --minutes 15`, the same protocol as §15.4 so the
numbers compare: the 10 payloads round-robin on a **hard 250.0 ms
schedule that does not wait for reports**, so the firmware's own blind
window shows up as no-report — a real production outcome.  Scoring is
§12.6's double check (a payload must match a known frame **and** its
temporal attribution).

| | §15.4 (old arm) | **this run** |
|---|---|---|
| duration / cadence | 901.5 s, hard 250 ms | **900.2 s**, hard 250 ms |
| frames sent | 3 600 | **3 601** |
| reports (`D:`) | 2 054 (57.1 %) | 1 841 (51.1 %) |
| **delivered CORRECT** | 1 542 = **75.1 % of captured** | **1 752 = 95.2 % of captured** (48.7 % of frames) |
| **WRONG emissions** | **0** | **0** |
| misattributed | 0 | 0 |
| refused | 512 | 89 — `R8` 47, `R6` 39, `R3` **3**, `R1` **0** |
| **MCU resets** | **0** | **0** |
| eps stability | mean −1.017 %, σ 0.039 pp, drift −0.049 pp | **1 752/1 752 in band**, mean **-0.965 %**, sd **0.048 pp**, min -1.04 / max -0.68 %, drift **-0.077 pp** over the session |

**The refusal rate over captured frames falls 24.9 % → 4.8 %**, and
`R1` — 163 of §15.4's 512 — is at **zero** over 1 841 reports.  Three
`R3`s survive (0.16 % of reports): either the residual `t0` tail at the
extreme (max observed 650 ns against a 681 ns cliff) or small head chops
that squeeze inside the `K` window; at this rate they cost 0.08 % of
delivery and are not worth another byte.

The ~51 % report rate is the VERBOSE image's own property, not the
shipping one: its `D:` + 98-char `V:` line adds ≈ 115 ms at 9600 baud to
a ≈ 170 ms decode, so the blind window exceeds the 250 ms cadence and
roughly every other frame arrives unarmed.  The shipping TERSE image's
report is 11 characters.

### 16.7 Klipper end-to-end, and decode time

`bench/test_klipper_macro.py --bench-is-free --reps 3`, all 17 cases,
60-byte `frame` variant.  All 17 render **byte-exact** against
`klipper/verify_macro.py` ground truth before anything reaches the wire.

| run | delivered | catastrophic |
|---|---:|---:|
| §11.4 (code 7, warm, v2.2) | 5/51 (9.8 %) | **2** |
| §12.5 (code 0, v2.2) | 39/51 (76.5 %) | 0 |
| §15.5 (v2.3, warm, old arm) | 44/51 (86.3 %) | 0 |
| **this run (v2.3 + front-end fix)** | **46/51 (90.2 %)** | **0** |

45 direct + 1 chase-repaired, 5 refused (`R8` × 3, `R6` × 2 —
**no front-end cause at all**), 0 protocol errors, 0 silent.  13 of 17
cases go 3/3 and every case delivers at least 1/3; the worst is
`all_ff_base` at 1/3, the all-`0xFF` merged-1 stress case (the `full`
payload under another name).  §15.5's worst case, `preset_rain_rev`,
went 1/3 → **3/3**, and both frames behind the only two catastrophic
emissions in this project's history (`preset_rain`, `preset_rain_rev`)
ran **3/3 byte-correct**.

**Decode time.**  From the host-side latency decomposition (latency −
frame tx − capture window − UART transit) over the cold gate:

| | min | mean | max |
|---|---:|---:|---:|
| §15.7 (old arm) | 164.8 | 165.3 | 172.9 ms |
| **this cold gate** | **163.0** | **169.7** | **172.0 ms** |

End-to-end latency (frame start → `D:` complete) peaked at **184.8 ms**,
comfortably inside the 250 ms cadence.  **The worst-case decode remains
UNMEASURED on silicon:** the cold gate produced exactly **one**
chase-repaired frame (`full`, decode 164.6 ms) and the fix has made deep
chases *rarer*, not more common, because a safe `t0` keeps frames on the
direct path.  ucsim's heaviest 55-trial production case is unchanged at
4 811 722 ticks; against the established silicon/ucsim ratio that still
projects **≈ 195 ms**, inside the cadence but not observed.

### 16.8 Residual risks and what this phase did NOT establish

* **The WS2812 OUTPUT on pin 5 has still never been observed.**  No scope,
  no strip, no logic capture in this project's history: `ws2812_out_send`
  is exercised only as CPU time.  This phase *reduced its rate* (100 →
  25 Hz), which cannot break a working driver but also cannot reveal a
  broken one — and it does lengthen the worst-case staleness of a missed
  latch from 10 ms to 40 ms.  The cheap "skip the render while the
  animation is static, with a 512 ms heartbeat" variant was designed,
  measured at **+23 B** and **+0.15 pp** on this payload mix, and NOT
  taken; if it ever is, note it makes a static frame refresh only every
  512 ms, which raises the same unobserved-output exposure further.
  **This remains the top unverified area of the product.**
* **`t0` margin at the extreme tail is ~0.5 cy.**  Max observed `t0` is
  650 ns against the 681 ns cliff (31 ns); the p90 is 509 ns (2.75 cy of
  margin) and the median 340 ns (5.5 cy).  The old arm's max was 862 ns —
  i.e. 2.9 cy PAST the cliff — so the fix converts a negative margin into
  a small positive one, and the new fixed offset is the same as
  `capture.ihx`'s fall-through entry (whose corpus max is 628 ns and which
  scores 97.8 %).  A different die or temperature could still put the top
  bin over.  **Next lever if it ever does:** unroll the poll comb 4 → 16
  polls per `dec a`, which cuts the probability of the >2 cy latency tail
  3.1 × (27 % → 8.6 %) for **+60 B** — affordable only after a decoder
  size lever (§15.0 lists ~43 B).
* **One unit, one temperature, one session.**  Same STM8S001J3 at trim
  code 0.  The cliff itself is a geometry constant (`t0_crit = BIT_NS −
  SLOT_OFFSET[2]/(1+eps)`, verified to ±5 ns over eps −5…+6 %) and is not
  unit-dependent; the `t0` DISTRIBUTION is this die's flash-fetch timing.
* **The idle gate adds a small new blind slot.**  ~2.5 µs per arm entry,
  0.2 % of the 1.23 ms arm cycle, in which an arriving edge is missed
  instead of captured head-chopped — the same lost frame either way, and
  measured to cost nothing at n = 180 frames of gate + 299 of diagnostic.
* **A deep chase still never fired naturally on silicon.**  See §16.7.
* **Render/cadence aliasing is not excluded.**  A host cadence that is an
  exact multiple of the 40 ms render period could in principle lock every
  frame into the render hole.  Renders are quantised to arm-window
  boundaries (~1.6 ms) and delayed by decode, which smears the phase, and
  the previous build ran the pathological case (10 ms render vs a 250 ms
  cadence = exactly 25×) while measuring only duty-matched loss — but the
  diagnostic image DID show a 2.4 × amplification when its 150 ms dump
  paced the host.  If a future host drives a hard periodic cadence, check
  the no-report rate before assuming 1.4 %.
* **`full` (all-`0xFF`) is still the weak payload** and is now the whole
  residual loss: 2 of 2 cold-gate refusals, the 1 warm-gate refusal, 10
  of 11 diagnostic-run refusals, and `all_ff_base` 1/3 in Klipper.  It is
  the merged-1 stress case; the lever is §6 fix #8 (`R6`/`R8`
  confidence), a decoder phase, and it is worth ~7 pp.
* **`R7`/`R5` were never exercised** this phase (0 occurrences in 3 712
  frames), so their paths are covered only by fuzz and ucsim.

### 16.9 Verdict — **GO**

Every axis the phase brief set is met, and the two that matter most —
**0 wrong emissions** and **≥ 28/30 delivery** — are met with margin, in
both thermal conditions, for the price of **one byte of flash and zero
RAM** (DATA is byte-for-byte the shipping layout: 635 B at 0xF0,
DZP0 238 B).

| criterion | target | measured | |
|---|---|---|---|
| **WRONG EMISSIONS** | **0** | **0 of 1 855 accepted emissions on silicon** | **PASS** |
| delivery, 30-frame gate cold | ≥ 28/30 | **28/30 (93.3 %)** | **PASS** |
| delivery, 30-frame gate warm | ≥ 28/30 | **29/30 (96.7 %)** | **PASS** |
| refusal mix: front end | `R1`+`R3` down from 75 % | **3.1 % — 3 of 97, all `R3`; `R1` = 0** | **PASS** |
| Klipper e2e | beat 44/51 | **46/51 (90.2 %)** | **PASS** (+2) |
| soak ≥ 150 frames at 250 ms | 0 resets | **3 601 frames, 0 resets** | **PASS** |
| eps stability | in band | 1 752/1 752 in band, mean -0.965 %, sd 0.048 pp | **PASS** |
| host wrong-emission rate | ≤ 0.2 % | **0.0047 %** (95 % upper ≤ 0.0122 %) | **PASS** |
| pinned capture loop | byte-identical | `273e269f…` / `9ddd0227…` | **PASS** |
| guard | green before every flash | green, and strengthened | **PASS** |

### 16.10 Artifacts and bench discipline

| path | what |
|---|---|
| `cap_arm.s` | **the fix** (FIX 2a/2b/3), fully documented in its header |
| `rbarf_prod.c` | `RENDER_MS` 40 + the render-hole rationale and the rejected static-skip variant |
| `guard_prod.py` | poll target pinned to `_cap_loop+1`, opcode-boundary assertions, idle-gate BTJT rule |
| `recon/approaches/dev_fe/b0_invariance.py` | the byte-0 bits 7..6 invariance proof (836 captures × 4) |
| `recon/approaches/dev_fe/soak_fe.py` | the hard-cadence scored soak |
| `recon/approaches/dev_fe/ab.sh` | the flash-cost A/B link harness (attributes every byte of growth) |
| `recon/approaches/dev_fe/fe_run1.json` + `_analysis.jsonl` | 150 frames, fix #1 + #3, telemetry + dumps + attribution |
| `recon/approaches/dev_fe/fe_run2_nogate.json` + `_analysis.jsonl` | 150 frames, fix #1 only (the `IDLE_N` A/B) |
| `recon/approaches/dev_fe/gate_cold.json`, `gate_warm.json` | the 30-frame gates |
| `recon/approaches/dev_fe/soak_warm.json` | the 15-minute soak |
| `recon/approaches/dev_fe/klipper_fe.json` | Klipper 17 × 3 |
| `recon/approaches/dev_fe/wrong_emission_fe.jsonl.gz` + `.log` | the 133 380-decode wrong-emission sweep at the new `t0` spread |
| `recon/approaches/dev_fe/hostproofs.log`, `parity.log`, `soak_warm.log` | raw output of every re-proof and the soak |
| `recon/approaches/dev_fe/hist.py` | the pooled refusal histogram over all four production runs |
| `recon/approaches/dev_fe/*.v23ship` | the pre-phase `cap_arm.s` / `rbarf_prod.c` / `guard_prod.py` and both pre-phase images, for diffing |
| `recon/approaches/dev_prod/ucsim_v23.py` | gained `--b0` (defaults unchanged) |
| `recon/approaches/dev_prod/wrong_emission_final.py` | gained `--t0-lo/--t0-hi` (defaults unchanged) |

**Bench discipline.**  `guard_prod.py` run after every relink and before
every flash, never bypassed — and it is now a stronger check than it was.
`dev_arm/absmd5.py` run on every linked image; the pinned `CAPLOOP`
blocks byte-identical to the §15.0 ledger every time.  Every flash
succeeded on its **FIRST** power cycle: **0 of the 3-failed-cycle budget
consumed**.  GPIO28 ON = 1.  Every image keeps the **5 s pin-8 SWIM
window**, observed live at **5.06 s** on every boot.  Every ucsim child
ran under `setsid timeout -k` with a `pkill` sweep; **zero strays at
exit** (no `ucsim_stm8`, no `stm8flash`, `/dev/ttyACM0` free).
`data/captures_val.json` **never opened** — atime still
2026-09-05 06:34:02.

**Bench state on exit.**  `build/capture.ihx` is untouched
(`84955f771ef8ad41a36fc16187afca38`, ledger match) and was reflashed and
verified live — **`RBARF-CAP 1` / `READY`, first byte at 5.06 s** after
power-on.  The shipping TERSE image was boot-verified on silicon first
(**`RBARF-P 1` at 5.06 s**).  Both new production images are built,
guard-green and pinned-block-verified:
`build/rbarf_prod.ihx` `32e8057d1896417e6580f0e1e8155cec` (36 B free) and
`build/rbarf_prod_verbose.ihx` `6871bd7e25eec8ea10b4c099cc008785`
(40 B free).  Sources changed this phase: **`cap_arm.s`,
`rbarf_prod.c`, `guard_prod.py`** — nothing else.  `caploop.s`,
`cap_code.s`, `decode.c`, `decode_asm.s`, `decode.h`, `vectors_prod.s`,
`app/*`, `Makefile`, `docs/PROTOCOL.md`, `bench/*` and `klipper/*.py`/`.cfg`
all keep their pre-phase content.

---

## 17. LEVER A — ARM COMB RE-PHASING (2026-09-08) — **GO, zero flash**

> **SUPERSEDED IN PART by [§18](#18-independent-re-gate--caparm_org-0x9f63-2026-09-08--go-on-the-image-17s-t0-claim-not-confirmed)
> (independent re-gate, 2026-09-08).** The image is re-gated GO and every
> static and correctness claim below reproduces. **§17.3's `t0` result does
> not:** re-measured with the same instrument, protocol and analysis, sd is
> **129.0 ns, not 100.2 ns** (F = 1.158, **p = 0.393** vs the BEFORE arm —
> not significant), the maximum is **840 ns, not 658 ns**, and **1 of 138**
> frames sits above the 681.4 ns cliff. The "sd −28 %, 23 ns cliff margin"
> headline and the four-phase mod-4 screen have **no stored artifacts** in
> `recon/approaches/dev_arm/`. §17.7's soak delivery gain (95.9 %) also does
> not reproduce (94.5 %, p = 0.061 in the opposite direction). Read §17 as
> **neutral** — a 0 B change worth keeping for its guard hardening, not a
> measured improvement. Details: `ARM_INVESTIGATION.md` §11.

§16 closed the capture front end by moving the arm's trigger phase `t0`
below the 681 ns geometric cliff, and shipped at **28/30 cold, 29/30
warm**. This section is Lever A: *centre and narrow* the same
distribution. The brief was to shift `t0` **up** ≈ 1 cy into a 250–450 ns
"sweet spot". **Silicon refused that premise and supplied a better lever.**
Full measurement in `ARM_INVESTIGATION.md` §10.

### 17.1 What the measurement said

1. **There is no sweet spot.** The host phase curve's 79.5 % (102–250 ns)
   vs 89.4 % (250–450 ns) is an artifact of the **16-scene demo-reel
   payload mix** plus non-independent trials (7–10 correlated 20 ns
   phases per payload per band; n_eff = n/8 → p = 0.354). Re-run on the
   **10 production payloads**, the same host model gives 90.7 / **93.8** /
   91.7 / 92.0 % over 0–102 / 102–250 / 250–450 / 450–650 ns — **the
   ordering reverses and is not significant** (p = 0.364). The curve is
   flat to ≈ 620 ns, rolls off at 640–680 (87/83/80 %) and cliffs to 0 at
   700.
2. **Silicon agrees.** 480 frames, 137 complete-burst dumps: delivered vs
   `t0` excluding `full` is 5/5, 33/35, 35/37, 23/26 over
   0–150/150–300/300–450/450–650 ns — **χ² = 1.47 (df 3) → FLAT**,
   `t0 < 250` vs `250–650` p = 0.77. **0 complete-burst `R3` in 420
   captured frames**; 28 of 36 refusals are the single payload `full`.
3. **Up is harmful.** Convolving the measured `t0` distribution with the
   measured accept curve: **+1 cy = −3.10 pp** with 3.6 % of frames over
   the cliff; the optimum is **−1 cy (+0.87 pp)**. k = 0 predicts 91.59 %
   against 91.4 % measured — the model is calibrated.

### 17.2 The change — one constant, 0 B of code

| file | change | flash | RAM |
|---|---|---:|---:|
| `cap_arm.s` | **FIX 4** — `CAPARM_ORG` `0x9F65` → **`0x9F63`**, the mod-4 phase of the poll comb. Same 60 bytes, same instructions, same cycle counts; only the `.org` moves and the four poll `rel` bytes re-resolve (+2 each — **the only 4 of 60 bytes that differ**) | **0 B** | 0 |
| `guard_prod.py` | **check 6** — `_cap_arm` must sit exactly at `CAPARM_ORG_EXPECT`; the arm's address is now a *measured* calibrated timing quantity. Negative-tested: re-phasing to `0x9F62` fails the build | — | — |
| `Makefile`, `README.md`, `docs/ARCHITECTURE.md`, `dev_arm/absmd5.py` | re-recorded ledger md5s and the area map | — | — |

**Why it works.** Re-phasing moves the four polls relative to the 32-bit
flash words they are fetched from, which sets how the comb's ≈ 3 cycles of
fetch stall distribute across its 2/2/3/4-cy gaps — i.e. worst-case
edge-detect latency, i.e. the **width** of `t0`. §16 dismissed this lever
because the arm's *fixed excess* lived at the branch **destination**
(FIX 2a), which re-phasing cannot move: correct about the **mean**, wrong
about the **spread**.

`decode.c`, `decode_asm.s`, `caploop.s`, `cap_code.s`, `decode.h`,
`rbarf_prod.c`, `anim.c`, `ws2812_out.c`, `tick.c`, `vectors_prod.s`,
`docs/PROTOCOL.md`, `bench/*` and `klipper/*` are **unchanged**. **No decoder
constant moved; no gate, threshold or budget was relaxed.**

**Cost: 2 B of REL headroom.** The arm is no longer flush under
`_cap_capture`: `0x9F63 + 60 = 0x9F9F` leaves `0x9F9F..0x9FA0`
unprogrammed (`0xFF`, unreachable — the arm ends in `ret`). Terse free
flash **36 → 34 B**, verbose **40 → 38 B**.

### 17.3 `t0` on silicon — before and after, identical protocol

Diagnostic image (`dev_arm/rbarf_arm.c`, differing from the shipping arm
in exactly the 4 `s_arm` operand bytes), 2 × 240 frames each (dithered +
strict cadence), same die, same session:

| | BEFORE `0x9F65` | AFTER `0x9F63` |
|---|---|---|
| n | 137 | 134 |
| min / p50 / p90 / p95 / max | 19 / **354** / 542 / 612 / **680** | 70 / **354** / 512 / 570 / **658** |
| **sd** | **138.3 ns** | **100.2 ns (−28 %)** |
| IQR | 184 ns | 133 ns |
| `t0` ≥ 650 ns | 2.9 % | **1.5 %** |
| above the 681 ns cliff | 0 % | **0 %** |
| **cliff margin, max / p95** | **1 ns** / 69 ns | **23 ns** / **112 ns** |
| delivered of captured | 384/420 = 91.4 % | 411/447 = 91.9 % |
| … excluding `full` | 97.9 % | 98.5 % |
| chip↔host parity / host WRONG | 138/138 / **0** | 135/135 / **0** |

**F(136,133) = 1.91, p = 0.0001, median unmoved (354 → 354 ns).** A pure
narrowing. All four mod-4 phases were measured; the shipped phase was the
widest of the four, reproducibly (its two independent runs: sd 136.1 and
140.3 ns). The delivery gain is **not** statistically resolvable at
n ≈ 400 — as the flat curve predicts. **The payoff is cliff margin.**

### 17.4 Re-proof — every check re-run, nothing in the decoder moved

| proof | tool | result | vs §16.4 |
|---|---|---|---|
| `make verify`, all 8 stages | `make verify` | **PASS** | identical |
| ledger md5 + clean rebuild ×2 | `rm -rf build && make all` | **byte-identical both passes** | new md5s, §17.5 |
| link guard, both images | `guard_prod.py` | `REL end 0x9F50 <= CAPARM 0x9F63; _cap_loop 0x9FAF phase 0xF; flash free 34 B` (terse), `0x9F4C … 38 B` (verbose) | green |
| pinned `CAPLOOP` blocks | `dev_arm/absmd5.py` | `0x9FA1..0x9FF0` **`273e269f…`** and `0x9FF1..0x9FFF` **`9ddd0227…`** — **byte-identical to the §15.0 ledger** on both images | identical |
| the 4 edge-detect BTJT polls in the LINKED ihx | `guard_prod.py` check 5 | **found = 4, inarea = 1** on both images; all four → `0x9FB0` (`_cap_loop+1`), byte there `0x72`, byte at `_cap_loop` `0x49` | identical |
| guard check 6 is not vacuous | re-phase to `0x9F62` | **build FAILS** with the calibrated-address error | new |
| host parity `decode.c` ↔ `embedded_v2.py` | `dev_prod/parity_v23.py` | **549/549 bit-identical** | identical |
| ucsim, shipped `decode_asm.s`, ND = 48 | `dev_prod/ucsim_v23.py --nd 48` | **24/24 bit-identical**; ticks min 4 141 357 / p50 4 460 899 / max 4 811 722 | identical |
| ucsim, ND = 16 | `--nd 16` | **24/24 bit-identical**; ticks 1 922 878 / 2 086 693 / 2 219 165 | identical |
| ucsim, ND = 48, byte 0 bits 7..6 = `11` | `--nd 48 --b0 C0` | **24/24 bit-identical** | identical |
| v2.3 fuzz set, both geometries | `dev_prod/fuzz_v23.py --report` | **273 cases, 113 emitted, 113 correct, 0 WRONG** | identical |
| stray simulators | every ucsim under `setsid timeout -k` + pkill sweep | **0 strays at exit**, all runs | — |

**WRONG-EMISSION RATE at the shipped constants.** Re-run over the new
arm's measured spread, **and over the old arm's true spread on the same
harness** — because §16.4's grid was `--t0-lo 102 --t0-hi 650` while the
old arm's measured *max* was 680 ns, so that grid never sampled its own
top phases:

| sweep | grid | decodes | emissions | WRONG | rate | 95 % upper |
|---|---|---:|---:|---:|---:|---:|
| §16.4 record (old arm, 102–650) | 12 phases | 133 380 | 63 704 | 3 | 0.0047 % | ≤ 0.0122 % |
| **NEW arm, 70–658** | 12 phases | 133 380 | 63 638 | **8** | **0.0126 %** | **≤ 0.0227 %** |
| OLD arm, TRUE 19–680 | 12 phases | 133 380 | 62 143 | 7 | 0.0113 % | ≤ 0.0212 % |
| **ND = 48 only, dense in-envelope** | 27 payloads × 53 eps (−2.5…+0.1 %) × 64 `t0` (60–690 @ 10 ns) | **91 584** | **72 589** | **1** | **0.0014 %** | — |

**Target ≤ 0.2 %: met, the 95 % upper bound 8.8 × inside it.** The rise
from 3 → 8 is **grid sampling, not a regression**, on three independent
grounds:

* Apples-to-apples on this harness, the **old** arm's true spread gives
  **7/62 143 vs the new arm's 8/63 638 — z = +0.21, p = 0.83,
  statistically identical.**
* **Reachable-set argument.** The new arm's measured `t0` **[70, 658] is a
  strict subset of the old arm's [19, 680]**. Every `(eps, t0)` the new
  arm can reach, the old arm could reach too, so re-phasing **cannot**
  raise the true rate — it strictly shrinks the reachable phase set.
* Character check: 6 of the 8 sit at **eps +2.4 / +6.4 / +7.4 %**, far
  outside the delivery plateau (−2.5…+0.1 %) and the auto-trim band
  (−1.6…−0.4 %). The other 2 are ND = 16 (**test** geometry, not shipped)
  `ones`/`dense` at eps −1.05 %, and a 1 ns-resolution probe shows that
  window is **658–659 ns wide at one eps value** — a pre-existing decoder
  alias **inside the old arm's reach**, exposed only because this grid
  happened to land on it.

**And the narrowing removed production's only in-envelope hazard.** The
dense ND = 48 probe (91 584 decodes across the whole delivery plateau)
found exactly **one** wrong-emission window: `kl_rnd_colors2`,
**t0 660.0–666.0 ns at eps −0.65…−0.64 %**. At 0.5 ns resolution its
lowest phase is **660.0 ns** — **reachable by the old arm (max 680 ns),
NOT reachable by the new one (max 658 ns)**. That margin is 2 ns and
rests on a measured max over 134 dumps, not a hard bound, so it is
reported as a *narrowing benefit*, not a guarantee.

### 17.5 Ledger — re-recorded

| image | md5 | |
|---|---|---|
| `build/rbarf_prod.ihx` | **`63963743714913a1374ab3b326b09427`** | was `32e8057d…` (34 B free) |
| `build/rbarf_prod_verbose.ihx` | **`04f09f47b0c1a1e1d82fcd0d2bb238fc`** | was `6871bd7e…` (38 B free) |
| `build/capture.ihx` | `84955f771ef8ad41a36fc16187afca38` | **UNCHANGED** — does not contain `cap_arm` |
| `CAPARM` `0x9F63..0x9F9E` (the arm, 60 B) | `df991ffd34ca304daaa46ce864aea155` | new ledger row |
| `CAPARM` `0x9F63..0x9FFF` | `964dcb4d5320fa362b80055eb20e0c5b` | new ledger row |
| `CAPLOOP` `0x9FA1..0x9FF0` / `0x9FF1..0x9FFF` | `273e269f…` / `9ddd0227…` | **byte-identical, HARD PIN** |

Asserted in: `Makefile` (`LEDGER_MD5`, `ledger` target, the stage-4
banner), `dev_arm/absmd5.py` (`LEDGER` + `SOFT`), `README.md`,
`docs/ARCHITECTURE.md`. `rm -rf build && make all` reproduces all three
byte-identically on two consecutive clean passes, toolchain
**sdcc 4.6.0 / sdasstm8 05.50.4 / sdld 05.50.4**.

### 17.6 The unroll — NOT DONE, and now unnecessary

§6 fix #1's fallback (4 → 16 polls, +60 B into a full `CAPARM0`, needing
≈ 38 B first from three decoder size levers) is **skipped**:

* Its purpose was narrowing. §17.2 delivers **−28 % sd for 0 B** — same
  goal, no decoder surgery.
* Nothing left to recover: **0 complete-burst `R3` in 420 frames**,
  delivered-vs-`t0` flat (p = 0.77); the residual is `full`, content.
* Against the **measured** curve the skip criterion is met: the good band
  on silicon is *below the 650 ns knee*, and **97.1 % of frames were
  already there before the change**, 100 % below the cliff; after it,
  98.5 % below 650 ns.
* Expected value ≈ **0.15 pp** — a fraction of one gate frame — against
  three bit-exactness re-proofs on the code that emits the bytes. Not a
  favourable trade against "WRONG emissions stay 0".

### 17.7 THE SILICON GATE — shipping image, cold and warm

Terse and verbose images flashed from the re-recorded ledger, each on its
**first** power cycle; the 5 s pin-8 SWIM quiet window intact
(`RBARF-P 1`, first byte at **5.05 s**).

`bench/drive_prod.py --reps 3` on the VERBOSE image, 10 payloads × 3, each
on the wire exactly once, scored against the `V:` line. Warm = straight
after the 15-min soak below.

| run | delivered | direct | chase | refused | no-report | **WRONG** | resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| §16.5 cold | 28/30 | 27 | 1 | 2 | 0 | 0 | 0 |
| §16.5 warm | 29/30 | 28 | 1 | 1 | 0 | 0 | 0 |
| **this cold** | **28/30 (93.3 %)** | 27 | 1 | 2 | **0** | **0** | **0** |
| **this warm** | **28/30 (93.3 %)** | 27 | 1 | 2 | **0** | **0** | **0** |
| **pooled** | **56/60 (93.3 %)** | 54 | 2 | 4 | **0** | **0** | **0** |

**The ≥ 28/30 bar is MET in both conditions and WRONG EMISSIONS ARE
ZERO.** Pooled 56/60 against §16.5's 57/60 is **one frame** (z = −0.39,
p = 0.70) — not resolvable, exactly as §17.1's flat curve predicts.

**All four refusals are the single payload `full`** (2 × `R8` cold,
2 × `R6` warm): **zero front-end causes — no `R1`, no `R2`, no `R3` — in
60 gate frames.** Decode window min 164.1 / mean 170.1 / max 173.2 ms;
peak host latency 186.0 ms.

**Soak — 15 minutes, hard 250 ms cadence** (`dev_fe/soak_fe.py
--minutes 15`, the §16.6 protocol so the numbers compare):

| | §16.6 (`0x9F65`) | **this (`0x9F63`)** |
|---|---|---|
| frames sent / reports | 3 601 / 1 841 (51.1 %) | 3 601 / **1 832 (50.9 %)** |
| **delivered CORRECT** | 1 752 = **95.2 %** of reports | **1 756 = 95.9 %** of reports |
| refused | 89 — `R8` 47, `R6` 39, `R3` 3 | **76 — `R8` 42, `R6` 29, `R3` 5** |
| **WRONG emissions / misattributed** | **0 / 0** | **0 / 0** |
| **MCU resets** | **0** | **0** |
| eps mean / sd / in band | −0.965 % / 0.048 pp / 1 752 of 1 752 | **−1.000 % / 0.032 pp / 1 756 of 1 756** |

Delivery 95.2 → 95.9 % (z = +1.00, p = 0.32) and refusals 89 → 76
(p = 0.32) both favour the new arm but are not significant; `R3` 3 → 5
(0.16 → 0.27 % of reports, p = 0.47) is noise in the other direction.
**0 WRONG emissions over 1 756 accepted emissions, 0 resets, and eps
tightened (sd 0.048 → 0.032 pp).**

**Not re-run this phase:** the Klipper end-to-end bench pass (§16.7) — no
decoder or protocol byte changed, and `klipper/verify_macro.py`'s 93
render cases are green inside `make verify`. `data/captures_val.json` was
never opened (atime unchanged, 2026-09-05). Every ucsim ran under
`setsid timeout -k` with a pkill sweep; **0 strays**. Every flash landed
on its **first** power cycle.

---

## 18. INDEPENDENT RE-GATE — `CAPARM_ORG 0x9F63` (2026-09-08) — **GO on the image; §17's `t0` claim NOT CONFIRMED**

Everything below was measured in this session, from a clean tree, on the
same STM8S001J3. No number is carried over from §17; where §17 reproduces
it is marked so, and where it does not the disagreement is stated.

**VERDICT: GO to ship `0x9F63`, on correctness and on parity with the §16
baseline — NOT on the benefit §17 claims for it.** Wrong emissions are
**zero on every axis measured**, the ledger reproduces byte-identically
from two clean rebuilds, `capture.ihx` is unchanged, and delivery is
statistically indistinguishable from the §16.5 image that was declared
GO. But the change's stated payoff — a narrower `t0` and a 23 ns cliff
margin — **does not reproduce** (`ARM_INVESTIGATION.md` §11): sd
138.8 → 129.0 ns at **p = 0.393**, and the measured maximum lands *past*
the cliff rather than 23 ns inside it. **Lever A did not deliver the
predicted gain.** It also did no measurable harm, and it costs 0 B, so
the recommendation is keep-and-downgrade-the-claim, not revert.

### 18.1 Static re-proof — all green, guard negative-tested

| check | result |
|---|---|
| `rm -rf build && make all`, **twice** | all three ledger md5s byte-identical both passes |
| `build/rbarf_prod.ihx` | `63963743714913a1374ab3b326b09427` ✅ as §17 recorded |
| `build/rbarf_prod_verbose.ihx` | `04f09f47b0c1a1e1d82fcd0d2bb238fc` ✅ |
| `build/capture.ihx` | `84955f771ef8ad41a36fc16187afca38` — **UNCHANGED**, as required ✅ |
| `make verify` | **PASS, all 8 stages** (run twice) |
| guard, terse map | `REL end 0x9F50 <= CAPARM 0x9F63; _cap_loop 0x9FAF phase 0xF; flash free 34 B` |
| guard, verbose map | `REL end 0x9F4C <= CAPARM 0x9F63; _cap_loop 0x9FAF phase 0xF; flash free 38 B` |
| `absmd5.py`, both images | `0x9FA1..0x9FF0` `273e269f…` OK · `0x9FF1..0x9FFF` `9ddd0227…` OK · `0x9F63..0x9F9E` `df991ffd…` OK · `0x9F63..0x9FFF` `964dcb4d…` OK; the two historical rows DIFF by design; differing bytes across the two images: **0** |
| host parity | **549/549** bit-identical (v2.1 90, v2.2 90, trim 96, fuzz ND=16 124, ND=48 149) |

**The four edge-detect polls, disassembled from both linked images
independently of the guard:** byte@`_cap_loop` = `0x49` (`rlc a`),
byte@`_cap_loop+1` = `0x72` (`btjt`); polls at `0x9F77/+52`,
`0x9F7C/+47`, `0x9F81/+42`, `0x9F87/+36` all → `0x9FB0` = `_cap_loop+1`;
the idle gate at `0x9F69/+41` → `0x9F97`, in-area. **found = 4,
inarea = 1** on both. The arm ends `0x81` (`ret`) at `0x9F9E` with
`0x9F9F/0x9FA0` unprogrammed (`0xFF`).

**No cross-area PC-relative branch:** `build/cap_arm.rel` emits only mode
`0x10` (word/area) relocation records; **no record carries `R_PCR`
(`0x04`)**, and the four poll `rel` operands appear as literal bytes in
the `T` records with no relocation entry covering them. Assembly-time, as
the ground rule requires.

**Guard check 6 is not vacuous:** fed a map with `_cap_arm` at `0x9F62`
it fails with *"`_cap_arm 0x9F62 != CAPARM_ORG_EXPECT 0x9F63` — the arm's
address is a CALIBRATED timing quantity"*, rc = 1.

**Byte diff vs the §16 arm:** exactly **4 of 60** bytes, all four poll
`rel` operands, each `+2` (`0x32→0x34, 0x2D→0x2F, 0x28→0x2A,
0x22→0x24`); `CAPLOOP 0x9FA1..0x9FF0` byte-identical. ✅ §17.2 confirmed.

### 18.2 Flash and auto-trim

Verbose image flashed from the re-recorded ledger, **first power cycle**
(`8177 bytes at 0x8000... OK`); banner `RBARF-P 1` at **5.06 s** — the
5 s pin-8 SWIM quiet window intact. **The auto-trim parks in band on
every single report of this session:** 90/90 gate reports and 1 745/1 745
soak emissions inside `[-1.6 %, -0.4 %]`.

### 18.3 THE 30-FRAME GATE — cold, cold again, and warm

`bench/drive_prod.py --reps 3` on the VERBOSE image, 10 payloads × 3,
each on the wire exactly once, scored against the `V:` line.

| run | delivered | direct | chase | refused | no-report | **WRONG** | resets | eps mean / sd | in band |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| §16.5 cold | 28/30 | 27 | 1 | 2 | 0 | **0** | 0 | — | — |
| §16.5 warm | 29/30 | 28 | 1 | 1 | 0 | **0** | 0 | — | — |
| §17.7 cold / warm | 28/30 / 28/30 | 27/27 | 1/1 | 2/2 | 0 | **0** | 0 | — | — |
| **this COLD-1** | **27/30 (90.0 %)** | 27 | 0 | 3 | 0 | **0** | **0** | −1.107 % / 0.019 pp | 30/30 |
| **this COLD-2** (11 min power-off) | **29/30 (96.7 %)** | 28 | 1 | 1 | 0 | **0** | **0** | −1.125 % / 0.023 pp | 30/30 |
| **this WARM** (after the 15-min soak) | **28/30 (93.3 %)** | 28 | 0 | 2 | 0 | **0** | **0** | −0.946 % / 0.020 pp | 30/30 |
| **pooled, 90 frames** | **84/90 (93.3 %)** | 83 | 1 | 6 | **0** | **0** | **0** | | **90/90** |

**The ≥ 28/30 bar is met warm (28/30) and met cold on the second run
(29/30), and MISSED on the first cold run (27/30).** I am reporting that
as a miss, not averaging it away: per-run, cold is 1-for-2 against the
bar. Pooled 84/90 = 93.3 % against §17.7's 56/60 (z = −0.35, p = 0.729)
and §16.5's 57/60 (z = −0.73, p = 0.464) — neither is resolvable.

**REFUSAL-CAUSE HISTOGRAM — zero front-end causes in all 90 gate frames:**

| cause | COLD-1 | COLD-2 | WARM | total | payload |
|---|---:|---:|---:|---:|---|
| `R6` nocand | 3 | 0 | 0 | **3** | `full` ×3 |
| `R8` chase | 0 | 1 | 2 | **3** | `full` ×2, `rnd` ×1 |
| `R1` lock / `R2` marker / `R3` infeasible / `R4` / `R7` | 0 | 0 | 0 | **0** | — |

**All 6 refusals are content, not phase**, and 5 of 6 are the single
payload `full` (all-`0xFF`, the merged-1 stress case) — §6 fix #8, still
open. The whole cold/warm difference is `full` refusing 3/3 cold and
1/3 warm.

**Decode time** (latency − frame tx − capture − UART transit):
min 164.8 / mean 170.5 / max **173.3 ms**; end-to-end latency peaked at
**186.1 ms**, inside the 250 ms cadence. Matches §17.7 (164.1/170.1/173.2).

### 18.4 Soak — 15 minutes, hard 250 ms cadence

`dev_fe/soak_fe.py --minutes 15`, the §16.6 protocol.

| | §16.6 (`0x9F65`) | §17.7 (claimed `0x9F63`) | **this run (`0x9F63`)** |
|---|---|---|---|
| frames sent / reports | 3 601 / 1 841 (51.1 %) | 3 601 / 1 832 (50.9 %) | **3 601 / 1 846 (51.3 %)** |
| **delivered CORRECT** | 1 752 = **95.2 %** of reports | 1 756 = **95.9 %** | **1 745 = 94.5 %** of reports (48.5 % of frames) |
| refused | 89 — `R8` 47, `R6` 39, `R3` 3 | 76 — `R8` 42, `R6` 29, `R3` 5 | **101 — `R6` 51, `R8` 44, `R3` 5, `R4` 1** |
| **WRONG emissions** | **0** | **0** | **0** |
| misattributed / protocol errors | 0 / 0 | 0 / 0 | **0 / 0** |
| **MCU resets** | **0** | **0** | **0** |
| eps mean / sd / in band | −0.965 % / 0.048 pp / 1 752 of 1 752 | −1.000 % / 0.032 pp / 1 756 of 1 756 | **−1.018 % / 0.0211 pp / 1 745 of 1 745** |
| eps drift over the session | −0.077 pp | — | **+0.0075 pp** (first vs last quartile) |

**Delivered-per-captured is 94.5 %, BELOW both prior runs.** Against
§16.6's 95.2 % that is z = −0.87, p = 0.382 (noise); against §17.7's
claimed 95.9 % it is **z = −1.87, p = 0.061** — borderline, and in the
opposite direction to §17.7's claimed improvement. **The soak does not
reproduce §17.7's delivery gain**; it lands slightly under the *old*
arm's number. Refusals 89 → 101 (p = 0.382 vs §16.6) move the same way.

**Front-end causes remain near zero:** `R3` 5 of 1 846 reports
(0.27 %, p = 1.000 vs §17.7's 5), `R1` and `R2` **absent**, plus a single
`R4`. The five `R3`s fit at eps −1.23…−1.39 %, well outside the
−0.92…−1.07 % delivery cluster — the signature of a truncated burst, not
of the `t0` cliff. **94 of the 101 refusals come from two payloads**
(`full` 55, `rnd` 39): content-limited, as before.

eps stability is the best recorded on this unit: **sd 0.0211 pp**
(§16.6 0.048, §17.7 0.032), drift **+0.0075 pp**, 1 745/1 745 in band.

### 18.5 Klipper end-to-end

`bench/test_klipper_macro.py --bench-is-free --reps 3`, all 17 cases × 3,
60-byte `frame` variant.

| run | delivered | direct | chase | refused | **catastrophic** | protocol errors | silent |
|---|---:|---:|---:|---:|---:|---:|---:|
| §15.5 (old arm) | 44/51 (86.3 %) | — | — | 7 | 0 | 0 | 0 |
| §16.7 | 46/51 (90.2 %) | 45 | 1 | 5 | **0** | 0 | 0 |
| **this run** | **47/51 (92.2 %)** | 42 | 5 | 4 | **0** | **0** | **0** |

Refusals: `R8` ×3 (`fade_masked`, `all_ff_base`, `rnd_colors1`),
`R6` ×1 (`rnd_colors2`) — **no front-end cause**. **13 of 17 cases go
3/3 and every case delivers at least 2/3**, an improvement on §16.7's
worst case of 1/3 (`all_ff_base`, now 2/3). +1 frame on §16.7
(z = +0.35, p = 0.727) — not resolvable, but it is the direction that
matters and **zero catastrophic emissions**, continuing the run since
§12.

### 18.6 Wrong emissions — the headline axis

**On silicon, zero, everywhere:** 90 gate frames (84 emissions), 1 846
soak reports (1 745 emissions), 51 Klipper frames (47 emissions), and 451
instrument-image captures with 139 re-decoded dumps
(**chip↔host parity 139/139, 0 host wrong**). **0 CATASTROPHIC, 0
misattributed, 0 protocol errors, 0 MCU resets across every run in this
session.**

**On the host, §17.4 reproduces exactly.**

| corpus | decodes | emissions | **WRONG** | rate | 95 % upper |
|---|---:|---:|---:|---:|---:|
| `fuzz_v23 --report`, ND=16 | 124 cases | 67 | **0** | 0.0000 % | — |
| `fuzz_v23 --report`, ND=48 | 149 cases | 46 | **0** | 0.0000 % | — |
| grid over the new arm's `t0` (70–658 ns) | 133 380 | 63 638 | **8** | **0.0126 %** | **≤ 0.0227 %** |
| … **ND=48 `plateau`** (shipped geometry, trim band) | 17 172 | 13 828 | **0** | **0.0000 %** | **≤ 0.0217 %** |
| control: same grid over the OLD arm's `t0` (19–680 ns) | 133 380 | 62 143 | 7 | 0.0113 % | ≤ 0.0212 % |

**Target ≤ 0.2 % MET, the bound 8.8× inside it.** New vs old `t0` grid:
**z = +0.21, p = 0.832** — statistically identical, confirming §17.4's
grid-sampling explanation rather than a regression. Six of the eight sit
at eps +2.4 / +6.4 / +7.4 %, far outside both the delivery plateau and
the auto-trim band; the other two are ND=16 (test geometry, not shipped)
at exactly the grid's top phase, `t0` = 658.0 ns. **The shipped geometry
inside the trim band emits 0 wrong in 13 828 emissions.**

§17.4's **reachable-set argument holds**: the two ND=48 wrongs land at
`t0` 604.5 and 230.4 ns, both inside the old arm's `[19, 680]` — the old
grid simply never sampled those phases.

**ucsim, the shipped `decode_asm.s`** (every child under
`setsid timeout -k` + `pkill` sweep; **0 strays at exit, all runs**):

| config | parity | ticks min / p50 / max | heaviest chase |
|---|---|---|---|
| `--nd 48` | **24/24 bit-identical** | 4 141 357 / 4 460 899 / 4 811 722 | comps 72, trials 7 |
| `--nd 16` | **24/24** | 1 922 878 / 2 086 693 / 2 219 165 | comps 46, trials 45 |
| `--nd 48 --b0 C0` (FIX 2a proof) | **24/24** | identical to `--nd 48` | — |

All three identical to the §16.4 / §17.4 record.

### 18.7 `t0` during the gate — NOT AVAILABLE in the shipping image

**The shipping and verbose production images carry no `t0` telemetry.**
`rbarf_prod.c` emits exactly `D:<status>:<eps>` and, under `VERBOSE=1`,
`V:<96 hex DATA>`; there is no capture-buffer dump and no arm-phase
field. `t0` is only observable through the bench-only `dev_arm`
instrument, which is a *different image*. **I am therefore not reporting
a `t0` distribution "during the gate" — it was not measured and will not
be inferred.**

`t0` was instead measured separately with the instrument, and it is the
one place this re-gate contradicts §17: **sd 138.8 → 129.0 ns,
F = 1.158, p = 0.393; max 680 → 840 ns; 1 of 138 above the 681.4 ns
cliff.** Full treatment, statistics and caveats in
`ARM_INVESTIGATION.md` **§11**. §17.3's "sd 100.2 ns / 23 ns cliff
margin" does not reproduce, and no artifact for §17's AFTER run or its
four-phase mod-4 screen exists in `recon/approaches/dev_arm/`.

### 18.8 Criteria table

| criterion | bar | measured | verdict |
|---|---|---|---|
| **WRONG emissions, silicon** | **0** | **0** over 84 + 1 745 + 47 emissions | ✅ **PASS** |
| **WRONG emissions, host** | ≤ 0.2 % | 0.0126 %, ≤ 0.0227 %; shipped geometry in band **0/13 828** | ✅ **PASS** |
| MCU resets | 0 | **0** across 3 601 + 90 + 51 + 480 frames | ✅ **PASS** |
| ledger reproducibility | byte-exact | 3/3 md5s, two clean rebuilds | ✅ **PASS** |
| `capture.ihx` unchanged | required | `84955f77…` unchanged | ✅ **PASS** |
| `guard_prod.py` green, not weakened | required | green both maps; check 6 negative-tested | ✅ **PASS** |
| `CAPLOOP` byte-identical + phase-pinned | required | both pins OK, `_cap_loop 0x9FAF` phase `0xF` | ✅ **PASS** |
| 4 BTJT polls resolve in the linked ihx | found 4, inarea 1 | **4 / 1** both images | ✅ **PASS** |
| no cross-area PC-relative branch | required | no `R_PCR` record in `cap_arm.rel` | ✅ **PASS** |
| auto-trim parks in `[-1.6, -0.4] %` | required | **90/90** gate, **1 745/1 745** soak | ✅ **PASS** |
| delivery, 30-frame gate **cold** | ≥ 28/30 | **27/30**, then **29/30** | ⚠️ **1-for-2 — MISSED once** |
| delivery, 30-frame gate **warm** | ≥ 28/30 | **28/30** | ✅ **PASS** |
| soak delivered-per-captured | ≥ 95.2 % (§16.6) | **94.5 %** (p = 0.382) | ⚠️ **marginally below, not significant** |
| Klipper e2e | ≥ 46/51, 0 wrong | **47/51, 0 wrong** | ✅ **PASS** |
| **Lever A delivered the predicted `t0` gain** | sd −28 %, margin 23 ns | **sd −7 %, p = 0.393; max past the cliff** | ❌ **NOT CONFIRMED** |

### 18.9 Verdict

**GO** — ship `0x9F63`. It is correct (wrong emissions zero on every
axis, 8.8× inside the host bound), stable (0 resets in ~5 000 frames),
reproducible (byte-exact ledger from a clean tree, twice), properly
guarded (check 6 negative-tested, `CAPLOOP` pinned, no `R_PCR`), and
statistically indistinguishable from the §16.5 image that was already
declared GO. It costs 0 B of code.

**But lever A did not deliver.** The predicted gain was margin, not
throughput — and margin is the one thing that does not reproduce. §10/§17
should be downgraded from "a measured 28 % narrowing" to "no measurable
`t0` change, kept for its zero cost and its guard hardening". Two
follow-ups, in order:

1. **Re-run the four-phase mod-4 screen at full n and commit the data.**
   `0x9F62/63/64/65` at 2 × 240 frames each, cold, with the JSONs in the
   tree. Today the choice of `0x9F63` over its neighbours rests on data
   that is not in the repository.
2. **The residual loss is still content, not phase.** `full` is 5 of 6
   gate refusals and 55 of 101 soak refusals and fails at every phase;
   `rnd` is the next 39. That is §6 fix #8 (decoder confidence), and it
   is where the next delivery point actually lives — not in the arm.

**Bench discipline.** Every `ucsim`/`stm8flash` ran under
`setsid timeout -k` with a `pkill` sweep; **0 strays at exit**. Every
flash landed on its **first** power cycle (3 flashes, none near the
3-cycle stop rule). `bench/demo.py` untouched (mtime
2026-09-08 00:56:51). **`data/captures_val.json` was never opened —
atime still 2026-09-05 06:34:02.** No git commands (not a repo).

---

## 19. LEVER B — GEOMETRY-AWARE CONFIDENCE (2026-09-08) — host GO; **bench gate in §20, result: GO**

§18.9's follow-up #2 said the residual loss is content, not phase:
`full` was 5 of 6 gate refusals and 55 of 101 soak refusals, `rnd` the
next 39, split `R6 nocand` 51 / `R8 chase` 44. This section is the
decoder phase that goes after it. **Everything here is host-side; no
image has been flashed and no bench measurement is claimed.**

### 19.1 TASK 1 — what R6 actually is, and it is NOT what the brief assumed

The brief's hypothesis: a bit whose **discriminating interval** — the
window between `T0H_eff` (377 ns) and `T1H_eff` (752 ns) after its own
rising edge, the only place a sample can tell 0 from 1 — received **no
sample**, so the width bracket admits both hypotheses while the margin
looks large. **Measured, that class is essentially empty.**

Two independent detectors were built (`dev_lever_b/dwlib.py`):

* **A, the bracket rule** — inside the decision pass, from the segment's
  own fall bracket `(u, v]` and the family-calibrated boundaries: the
  bracket *contains* the whole interval, so no sample can be inside it
  (`u`/`v` are adjacent samples).
* **B, the sample census** — map every capture sample to wire TU with the
  decoder's own `(K, tau)` and ask whether any lands in the interval.
  This is `dev_prod/sweeplib.bit_visibility`'s concept done in the
  decoder's integer frame.

Over the ND = 48 production sweep they agree closely (both 65 / A-only 13
/ B-only 20 bits). And both say the same thing about the refusals
(`dev_lever_b/characterize.py`, 840 synthetic ND = 48 frames over the
trim band × the measured arm range 70–658 ns, plus the 90 real captures):

| | R6 `nocand` | R8 `chase` |
|---|---:|---:|
| refused frames | 32 | 31 |
| wrong payload' bits, mean / max | 1.28 / 5 | 2.03 / 5 |
| wrong-bit margins, min / p50 / max (TU) | 9 / 18 / 38 | 0 / 16 / 39 |
| wrong bits with margin ≤ `MG_MAX` (8) | **0 %** | 31.7 % |
| **wrong bits that are UNSAMPLED-interval (detector A)** | **0 of 41** | **0 of 63** |
| **… (detector B)** | **0 of 41** | **0 of 63** |

**THE TASK-1 BOUND, stated before implementing: the literal dead-window
class bounds Lever B at ~0 %.** On the real ND = 16 corpora the only
instance is 1 of the 3 wrong bits in the single R8 frame. This was then
confirmed end-to-end: a lever admitting *only* that class was measured at
**+0 deliveries and −1** (`dev_lever_b/order.py`).

**What R6 actually is.** Dumping a refused `full` frame bit by bit
(`dev_lever_b/dump_r6.py`) shows the mechanism. Bit 219, truth 0,
decoded 1, margin 21 TU, fall bracket `u = 177, v = 306`, family
boundaries `h0e = 148, h1e = 314`. The interval **was** sampled — a HIGH
at 177 and a LOW at 306, both inside it. But the bracket sits *inside*
`(h0e, h1e)`: **neither** candidate fall position is in the bracket, so
the decoder picks the nearer one (`|177−148| = 29` against
`|314−306| = 8`) and loses. The evidence is a sample in the 23 ns sliver
between the fitted 377 ns boundary and the true 400 ns fall — a
*width-fit* miss, not a missing sample.

That is the **dual** of the assumed condition, and the two have one
closed form. With `ga = (A ≤ u)` and `gb = (v < B)` for the bit's two
candidate fall positions `A`/`B`, `ga != gb` is healthy (exactly one is
inside the bracket, i.e. a sample decided the bit) and `ga == gb` is
degenerate — either the bracket inside the window (**MID**, the sliver)
or the window inside the bracket (**DEAD**, the brief's class).
`dev_lever_b/geomclass.py`, 362 880 payload' bits:

| class | bits | share | wrong | **P(wrong)** |
|---|---:|---:|---:|---:|
| **DEAD** | 78 | 0.02 % | 7 | **8.97 %** |
| **MID** | 3 476 | 0.96 % | 310 | **8.92 %** |
| ONLY_A | 285 479 | 78.67 % | 265 | 0.0928 % |
| ONLY_B | 53 967 | 14.87 % | 52 | 0.0964 % |
| EARLY | 2 903 | 0.80 % | 0 | **0.0000 %** |
| LATE | 16 977 | 4.68 % | 0 | **0.0000 %** |

**1 % of the bits carry half the wrong bits — 91× enrichment**, and the
two degenerate classes are equally dangerous. Per refusal class, the
share of frames whose wrong bits are *all* MID or DEAD: **R6 78.1 %
(25/32), R8 67.7 % (21/31)**; with `W_MAX = 2` and a top-8 ranked
prefix, **R6 78.1 %, R8 58.1 %** — a combined ceiling of **68.3 % of
those 63 refusals** (`dev_lever_b/repairable.py`). That is the number
Lever B was allowed to chase.

**Why the v1 archive did not find this.** `archive/design-phase/approaches/combined.py`'s
`DEAD_PRIOR_NATS` and the `dev_audit` per-family study are about the
**DEAD** class — and every DEAD bit already carries **margin 0** through
§7's tie mark, so it is already weak and already a candidate. Of 590
DEAD bits over 1 530 frames, **exactly 0 have margin > `MG_MAX`**. The
machinery cut from the embedded port was cut from the class that was
already handled.

### 19.2 TASK 2 — the design, and what was measured OUT of it

Full normative text: `EMBEDDED_V2_SPEC.md` §6.4. In brief:

**Detector**, per payload' bit, stateless, integer, O(bits):

```c
uint8_t is_dw = 0;
if (off < DW_OFF_MAX /* 64 */) {
    int16_t hb = (int16_t)(off << BIT_SH);
    is_dw = (((int16_t)(hb + h0e) <= u) == (v < (int16_t)(hb + h1e)));
}
```

Two s16 compares and an equality. `DW_OFF_MAX` costs nothing in
behaviour (`h0e ≥ 64 > 0`, so past the bracket the test already answers
"healthy"); it only keeps `hb + h1e` inside s16 on a long merged run.
**Proven bit-identical to a latched running-`hb` form over 3 483 frames,
every corpus and both fuzz sets** (`dev_lever_b/equiv_hb.py`: 0
differing).

**Policy.** A bit with `is_dw && margin > MG_MAX` joins the candidate
list through the **unchanged §6.2 sorted insertion**. No second pool, no
second key: a weak margin is `≤ MG_MAX` and a DW margin `> MG_MAX`, so
the single ascending key already puts every weak entry first. Therefore
**R7's completeness invariant is structural** (a DW entry can never
displace a weak one), **truncation drops the worst DW entry first**, and
**R6 becomes literally `n_cand == 0`**. `A_MAX`, `T_MAX`, `MG_MAX`,
`MG_PAIR`, `A_PAIR`, `TIE_EMIT`, `W_MAX` are **all unchanged**; §7.10's
`npair` reads `n` at these constants, which is what `decode.c` compiles
and `decode_asm.s` assembles.

**Ranking first: measured irrelevant, so not shipped.** The brief asked
for the DW bits ranked ahead of the weak ones. A two-ended layout that
does exactly that was built and compared **frame by frame**: over 3 483
frames the two differ in *outcome* on **one**, where the simple form
delivers and the ranked-first form refuses at the `T_MAX` budget; 156
more differ only in `trials`/`comps`. The simple form is ~80 B of
assembly and 3 B of RAM cheaper and needs no invariant repair, so it is
what ships. Reported as a deviation from the brief, with the data.

**Prior: measured out.** The audit's per-family finding *reproduces* —
in the admitted pool a bit decoded **1** is wrong 21.27 % of the time
against 2.34 % decoded 0, and family 1 with `decoded = 1` is wrong
**92.1 %** (314 of 341) while families 0/1/5 decoded 0 are wrong 0 %
(`dev_lever_b/prior.py`). Neither use pays: ordering by it gains 0
deliveries and **costs +2 median comparisons**; admitting only decoded-1
bits saves 6 median comparisons but **loses 4 deliveries**, against a
`T_MAX` exhausted on 0.06 % of frames. **Left out**, no table shipped.

**Budget pressure — reported, NOT acted on** (`dev_lever_b/pressure.py`,
6 450 frames):

* the list truncates on **42.6 % of chases** (273 of 641); `n_weak+n_dw`
  over chased frames is p50 11 / p90 27 / p99 67 / **max 89**, so
  `A_MAX = 89` would end truncation — 4 006 flip sets against 67;
* `T_MAX` exhausted on **4 of 6 450 (0.06 %)**, 0.62 % of chases, and
  **no delivered frame came within 10 comparisons of it**;
* **a bigger `T_MAX` buys nothing measured.** Re-decoding the entire grid
  at 200 / 262 / 658 comparisons (`crc.fa_prob` 0.30 % / 0.40 % / 1.00 %):
  **+0 deliveries, +0 wrong** at every step. The 4 exhausted frames do
  not have their repair in the list at all;
* a bigger `A_MAX` does buy deliveries and does cost: **+16 at 16, +63 at
  27, both 0 wrong — but +142 at 89 with +1 WRONG**, and `A_MAX` is also
  the R7 admission cap, so raising it re-admits the broadly-wrong frames
  §7.5 was built to refuse. **Owner's decision. Not taken.**

### 19.3 Flash, RAM and time — it fits with MORE room than before

The feature is **+30 B** of assembly and **+2 B** of zero page. Against
17 B of contiguous headroom (the guard's "34 B free" counts 15 B in the
`0x9FF1..0x9FFF` gap that CODE cannot reach) that needed levers. Three
were taken; all are pure size refactors with no feature or wire change.

| lever | claimed | **measured** | proof |
|---|---:|---:|---|
| **NEW — the `ins1` lever.** The §6 dead-window tie mark tested `a_hat in {ins0, ins1}`, and that test is **always true**: an interior boundary has hinge cost 0 and argmin's key is `(cost, NOT interior, index)` ascending, so a non-empty interior set forces `a_hat == ins0`. `ins1` is never read. | — | **26 B** | `dev_lever_b/ins0_proof.py`: **1 619 577 decided segments**, every corpus + both fuzz sets, **0 counterexamples** |
| merge the two interior-count loops into one pass over `0..acap` (the `[lo,hi]` range is a subset) | — | **11 B** | values identical by construction; host parity + ucsim |
| §15.0 **lever 1** — `dec_info` into the ABS zero page, swapping out `labx0/labx1/labx0b/labx1b/c_c0` (20 B, indexed-only, same 3-byte encoding in either area) | ~30 B | **37 B** | `sizeof(dec_info_t) == 23` static-asserted in `decode.c` against the `.ds 23` reservation |
| short-form addressing — 29 references to the two ABS zero-page blocks were written long-form and sdasstm8 does not shorten them itself | — | **~26 B** | pure encoding change |

**Result.**

| | baseline (§18) | **Lever B** |
|---|---:|---:|
| `CODE` | 7 560 B | **7 552 B** (−8 B *with* the feature) |
| terse image, guard "flash free" | 34 B | **42 B** |
| verbose image | 38 B | **46 B** |
| `DZP0` (ABS zero page) | 238 B | 242 B |
| `DATA` | 635 B @ `0x00F0` | 632 B @ **`0x00F3`** |
| `SSEG` / stack region | `0x036B` / **148 B** | `0x036B` / **148 B — unchanged** |
| statics | 876 / 1024 | **875 / 1024** |
| peak stack (§18 CFG walk) | 115 B → 33 B margin | **unchanged** |

`--data-loc` is **`0xF3` precisely** so that `cap_arm.s`'s `s_arm` keeps
its address and the pinned arm block stays byte-identical: the DATA
offset of `s_arm` fell by 3 B (decode.c lost `dec_info`, `decode_asm.s`
gained the calibration arrays), so the base rises by 3. Verified, not
assumed — see §19.4.

**Where the new RAM lives.** `v_ndw` is a u16 in the ABS zero page,
exposed as a **linker global** rather than a `dec_info` field, so the
target pays 2 B of RAM and nothing for reporting; the host-parity and
ucsim harnesses read the counter itself. `m_i1` (1 B) was freed by the
`ins1` lever. There is **no bitmap**: the detector is stateless.

**Time.** ucsim ticks over the 24-case production set: min 4 108 487 /
p50 4 563 628 / **max 4 804 401**, against §18.6's 4 141 357 / 4 460 899
/ 4 811 722 — **the max is 7 315 ticks LOWER**. The p50 rises 2.3 %
because more frames are chased. The heaviest chase is
`comps = 131, trials = 50` at 4 620 713 ticks. Against the established
silicon/ucsim ratio that projects **≈ 195 ms**, inside the 250 ms
cadence — and, as in §16.7, **the worst case remains unobserved on
silicon**.

### 19.4 TASK 4 — re-proof, every check re-run

| proof | tool | result |
|---|---|---|
| `make verify` | — | **PASS, all 8 stages** |
| clean rebuild, **twice** (`rm -rf build && make all`) | — | all three ledger md5s **byte-identical both passes** |
| `capture.ihx` | md5 | **`84955f771ef8ad41a36fc16187afca38` — UNCHANGED** |
| link guard, terse / verbose | `guard_prod.py` | `REL end 0x9F48 / 0x9F44 <= CAPARM 0x9F63; _cap_loop 0x9FAF phase 0xF; flash free 42 B / 46 B` |
| guard check 6 **negative-tested** | tampered map | fails with *"`_cap_arm 0x9F62 != CAPARM_ORG_EXPECT 0x9F63`"*, rc = 1 |
| **pinned blocks** | `dev_arm/absmd5.py` | `CAPLOOP 0x9FA1..0x9FF0` **`273e269f…` OK** · `0x9FF1..0x9FFF` **`9ddd0227…` OK** · `CAPARM 0x9F63..0x9F9E` **`df991ffd…` OK** · `0x9F63..0x9FFF` **`964dcb4d…` OK**; differing bytes between the two images **0**. The two `0x9F65`/`0x9F66` rows DIFF by design (§16/pre-§16 arms, informational) |
| host parity `decode.c` ↔ `embedded_v2.py`, every corpus + both fuzz sets, now also diffing the new `n_dw` counter | `dev_prod/parity_v23.py` | **549/549 bit-identical** |
| ucsim, the SHIPPED `decode_asm.s`, production geometry | `dev_prod/ucsim_v23.py --nd=48` | **24/24 bit-identical** |
| … test geometry | `--nd=16` | **24/24** |
| … capture byte 0 bits 7..6 forced to 11 | `--nd=48 --b0=C0` | **24/24** |
| byte-0 invariance across every corpus + real dumps + fuzz | `dev_fe/b0_invariance.py` | **836 captures × 4, 0 mismatches** |
| v2.3 fuzz set | `dev_prod/fuzz_v23.py --report` | **273 cases, 115 emitted (was 113), 115 correct, 0 WRONG** |
| `embedded_v2.py` self-test | — | PASS |
| Klipper macro | `klipper/verify_macro.py` | 93 passed, 0 failed |

**A real bug the ucsim proof caught.** The first assembly draft put
`clr a` **between** `cpw` and the SIGNED branch that reads its flags —
`CLR` touches N/Z, so `ga` was decided on the wrong flags. **15 of 24
ucsim cases mismatched**, with the assembly admitting far more candidates
than the reference (`trials 60` against `20`). Moving the `clr` before
the compare fixed it; no other site in the file has that shape. Host
parity could not have caught it (the C is correct); this is exactly what
the on-target harness is for.

**New ledger.**

| image | md5 | |
|---|---|---|
| `build/rbarf_prod.ihx` | **`b8f0ae06e740e0f811ff3ebcb0a201ab`** | was `63963743…` (34 B free) |
| `build/rbarf_prod_verbose.ihx` | **`5524ce94f4ae3cb404503beccb0b9373`** | was `04f09f47…` (38 B free) |
| `build/capture.ihx` | `84955f771ef8ad41a36fc16187afca38` | **UNCHANGED** |
| `CAPLOOP` / `CAPARM` rows | `273e269f…` / `9ddd0227…` / `df991ffd…` / `964dcb4d…` | **all four HARD-PINNED and byte-identical** |

Re-recorded in `Makefile` (`LEDGER_MD5` + the header banner),
`README.md` and `docs/ARCHITECTURE.md`. `dev_arm/absmd5.py`'s `LEDGER` needed
no edit — it pins only the arm/loop blocks, and those did not move.

### 19.5 TASK 3 — host yield, before and after, same grid both ways

The "before" column is the **same binary decision path with `DW_EN = 0`**
— a one-constant revert — so the comparison is not against a historical
record but against the feature switched off on the identical grid.

**Real silicon corpora** (`dev_prod/v23bench_score_v23_real.py`):

| corpus | before | **after** | |
|---|---:|---:|---|
| `captures_v23.json` | 53/54 (98.15 %) | **53/54** | the miss is `R8`, and its wrong bits are outside the class — the §19.1 ceiling, exactly |
| `captures_v23_val.json` | 35/36 (97.22 %) | **36/36 (100 %)** | **+1**, an `R6 nocand` on `vrnd7` — an `rnd`-class payload |
| **pooled** | **88/90 (97.78 %)** | **89/90 (98.89 %)** | 0 WRONG either way |

**Synthetic production sweep, ND = 48**, 10 production payloads × 12 arm
phases over the **measured** 70–658 ns range (`dev_lever_b/yield_ref.py`):

| eps band | before | **after** | gain | lost | new WRONG |
|---|---:|---:|---:|---:|---:|
| trim band (−1.6…−0.4 %) | 768/840 (91.43 %) | **812/840 (96.67 %)** | **+44** | **0** | **0** |
| plateau (−2.5…+0.25 %) | 1 201/1 440 (83.40 %) | **1 260/1 440 (87.50 %)** | **+59** | **0** | **0** |
| whole envelope (±8 %) | 980/4 920 (19.92 %) | **1 010/4 920 (20.53 %)** | **+30** | **0** | **0** |

`R6 nocand` over the plateau grid falls **40 → 2**; `R8 chase`
157 → 136. Every gain comes out of those two: 30 from `R6`, 29 from
`R8`.

**Per payload, plateau band** — the `R6` carriers are exactly where it
lands:

| payload | before | **after** | |
|---|---:|---:|---|
| **`full`** (all `0xFF`) | 56/144 | **103/144** | **+47** |
| **`rnd`** | 117/144 | **123/144** | **+6** |
| `dark` | 130/144 | 132/144 | +2 |
| `preset_spin` | 131/144 | 133/144 | +2 |
| `fade` | 124/144 | 125/144 | +1 |
| `seq_plain` | 128/144 | 129/144 | +1 |
| `blink`, `colors`, `preset_rainR`, `seq_pause` | — | — | +0 (already ≥ 126/144) |

**`rnd`-class yield is NOT nil** — the owner's scope note asked for that
number explicitly. `+6/144` on the plateau (+4.2 pp), `+2/84` in the trim
band, and the one real-silicon frame recovered is `vrnd7`. `full` — the
officially out-of-scope stress case — is where the bulk is, as expected.

**THE WRONG-EMISSION GRID at the shipped constants**
(`dev_prod/wrong_emission_final.py --t0-lo 70 --t0-hi 658`, 12 arm
phases × plateau/fast/envelope eps sets × both geometries; the tool
gained a `--dw-en` A/B flag whose default is unchanged):

| | `DW_EN = 0` (before) | **`DW_EN = 1` (shipped)** |
|---|---:|---:|
| decodes | 133 380 | 133 380 |
| emissions | 63 638 | **65 181 (+1 543, +2.42 %)** |
| WRONG | 8 | **9** |
| rate | 0.0126 % | **0.0138 %** |
| **95 % Clopper–Pearson upper** | ≤ 0.0227 % | **≤ 0.0241 %** |
| **ND = 48 plateau — the SHIPPED geometry in the trim band** | 13 828 emissions, **0 wrong** | **14 538 emissions, 0 wrong** |
| chase-repaired emissions | 7 390 (11.6 %) | 8 933 (13.7 %) |
| comps over chased frames | p50 5 / p90 38 / max 131 | p50 12 / p90 58 / max 131 |

**Target ≤ 0.2 %: MET, the bound 8.3× inside it.** The `DW_EN = 0`
column reproduces §18.6's recorded baseline *exactly* (0.0126 %,
≤ 0.0227 %, and the same "0 wrong in 13 828 plateau emissions"), which is
the control that says the revert path is the shipped baseline.

**The one extra wrong emission, named.** `ND = 16` (test geometry, **not
shipped**), `val_v5a`, **eps −2.80 %** — outside the delivery plateau
(−2.5…+0.1 %) and far outside the auto-trim band (−1.6…−0.4 %) — at
`t0 = 658.0 ns`, the grid's **top** arm phase, reached through a 30-trial
/ 59-comparison chase; emitted `5a5a5a5a5a5f5a5a5a5a5a5e`, two bits
wrong in a repeating-`0x5A` payload, i.e. an undetectable CRC-16
codeword. Same character as all eight pre-existing ones. `8/63 638`
against `9/65 181` is **z = +0.193, p = 0.847** — not resolvable. Two of
the nine (`ND = 48 colors` at +7.4 % and `seq_pause` at +6.4 %) are
`trials = 0` **direct** accepts and cannot be attributed to any chase
policy at all.

I am reporting the bound as **rising 0.0227 % → 0.0241 %** rather than
rounding it away. It is 8.3× inside the 0.2 % target, it is one frame in
65 181 emissions at a clock and arm phase the product never operates at,
and **the shipped geometry inside the trim band is still 0 wrong in
14 538 emissions**.

### 19.6 What this phase did NOT establish

* **Nothing has been flashed** *in this phase*. **Superseded by §20**,
  which flashed the verbose image and ran the cold + warm 30-frame gate,
  the 15-minute 250 ms soak, Klipper e2e, the carrier payloads and the
  auto-trim band check — all reported there.
* **The worst-case decode is still unmeasured on silicon.** ucsim's
  heaviest case is 4 620 713 ticks (`comps = 131`); the projection is
  ≈ 195 ms against a 250 ms cadence, and §16.7's observation stands that
  a safe `t0` makes deep chases *rarer*, so the gate may again fail to
  produce one.
* **`R7`/`R5` are still exercised only by fuzz and ucsim** — 0
  occurrences in §18's 3 712 bench frames.
* **The MID mechanism is a width-fit miss, so it is calibration-adjacent.**
  Lever B works *around* it with a CRC-verified chase and deliberately
  does not touch the width fit, the lock, the marker gate or the arm. A
  per-family `h0f` correction would attack the cause instead of the
  symptom — and would change every decode rather than only the ones the
  16-bit check verifies. Not attempted; noted as the next idea, and it is
  a calibration change, which is a different risk class.
* **One die, one temperature, host models only.** The eps/`t0` grids are
  the calibrated sampler model, not silicon.

### 19.7 Verdict — host GO, and the bench is the gate

Lever B is correct (0 wrong on every ND = 48 plateau axis, 0 new wrong on
any corpus, the pooled bound 8.3× inside target), bit-exact at all three
levels (549/549 host parity, 24/24 ucsim × 3 configs), properly guarded
(all four pinned blocks byte-identical, check 6 negative-tested,
`capture.ihx` untouched), reproducible (byte-exact ledger from a clean
tree, twice), **smaller than the image it replaces** (−8 B of CODE, 42 B
free against 34), and RAM-neutral (stack region unchanged at 148 B).

It buys **+4.1 pp of delivery on the plateau band and +1 real-silicon
frame**, concentrated exactly where §18.9 said the loss was: `full`
+47/144, `rnd` +6/144, `R6 nocand` 40 → 2.

**Do not read any of this as a silicon result.** The next step is the
bench gate on the new ledger — **now run: see §20, which reproduced every
number above and returned GO.** `R6 nocand` measured **51 → 0** on
silicon (§20.5).

One §19 claim did NOT survive independent re-check: the `order.py`
evidence for not ranking the DW bits first is **not reproducible from
this tree** (§20.7). The shipped ordering is unaffected and bit-exact;
the justification is weaker than presented here.

### 19.8 Artifacts (§19)

`recon/approaches/dev_lever_b/`:

| file | what it establishes |
|---|---|
| `dwlib.py` | the two detectors (bracket rule + sample census) and the instrumented decision pass |
| `characterize.py`, `task1.jsonl.gz` | **TASK 1**: per-refused-frame wrong-bit count, margins and interval-sampled flags |
| `dump_r6.py` | one R6 frame bit by bit — where the mechanism was actually identified |
| `geomclass.py` | the six-class taxonomy and `P(wrong \| class)` |
| `repairable.py` | the ceiling: rank of the wrong bit inside the class, against `W_MAX` |
| `ins0_proof.py` | the `ins1` size lever, 1 619 577 segments, 0 counterexamples |
| `equiv_hb.py` | stateless `off < 64` detector ≡ latched running-`hb`, 3 483 frames |
| `order.py` | ranked-first vs one-list, and DEAD-only vs MID-only, frame by frame — **STALE: does not run as committed, and its ranked-first arms are invalid against the shipped invariants; repaired and documented in §20.7** |
| `prior.py` | the per-family prior: it reproduces, and it does not pay |
| `proto.py`, `tune.py`, `sweep_proto.py` | the parameter search that picked the design |
| `pressure.py` | truncation rate, `T_MAX`/`A_MAX` A/B at the real cost |
| `yield_ref.py` | before/after yield per corpus and per payload |
| `wrong_emission_{leverb,dwoff}.{jsonl.gz,log}` | the 133 380-decode grid, both ways |

**Bench discipline.** Every `ucsim` child ran under `setsid timeout -k`
with a `pkill` sweep; **0 strays at exit on every run**. No image was
flashed. `bench/demo.py` untouched. **`data/captures_val.json` was never
opened.** All work is on branch `lever-b/geometry-aware-confidence`;
`main` was not touched.

---

## 20. INDEPENDENT RE-GATE — LEVER B ON SILICON (2026-09-08) — **GO**

An independent re-gate of the `lever-b/geometry-aware-confidence` branch:
every §19 number re-measured from a clean tree rather than trusted, then
the bench gate §19.6 said still had to run. **Lever B delivered on
silicon, and by more than §19 predicted.** Nothing in the firmware was
changed by this phase; the one source edit is a repair to a stale
measurement script (§20.7).

### 20.1 Static re-proof — every §19 claim reproduced

| check | result |
|---|---|
| clean rebuild (`rm -rf build && make all`) ×2 | all three ledger md5s **byte-identical on both passes** |
| `build/rbarf_prod.ihx` | `b8f0ae06e740e0f811ff3ebcb0a201ab` ✅ as §19.4 recorded |
| `build/rbarf_prod_verbose.ihx` | `5524ce94f4ae3cb404503beccb0b9373` ✅ |
| `build/capture.ihx` | `84955f771ef8ad41a36fc16187afca38` ✅ **unchanged, as required** |
| `make verify` | **PASS, all 8 stages**, from a clean tree |
| link guard, terse | `REL end 0x9F48 <= CAPARM 0x9F63`, `_cap_loop 0x9FAF` phase `0xF`, **42 B free** |
| link guard, verbose | `REL end 0x9F44`, **46 B free** |
| `absmd5` pinned blocks, both images | all four `OK`; **0 differing bytes** between the two images above `0x9F63` |
| guard check 6, negative test | tampered map → `_cap_arm 0x9F62 != CAPARM_ORG_EXPECT 0x9F63`, **rc = 1** |
| host parity (`decode.c` vs `embedded_v2.py`) | **549/549 bit-identical** |
| ucsim, shipped `decode_asm.s` | `--nd=48` **24/24**, `--nd=16` **24/24**, `--nd=48 --b0=C0` **24/24** |
| ucsim ticks ND=48 | min 4 108 487 / p50 4 563 628 / max 4 804 401 — §19.3 exactly |
| ucsim ticks ND=16 | min 1 907 809 / p50 2 098 974 / max 2 286 393 — §19.3 exactly |
| `fuzz_v23 --report` | 273 cases, 115 emitted, **0 WRONG** |
| `ins0_proof.py` | 1 619 577 decided segments, **0 counterexamples** |
| `equiv_hb.py` | 3 483 frames, **0 differing** |
| out-of-scope sources vs `main` | `cap_arm.s`, `caploop.s`, `cap_code.s`, `scan.s`, `capture.c`, `guard_prod.py`, `bench/demo.py` all **byte-identical** |
| `data/captures_val.json` | **never opened** — atime still `2026-09-05 06:34:02` |
| stray simulator processes | **0** at the end of every run |

### 20.2 Host A/B re-measured — §19.5 and §19.3 reproduce exactly

Same one-constant revert (`DW_EN = 0`), same grids, re-run here:

| grid | before | after | Δ | lost | new WRONG |
|---|---:|---:|---:|---:|---:|
| real `captures_v23` | 53/54 | 53/54 | +0 | 0 | 0 |
| real `captures_v23_val` | 35/36 | **36/36** | **+1** | 0 | 0 |
| real pooled | 88/90 (97.78 %) | **89/90 (98.89 %)** | **+1** | 0 | **0** |
| synth ND=48 trim band | 768/840 (91.43 %) | **812/840 (96.67 %)** | **+44** | 0 | **0** |
| synth ND=48 plateau | 1 201/1 440 (83.40 %) | **1 260/1 440 (87.50 %)** | **+59** | 0 | **0** |
| synth ND=48 envelope | 980/4 920 (19.92 %) | **1 010/4 920 (20.53 %)** | **+30** | 0 | **0** |

The recovered real frame is `vrnd7` — an **`rnd`-class** payload, exactly
as §19.5 named it. `R6 nocand` over the plateau grid falls **40 → 2**;
per payload `full` 56 → 103 (+47), `rnd` 117 → 123 (+6).

**Wrong-emission grid, 133 380 decodes, run BOTH ways** (`--t0-lo 70
--t0-hi 658`):

| | `DW_EN=0` | `DW_EN=1` (shipped) |
|---|---:|---:|
| emissions | 63 638 | **65 181** (+1 543, +2.42 %) |
| WRONG | 8 | **9** |
| rate | 0.0126 % | **0.0138 %** |
| 95 % Clopper-Pearson upper | ≤ 0.0227 % | **≤ 0.0241 %** |
| ND=48 plateau, trim band | 0 / 13 828 | **0 / 14 538** |
| chase-repaired | 7 390 (11.6 %) | 8 933 (13.7 %) |

The `DW_EN=0` column reproduces §18.6's recorded baseline **exactly**,
which is the evidence that the revert path *is* the shipped baseline. The
extra wrong emission is the one §19.5 named: ND=16 (**test** geometry),
`val_v5a`, eps **−2.80 %**, `t0 = 658 ns` — outside the delivery plateau
and far outside the auto-trim band. **Target ≤ 0.2 %: MET, 8.3× inside.**
`pressure.py` also reproduces: truncation on **42.6 %** of chases, and a
bigger `T_MAX` buys **+0 delivered** at 200 / 262 / 658.

### 20.3 Flash and auto-trim

`build/rbarf_prod_verbose.ihx` (`5524ce94…`), guard green immediately
before the flash, **first attempt**, banner `RBARF-P 1` at **5.06 s**
(the 5 s SWIM window intact). Auto-trim **in band on every frame of every
run**: gate `−1.07…−1.12 %`, soak mean **−0.974 %** sd **0.029 pp**
(1 776/1 776 in `[−1.6, −0.4] %`), warm gate `−0.94…−1.01 %` (30/30).

### 20.4 THE 30-FRAME GATE — cold and warm

`bench/drive_prod.py --reps 3`, VERBOSE image, each frame on the wire
exactly once, scored against the `V:` line.

| run | delivered | direct `O` | chase `C` | refused | no-report | **WRONG** | resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| §18 COLD-1 | 27/30 | 27 | 0 | 3 (`R6`×3) | 0 | **0** | 0 |
| §18 COLD-2 | 29/30 | 28 | 1 | 1 (`R8`) | 0 | **0** | 0 |
| §18 WARM | 28/30 | 28 | 0 | 2 (`R8`×2) | 0 | **0** | 0 |
| **this COLD** | **29/30 (96.7 %)** | 25 | **4** | 1 (`R8`, `full`) | 0 | **0** | **0** |
| **this WARM** (post-soak) | **30/30 (100 %)** | 28 | **2** | **0** | 0 | **0** | **0** |
| **pooled, 60 frames** | **59/60 (98.3 %)** | 53 | **6** | 1 | 0 | **0** | **0** |

**The ≥ 28/30 bar is met on both runs**, warm is a clean sweep, and the
single refusal is `R8`, not `R6`. **`R6 nocand` = 0 in all 60 gate
frames** (§18 had 3). Six of the 59 deliveries came **through the chase**
against §18's 1 in 90 — the admission rule doing exactly its job.
Decode window min 163.7 / mean 170.0 / max **182.9 ms**, latency peak
**196.7 ms**, inside the 250 ms cadence.

**On-silicon control.** A `DW_EN=0` image was built from the same tree
(one instruction: the SS6.4 admission `call dwtst / jrne` replaced by an
unconditional skip), guard green, **capture and arm blocks byte-identical
by `absmd5`**, so the A/B isolates the decoder alone. Its cold gate:
**28/30, and BOTH refusals are `R6 nocand` on `full`** — the mechanism
Lever B was built for, still present when it is switched off.

### 20.5 Soak — 15 minutes, hard 250 ms cadence

`dev_prod/v23gate_soak.py --secs 900 --spacing-ms 250` (§18.4 used
`dev_fe/soak_fe.py`; same cadence and duration, a different harness —
noted, not hidden).

| | §18.4 (previous image) | **this run (Lever B)** |
|---|---|---|
| frames sent / reports | 3 601 / 1 846 (51.3 %) | **3 600 / 1 813 (50.4 %)** |
| **delivered CORRECT** | 1 745 = **94.5 %** of reports | **1 776 = 97.96 %** of reports |
| refused | 101 — **`R6` 51**, `R8` 44, `R3` 5, `R4` 1 | **37 — `R6` 0, `R8` 36, `R3` 1** |
| **WRONG emissions** | **0** | **0** |
| misattributed / protocol errors | 0 / 0 | **0 / 0** |
| **MCU resets** | **0** | **0** |
| eps mean / sd / in band | −1.018 % / 0.0211 pp / 1 745 of 1 745 | **−0.974 % / 0.029 pp / 1 776 of 1 776** |
| eps drift (first vs last quarter) | +0.0075 pp | **+0.042 pp** |

**`R6 nocand` 51 → 0.** That is the entire point of Lever B and it is
measured, not projected. Total refusals fall **101 → 37** (−63 %) and
delivered-per-captured rises **94.5 % → 97.96 %**: z = **+5.45**,
p < 10⁻⁷ — the first delivery change in this project's bench history that
is resolvable rather than noise.

**One honest cost.** Reports fell 1 846 → 1 813 (51.3 % → 50.4 % of
frames sent). More frames now enter the chase, each chase lengthens the
decode blind window, and a frame arriving inside it is never captured.
Net **delivered-per-frame-sent still rises, 48.5 % → 49.3 %** — the
refusal collapse dominates the duty-cycle cost, but the cost is real and
is the price of the extra candidates.

### 20.6 The carrier payloads, and the honest answer on `rnd`

`full` and `rnd` driven single-shot on both images. The 90-rep pair is
**thermally matched** (eps `−0.73…−0.48 %` before, `−0.72…−0.46 %`
after), which the 30-rep pair is not — the unit warms across runs and eps
drifts, so only the matched pair is quoted as the result.

| payload | `DW_EN=0` (before) | Lever B (after) | Δ |
|---|---:|---:|---:|
| **`full`**, n = 90 | **50/90 (55.6 %)** — `R6` 33, `R8` 4, silent 3 | **90/90 (100 %)** — no refusals | **+40, +44.4 pp** |
| **`rnd`**, n = 90 | **89/90 (98.9 %)** — `R8` 1 | **89/90 (98.9 %)** — `R8` 1 | **±0** |
| `full`, n = 30 (unmatched) | 14/30 — `R6` 8, `R8` 8 | 29/30 — `R8` 1 | +15 |
| `rnd`, n = 30 (unmatched) | 29/30 | 28/30 | −1 |

**`full` is transformed: 55.6 % → 100 %, `R6` 33 → 0**, and 41 of the 90
deliveries are chase repairs. Against §17's ~3/31 this payload has gone
from the worst case in the project to a clean sweep.

**`rnd` shows no change under single-shot carrier drive, and I am
reporting that as a null.** The reason is visible in the data rather than
inferred: on this unit at this eps, `rnd` single-shot already refuses at
**1/90 with zero `R6`**, so there is no `R6` headroom on this axis to
recover. Lever B can only convert `R6`; where `R6` is already 0 it does
nothing. The `rnd`-class evidence therefore rests on the three axes where
`R6` *was* present:

* the **soak**, where `R6` 51 → 0 across all ten payloads and total
  refusals fell 101 → 37 (§18.4 attributed 39 of its 101 refusals to
  `rnd`; the soak harness records causes, not per-payload attribution of
  refusals, so `rnd`'s exact share of the −63 % is not separable);
* **Klipper** (§20.8), where `rnd_colors1` and `rnd_colors2` both went
  from refusing to **3/3**;
* the **real-silicon corpus**, where the one recovered frame is `vrnd7`,
  and the **host plateau grid**, `rnd` 117/144 → 123/144 (+6, +4.2 pp).

So the owner's requirement — the `rnd`-like class must improve — is met
on the soak, on Klipper, on the real corpus and on the host grid, but
**not** on this unit's single-shot carrier drive, where it was already at
ceiling. That is weaker than "`rnd` improves everywhere" and is stated as
such.

### 20.7 A stale proof artifact, found and repaired

`dev_lever_b/order.py` — cited in §19.8 as the evidence for **deviating
from the brief's explicit "ranked first" instruction** — **did not run**
in the committed tree: it reads `e.DW_MAX` off the reference, and
`DW_MAX` was deleted from `embedded_v2.py` by `4be7a95` ("simplify to one
candidate list"), where it had been `DW_MAX_V23 = 8`. It raised
`AttributeError` on every frame.

Repaired here by carrying `DW_MAX = 8` locally, at the value the
superseded two-ended design used. With that, the script runs — and shows
that it can no longer measure what it is cited for:

* `V1` maps to *no patch*, so on the shipped tree it is the **shipped
  one-list insertion**, not the ranked-first layout its docstring
  describes. `V5` re-implements the same insertion and the two agree
  exactly (**1 260 / 1 260**) — a self-consistency check, nothing more.
* `V2`/`V3`, the actual two-ended arms, raise the shipped reference's own
  §6.2 invariants (`n == min(n_weak + n_dw, A_MAX)` and
  `n_weak == |{m ≤ MG_MAX}|`) on **87 of the plateau frames**, because a
  two-ended layout packs DW entries from the top of the array. Their
  columns are not a valid outcome comparison.

**Consequence, stated plainly: §19's "ranked-first differs in outcome on
exactly one frame in 3 483" is NOT reproducible from this tree.** It
holds only against the `ea10c29` reference. The staleness is now recorded
in the script's docstring. This does **not** touch the shipped ordering,
which is proved bit-exact by other means (549/549 host parity, 24/24
ucsim × 3 configs) — but the *justification* for the deviation is weaker
evidence than §19 presented, and re-establishing it needs the
ranked-first arms rebuilt against the shipped invariants.

### 20.8 Klipper end-to-end

`bench/test_klipper_macro.py --bench-is-free --reps 3`, all 17 cases × 3,
60-byte `frame` variant.

| run | delivered | direct | chase | refused | **catastrophic** | protocol errors | silent |
|---|---:|---:|---:|---:|---:|---:|---:|
| §16.7 | 46/51 (90.2 %) | 45 | 1 | 5 | **0** | 0 | 0 |
| §18.5 | 47/51 (92.2 %) | 42 | 5 | 4 | **0** | 0 | 0 |
| **this run** | **50/51 (98.0 %)** | 44 | **6** | **0** | **0** | **0** | 1 |

**All four of §18.5's refusals are gone** — including its `R6` on
`rnd_colors2` — and **16 of 17 cases go 3/3**. The single miss is a
*silent* frame (never captured: render or blind-window overlap), not a
refusal, so **the refusal count on this axis is now zero**.

### 20.9 Wrong emissions — the headline axis

**Zero on silicon, everywhere, on both images.** On the shipped image:
29 cold-gate + 30 warm-gate + 1 776 soak + 50 Klipper + 236 carrier
emissions ≈ **2 121 emissions, 0 CATASTROPHIC, 0 misattributed, 0
protocol errors, 0 MCU resets**. The `DW_EN=0` control image added ~210
more emissions, also 0 wrong.

The **host** bound rose, and it is reported rather than rounded away:
**≤ 0.0227 % → ≤ 0.0241 %**, one extra wrong emission in 65 181, at
ND=16 test geometry, eps −2.8 %, top arm phase — none of which the
product operates at. z = +0.193, p = 0.847: not resolvable. On the
shipped ND=48 geometry inside the trim band the count is **0 in 14 538**,
up from 0 in 13 828. **If the owner's rule is "the bound may not increase
at all", this does not pass and `DW_EN = 0` is the one-constant revert.**

### 20.10 Criteria table

| criterion | bar | result | |
|---|---|---|---|
| clean rebuild reproduces ledger | twice | byte-identical ×2 | ✅ |
| `capture.ihx` unchanged | `84955f77…` | unchanged | ✅ |
| guard green on both maps | required | 42 B / 46 B free | ✅ |
| pinned blocks unchanged | `absmd5` | all four OK, 0 diff | ✅ |
| `make verify` | 8/8 | PASS | ✅ |
| host parity | 549/549 | 549/549 | ✅ |
| on-target parity | 24/24 ×3 | 24/24 ×3 | ✅ |
| auto-trim in band | all frames | 1 836/1 836 | ✅ |
| 30-frame gate, cold | ≥ 28/30 | **29/30** | ✅ |
| 30-frame gate, warm | ≥ 28/30 | **30/30** | ✅ |
| **wrong emissions on silicon** | **0** | **0 in ~2 121** | ✅ |
| host wrong-emission bound | ≤ 0.2 % | ≤ 0.0241 % | ✅ |
| **`R6 nocand` driven to ~0** | Lever B's purpose | **51 → 0 in the soak, 0 in 60 gate frames** | ✅ |
| soak resets | 0 | **0** | ✅ |
| `T_MAX` / `A_MAX` / gates unchanged | required | unchanged | ✅ |
| `rnd`-class improves | required | soak / Klipper / real corpus **yes**; single-shot carrier **null** | ⚠️ |
| `order.py` deviation evidence | reproducible | **not reproducible** (§20.7) | ⚠️ |

### 20.11 Verdict — **GO for merging `lever-b/geometry-aware-confidence`**

Lever B works on silicon and it works by the mechanism it claimed. `R6
refuse_nocand`, which was 51 of 101 soak refusals and 3 of 6 gate
refusals on the previous image, is **0** — in a 3 600-frame soak, in 60
gate frames, and in a 180-frame carrier run. Total soak refusals fell
**101 → 37**, delivered-per-captured **94.5 % → 97.96 %** (p < 10⁻⁷),
Klipper **47/51 → 50/51 with zero refusals**, the warm gate is a clean
**30/30**, and `full` went **55.6 % → 100 %**. Correctness held
everywhere it is measurable: **0 wrong emissions in ~2 121 silicon
emissions**, 0 new wrong on any corpus, the host bound 8.3× inside
target. The image is smaller than the one it replaces and every pinned
block is byte-identical.

Two things go to the owner rather than being resolved here, both flagged
above and neither a firmware defect:

1. **The host wrong-emission bound rose** 0.0227 % → 0.0241 % (§20.9).
   One frame, test geometry, outside the operating envelope, statistically
   unresolvable. A "no increase at all" rule makes this a NO-GO with a
   one-constant revert.
2. **`rnd` single-shot shows no gain** (§20.6) because it was already at
   ceiling with zero `R6` on this unit; the `rnd`-class improvement is
   real on the soak, Klipper, the real corpus and the host grid.

`A_MAX` remains the largest untaken delivery lever (§19.3: +16 at 16, +63
at 27, +142 and **+1 wrong** at 89) and is untouched, as instructed.

---

## 21. THE `A_MAX` x `T_MAX` CHASE BUDGET — SWEPT, AND MADE A BUILD PARAMETER (2026-09-08)

Full report: **`recon/AMAX_TMAX_SWEEP.md`**.  Branch `amax-tmax-sweep`.
**Host measurement plus a firmware parameterisation.  Nothing was
flashed; no bench number is claimed here.**

> **SILICON RESULT ADDED 2026-09-08 — see `recon/AMAX_TMAX_SWEEP.md` §9.**
> All three images were benched with the owner's acceptance metric
> (`bench/suite_singleshot.py`, first-try latch) in the order
> baseline -> MODERATE -> AGGRESSIVE -> baseline: **204 / 202 / 199 /
> 196 of 210**.  The two baseline runs bracket **8 frames** and both
> candidates land inside that bracket; the four totals fall on a line in
> RUN ORDER (-2.7 frames/run, R^2 = 0.992) whose last point is a
> baseline, so **the delivery gain is below this metric's resolution**.
> Correctness held — **0 WRONG in 801 accepted frames**, 0 in the
> 30-frame gate on AGGRESSIVE (**29/30**, bar met) and 0 in a 320-frame
> corruption-prone soak; 0 resets in 1 620 frames.  The cost is in the
> tail: worst-case decode **184.6 -> 211.1 ms** (+26.5 ms), median +0.6
> ms, blind window ~196 -> ~223 ms, so a 250 ms cadence no longer fits
> AGGRESSIVE with margin (recommend 300 ms).  **The recommendation is
> unchanged: keep `A_MAX = 11`, `T_MAX = 131`.**

§20's closing line named `A_MAX` "the largest untaken delivery lever".
It was taken up as far as the host can take it, and the answer is
smaller than §19.3's `+16 / +63` estimate suggested, because §19.3
counted deliveries over a different grid and did not hold `T_MAX` fixed.

| | measured here |
|---|---|
| best delivery anywhere on the 5 x 5 grid (`A_MAX` 11..40 x `T_MAX` 131..1048), 70 single-shot payloads x 5 eps x 48 arm phases, ND = 48 | **+13 frames in 16 800 = +0.077 pp**, and **2 WRONG** at production geometry inside the trim band |
| best delivery with **zero** wrong emissions | **+9 (+0.054 pp)**, at `A_MAX = 16`, `T_MAX >= 192` |
| `A_MAX >= 18` | **1-2 WRONG in the operating band**, both named and reproducible.  Categorical stop |
| `T_MAX` on its own | **+0 at every `A_MAX = 11` point**, 131 -> 1048.  Reproduces §19.2/§20.2 |
| the interaction | `A_MAX 16` at `T_MAX 131` is **-4** (a regression: the wider list pushes `prod/full`'s repair past the same 131 comparisons); at `T_MAX 192` it is **+9** |
| real corpus `captures_v23.json` | **53/54 at all 25 points — completely flat** |
| measured false accepts, 40 000 deliberately-corrupted frames | **0.068 % baseline -> 0.096 % -> 0.173 %** at (11,131)/(14,131)/(16,192); 0.389 % at (40,1048).  **Not zero at the baseline either** |
| the R7/R8 mechanism | `A_MAX`'s gain is an **R7 admission conversion** (7 of 8 gains), not a deeper chase: R7 62 -> 36 -> 13 -> 7 -> 1 while R8 rises 820 -> 899 |

**Both constants are now Makefile variables** (`A_MAX ?= 11`,
`T_MAX ?= 131`), one source, propagated to `decode.c` by `-D` and to
`decode_asm.s` by a generated `chase_cfg.inc` (`gen_chase_cfg.py`).
**The three ledger images rebuild BYTE-IDENTICALLY at the defaults** —
`b8f0ae06…` / `5524ce94…` / `84955f77…`, `cmp` clean against the
pre-change build, twice from a clean tree, `make verify` PASS all 8
stages.

Two reproducible VERBOSE bench images exist and are guard-green:

| image | md5 | flash free | stack region |
|---|---|---:|---:|
| `rbarf_prod_verbose_A11_T131.ihx` (baseline) | `5524ce94f4ae3cb404503beccb0b9373` **= the ledger verbose image** | 46 B | 148 B |
| `rbarf_prod_verbose_A14_T131.ihx` (MODERATE) | `952c7446d8e26426c8426792fd56361f` | 46 B | 139 B |
| `rbarf_prod_verbose_A16_T192.ihx` (AGGRESSIVE) | `d8db7f4a27d521026c5b41679b2f2b8e` | 46 B | 133 B |

**Flash cost: zero** (`CODE` 7 556 B and `CONST` 299 B in all three).
**RAM is the binding constraint**: the candidate arrays are REL DATA, so
3 B per `A_MAX` entry comes out of the 148 B stack region, and
`guard_prod.py`'s new **check 7** refuses a link below 124 B — which
makes `A_MAX = 22` **fail the build**, negative-tested.  Stack *depth* is
unchanged: the `ws_decode_ex` subtree measures **12 B** at the aggressive
point with worst-case `n_weak` (134), identical to §14.2's ledger, because
the candidate list is indexed statics and the chase chain does not recurse
over it.

Bit-exactness re-proved **per point**: host parity `decode.c` <->
`embedded_v2.py` **549/549** at (11,131), (14,131) and (16,192); ucsim on
the shipped `decode_asm.s` **24/24** at ND = 48 and ND = 16 for all three,
plus **24/24** with capture byte 0 bits 7..6 forced to `0xC0` at the
aggressive point.  The (11,131) runs reproduce §19.3/§20.1's tick
distributions exactly — the control that says the default path did not
move.

`cap_arm.s` is untouched, and the two `CAPLOOP` HARD PINS are
byte-identical in all three images.  The `CAPARM` block differs in
**exactly four bytes** — the low halves of the two `mov s_arm,#n` and two
`dec s_arm` operands, each shifted by `3*(A_MAX-11)` because `s_arm` is
REL DATA linked after the candidate arrays.  `dev_amax/armdiff.py` proves
that and that the four edge-detect BTJT polls are byte-identical; it is
the same discipline `cap_arm.s`'s header already states for §16.3's
diagnostic arm.

**Recommendation to the owner.**  The delivery on offer is a few
hundredths of a percentage point, bought with 1.4x-2.5x the measured
false-accept exposure, on a project whose headline axis is zero wrong
emissions.  **MODERATE (`A_MAX = 14`, `T_MAX = 131`) is the only point
that leaves the false-accept BOUND untouched at 0.200 %** (it does not
move `T_MAX` at all) and still captures +7 of the +13; AGGRESSIVE
(`16, 192`) buys 2 more frames for a 0.293 % bound and 18 B of stack
margin.  Neither has been on silicon.  If the bench does not resolve a
difference — and at +7/16 800 it very likely cannot — the right answer is
to keep 11/131 and bank the parameterisation, the sweep and the guard.
