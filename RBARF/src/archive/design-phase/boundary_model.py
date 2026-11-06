"""boundary_model - WS2812 reconstruction on a calibrated non-uniform
sampling grid with per-loop clock tracking.

What the sampler really does
----------------------------
The STM8 polling loop takes 8 samples per iteration at *non-uniform*
intra-loop offsets.  The firmware comment claims cycle positions
[1,5,9,13,17,21,27,32] out of a 37-cycle loop, but the loop really runs
~40 cycles, so ~3 cycles are unaccounted for.  Fitting the intra-loop
geometry against the known frame waveform (offline, see
approaches/dev_boundary_model/) shows the missing time sits in the
end-of-loop bookkeeping *and* in the gap around slot 3: the calibrated
fractional offsets are

    F = [0, .100, .200, .280, .400, .510, .650, .775]     (of one loop)

i.e. inter-sample gaps of about [4.0, 4.0, 3.2, 4.8, 4.4, 5.6, 5.0, 9.0]
cycles.  The ~9-cycle end-of-loop gap (~560 ns) is what swallows 0-bit
pulses and merges adjacent 1-bit pulses.

With F fixed, the residual error of a *linear* time base
t(it,slot) = B + L*(it + F[slot]) is still ~12% of samples, but giving
every loop its own start time S_it drops it to ~0.5%: the HSI clock
wanders by a few hundred ns across a frame ("clock stretching").  So the
decoder tracks S_it explicitly:

  1. seed (L, B) from the known header/trailer on the exact 1250 ns grid;
  2. Viterbi over per-loop start offsets e_it (total-variation prior),
     scoring each candidate against what the waveform *must* look like
     regardless of the unknown payload bits - every bit cell has a rising
     edge at an exact multiple of 1250 ns, is high for the first 350 ns
     and low for the last 550 ns, whatever its value;
  3. refit the linear trend, repeat;
  4. timestamp every sample from the tracked S_it, pool the samples of
     each 1250 ns cell and pick the bit whose waveform explains them.
"""

# --- calibrated hardware constants ------------------------------------
F = (0.0, 0.100, 0.200, 0.280, 0.400, 0.510, 0.650, 0.775)

BIT = 1250.0
T0H = 350.0
T1H = 700.0
NBITS = 192
FRAME_END = NBITS * BIT
PAY_LO, PAY_HI = 32, 160          # payload bit-cell range

B_LO, B_HI = -200.0, 450.0
L_LO, L_HI = 2465.0, 2555.0

E_HALF = 620.0                    # per-loop offset search half-range (ns)
E_STEP = 5.0
LAMBDA = 1.0 / 55.0               # L1 prior: cost per ns of clock step
ALPHA = 0.0                       # extra quadratic prior (cost per ns^2)
PAIR_W = 4                        # weight of the within-cell consistency term
MAX_LOOP = 101


# ---------------------------------------------------------------- helpers
def _bits(bs):
    return [(b >> (7 - k)) & 1 for b in bs for k in range(8)]


def _thresholds(header, trailer):
    """th[j] = high duration of cell j, or None when the bit is unknown."""
    th = [None] * NBITS
    for i, v in enumerate(_bits(header)):
        th[i] = T1H if v else T0H
    for j, v in enumerate(_bits(trailer)):
        th[160 + j] = T1H if v else T0H
    return th


# ------------------------------------------------- seed (L, B) from ends
def _match_intervals(t0, v, th, blo, bhi):
    """B-intervals inside [blo,bhi] where a sample at offset t0 with level
    v agrees with the *known* part of the waveform.  None when the sample
    could land on an unknown payload cell."""
    lo_t, hi_t = t0 + blo, t0 + bhi
    j0 = int(lo_t // BIT)
    j1 = int(hi_t // BIT)
    if lo_t < 0.0:
        return None
    for j in range(j0, j1 + 1):
        if j < NBITS and th[j] is None:
            return None
    out = []
    for j in range(j0, j1 + 1):
        a = j * BIT
        if j >= NBITS:
            hi0 = hi1 = a           # nothing high after the frame
        else:
            hi0, hi1 = a, a + th[j]
        seg_a, seg_b = max(a, lo_t), min(a + BIT, hi_t)
        if seg_b <= seg_a:
            continue
        if v:
            lo2, hi2 = max(hi0, seg_a), min(hi1, seg_b)
            if hi2 > lo2:
                out.append((lo2 - t0, hi2 - t0))
        else:
            for lo2, hi2 in ((seg_a, min(hi0, seg_b)), (max(hi1, seg_a), seg_b)):
                if hi2 > lo2:
                    out.append((lo2 - t0, hi2 - t0))
    return out


def _best_B(xs, vs, L, th, blo, bhi):
    events = []
    for x, v in zip(xs, vs):
        iv = _match_intervals(L * x, v, th, blo, bhi)
        if iv is None:
            continue
        for a, b in iv:
            events.append((a, 1))
            events.append((b, -1))
    if not events:
        return -1, 0.0
    events.sort()
    cur = best = -1
    blo_ = bhi_ = 0.0
    i, m = 0, len(events)
    cur = 0
    while i < m:
        p = events[i][0]
        while i < m and events[i][0] == p:
            cur += events[i][1]
            i += 1
        nxt = events[i][0] if i < m else p
        if cur > best and nxt > p:
            best, blo_, bhi_ = cur, p, nxt
    return best, 0.5 * (blo_ + bhi_)


def _seed_candidates(samples, th, n_keep=4):
    xs, vs = [], []
    for it, sl, v in samples:
        if it > MAX_LOOP + 8:
            break
        xs.append(it + F[sl])
        vs.append(v)
    scored = []
    L = L_LO
    while L <= L_HI + 1e-9:
        sc, B = _best_B(xs, vs, L, th, B_LO, B_HI)
        scored.append((sc, L, B))
        L += 0.25
    scored.sort(key=lambda r: -r[0])
    picked = []
    for sc, L, B in scored:
        if all(abs(L - p[1]) > 4.0 for p in picked):
            # local refinement
            best = (sc, L, B)
            step = 0.02
            Lx = L - 0.25
            while Lx <= L + 0.25 + 1e-9:
                s2, B2 = _best_B(xs, vs, Lx, th, B_LO, B_HI)
                if s2 > best[0]:
                    best = (s2, Lx, B2)
                Lx += step
            picked.append(best)
            if len(picked) >= n_keep:
                break
    return picked


# ------------------------------------------------ per-loop Viterbi track
def _cost_runs(tA, tB, v, th, out):
    """append (lo,hi) sub-intervals of [tA,tB) where a sample of level v
    is *impossible*, whatever the unknown payload bits are."""
    j = int(tA // BIT)
    if j < 0:
        if v:
            out.append((tA, min(tB, 0.0)))
        j = 0
    while j * BIT < tB:
        a = j * BIT
        if j >= NBITS:
            if v:
                out.append((max(tA, a), tB))
            return
        t = th[j]
        if t is None:
            if v:
                lo, hi = a + T1H, a + BIT
            else:
                lo, hi = a, a + T0H
            if hi > tA and lo < tB:
                out.append((max(lo, tA), min(hi, tB)))
        else:
            if v:
                lo, hi = a + t, a + BIT
                if hi > tA and lo < tB:
                    out.append((max(lo, tA), min(hi, tB)))
            else:
                lo, hi = a, a + t
                if hi > tA and lo < tB:
                    out.append((max(lo, tA), min(hi, tB)))
        j += 1


def _pair_runs(tA, tB, gap, th, out):
    """Two samples of *different* level, `gap` ns apart, cannot both sit in
    the same unknown cell's discriminating window [350,700): whichever bit
    the cell carries, both would read the same.  Append the impossible
    sub-intervals for the earlier sample's time."""
    if gap >= T1H - T0H:
        return
    j = int(tA // BIT)
    if j < 0:
        j = 0
    while j * BIT < tB:
        if j >= NBITS:
            return
        if th[j] is None:
            lo = j * BIT + T0H
            hi = j * BIT + T1H - gap
            if hi > tA and lo < tB:
                out.append((max(lo, tA), min(hi, tB)))
        j += 1


def _quad_dt(f, alpha, n):
    """Lower envelope of parabolas: D[q] = min_p f[p] + alpha*(q-p)^2,
    with the arg-min (Felzenszwalb & Huttenlocher)."""
    v = [0] * n
    z = [0.0] * (n + 1)
    k = 0
    z[0] = -1e30
    z[1] = 1e30
    for q in range(1, n):
        fq = f[q] + alpha * q * q
        while True:
            p = v[k]
            s = (fq - (f[p] + alpha * p * p)) / (2.0 * alpha * (q - p))
            if s <= z[k]:
                k -= 1
                if k < 0:
                    k = 0
                    v[0] = q
                    z[0] = -1e30
                    z[1] = 1e30
                    s = None
                    break
            else:
                break
        if s is None:
            continue
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = 1e30
    out = [0.0] * n
    ptr = [0] * n
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        p = v[k]
        d = q - p
        out[q] = alpha * d * d + f[p]
        ptr[q] = p
    return out, ptr


def _track(samples, L, B, th, e_half=E_HALF, e_step=E_STEP, rounds=3):
    """returns (S_list, total_cost) with one start time per loop."""
    by_loop = {}
    for it, sl, v in samples:
        if it > MAX_LOOP:
            break
        by_loop.setdefault(it, []).append((sl, v))
    loops = sorted(by_loop)
    ne = int(2 * e_half / e_step) + 1
    e0 = -e_half
    lam = LAMBDA * e_step
    Sfin = None
    total = 0.0
    for _rnd in range(rounds):
        offs = [L * f for f in F]
        ems = []
        for it in loops:
            base = B + L * it
            delta = [0] * (ne + 1)
            for sl, v in by_loop[it]:
                o = offs[sl]
                shift = base + o + e0
                tA = shift
                tB = shift + (ne - 1) * e_step + 1e-9
                runs = []
                _cost_runs(tA, tB, v, th, runs)
                for a, b in runs:
                    i0 = int((a - shift) / e_step)
                    if (a - shift) > i0 * e_step:
                        i0 += 1
                    i1 = int((b - shift) / e_step)
                    if (b - shift) > i1 * e_step:
                        i1 += 1
                    if i0 < 0:
                        i0 = 0
                    if i1 > ne:
                        i1 = ne
                    if i1 > i0:
                        delta[i0] += 1
                        delta[i1] -= 1
            if PAIR_W:
                sam = sorted(by_loop[it])
                for a in range(len(sam) - 1):
                    (k1, v1), (k2, v2) = sam[a], sam[a + 1]
                    if v1 == v2:
                        continue
                    gap = offs[k2] - offs[k1]
                    shift = base + offs[k1] + e0
                    runs = []
                    _pair_runs(shift, shift + (ne - 1) * e_step + 1e-9,
                               gap, th, runs)
                    for aa, bb in runs:
                        i0 = int((aa - shift) / e_step)
                        if (aa - shift) > i0 * e_step:
                            i0 += 1
                        i1 = int((bb - shift) / e_step)
                        if (bb - shift) > i1 * e_step:
                            i1 += 1
                        if i0 < 0:
                            i0 = 0
                        if i1 > ne:
                            i1 = ne
                        if i1 > i0:
                            delta[i0] += PAIR_W
                            delta[i1] -= PAIR_W
            em = [0] * ne
            run = 0
            for i in range(ne):
                run += delta[i]
                em[i] = run
            ems.append(em)

        # ---- Viterbi with a quadratic (Brownian) prior on the loop-to-loop
        # ---- clock step: HSI jitter accumulates as a random walk, so the
        # ---- MAP trajectory interpolates instead of jumping.
        n = len(loops)
        dp = list(ems[0])
        ptrs = []
        alpha = ALPHA * e_step * e_step          # cost per grid-step^2
        for k in range(1, n):
            f = list(dp)
            pt = list(range(ne))
            for i in range(1, ne):
                cand = f[i - 1] + lam
                if cand < f[i]:
                    f[i] = cand
                    pt[i] = pt[i - 1]
            for i in range(ne - 2, -1, -1):
                cand = f[i + 1] + lam
                if cand < f[i]:
                    f[i] = cand
                    pt[i] = pt[i + 1]
            if alpha > 0.0:
                g, pg = _quad_dt(dp, alpha, ne)
                for i in range(ne):
                    if g[i] < f[i]:
                        f[i] = g[i]
                        pt[i] = pg[i]
            em = ems[k]
            dp = [f[i] + em[i] for i in range(ne)]
            ptrs.append(pt)
        j = min(range(ne), key=lambda i: dp[i])
        total = dp[j]
        idx = [0] * n
        idx[n - 1] = j
        for k in range(n - 1, 0, -1):
            idx[k - 1] = ptrs[k - 1][idx[k]]
        S = [B + L * loops[k] + (e0 + idx[k] * e_step) for k in range(n)]
        Sfin = (loops, S)

        # ---- refit the linear trend
        m = sum(1 for it in loops if it <= 97)
        if m < 8:
            break
        sx = sy = sxx = sxy = 0.0
        for k in range(m):
            x = float(loops[k])
            y = S[k]
            sx += x
            sy += y
            sxx += x * x
            sxy += x * y
        den = m * sxx - sx * sx
        if den == 0:
            break
        nL = (m * sxy - sx * sy) / den
        nB = (sy - nL * sx) / m
        if abs(nL - L) < 1e-4 and abs(nB - B) < 1e-3:
            L, B = nL, nB
            break
        L, B = nL, nB
    return Sfin, total, L, B


# ---------------------------------------------------------------- decode
def _cells_from(samples, loops, S, L):
    pos = {it: S[k] for k, it in enumerate(loops)}
    offs = [L * f for f in F]
    cells = {}
    for it, sl, v in samples:
        s = pos.get(it)
        if s is None:
            continue
        t = s + offs[sl]
        if t < 0.0 or t >= FRAME_END:
            continue
        j = int(t // BIT)
        cells.setdefault(j, []).append((t - j * BIT, v))
    return cells


def _classify(ph):
    """(bit, margin) - margin 0 means the cell carries no discriminating
    sample (the classic swallowed-pulse blind spot)."""
    e0 = e1 = 0
    m0 = m1 = 0.0
    for p, v in ph:
        if p < T0H:
            if not v:
                e0 += 1
                e1 += 1
        elif p < T1H:
            if v:
                e0 += 1
                m1 += min(p - T0H, T1H - p)
            else:
                e1 += 1
                m0 += min(p - T0H, T1H - p)
        else:
            if v:
                e0 += 1
                e1 += 1
    if e0 < e1:
        return 0, e1 - e0
    if e1 < e0:
        return 1, e0 - e1
    if m0 != m1:
        return (0, 0) if m0 > m1 else (1, 0)
    return (1 if any(v for _p, v in ph) else 0), 0


def _payload_bits(cells):
    bits = []
    margins = []
    for j in range(PAY_LO, PAY_HI):
        b, m = _classify(cells.get(j, []))
        bits.append(b)
        margins.append(m)
    return bits, margins


def decode(samples, meta):
    header = bytes.fromhex(meta.get("header", "FF00AA65"))
    trailer = bytes.fromhex(meta.get("trailer", "9A5500FF"))
    th0 = _thresholds(header, trailer)

    cands = _seed_candidates(samples, th0)
    best = None
    for _sc, L, B in cands:
        res, cost, L2, B2 = _track(samples, L, B, th0)
        if res is None:
            continue
        if best is None or cost < best[0]:
            best = (cost, res, L2, B2)
    if best is None:
        return None
    _cost, (loops, S), L, B = best

    # --- self-consistent refinement: feed the decoded payload back into
    # --- the waveform hypothesis so the tracker sees all 192 bit cells.
    th = list(th0)
    bits = None
    seen = set()
    for _round in range(5):
        cells = _cells_from(samples, loops, S, L)
        bits, _marg = _payload_bits(cells)
        key = tuple(bits)
        if key in seen:
            break
        seen.add(key)
        th_new = list(th0)
        for k, b in enumerate(bits):
            th_new[PAY_LO + k] = T1H if b else T0H
        th = th_new
        res, cost, L, B = _track(samples, L, B, th, rounds=2)
        if res is None:
            break
        loops, S = res

    cells = _cells_from(samples, loops, S, L)
    bits, _marg = _payload_bits(cells)
    out = bytearray()
    for byte_i in range(16):
        val = 0
        for k in range(8):
            val = (val << 1) | bits[byte_i * 8 + k]
        out.append(val)
    return bytes(out)
