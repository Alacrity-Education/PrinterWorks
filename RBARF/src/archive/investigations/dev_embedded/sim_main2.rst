                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module sim_main2
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _main
                                     11 	.globl _done
                                     12 	.globl _ws_decode
                                     13 	.globl _result
                                     14 	.globl _payload
                                     15 	.globl _cap_buf
                                     16 ;--------------------------------------------------------
                                     17 ; ram data
                                     18 ;--------------------------------------------------------
                                     19 	.area DATA
      000001                         20 _cap_buf::
      000001                         21 	.ds 256
      000101                         22 _payload::
      000101                         23 	.ds 48
      000131                         24 _result::
      000131                         25 	.ds 1
                                     26 ;--------------------------------------------------------
                                     27 ; ram data
                                     28 ;--------------------------------------------------------
                                     29 	.area INITIALIZED
                                     30 ;--------------------------------------------------------
                                     31 ; Stack segment in internal ram
                                     32 ;--------------------------------------------------------
                                     33 	.area SSEG
      00030F                         34 __start__stack:
      00030F                         35 	.ds	1
                                     36 
                                     37 ;--------------------------------------------------------
                                     38 ; absolute external ram data
                                     39 ;--------------------------------------------------------
                                     40 	.area DABS (ABS)
                                     41 
                                     42 ; default segment ordering for linker
                                     43 	.area HOME
                                     44 	.area GSINIT
                                     45 	.area GSFINAL
                                     46 	.area CONST
                                     47 	.area INITIALIZER
                                     48 	.area CODE
                                     49 
                                     50 ;--------------------------------------------------------
                                     51 ; interrupt vector
                                     52 ;--------------------------------------------------------
                                     53 	.area HOME
      008000                         54 __interrupt_vect:
      008000 82 00 80 07             55 	int s_GSINIT ; reset
                                     56 ;--------------------------------------------------------
                                     57 ; global & static initialisations
                                     58 ;--------------------------------------------------------
                                     59 	.area HOME
                                     60 	.area GSINIT
                                     61 	.area GSFINAL
                                     62 	.area GSINIT
      008007 CD 9F 04         [ 4]   63 	call	___sdcc_external_startup
      00800A 4D               [ 1]   64 	tnz	a
      00800B 27 03            [ 1]   65 	jreq	__sdcc_init_data
      00800D CC 80 04         [ 2]   66 	jp	__sdcc_program_startup
      008010                         67 __sdcc_init_data:
                                     68 ; stm8_genXINIT() start
      008010 AE 03 0D         [ 2]   69 	ldw x, #l_DATA
      008013 27 07            [ 1]   70 	jreq	00002$
      008015                         71 00001$:
      008015 72 4F 00 00      [ 1]   72 	clr (s_DATA - 1, x)
      008019 5A               [ 2]   73 	decw x
      00801A 26 F9            [ 1]   74 	jrne	00001$
      00801C                         75 00002$:
      00801C AE 00 01         [ 2]   76 	ldw	x, #l_INITIALIZER
      00801F 27 09            [ 1]   77 	jreq	00004$
      008021                         78 00003$:
      008021 D6 81 54         [ 1]   79 	ld	a, (s_INITIALIZER - 1, x)
      008024 D7 03 0D         [ 1]   80 	ld	(s_INITIALIZED - 1, x), a
      008027 5A               [ 2]   81 	decw	x
      008028 26 F7            [ 1]   82 	jrne	00003$
      00802A                         83 00004$:
                                     84 ; stm8_genXINIT() end
                                     85 	.area GSFINAL
      00802A CC 80 04         [ 2]   86 	jp	__sdcc_program_startup
                                     87 ;--------------------------------------------------------
                                     88 ; Home
                                     89 ;--------------------------------------------------------
                                     90 	.area HOME
                                     91 	.area HOME
      008004                         92 __sdcc_program_startup:
      008004 CC 81 5A         [ 2]   93 	jp	_main
                                     94 ;	return from main will return to caller
                                     95 ;--------------------------------------------------------
                                     96 ; code
                                     97 ;--------------------------------------------------------
                                     98 	.area CODE
                                     99 ;	sim_main2.c: 8: void done(void) { __asm__("halt"); for (;;) ; }
                                    100 ;	-----------------------------------------
                                    101 ;	 function done
                                    102 ;	-----------------------------------------
      008156                        103 _done:
      008156 8E               [10]  104 	halt
      008157                        105 00103$:
      008157 20 FE            [ 2]  106 	jra	00103$
      008159 81               [ 4]  107 	ret
                                    108 ;	sim_main2.c: 9: void main(void)
                                    109 ;	-----------------------------------------
                                    110 ;	 function main
                                    111 ;	-----------------------------------------
      00815A                        112 _main:
      00815A 52 04            [ 2]  113 	sub	sp, #4
                                    114 ;	sim_main2.c: 12: for (i = 0; i < 256; i++) cap_buf[i] = test_cap[i];
      00815C 90 AE 00 01      [ 2]  115 	ldw	y, #_cap_buf+0
      008160 5F               [ 1]  116 	clrw	x
      008161 1F 03            [ 2]  117 	ldw	(0x03, sp), x
      008163                        118 00102$:
      008163 93               [ 1]  119 	ldw	x, y
      008164 72 FB 03         [ 2]  120 	addw	x, (0x03, sp)
      008167 1F 01            [ 2]  121 	ldw	(0x01, sp), x
      008169 1E 03            [ 2]  122 	ldw	x, (0x03, sp)
      00816B D6 80 55         [ 1]  123 	ld	a, (_test_cap+0, x)
      00816E 1E 01            [ 2]  124 	ldw	x, (0x01, sp)
      008170 F7               [ 1]  125 	ld	(x), a
      008171 1E 03            [ 2]  126 	ldw	x, (0x03, sp)
      008173 5C               [ 1]  127 	incw	x
      008174 1F 03            [ 2]  128 	ldw	(0x03, sp), x
      008176 A3 01 00         [ 2]  129 	cpw	x, #0x0100
      008179 25 E8            [ 1]  130 	jrc	00102$
                                    131 ;	sim_main2.c: 13: g_phases = PHASES;
      00817B 35 05 03 0E      [ 1]  132 	mov	_g_phases+0, #0x05
                                    133 ;	sim_main2.c: 14: result = ws_decode(cap_buf, 256, payload);
      00817F 93               [ 1]  134 	ldw	x, y
      008180 4B 01            [ 1]  135 	push	#<(_payload+0)
      008182 4B 01            [ 1]  136 	push	#((_payload+0) >> 8)
      008184 4B 00            [ 1]  137 	push	#0x00
      008186 4B 01            [ 1]  138 	push	#0x01
      008188 CD 9D 26         [ 4]  139 	call	_ws_decode
      00818B C7 01 31         [ 1]  140 	ld	_result+0, a
                                    141 ;	sim_main2.c: 15: done();
      00818E 5B 04            [ 2]  142 	addw	sp, #4
                                    143 ;	sim_main2.c: 16: }
      008190 CC 81 56         [ 2]  144 	jp	_done
                                    145 	.area CODE
                                    146 	.area CONST
                                    147 	.area INITIALIZER
                                    148 	.area CABS (ABS)
