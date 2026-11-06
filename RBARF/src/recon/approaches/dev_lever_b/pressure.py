#!/usr/bin/env python3
"""TASK 2b -- BUDGET PRESSURE, reported and NOT acted on.

Three questions, all measured at the SHIPPED constants (A_MAX = 11,
T_MAX = 131, W_MAX = 2):

  1. How often does the candidate list TRUNCATE?  The list holds A_MAX
     entries; n_weak + n_dw above that drops the highest-margin DW
     entries first (weak entries can never be dropped -- their margin is
     <= MG_MAX and a DW entry's is > MG_MAX, so weak sorts strictly
     ahead).  What would A_MAX have to be to stop truncating?
  2. How often is T_MAX exhausted, and what would T_MAX have to be?
  3. What would a bigger T_MAX COST?  crc.fa_budget(target, 1) inverts
     the 16-bit false-accept curve, so the price of any budget is a
     number, not an argument -- and raising it is the OWNER's call.
"""
import argparse
import collections
import json
import multiprocessing as mp
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
NEWIMPL = SC.parents[2]
sys.path.insert(0, str(SC))
sys.path.insert(0, str(NEWIMPL / "recon"))
sys.path.insert(0, str(NEWIMPL / "bench"))
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import dwlib                                                   # noqa: E402
import crc                                                     # noqa: E402
from harness import linearize                                  # noqa: E402

PLATEAU = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ENVELOPE = [round(-0.08 + i * 0.004, 6) for i in range(41)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_E = {}


def ref(nd):
    if nd not in _E:
        m = dwlib.load_ref()
        m._configure(nd)
        _E[nd] = m
    return _E[nd]


def one(job):
    nd, samples, _truth = job
    e = ref(nd)
    out, info = e.decode_ex(samples)
    st = e.decode_state(samples)
    nw = st["n_weak"] if st else 0
    nd_ = st.get("n_dw", 0) if st else 0
    ncand = len(st["cand_t"]) if st else 0
    return (int(out is not None), nw, nd_, ncand,
            info.get("trials", 0), info.get("comps", 0),
            int(bool(info.get("budget_hit"))), info["cause"] or "ok",
            int(bool(info.get("chased"))))


def one_a(arg):
    """Re-decode at an overridden A_MAX (which is BOTH the list capacity
    and the R7 admission cap, so this A/B moves two things at once and
    the report says so)."""
    (nd, samples, truth), am = arg
    e = ref(nd)
    e.A_MAX = e.A_PAIR = am
    out, info = e.decode_ex(samples)
    e.A_MAX = e.A_PAIR = e.A_MAX_V23
    return (int(out == truth), int(out is not None and out != truth),
            int(bool(info.get("budget_hit"))))


def one_t(arg):
    """Re-decode at an overridden T_MAX -- the A/B for a bigger budget."""
    (nd, samples, truth), t = arg
    e = ref(nd)
    e.T_MAX = t
    out, _info = e.decode_ex(samples)
    e.T_MAX = e.T_MAX_V23                      # restore the shipped value
    return (int(out == truth), int(out is not None and out != truth))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    a = ap.parse_args()
    import v23lib as L
    jobs = []
    for nm, pts in (("plateau", PLATEAU), ("envelope", ENVELOPE)):
        for _p, d in L.prod_payloads().items():
            for eps in pts:
                for t0 in ARM:
                    jobs.append((48, L.linearize(L.capture(d, eps, t0)),
                                 d))
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        for c in json.loads((NEWIMPL / "data" / fn).read_text())["captures"]:
            jobs.append((16, linearize(c["capture"]),
                         bytes.fromhex(c["payload"])[:16]))
    with mp.Pool(a.j) as p:
        rows = p.map(one, jobs, chunksize=8)
    n = len(rows)
    print("frames: %d (ND=48 plateau + envelope x 12 arm phases, plus the "
          "90 real ND=16 captures)\n" % n)

    print("1. CANDIDATE-LIST TRUNCATION  (A_MAX = 11)")
    print("   Only frames that REACH the chase can be hurt by it: R7")
    print("   refuses n_weak > A_MAX before the list is ever read, and a")
    print("   direct accept never reads it.  Truncation also drops ONLY DW")
    print("   entries -- weak margins are <= MG_MAX and DW margins")
    print("   > MG_MAX, so a DW entry can never sort ahead of a weak one,")
    print("   which is why R7's completeness invariant is STRUCTURAL.")
    ch = [r for r in rows if r[8]]
    for tag, pool in (("all frames", rows), ("CHASED frames", ch)):
        w = sorted(r[1] + r[2] for r in pool) or [0]
        tr = [r for r in pool if r[1] + r[2] > 11]
        print("   %-14s n=%-5d  n_weak+n_dw p50 %-4d p90 %-4d p99 %-4d "
              "max %-4d | truncating %d (%.2f %%)"
              % (tag, len(pool), w[len(w) // 2], w[int(len(w) * .9)],
                 w[int(len(w) * .99)], w[-1], len(tr),
                 100.0 * len(tr) / max(1, len(pool))))
    w = sorted(r[1] + r[2] for r in ch) or [0]
    print("   A_MAX that would stop truncating a CHASED frame: %d"
          " (p90 %d, p99 %d)"
          % (w[-1], w[int(len(w) * .9)], w[int(len(w) * .99)]))
    print("   ... 1 + n + C(n,2) flip sets at n = %d is %d, against 67 at"
          " n = 11 -- and T_MAX caps COMPARISONS at 131 either way, so a"
          " bigger A_MAX buys reachable flip sets, not exposure."
          % (w[-1], 1 + w[-1] + w[-1] * (w[-1] - 1) // 2))

    print("\n2. T_MAX PRESSURE  (T_MAX = 131 residual comparisons)")
    c = sorted(r[5] for r in ch) or [0]
    bh = [r for r in rows if r[6]]
    print("   comps over CHASED frames : p50 %d  p90 %d  p99 %d  max %d"
          % (c[len(c) // 2], c[int(len(c) * .9)], c[int(len(c) * .99)],
             c[-1]))
    print("   T_MAX exhausted (R8 at the budget): %d of %d frames "
          "(%.3f %%), %d of %d chases (%.2f %%)"
          % (len(bh), n, 100.0 * len(bh) / n, len(bh), len(ch),
             100.0 * len(bh) / max(1, len(ch))))
    print("   delivered frames within 10 comps of the budget: %d"
          % sum(1 for r in rows if r[0] and r[5] >= 121))

    print("\n3. WHAT A BIGGER BUDGET WOULD BUY AND COST  (owner's call --")
    print("   re-decoding EVERY frame at each T_MAX, not extrapolating)")
    print("   %-7s %-13s %-9s %-9s %s"
          % ("T_MAX", "fa_prob(T,1)", "delivered", "WRONG", "vs T_MAX=131"))
    base = None
    for t in (131, 200, 262, 658):
        with mp.Pool(a.j) as p:
            rr = p.map(one_t, [(j, t) for j in jobs], chunksize=8)
        dl = sum(1 for x in rr if x[0])
        wr = sum(1 for x in rr if x[1])
        if base is None:
            base = (dl, wr)
        print("   %-7d %-13s %-9d %-9d %+d delivered, %+d WRONG"
              % (t, "%.4f %%" % (100 * crc.fa_prob(t, 1)), dl, wr,
                 dl - base[0], wr - base[1]))
    print("   crc.fa_budget(0.002, 1) = %d  <- where 131 comes from;"
          " fa_budget(0.004, 1) = %d, fa_budget(0.01, 1) = %d"
          % (crc.fa_budget(0.002, 1), crc.fa_budget(0.004, 1),
             crc.fa_budget(0.01, 1)))
    print("\n3b. WHAT A BIGGER A_MAX WOULD BUY AND COST  (owner's call).")
    print("   A_MAX is BOTH the list capacity and the R7 admission cap, so")
    print("   raising it also lets BROADLY-wrong frames into the chase --")
    print("   the exposure SS7.5 was built to refuse.  T_MAX = 131 stays.")
    print("   %-7s %-9s %-9s %-9s %s"
          % ("A_MAX", "delivered", "WRONG", "T_MAX hit", "vs A_MAX=11"))
    b2 = None
    for am in (11, 16, 27, 89):
        with mp.Pool(a.j) as p:
            rr = p.map(one_a, [(j, am) for j in jobs], chunksize=8)
        dl = sum(1 for x in rr if x[0])
        wr = sum(1 for x in rr if x[1])
        bhh = sum(1 for x in rr if x[2])
        if b2 is None:
            b2 = (dl, wr)
        print("   %-7d %-9d %-9d %-9d %+d delivered, %+d WRONG"
              % (am, dl, wr, bhh, dl - b2[0], wr - b2[1]))

    print("   NOT CHANGED.  T_MAX = 131 IS the false-accept bound: every")
    print("   emission has paid at most 131 x 2^-16 = 0.1997 %, and that")
    print("   is exactly what makes widening the CANDIDATE set safe.")

    print("\n4. REFUSAL MIX")
    cz = collections.Counter(r[7] for r in rows)
    print("   ", dict(cz.most_common()))


if __name__ == "__main__":
    main()
