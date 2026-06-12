# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-06-12 | `./run_all.sh --samples 3` Phase 1 (config_hash `c68bd88010e0`, prompts_hash `1e34d3f487ef`) | experimental | legacy/raw_responses_2026-06-12.json | IN PROGRESS: 232/540 responses (26/60 prompts x 3 models x 3 samples); collection interrupted 2026-06-12 ~13:00, resume with `./run_all.sh --resume --samples 3` |
| blinded_responses.json | processed | 2026-05-22 | `python -m ai_eval.blind` on the 2026-05-22 raw collection | superseded | legacy/blinded_responses_2026-04-04.json | Derived from the rotated legacy/raw_responses_2026-06-12.json (the 2026-05-22 single-sample run), NOT from the in-progress raw above; regenerate after collection completes |
| blind_lookup.json | processed | 2026-05-22 | `python -m ai_eval.blind` on the 2026-05-22 raw collection | superseded | legacy/blind_lookup_2026-04-04.json | Same vintage as blinded_responses.json; pre-refactor random IDs |
| judge_scores.json | raw_output | 2026-05-22 | `python -m ai_eval.judge` (rubric in judge_prompt_template.txt, temp 0.0) | superseded | legacy/judge_scores_2026-04-04.json | 540 judgments of the 2026-05-22 responses; 29 null; will be orphaned and rotated when the 3-sample set is blinded |
| analysis_results.json | processed | 2026-05-22 | `python -m ai_eval.analyze` (analyze_version 2, bootstrap seed 20260521) | superseded | legacy/analysis_results_2026-05-22.json | Statistics for the 2026-05-22 single-sample run |
| report.html | report | 2026-05-22 | `python -m ai_eval.report` on analysis_results.json | superseded | — | Report for the 2026-05-22 single-sample run |

**Current state (2026-06-12):** a 3-sample collection is mid-flight. Until it
completes and Phases 2-5 re-run, the only artifact aligned with
raw_responses.json is raw_responses.json itself; everything else still
describes the 2026-05-22 run, whose raw file now lives at
legacy/raw_responses_2026-06-12.json.
