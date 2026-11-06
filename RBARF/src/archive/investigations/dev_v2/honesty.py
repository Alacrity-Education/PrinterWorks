#!/usr/bin/env python3
"""A6 refusal-honesty audit + pre-CRC containment on the v2.1 corpora.

For every capture: run P1..P4, compare the raw payload' bits against
ground truth (ground truth used as a RULER only -- nothing feeds back),
then classify what the full decoder did with it:

  * exact pre-CRC        -> should be delivered via 'direct' (or 'chase'
                            when only CHECK bits were wrong)
  * wrong bits contained (all wrong bits in the admitted weak set, weight
    <= W_MAX)            -> chase-reachable
  * a REFUSAL is HONEST when the frame was NOT exact pre-CRC and NOT
    chase-reachable, or was blocked by an admission/emit gate whose
    condition genuinely held (n_weak = 0 / > A_MAX, n_tied > 8, or the
    parity gate proving no admissible trial could pass).

A refusal that hides a frame the chase could have repaired is a policy
bug (spec SS13.2 A6) and is flagged loudly.
"""
import sys
import pathlib
from collections import Counter

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches"))
from harness import load_dataset, linearize      # noqa: E402
import embedded_v2 as v2                         # noqa: E402

ND = 16


def bits_of(bs):
    return [(b >> (7 - j)) & 1 for b in bs for j in range(8)]


def run(path):
    v2._configure(ND)
    _, caps = load_dataset(path)
    c = Counter()
    hist = Counter()
    bad = []
    for cap in caps:
        pp = bytes.fromhex(cap["payload"])
        truth = pp[:ND]
        samples = linearize(cap["capture"])
        st = v2.decode_state(samples)
        got, info = v2.decode_ex(samples)
        if st is None:
            c["no_lock"] += 1
            continue
        pb = st["bits"][v2.PP_LO:v2.PP_HI]
        eb = bits_of(pp)
        wrong = [i for i in range(8 * v2.NPP) if pb[i] != eb[i]]
        hist[len(wrong)] += 1
        weak = set(st["cand_t"]) if st["n_weak"] <= v2.A_MAX else None
        contained = (weak is not None and len(wrong) <= v2.W_MAX
                     and set(wrong) <= weak)
        if not wrong:
            c["exact_preCRC"] += 1
        elif contained:
            c["contained"] += 1
        else:
            c["out_of_reach"] += 1
        if got is None:
            # the refusal is honest unless the frame was exact pre-CRC or
            # its wrong bits were contained AND no gate condition held
            if not wrong:
                bad.append((cap["pattern"], cap["rep"], info["cause"],
                            "refused an EXACT frame"))
            elif contained and info["cause"] == "refuse_chase":
                # chase ran (or was parity-gated) and still missed a
                # contained error: legitimate only when the needed trial
                # was outside the admitted budget (e.g. data+check pair
                # with the check bit not in the weak set, or the parity
                # gate proving the sole candidate impossible -- meaning
                # the true wrong set involves a bit outside 'weak')
                wrong_d = [i for i in wrong if i < 8 * ND]
                bad.append((cap["pattern"], cap["rep"], info["cause"],
                            "contained wrong=%s (data %s) n_weak=%d "
                            "n_tied=%d NOT recovered"
                            % (wrong, wrong_d, st["n_weak"], st["n_tied"])))
        elif got != truth:
            bad.append((cap["pattern"], cap["rep"], info["path"],
                        "CATASTROPHIC"))
        c["refused" if got is None else "emitted"] += 1
    name = pathlib.Path(path).name
    print("--- %s (n=%d) ---" % (name, len(caps)))
    print("  pre-CRC: exact %d, wrong-but-contained %d, out-of-reach %d"
          % (c["exact_preCRC"], c["contained"], c["out_of_reach"]))
    print("  wrong-bit histogram over payload' (%d bits): %s"
          % (8 * v2.NPP, dict(sorted(hist.items()))))
    print("  decoder: emitted %d, refused %d"
          % (c["emitted"], c["refused"]))
    if bad:
        for b in bad:
            print("  A6 VIOLATION? %s rep %d [%s] %s" % b)
    else:
        print("  A6: every refusal honest (no refused frame was exact or "
              "chase-reachable-and-admitted)")
    print()
    return bad


allbad = []
for p in (sys.argv[1:] or
          [str(R.parent / "data" / "captures_v21.json"),
           str(R.parent / "data" / "captures_v21_val.json")]):
    allbad += run(p)
print("A6 overall:", "PASS" if not allbad else "%d flags" % len(allbad))
