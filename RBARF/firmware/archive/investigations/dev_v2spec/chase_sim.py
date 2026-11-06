import random, itertools
def crc8(d):
    r = 0
    for b in d:
        r ^= b
        for _ in range(8):
            r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r
def crc16z(d):
    r = 0
    for b in d:
        r ^= b << 8
        for _ in range(8):
            r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r
NM, NP = 50, 51
S8, S16 = [], []
for k in range(NP * 8):
    p, b = k >> 3, 7 - (k & 7)
    if p < NM:
        e = bytearray(NM); e[p] = 1 << b; S8.append(crc8(e))
    else:
        S8.append(1 << b)
    if p < 48:
        e = bytearray(48); e[p] = 1 << b; S16.append(crc16z(e))
    else:
        S16.append(0)          # CRC16 bytes / CRC8 byte are not CRC16-covered
def order(n, wmax, tmax):
    out = []
    for w in range(wmax + 1):
        for s in itertools.combinations(range(n), w):
            out.append(s)
            if len(out) >= tmax: return out
    return out
def sim(n, wmax, tmax, cont, trials=40000, seed=7):
    random.seed(seed)
    O = order(n, wmax, tmax)
    ok = wrong_stop = nomatch = falseacc = 0
    for _ in range(trials):
        cand = random.sample(range(NP * 8), n)
        nf = random.choice([1, 2, 3])
        true = tuple(sorted(random.sample(range(n), nf)))
        r0 = r16 = 0
        for i in true:
            r0 ^= S8[cand[i]]; r16 ^= S16[cand[i]]
        if r0 == 0:
            continue
        done = False
        for s in O:
            x = y = 0
            for i in s: x ^= S8[cand[i]]; y ^= S16[cand[i]]
            if x != r0: continue
            if y == r16:                      # CRC16 verify passes
                if s == true: ok += 1
                else: falseacc += 1
                done = True; break
            if not cont:
                wrong_stop += 1; done = True; break
            wrong_stop += 0
        if not done: nomatch += 1
    t = trials
    print("n=%2d W<=%d T=%3d %-9s  true=%5.2f%%  wrongstop=%5.2f%%  "
          "nomatch=%5.2f%%  FALSE-ACCEPT=%d/%d"
          % (n, wmax, tmax, "CONTINUE" if cont else "STOP",
             100*ok/t, 100*wrong_stop/t, 100*nomatch/t, falseacc, t))
for n, w, T in ((8,2,37), (8,3,64), (8,3,93), (12,2,79), (12,3,150)):
    sim(n, w, T, False); sim(n, w, T, True)
