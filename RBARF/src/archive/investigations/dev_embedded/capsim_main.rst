                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module capsim_main
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _main
                                     11 	.globl _done
                                     12 	.globl _buf
                                     13 ;--------------------------------------------------------
                                     14 ; ram data
                                     15 ;--------------------------------------------------------
                                     16 	.area DATA
      000001                         17 _buf::
      000001                         18 	.ds 64
                                     19 ;--------------------------------------------------------
                                     20 ; ram data
                                     21 ;--------------------------------------------------------
                                     22 	.area INITIALIZED
                                     23 ;--------------------------------------------------------
                                     24 ; Stack segment in internal ram
                                     25 ;--------------------------------------------------------
                                     26 	.area SSEG
      000041                         27 __start__stack:
      000041                         28 	.ds	1
                                     29 
                                     30 ;--------------------------------------------------------
                                     31 ; absolute external ram data
                                     32 ;--------------------------------------------------------
                                     33 	.area DABS (ABS)
                                     34 
                                     35 ; default segment ordering for linker
                                     36 	.area HOME
                                     37 	.area GSINIT
                                     38 	.area GSFINAL
                                     39 	.area CONST
                                     40 	.area INITIALIZER
                                     41 	.area CODE
                                     42 
                                     43 ;--------------------------------------------------------
                                     44 ; interrupt vector
                                     45 ;--------------------------------------------------------
                                     46 	.area HOME
      008000                         47 __interrupt_vect:
      008000 82 00 80 07             48 	int s_GSINIT ; reset
                                     49 ;--------------------------------------------------------
                                     50 ; global & static initialisations
                                     51 ;--------------------------------------------------------
                                     52 	.area HOME
                                     53 	.area GSINIT
                                     54 	.area GSFINAL
                                     55 	.area GSINIT
      008007 CD 80 7D         [ 4]   56 	call	___sdcc_external_startup
      00800A 4D               [ 1]   57 	tnz	a
      00800B 27 03            [ 1]   58 	jreq	__sdcc_init_data
      00800D CC 80 04         [ 2]   59 	jp	__sdcc_program_startup
      008010                         60 __sdcc_init_data:
                                     61 ; stm8_genXINIT() start
      008010 AE 00 40         [ 2]   62 	ldw x, #l_DATA
      008013 27 07            [ 1]   63 	jreq	00002$
      008015                         64 00001$:
      008015 72 4F 00 00      [ 1]   65 	clr (s_DATA - 1, x)
      008019 5A               [ 2]   66 	decw x
      00801A 26 F9            [ 1]   67 	jrne	00001$
      00801C                         68 00002$:
      00801C AE 00 00         [ 2]   69 	ldw	x, #l_INITIALIZER
      00801F 27 09            [ 1]   70 	jreq	00004$
      008021                         71 00003$:
      008021 D6 80 2C         [ 1]   72 	ld	a, (s_INITIALIZER - 1, x)
      008024 D7 00 40         [ 1]   73 	ld	(s_INITIALIZED - 1, x), a
      008027 5A               [ 2]   74 	decw	x
      008028 26 F7            [ 1]   75 	jrne	00003$
      00802A                         76 00004$:
                                     77 ; stm8_genXINIT() end
                                     78 	.area GSFINAL
      00802A CC 80 04         [ 2]   79 	jp	__sdcc_program_startup
                                     80 ;--------------------------------------------------------
                                     81 ; Home
                                     82 ;--------------------------------------------------------
                                     83 	.area HOME
                                     84 	.area HOME
      008004                         85 __sdcc_program_startup:
      008004 CC 80 31         [ 2]   86 	jp	_main
                                     87 ;	return from main will return to caller
                                     88 ;--------------------------------------------------------
                                     89 ; code
                                     90 ;--------------------------------------------------------
                                     91 	.area CODE
                                     92 ;	capsim_main.c: 4: void done(void) { __asm__("halt"); for(;;); }
                                     93 ;	-----------------------------------------
                                     94 ;	 function done
                                     95 ;	-----------------------------------------
      00802D                         96 _done:
      00802D 8E               [10]   97 	halt
      00802E                         98 00103$:
      00802E 20 FE            [ 2]   99 	jra	00103$
      008030 81               [ 4]  100 	ret
                                    101 ;	capsim_main.c: 5: void main(void)
                                    102 ;	-----------------------------------------
                                    103 ;	 function main
                                    104 ;	-----------------------------------------
      008031                        105 _main:
                                    106 ;	capsim_main.c: 7: __asm__("ldw x, #_buf");
      008031 AE 00 01         [ 2]  107 	ldw	x, #_buf
                                    108 ;	capsim_main.c: 8: __asm__("call _capsim");
      008034 CD 80 3A         [ 4]  109 	call	_capsim
                                    110 ;	capsim_main.c: 9: done();
                                    111 ;	capsim_main.c: 10: }
      008037 CC 80 2D         [ 2]  112 	jp	_done
                                    113 	.area CODE
                                    114 	.area CONST
                                    115 	.area INITIALIZER
                                    116 	.area CABS (ABS)
