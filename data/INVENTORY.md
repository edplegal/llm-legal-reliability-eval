# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-07-02 | `./run_all.sh --samples 3` + `--resume` (6-model gen-5 grid, provider-default sampling, output caps 8192; config_hash `d64f7b847f91`, prompts_hash `1e34d3f487ef`) | authoritative | legacy/raw_responses_2026-07-02_030919.json | COMPLETE: 1080 responses (60 prompts x 6 models x 3 samples): gpt-5.5, gpt-5.4-mini, claude-sonnet-5, claude-haiku-4.5, gemini-3.5-flash, gemini-3.1-flash-lite. Single config vintage. Collection was interrupted once by an OpenAI budget cap (both OpenAI arms stalled at 60/180) and resumed after the cap was raised. |
| blinded_responses.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blinded_responses_2026-07-02.json | 1080 identity-stripped, shuffled responses for judging |
| blind_lookup.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blind_lookup_2026-07-02.json | 1080-entry response_id -> (model, prompt, sample) unblinding map |
| judge_scores.json | raw_output | 2026-07-03 | `ai_eval.judge --resume` (provider-default sampling; shape-validated since the 2026-07-03 repair) | authoritative | legacy/judge_scores_2026-07-03.json | COMPLETE: 6480 judgments (1080 responses x 6 judges); 25 null (all gemini-3.5-flash JSON failures, 0.39%). Four Sonnet-5 judgments originally arrived with flat guardrail/regulatory fields (ints instead of objects); they were dropped and re-judged under the new shape validation — the pre-repair snapshot is the legacy file. |
| analysis_results.json | processed | 2026-07-03 | `ai_eval.analyze` (analyze_version 3, bootstrap seed 20260521) | authoritative | legacy/analysis_results_2026-07-03.json | Statistics for the six-model gen-5 dataset: 6480 judgments, 3 samples/cell, 6-judge panel |
| report.html | report | 2026-07-03 | `ai_eval.report` on analysis_results.json | authoritative | legacy/report_2026-07-03.html | Self-contained interactive report over the gen-5 dataset |

**Current state (2026-07-03):** the six-model gen-5 dataset is COMPLETE
and internally consistent: 1080 responses (single config
`d64f7b847f91`), 6480 judgments (25 null), v3 analysis, and report all
derive from the same collection. The complete 4.6-era judged dataset
remains preserved in legacy/ under the 2026-07-02 suffixes and supports
the cross-generation comparison (Sonnet 4 vs 4.6 under stable judges).
