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
      008095                         72 _g_NB:
      008095 00 E0                   73 	.dw #0x00e0
                                     74 	.area CODE
                                     75 	.area CONST
      008097                         76 _g_yend:
      008097 00 01 C2 A4             77 	.byte #0x00, #0x01, #0xc2, #0xa4	; 115364
                                     78 	.area CODE
                                     79 	.area CONST
      00809B                         80 _g_ymid:
      00809B 00 00 E2 00             81 	.byte #0x00, #0x00, #0xe2, #0x00	; 57856
                                     82 	.area CODE
                                     83 	.area CONST
      00809F                         84 _g_Wu11:
      00809F 0D F9 A0 00             85 	.byte #0x0d, #0xf9, #0xa0, #0x00	; 234463232
                                     86 	.area CODE
                                     87 	.area CONST
      0080A3                         88 _g_NBm32:
      0080A3 00 C0                   89 	.dw #0x00c0
                                     90 	.area CODE
                                     91 	.area CONST
      0080A5                         92 _g_PPHI:
      0080A5 00 C0                   93 	.dw #0x00c0
                                     94 	.area CODE
                                     95 	.area CONST
      0080A7                         96 _g_ND:
      0080A7 00 10                   97 	.dw #0x0010
                                     98 	.area CODE
                                     99 	.area CONST
      0080A9                        100 _g_ND8:
      0080A9 00 80                  101 	.dw #0x0080
                                    102 	.area CODE
                                    103 	.area CONST
      0080AB                        104 _g_NPP:
      0080AB 00 14                  105 	.dw #0x0014
                                    106 	.area CODE
                                    107 	.area CONST
      0080AD                        108 _g_CHK:
      0080AD 04                     109 	.db #0x04	; 4
                                    110 	.area CODE
                                    111 	.area INITIALIZER
                                    112 	.area CABS (ABS)
