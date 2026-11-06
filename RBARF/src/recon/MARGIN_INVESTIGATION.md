# RBARF delivery-margin investigation — the low-entropy gap is a trim-target defect

> **Relocation note (housekeeping 2026-09-08).** The bench-only mains this
> document names — `rbarf_prod_tf.c`, `rbarf_dbg_tf.c` — now live in
> `../archive/firmware-variants/`. Neither was ever in a default `make`
> target; both still compile. See `../archive/README.md`.

**Date:** 2026-09-07 · **Unit:** STM8S001J3 on the [rbarf-test-bench] rig ·
**Phase:** Margin (investigation only — no shipping file changed, calibrated
capture timing untouched)

## TL;DR

The single-shot delivery gap is **not** an intrinsic property of low-entropy
payloads, and it is **not** the sampler model being wrong about the silicon.
It is an **operating-point defect**: the SS11 auto-trim parks the unit at
**code 7 (eps ≈ +0.02…+0.13 % cold, +0.15…+0.33 % warm)**, which sits **on
the fast-side emit-gate cliff at eps ≈ +0.1 %**. Below that cliff the decoder
delivers on a broad **85–96 % plateau all the way to −2.2 %**; above it,
delivery falls off to ~10 %. Trim granularity is 1.16 %/step, so near zero the
only two reachable points are **−1.07 % (code 0, on the plateau)** and
**+0.02 % (code 7, on the cliff)** — and the auto-trim picks the cliff.

**Demonstrated live on the 30-frame gate mix, this session, no shipping file
changed** (bench-only runtime-trim-forced image, decoder + capture loop
byte-identical to production):

| operating point | cold | warm | path mix |
|---|---|---|---|
| **auto-trim = code 7 (+0.02 %)** [PROD_CLOSURE §11.1] | 14/30 | 14/30 | 6–7 O + 7–8 C |
| **forced code 0 (−1.07 %)** [this session] | **24/30** | **25/30** | **24–25 O + 0–1 C** |

The two payloads that *never* delivered under auto-trim deliver once
off-resonance: **`fade` 0/6 → 5/6, `dark` 0/6 → 3/6, `colors` 3/6 → 6/6**
(cold+warm pooled). Every code-0 delivery was **direct (O)** — the fragile
chase is not even invoked — which also collapses the §11.4 catastrophic
exposure (the chase false-accept lives on the *fast* side, code 6).

**Recommended fix #1 (zero flash cost): retarget the auto-trim deadband from
"centre eps = 0" to "centre eps ≈ −1 %".** It is a constant change in
`auto_trim()`; on this unit it converges to exactly the code 0 measured above.

---

## 1. Method

Everything here is either (a) the real host decoder — `decode.c` compiled by
gcc at the **production geometry** (`-DND_DATA=48 -DCHECK_EN=1 -DCHK_LEN=4`),
which is bit-exact against the on-chip `decode_asm.s` (PROD_CLOSURE §4, and
re-confirmed **80/80 parity** below), driven over synthetic captures from the
calibrated sampler model (`recon/synth.py` physics, reproduced in
`dev_prod/sweeplib.py`); or (b) **new instrumented silicon captures** taken
this session through bench-only images that force `CLK_HSITRIMR` and dump the
raw capture before decoding.

**Bench-only images built and used** (production-identical link flags; guard
green on every one; `_cap_loop` pinned `0x9FAF`, phase `0xF`; the calibrated
capture loop and the whole decoder are byte-identical to the shipping build —
only the `main()` trim policy differs):

| image | source | role |
|---|---|---|
| `rbarf_prod_tf0.ihx` | `rbarf_prod_tf.c -DTF_FIXED=0` VERBOSE | trim held at code 0 for the whole run; `drive_prod.py` runs unmodified |
| `rbarf_prod_tfc.ihx` | `rbarf_prod_tf.c` VERBOSE | round-robins codes {7,0,6,1} one per report → all four eps points on one thermal trajectory |
| `rbarf_dbg_tfc.ihx` | `rbarf_dbg_tf.c` | dump-before-decode + the same trim cycle → 80 real captures paired with their operating point |

Shipping images verified byte-identical to the ledger **before and after**
(`rbarf_prod.ihx` md5 `9baabefe…`, verbose `bcf83129…`, `capture.ihx`
`84955f77…`). `build/capture.ihx` restored at exit (banner `RBARF-CAP 1` +
`READY`, first byte 5.06 s). `data/captures_val.json` never opened. No
ucsim/sstm8 run this session (all host gcc); 0 stray simulators confirmed.
0 MCU resets across all 281 frames driven; 0 of the 3-power-cycle budget
consumed (every flash and power-up first attempt).

---

## 2. Mechanism — the fast-side emit-gate cliff (hypothesis (a), refined)

Synthetic sweep of the production decoder over the 10 gate payloads ×
134 eps points × 16 t0 phases (`dev_prod/margin_synth_sweep.jsonl.gz`,
21 440 cases). Gate-mix delivery vs eps, pooled over payloads and phase:

```
 eps      deliv%   mean_weak  mean_tied  mean_merged   <- per frame
-2.20%    88.8       0.9        0.1        5.5
-1.60%    88.1       0.7        0.5        9.6
-1.00%    93.8       0.7        0.5       13.1
-0.60%    95.0       0.3        0.1       14.2
-0.20%    94.4       0.2        0.0       15.3
+0.00%    91.9       0.2        0.0       16.2   <- merge peak (TRIM_SWEEP)
+0.20%    23.1       5.6        2.0       14.2   <- CLIFF
+0.40%    10.0      14.6        7.8       11.0
+0.60%    10.0      25.8       16.2        8.6
+1.20%    10.0      63.3       51.3        3.5
+1.60%     3.8      87.9       71.0        0.9
```

Three facts settle the mechanism:

1. **The response is a sharp one-sided cliff at eps ≈ +0.1 %, not a symmetric
   resonance notch.** The plateau spans roughly **−2.2 % … +0.05 %** at
   85–96 %; the collapse is entirely on the fast side.
2. **1-bit merging peaks at eps ≈ 0 exactly as TRIM_SWEEP.md predicts (16/frame),
   but merging alone is not what refuses.** Delivery is still 92 % at the merge
   peak. Merging only becomes fatal once it turns into **weak/tied bits**: for
   eps > 0 the mean weak-bit count explodes 0.2 → 5.6 → 14.6 per +0.2 % and the
   zero-margin (tied) count 0 → 2.0 → 7.8. Those trip the emit gate
   (`n_tied > TIE_EMIT=8` → R5; `n_weak > A_MAX=5` → R7) and force the chase
   (R8). The decoder models merging fine; it cannot manufacture margin that the
   compressed fast-side grid has removed.
3. **On the slow side the weak/tied counts stay ~0**, so decodes are **DIRECT
   and robust** across the whole −0.1 … −2.2 % plateau. `dark`'s only genuine
   sensitivity — swallowed-0 bits — grows slowly toward the far slow corner
   (mean_miss0 0.0 at −0.4 % → 4.7 at −2.4 %), which is why the plateau
   finally rolls off past −2.3 %, not before.

The auto-trim targets eps = 0 with a ±0.6 % deadband. From factory (code 0,
−1.07 %) it takes one step to code 7 (+0.02 %) and stops — **landing on the
cliff edge**, with all of its cold margin (+0.13 %) and every degree of warming
pushing it *over*.

### 2.1 Silicon reproduces the zones (the model is right about the physics)

30-frame gate at each forced trim code (interleaved run
`dev_prod/margin_trimcycle.json`, all four codes on one thermal trajectory,
plus the two dedicated code-0 gates):

| code | eps (measured) | gate delivery | vs synth-sweep at that eps |
|---|---|---|---|
| 7 | +0.02…+0.13 % | 7/30 (interleaved) · 14/30 (auto-trim §11.1) | model 70–92 % cold, **10 % warm** |
| **0** | **−0.87…−1.07 %** | **26/30 (interleaved) · 24/30 cold · 25/30 warm** | model **90–94 %** |
| 1 | −2.05…−2.25 % | 23/30 (interleaved) | model 88 % |
| 6 | +1.27…+1.48 % | 3/30 (interleaved) | model 10 % |

Silicon and the model agree on every zone. Code 6 (+1.27 %) delivering only
3/30 — all chase (C) — is the same fast-side collapse, one step further out,
and is where the §11.4 catastrophic false-accept was reproduced in the sweep
(`rnd` at +1.27 %). Code 0 is the sweet spot: maximal distance from **both**
the +0.1 % cliff and the −2.3 % swallow-edge.

---

## 3. Hypothesis (c): the synthetic model is optimistic — but only on the cliff

80 real captures were dumped before decode and each fitted (t0, eps) against
the calibrated model, then a **matched synthetic twin** (same fitted t0, eps)
was decoded (`dev_prod/margin_dump_analysis.jsonl`).

- **Host-decode parity: 80/80.** The host decoder reproduces the on-chip
  verdict (O/C/R-cause) on every dumped capture — the dumps are trustworthy
  and the C/asm decoders still agree at production geometry.
- **The sampler statistics match exactly.** Mean weak-bit and merged-loop
  counts are identical real-vs-twin at every code (code 7: weak 3.9/3.9,
  merged 18.7/19.9; code 0: 0.3/0.3, 19.8/19.7; code 6: 69.2/69.2, 3.0/3.0).
  The model's *physics* is not optimistic.
- **Delivery-outcome agreement is where it splits, and only at the cliff:**

  | code | real deliv | twin deliv | outcome-match | note |
  |---|---|---|---|---|
  | 7 (+0.02 %) | 4/19 | **8/19** | 13/19 | **twin 2× optimistic** — all in R8 chase flips |
  | 0 (−1.07 %) | 15/18 | 11/18 | 14/18 | twin *pessimistic* |
  | 6 (+1.27 %) | 1/18 | 1/18 | 17/18 | matched |
  | 1 (−2.25 %) | 12/18 | 11/18 | 13/18 | matched |

The model over-predicts delivery **only at the parked point (code 7)**, and the
disagreements are almost all `R8 ↔ C` — i.e. the *chase* landing differently
on sub-sample perturbations the model does not carry. That is the explanation
for the headline "synthetic 89–96 % vs silicon 27–60 %": the model was being
read **at the operating point the auto-trim chose**, which is exactly the
regime (heavy weak-bit chase) where its chase accounting is fragile. Move one
trim code onto the plateau and the model becomes accurate-to-pessimistic — the
89–96 % is real there, and silicon delivers 80–87 %.

---

## 4. Hypothesis (b)/(d): capture-arm t0 spread and lock-fails — a small, separate residual

- The fitted t0 spans **375–736 ns (p10–p90), median 560 ns**, wider than the
  capture.ihx-fitted 254–501 ns range. This is a real difference — the
  production `cap_arm.s` bounded-arm path triggers a little later and with
  more spread than the blocking `capture.c` entry the model was fitted on —
  but t0 **does not gate delivery inside the plateau** (the twin, which uses
  the fitted t0, reproduces the plateau outcomes).
- **~6 % of frames (5/80) produce a malformed capture** — fit agreement only
  0.68–0.77 (un-modelable at any t0/eps → the arm caught a partial/mis-phased
  frame), producing an **R1 seed-lock failure** (K outside [K_MIN,K_MAX],
  decode aborts in ~3–11 ms). These are **trim-independent**: they appear at
  code 0 too (2/30 in each code-0 gate). They cap the achievable rate at
  ~28/30 even at ideal eps, and are the honest reason code 0 lands at 24–25/30
  rather than the model's ~28.

This is a genuine but minor arm-timing contributor, cleanly separable from the
resonance and **not** touched by the trim fix.

---

## 5. Root-cause split (of the 14/30 → ~28/30 headroom, ≈14 frames)

| contributor | frames | evidence | independent lever? |
|---|---:|---|---|
| **Operating-point on the emit-gate cliff** (auto-trim parks code 7, not code 0) | **~10–11** | 14→24-25 live; 7→26/30 isolated interleaved | **yes — zero-cost trim retarget** |
| Thermal drift | (amplifies the above) | code 7 warm 14/30 & low-entropy→0; code 0 warm still 25/30 | no — only harmful because the target sits on the cliff; retarget neutralizes it |
| Synthetic-model optimism | (explains synth-vs-silicon, not a frame lever) | twin 8/19 vs real 4/19 at code 7; accurate at code 0 | no — evaporates off-resonance |
| Capture-arm mis-trigger / R1 lock-fail | ~2 | 5/80 malformed dumps; 2/30 R1 in each code-0 gate | partly — arm-timing, needs its own validation |
| Residual low-entropy content margin (`dark`/`fade` R2/R3 at good eps) | ~2–3 | code-0 `dark` still 3/6 | genuine, harder |

The resonance operating point and its thermal amplification, acting through the
fast-side emit-gate cliff, are essentially the entire gap. Model optimism is
why it was not predicted. Arm/lock is a small independent residual.

---

## 6. Ranked fixes

### #1 — Retarget the auto-trim deadband to eps ≈ −1 % · ZERO flash cost · DEMONSTRATED +10–11 frames

`rbarf_prod.c auto_trim()` currently centres on eps 0:

```c
if (eps_centi > 60 && v < 3) v++;          /* clock fast -> slow it  */
else if (eps_centi < -60 && v > -4) v--;   /* clock slow -> speed up */
```

From factory (−107 centi) this converges to **code 7 (+0.02 %), on the cliff.**
Re-centre the deadband on −100 centi (keep the ±0.6 % width), e.g.

```c
if (eps_centi > -40 && v < 3) v++;         /* only slow it if faster than -0.4% */
else if (eps_centi < -160 && v > -4) v--;  /* only speed it if slower than -1.6% */
```

This converges to any code landing in **eps ∈ [−1.6 %, −0.4 %]** — on this unit
**code 0 (−1.07 %)**, dead centre of the plateau, with ~1 % of thermal headroom
to the +0.1 % cliff and ~1.2 % to the −2.3 % swallow-edge. It is a **constant
change** (no new code path), so flash is unchanged.

- **Live proof (this unit, this session):** forcing exactly this operating
  point gave **24/30 cold, 25/30 warm** (vs 14/30 auto-trim), all direct, 0
  chase, 0 catastrophic, 0 resets. The isolated interleaved run gave **26/30**
  at code 0 against **7/30** at code 7 on the *same thermal trajectory*.
- **Bonus:** removes the fragile chase (0–1 C at code 0 vs 7–8 C at code 7) and
  therefore the §11.4 false-accept surface, which lives on the fast side.
- **Note the 1.16 %/step granularity is the whole point:** near zero the auto-
  trim can only choose −1.07 % or +0.02 %; today it deterministically chooses
  the worse of the two. This fix flips that choice. (It does not need — and
  must not wait for — finer trim resolution.)

*Caveat for portability:* the fix is unit-agnostic (it targets an eps band, not
a code), but the specific 24-26/30 number is this unit at this ambient. A unit
whose plateau/cliff sit differently would still be pulled into the −0.4…−1.6 %
band; the band itself should be re-confirmed if the population HSI spread is
wide.

### #2 — Recover the R1 lock-fails (arm-timing) · firmware-only · ~+2 frames · needs its own validation

~6 % of frames mis-trigger the bounded arm and refuse R1 in a few ms. A cheap
lock-retry (re-arm once immediately on an R1 within the same blind budget), or
a small widening of the arm search window, would recover most. **Touches
calibrated capture/arm timing → requires the capture-loop phase guard to stay
green and its own bench validation** (out of scope for the zero-risk lever).

### #3 — Bound the chase (the §11.4 catastrophic fix) · do it *with* #1

At code 0 the chase is barely invoked (1/20 dumps), so capping candidate
count / edit distance costs ≈0 deliveries there while closing the false-accept.
#1 and #3 are synergistic: #1 moves the operating point out of the chase-heavy
regime, #3 makes whatever chase remains safe.

### #4 — Low-entropy content margin (`dark`/`fade`) · genuine, harder · ~+2–3 frames

Even at ideal eps, all-zero `dark` (3/6) and long-run `fade` retain some
residual margin loss (swallowed-0 / marker sensitivity). This is the only part
of the original "content correlation" that is intrinsic. Decoder change,
separate validation; lowest priority given #1 does the heavy lifting.

**To clear ≥26/30 reliably:** #1 alone reaches 24–26/30 (26 in the isolated
run, 25 warm); pair with #2 to clear the bar with margin. #1 is the zero-risk
win and should ship first.

---

## 7. What this reframes

PROD_CLOSURE §9.1/§11.1 read the shortfall as a **content correlation** —
"high-entropy delivers, all-zero `dark` and long-run `fade` never do." That
correlation is real **but it is an interaction with the operating point, not an
intrinsic payload property.** At the auto-trim point (code 7) `dark`/`fade` are
0/6; one trim code away (code 0) they are 3/6 and 5/6. The decoder was never
failing these payloads — it was failing them *at +0.1 % eps*, and the auto-trim
guarantees +0.1 % eps. §11.3's temperature finding is the same story: warming is
only a delivery lever because it walks the cliff-parked operating point further
over the cliff.

---

## Artifacts produced (all bench-only / analysis; no shipping file changed)

| path | contents |
|---|---|
| `rbarf_prod_tf.c` | bench-only trim-forced main (`-DTF_FIXED=v` fixed, or round-robin {7,0,6,1}); links the production `PROD_RELS` unchanged |
| `rbarf_dbg_tf.c` | bench-only dump-before-decode + the trim cycle |
| `bench/drive_tf.py` | interleaved 4-code campaign driver (adaptive per-payload until all codes seen; single transmission) |
| `bench/dump_tf.py` | instrumented-capture collector (pairs each raw capture with its operating point + on-chip verdict) |
| `recon/approaches/dev_prod/margin_gate_code0_cold.json` / `…_warm.json` | the demonstrated 24/30 & 25/30 code-0 gates |
| `recon/approaches/dev_prod/margin_trimcycle.json` | the 4-code interleaved run (code0 26/30 vs code7 7/30) |
| `recon/approaches/dev_prod/margin_dumps.json` | 80 raw silicon captures + verdict + code |
| `recon/approaches/dev_prod/margin_dump_analysis.jsonl` | per-capture parity, (t0,eps) fit, matched-twin decode |
| `recon/approaches/dev_prod/margin_synth_sweep.jsonl.gz` | 21 440-case eps×t0×payload delivery sweep |
| `recon/approaches/dev_prod/sweeplib.py` / `sweep.py` / `analyze_dumps.py` | reproduction (host decoder `decode_host_prod.so` = `decode.c` at ND48/CHK4) |

Bench state on exit: `build/capture.ihx` restored (md5 `84955f77…`) and
verified — banner `RBARF-CAP 1` + `READY`, first byte 5.06 s.
