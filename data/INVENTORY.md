# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-07-02 | `./run_all.sh --samples 3` + `--resume` (6-model gen-5 grid, provider-default sampling, output caps 8192; config_hash `d64f7b847f91`, prompts_hash `1e34d3f487ef`) | authoritative | legacy/raw_responses_2026-07-02_030919.json | COMPLETE: 1080 responses (60 prompts x 6 models x 3 samples): gpt-5.5, gpt-5.4-mini, claude-sonnet-5, claude-haiku-4.5, gemini-3.5-flash, gemini-3.1-flash-lite. Single config vintage. Collection was interrupted once by an OpenAI budget cap (both OpenAI arms stalled at 60/180) and resumed after the cap was raised. |
| blinded_responses.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blinded_responses_2026-07-02.json | 1080 identity-stripped, shuffled responses for judging |
| blind_lookup.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blind_lookup_2026-07-02.json | 1080-entry response_id -> (model, prompt, sample) unblinding map |
| judge_scores.json | raw_output | 2026-07-03 | `ai_eval.judge --resume` (provider-default sampling; shape-validated since the 2026-07-03 repair) | authoritative | legacy/judge_scores_2026-07-03.json | COMPLETE: 6480 judgments (1080 responses x 6 judges); 25 null (all gemini-3.5-flash JSON failures, 0.39%). Four Sonnet-5 judgments originally arrived with flat guardrail/regulatory fields (ints instead of objects); they were dropped and re-judged under the new shape validation — the pre-repair snapshot is the legacy file. |
| bridge_scores.json | raw_output | 2026-07-03 | `AI_EVAL_BASE_DIR=bridge_run ai_eval.judge` (judges gpt-4o + gemini-2.5-flash at temperature 0.0, judge cap 4096 — replicating the historical judging conditions; shape-validated) | authoritative | — | Bridge-judging pass: 2160 judgments (1080 gen-5 responses x 2 legacy judges; 9 gemini nulls, 0.8%). NOT part of the six-judge panel data — a methodological side-channel that makes cross-generation comparisons judge-controlled. gpt-4o served as gpt-4o-2024-08-06, the identical snapshot used in both prior judging eras. Joins blind_lookup.json. |
| analysis_results.json | processed | 2026-07-08 | `ai_eval.analyze` (analyze_version 4, bootstrap seed 20260521) | authoritative | legacy/analysis_results_2026-07-08.json | Statistics for the six-model gen-5 dataset: 6480 judgments, 3 samples/cell, 6-judge panel. v4 adds the style-corrected self-favoritism metrics (style_deviation, net_self_premium with CIs): the raw premium confounds judge grading style with self-treatment; v4 separates them. All v3 numbers are unchanged. |
| report.html | report | 2026-07-08 | `ai_eval.report` on analysis_results.json | authoritative | legacy/report_2026-07-08.html | Self-contained interactive report over the gen-5 dataset; self-favoritism tables now show style deviation and net self-premium columns |

**Current state (2026-07-03):** the six-model gen-5 dataset is COMPLETE
and internally consistent: 1080 responses (single config
`d64f7b847f91`), 6480 judgments (25 null), v3 analysis, and report all
derive from the same collection. The complete 4.6-era judged dataset
remains preserved in legacy/ under the 2026-07-02 suffixes and supports
the cross-generation comparison (Sonnet 4 vs 4.6 under stable judges).
