//! Byte-for-byte parity of `rbarf_anim::render` against the original C
//! `anim_render` (src/app/anim.c, compiled by build.rs). Host only.
#![cfg(rbarf_c_ref)]

use rbarf_anim::{FRAME_LEN, OUT_LEN, render};

unsafe extern "C" {
    fn rbarf_c_anim_render(frame: *const u8, now_ms: u16, out: *mut u8);
}

/// The C engine works on global buffers; the test harness runs tests on
/// several threads, so every C call is serialised.
static C_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

fn c_render(frame: &[u8; FRAME_LEN], now_ms: u16) -> [u8; OUT_LEN] {
    let mut out = [0u8; OUT_LEN];
    let _guard = C_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // SAFETY: the shim reads 48 bytes from `frame` and writes 24 to `out`.
    unsafe { rbarf_c_anim_render(frame.as_ptr(), now_ms, out.as_mut_ptr()) };
    out
}

fn check(frame: &[u8; FRAME_LEN], now_ms: u16) {
    let want = c_render(frame, now_ms);
    let mut got = [0x5Au8; OUT_LEN];
    render(frame, now_ms, &mut got);
    assert_eq!(
        got, want,
        "mismatch: now_ms={now_ms} frame={frame:02X?}\n rust={got:02X?}\n    c={want:02X?}"
    );
}

/// SplitMix64 — tiny seeded PRNG, reproducible across runs.
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn byte(&mut self) -> u8 {
        self.next() as u8
    }
    fn fill(&mut self, b: &mut [u8]) {
        for x in b {
            *x = self.byte();
        }
    }
}

const MODES: core::ops::RangeInclusive<u8> = 0x00..=0x0A;
const DURATIONS: [u8; 7] = [0, 1, 2, 3, 7, 20, 255];
const MASKS: [u8; 5] = [0x00, 0x01, 0x80, 0xA5, 0xFF];
const GAMMAS: [u8; 6] = [0, 1, 2, 4, 5, 255];

/// Sequence payloads for flags[7..23] (16 bytes, the rest padded with 0xFF).
fn sequences() -> Vec<[u8; 16]> {
    let raw: &[&[u8]] = &[
        &[0x9F],                   // empty: first nibble >= 9
        &[0xFF],                   // empty
        &[0x3F],                   // single step
        &[0x8F],                   // single pause step
        &[0x01, 0x57, 0x62, 0xFF], // spin
        &[0x26, 0x75, 0x10, 0xFF], // spin rev
        &[0x34, 0x01, 0x57, 0x62, 0xFF],
        &[0x01, 0x2F],             // odd length (3)
        &[0x18, 0x28, 0x38, 0xFF], // nibble-8 pauses
        &[0x00, 0x11, 0x0F],       // repeated indices
        &[0x77, 0x7F],             // same LED everywhere
        &[0x05, 0xFF],             // two steps
        // 32 valid nibbles (no terminator inside flags[7..23])
        &[
            0x01, 0x23, 0x45, 0x67, 0x80, 0x12, 0x34, 0x56, 0x78, 0x76, 0x54, 0x32, 0x10, 0x88,
            0x07, 0x70,
        ],
        &[0x00; 16], // 32 x LED 0
        &[0x88; 16], // 32 x pause
    ];
    raw.iter()
        .map(|s| {
            let mut b = [0xFFu8; 16];
            b[..s.len()].copy_from_slice(s);
            b
        })
        .collect()
}

/// Times straddling every cycle/step/half boundary of the durations above,
/// plus the u16 wrap.
fn times() -> Vec<u16> {
    let mut t: Vec<u16> = vec![
        0, 1, 2, 5, 9, 10, 11, 65535, 65534, 65530, 65529, 65520, 32767, 32768,
    ];
    for d in DURATIONS {
        let cycle = d as u32 * 50;
        for k in [
            cycle / 4,
            cycle / 3,
            cycle / 2,
            cycle,
            cycle * 3 / 2,
            cycle * 7,
        ] {
            for delta in [-11i32, -1, 0, 1, 10] {
                let v = k as i32 + delta;
                if (0..=65535).contains(&v) {
                    t.push(v as u16);
                }
            }
        }
    }
    t.sort_unstable();
    t.dedup();
    t
}

#[test]
fn structured_sweep() {
    let mut rng = Rng(0x5242_4152_465F_7632); // "RBARF_v2"
    let seqs = sequences();
    let ts = times();

    // Base colour sets: extremes (sum+clamp, lerp edges) and random.
    let mut bases: Vec<[u8; 24]> = vec![[0xFF; 24], [0x00; 24]];
    let mut b = [0u8; 24];
    for (i, x) in b.iter_mut().enumerate() {
        *x = [0x00, 0x80, 0xFF, 0x7F, 0x01, 0xC0][i % 6];
    }
    bases.push(b);
    rng.fill(&mut b);
    bases.push(b);

    let mut cases = 0u64;
    for mode in MODES {
        for dur in DURATIONS {
            for mask in MASKS {
                for feat in 0u8..=15 {
                    for (si, seq) in seqs.iter().enumerate() {
                        // features and sequence only matter for mode 0x03 (and
                        // flags[6..9] = mask colour for blink/fade): full
                        // product there, a thinner slice elsewhere.
                        if mode != 0x03 && (feat % 5 != 0 || si % 4 != 0) {
                            continue;
                        }
                        for (gi, gamma) in GAMMAS.iter().enumerate() {
                            let base = &bases[(feat as usize + si + gi) % bases.len()];
                            let mut frame = [0u8; 48];
                            frame[..24].copy_from_slice(base);
                            frame[24] = mode;
                            frame[25] = dur;
                            frame[26] = mask;
                            rng.fill(&mut frame[27..30]); // alt / bg colour
                            frame[30] = feat;
                            frame[31..47].copy_from_slice(seq);
                            frame[47] = *gamma;
                            for &t in &ts {
                                check(&frame, t);
                                cases += 1;
                            }
                        }
                    }
                }
            }
        }
    }
    println!("structured sweep: {cases} cases, all byte-identical");
    assert!(cases > 100_000);
}

#[test]
fn random_frames() {
    const N: u64 = 400_000;
    let mut rng = Rng(0xC0FF_EE00_2026_1003);
    let mut frame = [0u8; 48];
    for i in 0..N {
        rng.fill(&mut frame);
        if i % 2 == 0 {
            // bias towards the implemented modes and gamma-on
            frame[24] = rng.byte() % 5;
            if i % 4 == 0 {
                frame[47] = rng.byte() % 6;
            }
            if i % 8 == 0 {
                frame[25] = rng.byte() % 8; // short cycles
            }
        }
        let t = rng.next() as u16;
        check(&frame, t);
    }
    println!("random: {N} cases, all byte-identical");
}
