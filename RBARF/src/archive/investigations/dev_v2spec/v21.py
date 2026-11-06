"""v2.1 wire format + chase reference implementation (spec-shaped).

CRC8 = poly 0x07, init 0x00, no reflect, no xorout, over DATA bytes only.
payload' = DATA || [C,C,C].
"""
import itertools


def crc8(d):
    r = 0
    for b in d:
        r ^= b
        for _ in range(8):
            r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r


def pow8(j):
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r


def payload_v21(data):
    c = crc8(data)
    return bytes(data) + bytes([c, c, c])


_SYN_CACHE = {}


def syn_table(ND):
    """syn[k] for k = payload'-bit index (MSB-first over ND+3 bytes).

    Data bits: XOR into the CRC8 residual.  Check bits: no CRC effect
    (they move the reference instead).
    """
    if ND in _SYN_CACHE:
        return _SYN_CACHE[ND]
    S = [0] * ((ND + 3) * 8)
    for p in range(ND):
        for b in range(8):                       # b = bit VALUE weight
            k = 8 * p + (7 - b)                  # MSB-first index
            S[k] = pow8(8 * (ND - 1 - p) + b + 8)
    _SYN_CACHE[ND] = S
    return S


def maj3(c0, c1, c2):
    if c0 == c1 or c0 == c2:
        return c0
    if c1 == c2:
        return c1
    return None


def bitmaj3(c0, c1, c2):
    return (c0 & c1) | (c0 & c2) | (c1 & c2)


def order_wmajor(n, wmax, tmax):
    out = []
    for w in range(wmax + 1):
        for s in itertools.combinations(range(n), w):
            out.append(s)
            if len(out) >= tmax:
                return out
    return out


def order_cost(n, wmax, tmax, cost):
    out = []
    for w in range(wmax + 1):
        out.extend(itertools.combinations(range(n), w))
    out.sort(key=lambda s: (sum(cost[i] for i in s), len(s), s))
    return out[:tmax]


def order_dfirst(n, wmax, tmax, cost, isdata):
    """Data-minimal ordering: prefer trials that disturb FEWER DATA bits.

    key = (#data bits flipped, weight, summed margin cost, index tuple)
    """
    out = []
    for w in range(wmax + 1):
        out.extend(itertools.combinations(range(n), w))
    out.sort(key=lambda s: (sum(1 for i in s if isdata[i]), len(s),
                            sum(cost[i] for i in s), s))
    return out[:tmax]


def chase(bits, mgv, ND, N_CAND=8, WMAX=3, TMAX=93, ordering="wmajor",
          fallback=True, W_FB=1, guard="none"):
    """bits/mgv: payload'-relative lists of length (ND+3)*8.

    Returns (payload_bytes|None, ntrials, path) where path is one of
    'direct', 'chase', 'fallback', 'refuse'.
    """
    NPP = ND + 3
    S = syn_table(ND)
    by = [0] * NPP
    for p in range(NPP):
        v = 0
        for j in range(8):
            v = (v << 1) | bits[8 * p + j]
        by[p] = v
    data = bytes(by[:ND])
    C = [by[ND], by[ND + 1], by[ND + 2]]
    r_base = crc8(data)

    R = maj3(*C)
    if R is not None and r_base == R:
        return data, 0, "direct"

    cand = sorted(range(NPP * 8), key=lambda k: (mgv[k], k))[:N_CAND]
    cost = [mgv[k] for k in cand]
    isdata = [k < ND * 8 for k in cand]
    if ordering == "wmajor":
        O = order_wmajor(N_CAND, WMAX, TMAX)
    elif ordering == "cost":
        O = order_cost(N_CAND, WMAX, TMAX, cost)
    else:
        O = order_dfirst(N_CAND, WMAX, TMAX, cost, isdata)
    n_tr = 0
    hits = []
    for s in O:
        if not s:
            continue                      # the empty trial IS the direct test
        n_tr += 1
        Cp = list(C)
        r = r_base
        for i in s:
            k = cand[i]
            p, b = k >> 3, 7 - (k & 7)
            if p < ND:
                r ^= S[k]
            else:
                Cp[p - ND] ^= 1 << b
        Rp = maj3(*Cp)
        if Rp is None:
            continue
        if r == Rp:
            hits.append(s)
            if guard == "alias":
                # reject a pass whose flipped DATA bits are syndrome-aliased
                # by another candidate not in the trial (indistinguishable
                # hypothesis: x has order 127 mod 0x107)
                amb = False
                for i in s:
                    if cand[i] >= ND * 8:
                        continue
                    for j in range(len(cand)):
                        if j not in s and cand[j] < ND * 8 \
                                and S[cand[j]] == S[cand[i]]:
                            amb = True
                if amb:
                    continue
            if guard != "unique":
                d = bytearray(data)
                for i in s:
                    k = cand[i]
                    p, b = k >> 3, 7 - (k & 7)
                    if p < ND:
                        d[p] ^= 1 << b
                return bytes(d), n_tr, "chase"
    if guard == "unique" and len(hits) == 1:
        s = hits[0]
        d = bytearray(data)
        for i in s:
            k = cand[i]
            p, b = k >> 3, 7 - (k & 7)
            if p < ND:
                d[p] ^= 1 << b
        return bytes(d), n_tr, "chase"

    if fallback and maj3(*C) is None:
        refs = [bitmaj3(*C)]
        conf = sorted(range(3), key=lambda q: -sum(
            mgv[8 * (ND + q) + j] for j in range(8)))
        refs += [C[q] for q in conf]
        dcand = [i for i in range(N_CAND) if cand[i] < ND * 8]
        for Rf in refs:
            for w in range(W_FB + 1):
                for s in itertools.combinations(dcand, w):
                    n_tr += 1
                    r = r_base
                    for i in s:
                        r ^= S[cand[i]]
                    if r == Rf:
                        d = bytearray(data)
                        for i in s:
                            k = cand[i]
                            d[k >> 3] ^= 1 << (7 - (k & 7))
                        return bytes(d), n_tr, "fallback"
    return None, n_tr, "refuse"
