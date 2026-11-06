"""Phase-2 preliminary: with the votes machinery CUT, are the wrong payload
bits inside the N lowest-margin payload positions (the v2 chase list)?"""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from harness import load_dataset, linearize
import ref_marg as ref

ref.VOTES = False           # the v2 cut

def run(ds, label):
    meta, caps = load_dataset(ds)
    tot = exact = refused = 0
    nwrong = Counter(); cont = Counter(); ranks = []
    per_trim = {}
    for c in caps:
        tot += 1
        exp = bytes.fromhex(c["payload"])
        st = ref.decode_state(linearize(c["capture"]))
        key = c.get("trim", "-")
        d = per_trim.setdefault(key, [0, 0, 0, 0])   # n, exact, reach, refuse
        d[0] += 1
        if st is None:
            refused += 1; d[3] += 1; continue
        bits = st["bits"]; mgv = st["mgv"]
        viol = sum(1 for t in range(ref.NB)
                   if ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t])
        if viol or st["infeasible"] > ref.GATE_INFEAS \
           or st["label_err"] > ref.GATE_LABERR:
            refused += 1; d[3] += 1; continue
        exp_bits = ref._bits_of(exp)
        wrong = [i for i in range(8 * ref.N_PAYLOAD)
                 if bits[32 + i] != exp_bits[i]]
        nwrong[len(wrong)] += 1
        if not wrong:
            exact += 1; d[1] += 1; d[2] += 1; cont[0] += 1; continue
        # candidate list = payload bits sorted by (margin, index)
        order = sorted(range(8 * ref.N_PAYLOAD),
                       key=lambda i: (mgv[32 + i], i))
        pos = {b: k for k, b in enumerate(order)}
        worst = max(pos[w] for w in wrong)
        ranks.append((len(wrong), worst))
        for n in (4, 8, 12, 16):
            if worst < n and len(wrong) <= 3: cont[n] += 1
        if worst < 8 and len(wrong) <= 3: d[2] += 1
    print("=== %s: %d captures (VOTES CUT, pre-CRC) ===" % (label, tot))
    print("  emitted %d  refused %d  exact %d (%.1f%%)"
          % (tot - refused, refused, exact, 100 * exact / tot))
    print("  wrong-bit histogram over emitted:",
          dict(sorted(nwrong.items())))
    em = tot - refused
    for n in (4, 8, 12, 16):
        r = exact + cont[n]
        print("  reachable by chase with N_CAND=%2d, W<=3: %d/%d emitted"
              " (%.1f%%)" % (n, r, em, 100 * r / em if em else 0))
    if ranks:
        print("  worst wrong-bit rank in the margin order (n_wrong, rank):",
              sorted(ranks)[:14], "..." if len(ranks) > 14 else "")
    if len(per_trim) > 1:
        print("  per trim code  n / exact / chase-reachable / refused:")
        for k in sorted(per_trim):
            n, e, r, rf = per_trim[k]
            print("    trim %s: %2d  exact %2d  reach %2d  refused %2d" % (k, n, e, r, rf))

run(str(R.parent / "data" / "captures.json"), "captures.json (bench, eps=-1.1%)")
run(str(R.parent / "data" / "captures_trim.json"), "captures_trim.json (8 trim codes)")
