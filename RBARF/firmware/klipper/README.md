# RBARF Klipper macros (wire protocol v2.3)

> ## STATUS 2026-09-07 (CAPTURE FRONT-END FIX): **GO** — delivery bar met, 0 wrong
>
> The v2.3 decoder was already correct on silicon (§15); what was losing
> frames was the **capture front end**, and it is fixed
> (`../recon/PROD_CLOSURE.md` §16, `../recon/ARM_INVESTIGATION.md` §9).
> Three edits worth **one byte of flash** — the armed capture now enters
> the pinned sampling loop one instruction later (word-aligned, one cycle
> earlier, which puts the trigger phase back under a hard 681 ns
> geometric cliff), the poll comb is retimed, the arm refuses to trigger
> mid-burst, and the LED render dropped 100 Hz → 25 Hz because it is a
> blind window for the receiver.
>
> | | delivered | catastrophic |
> |---|---:|---:|
> | before (auto-trim parked on the cliff, code 7, v2.2) | 5/51 (9.8 %) | **2** |
> | v2.2 final gate (auto-trim retargeted, code 0) | 39/51 (76.5 %) | 0 |
> | v2.3 silicon gate (old arm, warm) | 44/51 (86.3 %) | 0 |
> | **v2.3 + front-end fix (this run)** | **46/51 (90.2 %)** | **0** |
>
> All 17 cases still render **byte-exact** against `verify_macro.py`
> before anything reaches the wire, with v2.3 framing `FF AA 65` …
> `9A 00 FF` and CRC-16 × 3.  13 of 17 cases go 3/3 and **every case
> delivers at least 1/3**; the 5 refusals are `R8` × 3 and `R6` × 2 —
> decoder confidence on the all-`0xFF` and pseudo-random payloads, with
> **no arm-side cause left**.  `preset_rain_rev`, §15's worst case at
> 1/3, is now **3/3**.
>
> **The 30-frame device gate now passes in both conditions: 28/30 cold
> and 29/30 warm, against 26/30 and 22/30 before** — and `R1`+`R3`, the
> arm-side refusals that were 75 % of all losses, are down to **3.1 %**
> (3 of 97, all `R3`).  Across this phase's production runs: **3 712
> frames on the wire, 1 855 accepted emissions, 0 wrong, 0 MCU
> resets.**
>
> **Unchanged for macro users:** the wire format, `rbarf.cfg`, the
> minimum inter-frame gap (that floor is set by the decode blind window,
> ≈ 178 ms, not by the render) and every host-side check. The render
> change is invisible on the wire; it only means the LED strip refreshes
> at 25 Hz instead of 100 Hz, which is still far above the animation
> rates the protocol can request (`f[1] × 50 ms`, minimum 50 ms cycle,
> production frames 1000-2500 ms).
>
> **Where the residual loss is now.**  Pooled over every production
> frame this phase put on the wire (30 cold + 30 warm + 3 601 soak + 51
> Klipper): **97 refusals — `R8` chase 50 (51.5 %), `R6` nocand 44
> (45.4 %), `R3` infeasible 3 (3.1 %), `R1` lock 0.**  The capture front
> end, which was 75 % of the loss in §15, is gone; what is left is
> decoder CONFIDENCE (`R6`/`R8`) and it is concentrated in the all-`0xFF`
> payload.  Because delivery is **single transmission**, a missed frame
> just leaves the previous animation running — it is a lost update, never
> wrong output.
>
> For reference, the host reference decoder scores **97.78 % (88/90)** on
> the fresh real v2.3 corpora acquired with the `9A 00 FF` trailer; the
> device now tracks it closely (95.2 % of captured frames over a
> 3 601-frame soak).
>
> The two v2.2 fixes that closed the catastrophic emissions are unchanged
> and still carry it: the **auto-trim retarget** (deadband centred on
> eps ≈ −1 %, so the unit parks at trim code 0 in the middle of the
> delivery plateau instead of code 7 on the cliff) and the **bounded
> chase**.  v2.3 adds CRC-16/CCITT-FALSE written 3× with per-byte
> majority recovery and the restored `9A 00 FF` trailer zeros probe.
>
> The pre-fix runs are preserved:
> `bench_klipper_macro_results.prefix_baseline.json` (the only two
> recorded catastrophic rows) and
> `../recon/approaches/dev_prod/bench_v23_klipper.json` (§15, old arm).
> This run is `../recon/approaches/dev_fe/klipper_fe.json`.
>
> **Bench-image note:** the gate is run against
> `build/rbarf_prod_verbose.ihx`, whose `V:` line is what makes a wrong
> emission observable at all.  From v2.3 that image reports eps as
> `x<4 hex>` (raw big-endian int16 centi-percent) instead of decimal —
> the 92 B decimal printer does not fit alongside the `V:` line in the
> 8 KB image.  The **shipping terse image still prints decimal**;
> `bench/epsfmt.py` parses both.

`rbarf.cfg` drives the RBARF board from Klipper over a WS2812 output pin.
One command, `RBARF_SET`, takes friendly named parameters, builds the
**entire v2.3 wire frame in Jinja** — header, 48 data bytes, the
three-times-repeated CRC-16 check block and trailer — and clocks it out
as 20 `SET_LED` calls.

```
HEADER(3)  DATA(48)                    CHECK(6)              TRAILER(3)
FF AA 65   8 base colours + 24 flags   C16_HI C16_LO x3      9A 00 FF
           --------------- 60 protocol bytes = 20 LEDs -------------
```

The frame must tile the 3-byte-LED chain exactly, which is why the
marker trim (8 marker bytes → 6) and the check-block growth (4 → 6)
are **one change**: together they hold the frame at 60 bytes. The two
recovered marker bytes buy a 16-bit check, which is 256× stronger per
chase trial than v2.2's CRC-8 — that is what lets the decoder emit on
an imperfect reconstruction instead of refusing. The receiver recovers
its reference by independent **per-byte** majority
(`reference_HI = majority(H1,H2,H3)`, `reference_LO` likewise), so two
copies damaged in different byte positions still yield the exact 16-bit
reference. See `../../docs/PROTOCOL.md`.

Delivery is **single transmission**: one `RBARF_SET` puts one frame on
the wire, once. No repeats, no retries, no acks. A frame the device
misses simply leaves the previous animation running until you send the
next one.

That has one practical consequence: **do not fire `RBARF_SET` back to
back.** While the device decodes and reports a frame it has no capture
armed, and anything arriving in that blind window is lost with nothing to
recover it.

### Minimum inter-frame gap — measured

Swept on hardware with `../bench/rate_probe.py` against the shipping
firmware (`rbarf_prod.ihx`), 12 frames per period, free-running:

| gap between frames | rate | frames the device saw | decoded |
|---:|---:|---:|---:|
| 400 ms | 2.5 Hz | 12/12 | 12 |
| **250 ms** | 4.0 Hz | 12/12 | 10 |
| **220 ms** | 4.5 Hz | **12/12** | **12** |
| 200 ms | 5.0 Hz | 12/12 | 11 |
| **180 ms** | 5.6 Hz | 12/12 | 11 |
| 160 ms | 6.2 Hz | **7/12** | 4 |
| 140 ms | 7.1 Hz | 6/12 | 6 |
| 100 ms | 10 Hz | 6/12 | 6 |

* **Hard floor 180 ms.** The decode blind window is **≈178 ms** (decode
  ~168 ms plus the UART report). Below 180 ms the device is blind for a
  whole frame period and the armed fraction falls straight to ~50 % — half
  your commands vanish with no report at all.
* **Recommended minimum: 250 ms** between `RBARF_SET` calls. That is the
  180 ms floor plus margin for jitter in Klipper's command scheduling; do
  not design for the floor itself.
* Peak measured throughput is 5.1 delivered frames/s, at 180 ms.
* If you are testing against the VERBOSE bench image, the floor is
  **300 ms** — its `V:` diagnostic line adds ~103 ms to every blind window.

Do not put `RBARF_SET` in a tight loop or in a per-layer macro that can be
re-entered quickly. Raw sweep data: `../recon/approaches/dev_prod/`
`rate_probe_terse.json` (shipping) and `rate_probe_results.json` (verbose).

---

## Install

1. Copy `rbarf.cfg` next to `printer.cfg`.
2. Add to `printer.cfg`:

   ```ini
   [include rbarf.cfg]
   ```

3. Open `rbarf.cfg`, uncomment the `[neopixel rbarf]` block and set your
   pin.
4. `RESTART`.

If `printer.cfg` already has a `SET_LED_INTEGER` macro (the one in the
repo's top-level `KLIPPER.md`), **delete one of the two copies** —
Klipper refuses to start with a duplicate macro name.

### `[neopixel]` configuration

```ini
[neopixel rbarf]
pin: PA8              # <- your pin
chain_count: 20
color_order: GRB
initial_RED: 0.0
initial_GREEN: 0.0
initial_BLUE: 0.0
```

**`chain_count: 20` is mandatory.** 20 LEDs x 3 bytes = 60 bytes = the
v2.3 frame, **exactly**. Any other value truncates or extends the frame
and the device will refuse it (a single surplus byte inflates the
decoder's clock fit by ~1.6 % and forces a refusal — the measured "pad
law" that fixes the frame size at 60 bytes, in v2.3 as in v2.2).

**`color_order: GRB` is mandatory.** The frame is a raw byte stream, not
a picture, so what matters is which `SET_LED` parameter lands on which
wire byte. With `GRB`:

| `SET_LED` parameter | wire byte of that LED |
|---------------------|-----------------------|
| `GREEN`             | 0                     |
| `RED`               | 1                     |
| `BLUE`              | 2                     |

`RBARF_SET` feeds `GREEN=frame[3n]`, `RED=frame[3n+1]`,
`BLUE=frame[3n+2]`, so the frame lands on the wire in order. `GRB` is
also what the top-level `KLIPPER.md` has always specified and what the
application payload itself uses, so a base colour `rrggbb` arrives with
its channels intact.

If you name the section something other than `rbarf`, pass
`LED_NAME=<name>` to every command.

---

## Quick start

```gcode
RBARF_SET MODE=STATIC COLOR=ff0000
RBARF_SET MODE=BLINK  COLOR=ff0000 ALT_COLOR=0000ff DURATION_MS=500
RBARF_SET MODE=FADE   COLOR=00ff00 DURATION_MS=2000 GAMMA=1
RBARF_SET MODE=SPIN   COLOR=ffffff DURATION_MS=1000 FADE=3
RBARF_SET MODE=SEQUENCE SEQ="0,1,5,7" COLOR=00ffff DURATION_MS=1200
RBARF_OFF
```

---

## Modes

| `MODE=`    | wire mode | what it does |
|------------|-----------|--------------|
| `STATIC`   | `0x00`    | base colours, no animation |
| `BLINK`    | `0x01`    | base colour first half of the cycle, `ALT_COLOR` second half |
| `FADE`     | `0x02`    | triangle-wave interpolation base -> `ALT_COLOR` -> base |
| `SEQUENCE` | `0x03`    | walk the LED order you give in `SEQ` |
| `SPIN`     | `0x03`    | sequence `0,1,5,7,6,2` |
| `SPIN_REV` | `0x03`    | sequence `2,6,7,5,1,0` |
| `RAIN`     | `0x03`    | sequence `3,4,0,1,5,7,6,2` |
| `RAIN_REV` | `0x03`    | sequence `2,6,7,5,1,0,4,3` |
| `DRAW`     | `0x03`    | sequence `0,1,2,3,4,5,6,7` |
| `DRAW_REV` | `0x03`    | sequence `7,6,5,4,3,2,1,0` |

`SPIN` through `DRAW_REV` are **expanded by this macro** into mode-`0x03`
sequences. The chip no longer carries the preset tables (owner decision;
see `../app/anim.c`), so the macro packs the nibbles itself and sends
mode `0x03`. The bytes it produces in `flags[7..]` are byte-for-byte the
old on-chip tables:

| mode | `flags[7..]` |
|------|--------------|
| `SPIN` | `01 57 62 FF` |
| `SPIN_REV` | `26 75 10 FF` |
| `RAIN` | `34 01 57 62 FF` |
| `RAIN_REV` | `26 75 10 43 FF` |
| `DRAW` | `01 23 45 67 FF` |
| `DRAW_REV` | `76 54 32 10 FF` |

`verify_macro.py` asserts that equality for every preset.

---

## Parameter reference

Parameters that do not apply to the chosen mode are **rejected with an
explanatory error** rather than silently written into the wrong wire
field. So is any unknown parameter name.

| parameter | value | modes | default | meaning |
|-----------|-------|-------|---------|---------|
| `MODE` | name from the table above | all | `STATIC` | animation mode. Case-insensitive. |
| `COLOR` | `rrggbb` | all | `000000` | one colour for all 8 LEDs (and the fill before the first `COLORS` entry) |
| `COLORS` | `rrggbb,rrggbb,...` | all | — | up to 8 entries, LED 0 first |
| `DURATION_MS` | `0`..`12750` | all but `STATIC` | `1000` | full cycle time |
| `ALT_COLOR` | `rrggbb` | `BLINK` `FADE` | `000000` | the second colour |
| `MASK_COLOR` | `rrggbb` | `BLINK` `FADE` | `000000` | colour shown by masked LEDs |
| `BG_COLOR` | `rrggbb` | sequence modes | `000000` | background behind the running LED |
| `MASK` | LED index list, e.g. `0,3,7` | all but `STATIC` | none | LEDs excluded from the animation |
| `MASK_BITS` | `0`..`255` | all but `STATIC` | `0` | the raw mask byte instead of `MASK` |
| `SEQ` | step list, e.g. `0,1,5,7` | `SEQUENCE` only | — | required for `MODE=SEQUENCE` |
| `FADE` | `0` `2` `3` | sequence modes | `0` | `0` none, `2` = 2-LED fading, `3` = 3-LED fading |
| `GROUP` | `1` `2` `4` | sequence modes | `1` | LEDs lit simultaneously |
| `FEATURES` | `0`..`15` | sequence modes | — | the raw feature byte instead of `FADE`+`GROUP` |
| `GAMMA` | `0` `1` (`OFF` `ON`) | all | `0` | gamma correction on the output |
| `LED_NAME` | section name | all | `rbarf` | which `[neopixel]` to drive |
| `SYNC` | `0` `1` | all | `0` | `0` send now, `1` queue with print moves |
| `DEBUG` | `0` `1` | all | `0` | `1` echoes the 60 frame bytes as hex to the console |

Colours are **exactly six hex digits**, lower or upper case, with no
leading `#`. Quotes around list values are optional but recommended
(`COLORS="ff0000,00ff00"`); Klipper parses parameters with `shlex`, so
quotes are stripped for you.

### `COLOR` / `COLORS`

Carry-forward fill:

* `COLOR` is the starting colour for LED 0.
* each `COLORS` entry replaces the current colour **from that LED
  onwards**;
* an empty entry keeps the previous colour;
* everything past the last entry keeps the last colour.

```gcode
RBARF_SET MODE=STATIC COLOR=ff0000
;   -> all 8 red

RBARF_SET MODE=STATIC COLORS="ff0000,,0000ff,112233"
;   -> red red blue  112233 112233 112233 112233 112233

RBARF_SET MODE=STATIC COLOR=808080 COLORS=",,ff00ff"
;   -> grey grey magenta magenta magenta magenta magenta magenta
```

### `DURATION_MS`

The wire field is one byte of 50 ms units, so the usable range is
**0 to 12750 ms** and the value is snapped to the nearest 50 ms.
`DURATION_MS=0` means static.

A value that would round down to zero (1..24 ms) is **rejected** rather
than silently turning the animation off.

### `MASK` vs `MASK_BITS`

`MASK` takes **LED indexes**, not a bit value:

```gcode
MASK=0,3,7        ; mask LEDs 0, 3 and 7
```

The wire byte has bit 7 = LED 0 down to bit 0 = LED 7, so `MASK=0,7` is
the byte `0x81` (129) and `MASK=0,3,7` is `0x91` (145). If you would
rather write the byte yourself use `MASK_BITS=129`. Giving both `MASK`
and `MASK_BITS` is an error.

What masking *does* depends on the mode:

* `BLINK` / `FADE` — masked LEDs are excluded from the animation and show
  `MASK_COLOR` statically;
* sequence modes — masked LEDs always show their own base colour,
  whatever the animation is doing.

### `SEQ`

A comma-separated list of steps for `MODE=SEQUENCE`:

* `0`..`7` — light that LED;
* `8`, `P`, `PAUSE` or `-` — a pause step that renders nothing;
* at most **31 steps** (the wire field holds 32 nibbles and the last one
  is the terminator).

The macro nibble-packs the steps and appends the terminator itself.

```gcode
RBARF_SET MODE=SEQUENCE SEQ="0,1,5,8,7" COLOR=00ffff DURATION_MS=1500 FADE=3 GROUP=2
;   flags[7..] = 01 58 7F
```

### `FADE` / `GROUP` / `FEATURES`

`FADE` and `GROUP` are the friendly spelling of the feature bits:

| `FADE=` | bit | `GROUP=` | bit |
|---------|-----|----------|-----|
| `0` | — | `1` | — |
| `2` | bit 1 (2-LED fading) | `2` | bit 2 (2-LED grouping) |
| `3` | bit 0 (3-LED fading) | `4` | bit 3 (4-LED grouping) |

3-LED fading has priority over 2-LED fading on the chip, and 4-LED
grouping over 2-LED grouping — which is why the friendly parameters only
let you pick one of each. `FEATURES=0..15` writes the byte directly and
cannot be combined with `FADE` or `GROUP`.

### `GAMMA`

`0` = off, `1` = on. The current firmware build carries a single curve
(gamma 2.2), so `2`, `3` and `4` are accepted for forward compatibility
with the old four-curve field but behave exactly like `1`.

### `SYNC`

Default `0`: the frame goes out immediately. `SYNC=1` queues it with the
print-move lookahead, i.e. Klipper's own `SET_LED` default. Klipper
builds too old to know `SYNC` ignore the parameter and behave as
`SYNC=1`.

---

## `RBARF_OFF`

```gcode
RBARF_OFF [LED_NAME=<name>]
```

Equivalent to `RBARF_SET MODE=STATIC COLOR=000000`. It sends a complete
v2.3 frame like every other command, so the device replaces its state
instead of holding the previous animation.

---

## More examples

```gcode
; red blinking to blue twice a second
RBARF_SET MODE=BLINK COLOR=ff0000 ALT_COLOR=0000ff DURATION_MS=500

; green breathing over two seconds, gamma corrected
RBARF_SET MODE=FADE COLOR=00ff00 DURATION_MS=2000 GAMMA=1

; red fading to green, but LEDs 0 and 7 pinned blue
RBARF_SET MODE=FADE COLOR=ff0000 ALT_COLOR=00ff00 DURATION_MS=1000 MASK=0,7 MASK_COLOR=0000ff

; white spin with a 3-LED comet tail on a black background
RBARF_SET MODE=SPIN COLOR=ffffff BG_COLOR=000000 DURATION_MS=1000 FADE=3

; blue rain, two LEDs at a time, no fading
RBARF_SET MODE=RAIN COLOR=0000ff DURATION_MS=1500 FADE=0 GROUP=2

; a per-LED gradient held static
RBARF_SET MODE=STATIC COLORS="200000,400000,600000,800000,a00000,c00000,e00000,ff0000"

; custom walk with a pause between passes
RBARF_SET MODE=SEQUENCE SEQ="0,1,2,3,P,P" COLOR=ffaa00 DURATION_MS=1200 FADE=2

; what exactly went on the wire
RBARF_SET MODE=STATIC COLOR=ff0000 DEBUG=1

; a differently named neopixel section
RBARF_SET MODE=STATIC COLOR=ff0000 LED_NAME=status_strip
```

---

## Verifying it without hardware

```
python3 klipper/verify_macro.py
```

This is a real proof, not a smoke test. It

* reads `rbarf.cfg` with **the same parser Klipper uses**
  (`RawConfigParser(strict=False, inline_comment_prefixes=(';', '#'))`),
* renders the macro with the **real jinja2 library** in Klipper's exact
  environment (delimiters `{% %}` / `{ }`, `jinja2.ext.do`, `params` as
  strings, `action_raise_error` / `action_respond_info` with Klipper's
  return values),
* runs the rendered G-code through a miniature dispatcher that parses
  extended commands the way `gcode.py` does and recurses into
  `SET_LED_INTEGER`,
* emulates `neopixel.py` — `int(value * 255. + .5)` per channel in
  `color_order` — to recover the exact 60 bytes that would leave the pin,
* and asserts them against ground truth built with `../bench/crc.py` and
  `../bench/patterns.py`.

Covered: static, carry-forward `COLORS`, blink, fade with a mask, an
explicit sequence with a pause and a terminator, all six preset
expansions byte-matched against the nibble tables, every `FADE`/`GROUP`
combination, gamma on and off, `RBARF_OFF`, three randomized frames, the
3-byte header / 3-byte trailer / tripled 16-bit check block (HI,LO per
copy) / `TRANSMIT` pattern on every case, the two arithmetic identities
the table-free Jinja CRC16 depends on (the `x ^ 0x1021` fold for all
32768 even 16-bit values, and the whole bit-serial loop against
`crc.py` over 2006 vectors), 32 input-validation errors, and a lint for
Jinja constructs Klipper cannot take — including a check that no CRC8
survives in the macro bodies. 93 cases, all green.

## Verifying it *with* hardware

`../bench/test_klipper_macro.py` renders the macro exactly the same way
and pushes the frames at the real device through the Pico test probe,
scoring the decode reports against ground truth. The default variant is
`frame` — the exact 60-byte stream Klipper clocks out, which IS the
protocol frame; `pad1`/`lead1` add one surplus 0x00 as negative controls
that the pad law says must refuse.

> **No longer blocked — the v2.3 image exists, fits and has run.** The
> verbose link was **46 B over** `CAPARM0` after the pipeline tail went
> back to hand assembly (`../recon/PROD_CLOSURE.md` §14.2). It fits now:
> in VERBOSE builds only, eps is emitted as `x` + 4 hex digits through the
> hex printer the `V:` line already carries, which drops the 92 B decimal
> printer (`uart_put_i16` 84 B + its power-of-ten table 8 B) for 6 B. The
> verbose link ends `0x9F4C`, **4 B below the terse image's** `0x9F50`;
> `guard_prod.py` is green on both maps and the pinned capture block is
> byte-identical in both images and to the ledger. The **shipping terse
> image did not change** (md5 `b79f4324…`, still prints decimal eps).
> `bench/epsfmt.py` parses both encodings, so old bench logs still read.
>
> **The trailer byte is DECIDED, APPLIED and now confirmed on v2.3
> silicon (owner, 2026-09-07):** `TRAILER = 9A 00 FF`. Fresh corpora
> acquired with it score **97.78 % (88/90), 0 wrong** against the old
> `9A 55 FF` corpora's **78.9 % (71/90)** through the same shipped
> decoder — paired by `(pattern, rep)`, McNemar **19:2**, χ²(cc) 12.19,
> exact p = 2.2 × 10⁻⁴ (§15.1) — and against v2.2's **93.3 %**. That
> reproduces §13.3's drift-interleaved A/B (71.1 % → 97.8 %, 25:1,
> p < 0.001) independently. `rbarf.cfg`'s trailer literal
> (`154, 0, 255`), `verify_macro.py`'s trailer lint and the frame diagram
> above all carry the byte; sizing is unchanged (60 B = 20 LEDs).
>
> The v2.2 run below is kept as the number v2.3 had to reproduce — it did,
> with 5 frames to spare (44/51 vs 39/51), warm.

**v2.3 SILICON GATE run (2026-09-07, warm, in
`../recon/approaches/dev_prod/bench_v23_klipper.json`):**

```
17/17 cases render byte-exact against verify_macro.py ground truth
44/51 delivered (41 direct + 3 chase-repaired), 0 CATASTROPHIC, 0 silent
  refusals 7: R3 infeasible 5, R1 lock 1, R8 chase 1
  eps -0.89 .. -0.99 % on delivered  (auto-trim at code 0, 44/44 in band)
  13 of 17 cases 3/3; worst preset_rain_rev 1/3
  preset_rain 3/3 and every preset_rain_rev emission byte-correct --
  these are the two frames that produced the only two catastrophic
  emissions in this project's history
```

**Last v2.2 run (2026-09-07, post-fix, in
`bench_klipper_macro_results.json`):**

```
17/17 cases render byte-exact against verify_macro.py ground truth
39/51 delivered (30 direct + 9 chase-repaired), 0 CATASTROPHIC, 0 silent
  refusals 12: R2 marker 6, R8 chase 5, R3 infeasible 1
  eps -0.98 .. -1.32 %  (auto-trim parked at code 0, in band throughout)
```

**Historical v2.1 run (2026-09-06, the campaign that motivated v2.2 —
results now in `bench_klipper_padplacement.json`; the v2.2 pre-fix run
with the two catastrophic rows is in
`bench_klipper_macro_results.prefix_baseline.json`):**

```
15/15 cases render byte-exact against verify_macro.py ground truth
3/90 delivered, 0 CATASTROPHIC, 0 silent
  bare   (59 B): 3/45   eps mean +0.24 %
  padded (60 B): 0/45   eps mean +1.79 %   43/45 refuse R3 infeasible
  lead   (60 B): 0/30   eps mean +1.85 %   (pad at the front is no better)
```

`../bench/pad_law.py` then isolated the mechanism on a payload with no
margin problem, sweeping 0–3 pad bytes in both positions: the eps offset
is linear at **+1.6 % per surplus byte** and delivery goes 4/4 → 0/24 at
the first extra byte. That measurement is why v2.2's frame is 60 bytes.

To re-run when the bench is free (this is exactly what §15.5 ran):

```
make rbarf-prod                 # guard_prod.py green on BOTH maps
python3 flash.py --ihx build/rbarf_prod_verbose.ihx flash-only
python3 bench/test_klipper_macro.py --bench-is-free --reps 3
```

`make rbarf-prod` now produces both images and exits 0.

Without `--bench-is-free` it prints its instructions and exits without
opening anything.

---

## Notes on Klipper

* **Delimiters.** Klipper's Jinja uses `{% %}` for statements and single
  braces `{ }` for expressions — not `{{ }}`. The macro follows that.
* **No bitwise operators.** Klipper's Jinja has no `^`, `&`, `<<` or
  `>>` (`|` is the filter operator). That is why the CRC-16 is computed
  bit-serially rather than with a lookup table: a table-driven CRC16
  needs `(crc >> 8) ^ byte` plus a 256-entry 16-bit table, so it would
  require a second table just to XOR two bytes. The bit-serial form
  keeps one single-bit XOR (`(a+b) % 2`) and folds the polynomial
  arithmetically, which is exact because bit 0 of the register is always
  clear right after the shift:

  ```
  x ^ 0x1021 == x + 4129 - 8192 * ((x // 4096) % 2)    (bit 12)
                         -   64 * ((x //   32) % 2)    (bit 5)
  ```

  It mirrors `crc16_ccitt_false_bitwise()` in `../bench/crc.py` — the
  same table-free reference an on-chip port mirrors — and
  `verify_macro.py` proves the identity for all 32768 even 16-bit values
  and the two implementations agree on every frame.
* **No `0x` literals.** Klipper pinned Jinja2 2.11.3 for years, and
  Jinja2 2.x cannot lex hex integer literals. Everything in the macro is
  decimal.
* **No `{# #}` comments.** Klipper reads `.cfg` with
  `inline_comment_prefixes=(';', '#')`, which would eat the closing `#}`
  of a Jinja comment preceded by a space and leave the comment
  unterminated. The `;` lines inside the macro bodies are stripped by
  that same parser before Jinja ever sees them, which is safe.
* **`SET_LED_INTEGER`.** Every value on the wire is an exact 0–255
  integer; the helper divides by 255.0 once and Klipper's
  `int(v * 255 + 0.5)` recovers the byte exactly. This is the convention
  the top-level `KLIPPER.md` established and it is kept here.
* **`SYNC`.** `SET_LED SYNC=` is a newer Klipper parameter. Builds that
  do not know it ignore it (Klipper does not reject unknown parameters),
  which means those builds behave as `SYNC=1`.
* **No `printer.` access.** The macro reads nothing from the printer
  object, so it works before homing, during a print, and from any
  context.

### If you are coming from the old `KLIPPER.md` macros

The top-level `KLIPPER.md` documents the **v1** framing and is obsolete:

| | old (v1) | new (v2.3) |
|---|---|---|
| `chain_count` | 17 | **20** (= the 60-byte frame, exactly) |
| sync preamble LED | `G=255 R=255 B=254`, mandatory | **gone** — do not send it |
| framing | none | `FF AA 65` … `9A 00 FF` |
| check block | none | `CRC16` x3 (HI,LO each) over the 48 data bytes |
| preset modes `0x04`-`0x09` | sent as-is, chip expanded them | **host-expanded** into mode `0x03` here |
| commands | `RBARF_STATIC`, `RBARF_BLINK`, `RBARF_SPIN`, … | one `RBARF_SET MODE=…` |
| colour parameters | `RED=` `GREEN=` `BLUE=` integers | `COLOR=rrggbb` |

Sending a v1, v2.1 or v2.2 frame to v2.3 firmware gets you a refusal,
not a wrong animation — but it is still a lost frame, so remove the old
macros.
