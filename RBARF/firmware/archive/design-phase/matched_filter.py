"""Matched-filter WS2812 reconstruction with globally anchored phase tracking.

What the data actually looks like
--------------------------------
The transmitter waveform is fully determined by the 192 frame bits on an
exact 1250 ns grid (T0H 350 ns, T1H 700 ns).  The receiver samples it 8x per
sampling-loop iteration at *unevenly spaced* instants.  Two facts were
measured from the bench captures (see dev_matched_filter/):

1. The 8 intra-loop sample offsets are a stable constant of the firmware
   (``SLOT_O`` below, ~[128, 366, 664, 858, 1215, 1468, 1831, 2040] ns).
   Fitting them freely per capture gives the same values to +-40 ns; they are
   NOT the documented [1,5,9,13,17,21,27,32]/37 cycle positions.
2. The loop period is ~2 WS2812 bits, but it is *not* constant: with the
   slot offsets fixed, the per-iteration loop start time still needs a
   +-70..100 ns wobble to explain the samples (data-dependent instruction
   timing plus HSI wander).  A single global period + drift model therefore
   tops out around 92% of samples explained, which is nowhere near enough
   to decode 128 bits.

Algorithm
---------
Forward-model the sample instants as

    t(i, s) = P*i + psi_i + SLOT_O[s]

and score every bit cell by matched filter: within cell k the waveform is a
high of 350 ns (bit 0) or 700 ns (bit 1) followed by low, so the number of
samples whose observed level disagrees with the template is the correlation
cost.  ``psi_i`` (the per-iteration phase) and the 192 bits are then solved
*jointly* by a Viterbi pass over iterations:

  state after iteration i = (quantised psi_i, bits 2i+1 and 2i+2)
  transition cost         = matched-filter cost of iteration i's 8 samples
                            + a continuity penalty on psi_i - psi_{i-1}

Because one iteration spans ~2 bit cells, an iteration's samples only ever
touch bits 2i-1 .. 2i+2, so a 2-bit overlap state makes the recursion exact.
The 32-bit header and 32-bit trailer are *forced* to their known values (as
is the all-low latch tail after bit 191), which anchors the grid at both
ends of the frame and stops the phase track from sliding by a whole bit.
The loop period ``P`` is picked by re-running the Viterbi over a small grid
and keeping the cheapest solution.

Deterministic; numpy if available, otherwise a pure-python fallback.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import numpy as _np
except Exception:                                     # pragma: no cover
    _np = None

BIT = 1250.0
T0H = 320.0
T1H = 680.0
NBITS = 192
HDR = 32
NPAY = 128

# Intra-loop sample offsets (ns), measured; see module docstring.
SLOT_O = [128.5, 365.5, 663.5, 858.0, 1215.0, 1467.5, 1830.5, 2040.0]

# Loop-period search grid (ns per 8-sample iteration, ~2 bit periods).
P_LO, P_HI, P_STEP = 2488.0, 2524.0, 3.0

# Per-iteration phase grid (ns).
PSI_LO, PSI_HI, PSI_STEP = -520.0, 620.0, 10.0

# Continuity penalty on the per-iteration phase wobble: cost (in units of
# "one mismatched sample") per ns of |dpsi| beyond a free deadband.
JIT_DEAD = 0.0
JIT_LAM = 0.011

# Edge-softening scale (ns): a template disagreement within this distance of
# a modelled edge is discounted proportionally.  0 disables the softening.
EDGE_SOFT = 60.0

BIG = 1e9
TAIL_LOOPS = 3          # extra all-low iterations past the frame

# Soft (BCJR) decoding: marginalise the phase track instead of taking the
# single best one.  TEMP converts matched-filter cost into log-likelihood.
SOFT_OUTPUT = False
TEMP = 1.0

# Ensemble of model variants: (T0H, T1H, EDGE_SOFT, JIT_LAM, weight).
ENSEMBLE = True
MARGIN_CAP = 1.5
VARIANTS = [
    (320.0, 680.0, 60.0, 0.011, 1.0),
]

# Trigger prior: the capture is armed on the frame's first rising edge, so
# sample (0, 0) must land only a cycle or two into bit 0.  Penalising phase
# tracks that start somewhere else removes most whole-bit slips.
START_MID = 90.0
START_WIN = 220.0
START_LAM = 0.02

# Which way to resolve a bit cell whose samples carry no evidence at all
# (nothing in the [T0H, T1H) discrimination window).
TIE_BIT = 0

# EM refinement of the per-capture slot offsets: (search window, step) per
# round, and the maximum drift allowed away from the global constants.
EM_ROUNDS = 0
EM_SCHED = [(60.0, 5.0), (30.0, 2.5), (16.0, 2.0)]
EM_CLAMP = 90.0


def _bit_types(meta):
    """typ[k] for k in [-2, NBITS+8): 0/1 forced, 3 free, 2 always-low."""
    hdr = bytes.fromhex(meta.get("header", "FF00AA65"))
    trl = bytes.fromhex(meta.get("trailer", "9A5500FF"))
    hb = [int(b) for byte in hdr for b in f"{byte:08b}"]
    tb = [int(b) for byte in trl for b in f"{byte:08b}"]
    typ = [3] * NBITS
    for i, b in enumerate(hb):
        typ[i] = b
    for i, b in enumerate(tb):
        typ[HDR + NPAY + i] = b
    return typ


def _grid(samples):
    """levels[it][slot] plus the last iteration holding a high sample."""
    last = 0
    mx = samples[-1][0] + 1
    lv = [[0] * 8 for _ in range(mx)]
    for it, sl, v in samples:
        lv[it][sl] = v
        if v:
            last = it
    return lv, last


def decode(samples, meta):
    if not samples:
        return None
    lv, last_it = _grid(samples)
    if last_it < 80:
        return None
    typ = _bit_types(meta)
    nloops = min(len(lv), (NBITS + 1) // 2 + 1 + TAIL_LOOPS)

    levels = [lv[i] for i in range(nloops)]

    if _np is not None:
        return _decode_np(levels, typ, nloops)
    return _decode_py(levels, typ, nloops)


def _cost(u, W, V):
    """Soft matched-filter cost for one template.

    ``u`` is the sample's phase inside its bit cell, the template is high on
    [0, W) and low on [W, 1250).  A disagreement costs 1, except close to a
    template edge, where it is discounted linearly: a sample that reads low
    only 20 ns past the modelled falling edge is far more likely to be a
    small timing error than a wrong bit, and forcing it to cost a full unit
    is what makes long 1-runs decode as 0.
    """
    np = _np
    pred = (u < W)
    bad = pred != (V != 0)
    if EDGE_SOFT <= 0.0:
        return bad.astype(np.float64)
    disc = np.where(pred, np.minimum(u, W - u), np.minimum(u - W, BIT - u))
    return bad * np.minimum(1.0, disc * (1.0 / EDGE_SOFT))


# ---------------------------------------------------------------- numpy path
def _emissions(levels, typ, nloops, P, PSI, O):
    """E[i, p, mask] = matched-filter mismatch count for iteration i."""
    np = _np
    npsi = len(PSI)
    E = np.empty((nloops, npsi, 16), dtype=np.float32)
    # bit type for each (iteration, relative cell 0..3)
    tt = np.empty((nloops, 4), dtype=np.int64)
    for i in range(nloops):
        for r in range(4):
            k = 2 * i - 1 + r
            tt[i, r] = 2 if (k < 0 or k >= NBITS) else typ[k]
    Oa = np.asarray(O)
    for i in range(nloops):
        x = P * i + PSI[:, None] + Oa[None, :] - (2 * i - 1) * BIT
        r = np.floor(x * (1.0 / BIT)).astype(np.int64)
        u = x - r * BIT
        np.clip(r, 0, 3, out=r)
        V = np.asarray(levels[i], dtype=np.int8)[None, :]
        c0 = _cost(u, T0H, V)
        c1 = _cost(u, T1H, V)
        clo = (V != 0).astype(np.float64)
        F = tt[i][r]
        free = F == 3
        for m in range(16):
            mb = (m >> r) & 1
            sel = np.where(free, mb, F)
            cost = np.where(sel == 2, clo, np.where(sel == 1, c1, c0))
            E[i, :, m] = cost.sum(axis=1)
    return E, tt


def _start_prior(PSI, o0):
    np = _np
    t0 = PSI + o0
    return START_LAM * np.maximum(0.0, np.abs(t0 - START_MID) - START_WIN)


def _allowed(tt_row):
    """allowed u indices (rel cells 0,1) and w indices (rel cells 2,3)."""
    def sets(a, b):
        va = (0, 1) if a == 3 else ((0,) if a in (0, 2) else (1,))
        vb = (0, 1) if b == 3 else ((0,) if b in (0, 2) else (1,))
        return [x + 2 * y for y in vb for x in va]
    return sets(tt_row[0], tt_row[1]), sets(tt_row[2], tt_row[3])


def _viterbi(E, tt, nloops, PSI, jitlam, jitdead, prior=None):
    np = _np
    npsi = len(PSI)
    d = np.abs(PSI[:, None] - PSI[None, :])
    J = jitlam * np.maximum(0.0, d - jitdead)
    D = np.full((npsi, 4), BIG, dtype=np.float64)
    bp_p = np.zeros((nloops, npsi, 4), dtype=np.int16)
    bp_u = np.zeros((nloops, npsi, 4), dtype=np.int8)
    for i in range(nloops):
        us, ws = _allowed(tt[i])
        if i == 0:
            M = np.zeros((npsi, 4), dtype=np.float64)
            if prior is not None:
                M += prior[:, None]
            M[:, [u for u in range(4) if u not in us]] = BIG
            bp_p[0] = np.arange(npsi, dtype=np.int16)[:, None]
        else:
            tot = D[None, :, :] + J[:, :, None]         # [new, old, u]
            bp_p[i] = np.argmin(tot, axis=1).astype(np.int16)
            M = np.min(tot, axis=1)
        Dn = np.full((npsi, 4), BIG)
        for w in ws:
            X = M + E[i, :, 4 * w:4 * w + 4]
            # forbid disallowed u
            for u in range(4):
                if u not in us:
                    X[:, u] = BIG
            j = np.argmin(X, axis=1)
            Dn[:, w] = X[np.arange(npsi), j]
            bp_u[i, :, w] = j.astype(np.int8)
        D = Dn
    # backtrack
    j = int(np.argmin(D))
    p, w = divmod(j, 4)
    cost = float(D[p, w])
    seq = []
    for i in range(nloops - 1, -1, -1):
        u = int(bp_u[i, p, w])
        seq.append((i, u, w, p))
        pp = int(bp_p[i, p, u])
        w = u
        p = pp
    seq.reverse()
    bits = [0] * (NBITS + 8)
    psi = [0.0] * nloops
    for i, u, w, p in seq:
        b0 = u & 1
        b1 = (u >> 1) & 1
        k0 = 2 * i - 1
        if 0 <= k0 < len(bits):
            bits[k0] = b0
        if 0 <= k0 + 1 < len(bits):
            bits[k0 + 1] = b1
        psi[i] = float(PSI[p])
    return cost, bits, psi


def _lse(a, axis):
    np = _np
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isfinite(m), m, 0.0)
    return (m + np.log(np.exp(a - m).sum(axis=axis, keepdims=True))).squeeze(axis)


def _bcjr(E, tt, nloops, PSI, jitlam, jitdead, temp):
    """Forward-backward over the same trellis -> per-bit log-odds.

    Marginalising the phase (instead of committing to the single best track,
    as Viterbi does) is what rescues bit cells whose own samples happen to
    carry no evidence: their posterior then comes from how each hypothesis
    reshapes the phase track that the neighbouring cells have to live with.
    """
    np = _np
    npsi = len(PSI)
    NEG = -1e18
    J = (jitlam / temp) * np.maximum(0.0, np.abs(PSI[:, None] - PSI[None, :])
                                     - jitdead)
    Es = E / temp
    allow = [_allowed(tt[i]) for i in range(nloops)]

    F = [None] * nloops
    Ms = [None] * nloops
    for i in range(nloops):
        us, ws = allow[i]
        if i == 0:
            M = np.full((npsi, 4), NEG)
            for u in us:
                M[:, u] = 0.0
        else:
            X = F[i - 1][None, :, :] - J[:, :, None]
            M = _lse(X, 1)
            for u in range(4):
                if u not in us:
                    M[:, u] = NEG
        Ms[i] = M
        Fi = np.full((npsi, 4), NEG)
        for w in ws:
            Fi[:, w] = _lse(M - Es[i, :, 4 * w:4 * w + 4], 1)
        F[i] = Fi

    logZ = float(_lse(F[nloops - 1].ravel(), 0))
    G = np.zeros((npsi, 4))
    marg = {}
    for i in range(nloops - 1, -1, -1):
        us, ws = allow[i]
        for w in range(4):
            if w not in ws:
                G[:, w] = NEG
        stack = np.stack([-Es[i, :, 4 * w:4 * w + 4] + G[:, w][:, None]
                          for w in range(4)], axis=0)      # [w, p, u]
        H = _lse(stack, 0)                                 # [p, u]
        for u in range(4):
            if u not in us:
                H[:, u] = NEG
        q = _lse(Ms[i] + H, 0)                             # [u]
        for r in (0, 1):
            k = 2 * i - 1 + r
            if 0 <= k < NBITS and tt[i, r] == 3:
                one = [u for u in range(4) if (u >> r) & 1]
                zero = [u for u in range(4) if not (u >> r) & 1]
                marg[k] = (float(_lse(q[one], 0)), float(_lse(q[zero], 0)))
        if i:
            G = _lse(H[:, None, :] - J[:, :, None], 0)     # over p -> [p', u]
    return marg, logZ


def _margins(E, tt, nloops, PSI, jitlam, jitdead, prior=None):
    """Min-sum forward/backward -> per-bit (best cost with 1, with 0).

    Same trellis as the Viterbi, but run in both directions so that every
    free bit gets the cost of the best whole-frame explanation that contains
    it set to 1 and to 0.  The difference is a calibrated per-bit margin,
    which is what lets several model variants be combined sensibly.
    """
    np = _np
    npsi = len(PSI)
    J = jitlam * np.maximum(0.0, np.abs(PSI[:, None] - PSI[None, :]) - jitdead)
    allow = [_allowed(tt[i]) for i in range(nloops)]
    F = [None] * nloops
    Ms = [None] * nloops
    for i in range(nloops):
        us, ws = allow[i]
        if i == 0:
            M = np.full((npsi, 4), BIG)
            for u in us:
                M[:, u] = 0.0 if prior is None else prior
        else:
            M = np.min(F[i - 1][None, :, :] + J[:, :, None], axis=1)
            for u in range(4):
                if u not in us:
                    M[:, u] = BIG
        Ms[i] = M
        Fi = np.full((npsi, 4), BIG)
        for w in ws:
            Fi[:, w] = np.min(M + E[i, :, 4 * w:4 * w + 4], axis=1)
        F[i] = Fi
    G = np.zeros((npsi, 4))
    out = {}
    for i in range(nloops - 1, -1, -1):
        us, ws = allow[i]
        for w in range(4):
            if w not in ws:
                G[:, w] = BIG
        H = np.min(np.stack([E[i, :, 4 * w:4 * w + 4] + G[:, w][:, None]
                             for w in range(4)], axis=0), axis=0)
        for u in range(4):
            if u not in us:
                H[:, u] = BIG
        q = np.min(Ms[i] + H, axis=0)                  # [u]
        for r in (0, 1):
            k = 2 * i - 1 + r
            if 0 <= k < NBITS and tt[i, r] == 3:
                c1 = min(q[u] for u in range(4) if (u >> r) & 1)
                c0 = min(q[u] for u in range(4) if not (u >> r) & 1)
                out[k] = (float(c1), float(c0))
        if i:
            G = np.min(H[:, None, :] + J[:, :, None], axis=0)
    return out


def _refit_o(levels, bits, psi, P, O, nloops, win, step):
    """Re-fit the 8 intra-loop offsets given bits + phase track (decoupled)."""
    np = _np
    thr = np.array([(T1H if (0 <= k < NBITS and bits[k]) else
                     (T0H if 0 <= k < NBITS else -1.0))
                    for k in range(-2, NBITS + 12)], dtype=np.float64)
    off = 2                          # index shift for negative cells
    ps = np.asarray(psi[:nloops]) + P * np.arange(nloops)
    V = np.asarray([levels[i] for i in range(nloops)], dtype=np.int8)
    cand = np.arange(-win, win + 1e-9, step)
    out = list(O)
    for s in range(8):
        t = ps[None, :] + O[s] + cand[:, None]          # [nc, nloops]
        k = np.floor(t * (1.0 / BIT)).astype(np.int64)
        k = np.clip(k, -2, NBITS + 11)
        u = t - k * BIT
        pred = (u < thr[k + off]).astype(np.int8)
        g = (pred == V[:, s][None, :]).sum(axis=1)
        out[s] = O[s] + float(cand[int(np.argmax(g))])
    return out


def _pack(bits):
    out = bytearray()
    for i in range(16):
        v = 0
        for b in bits[HDR + i * 8: HDR + i * 8 + 8]:
            v = (v << 1) | b
        out.append(v)
    return bytes(out)


def _decode_soft(levels, typ, nloops):
    """Soft decoding: marginalise the phase track AND the loop period."""
    np = _np
    PSI = np.arange(PSI_LO, PSI_HI + 1e-9, PSI_STEP)
    O = list(SLOT_O)
    acc = {}
    P = P_LO
    while P <= P_HI + 1e-9:
        E, tt = _emissions(levels, typ, nloops, P, PSI, O)
        marg, _ = _bcjr(E, tt, nloops, PSI, JIT_LAM, JIT_DEAD, TEMP)
        for k, (l1, l0) in marg.items():
            a = acc.setdefault(k, [[], []])
            a[0].append(l1)
            a[1].append(l0)
        P += P_STEP
    if not acc:
        return None
    bits = [0] * (NBITS + 8)
    for k, t in enumerate(typ):
        if t in (0, 1):
            bits[k] = t
    for k, (l1s, l0s) in acc.items():
        m = max(max(l1s), max(l0s))
        s1 = sum(_expf(x - m) for x in l1s)
        s0 = sum(_expf(x - m) for x in l0s)
        bits[k] = 1 if s1 > s0 else 0
    return _pack(bits)


def _expf(x):
    import math
    return math.exp(x) if x > -700.0 else 0.0


def _decode_ens(levels, typ, nloops):
    """Ensemble of model variants combined through per-bit min-sum margins.

    Each variant is the same matched filter under slightly different physical
    assumptions (pulse widths, edge softness, phase stiffness).  Where they
    agree the bit is certain; where they disagree the summed margins pick the
    hypothesis that is cheapest across the whole family, which is far more
    stable than trusting one point estimate of a model we only know to +-tens
    of nanoseconds.
    """
    np = _np
    PSI = np.arange(PSI_LO, PSI_HI + 1e-9, PSI_STEP)
    global T0H, T1H, EDGE_SOFT
    t0_, t1_, es_ = T0H, T1H, EDGE_SOFT
    pri = _start_prior(PSI, SLOT_O[0])
    acc = {}
    try:
        for var in VARIANTS:
            t0, t1, es, lam, wt = var[:5]
            dO = var[5] if len(var) > 5 else None
            O = SLOT_O if dO is None else [a + b for a, b in zip(SLOT_O, dO)]
            T0H, T1H, EDGE_SOFT = t0, t1, es
            best = None
            allm = None
            P = P_LO
            while P <= P_HI + 1e-9:
                E, tt = _emissions(levels, typ, nloops, P, PSI, O)
                c = _viterbi(E, tt, nloops, PSI, lam, JIT_DEAD, pri)[0]
                if best is None or c < best:
                    best = c
                    allm = _margins(E, tt, nloops, PSI, lam, JIT_DEAD, pri)
                P += P_STEP
            if allm is None:
                continue
            for k, (c1, c0) in allm.items():
                d = c1 - c0
                lim = MARGIN_CAP
                if d > lim:
                    d = lim
                elif d < -lim:
                    d = -lim
                acc[k] = acc.get(k, 0.0) + wt * d
    finally:
        T0H, T1H, EDGE_SOFT = t0_, t1_, es_
    if not acc:
        return None
    bits = [0] * (NBITS + 8)
    for k, t in enumerate(typ):
        if t in (0, 1):
            bits[k] = t
    for k, d in acc.items():
        bits[k] = 1 if (d < 0.0 or (d == 0.0 and TIE_BIT)) else 0
    return _pack(bits)


def _decode_np(levels, typ, nloops):
    if ENSEMBLE:
        return _decode_ens(levels, typ, nloops)
    if SOFT_OUTPUT:
        return _decode_soft(levels, typ, nloops)
    np = _np
    PSI = np.arange(PSI_LO, PSI_HI + 1e-9, PSI_STEP)
    O = list(SLOT_O)
    best = None
    P = P_LO
    while P <= P_HI + 1e-9:
        E, tt = _emissions(levels, typ, nloops, P, PSI, O)
        r = _viterbi(E, tt, nloops, PSI, JIT_LAM, JIT_DEAD,
                     _start_prior(PSI, O[0]))
        if best is None or r[0] < best[0]:
            best = (r[0], r[1], r[2], P)
        P += P_STEP
    if best is None:
        return None
    P0 = best[3]
    for dP in (-P_STEP / 2.0, P_STEP / 2.0):
        E, tt = _emissions(levels, typ, nloops, P0 + dP, PSI, O)
        r = _viterbi(E, tt, nloops, PSI, JIT_LAM, JIT_DEAD)
        if r[0] < best[0]:
            best = (r[0], r[1], r[2], P0 + dP)

    if not EM_ROUNDS:
        return _pack(best[1])

    cost, bits, psi, P = best
    O_cur = list(O)
    for rnd in range(EM_ROUNDS):
        win, step = EM_SCHED[min(rnd, len(EM_SCHED) - 1)]
        newO = _refit_o(levels, bits, psi, P, O_cur, nloops, win, step)
        newO = [min(max(n, o - EM_CLAMP), o + EM_CLAMP)
                for n, o in zip(newO, SLOT_O)]
        if all(abs(a - b) < 1e-9 for a, b in zip(newO, O_cur)):
            break
        O_cur = newO
        bb = None
        for dP in (-P_STEP / 2.0, 0.0, P_STEP / 2.0):
            E, tt = _emissions(levels, typ, nloops, P + dP, PSI, O_cur)
            r = _viterbi(E, tt, nloops, PSI, JIT_LAM, JIT_DEAD)
            if bb is None or r[0] < bb[0]:
                bb = (r[0], r[1], r[2], P + dP)
        cost, bits, psi, P = bb
    return _pack(bits)


# ------------------------------------------------------------ python fallback
def _decode_py(levels, typ, nloops):        # pragma: no cover
    return None
