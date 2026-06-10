# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-05-22 | `python -m ai_eval.collect` (config.json + prompts.json, prompts_hash `1e34d3f487ef`) | authoritative | legacy/raw_responses_2026-04-04.json | 180 responses: 60 prompts x 3 models (gpt-4o, claude-sonnet-4, gemini-2.5-flash) x 1 sample, temp 0.7 |
| blinded_responses.json | processed | 2026-05-22 | `python -m ai_eval.blind` on raw_responses.json | authoritative | legacy/blinded_responses_2026-04-04.json | Model identity stripped, shuffled; judges score these |
| blind_lookup.json | processed | 2026-05-22 | `python -m ai_eval.blind` on raw_responses.json | authoritative | legacy/blind_lookup_2026-04-04.json | response_id -> model/prompt mapping for unblinding (never shown to judges) |
| judge_scores.json | raw_output | 2026-05-22 | `python -m ai_eval.judge` (rubric in judge_prompt_template.txt, temp 0.0) | authoritative | legacy/judge_scores_2026-04-04.json | 540 judgments: 180 responses x 3 judges; 29 null (judge JSON parse failures) |
| analysis_results.json | processed | 2026-05-22 | `python -m ai_eval.analyze` (analyze_version 2, bootstrap seed 20260521) | authoritative | legacy/analysis_results_2026-05-22.json | Unblinded statistics: model averages w/ bootstrap CIs, Krippendorff alpha, self-favoritism, calibration, pressure drift |
| report.html | report | 2026-05-22 | `python -m ai_eval.report` on analysis_results.json | authoritative | — | Interactive HTML report incl. manual tie-breaking interface |
