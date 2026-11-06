#!/usr/bin/env python3
"""Link guard for the PRODUCTION image (extends the bench caploop guard).

sdld does not check REL/ABS overlaps, and the cycle-calibrated capture
loop is flash-address-PHASE dependent (proven on bench 2026-09-06:
+3 fetch-stall cycles exist only at the capture.ihx alignment).  This
guard fails the build unless:

  1. every REL flash area (HOME/GSINIT/GSFINAL/CONST/CODE/INITIALIZER)
     ends at or below CAPARM0's start (0x9F63 in the current link; the
     address is read from the `_cap_arm` symbol, never hardcoded) -- no
     silent overlap with the pinned blocks;
  2. _cap_capture  == 0x8111 (mod 16)  -- legacy blocking entry phase;
  3. _cap_loop     == 0x811F (mod 16)  -- the calibrated sampling loop
     itself (entered by _cap_arm at its R0 poll, _cap_loop+1);
  4. CAPARM0 does not overlap CAPLOOP1 and CAPLOOP1 ends inside flash.
     CAPARM0 is NOT flush under CAPLOOP any more: cap_arm.s FIX 4 re-phased
     CAPARM_ORG to 0x9F63 for its measured effect on the poll comb's
     fetch-stall spread, which leaves 0x9F9F..0x9FA0 unprogrammed and
     unreachable (the arm ends in `ret`);
  5. cap_arm's four edge-detect BTJT polls all target _cap_loop+1 in the
     LINKED image, that byte really is a BTJT opcode (an instruction
     boundary) and the byte at _cap_loop really is the loop-top `rlc a`
     that the +1 entry deliberately skips (ARM_INVESTIGATION.md, cap_arm.s
     FIX 2a); any other 0x72 0x06 0x50 0x0B poll in cap_arm (the idle
     gate) must branch inside cap_arm itself.
  7. CHASE BUDGET (recon/AMAX_TMAX_SWEEP.md).  A_MAX and T_MAX are
     Makefile variables now, so the guard re-derives them from the
     GENERATED chase_cfg.inc that decode_asm.s was assembled with and
     checks the LINKED image against them, instead of trusting the build:
       * T_MAX in 1..255 -- ch_comps is a u8 in decode.c, a u8 in
         decode_asm.s (z_comps) and a u8 report field in dec_info;
       * A_MAX*(A_MAX+1)/2 <= 255 -- the worst-case chase trial count has
         to fit dec_info.trials (u8), which caps A_MAX at 22;
       * _v_cand_m - _v_cand_t == 2*A_MAX in the map, i.e. the candidate
         arrays really were reserved at the configured capacity (this is
         what catches a stale decode_asm.rel linked against the old .inc);
       * the STACK REGION (0x400 - end of SSEG) stays >= MIN_STACK.  The
         candidate arrays are REL DATA, so every extra A_MAX entry costs
         3 B of DATA and takes 3 B out of the stack region: the measured
         peak is 115 B (PROD_CLOSURE SS14.2, re-measured per point with
         dev_prod/stackprobe_v23.py), and the guard refuses a link that
         leaves less than MIN_STACK.
     The .inc path is the second argument, or chase_cfg.inc beside the
     map; with neither the guard falls back to the ledger 11 / 131.

  6. _cap_arm sits EXACTLY at CAPARM_ORG_EXPECT.  The arm's address is a
     CALIBRATED TIMING QUANTITY, not a free placement choice: the mod-4
     phase of the four edge-detect polls relative to the 32-bit flash
     words sets how the comb's ~3 cy of fetch stall distribute across its
     2/2/3/4-cy gaps, hence the WIDTH of the t0 distribution.  Measured on
     silicon over all four phases (ARM_INVESTIGATION.md SS10): sd 138 ns at
     0x9F65 (mod4=1) versus 98-109 ns at the other three, and 0x9F63
     confirmed at n=134 with sd 138.3 -> 100.2 ns, F(136,133)=1.91,
     p=0.0001, median unmoved.  A silent move back to a wide phase would
     re-open the 681 ns cliff tail, so it fails the build.

Usage: guard_prod.py <mapfile> [chase_cfg.inc]
"""
import re
import sys
from pathlib import Path

REL_FLASH = ("HOME", "GSINIT", "GSFINAL", "CONST", "CODE", "INITIALIZER")

# cap_arm.s CAPARM_ORG.  Calibrated, not arbitrary -- see check 6 in the
# docstring and cap_arm.s FIX 4.  Keep the two in lockstep.
CAPARM_ORG_EXPECT = 0x9F63

# the shipped ledger chase budget (Makefile A_MAX / T_MAX defaults)
A_MAX_LEDGER, T_MAX_LEDGER = 11, 131
# STM8S001J3 RAM ends at 0x03FF; the stack grows down from there.  Peak
# decode-path depth measured at 115 B (PROD_CLOSURE SS14.2 / SS19.3), so
# 124 B is that plus a 9 B floor.  A bigger A_MAX eats this region 3 B per
# entry -- if a point needs more, it needs a RAM lever first, not a
# smaller number here.
RAM_END = 0x0400
MIN_STACK = 124
STACK_PEAK_MEASURED = 115


def read_chase_cfg(mappath, incarg=None):
    """-> (A_MAX, T_MAX, source).  The GENERATED include is authoritative;
    absent, the ledger defaults."""
    cands = []
    if incarg:
        cands.append(Path(incarg))
    cands.append(Path(mappath).resolve().parent / "chase_cfg.inc")
    for c in cands:
        try:
            txt = c.read_text()
        except OSError:
            continue
        a = re.search(r"^A_MAX_CFG\s*=\s*(\d+)", txt, re.M)
        t = re.search(r"^T_MAX_CFG\s*=\s*(\d+)", txt, re.M)
        if a and t:
            return int(a.group(1)), int(t.group(1)), str(c)
    return A_MAX_LEDGER, T_MAX_LEDGER, "defaults (no chase_cfg.inc found)"


def _load_ihx(path):
    """Parse an Intel-HEX file into {addr: byte}."""
    mem = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith(":"):
                continue
            n = int(line[1:3], 16)
            addr = int(line[3:7], 16)
            typ = int(line[7:9], 16)
            if typ == 0:
                data = bytes.fromhex(line[9:9 + 2 * n])
                for i, b in enumerate(data):
                    mem[addr + i] = b
    return mem


def main(path, incarg=None):
    m = open(path).read()
    areas = {}
    for name, addr, size in re.findall(
            r"^([A-Z_0-9]+)\s+([0-9A-F]{8})\s+([0-9A-F]{8})", m, re.M):
        areas[name] = (int(addr, 16), int(size, 16))
    syms = {}
    for addr, name in re.findall(r"([0-9A-F]{8})\s+(_cap_capture|_cap_loop|_cap_arm)\b", m):
        syms[name] = int(addr, 16)

    errs = []
    # sdld's map lists ABS areas with addr 0; anchor on the symbols and
    # take only the SIZE from the area table.
    caparm = caploop = None
    if "CAPARM0" in areas and "_cap_arm" in syms:
        caparm = (syms["_cap_arm"], areas["CAPARM0"][1])
    else:
        errs.append("CAPARM0/_cap_arm missing (cap_arm.s not linked?)")
    lp = areas.get("CAPLOOP1") or areas.get("CAPLOOP0")
    if lp and "_cap_capture" in syms:
        caploop = (syms["_cap_capture"], lp[1])
    else:
        errs.append("CAPLOOP/_cap_capture missing (scan.s not linked?)")

    rel_end = 0
    worst = None
    for name in REL_FLASH:
        if name in areas:
            a, s = areas[name]
            if a >= 0x8000 and a + s > rel_end:
                rel_end = a + s
                worst = name
    if caparm and rel_end > caparm[0]:
        errs.append("OVERLAP: %s ends 0x%X > CAPARM0 start 0x%X"
                    % (worst, rel_end, caparm[0]))

    if "_cap_capture" in syms and (syms["_cap_capture"] - 0x8111) % 16:
        errs.append("PHASE: _cap_capture 0x%X !~ 0x8111 mod 16"
                    % syms["_cap_capture"])
    if "_cap_loop" in syms and (syms["_cap_loop"] - 0x811F) % 16:
        errs.append("PHASE: _cap_loop 0x%X !~ 0x811F mod 16"
                    % syms["_cap_loop"])
    if "_cap_loop" not in syms:
        errs.append("_cap_loop symbol missing from map")
    # cap_arm.s hardcodes CL_ENT = 0x9FAF for its edge-detect BTJT bytes
    # (an sdld PCR-relocation bug corrupts the symbolic form -- see
    # cap_arm.s / PROD_CLOSURE.md SS7.4).  The hardcode is only safe while
    # _cap_loop actually sits there, so pin the EXACT address, not mod 16.
    if syms.get("_cap_loop") not in (None, 0x9FAF):
        errs.append("_cap_loop 0x%X != 0x9FAF (cap_arm BTJT_CL hardcode)"
                    % syms["_cap_loop"])
    # cap_arm's own address is calibrated (FIX 4): its mod-4 phase sets the
    # poll comb's fetch-stall spread, i.e. the width of the t0 distribution.
    if syms.get("_cap_arm") not in (None, CAPARM_ORG_EXPECT):
        errs.append("_cap_arm 0x%X != CAPARM_ORG_EXPECT 0x%X -- the arm's "
                    "address is a CALIBRATED timing quantity (cap_arm.s "
                    "FIX 4); re-phasing it changes the t0 spread and must "
                    "be re-measured on silicon, not changed silently"
                    % (syms["_cap_arm"], CAPARM_ORG_EXPECT))

    # Disassemble cap_arm's BTJT polls in the LINKED image and confirm every
    # edge-detect poll branches to the documented loop entry _cap_loop+1
    # (the R0 poll -- cap_arm.s FIX 2a skips the loop-top `rlc a`, which
    # only ever deposits the PREVIOUS iteration's BS1 and so writes byte 0
    # bits 7..6, which no consumer reads).  This is the check that would
    # have caught the shipped ILLOPF: sdld silently mis-relocated the 3rd
    # poll to 0x9FAD (mid-instruction).  The map alone cannot see it -- read
    # the .ihx that sits beside the .map.
    if "_cap_arm" in syms and "_cap_loop" in syms:
        ihx = path[:-4] + ".ihx" if path.endswith(".map") else path + ".ihx"
        try:
            mem = _load_ihx(ihx)
        except OSError:
            mem = None
        if mem is not None:
            base = syms["_cap_arm"]
            lp = syms["_cap_loop"]
            tgt = lp + 1                      # CL_R0, the documented entry
            # scan ONLY cap_arm's own bytes (below _cap_capture), else the
            # caploop wait_low btjt (also 72 06 50 0B) is miscounted
            span = (syms.get("_cap_capture", base + 0x3C) - base)
            # the entry must be an instruction boundary INSIDE the pinned
            # loop: _cap_loop = `rlc a` (0x49), _cap_loop+1 = BTJT (0x72).
            if mem.get(lp) != 0x49:
                errs.append("byte at _cap_loop 0x%X is 0x%02X, expected 0x49 "
                            "(rlc a): the +1 entry assumption is broken"
                            % (lp, mem.get(lp, 0)))
            if mem.get(tgt) != 0x72:
                errs.append("byte at _cap_loop+1 0x%X is 0x%02X, expected "
                            "0x72 (btjt): entry is not an instruction "
                            "boundary" % (tgt, mem.get(tgt, 0)))
            found = inarea = 0
            for off in range(0, max(0, span)):
                a = base + off
                if bytes(mem.get(a + i, 0) for i in range(4)) == \
                        b"\x72\x06\x50\x0b":
                    rel = mem.get(a + 4, 0)
                    rel -= 256 if rel >= 128 else 0
                    dst = a + 5 + rel
                    if dst == tgt:
                        found += 1
                    elif base <= dst < base + span:
                        inarea += 1           # idle gate: same-area branch
                    else:
                        errs.append("BTJT poll @0x%X -> 0x%X, neither "
                                    "_cap_loop+1 0x%X nor inside cap_arm "
                                    "(sdld mis-relocation)" % (a, dst, tgt))
            if found != 4:
                errs.append("expected 4 edge-detect BTJT polls -> 0x%X in "
                            "cap_arm, found %d (layout changed?)"
                            % (tgt, found))
            if inarea != 1:
                errs.append("expected 1 in-area BTJT (the idle gate) in "
                            "cap_arm, found %d (layout changed?)" % inarea)

    if caparm and caploop:
        if caparm[0] + caparm[1] > caploop[0]:
            errs.append("OVERLAP: CAPARM0 0x%X+0x%X crosses CAPLOOP 0x%X"
                        % (caparm[0], caparm[1], caploop[0]))
        if caploop[0] + caploop[1] > 0xA000:
            errs.append("CAPLOOP runs past flash end")

    # vector-gap packing: VGAP must stay inside 0x8004..0x8063 and the
    # REL flash areas must start at/above --code-loc 0x8068.  sdld banks
    # ABS areas as <name>0/<name>1... and prints their addr as 0, so the
    # start is anchored on the exported `sot` symbol (decode_asm.s).
    vgap = areas.get("VGAP1") or areas.get("VGAP0")
    if vgap:
        mvg = re.search(r"([0-9A-F]{8})\s+sot\b", m)
        if not mvg:
            errs.append("VGAP present but `sot` anchor symbol missing")
        else:
            vg_start = int(mvg.group(1), 16)
            vg_end = vg_start + vgap[1]
            if vg_start < 0x8004 or vg_end > 0x8064:
                errs.append("VGAP 0x%X..0x%X outside the TRAP..IRQ22 "
                            "window 0x8004..0x8063" % (vg_start, vg_end - 1))
        if "HOME" in areas and areas["HOME"][0] < 0x8068:
            errs.append("HOME 0x%X below --code-loc 0x8068 (vector table "
                        "would be clobbered)" % areas["HOME"][0])

    # ---- check 7: the chase budget, re-derived and checked ------------
    amax, tmax, csrc = read_chase_cfg(path, incarg)
    if not 1 <= tmax <= 255:
        errs.append("T_MAX %d outside 1..255 (%s): ch_comps and "
                    "dec_info.comps are u8" % (tmax, csrc))
    if not 2 <= amax <= 255:
        errs.append("A_MAX %d outside 2..255 (%s)" % (amax, csrc))
    elif amax * (amax + 1) // 2 > 255:
        errs.append("A_MAX %d -> %d worst-case chase trials, which "
                    "overflows the u8 dec_info.trials (max A_MAX 22)"
                    % (amax, amax * (amax + 1) // 2))
    for addr, nm in re.findall(
            r"([0-9A-F]{8})\s+(_v_cand_t|_v_cand_m)\b", m):
        syms[nm] = int(addr, 16)
    if "_v_cand_t" in syms and "_v_cand_m" in syms:
        span = syms["_v_cand_m"] - syms["_v_cand_t"]
        if span != 2 * amax:
            errs.append("_v_cand_t.._v_cand_m spans %d B but A_MAX %d "
                        "needs %d (%s): decode_asm.rel was assembled "
                        "against a DIFFERENT chase_cfg.inc"
                        % (span, amax, 2 * amax, csrc))
    else:
        errs.append("_v_cand_t/_v_cand_m missing from the map "
                    "(decode_asm.s not linked?)")
    stack = None
    if "SSEG" in areas:
        sa, ss = areas["SSEG"]
        stack = RAM_END - (sa + ss)
        if stack < MIN_STACK:
            errs.append("STACK REGION %d B < MIN_STACK %d B (SSEG ends "
                        "0x%X): the decode path peaks at %d B measured, "
                        "and the A_MAX %d candidate arrays are REL DATA "
                        "(3 B per entry).  This point needs a RAM lever, "
                        "not a smaller floor."
                        % (stack, MIN_STACK, sa + ss,
                           STACK_PEAK_MEASURED, amax))

    # zero-page asm state (DZP): REL DATA must start above it
    if "DZP0" in areas:
        dzp_end = 0x0001 + areas["DZP0"][1]
        if "DATA" in areas and areas["DATA"][0] < dzp_end:
            errs.append("OVERLAP: REL DATA 0x%X below DZP end 0x%X "
                        "(--data-loc)" % (areas["DATA"][0], dzp_end))

    if errs:
        print("PROD GUARD FAIL (%s):" % path)
        for e in errs:
            print("  " + e)
        return 1

    free = (caparm[0] - rel_end) + (0xA000 - (caploop[0] + caploop[1]))
    print("prod guard OK: REL end 0x%X <= CAPARM 0x%X; _cap_loop 0x%X "
          "phase 0x%X; flash free %d B" %
          (rel_end, caparm[0], syms["_cap_loop"], syms["_cap_loop"] % 16,
           free))
    print("   chase budget A_MAX %d T_MAX %d (%s); cand arrays %d B; "
          "worst-case trials %d; stack region %s B (peak %d measured)"
          % (amax, tmax, csrc, 3 * amax, min(amax * (amax + 1) // 2,
                                             tmax - 1),
             stack if stack is not None else "?", STACK_PEAK_MEASURED))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1],
                          sys.argv[2] if len(sys.argv) > 2 else None))
