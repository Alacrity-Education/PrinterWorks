# marker-split study — bulk raw rows removed (housekeeping 2026-09-08)

The three raw row dumps written by `marker_split_study.py`

    marker_split_results.jsonl.gz    2 270 529 B   the 3 candidate splits
    marker_split_controls.jsonl.gz   5 307 652 B   4 diagnostic controls
    marker_split_drift.jsonl.gz      1 161 136 B   within-capture drift sub-sweep
                                     ---------
                                     8 739 317 B

were **deleted**. They were bulk intermediates, not evidence:

* no document and no script referenced them (only `analyze_marker_split.py`
  reads them, and only to produce the report that is kept);
* the study is **purely synthetic and deterministic** — its own header says
  "STUDY ONLY ... No bench, no simulator, no firmware". It replays
  `recon/synth.py`'s calibrated sampler through `embedded_v2.py`'s lock
  stage, so every row is reproducible from files still in the tree;
* the decision output they support is retained verbatim in
  `marker_split_report.txt` (all 200 880 runs summarised).

**Reproduce the raw rows:**

    cd recon/approaches/dev_prod
    python3 marker_split_study.py          # rewrites the three .jsonl(.gz)
    python3 analyze_marker_split.py        # reprints marker_split_report.txt

Nothing else in the tree changed. The chosen split (owner decision
`FF AA 65` / `9A 00 FF`, PROTOCOL.md) is unaffected.
