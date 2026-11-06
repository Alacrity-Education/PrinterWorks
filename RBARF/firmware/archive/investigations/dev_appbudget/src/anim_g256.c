#include "anim.h"
#include "ws2812_in.h"
#include "ws2812_out.h"

#if !(defined(CUT_GAMMA))
/* Gamma LUT: 4 curves (1.8, 2.2, 2.5, 2.8) x 256 entries, stored in flash */
static const uint8_t gamma_lut[256] = {
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
    0xDF, 0xE1, 0xE3, 0xE5, 0xE7, 0xEA, 0xEC, 0xEE, 0xF0, 0xF2, 0xF4, 0xF6, 0xF8, 0xFB, 0xFD, 0xFF
};
#endif

#if !(defined(CUT_AUTOSEQ) || defined(CUT_SEQ))
/* Sequence data for auto-fill modes (stored in flash) */
static const uint8_t seq_spin_fwd[] = {0x01, 0x57, 0x62, 0xFF};
static const uint8_t seq_spin_rev[] = {0x26, 0x75, 0x10, 0xFF};
static const uint8_t seq_rain_fwd[] = {0x34, 0x01, 0x57, 0x62, 0xFF};
static const uint8_t seq_rain_rev[] = {0x26, 0x75, 0x10, 0x43, 0xFF};
static const uint8_t seq_draw_fwd[] = {0x01, 0x23, 0x45, 0x67, 0xFF};
static const uint8_t seq_draw_rev[] = {0x76, 0x54, 0x32, 0x10, 0xFF};
#endif

#if !(defined(CUT_SEQ) && defined(CUT_FADE))
static uint8_t lerp(uint8_t x1, uint8_t x2, uint8_t m, uint8_t z)
{
    if (z == 0) return x2;
    return (uint8_t)(((uint16_t)x1 * m + (uint16_t)x2 * (z - m)) / z);
}
#endif

#if !(defined(CUT_SEQ))
static uint8_t get_seq_nib(const uint8_t *f, uint8_t idx)
{
    uint8_t v = f[7 + (idx >> 1)];
    return (idx & 1) ? (v & 0x0F) : (v >> 4);
}
#endif

#if !(defined(CUT_SEQ))
static uint8_t count_seq_len(const uint8_t *f)
{
    uint8_t len = 0;
    for (uint8_t i = 0; i < 32; i++) {
        if (get_seq_nib(f, i) > 8) break;
        len++;
    }
    return len;
}
#endif

#if !(defined(CUT_SEQ) && defined(CUT_FADE))
static void scale_phase(uint16_t phase, uint16_t dur, uint8_t *m, uint8_t *z)
{
    while (dur > 255) { dur >>= 1; phase >>= 1; }
    *z = dur ? (uint8_t)dur : 1;
    *m = (uint8_t)phase;
    if (*m > *z) *m = *z;
}
#endif

#if !(defined(CUT_AUTOSEQ) || defined(CUT_SEQ))
static void fill_seq_data(uint8_t *f, const uint8_t *data, uint8_t len)
{
    for (uint8_t i = 0; i < len; i++)
        f[7 + i] = data[i];
    f[0] = 0x03;
}
#endif

#if !(defined(CUT_SEQ))
static void add_clamp(uint8_t led, uint8_t g, uint8_t r, uint8_t b)
{
    uint8_t *p = ws2812_out_buf + led * 3;
    uint16_t s;
    s = (uint16_t)p[0] + g; p[0] = s > 255 ? 255 : (uint8_t)s;
    s = (uint16_t)p[1] + r; p[1] = s > 255 ? 255 : (uint8_t)s;
    s = (uint16_t)p[2] + b; p[2] = s > 255 ? 255 : (uint8_t)s;
}
#endif

static void anim_none(const uint8_t *base)
{
    for (uint8_t i = 0; i < WS2812_OUT_BUF_SIZE; i++)
        ws2812_out_buf[i] = base[i];
}

#if !(defined(CUT_BLINK) && defined(CUT_FADE))
static void apply_mask(const uint8_t *f)
{
    uint8_t mask = f[2];
    if (!mask) return;
    for (uint8_t i = 0; i < 8; i++) {
        if (mask & (0x80 >> i)) {
            ws2812_out_buf[i * 3]     = f[6];
            ws2812_out_buf[i * 3 + 1] = f[7];
            ws2812_out_buf[i * 3 + 2] = f[8];
        }
    }
}
#endif

#if !(defined(CUT_BLINK))
static void anim_blink(uint16_t now_ms, const uint8_t *base, const uint8_t *f)
{
    uint16_t cycle = (uint16_t)f[1] * 50;
    if (cycle == 0) { anim_none(base); return; }
    uint8_t first_half = (now_ms % cycle) < (cycle >> 1);
    for (uint8_t i = 0; i < WS2812_OUT_BUF_SIZE; i++)
        ws2812_out_buf[i] = first_half ? base[i] : f[3 + (i % 3)];
    apply_mask(f);
}
#endif

#if !(defined(CUT_FADE))
static void anim_fade(uint16_t now_ms, const uint8_t *base, const uint8_t *f)
{
    uint16_t cycle = (uint16_t)f[1] * 50;
    if (cycle == 0) { anim_none(base); return; }
    uint16_t half = cycle >> 1;
    if (half == 0) half = 1;
    uint16_t elapsed = now_ms % cycle;
    uint16_t phase = (elapsed < half) ? elapsed : (cycle - elapsed);

    uint8_t m, z;
    scale_phase(phase, half, &m, &z);

    for (uint8_t i = 0; i < WS2812_OUT_BUF_SIZE; i++)
        ws2812_out_buf[i] = lerp(f[3 + (i % 3)], base[i], m, z);
    apply_mask(f);
}
#endif

#if !(defined(CUT_SEQ))
static void anim_sequence(uint16_t now_ms, const uint8_t *base, const uint8_t *f)
{
    if (f[1] == 0) { anim_none(base); return; }

    uint8_t seq_len = count_seq_len(f);
    if (seq_len == 0) { anim_none(base); return; }

    uint8_t mask     = f[2];
    uint8_t features = f[6];
    uint8_t bg[3]    = {f[3], f[4], f[5]};

    uint16_t cycle_cs = (uint16_t)f[1] * 5;
    uint16_t elapsed_cs = (now_ms / 10) % cycle_cs;

    uint16_t step_dur = cycle_cs / seq_len;
    if (step_dur == 0) step_dur = 1;
    uint8_t step = (uint8_t)(elapsed_cs / step_dur);
    if (step >= seq_len) step = seq_len - 1;
    uint16_t phase = elapsed_cs - (uint16_t)step * step_dur;

    uint8_t m, z;
    scale_phase(phase, step_dur, &m, &z);

    uint8_t gsz = 1;
    if (features & 8)      gsz = 4;
    else if (features & 4) gsz = 2;

    /* fill background */
    for (uint8_t i = 0; i < 8; i++) {
        ws2812_out_buf[i * 3]     = bg[0];
        ws2812_out_buf[i * 3 + 1] = bg[1];
        ws2812_out_buf[i * 3 + 2] = bg[2];
    }

    uint8_t written = 0;

    if (features & 1) {
        /* 3-LED fading: current = full base, prev fades out, next fades in */
        for (uint8_t g = 0; g < gsz; g++) {
            uint8_t led = get_seq_nib(f, (step + g) % seq_len);
            if (led < 8) {
                ws2812_out_buf[led * 3]     = base[led * 3];
                ws2812_out_buf[led * 3 + 1] = base[led * 3 + 1];
                ws2812_out_buf[led * 3 + 2] = base[led * 3 + 2];
                written |= (1 << led);
            }
        }

        /* previous step: fading TO bg (m=0: base, m=z: bg) */
        {
            uint8_t prev = (step + seq_len - 1) % seq_len;
            uint8_t led  = get_seq_nib(f, prev);
            if (led < 8) {
                uint8_t vg = lerp(bg[0], base[led * 3],     m, z);
                uint8_t vr = lerp(bg[1], base[led * 3 + 1], m, z);
                uint8_t vb = lerp(bg[2], base[led * 3 + 2], m, z);
                if (written & (1 << led))
                    add_clamp(led, vg, vr, vb);
                else {
                    ws2812_out_buf[led * 3]     = vg;
                    ws2812_out_buf[led * 3 + 1] = vr;
                    ws2812_out_buf[led * 3 + 2] = vb;
                    written |= (1 << led);
                }
            }
        }

        /* next step: fading FROM bg (m=0: bg, m=z: base) */
        {
            uint8_t next = (step + gsz) % seq_len;
            uint8_t led  = get_seq_nib(f, next);
            if (led < 8) {
                uint8_t vg = lerp(base[led * 3],     bg[0], m, z);
                uint8_t vr = lerp(base[led * 3 + 1], bg[1], m, z);
                uint8_t vb = lerp(base[led * 3 + 2], bg[2], m, z);
                if (written & (1 << led))
                    add_clamp(led, vg, vr, vb);
                else {
                    ws2812_out_buf[led * 3]     = vg;
                    ws2812_out_buf[led * 3 + 1] = vr;
                    ws2812_out_buf[led * 3 + 2] = vb;
                    written |= (1 << led);
                }
            }
        }
    } else if (features & 2) {
        /* 2-LED fading: current fades in, previous fades out */
        for (uint8_t g = 0; g < gsz; g++) {
            uint8_t led = get_seq_nib(f, (step + g) % seq_len);
            if (led < 8) {
                ws2812_out_buf[led * 3]     = lerp(base[led * 3],     bg[0], m, z);
                ws2812_out_buf[led * 3 + 1] = lerp(base[led * 3 + 1], bg[1], m, z);
                ws2812_out_buf[led * 3 + 2] = lerp(base[led * 3 + 2], bg[2], m, z);
                written |= (1 << led);
            }
        }

        {
            uint8_t prev = (step + seq_len - 1) % seq_len;
            uint8_t led  = get_seq_nib(f, prev);
            if (led < 8) {
                uint8_t vg = lerp(bg[0], base[led * 3],     m, z);
                uint8_t vr = lerp(bg[1], base[led * 3 + 1], m, z);
                uint8_t vb = lerp(bg[2], base[led * 3 + 2], m, z);
                if (written & (1 << led))
                    add_clamp(led, vg, vr, vb);
                else {
                    ws2812_out_buf[led * 3]     = vg;
                    ws2812_out_buf[led * 3 + 1] = vr;
                    ws2812_out_buf[led * 3 + 2] = vb;
                    written |= (1 << led);
                }
            }
        }
    } else {
        /* no fading: solid group */
        for (uint8_t g = 0; g < gsz; g++) {
            uint8_t led = get_seq_nib(f, (step + g) % seq_len);
            if (led < 8) {
                ws2812_out_buf[led * 3]     = base[led * 3];
                ws2812_out_buf[led * 3 + 1] = base[led * 3 + 1];
                ws2812_out_buf[led * 3 + 2] = base[led * 3 + 2];
            }
        }
    }

    /* masked LEDs always show base color */
    for (uint8_t i = 0; i < 8; i++) {
        if (mask & (0x80 >> i)) {
            ws2812_out_buf[i * 3]     = base[i * 3];
            ws2812_out_buf[i * 3 + 1] = base[i * 3 + 1];
            ws2812_out_buf[i * 3 + 2] = base[i * 3 + 2];
        }
    }
}
#endif

#if !(defined(CUT_GAMMA))
static void apply_gamma(uint8_t cfg)
{
    if (cfg == 0) return;
        for (uint8_t i = 0; i < WS2812_OUT_BUF_SIZE; i++)
        ws2812_out_buf[i] = gamma_lut[ws2812_out_buf[i]];
}
#endif

void anim_render(uint16_t now_ms)
{
    uint8_t base[24];
    uint8_t f[24];

    for (uint8_t i = 0; i < 8; i++) {
        uint8_t src = (7 - i) * 3;
        uint8_t dst = i * 3;
        base[dst]     = ws2812_in_buf[src];
        base[dst + 1] = ws2812_in_buf[src + 1];
        base[dst + 2] = ws2812_in_buf[src + 2];
    }
    for (uint8_t i = 0; i < 24; i++)
        f[i] = ws2812_in_buf[24 + i];

    switch (f[0]) {
#if !(defined(CUT_BLINK))
    case 0x01: anim_blink(now_ms, base, f);    break;
#endif
#if !(defined(CUT_FADE))
    case 0x02: anim_fade(now_ms, base, f);     break;
#endif
#if !(defined(CUT_AUTOSEQ) || defined(CUT_SEQ))
    case 0x04: fill_seq_data(f, seq_spin_fwd, sizeof(seq_spin_fwd));
               anim_sequence(now_ms, base, f); break;
    case 0x05: fill_seq_data(f, seq_spin_rev, sizeof(seq_spin_rev));
               anim_sequence(now_ms, base, f); break;
    case 0x06: fill_seq_data(f, seq_rain_fwd, sizeof(seq_rain_fwd));
               anim_sequence(now_ms, base, f); break;
    case 0x07: fill_seq_data(f, seq_rain_rev, sizeof(seq_rain_rev));
               anim_sequence(now_ms, base, f); break;
    case 0x08: fill_seq_data(f, seq_draw_fwd, sizeof(seq_draw_fwd));
               anim_sequence(now_ms, base, f); break;
    case 0x09: fill_seq_data(f, seq_draw_rev, sizeof(seq_draw_rev));
               anim_sequence(now_ms, base, f); break;
#endif
#if !(defined(CUT_SEQ))
    case 0x03: anim_sequence(now_ms, base, f); break;
#endif
    default:   anim_none(base);                break;
    }

#if !(defined(CUT_GAMMA))
    apply_gamma(f[23]);
#endif

    for (uint8_t i = 0; i < 4; i++) {
        uint8_t lo = i * 3, hi = (7 - i) * 3, tmp;
        tmp = ws2812_out_buf[lo];     ws2812_out_buf[lo]     = ws2812_out_buf[hi];     ws2812_out_buf[hi]     = tmp;
        tmp = ws2812_out_buf[lo + 1]; ws2812_out_buf[lo + 1] = ws2812_out_buf[hi + 1]; ws2812_out_buf[hi + 1] = tmp;
        tmp = ws2812_out_buf[lo + 2]; ws2812_out_buf[lo + 2] = ws2812_out_buf[hi + 2]; ws2812_out_buf[hi + 2] = tmp;
    }
}
