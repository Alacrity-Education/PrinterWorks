# RBARF -- STM8S001J3 WS2812 receiver.  Build, verify, flash.
#
#   make            same as `make all`
#   make all        every SHIPPING image (capture + both production images
#                   + the hello bring-up image).  No bench/optional target
#                   is in here, so `make all` cannot fail on one.
#   make verify     the whole hardware-free proof suite (see `verify:`)
#   make help       every target, one line each
#   make clean      delete build/ -- and nothing else
#
# The three ledger images MUST rebuild byte-identically:
#   build/rbarf_prod.ihx          b8f0ae06e740e0f811ff3ebcb0a201ab
#   build/rbarf_prod_verbose.ihx  5524ce94f4ae3cb404503beccb0b9373
#   build/capture.ihx             84955f771ef8ad41a36fc16187afca38
# with the PINNED toolchain (sdcc 4.6.0 / sdasstm8 + sdld V05.50.4).
# toolcheck.py enforces that and fails the build loudly on anything else;
# see README.md "Toolchain" and toolcheck.py for the escape hatch.
#
# Bench/host paths are NOT hardcoded: see rbarf_config.py
# ($RBARF_PICOTOOL_HOST, $RBARF_PROBE_PORT, $RBARF_STM8FLASH, ...).

CC      = sdcc
AS      = sdasstm8
PYTHON  = python3
CFLAGS  = -mstm8 --std-c99 --opt-code-size
BUILD   = build

# ======================================================================
# CHASE BUDGET -- the ONE source for both constants (recon/AMAX_TMAX_SWEEP.md)
# ======================================================================
#   A_MAX  admitted weak/DW candidates; ALSO the R7 admission cap.  Flip
#          sets = 1 + A_MAX + C(A_MAX,2); worst-case trials
#          A_MAX*(A_MAX+1)/2 must fit dec_info.trials (u8) -> A_MAX <= 22.
#   T_MAX  residual comparisons.  It IS the per-frame false-accept bound,
#          fa = 1-(1-2^-16)^T_MAX.  z_comps/dec_info.comps are u8 -> <= 255.
#
# The DEFAULTS ARE THE SHIPPED LEDGER VALUES, so `make all` with neither
# variable set rebuilds all three ledger images BYTE-IDENTICALLY.  The
# values reach decode.c as -DA_MAX_CFG/-DT_MAX_CFG and decode_asm.s as the
# generated chase_cfg.inc (gen_chase_cfg.py -- sdasstm8 has no -D), so the
# C and the assembly cannot drift apart.  guard_prod.py re-derives both
# from the .inc beside the map and checks the linked image against them.
A_MAX ?= 11
T_MAX ?= 131
CHASE_TAG  = A$(A_MAX)_T$(T_MAX)
CHASE_INC  = $(BUILD)/chase_cfg.inc
CHASE_DEF  = -DA_MAX_CFG=$(A_MAX) -DT_MAX_CFG=$(T_MAX)

.DEFAULT_GOAL := all

# The build directory is an ORDER-ONLY prerequisite everywhere (`| $(BUILD)`)
# so a newer directory mtime never triggers a rebuild.  Creating it is also
# where the toolchain pin is enforced for a clean build, before anything is
# compiled.
$(BUILD):
	@$(PYTHON) toolcheck.py
	@mkdir -p $(BUILD)

.PHONY: toolcheck
toolcheck:
	@$(PYTHON) toolcheck.py

# The assembler's copy of the chase budget.  gen_chase_cfg.py rewrites the
# file only when the VALUES change, so an unchanged parameter point never
# re-triggers an assembly, and a changed one always does.  FORCE (not
# .PHONY) so the recipe runs but the timestamp only moves on a real change.
$(CHASE_INC): gen_chase_cfg.py FORCE | $(BUILD)
	@$(PYTHON) gen_chase_cfg.py $(A_MAX) $(T_MAX) $(CHASE_INC)

.PHONY: FORCE
FORCE:

# ======================================================================
# SHIPPING images
# ======================================================================

SHIPPING = $(BUILD)/capture.ihx $(BUILD)/rbarf_prod.ihx \
           $(BUILD)/rbarf_prod_verbose.ihx $(BUILD)/hello.ihx

.PHONY: all
all: toolcheck $(SHIPPING)

# ---- hello: UART bring-up image (9600 8N1 on pin 8, 5 s SWIM window) --
$(BUILD)/hello.ihx: hello.c | $(BUILD)
	$(CC) $(CFLAGS) hello.c -o $(BUILD)/hello.ihx

# ---- capture: the CALIBRATED acquisition image (ledger 84955f77...) ---
# cap_code.s is assembled straight into build/ (-o), so nothing is written
# beside the sources and nothing has to be moved afterwards.
$(BUILD)/cap_code.rel: cap_code.s | $(BUILD)
	$(AS) -plosg -o $(BUILD)/cap_code.rel cap_code.s

$(BUILD)/capture.ihx: capture.c $(BUILD)/cap_code.rel | $(BUILD)
	@$(PYTHON) toolcheck.py --quiet
	$(CC) $(CFLAGS) capture.c $(BUILD)/cap_code.rel -o $(BUILD)/capture.ihx

# ---- PRODUCTION image (rbarf_prod.c + decoder + app) ------------------
# ND_DATA=48, CHK_LEN=6 (60-byte v2.3 frames = exactly 20 WS2812 LEDs),
# CAP_BYTES=288 (spec SS3; still >= the 480-bit frame at the +8% HSI
# corner), armed capture with timeout (cap_arm.s, production-only
# module), TIM4 millis, 25 Hz render (RENDER_MS=40), terse UART.  VERBOSE=1 builds the
# bench-verification variant (full 96-hex data line after every verified
# decode).
# guard_prod.py enforces the capture-loop address-phase pinning and the
# REL/ABS no-overlap rule for THIS link (sdld checks neither).
# --data-loc 0xF3: decode_asm.s keeps its state in an ABS zero-page block
# (DZP, 0x0001..) so every access uses the short 1-byte-address forms;
# REL DATA must start above it (guard_prod.py checks).
PRODFLAGS = -DND_DATA=48 -DCHECK_EN=1 -DCHK_LEN=6 -DUSE_ASM_SCAN=1 -DUSE_ASM_DEC=1 \
	$(CHASE_DEF) \
	--max-allocs-per-node 100000 --data-loc 0xF3 --code-loc 0x8068 -I. -Iapp

$(BUILD)/decode_asm.rel: decode_asm.s $(CHASE_INC) | $(BUILD)
	$(AS) -plosg -I$(BUILD) -o $(BUILD)/decode_asm.rel decode_asm.s

$(BUILD)/cap_arm.rel: cap_arm.s | $(BUILD)
	$(AS) -plosg -o $(BUILD)/cap_arm.rel cap_arm.s

$(BUILD)/vectors_prod.rel: vectors_prod.s | $(BUILD)
	$(AS) -plosg -o $(BUILD)/vectors_prod.rel vectors_prod.s

$(BUILD)/caploop.rel: caploop.s | $(BUILD)
	$(AS) -plosg -o $(BUILD)/caploop.rel caploop.s

$(BUILD)/tick.rel: app/tick.c app/ws2812_in.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/tick.c -o $(BUILD)/tick.rel

$(BUILD)/decode_prod.rel: decode.c decode.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -c decode.c -o $(BUILD)/decode_prod.rel

$(BUILD)/anim.rel: app/anim.c app/anim.h app/ws2812_in.h app/ws2812_out.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/anim.c -o $(BUILD)/anim.rel

$(BUILD)/ws2812_out.rel: app/ws2812_out.c app/ws2812_out.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/ws2812_out.c -o $(BUILD)/ws2812_out.rel

$(BUILD)/rbarf_prod_main.rel: rbarf_prod.c decode.h app/ws2812_in.h app/ws2812_out.h app/anim.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -c rbarf_prod.c -o $(BUILD)/rbarf_prod_main.rel

$(BUILD)/rbarf_prod_main_v.rel: rbarf_prod.c decode.h app/ws2812_in.h app/ws2812_out.h app/anim.h | $(BUILD)
	$(CC) $(CFLAGS) $(PRODFLAGS) -DVERBOSE=1 -c rbarf_prod.c -o $(BUILD)/rbarf_prod_main_v.rel

PROD_RELS = $(BUILD)/decode_prod.rel $(BUILD)/decode_asm.rel $(BUILD)/caploop.rel \
	$(BUILD)/cap_arm.rel $(BUILD)/anim.rel $(BUILD)/ws2812_out.rel $(BUILD)/tick.rel \
	$(BUILD)/vectors_prod.rel

$(BUILD)/rbarf_prod.ihx: $(BUILD)/rbarf_prod_main.rel $(PROD_RELS) | $(BUILD)
	@$(PYTHON) toolcheck.py --quiet
	$(CC) $(CFLAGS) $(PRODFLAGS) -o $(BUILD)/rbarf_prod.ihx \
		$(BUILD)/rbarf_prod_main.rel $(PROD_RELS)
	@$(PYTHON) guard_prod.py $(BUILD)/rbarf_prod.map

$(BUILD)/rbarf_prod_verbose.ihx: $(BUILD)/rbarf_prod_main_v.rel $(PROD_RELS) | $(BUILD)
	@$(PYTHON) toolcheck.py --quiet
	$(CC) $(CFLAGS) $(PRODFLAGS) -o $(BUILD)/rbarf_prod_verbose.ihx \
		$(BUILD)/rbarf_prod_main_v.rel $(PROD_RELS)
	@$(PYTHON) guard_prod.py $(BUILD)/rbarf_prod_verbose.map

# ======================================================================
# CHASE-BUDGET BENCH IMAGES -- recon/AMAX_TMAX_SWEEP.md
# ======================================================================
# One VERBOSE image per (A_MAX, T_MAX) point, each with its own object
# directory so a parameter change can never link a stale .rel:
#
#   make amax-verbose A_MAX=16 T_MAX=192
#       -> build/rbarf_prod_verbose_A16_T192.ihx  (+ .map, guard-checked)
#   make amax-bench           # the baseline + both chosen points, then md5
#
# VERBOSE because bench/suite_singleshot.py needs the `V:` line to
# BYTE-verify a delivered frame; the suite itself is the acceptance metric
# and is never edited.  A_MAX=11 T_MAX=131 reproduces the ledger verbose
# image bit-for-bit (proved by `amax-bench`'s md5 line).
CHASE_OBJ = $(BUILD)/obj_$(CHASE_TAG)
AMAX_IHX  = $(BUILD)/rbarf_prod_verbose_$(CHASE_TAG).ihx
AMAX_RELS = $(CHASE_OBJ)/decode_prod.rel $(CHASE_OBJ)/decode_asm.rel \
	$(CHASE_OBJ)/caploop.rel $(CHASE_OBJ)/cap_arm.rel \
	$(CHASE_OBJ)/anim.rel $(CHASE_OBJ)/ws2812_out.rel \
	$(CHASE_OBJ)/tick.rel $(CHASE_OBJ)/vectors_prod.rel

.PHONY: amax-verbose
amax-verbose: | $(BUILD)
	@$(PYTHON) toolcheck.py --quiet
	@mkdir -p $(CHASE_OBJ)
	@$(PYTHON) gen_chase_cfg.py $(A_MAX) $(T_MAX) $(CHASE_OBJ)/chase_cfg.inc
	$(AS) -plosg -I$(CHASE_OBJ) -o $(CHASE_OBJ)/decode_asm.rel decode_asm.s
	$(AS) -plosg -o $(CHASE_OBJ)/cap_arm.rel cap_arm.s
	$(AS) -plosg -o $(CHASE_OBJ)/caploop.rel caploop.s
	$(AS) -plosg -o $(CHASE_OBJ)/vectors_prod.rel vectors_prod.s
	$(CC) $(CFLAGS) $(PRODFLAGS) -c decode.c -o $(CHASE_OBJ)/decode_prod.rel
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/anim.c -o $(CHASE_OBJ)/anim.rel
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/ws2812_out.c -o $(CHASE_OBJ)/ws2812_out.rel
	$(CC) $(CFLAGS) $(PRODFLAGS) -c app/tick.c -o $(CHASE_OBJ)/tick.rel
	$(CC) $(CFLAGS) $(PRODFLAGS) -DVERBOSE=1 -c rbarf_prod.c \
		-o $(CHASE_OBJ)/rbarf_prod_main_v.rel
	$(CC) $(CFLAGS) $(PRODFLAGS) -o $(AMAX_IHX) \
		$(CHASE_OBJ)/rbarf_prod_main_v.rel $(AMAX_RELS)
	@$(PYTHON) guard_prod.py $(BUILD)/rbarf_prod_verbose_$(CHASE_TAG).map \
		$(CHASE_OBJ)/chase_cfg.inc

# The three reproducible bench images: baseline, MODERATE, AGGRESSIVE.
# Recorded md5s (recon/AMAX_TMAX_SWEEP.md SS6), sdcc 4.6.0 / sdasstm8 +
# sdld V05.50.4, clean tree:
#   A11_T131 (baseline)   5524ce94f4ae3cb404503beccb0b9373
#                         == the LEDGER verbose image, byte-identical
#   A14_T131 (MODERATE)   952c7446d8e26426c8426792fd56361f
#   A16_T192 (AGGRESSIVE) d8db7f4a27d521026c5b41679b2f2b8e
# These are BENCH images (VERBOSE), not shipping images: they are NOT in
# `all`, NOT in LEDGER_MD5 and NOT in `verify`.
AMAX_POINTS = 11:131 14:131 16:192
AMAX_LEDGER_MD5 = 5524ce94f4ae3cb404503beccb0b9373  $(BUILD)/rbarf_prod_verbose_A11_T131.ihx\n952c7446d8e26426c8426792fd56361f  $(BUILD)/rbarf_prod_verbose_A14_T131.ihx\nd8db7f4a27d521026c5b41679b2f2b8e  $(BUILD)/rbarf_prod_verbose_A16_T192.ihx

.PHONY: amax-bench
amax-bench:
	@for p in $(AMAX_POINTS); do \
		a=$${p%%:*}; t=$${p##*:}; \
		$(MAKE) --no-print-directory amax-verbose A_MAX=$$a T_MAX=$$t \
			|| exit 1; \
	done
	@echo "== chase-budget bench images ================================="
	@for p in $(AMAX_POINTS); do \
		a=$${p%%:*}; t=$${p##*:}; \
		md5sum $(BUILD)/rbarf_prod_verbose_A$${a}_T$${t}.ihx; \
	done
	@printf '$(AMAX_LEDGER_MD5)\n' | md5sum --check --strict -
	@echo "(A11_T131 must equal the ledger verbose image 5524ce94... --"
	@echo " the byte-identity proof for the parameterisation)"
	@cmp $(BUILD)/rbarf_prod_verbose_A11_T131.ihx \
		$(BUILD)/rbarf_prod_verbose.ihx \
		&& echo "A11_T131 == build/rbarf_prod_verbose.ihx: BYTE-IDENTICAL"

.PHONY: rbarf-prod
rbarf-prod: $(BUILD)/rbarf_prod.ihx $(BUILD)/rbarf_prod_verbose.ihx
	@echo "=== flash area map ($(BUILD)/rbarf_prod.map) ==="
	@grep -E "^(CODE|CONST|DATA|GSINIT|GSFINAL|HOME|SSEG|INITIAL|VECT|CAP)" \
		$(BUILD)/rbarf_prod.map || true

# ======================================================================
# VERIFY -- the hardware-free proof suite.  No bench, no ucsim, no flash.
# ======================================================================
# Everything here runs on the host in a couple of seconds and is the one
# command a newcomer should run to confirm the tree is sound.  It FAILS
# (non-zero) on any drift, including a ledger md5 that no longer matches.
# Deliberately NOT included (slow or needs hardware):
#   bench gates/soaks     bench/drive_prod.py, bench/rate_spot.py, ...
LEDGER_MD5 = b8f0ae06e740e0f811ff3ebcb0a201ab  $(BUILD)/rbarf_prod.ihx\n5524ce94f4ae3cb404503beccb0b9373  $(BUILD)/rbarf_prod_verbose.ihx\n84955f771ef8ad41a36fc16187afca38  $(BUILD)/capture.ihx

.PHONY: verify ledger
verify: toolcheck ledger
	@echo "== [2/5] link guard, production image =========================="
	@$(PYTHON) guard_prod.py $(BUILD)/rbarf_prod.map
	@echo "== [3/5] link guard, verbose image ============================"
	@$(PYTHON) guard_prod.py $(BUILD)/rbarf_prod_verbose.map
	@echo "== [4/5] bench/crc.py self-test ================================"
	@$(PYTHON) bench/crc.py >/dev/null && echo "bench/crc.py: PASS"
	@echo "== [5/5] bench/patterns.py self-test ==========================="
	@$(PYTHON) bench/patterns.py >/dev/null && echo "bench/patterns.py: PASS"
	@echo
	@echo "VERIFY: PASS -- every check above completed and none failed."

# md5 the three ledger images and ASSERT them (used by `verify`)
ledger: $(BUILD)/rbarf_prod.ihx $(BUILD)/rbarf_prod_verbose.ihx $(BUILD)/capture.ihx
	@echo "== [1/5] ledger md5 ============================================"
	@printf '$(LEDGER_MD5)\n' | md5sum --check --strict -
	@md5sum $(BUILD)/rbarf_prod.ihx $(BUILD)/rbarf_prod_verbose.ihx \
		$(BUILD)/capture.ihx

# ======================================================================
# FLASH (needs the bench: probe + ST-LINK; see README.md)
# ======================================================================
.PHONY: flash flash-capture flash-prod flash-prod-verbose
flash: $(BUILD)/hello.ihx
	$(PYTHON) flash.py

flash-capture: $(BUILD)/capture.ihx
	$(PYTHON) flash.py --ihx $(BUILD)/capture.ihx flash-only

flash-prod: $(BUILD)/rbarf_prod.ihx
	$(PYTHON) flash.py --ihx $(BUILD)/rbarf_prod.ihx flash-only

flash-prod-verbose: $(BUILD)/rbarf_prod_verbose.ihx
	$(PYTHON) flash.py --ihx $(BUILD)/rbarf_prod_verbose.ihx flash-only

# ======================================================================
.PHONY: clean clean-pyc help
clean:
	rm -rf $(BUILD)

# __pycache__ is generated, never evidence.  Kept out of `clean` so that
# `make clean && make all` stays exactly the ledger rebuild.
clean-pyc:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

help:
	@echo "RBARF make targets"
	@echo "  all                 every shipping image (default)"
	@echo "  verify              hardware-free checks (ledger, link guards,"
	@echo "                      protocol self-tests) -- run this first"
	@echo "  ledger              md5 the three shipping images vs the ledger"
	@echo "  toolcheck           check sdcc/sdas/sdld against the pinned versions"
	@echo "  rbarf-prod          production images + flash-area map"
	@echo "  amax-verbose        one chase-budget VERBOSE bench image"
	@echo "                      (make amax-verbose A_MAX=16 T_MAX=192)"
	@echo "  amax-bench          baseline + both chosen points, with md5s"
	@echo "  clean               remove build/ (nothing else)"
	@echo "  clean-pyc           remove __pycache__ trees"
	@echo ""
	@echo " flashing (needs the bench -- see README.md):"
	@echo "  flash               hello bring-up image"
	@echo "  flash-capture       calibrated acquisition image"
	@echo "  flash-prod          production image (terse)"
	@echo "  flash-prod-verbose  production image (verbose bench build)"
