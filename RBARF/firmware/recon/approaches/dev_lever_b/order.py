#!/usr/bin/env python3
"""Does the DW pool have to be RANKED FIRST, and does it have to be
SORTED?  Four candidate-list layouts, same detector, same gates:

  V1  two-ended: DW prefix sorted by (margin, index), weak after
      -- "ranked first", ~150 B of STM8 assembly
  V2  two-ended, DW pool = the FIRST DW_MAX DW bits in bit-index order
      (no margin search, no shift)
  V3  two-ended, DW pool = the DW_MAX smallest margins, UNORDERED
      (replace-the-worst in place, no shift)
  V5  ONE list, one insertion, key = margin: weak keys (<= MG_MAX) sort
      ahead of DW keys (> MG_MAX) automatically, so weak completeness is
      structural and the existing sorted insert is REUSED VERBATIM
      -- ~15 B of assembly, but the DW pool is ranked LAST

Also reports P(wrong | weak) against P(wrong | DW), which is what the
"they are the likeliest wrong" premise rests on.

STALENESS WARNING (added by the independent re-gate, PROD_CLOSURE SS20).
This script was written against the FIRST Lever B reference (commit
ea10c29), whose candidate list was itself two-ended.  The shipped
reference (4be7a95) is ONE list, and it asserts its own invariants:

    assert n == min(st["n_weak"] + n_dw, A_MAX)                (SS6.2)
    assert st["n_weak"] == sum(1 for x in st["cand_m"] if x <= MG_MAX)

A two-ended layout packs DW entries from the TOP of the array and so
violates both.  Consequences for what this script can still measure:

  * V1 maps to `None` (no patch), so on the shipped tree it is the
    SHIPPED one-list insertion -- NOT the "ranked first" layout the
    list above describes.  V5 re-implements the same insertion, and the
    two agree exactly (1 260 / 1 260 on the ND=48 plateau grid), which
    is a useful self-consistency check and nothing more.
  * V2 and V3 raise those asserts on 87 of the plateau frames, so their
    columns are NOT a valid outcome comparison.

The "ranked first buys nothing / differs on exactly one frame in 3 483"
result therefore CANNOT be reproduced from this tree; it holds only
against the ea10c29 reference.  Re-establishing it would need the
ranked-first arms rebuilt against the shipped invariants.  The SHIPPED
ordering is unaffected and is proved bit-exact elsewhere (549/549 host
parity, 24/24 ucsim x 3 configs).
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
sys.path.insert(0, str(NEWIMPL / "recon" / "approaches" / "dev_prod"))
import dwlib                                                   # noqa: E402
from harness import linearize                                  # noqa: E402

# DW_MAX is a parameter OF THE SUPERSEDED two-ended design (the "ranked
# first" layout this script exists to measure against), not of the
# shipped one.  The shipped reference dropped it in
# `Lever B: simplify to one candidate list and a stateless detector`, so
# the ranked-first variants below carry it locally -- at the value the
# two-ended design used (DW_MAX_V23 = 8, commit ea10c29) -- instead of
# reading it off the reference module, which no longer defines it.
DW_MAX = 8

EPS = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ARM = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_M = {}


def _ins_v2(e, ct, cm, nw, nd, k, m, is_dw):
    A = e.A_MAX
    if not is_dw:
        return _ins_weak(e, ct, cm, nw, nd, k, m)
    if nd >= DW_MAX or nw + nd >= A:
        return nw, nd
    ct[A - 1 - nd], cm[A - 1 - nd] = k, m
    return nw, nd + 1


def _ins_v3(e, ct, cm, nw, nd, k, m, is_dw):
    A = e.A_MAX
    if not is_dw:
        return _ins_weak(e, ct, cm, nw, nd, k, m)
    if nd < DW_MAX and nw + nd < A:
        ct[A - 1 - nd], cm[A - 1 - nd] = k, m
        return nw, nd + 1
    w = 0                                     # index of the worst kept
    for i in range(1, nd):
        if cm[A - 1 - i] > cm[A - 1 - w]:
            w = i
    if nd and cm[A - 1 - w] > m:
        ct[A - 1 - w], cm[A - 1 - w] = k, m
    return nw, nd


def _ins_weak(e, ct, cm, nw, nd, k, m):
    A = e.A_MAX
    i = nw
    while i > 0 and cm[i - 1] > m:
        i -= 1
    if i >= A:
        return nw, nd
    if nw + nd >= A and nd > 0:
        nd -= 1
    top = nw if nw + nd < A else A - 1 - nd
    for j in range(top, i, -1):
        ct[j], cm[j] = ct[j - 1], cm[j - 1]
    ct[i], cm[i] = k, m
    return min(nw + 1, A - nd), nd


def _ins_v5(e, ct, cm, n, k, m):
    """The PRE-LEVER-B sorted insert, VERBATIM, over ONE list whose only
    key is the margin.  Weak margins are <= MG_MAX and DW margins are
    > MG_MAX, so every weak entry sorts ahead of every DW entry: weak
    completeness is structural, truncation drops the WORST DW entry
    first, and the assembly is reused unchanged."""
    A = e.A_MAX
    i = n
    while i > 0 and cm[i - 1] > m:
        i -= 1
    if i >= A:
        return n
    j = n if n < A else A - 1
    while j > i:
        ct[j], cm[j] = ct[j - 1], cm[j - 1]
        j -= 1
    ct[i], cm[i] = k, m
    return n + 1 if n < A else n


def install(e, variant):
    e._VAR = variant
    e._decide_pass = lambda s, K, tau, cal: _dp(e, s, K, tau, cal)
    return e


def _dp(e, samples, K, tau, cal):
    ins = {"V1": None, "V2": _ins_v2, "V3": _ins_v3,
           "V5": None}[e._VAR]
    v5 = e._VAR == "V5"
    NB = e.NB
    A = e.A_MAX
    bits = [0] * NB
    infeasible = label_err = n_seg = 0
    ct = [0] * A
    cm = [0] * A
    nw = nd = 0
    n_weak = n_tied = n_dw = 0
    chk_conf = [0] * e.CHK_LEN
    tie_pend = -1
    nd8 = 8 * e.N_DATA
    for (k0, k1, u, v, fam) in e._seg_stream(samples, K, tau):
        n_seg += 1
        if k0 >= NB:
            continue
        a_hat, c_hat, costs, lo, hi, inter, a_free = e._decide(
            k0, k1, u, v, fam, cal)
        if c_hat > e.INFEAS_U:
            infeasible += 1
        known_all = all(e.KNOWN[t] >= 0 for t in range(k0, min(k1, NB)))
        dead = sum(1 for x in inter if x) >= 2
        if known_all and lo == hi and a_free != lo and not dead:
            label_err += 1
        tie_here = -1
        insl = [a for a in range(lo, hi + 1) if inter[a]]
        if len(insl) >= 2 and a_hat in insl[:2]:
            t = k0 + insl[0]
            if t < NB:
                tie_here = t
        h0c, h1c = cal.h0f[fam], cal.h1f[fam]
        kk1 = min(k1, NB)
        hb = 0
        past = False
        for t in range(k0, kk1):
            off = t - k0
            bits[t] = 1 if off < a_hat else 0
            if past or hb > v:
                past = True
                is_dw = False
            else:
                is_dw = ((hb + h0c) <= u) == (v < (hb + h1c))
            hb += e.BIT_U
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            m = 255 if (c0 is None or c1 is None) else min(255, abs(c0 - c1))
            if t == tie_here or t == tie_pend:
                m = 0
            if e.PP_LO <= t < e.PP_HI:
                k = t - e.PP_LO
                if k >= nd8:
                    chk_conf[(k - nd8) >> 3] = e._u16(
                        chk_conf[(k - nd8) >> 3] + m)
                if m <= e.MG_MAX:
                    n_weak = e._u16(n_weak + 1)
                    if m == 0:
                        n_tied = e._u16(n_tied + 1)
                    if v5:
                        nw = _ins_v5(e, ct, cm, nw, e._u16(k), e._u8(m))
                    else:
                        nw, nd = ins(e, ct, cm, nw, nd, e._u16(k),
                                     e._u8(m), False)
                elif is_dw and e.DW_EN:
                    n_dw = e._u16(n_dw + 1)
                    if v5:
                        nw = _ins_v5(e, ct, cm, nw, e._u16(k), e._u8(m))
                    else:
                        nw, nd = ins(e, ct, cm, nw, nd, e._u16(k),
                                     e._u8(m), True)
        if tie_pend >= 0 and tie_pend < kk1:
            tie_pend = -1
        if tie_here >= kk1:
            tie_pend = tie_here
    if e._VAR == "V5":
        cl_t, cl_m = ct[:nw], cm[:nw]
        nd = 0
    else:
        cl_t = [ct[A - 1 - i] for i in range(nd)] + ct[:nw]
        cl_m = [cm[A - 1 - i] for i in range(nd)] + cm[:nw]
    return dict(bits=bits, infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, cand_t=cl_t, cand_m=cl_m,
                n_weak=n_weak, n_tied=n_tied, n_dw=n_dw,
                n_cw=nw, n_cd=nd, chk_conf=chk_conf)


def mods(key):
    nd, var = key
    if key not in _M:
        base = dwlib.load_ref()
        base._configure(nd)
        base.DW_EN = 0
        m = dwlib.load_ref()
        m._configure(nd)
        if var != "V1":
            install(m, var)
        if var == "V5":
            # every ADMITTED candidate is pair-eligible -- what the C's
            # compiled-out A_PAIR/MG_PAIR test and the assembly already do
            m.MG_PAIR = 255
        _M[key] = (base, m)
    return _M[key]


def one(job):
    key, pat, data, s = job
    b, lb = mods(key)
    o0, i0 = b.decode_ex(s)
    try:
        o1, i1 = lb.decode_ex(s)
    except AssertionError as exc:
        return (pat, o0 == data, False, False, 0, 0, False, i0["cause"],
                "ASSERT:" + str(exc)[:30])
    return (pat, o0 == data, o1 == data, o1 is not None and o1 != data,
            i1.get("comps", 0), i1.get("trials", 0),
            bool(i1.get("budget_hit")), i0["cause"], i1["cause"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    a = ap.parse_args()
    import v23lib as L
    caps = [(p, d, L.linearize(L.capture(d, e, t)))
            for p, d in L.prod_payloads().items() for e in EPS for t in ARM]
    real = []
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        for c in json.loads((NEWIMPL / "data" / fn).read_text())["captures"]:
            real.append((c["pattern"], bytes.fromhex(c["payload"])[:16],
                         linearize(c["capture"])))
    print("%-18s %6s %6s %5s %5s %5s %5s %7s %s"
          % ("variant", "before", "after", "gain", "lost", "WRNG", "bhit",
             "cmpmax", "rnd"))
    for var in ("V1", "V2", "V3", "V5"):
        for nd, pool, tag in ((48, caps, "48"), (16, real, "16r")):
            key = (nd, var)
            jobs = [(key, p, d, s) for (p, d, s) in pool]
            with mp.Pool(a.j) as pl:
                rows = pl.map(one, jobs, chunksize=8)
            asrt = [r for r in rows if str(r[8]).startswith("ASSERT")]
            b = sum(1 for r in rows if r[1])
            aa = sum(1 for r in rows if r[2])
            g = sum(1 for r in rows if r[2] and not r[1])
            lo = sum(1 for r in rows if r[1] and not r[2])
            w = sum(1 for r in rows if r[3])
            bh = sum(1 for r in rows if r[6])
            rnd = sum(1 for r in rows if r[0] == "rnd" and r[2])
            print("%-18s %6d %6d %5d %5d %5d %5d %7d %s%s"
                  % ("%s ND=%s" % (var, tag), b, aa, g, lo, w, bh,
                     max(r[4] for r in rows),
                     ("%d/144" % rnd) if nd == 48 else "",
                     ("  ASSERTS %d" % len(asrt)) if asrt else ""))
            if lo:
                print("   LOST:", [(r[0], r[7], r[8]) for r in rows
                                   if r[1] and not r[2]][:6])


if __name__ == "__main__":
    main()
