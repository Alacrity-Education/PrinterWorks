#!/usr/bin/env python3
"""Score embedded_v2 on the v2.1 rev2 corpora (real check blocks on the
wire).  eval.py's expected payload is the 19-byte payload'; embedded_v2
returns the 16 DATA bytes, so this wrapper scores data-16 against
ground-truth payload'[:16] and adds the single-shot accounting eval.py
does not know about.

SINGLE-SHOT scoring (EMBEDDED_V2_SPEC.md SS13.2, applied literally):

    delivered     = emitted AND equal to ground truth
    CATASTROPHIC  = emitted AND not equal to ground truth   (target: 0)
    missed        = refused          (a refusal IS a missed frame)

Reports per pattern and overall: exact-success rate, refusals by cause,
catastrophics (each occurrence described), successes needing chase
corrections, chase invocations, trial statistics, and the a-priori
false-accept bound for the executed chases.  Runs every capture twice to
verify determinism (A9): identical bytes + identical path labels.

Usage:
    python3 approaches/dev_v2/eval_v21.py ../data/captures_v21.json
    python3 approaches/dev_v2/eval_v21.py ../data/captures_v21_val.json
"""
import sys
import pathlib
from collections import Counter, defaultdict

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches"))
from harness import load_dataset, linearize      # noqa: E402
import embedded_v2 as v2                         # noqa: E402

ND = 16


def run(path):
    v2._configure(ND)                     # v2.1 test build: 19 B payload'
    meta, caps = load_dataset(path)
    per = defaultdict(Counter)
    tot = Counter()
    st = Counter(maxtrials=0, max_acmp=0)
    cats = []
    det_rows = []
    for c in caps:
        samples = linearize(c["capture"])
        pp = bytes.fromhex(c["payload"])
        assert len(pp) == ND + 3, "not a v2.1 payload' -- wrong dataset?"
        truth = pp[:ND]
        got, info = v2.decode_ex(samples)
        got2, info2 = v2.decode_ex(samples)          # A9 determinism
        assert got == got2 and info["path"] == info2["path"] \
            and info["cause"] == info2["cause"], "NON-DETERMINISTIC"
        p = per[c["pattern"]]
        p["n"] += 1
        tot["n"] += 1
        if info["chased"]:
            st["chases"] += 1
            st["trials"] += info["trials"]
            st["maxtrials"] = max(st["maxtrials"], info["trials"])
            st["max_acmp"] = max(st["max_acmp"], info["alias_cmp"])
        if got is None:
            p["miss"] += 1
            tot["miss"] += 1
            tot[info["cause"]] += 1
            det_rows.append((c["pattern"], c["rep"], "MISS", info["cause"],
                             info.get("n_weak"), info.get("n_tied"),
                             info["trials"]))
        elif got == truth:
            p["exact"] += 1
            tot["exact"] += 1
            tot["path_" + info["path"]] += 1
            if info["path"] == "chase":
                st["corrections"] += 1
                det_rows.append((c["pattern"], c["rep"], "CHASE-FIX",
                                 "flips=%s" % (info["flips"],),
                                 info["n_weak"], info["n_tied"],
                                 info["trials"]))
        else:
            p["CAT"] += 1
            tot["CAT"] += 1
            cats.append((c["pattern"], c["rep"], info["path"],
                         got.hex(), truth.hex()))
    name = pathlib.Path(path).name
    print("=" * 72)
    print("%s  --  %d captures, SINGLE SHOT (a refusal is a miss)"
          % (name, tot["n"]))
    print("=" * 72)
    print("%-12s %-9s %-8s %-6s %s" % ("pattern", "exact", "missed",
                                       "CAT", "notes"))
    for pat in sorted(per):
        p = per[pat]
        note = ""
        if p["miss"]:
            note = "MISS x%d" % p["miss"]
        print("%-12s %4d/%-4d %5d %6d   %s"
              % (pat, p["exact"], p["n"], p["miss"], p["CAT"], note))
    print("-" * 72)
    ex, n = tot["exact"], tot["n"]
    print("EXACT (delivered)   %d/%d = %.2f%%   miss rate %.2f%%"
          % (ex, n, 100.0 * ex / n, 100.0 * tot["miss"] / n))
    print("  path split: direct %d, chase-corrected %d"
          % (tot["path_direct"], tot["path_chase"]))
    print("  refusals %d: lock %d marker %d infeasible %d labelerr %d "
          "emitgate %d nocand %d admission %d chase-exhausted %d"
          % (tot["miss"], tot["refuse_lock"], tot["refuse_marker"],
             tot["refuse_infeasible"], tot["refuse_labelerr"],
             tot["refuse_emitgate"], tot["refuse_nocand"],
             tot["refuse_admit"], tot["refuse_chase"]))
    print("  CATASTROPHIC (emitted != truth, CRC8-passed): %d" % tot["CAT"])
    for cat in cats:
        print("    !!! %s rep %d via %s: got %s want %s" % cat)
    fa = 0.0
    if st["chases"]:
        fa = st["chases"] * (1 - (1 - 1 / 256.0) ** st["maxtrials"])
    print("  chase: invocations %d, corrections %d, trials total %d "
          "(mean %.1f, max %d <= 15+1), alias-compares max %d (<= 25)"
          % (st["chases"], st["corrections"], st["trials"],
             st["trials"] / max(1, st["chases"]), st["maxtrials"],
             st["max_acmp"]))
    print("  a-priori false-accept bound of the executed chases: "
          "%d x (1-(1-1/256)^%d) = %.3f expected; observed %d"
          % (st["chases"], st["maxtrials"], fa, tot["CAT"]))
    if det_rows:
        print("  per-capture events:")
        for r in det_rows:
            print("    %-12s rep %d  %-9s %-28s n_weak=%s n_tied=%s "
                  "trials=%d" % r)
    print("  determinism (two runs, byte + path identical): PASS")
    print()
    return tot, st


if __name__ == "__main__":
    paths = sys.argv[1:] or [str(R.parent / "data" / "captures_v21.json"),
                             str(R.parent / "data" / "captures_v21_val.json")]
    gt = Counter()
    gs = Counter(maxtrials=0, max_acmp=0)
    for p in paths:
        t, s = run(p)
        for k, val in t.items():
            gt[k] += val
        for k in ("chases", "corrections", "trials"):
            gs[k] += s[k]
        gs["maxtrials"] = max(gs["maxtrials"], s["maxtrials"])
        gs["max_acmp"] = max(gs["max_acmp"], s["max_acmp"])
    if len(paths) > 1:
        print("#" * 72)
        print("COMBINED over %d captures: exact %d (%.2f%%), missed %d, "
              "CATASTROPHIC %d, chase-corrected %d"
              % (gt["n"], gt["exact"], 100.0 * gt["exact"] / gt["n"],
                 gt["miss"], gt["CAT"], gt["path_chase"]))
