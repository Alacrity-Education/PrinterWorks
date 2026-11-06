"""Prototype of the edge_dp Viterbi aligner.

Trellis: bit index k = 0..191.
State  : phase residual delta (nominal-receiver ns) of the bit-k boundary
         relative to the linear prediction phi + k*Delta.
Per Delta (nominal receiver ns per WS2812 bit) hypothesis we run one DP;
the winner over Delta is taken.

Emission: soft level model.  For each sample falling inside the bit
window, predicted P(high) = sigmoid((f_b - f)/w) with f the fractional
position in the bit and f_b = 0.6 (bit 1) or 0.3 (bit 0).

Known header/trailer bits are forced; payload bits are free (and can
carry an external log-prior -> the fusion hook).
"""
import numpy as np
import model as M

HEADER_BITS = np.array([(b >> (7 - j)) & 1 for b in bytes.fromhex("FF00AA65") for j in range(8)])
TRAILER_BITS = np.array([(b >> (7 - j)) & 1 for b in bytes.fromhex("9A5500FF") for j in range(8)])
NBITS = 192
F1, F0 = 0.6, 0.3


def build_tau(idx, o):
    return np.array([i * 2500.0 + o[s] for i, s in idx])


class DP:
    def __init__(self, tau, obs, o=None, w=0.055, floor=0.02,
                 dgrid=6.0, dmax=420.0, wander=3, lam=0.9, maxin=7):
        self.T = np.asarray(tau, dtype=np.float64)
        self.V = np.asarray(obs, dtype=np.float64)
        self.w = w
        self.floor = floor
        self.d = np.arange(-dmax, dmax + 1e-9, dgrid)     # phase residual grid
        self.nd = len(self.d)
        self.dgrid = dgrid
        self.wander = wander
        self.lam = lam
        self.maxin = maxin

    def emission(self, beta, Delta):
        """beta: (B,) array of bit-start times. -> cost (2, B) for b=0,1."""
        lo = np.searchsorted(self.T, beta, side="left")
        hi = np.searchsorted(self.T, beta + Delta, side="left")
        cost = np.zeros((2, len(beta)))
        for j in range(self.maxin):
            idx = lo + j
            valid = idx < hi
            if not valid.any():
                break
            ii = np.clip(idx, 0, len(self.T) - 1)
            f = (self.T[ii] - beta) / Delta
            v = self.V[ii]
            for bi, fb in ((0, F0), (1, F1)):
                q = 1.0 / (1.0 + np.exp(-(fb - f) / self.w))
                q = self.floor + (1.0 - 2.0 * self.floor) * q
                c = -(v * np.log(q) + (1.0 - v) * np.log(1.0 - q))
                cost[bi] += np.where(valid, c, 0.0)
        return cost

    def run(self, phi, Delta, prior=None):
        """prior: (192,2) additive log-cost per bit value, or None.
        returns (total_cost, bits, delta_track)."""
        nd = self.nd
        BIG = 1e12
        cost = np.full(nd, BIG)
        cost[:] = 0.5 * (self.d / 60.0) ** 2          # weak prior on initial phase
        bt_state = np.zeros((NBITS, nd), dtype=np.int32)
        bt_bit = np.zeros((NBITS, nd), dtype=np.int8)
        shifts = np.arange(-self.wander, self.wander + 1)
        step_pen = self.lam * (shifts * self.dgrid / 25.0) ** 2

        for k in range(NBITS):
            beta = phi + k * Delta + self.d
            em = self.emission(beta, Delta)
            if k < 32:
                b = HEADER_BITS[k]
                ec, eb = em[b], np.full(nd, b, dtype=np.int8)
            elif k >= 160:
                b = TRAILER_BITS[k - 160]
                ec, eb = em[b], np.full(nd, b, dtype=np.int8)
            else:
                e = em.copy()
                if prior is not None:
                    e[0] += prior[k, 0]
                    e[1] += prior[k, 1]
                eb = (e[1] < e[0]).astype(np.int8)
                ec = np.minimum(e[0], e[1])
            # transition: new delta index = old + shift
            best = np.full(nd, BIG)
            arg = np.zeros(nd, dtype=np.int32)
            for si, sh in enumerate(shifts):
                src = np.roll(cost, sh)
                if sh > 0:
                    src[:sh] = BIG
                elif sh < 0:
                    src[sh:] = BIG
                cand = src + step_pen[si]
                m = cand < best
                best[m] = cand[m]
                arg[m] = np.arange(nd)[m] - sh
            cost = best + ec
            bt_state[k] = np.clip(arg, 0, nd - 1)
            bt_bit[k] = eb

        j = int(np.argmin(cost))
        total = float(cost[j])
        bits = np.zeros(NBITS, dtype=np.int8)
        track = np.zeros(NBITS)
        for k in range(NBITS - 1, -1, -1):
            bits[k] = bt_bit[k, j]
            track[k] = self.d[j]
            j = int(bt_state[k, j])
        return total, bits, track


def bits_to_payload(bits):
    out = bytearray()
    for byi in range(4, 20):
        v = 0
        for j in range(8):
            v = (v << 1) | int(bits[byi * 8 + j])
        out.append(v)
    return bytes(out)


def decode(tau, obs, phis, deltas, prior=None, **kw):
    dp = DP(tau, obs, **kw)
    best = (1e18, None, None, None)
    for D in deltas:
        for phi in phis:
            c, b, tr = dp.run(phi, D, prior)
            if c < best[0]:
                best = (c, b, D, phi)
    return best
