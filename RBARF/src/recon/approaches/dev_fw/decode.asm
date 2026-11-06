;--------------------------------------------------------
; File Created by SDCC : free open source ISO C Compiler
; Version 4.6.0 #16555 (Linux)
;--------------------------------------------------------
	.module decode
	
;--------------------------------------------------------
; Public variables in this module
;--------------------------------------------------------
	.globl _scan_next
	.globl _scan_init
	.globl _dec_info
	.globl _ws_decode_ex
	.globl _dec_eps_centi
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_dec_info::
	.ds 20
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
	.ds 24
_d_infeas:
	.ds 2
_d_laberr:
	.ds 2
_d_nseg:
	.ds 2
_d_costs:
	.ds 32
_d_inter:
	.ds 2
_v_cand_t:
	.ds 10
_v_cand_m:
	.ds 5
_v_ncand:
	.ds 1
_v_nweak:
	.ds 2
_v_ntied:
	.ds 2
_v_tiepend:
	.ds 2
_d_pp:
	.ds 16
_ss:
	.ds 20
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area INITIALIZED
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 127: static int8_t known_bit(uint16_t t)
;	-----------------------------------------
;	 function known_bit
;	-----------------------------------------
_known_bit:
	push	a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 129: if (t < 32)
	ldw	y, x
	cpw	x, #0x0020
	jrnc	00102$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 130: return (int8_t)((HDR[t >> 3] >> (7 - (t & 7))) & 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 131: if (t >= NB - 32) {
	cpw	y, #0x00a0
	jrc	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 132: uint16_t u = t - (NB - 32);
	subw	x, #0x00a0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 133: return (int8_t)((TRL[u >> 3] >> (7 - (u & 7))) & 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 135: return -1;
	.byte 0xc5
00104$:
	ld	a, #0xff
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 136: }
	addw	sp, #1
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 301: static int32_t map_raw(uint16_t t)
;	-----------------------------------------
;	 function map_raw
;	-----------------------------------------
_map_raw:
	sub	sp, #8
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 303: return (int32_t)((uint32_t)t * g_K >> KQ) + g_tau;
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
	ldw	(0x07, sp), x
	clrw	x
	tnz	(0x07, sp)
	jrpl	00105$
	decw	x
00105$:
	addw	y, (0x07, sp)
	ld	a, xl
	adc	a, (0x02, sp)
	rlwa	x
	adc	a, (0x01, sp)
	ld	xh, a
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 304: }
	addw	sp, #8
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 308: static uint8_t seed(void)
;	-----------------------------------------
;	 function seed
;	-----------------------------------------
_seed:
	sub	sp, #6
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 311: uint16_t r0m = 0, flm = 0;
	clrw	x
	ldw	(0x01, sp), x
	clrw	x
	ldw	(0x03, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 313: scan_init();
	call	_scan_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 314: while (scan_next()) {
	clrw	x
	ldw	(0x05, sp), x
00103$:
	call	_scan_next
	tnz	a
	jreq	00105$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 315: if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
	ldw	x, (0x05, sp)
	jrne	00102$
	ldw	x, _scan_ra+0
	addw	x, _scan_rb+0
	srlw	x
	ldw	(0x01, sp), x
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 316: flm = (uint16_t)((scan_fa + scan_fb) >> 1);
	ldw	x, _scan_fa+0
	addw	x, _scan_fb+0
	srlw	x
	ldw	(0x03, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 317: np++;
	ldw	x, (0x05, sp)
	incw	x
	ldw	(0x05, sp), x
	jra	00103$
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 319: if (np < 8 || flm <= r0m) return 0;
	ldw	x, (0x05, sp)
	cpw	x, #0x0008
	jrc	00106$
	ldw	x, (0x03, sp)
	cpw	x, (0x01, sp)
	jrugt	00107$
00106$:
	clr	a
	jra	00112$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 321: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
	ldw	y, (0x03, sp)
	subw	y, (0x01, sp)
	clrw	x
	pushw	y
	pushw	x
	push	#0x00
	push	#0xa0
	push	#0xf9
	push	#0x0b
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 322: if (K < K_MIN || K > K_MAX) return 0;
	call	__divulong
	addw	sp, #8
	ldw	(0x05, sp), x
	ldw	(0x03, sp), y
	ldw	x, (0x05, sp)
	cpw	x, #0xb3b0
	ld	a, (0x04, sp)
	sbc	a, #0x00
	ld	a, (0x03, sp)
	sbc	a, #0x00
	jrc	00109$
	ldw	x, #0xea60
	cpw	x, (0x05, sp)
	clr	a
	sbc	a, (0x04, sp)
	clr	a
	sbc	a, (0x03, sp)
	jrnc	00110$
00109$:
	clr	a
	jra	00112$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 323: g_K = (uint16_t)K;
	ldw	x, (0x05, sp)
	ldw	_g_K+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 324: g_tau = (int16_t)(BIAS_U - (int32_t)((uint32_t)r0m * g_K >> KQ));
	ldw	y, (0x01, sp)
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
	ldw	(0x05, sp), y
	ldw	x, #0x0200
	subw	x, (0x05, sp)
	ldw	_g_tau+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 325: return 1;
	ld	a, #0x01
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 326: }
	addw	sp, #6
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 330: static void refine(void)
;	-----------------------------------------
;	 function refine
;	-----------------------------------------
_refine:
	sub	sp, #40
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 335: int32_t se_lo = 0, se_hi = 0;                    /* ** 32-bit ** */
	clrw	x
	ldw	(0x17, sp), x
	ldw	(0x15, sp), x
	clrw	x
	ldw	(0x1b, sp), x
	ldw	(0x19, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 336: uint32_t sy_lo = 0, sy_hi = 0;                   /* ** 32-bit ** */
	clrw	x
	ldw	(0x1f, sp), x
	ldw	(0x1d, sp), x
	clrw	x
	ldw	(0x23, sp), x
	ldw	(0x21, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 340: scan_init();
	call	_scan_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 341: while (scan_next()) {
	clrw	x
	ldw	(0x25, sp), x
	clrw	x
	ldw	(0x27, sp), x
00108$:
	call	_scan_next
	ld	(0x14, sp), a
	jrne	00186$
	jp	00110$
00186$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 345: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
	ldw	x, _scan_ra+0
	addw	x, _scan_rb+0
	srlw	x
	call	_map_raw
	ldw	(0x0d, sp), x
	ldw	(0x0b, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 346: if (y < 0) y = 0;
	tnz	(0x0b, sp)
	jrpl	00102$
	clrw	x
	ldw	(0x0d, sp), x
	ldw	(0x0b, sp), x
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 347: if ((uint32_t)y > y_end) break;
	ldw	y, (0x0d, sp)
	ldw	(0x11, sp), y
	ldw	y, (0x0b, sp)
	ldw	(0x0f, sp), y
	ldw	x, #0x82a4
	cpw	x, (0x11, sp)
	ld	a, #0x01
	sbc	a, (0x10, sp)
	clr	a
	sbc	a, (0x0f, sp)
	jrnc	00188$
	jp	00110$
00188$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 348: q = ((uint32_t)y + BIT_H) >> BIT_SH;
	ld	a, (0x11, sp)
	add	a, #0x01
	ldw	x, (0x0f, sp)
	jrnc	00189$
	incw	x
00189$:
	rlwa	x
	clr	(0x07, sp)
	srl	a
	rrcw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 349: e = (int16_t)(y - (int32_t)(q << BIT_SH));
	clr	a
	rlwa	x
	sllw	x
	ldw	y, (0x0d, sp)
	ldw	(0x13, sp), y
	negw	x
	addw	x, (0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 350: if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
	ldw	(0x0d, sp), x
	clrw	x
	tnz	(0x0d, sp)
	jrpl	00190$
	decw	x
00190$:
	ld	a, (0x12, sp)
	cp	a, #0x00
	ld	a, (0x11, sp)
	sbc	a, #0xc2
	ld	a, (0x10, sp)
	sbc	a, #0x00
	ld	a, (0x0f, sp)
	sbc	a, #0x00
	jrnc	00106$
	ldw	y, (0x25, sp)
	incw	y
	ldw	(0x25, sp), y
	ldw	y, (0x0d, sp)
	addw	y, (0x17, sp)
	ldw	(0x17, sp), y
	ld	a, xl
	adc	a, (0x16, sp)
	ld	(0x16, sp), a
	ld	a, xh
	adc	a, (0x15, sp)
	ld	(0x15, sp), a
	ldw	x, (0x1f, sp)
	addw	x, (0x11, sp)
	ldw	(0x1f, sp), x
	ld	a, (0x1e, sp)
	adc	a, (0x10, sp)
	ld	(0x1e, sp), a
	ld	a, (0x1d, sp)
	adc	a, (0x0f, sp)
	ld	(0x1d, sp), a
	jp	00108$
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 351: else                     { n_hi++; se_hi += e; sy_hi += (uint32_t)y; }
	ldw	y, (0x27, sp)
	incw	y
	ldw	(0x27, sp), y
	ldw	y, (0x0d, sp)
	addw	y, (0x1b, sp)
	ldw	(0x1b, sp), y
	ld	a, xl
	adc	a, (0x1a, sp)
	ld	(0x1a, sp), a
	ld	a, xh
	adc	a, (0x19, sp)
	ld	(0x19, sp), a
	ldw	x, (0x23, sp)
	addw	x, (0x11, sp)
	ldw	(0x23, sp), x
	ld	a, (0x22, sp)
	adc	a, (0x10, sp)
	ld	(0x22, sp), a
	ld	a, (0x21, sp)
	adc	a, (0x0f, sp)
	ld	(0x21, sp), a
	jp	00108$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 353: if (n_lo < 2 || n_hi < 2) return;
	ldw	x, (0x25, sp)
	cpw	x, #0x0002
	jrnc	00192$
	jp	00119$
00192$:
	ldw	x, (0x27, sp)
	cpw	x, #0x0002
	jrnc	00112$
	jp	00119$
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 354: me_lo = se_lo / (int32_t)n_lo;
	ldw	y, (0x25, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x1b, sp)
	pushw	x
	ldw	x, (0x1b, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 355: me_hi = se_hi / (int32_t)n_hi;
	call	__divslong
	addw	sp, #8
	ldw	(0x07, sp), x
	ldw	(0x05, sp), y
	ldw	y, (0x27, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x1f, sp)
	pushw	x
	ldw	x, (0x1f, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 356: my_lo = sy_lo / n_lo;
	call	__divslong
	addw	sp, #8
	ldw	(0x0b, sp), x
	ldw	(0x09, sp), y
	ldw	y, (0x25, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x23, sp)
	pushw	x
	ldw	x, (0x23, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 357: my_hi = sy_hi / n_hi;
	call	__divulong
	addw	sp, #8
	ldw	(0x13, sp), x
	ldw	(0x11, sp), y
	ldw	y, (0x27, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x27, sp)
	pushw	x
	ldw	x, (0x27, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 358: de = me_hi - me_lo;
	call	__divulong
	addw	sp, #8
	ldw	(0x0f, sp), x
	ldw	(0x0d, sp), y
	ldw	x, (0x0b, sp)
	subw	x, (0x07, sp)
	ldw	(0x03, sp), x
	ld	a, (0x0a, sp)
	sbc	a, (0x06, sp)
	ld	(0x02, sp), a
	ld	a, (0x09, sp)
	sbc	a, (0x05, sp)
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 359: dy = (int32_t)my_hi - (int32_t)my_lo;
	ldw	x, (0x0f, sp)
	subw	x, (0x13, sp)
	ldw	(0x07, sp), x
	ld	a, (0x0e, sp)
	sbc	a, (0x12, sp)
	ld	(0x06, sp), a
	ld	a, (0x0d, sp)
	sbc	a, (0x11, sp)
	ld	(0x05, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 360: if (dy <= 0) return;
	clrw	x
	cpw	x, (0x07, sp)
	clr	a
	sbc	a, (0x06, sp)
	clr	a
	sbc	a, (0x05, sp)
	jrslt	00115$
	jp	00119$
00115$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 361: dk = ((int32_t)g_K * de) / dy;                   /* ** 32-bit ** */
	ldw	x, _g_K+0
	ldw	(0x0b, sp), x
	clr	(0x0a, sp)
	clr	(0x09, sp)
	ldw	x, (0x03, sp)
	pushw	x
	ldw	x, (0x03, sp)
	pushw	x
	ldw	x, (0x0f, sp)
	pushw	x
	ldw	x, (0x0f, sp)
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x13, sp), x
	ldw	x, (0x07, sp)
	pushw	x
	ldw	x, (0x07, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	pushw	y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 362: me = (se_lo + se_hi) / (int32_t)(n_lo + n_hi);
	call	__divslong
	addw	sp, #8
	ldw	(0x0f, sp), x
	ldw	(0x0d, sp), y
	ldw	x, (0x17, sp)
	addw	x, (0x1b, sp)
	ldw	(0x13, sp), x
	ld	a, (0x16, sp)
	adc	a, (0x1a, sp)
	ld	(0x12, sp), a
	ld	a, (0x15, sp)
	adc	a, (0x19, sp)
	ld	(0x11, sp), a
	ldw	x, (0x25, sp)
	addw	x, (0x27, sp)
	ldw	(0x1b, sp), x
	ldw	y, x
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 363: my = (sy_lo + sy_hi) / (uint32_t)(n_lo + n_hi);
	call	__divslong
	addw	sp, #8
	ldw	(0x19, sp), x
	ldw	(0x17, sp), y
	ldw	x, (0x1f, sp)
	addw	x, (0x23, sp)
	ldw	(0x27, sp), x
	ld	a, (0x1e, sp)
	adc	a, (0x22, sp)
	ld	(0x26, sp), a
	ld	a, (0x1d, sp)
	adc	a, (0x21, sp)
	ld	(0x25, sp), a
	ldw	y, (0x1b, sp)
	clrw	x
	pushw	y
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 364: dtau = -me + (de * ((int32_t)my - g_tau)) / dy;  /* ** 32-bit ** */
	call	__divulong
	addw	sp, #8
	exgw	x, y
	ld	a, (0x19, sp)
	ld	(0x27, sp), a
	ld	a, (0x1a, sp)
	neg	a
	ld	(0x20, sp), a
	clr	a
	sbc	a, (0x27, sp)
	ld	(0x1f, sp), a
	rlwa	x
	ld	(0x21, sp), a
	rrwa	x
	ld	a, xl
	ldw	x, _g_tau+0
	ldw	(0x27, sp), x
	clrw	x
	tnz	(0x27, sp)
	jrpl	00195$
	decw	x
00195$:
	subw	y, (0x27, sp)
	pushw	x
	sbc	a, (2, sp)
	popw	x
	ld	xl, a
	ld	a, (0x21, sp)
	pushw	x
	sbc	a, (1, sp)
	popw	x
	ld	xh, a
	pushw	y
	pushw	x
	ldw	x, (0x07, sp)
	pushw	x
	ldw	x, (0x07, sp)
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x27, sp), x
	ldw	x, (0x07, sp)
	pushw	x
	ldw	x, (0x07, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	pushw	y
	call	__divslong
	addw	sp, #8
	addw	x, (0x1f, sp)
	ldw	(0x27, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 365: K2 = (int32_t)g_K - dk;
	ldw	x, (0x0b, sp)
	subw	x, (0x0f, sp)
	ldw	(0x25, sp), x
	clr	a
	sbc	a, (0x0e, sp)
	ld	(0x24, sp), a
	clr	a
	sbc	a, (0x0d, sp)
	ld	(0x23, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 366: if (K2 < (int32_t)K_MIN || K2 > (int32_t)K_MAX) return;
	ldw	x, (0x25, sp)
	cpw	x, #0xb3b0
	ld	a, (0x24, sp)
	sbc	a, #0x00
	ld	a, (0x23, sp)
	sbc	a, #0x00
	jrslt	00119$
	ldw	x, #0xea60
	cpw	x, (0x25, sp)
	clr	a
	sbc	a, (0x24, sp)
	clr	a
	sbc	a, (0x23, sp)
	jrslt	00119$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 367: g_K = (uint16_t)K2;
	ldw	x, (0x25, sp)
	ldw	_g_K+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 368: g_tau = (int16_t)(g_tau + dtau);
	ldw	x, _g_tau+0
	addw	x, (0x27, sp)
	ldw	_g_tau+0, x
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 369: }
	addw	sp, #40
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 393: static void ss_init(void)
;	-----------------------------------------
;	 function ss_init
;	-----------------------------------------
_ss_init:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 395: scan_init();
	call	_scan_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 396: ss.y_end = (uint32_t)BIAS_U + (uint32_t)NB * BIT_U + TAIL_U;
	ldw	x, #(_ss+0)
	ldw	y, #0x82a4
	ldw	(0x2, x), y
	ldw	y, #0x0001
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 397: ss.y_prev = 0; ss.have_y = 0; ss.n = 0;
	ldw	x, #(_ss+4)
	clrw	y
	ldw	(0x2, x), y
	ldw	(x), y
	mov	_ss+8, #0x00
	ldw	x, #(_ss+9)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 398: ss.pend = 0; ss.src_done = 0;
	mov	_ss+11, #0x00
	mov	_ss+19, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 399: ss.p_k0 = 0; ss.p_u = 0; ss.p_v = 0; ss.p_fam = 0;
	ldw	x, #(_ss+12)
	clr	(0x1, x)
	clr	(x)
	ldw	x, #(_ss+14)
	clr	(0x1, x)
	clr	(x)
	ldw	x, #(_ss+16)
	clr	(0x1, x)
	clr	(x)
	mov	_ss+18, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 400: }
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 402: static uint8_t ss_next(Seg *out)
;	-----------------------------------------
;	 function ss_next
;	-----------------------------------------
_ss_next:
	sub	sp, #31
	ldw	(0x1e, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
00121$:
	ld	a, _ss+19
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
	ldw	y, (0x1e, sp)
	ldw	(0x0d, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
	ldw	x, (0x1e, sp)
	incw	x
	incw	x
	ldw	(0x0f, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, (0x1e, sp)
	addw	x, #0x0004
	ldw	(0x11, sp), x
	ldw	x, (0x1e, sp)
	addw	x, #0x0006
	ldw	(0x13, sp), x
	ldw	x, (0x1e, sp)
	addw	x, #0x0008
	ldw	(0x15, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
	tnz	a
	jreq	00242$
	jp	00123$
00242$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 409: if (!scan_next()) { ss.src_done = 1; break; }
	call	_scan_next
	tnz	a
	jrne	00102$
	mov	_ss+19, #0x01
	jp	00123$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 410: y = map_raw((uint16_t)((scan_ra + scan_rb) >> 1));
	ldw	x, _scan_ra+0
	addw	x, _scan_rb+0
	srlw	x
	call	_map_raw
	ldw	(0x03, sp), x
	ldw	(0x01, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 411: if (y < 0) y = 0;
	tnz	(0x01, sp)
	jrpl	00104$
	clrw	x
	ldw	(0x03, sp), x
	ldw	(0x01, sp), x
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 412: if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
	ldw	y, (0x03, sp)
	ldw	(0x07, sp), y
	ldw	y, (0x01, sp)
	ldw	(0x05, sp), y
	ldw	x, #(_ss+0)
	ldw	y, x
	ldw	y, (0x2, y)
	ldw	x, (x)
	ld	a, yl
	cp	a, (0x08, sp)
	ld	a, yh
	sbc	a, (0x07, sp)
	ld	a, xl
	sbc	a, (0x06, sp)
	ld	a, xh
	sbc	a, (0x05, sp)
	jrnc	00106$
	mov	_ss+19, #0x01
	jp	00123$
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 413: if (!ss.have_y) { ss.n = 0; ss.have_y = 1; }
	ld	a, _ss+8
	jrne	00110$
	ldw	x, #(_ss+9)
	clr	(0x1, x)
	clr	(x)
	mov	_ss+8, #0x01
	jra	00111$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 415: d = y - (int32_t)ss.y_prev;
	ldw	x, #(_ss+4)
	ldw	y, x
	ldw	y, (0x2, y)
	ldw	x, (x)
	ldw	(0x0b, sp), y
	ldw	(0x09, sp), x
	ldw	y, (0x03, sp)
	subw	y, (0x0b, sp)
	ld	a, (0x02, sp)
	sbc	a, (0x0a, sp)
	ld	(0x1b, sp), a
	ld	a, (0x01, sp)
	sbc	a, (0x09, sp)
	ld	(0x1a, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 416: dn = (int16_t)((d + BIT_H) >> BIT_SH);
	addw	y, #0x0100
	ldw	x, (0x1a, sp)
	jrnc	00247$
	incw	x
00247$:
	clr	a
	tnzw	x
	jrpl	00248$
	dec	a
00248$:
	rrwa	x
	rrwa	y
	sraw	x
	rrcw	y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 417: if (dn > 0) ss.n = (uint16_t)(ss.n + dn);
	ldw	x, y
	cpw	x, #0x0000
	jrsle	00111$
	ldw	x, _ss+9
	ldw	(0x1c, sp), y
	addw	x, (0x1c, sp)
	ldw	_ss+9, x
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 419: ss.y_prev = (uint32_t)y;
	ldw	x, #(_ss+4)
	ldw	y, (0x07, sp)
	ldw	(0x2, x), y
	ldw	y, (0x05, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 420: yfa = map_raw(scan_fa);
	ldw	x, _scan_fa+0
	call	_map_raw
	ldw	(0x1c, sp), x
	ldw	(0x1a, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 421: yfb = map_raw(scan_fb);
	ldw	x, _scan_fb+0
	call	_map_raw
	ldw	(0x09, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
	ld	a, _ss+11
	ld	(0x17, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	y, (0x1c, sp)
	ldw	(0x18, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	(0x1a, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
	tnz	(0x17, sp)
	jreq	00113$
	ldw	y, _ss+9
	ldw	x, _ss+12
	ldw	(0x1c, sp), x
	ldw	x, y
	cpw	x, (0x1c, sp)
	jrne	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 423: base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
	ldw	x, (0x1c, sp)
	swapw	x
	clr	a
	clr	(0x14, sp)
	exg	a, xl
	ld	(0x11, sp), a
	exg	a, xl
	ld	(0x10, sp), a
	clr	a
	ld	xl, a
	sllw	x
	rlc	(0x11, sp)
	rlc	(0x10, sp)
	addw	x, #0x0200
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	(0x1c, sp), x
	ldw	x, (0x18, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x1a, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+16, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
	mov	_ss+18, _scan_sfa+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 427: continue;
	jp	00121$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 429: if (ss.pend) {
	tnz	(0x17, sp)
	jrne	00255$
	jp	00118$
00255$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
	ldw	x, _ss+12
	ldw	y, (0x0d, sp)
	ldw	(y), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
	ldw	x, _ss+9
	cpw	x, #0x00c0
	jrnc	00128$
	ldw	(0x1c, sp), x
	jra	00129$
00128$:
	ldw	x, #0x00c0
	ldw	(0x1c, sp), x
00129$:
	ldw	x, (0x0f, sp)
	ldw	y, (0x1c, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, _ss+14
	ldw	y, (0x11, sp)
	ldw	(y), x
	ldw	x, _ss+16
	ldw	y, (0x13, sp)
	ldw	(y), x
	ld	a, _ss+18
	ldw	x, (0x15, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 433: if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
	ldw	x, _ss+9
	ldw	(0x1c, sp), x
	cpw	x, #0x00c0
	jrc	00116$
	mov	_ss+11, #0x00
	mov	_ss+19, #0x01
	ld	a, #0x01
	jp	00126$
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 434: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
	ldw	x, (0x1c, sp)
	clrw	y
	clr	a
	sll	a
	rlcw	x
	exg	a, yl
	rlc	a
	exg	a, yl
	ld	(0x17, sp), a
	addw	x, #0x0002
	ldw	(0x15, sp), x
	clr	a
	adc	a, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 435: ss.p_k0 = ss.n;
	ldw	x, #(_ss+12)
	ldw	y, (0x1c, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 436: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	y, (0x16, sp)
	ldw	(0x1c, sp), y
	ldw	x, (0x18, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 437: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x1a, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+16, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 438: ss.p_fam = scan_sfa;
	mov	_ss+18, _scan_sfa+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 439: return 1;
	ld	a, #0x01
	jra	00126$
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 441: if (ss.n >= NB) { ss.src_done = 1; break; }
	ldw	x, _ss+9
	ldw	(0x1c, sp), x
	cpw	x, #0x00c0
	jrc	00120$
	mov	_ss+19, #0x01
	jra	00123$
00120$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 442: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
	ld	a, (0x1d, sp)
	ld	yh, a
	clr	a
	clrw	x
	exg	a, yl
	clr	a
	exg	a, yl
	sllw	y
	rlc	a
	rlcw	x
	addw	y, #0x0200
	adc	a, #0x00
	ld	(0x15, sp), a
	clr	a
	adc	a, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 443: ss.pend = 1;
	mov	_ss+11, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 444: ss.p_k0 = ss.n;
	ldw	x, _ss+9
	ldw	_ss+12, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 445: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	(0x1c, sp), y
	ldw	x, (0x18, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 446: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x1a, sp)
	subw	x, (0x1c, sp)
	ldw	_ss+16, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 447: ss.p_fam = scan_sfa;
	mov	_ss+18, _scan_sfa+0
	jp	00121$
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 449: if (ss.pend) {
	ld	a, _ss+11
	jreq	00125$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 450: ss.pend = 0;
	mov	_ss+11, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 451: out->k0 = ss.p_k0; out->k1 = NB;
	ldw	x, _ss+12
	ldw	y, (0x0d, sp)
	ldw	(y), x
	ldw	x, (0x0f, sp)
	ldw	y, #0x00c0
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 452: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, _ss+14
	ldw	y, (0x11, sp)
	ldw	(y), x
	ldw	x, _ss+16
	ldw	y, (0x13, sp)
	ldw	(y), x
	ld	a, _ss+18
	ldw	x, (0x15, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 453: return 1;
	ld	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 455: return 0;
	.byte 0x21
00125$:
	clr	a
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 456: }
	addw	sp, #31
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 460: static void a_bounds(uint16_t k0, uint16_t k1, int16_t *amin, int16_t *amax)
;	-----------------------------------------
;	 function a_bounds
;	-----------------------------------------
_a_bounds:
	sub	sp, #12
	ldw	(0x09, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 462: uint16_t t, e = (k1 < NB) ? k1 : NB;
	ldw	x, (0x0f, sp)
	cpw	x, #0x00c0
	jrc	00117$
	ldw	x, #0x00c0
00117$:
	ldw	(0x01, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 463: *amin = 0;
	ldw	y, (0x11, sp)
	ldw	(0x03, sp), y
	ldw	x, y
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 464: *amax = (int16_t)(k1 - k0);
	ldw	y, (0x13, sp)
	ldw	(0x05, sp), y
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x05, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
	ldw	y, (0x09, sp)
	ldw	(0x0b, sp), y
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 466: int8_t kb = known_bit(t);
	ldw	x, (0x0b, sp)
	cpw	x, (0x01, sp)
	jrnc	00114$
	call	_known_bit
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
	ldw	y, (0x0b, sp)
	subw	y, (0x09, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 467: if (kb == 1) {
	cp	a, #0x01
	jrne	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
	ldw	(0x07, sp), y
	ldw	x, y
	incw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 469: if (m > *amin) *amin = m;
	ldw	y, (0x03, sp)
	ldw	y, (y)
	ldw	(0x07, sp), y
	cpw	x, (0x07, sp)
	jrsle	00113$
	ldw	y, (0x03, sp)
	ldw	(y), x
	jra	00113$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 470: } else if (kb == 0) {
	tnz	a
	jrne	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 471: int16_t m = (int16_t)(t - k0);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 472: if (m < *amax) *amax = m;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 465: for (t = k0; t < e; t++) {
	ldw	x, (0x0b, sp)
	incw	x
	ldw	(0x0b, sp), x
	jra	00112$
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 475: }
	ldw	x, (13, sp)
	addw	sp, #20
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 479: static int8_t label_interval(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function label_interval
;	-----------------------------------------
_label_interval:
	sub	sp, #10
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 482: int16_t L = (int16_t)(k1 - k0);
	negw	x
	addw	x, (0x0d, sp)
	ldw	(0x09, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 484: if (a == 0) { *lo = u; *hi = v; return 0; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 485: if (a == L) {
	ldw	x, (0x13, sp)
	cpw	x, (0x09, sp)
	jrne	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 486: off = (int16_t)((L - 1) * BIT_U);
	ldw	x, (0x09, sp)
	decw	x
	clr	a
	rlwa	x
	sllw	x
	ldw	(0x09, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 487: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 488: return 1;
	ld	a, #0x01
	jp	00113$
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 490: mid = (int16_t)((u + v) >> 1);
	ldw	y, (0x0f, sp)
	addw	y, (0x11, sp)
	sraw	y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 491: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 492: if (d1 < 0) d1 = (int16_t)-d1;
	ldw	(0x07, sp), x
	tnzw	x
	jrpl	00106$
	neg	(0x08, sp)
	clr	a
	sbc	a, (0x07, sp)
	ld	(0x07, sp), a
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 493: d0 = (int16_t)(mid - (a * BIT_U + H0P));
	ld	a, (0x0a, sp)
	ld	(0x05, sp), a
	clr	(0x06, sp)
	sll	(0x06, sp)
	rlc	(0x05, sp)
	ldw	x, (0x05, sp)
	addw	x, #0x009a
	ldw	(0x09, sp), x
	subw	y, (0x09, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 494: if (d0 < 0) d0 = (int16_t)-d0;
	ldw	(0x09, sp), y
	ldw	x, y
	tnzw	x
	jrpl	00108$
	neg	(0x0a, sp)
	clr	a
	sbc	a, (0x09, sp)
	ld	(0x09, sp), a
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 495: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 496: if (d1 <= d0) {
	ldw	x, (0x07, sp)
	cpw	x, (0x09, sp)
	jrsgt	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 497: off = (int16_t)((a - 1) * BIT_U);
	ldw	y, (0x03, sp)
	ldw	(0x09, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 498: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 499: return 1;
	ld	a, #0x01
	jra	00113$
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 501: off = (int16_t)(a * BIT_U);
	ldw	y, (0x05, sp)
	ldw	(0x09, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 502: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	y, (0x0f, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x15, sp)
	ldw	(x), y
	ldw	y, (0x11, sp)
	subw	y, (0x09, sp)
	ldw	x, (0x01, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 503: return 0;
	clr	a
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 504: }
	ldw	x, (11, sp)
	addw	sp, #24
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 506: static void cal_cloud(int16_t u, uint8_t fam)
;	-----------------------------------------
;	 function cal_cloud
;	-----------------------------------------
_cal_cloud:
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 510: if (fam != 5 && fam != 6) return;
	cp	a, #0x05
	jreq	00102$
	cp	a, #0x06
	jrne	00111$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 511: if (u < 0) return;
	tnzw	x
	jrmi	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 512: f = (uint8_t)(fam - 5);
	sub	a, #0x05
	ld	yl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 513: x = (int16_t)(u & (BIT_U - 1));
	ld	a, xh
	and	a, #0x01
	ld	xh, a
	ldw	(0x01, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 514: d = (int16_t)(x - c_c0[f]);
	ldw	x, y
	clr	a
	ld	xh, a
	sllw	x
	ldw	x, (_c_c0+0, x)
	negw	x
	addw	x, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 515: if (d >= -EPS_HIST && d < EPS_HIST) {
	cpw	x, #0xffc0
	jrslt	00111$
	cpw	x, #0x0040
	jrsge	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 516: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
	addw	x, #0x0040
	sraw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 517: if (c_hist[f][b] < 255) c_hist[f][b]++;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 519: }
	popw	x
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 521: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function cal_add
;	-----------------------------------------
_cal_add:
	sub	sp, #12
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 525: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 526: if (cls < 0) return;
	ld	(0x0a, sp), a
	jrpl	00102$
	jp	00138$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if (lo > c_lo0) c_lo0 = lo;
	ldw	x, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: if (hi < c_hi0) c_hi0 = hi;
	ldw	y, (0x03, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 527: if (cls == 0) {
	tnz	(0x0a, sp)
	jrne	00116$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if (lo > c_lo0) c_lo0 = lo;
	pushw	x
	ldw	x, (0x03, sp)
	cpw	x, _c_lo0+0
	popw	x
	jrsle	00104$
	ldw	_c_lo0+0, x
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: if (hi < c_hi0) c_hi0 = hi;
	ldw	x, (0x03, sp)
	cpw	x, _c_hi0+0
	jrsge	00106$
	ldw	_c_hi0+0, y
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 530: if (c_n0 < 255) c_n0++;
	ld	a, _c_n0+0
	cp	a, #0xff
	jrnc	00117$
	inc	_c_n0+0
	jra	00117$
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 532: if (lo > c_lo1) c_lo1 = lo;
	pushw	x
	ldw	x, (0x03, sp)
	cpw	x, _c_lo1+0
	popw	x
	jrsle	00110$
	ldw	_c_lo1+0, x
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 533: if (hi < c_hi1) c_hi1 = hi;
	ldw	x, (0x03, sp)
	cpw	x, _c_hi1+0
	jrsge	00112$
	ldw	_c_hi1+0, y
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 534: if (c_n1 < 255) c_n1++;
	ld	a, _c_n1+0
	cp	a, #0xff
	jrnc	00117$
	inc	_c_n1+0
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 536: if ((fam == 5 || fam == 6) && lo >= 0) {
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 537: uint8_t f = (uint8_t)(fam - 5);
	ld	a, (0x15, sp)
	sub	a, #0x05
	ld	xl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 538: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 539: if (d >= -EPS_HIST && d < EPS_HIST) {
	ldw	(0x07, sp), x
	cpw	x, #0xffc0
	jrslt	00138$
	ldw	x, (0x07, sp)
	cpw	x, #0x0040
	jrsge	00138$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 540: if (cls == 0) {
	tnz	(0x0a, sp)
	jrne	00129$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 541: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 542: else if (d > c_labx0b[f]) c_labx0b[f] = d;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 544: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 545: else if (d < c_labx1b[f]) c_labx1b[f] = d;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 549: }
	ldw	x, (13, sp)
	addw	sp, #23
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 552: static uint8_t theta56(uint8_t f, int16_t *theta_out)
;	-----------------------------------------
;	 function theta56
;	-----------------------------------------
_theta56:
	sub	sp, #38
	ldw	(0x23, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 554: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	(0x01, sp), x
	ldw	x, (_c_labx0+0, x)
	ldw	y, (0x01, sp)
	ldw	y, (_c_labx1+0, y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 555: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 556: int16_t zlo = (int16_t)(x0 + 1);
	ldw	x, (0x03, sp)
	incw	x
	ldw	(0x09, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 557: int16_t zhi = x1;
	ldw	(0x0b, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 558: int16_t theta = 0;
	clrw	x
	ldw	(0x0d, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 559: uint8_t have_theta = 0;
	clr	(0x0f, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 560: int16_t top = 0;
	clrw	x
	ldw	(0x10, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 561: uint8_t have_top = 0, clear1 = 0;
	clr	(0x12, sp)
	clr	(0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 563: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
	ldw	x, #0xffe0
	cpw	x, (0x09, sp)
	jrslt	00102$
	ldw	(0x09, sp), x
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 564: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
	ldw	x, (0x0b, sp)
	cpw	x, #0x0020
	jrsle	00104$
	ldw	x, #0x0020
	ldw	(0x0b, sp), x
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
	exg	a, xl
	ld	a, #0x40
	exg	a, xl
	mul	x, a
	ldw	(0x14, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 565: if (zlo < zhi) {
	ldw	x, (0x09, sp)
	cpw	x, (0x0b, sp)
	jrslt	00489$
	jp	00126$
00489$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 566: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
	ldw	x, (0x09, sp)
	addw	x, #0x0040
	sraw	x
	exg	a, xl
	ld	(0x25, sp), a
	exg	a, xl
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 567: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
	ldw	x, (0x0b, sp)
	addw	x, #0x003f
	sraw	x
	exg	a, xl
	ld	(0x16, sp), a
	exg	a, xl
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 568: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
	ldw	y, (0x09, sp)
	ldw	(0x17, sp), y
	clrw	x
	ldw	(0x19, sp), x
	clrw	x
	ldw	(0x1b, sp), x
	clrw	x
	decw	x
	ldw	(0x1d, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
	ldw	x, (0x14, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x1f, sp), x
	clr	(0x26, sp)
00170$:
	ld	a, (0x25, sp)
	cp	a, (0x16, sp)
	jrugt	00253$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 571: if (c_hist[f][b]) {
	clrw	x
	ld	a, (0x25, sp)
	ld	xl, a
	addw	x, (0x1f, sp)
	ld	a, (x)
	jreq	00171$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 572: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
	ld	a, (0x25, sp)
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #0xffc1
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 573: int16_t gp = (int16_t)(x - prev);
	ldw	(0x21, sp), x
	subw	x, (0x17, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 574: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
	cpw	x, (0x1d, sp)
	jrsle	00106$
	ldw	(0x1d, sp), x
	ldw	y, (0x17, sp)
	ldw	(0x19, sp), y
	ldw	y, (0x21, sp)
	ldw	(0x1b, sp), y
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 575: prev = x;
	ldw	y, (0x21, sp)
	ldw	(0x17, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 576: nocc++;
	inc	(0x26, sp)
00171$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 570: for (b = blo; b <= bhi; b++) {
	inc	(0x25, sp)
	jra	00170$
00253$:
	ld	a, (0x26, sp)
	ld	xl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 580: int16_t gp = (int16_t)(zhi - prev);
	ldw	y, (0x0b, sp)
	subw	y, (0x17, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 581: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 583: if (nocc == 0) {
	ld	a, xl
	tnz	a
	jrne	00123$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 584: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 586: uint8_t ok = (bg >= EPS_GAP_MIN);
	ldw	y, (0x1d, sp)
	cpw	y, #0x0005
	jrslt	00497$
	clr	a
	.byte 0xc5
00497$:
	ld	a, #0x01
00498$:
	xor	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 587: if (ok && (uint8_t)(nocc + 1) >= 4) {
	ld	(0x26, sp), a
	jreq	00118$
	ld	a, xl
	inc	a
	cp	a, #0x04
	jrc	00118$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 588: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 589: ok = 0;
	clr	(0x26, sp)
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 591: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
	tnz	(0x26, sp)
	jreq	00126$
	ldw	x, (0x19, sp)
	addw	x, (0x1b, sp)
	sraw	x
	ldw	(0x0d, sp), x
	ld	a, #0x01
	ld	(0x0f, sp), a
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 594: if (has0 || has1) {
	tnz	(0x05, sp)
	jrne	00144$
	tnz	(0x08, sp)
	jrne	00505$
	jp	00245$
00505$:
00144$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 595: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
	ldw	x, #0xffe0
	ldw	(0x21, sp), x
	ldw	x, #0x0020
	ldw	(0x25, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 596: if (has0) {
	tnz	(0x05, sp)
	jreq	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 597: wlo = (int16_t)(x0 - EPS_SLACK1);
	ldw	x, (0x03, sp)
	subw	x, #0x0008
	ldw	(0x21, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 598: if (c_labx0b[f] > -0x4000 &&
	ldw	x, (0x01, sp)
	ldw	x, (_c_labx0b+0, x)
	cpw	x, #0xc000
	jrsle	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 599: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
	decw	x
	decw	x
	cpw	x, (0x21, sp)
	jrsle	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 600: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
	ldw	(0x21, sp), x
00131$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 602: if (has1) {
	tnz	(0x08, sp)
	jreq	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 603: whi = (int16_t)(x1 + EPS_SLACK1);
	ldw	x, (0x06, sp)
	addw	x, #0x0008
	ldw	(0x25, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 604: if (c_labx1b[f] < 0x3FFF &&
	ldw	x, (0x01, sp)
	ldw	x, (_c_labx1b+0, x)
	cpw	x, #0x3fff
	jrsge	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 605: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
	incw	x
	incw	x
	cpw	x, (0x25, sp)
	jrsge	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 606: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
	ldw	(0x25, sp), x
00136$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 608: if (wlo > whi) {
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 609: theta = (int16_t)((wlo + whi) >> 1);
	ldw	x, (0x21, sp)
	cpw	x, (0x25, sp)
	jrsle	00142$
	addw	x, (0x25, sp)
	sraw	x
	ldw	(0x0d, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 610: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
	jra	00245$
00142$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 612: int16_t th = have_theta ? theta : 0;
	tnz	(0x0f, sp)
	jreq	00175$
	ldw	y, (0x0d, sp)
	ldw	(0x1f, sp), y
	.byte 0xbc
00175$:
	clrw	x
	ldw	(0x1f, sp), x
00176$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 613: if (th < wlo) th = wlo;
	ldw	x, (0x1f, sp)
	cpw	x, (0x21, sp)
	jrsge	00138$
	ldw	y, (0x21, sp)
	ldw	(0x1f, sp), y
00138$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 614: if (th > whi) th = whi;
	ldw	x, (0x1f, sp)
	cpw	x, (0x25, sp)
	jrsle	00140$
	ldw	y, (0x25, sp)
	ldw	(0x1f, sp), y
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 615: theta = th;
	ldw	y, (0x1f, sp)
	ldw	(0x0d, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 616: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 619: for (b = 0; b < 64; b++) {
00245$:
	ldw	x, (0x14, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x21, sp), x
	clr	(0x26, sp)
00172$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 621: if (!c_hist[f][b]) continue;
	clrw	x
	ld	a, (0x26, sp)
	ld	xl, a
	addw	x, (0x21, sp)
	ld	a, (x)
	jreq	00157$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 622: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 623: if (d > EPS_CLEAR1) clear1 = 1;
	ld	a, (0x20, sp)
	cp	a, #0x12
	jrsle	00155$
	ld	a, #0x01
	ld	(0x13, sp), a
	jra	00157$
00155$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 624: else if (d > -EPS_CLAMP56) {
	ldw	x, (0x1f, sp)
	cpw	x, #0xffe8
	jrsle	00157$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 625: if (!have_top || d > top) top = d;
	tnz	(0x12, sp)
	jreq	00149$
	ldw	x, (0x1f, sp)
	cpw	x, (0x10, sp)
	jrsle	00150$
00149$:
	ldw	y, (0x1f, sp)
	ldw	(0x10, sp), y
00150$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 626: have_top = 1;
	ld	a, #0x01
	ld	(0x12, sp), a
00157$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 619: for (b = 0; b < 64; b++) {
	inc	(0x26, sp)
	ld	a, (0x26, sp)
	cp	a, #0x40
	jrc	00172$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 629: if (!clear1 && have_top) {
	tnz	(0x13, sp)
	jrne	00167$
	tnz	(0x12, sp)
	jreq	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 630: int16_t floor_ = (int16_t)(top + EPS_TOPM);
	ld	a, (0x11, sp)
	add	a, #0x03
	ld	(0x26, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x25, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 631: if (!have_theta || floor_ > theta) theta = floor_;
	tnz	(0x0f, sp)
	jreq	00159$
	ldw	x, (0x25, sp)
	cpw	x, (0x0d, sp)
	jrsle	00160$
00159$:
	ldw	y, (0x25, sp)
	ldw	(0x0d, sp), y
00160$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 632: have_theta = 1;
	ld	a, #0x01
	ld	(0x0f, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 633: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
	tnz	(0x08, sp)
	jreq	00167$
	ldw	x, (0x06, sp)
	incw	x
	incw	x
	cpw	x, (0x25, sp)
	jrsle	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 634: theta > (int16_t)(x1 + EPS_SLACK))
	cpw	x, (0x0d, sp)
	jrsge	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 635: theta = (int16_t)(x1 + EPS_SLACK);
	ldw	(0x0d, sp), x
00167$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 637: *theta_out = theta;
	ldw	x, (0x23, sp)
	ldw	y, (0x0d, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 638: return have_theta;
	ld	a, (0x0f, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 639: }
	addw	sp, #38
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 641: static void calibrate(void)
;	-----------------------------------------
;	 function calibrate
;	-----------------------------------------
_calibrate:
	sub	sp, #21
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 645: c_lo0 = c_lo1 = -0x4000;
	ldw	x, #0xc000
	ldw	_c_lo1+0, x
	ldw	x, #0xc000
	ldw	_c_lo0+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 646: c_hi0 = c_hi1 = 0x3FFF;
	ldw	x, #0x3fff
	ldw	_c_hi1+0, x
	ldw	x, #0x3fff
	ldw	_c_hi0+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 647: c_n0 = c_n1 = 0;
	clr	_c_n1+0
	clr	_c_n0+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 648: c_h0c = H0P; c_h1c = H1P;
	ldw	x, #0x009a
	ldw	_c_h0c+0, x
	ldw	x, #0x0134
	ldw	_c_h1c+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 649: c_d56[0] = c_d56[1] = 0;
	mov	_c_d56+1, #0x00
	mov	_c_d56+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 650: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 651: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: for (f = 0; f < 2; f++) {
	clr	(0x15, sp)
00138$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
	clrw	x
	ld	a, (0x15, sp)
	ld	xl, a
	sllw	x
	ldw	(0x11, sp), x
	ldw	y, x
	addw	y, #(_c_c0+0)
	ldw	x, (0x11, sp)
	ldw	x, (_c_gap56+0, x)
	ldw	(0x13, sp), x
	ldw	x, #0x01ce
	subw	x, (0x13, sp)
	sraw	x
	ldw	(y), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 655: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
	ld	a, (0x15, sp)
	ld	xl, a
	ld	a, #0x40
	mul	x, a
	addw	x, #(_c_hist+0)
	ldw	(0x13, sp), x
	clr	a
00136$:
	clrw	x
	ld	xl, a
	addw	x, (0x13, sp)
	clr	(x)
	inc	a
	cp	a, #0x40
	jrc	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 656: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
	ldw	x, (0x11, sp)
	addw	x, #(_c_labx0+0)
	clr	(0x1, x)
	ld	a, #0xc0
	ld	(x), a
	ldw	x, (0x11, sp)
	addw	x, #(_c_labx0b+0)
	clr	(0x1, x)
	ld	a, #0xc0
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 657: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
	ldw	x, (0x11, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1+0), x), y
	ldw	x, (0x11, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1b+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: for (f = 0; f < 2; f++) {
	inc	(0x15, sp)
	ld	a, (0x15, sp)
	cp	a, #0x02
	jrc	00138$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 659: ss_init();
	call	_ss_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 660: while (ss_next(&sg)) {
00112$:
	ldw	x, sp
	incw	x
	call	_ss_next
	ld	(0x15, sp), a
	jrne	00409$
	jp	00114$
00409$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 662: uint8_t known_all = 1;
	ld	a, #0x01
	ld	(0x11, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 664: cal_cloud(sg.u, sg.fam);
	ld	a, (0x09, sp)
	ldw	x, (0x05, sp)
	call	_cal_cloud
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 665: if (sg.k1 > NB) continue;
	ldw	x, (0x03, sp)
	cpw	x, #0x00c0
	jrugt	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 666: e = (sg.k1 < NB) ? sg.k1 : NB;
	cpw	x, #0x00c0
	jrnc	00146$
	ldw	(0x14, sp), x
	jra	00147$
00146$:
	ldw	x, #0x00c0
	ldw	(0x14, sp), x
00147$:
	ldw	y, (0x14, sp)
	ldw	(0x12, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: for (t = sg.k0; t < e; t++)
	ldw	x, sp
	incw	x
	ldw	(0x0e, sp), x
	ldw	x, (x)
	ldw	(0x14, sp), x
00141$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 668: if (known_bit(t) < 0) { known_all = 0; break; }
	ldw	x, (0x14, sp)
	cpw	x, (0x12, sp)
	jrnc	00107$
	call	_known_bit
	tnz	a
	jrpl	00142$
	clr	(0x11, sp)
	jra	00107$
00142$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: for (t = sg.k0; t < e; t++)
	ldw	x, (0x14, sp)
	incw	x
	ldw	(0x14, sp), x
	jra	00141$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: if (!known_all) continue;
	tnz	(0x11, sp)
	jreq	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 670: a_bounds(sg.k0, sg.k1, &amin, &amax);
	ldw	y, (0x03, sp)
	ldw	x, (0x0e, sp)
	ldw	x, (x)
	ldw	(0x14, sp), x
	ldw	x, sp
	addw	x, #12
	pushw	x
	ldw	x, sp
	addw	x, #12
	pushw	x
	pushw	y
	ldw	x, (0x1a, sp)
	call	_a_bounds
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 671: if (amin == amax)
	ldw	x, (0x0a, sp)
	cpw	x, (0x0c, sp)
	jrne	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 672: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
	ld	a, (0x09, sp)
	ldw	y, (0x07, sp)
	ldw	(0x10, sp), y
	ldw	y, (0x05, sp)
	ldw	(0x12, sp), y
	ldw	y, (0x03, sp)
	ldw	x, (0x0e, sp)
	ldw	x, (x)
	ldw	(0x14, sp), x
	ldw	x, (0x0a, sp)
	pushw	x
	push	a
	ldw	x, (0x13, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	pushw	y
	ldw	x, (0x1d, sp)
	call	_cal_add
	jp	00112$
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 676: int16_t h0 = H0P, h1 = H1P;
	ldw	x, #0x009a
	ldw	(0x10, sp), x
	ldw	x, #0x0134
	ldw	(0x12, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 677: if (c_n0 >= LAB_MIN) {
	ld	a, _c_n0+0
	cp	a, #0x03
	jrc	00119$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 678: int16_t h = (c_lo0 > c_hi0) ? (int16_t)((c_lo0 + c_hi0) >> 1)
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
	ldw	(0x14, sp), x
	jra	00153$
00152$:
	ldw	x, #0x009a
	ldw	(0x14, sp), x
00153$:
	ldw	x, (0x14, sp)
00151$:
00149$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 680: if (h >= H0_LO && h <= H0_HI) h0 = h;
	ldw	y, x
	cpw	x, #0x0070
	jrslt	00119$
	cpw	x, #0x00c0
	jrsgt	00119$
	ldw	(0x10, sp), y
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 682: if (c_n1 >= LAB_MIN) {
	ld	a, _c_n1+0
	cp	a, #0x03
	jrc	00124$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: int16_t h = (c_lo1 > c_hi1) ? (int16_t)((c_lo1 + c_hi1) >> 1)
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
	ldw	(0x14, sp), x
	jra	00159$
00158$:
	ldw	x, #0x0134
	ldw	(0x14, sp), x
00159$:
	ldw	x, (0x14, sp)
00157$:
00155$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 685: if (h >= H1_LO && h <= H1_HI) h1 = h;
	ldw	y, x
	cpw	x, #0x00fc
	jrslt	00124$
	cpw	x, #0x0178
	jrsgt	00124$
	ldw	(0x12, sp), y
00124$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 687: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
	ldw	x, (0x12, sp)
	subw	x, (0x10, sp)
	cpw	x, #0x0070
	jrslt	00125$
	cpw	x, #0x00c4
	jrsle	00126$
00125$:
	ldw	x, #0x009a
	ldw	(0x10, sp), x
	ldw	x, #0x0134
	ldw	(0x12, sp), x
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 688: c_h0c = h0; c_h1c = h1;
	ldw	x, (0x10, sp)
	ldw	_c_h0c+0, x
	ldw	x, (0x12, sp)
	ldw	_c_h1c+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: for (f = 0; f < 2; f++) {
	clr	(0x15, sp)
00143$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 692: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
	ldw	x, sp
	addw	x, #12
	ld	a, (0x15, sp)
	call	_theta56
	ld	(0x14, sp), a
	clrw	x
	ld	a, (0x15, sp)
	ld	xl, a
	addw	x, #(_c_d56+0)
	ldw	(0x11, sp), x
	tnz	(0x14, sp)
	jrne	00129$
	ldw	x, (0x11, sp)
	clr	(x)
	jra	00134$
00129$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 693: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
	ldw	x, _c_h0c+0
	addw	x, _c_h1c+0
	ldw	(0x13, sp), x
	clrw	x
	ld	a, (0x15, sp)
	ld	xl, a
	sllw	x
	ldw	y, x
	ldw	x, (_c_gap56+0, x)
	negw	x
	addw	x, (0x13, sp)
	sraw	x
	ldw	(0x13, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 694: delta = (int16_t)(th + c_c0[f] - cfit);
	ldw	x, y
	ldw	x, (_c_c0+0, x)
	addw	x, (0x0c, sp)
	subw	x, (0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 695: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
	cpw	x, #0xffe8
	jrsge	00131$
	ldw	x, #0xffe8
00131$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 696: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
	ldw	y, x
	cpw	y, #0x0018
	jrsle	00133$
	ldw	x, #0x0018
00133$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 697: c_d56[f] = (int8_t)delta;
	ld	a, xl
	ldw	x, (0x11, sp)
	ld	(x), a
00134$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: for (f = 0; f < 2; f++) {
	inc	(0x15, sp)
	ld	a, (0x15, sp)
	cp	a, #0x02
	jrc	00143$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 699: }
	addw	sp, #21
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 703: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
;	-----------------------------------------
;	 function hinge
;	-----------------------------------------
_hinge:
	pushw	x
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 705: int16_t g = 0;
	clrw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 706: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
	subw	y, (0x07, sp)
	cpw	y, #0x0000
	jrsle	00102$
	ldw	x, y
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 707: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
	ldw	y, (0x07, sp)
	subw	y, (0x05, sp)
	ldw	(0x01, sp), y
	cpw	x, (0x01, sp)
	jrsge	00104$
	ldw	x, (0x01, sp)
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 708: return (uint16_t)g;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 709: }
	ldw	y, (3, sp)
	addw	sp, #8
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 712: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function decide
;	-----------------------------------------
_decide:
	sub	sp, #24
	ldw	(0x15, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 716: int16_t L = (int16_t)(k1 - k0);
	ldw	x, (0x1b, sp)
	subw	x, (0x15, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 717: int16_t acap = (L < A_CAP) ? L : A_CAP;
	ldw	(0x05, sp), x
	cpw	x, #0x000f
	jrslt	00144$
	ldw	x, #0x000f
00144$:
	ldw	(0x07, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 718: int16_t h0e = c_h0c, h1e = c_h1c;
	ldw	x, _c_h0c+0
	ldw	(0x09, sp), x
	ldw	x, _c_h1c+0
	ldw	(0x0b, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 722: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 723: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 724: d_inter = 0;
	clrw	x
	ldw	_d_inter+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: for (a = 0; a <= acap; a++) {
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 728: if (a == 0) {
	ldw	x, (0x17, sp)
	jrne	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 729: c = hinge(u, v, h0e);
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 730: it = (u < h0e && h0e <= v);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
	ldw	y, (0x17, sp)
	ldw	(0x11, sp), y
	ldw	x, y
	decw	x
	clr	a
	rlwa	x
	sllw	x
	addw	x, (0x0b, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 733: c = hinge(u, v, h);
	ldw	(0x13, sp), x
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 734: it = (u < h && h <= v);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 735: if (a < L) {
	ldw	x, (0x17, sp)
	cpw	x, (0x05, sp)
	jrsge	00114$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 736: int16_t h2 = (int16_t)(a * BIT_U + h0e);
	rlwa	x
	ld	a, (0x12, sp)
	rrwa	x
	exg	a, xl
	clr	a
	exg	a, xl
	sllw	x
	addw	x, (0x09, sp)
	ldw	(0x13, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 737: uint16_t c2 = hinge(u, v, h2);
	push	a
	ldw	x, (0x14, sp)
	pushw	x
	ldw	x, (0x22, sp)
	pushw	x
	ldw	x, (0x22, sp)
	call	_hinge
	pop	a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 738: if (c2 < c) c = c2;
	cpw	x, (0x0f, sp)
	jrnc	00106$
	ldw	(0x0f, sp), x
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 739: if (u < h2 && h2 <= v) it = 1;
	ldw	x, (0x1d, sp)
	cpw	x, (0x13, sp)
	jrsge	00114$
	ldw	x, (0x13, sp)
	cpw	x, (0x1f, sp)
	jrsgt	00114$
	ld	a, #0x01
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 742: d_costs[a] = c;
	ldw	x, (0x17, sp)
	sllw	x
	ldw	y, (0x0f, sp)
	ldw	((_d_costs+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 743: if (it) d_inter |= (uint16_t)(1u << a);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: for (a = 0; a <= acap; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jp	00133$
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 746: bc = 0xFFFF; bi = 1; *a_free = 0;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 747: for (a = 0; a <= acap; a++) {
	clrw	x
	ldw	(0x17, sp), x
00136$:
	ldw	x, (0x17, sp)
	cpw	x, (0x07, sp)
	jrsgt	00123$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 748: uint8_t it = (uint8_t)((d_inter >> a) & 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 749: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 750: bc = d_costs[a]; bi = it; *a_free = a;
	ldw	(0x10, sp), x
	ld	(0x12, sp), a
	ldw	x, (0x13, sp)
	ldw	y, (0x17, sp)
	ldw	(x), y
00137$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 747: for (a = 0; a <= acap; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jra	00136$
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 753: a_bounds(k0, k1, &amin, &amax);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 754: lo = (amin > 0) ? amin : 0;
	ldw	x, (0x01, sp)
	cpw	x, #0x0000
	jrsgt	00152$
	clrw	x
00152$:
	ldw	(0x0c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 755: hi = (amax < acap) ? amax : acap;
	ldw	x, (0x03, sp)
	cpw	x, (0x07, sp)
	jrsge	00153$
	ldw	x, (0x03, sp)
	.byte 0xc5
00153$:
	ldw	x, (0x07, sp)
00154$:
	ldw	(0x0e, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 756: if (lo > hi) { lo = 0; hi = acap; }
	ldw	x, (0x0c, sp)
	cpw	x, (0x0e, sp)
	jrsle	00125$
	clrw	x
	ldw	(0x0c, sp), x
	ldw	y, (0x07, sp)
	ldw	(0x0e, sp), y
00125$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 757: bc = 0xFFFF; bi = 1; *a_hat = lo;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: for (a = lo; a <= hi; a++) {
	ldw	y, (0x0c, sp)
	ldw	(0x17, sp), y
00139$:
	ldw	x, (0x17, sp)
	cpw	x, (0x0e, sp)
	jrsgt	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 759: uint8_t it = (uint8_t)((d_inter >> a) & 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 760: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 761: bc = d_costs[a]; bi = it; *a_hat = a;
	ldw	(0x10, sp), x
	ld	(0x12, sp), a
	ldw	x, (0x13, sp)
	ldw	y, (0x17, sp)
	ldw	(x), y
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: for (a = lo; a <= hi; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jra	00139$
00131$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 764: *lo_out = lo; *hi_out = hi;
	ldw	x, (0x26, sp)
	ldw	y, (0x0c, sp)
	ldw	(x), y
	ldw	x, (0x28, sp)
	ldw	y, (0x0e, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 765: return acap;
	ldw	x, (0x07, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 766: }
	ldw	y, (25, sp)
	addw	sp, #41
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 769: static void cand_insert(uint16_t k, uint8_t m)
;	-----------------------------------------
;	 function cand_insert
;	-----------------------------------------
_cand_insert:
	sub	sp, #7
	ldw	(0x05, sp), x
	ld	(0x04, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 771: uint8_t i = v_ncand, j;
	ld	a, _v_ncand+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 772: while (i > 0 && v_cand_m[i - 1] > m) i--;
	ld	(0x03, sp), a
	ld	(0x07, sp), a
00102$:
	tnz	(0x07, sp)
	jreq	00132$
	ld	a, (0x07, sp)
	dec	a
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	ld	a, (_v_cand_m+0, x)
	cp	a, (0x04, sp)
	jrule	00132$
	dec	(0x07, sp)
	jra	00102$
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 773: if (i >= A_MAX) return;
	ld	a, (0x07, sp)
	ld	(0x01, sp), a
	cp	a, #0x05
	jrnc	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 774: j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
	ld	a, _v_ncand+0
	cp	a, #0x05
	jrnc	00114$
	ld	a, (0x03, sp)
	.byte 0xc5
00114$:
	ld	a, #0x04
00115$:
	ld	(0x07, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 775: while (j > i) {
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 776: v_cand_t[j] = v_cand_t[j - 1];
	ld	a, (0x07, sp)
	cp	a, (0x01, sp)
	jrule	00109$
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #(_v_cand_t+0)
	exgw	x, y
	ld	a, (0x07, sp)
	dec	a
	ld	(0x03, sp), a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x02, sp), a
	ldw	x, (0x02, sp)
	sllw	x
	ldw	x, (_v_cand_t+0, x)
	ldw	(y), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 777: v_cand_m[j] = v_cand_m[j - 1];
	clrw	x
	ld	a, (0x07, sp)
	ld	xl, a
	addw	x, #(_v_cand_m+0)
	ldw	y, (0x02, sp)
	addw	y, #(_v_cand_m+0)
	ld	a, (y)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 778: j--;
	dec	(0x07, sp)
	jra	00107$
00109$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 780: v_cand_t[i] = k;
	ld	a, (0x01, sp)
	clrw	x
	ld	xl, a
	sllw	x
	ldw	y, (0x05, sp)
	ldw	((_v_cand_t+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 781: v_cand_m[i] = m;
	clrw	x
	ld	a, (0x01, sp)
	ld	xl, a
	ld	a, (0x04, sp)
	ld	((_v_cand_m+0), x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 782: if (v_ncand < A_MAX) v_ncand++;
	ld	a, _v_ncand+0
	cp	a, #0x05
	jrnc	00112$
	inc	_v_ncand+0
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 783: }
	addw	sp, #7
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 785: static void decide_pass(void)
;	-----------------------------------------
;	 function decide_pass
;	-----------------------------------------
_decide_pass:
	sub	sp, #33
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 789: for (t = 0; t < NBB; t++) d_bits[t] = 0;
	clr	a
00168$:
	clrw	x
	ld	xl, a
	clr	((_d_bits+0), x)
	inc	a
	cp	a, #0x18
	jrc	00168$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 790: d_infeas = 0; d_laberr = 0; d_nseg = 0;
	clrw	x
	ldw	_d_infeas+0, x
	clrw	x
	ldw	_d_laberr+0, x
	clrw	x
	ldw	_d_nseg+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 791: v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1;
	clr	_v_ncand+0
	clrw	x
	ldw	_v_nweak+0, x
	clrw	x
	ldw	_v_ntied+0, x
	clrw	x
	decw	x
	ldw	_v_tiepend+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 792: ss_init();
	call	_ss_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 793: while (ss_next(&sg)) {
00165$:
	ldw	x, sp
	incw	x
	call	_ss_next
	tnz	a
	jrne	00557$
	jp	00185$
00557$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 796: int16_t tie_here = -1, ins0 = -1, ins1 = -1;
	clrw	x
	decw	x
	ldw	(0x12, sp), x
	clrw	x
	decw	x
	ldw	(0x18, sp), x
	clrw	x
	decw	x
	ldw	(0x1a, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 799: d_nseg++;
	ldw	x, _d_nseg+0
	incw	x
	ldw	_d_nseg+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: if (sg.k0 >= NB) continue;
	ldw	x, sp
	incw	x
	ldw	(0x14, sp), x
	ldw	x, (x)
	ldw	(0x1c, sp), x
	cpw	x, #0x00c0
	jrnc	00165$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: &a_hat, &a_free, &lo, &hi);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 801: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
	ld	a, (0x09, sp)
	ldw	y, (0x07, sp)
	ldw	x, (0x05, sp)
	ldw	(0x1e, sp), x
	ldw	x, (0x03, sp)
	ldw	(0x20, sp), x
	ldw	x, sp
	addw	x, #16
	pushw	x
	ldw	x, sp
	addw	x, #16
	pushw	x
	ldw	x, sp
	addw	x, #16
	pushw	x
	ldw	x, sp
	addw	x, #16
	pushw	x
	push	a
	pushw	y
	ldw	x, (0x29, sp)
	pushw	x
	ldw	x, (0x2d, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	call	_decide
	ldw	(0x1c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 803: c_hat = d_costs[a_hat];
	ldw	x, (0x0a, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 804: if (c_hat > INFEAS_U) d_infeas++;
	cpw	x, #0x00a0
	jrule	00105$
	ldw	x, _d_infeas+0
	incw	x
	ldw	_d_infeas+0, x
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: kk1 = (sg.k1 < NB) ? sg.k1 : NB;
	ldw	x, (0x03, sp)
	cpw	x, #0x00c0
	jrnc	00187$
	exg	a, xl
	ld	(0x21, sp), a
	exg	a, xl
	clr	a
	jra	00188$
00187$:
	ld	a, #0xc0
	ld	(0x21, sp), a
	clr	a
00188$:
	ld	(0x16, sp), a
	ld	a, (0x21, sp)
	ld	(0x17, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 806: known_all = 1;
	ld	a, #0x01
	ld	(0x1e, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: for (t = sg.k0; t < kk1; t++)
	ldw	x, (0x14, sp)
	ldw	x, (x)
	ldw	(0x20, sp), x
00171$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 808: if (known_bit(t) < 0) { known_all = 0; break; }
	ldw	x, (0x20, sp)
	cpw	x, (0x16, sp)
	jrnc	00108$
	call	_known_bit
	tnz	a
	jrpl	00172$
	clr	(0x1e, sp)
	jra	00108$
00172$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: for (t = sg.k0; t < kk1; t++)
	ldw	x, (0x20, sp)
	incw	x
	ldw	(0x20, sp), x
	jra	00171$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 809: dead = 0; nins = 0;
	clr	(0x1f, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 810: for (a = 0; a <= acap; a++)
	clr	a
	clrw	x
	ldw	(0x20, sp), x
00174$:
	ldw	x, (0x20, sp)
	cpw	x, (0x1c, sp)
	jrsgt	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 811: if ((d_inter >> a) & 1) nins++;
	push	a
	ldw	x, _d_inter+0
	ld	a, (0x22, sp)
	jreq	00566$
00565$:
	srlw	x
	dec	a
	jrne	00565$
00566$:
	pop	a
	srlw	x
	jrnc	00175$
	inc	a
00175$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 810: for (a = 0; a <= acap; a++)
	ldw	x, (0x20, sp)
	incw	x
	ldw	(0x20, sp), x
	jra	00174$
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 812: if (nins >= 2) dead = 1;
	cp	a, #0x02
	jrc	00113$
	ld	a, #0x01
	ld	(0x1f, sp), a
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 813: if (known_all && lo == hi && a_free != lo && !dead)
	tnz	(0x1e, sp)
	jreq	00115$
	ldw	x, (0x0e, sp)
	cpw	x, (0x10, sp)
	jrne	00115$
	ldw	x, (0x0c, sp)
	cpw	x, (0x0e, sp)
	jreq	00115$
	tnz	(0x1f, sp)
	jrne	00115$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: d_laberr++;
	ldw	x, _d_laberr+0
	incw	x
	ldw	_d_laberr+0, x
00115$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 819: for (a = lo; a <= hi; a++) {
	ldw	x, (0x0e, sp)
	clr	a
	ldw	(0x20, sp), x
00177$:
	ldw	x, (0x20, sp)
	cpw	x, (0x10, sp)
	jrsgt	00126$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 820: if ((d_inter >> a) & 1) {
	push	a
	ldw	x, _d_inter+0
	ld	a, (0x22, sp)
	jreq	00580$
00579$:
	srlw	x
	dec	a
	jrne	00579$
00580$:
	pop	a
	srlw	x
	jrnc	00178$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 821: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
	tnz	a
	jrne	00122$
	ldw	y, (0x20, sp)
	ldw	(0x18, sp), y
	jra	00123$
00122$:
	cp	a, #0x01
	jrne	00123$
	ldw	y, (0x20, sp)
	ldw	(0x1a, sp), y
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 822: nins++;
	inc	a
00178$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 819: for (a = lo; a <= hi; a++) {
	ldw	x, (0x20, sp)
	incw	x
	ldw	(0x20, sp), x
	jra	00177$
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: if (sg.k0 >= NB) continue;
	ldw	x, (0x14, sp)
	ldw	x, (x)
	ldw	(0x20, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
	cp	a, #0x02
	jrc	00130$
	ldw	x, (0x0a, sp)
	cpw	x, (0x18, sp)
	jreq	00129$
	ldw	x, (0x0a, sp)
	cpw	x, (0x1a, sp)
	jrne	00130$
00129$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 826: uint16_t tt = (uint16_t)(sg.k0 + ins0);
	ldw	x, (0x18, sp)
	addw	x, (0x20, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 827: if (tt < NB) tie_here = (int16_t)tt;
	cpw	x, #0x00c0
	jrnc	00130$
	ldw	(0x12, sp), x
00130$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: for (t = sg.k0; t < kk1; t++) {
	ldw	y, (0x20, sp)
	ldw	(0x1e, sp), y
00183$:
	ldw	x, (0x1e, sp)
	cpw	x, (0x16, sp)
	jrc	00595$
	jp	00159$
00595$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 831: int16_t off = (int16_t)(t - sg.k0);
	ldw	x, (0x14, sp)
	ldw	x, (x)
	negw	x
	addw	x, (0x1e, sp)
	ldw	(0x18, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 832: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
	clrw	x
	decw	x
	ldw	(0x1a, sp), x
	clrw	x
	decw	x
	ldw	(0x1c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 833: if (off < a_hat) BSET(d_bits, t);
	ldw	x, (0x18, sp)
	cpw	x, (0x0a, sp)
	jrsge	00134$
	ldw	x, (0x1e, sp)
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	(0x20, sp), a
	ld	a, (0x1f, sp)
	and	a, #0x07
	ld	(0x21, sp), a
	ld	a, #0x01
	push	a
	ld	a, (0x22, sp)
	jreq	00598$
00597$:
	sll	(1, sp)
	dec	a
	jrne	00597$
00598$:
	pop	a
	or	a, (0x20, sp)
	ld	(x), a
00134$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 834: for (a = lo; a <= hi; a++) {
	ldw	y, (0x0e, sp)
	ldw	(0x20, sp), y
00180$:
	ldw	x, (0x20, sp)
	cpw	x, (0x10, sp)
	jrsgt	00142$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 835: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
	ldw	x, (0x20, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
	pushw	x
	ldw	x, (0x22, sp)
	cpw	x, (0x1a, sp)
	popw	x
	jrsle	00140$
	cpw	x, (0x1c, sp)
	jrnc	00181$
	ldw	(0x1c, sp), x
	jra	00181$
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 836: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
	cpw	x, (0x1a, sp)
	jrnc	00181$
	ldw	(0x1a, sp), x
00181$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 834: for (a = lo; a <= hi; a++) {
	ldw	x, (0x20, sp)
	incw	x
	ldw	(0x20, sp), x
	jra	00180$
00142$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 838: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
	ldw	x, (0x1a, sp)
	incw	x
	jreq	00145$
	ldw	x, (0x1c, sp)
	incw	x
	jrne	00146$
00145$:
	ldw	x, #0x00ff
	ldw	(0x20, sp), x
	jra	00147$
00146$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 840: int16_t dm = (int16_t)(c0m - c1m);
	ldw	x, (0x1a, sp)
	subw	x, (0x1c, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 841: if (dm < 0) dm = (int16_t)-dm;
	ldw	(0x20, sp), x
	tnzw	x
	jrpl	00144$
	neg	(0x21, sp)
	clr	a
	sbc	a, (0x20, sp)
	ld	(0x20, sp), a
00144$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 842: m = (dm > 255) ? 255 : (uint16_t)dm;
	ldw	x, #0x00ff
	cpw	x, (0x20, sp)
	jrsgt	00189$
	ldw	(0x20, sp), x
00189$:
00147$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 844: if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
	ldw	x, (0x1e, sp)
	cpw	x, (0x12, sp)
	jreq	00149$
	cpw	x, _v_tiepend+0
	jrne	00150$
00149$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 845: m = 0;                       /* decided by tie-break */
	clrw	x
	ldw	(0x20, sp), x
00150$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 846: if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
	ldw	y, (0x1e, sp)
	ldw	(0x1c, sp), y
	ldw	x, y
	cpw	x, #0x0020
	jrc	00184$
	ldw	x, (0x1e, sp)
	cpw	x, #0x00a0
	jrnc	00184$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 847: if (m <= MG_MAX) {
	ldw	x, (0x20, sp)
	cpw	x, #0x0008
	jrugt	00184$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 848: uint16_t k = t - PP_LO;
	ldw	x, (0x1c, sp)
	subw	x, #0x0020
	ldw	(0x1c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 849: v_nweak++;
	ldw	x, _v_nweak+0
	incw	x
	ldw	_v_nweak+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 850: if (m == 0) v_ntied++;
	ldw	x, (0x20, sp)
	jrne	00153$
	ldw	x, _v_ntied+0
	incw	x
	ldw	_v_ntied+0, x
00153$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 851: cand_insert(k, (uint8_t)m);
	ld	a, (0x21, sp)
	ldw	x, (0x1c, sp)
	call	_cand_insert
00184$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: for (t = sg.k0; t < kk1; t++) {
	ldw	x, (0x1e, sp)
	incw	x
	ldw	(0x1e, sp), x
	jp	00183$
00159$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 855: if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
	ldw	x, _v_tiepend+0
	ldw	y, (0x16, sp)
	ldw	(0x20, sp), y
	tnzw	x
	jrmi	00161$
	ldw	x, (0x20, sp)
	cpw	x, _v_tiepend+0
	jrsle	00161$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 856: v_tiepend = -1;                  /* consumed              */
	clrw	x
	decw	x
	ldw	_v_tiepend+0, x
00161$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 857: if (tie_here >= (int16_t)kk1)
	ldw	x, (0x12, sp)
	cpw	x, (0x20, sp)
	jrsge	00625$
	jp	00165$
00625$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 858: v_tiepend = tie_here;            /* lands in next segment */
	ldw	x, (0x12, sp)
	ldw	_v_tiepend+0, x
	jp	00165$
00185$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 860: }
	addw	sp, #33
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 970: static uint8_t chase(uint8_t *out)
;	-----------------------------------------
;	 function chase
;	-----------------------------------------
_chase:
	sub	sp, #7
	ldw	(0x04, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: for (p = 0; p < NPP; p++) {
	clr	(0x06, sp)
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 975: uint8_t val = 0;
	clr	(0x03, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 976: uint16_t base = PP_LO + ((uint16_t)p << 3);
	ld	a, (0x06, sp)
	sll	a
	sll	a
	sll	a
	add	a, #0x20
	ld	yl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (j = 0; j < 8; j++)
	clr	(0x07, sp)
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: val = (uint8_t)((val << 1) | BGET(d_bits, base + j));
	ld	a, (0x03, sp)
	sll	a
	ld	(0x01, sp), a
	ld	a, (0x07, sp)
	ld	(0x03, sp), a
	clr	(0x02, sp)
	ldw	x, y
	clr	a
	ld	xh, a
	addw	x, (0x02, sp)
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	add	a, (0x07, sp)
	and	a, #0x07
	jreq	00174$
00173$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00173$
00174$:
	ld	a, xl
	and	a, #0x01
	or	a, (0x01, sp)
	ld	(0x03, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (j = 0; j < 8; j++)
	inc	(0x07, sp)
	ld	a, (0x07, sp)
	cp	a, #0x08
	jrc	00106$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 979: d_pp[p] = val;
	clrw	x
	ld	a, (0x06, sp)
	ld	xl, a
	ld	a, (0x03, sp)
	ld	((_d_pp+0), x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: for (p = 0; p < NPP; p++) {
	inc	(0x06, sp)
	ld	a, (0x06, sp)
	cp	a, #0x10
	jrc	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 981: dec_info.n_weak = v_nweak;
	mov	_dec_info+6, _v_nweak+1
	mov	_dec_info+5, _v_nweak+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 982: dec_info.n_tied = v_ntied;
	mov	_dec_info+8, _v_ntied+1
	mov	_dec_info+7, _v_ntied+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 986: if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
	ldw	x, _v_ntied+0
	cpw	x, #0x0008
	jrule	00126$
	mov	_dec_info+1, #0x05
	clr	a
	jra	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 987: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
00126$:
	clr	a
00110$:
	clrw	y
	ld	yl, a
	addw	y, (0x04, sp)
	clrw	x
	ld	xl, a
	addw	x, #(_d_pp+0)
	push	a
	ld	a, (x)
	ld	(y), a
	pop	a
	inc	a
	cp	a, #0x10
	jrc	00110$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 988: return DEC_LEGACY;
	ld	a, #0x03
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1036: }
	addw	sp, #7
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1040: uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
;	-----------------------------------------
;	 function ws_decode_ex
;	-----------------------------------------
_ws_decode_ex:
	sub	sp, #6
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1044: dec_info.path = DEC_REFUSE;
	ldw	x, #(_dec_info+0)
	ldw	(0x01, sp), x
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1045: dec_info.cause = CAUSE_NONE;
	mov	_dec_info+1, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1046: dec_info.trials = 0;
	mov	_dec_info+2, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1047: dec_info.alias_cmp = 0;
	mov	_dec_info+3, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1048: dec_info.chased = 0;
	mov	_dec_info+4, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1049: dec_info.n_weak = 0;
	ldw	x, #(_dec_info+5)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1050: dec_info.n_tied = 0;
	ldw	x, #(_dec_info+7)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1051: dec_info.K = 0;
	ldw	x, #(_dec_info+9)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1052: dec_info.tau = 0;
	ldw	x, #(_dec_info+11)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1053: dec_info.violations = 0;
	mov	_dec_info+13, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: dec_info.infeasible = 0;
	ldw	x, #(_dec_info+14)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1055: dec_info.label_err = 0;
	ldw	x, #(_dec_info+16)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1056: dec_info.n_seg = 0;
	ldw	x, #(_dec_info+18)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1057: scan_cap = cap;
	ldw	_scan_cap+0, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1058: scan_len = ncap;
	ldw	x, (0x09, sp)
	ldw	_scan_len+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1059: if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
	call	_seed
	tnz	a
	jrne	00132$
	mov	_dec_info+1, #0x01
	clr	a
	jp	00119$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1060: for (r = 0; r < 2; r++) refine();
00132$:
	ld	a, #0x02
00116$:
	push	a
	call	_refine
	pop	a
	dec	a
	jrne	00116$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1061: calibrate();
	call	_calibrate
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1062: decide_pass();
	call	_decide_pass
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1063: dec_info.K = g_K;
	mov	_dec_info+10, _g_K+1
	mov	_dec_info+9, _g_K+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1064: dec_info.tau = g_tau;
	mov	_dec_info+12, _g_tau+1
	mov	_dec_info+11, _g_tau+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1065: dec_info.infeasible = d_infeas;
	mov	_dec_info+15, _d_infeas+1
	mov	_dec_info+14, _d_infeas+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1066: dec_info.label_err = d_laberr;
	mov	_dec_info+17, _d_laberr+1
	mov	_dec_info+16, _d_laberr+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: dec_info.n_seg = d_nseg;
	mov	_dec_info+19, _d_nseg+1
	mov	_dec_info+18, _d_nseg+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: for (t = 0; t < NB; t++) {
	clr	(0x04, sp)
	clrw	x
	ldw	(0x05, sp), x
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1069: int8_t kb = known_bit(t);
	ldw	x, (0x05, sp)
	call	_known_bit
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1070: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
	ld	(0x03, sp), a
	jrmi	00118$
	ldw	x, (0x05, sp)
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x06, sp)
	and	a, #0x07
	jreq	00207$
00206$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00206$
00207$:
	ld	a, xl
	and	a, #0x01
	cp	a, (0x03, sp)
	jreq	00118$
	inc	(0x04, sp)
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: for (t = 0; t < NB; t++) {
	ldw	x, (0x05, sp)
	incw	x
	ldw	(0x05, sp), x
	cpw	x, #0x00c0
	jrc	00117$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1072: dec_info.violations = viol;
	ldw	x, #(_dec_info+13)
	ld	a, (0x04, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1073: if (viol > 0)               { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
	tnz	(0x04, sp)
	jreq	00109$
	mov	_dec_info+1, #0x02
	clr	a
	jra	00119$
00109$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1074: if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
	ldw	x, _d_infeas+0
	cpw	x, #0x0004
	jrule	00111$
	mov	_dec_info+1, #0x03
	clr	a
	jra	00119$
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1075: if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
	ldw	x, _d_laberr+0
	cpw	x, #0x0006
	jrule	00113$
	mov	_dec_info+1, #0x04
	clr	a
	jra	00119$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1076: dec_info.path = chase(out);                                      /* R5..R8 inside */
	ldw	x, (0x0b, sp)
	call	_chase
	ldw	x, (0x01, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1077: return dec_info.path;
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1078: }
	ldw	x, (7, sp)
	addw	sp, #12
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1080: int16_t dec_eps_centi(void)
;	-----------------------------------------
;	 function dec_eps_centi
;	-----------------------------------------
_dec_eps_centi:
	sub	sp, #8
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1085: return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
	ldw	x, _dec_info+9
	ldw	(0x03, sp), x
	clrw	y
	ld	a, #0xcd
	sub	a, (0x04, sp)
	ld	(0x08, sp), a
	ld	a, #0xcc
	sbc	a, (0x03, sp)
	ld	(0x07, sp), a
	clrw	x
	jrnc	00103$
	decw	x
00103$:
	pushw	y
	ld	a, (0x0a, sp)
	push	a
	ld	a, (0x0a, sp)
	push	a
	pushw	x
	push	#0x10
	push	#0x27
	clrw	x
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1086: / (int32_t)dec_info.K);
	call	__mullong
	addw	sp, #8
	ldw	(0x07, sp), y
	popw	y
	ld	a, (0x04, sp)
	push	a
	ld	a, (0x04, sp)
	push	a
	pushw	y
	pushw	x
	ldw	x, (0x0b, sp)
	pushw	x
	call	__divslong
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1087: }
	addw	sp, #16
	ret
	.area CODE
	.area CONST
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
	.area INITIALIZER
	.area CABS (ABS)
