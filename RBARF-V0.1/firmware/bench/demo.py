#!/usr/bin/env python3
"""RBARF demo reel — 15 animations driven through the test probe.

Sends v2.3 frames (60 B = exactly 20 WS2812 LEDs) to the STM8 on the
probe's WS2812 pin and, for each one, reads the device's decode report
back over UART.  That makes the reel self-verifying: even with no LED
strip attached you can watch every frame being accepted on-chip; attach
a strip to STM8 pin 5 and it becomes a visual demo.

Requires the PRODUCTION firmware on the target (build/rbarf_prod.ihx or
the verbose variant) -- pass --flash to program it first.  With the
capture firmware flashed instead, frames are still sent but the device
reports CAP: dumps rather than decodes.

  python3 bench/demo.py --list            # show the reel
  python3 bench/demo.py --flash           # flash prod firmware, then run
  python3 bench/demo.py --hold 8          # linger on each animation
  python3 bench/demo.py --only comet,rain # pick scenes
  python3 bench/demo.py --loop            # run forever (Ctrl-C to stop)
"""

import argparse
import glob
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent

# Probe host library: overridable so the tree is not tied to one machine.
_PICOTOOL = os.environ.get(
    "RBARF_PICOTOOL_HOST", "/home/alex.lucaci/Projects/picotool/host")
sys.path.insert(0, _PICOTOOL)
try:
    from testprobe import TestProbe
except ImportError:
    sys.exit(f"cannot import testprobe from {_PICOTOOL!r}\n"
             f"set RBARF_PICOTOOL_HOST to your picotool 'host' directory")

sys.path.insert(0, str(_HERE))
from patterns import build_payload_v23, frame_v23  # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600

FRAME_GAP = 0.40        # > the ~180 ms decode blind window, with margin
MAX_TRIES = 6           # attempts to land one frame before moving on
DEFAULT_HOLD = 6.0      # seconds per animation

# ---- protocol: animation modes and flag layout (see ../../docs/ANIMATION_PROTOCOL.md) ----
NONE, BLINK, FADE, SEQ = 0x00, 0x01, 0x02, 0x03

# Feature bits (sequence modes)
F_FADE3 = 0x01          # current LED bright, previous fades out, next fades in
F_FADE2 = 0x02          # current fades in, previous fades out
F_GROUP2 = 0x04         # two consecutive LEDs lit together
F_GROUP4 = 0x08         # four consecutive LEDs lit together

# Preset step orders -- these are HOST-side expansions now (the chip only
# implements modes 0..3); tables from ../../docs/ANIMATION_PROTOCOL.md.
SPIN =      [0, 1, 5, 7, 6, 2]
SPIN_REV =  [2, 6, 7, 5, 1, 0]
RAIN =      [3, 4, 0, 1, 5, 7, 6, 2]
RAIN_REV =  [2, 6, 7, 5, 1, 0, 4, 3]
DRAW =      [0, 1, 2, 3, 4, 5, 6, 7]
DRAW_REV =  [7, 6, 5, 4, 3, 2, 1, 0]
PAUSE = 8               # renders nothing, holds a step


CH_MAX = 0xF0           # see _rgb()


def _rgb(h):
    """Hex colour -> (r, g, b), each channel capped at CH_MAX.

    The cap keeps 0xFF out of the payload.  Long runs of 1-bits are the
    decoder's one weak content class (the merged-1 stress case: adjacent
    1-bits whose separating low falls in a sampling dead zone), and a
    palette full of saturated 0xFF channels turns a demo into a stress
    test.  0xF0 vs 0xFF is a ~6 % brightness difference -- invisible --
    and it breaks 1-runs at every byte boundary.  Purely a palette
    choice in this script; the firmware is unchanged.
    """
    h = h.lstrip("#")
    return tuple(min(CH_MAX, int(h[i:i + 2], 16)) for i in (0, 2, 4))


def build_data(colors, mode=NONE, duration_ms=0, alt=None, mask=0,
               mask_color=None, bg=None, features=0, seq=None, gamma=1):
    """Assemble the 48-byte DATA block: 8 base LEDs (GRB) + 24 flag bytes."""
    d = bytearray(48)
    for i in range(8):
        r, g, b = _rgb(colors[i % len(colors)])
        d[i * 3], d[i * 3 + 1], d[i * 3 + 2] = g, r, b   # wire order is GRB

    F = 24                                   # flags[0] lives at byte 24
    d[F + 0] = mode
    d[F + 1] = min(255, duration_ms // 50)   # duration in 50 ms units
    d[F + 2] = mask                          # bit7 = LED0 .. bit0 = LED7
    if mode in (BLINK, FADE):
        if alt:
            r, g, b = _rgb(alt)
            d[F + 3], d[F + 4], d[F + 5] = g, r, b
        if mask_color:
            r, g, b = _rgb(mask_color)
            d[F + 6], d[F + 7], d[F + 8] = g, r, b
    elif mode == SEQ:
        if bg:
            r, g, b = _rgb(bg)
            d[F + 3], d[F + 4], d[F + 5] = g, r, b
        d[F + 6] = features
        nib = list(seq or []) + [0xF]        # 9..15 terminates the sequence
        if len(nib) % 2:
            nib.append(0xF)
        for j in range(0, min(len(nib), 32), 2):
            d[F + 7 + j // 2] = (nib[j] << 4) | nib[j + 1]
    d[F + 23] = gamma
    return bytes(d)


# --------------------------------------------------------------- the reel
RAINBOW = ["FF0033", "FF6A00", "FFD100", "5CFF3D",
           "00E5CC", "0091FF", "6B4DFF", "FF3DC4"]
SUNSET = ["FFD08A", "FFA45C", "FF7A45", "FF4E50",
          "E63462", "A02A5B", "5C2A5B", "2B1B4A"]
DEEPSEA = ["0A1E4A", "12356E", "1B5299", "2A79B8",
           "3FA8C9", "63D0D8", "9BE8E0", "D6F7F0"]
EMBER = ["2B0A00", "5C1A00", "8A2E00", "C24E00",
         "FF7A1A", "FFA64D", "FFD199", "FFF0DB"]

REEL = [
    ("rainbow", "eight hues, held still — the base-colour path",
     build_data(RAINBOW)),

    ("sunset", "warm gradient, gamma-corrected",
     build_data(SUNSET)),

    ("deepsea", "cool gradient from abyss to foam",
     build_data(DEEPSEA)),

    ("police", "red/blue alternating strobe (blink to black)",
     build_data(["FF0018", "0022FF"] * 4, mode=BLINK,
                duration_ms=400, alt="000000")),

    ("breathe", "slow amber breathing (fade to near-dark)",
     build_data(["FFB000"], mode=FADE, duration_ms=3000, alt="140700")),

    ("duotone", "cyan to magenta cross-fade",
     build_data(["00FFD0"], mode=FADE, duration_ms=2000, alt="FF00A8")),

    ("halfmast", "four LEDs breathe, four hold steady (LED mask)",
     build_data(["00E5FF"], mode=FADE, duration_ms=1800,
                alt="000814", mask=0xAA, mask_color="FF2D00")),

    ("spin", "cyan runner with a 3-LED comet fade",
     build_data(["00F0FF"], mode=SEQ, duration_ms=900, bg="001018",
                features=F_FADE3, seq=SPIN)),

    ("spin_rev", "gold runner the other way round",
     build_data(["FFC400"], mode=SEQ, duration_ms=900, bg="140800",
                features=F_FADE3, seq=SPIN_REV)),

    ("rain", "pale droplets falling on deep blue",
     build_data(["D8F0FF"], mode=SEQ, duration_ms=1200, bg="000A1E",
                features=F_FADE2, seq=RAIN)),

    # 5CD07C measured 11/12 accepted on the bench where 39FF6A managed
    # 5/12 (R8, chase exhausted) -- same palette-choice reasoning as
    # `bounce`; the firmware is not involved.
    ("matrix", "green cascade, reversed rain order",
     build_data(["5CD07C"], mode=SEQ, duration_ms=1000, bg="08160C",
                features=F_FADE3, seq=RAIN_REV)),

    ("draw", "orange progressive fill",
     build_data(["FF6A00"], mode=SEQ, duration_ms=1400, bg="100400",
                seq=DRAW)),

    ("undraw", "violet unwinding, with a 2-LED fade tail",
     build_data(["A855FF"], mode=SEQ, duration_ms=1400, bg="0A0018",
                features=F_FADE2, seq=DRAW_REV)),

    # Coral rather than magenta: the FF2D95 payload measured 2/8 latched
    # on the bench where FF5A72 measures 6/8 -- 0x95/0x2D interleave
    # isolated single bits, which is the decoder's knife-edge content
    # class.  Palette choice only; see _rgb() and docs/ARCHITECTURE.md.
    ("bounce", "coral head sweeping back and forth",
     build_data(["FF5A72"], mode=SEQ, duration_ms=1800, bg="1A0812",
                features=F_FADE3,
                seq=[0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1])),

    ("twinsweep", "mint pairs marching (2-LED grouping + pauses)",
     build_data(["00FFA3"], mode=SEQ, duration_ms=900, bg="001410",
                features=F_GROUP2,
                seq=[0, PAUSE, 2, PAUSE, 4, PAUSE, 6, PAUSE])),

    ("quadwave", "ember quartets, four LEDs lit at a time",
     build_data(EMBER, mode=SEQ, duration_ms=1100, bg="0A0200",
                features=F_GROUP4, seq=[0, 2, 4, 6])),
]


class Lines:
    """Collect UART bytes into lines."""

    def __init__(self):
        self.buf = bytearray()
        self.lines = []
        self.cond = threading.Condition()

    def feed(self, data):
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[:nl + 1]
                if line:
                    self.lines.append(line.decode("ascii", errors="replace"))
            self.cond.notify_all()

    def take(self, prefixes, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, ln in enumerate(self.lines):
                    if any(ln.startswith(p) for p in prefixes):
                        del self.lines[:i + 1]
                        return ln
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                self.cond.wait(left)

    def clear(self):
        # BOTH buffers.  Dropping only `lines` leaves a half-received
        # line's bytes in `buf`, which then prefix the NEXT line -- the
        # report stops starting with "D:" and a perfectly good decode is
        # scored as "no report".  That bug alone accounted for ~28 % of
        # apparent misses when this script switched scenes.
        with self.cond:
            self.lines.clear()
            self.buf.clear()


def probe_port():
    hits = sorted(glob.glob("/dev/serial/by-id/usb-Raspberry_Pi_Pico_*"))
    return hits[0] if hits else "/dev/ttyACM0"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=None)
    ap.add_argument("--hold", type=float, default=DEFAULT_HOLD,
                    help=f"seconds per animation (default {DEFAULT_HOLD})")
    ap.add_argument("--only", default=None,
                    help="comma-separated scene names")
    ap.add_argument("--loop", action="store_true", help="repeat forever")
    ap.add_argument("--list", action="store_true", help="list scenes, exit")
    ap.add_argument("--flash", action="store_true",
                    help="flash build/rbarf_prod.ihx before running")
    ap.add_argument("--no-verify", action="store_true",
                    help="do not wait for the device's decode report")
    args = ap.parse_args()

    reel = REEL
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        reel = [s for s in REEL if s[0] in want]
        missing = want - {s[0] for s in reel}
        if missing:
            sys.exit(f"unknown scene(s): {', '.join(sorted(missing))}")

    if args.list:
        print(f"{len(REEL)} scenes:")
        for name, desc, data in REEL:
            print(f"  {name:11s} {desc}")
        return

    if args.flash:
        ihx = _PROJ / "build" / "rbarf_prod.ihx"
        if not ihx.exists():
            sys.exit(f"{ihx} not built — run: make rbarf-prod")
        print(f"[demo] flashing {ihx.name}")
        r = subprocess.run([sys.executable, str(_PROJ / "flash.py"),
                            "--ihx", str(ihx), "flash-only"],
                           cwd=str(_PROJ), timeout=180)
        if r.returncode != 0:
            sys.exit("[demo] flash failed")

    port = args.port or probe_port()
    lines = Lines()

    with TestProbe(port) as probe:
        print(f"[demo] probe {probe.ident()} on {port}")
        probe.on_uart_rx = lines.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        print("[demo] power-cycling target (5 s SWIM window)...")
        probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
        time.sleep(2.0)
        probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
        banner = lines.take(("RBARF",), 15.0)
        print(f"[demo] target says: {banner or '(no banner)'}")
        if banner and "CAP" in banner:
            print("[demo] NOTE: capture firmware is flashed, not the "
                  "production decoder — frames will be captured, not "
                  "rendered. Re-run with --flash for the demo proper.")
        time.sleep(0.5)
        lines.clear()

        print(f"[demo] {len(reel)} scenes, {args.hold:.0f}s each — "
              f"watch pin 5\n")
        first = True
        while first or args.loop:
            first = False
            for name, desc, data in reel:
                fr = frame_v23(build_payload_v23(data))
                assert len(fr) == 60, len(fr)
                print(f"  {name:11s} {desc}")
                # A frame carries complete state and the device latches
                # it, so land ONE frame and let the chip animate -- which
                # is also how the real host behaves (rare frames, single
                # transmission, no repeats).
                t_scene = time.monotonic()
                landed, tries = False, 0
                while tries < MAX_TRIES and not landed:
                    lines.clear()
                    probe.ws2812_write(fr)
                    tries += 1
                    if args.no_verify:
                        landed = True
                        break
                    rep = lines.take(("D:", "DEC", "CAP:"), 1.2)
                    if rep and rep.startswith(("D:", "DEC")):
                        parts = rep.split(":")
                        if len(parts) > 1 and parts[1].startswith(("O", "C")):
                            landed = True
                            break
                    time.sleep(FRAME_GAP)
                if args.no_verify:
                    print("              sent (verification off)")
                elif landed:
                    how = "first try" if tries == 1 else f"{tries} tries"
                    print(f"              latched, {how} — animating")
                else:
                    print(f"              NOT latched after {tries} tries "
                          f"(previous scene still showing)")
                left = args.hold - (time.monotonic() - t_scene)
                if left > 0:
                    time.sleep(left)
        print("\n[demo] done")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[demo] stopped")
