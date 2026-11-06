#!/bin/sh
set -e
# repo root, derived from this script's location (no hardcoded home)
R=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
D=$R/recon/approaches/dev_fe
PF="-DND_DATA=48 -DCHECK_EN=1 -DCHK_LEN=6 -DUSE_ASM_SCAN=1 -DUSE_ASM_DEC=1 --max-allocs-per-node 100000 --data-loc 0xF0 --code-loc 0x8068 -I$R -I$R/app"
link() {  # $1 = main.rel  $2 = cap_arm.rel  $3 = out name
  sdcc -mstm8 --std-c99 --opt-code-size $PF -o $D/$3.ihx "$1" "$2" \
    $R/build/decode_prod.rel $R/build/decode_asm.rel $R/build/caploop.rel \
    $R/build/anim.rel $R/build/ws2812_out.rel $R/build/tick.rel \
    $R/build/vectors_prod.rel
  python3 - "$D/$3.map" "$3" <<'PY'
import re,sys
m=open(sys.argv[1]).read(); end=0
for n,a,s in re.findall(r'^([A-Z_0-9]+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})',m,re.M):
    a=int(a,16); s=int(s,16)
    if n in ('HOME','GSINIT','GSFINAL','CONST','CODE','INITIALIZER') and a>=0x8000:
        end=max(end,a+s)
ca=int(re.search(r'([0-9A-F]{8})\s+_cap_arm',m).group(1),16)
print('%-14s REL end 0x%X  CAPARM 0x%X  free %d'%(sys.argv[2],end,ca,ca-end))
PY
}
link $D/base_prod.rel      $D/base_cap_arm.rel   base_base
link $D/base_prod.rel      $R/build/cap_arm.rel  base_newarm
link $R/build/rbarf_prod_main.rel $D/base_cap_arm.rel new_basearm
