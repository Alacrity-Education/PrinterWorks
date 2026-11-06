"""Chase outcome conditioned on the MEASURED wrong-bit weight + rank mix."""
import random, itertools
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
def pow16(j):
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r
def syn(NPP, p, b):
    j = 8 * (NPP - 1 - p) + b
    return pow8(j), (pow16(j - 8) if j >= 8 else 0)
def order(n, wmax, tmax):
    out = []
    for w in range(wmax + 1):
        for s in itertools.combinations(range(n), w):
            out.append(s)
            if len(out) >= tmax: return out
    return out
def sim(NPP, weights, n=8, wmax=3, tmax=93, cont=False, trials=40000, seed=11):
    random.seed(seed)
    O = order(n, wmax, tmax)
    S = [syn(NPP, k >> 3, 7 - (k & 7)) for k in range(NPP * 8)]
    ok = stop = nomatch = fa = undet = 0
    for _ in range(trials):
        cand = random.sample(range(NPP * 8), n)
        nf = random.choice(weights)
        true = tuple(sorted(random.sample(range(n), nf)))
        r8 = r16 = 0
        for i in true:
            r8 ^= S[cand[i]][0]; r16 ^= S[cand[i]][1]
        if r8 == 0: undet += 1; continue
        done = False
        for s in O:
            x = y = 0
            for i in s: x ^= S[cand[i]][0]; y ^= S[cand[i]][1]
            if x != r8: continue
            if y == r16:
                (ok if s == true else fa).__class__  # noop
                if s == true: ok += 1
                else: fa += 1
                done = True; break
            if not cont: stop += 1; done = True; break
        if not done: nomatch += 1
    t = trials
    print("  NPP=%2d w=%-12s %-8s -> recovered %5.2f%%  refuse(wrongstop) %5.2f%%"
          "  refuse(nomatch) %5.2f%%  undetectable %.2f%%  FALSE-ACCEPT %d"
          % (NPP, str(weights), "CONT" if cont else "STOP",
             100*ok/t, 100*stop/t, 100*nomatch/t, 100*undet/t, fa))
print("production payload' = 51 B (408 chase-eligible bits):")
for w in ([1], [2], [3], [1,1,1,1,1,1,1,2,2]):     # last = measured bench mix
    sim(51, w, cont=False); sim(51, w, cont=True)
print("test payload' = 19 B (152 chase-eligible bits):")
for w in ([1], [1,1,1,1,1,1,1,2,2]):
    sim(19, w, cont=False)
