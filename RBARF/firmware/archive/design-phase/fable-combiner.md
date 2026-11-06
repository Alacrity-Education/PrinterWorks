# Fable 5 combiner-agent prompt (WS2812 reconstruction)

Saved for reuse and study. This is the prompt of the **Combine** phase
agent from the `ws2812-design-combine` workflow (run `wf_6ab72430-314`):
a single Fable 5 agent that reads six technique *design documents*
(written by Opus agents) and architects + implements the combined
decoder.

## Agent configuration

| Setting | Value |
|---|---|
| model | `fable` (Claude Fable 5) |
| effort | `max` |
| label | `combine:fable-architect` |
| output | structured, schema below |

Runtime-interpolated placeholders:
- `<ROOT>` = `/home/alex.lucaci/Projects/RBARF/new-implementation/recon`
- `<SUMMARIES>` = one block per delivered design, built from each design
  agent's structured output:
  `- <name>: <one_line_summary>\n  evidence: <key_evidence>\n  role: <composition_role>`

## Prompt (verbatim template)

```
You are the architect-implementer for a WS2812 reconstruction decoder.
Six technique designs were produced by other agents; your job is to
combine them into ONE decoder that recovers bits none of the individual
techniques could recover alone.

Working directory: <ROOT>
Read, in this order:
1. <ROOT>/DATASET.md and <ROOT>/HSI_TEMPERATURE.md
2. <ROOT>/harness.py and <ROOT>/eval.py (the decode() contract and scoring)
3. ALL design documents in <ROOT>/designs/*.md — these are your primary
   inputs. Summaries:
<SUMMARIES>
4. <ROOT>/approaches/dev_calibration/fitted_model.json if it exists — a
   fitted sampler timing model (slot offsets, effective pulse widths).
5. <ROOT>/approaches/*.py — PARTIAL implementations from an aborted
   earlier run: reference material of unknown quality only; do not trust,
   do not build on them blindly.

Then ARCHITECT: decide the pipeline (e.g. calibrated time base ->
anchored scale/phase estimation -> soft pulse/gap evidence -> global
ML/DP fusion under the 192-bit + known-marker constraints), taking from
each design what it does best and writing down (in a header comment) what
you took and what you rejected, with reasons.

IMPLEMENT <ROOT>/approaches/combined.py:
  def decode(samples: list[tuple[int,int,int]], meta: dict) -> bytes | None
Python stdlib (numpy allowed if importable), deterministic, no ground
truth reads. Iterate against:
  cd <ROOT> && python3 eval.py approaches/combined.py          (train)
Debug with scratch scripts in <ROOT>/approaches/dev_combined/. When train
is maxed (goal: 36/36), run each ONCE and report truthfully:
  python3 eval.py approaches/combined.py --holdout
  python3 eval.py approaches/combined.py --all
  python3 eval_envelope.py approaches/combined.py   (temperature envelope;
    if synth.py still uses the uncalibrated model, note that caveat)
RULES: do not modify harness.py, eval.py, eval_envelope.py, synth.py,
DATASET.md, designs/*, or the dataset. Not a git repo.
```

## Structured-output schema

```json
{
  "type": "object",
  "properties": {
    "file": {"type": "string"},
    "architecture": {"type": "string",
      "description": "the combined pipeline and which design contributed each stage"},
    "train_exact": {"type": "integer"},
    "train_total": {"type": "integer"},
    "holdout_exact": {"type": "integer"},
    "holdout_total": {"type": "integer"},
    "all_exact": {"type": "integer"},
    "all_total": {"type": "integer"},
    "envelope_summary": {"type": "string"},
    "rejected_ideas": {"type": "string"},
    "remaining_failures": {"type": "string"}
  },
  "required": ["file", "architecture", "train_exact", "train_total",
               "holdout_exact", "holdout_total", "all_exact", "all_total",
               "envelope_summary", "rejected_ideas", "remaining_failures"]
}
```

## Design notes (why the prompt is shaped this way)

- **Designs, not code, as primary input** — six independent Opus agents
  each deliver a design document with a mandatory *Composition
  interface* section (inputs consumed, soft outputs emitted, pipeline
  position), so the combiner fuses techniques instead of picking one.
- **Read order is prescribed** — task brief and oscillator envelope
  first, contract second, designs third, so the architecture is grounded
  before any code is seen.
- **Partial prior implementations are explicitly demoted** to untrusted
  reference material, preventing anchoring on a half-finished decoder.
- **"Write down what you took and what you rejected, with reasons"**
  forces an explicit architecture record into the deliverable's header.
- **Truthful-reporting framing + a separate adversarial audit phase**
  (another agent re-runs every score and reads the code for ground-truth
  cheating) keeps the reported numbers honest.
- **Holdout and temperature-envelope runs are "run ONCE at the end"** to
  avoid overfitting to the held-out reps or the synthetic sweep.

Full workflow script (all three phases):
`~/.claude/projects/-home-alex-lucaci-Projects-RBARF-new-implementation-recon/bf44f603-059d-4dee-b7ee-55d68a948043/workflows/scripts/ws2812-design-combine-wf_6ab72430-314.js`
