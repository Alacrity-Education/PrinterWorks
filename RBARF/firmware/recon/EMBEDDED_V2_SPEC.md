# Embedded Decoder v2 — Specification

> **Wire-version status (2026-09-07, third revision).** This document
> specifies the decoder for wire protocol **v2.2** (4+4-byte markers,
> `[CRC8]*4`) and every measurement in it is a v2.2 measurement. The
> code has since moved on: `approaches/embedded_v2.py` (normative),
> `decode.c` and `decode_asm.s` now implement **v2.3** — 3+3-byte
> markers `FF AA 65` / **`9A 00 FF`** (`PP_LO = 24`; the trailer's
> middle byte is a worst-case-ZEROS calibration probe, not a second
> bit-period ruler — owner decision 2026-09-07, +26.7 points of
> delivery on silicon), one CRC-16/CCITT-FALSE written three times,
> independent per-byte majority with a confidence-ranked reference cross
> product, and the three owner-directed **relaxations** (wide clock
> window, marker threshold, `A_MAX = 11` with a `T_MAX = 131`
> residual-comparison budget). See `../../docs/PROTOCOL.md` for the wire and the
> phase report for the parameter measurements.
>
> **What that changes about the sections below.** §7.1–7.6 (CRC8
> reference, syndrome table, budget) are superseded — the 8-bit numbers
> justified a budget of 9 trials, a 16-bit check affords 131. §7.7 (the
> alias guard) is **retired with a proof**: `ord(x) mod 0x11021 = 32767`,
> so the 384 production data-bit syndromes are all distinct and the
> ambiguity cannot arise. §7.4's parity gate **survives verbatim**:
> `0x11021 = (x+1)·0xF01F`, so every single-bit syndrome still has odd
> parity. §7.8's split-vote fallback is **live** in v2.3, not a build
> flag. §9.1's R2/R3 become thresholds and **R5 is retired**. §10's
> flash and RAM budgets are superseded by the v2.3 build measurements in
> the phase report. **§6.4 (LEVER B, 2026-09-08) adds a fourth live
> mechanism**: a geometric admission rule that lets a bit whose
> *discriminating interval* gives no usable evidence into the chase
> regardless of its apparent margin, which is what `R6 refuse_nocand`
> was made of; `A_MAX` and `T_MAX` are unchanged and `T_MAX` remains the
> whole false-accept bound. The v2.3 terse production image **fits**:
> 8 151/8 192 B with the pipeline tail hand-assembled in `decode_asm.s`
> (986 B against 1 641 B of compiled C CODE + 110 B of CONST), which
> closed the 748 B overflow §13.1 measured; the VERBOSE bench variant is
> still 46 B over. See `PROD_CLOSURE.md` §14. The v2.2 compat
> geometries (`chk=4` / `chk=3`) still decode bit-for-bit as specified
> here, and the parity harnesses prove it — but note that only
> `decode.c` carries them now: `decode_asm.s` is v2.3-geometry only.

WS2812 receiver for the STM8S001J3. This document specifies the **v2**
on-chip decoder: the v1 pipeline (`approaches/embedded_ref.py`,
`../archive/investigations/dev_embedded/decoder.c`) with the byte-period **votes**
machinery and the second sampler model **removed**, and a **CRC8-guided
confidence chase** added in their place.

Scope: precise enough to implement from. Every number is either measured
(cited to its source and reproducible from `../archive/investigations/dev_v2spec/`) or
derived here with the derivation shown. Items marked **(est.)** are
engineering estimates, not measurements, and are flagged as such
wherever they appear in a budget.

## 0. Inputs and their status

| Input | Source | Status here |
|---|---|---|
| v1 algorithm, ablations, per-function flash, cycle counts | `EMBEDDED_FEASIBILITY.md` | baseline; every "cost of removal" cites its §2 table |
| v1 fixed-point contract | `approaches/embedded_ref.py` header | carried forward verbatim (§4) |
| sampler timing model | `DATASET.md` ADDENDUM, `HSI_TEMPERATURE.md` | unchanged; hard-coded integer cycles |
| trim → eps map | `TRIM_SWEEP.md` | §11 auto-trim hygiene only |
| CRC block v2.1 rev2 | project owner, **FIXED** | §2 — reproduced, not redesigned |
| single-transmission rule | project owner, **FIXED** | §9 refusal policy is written around it |
| host-side reference implementation | `../bench/crc.py`, `../bench/patterns.py` | this spec's receiver policy is the mirror image of `crc.majority` / `crc.reference_candidates` / `crc.fa_prob_crc8` (the 8-bit function; v2.3 renamed the 16-bit one to `crc.fa_prob`) |

Measurements made **for this spec** (all scratch in
`../archive/investigations/dev_v2spec/`; no file outside that directory and this one was
created or modified):

| Script | What it establishes |
|---|---|
| `v21.py` | the v2.1 rev2 wire format + a reference chase, in the exact shape the STM8 runs |
| `e2e_v2.py`, `prod_e2e.py` | end-to-end decode+chase of **real v2.1 rev2 frames** (synthetic captures) at 19 clock points, test (216-bit) and production (472-bit) scale |
| `sweep.py`, `sweep2.py`, `sweep3.py`, `sweep_prod.py`, `sweep_prod2.py` | admission-gate / budget / ordering sweeps that pick §7's constants |
| `guards.py`, `final.py`, `numbers.py` | the catastrophic-zero frontier and the numbers §8 and §12 quote |
| `real_reach.py`, `real_v21.py` | **real-silicon** anchors: 54 + 96 + 24 v2.0 captures and 54 + 36 real 27-byte v2.1-length captures |
| `diag.py` | why a broken frame must not be chased (the tie-count separator) |
| `containment.py`, `correlate.py`, `crc_vectors.py`, `syndrome.py`, `syn_pow.py`, `budget.py` | earlier-round measurements, still cited where noted |
| `ref_marg.py` | v1 integer reference instrumented to expose per-bit margins; reproduces the feasibility report's 51/54 with votes ON (verified, §6.1) |

---

## 1. What changes, in one table

| | v1 (measured) | v2 (this spec) |
|---|---|---|
| wire payload | 16 B test / 48 B prod | **+3 B check block** → 19 B / 51 B |
| frame | 24 B / 56 B (192 / 448 bits) | **27 B / 59 B (216 / 472 bits)** |
| capture buffer | 256 B | **288 B** prod / 128 B test — §3 |
| bit-error repair | dead-window + knife byte-period **votes** (heuristic, unverified) | **CRC8 confidence chase** — every emitted payload is CRC8-checked |
| second sampler model | already absent (dropped in v1, cost measured) | absent, and formally closed — §5.3 |
| per-bit confidence | 1-bit map (margin ≥ 16 TU) + 32-entry knife list | **u8 margin, streamed top-5 list** — §6 |
| repetition | n/a | **none** — one copy per logical frame, a refusal *is* a miss |
| decoder DATA | 781 B, overlay **mandatory** | **≈ 651 B**, overlay **optional** — §10.2 |
| decoder flash | 7.8 KB (2.30 KB over budget beside the app) | **≈ 7.43 KB (est.)** (1.74 KB over) — §10.1 |
| decode cycles | ~4.41 M ucsim ticks @448 bits | **~4.39 M ticks @472 bits** — §10.3 |
| silent wrong payload | **measured 40 / 174 real captures** — v1 never refuses on them, and 40 of its emissions are wrong (§12.4) | **0 / 2736** end-to-end decodes across ±8 % — §8, §12 |

The headline: v2 trades a heuristic bit-repair mechanism for a *checked*
one. It is smaller, no slower, needs no RAM overlay — and every payload
it emits has been verified against a check value carried on the wire.
Where v1 emitted a confidently-wrong payload it now either repairs it
(measured) or refuses.

---

## 2. Wire format v2.1 rev2 — NORMATIVE, do not redesign

### 2.1 Frame

```
frame = HEADER(4) || payload'(P) || TRAILER(4)          bytes, MSB first
HEADER  = FF 00 AA 65
TRAILER = 9A 55 00 FF
payload' = DATA(D) || CRC8 || CRC8 || CRC8              P = D + 3
```

| build | D (data) | P (payload') | frame | frame bits |
|---|---|---|---|---|
| test / bring-up | 16 | 19 | 27 | 216 |
| production (16 LEDs, GRB) | 48 | 51 | 59 | 472 |

The wire framing (HEADER/TRAILER, MSB-first, low idle before, low latch
after, edge-triggered capture start) is **unchanged from v1**.

### 2.2 CRC8

CRC-8/SMBUS: **poly 0x07, init 0x00, no input or output reflection,
xorout 0x00**, computed over the **DATA bytes only** — the check bytes
are not part of their own message. Check value: `CRC8("123456789") =
0xF4` (verified, `../archive/investigations/dev_v2spec/v21.py`).

The same byte is written three times. It is an LED-sized (3-byte) block
so the frame stays a whole number of LEDs on the wire.

**There is no CRC16 anywhere in v2.1 rev2** — dropped by owner decision.
The entire residual risk of the chase is the 8-bit check's per-trial
false accept, bounded by the trial budget alone. §8 states those numbers
honestly wherever a budget is chosen.

### 2.3 Why triplication, and what it buys (measured)

The check block travels the same corrupted channel as the data and is
exactly as exposed to reconstruction error. The receiver takes the
**2-of-3 byte-equality majority** of the three decoded check bytes as
its chase reference: any two identical bytes win, so one mangled check
byte is harmless.

Measured on 1710 production-scale decodes across 19 clock points
(`../archive/investigations/dev_v2spec/numbers.py`), the decoded check block was:

| outcome | count | share |
|---|---|---|
| all three copies equal | 1235 | 76.3 % |
| exactly one copy corrupted, **majority saved the frame** | 293 | **18.1 %** |
| all three differ (no majority) | 90 | 5.6 % |

The triplication is not ceremonial: on nearly one frame in five it is
the only reason a reference existed at all.

### 2.4 Test vectors (computed, `../archive/investigations/dev_v2spec/v21.py`)

```
DATA (test)  = 00 01 02 ... 0F                       (16 B)
CRC8         = 0x41
payload'(19) = 000102030405060708090A0B0C0D0E0F 41 41 41
frame(27)    = FF00AA65 000102030405060708090A0B0C0D0E0F 414141 9A5500FF

DATA (prod)  = (i*5)&0xFF for i in 0..47             (48 B)
CRC8         = 0xF6
payload'(51) = 00050A0F...EBF0F5 F6 F6 F6            (…F0F5 = bytes 46,47)
frame len    = 59 B = 472 bits
```

### 2.5 Single transmission — NORMATIVE

The host **cannot repeat frames**. Each logical frame is sent exactly
once and must decode from that one copy. There are no sequence numbers
and no retransmission. Consequences that the rest of this spec is built
around:

- **A refusal is a missed frame.** It is not "wait for the next copy".
- **Chase hard before refusing.** Every recovery the chase makes is a
  frame that would otherwise be lost outright.
- **A catastrophic — confidently wrong data that passes CRC — is
  strictly worse than a refusal, and must stay at 0.** This is the
  constraint that sets the chase budget (§7.6), not an abstract
  1/256 argument.

---

## 3. Frame geometry and capture-buffer sizing

Sampler model (fitted, hardware-exact; `DATASET.md` ADDENDUM): loop = 40
CPU cycles = 2500.0 ns nominal, 8 samples/loop, 1 capture byte/loop.
A frame of `NB` bits occupies `NB · 1250 ns` on the wire, i.e.

```
loops(NB, eps) = NB · 1250 · (1 + eps) / 2500 = NB · (1 + eps) / 2
```

plus the capture's accounting slack (trigger phase `t0` 254…501 ns and
the latch tail). Calibrating that slack against the feasibility report's
own figure (448 bits at +8 % → "243 loops", §1) gives **1.08 loops** of
slack; the table below uses it.

| build | NB | −7.5 % | nominal | +7.5 % | +8 % | +8 % incl. slack |
|---|---|---|---|---|---|---|
| test | 216 | 99.9 | 108.0 | 116.1 | 116.6 | **117.7** |
| production | 472 | 218.3 | 236.0 | 253.7 | 254.9 | **256.0** |

| buffer | margin at +8 %, production |
|---|---|
| 256 B | **+0.0 loops** — exactly at the edge, no margin |
| 272 B | +16.0 loops (37 µs) |
| **288 B** | **+32.0 loops (74 µs)** ← specified |
| 320 B | +64.0 loops (148 µs) |

**`CAP_BYTES = 288` for production, `CAP_BYTES = 128` for the test
build** (+10.3 loops of margin at +8 %; bring-up only — use 160 B if the
bench ever needs headroom). v1's 256 B is *not* transferable: the v2.1
frame is 24 bits longer and 256 B lands exactly on the truncation
boundary at the fast corner, where a truncated trailer destroys the
lock. This is the one RAM item that grows in v2.

---

## 4. Fixed-point contract (carried forward unchanged)

Reproduced verbatim from `approaches/embedded_ref.py`; v2 changes
nothing here. TU ("time unit") = BIT / 2^9 = 1250/512 ns = **2.4414 ns**
(`BIT_SH = 9`; at BIT_SH = 7 the (5,6)-family knife boundaries were
measured lost to quantization — feasibility §3).

| quantity | format | range / units |
|---|---|---|
| `t` receiver time | u16 | CPU cycles; ≤ ~27.5 k over a 640-loop capture |
| `K` clock scale | u16 | Q11 TU/cycle; nominal `K_NOM = 52429` |
| `t·K` | **u32** | ≤ 27.5 k · 60000 < 2³¹ |
| `y` mapped wire time | **u32** | TU; `BIAS + NB·512 + TAIL` ≈ 242 k at 472 bits |
| `tau` lock offset | s16 | TU |
| `u`, `v` fall bracket | s16 | TU, relative to the pulse's bit lattice |
| `h0c`, `h1c`, `theta`, `eps` | s16 | TU |
| `Se` residual sums | **s32** | ≤ 240 pulses · 256 TU |
| `Sy` position sums | **u32** | ≤ 240 pulses · 242 k TU |
| `K·de`, seed dividend | **s32** | see `_seed` / `_refine` |
| **`mgv` per-bit margin (v2, new)** | **u8** | TU, saturating at 255 — §6.1 |
| **`r` CRC8 residual (v2, new)** | **u8** | GF(2⁸) |

Divisions: ~10 per decode (lock + calibration). All ranges are enforced
by asserts on every dataset and synthetic run in the Python reference
(zero violations). The u32 range check must be **re-run at NB = 472**
before the C build is trusted: `y` grows from ~230 k to ~242 k TU and
`Sy` with it; both stay far inside u32, but the assert battery is the
proof, not this sentence.

Fixed constants unchanged from v1: `LOOP_CY = 40`,
`O_CY = [0,4,9,13,17,21,27,32]`, `W_CY = [0,-1,0,+2,0,0,0,+1]`,
`H0P = 154`, `H1P = 308`, `TAIL_U = 164`, `K_MIN/K_MAX = 46000/60000`,
`INFEAS_U = 160`, `H0_LO/HI = 112/192`, `H1_LO/HI = 252/376`,
`SEP_LO/HI = 112/196`, `GATE_INFEAS = 4`, `GATE_LABERR = 6`, and the eps
analog block (`EPS_ZONE 32`, `EPS_HIST 64`, `EPS_GAP_MIN 5`,
`EPS_CLAMP56 24`, `EPS_CLEAR1 18`, `EPS_TOPM 3`, `EPS_SLACK 2`,
`EPS_SLACK1 8`).

Constants that **disappear** in v2: `KNIFE_M`, `KNIFE_MAX`,
`KNIFE_PAIR_MIN`, `KNIFE_AGREE_PCT`, `DEAD_VOTE_MIN`, `CONF_M`,
`OADJ_U[8]`.

Constants that **appear** in v2 (all justified in §7):
`CHK_LEN = 3`, `MG_MAX = 8`, `A_MAX = 5`, `W_MAX = 2`,
`TIE_EMIT = 8`, `CRC8_POLY = 0x07`, `XPOW[127]`.

Constants that appear with **LEVER B** (§6.4): `DW_EN = 1` (0 in every
compat mode, which is the whole revert), `DW_OFF_MAX = 64`. No new
threshold: the admission test is the geometry, not a tunable.

---

## 5. Pipeline — what is kept, what is cut

### 5.1 Stages KEPT unchanged

Every stage below is bit-identical to v1; the only edit is `NB` (448 →
472) and the frame template used by `a_bounds`/`known_bit`.

| stage | function in `decoder.c` | role |
|---|---|---|
| P1 endpoint seed | `seed`, `ps_init`, `ps_next` | first-rise / last-fall brackets; the **known frame length** pins K to ±0.1 %, excluding one-bit-slip aliases a priori (this is why no Hough grid is needed) |
| P2 lock refine (×2) | `refine`, `map_y` | integer two-half-means residual regression for (K, tau) |
| P3 marker calibration | `calibrate`, `cal_add`, `cal_cloud`, `theta56`, `label_interval` | interval-intersection h0c/h1c fit + the **eps analog** (64-bin fold histogram per razor family) |
| P4 segmentation + decision | `ss_init`, `ss_next`, `a_bounds`, `hinge`, `decide` | gap-accounting segmentation `(Δy+256)>>9`; marker-constrained leading-ones argmin by interval hinge, interior-preferred, fewer-ones tie-break |
| S8c honest refusal gates | in `ws_decode` | violations > 0 / infeasible > 4 / label_err > 6, with the dead-marker-window adaptation |

The eps analog stays because it is the single most valuable mechanism in
the pipeline: turning it off costs **−7 captures** (46/54 vs 53/54,
feasibility §2). Nothing in v2 touches it.

### 5.2 Stage REMOVED — the votes machinery

Removed: `votes()`, `is_knife()`, `is_resolved()`, the knife candidate
list, the resolved list, and the `conf` / `tied` bitmaps that fed them.

**Measured cost of removal** (feasibility §2, ablations on the 54-capture
corpus, baseline 53/54):

| ablation | result | delta |
|---|---|---|
| knife vote off | 47/54 | **−6** |
| dead-window vote off | 51/54 | −2 |
| both votes off | 45/54 | **−8** |

Re-measured here on real silicon with the v1 integer reference
(`../archive/investigations/dev_v2spec/real_reach.py`, `ref_marg.py`):

| corpus | votes ON | votes CUT |
|---|---|---|
| 54 real bench captures | **51/54 exact (94.4 %)** | 45/54 exact (83.3 %) |

The 51/54 reproduces the feasibility report exactly, which is the
evidence that `ref_marg.py` is a faithful stand-in for `decoder.c`.

**But the 51/54 is not the whole story, and this is why v2 exists.** Run
the same v1 decoder — votes on, all refusal gates active — over every
real capture the project owns (`../archive/investigations/dev_v2spec/real_reach.py`, verification
pass):

| corpus | n | emitted | exact | **silently wrong** | refused |
|---|---|---|---|---|---|
| bench (`captures.json`) | 54 | 54 | 51 | **3** | 0 |
| validation (`captures_val.json`) | 24 | 24 | 20 | **4** | 0 |
| trim sweep (`captures_trim.json`) | 96 | 96 | 63 | **33** | 0 |
| **total** | **174** | **174** | **134** | **40 (23 %)** | **0** |

v1 refuses *nothing* on real silicon and emits 40 wrong payloads with no
indication that anything went wrong. Under the single-transmission rule
that is 40 unrecoverable, unnoticeable corruptions. That number — not
the 51/54 — is what the CRC block was added to fix.

**What replaces the 8 lost captures.** With the votes cut, the wrong
bits are not gone — they are *low-margin*, and the chase can reach them.
On the same 54 real captures, under the exact v2 admission policy of §7
(no ground truth used except as a ruler):

| | count |
|---|---|
| exact pre-CRC | 45 |
| wrong bits contained in the admitted weak set, weight ≤ 2 → **chase-reachable** | 5 |
| **ceiling** | **50 / 54 (92.6 %)** |
| out of reach (→ refusal) | 1 |
| refused by the admission gate | 3 |

So v2 ends up **one capture below** v1's votes on this corpus — and
every one of its 50 is CRC8-verified, while v1's 51 were asserted. That
trade is the whole point of §5.2: see §12.4 for what v1's unverified
emissions actually cost on the trim corpus.

**Why the votes cannot simply be kept as well.** Two reasons, both
measured: (a) flash — `votes()` is the single largest function in the
build at **1038 B** (feasibility §5), and the decoder is already 2.3 KB
over budget; (b) at production scale the dead-window vote was *already*
found to misfire — the feasibility report documents it flipping a dead
bit on 3 coincidentally-unanimous siblings on a 448-bit random payload,
which is precisely the confidently-wrong failure the CRC exists to stop.

### 5.3 Stage REMOVED (formally closed) — the second sampler model

This is a *formal closure*, not a new cut: the embedded v1 build already
ships only the integer "fit" geometry. The record, so nobody reopens it:

| variant | measured |
|---|---|
| host dual-model arbitration ("cal" + "fit") | 53/54 |
| fit-only (what the embedded build ships) | 50/54 (**−3**) |
| cal-only | 53/54 |
| cal's sub-cycle slot offsets transplanted as a static table (`OADJ_U`) | **35/54 — harmful** |

The −3 is a real, unrecoverable architecture loss (the `nibbles_1` class:
the feasibility report shows truth-0 at u = 150 and truth-1 at u = 148 in
the same capture — not linearly separable in a single fitted geometry).
v2 deletes the `OADJ_U[8]` table and the code path that reads it. Flash
saved: 8 B const plus the per-sample add (est. ~30 B). **Additional
accuracy cost of this closure in v2: zero** — the −3 was already paid in
v1, and the chase now recovers part of it (`nibbles`-class errors are
low-margin single bits, which is exactly what §7 chases).

### 5.4 Stage REMOVED — self-training second pass

Already off in v1's final config (`SELF_TRAIN = False`), measured to
change **nothing** on all 54 real and 18 production-size synthetic
decodes. It stays out. Saves 2 of 7 capture scans.

### 5.5 Stage ADDED — CRC8 confidence chase

New pipeline tail, after P4 and before the refusal gates:

```
P4  decision + emit + per-bit u8 margin + streaming top-5 weak list   (§6)
C1  assemble payload' bytes; CRC8 over DATA; 2-of-3 majority reference
C2  direct check: crc8(DATA) == reference ?  -> emit                  (§7.1)
C3  admission gates (tie count, weak-set size)                        (§7.5)
C4  bounded trial enumeration, cheapest-first, stop at first pass     (§7.4)
C5  alias guard on the accepted trial                                 (§7.7)
S8c honest refusal gates (unchanged) + chase-exhausted refusal        (§9)
```

Scan count is unchanged at 5 — the chase adds **no** pass over the
capture buffer. It works entirely on the 59-byte decoded bit array and a
5-entry candidate list.

---

## 6. Decision pass: the margin becomes a first-class output

### 6.1 What `decide` already computes

`decide(k0, k1, u, v, fam, cal)` evaluates every feasible leading-ones
hypothesis `a ∈ [lo, hi]` and returns the argmin of an interval hinge
cost. v1 then reduces the runner-up gap to one bit:

```c
/* v1 */  conf[t] = (margin >= CONF_M);        /* CONF_M = 16 TU */
          tied[t] = (margin == 0);
```

The margin is `|c0 − c1|` where `c0` is the least cost among hypotheses
that put bit `t` at 0 and `c1` the least among those that put it at 1 —
i.e. a genuine per-bit log-likelihood-ratio analog in TU, already
computed, already integer, and thrown away.

**v2 keeps it.** For every payload' bit `t`:

```c
uint8_t m = (c0_absent || c1_absent) ? 255 : min(255, abs(c0 - c1));
if (tied)  m = 0;                              /* no evidence at all */
```

Units are TU (2.44 ns). `m = 0` means the two hypotheses cost exactly
the same — the bit was decided by tie-break, not by evidence. `m = 255`
means one polarity was infeasible.

### 6.2 Streaming top-N weak list

The decoder never stores 408 margins. It maintains a **sorted 5-entry
insertion list** of the lowest-margin payload' bit positions, plus a
counter:

```c
uint16_t cand_t[A_MAX];        /* bit index, ascending margin */
uint8_t  cand_m[A_MAX];        /* the margin */
uint8_t  n_cand;               /* entries in use, <= A_MAX */
uint16_t n_weak;               /* COUNT of payload' bits with m <= MG_MAX */
uint16_t n_tied;               /* COUNT of payload' bits with m == 0     */

/* per payload' bit, during decide_pass: */
if (m <= MG_MAX) {
    n_weak++;
    if (m == 0) n_tied++;
    insert_sorted(t, m);       /* keeps the A_MAX smallest, ties by index */
}
```

`n_weak` counts **all** weak bits, including those that did not fit the
list — §7.5 depends on knowing when the list is *incomplete*.

Ordering rule for ties in `m`: **ascending bit index**. This makes the
candidate list a deterministic function of the decode, which the phase-3
parity harness relies on.

### 6.3 What `decide_pass` no longer does

Deleted: the `conf[]` and `tied[]` bitmaps (2 × 59 B), the knife
candidate list (32 × u16), the resolved list (16 × u16), and the
`is_knife`/`is_resolved` predicates. The `bits[]` bitmap stays.

### 6.4 Dead-window candidates — LEVER B (2026-09-08)

> **Status: LIVE in v2.3** (`DW_EN = 1`), off in every compat mode.
> Normative in `approaches/embedded_v2.py`; `decode.c` and
> `decode_asm.s` are bit-exact against it. Measurements:
> `approaches/dev_lever_b/`, full write-up `PROD_CLOSURE.md` §19.

**The problem this fixes.** With the capture front end repaired (§16 of
the phase report) the front-end refusals `R1`/`R3` are at ~0 and what is
left is **content**: `R6 refuse_nocand` — `n_weak == 0`, so
reconstruction errors exist (mean ~1 bit/frame) but *no bit was admitted
as a weak candidate*, the chase has nothing to try, and the 16-bit check
simply refuses. The wrong bits carry a **large apparent margin**.

**Why the margin lies.** A payload' bit's **discriminating interval** is
the only wire-time window in which a sample can tell 0 from 1:

```
A = off·BIT_U + h0c      the fall position if the bit is 0
B = off·BIT_U + h1c      the fall position if the bit is 1
```

(`h0c`/`h1c` = the family-calibrated boundaries `decide` already uses;
`off` = the bit's offset inside its segment). Below `A` the line is high
either way; above `B` it is low either way. And the *entire* observation
is the fall bracket `(u, v]` — `u` the last HIGH sample, `v` the first
LOW sample, **adjacent in the sample comb**, so no sample lies strictly
between them. Write

```
ga = (A <= u)            gb = (v < B)
```

`ga != gb` is the **healthy** case: exactly one of the two candidate fall
positions lies inside the bracket, i.e. a sample *decided* the bit.
`ga == gb` is **degenerate**, and covers both ways that happens:

| class | condition | what it means |
|---|---|---|
| **MID** | `ga = gb = 1`, i.e. `A ≤ u` and `v < B` | the bracket lies **inside** the window: a transition *was* seen, but at NEITHER fitted boundary, so the polarity rests on which boundary is nearer — on the width fit, not on a sample |
| **DEAD** | `ga = gb = 0`, i.e. `u < A` and `B ≤ v` | the window lies **inside** the bracket: **no sample in it at all**, both hypotheses admitted |
| ONLY_A | `u < A ≤ v` only | the 0-fall was observed |
| ONLY_B | `u < B ≤ v` only | the 1-fall was observed |
| EARLY | `v < A` | bracket entirely before the window |
| LATE | `B < u` | bracket entirely after the window |

**Measured, and it is not the class the v1 archive expected.** Over
1 440 synthetic production frames (ND = 48, plateau × 12 arm phases) plus
the 90 real ND = 16 captures — `dev_lever_b/geomclass.py`, 362 880
payload' bits:

| class | bits | share | wrong | **P(wrong)** | margin p50, right / wrong |
|---|---:|---:|---:|---:|---|
| **DEAD** | 78 | 0.02 % | 7 | **8.97 %** | 0 / 0 |
| **MID** | 3 476 | 0.96 % | 310 | **8.92 %** | 38 / 13 |
| ONLY_A | 285 479 | 78.67 % | 265 | 0.0928 % | 95 / 54 |
| ONLY_B | 53 967 | 14.87 % | 52 | 0.0964 % | 73 / 38 |
| EARLY | 2 903 | 0.80 % | 0 | **0.0000 %** | 147 / — |
| LATE | 16 977 | 4.68 % | 0 | **0.0000 %** | 255 / — |

**1 % of the bits carry half the wrong bits — a 91× enrichment.** And
the v1 archive's dead window (`archive/design-phase/approaches/combined.py`'s
`DEAD_PRIOR_NATS`, the "both hypotheses interior" test) is the **DEAD**
row: it is real, but every DEAD bit already carries **margin 0** through
§7's tie mark, so it is already weak and already a candidate. **Of the
590 DEAD bits found across 1 530 frames, exactly 0 have margin >
MG_MAX** — a DEAD-only lever was measured at **+0 deliveries and −1**
(`dev_lever_b/order.py`). Everything Lever B recovers is **MID**.

**The rule (normative).**

```c
#define DW_OFF_MAX 64        /* off*BIT_U <= 32256, + h1c <= 424 -> s16 */
uint8_t is_dw = 0;
if (off < DW_OFF_MAX) {
    int16_t hb = (int16_t)(off << BIT_SH);
    is_dw = (((int16_t)(hb + h0c) <= u) == (v < (int16_t)(hb + h1c)));
}
```

Stateless — `hb` is a pure function of `off`, no accumulator, no latch.
`DW_OFF_MAX` costs **nothing in behaviour**: `h0c ≥ H0_LO − FAM_CLAMP −
EPS_CLAMP56 = 64 > 0`, so once `hb > v` the test already answers
"healthy" on its own (`hb + h0c > v ≥ u` kills `ga`, `hb + h1c > v`
sets `gb`); the guard exists only to keep `hb + h1c` inside s16 on an
arbitrarily long merged run. **Proven bit-identical to a latched
running-`hb` form over 3 483 frames, every corpus and both fuzz sets**
(`dev_lever_b/equiv_hb.py`, 0 differing).

**Candidate policy.** A **DW candidate** is a payload' bit with
`is_dw && margin > MG_MAX` — degenerate geometry carrying a *confident*
apparent margin, which is exactly the R6 mechanism. It joins the
candidate list through the **same §6.2 sorted insertion, unchanged**:

```c
if (m <= MG_MAX)      { n_weak++; if (!m) n_tied++; cand_insert(k, m); }
else if (DW_EN && is_dw) {        n_dw++;           cand_insert(k, m); }
```

There is **no second pool and no second key**. A weak bit's margin is
`≤ MG_MAX` and a DW bit's is `> MG_MAX`, so the single ascending margin
key already places every weak entry ahead of every DW entry. Three
consequences, all structural rather than measured:

1. **R7's completeness invariant is untouched.** "`n_weak ≤ A_MAX` ⟹ the
   list holds every weak bit" still holds, because a DW entry can never
   sort ahead of a weak one. No eviction rule, no reserved slots.
2. **Truncation drops the WORST DW entry first** — the highest-margin,
   least-suspicious one.
3. **`R6` becomes literally "nothing to chase": `n_cand == 0`.** That is
   equivalent to `n_weak == 0 && n_dw == 0` (`cand_insert` bails out only
   when the insertion index reaches `A_MAX`, impossible while the list is
   empty, so the first admitted bit of either class always lands) and it
   is one byte cheaper on the target.

`A_MAX`, `T_MAX`, `MG_MAX`, `MG_PAIR`, `A_PAIR`, `TIE_EMIT`, `W_MAX` are
**all unchanged**. §7.10's W2 bound reads `npair = n` at the v2.3
constants (`A_PAIR = A_MAX`, `MG_PAIR = MG_MAX`), i.e. "pairs come only
from ADMITTED candidates" — and a DW bit *is* an admitted candidate; its
margin is precisely the quantity the geometry says nothing about. This is
what `decode.c` compiles (the `A_PAIR`/`MG_PAIR` test is `#if`'d out at
these constants) and what `decode_asm.s` assembles (no test at all).

**Why widening the candidate set does not widen the risk.** `T_MAX` is
the false-accept bound and it is a bound on **residual comparisons**, not
on candidates: every emission has paid at most `131 · 2⁻¹⁶ = 0.1997 %` of
exposure regardless of how the flip sets were chosen. That is the whole
reason a geometric admission rule is affordable here and was not
affordable under the 8-bit check.

**Ranking: measured irrelevant.** A two-ended layout that gives the DW
bits their own sorted prefix *ahead* of the weak ones was built and
compared frame by frame: over 3 483 frames the two differ in **outcome on
exactly one**, where the simple form *delivers* and the ranked-first form
refuses at the `T_MAX` budget; 156 more differ only in `trials`/`comps`
(`dev_lever_b/order.py`). The simple form is kept — it is ~80 B of
assembly and 3 B of RAM cheaper and needs no invariant repair.

**Prior: measured out.** The v1 audit's per-family "fewer-ones" prior
does reproduce in this class — in the admitted pool a bit decoded **1**
is wrong 21.27 % of the time against 2.34 % for a bit decoded 0, and
family 1 with `decoded = 1` is wrong **92.1 %** of the time (314 of 341)
while families 0/1/5 with `decoded = 0` are wrong 0 % — but neither use
of it pays (`dev_lever_b/prior.py`, `order.py`):

| variant | deliveries | median comparisons per chase |
|---|---:|---:|
| key `(margin, index)` — **shipped** | +59 | 14 |
| key `(decoded=1 first, margin, index)` | +59 | **16** — *worse* |
| admit only `decoded = 1` bits | **+55** | 8 |

Ordering by the prior gains nothing and *costs* two comparisons; the
admission form buys a 43 % trial reduction for **4 deliveries**, against
a `T_MAX` that is exhausted on 0.06 % of frames. There is no trial
pressure to spend deliveries on, so **the prior is left out** and no
per-family table is shipped.

**Budget pressure, reported and not acted on** (`dev_lever_b/pressure.py`,
6 450 frames: ND = 48 plateau + envelope × 12 arm phases plus the 90 real
ND = 16 captures):

* the list truncates on **42.6 % of chases** (273 of 641); over chased
  frames `n_weak + n_dw` is p50 11 / p90 27 / p99 67 / max 89, so
  `A_MAX = 89` would be needed to stop truncating at all — 4 006 flip
  sets against 67;
* `T_MAX` is exhausted on **4 of 6 450 frames (0.06 %)**, 0.62 % of
  chases, and **no delivered frame came within 10 comparisons of it**;
* **a bigger `T_MAX` buys nothing measured**: re-decoding the whole grid
  at 200 / 262 / 658 comparisons (0.30 % / 0.40 % / 1.00 % exposure)
  yields **+0 deliveries and +0 wrong** — the 4 budget-exhausted frames
  do not have their repair in the list at all;
* a bigger `A_MAX` does buy deliveries, and it costs: +16 at 16 and +63
  at 27 with 0 wrong, but **+142 at 89 with +1 WRONG** — and `A_MAX` is
  also the R7 admission cap, so raising it re-admits the broadly-wrong
  frames §7.5 was built to refuse. **Owner's decision, not taken here.**

**Cost.** Detector + routing + the R6 gate = **+30 B** of assembly and
**+2 B** of zero page (`v_ndw`, a u16 exposed as a linker global rather
than a `dec_info` field so the target pays nothing for reporting). Three
size levers more than paid for it — see the phase report §19.3; the
shipped decoder is **8 B smaller** with the feature in it, the terse
image has **42 B free** (was 34) and the stack region is unchanged at
148 B.

---

## 7. The CRC8 confidence chase

Notation: `D[0..ND-1]` decoded data bytes, `C[0..2]` decoded check
bytes, `NPP = ND + 3`. Payload' bit index `k ∈ [0, 8·NPP)`, MSB-first:
byte `p = k >> 3`, bit-value weight `b = 7 − (k & 7)`.

### 7.1 Reference and the direct check

```
R = majority(C[0], C[1], C[2])          /* 2-of-3 byte equality       */
      = C0            if C0 == C1 or C0 == C2
      = C1            if C1 == C2
      = NONE          otherwise (all three differ)

r_base = crc8(D)                        /* bitwise, table-free        */

if R != NONE and r_base == R:  EMIT D   /* direct accept, no chase    */
```

`crc8` is the 8-shifts-per-byte bitwise form — no 256-byte table (it
would not fit the flash budget and is not needed: one CRC8 over 48 bytes
costs ~2.3 k cycles, 0.05 % of a decode).

### 7.2 The trial loop needs no CRC recomputation

CRC8 with init 0x00 and xorout 0x00 is **linear over GF(2)**: for any
error pattern `e`, `crc8(D ⊕ e) = crc8(D) ⊕ crc8(e)`. Verified
exhaustively over 3000 random 1–3-bit patterns at ND = 48, 0 mismatches
(`../archive/investigations/dev_v2spec/v21.py` self-check; the same property was verified over
2000 patterns in the earlier `crc_vectors.py`).

The single-bit syndrome has a closed form. For a data bit at byte `p`,
weight `b`, its distance from the end of the message is
`j = 8·(ND − 1 − p) + b`, and

```
syn8(p, b) = x^(j + 8)  mod  (x^8 + x^2 + x + 1)
```

**The order of `x` modulo 0x107 is 127** (measured — 0x107 factors as
`(x+1)(x^7+x+1)`, and `x^7+x+1` is primitive of degree 7). So a
**127-byte flash table indexed mod 127 covers every frame size**:

```c
static const uint8_t XPOW[127] = { 0x01,0x02,0x04,0x08,0x10,0x20,0x40,
                                   0x80,0x07,0x0E,0x1C,0x38,0x70,0xE0,
                                   0xC7,0x89, ... };      /* x^0 .. x^126 */

#define SYN8(p, b)  XPOW[ (8u*(ND - 1u - (p)) + (b) + 8u) % 127u ]
```

Verified: 0 mismatches against a direct `crc8` of every unit error
vector, at both ND = 16 and ND = 48 (`dev_v2spec`, §"XPOW formula").
The `% 127` is a subtract-while-≥ loop (at most 4 iterations at ND = 48).

Bits inside the **check bytes have no CRC syndrome** — they are not part
of the message. Flipping one changes the *reference*, not the residual.
That asymmetry drives the trial ordering in §7.4.

Two structural properties of poly 0x07 that matter and are **not** coin
flips (both verified in `dev_v2spec`):

- `(x+1)` divides the polynomial ⇒ **every odd-weight error is
  detected**, and the syndrome's byte parity equals the error weight
  parity. This gives a free **parity gate** (§7.4).
- Every single-bit error is detected (no syndrome is zero), and every
  burst up to 8 bits is detected.

And one that cuts the other way, stated plainly because it sets the
chase's floor (§8.3): with order 127, the **384 production data-bit
positions map onto only 127 distinct single-bit syndromes** — about 3
positions per syndrome. Two positions 127 bits apart are
*indistinguishable* to the chase.

### 7.3 The residual test

For a trial flip set `S ⊆ candidates`:

```
C'      = C with S's check-byte bits toggled
R'      = majority(C'[0], C'[1], C'[2])        /* may be NONE       */
r'      = r_base ⊕ XOR{ SYN8(p,b) : (p,b) ∈ S, p < ND }
PASS   iff  R' != NONE  and  r' == R'
```

A trial whose `R'` is NONE is skipped (it consumes a trial slot but can
never pass).

### 7.4 Trial enumeration — order and budget

Candidates are `cand_t[0..n_cand-1]`, already sorted ascending by margin
(§6.2). Enumeration is **data-minimal, cheapest-first**: the sort key is

```
( number of DATA bits flipped , weight , summed margin , index tuple )
```

which decomposes into a fixed five-phase loop nest — **no sorting is
needed on the target**:

| phase | flips | why it comes first |
|---|---|---|
| 1 | one check bit | leaves DATA untouched; cannot corrupt the payload |
| 2 | two check bits | ditto |
| 3 | one data bit | the classic single knife-bit repair |
| 4 | one data + one check bit | |
| 5 | two data bits | most invasive, tried last |

Within a phase, iterate candidate indices ascending (`i`, then `j > i`).
**Measured: this cheap index order and an exact summed-margin sort give
byte-identical results** — 675/1710 delivered, 0 catastrophic at
production scale; 520/1026, 0 catastrophic at test scale
(`dev_v2spec`, ordering comparison). The target ships the index order.

Rationale for putting check-only flips first: the check block is
disposable — the receiver needs it only to verify, and it is 3 of 19 (or
3 of 51) bytes on the same corrupted wire. A mismatch explained by
*check* damage costs the payload nothing; one explained by *data* damage
rewrites the payload. Preferring the former is the strictly safer error
hypothesis. This ordering was worth removing one catastrophic at test
scale in the sweep that selected it (`../archive/investigations/dev_v2spec/sweep3.py`: `wmajor` 1
catastrophic vs `dfirst` 0, same delivery).

**Weight cap `W_MAX = 2`. Budget**

```
T = 1 + n + n(n−1)/2        with  n = n_cand ≤ A_MAX = 5     ⇒  T ≤ 16
```

The `1` is the empty trial, which *is* the direct check of §7.1 and is
not re-evaluated.

> **Superseded by §7.10 (v2.2a).** The pair phases (2, 4, 5) are now
> additionally restricted to the candidate prefix `[0, n_pair)`, which
> lowers the budget to `T ≤ 1 + n + C(A_PAIR,2) = 9`. Everything else in
> this subsection is unchanged.

**Parity gate (free, exact).** Trials in phases 3 and 5 do not touch the
check bytes, so `R' = R` is fixed. A weight-`w` data-only flip set has a
syndrome of parity `w mod 2`. Therefore:

```
if parity(r_base ⊕ R) == 0:  skip all of phase 3   (data singles)
if parity(r_base ⊕ R) == 1:  skip all of phase 5   (data pairs)
```

This removes trials that provably cannot pass. It halves the loop work
and changes neither delivery nor false-accept exposure (the skipped
trials had pass probability exactly 0).

### 7.5 Admission gates — the part that actually bounds the risk

A chase over a frame that is *broadly* wrong is pure risk: the true fix
is not in the list, the budget is spent, and each trial gets a free
1/256 shot at emitting garbage. Measured, this is not a theoretical
concern — it dominates. With no admission gate at all
(`../archive/investigations/dev_v2spec/e2e_v2.py`, N=8, W≤3, T=93, test scale, 432 decodes over
the 8 real trim codes): **51 catastrophics**, one in three chased frames
at the fast corners.

Two gates, both computed for free during the decision pass (§6.2):

```
G1  EMIT GATE       n_tied > TIE_EMIT (= 8)         -> REFUSE
                    (applies to the DIRECT path too — see below)
G2  ADMISSION GATE  n_weak == 0                     -> REFUSE (nothing to chase)
                    n_weak >  A_MAX (= 5)           -> REFUSE (list is incomplete;
                                                       the error is probably outside it)
```

**G1 also gates the direct accept.** This is deliberate and measured. At
+7.5 % the sampler misses so many windows that `0xFF` decodes as `0xAA`
*and the check block `0F 0F 0F` decodes as `0A 0A 0A` by the same
systematic mechanism* — all three copies agree, the majority is
confidently wrong, and `crc8(mangled data)` coincidentally equalled it.
That is a catastrophic no chase policy can touch, because no chase ran.
Measured with the full §7 policy otherwise unchanged, over the whole
±8 % envelope:

| direct-path emit gate | test scale (n = 1026) | production scale (n = 1710) |
|---|---|---|
| none | 564 delivered, **3 catastrophic** | 716 delivered, **3 catastrophic** |
| **`n_tied ≤ 8`** | **520 delivered, 0 catastrophic** | **675 delivered, 0 catastrophic** |

The 44 (test) / 41 (production) lost deliveries are all at |eps| ≥ 5 %,
where the delivery rate is ~11 % and ~3 % anyway. Given the owner's rule
that a catastrophic is strictly worse than a refusal, `TIE_EMIT = 8` is
normative. **Note it is an absolute count, not a fraction** — 8 of 152
payload' bits at test scale, 8 of 408 at production scale; the tighter
production behaviour is intended.

**Why `n_weak > A_MAX` refuses rather than truncating.** If more bits are
weak than the list can hold, the list no longer *contains* the ambiguity
— the chase would be searching a strict subset of the plausible error
patterns while still paying the full false-accept exposure. Refusing is
the honest move. Measured at production scale (§7.6) this rule is what
takes catastrophics to zero.

### 7.6 Choosing `A_MAX` and `W_MAX` — the budget justification

The trial budget is **not** chosen from the 1/256 arithmetic. It is
chosen from the measured catastrophic-zero frontier, on 2736 end-to-end
decodes of real v2.1 rev2 frames spanning ±8 % clock error
(`../archive/investigations/dev_v2spec/final.py`; emit gate 8, `MG_MAX = 8`, alias guard on):

**Production, 48 B data / 472-bit frame (n = 1710; strong band = the 8
points in −2.5…+1.3 %, n = 720)**

| admission | W | T_max | all ±8 %: delivered / +chase / CAT | strong band: delivered / +chase / CAT |
|---|---|---|---|---|
| chase OFF | — | — | 644 (37.7 %) / — / 0 | 574 (79.7 %) / — / 0 |
| ≤ 2 | 2 | 4 | 660 (38.6 %) / +16 / 0 | 587 (81.5 %) / +13 / 0 |
| ≤ 3 | 2 | 7 | 668 (39.1 %) / +24 / 0 | 590 (81.9 %) / +16 / 0 |
| ≤ 4 | 2 | 11 | 671 (39.2 %) / +27 / 0 | 592 (82.2 %) / +18 / 0 |
| **≤ 5** | **2** | **16** | **675 (39.5 %) / +31 / 0** | **594 (82.5 %) / +20 / 0** |
| ≤ 6 | 2 | 22 | 679 (39.7 %) / +35 / **1** | 595 (82.6 %) / +21 / 0 |
| ≤ 8 | 2 | 37 | 684 (40.0 %) / +40 / **2** | 597 (82.9 %) / +23 / 0 |

**Test, 16 B data / 216-bit frame (n = 1026; strong band n = 432)**

| admission | W | T_max | all ±8 %: delivered / +chase / CAT | strong band |
|---|---|---|---|---|
| chase OFF | — | — | 501 (48.8 %) / — / 0 | 388 (89.8 %) / 0 |
| ≤ 4 | 2 | 11 | 519 (50.6 %) / +18 / 0 | 395 (91.4 %) / 0 |
| **≤ 5** | **2** | **16** | **520 (50.7 %) / +19 / 0** | **395 (91.4 %) / 0** |
| ≤ 6 | 2 | 22 | 526 (51.3 %) / +25 / **1** | 395 (91.4 %) / 0 |
| ≤ 8 | 2 | 37 | 538 (52.4 %) / +37 / **5** | 395 (91.4 %) / 0 |

`A_MAX = 5, W_MAX = 2, T_max = 16` is **the largest budget that is
catastrophic-free on both corpora simultaneously**. `A_MAX = 6` breaks
both. Going to `A_MAX = 8` (the owner's ≤ 8 ceiling) would buy +9
production deliveries and +18 test deliveries at the price of 2 and 5
catastrophics respectively — a trade the single-transmission rule
forbids.

`W_MAX = 3` was also swept and is worse everywhere it was tried: at test
scale, admission 3 / W ≤ 3 / T = 93 gives 3 catastrophics against 0 for
W ≤ 2 (`../archive/investigations/dev_v2spec/sweep3.py`). The chase is a *knife-bit* repair, not
an error-correcting code.

### 7.7 The alias guard

The order-127 collapse of §7.2 has a concrete failure mode, and it was
observed: a production frame at +1.0 % with exactly one wrong data bit,
`n_tied = 2`, `n_weak = 3` — the chase's first weight-1 trial matched
the residual **at the wrong candidate**, because that candidate's
position was 127 bits away from the true one and therefore carried an
identical syndrome. Two wrong bits emitted, CRC-clean.

Guard, applied at the moment a trial passes (it is a validity condition
on the accepted hypothesis, not a continuation of the search — the
"stop at first pass" rule of §2.5 is intact):

```
on PASS with flip set S:
    for each data bit i in S:
        for each candidate j not in S, j a data bit:
            if SYN8(j) == SYN8(i):  reject this trial, continue the loop
```

Cost: `n_cand² ≤ 25` byte compares, once. Measured at the **final
budget** of §7.6 (`A_MAX = 5`, `W_MAX = 2`, `T ≤ 16`), production scale,
n = 1710:

| guard | delivered | catastrophic |
|---|---|---|
| none | 676 | **1** |
| **alias (normative)** | **675** | **0** |
| unique-pass (run the whole budget, accept only if exactly one trial passes) | 665 | 0 |

The same three at the looser `A_MAX = 4 / T = 11` point
(`../archive/investigations/dev_v2spec/guards.py`) read 672/1, 671/0, 663/0 — the guard's effect
is stable across budgets.

The alias guard costs one recovery in 1710 and removes the catastrophic.
The unique-pass variant also reaches zero but costs ten recoveries at
production scale and five at test scale, gains nothing the alias guard
has not already taken, and would change the owner-fixed "stop at first
pass" rule. **The alias guard is normative; unique-pass is not adopted**
(see §13.5 for the standing option).

At test scale the guard is inert: 128 data-bit positions is just past
127, so there is exactly one aliasing pair and it never fired. It is
production scale that needs it.

### 7.8 The all-three-differ fallback

When `R = NONE` at the top of the chase, the primary loop still works —
phases 1 and 2 flip check bits and can *create* a majority, and a trial
whose `R'` is still NONE is skipped. That path is normative and is
already covered by §7.3–7.7.

If the primary loop is exhausted and the base block had no majority, a
**bounded secondary path** is defined (mirroring
`bench/crc.reference_candidates`):

```
refs = [ C[q0], C[q1], C[q2] ]     ordered by DESCENDING per-byte
                                   confidence = sum of the 8 bit margins
                                   of that check byte (ties: wire order)
for R_f in refs:
    for S over data candidates only, |S| <= W_FB (= 1):     /* T_FB = 1 + n_data */
        if r_base ^ XOR SYN8(S) == R_f:  EMIT
```

False-accept math for the two paths:

| path | references | trials | bound `1 − (1 − refs/256)^T` |
|---|---|---|---|
| primary (majority exists) | 1 | ≤ 16 | **6.07 %** per chase that runs to exhaustion |
| primary (no majority; check-repair trials only) | 1 | ≤ 16 | 6.07 % |
| fallback, 3 references, `W_FB = 1`, `T_FB ≤ 6` | 3 | ≤ 6 | **6.87 %** |
| fallback if it were given the full budget (`T = 16`, 3 refs) | 3 | 16 | 17.19 % |

**Default: `CHASE_SPLIT_VOTE = 0` (fallback OFF).** Measured at the
final budget of §7.6, enabling it changes **nothing**: 520 delivered /
0 catastrophic at test scale and 675 / 0 at production scale, identical
to the fallback-off figures. At the looser budgets swept it was actively
harmful — at `A_MAX = 8 / W ≤ 2 / T = 37` it delivered the same 534
frames at test scale and added **1 catastrophic**
(`../archive/investigations/dev_v2spec/sweep3.py`, `dfirst fb=1` vs `fb=0`), and the same at
production scale.

So the fallback buys zero deliveries while tripling the per-trial false
accept exposure (6.87 % vs 6.07 %, table above). The reason is visible in
§2.3: an all-differ block means ≥ 2 of the 24 check bits are wrong,
which is strong evidence that the *frame* is bad, not just its check
block. The code path is specified so it can be enabled behind a build
flag if a future corpus changes the answer; it must not be enabled
without re-running `../archive/investigations/dev_v2spec/sweep3.py` and `../archive/investigations/dev_v2spec/numbers.py`.

All-differ frequency, measured: **90 / 1618 emitted-or-analysed
production decodes = 5.6 %** (§2.3).

### 7.9 Pseudocode (normative)

```c
/* ---- state produced by decide_pass (§6.2) ---------------------------- */
uint8_t  bits[NBB];                  /* whole-frame bit array            */
uint16_t cand_t[A_MAX]; uint8_t cand_m[A_MAX];
uint8_t  n_cand;  uint16_t n_weak, n_tied;

/* ---- constants ------------------------------------------------------- */
#define CHK_LEN   3
#define MG_MAX    8       /* TU: a bit is "weak" at <= 8 TU (19.5 ns)     */
#define A_MAX     5       /* candidate list capacity AND admission cap    */
#define W_MAX     2
#define A_PAIR    3       /* §7.10 W2 bound: pair phases use cand[0..2]   */
#define MG_PAIR   4       /*          ... and only at margin <= 4 TU      */
#define TIE_EMIT  8       /* absolute count of zero-margin payload' bits  */
#define ND        48      /* 16 in the test build                         */
#define NPP       (ND + CHK_LEN)

/* ---- C1: assemble ---------------------------------------------------- */
uint8_t P[NPP];  bits_to_bytes(bits + 4, P, NPP);      /* skip HEADER     */
uint8_t *D = P, C0 = P[ND], C1 = P[ND+1], C2 = P[ND+2];
uint8_t r_base = crc8(D, ND);
uint8_t R, have_R;
if      (C0 == C1 || C0 == C2) { R = C0; have_R = 1; }
else if (C1 == C2)             { R = C1; have_R = 1; }
else                           { R = 0;  have_R = 0; }

/* ---- C2: direct accept ----------------------------------------------- */
if (n_tied > TIE_EMIT)          return REFUSE;         /* G1, both paths  */
if (have_R && r_base == R)      return EMIT(D);

/* ---- C3: admission --------------------------------------------------- */
if (n_weak == 0 || n_weak > A_MAX)  return REFUSE;     /* G2              */

/* ---- C4/C5: bounded, data-minimal, cheapest-first -------------------- */
uint8_t par = parity8(r_base ^ R);                     /* only if have_R  */
for (phase = 1; phase <= 5; phase++) {
    if ( have_R && phase == 3 && par == 0 ) continue;  /* parity gate     */
    if ( have_R && phase == 5 && par == 1 ) continue;
    FOR each flip set S of this phase, candidate indices ascending:
        if (|S| == 2 && max(S) >= n_pair) continue;    /* §7.10 W2 bound  */
        C' = {C0,C1,C2} with S's check bits toggled;
        R' = majority(C');            if (R' == NONE) continue;
        r' = r_base;
        for (i in S) if (cand_t[i] is a DATA bit) r' ^= SYN8(cand_t[i]);
        if (r' != R') continue;
        if (alias_ambiguous(S)) continue;              /* §7.7            */
        apply S's DATA flips to D;
        return EMIT(D);
}
return REFUSE;                                          /* chase exhausted */
```

Worst-case trial count: 16 (**9** with §7.10). Worst-case alias-guard
compares: 25.

### 7.10 The W2 bound (v2.2a) — pairs come only from the weakest candidates

**Why.** On 2026-09-07 the Klipper corpus produced the project's first
two wrong emissions (PROD_CLOSURE §11.4). Both check blocks were
**unanimous**, so the majority-of-4 vote is exonerated; both emissions
differed from ground truth in exactly **four bits, all 0→1, inside a
≥ 96-bit all-zero run**, and in both cases

```
XOR over the four error bits of SYN8(k)  =  0x00
```

i.e. the emitted error was an **undetectable weight-4 CRC-8 codeword**
(verified for both recorded frames). An 8-bit check cannot survive 15
enumerated weight-≤2 candidates on frames that badly decoded, and **10
of those 15 are pair sets** — two thirds of the whole exposure buys 18 %
of the repairs (measured: 151 of 847 chase accepts across the four
verified corpora plus the production-geometry sweeps).

**Rule (normative).**

```
A_PAIR  = 3        /* a weight-2 trial may only combine candidates
                      cand[0..A_PAIR-1] -- the weakest ones      */
MG_PAIR = 4        /* ... and only ones at margin <= 4 TU (9.8 ns) */

n_pair = 0;
while (n_pair < n_cand && n_pair < A_PAIR && cand_m[n_pair] <= MG_PAIR)
    n_pair++;
```

Phases 2, 4 and 5 skip any pair whose **larger** index is `>= n_pair`.
`cand_m` is non-decreasing (§6.2 insertion), so the eligible set is a
*prefix* and the larger member of a pair carries both the larger index
and the larger margin — one comparison implements the whole rule, and
the surviving trials are a **subsequence of the §7.4 order**, so the
first passing admissible trial is unchanged. Phases 1 and 3 (all the
weight-1 repairs) are untouched.

**Budget and false-accept math.**

```
T <= 1 + n_cand + C(A_PAIR, 2) = 1 + 5 + 3 = 9      (was 16)
crc.fa_prob_crc8(9, 1)  = 3.46 %   per chased frame   (was 6.07 %)
crc.fa_prob_crc8(9, 2)  = 6.82 %   2-2 tie fallback   (was 11.79 %)
```

(These are the **8-bit** numbers, so from v2.3 on they live in
`crc.fa_prob_crc8`; `crc.fa_prob` is now the 16-bit function. The whole
reason this bound had to be so tight is the 8-bit check: v2.3's 16-bit
check affords 131 wrong trials at a 0.2 % wrong-emission target, where
the 8-bit check affords none — see `../../docs/PROTOCOL.md`.)

This is a **hard, data-independent** bound: unlike a margin-only rule it
does not degrade to 15 trials when every candidate happens to be weak.
Measured reduction in `P(wrong | accept)` over the production-geometry
sweeps is **1.446 % → 0.836 %**, i.e. 1.73×, against the 1.76× the
arithmetic predicts.

**Measured cost.** Zero deliveries across `captures_v21{,_val}.json` +
`captures_v22{,_val}.json` (166/180 before and after, 146 direct + 20
chase both ways). In the post-fix-#1 operating band (eps −1.6…−0.4 %)
the cost is exactly zero and there are no chase false-accepts to remove
— the bound is insurance for the thermal/arm-timing excursions, and
§11.4's exposure lives on the fast side that fix #1 vacates.

---

## 8. False-accept math — stated honestly

### 8.1 The per-trial figure

An 8-bit check accepts a wrong candidate with probability 2⁻⁸ per
reference. Over `T` wrong candidates actually evaluated:

```
P(at least one false accept) = 1 − (1 − refs/256)^T
```

| T | 1 reference | 3 references |
|---|---|---|
| 4 | 1.55 % | 4.61 % |
| 7 | 2.70 % | 7.92 % |
| 11 | 4.21 % | 12.16 % |
| **9 (this spec, §7.10)** | **3.46 %** | 10.07 % |
| 16 (v2.2, before §7.10) | 6.07 % | 17.19 % |
| 37 | 13.48 % | 35.35 % |
| 93 | 30.51 % | 66.59 % |

A refinement, for accuracy rather than comfort: the parity gate (§7.4)
means only trials of the *correct* weight parity are ever evaluated, and
those pass falsely with probability ≈ 1/128 (a weight-`w` syndrome ranges
over the 128 values of its parity coset — measured: 127 distinct values
at w = 1, 128 at w = 2 and 3, near-uniform). Half the trials at 1/128
gives the same aggregate `T/256`, so the table above is correct as
written; the gate buys cycles, not safety.

### 8.2 What that means per frame

The 6.07 % figure is **conditional on a chase running to exhaustion with
the true fix absent from the list**. It is not a per-frame rate. The
per-frame rate is what the admission gates control, and it is measured:

| corpus | frames | chases executed | trials evaluated, total | expected false accepts = trials/256 | **observed** |
|---|---|---|---|---|---|
| production, 472-bit, ±8 % | 1710 | 52 (3.0 %) | 190 | **0.74** | **0** |
| test, 216-bit, ±8 % | 1026 | 40 (3.9 %) | 252 | **0.98** | **0** |

Mean trials per chase: 3.7 (production), 6.3 (test) — far below the
worst case of 16, because most chases stop at phase 1 or 3.

Per-frame catastrophic exposure, upper bound, production:
`52/1710 × 6.07 % = 0.18 %`. Using the actual trial count rather than
the worst case: `0.74/1710 = 4.3 × 10⁻⁴` per frame. **Observed across
the whole 2736-decode corpus: zero.**

That is the honest ceiling. It is not zero, and no CRC8-only scheme can
make it zero — but it is bounded, it is two to three orders of magnitude
below the rate of frames the chase *saves*, and it is measured to be
below the resolution of a 2736-decode corpus.

### 8.3 The floor that the polynomial sets

Three things cannot be engineered away without changing the wire format
(which is fixed):

1. **Direct-accept exposure.** A frame whose data is wrong but whose
   `crc8(D)` happens to equal the decoded majority is accepted with no
   chase at all, at rate 2⁻⁸ over wrong frames that reach the direct
   check. The emit gate (§7.5) is the only lever, and it costs
   deliveries. Measured residual after the gate: 0 in 2736.
2. **Syndrome aliasing.** Order 127 means 3.02 production data positions
   per single-bit syndrome. The alias guard (§7.7) converts the
   in-list case into a refusal; two *out-of-list* aliases are invisible.
3. **HD limit.** Published CRC-8 selection tables give poly 0x07
   HD = 4 for datawords up to 119 bits. Our test dataword is 128 bits
   and the production dataword 384 bits, both past it — so **do not
   assume all 2- and 3-bit errors are caught**. Measured for our
   lengths: 1 undetectable double-bit pair among 8128 at ND = 16, and
   390 among 73536 at ND = 48 (0.53 %).

---

## 9. Refusal policy

There is **one copy of every frame** (§2.5). The decoder's job is to
maximise verified deliveries subject to zero catastrophics.

### 9.1 The gates, in evaluation order

| # | gate | condition | why |
|---|---|---|---|
| R1 | hard lock failure | no first rise / no latch / `K` outside `[K_MIN, K_MAX]` | v1, unchanged |
| R2 | marker violation | any HEADER/TRAILER bit decoded against the template | v1, unchanged — the strongest single evidence the lock is wrong |
| R3 | infeasible | `infeasible > GATE_INFEAS (4)` | v1, unchanged |
| R4 | label error | `label_err > GATE_LABERR (6)`, with the dead-marker-window adaptation (a window where both hypotheses are interior is *not* a label error, or the entire +5…+7.5 % corner refuses wholesale) | v1, unchanged |
| R5 | **emit gate** | `n_tied > TIE_EMIT (8)` | **new, §7.5** — applies to the direct path as well |
| R6 | **no candidate** | CRC mismatch and the candidate list is EMPTY (`n_weak == 0` **and** `n_dw == 0` — §6.4 admits dead-window bits too) | **new** — nothing to chase; the frame is confidently wrong |
| R7 | **admission** | CRC mismatch and `n_weak > A_MAX (5)` | **new, §7.5** — the candidate list does not contain the ambiguity |
| R8 | **chase exhausted** | all ≤ 16 trials evaluated, none passed the residual test and the alias guard | **new** — the honest end of the road |

### 9.2 When to emit

Emit if and only if:

- R1–R5 all pass, **and**
- either `crc8(D) == majority(C)` directly (path `direct`), or a chase
  trial passed the residual test and the alias guard (path `chase`).

Never emit on a CRC mismatch. Never emit with `R = NONE` unless a trial
repaired the check block into a majority (§7.8).

### 9.3 Refusal accounting, measured

Where the refusals actually come from (production, 1710 decodes, ±8 %,
`../archive/investigations/dev_v2spec/numbers.py`):

| refusal cause | count | share of all frames |
|---|---|---|
| R1–R4 hard gates | 92 | 5.4 % |
| R5 emit gate | 783 | 45.8 % |
| R6 no candidate | 8 | 0.5 % |
| R7 admission | 131 | 7.7 % |
| R8 chase exhausted | 21 | 1.2 % |
| **delivered** | **675** | **39.5 %** |

The R5 mass is almost entirely at |eps| ≥ 2.5 %, where the sampler
simply does not see enough of the waveform (§12.2). Inside the strong
band the same table reads 594 delivered of 720 (82.5 %).

### 9.4 What the application must do with a refusal

A refusal is a missed frame: the LED state must **hold its previous
value**, not blank and not partially update. The decoder writes the
output buffer only on the emit path. At the WS2812 host's 10 Hz frame
rate, a refusal costs 100 ms of staleness — visually invisible, and
strictly better than a wrong colour block.

---

## 10. Budgets

### 10.1 Flash

v1 measured, per function, SDCC 4.6 `-mstm8 --opt-code-size`, NB = 448
(`EMBEDDED_FEASIBILITY.md` §5). The itemised functions sum to **7309 B**;
the report's stated total is 7.37 KB code + ~0.35 KB SDCC 32-bit
mul/div library + 40 B const = **7.8 KB**.

| function | v1 bytes | v2 |
|---|---|---|
| `votes` | 1038 | **REMOVED** |
| `ps_next` (sample scanner) | 798 | keep |
| `decide_pass` | 750 | keep, **−70 (est.)** bitmaps, **+150 (est.)** margin + top-5 insertion |
| `refine` | 697 | keep |
| `theta56` | 669 | keep |
| `calibrate` | 649 | keep |
| `ss_next` | 634 | keep |
| `decide` | 528 | keep (margin is already computed; it is now returned) |
| `ps_init` / `ss_init` / `a_bounds` | 306 | keep |
| `known_bit`, `cal_cloud`, `map_y`, misc | 293 | **−60 (est.)** (`is_knife`, `is_resolved`, `OADJ_U` path) |
| `cal_add` | 277 | keep |
| `ws_decode` | 260 | keep |
| `label_interval` | 219 | keep |
| `seed` | 191 | keep |
| **new** `crc8` bitwise | — | **+45 (est.)** |
| **new** `chase` (5-phase enumerator, syndrome XOR, majority, apply) | — | **+420 (est.)** |
| **new** `majority` + reference + alias guard + parity gate | — | **+90 (est.)** |
| **new** `XPOW[127]` const | — | **+127 (exact)** |
| removed `OADJ_U[8]` const | 8 | −8 |

```
code   7.37 KB − 1038 − 70 − 60 + 150 + 45 + 420 + 90  =  7.37 KB − 463 B
                                                       ≈  6.92 KB   (est.)
const  40 B − 8 B + 127 B                              =  159 B
lib    0.35 KB (unchanged: the chase adds no 32-bit mul or div)
TOTAL                                                  ≈  7.43 KB   (est.)
```

**Verdict: still does not fit.** Minimum production application is
2.5 KB (feasibility §5: gamma LUT shrunk to 256 B, no debug UART), so
7.43 + 2.5 ≈ **9.93 KB against 8.19 KB — over by ~1.74 KB (21 %)**,
improved from v1's 2.30 KB (28 %) but not closed.

The paths are unchanged from the feasibility report and both remain
open:

- **Hand-assembly of the streaming layer.** `ps_next` + `ss_next` +
  `refine` bodies are ~2.1 KB of C whose SDCC codegen costs ~10–14 B per
  source operation; a rewrite is a realistic −2…−2.5 KB. That closes the
  gap with margin. Unproven until done.
- **Part change.** A pin-compatible STM8S003/005 or S103K3 removes the
  constraint at board-respin cost.

What v2 changes about this risk: the cut is now in code that carries
**no accuracy** (the votes were replaced by a *better-measured*
mechanism, §12.4), where v1's only remaining cuts were the eps analog
(−7 captures) and the votes (−8). The accuracy-vs-size cliff has moved
1.7 KB further away.

### 10.2 RAM

v1 measured DATA = **781 B** + 187 B peak stack (SDCC map, NB = 448).
Deltas for v2 at NB = 472:

| item | Δ | note |
|---|---|---|
| capture buffer 256 → 288 | **+32** | §3, mandatory |
| `bits[]` bitmap 56 → 59 | **+3** | NB/8 |
| `conf[]` + `tied[]` bitmaps | **−112** | 2 × 56, gone with the votes |
| knife list 32 × u16 | **−64** | gone |
| resolved list 16 × u16 | **−32** | gone |
| candidate list `cand_t[5]` u16 + `cand_m[5]` u8 + counters | **+18** | §6.2 |
| chase working set (`P[]` overlays the payload buffer; `C0..C2`, `R`, `r_base`, `par`, phase/loop regs) | **+16** | |
| payload out 48 → 51 | **+3** | the 3 check bytes land here too |
| **net** | **−136** | |

```
DATA  ≈ 781 − 136 = 645 B      (call it 651 B with (est.) slop)
stack ≈ 187 B peak measured in v1; v2 removes the votes() frame and adds
        a shallow chase frame -> budget 192 B unchanged
app   ≈ 80 B (ws2812_out 48 + timers/flags)

TOTAL ≈ 651 + 192 + 80 = 923 B  of 1024  ->  ~101 B margin
```

**The v1 histogram overlay is no longer mandatory.** v1 needed it
(1053 B without). v2 fits with 101 B to spare and *still has the overlay
available* — the two 64-byte eps fold histograms are dead before the
decision pass first writes `bits[]`, so overlaying them gives 795 B and
**229 B margin** if the application grows.

### 10.3 Cycles

v1 measured 4.41 M ucsim ticks for a 448-bit decode, of which `votes`
was 252 k (feasibility §6). ucsim under-reads this silicon by ~7 % on
this instruction mix (calibrated against the one hardware-exact loop).

```
v2 core = (4.41 M − 0.252 M) × 472/448 = 4.381 M ticks
```

New work:

| item | est. ticks |
|---|---|
| per-bit margin + top-5 insertion, 472 bits | ~3.8 k |
| `crc8` over 48 data bytes, bitwise | ~2.3 k |
| ≤ 16 trials × (≤ 2 XPOW loads + XOR + 3 compares + `%127`) | ~0.7 k |
| majority, alias guard, byte assembly | ~0.4 k |
| **total** | **~7 k (est.)** |

```
v2 total ≈ 4.39 M ticks   (v1: 4.41 M)
with +7 % silicon correction ≈ 4.70 M cycles ≈ 294 ms @ 16 MHz
```

**The votes removal exactly pays for the 5.4 % longer frame.** v2 is not
slower than v1, and the chase is 0.16 % of the decode — it is free.

The 100 ms goal still fails by ~3× as plain SDCC C, for the same reason
as v1 (~200+ ticks per sample visit measured against ~15–20 attainable).
The tight-assembly projection of ~62–95 ms is unchanged and remains
unproven. If the goal is relaxed, a 0.3 s decode against a 10 Hz input
gives a ~3 Hz display update, because frames latch.

---

## 11. HSITRIMR auto-trim — opportunistic hygiene only

**Normative: the decoder never depends on trim.** It locks wide-band
(±7.5 %) single-shot from the frame's own header/trailer, with no
operating-point pinning, no fresh trim, and no thermal forward model
(the STM8S001J3 has **no on-chip temperature sensor** — DS12129 §4.12
provides only a temperature-independent bandgap).

After a **successful, CRC-verified** decode, and only then, the firmware
may nudge `CLK_HSITRIMR` toward the measured operating point. This
serves the debug UART (which breaks beyond ~±4.5 % clock error) and
keeps the sampler near the band where swallowed-zero and merge artifacts
are mildest. It is never required for decoding.

Recovering eps from the lock (integer, no division beyond one):

```
K is Q11 TU/cycle, K_NOM = 52429.        eps ≈ (K_NOM − K) / K
eps_x100 = ((int32)(K_NOM − K) * 10000) / K / 100      /* percent × 100 */
```

Trim map, measured on this unit at 3.3 V (`TRIM_SWEEP.md`, 96 captures,
12 per code, two independent estimators agreeing to 0.04–0.14 %):

| code | signed value | mean eps | sd |
|---|---|---|---|
| 4 | −4 | +3.733 % | 0.037 % |
| 5 | −3 | +2.492 % | 0.019 % |
| 6 | −2 | +1.274 % | 0.033 % |
| 7 | −1 | **+0.022 %** | 0.034 % |
| 0 | +0 (factory) | −1.072 % | 0.043 % |
| 1 | +1 | −2.248 % | 0.073 % |
| 2 | +2 | −3.281 % | 0.021 % |
| 3 | +3 | −4.385 % | 0.041 % |

The mapping is **signed 3-bit two's complement**, strictly monotonic in
signed order, mean step −1.16 % (worst-case residual after optimal
trimming ≈ ±0.6 %). Total authority −4.38 %…+3.73 %.

Policy:

```
after EMIT:
    eps_meas = eps_from_K();
    v_target = clamp(round((eps_meas + 1.07) / 1.16) as signed 3-bit, -4, +3);
    if (v_target != v_current && |eps_meas| > 0.6%)   /* hysteresis */
        CLK_HSITRIMR = encode_signed3(v_target);
```

Never trim on a refusal (the eps estimate came from a lock the decoder
just declined to trust). Never trim mid-capture. Restore factory trim
around UART transmission if the firmware follows the trim-sweep
firmware's pattern (`TRIM_SWEEP.md`, "Firmware design" — all UART at
factory trim, which is why 96/96 dumps arrived clean).

**Known trade, measured** (`TRIM_SWEEP.md`): trimming to eps ≈ 0 is
optimal for the UART and eliminates swallowed zeros, but it *maximises*
1-bit merging on dense-ones data (64 merged loops on `ones` at code 7 vs
5–12 at the slow codes) — a resonance, because at eps ≈ 0 the 40-cycle
loop is exactly 2 bit periods and the end-of-loop gap lands at the same
bit-grid phase every loop. The decoder models merging exactly, and the
merging is deterministic there, so this is handled. If it ever becomes a
problem, target eps ≈ +1…+2.5 % instead — still inside the strong band,
merging drops to ~5/frame, swallowing stays zero.

---

## 12. Measured behaviour

All figures below are single-shot: one capture, one decode, no
repetition.

### 12.1 Real silicon, real v2.1-length frames

`data/captures_v21.json` and `data/captures_v21_val.json` are **real
bench captures of 27-byte frames** (216 bits — the true v2.1 geometry) at
this unit's factory trim (eps ≈ −1.1 %). Their check block is the v2.1
**rev1** layout (`CRC16_HI || CRC16_LO || CRC8`), superseded by rev2, so
the CRC *arithmetic* cannot be replayed on them — but what the chase
actually depends on can be, and is (`../archive/investigations/dev_v2spec/real_v21.py`): with the
votes cut and the §7 admission policy applied,

| corpus | n | exact pre-CRC | chase-reachable | **ceiling** | out of reach |
|---|---|---|---|---|---|
| `captures_v21.json` | 54 | 47 (87.0 %) | +4 | **51 / 54 (94.4 %)** | 3 |
| `captures_v21_val.json` (unseen patterns) | 36 | 31 (86.1 %) | +4 | **35 / 36 (97.2 %)** | 1 |

Wrong-bit histogram over the 152 payload' bits: `{0: 47, 1: 4, 2: 2,
3: 1}` and `{0: 31, 1: 4, 3: 1}`. Check-block bits were themselves wrong
in 1 of 54 frames — the case triplication exists for.

### 12.2 End-to-end, real v2.1 rev2 frames, synthetic captures

Generator = `synth.py` with the fitted sampler model, validated at
99.93 % mean sample agreement against the real captures
(`HSI_TEMPERATURE.md`). Policy: `TIE_EMIT = 8`, `MG_MAX = 8`,
`A_MAX = 5`, `W_MAX = 2`, data-minimal ordering, alias guard on,
split-vote fallback off.

**Production (48 B data, 472-bit frame), 90 decodes per clock point**

| eps | delivered | direct | chase | refuse | CAT |
|---|---|---|---|---|---|
| −8.0 % | 0 (0.0 %) | 0 | 0 | 90 | 0 |
| −7.5 % | 0 (0.0 %) | 0 | 0 | 90 | 0 |
| −5.0 % | 14 (15.6 %) | 13 | 1 | 76 | 0 |
| −4.385 % (trim 3) | 0 (0.0 %) | 0 | 0 | 90 | 0 |
| −3.281 % (trim 2) | 17 (18.9 %) | 16 | 1 | 73 | 0 |
| −2.5 % | 60 (66.7 %) | 60 | 0 | 30 | 0 |
| −2.248 % (trim 1) | 60 (66.7 %) | 59 | 1 | 30 | 0 |
| −1.072 % (trim 0, factory) | 79 (87.8 %) | 74 | 5 | 11 | 0 |
| −1.0 % | 87 (96.7 %) | 85 | 2 | 3 | 0 |
| 0.0 % | 89 (98.9 %) | 89 | 0 | 1 | 0 |
| +0.022 % (trim 7) | 87 (96.7 %) | 86 | 1 | 3 | 0 |
| +1.0 % | 70 (77.8 %) | 66 | 4 | 20 | 0 |
| +1.274 % (trim 6) | 62 (68.9 %) | 55 | 7 | 28 | 0 |
| +2.492 % (trim 5) | 16 (17.8 %) | 13 | 3 | 74 | 0 |
| +2.5 % | 22 (24.4 %) | 22 | 0 | 68 | 0 |
| +3.733 % (trim 4) | 9 (10.0 %) | 3 | 6 | 81 | 0 |
| +5.0 % | 3 (3.3 %) | 3 | 0 | 87 | 0 |
| +7.5 % | 0 (0.0 %) | 0 | 0 | 90 | 0 |
| +8.0 % | 0 (0.0 %) | 0 | 0 | 90 | 0 |
| **total** | **675 / 1710 (39.5 %)** | 644 | **31** | 1035 | **0** |

**Test (16 B data, 216-bit frame), 54 decodes per clock point**

| eps | delivered | CAT | | eps | delivered | CAT |
|---|---|---|---|---|---|---|
| −8.0 % | 2 (3.7 %) | 0 | | +0.022 % | 54 (100 %) | 0 |
| −7.5 % | 4 (7.4 %) | 0 | | +1.0 % | 40 (74.1 %) | 0 |
| −5.0 % | 22 (40.7 %) | 0 | | +1.274 % | 37 (68.5 %) | 0 |
| −4.385 % | 4 (7.4 %) | 0 | | +2.492 % | 22 (40.7 %) | 0 |
| −3.281 % | 31 (57.4 %) | 0 | | +2.5 % | 25 (46.3 %) | 0 |
| −2.5 % | 54 (100 %) | 0 | | +3.733 % | 10 (18.5 %) | 0 |
| −2.248 % | 54 (100 %) | 0 | | +5.0 % | 3 (5.6 %) | 0 |
| −1.072 % | 51 (94.4 %) | 0 | | +7.5 % | 0 (0.0 %) | 0 |
| −1.0 % | 51 (94.4 %) | 0 | | +8.0 % | 2 (3.7 %) | 0 |
| 0.0 % | 54 (100 %) | 0 | | **total** | **520 / 1026 (50.7 %)** | **0** |

Strong band (−2.5 %…+1.3 %): **594/720 = 82.5 %** production,
**395/432 = 91.4 %** test, 0 catastrophic in both.

### 12.3 Read this correctly

- **Production frames are 2.2× longer than test frames and deliver
  materially worse.** At the factory operating point, 87.8 % (production)
  against 94.4 % (test). This is the single most important number in the
  document for anyone sizing the system: more bits, more chances for the
  one knife bit that costs the frame.
- **The corner zeros are refusals, not errors.** Beyond ±5 % up to half
  the payload windows are never sampled; this is the physical dead-window
  ceiling documented in `HSI_TEMPERATURE.md`, not a v2 regression.
- **The synthetic and real corpora agree where they overlap.** At the
  factory trim point the synthetic test-scale figure is 51/54 (94.4 %)
  and the real 27-byte corpus ceiling is 51/54 (94.4 %).
- **The chase's contribution is modest and real**: +31 of 1710 at
  production scale (+4.8 % relative), +19 of 1026 at test scale. It is
  not an error-correcting code; it is a knife-bit repair with a receipt.

### 12.4 What v2 buys against v1, honestly

| | v1 (votes) | v2 (chase) |
|---|---|---|
| 54 real bench captures, v2.0 payloads | 51/54 exact (94.4 %) | 50/54 ceiling (92.6 %) |
| every emission verified? | **no** | **yes** |
| refusals on 174 real captures | **0** | gated by §9 |
| **silently wrong payloads on those 174 real captures** | **40 (23 %)** — 3 bench, 4 validation, 33 trim | — |
| catastrophics, 2736 end-to-end v2.1 decodes across ±8 % | n/a (no CRC to check against) | **0** |
| flash | 7.8 KB | ≈ 7.43 KB (est.) |
| RAM | 781 B DATA, overlay mandatory | ≈ 651 B DATA, overlay optional |
| cycles | 4.41 M @448 bits | 4.39 M @472 bits |

v2 gives up one capture in 54 at the bench point and buys a receipt on
every one of the rest. Across the trim sweep the exchange is not close:
v1 emits 33 wrong payloads in 96 with a straight face; v2 emits none,
and converts what it cannot verify into refusals the application can
see. Under the single-transmission rule — where a silent wrong payload
is unrecoverable and unnoticeable and a refusal merely holds the last
frame — that is the trade the owner asked for.

---

## 13. Phase-3 validation — acceptance criteria

### 13.1 Prerequisite: acquire a rev2 corpus

`data/captures_v21.json` / `_val.json` carry the **rev1** check layout.
Phase 3 cannot start until they are re-acquired with
`payload' = DATA || [CRC8]×3` (`bench/patterns.py` `PATTERNS_V21` /
`VAL_PATTERNS_V21` already build this; `bench/crc.py` is the authority).
Required corpus:

| corpus | content | n |
|---|---|---|
| C1 bench | 18 patterns × 3 reps, factory trim | 54 |
| C2 validation | 12 unseen patterns × 3 reps, factory trim | 36 |
| C3 trim sweep | 6 patterns × 8 trim codes × 2 reps (spans −4.4 %…+3.7 %) | 96 |
| C4 production geometry | ≥ 20 distinct 48-byte payloads × 3 reps × ≥ 3 trim codes, 59-byte frames | ≥ 180 |

C4 is not optional. Every production-scale number in §12.2 is synthetic;
the 472-bit frame has never been on this bench's wire.

### 13.2 Per-frame criteria — SINGLE SHOT

**Every capture must decode on its own.** No repetition, no voting
across reps, no "the pattern decoded in rep 1 so it counts". Each
capture is scored independently against its own ground truth.

| # | criterion | threshold | rationale |
|---|---|---|---|
| **A1** | **Catastrophic rate** — a payload emitted that differs from ground truth | **exactly 0**, on every corpus, every trim code | owner-fixed; a silent wrong payload is unrecoverable under single transmission |
| A2 | Delivery, C1 (bench, 216-bit) | ≥ 90 % (measured ceiling 94.4 %) | §12.1 |
| A3 | Delivery, C2 (unseen patterns) | ≥ 90 %, and within 5 points of A2 | generalisation, not tuning |
| A4 | Delivery, C4 (production, 472-bit), at trim 0 / 7 / 6 | ≥ 80 % (synthetic predicts 87.8 / 96.7 / 68.9 %) | §12.2; the 68.9 % at +1.27 % is the binding point |
| A5 | Delivery, C3, pooled over all 8 trim codes | ≥ 60 % (synthetic predicts 62 %) | wide-band, no fresh trim |
| A6 | Refusals are honest | every refusal, when scored against ground truth, is a frame the decoder could not have decoded correctly, **or** a frame whose correct decode was outside the admitted candidate set | a refusal that hides a decodable frame is a policy bug |
| A7 | Chase yield | ≥ 3 % of delivered frames come via the chase path on C3 | if the chase never fires it is dead flash |
| A8 | Trial budget respected | no decode evaluates > 16 trials; alias-guard compares ≤ 25 | §7.4 |
| A9 | Determinism | two runs over the same corpus produce byte-identical output and identical path labels (`direct` / `chase` / refusal cause) | v1 requirement, carried forward |

**Scoring definitions, to be applied literally:**

```
delivered    = emitted AND equal to ground truth
CATASTROPHIC = emitted AND not equal to ground truth        -> A1 fails
missed       = refused                                      -> counts against A2..A5
```

A refusal is a miss. There is no third category.

### 13.3 Parity and budget criteria

| # | criterion | threshold |
|---|---|---|
| B1 | C port vs Python reference | byte-identical output **and identical path label** on 100 % of C1–C4 |
| B2 | Fixed-point asserts at NB = 472 | zero u16/s16/u32/s32 violations across all of C1–C4 and the synthetic envelope |
| B3 | Capture buffer | correct decode from the **first 288 bytes only** on C4 at every trim code, including trim 4 (+3.73 %) |
| B4 | RAM | SDCC map DATA ≤ 660 B; measured peak stack ≤ 192 B; total with app ≤ 1024 B |
| B5 | Flash | recorded, per function, against §10.1's estimate; every (est.) line replaced by a measurement |
| B6 | Cycles | ucsim ticks ≤ 4.5 M on a 472-bit decode; chase ≤ 10 k ticks |
| B7 | CRC vectors | `CRC8("123456789") == 0xF4`; §2.4's two frame vectors reproduce byte-for-byte on target |
| B8 | `XPOW[127]` | on-target `SYN8(p,b)` matches a direct `crc8` of the unit error vector for all 408 production data-bit positions |

### 13.4 Envelope criterion, stated honestly

The ±7.5 % requirement is a *lock* requirement, and the decoder meets
it: it acquires K and tau single-shot across the whole band with no
prior. It is **not** a delivery requirement, and no decoder can make it
one: at |eps| ≥ 5 % up to half the payload's sampling windows fall in
dead zones and the information is simply not in the capture
(`HSI_TEMPERATURE.md` §2; both the host and the embedded v1 decoder sit
on the same ceiling).

| # | criterion | threshold |
|---|---|---|
| C1 | Lock acquired (K within `[K_MIN, K_MAX]`, markers consistent) across −7.5 %…+7.5 % | ≥ 95 % of captures |
| C2 | **Catastrophic rate at every corner including ±8 %** | **exactly 0** |
| C3 | Delivery at ±7.5 % | recorded, no threshold — expected 0–8 % |

C2 is the criterion that matters at the corners. A decoder that refuses
everything beyond ±5 % passes C2 and C3; one that emits a wrong colour
frame there fails outright.

### 13.5 Standing options requiring owner sign-off

Two measured alternatives are specified but **not enabled**, because
each would change an owner-fixed rule. Numbers are given so the decision
can be made on evidence, not taste:

| option | what it changes | measured effect at the final budget |
|---|---|---|
| **unique-pass accept** (run the full ≤ 16-trial budget, accept only if exactly one trial passes) | violates the owner-fixed "stop at first CRC8 pass" | production −10 deliveries (675 → 665), test −5 (520 → 515); catastrophic already 0 with the alias guard, so this buys a second independent 0 at a real delivery cost |
| **split-vote fallback** (`CHASE_SPLIT_VOTE = 1`, §7.8) | enables the 3-reference path when all three check bytes differ | **+0 deliveries, +0 catastrophic** at the final budget; **+1 catastrophic** at the looser budgets swept. Triples per-trial exposure for no measured gain — do not enable |

---

## 14. Risks

1. **Flash is still the hard wall.** ~1.74 KB over (est.) beside a 2.5 KB
   application. v2 moved it 0.56 KB in the right direction and moved the
   remaining cut out of accuracy-critical code, but the wall stands.
   Mitigations unchanged: hand-assembly of the streaming layer
   (−2…−2.5 KB projected) or a part change.
2. **Every production-scale number is synthetic.** The 472-bit frame has
   never been captured on this bench. Corpus C4 (§13.1) is the gate.
3. **The rev2 corpus does not exist yet.** `captures_v21*.json` carry
   the superseded rev1 check layout.
4. **CRC8 sets a floor that cannot be engineered away** (§8.3): the
   direct-accept 2⁻⁸ exposure, order-127 syndrome aliasing, and HD < 4
   at our dataword lengths. Measured residual is 0 in 2736 decodes, but
   the bound is 4.3 × 10⁻⁴ per frame, not 0.
5. **The emit gate costs deliveries at the corners.** `TIE_EMIT = 8`
   trades 44 deliveries in 1026 (test) and 41 in 1710 (production), all
   at |eps| ≥ 5 %, for 3 catastrophics on each corpus. If the owner ever
   re-weights that trade, re-run `../archive/investigations/dev_v2spec/numbers.py` with the gate
   varied — do not adjust the constant by intuition.
6. **`A_MAX = 5` is calibrated against two corpora, not a theory.**
   `A_MAX = 6` produced catastrophics on both. A materially different
   payload distribution (e.g. real GRB data with long runs) could move
   the frontier; A1 in §13.2 is the tripwire.
7. **Model drift.** The decoder still hard-codes the fitted sampler
   geometry in integer cycles. A change to the capture loop's
   instruction alignment silently invalidates `W_CY[]`. The
   `dev_calibration/` re-verification procedure must gate any capture
   loop edit — unchanged from v1, and now also gates the `XPOW`/frame
   constants because `ND` appears in `SYN8`.
8. **`nibbles_1`-class captures** remain a known −1 against the host: no
   single-geometry decoder recovers them, and a static per-slot offset
   table was measured harmful (35/54). The chase reaches some of this
   class (they are low-margin single bits) but not reliably.

---

## 15. Files

Specification inputs (unmodified):

- `EMBEDDED_FEASIBILITY.md` — v1 ablations, per-function flash, cycle
  measurements, RAM map.
- `approaches/embedded_ref.py` — v1 integer reference; §4's contract.
- `../archive/investigations/dev_embedded/decoder.c` — v1 C port; the functions §10.1
  costs.
- `DATASET.md` (ADDENDUM), `HSI_TEMPERATURE.md`, `TRIM_SWEEP.md`.
- `../bench/crc.py`, `../bench/patterns.py` — the host side of §2; this
  spec's receiver policy mirrors `majority` / `reference_candidates` /
  `fa_prob_crc8`, which from v2.3 on are the explicitly labeled CRC8
  compat helpers (the v2.3 wire uses `check_block_v23` /
  `reference_bytes_v23` / `fa_prob`).

Measurement scratch for this spec (`../archive/investigations/dev_v2spec/`, all new):

- `v21.py` — v2.1 rev2 format + reference chase (`syn_table`, `maj3`,
  the three orderings, the two guards, the fallback).
- `ref_marg.py` — v1 integer reference instrumented with per-bit
  margins; reproduces 51/54 with votes ON.
- `e2e_v2.py`, `prod_e2e.py` — end-to-end harnesses (test / production
  scale) with decode caches.
- `sweep.py`, `sweep2.py`, `sweep3.py`, `sweep_prod.py`,
  `sweep_prod2.py`, `guards.py`, `final.py` — the sweeps that chose
  §7's constants.
- `numbers.py` — the single script that prints every figure in §8.2,
  §9.3 and §12.2.
- `real_reach.py`, `real_v21.py` — real-silicon containment.
- `diag.py` — the tie-count separator behind §7.5.
- `containment.py`, `correlate.py`, `crc_vectors.py`, `syndrome.py`,
  `syn_pow.py`, `budget.py` — earlier-round measurements.
- `EMBEDDED_V2_SPEC.rev1-superseded.md` — the previous draft of this
  document (CRC16 + repetition), kept for provenance.
