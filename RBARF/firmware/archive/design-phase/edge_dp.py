"""edge_dp -- Viterbi/BCJR alignment of the WS2812 bit grid to the oversampled stream.

Idea
----
The transmitter is crystal-exact: bit k occupies [k*1250, (k+1)*1250) ns and is
high for T0H=350 (bit 0) or T1H=700 (bit 1) at the start of that window, so the
signal is fully described by the 192 frame bits.  The *receiver* is the messy
part: an 8-samples-per-loop polling loop whose absolute sample instants are only
known as

    t(i, s) = t0 + P * (i + c[s] / 40)

with an unknown per-capture loop period P (HSI spread ~0.7%), an unknown trigger
offset t0, and slot cycle positions c[s] that are only nominally documented.  On
top of that the clock stretches slowly within one capture.

Rather than trusting a global time base, the bit sequence is aligned to the
sample stream by dynamic programming over a hidden state

    (j, b)   j = sample-time residual bin (DT ns), b = value of the WS2812 bit
             the current sample falls into

Stepping to the next sample the residual may drift by +-1 bin at a small cost
(clock stretching); the bit index follows from the absolute time; whenever a bit
boundary is crossed a fresh bit value is emitted, forced to the known header /
trailer bits where applicable.  The emission cost is a soft mismatch between the
observed level and the level the hypothesised bit predicts at that sample's
phase, so a sample that misses a threshold by a few ns is cheap while a gross
mismatch costs ~1.  Samples whose phase falls in the [T0H, T1H) window are the
ones that actually carry the bit; the DP naturally ignores bits that landed in an
inter-slot dead zone instead of failing on them.

A forward-backward pass then gives, for every payload bit, the best achievable
alignment cost with that bit forced to 0 and to 1; the difference is a per-bit
margin.  The margins are accumulated over a scan of the loop period P (whose
plausible window is pinned by the frame-end anchor: the last high sample of the
capture must straddle 191*1250 + 700 ns), weighted by the alignment likelihood.
The payload is read off the sign of the accumulated margins.

Pure stdlib, deterministic.
"""

import math

BIT = 1250.0
T0H = 350.0
T1H = 700.0
NBITS = 192
FRAME_END = 191 * BIT + T1H          # 239450 ns, last falling edge

# --- receiver model (calibrated on the train split) -----------------------
LOOP_CYCLES = 40.0
SLOT_CYCLES = (1.0, 5.0, 9.0, 13.0, 17.0, 21.0, 27.0, 32.0)

DT = 25.0                 # residual quantisation (ns)
JR = 26                   # residual bins each side
DRIFT_COST = 0.10         # cost of one bin of clock stretch
DRIFT_EVERY_SAMPLE = True  # False: only at loop boundaries (slot 0)
MISS_BASE = 0.30          # fixed part of a level mismatch
MISS_TOL = 90.0           # ns; near-threshold mismatches are cheap
WIN_LO_PAD = 1400.0       # ns of trigger-offset + drift slack, low side
WIN_HI_PAD = 800.0        # ... high side
P_COARSE = 1.0
P_FINE = 0.2
P_REFINE_N = 6
TEMP = 1.2                # soft-combination temperature over the P scan
MARGIN_CLIP = 4.0
EM_PASSES = 0             # timing-model refits on the decoded bits
EM_SHIFTS = (-0.6, -0.3, 0.0, 0.3, 0.6)   # period deltas to realign over
REFIT_ROUNDS = 30
REFIT_SLOTS = False       # let the EM refit move individual slot offsets
SLOT_SLACK = 45.0         # ns of slack allowed when it does
INF = float("inf")


def _frame_masks(meta):
    hdr = bytes.fromhex(meta.get("header", "FF00AA65"))
    trl = bytes.fromhex(meta.get("trailer", "9A5500FF"))
    forced = [-1] * NBITS
    for n, byte in enumerate(hdr):
        for k in range(8):
            forced[n * 8 + k] = (byte >> (7 - k)) & 1
    base = NBITS - 8 * len(trl)
    for n, byte in enumerate(trl):
        for k in range(8):
            forced[base + n * 8 + k] = (byte >> (7 - k)) & 1
    return forced, len(hdr) * 8


def _p_window(samples):
    last = None
    for n, (_, _, v) in enumerate(samples):
        if v:
            last = n
    if last is None or last + 1 >= len(samples):
        return 2492.0, 2528.0
    (i1, s1, _) = samples[last]
    (i2, s2, _) = samples[last + 1]
    f1 = i1 + SLOT_CYCLES[s1] / LOOP_CYCLES
    f2 = i2 + SLOT_CYCLES[s2] / LOOP_CYCLES
    lo = (FRAME_END - WIN_LO_PAD) / f2
    hi = (FRAME_END + WIN_HI_PAD) / f1
    return lo - 2.0, hi + 2.0


def _emit(phase, level, bitval):
    th = T1H if bitval else T0H
    pred = 1 if 0.0 <= phase < th else 0
    if pred == level:
        return 0.0
    if level == 1:
        d = phase - th if phase >= th else -phase
    else:
        d = th - phase
    if d <= 0.0:
        return MISS_BASE
    if d >= MISS_TOL:
        return 1.0
    return MISS_BASE + (1.0 - MISS_BASE) * (d / MISS_TOL)


def _align(nom, levels, forced, dmask=None):
    """Forward-backward alignment.

    Returns (best_cost, c0, c1) where c0[k]/c1[k] are the cheapest alignment
    costs with frame bit k forced to 0 / 1 (INF if impossible).
    """
    n_s = len(nom)
    nj = 2 * JR + 1
    if dmask is None:
        steps = [(-1, 0, 1)] * n_s
    else:
        steps = [(-1, 0, 1) if d else (0,) for d in dmask]
    kk = []
    em = []                     # em[n][j][b] emission cost
    for n in range(n_s):
        base = nom[n]
        lv = levels[n]
        krow = [0] * nj
        erow = [None] * nj
        for j in range(nj):
            t = base + (j - JR) * DT
            if t < 0.0:
                krow[j] = -1
                erow[j] = (0.0 if lv == 0 else 1.0, INF)
            else:
                k = int(t / BIT)
                if k >= NBITS:
                    krow[j] = NBITS
                    erow[j] = (0.0 if lv == 0 else 1.0, INF)
                else:
                    krow[j] = k
                    ph = t - k * BIT
                    fb = forced[k]
                    e0 = _emit(ph, lv, 0) if fb != 1 else INF
                    e1 = _emit(ph, lv, 1) if fb != 0 else INF
                    erow[j] = (e0, e1)
        kk.append(krow)
        em.append(erow)

    # ---- forward -------------------------------------------------------
    F = [None] * n_s
    cur = [[INF, INF] for _ in range(nj)]
    for j in range(nj):
        if kk[0][j] != 0:
            continue
        e0, e1 = em[0][j]
        cur[j][0] = e0
        cur[j][1] = e1
    F[0] = cur
    for n in range(1, n_s):
        prev = F[n - 1]
        krow = kk[n]
        pk = kk[n - 1]
        erow = em[n]
        cur = [[INF, INF] for _ in range(nj)]
        for j in range(nj):
            k2 = krow[j]
            if k2 < 0:
                continue
            e0, e1 = erow[j]
            if e0 is INF and e1 is INF:
                continue
            same = INF          # best prev cost with b unchanged, per b
            same0 = INF
            same1 = INF
            anyb = INF          # best prev cost over any b (bit boundary)
            for d in steps[n]:
                jp = j - d
                if jp < 0 or jp >= nj:
                    continue
                k1 = pk[jp]
                pen = DRIFT_COST if d else 0.0
                pv = prev[jp]
                if k1 < 0 or k1 >= NBITS:
                    # coming from outside the frame: only valid into bit 0
                    if k1 < 0 and k2 == 0:
                        v = pv[0] + pen
                        if v < anyb:
                            anyb = v
                    elif k1 >= NBITS and k2 >= NBITS:
                        v = pv[0] + pen
                        if v < same0:
                            same0 = v
                    continue
                dk = k2 - k1
                if dk == 0:
                    v = pv[0] + pen
                    if v < same0:
                        same0 = v
                    v = pv[1] + pen
                    if v < same1:
                        same1 = v
                elif dk == 1:
                    v = (pv[0] if pv[0] < pv[1] else pv[1]) + pen
                    if v < anyb:
                        anyb = v
            if k2 >= NBITS:
                b0 = same0 if same0 < anyb else anyb
                if b0 < INF:
                    cur[j][0] = b0 + e0
                continue
            b0 = same0 if same0 < anyb else anyb
            b1 = same1 if same1 < anyb else anyb
            if b0 < INF and e0 < INF:
                cur[j][0] = b0 + e0
            if b1 < INF and e1 < INF:
                cur[j][1] = b1 + e1
        F[n] = cur
        del same

    # ---- backward ------------------------------------------------------
    B = [None] * n_s
    cur = [[INF, INF] for _ in range(nj)]
    for j in range(nj):
        if kk[n_s - 1][j] >= NBITS - 1:
            cur[j][0] = 0.0
            cur[j][1] = 0.0
    if all(cur[j][0] is INF for j in range(nj)):
        for j in range(nj):
            cur[j][0] = 0.0
            cur[j][1] = 0.0
    B[n_s - 1] = cur
    for n in range(n_s - 2, -1, -1):
        nxt = B[n + 1]
        krow = kk[n]
        nk = kk[n + 1]
        erow = em[n + 1]
        cur = [[INF, INF] for _ in range(nj)]
        for jp in range(nj):
            k1 = krow[jp]
            if k1 < 0:
                # only bit-0 entry is meaningful
                best = INF
                for d in steps[n + 1]:
                    j = jp + d
                    if j < 0 or j >= nj:
                        continue
                    if nk[j] != 0:
                        continue
                    pen = DRIFT_COST if d else 0.0
                    e0, e1 = erow[j]
                    for b2 in (0, 1):
                        e = e0 if b2 == 0 else e1
                        if e is INF:
                            continue
                        v = nxt[j][b2] + e + pen
                        if v < best:
                            best = v
                cur[jp][0] = best
                cur[jp][1] = best
                continue
            r0 = INF
            r1 = INF
            for d in steps[n + 1]:
                j = jp + d
                if j < 0 or j >= nj:
                    continue
                k2 = nk[j]
                if k2 < 0:
                    continue
                pen = DRIFT_COST if d else 0.0
                e0, e1 = erow[j]
                if k2 >= NBITS:
                    if k1 >= NBITS:
                        v = nxt[j][0] + e0 + pen
                        if v < r0:
                            r0 = v
                        if v < r1:
                            r1 = v
                    elif k2 - k1 == 1:
                        v = nxt[j][0] + e0 + pen
                        if v < r0:
                            r0 = v
                        if v < r1:
                            r1 = v
                    continue
                if k1 >= NBITS:
                    continue
                dk = k2 - k1
                if dk == 0:
                    if e0 < INF:
                        v = nxt[j][0] + e0 + pen
                        if v < r0:
                            r0 = v
                    if e1 < INF:
                        v = nxt[j][1] + e1 + pen
                        if v < r1:
                            r1 = v
                elif dk == 1:
                    v = INF
                    if e0 < INF:
                        v = nxt[j][0] + e0 + pen
                    if e1 < INF:
                        v2 = nxt[j][1] + e1 + pen
                        if v2 < v:
                            v = v2
                    if v < r0:
                        r0 = v
                    if v < r1:
                        r1 = v
            cur[jp][0] = r0
            cur[jp][1] = r1
        B[n] = cur

    best = INF
    c0 = [INF] * NBITS
    c1 = [INF] * NBITS
    for n in range(n_s):
        Fn = F[n]
        Bn = B[n]
        krow = kk[n]
        for j in range(nj):
            k = krow[j]
            if k < 0 or k >= NBITS:
                continue
            f = Fn[j]
            b = Bn[j]
            v = f[0] + b[0]
            if v < c0[k]:
                c0[k] = v
            if v < best:
                best = v
            v = f[1] + b[1]
            if v < c1[k]:
                c1[k] = v
            if v < best:
                best = v
    return best, c0, c1


def _nominal(samples, P):
    per = P / LOOP_CYCLES
    lim = FRAME_END + 2600.0
    nom = []
    levels = []
    dmask = []
    for (i, s, v) in samples:
        t = P * i + per * SLOT_CYCLES[s]
        if t > lim:
            break
        nom.append(t)
        levels.append(v)
        dmask.append(True if DRIFT_EVERY_SAMPLE else s == 0)
    return nom, levels, dmask


def _combine(results, pl0):
    cmin = min(r[0] for r in results)
    acc = [0.0] * NBITS
    wsum = 0.0
    for cost, p, c0, c1 in results:
        w = math.exp(-(cost - cmin) / TEMP)
        if w < 1e-6:
            continue
        wsum += w
        for k in range(pl0, pl0 + 128):
            a = c0[k]
            b = c1[k]
            if a is INF and b is INF:
                continue
            if a is INF:
                acc[k] += w
                continue
            if b is INF:
                acc[k] -= w
                continue
            d = a - b
            if d > MARGIN_CLIP:
                d = MARGIN_CLIP
            elif d < -MARGIN_CLIP:
                d = -MARGIN_CLIP
            acc[k] += w * d
    return acc, wsum


# ---------------------------------------------------------------- EM refit

def _soft_cost(idx, slots, levels, bits, t0, P, D, delta):
    """soft level-mismatch cost of an explicit timing model, given `bits`."""
    tot = 0.0
    for n in range(len(idx)):
        i = idx[n]
        t = t0 + P * i + D * i * i + delta[slots[n]]
        lv = levels[n]
        if t < 0.0:
            if lv:
                tot += 1.0
            continue
        k = int(t / BIT)
        if k >= NBITS:
            if lv:
                tot += 1.0
            continue
        ph = t - k * BIT
        th = T1H if bits[k] else T0H
        if (ph < th) == (lv == 1):
            continue
        d = (ph - th) if lv else (th - ph)
        if d < 0.0:
            d = -d
        tot += 1.0 if d >= MISS_TOL else MISS_BASE + (1.0 - MISS_BASE) * d / MISS_TOL
    return tot


def _refit(idx, slots, levels, bits, P, delta0):
    t0 = 0.0
    D = 0.0
    delta = list(delta0)
    cur = _soft_cost(idx, slots, levels, bits, t0, P, D, delta)
    for _ in range(REFIT_ROUNDS):
        imp = False
        if REFIT_SLOTS:
            for st in (10.0, 3.0, 1.0):
                for s in range(8):
                    for d in (st, -st):
                        if abs(delta[s] + d - delta0[s]) > SLOT_SLACK:
                            continue
                        d2 = list(delta)
                        d2[s] += d
                        c = _soft_cost(idx, slots, levels, bits, t0, P, D, d2)
                        if c < cur - 1e-9:
                            cur, delta = c, d2
                            imp = True
        for st in (0.3, 0.1, 0.03):
            for d in (st, -st):
                c = _soft_cost(idx, slots, levels, bits, t0, P + d, D, delta)
                if c < cur - 1e-9:
                    cur, P = c, P + d
                    imp = True
        for st in (6.0, 2.0, 0.6):
            for d in (st, -st):
                c = _soft_cost(idx, slots, levels, bits, t0 + d, P, D, delta)
                if c < cur - 1e-9:
                    cur, t0 = c, t0 + d
                    imp = True
        for st in (0.02, 0.006, 0.002):
            for d in (st, -st):
                c = _soft_cost(idx, slots, levels, bits, t0, P, D + d, delta)
                if c < cur - 1e-9:
                    cur, D = c, D + d
                    imp = True
        if not imp:
            break
    return cur, t0, P, D, delta


def decode(samples, meta):
    if not samples or len(samples) < 400:
        return None
    forced, pl0 = _frame_masks(meta)
    plo, phi = _p_window(samples)

    results = []
    p = plo
    while p <= phi + 1e-9:
        nom, levels, dmask = _nominal(samples, p)
        if len(nom) >= 300:
            r = _align(nom, levels, forced, dmask)
            if r[0] < INF:
                results.append((r[0], p, r[1], r[2]))
        p += P_COARSE
    if not results:
        return None
    results.sort(key=lambda r: r[0])
    seeds = [r[1] for r in results[:P_REFINE_N]]
    seen = set(round(r[1], 4) for r in results)
    for p0 in seeds:
        k = -int(P_COARSE / P_FINE)
        while k <= int(P_COARSE / P_FINE):
            p = p0 + k * P_FINE
            k += 1
            key = round(p, 4)
            if key in seen or p < plo - P_COARSE or p > phi + P_COARSE:
                continue
            seen.add(key)
            nom, levels, dmask = _nominal(samples, p)
            if len(nom) < 300:
                continue
            r = _align(nom, levels, forced, dmask)
            if r[0] < INF:
                results.append((r[0], p, r[1], r[2]))
    if not results:
        return None

    acc, wsum = _combine(results, pl0)
    if wsum <= 0.0:
        return None

    # ---- EM: refit the receiver timing model on the current bit estimate,
    # ---- then realign on the sharpened time base.
    if EM_PASSES:
        results.sort(key=lambda r: r[0])
        Pbest = results[0][1]
        lim = FRAME_END + 2600.0
        idx = []
        slots = []
        levels = []
        dmask = []
        for (i, s, v) in samples:
            if Pbest * i > lim:
                break
            idx.append(i)
            slots.append(s)
            levels.append(v)
            dmask.append(True if DRIFT_EVERY_SAMPLE else s == 0)
        for _ in range(EM_PASSES):
            bits = list(forced)
            for k in range(pl0, pl0 + 128):
                if bits[k] < 0:
                    bits[k] = 1 if acc[k] > 0.0 else 0
            delta0 = [Pbest / LOOP_CYCLES * c for c in SLOT_CYCLES]
            cost, t0, Pf, D, delta = _refit(idx, slots, levels, bits,
                                            Pbest, delta0)
            res2 = []
            for dp in EM_SHIFTS:
                sc = (Pf + dp) / Pf
                nn = [t0 + (Pf + dp) * idx[n] + D * idx[n] * idx[n]
                      + delta[slots[n]] * sc for n in range(len(idx))]
                r = _align(nn, levels, forced, dmask)
                if r[0] < INF:
                    res2.append((r[0], Pf + dp, r[1], r[2]))
            if not res2:
                break
            a2, w2 = _combine(res2, pl0)
            if w2 <= 0.0:
                break
            acc = a2
            Pbest = Pf

    out = bytearray()
    for n in range(16):
        v = 0
        for k in range(8):
            v = (v << 1) | (1 if acc[pl0 + n * 8 + k] > 0.0 else 0)
        out.append(v)
    return bytes(out)
