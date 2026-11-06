#!/usr/bin/env python3
"""Generate a guarded copy of the read-only anim.c so feature-cut variants can
be compiled and measured.  The original tree is never touched: we read anim.c
and write src/anim_var.c here.

Guards (define to remove the feature):
  CUT_GAMMA    gamma LUT (1024 B CONST) + apply_gamma + its call
  CUT_AUTOSEQ  built-in spin/rain/draw tables + fill_seq_data + cases 04..09
  CUT_SEQ      all of CUT_AUTOSEQ plus anim_sequence/case 03 and its helpers
  CUT_FADE     anim_fade + case 02
  CUT_BLINK    anim_blink + case 01
"""
import os

SRC = '/home/alex.lucaci/Projects/RBARF/anim.c'
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'anim_var.c')

lines = open(SRC).read().split('\n')          # lines[0] is anim.c line 1

# (first_line, last_line, guard_expr) — 1-based, inclusive
RANGES = [
    (5,   75,  'defined(CUT_GAMMA)'),                        # comment + gamma_lut
    (77,  83,  'defined(CUT_AUTOSEQ) || defined(CUT_SEQ)'),  # seq tables
    (85,  89,  'defined(CUT_SEQ) && defined(CUT_FADE)'),     # lerp
    (91,  95,  'defined(CUT_SEQ)'),                          # get_seq_nib
    (97,  105, 'defined(CUT_SEQ)'),                          # count_seq_len
    (107, 113, 'defined(CUT_SEQ) && defined(CUT_FADE)'),     # scale_phase
    (115, 120, 'defined(CUT_AUTOSEQ) || defined(CUT_SEQ)'),  # fill_seq_data
    (122, 129, 'defined(CUT_SEQ)'),                          # add_clamp
    (137, 148, 'defined(CUT_BLINK) && defined(CUT_FADE)'),   # apply_mask
    (150, 158, 'defined(CUT_BLINK)'),                        # anim_blink
    (160, 175, 'defined(CUT_FADE)'),                         # anim_fade
    (177, 311, 'defined(CUT_SEQ)'),                          # anim_sequence
    (313, 319, 'defined(CUT_GAMMA)'),                        # apply_gamma
    (337, 337, 'defined(CUT_BLINK)'),                        # case 0x01
    (338, 338, 'defined(CUT_FADE)'),                         # case 0x02
    (339, 350, 'defined(CUT_AUTOSEQ) || defined(CUT_SEQ)'),  # cases 0x04..0x09
    (351, 351, 'defined(CUT_SEQ)'),                          # case 0x03
    (355, 355, 'defined(CUT_GAMMA)'),                        # apply_gamma() call
]

out = []
opens = {}
closes = {}
for a, b, g in RANGES:
    opens.setdefault(a, []).append(g)
    closes.setdefault(b, []).append(g)

for i, text in enumerate(lines, start=1):
    for g in opens.get(i, []):
        out.append('#if !(%s)' % g)
    out.append(text)
    for g in reversed(closes.get(i, [])):
        out.append('#endif')

open(DST, 'w').write('\n'.join(out))
print('wrote', DST, len(out), 'lines')
