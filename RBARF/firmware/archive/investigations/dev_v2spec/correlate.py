"""Are per-copy failures INDEPENDENT across repetitions of the same
(pattern, trim)?  The trim corpus has 2 reps per cell -- measure directly."""
import sys, pathlib
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from harness import load_dataset, linearize
import ref_marg as ref
ref.VOTES = False
EPS = {0: -1.07, 1: -2.25, 2: -3.28, 3: -4.38,
       4: +3.73, 5: +2.49, 6: +1.27, 7: +0.02}

def outcome(c):
    exp = bytes.fromhex(c["payload"])
    st = ref.decode_state(linearize(c["capture"]))
    if st is None: return "REFUSE", 99
    bits, mgv = st["bits"], st["mgv"]
    if any(ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t] for t in range(ref.NB)) \
       or st["infeasible"] > ref.GATE_INFEAS or st["label_err"] > ref.GATE_LABERR:
        return "REFUSE", 99
    eb = ref._bits_of(exp)
    wrong = [i for i in range(8 * ref.N_PAYLOAD) if bits[32 + i] != eb[i]]
    if not wrong: return "EXACT", 0
    order = sorted(range(8 * ref.N_PAYLOAD), key=lambda i: (mgv[32 + i], i))
    pos = {b: k for k, b in enumerate(order)}
    worst = max(pos[w] for w in wrong)
    return ("REACH" if (worst < 8 and len(wrong) <= 3) else "LOST"), len(wrong)

meta, caps = load_dataset(str(R.parent / "data" / "captures_trim.json"))
cell = {}
for c in caps:
    cell.setdefault((c["trim"], c["pattern"]), {})[c["rep"]] = outcome(c)
both = one = none = 0
print("cell-by-cell (trim, pattern) -> rep0 / rep1:")
for k in sorted(cell, key=lambda k: (EPS[k[0]], k[1])):
    o = cell[k]
    good = [r for r in o if o[r][0] in ("EXACT", "REACH")]
    tag = {2: "both-ok", 1: "SPLIT", 0: "both-fail"}[len(good)]
    if len(good) == 2: both += 1
    elif len(good) == 1: one += 1
    else: none += 1
    if len(good) != 2:
        print("  eps%+6.2f%% %-6s  rep0=%-6s(%d)  rep1=%-6s(%d)  %s"
              % (EPS[k[0]], k[1], o[0][0], o[0][1], o[1][0], o[1][1], tag))
n = both + one + none
print("cells: both-ok %d  split %d  both-fail %d  (n=%d)" % (both, one, none, n))
p = (2 * both + one) / (2.0 * n)
print("marginal per-copy success p = %.3f" % p)
print("independent model P(both fail) = %.3f ; OBSERVED = %.3f"
      % ((1 - p) ** 2, none / n))
