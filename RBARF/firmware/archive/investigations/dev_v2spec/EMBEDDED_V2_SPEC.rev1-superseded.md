# Embedded Decoder v2 — Specification

WS2812 receiver for the STM8S001J3. This document specifies the **v2**
on-chip decoder: the v1 pipeline (`approaches/embedded_ref.py`,
`approaches/dev_embedded/decoder.c`) with the byte-period **votes**
machinery and the second sampler model **removed**, and a **CRC-guided
confidence chase** added in their place.

Scope: precise enough to implement from. Every number is either measured
(cited to its source) or derived here with the derivation shown. Items
marked **(est.)** are engineering estimates, not measurements, and are
flagged as such wherever they appear in a budget.

Status of the inputs:

| Input | Source | Role here |
|---|---|---|
| v1 algorithm, ablations, budgets | `EMBEDDED_FEASIBILITY.md` | baseline; every "cost of removal" cites its §2 table |
| v1 fixed-point contract | `approaches/embedded_ref.py` header | carried forward verbatim in §4 |
| sampler timing model | `DATASET.md` ADDENDUM, `HSI_TEMPERATURE.md` | unchanged; hard-coded integer cycles |
| trim → eps map | `TRIM_SWEEP.md` | §10 auto-trim hygiene only |
| CRC block v2.1 | project owner, FIXED | §2, not redesigned |

New measurements made for this spec (scratch in
`approaches/dev_v2spec/`, no existing file modified):

| Script | What it establishes |
|---|---|
| `crc_vectors.py` | CRC test vectors; CRC8/CRC16 difference-linearity (4000/4000) |
| `syn_pow.py` | closed-form syndrome `x^j mod g` (§7.2), verified 0/4000 mismatches |
| `budget.py` | capture-buffer sizing, trial counts, cycle scaling |
| `syndrome.py`, `chase_sim.py`, `chase_sim2.py` | chase outcome rates, false-accept counts |
| `containment.py`, `correlate.py` | **votes-cut decode of the 54-capture and 96-capture trim corpora**: are the wrong bits reachable by the chase, and are repetitions independent? |

---

## 1. What changes, in one table

| | v1 (measured) | v2 (this spec) |
|---|---|---|
| wire payload | 16 B test / 48 B prod | **+3 B check block** → 19 B / 51 B |
| frame | 24 B / 56 B (192 / 448 bits) | **27 B / 59 B (216 / 472 bits)** |
| capture buffer | 256 B | **288 B** (prod) / 128 B (test) — §3 |
| bit-error correction | dead-window + knife byte-period **votes**, unverified | **CRC8 confidence chase**, every emitted payload CRC-checked |
| second sampler model | absent (single fitted geometry) | absent, and formally closed — §5.3 |
| decoder DATA | 781 B, overlay mandatory | **≈ 650 B**, overlay optional — §9 |
| decoder flash | 7.8 KB (2.30 KB over budget with app) | **≈ 7.13 KB** (1.63 KB over) — §8 |
| decode cycles | ~4.4–4.8 M ucsim ticks | ~4.4–4.8 M ticks (unchanged) — §8.3 |
| silent wrong payload | **measured 1/96 on the trim corpus** (63 wrong bits, passed every v1 gate) | bounded by ≤ 93·2⁻²⁴ ≈ 5.5·10⁻⁶ per chased frame — §7.5 |
| exact delivery, bench corpus | 51/54 unverified | **≈ 52.7/54 CRC-verified** (§6.4) |

The headline: v2 trades a heuristic bit-repair mechanism for a *checked*
one. It is smaller, no slower, and — measured on the same 54 captures —
recovers **more** frames than the votes it replaces, with every recovery
verified rather than asserted.

---

## 2. Wire format v2.1 (FIXED — normative, do not redesign)

### 2.1 Frame

```
HEADER(4)  = FF 00 AA 65          unchanged
PAYLOAD'   = DATA(ND) || CRC16_HI || CRC16_LO || CRC8      (ND+3 bytes)
TRAILER(4) = 9A 55 00 FF          unchanged
```

Bytes MSB-first. Line idles low before the frame and latches low after.

| build | ND | NP' = ND+3 | frame bytes | NB (bits) |
|---|---|---|---|---|
| test / dataset | 16 | 19 | 27 | **216** |
| production | 48 | 51 | 59 | **472** |

The check block is **LED-like**: three ordinary payload bytes on the
wire, indistinguishable to the sampler, subject to the same bit errors,
and therefore themselves chase-eligible (§7.2).

### 2.2 CRC definitions

**CRC16 = CRC-16/CCITT-FALSE**, poly `0x1021`, init `0xFFFF`, no input
or output reflection, no xorout. Computed over the **DATA bytes only**
(ND bytes). Transmitted big-endian: `CRC16_HI` then `CRC16_LO`.

**CRC8**, poly `0x07`, init `0x00`, no reflection, no xorout. Computed
over **DATA || CRC16_HI || CRC16_LO** (ND+2 bytes) — one CRC8 check
therefore covers the whole payload including the CRC16 field.

Reference implementations (bit-serial, table-free) and the on-chip forms
are in §7.1.

### 2.3 Test vectors (computed, `dev_v2spec/crc_vectors.py`)

Standard check value, message `"123456789"`:
`CRC16 = 0x29B1`, `CRC8 = 0xF4`.

Test build, `DATA = 00 01 … 0F`:

```
CRC16 = 0x3B37   CRC8 = 0xA5
payload'(19) = 000102030405060708090A0B0C0D0E0F 3B37 A5
frame(27)    = FF00AA65 000102030405060708090A0B0C0D0E0F 3B37A5 9A5500FF
```

Production build, `DATA[i] = (5·i) & 0xFF`, i = 0…47:

```
CRC16 = 0xE8D8   CRC8 = 0x87
payload'(51) = 00050A0F…E1E6EB E8D8 87
```

These three vectors are normative build-time self-tests: the firmware
must reproduce them at NP' = 19 and NP' = 51 before shipping.

### 2.4 Repetition

Each logical frame is transmitted **3×**, spaced ≥ 500 ms. Receivers
treat **any** CRC-valid copy as delivery. There are no sequence numbers
and no de-duplication: application of a payload must be **idempotent**
(a GRB payload is a state, not a delta — this holds for the current
application). Two *different* logical frames must not be sent inside one
500 ms window, since the receiver cannot order them.

Do not model the 3 copies as independent trials. §11.3 measures the
correlation directly and it is large.

---

## 3. Frame geometry constants and capture-buffer sizing

Time unit **TU = BIT / 2⁹ = 1250 / 512 ns = 2.4414 ns** (unchanged;
`EMBEDDED_FEASIBILITY.md` §3 measured that TU = BIT/128 loses the (5,6)
knife boundaries to quantization).

| constant | test (NB=216) | prod (NB=472) | formula |
|---|---|---|---|
| `NB` | 216 | 472 | 8·(8 + NP') |
| `W_U` (wire span, seed) | 110 388 | **241 460** | (NB−1)·512 + H1P, H1P = 308 |
| `Y_END` | 111 268 | **242 340** | 512 + NB·512 + 164 |
| `NBB` (bitmap bytes) | 27 | **59** | NB/8 |
| capture buffer `NCAP` | **128** | **288** | below |

### 3.1 Why 256 bytes is no longer enough

The v1 sizing (`EMBEDDED_FEASIBILITY.md` §1) is reproduced exactly by
`loops(nbits, ε) = nbits·1250 / (2500/(1+ε))` plus a **1.08-loop
accounting slack** for `t0` and trailing-fall detection (this slack is
what turns the computed 241.9 into the report's 243 at +8 % for 448
bits — `dev_v2spec/budget.py` recovers it to 0.01 loops).

| frame | nominal | −7.5 % | +7.5 % | +8 % (with slack) |
|---|---|---|---|---|
| v1 prod, 448 bits | 224.0 | 207.2 | 240.8 | **243.0** |
| **v2 prod, 472 bits** | 236.0 | 218.3 | 253.7 | **256.0** |
| v2 test, 216 bits | 108.0 | 99.9 | 116.1 | 117.7 |

The check block puts the fast corner at **exactly 256.0 loops** — zero
margin in a 256-byte buffer. This is not a rounding argument to wave
away: at +8 % a 256 B buffer truncates the trailer, the endpoint seed
loses `mid_fl`, and the decode fails wholesale.

| buffer | margin at +8 % |
|---|---|
| 256 B | **0.0 loops (0 µs)** — unusable |
| 272 B | 16.0 loops (37 µs) |
| **288 B** | **32.0 loops (74 µs)** — specified |
| 320 B | 64.0 loops (148 µs) |

**`NCAP = 288` for the production build** (not a power of two; indexing
is linear `cap[i]`, `ncap` is a runtime argument, so this costs nothing).
The slow corner needs 219 loops, so 288 covers the whole ±8 % span.

**`NCAP = 128` for the test build** (10.3 loops ≈ 24 µs at +8 %). If the
test build must also be validated at the fast corner, use 144.

`LATCH_RUN = 200` consecutive low samples is unchanged and remains the
only other clock-sensitive sizing.

---

## 4. Fixed-point contract (carried forward unchanged)

From the `embedded_ref.py` header, with the production ranges re-checked
against NB = 472 and NCAP = 288:

| quantity | format | range / units | v2 re-check |
|---|---|---|---|
| `t` receiver time | u16 | CPU cycles | 288 loops · 40 + 32 = 11 552 ✓ |
| `K` clock scale | u16 Q11 | TU/cycle, nominal `K_NOM = 52429` | ✓ |
| `t·K` | **u32** | ≤ 11 552 · 60 000 = 6.9·10⁸ < 2³¹ ✓ | ✓ |
| `y` mapped wire time | **u32** | TU; `Y_END` = 242 340 | exceeds u16 — u32 mandatory |
| `tau` lock offset | s16 | TU | ✓ |
| `u`, `v` fall bracket | s16 | TU, relative to the bit lattice | ✓ |
| `h0c`/`h1c`/`theta`/`eps` | s16 | TU | ✓ |
| `Se` residual sums | **s32** | ≤ 242 pulses · 256 TU | ✓ |
| `Sy` position sums | **u32** | ≤ 242 · 242 340 = 5.9·10⁷ | ✓ |
| `K·de`, seed dividend | **s32** | see `_seed`/`_refine` | ✓ |
| per-bit margin `m` | **u8** | TU, saturating at 255 | new, §6.1 |
| CRC8 residual / syndrome | u8 | GF(2) | new, §7 |
| CRC16 residual / syndrome | u16 | GF(2) | new, §7 |

Sampler model constants (`dev_calibration/fitted_model.json`, exact
integer cycles, **unchanged**): `LOOP_CY = 40`,
`O_CY = [0,4,9,13,17,21,27,32]`, `W_CY = [0,−1,0,+2,0,0,0,+1]`,
`H0P = 154` (377 ns), `H1P = 308` (752 ns), `BIAS_U = 512`,
`TAIL_U = 164`.

`OADJ_U[]` — the optional per-slot sub-cycle tweak table — is **deleted**
(§5.3), not merely zeroed.

Divisions per decode: ~10 (lock + calibration), unchanged. The chase
introduces **no divisions and no multiplications** (§7.3).

---

## 5. Pipeline

### 5.1 Stages KEPT unchanged

| Stage | Function(s) in `decoder.c` | Contract |
|---|---|---|
| **S0** model clock `A[m]` | `ps_next` | exact integer cycles: `t = i·40 + O_CY[s] + Σ W_CY[j]·(HIGH reads so far)`. Causal, computable while streaming. **Any edit to the capture loop invalidates this** — see §12.4. |
| **S1** run → rise/fall brackets | `ps_next` | forward-only, O(1) state, no pulse array ever materialised |
| **P1** endpoint seed | `seed` | `K = (W_U << 11) / span`, `span = mid_fl − mid_r0`; `tau = BIAS_U − ((mid_r0·K) >> 11)`. Guard `K_MIN=46000 ≤ K ≤ K_MAX=60000`. |
| **P2** lock refine ×2 | `refine` | nearest-lattice residuals of rise-bracket midpoints, two-half-mean regression → `(dk, dtau)`. Unchanged, including the documented *rejections*: an interval-censored mean residual collapses (measured 21/54) and the Hough polish is net-negative (`EMBEDDED_FEASIBILITY.md` §3). |
| **S3** gap-accounting segmentation | `ss_next` | exact integers, `(Δy + 256) >> 9` |
| **P3** marker calibration + eps analog | `calibrate`, `cal_add`, `cal_cloud`, `theta56`, `label_interval` | interval-intersection width fit + the 64-bin fold histogram per razor family (5,6)/(6,7). **The single most valuable mechanism** — ablation `eps off: 46/54 (−7)`. Untouched. |
| **P4** hinge decision | `decide`, `hinge`, `a_bounds` | interval hinge (compare-only), tie-break *least cost → interior-before-grazing → fewer ones*. The interior rule decides rnd3_2's last knife bit; keep it. |
| **S6** assembly + marker forcing | `a_bounds` from the KNOWN template (flash const) | template is now 59 bytes; `known_bit(t)` covers t < 32 and t ≥ NB−32 |
| **S8c** honest refusal gates | `ws_decode` | `violations > 0`, `infeasible > 4`, `label_err > 6`, **with** the dead-marker-window adaptation (a window with both hypotheses interior carries no evidence and must not count as a label error — without it the entire +5…+7.5 % corner refuses wholesale) |

### 5.2 Stage REMOVED — the votes machinery

**Removed:** `votes()`, `is_knife()`, `is_resolved()`, the `d_conf` and
`d_tied` bitmaps, `d_knife[32]`, `d_resolved[16]`, and the per-lag
byte-periodicity proof (`KNIFE_PAIR_MIN`, `KNIFE_AGREE_PCT`,
`DEAD_VOTE_MIN`, `CONF_M`, `KNIFE_M` constants).

**Measured cost of removal** (`EMBEDDED_FEASIBILITY.md` §2 ablations,
baseline 53/54):

| ablation | exact/54 | Δ |
|---|---|---|
| dead-window vote off | 51 | −2 |
| knife vote off | 47 | −6 |
| **both votes off** | **45** | **−8** |

Independently reproduced here: running `embedded_ref` with
`VOTES = False` over all 54 captures gives **45/54 exact**
(`dev_v2spec/containment.py`) — an exact match to the ablation battery,
which validates the instrumented copy used for the rest of §6.

**Why this is nonetheless the right cut.** The votes flipped bits on the
strength of a *periodicity heuristic* with no verification: their gate
proves that lags 8/16 are consistent among confident bits, then applies
that consistency to an uncertain bit. On a random 448-bit production
payload the periodicity assumption is simply false, and the report
already records the gating fix that was needed after an ungated dead
vote flipped three bits on coincidentally unanimous siblings. The chase
performs the same class of repair — flip the least-confident bits — but
**accepts a repair only if a CRC agrees**, so a wrong repair becomes a
refusal instead of a silent error. §6.4 shows it also recovers *more*
captures than the votes did.

### 5.3 Stage REMOVED (formally closed) — the second sampler model

The host's dual sampler model ("cal" + "fit" arbitration) is **not** in
the v2 decoder, and the `OADJ_U[]` hook that would have allowed a static
transplant is deleted.

**Measured cost** (`EMBEDDED_FEASIBILITY.md` §2):

| variant | exact/54 |
|---|---|
| host dual-model arbitration | 53 |
| fit-only | 50 (−3) |
| cal-only | 53 |
| **static per-slot offset transplant (`OADJ_U` populated)** | **35 (−18)** |

The embedded final config lands at 51/54 with the fit geometry plus the
eps analog, i.e. the architecture loss is **−1 capture vs the host**
(class: `nibbles_1`, where truth-0 sits at u = 150 and truth-1 at u = 148
*in the same capture* — not linearly separable in a single geometry).
The report is explicit that no single-geometry decoder recovers this and
that the static-table route is actively harmful.

**Flash consequence:** removal saves ~30 B measured (the two `OADJ_U`
additions in `ss_next`) — the machinery was never built. Its real value
is *foreclosure*: adding a second geometry would need a second
calibration state set and an arbitration pass, an estimated **+0.6…1.0 KB
(est.)** against a budget already 1.63 KB over (§8). The −1 capture is
accepted and handed to the 3× repetition.

### 5.4 Stage REMOVED — self-training second pass

Already off in v1 (`SELF_TRAIN = False`, measured **0** change on all 54
real and 18 production-size synthetic decodes) and absent from the C
build. Stays out. Confirmed here only so that no implementer re-enables
it: it costs 2 of 7 capture scans for nothing.

### 5.5 Stage ADDED — CRC-guided confidence chase

New stages, in `ws_decode` order: candidate collection (folded into
`decide_pass`, §6.1) → residual computation (§7.1) → syndrome walk
(§7.2) → bounded enumeration (§7.3) → verify and emit (§7.4).

---

## 6. Decision pass changes — from votes to a candidate list

### 6.1 The margin becomes a first-class output

`decide_pass` already computes, for every bit `t` in a segment, the
quantity the votes used only as a 1-bit confidence flag:

```
c1m = min{ costs[a] : lo ≤ a ≤ hi, a >  off }
c0m = min{ costs[a] : lo ≤ a ≤ hi, a ≤ off }
m   = 255                     if c0m or c1m does not exist
    = min(255, |c0m − c1m|)   otherwise            # u8, saturating
```

`m` is the interval-hinge analog of `|LLR|`: the cost a bit must pay to
flip. In v1 it was thresholded (`m ≥ CONF_M` → `conf[t] = 1`) and
discarded. In v2 it is **ranked**.

Two adaptations, which is how the two votes' value is preserved without
the votes:

1. **Dead-window ties → margin 0.** The v1 predicate is unchanged: within
   a segment, collect `ins` = the hypotheses `a ∈ [lo, hi]` that are
   *interior* (`u < h ≤ v`); if `|ins| ≥ 2` and `a_hat ∈ {ins[0], ins[1]}`,
   the bit at `t = k0 + ins[0]` is a dead-window tie. v1 set
   `tied[t] = 1`; **v2 sets `m := 0`**, which forces the bit to the head
   of the candidate list. This carries the dead-window vote's −2
   captures into the chase at zero code cost.
2. **Knife bits need no special case.** A knife bit is by construction a
   single-bit (5,6)/(6,7)-family pulse with `|costs[0] − costs[1]| <
   KNIFE_M = 24` — i.e. it *already has a low `m`* and ranks near the
   head. The v1 `d_knife[]` list, its `KNIFE_MAX` cap, and the
   `is_knife()` linear searches are deleted; the candidate list is a
   strict generalisation of them.

**The v2 candidate list is the margin-ranked union of the old knife list
and the old dead-tie list, truncated to 8.**

### 6.2 Streaming top-N collection

Maintain an 8-entry array sorted ascending by `(m, t)`, updated in place
as bits are emitted (bits arrive in increasing `t`, so ties break to the
lower index automatically if insertion uses strict `<`):

```
if 32 <= t < 32 + 8*NP'  and  m < CHASE_M:
    insert (t, m) into cand[0..NCAND-1] keeping ascending (m, t)
```

- `NCAND = 8` (fixed; §7.6 shows raising it buys nothing measurable).
- `CHASE_M = 64` (156 ns). Only a gate against chasing a clean frame;
  truncation at 8 is what actually bounds the list.
- **Header and trailer bits are never candidates.** They are hard-checked
  by the marker-violation gate, and flipping them would defeat it.
- Cost: ≤ 8 compares per payload bit, ≈ 3.3 k compares per production
  frame — under 0.1 % of the decode.

### 6.3 What `decide_pass` no longer does

Deleted: `d_conf` writes, `d_tied` bitmap (replaced by a segment-local
`uint16_t` interior mask — the tie position is always inside the segment
being processed, so no NB-wide array is needed), knife detection and
append, `CONF_M`/`KNIFE_M` thresholds.

### 6.4 Measured: is the chase list good enough?

`dev_v2spec/containment.py` runs `embedded_ref` with `VOTES = False`
over the real corpora, and for every emitted-but-wrong capture asks:
*are all the wrong payload bits inside the N lowest-margin positions,
with total weight ≤ 3?*

**54-capture dataset (bench, ε ≈ −1.07 %):**

```
emitted 54   refused 0   exact 45 (83.3 %)
wrong-bit histogram:  0 bits: 45   1 bit: 7   2 bits: 2
reachable by chase, W ≤ 3:   N=4 → 53/54   N=8 → 53/54   N=12 → 53/54
worst wrong-bit rank: (1,0) (1,0) (1,0) (1,1) (1,1) (1,1) (1,2) (2,3) (2,16)
```

Eight of the nine votes-lost captures have their wrong bits at margin
ranks 0–3 — the chase reaches them at `NCAND = 4`. The ninth needs rank
16 and is out of reach at any sane list size.

Combining with the chase's own success rate under the measured weight
mix (§7.6: 96.4 % of reachable frames end on the true pattern):

> **v2 bench-corpus expectation ≈ 45 + 0.964·8 = 52.7 / 54 (97.6 %),
> every one CRC-verified — against v1's 51/54 unverified.**

**96-capture trim corpus (8 CLK_HSITRIMR codes, ε = −4.38 … +3.73 %):**

```
emitted 96   refused 0   exact 59 (61.5 %)
reachable by chase, W ≤ 3:  N=4 → 72/96   N=8 → 78/96   N=12 → 78/96
```

| trim | ε | n | exact | chase-reachable | est. per-copy CRC-verified delivery |
|---|---|---|---|---|---|
| 3 | −4.38 % | 12 | 1 | 7 | 56.5 % |
| 2 | −3.28 % | 12 | 5 | 11 | 89.9 % |
| 1 | −2.25 % | 12 | 12 | 12 | 100 % |
| 0 | −1.07 % | 12 | 10 | 12 | 99.4 % |
| 7 | +0.02 % | 12 | 10 | 12 | 99.4 % |
| 6 | +1.27 % | 12 | 10 | 10 | 83.3 % |
| 5 | +2.49 % | 12 | 5 | 8 | 65.8 % |
| 4 | +3.73 % | 12 | 6 | 6 | 50.0 % |

(Delivery column = `exact + 0.964·(reach − exact)`, §7.6.)

Three findings that shape the rest of this spec:

1. **`NCAND` is not the binding constraint — `W_MAX` is.** N = 8, 12 and
   16 all give 78/96, because the unreachable captures have 4–10 wrong
   bits, beyond any weight-3 enumeration. This is why §7.6 fixes
   `NCAND = 8` and does not offer a larger list as a tuning lever.
2. **The refusal gates never fire on real bench data** — 0 refusals in
   150 captures. All of v2's protection comes from the CRC.
3. **v1 emits grossly wrong payloads through its gates.** One trim
   capture (`zeros`, trim 5, rep 1) decoded with **63 wrong bits** and
   passed every v1 gate: marker violations 0, infeasible ≤ 4, label
   errors ≤ 6. That is a 1-in-96 silent-corruption rate on real
   hardware. CRC8 alone rejects it with p = 255/256; CRC8 + CRC16 with
   p ≈ 1 − 2⁻²⁴.

**Caveat, load-bearing:** these corpora carry *v1 framing* (16-byte
payload, 192-bit frame). They are a proxy. The margins, and therefore the
containment numbers, must be re-measured on v2-framed captures — this is
acceptance criterion **A3** (§11.2).

---

## 7. The confidence-guided chase

### 7.1 Residuals

Let `pay[0 .. NP'−1]` be the received payload' bytes extracted from the
decoded bit array (`pay[i] = bits[32 + 8i .. 32 + 8i + 7]`, MSB-first).

```
r8  = CRC8 (pay[0 .. ND+1])            XOR  pay[ND+2]           # u8
r16 = CRC16(pay[0 .. ND−1])            XOR  (pay[ND]<<8 | pay[ND+1])   # u16
```

`r8 == 0` ⇔ the payload passes CRC8. `r16 == 0` ⇔ it passes CRC16.

On-chip, bit-serial and table-free (no 256-byte tables — flash is the
binding constraint):

```c
static uint8_t crc8_bits(const uint8_t *d, uint8_t n) {
    uint8_t r = 0x00, i, k;
    for (i = 0; i < n; i++) {
        r ^= d[i];
        for (k = 0; k < 8; k++)
            r = (r & 0x80) ? (uint8_t)((r << 1) ^ 0x07) : (uint8_t)(r << 1);
    }
    return r;
}

static uint16_t crc16_bits(const uint8_t *d, uint8_t n) {
    uint16_t r = 0xFFFF; uint8_t i, k;
    for (i = 0; i < n; i++) {
        r ^= (uint16_t)d[i] << 8;
        for (k = 0; k < 8; k++)
            r = (r & 0x8000) ? (uint16_t)((r << 1) ^ 0x1021) : (uint16_t)(r << 1);
    }
    return r;
}
```

Cost: 400 bit-steps (CRC8, 50 bytes) and 384 bit-steps (CRC16, 48 bytes)
per production frame. Each runs **once**, never inside the trial loop.

### 7.2 Syndromes — the trial loop needs no CRC at all

Both CRCs are linear over GF(2) in the *difference*: the init constant
and the message prefix cancel, so for any error pattern `e`

```
CRC(x XOR e) XOR CRC(x)  =  CRC_init0(e)
```

Verified exhaustively for both polynomials: 2000/2000 random
1–3-bit patterns each, `dev_v2spec/crc_vectors.py`.

Better, the per-position syndrome has a **closed form**. For a flip of
payload' byte `p`, bit `b` (b = 7 for the MSB), define the
payload'-relative bit distance from the end of the payload:

```
j = 8*(NP' − 1 − p) + b
```

then

```
syn8 (p,b) = x^j       mod 0x107     (= x^8 + x^2 + x + 1)      # u8
syn16(p,b) = x^(j−8)   mod 0x11021   (= x^16 + x^12 + x^5 + 1)  # u16,  0 if j < 8
```

and `r8 = XOR of syn8` over the true error positions, `r16 = XOR of
syn16` likewise. Verified end-to-end on 4000 random (DATA, 1–3 flips)
production frames: **0 mismatches** (`dev_v2spec/syn_pow.py`).

This one formula covers all three regions uniformly, which is why no
special-casing is needed:

| region | p | effect | formula gives |
|---|---|---|---|
| DATA | 0 … ND−1 | changes both CRC messages | `x^j`, `x^(j−8)` |
| CRC16_HI / _LO | ND, ND+1 | changes the CRC8 message **and** the CRC16 comparand | `x^j`, `1<<(b+8)` / `1<<b` — which is exactly `x^(j−8)` |
| CRC8 | ND+2 | changes the CRC8 comparand only | `x^j = 1<<b`; `syn16 = 0` |

**On-chip syndrome walk.** Sort the ≤ 8 candidates by descending byte
index (ascending `j`) — an 8-element insertion sort. Then walk `j` from
0 upward once, maintaining `(a8, a16) = (x^j mod g8, x^(j−8) mod g16)`
by one shift-xor each, emitting a candidate's syndrome pair when `j`
reaches its value:

```
a8 = 1; a16 = 0; jn = 0
for j in 0 .. j_max:                      # j_max = largest candidate j
    if j == 8: a16 = 1
    while jn < NCAND and cand[jn].j == j:
        cand[jn].s8 = a8; cand[jn].s16 = a16; jn += 1
    a8  = (a8 << 1)  ^ (0x07   if a8  & 0x80   else 0)
    a16 = (a16 << 1) ^ (0x1021 if a16 & 0x8000 else 0)
```

≤ 408 iterations for production, ~12 cycles each ≈ **5 k cycles**. This
replaces eight separate partial CRC passes (~19 k cycles) and is
smaller in flash.

### 7.3 Trial enumeration

With syndromes in hand, a trial is two XORs and two compares — no CRC,
no multiply, no divide:

```
CHASE(cand[0..n-1], r8, r16):            # cand sorted ASCENDING by (m, t)
    # ---- trial 0: the unmodified payload -------------------------------
    if r8 == 0:
        return VERIFY(empty set)
    # ---- weight-major, index-lex enumeration ---------------------------
    trials = 1
    for w in 1 .. W_MAX:                              # W_MAX = 3
        for S in combinations(0..n-1, w) in lexicographic order:
            trials += 1
            if trials > T_MAX: return REFUSE          # budget exhausted
            s8 = XOR of cand[i].s8 for i in S
            if s8 != r8: continue                     # CRC8 fails: next
            return VERIFY(S)                          # FIRST CRC8 pass — stop
    return REFUSE                                     # no CRC8 pass in budget

VERIFY(S):
    if CRC16_VERIFY_ENABLED:
        s16 = XOR of cand[i].s16 for i in S
        if s16 != r16: return REFUSE                  # see 7.4
    apply flips S to the bit array and re-extract payload'
    return EMIT(pay[0 .. ND-1])
```

**Ordering.** Candidates are already ascending by margin, so
weight-major, index-lexicographic enumeration is *approximately*
cheapest-first by `Σ m_i`: weight dominates the cost (a 1-bit
explanation is nearly always cheaper than a 2-bit one), and within a
weight, low indices are low margins. Exact `Σ m` ordering is available
at ~+120 B of flash (est.) and is **not** specified: the order only
decides which of several syndrome-matching patterns is reported first —
correctness is carried by the CRC, not by the order. Ties in `m` break
to the lower bit index, which makes the enumeration deterministic (a
hard requirement: two receivers seeing the same capture must decide
identically).

**Budget.** `NCAND = 8`, `W_MAX = 3`, `T_MAX = 93`.

```
trials = C(8,0) + C(8,1) + C(8,2) + C(8,3) = 1 + 8 + 28 + 56 = 93
```

`T_MAX = 93` is exactly the **complete** weight-≤3 enumeration. This is
deliberate: with a complete set, a "no CRC8 pass" outcome means the error
is genuinely out of reach, never a budget artefact — which makes the
refusal interpretable and the phase-3 metrics clean. Truncating (e.g.
T_MAX = 64) was measured to convert 13.2 % of recoverable frames into
refusals for no benefit (§7.6).

| n | W ≤ 2 | W ≤ 3 |
|---|---|---|
| 4 | 11 | 15 |
| **8** | 37 | **93** |
| 12 | 79 | 299 |
| 16 | 137 | 697 |

### 7.4 Refuse-on-CRC16-mismatch

Normative policy, per the fixed spec: chase trials check **CRC8 only**;
the **first** CRC8 pass stops the chase; the winner gets **one** CRC16
verification. If that verification fails, the frame is **REFUSED** — the
chase does not continue.

This is the conservative reading and it has a clean consequence:

> A CRC8 false pass costs a **miss**, never a **wrong payload**.

Misses are what the 3× repetition exists to cover.

**CRC16 verify is not optional in practice.** The fixed spec makes it
conditional on flash. The measurement that decides it: over the 408
chase-eligible production bit positions, CRC8 (poly 0x07) yields only
**127 distinct syndromes** — `x^j mod 0x107` has period 127 — so single-bit
syndromes alias with multiplicity 3–4, and **every** single-bit error in
a 51-byte payload' shares its syndrome with 2–3 other eligible positions
(measured, `dev_v2spec/syndrome.py`). CRC8 alone cannot even *locate* a
single-bit error. The joint (CRC8, CRC16) syndrome over the 384 DATA bit
positions is **collision-free (384 distinct / 384)**.

Cost of including it: `crc16_bits` ≈ **70 B (est.)**, plus one u16 per
candidate (16 B RAM) and a second shift-xor in the syndrome walk. Against
a flash gap of 1.63 KB that must be closed by hand-optimization anyway
(§8), 70 B is not a decision point. **Specified: `CRC16_VERIFY_ENABLED =
1`.** If a final build genuinely cannot afford it, `T_MAX` must drop to
**8** (weight-1 only), because with CRC8 alone the false-accept bound is
`T·2⁻⁸` — 36 % at T = 93, which is not a decoder, it is a random number
generator.

### 7.5 False-accept math

A wrong candidate is accepted iff its 24-bit joint syndrome matches. Per
trial, heuristically `p = 2⁻⁸` for CRC8 and `2⁻¹⁶` for CRC16.

| bound | value | note |
|---|---|---|
| P(a given wrong trial passes CRC8) | 2⁻⁸ = 3.9·10⁻³ | as specified by the owner |
| P(a given wrong trial passes CRC8 **and** CRC16) | 2⁻²⁴ = 6.0·10⁻⁸ | |
| **P(false accept per chased frame)** ≤ T·2⁻²⁴ | **93 · 2⁻²⁴ = 5.5·10⁻⁶** | union bound over ≤ T wrong trials |
| P(false accept per logical frame, 3 copies) | ≤ 1.7·10⁻⁵ | |
| P(a false CRC8 pass aborts the chase) ≤ 1−(1−2⁻⁸)^(T−1) | ≤ 30 % worst case | costs a miss, not an error |

The last row is a *worst-case* bound (true pattern ranked last). §7.6
measures the realised rate at 3.5 % under the observed error mix.

Measured false accepts: **0 in 40 000** simulated chases at every tested
`(n, W_MAX, T_MAX)` (`chase_sim.py`, `chase_sim2.py`) — consistent with
the 5.5·10⁻⁶ bound (95 % upper confidence 7.5·10⁻⁵).

Residual undetectable errors: 0.10 % of chased frames under the measured
weight mix have `r8 == 0` with a wrong payload (the error pattern is in
the CRC8 kernel). Those are emitted without ever entering the chase, and
are caught only by CRC16 if enabled — another reason it is enabled.

### 7.6 Measured chase outcomes

`dev_v2spec/chase_sim2.py`, production geometry (NP' = 51, 408 eligible
positions), 40 000 frames per row, true flips drawn inside the candidate
list, `n = 8`, `W_MAX = 3`, `T_MAX = 93`:

| true weight | recovered | refuse (false CRC8 stop) | refuse (no match) | undetectable | false accepts |
|---|---|---|---|---|---|
| 1 bit | 98.10 % | 1.90 % | 0 | 0 | **0** |
| 2 bits | 90.77 % | 8.67 % | 0 | 0.56 % | **0** |
| 3 bits | 77.49 % | 22.51 % | 0 | 0 | **0** |
| **measured bench mix** (7×1bit, 2×2bit, §6.4) | **96.38 %** | 3.52 % | 0 | 0.10 % | **0** |

Test geometry (NP' = 19), measured mix: **97.85 %** recovered.

Budget sensitivity (measured, same harness):

| config | recovered | refuse | note |
|---|---|---|---|
| n=8, W≤2, T=37 | 62.8 % | 37.0 % | weight-3 errors unreachable |
| n=8, W≤3, **T=93** | **88.6 %** | 11.4 % | **specified** (uniform 1–3 weight mix) |
| n=8, W≤3, T=64 | 76.6 % | 23.2 % | truncation costs 12 pp for nothing |
| n=12, W≤3, T=150 | 66.2 % | 33.7 % | more candidates ⇒ more wrong subsets ⇒ worse |

The n=12 row is the quantitative reason `NCAND` is fixed at 8: enlarging
the list adds far more wrong hypotheses than true ones, and §6.4 already
showed it adds no reachability.

**Non-normative option, requires owner sign-off.** Continuing the
enumeration after a CRC16 mismatch instead of refusing (possible at zero
extra cost, since `s16` is already carried per candidate) raises recovery
under the measured mix from 96.38 % → **99.90 %**, and for weight-3 from
77.5 % → 100 %, with false accepts still 0/40 000 and the same
`T·2⁻²⁴` bound. It is a strict improvement, it changes only on-chip
policy (not the wire), and it is offered here as a phase-3 A/B, not as
the specification.

---

## 8. Flash budget

Baseline: `EMBEDDED_FEASIBILITY.md` §5, SDCC 4.6, `-mstm8
--opt-code-size`, NB = 448, per-function bytes from the assembler
listing. The itemised functions sum to **7309 B**; the report's stated
code total is 7.37 KB = 7547 B, so **238 B is unitemised** and is carried
forward unchanged.

| function | v1 (measured) | v2 | Δ | basis |
|---|---|---|---|---|
| `ps_next` (sample scanner) | 798 | 798 | 0 | unchanged |
| `ss_next` | 634 | 604 | −30 | `OADJ_U` additions deleted **(est.)** |
| `ps_init`/`ss_init`/`a_bounds` | 306 | 306 | 0 | |
| `seed` | 191 | 191 | 0 | |
| `refine` | 697 | 697 | 0 | |
| `known_bit`, `cal_cloud`, `map_y`, misc | 293 | 293 | 0 | |
| `label_interval` | 219 | 219 | 0 | |
| `cal_add` | 277 | 277 | 0 | |
| `calibrate` | 649 | 649 | 0 | |
| `theta56` | 669 | 669 | 0 | |
| `decide` | 528 | 528 | 0 | |
| `decide_pass` | 750 | 720 | −30 | −conf/tied/knife, +top-8 insert **(est.)** |
| **`votes` + `is_knife` + `is_resolved`** | **1038 + ~60** | **0** | **−1098** | measured 1038; helpers **(est.)** |
| `crc8_bits` | — | 55 | +55 | **(est.)** |
| `crc16_bits` | — | 70 | +70 | **(est.)** |
| chase syndrome walk | — | 120 | +120 | **(est.)** |
| chase enumeration + apply | — | 200 | +200 | **(est.)** |
| `ws_decode` (+ payload' extract, residuals, trim hook) | 260 | 340 | +80 | **(est.)** |
| unitemised (report §5 total) | 238 | 238 | 0 | |
| **code subtotal** | **7547 (7.37 KB)** | **6914 (6.75 KB)** | **−633** | |
| SDCC 32-bit mul/div library | 358 | 358 | 0 | still needed by `map_y`/`refine` |
| const (template, tables) | 40 | 32 | −8 | `OADJ_U` deleted |
| **decoder total** | **7945 (7.76 KB)** | **7304 (7.13 KB)** | **−641** | |

### 8.1 Verdict

| | v1 | v2 |
|---|---|---|
| decoder | 7.76 KB | **7.13 KB** |
| minimum production app (256 B gamma, no debug UART) | 2.50 KB | 2.50 KB |
| total | 10.26 KB | **9.63 KB** |
| budget | 8.00 KB (8192 B) | 8.00 KB |
| **overrun** | **2.30 KB (29 %)** | **1.63 KB (20 %)** |

**Flash still does not fit.** v2 removes 29 % of the overrun without
touching accuracy-critical code, but the hand-optimization path in
`EMBEDDED_FEASIBILITY.md` §5 remains mandatory. What changes is the
margin on that path: the projected assembly rewrite of the streaming
layer (`ps_next`/`ss_next`/`refine`, ~2.1 KB of C → **−2…−2.5 KB
projected**) now closes a 1.63 KB gap with **0.4…0.9 KB of slack**
instead of *just barely* closing 2.30 KB. The "fuse the two vote loops"
half of that plan is obsolete — there are no vote loops — so the target
is purely the sample scanner.

The alternative remains unchanged: a pin-compatible STM8S003/005 or
S103K3 removes the constraint at a board-respin cost.

### 8.2 RAM budget

`decoder.c` keeps all state in static globals, so the linker map is the
measurement. v1: **DATA = 781 B**, peak stack 187 B.

| item | v1 (NB=448) | v2 (NB=472) | Δ |
|---|---|---|---|
| capture buffer | 256 | **288** | +32 (§3.1) |
| `bits` bitmap | 56 | 59 | +3 |
| `conf` bitmap | 56 | **0** | −56 |
| `tied` bitmap | 56 | **0** (→ 2 B segment-local mask) | −54 |
| eps fold histograms 2×64 | 128 | 128 | 0 |
| knife list 32×u16 | 64 | **0** | −64 |
| resolved list 16×u16 | 32 | **0** | −32 |
| hypothesis costs 16×u16 | 32 | 32 | 0 |
| label windows / c0 / gaps / widths | ~40 | ~40 | 0 |
| lock + stream state, counters | ~53 | ~53 | 0 |
| payload' out | 48 | 51 | +3 |
| **chase state** | — | **37** | +37 |
| — cand positions 8×u16 | | 16 | |
| — cand margins 8×u8 | | 8 | |
| — cand syn8 8×u8 | | 8 | |
| — cand syn16 8×u16 | | *16 (if CRC16 verify enabled)* | |
| — `r8`, `r16`, subset mask, counters | | 5 | |
| **itemised total** | 821 | **690** (706 with syn16) | −131 |
| **expected measured DATA** | **781** | **≈ 650** (≈ 666 with syn16) | **−131** |

(v1's itemisation runs 40 B above its measured DATA — the `~` rows are
optimistic — so the same correction is applied to the v2 estimate.)

| | v1 | v2 no overlay | v2 with overlay |
|---|---|---|---|
| decoder DATA | 781 | ≈ 666 | ≈ 538 |
| stack (measured peak 187) | 192 | 192 | 192 |
| app persistent (ws2812_out 48 + timers/flags) | ~80 | ~80 | ~80 |
| **total** | **~925 (overlay mandatory)** | **~938** | **~810** |
| margin under 1024 | ~100 | ~86 | **~214** |

**The overlay is no longer mandatory** — v2 fits with ~86 B of margin
without it. The overlay remains available and is recommended: the two
64-byte eps histograms are dead the moment P3 ends, and P4 is the first
writer of `bits` / payload' / the chase list, whose combined 126 B (142 B
with syn16) covers them. This is the same liveness argument v1 used, with
a different target region.

### 8.3 Cycle budget

v1 measured (ucsim, NB = 448, production frame from a 256 B buffer):
**4.41 M ticks** (aa48), range 4.40–4.82 M across payloads, of which
**votes = 252 k**.

v2:

```
non-votes work  = (4.41 M − 0.252 M) × 472/448   = 4.38 M     (frame growth)
chase           = base CRC8 4.8 k + base CRC16 6.0 k
                  + syndrome walk 5.0 k + 93 trials × ~40 cy 3.7 k
                  ≈ 20 k   (0.5 %)
total           ≈ 4.40 M ticks
```

**The frame growth is paid for exactly by the votes removal.** With the
documented +7 % silicon correction (ucsim under-reads this chip on this
instruction mix): **≈ 4.7 M cycles ≈ 295 ms at 16 MHz** — unchanged from
v1, and still **~3× over the 100 ms goal as plain SDCC C.** The
mitigation is unchanged and unaffected by v2: the op counts are small
(worst case ~10.5 k sample-visits, ~2.4 k pulse-visits, ~3.8 k 32-bit
multiplies, 17 divisions), and at hand-assembly rates the same work costs
≈ 1.0 M cycles ≈ 62 ms. If the goal is relaxed, the application degrades
to a ~3 Hz update rate against 10 Hz input rather than failing.

The chase adds nothing meaningful to this picture. It is 0.5 % of the
decode, contains no multiply and no divide, and its cost is independent
of payload content.

---

## 9. Refusal policy

Evaluated in this order. **No payload leaves the decoder without a CRC
pass** — that is the v2 invariant.

| # | Condition | Outcome | Rationale |
|---|---|---|---|
| 1 | `seed()` fails: < 8 pulses, `span ≤ 0`, or `K ∉ [46000, 60000]` | **REFUSE** | no frame, or clock outside ±12 % — unchanged |
| 2 | marker violations > 0 (any of the 64 header/trailer bits wrong) | **REFUSE** | unchanged; cheap, catches lock failure before the chase |
| 3 | `infeasible > 4` | **REFUSE** | unchanged |
| 4 | `label_err > 6`, **with** the dead-marker-window adaptation | **REFUSE** | unchanged; without the adaptation the whole +5…+7.5 % corner refuses |
| 5 | `r8 == 0` (base payload passes CRC8) | → step 7 with the empty flip set | fast path, no chase |
| 6 | chase (§7.3): first CRC8 pass within `T_MAX = 93` trials | → step 7; **no pass ⇒ REFUSE** | |
| 7 | CRC16 verify of the winner: `r16 ⊕ ⊕s16 == 0` | **EMIT** `pay[0..ND−1]`; mismatch ⇒ **REFUSE** | §7.4 |

Notes:

- Steps 2–4 run **before** the chase deliberately. A frame whose lock
  failed produces garbage in every bit, and both the marker gate and the
  chase would reject it — but the marker gate costs 64 compares and the
  chase costs 20 k cycles. More importantly, ordering the gates first
  means a lock failure can never be laundered into an emit by a CRC
  coincidence.
- The chase **never** flips header or trailer bits (§6.2), so a chase
  winner cannot retroactively invalidate step 2.
- Refusal is silent at the wire level: no NAK, no retransmit request.
  Recovery is exclusively the 3× repetition.
- **Give up rather than widen.** There is no fallback that relaxes
  `W_MAX`, enlarges `NCAND`, or retries with a different lock on a
  refusal. §6.4 and §7.6 both show widening makes the decoder worse, not
  better. A refused frame is a refused frame.

---

## 10. HSITRIMR auto-trim — opportunistic hygiene only

**Not part of the decode path. Never required for a decode.** The
decoder locks wide-band, single-shot, from the frame's own
header/trailer (§5.1 P1/P2, guard band ±12 %); it assumes no operating
point and gets no fresh trim. This section exists solely to keep the
**debug UART** healthy, which breaks beyond ~±4.5 % clock error
(`HSI_TEMPERATURE.md` §3), and to nudge the sampler toward the strong
band as a side effect.

**Trigger:** after a **CRC16-verified** emit only. Never after a refusal,
never after a CRC8-only accept, never mid-capture.

**Measurement.** The locked `K` is the clock error, to the precision the
lock achieves:

```
eps_x100 = ((K_NOM − K) · 10000) / K          # signed, in units of 0.01 %
```

Verified round-trip (`dev_v2spec/budget.py`): ε = −7.500 % → K = 56680 →
recovered −7.50 %; ε = +3.730 % → K = 50544 → −+3.72 %. Integer error
≤ 0.02 % across the envelope.

**Correction** (`TRIM_SWEEP.md`): CLK_HSITRIMR (0x50CC) is a **signed
3-bit two's-complement** field; an increasing signed value *lowers* the
frequency by a mean **1.16 % per step**; total authority −4.38 … +3.73 %.

```
v_new = clamp(v_cur + round(eps_x100 / 116), −4, +3)
```

Sanity check against the measured table: at factory (v = 0) this unit
measures ε = −1.07 %, so `v_new = 0 + round(−107/116) = −1` → code 7,
whose measured residual is **+0.022 % ± 0.034 %** — the best of all eight
codes. The formula selects it.

**Guard rails, all mandatory:**

1. **Slew limit ±1 step per successful decode.** No jumps.
2. **Hysteresis:** only move if `|eps_x100| > 58` (half a step). Prevents
   oscillation between two codes straddling zero.
3. **Never write CLK_HSITRIMR while a capture is armed or running.** The
   trim-sweep firmware's discipline applies: restore/settle around the
   sampler, and drain the UART shifter (TC flag) before changing the
   clock.
4. **No thermal forward model.** The STM8S001J3 has no temperature sensor
   (DS12129 §4.12 provides only a temperature-independent bandgap on
   AIN7). Trim is measured-and-corrected, never predicted.
5. **The decoder must remain correct at factory trim forever.** A build
   whose decode depends on a converged trim is a spec violation. Verify
   by running the whole phase-3 corpus with auto-trim disabled.

**Known trade-off, from the sweep:** trimming to ε ≈ 0 is optimal for the
UART and eliminates swallowed 0-bits, but it *maximises* 1-bit merging
on dense-ones data (code 7 measures 64 merged loops on `ones` vs 5–12 at
the slow codes) — a phase resonance, since at ε ≈ 0 the 40-cycle loop is
exactly 2 bit periods. The decoder models merging exactly, and merging at
ε ≈ 0 is deterministic, so this is handled. If it ever becomes
problematic, target ε ≈ +1…+2.5 % instead (still inside the strong
band, merging drops to ~5/frame, nothing swallowed).

---

## 11. Phase-3 acceptance criteria

### 11.1 Corpus to acquire (prerequisite)

The existing datasets carry **v1 framing** and cannot validate v2. Phase
3 begins with a new bench acquisition, `data/captures_v2_trim.json`:

- v2 framing, **27-byte test frames** (216 bits), 16-byte DATA + check
  block, CRC computed by the transmitter.
- **8 CLK_HSITRIMR codes** × **≥ 8 patterns** (the 6 sweep patterns plus
  `nibbles` and `dense`, the two classes that stress the razor families)
  × **≥ 3 reps** = ≥ 192 captures. **3 reps is a hard requirement**: with
  2 reps the N = 3 miss rate can only be extrapolated, and §11.3 shows
  extrapolation is unsafe.
- Same firmware discipline as `capture_trim.c`: all UART at factory trim,
  trim applied only around `cap_code`, checksum on every dump.
- Capture 288 bytes (or 640 and truncate, to allow the buffer-sizing
  check A2 to be made from the same data).
- Ambient recorded as uninstrumented, as before.

A production-size (59-byte) synthetic corpus from `synth.py` at the
eleven ε points is required in addition, but is **supporting evidence
only** — it shares its timing model with the decoder.

### 11.2 Per-copy criteria

| ID | Criterion | Threshold |
|---|---|---|
| **A1** | C decoder output bit-identical to the updated `embedded_ref` on 100 % of the v2 corpus (real + synthetic), both at NP' = 19 and NP' = 51. Zero fixed-point assert violations. Two full runs sha256-identical. | **exact** |
| **A2** | Capture buffer: no truncated trailer at any trim code. Report max loops consumed per code. | **≥ 16 loops (37 µs) headroom at the fastest code (+3.73 %)** |
| **A3** | Chase-list containment: over emitted-but-wrong frames, fraction whose wrong bits all lie in the 8 lowest-margin payload' positions with weight ≤ 3. Re-measures §6.4 on v2 framing. | **≥ 85 %** in the band \|ε\| ≤ 2.5 %; report the full curve |
| **A4** | **False accepts: any CRC-verified emit whose payload ≠ ground truth.** | **0 — hard fail of phase 3, no exceptions** |
| **A5** | Chase telemetry: chase-entry rate, chase-win rate, mean/max trials, false-CRC8-stop rate. The last must be consistent with the ≤ 30 % worst-case and the 3.5 % measured-mix figure of §7.6. | reported, and within bounds |
| **A6** | Build-time CRC self-test: the three vectors of §2.3 reproduce exactly at both NP'. | **exact** |
| **A7** | Fault injection: flip 1, 2, 3 and 5 known bits at known margin ranks in a good capture; confirm 1–3 are recovered when in the list, 5 is refused, and no injection ever produces a wrong emit. | **0 wrong emits over ≥ 1000 injections** |
| **A8** | Cycle count: ucsim ticks for the v2 build. | **≤ 4.9 M** (v2 projection + 10 %) |
| **A9** | Flash and RAM from the SDCC map. | code ≤ **7.3 KB**; DATA ≤ **700 B**; peak stack ≤ **200 B** |

### 11.3 Miss rate with 3× repetition — the criterion that matters

**Definition.** A logical frame is *missed* iff **all 3 copies refuse or
are lost**. A logical frame is *falsely delivered* iff any copy produces
a CRC-verified emit with the wrong payload (A4 already forbids this).

**Do not compute the miss rate as `(1 − p)³`.** `dev_v2spec/correlate.py`
measures the correlation directly on the 96-capture trim corpus, which
has 2 reps per (pattern, trim) cell:

```
48 cells:   both-ok 36    split 6    both-fail 6
marginal per-copy success p = 0.812
independent model P(both fail) = 0.035
OBSERVED     P(both fail) = 0.125          <-- 3.6x the independent model
```

The both-fail cells are pattern-and-ε specific, not random:

| ε | pattern | rep0 | rep1 |
|---|---|---|---|
| −4.38 % | `aa` | LOST (8 wrong bits) | LOST (4) |
| +1.27 % | `edges` | LOST (8) | LOST (5) |
| +2.49 % | `edges` | LOST (10) | LOST (8) |
| +3.73 % | `edges` | LOST (7) | LOST (9) |
| +3.73 % | `rnd1` | LOST (6) | LOST (10) |
| +3.73 % | `rnd2` | LOST (10) | LOST (8) |

A (pattern, ε) combination that fails tends to fail **every time**: the
copies share the same clock error and the same dead-sampling-window
geometry, and only `t0` (capture start phase, fitted range 254…501 ns)
decorrelates them. Repetition buys much less than the independent model
promises. Extrapolating the 2-rep data to N = 3 by treating each cell's
per-copy rate as `{1, 0.5, 0}` gives an estimated 3× miss rate of
**≈ 14 %** over the full trim authority, against 0.66 % for the
independent model — a factor of 21.

**Therefore the miss rate must be measured, not modelled.** Criteria:

| ID | Criterion | Threshold |
|---|---|---|
| **A10a** | 3× logical miss rate over trim codes with \|ε\| ≤ 2.5 % (codes 1, 0, 7, 6) | **≤ 1 %** |
| **A10b** | 3× logical miss rate over the full trim authority (−4.38 … +3.73 %) | **≤ 15 %**, and every both/all-fail cell attributed to a named physical mechanism (dead sampling window at that ε for that pattern), never to a decoder defect |
| **A10c** | 3× logical **false-delivery** count, whole corpus | **0** |
| **A10d** | Report the per-cell all-fail table (like the one above) and the observed-vs-independent ratio. A ratio > 5 is a finding requiring escalation to the owner: it would mean repetition is nearly worthless and a *payload-diversifying* mechanism (e.g. bit-interleaving across copies) is needed. | reported |

### 11.4 The ±7.5 % requirement, stated honestly

The system requirement is that the decoder lock wide-band ±7.5 %
single-shot with no fresh trim. **It does** — the lock guard band is
±12 % and P1 derives `K` from the frame's own endpoint span with no
prior. What it cannot do is *decode* reliably at the extremes, and that
is a physical ceiling, not a decoder defect: at large \|ε\| up to half
the payload's discriminating windows are never sampled. Both the
embedded and host decoders sit at the same ceiling
(`EMBEDDED_FEASIBILITY.md` §3), and the embedded one is the *better* of
the two at the fast corners.

Per-copy exact rates from the v1 envelope sweep, and what 3× repetition
buys **under the (optimistic) independence assumption**:

| ε | per-copy | N=3 | N=6 | N=9 | N=12 |
|---|---|---|---|---|---|
| −7.5 % | 0.222 | 52.9 % | 77.9 % | 89.6 % | 95.1 % |
| −5.0 % | 0.704 | 97.4 % | 99.9 % | 100 % | 100 % |
| −2.5 % | 1.000 | 100 % | 100 % | 100 % | 100 % |
| −1.1 % (bench) | 0.981 | 100 % | 100 % | 100 % | 100 % |
| +1.0 % | 0.704 | 97.4 % | 99.9 % | 100 % | 100 % |
| +2.5 % | 0.593 | 93.2 % | 99.5 % | 100 % | 100 % |
| +5.0 % | 0.259 | 59.4 % | 83.5 % | 93.3 % | 97.3 % |
| +7.5 % | 0.167 | 42.1 % | 66.5 % | 80.6 % | 88.8 % |

Read this correctly, and record it in the phase-3 report:

- **In the trim-reachable band (ε ∈ [−2.5 %, +1 %]) 3× repetition is
  effectively perfect.** This is the design point, and §10's hygiene loop
  is what keeps the operating point there.
- **At the untrimmed ±7.5 % corners, 3× repetition delivers roughly half
  of all frames** — and §11.3 says even that is optimistic, because the
  copies are correlated. Meeting a high delivery requirement at those
  corners needs **N ≈ 12–18 repetitions**, not 3.
- If the owner's "frames are rare and must not be missed" requirement is
  meant to hold at the untrimmed extremes, then **3× repetition is not
  sufficient and the repetition count is the parameter to change** — it
  is a transmitter-side decision costing nothing on the receiver. This
  spec flags it rather than silently assuming the corners never occur.

---

## 12. Risks

1. **Flash remains the hard wall.** v2 cuts the overrun from 2.30 KB to
   1.63 KB without touching accuracy-critical code, but does not close
   it. The assembly rewrite of `ps_next`/`ss_next`/`refine` is still
   required; it now has 0.4–0.9 KB of projected slack instead of ~0.
2. **The cycle projection is still unproven.** 62–95 ms rests on that
   same rewrite; as-compiled is ~295 ms. Unchanged by v2.
3. **Correlated repetition failures** (§11.3, measured 3.6× the
   independent model). The mitigation in this spec is the auto-trim
   hygiene keeping ε in the strong band. If phase 3 measures A10b above
   15 %, the escalation path is more repetitions or payload
   diversification, not decoder work.
4. **Model drift.** The decoder hard-codes the fitted sampler geometry as
   exact integer cycles. A firmware change to the capture loop
   (instruction alignment moves `W_CY[]`) silently invalidates it. The
   re-verification procedure in `approaches/dev_calibration/` must gate
   any capture-loop edit — including the buffer-size change in §3, which
   touches `cap_code` and therefore **requires re-running that
   verification before phase 3 begins**.
5. **`nibbles_1`-class captures** remain a known −1 vs the host that no
   single-geometry decoder recovers (§5.3), now handed to repetition.
6. **CRC8's 127-bit syndrome period** (§7.4) means CRC8 alone cannot
   locate even a single-bit error on a 51-byte payload'. Any future build
   that drops the CRC16 verify to save flash must simultaneously drop
   `T_MAX` to 8 — this coupling is easy to lose in a size-reduction pass
   and should be asserted at build time.
7. **The containment numbers in §6.4 are proxies** measured on v1-framed
   captures. A3 re-establishes them on v2 framing; if containment comes
   in below 85 %, the chase's value drops proportionally and §5.2's cut
   must be revisited with the owner.

---

## 13. Files

Specified (to be written in implementation):

- `approaches/embedded_ref_v2.py` — integer reference, votes removed,
  chase added; same assert discipline, same determinism requirement.
- `approaches/dev_embedded/decoder_v2.c` — bit-exact C port.
- `data/captures_v2_trim.json` — the phase-3 corpus (§11.1).

Scratch for this spec (`approaches/dev_v2spec/`, no existing file
modified):

- `crc_vectors.py` — §2.3 vectors; CRC8/CRC16 difference-linearity proof.
- `syn_pow.py` — §7.2 closed-form syndrome, verified 0/4000.
- `budget.py` — §3.1 buffer sizing, §7.3 trial counts, §8.3 cycles,
  §10 eps round-trip.
- `syndrome.py` — CRC8 syndrome collision statistics (127 distinct / 408
  positions); joint (CRC8, CRC16) collision-free over DATA.
- `chase_sim.py`, `chase_sim2.py` — §7.6 outcome tables, 40 000 frames
  per row.
- `ref_marg.py` — instrumented copy of `embedded_ref.py` exposing the
  per-bit margin (4 mechanical edits, listed in the patch script).
- `containment.py` — §6.4, both real corpora.
- `correlate.py` — §11.3 repetition correlation.
