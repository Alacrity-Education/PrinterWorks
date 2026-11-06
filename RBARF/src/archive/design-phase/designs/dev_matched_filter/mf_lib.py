"""Shared helpers for matched-filter exploration."""
import sys, math
from pathlib import Path
R = Path("/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, str(R))
from harness import load_dataset, linearize  # noqa

BIT = 1250.0
T1H = 700.0
T0H = 350.0
HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")

# Nominal receiver-clock slot layout, in *nominal ns* (62.5 ns/cycle, 40 cy loop)
LOOP_CY = 40
CY = 62.5
SLOT_CY_DOC = [1, 5, 9, 13, 17, 21, 27, 32]           # documented (37cy loop)
# candidate: 3 extra cycles all at end-of-loop gap -> gaps 4,4,4,4,4,6,5,9
SLOT_CY_END3 = [1, 5, 9, 13, 17, 21, 27, 32]


def tau(i, s, slot_cy=SLOT_CY_END3):
    """Receiver time in nominal ns (cycles*62.5) for (iteration, slot)."""
    return (i * LOOP_CY + slot_cy[s]) * CY


def bits_of(payload: bytes):
    fr = HEADER + payload + TRAILER
    return [(byte >> (7 - k)) & 1 for byte in fr for k in range(8)]


def level_at(bits, t):
    """Transmitter waveform level at absolute ns t (t=0 = frame start)."""
    if t < 0:
        return 0
    k = int(t // BIT)
    if k >= len(bits):
        return 0
    w = t - k * BIT
    return 1 if w < (T1H if bits[k] else T0H) else 0


def edge_dist(bits, t):
    """Distance in ns from t to the nearest waveform transition (>=0)."""
    if t < 0:
        return -t
    k = int(t // BIT)
    if k >= len(bits):
        return t - len(bits) * BIT
    w = t - k * BIT
    h = T1H if bits[k] else T0H
    return min(w, abs(w - h), BIT - w)


def samples_arrays(cap, slot_cy=SLOT_CY_END3):
    sm = linearize(cap["capture"])
    tt = [tau(i, s, slot_cy) for i, s, _ in sm]
    lv = [v for _, _, v in sm]
    return sm, tt, lv


def load():
    return load_dataset()
