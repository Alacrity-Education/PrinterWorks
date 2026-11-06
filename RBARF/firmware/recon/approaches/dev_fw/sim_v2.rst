                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module sim_v2
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _main
                                     11 	.globl _ws_decode_ex
                                     12 	.globl _g_out
                                     13 	.globl _g_status
                                     14 ;--------------------------------------------------------
                                     15 ; ram data
                                     16 ;--------------------------------------------------------
                                     17 	.area DATA
      00013B                         18 _g_status::
      00013B                         19 	.ds 1
      00013C                         20 _g_out::
      00013C                         21 	.ds 16
                                     22 ;--------------------------------------------------------
                                     23 ; ram data
                                     24 ;--------------------------------------------------------
                                     25 	.area INITIALIZED
                                     26 ;--------------------------------------------------------
                                     27 ; Stack segment in internal ram
                                     28 ;--------------------------------------------------------
                                     29 	.area SSEG
      009BB0                         30 __start__stack:
      009BB0                         31 	.ds	1
                                     32 
                                     33 ;--------------------------------------------------------
                                     34 ; absolute external ram data
                                     35 ;--------------------------------------------------------
                                     36 	.area DABS (ABS)
                                     37 
                                     38 ; default segment ordering for linker
                                     39 	.area HOME
                                     40 	.area GSINIT
                                     41 	.area GSFINAL
                                     42 	.area CONST
                                     43 	.area INITIALIZER
                                     44 	.area CODE
                                     45 
                                     46 ;--------------------------------------------------------
                                     47 ; interrupt vector
                                     48 ;--------------------------------------------------------
                                     49 	.area HOME
      008000                         50 __interrupt_vect:
      008000 82 00 80 07             51 	int s_GSINIT ; reset
                                     52 ;--------------------------------------------------------
                                     53 ; global & static initialisations
                                     54 ;--------------------------------------------------------
                                     55 	.area HOME
                                     56 	.area GSINIT
                                     57 	.area GSFINAL
                                     58 	.area GSINIT
      008007 CD 9B 27         [ 4]   59 	call	___sdcc_external_startup
      00800A 4D               [ 1]   60 	tnz	a
      00800B 27 03            [ 1]   61 	jreq	__sdcc_init_data
      00800D CC 80 04         [ 2]   62 	jp	__sdcc_program_startup
      008010                         63 __sdcc_init_data:
                                     64 ; stm8_genXINIT() start
      008010 AE 01 62         [ 2]   65 	ldw x, #l_DATA
      008013 27 07            [ 1]   66 	jreq	00002$
      008015                         67 00001$:
      008015 72 4F 00 00      [ 1]   68 	clr (s_DATA - 1, x)
      008019 5A               [ 2]   69 	decw x
      00801A 26 F9            [ 1]   70 	jrne	00001$
      00801C                         71 00002$:
      00801C AE 00 00         [ 2]   72 	ldw	x, #l_INITIALIZER
      00801F 27 09            [ 1]   73 	jreq	00004$
      008021                         74 00003$:
      008021 D6 81 36         [ 1]   75 	ld	a, (s_INITIALIZER - 1, x)
      008024 D7 01 62         [ 1]   76 	ld	(s_INITIALIZED - 1, x), a
      008027 5A               [ 2]   77 	decw	x
      008028 26 F7            [ 1]   78 	jrne	00003$
      00802A                         79 00004$:
                                     80 ; stm8_genXINIT() end
                                     81 	.area GSFINAL
      00802A CC 80 04         [ 2]   82 	jp	__sdcc_program_startup
                                     83 ;--------------------------------------------------------
                                     84 ; Home
                                     85 ;--------------------------------------------------------
                                     86 	.area HOME
                                     87 	.area HOME
      008004                         88 __sdcc_program_startup:
      008004 CC 96 69         [ 2]   89 	jp	_main
                                     90 ;	return from main will return to caller
                                     91 ;--------------------------------------------------------
                                     92 ; code
                                     93 ;--------------------------------------------------------
                                     94 	.area CODE
                                     95 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 19: static void sim_done(void) { __asm__("halt"); for (;;) ; }
                                     96 ;	-----------------------------------------
                                     97 ;	 function sim_done
                                     98 ;	-----------------------------------------
      009665                         99 _sim_done:
      009665 8E               [10]  100 	halt
      009666                        101 00103$:
      009666 20 FE            [ 2]  102 	jra	00103$
      009668 81               [ 4]  103 	ret
                                    104 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 21: void main(void)
                                    105 ;	-----------------------------------------
                                    106 ;	 function main
                                    107 ;	-----------------------------------------
      009669                        108 _main:
                                    109 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 23: g_status = ws_decode_ex(CAP, CAP_LEN, g_out);
      009669 CE 80 35         [ 2]  110 	ldw	x, _CAP_LEN+0
      00966C 4B 3C            [ 1]  111 	push	#<(_g_out+0)
      00966E 4B 01            [ 1]  112 	push	#((_g_out+0) >> 8)
      009670 89               [ 2]  113 	pushw	x
      009671 AE 80 37         [ 2]  114 	ldw	x, #(_CAP+0)
      009674 CD 95 0F         [ 4]  115 	call	_ws_decode_ex
      009677 C7 01 3B         [ 1]  116 	ld	_g_status+0, a
                                    117 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 24: sim_done();
                                    118 ;	/home/alex.lucaci/Projects/RBARF/new-implementation/recon/approaches/dev_fw/sim_v2.c: 25: }
      00967A CC 96 65         [ 2]  119 	jp	_sim_done
                                    120 	.area CODE
                                    121 	.area CONST
                                    122 	.area INITIALIZER
                                    123 	.area CABS (ABS)
