# `dev_amax` — the `A_MAX` x `T_MAX` chase-budget sweep

Report: **`recon/AMAX_TMAX_SWEEP.md`** (every table in its §3 is rendered
by `tables.py` from the JSONs here — no number is typed by hand).
Firmware side: `gen_chase_cfg.py`, the `Makefile`'s `A_MAX`/`T_MAX`,
`guard_prod.py` check 7, `embedded_v2.set_chase_budget()`.

## Reproducing

```sh
python3 sweep_amax_tmax.py validate       # the grid-independence proof
python3 sweep_amax_tmax.py suite          # corpus (a), 16 800 captures/point
python3 sweep_amax_tmax.py real           # corpus (b), captures_v23.json
python3 sweep_amax_tmax.py wrong -n 40000 # corpus (c), measured false accepts
python3 per_payload.py 14:131 16:192      # per-payload / per-capture attribution
python3 tables.py                         # the report tables
RBARF_AGRID=11,13,14,16,18,19 RBARF_TGRID=131,160,192,224,255,262 \
  python3 sweep_amax_tmax.py suite        # the refinement grid (Table 4)
```

`data/captures_val.json` is never opened by anything here.

## Files

| file | what |
|---|---|
| `amaxlib.py` | grid, corpora parameters, reference driver, `fa_bound` / `max_trials` / `proj_ms` with their sources cited |
| `sweep_amax_tmax.py` | the three corpora + `--validate` |
| `per_payload.py` / `.log` | which payloads move, and the ONE regression (`prod/full` at A14/T131) |
| `tables.py` / `tables.md` | the report tables |
| `armdiff.py` | pinned-block proof: CAPLOOP identical, CAPARM differing in exactly the 4 `s_arm` operand bytes |
| `run_ucsim_points.sh` | the ucsim sweep driver |
| `sweep_suite.json`, `sweep_real.json`, `sweep_wrong.json` + `sweep_wrong_<stratum>.json` | the 5 x 5 grid |
| `sweep_suite_fine.json` | 6 x 6 refinement (Table 4) |
| `sweep_suite_tknee.json` | the `T_MAX` knee at `A_MAX = 16` (Table 5) |
| `sweep_wrong*_points.json` | corpus (c) restricted to the chosen points, same seed (Table 6) |
| `ucsim_*.log` | the 7 on-target (`decode_asm.s`) parity runs |
| `stack_*.log` | the sentinel/low-water stack probe, baseline and aggressive, worst-case `n_weak` |
| `suite.log`, `wrong.log`, `wrong_points.log` | raw sweep output |

## Gotchas found the hard way

* `pkill -f ucsim_stm8` matches the shell running it. Use `pkill -x`.
* Python 3.14 defaults to a **forkserver** start method on Linux, so a
  runtime-set module global is NOT inherited by pool workers — pass it in
  the task (see `per_payload.py`).
* `sdasstm8` wants `-Idir`, not `-I dir`.
* A stale `ucsim` holding the `-Z` port makes a whole run report
  "target said nothing" mismatches. `ucsim_v23.py` now retries the
  connect for 10 s and retries a dropped case up to 3 times, printing
  every retry.
