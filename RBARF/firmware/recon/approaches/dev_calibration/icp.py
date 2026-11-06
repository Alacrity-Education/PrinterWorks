"""ICP-style joint calibration.

Alternates
  (a) assignment: for every sample decide how far its model time T must
      move to sit at least MARGIN ns inside the region its observed level
      requires, and
  (b) a linear least-squares step on ALL parameters at once
      p = [o1..o7, G, d, k_c (54), t0_c (54)]

with an outer 2-D line search on (eff_high_1, eff_high_0) and a final
integer polish on the raw agreement count.
"""
import json
import sys
import time

import numpy as np

import fitlib as F

DOC = np.array([1, 5, 9, 13, 17, 21, 27, 32], float)
NOFF = 7          # o[1..7]; o[0] pinned (degenerate with t0)
O0 = 62.5


class Fit:
    def __init__(self, caps, o, G, d, h1, h0, t0, k):
        self.caps = caps
        self.C = len(caps)
        self.o = np.asarray(o, float).copy()
        self.G = G
        self.d = d
        self.h1 = h1
        self.h0 = h0
        self.t0 = np.asarray(t0, float).copy()
        self.k = np.asarray(k, float).copy()
        # flat per-sample arrays over the active window
        self.it = np.concatenate([c["ait"] for c in caps])
        self.sl = np.concatenate([c["asl"] for c in caps])
        self.lv = np.concatenate([c["alv"] for c in caps])
        self.NN = np.concatenate([c["aN"] for c in caps])
        self.cidx = np.concatenate([np.full(c["an"], j) for j, c in enumerate(caps)])
        self.n = len(self.it)
        self.Bs = None
        self.rebuild_edges()

    def rebuild_edges(self):
        self.Bs = [F.edges_of(c["bits"], self.h1, self.h0) for c in self.caps]
        self.Bcat = np.concatenate(self.Bs)
        off = np.cumsum([0] + [len(b) for b in self.Bs])
        self.Boff = off

    def times(self):
        A = self.it * self.G + self.o[self.sl] - self.d * self.NN
        return self.t0[self.cidx] + self.k[self.cidx] * A, A

    def predict(self, T=None):
        if T is None:
            T, _ = self.times()
        pred = np.empty(self.n, dtype=np.int8)
        for j, c in enumerate(self.caps):
            m = self.cidx == j
            pred[m] = F.level_at(T[m], self.Bs[j])
        return pred

    def matches(self):
        return int(np.count_nonzero(self.predict() == self.lv))

    # ------------------------------------------------------------ assignment
    def residuals(self, margin=25.0, wmargin=0.15):
        T, A = self.times()
        r = np.zeros(self.n)
        w = np.zeros(self.n)
        for j in range(self.C):
            m = self.cidx == j
            B = self.Bs[j]
            t = T[m]
            idx = np.searchsorted(B, t, side="right")
            pred = (idx & 1).astype(np.int8)
            lo = np.where(idx > 0, B[np.clip(idx - 1, 0, len(B) - 1)], -1e12)
            hi = np.where(idx < len(B), B[np.clip(idx, 0, len(B) - 1)], 1e12)
            dlo = t - lo
            dhi = hi - t
            near_lo = dlo <= dhi
            dm = np.minimum(dlo, dhi)
            bad = pred != self.lv[m]
            # direction to move: toward nearest edge if wrong, away if right
            # +1 = move T later.  Nearest edge below -> "away" is later.
            sgn = np.where(near_lo, 1.0, -1.0)
            rj = np.where(bad, -sgn * (dm + margin),
                          np.where(dm < margin, sgn * (margin - dm), 0.0))
            wj = np.where(bad, 1.0, np.where(dm < margin, wmargin, 0.0))
            r[m] = rj
            w[m] = wj
        return r, w, T, A

    # ------------------------------------------------------------- LS step
    def ls_step(self, margin=25.0, wmargin=0.15, ridge=1e-3, damp=1.0):
        r, w, T, A = self.residuals(margin, wmargin)
        sel = w > 0
        rows = int(sel.sum())
        P = NOFF + 2 + 2 * self.C
        J = np.zeros((rows + 1 + P, P))
        y = np.zeros(rows + 1 + P)
        sl = self.sl[sel]
        ci = self.cidx[sel]
        kk = self.k[ci]
        ww = w[sel]
        rr = r[sel]
        idx = np.arange(rows)
        so = sl - 1
        ok = so >= 0
        J[idx[ok], so[ok]] = kk[ok]                       # o[1..7]
        J[idx, NOFF] = kk * self.it[sel]                  # G
        J[idx, NOFF + 1] = -kk * self.NN[sel]             # d
        J[idx, NOFF + 2 + ci] = A[sel]                    # k_c
        J[idx, NOFF + 2 + self.C + ci] = 1.0              # t0_c
        J[:rows] *= ww[:, None]
        y[:rows] = rr * ww
        # gauge: mean(k) == 1
        J[rows, NOFF + 2:NOFF + 2 + self.C] = 30.0 / self.C
        y[rows] = 30.0 * (1.0 - self.k.mean())
        # ridge
        scale = np.array([1.0] * NOFF + [0.02, 0.5]
                         + [4e4] * self.C + [1.0] * self.C)
        J[rows + 1:] = np.diag(ridge / scale)
        dp = np.linalg.lstsq(J, y, rcond=None)[0] * damp
        return dp

    def apply(self, dp):
        self.o[1:] += dp[:NOFF]
        self.G += dp[NOFF]
        self.d += dp[NOFF + 1]
        self.k += dp[NOFF + 2:NOFF + 2 + self.C]
        self.t0 += dp[NOFF + 2 + self.C:]

    def state(self):
        return (self.o.copy(), self.G, self.d, self.h1, self.h0,
                self.t0.copy(), self.k.copy())

    def restore(self, st):
        self.o, self.G, self.d, self.h1, self.h0, self.t0, self.k = (
            st[0].copy(), st[1], st[2], st[3], st[4], st[5].copy(), st[6].copy())
        self.rebuild_edges()


DAMPS = (1.0, 0.7, 0.45, 0.3, 0.2, 0.12, 0.07, 0.04, 0.02, 0.01)


def cost(fit, margin, wmargin=0.15):
    r, w, _, _ = fit.residuals(margin, wmargin)
    return float((w * r * r).sum())


def run_icp(fit, iters=40, margin0=40.0, log=print):
    best = fit.matches()
    bstate = fit.state()
    margin = margin0
    for t in range(iters):
        c0 = cost(fit, margin)
        st = fit.state()
        dp = fit.ls_step(margin=margin, damp=1.0)
        pick, pc = None, c0
        for damp in DAMPS:
            fit.restore(st)
            fit.apply(dp * damp)
            c = cost(fit, margin)
            if c < pc:
                pc, pick = c, damp
        fit.restore(st)
        if pick is not None:
            fit.apply(dp * pick)
        m = fit.matches()
        if m > best:
            best, bstate = m, fit.state()
        if t % 4 == 3:
            margin = max(6.0, margin * 0.7)
        log(f"   icp{t:02d} m={m} ({100*m/fit.n:.3f}%) cost={pc:.3e} "
            f"damp={pick} G={fit.G:.2f} d={fit.d:.2f} "
            f"o={np.round(fit.o,1).tolist()}")
        if pick is None:
            break
    fit.restore(bstate)
    return best
