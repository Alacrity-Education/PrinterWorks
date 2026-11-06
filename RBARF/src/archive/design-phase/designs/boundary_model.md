# boundary_model — technique design

Non-uniform sampling-grid model. Turns `(iteration, slot)` coordinates into
true per-sample timestamps, and turns those timestamps into a statement of
**which bit cell each sample constrains, how strongly, and where the
information is genuinely absent**.

All numbers below were measured on `data/captures.json` (54 real captures)
by scripts in `designs/dev_boundary_model/` (`bm_offsets.py`, `bm_int.py`,
`bm_scan.py`, `bm_phase.py`, `bm_final.py`, `bm_soft.py`, `bm_probe.py`,
`bm_slot7.py`, `bm_perr.py`, `bm_env.py`).

---

## Target artifact & evidence

### The artifact

DATASET.md artifact #3: *byte-boundary delays*. The sampler's 8 slots are
not uniformly spaced, and the loop is ~40 cycles rather than the 37 the
source comment claims. Where those extra cycles sit decides where the
dead zones fall, which decides which bits leave no trace at all. Every
other technique in this project builds on a time base; if the time base is
wrong by one inter-slot gap, pulse widths, edge positions and matched
filters are all wrong in a *structured*, data-correlated way.

### What the data says

**1. The loop is 40 CPU cycles, and the intra-loop positions are (almost)
exactly the documented ones. All ~3 undocumented cycles are in the
loop-back branch.**

The clean way to measure intra-loop geometry is to give every loop its own
free phase `phi_i`. That absorbs *all* clock scale, phase and drift, so
what remains is pure intra-loop geometry. Objective = mismatched samples
over 54 captures × loops 0..93 × 8 slots = 40 608 samples, wire level
computed from the known frame bits (`bm_offsets.py` / `bm_int.py`):

| geometry (cycle positions), cycle τ | mismatch |
|---|---|
| documented `[1,5,9,13,17,21,27,32]`, τ=62.5 | **3.566 %** |
| documented, τ=62.75 | 1.596 % |
| `[1,5,9,13,17,21,27,31]`, τ=62.75 | **1.172 %** |
| best integer fit `[1,4,8,13,17,21,27,31]`, τ=62.75 | 1.172 % |
| unconstrained 8 **real-valued** offsets (free fit) | 1.172 % |
| uniform 4-cycle spacing `[1,5,9,13,17,21,25,29]` | 3.221 % |
| `dev_calibration/final.json` geometry `[1,5,9,14,18,22,28,32]`, τ=62.5 | 2.295 % |

Two things matter here. First, the integer-cycle model **loses nothing**
against a free real-valued 8-offset fit (both 1.172 %), so the geometry
really is integer CPU cycles — no need for the fractional offsets that
`dev_calibration` reports. Second, the *documented* positions with slot 7
pulled in one cycle are already optimal; there is no need to redistribute
cycles inside the loop. Per-slot ±3-cycle scan around the optimum
(`bm_scan.py`) gives the identifiability:

```
C[1]=4/5 tie   C[2]=8/9 tie   C[3]=13   C[4]=16/17 tie
C[5]=21 (±1 costs 1.2 pp)     C[6]=27 (±1 costs 0.7 pp)   C[7]=30/31 tie
```

A **non-circular** leave-one-slot-out test (`bm_slot7.py`: fit `phi_i`
from the other 7 slots, then scan the probe slot's position) confirms slot
7 at C=31 with a best offset of **+5 ns** — i.e. within a tenth of a
cycle. So:

```
LOOP_CY = 40,  SLOT_CY = [1, 5, 9, 13, 17, 21, 27, 31]
GAP_CY  = [4, 4, 4, 4, 4, 6, 4, 10]      # gap[7] wraps to next loop's slot 0
```

The assembly (`cap_code.s`) accounts for 37 of those 40 cycles. The
remaining 3 are at the `JRNE` loop-back — a taken-branch refill —
i.e. **entirely inside the slot7→slot0 gap**, which is therefore
**10 cycles ≈ 625 ns**, not the 6 cycles the source comment claims.

**2. The sampler's loop length is data-independent.** The
`BTJT`/`NOP`/`RLC` idiom is 4 cycles whether the branch is taken or not.
Adding a per-HIGH-read cycle shift (`bm_int.py`, parameter `dcy`) makes
things worse, not better:

```
dcy =  0 : 1.172 %      dcy = -1 : 1.258 %      dcy = +1 : 3.787 %
```

This directly contradicts the per-slot data-dependent term `w` in
`approaches/dev_calibration/fitted_model.json` (`final.json`). See
"Calibration → relationship to dev_calibration" below.

**3. The effective high widths are the nominal ones.** A 5×5 grid scan
over `(h1, h0)` puts the optimum exactly at **(750, 375) ns** — no STM8
input-threshold correction is warranted. (`dev_calibration` reports
737.25 / 339.25; that is its own model error being absorbed.)

**4. The loop period is ~2 bit periods, so the alignment barely moves.**
Per-capture loop period `G` (from the slope of the tracked `phi_i`,
`bm_final.py`):

```
G:  min 2494.5   median 2498.4   max 2513.1 ns      (spread 0.75 %)
tau = G/40 = 62.36..62.83 ns  ->  f_cpu 15.92..16.03 MHz, eps -0.5%..+0.2%
```

`harness.LOOP_NS = 2507.3` is 0.36 % above the measured median — do not
use it as a default. `G - 2500` is the **crawl rate**: −5.5 to +13 ns per
loop. The frame lives in loops 0..95 of 640; the other 544 loops are latch
low.

**5. The decision window is 375 ns wide, and roughly a fifth of one bit
position per loop can fall entirely inside a dead zone.** A sample at
in-bit phase `p` is informative iff `p ∈ [375, 750)`; below 375 the line
is high for both bit values, at or above 750 it is low for both. Measured
on the fitted grid (`bm_final.py`, payload bits only, 54 × 128 = 6912):

```
informative samples per payload bit:  0 -> 125 (1.81 %)
                                      1 -> 4510 (65.2 %)
                                      2 -> 2277 (32.9 %)
                                     >2 -> 0
blind payload bits: 125 = 1.81 %, mean 2.3/capture
   distribution: 0 blind in 36 captures, 7-9 blind in 18 captures
   (the 18 are exactly the captures with G >= 2508 ns)
blind bit caused by the gap after slot 7: 119 / 125
blind bit caused by the gap after slot 5:   6 / 125
max run of consecutive blind bits: 1   (never two in a row)
```

**No bit ever gets more than two informative samples**, and two thirds get
exactly one. There is essentially no redundancy: one mis-timed sample is
one wrong bit. That is the single most important fact this technique
contributes.

**6. Information is concentrated in three slots.** Fraction of each slot's
samples that land in a decision window:

```
slot     0      1      2      3      4      5      6      7
frac   0.041  0.273  0.634  0.303  0.030  0.080  0.674  0.620
```

Slots 2, 6, 7 carry ~74 % of all bit evidence; slots 0 and 4 are almost
always in a blind zone.

**7. Slot 7 is the unreliable one.** Error rate of *informative* samples
against the true bit (`bm_perr.py`):

```
slot      1      3      6      2      5      7      4      0     all
rate   0.14%  0.70%  0.81%  1.37%  6.8%   8.2%  18.8%  36.9%   3.52%
n       1415   1572   3478   3287    411   3203    154    214   13734
```

Slot 7's errors are one-sided (predicted HIGH, read LOW) and concentrated
on 1-bits, because in the phase regime the trigger locks the sampler into,
slot 7 sits at in-bit phase ≈ 695 ns — only ~55 ns before the T1H falling
edge. Its *position* is confirmed correct (+5 ns), so this is a margin
problem, not a geometry problem. Slots 0 and 4 are informative so rarely
that when they are, the loop is in a fast-transition regime where the
phase estimate is weakest.

---

## Algorithm

### Global constants (hardware — never re-fit per capture)

```
LOOP_CY  = 40                              # CPU cycles per sampling loop
SLOT_CY  = [1, 5, 9, 13, 17, 21, 27, 31]   # slot read positions, cycles
GAP_CY   = [4, 4, 4, 4, 4, 6, 4, 10]       # GAP_CY[s] = SLOT_CY[s+1]-SLOT_CY[s],
                                           #   GAP_CY[7] wraps to next loop
SPAN_K   = 1.006          # intra-loop stretch when tau is tied to G/LOOP_CY
BIT_NS   = 1250.0         # exact, crystal
H0_NS    = 375.0          # exact ('0' high width)
H1_NS    = 750.0          # exact ('1' high width)
WIN_LO, WIN_HI = H0_NS, H1_NS              # the decision window
SIG_NS   = [55, 25, 35, 30, 60, 55, 35, 60]   # per-slot timing sigma (see below)
PERR     = [0.369, 0.0014, 0.0137, 0.0070,    # per-slot error floor, MEASURED
            0.188, 0.068, 0.0081, 0.0815]
LLR_CAP  = 6.0
```

`SPAN_K` matters: with `tau = G/40`, `SPAN_K * 30 = 30.18` cycles of
intra-loop span, so the end-of-loop gap is `40 - 30.18 = 9.82` cycles
rather than a flat 10. Fitting `SPAN_K` on real captures
(`bm_probe.py`, part C) gives a clear optimum at 1.006 (1.000 → 2470
mismatched samples, 1.006 → 1934, 1.010 → 1990). Equivalently, use a free
intra-loop `tau_intra ≈ 62.75 ns` alongside `tau_loop = G/40 ≈ 62.45 ns`;
that scores marginally better still (1883) but needs two clock
parameters instead of one.

### Per-capture state

```
tau        : CPU cycle in ns
phi[0..L-1]: per-loop phase offset in ns (L = number of loops spanned by frame)
```

### Core: timestamps and dead zones

```
function timestamps(samples, tau, phi):
    for each sample m = (i, s, level):
        t[m] = LOOP_CY * tau * i  +  phi[i]  +  SPAN_K * tau * SLOT_CY[s]
    return t

function dead_zones(t):
    # one interval per consecutive sample pair, in chronological order
    for m in 0 .. len(t)-2:
        Z[m] = (t[m], t[m+1])           # width = GAP_CY[slot(m)] * tau * SPAN_K
    return Z
```

`Z[m]` is where the line may do anything unobserved. Width is
`4τ ≈ 251 ns` for six of the eight gaps, `6τ ≈ 377 ns` after slot 5, and
`9.82τ ≈ 615 ns` (10 raw cycles, 627 ns, less the `SPAN_K` correction)
after slot 7. Those three numbers are the whole artifact.

### Core: per-sample bit constraint

```
function constrain(t, level):
    b = floor(t / BIT_NS)                 # bit cell index
    p = t - b * BIT_NS                    # in-bit phase
    if b < 0 or b >= NBITS: return NONE
    if p <  WIN_LO:  return (b, BLIND_HIGH)   # line is high for '0' and '1'
    if p >= WIN_HI:  return (b, BLIND_LOW)    # line is low  for '0' and '1'
    return (b, DECIDES, level)                # level == bit value
```

### Core: soft evidence

Model the observed level as a noisy threshold on `p` with per-slot timing
sigma and a per-slot error floor:

```
function llr_contribution(b, p, s, level):
    # P(read HIGH | bit value v) for v = 1 and v = 0
    q1 = clamp01((1 - 2*PERR[s]) * Phi((H1_NS - p) / SIG_NS[s]) + PERR[s])
    q0 = clamp01((1 - 2*PERR[s]) * Phi((H0_NS - p) / SIG_NS[s]) + PERR[s])
    if level == 1: d = log(q1)     - log(q0)
    else:          d = log(1 - q1) - log(1 - q0)
    return clip(d, -LLR_CAP, +LLR_CAP)      # positive favours bit = 1
```

`Phi` is the standard normal CDF (a logistic with scale `SIG/1.7` is
fine). Note the model degrades gracefully: for `p << H0` both `q` are ≈1
and the contribution is ≈0 (blind high); for `p >> H1` both are ≈0 (blind
low); inside the window `q1≈1, q0≈0` and the contribution saturates at
`±log((1-PERR)/PERR)`, which is 2.4 for slot 7 and 6.2 for slot 1 — the
per-slot reliability falls straight out of the model.

### Top level

```
function boundary_model(samples, meta, phase_hint = NONE):
    # ---- 1. clock -----------------------------------------------------
    tau, phi = calibrate(samples, phase_hint)          # see Calibration
    t = timestamps(samples, tau, phi)
    Z = dead_zones(t)

    # ---- 2. per-bit evidence -----------------------------------------
    LLR   = array(NBITS, 0.0)
    EVID  = array(NBITS, [])
    for m, (i, s, level) in enumerate(samples):
        c = constrain(t[m], level)
        if c is NONE: continue
        (b, kind, ...) = c
        p = t[m] - b * BIT_NS
        LLR[b] += llr_contribution(b, p, s, level)
        if kind == DECIDES: EVID[b].append((m, s, p, level))

    # ---- 3. availability masks ---------------------------------------
    for b in 0 .. NBITS-1:
        n_in       = count of EVID[b]
        BLIND[b]   = (n_in == 0)
        CONFLICT[b]= (n_in >= 2 and not all levels in EVID[b] equal)
        MARGIN[b]  = max over EVID[b] of min(p - H0_NS, H1_NS - p)   # ns
        # which gap swallowed the window, for blind bits
        GAPOF[b]   = slot s such that Z[m] covers [b*1250+H0, b*1250+H1)

    # ---- 4. hard constraints for downstream ---------------------------
    EDGE = []
    for m in 1 .. len(t)-1:
        if level[m] == 1 and level[m-1] == 0:
            EDGE.append(RISING, m, (t[m-1], t[m]))   # a bit boundary k*1250 is in here
        if level[m] == 0 and level[m-1] == 1:
            EDGE.append(FALLING, m, (t[m-1], t[m]))  # k*1250 + hw is in here, hw in {375,750}

    return { t, bit_of_sample, phase_of_sample, LLR, EVID,
             BLIND, CONFLICT, MARGIN, GAPOF, Z, EDGE, tau, phi }
```

---

## Calibration

Two levels, and the split is the whole point: **geometry is global,
clock is per capture.**

### Global (fit once, ship as constants)

`LOOP_CY`, `SLOT_CY`, `SPAN_K`, `SIG_NS`, `PERR`. Refit procedure if the
firmware ever changes (this is what `bm_int.py` does):

1. For every capture, for every loop `i`, and every candidate phase `phi`
   on a 1 ns grid over `[0, 1250)`, count mismatched samples of that loop
   against the known frame bits; take the minimum over `phi`. Summing
   these per-loop minima over all captures is an objective that is
   **completely blind to clock scale, phase and drift** — it measures
   intra-loop geometry only.
2. Coordinate-descend integer `SLOT_CY[1..7]` (each gap in 2..10 cycles)
   and continuous `tau` on that objective. `SLOT_CY[0]` is pinned (it is
   absorbed by the phase).
3. Cross-check with a leave-one-slot-out fit (`bm_slot7.py`) so the
   per-slot position is not confirmed by itself.
4. Per-slot `PERR` from the informative-sample error rate table above
   (measured — use those numbers directly).
   `SIG_NS` is **not** independently measured here and the values in the
   Algorithm block are recommended starting points, not results. What was
   measured is the aggregate transition: binning `P(read HIGH)` by in-bit
   phase in 25 ns bins (`bm_soft.py`), the `bit=0` edge goes
   `0.990 → 0.004` across the 375 ns boundary and the `bit=1` edge goes
   `0.997 → 0.001` across 750 ns — i.e. **both transitions are sharper
   than one 25 ns bin**. So the threshold itself is crisp; `SIG_NS` is
   modelling *phase-estimate* uncertainty, not analogue slew, and should
   be set from the residual phase error of whatever tracker supplies
   `phi` (≈7 ns median, ≈130 ns worst-case per capture for the interval
   tracker below). The larger values suggested for slots 0, 4, 5, 7
   reflect their higher measured error rates, not a measured slew.

### Per capture

The decoder never knows the payload, so calibration must run on
information that does not depend on bit values. There are three such
sources, in increasing strength:

**(a) Trigger anchor.** Capture starts at the frame's first rising edge,
so bit 0 starts at `t = 0` and `t(0,0) = rho ∈ (0, 2*tau]`. This fixes the
integer-bit ambiguity that the lattice fit below cannot resolve.

**(b) Frame span anchor.** The frame is exactly 192 bits and its trailer
ends `FF`, so the last falling edge of the frame is at
`191*1250 + 750 = 239500 ns`. Locate the last high sample `(i_end, s_end)`
and the first low sample after it; then

```
239500 ∈ ( t(i_end, s_end), t(next) )
```

Solving with `phi ≈ rho` gives `tau` to about ±0.3 % in one step. This is
the coarse scale estimate and it needs no header/trailer bit values at
all.

**(c) Rising-edge lattice — the strong one.** *Every* WS2812 bit starts
with a rising edge, whatever its value. So every observed low→high
transition brackets a point of the exact 1250 ns lattice:

```
for each rising edge between samples m-1 (low) and m (high):
      exists integer k:  k*1250 ∈ ( t[m-1], t[m] ]
```

Real captures contain **152–190 rising edges** (median ~180), roughly two
per loop. This is a data-independent phase reference denser than the
header/trailer.

Recommended estimator, measured against the oracle Viterbi phase
(`bm_probe.py`):

| estimator | median \|err\| | median of per-capture max |
|---|---|---|
| bracket **midpoint** + robust line fit | 67 ns | 246 ns |
| **interval constraints** (below) | **6.9 ns** | 129 ns |

Midpoints are biased because the brackets are wildly asymmetric (250 ns
gaps versus a 625 ns gap). Use the intervals:

```
function calibrate(samples, phase_hint):
    tau  <- from anchor (b); refine on a 0.05 ns grid
    L    <- ceil(240000 / (LOOP_CY * tau)) + 1
    base[m] = LOOP_CY*tau*i(m) + SPAN_K*tau*SLOT_CY[s(m)]     # phi-free part
    R    <- rising-edge brackets (lo=base[m-1], hi=base[m], loop=i(m))

    # coarse: one global phi0 minimising Huber distance of (mid+phi0) to the lattice
    phi0 <- argmin over phi on a 2 ns grid of
              sum over R of huber( dist((base_mid + phi) mod 1250, lattice), 300 )
    phi[i] <- phi0 for all i

    repeat 6 times:                     # interval propagation
        for i in 0 .. L-1:
            A, B <- empty
            for each bracket r in R with |loop(r) - i| <= 2:
                k <- round( (mid(r) + phi[i]) / 1250 )
                A.append( k*1250 - hi(r) )      # phi >= this
                B.append( k*1250 - lo(r) )      # phi <  this
            lo, hi <- max(A), min(B)
            phi_new[i] <- (lo+hi)/2  if lo <= hi
                          else median over r of (A[r]+B[r])/2   # infeasible -> centre
        phi <- phi_new

    # resolve the whole-bit ambiguity with the trigger anchor
    shift <- 1250 * round( (phi[0] - rho_expected) / 1250 )
    phi <- phi - shift
    # optional polish on the 64 known header/trailer bits
    (tau, phi) <- local search maximising agreement on bits 0..31 and 160..191
    return tau, phi
```

The `|loop - i| <= 2` window is what makes it a *track*, not a fit: the
loop-to-loop phase is not a straight line. Measured non-linearity of the
oracle phase against a best-fit line over 94 loops: **median 147 ns, max
378 ns**. A rigid two-parameter clock therefore mis-places samples by up
to ±378 ns — more than the width of a decision window. This is the
"clock stretching" artifact and it is why `phi` must be per loop.

How much loop-to-loop movement must the tracker allow? Constraining the
step `|phi[i+1] - phi[i]|` and re-solving (`bm_jitter.py`, sample
mismatch over 40 608 samples; the absolute level is optimistic because
this objective lets each loop reach for a wider phase range, but the
*relative* ordering is the point):

```
step limit   +-0     +-5    +-10   +-20   +-40   +-80  +-160  unbounded
mismatch    16.87%  8.60%  6.53%  4.97%  2.68%  1.05%  0.40%    0.30%
```

A rigid loop period (`+-0`) is off by an order of magnitude. **Allow at
least ±80 ns/loop** of phase movement in the tracker; below ±20 ns/loop
the model is structurally unable to follow the clock. Note also that one
loop's own 8 samples pin its phase only to a **median 235 ns wide**
interval (p10 5 ns, p90 255 ns) — the phase is identified by the
*sequence*, never by a single loop.

If a `clock_stretch` technique is present it should own `phi` and pass it
in as `phase_hint`; boundary_model then skips the coarse stage and only
runs the interval-propagation polish. If not, the procedure above stands
on its own.

### Relationship to `dev_calibration/fitted_model.json`

`approaches/dev_calibration/final.json` reports 99.47 % sample agreement,
but that is computed over **all 5118 samples**, of which 4355 are the
post-frame latch low. Re-scored on the frame region only it is **3.46 %
mismatch** (`bm_common` + the re-evaluation in this design's exploration).
Three of its parameters do not survive scrutiny:

* `G = 2525.89 ns` is not the physical loop period. Its data term
  `sum_j w[j] * Hc_j(i,s)` counts HIGH reads per slot before the sample,
  and `Hc_j(i,s) ≈ rho_j * i` is nearly collinear with `i` — so `w`
  silently re-parametrises the loop period. Its *effective* mean loop is
  ~2500 ns, which agrees with the direct measurement (2494.5–2513.1 ns).
  Verified independently: the frame's last high sample sits at loop 95 of
  640, and 192 × 1250 ns / 95.x loops forces G ≈ 2500, not 2526.
* `w = [0, -62.5, 0, 125, 0, 0, 0, 62.5]` implies a data-dependent loop
  length. Directly tested here and rejected (`dcy=+1` → 3.787 %,
  `dcy=0` → 1.172 %).
* `h1 = 737.25, h0 = 339.25` are absorbing that model error; the grid
  optimum for a correct geometry is exactly (750, 375).

Its geometry `[1, 5, 9, 14, 18, 22, 28, 32]` scores 2.295 % on the
clock-free objective versus 1.172 % here. **Recommendation: keep
`dev_calibration`'s per-capture `(t0, k)` seeding idea, replace its
geometry and drop its `w` term.**

---

## Envelope behavior

Let `eps` be the relative HSI frequency error; `tau = 62.5/(1+eps)`, and
every gap scales with `tau` while the decision window (375 ns wide, set by
the crystal-exact transmitter) does not. From `bm_env.py`, sweeping the
trigger phase `rho ∈ [0, 2*tau)`:

| eps | gap after slot 5 | gap after slot 7 | mean blind payload bits | worst |
|---|---|---|---|---|
| −8.0 % | 407.6 ns | 679.3 ns | 16.7 | 19 |
| **−7.5 %** | **405.4 ns** | **675.7 ns** | **16.4** | 17 |
| −5.0 % | 394.7 | 657.9 | 14.5 | 19 |
| −2.5 % | 384.6 | 641.0 | 12.7 | 15 |
| −1.0 % | 378.8 | 631.3 | 15.6 | 19 |
| −0.3 % (bench) | 376.1 | 626.9 | **0.8** | 5 |
| 0.0 % | 375.0 | 625.0 | **0.0** | 0 |
| +1.0 % | 371.3 | 618.8 | 18.3 | 20 |
| +2.5 % | 365.9 | 609.8 | 11.6 | 12 |
| +5.0 % | 357.1 | 595.2 | 11.2 | 12 |
| **+7.5 %** | **348.8** | **581.4** | **11.2** | 13 |

Three things to take from this.

**The bench point is a lucky resonance, not a typical one.** At `eps = 0`
the loop is `40 × 62.5 = 2500 ns` — exactly two bit periods — so the
sampling phase never crawls, and the trigger (`rho ∈ (0, 2*tau]`, at most
125 ns) locks it into a region where both per-loop bit positions are
covered. That is why the real captures show a median of **0** blind bits.
Move off resonance in *either* direction and the phase crawls out of the
lucky region: 11–18 blind payload bits, i.e. 9–14 % of the payload with
no local evidence at all. **A decoder tuned only on the bench data will
look far better than it is.**

**The slow corner is the hard one, but not because the count is worst.**
At `eps = −7.5 %` the slot7→slot0 gap grows to **676 ns**, which exceeds
T1L (500 ns) *and* T0H (375 ns) with room to spare, so both merged 1-bits
and swallowed 0-bits are guaranteed rather than occasional; and the
slot5→slot6 gap crosses 375 ns (405 ns) so it starts blinding bits too
(at the bench it contributes only 6 of 125). Blind-bit count is 16.4
versus 11.2 at the fast corner — but the qualitative difference is that at
the slow corner *two* gaps blind, so the blind bits are less regularly
spaced and the "never two in a row" property is no longer guaranteed. At
`eps = +7.5 %` gap 5→6 shrinks to 349 ns < 375 ns and can no longer blind
anything; only the end-of-loop gap does, and it is 7 % narrower.

**Blind-bit count is not monotone in eps.** `+1 %` (18.3) is worse than
`+7.5 %` (11.2). The driver is the crawl rate `G − 2500 ≈ −2500 × eps`
ns/loop against the ~250 ns wide blind band:

```
run length in loops  ~  250 / |2500 * eps|
   eps = -0.3 %  ->  ~33 loops   (matches the observed ~35-loop runs)
   eps = +-1 %   ->  ~10 loops
   eps = +-7.5 % ->  ~1.3 loops
```

Near resonance the sampler either misses the blind band entirely (0 blind
bits) or parks in it for tens of loops. Far from resonance it sweeps
through repeatedly, giving a steady 11–17 blind bits spread evenly over
the frame. **The decoder must not assume blind bits are rare *or* that
they are evenly spread; both regimes occur inside the envelope.**

Within-capture drift of ±0.2 % at the slow corner changes almost nothing
(mean blind 16.5–16.6, max 20 vs 17) — the technique's per-loop `phi`
track absorbs it by construction. `tau` may be held constant across the
capture; `phi` may not.

---

## Failure modes

Being blunt about where this technique alone loses bits.

1. **Blind bits are a hard information limit, not a weakness of the
   estimator.** When the decision window `[b*1250+375, b*1250+750)` lies
   entirely inside a dead zone, the samples before it are high for both
   bit values and the samples after it are low for both. There is nothing
   to recover locally. 1.81 % of payload bits at the bench, up to ~14 %
   across the envelope. This technique's contribution is to *identify*
   them exactly, not to decide them.

2. **No redundancy.** Two thirds of bits are decided by a single sample.
   A phase error of a few tens of ns near a window edge flips a bit with
   no second opinion. 2.37 % of payload bits already have two in-window
   samples that *disagree* (`CONFLICT`) at the bench — those are the
   symptom, and the ones with a single sample are the silent version of
   the same problem.

3. **Slot 7 is systematically marginal.** 8.2 % error rate on informative
   samples, one-sided (reads LOW where the model says HIGH), because in
   the trigger-locked phase regime it sits ~55 ns before the T1H edge. It
   supplies 23 % of all informative samples, so this alone accounts for
   ~54 % of the technique's decision errors. Down-weighting it (via
   `PERR[7]`) helps the soft path but throws away real evidence in the
   hard path.

4. **Phase tracking needs rising edges, and merged pulses remove them.**
   The lattice bootstrap relies on low→high transitions. A run of 1-bits
   whose 500 ns T1L falls in the 625 ns end-of-loop gap produces one long
   high with *no* rising edge for several bits. In the worst captures the
   interval tracker's error exceeds 60 ns on up to 64 of 94 loops, with a
   maximum of ~620 ns. Those are exactly the `ones`/`impulse_lo`/`runs`
   patterns, which have the fewest rising edges (151–157 versus ~187).
   **This technique is weakest precisely where `missed_zero` and the
   merge-aware techniques are needed most** — it must be paired, not
   trusted alone.

5. **The residual is not white.** Even with an oracle per-loop phase, 1.17 %
   of samples still disagree with the wire. The residual concentrates in
   slot 7 and in loops where the phase is in fast transition (slots 0 and
   4 becoming informative). A Gaussian-noise assumption in the LLR will
   be optimistic there; the per-slot `PERR` floor is what keeps it honest.

6. **The whole-bit ambiguity is only broken by the trigger.** The rising-edge
   lattice determines `phi` modulo 1250 ns. If the trigger assumption
   (`t(0,0) ∈ (0, 2*tau]`, sample (0,0) high) is violated — a glitch, a
   pre-frame edge — every bit index shifts by one and the payload is
   garbage while looking internally consistent. Guard with the
   header/trailer check; do not trust `phi` alone.

7. **Geometry is assumed rigid within a loop.** If the STM8 ever runs the
   sampler from Flash with different prefetch alignment (or an interrupt
   fires), `GAP_CY[7]` changes and the whole dead-zone map moves. Nothing
   in the per-capture calibration would catch a *constant* change; only
   the global refit would.

---

## Composition interface

### Pipeline position

**Stage 1 — the time base. Everything else consumes its output.**

```
  raw samples
      |
      v
  [boundary_model]  <---- optional phase_hint from clock_stretch
      |  t[], bit_of[], phase_of[], Z[], EDGE[], LLR[], BLIND[], CONFLICT[]
      +-------------------+--------------------+-------------------+
      v                   v                    v                   v
 [matched_filter]   [edge_dp]           [missed_zero]      [histogram_adaptive]
      |                   |                    |                   |
      +-------------------+--------------------+-------------------+
                          v
                    LLR combination -> per-bit decision -> frame check
```

It runs **before** any bit-decision stage because pulse widths, edge
positions, template correlations and run-length histograms are all
meaningless in `(iteration, slot)` coordinates. It should run **after**
(or jointly with) whatever estimates the per-loop phase; the two are
mutually recursive and two passes suffice: bootstrap `phi` from rising
edges, decode, then re-fit `phi` on the decided bits and decode again.

### Inputs it needs

* `samples: [(iteration, slot, level)]` and `meta` (nothing else is
  required — the global geometry constants are compiled in).
* **Optional** `phase_hint: phi[0..L-1]` from `clock_stretch`. If given,
  boundary_model skips the coarse lattice stage and only polishes.
* **Optional** `bit_posterior[0..191]` from a previous pass, for the
  second-pass phase refit (use only bits with `|LLR| > 3`).

### Outputs it provides

| output | shape | meaning |
|---|---|---|
| `t[m]` | per sample | absolute ns from the frame's first rising edge |
| `bit_of[m]`, `phase_of[m]` | per sample | bit cell index and in-bit phase |
| `Z[m] = (t[m], t[m+1])` | per gap | the dead zone; where an edge may hide |
| `LLR[b]` | 192 | log-odds for bit `b` = 1, clipped to ±6 |
| `EVID[b]` | 192 lists | the in-window samples backing bit `b` |
| `BLIND[b]` | 192 bools | **no** sample in `[375, 750)` — 0 information |
| `CONFLICT[b]` | 192 bools | ≥2 in-window samples that disagree |
| `MARGIN[b]` | 192 | ns from the best in-window sample to the nearer edge |
| `GAPOF[b]` | 192 | which inter-slot gap swallowed a blind bit's window |
| `EDGE[]` | list | bracket intervals for observed transitions |
| `tau`, `phi[]` | scalars/array | the fitted clock, for other stages to reuse |

### Constraints it can enforce on the other techniques

1. **Edge brackets are hard.** For a rising edge bracketed by `(t_a, t_b)`,
   some `k*1250` lies in that interval — for *any* bit value. For a
   falling edge, `k*1250 + hw` lies in it with `hw ∈ {375, 750}`; this is
   a two-way constraint that *links the bit value to the timing*, and an
   `edge_dp` search should use it as a transition-legality test rather
   than as a soft cost.
2. **Dead-zone widths bound what may be hidden.** A gap of width `w` can
   hide at most `floor(w / 1250) ` complete bits and at most one
   transition pair if `w < 1250`. At the bench `w ≤ 625 ns`, so **no
   whole bit can hide in any gap** — this kills a large class of
   hypotheses in any run-length or merge-repair search. At `eps = −7.5 %`
   the widest gap is 676 ns, still well under 1250, so the property holds
   across the whole envelope. `missed_zero` should use this to bound its
   insertion search to at most one swallowed pulse per gap.
3. **Blind bits are never adjacent** (measured max run = 1 at the bench;
   verify per capture from `BLIND[]` since the slow corner can break it).
   So a blind bit always has two decided neighbours — a byte-level or
   run-length prior over the neighbourhood is always applicable.
4. **`LLR[b] == 0` means "ask someone else", not "50/50 noise".** The
   downstream combiner should treat `BLIND[b]` as a *routing* signal:
   those bits must be decided by merge/pulse-width reasoning
   (`missed_zero`, `matched_filter`) or by frame-level structure, never
   by thresholding a near-zero LLR.
5. **Slot-7 down-weighting is exportable.** `PERR[s]` is a per-slot
   reliability that any technique reading raw levels can apply.

### How to combine the soft outputs

`LLR[b]` is additive log-odds and can simply be summed with the LLRs from
`matched_filter`, `missed_zero` and `histogram_adaptive` before the
decision. Two cautions: (a) do not double-count — if another technique
also reads the same in-window samples, it must not re-add the same
evidence; boundary_model's `EVID[b]` lists exactly which sample indices
it consumed. (b) `CONFLICT[b]` marks bits where boundary_model's own
evidence is internally inconsistent — halve its LLR there rather than
trusting the sum.

---

## Key numbers

Constants and measurements the implementer should reuse verbatim.

**Geometry (global, hardware)**

```
LOOP_CY  = 40 cycles                       (not the 37 in cap_code.s)
SLOT_CY  = [1, 5, 9, 13, 17, 21, 27, 31]
GAP_CY   = [4, 4, 4, 4, 4, 6, 4, 10]       (last wraps to next loop's slot 0)
SPAN_CY  = 30 (slot0 -> slot7); effective 30.2 +- 0.4 when tau = G/40
SPAN_K   = 1.006                           (intra-loop stretch, tau tied to G/40)
```

Gap widths in ns: `4 cy -> 250 (bench 251)`, `6 cy -> 375 (376)`,
`10 cy -> 625 (627)`.

**Clock (per capture)**

```
G (loop period)   min 2494.5   median 2498.4   max 2513.1 ns
tau = G/40        62.36 .. 62.83 ns   (f_cpu 15.92 .. 16.03 MHz)
eps               -0.5 % .. +0.2 %
crawl G - 2500    -5.5 .. +13.1 ns/loop
frame span        loops 0..95 of 640;  192 bits x 1250 = 240000 ns
last falling edge 239500 ns exactly (trailer ends FF)
DO NOT default to harness.LOOP_NS = 2507.3 (0.36 % above the median)
```

**Wire (exact, transmitter side)**

```
BIT_NS = 1250,  H0_NS = 375,  H1_NS = 750
decision window = [375, 750) ns after bit start; width 375 ns = 30 % of a bit
(h1, h0) grid optimum is exactly (750, 375) - no threshold correction
```

**Fit quality (mismatched samples, clock-free per-loop-phase objective,
40608 samples)**

```
documented geometry @ tau=62.5      3.566 %
this design's geometry @ tau=62.75  1.172 %
free real-valued 8-offset fit       1.172 %   (integer model loses nothing)
data-dependent loop (dcy = +-1)     3.787 % / 1.258 %   (rejected)
dev_calibration geometry @ 62.5     2.295 %
dev_calibration final.json, frame region only:  3.46 % mismatch
```

**Decision availability (54 captures x 128 payload bits = 6912)**

```
informative samples per bit:  0 -> 1.81 %   1 -> 65.2 %   2 -> 32.9 %   >2 -> 0
blind payload bits            125 (1.81 %), mean 2.3/capture
   0 blind in 36 captures; 7-9 blind in 18 (all with G >= 2508 ns)
blind cause: gap after slot 7  119/125     gap after slot 5  6/125
max run of consecutive blind bits: 1
conflicting in-window evidence: 164 bits (2.37 %)
per-slot informative fraction: [.041, .273, .634, .303, .030, .080, .674, .620]
per-slot error rate (informative samples):
   slot   0      1      2      3      4      5      6      7     all
   rate  36.9%  0.14%  1.37%  0.70%  18.8%  6.8%   0.81%  8.2%   3.52%
   n      214   1415   3287   1572    154    411   3478   3203  13734
```

**Phase tracking**

```
rising edges per capture           152 .. 190 (median ~180)
oracle phi non-linearity vs a line median 147 ns, max 378 ns over 94 loops
one loop's 8 samples pin its phase to a 235 ns interval (median; p90 255)
phase-step limit -> mismatch:      +-0: 16.87%   +-20: 4.97%
                                   +-40: 2.68%   +-80: 1.05%   free: 0.30%
blind track, bracket midpoints     median error 67 ns, per-capture max ~246 ns
blind track, interval constraints  median error 6.9 ns, per-capture max ~129 ns
worst case (few rising edges)      up to 620 ns on ones/impulse_lo/runs
```

**Envelope**

```
gap after slot 7:  625 ns @ 0 %,  676 ns @ -7.5 %,  581 ns @ +7.5 %
gap after slot 5:  375 ns @ 0 %,  405 ns @ -7.5 %,  349 ns @ +7.5 %
mean blind payload bits: 0.0 @ 0 %, 0.8 @ -0.3 %, 16.4 @ -7.5 %, 11.2 @ +7.5 %
   (non-monotone: 18.3 @ +1 %)
blind-run length ~ 250 / |2500 * eps| loops
   -0.3 % -> ~33 loops (matches the observed ~35-loop runs)
   +-7.5 % -> ~1.3 loops
+-0.2 % within-capture drift at the slow corner: no material change
no gap ever exceeds 1250 ns across the envelope -> no whole bit can hide
```
