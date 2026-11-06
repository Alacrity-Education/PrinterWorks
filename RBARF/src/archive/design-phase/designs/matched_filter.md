# matched_filter — technique design

*Waveform-level reconstruction on a fine grid, with a two-anchor global
lock and per-cell template scoring.*

All numbers below were measured by the scripts in
`/home/alex.lucaci/Projects/RBARF/new-implementation/recon/designs/dev_matched_filter/`
(`common.py`, `mf.py`, `e2_oracle.py`, `e4_cells.py`, `e6_fold.py`,
`e8_decidability.py`, `e9_envelope.py`, `e11_ablate.py`, `e12_real.py`,
`e13_anchorcal.py`, `e14_resid.py`, `e15_tol.py`) against
`../data/captures.json` (54 real captures) and, for the clock envelope,
against `synth.py`.

---

## Target artifact & evidence

**What this technique fixes.** Every pulse-oriented decoder (count pulses,
measure widths, find edges) is destroyed by the three headline artifacts:
swallowed 0-bits, merged 1-bits, and byte-boundary gap distortion. This
technique removes them by construction: it never counts a pulse and never
measures a width. It fixes one affine map from *receiver phase* to *wire
time* using only the 64 known header/trailer bits, then asks each of the
128 payload bit cells a single local question — "of the samples that landed
inside this cell, do any of them fall in the window where a `1` and a `0`
differ, and what did they read?" A swallowed pulse and a merged pulse are
then not errors at all; they are simply *samples that carry no information*,
and the technique reports them as erasures instead of guessing.

**Evidence 1 — the artifacts are real and large.** Using a per-capture
oracle time base (`e4_cells.py`, nominal grid):

| phenomenon | measurement over all 54 captures |
|---|---|
| 0-bits producing **zero** high samples | 171 / 5505 = **3.11 %** |
| 1-bits producing zero high samples | 30 / 4863 = 0.62 % |
| adjacent `11` pairs sampled as one merged high | 551 / 2931 = **18.8 %** |
| samples landing in one bit cell | 3 (4133×), 4 (2106×), 5 (4126×) — a strict 3/5 alternation |

The 3/5 alternation is the byte-boundary artifact: the slot7→slot0 gap is
~9 CPU cycles (562 ns at nominal) versus ~4 cycles elsewhere, so one of the
two bit cells per sampling loop is starved.

**Evidence 2 — the swallowing reaches into the header's own `00` byte.**
Header is `FF 00 AA 65`; bits 8..15 are eight consecutive `0`s whose T0H
must survive to be seen. Measured (`e4_cells.py`):

* 37 / 432 header-`00` zero bits (**8.6 %**) produced no high sample at all;
* 19 of 54 captures lost at least one of the eight; two captures lost four
  of the eight;
* worst frame-bit positions across the dataset are 191, 15, 14, 13, 12 and
  179, 181 — i.e. the tails of *both* `00` bytes (header bits 8..15 and
  trailer bits 176..183) and the last trailer bit.

An anchor that depended on seeing those eight pulses would be fragile. The
ablation in `e11_ablate.py` shows this technique's anchor does not depend on
them at all (see *Envelope behavior*).

**Evidence 3 — the wire template is exactly `750 / 375`, not `700 / 350`.**
`e6_fold.py` folds the perfectly periodic payload regions (`ones` payload =
128 identical `1` bits → period 1250 ns; `zeros` → 128 identical `0` bits)
against a scanned (phase, κ) and reads the high window straight off the
data:

```
ones_0  high window = 750.9 ns   (fold agreement 94.7 %)
ones_1  high window = 754.3 ns   (95.1 %)
ones_2  high window = 749.8 ns   (94.9 %)
zeros_1 fold: fully HIGH for phase 1150…1250 and 0…300, fully LOW 300…1100
        → effective T0H ≈ 350–400 ns, rise smeared over ~150 ns
```

So `h1 = 750 ns` is confirmed to ±5 ns, contradicting
`harness.T1H_NS = 700`. The implementer must use 750/375-ish, not the
harness constants. (`synth.py` also uses 700/350; when scoring against
`synth.py` set the template to *its* constants — see *Calibration*.)

**Evidence 4 — the pay-off.** With a correct fine grid (measured on
`synth.py`, whose grid is known exactly, `e11_ablate.py` mode `joint`):

| ε | erasures | **BER among decidable cells** | lock failures | erasure runs |
|---|---|---|---|---|
| −7.5 % | 11.72 % | **0.0000 %** | 0/54 | all length 1 |
| −5.0 % | 10.42 % | **0.0000 %** | 0/54 | all length 1 |
| −2.5 % |  9.38 % | **0.0000 %** | 0/54 | all length 1 |
| −0.3 % (bench) |  7.29 % | 0.3121 % | 0/54 | all length 1 |
| +2.5 % |  8.85 % | **0.0000 %** | 0/54 | all length 1 |
| +5.0 % |  8.85 % | **0.0000 %** | 0/54 | all length 1 |
| +7.5 % |  7.55 % | **0.0000 %** | 0/54 | all length 1 |

The technique produces essentially **no wrong decisions** — only erasures,
and never two erasures in a row.

---

## Algorithm

### Notation and parameters

| symbol | meaning | default |
|---|---|---|
| `G_CY` | sampling-loop length, nominal CPU cycles | `40.0` |
| `P_CY[0..7]` | intra-loop slot offsets, nominal cycles, `P_CY[0]=0` | `[0,4,8,12,16,20,26,31]` |
| `κ` | ns per nominal CPU cycle (= `62.5/(1+ε)`) | fitted per capture |
| `t0` | wire time of sample `(0,0)` | fitted per capture |
| `BIT` | wire bit period | `1250.0` ns |
| `h1`, `h0` | effective high time of a `1` / `0` bit | `750.0` / `375.0` ns |
| `NB` | frame bits | `192` (32 hdr + 128 payload + 32 trl) |
| `N_HDR` | leading samples guaranteed inside the header | `112` |
| `T0_LO`,`T0_HI`,`T0_STEP` | coarse `t0` search | `0`, `520`, `4` ns |
| `K_LO`,`K_HI`,`K_STEP` | coarse `κ` search | `57.4`, `68.0`, `0.02` ns/cy |
| `K_WIN`,`K_FINE` | stage-2 `κ` window / step | `0.6`, `0.004` ns/cy |
| `T0_WIN`,`T0_FINE` | stage-2 `t0` window / step | `40`, `2` ns |
| `TRL_MIN` | minimum trailer samples for a valid hypothesis | `40` |
| `NW` | samples considered (frame + margin) | `900` |
| `λ` | LLR per unit margin | from `p_e`, below |
| `I_MAX` | impossible-sample rate that flags low confidence | `0.03` |

`HDR_BITS = bits("FF00AA65")`, `TRL_BITS = bits("9A5500FF")`, MSB-first.
Trailer wire window is `[T_TRL0, T_END) = [200000, 240000)` ns.

### Step 0 — fine grid (each sample is one point constraint)

```
samples -> arrays it[n], sl[n], obs[n]     (chronological, n = 0..NW-1)
u[n]  = it[n] * G_CY + P_CY[sl[n]] + d[sl[n]]      # receiver phase, cycles
t(n | t0, κ) = t0 + κ * u[n]                       # wire time, ns
```

`d[0..7]` is an optional per-slot correction supplied by the calibration
technique (`d = 0` by default, `d[0] ≡ 0` — it is degenerate with `t0`).
If the calibration technique supplies a general monotone warp `w(u)`
(clock stretching), use `t = t0 + κ·w(u)`; nothing else changes.

The predicted wire level for a known bit sequence `B` starting at wire
time `T_lo`:

```
def wire(t, B, T_lo, h1, h0):
    j = floor((t - T_lo) / BIT)                 # bit index
    p = (t - T_lo) - j*BIT                      # phase inside the cell
    return (0 <= j < len(B)) and p < (h1 if B[j] else h0)
```

### Step 1 — coarse header lock (bipolar correlation over `t0 × κ`)

Only the first `N_HDR = 112` samples are used. 112 samples is the largest
count that is still inside the 40 µs header at the **fast** corner
(ε = +8 % ⇒ 137 samples per header) *and* at the slow corner
(ε = −8 % ⇒ 118 samples per header). Score:

```
S_h(t0, κ) = Σ_{n < N_HDR}  0                       if t(n) ∉ [0, 32*BIT)
                            +1 if wire(...) == obs[n]
                            -1 otherwise
(t0_h, κ_h) = argmax over T0S × KS
```

`T0S = arange(T0_LO, T0_HI, T0_STEP)`, `KS = arange(K_LO, K_HI, K_STEP)`.
The `t0 ≥ 0` bound is a hard physical prior: the capture is edge-triggered
on the frame's first rising edge, so sample `(0,0)` cannot precede wire
time 0. (Measured across the 54 real captures: `t0 ∈ [50, 490] ns`.)
Vectorise the inner loop over `t0` (broadcast `t0s[:,None] + κ*u[None,:]`);
one `κ` value costs a single `112 × |T0S|` array op.

### Step 2 — joint lock with the trailer (the long lever arm)

```
def anchor_score(t0, κ):
    t = t0 + κ*u
    m_h = (t >= 0)       & (t < 32*BIT)
    m_t = (t >= T_TRL0)  & (t < T_END)
    if count(m_t) < TRL_MIN: return -inf
    s  = Σ_{m_h} ±1 vs wire(t, HDR_BITS, 0)
    s += Σ_{m_t} ±1 vs wire(t, TRL_BITS, T_TRL0)
    return s

(t0*, κ*) = argmax anchor_score over
            κ ∈ [κ_h - K_WIN, κ_h + K_WIN) step K_FINE
            t0 ∈ [max(0, t0_h - T0_WIN), t0_h + T0_WIN) step T0_FINE
then compass/pattern-search polish: steps (2 ns, 0.02 ns/cy), halve on
failure, stop below 1e-3.
```

Why the two stages are both needed: the header spans 40 µs, so a header-only
fit knows `κ` only to ~0.2 %, which is ±480 ns at the far end of the frame —
four times the placement tolerance (see *Key numbers*). The trailer sits
200 µs away, giving a 6× longer lever; the joint fit reaches
`|Δκ|/κ ≈ 0.002–0.006 %`. The ablation (`e11_ablate.py hdr_only`) confirms
the header alone is unusable: up to **54/54 lock failures** and BER 7–38 %.

A one-bit slip of the trailer would need `Δκ/κ = 1250/240000 = 0.52 %`,
which *is* inside `K_WIN`; it is rejected because such a hypothesis breaks
the header term. Empirically zero slips in 594 synthetic locks.

### Step 3 — per-cell template scoring (128 payload cells)

Payload bit `j = 32..159` (payload index `q = j-32`):

```
lo = j*BIT
M  = { n : lo <= t(n) < lo+BIT }
p  = t(M) - lo                       # phase inside the cell
o  = obs(M)

pred1 = (p < h1);  pred0 = (p < h0)
S1 = Σ (pred1 == o) - Σ (pred1 != o)
S0 = Σ (pred0 == o) - Σ (pred0 != o)

n_dis[q]   = |{ p ∈ [h0, h1) }|      # discriminating samples
margin[q]  = S1 - S0  =  2*( #(discriminating & high) - #(discriminating & low) )
bit[q]     = 1 if margin[q] > 0 else 0
erased[q]  = (n_dis[q] == 0)          # margin is then identically 0
llr[q]     = λ * margin[q]
```

Note the algebra: samples with `p < h0` (both templates say high) and
`p >= h1` (both say low) cancel exactly in `S1 - S0`. Only the
`[h0, h1)` window decides. `margin` is therefore `2·(agree − disagree)`
over the discriminating samples alone, and `|margin|/2 ≤ n_dis`.

Do **not** soften the template edges. A sigmoid template (tested,
`e10_soft.py`, σ ∈ {1, 60, 110, 160} ns) does not help and mildly hurts
(BER 3.78 % → 3.69 % at σ=110 but weak-LLR mass grows 7.7 % → 12.0 %):
the residual phase error is a slowly-varying *deterministic* model error,
not per-sample noise, so a soft edge injects a systematic bias toward `1`
for every sample sitting just below `h0`.

### Step 4 — self-check (no ground truth required)

```
impossible = |{ n in payload cells : p(n) >= h1  and obs[n] == 1 }|
           + |{ n in payload cells : p(n) <  h0  and obs[n] == 0 }|
p_e        = anchor_mismatches / anchor_samples        # from Step 2
confidence = "high" if impossible/NW < I_MAX and p_e < 0.03 else "low"
```

No bit value can be high at phase ≥ `h1`, nor low at phase < `h0`; every
such sample is proof that the grid or the anchor is wrong. Measured:
**0–8 per capture on synthetic data with the correct grid, 41–47 per
capture on real captures with the affine 8-slot grid.** This is the single
most useful number the technique exports.

### Step 5 — output

```
payload_bytes  = pack(bit[0..127])            # MSB-first, 16 bytes
llr[0..127], erased[0..127], n_dis[0..127]
anchor = (t0*, κ*, anchor_score, p_e, impossible)
cell_geometry[q] = list of (sample_index, phase_ns) for cell q
```

---

## Calibration

Everything is estimated per capture except the grid shape and the wire
template, which are global.

**`t0`, `κ` — per capture, from the anchors only (Steps 1–2).** This is the
whole point of the technique: 64 known bits ≈ 256 labelled samples are far
more than the 2 free parameters need. No ground truth, no payload.

**`p_e` — per capture, free.** After the lock, `p_e = (number of anchor
samples whose predicted level disagrees) / (number of anchor samples)`.
This is the channel's own error rate measured on known bits of the *same*
capture. Set

```
λ = 0.5 * log((1 - p_e) / p_e)         # nats per unit margin
```

so `llr[q] = λ·margin[q]` is a genuine log-likelihood ratio. Measured
`p_e`: **0 on synthetic captures with the correct grid; 0.102 on real
captures with the best affine 8-slot grid** (⇒ λ ≈ 1.09).

**`h1`, `h0` — global, from the phase fold.** `h1 = 750 ns` (measured
749.8 / 750.9 / 754.3 on `ones_0/1/2`); `h0 = 375 ns` nominal, with the
anchor-only calibration preferring `390 ns`. Recommend `h1 = 750`,
`h0 = 385` for real captures. When scoring against `synth.py`, use
`synth.T1H_NS = 700`, `synth.T0H_NS = 350` instead — the generator and the
hardware disagree and a template/generator mismatch alone costs ~2 % BER.
Optionally refit `h1, h0` per capture by adding them to the Step-2 search
(±40 ns, 10 ns steps); on real captures this moves `h0` by up to +40 ns and
gains ~0.5 % anchor agreement.

**`G_CY`, `P_CY`, `d[]` — global, from the calibration technique.** Load
`approaches/dev_calibration/fitted_model.json` if present and convert its
ns offsets to nominal cycles (`P_CY[s] = o[s]/62.5`, `G_CY = G/62.5`).
If it is not available, this technique can calibrate the grid **itself,
without ground truth**, by maximising the *summed anchor score across
captures* (`e13_anchorcal.py`): coordinate ascent on `P_CY[1..7]`, `G_CY`,
`h1`, `h0` with `(t0, κ)` refit per capture at every evaluation. That
objective raised anchor agreement 89.44 % → 90.08 % and converged to

```
G_CY = 40.0    P_CY = [0, 3.125, 8, 12, 16, 20, 26, 29]
gaps(cy) = [3.125, 4.875, 4, 4, 4, 6, 3, 11]   h1 = 750   h0 = 390
```

i.e. the ~3 undocumented cycles are **not all** in the slot7→slot0 gap: the
fit moves ~1 cycle out of the slot0→slot1 gap and puts 11 cycles in the
end-of-loop gap. `e14_resid.py` localises the remaining residual: anchor
mismatch by slot is **s0 22.1 %, s5 15.0 %, s6 11.7 %, s7 10.4 %**, versus
**s1 1.7 %** and s2–s4 6–8 %; by phase inside the cell it concentrates in
the bins straddling 0, `h0` and `h1` (23 %, 14 %, 12–14 %) versus 1–4 %
elsewhere. Conclusion for the calibration technique: **the residual is a
per-slot phase error, dominated by slot 0 and the three end-of-loop slots,
not a structural failure of the affine model.** Give those four slots the
most freedom.

**`N_HDR`** is derived from the widest ε to be supported:
`N_HDR = floor(32·BIT / (κ_slowest · G_CY/8))` minus a few samples;
112 covers ±8 %.

**Search ranges.** `K_LO/K_HI` must cover the design envelope:
`62.5/1.08 = 57.9` to `62.5/0.92 = 67.9`; use `[57.4, 68.0]`.
Real captures all landed in `κ ∈ [62.39, 62.89]` (loop 2495.6–2515.4 ns,
median 2497.3 ns). Note `harness.LOOP_NS = 2507.3` is ~0.4 % above this
median — do not seed from it.

---

## Envelope behavior

Measured with `synth.py` at ε ∈ {−8, −7.5, −5, −2.5, −1, −0.3, 0, +1,
+2.5, +5, +7.5, +8} %, 54 captures per point (`e9_envelope.py`,
`e11_ablate.py`).

**Anchor lock holds across the entire envelope and one point past each
corner.**

| ε | \|Δt0\| | \|Δκ\|/κ | \|end-of-frame placement error\| | lock failures |
|---|---|---|---|---|
| −7.5 % | 6.9 ns | 0.0022 % | mean 2.0 ns, max 3.9 ns | 0 / 54 |
| −0.3 % | 4.6 ns | 0.0022 % | mean 3.0 ns, max 5.1 ns | 0 / 54 |
| +7.5 % | 4.4 ns | 0.0061 % | mean 16.6 ns, max 20.6 ns | 0 / 54 |

Against a tolerance of ~±20 ns (below) this is comfortable but not lavish
at the fast corner.

**Slow corner (ε = −7.5 %, the hard one).** The gap vector stretches:

```
ε = +7.5 %  gaps(ns) = [232.6 ×5, 348.8, 290.7, 523.3]   loop 2325.6
ε =  0.0 %  gaps(ns) = [250.0 ×5, 375.0, 312.5, 562.5]   loop 2500.0
ε = −7.5 %  gaps(ns) = [270.3 ×5, 405.4, 337.8, 608.1]   loop 2702.7
```

At −7.5 % the end-of-loop gap (608 ns) exceeds both T0H (375 ns) and T1L
(500 ns), so *both* swallowing and 1-bit merging get worse — exactly as
`HSI_TEMPERATURE.md` predicts. **This technique is indifferent to both.**
What it *does* feel is that the widening gap more often covers the entire
375 ns discriminating window `[h0, h1)`, which is what an erasure is:

| ε | −7.5 % | −5 % | −2.5 % | −0.3 % | +2.5 % | +5 % | +7.5 % |
|---|---|---|---|---|---|---|---|
| erasure rate | 11.72 % | 10.42 % | 9.38 % | 7.29 % | 8.85 % | 8.85 % | 7.55 % |
| BER (decidable) | 0.00 % | 0.00 % | 0.00 % | 0.31 % | 0.00 % | 0.00 % | 0.00 % |
| exact frames | 6/54 | 6/54 | 6/54 | 10/54 | 6/54 | 9/54 | 8/54 |

Erasure rate grows ~4.4 points from the fast corner to the slow corner —
a graceful, fully predictable degradation. **At every ε the erasure runs
are all of length 1**: because the loop is ≈2 bit periods, consecutive
cells never both lose their discriminating window. That guarantee is
what makes the erasures cheap for a downstream technique to fill.

**Anchors survive the slow corner because they are over-determined.** Each
anchor carries **36–48 discriminating samples** (median 36–41 across ε) for
32 known bits. Two ablations:

* `hdr_no00` — the eight header `00` bits are *deleted from the template*:
  results are indistinguishable from the full joint lock (0/54 lock
  failures, BER-decidable 0.00 % at ±7.5 %, erasure 12.50 % vs 11.72 % at
  −7.5 %). **Swallowed pulses inside the header's `00` byte cost nothing.**
  Given that 8.6 % of real header-`00` pulses actually do vanish and 2 of
  54 captures lose four of the eight, this is the decisive robustness
  result.
* `hdr_only` — trailer removed: 0–54 lock failures per ε point, mean
  end-of-frame error 55–548 ns, BER-decidable 7.2–37.5 %. The global
  anchoring is mandatory, not an optimisation.

**Within-capture drift.** `synth.py`'s ±0.2 % linear ramp at ε = −7.5 %:
erasures unchanged (11.72 %), BER-decidable 0.31 % → **1.75–2.37 %**,
impossible-sample count 0.6 → 4.7–6.0 per capture. A 2-parameter affine map
cannot represent a ramp; adding a quadratic term `t = t0 + κ(u + β u²/U)`
was tried and **does not work** — with the only labelled data at the two
ends of the frame, β is nearly unobservable (fitted β ≈ 3e-5 against a true
0.002, BER-decidable 2.37 % → 1.86 %). Drift must come from elsewhere; see
*Composition interface*.

---

## Failure modes

**1. Erasures are irreducible for this technique — 7.3 % to 12.5 % of
payload bits.** If no sample lands in `[h0, h1)` inside a cell, the wire
was literally never observed at a time where a `0` and a `1` differ. No
amount of scoring recovers it. That is 9–16 bits per frame; spread over
16 bytes almost every byte carries one. Exact-frame rate for this
technique **alone** is therefore 6–10 / 54 even with a perfect grid and a
perfect anchor. It cannot be the last stage of the pipeline.

**2. On real captures the technique is grid-limited, badly.** With the best
affine 8-slot grid I could fit, **10.24 % of the 13816 anchor samples still
mismatch**, and the payload result collapses to erasures 8.25 %,
BER-decidable **15.25 %**, exact 5/54, impossible 46.6 per capture
(`e13_anchorcal.py`). The same code on `synth.py` — identical algorithm,
correct grid — gives BER-decidable 0.00 % and impossible ≈ 0. Every one of
those 15 percentage points is grid error, not technique error. This
technique's real-capture value is unlocked only by whatever slot model the
calibration effort lands on; conversely it is a very sharp instrument for
*measuring* that model (§ Composition).

**3. Per-capture slot fitting from the anchors alone is not enough.**
Fitting `d[1..7]` per capture on the 256 anchor samples (`e12_real.py`)
gave BER-decidable 22.1 % — worse than a good global grid. 256 samples
over-fit 7 offsets. Fit the grid globally, across captures.

**4. Within-capture clock wander.** ±0.2 % costs ~2 % BER on decidable
cells and cannot be estimated from the anchors (see above).

**5. Ties inside decidable cells.** `margin[q] == 0` with `n_dis > 0` means
the discriminating samples contradict each other — only possible when the
grid or anchor is wrong. On real captures this is not rare; the hard
decision then falls to the `>0` tie-break (biased to `0`) and should
instead be reported as an erasure with `llr = 0`. Implementers: treat
`margin == 0` as erased regardless of `n_dis`.

**6. Out-of-range ε.** If the true ε falls outside `[K_LO, K_HI]` the
stage-1 argmax pins to a range edge and everything downstream is garbage.
The `impossible` counter catches it (it goes to tens of percent), but the
technique has no recovery of its own.

**7. Anchor-window assumption.** `N_HDR` and the trailer wire window assume
the frame is exactly 192 bits starting at wire time 0 and the buffer is long
enough. That is safe here (frame ends at loop ~95 of 640) but is not a
general property.

**8. Degenerate ε = 0.** At exactly ε = 0 the loop is exactly 2 bit periods,
sample phases are static and the erasure rate drops to 0 (54/54 exact in
`e11_ablate.py`). Do not read that row as a performance claim — it is a
commensurability artifact that real hardware never hits (real captures sit
at loop 2495.6–2515.4 ns, i.e. ε ≈ −0.6 % … +0.2 % relative to 2500 ns).

---

## Composition interface

**Pipeline position: stage 2 of 3 — after grid calibration, before erasure
filling.** This technique owns *global time*; it should be the only place
where `(t0, κ)` is decided, and every other technique should consume its
map rather than re-deriving one.

### Inputs it needs

| input | source | fallback |
|---|---|---|
| `G_CY`, `P_CY[8]`, optional `d[8]` | calibration technique (`fitted_model.json`) | nominal `[0,4,8,12,16,20,26,31]`, `G=40` |
| optional monotone warp `w(u)` | `clock_stretch` | identity |
| `h1`, `h0` | global constants (750 / 385) | refit in Step 2 |
| raw `(it, sl, obs)` | harness | — |

### Outputs it provides

1. **`(t0*, κ*)` — the global affine time base**, accurate to
   `|Δt0| ≈ 5 ns` and `|Δκ|/κ ≈ 0.003 %` when the grid is right. Every
   other technique should use `t(n) = t0* + κ*·u(n)` instead of its own
   estimate; this alone removes "clock stretching" as a separate problem
   for `edge_dp`, `missed_zero`, `boundary_model` and
   `histogram_adaptive`.
2. **128 bit-cell posteriors** `llr[q] = λ·margin[q]` with
   `λ = ½·log((1−p_e)/p_e)`, `p_e` measured on the same capture's anchors.
   These are proper LLRs and can be summed with any other technique's
   independent LLRs.
3. **An erasure mask** `erased[q]` and its cause `n_dis[q] == 0`. Crucially,
   this mask is **computable from geometry alone, before looking at the
   data** — it is a function of `(t0*, κ*, G_CY, P_CY, h0, h1)` only. Hand
   it forward as a *work list*: "these 9–16 cells are the only ones anybody
   needs to argue about."
4. **Per-cell sample geometry** `cell_geometry[q] = [(n, phase_ns), …]`, and
   for erased cells the exact unobserved sub-interval of the cell. A
   pulse-width or edge-based technique can use that to reason about total
   high time without re-deriving timing.
5. **Grid-quality metrics**: `anchor_score`, `p_e`, `impossible`. These are
   ground-truth-free.

### Constraints it can enforce

* **Frame geometry**: the first payload bit starts at wire time
  `32·1250 = 40000 ns` and the last ends at `200000 ns`, both known to
  ±20 ns. Any technique proposing a bit boundary outside that map is wrong.
* **Impossible-sample veto**: a candidate payload assignment that requires a
  sample at cell phase ≥ `h1` to read high, or at phase < `h0` to read low,
  is inconsistent with the anchor and must be rejected (or must force an
  anchor re-lock).
* **Erasure isolation**: no two adjacent payload cells are ever both erased
  (measured: every erasure run has length exactly 1, at every ε from −7.5 %
  to +7.5 %). A downstream search over erasure fillings therefore never
  needs to consider adjacent-pair ambiguity — the neighbours of an erased
  cell are always hard-decided.

### How it should combine with the other five

* **`calibration`** → this technique. Consume the fitted slot model. In
  return, offer the *anchor score* as a ground-truth-free calibration loss
  (`e13_anchorcal.py` shows it works end-to-end) and the per-slot mismatch
  breakdown (`s0 22.1 %`, `s5 15.0 %`, `s6 11.7 %`, `s7 10.4 %` vs `s1
  1.7 %`) as the diagnostic that says *which* slots still need freedom.
  Getting anchor mismatch from 10.2 % to ~1 % is worth ~15 points of BER.
* **`clock_stretch`** ↔ this technique, iteratively. It cannot see drift
  (only two anchors, both at the ends); `clock_stretch` can, using
  payload-derived edges. Loop: matched_filter locks `(t0, κ)` → publishes
  bit-cell boundaries → `clock_stretch` proposes a warp `w(u)` →
  matched_filter re-locks on the warped grid and reports whether
  `impossible` went down. That counter is the referee.
* **`missed_zero`** → fills erasures. Its whole subject (a swallowed T0H
  leaves only a long low gap) is precisely the erased-cell population here,
  and it now gets them as an explicit, short, non-adjacent list with exact
  timing context instead of having to find them.
* **`edge_dp`** → independent evidence. Run it on the same `(t0*, κ*)` map
  and sum its per-bit LLRs with these. Its strength (transition timing
  between cells) is orthogonal to this technique's weakness (no sample in
  the discriminating window), because an erased cell's *neighbours* are
  always decided, so the edge structure around it is pinned.
* **`histogram_adaptive`** → supplies better `h1`, `h0` (and their spread)
  from the observed phase distribution; this technique consumes them
  directly as template parameters. Feed it the folded phase histogram
  computed at `(t0*, κ*)` — the fold in `e6_fold.py` is exactly the input
  it wants and is much cleaner once globally anchored.
* **`boundary_model`** → refines `P_CY` near the end-of-loop gap, which is
  where all the erasures come from. Every cycle it moves out of that gap
  converts erasures into decisions; the erasure rate is a direct scoreboard
  for it (7.3 % at bench, and geometrically `≈ (end_gap − (h1−h0)) / loop`).

**Recommended combination rule.** Take the anchor and cell geometry from
this technique as fixed. Sum LLRs from `matched_filter`, `edge_dp` and
`missed_zero` per bit. Decide bits with `|LLR| > τ`; for the remaining
(erased) cells run a constrained search — at most ~16 cells, never
adjacent — scored by total sample agreement under the same fine grid,
with the `impossible`-sample veto applied. That search is what turns
6–10/54 into a high exact-match rate.

---

## Key numbers

Constants and measurements the implementer should reuse verbatim.

**Time base**

| quantity | value | source |
|---|---|---|
| loop length | `G_CY = 40.0` nominal CPU cycles | fit, `e13` |
| slot offsets (nominal seed) | `[0, 4, 8, 12, 16, 20, 26, 31]` cycles | doc + 3 extra cycles in end gap |
| slot offsets (anchor-calibrated) | `[0, 3.125, 8, 12, 16, 20, 26, 29]` cycles | `e13_anchorcal.py` |
| inter-sample gaps (calibrated) | `[3.125, 4.875, 4, 4, 4, 6, 3, 11]` cycles | `e13` |
| gaps in ns at ε=0 | `[250, 250, 250, 250, 250, 375, 312.5, 562.5]` | `e8` |
| gaps in ns at ε=−7.5 % | `[270.3 ×5, 405.4, 337.8, 608.1]`, loop 2702.7 ns | `e8` |
| gaps in ns at ε=+7.5 % | `[232.6 ×5, 348.8, 290.7, 523.3]`, loop 2325.6 ns | `e8` |
| `κ` on the 54 real captures | 62.39 … 62.89 ns/cycle, median **62.43** | `e2`, `e14` |
| loop period, real captures | 2495.6 … 2515.4 ns, median **2497.3 ns** | `e2`, `e14` |
| `harness.LOOP_NS` | 2507.3 ns — **~0.4 % high**, do not seed from it | — |
| `t0` on real captures | 50 … 490 ns (hard prior: `t0 ≥ 0`) | `e12`, `e14` |

**Wire template**

| quantity | value |
|---|---|
| bit period | 1250.0 ns (exact) |
| `h1` measured by phase fold | **750.9 / 749.8 / 754.3 ns** → use **750** |
| `h0` | nominal 375; anchor-cal prefers **390**; recommend **385** |
| discriminating window width `h1−h0` | 365–375 ns |
| edge smear seen in the fold | ~150 ns (model error, not noise — keep the template hard) |
| `synth.py` uses | 700 / 350 — mismatch costs ~2 % BER, switch templates when scoring against it |

**Anchors**

| quantity | value |
|---|---|
| `N_HDR` (samples safely inside the header) | **112** (118 at ε=−8 %, 137 at ε=+8 %) |
| samples per anchor window | ~128 |
| discriminating samples per anchor | **36–48** (median 36–41) |
| anchor accuracy, correct grid | `|Δt0| = 4.4–6.9 ns`, `|Δκ|/κ = 0.0022–0.0061 %` |
| end-of-frame placement error | mean 2.0–16.6 ns, max **20.6 ns** |
| lock failures over 12 ε points × 54 captures | **0** |
| header-only lock, end-of-frame error | 55–548 ns (up to 54/54 failures) — unusable |
| anchor mismatch rate, real captures, best affine grid | **10.24 %** (1415/13816) |
| anchor mismatch by slot (real) | s0 22.1, s5 15.0, s6 11.7, s7 10.4, s2–4 6–8, **s1 1.7 %** |

**Placement tolerance** (`e15_tol.py`, BER among decidable cells versus a
deliberate anchor offset; ε ∈ {−7.5, −0.3, +7.5} %):

| anchor offset | ≈0 ns | ±20 ns | ±40 ns | ±60 ns | ±160 ns |
|---|---|---|---|---|---|
| BER (decidable) | 0–1.6 % | ~1–3 % | 3–6 % | 10–13 % | 25–39 % |
| `Δκ/κ` | 0 | — | 0.05 % → 2–4 % | — | 0.10 % → 5–18 % |

**Cell statistics**

| quantity | value |
|---|---|
| samples per bit cell | 3 (4133), 4 (2106), 5 (4126) — strict 3/5 alternation |
| erasure rate (`n_dis == 0`), ε = −7.5 → +7.5 % | **11.72 % → 7.55 %** (7.29 % at bench) |
| erasure run lengths | **always exactly 1**, at every ε |
| erasures per frame | 9–16 of 128 |
| BER among decidable cells, correct grid | **0.00 %** (0.31 % at ε=−0.3 %) |
| BER among decidable cells, real captures, affine grid | 15.25 % (grid-limited) |
| impossible samples per capture | **0–8** (correct grid) vs **41–47** (real, affine grid) |
| exact frames, this technique alone, correct grid | 6–10 / 54 |
| effect of ±0.2 % within-capture drift | BER-decidable 0.31 % → 1.75–2.37 %; impossible 0.6 → 4.7–6.0 |

**Artifact rates on real captures** (context for the other techniques)

| quantity | value |
|---|---|
| 0-bits with zero high samples | 171 / 5505 = 3.11 % |
| 1-bits with zero high samples | 30 / 4863 = 0.62 % |
| header `00` byte: zero bits with no high sample | 37 / 432 = **8.6 %** |
| captures losing ≥1 of the 8 header-`00` pulses | **19 / 54** (two lose 4 of 8) |
| merged adjacent `11` pairs | 551 / 2931 = 18.8 % |
| worst frame-bit positions | 191, 15, 14, 13, 12, 179, 181 (the two `00` bytes' tails) |
