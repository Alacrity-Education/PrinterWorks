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
	.globl _scan_sfa
	.globl _scan_fb
	.globl _scan_fa
	.globl _scan_rb
	.globl _scan_ra
	.globl _scan_len
	.globl _scan_cap
	.globl _ws_decode_ex
	.globl _dec_eps_centi
;--------------------------------------------------------
; ram data
;--------------------------------------------------------
	.area DATA
_scan_cap::
	.ds 2
_scan_len::
	.ds 2
_scan_ra::
	.ds 2
_scan_rb::
	.ds 2
_scan_fa::
	.ds 2
_scan_fb::
	.ds 2
_scan_sfa::
	.ds 1
_ps:
	.ds 22
_dec_info::
	.ds 20
_g_K:
	.ds 2
_g_tau:
	.ds 2
_c_lo:
	.ds 4
_c_hi:
	.ds 4
_c_n:
	.ds 2
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
	.ds 27
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
	.ds 19
_ss:
	.ds 20
_ch_rbase:
	.ds 1
_ch_n:
	.ds 1
_ch_isd:
	.ds 5
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
	cpw	y, #0x00b8
	jrc	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 132: uint16_t u = t - (NB - 32);
	subw	x, #0x00b8
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 174: void scan_init(void)
;	-----------------------------------------
;	 function scan_init
;	-----------------------------------------
_scan_init:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 176: ps.i = 0; ps.s = 0; ps.tbase = 0; ps.wsum = 0;
	ldw	x, #(_ps+0)
	clr	(0x1, x)
	clr	(x)
	mov	_ps+2, #0x00
	ldw	x, #(_ps+3)
	clr	(0x1, x)
	clr	(x)
	ldw	x, #(_ps+5)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 177: ps.t_prev = 0; ps.have_prev = 0;
	ldw	x, #(_ps+7)
	clr	(0x1, x)
	clr	(x)
	mov	_ps+9, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 178: ps.in_pulse = 0; ps.seen = 0; ps.done = 0; ps.low_run = 0;
	mov	_ps+10, #0x00
	mov	_ps+11, #0x00
	mov	_ps+12, #0x00
	ldw	x, #(_ps+13)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 179: ps.ra = ps.rb = ps.fa = 0; ps.sfa = 0;
	ldw	x, #(_ps+19)
	clr	(0x1, x)
	clr	(x)
	ldw	x, #(_ps+17)
	clr	(0x1, x)
	clr	(x)
	ldw	x, #(_ps+15)
	clr	(0x1, x)
	clr	(x)
	mov	_ps+21, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 180: }
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 183: uint8_t scan_next(void)
;	-----------------------------------------
;	 function scan_next
;	-----------------------------------------
_scan_next:
	sub	sp, #8
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
00133$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 185: while (!ps.done) {
	ld	a, _ps+12
	jreq	00320$
	jp	00135$
00320$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 186: uint8_t v, s = ps.s;
	ld	a, _ps+2
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 188: if (ps.i >= scan_len) break;
	ldw	x, #(_ps+0)
	ldw	(0x02, sp), x
	ldw	x, (x)
	ldw	(0x04, sp), x
	cpw	x, _scan_len+0
	jrc	00321$
	jp	00135$
00321$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
	ldw	x, (0x04, sp)
	incw	x
	ldw	y, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
	addw	x, _scan_cap+0
	ldw	(0x06, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 189: if (s == 6 && ps.i + 1 < scan_len) {
	cpw	y, _scan_len+0
	clr	a
	rlc	a
	ld	(0x08, sp), a
	ld	a, (0x01, sp)
	cp	a, #0x06
	jreq	00324$
	jp	00113$
00324$:
	tnz	(0x08, sp)
	jrne	00325$
	jp	00113$
00325$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 190: uint8_t bt = scan_cap[ps.i + 1];
	ldw	x, (0x06, sp)
	ld	a, (x)
	ld	xl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 191: if (bt == 0x00 && !ps.in_pulse) {
	tnz	a
	jrne	00107$
	ld	a, _ps+10
	jrne	00107$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 193: ps.t_prev = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum);
	ldw	x, _ps+3
	addw	x, #0x003d
	ldw	y, _ps+5
	ldw	(0x07, sp), y
	addw	x, (0x07, sp)
	ldw	_ps+7, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 194: ps.have_prev = 1;
	mov	_ps+9, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 195: ps.low_run = (uint16_t)(ps.low_run + 8);
	ldw	x, _ps+13
	addw	x, #0x0008
	ldw	_ps+13, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 196: ps.i++; ps.tbase += LOOP_CY;        /* s stays 6 */
	ldw	x, (0x02, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x02, sp)
	ldw	(y), x
	ldw	x, _ps+3
	addw	x, #0x0028
	ldw	_ps+3, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 197: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
	ld	a, _ps+11
	jrne	00328$
	jp	00133$
00328$:
	ldw	x, _ps+13
	cpw	x, #0x00c8
	jrnc	00329$
	jp	00133$
00329$:
	mov	_ps+12, #0x01
	jp	00135$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 198: continue;
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 200: if (bt == 0xFF && ps.in_pulse) {
	ld	a, xl
	inc	a
	jrne	00113$
	ld	a, _ps+10
	jreq	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 202: ps.fa = (uint16_t)(ps.tbase + LOOP_CY + 21 + ps.wsum + 2);
	ldw	y, _ps+3
	ldw	x, _ps+5
	addw	x, #0x003f
	ldw	(0x07, sp), y
	addw	x, (0x07, sp)
	ldw	_ps+19, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 203: ps.wsum += 2;               /* sum of W over the octet */
	ldw	x, _ps+5
	incw	x
	incw	x
	ldw	_ps+5, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 204: ps.sfa = 5;
	mov	_ps+21, #0x05
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 205: ps.low_run = 0;
	ldw	x, #(_ps+13)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 206: ps.seen = 1;
	mov	_ps+11, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 207: ps.t_prev = ps.fa;
	ldw	x, _ps+19
	ldw	_ps+7, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 208: ps.have_prev = 1;
	mov	_ps+9, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 209: ps.i++; ps.tbase += LOOP_CY;
	ldw	x, (0x02, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x02, sp)
	ldw	(y), x
	ldw	x, _ps+3
	addw	x, #0x0028
	ldw	_ps+3, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 210: continue;
	jp	00133$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 213: if (s < 6) {
	ld	a, (0x01, sp)
	cp	a, #0x06
	jrnc	00118$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 214: v = (uint8_t)((scan_cap[ps.i] >> (5 - s)) & 1);
	ldw	x, _scan_cap+0
	addw	x, (0x04, sp)
	ld	a, (x)
	ld	xl, a
	ld	a, #0x05
	sub	a, (0x01, sp)
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
	ld	(0x04, sp), a
	jra	00119$
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 216: if (ps.i + 1 >= scan_len) {     /* last loop: BS lost */
	ld	a, (0x08, sp)
	jrne	00116$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 217: ps.i++; ps.s = 0; ps.tbase += LOOP_CY;
	ldw	x, (0x04, sp)
	incw	x
	ldw	y, (0x02, sp)
	ldw	(y), x
	mov	_ps+2, #0x00
	ldw	x, _ps+3
	addw	x, #0x0028
	ldw	_ps+3, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 218: continue;
	jp	00133$
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 220: v = (uint8_t)((scan_cap[ps.i + 1] >> (7 - (s - 6))) & 1);
	ldw	x, (0x06, sp)
	ld	a, (x)
	ld	xl, a
	ld	a, (0x01, sp)
	sub	a, #0x06
	ld	(0x08, sp), a
	ld	a, #0x07
	sub	a, (0x08, sp)
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
	ld	(0x04, sp), a
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 222: t = (uint16_t)(ps.tbase + O_CY[s] + ps.wsum);
	ldw	y, _ps+3
	clrw	x
	ld	a, (0x01, sp)
	ld	xl, a
	ld	a, (_O_CY+0, x)
	ld	(0x08, sp), a
	clr	(0x07, sp)
	addw	y, (0x07, sp)
	ldw	x, _ps+5
	ldw	(0x05, sp), y
	addw	x, (0x05, sp)
	ldw	(0x07, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 223: if (s == 7) { ps.s = 0; ps.i++; ps.tbase += LOOP_CY; }
	ld	a, (0x01, sp)
	cp	a, #0x07
	jrne	00121$
	mov	_ps+2, #0x00
	ldw	x, (0x02, sp)
	ldw	x, (x)
	incw	x
	ldw	y, (0x02, sp)
	ldw	(y), x
	ldw	x, _ps+3
	addw	x, #0x0028
	ldw	_ps+3, x
	jra	00122$
00121$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 224: else        { ps.s = (uint8_t)(s + 1); }
	ld	a, (0x01, sp)
	inc	a
	ld	_ps+2, a
00122$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 225: if (v) {
	tnz	(0x04, sp)
	jreq	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 226: ps.wsum += W_CY[s];
	ldw	y, _ps+5
	clrw	x
	ld	a, (0x01, sp)
	ld	xl, a
	addw	x, #(_W_CY+0)
	ld	a, (x)
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	ldw	(0x05, sp), y
	addw	x, (0x05, sp)
	ldw	_ps+5, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 227: if (!ps.in_pulse) {
	ld	a, _ps+10
	jrne	00124$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 228: ps.in_pulse = 1;
	mov	_ps+10, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 229: ps.ra = ps.have_prev ? ps.t_prev
	ld	a, _ps+9
	jreq	00140$
	ldw	x, _ps+7
	jra	00141$
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 230: : (t >= FIRST_BR ? (uint16_t)(t - FIRST_BR) : 0);
	ldw	y, (0x07, sp)
	ldw	(0x03, sp), y
	ldw	x, y
	cpw	x, #0x0004
	jrc	00142$
	ldw	x, (0x03, sp)
	subw	x, #0x0004
	ldw	(0x05, sp), x
	.byte 0xbc
00142$:
	clrw	x
	ldw	(0x05, sp), x
00143$:
	ldw	x, (0x05, sp)
00141$:
	ldw	_ps+15, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 231: ps.rb = t;
	ldw	x, #(_ps+17)
	ldw	y, (0x07, sp)
	ldw	(x), y
00124$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 233: ps.fa = t;
	ldw	x, #(_ps+19)
	ldw	y, (0x07, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 234: ps.sfa = s;
	ldw	x, #(_ps+21)
	ld	a, (0x01, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 235: ps.low_run = 0;
	ldw	x, #(_ps+13)
	clr	(0x1, x)
	clr	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 236: ps.seen = 1;
	mov	_ps+11, #0x01
	jra	00132$
00131$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 238: if (ps.in_pulse) {
	ld	a, _ps+10
	jreq	00126$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 239: ps.in_pulse = 0;
	mov	_ps+10, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 240: scan_ra = ps.ra; scan_rb = ps.rb;
	ldw	x, _ps+15
	ldw	_scan_ra+0, x
	ldw	x, _ps+17
	ldw	_scan_rb+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 241: scan_fa = ps.fa; scan_fb = t; scan_sfa = ps.sfa;
	ldw	x, _ps+19
	ldw	_scan_fa+0, x
	ldw	x, (0x07, sp)
	ldw	_scan_fb+0, x
	mov	_scan_sfa+0, _ps+21
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 242: ps.t_prev = t; ps.have_prev = 1;
	ldw	x, #(_ps+7)
	ldw	y, (0x07, sp)
	ldw	(x), y
	mov	_ps+9, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 243: ps.low_run = 1;
	mov	_ps+14, #0x01
	mov	_ps+13, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 244: return 1;
	ld	a, #0x01
	jra	00138$
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 246: ps.low_run++;
	ldw	x, _ps+13
	incw	x
	ldw	_ps+13, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 247: if (ps.seen && ps.low_run >= LATCH_RUN) { ps.done = 1; break; }
	ld	a, _ps+11
	jreq	00132$
	ldw	x, _ps+13
	cpw	x, #0x00c8
	jrc	00132$
	mov	_ps+12, #0x01
	jra	00135$
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 249: ps.t_prev = t;
	ldw	x, #(_ps+7)
	ldw	y, (0x07, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 250: ps.have_prev = 1;
	mov	_ps+9, #0x01
	jp	00133$
00135$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 252: if (ps.in_pulse) {                      /* capture ended high */
	ld	a, _ps+10
	jreq	00137$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 253: ps.in_pulse = 0;
	mov	_ps+10, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 254: scan_ra = ps.ra; scan_rb = ps.rb;
	ldw	x, _ps+15
	ldw	_scan_ra+0, x
	ldw	x, _ps+17
	ldw	_scan_rb+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 255: scan_fa = ps.fa; scan_fb = (uint16_t)(ps.fa + FIRST_BR);
	ldw	x, _ps+19
	ldw	_scan_fa+0, x
	ldw	x, _ps+19
	addw	x, #0x0004
	ldw	_scan_fb+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 256: scan_sfa = ps.sfa;
	mov	_scan_sfa+0, _ps+21
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 257: return 1;
	ld	a, #0x01
	jra	00138$
00137$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 259: ps.done = 1;
	mov	_ps+12, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 260: return 0;
	clr	a
00138$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 261: }
	addw	sp, #8
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 313: scan_init();
	pushw	x
	call	_scan_init
	popw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 314: while (scan_next()) {
	clrw	y
00103$:
	pushw	x
	pushw	y
	call	_scan_next
	popw	y
	popw	x
	tnz	a
	jreq	00105$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 315: if (np == 0) r0m = (uint16_t)((scan_ra + scan_rb) >> 1);
	tnzw	y
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 317: np++;
	incw	y
	jra	00103$
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 319: if (np < 8 || flm <= r0m) return 0;
	cpw	y, #0x0008
	jrc	00106$
	cpw	x, (0x01, sp)
	jrugt	00107$
00106$:
	clr	a
	jra	00112$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 321: K = (Wu << KQ) / (uint32_t)(flm - r0m);          /* ** 32-bit ** */
	subw	x, (0x01, sp)
	clrw	y
	pushw	x
	pushw	y
	push	#0x00
	push	#0xa0
	push	#0x79
	push	#0x0d
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
	ld	a, #0x0b
00161$:
	srlw	y
	rrcw	x
	dec	a
	jrne	00161$
	ldw	(0x05, sp), x
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
	tnz	a
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
	ldw	x, #0xb2a4
	cpw	x, (0x11, sp)
	ld	a, #0x01
	sbc	a, (0x10, sp)
	clr	a
	sbc	a, (0x0f, sp)
	jrnc	00188$
	jp	00110$
00188$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 348: q = ((uint32_t)y + BIT_H) >> BIT_SH;
	ldw	x, (0x11, sp)
	addw	x, #0x0100
	ldw	y, (0x0f, sp)
	jrnc	00189$
	incw	y
00189$:
	srlw	y
	rrcw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 349: e = (int16_t)(y - (int32_t)(q << BIT_SH));
	clr	a
	ld	xl, a
	sllw	x
	ldw	y, (0x0d, sp)
	ldw	(0x13, sp), y
	negw	x
	addw	x, (0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 350: if ((uint32_t)y < mid_u) { n_lo++; se_lo += e; sy_lo += (uint32_t)y; }
	exgw	x, y
	ld	a, yh
	rlc	a
	clr	a
	sbc	a, #0x00
	push	a
	ld	(0x0c, sp), a
	pop	a
	ldw	x, (0x11, sp)
	cpw	x, #0xda00
	push	a
	ld	a, (0x11, sp)
	sbc	a, #0x00
	ld	a, (0x10, sp)
	sbc	a, #0x00
	pop	a
	jrnc	00106$
	ldw	x, (0x25, sp)
	incw	x
	ldw	(0x25, sp), x
	ldw	x, y
	addw	x, (0x17, sp)
	ldw	(0x17, sp), x
	adc	a, (0x16, sp)
	ld	(0x16, sp), a
	ld	a, (0x0b, sp)
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
	ldw	x, (0x27, sp)
	incw	x
	ldw	(0x27, sp), x
	ldw	x, y
	addw	x, (0x1b, sp)
	ldw	(0x1b, sp), x
	adc	a, (0x1a, sp)
	ld	(0x1a, sp), a
	ld	a, (0x0b, sp)
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
	jrnc	00193$
	jp	00119$
00193$:
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
	ldw	(0x0d, sp), y
	ldw	y, (0x0b, sp)
	subw	y, (0x07, sp)
	ldw	(0x03, sp), y
	ld	a, (0x0a, sp)
	sbc	a, (0x06, sp)
	ld	(0x02, sp), a
	ld	a, (0x09, sp)
	sbc	a, (0x05, sp)
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 359: dy = (int32_t)my_hi - (int32_t)my_lo;
	ld	a, (0x0e, sp)
	subw	x, (0x13, sp)
	ldw	(0x07, sp), x
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
	ldw	(0x21, sp), x
	ldw	x, _g_tau+0
	ldw	(0x27, sp), x
	ld	a, (0x27, sp)
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x26, sp), a
	ld	(0x25, sp), a
	subw	y, (0x27, sp)
	ld	a, (0x22, sp)
	sbc	a, (0x26, sp)
	ld	xl, a
	ld	a, (0x21, sp)
	sbc	a, (0x25, sp)
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
	ldw	y, #0xb2a4
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
	sub	sp, #28
	ldw	(0x1b, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 404: while (!ss.src_done) {
00121$:
	ld	a, _ss+19
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
	ldw	y, (0x1b, sp)
	ldw	(0x01, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
	ldw	x, (0x1b, sp)
	incw	x
	incw	x
	ldw	(0x03, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, (0x1b, sp)
	addw	x, #0x0004
	ldw	(0x05, sp), x
	ldw	x, (0x1b, sp)
	addw	x, #0x0006
	ldw	(0x07, sp), x
	ldw	x, (0x1b, sp)
	addw	x, #0x0008
	ldw	(0x09, sp), x
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
	ldw	(0x0d, sp), x
	ldw	(0x0b, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 411: if (y < 0) y = 0;
	tnz	(0x0b, sp)
	jrpl	00104$
	clrw	x
	ldw	(0x0d, sp), x
	ldw	(0x0b, sp), x
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 412: if ((uint32_t)y > ss.y_end) { ss.src_done = 1; break; }
	ldw	y, (0x0d, sp)
	ldw	(0x11, sp), y
	ldw	y, (0x0b, sp)
	ldw	(0x0f, sp), y
	ldw	x, #(_ss+0)
	ldw	y, x
	ldw	y, (0x2, y)
	ldw	x, (x)
	ld	a, yl
	cp	a, (0x12, sp)
	ld	a, yh
	sbc	a, (0x11, sp)
	ld	a, xl
	sbc	a, (0x10, sp)
	ld	a, xh
	sbc	a, (0x0f, sp)
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
	ldw	(0x15, sp), y
	ldw	(0x13, sp), x
	ldw	y, (0x0d, sp)
	subw	y, (0x15, sp)
	ld	a, (0x0c, sp)
	sbc	a, (0x14, sp)
	ld	(0x18, sp), a
	ld	a, (0x0b, sp)
	sbc	a, (0x13, sp)
	ld	(0x17, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 416: dn = (int16_t)((d + BIT_H) >> BIT_SH);
	addw	y, #0x0100
	ldw	x, (0x17, sp)
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
	ldw	(0x19, sp), y
	addw	x, (0x19, sp)
	ldw	_ss+9, x
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 419: ss.y_prev = (uint32_t)y;
	ldw	x, #(_ss+4)
	ldw	y, (0x11, sp)
	ldw	(0x2, x), y
	ldw	y, (0x0f, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 420: yfa = map_raw(scan_fa);
	ldw	x, _scan_fa+0
	call	_map_raw
	ldw	(0x19, sp), x
	ldw	(0x17, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 421: yfb = map_raw(scan_fb);
	ldw	x, _scan_fb+0
	call	_map_raw
	ldw	(0x11, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
	ld	a, _ss+11
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	y, (0x19, sp)
	ldw	(0x15, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	(0x17, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 422: if (ss.pend && ss.n == ss.p_k0) {            /* spurious split */
	tnz	a
	jreq	00113$
	ldw	x, _ss+9
	ldw	(0x19, sp), x
	ldw	x, _ss+12
	cpw	x, (0x19, sp)
	jrne	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 423: base = (uint32_t)BIAS_U + (uint32_t)ss.p_k0 * BIT_U;
	rlwa	y
	ld	a, xl
	rrwa	y
	ld	a, xh
	clrw	x
	exg	a, yl
	clr	a
	exg	a, yl
	sllw	y
	rlc	a
	rlcw	x
	addw	y, #0x0200
	adc	a, #0x00
	rrwa	x
	adc	a, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 424: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	(0x19, sp), y
	ldw	x, (0x15, sp)
	subw	x, (0x19, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 425: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x17, sp)
	subw	x, (0x19, sp)
	ldw	_ss+16, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 426: ss.p_fam = scan_sfa;
	mov	_ss+18, _scan_sfa+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 427: continue;
	jp	00121$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 429: if (ss.pend) {
	tnz	a
	jrne	00254$
	jp	00118$
00254$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 430: out->k0 = ss.p_k0;
	ldw	x, _ss+12
	ldw	y, (0x01, sp)
	ldw	(y), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 431: out->k1 = (ss.n < NB) ? ss.n : NB;
	ldw	x, _ss+9
	cpw	x, #0x00d8
	jrnc	00128$
	ldw	(0x19, sp), x
	jra	00129$
00128$:
	ldw	x, #0x00d8
	ldw	(0x19, sp), x
00129$:
	ldw	x, (0x03, sp)
	ldw	y, (0x19, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 432: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, _ss+14
	ldw	y, (0x05, sp)
	ldw	(y), x
	ldw	x, _ss+16
	ldw	y, (0x07, sp)
	ldw	(y), x
	ld	a, _ss+18
	ldw	x, (0x09, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 433: if (ss.n >= NB) { ss.pend = 0; ss.src_done = 1; return 1; }
	ldw	x, _ss+9
	ldw	(0x19, sp), x
	cpw	x, #0x00d8
	jrc	00116$
	mov	_ss+11, #0x00
	mov	_ss+19, #0x01
	ld	a, #0x01
	jp	00126$
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 434: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
	ldw	y, (0x19, sp)
	clrw	x
	clr	a
	sll	a
	rlcw	y
	rlcw	x
	ld	(0x14, sp), a
	addw	y, #0x0002
	ldw	(0x12, sp), y
	clr	a
	adc	a, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 435: ss.p_k0 = ss.n;
	ldw	x, #(_ss+12)
	ldw	y, (0x19, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 436: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	y, (0x13, sp)
	ldw	(0x19, sp), y
	ldw	x, (0x15, sp)
	subw	x, (0x19, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 437: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x17, sp)
	subw	x, (0x19, sp)
	ldw	_ss+16, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 438: ss.p_fam = scan_sfa;
	mov	_ss+18, _scan_sfa+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 439: return 1;
	ld	a, #0x01
	jra	00126$
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 441: if (ss.n >= NB) { ss.src_done = 1; break; }
	ldw	x, _ss+9
	cpw	x, #0x00d8
	jrc	00120$
	mov	_ss+19, #0x01
	jra	00123$
00120$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 442: base = (uint32_t)BIAS_U + (uint32_t)ss.n * BIT_U;
	clrw	y
	clr	a
	sll	a
	rlcw	x
	exg	a, yl
	rlc	a
	exg	a, yl
	ld	(0x14, sp), a
	addw	x, #0x0002
	ldw	(0x12, sp), x
	clr	a
	adc	a, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 443: ss.pend = 1;
	mov	_ss+11, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 444: ss.p_k0 = ss.n;
	ldw	x, _ss+9
	ldw	_ss+12, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 445: ss.p_u = (int16_t)(yfa - (int32_t)base);
	ldw	y, (0x13, sp)
	ldw	(0x19, sp), y
	ldw	x, (0x15, sp)
	subw	x, (0x19, sp)
	ldw	_ss+14, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 446: ss.p_v = (int16_t)(yfb - (int32_t)base);
	ldw	x, (0x17, sp)
	subw	x, (0x19, sp)
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
	ldw	y, (0x01, sp)
	ldw	(y), x
	ldw	x, (0x03, sp)
	ldw	y, #0x00d8
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 452: out->u = ss.p_u; out->v = ss.p_v; out->fam = ss.p_fam;
	ldw	x, _ss+14
	ldw	y, (0x05, sp)
	ldw	(y), x
	ldw	x, _ss+16
	ldw	y, (0x07, sp)
	ldw	(y), x
	ld	a, _ss+18
	ldw	x, (0x09, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 453: return 1;
	ld	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 455: return 0;
	.byte 0x21
00125$:
	clr	a
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 456: }
	addw	sp, #28
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
	cpw	x, #0x00d8
	jrc	00117$
	ldw	x, #0x00d8
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
	ldw	x, (0x0b, sp)
	subw	x, (0x09, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 467: if (kb == 1) {
	cp	a, #0x01
	jrne	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 468: int16_t m = (int16_t)(t - k0 + 1);
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
	ldw	y, (0x05, sp)
	ldw	y, (y)
	ldw	(0x07, sp), y
	cpw	x, (0x07, sp)
	jrsge	00113$
	ldw	y, (0x05, sp)
	ldw	(y), x
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
	sub	sp, #8
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 482: int16_t L = (int16_t)(k1 - k0);
	negw	x
	addw	x, (0x0b, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 485: if (a == 0) { off = 0; cls = 0; }
	ldw	y, (0x11, sp)
	jrne	00114$
	clrw	x
	ldw	(0x07, sp), x
	clr	(0x06, sp)
	jp	00115$
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 486: else if (a == L) { off = (int16_t)((L - 1) * BIT_U); cls = 1; }
	cpw	x, (0x11, sp)
	jrne	00111$
	decw	x
	clr	a
	rlwa	x
	sllw	x
	ldw	(0x07, sp), x
	ld	a, #0x01
	ld	(0x06, sp), a
	jra	00115$
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 488: mid = (int16_t)((u + v) >> 1);
	ldw	y, (0x0d, sp)
	addw	y, (0x0f, sp)
	sraw	y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 489: d1 = (int16_t)(mid - ((a - 1) * BIT_U + H1P));
	ldw	x, (0x11, sp)
	ldw	(0x07, sp), x
	decw	x
	exg	a, xl
	ld	(0x01, sp), a
	exg	a, xl
	clr	(0x02, sp)
	sll	(0x02, sp)
	rlc	(0x01, sp)
	ldw	x, (0x01, sp)
	addw	x, #0x0134
	ldw	(0x05, sp), x
	ldw	x, y
	subw	x, (0x05, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 490: if (d1 < 0) d1 = (int16_t)-d1;
	ldw	(0x05, sp), x
	tnzw	x
	jrpl	00102$
	neg	(0x06, sp)
	clr	a
	sbc	a, (0x05, sp)
	ld	(0x05, sp), a
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 491: d0 = (int16_t)(mid - (a * BIT_U + H0P));
	ld	a, (0x08, sp)
	ld	(0x03, sp), a
	clr	(0x04, sp)
	sll	(0x04, sp)
	rlc	(0x03, sp)
	ldw	x, (0x03, sp)
	addw	x, #0x009a
	ldw	(0x07, sp), x
	subw	y, (0x07, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 492: if (d0 < 0) d0 = (int16_t)-d0;
	ldw	(0x07, sp), y
	ldw	x, y
	tnzw	x
	jrpl	00104$
	neg	(0x08, sp)
	clr	a
	sbc	a, (0x07, sp)
	ld	(0x07, sp), a
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 493: if ((d0 < d1 ? d0 : d1) > LAB_OUT) return -1;
	ldw	x, (0x07, sp)
	cpw	x, (0x05, sp)
	jrsge	00118$
	ldw	x, (0x07, sp)
	.byte 0xc5
00118$:
	ldw	x, (0x05, sp)
00119$:
	cpw	x, #0x00f6
	jrsle	00106$
	ld	a, #0xff
	jra	00116$
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 494: if (d1 <= d0) { off = (int16_t)((a - 1) * BIT_U); cls = 1; }
	ldw	x, (0x05, sp)
	cpw	x, (0x07, sp)
	jrsgt	00108$
	ldw	y, (0x01, sp)
	ldw	(0x07, sp), y
	ld	a, #0x01
	ld	(0x06, sp), a
	jra	00115$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 495: else          { off = (int16_t)(a * BIT_U);       cls = 0; }
	ldw	y, (0x03, sp)
	ldw	(0x07, sp), y
	clr	(0x06, sp)
00115$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 497: *lo = (int16_t)(u - off); *hi = (int16_t)(v - off);
	ldw	x, (0x13, sp)
	ldw	y, (0x0d, sp)
	subw	y, (0x07, sp)
	ldw	(x), y
	ldw	x, (0x15, sp)
	ldw	y, (0x0f, sp)
	subw	y, (0x07, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 498: return cls;
	ld	a, (0x06, sp)
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 499: }
	ldw	x, (9, sp)
	addw	sp, #22
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 501: static void cal_cloud(int16_t u, uint8_t fam)
;	-----------------------------------------
;	 function cal_cloud
;	-----------------------------------------
_cal_cloud:
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 505: if (fam != 5 && fam != 6) return;
	cp	a, #0x05
	jreq	00102$
	cp	a, #0x06
	jrne	00111$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 506: if (u < 0) return;
	tnzw	x
	jrmi	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 507: f = (uint8_t)(fam - 5);
	sub	a, #0x05
	ld	yl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 508: x = (int16_t)(u & (BIT_U - 1));
	ld	a, xh
	and	a, #0x01
	ld	xh, a
	ldw	(0x01, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 509: d = (int16_t)(x - c_c0[f]);
	ldw	x, y
	clr	a
	ld	xh, a
	sllw	x
	ldw	x, (_c_c0+0, x)
	negw	x
	addw	x, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 510: if (d >= -EPS_HIST && d < EPS_HIST) {
	cpw	x, #0xffc0
	jrslt	00111$
	cpw	x, #0x0040
	jrsge	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 511: uint8_t b = (uint8_t)((d + EPS_HIST) >> 1);
	addw	x, #0x0040
	sraw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 512: if (c_hist[f][b] < 255) c_hist[f][b]++;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 514: }
	popw	x
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 516: static void cal_add(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function cal_add
;	-----------------------------------------
_cal_add:
	sub	sp, #10
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 520: int8_t cls = label_interval(k0, k1, u, v, a, &lo, &hi);
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, sp
	addw	x, #3
	pushw	x
	ldw	x, (0x18, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	ldw	x, (0x17, sp)
	pushw	x
	ldw	x, y
	call	_label_interval
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 521: if (cls < 0) return;
	ld	(0x08, sp), a
	jrpl	00102$
	jp	00129$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 523: uint8_t ci = (uint8_t)cls;
	ld	a, (0x08, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 524: if (lo > c_lo[ci]) c_lo[ci] = lo;
	clrw	x
	ld	xl, a
	sllw	x
	ldw	(0x09, sp), x
	ldw	y, x
	addw	y, #(_c_lo+0)
	ldw	x, y
	ldw	x, (x)
	cpw	x, (0x01, sp)
	jrsge	00104$
	ldw	x, y
	ldw	y, (0x01, sp)
	ldw	(x), y
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 525: if (hi < c_hi[ci]) c_hi[ci] = hi;
	ldw	y, (0x09, sp)
	addw	y, #(_c_hi+0)
	ldw	x, y
	ldw	x, (x)
	ldw	(0x09, sp), x
	ldw	x, (0x03, sp)
	cpw	x, (0x09, sp)
	jrsge	00106$
	ldw	x, y
	ldw	y, (0x03, sp)
	ldw	(x), y
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 526: if (c_n[ci] < 255) c_n[ci]++;
	clrw	x
	ld	xl, a
	addw	x, #(_c_n+0)
	ld	a, (x)
	cp	a, #0xff
	jrnc	00108$
	inc	a
	ld	(x), a
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 528: if ((fam == 5 || fam == 6) && lo >= 0) {
	ld	a, (0x13, sp)
	cp	a, #0x05
	jreq	00128$
	ld	a, (0x13, sp)
	cp	a, #0x06
	jreq	00244$
	jp	00129$
00244$:
00128$:
	ldw	x, (0x01, sp)
	jrpl	00245$
	jp	00129$
00245$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 529: uint8_t f = (uint8_t)(fam - 5);
	ld	a, (0x13, sp)
	sub	a, #0x05
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 530: int16_t d = (int16_t)((lo & (BIT_U - 1)) - c_c0[f]);
	push	a
	exg	a, xl
	ld	(0x08, sp), a
	exg	a, xl
	ld	a, xh
	and	a, #0x01
	ld	(0x07, sp), a
	pop	a
	clrw	x
	ld	xl, a
	sllw	x
	ldw	y, x
	ldw	x, (_c_c0+0, x)
	ldw	(0x09, sp), x
	ldw	x, (0x06, sp)
	subw	x, (0x09, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 531: if (d >= -EPS_HIST && d < EPS_HIST) {
	ldw	(0x05, sp), x
	cpw	x, #0xffc0
	jrslt	00129$
	ldw	x, (0x05, sp)
	cpw	x, #0x0040
	jrsge	00129$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 532: if (cls == 0) {
	tnz	(0x08, sp)
	jrne	00120$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 533: if (d > c_labx0[f]) { c_labx0b[f] = c_labx0[f]; c_labx0[f] = d; }
	ldw	x, y
	addw	x, #(_c_labx0+0)
	ldw	(0x09, sp), x
	ldw	x, (x)
	cpw	x, (0x05, sp)
	jrsge	00112$
	ldw	((_c_labx0b+0), y), x
	ldw	x, (0x09, sp)
	ldw	y, (0x05, sp)
	ldw	(x), y
	jra	00129$
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 534: else if (d > c_labx0b[f]) c_labx0b[f] = d;
	addw	y, #(_c_labx0b+0)
	ldw	x, y
	ldw	x, (x)
	cpw	x, (0x05, sp)
	jrsge	00129$
	ldw	x, y
	ldw	y, (0x05, sp)
	ldw	(x), y
	jra	00129$
00120$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 536: if (d < c_labx1[f]) { c_labx1b[f] = c_labx1[f]; c_labx1[f] = d; }
	ldw	x, y
	addw	x, #(_c_labx1+0)
	ldw	(0x07, sp), x
	ldw	x, (x)
	ldw	(0x09, sp), x
	ldw	x, (0x05, sp)
	cpw	x, (0x09, sp)
	jrsge	00117$
	ldw	x, y
	ldw	y, (0x09, sp)
	ldw	((_c_labx1b+0), x), y
	ldw	x, (0x07, sp)
	ldw	y, (0x05, sp)
	ldw	(x), y
	jra	00129$
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 537: else if (d < c_labx1b[f]) c_labx1b[f] = d;
	addw	y, #(_c_labx1b+0)
	ldw	x, y
	ldw	x, (x)
	ldw	(0x09, sp), x
	ldw	x, (0x05, sp)
	cpw	x, (0x09, sp)
	jrsge	00129$
	ldw	x, y
	ldw	y, (0x05, sp)
	ldw	(x), y
00129$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 541: }
	ldw	x, (11, sp)
	addw	sp, #21
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 544: static uint8_t theta56(uint8_t f, int16_t *theta_out)
;	-----------------------------------------
;	 function theta56
;	-----------------------------------------
_theta56:
	sub	sp, #40
	ldw	(0x25, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 546: int16_t x0 = c_labx0[f], x1 = c_labx1[f];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	(0x05, sp), x
	ldw	x, (_c_labx0+0, x)
	ldw	y, (0x05, sp)
	ldw	y, (_c_labx1+0, y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 547: uint8_t has0 = (x0 > -0x4000), has1 = (x1 < 0x3FFF);
	ldw	(0x07, sp), x
	cpw	x, #0xc000
	jrsgt	00483$
	clr	(0x09, sp)
	jra	00484$
00483$:
	push	a
	ld	a, #0x01
	ld	(0x0a, sp), a
	pop	a
00484$:
	ldw	(0x0a, sp), y
	ldw	x, y
	cpw	x, #0x3fff
	jrslt	00485$
	clr	(0x0c, sp)
	jra	00486$
00485$:
	push	a
	ld	a, #0x01
	ld	(0x0d, sp), a
	pop	a
00486$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 548: int16_t zlo = (int16_t)(x0 + 1);
	ldw	x, (0x07, sp)
	incw	x
	ldw	(0x0d, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 549: int16_t zhi = x1;
	ldw	(0x0f, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 550: int16_t theta = 0;
	clrw	x
	ldw	(0x11, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 551: uint8_t have_theta = 0;
	clr	(0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 552: int16_t top = 0;
	clrw	x
	ldw	(0x14, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 553: uint8_t have_top = 0, clear1 = 0;
	clr	(0x16, sp)
	clr	(0x17, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 555: if (zlo < -EPS_ZONE) zlo = -EPS_ZONE;
	ldw	x, #0xffe0
	cpw	x, (0x0d, sp)
	jrslt	00102$
	ldw	(0x0d, sp), x
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 556: if (zhi > EPS_ZONE) zhi = EPS_ZONE;
	ldw	x, (0x0f, sp)
	cpw	x, #0x0020
	jrsle	00104$
	ldw	x, #0x0020
	ldw	(0x0f, sp), x
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
	exg	a, xl
	ld	a, #0x40
	exg	a, xl
	mul	x, a
	ldw	(0x18, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 557: if (zlo < zhi) {
	ldw	x, (0x0d, sp)
	cpw	x, (0x0f, sp)
	jrslt	00489$
	jp	00126$
00489$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 558: uint8_t blo = (uint8_t)((zlo + EPS_HIST) >> 1);
	ldw	x, (0x0d, sp)
	addw	x, #0x0040
	sraw	x
	exg	a, xl
	ld	(0x27, sp), a
	exg	a, xl
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 559: uint8_t bhi = (uint8_t)((zhi - 1 + EPS_HIST) >> 1);
	ldw	x, (0x0f, sp)
	addw	x, #0x003f
	sraw	x
	exg	a, xl
	ld	(0x1a, sp), a
	exg	a, xl
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 560: int16_t prev = zlo, best_lo = 0, best_hi = 0, bg = -1;
	ldw	y, (0x0d, sp)
	ldw	(0x1b, sp), y
	clrw	x
	ldw	(0x1d, sp), x
	clrw	x
	ldw	(0x1f, sp), x
	clrw	x
	decw	x
	ldw	(0x21, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
	ldw	x, (0x18, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x23, sp), x
	clr	(0x28, sp)
00170$:
	ld	a, (0x27, sp)
	cp	a, (0x1a, sp)
	jrugt	00253$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 563: if (c_hist[f][b]) {
	clrw	x
	ld	a, (0x27, sp)
	ld	xl, a
	addw	x, (0x23, sp)
	ld	a, (x)
	jreq	00171$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 564: int16_t x = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
	ld	a, (0x27, sp)
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #0xffc1
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 565: int16_t gp = (int16_t)(x - prev);
	ldw	y, x
	subw	x, (0x1b, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 566: if (gp > bg) { bg = gp; best_lo = prev; best_hi = x; }
	cpw	x, (0x21, sp)
	jrsle	00106$
	ldw	(0x21, sp), x
	ldw	x, (0x1b, sp)
	ldw	(0x1d, sp), x
	ldw	(0x1f, sp), y
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 567: prev = x;
	ldw	(0x1b, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 568: nocc++;
	inc	(0x28, sp)
00171$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 562: for (b = blo; b <= bhi; b++) {
	inc	(0x27, sp)
	jra	00170$
00253$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 572: int16_t gp = (int16_t)(zhi - prev);
	ldw	x, (0x0f, sp)
	subw	x, (0x1b, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 573: if (gp > bg) { bg = gp; best_lo = prev; best_hi = zhi; }
	cpw	x, (0x21, sp)
	jrsle	00111$
	ldw	(0x21, sp), x
	ldw	y, (0x1b, sp)
	ldw	(0x1d, sp), y
	ldw	y, (0x0f, sp)
	ldw	(0x1f, sp), y
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 575: if (nocc == 0) {
	tnz	(0x28, sp)
	jrne	00123$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 576: if (has0 && has1) { theta = (int16_t)((zlo + zhi) >> 1); have_theta = 1; }
	tnz	(0x09, sp)
	jrne	00495$
	jp	00126$
00495$:
	tnz	(0x0c, sp)
	jrne	00496$
	jp	00126$
00496$:
	ldw	x, (0x0d, sp)
	addw	x, (0x0f, sp)
	sraw	x
	ldw	(0x11, sp), x
	ld	a, #0x01
	ld	(0x13, sp), a
	jra	00126$
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 578: uint8_t ok = (bg >= EPS_GAP_MIN);
	ldw	x, (0x21, sp)
	cpw	x, #0x0005
	jrslt	00497$
	clr	a
	.byte 0xc5
00497$:
	ld	a, #0x01
00498$:
	xor	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 579: if (ok && (uint8_t)(nocc + 1) >= 4) {
	ld	(0x27, sp), a
	jreq	00118$
	ld	a, (0x28, sp)
	inc	a
	cp	a, #0x04
	jrc	00118$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 580: if ((int32_t)2 * bg * (nocc + 1) < (int32_t)5 * (zhi - zlo))
	ldw	y, (0x21, sp)
	clrw	x
	tnzw	y
	jrpl	00501$
	decw	x
00501$:
	sllw	y
	rlcw	x
	ldw	(0x21, sp), x
	ld	a, (0x28, sp)
	clrw	x
	ld	xl, a
	incw	x
	ld	a, xh
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	(0x02, sp), a
	ld	(0x01, sp), a
	pushw	x
	ldw	x, (0x03, sp)
	pushw	x
	pushw	y
	ldw	x, (0x27, sp)
	pushw	x
	call	__mullong
	addw	sp, #8
	ldw	(0x21, sp), y
	ldw	y, (0x0f, sp)
	subw	y, (0x0d, sp)
	pushw	x
	pushw	y
	ldw	x, #0x0005
	call	___mulsint2slong
	addw	sp, #2
	ldw	(0x11, sp), x
	ldw	(0x0f, sp), y
	popw	x
	cpw	x, (0x0f, sp)
	ld	a, (0x22, sp)
	sbc	a, (0x0e, sp)
	ld	a, (0x21, sp)
	sbc	a, (0x0d, sp)
	jrsge	00118$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 581: ok = 0;
	clr	(0x27, sp)
00118$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 583: if (ok) { theta = (int16_t)((best_lo + best_hi) >> 1); have_theta = 1; }
	tnz	(0x27, sp)
	jreq	00126$
	ldw	x, (0x1d, sp)
	addw	x, (0x1f, sp)
	sraw	x
	ldw	(0x11, sp), x
	ld	a, #0x01
	ld	(0x13, sp), a
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 586: if (has0 || has1) {
	tnz	(0x09, sp)
	jrne	00144$
	tnz	(0x0c, sp)
	jreq	00245$
00144$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 587: int16_t wlo = -EPS_ZONE, whi = EPS_ZONE;
	ldw	x, #0xffe0
	ldw	(0x23, sp), x
	ldw	x, #0x0020
	ldw	(0x27, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 588: if (has0) {
	tnz	(0x09, sp)
	jreq	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 589: wlo = (int16_t)(x0 - EPS_SLACK1);
	ldw	x, (0x07, sp)
	subw	x, #0x0008
	ldw	(0x23, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 590: if (c_labx0b[f] > -0x4000 &&
	ldw	x, (0x05, sp)
	ldw	x, (_c_labx0b+0, x)
	cpw	x, #0xc000
	jrsle	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 591: (int16_t)(c_labx0b[f] - EPS_SLACK) > wlo)
	decw	x
	decw	x
	cpw	x, (0x23, sp)
	jrsle	00131$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 592: wlo = (int16_t)(c_labx0b[f] - EPS_SLACK);
	ldw	(0x23, sp), x
00131$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 594: if (has1) {
	tnz	(0x0c, sp)
	jreq	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 595: whi = (int16_t)(x1 + EPS_SLACK1);
	ldw	x, (0x0a, sp)
	addw	x, #0x0008
	ldw	(0x27, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 596: if (c_labx1b[f] < 0x3FFF &&
	ldw	x, (0x05, sp)
	ldw	x, (_c_labx1b+0, x)
	cpw	x, #0x3fff
	jrsge	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 597: (int16_t)(c_labx1b[f] + EPS_SLACK) < whi)
	incw	x
	incw	x
	cpw	x, (0x27, sp)
	jrsge	00136$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 598: whi = (int16_t)(c_labx1b[f] + EPS_SLACK);
	ldw	(0x27, sp), x
00136$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 600: if (wlo > whi) {
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 601: theta = (int16_t)((wlo + whi) >> 1);
	ldw	x, (0x23, sp)
	cpw	x, (0x27, sp)
	jrsle	00142$
	addw	x, (0x27, sp)
	sraw	x
	ldw	(0x11, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 602: have_theta = 1;
	ld	a, #0x01
	ld	(0x13, sp), a
	jra	00245$
00142$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 604: int16_t th = have_theta ? theta : 0;
	tnz	(0x13, sp)
	jreq	00175$
	ld	a, (0x12, sp)
	rlwa	x
	ld	a, (0x11, sp)
	rrwa	x
	jra	00176$
00175$:
	clr	a
	clrw	x
00176$:
	ld	xl, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 605: if (th < wlo) th = wlo;
	cpw	x, (0x23, sp)
	jrsge	00138$
	ldw	x, (0x23, sp)
00138$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 606: if (th > whi) th = whi;
	cpw	x, (0x27, sp)
	jrsle	00140$
	ldw	x, (0x27, sp)
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 607: theta = th;
	ldw	(0x11, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 608: have_theta = 1;
	ld	a, #0x01
	ld	(0x13, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
00245$:
	ldw	x, (0x18, sp)
	addw	x, #(_c_hist+0)
	ldw	(0x23, sp), x
	clr	(0x28, sp)
00172$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 613: if (!c_hist[f][b]) continue;
	clrw	x
	ld	a, (0x28, sp)
	ld	xl, a
	addw	x, (0x23, sp)
	ld	a, (x)
	jreq	00157$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 614: d = (int16_t)(((int16_t)b << 1) - EPS_HIST + 1);
	clrw	x
	ld	a, (0x28, sp)
	ld	xl, a
	sllw	x
	addw	x, #193
	ld	a, xl
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 615: if (d > EPS_CLEAR1) clear1 = 1;
	ld	a, xl
	cp	a, #0x12
	jrsle	00155$
	ld	a, #0x01
	ld	(0x17, sp), a
	jra	00157$
00155$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 616: else if (d > -EPS_CLAMP56) {
	cpw	x, #0xffe8
	jrsle	00157$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 617: if (!have_top || d > top) top = d;
	tnz	(0x16, sp)
	jreq	00149$
	cpw	x, (0x14, sp)
	jrsle	00150$
00149$:
	ldw	(0x14, sp), x
00150$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 618: have_top = 1;
	ld	a, #0x01
	ld	(0x16, sp), a
00157$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 611: for (b = 0; b < 64; b++) {
	inc	(0x28, sp)
	ld	a, (0x28, sp)
	cp	a, #0x40
	jrc	00172$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 621: if (!clear1 && have_top) {
	tnz	(0x17, sp)
	jrne	00167$
	tnz	(0x16, sp)
	jreq	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 622: int16_t floor_ = (int16_t)(top + EPS_TOPM);
	ld	a, (0x15, sp)
	add	a, #0x03
	ld	xl, a
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 623: if (!have_theta || floor_ > theta) theta = floor_;
	tnz	(0x13, sp)
	jreq	00159$
	cpw	x, (0x11, sp)
	jrsle	00160$
00159$:
	ldw	(0x11, sp), x
00160$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 624: have_theta = 1;
	ld	a, #0x01
	ld	(0x13, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 625: if (has1 && (int16_t)(x1 + EPS_SLACK) > floor_ &&
	tnz	(0x0c, sp)
	jreq	00167$
	ldw	y, (0x0a, sp)
	addw	y, #0x0002
	ldw	(0x27, sp), y
	cpw	x, (0x27, sp)
	jrsge	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 626: theta > (int16_t)(x1 + EPS_SLACK))
	ldw	x, (0x11, sp)
	cpw	x, (0x27, sp)
	jrsle	00167$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 627: theta = (int16_t)(x1 + EPS_SLACK);
	ldw	y, (0x27, sp)
	ldw	(0x11, sp), y
00167$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 629: *theta_out = theta;
	ldw	x, (0x25, sp)
	ldw	y, (0x11, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 630: return have_theta;
	ld	a, (0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 631: }
	addw	sp, #40
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 634: static int16_t width_fit(uint8_t ci, int16_t prior, int16_t blo, int16_t bhi)
;	-----------------------------------------
;	 function width_fit
;	-----------------------------------------
_width_fit:
	sub	sp, #4
	ldw	(0x03, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 636: int16_t lo = c_lo[ci], hi = c_hi[ci], h;
	clrw	x
	ld	xl, a
	sllw	x
	ldw	y, x
	ldw	x, (_c_lo+0, x)
	ldw	(0x01, sp), x
	ldw	y, (_c_hi+0, y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 637: if (c_n[ci] < LAB_MIN) return prior;
	clrw	x
	ld	xl, a
	addw	x, #(_c_n+0)
	ld	a, (x)
	cp	a, #0x03
	jrnc	00102$
	ldw	x, (0x03, sp)
	jra	00103$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 638: h = (lo > hi) ? (int16_t)((lo + hi) >> 1)
	exgw	x, y
	cpw	x, (0x01, sp)
	exgw	x, y
	jrsge	00105$
	ldw	x, y
	addw	x, (0x01, sp)
	sraw	x
	jra	00106$
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 639: : (prior < lo ? lo : (prior > hi ? hi : prior));
	ldw	x, (0x03, sp)
	cpw	x, (0x01, sp)
	jrsge	00107$
	ldw	x, (0x01, sp)
	jra	00108$
00107$:
	exgw	x, y
	cpw	x, (0x03, sp)
	exgw	x, y
	jrsge	00109$
	ldw	(0x01, sp), y
	jra	00110$
00109$:
	ldw	y, (0x03, sp)
	ldw	(0x01, sp), y
00110$:
	ldw	x, (0x01, sp)
00108$:
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 640: return (h >= blo && h <= bhi) ? h : prior;
	cpw	x, (0x07, sp)
	jrslt	00111$
	cpw	x, (0x09, sp)
	jrsle	00112$
00111$:
	ldw	x, (0x03, sp)
00112$:
00103$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 641: }
	ldw	y, (5, sp)
	addw	sp, #10
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 643: static void calibrate(void)
;	-----------------------------------------
;	 function calibrate
;	-----------------------------------------
_calibrate:
	sub	sp, #21
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 647: c_lo[0] = c_lo[1] = -0x4000;
	mov	_c_lo+3, #0x00
	mov	_c_lo+2, #0xc0
	mov	_c_lo+1, #0x00
	mov	_c_lo+0, #0xc0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 648: c_hi[0] = c_hi[1] = 0x3FFF;
	mov	_c_hi+3, #0xff
	mov	_c_hi+2, #0x3f
	mov	_c_hi+1, #0xff
	mov	_c_hi+0, #0x3f
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 649: c_n[0] = c_n[1] = 0;
	mov	_c_n+1, #0x00
	mov	_c_n+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 650: c_h0c = H0P; c_h1c = H1P;
	ldw	x, #0x009a
	ldw	_c_h0c+0, x
	ldw	x, #0x0134
	ldw	_c_h1c+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 651: c_d56[0] = c_d56[1] = 0;
	mov	_c_d56+1, #0x00
	mov	_c_d56+0, #0x00
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 652: c_gap56[0] = (int16_t)((uint32_t)6 * g_K >> KQ);
	ldw	x, _g_K+0
	pushw	x
	ldw	x, #0x0006
	call	___muluint2ulong
	addw	sp, #2
	ld	a, #0x0b
00285$:
	srlw	y
	rrcw	x
	dec	a
	jrne	00285$
	ldw	_c_gap56+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 653: c_gap56[1] = (int16_t)((uint32_t)5 * g_K >> KQ);
	ldw	x, _g_K+0
	pushw	x
	ldw	x, #0x0005
	call	___muluint2ulong
	addw	sp, #2
	ld	a, #0x0b
00287$:
	srlw	y
	rrcw	x
	dec	a
	jrne	00287$
	ldw	_c_gap56+2, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
	clr	(0x15, sp)
00128$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 656: c_c0[f] = (int16_t)((H0P + H1P - c_gap56[f]) >> 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 657: for (b = 0; b < 64; b++) c_hist[f][b] = 0;
	ld	a, (0x15, sp)
	ld	xl, a
	ld	a, #0x40
	mul	x, a
	addw	x, #(_c_hist+0)
	ldw	(0x13, sp), x
	clr	a
00126$:
	clrw	x
	ld	xl, a
	addw	x, (0x13, sp)
	clr	(x)
	inc	a
	cp	a, #0x40
	jrc	00126$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 658: c_labx0[f] = -0x4000; c_labx0b[f] = -0x4000;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 659: c_labx1[f] = 0x3FFF;  c_labx1b[f] = 0x3FFF;
	ldw	x, (0x11, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1+0), x), y
	ldw	x, (0x11, sp)
	ldw	y, #0x3fff
	ldw	((_c_labx1b+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 654: for (f = 0; f < 2; f++) {
	inc	(0x15, sp)
	ld	a, (0x15, sp)
	cp	a, #0x02
	jrc	00128$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 661: ss_init();
	call	_ss_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 662: while (ss_next(&sg)) {
00112$:
	ldw	x, sp
	incw	x
	call	_ss_next
	tnz	a
	jrne	00291$
	jp	00114$
00291$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 664: uint8_t known_all = 1;
	ld	a, #0x01
	ld	(0x13, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 666: cal_cloud(sg.u, sg.fam);
	ld	a, (0x09, sp)
	ldw	x, (0x05, sp)
	call	_cal_cloud
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 667: if (sg.k1 > NB) continue;
	ldw	x, (0x03, sp)
	cpw	x, #0x00d8
	jrugt	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 668: e = (sg.k1 < NB) ? sg.k1 : NB;
	cpw	x, #0x00d8
	jrnc	00136$
	ld	a, xl
	jra	00137$
00136$:
	ld	a, #0xd8
	clrw	x
00137$:
	ld	(0x15, sp), a
	rlwa	x
	ld	(0x14, sp), a
	rrwa	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
	ldw	x, sp
	incw	x
	ldw	(0x0e, sp), x
	ldw	x, (x)
00131$:
	cpw	x, (0x14, sp)
	jrnc	00107$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 670: if (known_bit(t) < 0) { known_all = 0; break; }
	pushw	x
	call	_known_bit
	popw	x
	tnz	a
	jrpl	00132$
	clr	(0x13, sp)
	jra	00107$
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 669: for (t = sg.k0; t < e; t++)
	incw	x
	jra	00131$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 671: if (!known_all) continue;
	tnz	(0x13, sp)
	jreq	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 672: a_bounds(sg.k0, sg.k1, &amin, &amax);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 673: if (amin == amax)
	ldw	x, (0x0a, sp)
	cpw	x, (0x0c, sp)
	jrne	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 674: cal_add(sg.k0, sg.k1, sg.u, sg.v, sg.fam, amin);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 678: int16_t h0 = width_fit(0, H0P, H0_LO, H0_HI);
	push	#0xc0
	push	#0x00
	push	#0x70
	push	#0x00
	ldw	x, #0x009a
	clr	a
	call	_width_fit
	ldw	(0x14, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 679: int16_t h1 = width_fit(1, H1P, H1_LO, H1_HI);
	push	#0x78
	push	#0x01
	push	#0xfc
	push	#0x00
	ldw	x, #0x0134
	ld	a, #0x01
	call	_width_fit
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 680: if ((h1 - h0) < SEP_LO || (h1 - h0) > SEP_HI) { h0 = H0P; h1 = H1P; }
	ldw	y, x
	subw	x, (0x14, sp)
	cpw	x, #0x0070
	jrslt	00115$
	cpw	x, #0x00c4
	jrsle	00116$
00115$:
	ldw	x, #0x009a
	ldw	(0x14, sp), x
	ldw	y, #0x0134
00116$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 681: c_h0c = h0; c_h1c = h1;
	ldw	x, (0x14, sp)
	ldw	_c_h0c+0, x
	ldw	_c_h1c+0, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
	clr	(0x15, sp)
00133$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 685: if (!theta56(f, &th)) { c_d56[f] = 0; continue; }
	ldw	x, sp
	addw	x, #12
	ld	a, (0x15, sp)
	call	_theta56
	clrw	x
	exg	a, xl
	ld	a, (0x15, sp)
	exg	a, xl
	addw	x, #(_c_d56+0)
	ldw	(0x11, sp), x
	tnz	a
	jrne	00119$
	ldw	x, (0x11, sp)
	clr	(x)
	jra	00124$
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 686: cfit = (int16_t)((c_h0c + c_h1c - c_gap56[f]) >> 1);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 687: delta = (int16_t)(th + c_c0[f] - cfit);
	ldw	x, y
	ldw	x, (_c_c0+0, x)
	addw	x, (0x0c, sp)
	subw	x, (0x13, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 688: if (delta < -EPS_CLAMP56) delta = -EPS_CLAMP56;
	cpw	x, #0xffe8
	jrsge	00121$
	ldw	x, #0xffe8
00121$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 689: if (delta > EPS_CLAMP56) delta = EPS_CLAMP56;
	ldw	y, x
	cpw	y, #0x0018
	jrsle	00123$
	ldw	x, #0x0018
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 690: c_d56[f] = (int8_t)delta;
	ld	a, xl
	ldw	x, (0x11, sp)
	ld	(x), a
00124$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 683: for (f = 0; f < 2; f++) {
	inc	(0x15, sp)
	ld	a, (0x15, sp)
	cp	a, #0x02
	jrc	00133$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 692: }
	addw	sp, #21
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 696: static uint16_t hinge(int16_t u, int16_t v, int16_t h)
;	-----------------------------------------
;	 function hinge
;	-----------------------------------------
_hinge:
	pushw	x
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 698: int16_t g = 0;
	clrw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 699: if ((int16_t)(u - h) > g) g = (int16_t)(u - h);
	subw	y, (0x07, sp)
	cpw	y, #0x0000
	jrsle	00102$
	ldw	x, y
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 700: if ((int16_t)(h - v) > g) g = (int16_t)(h - v);
	ldw	y, (0x07, sp)
	subw	y, (0x05, sp)
	ldw	(0x01, sp), y
	cpw	x, (0x01, sp)
	jrsge	00104$
	ldw	x, (0x01, sp)
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 701: return (uint16_t)g;
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 702: }
	ldw	y, (3, sp)
	addw	sp, #8
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 706: static int16_t argmin_ab(int16_t lo, int16_t hi)
;	-----------------------------------------
;	 function argmin_ab
;	-----------------------------------------
_argmin_ab:
	sub	sp, #6
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 708: uint16_t bc = 0xFFFF;
	clrw	x
	decw	x
	ldw	(0x01, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 709: uint8_t bi = 1;
	ld	a, #0x01
	ld	(0x03, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 710: int16_t a, best = lo;
	ldw	(0x04, sp), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
00108$:
	exgw	x, y
	cpw	x, (0x09, sp)
	exgw	x, y
	jrsgt	00106$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 712: uint8_t it = (uint8_t)((d_inter >> a) & 1);
	ldw	x, _d_inter+0
	ld	a, yl
	tnz	a
	jreq	00155$
00154$:
	srlw	x
	dec	a
	jrne	00154$
00155$:
	ld	a, xl
	and	a, #0x01
	ld	(0x06, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 713: if (d_costs[a] < bc || (d_costs[a] == bc && it && !bi)) {
	ldw	x, y
	sllw	x
	ldw	x, (_d_costs+0, x)
	cpw	x, (0x01, sp)
	jrc	00101$
	cpw	x, (0x01, sp)
	jrne	00109$
	tnz	(0x06, sp)
	jreq	00109$
	tnz	(0x03, sp)
	jrne	00109$
00101$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 714: bc = d_costs[a]; bi = it; best = a;
	ldw	(0x01, sp), x
	ld	a, (0x06, sp)
	ld	(0x03, sp), a
	ldw	(0x04, sp), y
00109$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 711: for (a = lo; a <= hi; a++) {
	incw	y
	jra	00108$
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 717: return best;
	ldw	x, (0x04, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 718: }
	addw	sp, #6
	popw	y
	addw	sp, #2
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 721: static int16_t decide(uint16_t k0, uint16_t k1, int16_t u, int16_t v,
;	-----------------------------------------
;	 function decide
;	-----------------------------------------
_decide:
	sub	sp, #24
	ldw	(0x15, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 725: int16_t L = (int16_t)(k1 - k0);
	ldw	x, (0x1b, sp)
	subw	x, (0x15, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 726: int16_t acap = (L < A_CAP) ? L : A_CAP;
	ldw	(0x05, sp), x
	cpw	x, #0x000f
	jrslt	00126$
	ldw	x, #0x000f
00126$:
	ldw	(0x07, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 727: int16_t h0e = c_h0c, h1e = c_h1c;
	ldw	x, _c_h0c+0
	ldw	(0x09, sp), x
	ldw	x, _c_h1c+0
	ldw	(0x0b, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 729: if (fam == 5) { h0e = (int16_t)(h0e + c_d56[0]); h1e = (int16_t)(h1e + c_d56[0]); }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 730: if (fam == 6) { h0e = (int16_t)(h0e + c_d56[1]); h1e = (int16_t)(h1e + c_d56[1]); }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 731: d_inter = 0;
	clrw	x
	ldw	_d_inter+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
	ldw	x, (0x1d, sp)
	cpw	x, (0x09, sp)
	jrslt	00273$
	clr	(0x0d, sp)
	jra	00274$
00273$:
	ld	a, #0x01
	ld	(0x0d, sp), a
00274$:
	ldw	x, (0x09, sp)
	cpw	x, (0x1f, sp)
	jrsgt	00275$
	clr	(0x0e, sp)
	jra	00276$
00275$:
	ld	a, #0x01
	ld	(0x0e, sp), a
00276$:
	clrw	x
	ldw	(0x17, sp), x
00121$:
	ldw	x, (0x17, sp)
	cpw	x, (0x07, sp)
	jrsle	00277$
	jp	00117$
00277$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 735: if (a == 0) {
	ldw	x, (0x17, sp)
	jrne	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 736: c = hinge(u, v, h0e);
	ldw	x, (0x09, sp)
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 737: it = (u < h0e && h0e <= v);
	tnz	(0x0d, sp)
	jreq	00127$
	tnz	(0x0e, sp)
	jreq	00128$
00127$:
	clr	a
	jra	00114$
00128$:
	ld	a, #0x01
	jra	00114$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 739: int16_t h = (int16_t)((a - 1) * BIT_U + h1e);
	ldw	y, (0x17, sp)
	ldw	(0x11, sp), y
	ldw	x, y
	decw	x
	clr	a
	rlwa	x
	sllw	x
	addw	x, (0x0b, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 740: c = hinge(u, v, h);
	ldw	(0x13, sp), x
	pushw	x
	ldw	x, (0x21, sp)
	pushw	x
	ldw	x, (0x21, sp)
	call	_hinge
	ldw	(0x0f, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 741: it = (u < h && h <= v);
	ldw	x, (0x1d, sp)
	cpw	x, (0x13, sp)
	jrsge	00130$
	ldw	x, (0x13, sp)
	cpw	x, (0x1f, sp)
	jrsle	00131$
00130$:
	clr	a
	.byte 0xc5
00131$:
	ld	a, #0x01
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 742: if (a < L) {
	ldw	x, (0x17, sp)
	cpw	x, (0x05, sp)
	jrsge	00114$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 743: int16_t h2 = (int16_t)(a * BIT_U + h0e);
	rlwa	x
	ld	a, (0x12, sp)
	rrwa	x
	exg	a, xl
	clr	a
	exg	a, xl
	sllw	x
	addw	x, (0x09, sp)
	ldw	(0x13, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 744: uint16_t c2 = hinge(u, v, h2);
	push	a
	ldw	x, (0x14, sp)
	pushw	x
	ldw	x, (0x22, sp)
	pushw	x
	ldw	x, (0x22, sp)
	call	_hinge
	pop	a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 745: if (c2 < c) c = c2;
	cpw	x, (0x0f, sp)
	jrnc	00106$
	ldw	(0x0f, sp), x
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 746: if (u < h2 && h2 <= v) it = 1;
	ldw	x, (0x1d, sp)
	cpw	x, (0x13, sp)
	jrsge	00114$
	ldw	x, (0x13, sp)
	cpw	x, (0x1f, sp)
	jrsgt	00114$
	ld	a, #0x01
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 749: d_costs[a] = c;
	ldw	x, (0x17, sp)
	sllw	x
	ldw	y, (0x0f, sp)
	ldw	((_d_costs+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 750: if (it) d_inter |= (uint16_t)(1u << a);
	tnz	a
	jreq	00122$
	clrw	x
	incw	x
	ld	a, (0x18, sp)
	jreq	00289$
00288$:
	sllw	x
	dec	a
	jrne	00288$
00289$:
	ld	a, xl
	or	a, _d_inter+1
	rlwa	x
	or	a, _d_inter+0
	ld	xh, a
	ldw	_d_inter+0, x
00122$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 732: for (a = 0; a <= acap; a++) {
	ldw	x, (0x17, sp)
	incw	x
	ldw	(0x17, sp), x
	jp	00121$
00117$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 753: *a_free = argmin_ab(0, acap);
	ldw	x, (0x24, sp)
	pushw	x
	ldw	y, (0x09, sp)
	pushw	y
	clrw	x
	call	_argmin_ab
	exgw	x, y
	popw	x
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 754: a_bounds(k0, k1, &amin, &amax);
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 755: lo = (amin > 0) ? amin : 0;
	ldw	x, (0x01, sp)
	cpw	x, #0x0000
	jrsgt	00134$
	clrw	x
00134$:
	ldw	(0x13, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 756: hi = (amax < acap) ? amax : acap;
	ldw	x, (0x03, sp)
	cpw	x, (0x07, sp)
	jrsge	00135$
	ldw	x, (0x03, sp)
	.byte 0xc5
00135$:
	ldw	x, (0x07, sp)
00136$:
	ldw	(0x17, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 757: if (lo > hi) { lo = 0; hi = acap; }
	ldw	x, (0x13, sp)
	cpw	x, (0x17, sp)
	jrsle	00119$
	clrw	x
	ldw	(0x13, sp), x
	ldw	y, (0x07, sp)
	ldw	(0x17, sp), y
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 758: *a_hat = argmin_ab(lo, hi);
	ldw	x, (0x22, sp)
	pushw	x
	ldw	y, (0x19, sp)
	pushw	y
	ldw	x, (0x17, sp)
	call	_argmin_ab
	exgw	x, y
	popw	x
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 759: *lo_out = lo; *hi_out = hi;
	ldw	x, (0x26, sp)
	ldw	y, (0x13, sp)
	ldw	(x), y
	ldw	x, (0x28, sp)
	ldw	y, (0x17, sp)
	ldw	(x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 760: return acap;
	ldw	x, (0x07, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 761: }
	ldw	y, (25, sp)
	addw	sp, #41
	jp	(y)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 764: static void cand_insert(uint16_t k, uint8_t m)
;	-----------------------------------------
;	 function cand_insert
;	-----------------------------------------
_cand_insert:
	sub	sp, #7
	ldw	(0x05, sp), x
	ld	(0x04, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 766: uint8_t i = v_ncand, j;
	ld	a, _v_ncand+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 767: while (i > 0 && v_cand_m[i - 1] > m) i--;
	ld	(0x07, sp), a
00102$:
	tnz	a
	jreq	00132$
	ld	xl, a
	decw	x
	push	a
	ld	a, xl
	rlc	a
	clr	a
	sbc	a, #0x00
	ld	xh, a
	pop	a
	addw	x, #(_v_cand_m+0)
	push	a
	ld	a, (x)
	cp	a, (0x05, sp)
	pop	a
	jrule	00132$
	dec	a
	jra	00102$
00132$:
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 768: if (i >= A_MAX) return;
	cp	a, #0x05
	jrnc	00112$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 769: j = (v_ncand < A_MAX) ? v_ncand : (A_MAX - 1);
	ld	a, _v_ncand+0
	cp	a, #0x05
	jrnc	00114$
	ld	a, (0x07, sp)
	.byte 0xc5
00114$:
	ld	a, #0x04
00115$:
	ld	(0x07, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 770: while (j > i) {
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 771: v_cand_t[j] = v_cand_t[j - 1];
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 772: v_cand_m[j] = v_cand_m[j - 1];
	clrw	x
	ld	a, (0x07, sp)
	ld	xl, a
	addw	x, #(_v_cand_m+0)
	ldw	y, (0x02, sp)
	addw	y, #(_v_cand_m+0)
	ld	a, (y)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 773: j--;
	dec	(0x07, sp)
	jra	00107$
00109$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 775: v_cand_t[i] = k;
	ld	a, (0x01, sp)
	clrw	x
	ld	xl, a
	sllw	x
	ldw	y, (0x05, sp)
	ldw	((_v_cand_t+0), x), y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 776: v_cand_m[i] = m;
	clrw	x
	ld	a, (0x01, sp)
	ld	xl, a
	ld	a, (0x04, sp)
	ld	((_v_cand_m+0), x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 777: if (v_ncand < A_MAX) v_ncand++;
	ld	a, _v_ncand+0
	cp	a, #0x05
	jrnc	00112$
	inc	_v_ncand+0
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 778: }
	addw	sp, #7
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 780: static void decide_pass(void)
;	-----------------------------------------
;	 function decide_pass
;	-----------------------------------------
_decide_pass:
	sub	sp, #33
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 784: for (t = 0; t < NBB; t++) d_bits[t] = 0;
	clr	a
00168$:
	clrw	x
	ld	xl, a
	clr	((_d_bits+0), x)
	inc	a
	cp	a, #0x1b
	jrc	00168$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 785: d_infeas = 0; d_laberr = 0; d_nseg = 0;
	clrw	x
	ldw	_d_infeas+0, x
	clrw	x
	ldw	_d_laberr+0, x
	clrw	x
	ldw	_d_nseg+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 786: v_ncand = 0; v_nweak = 0; v_ntied = 0; v_tiepend = -1;
	clr	_v_ncand+0
	clrw	x
	ldw	_v_nweak+0, x
	clrw	x
	ldw	_v_ntied+0, x
	clrw	x
	decw	x
	ldw	_v_tiepend+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 787: ss_init();
	call	_ss_init
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 788: while (ss_next(&sg)) {
00165$:
	ldw	x, sp
	incw	x
	call	_ss_next
	tnz	a
	jrne	00557$
	jp	00185$
00557$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 791: int16_t tie_here = -1, ins0 = -1, ins1 = -1;
	clrw	x
	decw	x
	ldw	(0x12, sp), x
	clrw	x
	decw	x
	ldw	(0x19, sp), x
	clrw	x
	decw	x
	ldw	(0x1b, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 794: d_nseg++;
	ldw	x, _d_nseg+0
	incw	x
	ldw	_d_nseg+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
	ldw	x, sp
	incw	x
	ldw	(0x14, sp), x
	ldw	x, (x)
	ldw	(0x17, sp), x
	cpw	x, #0x00d8
	jrnc	00165$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 797: &a_hat, &a_free, &lo, &hi);
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 796: acap = decide(sg.k0, sg.k1, sg.u, sg.v, sg.fam,
	ld	a, (0x09, sp)
	ldw	y, (0x07, sp)
	ldw	(0x1e, sp), y
	ldw	y, (0x05, sp)
	ldw	(0x20, sp), y
	ldw	y, (0x03, sp)
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
	ldw	x, (0x27, sp)
	pushw	x
	ldw	x, (0x2b, sp)
	pushw	x
	pushw	y
	ldw	x, (0x26, sp)
	call	_decide
	ldw	(0x1d, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 798: c_hat = d_costs[a_hat];
	ldw	x, (0x0a, sp)
	sllw	x
	ldw	x, (_d_costs+0, x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 799: if (c_hat > INFEAS_U) d_infeas++;
	cpw	x, #0x00a0
	jrule	00105$
	ldw	x, _d_infeas+0
	incw	x
	ldw	_d_infeas+0, x
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 800: kk1 = (sg.k1 < NB) ? sg.k1 : NB;
	ldw	x, (0x03, sp)
	cpw	x, #0x00d8
	jrnc	00187$
	ld	a, xl
	jra	00188$
00187$:
	ld	a, #0xd8
	clrw	x
00188$:
	ld	(0x17, sp), a
	rlwa	x
	ld	(0x16, sp), a
	rrwa	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 801: known_all = 1;
	ld	a, #0x01
	ld	(0x1f, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
	ldw	x, (0x14, sp)
	ldw	x, (x)
00171$:
	cpw	x, (0x16, sp)
	jrnc	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 803: if (known_bit(t) < 0) { known_all = 0; break; }
	pushw	x
	call	_known_bit
	popw	x
	tnz	a
	jrpl	00172$
	clr	(0x1f, sp)
	jra	00108$
00172$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 802: for (t = sg.k0; t < kk1; t++)
	incw	x
	jra	00171$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 804: dead = 0; nins = 0;
	clr	(0x20, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
	clr	(0x21, sp)
	clrw	x
00174$:
	cpw	x, (0x1d, sp)
	jrsgt	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 806: if ((d_inter >> a) & 1) nins++;
	ldw	y, _d_inter+0
	ld	a, xl
	tnz	a
	jreq	00565$
00564$:
	srlw	y
	dec	a
	jrne	00564$
00565$:
	srlw	y
	jrnc	00175$
	inc	(0x21, sp)
00175$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 805: for (a = 0; a <= acap; a++)
	incw	x
	jra	00174$
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 807: if (nins >= 2) dead = 1;
	ld	a, (0x21, sp)
	cp	a, #0x02
	jrc	00113$
	ld	a, #0x01
	ld	(0x20, sp), a
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 808: if (known_all && lo == hi && a_free != lo && !dead)
	tnz	(0x1f, sp)
	jreq	00115$
	ldw	x, (0x0e, sp)
	cpw	x, (0x10, sp)
	jrne	00115$
	ldw	x, (0x0c, sp)
	cpw	x, (0x0e, sp)
	jreq	00115$
	tnz	(0x20, sp)
	jrne	00115$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 809: d_laberr++;
	ldw	x, _d_laberr+0
	incw	x
	ldw	_d_laberr+0, x
00115$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
	ldw	x, (0x0e, sp)
	clr	(0x1f, sp)
00177$:
	cpw	x, (0x10, sp)
	jrsgt	00126$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 815: if ((d_inter >> a) & 1) {
	ldw	y, _d_inter+0
	ld	a, xl
	tnz	a
	jreq	00578$
00577$:
	srlw	y
	dec	a
	jrne	00577$
00578$:
	srlw	y
	jrnc	00178$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 816: if (nins == 0) ins0 = a; else if (nins == 1) ins1 = a;
	tnz	(0x1f, sp)
	jrne	00122$
	ldw	(0x19, sp), x
	jra	00123$
00122$:
	ld	a, (0x1f, sp)
	dec	a
	jrne	00123$
	ldw	(0x1b, sp), x
00123$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 817: nins++;
	inc	(0x1f, sp)
00178$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 814: for (a = lo; a <= hi; a++) {
	incw	x
	jra	00177$
00126$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 795: if (sg.k0 >= NB) continue;
	ldw	x, (0x14, sp)
	ldw	x, (x)
	ldw	(0x20, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 820: if (nins >= 2 && (a_hat == ins0 || a_hat == ins1)) {
	ld	a, (0x1f, sp)
	cp	a, #0x02
	jrc	00130$
	ldw	x, (0x0a, sp)
	cpw	x, (0x19, sp)
	jreq	00129$
	ldw	x, (0x0a, sp)
	cpw	x, (0x1b, sp)
	jrne	00130$
00129$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 821: uint16_t tt = (uint16_t)(sg.k0 + ins0);
	ldw	x, (0x19, sp)
	addw	x, (0x20, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 822: if (tt < NB) tie_here = (int16_t)tt;
	cpw	x, #0x00d8
	jrnc	00130$
	ldw	(0x12, sp), x
00130$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
	ldw	y, (0x20, sp)
	ldw	(0x1e, sp), y
00183$:
	ldw	x, (0x1e, sp)
	cpw	x, (0x16, sp)
	jrc	00592$
	jp	00159$
00592$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 826: int16_t off = (int16_t)(t - sg.k0);
	ldw	x, (0x14, sp)
	ldw	x, (x)
	negw	x
	addw	x, (0x1e, sp)
	ldw	(0x18, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 827: uint16_t c0m = 0xFFFF, c1m = 0xFFFF, m;
	clrw	x
	decw	x
	ldw	(0x1a, sp), x
	clrw	x
	decw	x
	ldw	(0x1c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 828: if (off < a_hat) BSET(d_bits, t);
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
	jreq	00595$
00594$:
	sll	(1, sp)
	dec	a
	jrne	00594$
00595$:
	pop	a
	or	a, (0x20, sp)
	ld	(x), a
00134$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
	ldw	y, (0x0e, sp)
	ldw	(0x20, sp), y
00180$:
	ldw	x, (0x20, sp)
	cpw	x, (0x10, sp)
	jrsgt	00142$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 830: if (a > off) { if (d_costs[a] < c1m) c1m = d_costs[a]; }
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 831: else         { if (d_costs[a] < c0m) c0m = d_costs[a]; }
	cpw	x, (0x1a, sp)
	jrnc	00181$
	ldw	(0x1a, sp), x
00181$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 829: for (a = lo; a <= hi; a++) {
	ldw	x, (0x20, sp)
	incw	x
	ldw	(0x20, sp), x
	jra	00180$
00142$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 833: if (c0m == 0xFFFF || c1m == 0xFFFF) m = 255;
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
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 835: int16_t dm = (int16_t)(c0m - c1m);
	ldw	x, (0x1a, sp)
	subw	x, (0x1c, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 836: if (dm < 0) dm = (int16_t)-dm;
	ldw	(0x20, sp), x
	tnzw	x
	jrpl	00144$
	neg	(0x21, sp)
	clr	a
	sbc	a, (0x20, sp)
	ld	(0x20, sp), a
00144$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 837: m = (dm > 255) ? 255 : (uint16_t)dm;
	ldw	x, #0x00ff
	cpw	x, (0x20, sp)
	jrsgt	00189$
	ldw	(0x20, sp), x
00189$:
00147$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 839: if ((int16_t)t == tie_here || (int16_t)t == v_tiepend)
	ldw	x, (0x1e, sp)
	cpw	x, (0x12, sp)
	jreq	00149$
	cpw	x, _v_tiepend+0
	jrne	00150$
00149$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 840: m = 0;                       /* decided by tie-break */
	clrw	x
	ldw	(0x20, sp), x
00150$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 841: if (t >= PP_LO && t < PP_HI) {   /* payload' bits only   */
	ldw	x, (0x1e, sp)
	cpw	x, #0x0020
	jrc	00184$
	ldw	y, (0x1e, sp)
	cpw	y, #0x00b8
	jrnc	00184$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 842: if (m <= MG_MAX) {
	ldw	y, (0x20, sp)
	cpw	y, #0x0008
	jrugt	00184$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 843: uint16_t k = t - PP_LO;
	subw	x, #0x0020
	ldw	(0x1c, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 844: v_nweak++;
	ldw	x, _v_nweak+0
	incw	x
	ldw	_v_nweak+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 845: if (m == 0) v_ntied++;
	ldw	x, (0x20, sp)
	jrne	00153$
	ldw	x, _v_ntied+0
	incw	x
	ldw	_v_ntied+0, x
00153$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 846: cand_insert(k, (uint8_t)m);
	ld	a, (0x21, sp)
	ldw	x, (0x1c, sp)
	call	_cand_insert
00184$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 825: for (t = sg.k0; t < kk1; t++) {
	ldw	x, (0x1e, sp)
	incw	x
	ldw	(0x1e, sp), x
	jp	00183$
00159$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 850: if (v_tiepend >= 0 && v_tiepend < (int16_t)kk1)
	ldw	x, _v_tiepend+0
	ldw	y, (0x16, sp)
	ldw	(0x20, sp), y
	tnzw	x
	jrmi	00161$
	ldw	x, (0x20, sp)
	cpw	x, _v_tiepend+0
	jrsle	00161$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 851: v_tiepend = -1;                  /* consumed              */
	clrw	x
	decw	x
	ldw	_v_tiepend+0, x
00161$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 852: if (tie_here >= (int16_t)kk1)
	ldw	x, (0x12, sp)
	cpw	x, (0x20, sp)
	jrsge	00622$
	jp	00165$
00622$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 853: v_tiepend = tie_here;            /* lands in next segment */
	ldw	x, (0x12, sp)
	ldw	_v_tiepend+0, x
	jp	00165$
00185$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 855: }
	addw	sp, #33
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 861: static uint8_t crc8(const uint8_t *d, uint8_t n)
;	-----------------------------------------
;	 function crc8
;	-----------------------------------------
_crc8:
	sub	sp, #4
	ldw	(0x02, sp), x
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 863: uint8_t r = 0, i, j;
	clrw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 864: for (i = 0; i < n; i++) {
	clr	a
	ld	xl, a
00107$:
	ld	a, xl
	cp	a, (0x01, sp)
	jrnc	00102$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 865: r ^= d[i];
	clrw	y
	exg	a, yl
	ld	a, xl
	exg	a, yl
	addw	y, (0x02, sp)
	ld	a, (y)
	pushw	x
	xor	a, (1, sp)
	popw	x
	ld	xh, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 866: for (j = 0; j < 8; j++)
	ld	a, #0x08
	ld	(0x04, sp), a
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 867: r = (r & 0x80) ? (uint8_t)((uint8_t)(r << 1) ^ CRC8_POLY)
	ld	a, xh
	sll	a
	tnzw	x
	jrpl	00111$
	xor	a, #0x07
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 868: : (uint8_t)(r << 1);
00111$:
	ld	xh, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 866: for (j = 0; j < 8; j++)
	dec	(0x04, sp)
	jrne	00105$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 864: for (i = 0; i < n; i++) {
	ld	a, xl
	inc	a
	ld	xl, a
	jra	00107$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 870: return r;
	ld	a, xh
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 871: }
	addw	sp, #4
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 874: static uint8_t syn8(uint16_t k)
;	-----------------------------------------
;	 function syn8
;	-----------------------------------------
_syn8:
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 876: uint8_t p = (uint8_t)(k >> 3);
	ldw	y, x
	srlw	x
	srlw	x
	srlw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 877: uint8_t b = (uint8_t)(7 - (k & 7));
	ld	a, yl
	and	a, #0x07
	ld	(0x02, sp), a
	ld	a, #0x07
	sub	a, (0x02, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 878: uint16_t j = (uint16_t)(8u * (uint16_t)(ND_DATA - 1 - p) + b + 8u);
	exg	a, xl
	ld	(0x02, sp), a
	exg	a, xl
	clr	(0x01, sp)
	ldw	x, #0x000f
	subw	x, (0x01, sp)
	sllw	x
	sllw	x
	sllw	x
	ld	(0x02, sp), a
	clr	(0x01, sp)
	addw	x, (0x01, sp)
	addw	x, #0x0008
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 879: while (j >= 127u) j -= 127u;   /* <= 4 iterations at ND = 48 */
00101$:
	ldw	y, x
	cpw	y, #0x007f
	jrc	00103$
	ldw	x, y
	subw	x, #0x007f
	jra	00101$
00103$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 880: return XPOW[j];
	ld	a, (_XPOW+0, x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 881: }
	popw	x
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 883: static uint8_t parity8(uint8_t x)
;	-----------------------------------------
;	 function parity8
;	-----------------------------------------
_parity8:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 885: x ^= (uint8_t)(x >> 4);
	push	a
	swap	a
	and	a, #0x0f
	xor	a, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 886: x ^= (uint8_t)(x >> 2);
	ld	(0x01, sp), a
	srl	(0x01, sp)
	srl	(0x01, sp)
	xor	a, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 887: x ^= (uint8_t)(x >> 1);
	ld	(0x01, sp), a
	srl	(0x01, sp)
	xor	a, (0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 888: return (uint8_t)(x & 1);
	and	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 889: }
	addw	sp, #1
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 892: static uint8_t maj3(uint8_t c0, uint8_t c1, uint8_t c2, uint8_t *r)
;	-----------------------------------------
;	 function maj3
;	-----------------------------------------
_maj3:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 894: if (c0 == c1 || c0 == c2) { *r = c0; return 1; }
	ldw	x, (0x05, sp)
	cp	a, (0x03, sp)
	jreq	00101$
	cp	a, (0x04, sp)
	jrne	00102$
00101$:
	ld	(x), a
	ld	a, #0x01
	jra	00106$
00102$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 895: if (c1 == c2)             { *r = c1; return 1; }
	ld	a, (0x03, sp)
	cp	a, (0x04, sp)
	jrne	00105$
	ld	a, (0x03, sp)
	ld	(x), a
	ld	a, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 896: return 0;
	.byte 0x21
00105$:
	clr	a
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 897: }
	ldw	x, (1, sp)
	addw	sp, #6
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 906: static uint8_t try_trial(uint8_t i, uint8_t j)
;	-----------------------------------------
;	 function try_trial
;	-----------------------------------------
_try_trial:
	sub	sp, #11
	ld	(0x09, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 910: uint8_t r = ch_rbase, Rp, m, idx, amb;
	ld	a, _ch_rbase+0
	ld	(0x0a, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 911: Cp[0] = d_pp[ND_DATA]; Cp[1] = d_pp[ND_DATA + 1];
	ld	a, _d_pp+16
	ld	(0x01, sp), a
	ld	a, _d_pp+17
	ld	(0x02, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 912: Cp[2] = d_pp[ND_DATA + 2];
	ld	a, _d_pp+18
	ld	(0x03, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 913: sel[0] = i; sel[1] = j;
	ld	a, (0x09, sp)
	ld	(0x04, sp), a
	ld	a, (0x0e, sp)
	ld	(0x05, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 914: dec_info.trials++;
	ldw	x, #(_dec_info+0)+2
	inc	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 915: for (m = 0; m < 2; m++) {
	clr	(0x0b, sp)
00133$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 917: idx = sel[m];
	clrw	x
	ld	a, (0x0b, sp)
	ld	xl, a
	pushw	x
	ldw	x, sp
	addw	x, #6
	addw	x, (1, sp)
	addw	sp, #2
	ld	a, (x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 918: if (idx == 0xFF) break;
	cp	a, #0xff
	jreq	00106$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 919: k = v_cand_t[idx];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_v_cand_t+0, x)
	ldw	y, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 920: if (k < ND8) {
	cpw	y, #0x0080
	jrnc	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 921: r ^= syn8(k);                   /* data bit: XOR syndrome    */
	ldw	x, y
	call	_syn8
	xor	a, (0x0a, sp)
	ld	(0x0a, sp), a
	jra	00134$
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 923: uint16_t kc = k - ND8;          /* check bit: move the ref   */
	ldw	x, y
	subw	x, #0x0080
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 924: Cp[kc >> 3] ^= (uint8_t)(1u << (7 - (k & 7)));
	srlw	x
	srlw	x
	srlw	x
	ldw	(0x07, sp), x
	ldw	x, sp
	incw	x
	addw	x, (0x07, sp)
	ld	a, (x)
	ld	(0x07, sp), a
	ld	a, yl
	and	a, #0x07
	ld	(0x08, sp), a
	ld	a, #0x07
	sub	a, (0x08, sp)
	ld	(0x08, sp), a
	ld	a, #0x01
	push	a
	ld	a, (0x09, sp)
	jreq	00295$
00294$:
	sll	(1, sp)
	dec	a
	jrne	00294$
00295$:
	pop	a
	xor	a, (0x07, sp)
	ld	(x), a
00134$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 915: for (m = 0; m < 2; m++) {
	inc	(0x0b, sp)
	ld	a, (0x0b, sp)
	cp	a, #0x02
	jrc	00133$
00106$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 927: if (!maj3(Cp[0], Cp[1], Cp[2], &Rp)) return 0; /* slot burned, no ref */
	ldw	x, sp
	addw	x, #6
	exgw	x, y
	ld	a, (0x03, sp)
	ld	xl, a
	ld	a, (0x02, sp)
	ld	xh, a
	ld	a, (0x01, sp)
	ld	(0x0b, sp), a
	pushw	y
	ld	a, xl
	push	a
	ld	a, xh
	push	a
	ld	a, (0x0f, sp)
	call	_maj3
	tnz	a
	jrne	00108$
	clr	a
	jp	00140$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 928: if (r != Rp) return 0;
	ld	a, (0x0a, sp)
	cp	a, (0x06, sp)
	jreq	00110$
	clr	a
	jp	00140$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 931: amb = 0;
	clr	(0x07, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 932: for (m = 0; m < 2; m++) {
	clr	(0x0a, sp)
00137$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 935: idx = sel[m];
	clrw	x
	ld	a, (0x0a, sp)
	ld	xl, a
	pushw	x
	ldw	x, sp
	addw	x, #6
	addw	x, (1, sp)
	addw	sp, #2
	ld	a, (x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 936: if (idx == 0xFF) break;
	cp	a, #0xff
	jreq	00125$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 937: ki = v_cand_t[idx];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_v_cand_t+0, x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 938: if (ki >= ND8) continue;
	cpw	x, #0x0080
	jrnc	00124$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 939: si = syn8(ki);
	call	_syn8
	ld	(0x08, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 940: for (jj = 0; jj < ch_n; jj++) {
	clr	(0x0b, sp)
00136$:
	ld	a, (0x0b, sp)
	cp	a, _ch_n+0
	jrnc	00124$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 941: if (jj == i || jj == j) continue;
	ld	a, (0x0b, sp)
	cp	a, (0x09, sp)
	jreq	00122$
	ld	a, (0x0b, sp)
	cp	a, (0x0e, sp)
	jreq	00122$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 942: if (v_cand_t[jj] < ND8) {
	ld	a, (0x0b, sp)
	clrw	x
	ld	xl, a
	sllw	x
	addw	x, #(_v_cand_t+0)
	ldw	y, x
	ldw	x, (x)
	cpw	x, #0x0080
	jrnc	00122$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 943: dec_info.alias_cmp++;
	ldw	x, #(_dec_info+0)+3
	inc	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 944: if (syn8(v_cand_t[jj]) == si) amb = 1;
	ldw	x, y
	ldw	x, (x)
	call	_syn8
	sub	a, (0x08, sp)
	jrne	00122$
	inc	a
	ld	(0x07, sp), a
00122$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 940: for (jj = 0; jj < ch_n; jj++) {
	inc	(0x0b, sp)
	jra	00136$
00124$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 932: for (m = 0; m < 2; m++) {
	inc	(0x0a, sp)
	ld	a, (0x0a, sp)
	cp	a, #0x02
	jrc	00137$
00125$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 948: if (amb) return 0;
	tnz	(0x07, sp)
	jreq	00177$
	clr	a
	jra	00140$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 950: for (m = 0; m < 2; m++) {
00177$:
	clr	(0x0b, sp)
00138$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 952: idx = sel[m];
	clrw	x
	ld	a, (0x0b, sp)
	ld	xl, a
	pushw	x
	ldw	x, sp
	addw	x, #6
	addw	x, (1, sp)
	addw	sp, #2
	ld	a, (x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 953: if (idx == 0xFF) break;
	cp	a, #0xff
	jreq	00132$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 954: k = v_cand_t[idx];
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_v_cand_t+0, x)
	ldw	y, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 955: if (k < ND8)
	cpw	y, #0x0080
	jrnc	00139$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 956: d_pp[k >> 3] ^= (uint8_t)(1u << (7 - (k & 7)));
	ldw	x, y
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_pp+0)
	ld	a, (x)
	ld	(0x08, sp), a
	ld	a, yl
	and	a, #0x07
	ld	(0x0a, sp), a
	ld	a, #0x07
	sub	a, (0x0a, sp)
	ld	(0x0a, sp), a
	ld	a, #0x01
	push	a
	ld	a, (0x0b, sp)
	jreq	00323$
00322$:
	sll	(1, sp)
	dec	a
	jrne	00322$
00323$:
	pop	a
	xor	a, (0x08, sp)
	ld	(x), a
00139$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 950: for (m = 0; m < 2; m++) {
	inc	(0x0b, sp)
	ld	a, (0x0b, sp)
	cp	a, #0x02
	jrc	00138$
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 958: return 1;
	ld	a, #0x01
00140$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 959: }
	addw	sp, #11
	popw	x
	addw	sp, #1
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 963: static uint8_t chase_singles(uint8_t want)
;	-----------------------------------------
;	 function chase_singles
;	-----------------------------------------
_chase_singles:
	pushw	x
	ld	(0x01, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 966: for (p = 0; p < ch_n; p++)
	clr	(0x02, sp)
00106$:
	ld	a, (0x02, sp)
	cp	a, _ch_n+0
	jrnc	00104$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 967: if (ch_isd[p] == want && try_trial(p, 0xFF)) return 1;
	clrw	x
	ld	a, (0x02, sp)
	ld	xl, a
	ld	a, (_ch_isd+0, x)
	cp	a, (0x01, sp)
	jrne	00107$
	push	#0xff
	ld	a, (0x03, sp)
	call	_try_trial
	tnz	a
	jreq	00107$
	ld	a, #0x01
	jra	00108$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 966: for (p = 0; p < ch_n; p++)
	inc	(0x02, sp)
	jra	00106$
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 968: return 0;
	clr	a
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 969: }
	popw	x
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 974: static uint8_t chase_pairs(uint8_t sum_want)
;	-----------------------------------------
;	 function chase_pairs
;	-----------------------------------------
_chase_pairs:
	sub	sp, #6
	ld	(0x04, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (p = 0; p < ch_n; p++)
	clr	(0x05, sp)
00110$:
	ld	a, (0x05, sp)
	cp	a, _ch_n+0
	jrnc	00105$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: for (j = (uint8_t)(p + 1); j < ch_n; j++)
	ld	a, (0x05, sp)
	inc	a
	ld	(0x06, sp), a
	clrw	x
	ld	a, (0x05, sp)
	ld	xl, a
	addw	x, #(_ch_isd+0)
	ldw	(0x01, sp), x
00107$:
	ld	a, (0x06, sp)
	cp	a, _ch_n+0
	jrnc	00111$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 979: if ((uint8_t)(ch_isd[p] + ch_isd[j]) == sum_want &&
	ldw	x, (0x01, sp)
	ld	a, (x)
	ld	(0x03, sp), a
	clrw	x
	ld	a, (0x06, sp)
	ld	xl, a
	ld	a, (_ch_isd+0, x)
	add	a, (0x03, sp)
	cp	a, (0x04, sp)
	jrne	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 980: try_trial(p, j))
	ld	a, (0x06, sp)
	push	a
	ld	a, (0x06, sp)
	call	_try_trial
	tnz	a
	jreq	00108$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 981: return 1;
	ld	a, #0x01
	jra	00112$
00108$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 978: for (j = (uint8_t)(p + 1); j < ch_n; j++)
	inc	(0x06, sp)
	jra	00107$
00111$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 977: for (p = 0; p < ch_n; p++)
	inc	(0x05, sp)
	jra	00110$
00105$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 982: return 0;
	clr	a
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 983: }
	addw	sp, #6
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 989: static uint8_t chase(uint8_t *out)
;	-----------------------------------------
;	 function chase
;	-----------------------------------------
_chase:
	sub	sp, #8
	ldw	(0x05, sp), x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
	clr	(0x07, sp)
00132$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 994: uint8_t val = 0;
	clr	a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 995: uint16_t base = PP_LO + ((uint16_t)p << 3);
	exg	a, xl
	ld	a, (0x07, sp)
	exg	a, xl
	sllw	x
	sllw	x
	sllw	x
	addw	x, #32
	ldw	y, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
	clr	(0x08, sp)
00130$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 997: val = (uint8_t)((val << 1) | BGET(d_bits, base + j));
	sll	a
	ld	(0x02, sp), a
	ld	a, (0x08, sp)
	ld	(0x04, sp), a
	clr	(0x03, sp)
	ldw	x, y
	clr	a
	ld	xh, a
	addw	x, (0x03, sp)
	srlw	x
	srlw	x
	srlw	x
	addw	x, #(_d_bits+0)
	ld	a, (x)
	ld	xl, a
	ld	a, yl
	add	a, (0x08, sp)
	and	a, #0x07
	jreq	00319$
00318$:
	exg	a, xl
	srl	a
	exg	a, xl
	dec	a
	jrne	00318$
00319$:
	ld	a, xl
	and	a, #0x01
	or	a, (0x02, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 996: for (j = 0; j < 8; j++)
	inc	(0x08, sp)
	push	a
	ld	a, (0x09, sp)
	cp	a, #0x08
	pop	a
	jrc	00130$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 998: d_pp[p] = val;
	clrw	x
	exg	a, xl
	ld	a, (0x07, sp)
	exg	a, xl
	addw	x, #(_d_pp+0)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 993: for (p = 0; p < NPP; p++) {
	inc	(0x07, sp)
	ld	a, (0x07, sp)
	cp	a, #0x13
	jrc	00132$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1000: dec_info.n_weak = v_nweak;
	mov	_dec_info+6, _v_nweak+1
	mov	_dec_info+5, _v_nweak+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1001: dec_info.n_tied = v_ntied;
	mov	_dec_info+8, _v_ntied+1
	mov	_dec_info+7, _v_ntied+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1010: uint8_t R = 0, have_R, par;
	clr	(0x01, sp)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1011: ch_rbase = crc8(d_pp, ND_DATA);
	ld	a, #0x10
	ldw	x, #(_d_pp+0)
	call	_crc8
	ld	_ch_rbase+0, a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1012: have_R = maj3(d_pp[ND_DATA], d_pp[ND_DATA + 1], d_pp[ND_DATA + 2], &R);
	ldw	y, sp
	incw	y
	ld	a, _d_pp+18
	ld	(0x08, sp), a
	ld	a, _d_pp+17
	ld	xl, a
	ld	a, _d_pp+16
	ld	xh, a
	pushw	y
	ld	a, (0x0a, sp)
	push	a
	ld	a, xl
	push	a
	ld	a, xh
	call	_maj3
	ld	(0x07, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1014: if (v_ntied > TIE_EMIT) { dec_info.cause = CAUSE_EMITGATE; return DEC_REFUSE; }
	ldw	x, _v_ntied+0
	cpw	x, #0x0008
	jrule	00104$
	mov	_dec_info+1, #0x05
	clr	a
	jp	00141$
00104$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1016: if (have_R && ch_rbase == R) {
	tnz	(0x07, sp)
	jreq	00107$
	ld	a, (0x01, sp)
	cp	a, _ch_rbase+0
	jrne	00107$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1017: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
	clr	a
00134$:
	clrw	y
	ld	yl, a
	addw	y, (0x05, sp)
	clrw	x
	ld	xl, a
	addw	x, #(_d_pp+0)
	push	a
	ld	a, (x)
	ld	(y), a
	pop	a
	inc	a
	cp	a, #0x10
	jrc	00134$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1018: return DEC_DIRECT;
	ld	a, #0x01
	jp	00141$
00107$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1021: if (v_nweak == 0) { dec_info.cause = CAUSE_NOCAND; return DEC_REFUSE; }
	ldw	x, _v_nweak+0
	jrne	00110$
	mov	_dec_info+1, #0x06
	clr	a
	jp	00141$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1022: if (v_nweak > A_MAX) { dec_info.cause = CAUSE_ADMIT; return DEC_REFUSE; }
	ldw	x, _v_nweak+0
	cpw	x, #0x0005
	jrule	00112$
	mov	_dec_info+1, #0x07
	clr	a
	jp	00141$
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1024: ch_n = v_ncand;
	mov	_ch_n+0, _v_ncand+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1025: for (p = 0; p < ch_n; p++)
	clr	(0x08, sp)
00137$:
	ld	a, (0x08, sp)
	cp	a, _ch_n+0
	jrnc	00113$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1026: ch_isd[p] = (v_cand_t[p] < ND8);
	clrw	y
	ld	a, (0x08, sp)
	ld	yl, a
	addw	y, #(_ch_isd+0)
	ld	a, (0x08, sp)
	clrw	x
	ld	xl, a
	sllw	x
	ldw	x, (_v_cand_t+0, x)
	cpw	x, #0x0080
	clr	a
	rlc	a
	ld	(y), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1025: for (p = 0; p < ch_n; p++)
	inc	(0x08, sp)
	jra	00137$
00113$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1027: par = have_R ? parity8((uint8_t)(ch_rbase ^ R)) : 0xFF;
	tnz	(0x07, sp)
	jreq	00143$
	ld	a, (0x01, sp)
	xor	a, _ch_rbase+0
	call	_parity8
	.byte 0xc5
00143$:
	ld	a, #0xff
00144$:
	ld	(0x08, sp), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1028: dec_info.chased = 1;
	mov	_dec_info+4, #0x01
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1031: if (chase_singles(0)) goto accept;      /* phase 1: one check bit */
	clr	a
	call	_chase_singles
	tnz	a
	jrne	00185$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1032: if (chase_pairs(0)) goto accept;        /* phase 2: two check bits */
	clr	a
	call	_chase_pairs
	tnz	a
	jrne	00185$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1033: if (!(have_R && par == 0) &&            /* phase 3: one data bit */
	tnz	(0x07, sp)
	jreq	00121$
	tnz	(0x08, sp)
	jreq	00119$
00121$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1034: chase_singles(1)) goto accept;
	ld	a, #0x01
	call	_chase_singles
	tnz	a
	jrne	00185$
00119$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1035: if (chase_pairs(1)) goto accept;        /* phase 4: data + check */
	ld	a, #0x01
	call	_chase_pairs
	tnz	a
	jrne	00185$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1036: if (!(have_R && par == 1) &&            /* phase 5: two data bits */
	tnz	(0x07, sp)
	jreq	00127$
	ld	a, (0x08, sp)
	dec	a
	jreq	00125$
00127$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1037: chase_pairs(2)) goto accept;
	ld	a, #0x02
	call	_chase_pairs
	tnz	a
	jrne	00185$
00125$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1038: dec_info.cause = CAUSE_CHASE;           /* R8: the honest end */
	mov	_dec_info+1, #0x08
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1039: return DEC_REFUSE;
	clr	a
	jra	00141$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1041: for (p = 0; p < ND_DATA; p++) out[p] = d_pp[p];
00185$:
	clr	a
00139$:
	clrw	y
	ld	yl, a
	addw	y, (0x05, sp)
	clrw	x
	ld	xl, a
	addw	x, #(_d_pp+0)
	push	a
	ld	a, (x)
	ld	(y), a
	pop	a
	inc	a
	cp	a, #0x10
	jrc	00139$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1042: return DEC_CHASE;
	ld	a, #0x02
00141$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1045: }
	addw	sp, #8
	ret
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1049: uint8_t ws_decode_ex(const uint8_t *cap, uint16_t ncap, uint8_t *out)
;	-----------------------------------------
;	 function ws_decode_ex
;	-----------------------------------------
_ws_decode_ex:
	pushw	x
	exgw	x, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
	clr	a
00115$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1055: ((uint8_t *)&dec_info)[t] = 0;
	clrw	x
	ld	xl, a
	clr	((_dec_info+0), x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1054: for (t = 0; t < sizeof(dec_info); t++)
	inc	a
	cp	a, #0x14
	jrc	00115$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1056: scan_cap = cap;
	ldw	_scan_cap+0, y
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1057: scan_len = ncap;
	ldw	x, (0x05, sp)
	ldw	_scan_len+0, x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1058: if (!seed()) { dec_info.cause = CAUSE_LOCK; return DEC_REFUSE; }   /* R1 */
	call	_seed
	tnz	a
	jrne	00139$
	mov	_dec_info+1, #0x01
	clr	a
	jp	00122$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1059: for (r = 0; r < 2; r++) refine();
00139$:
	ld	a, #0x02
00119$:
	push	a
	call	_refine
	pop	a
	dec	a
	jrne	00119$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1060: calibrate();
	call	_calibrate
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1061: decide_pass();
	call	_decide_pass
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1062: dec_info.K = g_K;
	mov	_dec_info+10, _g_K+1
	mov	_dec_info+9, _g_K+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1063: dec_info.tau = g_tau;
	mov	_dec_info+12, _g_tau+1
	mov	_dec_info+11, _g_tau+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1064: dec_info.infeasible = d_infeas;
	mov	_dec_info+15, _d_infeas+1
	mov	_dec_info+14, _d_infeas+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1065: dec_info.label_err = d_laberr;
	mov	_dec_info+17, _d_laberr+1
	mov	_dec_info+16, _d_laberr+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1066: dec_info.n_seg = d_nseg;
	mov	_dec_info+19, _d_nseg+1
	mov	_dec_info+18, _d_nseg+0
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
	clr	(0x02, sp)
	clrw	x
00120$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1068: int8_t kb = known_bit(t);
	pushw	x
	call	_known_bit
	ld	(0x03, sp), a
	popw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1069: if (kb >= 0 && (int8_t)BGET(d_bits, t) != kb) viol++;
	tnz	(0x01, sp)
	jrmi	00121$
	ldw	y, x
	ld	a, #0x08
	div	y, a
	addw	y, #(_d_bits+0)
	ld	a, (y)
	ld	yl, a
	ld	a, xl
	and	a, #0x07
	jreq	00228$
00227$:
	exg	a, yl
	srl	a
	exg	a, yl
	dec	a
	jrne	00227$
00228$:
	ld	a, yl
	and	a, #0x01
	cp	a, (0x01, sp)
	jreq	00121$
	inc	(0x02, sp)
00121$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1067: for (t = 0; t < NB; t++) {
	incw	x
	cpw	x, #0x00d8
	jrc	00120$
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1071: dec_info.violations = viol;
	ldw	x, #(_dec_info+13)
	ld	a, (0x02, sp)
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1072: if (viol > 0)               { dec_info.cause = CAUSE_MARKER;     return DEC_REFUSE; } /* R2 */
	tnz	(0x02, sp)
	jreq	00110$
	mov	_dec_info+1, #0x02
	clr	a
	jra	00122$
00110$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1073: if (d_infeas > GATE_INFEAS) { dec_info.cause = CAUSE_INFEASIBLE; return DEC_REFUSE; } /* R3 */
	ldw	x, _d_infeas+0
	cpw	x, #0x0004
	jrule	00112$
	mov	_dec_info+1, #0x03
	clr	a
	jra	00122$
00112$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1074: if (d_laberr > GATE_LABERR) { dec_info.cause = CAUSE_LABELERR;   return DEC_REFUSE; } /* R4 */
	ldw	x, _d_laberr+0
	cpw	x, #0x0006
	jrule	00114$
	mov	_dec_info+1, #0x04
	clr	a
	jra	00122$
00114$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1075: dec_info.path = chase(out);                                      /* R5..R8 inside */
	ldw	x, #(_dec_info+0)
	pushw	x
	ldw	x, (0x09, sp)
	call	_chase
	popw	x
	ld	(x), a
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1076: return dec_info.path;
00122$:
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1077: }
	ldw	x, (3, sp)
	addw	sp, #8
	jp	(x)
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1079: int16_t dec_eps_centi(void)
;	-----------------------------------------
;	 function dec_eps_centi
;	-----------------------------------------
_dec_eps_centi:
	sub	sp, #4
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1084: return (int16_t)((((int32_t)K_NOM - (int32_t)dec_info.K) * 10000L)
	ldw	x, _dec_info+9
	ldw	(0x03, sp), x
	clrw	x
	ldw	(0x01, sp), x
	ldw	y, #0xcccd
	subw	y, (0x03, sp)
	ldw	x, (0x01, sp)
	jrnc	00103$
	incw	x
00103$:
	negw	x
	pushw	y
	pushw	x
	push	#0x10
	push	#0x27
	clrw	x
	pushw	x
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1085: / (int32_t)dec_info.K);
	call	__mullong
	addw	sp, #8
	ld	a, (0x04, sp)
	push	a
	ld	a, (0x04, sp)
	push	a
	clr	a
	push	a
	clr	a
	push	a
	pushw	x
	pushw	y
	call	__divslong
;	/home/alex.lucaci/Projects/RBARF/new-implementation/decode.c: 1086: }
	addw	sp, #12
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
	.area CONST
_XPOW:
	.db #0x01	; 1
	.db #0x02	; 2
	.db #0x04	; 4
	.db #0x08	; 8
	.db #0x10	; 16
	.db #0x20	; 32
	.db #0x40	; 64
	.db #0x80	; 128
	.db #0x07	; 7
	.db #0x0e	; 14
	.db #0x1c	; 28
	.db #0x38	; 56	'8'
	.db #0x70	; 112	'p'
	.db #0xe0	; 224
	.db #0xc7	; 199
	.db #0x89	; 137
	.db #0x15	; 21
	.db #0x2a	; 42
	.db #0x54	; 84	'T'
	.db #0xa8	; 168
	.db #0x57	; 87	'W'
	.db #0xae	; 174
	.db #0x5b	; 91
	.db #0xb6	; 182
	.db #0x6b	; 107	'k'
	.db #0xd6	; 214
	.db #0xab	; 171
	.db #0x51	; 81	'Q'
	.db #0xa2	; 162
	.db #0x43	; 67	'C'
	.db #0x86	; 134
	.db #0x0b	; 11
	.db #0x16	; 22
	.db #0x2c	; 44
	.db #0x58	; 88	'X'
	.db #0xb0	; 176
	.db #0x67	; 103	'g'
	.db #0xce	; 206
	.db #0x9b	; 155
	.db #0x31	; 49	'1'
	.db #0x62	; 98	'b'
	.db #0xc4	; 196
	.db #0x8f	; 143
	.db #0x19	; 25
	.db #0x32	; 50	'2'
	.db #0x64	; 100	'd'
	.db #0xc8	; 200
	.db #0x97	; 151
	.db #0x29	; 41
	.db #0x52	; 82	'R'
	.db #0xa4	; 164
	.db #0x4f	; 79	'O'
	.db #0x9e	; 158
	.db #0x3b	; 59
	.db #0x76	; 118	'v'
	.db #0xec	; 236
	.db #0xdf	; 223
	.db #0xb9	; 185
	.db #0x75	; 117	'u'
	.db #0xea	; 234
	.db #0xd3	; 211
	.db #0xa1	; 161
	.db #0x45	; 69	'E'
	.db #0x8a	; 138
	.db #0x13	; 19
	.db #0x26	; 38
	.db #0x4c	; 76	'L'
	.db #0x98	; 152
	.db #0x37	; 55	'7'
	.db #0x6e	; 110	'n'
	.db #0xdc	; 220
	.db #0xbf	; 191
	.db #0x79	; 121	'y'
	.db #0xf2	; 242
	.db #0xe3	; 227
	.db #0xc1	; 193
	.db #0x85	; 133
	.db #0x0d	; 13
	.db #0x1a	; 26
	.db #0x34	; 52	'4'
	.db #0x68	; 104	'h'
	.db #0xd0	; 208
	.db #0xa7	; 167
	.db #0x49	; 73	'I'
	.db #0x92	; 146
	.db #0x23	; 35
	.db #0x46	; 70	'F'
	.db #0x8c	; 140
	.db #0x1f	; 31
	.db #0x3e	; 62
	.db #0x7c	; 124
	.db #0xf8	; 248
	.db #0xf7	; 247
	.db #0xe9	; 233
	.db #0xd5	; 213
	.db #0xad	; 173
	.db #0x5d	; 93
	.db #0xba	; 186
	.db #0x73	; 115	's'
	.db #0xe6	; 230
	.db #0xcb	; 203
	.db #0x91	; 145
	.db #0x25	; 37
	.db #0x4a	; 74	'J'
	.db #0x94	; 148
	.db #0x2f	; 47
	.db #0x5e	; 94
	.db #0xbc	; 188
	.db #0x7f	; 127
	.db #0xfe	; 254
	.db #0xfb	; 251
	.db #0xf1	; 241
	.db #0xe5	; 229
	.db #0xcd	; 205
	.db #0x9d	; 157
	.db #0x3d	; 61
	.db #0x7a	; 122	'z'
	.db #0xf4	; 244
	.db #0xef	; 239
	.db #0xd9	; 217
	.db #0xb5	; 181
	.db #0x6d	; 109	'm'
	.db #0xda	; 218
	.db #0xb3	; 179
	.db #0x61	; 97	'a'
	.db #0xc2	; 194
	.db #0x83	; 131
	.area CODE
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
	.area INITIALIZER
	.area CABS (ABS)
