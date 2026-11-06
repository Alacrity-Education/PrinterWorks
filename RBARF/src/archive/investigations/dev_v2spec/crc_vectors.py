def crc16_ccitt_false(d):
    r = 0xFFFF
    for b in d:
        r ^= b << 8
        for _ in range(8):
            r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r

def crc8(d):
    r = 0x00
    for b in d:
        r ^= b
        for _ in range(8):
            r = ((r << 1) ^ 0x07) & 0xFF if (r & 0x80) else (r << 1) & 0xFF
    return r

print("check 123456789: crc16=0x%04X crc8=0x%02X" % (
    crc16_ccitt_false(b"123456789"), crc8(b"123456789")))

# test-frame vector: DATA = 00..0F
data = bytes(range(16))
c16 = crc16_ccitt_false(data)
blk = bytes([c16 >> 8, c16 & 0xFF])
c8 = crc8(data + blk)
pay = data + blk + bytes([c8])
frame = bytes.fromhex("FF00AA65") + pay + bytes.fromhex("9A5500FF")
print("TEST data 00..0F: crc16=0x%04X crc8=0x%02X" % (c16, c8))
print("payload'(19) =", pay.hex().upper())
print("frame(%d)      =" % len(frame), frame.hex().upper())

# production vector: DATA = 48 bytes GRB ramp i*5 & 0xFF
d48 = bytes((i * 5) & 0xFF for i in range(48))
c16b = crc16_ccitt_false(d48)
blkb = bytes([c16b >> 8, c16b & 0xFF])
c8b = crc8(d48 + blkb)
print("PROD ramp(i*5): crc16=0x%04X crc8=0x%02X" % (c16b, c8b))
print("payload'(51) =", (d48 + blkb + bytes([c8b])).hex().upper())
print("frame len    =", 4 + 51 + 4, "bytes =", 8 * 59, "bits")

# linearity proof of the syndrome trick (CRC8, init 0 -> literally linear)
import random
random.seed(1)
msg = bytearray(random.randrange(256) for _ in range(50))
base = crc8(msg)
for trial in range(2000):
    ks = random.sample(range(50 * 8), random.randrange(1, 4))
    syn = 0
    for k in ks:
        e = bytearray(50)
        e[k >> 3] = 1 << (7 - (k & 7))
        syn ^= crc8(e)
    m2 = bytearray(msg)
    for k in ks:
        m2[k >> 3] ^= 1 << (7 - (k & 7))
    assert crc8(m2) == base ^ syn, (ks,)
print("CRC8 syndrome linearity: 2000/2000 OK")

# CRC16 difference-linearity (init cancels in the XOR difference)
def crc16_zero_init(d):
    r = 0x0000
    for b in d:
        r ^= b << 8
        for _ in range(8):
            r = ((r << 1) ^ 0x1021) & 0xFFFF if (r & 0x8000) else (r << 1) & 0xFFFF
    return r
msg = bytearray(random.randrange(256) for _ in range(48))
base16 = crc16_ccitt_false(msg)
for trial in range(2000):
    ks = random.sample(range(48 * 8), random.randrange(1, 4))
    syn = 0
    for k in ks:
        e = bytearray(48)
        e[k >> 3] = 1 << (7 - (k & 7))
        syn ^= crc16_zero_init(e)
    m2 = bytearray(msg)
    for k in ks:
        m2[k >> 3] ^= 1 << (7 - (k & 7))
    assert crc16_ccitt_false(m2) == base16 ^ syn
print("CRC16 difference-linearity: 2000/2000 OK")
