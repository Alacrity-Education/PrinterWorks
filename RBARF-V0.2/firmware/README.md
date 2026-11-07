# RBARF v0.2 firmware (STM32C011D6, Rust + Embassy)

`rbarf-anim` is a byte-exact port of the v0.1 `RBARF-V0.1/firmware/app/anim.c` engine.
`rbarf-fw` renders it at 100 Hz and drives the 8 WS2812 LEDs, and receives
v2.3 frames on LED_IN (`src/ws2812_in/`, decode logic in `rbarf-proto`; see
"Receiver" below).
Status (2026-10-03): display path runs on the board. The receiver is
implemented and armed on the board, but has not seen a real frame yet: the
Pico's WS2812 stimulus (GPIO3) is not wired to LED_IN. The PWM+DMA output
needed one fix, found with the webcam check (`bench/led_cam.py`): embassy's `waveform_up`
enables the timer's update-DMA request before it starts the DMA channel, so
the first buffer entry could be lost and LED0 then showed its value doubled
for one 10 ms frame, about 3 times a second ("jittery animations"). The DMA
buffer now starts with one idle entry (`LEAD` in `ws2812_out/pwm.rs`).
A demo task cycles through built-in frames every 5 s (static, blink, fade,
spin, spin with gamma) until the receiver accepts its first frame, then
stops for good.

## Build / flash / run

```sh
cd firmware
cargo build --release              # firmware, thumbv6m-none-eabi (default target)
cargo run --release                # flash + defmt RTT log: probe-rs run --chip STM32C011D6
cargo test-anim                    # host tests incl. C parity (= cargo test -p rbarf-anim --target host-tuple)
cargo test-proto                   # host tests of the receiver's decode step (rbarf-proto)
(cd rbarf-anim && cargo test)      # same, from the crate directory
```

The workspace default target is thumbv6m, so a plain `cargo test -p rbarf-anim`
run from `firmware/` would build the tests for the MCU. Use one of the two test
commands above instead. The parity test compiles the original `RBARF-V0.1/firmware/app/anim.c`
with the host C compiler. The firmware build never needs a C compiler.

Features of `rbarf-fw`, one per group:

| Group | Default | Alternative |
|---|---|---|
| LED output backend | `out-pwm`: TIM1 CH1 PWM + DMA | `out-spi`: SPI1 MOSI on PA2. Compiles, untested |
| embassy-time driver | `time-tim14`: own driver on TIM14 (`src/time_driver.rs`), bench-tested. Resource split B: TIM3 goes to the receiver | `time-tim3`: embassy-stm32 `time-driver-tim3`. No receiver in this build; the demo runs forever |

Bench diagnostics (off by default): `time-selftest` (boot-time check of
`Timer::after`/`Timer::at`, including the 65.536 ms TIM14 period boundary and
an alarm in the past) and `rx-hist` (64-bin width histogram of every
480-pulse burst, logged every 10 s; bench check B2).

Build a non-default combination with, for example,
`cargo build --release --no-default-features --features out-pwm,time-tim3`.

All crates come from crates.io (no git dependencies).

## Hardware facts (from `hardware/PINOUT.md`)

| Item | Value |
|---|---|
| MCU | STM32C011D6Yx WLCSP-12, 32 KB flash, 6 KB RAM. HSI48 only, no crystal. Reset clock 12 MHz. Firmware sets SYSCLK = 48 MHz (HSI48 / 1, flash 1 WS) |
| LED output | Ball **F3** = PF2-NRST / PA0 / PA1 / PA2. Firmware uses **PA0 = TIM1_CH1 (AF5)** and sets SYSCFG_CFGR3.PINMUX1 = 01. Goes to the Q1 NMOS **inverter**, so MCU HIGH = DIN LOW. The pin idles driven HIGH. High-Z would leave the gate floating |
| Output timing | 48 MHz / 60 = 800 kHz. T0H 17 ticks, T1H 34 ticks. 192 data periods, then 48 zero periods (60 µs latch). CCR1 ends at 0, so the pin stays HIGH. The driver also waits 300 µs (`LATCH`) after the last frame before the next one |
| DMA | tim1_up on DMA1 CH1 (`waveform_up`) |
| NRST | F3 is a GPIO only when FLASH_OPTR.NRST_MODE = 10. The factory value is 11 |
| UART | **PC14 = USART1_TX (AF0)**, ball B3 → TP3, 115200 8N1, TX only. Prints the same heartbeat as RTT |
| SWD | PA13 (TP1) and PA14 (TP2) only. **No NRST on the debugger**, so connect-under-reset is impossible. Firmware never touches PA13/PA14 and never enters Stop/Standby |
| LED_IN | Balls D1 (PA8 / PA11 / PA9) and F1 (PA3..PA6), shorted together, raw 5 V. Never outputs, never pulls. **PA6 = TIM3_CH1 AF1 input**, open-drain, no pull, SYSCFG_CFGR3.PINMUX5 = 11. PA8/PA11 digital input, no pull. PA3/PA4/PA5/PA9 stay analog |
| Receiver | TIM3 PWM input + DMA1_CH2 (tim3_ch2, circular, 1024 B ring), TIM3 interrupt at the top NVIC level |
| Time base | TIM14 (own embassy-time driver, 1 MHz tick), NVIC level 1 |
| UART DMA | DMA1_CH3 (usart1_tx). All three DMA channels are now in use |
| NVIC | M0+ has 4 levels. embassy-stm32 0.6 builds with `prio-bits-4`, so its `Priority::P1..P3` all land on level 0. Use P0/P4/P8/P12 (`board::PRIO_*`) |
| Reserved/untouched | PA1, PA2, PF2 (the other F3 GPIOs), the other TIM1 channels, SPI1, TIM16/17 |
| Bench | Pico GPIO28 = DUT power (PMOS high-side, 1 = ON), GPIO3 = WS2812 stimulus into LED_IN (J2.2), GPIO1 = UART0 RX from TP3 (115200). ST-LINK/V2 does SWD and RTT through probe-rs (see `docs/PICOTOOL.md`) |

All pin, timer and DMA bindings are in `rbarf-fw/src/board.rs`.

## Bench

`bench/rbarf_bench.py` drives the RP2040 test probe (DUT power) and probe-rs
(ST-LINK, SWD only).

| Subcommand | What |
|---|---|
| `power on\|off\|cycle` | switch DUT power via Pico GPIO28 |
| `info` | SWD attach check |
| `optr` | decode FLASH_OPTR (incl. NRST_MODE) |
| `reset` | debugger system reset; the core runs afterwards (`probe-rs download` leaves it halted) |
| `flash [--elf F]` | download, then power-cycle |
| `rtt [--seconds 20]` | attach and stream the defmt RTT log |
| `run [--seconds 20] [--no-build]` | build, flash, power-cycle, RTT log |
| `rtt --no-uart` | RTT only, leaves the Pico port free for a parallel `send` |
| `send` | build v2.3 frames and send them into LED_IN from Pico GPIO3 (see below) |

`send` encodes with `RBARF-V0.1/firmware/bench/crc.py` (the v0.1 reference encoder): `FF AA 65`
+ 48 data bytes + CRC16-CCITT-FALSE x3 + `9A 00 FF`. The payload comes from
`--hex` (48 bytes), `--preset` (the `demo.rs` frames, plus `blue`, `red`,
`green` and `off` solid colours), or `--pattern counter|prbs|all` (soak
payloads; frame number in data bytes 0..4, which the `rx:` line echoes as
`last`; `all` also cycles the 16-byte stress set of `RBARF-V0.1/firmware/bench/patterns.py`
tiled to 48 bytes). `--count N`, `--interval S` (extra idle on top of the
Pico's own 310 us latch), `--dry-run` prints the frames in hex. Frames go 32
per probe batch, about 458 frames/s. The Pico latches after every frame, so
the gap between frames is at least 310 us, and the 50 us gap of B4 cannot be
produced with this API.

`bench/led_cam.py NAME --record 45` records the LEDs with the webcam at fixed
exposure, isolates the LED by temporal variance and counts one-frame
brightness spikes (0 expected; the pre-fix firmware gave 50 to 70 per 45 s).

Environment: `RBARF_PICOTOOL_HOST` (default `~/Projects/picotool/host`),
`RBARF_PROBE_PORT` (default the Pico under `/dev/serial/by-id/`, else
`/dev/ttyACM0`).

Caveats:
- Power-cycle after flashing a virgin part: it boots the ST system bootloader
  while flash is empty (EMPTY flag), re-evaluated only at power-on or
  option-byte load. `flash` and `run` do this.
- The first boot may reprogram NRST_MODE and reset the chip once, so the RTT
  log may restart.

## First boot / option bytes

`optbytes::ensure_nrst_gpio()` runs first in `main`. If NRST_MODE ≠ 10, it
logs a warning and then rewrites only the NRST_MODE field (RDP and everything
else are written back unchanged). It then starts the option-byte load, which
resets the chip. Expect one extra reset on the first boot of each board. A
no-init RAM marker stops it retrying in a loop. If the field is still wrong,
the LED output stays disabled and an error is logged over RTT and UART.

A **virgin** part with empty flash boots the ST system bootloader (EMPTY
flag). After the first flash, **power-cycle** the board (Pico GPIO28 off/on)
so that it boots from main flash.

## Receiver (`src/ws2812_in/`, split B)

Design: `docs/INPUT_CAPTURE_OPTIONS.md` option 4a, implemented as specified,
with no fallback in use. TIM3_CH1 on PA6 (ball F1) runs in PWM-input mode.
A rising edge resets and starts the counter (SMS = 1000, TS = TI1FP1). The
falling edge captures the high time in CCR2 (IC1F = 0010). Each capture
makes DMA1_CH2 copy CCR2's low byte into a circular 1024-byte ring. CR1 has
OPM = 1 and URS = 1, with ARR = 959. After 20 µs without a rising edge the
counter overflows and stops, giving one update interrupt per frame. That
ISR (`hw.rs`, top NVIC level, about 50 cycles) clears UIF/CC1OF/CC2OF,
snapshots the DMA index and signals the task. The task then:
- runs `rbarf_proto::decode`: n must be 480, widths ≥ 27 ticks are 1, pack
  60 bytes, check `FF AA 65` / `9A 00 FF`, check the CRC16 with a strict
  per-byte 2-of-3 majority;
- checks that the DMA did not overwrite the frame while it was being read;
- on success, writes `FRAME` and stops the demo.

Failures are counted by cause and the previous frame stays displayed.

Once a second the heartbeat prints:

```
rx: ok N | short N long N marker N crc N ovr N late N missed N vote N | uif N restarted N | w0 a..b w1 c..d | dma I line L | last XXXXXXXX
```

The counters are cumulative. `w0`/`w1` are the min..max widths per class
during the last second (255..0 means none). `uif` counts end-of-frame
interrupts. `restarted` counts UIFs that found the counter already
restarted (B1 expects 0). `vote` counts frames accepted with an unequal CRC
copy. `last` is data bytes 0..4 of the last accepted frame. The UART
heartbeat appends `rx ok/errors`.

Logging cost: defmt-rtt encodes each frame inside a critical section, so
interrupts stay masked for the whole log call. Measured: an empty frame
takes 46 µs with rzcobs and 14 µs with `encoding-raw` (enabled on the `defmt` dependency in `rbarf-fw/Cargo.toml`; probe-rs reads the encoding from the ELF);
the `rx:` line takes about 110 µs with typed arguments. The TIM3 ISR can
therefore start up to about 110 µs late, once a second. That only matters
for back-to-back frames whose latch gap is under about 130 µs. Such a frame
pair is counted as long + short and dropped, never mis-decoded.

To verify once the stimulus is wired (B1/B2/B3/B5), with a 4-minute soak of
10^5 frames:

```sh
python3 firmware/bench/rbarf_bench.py run --seconds 5          # flash + start
python3 firmware/bench/rbarf_bench.py rtt --no-uart --seconds 260 > soak.log &
sleep 3; python3 firmware/bench/rbarf_bench.py send --pattern all --count 100000 --progress 10000
grep "rx:" soak.log | tail -1
# expect: ok 100000, all failure counters 0, uif 100000, restarted 0,
#         w0 ~18..19, w1 ~36..37 (offset to be recorded), last 0001869f
```

## TODO / unverified on hardware

- First boot: the OBL_LAUNCH self-reprogramming. It also depends on SRAM
  surviving the OBL reset (the loop-guard marker).
- Pin level during the first microseconds. F3 floats from reset until
  `board::led_ball_select()` drives PA0 HIGH, which happens right after
  `embassy_stm32::init`.
- The `out-spi` MOSI idle level.
- The receiver with a real input signal: every bench check B1-B12 of
  `docs/INPUT_CAPTURE_OPTIONS.md` §6. Verified so far: the register setup
  (read back over SWD), and the floating input over 80 s (line reads low:
  0 UIF, DMA index fixed, anim tick 10 000 ± 79 µs, no panic, one `rx:` line
  per second, 0 webcam glitches in 45 s with the demo cycling).
- HSI48 on this board runs 0.40 % fast (both time drivers agree, measured
  against host time over UART). Every timing here, embassy-time included,
  inherits this; HSITRIM is not used.
- The final gamma curve. The LUT is the v0.1 γ2.2 placeholder.
