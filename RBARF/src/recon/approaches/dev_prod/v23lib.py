"""v2.3 synthetic-capture + reference-decoder lab (host only, no bench).

Shared by relax_sweep.py (RELAXATIONS A/B/C parameter search), fuzz_v23.py
(the >=80-case bit-exactness + wrong-emission corpus) and parity_v23.py.

Physics: recon/synth.py's calibrated sampler (the model fitted to the 54
real captures), identical to dev_prod/sweeplib.py, plus the deliberate
capture MALFORMATIONS that the R1/R2 refusal classes actually come from
on silicon (MARGIN_INVESTIGATION.md SS4: ~6 % of frames mis-arm).

Frames are v2.3: HEADER FF AA 65 || DATA || (C16_HI C16_LO)x3 ||
TRAILER 9A 00 FF -- 28 B at ND=16, 60 B (= 20 LEDs) at ND=48.
"""
import importlib.util
import sys
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "bench"))

import synth                                                    # noqa: E402
from synth import (LOOP_NS, SLOT_OFFSET_NS, BRANCH_COST_NS, BIT_NS,  # noqa
                   T1H_NS, T0H_NS)
from crc import build_payload_v23, crc16_ccitt_false             # noqa: E402
from patterns import (HEADER_V23, TRAILER_V23, PATTERNS,         # noqa: E402
                      VAL_PATTERNS)

CAP_BYTES_PROD = 288
CAP_BYTES_TEST = 160


def load_ref():
    """A FRESH embedded_v2 module instance (so a sweep can hold several
    parameter sets side by side without cross-talk)."""
    spec = importlib.util.spec_from_file_location(
        "embedded_v2_x", NEWIMPL / "recon" / "approaches" / "embedded_v2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wire_frame(data: bytes) -> bytes:
    p = build_payload_v23(data)
    assert len(p) == len(data) + 6
    fr = HEADER_V23 + p + TRAILER_V23
    assert len(fr) == len(data) + 12
    return fr


def frame_bits(data: bytes):
    return [int(b) for byte in wire_frame(data) for b in f"{byte:08b}"]


def simulate(bits, eps, phase_ns, n_iter, drift=0.0):
    """[(i, s, level)] like synth._simulate; drift = linear eps ramp in
    percent across the burst (0 = none)."""
    out = []
    wsum = 0.0
    nb = len(bits)
    span = nb * BIT_NS
    for i in range(n_iter):
        base = i * LOOP_NS
        for s in range(8):
            a = base + SLOT_OFFSET_NS[s] + wsum
            e = eps
            if drift:
                frac = min(max((a) / span, 0.0), 1.0)
                e = eps + drift * (frac - 0.5)
            t = phase_ns + a / (1.0 + e)
            if t < 0:
                lvl = 0
            else:
                k = int(t // BIT_NS)
                lvl = 0 if k >= nb else (
                    1 if (t - k * BIT_NS) < (T1H_NS if bits[k] else T0H_NS)
                    else 0)
            if lvl:
                wsum += BRANCH_COST_NS[s]
            out.append((i, s, lvl))
    return out


def pack(samples, nbytes):
    """cap_code.s capture layout (fuzz48.pack semantics)."""
    lv = {(i, s): v for (i, s, v) in samples}
    out = bytearray(nbytes)
    for i in range(nbytes):
        b = 0
        if i > 0:
            b |= lv.get((i - 1, 6), 0) << 7
            b |= lv.get((i - 1, 7), 0) << 6
        for s in range(6):
            b |= lv.get((i, s), 0) << (5 - s)
        out[i] = b
    return bytes(out)


def linearize(raw: bytes):
    """The firmware's own inverse of pack() (recon/harness.linearize)."""
    out = []
    n = len(raw)
    for i in range(n):
        b = raw[i]
        for k in range(6):
            out.append((i, k, (b >> (5 - k)) & 1))
        if i + 1 < n:
            nb = raw[i + 1]
            out.append((i, 6, (nb >> 7) & 1))
            out.append((i, 7, (nb >> 6) & 1))
    out.sort(key=lambda s: (s[0], s[1]))
    return out


def capture(data: bytes, eps: float, t0: float, ncap=None, drift=0.0,
            trunc=0, chop=0):
    """One synthetic capture, raw bytes in cap_code.s layout.

    trunc: drop the last `trunc` capture bytes (arm fired late / buffer ran
           out -> the burst's TAIL is missing, which is exactly the
           malformed-capture shape MARGIN_INVESTIGATION SS4 measured)
    chop:  drop the first `chop` bytes and shift left (arm fired late ->
           the burst's HEAD is missing; the endpoint seed sees a short span)
    """
    nb_bytes = ncap or (CAP_BYTES_PROD if len(data) == 48 else CAP_BYTES_TEST)
    bits = frame_bits(data)
    sm = simulate(bits, eps, t0, nb_bytes + 1, drift)
    raw = bytearray(pack(sm, nb_bytes))
    if chop:
        raw = raw[chop:] + bytes(chop)
    if trunc:
        raw = raw[:nb_bytes - trunc]
    return bytes(raw)


def set_params(ev, **kw):
    """Override reference constants for a sweep point (after _configure)."""
    for k, v in kw.items():
        assert hasattr(ev, k), k
        setattr(ev, k, v)


PROD_PATTERNS = None


def prod_payloads():
    """The 10 production gate payloads (bench/drive_prod.py FRAMES) --
    imported from the file, the bench itself is never touched."""
    global PROD_PATTERNS
    if PROD_PATTERNS is None:
        spec = importlib.util.spec_from_file_location(
            "drive_prod_frames", NEWIMPL / "bench" / "drive_prod.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        PROD_PATTERNS = dict(m.FRAMES)
    return PROD_PATTERNS


def test_payloads(include_val=True):
    d = dict(PATTERNS)
    if include_val:
        d.update({("val_" + k): v for k, v in VAL_PATTERNS.items()})
    return d
