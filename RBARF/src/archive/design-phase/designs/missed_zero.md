# missed_zero — technique design

Swallowed-0-bit recovery by gap accounting on the exact 1250 ns grid, plus the
dual artifact (merged 1-bit runs) split by the same arithmetic.

All numbers below were measured by me on the 54 real captures (and on
`synth.py` for the envelope); exploration code is in
`/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/dev_missed_zero/`
(`m1_basics.py` … `m16_lock.py`, `mz_common.py`).

---

## Target artifact & evidence

### The two artifacts

The WS2812 waveform has a **rising edge at every bit boundary**, exactly at
`n·1250 ns`, for both symbols. What varies is only the high duration
(`T0H≈350`, `T1H≈700`) and hence the low duration (`T0L≈900`, `T1L≈550`).
The sampler's largest inter-slot dead zone is the **slot7→slot0 gap**, so:

* a bit's whole high phase can land in that gap → **swallowed 0-bit**: no
  pulse at all, only an over-long low gap;
* a 1-bit's `T1L` can land in that gap → **merged pulse**: two (or more)
  bits appear as one ~2 µs high.

`T0L = 900 ns` is larger than any dead zone anywhere in the envelope, so a
**0-bit never merges** — this is the structural invariant the whole technique
rests on (see *Failure modes* for the margin).

### Measured on the real dataset (54 captures, time base = fitted calibration model)

| quantity | value |
|---|---|
| in-frame samples | 41 460 / 54 captures → **3.999 samples per bit** |
| frame occupies | first ~96 of the 640 loops (192 bits × 1250 ns = 240 µs) |
| inter-slot gaps (ns), slot s→s+1 | 249.8, 268.8 / 206.4\*, 278.9, 265.5 / 390.8\*, 263.3, 339.0, 273.2, **587.8 / 650.8\*** |
| **swallowed 0-bits** | **282 / 5505 zeros = 5.12 %** (5.2 per frame; worst capture `rnd3_0` = 21, `sparse_2` = 18) |
| swallowed 1-bits | **0 / 4863** — a 1-bit is never fully lost |
| swallow location | 218/282 (77 %) in the slot7→slot0 gap, 31 slot4→5, 29 slot5→6, 4 slot3→4 |
| **merged 1-bits** (T1L unobserved) | **723 / 4863 ones = 14.9 %** (13.4 per frame; `runs` pattern: 55/frame) |
| merge location | **723/723 = 100 % in the slot7→slot0 gap** |
| observed span-2 pulses | 709; span-3 pulses: **0** |
| mean high samples | 1.21 per 0-bit, 2.57 per 1-bit |
| pulse sample-count histogram | {1: 4009, 2: 2949, 3: 1886, 4: 14, 5: 159, 6: 536} |

\* the calibration model's data-dependent term `w = [0,−62.5,0,+125,0,0,0,+62.5]`
makes three of the eight gaps bimodal (value when the *preceding* slot read HIGH).

### Why gap accounting works: the two things that are exactly recoverable

1. **Rise-to-rise distance quantises perfectly.** Consecutive visible pulses
   start at exact grid points, so `Δrise / 1250` must be an integer.
   Measured: `round(Δrise/BIT)` equalled the true bit advance
   **9323 / 9323 = 100.00 %**; the fractional residual has σ = 0.114 bit and
   max |·| = 0.373 bit — a factor 1.34 of margin before a rounding error.
2. **The pulse's total high duration is bracketed.** The true fall lies in
   `(fa, fb]` = (last high sample, first low sample). Testing which of
   `{h0, h1, BIT+h0, BIT+h1, 2BIT+h0, …}` lies inside that bracket resolves
   span *and* the last bit simultaneously.

Everything else follows by arithmetic:
`hidden_zeros(j) = n[j+1] − n[j] − span(j)`.

### The decisive experiment

Running the full pipeline against ground truth (`m5_diag.py`), the error
taxonomy over all 54 captures was:

```
error taxonomy: {'lastbit': 115, 'span': 0, 'hidden': 0}
                 ... and all 115 sat on pulses whose candidate set was ambiguous
```

**Zero index-advance errors, zero span errors, zero hidden-zero-count errors.**
All 282 swallowed 0-bits and all 709 merged pairs were reconstructed correctly.
The only residual errors are the last-bit width call — which is exactly the
decision the *other* five techniques exist to make.

### The mechanism nobody documented: the sampler phase-locks to the bit grid

`m16_lock.py`. The calibration model's data-dependent term is a **negative
feedback loop**. `w[3] = +125 ns` fires only when slot 3 reads HIGH; slot 3 sits
late in the bit (offset ≈ 500–780 ns), so it reads high only when the phase has
drifted *early*, and the +125 ns then pushes the phase back. Consequence:

| | in-frame loop period | idle-tail loop period |
|---|---|---|
| range over 54 captures | **2494.7 … 2513.4 ns** (bimodal: a cluster at ~2497 and one at ~2510) | 2525.1 … 2528.5 ns |

The frame drags the loop from 2527.5 ns to within ~2 ns of exactly `2·BIT`.
Residual in-frame phase crawl is only **−0.2 … −5.6 ns/loop** (median 3.6),
not the ~25 ns/loop a rigid 2525.9 ns loop would give.

This explains three otherwise puzzling facts:
* **intrinsic ambiguity is tiny**: only **42 / 10 368 bits (0.41 %, 0.78 per
  frame)** have *no* sample in the decisive window `[n·BIT+350, n·BIT+700)`, where
  the naive geometry (a 587.8 ns dead zone against a 350 ns window) predicts 9.4 %;
* artifacts are **pattern-clustered**, not uniform — the ~2510 lock state
  (`p55`, `lone1`, `msb1`, `count`, `sparse`, `edges`) carries all the
  ambiguous bits and the high swallow counts, the ~2497 state carries almost none;
* `harness.LOOP_NS = 2507.3` is the *median of a bimodal in-frame
  distribution*, which is why no single loop period fits well.

**Implementer warning:** `synth.py` has no `w` term, so its loop is rigid and
its phase crawls freely. It therefore shows 7–12 % intrinsically ambiguous bits
and 8–12 swallowed zeros/frame where the real hardware shows 0.41 % and 5.2.
Treat synth results as a pessimistic bound, not as the bench point.

---

## Algorithm

### Inputs

| symbol | meaning | source |
|---|---|---|
| `samples` | `[(i, s, level)]` chronological | harness |
| `G` | loop grain in model-ns | calibration (`2525.894`) |
| `o[0..7]` | intra-loop slot offsets, model-ns | calibration |
| `w[0..7]` | ns added to every later sample per HIGH read at slot j | calibration |
| `h0, h1` | effective high durations | calibration (`339.25 / 737.25`) or nominal `350 / 700` |
| `BIT` | 1250.0 (exact) | protocol |
| `NB` | 192 (frame bits) | protocol |
| `delta` | bracket dilation, ns (default **40**) | global, see *Calibration* |
| `S_MAX` | max merge multiplicity to consider (default **4**) | global |
| `KLO, KHI` | blind scale search range (default `[0.92, 1.09]`) | global |

### Pseudocode

```python
# ---------- 0. model clock ------------------------------------------------
# A[m] is a monotone "receiver clock" in model-ns; the only unknowns left are a
# single scale kappa and offset tau (the HSI error and the trigger phase).
run = [0]*8
for m, (i, s, lev) in enumerate(samples):
    A[m] = i*G + o[s] + sum(w[j]*run[j] for j in range(8))
    run[s] += lev
L[m] = level of sample m

# ---------- 1. runs -> brackets ------------------------------------------
# For each maximal run of HIGH samples [i0..i1]:
#   true rise in (ra, rb]   ra = A[i0-1]  (or A[i0]-250 for the first pulse)
#                           rb = A[i0]
#   true fall in (fa, fb]   fa = A[i1]
#                           fb = A[i1+1] (or A[i1]+250 at the buffer end)
P = [ {ra, rb, fa, fb, rmid=(ra+rb)/2, fmid=(fa+fb)/2, ns=i1-i0+1} for each run ]

# ---------- 2. blind grid fit (rise-bracket Hough) ------------------------
# EVERY WS2812 bit begins with a rising edge at an exact multiple of BIT, so a
# correct (kappa, tau) makes as many rise brackets as possible straddle a grid
# point.  No knowledge of the bit values is needed.
def hough_score(kappa, tau):
    hits, resid = 0, 0.0
    for p in P:
        rm = kappa*p.rmid + tau
        if rm >= NB*BIT + 400: continue           # past the frame -> latch tail
        g = round(rm/BIT)*BIT
        if kappa*p.ra + tau <= g <= kappa*p.rb + tau: hits += 1
        resid += abs(rm - g)
    return (hits, -resid)                          # lexicographic

kappa, tau = argmax over
    kappa in linspace(KLO, KHI, 521), tau in arange(-400, 600, 20)
then 3 refinement passes:  kappa +- 5e-4 -> 1e-4 -> 2e-5 (41 pts),
                           tau  +- 60 -> 12 -> 3 ns      (31 pts)

for p in P:  map ra, rb, fa, fb, rmid, fmid  ->  tau + kappa*x
P = [p for p in P if p.rmid < NB*BIT + 400]        # drop latch-tail glitches

# ---------- 3. bit indices (the gap accounting proper) --------------------
n[0] = round(P[0].rmid / BIT)                      # normally 0: edge-triggered
if n[0] != 0: n[0] = 0                             # hard anchor, see Calibration
for j in 1..len(P)-1:
    n[j] = n[j-1] + round((P[j].rmid - P[j-1].rmid) / BIT)   # 100% exact (measured)

# ---------- 4. per-pulse hypothesis set ----------------------------------
# Total high duration of a pulse covering s bits ending in value b:
#     H(s,b) = (s-1)*BIT + (h1 if b else h0)
# and the observation constrains  fa < n*BIT + H <= fb.
for j, p in enumerate(P):
    nxt   = n[j+1] if j+1 < len(P) else NB
    s_cap = min(S_MAX, max(1, nxt - n[j]))         # cannot cover past the next rise
    u = p.fa - n[j]*BIT
    v = p.fb - n[j]*BIT
    F[j] = [ (s,b) for s in 1..s_cap for b in (0,1)
             if u - delta < H(s,b) <= v + delta ]
    # soft score for every (s,b), used by the combiner:
    LL[j][(s,b)] = -( max(0, u - H(s,b))**2 + max(0, H(s,b) - v)**2 ) / (2*sigma**2)
    if F[j] is empty:                              # time-base slip
        F[j] = all (s,b) with s <= s_cap ; flag INFEASIBLE
    pick (s*, b*) = argmax LL[j] over F[j]         # == nearest H to (u+v)/2

# ---------- 5. emit bits --------------------------------------------------
bits = [0]*NB                                      # zeros are the default!
for j, p in enumerate(P):
    s, b = chosen[j]
    for a in 0 .. s-2:  bits[n[j]+a] = 1           # merge prefix: ALWAYS 1
    bits[n[j]+s-1] = b                             # the width-decided bit
    nxt = n[j+1] if j+1 < len(P) else NB
    # hidden = nxt - n[j] - s  swallowed zeros; they are already 0 in `bits`
    hidden[j] = nxt - n[j] - s                     # >= 0 by construction of s_cap
# bits after the last pulse's span are 0 (latch)

# ---------- 6. frame ------------------------------------------------------
frame_bytes = pack MSB-first
check frame_bytes[0:4] == FF 00 AA 65 and frame_bytes[20:24] == 9A 55 00 FF
payload = frame_bytes[4:20]
```

### Why step 4 also splits merged pulses

A span-2 pulse has `H ∈ {1600, 1950}` (nominal) — 900+ ns away from any span-1
candidate, so span is decided with enormous margin. Measured widths
(`fmid − rmid`) on real data:

| class | n | mean | p1 | p99 |
|---|---|---|---|---|
| span 1, last 0 | 5062 | 366.7 | 228.1 | 647.3 |
| span 1, last 1 | 3606 | 751.0 | 470.9 | 890.2 |
| span 2, last 0 | 161 | 1721.7 | 1446.4 | 1748.5 |
| span 2, last 1 | 548 | 1984.1 | 1689.3 | 1991.2 |

Span-1 vs span-2 never overlap (max span-1 = 1069.8 < min span-2 = 1445.9);
last-0 vs last-1 *do* overlap on the midpoint statistic — which is precisely why
step 4 uses the **bracket**, not the midpoint, and why the leftovers become soft
outputs instead of guesses.

---

## Calibration

| parameter | how it is obtained | measured value / range |
|---|---|---|
| `G, o[], w[], h0, h1` | **global**, from the calibration technique's fit (`approaches/dev_calibration/final.json`, 99.47 % sample agreement). If unavailable, fall back to `G = 2500`, `o = [1,5,9,13,17,21,27,32]·62.5`, `w = 0`, `h0/h1 = 350/700` — the technique still works (it is scale-blind), only `delta` must be raised. | `G = 2525.894`; `o = [61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0, 1727.0, 2000.0]`; `w = [0, −62.5, 0, 125, 0, 0, 0, 62.5]`; `h0 = 339.25`, `h1 = 737.25` |
| `kappa, tau` | **per capture, blind** (step 2). Needs no bit knowledge: it only asserts that rise brackets straddle grid points. Cost ≈ 521×51 coarse + 3×41×31 fine evaluations over ~180 pulses — a few ms in numpy. | real dataset: `kappa ∈ [1.00048, 1.00121]`, `tau ∈ [196, 441] ns` |
| `delta` | **global**, swept (`m14_delta.py`). It buys reliability with coverage; see the table below. Scale it with `kappa` (dead zones scale as `1/(1+ε)`), i.e. use `delta_eff = delta · kappa`. | **40 ns** default |
| `sigma` (soft-score slack) | same physical quantity as `delta`; use `sigma = delta` (40–50 ns). | 45 ns |
| `S_MAX` | span-3 was never observed at the bench point and only span ≤ 2 occurred anywhere in the ±8 % synth sweep; 4 is a safety margin that costs nothing. | 4 |
| `KLO, KHI` | must cover `1/(1+ε)` over the ±7.5 % envelope **relative to the model grain**: `[0.926, 1.087]`; use `[0.92, 1.09]`. If the grain is the nominal 2500 instead of 2525.9, shift by 1.0103 → `[0.93, 1.10]`. | — |

### The `delta` sweep (real dataset, blind time base, all 9553 pulses)

| `delta` (ns) | unique hypothesis | of those, correct | ambiguous (≥2) | truth in the ambiguous set | infeasible | exact payloads |
|---|---|---|---|---|---|---|
| 0 | 90.01 % | 98.78 % | 0.27 % | 100.00 % | 9.71 % | 26/54 |
| **40** | **96.71 %** | **99.66 %** | **3.22 %** | **100.00 %** | 0.06 % | 26/54 |
| 80 | 89.33 % | 99.78 % | 10.67 % | 99.71 % | 0.00 % | 26/54 |
| 120 | 81.24 % | 99.88 % | 18.76 % | 99.27 % | 0.00 % | 26/54 |
| 160 | 66.25 % | 99.98 % | 33.75 % | 99.35 % | 0.00 % | 26/54 |

`delta = 40` is the knee: 96.7 % of pulses decided uniquely at 99.66 %
accuracy, with only ~5.7 pulses per frame handed to the combiner and the truth
guaranteed to be in the handed-over pair.

### What NOT to do

I tried refitting `(tau, kappa, h0, h1)` by maximising total sample agreement
against the decoded waveform and iterating (`m11_iter.py`). **It makes things
worse** (26 → 24/54 exact, and the effect saturates after one iteration).
Reason: total-sample agreement is dominated by the 4400 trivially-low latch
samples and by mid-pulse samples that carry no edge information; it pulls the
time base off the rise-edge-consistent optimum that the classifier needs.
Likewise, using the calibration's own ground-truth-fitted `(t0, k)` gives
**23/54**, worse than the blind rise-Hough fit's **26/54**. *The Hough
objective is the right objective for this technique* — the combiner should keep
it as a separate, gap-accounting-specific estimate even if a global calibration
`(t0, k)` is available.

An affine self-consistent phase re-fit (`t += a + b·n`, feasibility-maximising)
was also neutral-to-negative (26 → 25) — the residual crawl is only ~0.5 ns/bit
(−0.13 % … +0.007 % equivalent clock error), already below the bracket width.

---

## Envelope behavior

### Physics at the corners

The dead zone that produces both artifacts is the slot7→slot0 gap. It scales as
`1/(1+ε)`:

| ε | slot7 gap (synth geometry, ns) | vs `T0H = 350` | vs `T1L = 550` | vs `T0L = 900` |
|---|---|---|---|---|
| +7.5 % | 523.3 | swallows | marginal | safe |
| 0 (bench, synth) | 562.5 | swallows | marginal | safe |
| bench, real (calib model) | 587.8 / 650.8 | swallows | swallows | safe |
| −7.5 % | 608.1 | swallows | swallows | safe |
| −8 % | 611.4 | swallows | swallows | safe |

**The `T0L = 900 ns` margin never closes**: even at −8 % the largest dead zone is
611 ns (synth) / 703 ns (real geometry, 650.8 × 1.087), leaving ≥ 197 ns of
margin. So *0-bits never merge anywhere in the envelope*, and the "merge prefix
bits are all 1" invariant that the algorithm emits as a hard constraint is safe.
It would only break if the end-of-loop gap exceeded ~14.4 cycles.

### Measured on synth, 18 patterns × 3 phases per point (`m10_env.py`)

| ε | index-advance exact | span exact | hidden-count exact | last-bit correct | flagged ambiguous | swallowed 0s/frame |
|---|---|---|---|---|---|---|
| −8.0 % | **1.0000** | **1.0000** | **1.0000** | 0.9417 | 35.1 % | 11.8 |
| −7.5 % | **1.0000** | **1.0000** | **1.0000** | 0.9326 | 30.5 % | 12.0 |
| −5.0 % | **1.0000** | **1.0000** | **1.0000** | 0.9321 | 30.2 % | 7.9 |
| −2.5 % | **1.0000** | **1.0000** | **1.0000** | 0.9454 | 28.1 % | 12.0 |
| 0 | **1.0000** | **1.0000** | **1.0000** | 0.9226 | 16.7 % | 0.0 |
| +2.5 % | **1.0000** | **1.0000** | **1.0000** | 0.9549 | 25.0 % | 6.8 |
| +5.0 % | **1.0000** | **1.0000** | **1.0000** | 0.9475 | 27.7 % | 7.5 |
| +7.5 % | **1.0000** | **1.0000** | **1.0000** | 0.9562 | 28.0 % | 7.2 |
| +8.0 % | **1.0000** | **1.0000** | **1.0000** | 0.9602 | 20.5 % | 8.0 |

**The gap-accounting core is exact across the whole ±8 % envelope.** Bit
indexing, merge splitting and swallowed-zero counting never fail once the blind
scale search covers the corner. That is the technique's contribution and it is
temperature-proof.

### Slow-corner analysis (ε = −7.5 %, the hard corner)

* Samples per bit falls from 4.00 to `1250·(1+ε)/(2500/8)` = **3.70**. The
  rise-bracket width grows by 8.1 %; worst-case rmid error rises from 0.373 to
  ~0.40 bit — still inside the ±0.5 bit rounding margin, but the headroom drops
  from 34 % to 25 %. This is the single number to watch.
* Swallowed 0-bits per frame roughly double (5.2 real / 0 synth-nominal →
  ~12 synth). Every one of them is still recovered by the arithmetic, because
  recovery does not depend on seeing the pulse — only on the two neighbouring
  rises.
* Merged spans stay at ≤ 2 across the whole sweep (`m15_envstats.py`), so
  `S_MAX = 4` is never binding.
* The *last-bit* decision is what degrades: the decisive window
  `[350, 700)` is 350 ns against a 608 ns dead zone, so 7–12 % of bits become
  information-free in the rigid synth model. **Caveat**: the real hardware's
  `w` feedback (see above) holds this to 0.41 % at the bench point; whether the
  lock survives at ±7.5 % is untestable with the present data and is the main
  open risk. If the lock is lost, `flagged ambiguous` rises to ~30 % and the
  combiner carries the whole burden of the width decision.
* `delta` must be scaled by `kappa` at the corners, otherwise a fixed 40 ns is
  ~8 % too tight at −7.5 % and the INFEASIBLE rate climbs.

---

## Failure modes

Honest list of where **this technique alone** loses bits.

1. **The last-bit width call is not solved here.** With `delta = 40` on real
   data: 3.2 % of pulses (≈ 5.7 per frame) come out as a two-element candidate
   set, and among the "unique" 96.7 % there is still a 0.34 % error rate
   (≈ 0.55 bits per frame). End to end that is **26/54 exact payloads (48 %)**
   standalone, with a payload-bit-error histogram of
   `{0 err: 26, 1: 10, 2: 10, 3: 4, 4: 4}` — mean 1.1 wrong payload bits.
   This technique's job is to *segment* and to *count*, not to decide widths.

2. **Truly information-free bits.** 42 / 10 368 bits (0.41 %, 0.78 per frame)
   have no sample anywhere in `[n·BIT+350, n·BIT+700)`. For those, a 0 and a 1
   produce byte-identical sample sequences: no amount of local processing can
   separate them. Only cross-technique evidence (the `w` feedback's effect on
   *later* sample times, or an outer code) could. These are always flagged.

3. **A missed rise ⇒ index slip ⇒ catastrophic.** The whole scheme is
   incremental: one wrong `round(Δrise/BIT)` shifts every later bit. It never
   happened on the real data (9323/9323) or anywhere in the synth sweep, but the
   margin is only 1.34× at the bench point and 1.25× at −7.5 %. Two failure
   triggers: (a) a wrong `kappa` from the Hough fit (a local optimum at
   `kappa·(1±1/192)`), (b) a genuinely long run of consecutive swallowed
   0-bits (see 4). Mitigation: the header/trailer check in step 6 detects a slip
   with near certainty, and the combiner should treat a header/trailer mismatch
   as "re-run with the second-best Hough peak".

4. **Long runs of consecutive swallowed 0-bits.** Recovery is exact only
   because the *gap* is measured between two visible rises. Measured run
   lengths of consecutive swallowed zeros: **274 runs of 1, 4 runs of 2, none
   longer**. A run of ≥ 5 would put the gap at ≥ 6·1250 = 7500 ns and the
   rounding margin is still ample, so length itself is not the danger — the
   danger is a swallowed zero at the *very start* (before the first visible
   pulse) or *very end* of the frame, where there is no bracketing rise. The
   start is protected (bit 0 of the header is `1`, and the capture is edge
   triggered on it); the end is protected by the trailer ending in `FF`.
   A frame whose header/trailer were not `FF…FF`-bounded would be exposed.

5. **INFEASIBLE pulses (time-base slip).** At `delta = 0`, 9.7 % of pulses have
   *no* hypothesis inside the bracket — proof that the calibration time base is
   off by up to ~120 ns locally. `delta = 40` cuts this to 0.06 %, but it is a
   band-aid: the underlying residual is a real limit on how tight the brackets
   can be, and it is what forces 3.2 % of pulses into ambiguity that better
   calibration would resolve.

6. **Latch-tail glitches.** 176 high runs per 54 captures land outside any true
   bit window under the calibration time base. Step 2's `rmid < NB·BIT + 400`
   filter removes the post-frame ones; the rest are absorbed as INFEASIBLE.
   A stray glitch *inside* the frame would inject a spurious rise and slip the
   index — the combiner should drop single-sample runs whose rise bracket does
   not straddle a grid point at any `delta`.

7. **Span-3+ merges are untested.** Never observed on real data or in the
   ±8 % sweep. The code handles them, but the width separation between
   `H(3,0)=2850` and `H(2,1)=1950` has not been validated empirically.

8. **Non-monotone `n[]` is not handled.** If two pulses round to the same index
   (never observed), the emission loop would overwrite. Add an assertion.

---

## Composition interface

### Pipeline position

```
   raw samples
        |
   [calibration]  -> G, o[], w[], h0, h1   (global, once)
        |
   [missed_zero]  -> model clock A, blind (kappa,tau), PULSE SEGMENTATION
        |             +--- bit index n[j] per pulse      (hard, 100% exact)
        |             +--- span s[j], hidden zeros       (hard, 100% exact)
        |             +--- per-bit soft/hard labels
        v
   [matched_filter] [histogram_adaptive] [boundary_model] [edge_dp] [clock_stretch]
        |             all of these decide *widths*; they should consume
        |             missed_zero's segmentation instead of re-deriving one
        v
   [combiner]  per-bit LLR fusion + header/trailer constraint -> payload
```

`missed_zero` belongs **immediately after calibration and before every
width-decision technique**, because it converts "a list of pulses" into "a
labelled 192-slot bit grid" — the coordinate system the others need. It should
*not* be a voter at the end.

### Inputs it needs

* `samples`, and the calibration model `(G, o[], w[], h0, h1)`. It degrades
  gracefully to nominal geometry (`G=2500`, doc offsets, `w=0`).
* Nothing else. In particular it does **not** need a prior `(t0, k)` — and
  measurably should not use one (see *Calibration → What NOT to do*).

### Outputs it provides

1. **`kappa, tau`** — a rise-edge-consistent per-capture time base, plus the
   Hough hit count as a confidence (real data: ≥ 95 % of rise brackets straddle
   a grid point at the optimum). Offer the top-3 Hough peaks so the combiner can
   retry on a header/trailer failure.
2. **`n[j]`, the bit index of every visible pulse** — hard, 100 % exact on 9323
   real transitions and across ±8 % synth. Publish it as a *constraint*, not a
   suggestion: any technique proposing a different bit boundary is wrong.
3. **`span[j]` and `hidden[j]`** with these enforceable constraints:
   * `bits[n[j] .. n[j]+span-2] == 1` (merge prefix — structurally guaranteed,
     `T0L=900` > every dead zone in the envelope);
   * `bits[n[j]+span .. n[j+1]-1] == 0` (hidden zeros — a swallowed bit is
     always a 0, measured 0/4863 1-bits ever lost);
   * `sum over j of (span[j] + hidden[j]) == 192` exactly.
   On real data these three account for **282 zeros and 709 merged ones per
   54 frames that no width-based technique can see at all**.
4. **Per-pulse candidate set `F[j]` and log-likelihoods `LL[j][(s,b)]`** —
   `LL = −(max(0, u−H)² + max(0, H−v)²)/(2σ²)`, `σ = 45 ns`. Convert to a
   per-bit LLR for the last bit of each pulse:
   `LLR(bit n[j]+s−1) = LL[j][(s,1)] − LL[j][(s,0)]`. Bits covered by a merge
   prefix or by a hidden gap get LLR = ±∞ (hard).
5. **A per-bit dead-zone schedule**, computed from sample times alone (no bit
   knowledge), with measured **precision 1.000** against truth:
   * `S(n)` = no sample in `[n·BIT, n·BIT+h0)` → this bit, if 0, is invisible
     (recall 0.784 — it is a sufficient condition, not necessary);
   * `M(n)` = no sample in `[n·BIT+h1, (n+1)·BIT)` → this bit, if 1, merges
     forward (recall 0.759);
   * `D(n)` = a sample exists in `[n·BIT+h0, n·BIT+h1)` → the bit is locally
     decidable. `¬D(n)` fires on 0.41 % of real bits and marks the genuinely
     unrecoverable ones.
   This lets the combiner *predict* which bits every other technique will get
   wrong, and down-weight them before voting.

### How the combiner should use it

* Take the segmentation as ground truth; let the other techniques supply LLRs
  **only for the last bit of each pulse** (≈ 160 of 192 bits per frame). This
  removes ~30 bits/frame from contention for free.
* Fuse LLRs, then apply the header/trailer as a hard 64-bit constraint. Because
  `missed_zero` reports the truth-containing candidate set 100 % of the time at
  `delta ≤ 40`, a header/trailer mismatch is a reliable signal to flip the
  lowest-|LLR| flagged bits (there are only ~5.7 candidates per frame) rather
  than to re-decode.
* Where `¬D(n)`, do not let any technique vote confidently: no sampler observed
  the discriminating interval, so a confident width estimate there is an
  artifact of the estimator, not of the data.
* If a second `missed_zero` pass is affordable, re-run step 2 restricted to the
  rise brackets whose pulses the combiner has since resolved — the Hough
  objective gets sharper as `delta` can be shrunk.

---

## Key numbers

Constants and thresholds an implementer should reuse verbatim.

```python
BIT_NS   = 1250.0            # exact, crystal-derived
T0H_NS   = 350.0 ; T1H_NS = 700.0
T0L_NS   = 900.0 ; T1L_NS = 550.0
NBITS    = 192               # FF 00 AA 65 + 16 payload + 9A 55 00 FF

# --- calibration model (approaches/dev_calibration/final.json, 99.47% agree) --
G_NS   = 2525.894
SLOT_O = [61.875, 311.625, 580.375, 859.25, 1124.75, 1388.0, 1727.0, 2000.0]
SLOT_W = [0.0, -62.5, 0.0, 125.0, 0.0, 0.0, 0.0, 62.5]   # ns per HIGH read, cumulative
H0_EFF = 339.25 ; H1_EFF = 737.25

# --- derived inter-slot gaps (ns), s -> s+1 ; "/x" = value when slot s read HIGH
GAPS = [249.75, 268.75/206.25, 278.875, 265.50/390.50, 263.25, 339.00, 273.00,
        587.77/650.27]                       # sum = 40.414 CPU cycles @62.5 ns
DEAD_ZONE = 587.77                           # slot7 -> slot0, the only real one
                                             # 9.40 cycles; 100% of merges here

# --- technique parameters -------------------------------------------------
DELTA_NS = 40.0     # bracket dilation; scale by kappa at the envelope corners
SIGMA_NS = 45.0     # soft-score slack
S_MAX    = 4        # max merge multiplicity (>=2 observed, 3 never)
K_RANGE  = (0.92, 1.09)   # blind scale search vs G_NS, covers +-7.5% HSI
TAIL_MARGIN_NS = 400.0    # drop pulses with rmid > NBITS*BIT + this
```

Empirical distributions to sanity-check an implementation against:

| measurement | value |
|---|---|
| in-frame samples per bit | 3.999 |
| in-frame effective loop period | 2494.7 – 2513.4 ns (bimodal ≈2497 / ≈2510); idle tail 2525.1 – 2528.5 ns |
| in-frame residual phase crawl | −0.2 … −5.6 ns/loop, median 3.6 |
| per-capture blind fit | `kappa ∈ [1.00048, 1.00121]`, `tau ∈ [196, 441] ns` |
| `round(Δrise/BIT)` accuracy | 9323 / 9323 = 1.0000 (residual σ = 0.114 bit, max 0.373) |
| rise residual `rmid − n·BIT` | mean −32.6 ns, σ 115.1, range [−359, +421] |
| rise bracket width | mean 358.4 ns, p90 588.2; grid point inside 95.4 % |
| swallowed 0-bits | 282 / 5505 = 5.12 % (5.2/frame; max 21) — **282/282 recovered** |
| lost 1-bits | 0 / 4863 |
| merged 1-bits | 723 / 4863 = 14.9 % (13.4/frame; max 55) — 100 % in the slot7 gap |
| observed span-2 pulses | 709 — **709/709 split correctly** |
| swallow-run lengths | 274×1, 4×2, none longer |
| merge bursts (consecutive loops) | strict runs {1:283, 2:90, 3:60, 4:35, 7:20, 9:1, 10:1}; with ≤2-loop linkage, bursts up to 49 loops |
| intrinsically undecidable bits | 42 / 10368 = 0.41 % (0.78/frame) |
| pulse widths `fmid−rmid` | (1,0) 366.7±121.2 · (1,1) 751.0±136.6 · (2,0) 1721.7±84.9 · (2,1) 1984.1±44.1 |
| pulse sample counts | {1: 4009, 2: 2949, 3: 1886, 4: 14, 5: 159, 6: 536} |
| standalone exact payloads | **26 / 54** (blind fit, `delta` any of 0–200) |
| standalone payload bit errors | {0: 26, 1: 10, 2: 10, 3: 4, 4: 4} captures |
| error taxonomy | last-bit 115, **span 0, hidden-count 0, index 0** |
