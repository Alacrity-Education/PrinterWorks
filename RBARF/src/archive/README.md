# archive/ — superseded and historical material

Everything in here was **moved out of the live tree on 2026-09-08** as
housekeeping. Nothing was rewritten: the files are byte-for-byte what they
were, only relocated. Nothing here is built by `make all`, and nothing here
is on any shipping path.

Every published document that cited a file in here was updated to the new
path in the same pass; the moved-path table at the bottom is the full list.

> **Absolute paths inside archived scratch.** Many of the design-phase and
> investigation scripts hardcode
> `/home/alex.lucaci/Projects/RBARF/new-implementation/...` (that tree is now
> `src/`). Those paths
> describe the **pre-archive** layout and were deliberately left alone —
> this is frozen history, and rewriting a few hundred lines of dead scratch
> would change files whose only value is being exactly what was run. The
> **live** tree has no hardcoded home directories left (see
> `../rbarf_config.py`). Expect to fix a `sys.path` line by hand if you want
> to re-run something in here.

---

## firmware-variants/ — superseded and bench-only firmware mains

| file | what it was | superseded by | builds today? |
|---|---|---|---|
| `rbarf_v21.c` | v2.1 production main: ND_DATA=16, CHK_LEN=3, CRC8 chase. The image behind the first on-silicon bench proof (`recon/PROD_CLOSURE.md` §6) | `rbarf_prod.c` — v2.2 (§11), then v2.3 / ND_DATA=48 / CHK_LEN=6 / CRC-16 (§13–§16) | **No.** `make rbarf-v21` fails the link guard: CODE ends `0x9FAD`, over the pinned capture loop at `0x9FA1`. See "why" below |
| `rbarf_v21_trim.c` | same decoder, but forces `CLK_HSITRIMR` through {6,7,0,1,2} once per decode — the step-6 miss-rate campaign (`recon/CAMPAIGN.md`) | the opportunistic auto-trim in `rbarf_prod.c`, retargeted per `recon/MARGIN_INVESTIGATION.md` | **No.** `make rbarf-v21-trim` fails the same guard (CODE ends `0x9FB9`). **This target previously had no guard at all and emitted a silently CORRUPT image**; `../guard_caploop.py` now catches it |
| `capture_trim.c` | acquisition firmware that rotates the HSI trim code 0…7 — produced `data/captures_trim.json` and `recon/TRIM_SWEEP.md` | the runtime auto-trim in `rbarf_prod.c` | **Yes** — `make capture-trim` |
| `rbarf_dbg.c` | dump-before-decode diagnostic; drove `bench/crashcap.py` during the ILLOPF hunt (`PROD_CLOSURE` §7.7) | the bug is fixed (`cap_arm.s`, §7.4); no replacement needed | compiles (never had a make target) |
| `rbarf_bc.c` + `crumb.s` | reset-surviving stage breadcrumb — the pair that localised the illegal-opcode reset to the capture path | fix landed in `cap_arm.s`; `guard_prod.py` now asserts the BTJT poll targets so the class of bug cannot return | compiles / assembles |
| `rbarf_bc_gate.c` | TIM4-gated control build for the same investigation | as above | compiles |
| `rbarf_prod_tf.c` | bench-only trim-forced production main (`-DTF_FIXED=v`, or round-robin {7,0,6,1}) — the margin investigation's operating-point sweep | conclusion folded into the auto-trim target (`recon/MARGIN_INVESTIGATION.md`) | compiles |
| `rbarf_dbg_tf.c` | dump-before-decode **+** the trim cycle: 80 real captures paired with their operating point | as above | compiles |

**Why the two v2.1 decoder targets no longer link.** They link the *current*
`decode.c`, which has since grown into the v2.3 decoder (CRC-16 chase, 3+3
markers, the wider reference cross product). Even at v2.1 geometry
(`ND_DATA=16`, `CHK_LEN=3`) it no longer fits underneath `caploop.s`'s pinned
`.org 0x9FA1`. Rebuilding a genuine v2.1 image needs a v2.1-era `decode.c`,
which this tree does not keep. **This is history, not a regression.** Do not
"fix" it by moving the capture loop: that block's flash address *phase* is
calibrated and pinned (`recon/PROD_CLOSURE.md` §2, `../guard_prod.py`).

---

## design-phase/ — the host reconstruction design phase

The seven candidate decoders, their scratch, and their design documents.
`recon/approaches/combined.py` (kept live) is the fusion of six of them and
is the artifact the README's 53/54 · 21/24 result refers to;
`recon/approaches/embedded_v2.py` (kept live) is the normative on-chip
reference that superseded the whole line.

| item | what |
|---|---|
| `baseline.py` | trivial threshold decoder — the floor everything else was measured against |
| `boundary_model.py`, `clock_stretch.py`, `edge_dp.py`, `histogram_adaptive.py`, `matched_filter.py`, `missed_zero.py` | the six designed techniques, one file each |
| `dev_boundary_model/`, `dev_clock_stretch/`, `dev_edge_dp/`, `dev_histogram_adaptive/`, `dev_matched_filter/`, `dev_missed_zero/`, `dev_combined/` | per-technique scratch: calibration fits, sweeps, diagnostics, logs |
| `designs/` | the design document per technique (`*.md`) plus its own `dev_*` scratch |
| `fable-combiner.md` | the prompt used to architect `combined.py` from the six designs |

Superseded: 2026-09-05/06, by `combined.py` and then by `embedded_v2.py` +
`decode.c` + `decode_asm.s`. Scoring harness (still live):
`python3 recon/eval.py <approach.py>` — but see the absolute-path note above.

---

## investigations/ — completed investigations whose reports are published

Each directory is the scratch behind a report that is **kept live** in
`recon/` or at the tree root. The reports are the deliverable; these are the
working files that produced their numbers.

| directory | report it backs | notes |
|---|---|---|
| `dev_appbudget/` | `../../docs/APP_BUDGET.md` | the app flash/RAM/stack measurement. `build_noopt/` and `build_optsize/` (6.3 MB of SDCC intermediates) were **deleted** — regenerate with `python3 measure.py` from `src/`. `mkvariants.py` reads the old June `anim.c` in the parent tree |
| `dev_embedded/` | `recon/EMBEDDED_FEASIBILITY.md` | the v1 integer-only C port (`decoder.c`) and its ablation battery. `decoder_16.so` / `decoder_48.so` deleted — `eval_c.py` rebuilds them with gcc |
| `dev_v2/`, `dev_v2spec/` | `recon/EMBEDDED_V2_SPEC.md` | v2 spec derivations. `dev_v2spec/EMBEDDED_V2_SPEC.rev1-superseded.md` is the spec's own superseded revision 1. The `*.pkl` files are computation caches for `numbers.py` / `guards.py` / `final.py`; regenerate with `prod_e2e.py` and `e2e_v2.py` |
| `dev_trimsweep/` | `recon/TRIM_SWEEP.md` | HSITRIMR sweep analysis |
| `dev_audit/`, `dev_harden/`, `dev_reverify/` | (no dedicated report) | decoder robustness / sensitivity / ablation probes from the hardening pass; findings were folded into `combined.py` and `EMBEDDED_V2_SPEC.md`. Cited by no document — kept because they are not regenerable |

---

## What stayed LIVE (for contrast)

These were *considered* for archiving and deliberately kept, because live
harnesses import them or a published artifacts table names them as evidence:

* `recon/approaches/dev_prod/` — the v2.3 proof harnesses (`parity_v23.py`
  is in `make verify`), the gate/soak/fuzz/Klipper JSONs.
* `recon/approaches/dev_arm/` — the arm investigation, and `absmd5.py`,
  which `make verify` uses to check the pinned CAPLOOP blocks.
* `recon/approaches/dev_fe/` — the §16 capture-front-end fix evidence (the
  **GO** verdict rests on it).
* `recon/approaches/dev_fw/` — superseded as a *proof* (`parity_host.py`
  186/186 became `parity_v23.py` 549/549) but still **shared
  infrastructure**: `ucsim_bitexact.py`, `sim_v2.c` and `vectors_sim.s` are
  imported by live `dev_prod` harnesses (`fuzz_v22.py`, `smoke48.py`,
  `stackprobe48.py`, `chase_cover.py`, `ucsim_v23.py`).
* `recon/approaches/dev_calibration/` — holds the calibration fit
  (`fitted_model.json`) that `recon/synth.py`'s sampler model comes from,
  and is cited by a dozen documents.

---

## Moved-path table

| was | is now |
|---|---|
| `rbarf_v21.c` | `archive/firmware-variants/rbarf_v21.c` |
| `rbarf_v21_trim.c` | `archive/firmware-variants/rbarf_v21_trim.c` |
| `capture_trim.c` | `archive/firmware-variants/capture_trim.c` |
| `rbarf_dbg.c` | `archive/firmware-variants/rbarf_dbg.c` |
| `rbarf_dbg_tf.c` | `archive/firmware-variants/rbarf_dbg_tf.c` |
| `rbarf_prod_tf.c` | `archive/firmware-variants/rbarf_prod_tf.c` |
| `rbarf_bc.c` | `archive/firmware-variants/rbarf_bc.c` |
| `rbarf_bc_gate.c` | `archive/firmware-variants/rbarf_bc_gate.c` |
| `crumb.s` | `archive/firmware-variants/crumb.s` |
| `recon/approaches/baseline.py` | `archive/design-phase/baseline.py` |
| `recon/approaches/boundary_model.py` | `archive/design-phase/boundary_model.py` |
| `recon/approaches/clock_stretch.py` | `archive/design-phase/clock_stretch.py` |
| `recon/approaches/edge_dp.py` | `archive/design-phase/edge_dp.py` |
| `recon/approaches/histogram_adaptive.py` | `archive/design-phase/histogram_adaptive.py` |
| `recon/approaches/matched_filter.py` | `archive/design-phase/matched_filter.py` |
| `recon/approaches/missed_zero.py` | `archive/design-phase/missed_zero.py` |
| `recon/approaches/dev_boundary_model/` | `archive/design-phase/dev_boundary_model/` |
| `recon/approaches/dev_clock_stretch/` | `archive/design-phase/dev_clock_stretch/` |
| `recon/approaches/dev_edge_dp/` | `archive/design-phase/dev_edge_dp/` |
| `recon/approaches/dev_histogram_adaptive/` | `archive/design-phase/dev_histogram_adaptive/` |
| `recon/approaches/dev_matched_filter/` | `archive/design-phase/dev_matched_filter/` |
| `recon/approaches/dev_missed_zero/` | `archive/design-phase/dev_missed_zero/` |
| `recon/approaches/dev_combined/` | `archive/design-phase/dev_combined/` |
| `recon/designs/` | `archive/design-phase/designs/` |
| `prompts/fable-combiner.md` | `archive/design-phase/fable-combiner.md` |
| `recon/approaches/dev_appbudget/` | `archive/investigations/dev_appbudget/` |
| `recon/approaches/dev_audit/` | `archive/investigations/dev_audit/` |
| `recon/approaches/dev_embedded/` | `archive/investigations/dev_embedded/` |
| `recon/approaches/dev_harden/` | `archive/investigations/dev_harden/` |
| `recon/approaches/dev_reverify/` | `archive/investigations/dev_reverify/` |
| `recon/approaches/dev_trimsweep/` | `archive/investigations/dev_trimsweep/` |
| `recon/approaches/dev_v2/` | `archive/investigations/dev_v2/` |
| `recon/approaches/dev_v2spec/` | `archive/investigations/dev_v2spec/` |

The now-empty `prompts/` directory was removed.
