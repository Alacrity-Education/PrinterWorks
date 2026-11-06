#!/usr/bin/env python3
"""Wide-band evaluation of embedded_v2 on the real trim-sweep corpus.

../data/captures_trim.json: 96 real captures at 8 CLK_HSITRIMR codes
spanning eps -4.385%..+3.733% (TRIM_SWEEP.md), 6 patterns x 2 reps per
code.  These frames carry the OLD v2.0 16-byte payloads with NO check
block, so the CRC chase cannot run -- per the task, this corpus scores
LOCK + SEGMENTATION only (chase disabled via _configure(16, check=False)),
proving the wide-band single-shot lock on real hardware.

Scored per capture (spec SS13.4 C1 wording):

  lock      = endpoint seed acquired AND K within [K_MIN, K_MAX]
  markers   = all 64 known HEADER/TRAILER bits decode to the template
              (violations == 0) -- "markers consistent"
  LOCK OK   = lock AND markers            <- the acceptance criterion
  seg exact = the 128 payload bits equal ground truth pre-CRC
              (reported for context; the v2.1 chase machinery is what
              turns near-misses into deliveries, and it needs the check
              block these old frames do not carry)

Also reported: the K-derived eps estimate per code against TRIM_SWEEP.md's
measured means (the SS11 auto-trim formula), and what the legacy
(unverified) emit path would deliver after gates R1..R5.
"""
import sys
import pathlib
from collections import defaultdict, Counter

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches"))
from harness import load_dataset, linearize      # noqa: E402
import embedded_v2 as v2                         # noqa: E402

# measured trim -> eps map (TRIM_SWEEP.md, alignment method)
TRIM_EPS = {0: -1.072, 1: -2.248, 2: -3.281, 3: -4.385,
            4: +3.733, 5: +2.492, 6: +1.274, 7: +0.022}


def bits_of(bs):
    return [(b >> (7 - j)) & 1 for b in bs for j in range(8)]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        str(R.parent / "data" / "captures_trim.json")
    v2._configure(16, check=False)        # legacy v2.0 geometry, chase OFF
    assert v2.NB == 192 and not v2.CHASE_EN
    _, caps = load_dataset(path)
    per = defaultdict(Counter)
    eps_est = defaultdict(list)
    tot = Counter()
    fails = []
    for c in caps:
        code = c["trim"]
        p = per[code]
        p["n"] += 1
        tot["n"] += 1
        samples = linearize(c["capture"])
        st = v2.decode_state(samples)
        st2 = v2.decode_state(samples)                  # A9 determinism
        assert (st is None) == (st2 is None) and \
            (st is None or st["bits"] == st2["bits"]), "NON-DETERMINISTIC"
        if st is None:
            fails.append((code, c["pattern"], c["rep"], "no seed/lock"))
            continue
        lock = v2.K_MIN <= st["K"] <= v2.K_MAX
        viol = sum(1 for t in range(v2.NB)
                   if v2.KNOWN[t] >= 0 and st["bits"][t] != v2.KNOWN[t])
        markers = viol == 0
        eb = bits_of(bytes.fromhex(c["payload"]))
        seg = st["bits"][v2.PP_LO:v2.PP_HI] == eb
        gates = (st["infeasible"] <= v2.GATE_INFEAS
                 and st["label_err"] <= v2.GATE_LABERR)
        emitted, info = v2.decode_ex(samples)
        p["lock"] += int(lock)
        p["markers"] += int(markers)
        p["lockok"] += int(lock and markers)
        p["seg"] += int(seg)
        p["gates"] += int(gates)
        p["legacy_emit"] += int(emitted is not None)
        p["legacy_exact"] += int(emitted is not None
                                 and emitted == bytes.fromhex(c["payload"]))
        tot["lock"] += int(lock)
        tot["markers"] += int(markers)
        tot["lockok"] += int(lock and markers)
        tot["seg"] += int(seg)
        if lock:
            # SS11: eps = (K_NOM - K) / K, here in float % (wrapper only)
            eps_est[code].append(100.0 * (v2.K_NOM - st["K"]) / st["K"])
        if not (lock and markers):
            fails.append((code, c["pattern"], c["rep"],
                          "lock=%s viol=%d" % (lock, viol)))
    print("=" * 76)
    print("captures_trim.json -- 96 real captures, 8 trim codes, "
          "LOCK + SEGMENTATION (chase disabled: v2.0 frames carry no "
          "check block)")
    print("=" * 76)
    print("%-5s %-9s %-9s %5s %8s %8s %10s %12s %s"
          % ("code", "eps_meas", "eps_est", "n", "lock", "markers",
             "LOCK OK", "seg exact", "legacy emit/exact"))
    for code in sorted(per, key=lambda k: TRIM_EPS.get(k, 0)):
        p = per[code]
        ee = eps_est[code]
        est = sum(ee) / len(ee) if ee else float("nan")
        print("%-5s %+8.3f%% %+8.3f%% %5d %8s %8s %10s %12s %6s"
              % (code, TRIM_EPS.get(code, 0), est, p["n"],
                 "%d/%d" % (p["lock"], p["n"]),
                 "%d/%d" % (p["markers"], p["n"]),
                 "%d/%d" % (p["lockok"], p["n"]),
                 "%d/%d" % (p["seg"], p["n"]),
                 "%d/%d" % (p["legacy_emit"], p["legacy_exact"])))
    print("-" * 76)
    print("TOTAL  lock %d/%d   markers %d/%d   LOCK OK %d/%d   "
          "seg exact %d/%d"
          % (tot["lock"], tot["n"], tot["markers"], tot["n"],
             tot["lockok"], tot["n"], tot["seg"], tot["n"]))
    for f in fails:
        print("  LOCK FAIL trim %s %s rep %d: %s" % f)
    print("acceptance (wide-band lock on all 96): %s"
          % ("PASS" if tot["lockok"] == tot["n"] else "FAIL"))
    print("determinism (two runs identical): PASS")
    return 0 if tot["lockok"] == tot["n"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
