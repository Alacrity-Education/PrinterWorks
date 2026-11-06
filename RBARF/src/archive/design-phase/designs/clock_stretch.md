# clock_stretch — technique design

Per-capture receiver-clock estimation and bit-grid phase tracking.
Produces the **time base** every other technique slices on.

Exploration code: `designs/dev_clock_stretch/exp1..exp27*.py`
(`common.py` holds the shared loaders; every number quoted below is
reproducible by running the named script).

---

## Target artifact & evidence

The artifact is DATASET.md artifact #1: *"the receiver clock is only
nominally 16 MHz; scale and drift must be estimated per capture."* Under
the HSI envelope an unestimated ±7.5 % scale error mis-places the last
frame bit by 14.4 bit periods. Everything downstream — slicing, missed-zero
insertion, matched filtering, edge DP — is meaningless without a correct
`t(iteration, slot)` map.

Five measurements shaped the design. They partly **contradict the brief**,
so they are given with their evidence.

### E1. The apparent 0.7–1.1 % per-capture clock spread is mostly estimator bias, not oscillator variation

`exp1_oracle_scale.py` reproduces the DATASET.md story: fitting `t = φ + C·cycle`
against ground-truth edges with the documented slot model gives cycle
durations spanning **1.137 %** (62.402 … 63.112 ns), with the slow outliers
being exactly the 0-rich patterns (`impulse_hi` −0.96 %, `msb1` −0.78 %,
`zeros` −0.61 %, `lone1`, `edges`) and the 1-rich patterns clustered at
+0.1 %. Clock error cannot correlate with payload content — this is bias
from swallowed 0-bits plus a wrong intra-loop slot model.

`exp6_residual_decomp.py` removes a **global** (all-54-captures) per-slot-pair
bias and refits. The per-capture loop period collapses to

```
L = 2499.21 … 2500.08 ns   (54 captures, spread 0.035 %)
```

`exp8_pipeline.py`, running the full blind pipeline (no ground truth at all),
gets `L = 2499.815 ± 0.084 ns`, min 2499.59, max 2500.04 — a **0.018 %**
spread across all 54 captures. All 54 were taken on one chip in one bench
session, so a near-zero spread is the physically expected answer; the 1.1 %
figure was an artifact.

**Design consequence:** the estimator must be *unbiased under pattern
content*, and the *envelope* (±7.5 %) is a between-capture/temperature
phenomenon, not a within-session one.

### E2. There is no measurable within-capture clock wander

`exp6` fits a quadratic to the post-bias residual of each capture:

```
linear term across the frame:  mean 0.0, std 1.2, max |.| = 2.8 ns end-to-end
  -> residual rate error 0.0012 % of clock
```

2.8 ns over the 240 µs frame is 0.0023 bit. The HSI_TEMPERATURE.md margin
allowance of ±0.2 % within-capture ramp, even if real, produces only
`L·g·U²/(2·U_cap)` = **36 ns** of raw bow over the frame and ~9 ns after a
linear fit absorbs the mean slope — 48× under the error budget (E5).

`exp11_anchor_track.py` splits each capture into six 32-bit segments and
reports the median grid phase per segment. The segment phases do **not**
ramp; they hop between discrete levels (−85 / −128 / −171 / +65 ns, spaced
~43 ns) set by *which slot-pairs happen to carry rises in that segment*.
`exp14_tolerance_pll.py` sweeps a 2nd-order PLL: on real captures rms
improves only 10.9 → 8.9 ns (kp = 0.3) and the worst case is unchanged; on
synthetic captures **with a real +0.2 % drift injected** every gain makes it
worse (worst 310.8 ns at kp = 0 → 315.8 ns at kp = 0.3).

**Design consequence: a PLL is the wrong instrument here.** A global
2-parameter fit is the maximum-likelihood answer and any loop filter with
useful bandwidth ends up tracking slot-mix bias. The tracker in this design
is therefore a *frozen-rate Kalman filter with data-derived process noise*,
which degenerates to the global fit at the measured wander level and only
opens up if a trip-wire fires.

### E3. The anchor-pair recipe in the brief (header AA vs trailer 55) is the *worst* scale estimator available

`exp11` computes the two-anchor scale from the phase difference between the
first and last segment:

```
L_2anchor - L_global : mean +2.18, std 1.36, max |.| = 5.96 ns  (0.238 % of clock)
```

versus the global fit's 0.084 ns spread — **15–70× worse**. Two anchors use
~60 of the ~180 available edges and put all the weight on two noisy endpoint
phases. The header/trailer are still essential, but for *origin and validity*,
not for *rate* (Stage 4/5 below).

### E4. Slot offsets cannot be bootstrapped per capture — there is an exact degeneracy at L = 2·BIT

`exp13_selfcal.py` fits `(φ, L, b₀…b₇)` jointly per capture against
rising-edge data with `Σb = 0`. On all 54 real captures and on synthetic
captures at every ε it returns

```
L = 2500.000 ns exactly, residual rms = 0.0 ns, on 54/54
```

and on synthetic data the coarse error is exactly `L_true − 2500` at every ε
(e.g. 202.70 ns at ε = −7.5 %). This is a *proof by construction*: when the
loop is exactly two bit periods the sampling phase never crawls, so each slot
sees a fixed bit-phase, and a per-slot constant explains every rising edge
perfectly for any truth. **clock_stretch has a hard dependency on a global
slot-offset calibration; it cannot produce one.**

The same degeneracy explains why the *empirically fitted bias table* is a
bench-only shortcut: `exp12_robust.py` applies the real-data bias table to
synthetic captures whose true slot offsets are the documented ones, and the
estimator fails 54/54 at ε = ±7.5 % (|ΔL| ≈ 200 ns — it locks a wrong alias)
while failing 0/54 at ε = 0. **Any per-slot table fitted at one clock is only
valid near that clock.** The primary estimator below is therefore
*interval-censored* and uses only calibrated slot *fractions*, which are
clock-invariant by construction.

### E5. What is actually achievable, and the error budget

Accumulated timing error at the end of the frame is `U_frame · ΔL` with
`U_frame = 192·1250/L ≈ 96.0` loops (`exp19_budget.py`):

| ΔL | end-of-frame shift | bit slip |
|---|---|---|
| 0.5 ns (0.02 %) | 48 ns | 0.038 |
| 1.0 ns | 96 ns | 0.077 |
| **4.5 ns (0.18 %)** | 432 ns | **0.346 ← budget limit** |
| 13.0 ns (0.52 %) | 1248 ns | 0.998 (full slip) |

`exp23_censored.py` + `exp24_cal_sensitivity.py`, on synthetic captures with
correct slot fractions, across ε ∈ {−8, −7.5, −5, −2.5, −1, −0.2, 0, +0.2,
+1, +2.5, +5, +7.5, +8} %:

```
median |ΔL| <= 0.35 ns,  max |ΔL| = 2.91 ns,  0/54 exceed 4.5 ns at every eps
```

`exp15_gridquality.py` measures the delivered grid against exact synthetic
truth: `max |Δt|` over the whole frame ≤ **54 ns**, rms 9–21 ns, and the
fraction of samples assigned to the wrong bit is ≤ 2.5 % worst-capture,
≤ 1.3 % mean, across the whole envelope.

### E6. Corrections to the brief's constants (three independent methods)

`harness.LOOP_NS = 2507.3` is high. Four measurements:

1. Blind rising-edge LS, 54 captures (`exp8`): **2499.815 ± 0.084 ns**.
2. Joint sample-level likelihood over 43 200 in-frame samples with a
   *shared* L and per-capture φ (`exp17`/`exp18`): peak **86.4 % at 2498 ns**,
   84.5 % at 2499.8, **72.0 % at 2507.3**, 83.4 % at 2508.
3. Direct beat-crawl slope of the first-rise slot per loop, no bit counting
   (`exp10`): −1.05 to −2.91 ns/loop on clean patterns → **L = 2497–2499 ns**.
4. Merged-pulse episode length (`exp20`): `ones` shows one **32/33/34-loop**
   merge episode in all three reps. With the 9-cycle end-of-loop gap
   (≈562 ns) the merge phase window is 562 − T1L(550) = 12 ns wide, so
   |δ| = |L − 2500| = 12/33 = **0.36 ns/loop → L ∈ [2499.6, 2500.4]**.

Note that method 4 also refutes the brief's *"beat crawl ≈ 7.3 ns/loop"*:
7.3 ns/loop would make that episode 12/7.3 ≈ 1.6 loops long, not 33. The
crawl at the bench point is **≈ −0.2 to −0.4 ns/loop**, i.e. the sampler is
almost exactly commensurate with two bit periods.

When each capture is also given a free scale, the shared-L likelihood is flat
over 2492–2506 (`exp27`), so the *absolute* bench loop period carries a
residual ±0.2 % uncertainty from the slot-offset/pulse-width degeneracy.
**Best estimate `L_bench = 2500 ± 3 ns` (point estimate 2499.8).** This is
precisely why nothing may be hard-coded; use 2500.0 as the *nominal* only,
and never 2507.3 as a fixed time base (it costs 0.3 % = 0.58 bit of slip).

### E7. Near-commensurate operation is the hard corner — not ±7.5 %

Because `L ≈ 2·BIT` at the bench, the sampling phase is frozen across the
frame (total crawl −19 ns = −0.015 bit over 96 loops, `exp20`). Consequences
measured:

- **Samples per bit alternate 5 / 3 by bit parity and never equal 4**
  (`exp19`: histogram is exactly `{3: 5184, 5: 5184}` over 54×192 bits).
  Odd-indexed bits are permanently undersampled; their T0H (350 ns) sits in
  the same phase for the whole frame, so 0-bit swallowing is *systematic*,
  not random, and does not average out.
- Losses concentrate: `exp20` counts lost rising edges over the envelope —
  1 lost at ε = 0, **23.2 lost at ε = −0.2 %**, and only 8–15 at ±5…8 %,
  because a large crawl randomises the sampling phase.
- Estimator conditioning is worst here too. `exp14`'s slot-calibration
  tolerance scan (random per-slot error, "fail" = |ΔL| > 1 ns):
  `ε = −7.5 %` tolerates 130 ns rms; `ε = ±2.5 %` tolerates 130 ns rms;
  **`ε = −0.5 %` fails 8/54 at only 20 ns rms.**

**Design consequence:** the technique must report an explicit
`commensurate_risk` flag when |L − 2·BIT| is small, because that regime
demands the *most* accurate slot calibration and produces the *most*
clustered downstream bit errors.

### E8. The estimator is nearly immune to swallowed bits

`exp12`, destroying rising edges at random on real captures (a rising edge is
removed by extending the preceding low over the whole pulse):

```
keep 100 %: |dL| max 0.24 ns      keep 35 %: max 0.30 ns
keep  50 %: max 0.30 ns           keep 15 % (~28 edges): max 0.42 ns
0/54 captures exceeded 3 ns at any decimation level
```

Edge *loss* is harmless (censoring is missing-at-random with respect to the
grid). Edge *displacement* — the bias in E1/E4 — is what hurts. That asymmetry
is the reason the cost function below is an interval-censoring cost.

---

## Algorithm

Notation: `it ∈ [0,639]`, `slot ∈ [0,7]`, `lev ∈ {0,1}`.
Sample time model, with `a[s]` the calibrated intra-loop slot offset as a
**fraction of one loop** (clock-invariant):

```
u(n)        = it(n) + a[slot(n)]              # position in loop units
t(n; φ,L)   = φ + u(n)·L                      # absolute ns, t=0 at the frame's first rising edge
bit_index(n)= floor((t(n) - k0·BIT) / BIT)
```

### Parameters

| name | value | meaning |
|---|---|---|
| `BIT` | 1250.0 ns | bit period (exact) |
| `T0H`,`T1H` | 350.0, 700.0 ns | nominal high widths |
| `T0H_EFF`,`T1H_EFF` | 339.25, 737.25 ns | effective widths incl. sampler aperture (from `dev_calibration/final.json`); prefer these when available |
| `N_BITS` | 192 | frame length |
| `L_NOM` | 2500.0 ns | nominal loop = 40 cy @ 16 MHz. **Not** 2507.3 (E6) |
| `EPS_MAX` | 0.085 | search half-range (one point past the ±7.5 % corner) |
| `L_LO`,`L_HI` | 2304.1, 2732.2 | `L_NOM/(1±EPS_MAX)` |
| `DL_COARSE` | 2.0 ns | coarse grid step, must be ≤ `PULLIN` |
| `PULLIN` | `BIT/(2·U_frame)` ≈ 6.5 ns | fine-stage capture range (E-note below) |
| `ALIAS_STEP` | `BIT/U_frame` ≈ 13.0 ns | spacing of one-bit-slip aliases |
| `CLIP` | `0.45·BIT` = 562.5 ns | robust clip on the per-edge cost |
| `PHI_FRAC`,`PHI_FRAC_SD` | 0.0528, 0.0036 | trigger-offset prior: `φ ≈ PHI_FRAC·L` |
| `W_FALL` | 0.5 | weight of falling-edge terms vs rising |
| `K0_RANGE` | −2 … +2 | integer bit-origin search |
| `J_MIN` | 0.90 | minimum acceptable coarse peak quality |
| `RATIO_MAX` | 0.60 | max second-peak/first-peak ratio for a confident lock |
| `HDR_MIN` | 56 / 64 | header+trailer bit agreement required for lock validation |
| `DRIFT_TRIP` | 150 ns | segment-phase spread that opens the tracker |
| `KP`,`KI` | 0.0, 0.0 | tracker gains (default frozen; caps 0.1 / 0.004) |
| `SIGMA_EDGE` | 12 ns | per-edge residual sd used for the emitted covariance |

`PULLIN` note: the fine stage's basin is exactly half of `ALIAS_STEP`.
`exp7_acquire.py` verified it on real data — seeding the fine stage at
`L_true + off` converges 54/54 for `|off| ≤ 6.5 ns` and **0/54** for
`|off| ≥ 13 ns`. The coarse stage is therefore mandatory; you cannot
cold-start from a nominal value even at 0.5 % error.

### Stage 0 — frame window

```
n_last_high = max{ n : lev(n) == 1 }
i_last      = it(n_last_high)                 # measured: 94 or 95 on every capture
U_MAX       = i_last + 2
keep only samples with it <= U_MAX            # ~768 of 5117 samples
U_frame     = N_BITS·BIT / L                  # ≈ 96.0; recompute as L updates
```

The frame occupies **loops 0…95 of 640**; 545 loops (85 % of the buffer) are
idle low and carry no information. Restricting to the window removes the
trailing-idle samples that would otherwise dominate any level-based cost.

### Stage 1 — edge brackets

```
for each n with lev(n) != lev(n+1) and it(n) <= U_MAX:
    kind = +1 if rising else -1
    record (u0 = u(n), u1 = u(n+1), s = slot(n), kind)
```

A transition between samples n and n+1 *proves* the true edge lies in
`(t(n), t(n+1)]`. Do **not** collapse it to a midpoint — that is what
introduces the pattern-dependent bias of E1 (measured slot-pair midpoint
biases reach ±540 ns, `exp6`).
Typical yield: **152–190 rising brackets** of 192 (1-rich patterns lose the
most, to merging: `ones` 152–154, `zeros` 182–187).

### Stage 2 — coarse acquisition over the whole envelope

Two interchangeable statistics; both were validated. Use (a) as primary.

**(a) Interval-censored cost** (`exp23_censored.py`, envelope-safe, no bias table):

```
def cost(φ, L):
    S = 0; N = 0
    for (u0, u1, s, kind) in brackets:
        t0 = φ + u0·L ; t1 = φ + u1·L ; tm = (t0+t1)/2
        if kind > 0:                                   # rise: target k·BIT
            e = round(tm/BIT)·BIT
            c = max(0, t0 - e, e - t1)                 # 0 if the edge fits inside
        else:                                          # fall: k·BIT + T0H or T1H
            c = min over TH in {T0H_EFF, T1H_EFF} of
                    max(0, t0 - e_TH, e_TH - t1)
                where e_TH = round((tm-TH)/BIT)·BIT + TH
            c = c · W_FALL
        S += min(c, CLIP)² ; N += 1
    return S / N

L_coarse, φ_coarse = argmin over
    L ∈ arange(L_LO, L_HI, DL_COARSE),  φ ∈ arange(-100, 400, 50)
```

The cost is zero whenever the model's bit boundary lands anywhere inside the
observed bracket, so it is *unbiased* regardless of how wide the dead zone
is — exactly the property the midpoint estimator lacks.

**(b) Bias-corrected rising-edge periodogram** (`exp7`/`exp8`, cheaper, needs a
per-slot phase table `bf[s]` expressed as a fraction of L):

```
J(L) = | Σ_j sinc(g_j·L/BIT) · exp(2πi·(u_mid,j·L + bf[s_j]·L)/BIT) | / Σ_j |sinc(...)|
L_coarse = parabolic-interpolated argmax of J over the same grid
```

Measured on real captures: `J_peak ∈ [0.996, 1.000]`, second-peak ratio
mean 0.227 / max 0.287, 0.95-width 4.65 ns. **Use (b) only when the estimated
ε is within ±1 % of the clock at which `bf` was fitted** — outside that,
E4/`exp12` shows it locks wrong aliases (54/54 failures at ±7.5 %).

Record the top 3 local maxima as `alias_candidates` for Stage 5.

### Stage 3 — fine refinement

Coordinate/pattern search on `cost(φ, L)` from Stage 2's seed:

```
dφ, dL = 60.0, 3.0
repeat 7 times:
    while an improving move exists among
          (±dφ,0), (0,±dL), (±dφ,±dL):  accept it
    dφ *= 0.45 ; dL *= 0.45
```

(Equivalently: iterated closest-bit weighted least squares with Huber
weights, which converges in ~20 iterations and is what `exp8` used. Both
reach the same optimum; the pattern search avoids needing `bf`.)

Add the trigger prior as a soft term when the edge count is low
(< 60 brackets): `+ λ·((φ − PHI_FRAC·L)/(PHI_FRAC_SD·L))²`, λ = 1.

### Stage 4 — integer bit origin `k0`

The capture is edge-triggered on the frame's first rising edge, so `k0 = 0`
is the strong prior (`exp19`: 38/54 with an uncalibrated slot model, and the
16 `k0 = −1` cases all disappear once the slot bias is applied). Resolve it
by header/trailer correlation, which needs no payload knowledge:

```
HDR = bits of FF 00 AA 65   (32 bits)      TRL = bits of 9A 55 00 FF (32 bits)
for k0 in K0_RANGE:
    slice bits 0..191 on the grid shifted by k0·BIT
    score(k0) = agreement(bits[0:32], HDR) + agreement(bits[160:192], TRL)
k0 = argmax score ;  hdr_score = max score          # out of 64
```

### Stage 5 — lock validation and alias retry

```
locked = (J_peak >= J_MIN) and (second/first <= RATIO_MAX)
         and (hdr_score >= HDR_MIN) and (residual_rms <= 3·SIGMA_EDGE)
if not locked:
    for L_c in alias_candidates ∪ {L̂ ± ALIAS_STEP, L̂ ± 2·ALIAS_STEP}:
        rerun Stage 3+4 seeded at L_c ; keep the best hdr_score
if still not locked: emit lock_ok = False (do not silently return a grid)
```

The header/trailer span is used here as a *global integer* consistency check
(`t_last_fall = 191·BIT + T1H = 239450.0 ns` exactly), which is what it is
good for — not as the rate estimator (E3).

### Stage 6 — tracker (frozen-rate Kalman, not a PLL)

State `x = [θ, ν]` (grid phase in ns, loop period in ns), measurement = one
edge bracket, `H = [1, u_j]`.

```
Prediction:  x stays, P += Q·Δu     with  Q = diag(0, q_ν)
Correction:  only when the bracket does NOT contain the predicted boundary
             (censored innovation): y = signed distance to the nearer bracket end
             K = P·Hᵀ / (H·P·Hᵀ + R),  R = SIGMA_EDGE²
             x += K·y ;  P = (I − K·H)·P
```

Process noise from the data, not from a guess: E2's bound on the residual
rate ramp is 2.8 ns end-to-end over 96 loops, i.e.

```
q_ν = (2.8 / 96)² / 96  ≈ 8.9e-6 ns²/loop      # sd(ν) grows ~0.029 ns over the frame
```

At that `q_ν` the filter is numerically indistinguishable from the global
2-parameter fit — which is the correct behaviour (E2). Equivalent
proportional/integral gains: `KP = 0, KI = 0`.

**Trip-wire** (the only thing that opens the loop):

```
split the frame into 6 segments of 32 bits
seg_phase[g] = median over edges in g of (t - round(t/BIT)·BIT)
if max(seg_phase) - min(seg_phase) > DRIFT_TRIP  and  the profile is monotone:
    refit with a quadratic phase term  t = φ + u·L + c2·(u - ū)²
    (ridge-penalise c2 toward 0 with weight (36 ns)⁻²)
    or raise gains to KP = 0.1, KI = 0.004  (the largest values that helped
    at all in exp14; never higher)
```

Measured on real data the spread is dominated by slot-mix hopping, not drift,
and `exp9` shows order-1 and order-2 fits are indistinguishable even with a
+0.2 % ramp injected at ε = −7.5 % (res_max 310.8 vs 306.6 ns). The
monotonicity condition prevents the trip-wire firing on E2's hopping.

### Stage 7 — decision-directed re-fit (optional, after the first decode)

Once the downstream stack has produced 192 bits, every *falling* edge gains a
known target (`k·BIT + T1H` or `k·BIT + T0H`), roughly doubling the edge
count. `exp21_dd_refine.py` shows this must be done carefully: naively adding
falls raises the residual rms from 10.9 → 262.7 ns, because falls have their
own slot geometry. `exp22_fall_bias.py` fits separate global per-slot fall
biases split by bit value and the residual drops to **8.3 ns**, matching
rises. Under the interval-censored cost the bias vectors are unnecessary —
the fall term in Stage 2(a) already handles it, and Stage 7 simply replaces
`min over {T0H, T1H}` with the decided value. Expected benefit is small
(`exp21`: |ΔL| change ≤ 2.73 ns, mean −0.09) but it is the natural place to
close an EM loop with the slicer.

---

## Calibration

| quantity | scope | how estimated |
|---|---|---|
| `a[0..7]` slot offsets, **as fractions of the loop** | **global** (per firmware build) | From `approaches/dev_calibration/fitted_model.json` as `o[s]/G`. Fallback: `[1,5,9,13,17,21,27,32]/40`. **Never per capture** — E4 proves the per-capture problem is exactly degenerate at L = 2·BIT. |
| `T0H_EFF`, `T1H_EFF` | global | From the same calibration file (`h0 = 339.25`, `h1 = 737.25`). These absorb the sampler's input aperture; they differ from the transmitter's exact 350/700. |
| `bf[0..7]` bias table (optional fast path only) | global, **clock-conditional** | Iterated median of rising-edge residuals by starting slot (`exp6`, 4 rounds, converges to rms 22.1 ns). Valid only within ±1 % of the clock it was fitted at. |
| `L` loop period | **per capture** | Stage 2 grid over ±8.5 %, then Stage 3. Never seeded from a constant (`PULLIN` = ±0.26 %). |
| `φ` grid origin | **per capture** | Jointly with `L` in Stage 2/3; prior `φ = (0.0528 ± 0.0036)·L` from the trigger (measured 131.9 ± 9.0 ns, range [103.2, 143.6] over 54 captures). |
| `k0` integer origin | per capture | Header/trailer correlation, Stage 4; prior `k0 = 0`. |
| `q_ν` process noise | global | From E2's measured 2.8 ns end-to-end bound: `q_ν ≈ 8.9e-6 ns²/loop`. |
| `SIGMA_EDGE` | global | rms of the Stage-3 residual, measured 5.8–15.8 ns, mean 10.9 ns → use 12 ns. |

**Error decomposition** (the implementer should know which term dominates):
statistical σ_L from ~180 edges is ≈ 0.03–0.09 ns (matching the observed
0.084 ns spread over 54 captures), while systematic σ_L from an imperfect
slot calibration is ≈ 3.4–4.0 ns (`exp24`: censored estimator on real data
with documented fractions gives std 4.00 ns; with the exp18-fitted offsets,
3.38 ns). **Calibration quality is 40× the dominant error term.** Improving
`a[]` is worth more to this technique than anything in Stages 2–6.

---

## Envelope behavior

Nothing in the algorithm assumes a clock. `L_NOM` is only the centre of the
search and `EPS_MAX = 0.085` covers one point past each guaranteed corner.

**Acquisition across ±8 %** (`exp23`/`exp24`, censored cost, correct slot
fractions, grid 2280–2740 ns):

| ε | L_true | median \|ΔL\| | max \|ΔL\| | fails > 4.5 ns |
|---|---|---|---|---|
| −8.0 % | 2717.39 | 0.001 | 0.335 | 0/54 |
| −7.5 % | 2702.70 | 0.095 | 0.095 | 0/54 |
| −5.0 % | 2631.58 | 0.148 | 0.186 | 0/54 |
| −2.5 % | 2564.10 | 0.103 | 0.103 | 0/54 |
| −0.2 % | 2505.01 | 0.013 | 0.147 | 0/54 |
|  0.0 % | 2500.00 | 0.000 | 0.000 | 0/54 |
| +0.2 % | 2495.01 | 0.085 | 2.910 | 0/54 |
| +2.5 % | 2439.02 | 0.101 | 0.196 | 0/54 |
| +5.0 % | 2380.95 | 0.345 | 0.900 | 0/54 |
| +7.5 % | 2325.58 | 0.145 | 0.145 | 0/54 |
| +8.0 % | 2314.81 | 0.029 | 0.066 | 0/54 |

`exp9_envelope.py` independently confirms with the LS variant: **0/54 lock
failures at every ε**, coarse error ≤ 1.25 ns, refined error ≤ 0.59 ns.
The one apparent failure in an earlier run (15/54 at ε = −8 %) was a **grid
truncation bug** — `L_HI` must reach 2732 ns; the retest with the widened
grid is 0/54. Ship `L_HI = L_NOM/(1 − EPS_MAX)`, not a rounded number.

**Slow corner (ε = −7.5 %, the hard corner per HSI_TEMPERATURE.md).** The
loop stretches to 2702.7 ns, δ = L − 2·BIT = **+202.7 ns/loop**, so the
sampling phase crawls **14.4 bits over the frame**. Effects, measured on
synthetic captures (`exp20`):

- Rising edges detected: 177.2 of 192 (14.8 lost). Only slightly worse than
  the 8–15 lost at other non-commensurate points, and *better* than the 23.2
  lost at ε = −0.2 %.
- Merged pulses: 32.3 per capture (vs 45.4 at +7.5 %). Merging removes rising
  edges, but E8 shows the estimator survives losing 85 % of them.
- Estimation is *easier*, not harder: the large crawl gives full sampling-phase
  diversity, so `exp14`'s slot-calibration tolerance rises to 130 ns rms
  (vs 20 ns near commensurate).
- Grid quality holds: `exp15` reports max |Δt| = 32.0 ns and 0.20 % mean bit
  misassignment at ε = −7.5 %, vs 28.6 ns / 0.06 % at +7.5 %.

**Within-capture drift.** The specified ±0.2 % ramp is a non-event for this
technique. `exp9` at ε = −7.5 % with a +0.2 % ramp: res_rms 103.9 (order-1)
vs 103.5 (order-2), against a 104.2 no-drift reference — the drift is below
the noise floor of the estimator. The Stage-6 trip-wire exists only so that
a genuinely out-of-spec unit degrades gracefully rather than silently.

**Fast corner (ε = +7.5 %).** L shrinks to 2325.6 ns; the dead zones shrink
with it, merging and swallowing nearly vanish (only 8.2 rises lost), and all
metrics improve. This corner is free.

**Where the envelope genuinely bites** is neither corner but **ε near, but not
at, zero** (E7): |δ| small ⇒ frozen sampling phase ⇒ no averaging, the tightest
slot-calibration requirement (20 ns rms at ε = −0.5 %), the highest 0-bit loss
count (23.2 at ε = −0.2 %), and the exact degeneracy of E4 at δ = 0. **The
real bench captures sit in exactly this regime** (δ ≈ −0.2 ns/loop). The
implementer should treat "the estimator locked cleanly" as *not* implying
"the bits are easy".

---

## Failure modes

Honest accounting of where clock_stretch alone loses bits.

1. **It decodes nothing on its own.** `exp8_pipeline.py` runs the full blind
   clock pipeline followed by a deliberately naive slicer (bit = 1 if ≥ 2 high
   samples in the predicted window): **9/54 exact, 2051/10368 bit errors.**
   A perfect time base plus a bad slicer is still a bad decoder. This
   technique's deliverable is the grid, not the bits.

2. **It is blind to the 5/3 sampling asymmetry.** At the bench point every
   even bit gets 5 samples and every odd bit gets 3 (`exp19`, exactly
   5184/5184 with no 4s). A grid-only view reports "4.00 samples per bit on
   average" and hides that half the bits are 40 % undersampled. The slicer
   must be told the per-bit sample count; the grid alone will not save an
   odd-indexed 0-bit whose 350 ns T0H sits inside the slot7→slot0 gap.

3. **Hard dependency on the slot calibration.** With no calibration at all
   (`bf = 0`, `exp12`), real-capture L estimates spread to std 4.38 ns with
   **16/54 outliers > 3 ns** — three of those exceed the 4.5 ns budget and
   would slip a third of a bit at the frame end. With a calibration that is
   wrong in *kind* (a bench-fitted table applied at a different clock) the
   failure is catastrophic and silent: 54/54 wrong-alias locks at ±7.5 %.

4. **Exact degeneracy at δ = 0.** If a unit lands at L = 2·BIT exactly, the
   per-slot phase and the grid phase are unidentifiable (E4). The design
   handles this by refusing to fit slot offsets per capture, but it means the
   *quality* of a capture at δ ≈ 0 is bounded by the global calibration and
   cannot be improved from within the capture.

5. **One-bit-slip aliases are only 13 ns away.** `ALIAS_STEP = BIT/U_frame` =
   13.0 ns = 0.52 % of the clock. The coarse peak margin is comfortable on
   real data (second/first ≤ 0.287) but a capture that loses most of its
   rising edges — an all-ones payload at the slow corner, where merging is
   worst — narrows it. The Stage-5 header/trailer validation is the only thing
   that catches a slipped lock; without it, a 13 ns error produces a
   *plausible-looking* grid that is off by exactly one bit at the end.

6. **The trigger prior is a bench measurement.** `φ = (0.0528 ± 0.0036)·L`
   was fitted on one firmware build; a recompiled edge-detect preamble moves
   it. If the prior is used with `λ = 1` on a build where it is wrong, it will
   pull φ by up to its own error. Use it only in the low-edge-count branch.

7. **Truncated frames.** Stage 0 assumes the frame is fully contained
   (`i_last ≤ 95` on all 54 captures). A frame that runs past the buffer
   silently shortens `U_frame` and biases L. Guard: `i_last` must be in
   [88, 104]; outside that, refuse to lock.

8. **It cannot recover a swallowed bit, ever.** A T0H that produces zero high
   samples leaves the grid perfectly happy — the bit window simply contains
   four low samples. That is `missed_zero`'s job, and the grid is what makes
   it possible (a missed zero is only detectable as *"this bit's window is
   low but the model says a bit boundary is here"*).

---

## Composition interface

**Pipeline position: Stage 1 of 2 — immediately after slot calibration, before
every slicing technique.** All five other techniques become functions of
`(bit_index, phase_within_bit)` rather than of `(iteration, slot)`.

### Inputs required

```
samples : [(it, slot, lev)]                       from harness.linearize()
a[0..7] : slot offsets as fractions of the loop   from dev_calibration (REQUIRED)
h0, h1  : effective high widths                    from dev_calibration (optional)
```

If `dev_calibration` has not converged, fall back to `[1,5,9,13,17,21,27,32]/40`
and raise `cal_quality = "documented-fallback"`; downstream techniques should
widen their own tolerances by the 3.4–4.0 ns σ_L this implies.

### Outputs provided

Hard outputs (the time base):

```
lock_ok        : bool
L_hat, phi_hat : float ns      per-capture loop period and grid origin
eps_hat        : float         = L_NOM/L_hat - 1   (relative HSI error)
k0             : int           integer bit origin (≈ 0)
t[n]           : float ns      absolute time of every sample
k[n]           : int           bit index of every sample
frac[n]        : float [0,1)   phase within the bit
n_per_bit[b]   : int           samples in bit b's window  (3 or 5 at the bench)
```

Soft outputs (posteriors / confidences — the useful part for composition):

```
sigma_L, sigma_phi, cov_L_phi   : from the Stage-3 Hessian; typ. sigma_L ~= 0.09 ns
sigma_t(b) = sqrt(sigma_phi^2 + (u_b*sigma_L)^2)
                                : per-bit timing uncertainty, ~8-20 ns at the frame end
J_peak, peak_second_ratio       : coarse lock quality   (real data: 0.996-1.000 / <=0.287)
resid_rms, n_brackets           : fit quality           (5.8-15.8 ns / 152-190)
hdr_score                       : header+trailer agreement out of 64
alias_candidates : [(L, J)]     : top-3 coarse peaks, for a downstream retry
delta = L_hat - 2*BIT           : beat crawl per loop  (bench: ~ -0.2 ns/loop)
commensurate_risk = |delta| < 3 : bool -- warn that errors will be CLUSTERED (E7)
segment_phase[0..5]             : the drift trip-wire evidence, for logging
```

Constraints it can enforce on the other techniques:

- **Bit-grid rigidity.** 192 bit starts at exactly `k0·BIT + k·BIT` in the
  estimated time base. No slicer may place a bit boundary off this grid; any
  technique that wants a per-bit boundary adjustment must justify it against
  `sigma_t(b)` (≈ 10 ns), not against a bit period.
- **Frame-span constraint.** `t_last_fall = 191·BIT + T1H = 239450.0 ns` is an
  exact anchor. Reject any decode whose last falling edge lands more than
  `3·sigma_t(191)` from it.
- **Known-bit constraint.** The 32 header and 32 trailer bits are fixed; any
  technique's posterior over those must be clamped, and their disagreement is
  the shared lock-validity signal (`hdr_score`).
- **Sample-count prior.** `n_per_bit[b]` tells `missed_zero` and
  `histogram_adaptive` exactly how many observations each bit actually got —
  the 5/3 alternation means a "no high samples" observation is ~1.7× weaker
  evidence on odd bits than on even ones.

### How it combines with the other five

```
             +-- dev_calibration: a[], h0, h1 (global, offline)
             v
  [1] clock_stretch  ->  t[n], k[n], frac[n], sigma_t(b), n_per_bit[b]
             |
             +--> [2] boundary_model     : consumes frac[n] to model which
             |         dead zone each bit's T0H/T1L falls into. Needs the grid
             |         to know *where* the gaps sit relative to bit phase.
             +--> [3] matched_filter     : correlates the expected 0/1 sample
             |         template against lev[] on the grid; needs t[n] to build
             |         the template and n_per_bit[b] to normalise.
             +--> [4] histogram_adaptive : thresholds on high-sample counts
             |         per bit; needs n_per_bit[b] to avoid comparing 3-sample
             |         and 5-sample bits on the same scale.
             +--> [5] missed_zero        : detects "bit window is entirely low"
             |         -- only meaningful once the window is correctly placed.
             +--> [6] edge_dp            : Viterbi over bit sequences; takes
                       sigma_t(b) as its transition-timing variance and the
                       header/trailer clamp as boundary conditions.
             |
             v
  [7] (optional EM) decision-directed re-fit: feed the decided 192 bits back
      into clock_stretch Stage 7, which turns every falling edge into a hard
      constraint, then re-run [2]-[6] once. Measured tightening is small
      (|dL| <= 2.7 ns) -- run at most 2 iterations and keep the pass with the
      higher hdr_score.
```

**Combination rules that matter:**

1. clock_stretch must run **before** any technique reads a level, and must
   run **after** calibration. It is the only technique with a hard ordering
   requirement.
2. Emit soft, not hard: downstream should receive `sigma_t(b)` and integrate
   over grid uncertainty rather than trusting `t[n]` exactly. At the frame end
   `sigma_t(191)` ≈ 9 ns statistical but ≈ 330 ns if the calibration is the
   documented fallback — a 0.26-bit uncertainty that `edge_dp` should carry.
3. On `lock_ok = False`, the correct action is to **re-run the whole stack**
   on `alias_candidates[1]`, not to decode with a bad grid. The composed
   decoder should keep the candidate with the best `hdr_score`, breaking ties
   on total downstream likelihood.
4. `commensurate_risk` should switch downstream error handling from
   "independent bit errors" to "clustered bit errors": at δ ≈ 0 a bad
   sampling phase persists for the whole frame, so a technique that assumes
   independent per-bit noise (a plain histogram threshold) will be
   over-confident. `edge_dp` should widen its state or `boundary_model`
   should take over.
5. `eps_hat` is also a **product output**, not just an internal: it is a live
   measurement of the HSI error against a crystal reference, which is exactly
   the runtime `CLK_HSITRIMR` trim source that HSI_TEMPERATURE.md §3 asks for
   (measured precision 0.0035 % — 600× better than the ±2 % trim step).

---

## Key numbers

Constants and measurements to reuse. Script names are the source.

**Time base (bench point)**

| quantity | value | source |
|---|---|---|
| `L_bench`, loop period | **2499.815 ± 0.084 ns** (range 2499.59–2500.04) | exp8, 54 captures, blind |
| cross-check, joint likelihood | peak 2498 ns; 86.4 % vs 72.0 % at 2507.3 | exp17/exp18 |
| cross-check, beat slope | 2497–2499 ns | exp10 |
| cross-check, merge-episode | 2499.6–2500.4 ns | exp20 |
| absolute uncertainty (degeneracy-limited) | **2500 ± 3 ns** | exp27 |
| `harness.LOOP_NS = 2507.3` | **too high by ≈ 7.5 ns (0.30 %)** — do not use as a time base | exp17, exp10, exp20 |
| implied bench ε | **+0.007 %** vs 40 cy @16 MHz (not −0.3 %) | exp19 |
| between-capture spread (one session) | **0.018 %** | exp19 |
| beat crawl δ = L − 2·BIT | **−0.2 ns/loop** (not +7.3) | exp20 |
| total crawl over the frame | −19 ns = **−0.015 bit** | exp20 |
| `φ` trigger offset | **131.9 ± 9.0 ns**, range [103.2, 143.6] = **0.0528·L** ≈ 2.11 cy | exp19 |
| `k0` | 0 (38/54 uncalibrated; all 54 once slot bias applied) | exp19 |

**Frame geometry**

| quantity | value |
|---|---|
| frame length | 192 bits = 240 000 ns; last falling edge at **239450.0 ns** exactly |
| `U_frame` | 192·1250/L = **96.01 loops** |
| loops actually carrying the frame | **0…95 of 640** (545 loops, 85 % of the buffer, are idle low) |
| in-frame samples | ~768 of 5117 |
| samples per bit | **3 or 5, alternating by bit parity — never 4** (exactly 5184/5184 over 54×192) |
| rising brackets observed | 152–190 of 192 (median ~180); `ones` 152–154, `zeros` 182–187 |

**Estimator design constants**

| quantity | value | source |
|---|---|---|
| fine-stage pull-in | **±6.5 ns = ±0.26 % = BIT/(2·U_frame)** (54/54 converge inside, 0/54 outside) | exp7 |
| alias spacing | **13.0 ns = BIT/U_frame** | exp7/exp19 |
| coarse grid | `L ∈ [2304.1, 2732.2]`, step **2.0 ns** (203+ points); must reach 2732 — a 2710 cap breaks ε = −8 % | exp23/exp24 |
| coarse peak quality (real) | `J_peak` **0.996–1.000**; second/first mean 0.227, max 0.287; 0.95-width 4.65 ns | exp7/exp19 |
| Stage-3 residual rms | **5.8–15.8 ns, mean 10.9**; max residual mean 31.1, worst 40.3 ns | exp8/exp14 |
| σ_L statistical | **0.03–0.09 ns** | exp8/exp19 |
| σ_L systematic (calibration-limited) | **3.4–4.0 ns** ⇒ 0.26 bit at the frame end | exp24 |
| ΔL budget | **4.5 ns = 0.35 bit slip**; 13 ns = full slip | exp19 |
| envelope accuracy (correct `a[]`) | median \|ΔL\| ≤ 0.35 ns, max 2.91 ns, **0/54 fails at every ε ∈ [−8 %, +8 %]** | exp23/exp24 |
| grid quality vs exact truth | max \|Δt\| ≤ **54 ns**, rms 9–21 ns, bit-misassignment ≤ 2.5 % worst / ≤1.3 % mean | exp15 |
| robustness to edge loss | keep **15 %** of rises (~28 edges) → \|ΔL\| ≤ 0.42 ns, 0/54 > 3 ns | exp12 |
| slot-cal tolerance (rms per-slot error) | 130 ns at ε = ±7.5 % and ±2.5 %; **only ~10–20 ns at ε = −0.5 %** | exp14 |
| no-calibration penalty | `bf = 0` → L std 4.38 ns, **16/54 outliers > 3 ns** | exp12 |
| within-capture wander | linear term **max 2.8 ns end-to-end = 0.0012 % of clock**, mean 0.0, std 1.2 | exp6 |
| ±0.2 % spec ramp, raw / after linear fit | 36 ns / ~9 ns bow | derived + exp9 |
| PLL benefit | rms 10.9 → 8.9 ns at kp = 0.3 on real; **worse** on injected drift | exp14 |
| two-anchor (header vs trailer) scale error | **up to 5.96 ns (0.24 %), std 1.36** — 15–70× worse than the global fit | exp11 |

**Calibration tables (bench point; use only within ±1 % of L_bench)**

```
rising-edge slot-pair bias (ns), fitted globally over 54 captures, exp6:
    [-296.3, -530.4, +444.1, +168.5, -63.6, -346.1, +539.5, +84.3]
    -> as a fraction of L, divide by 2499.6

falling-edge slot bias (ns), split by the bit's value, exp22
    (residual drops 234.1 -> 8.3 ns rms):
    0-bit falls: [ +28.5, -208.5, -446.9, +542.1, +279.1,  -27.6, -353.0, +447.3]
    1-bit falls: [+401.4, +128.2, -114.5, -360.5,    0.0, +325.3,  -23.4, -443.3]

effective high widths (dev_calibration/final.json): h0 = 339.25, h1 = 737.25 ns
    (vs the transmitter's exact 350 / 700 -- the difference is sampler aperture)
```

**Merged-pulse episodes (bench, 1-rich patterns, exp20)** — useful as an
independent crawl check on any new capture:

```
ones   rep0/1/2 : 33 / 32 / 34 loops (one long episode each)
dense  rep0     : 3, 7, 8, 4, 1, 2, 2       runs rep0 : 4, 9, 9, 9, 3, 3
aa, p55         : only 1-3 loop episodes
|delta| = (gap_endofloop - T1L) / episode_length  ->  0.36 ns/loop at gap = 562 ns
```

**Envelope reference (synthetic, exp20)**

| ε | L (ns) | δ (ns/loop) | crawl/frame (bits) | rises lost /192 | merges |
|---|---|---|---|---|---|
| −8.0 % | 2717.4 | +217.4 | 15.4 | 14.7 | 36.4 |
| −7.5 % | 2702.7 | +202.7 | 14.4 | 14.8 | 32.3 |
| −2.5 % | 2564.1 | +64.1 | 4.8 | 14.0 | 40.0 |
| −0.2 % | 2505.0 | +5.0 | 0.38 | **23.2** | 13.7 |
| 0.0 % | 2500.0 | 0.0 | 0.00 | **1.0** | 0.0 |
| +2.5 % | 2439.0 | −61.0 | −4.8 | 7.8 | 42.3 |
| +7.5 % | 2325.6 | −174.4 | −14.4 | 8.2 | 45.4 |

(The ε = 0 / ε = −0.2 % rows are the E7 story: loss count is a *lottery* set
by the frozen phase, not a smooth function of ε.)
