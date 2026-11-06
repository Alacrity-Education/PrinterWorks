from collections import Counter
import random, itertools
from math import comb

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

# production: CRC8 message = DATA(48) || CRC16_HI || CRC16_LO = 50 bytes,
# plus the received CRC8 byte itself (comparand) = payload' bit range 0..407
NM = 50                       # CRC8-covered bytes
NP = 51                       # payload' bytes (chase-eligible)
syn8 = []
for k in range(NP * 8):
    p, b = k >> 3, 7 - (k & 7)
    if p < NM:
        e = bytearray(NM); e[p] = 1 << b
        syn8.append(crc8(e))
    else:
        syn8.append(1 << b)   # flip in the received CRC8 byte -> comparand
c = Counter(syn8)
print("prod: %d chase-eligible bit positions, %d distinct CRC8 syndromes"
      % (len(syn8), len(c)))
print("  zero syndromes (undetectable single-bit): %d" % c.get(0, 0))
print("  mean positions per syndrome value: %.2f ; max %d"
      % (len(syn8) / len(c), max(c.values())))
amb = sum(v - 1 for v in c.values())
print("  P(a random single-bit error shares its syndrome with >=1 other"
      " eligible position) = %.3f" % (sum(v for v in c.values() if v > 1) / len(syn8)))

# same for CRC16 over DATA(48) only -- 384 positions
syn16 = []
for k in range(48 * 8):
    p, b = k >> 3, 7 - (k & 7)
    e = bytearray(48); e[p] = 1 << b
    syn16.append(crc16z(e))
c16 = Counter(syn16)
print("prod CRC16: %d positions, %d distinct syndromes, max mult %d"
      % (len(syn16), len(c16), max(c16.values())))

# joint 24-bit syndrome over the 384 DATA positions
joint = Counter((syn8[k], syn16[k]) for k in range(48 * 8))
print("joint (CRC8,CRC16) over DATA bits: %d distinct / %d -> collisions %d"
      % (len(joint), 48 * 8, 48 * 8 - len(joint)))

# empirical: 2-3 random wrong bits among 8 candidates; how often does an
# earlier (weight-major, lex) subset match the true syndrome first?
random.seed(7)
def subsets(n, wmax, tmax):
    out = []
    for w in range(wmax + 1):
        for s in itertools.combinations(range(n), w):
            out.append(s)
            if len(out) >= tmax: return out
    return out
ORDER = subsets(8, 3, 64)
stop_before = 0; found = 0; trials = 20000
for _ in range(trials):
    cand = random.sample(range(NP * 8), 8)
    true = tuple(sorted(random.sample(range(8), random.choice([1, 2, 3]))))
    r0 = 0
    for i in true: r0 ^= syn8[cand[i]]
    if r0 == 0:                      # true error undetectable by CRC8 alone
        continue
    for s in ORDER:
        x = 0
        for i in s: x ^= syn8[cand[i]]
        if x == r0:
            if s == true: found += 1
            else: stop_before += 1
            break
print("chase sim (n=8, W<=3, T=64, %d frames with 1-3 true flips in list):"
      % trials)
print("  true pattern reached first : %.2f%%" % (100 * found / trials))
print("  earlier wrong CRC8 match   : %.2f%%" % (100 * stop_before / trials))
print("  no match within budget     : %.2f%%"
      % (100 * (trials - found - stop_before) / trials))
