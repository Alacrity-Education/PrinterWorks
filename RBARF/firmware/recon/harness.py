"""Shared harness for WS2812 reconstruction work.

Loads the acquired dataset and linearizes the oversampled capture bytes
into a chronologically ordered sample list. Times are exposed as
(iteration, slot) coordinates plus helper conversions — the exact
intra-loop sample offsets are NOT precisely known (see DATASET.md), so
decoders that model timing should treat them as calibratable.

Decoder contract (a module in approaches/):

    def decode(samples: list[tuple[int, int, int]], meta: dict) -> bytes | None
        samples: chronological (iteration, slot, level) triples.
                 iteration = sampling-loop index (0..639)
                 slot      = 0..7 sample slot within the loop
                 level     = 0/1
        meta:    dataset meta dict (see data/captures.json and DATASET.md),
                 augmented with harness constants below.
        returns: recovered PAYLOAD bytes (header/trailer stripped), or
                 None if no frame found.

Ground truth (the sent payload) is used by eval.py only for scoring;
decoders must not read the dataset file themselves.
"""

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "captures.json"

# --- Empirical timing constants (measured against the crystal-exact PIO
# --- signal; see DATASET.md "Timing ground truth") ---------------------
LOOP_NS = 2507.3          # one 8-sample loop, median across captures
BIT_NS = 1250.0           # WS2812 bit period (exact, crystal-derived)
T0H_NS = 350.0            # WS2812 short high (exact)
T1H_NS = 700.0            # WS2812 long high (exact)

# Nominal intra-loop slot offsets in ns: the old source comment claims
# cycle positions [1,5,9,13,17,21,27,32] out of 37; the measured loop is
# ~40.1 cycles, so these are scaled as a *starting estimate* only.
_DOC_POS = [1, 5, 9, 13, 17, 21, 27, 32]
SLOT_OFFSET_NS = [p * LOOP_NS / 37.0 for p in _DOC_POS]


def load_dataset(path=DATA):
    d = json.loads(Path(path).read_text())
    meta = dict(d["meta"])
    meta.update({
        "loop_ns_measured": LOOP_NS,
        "bit_ns": BIT_NS, "t0h_ns": T0H_NS, "t1h_ns": T1H_NS,
        "slot_offset_ns_estimate": SLOT_OFFSET_NS,
    })
    return meta, d["captures"]


def linearize(capture_hex: str):
    """Capture bytes -> chronological [(iteration, slot, level)].

    Stored byte i: bit7 = BS0 of iteration i-1 (slot 6), bit6 = BS1 of
    iteration i-1 (slot 7), bits5..0 = R0..R5 of iteration i (slots 0..5).
    Byte 0's bits 7..6 are garbage (skipped); the last iteration's
    boundary samples were never stored.
    """
    raw = bytes.fromhex(capture_hex)
    n = len(raw)
    out = []
    for i in range(n):
        b = raw[i]
        for k in range(6):                       # slots 0..5 from bits 5..0
            out.append((i, k, (b >> (5 - k)) & 1))
        if i + 1 < n:                            # slots 6,7 live in byte i+1
            nb = raw[i + 1]
            out.append((i, 6, (nb >> 7) & 1))
            out.append((i, 7, (nb >> 6) & 1))
    out.sort(key=lambda s: (s[0], s[1]))
    return out


def approx_time_ns(iteration: int, slot: int) -> float:
    """Approximate absolute sample time. Slot offsets are estimates —
    calibrate against the known header if you need better."""
    return iteration * LOOP_NS + SLOT_OFFSET_NS[slot]


def to_levels(samples):
    """[(it, slot, level)] -> parallel lists (times_ns, levels)."""
    times = [approx_time_ns(i, s) for i, s, _ in samples]
    levels = [v for _, _, v in samples]
    return times, levels


def high_pulses(samples):
    """[(t_rise_ns, t_fall_ns)] per high pulse, using approx times of the
    first sample at each new level."""
    pulses = []
    rise = None
    prev = samples[0][2]
    if prev:
        rise = approx_time_ns(samples[0][0], samples[0][1])
    for it, sl, v in samples[1:]:
        if v and not prev:
            rise = approx_time_ns(it, sl)
        elif prev and not v and rise is not None:
            pulses.append((rise, approx_time_ns(it, sl)))
            rise = None
        prev = v
    return pulses


def score(decoded, expected: bytes):
    """(exact: bool, byte_accuracy: float) for a decoded payload."""
    if decoded is None:
        return False, 0.0
    n = max(len(expected), len(decoded))
    if n == 0:
        return True, 1.0
    good = sum(1 for a, b in zip(decoded, expected) if a == b)
    return bytes(decoded) == expected, good / n
