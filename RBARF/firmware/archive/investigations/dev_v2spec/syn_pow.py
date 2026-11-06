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
def pow8(j):                       # x^j mod (x^8+x^2+x+1)
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r
def pow16(j):                      # x^j mod (x^16+x^12+x^5+1)
    r = 1
    for _ in range(j):
        r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r
NM = 50
ok = True
for p in range(NM):
    for b in range(8):
        e = bytearray(NM); e[p] = 1 << b
        j = 8 * (NM - 1 - p) + b       # bit-distance from end of message
        if crc8(e) != pow8(j + 8): ok = False; print("crc8 mismatch", p, b)
print("CRC8  syndrome == x^(j+8)  mod 0x107 :", ok)
# CRC8 byte itself (comparand): flip of bit b contributes 1<<b == x^b
print("  comparand: 1<<b == x^b :", all(pow8(b) == (1 << b) for b in range(8)))
# so with j' = 8*(NP-1-p)+b over payload' (NP=51) the CRC8 byte gives j'=b
print("  uniform:  syn8(p,b) = x^(8*(51-1-p)+b) for p<50 -> j+8 ; p=50 -> b  :",
      all(pow8(8 * (51 - 1 - p) + b) == pow8(8 * (NM - 1 - p) + b + 8)
          for p in range(NM) for b in range(8)))
ok = True
for p in range(48):
    for b in range(8):
        e = bytearray(48); e[p] = 1 << b
        j = 8 * (48 - 1 - p) + b
        if crc16z(e) != pow16(j + 16): ok = False; print("crc16 mismatch", p, b)
print("CRC16 syndrome == x^(j+16) mod 0x11021 :", ok)
print("period of x^j mod 0x107 :", next(j for j in range(1, 300) if pow8(j) == 1))
print("period of x^j mod 0x11021:", next((j for j in range(1, 200000) if pow16(j) == 1), None))

# --- uniform payload'-relative formula, verified end to end -------------
ND, NPP = 48, 51
def crc16f(d):
    r = 0xFFFF
    for x in d:
        r ^= x << 8
        for _ in range(8):
            r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r
def syn8_of(j):  return pow8(j)
def syn16_of(j): return pow16(j - 8) if j >= 8 else 0
import random
random.seed(3)
bad = 0
for _ in range(4000):
    data = bytearray(random.randrange(256) for _ in range(ND))
    c16 = crc16f(data); blk = bytes([c16 >> 8, c16 & 0xFF])
    pay = bytearray(data + blk + bytes([crc8(bytes(data) + blk)]))
    ks = random.sample(range(NPP * 8), random.randrange(1, 4))
    s8 = s16 = 0
    for k in ks:
        p, b = k >> 3, 7 - (k & 7)
        j = 8 * (NPP - 1 - p) + b
        s8 ^= syn8_of(j); s16 ^= syn16_of(j)
        pay[p] ^= 1 << b
    r8  = crc8(bytes(pay[:ND + 2])) ^ pay[ND + 2]
    r16 = crc16f(bytes(pay[:ND])) ^ ((pay[ND] << 8) | pay[ND + 1])
    if r8 != s8 or r16 != s16: bad += 1
print("uniform residual==XOR(syndromes): %d/4000 mismatches" % bad)
