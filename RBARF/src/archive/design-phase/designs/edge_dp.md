# edge_dp — technique design

Global maximum-likelihood alignment of the 192-bit frame to the raw
oversampled level stream, by dynamic programming over a
(bit index x phase residual x phase slope) trellis, with the header and
trailer pinned and the payload bits free. It is designed to be the
**final fusion stage**: every other technique's output enters as either a
per-bit log-prior, a per-sample weight, a hard constraint, or a
(kappa, phase) hypothesis, and edge_dp returns the MAP frame *plus
calibrated per-bit posteriors* that tell the caller exactly which bits it
could not resolve.

Exploration code, logs and the working prototype live in
`/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/dev_edge_dp/`
(`dp2.py` = Viterbi core, `bcjr.py` = forward-backward, `synth2.py` =
faithful envelope simulator, `d_*.py` = measurements, `*.log` = results).

---

## Target artifact & evidence

edge_dp does not target one artifact. It targets the *residual* left
after every local technique has done its best: **bits whose local
evidence is a near-tie**, and **phase/rate estimation coupled to the bit
decisions**. Three measurements define the problem.

### 1. The time base is already nearly exact — away from edges

Using the `dev_calibration` fitted model
`t = t0 + kappa * (i*G + o[slot] + Hc . w)` on the 54 real captures, and
restricting to the ~767 samples per capture that fall inside the 240 us
frame (`dev_edge_dp/d_cal.py`):

```
IN-FRAME agreement 39952/41411 = 0.9648      (median 26 bad samples / capture)
per-slot mismatch: slot0 6.09%  slot1 1.81%  slot2 1.97%  slot3 1.87%
                   slot4 1.93%  slot5 5.91%  slot6 1.98%  slot7 6.64%
```

And critically (`d_jit.py`), binning every in-frame sample by its
distance `x` to the nearest wire edge under the model:

```
x=   0- 25  n=3956  P(mismatch)=0.1757
x=  25- 50  n=3951  P(mismatch)=0.0990
x=  50- 75  n=3691  P(mismatch)=0.0826
x=  75-100  n=3363  P(mismatch)=0.0137
x= 100-125  n=3042  P(mismatch)=0.0056
x= 125-150  n=2683  P(mismatch)=0.0019
x>=150      n=15626 P(mismatch)=0.0000       <-- exactly zero, 15626 samples
```

So the model is *deterministically correct* more than 150 ns from an
edge, and all noise is a narrow band of edge-timing jitter. Fitting a
probit per slot to the falling edge (`d_edge.py`) gives the emission
widths edge_dp uses:

```
slot         0     1     2     3     4     5     6     7
sigma_fall  32    24    28    18   (6)    38    26    46   ns
delta_fall +76   +44   -12   -12   -12   +72    -4   -40   ns  (see Calibration)
pooled rise:  delta = -28 ns, sigma = 40 ns
pooled fall:  delta =  -4 ns, sigma = 44 ns
```

This is what makes a *soft* aligner worthwhile: a hard-threshold decoder
throws this structure away, while edge_dp turns "this sample is 30 ns
from a modelled edge" into 0.5 nats instead of 5 nats.

### 2. Bits are decided by one or two samples — often a near-tie

Per bit, only samples whose within-bit phase `u` lies in `[h0, h1)` =
`[339.25, 737.25)` discriminate '0' from '1' at all; everything outside
is predicted identically by both hypotheses. Measured on the real
captures (`d_bits.py`):

```
samples per bit window        : 2:29   3:3201  4:3940  5:3198
DISCRIMINATING samples per bit: 0:33   1:5691  2:4644      (of 10368 bits)
bits with ZERO discriminating sample: 33/10368 = 0.32%
   (all isolated -- longest run of consecutive zero-evidence bits = 1)
```

54.9% of all bits rest on a **single** sample. A per-bit soft decision
with the oracle time base and no coupling between bits
(`d_llr.py`, best emission width) already errs on

```
payload-region sign errors: 85 / 6912 = 1.23% of payload bits
captures whose 128 payload bits are all correct: 21/54
```

and the errors are weak — typical |LLR| at the error is 0.1..1.8 nats.
That is exactly the regime where a global model wins.

### 3. The residual is a *model* problem, not a *search* problem

The decisive measurement (`d_oracle.py`): for every capture the trellis
was run twice over the same (kappa, d, v) search — once with free payload
bits, once with all 192 bits pinned to ground truth — and the two path
costs compared.

```
EXACT 24/54;  of the 30 misses: SEARCH failures 0, MODEL failures 30
cost gap (true path - ML path): median +0.249 nats, max +2.729, min +0.010
```

Every failure is a case where the model genuinely scores the wrong frame
better, by a *quarter of a nat over an entire 192-bit frame*. The
Viterbi search itself never misses the true path. This is the core
justification for the composition design below: edge_dp does not need a
better search, it needs ~0.25–3 nats of external evidence, which is a
prior barely stronger than a coin flip.

Injecting a synthetic upstream hint of accuracy `acc` as a log-prior of
magnitude `lam` nats (`d_prior.py`, baseline emission = 24/54):

```
   acc    lam  EXACT   payload biterr
  ----   ----  -----   --------------
  0.00   0.00  24/54    0.00767      (no prior)
  0.80   0.25  36/54    0.00463
  0.90   1.00  40/54    0.00318
  0.95   1.00  45/54    0.00159
  0.98   1.00  46/54    0.00130
  1.00   2.00  54/54    0.00000
  0.80   4.00   4/54    0.02980      <-- over-confident prior is poison
```

### 4. What the technique itself achieves standalone

Prototype (`dp2.py`, per-slot widths + rise term, blind kappa, no
external evidence), 54 real captures:

```
edge_dp Viterbi      EXACT 30-32/54   payload bit error 0.46-0.48%
edge_dp BCJR (MAP)   EXACT 31/54      payload bit error 0.43%
   vs local per-bit soft decision (oracle time base)  21/54, 1.23%
```

and on the faithful simulator at a clock offset where no bit is
information-dead (eps = +1.0%): **54/54 exact, 0 bit errors** — the
aligner is optimal when the information is present (see Envelope).

---

## Algorithm

### Notation

```
M                  number of samples (5118)
(i_m, s_m, y_m)    iteration, slot, level of sample m (harness.linearize order)
NBITS = 192        frame bits: 32 header + 128 payload + 32 trailer
BIT   = 1250.0     ns, exact
h1, h0             effective high widths of a '1' / '0' bit, ns
G, o[0..7], w[0..7]  calibrated loop period, slot offsets, data-dependent terms
```

### Stage 0 — data-dependent sample coordinate `A`

```
Hc = zeros(8)                       # running count of HIGH reads per slot
for m in 0..M-1:                    # chronological
    A[m] = i_m * G + o[s_m] + dot(Hc, w)
    Hc[s_m] += y_m
```

`A[m]` is a pure function of the observed data (no unknowns). The true
sample time is `t[m] = phi + kappa * A[m]` with exactly two unknown
scalars. `w` captures the STM8 `BTJT` NOP-skip: a HIGH read changes the
loop length, so the time base is data-dependent but causal.

### Stage 1 — endpoint constraint -> blind kappa

The frame's first rising edge is at wire time 0 and, because the trailer
ends in `0xFF`, its last falling edge is at
`T_END = 191*BIT + h1 = 239487.25 ns`. Both are visible in the raw
levels (the line idles low outside the frame):

```
m0 = first index with y=1;  m1 = last index with y=1
a0 = (m0 == 0) ? A[0] : (A[m0-1] + A[m0]) / 2
a1 = (m1+1 < M) ? (A[m1] + A[m1+1]) / 2 : A[m1]
kappa0 = T_END / (a1 - a0)
d0_hat = -kappa0 * a0                    # phase seed (see sign convention)
```

Measured accuracy of `kappa0` (`d_kap.py`): bias **+0.15 % to +0.22 %**,
|error| <= **0.31 %** — *and that holds unchanged across the whole
+/-7.5 % envelope*, because it is a ratio of two quantities that scale
together. One endpoint measurement therefore replaces any wide frequency
search.

### Stage 2 — kappa grid

```
KGRID = { kappa0 * (1 + delta) : delta in arange(D_LO_K, D_HI_K, D_STEP_K) }
D_LO_K = -0.006, D_HI_K = +0.003, D_STEP_K = 2.5e-4      # 37 hypotheses
```

Spacing rationale: a residual rate error `dk` accumulates
`dk * 240000 ns` of phase over the frame; at `2.5e-4` that is 60 ns,
well inside the phase-residual grid, and the slope state absorbs the
rest.

### Stage 3 — emission tensor

Phase-residual grid `dgrid = arange(D_LO, D_HI, D_STEP)` (the sign
convention is `t_wire[m] = kappa*A[m] - d`, so `d ~ -phi`).

For each `di`, each sample `m` with
`j = floor((kappa*A[m] - dgrid[di]) / BIT)` in `[0, 192)` and
`u = kappa*A[m] - dgrid[di] - j*BIT`:

```
p_high(u, b, s) = FLOOR + (1 - 2*FLOOR)
                  * sigm((u - DR) / SR)                 # rising edge
                  * sigm((h_b - u) / WE[s])             # falling edge
E[b][j][di] += -( y_m*log p_high + (1-y_m)*log(1-p_high) )
```

Notes:
* the rising-edge factor is identical for `b = 0` and `b = 1`, so it does
  not change the bit LLR — it sharpens the **phase** estimate. Measured
  gain on real captures: 24 -> 29/54 exact.
* `WE[s]` per-slot (from the probit fit) is the single biggest emission
  win measured: 24 -> 31/54 exact, bit error 0.767% -> 0.521%.
* optional hard pruning: if the caller supplies it, set
  `E[b][j][di] = +INF` whenever a sample sits more than `X_HARD = 150 ns`
  from every edge of hypothesis `b` and disagrees with it. This is
  supported by P(mismatch) = 0 over 15626 such samples, and it prunes the
  lattice aggressively. Use it only with `FLOOR = 0` semantics in mind:
  it is a hard constraint and a single mis-calibrated slot can make a
  capture infeasible, so fall back to the soft path if all states die.

### Stage 4 — Viterbi over the (d, v) lattice

State: `(d, v)` where `d` is the phase residual of the bit boundary and
`v` the per-bit phase increment (residual rate). `v` is quantised to a
multiple of `D_STEP` so the transition is a pure array shift.

```
vgrid  = arange(-V_MAX, V_MAX, V_STEP)          # ns per bit
vshift = round(vgrid / D_STEP)                  # integer index shifts

cost[d][v] = 0.5 * ((dgrid[d] - d0_hat)/D0_SIG)^2       # initial phase prior

for j in 0..191:
    # ---- bit decision at this stage ----
    if j < 32:                b = HEADER_BITS[j]      ; e = E[b][j]
    elif j >= 160:            b = TRAILER_BITS[j-160] ; e = E[b][j]
    else:
        e0 = E[0][j] + PRIOR[j][0]      # external log-priors, 0 if none
        e1 = E[1][j] + PRIOR[j][1]
        bhat = (e1 < e0);  e = min(e0, e1)
    # ---- transition: d' = d + v ; v' in {v-1, v, v+1} ----
    for vi in 0..NV-1:
        best[.][vi] = min over dv in {-1,0,+1} of
                      shift(cost[.][vi+dv], vshift[vi]) + (dv != 0 ? V_PEN : 0)
    cost = best + e[:, None]
    store backpointers (d_prev index, v_prev index, bhat)

backtrack from argmin(cost) -> bits[0..191], phase track d(j)
```

The per-bit `min(e0, e1)` inside the stage is exact: bit `j` influences
no other stage (each WS2812 bit's waveform is entirely contained in its
own 1250 ns window, since every bit begins with a rise and ends low), so
the bit variable can be maximised locally *given the phase state*. This
is what keeps the trellis 2-D instead of 3-D.

### Stage 5 — pick / marginalise over kappa

Viterbi mode: keep the `kappa` with the lowest total cost.
Soft mode (recommended for fusion): run the forward–backward recursion
(`bcjr.py`) instead — replace `min` with `log-sum-exp` throughout — and
combine hypotheses by their evidence `logZ(kappa)`:

```
p1[j] = sum_kappa softmax(logZ)[kappa] * sigm(LLR_kappa[j])
LLR_out[j] = log(p1[j] / (1 - p1[j]))
```

### Stage 6 — outputs

MAP bits, payload bytes, `LLR_out[0..191]`, the low-confidence set
`{ j : |LLR_out[j]| < TAU }`, a ranked candidate list obtained by
enumerating that set, the chosen `kappa_hat`, and the phase track `d(j)`.

### Tractability

```
N_D = (D_HI - D_LO)/D_STEP + 1 = 145      (D_LO=-900, D_HI=+900, D_STEP=12.5)
N_V = 2*V_MAX/V_STEP + 1 = 9              (V_MAX=25, V_STEP=6.25)
states/stage  = 1305 ;  predecessors/state = 3  ->  3915 edges/stage
edges/frame   = 751,680 per kappa hypothesis
emission build = N_D * M_inframe * 2 ~ 145 * 770 * 2 = 223,300 evaluations
```

Measured (numpy, one core): **23–28 ms per (capture, kappa)** for
Viterbi, ~2x for BCJR. With 25–37 kappa hypotheses that is **0.6–1.2 s
per capture** (Viterbi) / ~2 s (BCJR). Everything is vectorised over the
`d` axis; the only Python loops are over 192 stages and 9 `v` values.

If that is too slow for the combined decoder:
* **Coarse-to-fine kappa**: run a 5-point coarse grid at `D_STEP = 25 ns`,
  then a 5-point fine grid around the winner. ~4x cheaper.
* **Beam**: prune states whose cost exceeds the stage minimum by
  `BEAM = 15` nats. (Recommended value, *not* measured — the observed
  frame-level margins are <3 nats, so 15 nats is generous, but the
  implementer should verify it changes no decision before enabling it.)
* Dropping the slope state entirely (`V_MAX = 0`, which freezes the phase
  residual for the whole frame) costs 1 frame in 54 at the bench, is 5x
  faster, and — measured — costs *nothing* under the modelled within-
  capture drift. See Envelope: on this data the slope state is not
  earning its keep, and the implementer should treat it as optional
  robustness rather than a required component.

---

## Calibration

Two tiers: **global** (fitted once, offline, shipped as constants) and
**per capture** (estimated inside `decode`).

### Global — fitted offline, reused verbatim

| Parameter | Source | Value used |
|---|---|---|
| `G` (nominal loop, ns) | `approaches/dev_calibration/fitted_model.json` (currently `final.json`) | 2525.8936 |
| `o[0..7]` (slot offsets, ns) | same | 61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0, 1727.0, 2000.0 |
| `w[0..7]` (data-dependent, ns per prior HIGH at that slot) | same | 0, -62.5, 0, +125, 0, 0, 0, +62.5 |
| `h1`, `h0` (effective high widths, ns) | same | 737.25, 339.25 |
| `WE[0..7]` (per-slot fall probit width, ns) | `dev_edge_dp/d_edge.py` | 32, 24, 28, 18, 12, 38, 26, 46 |
| `SR`, `DR` (rise width / offset, ns) | `d_edge.py` pooled | 40, -28 |
| `FLOOR` | `sweep.py` (flat 0.002..0.05, all within 2 frames) | 0.01 |
| `V_PEN` (nats per slope change) | `sweep2/3.py` (0.5/1.2/3 within 2 frames) | 1.2 |
| `D0_SIG` (ns) | phase seed slack | 1000 |

`edge_dp` **must not re-fit** `o[]`. I tried: taking the per-slot
`delta_fall` residuals above at face value and folding them into `o[]`
(`d_ocorr.py`) *lowers* in-frame agreement 0.9648 -> 0.9567 over four
iterations, because those per-slot deltas trade off against the
per-capture `(t0, kappa)` refit rather than representing real offset
error. They are genuine *emission* asymmetries, not timing offsets —
which is exactly how the design uses them (as `WE[s]`, not as `o[s]`).
Likewise, shifting `h1`/`h0` by a global `hoff` was tested and hurts
(`+25 ns` -> 18/54; `-12.5 ns` -> 28/54 vs 24/54 baseline; keep 0 with
the per-slot widths in place: `hoff = 0` scored best in `sweep3.py`).

If the calibration effort ships a revised `fitted_model.json`, only
`G, o, w, h1, h0` change; `WE`, `SR`, `DR` should be re-estimated by
re-running `d_edge.py` against the new model (2 minutes) because they are
residuals *of* that model.

### Per capture — inside `decode`

1. `kappa0` from the endpoint constraint (Stage 1). No ground truth, no
   iteration; bias +0.15..0.22 %, spread <= 0.31 % across +/-7.5 %.
2. `d0_hat = -kappa0 * a0`, used only as a soft Gaussian prior with
   `D0_SIG = 1000` ns — the trellis re-estimates the phase itself.
3. `kappa_hat`: argmin over `KGRID` of the Viterbi cost (or the
   evidence-weighted mean over `logZ` in soft mode).
4. `d(j)`: the phase track, an output of the DP, not a fitted parameter.

### Guard rails the implementer should assert

* `|d(j) - d0_hat| < 0.8 * (D_HI - D_LO)/2` for all `j`. If the track
  reaches the grid edge, `kappa` is wrong — widen `KGRID` and re-run.
  (This is a real failure I hit: with a mis-derived `kappa0` the phase
  walked 894 ns across the frame and clipped, dropping the score to
  3/54.)
* The 32 pinned header bits and 32 pinned trailer bits must be feasible:
  if the best path's header-stage costs exceed ~3 nats/bit the capture is
  probably not a frame — return `None`.

---

## Envelope behavior

Evaluated with `dev_edge_dp/synth2.py`, a simulator that reproduces the
*calibrated* sampler including the data-dependent term (unlike
`recon/synth.py`, which uses a uniform 40-cycle loop and no feedback).
Validation against real captures: high-run-length histograms match
closely (`ones` real `{1:21,2:52,3:45,5:2,6:35}` vs synth
`{1:22,2:50,3:48,4:1,5:1,6:34}`), and the information metric below at
eps ~ 0 reproduces the real captures to within 0.03 bits/frame.

### The binding constraint is information, not alignment

Count, per frame, the payload bits with **zero** samples in the
discriminating window `[h0, h1)` — bits no aligner can ever recover
(`d_dead.py`, 18 patterns x 7 start phases):

```
   eps    mean  median  p90  max   frac of captures with 0 dead bits
 -0.080  10.89     11    14   14        0.000
 -0.075  11.29     11    13   13        0.000
 -0.050   9.43      9    11   14        0.000
 -0.025   5.17      5     7    8        0.000
 -0.010   1.52      2     3    4        0.206
 +0.000   0.47      0     2    2        0.714
 +0.010   0.00      0     0    0        1.000
 +0.025  10.18      2    32   37        0.357
 +0.050  35.52     34    64   64        0.167
 +0.075  52.71     63    64   64        0.000
  REAL    0.50      0     2    3        0.667     <-- 54 real captures
```

edge_dp's end-to-end result tracks that table closely
(`env.log`, 18 patterns x 3 phases per point):

```
   eps   dead%   EXACT     payload biterr   0.5*dead (coin-flip floor)
 -0.080   8.02    5/54       0.0339            0.0401
 -0.075   8.94    3/54       0.0444            0.0447
 -0.050   7.54    7/54       0.0272            0.0377
 -0.025   4.05    1/54       0.0240            0.0203
 -0.010   0.95   22/54       0.0069            0.0048
 +0.000   0.41   36/54       0.0039            0.0021
 +0.010   0.00   54/54       0.0000            0.0000
 +0.025   7.83   26/54       0.0635            0.0392
 +0.050  27.56   12/54       0.1709            0.1378
 +0.075  41.00    2/54       0.1797            0.2050
 +0.080  44.47    3/54       0.2027            0.2224
```

Across the slow half of the envelope the observed bit error sits within a
factor ~1.8 of `0.5 x dead-fraction`, i.e. edge_dp gets essentially every
bit that carries information and coin-flips the rest. At eps = +1.0 %,
where the dead fraction is exactly zero, it is **perfect: 54/54 exact,
zero bit errors**. That is the strongest available statement about the
aligner — it is not the bottleneck anywhere in the envelope. (The excess
over the floor at eps in [-0.01, +0.05] is real and is the same marginal
model failure seen at the bench, amplified: those points have few dead
bits but many single-sample bits.)

### Slow corner (-7.5 %) analysis

* Sample spacing scales by 1.081. The end-of-loop gap
  `G - o[7] + o[0] = 587.8 ns` becomes **635 ns**, comfortably wider than
  the 398 ns discriminating window `[339.25, 737.25)` and wider than
  `T1L = BIT - h1 = 512.75 ns` — so both swallowed zeros and merged ones
  are guaranteed, as HSI_TEMPERATURE.md predicts. Mean largest
  inter-sample gap measured: 650 ns at eps=0 -> **703 ns** at -7.5 %.
* Consequence for edge_dp specifically: nothing breaks. `kappa0` is still
  accurate to 0.3 %, the phase track stays bounded, the header/trailer
  pins still fit. What is lost is 11.3 payload bits per frame of
  *evidence*. Exact-frame rate collapses to ~3-7/54 purely from that.
* The dead bits stay **isolated** (longest run of consecutive
  zero-evidence bits = 1 at every eps tested, both on real captures and
  across the envelope). This is the good news for composition: an
  isolated unknown bit inside an otherwise-correct byte is precisely what
  a byte-level or payload-structure prior can adjudicate.

### Fast corner (+7.5 %)

Two regimes, and which one is real depends on whether the fitted `w`
vector is physically true:

* With the fitted `w = [0,-62.5,0,125,0,0,0,62.5]`, the data-dependent
  feedback drives the sampler into a **period-2 phase-lock attractor**:
  the within-bit sample phase histogram develops a hole exactly over
  `[375, 750)` and 64 of 128 payload bits (every other bit) go dead. The
  same feedback is what makes the *bench* point unusually good (0.5 dead
  bits vs 7-9 for a feedback-free sampler) — so the bench point is a
  lucky resonance, not typical behaviour.
* With `w = 0` or with the mechanistic `w = -62.5` on every slot (one
  cycle saved per HIGH read), the dead fraction is a flat 4-9 % across
  the whole envelope with no lock-up:

```
  eps      w_fit      w_zero     w_mech        (% payload bits dead)
 -0.075     8.87       8.75      11.99
  0.000     0.37       9.22       7.07
 +0.010     0.00       0.00       7.15
 +0.075    41.06       6.09       4.13
```

  The real captures (0.32 % dead) match `w_fit` at the bench point and
  rule out `w_zero`/`w_mech` *there*, but nothing in the dataset
  constrains `w` away from the bench point. **The combined decoder should
  treat the +5 %/+7.5 % catastrophe as a credible risk, not a certainty,
  and should not be tuned around it.**

### Within-capture drift (+/-0.2 % ramp) — the slope state is *not* needed

I expected the `v` (slope) state to be justified here. It is not, and the
honest answer is quantitative (`d_drift.log`):

```
                              eps      EXACT   biterr
base (no drift, slope on)    +0.000    36/54   0.00391
drift +0.2 %, slope on       +0.000    34/54   0.00391
drift +0.2 %, slope OFF      +0.000    34/54   0.00391   (5x faster)
```

Reason: HSI_TEMPERATURE.md's +/-0.2 % wander is specified across the
whole 1.6 ms capture, but the frame occupies only its first ~96 of 640
loops. The rate change *within the frame* is therefore
`0.002 * 96/640 = 3.0e-4`, producing about `0.5 * 3e-4 * 240 us ~ 36 ns`
of phase curvature over the entire frame — barely three `D_STEP` cells,
and already absorbed by the `kappa` grid plus the phase-residual random
walk. The slope state costs 5x runtime for no measured gain. Keep it
only if the combined decoder must tolerate wander an order of magnitude
faster than the datasheet implies.

Ablations at the bench (`d_abl.log`, 54 real captures):

```
full (slope on, pins on)                 30/54   0.00477
no header/trailer pin                    30/54   0.00463
no slope state (V_MAX = 0)               29/54   0.00521   13 s vs 63 s
stiff phase (V_PEN = inf)                29/54   0.00521
free phase per bit (V_PEN = 0)           31/54   0.00637
```

The pin ablation was also run at the slow corner: eps = -7.5 % gives
3/54 and 0.0444 bit error **both with and without** the header/trailer
pins. The pins are structurally right — they are what makes the endpoint
constraint and the frame-span identity meaningful — but on this dataset
they are not what produces bits.

### UART caveat

HSI_TEMPERATURE.md notes the 9600-baud debug UART breaks beyond ~+/-4.5 %.
edge_dp needs nothing from the UART, but if the firmware ever
user-trims HSI from the WS2812 signal, `kappa_hat` from Stage 5 is
exactly the trim measurement: relative error <= 0.31 % blind, and better
than 0.05 % after the DP refines it — well inside the -2/+3.25 %
CLK_HSITRIMR residual.

---

## Failure modes

**1. Information-dead bits — the dominant failure, and unfixable here.**
0.32 % of bits at the bench (0.5 per frame), 4-9 % across the envelope.
No sample discriminates the hypotheses, so the emission LLR is exactly 0
and the DP falls back on the prior (a coin flip without one). edge_dp
*reports* these correctly (see Composition) but cannot resolve them.

**2. Marginal model failures.** All 30 bench-point misses are cases where
the model prefers the wrong frame by a median of 0.25 nats over the whole
frame (`d_oracle.log`). Any small error in `o[]`, `w[]`, `h1/h0` or the
per-slot widths can flip such a bit. These are also the cases most easily
rescued by a weak prior — which is the entire fusion argument, but it is
worth being blunt: **edge_dp alone is 30-32/54 on real captures, and its
last few frames are not defensible on modelling grounds.**

**3. Over-confident external priors are actively harmful.** An 80 %-
accurate prior at 4 nats collapses the decoder to 4/54 (worse than no
prior at 24/54). The fusion layer MUST feed calibrated LLRs and clip
`|PRIOR|` to ~2 nats unless the source is provably near-certain.

**4. Dependence on a global calibration it cannot repair.** edge_dp
assumes `G, o, w, h1, h0` are right. Its `(d, v)` state absorbs slow
phase/rate error but nothing per-sample: if `w` is wrong, every HIGH read
injects a 62.5-125 ns step that appears as emission noise, not as
trackable phase. If a future calibration changes `w`, re-derive `WE[s]`.

**5. Phase-grid clipping.** If `kappa0` is wrong by more than ~0.4 % the
phase walks off `[D_LO, D_HI]` and the decode collapses (measured: 3/54
with a mis-derived `kappa0`). Mitigated by the guard rail above, but it
is a silent failure without it.

**6. Header/trailer pinning buys nothing measurable.** The ablation
(`d_abl.log`) shows identical results with the pins removed at eps ~ 0
(30/54 both) *and* at eps = -7.5 % (3/54 both). Those bits are already
unambiguous, or already dead. The pins are insurance against gross
misalignment and the anchor for the endpoint constraint, not a source of
bits — do not count on them for margin.

**6b. The slope state likewise buys nothing measurable** (29 vs 30 of 54
at the bench; identical under the modelled +/-0.2 % drift) while costing
5x runtime. I designed it in expecting it to matter; it does not, at the
drift rate the datasheet implies. Reported as measured, not as designed.

**7. No payload-level structure.** edge_dp enforces the header, the
trailer and the exact 192-bit span; it knows nothing about byte
boundaries, CRCs or payload plausibility. A single flipped bit corrupts
exactly one byte and the frame fails exact-match. Every remaining frame
at the bench is a one- to three-bit miss.

**8. Cost.** 0.6-2 s per capture in numpy, 20-100x a threshold decoder.
Acceptable offline; not a firmware algorithm.

**9. Not evaluated: beam pruning.** The recommended `BEAM = 15` nats is
inferred from the margin structure, not measured. The prototype runs the
full lattice.

---

## Composition interface

edge_dp is the **terminal stage**. Everything upstream should emit soft
evidence rather than decisions; edge_dp is the only place where the hard
`bytes` decision is made.

### Inputs

| Input | Required | Shape / meaning | Who provides it |
|---|---|---|---|
| `samples` | yes | `[(it, slot, level)]` from `harness.linearize` | harness |
| `G, o[8], w[8], h1, h0` | yes | global time model | **calibration** |
| `WE[8], SR, DR, FLOOR` | yes | emission shape (constants above) | this design |
| `PRIOR[192][2]` | no | per-bit additive **log-cost**, i.e. `-log P(bit=b)`; 0 = no opinion; clip to 2.0 nats | matched_filter, histogram_adaptive, missed_zero, boundary_model |
| `SAMPLE_W[M]` | no | per-sample weight in `[0,1]` multiplying that sample's emission term; 0 = ignore this sample | any technique that can flag a sample as corrupted (e.g. a byte-boundary sample it distrusts) |
| `KGRID` | no | explicit `kappa` hypotheses; replaces Stage 2 | clock_stretch |
| `FORCE[j]` | no | hard bit constraints (implemented as `PRIOR = INF` on the other value) | any technique with a certainty |
| `DEADZONE` | no | intervals of wire time in which a missing pulse must not be penalised | missed_zero, boundary_model |

`SAMPLE_W` and `DEADZONE` both enter Stage 3 and require no change to the
trellis. `PRIOR` enters Stage 4 at the free-bit stages. This is the
whole integration surface: **three hooks, all additive, all inside the
emission/stage cost.**

### Outputs

| Output | Value measured at the bench |
|---|---|
| `payload: bytes` (MAP) | 30-32/54 exact standalone |
| `llr[192]` (BCJR posterior log-odds) | see reliability below |
| `low_conf` = bit indices with `abs(llr[j]) < TAU` | mean **2.07** bits/frame at `TAU=1`, median 1, max 11; 20/54 captures have none |
| `candidates` (enumerate `low_conf`, rank by path cost) | median list size **2**, p90 **32** at `TAU=1` |
| `kappa_hat`, `d(j)` phase track | a refined time base other techniques can re-run against |
| `logZ` / total path cost | comparable score for arbitrating between candidates or between whole decoders |

**The posterior is the product worth composing on.** Measured over all
6912 payload bits of the 54 real captures (`d_post.py`):

```
  0.0 <= |LLR| < 0.5   n=  56   error rate 0.4286
  0.5 <= |LLR| < 1.0   n=  56   error rate 0.1071
  1.0 <= |LLR| < 2.0   n= 191   error rate 0.0000
  2.0 <= |LLR| < 4.0   n=1004   error rate 0.0000
  4.0 <= |LLR| < 8.0   n=5381   error rate 0.0000
  8.0 <= |LLR|         n= 224   error rate 0.0000

  |LLR| >= 1 : coverage 98.4 %, 0 errors in 6803 bits
```

and at `TAU = 1` the low-confidence set contains **every** error in
**54/54** captures. edge_dp therefore never fails silently: it hands the
fusion layer a 2-bit-wide uncertainty on average, with a guarantee (on
this dataset) that the truth is inside the enumerated list.

### Pipeline position and the two-pass protocol

```
  raw samples
      |
      +--> [calibration]  -> G, o, w, h1, h0                     (offline)
      |
  pass 1: edge_dp (no priors)  -> kappa_hat, d(j), llr, low_conf
      |
      +--> matched_filter / histogram_adaptive / missed_zero /
           boundary_model / clock_stretch, all re-run **on the
           edge_dp time base** (kappa_hat + d(j)) instead of their
           own estimates -> per-bit LLRs, sample weights, dead zones
      |
  pass 2: edge_dp (with PRIOR, SAMPLE_W, DEADZONE)
      |
      +--> MAP payload + candidate list + posterior
```

This is a two-round turbo schedule. The justification for round 2 is the
margin measurement: the gap between the true frame and the ML frame is
0.25-2.7 nats, and the sensitivity table shows a 95 %-accurate 1-nat
prior moves 24/54 -> 45/54, a 98 %-accurate one -> 46/54. Upstream
techniques do not need to be right; they need to be *calibrated and
slightly better than chance on the marginal bits*.

### Concrete asks of the other five techniques

* **matched_filter** — per-bit LLR from correlating each bit window
  against the two template waveforms. This is the most natural direct
  `PRIOR` source; its LLRs should be temperature-scaled so that its own
  reliability curve matches edge_dp's (fit one scalar on the train split).
* **missed_zero** — instead of *deciding* that a zero was swallowed,
  emit the dead-zone interval and a prior favouring '0' on the affected
  bit. edge_dp's zero-evidence bits (0.32 % at bench, 4-9 % across the
  envelope) are exactly its target set, and they are always isolated.
* **boundary_model** — per-sample confidence: down-weight slots 0, 5 and
  7, whose in-frame mismatch rate is ~3x the others (6.1/5.9/6.6 % vs
  1.8-2.0 %). Feed as `SAMPLE_W`, or supply a better `w[]` to the
  calibration.
* **clock_stretch** — supply `KGRID` (and, if it models within-capture
  wander, an initial `v` track). It replaces Stage 2 and can shrink the
  runtime 25-37x if it pins `kappa` tightly.
* **histogram_adaptive** — a cheap independent `PRIOR`, and a
  disagreement flag: where its hard decision differs from edge_dp's MAP
  *and* `|llr| < 1`, that bit belongs in the candidate enumeration.

### Constraints edge_dp can enforce for the ensemble

* exactly 192 bits between the first rise and the last fall (endpoint);
* header `FF 00 AA 65` and trailer `9A 55 00 FF` exactly;
* a monotone, slowly-varying phase track (no bit may be skipped or
  duplicated — the classic insertion/deletion failure of edge-counting
  decoders is structurally impossible here);
* one consistent `(kappa, phase)` for the whole frame, so a candidate
  payload that requires an inconsistent time base is rejected by
  construction.

Any other technique that produces a full 16-byte candidate can be scored
by edge_dp: pin all 192 bits and read off the path cost. That gives the
fusion layer a single common likelihood scale on which to compare
candidate payloads from different decoders — the same machinery used for
`d_oracle.py`.

---

## Key numbers

Constants and measurements the implementer should reuse verbatim.

### Signal / frame

```
BIT_NS            1250.0        exact
h1 (eff. T1H)      737.25       fitted, use instead of the 700/750 nominal
h0 (eff. T0H)      339.25       fitted, use instead of the 350/375 nominal
T1L = BIT - h1     512.75
T0L = BIT - h0     910.75
discriminating window   [339.25, 737.25)  width 398 ns  (31.8 % of a bit)
T_END = 191*BIT + h1  239487.25 ns   (last falling edge; trailer ends 0xFF)
NBITS 192 = 32 header + 128 payload + 32 trailer
HEADER FF 00 AA 65    TRAILER 9A 55 00 FF   (MSB first)
```

### Sampler time model (global calibration)

```
G           2525.8936 ns
o[0..7]     61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0, 1727.0, 2000.0
inter-slot gaps  249.8, 268.8, 278.9, 265.5, 263.2, 339.0, 273.0
end-of-loop gap (slot7 -> next slot0)   587.8 ns   <-- the dead zone
w[0..7]     0, -62.5, 0, +125, 0, 0, 0, +62.5   (ns per prior HIGH at that slot)
in-frame samples per capture   ~767
in-frame model agreement       0.9648 (median 26 bad samples of 767)
```

### Emission model

```
WE[0..7]  32, 24, 28, 18, 12, 38, 26, 46     ns  (per-slot fall probit width)
SR, DR    40, -28                            ns  (pooled rise width, offset)
FLOOR     0.01
pooled fall probit: delta = -4 ns, sigma = 44 ns
P(sample disagrees with the model | distance to nearest edge):
   0-25 ns 0.176 | 25-50 0.099 | 50-75 0.083 | 75-100 0.014
   100-125 0.006 | 125-150 0.002 | >=150 ns  0.0000  (15626 samples)
per-slot in-frame mismatch: 6.09, 1.81, 1.97, 1.87, 1.93, 5.91, 1.98, 6.64 %
```

### Trellis

```
D_LO, D_HI, D_STEP    -900, +900, 12.5 ns    -> N_D = 145
V_MAX, V_STEP          25, 6.25 ns/bit       -> N_V = 9
V_PEN                  1.2 nats per slope change
D0_SIG                 1000 ns
KGRID                  kappa0 * (1 + delta), delta in [-0.006, +0.003] step 2.5e-4
X_HARD                 150 ns   (optional hard-constraint radius)
TAU                    1.0 nat  (low-confidence threshold)
cost: 751,680 edges + 223,300 emission evals per (capture, kappa);
      23-28 ms measured, 0.6-1.2 s per capture over the full kappa grid
```

### Blind per-capture estimator

```
kappa0 = T_END / (a1 - a0)
   bias      +0.15 % .. +0.22 %
   |error|   <= 0.31 %   -- unchanged across the entire +/-7.5 % envelope
```

### Observability (real captures, 54 x 192 bits)

```
samples per bit window          2: 0.3 %   3: 30.9 %   4: 38.0 %   5: 30.8 %
discriminating samples per bit  0: 0.32 %  1: 54.9 %   2: 44.8 %
zero-evidence bits              33 / 10368, ALL isolated (max run = 1)
dead payload bits per frame     mean 0.50, median 0, max 3
```

### Scores (54 real captures, payload exact-match)

```
local per-bit soft decision, oracle time base     21/54    1.23 % bit error
edge_dp Viterbi, flat emission                    24/54    0.77 %
edge_dp Viterbi, + rise term                      29/54    0.62 %
edge_dp Viterbi, + per-slot WE                    31/54    0.52 %
edge_dp Viterbi, + both                        30-32/54    0.46-0.48 %
edge_dp BCJR (MAP bits)                           31/54    0.43 %
   (the emission-ablation ladder 24->29->31->32 was run with an earlier,
    off-by-inversion kappa0 and an asymmetric relative kappa grid; it is
    internally consistent because the DP picks kappa by likelihood. The
    same best config with the corrected kappa0 of Stage 1 and a symmetric
    grid scores 30/54 at 0.48 %. Treat 30-32/54 as one number.)
edge_dp + 95 %-accurate 1-nat prior               45/54    0.16 %
edge_dp + 98 %-accurate 1-nat prior               46/54    0.13 %
edge_dp + exact 2-nat prior                       54/54    0.00 %
search vs model: 0 search failures, 30 model failures;
                 cost gap true-vs-ML median +0.25 nats, max +2.73
```

### Envelope (faithful simulator, 18 patterns x 3 phases)

```
   eps    dead%   EXACT    biterr
 -0.080    8.02    5/54    0.0339
 -0.075    8.94    3/54    0.0444
 -0.050    7.54    7/54    0.0272
 -0.025    4.05    1/54    0.0240
 -0.010    0.95   22/54    0.0069
  0.000    0.41   36/54    0.0039
 +0.010    0.00   54/54    0.0000
 +0.025    7.83   26/54    0.0635
 +0.050   27.56   12/54    0.1709
 +0.075   41.00    2/54    0.1797
 +0.080   44.47    3/54    0.2027
```

The `+0.025 .. +0.080` rows are dominated by the data-dependent
phase-lock attractor of the fitted `w` and should be read as a risk
scenario, not a prediction (see Envelope / Fast corner).

### Ablations (54 real captures)

```
full                                   30/54   0.00477    63 s
no header/trailer pin                  30/54   0.00463    63 s
no slope state (V_MAX = 0)             29/54   0.00521    13 s
stiff phase (V_PEN = inf)              29/54   0.00521    61 s
free phase per bit (V_PEN = 0)         31/54   0.00637   115 s
```
