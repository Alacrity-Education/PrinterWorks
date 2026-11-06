"""E11: composition-relevant metrics + anchor ablations, on synth.

  * erasure rate (cells with no discriminating sample)
  * BER among DECIDABLE cells   (target: ~0)
  * anchor lock failure rate, "impossible sample" self-check
  * ablations: header-only / trailer-only / joint;
               header with its 00 byte (bits 8..15) removed from the template
"""
import sys
from collections import Counter

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
H1, H0 = synth.T1H_NS, synth.T0H_NS
T_TRL0 = 160 * BIT_NS
T_END = 192 * BIT_NS
N_HDR = 112


def seg_score(t, obs, bits, t_lo, t_hi, bitmask=None):
    """bipolar match score over a known template segment."""
    m = (t >= t_lo) & (t < t_hi)
    if not m.any():
        return -10 ** 6, 0
    tt = t[m] - t_lo
    j = np.clip(np.floor(tt / BIT_NS).astype(int), 0, len(bits) - 1)
    if bitmask is not None:
        keep = bitmask[j]
        if not keep.any():
            return -10 ** 6, 0
        j, tt = j[keep], tt[keep]
        o = obs[m][keep]
    else:
        o = obs[m]
    p = tt - j * BIT_NS
    pred = p < np.where(bits[j], H1, H0)
    ok = pred == o
    return int(ok.sum()) - int((~ok).sum()), int(ok.size)


def lock(u, obs, use_hdr=True, use_trl=True, hdr_mask=None):
    t0s = np.arange(0., 460., 4.)
    ks = np.arange(56.0, 69.0, 0.02)
    # stage 1: coarse, vectorised over t0
    best = (-1e18, 0., 62.5)
    uh, oh = u[:N_HDR], obs[:N_HDR]
    for k in ks:
        t = t0s[:, None] + k * uh[None, :]
        j = np.floor(t / BIT_NS).astype(int)
        inb = (j >= 0) & (j < 32)
        jj = np.clip(j, 0, 31)
        p = t - jj * BIT_NS
        pred = p < np.where(HDR[jj], H1, H0)
        good = (pred == oh[None, :])
        if hdr_mask is not None:
            inb = inb & hdr_mask[jj]
        s = np.where(inb, np.where(good, 1, -1), 0).sum(1)
        a = int(np.argmax(s))
        if s[a] > best[0]:
            best = (float(s[a]), float(t0s[a]), float(k))
    _, t0, k = best
    if not use_trl:
        return t0, k

    def sc(t0, k):
        t = t0 + k * u
        s = 0
        if use_hdr:
            s += seg_score(t, obs, HDR, 0.0, 32 * BIT_NS, hdr_mask)[0]
        a, n = seg_score(t, obs, TRL, T_TRL0, T_END)
        if n < 40:
            return -10 ** 6
        return s + a
    b2 = (-1e18, t0, k)
    for kk in np.arange(k - 0.6, k + 0.6, 0.004):
        for tt in np.arange(max(0., t0 - 40), t0 + 40, 2.0):
            v = sc(tt, kk)
            if v > b2[0]:
                b2 = (v, tt, kk)
    s, t0, k = b2
    st, sk = 2.0, 0.02
    while st > 1e-3:
        f = None
        for da, db in ((st, 0), (-st, 0), (0, sk), (0, -sk),
                       (st, sk), (st, -sk), (-st, sk), (-st, -sk)):
            v = sc(t0 + da, k + db)
            if v > s:
                s, f = v, (t0 + da, k + db)
        if f is None:
            st /= 2
            sk /= 2
        else:
            t0, k = f
    return t0, k


def cells(u, obs, t0, k):
    t = t0 + k * u
    hard = np.zeros(128, int)
    marg = np.zeros(128, int)
    ndis = np.zeros(128, int)
    imposs = 0
    for j in range(32, 160):
        lo = j * BIT_NS
        m = (t >= lo) & (t < lo + BIT_NS)
        if not m.any():
            continue
        p = t[m] - lo
        o = obs[m]
        s1 = int(((p < H1) == o).sum()) - int(((p < H1) != o).sum())
        s0 = int(((p < H0) == o).sum()) - int(((p < H0) != o).sum())
        hard[j - 32] = 1 if s1 > s0 else 0
        marg[j - 32] = s1 - s0
        ndis[j - 32] = int(((p >= H0) & (p < H1)).sum())
        imposs += int(((p >= H1) & o).sum())
    return hard, marg, ndis, imposs


def one_eps(eps, mode):
    use_hdr, use_trl, hm = mode
    tot = dict(nb=0, era=0, errd=0, err=0, ex=0, cap=0, imp=0, lf=0)
    runs = Counter()
    ee = []
    for name, payload in PATTERNS.items():
        for r in range(3):
            ph = (r * 83.0) % 250.0
            s = synth.synth_capture(payload, eps=eps, phase_ns=ph)
            it = np.array([a for a, _, _ in s], float)
            sl = np.array([b for _, b, _ in s])
            obs = np.array([v for _, _, v in s], bool)
            u = it * G_CY + P_CY[sl]
            ktrue = 62.5 / (1 + eps)
            t0, k = lock(u, obs, use_hdr, use_trl, hm)
            ee.append((t0 + k * u[760]) - (ph + ktrue * u[760]))
            if abs(ee[-1]) > 250:
                tot["lf"] += 1
            hard, marg, ndis, imp = cells(u, obs, t0, k)
            truth = bits_of(payload)
            bad = hard != truth
            dec = ndis > 0
            tot["nb"] += 128
            tot["era"] += int((~dec).sum())
            tot["errd"] += int((bad & dec).sum())
            tot["err"] += int(bad.sum())
            tot["imp"] += imp
            tot["ex"] += int(not bad.any())
            tot["cap"] += 1
            c = 0
            for v in ~dec:
                c = c + 1 if v else 0
                if v:
                    runs[c] += 0
            # run lengths
            cur = 0
            for v in ~dec:
                if v:
                    cur += 1
                elif cur:
                    runs[cur] += 1
                    cur = 0
            if cur:
                runs[cur] += 1
    n = tot["nb"]
    print(f"{eps:+7.3f} era={100*tot['era']/n:6.2f}% "
          f"BERdec={100*tot['errd']/max(n-tot['era'],1):7.4f}% "
          f"BER={100*tot['err']/n:6.2f}% imp={tot['imp']/tot['cap']:5.2f} "
          f"exact={tot['ex']:3d}/{tot['cap']:<3d} lockfail={tot['lf']:3d} "
          f"|endErr|={np.mean(np.abs(ee)):7.1f} runs={dict(sorted(runs.items()))}")


MODES = {
    "joint":      (True, True, None),
    "hdr_only":   (True, False, None),
    "trl_only":   (False, True, None),
    "hdr_no00":   (True, True, np.array([1] * 8 + [0] * 8 + [1] * 16, bool)),
}

if __name__ == "__main__":
    modes = sys.argv[1:] or ["joint"]
    pts = [-0.075, -0.05, -0.025, -0.003, 0.0, 0.025, 0.05, 0.075]
    for mo in modes:
        print(f"=== mode {mo}")
        for e in pts:
            one_eps(e, MODES[mo])
