"""REAL v2.1-length captures (27-byte frame, 216 bits) on real silicon.

data/captures_v21*.json carry the v2.1 **rev1** check layout
(CRC16_HI||CRC16_LO||CRC8), superseded by rev2 ([CRC8]x3), so the CRC
arithmetic cannot be replayed here.  What IS measurable and is exactly
what the chase depends on: at true v2.1 frame length, on real silicon,
are the wrong DATA bits contained in the admitted weak set?
"""
import sys, pathlib
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
from harness import load_dataset, linearize             # noqa: E402
import ref_marg as ref                                  # noqa: E402
ref.VOTES = False
ref._configure(19)
TIE_EMIT, MG_MAX, A_MAX, W_MAX = 8, 8, 5, 2


def run(path, label):
    meta, caps = load_dataset(path)
    c = Counter(); hist = Counter()
    for cap in caps:
        pp = bytes.fromhex(cap["payload"])          # 19 B payload'
        st = ref.decode_state(linearize(cap["capture"]))
        if st is None:
            c["refuse_hard"] += 1; continue
        bits, mgv = st["bits"], st["mgv"]
        if any(ref.KNOWN[t] >= 0 and bits[t] != ref.KNOWN[t]
               for t in range(ref.NB)) or st["infeasible"] > ref.GATE_INFEAS \
                or st["label_err"] > ref.GATE_LABERR:
            c["refuse_hard"] += 1; continue
        pb = bits[32:32 + 152]; pm = mgv[32:32 + 152]
        eb = [(b >> (7 - j)) & 1 for b in pp for j in range(8)]
        wrong = [i for i in range(152) if pb[i] != eb[i]]
        wrong_d = [i for i in wrong if i < 128]
        hist[len(wrong)] += 1
        n0 = sum(1 for v in pm if v == 0)
        weak = [i for i in range(152) if pm[i] <= MG_MAX]
        if not wrong:
            c["exact"] += 1; continue
        if n0 > TIE_EMIT:
            c["refuse_emitgate"] += 1; continue
        if len(weak) == 0 or len(weak) > A_MAX:
            c["refuse_admit"] += 1; continue
        if len(wrong) <= W_MAX and set(wrong) <= set(weak):
            c["reachable"] += 1
        else:
            c["out_of_reach"] += 1
        if wrong_d and not wrong_d == wrong:
            c["_check_bits_also_wrong"] += 1
    n = sum(v for k, v in c.items() if not k.startswith("_"))
    print("--- %s (n=%d) ---" % (label, n))
    print("  exact payload' (19 B)  %3d (%5.1f%%)" % (c["exact"],
                                                      100. * c["exact"] / n))
    print("  chase-reachable        %3d  -> ceiling %3d (%5.1f%%)"
          % (c["reachable"], c["exact"] + c["reachable"],
             100. * (c["exact"] + c["reachable"]) / n))
    print("  refused: hard %d  emit-gate %d  admission %d  out-of-reach %d"
          % (c["refuse_hard"], c["refuse_emitgate"], c["refuse_admit"],
             c["out_of_reach"]))
    print("  wrong-bit histogram over payload' (152 bits):",
          dict(sorted(hist.items())))
    print("  frames where a CHECK-block bit was also wrong: %d"
          % c["_check_bits_also_wrong"])


D = R.parent / "data"
run(str(D / "captures_v21.json"), "captures_v21.json, 54 real 27-byte frames")
run(str(D / "captures_v21_val.json"),
    "captures_v21_val.json, 36 real 27-byte frames (unseen patterns)")
