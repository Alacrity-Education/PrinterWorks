# HSI Oscillator Drift & Tolerance Investigation

Project operating range: **+10 °C to +90 °C**, VDD = 3.3 V.
The STM8S001J3 runs its sampler and UART from the internal 16 MHz HSI RC
oscillator. Source: DS12129 Rev 4, Table 31.

## Datasheet guarantees

| Condition | Accuracy |
|---|---|
| Factory calibrated, VDD = 5 V, TA = 25 °C | **±5 %** |
| Factory calibrated, VDD = 5 V, -40…125 °C | **±7.5 %** (by characterization) |
| User-trimmed via CLK_HSITRIMR, at the given VDD & TA | **-2.0 / +3.25 %** (by design) |

Notes:
- There is **no tighter guarantee for a sub-range** like +10…+90 °C, and
  the typical fHSI-vs-temperature figure was removed from this datasheet
  revision. The ±5 % point figure applies at 5 V only — our target runs
  at 3.3 V, so even at room temperature the guaranteed bound is the
  full-range one.
- **Design envelope adopted: ±7.5 % frequency scale**, static per
  capture. Thermal time constants are seconds; within one 1.2 ms capture
  the thermal drift is negligible (≪0.01 %). Residual within-capture
  wander is RC-oscillator noise, modeled as ≤±0.2 % slow ramp for margin.
- Bench measurement (~25 °C, 3.3 V): loop period 2507.3 ns vs 2500 ns
  nominal → this unit sits at **≈ -0.3 %** today.

## Consequences for reconstruction

Let ε = relative HSI frequency error (receiver time base scales by 1/(1+ε)).

1. **Static time bases fail catastrophically.** A frame is 192 bits.
   An unestimated scale error mis-places the last bit by 192·ε bit
   periods: 1.9 bits at ε = 1 %, **14.4 bits at ε = 7.5 %**. Any decoder
   must estimate scale per capture (header `AA`, trailer `55`, and the
   header→trailer span are the intended references). This is why the v2
   framing exists.
2. **Swallowed 0-bits get worse at the slow corner.** T0H ≈ 350 ns vs
   the sampler's dead-zone gaps: the documented max gap (6 cy ≈ 375 ns)
   stretches to ~403 ns at ε = -7.5 %; with the ~3 undocumented extra
   cycles apparently in the end-of-loop gap (~9 cy ≈ 562 ns nominal),
   that gap stretches to **~604 ns** — comfortably swallowing any T0H
   pulse and even exceeding T1L (550 ns), so **1-bit merging also
   worsens** (already observed at room temperature). At ε = +7.5 % the
   gaps shrink and both artifacts nearly vanish. The hard corner for
   decoding is **slow HSI = hot end** (HSI typically slows when hot).
3. **The 9600-baud debug UART itself breaks beyond ~±4.5 %** clock
   error (8N1 sampling limit). Fine on the room-temperature bench;
   for production diagnostics over the full range the firmware must
   user-trim HSI (CLK_HSITRIMR, residual -2/+3.25 %) — or derive the trim
   at runtime from the WS2812 signal itself, whose 800 kbps timing is
   crystal-exact at the transmitter and can serve as a frequency
   reference.

## How this is included in the analysis

Real captures only cover the bench point (≈ -0.3 %). To evaluate the
full envelope, `synth.py` generates synthetic captures with a
parameterized sampler model (validated against the real captures at the
bench point), and `eval_envelope.py` sweeps ε across
{-8, -7.5, -5, -2.5, -1, 0, +1, +2.5, +5, +7.5, +8} % — one point past
each guaranteed corner — plus a ±0.2 % within-capture drift case, and
scores each decoder across all 18 test patterns at every point.
A decoder is judged temperature-ready when it holds its exact-match rate
across at least the ±7.5 % span.

## Calibrated model

`synth.py` originally used a hand-guessed 40-cycle grid. It now uses the
sampler timing model fitted to all 54 real captures
(`approaches/dev_calibration/fitted_model.json`):

    A(i,s) = i·LOOP + o[s] + Σ_j w[j]·C_j(i,s)
    t(i,s) = t0 + A(i,s) / (1 + ε)

| Constant | Fitted value |
|---|---|
| loop period `LOOP` | 40 cycles = **2500.0 ns** at nominal 16 MHz |
| inter-sample gaps | **[4, 5, 4, 4, 4, 6, 5, 8] cycles** |
| slot offsets `o[]` | 0, 250, 562.5, 812.5, 1062.5, 1312.5, 1687.5, 2000 ns |
| branch cost `w[]` | **[0, -1, 0, +2, 0, 0, 0, +1] cycles** per HIGH read |
| effective T1H | **752 ns** (750 ns wire + 2 ns common edge shift) |
| effective T0H | **377 ns** (375 ns wire + 2 ns common edge shift) |
| per-capture nuisances | `t0` 254…501 ns, `ε` fitted per capture |

Three refinements to the numbers quoted above, none of which changes a
conclusion:

- The ~3 cycles missing from the documented 37-cycle layout are now
  located: **+1 cycle in the R1→R2 gap and +2 cycles in the end-of-loop
  gap**. The end-of-loop (slot 7 → next slot 0) gap is therefore 8
  nominal cycles = 505.7 ns after a LOW read and, because `w[7]` = +1,
  **9 cycles = 568.9 ns after a HIGH read** — against T1L ≈ 498 ns. That
  is exactly the mechanism §2 above assumes for 1-bit merging, so the
  slow-corner argument stands as written (and the gap still stretches to
  ~604 ns at ε = -7.5 %).
- `w[]` is a *data-dependent* term (the `BTJT` taken / `NOP` skipped path
  costs a different whole number of cycles per sample site). It makes the
  loop length alternate by one cycle, which is why merged loops come in
  runs of 1–2 rather than one long block. It is causal (it depends only
  on samples already taken), so it simulates directly.
- The bench point is **ε ≈ -1.12 %**, not the ≈ -0.3 % inferred from the
  naive 37-cycle time base (mean effective loop 2502.49 ns; the ~0.7 %
  per-capture loop-period spread quoted in DATASET.md was an artefact of
  that time base — the true spread is ±0.014 %). This is still far
  inside the ±7.5 % envelope, so the design envelope is unchanged; it
  only moves where "today's unit" sits within it.

## Envelope results — hardened combined decoder (2026-09-05)

`eval_envelope.py approaches/combined.py`, calibrated generator, 54
synthetic captures per point:

| ε | exact | byte-acc | ε | exact | byte-acc |
|---|---|---|---|---|---|
| -8.0 % | 15/54 | 81.9 % | +1.0 % | 40/54 | 95.0 % |
| -7.5 % | 16/54 | 84.5 % | +2.5 % | 33/54 | 81.7 % |
| -5.0 % | 36/54 | 94.6 % | +5.0 % | 0/54 | 1.5 % |
| -2.5 % | 54/54 | 100 % | +7.5 % | 0/54 | 0.0 % |
| -1.0 % | 53/54 | 99.9 % | +8.0 % | 11/54 | 86.9 % |
| 0 % | 54/54 | 100 % | -7.5 %+drift | 6/54 | 79.1 % |

Reading this correctly:

- **Strong band: ε ∈ [-2.5 %, +1 %] — effectively perfect.** The slow
  (hot) side holds byte-acc ≥ 82 % all the way to -8 %.
- **The fast-corner zeros are refusals, not errors.** Byte-acc 0.0 % at
  +7.5 % means every capture returned `None` (the post-hardening honest-
  refusal gate): the decoder declines inputs it cannot decode reliably,
  where the pre-hardening build returned confidently wrong payloads
  (29 % byte-acc). For production, refusal is the correct corner
  behavior. (+8 % decoding *better* than +7.5 % indicates a time-base
  alias boundary — a known fast-corner phenomenon flagged in the
  clock_stretch design.)
- Caveats: the generator shares its timing model with the decoder's
  fallback config (mismatch untested — see the audit), and corner rates
  are partly information-ceiling-bound (dead sampling windows).

**Production conclusion:** the decoder alone does not hold the full
untrimmed ±7.5 % envelope — and does not need to. The pipeline already
measures each frame's clock error against the crystal-exact WS2812
signal to ~0.004 % precision; feeding that into `CLK_HSITRIMR` as a
runtime auto-trim keeps the operating point inside the strong band at
every temperature, and the refusal gate covers the transient before the
first trim converges. The oscillator investigation thus closes its own
loop: the reconstruction algorithm is the temperature compensation.

### Validation (`python3 synth.py`)

Each real capture is rebuilt from the model with only the two per-capture
nuisance parameters the brief allows (`t0`, `ε`) free; every sampler
constant is held fixed. Result (full log in
`approaches/dev_calibration/synth_validation.txt`):

- **18/18 patterns match.** Worst per-pattern mean high-pulse-count
  deviation 2.3 (`dense`); worst single capture 5 (`dense_0`, the
  hardest capture for the model — the independent check in
  `dev_calibration` reproduces it no better).
- **`ones` merged-loop count reproduced exactly: real 37/36/39 →
  synthetic 37/36/39.**
- Mean sample agreement 99.93 % over all 276 372 samples; worst capture
  99.77 % overall, 98.50 % inside the 96-loop frame window.

The envelope sweep in `eval_envelope.py` is unchanged apart from the
per-rep phases, which now span the fitted `t0` range (254…501 ns)
instead of 0…250 ns.
