                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module nodec
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _ws_decode
                                     11 	.globl _g_phases
                                     12 ;--------------------------------------------------------
                                     13 ; ram data
                                     14 ;--------------------------------------------------------
                                     15 	.area DATA
      000132                         16 _g_phases::
      000132                         17 	.ds 1
                                     18 ;--------------------------------------------------------
                                     19 ; ram data
                                     20 ;--------------------------------------------------------
                                     21 	.area INITIALIZED
                                     22 ;--------------------------------------------------------
                                     23 ; absolute external ram data
                                     24 ;--------------------------------------------------------
                                     25 	.area DABS (ABS)
                                     26 
                                     27 ; default segment ordering for linker
                                     28 	.area HOME
                                     29 	.area GSINIT
                                     30 	.area GSFINAL
                                     31 	.area CONST
                                     32 	.area INITIALIZER
                                     33 	.area CODE
                                     34 
                                     35 ;--------------------------------------------------------
                                     36 ; global & static initialisations
                                     37 ;--------------------------------------------------------
                                     38 	.area HOME
                                     39 	.area GSINIT
                                     40 	.area GSFINAL
                                     41 	.area GSINIT
                                     42 ;--------------------------------------------------------
                                     43 ; Home
                                     44 ;--------------------------------------------------------
                                     45 	.area HOME
                                     46 	.area HOME
                                     47 ;--------------------------------------------------------
                                     48 ; code
                                     49 ;--------------------------------------------------------
                                     50 	.area CODE
                                     51 ;	nodec.c: 3: uint8_t ws_decode(const uint8_t *cap, uint16_t ncap, uint8_t *out)
                                     52 ;	-----------------------------------------
                                     53 ;	 function ws_decode
                                     54 ;	-----------------------------------------
      00816A                         55 _ws_decode:
                                     56 ;	nodec.c: 4: { (void)cap; (void)ncap; (void)out; return 0; }
      00816A 4F               [ 1]   57 	clr	a
      00816B 1E 01            [ 2]   58 	ldw	x, (1, sp)
      00816D 5B 06            [ 2]   59 	addw	sp, #6
      00816F FC               [ 2]   60 	jp	(x)
                                     61 	.area CODE
                                     62 	.area CONST
                                     63 	.area INITIALIZER
                                     64 	.area CABS (ABS)
