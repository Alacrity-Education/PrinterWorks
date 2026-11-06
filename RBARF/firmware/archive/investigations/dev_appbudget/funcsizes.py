#!/usr/bin/env python3
"""Per-function byte sizes from an sdas .sym file: symbols in a given area are
sorted by address and differenced, the last one against the area size in the
Area Table at the end of the same file.  Works because sdas emits every
function label (static ones included) into the module symbol table.
"""
import re
import sys

SYM = re.compile(r'^\s*([0-9A-F]+)\s+(\S+)\s+([0-9A-F]{6})\s+G?R?')
AREA = re.compile(r'^\s+([0-9A-F])\s+(\S+)\s+size\s+([0-9A-F]+)\s+flags')


def parse(path):
    syms, areas = [], {}
    for line in open(path):
        m = AREA.match(line)
        if m:
            areas[m.group(1)] = (m.group(2), int(m.group(3), 16))
            continue
        m = SYM.match(line)
        if m:
            syms.append((m.group(1), m.group(2), int(m.group(3), 16)))
    return syms, areas


def main():
    for path in sys.argv[1:]:
        syms, areas = parse(path)
        print(f'\n=== {path} ===')
        for aidx, (aname, asize) in sorted(areas.items()):
            if asize == 0 or aname not in ('CODE', 'CONST', 'DATA'):
                continue
            items = sorted((a, n) for i, n, a in syms if i == aidx)
            if not items:
                continue
            print(f'-- area {aname} ({asize} B)')
            for k, (addr, name) in enumerate(items):
                end = items[k + 1][0] if k + 1 < len(items) else asize
                print(f'   {name:24s} 0x{addr:04X}  {end - addr:5d}')


if __name__ == '__main__':
    main()
