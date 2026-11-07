//! RBARF v2.3 wire frame, receiver side: turn 480 measured WS2812 high
//! times into bits, then check the markers and the CRC16 check block.
//!
//! Frame (`docs/PROTOCOL.md`): `FF AA 65` + 48 data bytes + CRC16 x 3
//! (`HI LO HI LO HI LO`) + `9A 00 FF` = 60 bytes = 480 bits, MSB first.
//! CRC16 is CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection,
//! xorout 0) over the 48 data bytes only. The 48 data bytes are exactly the
//! `frame` input of `rbarf_anim::render`.
//!
//! Why this is so short compared to the v0.1 decoder (`src/reference/`):
//! the v0.2 receiver measures every bit's high time in hardware from that
//! bit's own rising edge (TIM3 PWM input, `docs/INPUT_CAPTURE_OPTIONS.md`
//! option 4a), so bits are exact. There is no sampling grid, no clock
//! calibration and no chase search; one fixed threshold decides each bit.
//!
//! Check-block policy: per-byte majority, STRICT (`PROTOCOL.md`'s
//! `allow_split_vote=False`, design doc §4.4 "at least two of the three").
//! For each byte position (HI, LO) at least two of the three copies must
//! agree, and that majority must equal the computed CRC byte. The split-vote
//! candidate enumeration of `PROTOCOL.md` exists to feed a chase decoder
//! with per-bit confidences; an exact receiver has neither, and accepting a
//! frame on one lone matching copy would only widen the false-accept window.
//!
//! `no_std`, no `unsafe`, no panics for any input. The ring access is a
//! closure so the firmware can read its DMA ring with volatile loads.

#![no_std]
#![forbid(unsafe_code)]

/// Data bytes per frame (= `rbarf_anim::FRAME_LEN`).
pub const DATA_LEN: usize = 48;
/// Bytes on the wire per frame.
pub const WIRE_LEN: usize = 60;
/// WS2812 bits per frame.
pub const FRAME_BITS: usize = WIRE_LEN * 8;
pub const HEADER: [u8; 3] = [0xFF, 0xAA, 0x65];
pub const TRAILER: [u8; 3] = [0x9A, 0x00, 0xFF];
/// Offset of the 6-byte check block in the wire frame.
pub const CHECK_AT: usize = HEADER.len() + DATA_LEN;

/// A measured high time >= this many 48 MHz timer ticks is a `1`
/// (27 ticks = 562.5 ns; bench transmitter: 0 = 375 ns = 18 ticks,
/// 1 = 750 ns = 36 ticks). See the design doc §1.1 for the margins.
pub const THRESHOLD: u8 = 27;

/// Why a burst was not accepted as a frame.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "defmt", derive(defmt::Format))]
pub enum Reject {
    /// Fewer than 480 high pulses before the latch gap.
    Short,
    /// More than 480 high pulses before the latch gap.
    Long,
    /// `FF AA 65` / `9A 00 FF` not where they belong.
    Marker,
    /// No per-byte majority in the check block, or it disagrees with the
    /// CRC16 of the data.
    Crc,
}

/// How the three check copies voted on an accepted frame.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Vote {
    /// All three copies equal the computed CRC.
    Unanimous,
    /// At least one copy differs in some byte; the per-byte majority still
    /// matched. On an exact receiver this means a bit error on the line.
    Majority,
}

/// Min / max measured width (ticks) per decoded class.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WidthStats {
    pub min0: u8,
    pub max0: u8,
    pub min1: u8,
    pub max1: u8,
}

impl WidthStats {
    /// Empty: min = 255, max = 0 (so `merge` works from it).
    pub const EMPTY: Self = Self { min0: u8::MAX, max0: 0, min1: u8::MAX, max1: 0 };

    #[inline]
    fn add(&mut self, w: u8) {
        if w >= THRESHOLD {
            self.min1 = self.min1.min(w);
            self.max1 = self.max1.max(w);
        } else {
            self.min0 = self.min0.min(w);
            self.max0 = self.max0.max(w);
        }
    }

    pub fn merge(&mut self, o: &Self) {
        self.min0 = self.min0.min(o.min0);
        self.max0 = self.max0.max(o.max0);
        self.min1 = self.min1.min(o.min1);
        self.max1 = self.max1.max(o.max1);
    }
}

impl Default for WidthStats {
    fn default() -> Self {
        Self::EMPTY
    }
}

/// Thresholds `FRAME_BITS` widths (`width(0)` = first bit on the wire) into
/// the 60 wire bytes, MSB first, and records min/max per class.
pub fn pack_bits(width: impl Fn(usize) -> u8, out: &mut [u8; WIRE_LEN], stats: &mut WidthStats) {
    let mut i = 0;
    for byte in out.iter_mut() {
        let mut v = 0u8;
        for _ in 0..8 {
            let w = width(i);
            stats.add(w);
            v = (v << 1) | (w >= THRESHOLD) as u8;
            i += 1;
        }
        *byte = v;
    }
}

/// CRC-16/CCITT-FALSE, bitwise (48 bytes = ~3 k cycles on the M0+; a table
/// would cost 512 B of flash for ~60 us saved per frame).
pub fn crc16_ccitt_false(data: &[u8]) -> u16 {
    let mut crc: u16 = 0xFFFF;
    for &b in data {
        crc ^= (b as u16) << 8;
        for _ in 0..8 {
            crc = if crc & 0x8000 != 0 { (crc << 1) ^ 0x1021 } else { crc << 1 };
        }
    }
    crc
}

/// The value at least two of the three votes share, if any.
fn majority(a: u8, b: u8, c: u8) -> Option<u8> {
    if a == b || a == c {
        Some(a)
    } else if b == c {
        Some(b)
    } else {
        None
    }
}

/// Checks markers and the check block of a packed wire frame. On success
/// the 48 data bytes are `wire[3..51]` (see [`data`]).
pub fn validate(wire: &[u8; WIRE_LEN]) -> Result<Vote, Reject> {
    if wire[..3] != HEADER || wire[WIRE_LEN - 3..] != TRAILER {
        return Err(Reject::Marker);
    }
    let crc = crc16_ccitt_false(&wire[HEADER.len()..CHECK_AT]);
    let c = &wire[CHECK_AT..CHECK_AT + 6];
    let hi = majority(c[0], c[2], c[4]).ok_or(Reject::Crc)?;
    let lo = majority(c[1], c[3], c[5]).ok_or(Reject::Crc)?;
    if (hi as u16) << 8 | lo as u16 != crc {
        return Err(Reject::Crc);
    }
    let [h, l] = crc.to_be_bytes();
    if c == [h, l, h, l, h, l] { Ok(Vote::Unanimous) } else { Ok(Vote::Majority) }
}

/// The data part of a wire frame.
pub fn data(wire: &[u8; WIRE_LEN]) -> [u8; DATA_LEN] {
    let mut d = [0u8; DATA_LEN];
    d.copy_from_slice(&wire[HEADER.len()..CHECK_AT]);
    d
}

/// The whole receive step for one burst of `n` measured widths: length
/// check, threshold + pack, markers, CRC majority. `width(i)` is only
/// called for `i < FRAME_BITS` and only when `n == FRAME_BITS`.
pub fn decode(
    n: usize,
    width: impl Fn(usize) -> u8,
    stats: &mut WidthStats,
) -> Result<([u8; DATA_LEN], Vote), Reject> {
    if n < FRAME_BITS {
        return Err(Reject::Short);
    }
    if n > FRAME_BITS {
        return Err(Reject::Long);
    }
    let mut wire = [0u8; WIRE_LEN];
    pack_bits(width, &mut wire, stats);
    let vote = validate(&wire)?;
    Ok((data(&wire), vote))
}

/// Builds the wire frame for `data` (transmitter side; used by the tests
/// and mirrored by `bench/rbarf_bench.py send`).
pub fn encode(data: &[u8; DATA_LEN]) -> [u8; WIRE_LEN] {
    let mut w = [0u8; WIRE_LEN];
    w[..3].copy_from_slice(&HEADER);
    w[3..CHECK_AT].copy_from_slice(data);
    let [h, l] = crc16_ccitt_false(data).to_be_bytes();
    w[CHECK_AT..CHECK_AT + 6].copy_from_slice(&[h, l, h, l, h, l]);
    w[WIRE_LEN - 3..].copy_from_slice(&TRAILER);
    w
}
