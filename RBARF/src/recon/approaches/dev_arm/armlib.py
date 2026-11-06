"""Host-side forensics for the arm investigation (INVESTIGATION-ONLY).

* parse the diagnostic image's A/B lines and the driver's send events;
* burst geometry on a raw capture (rising edges, first/last high sample,
  implied bit span -> head chop / tail truncation / buffer overrun);
* re-decode every dump with the SHIPPED v2.3 production constants
  (decode.c, ND_DATA=48 CHECK_EN=1 CHK_LEN=6) -> chip-vs-host divergence;
* fit (chop, t0, eps) against recon/synth.py's calibrated sampler model,
  which is what says whether an R3 is a PARTIAL BURST or a genuine fit
  failure on a complete burst.

data/captures_val.json is never read.
"""
import ctypes
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "bench"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))

from synth import (LOOP_NS, SLOT_OFFSET_NS, BRANCH_COST_NS, BIT_NS,   # noqa
                   T1H_NS, T0H_NS)
from crc import build_payload_v23                                     # noqa
from patterns import HEADER_V23, TRAILER_V23                           # noqa

CAP_BYTES = 288
NBITS = 480                       # 60-byte v2.3 production frame
CAUSE = {0: "-", 1: "R1lock", 2: "R2marker", 3: "R3infeas", 4: "R4labelerr",
         5: "R5emitgate", 6: "R6nocand", 7: "R7admit", 8: "R8chase"}
STATUS = {0: "REFUSE", 1: "DIRECT", 2: "CHASE", 3: "LEGACY"}


# ---- wire ---------------------------------------------------------------

def wire_frame(data48: bytes) -> bytes:
    fr = HEADER_V23 + build_payload_v23(data48) + TRAILER_V23
    assert len(fr) == 60
    return fr


def frame_bits(data48: bytes):
    return [int(b) for byte in wire_frame(data48) for b in f"{byte:08b}"]


# ---- capture layout -----------------------------------------------------

def linearize(raw: bytes):
    """cap_code.s layout -> [(loop, slot, level)] in time order."""
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


def levels(raw: bytes):
    return [v for _, _, v in linearize(raw)]


def sample_time_ns(idx):
    """Nominal wall time of sample idx (loop = idx//8, slot = idx%8),
    ignoring the branch-cost accumulation (used for geometry only)."""
    return (idx // 8) * LOOP_NS + SLOT_OFFSET_NS[idx % 8]


def geometry(raw: bytes):
    """Burst geometry, model-free."""
    lv = levels(raw)
    n = len(lv)
    hi = [i for i, v in enumerate(lv) if v]
    g = {"n_samples": n, "n_high": len(hi)}
    if not hi:
        g.update(n_rise=0, first_hi=None, last_hi=None, span_ns=0.0,
                 span_bits=0.0, tail_zero_loops=len(raw), overrun=False)
        return g
    rises = sum(1 for i in range(1, n) if lv[i] and not lv[i - 1])
    if lv[0]:
        rises += 1
    f, l = hi[0], hi[-1]
    span = sample_time_ns(l) - sample_time_ns(f)
    g.update(n_rise=rises, first_hi=f, last_hi=l, span_ns=span,
             span_bits=span / BIT_NS,
             tail_zero_loops=len(raw) - 1 - (l // 8),
             head_zero_loops=f // 8,
             overrun=(l // 8) >= len(raw) - 2)
    return g


# ---- calibrated sampler model ------------------------------------------

def simulate(bits, eps, phase_ns, n_iter=CAP_BYTES):
    out = []
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
                    lvl = 1 if (t - k * BIT_NS) < (T1H_NS if bits[k]
                                                   else T0H_NS) else 0
            if lvl:
                wsum += BRANCH_COST_NS[s]
            out.append(lvl)
    return out


N_FIT = 250        # loops fitted (the 480-bit frame spans 240)


def _agree(bits, eps, ph, ref):
    sm = simulate(bits, eps, ph, n_iter=N_FIT)
    n = min(len(sm), len(ref))
    return sum(1 for a, b in zip(sm[:n], ref[:n]) if a == b), n


def fit(bits_full, raw, chop_candidates, eps_seed=-0.0107):
    """Best (chop, t0, eps) over the given chop candidates.

    chop = frame bits missing from the HEAD of the burst (the capture's
    first visible rise is bit `chop`).  Returns the best fit dict."""
    ref = levels(raw)[:N_FIT * 8]
    best = None
    for chop in chop_candidates:
        if chop >= len(bits_full):
            continue
        bits = bits_full[chop:]
        b = (-1, None, None)
        for j in range(-4, 5):
            eps = eps_seed + j * 4e-4
            for ph in range(0, 1251, 25):
                a, _ = _agree(bits, eps, float(ph), ref)
                if a > b[0]:
                    b = (a, float(ph), eps)
        a0, ph0, eps0 = b
        sp, se = 12.0, 2e-4
        while sp > 0.05:
            moved = False
            for dp, de in ((sp, 0), (-sp, 0), (0, se), (0, -se),
                           (sp, se), (sp, -se), (-sp, se), (-sp, -se)):
                a, _ = _agree(bits, eps0 + de, ph0 + dp, ref)
                if a > a0:
                    a0, ph0, eps0 = a, ph0 + dp, eps0 + de
                    moved = True
            if not moved:
                sp /= 2.0
                se /= 2.0
        rec = {"chop": chop, "t0_ns": round(ph0, 1), "eps": round(eps0, 6),
               "agree": round(a0 / len(ref), 5)}
        if best is None or rec["agree"] > best["agree"]:
            best = rec
    return best


# ---- the shipped-constants host decoder (decode.c ND48/CHK6) -----------

class DecInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_uint8), ("cause", ctypes.c_uint8),
                ("trials", ctypes.c_uint8), ("alias_cmp", ctypes.c_uint8),
                ("chased", ctypes.c_uint8),
                ("n_weak", ctypes.c_uint16), ("n_tied", ctypes.c_uint16),
                ("K", ctypes.c_uint16), ("tau", ctypes.c_int16),
                ("violations", ctypes.c_uint8),
                ("infeasible", ctypes.c_uint16),
                ("label_err", ctypes.c_uint16), ("n_seg", ctypes.c_uint16),
                ("comps", ctypes.c_uint8), ("n_refs", ctypes.c_uint8),
                ("ref_split", ctypes.c_uint8)]


_LIB = None


def decode(cap: bytes, ncap=None):
    global _LIB
    if _LIB is None:
        _LIB = ctypes.CDLL(str(SC / "dec48_v23.so"))
        _LIB.ws_decode_ex.restype = ctypes.c_uint8
        _LIB.ws_decode_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint16,
                                      ctypes.c_char_p]
        _LIB.dec_eps_centi.restype = ctypes.c_int16
    out = ctypes.create_string_buffer(48)
    st = _LIB.ws_decode_ex(cap, ncap or len(cap), out)
    info = DecInfo.in_dll(_LIB, "dec_info")
    eps_c = _LIB.dec_eps_centi() if info.K else 0
    return st, bytes(out.raw)[:48], info, eps_c


# ---- run-file parsing ---------------------------------------------------

def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def parse_A(line):
    h = line[1:]
    if len(h) != 28:
        return None
    b = bytes.fromhex(h)
    return {
        "status": b[0] >> 4, "cause": b[0] & 0x0F,
        "eps_centi": s16((b[1] << 8) | b[2]),
        "t_arm0": (b[3] << 8) | b[4], "t_arm1": (b[5] << 8) | b[6],
        "t_r0": (b[7] << 8) | b[8], "t_r1": (b[9] << 8) | b[10],
        "n_timeout": b[11], "t_prev_arm1": (b[12] << 8) | b[13],
    }


def u16d(a, b):
    """(a - b) mod 2**16 -- TIM2 is a 65.536 ms free-running us counter."""
    return (a - b) & 0xFFFF


def load_run(path):
    """-> list of rows, each {pattern, rep, sent, tel, cap|None, ...}."""
    import json
    d = json.loads(Path(path).read_text())
    ev = d["events"]
    rows = []
    pend = None
    ei = 0
    for s in d["stream"]:
        ln, t = s["line"], s["t"]
        if ln.startswith("A") and len(ln) == 29:
            while ei < len(ev) and ev[ei]["t_send"] <= t:
                pend = ev[ei]
                ei += 1
            tel = parse_A(ln)
            if tel is None:
                continue
            rows.append({"pattern": pend["pattern"] if pend else None,
                         "rep": pend["rep"] if pend else None,
                         "sent": pend["sent"] if pend else None,
                         "i": pend["i"] if pend else None,
                         "t_report": t,
                         "t_send": pend["t_send"] if pend else None,
                         "tel": tel, "cap": None})
        elif ln.startswith("B") and rows:
            rows[-1]["cap"] = ln[1:]
    # frames that produced no report at all
    seen = {r["i"] for r in rows}
    nore = [e for e in ev if e["i"] not in seen]
    return d["meta"], rows, nore
