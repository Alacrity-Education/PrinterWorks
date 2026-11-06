"""SINGLE-SHOT v2 delivery, measured by running the ACTUAL chase over the
ACTUAL error patterns produced by the votes-cut decoder on the real corpora.

Unlike chase_sim2.py (synthetic weight mixes), this takes, per real capture:
  - the real candidate list (8 lowest-margin payload bit positions)
  - the real wrong-bit set
and computes the real CRC8/CRC16 residuals by syndrome linearity, then runs
the real bounded enumeration.  Reports STOP vs CONT policy side by side.

Caveat (stated in the spec): the corpora are v1-framed (16 B payload, no
check block on the wire), so candidates are mapped into v2 test framing
(NP'=19) with the 24 check-block bits assumed error-free.  This is mildly
optimistic and is exactly what acceptance criterion A3 re-measures.
"""
import sys, pathlib, itertools
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from harness import load_dataset, linearize
import ref_marg as ref

ref.VOTES = False           # the v2 cut

NPP = 19                    # test framing payload' bytes (16 DATA + 3 check)
NCAND, WMAX, TMAX = 8, 3, 93


def pow8(j):
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r


def pow16(j):
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r


def syn(i):
    """syndrome pair for DATA bit index i (0..127), MSB-first within byte."""
    p, b = i >> 3, 7 - (i & 7)
    j = 8 * (NPP - 1 - p) + b
    return pow8(j), (pow16(j - 8) if j >= 8 else 0)


ORDER = []
for w in range(WMAX + 1):
    for s in itertools.combinations(range(NCAND), w):
        ORDER.append(s)
        if len(ORDER) >= TMAX:
            break
    if len(ORDER) >= TMAX:
        break
assert len(ORDER) == 93, len(ORDER)


def chase(cand, true_set, cont):
    """cand: list of DATA bit indices (len NCAND).  true_set: real wrong bit
    indices (any positions, possibly outside cand).  Returns one of
    'ok' | 'refuse' | 'FALSE'."""
    r8 = r16 = 0
    for i in true_set:
        a, b = syn(i)
        r8 ^= a
        r16 ^= b
    if r8 == 0 and r16 == 0:
        # residual vanishes: emitted unchased.  Correct only if truly clean.
        return "ok" if not true_set else "FALSE"
    truth = tuple(sorted(cand.index(i) for i in true_set)) \
        if all(i in cand for i in true_set) and len(true_set) <= WMAX else None
    for s in ORDER:
        x = y = 0
        for k in s:
            a, b = syn(cand[k])
            x ^= a
            y ^= b
        if x != r8:
            continue
        if y == r16:
            return "ok" if s == truth else "FALSE"
        if not cont:
            return "refuse"
    return "refuse"


def run(ds, label):
    meta, caps = load_dataset(ds)
    per_trim = {}
    tot = Counter()
    for c in caps:
        exp = bytes.fromhex(c["payload"])
        st = ref.decode_state(linearize(c["capture"]))
        key = c.get("trim", "-")
        d = per_trim.setdefault(key, Counter())
        d["n"] += 1
        tot["n"] += 1
        if st is None:
            d["refuse_stop"] += 1; d["refuse_cont"] += 1
            tot["refuse_stop"] += 1; tot["refuse_cont"] += 1
            continue
        bits, mgv = st["bits"], st["mgv"]
        viol = sum(1 for t in range(ref.NB)
                   if ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t])
        if viol or st["infeasible"] > ref.GATE_INFEAS \
           or st["label_err"] > ref.GATE_LABERR:
            d["refuse_stop"] += 1; d["refuse_cont"] += 1
            tot["refuse_stop"] += 1; tot["refuse_cont"] += 1
            continue
        exp_bits = ref._bits_of(exp)
        wrong = [i for i in range(8 * ref.N_PAYLOAD)
                 if bits[32 + i] != exp_bits[i]]
        cand = sorted(range(8 * ref.N_PAYLOAD),
                      key=lambda i: (mgv[32 + i], i))[:NCAND]
        for pol, tag in ((False, "stop"), (True, "cont")):
            out = chase(cand, wrong, pol)
            if out == "ok":
                d["ok_" + tag] += 1; tot["ok_" + tag] += 1
            elif out == "FALSE":
                d["FALSE_" + tag] += 1; tot["FALSE_" + tag] += 1
            else:
                d["refuse_" + tag] += 1; tot["refuse_" + tag] += 1
    print("=== %s ===" % label)
    print("  %-6s %4s | %-28s | %-28s" % ("trim", "n",
          "STOP  ok / refuse / FALSE", "CONT  ok / refuse / FALSE"))
    for k in sorted(per_trim, key=lambda z: str(z)):
        d = per_trim[k]
        print("  %-6s %4d | %5d %5d %5d  (%5.1f%%) | %5d %5d %5d  (%5.1f%%)"
              % (k, d["n"], d["ok_stop"], d["refuse_stop"], d["FALSE_stop"],
                 100 * d["ok_stop"] / d["n"],
                 d["ok_cont"], d["refuse_cont"], d["FALSE_cont"],
                 100 * d["ok_cont"] / d["n"]))
    n = tot["n"]
    print("  %-6s %4d | %5d %5d %5d  (%5.1f%%) | %5d %5d %5d  (%5.1f%%)"
          % ("ALL", n, tot["ok_stop"], tot["refuse_stop"], tot["FALSE_stop"],
             100 * tot["ok_stop"] / n,
             tot["ok_cont"], tot["refuse_cont"], tot["FALSE_cont"],
             100 * tot["ok_cont"] / n))
    print()


run(str(R.parent / "data" / "captures.json"), "captures.json (bench, eps=-1.1%)")
run(str(R.parent / "data" / "captures_trim.json"), "captures_trim.json (8 trim codes)")
