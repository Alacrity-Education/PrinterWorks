#!/usr/bin/env python3
"""Pick G_MAX / G_CAP and attribute the gain between the MID and DEAD
sub-classes.  Also probe A_MAX head-room (a_extra) so the report can say
what a larger list would buy WITHOUT changing it."""
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
import proto                                                   # noqa: E402
from harness import linearize                                  # noqa: E402

EPS = [round(-0.025 + i * 0.0025, 6) for i in range(12)]
ARM_T0 = [70.0 + i * (658.0 - 70.0) / 11 for i in range(12)]
_M = {}


def geom_only(e, which):
    """Restrict GEOM to one sub-class: 'mid' (bracket inside window) or
    'dead' (window inside bracket)."""
    orig = proto._decide_pass

    def dp(ee, s, K, tau, cal):
        return orig(ee, s, K, tau, cal)
    e._GEOM_WHICH = which
    return e


def mods(key):
    nd, gmax, gcap, aextra, which = key
    if key not in _M:
        base = dwlib.load_ref()
        base._configure(nd)
        lb = proto.load(nd, g_max=gmax, g_cap=gcap, a_extra=aextra)
        if which != "both":
            _patch_which(lb, which)
        _M[key] = (base, lb)
    return _M[key]


def _patch_which(e, which):
    """Replace the GEOM predicate: ga==gb splits into MID (ga=gb=1) and
    DEAD (ga=gb=0)."""
    src_dp = proto._decide_pass

    def dp(samples, K, tau, cal):
        e._WHICH = which
        return src_dp(e, samples, K, tau, cal)
    # simplest: wrap _decide via a flag consumed inside a re-implemented
    # loop -- instead we post-filter by monkeypatching the predicate used
    # in proto through a module-level hook.
    e._GEOM_FILTER = which
    e._decide_pass = lambda s, K, tau, cal: _dp_filtered(e, s, K, tau, cal)


def _dp_filtered(e, samples, K, tau, cal):
    """proto._decide_pass with the GEOM predicate narrowed."""
    which = e._GEOM_FILTER
    NB = e.NB
    bits = [0] * NB
    infeasible = label_err = n_seg = 0
    cand_t, cand_m = [], []
    n_g = 0
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
                g = False
            else:
                ga = (hb + h0c) <= u
                gb = v < (hb + h1c)
                g = (ga and gb) if which == "mid" else \
                    ((not ga) and (not gb)) if which == "dead" else \
                    (ga == gb)
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
                wk = m <= e.MG_MAX
                if wk:
                    n_weak = e._u16(n_weak + 1)
                    if m == 0:
                        n_tied = e._u16(n_tied + 1)
                if g:
                    n_geom = e._u16(n_geom + 1)
                if g or wk:
                    n_g = proto._cand_insert(e, cand_t, cand_m, n_g,
                                             e._u16(k), e._u8(m), g)
        if tie_pend >= 0 and tie_pend < kk1:
            tie_pend = -1
        if tie_here >= kk1:
            tie_pend = tie_here
    return dict(bits=bits, infeasible=infeasible, label_err=label_err,
                n_seg=n_seg, cand_t=cand_t, cand_m=cand_m,
                n_weak=n_weak, n_tied=n_tied, n_geom=n_geom, n_g=n_g,
                chk_conf=chk_conf)


def one(job):
    key, pat, data, samples = job
    base, lb = mods(key)
    o0, i0 = base.decode_ex(samples)
    o1, i1 = lb.decode_ex(samples)
    return (pat, o0 == data, o1 == data, o0 is not None and o0 != data,
            o1 is not None and o1 != data, i1.get("comps", 0),
            i1.get("trials", 0), i1.get("n_geom", 0),
            bool(i1.get("budget_hit")), i0["cause"], i1["cause"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=20)
    a = ap.parse_args()
    import v23lib as L
    caps = []
    for pat, data in L.prod_payloads().items():
        for eps in EPS:
            for t0 in ARM_T0:
                caps.append((pat, data, L.linearize(L.capture(data, eps, t0))))
    real = []
    for fn in ("captures_v23.json", "captures_v23_val.json"):
        d = json.loads((NEWIMPL / "data" / fn).read_text())
        for c in d["captures"]:
            real.append((c["pattern"], bytes.fromhex(c["payload"])[:16],
                         linearize(c["capture"])))
    print("SYNTH ND=48 plateau(-2.5..+0.25 %% at 0.25) x 12 arm phases: "
          "%d frames | REAL ND=16: %d" % (len(caps), len(real)))
    print("\n%-28s %6s %6s %6s %6s %5s %5s %6s"
          % ("variant", "before", "after", "gain", "lost", "WRNG", "bhit",
             "cmpmax"))
    for which in ("dead", "mid", "both"):
        for gmax, gcap in ((8, 24),):
            for nd, pool, tag in ((48, caps, "48"), (16, real, "16real")):
                key = (nd, gmax, gcap, 0, which)
                jobs = [(key, p, d, s) for (p, d, s) in pool]
                with mp.Pool(a.j) as pl:
                    rows = pl.map(one, jobs, chunksize=8)
                b = sum(1 for r in rows if r[1])
                aa = sum(1 for r in rows if r[2])
                g = sum(1 for r in rows if r[2] and not r[1])
                lo = sum(1 for r in rows if r[1] and not r[2])
                w = sum(1 for r in rows if r[4])
                bh = sum(1 for r in rows if r[8])
                cm = max(r[5] for r in rows)
                print("%-28s %6d %6d %6d %6d %5d %5d %6d"
                      % ("geom=%s ND=%s G=%d/%d" % (which, tag, gmax, gcap),
                         b, aa, g, lo, w, bh, cm))
    print()
    for gmax in (3, 5, 8, 11):
        for gcap in (12, 16, 24, 48, 10 ** 6):
            key = (48, gmax, gcap, 0, "both")
            jobs = [(key, p, d, s) for (p, d, s) in caps]
            with mp.Pool(a.j) as pl:
                rows = pl.map(one, jobs, chunksize=8)
            b = sum(1 for r in rows if r[1])
            aa = sum(1 for r in rows if r[2])
            g = sum(1 for r in rows if r[2] and not r[1])
            lo = sum(1 for r in rows if r[1] and not r[2])
            w = sum(1 for r in rows if r[4])
            bh = sum(1 for r in rows if r[8])
            cm = max(r[5] for r in rows)
            rnd = sum(1 for r in rows if r[0] == "rnd" and r[2])
            print("%-28s %6d %6d %6d %6d %5d %5d %6d   rnd %d/144"
                  % ("G_MAX=%d G_CAP=%s" % (gmax, gcap if gcap < 1000
                                            else "inf"),
                     b, aa, g, lo, w, bh, cm, rnd))


if __name__ == "__main__":
    main()
