#!/usr/bin/env python3
"""End-to-end proof of klipper/rbarf.cfg against real hardware.

    ####################################################################
    ##  RUN THIS WHEN THE BENCH IS FREE.  IT IS NOT RUN AS PART OF    ##
    ##  THE MACRO WORK AND HAS NEVER BEEN EXECUTED.                   ##
    ##                                                                ##
    ##  It opens the Pico test probe, power-cycles the STM8 and puts  ##
    ##  frames on the WS2812 line.  Another workflow owns the         ##
    ##  hardware, so the script refuses to touch a serial port unless  ##
    ##  you pass --bench-is-free explicitly.                          ##
    ####################################################################

What it proves
--------------
`klipper/verify_macro.py` proves the macro produces the right *bytes*.
This script proves those exact bytes are *decoded by the device*: it
renders RBARF_SET through the same Klipper emulation, takes the byte
stream that Klipper's neopixel driver would clock out, sends it with the
test probe, and scores the device's decode report against ground truth.

    ####################################################################
    ##  BLOCKED ON THE DEVICE SIDE.  The macro now emits v2.3 (3-byte  ##
    ##  markers + a tripled CRC16), but the on-chip decoder is still   ##
    ##  v2.2 (4-byte markers + [CRC8]*4).  Until the firmware speaks   ##
    ##  v2.3 every frame here will refuse on R2 (marker) -- that is    ##
    ##  expected, not a macro bug.  klipper/verify_macro.py is the     ##
    ##  host-side proof and is green.                                  ##
    ####################################################################

Pad-byte history: under v2.1 this script existed to test the one 0x00
pad byte a 20-LED chain forced onto the 59-byte frame -- and it proved
the pad FATAL (~+1.6 % clock-fit inflation per surplus byte; see
bench/pad_law.py and recon/PROD_CLOSURE.md section 9.4).  Protocol v2.2
designed the pad out and v2.3 keeps it designed out: the marker trim
(8 -> 6 bytes) and the check-block growth (4 -> 6 bytes) are one change,
so the frame is still 60 bytes = EXACTLY 20 LEDs and the stream Klipper
clocks out IS the protocol frame, byte for byte.

    "frame"  the 60-byte v2.3 stream = the protocol frame (default)
    "pad1"   the same + one trailing 0x00  (61 B; negative control:
             the pad law says it must refuse)
    "lead1"  one leading 0x00 + the frame  (61 B; negative control)

Firmware
--------
Needs the PRODUCTION geometry (ND_DATA=48, CHK_LEN=6, 60-byte frames)
built for v2.3 -- see the blocking note above:

    make rbarf-prod
    python3 flash.py --ihx build/rbarf_prod_verbose.ihx flash-only

Use the **_verbose** image: it adds "V:<96 hex>" after every verified
decode, which is what lets this script compare all 48 DATA bytes rather
than only trusting the status letter.  Without VERBOSE the script still
runs, but a pass only means "the device accepted a frame", not "the
device received these bytes" - it reports that reduced confidence.

Reports understood
------------------
    RBARF-P 1                 production banner
    D:O:<eps>                 direct CRC pass
    D:C:<eps>                 chase-repaired
    D:R<cause>:<eps>          refused, cause digit from decode.h CAUSE_*
    V:<96 hex>                the 48 decoded DATA bytes (VERBOSE builds)
    DEC:<hex>:<eps>:<status>  dev-firmware line format, also accepted

Usage (when the bench is free):
    python3 bench/test_klipper_macro.py --bench-is-free [--reps 3]
                                        [--port PORT] [--out FILE]
"""

import argparse
import glob
import json
import random
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# The macro renderer and the Klipper emulation live with the macro.
sys.path.insert(0, str(ROOT / "klipper"))
sys.path.insert(0, str(HERE))

from verify_macro import (MiniKlipper, CFG, build_data, hexc,      # noqa: E402
                          mask_byte_from_indexes, expected_stream,
                          PRESET_TABLES, MODE_STATIC, MODE_BLINK,
                          MODE_FADE, MODE_SEQ, STREAM_LEN, FRAME_LEN)
from crc import crc16_ccitt_false                                   # noqa: E402
from epsfmt import parse_eps                                        # noqa: E402

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600


# =========================================================================
# The frames to push - one per interesting macro code path
# =========================================================================

RED = (0xFF, 0x00, 0x00)
WHITE = (0xFF, 0xFF, 0xFF)
DIM = (0x40, 0x40, 0x40)


def build_cases():
    """(name, gcode, expected 48 DATA bytes) for every case."""
    cases = [
        ("off",
         "RBARF_OFF",
         build_data([(0, 0, 0)] * 8, MODE_STATIC)),

        ("static_red",
         "RBARF_SET MODE=STATIC COLOR=ff0000",
         build_data([RED] * 8, MODE_STATIC)),

        ("static_eight_colors",
         'RBARF_SET MODE=STATIC '
         'COLORS="ff0000,00ff00,0000ff,ffff00,ff00ff,00ffff,ffffff,404040"',
         build_data([(0xFF, 0, 0), (0, 0xFF, 0), (0, 0, 0xFF),
                     (0xFF, 0xFF, 0), (0xFF, 0, 0xFF), (0, 0xFF, 0xFF),
                     (0xFF, 0xFF, 0xFF), (0x40, 0x40, 0x40)], MODE_STATIC)),

        ("blink_500ms",
         "RBARF_SET MODE=BLINK COLOR=ff0000 ALT_COLOR=0000ff "
         "DURATION_MS=500",
         build_data([RED] * 8, MODE_BLINK, dur_units=10, alt=(0, 0, 0xFF))),

        ("fade_masked",
         "RBARF_SET MODE=FADE COLOR=ff0000 ALT_COLOR=00ff00 "
         "DURATION_MS=1000 MASK=0,7 MASK_COLOR=0000ff",
         build_data([RED] * 8, MODE_FADE, dur_units=20,
                    mask=mask_byte_from_indexes([0, 7]),
                    alt=(0, 0xFF, 0), maskc=(0, 0, 0xFF))),

        ("sequence_pause",
         'RBARF_SET MODE=SEQUENCE SEQ="0,1,5,8,7" COLOR=00ffff '
         'BG_COLOR=010203 DURATION_MS=1500 FADE=3 GROUP=2',
         build_data([(0, 0xFF, 0xFF)] * 8, MODE_SEQ, dur_units=30,
                    bg=(1, 2, 3), features=0x05, steps=[0, 1, 5, 8, 7])),

        # An all-zero DATA block is the degenerate worst case for the
        # sampler (every wire bit short).  Note its v2.3 CRC16 is
        # 0xDF9D, NOT zero -- CCITT-FALSE inits to 0xFFFF, so unlike the
        # old CRC8 the check block still carries real edges here.
        ("all_zero_data",
         "RBARF_SET MODE=STATIC COLOR=000000 GAMMA=0",
         build_data([(0, 0, 0)] * 8, MODE_STATIC)),

        # The opposite: dense ones.
        ("all_ff_base",
         "RBARF_SET MODE=STATIC COLOR=ffffff",
         build_data([WHITE] * 8, MODE_STATIC)),

        ("gamma_on",
         "RBARF_SET MODE=FADE COLOR=00ff00 DURATION_MS=2000 GAMMA=1",
         build_data([(0, 0xFF, 0)] * 8, MODE_FADE, dur_units=40, gamma=1)),
    ]

    # ---- high-entropy rnd COLORS frames ------------------------------
    # The hand-written cases above are deliberately low-entropy (flat
    # colours, all-zero, all-FF) because they stress the sampler's worst
    # cases -- but low entropy is exactly what the known production
    # margin gap punishes, so a refusal there says nothing about whether
    # the framing is right.  These two fill all 24 base bytes with
    # pseudorandom values (seeded, so ground truth is reproducible),
    # putting the frame in the high-entropy regime where a refusal can
    # only mean the FRAMING is wrong.  They are the pad verdict's
    # primary evidence.
    rng = random.Random(20260906)
    for n in (1, 2):
        base = [(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                for _ in range(8)]
        cases.append((
            "rnd_colors%d" % n,
            'RBARF_SET MODE=STATIC COLORS="%s"'
            % ",".join(hexc(c) for c in base),
            build_data(base, MODE_STATIC)))

    # every preset expansion
    for pname, (psteps, _tbl) in PRESET_TABLES.items():
        cases.append((
            "preset_%s" % pname.lower(),
            "RBARF_SET MODE=%s COLOR=404040 DURATION_MS=1000 FADE=3" % pname,
            build_data([DIM] * 8, MODE_SEQ, dur_units=20, features=0x01,
                       steps=psteps)))
    return cases


# =========================================================================
# UART line assembly (same shape as drive_v21.py)
# =========================================================================

class LineReader:
    def __init__(self):
        self.buf = bytearray()
        self.lines = []                    # (t_monotonic, str)
        self.cond = threading.Condition()

    def feed(self, data):
        now = time.monotonic()
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[: nl + 1]
                if line:
                    self.lines.append(
                        (now, line.decode("ascii", errors="replace")))
            self.cond.notify_all()

    def wait_for(self, prefix, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, line) in enumerate(self.lines):
                    if line.startswith(prefix):
                        del self.lines[: i + 1]
                        return t, line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, None
                self.cond.wait(remaining)

    def wait_any(self, prefixes, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, (t, line) in enumerate(self.lines):
                    if any(line.startswith(p) for p in prefixes):
                        del self.lines[: i + 1]
                        return t, line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None, None
                self.cond.wait(remaining)


def parse_report(line):
    """-> (status, eps_centi, data_hex or None).

    Accepts the production terse line  D:<O|C|R#>:<eps>
    and the dev-firmware line          DEC:<hex>:<eps>:<status>.
    """
    if line.startswith("DEC:"):
        try:
            _, hexdata, eps_s, status = line.split(":")
            return status, int(eps_s), hexdata.lower()
        except ValueError:
            return None, None, None
    if line.startswith("D:"):
        try:
            _, st, eps_s = line.split(":")
        except ValueError:
            return None, None, None
        if st == "O":
            status = "OK"
        elif st == "C":
            status = "CHASED"
        elif st.startswith("R"):
            status = "REFUSE" + st[1:]
        else:
            return None, None, None
        try:
            eps = parse_eps(eps_s)
        except ValueError:
            eps = 0
        return status, eps, None
    return None, None, None


# =========================================================================
# main
# =========================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-is-free", action="store_true",
                    help="REQUIRED. Confirms no other workflow owns the "
                         "bench right now. Without it nothing is opened.")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", default=None)
    ap.add_argument("--cases", default=None,
                    help="comma-separated case names to run (default: all). "
                         "Used to run a paired frame-vs-pad1 control on the "
                         "cases that actually deliver.")
    ap.add_argument("--variants", default="frame",
                    help="frame = the exact 60-byte v2.3 stream Klipper "
                         "clocks out (= the protocol frame); pad1/lead1 "
                         "add one surplus 0x00 as negative controls")
    ap.add_argument("--out", default=str(
        ROOT / "klipper" / "bench_klipper_macro_results.json"))
    args = ap.parse_args()

    if not args.bench_is_free:
        print(__doc__)
        print("Refusing to touch the bench without --bench-is-free.")
        return 2

    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in ("frame", "pad1", "lead1"):
            raise SystemExit("unknown variant %r" % v)

    # ---- render every case through the Klipper emulation ---------------
    kb = MiniKlipper(CFG)
    cases = build_cases()
    if args.cases:
        want = [c.strip() for c in args.cases.split(",") if c.strip()]
        known = {n for n, _g, _d in cases}
        for w in want:
            if w not in known:
                raise SystemExit("unknown case %r (have: %s)"
                                 % (w, ", ".join(sorted(known))))
        cases = [c for c in cases if c[0] in want]
    rendered = []
    print("[macro] rendering %d cases from %s" % (len(cases), CFG))
    for name, gcode, data in cases:
        streams = kb.send(gcode)
        if len(streams) != 1:
            raise SystemExit("[macro] %s produced %d transmissions"
                             % (name, len(streams)))
        stream = streams[0]
        if len(stream) != STREAM_LEN:
            raise SystemExit("[macro] %s produced %d bytes, want %d"
                             % (name, len(stream), STREAM_LEN))
        want = expected_stream(data)
        if stream != want:
            raise SystemExit("[macro] %s does not match ground truth - fix "
                             "the macro before going near the bench\n"
                             "  got  %s\n  want %s"
                             % (name, stream.hex(), want.hex()))
        assert len(stream) == FRAME_LEN == STREAM_LEN  # v2.3: no pad exists
        rendered.append({
            "name": name, "gcode": gcode, "data": data,
            # v2.3: the neopixel stream IS the protocol frame (60 B).
            "frame": stream,
            # negative controls: ONE surplus byte must refuse (pad law).
            "pad1": stream + b"\x00",
            "lead1": b"\x00" + stream,
            "crc16": crc16_ccitt_false(data),
        })
        print("  %-22s crc16 %04X  %s" % (name, crc16_ccitt_false(data),
                                          stream.hex()))
    print("[macro] all %d cases match klipper/verify_macro.py ground truth"
          % len(rendered))
    print()

    # ---- the bench ------------------------------------------------------
    sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                                if (p / "rbarf_config.py").is_file())))
    from rbarf_config import picotool_host, probe_port        # noqa: E402
    sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
    from testprobe import TestProbe                        # noqa: E402

    port = probe_port(args.port)

    reader = LineReader()
    rows = []
    n_ok = n_chase = n_refuse = n_cat = n_proto = n_silent = 0
    verbose_fw = False

    with TestProbe(port) as probe:
        print("[probe] %s on %s" % (probe.ident(), port))
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        banner = None
        for cycle in range(1, 4):          # bench rule: stop after 3 cycles
            print("[bench] power cycle %d/3 (5 s SWIM window)..." % cycle)
            probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
            time.sleep(2.0)
            probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
            _, banner = reader.wait_any(("RBARF-P", "RBARF-V21"), 15.0)
            if banner is not None:
                break
        if banner is None:
            raise SystemExit("[bench] FAIL: no firmware banner after 3 power "
                             "cycles -- STOP (bench rule). Flash "
                             "build/rbarf_prod_verbose.ihx first.")
        print("[bench] banner: %r" % banner)
        if not banner.startswith("RBARF-P"):
            print("[bench] WARNING: this is not the production image. The "
                  "dev image is ND_DATA=16 and cannot decode a 48-byte "
                  "frame. Flash build/rbarf_prod_verbose.ihx.")

        total = len(rendered) * len(variants) * args.reps
        done = 0
        for case in rendered:
            for variant in variants:
                wire = case[variant]
                for rep in range(args.reps):
                    # The production firmware re-arms on its own; it does
                    # not print READY. Give it more than the worst-case
                    # blind window (decode ~50-65 ms + report) before the
                    # next frame.
                    time.sleep(0.35)
                    t0 = time.monotonic()
                    probe.ws2812_write(wire)
                    t_rep, line = reader.wait_any(("D:", "DEC:"), 5.0)

                    row = {"case": case["name"], "variant": variant,
                           "rep": rep, "bytes": len(wire),
                           "frame": wire.hex().upper(), "line": line}

                    if line is None:
                        n_silent += 1
                        row["verdict"] = "NO-REPORT"
                        rows.append(row)
                        done += 1
                        print("[bench] %3d/%d %-22s %-6s r%d: NO REPORT "
                              "(frame never seen)"
                              % (done, total, case["name"], variant, rep))
                        continue

                    status, eps, hexdata = parse_report(line)
                    if status is None:
                        n_proto += 1
                        row["verdict"] = "PROTOCOL-ERROR"
                        rows.append(row)
                        done += 1
                        print("[bench] %3d/%d %-22s %-6s r%d: BAD LINE %r"
                              % (done, total, case["name"], variant, rep,
                                 line[:60]))
                        continue

                    # a VERBOSE build follows an accepted decode with V:
                    if status in ("OK", "CHASED") and hexdata is None:
                        _t, vline = reader.wait_for("V:", 1.5)
                        if vline is not None:
                            verbose_fw = True
                            hexdata = vline.split(":", 1)[1].strip().lower()

                    truth = case["data"].hex()
                    if status in ("OK", "CHASED"):
                        if hexdata is None:
                            verdict = "ACCEPTED-UNCHECKED"
                            n_ok += 1
                        elif hexdata == truth:
                            verdict = "DELIVERED"
                            if status == "OK":
                                n_ok += 1
                            else:
                                n_chase += 1
                        else:
                            verdict = "CATASTROPHIC"
                            n_cat += 1
                            row["decoded"] = hexdata
                            row["truth"] = truth
                    elif status.startswith("REFUSE"):
                        verdict = "MISSED"
                        n_refuse += 1
                    else:
                        verdict = "PROTOCOL-ERROR"
                        n_proto += 1

                    row.update(verdict=verdict, status=status,
                               eps_centi=eps,
                               report_ms=(t_rep - t0) * 1e3)
                    rows.append(row)
                    done += 1
                    print("[bench] %3d/%d %-22s %-6s r%d: %-18s %-8s "
                          "eps %+.2f%%"
                          % (done, total, case["name"], variant, rep,
                             verdict, status, eps / 100.0))

    # ---- summary --------------------------------------------------------
    delivered = n_ok + n_chase
    print()
    print("=" * 72)
    print("KLIPPER MACRO BENCH PROOF")
    print("  %d/%d delivered (%d direct + %d chased), %d refused (missed), "
          "%d CATASTROPHIC, %d protocol errors, %d silent"
          % (delivered, len(rows), n_ok, n_chase, n_refuse, n_cat, n_proto,
             n_silent))
    if not verbose_fw:
        print("  NOTE: no V: lines seen - this was not a VERBOSE build, so "
              "an accepted frame was NOT compared byte for byte. Reflash "
              "build/rbarf_prod_verbose.ihx for a real proof.")

    # per-case delivery by variant (v2.3: "frame" is the real case; any
    # pad1/lead1 rows are negative controls and SHOULD refuse)
    print()
    print("  per-case delivery:")
    for case in rendered:
        got = {}
        for variant in variants:
            v = [r for r in rows
                 if r["case"] == case["name"] and r["variant"] == variant]
            good = sum(1 for r in v if r.get("verdict") == "DELIVERED")
            got[variant] = "%d/%d" % (good, len(v))
        print("    %-22s %s" % (case["name"],
                                "  ".join("%s %s" % (k, v)
                                          for k, v in got.items())))
    print("=" * 72)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "macro": str(CFG),
            "firmware_expected": "build/rbarf_prod_verbose.ihx "
                                 "(ND_DATA=48, CHK_LEN=6, CHECK_EN=1, "
                                 "VERBOSE=1) built for v2.3. The on-chip "
                                 "decoder was still v2.2 when the macro "
                                 "moved to v2.3, so until the firmware is "
                                 "ported every frame refuses on R2 "
                                 "(marker), and that is expected.",
            "verbose_seen": verbose_fw,
            "variants": variants,
            "scoring": "single transmission: DELIVERED = accepted AND the "
                       "48 DATA bytes equal ground truth; REFUSE = missed "
                       "frame; accepted but different = CATASTROPHIC "
                       "(must be 0)",
            "pad_note": "v2.3: the 60-byte frame IS exactly the 20-LED "
                        "chain -- no pad byte exists. 'pad1'/'lead1' rows, "
                        "if present, are 61-byte negative controls that the "
                        "pad law says must refuse.",
        },
        "summary": {
            "rows": len(rows), "delivered": delivered, "direct": n_ok,
            "chased": n_chase, "refused": n_refuse, "catastrophic": n_cat,
            "protocol_errors": n_proto, "no_report": n_silent,
        },
        "rows": rows,
    }, indent=1))
    print("[bench] wrote %s" % out)

    if n_cat or n_proto:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
