                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module decode
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _g_CHK
                                     11 	.globl _g_NPP
                                     12 	.globl _g_ND8
                                     13 	.globl _g_ND
                                     14 	.globl _g_PPHI
                                     15 	.globl _g_NBm32
                                     16 	.globl _g_Wu11
                                     17 	.globl _g_ymid
                                     18 	.globl _g_yend
                                     19 	.globl _g_NB
                                     20 	.globl _ov
                                     21 	.globl _g_tau
                                     22 	.globl _g_K
                                     23 	.globl _dec_info
                                     24 ;--------------------------------------------------------
                                     25 ; ram data
                                     26 ;--------------------------------------------------------
                                     27 	.area DATA
      000100                         28 _dec_info::
      000100                         29 	.ds 20
      000114                         30 _g_K::
      000114                         31 	.ds 2
      000116                         32 _g_tau::
      000116                         33 	.ds 2
      000118                         34 _ov::
      000118                         35 	.ds 128
                                     36 ;--------------------------------------------------------
                                     37 ; ram data
                                     38 ;--------------------------------------------------------
                                     39 	.area INITIALIZED
                                     40 ;--------------------------------------------------------
                                     41 ; absolute external ram data
                                     42 ;--------------------------------------------------------
                                     43 	.area DABS (ABS)
                                     44 
                                     45 ; default segment ordering for linker
                                     46 	.area HOME
                                     47 	.area GSINIT
                                     48 	.area GSFINAL
                                     49 	.area CONST
                                     50 	.area INITIALIZER
                                     51 	.area CODE
                                     52 
                                     53 ;--------------------------------------------------------
                                     54 ; global & static initialisations
                                     55 ;--------------------------------------------------------
                                     56 	.area HOME
                                     57 	.area GSINIT
                                     58 	.area GSFINAL
                                     59 	.area GSINIT
                                     60 ;--------------------------------------------------------
                                     61 ; Home
                                     62 ;--------------------------------------------------------
                                     63 	.area HOME
                                     64 	.area HOME
                                     65 ;--------------------------------------------------------
                                     66 ; code
                                     67 ;--------------------------------------------------------
                                     68 	.area CODE
                                     69 	.area CODE
                                     70 	.area CONST
                                     71 	.area CONST
      00802D                         72 _g_NB:
      00802D 00 D8                   73 	.dw #0x00d8
                                     74 	.area CODE
                                     75 	.area CONST
      00802F                         76 _g_yend:
      00802F 00 01 B2 A4             77 	.byte #0x00, #0x01, #0xb2, #0xa4	; 111268
                                     78 	.area CODE
                                     79 	.area CONST
      008033                         80 _g_ymid:
      008033 00 00 DA 00             81 	.byte #0x00, #0x00, #0xda, #0x00	; 55808
                                     82 	.area CODE
                                     83 	.area CONST
      008037                         84 _g_Wu11:
      008037 0D 79 A0 00             85 	.byte #0x0d, #0x79, #0xa0, #0x00	; 226074624
                                     86 	.area CODE
                                     87 	.area CONST
      00803B                         88 _g_NBm32:
      00803B 00 B8                   89 	.dw #0x00b8
                                     90 	.area CODE
                                     91 	.area CONST
      00803D                         92 _g_PPHI:
      00803D 00 B8                   93 	.dw #0x00b8
                                     94 	.area CODE
                                     95 	.area CONST
      00803F                         96 _g_ND:
      00803F 00 10                   97 	.dw #0x0010
                                     98 	.area CODE
                                     99 	.area CONST
      008041                        100 _g_ND8:
      008041 00 80                  101 	.dw #0x0080
                                    102 	.area CODE
                                    103 	.area CONST
      008043                        104 _g_NPP:
      008043 00 13                  105 	.dw #0x0013
                                    106 	.area CODE
                                    107 	.area CONST
      008045                        108 _g_CHK:
      008045 03                     109 	.db #0x03	; 3
                                    110 	.area CODE
                                    111 	.area INITIALIZER
                                    112 	.area CABS (ABS)
