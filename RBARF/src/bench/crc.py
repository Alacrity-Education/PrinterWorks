"""CRC primitives for the RBARF wire protocol v2.3.

The v2.3 payload carries a **6-byte** check block appended after the data
bytes: one CRC-16 written three times, high byte first each time::

    payload' = DATA || C16_HI C16_LO || C16_HI C16_LO || C16_HI C16_LO

``CRC16`` is CRC-16/CCITT-FALSE — poly 0x1021, init 0xFFFF, no input or
output reflection, xorout 0x0000 — computed over the **DATA bytes only**.
Standard check value: ``CRC16("123456789") = 0x29B1``.

    frame = HEADER(3) || payload'(N+6) || TRAILER(3)

    build       DATA   payload'   frame
    ----------  ----   --------   ------------------------------------
    bench/test    16         22   3 + 22 + 3 = 28
    production    48         54   3 + 54 + 3 = 60 = EXACTLY 20 LEDs

Why a 16-bit check, three copies, per-byte majority
---------------------------------------------------
1. **Strength.**  v2.2's 8-bit check accepted a wrong chase candidate
   with probability ~1/256 per trial, which made a wide search
   unaffordable: at the 0.2 % wrong-emission target the CRC8 could not
   pay for even ONE wrong trial (``fa_budget(0.002, 1)`` = 0 under
   :func:`fa_prob_crc8`).  A 16-bit check is 256x stronger per trial —
   p_trial = R/65536 — and buys ~131 wrong trials at the same target.
   That is what makes the v2.3 design goal (**almost always emit**;
   refusals lose the frame outright under single-transmission delivery)
   affordable: emit even on an imperfect reconstruction, provided the
   16-bit check validates the payload.  :func:`fa_prob` / :func:`fa_table`
   / :func:`fa_budget` state that price honestly for any budget.

2. **Redundancy.**  The check block rides the same corrupted channel as
   the data — it is exactly as exposed to reconstruction error as the
   bytes it protects, and a mangled check byte would poison *every*
   chase trial, turning a recoverable frame into a lost one.  Three
   copies fix that.

3. **Per-byte majority, not per-block.**  The reference is recovered
   **independently for each byte position**::

       reference_HI = majority(H1, H2, H3)
       reference_LO = majority(L1, L2, L3)

   Per byte position the truth **survives as the majority** when >= 2 of
   the 3 copies are correct there, and **remains a candidate** when >= 1
   is.  That is strictly stronger than voting on the 16-bit value as a
   unit: two copies damaged in *different* byte positions (one HI, one
   LO) leave three distinct 16-bit blocks — no block-level majority at
   all — yet both per-byte votes still carry 2 good votes and the exact
   reference comes back.  See :func:`majority_byte`,
   :func:`reference_bytes_v23`.

4. **Bounded candidate enumeration.**  A byte position with no majority
   (all three copies differ there) contributes its distinct values as
   candidates, ranked by decode confidence; the references are the cross
   product, capped at ``REF_MAX_V23`` = 9 = 3 HI x 3 LO — the geometric
   maximum, so the cap never truncates a 3-copy block and exists as a
   hard bound for the on-chip port.  A decoder on a tighter budget may
   pass a smaller ``cap`` (or ``allow_split_vote=False`` to refuse
   instead).  Even the worst case is cheap: 9/65536 = 0.014 % per trial,
   still 28x safer than v2.2's *best* case.

5. **Exact LED tiling (the pad law).**  A Klipper ``neopixel`` chain is
   configured in 3-byte LEDs and any surplus wire byte inflates the
   decoder's whole-burst clock fit by ~1.6 %/byte — one pad byte is
   enough to force a refusal (measured: ``bench/pad_law.py``,
   ``recon/PROD_CLOSURE.md`` SS9.4).  3 + 48 + 6 + 3 = 60 bytes = exactly
   20 LEDs, so no pad byte can exist.  This is why the marker trim (8
   marker bytes -> 6) and the check-block growth (4 -> 6) had to happen
   together.

**CRC8 is GONE from v2.3.**  It went out with v2.2's 4-byte block; there
is no CRC8 anywhere on the v2.3 wire.  Every CRC8 helper below is kept
only as an explicitly labeled **compat mode** so the acquired
``captures_v21*.json`` / ``captures_v22*.json`` corpora and their parity
harnesses stay reproducible: ``crc8_smbus``, ``check_block``,
``build_payload``, ``split_payload``, ``majority``,
``reference_candidates``, ``verify_payload``, ``verify_intact`` (4-byte
v2.2 default, ``n=3`` for v2.1) and ``fa_prob_crc8`` / ``fa_table_crc8``.
Do not build new frames with them.  Note that ``fa_prob`` itself is now
the **16-bit** v2.3 function; the CRC8 numbers quoted in
``recon/EMBEDDED_V2_SPEC.md`` SS7.6/SS7.10 (e.g. ``fa_prob(9, 1)`` =
3.46 %) live under ``fa_prob_crc8`` from v2.3 on.

Both a table-driven variant (fast, used by the bench) and a table-free
bitwise variant (the reference an on-chip port mirrors, where a 512-byte
table does not fit the flash budget) are provided for CRC16 as well, and
are cross-checked against each other in the self-test below.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

# --- v2.3 (current) ---------------------------------------------------------
CRC16_POLY = 0x1021
CRC16_INIT = 0xFFFF
CRC16_XOROUT = 0x0000

CHECK_COPIES_V23 = 3         # the CRC16 is written three times
CHECK_BLOCK_LEN_V23 = 6      # 3 copies x (HI, LO)
REF_MAX_V23 = 9              # hard cap on the reference cross product

# --- superseded, compat only ------------------------------------------------
CRC8_POLY = 0x07
CRC8_INIT = 0x00

CHECK_BLOCK_LEN = 4          # v2.2: [CRC8] * 4          (compat)
CHECK_BLOCK_LEN_V21 = 3      # v2.1: [CRC8] * 3          (compat)


# ==========================================================================
# CRC-16/CCITT-FALSE  --  the v2.3 check
# ==========================================================================

def crc16_ccitt_false_bitwise(data: Iterable[int]) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), table-free.

    8 shifts per byte, no RAM/flash table.  This is the reference an
    on-chip chase loop mirrors, and the shape the Klipper Jinja macro
    ports bit for bit (Jinja has no bitwise operators at all).
    """
    crc = CRC16_INIT
    for byte in data:
        crc ^= (byte & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc ^ CRC16_XOROUT


def _make_crc16_table() -> tuple:
    table = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF if crc & 0x8000 \
                else (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)


CRC16_TABLE = _make_crc16_table()


def crc16_ccitt_false_table(data: Iterable[int]) -> int:
    crc = CRC16_INIT
    for byte in data:
        crc = ((crc << 8) & 0xFFFF) ^ CRC16_TABLE[((crc >> 8) ^ byte) & 0xFF]
    return crc ^ CRC16_XOROUT


def crc16_ccitt_false(data: Iterable[int]) -> int:
    """CRC-16/CCITT-FALSE over ``data``.  Check: ``'123456789'`` -> 0x29B1."""
    return crc16_ccitt_false_table(data)


# ==========================================================================
# v2.3 check block
# ==========================================================================

def check_block_v23(data: bytes) -> bytes:
    """The 6-byte v2.3 check block for ``data``.

    ``C16_HI C16_LO`` three times over — the SAME CRC16, byte order
    HI, LO in every copy.
    """
    c16 = crc16_ccitt_false(data)
    hi, lo = (c16 >> 8) & 0xFF, c16 & 0xFF
    return bytes((hi, lo) * CHECK_COPIES_V23)


def build_payload_v23(data: bytes) -> bytes:
    """``DATA || (C16_HI C16_LO) * 3`` — the v2.3 payload for ``data``."""
    data = bytes(data)
    return data + check_block_v23(data)


def split_payload_v23(payload: bytes) -> Tuple[bytes, bytes]:
    """Split a v2.3 payload into ``(data, check_block)``."""
    if len(payload) < CHECK_BLOCK_LEN_V23:
        raise ValueError(f"payload too short: {len(payload)} bytes")
    n = CHECK_BLOCK_LEN_V23
    return bytes(payload[:-n]), bytes(payload[-n:])


# --------------------------------------------------------------------------
# Per-byte majority reference recovery
# --------------------------------------------------------------------------

HI_IDX = (0, 2, 4)           # wire positions of the three C16_HI copies
LO_IDX = (1, 3, 5)           # wire positions of the three C16_LO copies


def majority_byte(votes: Sequence[int]) -> Optional[int]:
    """The value holding >= 2 of the three votes, else ``None``.

    With three votes at most one value can reach two, so there is no tie
    case: either a unique majority exists or all three votes differ.
    On target this is the same three-compare counting loop v2.2 used,
    run once per byte position instead of once per block.
    """
    if len(votes) != CHECK_COPIES_V23:
        raise ValueError(f"expected {CHECK_COPIES_V23} votes, "
                         f"got {len(votes)}")
    vals = [v & 0xFF for v in votes]
    for v in vals:
        if vals.count(v) >= 2:
            return v
    return None


def reference_bytes_v23(check: Sequence[int]
                        ) -> Tuple[Optional[int], Optional[int]]:
    """``(reference_HI, reference_LO)`` by INDEPENDENT per-byte majority.

    Each element is the >= 2-of-3 majority of that byte position across
    the three copies, or ``None`` when all three copies differ there.

    This independence is the whole point of the v2.3 policy: two copies
    damaged in *different* byte positions leave no block-level majority
    at all, yet both per-byte votes still carry two good votes, so the
    exact 16-bit reference comes back.
    """
    if len(check) != CHECK_BLOCK_LEN_V23:
        raise ValueError(f"check block must be {CHECK_BLOCK_LEN_V23} bytes, "
                         f"not {len(check)}")
    hi = majority_byte([check[i] for i in HI_IDX])
    lo = majority_byte([check[i] for i in LO_IDX])
    return hi, lo


def _ranked_bytes(check: Sequence[int], idx: Sequence[int],
                  confidence: Optional[Sequence[float]]
                  ) -> List[Tuple[int, float]]:
    """Candidates for one byte position as ``[(value, confidence)]``.

    A majority collapses the list to one entry.  Otherwise every
    distinct value is a candidate, ordered by the best confidence among
    the copies carrying it (descending; ties keep wire order), each
    keeping that best confidence as its score.
    """
    votes = [check[i] & 0xFF for i in idx]
    maj = majority_byte(votes)
    if maj is not None:
        conf = max((confidence[i] for i in idx
                    if (check[i] & 0xFF) == maj), default=0.0) \
            if confidence is not None else 0.0
        return [(maj, conf)]
    order = range(len(idx)) if confidence is None else \
        sorted(range(len(idx)), key=lambda j: (-confidence[idx[j]], j))
    out: List[Tuple[int, float]] = []
    for j in order:
        v = votes[j]
        if all(v != have for have, _ in out):
            c = confidence[idx[j]] if confidence is not None else 0.0
            out.append((v, c))
    return out


def reference_candidates_v23(check: Sequence[int],
                             confidence: Optional[Sequence[float]] = None,
                             cap: int = REF_MAX_V23) -> List[int]:
    """Ordered 16-bit chase references for a v2.3 check block.

    * **Both byte positions have a majority** (the normal case): a
      single-element list holding ``(HI << 8) | LO``.  One reference,
      p_trial = 1/65536.
    * **A byte position has no majority** (all three copies differ
      there): its distinct values become candidates ranked by decode
      confidence, and the references are the **cross product** of the
      two positions' candidate lists — 3 references when one position
      splits, 9 when both do.  Pairs are ordered by the sum of the two
      byte confidences (descending), tie-broken by per-position rank, so
      with no ``confidence`` supplied the order is the wire-order cross
      product, which is arbitrary — a decoder that has per-byte
      confidence SHOULD pass it (6 values, wire order
      ``H1 L1 H2 L2 H3 L3``).

    The list is truncated to ``cap`` entries (default ``REF_MAX_V23`` = 9
    = 3 x 3, the geometric maximum, so the default never truncates).
    Every extra reference tried multiplies the per-trial false-accept
    exposure: see :func:`fa_prob`.
    """
    if confidence is not None and len(confidence) != CHECK_BLOCK_LEN_V23:
        raise ValueError(f"confidence must be {CHECK_BLOCK_LEN_V23} values")
    if cap < 1:
        raise ValueError("cap must be >= 1")
    his = _ranked_bytes(check, HI_IDX, confidence)
    los = _ranked_bytes(check, LO_IDX, confidence)
    pairs = []
    for a, (hi, ch) in enumerate(his):
        for b, (lo, cl) in enumerate(los):
            pairs.append((-(ch + cl), a, b, (hi << 8) | lo))
    pairs.sort()
    return [p[3] for p in pairs[:cap]]


def verify_payload_v23(payload: bytes,
                       confidence: Optional[Sequence[float]] = None,
                       allow_split_vote: bool = True,
                       cap: int = REF_MAX_V23) -> bool:
    """Verify a v2.3 payload the way the receiver does.

    CRC16 over the data bytes must equal one of the references from
    :func:`reference_candidates_v23` — i.e. the per-byte majority
    reference, or (when a byte position has no majority and
    ``allow_split_vote`` is set) any of the ranked cross-product
    candidates.

    ``allow_split_vote=False`` is the strict policy: if either byte
    position lacks a majority, refuse.  Note this pulls against the
    v2.3 design goal — a refusal loses the frame outright, and the
    16-bit check is what makes the wide search safe — so the default
    is to enumerate.
    """
    data, check = split_payload_v23(payload)
    hi, lo = reference_bytes_v23(check)
    if not allow_split_vote and (hi is None or lo is None):
        return False
    return crc16_ccitt_false(data) in reference_candidates_v23(
        check, confidence, cap)


def verify_intact_v23(payload: bytes) -> bool:
    """Strictest check: all three copies present, equal, and correct.

    Used by the bench and by ``patterns.py`` to prove a payload came off
    the builder untouched — not the receiver policy (the receiver must
    tolerate corrupted check bytes; see :func:`verify_payload_v23`).
    """
    data, check = split_payload_v23(payload)
    return bytes(check) == check_block_v23(data)


# ==========================================================================
# False-accept math (v2.3, 16-bit check)
# State these numbers wherever a chase budget is picked.
# ==========================================================================

def fa_prob(trials: int, references: int = 1) -> float:
    """P(at least one false accept) over ``trials`` wrong chase candidates.

    A 16-bit check accepts a wrong candidate with probability 2^-16 per
    reference, so with ``references`` distinct references in play::

        p_trial = references / 65536
        P(>=1)  = 1 - (1 - p_trial) ** trials

    ``references`` is 1 in the normal case (both check-byte positions
    carry a per-byte majority), 3 when one position has no majority and
    the decoder tries its three candidates, and up to
    ``REF_MAX_V23`` = 9 when both positions split.

    This is an upper bound on the *residual* risk in the sense that
    matters here: it counts only candidates that are wrong AND actually
    evaluated, and it treats their CRC16 values as uniform.  The chase
    stops at its first match, so only wrong candidates examined *before*
    the true one are exposed, and the structural guarantees below make
    it pessimistic for near-miss candidates.

    Structural detection that is NOT a coin flip, from the polynomial
    x^16+x^12+x^5+1:
      * every single-bit error is detected;
      * every burst error up to 16 bits long is detected;
      * every 2-bit error is detected for datawords far longer than
        ours (ord(x) mod the poly is 32767 bits);
      * every ODD-weight error is detected: x^16+x^12+x^5+1 has four
        terms, so P(1) = 0 and 0x11021 IS divisible by (x+1) —
        0x11021 = (x+1) * 0xF01F, with the degree-15 cofactor PRIMITIVE
        (ord(x) mod 0xF01F = 2^15-1 = 32767).  [CORRECTION, 2026-09-07:
        this docstring previously claimed the opposite.  The claim was
        load-bearing — the decoder's chase skips a data-only trial phase
        whose weight parity cannot match the reference, which is only
        exact BECAUSE every single-bit syndrome has odd parity — and it
        is now verified numerically in embedded_v2._selftest(): the
        (x+1) division, the cofactor's order, and odd parity for all
        128 + 384 single-bit syndromes.]
      * ord(x) mod 0x11021 = 32767, so all 384 production (128 bench)
        data-bit syndromes are DISTINCT — which is why the v2.2 SS7.7
        alias guard is retired in v2.3 rather than ported.
      * HD = 4 out to 32751 bits, i.e. every 3-bit error is caught at
        our 128-bit bench and 384-bit production dataword lengths, which
        the 8-bit check could not promise past 119 bits.  Weight-4
        undetectable codewords DO exist at these lengths (that is what
        HD = 4 means): they are the irreducible floor, and the v2.3
        wrong-emission measurement found exactly that -- every wrong
        emission was one.

    For the CRC8 numbers of the superseded v2.2 wire, use
    :func:`fa_prob_crc8`.
    """
    if trials < 0:
        raise ValueError("trials must be >= 0")
    if not 1 <= references <= REF_MAX_V23:
        raise ValueError(f"references must be 1..{REF_MAX_V23}")
    return 1.0 - (1.0 - references / 65536.0) ** trials


def fa_budget(target: float, references: int = 1) -> int:
    """Largest wrong-trial count whose false-accept risk stays <= ``target``.

    The v2.3 design goal is to almost always emit, with the measured
    wrong-emission rate held at <= 0.2 % of emissions.  This inverts
    :func:`fa_prob` so a chase budget can be read straight off that
    target instead of argued about::

        fa_budget(0.002, 1) = 131 wrong trials      (16-bit check)
        fa_prob_crc8 equivalent = 0 wrong trials    (8-bit check)

    i.e. the 16-bit check is what makes a wide search affordable at all.
    """
    if not 0.0 <= target < 1.0:
        raise ValueError("target must be in [0, 1)")
    if not 1 <= references <= REF_MAX_V23:
        raise ValueError(f"references must be 1..{REF_MAX_V23}")
    t = 0
    while fa_prob(t + 1, references) <= target:
        t += 1
    return t


def fa_table(budgets: Sequence[int] = (1, 4, 16, 64, 131, 256, 1024)) -> str:
    """Human-readable v2.3 false-accept table (16-bit check)."""
    lines = ["  trials   1 reference   3 refs (1 byte split)   "
             "9 refs (both split)",
             "  ------   -----------   --------------------   "
             "-------------------"]
    for t in budgets:
        lines.append(f"  {t:6d}   {fa_prob(t, 1) * 100:10.4f}%   "
                     f"{fa_prob(t, 3) * 100:20.4f}%   "
                     f"{fa_prob(t, 9) * 100:18.4f}%")
    return "\n".join(lines)


# ==========================================================================
# ==========================================================================
#  COMPAT MODES BELOW -- superseded v2.2 / v2.1 CRC8 wire.
#  Kept ONLY so the acquired captures_v21*.json / captures_v22*.json
#  corpora and their parity harnesses stay reproducible.  There is no
#  CRC8 anywhere in v2.3; do not build new frames with any of this.
# ==========================================================================
# ==========================================================================

def crc8_smbus_bitwise(data: Iterable[int]) -> int:
    """COMPAT (v2.2/v2.1): CRC-8/SMBUS (poly 0x07, init 0x00), table-free."""
    crc = CRC8_INIT
    for byte in data:
        crc ^= byte & 0xFF
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ CRC8_POLY) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def _make_crc8_table() -> tuple:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = ((crc << 1) ^ CRC8_POLY) & 0xFF if crc & 0x80 \
                else (crc << 1) & 0xFF
        table.append(crc)
    return tuple(table)


CRC8_TABLE = _make_crc8_table()


def crc8_smbus_table(data: Iterable[int]) -> int:
    crc = CRC8_INIT
    for byte in data:
        crc = CRC8_TABLE[(crc ^ byte) & 0xFF]
    return crc


def crc8_smbus(data: Iterable[int]) -> int:
    """COMPAT (v2.2/v2.1): CRC-8/SMBUS.  Check: ``'123456789'`` -> 0xF4."""
    return crc8_smbus_table(data)


def check_block(data: bytes, n: int = CHECK_BLOCK_LEN) -> bytes:
    """COMPAT: the ``n``-byte CRC8 check block — ``[CRC8] * n``.

    ``n=4`` rebuilds v2.2 blocks, ``n=3`` v2.1 blocks.  v2.3 uses
    :func:`check_block_v23`.
    """
    if n not in (CHECK_BLOCK_LEN_V21, CHECK_BLOCK_LEN):
        raise ValueError(f"check block length must be 3 or 4, not {n}")
    c8 = crc8_smbus(data)
    return bytes((c8,) * n)


def build_payload(data: bytes, n: int = CHECK_BLOCK_LEN) -> bytes:
    """COMPAT: ``DATA || [CRC8]*n`` (v2.2 default n=4, v2.1 n=3)."""
    data = bytes(data)
    return data + check_block(data, n)


def split_payload(payload: bytes, n: int = CHECK_BLOCK_LEN
                  ) -> Tuple[bytes, bytes]:
    """COMPAT: split a CRC8 payload into ``(data, check_block)``."""
    if len(payload) < n:
        raise ValueError(f"payload too short: {len(payload)} bytes")
    return bytes(payload[:-n]), bytes(payload[-n:])


def majority(check: Sequence[int]) -> Optional[int]:
    """COMPAT (v2.2/v2.1): unique >= 2-vote byte-equality majority.

    Returns ``None`` when no value reaches 2 votes (all differ) or when
    TWO distinct values do (the 2-2 tie, possible only at n=4).  At n=3
    this is exactly the old 2-of-3 rule.

    v2.3 replaces this whole-block vote with the independent PER-BYTE
    majority of :func:`reference_bytes_v23`.
    """
    n = len(check)
    if n not in (CHECK_BLOCK_LEN_V21, CHECK_BLOCK_LEN):
        raise ValueError(f"check block must be 3 or 4 bytes, not {n}")
    vals = [x & 0xFF for x in check]
    win = None
    for v in vals:
        if vals.count(v) >= 2:
            if win is None:
                win = v
            elif v != win:
                return None          # 2-2 tie: two distinct >=2-vote values
    return win


def reference_candidates(check: Sequence[int],
                         confidence: Optional[Sequence[float]] = None
                         ) -> List[int]:
    """COMPAT (v2.2/v2.1): ordered 8-bit chase references for ``check``.

    Majority present -> a single-element list.  No majority (2-2 tie or
    all differ) -> the distinct candidate values in descending
    ``confidence`` order, ties keeping wire order.  v2.3 uses
    :func:`reference_candidates_v23`.
    """
    maj = majority(check)
    if maj is not None:
        return [maj]
    vals = [x & 0xFF for x in check]
    n = len(vals)
    if confidence is None:
        order = range(n)
    else:
        if len(confidence) != n:
            raise ValueError(f"confidence must be {n} values")
        order = sorted(range(n), key=lambda i: (-confidence[i], i))
    out: List[int] = []
    for i in order:
        if vals[i] not in out:
            out.append(vals[i])
    return out


def verify_payload(payload: bytes,
                   confidence: Optional[Sequence[float]] = None,
                   allow_split_vote: bool = True,
                   n: int = CHECK_BLOCK_LEN) -> bool:
    """COMPAT (v2.2/v2.1): receiver-side CRC8 check."""
    data, check = split_payload(payload, n)
    if not allow_split_vote and majority(check) is None:
        return False
    return crc8_smbus(data) in reference_candidates(check, confidence)


def verify_intact(payload: bytes, n: int = CHECK_BLOCK_LEN) -> bool:
    """COMPAT (v2.2/v2.1): all ``n`` check bytes present, equal, correct."""
    data, check = split_payload(payload, n)
    return bytes(check) == check_block(data, n)


def fa_prob_crc8(trials: int, references: int = 1) -> float:
    """COMPAT (v2.2/v2.1): false-accept probability for the **8-bit** check.

        p_trial = references / 256

    ``references`` is 1 with a >= 2-of-4 majority, 2 in the 2-2 tie
    fallback and 4 on a full split.  These are the numbers quoted in
    ``recon/EMBEDDED_V2_SPEC.md`` SS7.6/SS7.10 (``fa_prob(9, 1)`` =
    3.46 % there, now this function); v2.3's :func:`fa_prob` is the
    16-bit one.
    """
    if trials < 0:
        raise ValueError("trials must be >= 0")
    if not 1 <= references <= 4:
        raise ValueError("references must be 1..4")
    return 1.0 - (1.0 - references / 256.0) ** trials


def fa_table_crc8(budgets: Sequence[int] = (1, 4, 16, 64, 256, 1024)) -> str:
    """COMPAT (v2.2/v2.1): the 8-bit false-accept table."""
    lines = ["  trials   1 reference   2 refs (2-2 tie)   4 refs (full split)",
             "  ------   -----------   ----------------   -------------------"]
    for t in budgets:
        lines.append(f"  {t:6d}   {fa_prob_crc8(t, 1) * 100:10.4f}%   "
                     f"{fa_prob_crc8(t, 2) * 100:15.4f}%   "
                     f"{fa_prob_crc8(t, 4) * 100:18.4f}%")
    return "\n".join(lines)


# ==========================================================================
# Self-test
# ==========================================================================

if __name__ == "__main__":
    CHECK = b"123456789"

    # ---------------------------------------------------------------- v2.3
    # The standard CRC-16/CCITT-FALSE check value.
    assert crc16_ccitt_false(CHECK) == 0x29B1, \
        f"CRC16 check value: {crc16_ccitt_false(CHECK):#06x} != 0x29b1"
    assert crc16_ccitt_false_bitwise(CHECK) == 0x29B1, \
        f"CRC16 bitwise check: {crc16_ccitt_false_bitwise(CHECK):#06x}"
    assert crc16_ccitt_false_table(CHECK) == 0x29B1

    # Empty input = the init value (no xorout).
    assert crc16_ccitt_false(b"") == 0xFFFF
    assert crc16_ccitt_false_bitwise(b"") == 0xFFFF

    VECTORS = [
        b"\x00",
        b"\xff",
        b"\x00" * 16,
        b"\xff" * 16,
        b"\xaa" * 16,
        bytes(range(16)),
        bytes(range(48)),
        bytes(((i * 5) & 0xFF) for i in range(48)),
        b"A",
        b"RBARF",
    ]
    for v in VECTORS:
        assert crc16_ccitt_false(v) == crc16_ccitt_false_bitwise(v), v.hex()

    # Table vs bitwise over pseudorandom data of every length 0..64.
    x = 0x1234
    for n in range(65):
        buf = bytearray()
        for _ in range(n):
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
            buf.append((x >> 16) & 0xFF)
        b = bytes(buf)
        assert crc16_ccitt_false(b) == crc16_ccitt_false_bitwise(b), n

    # Structural: every single-bit error changes the CRC16.
    for v in VECTORS:
        if not v:
            continue
        base = crc16_ccitt_false(v)
        for i in range(len(v)):
            for bit in range(8):
                bad = bytearray(v)
                bad[i] ^= 1 << bit
                assert crc16_ccitt_false(bytes(bad)) != base, (v.hex(), i, bit)

    # Structural: HD >= 4 at our lengths -> every 2-bit error is detected.
    for v in (bytes(16), bytes(range(16))):
        base = crc16_ccitt_false(v)
        nb = 8 * len(v)
        for a in range(nb):
            for b_ in range(a + 1, nb):
                bad = bytearray(v)
                bad[a >> 3] ^= 1 << (7 - (a & 7))
                bad[b_ >> 3] ^= 1 << (7 - (b_ & 7))
                assert crc16_ccitt_false(bytes(bad)) != base, (a, b_)

    # ---- v2.3 check block ---------------------------------------------
    for v in VECTORS:
        blk = check_block_v23(v)
        c16 = crc16_ccitt_false(v)
        hi, lo = (c16 >> 8) & 0xFF, c16 & 0xFF
        assert len(blk) == CHECK_BLOCK_LEN_V23 == 6
        assert blk == bytes((hi, lo, hi, lo, hi, lo)), v.hex()
        # HI, LO order in every copy; the same value three times.
        assert all(blk[i] == hi for i in HI_IDX)
        assert all(blk[i] == lo for i in LO_IDX)

        payload = build_payload_v23(v)
        assert payload == bytes(v) + blk
        assert split_payload_v23(payload) == (bytes(v), blk)
        assert verify_intact_v23(payload), v.hex()
        assert verify_payload_v23(payload), v.hex()
        assert verify_payload_v23(payload, allow_split_vote=False), v.hex()
        assert reference_bytes_v23(blk) == (hi, lo)
        assert reference_candidates_v23(blk) == [c16]

        # Every single-bit flip in the DATA must be rejected.
        for i in range(len(v)):
            for bit in range(8):
                bad = bytearray(payload)
                bad[i] ^= 1 << bit
                assert not verify_payload_v23(bytes(bad)), (v.hex(), i, bit)

        # ONE fully corrupted copy (both its bytes) is harmless: each
        # byte position still has 2 good votes.
        for cp in range(CHECK_COPIES_V23):
            for m in (0x01, 0x80, 0xFF):
                bad = bytearray(payload)
                bad[len(v) + 2 * cp] ^= m
                bad[len(v) + 2 * cp + 1] ^= m
                chk = bytes(bad[-CHECK_BLOCK_LEN_V23:])
                assert reference_bytes_v23(chk) == (hi, lo), (v.hex(), cp, m)
                assert reference_candidates_v23(chk) == [c16]
                assert verify_payload_v23(bytes(bad)), (v.hex(), cp, m)
                assert verify_payload_v23(bytes(bad), allow_split_vote=False)

        # THE HEADLINE: three copies damaged in DIFFERENT byte positions.
        # copy0's HI, copy1's LO, copy2 untouched (and every rotation):
        # no two 16-bit blocks are equal, so a v2.2-style BLOCK majority
        # has nothing to vote on -- yet each byte position still carries
        # two good votes, so the exact 16-bit reference comes back.
        for a in range(CHECK_COPIES_V23):
            for b_ in range(CHECK_COPIES_V23):
                if a == b_:
                    continue
                bad = bytearray(payload)
                bad[len(v) + 2 * a] ^= 0x5A          # damage copy a's HI
                bad[len(v) + 2 * b_ + 1] ^= 0xA5     # damage copy b's LO
                chk = bytes(bad[-CHECK_BLOCK_LEN_V23:])
                blocks = [(chk[2 * i] << 8) | chk[2 * i + 1]
                          for i in range(CHECK_COPIES_V23)]
                assert len(set(blocks)) == 3, (v.hex(), a, b_, blocks)
                assert reference_bytes_v23(chk) == (hi, lo), (v.hex(), a, b_)
                assert reference_candidates_v23(chk) == [c16]
                assert verify_payload_v23(bytes(bad)), (v.hex(), a, b_)
                assert verify_payload_v23(bytes(bad), allow_split_vote=False)

        # One byte position with NO majority (all three HI copies differ):
        # 3 candidates x 1 = 3 references, the truth among them.
        bad = bytearray(payload)
        bad[len(v) + 0] ^= 0x01
        bad[len(v) + 2] ^= 0x02
        chk = bytes(bad[-CHECK_BLOCK_LEN_V23:])
        assert reference_bytes_v23(chk) == (None, lo), (v.hex(), chk.hex())
        cands = reference_candidates_v23(chk)
        assert len(cands) == 3 and c16 in cands, (v.hex(), cands)
        assert verify_payload_v23(bytes(bad)), v.hex()
        assert not verify_payload_v23(bytes(bad), allow_split_vote=False)
        # Confidence ranking puts the intact copy's byte first.
        ranked = reference_candidates_v23(
            chk, confidence=(0.1, 0.9, 0.2, 0.9, 0.9, 0.9))
        assert ranked[0] == c16, (v.hex(), [hex(r) for r in ranked])

        # BOTH byte positions split -> the full 3x3 cross product.
        bad = bytearray(payload)
        bad[len(v) + 0] ^= 0x01
        bad[len(v) + 2] ^= 0x02
        bad[len(v) + 1] ^= 0x04
        bad[len(v) + 3] ^= 0x08
        chk = bytes(bad[-CHECK_BLOCK_LEN_V23:])
        assert reference_bytes_v23(chk) == (None, None), v.hex()
        cands = reference_candidates_v23(chk)
        assert len(cands) == REF_MAX_V23 == 9, (v.hex(), cands)
        assert len(set(cands)) == 9
        assert c16 in cands, (v.hex(), [hex(r) for r in cands])
        assert verify_payload_v23(bytes(bad)), v.hex()
        assert not verify_payload_v23(bytes(bad), allow_split_vote=False)
        # The cap truncates the product, and a too-small cap can lose the
        # truth -- that is the trade a tight budget makes, stated openly.
        assert len(reference_candidates_v23(chk, cap=4)) == 4
        assert reference_candidates_v23(chk, cap=9) == cands
        # Confidence ranking floats the intact copy (copy 2) to the top.
        ranked = reference_candidates_v23(
            chk, confidence=(0.1, 0.1, 0.2, 0.2, 0.9, 0.9))
        assert ranked[0] == c16, (v.hex(), [hex(r) for r in ranked])
        assert verify_payload_v23(bytes(bad),
                                 confidence=(0.1, 0.1, 0.2, 0.2, 0.9, 0.9),
                                 cap=1), v.hex()

    # ---- per-byte majority truth table --------------------------------
    assert majority_byte((0x11, 0x11, 0x11)) == 0x11      # unanimous
    assert majority_byte((0x11, 0x11, 0x22)) == 0x11      # 2-1
    assert majority_byte((0x11, 0x22, 0x11)) == 0x11
    assert majority_byte((0x22, 0x11, 0x11)) == 0x11
    assert majority_byte((0x11, 0x22, 0x33)) is None      # all differ
    try:
        majority_byte((0x11, 0x22))
    except ValueError:
        pass
    else:
        raise AssertionError("majority_byte accepted 2 votes")

    # HI/LO independence, spelled out on one block.
    #   copy0 = 12 34   copy1 = 99 34   copy2 = 12 88
    #   -> blocks 0x1234, 0x9934, 0x1288 : all distinct (no block majority)
    #   -> HI votes 12,99,12 -> 0x12 ; LO votes 34,34,88 -> 0x34
    blk = bytes((0x12, 0x34, 0x99, 0x34, 0x12, 0x88))
    assert reference_bytes_v23(blk) == (0x12, 0x34)
    assert reference_candidates_v23(blk) == [0x1234]
    # A vote on the 16-bit blocks AS UNITS has nothing to decide here:
    _blocks = [0x1234, 0x9934, 0x1288]
    assert all(_blocks.count(b_) < 2 for b_ in _blocks)

    # ---- reference ranking --------------------------------------------
    blk = bytes((0x10, 0x40, 0x20, 0x40, 0x30, 0x40))     # HI splits
    assert reference_bytes_v23(blk) == (None, 0x40)
    assert reference_candidates_v23(blk) == [0x1040, 0x2040, 0x3040]
    assert reference_candidates_v23(
        blk, confidence=(0.1, 1.0, 0.9, 1.0, 0.5, 1.0)) == \
        [0x2040, 0x3040, 0x1040]
    blk = bytes((0x10, 0x01, 0x20, 0x02, 0x30, 0x03))     # both split
    assert reference_bytes_v23(blk) == (None, None)
    assert reference_candidates_v23(blk) == [
        0x1001, 0x1002, 0x1003,
        0x2001, 0x2002, 0x2003,
        0x3001, 0x3002, 0x3003]
    # Equal confidence keeps wire order (deterministic).
    assert reference_candidates_v23(blk, confidence=(1.0,) * 6) == \
        reference_candidates_v23(blk)
    try:
        reference_candidates_v23(blk, confidence=(1.0,) * 4)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted a 4-value confidence vector")

    # ---- v2.3 false-accept math ---------------------------------------
    assert abs(fa_prob(1, 1) - 1 / 65536) < 1e-15
    assert abs(fa_prob(1, 3) - 3 / 65536) < 1e-15
    assert abs(fa_prob(1, 9) - 9 / 65536) < 1e-15
    assert fa_prob(0) == 0.0
    assert fa_prob(64, 9) > fa_prob(64, 3) > fa_prob(64, 1)
    assert 0.0 < fa_prob(1024, 1) < 1.0
    # 256x stronger per trial than the superseded 8-bit check.
    assert abs(fa_prob(1, 1) * 256 - fa_prob_crc8(1, 1)) < 1e-15
    # The emit-always budget: <= 0.2 % wrong emissions.
    assert fa_budget(0.002, 1) == 131, fa_budget(0.002, 1)
    assert fa_prob(131, 1) <= 0.002 < fa_prob(132, 1)
    assert fa_budget(0.002, 3) == 43, fa_budget(0.002, 3)
    assert fa_budget(0.002, 9) == 14, fa_budget(0.002, 9)
    # The 8-bit check could not pay for a single wrong trial at 0.2 %.
    assert fa_prob_crc8(1, 1) > 0.002

    # ---------------------------------------------- COMPAT: v2.2 / v2.1
    assert crc8_smbus(CHECK) == 0xF4
    assert crc8_smbus_bitwise(CHECK) == 0xF4
    assert crc8_smbus(b"") == 0x00
    for v in VECTORS:
        assert crc8_smbus(v) == crc8_smbus_bitwise(v), v.hex()
        blk = check_block(v)
        assert len(blk) == CHECK_BLOCK_LEN == 4
        assert blk == bytes((crc8_smbus(v),) * 4)
        p = build_payload(v)
        assert split_payload(p) == (bytes(v), blk)
        assert verify_intact(p) and verify_payload(p)
        assert build_payload(v, n=3) == bytes(v) + blk[:3]
        assert verify_intact(build_payload(v, n=3), n=3)
    assert majority(b"\x11\x11\x11\x22") == 0x11
    assert majority(b"\x11\x11\x22\x22") is None
    assert majority(b"\x11\x22\x33\x44") is None
    assert majority(b"\x11\x22\x11") == 0x11
    assert reference_candidates(b"\x11\x22\x33\x44") == [0x11, 0x22,
                                                         0x33, 0x44]
    assert abs(fa_prob_crc8(1, 1) - 1 / 256) < 1e-12
    assert abs(fa_prob_crc8(9, 1) - 0.03459) < 1e-4      # SPEC SS7.10

    print("crc.py self-test OK  (v2.3 + v2.2/v2.1 compat)")
    print(f"  CRC-16/CCITT-FALSE('123456789') = "
          f"0x{crc16_ccitt_false(CHECK):04X}   <- standard check value")
    print(f"  check_block_v23(b'')            = "
          f"{check_block_v23(b'').hex().upper()}  "
          f"(HI LO, three times)")
    print(f"  check_block_v23(48 zero bytes)  = "
          f"{check_block_v23(bytes(48)).hex().upper()}")
    print()
    print("  v2.3 reference recovery: INDEPENDENT per-byte majority")
    print("    reference_HI = majority(H1,H2,H3), "
          "reference_LO = majority(L1,L2,L3)")
    print("    >= 2 of 3 correct at a byte position -> exact majority")
    print("    >= 1 of 3 correct at a byte position -> still a candidate")
    print("    no majority at a position -> its distinct values enumerate;")
    print(f"    references = cross product, capped at "
          f"REF_MAX_V23 = {REF_MAX_V23} (= 3 x 3)")
    print()
    print("  False accept of a wrong chase candidate (16-bit check):")
    print(fa_table())
    print("  1 reference = both check-byte positions had a majority "
          "(normal case)")
    print("  3 references = one byte position split, its 3 values tried")
    print("  9 references = both positions split, full 3x3 cross product")
    print()
    print("  Emit-always budget -- wrong trials affordable per frame at the")
    print("  <= 0.2 % wrong-emission target:")
    for r in (1, 3, 9):
        print(f"    {r} reference(s): {fa_budget(0.002, r):4d} wrong trials  "
              f"(risk {fa_prob(fa_budget(0.002, r), r) * 100:.4f} %)")
    print(f"    8-bit check (v2.2, compat): "
          f"{0 if fa_prob_crc8(1, 1) > 0.002 else 1} wrong trials  "
          f"(one trial alone is {fa_prob_crc8(1, 1) * 100:.4f} %)")
    print()
    print("  COMPAT -- superseded 8-bit check (v2.2/v2.1 corpora only):")
    print(fa_table_crc8())
