# CLK_HSITRIMR Trim Sweep — Measured HSI Clock Response

> **Relocation note (housekeeping 2026-09-08).** `capture_trim.c` is
> superseded and now lives in `../archive/firmware-variants/`; it still
> builds with `make capture-trim`. See `../archive/README.md`.

Acquired 2026-09-05 on the real bench (STM8S001J3, 3.3 V rail,
`capture_trim.c` + `cap_code.s`; dataset `../data/captures_trim.json`,
96 captures = 8 trim codes x 6 patterns {aa, zeros, ones, rnd1, rnd2,
edges} x 2 reps, all checksums verified, 0 bad dumps). Purpose: measure
how the WS2812 sampler's effective clock responds to each CLK_HSITRIMR
(0x50CC) code, as the basis for a forward clock-drift correction.

**Temperature**: the STM8S001J3 has **no on-chip temperature sensor**
(DS12129 §4.12 provides only a temperature-independent bandgap on AIN7);
ambient = uninstrumented room temperature. Recorded as such in the
dataset meta.

**Firmware design** (why the UART never garbled): all UART output runs
at factory trim (CLK_HSITRIMR=0x00). Per cycle: `TRIM:<code>` +
`READY` at factory trim → drain the UART shifter (TC flag) → write
CLK_HSITRIMR=code → `cap_code` samples at the trimmed clock → restore
0x00 → dump `CAP:<hex>:<sum>`. Every dump across all 8 codes arrived
clean.

## Method

eps = relative HSI frequency error vs nominal 16 MHz
(sample wall-time = t0 + A(i,s)/(1+eps), A = calibrated nominal sampler
time from `synth.py`: 40-cycle loop, gaps [4,5,4,4,4,6,5,8], branch
cost w = [0,-1,0,+2,0,0,0,+1]). Two independent estimators per capture
(`../archive/investigations/dev_trimsweep/analyze.py`):

1. **Span**: the frame spans exactly 191·1250 + 752 = 239 502 ns of
   wall time between first rising edge and last falling edge; the
   nominal-time span of the same interval in the capture gives
   1+eps directly (quantization ~±0.1%).
2. **Alignment**: maximize raw sample agreement against
   `synth._simulate` over the frame window with only (t0, eps) free —
   the same approach as `synth._align`, with wide eps bounds seeded by
   the span estimate.

Cross-check: mean |align − span| = 0.04–0.14% per trim code, within the
span method's quantization — the two methods agree at every code.
Alignment agreement stayed 92.3–100% (median ~98.8%) across the whole
sweep, so the calibrated sampler model holds at every trim code.

## Result: trim code → eps (alignment method, 12 captures/code)

| code | signed value | mean eps | sd | range | span-method mean |
|---|---|---|---|---|---|
| 0 | +0 (factory) | **−1.072 %** | 0.043 % | −1.128…−0.953 % | −1.11 % |
| 1 | +1 | **−2.248 %** | 0.073 % | −2.395…−2.167 % | −2.22 % |
| 2 | +2 | **−3.281 %** | 0.021 % | −3.314…−3.236 % | −3.30 % |
| 3 | +3 | **−4.385 %** | 0.041 % | −4.464…−4.310 % | −4.36 % |
| 4 | −4 | **+3.733 %** | 0.037 % | +3.704…+3.814 % | +3.75 % |
| 5 | −3 | **+2.492 %** | 0.019 % | +2.452…+2.504 % | +2.57 % |
| 6 | −2 | **+1.274 %** | 0.033 % | +1.205…+1.343 % | +1.25 % |
| 7 | −1 | **+0.022 %** | 0.034 % | −0.053…+0.066 % | +0.16 % |

Per-pattern means (alignment, %; no pattern dependence beyond the
per-capture spread):

| code | aa | edges | ones | rnd1 | rnd2 | zeros |
|---|---|---|---|---|---|---|
| 0 | −1.072 | −1.034 | −1.082 | −1.070 | −1.090 | −1.084 |
| 1 | −2.205 | −2.196 | −2.320 | −2.295 | −2.280 | −2.190 |
| 2 | −3.297 | −3.287 | −3.260 | −3.290 | −3.268 | −3.282 |
| 3 | −4.328 | −4.413 | −4.378 | −4.374 | −4.376 | −4.437 |
| 4 | +3.759 | +3.756 | +3.720 | +3.740 | +3.707 | +3.718 |
| 5 | +2.452 | +2.503 | +2.503 | +2.489 | +2.502 | +2.502 |
| 6 | +1.275 | +1.270 | +1.261 | +1.281 | +1.317 | +1.238 |
| 7 | +0.057 | +0.032 | −0.024 | +0.032 | −0.000 | +0.036 |

## Mapping conclusions

- **The mapping is SIGNED — 3-bit two's complement.** Codes 0..3 are
  +0..+3 trim steps, codes 4..7 are −4..−1. An increasing *signed*
  value LOWERS the frequency.
- **Strictly monotonic in signed order** (4,5,6,7,0,1,2,3 →
  +3.73, +2.49, +1.27, +0.02, −1.07, −2.25, −3.28, −4.38 %).
  Non-monotonic in unsigned code order: a +8.12 % wraparound jump
  between codes 3 and 4.
- **Step size**: adjacent signed steps of −1.03…−1.25 %; mean
  **−1.16 % per step** (≈186 kHz at 16 MHz). Steps, signed order
  −4→+3: −1.24, −1.22, −1.25, −1.09, −1.18, −1.03, −1.10 %.
- **Factory (code 0) sits at −1.07 %** on this unit today — consistent
  with the −1.12 % fitted from the 54-capture dataset (Δ 0.05 %;
  ambient uninstrumented, plus estimator differences).
- **Best cancellation of this unit's ≈−1.12 % error: code 7**
  (signed −1), measured residual **+0.022 % ± 0.034 %** — essentially
  perfect. No other code comes within 1 %.
- **Total trim authority: −4.38 % … +3.73 %** around nominal (8.12 %
  span), i.e. roughly ±4 steps of ~1.16 % around the factory point.
  With a ~1.16 % step, worst-case residual after optimal trimming is
  ~±0.6 % — comfortably inside the decoder's strong band
  (HSI_TEMPERATURE.md: perfect in [−2.5 %, +1 %]).

## Sampling-behavior changes across the sweep

Per-trim means (high-pulse count via `harness.high_pulses`, merged-1
loops via `synth._merged_loops` — the same statistics `synth.py`
`validate()` reports; wire carries exactly 192 pulses/frame;
swallowed ≈ 192 − pulses − merged):

| code | eps | pulses (all) | merged (all) | swallowed (all) | merged, `ones` | swallowed, `zeros` |
|---|---|---|---|---|---|---|
| 3 | −4.38 % | 180.8 | 5.2 | 6.1 | 10.5 | **10.0** |
| 2 | −3.28 % | 182.4 | 4.8 | 4.8 | 5.5 | 7.5 |
| 1 | −2.25 % | 181.9 | 8.2 | 1.9 | 9.0 | 2.5 |
| 0 | −1.07 % | 175.4 | 14.5 | 2.1 | 42.5 | 3.5 |
| 7 | +0.02 % | 169.7 | **22.2** | 0.2 | **64.0** | 0.0 |
| 6 | +1.27 % | 185.6 | 6.0 | 0.4 | 21.5 | 0.0 |
| 5 | +2.49 % | 187.4 | 4.6 | 0.0 | 21.0 | 0.0 |
| 4 | +3.73 % | 186.7 | 5.3 | 0.0 | 27.0 | 0.0 |

- **Swallowed 0-bits behave exactly as the model predicts**: strictly
  worse toward the slow side (`zeros`: 0 at all fast codes → 3.5 at
  factory → 10.0 at −4.4 %), because the inter-sample dead zones
  stretch by 1/(1+eps) past T0H = 377 ns.
- **Merged 1-bits are NON-monotonic and peak at eps ≈ 0 (code 7:
  64 merged loops on `ones`, vs 5–12 at the slow codes).** This is a
  resonance: at eps ≈ 0 the 40-cycle loop is exactly 2 bit periods, so
  the end-of-loop gap (505.7/568.9 ns vs T1L ≈ 498 ns) lands at the
  same bit-grid phase every loop — once it swallows an inter-bit low it
  swallows nearly all of them. At larger |eps| the boundary phase walks
  through the bit grid and merging happens only during part of each
  beat cycle. Factory (−1.07 %) is the second-worst point (42.5).
  Caveat: the merged-loop counter is the standard proxy (slot-7 and
  next slot-0 both high) and can count a single long T1H spanning the
  boundary; on a few `ones` captures pulses+merged slightly exceeds
  192 (swallowed estimate −1…−5), so treat merged counts as
  comparative, not exact.
- **Consequence for the forward correction**: trimming to eps ≈ 0 is
  optimal for the UART and for swallowed-zero elimination, but it
  *maximizes* 1-bit merging on dense-ones data. The decoder already
  models merging exactly (end-of-loop gap vs T1L), and merging at
  eps ≈ 0 is deterministic (phase-locked), so this is a handled —
  but worth-knowing — trade-off. If merging were ever problematic, a
  deliberate slight-fast target (eps ≈ +1…+2.5 %, still in the strong
  band) drops merging to ~5/frame and swallows nothing.

## Forward-correction takeaway

eps(code) ≈ −1.07 % − 1.16 %·v(code), v = two's-complement value of the
3 low bits. To correct a measured clock error eps_meas (from the
crystal-exact WS2812 frame itself), set
v = round((eps_meas − eps_factory_offset)/1.16 %) ... in practice on
this unit: measure eps at factory trim, pick the code whose table entry
cancels it — the table above IS the correction map for this unit; step
granularity limits the residual to ~±0.6 % worst-case. The trim→eps
table is embedded in `../data/captures_trim.json` meta
(`trim_eps_table`) for programmatic use.

Scratch/reproduction: `../archive/investigations/dev_trimsweep/` (`analyze.py`,
`results.json`, `analyze_log.txt`, `append_meta.py`).
