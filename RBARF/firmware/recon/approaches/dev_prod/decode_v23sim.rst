                                      1 ;--------------------------------------------------------
                                      2 ; File Created by SDCC : free open source ISO C Compiler
                                      3 ; Version 4.6.0 #16555 (Linux)
                                      4 ;--------------------------------------------------------
                                      5 	.module decode
                                      6 	
                                      7 ;--------------------------------------------------------
                                      8 ; Public variables in this module
                                      9 ;--------------------------------------------------------
                                     10 	.globl _g_TRB
                                     11 	.globl _g_PPE
                                     12 	.globl _g_PPB
                                     13 	.globl _g_TIEE
                                     14 	.globl _g_ND8
                                     15 	.globl _g_PPHI
                                     16 	.globl _g_NBmHT
                                     17 	.globl _g_Wu11
                                     18 	.globl _g_ymid
                                     19 	.globl _g_yend
                                     20 	.globl _g_NB
                                     21 	.globl _ov
                                     22 	.globl _g_tau
                                     23 	.globl _g_K
                                     24 ;--------------------------------------------------------
                                     25 ; ram data
                                     26 ;--------------------------------------------------------
                                     27 	.area DATA
      0000F3                         28 _g_K::
      0000F3                         29 	.ds 2
      0000F5                         30 _g_tau::
      0000F5                         31 	.ds 2
      0000F7                         32 _ov::
      0000F7                         33 	.ds 128
                                     34 ;--------------------------------------------------------
                                     35 ; ram data
                                     36 ;--------------------------------------------------------
                                     37 	.area INITIALIZED
                                     38 ;--------------------------------------------------------
                                     39 ; absolute external ram data
                                     40 ;--------------------------------------------------------
                                     41 	.area DABS (ABS)
                                     42 
                                     43 ; default segment ordering for linker
                                     44 	.area HOME
                                     45 	.area GSINIT
                                     46 	.area GSFINAL
                                     47 	.area CONST
                                     48 	.area INITIALIZER
                                     49 	.area CODE
                                     50 
                                     51 ;--------------------------------------------------------
                                     52 ; global & static initialisations
                                     53 ;--------------------------------------------------------
                                     54 	.area HOME
                                     55 	.area GSINIT
                                     56 	.area GSFINAL
                                     57 	.area GSINIT
                                     58 ;--------------------------------------------------------
                                     59 ; Home
                                     60 ;--------------------------------------------------------
                                     61 	.area HOME
                                     62 	.area HOME
                                     63 ;--------------------------------------------------------
                                     64 ; code
                                     65 ;--------------------------------------------------------
                                     66 	.area CODE
                                     67 	.area CODE
                                     68 	.area CONST
                                     69 	.area CONST
      008095                         70 _g_NB:
      008095 01 E0                   71 	.dw #0x01e0
                                     72 	.area CODE
                                     73 	.area CONST
      008097                         74 _g_yend:
      008097 00 03 C2 A4             75 	.byte #0x00, #0x03, #0xc2, #0xa4	; 246436
                                     76 	.area CODE
                                     77 	.area CONST
      00809B                         78 _g_ymid:
      00809B 00 01 E2 00             79 	.byte #0x00, #0x01, #0xe2, #0x00	; 123392
                                     80 	.area CODE
                                     81 	.area CONST
      00809F                         82 _g_Wu11:
      00809F 1D F9 A0 00             83 	.byte #0x1d, #0xf9, #0xa0, #0x00	; 502898688
                                     84 	.area CODE
                                     85 	.area CONST
      0080A3                         86 _g_NBmHT:
      0080A3 01 C8                   87 	.dw #0x01c8
                                     88 	.area CODE
                                     89 	.area CONST
      0080A5                         90 _g_PPHI:
      0080A5 01 C8                   91 	.dw #0x01c8
                                     92 	.area CODE
                                     93 	.area CONST
      0080A7                         94 _g_ND8:
      0080A7 01 80                   95 	.dw #0x0180
                                     96 	.area CODE
                                     97 	.area CONST
      0080A9                         98 _g_TIEE:
      0080A9 01 B1                   99 	.dw #0x01b1
                                    100 	.area CODE
                                    101 	.area CONST
      0080AB                        102 _g_PPB:
      0080AB 00 3C                  103 	.dw #0x003c
                                    104 	.area CODE
                                    105 	.area CONST
      0080AD                        106 _g_PPE:
      0080AD 00 6C                  107 	.dw #0x006c
                                    108 	.area CODE
                                    109 	.area CONST
      0080AF                        110 _g_TRB:
      0080AF 00 39                  111 	.dw #0x0039
                                    112 	.area CODE
                                    113 	.area INITIALIZER
                                    114 	.area CABS (ABS)
