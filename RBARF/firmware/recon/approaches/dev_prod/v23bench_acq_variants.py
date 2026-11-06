#!/usr/bin/env python3
"""SAME-SESSION real-silicon A/B of the dropped 0x00 calibration probe.

All four variants are 3+3 markers, 28-byte frames, identical DATA and
identical CRC16 check block.  ONLY the marker bytes differ, so frame
length, capture geometry and the pad law are held constant.

  V0  FF AA 65 / 9A 55 FF   the v2.3 SPEC markers (in-session control)
  V1  FF 00 65 / 9A 55 FF   0x00 probe in the HEADER
  V2  FF AA 65 / 9A 00 FF   0x00 probe in the TRAILER
  V3  FF 00 65 / 9A 00 FF   0x00 probe at BOTH ends (v2.2's arrangement)

Writes raw captures to the scratchpad; the repo's data/ is untouched.
"""
import glob, json, sys, time
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
sys.path.insert(0, str(NEWIMPL / "bench"))
from testprobe import TestProbe
from acquire import LineReader, PIN_POWER, POWER_ON_LEVEL, PIN_UART_RX, \
    PIN_UART_TX, PIN_WS2812, BAUD, CAP_BYTES
from patterns import PATTERNS
from crc import build_payload_v23

VARIANTS = {
    "V0_spec":    ("FFAA65", "9A55FF"),
    "V1_hdr00":   ("FF0065", "9A55FF"),
    "V2_trl00":   ("FFAA65", "9A00FF"),
    "V3_both00":  ("FF0065", "9A00FF"),
}
REPS = 3
OUT = Path(sys.argv[1])

reader = LineReader()
rows = []
port = probe_port()
with TestProbe(port) as probe:
    print("[probe]", probe.ident())
    probe.on_uart_rx = reader.feed
    probe.ws2812_config(PIN_WS2812)
    probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)
    print("[bench] power-cycling target...")
    probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL); time.sleep(2.0)
    probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)
    if reader.wait_for("RBARF-CAP", 15.0) is None:
        raise SystemExit("FAIL: no capture-firmware banner")
    print("[bench] capture firmware up")
    total = len(VARIANTS) * len(PATTERNS) * REPS
    done = 0
    # INTERLEAVE the variants per pattern so any slow thermal drift hits
    # all four equally instead of loading one of them.
    for name, payload in PATTERNS.items():
        for rep in range(REPS):
            for vname, (h, t) in VARIANTS.items():
                fr = bytes.fromhex(h) + build_payload_v23(payload) + bytes.fromhex(t)
                assert len(fr) == 28
                if reader.wait_for("READY", 10.0) is None:
                    raise SystemExit("FAIL: no READY %s %s r%d" % (vname, name, rep))
                time.sleep(0.05)
                probe.ws2812_write(fr)
                line = reader.wait_for("CAP:", 15.0)
                if line is None:
                    raise SystemExit("FAIL: no dump %s %s r%d" % (vname, name, rep))
                _, hexdata, cksum = line.split(":")
                raw = bytes.fromhex(hexdata)
                assert len(raw) == CAP_BYTES, len(raw)
                if sum(raw) & 0xFF != int(cksum, 16):
                    raise SystemExit("FAIL: checksum %s %s r%d" % (vname, name, rep))
                rows.append(dict(variant=vname, hdr=h, trl=t, pattern=name,
                                 rep=rep, payload=payload.hex().upper(),
                                 frame=fr.hex().upper(), capture=hexdata))
                done += 1
        print("[bench] %3d/%d  %s" % (done, total, name))
OUT.write_text(json.dumps(rows))
print("[bench] wrote", len(rows), "captures ->", OUT)
