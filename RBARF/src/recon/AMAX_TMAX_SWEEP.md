# A_MAX x T_MAX — THE CHASE BUDGET, SWEPT AND MADE A BUILD PARAMETER

2026-09-08, branch `amax-tmax-sweep`, from `2d329ee` (Lever B + the
single-shot suite).  **Host measurement plus a firmware
parameterisation.  Nothing was flashed; no bench number is claimed.**

The owner's question: *raise `A_MAX` and `T_MAX` and see if delivery
improves.*  Delivery = FIRST-TRY latch of a single frame, the
`bench/suite_singleshot.py` rule (no retries, no repeats).

**THE ANSWER, up front.**

* Delivery improves, and **barely**: the best point anywhere on the
  5 x 5 grid is **+13 frames in 16 800** (94.05 % -> 94.13 %, **+0.077
  pp**), and it costs 2 WRONG emissions at production geometry inside
  the auto-trim band.
* The **largest gain with zero wrong emissions is +9** (+0.054 pp), at
  `A_MAX = 16`, and it needs `T_MAX >= 192`.
* **`A_MAX >= 18` emits WRONG frames in the operating band.**  Two named
  false accepts (`klipper/rnd_colors2` at eps -1.20 %, t0 = 633 ns, and
  `demo/rain` at eps -1.20 %, t0 = 145 ns) reached through 75-224-trial
  chases.  That is a categorical stop: the project's headline axis is
  zero wrong emissions on the ND = 48 plateau.
* On a deliberately-corrupted 40 000-frame corpus the **measured**
  false-accept rate rises monotonically with the budget:
  **0.068 % -> 0.096 % -> 0.173 %** at (11,131) / (14,131) / (16,192),
  and to 0.389 % at (40,1048).  **It is not zero at the baseline
  either** — see §4.
* The real-silicon corpus `data/captures_v23.json` is **completely flat
  across all 25 points**: 53/54 everywhere, the one miss an `R8` whose
  repair is not in the candidate list at any capacity.

So the honest headline is *"a fraction of a percent of delivery, bought
with a doubling of measured false accepts, and it turns negative on
correctness above `A_MAX = 16`"* — which reproduces and sharpens §19.2's
warning that `A_MAX` "is also the R7 admission cap, so raising it
re-admits the broadly-wrong frames §7.5 was built to refuse".

---

## 1. What the two constants are, and why they interact

| | shipped | what it caps | cost axis |
|---|---:|---|---|
| `A_MAX` | 11 | candidate-list capacity **and** the R7 admission cap (`n_weak > A_MAX` -> R7).  Flip sets = `1 + A_MAX + C(A_MAX,2)`, worst-case trials `A_MAX*(A_MAX+1)/2` | 3 B of RAM per entry; decode TIME through trials |
| `T_MAX` | 131 | residual comparisons.  It **is** the per-frame false-accept bound, `fa = 1-(1-2^-16)^T` | the false-accept bound, and the blind window |

`A_PAIR` **tracks `A_MAX`** everywhere in this work.  v2.3's `_chase23`
sets `npair = n` and never reads `A_PAIR`; `decode.c`'s SS7.10 test is
`#if`'d out *because* `A_PAIR == A_MAX && MG_PAIR == MG_MAX`.  Pinning
them together is what keeps `1 + n + C(n,2)` true and keeps the three
implementations bit-identical at every point.  `MG_MAX`, `MG_PAIR`,
`TIE_EMIT`, `W_MAX`, `DW_EN` are untouched.

**The interaction is the whole story, and it is signed.**  Every extra
candidate adds trials, every trial spends at least one comparison, and
the comparison budget is *shared with the trials that come before the
repair in the cheapest-first enumeration*.  So at fixed `T_MAX` a bigger
`A_MAX` can PUSH THE TRUE REPAIR PAST THE BUDGET:

* `A_MAX 11 -> 16` at `T_MAX = 131`: **-4 frames** (a regression).
* the same `A_MAX 16` at `T_MAX = 192`: **+9**.
* `A_MAX 18` at `T_MAX = 131`: **-11**; at 192: **+11** (but 1 WRONG).

Neither constant has a 1-D curve.  Table 4 is the interaction; the
single frame that carries the sign flip is named in §3.

---

## 2. Method

| corpus | what | size |
|---|---|---|
| **(a) operating grid** | the **70 unique payloads of `bench/suite_singleshot.py`** (imported by exec-up-to-`main()`, the way that script imports its own tables), synthetic capture at eps -0.60/-0.80/-0.90/-1.05/-1.20 % x **48** arm phases spanning the measured 70..658 ns, ND = 48 production geometry | **16 800 captures** x 25 points |
| **(b) real silicon** | `data/captures_v23.json`, ND = 16 | 54 captures x 25 |
| **(c) corruption grid** | random payloads, 5 strata: 1-3 / 1-4 (slots R0..R5 only) / 1-6 random **sample-bit flips**, clean eps +-8 % (the R7 carriers a bigger `A_MAX` re-admits), and drift+trunc+chop | **40 000 frames** x 25 |

Driver: `recon/approaches/embedded_v2.py` — the **normative** reference —
through `dev_prod/v23lib.py`, exactly the way `dev_suite/dw_ab_suite_failures.py`
drives the `DW_EN` A/B.  The single entry point is the reference's own
new `set_chase_budget(a_max, t_max)`, which mirrors `decode.c`'s
`A_MAX_CFG`/`T_MAX_CFG` (and `A_PAIR` tracking `A_MAX`).

**`data/captures_val.json` was never opened.**

**Grid-independence shortcut, validated not assumed.**  A frame that
refuses at R1/R2/R3/R4/R5, or accepts DIRECT, never reads either
constant — the admission gates (C3) and the comparison budget both sit
*after* the direct accept in `_chase23` — so one decode answers the whole
grid for it.  `sweep_amax_tmax.py --validate` re-decodes a random sample
at all 25 points with no shortcut and compares: **600/600 and 450/450
captures identical across all 25 points, 0 mismatches**.  2 085 of the
16 800 operating captures actually reach the chase.

**Model-domain exclusions.**  188 of the 40 000 corrupted frames trip the
reference's own s16 range assertion in P3 (`_seg_stream`), on captures so
malformed that the fitted `(K, tau)` puts a segment offset outside s16.
That is strictly pre-chase and therefore grid-independent; the target's
real s16 arithmetic would wrap, the reference refuses to model it.  They
are counted separately and are in **neither** the delivered nor the
refused columns.

**Time projection.**  `worst-case ms = 170 + 0.54 x min(A_MAX*(A_MAX+1)/2, T_MAX-1)`.

* **0.54 ms per chase trial** — `PROD_CLOSURE.md` §15.7 ("**≈ 8.6 k
  ticks (0.54 ms) per chase trial**, of which the recomputed 384-step
  CRC is ~4.5 k"), restated in `docs/ARCHITECTURE.md` §5.4.  It is the price
  of the assembly tail recomputing `crc16(d_pp)` per trial instead of
  carrying the `XP8` syndrome table.  **Verified from both sources.**
* **170 ms fixed** — `PROD_CLOSURE.md` §20.4's measured decode window on
  silicon over the 60-frame Lever B gate: min 163.7 / **mean 170.0** /
  max 182.9 ms.  It is the mean of windows that already include whatever
  chase ran, so using it as the *fixed* term is mildly conservative.
* `min(flip sets, T_MAX-1)` because every trial spends at least one
  comparison and the direct accept already spent one.

---

## 3. THE FULL GRID

### Table 1 - corpus (a): the 70 single-shot payloads, ND=48, 16800 captures per point
(70 payloads x -0.60/-0.80/-0.90/-1.05/-1.20 eps x 48 arm phases 70..658 ns)

| A_MAX | T_MAX | delivered | % | vs base | WRONG | R3 | R6 | R7 | R8 | fa bound | trials mean/p99/max | comps mean/p99/max | worst-case ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 11 | 131 | 15801 | 94.05 % | +0 | **0** | 0 | 7 | 62 | 820 | 0.200 % | 2.56 / 56 / 65 | 3.87 / 58 / 131 | 205.6 |
| 11 | 262 | 15801 | 94.05 % | +0 | **0** | 0 | 7 | 62 | 820 | 0.399 % | 2.56 / 56 / 66 | 3.88 / 58 / 179 | 205.6 |
| 11 | 393 | 15801 | 94.05 % | +0 | **0** | 0 | 7 | 62 | 820 | 0.598 % | 2.56 / 56 / 66 | 3.88 / 58 / 179 | 205.6 |
| 11 | 524 | 15801 | 94.05 % | +0 | **0** | 0 | 7 | 62 | 820 | 0.796 % | 2.56 / 56 / 66 | 3.88 / 58 / 179 | 205.6 |
| 11 | 1048 | 15801 | 94.05 % | +0 | **0** | 0 | 7 | 62 | 820 | 1.586 % | 2.56 / 56 / 66 | 3.88 / 58 / 179 | 205.6 |
| 16 | 131 | 15797 | 94.03 % | -4 | **0** | 0 | 7 | 36 | 850 | 0.200 % | 3.92 / 100 / 126 | 5.39 / 121 / 131 | 240.2 |
| 16 | 262 | 15810 | 94.11 % | +9 | **0** | 0 | 7 | 36 | 837 | 0.399 % | 3.95 / 102 / 128 | 5.44 / 121 / 262 | 243.4 |
| 16 | 393 | 15810 | 94.11 % | +9 | **0** | 0 | 7 | 36 | 837 | 0.598 % | 3.95 / 105 / 136 | 5.46 / 121 / 393 | 243.4 |
| 16 | 524 | 15810 | 94.11 % | +9 | **0** | 0 | 7 | 36 | 837 | 0.796 % | 3.96 / 105 / 136 | 5.46 / 121 / 411 | 243.4 |
| 16 | 1048 | 15810 | 94.11 % | +9 | **0** | 0 | 7 | 36 | 837 | 1.586 % | 3.96 / 105 / 136 | 5.46 / 121 / 411 | 243.4 |
| 22 | 131 | 15785 | 93.96 % | -16 | **1** | 0 | 7 | 13 | 884 | 0.200 % | 4.47 / 117 / 131 | 5.96 / 131 / 131 | 240.2 |
| 22 | 262 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 13 | 855 | 0.399 % | 5.22 / 125 / 238 | 6.76 / 142 / 262 | 306.6 |
| 22 | 393 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 13 | 855 | 0.598 % | 5.23 / 127 / 238 | 6.80 / 142 / 393 | 306.6 |
| 22 | 524 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 13 | 855 | 0.796 % | 5.24 / 127 / 238 | 6.83 / 142 / 524 | 306.6 |
| 22 | 1048 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 13 | 855 | 1.586 % | 5.25 / 127 / 253 | 6.86 / 142 / 720 | 306.6 |
| 27 | 131 | 15783 | 93.95 % | -18 | **1** | 0 | 7 | 7 | 892 | 0.200 % | 4.60 / 120 / 131 | 6.11 / 131 / 131 | 240.2 |
| 27 | 262 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 7 | 861 | 0.399 % | 5.51 / 135 / 262 | 7.07 / 152 / 262 | 310.9 |
| 27 | 393 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 7 | 860 | 0.598 % | 5.85 / 137 / 359 | 7.43 / 152 / 393 | 374.1 |
| 27 | 524 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 7 | 860 | 0.796 % | 5.86 / 137 / 359 | 7.46 / 152 / 524 | 374.1 |
| 27 | 1048 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 7 | 860 | 1.586 % | 5.88 / 137 / 367 | 7.55 / 152 / 1048 | 374.1 |
| 40 | 131 | 15782 | 93.94 % | -19 | **1** | 0 | 7 | 1 | 899 | 0.200 % | 4.66 / 121 / 131 | 6.19 / 131 / 131 | 240.2 |
| 40 | 262 | 15813 | 94.12 % | +12 | **2** | 0 | 7 | 1 | 867 | 0.399 % | 5.63 / 140 / 262 | 7.21 / 158 / 262 | 310.9 |
| 40 | 393 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 1 | 866 | 0.598 % | 6.08 / 141 / 393 | 7.69 / 158 / 393 | 381.7 |
| 40 | 524 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 1 | 866 | 0.796 % | 6.33 / 141 / 524 | 7.96 / 158 / 524 | 452.4 |
| 40 | 1048 | 15814 | 94.13 % | +13 | **2** | 0 | 7 | 1 | 866 | 1.586 % | 6.62 / 141 / 785 | 8.33 / 158 / 1048 | 612.8 |

Total delivery gain available anywhere on the grid: **+13 frames** (15801 -> 15814, +0.077 pp); half of it is +6.5.

### Table 2 - corpus (c): MEASURED false accepts, 40000 corrupted frames
(39812 decodes after 188 model-domain exclusions; 14072 reach the chase)

| A_MAX | T_MAX | emissions | **WRONG** | measured rate | analytic fa bound | trials mean/p99/max |
|---:|---:|---:|---:|---:|---:|---:|
| 11 | 131 | 10307 | **7** | 0.0679 % | 0.200 % | 6.2 / 57 / 66 |
| 11 | 262 | 10312 | **7** | 0.0679 % | 0.399 % | 6.3 / 58 / 66 |
| 11 | 393 | 10312 | **7** | 0.0679 % | 0.598 % | 6.3 / 58 / 66 |
| 11 | 524 | 10312 | **7** | 0.0679 % | 0.796 % | 6.3 / 58 / 66 |
| 11 | 1048 | 10312 | **7** | 0.0679 % | 1.586 % | 6.3 / 58 / 66 |
| 16 | 131 | 10403 | **14** | 0.1346 % | 0.200 % | 11.4 / 122 / 126 |
| 16 | 262 | 10420 | **18** | 0.1727 % | 0.399 % | 11.8 / 122 / 134 |
| 16 | 393 | 10421 | **18** | 0.1727 % | 0.598 % | 12.0 / 123 / 136 |
| 16 | 524 | 10421 | **18** | 0.1727 % | 0.796 % | 12.0 / 123 / 136 |
| 16 | 1048 | 10421 | **18** | 0.1727 % | 1.586 % | 12.0 / 123 / 136 |
| 22 | 131 | 10413 | **12** | 0.1152 % | 0.200 % | 13.6 / 131 / 131 |
| 22 | 262 | 10474 | **27** | 0.2578 % | 0.399 % | 18.7 / 233 / 242 |
| 22 | 393 | 10482 | **27** | 0.2576 % | 0.598 % | 19.1 / 234 / 242 |
| 22 | 524 | 10483 | **27** | 0.2576 % | 0.796 % | 19.4 / 234 / 244 |
| 22 | 1048 | 10483 | **27** | 0.2576 % | 1.586 % | 19.7 / 235 / 253 |
| 27 | 131 | 10401 | **15** | 0.1442 % | 0.200 % | 14.7 / 131 / 131 |
| 27 | 262 | 10482 | **26** | 0.2480 % | 0.399 % | 21.4 / 262 / 262 |
| 27 | 393 | 10499 | **32** | 0.3048 % | 0.598 % | 25.0 / 353 / 363 |
| 27 | 524 | 10505 | **32** | 0.3046 % | 0.796 % | 25.4 / 354 / 364 |
| 27 | 1048 | 10509 | **33** | 0.3140 % | 1.586 % | 26.4 / 355 / 378 |
| 40 | 131 | 10372 | **12** | 0.1157 % | 0.200 % | 17.1 / 131 / 131 |
| 40 | 262 | 10464 | **22** | 0.2102 % | 0.399 % | 26.1 / 262 / 262 |
| 40 | 393 | 10502 | **29** | 0.2761 % | 0.598 % | 32.3 / 393 / 393 |
| 40 | 524 | 10520 | **33** | 0.3137 % | 0.796 % | 37.1 / 524 / 524 |
| 40 | 1048 | 10546 | **41** | 0.3888 % | 1.586 % | 45.6 / 782 / 795 |

### Table 3 - corpus (b): data/captures_v23.json, 54 real silicon captures, ND=16

Delivered at EVERY one of the 25 grid points: **[53]/54**; refusal cause at every point: [(('R8', 1),)]; WRONG 0 everywhere.  The corpus is completely FLAT over the grid.

### Table 4 - refinement A: delivered - baseline, the same 16800 captures

| A_MAX \ T_MAX | 131 | 160 | 192 | 224 | 255 | 262 |
|---:|---:|---:|---:|---:|---:|---:|
| **11** | +0 | +0 | +0 | +0 | +0 | +0 |
| **13** | +3 | +4 | +4 | +4 | +4 | +4 |
| **14** | +7 | +7 | +8 | +8 | +8 | +8 |
| **16** | -4 | +8 | +9 | +9 | +9 | +9 |
| **18** | -11 | +2 | +11 | +11 | +11 | +11 |
| **19** | -13 | +1 | +10 | +11 | +11 | +11 |

WRONG on the same grid (production geometry, trim band):

| A_MAX \ T_MAX | 131 | 160 | 192 | 224 | 255 | 262 |
|---:|---:|---:|---:|---:|---:|---:|
| **11** | 0 | 0 | 0 | 0 | 0 | 0 |
| **13** | 0 | 0 | 0 | 0 | 0 | 0 |
| **14** | 0 | 0 | 0 | 0 | 0 | 0 |
| **16** | 0 | 0 | 0 | 0 | 0 | 0 |
| **18** | 1 | 1 | 1 | 1 | 1 | 1 |
| **19** | 1 | 1 | 1 | 1 | 1 | 1 |

### Table 5 - refinement B: the T_MAX knee at A_MAX = 16

| T_MAX | 131 | 160 | 164 | 168 | 172 | 176 | 180 | 184 | 188 | 192 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| delivered - base | -4 | +8 | +8 | +8 | +8 | +8 | +8 | +8 | +8 | +9 |

### Table 6 - corpus (c) at the CHOSEN points (same 40000 frames, same seed)

| A_MAX | T_MAX | emissions | **WRONG** | measured rate | analytic fa bound |
|---:|---:|---:|---:|---:|---:|
| 11 | 131 | 10307 | **7** | 0.0679 % | 0.200 % |
| 11 | 192 | 10312 | **7** | 0.0679 % | 0.293 % |
| 14 | 131 | 10376 | **10** | 0.0964 % | 0.200 % |
| 14 | 192 | 10384 | **11** | 0.1059 % | 0.293 % |
| 16 | 131 | 10403 | **14** | 0.1346 % | 0.200 % |
| 16 | 192 | 10414 | **18** | 0.1728 % | 0.293 % |

(worst-case ms = 170 ms fixed pipeline + 0.54 ms x min(A_MAX*(A_MAX+1)/2, T_MAX-1))


---

## 4. Reading the grid

### 4.1 Where the gain comes from, frame by frame

`dev_amax/per_payload.py` keeps the outcome per payload AND per capture,
so no gain is a net figure hiding a regression.  Every capture whose
verdict moves, at both chosen points:

| point | payload | eps | t0 | baseline | new | trials/comps |
|---|---|---:|---:|---|---|---:|
| A14/T131 | `demo/deepsea` | -1.20 % | 458 ns | REFUSED R7 | **DELIVERED** chase | 29/30 |
| A14/T131 | `demo/deepsea` | -1.20 % | 483 ns | REFUSED R7 | **DELIVERED** chase | 3/4 |
| A14/T131 | `demo/undraw` | -1.05 % | 470 ns | REFUSED R7 | **DELIVERED** chase | 19/20 |
| A14/T131 | `klipper/all_ff_base` | -0.90 % | 70 ns | REFUSED R8 | **DELIVERED** chase | 98/123 |
| A14/T131 | `main-ext/aa` | -1.05 % | 508 ns | REFUSED R7 | **DELIVERED** chase | 1/2 |
| A14/T131 | `main-ext/dense` | -1.20 % | 545 ns | REFUSED R7 | **DELIVERED** chase | 1/2 |
| A14/T131 | `main-ext/rnd3` | -1.20 % | 433 ns | REFUSED R7 | **DELIVERED** chase | 6/7 |
| A14/T131 | `val-ext/vrnd7` | -1.05 % | 658 ns | REFUSED R7 | **DELIVERED** chase | 18/33 |
| **A14/T131** | **`prod/full`** | **-0.80 %** | **458 ns** | **DELIVERED chase** | **REFUSED R8** | **65/131** |
| A16/T192 | `demo/deepsea` | -1.20 % | 458 ns | REFUSED R7 | **DELIVERED** chase | 29/30 |
| A16/T192 | `demo/deepsea` | -1.20 % | 483 ns | REFUSED R7 | **DELIVERED** chase | 3/4 |
| A16/T192 | `demo/undraw` | -1.05 % | 470 ns | REFUSED R7 | **DELIVERED** chase | 20/21 |
| A16/T192 | `klipper/all_ff_base` | -0.90 % | 70 ns | REFUSED R8 | **DELIVERED** chase | 124/155 |
| A16/T192 | `main-ext/aa` | -1.05 % | 508 ns | REFUSED R7 | **DELIVERED** chase | 1/2 |
| A16/T192 | `main-ext/dense` | -1.20 % | 545 ns | REFUSED R7 | **DELIVERED** chase | 1/2 |
| A16/T192 | `main-ext/rnd3` | -1.20 % | 433 ns | REFUSED R7 | **DELIVERED** chase | 6/7 |
| A16/T192 | `val-ext/vchecker` | -1.20 % | 633 ns | REFUSED R8 | **DELIVERED** chase | 54/55 |
| A16/T192 | `val-ext/vrnd7` | -1.05 % | 658 ns | REFUSED R7 | **DELIVERED** chase | 24/49 |

Two things follow, and they are the mechanism:

1. **`A_MAX`'s gain is an R7 conversion, not a deeper chase.**  7 of the
   8 gains at A14 are `R7 -> DELIVERED`: frames whose `n_weak` sits in
   12..16, which the admission cap refused outright.  R7 falls 62 -> 36
   -> 13 -> 7 -> 1 across the `A_MAX` column; R8 rises 820 -> 850 -> 884
   -> 892 -> 899.  Most of what `A_MAX` un-refuses at R7 simply refuses
   at R8 instead.
2. **`T_MAX`'s only job is to pay for the candidates `A_MAX` admitted.**
   `prod/full` at eps -0.80 %, t0 = 458 ns is the named regression: it
   DELIVERS at the baseline through a 65-trial / 131-comparison chase,
   and at `A_MAX = 14` the wider list pushes its repair past the same 131
   comparisons -> `R8`.  `T_MAX = 192` buys it back.  That single frame is
   the whole difference between MODERATE's `+8 - 1 = +7` and
   AGGRESSIVE's `+9 - 0`.

### 4.2 Where it saturates

* **`A_MAX`**: at 16 for zero-wrong delivery.  18/19 add +2 more frames
  and **one WRONG**.  22/27/40 add nothing over 18 (+12/+13) and keep the
  2 WRONG.  R7 is exhausted by 27 (7 refusals left of 62).
* **`T_MAX`**: the knee is at **160** (+8) with a single extra frame at
  **192** (+9), and then **NOTHING** all the way to 1048 — Table 5.  This
  reproduces §19.2/§20.2's finding ("a bigger `T_MAX` buys **+0
  delivered** at 200 / 262 / 658") and refines it: `T_MAX` alone is worth
  0, and even alongside a bigger `A_MAX` it saturates at 192.
* **Beyond `A_MAX = 16` nothing is buyable at zero wrong.**  The residual
  R8s do not have their repair in the list at any capacity, which is the
  §19.1 ceiling, restated at a different lever.

### 4.3 What it costs

| | analytic fa bound | measured fa (corpus c) | worst-case decode | RAM (stack region) |
|---|---:|---:|---:|---:|
| (11,131) baseline | 0.200 % | 0.068 % | 205.6 ms | 148 B (33 B over peak) |
| (14,131) MODERATE | **0.200 % — unchanged** | 0.096 % | **226.7 ms** | 139 B (24 B) |
| (16,192) AGGRESSIVE | 0.293 % | 0.173 % | **243.4 ms** | 133 B (18 B) |
| (22,262) | 0.399 % | 0.258 % | 306.6 ms | **BUILD REFUSED** (115 B) |
| (40,1048) | 1.586 % | 0.389 % | 612.8 ms | **BUILD REFUSED** |

**The measured false-accept rate is NOT zero at the baseline.**  7 of
10 307 emissions (0.068 %) on the corruption grid are wrong at
`(11,131)`.  The Part-2 criterion as written ("both must have measured
WRONG = 0 on the corruption grid") is therefore **unsatisfiable by any
point, the shipped one included**, and saying so is the finding: a corpus
built to manufacture several wrong payload bits reaches undetectable
CRC-16 codewords regardless of budget.  The substitute gate actually
applied is in §5.

**Blind window.**  Decode time is the blind window: §20.5 measured
reports falling 1 846 -> 1 813 (51.3 % -> 50.4 % of frames sent) when
Lever B lengthened chases, "the price of the extra candidates".  Both
chosen points lengthen the *worst case* by 21 / 38 ms and the *mean*
trials over all 16 800 captures by **+0.88 / +1.39** (2.56 -> 3.44 ->
3.94), i.e. **+0.5 / +0.8 ms of mean decode**, so the same mechanism
applies at a fraction of Lever B's magnitude.  It is nonetheless real and
**unmeasured on silicon here**.

### 4.4 Pareto-optimal points

Objectives: maximise delivered, minimise the analytic fa bound, minimise
worst-case decode, and **WRONG = 0 on the operating grid** as a
constraint rather than an objective.  Of the 25 coarse points plus the 36
refinement points, the non-dominated set is:

| point | delivered | fa bound | worst-case ms | note |
|---|---:|---:|---:|---|
| **(11,131)** | +0 | 0.200 % | 205.6 | the shipped ledger; dominates every other `A_MAX = 11` point (they add fa for +0) |
| **(13,131)** | +3 | 0.200 % | 219.1 | |
| **(14,131)** | **+7** | **0.200 %** | **226.7** | **MODERATE** — the last point that moves neither the fa bound nor `T_MAX` |
| (16,160) | +8 | 0.244 % | 243.4 | |
| **(16,192)** | **+9** | **0.293 %** | **243.4** | **AGGRESSIVE** — the best zero-wrong delivery on the grid |

Everything with `A_MAX >= 18` is excluded by the WRONG constraint;
everything with `T_MAX > 192` is dominated (same delivery, higher fa);
`(22..40, 131)` are dominated on delivery AND carry a WRONG.

---

## 5. The two bench points — the criterion, stated

**MODERATE = `A_MAX = 14`, `T_MAX = 131`.**  Criterion as briefed: *the
smallest `(A_MAX, T_MAX)` capturing at least half of the total host
delivery gain available.*  Total gain anywhere on the grid is **+13**;
half is **+6.5**; `(14,131)` delivers **+7** and no smaller point in
either coordinate reaches +6.5 (`(13,*)` gives +3/+4, `(11,*)` gives +0).
It is smallest in **both** coordinates, and it is the strongest point
that leaves the false-accept bound **exactly unchanged at 0.200 %**,
because it does not touch `T_MAX` at all.

**AGGRESSIVE = `A_MAX = 16`, `T_MAX = 192`.**  Criterion as briefed: *the
best-delivering point whose analytic fa bound is <= 1.0 % AND whose
projected worst-case decode stays <= 250 ms.*  The admissible set is
`{A_MAX in 11..16} x {T_MAX <= 524}` — every `A_MAX >= 18` point breaks
the WRONG constraint and every `A_MAX >= 22` point also breaks the time
cap (306.6 ms at the cheapest).  Best delivery in that set is **+9**,
attained at `T_MAX in {192, 224, 255, 262, 393, 524}`; the tie is broken
to the **Pareto-optimal** member, `T_MAX = 192`, the smallest budget that
still buys the ninth frame (Table 5).  fa bound **0.293 %**, worst-case
**243.4 ms**.

**What was left on the table.**  `+13` at `(27,393)` / `(40,393)` and
`+11` at `(18,192)`: **+4 frames in 16 800 (+0.024 pp)**, unreachable
because those points emit 1-2 WRONG frames at production geometry inside
the auto-trim band, and the `A_MAX >= 22` ones also project 306-613 ms
against the 250 ms cadence and are **refused by the build** on RAM.

**The WRONG = 0 gate actually applied.**  The briefed gate (WRONG = 0 on
the corruption grid) cannot be met by any point including the shipped
one (§4.3), so the gate applied is, explicitly:

1. **WRONG = 0 on the operating grid** — corpus (a), 16 800 captures,
   production geometry, inside the auto-trim band: **0 at both chosen
   points**, and 1-2 at every `A_MAX >= 18` point.
2. **WRONG = 0 on the real-silicon corpus** — corpus (b): **0 at both**.
3. **The corruption-grid rate reported, not gated**: 0.068 % baseline ->
   **0.096 %** MODERATE -> **0.173 %** AGGRESSIVE, i.e. 1.4x and 2.5x the
   shipped rate on a corpus deliberately built to manufacture wrong
   payload bits.  Both stay far inside the project's 0.2 % target
   *rate*, but the direction is unambiguous and it is the reason
   MODERATE exists as an option at all.

---

## 6. The implementation

**One source: two Makefile variables.**

```
A_MAX ?= 11        # defaults ARE the shipped ledger values
T_MAX ?= 131
```

* to `decode.c` as `-DA_MAX_CFG=$(A_MAX) -DT_MAX_CFG=$(T_MAX)` (in
  `PRODFLAGS`), with `#ifndef` fallbacks to 11/131 so a compile without
  the flags is unchanged;
* to `decode_asm.s` as a **generated include** — `sdasstm8` has no `-D`,
  so `gen_chase_cfg.py` writes `chase_cfg.inc` (`A_MAX_CFG`, `A_MAX_M1`,
  `A_MAX_X2`, `T_MAX_CFG`; the two derived forms are written out so
  nothing rests on the assembler's expression parser) and the assembly
  is invoked with `-I$(BUILD)`.  The generator only rewrites the file
  when the values change, so an unchanged point never re-assembles;
* to `embedded_v2.py` as `set_chase_budget(a_max, t_max)`, and to the two
  bit-exactness harnesses as `--amax/--tmax` (defaults unchanged, so
  `make verify`'s invocation is untouched).

The five `A_MAX` sites and one `T_MAX` site in `decode_asm.s`:
`candi`'s `cp a,#A_MAX_CFG` (list-full), `cp a,#A_MAX_CFG` +
`ld a,#A_MAX_M1` (`j = min(ncand, A_MAX-1)`), `cp a,#A_MAX_CFG`
(`ncand++`), the R7 gate's `cpw x,#A_MAX_CFG`, and `chmat`'s
`cp a,#T_MAX_CFG`; plus the two reservations
`_v_cand_t: .ds A_MAX_X2` / `_v_cand_m: .ds A_MAX_CFG`.

**`A_PAIR` is defined as `A_MAX_CFG`** in `decode.c`, which keeps
`#if A_PAIR < A_MAX || MG_PAIR < MG_MAX` false at every point — i.e. the
SS7.10 pair test stays compiled OUT, matching `_chase23`'s `npair = n`
and `decode_asm.s`'s no-test-at-all.  Without that, raising `A_MAX` would
silently compile a pair restriction into the C that neither the reference
nor the assembly has.

### 6.1 BYTE-IDENTITY at the defaults — proved

`rm -rf build && make all`, twice, against the images built from `2d329ee`
before any edit:

| image | md5 | |
|---|---|---|
| `build/rbarf_prod.ihx` | `b8f0ae06e740e0f811ff3ebcb0a201ab` | **byte-identical to HEAD** (`cmp` clean) |
| `build/rbarf_prod_verbose.ihx` | `5524ce94f4ae3cb404503beccb0b9373` | **byte-identical** — the Lever B verbose image |
| `build/capture.ihx` | `84955f771ef8ad41a36fc16187afca38` | **byte-identical, untouched** |

Two consecutive clean rebuilds produce identical md5s.  `make verify`:
**PASS, all 8 stages**.

### 6.2 The three bench images

`make amax-bench` builds all three (each with its **own object
directory**, so a parameter change can never link a stale `.rel`) and
md5-checks them:

| image | A_MAX | T_MAX | md5 | flash free | DATA | stack region |
|---|---:|---:|---|---:|---:|---:|
| `build/rbarf_prod_verbose_A11_T131.ihx` | 11 | 131 | `5524ce94f4ae3cb404503beccb0b9373` | 46 B | 632 B | 148 B |
| `build/rbarf_prod_verbose_A14_T131.ihx` | 14 | 131 | `952c7446d8e26426c8426792fd56361f` | 46 B | 641 B | 139 B |
| `build/rbarf_prod_verbose_A16_T192.ihx` | 16 | 192 | `d8db7f4a27d521026c5b41679b2f2b8e` | 46 B | 647 B | 133 B |

**The baseline image's md5 equals the Lever B verbose ledger image
`5524ce94…` exactly** — `cmp` against `build/rbarf_prod_verbose.ihx` is
clean.  That is the byte-identity proof for the whole parameterisation.

### 6.3 FLASH: zero

`CODE` **7 556 B** and `CONST` **299 B** in all three images, and
`guard_prod.py` reports **flash free 46 B** in all three.  The immediates
are the same width at 11/14/16 and 131/192, and the arrays are RAM.  **The
42 B of headroom was not touched.**

### 6.4 RAM: this is the binding constraint

The candidate arrays are **REL DATA** (`_v_cand_t` at `0x031F`), not zero
page — the zero page is full at `DZP0` = 242 B with `--data-loc 0xF3`
immediately above it.  So every extra `A_MAX` entry costs 3 B of DATA and
takes 3 B out of the 148 B stack region.

| | statics | stack region | over the 115 B peak |
|---|---:|---:|---:|
| A_MAX 11 | 876 / 1024 | **148 B** | 33 B |
| A_MAX 14 | 885 / 1024 | **139 B** | **24 B** |
| A_MAX 16 | 891 / 1024 | **133 B** | **18 B** |
| A_MAX 22 | 909 / 1024 | 115 B | **0 B — build REFUSED** |

**Stack DEPTH does not move.**  `dev_prod/stackprobe_v23.py` (sentinel
paint + ucsim low-water) at the AGGRESSIVE point over 8 cases including
the worst-case `n_weak` (**134, 113, 90, 80** — all R7 refusals — plus
the heaviest chase, `trials = 21, comps = 192`): `ws_decode_ex` subtree
**12 B**, identical to the baseline run's 12 B and to the
`PROD_CLOSURE.md` §14.2 ledger.  That is structural: the candidate list
is indexed statics, and the deepest chain
(`chasez -> cpair -> trial -> push -> refbld -> rank3 -> putval`) does not
recurse over it.  The 115 B peak is the **animation** engine's
`anim_sequence -> seq_edge -> lerp` chain (98 B) plus the 9 B TIM4 ISR
context — nothing the chase touches.

`guard_prod.py` **check 7** is new and refuses a link whose stack region
falls below `MIN_STACK = 124 B` (the 115 B measured peak + 9 B).  **`make
amax-verbose A_MAX=22` fails the build** with exactly that message.  A
point past `A_MAX = 16` needs a RAM lever first: the honest RAM ceiling
on this layout is **`A_MAX = 19`** (124 B region, exactly `MIN_STACK`, 9 B
over the measured peak), and the u8 `dec_info.trials` caps it at 22 in any
case.  `A_MAX = 19` is excluded anyway — 1 WRONG on the operating grid
**and** a 272.6 ms worst case, past the 250 ms cadence.

### 6.5 The pinned blocks — and the four bytes that DO move

`cap_arm.s` is **untouched** (byte-identical to `main`).  But `s_arm`,
its 1-byte RAM counter, is REL DATA linked *after* the candidate arrays,
so it moves up by `3*(A_MAX-11)` — and its address is an operand inside
the pinned `CAPARM` block.  `dev_amax/armdiff.py` proves that is the
*only* change:

| image | CAPLOOP `0x9FA1..0x9FF0` / `0x9FF1..0x9FFF` | CAPARM differing bytes | 4 BTJT polls |
|---|---|---|---|
| A11_T131 | **byte-identical (HARD PINS)** | **0** | byte-identical |
| A14_T131 | **byte-identical** | **4**: `0x9F66 0x9F74 0x9F92 0x9F9A`, each **+9** | byte-identical |
| A16_T192 | **byte-identical** | **4**: same four, each **+15** | byte-identical |

Those four bytes are the low halves of the two `mov s_arm,#n` and two
`dec s_arm` operands.  `cap_arm.s`'s own header already states this
discipline for the §16.3 diagnostic arm ("differs from this arm in
exactly the 4 `s_arm` operand bytes, all four polls byte-identical"), and
`absmd5.py`'s docstring already treats the CAPARM rows as informational
for exactly this reason.  Every calibrated quantity is untouched:
`CAPARM_ORG = 0x9F63`, `_cap_loop = 0x9FAF`, the 2/2/3/4-cy poll comb,
the `_cap_loop+1` branch targets, and both instruction-boundary
assertions — `guard_prod.py` checks 1-6 pass unchanged on all three
images.

### 6.6 BIT-EXACTNESS at every point built

Python <-> C <-> asm, re-proved per point.

| proof | (11,131) | (14,131) | (16,192) |
|---|---|---|---|
| host parity `decode.c` <-> `embedded_v2.py`, all corpora + both fuzz sets (`parity_v23.py`) | **549/549** | **549/549** | **549/549** |
| ucsim, the SHIPPED `decode_asm.s`, ND = 48 | **24/24** | **24/24** | **24/24** |
| ucsim, ND = 16 | **24/24** | **24/24** | **24/24** |
| ucsim, ND = 48, capture byte 0 bits 7..6 forced to `0xC0` | 24/24 (§20.1) | — | **24/24** |

`comps` is compared as a `dec_info` field in both harnesses, so
`T_MAX = 192` is checked on-target, not inferred.  The `(11,131)` ND=48
and ND=16 runs reproduce `PROD_CLOSURE.md` §19.3/§20.1 **exactly**: min
4 108 487 / p50 4 563 628 / max 4 804 401 and min 1 907 809 / p50
2 098 974 / max 2 286 393 — the control that says the parameterisation
did not move the default path.

**ucsim decode ticks** (ND = 48, 24 cases):

| point | min | p50 | max | heaviest chase |
|---|---:|---:|---:|---|
| (11,131) | 4 108 487 | 4 563 628 | **4 804 401** | `comps=131 trials=50` -> 4 620 713 |
| (14,131) | 4 108 559 | 4 591 095 | **5 009 623** (+4.3 %) | `comps=131 trials=50` -> 4 620 785 |
| (16,192) | 4 108 607 | 4 656 313 | **5 228 707** (+8.8 %) | `comps=192 trials=21` -> 4 332 929 |

Against the established silicon/ucsim ratio (~0.70x), 5 228 707 ticks
projects to **~229 ms**, consistent with the 243.4 ms analytic worst
case and inside the 250 ms cadence — **but the true worst case (136
trials) is not in the 24-case set and remains unmeasured**, on ucsim as
well as on silicon.

### 6.7 Guards, negative-tested

| check | test | result |
|---|---|---|
| `guard_prod.py` check 7, stale include | A16 map against the A11 `.inc` | **FAIL**, rc 1: *"`_v_cand_t.._v_cand_m` spans 32 B but A_MAX 11 needs 22 … assembled against a DIFFERENT chase_cfg.inc"* |
| `guard_prod.py` check 7, RAM floor | `make amax-verbose A_MAX=22` | **FAIL**, rc 1: *"STACK REGION 115 B < MIN_STACK 124 B … needs a RAM lever, not a smaller floor"* |
| `gen_chase_cfg.py`, u8 `trials` | `A_MAX = 23` | **refused**: 276 worst-case trials > 255 |
| `gen_chase_cfg.py`, u8 `comps` | `T_MAX = 256` | **refused** |
| `decode.c` `#error` pair | the same two limits at compile time | present, unreachable via the Makefile because the generator refuses first |
| `guard_prod.py` checks 1-6 | all three images | pass, unchanged |
| `absmd5.py` | all three images | both CAPLOOP HARD PINS OK |

---

## 7. What this work did NOT establish

* **Nothing was flashed.  No bench number is claimed.**  The two images
  exist, are guard-green and are reproducible; `bench/suite_singleshot.py`
  has not been run against them.  The suite is the acceptance metric and
  is **byte-identical to HEAD** — as are `caploop.s`, `cap_arm.s`,
  `cap_code.s`, `capture.ihx`, `bench/demo.py` and every capture/arm path
  in `rbarf_prod.c`.
* **The corruption grid is harsher than the physics.**  Flipping stored
  sample bits is not a failure mode this receiver has: the capture loop
  samples a real line.  It is a deliberate stress that manufactures
  multi-bit payload errors, which is precisely the regime a wider chase
  mines for undetectable codewords.  Read its rates as an exposure
  ordering, not as a predicted field rate.  The project's own
  `wrong_emission_final.py` grid (eps x arm phase, no injected damage)
  was **not** re-run across this grid — that is the obvious next
  measurement and it is not here.
* **The worst-case decode is unmeasured** at 136 trials, on silicon and
  in ucsim alike; §16.7's observation stands that a safe `t0` makes deep
  chases rarer, so a bench gate may again fail to produce one.
* **The blind-window cost is projected, not measured.**  §20.5 measured
  it for Lever B (reports 51.3 % -> 50.4 %); the same mechanism applies
  here at roughly half the magnitude, and nothing here measures it.
* **One eps band, one arm range, host models only.**  Corpus (a) is the
  calibrated sampler model over the auto-trim band, not silicon.
* **`A_MAX = 19` was not built.**  Table 4 says it delivers +11 with 1
  WRONG, so it is excluded on correctness, and its 272.6 ms worst case
  breaks the time cap as well; the RAM (124 B region, exactly the guard's
  floor) would just have allowed it.
* **`data/captures_v23_val.json` was not swept** (only `captures_v23.json`
  is in corpus (b)); `data/captures_val.json` was never opened.
* Two harnesses gained a **robustness** fix while being parameterised:
  `ucsim_v23.py` now retries the ucsim connect for 10 s instead of a
  fixed 0.5 s sleep, and retries a case up to 3 times on a dropped `-Z`
  socket, printing every retry.  Both were needed — a refused connect had
  produced a run of 8 bogus "target reported nothing" mismatches, which
  is exactly the kind of artefact that must not be recordable.  Defaults
  and results are otherwise unchanged.

---

## 8. Artifacts

`recon/approaches/dev_amax/`:

| file | what |
|---|---|
| `amaxlib.py` | the grid, the corpora's parameters, the reference driver, `fa_bound`/`max_trials`/`proj_ms` with their sources |
| `sweep_amax_tmax.py` | the three corpora + `--validate` (the grid-independence shortcut proof) |
| `sweep_suite.json`, `sweep_real.json`, `sweep_wrong.json` (+ 5 per-stratum files) | the 5 x 5 grid on all three corpora |
| `sweep_suite_fine.json`, `sweep_suite_tknee.json`, `sweep_wrong_points.json` | the refinement grids (Tables 4-6) |
| `per_payload.py`, `per_payload.log` | per-payload / per-capture attribution — §4.1's table, including the one regression |
| `tables.py`, `tables.md` | every table in §3 rendered from the JSONs; no number in §3 is typed by hand |
| `armdiff.py` | the pinned-block proof: CAPLOOP identical, CAPARM differing in exactly the 4 `s_arm` operand bytes |
| `ucsim_*.log` | the 7 on-target parity runs |
| `stack_base_nweak.log`, `stack_A16_T192_nweak.log` | the stack watermark at worst-case `n_weak` |
| `run_ucsim_points.sh` | the ucsim sweep driver |

Firmware/build: `gen_chase_cfg.py` (new), `Makefile` (`A_MAX`/`T_MAX`,
`amax-verbose`, `amax-bench`), `decode.c`, `decode_asm.s`,
`guard_prod.py` (check 7), `recon/approaches/embedded_v2.py`
(`set_chase_budget`), `dev_prod/parity_v23.py`, `dev_prod/ucsim_v23.py`,
`dev_prod/stackprobe_v23.py` (`--amax/--tmax`).

**Bench discipline.**  Every `ucsim` child ran under `timeout -k` with a
`pkill -x` sweep; **0 strays at exit** on every run.  No image was
flashed.  `bench/suite_singleshot.py` and `bench/demo.py` untouched.
`data/captures_val.json` **never opened**.  All work is on branch
`amax-tmax-sweep`; `main` was not touched and nothing was merged.

---

## 9. SILICON — THE OWNER'S ACCEPTANCE METRIC (2026-09-08)

§7 opened with "nothing was flashed and no bench number is claimed".
This section closes that. All three images went on the die, in the order
**baseline → MODERATE → AGGRESSIVE → baseline** so that thermal drift
could not be mistaken for an image effect, and the acceptance metric is
the owner's: **first-try latch of a single frame**,
`bench/suite_singleshot.py --passes 3` (70 unique payloads × 3 shuffled
passes, seed 20260908, 500 ms gap, one transmission per frame, bytes
checked against the `V:` line). The suite is **byte-identical for every
run and to the version that produced the `main` / Lever B numbers**
(`b7333ff6247f3cd8c4fd80fa721fe17b`), and was not edited.

### 9.1 Pre-flight — the images were re-proved, not trusted

| check | result |
|---|---|
| `make verify` | **PASS, all 8 stages**, ledger `b8f0ae06…` / `5524ce94…` / `84955f77…` |
| `guard_prod.py` on all three bench maps | **green**: 46 B flash free in all three; stack region 148 / 139 / 133 B |
| `absmd5.py`, three bench images | both **CAPLOOP HARD PINS byte-identical** (`273e269f…`, `9ddd0227…`); `CAPARM` differs in **exactly 4 bytes** (`0x9F66`, `0x9F74`, `0x9F92`, `0x9F9A`) — §6's `s_arm` operands, reproduced |
| host parity `decode.c` ↔ `embedded_v2.py`, **re-run at each point** | **549/549** at (11,131), (14,131) and (16,192) |
| ucsim on the SHIPPED `decode_asm.s`, ND=48, **re-run at each new point** | **24/24** at (14,131), max **5 009 623** ticks; **24/24** at (16,192), max **5 228 707** ticks — §6's figures to the tick |
| md5 of each flashed image | `5524ce94f4ae3cb404503beccb0b9373` / `952c7446d8e26426c8426792fd56361f` / `d8db7f4a27d521026c5b41679b2f2b8e` |
| `data/captures_val.json` | **never opened** — atime still `2026-09-05 06:34:02` |

Every flash succeeded on its **first** power cycle; the 5 s SWIM window
was observed live at **5.05 s** on the final boot.

### 9.2 THE RESULT — four runs, and the baseline's own spread

| run | order | first-try | Δ vs baseline mean | eps range | mean eps | causes | SILENT | **WRONG** | resets |
|---|---:|---:|---:|---|---:|---|---:|---:|---:|
| **baseline (11,131)** `base_r1` | 1 | **204/210 (97.14 %)** | +4 | −0.90…−0.78 % | −0.849 % | `R8`×4 | 2 | **0** | **0** |
| **MODERATE (14,131)** | 2 | **202/210 (96.19 %)** | **+2** | −0.95…−0.83 % | −0.897 % | `R8`×7 | 1 | **0** | **0** |
| **AGGRESSIVE (16,192)** | 3 | **199/210 (94.76 %)** | **−1** | −1.40…−0.82 % | −0.925 % | `R8`×10, `R3`×1 | 0 | **0** | **0** |
| **baseline (11,131)** `base_r2` | 4 | **196/210 (93.33 %)** | −4 | −1.29…−0.79 % | −0.886 % | `R8`×7, `R7`×1, `R3`×3 | 3 | **0** | **0** |

*(for reference, the same suite on the previous images: `main` 193/210,
Lever B 198/210.)*

**The two baseline runs differ by 8 frames — 204 vs 196, 3.81 pp — and
both candidate images land strictly inside that interval.** The
baseline's own thermal/temporal spread is therefore larger than the
entire effect being measured, and it is larger in the direction that
matters: the *second* baseline is the **worst** of the four runs.

The four totals in run order are 204, 202, 199, 196 — a decline of
**−2.7 frames per run** with **R² = 0.992** against run index, residuals
under one frame. Run order explains 99.2 % of the between-run variance;
image identity explains what is left, which is nothing resolvable. The
second baseline is what makes this a measurement rather than a guess: had
the images been the cause, `base_r2` would have returned to ~204.

Per family (first-try / attempts):

| family | n | baseline r1 | MODERATE | AGGRESSIVE | baseline r2 |
|---|---:|---:|---:|---:|---:|
| `main-ext` | 54 | 54/54 | 53/54 | 50/54 | 54/54 |
| `val-ext` | 36 | 36/36 | 36/36 | 35/36 | 34/36 |
| `prod` | 27 | 26/27 | 25/27 | **27/27** | 26/27 |
| `klipper` | 45 | 44/45 | 40/45 | 43/45 | 42/45 |
| `demo` | 48 | 44/48 | **48/48** | 44/48 | 40/48 |

The per-family columns do not agree with each other between the two
baseline runs either (`demo` 44 → 40, `val-ext` 36 → 34), which is the
same message at finer grain: at n = 48 per family per run this suite
cannot separate the images.

**Strict per-pattern 3-of-3 failures** (a pattern that missed in every
pass — the harshest reading of the metric):

| image | 3/3-fail patterns |
|---|---|
| baseline r1 | **none** |
| MODERATE (14,131) | **`klipper/rnd_colors2`** |
| AGGRESSIVE (16,192) | **none** |
| baseline r2 | **none** |

`klipper/rnd_colors2` is the only pattern to fail 3/3 anywhere in this
phase, and it failed on MODERATE — the point the host sweep called the
safer one. It refuses (`R8`) in at least one pass of all four runs.

**Correctness: zero wrong emissions everywhere.** Across the four
acceptance runs the images accepted **801 frames** (204 + 202 + 199 +
196) and **every one was byte-exact against the `V:` line**: 0 WRONG,
0 protocol errors, 0 misattributions, **0 MCU resets** in 840 frames on
the wire. Auto-trim stayed in the `[−1.6, −0.4] %` band on every one of
the 834 reports.

### 9.3 AGGRESSIVE — the 30-frame gate, and the wrong-emission soak

Both on `d8db7f4a…`, freshly flashed, guard green immediately before.

**Gate** — `bench/drive_prod.py --reps 3`, the §16.5/§20.4 invocation, 10
production payloads × 3, each on the wire exactly once:

| | delivered | direct `O` | chase `C` | refused | no-report | **CATASTROPHIC** | resets |
|---|---:|---:|---:|---:|---:|---:|---:|
| **AGGRESSIVE (16,192)** | **29/30 (96.7 %)** | 26 | **3** | 1 (`R8`, `rnd`) | 0 | **0** | **0** |
| Lever B §20.4 cold | 29/30 | 25 | 4 | 1 (`R8`, `full`) | 0 | 0 | 0 |

**The ≥ 28/30 bar is MET.** eps −0.95…−0.88 %, 30/30 in band. Decode
window min 162.9 / mean 169.7 / max 184.1 ms; latency peak 196.9 ms.

**Wrong-emission soak** — 320 frames of the corruption-prone subset: the
20 payloads that are either pale / 1-dense (`ones`, `impulse_lo`,
`vwalkz`, `runs`, `dense`, `full`, `all_ff_base`, `vprime`, `vchecker`)
or random (`rnd1-3`, `vrnd4-8`, `rnd`, `rnd_colors1/2`) — i.e. the R7/R8
carriers a bigger `A_MAX` re-admits, 16 shuffled passes at the suite's
500 ms gap.

| | frames | reports | delivered correct | refused | **WRONG** | resets |
|---|---:|---:|---:|---:|---:|---:|
| **AGGRESSIVE soak** | **320** | **320 (100 %)** | **315 (98.4 %)** | 5 (all `R8`) | **0** | **0** |

**Zero wrong emissions.** The hard-stop condition did not fire. 35 of
the 315 deliveries were chase repairs. Pooling every frame this phase
put on the AGGRESSIVE image — 199 acceptance + 29 gate + 195 timed +
315 soak + 10 closing liveness = **748 accepted emissions, 0 WRONG**;
MODERATE contributed **202 accepted emissions, 0 WRONG**.

Total frames on the wire this phase: **1 620** (840 acceptance + 30 gate
+ 210 timed AGGRESSIVE + 320 soak + 210 timed baseline + 10 liveness),
**0 MCU resets**, 0 protocol errors.  *(The commit message of `ea0d605`
says "1 490 frames"; that is an arithmetic slip in the message — the
correct total is 1 620, itemised above.)*

### 9.4 Decode time on silicon — the median does not move, the tail does

Measured with a **copy** of the suite under
`recon/approaches/dev_suite/suite_timed.py` (the acceptance suite records
no timing and was not edited); the copy is proved to build a
**byte-identical 70-payload set** and uses `bench/drive_prod.py`'s
decomposition verbatim, `decode_ms = (t_D-line-complete − t_write-start)
− frame tx (0.600 ms) − capture window (0.728 ms) − UART transit`, so the
numbers are comparable with §16.7 and §20.4.

Same 70 payloads × 3 passes on each image, same session, ~13 minutes
apart:

| | reports | min | p50 | p90 | p99 | **max** | direct max | **deepest chase repair** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **baseline (11,131)** | 206 | 150.2 | 167.9 | 170.0 | 179.1 | **184.6** | 172.8 | **179.1 ms** |
| **AGGRESSIVE (16,192)** | 208 | 152.5 | 168.5 | 171.1 | 205.3 | **211.1** | 173.0 | **205.3 ms** |
| AGGRESSIVE soak (320 fr) | 320 | 150.1 | 164.0 | 168.2 | 186.0 | 194.9 | 170.4 | 194.9 ms |

* **The direct path is untouched**: 172.8 → 173.0 ms, and the median
  moves **+0.6 ms**. Raising the budget costs nothing on a frame that
  does not chase, which is 86 % of them.
* **The tail grows by +26.5 ms**: the longest decode goes **184.6 →
  211.1 ms** (a chase that exhausted the 192-comparison budget and then
  refused, `demo/rain`), and the longest *successful* repair **179.1 →
  205.3 ms** (`demo/deepsea`). That is +61 comparisons at ≈ 0.43 ms
  each — the `T_MAX` 131 → 192 change, priced on silicon.
* Against the project's **170 ms** figure (§16.7 mean 169.7, §20.4 max
  182.9 ms): the mean is unchanged at **169.7 ms** on the gate, and the
  **maximum observed decode rises 182.9 → 211.1 ms**.
* §4.3 predicted **+0.8 ms of mean decode** at AGGRESSIVE from the
  +1.39 mean trials. Measured: **+0.6 ms on the median** over the same
  70 payloads. The host model of the *mean* cost is confirmed on
  silicon; it is the *tail* the host model priced at +38 ms and silicon
  prices at **+26.5 ms** (because the 136-trial case never fires).
* The analytic worst case (136 trials, 243.4 ms) **still did not fire**.
  The deepest chase this phase produced is the 192-comparison refusal at
  211.1 ms, so 211.1 ms is a measured floor on the tail, not its ceiling.

**Blind window and cadence.** The blind window is the decode plus the
report emission. On the VERBOSE bench image the observed
frame-start → `D:`-complete latency peaked at **224.9 ms** (baseline
198.4 ms), and the 98-char `V:` line adds ≈ 102 ms more before the arm
re-opens. On the shipping **TERSE** image the report is 11 characters
≈ 11.5 ms, so the worst-case blind window is
**≈ 223 ms** measured (211.1 + 11.5), against **≈ 196 ms** for the
baseline, and **≈ 255 ms** if the unfired 243.4 ms analytic worst case
is allowed for.

> **Recommendation.** The 250 ms cadence used by every soak in this
> project leaves the baseline ~54 ms of armed time per period at its
> worst case (21 %) but leaves AGGRESSIVE only **~27 ms (11 %)**, and
> **none at all** if the analytic worst case is ever reached. If
> `A_MAX = 16, T_MAX = 192` is ever shipped, **raise the minimum
> inter-frame gap to 300 ms** (≥ 275 ms measured + margin for the
> unmeasured 136-trial case); at 250 ms expect roughly double the
> no-report rate on chase-heavy payloads. The baseline at 250 ms is
> unchanged and the suite's own **500 ms gap is comfortable for both**.

### 9.5 Verdict — the bench does not resolve a gain, and §8's own advice stands

**Raising `A_MAX`/`T_MAX` did not improve first-try latch on silicon
beyond the baseline spread, in either direction.** The two baseline runs
bracket 8 frames (204/210 and 196/210); MODERATE scored 202 and
AGGRESSIVE 199, both inside that bracket and both within ±4 of the
baseline mean of 200. The four runs fall almost exactly on a line in run
order (−2.7 frames/run, R² = 0.992) whose last point is a *baseline*, so
the trend is thermal/temporal and the image effect is below this
metric's resolution — exactly the outcome §8 predicted for a host gain of
+7 and +9 frames in 16 800 (+0.042 / +0.054 pp).

What the bench *does* establish, positively:

* **Correctness holds on silicon at both new points.** 0 WRONG in 801
  accepted frames over the four acceptance runs, 0 in the 30-frame gate,
  and **0 in a 320-frame soak deliberately loaded with the pale-1-dense
  and random carriers a bigger `A_MAX` re-admits**. 0 MCU resets, 0
  protocol errors, auto-trim in band throughout.
* **AGGRESSIVE passes the production gate** (29/30, ≥ 28/30 bar) with the
  same shape as Lever B's own cold gate.
* **The cost is entirely in the tail**: median decode +0.6 ms, worst-case
  decode **+26.5 ms**, and a blind window that no longer fits a 250 ms
  cadence with margin.

**The false-accept bound bought at that price** is the host figure, and
it is unchanged by this phase because nothing here measures it on
silicon: **0.1997 % at MODERATE** (`T_MAX` untouched, so the bound is
identical to the shipped 0.200 %) and **0.2925 % at AGGRESSIVE**, against
the project's 0.2 % target — i.e. AGGRESSIVE is the only one of the three
that **exceeds the stated target**, on a measured corruption-grid
exposure of 2.5 × the shipped image's (§4.3). MODERATE buys +2 frames of
unresolvable delivery for no change in the bound; AGGRESSIVE buys −1
frame of unresolvable delivery for a bound above target and 26.5 ms of
worst-case decode.

**Recommendation, unchanged from §8 and now with silicon behind it: keep
`A_MAX = 11, T_MAX = 131` and bank the parameterisation, the sweep, the
guard's check 7 and these four runs as the measurement that says the
lever is not worth pulling.** If it is pulled anyway, MODERATE is the
only defensible point — it leaves the bound alone, costs no decode time
(`T_MAX` untouched), and the 9 B of stack it spends are the cheapest of
the two.

### 9.6 What §9 did NOT establish

1. **One unit, one session, one afternoon.** Four runs of 210 frames,
   one STM8S001J3, eps −1.40…−0.78 %. The 8-frame baseline spread is
   this session's noise floor, not a characterised distribution — two
   runs give a range, not a variance.
2. **The gate and the soak were run on AGGRESSIVE only**, as briefed.
   MODERATE has no 30-frame gate, no soak and no silicon timing on it;
   its only silicon evidence is its 202/210 acceptance run.
3. **The 136-trial worst case is still unproduced**, in ucsim and on
   silicon. 211.1 ms is the deepest decode ever measured on this
   project; 243.4 ms remains analytic, and the cadence recommendation
   above carries margin for it rather than measuring it.
4. **The soak is 320 frames at a 500 ms gap, not a hard-cadence
   15-minute soak.** It is a wrong-emission exposure test on the
   corruption-prone payloads, not a duty-cycle measurement; the
   §20.5-style report-rate cost of the wider list at 250 ms is
   **still projected, not measured**.
5. **No Klipper end-to-end run** on either new image (§20.8's axis).
6. **The false-accept bound is host arithmetic.** Nothing on silicon in
   this phase measures a false-accept rate; 738 emissions with 0 WRONG
   bounds it at ≤ 0.41 % (95 %) on AGGRESSIVE, which is far too loose to
   discriminate 0.20 % from 0.29 %.
7. **`data/captures_val.json` was never opened** and no host sweep,
   tuning or decode was run against it.

### 9.7 Artifacts

| path | what |
|---|---|
| `dev_suite/singleshot_base_r1.json`, `singleshot_base_r2.json` | the two baseline acceptance runs — the thermal noise floor |
| `dev_suite/singleshot_A14_T131_r1.json` | MODERATE acceptance run |
| `dev_suite/singleshot_A16_T192_r1.json` | AGGRESSIVE acceptance run |
| `dev_suite/gate_A16_T192.json` | the 30-frame `drive_prod.py` gate |
| `dev_suite/timed_A16_T192_soak.json` | the 320-frame wrong-emission soak |
| `dev_suite/timed_A11_T131_timed.json`, `timed_A16_T192_timed.json` | the same-session decode-time A/B |
| `dev_suite/suite_timed.py` | the timing/soak COPY of the acceptance suite (the suite itself is untouched) |

**Bench discipline.** `guard_prod.py` green before every flash, never
bypassed. `bench/suite_singleshot.py` byte-identical for all four
acceptance runs (`b7333ff6…`) and unmodified; `caploop.s`, `cap_arm.s`,
`cap_code.s`, `build/capture.ihx` (`84955f77…`) and `bench/demo.py`
byte-identical to `main`. Every `ucsim` child under `timeout -k` with a
`pkill` sweep; **0 strays at exit**, `/dev/ttyACM0` free. Every flash
first-cycle.  The closing act was a 10-frame `drive_prod.py --reps 1`
liveness check on the flashed image: **10/10 delivered correct (8 `O` +
2 `C`), 0 CATASTROPHIC, 0 resets**, eps −1.11…−1.07 %, decode min 164.8
/ mean 170.7 / max 184.7 ms — the target is up, decoding, and powered.
**Bench state on exit: the AGGRESSIVE image
`rbarf_prod_verbose_A16_T192.ihx` (`d8db7f4a27d521026c5b41679b2f2b8e`) is
flashed and the target is POWERED ON**, banner `RBARF-P 1` at **5.05 s**.
