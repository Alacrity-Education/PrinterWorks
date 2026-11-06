"""clock_stretch: oscillator-variation compensation by edge-anchored tracking.

Why a fixed time base fails
---------------------------
The transmitter sits on an exact 1250 ns grid; the STM8 sampling loop does
not.  Its HSI-derived period is unknown per capture (~1% spread measured
here: ~19.4 to ~20.3 sampling-loop cycles per WS2812 bit), the trigger
latency shifts the whole sample phase by up to several cycles, and the
period is not even constant inside a capture -- a level-dependent
instruction path makes the loop a cycle longer or shorter depending on
what the pin reads, so the effective rate wobbles with the local bit
density.  A brute-force scan over every constant (period, phase) pair
decodes only a handful of the 36 training captures; the rest need
tracking.

What this decoder does
----------------------
Work in the sampler's own *cycle space*

    c(iteration, slot) = iteration * 40 + slot_pos[slot]

and recover the monotone map from bit index to cycle space,

    C[k] = cycle position of the rising edge that starts bit k,

with a cell-local phase model inside each bit (piecewise-linear in time).

  1. Every WS2812 bit -- 0 or 1 -- begins with a rising edge, so observed
     low->high sample transitions are *payload-agnostic* phase references
     spread over the whole frame.  Each one brackets C[k] between the last
     low and the first high sample.
  2. Bit indices come from round(delta_c / rate): one bit is ~20 cycles,
     so missed edges (merged 1-pulses, swallowed T0H blips) quantise
     unambiguously to delta_k = 2, 3, ...
  3. C is then fitted as a smooth monotone curve that satisfies those
     brackets: squared-hinge feasibility plus a second-difference
     (rate-smoothness) penalty, minimised by projected gradient descent.
     Curvature is what absorbs drift and clock stretching, so phase error
     never accumulates across the frame.
  4. Falling edges are added as anchors too: for the known header
     (FF 00 AA 65) and trailer (9A 55 00 FF) straight away -- they
     re-measure the bit period at both ends of the frame -- and for the
     payload in decision-directed passes, since a fall at T0H vs T1H pins
     the phase inside a cell much harder than a rise does.
  5. Bits are read off with a soft (log-likelihood) sample model; the
     known 64 header/trailer bits score competing hypotheses.
"""

import math

BIT = 1250.0
NBITS = 192
PAY0 = 32

L_CYCLES = 40.0
SLOT_POS = [1.41, 4.78, 9.88, 12.69, 19.06, 21.97, 27.50, 31.44]

T0H = 350.0
T1H = 700.0
SIG = 70.0
SIG_RISE = 55.0

MIN_W = 14.0          # cycles per bit, lower clamp
MAX_W = 26.0

HEADER_BITS = [int(c) for b in bytes.fromhex("FF00AA65") for c in f"{b:08b}"]
TRAILER_BITS = [int(c) for b in bytes.fromhex("9A5500FF") for c in f"{b:08b}"]
KNOWN = {}
for _i, _b in enumerate(HEADER_BITS):
    KNOWN[_i] = _b
for _i, _b in enumerate(TRAILER_BITS):
    KNOWN[NBITS - 32 + _i] = _b


# ----------------------------------------------------------- sample model
def _p_high(ph, bit):
    th = T1H if bit else T0H
    a = 1.0 / (1.0 + math.exp(-ph / SIG_RISE))
    c = 1.0 / (1.0 + math.exp((ph - th) / SIG))
    v = a * c
    return 1e-4 if v < 1e-4 else (1 - 1e-4 if v > 1 - 1e-4 else v)


_ST = 2.0
_NL = int(BIT / _ST) + 3
_LLR = [0.0] * _NL          # LLR contribution of a sample reading high
_LLR0 = [0.0] * _NL         # ... reading low
_L1 = [(0.0, 0.0)] * _NL    # (log P(high|bit=1), log P(low|bit=1))
_L0 = [(0.0, 0.0)] * _NL
_LIDLE = math.log(1e-4)


def _rebuild():
    for j in range(_NL):
        p1 = _p_high(j * _ST, 1)
        p0 = _p_high(j * _ST, 0)
        _LLR[j] = math.log(p1) - math.log(p0)
        _LLR0[j] = math.log(1.0 - p1) - math.log(1.0 - p0)
        _L1[j] = (math.log(p1), math.log(1.0 - p1))
        _L0[j] = (math.log(p0), math.log(1.0 - p0))


_rebuild()


def _llr_phase(ph, level):
    j = int(ph / _ST)
    if j < 0:
        j = 0
    elif j >= _NL:
        j = _NL - 1
    return _LLR[j] if level else _LLR0[j]


# ------------------------------------------------------------ cycle space
def _cycles(samples):
    return [it * L_CYCLES + SLOT_POS[sl] for it, sl, _ in samples]


def _transitions(samples, cyc):
    """(kind, a, b): kind +1 rising, -1 falling; edge lies in (a, b)."""
    out = []
    prev = samples[0][2]
    for n in range(1, len(samples)):
        v = samples[n][2]
        if v != prev:
            out.append((1 if v else -1, cyc[n - 1], cyc[n]))
        prev = v
    return out


def _assign_rises(rises, rate):
    ks = [0]
    for j in range(1, len(rises)):
        d = (rises[j] - rises[j - 1]) / rate
        dk = int(math.floor(d + 0.5))
        if dk < 1:
            dk = 1
        ks.append(ks[-1] + dk)
    return ks


# --------------------------------------------------------------- the fit
def _initial_curve(kk, mids, rate):
    n = len(kk)
    sk = float(sum(kk))
    sm = sum(mids)
    skk = float(sum(k * k for k in kk))
    skm = sum(k * m for k, m in zip(kk, mids))
    den = n * skk - sk * sk
    beta = rate
    alpha = sm / n - beta * sk / n
    if den > 0:
        b2 = (n * skm - sk * sm) / den
        if MIN_W <= b2 <= MAX_W:
            beta = b2
            alpha = (sm - beta * sk) / n
    return [alpha + beta * k for k in range(NBITS + 1)]


def _fit(C, anchors, lam=0.6, mu=0.004, iters=260, step=0.05):
    """anchors: (k, frac, a, b, w).  position = C[k] + frac*(C[k+1]-C[k])."""
    N = NBITS + 1
    for _ in range(iters):
        g = [0.0] * N
        for (k, frac, a, b, w) in anchors:
            if frac == 0.0:
                p = C[k]
            else:
                p = C[k] + frac * (C[k + 1] - C[k])
            if p < a:
                d = p - a
            elif p > b:
                d = p - b
            else:
                d = 0.0
            mid = 0.5 * (a + b)
            gr = 2.0 * w * d + 2.0 * mu * (p - mid)
            if frac == 0.0:
                g[k] += gr
            else:
                g[k] += gr * (1.0 - frac)
                g[k + 1] += gr * frac
        # second-difference smoothness on C
        for k in range(1, N - 1):
            s = C[k + 1] - 2.0 * C[k] + C[k - 1]
            if s:
                t = 2.0 * lam * s
                g[k + 1] += t
                g[k - 1] += t
                g[k] -= 2.0 * t
        for k in range(N):
            C[k] -= step * g[k]
        # keep monotone with a plausible bit width
        for k in range(1, N):
            d = C[k] - C[k - 1]
            if d < MIN_W:
                C[k] = C[k - 1] + MIN_W
            elif d > MAX_W:
                C[k] = C[k - 1] + MAX_W
    return C


# ------------------------------------------------------------- decoding
def _llrs(samples, cyc, C):
    llr = [0.0] * NBITS
    n = len(samples)
    k = 0
    i = 0
    while i < n and cyc[i] < C[0]:
        i += 1
    while i < n and k < NBITS:
        c = cyc[i]
        if c >= C[k + 1]:
            k += 1
            continue
        span = C[k + 1] - C[k]
        ph = (c - C[k]) * BIT / span
        llr[k] += _llr_phase(ph, samples[i][2])
        i += 1
    return llr


def _cell_lls(samples, cyc, C, n_end):
    """(LL0, LL1) per bit cell: log-likelihood of the observed samples."""
    LL0 = [0.0] * NBITS
    LL1 = [0.0] * NBITS
    out = 0.0
    k = 0
    i = 0
    c0 = C[0]
    while i < n_end and cyc[i] < c0:
        if samples[i][2]:
            out += _LIDLE
        i += 1
    while i < n_end and k < NBITS:
        c = cyc[i]
        if c >= C[k + 1]:
            k += 1
            continue
        span = C[k + 1] - C[k]
        j = int((c - C[k]) * BIT / span / _ST)
        if j < 0:
            j = 0
        elif j >= _NL:
            j = _NL - 1
        if samples[i][2]:
            LL1[k] += _L1[j][0]
            LL0[k] += _L0[j][0]
        else:
            LL1[k] += _L1[j][1]
            LL0[k] += _L0[j][1]
        i += 1
    while i < n_end:
        if samples[i][2]:
            out += _LIDLE
        i += 1
    return LL0, LL1, out


def _prof_score(LL0, LL1, out):
    s = out
    for k in range(NBITS):
        b = KNOWN.get(k)
        if b is None:
            s += LL1[k] if LL1[k] > LL0[k] else LL0[k]
        else:
            s += LL1[k] if b else LL0[k]
    return s


KNOT_SETS = ((0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192),
             tuple(range(0, 193, 8)))
ANCHOR_PEN = 0.09
WIGGLE_PEN = 0.30


def _apply_delta(C, delta, knots):
    out = [0.0] * (NBITS + 1)
    nk = len(knots)
    seg = 0
    for k in range(NBITS + 1):
        while seg + 1 < nk - 1 and k >= knots[seg + 1]:
            seg += 1
        a = knots[seg]
        b = knots[seg + 1]
        f = (k - a) / float(b - a)
        out[k] = C[k] + delta[seg] * (1.0 - f) + delta[seg + 1] * f
    return out


def _anchor_cost(C, anchors):
    tot = 0.0
    for (k, frac, a, b, w) in anchors:
        p = C[k] if frac == 0.0 else C[k] + frac * (C[k + 1] - C[k])
        if p < a:
            d = a - p
        elif p > b:
            d = p - b
        else:
            continue
        tot += w * d * d
    return tot


def _refine_ml(samples, cyc, C, n_end, anchors, knot_sets=((0, 16, 32, 48, 64,
               80, 96, 112, 128, 144, 160, 176, 192),)):
    """Maximum-likelihood phase refinement, profiled over unknown bits.

    Rise brackets leave the absolute phase of a long uniform run
    under-determined (any offset inside the bracket fits), which is exactly
    how a run of 0-bits gets read as 1-bits.  The full sample likelihood
    does not have that ambiguity: a 0-cell and a 1-cell hold a different
    *number* of high samples.  So a smooth correction is line-searched here
    against the sample likelihood, kept honest by the rise-bracket hinge
    (payload-independent) and a wiggle penalty, and re-anchored on the
    known header/trailer bits.
    """
    for knots in knot_sets:
        nk = len(knots)
        delta = [0.0] * nk
        L0, L1, o = _cell_lls(samples, cyc, C, n_end)
        best = _prof_score(L0, L1, o) - ANCHOR_PEN * _anchor_cost(C, anchors)
        for step in (4.0, 2.0, 1.0, 0.5, 0.25):
            for _ in range(6):
                improved = False
                for i in range(nk):
                    for d in (step, -step):
                        cand = list(delta)
                        cand[i] += d
                        C2 = _apply_delta(C, cand, knots)
                        ok = True
                        for k in range(1, NBITS + 1):
                            if C2[k] - C2[k - 1] < MIN_W:
                                ok = False
                                break
                        if not ok:
                            continue
                        L0, L1, o = _cell_lls(samples, cyc, C2, n_end)
                        sc = _prof_score(L0, L1, o) \
                            - ANCHOR_PEN * _anchor_cost(C2, anchors)
                        for t in range(1, nk - 1):
                            s2 = cand[t + 1] - 2.0 * cand[t] + cand[t - 1]
                            sc -= WIGGLE_PEN * s2 * s2
                        if sc > best + 1e-9:
                            best = sc
                            delta = cand
                            improved = True
                if not improved:
                    break
        C = _apply_delta(C, delta, knots)
    L0, L1, o = _cell_lls(samples, cyc, C, n_end)
    return C, _prof_score(L0, L1, o)


DP_E = 16            # +-DP_E * DP_RES cycles of correction
DP_D = 6             # +-DP_D * DP_RES cycles of rate correction per bit
DP_RES = 0.2
POSTERIOR = False
DP_RATE_PEN = 0.4    # prior against rate excursions
DP_BRACKET_PEN = 2.5


def _dp_track(samples, cyc, C, n_end, brackets_by_k):
    """Viterbi phase tracking: the clock-recovery loop, done optimally.

    State = phase correction of C[k] (quantised); transition = correction
    of the local bit period.  Emission = the best (profiled) sample
    log-likelihood of the resulting bit cell, plus a hinge for the observed
    rising edge that must fall inside the cell boundary bracket.  Because
    the state carries the phase, error cannot accumulate: every bit cell is
    re-timed from the samples it actually contains.
    """
    ne = 2 * DP_E + 1
    nd = 2 * DP_D + 1
    NEG = -1e18
    score = [NEG] * ne
    score[DP_E] = 0.0
    back = []
    # index samples per cell window
    i0 = 0
    n = n_end
    marginL = DP_E * DP_RES + 1.0
    for k in range(NBITS):
        lo = C[k] - marginL
        hi = C[k + 1] + marginL
        while i0 < n and cyc[i0] < lo:
            i0 += 1
        j = i0
        win = []
        while j < n and cyc[j] < hi:
            win.append((cyc[j], samples[j][2]))
            j += 1
        W0 = C[k + 1] - C[k]
        br = brackets_by_k.get(k)
        kb = KNOWN.get(k)
        # emission[e][d]
        em = [[0.0] * nd for _ in range(ne)]
        for ei in range(ne):
            s = C[k] + (ei - DP_E) * DP_RES
            pen0 = 0.0
            if br is not None:
                if s < br[0]:
                    pen0 = -DP_BRACKET_PEN * (br[0] - s) ** 2
                elif s > br[1]:
                    pen0 = -DP_BRACKET_PEN * (s - br[1]) ** 2
            for di in range(nd):
                d = (di - DP_D) * DP_RES
                w = W0 + d
                if w < MIN_W:
                    em[ei][di] = NEG
                    continue
                f = BIT / w
                l0 = 0.0
                l1 = 0.0
                for (c, v) in win:
                    if c < s:
                        continue
                    ph = (c - s) * f
                    if ph >= BIT:
                        continue
                    q = int(ph / _ST)
                    if v:
                        l1 += _L1[q][0]
                        l0 += _L0[q][0]
                    else:
                        l1 += _L1[q][1]
                        l0 += _L0[q][1]
                if kb is None:
                    e = l1 if l1 > l0 else l0
                else:
                    e = l1 if kb else l0
                em[ei][di] = e + pen0 - DP_RATE_PEN * d * d
        nxt = [NEG] * ne
        bk = [0] * ne
        for ei in range(ne):
            sc = score[ei]
            if sc == NEG:
                continue
            row = em[ei]
            for di in range(nd):
                ej = ei + (di - DP_D)
                if ej < 0 or ej >= ne:
                    continue
                v = sc + row[di]
                if v > nxt[ej]:
                    nxt[ej] = v
                    bk[ej] = ei
        score = nxt
        back.append(bk)
    bestj = max(range(ne), key=lambda x: score[x])
    total = score[bestj]
    path = [0] * (NBITS + 1)
    path[NBITS] = bestj
    for k in range(NBITS - 1, -1, -1):
        bestj = back[k][bestj]
        path[k] = bestj
    return [C[k] + (path[k] - DP_E) * DP_RES for k in range(NBITS + 1)], total


def _lse(vals):
    m = max(vals)
    if m <= -1e17:
        return m
    s = 0.0
    for v in vals:
        d = v - m
        if d > -40.0:
            s += math.exp(d)
    return m + math.log(s)


def _dp_posterior(samples, cyc, C, n_end, brackets_by_k):
    """Forward-backward over the same phase lattice as _dp_track.

    Viterbi commits to one phase trajectory; the marginal posterior
    averages each bit decision over the phase uncertainty that is actually
    left, which is what rescues the cells whose only discriminating sample
    sits near a T0H/T1H edge.
    """
    ne = 2 * DP_E + 1
    nd = 2 * DP_D + 1
    NEG = -1e18
    ems = []
    i0 = 0
    n = n_end
    marginL = DP_E * DP_RES + 1.0
    for k in range(NBITS):
        lo = C[k] - marginL
        hi = C[k + 1] + marginL
        while i0 < n and cyc[i0] < lo:
            i0 += 1
        j = i0
        win = []
        while j < n and cyc[j] < hi:
            win.append((cyc[j], samples[j][2]))
            j += 1
        W0 = C[k + 1] - C[k]
        br = brackets_by_k.get(k)
        e0 = [[NEG] * nd for _ in range(ne)]
        e1 = [[NEG] * nd for _ in range(ne)]
        for ei in range(ne):
            s = C[k] + (ei - DP_E) * DP_RES
            pen0 = 0.0
            if br is not None:
                if s < br[0]:
                    pen0 = -DP_BRACKET_PEN * (br[0] - s) ** 2
                elif s > br[1]:
                    pen0 = -DP_BRACKET_PEN * (s - br[1]) ** 2
            r0 = e0[ei]
            r1 = e1[ei]
            for di in range(nd):
                d = (di - DP_D) * DP_RES
                w = W0 + d
                if w < MIN_W:
                    continue
                f = BIT / w
                l0 = 0.0
                l1 = 0.0
                for (c, v) in win:
                    if c < s:
                        continue
                    ph = (c - s) * f
                    if ph >= BIT:
                        continue
                    q = int(ph / _ST)
                    if v:
                        l1 += _L1[q][0]
                        l0 += _L0[q][0]
                    else:
                        l1 += _L1[q][1]
                        l0 += _L0[q][1]
                pen = pen0 - DP_RATE_PEN * d * d
                r0[di] = l0 + pen
                r1[di] = l1 + pen
        ems.append((e0, e1))

    def comb(ei, di, k):
        e0, e1 = ems[k]
        a = e0[ei][di]
        b = e1[ei][di]
        kb = KNOWN.get(k)
        if kb is None:
            if a <= NEG / 2:
                return a
            return _lse((a, b)) - 0.6931471805599453
        return b if kb else a

    alpha = [[NEG] * ne for _ in range(NBITS + 1)]
    for ei in range(ne):
        d = (ei - DP_E) * DP_RES
        alpha[0][ei] = -0.05 * d * d
    for k in range(NBITS):
        cur = alpha[k]
        nxt = alpha[k + 1]
        for ei in range(ne):
            a = cur[ei]
            if a <= NEG / 2:
                continue
            for di in range(nd):
                ej = ei + (di - DP_D)
                if ej < 0 or ej >= ne:
                    continue
                v = a + comb(ei, di, k)
                if v <= NEG / 2:
                    continue
                if nxt[ej] <= NEG / 2:
                    nxt[ej] = v
                else:
                    m = nxt[ej]
                    if v > m:
                        nxt[ej] = v + math.log1p(math.exp(m - v))
                    else:
                        nxt[ej] = m + math.log1p(math.exp(v - m))
    beta = [[NEG] * ne for _ in range(NBITS + 1)]
    for ei in range(ne):
        beta[NBITS][ei] = 0.0
    for k in range(NBITS - 1, -1, -1):
        cur = beta[k]
        nxt = beta[k + 1]
        for ei in range(ne):
            acc = NEG
            for di in range(nd):
                ej = ei + (di - DP_D)
                if ej < 0 or ej >= ne:
                    continue
                b = nxt[ej]
                if b <= NEG / 2:
                    continue
                v = b + comb(ei, di, k)
                if v <= NEG / 2:
                    continue
                if acc <= NEG / 2:
                    acc = v
                elif v > acc:
                    acc = v + math.log1p(math.exp(acc - v))
                else:
                    acc = acc + math.log1p(math.exp(v - acc))
            cur[ei] = acc

    llr = [0.0] * NBITS
    for k in range(NBITS):
        e0, e1 = ems[k]
        v0 = []
        v1 = []
        for ei in range(ne):
            a = alpha[k][ei]
            if a <= NEG / 2:
                continue
            for di in range(nd):
                ej = ei + (di - DP_D)
                if ej < 0 or ej >= ne:
                    continue
                b = beta[k + 1][ej]
                if b <= NEG / 2 or e0[ei][di] <= NEG / 2:
                    continue
                v0.append(a + b + e0[ei][di])
                v1.append(a + b + e1[ei][di])
        if v0:
            llr[k] = _lse(v1) - _lse(v0)
    total = _lse(alpha[NBITS])
    return llr, total


def _bits_from(llr):
    return [1 if llr[k] > 0 else 0 for k in range(NBITS)]


def _known_score(llr):
    s = 0.0
    for k, b in KNOWN.items():
        s += llr[k] if b else -llr[k]
    return s


def _fall_anchors(trans, C, bits, only_known):
    """attach each falling transition to the bit whose pulse it ends."""
    out = []
    k = 0
    for kind, a, b in trans:
        if kind != -1:
            continue
        mid = 0.5 * (a + b)
        while k + 1 <= NBITS and C[k + 1] < mid:
            k += 1
        if k >= NBITS:
            break
        kk = k
        # a fall at phase < ~200 more likely belongs to the previous cell
        span = C[kk + 1] - C[kk]
        ph = (mid - C[kk]) * BIT / span
        if ph < 120.0 and kk > 0:
            kk -= 1
            span = C[kk + 1] - C[kk]
            ph = (mid - C[kk]) * BIT / span
        if only_known and kk not in KNOWN:
            continue
        v = KNOWN[kk] if kk in KNOWN else bits[kk]
        th = T1H if v else T0H
        # only trust it if the model fall is anywhere near the bracket
        out.append((kk, th / BIT, a, b, 1.0))
    return out


def _solve(samples):
    cyc = _cycles(samples)
    trans = _transitions(samples, cyc)
    rises = [(a, b) for kind, a, b in trans if kind == 1]
    if len(rises) < 40:
        return None
    rmids = [0.5 * (a + b) for a, b in rises]

    n_end = len(samples)
    for n in range(len(samples) - 1, -1, -1):
        if samples[n][2]:
            n_end = min(len(samples), n + 12)
            break

    best = None
    seen = set()
    for rate in (19.2, 19.6, 20.0, 20.4):
        ks = _assign_rises(rmids, rate)
        key = tuple(ks)
        if key in seen:
            continue
        seen.add(key)
        # bit 0's rise precedes the first (edge-triggered) sample; the
        # trigger latency is a few cycles, so anchor it loosely.
        kk = [k + 1 for k in ks]
        anchors = [(0, 0.0, cyc[0] - 7.0, cyc[0], 0.3)]
        by_k = {}
        for j, k in enumerate(kk):
            if k > NBITS:
                break
            a, b = rises[j]
            anchors.append((k, 0.0, a, b, 1.0))
            if k not in by_k:
                by_k[k] = (a, b)
        C = _initial_curve([0] + kk, [cyc[0] - 2.0] + rmids, rate)
        C = _fit(C, anchors)

        for it in range(3):
            llr = _llrs(samples, cyc, C)
            bits = _bits_from(llr)
            fa = _fall_anchors(trans, C, bits, only_known=(it == 0))
            C2 = _fit(list(C), anchors + fa, iters=140)
            if _known_score(_llrs(samples, cyc, C2)) >= _known_score(llr):
                C = C2
            else:
                break

        C, sc = _refine_ml(samples, cyc, C, n_end, anchors, KNOT_SETS)
        C, sc = _dp_track(samples, cyc, C, n_end, by_k)
        if POSTERIOR:
            llr, sc = _dp_posterior(samples, cyc, C, n_end, by_k)
        else:
            llr = _llrs(samples, cyc, C)
        if best is None or sc > best[0]:
            best = (sc, llr, C, rate)
    return best


def decode(samples, meta):
    if not samples or len(samples) < 400:
        return None
    best = _solve(samples)
    if best is None:
        return None
    llr = best[1]
    out = bytearray()
    for i in range(16):
        v = 0
        for j in range(8):
            v = (v << 1) | (1 if llr[PAY0 + i * 8 + j] > 0 else 0)
        out.append(v)
    return bytes(out)
