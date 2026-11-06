/*
 * decoder.c -- C port of approaches/embedded_ref.py (final config:
 * SELF_TRAIN off, FAM_OFFSETS off -- both measured zero accuracy value).
 *
 * Compiles for both the host (gcc, for bit-exact parity testing against
 * the Python reference via ctypes) and the STM8S001J3 (sdcc -mstm8,
 * for MEASURED flash size, RAM size, and simulated cycle counts).
 *
 * Input is the RAW capture buffer in cap_code.s byte layout (bit7/6 =
 * BS0/BS1 of the previous loop, bits5..0 = R0..R5 of this loop); the
 * linearization is done inline while streaming -- exactly what the
 * production firmware would do.
 *
 * Fixed-point formats (TU = 1250/512 ns = 2.44 ns):
 *   t (receiver time)   u16  CPU cycles
 *   K (clock scale)     u16  Q11 TU/cycle (nominal 52429)
 *   t*K                 u32  <= 27.5k * 60000 < 2^31      ** 32-bit **
 *   y (mapped time)     u32  TU (production frame end ~230k)
 *   tau                 s16  TU
 *   u, v, h*, theta     s16  TU (pulse-relative)
 *   Se / Sy sums        s32/u32                            ** 32-bit **
 *
 * All state is in static globals so the linker map MEASURES the RAM
 * working set.  NB_PAYLOAD selects the frame size (16 = dataset,
 * 48 = production).
 */

#include <stdint.h>

#ifndef NB_PAYLOAD
#define NB_PAYLOAD 16
#endif
#define NB   (8 * (8 + NB_PAYLOAD))
#define NBB  (NB / 8)

/* ---- fitted sampler model (integer cycles) --------------------------- */
static const uint8_t O_CY[8] = {0, 4, 9, 13, 17, 21, 27, 32};
static const int8_t  W_CY[8] = {0, -1, 0, 2, 0, 0, 0, 1};

#define LOOP_CY   40
#define BIT_SH    9
#define BIT_U     512
#define BIT_H     256
#define BIAS_U    512
#define TAIL_U    164
#define H0P       154
#define H1P       308
#define KQ        11
#define K_MIN     46000u
#define K_MAX     60000u
#define FIRST_BR  4
#define LATCH_RUN 200

#define INFEAS_U  160
#define LAB_MIN   3
#define LAB_OUT   246
#define H0_LO 112
#define H0_HI 192
#define H1_LO 252
#define H1_HI 376
#define SEP_LO 112
#define SEP_HI 196
#define CONF_M 16
#define KNIFE_M 24
#define DEAD_VOTE_MIN 3
#define KNIFE_PAIR_MIN 40
#define KNIFE_AGREE_PCT 99
#define KNIFE_MAX 32
#define RESOLVED_MAX 16
#define GATE_INFEAS 4
#define GATE_LABERR 6
#define A_CAP 15                /* hypothesis cap; measured max span 2 */

#define EPS_ZONE 32
#define EPS_HIST 64
#define EPS_GAP_MIN 5
#define EPS_CLAMP56 24
#define EPS_CLEAR1 18
#define EPS_TOPM 3
#define EPS_SLACK 2
#define EPS_SLACK1 8

static const uint8_t HDR[4] = {0xFF, 0x00, 0xAA, 0x65};
static const uint8_t TRL[4] = {0x9A, 0x55, 0x00, 0xFF};

/* KNOWN frame template: -1 unknown, 0/1 marker bits */
static int8_t known_bit(uint16_t t)
{
    if (t < 32)
        return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
    if (t >= NB - 32) {
        uint16_t u = t - (NB - 32);
        return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
    }
    return -1;
}

/* ---- pulse stream (linearize + model clock + run detection) ---------- */

typedef struct {
    uint16_t ra, rb, fa, fb;    /* brackets, receiver cycles */
    uint8_t sfa;                /* slot of last high sample (family id) */
} Pulse;

typedef struct {
    const uint8_t *cap;
    uint16_t ncap;
    uint16_t i;                 /* loop index */
    uint8_t s;                  /* slot 0..7 */
    uint16_t tbase;             /* i * LOOP_CY */
    int16_t wsum;
    uint16_t t_prev;
    uint8_t have_prev;
    uint8_t in_pulse, seen, done;
    uint16_t low_run;
    uint16_t ra, rb, fa;
    uint8_t sfa;
} PStream;

static void ps_init(PStream *p, const uint8_t *cap, uint16_t ncap)
{
    p->cap = cap; p->ncap = ncap;
    p->i = 0; p->s = 0; p->tbase = 0; p->wsum = 0;
    p->t_prev = 0; p->have_prev = 0;
    p->in_pulse = 0; p->seen = 0; p->done = 0; p->low_run = 0;
    p->ra = p->rb = p->fa = 0; p->sfa = 0;
}

/* next pulse; returns 1 and fills *out, or 0 at stream end */
static uint8_t ps_next(PStream *p, Pulse *out)
{
    while (!p->done) {
        uint8_t v, s = p->s;
        uint16_t t;
        if (p->i >= p->ncap) break;
        if (s == 6 && p->i + 1 < p->ncap) {
            uint8_t bt = p->cap[p->i + 1];
            if (bt == 0x00 && !p->in_pulse) {
                p->t_prev = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum);
                p->have_prev = 1;
                p->low_run = (uint16_t)(p->low_run + 8);
                p->i++; p->tbase += LOOP_CY;    /* s stays 6 */
                if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
                continue;
            }
            if (bt == 0xFF && p->in_pulse) {
                p->fa = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum + 2);
                p->wsum += 2;                   /* sum of W over the octet */
                p->sfa = 5;
                p->low_run = 0;
                p->seen = 1;
                p->t_prev = p->fa;
                p->have_prev = 1;
                p->i++; p->tbase += LOOP_CY;
                continue;
            }
        }
        if (s < 6) {
            v = (uint8_t)((p->cap[p->i] >> (5 - s)) & 1);
        } else {
            if (p->i + 1 >= p->ncap) {      /* last loop: BS lost */
                p->i++; p->s = 0; p->tbase += LOOP_CY;
                continue;
            }
            v = (uint8_t)((p->cap[p->i + 1] >> (7 - (s - 6))) & 1);
        }
        t = (uint16_t)(p->tbase + O_CY[s] + p->wsum);
        /* advance slot cursor now so early returns keep state */
        if (s == 7) { p->s = 0; p->i++; p->tbase += LOOP_CY; }
        else        { p->s = (uint8_t)(s + 1); }
        if (v) {
            p->wsum += W_CY[s];
            if (!p->in_pulse) {
                p->in_pulse = 1;
                p->ra = p->have_prev ? p->t_prev
                                     : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
                p->rb = t;
            }
            p->fa = t;
            p->sfa = s;
            p->low_run = 0;
            p->seen = 1;
        } else {
            if (p->in_pulse) {
                p->in_pulse = 0;
                out->ra = p->ra; out->rb = p->rb;
                out->fa = p->fa; out->fb = t; out->sfa = p->sfa;
                p->t_prev = t; p->have_prev = 1;
                p->low_run = 1;
                return 1;
            }
            p->low_run++;
            if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
        }
        p->t_prev = t;
        p->have_prev = 1;
    }
    if (p->in_pulse) {                       /* capture ended high */
        p->in_pulse = 0;
        out->ra = p->ra; out->rb = p->rb;
        out->fa = p->fa; out->fb = (uint16_t)(p->fa + FIRST_BR);
        out->sfa = p->sfa;
        return 1;
    }
    p->done = 1;
    return 0;
}

/* ---- decoder state (static: the map file measures this) -------------- */

static uint16_t g_K;
static int16_t g_tau;

/* calibration */
static int16_t c_lo0, c_hi0, c_lo1, c_hi1;
static uint8_t c_n0, c_n1;
static int16_t c_h0c, c_h1c;
static int8_t  c_d56[2];                    /* boundary shift, fams 5,6 */
static uint8_t c_hist[2][64];
static int16_t c_labx0[2], c_labx1[2], c_labx0b[2], c_labx1b[2];
static int16_t c_c0[2];
static int16_t c_gap56[2];

/* decision */
static uint8_t d_bits[NBB], d_conf[NBB], d_tied[NBB];
static uint16_t d_knife[KNIFE_MAX];
static uint8_t d_nknife;
static uint16_t d_resolved[RESOLVED_MAX];
static uint8_t d_nres;
static uint8_t d_infeas, d_laberr;
static uint16_t d_nseg;
static uint16_t d_costs[A_CAP + 1];
static uint16_t d_inter;                    /* bitmask over a */

#define BGET(arr, t)  ((arr[(t) >> 3] >> ((t) & 7)) & 1)
#define BSET(arr, t)  (arr[(t) >> 3] |= (uint8_t)(1u << ((t) & 7)))
#define BCLR(arr, t)  (arr[(t) >> 3] &= (uint8_t)~(1u << ((t) & 7)))

static uint32_t map_y(uint16_t t)
{
    return (uint32_t)((uint32_t)t * g_K >> KQ) + (uint32_t)(int32_t)g_tau;
    /* tau >= 0 always by construction (seed anchors bit 0 at BIAS_U) */
}

/* ---- P1: endpoint seed ------------------------------------------------ */

static uint8_t seed(const uint8_t *cap, uint16_t ncap)
{
    PStream ps;
    Pulse p;
    uint16_t np = 0;
    uint16_t r0m = 0, flm = 0;
    uint32_t Wu, K;
    ps_init(&ps, cap, ncap);
    while (ps_next(&ps, &p)) {
        if (np == 0) r0m = (uint16_t)((p.ra + p.rb) >> 1);
        flm = (uint16_t)((p.fa + p.fb) >> 1);
        np++;
    }
    if (np < 8 || flm <= r0m) return 0;
    Wu = (uint32_t)(NB - 1) * BIT_U + H1P;
    K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
    if (K < K_MIN || K > K_MAX) return 0;
    g_K = (uint16_t)K;
    g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
    return 1;
}

/* ---- P2: residual-regression refinement (x2) -------------------------- */

static void refine(const uint8_t *cap, uint16_t ncap)
{
    PStream ps;
    Pulse p;
    uint32_t y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
    uint32_t mid_u = (uint32_t)BIAS_U + (uint32_t)(NB / 2) * BIT_U;
    uint16_t n_lo = 0, n_hi = 0;
    int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
    uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
    int32_t me_lo, me_hi, me, dk, dtau;
    uint32_t my_lo, my_hi, my;
    int32_t de, dy;
    ps_init(&ps, cap, ncap);
    while (ps_next(&ps, &p)) {
        uint32_t y, q;
        int16_t e;
        y = map_y((uint16_t)((p.ra + p.rb) >> 1));
        if (y > y_end) break;
        q = (y + BIT_H) >> BIT_SH;
        e = (int16_t)((int32_t)y - (int32_t)(q << BIT_SH));
        if (y < mid_u) { n_lo++; se_lo += e; sy_lo += y; }
        else           { n_hi++; se_hi += e; sy_hi += y; }
    }
    if (n_lo < 2 || n_hi < 2) return;
    me_lo = se_lo / (int32_t)n_lo;
    me_hi = se_hi / (int32_t)n_hi;
    my_lo = sy_lo / n_lo;
    my_hi = sy_hi / n_hi;
    de = me_hi - me_lo;
    dy = (int32_t)my_hi - (int32_t)my_lo;
    if (dy <= 0) return;
    dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
    me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
    my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
    dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
    if ((uint32_t)((int32_t)g_K - dk) < K_MIN ||
        (uint32_t)((int32_t)g_K - dk) > K_MAX) return;
    g_K = (uint16_t)((int32_t)g_K - dk);
    g_tau = (int16_t)(g_tau + dtau);
}

/* ---- segment stream (gap accounting) ----------------------------------
 * Iterator over (k0, k1, u, v, fam) with same-bit merging.
 */
typedef struct {
    PStream ps;
    uint32_t y_end;
    uint32_t y_prev;
    uint8_t have_y;
    uint16_t n;
    /* pending segment */
    uint8_t pend;
    uint16_t p_k0;
    int16_t p_u, p_v;
    uint8_t p_fam;
    uint8_t src_done;
} SStream;

typedef struct {
    uint16_t k0, k1;
    int16_t u, v;
    uint8_t fam;
} Seg;

static void ss_init(SStream *s, const uint8_t *cap, uint16_t ncap)
{
    ps_init(&s->ps, cap, ncap);
    s->y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
    s->y_prev = 0; s->have_y = 0; s->n = 0;
    s->pend = 0; s->src_done = 0;
    s->p_k0 = 0; s->p_u = 0; s->p_v = 0; s->p_fam = 0;
}

static uint8_t ss_next(SStream *s, Seg *out)
{
    Pulse p;
    while (!s->src_done) {
        uint32_t y, yfa, yfb, base;
        int32_t d;
        int16_t dn;
        if (!ps_next(&s->ps, &p)) { s->src_done = 1; break; }
        y = map_y((uint16_t)((p.ra + p.rb) >> 1));
        if (y > s->y_end) { s->src_done = 1; break; }
        if (!s->have_y) { s->n = 0; s->have_y = 1; }
        else {
            d = (int32_t)y - (int32_t)s->y_prev;
            dn = (int16_t)((d + BIT_H) >> BIT_SH);
            if (dn > 0) s->n = (uint16_t)(s->n + dn);
        }
        s->y_prev = y;
        yfa = map_y(p.fa);
        yfb = map_y(p.fb);
        if (s->pend && s->n == s->p_k0) {            /* spurious split */
            base = (uint32_t)BIAS_U + (uint32_t)s->p_k0 * BIT_U;
            s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
            s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
            s->p_fam = p.sfa;
            continue;
        }
        if (s->pend) {
            out->k0 = s->p_k0;
            out->k1 = (s->n < NB) ? s->n : NB;
            out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
            /* stage the new pulse as pending */
            if (s->n >= NB) { s->pend = 0; s->src_done = 1; return 1; }
            base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
            s->p_k0 = s->n;
            s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
            s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
            s->p_fam = p.sfa;
            return 1;
        }
        if (s->n >= NB) { s->src_done = 1; break; }
        base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
        s->pend = 1;
        s->p_k0 = s->n;
        s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
        s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
        s->p_fam = p.sfa;
    }
    if (s->pend) {
        s->pend = 0;
        out->k0 = s->p_k0; out->k1 = NB;
        out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
        return 1;
    }
    return 0;
}

/* ---- marker constraints ----------------------------------------------- */

static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
{
    uint16_t t, e = (k1 < NB) ? k1 : NB;
    *amin = 0;
    *amax = (int16_t)(k1 - k0);
    for (t = k0; t < e; t++) {
        int8_t kb = known_bit(t);
        if (kb == 1) {
            int16_t m = (int16_t)(t - k0 + 1);
            if (m > *amin) *amin = m;
        } else if (kb == 0) {
            int16_t m = (int16_t)(t - k0);
            if (m < *amax) *amax = m;
        }
    }
}

/* ---- P3: calibration --------------------------------------------------- */

/* label -> (cls, lo, hi); returns cls or -1 */
static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                             int16_t a, int16_t *lo, int16_t *hi)
{
    int16_t L = (int16_t)(k1 - k0);
    int16_t mid, d0, d1, off;
    if (a == 0) { *lo = u; *hi = v; return 0; }
    if (a == L) {
        off = (int16_t)((L - 1) * BIT_U);
        *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
        return 1;
    }
    mid = (int16_t)((u + v) >> 1);
    d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
    if (d1 < 0) d1 = (int16_t)-d1;
    d0 = (int16_t)(mid - (a * BIT_U + H0P));
    if (d0 < 0) d0 = (int16_t)-d0;
    if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
    if (d1 <= d0) {
        off = (int16_t)((a - 1) * BIT_U);
        *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
        return 1;
    }
    off = (int16_t)(a * BIT_U);
    *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
    return 0;
}

static void cal_cloud(int16_t u, uint8_t fam)
{
    int16_t d, x;
    uint8_t f;
    if (fam != 5 && fam != 6) return;
    if (u < 0) return;
    f = (uint8_t)(fam - 5);
    x = (int16_t)(u & (BIT_U - 1));
    d = (int16_t)(x - c_c0[f]);
    if (d >= -EPS_HIST && d < EPS_HIST) {
        uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
        if (c_hist[f][b] < 255) c_hist[f][b]++;
    }
}

static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                    uint8_t fam, int16_t a)
{
    int16_t lo, hi;
    int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
    if (cls < 0) return;
    if (cls == 0) {
        if (lo > c_lo0) c_lo0 = lo;
        if (hi < c_hi0) c_hi0 = hi;
        if (c_n0 < 255) c_n0++;
    } else {
        if (lo > c_lo1) c_lo1 = lo;
        if (hi < c_hi1) c_hi1 = hi;
        if (c_n1 < 255) c_n1++;
    }
    if ((fam == 5 || fam == 6) && lo >= 0) {
        uint8_t f = (uint8_t)(fam - 5);
        int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
        if (d >= -EPS_HIST && d < EPS_HIST) {
            if (cls == 0) {
                if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
                else if (d > c_labx0b[f]) c_labx0b[f] = d;
            } else {
                if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
                else if (d < c_labx1b[f]) c_labx1b[f] = d;
            }
        }
    }
}

/* largest label-feasible density gap (or clamp) in fold coordinate d */
static uint8_t theta56(uint8_t f, int16_t *theta_out)
{
    int16_t x0 = c_labx0[f], x1 = c_labx1[f];
    uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
    int16_t zlo = (int16_t)(x0 + 1);
    int16_t zhi = x1;
    int16_t theta = 0;
    uint8_t have_theta = 0;
    int16_t top = 0;
    uint8_t have_top = 0, clear1 = 0;
    uint8_t b;
    if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
    if (zhi > EPS_ZONE) zhi = EPS_ZONE;
    if (zlo < zhi) {
        uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
        uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
        /* build sentinel+points sequence on the fly, track largest gap */
        int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
        uint8_t nocc = 0;
        for (b = blo; b <= bhi; b++) {
            if (c_hist[f][b]) {
                int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
                int16_t gp = (int16_t)(x - prev);
                if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
                prev = x;
                nocc++;
            }
        }
        {
            int16_t gp = (int16_t)(zhi - prev);
            if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
        }
        if (nocc == 0) {
            if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
        } else {
            uint8_t ok = (bg >= EPS_GAP_MIN);
            if (ok && (uint8_t)(nocc + 1) >= 4) {
                /* sweep guard: 2*bg*(ngaps) >= 5*span */
                if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
                    ok = 0;
            }
            if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
        }
    }
    if (has0 || has1) {
        int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
        if (has0) {
            wlo = (int16_t)(x0 - EPS_SLACK1);
            if (c_labx0b[f] > -0x4000 &&
                (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
                wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
        }
        if (has1) {
            whi = (int16_t)(x1 + EPS_SLACK1);
            if (c_labx1b[f] < 0x3FFF &&
                (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
                whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
        }
        if (wlo > whi) {
            theta = (int16_t)((wlo + whi) >> 1);
            have_theta = 1;
        } else {
            int16_t th = have_theta ? theta : 0;
            if (th < wlo) th = wlo;
            if (th > whi) th = whi;
            theta = th;
            have_theta = 1;
        }
    }
    for (b = 0; b < 64; b++) {
        int16_t d;
        if (!c_hist[f][b]) continue;
        d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
        if (d > EPS_CLEAR1) clear1 = 1;
        else if (d > -EPS_CLAMP56) {
            if (!have_top || d > top) top = d;
            have_top = 1;
        }
    }
    if (!clear1 && have_top) {
        int16_t floor_ = (int16_t)(top + EPS_TOPM);
        if (!have_theta || floor_ > theta) theta = floor_;
        have_theta = 1;
        if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
            theta > (int16_t)(x1 + EPS_SLACK))
            theta = (int16_t)(x1 + EPS_SLACK);
    }
    *theta_out = theta;
    return have_theta;
}

static void calibrate(const uint8_t *cap, uint16_t ncap)
{
    SStream ss;
    Seg sg;
    uint8_t f;
    c_lo0 = c_lo1 = -0x4000;
    c_hi0 = c_hi1 = 0x3FFF;
    c_n0 = c_n1 = 0;
    c_h0c = H0P; c_h1c = H1P;
    c_d56[0] = c_d56[1] = 0;
    c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
    c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
    for (f = 0; f < 2; f++) {
        uint8_t b;
        c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
        for (b = 0; b < 64; b++) c_hist[f][b] = 0;
        c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
        c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
    }
    ss_init(&ss, cap, ncap);
    while (ss_next(&ss, &sg)) {
        uint16_t t, e;
        uint8_t known_all = 1;
        int16_t amin, amax;
        cal_cloud(sg.u, sg.fam);
        if (sg.k1 > NB) continue;
        e = (sg.k1 < NB) ? sg.k1 : NB;
        for (t = sg.k0; t < e; t++)
            if (known_bit(t) < 0) { known_all = 0; break; }
        if (!known_all) continue;
        a_bounds(sg.k0, sg.k1, &amin, &amax);
        if (amin == amax)
            cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
    }
    /* width fit: intersection, prior-clamped, guarded */
    {
        int16_t h0 = H0P, h1 = H1P;
        if (c_n0 >= LAB_MIN) {
            int16_t h = (c_lo0 > c_hi0) ? (int16_t)((c_lo0 + c_hi0) >> 1)
                : (H0P < c_lo0 ? c_lo0 : (H0P > c_hi0 ? c_hi0 : H0P));
            if (h >= H0_LO && h <= H0_HI) h0 = h;
        }
        if (c_n1 >= LAB_MIN) {
            int16_t h = (c_lo1 > c_hi1) ? (int16_t)((c_lo1 + c_hi1) >> 1)
                : (H1P < c_lo1 ? c_lo1 : (H1P > c_hi1 ? c_hi1 : H1P));
            if (h >= H1_LO && h <= H1_HI) h1 = h;
        }
        if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
        c_h0c = h0; c_h1c = h1;
    }
    for (f = 0; f < 2; f++) {
        int16_t th, cfit, delta;
        if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
        cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
        delta = (int16_t)(th + c_c0[f] - cfit);
        if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
        if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
        c_d56[f] = (int8_t)delta;
    }
}

/* ---- P4: decision ------------------------------------------------------ */

static uint16_t hinge(int16_t u, int16_t v, int16_t h)
{
    int16_t g = 0;
    if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
    if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
    return (uint16_t)g;
}

/* fills d_costs / d_inter for a in [0..acap]; returns acap */
static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
                      uint8_t fam, int16_t *a_hat, int16_t *a_free,
                      int16_t *lo_out, int16_t *hi_out)
{
    int16_t L = (int16_t)(k1 - k0);
    int16_t acap = (L < A_CAP) ? L : A_CAP;
    int16_t h0e = c_h0c, h1e = c_h1c;
    int16_t amin, amax, lo, hi, a;
    uint16_t bc;
    uint8_t bi;
    if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
    if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
    d_inter = 0;
    for (a = 0; a <= acap; a++) {
        uint16_t c;
        uint8_t it;
        if (a == 0) {
            c = hinge(u, v, h0e);
            it = (u < h0e && h0e <= v);
        } else {
            int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
            c = hinge(u, v, h);
            it = (u < h && h <= v);
            if (a < L) {
                int16_t h2 = (int16_t)(a * BIT_U + h0e);
                uint16_t c2 = hinge(u, v, h2);
                if (c2 < c) c = c2;
                if (u < h2 && h2 <= v) it = 1;
            }
        }
        d_costs[a] = c;
        if (it) d_inter |= (uint16_t)(1u << a);
    }
    /* free argmin: (cost, !interior, a) */
    bc = 0xFFFF; bi = 1; *a_free = 0;
    for (a = 0; a <= acap; a++) {
        uint8_t it = (uint8_t)((d_inter >> a) & 1);
        if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
            bc = d_costs[a]; bi = it; *a_free = a;
        }
    }
    a_bounds(k0, k1, &amin, &amax);
    lo = (amin > 0) ? amin : 0;
    hi = (amax < acap) ? amax : acap;
    if (lo > hi) { lo = 0; hi = acap; }
    bc = 0xFFFF; bi = 1; *a_hat = lo;
    for (a = lo; a <= hi; a++) {
        uint8_t it = (uint8_t)((d_inter >> a) & 1);
        if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
            bc = d_costs[a]; bi = it; *a_hat = a;
        }
    }
    *lo_out = lo; *hi_out = hi;
    return acap;
}

static void decide_pass(const uint8_t *cap, uint16_t ncap)
{
    SStream ss;
    Seg sg;
    uint16_t t;
    for (t = 0; t < NBB; t++) { d_bits[t] = 0; d_conf[t] = 0; d_tied[t] = 0; }
    d_nknife = 0; d_nres = 0;
    d_infeas = 0; d_laberr = 0; d_nseg = 0;
    ss_init(&ss, cap, ncap);
    while (ss_next(&ss, &sg)) {
        int16_t a_hat, a_free, lo, hi, acap, a;
        int16_t L = (int16_t)(sg.k1 - sg.k0);
        uint16_t e, c_hat;
        uint8_t known_all, dead, nins;
        int16_t ins0 = -1, ins1 = -1;
        d_nseg++;
        if (sg.k0 >= NB) continue;
        acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
                      &a_hat, &a_free, &lo, &hi);
        c_hat = d_costs[a_hat];
        if (c_hat > INFEAS_U && d_infeas < 255) d_infeas++;
        e = (sg.k1 < NB) ? sg.k1 : NB;
        known_all = 1;
        for (t = sg.k0; t < e; t++)
            if (known_bit(t) < 0) { known_all = 0; break; }
        dead = 0; nins = 0;
        for (a = 0; a <= acap; a++)
            if ((d_inter >> a) & 1) nins++;
        if (nins >= 2) dead = 1;
        if (known_all && lo == hi && a_free != lo && !dead && d_laberr < 255)
            d_laberr++;
        /* dead-window tie inside allowed range */
        nins = 0;
        for (a = lo; a <= hi; a++) {
            if ((d_inter >> a) & 1) {
                if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
                nins++;
            }
        }
        if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
            uint16_t tt = (uint16_t)(sg.k0 + ins0);
            if (tt < NB) BSET(d_tied, tt);
        }
        /* emit + margins */
        for (t = sg.k0; t < e; t++) {
            int16_t off = (int16_t)(t - sg.k0);
            uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
            if (off < a_hat) BSET(d_bits, t);
            for (a = lo; a <= hi; a++) {
                if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
                else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
            }
            if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
            else {
                int16_t dm = (int16_t)(c0m - c1m);
                if (dm < 0) dm = (int16_t)-dm;
                m = (dm > 255) ? 255 : (uint16_t)dm;
            }
            if (m >= CONF_M && !BGET(d_tied, t)) BSET(d_conf, t);
        }
        /* knife candidates */
        if ((sg.fam == 5 || sg.fam == 6) && L == 1 &&
            sg.k0 >= 32 && sg.k0 < NB - 32) {
            int16_t dm = (int16_t)(d_costs[0] - d_costs[1]);
            if (dm < 0) dm = (int16_t)-dm;
            if (dm > 255) dm = 255;
            if (dm < KNIFE_M && d_nknife < KNIFE_MAX)
                d_knife[d_nknife++] = sg.k0;
        }
    }
}

/* ---- votes -------------------------------------------------------------- */

static uint8_t is_knife(uint16_t t)
{
    uint8_t i;
    for (i = 0; i < d_nknife; i++)
        if (d_knife[i] == t) return 1;
    return 0;
}

static uint8_t is_resolved(uint16_t t)
{
    uint8_t i;
    for (i = 0; i < d_nres; i++)
        if (d_resolved[i] == t) return 1;
    return 0;
}

static void votes(void)
{
    uint8_t lag_ok[2] = {0, 0};
    uint8_t li;
    uint16_t t;
    for (li = 0; li < 2; li++) {
        uint16_t lag = li ? 16 : 8;
        uint16_t n_pair = 0, agree = 0;
        for (t = 32; t + lag < (uint16_t)(NB - 32); t++) {
            uint16_t s = (uint16_t)(t + lag);
            if (is_knife(t) || is_knife(s)) continue;
            if (BGET(d_tied, t) || BGET(d_tied, s)) continue;
            if (!BGET(d_conf, t) || !BGET(d_conf, s)) continue;
            n_pair++;
            if (BGET(d_bits, t) == BGET(d_bits, s)) agree++;
        }
        lag_ok[li] = (n_pair >= KNIFE_PAIR_MIN &&
                      (uint32_t)agree * 100 >=
                      (uint32_t)KNIFE_AGREE_PCT * n_pair);
    }
    if (!lag_ok[0] && !lag_ok[1]) return;
    /* dead-window vote (gated) */
    for (t = 32; t < (uint16_t)(NB - 32); t++) {
        uint8_t nv = 0, val = 0, mixed = 0;
        int8_t j;
        static const int16_t DTS[4] = {-16, -8, 8, 16};
        if (!BGET(d_tied, t)) continue;
        for (j = 0; j < 4; j++) {
            int16_t dt = DTS[j];
            int32_t s = (int32_t)t + dt;
            uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
            if (!lag_ok[lag == 16]) continue;
            if (s < 32 || s >= NB - 32) continue;
            if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
                continue;
            if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
            else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
            nv++;
        }
        if (nv >= DEAD_VOTE_MIN && !mixed) {
            if (val) BSET(d_bits, t); else BCLR(d_bits, t);
            if (d_nres < RESOLVED_MAX) d_resolved[d_nres++] = t;
        }
    }
    /* knife vote */
    {
        uint8_t i;
        for (i = 0; i < d_nknife; i++) {
            uint16_t tk = d_knife[i];
            uint8_t nv = 0, val = 0, mixed = 0;
            int8_t j;
            static const int16_t DTS[4] = {-16, -8, 8, 16};
            if (is_resolved(tk)) continue;
            for (j = 0; j < 4; j++) {
                int16_t dt = DTS[j];
                int32_t s = (int32_t)tk + dt;
                uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
                if (!lag_ok[lag == 16]) continue;
                if (s < 32 || s >= NB - 32) continue;
                if (is_knife((uint16_t)s)) continue;
                if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
                    continue;
                if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
                else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
                nv++;
            }
            if (nv >= 1 && !mixed) {
                if (val) BSET(d_bits, tk); else BCLR(d_bits, tk);
            }
        }
    }
}

/* ---- top level ---------------------------------------------------------- */

/* returns 1 + payload in out[NB_PAYLOAD], or 0 (refusal / no frame) */
volatile uint8_t g_phases = 5;    /* dev: phase limiter for profiling */

uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out)
{
    uint16_t t;
    uint8_t viol = 0, r;
    if (!seed(cap, ncap)) return 0;
    if (g_phases < 2) return 0;
    for (r = 0; r < 2; r++) refine(cap, ncap);
    if (g_phases < 3) return 0;
    calibrate(cap, ncap);
    if (g_phases < 4) return 0;
    decide_pass(cap, ncap);
    if (g_phases < 5) return 0;
    votes();
    for (t = 0; t < NB; t++) {
        int8_t kb = known_bit(t);
        if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
    }
    if (viol > 0 || d_infeas > GATE_INFEAS || d_laberr > GATE_LABERR)
        return 0;
    for (t = 0; t < NB_PAYLOAD; t++) {
        uint8_t b = 0, j;
        for (j = 0; j < 8; j++)
            b = (uint8_t)((b << 1) | BGET(d_bits, 32 + 8 * t + j));
        out[t] = b;
    }
    return 1;
}
