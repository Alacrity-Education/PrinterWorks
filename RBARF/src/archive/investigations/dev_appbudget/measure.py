#!/usr/bin/env python3
"""Compile anim_var.c under each feature-cut combination and report the
linked-area sizes SDCC produces.  Two flag sets: the old build's exact flags
(-mstm8 --std-c99) and the same plus --opt-code-size.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')

VARIANTS = [
    ([], 'baseline (all modes + gamma)'),
    (['CUT_GAMMA'], 'no gamma LUT'),
    (['CUT_AUTOSEQ'], 'no built-in spin/rain/draw (04-09)'),
    (['CUT_SEQ', 'CUT_AUTOSEQ'], 'no sequence at all (03-09)'),
    (['CUT_BLINK'], 'no blink (01)'),
    (['CUT_FADE'], 'no fade (02)'),
    (['CUT_BLINK', 'CUT_FADE'], 'no blink + no fade'),
    (['CUT_GAMMA', 'CUT_AUTOSEQ'], 'no gamma + no built-in seq'),
    (['CUT_GAMMA', 'CUT_SEQ', 'CUT_AUTOSEQ'], 'no gamma + no sequence'),
    (['CUT_GAMMA', 'CUT_AUTOSEQ', 'CUT_BLINK'], 'no gamma + no built-in seq + no blink'),
    (['CUT_GAMMA', 'CUT_SEQ', 'CUT_AUTOSEQ', 'CUT_BLINK'],
     'fade only (+ none)'),
    (['CUT_GAMMA', 'CUT_SEQ', 'CUT_AUTOSEQ', 'CUT_FADE'],
     'blink only (+ none)'),
    (['CUT_GAMMA', 'CUT_SEQ', 'CUT_AUTOSEQ', 'CUT_BLINK', 'CUT_FADE'],
     'none only (bare passthrough)'),
]

AREA = re.compile(r'^A (\S+) size ([0-9A-F]+) ')


def areas(rel):
    out = {}
    for line in open(rel):
        m = AREA.match(line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def build(src, defines, extra, outrel):
    cmd = ['sdcc', '-mstm8', '--std-c99'] + extra
    cmd += ['-D' + d for d in defines]
    cmd += ['-c', src, '-o', outrel]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print('BUILD FAILED:', ' '.join(cmd), file=sys.stderr)
        print(r.stderr[:2000], file=sys.stderr)
        sys.exit(1)
    return areas(outrel)


def main():
    for extra, tag, bdir in ((['--opt-code-size'], '--opt-code-size',
                              os.path.join(HERE, 'build_optsize')),
                             ([], 'old flags (no --opt-code-size)',
                              os.path.join(HERE, 'build_noopt'))):
        os.makedirs(bdir, exist_ok=True)
        print(f'\n### anim.c variants, {tag}')
        print(f"{'variant':44s} {'CODE':>6s} {'CONST':>6s} {'total':>6s} {'saved':>7s}")
        base = None
        for i, (defs, label) in enumerate(VARIANTS):
            a = build(os.path.join(SRC, 'anim_var.c'), defs, extra,
                      os.path.join(bdir, f'anim_v{i}.rel'))
            tot = a.get('CODE', 0) + a.get('CONST', 0)
            if base is None:
                base = tot
            print(f"{label:44s} {a.get('CODE',0):6d} {a.get('CONST',0):6d} "
                  f"{tot:6d} {base - tot:7d}")

        print(f'\n### other app modules, {tag}')
        for mod in ('ws2812_out', 'main', 'tick'):
            p = os.path.join(SRC, mod + '.c')
            if not os.path.exists(p):
                continue
            a = build(p, [], extra, os.path.join(bdir, mod + '.rel'))
            flash = sum(a.get(k, 0) for k in
                        ('CODE', 'CONST', 'HOME', 'GSINIT', 'GSFINAL',
                         'INITIALIZER'))
            ram = a.get('DATA', 0) + a.get('INITIALIZED', 0) + a.get('SSEG', 0)
            print(f"{mod:16s} CODE {a.get('CODE',0):5d}  CONST {a.get('CONST',0):5d}  "
                  f"HOME {a.get('HOME',0):3d}  GSINIT {a.get('GSINIT',0):3d}  "
                  f"GSFINAL {a.get('GSFINAL',0):2d}  -> flash {flash:5d}  ram {ram:4d}")


if __name__ == '__main__':
    main()
