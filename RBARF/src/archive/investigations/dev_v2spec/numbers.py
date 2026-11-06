"""Every number the spec quotes for the CHOSEN policy, in one place.

Policy: emit gate n_tied<=8; chase admission MG_MAX=8, A_MAX=5, W<=2,
T = 1+n+C(n,2) <= 16; ordering data-minimal; alias guard on; split-vote
fallback OFF.
"""
import sys, pathlib, pickle
from collections import Counter
R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R.parent / "bench"))
sys.path.insert(0, str(R / "approaches" / "dev_v2spec"))
import v21                                             # noqa: E402
D = pathlib.Path(__file__).parent
PROD = pickle.load((D / "prod_cache.pkl").open("rb"))
TEST = pickle.load((D / "e2e_cache.pkl").open("rb"))
TIE_EMIT, MG_MAX, A_MAX, W_MAX = 8, 8, 5, 2


def decide(rec, truth, ND, stats):
    if rec is None or rec[2]:
        return "refuse_gate"
    bits, mgv, _ = rec
    NPP = ND + 3
    by = []
    for p in range(NPP):
        v = 0
        for j in range(8):
            v = (v << 1) | bits[8 * p + j]
        by.append(v)
    C = by[ND:]
    stats["blk_all3" if C[0] == C[1] == C[2] else
          ("blk_2of3" if v21.maj3(*C) is not None else "blk_alldiff")] += 1
    n0 = sum(1 for v in mgv if v == 0)
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
    if path == "direct":
        if n0 > TIE_EMIT:
            return "refuse_emitgate"
        return "ok_direct" if got == truth else "CAT_direct"
    if n0 > TIE_EMIT:
        return "refuse_emitgate"
    nlow = sum(1 for v in mgv if v <= MG_MAX)
    if nlow == 0:
        return "refuse_nocand"
    if nlow > A_MAX:
        return "refuse_admit"
    T = 1 + nlow + nlow * (nlow - 1) // 2
    stats["chases"] += 1
    got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W_MAX, TMAX=T,
                              ordering="dfirst", fallback=False, guard="alias")
    stats["trials"] += nt
    stats["maxtrials"] = max(stats["maxtrials"], nt)
    if got is None:
        return "refuse_chase"
    return "ok_chase" if got == truth else "CAT_chase"


def variant(recs, ND, td=TIE_EMIT, guard="alias", fb=False):
    c = Counter()
    for k, (rec, truth) in recs.items():
        if rec is None or rec[2]:
            c["refuse"] += 1; continue
        bits, mgv, _ = rec
        n0 = sum(1 for v in mgv if v == 0)
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=0, WMAX=0, TMAX=1)
        if path == "direct":
            if n0 > td:
                c["refuse"] += 1; continue
            c["ok" if got == truth else "CAT"] += 1; continue
        if n0 > td:
            c["refuse"] += 1; continue
        nlow = sum(1 for v in mgv if v <= MG_MAX)
        if nlow == 0 or nlow > A_MAX:
            c["refuse"] += 1; continue
        T = 1 + nlow + nlow * (nlow - 1) // 2
        got, nt, path = v21.chase(bits, mgv, ND, N_CAND=nlow, WMAX=W_MAX,
                                  TMAX=T, ordering="dfirst", fallback=fb,
                                  guard=guard)
        if got is None:
            c["refuse"] += 1
        else:
            c["ok" if got == truth else "CAT"] += 1
    return c


print("### policy variants at the FINAL budget (A_MAX=5, W<=2, T<=16) ###")
for lab, recs, ND in (("production", PROD, 48), ("test", TEST, 16)):
    for tag, kw in (("FINAL (emit gate 8, alias, fb off)", {}),
                    ("emit gate OFF", dict(td=10 ** 9)),
                    ("alias guard OFF", dict(guard="none")),
                    ("unique-pass accept", dict(guard="unique")),
                    ("split-vote fallback ON", dict(fb=True))):
        c = variant(recs, ND, **kw)
        print("  %-11s %-36s deliver %4d  CAT %d  refuse %4d"
              % (lab, tag, c["ok"], c["CAT"], c["refuse"]))
print()

for label, recs, ND in (("PRODUCTION 48 B / 472-bit frame", PROD, 48),
                        ("TEST 16 B / 216-bit frame", TEST, 16)):
    print("=" * 74)
    print(label)
    print("=" * 74)
    tot, st = Counter(), Counter()
    per = {}
    for k, (rec, truth) in recs.items():
        s = Counter(maxtrials=0)
        o = decide(rec, truth, ND, s)
        tot[o] += 1
        st.update(s); st["maxtrials"] = max(st["maxtrials"], s["maxtrials"])
        d = per.setdefault(k[0], Counter())
        d[o] += 1
    n = len(recs)
    ok = tot["ok_direct"] + tot["ok_chase"]
    cat = tot["CAT_direct"] + tot["CAT_chase"]
    print("n=%d  DELIVERED %d (%.2f%%)  = direct %d + chase %d" %
          (n, ok, 100.0 * ok / n, tot["ok_direct"], tot["ok_chase"]))
    print("  refusals: hard-gate %d  emit-gate %d  no-candidate %d  "
          "admission %d  chase-exhausted %d"
          % (tot["refuse_gate"], tot["refuse_emitgate"], tot["refuse_nocand"],
             tot["refuse_admit"], tot["refuse_chase"]))
    print("  CATASTROPHIC %d (direct %d, chase %d)"
          % (cat, tot["CAT_direct"], tot["CAT_chase"]))
    print("  chases executed %d ; trials total %d ; mean %.1f ; max %d"
          % (st["chases"], st["trials"],
             st["trials"] / max(1, st["chases"]), st["maxtrials"]))
    print("  a-priori FA bound: %d chases x (1-(1-1/256)^%d) = %.2f expected"
          % (st["chases"], st["maxtrials"],
             st["chases"] * (1 - (1 - 1 / 256.0) ** st["maxtrials"])))
    print("  decoded check block: all-3-equal %d  2-of-3 %d  all-differ %d"
          % (st["blk_all3"], st["blk_2of3"], st["blk_alldiff"]))
    print("  per eps:")
    for e in sorted(per):
        d = per[e]
        m = sum(d.values())
        print("    %+7.3f%%  n=%3d  deliver %3d (%5.1f%%)  dir %3d chase %2d"
              "  refuse %3d  CAT %d"
              % (e * 100, m, d["ok_direct"] + d["ok_chase"],
                 100.0 * (d["ok_direct"] + d["ok_chase"]) / m, d["ok_direct"],
                 d["ok_chase"], sum(v for kk, v in d.items()
                                    if kk.startswith("refuse")),
                 d["CAT_direct"] + d["CAT_chase"]))
    print()
