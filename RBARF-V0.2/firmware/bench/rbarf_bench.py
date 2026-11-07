#!/usr/bin/env python3
"""RBARF v0.2 bench driver: DUT power via the RP2040 test probe, flashing and
RTT logs via probe-rs over the ST-LINK (SWD only, no NRST on this board).

Bench wiring (see firmware/README.md and hardware/PINOUT.md):
  Pico GPIO28 -> NMOS gate switching DUT power      (1 = ON)
  Pico GPIO3  -> WS2812 stimulus into the board's LED_IN (J2.2)
  Pico GPIO1  <- board TP3 (USART1_TX, PC14)        UART0 RX, 115200 8N1
  ST-LINK/V2  -> TP1 SWDIO, TP2 SWCLK, GND

Why the power cycle after flashing: a virgin STM32C0 boots the ST system
bootloader while its flash is empty (EMPTY flag), and the flag is only
re-evaluated at power-on / option-byte load. The firmware's first boot may
also reprogram NRST_MODE (ball F3 = LED output) and reset itself once.

  python3 firmware/bench/rbarf_bench.py power on|off|cycle
  python3 firmware/bench/rbarf_bench.py info            # SWD attach check
  python3 firmware/bench/rbarf_bench.py optr            # decode FLASH_OPTR
  python3 firmware/bench/rbarf_bench.py reset           # debugger reset, core runs
  python3 firmware/bench/rbarf_bench.py flash [--elf F] # download + power cycle
  python3 firmware/bench/rbarf_bench.py rtt [--seconds 20]
  python3 firmware/bench/rbarf_bench.py run [--seconds 20] [--no-build]
  python3 firmware/bench/rbarf_bench.py rtt --no-uart --seconds 60 &   # while sending
  python3 firmware/bench/rbarf_bench.py send --preset blue --count 1
  python3 firmware/bench/rbarf_bench.py send --pattern all --count 20000 --interval 0
  python3 firmware/bench/rbarf_bench.py send --hex 0011..(48 bytes) --dry-run

`send` builds v2.3 frames (FF AA 65 + 48 data + CRC16-CCITT-FALSE x3 +
9A 00 FF, docs/PROTOCOL.md) with the encoder in RBARF-V0.1/firmware/bench/crc.py and
streams them into LED_IN from Pico GPIO3. Only one process can own the Pico
serial port: run `rtt` with --no-uart alongside it.

Environment: RBARF_PICOTOOL_HOST (default ~/Projects/picotool/host),
RBARF_PROBE_PORT (default: /dev/serial/by-id/usb-Raspberry_Pi_Pico_*, else
/dev/ttyACM0).
"""

import argparse
import glob
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW_DIR = HERE.parent
REPO = FW_DIR.parent

CHIP = "STM32C011D6"
DEFAULT_ELF = FW_DIR / "target" / "thumbv6m-none-eabi" / "release" / "rbarf-fw"

POWER_PIN = 28  # Pico GPIO -> DUT power NMOS gate, 1 = ON
WS_PIN = 3  # Pico GPIO -> LED_IN (WS2812 stimulus)
UART_TX_PIN, UART_RX_PIN, UART_BAUD = 0, 1, 115_200  # Pico UART0; RX <- board TP3

# v2.3 frame encoder: reuse the reference implementation of the v0.1 bench
# (RBARF-V0.1/firmware/bench/crc.py, stdlib only; patterns.py holds the 16-byte test set).
sys.path.insert(0, str(REPO.parent / "RBARF-V0.1" / "firmware" / "bench"))
from crc import build_payload_v23, crc16_ccitt_false  # noqa: E402
from patterns import HEADER_V23, PATTERNS, TRAILER_V23, VAL_PATTERNS, frame_v23  # noqa: E402

FLASH_OPTR = 0x4002_2020
NRST_MODE_NAMES = {0: "reserved", 1: "reset input only", 2: "PF2 GPIO", 3: "bidirectional reset (factory)"}


# ---------------------------------------------------------------- probe ----
def _picotool_host() -> str:
    p = os.environ.get("RBARF_PICOTOOL_HOST", str(Path.home() / "Projects/picotool/host"))
    if not os.path.isfile(os.path.join(p, "testprobe", "__init__.py")):
        sys.exit(f"[bench] picotool host library not found at {p!r}; set RBARF_PICOTOOL_HOST")
    return p


def _probe_port() -> str:
    env = os.environ.get("RBARF_PROBE_PORT")
    if env:
        return env
    hits = sorted(glob.glob("/dev/serial/by-id/usb-Raspberry_Pi_Pico_*"))
    if hits:
        return hits[0]
    if os.path.exists("/dev/ttyACM0"):
        return "/dev/ttyACM0"
    sys.exit("[bench] no Pico probe serial port found (is cdc_acm loaded? rebooted after a kernel upgrade?)")


class Probe:
    def __init__(self):
        sys.path.insert(0, _picotool_host())
        from testprobe import TestProbe  # noqa: E402

        self._p = TestProbe(_probe_port())

    def __enter__(self):
        self._p.__enter__()
        return self

    def __exit__(self, *a):
        return self._p.__exit__(*a)

    def power(self, on: bool):
        self._p.gpio_config(POWER_PIN, "O")
        self._p.gpio_write(POWER_PIN, 1 if on else 0)

    def power_state(self) -> int:
        return self._p.gpio_read(POWER_PIN)

    def ws2812_send(self, data: bytes):
        self._p.ws2812_config(WS_PIN)
        self._p.ws2812_write(data)

    def ws2812_frames(self, frames, gap_us: int = 1, per_batch: int = 32):
        """Sends each frame as its own WS2812 burst. A WW followed by a
        non-WW command latches (FIFO drain + 310 us low) on the Pico, so the
        line idles >= 310 us + gap_us between frames; consecutive WWs would
        be glued into one burst. 64 commands per batch -> 32 frames."""
        self._p.ws2812_config(WS_PIN)
        frames = list(frames)
        for k in range(0, len(frames), per_batch):
            b = self._p.batch()
            for f in frames[k:k + per_batch]:
                b.ws2812_write(f)
                b.delay_us(max(1, gap_us))
            b.run()
            if b.error is not None:
                raise SystemExit(f"[bench] probe error: {b.error}")

    def uart_start(self):
        self._p.uart_config(UART_TX_PIN, UART_RX_PIN, UART_BAUD)
        self._p.uart_read(timeout=0)  # drop anything stale

    def uart_poll(self) -> bytes:
        return self._p.uart_read(timeout=0.05)


def power(state: str, off_time: float = 1.0):
    with Probe() as pr:
        if state == "on":
            pr.power(True)
        elif state == "off":
            pr.power(False)
        elif state == "cycle":
            pr.power(False)
            time.sleep(off_time)
            pr.power(True)
        else:
            raise SystemExit(f"bad power state {state!r}")
        time.sleep(0.3)
        print(f"[bench] DUT power GPIO{POWER_PIN} = {pr.power_state()} (1 = ON)")


# ------------------------------------------------------------- probe-rs ----
def _run(cmd, timeout=120, check=True, capture=False):
    print("[bench] $", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, timeout=timeout, text=True, capture_output=capture)
    if check and r.returncode != 0:
        if capture:
            sys.stderr.write(r.stdout or "")
            sys.stderr.write(r.stderr or "")
        raise SystemExit(f"[bench] command failed with exit code {r.returncode}")
    return r


DBGMCU_IDCODE = 0x4001_5800


def info():
    """SWD health check. probe-rs cannot auto-identify the C011, so a bare
    `probe-rs info` always ends with "could not automatically be determined";
    the decisive test is a named-chip read of DBGMCU_IDCODE (0x443 = C011)."""
    r = _run(["probe-rs", "info", "--protocol", "swd"], check=False, capture=True)
    out = (r.stdout or "") + (r.stderr or "")
    if "JtagGetIdcodeError" in out:
        print(out)
        print("[bench] no SWD response: check SWDIO (TP1) / SWCLK (TP2) / GND to the ST-LINK and DUT 3.3 V")
        return 1
    print("[bench] SWD debug port answered (probe-rs cannot auto-identify the C011; that is expected)")
    r = _run(["probe-rs", "read", "--chip", CHIP, "--protocol", "swd", "b32", f"{DBGMCU_IDCODE:#x}", "1"],
             check=False, capture=True)
    out = (r.stdout or "").strip()
    try:
        val = int(out.split()[-1], 16)
    except (ValueError, IndexError):
        print(out, (r.stderr or "").strip())
        print("[bench] SWD answered but the named-chip read failed")
        return 1
    print(f"DBGMCU_IDCODE = {val:#010x}  dev_id = {val & 0xFFF:#05x} ({'STM32C011/C031' if (val & 0xFFF) == 0x443 else 'unexpected'})"
          f"  rev_id = {val >> 16:#06x}")
    return 0 if (val & 0xFFF) == 0x443 else 1


def optr():
    r = _run(["probe-rs", "read", "--chip", CHIP, "b32", f"{FLASH_OPTR:#x}", "1"], check=False, capture=True)
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if r.returncode != 0:
        print(out, err)
        return 1
    try:
        val = int(out.split()[-1], 16)
    except (ValueError, IndexError):
        print(out, err)
        return 1
    mode = (val >> 27) & 3
    print(f"FLASH_OPTR = {val:#010x}  NRST_MODE = {mode:#04b} ({NRST_MODE_NAMES[mode]})"
          f"  RDP = {val & 0xFF:#04x}  NBOOT_SEL = {(val >> 24) & 1}  SECURE_MUXING_EN = {(val >> 23) & 1}")
    return 0


def build():
    _run(["cargo", "build", "--release", "-p", "rbarf-fw"], timeout=900)


def reset():
    """System reset through the debugger; the core runs afterwards. Needed
    after `probe-rs download`, which leaves the core halted."""
    _run(["probe-rs", "reset", "--chip", CHIP, "--protocol", "swd"], timeout=60)


def uart_alive(seconds: float = 3.0) -> bool:
    """True if the board prints anything on its UART within `seconds`."""
    try:
        with Probe() as pr:
            pr.uart_start()
            t_end = time.monotonic() + seconds
            while time.monotonic() < t_end:
                if pr.uart_poll().strip(b"\x00"):
                    return True
    except Exception as e:
        print(f"[bench] uart check unavailable: {e}")
    return False


def flash(elf: Path, cycle: bool = True):
    if not elf.is_file():
        raise SystemExit(f"[bench] ELF not found: {elf} (run with `run`, or `cargo build --release` first)")
    with Probe() as pr:
        if pr.power_state() != 1:
            pr.power(True)
            time.sleep(0.5)
    _run(["probe-rs", "download", "--chip", CHIP, "--protocol", "swd", "--non-interactive", str(elf)], timeout=180)
    # download leaves the core halted: run it.
    reset()
    if cycle:
        # A real power-on clears the virgin-flash EMPTY state and lets the
        # firmware's first-boot option-byte check run from a clean start.
        # 3 s off: the 3.3 V rail can be held up briefly through the SWD /
        # UART pins, so give it time to fall.
        power("cycle", off_time=3.0)
    if uart_alive():
        print("[bench] board is running (UART output seen)")
    else:
        print("[bench] no UART output after flashing; issuing a debugger reset")
        reset()
        print("[bench] board running after reset" if uart_alive() else "[bench] WARNING: still silent on UART")


def _uart_thread(stop, deadline):
    """Prints the board's UART (TP3 -> Pico GPIO1) as `[uart] ...` lines."""
    try:
        with Probe() as pr:
            pr.uart_start()
            buf = b""
            while not stop.is_set() and time.monotonic() < deadline:
                buf += pr.uart_poll()
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    print("[uart]", line.rstrip(b"\r").decode("ascii", "replace"), flush=True)
            if buf:
                print("[uart]", buf.decode("ascii", "replace"), flush=True)
    except Exception as e:  # the probe port is optional for RTT
        print(f"[bench] uart capture unavailable: {e}", flush=True)


def rtt(elf: Path, seconds: float, retries: int = 2, uart: bool = True):
    """Attach for RTT/defmt for `seconds`; re-attach once if the target
    resets underneath us (the first-boot NRST_MODE reprogram does that).
    In parallel, prints the board's UART through the Pico."""
    import threading

    deadline = time.monotonic() + seconds
    stop = threading.Event()
    th = None
    if uart:
        th = threading.Thread(target=_uart_thread, args=(stop, deadline), daemon=True)
        th.start()
    attempt = 0
    while time.monotonic() < deadline and attempt <= retries:
        attempt += 1
        cmd = ["probe-rs", "attach", "--chip", CHIP, "--protocol", "swd", "--no-catch-reset", str(elf)]
        print("[bench] $", " ".join(cmd), flush=True)
        p = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # Watchdog: a silent attach (no RTT lines) must not block readline()
        # past the deadline.
        remaining = max(0.1, deadline - time.monotonic())
        wd = threading.Timer(remaining, lambda: p.poll() is None and p.terminate())
        wd.daemon = True
        wd.start()
        got_output = False
        try:
            while True:
                line = p.stdout.readline()
                if not line:
                    break
                got_output = True
                sys.stdout.write(line)
                sys.stdout.flush()
        finally:
            wd.cancel()
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(5)
                except subprocess.TimeoutExpired:
                    p.kill()
        if not got_output:
            print("[bench] attach produced no output: core halted or RTT block not found; try `rbarf_bench.py reset`", flush=True)
        if time.monotonic() < deadline:
            print(f"[bench] attach ended (exit {p.returncode}); re-attaching in 1 s", flush=True)
            time.sleep(1.0)
    stop.set()
    if th:
        th.join(timeout=2)


# ------------------------------------------------------------ v2.3 send ----
DATA_LEN = 48  # = rbarf_anim::FRAME_LEN


def encode_v23(data: bytes) -> bytes:
    """FF AA 65 + data + (CRC16 HI, LO) x 3 + 9A 00 FF (60 bytes = 20 LEDs)."""
    if len(data) != DATA_LEN:
        raise SystemExit(f"[bench] payload must be {DATA_LEN} bytes, got {len(data)}")
    f = frame_v23(build_payload_v23(bytes(data)))
    assert len(f) == 60 and f[:3] == HEADER_V23 and f[-3:] == TRAILER_V23
    return f


# Demo presets: byte-for-byte copies of firmware/rbarf-fw/src/demo.rs.
_D = 0x20
_RED, _GREEN, _BLUE = (0, _D, 0), (_D, 0, 0), (0, 0, _D)  # GRB triples
_YELLOW, _CYAN, _MAGENTA, _WHITE, _ORANGE = (_D, _D, 0), (_D, 0, _D), (0, _D, _D), (_D, _D, _D), (0x08, _D, 0)


def _demo_frame(base, head=()):
    flags = bytes(head) + bytes(24 - len(head))
    return bytes(c for grb in base for c in grb) + flags


def _spin_gamma():
    f = bytearray(_demo_frame(
        [(0x80, 0, 0), (0x80, 0x40, 0), (0, 0x80, 0), (0, 0x80, 0x40),
         (0, 0, 0x80), (0x40, 0, 0x80), (0x80, 0, 0x80), (0x80, 0x80, 0x80)],
        [0x03, 16, 0x00, 0, 0, 0, 0x01, 0x01, 0x57, 0x62, 0xFF]))
    f[24 + 23] = 1
    return bytes(f)


PRESETS = {
    "static": _demo_frame([_RED, _ORANGE, _YELLOW, _GREEN, _CYAN, _BLUE, _MAGENTA, _WHITE], [0x00]),
    "blink": _demo_frame([_RED] * 8, [0x01, 20, 0x80, 0, 0, _D, _D, _D, _D]),
    "fade": _demo_frame([_GREEN] * 8, [0x02, 40, 0x00, 0, _D, _D]),
    "spin": _demo_frame([_WHITE] * 8, [0x03, 16, 0x00, 0, 0, 0, 0x01, 0x01, 0x57, 0x62, 0xFF]),
    "spin_gamma": _spin_gamma(),
    # Solid colours for the end-to-end check (static mode, all 8 LEDs).
    "blue": _demo_frame([(0, 0, 0x40)] * 8, [0x00]),
    "red": _demo_frame([(0, 0x40, 0)] * 8, [0x00]),
    "green": _demo_frame([(0x40, 0, 0)] * 8, [0x00]),
    "off": _demo_frame([(0, 0, 0)] * 8, [0x00]),
}
assert all(len(p) == DATA_LEN for p in PRESETS.values())


def _prbs(seed: int, n: int) -> bytes:
    """xorshift32, seeded per frame (never 0)."""
    x = (seed * 2654435761 + 1) & 0xFFFFFFFF or 1
    out = bytearray()
    for _ in range(n):
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        out.append(x & 0xFF)
    return bytes(out)


def pattern_payload(kind: str, i: int) -> bytes:
    """Payload number i of a soak pattern. Every kind puts the frame number
    i in bytes 0..4 (big endian) except the raw `all` stress patterns; the
    firmware logs the first 4 data bytes of the last accepted frame."""
    seq = i.to_bytes(4, "big")
    if kind == "counter":
        return seq + bytes((i + k) & 0xFF for k in range(DATA_LEN - 4))
    if kind == "prbs":
        return seq + _prbs(i, DATA_LEN - 4)
    if kind == "all":
        # patterns.py's 16-byte stress set (zeros, ones, aa, runs, ...) tiled
        # to 48 bytes, then counter and PRBS frames, round robin.
        pats = list(PATTERNS.values()) + list(VAL_PATTERNS.values())
        k = i % (len(pats) + 2)
        if k < len(pats):
            return pats[k] * 3
        return pattern_payload("counter" if k == len(pats) else "prbs", i)
    raise SystemExit(f"[bench] unknown pattern {kind!r}")


def send(a) -> int:
    if a.hex is not None:
        data = bytes.fromhex(a.hex.replace(" ", "").replace(":", ""))
        payloads = lambda i: data  # noqa: E731
    elif a.preset is not None:
        payloads = lambda i: PRESETS[a.preset]  # noqa: E731
    else:
        payloads = lambda i: pattern_payload(a.pattern, a.start + i)  # noqa: E731
    if a.dry_run:
        for i in range(min(a.count, 4)):
            d = payloads(i)
            f = encode_v23(d)
            print(f"frame {i}: CRC16 = {crc16_ccitt_false(d):#06x}")
            print("  " + f[:3].hex(" ") + " | " + f[3:51].hex(" ") + " | " + f[51:57].hex(" ") + " | " + f[57:].hex(" "))
        return 0
    gap_us = int(a.interval * 1e6)
    per_batch = 32 if gap_us < 200_000 else 1
    t0 = time.monotonic()
    sent = 0
    with Probe() as pr:
        while sent < a.count:
            n = min(per_batch * 8, a.count - sent)
            pr.ws2812_frames((encode_v23(payloads(sent + k)) for k in range(n)), gap_us=gap_us, per_batch=per_batch)
            sent += n
            if a.progress and sent % a.progress < n:
                dt = time.monotonic() - t0
                print(f"[bench] sent {sent} frames in {dt:.1f} s ({sent / dt:.0f}/s)", flush=True)
    dt = time.monotonic() - t0
    print(f"[bench] sent {sent} frames in {dt:.2f} s ({sent / max(dt, 1e-9):.0f} frames/s)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("power")
    s.add_argument("state", choices=["on", "off", "cycle"])
    s.add_argument("--off-time", type=float, default=1.0)
    sub.add_parser("info")
    sub.add_parser("optr")
    sub.add_parser("reset")
    s = sub.add_parser("flash")
    s.add_argument("--elf", type=Path, default=DEFAULT_ELF)
    s.add_argument("--no-cycle", action="store_true")
    s = sub.add_parser("rtt")
    s.add_argument("--elf", type=Path, default=DEFAULT_ELF)
    s.add_argument("--seconds", type=float, default=20)
    s.add_argument("--no-uart", action="store_true", help="leave the Pico port free (for a parallel `send`)")
    s = sub.add_parser("send", help="send v2.3 frames into LED_IN (Pico GPIO3)")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--hex", help="48-byte payload as hex")
    g.add_argument("--preset", choices=sorted(PRESETS), help="demo.rs frame or a solid colour")
    g.add_argument("--pattern", choices=["counter", "prbs", "all"], default="counter",
                   help="soak payloads; frame number in bytes 0..4 (default)")
    s.add_argument("--count", type=int, default=1)
    s.add_argument("--interval", type=float, default=0.0,
                   help="extra idle seconds between frames, on top of the Pico's 310 us latch")
    s.add_argument("--start", type=int, default=0, help="first frame number for --pattern")
    s.add_argument("--progress", type=int, default=0, metavar="N", help="print progress every N frames")
    s.add_argument("--dry-run", action="store_true", help="print the first frames in hex, do not send")
    s = sub.add_parser("run")
    s.add_argument("--elf", type=Path, default=DEFAULT_ELF)
    s.add_argument("--seconds", type=float, default=20)
    s.add_argument("--no-build", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "power":
        power(a.state, a.off_time)
    elif a.cmd == "info":
        return info()
    elif a.cmd == "optr":
        return optr()
    elif a.cmd == "reset":
        reset()
    elif a.cmd == "flash":
        flash(a.elf, cycle=not a.no_cycle)
    elif a.cmd == "rtt":
        rtt(a.elf, a.seconds, uart=not a.no_uart)
    elif a.cmd == "send":
        return send(a)
    elif a.cmd == "run":
        if not a.no_build:
            os.chdir(FW_DIR)
            build()
        flash(a.elf)
        time.sleep(1.0)
        rtt(a.elf, a.seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
