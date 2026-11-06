#!/usr/bin/env python3
"""Flash + verify the RBARF STM8S001J3 using the RP2040 test probe bench.

Bench wiring (see ../docs/PICOTOOL.md):
  Pico GPIO28 -> low-side MOSFET gate: 1 = target power ON, 0 = OFF
  Pico GPIO29 -> WS2812 test signal into STM8 pin 7 (unused here)
  Pico GPIO1  <- STM8 pin 8 (PD5/UART1_TX, shared with PD1/SWIM), 9600 8N1
  ST-LINK/V2 SWIM -> STM8 pin 8 through 470R

STM8 pin 8 is shared between SWIM and UART1_TX, and the firmware keeps it
quiet for the first 5 s after power-on. Flashing therefore power-cycles the
target through the probe and launches stm8flash inside that window.

Usage:
  flash.py                  flash build/hello.ihx, then power-cycle + verify UART
  flash.py --ihx F          flash a specific image
  flash.py flash-only       flash without the UART verification pass
  flash.py listen [SECS]    power-cycle and dump UART output only (no flashing)
  flash.py power on|off     manual target power control
"""

import argparse
import glob
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port, stm8flash        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
from testprobe import TestProbe  # noqa: E402

PIN_POWER = 28          # low-side MOSFET gate switching target power
POWER_ON_LEVEL = 1      # gate high = target ON (bench-verified 2026-09-05)
PIN_UART_RX = 1         # Pico UART0 RX  <- STM8 pin 8
PIN_UART_TX = 0         # UART0 TX pair for pin 1; unconnected on the bench
BAUD = 9600

POWER_OFF_SECS = 2.0    # let the target rails drain between cycles
SWIM_SETTLE_SECS = 0.3  # target power-up before stm8flash starts
FLASH_ATTEMPTS = 3
# resolved lazily so `flash.py --help` works without the tool installed;
# stm8flash() reports "not installed / not configured" instead of a traceback
STM8FLASH_ARGS = ["-c", "stlinkv2", "-p", "stm8s001j3"]


def stm8flash_cmd():
    return [stm8flash()] + STM8FLASH_ARGS


def default_port() -> str:
    return probe_port()


def power(probe: TestProbe, on: bool) -> None:
    probe.gpio_write(PIN_POWER, POWER_ON_LEVEL if on else 1 - POWER_ON_LEVEL)


def power_cycle(probe: TestProbe) -> float:
    """Power off, drain, power on. Returns the power-on timestamp."""
    power(probe, False)
    time.sleep(POWER_OFF_SECS)
    power(probe, True)
    return time.monotonic()


def run_stm8flash(probe: TestProbe, ihx: str) -> None:
    """Power-cycle and flash inside the 5 s SWIM window, with retries."""
    for attempt in range(1, FLASH_ATTEMPTS + 1):
        print(f"[flash] attempt {attempt}/{FLASH_ATTEMPTS}: power-cycling target")
        power_cycle(probe)
        time.sleep(SWIM_SETTLE_SECS)
        cmd = stm8flash_cmd() + ["-w", ihx]
        print(f"[flash] {' '.join(cmd)}")
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
        except subprocess.TimeoutExpired:
            print("[flash] stm8flash timed out")
            continue
        out = (res.stdout + res.stderr).strip()
        if out:
            print("\n".join(f"[stm8flash] {l}" for l in out.splitlines()))
        if res.returncode == 0:
            print("[flash] OK")
            return
        print(f"[flash] failed (rc={res.returncode})")
    raise SystemExit("[flash] giving up: stm8flash failed on every attempt")


def listen(probe: TestProbe, secs: float) -> bytes:
    """Power-cycle the target and capture UART output for `secs` seconds."""
    chunks = []  # (t_monotonic, bytes)
    probe.on_uart_rx = lambda data: chunks.append((time.monotonic(), data))
    probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)
    probe.uart_read()          # drain anything stale
    chunks.clear()

    print(f"[uart] power-cycling target, listening {secs:.0f}s at {BAUD} baud")
    t_on = power_cycle(probe)

    # Power-transition noise on the shared pin can look like a break;
    # discard whatever arrives in the first 0.5 s (real firmware output
    # starts only after the 5 s quiet window).
    time.sleep(0.5)
    probe.uart_read()
    chunks.clear()

    end = t_on + secs
    while time.monotonic() < end:
        time.sleep(0.1)
    probe.on_uart_rx = None

    data = b"".join(c for _, c in chunks)
    if chunks:
        t_first = chunks[0][0] - t_on
        print(f"[uart] first byte {t_first:.2f}s after power-on, "
              f"{len(data)} bytes total")
        if t_first < 4.5:
            print("[uart] WARNING: output before 4.5s — the 5s SWIM quiet "
                  "window looks violated")
    else:
        print("[uart] no data received")
    text = data.decode("ascii", errors="replace")
    print("[uart] --- captured output ---")
    print(text if text else "(nothing)")
    print("[uart] ------------------------")
    return data


def verify(probe: TestProbe, secs: float) -> None:
    data = listen(probe, secs)
    if b"hello" in data:
        print("[verify] PASS: hello-world output received")
    else:
        raise SystemExit("[verify] FAIL: expected 'hello' in UART output")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", default=default_port(), help="probe serial port")
    ap.add_argument("--ihx", default="build/hello.ihx", help="image to flash")
    ap.add_argument("--listen-secs", type=float, default=12.0,
                    help="UART capture window after power-on")
    ap.add_argument("mode", nargs="*", default=[],
                    help="[flash-only | listen [SECS] | power on|off]")
    args = ap.parse_args()

    with TestProbe(args.port) as probe:
        print(f"[probe] {probe.ident()} on {args.port}")

        if args.mode and args.mode[0] == "power":
            if len(args.mode) != 2 or args.mode[1] not in ("on", "off"):
                raise SystemExit("usage: flash.py power on|off")
            power(probe, args.mode[1] == "on")
            print(f"[power] target power {args.mode[1]}")
        elif args.mode and args.mode[0] == "listen":
            secs = float(args.mode[1]) if len(args.mode) > 1 else args.listen_secs
            listen(probe, secs)
        elif args.mode and args.mode[0] == "flash-only":
            run_stm8flash(probe, args.ihx)
        elif not args.mode:
            run_stm8flash(probe, args.ihx)
            verify(probe, args.listen_secs)
        else:
            raise SystemExit(f"unknown mode: {' '.join(args.mode)}")


if __name__ == "__main__":
    main()
