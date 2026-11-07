//! Host tests of the receive step: synthetic TIM3 width bursts of known
//! frames through `decode`, plus every corruption class the receiver must
//! reject or tolerate. These stand in for the silicon soak (B3) until the
//! bench stimulus is wired.

use rbarf_proto::*;

/// Tiny deterministic PRNG (xorshift32) for jitter and payloads.
struct Rng(u32);
impl Rng {
    fn next(&mut self) -> u32 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        self.0 = x;
        x
    }
    fn range(&mut self, lo: u8, hi: u8) -> u8 {
        lo + (self.next() % (hi - lo + 1) as u32) as u8
    }
}

/// What the DMA ring would hold for `wire`: one CCR2 low byte per bit.
fn widths(wire: &[u8], t0: u8, t1: u8) -> Vec<u8> {
    wire.iter()
        .flat_map(|&b| (0..8).map(move |k| if b & (0x80 >> k) != 0 { t1 } else { t0 }))
        .collect()
}

fn decode_vec(w: &[u8]) -> Result<([u8; DATA_LEN], Vote), Reject> {
    let mut st = WidthStats::EMPTY;
    decode(w.len(), |i| w[i], &mut st)
}

/// The demo `STATIC` preset (firmware/rbarf-fw/src/demo.rs).
fn demo_static() -> [u8; DATA_LEN] {
    let mut d = [0u8; DATA_LEN];
    let base: [[u8; 3]; 8] = [
        [0, 0x20, 0],
        [0x08, 0x20, 0],
        [0x20, 0x20, 0],
        [0x20, 0, 0],
        [0x20, 0, 0x20],
        [0, 0, 0x20],
        [0, 0x20, 0x20],
        [0x20, 0x20, 0x20],
    ];
    for (i, c) in base.iter().enumerate() {
        d[i * 3..i * 3 + 3].copy_from_slice(c);
    }
    d
}

fn ramp() -> [u8; DATA_LEN] {
    core::array::from_fn(|i| i as u8)
}

#[test]
fn crc_check_value() {
    assert_eq!(crc16_ccitt_false(b"123456789"), 0x29B1);
}

/// Same frames as `rbarf_bench.py send --dry-run` prints (Python encoder in
/// src/bench/crc.py): the two encoders agree byte for byte.
#[test]
fn encoder_matches_python_bench() {
    let f = encode(&demo_static());
    assert_eq!(&f[..3], &[0xFF, 0xAA, 0x65]);
    assert_eq!(&f[51..57], &[0xAE, 0x1A, 0xAE, 0x1A, 0xAE, 0x1A]);
    assert_eq!(&f[57..], &[0x9A, 0x00, 0xFF]);
    let f = encode(&ramp());
    assert_eq!(&f[51..57], &[0x11, 0x6F, 0x11, 0x6F, 0x11, 0x6F]);
    assert_eq!(f.len(), 60);
    assert_eq!(FRAME_BITS, 480);
}

#[test]
fn nominal_round_trip() {
    for data in [demo_static(), ramp(), [0u8; DATA_LEN], [0xFF; DATA_LEN], [0xAA; DATA_LEN]] {
        let w = widths(&encode(&data), 18, 36);
        assert_eq!(decode_vec(&w), Ok((data, Vote::Unanimous)));
    }
}

#[test]
fn width_stats_per_class() {
    let w = widths(&encode(&ramp()), 18, 36);
    let mut st = WidthStats::EMPTY;
    decode(480, |i| w[i], &mut st).unwrap();
    assert_eq!(st, WidthStats { min0: 18, max0: 18, min1: 36, max1: 36 });
    let mut all = WidthStats::EMPTY;
    all.merge(&st);
    all.merge(&WidthStats { min0: 15, max0: 20, min1: 33, max1: 40 });
    assert_eq!(all, WidthStats { min0: 15, max0: 20, min1: 33, max1: 40 });
}

/// The threshold is exactly 27: 26 is a 0, 27 is a 1.
#[test]
fn threshold_edge() {
    let f = encode(&ramp());
    assert!(decode_vec(&widths(&f, 26, 27)).is_ok());
    assert!(decode_vec(&widths(&f, 0, 255)).is_ok());
    // 27 for a zero makes every 0 a 1: markers break.
    assert_eq!(decode_vec(&widths(&f, 27, 36)), Err(Reject::Marker));
    assert_eq!(decode_vec(&widths(&f, 18, 26)), Err(Reject::Marker));
}

/// 20 000 random payloads, every width jittered independently across the
/// worst-case envelope of the design doc §1.1 (±3 % clock, ±1 tick).
#[test]
fn random_payloads_with_jitter() {
    let mut r = Rng(0x1234_5678);
    for _ in 0..20_000 {
        let data: [u8; DATA_LEN] = core::array::from_fn(|_| r.next() as u8);
        let f = encode(&data);
        let w: Vec<u8> = widths(&f, 0, 1)
            .iter()
            .map(|&b| if b == 1 { r.range(33, 40) } else { r.range(15, 21) })
            .collect();
        assert_eq!(decode_vec(&w), Ok((data, Vote::Unanimous)));
    }
}

#[test]
fn length_errors() {
    let w = widths(&encode(&ramp()), 18, 36);
    assert_eq!(decode_vec(&w[..479]), Err(Reject::Short));
    assert_eq!(decode_vec(&[]), Err(Reject::Short));
    assert_eq!(decode_vec(&w[1..]), Err(Reject::Short)); // first bit lost
    let mut long = w.clone();
    long.push(18);
    assert_eq!(decode_vec(&long), Err(Reject::Long));
    let mut glitch = w.clone();
    glitch.insert(200, 3); // extra short pulse inside the frame
    assert_eq!(decode_vec(&glitch), Err(Reject::Long));
    // Large bursts (the ISR's n is mod 1024, but any n != 480 is rejected).
    let big = vec![18u8; 1023];
    assert_eq!(decode_vec(&big), Err(Reject::Long));
}

/// Two frames glued into one burst (latch gap too short) are 960 bits.
#[test]
fn glued_frames_rejected() {
    let f = encode(&ramp());
    let mut w = widths(&f, 18, 36);
    w.extend(widths(&f, 18, 36));
    assert_eq!(decode_vec(&w), Err(Reject::Long));
}

#[test]
fn bad_markers() {
    for pos in [0usize, 1, 2, 57, 58, 59] {
        let mut f = encode(&ramp());
        f[pos] ^= 0x10;
        assert_eq!(decode_vec(&widths(&f, 18, 36)), Err(Reject::Marker), "byte {pos}");
    }
}

/// Every single-bit error in the 480-bit frame: markers -> Marker, data ->
/// Crc, one check copy -> accepted by majority with the right data.
#[test]
fn every_single_bit_flip() {
    let data = demo_static();
    let good = encode(&data);
    for bit in 0..FRAME_BITS {
        let mut w = widths(&good, 18, 36);
        w[bit] = if w[bit] >= THRESHOLD { 18 } else { 36 };
        let byte = bit / 8;
        let got = decode_vec(&w);
        match byte {
            0..3 | 57..60 => assert_eq!(got, Err(Reject::Marker), "bit {bit}"),
            3..51 => assert_eq!(got, Err(Reject::Crc), "bit {bit}"),
            51..57 => assert_eq!(got, Ok((data, Vote::Majority)), "bit {bit}"),
            _ => unreachable!(),
        }
    }
}

/// Two-bit errors inside the data never pass (CRC16 HD >= 4 at this length).
#[test]
fn data_double_bit_flips_rejected() {
    let good = encode(&ramp());
    let base = widths(&good, 18, 36);
    for a in (24..408).step_by(7) {
        for b in (a + 1)..408 {
            let mut w = base.clone();
            for k in [a, b] {
                w[k] = if w[k] >= THRESHOLD { 18 } else { 36 };
            }
            assert_eq!(decode_vec(&w), Err(Reject::Crc), "bits {a},{b}");
        }
    }
}

fn with_check(data: &[u8; DATA_LEN], check: [u8; 6]) -> Vec<u8> {
    let mut f = encode(data);
    f[CHECK_AT..CHECK_AT + 6].copy_from_slice(&check);
    widths(&f, 18, 36)
}

#[test]
fn crc_majority_rules() {
    let data = ramp();
    let [h, l] = crc16_ccitt_false(&data).to_be_bytes();
    let (x, y) = (h ^ 0x5A, l ^ 0xC3);
    let ok_maj = Ok((data, Vote::Majority));
    // One whole bad copy: accepted (either position of the bad copy).
    assert_eq!(decode_vec(&with_check(&data, [x, y, h, l, h, l])), ok_maj);
    assert_eq!(decode_vec(&with_check(&data, [h, l, x, y, h, l])), ok_maj);
    assert_eq!(decode_vec(&with_check(&data, [h, l, h, l, x, y])), ok_maj);
    // Two copies bad in DIFFERENT byte positions: per-byte majority still
    // has two good votes each (PROTOCOL.md worked example): accepted.
    assert_eq!(decode_vec(&with_check(&data, [x, l, h, y, h, l])), ok_maj);
    // Two bad copies, same byte position, different values: no majority.
    assert_eq!(decode_vec(&with_check(&data, [x, l, x ^ 1, l, h, l])), Err(Reject::Crc));
    // Two bad copies agreeing on a wrong value: wrong majority.
    assert_eq!(decode_vec(&with_check(&data, [x, y, x, y, h, l])), Err(Reject::Crc));
    // Two whole bad copies, all different.
    assert_eq!(decode_vec(&with_check(&data, [x, y, x ^ 1, y ^ 1, h, l])), Err(Reject::Crc));
    // Three bad copies.
    assert_eq!(decode_vec(&with_check(&data, [x, y, x, y, x, y])), Err(Reject::Crc));
    // Unanimous control.
    assert_eq!(decode_vec(&with_check(&data, [h, l, h, l, h, l])), Ok((data, Vote::Unanimous)));
}

/// Wrong-but-consistent CRC (e.g. the CRC of other data) is rejected.
#[test]
fn foreign_crc_rejected() {
    let a = ramp();
    let b = demo_static();
    let [h, l] = crc16_ccitt_false(&b).to_be_bytes();
    assert_eq!(decode_vec(&with_check(&a, [h, l, h, l, h, l])), Err(Reject::Crc));
}

/// The ring is read through a closure; the receiver passes an index into a
/// circular buffer. A frame that wraps the ring end decodes the same.
#[test]
fn ring_wraparound() {
    const RING: usize = 1024;
    let data = demo_static();
    let w = widths(&encode(&data), 18, 36);
    let mut ring = [0u8; RING];
    let start = RING - 100;
    for (k, &x) in w.iter().enumerate() {
        ring[(start + k) % RING] = x;
    }
    let mut st = WidthStats::EMPTY;
    let got = decode(480, |i| ring[(start + i) & (RING - 1)], &mut st);
    assert_eq!(got, Ok((data, Vote::Unanimous)));
}

/// Garbage of exactly 480 widths never panics and essentially never passes.
#[test]
fn random_garbage() {
    let mut r = Rng(42);
    let mut accepted = 0;
    for _ in 0..50_000 {
        let w: Vec<u8> = (0..480).map(|_| r.next() as u8).collect();
        if decode_vec(&w).is_ok() {
            accepted += 1;
        }
    }
    assert_eq!(accepted, 0);
}
