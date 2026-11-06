"""B1-style parity: embedded_v2's P1..P4 vs the spec's instrumented v1
reference (dev_v2spec/ref_marg.py, votes OFF) on every real capture.

embedded_v2 must be bit-identical to ref_marg minus votes: same bits[],
same hard-gate counters, and its streaming weak-set accounting (n_weak,
n_tied, top-A_MAX candidate list) must equal the same quantities derived
from ref_marg's full mgv array.  Any mismatch is a porting bug.
"""
import sys
import pathlib

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
sys.path.insert(0, str(R.parent / "bench"))
from harness import load_dataset, linearize      # noqa: E402
import ref_marg as ref                           # noqa: E402
import embedded_v2 as v2                         # noqa: E402

ref.VOTES = False
DATA = R.parent / "data"


def check(path, npp, label):
    ref._configure(npp)
    v2._configure(npp - 3 if npp > 16 else npp,
                  check=(npp > 16))
    assert ref.NB == v2.NB, (ref.NB, v2.NB)
    _, caps = load_dataset(path)
    n_ok = 0
    for c in caps:
        s = linearize(c["capture"])
        a = ref.decode_state(s)
        b = v2.decode_state(s)
        tag = "%s/%s r%s" % (label, c["pattern"], c["rep"])
        if (a is None) != (b is None):
            print("MISMATCH none-ness", tag, a is None, b is None)
            continue
        if a is None:
            n_ok += 1
            continue
        ok = True
        if a["bits"] != b["bits"]:
            print("MISMATCH bits", tag,
                  [i for i in range(ref.NB)
                   if a["bits"][i] != b["bits"][i]][:8])
            ok = False
        for kk in ("infeasible", "label_err", "n_seg"):
            if a[kk] != b[kk]:
                print("MISMATCH", kk, tag, a[kk], b[kk])
                ok = False
        # weak-set accounting from ref's full mgv array (payload' slice)
        pm = a["mgv"][32:32 + 8 * v2.NPP]
        n_weak = sum(1 for m in pm if m <= v2.MG_MAX)
        n_tied = sum(1 for m in pm if m == 0)
        cand = sorted(range(len(pm)), key=lambda k: (pm[k], k))[:v2.A_MAX]
        cand = [k for k in cand if pm[k] <= v2.MG_MAX]
        if n_weak != b["n_weak"] or n_tied != b["n_tied"]:
            print("MISMATCH weak/tied", tag,
                  (n_weak, n_tied), (b["n_weak"], b["n_tied"]))
            ok = False
        if cand != b["cand_t"]:
            print("MISMATCH cand list", tag, cand, b["cand_t"],
                  [pm[k] for k in cand], b["cand_m"])
            ok = False
        else:
            if [pm[k] for k in cand] != b["cand_m"]:
                print("MISMATCH cand margins", tag)
                ok = False
        n_ok += int(ok)
    print("%-28s %d/%d captures bit-identical" % (label, n_ok, len(caps)))
    return n_ok == len(caps)


ok = True
ok &= check(str(DATA / "captures.json"), 16, "captures.json")
ok &= check(str(DATA / "captures_trim.json"), 16, "captures_trim.json")
ok &= check(str(DATA / "captures_v21.json"), 19, "captures_v21.json")
ok &= check(str(DATA / "captures_v21_val.json"), 19, "captures_v21_val.json")
print("PARITY:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
