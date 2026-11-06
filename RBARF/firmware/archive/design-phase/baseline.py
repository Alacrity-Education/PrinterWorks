"""Naive baseline: threshold pulse widths on the estimated time base.

Exists to validate the eval plumbing and set a floor. Known-broken
against swallowed 0-bits, boundary delays, and merged pulses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from harness import high_pulses  # noqa: E402


def decode(samples, meta):
    pulses = high_pulses(samples)
    if len(pulses) < 40:
        return None

    bit_ns = meta["bit_ns"]
    # Assign each pulse to a bit slot by rise time; classify by width.
    t0 = pulses[0][0]
    bits = {}
    for rise, fall in pulses:
        slot = round((rise - t0) / bit_ns)
        width = fall - rise
        n_merged = max(1, round((width + 550.0) / bit_ns))
        if n_merged > 1:
            for k in range(n_merged):
                bits[slot + k] = 1
        else:
            bits[slot] = 1 if width > 525.0 else 0

    if not bits:
        return None
    n_slots = max(bits) + 1
    stream = [bits.get(i, 0) for i in range(n_slots)]

    # Locate the header bit pattern allowing a few mismatches.
    header = bytes.fromhex(meta["header"])
    hbits = [int(b) for byte in header for b in f"{byte:08b}"]
    best_pos, best_err = None, 999
    for pos in range(0, min(len(stream) - len(hbits), 64)):
        err = sum(1 for a, b in zip(hbits, stream[pos:pos + len(hbits)])
                  if a != b)
        if err < best_err:
            best_pos, best_err = pos, err
    if best_pos is None or best_err > 4:
        return None

    start = best_pos + len(hbits)
    payload_bits = stream[start:start + 16 * 8]
    if len(payload_bits) < 128:
        payload_bits += [0] * (128 - len(payload_bits))
    out = bytearray()
    for i in range(16):
        v = 0
        for b in payload_bits[i * 8:(i + 1) * 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)
