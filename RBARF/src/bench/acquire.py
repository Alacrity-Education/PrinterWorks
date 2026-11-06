#!/usr/bin/env python3
"""Acquire WS2812 captures from the STM8 through the test bench.

Flow per session:
  1. power-cycle the target (capture firmware boots, 5 s SWIM window)
  2. wait for the READY line on UART (9600, Pico GPIO1 <- STM8 pin 8)
  3. for each pattern x bench repetition (--reps, see note below):
       send frame on Pico GPIO29 (WS2812 generator) -> STM8 pin 7
       read the CAP:<hex>:<sum> dump, verify checksum
       wait for the next READY
  4. write data/captures.json with dataset metadata

Usage: python3 bench/acquire.py [--reps 3] [--port PORT] [--out FILE]
                     [--set main|val|v21|v21val|v22|v22val|v23|v23val]

Pattern sets:
  v23     CURRENT: the 18 main patterns as v2.3 payloads (16 data + 6
          check bytes = 22-byte payload, 28-byte frame)
  v23val  CURRENT: the 12 held-out patterns as v2.3 payloads
  main    18 v2.0 patterns, 16-byte payload, 24-byte frame
  val     12 v2.0 held-out patterns, 16-byte payload, 24-byte frame
  v22     SUPERSEDED: the 18 main patterns as v2.2 payloads (16 data +
          4 CRC8 check bytes = 20-byte payload, 28-byte frame)
  v22val  SUPERSEDED: the 12 held-out patterns as v2.2 payloads
  v21     SUPERSEDED: the 18 main patterns as v2.1 payloads (16 data +
          3 CRC8 check bytes = 19-byte payload, 27-byte frame)
  v21val  SUPERSEDED: the 12 held-out patterns as v2.1 payloads

v2.3 is the first version to change the framing bytes: the markers trim
to 3 bytes at each end (HEADER FF AA 65, TRAILER 9A 00 FF -- the
trailer's middle byte is a worst-case-ZEROS calibration probe, not a
second bit-period ruler; owner decision 2026-09-07) and the check
block grows to 6 bytes -- ``C16_HI C16_LO`` three times, one
CRC-16/CCITT-FALSE over the DATA bytes only. The receiver recovers its
reference by INDEPENDENT PER-BYTE majority (reference_HI = majority of
the three HI copies, reference_LO likewise), so two copies damaged in
different byte positions still yield the exact 16-bit reference. There
is no CRC8 anywhere in v2.3; the v2.1/v2.2 sets keep it only as a compat
mode so their corpora stay reproducible. See bench/crc.py and
../../docs/PROTOCOL.md.

Note that ``--reps`` here is a BENCH convenience: it acquires N
independent captures of the same frame for dataset statistics. It is not
a protocol feature -- in the real link the host sends each logical frame
exactly once (single transmission, no repeats, no retries, no sequence
numbers).
"""

import argparse
import glob
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / "rbarf_config.py").is_file())))
from rbarf_config import picotool_host, probe_port        # noqa: E402
sys.path.insert(0, picotool_host())   # probe lib; $RBARF_PICOTOOL_HOST
from testprobe import TestProbe  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from patterns import (HEADER, TRAILER, PATTERNS, VAL_PATTERNS,  # noqa: E402
                      HEADER_V23, TRAILER_V23,
                      PATTERNS_V21, VAL_PATTERNS_V21,
                      PATTERNS_V22, VAL_PATTERNS_V22,
                      PATTERNS_V23, VAL_PATTERNS_V23,
                      frame, frame_v23)

PIN_POWER = 28
POWER_ON_LEVEL = 1
PIN_UART_RX = 1
PIN_UART_TX = 0
PIN_WS2812 = 29
BAUD = 9600
CAP_BYTES = 640

META = {
    "device": "STM8S001J3 @ 16 MHz nominal (HSI, ~±1-2% tolerance)",
    "firmware": "capture.c + cap_code.s",
    "signal": "WS2812 NZR 800 kbps from RP2040 PIO (T0H~350ns, T1H~700ns, "
              "bit 1.25us, exact crystal-derived timing)",
    "capture_bytes": CAP_BYTES,
    "samples_per_byte": 8,
    "period_cycles": 37,
    "f_cpu_nominal_hz": 16_000_000,
    "sample_cycle_positions": [1, 5, 9, 13, 17, 21, 27, 32],
    "sample_gaps_cycles": [4, 4, 4, 4, 4, 6, 5, 6],
    "byte_layout": "bit7=BS0 of PREVIOUS iteration, bit6=BS1 of PREVIOUS "
                   "iteration, bit5..bit0=R0..R5 of THIS iteration. "
                   "Chronological order within iteration i: R0..R5 at "
                   "37*i+[1,5,9,13,17,21], BS0 at 37*i+27, BS1 at 37*i+32 "
                   "(stored in byte i+1 bits 7,6). First byte's bits 7..6 "
                   "are garbage; the last iteration's BS0/BS1 are lost.",
    "trigger": "capture starts at the first rising edge on the signal; "
               "sample R0 of iteration 0 lands ~1 cycle after the edge "
               "test fell through",
    "header": HEADER.hex().upper(),
    "trailer": TRAILER.hex().upper(),
    "checksum": "sum of 640 raw capture bytes mod 256",
}

# Per-set definition: pattern dict, default output name, protocol version.
# The version also selects the framing: v2.3 uses the 3-byte markers and
# frame_v23(); every earlier set keeps the 4-byte markers and frame().
SETS = {
    "main":   (PATTERNS,         "captures.json",          None),
    "val":    (VAL_PATTERNS,     "captures_val.json",      None),
    "v21":    (PATTERNS_V21,     "captures_v21.json",      "v2.1"),
    "v21val": (VAL_PATTERNS_V21, "captures_v21_val.json",  "v2.1"),
    "v22":    (PATTERNS_V22,     "captures_v22.json",      "v2.2"),
    "v22val": (VAL_PATTERNS_V22, "captures_v22_val.json",  "v2.2"),
    "v23":    (PATTERNS_V23,     "captures_v23.json",      "v2.3"),
    "v23val": (VAL_PATTERNS_V23, "captures_v23_val.json",  "v2.3"),
}

# Added to META only for the v2.3 sets (current).  v2.3 is the first
# version to change HEADER/TRAILER, so those keys are overwritten too.
META_V23 = {
    "protocol": "v2.3",
    "header": HEADER_V23.hex().upper(),
    "trailer": TRAILER_V23.hex().upper(),
    "marker_split": "3 + 3 bytes; 48 known marker bits (was 64). Chosen by "
                    "measurement over the 3+3 / 4+2 / 2+4 candidates: lock "
                    "success is identical (100% for all three across eps "
                    "-8..+8% x t0 375-736 ns x 18 payloads, 52488 reference "
                    "decodes) and no split wins once marker CONTENT is held "
                    "fixed -- recon/approaches/dev_prod/"
                    "marker_split_study.py",
    "marker_bytes": "HEADER FF AA 65 = sync / bit-period ruler / byte "
                    "alignment. TRAILER 9A 00 FF = byte alignment / "
                    "worst-case-ZEROS calibration probe / sync + latch. "
                    "TRAILER[1] is 0x00, NOT a second bit-period ruler: "
                    "owner decision 2026-09-07 traded 0x55 for 0x00 on the "
                    "marker-split study's own controls (+7.0 points of "
                    "plateau bit-exact reconstruction, t0-p90 tail cut) "
                    "and on the Gate phase's real-silicon interleaved A/B "
                    "(+26.7 points of delivery, 71.1% -> 97.8% pooled over "
                    "90 paired cells, paired McNemar 25:1, chi2 20.35, "
                    "p<0.001, 0 wrong either way). The end-of-frame ruler "
                    "measured NO benefit even under within-capture drift, "
                    "because the refine stage regresses over whole-burst "
                    "pulses rather than markers. Frame sizing and the 48 "
                    "known marker bits are unchanged. Corpora acquired "
                    "before that date carry trailer 9A55FF and are COMPAT "
                    "corpora -- see recon/PROD_CLOSURE.md section 13.",
    "payload_layout": "DATA(16) || C16_HI C16_LO || C16_HI C16_LO || "
                      "C16_HI C16_LO = 22 bytes; frame = 3 + 22 + 3 = 28 "
                      "bytes",
    "crc16": "CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, "
             "xorout 0x0000) over the DATA bytes only. Check value "
             "CRC16('123456789') = 0x29B1",
    "check_block": "the same CRC16 written three times, byte order HI,LO in "
                   "every copy. The receiver recovers its reference by "
                   "INDEPENDENT PER-BYTE majority: reference_HI = "
                   "majority(H1,H2,H3), reference_LO = majority(L1,L2,L3). "
                   "Per byte position the truth survives as the majority "
                   "when >=2 of the 3 copies are correct there and remains "
                   "a candidate when >=1 is, so two copies damaged in "
                   "DIFFERENT byte positions still give the exact 16-bit "
                   "reference even though no two 16-bit blocks agree. A "
                   "byte position with no majority contributes its distinct "
                   "values as candidates ranked by decode confidence; the "
                   "references are the cross product, capped at 9 (= 3x3).",
    "crc8": "NONE. CRC8 is gone from v2.3 -- it went out with v2.2's "
            "4-byte block. The v2.1/v2.2 sets keep it only as a compat "
            "mode.",
    "production_sizing": "48 data bytes + 6 check bytes = 54-byte payload, "
                         "60-byte frame = exactly 20 WS2812 LEDs (no pad "
                         "byte; any surplus wire byte inflates the "
                         "decoder's whole-burst clock fit ~1.6%/byte -- "
                         "bench/pad_law.py). The marker trim (8->6 bytes) "
                         "and the check-block growth (4->6 bytes) are one "
                         "change: together they hold the frame at 60 bytes.",
    "design_goal": "ALMOST ALWAYS EMIT. A refusal loses the frame outright "
                   "under single-transmission delivery, so the decoder "
                   "emits even on an imperfect reconstruction PROVIDED the "
                   "16-bit check validates the payload. The 16-bit check is "
                   "what makes that safe: p_trial = R/65536, 256x stronger "
                   "per trial than the old CRC8, which affords about 131 "
                   "wrong trials per frame at the <=0.2% wrong-emission "
                   "target (bench/crc.py fa_budget) where the 8-bit check "
                   "could not afford one. The measured wrong-emission rate "
                   "is reported at every step and must never be hidden.",
    "delivery": "single transmission: each logical frame goes on the wire "
                "exactly once; no repeats, no retries, no acks, no sequence "
                "numbers. The --reps captures in this dataset are "
                "independent bench acquisitions of the same frame, not "
                "protocol repeats.",
}

# Added to META only for the v2.1 sets (superseded; kept so the existing
# captures_v21*.json corpora stay reproducible); the v2.0 datasets keep
# the exact metadata they have always had.
META_V21 = {
    "protocol": "v2.1",
    "payload_layout": "DATA(16) || CRC8 || CRC8 || CRC8 = 19 bytes; "
                      "frame = 4 + 19 + 4 = 27 bytes",
    "crc8": "CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no xorout) "
            "over the DATA bytes only",
    "check_block": "the same CRC8 repeated 3 times (triplication); the "
                   "receiver takes the 2-of-3 MAJORITY of the decoded check "
                   "bytes as its chase reference, so one corrupted check byte "
                   "is harmless. No majority (all three differ) -> rank the "
                   "three candidates by decode confidence and try in order.",
    "production_sizing": "48 data bytes + 3 check bytes = 51-byte payload, "
                         "59-byte frame",
    "delivery": "single transmission: each logical frame goes on the wire "
                "exactly once; no repeats, no retries, no acks, no sequence "
                "numbers. The --reps captures in this dataset are independent "
                "bench acquisitions of the same frame, not protocol repeats.",
}

# Added to META only for the v2.2 sets.
META_V22 = {
    "protocol": "v2.2",
    "payload_layout": "DATA(16) || CRC8 || CRC8 || CRC8 || CRC8 = 20 bytes; "
                      "frame = 4 + 20 + 4 = 28 bytes",
    "crc8": "CRC-8/SMBUS (poly 0x07, init 0x00, no reflection, no xorout) "
            "over the DATA bytes only",
    "check_block": "the same CRC8 repeated 4 times; the receiver's chase "
                   "reference is the UNIQUE value holding >= 2 of the 4 "
                   "votes, so one corrupted check byte is harmless and two "
                   "differently-corrupted ones still leave a majority. A "
                   "2-2 tie or a full split (no such value) -> rank the "
                   "distinct candidates by decode confidence and try in "
                   "order.",
    "production_sizing": "48 data bytes + 4 check bytes = 52-byte payload, "
                         "60-byte frame = exactly 20 WS2812 LEDs (no pad "
                         "byte; any surplus wire byte inflates the clock "
                         "fit ~1.6%/byte -- bench/pad_law.py)",
    "delivery": "single transmission: each logical frame goes on the wire "
                "exactly once; no repeats, no retries, no acks, no sequence "
                "numbers. The --reps captures in this dataset are independent "
                "bench acquisitions of the same frame, not protocol repeats.",
}


class LineReader:
    """Assemble UART RX bytes into lines."""

    def __init__(self):
        self.buf = bytearray()
        self.lines = []
        self.cond = threading.Condition()

    def feed(self, data: bytes) -> None:
        with self.cond:
            self.buf.extend(data)
            while True:
                nl = self.buf.find(b"\n")
                if nl < 0:
                    break
                line = bytes(self.buf[:nl]).replace(b"\r", b"")
                del self.buf[: nl + 1]
                if line:
                    self.lines.append(line.decode("ascii", errors="replace"))
            self.cond.notify_all()

    def wait_for(self, prefix: str, timeout: float):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, line in enumerate(self.lines):
                    if line.startswith(prefix):
                        del self.lines[: i + 1]
                        return line
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.cond.wait(remaining)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--port", default=None)
    ap.add_argument("--set", choices=tuple(SETS), default="main",
                    help="pattern set: v23 / v23val are the current v2.3 "
                         "payloads (16 data + 6 check = 22 bytes) in the "
                         "3-byte markers, 28-byte frames; main (18) and "
                         "val (12, held out) are the v2.0 sets; v22 / "
                         "v22val and v21 / v21val are the superseded CRC8 "
                         "payloads, kept only to reproduce their corpora")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    patterns, default_name, version = SETS[args.set]
    if args.out is None:
        args.out = str(Path(__file__).parent.parent / "data" / default_name)

    meta = dict(META)
    if version == "v2.1":
        meta.update(META_V21)
    elif version == "v2.2":
        meta.update(META_V22)
    elif version == "v2.3":
        meta.update(META_V23)

    # v2.3 is the first version to change the framing bytes.
    wrap = frame_v23 if version == "v2.3" else frame
    frame_len = len(wrap(next(iter(patterns.values()))))
    print(f"[bench] set={args.set} ({len(patterns)} patterns, "
          f"{frame_len}-byte frames) -> {args.out}")

    port = probe_port(args.port)

    reader = LineReader()
    captures = []
    t_start = time.time()

    with TestProbe(port) as probe:
        print(f"[probe] {probe.ident()} on {port}")
        probe.on_uart_rx = reader.feed
        probe.ws2812_config(PIN_WS2812)
        probe.uart_config(PIN_UART_TX, PIN_UART_RX, BAUD)

        print("[bench] power-cycling target (5s boot window)...")
        probe.gpio_write(PIN_POWER, 1 - POWER_ON_LEVEL)
        time.sleep(2.0)
        probe.gpio_write(PIN_POWER, POWER_ON_LEVEL)

        if reader.wait_for("RBARF-CAP", 15.0) is None:
            raise SystemExit("[bench] FAIL: no banner from capture firmware")
        print("[bench] capture firmware is up")

        total = len(patterns) * args.reps
        done = 0
        for name, payload in patterns.items():
            fr = wrap(payload)
            for rep in range(args.reps):
                if reader.wait_for("READY", 10.0) is None:
                    raise SystemExit(f"[bench] FAIL: no READY before "
                                     f"{name} rep {rep}")
                time.sleep(0.05)
                probe.ws2812_write(fr)
                line = reader.wait_for("CAP:", 15.0)
                if line is None:
                    raise SystemExit(f"[bench] FAIL: no dump for {name} "
                                     f"rep {rep}")
                try:
                    _, hexdata, cksum = line.split(":")
                except ValueError:
                    raise SystemExit(f"[bench] FAIL: bad dump line for "
                                     f"{name} rep {rep}: {line[:60]}...")
                raw = bytes.fromhex(hexdata)
                if len(raw) != CAP_BYTES:
                    raise SystemExit(f"[bench] FAIL: {name} rep {rep}: "
                                     f"{len(raw)} bytes, want {CAP_BYTES}")
                if sum(raw) & 0xFF != int(cksum, 16):
                    raise SystemExit(f"[bench] FAIL: checksum mismatch on "
                                     f"{name} rep {rep}")
                captures.append({
                    "pattern": name,
                    "rep": rep,
                    "payload": payload.hex().upper(),
                    "frame": fr.hex().upper(),
                    "capture": hexdata,
                })
                done += 1
                print(f"[bench] {done:3d}/{total}  {name} rep {rep}: OK "
                      f"({sum(bin(b).count('1') for b in raw)} high samples)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"meta": meta, "acquired_unix": t_start, "captures": captures},
        indent=1))
    print(f"[bench] wrote {len(captures)} captures to {out}")


if __name__ == "__main__":
    main()
