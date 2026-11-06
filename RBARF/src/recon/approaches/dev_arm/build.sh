#!/bin/sh
# Build the BENCH-ONLY arm-diagnostic image against the UNMODIFIED
# production .rel set.  Mirrors the Makefile's PRODFLAGS/PROD_RELS link
# exactly; writes only into recon/approaches/dev_arm/.  Never touches
# build/rbarf_prod*.ihx.
set -e
# repo root, derived from this script's location (no hardcoded home)
R=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
D=$R/recon/approaches/dev_arm
PRODFLAGS="-DND_DATA=48 -DCHECK_EN=1 -DCHK_LEN=6 -DUSE_ASM_SCAN=1 -DUSE_ASM_DEC=1 \
 --max-allocs-per-node 100000 --data-loc 0xF0 --code-loc 0x8068 -I$R -I$R/app"
CFLAGS="-mstm8 --std-c99 --opt-code-size"
cd "$D"
sdcc $CFLAGS $PRODFLAGS -c "$D/rbarf_arm.c" -o "$D/rbarf_arm_main.rel"
sdcc $CFLAGS $PRODFLAGS -o "$D/rbarf_arm.ihx" \
  "$D/rbarf_arm_main.rel" \
  "$R/build/decode_prod.rel" "$R/build/decode_asm.rel" "$R/build/caploop.rel" \
  "$R/build/cap_arm.rel" "$R/build/anim.rel" "$R/build/ws2812_out.rel" \
  "$R/build/tick.rel" "$R/build/vectors_prod.rel"
python3 "$R/guard_prod.py" "$D/rbarf_arm.map"
python3 "$D/absmd5.py" "$D/rbarf_arm.ihx"
