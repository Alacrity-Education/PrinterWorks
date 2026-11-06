"""E10: SOFT matched filter.

Template is probabilistic:  P(sample reads HIGH | cell phase p, bit b) =
    q_b(p) = Phi(p/sigma) * Phi((h_b - p)/sigma)
with sigma the effective edge-transition width (input threshold + slot-offset
residual + anchor residual).  A sample near a template edge then carries
partial information, which shrinks the erasure set.

Stage 1: header-only lock over (t0, kappa) -- coarse kappa.
Stage 2: header+trailer joint refinement -- long-lever kappa.
Stage 3: per-payload-cell LLR.
"""
import sys

import numpy as np

sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/recon")
sys.path.insert(0, "/home/alex.lucaci/Projects/RBARF/new-implementation/bench")
from patterns import PATTERNS                    # noqa: E402
import synth                                     # noqa: E402

from common import bits_of, HEADER, TRAILER, BIT_NS   # noqa: E402

G_CY = 40.0
P_CY = np.array([0., 4., 8., 12., 16., 20., 26., 31.])
HDR = bits_of(HEADER).astype(bool)
TRL = bits_of(TRAILER).astype(bool)
NB = 192
T_TRL0 = 160 * BIT_NS
T_END = NB * BIT_NS
N_HDR = 112
PCLIP = 2e-3

_SQ2 = np.sqrt(2.0)


def Phi(x):
    from scipy.special import erf
    return 0.5 * (1.0 + erf(x / _SQ2))


try:
    import scipy.special  # noqa: F401
except ImportError:                                   # fallback
    def Phi(x):                                       # noqa: F811
        return 0.5 * (1.0 + np.tanh(1.2 * x))


def qprob(p, h, sigma):
    """P(read HIGH) at cell phase p for a pulse [0, h)."""
    q = Phi(p / sigma) * Phi((h - p) / sigma)
    return np.clip(q, PCLIP, 1.0 - PCLIP)


def loglik(obs, q):
    return np.where(obs, np.log(q), np.log1p(-q))


def template_ll(t, obs, bits, h1, h0, sigma, t_lo, t_hi):
    """log-likelihood of the observed samples under a known bit template
    covering wire times [t_lo, t_hi)."""
    m = (t >= t_lo) & (t < t_hi)
    if not m.any():
        return -1e9, 0
    tt = t[m] - t_lo
    j = np.floor(tt / BIT_NS).astype(int)
    j = np.clip(j, 0, len(bits) - 1)
    p = tt - j * BIT_NS
    h = np.where(bits[j], h1, h0)
    return float(loglik(obs[m], qprob(p, h, sigma)).sum()), int(m.sum())


def lock(u, obs, h1, h0, sigma, t0s, ks, kwin=None, t0win=None):
    """Stage 1 (header) then stage 2 (header+trailer)."""
    best = (-1e18, 0.0, 0.0)
    uh, oh = u[:N_HDR], obs[:N_HDR]
    for k in ks:
        t = t0s[:, None] + k * uh[None, :]
        j = np.floor(t / BIT_NS).astype(int)
        inb = (j >= 0) & (j < 32)
        jj = np.clip(j, 0, 31)
        p = t - jj * BIT_NS
        h = np.where(HDR[jj], h1, h0)
        ll = loglik(oh[None, :], qprob(p, h, sigma))
        s = np.where(inb, ll, 0.0).sum(1)
        a = int(np.argmax(s))
        if s[a] > best[0]:
            best = (float(s[a]), float(t0s[a]), float(k))
    _, t0h, kh = best

    # stage 2: joint, kappa refined on the 200 us lever arm
    kw = kwin if kwin is not None else 0.6
    tw = t0win if t0win is not None else 40.0
    best2 = (-1e18, t0h, kh)
    for k in np.arange(kh - kw, kh + kw, 0.004):
        for t0 in np.arange(t0h - tw, t0h + tw, 2.0):
            t = t0 + k * u
            a, _ = template_ll(t, obs, HDR, h1, h0, sigma, 0.0, 32 * BIT_NS)
            b, nb_ = template_ll(t, obs, TRL, h1, h0, sigma, T_TRL0, T_END)
            if nb_ < 40:
                continue
            if a + b > best2[0]:
                best2 = (a + b, t0, k)
    s, t0, k = best2
    st, sk = 2.0, 0.02
    while st > 1e-3:
        f = None
        for da, db in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            t = (t0 + da) + (k + db) * u
            a, _ = template_ll(t, obs, HDR, h1, h0, sigma, 0.0, 32 * BIT_NS)
            b, nb_ = template_ll(t, obs, TRL, h1, h0, sigma, T_TRL0, T_END)
            if nb_ >= 40 and a + b > s:
                s, f = a + b, (t0 + da, k + db)
        if f is None:
            st /= 2
            sk /= 2
        else:
            t0, k = f
    return s, t0, k, kh


def payload_llr(u, obs, t0, k, h1, h0, sigma):
    t = t0 + k * u
    llr = np.zeros(128)
    ndis = np.zeros(128, int)
    for j in range(32, 160):
        lo = j * BIT_NS
        m = (t >= lo) & (t < lo + BIT_NS)
        if not m.any():
            continue
        p = t[m] - lo
        o = obs[m]
        q1 = qprob(p, h1, sigma)
        q0 = qprob(p, h0, sigma)
        llr[j - 32] = float((loglik(o, q1) - loglik(o, q0)).sum())
        ndis[j - 32] = int(((p >= h0) & (p < h1)).sum())
    return llr, ndis


def run(eps_points, sigma, h1=None, h0=None, tag=""):
    h1 = synth.T1H_NS if h1 is None else h1
    h0 = synth.T0H_NS if h0 is None else h0
    print(f"--- sigma={sigma} h1={h1} h0={h0} {tag}")
    print(f"{'eps':>8} {'dk%':>8} {'endErr':>9} {'BER%':>7} {'eras%':>7} "
          f"{'|llr|<1%':>9} {'exact':>8} {'lockfail':>8}")
    for eps in eps_points:
        ber = nb = er = wk = 0
        ee = []
        dks = []
        ex = 0
        ncap = 0
        lf = 0
        for name, payload in PATTERNS.items():
            for r in range(3):
                ph = (r * 83.0) % 250.0
                s = synth.synth_capture(payload, eps=eps, phase_ns=ph)
                it = np.array([a for a, _, _ in s], float)
                sl = np.array([b for _, b, _ in s])
                obs = np.array([v for _, _, v in s], bool)
                u = it * G_CY + P_CY[sl]
                ktrue = 62.5 / (1 + eps)
                _, t0, k, kh = lock(u, obs, h1, h0, sigma,
                                    np.arange(0., 460., 4.),
                                    np.arange(56.0, 69.0, 0.02))
                nlast = 760
                ee.append((t0 + k * u[nlast]) - (ph + ktrue * u[nlast]))
                dks.append(100 * (k - ktrue) / ktrue)
                if abs(ee[-1]) > 300:
                    lf += 1
                llr, ndis = payload_llr(u, obs, t0, k, h1, h0, sigma)
                hard = (llr > 0).astype(int)
                truth = bits_of(payload)
                e = int((hard != truth).sum())
                ber += e
                nb += 128
                er += int((ndis == 0).sum())
                wk += int((np.abs(llr) < 1.0).sum())
                ex += (e == 0)
                ncap += 1
        print(f"{eps:+8.3f} {np.mean(np.abs(dks)):8.4f} "
              f"{np.mean(np.abs(ee)):9.1f} {100*ber/nb:7.3f} "
              f"{100*er/nb:7.2f} {100*wk/nb:9.2f} {ex:3d}/{ncap:<4d} {lf:8d}")


if __name__ == "__main__":
    pts = [-0.075, -0.03, -0.003, 0.0, 0.03, 0.075]
    for sg in (float(x) for x in sys.argv[1:] or ["1.0", "60.0", "110.0", "160.0"]):
        run(pts, sg)
