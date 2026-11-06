"""Shared lib for the margin investigation: calibrated-sampler simulation
(clone of recon/synth.py physics, additionally returning wall times), the
capture packer (fuzz48.pack), the 10 gate payloads (drive_prod FRAMES,
imported without touching the bench), and the host decoder (decode.c,
production geometry ND48/CHK4) via ctypes.

INVESTIGATION-ONLY: nothing here modifies project files.
"""
import ctypes
import importlib.util
import sys
from pathlib import Path

NEWIMPL = Path(__file__).resolve().parents[3]
SC = Path(__file__).resolve().parent
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "bench"))

from crc import build_payload, crc8_smbus          # noqa: E402
import synth                                        # noqa: E402
from synth import (LOOP_NS, SLOT_OFFSET_NS, BRANCH_COST_NS, BIT_NS,  # noqa
                   T1H_NS, T0H_NS)

HEADER = bytes.fromhex("FF00AA65")
TRAILER = bytes.fromhex("9A5500FF")
CAP_BYTES = 288

# ---- the 10 gate payloads (drive_prod.py FRAMES, loaded from the file) --
_spec = importlib.util.spec_from_file_location(
    "drive_prod_frames", NEWIMPL / "bench" / "drive_prod.py")
# drive_prod imports testprobe at module load; that works on this host
# (the picotool host lib is importable), but guard anyway:
try:
    _dp = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_dp)
    FRAMES = _dp.FRAMES
except Exception:  # fall back: re-create verbatim
    raise

def wire_frame(data48: bytes) -> bytes:
    p = build_payload(data48)
    assert len(p) == 52
    fr = HEADER + p + TRAILER
    assert len(fr) == 60
    return fr


# ---- simulation (identical physics to synth._simulate, but also
#      returns wall times so swallow/merge can be attributed per bit) ----

def frame_bits(data48: bytes):
    return [int(b) for byte in wire_frame(data48) for b in f"{byte:08b}"]


def simulate(bits, eps, phase_ns, n_iter=CAP_BYTES):
    """[(i, s, level)] like synth._simulate (drift=0), plus a parallel
    list of wall times (ns, relative to first frame edge)."""
    out = []
    times = []
    wsum = 0.0
    f_rel = 1.0 + eps
    nb = len(bits)
    for i in range(n_iter):
        base = i * LOOP_NS
        for s in range(8):
            a = base + SLOT_OFFSET_NS[s] + wsum
            t = phase_ns + a / f_rel
            if t < 0:
                lvl = 0
            else:
                k = int(t // BIT_NS)
                if k >= nb:
                    lvl = 0
                else:
                    within = t - k * BIT_NS
                    lvl = 1 if within < (T1H_NS if bits[k] else T0H_NS) else 0
            if lvl:
                wsum += BRANCH_COST_NS[s]
            out.append((i, s, lvl))
            times.append(t)
    return out, times


def pack(samples, nbytes=CAP_BYTES):
    """fuzz48.pack, verbatim semantics."""
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


def bit_visibility(bits, samples, times):
    """Per-bit sampling census on the SIMULATED capture: for every frame
    bit, how many samples landed inside its high pulse. Returns
    (miss1, miss0, merged) where miss1/miss0 = count of 1/0 bits whose
    high pulse received no sample (swallowed), merged = count of adjacent
    1-1 bit pairs whose separating low gap received no sample."""
    nb = len(bits)
    hits = [0] * nb
    lowhit = [0] * nb            # samples in the LOW part of bit k
    for (i, s, lvl), t in zip(samples, times):
        if t < 0:
            continue
        k = int(t // BIT_NS)
        if k >= nb:
            continue
        within = t - k * BIT_NS
        if within < (T1H_NS if bits[k] else T0H_NS):
            hits[k] += 1
        else:
            lowhit[k] += 1
    miss1 = sum(1 for k in range(nb) if bits[k] and not hits[k])
    miss0 = sum(1 for k in range(nb) if not bits[k] and not hits[k])
    merged = sum(1 for k in range(nb - 1)
                 if bits[k] and bits[k + 1] and not lowhit[k])
    return miss1, miss0, merged


# ---- host decoder (decode.c, gcc, ND48/CHK4) ---------------------------

class DecInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_uint8), ("cause", ctypes.c_uint8),
                ("trials", ctypes.c_uint8), ("alias_cmp", ctypes.c_uint8),
                ("chased", ctypes.c_uint8),
                ("n_weak", ctypes.c_uint16), ("n_tied", ctypes.c_uint16),
                ("K", ctypes.c_uint16), ("tau", ctypes.c_int16),
                ("violations", ctypes.c_uint8),
                ("infeasible", ctypes.c_uint16),
                ("label_err", ctypes.c_uint16), ("n_seg", ctypes.c_uint16)]


_LIB = None


def decoder():
    global _LIB
    if _LIB is None:
        _LIB = ctypes.CDLL(str(SC / "decode_host_prod.so"))
        _LIB.ws_decode_ex.restype = ctypes.c_uint8
        _LIB.ws_decode_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                      ctypes.c_char_p]
        _LIB.dec_eps_centi.restype = ctypes.c_int16
    return _LIB


def decode(cap: bytes):
    lib = decoder()
    out = ctypes.create_string_buffer(48)
    st = lib.ws_decode_ex(cap, len(cap), out)
    info = DecInfo.in_dll(lib, "dec_info")
    eps_c = lib.dec_eps_centi() if info.K else 0
    return st, bytes(out.raw), info, eps_c


CAUSE_NAME = {0: "-", 1: "R1lock", 2: "R2marker", 3: "R3infeas",
              4: "R4label", 5: "R5emitgate", 6: "R6nocand", 7: "R7admit",
              8: "R8chase"}


def run_case(data48: bytes, eps: float, t0: float):
    """One synthetic capture end to end. Returns a result dict."""
    bits = frame_bits(data48)
    samples, times = simulate(bits, eps, t0)
    cap = pack(samples)
    st, out, info, eps_c = decode(cap)
    delivered = st in (1, 2) and out == data48
    cat = st in (1, 2) and out != data48
    m1, m0, mg = bit_visibility(bits, samples, times)
    return {
        "eps": eps, "t0": t0, "status": int(st),
        "delivered": bool(delivered), "catastrophic": bool(cat),
        "cause": int(info.cause), "n_weak": int(info.n_weak),
        "n_tied": int(info.n_tied), "trials": int(info.trials),
        "violations": int(info.violations),
        "infeasible": int(info.infeasible),
        "label_err": int(info.label_err),
        "eps_centi": int(eps_c),
        "miss1": m1, "miss0": m0, "merged": mg,
    }
