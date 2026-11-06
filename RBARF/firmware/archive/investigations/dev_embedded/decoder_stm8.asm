;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module decoder
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _ws_decode
	.globl _g_phases
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_g_K:
	.ds 2
_g_tau:
	.ds 2
_c_lo0:
	.ds 2
_c_hi0:
	.ds 2
_c_lo1:
	.ds 2
_c_hi1:
	.ds 2
_c_n0:
	.ds 1
_c_n1:
	.ds 1
_c_h0c:
	.ds 2
_c_h1c:
	.ds 2
_c_d56:
	.ds 2
_c_hist:
	.ds 128
_c_labx0:
	.ds 4
_c_labx1:
	.ds 4
_c_labx0b:
	.ds 4
_c_labx1b:
	.ds 4
_c_c0:
	.ds 4
_c_gap56:
	.ds 4
_d_bits:
	.ds 56
_d_conf:
	.ds 56
_d_tied:
	.ds 56
_d_knife:
	.ds 64
_d_nknife:
	.ds 1
_d_resolved:
	.ds 32
_d_nres:
	.ds 1
_d_infeas:
	.ds 1
_d_laberr:
	.ds 1
_d_nseg:
	.ds 2
_d_costs:
	.ds 32
_d_inter:
	.ds 2
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area INITIALIZED
_g_phases::
	.ds 1
;--------------------------------------------------------
; absolute external ram data
;--------------------------------------------------------
	.area DABS (ABS)

; default segment ordering for linker
	.area HOME
	.area GSINIT
	.area GSFINAL
	.area CONST
	.area INITIALIZER
	.area CODE

;--------------------------------------------------------
; global & static initialisations
;--------------------------------------------------------
	.area HOME
	.area GSINIT
	.area GSFINAL
	.area GSINIT
;--------------------------------------------------------
; Home
;--------------------------------------------------------
	.area HOME
	.area HOME
;--------------------------------------------------------
; code
;--------------------------------------------------------
	.area CODE
;	decoder.c: 87: static int8_t known_bit(uint16_t t)
;	-----------------------------------------
;	 function known_bit
;	-----------------------------------------
_known_bit:
	push	a
;	decoder.c: 89: if (t < 32)
	ldw	y, x
	cpw	x, #0x0020
	jrnc	00102$
;	decoder.c: 90: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
	ldw	x, y
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_HDR+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	and	a, #0x07
	ld	(0x01, sp), a
	ld	a, #0x07
	sub	a, (0x01, sp)
	jreq	00125$
00124$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00124$
00125$:
	ld	a, xl
	and	a, #0x01
	jra	00105$
00102$:
;	decoder.c: 91: if (t >= NB - 32) {
	cpw	x, #0x01a0
	jrc	00104$
;	decoder.c: 92: uint16_t u = t - (NB - 32);
	subw	x, #0x01a0
;	decoder.c: 93: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
	ldw	y, x
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_TRL+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	and	a, #0x07
	ld	(0x01, sp), a
	ld	a, #0x07
	sub	a, (0x01, sp)
	jreq	00128$
00127$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00127$
00128$:
	ld	a, xl
	and	a, #0x01
;	decoder.c: 95: return -1;
	.byte 0xc5
00104$:
	ld	a, #0xff
00105$:
;	decoder.c: 96: }
	addw	sp, #1
	ret
;	decoder.c: 120: static void ps_init(PStream *p, const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function ps_init
;	-----------------------------------------
_ps_init:
	sub	sp, #4
;	decoder.c: 122: p->cap = cap; p->ncap = ncap;
	ldw	y, x
	ld	a, (0x08, sp)
	ld	(0x1, x), a
	ld	a, (0x07, sp)
	ld	(x), a
	ldw	x, y
	incw	x
	incw	x
	ld	a, (0x0a, sp)
	ld	(0x1, x), a
	ld	a, (0x09, sp)
	ld	(x), a
;	decoder.c: 123: p->i = 0; p->s = 0; p->tbase = 0; p->wsum = 0;
	ldw	x, y
	addw	x, #0x0004
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	clr	(0x0006, x)
	ldw	x, y
	addw	x, #0x0007
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	addw	x, #0x0009
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 124: p->t_prev = 0; p->have_prev = 0;
	ldw	x, y
	addw	x, #0x000b
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	clr	(0x000d, x)
;	decoder.c: 125: p->in_pulse = 0; p->seen = 0; p->done = 0; p->low_run = 0;
	ldw	x, y
	clr	(0x000e, x)
	ldw	x, y
	clr	(0x000f, x)
	ldw	x, y
	clr	(0x0010, x)
	ldw	x, y
	addw	x, #0x0011
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 126: p->ra = p->rb = p->fa = 0; p->sfa = 0;
	ldw	x, y
	addw	x, #0x0013
	ldw	(0x01, sp), x
	ldw	x, y
	addw	x, #0x0015
	ldw	(0x03, sp), x
	ldw	x, y
	addw	x, #0x0017
	clr	(0x1, x)
	clr	(x)
	ldw	x, (0x03, sp)
	clr	(0x1, x)
	clr	(x)
	ldw	x, (0x01, sp)
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	clr	(0x0019, x)
;	decoder.c: 127: }
	ldw	x, (5, sp)
	addw	sp, #10
	jp	(x)
;	decoder.c: 130: static uint8_t ps_next(PStream *p, Pulse *out)
;	-----------------------------------------
;	 function ps_next
;	-----------------------------------------
_ps_next:
	sub	sp, #53
;	decoder.c: 132: while (!p->done) {
	ldw	(0x34, sp), x
	addw	x, #0x000e
	ldw	(0x03, sp), x
	ldw	x, (0x34, sp)
	addw	x, #0x0009
	ldw	(0x05, sp), x
	ldw	x, (0x34, sp)
	addw	x, #0x000f
	ldw	(0x07, sp), x
	ldw	x, (0x34, sp)
	addw	x, #0x0010
	ldw	(0x09, sp), x
	ldw	x, (0x34, sp)
	addw	x, #0x000d
	ldw	(0x0b, sp), x
	ldw	x, (0x34, sp)
	addw	x, #0x000b
	ldw	(0x0d, sp), x
	ldw	y, (0x07, sp)
	ldw	(0x0f, sp), y
00133$:
	ldw	x, (0x09, sp)
	ld	a, (x)
;	decoder.c: 147: p->fa = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum + 2);
	ldw	x, (0x34, sp)
	addw	x, #0x0017
	ldw	(0x11, sp), x
;	decoder.c: 149: p->sfa = 5;
	ldw	x, (0x34, sp)
	addw	x, #0x0019
	ldw	(0x13, sp), x
;	decoder.c: 175: p->ra = p->have_prev ? p->t_prev
	ldw	x, (0x34, sp)
	addw	x, #0x0013
	ldw	(0x15, sp), x
;	decoder.c: 177: p->rb = t;
	ldw	x, (0x34, sp)
	addw	x, #0x0015
	ldw	(0x17, sp), x
;	decoder.c: 186: out->ra = p->ra; out->rb = p->rb;
	ldw	y, (0x38, sp)
	ldw	(0x19, sp), y
	ldw	x, y
	incw	x
	incw	x
	ldw	(0x1b, sp), x
;	decoder.c: 187: out->fa = p->fa; out->fb = t; out->sfa = p->sfa;
	ldw	x, y
	addw	x, #0x0004
	ldw	(0x1d, sp), x
	ldw	x, y
	addw	x, #0x0006
	ldw	(0x1f, sp), x
	ldw	x, y
	addw	x, #0x0008
	ldw	(0x21, sp), x
;	decoder.c: 132: while (!p->done) {
	tnz	a
	jreq	00320$
	jp	00135$
00320$:
;	decoder.c: 133: uint8_t v, s = p->s;
	ldw	x, (0x34, sp)
	addw	x, #0x0006
	ldw	(0x23, sp), x
	ld	a, (x)
	ld	(0x25, sp), a
;	decoder.c: 135: if (p->i >= p->ncap) break;
	ldw	x, (0x34, sp)
	addw	x, #0x0004
	ldw	(0x26, sp), x
	ldw	x, (x)
	ldw	(0x28, sp), x
	ldw	x, (0x34, sp)
	ldw	x, (0x2, x)
	ldw	(0x01, sp), x
	ldw	x, (0x28, sp)
	cpw	x, (0x01, sp)
	jrc	00321$
	jp	00135$
00321$:
;	decoder.c: 137: uint8_t bt = p->cap[p->i + 1];
	ldw	y, (0x34, sp)
	ldw	(0x2a, sp), y
;	decoder.c: 139: p->t_prev = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum);
	ldw	x, (0x34, sp)
	addw	x, #0x0007
	ldw	(0x2c, sp), x
;	decoder.c: 141: p->low_run = (uint16_t)(p->low_run + 8);
	ldw	x, (0x34, sp)
	addw	x, #0x0011
	ldw	(0x2e, sp), x
;	decoder.c: 136: if (s == 6 && p->i + 1 < p->ncap) {
	ldw	x, (0x28, sp)
	incw	x
	ldw	(0x30, sp), x
	cpw	x, (0x01, sp)
	clr	a
	rlc	a
	ld	(0x32, sp), a
	ld	a, (0x25, sp)
	cp	a, #0x06
	jreq	00324$
	jp	00113$
00324$:
	tnz	(0x32, sp)
	jrne	00325$
	jp	00113$
00325$:
;	decoder.c: 137: uint8_t bt = p->cap[p->i + 1];
	ldw	x, (0x2a, sp)
	ldw	x, (x)
	addw	x, (0x30, sp)
	ld	a, (x)
;	decoder.c: 138: if (bt == 0x00 && !p->in_pulse) {
	ld	(0x33, sp), a
	jrne	00107$
	ldw	x, (0x03, sp)
	ld	a, (x)
	jrne	00107$
;	decoder.c: 139: p->t_prev = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum);
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	addw	x, #0x003d
	ldw	y, (0x05, sp)
	ldw	y, (y)
	ldw	(0x32, sp), x
	addw	y, (0x32, sp)
	ldw	x, (0x0d, sp)
	ldw	(x), y
;	decoder.c: 140: p->have_prev = 1;
	ldw	x, (0x0b, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 141: p->low_run = (uint16_t)(p->low_run + 8);
	ldw	x, (0x2e, sp)
	ldw	x, (x)
	addw	x, #0x0008
	ldw	y, (0x2e, sp)
	ldw	(y), x
;	decoder.c: 142: p->i++; p->tbase += LOOP_CY;    /* s stays 6 */
	ldw	x, (0x26, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x26, sp)
	ldw	(y), x
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	addw	x, #0x0028
	ldw	y, (0x2c, sp)
	ldw	(y), x
;	decoder.c: 143: if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
	ldw	x, (0x07, sp)
	ld	a, (x)
	ld	(0x33, sp), a
	jrne	00328$
	jp	00133$
00328$:
	ldw	x, (0x2e, sp)
	ldw	x, (x)
	cpw	x, #0x00c8
	jrnc	00329$
	jp	00133$
00329$:
	ldw	x, (0x09, sp)
	ld	a, #0x01
	ld	(x), a
	jp	00135$
;	decoder.c: 144: continue;
00107$:
;	decoder.c: 146: if (bt == 0xFF && p->in_pulse) {
	ld	a, (0x33, sp)
	inc	a
	jrne	00113$
	ldw	x, (0x03, sp)
	ld	a, (x)
	jreq	00113$
;	decoder.c: 147: p->fa = (uint16_t)(p->tbase + LOOP_CY + 21 + p->wsum + 2);
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	ldw	y, (0x05, sp)
	ldw	y, (y)
	addw	y, #0x003f
	ldw	(0x32, sp), x
	addw	y, (0x32, sp)
	ldw	x, (0x11, sp)
	ldw	(x), y
;	decoder.c: 148: p->wsum += 2;                   /* sum of W over the octet */
	ldw	x, (0x05, sp)
	ldw	x, (x)
	incw	x
	incw	x
	exgw	x, y
	ldw	x, (0x05, sp)
	ldw	(x), y
;	decoder.c: 149: p->sfa = 5;
	ldw	x, (0x13, sp)
	ld	a, #0x05
	ld	(x), a
;	decoder.c: 150: p->low_run = 0;
	ldw	x, (0x2e, sp)
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 151: p->seen = 1;
	ldw	x, (0x07, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 152: p->t_prev = p->fa;
	ldw	x, (0x11, sp)
	ldw	x, (x)
	ldw	y, (0x0d, sp)
	ldw	(y), x
;	decoder.c: 153: p->have_prev = 1;
	ldw	x, (0x0b, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 154: p->i++; p->tbase += LOOP_CY;
	ldw	x, (0x26, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x26, sp)
	ldw	(y), x
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	addw	x, #0x0028
	ldw	y, (0x2c, sp)
	ldw	(y), x
;	decoder.c: 155: continue;
	jp	00133$
00113$:
;	decoder.c: 158: if (s < 6) {
	ld	a, (0x25, sp)
	cp	a, #0x06
	jrnc	00118$
;	decoder.c: 159: v = (uint8_t)((p->cap[p->i] >> (5 - s)) & 1);
	ldw	x, (0x2a, sp)
	ldw	x, (x)
	addw	x, (0x28, sp)
	ld	a, (x)
	ld	xl, a
	ld	a, #0x05
	sub	a, (0x25, sp)
	jreq	00336$
00335$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00335$
00336$:
	ld	a, xl
	and	a, #0x01
	ld	(0x29, sp), a
	jra	00119$
00118$:
;	decoder.c: 161: if (p->i + 1 >= p->ncap) {      /* last loop: BS lost */
	ld	a, (0x32, sp)
	jrne	00116$
;	decoder.c: 162: p->i++; p->s = 0; p->tbase += LOOP_CY;
	ldw	x, (0x28, sp)
	incw	x
	ldw	y, (0x26, sp)
	ldw	(y), x
	ldw	x, (0x23, sp)
	clr	(x)
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	addw	x, #0x0028
	ldw	y, (0x2c, sp)
	ldw	(y), x
;	decoder.c: 163: continue;
	jp	00133$
00116$:
;	decoder.c: 165: v = (uint8_t)((p->cap[p->i + 1] >> (7 - (s - 6))) & 1);
	ldw	x, (0x2a, sp)
	ldw	x, (x)
	addw	x, (0x30, sp)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x25, sp)
	sub	a, #0x06
	ld	(0x33, sp), a
	ld	a, #0x07
	sub	a, (0x33, sp)
	jreq	00339$
00338$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00338$
00339$:
	ld	a, xl
	and	a, #0x01
	ld	(0x29, sp), a
00119$:
;	decoder.c: 167: t = (uint16_t)(p->tbase + O_CY[s] + p->wsum);
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	ldw	y, x
	clrw	x
	ld	a, (0x25, sp)
	ld	xl, a
	ld	a, (_O_CY+0, x)
	ld	(0x33, sp), a
	clr	(0x32, sp)
	addw	y, (0x32, sp)
	ldw	x, (0x05, sp)
	ldw	(0x2a, sp), x
	ldw	x, (0x05, sp)
	ldw	x, (x)
	ldw	(0x30, sp), y
	addw	x, (0x30, sp)
	ldw	(0x32, sp), x
;	decoder.c: 169: if (s == 7) { p->s = 0; p->i++; p->tbase += LOOP_CY; }
	ld	a, (0x25, sp)
	cp	a, #0x07
	jrne	00121$
	ldw	x, (0x23, sp)
	clr	(x)
	ldw	x, (0x26, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x26, sp)
	ldw	(y), x
	ldw	x, (0x2c, sp)
	ldw	x, (x)
	addw	x, #0x0028
	ldw	y, (0x2c, sp)
	ldw	(y), x
	jra	00122$
00121$:
;	decoder.c: 170: else        { p->s = (uint8_t)(s + 1); }
	ld	a, (0x25, sp)
	inc	a
	ldw	x, (0x23, sp)
	ld	(x), a
00122$:
;	decoder.c: 171: if (v) {
	tnz	(0x29, sp)
	jreq	00131$
;	decoder.c: 172: p->wsum += W_CY[s];
	ldw	x, (0x2a, sp)
	ldw	x, (x)
	ldw	y, x
	clrw	x
	ld	a, (0x25, sp)
	ld	xl, a
	addw	x, #(_W_CY+0)
	ld	a, (x)
	ld	(0x31, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x30, sp), a
	addw	y, (0x30, sp)
	ldw	x, (0x2a, sp)
	ldw	(x), y
;	decoder.c: 173: if (!p->in_pulse) {
	ldw	x, (0x03, sp)
	ld	a, (x)
	jrne	00124$
;	decoder.c: 174: p->in_pulse = 1;
	ldw	x, (0x03, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 175: p->ra = p->have_prev ? p->t_prev
	ldw	x, (0x0b, sp)
	ld	a, (x)
	jreq	00140$
	ldw	x, (0x0d, sp)
	ldw	x, (x)
	ldw	(0x30, sp), x
	jra	00141$
00140$:
;	decoder.c: 176: : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
	ldw	y, (0x32, sp)
	ldw	(0x30, sp), y
	ldw	x, y
	cpw	x, #0x0004
	jrc	00142$
	ldw	x, (0x30, sp)
	subw	x, #0x0004
	.byte 0x21
00142$:
	clrw	x
00143$:
	ldw	(0x30, sp), x
00141$:
	ldw	y, (0x30, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
;	decoder.c: 177: p->rb = t;
	ldw	x, (0x17, sp)
	ldw	y, (0x32, sp)
	ldw	(x), y
00124$:
;	decoder.c: 179: p->fa = t;
	ldw	x, (0x11, sp)
	ldw	y, (0x32, sp)
	ldw	(x), y
;	decoder.c: 180: p->sfa = s;
	ldw	x, (0x13, sp)
	ld	a, (0x25, sp)
	ld	(x), a
;	decoder.c: 181: p->low_run = 0;
	ldw	x, (0x2e, sp)
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 182: p->seen = 1;
	ldw	x, (0x07, sp)
	ld	a, #0x01
	ld	(x), a
	jra	00132$
00131$:
;	decoder.c: 184: if (p->in_pulse) {
	ldw	x, (0x03, sp)
	ld	a, (x)
	jreq	00126$
;	decoder.c: 185: p->in_pulse = 0;
	ldw	x, (0x03, sp)
	clr	(x)
;	decoder.c: 186: out->ra = p->ra; out->rb = p->rb;
	ldw	x, (0x15, sp)
	ldw	x, (x)
	ldw	y, (0x19, sp)
	ldw	(y), x
	ldw	x, (0x17, sp)
	ldw	x, (x)
	ldw	y, (0x1b, sp)
	ldw	(y), x
;	decoder.c: 187: out->fa = p->fa; out->fb = t; out->sfa = p->sfa;
	ldw	x, (0x11, sp)
	ldw	x, (x)
	ldw	y, (0x1d, sp)
	ldw	(y), x
	ldw	x, (0x1f, sp)
	ldw	y, (0x32, sp)
	ldw	(x), y
	ldw	x, (0x13, sp)
	ld	a, (x)
	ldw	x, (0x21, sp)
	ld	(x), a
;	decoder.c: 188: p->t_prev = t; p->have_prev = 1;
	ldw	x, (0x0d, sp)
	ldw	y, (0x32, sp)
	ldw	(x), y
	ldw	x, (0x0b, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 189: p->low_run = 1;
	ldw	x, (0x2e, sp)
	ldw	y, #0x0001
	ldw	(x), y
;	decoder.c: 190: return 1;
	ld	a, #0x01
	jra	00138$
00126$:
;	decoder.c: 192: p->low_run++;
	ldw	x, (0x2e, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x2e, sp)
	ldw	(y), x
;	decoder.c: 193: if (p->seen && p->low_run >= LATCH_RUN) { p->done = 1; break; }
	ldw	x, (0x0f, sp)
	ld	a, (x)
	jreq	00132$
	ldw	x, (0x2e, sp)
	ldw	x, (x)
	cpw	x, #0x00c8
	jrc	00132$
	ldw	x, (0x09, sp)
	ld	a, #0x01
	ld	(x), a
	jra	00135$
00132$:
;	decoder.c: 195: p->t_prev = t;
	ldw	x, (0x0d, sp)
	ldw	y, (0x32, sp)
	ldw	(x), y
;	decoder.c: 196: p->have_prev = 1;
	ldw	x, (0x0b, sp)
	ld	a, #0x01
	ld	(x), a
	jp	00133$
00135$:
;	decoder.c: 198: if (p->in_pulse) {                       /* capture ended high */
	ldw	x, (0x03, sp)
	ld	a, (x)
	jreq	00137$
;	decoder.c: 199: p->in_pulse = 0;
	ldw	x, (0x03, sp)
	clr	(x)
;	decoder.c: 200: out->ra = p->ra; out->rb = p->rb;
	ldw	x, (0x15, sp)
	ldw	x, (x)
	ldw	y, (0x19, sp)
	ldw	(y), x
	ldw	x, (0x17, sp)
	ldw	x, (x)
	ldw	y, (0x1b, sp)
	ldw	(y), x
;	decoder.c: 201: out->fa = p->fa; out->fb = (uint16_t)(p->fa + FIRST_BR);
	ldw	x, (0x11, sp)
	ldw	x, (x)
	ldw	y, (0x1d, sp)
	ldw	(y), x
	ldw	x, (0x11, sp)
	ldw	x, (x)
	addw	x, #0x0004
	ldw	y, (0x1f, sp)
	ldw	(y), x
;	decoder.c: 202: out->sfa = p->sfa;
	ldw	x, (0x13, sp)
	ld	a, (x)
	ldw	x, (0x21, sp)
	ld	(x), a
;	decoder.c: 203: return 1;
	ld	a, #0x01
	jra	00138$
00137$:
;	decoder.c: 205: p->done = 1;
	ldw	x, (0x09, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 206: return 0;
	clr	a
00138$:
;	decoder.c: 207: }
	ldw	x, (54, sp)
	addw	sp, #57
	jp	(x)
;	decoder.c: 239: static uint32_t map_y(uint16_t t)
;	-----------------------------------------
;	 function map_y
;	-----------------------------------------
_map_y:
	sub	sp, #8
;	decoder.c: 241: return (uint32_t)((uint32_t)t * g_K >> KQ) + (uint32_t)(int32_t)g_tau;
	ldw	y, _g_K+0
	pushw	y
	call	___muluint2ulong
	addw	sp, #2
	exgw	x, y
	ld	a, #0x0b
00103$:
	srlw	x
	rrcw	y
	dec	a
	jrne	00103$
	ldw	(0x01, sp), x
	ldw	x, _g_tau+0
	ld	a, xh
	rlc	a
	clr	a
	sbc	a, #0x00
	ldw	(0x07, sp), x
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	addw	y, (0x07, sp)
	push	a
	ld	a, xl
	adc	a, (0x03, sp)
	ld	xl, a
	pop	a
	adc	a, (0x01, sp)
	ld	xh, a
	exgw	x, y
;	decoder.c: 243: }
	addw	sp, #8
	ret
;	decoder.c: 247: static uint8_t seed(const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function seed
;	-----------------------------------------
_seed:
	sub	sp, #41
	exgw	x, y
;	decoder.c: 252: uint16_t r0m = 0, flm = 0;
	clrw	x
	ldw	(0x24, sp), x
	clrw	x
	ldw	(0x26, sp), x
;	decoder.c: 254: ps_init(&ps, cap, ncap);
	ldw	x, (0x2c, sp)
	pushw	x
	pushw	y
	ldw	x, sp
	addw	x, #5
	call	_ps_init
;	decoder.c: 255: while (ps_next(&ps, &p)) {
	clrw	x
	ldw	(0x28, sp), x
00103$:
	ldw	x, sp
	addw	x, #27
	pushw	x
	ldw	x, sp
	addw	x, #3
	call	_ps_next
	tnz	a
	jreq	00105$
;	decoder.c: 256: if (np == 0) r0m = (uint16_t)((p.ra + p.rb) >> 1);
	ldw	x, (0x28, sp)
	jrne	00102$
	ldw	x, (0x1b, sp)
	ldw	y, (0x1d, sp)
	ldw	(0x26, sp), y
	addw	x, (0x26, sp)
	srlw	x
	ldw	(0x24, sp), x
00102$:
;	decoder.c: 257: flm = (uint16_t)((p.fa + p.fb) >> 1);
	ldw	y, (0x1f, sp)
	ldw	(0x26, sp), y
	ldw	x, (0x21, sp)
	addw	x, (0x26, sp)
	srlw	x
	ldw	(0x26, sp), x
;	decoder.c: 258: np++;
	ldw	x, (0x28, sp)
	incw	x
	ldw	(0x28, sp), x
	jra	00103$
00105$:
;	decoder.c: 260: if (np < 8 || flm <= r0m) return 0;
	ldw	x, (0x28, sp)
	cpw	x, #0x0008
	jrc	00106$
	ldw	x, (0x26, sp)
	cpw	x, (0x24, sp)
	jrugt	00107$
00106$:
	clr	a
	jra	00112$
00107$:
;	decoder.c: 262: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
	ldw	y, (0x26, sp)
	subw	y, (0x24, sp)
	clrw	x
	pushw	y
	pushw	x
	push	#0x00
	push	#0xa0
	push	#0xf9
	push	#0x1b
;	decoder.c: 263: if (K < K_MIN || K > K_MAX) return 0;
	call	__divulong
	addw	sp, #8
	ldw	(0x28, sp), x
	ldw	(0x26, sp), y
	ldw	x, (0x28, sp)
	cpw	x, #0xb3b0
	ld	a, (0x27, sp)
	sbc	a, #0x00
	ld	a, (0x26, sp)
	sbc	a, #0x00
	jrc	00109$
	ldw	x, #0xea60
	cpw	x, (0x28, sp)
	clr	a
	sbc	a, (0x27, sp)
	clr	a
	sbc	a, (0x26, sp)
	jrnc	00110$
00109$:
	clr	a
	jra	00112$
00110$:
;	decoder.c: 264: g_K = (uint16_t)K;
	ldw	x, (0x28, sp)
	ldw	_g_K+0, x
;	decoder.c: 265: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
	ldw	y, (0x24, sp)
	ldw	x, _g_K+0
	pushw	x
	ldw	x, y
	call	___muluint2ulong
	addw	sp, #2
	exgw	x, y
	ld	a, #0x0b
00162$:
	srlw	x
	rrcw	y
	dec	a
	jrne	00162$
	ldw	(0x28, sp), y
	ldw	x, #0x0200
	subw	x, (0x28, sp)
	ldw	_g_tau+0, x
;	decoder.c: 266: return 1;
	ld	a, #0x01
00112$:
;	decoder.c: 267: }
	ldw	x, (42, sp)
	addw	sp, #45
	jp	(x)
;	decoder.c: 271: static void refine(const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function refine
;	-----------------------------------------
_refine:
	sub	sp, #75
	exgw	x, y
;	decoder.c: 278: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
	clrw	x
	ldw	(0x3a, sp), x
	ldw	(0x38, sp), x
	clrw	x
	ldw	(0x3e, sp), x
	ldw	(0x3c, sp), x
;	decoder.c: 279: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
	clrw	x
	ldw	(0x42, sp), x
	ldw	(0x40, sp), x
	clrw	x
	ldw	(0x46, sp), x
	ldw	(0x44, sp), x
;	decoder.c: 283: ps_init(&ps, cap, ncap);
	ldw	x, (0x4e, sp)
	pushw	x
	pushw	y
	ldw	x, sp
	addw	x, #5
	call	_ps_init
;	decoder.c: 284: while (ps_next(&ps, &p)) {
	clrw	x
	ldw	(0x48, sp), x
	clrw	x
	ldw	(0x4a, sp), x
00106$:
	ldw	x, sp
	addw	x, #27
	pushw	x
	ldw	x, sp
	addw	x, #3
	call	_ps_next
	ld	(0x37, sp), a
	jrne	00176$
	jp	00108$
00176$:
;	decoder.c: 287: y = map_y((uint16_t)((p.ra + p.rb) >> 1));
	ldw	x, (0x1b, sp)
	ldw	y, (0x1d, sp)
	ldw	(0x36, sp), y
	addw	x, (0x36, sp)
	srlw	x
	call	_map_y
	ldw	(0x32, sp), x
	ldw	(0x30, sp), y
;	decoder.c: 288: if (y > y_end) break;
	ldw	x, #0x82a4
	cpw	x, (0x32, sp)
	ld	a, #0x03
	sbc	a, (0x31, sp)
	clr	a
	sbc	a, (0x30, sp)
	jrnc	00177$
	jp	00108$
00177$:
;	decoder.c: 289: q = (y + BIT_H) >> BIT_SH;
	ld	a, (0x32, sp)
	add	a, #0x01
	ldw	x, (0x30, sp)
	jrnc	00178$
	incw	x
00178$:
	rlwa	x
	clr	(0x34, sp)
	srl	a
	rrcw	x
;	decoder.c: 290: e = (int16_t)((int32_t)y - (int32_t)(q << BIT_SH));
	ldw	y, (0x32, sp)
	ldw	(0x36, sp), y
	clr	a
	rlwa	x
	sllw	x
	negw	x
	addw	x, (0x36, sp)
;	decoder.c: 291: if (y < mid_u) { n_lo++; se_lo += e; sy_lo += y; }
	ldw	(0x36, sp), x
	clrw	x
	tnz	(0x36, sp)
	jrpl	00179$
	decw	x
00179$:
	ld	a, (0x33, sp)
	cp	a, #0x00
	ld	a, (0x32, sp)
	sbc	a, #0xc2
	ld	a, (0x31, sp)
	sbc	a, #0x01
	ld	a, (0x30, sp)
	sbc	a, #0x00
	jrnc	00104$
	ldw	y, (0x48, sp)
	incw	y
	ldw	(0x48, sp), y
	ldw	y, (0x36, sp)
	addw	y, (0x3a, sp)
	ldw	(0x3a, sp), y
	ld	a, xl
	adc	a, (0x39, sp)
	ld	(0x39, sp), a
	ld	a, xh
	adc	a, (0x38, sp)
	ld	(0x38, sp), a
	ldw	x, (0x42, sp)
	addw	x, (0x32, sp)
	ldw	(0x42, sp), x
	ld	a, (0x41, sp)
	adc	a, (0x31, sp)
	ld	(0x41, sp), a
	ld	a, (0x40, sp)
	adc	a, (0x30, sp)
	ld	(0x40, sp), a
	jp	00106$
00104$:
;	decoder.c: 292: else           { n_hi++; se_hi += e; sy_hi += y; }
	ldw	y, (0x4a, sp)
	incw	y
	ldw	(0x4a, sp), y
	ldw	y, (0x36, sp)
	addw	y, (0x3e, sp)
	ldw	(0x3e, sp), y
	ld	a, xl
	adc	a, (0x3d, sp)
	ld	(0x3d, sp), a
	ld	a, xh
	adc	a, (0x3c, sp)
	ld	(0x3c, sp), a
	ldw	x, (0x46, sp)
	addw	x, (0x32, sp)
	ldw	(0x46, sp), x
	ld	a, (0x45, sp)
	adc	a, (0x31, sp)
	ld	(0x45, sp), a
	ld	a, (0x44, sp)
	adc	a, (0x30, sp)
	ld	(0x44, sp), a
	jp	00106$
00108$:
;	decoder.c: 294: if (n_lo < 2 || n_hi < 2) return;
	ldw	x, (0x48, sp)
	cpw	x, #0x0002
	jrnc	00181$
	jp	00117$
00181$:
	ldw	x, (0x4a, sp)
	cpw	x, #0x0002
	jrnc	00110$
	jp	00117$
00110$:
;	decoder.c: 295: me_lo = se_lo / (int32_t)n_lo;
	ldw	y, (0x48, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x3e, sp)
	pushw	x
	ldw	x, (0x3e, sp)
	pushw	x
;	decoder.c: 296: me_hi = se_hi / (int32_t)n_hi;
	call	__divslong
	addw	sp, #8
	ldw	(0x2a, sp), x
	ldw	(0x28, sp), y
	ldw	y, (0x4a, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x42, sp)
	pushw	x
	ldw	x, (0x42, sp)
	pushw	x
;	decoder.c: 297: my_lo = sy_lo / n_lo;
	call	__divslong
	addw	sp, #8
	ldw	(0x2e, sp), x
	ldw	(0x2c, sp), y
	ldw	y, (0x48, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x46, sp)
	pushw	x
	ldw	x, (0x46, sp)
	pushw	x
;	decoder.c: 298: my_hi = sy_hi / n_hi;
	call	__divulong
	addw	sp, #8
	ldw	(0x36, sp), x
	ldw	(0x34, sp), y
	ldw	y, (0x4a, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x4a, sp)
	pushw	x
	ldw	x, (0x4a, sp)
	pushw	x
;	decoder.c: 299: de = me_hi - me_lo;
	call	__divulong
	addw	sp, #8
	ldw	(0x32, sp), x
	ldw	(0x30, sp), y
	ldw	x, (0x2e, sp)
	subw	x, (0x2a, sp)
	ldw	(0x26, sp), x
	ld	a, (0x2d, sp)
	sbc	a, (0x29, sp)
	ld	(0x25, sp), a
	ld	a, (0x2c, sp)
	sbc	a, (0x28, sp)
	ld	(0x24, sp), a
;	decoder.c: 300: dy = (int32_t)my_hi - (int32_t)my_lo;
	ldw	x, (0x32, sp)
	subw	x, (0x36, sp)
	ldw	(0x2a, sp), x
	ld	a, (0x31, sp)
	sbc	a, (0x35, sp)
	ld	(0x29, sp), a
	ld	a, (0x30, sp)
	sbc	a, (0x34, sp)
	ld	(0x28, sp), a
;	decoder.c: 301: if (dy <= 0) return;
	clrw	x
	cpw	x, (0x2a, sp)
	clr	a
	sbc	a, (0x29, sp)
	clr	a
	sbc	a, (0x28, sp)
	jrslt	00113$
	jp	00117$
00113$:
;	decoder.c: 302: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
	ldw	x, _g_K+0
	ldw	(0x2e, sp), x
	clr	a
	clr	(0x2c, sp)
	push	a
	ldw	x, (0x27, sp)
	pushw	x
	ldw	x, (0x27, sp)
	pushw	x
	ldw	x, (0x33, sp)
	pushw	x
	ld	xl, a
	rlwa	x
	clr	a
	rrwa	x
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x37, sp), x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x3b, sp)
	pushw	x
	pushw	y
;	decoder.c: 303: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
	call	__divslong
	addw	sp, #8
	ldw	(0x33, sp), x
	ldw	(0x31, sp), y
	pop	a
	ldw	x, (0x3a, sp)
	addw	x, (0x3e, sp)
	ldw	(0x36, sp), x
	ldw	y, (0x38, sp)
	jrnc	00184$
	incw	y
00184$:
	addw	y, (0x3c, sp)
	ldw	x, (0x48, sp)
	addw	x, (0x4a, sp)
	ldw	(0x3e, sp), x
	ldw	(0x4a, sp), x
	clrw	x
	ldw	(0x48, sp), x
	push	a
	ldw	x, (0x4b, sp)
	pushw	x
	ldw	x, (0x4b, sp)
	pushw	x
	ldw	x, (0x3b, sp)
	pushw	x
	pushw	y
;	decoder.c: 304: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
	call	__divslong
	addw	sp, #8
	ldw	(0x3d, sp), x
	ldw	(0x3b, sp), y
	pop	a
	ldw	x, (0x42, sp)
	addw	x, (0x46, sp)
	ldw	(0x4a, sp), x
	ldw	y, (0x40, sp)
	jrnc	00185$
	incw	y
00185$:
	addw	y, (0x44, sp)
	ldw	x, (0x3e, sp)
	ldw	(0x46, sp), x
	clrw	x
	ldw	(0x44, sp), x
	push	a
	ldw	x, (0x47, sp)
	pushw	x
	ldw	x, (0x47, sp)
	pushw	x
	ldw	x, (0x4f, sp)
	pushw	x
	pushw	y
;	decoder.c: 305: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
	call	__divulong
	addw	sp, #8
	ldw	(0x49, sp), y
	pop	a
	ldw	y, (0x3c, sp)
	ldw	(0x46, sp), y
	push	a
	ld	a, (0x48, sp)
	neg	a
	ld	(0x40, sp), a
	clr	a
	sbc	a, (0x47, sp)
	ld	(0x3f, sp), a
	pop	a
	ldw	y, (0x48, sp)
	ldw	(0x40, sp), y
	ldw	y, _g_tau+0
	ldw	(0x46, sp), y
	push	a
	ld	a, (0x47, sp)
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x46, sp), a
	ld	(0x45, sp), a
	pop	a
	subw	x, (0x46, sp)
	push	a
	ld	a, (0x42, sp)
	sbc	a, (0x46, sp)
	ld	(0x4a, sp), a
	ld	a, (0x41, sp)
	sbc	a, (0x45, sp)
	ld	(0x49, sp), a
	pushw	x
	ldw	x, (0x4b, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x4b, sp), x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x4f, sp)
	pushw	x
	pushw	y
	call	__divslong
	addw	sp, #9
	addw	x, (0x3e, sp)
	ldw	(0x4a, sp), x
;	decoder.c: 306: if ((uint32_t)((int32_t)g_K - dk) < K_MIN ||
	ldw	y, (0x2e, sp)
	subw	y, (0x32, sp)
	ldw	x, (0x30, sp)
	jrnc	00186$
	incw	x
00186$:
	negw	x
	ldw	(0x48, sp), y
	ldw	(0x46, sp), x
	ldw	x, (0x48, sp)
	cpw	x, #0xb3b0
	ld	a, (0x47, sp)
	sbc	a, #0x00
	ld	a, (0x46, sp)
	sbc	a, #0x00
	jrc	00117$
;	decoder.c: 307: (uint32_t)((int32_t)g_K - dk) > K_MAX) return;
	ldw	x, #0xea60
	cpw	x, (0x48, sp)
	clr	a
	sbc	a, (0x47, sp)
	clr	a
	sbc	a, (0x46, sp)
	jrc	00117$
;	decoder.c: 308: g_K = (uint16_t)((int32_t)g_K - dk);
	ldw	x, _g_K+0
	ldw	y, (0x32, sp)
	ldw	(0x48, sp), y
	subw	x, (0x48, sp)
	ldw	_g_K+0, x
;	decoder.c: 309: g_tau = (int16_t)(g_tau + dtau);
	ldw	x, _g_tau+0
	addw	x, (0x4a, sp)
	ldw	_g_tau+0, x
00117$:
;	decoder.c: 310: }
	ldw	x, (76, sp)
	addw	sp, #79
	jp	(x)
;	decoder.c: 335: static void ss_init(SStream *s, const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function ss_init
;	-----------------------------------------
_ss_init:
	pushw	x
	exgw	x, y
;	decoder.c: 337: ps_init(&s->ps, cap, ncap);
	ldw	(0x01, sp), y
	pushw	y
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x07, sp)
	call	_ps_init
	popw	y
;	decoder.c: 338: s->y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
	ldw	x, y
	addw	x, #0x001a
	ld	a, #0xa4
	ld	(0x3, x), a
	ld	a, #0x82
	ld	(0x2, x), a
	ld	a, #0x03
	ld	(0x1, x), a
	clr	(x)
;	decoder.c: 339: s->y_prev = 0; s->have_y = 0; s->n = 0;
	ldw	x, y
	addw	x, #0x001e
	clr	(0x3, x)
	clr	(0x2, x)
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	clr	(0x0022, x)
	ldw	x, y
	addw	x, #0x0023
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 340: s->pend = 0; s->src_done = 0;
	ldw	x, y
	clr	(0x0025, x)
	ldw	x, y
	clr	(0x002d, x)
;	decoder.c: 341: s->p_k0 = 0; s->p_u = 0; s->p_v = 0; s->p_fam = 0;
	ldw	x, y
	addw	x, #0x0026
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	addw	x, #0x0028
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	addw	x, #0x002a
	clr	(0x1, x)
	clr	(x)
	ldw	x, y
	clr	(0x002c, x)
;	decoder.c: 342: }
	ldw	x, (3, sp)
	addw	sp, #8
	jp	(x)
;	decoder.c: 344: static uint8_t ss_next(SStream *s, Seg *out)
;	-----------------------------------------
;	 function ss_next
;	-----------------------------------------
_ss_next:
	sub	sp, #58
;	decoder.c: 347: while (!s->src_done) {
	ldw	(0x39, sp), x
	ldw	(0x16, sp), x
	ldw	x, (0x39, sp)
	addw	x, #0x001e
	ldw	(0x18, sp), x
	ldw	x, (0x39, sp)
	addw	x, #0x0023
	ldw	(0x1a, sp), x
	ldw	x, (0x39, sp)
	addw	x, #0x0026
	ldw	(0x1c, sp), x
	ldw	x, (0x39, sp)
	addw	x, #0x002d
	ldw	(0x1e, sp), x
00119$:
	ldw	x, (0x1e, sp)
	ld	a, (x)
;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
	ldw	x, (0x39, sp)
	addw	x, #0x0025
	ldw	(0x20, sp), x
;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
	ldw	x, (0x39, sp)
	addw	x, #0x0028
	ldw	(0x22, sp), x
;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
	ldw	x, (0x39, sp)
	addw	x, #0x002a
	ldw	(0x24, sp), x
;	decoder.c: 367: s->p_fam = p.sfa;
	ldw	x, (0x39, sp)
	addw	x, #0x002c
	ldw	(0x26, sp), x
;	decoder.c: 371: out->k0 = s->p_k0;
	ldw	y, (0x3d, sp)
	ldw	(0x28, sp), y
;	decoder.c: 372: out->k1 = (s->n < NB) ? s->n : NB;
	ldw	x, y
	incw	x
	incw	x
	ldw	(0x2a, sp), x
;	decoder.c: 373: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
	ldw	x, y
	addw	x, #0x0004
	ldw	(0x2c, sp), x
	ldw	x, y
	addw	x, #0x0006
	ldw	(0x2e, sp), x
	ldw	x, y
	addw	x, #0x0008
	ldw	(0x30, sp), x
;	decoder.c: 347: while (!s->src_done) {
	tnz	a
	jreq	00232$
	jp	00121$
00232$:
;	decoder.c: 351: if (!ps_next(&s->ps, &p)) { s->src_done = 1; break; }
	ldw	x, sp
	addw	x, #13
	ldw	y, (0x39, sp)
	pushw	x
	ldw	x, y
	call	_ps_next
	tnz	a
	jrne	00102$
	ldw	x, (0x1e, sp)
	ld	a, #0x01
	ld	(x), a
	jp	00121$
00102$:
;	decoder.c: 352: y = map_y((uint16_t)((p.ra + p.rb) >> 1));
	ldw	y, (0x0d, sp)
	ldw	(0x37, sp), y
	ldw	x, (0x0f, sp)
	addw	x, (0x37, sp)
	srlw	x
	call	_map_y
	ldw	(0x03, sp), x
	ldw	(0x01, sp), y
;	decoder.c: 353: if (y > s->y_end) { s->src_done = 1; break; }
	ldw	x, (0x16, sp)
	ldw	y, x
	ldw	y, (0x1c, y)
	ldw	x, (0x1a, x)
	ld	a, yl
	cp	a, (0x04, sp)
	ld	a, yh
	sbc	a, (0x03, sp)
	ld	a, xl
	sbc	a, (0x02, sp)
	ld	a, xh
	sbc	a, (0x01, sp)
	jrnc	00104$
	ldw	x, (0x1e, sp)
	ld	a, #0x01
	ld	(x), a
	jp	00121$
00104$:
;	decoder.c: 354: if (!s->have_y) { s->n = 0; s->have_y = 1; }
	ldw	x, (0x39, sp)
	addw	x, #0x0022
	ld	a, (x)
	ld	(0x38, sp), a
	jrne	00108$
	ldw	y, (0x1a, sp)
	clr	(0x1, y)
	clr	(y)
	ld	a, #0x01
	ld	(x), a
	jra	00109$
00108$:
;	decoder.c: 356: d = (int32_t)y - (int32_t)s->y_prev;
	ldw	y, (0x03, sp)
	ldw	(0x07, sp), y
	ld	a, (0x01, sp)
	ld	(0x05, sp), a
	ld	a, (0x02, sp)
	ldw	x, (0x18, sp)
	ldw	y, x
	ldw	y, (0x2, y)
	ldw	x, (x)
	ldw	(0x0b, sp), y
	ldw	(0x09, sp), x
	ldw	y, (0x07, sp)
	subw	y, (0x0b, sp)
	sbc	a, (0x0a, sp)
	ld	(0x36, sp), a
	ld	a, (0x05, sp)
	sbc	a, (0x09, sp)
	ld	(0x35, sp), a
;	decoder.c: 357: dn = (int16_t)((d + BIT_H) >> BIT_SH);
	addw	y, #0x0100
	ldw	x, (0x35, sp)
	jrnc	00236$
	incw	x
00236$:
	clr	a
	tnzw	x
	jrpl	00237$
	dec	a
00237$:
	rrwa	x
	rrwa	y
	sraw	x
	rrcw	y
;	decoder.c: 358: if (dn > 0) s->n = (uint16_t)(s->n + dn);
	ldw	x, y
	cpw	x, #0x0000
	jrsle	00109$
	ldw	x, (0x1a, sp)
	ldw	x, (x)
	ldw	(0x37, sp), x
	addw	y, (0x37, sp)
	ldw	x, (0x1a, sp)
	ldw	(x), y
00109$:
;	decoder.c: 360: s->y_prev = y;
	ldw	x, (0x18, sp)
	ldw	y, (0x03, sp)
	ldw	(0x2, x), y
	ldw	y, (0x01, sp)
	ldw	(x), y
;	decoder.c: 361: yfa = map_y(p.fa);
	ldw	x, (0x11, sp)
	call	_map_y
	ldw	(0x37, sp), x
	ldw	(0x35, sp), y
;	decoder.c: 362: yfb = map_y(p.fb);
	ldw	x, (0x13, sp)
	call	_map_y
	ldw	(0x09, sp), y
;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
	ldw	y, (0x20, sp)
	ld	a, (y)
	ld	(0x32, sp), a
;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
	ldw	y, (0x37, sp)
	ldw	(0x33, sp), y
;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
	ldw	(0x35, sp), x
;	decoder.c: 367: s->p_fam = p.sfa;
;	decoder.c: 363: if (s->pend && s->n == s->p_k0) {            /* spurious split */
	tnz	(0x32, sp)
	jreq	00111$
	ldw	x, (0x1a, sp)
	ldw	x, (x)
	ldw	y, (0x1c, sp)
	ldw	y, (y)
	ldw	(0x37, sp), y
	cpw	x, (0x37, sp)
	jrne	00111$
;	decoder.c: 364: base = (uint32_t)BIAS_U + (uint32_t)s->p_k0 * BIT_U;
	ldw	x, (0x37, sp)
	swapw	x
	clr	a
	clr	(0x2f, sp)
	exg	a, xl
	ld	(0x2c, sp), a
	exg	a, xl
	ld	(0x2b, sp), a
	clr	a
	ld	xl, a
	sllw	x
	rlc	(0x2c, sp)
	rlc	(0x2b, sp)
	addw	x, #0x0200
;	decoder.c: 365: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
	ldw	(0x37, sp), x
	ldw	y, (0x33, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x22, sp)
	ldw	(x), y
;	decoder.c: 366: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
	ldw	y, (0x35, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x24, sp)
	ldw	(x), y
;	decoder.c: 367: s->p_fam = p.sfa;
	ld	a, (0x15, sp)
	ldw	x, (0x26, sp)
	ld	(x), a
;	decoder.c: 368: continue;
	jp	00119$
00111$:
;	decoder.c: 370: if (s->pend) {
	tnz	(0x32, sp)
	jrne	00244$
	jp	00116$
00244$:
;	decoder.c: 371: out->k0 = s->p_k0;
	ldw	y, (0x1c, sp)
	ldw	(0x37, sp), y
	ldw	x, (0x1c, sp)
	ldw	x, (x)
	ldw	y, (0x28, sp)
	ldw	(y), x
;	decoder.c: 372: out->k1 = (s->n < NB) ? s->n : NB;
	ldw	y, (0x1a, sp)
	ldw	(0x28, sp), y
	ldw	x, (0x1a, sp)
	ldw	x, (x)
	ldw	(0x1c, sp), x
	cpw	x, #0x01c0
	jrc	00127$
	ldw	x, #0x01c0
	ldw	(0x1c, sp), x
00127$:
	ldw	y, (0x1c, sp)
	ldw	x, (0x2a, sp)
	ldw	(x), y
;	decoder.c: 373: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
	ldw	x, (0x22, sp)
	ldw	x, (x)
	ldw	y, (0x2c, sp)
	ldw	(y), x
	ldw	x, (0x24, sp)
	ldw	x, (x)
	ldw	y, (0x2e, sp)
	ldw	(y), x
	ldw	x, (0x26, sp)
	ld	a, (x)
	ldw	x, (0x30, sp)
	ld	(x), a
;	decoder.c: 375: if (s->n >= NB) { s->pend = 0; s->src_done = 1; return 1; }
	ldw	x, (0x28, sp)
	ldw	x, (x)
	ldw	(0x31, sp), x
	cpw	x, #0x01c0
	jrc	00114$
	ldw	x, (0x20, sp)
	clr	(x)
	ldw	x, (0x1e, sp)
	ld	a, #0x01
	ld	(x), a
	jp	00124$
00114$:
;	decoder.c: 376: base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
	ldw	y, (0x31, sp)
	clrw	x
	clr	a
	sll	a
	rlcw	y
	rlcw	x
	ld	(0x30, sp), a
	addw	y, #0x0002
	ldw	(0x2e, sp), y
	ld	a, xl
	adc	a, #0x00
;	decoder.c: 377: s->p_k0 = s->n;
	ldw	x, (0x37, sp)
	ldw	y, (0x31, sp)
	ldw	(x), y
;	decoder.c: 378: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
	ldw	y, (0x2f, sp)
	ldw	(0x37, sp), y
	ldw	y, (0x33, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x22, sp)
	ldw	(x), y
;	decoder.c: 379: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
	ldw	y, (0x35, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x24, sp)
	ldw	(x), y
;	decoder.c: 380: s->p_fam = p.sfa;
	ld	a, (0x15, sp)
	ldw	x, (0x26, sp)
	ld	(x), a
;	decoder.c: 381: return 1;
	ld	a, #0x01
	jp	00124$
00116$:
;	decoder.c: 383: if (s->n >= NB) { s->src_done = 1; break; }
	ldw	x, (0x1a, sp)
	ldw	x, (x)
	ldw	(0x37, sp), x
	cpw	x, #0x01c0
	jrc	00118$
	ldw	x, (0x1e, sp)
	ld	a, #0x01
	ld	(x), a
	jra	00121$
00118$:
;	decoder.c: 384: base = (uint32_t)BIAS_U + (uint32_t)s->n * BIT_U;
	ldw	y, (0x37, sp)
	clrw	x
	clr	a
	sll	a
	rlcw	y
	rlcw	x
	ld	(0x32, sp), a
	addw	y, #0x0002
	ldw	(0x30, sp), y
	ld	a, xl
	adc	a, #0x00
	ld	(0x2f, sp), a
;	decoder.c: 385: s->pend = 1;
	ldw	x, (0x20, sp)
	ld	a, #0x01
	ld	(x), a
;	decoder.c: 386: s->p_k0 = s->n;
	ldw	x, (0x1a, sp)
	ldw	x, (x)
	ldw	y, (0x1c, sp)
	ldw	(y), x
;	decoder.c: 387: s->p_u = (int16_t)((int32_t)yfa - (int32_t)base);
	ldw	y, (0x31, sp)
	ldw	(0x37, sp), y
	ldw	y, (0x33, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x22, sp)
	ldw	(x), y
;	decoder.c: 388: s->p_v = (int16_t)((int32_t)yfb - (int32_t)base);
	ldw	y, (0x35, sp)
	subw	y, (0x37, sp)
	ldw	x, (0x24, sp)
	ldw	(x), y
;	decoder.c: 389: s->p_fam = p.sfa;
	ld	a, (0x15, sp)
	ldw	x, (0x26, sp)
	ld	(x), a
	jp	00119$
00121$:
;	decoder.c: 391: if (s->pend) {
	ldw	x, (0x20, sp)
	ld	a, (x)
	jreq	00123$
;	decoder.c: 392: s->pend = 0;
	ldw	x, (0x20, sp)
	clr	(x)
;	decoder.c: 393: out->k0 = s->p_k0; out->k1 = NB;
	ldw	x, (0x1c, sp)
	ldw	x, (x)
	ldw	y, (0x28, sp)
	ldw	(y), x
	ldw	x, (0x2a, sp)
	ldw	y, #0x01c0
	ldw	(x), y
;	decoder.c: 394: out->u = s->p_u; out->v = s->p_v; out->fam = s->p_fam;
	ldw	x, (0x22, sp)
	ldw	x, (x)
	ldw	y, (0x2c, sp)
	ldw	(y), x
	ldw	x, (0x24, sp)
	ldw	x, (x)
	ldw	y, (0x2e, sp)
	ldw	(y), x
	ldw	x, (0x26, sp)
	ld	a, (x)
	ldw	x, (0x30, sp)
	ld	(x), a
;	decoder.c: 395: return 1;
	ld	a, #0x01
;	decoder.c: 397: return 0;
	.byte 0x21
00123$:
	clr	a
00124$:
;	decoder.c: 398: }
	ldw	x, (59, sp)
	addw	sp, #62
	jp	(x)
;	decoder.c: 402: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
;	-----------------------------------------
;	 function a_bounds
;	-----------------------------------------
_a_bounds:
	sub	sp, #12
	ldw	(0x09, sp), x
;	decoder.c: 404: uint16_t t, e = (k1 < NB) ? k1 : NB;
	ldw	x, (0x0f, sp)
	cpw	x, #0x01c0
	jrc	00117$
	ldw	x, #0x01c0
00117$:
	ldw	(0x01, sp), x
;	decoder.c: 405: *amin = 0;
	ldw	y, (0x11, sp)
	ldw	(0x03, sp), y
	ldw	x, y
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 406: *amax = (int16_t)(k1 - k0);
	ldw	y, (0x13, sp)
	ldw	(0x05, sp), y
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x05, sp)
	ldw	(x), y
;	decoder.c: 407: for (t = k0; t < e; t++) {
	ldw	y, (0x09, sp)
	ldw	(0x0b, sp), y
00112$:
;	decoder.c: 408: int8_t kb = known_bit(t);
	ldw	x, (0x0b, sp)
	cpw	x, (0x01, sp)
	jrnc	00114$
	call	_known_bit
;	decoder.c: 410: int16_t m = (int16_t)(t - k0 + 1);
	ldw	y, (0x0b, sp)
	subw	y, (0x09, sp)
;	decoder.c: 409: if (kb == 1) {
	cp	a, #0x01
	jrne	00108$
;	decoder.c: 410: int16_t m = (int16_t)(t - k0 + 1);
	ldw	(0x07, sp), y
	ldw	x, y
	incw	x
;	decoder.c: 411: if (m > *amin) *amin = m;
	ldw	y, (0x03, sp)
	ldw	y, (y)
	ldw	(0x07, sp), y
	cpw	x, (0x07, sp)
	jrsle	00113$
	ldw	y, (0x03, sp)
	ldw	(y), x
	jra	00113$
00108$:
;	decoder.c: 412: } else if (kb == 0) {
	tnz	a
	jrne	00113$
;	decoder.c: 413: int16_t m = (int16_t)(t - k0);
;	decoder.c: 414: if (m < *amax) *amax = m;
	ldw	x, (0x05, sp)
	ldw	x, (x)
	ldw	(0x07, sp), x
	exgw	x, y
	cpw	x, (0x07, sp)
	exgw	x, y
	jrsge	00113$
	ldw	x, (0x05, sp)
	ldw	(x), y
00113$:
;	decoder.c: 407: for (t = k0; t < e; t++) {
	ldw	x, (0x0b, sp)
	incw	x
	ldw	(0x0b, sp), x
	jra	00112$
00114$:
;	decoder.c: 417: }
	ldw	x, (13, sp)
	addw	sp, #20
	jp	(x)
;	decoder.c: 422: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function label_interval
;	-----------------------------------------
_label_interval:
	sub	sp, #10
;	decoder.c: 425: int16_t L = (int16_t)(k1 - k0);
	negw	x
	addw	x, (0x0d, sp)
	ldw	(0x09, sp), x
;	decoder.c: 427: if (a == 0) { *lo = u; *hi = v; return 0; }
	ldw	y, (0x17, sp)
	ldw	(0x01, sp), y
	ldw	x, (0x13, sp)
	jrne	00102$
	ldw	x, (0x15, sp)
	ldw	y, (0x0f, sp)
	ldw	(x), y
	ldw	x, (0x01, sp)
	ldw	y, (0x11, sp)
	ldw	(x), y
	clr	a
	jp	00113$
00102$:
;	decoder.c: 428: if (a == L) {
	ldw	x, (0x13, sp)
	cpw	x, (0x09, sp)
	jrne	00104$
;	decoder.c: 429: off = (int16_t)((L - 1) * BIT_U);
	ldw	x, (0x09, sp)
	decw	x
	clr	a
	rlwa	x
	sllw	x
	ldw	(0x09, sp), x
;	decoder.c: 430: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	decoder.c: 431: return 1;
	ld	a, #0x01
	jp	00113$
00104$:
;	decoder.c: 433: mid = (int16_t)((u + v) >> 1);
	ldw	y, (0x0f, sp)
	addw	y, (0x11, sp)
	sraw	y
;	decoder.c: 434: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
	ldw	x, (0x13, sp)
	ldw	(0x09, sp), x
	decw	x
	exg	a, xl
	ld	(0x03, sp), a
	exg	a, xl
	clr	(0x04, sp)
	sll	(0x04, sp)
	rlc	(0x03, sp)
	ldw	x, (0x03, sp)
	addw	x, #0x0134
	ldw	(0x07, sp), x
	ldw	x, y
	subw	x, (0x07, sp)
;	decoder.c: 435: if (d1 < 0) d1 = (int16_t)-d1;
	ldw	(0x07, sp), x
	tnzw	x
	jrpl	00106$
	neg	(0x08, sp)
	clr	a
	sbc	a, (0x07, sp)
	ld	(0x07, sp), a
00106$:
;	decoder.c: 436: d0 = (int16_t)(mid - (a * BIT_U + H0P));
	ld	a, (0x0a, sp)
	ld	(0x05, sp), a
	clr	(0x06, sp)
	sll	(0x06, sp)
	rlc	(0x05, sp)
	ldw	x, (0x05, sp)
	addw	x, #0x009a
	ldw	(0x09, sp), x
	subw	y, (0x09, sp)
;	decoder.c: 437: if (d0 < 0) d0 = (int16_t)-d0;
	ldw	(0x09, sp), y
	ldw	x, y
	tnzw	x
	jrpl	00108$
	neg	(0x0a, sp)
	clr	a
	sbc	a, (0x09, sp)
	ld	(0x09, sp), a
00108$:
;	decoder.c: 438: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
	ldw	x, (0x09, sp)
	cpw	x, (0x07, sp)
	jrsge	00115$
	ldw	x, (0x09, sp)
	.byte 0xc5
00115$:
	ldw	x, (0x07, sp)
00116$:
	cpw	x, #0x00f6
	jrsle	00110$
	ld	a, #0xff
	jra	00113$
00110$:
;	decoder.c: 439: if (d1 <= d0) {
	ldw	x, (0x07, sp)
	cpw	x, (0x09, sp)
	jrsgt	00112$
;	decoder.c: 440: off = (int16_t)((a - 1) * BIT_U);
	ldw	y, (0x03, sp)
	ldw	(0x09, sp), y
;	decoder.c: 441: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	decoder.c: 442: return 1;
	ld	a, #0x01
	jra	00113$
00112$:
;	decoder.c: 444: off = (int16_t)(a * BIT_U);
	ldw	y, (0x05, sp)
	ldw	(0x09, sp), y
;	decoder.c: 445: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	decoder.c: 446: return 0;
	clr	a
00113$:
;	decoder.c: 447: }
	ldw	x, (11, sp)
	addw	sp, #24
	jp	(x)
;	decoder.c: 449: static void cal_cloud(int16_t u, uint8_t fam)
;	-----------------------------------------
;	 function cal_cloud
;	-----------------------------------------
_cal_cloud:
	pushw	x
;	decoder.c: 453: if (fam != 5 && fam != 6) return;
	cp	a, #0x05
	jreq	00102$
	cp	a, #0x06
	jrne	00111$
00102$:
;	decoder.c: 454: if (u < 0) return;
	tnzw	x
	jrmi	00111$
;	decoder.c: 455: f = (uint8_t)(fam - 5);
	sub	a, #0x05
	ld	yl, a
;	decoder.c: 456: x = (int16_t)(u & (BIT_U - 1));
	ld	a, xh
	and	a, #0x01
	ld	xh, a
	ldw	(0x01, sp), x
;	decoder.c: 457: d = (int16_t)(x - c_c0[f]);
	ldw	x, y
	clr	a
	ld	xh, a
	sllw	x
	ldw	x, (_c_c0+0, x)
	negw	x
	addw	x, (0x01, sp)
;	decoder.c: 458: if (d >= -EPS_HIST && d < EPS_HIST) {
	cpw	x, #0xffc0
	jrslt	00111$
	cpw	x, #0x0040
	jrsge	00111$
;	decoder.c: 459: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
	addw	x, #0x0040
	sraw	x
;	decoder.c: 460: if (c_hist[f][b] < 255) c_hist[f][b]++;
	ld	a, #0x40
	mul	y, a
	addw	y, #(_c_hist+0)
	ldw	(0x01, sp), y
	clr	a
	ld	xh, a
	addw	x, (0x01, sp)
	ld	a, (x)
	cp	a, #0xff
	jrnc	00111$
	inc	a
	ld	(x), a
00111$:
;	decoder.c: 462: }
	popw	x
	ret
;	decoder.c: 464: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function cal_add
;	-----------------------------------------
_cal_add:
	sub	sp, #12
	exgw	x, y
;	decoder.c: 468: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, (0x1a, sp)
	pushw	x
	ldw	x, (0x19, sp)
	pushw	x
	ldw	x, (0x19, sp)
	pushw	x
	ldw	x, (0x19, sp)
	pushw	x
	ldw	x, y
	call	_label_interval
;	decoder.c: 469: if (cls < 0) return;
	ld	(0x0a, sp), a
	jrpl	00102$
	jp	00138$
00102$:
;	decoder.c: 471: if (lo > c_lo0) c_lo0 = lo;
	ldw	x, (0x01, sp)
;	decoder.c: 472: if (hi < c_hi0) c_hi0 = hi;
	ldw	y, (0x03, sp)
;	decoder.c: 470: if (cls == 0) {
	tnz	(0x0a, sp)
	jrne	00116$
;	decoder.c: 471: if (lo > c_lo0) c_lo0 = lo;
	pushw	x
	ldw	x, (0x03, sp)
	cpw	x, _c_lo0+0
	popw	x
	jrsle	00104$
	ldw	_c_lo0+0, x
00104$:
;	decoder.c: 472: if (hi < c_hi0) c_hi0 = hi;
	ldw	x, (0x03, sp)
	cpw	x, _c_hi0+0
	jrsge	00106$
	ldw	_c_hi0+0, y
00106$:
;	decoder.c: 473: if (c_n0 < 255) c_n0++;
	ld	a, _c_n0+0
	cp	a, #0xff
	jrnc	00117$
	inc	_c_n0+0
	jra	00117$
00116$:
;	decoder.c: 475: if (lo > c_lo1) c_lo1 = lo;
	pushw	x
	ldw	x, (0x03, sp)
	cpw	x, _c_lo1+0
	popw	x
	jrsle	00110$
	ldw	_c_lo1+0, x
00110$:
;	decoder.c: 476: if (hi < c_hi1) c_hi1 = hi;
	ldw	x, (0x03, sp)
	cpw	x, _c_hi1+0
	jrsge	00112$
	ldw	_c_hi1+0, y
00112$:
;	decoder.c: 477: if (c_n1 < 255) c_n1++;
	ld	a, _c_n1+0
	cp	a, #0xff
	jrnc	00117$
	inc	_c_n1+0
00117$:
;	decoder.c: 479: if ((fam == 5 || fam == 6) && lo >= 0) {
	ld	a, (0x15, sp)
	cp	a, #0x05
	jreq	00137$
	ld	a, (0x15, sp)
	cp	a, #0x06
	jreq	00289$
	jp	00138$
00289$:
00137$:
	ldw	y, (0x01, sp)
	jrpl	00290$
	jp	00138$
00290$:
;	decoder.c: 480: uint8_t f = (uint8_t)(fam - 5);
	ld	a, (0x15, sp)
	sub	a, #0x05
	ld	xl, a
;	decoder.c: 481: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
	ld	a, yh
	and	a, #0x01
	ld	yh, a
	clr	a
	ld	xh, a
	sllw	x
	ldw	(0x05, sp), x
	ldw	x, (_c_c0+0, x)
	ldw	(0x0b, sp), x
	ldw	x, y
	subw	x, (0x0b, sp)
;	decoder.c: 482: if (d >= -EPS_HIST && d < EPS_HIST) {
	ldw	(0x07, sp), x
	cpw	x, #0xffc0
	jrslt	00138$
	ldw	x, (0x07, sp)
	cpw	x, #0x0040
	jrsge	00138$
;	decoder.c: 483: if (cls == 0) {
	tnz	(0x0a, sp)
	jrne	00129$
;	decoder.c: 484: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
	ldw	x, (0x05, sp)
	addw	x, #(_c_labx0+0)
	ldw	(0x0b, sp), x
	ldw	x, (x)
	cpw	x, (0x07, sp)
	jrsge	00121$
	ldw	y, (0x05, sp)
	ldw	((_c_labx0b+0), y), x
	ldw	x, (0x0b, sp)
	ldw	y, (0x07, sp)
	ldw	(x), y
	jra	00138$
00121$:
;	decoder.c: 485: else if (d > c_labx0b[f]) c_labx0b[f] = d;
	ldw	y, (0x05, sp)
	addw	y, #(_c_labx0b+0)
	ldw	x, y
	ldw	x, (x)
	cpw	x, (0x07, sp)
	jrsge	00138$
	ldw	x, y
	ldw	y, (0x07, sp)
	ldw	(x), y
	jra	00138$
00129$:
;	decoder.c: 487: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
	ldw	x, (0x05, sp)
	addw	x, #(_c_labx1+0)
	ldw	(0x09, sp), x
	ldw	x, (x)
	ldw	(0x0b, sp), x
	ldw	x, (0x07, sp)
	cpw	x, (0x0b, sp)
	jrsge	00126$
	ldw	x, (0x05, sp)
	ldw	y, (0x0b, sp)
	ldw	((_c_labx1b+0), x), y
	ldw	x, (0x09, sp)
	ldw	y, (0x07, sp)
	ldw	(x), y
	jra	00138$
00126$:
;	decoder.c: 488: else if (d < c_labx1b[f]) c_labx1b[f] = d;
	ldw	y, (0x05, sp)
	addw	y, #(_c_labx1b+0)
	ldw	x, y
	ldw	x, (x)
	ldw	(0x0b, sp), x
	ldw	x, (0x07, sp)
	cpw	x, (0x0b, sp)
	jrsge	00138$
	ldw	x, y
	ldw	y, (0x07, sp)
	ldw	(x), y
00138$:
;	decoder.c: 492: }
	ldw	x, (13, sp)
	addw	sp, #23
	jp	(x)
;	decoder.c: 495: static uint8_t theta56(uint8_t f, int16_t *theta_out)
;	-----------------------------------------
;	 function theta56
;	-----------------------------------------
_theta56:
	sub	sp, #38
	ldw	(0x23, sp), x
;	decoder.c: 497: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	(0x01, sp), x
	ldw	x, (_c_labx0+0, x)
	ldw	y, (0x01, sp)
	ldw	y, (_c_labx1+0, y)
;	decoder.c: 498: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
	ldw	(0x03, sp), x
	cpw	x, #0xc000
	jrsgt	00483$
	clr	(0x05, sp)
	jra	00484$
00483$:
	push	a
	ld	a, #0x01
	ld	(0x06, sp), a
	pop	a
00484$:
	ldw	(0x06, sp), y
	ldw	x, y
	cpw	x, #0x3fff
	jrslt	00485$
	clr	(0x08, sp)
	jra	00486$
00485$:
	push	a
	ld	a, #0x01
	ld	(0x09, sp), a
	pop	a
00486$:
;	decoder.c: 499: int16_t zlo = (int16_t)(x0 + 1);
	ldw	x, (0x03, sp)
	incw	x
	ldw	(0x09, sp), x
;	decoder.c: 500: int16_t zhi = x1;
	ldw	(0x0b, sp), y
;	decoder.c: 501: int16_t theta = 0;
	clrw	x
	ldw	(0x0d, sp), x
;	decoder.c: 502: uint8_t have_theta = 0;
	clr	(0x0f, sp)
;	decoder.c: 503: int16_t top = 0;
	clrw	x
	ldw	(0x10, sp), x
;	decoder.c: 504: uint8_t have_top = 0, clear1 = 0;
	clr	(0x12, sp)
	clr	(0x13, sp)
;	decoder.c: 506: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
	ldw	x, #0xffe0
	cpw	x, (0x09, sp)
	jrslt	00102$
	ldw	(0x09, sp), x
00102$:
;	decoder.c: 507: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
	ldw	x, (0x0b, sp)
	cpw	x, #0x0020
	jrsle	00104$
	ldw	x, #0x0020
	ldw	(0x0b, sp), x
00104$:
;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
	exg	a, xl
	ld	a, #0x40
	exg	a, xl
	mul	x, a
	ldw	(0x14, sp), x
;	decoder.c: 508: if (zlo < zhi) {
	ldw	x, (0x09, sp)
	cpw	x, (0x0b, sp)
	jrslt	00489$
	jp	00126$
00489$:
;	decoder.c: 509: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
	ldw	x, (0x09, sp)
	addw	x, #0x0040
	sraw	x
	exg	a, xl
	ld	(0x25, sp), a
	exg	a, xl
;	decoder.c: 510: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
	ldw	x, (0x0b, sp)
	addw	x, #0x003f
	sraw	x
	exg	a, xl
	ld	(0x16, sp), a
	exg	a, xl
;	decoder.c: 512: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
	ldw	y, (0x09, sp)
	ldw	(0x17, sp), y
	clrw	x
	ldw	(0x19, sp), x
	clrw	x
	ldw	(0x1b, sp), x
	clrw	x
	decw	x
	ldw	(0x1d, sp), x
;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
	ldw	x, (0x14, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x1f, sp), x
	clr	(0x26, sp)
00170$:
	ld	a, (0x25, sp)
	cp	a, (0x16, sp)
	jrugt	00253$
;	decoder.c: 515: if (c_hist[f][b]) {
	clrw	x
	ld	a, (0x25, sp)
	ld	xl, a
	addw	x, (0x1f, sp)
	ld	a, (x)
	jreq	00171$
;	decoder.c: 516: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
	ld	a, (0x25, sp)
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #0xffc1
;	decoder.c: 517: int16_t gp = (int16_t)(x - prev);
	ldw	(0x21, sp), x
	subw	x, (0x17, sp)
;	decoder.c: 518: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
	cpw	x, (0x1d, sp)
	jrsle	00106$
	ldw	(0x1d, sp), x
	ldw	y, (0x17, sp)
	ldw	(0x19, sp), y
	ldw	y, (0x21, sp)
	ldw	(0x1b, sp), y
00106$:
;	decoder.c: 519: prev = x;
	ldw	y, (0x21, sp)
	ldw	(0x17, sp), y
;	decoder.c: 520: nocc++;
	inc	(0x26, sp)
00171$:
;	decoder.c: 514: for (b = blo; b <= bhi; b++) {
	inc	(0x25, sp)
	jra	00170$
00253$:
	ld	a, (0x26, sp)
	ld	xl, a
;	decoder.c: 524: int16_t gp = (int16_t)(zhi - prev);
	ldw	y, (0x0b, sp)
	subw	y, (0x17, sp)
;	decoder.c: 525: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
	exgw	x, y
	cpw	x, (0x1d, sp)
	exgw	x, y
	jrsle	00111$
	ldw	(0x1d, sp), y
	ldw	y, (0x17, sp)
	ldw	(0x19, sp), y
	ldw	y, (0x0b, sp)
	ldw	(0x1b, sp), y
00111$:
;	decoder.c: 527: if (nocc == 0) {
	ld	a, xl
	tnz	a
	jrne	00123$
;	decoder.c: 528: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
	tnz	(0x05, sp)
	jrne	00495$
	jp	00126$
00495$:
	tnz	(0x08, sp)
	jrne	00496$
	jp	00126$
00496$:
	ldw	x, (0x09, sp)
	addw	x, (0x0b, sp)
	sraw	x
	ldw	(0x0d, sp), x
	ld	a, #0x01
	ld	(0x0f, sp), a
	jp	00126$
00123$:
;	decoder.c: 530: uint8_t ok = (bg >= EPS_GAP_MIN);
	ldw	y, (0x1d, sp)
	cpw	y, #0x0005
	jrslt	00497$
	clr	a
	.byte 0xc5
00497$:
	ld	a, #0x01
00498$:
	xor	a, #0x01
;	decoder.c: 531: if (ok && (uint8_t)(nocc + 1) >= 4) {
	ld	(0x26, sp), a
	jreq	00118$
	ld	a, xl
	inc	a
	cp	a, #0x04
	jrc	00118$
;	decoder.c: 533: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
	ldw	y, (0x1d, sp)
	ld	a, yh
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	rlwa	x
	ld	(0x20, sp), a
	rrwa	x
	ld	(0x1f, sp), a
	sllw	y
	rlc	(0x20, sp)
	rlc	(0x1f, sp)
	ldw	(0x21, sp), y
	clr	a
	ld	xh, a
	incw	x
	clrw	y
	tnzw	x
	jrpl	00501$
	decw	y
00501$:
	pushw	x
	pushw	y
	ldw	x, (0x25, sp)
	pushw	x
	ldw	x, (0x25, sp)
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x21, sp), x
	ldw	(0x1f, sp), y
	ldw	x, (0x0b, sp)
	subw	x, (0x09, sp)
	pushw	x
	ldw	x, #0x0005
	call	___mulsint2slong
	addw	sp, #2
	ldw	(0x0b, sp), x
	ldw	(0x09, sp), y
	ldw	x, (0x21, sp)
	cpw	x, (0x0b, sp)
	ld	a, (0x20, sp)
	sbc	a, (0x0a, sp)
	ld	a, (0x1f, sp)
	sbc	a, (0x09, sp)
	jrsge	00118$
;	decoder.c: 534: ok = 0;
	clr	(0x26, sp)
00118$:
;	decoder.c: 536: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
	tnz	(0x26, sp)
	jreq	00126$
	ldw	x, (0x19, sp)
	addw	x, (0x1b, sp)
	sraw	x
	ldw	(0x0d, sp), x
	ld	a, #0x01
	ld	(0x0f, sp), a
00126$:
;	decoder.c: 539: if (has0 || has1) {
	tnz	(0x05, sp)
	jrne	00144$
	tnz	(0x08, sp)
	jrne	00505$
	jp	00245$
00505$:
00144$:
;	decoder.c: 540: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
	ldw	x, #0xffe0
	ldw	(0x21, sp), x
	ldw	x, #0x0020
	ldw	(0x25, sp), x
;	decoder.c: 541: if (has0) {
	tnz	(0x05, sp)
	jreq	00131$
;	decoder.c: 542: wlo = (int16_t)(x0 - EPS_SLACK1);
	ldw	x, (0x03, sp)
	subw	x, #0x0008
	ldw	(0x21, sp), x
;	decoder.c: 543: if (c_labx0b[f] > -0x4000 &&
	ldw	x, (0x01, sp)
	ldw	x, (_c_labx0b+0, x)
	cpw	x, #0xc000
	jrsle	00131$
;	decoder.c: 544: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
	decw	x
	decw	x
	cpw	x, (0x21, sp)
	jrsle	00131$
;	decoder.c: 545: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
	ldw	(0x21, sp), x
00131$:
;	decoder.c: 547: if (has1) {
	tnz	(0x08, sp)
	jreq	00136$
;	decoder.c: 548: whi = (int16_t)(x1 + EPS_SLACK1);
	ldw	x, (0x06, sp)
	addw	x, #0x0008
	ldw	(0x25, sp), x
;	decoder.c: 549: if (c_labx1b[f] < 0x3FFF &&
	ldw	x, (0x01, sp)
	ldw	x, (_c_labx1b+0, x)
	cpw	x, #0x3fff
	jrsge	00136$
;	decoder.c: 550: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
	incw	x
	incw	x
	cpw	x, (0x25, sp)
	jrsge	00136$
;	decoder.c: 551: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
	ldw	(0x25, sp), x
00136$:
;	decoder.c: 553: if (wlo > whi) {
;	decoder.c: 554: theta = (int16_t)((wlo + whi) >> 1);
	ldw	x, (0x21, sp)
	cpw	x, (0x25, sp)
	jrsle	00142$
	addw	x, (0x25, sp)
	sraw	x
	ldw	(0x0d, sp), x
;	decoder.c: 555: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
	jra	00245$
00142$:
;	decoder.c: 557: int16_t th = have_theta ? theta : 0;
	tnz	(0x0f, sp)
	jreq	00175$
	ldw	y, (0x0d, sp)
	ldw	(0x1f, sp), y
	.byte 0xbc
00175$:
	clrw	x
	ldw	(0x1f, sp), x
00176$:
;	decoder.c: 558: if (th < wlo) th = wlo;
	ldw	x, (0x1f, sp)
	cpw	x, (0x21, sp)
	jrsge	00138$
	ldw	y, (0x21, sp)
	ldw	(0x1f, sp), y
00138$:
;	decoder.c: 559: if (th > whi) th = whi;
	ldw	x, (0x1f, sp)
	cpw	x, (0x25, sp)
	jrsle	00140$
	ldw	y, (0x25, sp)
	ldw	(0x1f, sp), y
00140$:
;	decoder.c: 560: theta = th;
	ldw	y, (0x1f, sp)
	ldw	(0x0d, sp), y
;	decoder.c: 561: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
;	decoder.c: 564: for (b = 0; b < 64; b++) {
00245$:
	ldw	x, (0x14, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x21, sp), x
	clr	(0x26, sp)
00172$:
;	decoder.c: 566: if (!c_hist[f][b]) continue;
	clrw	x
	ld	a, (0x26, sp)
	ld	xl, a
	addw	x, (0x21, sp)
	ld	a, (x)
	jreq	00157$
;	decoder.c: 567: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
	ld	a, (0x26, sp)
	clrw	x
	sll	a
	rlcw	x
	add	a, #0xc1
	ld	(0x20, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x1f, sp), a
;	decoder.c: 568: if (d > EPS_CLEAR1) clear1 = 1;
	ld	a, (0x20, sp)
	cp	a, #0x12
	jrsle	00155$
	ld	a, #0x01
	ld	(0x13, sp), a
	jra	00157$
00155$:
;	decoder.c: 569: else if (d > -EPS_CLAMP56) {
	ldw	x, (0x1f, sp)
	cpw	x, #0xffe8
	jrsle	00157$
;	decoder.c: 570: if (!have_top || d > top) top = d;
	tnz	(0x12, sp)
	jreq	00149$
	ldw	x, (0x1f, sp)
	cpw	x, (0x10, sp)
	jrsle	00150$
00149$:
	ldw	y, (0x1f, sp)
	ldw	(0x10, sp), y
00150$:
;	decoder.c: 571: have_top = 1;
	ld	a, #0x01
	ld	(0x12, sp), a
00157$:
;	decoder.c: 564: for (b = 0; b < 64; b++) {
	inc	(0x26, sp)
	ld	a, (0x26, sp)
	cp	a, #0x40
	jrc	00172$
;	decoder.c: 574: if (!clear1 && have_top) {
	tnz	(0x13, sp)
	jrne	00167$
	tnz	(0x12, sp)
	jreq	00167$
;	decoder.c: 575: int16_t floor_ = (int16_t)(top + EPS_TOPM);
	ld	a, (0x11, sp)
	add	a, #0x03
	ld	(0x26, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x25, sp), a
;	decoder.c: 576: if (!have_theta || floor_ > theta) theta = floor_;
	tnz	(0x0f, sp)
	jreq	00159$
	ldw	x, (0x25, sp)
	cpw	x, (0x0d, sp)
	jrsle	00160$
00159$:
	ldw	y, (0x25, sp)
	ldw	(0x0d, sp), y
00160$:
;	decoder.c: 577: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
;	decoder.c: 578: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
	tnz	(0x08, sp)
	jreq	00167$
	ldw	x, (0x06, sp)
	incw	x
	incw	x
	cpw	x, (0x25, sp)
	jrsle	00167$
;	decoder.c: 579: theta > (int16_t)(x1 + EPS_SLACK))
	cpw	x, (0x0d, sp)
	jrsge	00167$
;	decoder.c: 580: theta = (int16_t)(x1 + EPS_SLACK);
	ldw	(0x0d, sp), x
00167$:
;	decoder.c: 582: *theta_out = theta;
	ldw	x, (0x23, sp)
	ldw	y, (0x0d, sp)
	ldw	(x), y
;	decoder.c: 583: return have_theta;
	ld	a, (0x0f, sp)
;	decoder.c: 584: }
	addw	sp, #38
	ret
;	decoder.c: 586: static void calibrate(const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function calibrate
;	-----------------------------------------
_calibrate:
	sub	sp, #69
	ldw	(0x44, sp), x
;	decoder.c: 591: c_lo0 = c_lo1 = -0x4000;
	ldw	x, #0xc000
	ldw	_c_lo1+0, x
	ldw	x, #0xc000
	ldw	_c_lo0+0, x
;	decoder.c: 592: c_hi0 = c_hi1 = 0x3FFF;
	ldw	x, #0x3fff
	ldw	_c_hi1+0, x
	ldw	x, #0x3fff
	ldw	_c_hi0+0, x
;	decoder.c: 593: c_n0 = c_n1 = 0;
	clr	_c_n1+0
	clr	_c_n0+0
;	decoder.c: 594: c_h0c = H0P; c_h1c = H1P;
	ldw	x, #0x009a
	ldw	_c_h0c+0, x
	ldw	x, #0x0134
	ldw	_c_h1c+0, x
;	decoder.c: 595: c_d56[0] = c_d56[1] = 0;
	mov	_c_d56+1, #0x00
	mov	_c_d56+0, #0x00
;	decoder.c: 596: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
	ldw	x, _g_K+0
	pushw	x
	ldw	x, #0x0006
	call	___muluint2ulong
	addw	sp, #2
	ld	a, #0x0b
00403$:
	srlw	y
	rrcw	x
	dec	a
	jrne	00403$
	ldw	_c_gap56+0, x
;	decoder.c: 597: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
	ldw	x, _g_K+0
	pushw	x
	ldw	x, #0x0005
	call	___muluint2ulong
	addw	sp, #2
	ld	a, #0x0b
00405$:
	srlw	y
	rrcw	x
	dec	a
	jrne	00405$
	ldw	_c_gap56+2, x
;	decoder.c: 598: for (f = 0; f < 2; f++) {
	clr	(0x43, sp)
00138$:
;	decoder.c: 600: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
	clrw	x
	ld	a, (0x43, sp)
	ld	xl, a
	sllw	x
	ldw	(0x3f, sp), x
	ldw	y, x
	addw	y, #(_c_c0+0)
	ldw	x, (0x3f, sp)
	ldw	x, (_c_gap56+0, x)
	ldw	(0x41, sp), x
	ldw	x, #0x01ce
	subw	x, (0x41, sp)
	sraw	x
	ldw	(y), x
;	decoder.c: 601: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
	ld	a, (0x43, sp)
	ld	xl, a
	ld	a, #0x40
	mul	x, a
	addw	x, #(_c_hist+0)
	ldw	(0x41, sp), x
	clr	a
00136$:
	clrw	x
	ld	xl, a
	addw	x, (0x41, sp)
	clr	(x)
	inc	a
	cp	a, #0x40
	jrc	00136$
;	decoder.c: 602: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
	ldw	x, (0x3f, sp)
	addw	x, #(_c_labx0+0)
	clr	(0x1, x)
	ld	a, #0xc0
	ld	(x), a
	ldw	x, (0x3f, sp)
	addw	x, #(_c_labx0b+0)
	clr	(0x1, x)
	ld	a, #0xc0
	ld	(x), a
;	decoder.c: 603: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
	ldw	x, (0x3f, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1+0), x), y
	ldw	x, (0x3f, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1b+0), x), y
;	decoder.c: 598: for (f = 0; f < 2; f++) {
	inc	(0x43, sp)
	ld	a, (0x43, sp)
	cp	a, #0x02
	jrc	00138$
;	decoder.c: 605: ss_init(&ss, cap, ncap);
	ldw	x, (0x48, sp)
	pushw	x
	ldw	x, (0x46, sp)
	pushw	x
	ldw	x, sp
	addw	x, #5
	call	_ss_init
;	decoder.c: 606: while (ss_next(&ss, &sg)) {
00112$:
	ldw	x, sp
	addw	x, #47
	pushw	x
	ldw	x, sp
	addw	x, #3
	call	_ss_next
	ld	(0x43, sp), a
	jrne	00409$
	jp	00114$
00409$:
;	decoder.c: 608: uint8_t known_all = 1;
	ld	a, #0x01
	ld	(0x41, sp), a
;	decoder.c: 610: cal_cloud(sg.u, sg.fam);
	ld	a, (0x37, sp)
	ldw	x, (0x33, sp)
	call	_cal_cloud
;	decoder.c: 611: if (sg.k1 > NB) continue;
	ldw	x, (0x31, sp)
	cpw	x, #0x01c0
	jrugt	00112$
;	decoder.c: 612: e = (sg.k1 < NB) ? sg.k1 : NB;
	cpw	x, #0x01c0
	jrnc	00146$
	ldw	(0x42, sp), x
	jra	00147$
00146$:
	ldw	x, #0x01c0
	ldw	(0x42, sp), x
00147$:
;	decoder.c: 613: for (t = sg.k0; t < e; t++)
	ldw	x, sp
	addw	x, #47
	ldw	(0x3c, sp), x
	ldw	x, (x)
00141$:
	cpw	x, (0x42, sp)
	jrnc	00107$
;	decoder.c: 614: if (known_bit(t) < 0) { known_all = 0; break; }
	pushw	x
	call	_known_bit
	popw	x
	tnz	a
	jrpl	00142$
	clr	(0x41, sp)
	jra	00107$
00142$:
;	decoder.c: 613: for (t = sg.k0; t < e; t++)
	incw	x
	jra	00141$
00107$:
;	decoder.c: 615: if (!known_all) continue;
	tnz	(0x41, sp)
	jreq	00112$
;	decoder.c: 616: a_bounds(sg.k0, sg.k1, &amin, &amax);
	ldw	y, (0x31, sp)
	ldw	x, (0x3c, sp)
	ldw	x, (x)
	ldw	(0x42, sp), x
	ldw	x, sp
	addw	x, #58
	pushw	x
	ldw	x, sp
	addw	x, #58
	pushw	x
	pushw	y
	ldw	x, (0x48, sp)
	call	_a_bounds
;	decoder.c: 617: if (amin == amax)
	ldw	x, (0x38, sp)
	cpw	x, (0x3a, sp)
	jrne	00112$
;	decoder.c: 618: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
	ld	a, (0x37, sp)
	ldw	y, (0x35, sp)
	ldw	(0x3e, sp), y
	ldw	y, (0x33, sp)
	ldw	(0x40, sp), y
	ldw	y, (0x31, sp)
	ldw	x, (0x3c, sp)
	ldw	x, (x)
	ldw	(0x42, sp), x
	ldw	x, (0x38, sp)
	pushw	x
	push	a
	ldw	x, (0x41, sp)
	pushw	x
	ldw	x, (0x45, sp)
	pushw	x
	pushw	y
	ldw	x, (0x4b, sp)
	call	_cal_add
	jp	00112$
00114$:
;	decoder.c: 622: int16_t h0 = H0P, h1 = H1P;
	ldw	x, #0x009a
	ldw	(0x3e, sp), x
	ldw	x, #0x0134
	ldw	(0x40, sp), x
;	decoder.c: 623: if (c_n0 >= LAB_MIN) {
	ld	a, _c_n0+0
	cp	a, #0x03
	jrc	00119$
;	decoder.c: 624: int16_t h = (c_lo0 > c_hi0) ? (int16_t)((c_lo0 + c_hi0) >> 1)
	ldw	x, _c_hi0+0
	cpw	x, _c_lo0+0
	jrsge	00148$
	ldw	x, _c_lo0+0
	addw	x, _c_hi0+0
	sraw	x
	jra	00149$
00148$:
	ldw	x, _c_lo0+0
	cpw	x, #0x009a
	jrsgt	00151$
	ldw	x, _c_hi0+0
	cpw	x, #0x009a
	jrsge	00152$
	ldw	x, _c_hi0+0
	ldw	(0x42, sp), x
	jra	00153$
00152$:
	ldw	x, #0x009a
	ldw	(0x42, sp), x
00153$:
	ldw	x, (0x42, sp)
00151$:
00149$:
;	decoder.c: 626: if (h >= H0_LO && h <= H0_HI) h0 = h;
	ldw	y, x
	cpw	x, #0x0070
	jrslt	00119$
	cpw	x, #0x00c0
	jrsgt	00119$
	ldw	(0x3e, sp), y
00119$:
;	decoder.c: 628: if (c_n1 >= LAB_MIN) {
	ld	a, _c_n1+0
	cp	a, #0x03
	jrc	00124$
;	decoder.c: 629: int16_t h = (c_lo1 > c_hi1) ? (int16_t)((c_lo1 + c_hi1) >> 1)
	ldw	x, _c_hi1+0
	cpw	x, _c_lo1+0
	jrsge	00154$
	ldw	x, _c_lo1+0
	addw	x, _c_hi1+0
	sraw	x
	jra	00155$
00154$:
	ldw	x, _c_lo1+0
	cpw	x, #0x0134
	jrsgt	00157$
	ldw	x, _c_hi1+0
	cpw	x, #0x0134
	jrsge	00158$
	ldw	x, _c_hi1+0
	ldw	(0x42, sp), x
	jra	00159$
00158$:
	ldw	x, #0x0134
	ldw	(0x42, sp), x
00159$:
	ldw	x, (0x42, sp)
00157$:
00155$:
;	decoder.c: 631: if (h >= H1_LO && h <= H1_HI) h1 = h;
	ldw	y, x
	cpw	x, #0x00fc
	jrslt	00124$
	cpw	x, #0x0178
	jrsgt	00124$
	ldw	(0x40, sp), y
00124$:
;	decoder.c: 633: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
	ldw	x, (0x40, sp)
	subw	x, (0x3e, sp)
	cpw	x, #0x0070
	jrslt	00125$
	cpw	x, #0x00c4
	jrsle	00126$
00125$:
	ldw	x, #0x009a
	ldw	(0x3e, sp), x
	ldw	x, #0x0134
	ldw	(0x40, sp), x
00126$:
;	decoder.c: 634: c_h0c = h0; c_h1c = h1;
	ldw	x, (0x3e, sp)
	ldw	_c_h0c+0, x
	ldw	x, (0x40, sp)
	ldw	_c_h1c+0, x
;	decoder.c: 636: for (f = 0; f < 2; f++) {
	clr	(0x43, sp)
00143$:
;	decoder.c: 638: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
	ldw	x, sp
	addw	x, #58
	ld	a, (0x43, sp)
	call	_theta56
	ld	(0x42, sp), a
	clrw	x
	ld	a, (0x43, sp)
	ld	xl, a
	addw	x, #(_c_d56+0)
	ldw	(0x3f, sp), x
	tnz	(0x42, sp)
	jrne	00129$
	ldw	x, (0x3f, sp)
	clr	(x)
	jra	00134$
00129$:
;	decoder.c: 639: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
	ldw	x, _c_h0c+0
	addw	x, _c_h1c+0
	ldw	(0x41, sp), x
	clrw	x
	ld	a, (0x43, sp)
	ld	xl, a
	sllw	x
	ldw	y, x
	ldw	x, (_c_gap56+0, x)
	negw	x
	addw	x, (0x41, sp)
	sraw	x
	ldw	(0x41, sp), x
;	decoder.c: 640: delta = (int16_t)(th + c_c0[f] - cfit);
	ldw	x, y
	ldw	x, (_c_c0+0, x)
	addw	x, (0x3a, sp)
	subw	x, (0x41, sp)
;	decoder.c: 641: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
	cpw	x, #0xffe8
	jrsge	00131$
	ldw	x, #0xffe8
00131$:
;	decoder.c: 642: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
	ldw	y, x
	cpw	y, #0x0018
	jrsle	00133$
	ldw	x, #0x0018
00133$:
;	decoder.c: 643: c_d56[f] = (int8_t)delta;
	ld	a, xl
	ldw	x, (0x3f, sp)
	ld	(x), a
00134$:
;	decoder.c: 636: for (f = 0; f < 2; f++) {
	inc	(0x43, sp)
	ld	a, (0x43, sp)
	cp	a, #0x02
	jrc	00143$
;	decoder.c: 645: }
	ldw	x, (70, sp)
	addw	sp, #73
	jp	(x)
;	decoder.c: 649: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
;	-----------------------------------------
;	 function hinge
;	-----------------------------------------
_hinge:
	pushw	x
	exgw	x, y
;	decoder.c: 651: int16_t g = 0;
	clrw	x
;	decoder.c: 652: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
	subw	y, (0x07, sp)
	cpw	y, #0x0000
	jrsle	00102$
	ldw	x, y
00102$:
;	decoder.c: 653: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
	ldw	y, (0x07, sp)
	subw	y, (0x05, sp)
	ldw	(0x01, sp), y
	cpw	x, (0x01, sp)
	jrsge	00104$
	ldw	x, (0x01, sp)
00104$:
;	decoder.c: 654: return (uint16_t)g;
;	decoder.c: 655: }
	ldw	y, (3, sp)
	addw	sp, #8
	jp	(y)
;	decoder.c: 658: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function decide
;	-----------------------------------------
_decide:
	sub	sp, #24
	ldw	(0x15, sp), x
;	decoder.c: 662: int16_t L = (int16_t)(k1 - k0);
	ldw	x, (0x1b, sp)
	subw	x, (0x15, sp)
;	decoder.c: 663: int16_t acap = (L < A_CAP) ? L : A_CAP;
	ldw	(0x05, sp), x
	cpw	x, #0x000f
	jrslt	00144$
	ldw	x, #0x000f
00144$:
	ldw	(0x07, sp), x
;	decoder.c: 664: int16_t h0e = c_h0c, h1e = c_h1c;
	ldw	x, _c_h0c+0
	ldw	(0x09, sp), x
	ldw	x, _c_h1c+0
	ldw	(0x0b, sp), x
;	decoder.c: 668: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
	ld	a, (0x21, sp)
	cp	a, #0x05
	jrne	00102$
	ld	a, _c_d56+0
	ld	(0x18, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x17, sp), a
	ldw	x, (0x09, sp)
	addw	x, (0x17, sp)
	ldw	(0x09, sp), x
	ldw	x, (0x0b, sp)
	addw	x, (0x17, sp)
	ldw	(0x0b, sp), x
00102$:
;	decoder.c: 669: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
	ld	a, (0x21, sp)
	cp	a, #0x06
	jrne	00104$
	ld	a, _c_d56+1
	ld	(0x18, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x17, sp), a
	ldw	x, (0x09, sp)
	addw	x, (0x17, sp)
	ldw	(0x09, sp), x
	ldw	x, (0x0b, sp)
	addw	x, (0x17, sp)
	ldw	(0x0b, sp), x
00104$:
;	decoder.c: 670: d_inter = 0;
	clrw	x
	ldw	_d_inter+0, x
;	decoder.c: 671: for (a = 0; a <= acap; a++) {
	ldw	x, (0x1d, sp)
	cpw	x, (0x09, sp)
	jrslt	00373$
	clr	(0x0d, sp)
	jra	00374$
00373$:
	ld	a, #0x01
	ld	(0x0d, sp), a
00374$:
	ldw	x, (0x09, sp)
	cpw	x, (0x1f, sp)
	jrsgt	00375$
	clr	(0x0e, sp)
	jra	00376$
00375$:
	ld	a, #0x01
	ld	(0x0e, sp), a
00376$:
	clrw	x
	ldw	(0x17, sp), x
00133$:
	ldw	x, (0x17, sp)
	cpw	x, (0x07, sp)
	jrsle	00377$
	jp	00117$
00377$:
;	decoder.c: 674: if (a == 0) {
	ldw	x, (0x17, sp)
	jrne	00113$
;	decoder.c: 675: c = hinge(u, v, h0e);
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	decoder.c: 676: it = (u < h0e && h0e <= v);
	tnz	(0x0d, sp)
	jreq	00145$
	tnz	(0x0e, sp)
	jreq	00146$
00145$:
	clr	a
	jra	00114$
00146$:
	ld	a, #0x01
	jra	00114$
00113$:
;	decoder.c: 678: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
	ldw	y, (0x17, sp)
	ldw	(0x11, sp), y
	ldw	x, y
	decw	x
	clr	a
	rlwa	x
	sllw	x
	addw	x, (0x0b, sp)
;	decoder.c: 679: c = hinge(u, v, h);
	ldw	(0x13, sp), x
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	decoder.c: 680: it = (u < h && h <= v);
	ldw	x, (0x1d, sp)
	cpw	x, (0x13, sp)
	jrsge	00148$
	ldw	x, (0x13, sp)
	cpw	x, (0x1f, sp)
	jrsle	00149$
00148$:
	clr	a
	.byte 0xc5
00149$:
	ld	a, #0x01
00150$:
;	decoder.c: 681: if (a < L) {
	ldw	x, (0x17, sp)
	cpw	x, (0x05, sp)
	jrsge	00114$
;	decoder.c: 682: int16_t h2 = (int16_t)(a * BIT_U + h0e);
	rlwa	x
	ld	a, (0x12, sp)
	rrwa	x
	exg	a, xl
	clr	a
	exg	a, xl
	sllw	x
	addw	x, (0x09, sp)
	ldw	(0x13, sp), x
;	decoder.c: 683: uint16_t c2 = hinge(u, v, h2);
	push	a
	ldw	x, (0x14, sp)
	pushw	x
	ldw	x, (0x22, sp)
	pushw	x
	ldw	x, (0x22, sp)
	call	_hinge
	pop	a
;	decoder.c: 684: if (c2 < c) c = c2;
	cpw	x, (0x0f, sp)
	jrnc	00106$
	ldw	(0x0f, sp), x
00106$:
;	decoder.c: 685: if (u < h2 && h2 <= v) it = 1;
	ldw	x, (0x1d, sp)
	cpw	x, (0x13, sp)
	jrsge	00114$
	ldw	x, (0x13, sp)
	cpw	x, (0x1f, sp)
	jrsgt	00114$
	ld	a, #0x01
00114$:
;	decoder.c: 688: d_costs[a] = c;
	ldw	x, (0x17, sp)
	sllw	x
	ldw	y, (0x0f, sp)
	ldw	((_d_costs+0), x), y
;	decoder.c: 689: if (it) d_inter |= (uint16_t)(1u << a);
	tnz	a
	jreq	00134$
	clrw	x
	incw	x
	ld	a, (0x18, sp)
	jreq	00389$
00388$:
	sllw	x
	dec	a
	jrne	00388$
00389$:
	ld	a, xl
	or	a, _d_inter+1
	rlwa	x
	or	a, _d_inter+0
	ld	xh, a
	ldw	_d_inter+0, x
00134$:
;	decoder.c: 671: for (a = 0; a <= acap; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jp	00133$
00117$:
;	decoder.c: 692: bc = 0xFFFF; bi = 1; *a_free = 0;
	clrw	x
	decw	x
	ldw	(0x10, sp), x
	ld	a, #0x01
	ld	(0x12, sp), a
	ldw	y, (0x24, sp)
	ldw	(0x13, sp), y
	ldw	x, y
	clr	(0x1, x)
	clr	(x)
;	decoder.c: 693: for (a = 0; a <= acap; a++) {
	clrw	x
	ldw	(0x17, sp), x
00136$:
	ldw	x, (0x17, sp)
	cpw	x, (0x07, sp)
	jrsgt	00123$
;	decoder.c: 694: uint8_t it = (uint8_t)((d_inter >> a) & 1);
	ldw	x, _d_inter+0
	ld	a, (0x18, sp)
	jreq	00393$
00392$:
	srlw	x
	dec	a
	jrne	00392$
00393$:
	ld	a, xl
	and	a, #0x01
;	decoder.c: 695: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
	ldw	x, (0x17, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
	cpw	x, (0x10, sp)
	jrc	00118$
	cpw	x, (0x10, sp)
	jrne	00137$
	tnz	a
	jreq	00137$
	tnz	(0x12, sp)
	jrne	00137$
00118$:
;	decoder.c: 696: bc = d_costs[a]; bi = it; *a_free = a;
	ldw	(0x10, sp), x
	ld	(0x12, sp), a
	ldw	x, (0x13, sp)
	ldw	y, (0x17, sp)
	ldw	(x), y
00137$:
;	decoder.c: 693: for (a = 0; a <= acap; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jra	00136$
00123$:
;	decoder.c: 699: a_bounds(k0, k1, &amin, &amax);
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, (0x1f, sp)
	pushw	x
	ldw	x, (0x1b, sp)
	call	_a_bounds
;	decoder.c: 700: lo = (amin > 0) ? amin : 0;
	ldw	x, (0x01, sp)
	cpw	x, #0x0000
	jrsgt	00152$
	clrw	x
00152$:
	ldw	(0x0c, sp), x
;	decoder.c: 701: hi = (amax < acap) ? amax : acap;
	ldw	x, (0x03, sp)
	cpw	x, (0x07, sp)
	jrsge	00153$
	ldw	x, (0x03, sp)
	.byte 0xc5
00153$:
	ldw	x, (0x07, sp)
00154$:
	ldw	(0x0e, sp), x
;	decoder.c: 702: if (lo > hi) { lo = 0; hi = acap; }
	ldw	x, (0x0c, sp)
	cpw	x, (0x0e, sp)
	jrsle	00125$
	clrw	x
	ldw	(0x0c, sp), x
	ldw	y, (0x07, sp)
	ldw	(0x0e, sp), y
00125$:
;	decoder.c: 703: bc = 0xFFFF; bi = 1; *a_hat = lo;
	clrw	x
	decw	x
	ldw	(0x10, sp), x
	ld	a, #0x01
	ld	(0x12, sp), a
	ldw	y, (0x22, sp)
	ldw	(0x13, sp), y
	ldw	x, y
	ldw	y, (0x0c, sp)
	ldw	(x), y
;	decoder.c: 704: for (a = lo; a <= hi; a++) {
	ldw	y, (0x0c, sp)
	ldw	(0x17, sp), y
00139$:
	ldw	x, (0x17, sp)
	cpw	x, (0x0e, sp)
	jrsgt	00131$
;	decoder.c: 705: uint8_t it = (uint8_t)((d_inter >> a) & 1);
	ldw	x, _d_inter+0
	ld	a, (0x18, sp)
	jreq	00406$
00405$:
	srlw	x
	dec	a
	jrne	00405$
00406$:
	ld	a, xl
	and	a, #0x01
;	decoder.c: 706: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
	ldw	x, (0x17, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
	cpw	x, (0x10, sp)
	jrc	00126$
	cpw	x, (0x10, sp)
	jrne	00140$
	tnz	a
	jreq	00140$
	tnz	(0x12, sp)
	jrne	00140$
00126$:
;	decoder.c: 707: bc = d_costs[a]; bi = it; *a_hat = a;
	ldw	(0x10, sp), x
	ld	(0x12, sp), a
	ldw	x, (0x13, sp)
	ldw	y, (0x17, sp)
	ldw	(x), y
00140$:
;	decoder.c: 704: for (a = lo; a <= hi; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jra	00139$
00131$:
;	decoder.c: 710: *lo_out = lo; *hi_out = hi;
	ldw	x, (0x26, sp)
	ldw	y, (0x0c, sp)
	ldw	(x), y
	ldw	x, (0x28, sp)
	ldw	y, (0x0e, sp)
	ldw	(x), y
;	decoder.c: 711: return acap;
	ldw	x, (0x07, sp)
;	decoder.c: 712: }
	ldw	y, (25, sp)
	addw	sp, #41
	jp	(y)
;	decoder.c: 714: static void decide_pass(const uint8_t *cap, uint16_t ncap)
;	-----------------------------------------
;	 function decide_pass
;	-----------------------------------------
_decide_pass:
	sub	sp, #85
	ldw	(0x50, sp), x
;	decoder.c: 719: for (t = 0; t < NBB; t++) { d_bits[t] = 0; d_conf[t] = 0; d_tied[t] = 0; }
	clrw	y
00171$:
	ldw	x, y
	clr	((_d_bits+0), x)
	ldw	x, y
	clr	((_d_conf+0), x)
	ldw	x, y
	clr	((_d_tied+0), x)
	incw	y
	cpw	y, #0x0038
	jrc	00171$
;	decoder.c: 720: d_nknife = 0; d_nres = 0;
	clr	_d_nknife+0
	clr	_d_nres+0
;	decoder.c: 721: d_infeas = 0; d_laberr = 0; d_nseg = 0;
	clr	_d_infeas+0
	clr	_d_laberr+0
	clrw	x
	ldw	_d_nseg+0, x
;	decoder.c: 722: ss_init(&ss, cap, ncap);
	ldw	x, (0x58, sp)
	pushw	x
	ldw	x, (0x52, sp)
	pushw	x
	ldw	x, sp
	addw	x, #5
	call	_ss_init
;	decoder.c: 723: while (ss_next(&ss, &sg)) {
00168$:
	ldw	x, sp
	addw	x, #47
	pushw	x
	ldw	x, sp
	addw	x, #3
	call	_ss_next
	ld	(0x55, sp), a
	jrne	00592$
	jp	00188$
00592$:
;	decoder.c: 725: int16_t L = (int16_t)(sg.k1 - sg.k0);
	ldw	y, (0x31, sp)
	ldw	x, sp
	addw	x, #47
	ldw	(0x40, sp), x
	ldw	x, (x)
	ldw	(0x54, sp), x
	subw	y, (0x54, sp)
	ldw	(0x42, sp), y
;	decoder.c: 728: int16_t ins0 = -1, ins1 = -1;
	clrw	x
	decw	x
	ldw	(0x4a, sp), x
	clrw	x
	decw	x
	ldw	(0x4c, sp), x
;	decoder.c: 729: d_nseg++;
	ldw	x, _d_nseg+0
	incw	x
	ldw	_d_nseg+0, x
;	decoder.c: 730: if (sg.k0 >= NB) continue;
	ldw	x, (0x40, sp)
	ldw	x, (x)
	ldw	(0x4e, sp), x
	cpw	x, #0x01c0
	jrnc	00168$
;	decoder.c: 732: &a_hat, &a_free, &lo, &hi);
;	decoder.c: 731: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
	ld	a, (0x37, sp)
	ldw	y, (0x35, sp)
	ldw	x, (0x33, sp)
	ldw	(0x52, sp), x
	ldw	x, (0x31, sp)
	ldw	(0x54, sp), x
	ldw	x, sp
	addw	x, #62
	pushw	x
	ldw	x, sp
	addw	x, #62
	pushw	x
	ldw	x, sp
	addw	x, #62
	pushw	x
	ldw	x, sp
	addw	x, #62
	pushw	x
	push	a
	pushw	y
	ldw	x, (0x5d, sp)
	pushw	x
	ldw	x, (0x61, sp)
	pushw	x
	ldw	x, (0x5d, sp)
	call	_decide
	ldw	(0x4e, sp), x
;	decoder.c: 733: c_hat = d_costs[a_hat];
	ldw	x, (0x38, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
;	decoder.c: 734: if (c_hat > INFEAS_U && d_infeas < 255) d_infeas++;
	cpw	x, #0x00a0
	jrule	00105$
	ld	a, _d_infeas+0
	cp	a, #0xff
	jrnc	00105$
	inc	_d_infeas+0
00105$:
;	decoder.c: 735: e = (sg.k1 < NB) ? sg.k1 : NB;
	ldw	x, (0x31, sp)
	cpw	x, #0x01c0
	jrnc	00190$
	ldw	(0x54, sp), x
	jra	00191$
00190$:
	ldw	x, #0x01c0
	ldw	(0x54, sp), x
00191$:
	ldw	y, (0x54, sp)
	ldw	(0x44, sp), y
;	decoder.c: 736: known_all = 1;
	ld	a, #0x01
	ld	(0x52, sp), a
;	decoder.c: 737: for (t = sg.k0; t < e; t++)
	ldw	x, (0x40, sp)
	ldw	x, (x)
	ldw	(0x54, sp), x
00174$:
;	decoder.c: 738: if (known_bit(t) < 0) { known_all = 0; break; }
	ldw	x, (0x54, sp)
	cpw	x, (0x44, sp)
	jrnc	00109$
	call	_known_bit
	tnz	a
	jrpl	00175$
	clr	(0x52, sp)
	jra	00109$
00175$:
;	decoder.c: 737: for (t = sg.k0; t < e; t++)
	ldw	x, (0x54, sp)
	incw	x
	ldw	(0x54, sp), x
	jra	00174$
00109$:
;	decoder.c: 739: dead = 0; nins = 0;
	clr	(0x53, sp)
;	decoder.c: 740: for (a = 0; a <= acap; a++)
	clr	a
	clrw	x
	ldw	(0x54, sp), x
00177$:
	ldw	x, (0x54, sp)
	cpw	x, (0x4e, sp)
	jrsgt	00112$
;	decoder.c: 741: if ((d_inter >> a) & 1) nins++;
	push	a
	ldw	x, _d_inter+0
	ld	a, (0x56, sp)
	jreq	00602$
00601$:
	srlw	x
	dec	a
	jrne	00601$
00602$:
	pop	a
	srlw	x
	jrnc	00178$
	inc	a
00178$:
;	decoder.c: 740: for (a = 0; a <= acap; a++)
	ldw	x, (0x54, sp)
	incw	x
	ldw	(0x54, sp), x
	jra	00177$
00112$:
;	decoder.c: 742: if (nins >= 2) dead = 1;
	cp	a, #0x02
	jrc	00114$
	ld	a, #0x01
	ld	(0x53, sp), a
00114$:
;	decoder.c: 743: if (known_all && lo == hi && a_free != lo && !dead && d_laberr < 255)
	tnz	(0x52, sp)
	jreq	00116$
	ldw	x, (0x3c, sp)
	cpw	x, (0x3e, sp)
	jrne	00116$
	ldw	x, (0x3a, sp)
	cpw	x, (0x3c, sp)
	jreq	00116$
	tnz	(0x53, sp)
	jrne	00116$
	ld	a, _d_laberr+0
	cp	a, #0xff
	jrnc	00116$
;	decoder.c: 744: d_laberr++;
	inc	_d_laberr+0
00116$:
;	decoder.c: 747: for (a = lo; a <= hi; a++) {
	ldw	x, (0x3c, sp)
	clr	a
	ldw	(0x54, sp), x
00180$:
	ldw	x, (0x54, sp)
	cpw	x, (0x3e, sp)
	jrsgt	00128$
;	decoder.c: 748: if ((d_inter >> a) & 1) {
	push	a
	ldw	x, _d_inter+0
	ld	a, (0x56, sp)
	jreq	00617$
00616$:
	srlw	x
	dec	a
	jrne	00616$
00617$:
	pop	a
	srlw	x
	jrnc	00181$
;	decoder.c: 749: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
	tnz	a
	jrne	00124$
	ldw	y, (0x54, sp)
	ldw	(0x4a, sp), y
	jra	00125$
00124$:
	cp	a, #0x01
	jrne	00125$
	ldw	y, (0x54, sp)
	ldw	(0x4c, sp), y
00125$:
;	decoder.c: 750: nins++;
	inc	a
00181$:
;	decoder.c: 747: for (a = lo; a <= hi; a++) {
	ldw	x, (0x54, sp)
	incw	x
	ldw	(0x54, sp), x
	jra	00180$
00128$:
;	decoder.c: 753: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
	cp	a, #0x02
	jrc	00132$
	ldw	x, (0x38, sp)
	cpw	x, (0x4a, sp)
	jreq	00131$
	ldw	x, (0x38, sp)
	cpw	x, (0x4c, sp)
	jrne	00132$
00131$:
;	decoder.c: 754: uint16_t tt = (uint16_t)(sg.k0 + ins0);
	ldw	x, (0x40, sp)
	ldw	x, (x)
	ldw	(0x54, sp), x
	ldw	y, (0x4a, sp)
	addw	y, (0x54, sp)
;	decoder.c: 755: if (tt < NB) BSET(d_tied, tt);
	ldw	x, y
	cpw	x, #0x01c0
	jrnc	00132$
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	(0x54, sp), a
	ld	a, yl
	and	a, #0x07
	ld	(0x55, sp), a
	ld	a, #0x01
	push	a
	ld	a, (0x56, sp)
	jreq	00633$
00632$:
	sll	(1, sp)
	dec	a
	jrne	00632$
00633$:
	pop	a
	or	a, (0x54, sp)
	ld	(x), a
00132$:
;	decoder.c: 758: for (t = sg.k0; t < e; t++) {
	ldw	x, (0x40, sp)
	ldw	x, (x)
	ldw	(0x52, sp), x
00186$:
	ldw	x, (0x52, sp)
	cpw	x, (0x44, sp)
	jrc	00634$
	jp	00154$
00634$:
;	decoder.c: 759: int16_t off = (int16_t)(t - sg.k0);
	ldw	x, (0x40, sp)
	ldw	x, (x)
	negw	x
	addw	x, (0x52, sp)
	ldw	(0x46, sp), x
;	decoder.c: 760: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
	clrw	x
	decw	x
	ldw	(0x48, sp), x
	clrw	x
	decw	x
	ldw	(0x4a, sp), x
;	decoder.c: 761: if (off < a_hat) BSET(d_bits, t);
	ldw	x, (0x52, sp)
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x4c, sp), x
	ld	a, (0x53, sp)
	and	a, #0x07
	ld	(0x4e, sp), a
	ld	a, #0x01
	ld	(0x4f, sp), a
	ld	a, (0x4e, sp)
	jreq	00636$
00635$:
	sll	(0x4f, sp)
	dec	a
	jrne	00635$
00636$:
	ldw	x, (0x46, sp)
	cpw	x, (0x38, sp)
	jrsge	00136$
	ldw	x, (0x4c, sp)
	addw	x, #(_d_bits+0)
	ld	a, (x)
	or	a, (0x4f, sp)
	ld	(x), a
00136$:
;	decoder.c: 762: for (a = lo; a <= hi; a++) {
	ldw	y, (0x3c, sp)
	ldw	(0x54, sp), y
00183$:
	ldw	x, (0x54, sp)
	cpw	x, (0x3e, sp)
	jrsgt	00144$
;	decoder.c: 763: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
	ldw	x, (0x54, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
	pushw	x
	ldw	x, (0x56, sp)
	cpw	x, (0x48, sp)
	popw	x
	jrsle	00142$
	cpw	x, (0x4a, sp)
	jrnc	00184$
	ldw	(0x4a, sp), x
	jra	00184$
00142$:
;	decoder.c: 764: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
	cpw	x, (0x48, sp)
	jrnc	00184$
	ldw	(0x48, sp), x
00184$:
;	decoder.c: 762: for (a = lo; a <= hi; a++) {
	ldw	x, (0x54, sp)
	incw	x
	ldw	(0x54, sp), x
	jra	00183$
00144$:
;	decoder.c: 766: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
	ldw	x, (0x48, sp)
	incw	x
	jreq	00147$
	ldw	x, (0x4a, sp)
	incw	x
	jrne	00148$
00147$:
	ldw	x, #0x00ff
	ldw	(0x54, sp), x
	jra	00149$
00148$:
;	decoder.c: 768: int16_t dm = (int16_t)(c0m - c1m);
	ldw	x, (0x48, sp)
	subw	x, (0x4a, sp)
;	decoder.c: 769: if (dm < 0) dm = (int16_t)-dm;
	ldw	(0x54, sp), x
	tnzw	x
	jrpl	00146$
	neg	(0x55, sp)
	clr	a
	sbc	a, (0x54, sp)
	ld	(0x54, sp), a
00146$:
;	decoder.c: 770: m = (dm > 255) ? 255 : (uint16_t)dm;
	ldw	x, #0x00ff
	cpw	x, (0x54, sp)
	jrsgt	00192$
	ldw	(0x54, sp), x
00192$:
00149$:
;	decoder.c: 772: if (m >= CONF_M && !BGET(d_tied, t)) BSET(d_conf, t);
	ldw	x, (0x54, sp)
	cpw	x, #0x0010
	jrc	00187$
	ldw	x, (0x4c, sp)
	ld	a, (_d_tied+0, x)
	push	a
	ld	a, (0x4f, sp)
	jreq	00653$
00652$:
	srl	(1, sp)
	dec	a
	jrne	00652$
00653$:
	pop	a
	srl	a
	jrc	00187$
	ldw	x, (0x4c, sp)
	addw	x, #(_d_conf+0)
	ld	a, (x)
	or	a, (0x4f, sp)
	ld	(x), a
00187$:
;	decoder.c: 758: for (t = sg.k0; t < e; t++) {
	ldw	x, (0x52, sp)
	incw	x
	ldw	(0x52, sp), x
	jp	00186$
00154$:
;	decoder.c: 775: if ((sg.fam == 5 || sg.fam == 6) && L == 1 &&
	ld	a, (0x37, sp)
	cp	a, #0x05
	jreq	00165$
	cp	a, #0x06
	jreq	00661$
	jp	00168$
00661$:
00165$:
	ldw	x, (0x42, sp)
	decw	x
	jreq	00664$
	jp	00168$
00664$:
;	decoder.c: 776: sg.k0 >= 32 && sg.k0 < NB - 32) {
	ldw	x, (0x40, sp)
	ldw	x, (x)
	cpw	x, #0x0020
	jrnc	00665$
	jp	00168$
00665$:
	cpw	x, #0x01a0
	jrc	00666$
	jp	00168$
00666$:
;	decoder.c: 777: int16_t dm = (int16_t)(d_costs[0] - d_costs[1]);
	ldw	y, _d_costs+0
	ldw	x, _d_costs+2
	ldw	(0x54, sp), x
	subw	y, (0x54, sp)
;	decoder.c: 778: if (dm < 0) dm = (int16_t)-dm;
	ldw	x, y
	tnzw	x
	jrpl	00156$
	negw	y
00156$:
;	decoder.c: 779: if (dm > 255) dm = 255;
	ldw	x, y
	cpw	x, #0x00ff
	jrsle	00158$
	ldw	y, #0x00ff
00158$:
;	decoder.c: 780: if (dm < KNIFE_M && d_nknife < KNIFE_MAX)
	ldw	x, y
	cpw	x, #0x0018
	jrslt	00669$
	jp	00168$
00669$:
	ld	a, _d_nknife+0
	cp	a, #0x20
	jrc	00670$
	jp	00168$
00670$:
;	decoder.c: 781: d_knife[d_nknife++] = sg.k0;
	ld	a, _d_nknife+0
	inc	_d_nknife+0
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #(_d_knife+0)
	ldw	y, (0x40, sp)
	ldw	y, (y)
	ldw	(x), y
	jp	00168$
00188$:
;	decoder.c: 784: }
	ldw	x, (86, sp)
	addw	sp, #89
	jp	(x)
;	decoder.c: 788: static uint8_t is_knife(uint16_t t)
;	-----------------------------------------
;	 function is_knife
;	-----------------------------------------
_is_knife:
	pushw	x
	ldw	(0x01, sp), x
;	decoder.c: 791: for (i = 0; i < d_nknife; i++)
	clr	a
00105$:
	cp	a, _d_nknife+0
	jrnc	00103$
;	decoder.c: 792: if (d_knife[i] == t) return 1;
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_d_knife+0, x)
	cpw	x, (0x01, sp)
	jrne	00106$
	ld	a, #0x01
	jra	00107$
00106$:
;	decoder.c: 791: for (i = 0; i < d_nknife; i++)
	inc	a
	jra	00105$
00103$:
;	decoder.c: 793: return 0;
	clr	a
00107$:
;	decoder.c: 794: }
	popw	x
	ret
;	decoder.c: 796: static uint8_t is_resolved(uint16_t t)
;	-----------------------------------------
;	 function is_resolved
;	-----------------------------------------
_is_resolved:
	pushw	x
	ldw	(0x01, sp), x
;	decoder.c: 799: for (i = 0; i < d_nres; i++)
	clr	a
00105$:
	cp	a, _d_nres+0
	jrnc	00103$
;	decoder.c: 800: if (d_resolved[i] == t) return 1;
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_d_resolved+0, x)
	cpw	x, (0x01, sp)
	jrne	00106$
	ld	a, #0x01
	jra	00107$
00106$:
;	decoder.c: 799: for (i = 0; i < d_nres; i++)
	inc	a
	jra	00105$
00103$:
;	decoder.c: 801: return 0;
	clr	a
00107$:
;	decoder.c: 802: }
	popw	x
	ret
;	decoder.c: 804: static void votes(void)
;	-----------------------------------------
;	 function votes
;	-----------------------------------------
_votes:
	sub	sp, #25
;	decoder.c: 806: uint8_t lag_ok[2] = {0, 0};
	clr	(0x01, sp)
	clr	(0x02, sp)
;	decoder.c: 809: for (li = 0; li < 2; li++) {
	clr	(0x13, sp)
00174$:
;	decoder.c: 810: uint16_t lag = li ? 16 : 8;
	tnz	(0x13, sp)
	jreq	00183$
	ld	a, #0x10
	ld	(0x19, sp), a
	jra	00184$
00183$:
	ld	a, #0x08
	ld	(0x19, sp), a
00184$:
	ld	a, (0x19, sp)
	ld	(0x0e, sp), a
	clr	(0x0d, sp)
;	decoder.c: 812: for (t = 32; t + lag < (uint16_t)(NB - 32); t++) {
	clrw	x
	ldw	(0x14, sp), x
	clrw	x
	ldw	(0x16, sp), x
	ldw	x, #0x0020
	ldw	(0x18, sp), x
00173$:
	ldw	x, (0x18, sp)
	addw	x, (0x0d, sp)
	cpw	x, #0x01a0
	jrc	00591$
	jp	00113$
00591$:
;	decoder.c: 813: uint16_t s = (uint16_t)(t + lag);
	ldw	(0x0b, sp), x
;	decoder.c: 814: if (is_knife(t) || is_knife(s)) continue;
	ldw	x, (0x18, sp)
	call	_is_knife
	tnz	a
	jreq	00592$
	jp	00112$
00592$:
	ldw	x, (0x0b, sp)
	call	_is_knife
	tnz	a
	jreq	00593$
	jp	00112$
00593$:
;	decoder.c: 815: if (BGET(d_tied, t) || BGET(d_tied, s)) continue;
	ldw	x, (0x18, sp)
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x0f, sp), x
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x19, sp)
	and	a, #0x07
	ld	(0x11, sp), a
	jreq	00595$
00594$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00594$
00595$:
	srlw	x
	jrc	00112$
	ldw	y, (0x0b, sp)
	ld	a, #0x08
	div	y, a
	ldw	x, y
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x0c, sp)
	and	a, #0x07
	ld	(0x12, sp), a
	jreq	00598$
00597$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00597$
00598$:
	srlw	x
	jrc	00112$
;	decoder.c: 816: if (!BGET(d_conf, t) || !BGET(d_conf, s)) continue;
	ldw	x, (0x0f, sp)
	ld	a, (_d_conf+0, x)
	push	a
	ld	a, (0x12, sp)
	jreq	00601$
00600$:
	srl	(1, sp)
	dec	a
	jrne	00600$
00601$:
	pop	a
	srl	a
	jrnc	00112$
	ldw	x, y
	ld	a, (_d_conf+0, x)
	push	a
	ld	a, (0x13, sp)
	jreq	00604$
00603$:
	srl	(1, sp)
	dec	a
	jrne	00603$
00604$:
	pop	a
	srl	a
	jrnc	00112$
;	decoder.c: 817: n_pair++;
	ldw	x, (0x16, sp)
	incw	x
	ldw	(0x16, sp), x
;	decoder.c: 818: if (BGET(d_bits, t) == BGET(d_bits, s)) agree++;
	ldw	x, (0x0f, sp)
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x12, sp)
	jreq	00608$
00607$:
	srl	(1, sp)
	dec	a
	jrne	00607$
00608$:
	pop	a
	and	a, #0x01
	ld	(0x11, sp), a
	ldw	x, y
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x13, sp)
	jreq	00610$
00609$:
	srl	(1, sp)
	dec	a
	jrne	00609$
00610$:
	pop	a
	and	a, #0x01
	cp	a, (0x11, sp)
	jrne	00112$
	ldw	x, (0x14, sp)
	incw	x
	ldw	(0x14, sp), x
00112$:
;	decoder.c: 812: for (t = 32; t + lag < (uint16_t)(NB - 32); t++) {
	ldw	x, (0x18, sp)
	incw	x
	ldw	(0x18, sp), x
	jp	00173$
00113$:
;	decoder.c: 820: lag_ok[li] = (n_pair >= KNIFE_PAIR_MIN &&
	clrw	x
	ld	a, (0x13, sp)
	ld	xl, a
	pushw	x
	ldw	x, sp
	addw	x, #3
	addw	x, (1, sp)
	ldw	(0x1a, sp), x
	popw	x
	ldw	x, (0x16, sp)
	cpw	x, #0x0028
	jrc	00185$
;	decoder.c: 821: (uint32_t)agree * 100 >=
	ldw	x, (0x14, sp)
	pushw	x
	ldw	x, #0x0064
;	decoder.c: 822: (uint32_t)KNIFE_AGREE_PCT * n_pair);
	call	___muluint2ulong
	addw	sp, #2
	ldw	(0x11, sp), x
	ldw	(0x0f, sp), y
	ldw	x, (0x16, sp)
	pushw	x
	ldw	x, #0x0063
	call	___muluint2ulong
	addw	sp, #2
	ldw	(0x16, sp), x
	ldw	(0x14, sp), y
	ldw	x, (0x11, sp)
	cpw	x, (0x16, sp)
	ld	a, (0x10, sp)
	sbc	a, (0x15, sp)
	ld	a, (0x0f, sp)
	sbc	a, (0x14, sp)
	jrnc	00186$
00185$:
	clr	a
	.byte 0xc5
00186$:
	ld	a, #0x01
00187$:
	ldw	x, (0x18, sp)
	ld	(x), a
;	decoder.c: 809: for (li = 0; li < 2; li++) {
	inc	(0x13, sp)
	ld	a, (0x13, sp)
	cp	a, #0x02
	jrnc	00618$
	jp	00174$
00618$:
;	decoder.c: 824: if (!lag_ok[0] && !lag_ok[1]) return;
	ld	a, (0x01, sp)
	jrne	00271$
	ld	a, (0x02, sp)
	ld	(0x19, sp), a
	jrne	00271$
	jp	00181$
;	decoder.c: 826: for (t = 32; t < (uint16_t)(NB - 32); t++) {
00271$:
	ldw	x, #0x0020
	ldw	(0x16, sp), x
00177$:
;	decoder.c: 827: uint8_t nv = 0, val = 0, mixed = 0;
	clr	(0x03, sp)
	clr	(0x04, sp)
;	decoder.c: 830: if (!BGET(d_tied, t)) continue;
	ldw	x, (0x16, sp)
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x05, sp), x
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x17, sp)
	and	a, #0x07
	ld	(0x07, sp), a
	jreq	00622$
00621$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00621$
00622$:
	srlw	x
	jrc	00623$
	jp	00143$
00623$:
;	decoder.c: 831: for (j = 0; j < 4; j++) {
	clr	(0x18, sp)
	clr	(0x19, sp)
00176$:
;	decoder.c: 832: int16_t dt = DTS[j];
	ld	a, (0x19, sp)
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	sllw	x
	ldw	x, (_votes_DTS_30000_301+0, x)
	ldw	(0x08, sp), x
;	decoder.c: 833: int32_t s = (int32_t)t + dt;
	ldw	y, (0x16, sp)
	clrw	x
	ldw	(0x0a, sp), x
	ldw	x, (0x08, sp)
	ldw	(0x10, sp), x
	clrw	x
	tnz	(0x10, sp)
	jrpl	00624$
	decw	x
00624$:
	addw	y, (0x10, sp)
	ldw	(0x14, sp), y
	ld	a, xl
	adc	a, (0x0b, sp)
	ld	(0x13, sp), a
	ld	a, xh
	adc	a, (0x0a, sp)
	ld	(0x12, sp), a
;	decoder.c: 834: uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
	ldw	x, (0x08, sp)
	jrpl	00188$
	ld	a, (0x09, sp)
	neg	a
	ld	xl, a
	clr	a
	sbc	a, (0x08, sp)
	jra	00189$
00188$:
	ld	a, (0x09, sp)
	ld	xl, a
	ld	a, (0x08, sp)
00189$:
;	decoder.c: 835: if (!lag_ok[lag == 16]) continue;
	ld	xh, a
	cpw	x, #0x0010
	jrne	00627$
	ld	a, #0x01
	.byte 0x21
00627$:
	clr	a
00628$:
	ldw	x, sp
	incw	x
	pushw	x
	clrw	x
	ld	xl, a
	addw	x, (1, sp)
	addw	sp, #2
	ld	a, (x)
	jrne	00629$
	jp	00133$
00629$:
;	decoder.c: 836: if (s < 32 || s >= NB - 32) continue;
	ldw	x, (0x14, sp)
	cpw	x, #0x0020
	ld	a, (0x13, sp)
	sbc	a, #0x00
	ld	a, (0x12, sp)
	sbc	a, #0x00
	jrslt	00133$
	ldw	x, (0x14, sp)
	cpw	x, #0x01a0
	ld	a, (0x13, sp)
	sbc	a, #0x00
	ld	a, (0x12, sp)
	sbc	a, #0x00
	jrsge	00133$
;	decoder.c: 837: if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
	ldw	x, (0x14, sp)
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x10, sp), x
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x15, sp)
	and	a, #0x07
	ld	(0x15, sp), a
	jreq	00633$
00632$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00632$
00633$:
	srlw	x
	jrc	00133$
	ldw	x, (0x10, sp)
	ld	a, (_d_conf+0, x)
	push	a
	ld	a, (0x16, sp)
	jreq	00636$
00635$:
	srl	(1, sp)
	dec	a
	jrne	00635$
00636$:
	pop	a
	srl	a
	jrnc	00133$
;	decoder.c: 839: if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
	tnz	(0x18, sp)
	jrne	00131$
	ldw	x, (0x10, sp)
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x16, sp)
	jreq	00640$
00639$:
	srl	(1, sp)
	dec	a
	jrne	00639$
00640$:
	pop	a
	and	a, #0x01
	ld	(0x03, sp), a
	jra	00132$
00131$:
;	decoder.c: 840: else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
	ldw	x, (0x10, sp)
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x16, sp)
	jreq	00642$
00641$:
	srl	(1, sp)
	dec	a
	jrne	00641$
00642$:
	pop	a
	and	a, #0x01
	ld	(0x15, sp), a
	ld	a, (0x03, sp)
	cp	a, (0x15, sp)
	jreq	00132$
	ld	a, #0x01
	ld	(0x04, sp), a
00132$:
;	decoder.c: 841: nv++;
	inc	(0x18, sp)
00133$:
;	decoder.c: 831: for (j = 0; j < 4; j++) {
	inc	(0x19, sp)
	ld	a, (0x19, sp)
	cp	a, #0x04
	jrsge	00646$
	jp	00176$
00646$:
;	decoder.c: 843: if (nv >= DEAD_VOTE_MIN && !mixed) {
	ld	a, (0x18, sp)
	cp	a, #0x03
	jrc	00143$
	tnz	(0x04, sp)
	jrne	00143$
;	decoder.c: 844: if (val) BSET(d_bits, t); else BCLR(d_bits, t);
	ld	a, #0x01
	ld	(0x19, sp), a
	ld	a, (0x07, sp)
	jreq	00650$
00649$:
	sll	(0x19, sp)
	dec	a
	jrne	00649$
00650$:
	tnz	(0x03, sp)
	jreq	00136$
	ldw	x, (0x05, sp)
	addw	x, #(_d_bits+0)
	ld	a, (x)
	or	a, (0x19, sp)
	ld	(x), a
	jra	00137$
00136$:
	ldw	x, (0x05, sp)
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	(0x18, sp), a
	ld	a, (0x19, sp)
	cpl	a
	and	a, (0x18, sp)
	ld	(x), a
00137$:
;	decoder.c: 845: if (d_nres < RESOLVED_MAX) d_resolved[d_nres++] = t;
	ld	a, _d_nres+0
	cp	a, #0x10
	jrnc	00143$
	ld	a, _d_nres+0
	inc	_d_nres+0
	clrw	x
	ld	xl, a
	sllw	x
	ldw	y, (0x16, sp)
	ldw	((_d_resolved+0), x), y
00143$:
;	decoder.c: 826: for (t = 32; t < (uint16_t)(NB - 32); t++) {
	ldw	x, (0x16, sp)
	incw	x
	ldw	(0x16, sp), x
	cpw	x, #0x01a0
	jrnc	00654$
	jp	00177$
00654$:
;	decoder.c: 851: for (i = 0; i < d_nknife; i++) {
	clr	(0x17, sp)
00180$:
	ld	a, (0x17, sp)
	cp	a, _d_nknife+0
	jrc	00655$
	jp	00181$
00655$:
;	decoder.c: 852: uint16_t tk = d_knife[i];
	ld	a, (0x17, sp)
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_d_knife+0, x)
	ldw	(0x08, sp), x
;	decoder.c: 853: uint8_t nv = 0, val = 0, mixed = 0;
	clr	(0x0a, sp)
	clr	(0x0b, sp)
;	decoder.c: 856: if (is_resolved(tk)) continue;
	ldw	x, (0x08, sp)
	call	_is_resolved
	tnz	a
	jreq	00656$
	jp	00170$
00656$:
;	decoder.c: 857: for (j = 0; j < 4; j++) {
	clr	(0x18, sp)
	clr	(0x19, sp)
00178$:
;	decoder.c: 858: int16_t dt = DTS[j];
	ld	a, (0x19, sp)
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	sllw	x
	addw	x, #(_votes_DTS_40000_316+0)
	ldw	x, (x)
	ldw	(0x0c, sp), x
;	decoder.c: 859: int32_t s = (int32_t)tk + dt;
	ldw	y, (0x08, sp)
	clr	(0x14, sp)
	ldw	x, (0x0c, sp)
	ld	a, xh
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x0e, sp), a
	ldw	(0x12, sp), y
	clr	a
	addw	x, (0x12, sp)
	ldw	(0x15, sp), x
	adc	a, (0x0e, sp)
	ld	(0x14, sp), a
;	decoder.c: 860: uint16_t lag = (uint16_t)(dt < 0 ? -dt : dt);
	ldw	x, (0x0c, sp)
	jrpl	00190$
	ld	a, (0x0d, sp)
	neg	a
	push	a
	clr	a
	sbc	a, (0x0d, sp)
	ld	xh, a
	pop	a
	jra	00191$
00190$:
	ld	a, (0x0d, sp)
	rlwa	x
	ld	a, (0x0c, sp)
	rrwa	x
00191$:
;	decoder.c: 861: if (!lag_ok[lag == 16]) continue;
	ld	xl, a
	cpw	x, #0x0010
	jrne	00659$
	ld	a, #0x01
	.byte 0x21
00659$:
	clr	a
00660$:
	ldw	x, sp
	incw	x
	pushw	x
	clrw	x
	ld	xl, a
	addw	x, (1, sp)
	addw	sp, #2
	ld	a, (x)
	jrne	00661$
	jp	00162$
00661$:
;	decoder.c: 862: if (s < 32 || s >= NB - 32) continue;
	ldw	x, (0x15, sp)
	cpw	x, #0x0020
	ld	a, (0x14, sp)
	sbc	a, #0x00
	jrsge	00662$
	jp	00162$
00662$:
	ldw	x, (0x15, sp)
	cpw	x, #0x01a0
	ld	a, (0x14, sp)
	sbc	a, #0x00
	jrsge	00162$
;	decoder.c: 863: if (is_knife((uint16_t)s)) continue;
	ldw	x, (0x15, sp)
	pushw	x
	call	_is_knife
	popw	x
	tnz	a
	jrne	00162$
;	decoder.c: 864: if (BGET(d_tied, (uint16_t)s) || !BGET(d_conf, (uint16_t)s))
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x12, sp), x
	addw	x, #(_d_tied+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x16, sp)
	and	a, #0x07
	ld	(0x16, sp), a
	jreq	00666$
00665$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00665$
00666$:
	srlw	x
	jrc	00162$
	ldw	x, (0x12, sp)
	ld	a, (_d_conf+0, x)
	push	a
	ld	a, (0x17, sp)
	jreq	00669$
00668$:
	srl	(1, sp)
	dec	a
	jrne	00668$
00669$:
	pop	a
	srl	a
	jrnc	00162$
;	decoder.c: 866: if (nv == 0) val = (uint8_t)BGET(d_bits, (uint16_t)s);
	tnz	(0x18, sp)
	jrne	00160$
	ldw	x, (0x12, sp)
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x17, sp)
	jreq	00673$
00672$:
	srl	(1, sp)
	dec	a
	jrne	00672$
00673$:
	pop	a
	and	a, #0x01
	ld	(0x0a, sp), a
	jra	00161$
00160$:
;	decoder.c: 867: else if (val != BGET(d_bits, (uint16_t)s)) mixed = 1;
	ldw	x, (0x12, sp)
	ld	a, (_d_bits+0, x)
	push	a
	ld	a, (0x17, sp)
	jreq	00675$
00674$:
	srl	(1, sp)
	dec	a
	jrne	00674$
00675$:
	pop	a
	and	a, #0x01
	ld	(0x16, sp), a
	ld	a, (0x0a, sp)
	cp	a, (0x16, sp)
	jreq	00161$
	ld	a, #0x01
	ld	(0x0b, sp), a
00161$:
;	decoder.c: 868: nv++;
	inc	(0x18, sp)
00162$:
;	decoder.c: 857: for (j = 0; j < 4; j++) {
	inc	(0x19, sp)
	ld	a, (0x19, sp)
	cp	a, #0x04
	jrsge	00679$
	jp	00178$
00679$:
;	decoder.c: 870: if (nv >= 1 && !mixed) {
	ld	a, (0x18, sp)
	cp	a, #0x01
	jrc	00170$
	tnz	(0x0b, sp)
	jrne	00170$
;	decoder.c: 871: if (val) BSET(d_bits, tk); else BCLR(d_bits, tk);
	ldw	x, (0x08, sp)
	srlw	x
	srlw	x
	srlw	x
	ld	a, (0x09, sp)
	and	a, #0x07
	push	a
	ld	a, #0x01
	ld	(0x1a, sp), a
	pop	a
	tnz	a
	jreq	00683$
00682$:
	sll	(0x19, sp)
	dec	a
	jrne	00682$
00683$:
	tnz	(0x0a, sp)
	jreq	00165$
	addw	x, #(_d_bits+0)
	ld	a, (x)
	or	a, (0x19, sp)
	ld	(x), a
	jra	00170$
00165$:
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	(0x18, sp), a
	ld	a, (0x19, sp)
	cpl	a
	and	a, (0x18, sp)
	ld	(x), a
00170$:
;	decoder.c: 851: for (i = 0; i < d_nknife; i++) {
	inc	(0x17, sp)
	jp	00180$
00181$:
;	decoder.c: 875: }
	addw	sp, #25
	ret
;	decoder.c: 882: uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out)
;	-----------------------------------------
;	 function ws_decode
;	-----------------------------------------
_ws_decode:
	sub	sp, #6
	ldw	(0x04, sp), x
;	decoder.c: 886: if (!seed(cap, ncap)) return 0;
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x06, sp)
	call	_seed
	tnz	a
	jrne	00102$
	clr	a
	jp	00130$
00102$:
;	decoder.c: 887: if (g_phases < 2) return 0;
	ld	a, _g_phases+0
	cp	a, #0x02
	jrnc	00151$
	clr	a
	jp	00130$
;	decoder.c: 888: for (r = 0; r < 2; r++) refine(cap, ncap);
00151$:
	clr	a
00122$:
	push	a
	ldw	x, (0x0a, sp)
	pushw	x
	ldw	x, (0x07, sp)
	call	_refine
	pop	a
	inc	a
	cp	a, #0x02
	jrc	00122$
;	decoder.c: 889: if (g_phases < 3) return 0;
	ld	a, _g_phases+0
	cp	a, #0x03
	jrnc	00107$
	clr	a
	jp	00130$
00107$:
;	decoder.c: 890: calibrate(cap, ncap);
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x06, sp)
	call	_calibrate
;	decoder.c: 891: if (g_phases < 4) return 0;
	ld	a, _g_phases+0
	cp	a, #0x04
	jrnc	00109$
	clr	a
	jp	00130$
00109$:
;	decoder.c: 892: decide_pass(cap, ncap);
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x06, sp)
	call	_decide_pass
;	decoder.c: 893: if (g_phases < 5) return 0;
	ld	a, _g_phases+0
	cp	a, #0x05
	jrnc	00111$
	clr	a
	jp	00130$
00111$:
;	decoder.c: 894: votes();
	call	_votes
;	decoder.c: 895: for (t = 0; t < NB; t++) {
	clr	(0x06, sp)
	clrw	y
00124$:
;	decoder.c: 896: int8_t kb = known_bit(t);
	pushw	y
	ldw	x, y
	call	_known_bit
	ld	(0x05, sp), a
	popw	y
;	decoder.c: 897: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
	tnz	(0x03, sp)
	jrmi	00125$
	ldw	x, y
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	and	a, #0x07
	jreq	00280$
00279$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00279$
00280$:
	ld	a, xl
	and	a, #0x01
	cp	a, (0x03, sp)
	jreq	00125$
	inc	(0x06, sp)
00125$:
;	decoder.c: 895: for (t = 0; t < NB; t++) {
	incw	y
	ldw	x, y
	cpw	x, #0x01c0
	jrc	00124$
;	decoder.c: 899: if (viol > 0 || d_infeas > GATE_INFEAS || d_laberr > GATE_LABERR)
	tnz	(0x06, sp)
	jrne	00116$
	ld	a, _d_infeas+0
	cp	a, #0x04
	jrugt	00116$
	ld	a, _d_laberr+0
	cp	a, #0x06
	jrule	00164$
00116$:
;	decoder.c: 900: return 0;
	clr	a
	jra	00130$
;	decoder.c: 901: for (t = 0; t < NB_PAYLOAD; t++) {
00164$:
	clrw	y
00128$:
;	decoder.c: 902: uint8_t b = 0, j;
	clr	a
;	decoder.c: 903: for (j = 0; j < 8; j++)
	clr	(0x06, sp)
00126$:
;	decoder.c: 904: b = (uint8_t)((b << 1) | BGET(d_bits, 32 + 8 * t + j));
	sll	a
	ld	(0x01, sp), a
	ldw	x, y
	sllw	x
	sllw	x
	sllw	x
	addw	x, #0x0020
	ld	a, (0x06, sp)
	ld	(0x03, sp), a
	clr	(0x02, sp)
	addw	x, (0x02, sp)
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	sll	a
	sll	a
	sll	a
	add	a, #0x20
	add	a, (0x06, sp)
	and	a, #0x07
	jreq	00289$
00288$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00288$
00289$:
	ld	a, xl
	and	a, #0x01
	or	a, (0x01, sp)
;	decoder.c: 903: for (j = 0; j < 8; j++)
	inc	(0x06, sp)
	push	a
	ld	a, (0x07, sp)
	cp	a, #0x08
	pop	a
	jrc	00126$
;	decoder.c: 905: out[t] = b;
	ldw	x, y
	addw	x, (0x0b, sp)
	ld	(x), a
;	decoder.c: 901: for (t = 0; t < NB_PAYLOAD; t++) {
	incw	y
	ldw	x, y
	cpw	x, #0x0030
	jrc	00128$
;	decoder.c: 907: return 1;
	ld	a, #0x01
00130$:
;	decoder.c: 908: }
	ldw	x, (7, sp)
	addw	sp, #12
	jp	(x)
	.area CODE
	.area CONST
	.area CONST
_O_CY:
	.db #0x00	; 0
	.db #0x04	; 4
	.db #0x09	; 9
	.db #0x0d	; 13
	.db #0x11	; 17
	.db #0x15	; 21
	.db #0x1b	; 27
	.db #0x20	; 32
	.area CODE
	.area CONST
_W_CY:
	.db #0x00	;  0
	.db #0xff	; -1
	.db #0x00	;  0
	.db #0x02	;  2
	.db #0x00	;  0
	.db #0x00	;  0
	.db #0x00	;  0
	.db #0x01	;  1
	.area CODE
	.area CONST
_HDR:
	.db #0xff	; 255
	.db #0x00	; 0
	.db #0xaa	; 170
	.db #0x65	; 101	'e'
	.area CODE
	.area CONST
_TRL:
	.db #0x9a	; 154
	.db #0x55	; 85	'U'
	.db #0x00	; 0
	.db #0xff	; 255
	.area CODE
	.area CONST
_votes_DTS_30000_301:
	.dw #0xfff0
	.dw #0xfff8
	.dw #0x0008
	.dw #0x0010
	.area CODE
	.area CONST
_votes_DTS_40000_316:
	.dw #0xfff0
	.dw #0xfff8
	.dw #0x0008
	.dw #0x0010
	.area CODE
	.area INITIALIZER
__xinit__g_phases:
	.db #0x05	; 5
	.area CABS (ABS)
