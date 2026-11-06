"""Test patterns for WS2812 acquisition bring-up.

Frame = HEADER + payload + TRAILER (see ../../docs/PROTOCOL.md).
Payloads carry 16 data bytes, chosen to stress the acquisition/
reconstruction chain: dense ones, dense zeros, minimal pulses,
byte-boundary runs, and deterministic pseudo-random fills.

Protocol v2.3 (current)
-----------------------
The markers shrink to **3 bytes at each end** and the check block grows
to **6 bytes** — one CRC-16/CCITT-FALSE over the data bytes, written
three times, high byte first each time::

    HEADER_V23  = FF AA 65
    payload'    = DATA(16) || C16_HI C16_LO || C16_HI C16_LO
                           || C16_HI C16_LO                    = 22 B
    TRAILER_V23 = 9A 00 FF
    frame       = 3 + 22 + 3 = 28 B

The receiver recovers its reference by INDEPENDENT per-byte majority —
``reference_HI = majority(H1,H2,H3)``, ``reference_LO =
majority(L1,L2,L3)`` — so two copies damaged in different byte positions
still yield the exact 16-bit reference even though no two 16-bit blocks
agree.  See ``crc.py``.

The 3+3 marker split was chosen by measurement, not assumption:
``recon/approaches/dev_prod/marker_split_study.py`` compared 3+3, 4+2
and 2+4 over 200 880 reference-decoder runs (eps -8..+8 %, t0 375-736 ns,
all 18 payloads) and found lock success identical (100.00 % for all
three) with no split winning once marker CONTENT is held fixed.  The
same study's controls settled the marker BYTES: an 8-consecutive-zero
probe at a known position is what moves reconstruction, so the
trailer's ``55`` ruler became ``00`` (owner decision 2026-09-07,
+26.7 points of delivery on silicon).  ``PATTERNS_V23`` /
``VAL_PATTERNS_V23`` hold the test data wrapped that way — 22-byte
payloads, 28-byte frames.

Superseded sets, kept byte-exact so the acquired corpora and their
parity harnesses stay reproducible — do not use for new work:
``PATTERNS_V22`` / ``VAL_PATTERNS_V22`` (4-byte CRC8 block, 20-byte
payloads, 28-byte frames), ``PATTERNS_V21`` / ``VAL_PATTERNS_V21``
(3-byte CRC8 block, 19-byte payloads, 27-byte frames), and the v2.0
names ``PATTERNS`` / ``VAL_PATTERNS`` / ``PAYLOAD_LEN``, which other
tools import.  ``HEADER`` / ``TRAILER`` / ``frame()`` likewise stay on
the **4-byte v2.0-v2.2 markers**: ``recon/synth.py`` and the design
harnesses build the calibration corpus with them.  v2.3 work uses
``HEADER_V23`` / ``TRAILER_V23`` / ``frame_v23()``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from crc import (build_payload, build_payload_v23,     # noqa: E402,F401
                 check_block, check_block_v23, crc8_smbus,
                 crc16_ccitt_false, majority, majority_byte,
                 reference_bytes_v23, reference_candidates_v23,
                 verify_intact, verify_intact_v23,
                 verify_payload, verify_payload_v23)

# --- v2.3 markers (current) -------------------------------------------------
# Chosen split: (a) 3+3 (measured; see ../../docs/PROTOCOL.md).  Marker jobs:
#   FF sync  |  AA bit-period ruler  |  65 / 9A byte alignment
#   00 (trailer) = worst-case-ZEROS calibration probe at a KNOWN position
# and 9A is the bit complement of 65, so start and end stay distinguishable.
# The trailer's 0x55 ruler was traded for the 00 probe by owner decision
# (2026-09-07): the probe is worth +7.0 points of plateau bit-exact
# reconstruction on the model and +26.7 points of delivery on real
# silicon (71.1 % -> 97.8 %, paired McNemar 25:1, chi2 20.35, p<0.001),
# while the end-of-frame ruler measured no benefit even under
# within-capture drift -- the refine stage regresses over whole-burst
# pulses, not markers.  Sizing is unchanged: 3 + N + 6 + 3.
HEADER_V23 = bytes.fromhex("FFAA65")
TRAILER_V23 = bytes.fromhex("9A00FF")

# --- v2.0-v2.2 markers (compat; synth.py + the design harnesses) ------------
HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")

PAYLOAD_LEN = 16                                # DATA bytes, every version

# --- v2.3 sizing (current) --------------------------------------------------
CHECK_LEN_V23 = 6                               # (C16_HI, C16_LO) x 3
CHECK_COPIES_V23 = 3
DATA_LEN_V23 = PAYLOAD_LEN                      # test data stays 16 bytes
PAYLOAD_LEN_V23 = DATA_LEN_V23 + CHECK_LEN_V23  # 22
FRAME_LEN_V23 = len(HEADER_V23) + PAYLOAD_LEN_V23 + len(TRAILER_V23)   # 28

# Production sizing: 48 data bytes (16 LEDs, GRB) + 6 check bytes = 54-byte
# payload -> 60-byte frame = EXACTLY 20 WS2812 LEDs.  No pad byte can exist;
# the marker trim (8 -> 6) and the check growth (4 -> 6) had to happen
# together to keep that true (see ../../docs/PROTOCOL.md and bench/pad_law.py).
PROD_DATA_LEN = 48
PROD_PAYLOAD_LEN_V23 = PROD_DATA_LEN + CHECK_LEN_V23                   # 54
PROD_FRAME_LEN_V23 = (len(HEADER_V23) + PROD_PAYLOAD_LEN_V23
                      + len(TRAILER_V23))                              # 60

# --- superseded v2.2 sizing (corpora tooling only) --------------------------
CHECK_LEN = 4                                   # [CRC8] * 4
DATA_LEN_V22 = PAYLOAD_LEN
PAYLOAD_LEN_V22 = DATA_LEN_V22 + CHECK_LEN      # 20
FRAME_LEN_V22 = len(HEADER) + PAYLOAD_LEN_V22 + len(TRAILER)   # 28
PROD_PAYLOAD_LEN_V22 = PROD_DATA_LEN + CHECK_LEN                # 52
PROD_FRAME_LEN_V22 = len(HEADER) + PROD_PAYLOAD_LEN_V22 + len(TRAILER)  # 60

# --- superseded v2.1 sizing (corpora tooling only) --------------------------
CHECK_LEN_V21 = 3
PAYLOAD_LEN_V21 = PAYLOAD_LEN + CHECK_LEN_V21   # 19
FRAME_LEN_V21 = len(HEADER) + PAYLOAD_LEN_V21 + len(TRAILER)   # 27
PROD_PAYLOAD_LEN_V21 = PROD_DATA_LEN + CHECK_LEN_V21            # 51
PROD_FRAME_LEN_V21 = len(HEADER) + PROD_PAYLOAD_LEN_V21 + len(TRAILER)  # 59


def _lcg_bytes(seed: int, n: int) -> bytes:
    x = seed
    out = bytearray()
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


PATTERNS = {
    "zeros":      bytes([0x00] * 16),   # all-short pulses: max swallowed-bit stress
    "ones":       bytes([0xFF] * 16),   # all-long pulses
    "aa":         bytes([0xAA] * 16),   # alternating bits
    "p55":        bytes([0x55] * 16),   # alternating, opposite phase
    "lone1":      bytes([0x01] * 16),   # 7 zeros + lone one per byte
    "msb1":       bytes([0x80] * 16),   # lone one + 7 zeros per byte
    "count":      bytes(range(16)),     # low-entropy ramp
    "impulse_hi": bytes([0x00] * 7 + [0xFF] + [0x00] * 8),
    "impulse_lo": bytes([0xFF] * 7 + [0x00] + [0xFF] * 8),
    "blocks":     bytes([0x00, 0xFF] * 8),
    "nibbles":    bytes([0x0F, 0xF0] * 8),
    "sparse":     bytes([0x11] * 16),   # isolated ones
    "dense":      bytes([0xEE] * 16),   # isolated zeros
    "runs":       bytes([0x7F, 0xFE] * 8),   # long runs crossing byte boundaries
    "edges":      bytes([0x01, 0x80] * 8),   # ones adjacent to byte boundaries
    "rnd1":       _lcg_bytes(1, 16),
    "rnd2":       _lcg_bytes(2, 16),
    "rnd3":       _lcg_bytes(3, 16),
}

# Validation set: patterns NEVER seen by any calibration or tuning pass.
# Acquired separately (data/captures_val.json) as a clean generalization test.
VAL_PATTERNS = {
    "vrnd4":    _lcg_bytes(11, 16),
    "vrnd5":    _lcg_bytes(17, 16),
    "vrnd6":    _lcg_bytes(23, 16),
    "vrnd7":    _lcg_bytes(31, 16),
    "vrnd8":    _lcg_bytes(47, 16),
    "vgray":    bytes((i ^ (i >> 1)) for i in range(16)),
    "vwalk1":   bytes((1 << (i % 8)) for i in range(16)),        # walking one
    "vwalkz":   bytes(0xFF ^ (1 << (i % 8)) for i in range(16)), # walking zero
    "vprime":   bytes([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31,
                       37, 41, 43, 47, 53]),
    "v5a":      bytes([0x5A] * 16),
    "va5":      bytes([0xA5] * 16),
    "vchecker": bytes([0x33, 0xCC] * 8),
}

assert all(len(p) == PAYLOAD_LEN for p in PATTERNS.values())
assert all(len(p) == PAYLOAD_LEN for p in VAL_PATTERNS.values())


# ``build_payload_v23(data) -> DATA || (C16_HI C16_LO)*3`` is defined in
# ``crc.py`` and re-exported here so bench tools can get it from either
# module.  See crc.check_block_v23 / crc.reference_bytes_v23 for the
# per-byte majority policy.

# v2.3 pattern sets (current): identical test data, 6-byte check block.
PATTERNS_V23 = {name: build_payload_v23(p) for name, p in PATTERNS.items()}
VAL_PATTERNS_V23 = {name: build_payload_v23(p)
                    for name, p in VAL_PATTERNS.items()}

assert all(len(p) == PAYLOAD_LEN_V23 for p in PATTERNS_V23.values())
assert all(len(p) == PAYLOAD_LEN_V23 for p in VAL_PATTERNS_V23.values())

# Superseded v2.2 sets (4-byte CRC8 block) and v2.1 sets (3-byte CRC8
# block) — byte-exact reproductions of the frames in
# data/captures_v22*.json / captures_v21*.json; kept for the parity
# harnesses and acquire.py --set v22/v22val/v21/v21val only.
PATTERNS_V22 = {name: build_payload(p) for name, p in PATTERNS.items()}
VAL_PATTERNS_V22 = {name: build_payload(p) for name, p in VAL_PATTERNS.items()}
PATTERNS_V21 = {name: build_payload(p, n=CHECK_LEN_V21)
                for name, p in PATTERNS.items()}
VAL_PATTERNS_V21 = {name: build_payload(p, n=CHECK_LEN_V21)
                    for name, p in VAL_PATTERNS.items()}

assert all(len(p) == PAYLOAD_LEN_V22 for p in PATTERNS_V22.values())
assert all(len(p) == PAYLOAD_LEN_V22 for p in VAL_PATTERNS_V22.values())
assert all(len(p) == PAYLOAD_LEN_V21 for p in PATTERNS_V21.values())
assert all(len(p) == PAYLOAD_LEN_V21 for p in VAL_PATTERNS_V21.values())


def frame_v23(payload: bytes) -> bytes:
    """Wrap a v2.3 payload in the 3-byte markers."""
    return HEADER_V23 + payload + TRAILER_V23


def frame(payload: bytes) -> bytes:
    """COMPAT (v2.0-v2.2): wrap a payload in the 4-byte markers.

    ``recon/synth.py`` and the design harnesses build the calibration
    corpus through this function, so it keeps the old markers.  v2.3 work
    uses :func:`frame_v23`.
    """
    return HEADER + payload + TRAILER


def _selftest() -> None:
    """Round-trip every pattern through the v2.3 builder and the receiver
    policy, then confirm the superseded sets are still byte-exact.

    Per pattern, v2.3:
      * the payload is exactly ``data + (HI, LO) * 3``, HI first;
      * all three copies are equal and equal ``crc16_ccitt_false(data)``;
      * the per-byte majority returns that CRC16 and one reference;
      * receiver-side ``verify_payload_v23`` accepts it;
      * ONE fully corrupted copy is still accepted (2 of 3 per byte);
      * THREE COPIES DAMAGED IN DIFFERENT BYTE POSITIONS are still
        accepted -- no two 16-bit blocks agree, so a block-level vote has
        nothing to decide, yet each byte position keeps two good votes;
      * a byte position with no majority falls back to the ranked
        cross product, with the truth among the candidates;
      * any single-bit data error is rejected;
      * the frame is 28 bytes and starts/ends with the 3-byte markers.
    """
    n = 0
    for label, table in (("main", PATTERNS), ("val", VAL_PATTERNS)):
        v23 = PATTERNS_V23 if label == "main" else VAL_PATTERNS_V23
        v22 = PATTERNS_V22 if label == "main" else VAL_PATTERNS_V22
        v21 = PATTERNS_V21 if label == "main" else VAL_PATTERNS_V21
        for name, data in table.items():
            payload = v23[name]
            tag = f"{label}/{name}"
            assert payload == build_payload_v23(data), tag
            assert payload[:PAYLOAD_LEN] == data, tag
            assert len(payload) == PAYLOAD_LEN_V23 == 22, tag

            fr = frame_v23(payload)
            assert len(fr) == FRAME_LEN_V23 == 28, tag
            assert fr[:3] == HEADER_V23 == bytes.fromhex("FFAA65"), tag
            assert fr[-3:] == TRAILER_V23 == bytes.fromhex("9A00FF"), tag

            chk = payload[-CHECK_LEN_V23:]
            c16 = crc16_ccitt_false(data)
            hi, lo = (c16 >> 8) & 0xFF, c16 & 0xFF
            assert chk == check_block_v23(data), tag
            assert chk == bytes((hi, lo, hi, lo, hi, lo)), tag
            assert reference_bytes_v23(chk) == (hi, lo), tag
            assert reference_candidates_v23(chk) == [c16], tag
            assert verify_intact_v23(payload), f"{tag}: block not intact"
            assert verify_payload_v23(payload), f"{tag}: CRC16 verify failed"
            assert verify_payload_v23(payload, allow_split_vote=False), tag

            # One fully mangled copy must not cost the frame.
            for cp in range(CHECK_COPIES_V23):
                bad = bytearray(payload)
                bad[PAYLOAD_LEN + 2 * cp] ^= 0xFF
                bad[PAYLOAD_LEN + 2 * cp + 1] ^= 0xFF
                assert reference_bytes_v23(
                    bad[-CHECK_LEN_V23:]) == (hi, lo), (tag, cp)
                assert verify_payload_v23(bytes(bad)), (tag, cp)

            # THE HEADLINE: copies damaged in DIFFERENT byte positions.
            # copy0's HI and copy1's LO wrecked -> the three 16-bit blocks
            # are all distinct, so no block-level majority exists at all,
            # yet HI still votes 2-1 and LO still votes 2-1.
            bad = bytearray(payload)
            bad[PAYLOAD_LEN + 0] ^= 0x5A
            bad[PAYLOAD_LEN + 3] ^= 0xA5
            got = bytes(bad[-CHECK_LEN_V23:])
            blocks = [(got[2 * i] << 8) | got[2 * i + 1] for i in range(3)]
            assert len(set(blocks)) == 3, (tag, blocks)
            assert reference_bytes_v23(got) == (hi, lo), tag
            assert reference_candidates_v23(got) == [c16], tag
            assert verify_payload_v23(bytes(bad)), tag
            assert verify_payload_v23(bytes(bad), allow_split_vote=False), tag

            # A byte position with NO majority -> ranked cross product.
            bad = bytearray(payload)
            bad[PAYLOAD_LEN + 1] ^= 0x01
            bad[PAYLOAD_LEN + 3] ^= 0x02
            got = bytes(bad[-CHECK_LEN_V23:])
            assert reference_bytes_v23(got) == (hi, None), tag
            cands = reference_candidates_v23(got)
            assert len(cands) == 3 and c16 in cands, (tag, cands)
            assert verify_payload_v23(bytes(bad)), tag
            assert not verify_payload_v23(bytes(bad),
                                          allow_split_vote=False), tag

            # Any single-bit data error must be caught.
            for i in range(PAYLOAD_LEN):
                for bit in range(8):
                    bad = bytearray(payload)
                    bad[i] ^= 1 << bit
                    assert not verify_payload_v23(bytes(bad)), (tag, i, bit)

            # Superseded sets still byte-exact (same data, CRC8 block).
            assert v22[name] == data + check_block(data), tag
            assert v21[name] == data + check_block(data, n=3), tag
            assert v22[name][:-1] == v21[name], tag
            assert verify_intact(v22[name]) and verify_intact(v21[name], n=3)
            assert len(frame(v22[name])) == FRAME_LEN_V22 == 28, tag
            assert len(frame(v21[name])) == FRAME_LEN_V21 == 27, tag
            n += 1

    # Production sizing: 48 data + 6 check = 54 -> 60-byte frame, exactly
    # 20 x 3-byte WS2812 LEDs, no pad byte.
    prod = build_payload_v23(bytes(PROD_DATA_LEN))
    assert len(prod) == PROD_PAYLOAD_LEN_V23 == 54
    assert len(frame_v23(prod)) == PROD_FRAME_LEN_V23 == 60 == 20 * 3
    assert verify_intact_v23(prod) and verify_payload_v23(prod)
    # ... and the superseded v2.2 production frame was 60 bytes too, which
    # is why the marker trim and the check growth had to be one change.
    assert len(frame(build_payload(bytes(PROD_DATA_LEN)))) == 60

    print(f"patterns.py self-test OK ({n} patterns round-tripped, "
          f"v2.3 payload {PAYLOAD_LEN_V23} B, frame {FRAME_LEN_V23} B; "
          f"production {PROD_PAYLOAD_LEN_V23} B / {PROD_FRAME_LEN_V23} B "
          f"= 20 LEDs exactly)")


if __name__ == "__main__":
    print(f"--- v2.3 (markers {HEADER_V23.hex().upper()} / "
          f"{TRAILER_V23.hex().upper()}, data {DATA_LEN_V23} + check "
          f"{CHECK_LEN_V23} = payload {PAYLOAD_LEN_V23}, "
          f"frame {FRAME_LEN_V23}) ---")
    for label, table in (("main", PATTERNS_V23), ("val", VAL_PATTERNS_V23)):
        for name, p in table.items():
            data, chk = p[:-CHECK_LEN_V23], p[-CHECK_LEN_V23:]
            print(f"{label:4s} {name:11s} {data.hex()} + {chk.hex()}  "
                  f"frame={frame_v23(p).hex()}")

    print()
    _selftest()
