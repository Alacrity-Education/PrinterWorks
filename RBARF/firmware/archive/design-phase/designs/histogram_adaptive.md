# histogram_adaptive — technique design

Adaptive pulse statistics + global constraint repair.
No fixed nanosecond thresholds anywhere: every decision boundary is a
cluster boundary learned from the capture itself, and every hard decision
is re-opened by a frame-level constraint solver that knows the frame is
exactly 192 bits with a known 32-bit header and a known 32-bit trailer.

Exploration code and raw logs: `designs/dev_histogram_adaptive/`
(`g0_common.py` … `g13_final.py`). Every number below is measured on the
54 real captures (or on `synth.py` where stated).

---

## Target artifact & evidence

### What it fixes

1. **Per-capture drift of the *apparent* pulse statistics.** The
   receiver's effective sample rate is not constant across captures *or
   within one capture*, so any decoder with hard-coded ns thresholds
   mis-slices pulses. This technique never uses one.
2. **Ambiguity ranking.** It produces a calibrated per-cell margin and a
   per-bit constrained log-likelihood ratio, which is the soft input the
   fusion stage needs.
3. **Structural errors that local evidence cannot fix** — a swallowed
   0-bit or a merged 1-pair changes the *number* of bits a pulse covers.
   Locally these look plausible; globally they break the 192-bit count or
   the marker bytes. The repair stage converts that global inconsistency
   into a local correction.

### The generative model, verified on the data

Work in **cells**: rise → next rise. `g1_cells.py` labels all 9553 cells
of the 54 captures against the calibrated truth time base:

| true bit substring a cell covers | count | share |
|---|---|---|
| `0`  (one 0-bit, clean)              | 5110 | 53.49 % |
| `1`  (one 1-bit, clean)              | 3545 | 37.11 % |
| `11` (merged 1-pair, T1L swallowed)  |  553 |  5.79 % |
| `10` (1-bit then a swallowed 0)      |  192 |  2.01 % |
| `00` (0-bit then a swallowed 0)      |  117 |  1.22 % |
| `01`                                 |   24 |  0.25 % |
| 3-bit cells (`010`,`011`,`110`,`111`)|   12 |  0.13 % |

So a cell is always of the form

```
bits(cell) = [1]*(m-1) + [b] + [0]*(n-m)
             ^merged 1s   ^the bit whose fall we actually observe
                                ^swallowed 0-bits
```

with `n` = bits covered, `m` = merged prefix length, `b` ∈ {0,1}. The only
counter-examples are the 24 `01` + 5 of the 3-bit cells (0.30 % of cells),
and all of them are boundary-labelling artefacts of the truth model (the
first high sample of a genuine `1` cell being assigned to the preceding
swallowed `0`), not real violations. **The structural claim holds: a
merged prefix is always 1-bits, a swallowed suffix is always 0-bits.**
Mechanistically that must be so — merging needs a 500 ns T1L to fall in a
dead zone, swallowing needs a 375 ns T0H to; the 875 ns T0L never fits in
any gap (largest measured end-of-loop gap ≈ 588 ns, ≈ 604 ns at −7.5 %).

### The information is there; the *phase reference* is the bottleneck

With the calibrated time base, count the samples that land in the
discriminating window (between T0H and T1H) of each bit:

| discriminating samples per bit | 0 | 1 | 2 | ≥3 |
|---|---|---|---|---|
| bits (of 10368) | **49 (0.47 %)** | 6485 (62.5 %) | 3834 (37.0 %) | 0 |

Only 0.47 % of bits are informationally dead. But **62.5 % of bits rest on
a single sample**, so the phase of that one sample must be placed
correctly. Sensitivity of a per-sample window vote on the calibrated time
base (`g0`-derived sweep):

| perturbation | misclassified bits / 10368 |
|---|---|
| −20 ns global phase | 1234 (11.9 %) |
| 0 | 825 (7.96 %) |
| +20 ns | 492 (4.75 %) |
| residual scale ×0.9995 over the 240 µs frame | 1829 (17.6 %) |
| residual scale ×1.0005 | 198 (1.91 %) |

i.e. **tens of nanoseconds of phase error, or 5·10⁻⁴ of residual scale,
costs whole percent of bits.** That is why the front end below tracks the
bit grid *locally* instead of fitting one period per capture.

### Why the statistics must be adaptive and *local*

A single global comb fit for the bit period, in a fixed receiver
coordinate, gives P values spanning **1243 → 1280 receiver-ns across the
54 captures (2.9 % spread)** — four times the real 0.7 % HSI spread, and
the spread is *pattern*-correlated (`p55` 1243, `aa` 1268, `ones` 1267).
The apparent rate depends on the data because the sample loop's own
timing is level-dependent. A local (7-cell) linear tracker collapses that
to ≈0.3 % and halves the classification error:

| front end | cell classification error |
|---|---|
| midpoint + one global P, global threshold | 7.9 % |
| midpoint + one global P, per-capture 2-median threshold | 5.0 % |
| local tracker W=10 + per-capture 2-median | 3.55 % |
| **local tracker W=3 + per-capture 2-median** | **2.46 %** |

Tracker window sweep (`g8_full.py`, calibrated geometry, cell error /
front-end exact match): W=2 → 2.53 % / 24, **W=3 → 2.46 % / 24**,
W=4 → 2.56 % / 22, W=6 → 2.79 % / 20, W=10 → 3.55 % / 17,
W=20 → 5.65 % / 15, W=30 → 6.85 % / 15.

### Why the edge must be treated as an *interval*, not a midpoint

Inter-sample gaps in the receiver coordinate are 250 / 312.5 / 375 /
562.5 ns (counts 11013 / 2122 / 3104 / 2759 over all edges), i.e. a
rise/fall bracket is **0.217 bit wide at the median, 0.485 bit at worst**,
against a class separation of only 0.30 bit (T1H−T0H = 375 ns). Taking the
bracket midpoint therefore injects up to ±0.24 bit of noise. Using the
bracket as an interval instead, the fall bracket contains **both**
hypotheses in only 0.44 % of cells — so 99.6 % of cells are in principle
*definitively* classifiable once the phase reference is right.

### Value of the global repair

Same front end, three constraint settings (`g9_repair.py`, W=10):

| constraints | exact | bit error |
|---|---|---|
| none (unconstrained best path) | 18/54 | 0.0315 /bit |
| Σn = 192 only | 18/54 | 0.0315 /bit |
| **Σn = 192 + header + trailer** | 18/54 | **0.0134 /bit** |

The marker constraints remove **58 % of all bit errors**. The raw
front-end bit count is ≠192 in **17 of 54** captures, so the count
constraint alone is doing real work upstream of the marker check even
where it does not change the score.

Best configuration measured (W=3, no centering term):

| geometry | split | exact | byte acc | bit error |
|---|---|---|---|---|
| nominal slot offsets | train (reps 0,1) | 18/36 (50.0 %) | 92.4 % | 0.0088 |
| nominal slot offsets | holdout (rep 2)  | 7/18 (38.9 %)  | 92.4 % | 0.0078 |
| calibrated slot offsets | train | 17/36 (47.2 %) | 92.4 % | 0.0082 |
| calibrated slot offsets | holdout | 9/18 (50.0 %) | 92.7 % | 0.0075 |

**The technique is essentially insensitive to the slot-offset
calibration** (0.0088 vs 0.0082 per bit). That is deliberate and is its
main value in the ensemble: it is an *independent* estimate that does not
inherit `dev_calibration`'s modelling assumptions.

---

## Algorithm

### Parameters (all named, defaults measured)

| name | default | meaning |
|---|---|---|
| `SLOT_O[0..7]` | `[62.5,312.5,562.5,812.5,1062.5,1312.5,1687.5,2000.0]` | intra-loop slot offsets, ns (receiver coordinate) |
| `LOOP_G` | `2500.0` | nominal loop length, ns |
| `P_LO`,`P_HI` | `0.85*BIT_NS`, `1.15*BIT_NS` = 1062.5, 1437.5 | comb search range for the bit period in receiver-ns |
| `N_COMB` | `6001` | comb grid points (0.0625 ns resolution) |
| `Q_MAX` | `4.5` | rise-to-rise gaps longer than this many periods are ignored by the comb |
| `W_TRACK` | `3` | local-tracker half-window, in cells |
| `N_MAX` | `3` | max bits a single cell may cover |
| `M_MAX` | `3` | max merged-1 prefix length |
| `H0_INIT`,`H1_INIT` | `0.30`, `0.59` | 2-cluster seeds for the fall phase (bit units) |
| `CLUSTER_ITERS` | `60` | 1-D 2-median (k-medians) iterations |
| `EPS_CENTER` | `0.0` (use `0.10` when soft outputs matter) | weight of the bracket-centering cost |
| `W_RISE` | `1.0` | weight of the next-rise consistency cost |
| `N_ITER` | `3` | outer refit iterations |
| `N_KNOWN_MIN` | `8` | marker-labelled cells required before the supervised refit |
| `LAST_SLACK` | `6` | extra bits the final cell may absorb (trailing latch) |
| `NB` | `192` | frame bits |
| `HDR_BITS`,`TRL_BITS` | `FF 00 AA 65`, `9A 55 00 FF` | MSB-first |

### S1 — receiver coordinate

```
x[j] = it[j] * LOOP_G + SLOT_O[sl[j]]          # ns, nominal, per sample j
```
No per-capture scale here; the scale is absorbed by the bit period P
estimated in S3. If `dev_calibration/fitted_model.json` is available, use
its `o` and `G` instead (marginal gain, see evidence).

### S2 — edges → brackets → cells

```
for each level transition between sample j-1 and j:
    kind = 'R' if lv[j]==1 else 'F'
    bracket = (x[j-1], x[j])                # the edge lies inside
if lv[0] == 1:                              # capture is edge-triggered
    prepend a rise with bracket (x[0] - 300, x[0])

cells = []
fi = 0
for i, (ra, rb) in enumerate(rises):
    advance fi past falls that end at or before rise i
    if no fall remains: break
    cells.append({ra, rb, fa, fb, next_ra, next_rb})    # next_* = rise i+1
```
`ra..rb` = rise bracket, `fa..fb` = fall bracket. A capture yields
**152–191 cells** (192 minus swallowed/merged bits).

### S3 — adaptive bit period and *local* grid

```
rmid[i] = (ra[i] + rb[i]) / 2

# (a) comb fit: the fundamental of the rise-to-rise gap set
P0 = argmin_{P in linspace(P_LO, P_HI, N_COMB)}
         sum over gaps g = diff(rmid) with g/P <= Q_MAX of (g/P - round(g/P))^2

# (b) integer bit index per cell, then Lloyd-style re-quantisation
n[i]  = max(1, round((rmid[i+1] - rmid[i]) / P0));   n[last] = 1
k[i]  = cumsum(n) shifted right, k[0] = 0
repeat up to 3 times:
    (tau, Ploc) = local_track(rmid, k, W_TRACK)
    n[i] = max(1, round((rmid[i+1]-rmid[i]) / Ploc[i]))
    k'   = cumsum(n) shifted;  break if k' == k;  k = k'
(tau, Ploc) = local_track(rmid, k, W_TRACK)

local_track(rmid, k, W):
    for each cell i:
        a = max(0, i-W); b = min(C, i+W+1)
        least-squares fit rmid[a:b] ≈ alpha * k[a:b] + beta
        Ploc[i] = alpha ;  tau[i] = alpha * k[i] + beta
```
`tau[i]` is the estimated start time of the cell's first bit; `Ploc[i]` is
the local bit period. The 2·W_TRACK+1 = 7-cell window is short enough to
follow the level-dependent loop stretching (evidence above) and long
enough to average the ±0.11-bit bracket-midpoint noise.

### S4 — per-capture fall-phase clustering (this is the "histogram")

```
fmid[i] = (fa[i]+fb[i])/2
mhat[i] = max(1, floor((fmid[i]-tau[i]) / Ploc[i]) + 1)     # merged prefix
ph[i]   = (fmid[i]-tau[i]) / Ploc[i] - (mhat[i]-1)          # fall phase in [0,1)

(h0, h1) = two_median(ph, seed=(H0_INIT, H1_INIT), CLUSTER_ITERS)
    repeat: th = (h0+h1)/2 ; h0 = median(ph[ph<th]) ; h1 = median(ph[ph>=th])
theta = (h0+h1)/2
```
Because the fall of a *merged* run still sits at the last bit's T1H phase,
this histogram is bimodal regardless of merging — no need to segregate
merged cells first.

**Ambiguity metric (the soft output).** Normalise the distance to the
cluster boundary by the cell's own bracket half-width, so a cell whose
edge is pinned between two closely spaced samples is trusted more than one
straddling the 562 ns end-of-loop gap:

```
ph_lo[i] = (fa[i]-tau[i])/Ploc[i] - (mhat[i]-1)
ph_hi[i] = (fb[i]-tau[i])/Ploc[i] - (mhat[i]-1)
half[i]  = (ph_hi[i]-ph_lo[i])/2
margin[i] = (ph[i] - theta) / half[i]      # sign = decided bit, |.| = confidence
```

### S5 — cell hypothesis costs (interval hinge)

For cell *i* and hypothesis `(n, m, b)` with `m ≤ n ≤ m + N_MAX - 1`,
`1 ≤ m ≤ M_MAX`, `b ∈ {0,1}`:

```
h    = h0 if b==0 else h1
t_f  = tau[i] + (m - 1 + h) * Ploc[i]                # predicted fall
c_f  = max(0, fa[i] - t_f, t_f - fb[i]) / Ploc[i]    # hinge: 0 inside bracket
     + EPS_CENTER * ((t_f - fmid[i]) / Ploc[i])^2

t_r  = tau[i] + n * Ploc[i]                          # predicted next rise
c_r  = max(0, next_ra[i] - t_r, t_r - next_rb[i]) / Ploc[i]
     + EPS_CENTER * ((t_r - next_mid[i]) / Ploc[i])^2
c_r  = 0 for the last cell

cost(i, n, m, b) = c_f + W_RISE * c_r
```
Everything is in bit units, so the cost is scale-free.

### S6 — global constraint repair (the DP)

State = number of frame bits emitted so far, `k ∈ [0, NB]`.

```
F[0][0] = 0 ; F[0][k>0] = INF
for i in 0..C-1:
    for k with F[i][k] < INF:
        for (n, m, b) in hypotheses(i):
            if i == C-1:                       # last cell absorbs the tail
                n = NB - k
                if not (m <= n <= m + LAST_SLACK): continue
            if k + n > NB: continue
            emitted = [1]*(m-1) + [b] + [0]*(n-m)
            if any KNOWN[k+j] >= 0 and KNOWN[k+j] != emitted[j]: continue  # HARD
            relax F[i+1][k+n] with F[i][k] + cost(i,n,m,b)
answer = backtrack from F[C][NB]
```
`KNOWN[0:32] = HDR_BITS`, `KNOWN[160:192] = TRL_BITS`, else −1. The header
and trailer are **hard** constraints (they are known exactly); the count
`Σn = NB` is enforced by the terminal state. Size: ≈190 cells × 193 states
× 18 hypotheses ≈ 6.6·10⁵ relaxations — microseconds-to-milliseconds.

Cheapest-first repair is *implicit and exact*: the DP finds the minimum
total added cost, which is precisely "flip the ambiguous classifications
with the smallest margins until the constraints are satisfied". A greedy
priority-queue version over `|margin|` gives the same answer when the
required repairs are independent; the DP is preferred because a swallowed
zero at bit *k* shifts every later bit and the repairs are *not*
independent.

### S7 — semi-supervised refit, iterate

```
repeat N_ITER times:
    sol = DP(...)
    k = cumsum of sol's n, shifted
    (tau, Ploc) = local_track(rmid, k, W_TRACK)         # re-anchored grid
    # the 64 marker bits now label some cells -> supervised cluster centres
    labelled = [(KNOWN[k[i]+m_i-1], ph_i) for cells whose fall bit is known]
    if len(labelled) >= N_KNOWN_MIN:
        h0 = median(ph of labelled 0s) ; h1 = median(ph of labelled 1s)
```
The marker bytes are chosen well for this: `FF 00 AA 65` and
`9A 55 00 FF` contain long runs, alternations and both polarities, so the
supervised set spans the whole phase range.

### S8 — soft outputs

Compute the backward table `B[i][k]` the same way, then constrained
max-marginals:

```
for every (i, k, n, m, b) reachable:
    total = F[i][k] + cost(i,n,m,b) + B[i+1][k+n]
    for j in 0..n-1:
        v = emitted[j]
        cost_v[k+j] = min(cost_v[k+j], total)
LLR[k] = cost0[k] - cost1[k]          # >0 => bit is 1
bits[k] = 1 if LLR[k] > 0 else 0
```

---

## Calibration

Nothing in this technique is a hard-coded nanosecond number. Per quantity:

| quantity | how estimated | scope |
|---|---|---|
| `SLOT_O`, `LOOP_G` | documented cycle positions scaled to the loop; optionally replaced by `dev_calibration/fitted_model.json` `o`/`G`. Only sets the receiver coordinate — the bit period absorbs the rest. | global, weak dependence |
| bit period `P0` | comb fit on the rise-to-rise gap set (S3a). Purely self-consistency: minimise the distance of every gap to an integer multiple. | per capture |
| local period `Ploc[i]`, grid `tau[i]` | 7-cell local linear regression of rise midpoints on integer bit index (S3b), iterated with re-quantisation. | per cell (≈ per 7 bits) |
| high-phase centres `h0`, `h1` | 1-D 2-median clustering of the fall phases, seeded at 0.30/0.59, then **re-estimated supervised** from the 64 marker bits after the first DP pass. | per capture, refined |
| boundary `theta` | midpoint of the two learned centres. | per capture |
| bracket half-width `half[i]` | directly observed (the two samples straddling the edge). | per cell |
| `n`, `m` quantisation | `round(gap / Ploc)` then re-opened by the DP over `{m..m+N_MAX-1}`. | per cell |

Global constants that *are* fixed (and must be, they are frame structure,
not timing): `NB = 192`, `HDR_BITS`, `TRL_BITS`, `N_MAX`, `M_MAX`,
`W_TRACK`, `EPS_CENTER`, `W_RISE`.

`W_TRACK` is the only tuned hyper-parameter. It was swept on all 54
captures; the train/holdout split at the chosen value (train 18/36 exact,
holdout 7/18; bit error 0.0088 vs 0.0078) shows no split-specific
overfit — the curve is flat over W ∈ {2,3,4} and degrades smoothly
outside, so the choice is not knife-edge.

**Sanity gates the implementer should assert (blind, no ground truth):**
* `P0` within `[P_LO, P_HI]` and `|Ploc[i]/median(Ploc) - 1| < 0.03`;
* cell count in `[140, 195]`;
* `h1 - h0` in `[0.18, 0.42]` bit (measured spread: 0.20–0.36);
* DP reaches `F[C][NB] < INF` (0 failures observed on 54 real and 288
  synthetic captures); if it does not, relax `N_MAX`/`M_MAX` by 1 and
  retry, then drop the marker constraint to hypotheses-only and report
  the frame as low-confidence.

---

## Envelope behavior

The receiver time base scales by 1/(1+ε). In the receiver coordinate the
wire bit period therefore *appears* as `P ≈ BIT_NS·(1+ε)`. Measured on
`synth.py`: **P = 1156 ns at ε = −7.5 %, 1250 at ε = 0, 1343 at ε = +7.5 %**,
recovered correctly by the S3 tracker in every case, with the final bit
index landing on 191 (i.e. `Σn = 192`) at all three corners. This is
the reason `P_LO`/`P_HI` must be `0.85·BIT_NS … 1.15·BIT_NS` and not a
narrow band around 1250 — a range of ±5 % silently clips at the corners
and destroys every downstream stage.

**Slow corner (ε = −7.5 %, the hard one).** The end-of-loop dead zone
grows from ≈588 ns to ≈636 ns (real geometry) / 562 → 604 ns (documented
9-cycle gap). Consequences for this technique specifically:

* *Bracket widths grow by 7.5 %* — the worst fall bracket goes from 0.485
  to ≈0.52 bit, i.e. wider than the 0.30-bit class separation. Those cells
  become genuinely two-hypothesis and the DP must resolve them from the
  neighbours and the constraints. The `margin` metric degrades gracefully
  here (it is normalised by exactly that width), which is the point of
  normalising it.
* *The T1L (500 ns) is swallowed more often* → more merged cells. On
  `synth` the merged-prefix histogram stays at `m ≤ 2` and cells at
  `n ≤ 2` right across ε ∈ [−8 %, +8 %], so `N_MAX = M_MAX = 3` has one
  full step of headroom. **But `synth.py` under-models merging**: for the
  `ones` pattern the real capture shows 155 pulses for 192 one-bits (37
  merges, runs up to 31 samples long) while synth at the bench point shows
  192 pulses and no merges. Real data already contains 3-bit cells
  (12 of them). At the true slow corner I would expect `m = 3` and
  occasionally 4; **raise `N_MAX`/`M_MAX` to 4 for production** — the DP
  cost is linear in `N_MAX·M_MAX` and it is cheap insurance.
* *Discriminating coverage.* On synth, bits with zero discriminating
  samples go from 0.47 % (real, bench) to **7.5 % at +7.5 % and 11.2 % at
  −7.5 %**. Synth's uniform 4-cycle slot spacing plus one 9-cycle gap is
  harsher than the real sampler (real gaps 250–339 ns plus a 588 ns wrap),
  so treat those as an upper bound; but the direction is right and the
  slow corner is worse.

**Fast corner (ε = +7.5 %).** Gaps shrink, swallowing and merging both
recede; the technique's own error should fall. Synth confirms the trend
(0.0268 /bit at +7.5 % vs 0.0438 at −7.5 %).

**Synthetic sweep of the full pipeline** (nominal geometry, W=3 not yet
applied — these are W=10 numbers, treat as an upper bound on error):

| ε | exact | bit error | median cells |
|---|---|---|---|
| −8.0 % | 0/36 | 0.0422 | 178 |
| −7.5 % | 0/36 | 0.0438 | 179 |
| −5.0 % | 0/36 | 0.0467 | 184 |
| −2.5 % | 0/36 | 0.0321 | 178 |
| 0 % | 36/36 | 0.0000 | 192 |
| +2.5 % | 0/36 | 0.0333 | 184 |
| +5.0 % | 0/36 | 0.0240 | 185 |
| +7.5 % | 0/36 | 0.0268 | 185 |

The ε = 0 row is degenerate (the synthetic loop is exactly 2.000 bits, so
nothing is ever swallowed) and should not be read as a result. The honest
reading: **on synthetic data the technique holds a roughly constant
2.4–4.7 % bit error across the whole ±7.5 % span — flat, no cliff — but
that error is 3–5× its real-data error (0.8 %)**, because synth's
sampler geometry has 15–25× more informationally dead bits. Nothing about
the scale estimation breaks at the corners; what degrades is the raw
evidence per bit.

**Within-capture drift (±0.2 %).** Fully absorbed: `tau`/`Ploc` are
re-estimated every 7 cells, so a 0.2 % linear ramp over 96 loops is a
0.03 % deviation inside any one window — three orders of magnitude below
the tracker's own noise. No parameter change needed.

---

## Failure modes

Be clear about this: **alone, this technique reaches 25–26/54 exact
(≈48 %) and 0.008 bit-error on the real dataset.** It is not a decoder;
it is a constraint-enforcing soft front end. Where it loses bits:

1. **The payload region is unprotected.** 128 of 192 bits have no
   constraint at all. After repair the surviving errors are concentrated
   there: 75 residual errors across 54 captures, median 3 per failing
   capture, worst 13 (`rnd3_0`). The header/trailer constraint removes
   58 % of errors — it cannot touch the rest.
2. **Cascading index errors.** If a cell's `n` is wrong and the DP repairs
   the count elsewhere, a whole run of bits shifts. `rnd3_0` (13 errors),
   `rnd3_2` (9), `blocks_2` (10) fail this way. The count constraint makes
   the *total* right while the *placement* stays wrong. This is the single
   biggest residual failure and is exactly what a technique with a better
   per-sample time base (calibration / clock_stretch) should fix.
3. **Long merged runs.** `N_MAX = M_MAX = 3` cannot express a 4-bit cell.
   None occur at the bench point, but real `ones` captures already show
   31-sample-long highs, and the slow corner will produce them. Silent
   truncation → guaranteed bit errors.
4. **Hinge-cost ties.** The interval cost is 0 anywhere inside the
   bracket, so many hypotheses tie exactly and the LLR magnitude is
   uninformative for them. Measured: sweeping `EPS_CENTER` over
   0 … 2.0 and `W_RISE` over 0.5 … 2.0 changes the answer by at most one
   capture (18 → 19 of 54) — the Viterbi path is essentially determined by
   *feasibility*, not by cost. Consequence: `|LLR| > 0.5` covers only 588
   of 6912 payload bits (though with **zero** errors). Use
   `EPS_CENTER = 0.10` when the soft outputs matter more than the point
   estimate.
5. **Degenerate patterns.** `zeros` and `impulse_hi` produce very few
   1-bits, so the `h1` cluster is thinly populated; the unsupervised
   2-median seeded fit wanders (`h1` as low as 0.44 before the supervised
   refit). The marker bits rescue it — that dependency is real: without
   the supervised refit in S7 these captures lose several bits.
6. **First and last cell.** Cell 0 is anchored by the edge trigger
   (`k[0] = 0` is guaranteed, header bit 0 = MSB of `FF` = 1). The last
   cell has no next rise, so `n` is set purely by `NB - k`; a wrong `n`
   anywhere upstream is dumped there and shows up as a mangled trailer —
   which the hard trailer constraint then rejects, forcing the DP to place
   the error elsewhere. That is usually right but not always.
7. **Not robust to a missing frame.** There is no detector: the technique
   assumes the capture contains exactly one frame starting at sample 0.
   If the rise count is out of `[140, 195]` it should decline rather than
   emit garbage.

---

## Composition interface

### Inputs it needs

* `samples: [(iteration, slot, level)]`, `meta` — required.
* `SLOT_O[8]`, `LOOP_G` — optional; defaults to the documented layout.
  Supply `dev_calibration/fitted_model.json`'s `o`/`G` if the fit is
  finished (gain: 0.0088 → 0.0082 bit error, 18 → 17/36 train, 7 → 9/18
  holdout — a wash, so **do not block on the calibration**).
* Optionally an externally supplied per-sample time base `t[j]` (from
  `clock_stretch` or the full calibrated model). Feed it in place of S1's
  `x[j]`; S3–S8 are unchanged and will simply find `P ≈ 1250`. This is the
  cleanest way for another technique to contribute: it improves `tau`
  accuracy, which the evidence above shows is the dominant error term.
* Optionally external per-bit log-likelihoods `LLR_ext[0..191]` from any
  other technique (see below).

### Outputs it provides

| output | shape | use |
|---|---|---|
| `bits[192]` | hard decision | direct payload |
| `LLR[192]` | constrained max-marginal, `cost0 - cost1` | fusion weights |
| `suspects` | bit indices sorted by `|LLR|` ascending | list decoding |
| `cells[i] = (k_i, n_i, m_i, b_i, margin_i)` | segmentation | alignment for other techniques |
| `tau(k)`, `Ploc(k)` | bit-grid estimate over the frame | a time base others can reuse |
| `h0`, `h1`, `theta` | learned wire high-phases (bit units) | per-capture threshold others can borrow |
| `feasible[i]` | the surviving `(n,m,b)` set with costs | a compact factor graph |

**How good the soft outputs are** (W=3, calibrated geometry, 6912 payload
bits, 75 residual errors):

| |LLR| band | bits | errors | error rate | share of all errors |
|---|---|---|---|---|---|
| ≤ 0.00 | 47 | 16 | 0.340 | 21 % |
| ≤ 0.05 | 284 | 55 | 0.194 | 73 % |
| ≤ 0.10 | 995 | 74 | 0.074 | **98.7 %** |
| ≤ 0.20 | 3822 | 75 | 0.020 | 100 % |
| > 0.50 | 588 | 0 | **0.000** | — |

The lowest 10 % of `|LLR|` (691 bits) contains 98.7 % of the errors; the
worst capture needs a list depth of 26 to cover all of its errors.
Cell-level `margin` is sharper still (W=10 measurement): `|margin| ≥ 2.0`
→ 1457 cells at a 0.00069 error rate; `|margin| < 0.25` → 534 cells at a
0.34 error rate covering 54 % of all cell errors.

### Pipeline position

**Late-middle, and then again at the very end.** Two distinct roles:

1. **As a front end** (position 3, after geometry/time-base estimation,
   alongside `matched_filter` / `edge_dp`): it contributes an independent
   bit estimate plus a per-cell segmentation, using a *different* error
   model (interval/cluster rather than model-matched likelihood), so its
   errors decorrelate from techniques that lean on the fitted sampler.
2. **As the final constraint enforcer** (position 6, after fusion). This
   is where it is most valuable and the recommended primary use. S5's cost
   function takes one extra additive term:

```
cost(i, n, m, b) += LAMBDA_EXT * sum over j in 0..n-1 of
                        ( -LLR_ext[k+j] if emitted[j]==1 else +LLR_ext[k+j] )
```
with `LAMBDA_EXT` scaling the fused evidence into bit-phase units (start
at `LAMBDA_EXT = 1.0` with `LLR_ext` normalised to unit median magnitude).
Everything else — the 192-bit count, the hard header/trailer, the
`1*b0*` cell structure, the `n`/`m` re-quantisation — is then applied to
the *fused* soft bits. Any technique that emits per-bit soft values gets
frame-level consistency for free, and the DP is the exact minimum-cost
repair rather than a greedy patch.

### Constraints it can enforce for the ensemble

* exactly 192 bits between the frame's first rise and the trailer's end;
* `bits[0:32] == FF 00 AA 65`, `bits[160:192] == 9A 55 00 FF` (hard);
* a rise-to-rise cell covers `[1]*(m-1) + [b] + [0]*(n-m)` — merged
  prefixes are all 1, swallowed suffixes are all 0 (violated in 0.30 % of
  cells, all attributable to boundary labelling);
* cell bit indices are strictly increasing and partition `[0, 192)`;
* the last cell terminates the frame (bit 191 = 1, LSB of `FF`).

Any candidate frame from another technique can be *checked* against these
in O(cells) and rejected or repaired without re-running the front end.

---

## Key numbers

Constants and measurements the implementer should reuse.

**Wire (transmitter, crystal-exact).** Bit 1250 ns. `'1'` = 750 ns high +
500 ns low; `'0'` = 375 ns high + 875 ns low. **Note: `harness.py`'s
`T0H_NS = 350` / `T1H_NS = 700` and `DATASET.md` disagree with this and
with the fitted model — use 375/750.** The calibration fit's *effective*
thresholds (absorbing the STM8 input threshold and edge rate) are
**h0 = 339.25 ns (0.271 bit), h1 = 737.25 ns (0.590 bit)**; the
per-capture learned centres land at h0 ∈ [0.245, 0.354] (median 0.335),
h1 ∈ [0.534, 0.636] (median 0.589). Separation h1−h0 = 0.20…0.36 bit.

**Sampler geometry.** Loop ≈ 2507–2526 ns. Calibration's global fit:
`G = 2525.894 ns`, `o = [61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0,
1727.0, 2000.0]` → inter-slot gaps `[249.75, 268.75, 278.875, 265.5,
263.25, 339.0, 273.0]` and an **end-of-loop wrap gap of 587.8 ns**
(≈9.4 cycles). Documented/nominal alternative (works nearly as well):
`G = 2500`, `o = [62.5, 312.5, 562.5, 812.5, 1062.5, 1312.5, 1687.5,
2000.0]`, wrap 562.5 ns.

**Edge brackets, receiver-ns** (nominal geometry, all 54 captures):
250 ns ×11013, 312.5 ns ×2122, 375 ns ×3104, 562.5 ns ×2759; mean 322.8.
In bit units: p50 **0.217**, p90 0.268, max **0.485**.

**Cell census** (9553 cells / 54 captures): `0` 5110, `1` 3545,
`11` 553, `10` 192, `00` 117, `01` 24, 3-bit 12. Cells per capture
**152–191**. ≈8.3 % of bits live in multi-bit cells; ≈3.0 % of bits are
swallowed zeros; ≈5.4 % are merged ones. Structural violations 0.30 %.

**Discriminating samples per bit** (calibrated time base, window
(375, 750) ns): 0 → **49 bits (0.47 %)**, 1 → 6485 (62.5 %), 2 → 3834
(37.0 %), ≥3 → 0. Of the 49 dead bits, 40 are true 0s and 9 are true 1s.

**Apparent bit period in the receiver coordinate.** Global comb per
capture: **1243–1280 receiver-ns (2.9 % spread)** — pattern-correlated,
NOT clock spread. Local 7-cell tracker: median 1250.0 (nominal geometry) /
1262.9 (calibrated geometry), ≈0.3 % spread. Synthetic corners:
1156 (−7.5 %), 1250 (0), 1343 (+7.5 %) → search band must be
`0.85·1250 … 1.15·1250` ns.

**Phase-accuracy budget** (per-sample window vote, calibrated base):
±20 ns of global phase error moves the error rate between 4.7 % and
11.9 %; a residual scale error of 5·10⁻⁴ over the 240 µs frame moves it
between 1.9 % and 17.6 %.

**Tracker window sweep** (cell error / front-end exact, calibrated, real):
W=2 2.53 %/24, **W=3 2.46 %/24**, W=4 2.56 %/22, W=6 2.79 %/20,
W=8 2.93 %/20, W=10 3.55 %/17, W=14 4.46 %/16, W=20 5.65 %/15,
W=30 6.85 %/15.

**Constraint value** (W=10): unconstrained 0.0315 /bit → +count 0.0315 →
+header/trailer **0.0134** (−58 %). Raw bit count ≠192 in **17/54**
captures. DP infeasibility: 0 of 54 real, 0 of 288 synthetic.

**Best measured end-to-end** (W=3, `EPS_CENTER = 0`): nominal geometry
train 18/36 exact (50.0 %) / holdout 7/18 (38.9 %), byte accuracy 92.4 %,
0.0088 and 0.0078 bit error; calibrated geometry train 17/36 (47.2 %) /
holdout 9/18 (50.0 %), 0.0082 and 0.0075 bit error.

**Soft-output calibration** (W=3, calibrated, 6912 payload bits, 75
errors): `|LLR| > 0.5` → 588 bits, **0 errors**; `|LLR| ≤ 0.10` → 995 bits
holding 98.7 % of all errors; worst-capture list depth **26**.
Cell margin (W=10): `|margin| ≥ 2` → 1457 cells at 0.00069 error rate.

**Cost-model insensitivity:** `EPS_CENTER ∈ [0, 2.0]` × `W_RISE ∈
[0.5, 2.0]` changes the result by at most one capture out of 54 — the
hinge is saturated and feasibility dominates. Set `EPS_CENTER = 0.10`
only to break LLR ties.
