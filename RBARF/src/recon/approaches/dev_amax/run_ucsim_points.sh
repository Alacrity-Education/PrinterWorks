#!/bin/sh
# On-target (ucsim) bit-exactness of the SHIPPED decode_asm.s at each
# chase-budget point, against the reference at the SAME point.
# Every child runs under `setsid timeout -k` and a pkill sweep follows.
set -e
NI=/home/alex.lucaci/Projects/RBARF/src
OUT="$1"
cd "$NI"
for pt in "" "--amax 14 --tmax 131" "--amax 16 --tmax 192"; do
  for nd in 48 16; do
    echo "=================== ND=$nd  ${pt:-default 11/131} ==================="
    setsid timeout -k 10 3000 python3 recon/approaches/dev_prod/ucsim_v23.py \
        --nd $nd $pt 2>&1 | tail -6 || echo "FAILED"
    pkill -x ucsim_stm8 2>/dev/null || true
  done
done
echo "=================== ND=48 --b0 C0  A16/T192 ==================="
setsid timeout -k 10 3000 python3 recon/approaches/dev_prod/ucsim_v23.py \
    --nd 48 --b0 C0 --amax 16 --tmax 192 2>&1 | tail -6 || echo "FAILED"
pkill -x ucsim_stm8 2>/dev/null || true
echo "strays: $(pgrep -c -x ucsim_stm8 2>/dev/null || echo 0)"
