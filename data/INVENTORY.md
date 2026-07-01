# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-07-02 | `ai_eval.collect --resume --samples 3` (6-model grid config, output cap 8192) | experimental | legacy/raw_responses_2026-07-02.json | IN PROGRESS: 360/1080 (GPT-4o + Claude arms kept; Gemini Flash arm DROPPED for re-collection — 113/180 responses were truncated mid-sentence by the old 2048 output cap; chatgpt_mini / claude_haiku / gemini_pro arms pending). Resume with `./run_all.sh --resume --samples 3`. MIXED config_hash by design: GPT-4o at `c68bd88010e0`, Claude at `5069c7ddbd08`, new collection under the 6-model/8192 config. |
| blinded_responses.json | processed | 2026-06-17 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blinded_responses_2026-06-17.json | 540 identity-stripped, shuffled responses for judging |
| blind_lookup.json | processed | 2026-06-17 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blind_lookup_2026-06-17.json | 540-entry response_id -> (model, prompt, sample) unblinding map |
| judge_scores.json | raw_output | 2026-06-18 | `ai_eval.judge` (rubric in judge_prompt_template.txt, temp 0.0) | authoritative | legacy/judge_scores_2026-06-17.json | 1620 judgments (540 responses x 3 judges); 7 null (claude 1, gemini 6) from residual provider hiccups, surfaced in the report's tie-breaking section |
| analysis_results.json | processed | 2026-07-02 | `ai_eval.analyze` (analyze_version 3, bootstrap seed 20260521) | authoritative | legacy/analysis_results_2026-07-02.json | Statistics for the 3-sample Sonnet-4.6 run: 1620 judgments, 3 samples/cell; v3 adds variance_components, self-favoritism premium CIs, pressure-drift turn_means, low_n flags |
| report.html | report | 2026-07-02 | `ai_eval.report` on analysis_results.json | authoritative | legacy/report_2026-07-02.html | Self-contained interactive report incl. manual tie-breaking UI; v3 adds premium CI column, per-turn drift trajectories, low-n suppression |

**Current state (2026-07-02):** the grid has been upgraded to six
current-generation models (gpt-5.5 + gpt-5.4-mini, claude-sonnet-5 +
claude-haiku-4.5, gemini-3.5-flash + gemini-3.1-flash-lite), all sampling at
provider defaults (GPT-5.5 and Sonnet 5 reject explicit temperature; no
model receives sampling parameters). This supersedes both the earlier
tier-expansion plan and every artifact currently in `data/`: a FRESH
`./run_all.sh --samples 3` run (1080 responses, config_hash
`d64f7b847f91`, output caps 8192) will rotate the current raw (the two
4-era arms), the blinded set, all 1620 judge scores (fully orphaned by the
new collection), and the analysis/report to `legacy/`. Until that run
completes, everything in this folder describes the superseded
3-model/4-era dataset. If the run is interrupted, resume with
`./run_all.sh --resume --samples 3`.
