//! Built-in demo frames (48-byte host frames, GRB) for the bench, cycled
//! every few seconds until a receiver exists. Colours are dim (0x20) on
//! purpose.

use rbarf_anim::FRAME_LEN;

/// Builds a frame: eight base colours (GRB) + `flags[0..24]`.
const fn frame(base: [[u8; 3]; 8], flags: [u8; 24]) -> [u8; FRAME_LEN] {
    let mut f = [0u8; FRAME_LEN];
    let mut i = 0;
    while i < 8 {
        f[i * 3] = base[i][0];
        f[i * 3 + 1] = base[i][1];
        f[i * 3 + 2] = base[i][2];
        i += 1;
    }
    let mut k = 0;
    while k < 24 {
        f[24 + k] = flags[k];
        k += 1;
    }
    f
}

/// `flags` with the given leading bytes, rest 0 (`flags[7..]` = 0xFF for
/// an empty/terminated sequence where relevant is set by the caller).
const fn flags(head: &[u8]) -> [u8; 24] {
    let mut f = [0u8; 24];
    let mut i = 0;
    while i < head.len() {
        f[i] = head[i];
        i += 1;
    }
    f
}

const D: u8 = 0x20; // dim

// GRB triples
const RED: [u8; 3] = [0, D, 0];
const GREEN: [u8; 3] = [D, 0, 0];
const BLUE: [u8; 3] = [0, 0, D];
const YELLOW: [u8; 3] = [D, D, 0];
const CYAN: [u8; 3] = [D, 0, D];
const MAGENTA: [u8; 3] = [0, D, D];
const WHITE: [u8; 3] = [D, D, D];
const ORANGE: [u8; 3] = [0x08, D, 0];

/// Mode 0x00: static rainbow.
pub const STATIC: [u8; FRAME_LEN] = frame(
    [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA, WHITE],
    flags(&[0x00]),
);

/// Mode 0x01: blink red <-> blue, 1 s cycle (20 x 50 ms). LED 0 masked to
/// white (mask bit 7 = LED 0, mask colour = flags[6..9]).
pub const BLINK: [u8; FRAME_LEN] = frame([RED; 8], flags(&[0x01, 20, 0x80, 0, 0, D, D, D, D]));

/// Mode 0x02: fade green <-> magenta, 2 s triangle (40 x 50 ms).
pub const FADE: [u8; FRAME_LEN] = frame([GREEN; 8], flags(&[0x02, 40, 0x00, 0, D, D]));

/// Mode 0x03 "spin" (host expansion of preset 0x04): sequence 01 57 62 FF,
/// 3-LED fading (feature bit 0), 0.8 s per revolution, background off.
pub const SPIN: [u8; FRAME_LEN] = frame(
    [WHITE; 8],
    flags(&[0x03, 16, 0x00, 0, 0, 0, 0x01, 0x01, 0x57, 0x62, 0xFF]),
);

/// Mode 0x03 spin with gamma on (flags[23] = 1) and brighter colours, to
/// see the LUT at work.
pub const SPIN_GAMMA: [u8; FRAME_LEN] = {
    let mut f = frame(
        [
            [0x80, 0, 0],
            [0x80, 0x40, 0],
            [0, 0x80, 0],
            [0, 0x80, 0x40],
            [0, 0, 0x80],
            [0x40, 0, 0x80],
            [0x80, 0, 0x80],
            [0x80, 0x80, 0x80],
        ],
        flags(&[0x03, 16, 0x00, 0, 0, 0, 0x01, 0x01, 0x57, 0x62, 0xFF]),
    );
    f[24 + 23] = 1;
    f
};

/// Demo playlist: (name, frame).
pub const DEMOS: [(&str, [u8; FRAME_LEN]); 5] = [
    ("static", STATIC),
    ("blink", BLINK),
    ("fade", FADE),
    ("spin", SPIN),
    ("spin+gamma", SPIN_GAMMA),
];
