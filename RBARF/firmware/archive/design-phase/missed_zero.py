"""missed_zero - swallowed-0-bit recovery on the exact WS2812 bit grid.

The problem this approach is built around
-----------------------------------------
A WS2812 0-bit is only ~350 ns of high inside a 1250 ns cell.  The
sampler's loop period is close to *two* bit cells (~2500 ns), so every
slot samples at an almost fixed phase inside a cell - and whenever that
phase pattern happens to straddle a T0H, a whole run of 0-bits leaves
**no high sample at all**: no pulse, only a longer-than-expected low.
Any decoder that classifies visible pulses by width loses those bits
entirely, and loses the reverse case too (two 1-bits merging into one
~1.8 us high when the ~550 ns low between them lands in a dead zone).

So this decoder never measures a pulse.  It reconstructs the sampling
timeline and reads every one of the 192 cells off the *grid*:

  1. Timing model.  t(i,k) = T_i + FRAC[k] * (T_{i+1} - T_i): per-
     iteration loop start times with fixed intra-loop slot fractions.
     Leaving the loop length free per iteration is what makes this work
     - the captures contain fast local transients (loop lengths swing
     over 2400-2650 ns for a dozen iterations) that no single-period
     model, however well calibrated, can follow.

  2. Timeline search.  T_i is recovered by Viterbi on a quantized time
     lattice, coarse first (50 ns, +-1.7 us) and then refined at 12.5 ns
     in a narrow tube around the coarse path.  The emission cost is
     data-independent: a sample at cell phase < T0H must be high, one at
     phase >= T1H must be low, and every sample of one cell must agree
     with a single hypothesis.  Each cell is scored exactly once, on the
     loop transition it starts in, using the samples of both adjacent
     iterations - that is what keeps a cell's hypothesis consistent
     across the loop boundary.  The known header/trailer bits and the
     known 192-bit frame length anchor both ends.

  3. Decision.  Every cell is decided by min-sum forward-backward over
     the whole lattice: the cost of forcing the cell to 0 vs to 1,
     minimised over all timelines.  Deciding on a single best timeline
     instead throws away the fact that forcing a bit also constrains the
     timeline, which is exactly what is needed for cells whose own
     samples are a tie.  Confident bits are then pinned and the pass is
     repeated (turbo-style), so they constrain their neighbours.

Swallowed 0-bits fall out for free: a cell with no high sample can only
be a 0-bit, because a 700 ns high cannot miss every slot.  Merged 1-bit
pulses fall out too, because the cell boundary is known independently of
the pulse shape.
"""

BIT = 1250.0
T0H = 335.0        # effective high widths at the sampler's input
T1H = 715.0        # threshold (calibrated; nominal 350 / 700)
NBITS = 192                              # 4 + 16 + 4 bytes, MSB first
FRAME_END = (NBITS - 1) * BIT + T1H      # trailer 0xFF ends on a 1-bit

# Intra-loop slot offsets as a fraction of the loop period.  The
# documented cycle positions [1,5,9,13,17,21,27,32] belong to a loop the
# firmware comment claims is 37 cycles; the loop really runs ~40, and the
# unaccounted cycles sit in the wrap-around gap.  Calibrated on captures.
BASE_FRAC = [0.0, 0.100, 0.200, 0.300, 0.400, 0.500, 0.650, 0.775]
FRAC = list(BASE_FRAC)


PLO, PHI = 2360.0, 2680.0   # admissible per-iteration loop length (ns)
C_STEP, C_BAND = 50.0, 1700.0     # coarse lattice
F_STEP, F_BAND = 12.5, 200.0      # fine lattice (tube around coarse path)
PRIOR = 0.040               # cost per ns of loop-length deviation
KNOWN_W = 2.2               # weight on header/trailer cells
CAP = 240.0                 # per-cell cost clip (robustness to outliers)
TURBO_ROUNDS = 3
CONF_TH = 30.0
FRAC_SLACK = 0.02           # how far a per-capture slot phase may move
FRAC_KNOWN_ONLY = True      # calibrate slot phases on known cells only


# ------------------------------------------------------------------ setup
def _known_bits(meta):
    hdr = bytes.fromhex(meta.get("header", "FF00AA65"))
    trl = bytes.fromhex(meta.get("trailer", "9A5500FF"))
    hb = [(x >> (7 - j)) & 1 for x in hdr for j in range(8)]
    tb = [(x >> (7 - j)) & 1 for x in trl for j in range(8)]
    return hb + [None] * (NBITS - len(hb) - len(tb)) + tb


def _pen(ph, v, W):
    """Cost of seeing level v at cell phase ph if the high lasts W ns.

    Zero when consistent; otherwise the distance to the nearest edge of
    the hypothesised waveform, so samples near an edge cost little.
    """
    if ph < W:
        return 0.0 if v else ph
    return (min(ph - W, BIT - ph) if v else 0.0)


def _cell_pair(cl):
    p0 = p1 = 0.0
    for ph, v in cl:
        if ph < T0H:
            if not v:
                p0 += ph
                p1 += ph
            continue
        d0 = ph - T0H
        e = BIT - ph
        if e < d0:
            d0 = e
        if ph < T1H:
            if v:
                p0 += d0
            else:
                p1 += ph
        else:
            if v:
                p0 += d0
                d1 = ph - T1H
                if e < d1:
                    d1 = e
                p1 += d1
    if p0 > CAP:
        p0 = CAP
    if p1 > CAP:
        p1 = CAP
    return p0, p1


# ------------------------------------------------------------------- cost
def _emit(rows, rows2, T, dP, known, first, parts_out=None):
    """Cost of the bit cells that start inside (T, T+dP]."""
    cells = {}
    cost = 0.0
    if first:
        b0 = 0 if T <= 0.0 else int(T // BIT)
    else:
        b0 = int(T // BIT) + 1
    b1 = int((T + dP - 1e-9) // BIT)
    for sl, v in rows:
        tt = T + FRAC[sl] * dP
        b = int(tt // BIT)
        if b < b0 or b > b1:
            if v and b >= NBITS:
                cost += 45.0
            continue
        c = cells.get(b)
        if c is None:
            cells[b] = [(tt - b * BIT, v)]
        else:
            c.append((tt - b * BIT, v))
    if rows2 is not None:
        base = T + dP
        for sl, v in rows2:
            tt = base + FRAC[sl] * dP
            b = int(tt // BIT)
            if b < b0 or b > b1:
                continue
            c = cells.get(b)
            if c is None:
                cells[b] = [(tt - b * BIT, v)]
            else:
                c.append((tt - b * BIT, v))
    for b in range(b0, b1 + 1):
        if b < 0 or b >= NBITS:
            continue
        cl = cells.get(b)
        if not cl:
            continue
        kb = known[b]
        p0, p1 = _cell_pair(cl)
        if kb is not None:
            cost += KNOWN_W * (p1 if kb else p0)
        else:
            cm = p0 if p0 < p1 else p1
            cost += cm
            if parts_out is not None:
                parts_out.append((b, p0, p1, cm))
    return cost


# ---------------------------------------------------------------- lattice
def _ranges(centers, step, band):
    out = []
    for c in centers:
        lo = int((c - band) / step)
        hi = int((c + band) / step) + 1
        out.append((lo, hi))
    return out


def _solve(by_it, its, known, centers, step, band, P0, marginals=False):
    """Viterbi (and optionally min-sum forward-backward) on the lattice."""
    n = len(its)
    nlo = int(PLO / step)
    nhi = int(PHI / step) + 1
    rng = _ranges(centers, step, band)
    lo0, hi0 = rng[0]
    if lo0 < -4:
        lo0 = -4
    if hi0 > int(500.0 / step):
        hi0 = int(500.0 / step)
    if hi0 < lo0:
        hi0 = lo0
    rng[0] = (lo0, hi0)

    rows_l = [by_it[i] for i in its]
    alpha = [None] * n
    a0 = {}
    for j in range(lo0, hi0 + 1):
        a0[j] = 1.2 * abs(j * step - 60.0)
    alpha[0] = a0
    bks = []
    for idx in range(n - 1):
        rows = rows_l[idx]
        rows2 = rows_l[idx + 1]
        lo1, hi1 = rng[idx + 1]
        curr = {}
        bk = {}
        first = (idx == 0)
        for j, base in alpha[idx].items():
            T = j * step
            for m in range(nlo, nhi + 1):
                jn = j + m
                if jn < lo1 or jn > hi1:
                    continue
                dP = m * step
                v = base + _emit(rows, rows2, T, dP, known, first) \
                    + PRIOR * abs(dP - P0)
                old = curr.get(jn)
                if old is None or v < old:
                    curr[jn] = v
                    bk[jn] = j
        if not curr:
            return None
        alpha[idx + 1] = curr
        bks.append(bk)

    rows = rows_l[-1]
    fin = {}
    for j, base in alpha[n - 1].items():
        fin[j] = _emit(rows, None, j * step, P0, known, False)
    bestj = None
    bestv = None
    for j, base in alpha[n - 1].items():
        v = base + fin[j]
        if bestv is None or v < bestv:
            bestv = v
            bestj = j
    if bestj is None:
        return None
    path = [0] * n
    path[-1] = bestj
    j = bestj
    for idx in range(n - 1, 0, -1):
        j = bks[idx - 1][j]
        path[idx - 1] = j
    T = {}
    dP = {}
    for idx, it in enumerate(its):
        T[it] = path[idx] * step
        dP[it] = ((path[idx + 1] - path[idx]) * step
                  if idx + 1 < n else P0)
    res = {"T": T, "dP": dP, "centers": [p * step for p in path]}
    if not marginals:
        return res

    beta = [None] * n
    beta[n - 1] = fin
    for idx in range(n - 2, -1, -1):
        rows = rows_l[idx]
        rows2 = rows_l[idx + 1]
        bn = beta[idx + 1]
        cur = {}
        first = (idx == 0)
        for j in alpha[idx]:
            T0 = j * step
            best = None
            for m in range(nlo, nhi + 1):
                nb = bn.get(j + m)
                if nb is None:
                    continue
                dPv = m * step
                v = _emit(rows, rows2, T0, dPv, known, first) \
                    + PRIOR * abs(dPv - P0) + nb
                if best is None or v < best:
                    best = v
            if best is not None:
                cur[j] = best
        if not cur:
            return res
        beta[idx] = cur

    INF = float("inf")
    m0 = [INF] * NBITS
    m1 = [INF] * NBITS
    for idx in range(n - 1):
        rows = rows_l[idx]
        rows2 = rows_l[idx + 1]
        bn = beta[idx + 1]
        first = (idx == 0)
        for j, av in alpha[idx].items():
            T0 = j * step
            for m in range(nlo, nhi + 1):
                nb = bn.get(j + m)
                if nb is None:
                    continue
                dPv = m * step
                parts = []
                em = _emit(rows, rows2, T0, dPv, known, first, parts)
                if not parts:
                    continue
                base = av + em + PRIOR * abs(dPv - P0) + nb
                for b, c0, c1, cm in parts:
                    v0 = base - cm + c0
                    v1 = base - cm + c1
                    if v0 < m0[b]:
                        m0[b] = v0
                    if v1 < m1[b]:
                        m1[b] = v1
    rows = rows_l[-1]
    for j, av in alpha[n - 1].items():
        parts = []
        em = _emit(rows, None, j * step, P0, known, False, parts)
        if not parts:
            continue
        base = av + em
        for b, c0, c1, cm in parts:
            v0 = base - cm + c0
            v1 = base - cm + c1
            if v0 < m0[b]:
                m0[b] = v0
            if v1 < m1[b]:
                m1[b] = v1
    res["m0"] = m0
    res["m1"] = m1
    return res


# --------------------------------------------------------------- decoding
def _cells_of(by_it, its, T, dP):
    cells = [[] for _ in range(NBITS)]
    for it in its:
        t0 = T[it]
        d = dP[it]
        for sl, v in by_it[it]:
            tt = t0 + FRAC[sl] * d
            b = int(tt // BIT)
            if 0 <= b < NBITS:
                cells[b].append((tt - b * BIT, v))
    return cells


def _frac_cost(by_it, its, T, dP, known, f):
    cells = [[] for _ in range(NBITS)]
    for it in its:
        t0 = T[it]
        d = dP[it]
        for sl, v in by_it[it]:
            tt = t0 + f[sl] * d
            b = int(tt // BIT)
            if 0 <= b < NBITS:
                cells[b].append((tt - b * BIT, v))
    tot = 0.0
    for b in range(NBITS):
        cl = cells[b]
        if not cl:
            continue
        p0, p1 = _cell_pair(cl)
        kb = known[b]
        if kb is not None:
            tot += KNOWN_W * (p1 if kb else p0)
        elif not FRAC_KNOWN_ONLY:
            tot += p0 if p0 < p1 else p1
    return tot


def _fit_frac(by_it, its, T, dP, known, frac):
    """Per-capture refinement of the intra-loop slot phases.

    The phases are only nominally fixed: the HSI clock differs per
    capture, and the sampling code takes a different number of cycles
    depending on the level it read.  A few ns matter here - most residual
    bit errors are cells whose two hypotheses tie to within ~15 ns.  The
    known header and trailer bits drive the fit; FRAC is kept near
    nominal so it cannot run away.
    """
    frac = list(frac)
    cur = _frac_cost(by_it, its, T, dP, known, frac)
    for st in (0.016, 0.008, 0.004, 0.002, 0.001):
        for _ in range(8):
            improved = False
            for k in range(1, 8):
                base = frac[k]
                for d in (-st, st):
                    x = base + d
                    if abs(x - BASE_FRAC[k]) > FRAC_SLACK:
                        continue
                    if x <= frac[k - 1] + 0.012:
                        continue
                    if k < 7 and x >= frac[k + 1] - 0.012:
                        continue
                    if k == 7 and x > 0.95:
                        continue
                    cand = list(frac)
                    cand[k] = x
                    v = _frac_cost(by_it, its, T, dP, known, cand)
                    if v < cur - 1e-9:
                        cur = v
                        frac = cand
                        improved = True
            if not improved:
                break
    return frac


def _decide(cells):
    bits = []
    for b in range(NBITS):
        p0, p1 = _cell_pair(cells[b])
        bits.append(0 if p0 <= p1 else 1)
    return bits


def _pack(bits):
    out = bytearray()
    pb = bits[32:160]
    for i in range(16):
        v = 0
        for x in pb[i * 8:(i + 1) * 8]:
            v = (v << 1) | x
        out.append(v)
    return bytes(out)


def decode(samples, meta):
    if len(samples) < 200:
        return None
    lastn = None
    for n in range(len(samples) - 1, -1, -1):
        if samples[n][2]:
            lastn = n
            break
    if lastn is None or lastn < 100:
        return None
    work = samples[:min(len(samples), lastn + 24)]
    known = _known_bits(meta)

    by_it = {}
    for it, sl, v in work:
        by_it.setdefault(it, []).append((sl, v))
    its = sorted(by_it)
    if len(its) < 40:
        return None
    it_last = work[lastn][0]
    P0 = FRAME_END / (it_last + 0.55)
    if not (2400.0 < P0 < 2620.0):
        P0 = 2505.0

    global FRAC
    saved = FRAC
    try:
        return _decode_inner(by_it, its, known, P0)
    finally:
        FRAC = saved


def _softened(bits, known):
    soft = list(bits)
    for b in range(32):
        soft[b] = known[b]
    for b in range(160, NBITS):
        soft[b] = known[b]
    return soft


def _decode_inner(by_it, its, known, P0):
    global FRAC
    FRAC = list(BASE_FRAC)

    # --- coarse timeline
    res = _solve(by_it, its, known, [P0 * i for i in range(len(its))],
                 C_STEP, C_BAND, P0)
    if res is None:
        return None
    centers = res["centers"]

    # --- fine timeline; alternate slot-phase calibration and decoding
    bits = None
    soft = known
    for r in range(4):
        res = _solve(by_it, its, soft, centers, F_STEP, F_BAND, P0)
        if res is None:
            break
        centers = res["centers"]
        nb = _decide(_cells_of(by_it, its, res["T"], res["dP"]))
        FRAC = _fit_frac(by_it, its, res["T"], res["dP"], known, FRAC)
        if nb == bits and r >= 2:
            break
        bits = nb
        soft = _softened(bits, known)
    if bits is None:
        return None

    # --- turbo: marginal decisions, pin the confident ones, repeat
    conf = [0.0] * NBITS
    soft = list(known)
    for _ in range(TURBO_ROUNDS):
        res = _solve(by_it, its, soft, centers, F_STEP, F_BAND, P0,
                     marginals=True)
        if res is None or "m0" not in res:
            break
        centers = res["centers"]
        m0, m1 = res["m0"], res["m1"]
        for b in range(32, 160):
            if soft[b] is not None:
                continue
            a, c = m0[b], m1[b]
            if a == c:
                continue
            bits[b] = 0 if a < c else 1
            conf[b] = abs(a - c)
        nxt = list(known)
        nfix = 0
        for b in range(32, 160):
            if conf[b] > CONF_TH:
                nxt[b] = bits[b]
                nfix += 1
        if nfix == 0 or nxt == soft:
            break
        soft = nxt
    return _pack(bits)
