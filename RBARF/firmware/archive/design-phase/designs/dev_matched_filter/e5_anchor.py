"""E5: anchor lock.  Header-only vs trailer-only vs joint (t0, kappa)
matched-filter locks, compared against the oracle full-frame fit.
Then payload decoding from the joint anchor with per-cell soft scores.
"""
import json
import sys

import numpy as np

from common import load, bits_of, BIT_NS, HEADER, TRAILER
from mf import phase, wire_from_bits

cal_file = sys.argv[1] if len(sys.argv) > 1 else "e2_oracle.json"
cal = json.load(open(cal_file))
G = cal.get("G", 40.0)
P = np.array(cal.get("P", [0., 4., 8., 12., 16., 20., 26., 31.]))
H1 = cal.get("h1", cal.get("H1", 750.0))
H0 = cal.get("h0", cal.get("H0", 375.0))
ORACLE = json.load(open("e2_oracle.json"))["res"]

HDR = bits_of(HEADER)
TRL = bits_of(TRAILER)
NB_HDR = 32
NB_TRL = 32
T_HDR = NB_HDR * BIT_NS                      # 40000 ns
T_TRL0 = (192 - NB_TRL) * BIT_NS             # 200000 ns
T_END = 192 * BIT_NS
NW = 1100
N_HDR_SAFE = 112       # samples guaranteed inside header over +-7.5%


def hdr_score(u, lv, t0, k, h1, h0, n=N_HDR_SAFE):
    t = t0 + k * u[:n]
    pred = wire_from_bits(t, HDR, h1, h0)
    ok = (pred == lv[:n].astype(bool))
    return int(ok.sum()) - int((~ok).sum())


def trl_score(u, lv, t0, k, h1, h0):
    t = t0 + k * u
    m = (t >= T_TRL0) & (t < T_END)
    if m.sum() < 40:
        return -10 ** 6, 0
    tt = t[m] - T_TRL0
    pred = wire_from_bits(tt, TRL, h1, h0)
    ok = (pred == lv[m].astype(bool))
    return int(ok.sum()) - int((~ok).sum()), int(m.sum())


def grid_search(u, lv, t0s, ks, h1, h0, use_hdr=True, use_trl=True):
    best = None
    S = np.full((len(t0s), len(ks)), -1e9)
    for b, k in enumerate(ks):
        for a, t0 in enumerate(t0s):
            s = 0
            if use_hdr:
                s += hdr_score(u, lv, t0, k, h1, h0)
            if use_trl:
                s += trl_score(u, lv, t0, k, h1, h0)[0]
            S[a, b] = s
    a, b = np.unravel_index(np.argmax(S), S.shape)
    return S, t0s[a], ks[b]


def local(u, lv, t0, k, h1, h0, use_hdr, use_trl, st=8.0, sk=0.05):
    def sc(t0, k):
        s = 0
        if use_hdr:
            s += hdr_score(u, lv, t0, k, h1, h0)
        if use_trl:
            s += trl_score(u, lv, t0, k, h1, h0)[0]
        return s
    m = sc(t0, k)
    while st > 1e-3:
        f = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            mm = sc(t0 + a, k + b)
            if mm > m:
                m, f = mm, (t0 + a, k + b)
        if f is None:
            st /= 2
            sk /= 2
        else:
            t0, k = f
    return m, t0, k


def decode_payload(u, lv, t0, k, h1, h0):
    """per-cell 0/1 matched score for payload bits 32..159."""
    t = t0 + k * u
    hard = []
    marg = []
    for j in range(32, 160):
        lo, hi = j * BIT_NS, (j + 1) * BIT_NS
        m = (t >= lo) & (t < hi)
        if m.sum() == 0:
            hard.append(0)
            marg.append(0)
            continue
        ph_ = t[m] - lo
        obs = lv[m].astype(bool)
        s1 = int(((ph_ < h1) == obs).sum()) - int(((ph_ < h1) != obs).sum())
        s0 = int(((ph_ < h0) == obs).sum()) - int(((ph_ < h0) != obs).sum())
        hard.append(1 if s1 > s0 else 0)
        marg.append(s1 - s0)
    return np.array(hard), np.array(marg)


def main():
    meta, caps = load()
    t0s = np.arange(-400., 500., 4.)
    ks = np.arange(58.0, 68.0, 0.02)
    rows = []
    tot_bit_err = 0
    tot_bits = 0
    exact = 0
    amb = 0
    for c in caps:
        it, sl, lv = c["it"][:NW].astype(float), c["sl"][:NW], c["lv"][:NW]
        u = phase(it, sl, G, P)
        ot0, ok_ = ORACLE[c["key"]][:2]

        _, ht0, hk = grid_search(u, lv, t0s, ks, H1, H0, True, False)
        _, ht0, hk = local(u, lv, ht0, hk, H1, H0, True, False)
        _, jt0, jk = grid_search(u, lv, t0s, ks, H1, H0, True, True)
        sj, jt0, jk = local(u, lv, jt0, jk, H1, H0, True, True)

        hard, marg = decode_payload(u, lv, jt0, jk, H1, H0)
        truth = c["bits"][32:160]
        err = int((hard != truth).sum())
        tot_bit_err += err
        tot_bits += 128
        amb += int((marg == 0).sum())
        pay = bytes(int("".join(map(str, hard[i:i + 8])), 2) for i in range(0, 128, 8))
        ok = pay == c["payload"]
        exact += ok
        # end-of-frame placement error using the header-only lock
        e_end_h = (ht0 + hk * u[760]) - (ot0 + ok_ * u[760])
        e_end_j = (jt0 + jk * u[760]) - (ot0 + ok_ * u[760])
        rows.append((c["key"], ht0 - ot0, hk - ok_, e_end_h, jt0 - ot0,
                     jk - ok_, e_end_j, err, ok))
        print(f"{c['key']:14s} hdr: dt0={ht0-ot0:+8.1f} dk={hk-ok_:+.4f} "
              f"end_err={e_end_h:+9.1f}ns | joint: dt0={jt0-ot0:+8.1f} "
              f"dk={jk-ok_:+.4f} end_err={e_end_j:+8.1f}ns | biterr={err:3d} "
              f"{'OK' if ok else '  '}", flush=True)

    a = np.array([[r[3], r[6]] for r in rows])
    print("\nheader-only end-of-frame placement error (ns): "
          f"mean|.|={np.abs(a[:,0]).mean():.1f} max|.|={np.abs(a[:,0]).max():.1f}")
    print("joint end-of-frame placement error (ns): "
          f"mean|.|={np.abs(a[:,1]).mean():.1f} max|.|={np.abs(a[:,1]).max():.1f}")
    print(f"payload BER {tot_bit_err}/{tot_bits} = {100*tot_bit_err/tot_bits:.3f}%")
    print(f"exact frames {exact}/{len(caps)}")
    print(f"zero-margin (undecidable) cells {amb}/{tot_bits}")


main()
