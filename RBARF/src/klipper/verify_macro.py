#!/usr/bin/env python3
"""Host-side proof for klipper/rbarf.cfg - no Klipper, no hardware.

What this does
--------------
1. Reads ``rbarf.cfg`` with **the same parser Klipper uses**
   (``RawConfigParser(strict=False, inline_comment_prefixes=(';', '#'))``),
   so comment stripping, line stripping and multi-line value joining are
   byte-identical to what klippy would hand to Jinja.
2. Renders the macro bodies with **the real jinja2 library** in
   Klipper's exact environment: delimiters ``{%`` ``%}`` / ``{`` ``}``,
   the ``jinja2.ext.do`` extension, and a context holding ``params``
   (all values are strings, as Klipper's shlex parse produces),
   ``rawparams`` and the ``action_*`` helpers.  Nothing is added that
   Klipper does not provide.
3. Executes the rendered G-code through a minimal dispatcher that parses
   extended commands the way ``gcode.py`` does (shlex, keys uppercased),
   recurses into ``SET_LED_INTEGER`` (itself rendered from the cfg), and
   ends at ``SET_LED``.
4. Emulates ``neopixel.py``: ``int(value * 255. + .5)`` per channel,
   emitted in the configured ``color_order``, giving the exact 60-byte
   stream that would leave the MCU pin (v2.3: the frame IS 60 bytes =
   exactly 20 LEDs; there is no pad byte).
5. Asserts that stream against ground truth built from
   ``bench/crc.py`` + ``bench/patterns.py`` and from ../../docs/PROTOCOL.md read
   directly, for: static, blink, fade+mask, an explicit sequence with a
   pause and a terminator, every preset expansion, gamma on/off,
   RBARF_OFF, carry-forward COLORS, and randomized frames - plus the
   3-byte header, the 3-byte trailer, the tripled 16-bit check block
   (HI,LO per copy) and the TRANSMIT pattern on every single case.
6. Proves the two arithmetic identities the macro's table-free CRC16
   depends on, since Klipper's Jinja has no bitwise operators:
   ``x ^ 0x1021 == x + 4129 - 8192*((x//4096)%2) - 64*((x//32)%2)`` for
   every even 16-bit ``x``, and the whole bit-serial loop against
   ``crc16_ccitt_false`` / ``crc16_ccitt_false_bitwise``.
7. Checks the input validation raises, and lints the cfg for constructs
   Klipper's Jinja cannot take (0x literals, bitwise operators, ``{{``,
   ``{#``) - and for any CRC8 leftover, which has no place in v2.3.

Run:  python3 klipper/verify_macro.py
"""

import io
import configparser
import os
import random
import re
import shlex
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(os.path.dirname(HERE), "bench")
sys.path.insert(0, BENCH)

try:
    import jinja2
except ImportError:                                          # pragma: no cover
    sys.exit("verify_macro.py needs jinja2:  pip install jinja2")

from crc import (crc16_ccitt_false, crc16_ccitt_false_bitwise,  # noqa: E402
                 check_block_v23, build_payload_v23,
                 verify_intact_v23, verify_payload_v23,
                 reference_bytes_v23, reference_candidates_v23)
from patterns import (HEADER_V23 as HEADER,                     # noqa: E402
                      TRAILER_V23 as TRAILER,
                      frame_v23 as wrap_frame)

CFG = os.path.join(HERE, "rbarf.cfg")

CHAIN_COUNT = 20
COLOR_ORDER = "GRB"

# v2.3 frame geometry: 3 + 48 + 6 + 3 = 60, which tiles the 20-LED chain
# exactly.  The marker trim (8 -> 6 bytes) and the check-block growth
# (4 -> 6 bytes) are one change; together they hold the frame at 60.
HDR_LEN = 3
DATA_LEN = 48
CHK_LEN = 6                           # (C16_HI, C16_LO) x 3
TRL_LEN = 3
FRAME_LEN = HDR_LEN + DATA_LEN + CHK_LEN + TRL_LEN            # 60
STREAM_LEN = CHAIN_COUNT * 3          # 60 -- EQUAL to the frame, no pad
assert FRAME_LEN == STREAM_LEN == 60

# Offsets into the wire stream, so no case hard-codes a slice.
O_DATA = HDR_LEN                      # 3
O_CHK = O_DATA + DATA_LEN             # 51
O_TRL = O_CHK + CHK_LEN               # 57


# =========================================================================
# Klipper emulation
# =========================================================================

class CommandError(Exception):
    """Stands in for printer.command_error (what action_raise_error raises)."""


class MiniKlipper:
    """Just enough klippy to render a gcode_macro and catch its SET_LEDs."""

    def __init__(self, cfg_path):
        text = open(cfg_path).read()
        # EXACTLY what configfile.py::_build_config_wrapper does.
        fileconfig = configparser.RawConfigParser(
            strict=False, inline_comment_prefixes=(';', '#'))
        fileconfig.read_file(io.StringIO(text), cfg_path)
        self.fileconfig = fileconfig

        # EXACTLY what gcode_macro.py::PrinterGCodeMacro does.
        self.env = jinja2.Environment('{%', '%}', '{', '}',
                                      extensions=['jinja2.ext.do'])

        self.macros = {}
        for section in fileconfig.sections():
            if section.startswith("gcode_macro "):
                name = section.split(" ", 1)[1].strip().upper()
                self.macros[name] = self.env.from_string(
                    fileconfig.get(section, "gcode"))

        self.responses = []
        self.led_state = [(0., 0., 0., 0.)] * CHAIN_COUNT
        self.transmits = []           # (index, transmit, sync) in call order
        self.streams = []             # one 60-byte stream per TRANSMIT=1
        self.led_names = []           # the LED= target of every SET_LED
        self.depth = 0

    # ---- action_* helpers, with Klipper's return values ----------------
    def _action_respond_info(self, msg):
        self.responses.append(msg)
        return ""

    def _action_raise_error(self, msg):
        raise CommandError(msg)

    def _action_emergency_stop(self, msg="action_emergency_stop"):
        raise CommandError("emergency stop: %s" % msg)

    def _action_call_remote_method(self, method, **kwargs):
        return ""

    def context(self, params, rawparams):
        return {
            'params': params,
            'rawparams': rawparams,
            'printer': {},
            'action_respond_info': self._action_respond_info,
            'action_raise_error': self._action_raise_error,
            'action_emergency_stop': self._action_emergency_stop,
            'action_call_remote_method': self._action_call_remote_method,
        }

    # ---- gcode.py's extended-parameter parse ---------------------------
    @staticmethod
    def parse_line(line):
        """-> (COMMAND, {PARAM: 'value'}, rawparams) or (None, ...)."""
        line = line.strip()
        cpos = line.find(';')
        if cpos >= 0:
            line = line[:cpos].strip()
        if not line:
            return None, {}, ""
        parts = line.split(None, 1)
        cmd = parts[0].upper()
        rawparams = parts[1] if len(parts) > 1 else ""
        params = {}
        for tok in shlex.split(rawparams):
            if '=' not in tok:
                raise CommandError("malformed parameter %r" % tok)
            k, v = tok.split('=', 1)
            params[k.upper()] = v
        return cmd, params, rawparams

    # ---- run one gcode line -------------------------------------------
    def run_line(self, line):
        cmd, params, rawparams = self.parse_line(line)
        if cmd is None:
            return
        if cmd in self.macros:
            self.depth += 1
            if self.depth > 8:
                raise CommandError("macro recursion too deep")
            script = self.macros[cmd].render(self.context(params, rawparams))
            for sub in str(script).split('\n'):
                self.run_line(sub)
            self.depth -= 1
            return
        if cmd == "SET_LED":
            self.cmd_set_led(params)
            return
        raise CommandError("Unknown command: %r (from line %r)" % (cmd, line))

    # ---- led.py::cmd_SET_LED + neopixel.py::update_color_data ----------
    def cmd_set_led(self, params):
        def getf(name):
            v = float(params.get(name, 0.))
            if not 0. <= v <= 1.:
                raise CommandError("SET_LED %s=%s out of range 0..1"
                                   % (name, params.get(name)))
            return v
        index = int(params["INDEX"])
        if not 1 <= index <= CHAIN_COUNT:
            raise CommandError("SET_LED INDEX=%d outside chain" % index)
        transmit = int(params.get("TRANSMIT", 1))
        sync = int(params.get("SYNC", 1))
        self.led_state[index - 1] = (getf("RED"), getf("GREEN"),
                                     getf("BLUE"), getf("WHITE"))
        self.led_names.append(params["LED"])
        self.transmits.append((index, transmit, sync))
        if transmit:
            self.streams.append(self.render_chain())

    def render_chain(self):
        """neopixel.py: int(v * 255. + .5), laid out in color_order."""
        order = [("RGBW".index(c)) for c in COLOR_ORDER]
        out = bytearray()
        for color in self.led_state:
            for ci in order:
                out.append(int(color[ci] * 255. + .5))
        return bytes(out)

    # ---- one RBARF command -> the bytes on the wire --------------------
    def send(self, line):
        self.responses = []
        self.transmits = []
        self.streams = []
        self.led_names = []
        self.depth = 0
        self.run_line(line)
        return self.streams


# =========================================================================
# Ground truth, straight from ../../docs/PROTOCOL.md
# =========================================================================

MODE_STATIC, MODE_BLINK, MODE_FADE, MODE_SEQ = 0x00, 0x01, 0x02, 0x03

# Byte-exact nibble tables for the six preset modes, copied from
# ../app/anim.c ("the nibble sequences the host must send as mode 0x03")
# and cross-checked against ../../docs/ANIMATION_PROTOCOL.md's "Sequence auto-fill".
PRESET_TABLES = {
    "SPIN":     ([0, 1, 5, 7, 6, 2],          bytes([0x01, 0x57, 0x62, 0xFF])),
    "SPIN_REV": ([2, 6, 7, 5, 1, 0],          bytes([0x26, 0x75, 0x10, 0xFF])),
    "RAIN":     ([3, 4, 0, 1, 5, 7, 6, 2],
                 bytes([0x34, 0x01, 0x57, 0x62, 0xFF])),
    "RAIN_REV": ([2, 6, 7, 5, 1, 0, 4, 3],
                 bytes([0x26, 0x75, 0x10, 0x43, 0xFF])),
    "DRAW":     ([0, 1, 2, 3, 4, 5, 6, 7],
                 bytes([0x01, 0x23, 0x45, 0x67, 0xFF])),
    "DRAW_REV": ([7, 6, 5, 4, 3, 2, 1, 0],
                 bytes([0x76, 0x54, 0x32, 0x10, 0xFF])),
}


def pack_seq(steps):
    """Nibble-pack a step list, high nibble first, terminator 0xF."""
    nib = list(steps)
    if nib:
        nib.append(0xF)
        if len(nib) % 2:
            nib.append(0xF)
    return bytes((nib[i] << 4) | nib[i + 1] for i in range(0, len(nib), 2))


def mask_byte_from_indexes(idxs):
    """bit 7 = LED 0 ... bit 0 = LED 7."""
    b = 0
    for i in idxs:
        b |= 0x80 >> i
    return b


def build_data(base, mode, dur_units=0, mask=0, alt=(0, 0, 0),
               maskc=(0, 0, 0), bg=(0, 0, 0), features=0, steps=(),
               gamma=0):
    """The 48 DATA bytes: 8 base LEDs in GRB + 24 flag bytes."""
    data = bytearray()
    for (r, g, b) in base:
        data += bytes((g, r, b))                        # GRB on the wire
    f = [0] * 24
    f[0] = mode
    f[1] = dur_units
    f[2] = mask
    if mode in (MODE_BLINK, MODE_FADE):
        f[3], f[4], f[5] = alt[1], alt[0], alt[2]       # alt colour, GRB
        f[6], f[7], f[8] = maskc[1], maskc[0], maskc[2]  # mask colour, GRB
    elif mode == MODE_SEQ:
        f[3], f[4], f[5] = bg[1], bg[0], bg[2]          # background, GRB
        f[6] = features
        sb = pack_seq(steps)
        assert len(sb) <= 16, "sequence overflows flags 7..22"
        for i, v in enumerate(sb):
            f[7 + i] = v
    f[23] = gamma
    data += bytes(f)
    assert len(data) == 48
    return bytes(data)


def expected_stream(data):
    """HEADER(3) || DATA(48) || (C16_HI C16_LO) x3 || TRAILER(3).

    The 60 v2.3 wire bytes, built straight from bench/crc.py +
    bench/patterns.py so the macro is compared against the shipping host
    reference and not against a second copy of the same logic.
    """
    fr = wrap_frame(build_payload_v23(data))             # bench ground truth
    assert len(fr) == FRAME_LEN == STREAM_LEN
    return fr


# =========================================================================
# Assertions shared by every case
# =========================================================================

FAILURES = []
PASSES = []


def check_case(name, kb, gcode, data):
    """Send `gcode`, prove the wire stream equals ground truth for `data`."""
    try:
        streams = kb.send(gcode)

        assert len(streams) == 1, \
            "expected exactly 1 transmission, got %d" % len(streams)
        got = streams[0]
        assert len(got) == STREAM_LEN, \
            "stream is %d bytes, expected %d" % (len(got), STREAM_LEN)

        # --- TRANSMIT / INDEX pattern -----------------------------------
        assert len(kb.transmits) == CHAIN_COUNT, \
            "expected %d SET_LED calls, got %d" % (CHAIN_COUNT,
                                                   len(kb.transmits))
        for n, (idx, tx, _sync) in enumerate(kb.transmits):
            assert idx == n + 1, "SET_LED #%d has INDEX=%d" % (n + 1, idx)
            want_tx = 1 if n == CHAIN_COUNT - 1 else 0
            assert tx == want_tx, \
                "SET_LED INDEX=%d has TRANSMIT=%d, expected %d" % (
                    idx, tx, want_tx)

        want = expected_stream(data)

        # --- structural checks, spelled out ------------------------------
        assert got[0:O_DATA] == HEADER == bytes.fromhex("FFAA65"), \
            "header is %s" % got[0:O_DATA].hex()
        assert got[O_DATA:O_CHK] == data, "DATA block mismatch"

        c16 = crc16_ccitt_false(data)
        assert crc16_ccitt_false_bitwise(data) == c16, \
            "bench CRC16 table and bitwise disagree"
        hi, lo = (c16 >> 8) & 0xFF, c16 & 0xFF
        chk = bytes(got[O_CHK:O_TRL])
        assert chk == bytes((hi, lo, hi, lo, hi, lo)) \
            == check_block_v23(data), \
            "check block is %s, expected %02X %02X x3" % (chk.hex(), hi, lo)
        # per-byte majority: both positions unanimous -> exactly one
        # reference, and it is the CRC16 of the DATA bytes.
        assert reference_bytes_v23(chk) == (hi, lo), \
            "per-byte majority gave %r" % (reference_bytes_v23(chk),)
        assert reference_candidates_v23(chk) == [c16]
        payload = bytes(got[O_DATA:O_TRL])
        assert verify_intact_v23(payload), "payload not intact"
        assert verify_payload_v23(payload), "receiver-side CRC16 rejected it"
        assert got[O_TRL:] == TRAILER == bytes.fromhex("9A00FF"), \
            "trailer is %s" % got[O_TRL:].hex()

        # --- and the whole thing at once --------------------------------
        assert got == want, \
            "stream mismatch\n  got  %s\n  want %s" % (got.hex(), want.hex())

        PASSES.append(name)
        print("  PASS  %s" % name)
        return got
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append((name, exc))
        print("  FAIL  %s\n        %s" % (name, exc))
        if os.environ.get("RBARF_TRACE"):
            traceback.print_exc()
        return None


def check_raises(name, kb, gcode, needle):
    try:
        kb.send(gcode)
    except CommandError as exc:
        if needle.lower() in str(exc).lower():
            PASSES.append(name)
            print("  PASS  %s  -> %s" % (name, str(exc)[:72]))
            return
        FAILURES.append((name, "wrong message: %s" % exc))
        print("  FAIL  %s  message did not mention %r:\n        %s"
              % (name, needle, exc))
        return
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append((name, "wrong exception type: %r" % exc))
        print("  FAIL  %s  raised %r instead of a command error"
              % (name, exc))
        return
    FAILURES.append((name, "no error raised"))
    print("  FAIL  %s  accepted bad input" % name)


def hexc(rgb):
    return "%02x%02x%02x" % rgb


# =========================================================================
# Cases
# =========================================================================

def main():
    print("RBARF Klipper macro verification")
    print("  cfg    : %s" % CFG)
    print("  jinja2 : %s" % jinja2.__version__)
    print("  bench  : %s" % BENCH)
    print()

    kb = MiniKlipper(CFG)
    for need in ("RBARF_SET", "RBARF_OFF", "SET_LED_INTEGER"):
        assert need in kb.macros, "%s missing from rbarf.cfg" % need

    # ---------------------------------------------------------------
    print("[1] framing / CRC self-consistency")
    assert crc16_ccitt_false(b"123456789") == 0x29B1
    assert crc16_ccitt_false_bitwise(b"123456789") == 0x29B1
    assert wrap_frame(build_payload_v23(bytes(48)))[:HDR_LEN] == HEADER
    assert wrap_frame(build_payload_v23(bytes(48)))[-TRL_LEN:] == TRAILER
    assert len(wrap_frame(build_payload_v23(bytes(48)))) == 60
    print("  PASS  bench crc.py check value 0x29B1, header/trailer "
          "constants, 60-byte frame")
    PASSES.append("bench constants")

    # The macro cannot use ^, so it folds the polynomial arithmetically.
    # That identity is load-bearing: prove it, do not trust it.
    try:
        for x in range(0, 65536, 2):
            want = x ^ 0x1021
            got_fold = (x + 4129 - 8192 * ((x // 4096) % 2)
                        - 64 * ((x // 32) % 2))
            assert got_fold == want, \
                "fold identity fails at x=%d: %d != %d" % (x, got_fold, want)
        print("  PASS  x ^ 0x1021 == x + 4129 - 8192*bit12 - 64*bit5 for "
              "all 32768 even 16-bit x")
        PASSES.append("jinja fold identity")
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append(("jinja fold identity", exc))
        print("  FAIL  jinja fold identity: %s" % exc)

    # And the whole bit-serial loop the macro runs, in Python, against
    # both bench variants -- over the standard vector, the degenerate
    # all-zero / all-ones production blocks and 2000 random ones.
    try:
        POW2 = [128, 64, 32, 16, 8, 4, 2, 1]

        def jinja_crc16(dat):
            """Byte-for-byte the arithmetic in rbarf.cfg section 11:
            integer // and % only, no bitwise operators, no hex."""
            crc = 65535
            for b in dat:
                for pw in POW2:
                    fb = ((crc // 32768) + ((b // pw) % 2)) % 2
                    sh = (crc * 2) % 65536
                    crc = (sh + 4129 - 8192 * ((sh // 4096) % 2)
                           - 64 * ((sh // 32) % 2)) if fb == 1 else sh
            return crc

        rng = random.Random(20260907)
        vecs = [b"123456789", b"", bytes(48), bytes([255] * 48),
                bytes(range(48)), bytes(((i * 5) & 0xFF) for i in range(48))]
        vecs += [bytes(rng.randrange(256) for _ in range(48))
                 for _ in range(2000)]
        for v in vecs:
            j = jinja_crc16(v)
            assert j == crc16_ccitt_false(v) == crc16_ccitt_false_bitwise(v), \
                "macro CRC16 disagrees on %s: %04X" % (v.hex(), j)
        assert jinja_crc16(b"123456789") == 0x29B1
        print("  PASS  the macro's bit-serial CRC16 == bench crc.py on "
              "%d vectors (incl. 0x29B1)" % len(vecs))
        PASSES.append("jinja crc16 loop")
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append(("jinja crc16 loop", exc))
        print("  FAIL  jinja crc16 loop: %s" % exc)

    # ---------------------------------------------------------------
    print("[2] static")
    red = (0xFF, 0x00, 0x00)
    check_case("static red", kb,
               "RBARF_SET MODE=STATIC COLOR=ff0000",
               build_data([red] * 8, MODE_STATIC))

    check_case("static, default black (no params)", kb,
               "RBARF_SET",
               build_data([(0, 0, 0)] * 8, MODE_STATIC))

    check_case("static, lowercase mode name", kb,
               "RBARF_SET MODE=static COLOR=00ff00",
               build_data([(0, 0xFF, 0)] * 8, MODE_STATIC))

    # COLORS carry-forward: entry holds until the next one, empty keeps
    # the previous, COLOR is the value before the first entry.
    cols = ["ff0000", "", "0000ff", "112233"]
    want = [(0xFF, 0, 0), (0xFF, 0, 0), (0, 0, 0xFF),
            (0x11, 0x22, 0x33), (0x11, 0x22, 0x33), (0x11, 0x22, 0x33),
            (0x11, 0x22, 0x33), (0x11, 0x22, 0x33)]
    check_case("COLORS carry-forward", kb,
               'RBARF_SET MODE=STATIC COLORS="%s"' % ",".join(cols),
               build_data(want, MODE_STATIC))

    check_case("COLORS all eight distinct", kb,
               'RBARF_SET MODE=STATIC '
               'COLORS="010203,040506,070809,0a0b0c,0d0e0f,101112,131415,161718"',
               build_data([(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12),
                           (13, 14, 15), (16, 17, 18), (19, 20, 21),
                           (22, 23, 24)], MODE_STATIC))

    check_case("COLOR fills before the first COLORS entry", kb,
               'RBARF_SET MODE=STATIC COLOR=808080 COLORS=",,ff00ff"',
               build_data([(0x80, 0x80, 0x80), (0x80, 0x80, 0x80),
                           (0xFF, 0, 0xFF), (0xFF, 0, 0xFF), (0xFF, 0, 0xFF),
                           (0xFF, 0, 0xFF), (0xFF, 0, 0xFF), (0xFF, 0, 0xFF)],
                          MODE_STATIC))

    # ---------------------------------------------------------------
    print("[3] blink")
    check_case("blink red->blue 500 ms", kb,
               "RBARF_SET MODE=BLINK COLOR=ff0000 ALT_COLOR=0000ff "
               "DURATION_MS=500",
               build_data([red] * 8, MODE_BLINK, dur_units=10,
                          alt=(0, 0, 0xFF)))

    check_case("blink with mask + mask colour", kb,
               "RBARF_SET MODE=BLINK COLOR=ff8000 ALT_COLOR=000000 "
               "DURATION_MS=1000 MASK=0,7 MASK_COLOR=00ff00",
               build_data([(0xFF, 0x80, 0)] * 8, MODE_BLINK, dur_units=20,
                          mask=mask_byte_from_indexes([0, 7]),
                          alt=(0, 0, 0), maskc=(0, 0xFF, 0)))

    check_case("blink duration rounds to the 50 ms grid", kb,
               "RBARF_SET MODE=BLINK COLOR=ffffff DURATION_MS=1234",
               build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_BLINK,
                          dur_units=(1234 + 25) // 50))

    check_case("blink at the top of the duration range", kb,
               "RBARF_SET MODE=BLINK COLOR=ffffff DURATION_MS=12750",
               build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_BLINK,
                          dur_units=255))

    # ---------------------------------------------------------------
    print("[4] fade with mask")
    check_case("fade red->green, mask LEDs 0+7 blue", kb,
               "RBARF_SET MODE=FADE COLOR=ff0000 ALT_COLOR=00ff00 "
               "DURATION_MS=1000 MASK=0,7 MASK_COLOR=0000ff",
               build_data([red] * 8, MODE_FADE, dur_units=20,
                          mask=0x81, alt=(0, 0xFF, 0), maskc=(0, 0, 0xFF)))

    check_case("fade with MASK_BITS raw byte", kb,
               "RBARF_SET MODE=FADE COLOR=ff0000 ALT_COLOR=00ff00 "
               "DURATION_MS=1000 MASK_BITS=129 MASK_COLOR=0000ff",
               build_data([red] * 8, MODE_FADE, dur_units=20,
                          mask=129, alt=(0, 0xFF, 0), maskc=(0, 0, 0xFF)))

    # MASK=0,7 and MASK_BITS=129 must be the same byte.
    assert mask_byte_from_indexes([0, 7]) == 0x81 == 129

    # ---------------------------------------------------------------
    print("[5] explicit sequence with a pause and a terminator")
    steps = [0, 1, 5, 8, 7]                       # 8 = pause, odd length
    packed = pack_seq(steps)
    assert packed == bytes([0x01, 0x58, 0x7F]), packed.hex()
    got = check_case("SEQ=0,1,5,8,7 (pause + odd length)", kb,
                     'RBARF_SET MODE=SEQUENCE SEQ="0,1,5,8,7" COLOR=00ffff '
                     'BG_COLOR=010203 DURATION_MS=1500 FADE=3 GROUP=2',
                     build_data([(0, 0xFF, 0xFF)] * 8, MODE_SEQ,
                                dur_units=30, bg=(1, 2, 3),
                                features=0x01 + 0x04, steps=steps))
    if got is not None:
        flags = got[O_DATA + 24:O_CHK]
        assert flags[7:10] == bytes([0x01, 0x58, 0x7F]), flags[7:10].hex()
        assert all(v == 0 for v in flags[10:23]), "seq tail not zeroed"

    check_case("SEQ with the P pause alias", kb,
               'RBARF_SET MODE=SEQUENCE SEQ="0,P,7,P" COLOR=ffffff '
               'DURATION_MS=1000',
               build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_SEQ, dur_units=20,
                          steps=[0, 8, 7, 8]))

    check_case("SEQ at the 31-step limit", kb,
               'RBARF_SET MODE=SEQUENCE SEQ="%s" COLOR=ffffff '
               'DURATION_MS=5000' % ",".join(str(i % 8) for i in range(31)),
               build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_SEQ, dur_units=100,
                          steps=[i % 8 for i in range(31)]))

    check_case("SEQ single step", kb,
               'RBARF_SET MODE=SEQUENCE SEQ=4 COLOR=ff00ff DURATION_MS=200',
               build_data([(0xFF, 0, 0xFF)] * 8, MODE_SEQ, dur_units=4,
                          steps=[4]))

    # ---------------------------------------------------------------
    print("[6] preset expansion - must byte-match the nibble tables")
    for pname, (psteps, ptable) in PRESET_TABLES.items():
        assert pack_seq(psteps) == ptable, \
            "%s: local packer disagrees with the table" % pname
        got = check_case("preset %s" % pname, kb,
                         "RBARF_SET MODE=%s COLOR=204060 BG_COLOR=000000 "
                         "DURATION_MS=1000 FADE=3" % pname,
                         build_data([(0x20, 0x40, 0x60)] * 8, MODE_SEQ,
                                    dur_units=20, features=0x01,
                                    steps=psteps))
        if got is None:
            continue
        flags = got[O_DATA + 24:O_CHK]
        try:
            assert flags[0] == MODE_SEQ, \
                "%s: mode byte is %02X, presets must go out as 0x03" % (
                    pname, flags[0])
            assert flags[7:7 + len(ptable)] == ptable, \
                "%s: flags[7..] = %s, table = %s" % (
                    pname, flags[7:7 + len(ptable)].hex(), ptable.hex())
            assert all(v == 0 for v in flags[7 + len(ptable):23]), \
                "%s: bytes past the terminator are not zero" % pname
            print("        flags[7..] = %s  (matches anim.c)" % ptable.hex())
        except AssertionError as exc:
            FAILURES.append(("preset %s table" % pname, exc))
            print("  FAIL  preset %s table\n        %s" % (pname, exc))

    # ---------------------------------------------------------------
    print("[7] feature bits")
    for fade, group, bits in [("0", "1", 0x00), ("2", "1", 0x02),
                              ("3", "1", 0x01), ("0", "2", 0x04),
                              ("0", "4", 0x08), ("3", "4", 0x09),
                              ("2", "2", 0x06)]:
        check_case("FADE=%s GROUP=%s -> features %02X" % (fade, group, bits),
                   kb,
                   "RBARF_SET MODE=DRAW COLOR=ffffff DURATION_MS=1000 "
                   "FADE=%s GROUP=%s" % (fade, group),
                   build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_SEQ,
                              dur_units=20, features=bits,
                              steps=PRESET_TABLES["DRAW"][0]))
    check_case("FEATURES raw byte", kb,
               "RBARF_SET MODE=SPIN COLOR=ffffff DURATION_MS=1000 FEATURES=9",
               build_data([(0xFF, 0xFF, 0xFF)] * 8, MODE_SEQ, dur_units=20,
                          features=9, steps=PRESET_TABLES["SPIN"][0]))

    # ---------------------------------------------------------------
    print("[8] gamma on / off")
    check_case("gamma off", kb,
               "RBARF_SET MODE=STATIC COLOR=ff0000 GAMMA=0",
               build_data([red] * 8, MODE_STATIC, gamma=0))
    check_case("gamma on", kb,
               "RBARF_SET MODE=STATIC COLOR=ff0000 GAMMA=1",
               build_data([red] * 8, MODE_STATIC, gamma=1))
    check_case("gamma ON keyword", kb,
               "RBARF_SET MODE=STATIC COLOR=ff0000 GAMMA=ON",
               build_data([red] * 8, MODE_STATIC, gamma=1))
    check_case("gamma on with an animation", kb,
               "RBARF_SET MODE=FADE COLOR=00ff00 DURATION_MS=2000 GAMMA=1",
               build_data([(0, 0xFF, 0)] * 8, MODE_FADE, dur_units=40,
                          gamma=1))
    check_case("gamma 2 accepted for forward compatibility", kb,
               "RBARF_SET MODE=STATIC COLOR=ff0000 GAMMA=2",
               build_data([red] * 8, MODE_STATIC, gamma=2))

    # ---------------------------------------------------------------
    print("[9] RBARF_OFF")
    check_case("RBARF_OFF", kb, "RBARF_OFF",
               build_data([(0, 0, 0)] * 8, MODE_STATIC))

    # ---------------------------------------------------------------
    print("[10] randomized frames")
    rng = random.Random(20260906)
    # one frame from each family so the three randomized cases cannot all
    # collapse onto the same code path
    pools = [["BLINK", "FADE"],
             ["SEQUENCE"],
             ["SPIN", "SPIN_REV", "RAIN", "RAIN_REV", "DRAW", "DRAW_REV"]]
    for n in range(3):
        family = rng.choice(pools[n])
        base = [(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                for _ in range(8)]
        gamma = rng.choice([0, 1])
        parts = ["RBARF_SET", "MODE=%s" % family,
                 'COLORS="%s"' % ",".join(hexc(c) for c in base),
                 "GAMMA=%d" % gamma]
        kw = dict(gamma=gamma)
        if family == "STATIC":
            mode = MODE_STATIC
        else:
            ms = rng.randrange(0, 12751)
            parts.append("DURATION_MS=%d" % ms)
            units = (ms + 25) // 50
            if ms > 0 and units == 0:      # keep the case legal
                ms, units = 0, 0
                parts[-1] = "DURATION_MS=0"
            kw["dur_units"] = units
            midx = sorted(rng.sample(range(8), rng.randrange(0, 4)))
            if midx:
                parts.append("MASK=%s" % ",".join(str(i) for i in midx))
                kw["mask"] = mask_byte_from_indexes(midx)
            if family in ("BLINK", "FADE"):
                mode = MODE_BLINK if family == "BLINK" else MODE_FADE
                alt = (rng.randrange(256), rng.randrange(256),
                       rng.randrange(256))
                mkc = (rng.randrange(256), rng.randrange(256),
                       rng.randrange(256))
                parts += ["ALT_COLOR=%s" % hexc(alt),
                          "MASK_COLOR=%s" % hexc(mkc)]
                kw.update(alt=alt, maskc=mkc)
            else:
                mode = MODE_SEQ
                bg = (rng.randrange(256), rng.randrange(256),
                      rng.randrange(256))
                fade = rng.choice(["0", "2", "3"])
                group = rng.choice(["1", "2", "4"])
                parts += ["BG_COLOR=%s" % hexc(bg), "FADE=%s" % fade,
                          "GROUP=%s" % group]
                feat = (1 if fade == "3" else (2 if fade == "2" else 0)) \
                    + (4 if group == "2" else (8 if group == "4" else 0))
                kw.update(bg=bg, features=feat)
                if family == "SEQUENCE":
                    st = [rng.randrange(0, 9)
                          for _ in range(rng.randrange(1, 20))]
                    parts.append('SEQ="%s"' % ",".join(str(s) for s in st))
                    kw["steps"] = st
                else:
                    kw["steps"] = PRESET_TABLES[family][0]
        gcode = " ".join(parts)
        check_case("random #%d (%s)" % (n + 1, family), kb, gcode,
                   build_data(base, mode, **kw))
        print("        %s" % gcode[:150])

    # ---------------------------------------------------------------
    print("[11] input validation")
    bad = [
        ("bad mode name", "RBARF_SET MODE=SPARKLE", "is not a mode"),
        ("empty mode", "RBARF_SET MODE=", "is not a mode"),
        ("short hex colour", "RBARF_SET COLOR=ff00", "6 hex digits"),
        ("non hex colour", "RBARF_SET COLOR=gg0000", "non-hex"),
        ("bad COLORS entry", 'RBARF_SET COLORS="ff0000,zz1122"', "non-hex"),
        ("too many COLORS", 'RBARF_SET COLORS="'
         + ",".join(["ff0000"] * 9) + '"', "8 LEDs"),
        ("duration out of range",
         "RBARF_SET MODE=BLINK DURATION_MS=20000", "out of range"),
        ("duration not a number",
         "RBARF_SET MODE=BLINK DURATION_MS=1.5", "whole number"),
        ("duration rounds to static",
         "RBARF_SET MODE=BLINK DURATION_MS=20", "rounds to zero"),
        ("mask index out of range",
         "RBARF_SET MODE=BLINK MASK=0,9", "LED index"),
        ("mask not numeric", "RBARF_SET MODE=BLINK MASK=first", "LED index"),
        ("MASK and MASK_BITS together",
         "RBARF_SET MODE=BLINK MASK=0 MASK_BITS=1", "not both"),
        ("MASK_BITS out of range",
         "RBARF_SET MODE=BLINK MASK_BITS=256", "0 to 255"),
        ("SEQUENCE without SEQ", "RBARF_SET MODE=SEQUENCE", "needs SEQ"),
        ("SEQ step out of range",
         'RBARF_SET MODE=SEQUENCE SEQ="0,9"', "not valid"),
        ("SEQ too long", 'RBARF_SET MODE=SEQUENCE SEQ="%s"'
         % ",".join(["0"] * 32), "at most 31 steps"),
        ("SEQ on a preset mode",
         'RBARF_SET MODE=SPIN SEQ="0,1"', "not used by MODE=SPIN"),
        ("SEQ on blink", 'RBARF_SET MODE=BLINK SEQ="0,1"',
         "not used by MODE=BLINK"),
        ("ALT_COLOR on a sequence mode",
         "RBARF_SET MODE=DRAW ALT_COLOR=ff0000", "not used by MODE=DRAW"),
        ("BG_COLOR on blink",
         "RBARF_SET MODE=BLINK BG_COLOR=ff0000", "not used by MODE=BLINK"),
        ("MASK_COLOR on a sequence mode",
         "RBARF_SET MODE=SPIN MASK_COLOR=ff0000", "not used by MODE=SPIN"),
        ("DURATION_MS on static",
         "RBARF_SET MODE=STATIC DURATION_MS=500", "not used by MODE=STATIC"),
        ("FADE on blink", "RBARF_SET MODE=BLINK FADE=3",
         "not used by MODE=BLINK"),
        ("unknown parameter", "RBARF_SET COLOUR=ff0000",
         "unknown parameter"),
        ("FEATURES with FADE",
         "RBARF_SET MODE=SPIN FEATURES=1 FADE=3", "not both"),
        ("FEATURES out of range",
         "RBARF_SET MODE=SPIN FEATURES=16", "0 to 15"),
        ("FADE value", "RBARF_SET MODE=SPIN FADE=1", "must be 0"),
        ("GROUP value", "RBARF_SET MODE=SPIN GROUP=3", "must be 1, 2 or 4"),
        ("GAMMA value", "RBARF_SET GAMMA=7", "must be 0 or 1"),
        ("SYNC value", "RBARF_SET SYNC=2", "must be 0"),
        ("DEBUG value", "RBARF_SET DEBUG=yes", "must be 0 or 1"),
        ("empty LED_NAME", "RBARF_SET LED_NAME=", "neopixel section"),
    ]
    for nm, gc, needle in bad:
        check_raises(nm, kb, gc, needle)

    # ---------------------------------------------------------------
    print("[12] LED_NAME / SYNC plumbing")
    try:
        kb.send("RBARF_SET MODE=STATIC COLOR=010101")
        assert set(kb.led_names) == {"rbarf"}, kb.led_names
        assert {s for _i, _t, s in kb.transmits} == {0}, \
            "default SYNC should be 0 (send now)"
        kb.send("RBARF_SET MODE=STATIC COLOR=010101 "
                "LED_NAME=status_strip SYNC=1")
        assert set(kb.led_names) == {"status_strip"}, kb.led_names
        assert {s for _i, _t, s in kb.transmits} == {1}, "SYNC=1 not passed"
        kb.send("RBARF_OFF LED_NAME=status_strip")
        assert set(kb.led_names) == {"status_strip"}, kb.led_names
        PASSES.append("LED_NAME / SYNC plumbing")
        print("  PASS  LED_NAME and SYNC reach SET_LED, default SYNC=0")
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append(("LED_NAME / SYNC plumbing", exc))
        print("  FAIL  LED_NAME / SYNC plumbing: %s" % exc)

    # ---------------------------------------------------------------
    print("[13] DEBUG echo")
    try:
        streams = kb.send("RBARF_SET MODE=STATIC COLOR=ff0000 DEBUG=1")
        assert len(kb.responses) == 1, kb.responses
        echoed = kb.responses[0].split(":")[-1].strip()
        assert bytes.fromhex(echoed) == streams[0], "DEBUG hex != wire bytes"
        PASSES.append("DEBUG echo")
        print("  PASS  DEBUG=1 echoes the exact 60 wire bytes")
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append(("DEBUG echo", exc))
        print("  FAIL  DEBUG echo: %s" % exc)

    # ---------------------------------------------------------------
    print("[14] byte round-trip through Klipper's float conversion")
    try:
        for b in range(256):
            assert int((b / 255.0) * 255. + .5) == b, b
        PASSES.append("float round-trip")
        print("  PASS  every byte 0..255 survives value/255.0 -> "
              "int(v*255+0.5)")
    except Exception as exc:                              # noqa: BLE001
        FAILURES.append(("float round-trip", exc))
        print("  FAIL  float round-trip: %s" % exc)

    # ---------------------------------------------------------------
    print("[15] cfg lint - constructs Klipper's Jinja cannot take")
    src = open(CFG).read()
    bodies = "\n".join(
        kb.fileconfig.get(s, "gcode") for s in kb.fileconfig.sections()
        if s.startswith("gcode_macro "))
    stmts = "\n".join(re.findall(r"\{%.*?%\}", bodies, re.S))
    lints = [
        ("no 'is not' test negation in statements (Jinja 2.10+ only)",
         re.search(r"\bis\s+not\b", stmts) is None),
        ("no {{ }} interpolation (Klipper uses single braces)",
         "{{" not in bodies and "}}" not in bodies),
        ("no {# #} Jinja comments (RawConfigParser eats the closer)",
         "{#" not in bodies),
        ("no 0x hex literals (Jinja2 2.x cannot lex them)",
         re.search(r"\b0[xX][0-9a-fA-F]", bodies) is None),
        ("no bitwise & operator", "&" not in bodies),
        ("no bitwise ^ operator", "^" not in bodies),
        ("no << or >> shifts",
         "<<" not in bodies and ">>" not in bodies),
        ("no CRC8 leftover in the macro bodies (v2.3 has no CRC8)",
         re.search(r"crc8|CRC8|% 256\b.*\bfold", bodies) is None),
        ("CRC register initialises to 65535 (CRC-16/CCITT-FALSE)",
         "namespace(crc=65535)" in bodies),
        ("CRC folds mod 65536, not mod 256",
         "% 65536" in bodies and "(nsc.crc * 2) % 256" not in bodies),
        ("frame appends the CRC as HI then LO, three times",
         bodies.count("frame.append(crc_hi)") == 3
         and bodies.count("frame.append(crc_lo)") == 3),
        ("header literal is 255, 170, 101 (FF AA 65)",
         "[255, 170, 101]" in bodies),
        ("trailer literal is 154, 0, 255 (9A 00 FF -- the ZEROS probe, "
          "not a second bit-period ruler)",
         "[154, 0, 255]" in bodies),
        ("neopixel example says chain_count: 20",
         re.search(r"#chain_count:\s*20\b", src) is not None),
        ("neopixel example says color_order: GRB",
         re.search(r"#color_order:\s*GRB\b", src) is not None),
        ("neopixel example is commented out",
         re.search(r"^\[neopixel", src, re.M) is None),
    ]
    for label, ok in lints:
        if ok:
            PASSES.append("lint: " + label)
            print("  PASS  %s" % label)
        else:
            FAILURES.append(("lint: " + label, "failed"))
            print("  FAIL  %s" % label)

    # ---------------------------------------------------------------
    print()
    print("=" * 70)
    print("%d passed, %d failed" % (len(PASSES), len(FAILURES)))
    if FAILURES:
        print()
        for nm, exc in FAILURES:
            print("  FAILED: %s\n          %s" % (nm, exc))
        print("=" * 70)
        return 1
    print("all wire frames byte-match bench/crc.py + bench/patterns.py")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
