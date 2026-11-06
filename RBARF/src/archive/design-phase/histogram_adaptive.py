"""histogram_adaptive -- WS2812 reconstruction from an STM8 oversampled
capture: adaptive pulse statistics + a globally constrained loop-phase /
bit Viterbi.

How it works
------------
1. *Adaptive pulse statistics.*  Nothing on the receiver side is treated
   as a fixed nanosecond constant.  The sampling-loop period is estimated
   per capture, the eight intra-loop slot offsets are expressed as
   fractions of that period and then re-fitted per capture, and the
   effective high-pulse widths (what the GPIO actually reads as "high",
   which is *not* the documented 350/700 ns) are re-estimated per capture
   from the histogram of sample phases.  A first decode seeds those
   estimates and the whole thing is iterated to a fixed point.

2. *Global constraint.*  A frame is exactly 192 bits -- 32 header, 128
   payload, 32 trailer -- and the line latches low afterwards.  The last
   high sample pins the frame end and brackets the loop period; the
   header and trailer bit values are clamped inside the trellis.  A bit
   stream with the wrong number of bits between header and trailer is not
   representable by any path, so a miscounted swallowed zero or merged
   pulse cannot survive: it is repaired globally rather than patched
   locally.

3. *Loop-phase Viterbi.*  Within one sampling loop the slot offsets are
   rigid (a fixed instruction sequence); jitter enters only at the loop
   boundary (byte store / HSI drift).  The decoder therefore carries one
   hidden phase per *loop*, not per sample, together with the value of the
   bit the current sample sits in, and pays a soft cost near the WS2812
   edges.  Swallowed 0-bits (T0H entirely inside an inter-slot dead zone)
   and merged pulses (one long high across two 1-bits) need no special
   case -- they are just loops whose slots miss or straddle an edge.
"""

BIT_NS = 1250.0
NBITS = 192
HDR = "FF00AA65"
TRL = "9A5500FF"

# Seed values, refined per capture.
W0_NS = 375.0
W1_NS = 862.0
SLOT_FRAC = [0.0, 0.105, 0.245, 0.345, 0.470, 0.535, 0.720, 0.840]

PARAMS = {
    "Q": 12.5,
    "ER": 52,
    "BEAM": 26.0,
    "JMAX": 14,
    "JP1": 1.20,
    "JPR": 0.50,
    "EW0": 45.0,
    "EW1": 55.0,
    "PHI": 0.986,
    "PLO": 0.013,
    "W0": W0_NS,
    "W1": W1_NS,
    "NL": 17,
    "LSTEP": 1.5,
    "NREFINE": 3,
    "OFFWIN": 120.0,
    "OFFSTEP": 10.0,
    "MISSPEN": 8.0,
}


def _bits_of(hexs):
    return [int(x) for byte in bytes.fromhex(hexs) for x in f"{byte:08b}"]


def _known_bits(meta):
    m = meta if isinstance(meta, dict) else {}
    hdr = _bits_of(m.get("header", HDR))
    trl = _bits_of(m.get("trailer", TRL))
    known = [None] * NBITS
    for i, b in enumerate(hdr):
        if i < NBITS:
            known[i] = b
    for i, b in enumerate(trl):
        j = NBITS - len(trl) + i
        if 0 <= j < NBITS:
            known[j] = b
    return known


def _viterbi(per, nit, Lm, prm, known, offs, W0, W1):
    """per[i][s] = 0/1/None.  Returns (bitvals, cost, loop_starts)."""
    Q = prm["Q"]
    ER = prm["ER"]
    JMAX = prm["JMAX"]
    JP1 = prm["JP1"]
    JPR = prm["JPR"]
    jpen = [0.0] + [JP1 + JPR * (k - 1) for k in range(1, JMAX + 1)]
    BEAM = prm["BEAM"]
    EW0 = prm["EW0"]
    EW1 = prm["EW1"]
    PHI = prm["PHI"]
    PLO = prm["PLO"]

    NE = 2 * ER + 1
    NS = NE * 2
    INF = float("inf")
    inv = 1.0 / BIT_NS
    END = NBITS * BIT_NS
    from math import log
    LHI = -log(PHI)
    LHIC = -log(1.0 - PHI)
    LLO = -log(PLO)
    LLOC = -log(1.0 - PLO)

    def emit(tau, b, obs):
        if tau < 0.0 or tau >= END:
            return LLO if obs else LLOC
        k = int(tau * inv)
        ph = tau - k * BIT_NS
        w = W1 if b else W0
        ew = EW1 if b else EW0
        lo = w - ew
        if ph <= lo:
            return LHI if obs else LHIC
        hi = w + ew
        if ph >= hi:
            return LLO if obs else LLOC
        f = (ph - lo) / (hi - lo)
        p = PHI + (PLO - PHI) * f
        return -log(p) if obs else -log(1.0 - p)

    cost = [INF] * NS
    v0 = per[0][0]
    k0 = known[0]
    for ei in range(NE):
        e = (ei - ER) * Q
        if e < -100.0 or e > 300.0:
            continue
        c = (e if e > 0 else -e) * 0.002
        for b in (0, 1):
            if k0 is not None and k0 != b:
                continue
            cc = c + (emit(e, b, v0) if v0 is not None else 0.0)
            if cc < cost[ei * 2 + b]:
                cost[ei * 2 + b] = cc

    live = [i for i in range(NS) if cost[i] != INF]
    if not live:
        return None, INF, None
    parents = []
    prev_base = offs[0]
    for i in range(nit):
        for s in range(8):
            if i == 0 and s == 0:
                continue
            base = i * Lm + offs[s]
            obs = per[i][s]
            is_start = (s == 0)
            nc = [INF] * NS
            par = [-1] * NS
            em0 = [0.0] * NE
            em1 = [0.0] * NE
            kk = [0] * NE
            kp = [0] * NE
            for ei in range(NE):
                off = (ei - ER) * Q
                tau = base + off
                if obs is not None:
                    em0[ei] = emit(tau, 0, obs)
                    em1[ei] = emit(tau, 1, obs)
                kk[ei] = -1 if tau < 0 else int(tau * inv)
                tp = prev_base + off
                kp[ei] = -1 if tp < 0 else int(tp * inv)
            jr = range(-JMAX, JMAX + 1) if is_start else (0,)
            for si in live:
                c = cost[si]
                ei = si >> 1
                b = si & 1
                kprev = kp[ei]
                for j in jr:
                    ei2 = ei + j
                    if ei2 < 0 or ei2 >= NE:
                        continue
                    pj = c + jpen[j if j > 0 else -j]
                    k2 = kk[ei2]
                    if k2 == kprev:
                        tgt = ei2 * 2 + b
                        c2 = pj + (em1[ei2] if b else em0[ei2])
                        if c2 < nc[tgt]:
                            nc[tgt] = c2
                            par[tgt] = si
                    else:
                        kn = known[k2] if (0 <= k2 < NBITS) else None
                        if kn is None:
                            c2 = pj + em0[ei2]
                            if c2 < nc[ei2 * 2]:
                                nc[ei2 * 2] = c2
                                par[ei2 * 2] = si
                            c2 = pj + em1[ei2]
                            if c2 < nc[ei2 * 2 + 1]:
                                nc[ei2 * 2 + 1] = c2
                                par[ei2 * 2 + 1] = si
                        else:
                            tgt = ei2 * 2 + kn
                            c2 = pj + (em1[ei2] if kn else em0[ei2])
                            if c2 < nc[tgt]:
                                nc[tgt] = c2
                                par[tgt] = si
            mn = INF
            for i2 in range(NS):
                if nc[i2] < mn:
                    mn = nc[i2]
            if mn == INF:
                return None, INF, None
            lim = mn + BEAM
            live = []
            for i2 in range(NS):
                if nc[i2] <= lim:
                    live.append(i2)
                else:
                    nc[i2] = INF
            cost = nc
            parents.append(par)
            prev_base = base

    bi = -1
    bc = INF
    for i in range(NS):
        if cost[i] < bc:
            bc = cost[i]
            bi = i
    if bi < 0 or bc == INF:
        return None, INF, None
    path = [bi]
    for n in range(len(parents) - 1, -1, -1):
        bi = parents[n][bi]
        if bi < 0:
            return None, INF, None
        path.append(bi)
    path.reverse()

    bitvals = {}
    starts = [0.0] * nit
    idx = 0
    for i in range(nit):
        for s in range(8):
            if idx >= len(path):
                break
            si = path[idx]
            idx += 1
            e = ((si >> 1) - ER) * Q
            if s == 0:
                starts[i] = i * Lm + e
            tau = i * Lm + offs[s] + e
            if tau < 0:
                continue
            k = int(tau * inv)
            if 0 <= k < NBITS and k not in bitvals:
                bitvals[k] = si & 1
    return bitvals, bc, starts


def _assemble(bitvals):
    out = bytearray()
    for i in range(16):
        v = 0
        for j in range(8):
            v = (v << 1) | bitvals.get(32 + i * 8 + j, 0)
        out.append(v)
    return bytes(out)


def _prepare(samples):
    nit = 0
    for it, s, v in samples:
        if it + 1 > nit:
            nit = it + 1
    per = [[None] * 8 for _ in range(nit)]
    last = -1
    for it, s, v in samples:
        per[it][s] = v
        if v:
            n = it * 8 + s
            if n > last:
                last = n
    return per, nit, last


def _full_frame(bitvals, known):
    f = [0] * NBITS
    for k in range(NBITS):
        f[k] = known[k] if known[k] is not None else bitvals.get(k, 0)
    return f


def _refit(per, nit, starts, frame, offs, W0, W1, prm):
    """Adaptive re-estimation of slot offsets and effective pulse widths."""
    inv = 1.0 / BIT_NS
    win = prm["OFFWIN"]
    st = prm["OFFSTEP"]
    n = int(win / st)

    def lv(tau, w0, w1):
        if tau < 0.0 or tau >= NBITS * BIT_NS:
            return 0
        k = int(tau * inv)
        ph = tau - k * BIT_NS
        return 1 if ph < (w1 if frame[k] else w0) else 0

    newoffs = list(offs)
    for s in range(8):
        best = None
        for d in range(-n, n + 1):
            cand = offs[s] + d * st
            bad = 0
            for i in range(nit):
                v = per[i][s]
                if v is None:
                    continue
                if lv(starts[i] + cand, W0, W1) != v:
                    bad += 1
            if best is None or bad < best[0]:
                best = (bad, cand)
        newoffs[s] = best[1]
    sh = newoffs[0] - offs[0]
    if sh:
        newoffs = [x - sh for x in newoffs]
        starts = [x + sh for x in starts]

    # phases of all samples, split by the bit they land in
    ph0 = []
    ph1 = []
    for i in range(nit):
        for s in range(8):
            v = per[i][s]
            if v is None:
                continue
            tau = starts[i] + newoffs[s]
            if tau < 0.0 or tau >= NBITS * BIT_NS:
                continue
            k = int(tau * inv)
            (ph1 if frame[k] else ph0).append((tau - k * BIT_NS, v))

    def fit_w(lst, w, lo, hi):
        if len(lst) < 20:
            return w
        best = None
        c = lo
        while c <= hi:
            bad = 0
            for p, v in lst:
                if (1 if p < c else 0) != v:
                    bad += 1
            if best is None or bad < best[0]:
                best = (bad, c)
            c += 10.0
        return best[1]

    return newoffs, starts, fit_w(ph0, W0, 300.0, 470.0), \
        fit_w(ph1, W1, 760.0, 960.0)


def _run(samples, meta, prm):
    per, nit_all, last = _prepare(samples)
    if last < 400:
        return None, None
    known = _known_bits(meta)
    nit = min(nit_all, last // 8 + 2)

    li = last // 8
    ls = last % 8
    W0 = prm["W0"]
    W1 = prm["W1"]
    end = (NBITS - 1) * BIT_NS + W1
    denom = li + SLOT_FRAC[ls]
    Lc = end / denom if denom > 0 else 2500.0

    NL = prm["NL"]
    best = None
    for a in range(NL):
        Lm = Lc + (a - (NL - 1) // 2) * prm["LSTEP"]
        offs = [f * Lm for f in SLOT_FRAC]
        bv, c, starts = _viterbi(per, nit, Lm, prm, known, offs, W0, W1)
        if bv is None:
            continue
        miss = 0
        for k in range(NBITS):
            if k not in bv:
                miss += 1
        c += prm["MISSPEN"] * miss
        if best is None or c < best[0]:
            best = (c, bv, Lm, offs, starts, W0, W1)
    if best is None:
        return None, None

    # ---- adaptive refinement -------------------------------------------
    cur = best
    for _ in range(prm["NREFINE"]):
        c0, bv, Lm, offs, starts, w0, w1 = cur
        frame = _full_frame(bv, known)
        offs2, starts2, w0b, w1b = _refit(per, nit, starts, frame, offs,
                                          w0, w1, prm)
        got = None
        for dl in (-1.5, 0.0, 1.5):
            Lm2 = Lm + dl
            sc = Lm2 / Lm
            o2 = [x * sc for x in offs2]
            bv2, c2, st2 = _viterbi(per, nit, Lm2, prm, known, o2, w0b, w1b)
            if bv2 is None:
                continue
            miss = 0
            for k in range(NBITS):
                if k not in bv2:
                    miss += 1
            c2 += prm["MISSPEN"] * miss
            if got is None or c2 < got[0]:
                got = (c2, bv2, Lm2, o2, st2, w0b, w1b)
        if got is None:
            break
        if got[1] == cur[1] and abs(got[0] - cur[0]) < 1e-9:
            cur = got
            break
        cur = got
    return cur[1], cur


def decode(samples, meta):
    if not samples or len(samples) < 400:
        return None
    bv, _ = _run(samples, meta, PARAMS)
    if bv is None:
        return None
    return _assemble(bv)
