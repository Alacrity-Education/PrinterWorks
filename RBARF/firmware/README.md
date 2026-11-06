# RBARF firmware (`src/`)

Firmware for the STM8S001J3 (SO8N): a WS2812 **receiver** that decodes a data
stream faster than its own sampler, developed against the RP2040 test-probe
bench (path configurable — see [Configuration](#configuration--no-hardcoded-paths)).
The previous, pre-rewrite attempt lives in `../archive/legacy-firmware/` and is
not touched. The engineering documents (`ARCHITECTURE.md`, `PROTOCOL.md`,
`RECONSTRUCTION_PAPER.md`, `APP_BUDGET.md`) live in `../docs/`.

Status: **GO** on the v2.3 silicon gate — `recon/PROD_CLOSURE.md` §16.
Start with `make verify`.

## Layout

| path | role |
|---|---|
| `rbarf_prod.c` | **production main** — v2.3 receiver: armed capture, decode, auto-trim, 40 ms render, terse UART |
| `decode.c` / `decode.h` / `decode_asm.s` | the decoder. `decode.c` is the host-parity reference; `decode_asm.s` is the hand-assembled v2.3 pipeline tail actually shipped (`USE_ASM_DEC=1`) |
| `cap_arm.s` / `caploop.s` / `scan.s` | armed capture front end, the **cycle-calibrated sampling loop** (ABS-pinned at `0x9FA1`, phase `0xF`) and the asm scan hot path |
| `vectors_prod.s` | interrupt vector table |
| `reference/` | the whole firmware **written to be read** — four portable C99 files, one per component: `rbarf_decoder.c` (the decoder, v2.3 only, no build-time forks, one section per pipeline stage), `rbarf_capture.c` (`cap_arm.s` + `caploop.s`, rendered line for line with cycle counts, plus a host-executable model of the fitted sampler), `rbarf_ws2812_out.c` (the output driver and **every** inline-asm block in the shipped image) and `rbarf_vectors.c` (the vector table and its 92-byte gap reuse). Documentation, not firmware: proven bit-exact against `embedded_v2.py` by `make ref-parity` and byte-exact against `v23lib.capture()` by `make ref-capture-parity` |
| `app/` | application: `anim.c` (animation engine), `ws2812_out.c` (output driver), `tick.c` (TIM4 1 ms timebase) |
| `capture.c` + `cap_code.s` | the calibrated **acquisition** firmware — oversamples pin 7 like a logic analyser and dumps raw hex over UART. Its image is a ledger artifact |
| `hello.c` | UART bring-up image: 9600 8N1 on pin 8, 5 s SWIM window |
| `guard_prod.py` | **link guard** for every production link — address-phase pinning, REL/ABS overlap, the arm's BTJT poll targets. Never bypass it |
| `guard_caploop.py` | the weaker legacy guard for the superseded v2.1 links |
| `toolcheck.py` | pins the toolchain (see below) |
| `rbarf_config.py` | **all machine-specific paths** live here — probe library, probe port, external tools |
| `flash.py` | power-cycle via the probe, flash via stm8flash/ST-LINK, verify UART |
| `bench/` | host tooling: `patterns.py` (test payloads), `crc.py` (framing + CRC), `drive_prod.py` / `rate_spot.py` / `test_klipper_macro.py` (bench drivers), `demo.py` (animation demo reel) |
| `klipper/` | `rbarf.cfg` (the Klipper macro), `verify_macro.py` (93 host checks), bench results |
| `recon/` | the host reference and every published report: `synth.py` (calibrated sampler model), `harness.py`, `eval.py`, `approaches/embedded_v2.py` (**normative** decoder reference), `approaches/combined.py`, `PROD_CLOSURE.md`, `ARM_INVESTIGATION.md`, `MARGIN_INVESTIGATION.md`, `EMBEDDED_V2_SPEC.md`, … |
| `data/` | the acquired capture corpora. `captures_val.json` is a **sealed** validation set — never open it |
| `archive/` | superseded firmware variants, the design phase, completed investigations. See `archive/README.md` |
| `../docs/PROTOCOL.md` | the wire protocol (v2.3: `FF AA 65` + 48 DATA + `[CRC16]*3` + `9A 00 FF` = 60 B = 20 LEDs) |

## Toolchain (pinned)

The shipping images are **byte-reproducible**, and that only holds for one
toolchain — SDCC's code generator is not stable across releases:

```
sdcc      4.6.0
sdasstm8  V05.50.4     (sdas assembler, STM8)
sdld      V05.50.4
```

`toolcheck.py` runs at the start of every build and **fails loudly** on
anything else, rather than silently producing a different image. (The old
June 2026 firmware in `../archive/legacy-firmware/` was built with SDCC 4.5.0 — that
version is caught.) For a deliberate experiment:

```sh
make RBARF_SKIP_TOOLCHECK=1 <target>    # produces a NON-LEDGER image
```

### The flash ledger

`make clean && make all` must reproduce exactly:

```
b8f0ae06e740e0f811ff3ebcb0a201ab  build/rbarf_prod.ihx
5524ce94f4ae3cb404503beccb0b9373  build/rbarf_prod_verbose.ihx
84955f771ef8ad41a36fc16187afca38  build/capture.ihx
```

`make ledger` asserts all three; `make verify` includes it.

### The chase-budget bench images

The two chase constants are Makefile variables since
`recon/AMAX_TMAX_SWEEP.md` — `A_MAX` (admitted candidates, and the R7
admission cap) and `T_MAX` (residual comparisons, which IS the per-frame
false-accept bound).  **The defaults are the ledger values**, so an unset
variable rebuilds the three images above byte-identically; the values
reach `decode.c` as `-DA_MAX_CFG/-DT_MAX_CFG` and `decode_asm.s` as a
generated `chase_cfg.inc` (`gen_chase_cfg.py` — `sdasstm8` has no `-D`).

```sh
make amax-verbose A_MAX=16 T_MAX=192   # one VERBOSE bench image
make amax-bench                        # the baseline + both chosen points
```

```
5524ce94f4ae3cb404503beccb0b9373  build/rbarf_prod_verbose_A11_T131.ihx
952c7446d8e26426c8426792fd56361f  build/rbarf_prod_verbose_A14_T131.ihx
d8db7f4a27d521026c5b41679b2f2b8e  build/rbarf_prod_verbose_A16_T192.ihx
```

The A11_T131 row **is** the ledger verbose image, byte for byte — that is
the byte-identity proof for the parameterisation, and `make amax-bench`
`cmp`s it.  These are BENCH images: not in `all`, not in `ledger`, not in
`verify`.  `guard_prod.py` check 7 re-derives both constants from the
`.inc` beside the map and refuses a link whose stack region falls below
124 B (the measured 115 B peak + 9), which is what stops `A_MAX >= 22`:
the candidate arrays are REL DATA, 3 B per entry, out of a 148 B stack
region.

## Build

```sh
make                # = make all: every shipping image
make verify         # the hardware-free proof suite -- run this first
make help           # every target, one line each
make clean          # remove build/ and nothing else
```

`make all` builds only shipping images, so no optional or bench target can
break it. `make rbarf-prod` additionally prints the flash-area map.

Superseded targets (`rbarf-v21`, `rbarf-v21-trim`, `capture-trim`) build from
`archive/firmware-variants/`. Only `capture-trim` still links; the two v2.1
decoder targets fail their guard on purpose — `archive/README.md` explains
why, and why you must not "fix" it by moving the capture loop.

## Verify

`make verify` runs the whole hardware-free proof suite in ~3 s and fails on
any drift:

| # | check |
|---|---|
| 1 | the three ledger md5s (asserted) |
| 2–3 | `guard_prod.py` on both production maps |
| 4 | `recon/approaches/dev_arm/absmd5.py` — the pinned CAPLOOP blocks against the ledger |
| 5–6 | `bench/crc.py` and `bench/patterns.py` self-tests |
| 7 | `recon/approaches/embedded_v2.py` reference self-test |
| 8 | `klipper/verify_macro.py` (93 checks) + host parity `decode.c` ↔ `embedded_v2.py` (549 captures) |

Deliberately excluded because they are slow or need hardware: ucsim
bit-exactness (`recon/approaches/dev_prod/ucsim_v23.py`) and every bench
gate/soak.

## Configuration — no hardcoded paths

Everything machine-specific is resolved by `rbarf_config.py`, and every
value has an environment override. The defaults are the bench the shipping
images were proved on, so nothing needs setting on that machine:

| variable | default | what |
|---|---|---|
| `RBARF_PICOTOOL_HOST` | `/home/alex.lucaci/Projects/picotool/host` | directory holding the RP2040 probe library (the `testprobe` package) |
| `RBARF_PROBE_PORT` | glob `/dev/serial/by-id/usb-Raspberry_Pi_Pico_*`, else `/dev/ttyACM0` | probe serial device |
| `RBARF_STM8FLASH` | PATH lookup | `stm8flash` binary |
| `RBARF_UCSIM` | PATH lookup | `ucsim_stm8` binary |
| `RBARF_SDCC` / `RBARF_SDAS` | PATH lookup | compiler / assembler |
| `RBARF_SKIP_TOOLCHECK` | unset | bypass the toolchain pin (non-ledger build) |

On another machine, typically only the first is needed:

```sh
export RBARF_PICOTOOL_HOST=~/src/picotool/host
python3 rbarf_config.py          # prints what resolved, and what did not
```

A missing or misconfigured tool gives a one-line explanation, not a
traceback.

## Flash and bench (needs the rig)

```sh
make flash                  # hello bring-up image, then verify UART output
make flash-capture          # the calibrated acquisition image
make flash-prod             # production image (terse)
make flash-prod-verbose     # production image (verbose bench build)

python3 flash.py listen 15         # power-cycle and dump UART
python3 flash.py power on|off      # manual target power
python3 flash.py --ihx build/rbarf_prod.ihx flash-only
```

Bench drivers (all single-transmission, all under the 5-second rule):

```sh
python3 bench/drive_prod.py            # 10 production frames x N reps, scored
python3 bench/rate_spot.py             # applied-frame-rate probe
python3 bench/test_klipper_macro.py    # Klipper macro end to end
python3 bench/acquire.py               # collect a capture corpus -> data/
python3 bench/demo.py --list           # the animation demo reel
```

Expected `make flash` verification output: first byte ~5.1 s after power-on,
then `RBARF hello #N` every ~500 ms.

## Acquisition and reconstruction pipeline

1. `make flash-capture` — flash the capture firmware.
2. `python3 bench/acquire.py` — captures every pattern x3 into `data/captures.json`.
3. `python3 recon/eval.py recon/approaches/<name>.py` — score a decoder.

Timing truth discovered during bring-up (see `recon/DATASET.md` ADDENDUM):
the sampling loop is exactly 40 cycles (not the documented 37), with a
data-dependent +/-1-2 cycle term per HIGH read (`w = [0,-1,0,+2,0,0,0,+1]`),
fitted to 99.96 % sample agreement. That model lives in `recon/synth.py` and
is what the whole decoder is calibrated against.

## Reconstruction results (2026-09-05)

- `recon/approaches/combined.py` — Fable-5-architected fusion of six
  designed techniques (`archive/design-phase/designs/*.md`): **53/54 exact** on the
  tuning set (99.7 % bytes), 18/18 holdout, **21/24 on the sealed
  validation set** (`data/captures_val.json` — never used for tuning).
  Refuses rather than guesses on corrupted input (0 confident-wrong in
  109+ perturbation probes). The one tuning-set miss is at the measured
  information limit of the sampler.
- Temperature envelope (`recon/HSI_TEMPERATURE.md`): perfect in
  ε ∈ [-2.5 %, +1 %], graceful on the slow side, refuses at fast
  corners. Production answer: runtime `CLK_HSITRIMR` auto-trim using the
  decoder's own ~0.004 %-precision clock measurement.
- HSITRIMR sweep on hardware (`recon/TRIM_SWEEP.md`,
  `data/captures_trim.json`): 3-bit **signed** trim, ≈ -1.16 %/step,
  authority -4.4…+3.7 %; code 7 cancels this unit to +0.022 %.
  Discovery: merged-1 artifacts PEAK at ε≈0 (40-cycle loop resonates
  with 2 bit periods) while swallowed-0s vanish — the forward drift
  correction should target a small deliberate offset, not exactly 0.
- Embedded feasibility (`recon/EMBEDDED_FEASIBILITY.md`,
  `recon/approaches/embedded_ref.py` + `archive/investigations/dev_embedded/decoder.c`):
  integer-only port scores 51/54; **RAM fits** (~925/1024 B incl. 256 B
  capture buffer), **flash over by ~2.3 KB** and decode ~300 ms vs
  100 ms budget as auto-compiled C — needs hand-asm hot paths or a
  bigger-flash part. A 1–2 byte payload CRC is recommended for the
  production protocol.

## Bench wiring (verified 2026-09-05)

```
Pico GPIO28 -> MOSFET gate: 1 = target power ON, 0 = OFF
Pico GPIO29 -> WS2812 test signal into STM8 pin 7
Pico GPIO1  <- STM8 pin 8 (UART debug, 9600 8N1, receive-only)
ST-LINK/V2: SWIM -> STM8 pin 8 DIRECT (no series resistor!)
            TVCC -> target 3.3 V rail (MANDATORY, see below)
            GND  -> common bench ground
20 kOhm pull-up on the SWIM line (works; do not go lower unless entry
becomes flaky - then 1 kOhm)
```

STM8 pin 8 bonds PD1/SWIM + PD5/UART1_TX (+ PD3, PC6): SWIM and the debug
UART TX share the physical pin.

## The 5-second rule

Every firmware MUST keep pin 8 untouched for the first 5 seconds after
power-on (`delay_ms(5000)` before any UART/GPIO config of the shared pin).
That window is when `flash.py` performs SWIM entry - it is the only way to
reflash, since the SO8N package has no reset pin. After the window the
firmware disables SWIM (`CFG_GCR = 0x01`) so UART traffic cannot disturb it;
a power-on reset re-arms SWIM for the next flash.

## Hardware lessons learned (debug session 2026-09-04/05)

1. **ST-LINK TVCC must be fed 3.3 V from the target rail.** The SWIM line
   driver is powered/referenced from TVCC. With TVCC floating it reads
   ~0.65 V, the dongle holds SWIM low and every attempt fails instantly with
   `SWIM error 0x09` without ever driving the line.
2. **No series resistor in the SWIM line.** A 470 Ohm resistor (originally
   contention protection) breaks SWIM: entry reaches the target and the
   target answers, but the reply is mangled at the dongle (`SWIM error
   0x04`). Contention protection is unnecessary: the dongle releases the
   line when idle and the 5 s window keeps TX quiet during flashing.
3. `stm8flash -c stlinkv2 -p stm8s001j3` works as plain user; ST-LINK target
   voltage can be read via USB cmd `0xF7` for bench diagnostics.
4. The Pico can sniff the SWIM/UART line (UART RX at 1 Mbaud frames every
   low pulse) - useful to see whether entry pulses/replies reach pin 8.
