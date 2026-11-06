"""E9: matched-filter anchor + payload decode across the HSI envelope,
on synthetic captures whose sampler model is known exactly (synth.py).

Isolates the *technique's* behaviour from residual grid-calibration error.
Reports: anchor (t0, kappa) error, end-of-frame placement error, payload
BER, erasure (zero-margin) rate, exact-frame rate.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/bench")
from patterns import PATTERNS                      # noqa: E402
import synth                                       # noqa: E402

from common import bits_of, HEADER, TRAILER, BIT_NS   # noqa: E402
from mf import wire_from_bits                         # noqa: E402

G_CY = 40.0
P_CY = np.array([0., 4., 8., 12., 16., 20., 26., 31.])
# match the generator we are scoring against (synth.py uses 700/350;
# the REAL captures fold at 750/~360 -- see e6_fold.py)
H1, H0 = synth.T1H_NS, synth.T0H_NS
HDR = bits_of(HEADER)
TRL = bits_of(TRAILER)
T_TRL0 = 160 * BIT_NS
T_END = 192 * BIT_NS
N_HDR = 112


def uphase(it, sl):
    return it * G_CY + P_CY[sl]


def anchor_score(u, lv, t0, k, use_hdr, use_trl):
    s = 0
    if use_hdr:
        t = t0 + k * u[:N_HDR]
        ok = wire_from_bits(t, HDR, H1, H0) == lv[:N_HDR]
        s += int(ok.sum()) - int((~ok).sum())
    if use_trl:
        t = t0 + k * u
        m = (t >= T_TRL0) & (t < T_END)
        if m.sum() < 40:
            return -10 ** 6
        ok = wire_from_bits(t[m] - T_TRL0, TRL, H1, H0) == lv[m]
        s += int(ok.sum()) - int((~ok).sum())
    return s


def lock(u, lv, t0s, ks, use_hdr=True, use_trl=True):
    best = (-1e9, 0, 0)
    for k in ks:
        for t0 in t0s:
            s = anchor_score(u, lv, t0, k, use_hdr, use_trl)
            if s > best[0]:
                best = (s, t0, k)
    s, t0, k = best
    st, sk = 4.0, 0.06
    while st > 1e-3:
        f = None
        for a, b in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                     (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            ss = anchor_score(u, lv, t0 + a, k + b, use_hdr, use_trl)
            if ss > s:
                s, f = ss, (t0 + a, k + b)
        if f is None:
            st /= 2
            sk /= 2
        else:
            t0, k = f
    return s, t0, k


def soft_payload(u, lv, t0, k):
    t = t0 + k * u
    hard = np.zeros(128, int)
    marg = np.zeros(128, int)
    imposs = 0
    for j in range(32, 160):
        lo = j * BIT_NS
        m = (t >= lo) & (t < lo + BIT_NS)
        if not m.any():
            continue
        ph = t[m] - lo
        obs = lv[m]
        p1 = ph < H1
        p0 = ph < H0
        s1 = int((p1 == obs).sum()) - int((p1 != obs).sum())
        s0 = int((p0 == obs).sum()) - int((p0 != obs).sum())
        hard[j - 32] = 1 if s1 > s0 else 0
        marg[j - 32] = s1 - s0
        imposs += int(((ph >= H1) & obs).sum() + ((ph < H0) & ~obs).sum())
    return hard, marg, imposs


def run(eps_points):
    print(f"{'eps':>8} {'dt0':>8} {'dk%':>8} {'endErr':>9} {'BER%':>7} "
          f"{'eras%':>7} {'imposs':>7} {'exact':>7}")
    for eps in eps_points:
        dt0 = []
        dk = []
        ee = []
        ber = 0
        nb = 0
        er = 0
        imp = 0
        ex = 0
        ncap = 0
        for name, payload in PATTERNS.items():
            for r in range(3):
                ph = (r * 83.0) % 250.0
                s = synth.synth_capture(payload, eps=eps, phase_ns=ph)
                it = np.array([a for a, _, _ in s], float)
                sl = np.array([b for _, b, _ in s])
                lv = np.array([v for _, _, v in s], bool)
                u = uphase(it, sl)
                kap_true = 62.5 / (1 + eps)
                _, t0, k = lock(u, lv, np.arange(0., 460., 4.),
                                np.arange(56.0, 69.0, 0.02))
                dt0.append(t0 - ph)
                dk.append(100 * (k - kap_true) / kap_true)
                nlast = 760 if len(u) > 760 else len(u) - 1
                ee.append((t0 + k * u[nlast]) - (ph + kap_true * u[nlast]))
                hard, marg, ii = soft_payload(u, lv, t0, k)
                truth = bits_of(payload)
                e = int((hard != truth).sum())
                ber += e
                nb += 128
                er += int((marg == 0).sum())
                imp += ii
                ex += (e == 0)
                ncap += 1
        print(f"{eps:+8.3f} {np.mean(np.abs(dt0)):8.1f} "
              f"{np.mean(np.abs(dk)):8.4f} {np.mean(np.abs(ee)):9.1f} "
              f"{100*ber/nb:7.3f} {100*er/nb:7.2f} {imp/ncap:7.2f} "
              f"{ex:3d}/{ncap:<3d}")


if __name__ == "__main__":
    run([-0.08, -0.075, -0.05, -0.025, -0.01, -0.003, 0.0,
         0.01, 0.025, 0.05, 0.075, 0.08])
