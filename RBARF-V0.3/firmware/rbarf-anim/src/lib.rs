//! RBARF animation engine — a byte-exact `no_std` port of `src/app/anim.c`
//! (v2.1 production engine, tag `v0.1`).
//!
//! Input: the 48-byte decoded host frame (16 WS2812 LEDs, GRB). Bytes 0..24
//! are the eight base colours, bytes 24..48 are `flags[0..24]`
//! (see `docs/ANIMATION_PROTOCOL.md`). Output: the 24-byte GRB buffer for
//! the eight physical LEDs.
//!
//! Every quirk of the C engine is kept on purpose (the parity test in
//! `tests/parity.rs` compiles the original C and compares byte-for-byte):
//! base colours are copied LED 7..0 (reversed) and the result is mirrored
//! again at the end; blink/fade masked LEDs take `flags[6..9]`; nibble 8 is
//! a pause; the integer `lerp` returns `x2` when `z == 0`; `scale_phase`
//! truncates the phase to `u8` before clamping; `now_ms` is a wrapping
//! `u16` millisecond counter.
//!
//! No heap, no floats, and no panics for any input: every index is either a
//! constant range or guarded exactly like the C code (`led < 8`).

#![no_std]
#![forbid(unsafe_code)]

/// Size of the decoded host frame (16 LEDs x GRB).
pub const FRAME_LEN: usize = 48;
/// Size of the output buffer (8 LEDs x GRB).
pub const OUT_LEN: usize = 24;

/// Mode byte values understood by the engine (`flags[0]`). Anything else
/// renders the static base colours.
pub mod mode {
    pub const NONE: u8 = 0x00;
    pub const BLINK: u8 = 0x01;
    pub const FADE: u8 = 0x02;
    pub const SEQUENCE: u8 = 0x03;
}

/// Gamma 2.2 LUT — the single curve compiled into the v2.1 firmware
/// (placeholder pending the owner's final choice; identical to `anim.c`).
static GAMMA_LUT: [u8; 256] = [
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
    0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02,
    0x03, 0x03, 0x03, 0x03, 0x03, 0x04, 0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x05, 0x06, 0x06, 0x06,
    0x06, 0x07, 0x07, 0x07, 0x08, 0x08, 0x08, 0x09, 0x09, 0x09, 0x0A, 0x0A, 0x0B, 0x0B, 0x0B, 0x0C,
    0x0C, 0x0D, 0x0D, 0x0D, 0x0E, 0x0E, 0x0F, 0x0F, 0x10, 0x10, 0x11, 0x11, 0x12, 0x12, 0x13, 0x13,
    0x14, 0x14, 0x15, 0x16, 0x16, 0x17, 0x17, 0x18, 0x19, 0x19, 0x1A, 0x1A, 0x1B, 0x1C, 0x1C, 0x1D,
    0x1E, 0x1E, 0x1F, 0x20, 0x21, 0x21, 0x22, 0x23, 0x23, 0x24, 0x25, 0x26, 0x27, 0x27, 0x28, 0x29,
    0x2A, 0x2B, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
    0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
    0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x51, 0x52, 0x53, 0x54, 0x55, 0x57, 0x58, 0x59, 0x5A,
    0x5B, 0x5D, 0x5E, 0x5F, 0x61, 0x62, 0x63, 0x64, 0x66, 0x67, 0x69, 0x6A, 0x6B, 0x6D, 0x6E, 0x6F,
    0x71, 0x72, 0x74, 0x75, 0x77, 0x78, 0x79, 0x7B, 0x7C, 0x7E, 0x7F, 0x81, 0x82, 0x84, 0x85, 0x87,
    0x89, 0x8A, 0x8C, 0x8D, 0x8F, 0x91, 0x92, 0x94, 0x95, 0x97, 0x99, 0x9A, 0x9C, 0x9E, 0x9F, 0xA1,
    0xA3, 0xA5, 0xA6, 0xA8, 0xAA, 0xAC, 0xAD, 0xAF, 0xB1, 0xB3, 0xB5, 0xB6, 0xB8, 0xBA, 0xBC, 0xBE,
    0xC0, 0xC2, 0xC4, 0xC5, 0xC7, 0xC9, 0xCB, 0xCD, 0xCF, 0xD1, 0xD3, 0xD5, 0xD7, 0xD9, 0xDB, 0xDD,
    0xDF, 0xE1, 0xE3, 0xE5, 0xE7, 0xEA, 0xEC, 0xEE, 0xF0, 0xF2, 0xF4, 0xF6, 0xF8, 0xFB, 0xFD, 0xFF,
];

/// Blend position: the C code's global `lp_m` / `lp_z`, made explicit.
#[derive(Clone, Copy)]
struct Lp {
    m: u8,
    z: u8,
}

impl Lp {
    /// `lerp(x1, x2)` = `(x1*m + x2*(z-m)) / z`, or `x2` when `z == 0`.
    ///
    /// C evaluates this in `int` (at least 16 bits); `m <= z` holds on every
    /// call path (scale_phase clamps, blink uses 0/1 over 1), so the result
    /// fits `u16`. `u32` + wrapping keeps it panic-free even if not, with the
    /// same truncation to `u8` as the C cast.
    #[inline(always)]
    fn lerp(self, x1: u8, x2: u8) -> u8 {
        if self.z == 0 {
            return x2;
        }
        let a = (x1 as u32).wrapping_mul(self.m as u32);
        // C: (uint16_t)x2 * (lp_z - lp_m) — int arithmetic, may be negative
        // in theory; reproduced with two's-complement wrapping.
        let b = (x2 as i32).wrapping_mul(self.z as i32 - self.m as i32);
        let s = (a as i32).wrapping_add(b);
        (s / self.z as i32) as u8
    }
}

/// C `scale_phase`: shrink (phase, dur) until dur fits a byte; z = dur or 1;
/// m = (u8)phase clamped to z.
#[inline(always)]
fn scale_phase(mut phase: u16, mut dur: u16) -> Lp {
    while dur > 255 {
        dur >>= 1;
        phase >>= 1;
    }
    let z = if dur != 0 { dur as u8 } else { 1 };
    let mut m = phase as u8;
    if m > z {
        m = z;
    }
    Lp { m, z }
}

/// Sequence nibble `idx` (0..32): high nibble first, starting at `flags[7]`.
#[inline(always)]
fn seq_nib(f: &[u8; 24], idx: u8) -> u8 {
    // idx is always taken modulo a length <= 32, so 7 + idx/2 <= 22.
    let v = f[(7 + ((idx as usize & 31) >> 1)) % 24];
    if idx & 1 != 0 { v & 0x0F } else { v >> 4 }
}

fn count_seq_len(f: &[u8; 24]) -> u8 {
    let mut len = 0;
    for i in 0..32u8 {
        if seq_nib(f, i) > 8 {
            break;
        }
        len += 1;
    }
    len
}

#[inline(always)]
fn put3(out: &mut [u8; OUT_LEN], led: usize, v: [u8; 3]) {
    let p = led * 3;
    out[p] = v[0];
    out[p + 1] = v[1];
    out[p + 2] = v[2];
}

#[inline(always)]
fn get3(buf: &[u8; OUT_LEN], led: usize) -> [u8; 3] {
    let p = led * 3;
    [buf[p], buf[p + 1], buf[p + 2]]
}

/// C `seq_put`: write, or sum+clamp if this LED was already written.
fn seq_put(out: &mut [u8; OUT_LEN], led: u8, v: [u8; 3], written: u8) -> u8 {
    let bit = 1u8 << (led & 7);
    let l = (led & 7) as usize;
    if written & bit != 0 {
        let p = get3(out, l);
        put3(
            out,
            l,
            [
                p[0].saturating_add(v[0]),
                p[1].saturating_add(v[1]),
                p[2].saturating_add(v[2]),
            ],
        );
    } else {
        put3(out, l, v);
    }
    written | bit
}

/// C `seq_edge`: dir=false = previous step fading out, dir=true = next step
/// fading in.
fn seq_edge(
    out: &mut [u8; OUT_LEN],
    lp: Lp,
    base: &[u8; OUT_LEN],
    bg: [u8; 3],
    led: u8,
    dir: bool,
    written: u8,
) -> u8 {
    let b = get3(base, (led & 7) as usize);
    let mut v = [0u8; 3];
    for c in 0..3 {
        v[c] = if dir {
            lp.lerp(b[c], bg[c])
        } else {
            lp.lerp(bg[c], b[c])
        };
    }
    seq_put(out, led, v, written)
}

fn anim_none(out: &mut [u8; OUT_LEN], base: &[u8; OUT_LEN]) {
    *out = *base;
}

/// Blink/fade mask overlay: bit 7 = LED 0; masked LEDs take `flags[6..9]`.
fn apply_mask(out: &mut [u8; OUT_LEN], f: &[u8; 24]) {
    let mask = f[2];
    for led in 0..8 {
        if mask & (0x80 >> led) != 0 {
            put3(out, led, [f[6], f[7], f[8]]);
        }
    }
}

fn anim_blend(out: &mut [u8; OUT_LEN], lp: Lp, base: &[u8; OUT_LEN], f: &[u8; 24]) {
    for i in 0..OUT_LEN {
        out[i] = lp.lerp(f[3 + i % 3], base[i]);
    }
    apply_mask(out, f);
}

fn anim_blink(out: &mut [u8; OUT_LEN], now_ms: u16, base: &[u8; OUT_LEN], f: &[u8; 24]) {
    let cycle = f[1] as u16 * 50;
    if cycle == 0 {
        anim_none(out, base);
        return;
    }
    let m = if now_ms % cycle < (cycle >> 1) { 0 } else { 1 };
    anim_blend(out, Lp { m, z: 1 }, base, f);
}

fn anim_fade(out: &mut [u8; OUT_LEN], now_ms: u16, base: &[u8; OUT_LEN], f: &[u8; 24]) {
    let cycle = f[1] as u16 * 50;
    if cycle == 0 {
        anim_none(out, base);
        return;
    }
    let mut half = cycle >> 1;
    if half == 0 {
        half = 1;
    }
    let elapsed = now_ms % cycle;
    let phase = if elapsed < half {
        elapsed
    } else {
        cycle.wrapping_sub(elapsed)
    };
    anim_blend(out, scale_phase(phase, half), base, f);
}

fn anim_sequence(out: &mut [u8; OUT_LEN], now_ms: u16, base: &[u8; OUT_LEN], f: &[u8; 24]) {
    if f[1] == 0 {
        anim_none(out, base);
        return;
    }
    let seq_len = count_seq_len(f);
    if seq_len == 0 {
        anim_none(out, base);
        return;
    }

    let mask = f[2];
    let features = f[6];
    let bg = [f[3], f[4], f[5]];

    let cycle_cs = f[1] as u16 * 5;
    let elapsed_cs = (now_ms / 10) % cycle_cs;

    let mut step_dur = cycle_cs / seq_len as u16;
    if step_dur == 0 {
        step_dur = 1;
    }
    let mut step = (elapsed_cs / step_dur) as u8;
    if step >= seq_len {
        step = seq_len - 1;
    }
    let phase = elapsed_cs.wrapping_sub((step as u16).wrapping_mul(step_dur));
    let lp = scale_phase(phase, step_dur);

    let gsz: u8 = if features & 8 != 0 {
        4
    } else if features & 4 != 0 {
        2
    } else {
        1
    };

    // fill background
    for i in 0..OUT_LEN {
        out[i] = bg[i % 3];
    }

    let fade = features & 3 != 0;
    let fade3 = features & 1 != 0;
    let mut written: u8 = 0;

    for g in 0..gsz {
        // step < seq_len <= 32 and g < 4: no u8 overflow.
        let led = seq_nib(f, (step + g) % seq_len);
        if led < 8 {
            let b = get3(base, led as usize);
            let v = if fade3 || !fade {
                b
            } else {
                [
                    lp.lerp(b[0], bg[0]),
                    lp.lerp(b[1], bg[1]),
                    lp.lerp(b[2], bg[2]),
                ]
            };
            put3(out, led as usize, v);
            written |= 1 << led;
        }
    }

    if fade {
        let led = seq_nib(f, (step + seq_len - 1) % seq_len);
        if led < 8 {
            written = seq_edge(out, lp, base, bg, led, false, written);
        }
        if fade3 {
            let led = seq_nib(f, (step + gsz) % seq_len);
            if led < 8 {
                seq_edge(out, lp, base, bg, led, true, written);
            }
        }
    }

    // masked LEDs always show base colour
    for led in 0..8 {
        if mask & (0x80 >> led) != 0 {
            put3(out, led, get3(base, led));
        }
    }
}

fn apply_gamma(out: &mut [u8; OUT_LEN], cfg: u8) {
    if cfg == 0 || cfg > 4 {
        return;
    }
    for v in out.iter_mut() {
        *v = GAMMA_LUT[*v as usize];
    }
}

/// Render one animation frame — the Rust equivalent of C `anim_render`.
///
/// `frame` is the 48-byte decoded host frame, `now_ms` the wrapping 16-bit
/// millisecond clock, `out` receives the 24 GRB bytes for LEDs 0..8 in wire
/// order.
pub fn render(frame: &[u8; FRAME_LEN], now_ms: u16, out: &mut [u8; OUT_LEN]) {
    let mut f = [0u8; 24];
    f.copy_from_slice(&frame[24..48]);

    // base colours copied LED 7 .. LED 0 (reversed), as in the C code
    let mut base = [0u8; OUT_LEN];
    for i in 0..8 {
        let s = (7 - i) * 3;
        base[i * 3..i * 3 + 3].copy_from_slice(&frame[s..s + 3]);
    }

    match f[0] {
        mode::BLINK => anim_blink(out, now_ms, &base, &f),
        mode::FADE => anim_fade(out, now_ms, &base, &f),
        mode::SEQUENCE => anim_sequence(out, now_ms, &base, &f),
        _ => anim_none(out, &base),
    }

    apply_gamma(out, f[23]);

    // mirror the LED order back (swap LED i with LED 7-i)
    for i in 0..4 {
        let lo = get3(out, i);
        let hi = get3(out, 7 - i);
        put3(out, i, hi);
        put3(out, 7 - i, lo);
    }
}
