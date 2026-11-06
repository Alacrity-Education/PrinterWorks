"""LEVER B prototype: geometry-aware candidates, bolted onto a FRESH
embedded_v2 instance by monkeypatch so several parameter sets can be
measured side by side without editing the normative reference.

The design under test:

  * per payload' bit, GEOM = the bit's discriminating interval and the
    fall bracket fail to interleave:
        ga = (A <= u)      A = off*BIT_U + h0c   (fall position if 0)
        gb = (v <  B)      B = off*BIT_U + h1c   (fall position if 1)
        GEOM = (ga == gb)
    ga != gb is the healthy case: exactly one of the two candidate fall
    positions lies inside the observed bracket, i.e. a sample DECIDED
    the bit.  ga == gb splits into
        MID  (ga=gb=1): the bracket lies inside the window -- a
              transition was seen, but at NEITHER fitted boundary
        DEAD (ga=gb=0): the window lies inside the bracket -- no sample
              inside it at all, both hypotheses admitted
  * GEOM bits join the candidate list regardless of margin, as a PREFIX
    ranked by ascending (margin, bit index); the weak bits (m <= MG_MAX)
    follow, ranked the same way.  n_g = size of the prefix.
  * counters: n_weak unchanged (all m <= MG_MAX), n_geom = all GEOM bits.
  * R6 refuses only when BOTH pools are empty; R7 (weak completeness) is
    unchanged.
"""
import sys
from pathlib import Path

SC = Path(__file__).resolve().parent
sys.path.insert(0, str(SC))
import dwlib                                                   # noqa: E402

G_MAX = 8           # geometric prefix capacity
G_CAP = 24          # n_geom above this = the frame is broadly unresolved
                    # -> the prefix cannot contain the ambiguity, refuse
GEOM_EN = True


def install(e, g_max=None, g_cap=None, geom_en=None, a_extra=0,
            kw_geo_ones=False, kw_geo_d1=False):
    e.G_MAX = G_MAX if g_max is None else g_max
    e.G_CAP = G_CAP if g_cap is None else g_cap
    e.GEOM_EN = GEOM_EN if geom_en is None else geom_en
    e.A_TOT = e.A_MAX + a_extra
    e.GEO_ONES = bool(kw_geo_ones)
    e.GEO_D1 = bool(kw_geo_d1)
    e._decide_pass = lambda s, K, tau, cal: _decide_pass(e, s, K, tau, cal)
    e._chase23 = lambda st, info, D, C, nd8: _chase23(e, st, info, D, C, nd8)
    return e


def _geo_insert(e, geo_t, geo_m, k, m, bv=0):
    """Streaming top-G_MAX insertion, key (margin, bit index) ascending --
    the SS6.2 rule applied to a second, independent pool.  The weak pool
    and its completeness invariant (R7) are untouched."""
    key = (m,) if not e.GEO_ONES else ((0 if bv else 1), m)
    i = len(geo_t)
    while i > 0 and geo_m[i - 1] > key:
        i -= 1
    if i >= e.G_MAX:
        return
    geo_t.insert(i, k)
    geo_m.insert(i, key)
    if len(geo_t) > e.G_MAX:
        geo_t.pop()
        geo_m.pop()


def _decide_pass(e, samples, K, tau, cal):
    NB = e.NB
    bits = [0] * NB
    infeasible = label_err = n_seg = 0
    cand_t, cand_m = [], []
    geo_t, geo_m = [], []
    n_weak = n_tied = n_geom = 0
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
        ins = [a for a in range(lo, hi + 1) if inter[a]]
        if len(ins) >= 2 and a_hat in ins[:2]:
            t = k0 + ins[0]
            if t < NB:
                tie_here = t
        h0c, h1c = cal.h0f[fam], cal.h1f[fam]
        kk1 = min(k1, NB)
        hb = 0
        over = False
        for t in range(k0, kk1):
            off = t - k0
            bits[t] = 1 if off < a_hat else 0
            if over or hb > v:
                over = True
                geom = False
            else:
                geom = ((hb + h0c) <= u) == (v < (hb + h1c))
            hb += e.BIT_U
            c1 = min((costs[a] for a in range(lo, hi + 1) if a > off),
                     default=None)
            c0 = min((costs[a] for a in range(lo, hi + 1) if a <= off),
                     default=None)
            if c0 is None or c1 is None:
                m = 255
            else:
                m = min(255, abs(c0 - c1))
            if t == tie_here or t == tie_pend:
                m = 0
            if e.PP_LO <= t < e.PP_HI:
                k = t - e.PP_LO
                if k >= nd8:
                    chk_conf[(k - nd8) >> 3] = e._u16(
                        chk_conf[(k - nd8) >> 3] + m)
                wk = m <= e.MG_MAX
                if wk:
                    n_weak = e._u16(n_weak + 1)
                    if m == 0:
                        n_tied = e._u16(n_tied + 1)
                    e._cand_insert(cand_t, cand_m, e._u16(k), e._u8(m))
                elif geom and e.GEOM_EN:
                    n_geom = e._u16(n_geom + 1)
                    if not e.GEO_D1 or bits[t]:
                        _geo_insert(e, geo_t, geo_m, e._u16(k), e._u8(m),
                                    bits[t])
        if tie_pend >= 0 and tie_pend < kk1:
            tie_pend = -1
        if tie_here >= kk1:
            tie_pend = tie_here
    return dict(bits=bits, infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, cand_t=cand_t, cand_m=cand_m,
                geo_t=geo_t, geo_m=geo_m,
                n_weak=n_weak, n_tied=n_tied, n_geom=n_geom,
                n_g=len(geo_t), chk_conf=chk_conf)


def _chase23(e, st, info, D, C, nd8):
    conf = st["chk_conf"]
    r_base = e._crc16(bytes(D))
    hi, lo = e._ref_bytes(C)
    have_R = hi is not None and lo is not None
    info["r_base"] = r_base
    info["majority"] = ((hi << 8) | lo) if have_R else None
    info["ref_split"] = (hi is None) + (lo is None)
    cap = e.REF_MAX if (e.CHASE_SPLIT_VOTE
                        and info["violations"] <= e.MK_SOFT) else 1
    info["ref_cap"] = cap
    refs = e._ref_candidates(C, conf, cap)
    info["n_refs"] = len(refs)
    info["n_geom"] = st.get("n_geom", 0)
    if st["n_tied"] > e.TIE_EMIT:
        info["cause"] = "refuse_emitgate"
        return None
    comps = [0]

    def match(r, rset):
        for R in rset:
            if comps[0] >= e.T_MAX:
                return None
            comps[0] += 1
            if r == R:
                return True
        return False

    m = match(r_base, refs)
    if m:
        info["path"] = "direct"
        info["comps"] = comps[0]
        return bytes(D)
    n_geom = st.get("n_geom", 0)
    if st["n_weak"] == 0 and n_geom == 0:
        info["cause"] = "refuse_nocand"
        info["comps"] = comps[0]
        return None
    if st["n_weak"] > e.A_MAX:
        info["cause"] = "refuse_admit"
        info["comps"] = comps[0]
        return None
    cand_t = list(st["geo_t"]) + list(st["cand_t"])
    cand_m = [(x[-1] if isinstance(x, tuple) else x)
              for x in st["geo_m"]] + list(st["cand_m"])
    n = len(cand_t)
    isd = [cand_t[i] < nd8 for i in range(n)]
    pars = [e._parity16(r_base ^ R) for R in refs]
    skip3 = all(q == 0 for q in pars)
    skip5 = all(q == 1 for q in pars)
    info["chased"] = True
    npair = n                                     # every admitted entry
    info["npair"] = npair
    trials = 0
    for S in e._enum_trials(isd, skip3, skip5, npair):
        trials += 1
        Cp = list(C)
        r = r_base
        touched_chk = False
        for i in S:
            k = cand_t[i]
            if k < nd8:
                r = e._u16(r ^ e._syn16(k))
            else:
                q = (k - nd8) >> 3
                Cp[q] = e._u8(Cp[q] ^ (1 << (7 - (k & 7))))
                touched_chk = True
        rset = e._ref_candidates(Cp, conf, cap) if touched_chk else refs
        m = match(r, rset)
        if m is None:
            info["trials"] = trials
            info["comps"] = comps[0]
            info["budget_hit"] = True
            info["cause"] = "refuse_chase"
            return None
        if not m:
            continue
        D2 = bytearray(D)
        for i in S:
            k = cand_t[i]
            if k < nd8:
                D2[k >> 3] ^= 1 << (7 - (k & 7))
        info["path"] = "chase"
        info["trials"] = trials
        info["comps"] = comps[0]
        info["flips"] = tuple(cand_t[i] for i in S)
        return bytes(D2)
    info["trials"] = trials
    info["comps"] = comps[0]
    info["cause"] = "refuse_chase"
    return None


def load(nd, **kw):
    e = dwlib.load_ref()
    e._configure(nd)
    return install(e, **kw)
