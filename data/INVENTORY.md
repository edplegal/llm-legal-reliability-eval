# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-07-02 | `./run_all.sh --samples 3` + `--resume` (6-model gen-5 grid, provider-default sampling, output caps 8192; config_hash `d64f7b847f91`, prompts_hash `1e34d3f487ef`) | authoritative | legacy/raw_responses_2026-07-02_030919.json | COMPLETE: 1080 responses (60 prompts x 6 models x 3 samples): gpt-5.5, gpt-5.4-mini, claude-sonnet-5, claude-haiku-4.5, gemini-3.5-flash, gemini-3.1-flash-lite. Single config vintage. Collection was interrupted once by an OpenAI budget cap (both OpenAI arms stalled at 60/180) and resumed after the cap was raised. |
| blinded_responses.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blinded_responses_2026-07-02.json | 1080 identity-stripped, shuffled responses for judging |
| blind_lookup.json | processed | 2026-07-02 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blind_lookup_2026-07-02.json | 1080-entry response_id -> (model, prompt, sample) unblinding map |
| judge_scores.json | raw_output | 2026-07-02 | `ai_eval.judge --resume` (rubric in judge_prompt_template.txt, provider-default sampling) | experimental | legacy/judge_scores_2026-07-02.json | IN PROGRESS: 6 judges x 1080 responses = 6480 judgments, mid-run at commit time; deliberately NOT committed in its partial state — will be committed when judging completes |
| analysis_results.json | processed | 2026-07-02 | `ai_eval.analyze` (analyze_version 3, bootstrap seed 20260521) | superseded | legacy/analysis_results_2026-07-02.json | Statistics for the SUPERSEDED 3-sample Sonnet-4.6 dataset; will be regenerated over the 6-model judgments |
| report.html | report | 2026-07-02 | `ai_eval.report` on analysis_results.json | superseded | legacy/report_2026-07-02.html | Report over the superseded 4.6-era statistics; will be regenerated |

**Current state (2026-07-02):** the six-model gen-5 run is past collection
and blinding (both complete and committed); judging is mid-flight
(judge_scores.json is filling toward 6480 and is intentionally left
uncommitted until complete). analysis_results.json and report.html still
describe the superseded 4.6-era dataset and regenerate automatically when
judging finishes. The complete 4.6-era judged dataset (540 responses, 1620
judgments) is preserved intact in legacy/ under the 2026-07-02 suffixes —
it remains internally consistent and supports the cross-generation
comparison (Sonnet 4 vs 4.6 under stable judges).
