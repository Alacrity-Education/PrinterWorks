#!/bin/sh
# Build + run the anim equivalence proof (original ../anim.c vs refactored
# app/anim.c).  Usage: sh run_eq.sh [--negtest]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
RB=$(cd "$HERE/../../../.." && pwd)          # .../RBARF/src
OLD=$(cd "$RB/.." && pwd)                    # .../RBARF (original tree)

gcc -O1 -Wall -c "$OLD/anim.c" -I "$OLD" -o "$HERE/orig.o"
objcopy --redefine-sym anim_render=anim_render_ref "$HERE/orig.o"
gcc -O1 -Wall -c "$RB/app/anim.c" -I "$RB/app" -o "$HERE/new.o"
gcc -O1 -Wall "$HERE/driver.c" "$HERE/orig.o" "$HERE/new.o" -o "$HERE/eq"
"$HERE/eq" "$@"
