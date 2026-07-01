# Data Inventory

Pipeline outputs. One row per artifact. Update this file in the same commit
that adds, regenerates, or moves any artifact in this folder.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-06-17 | `ai_eval.collect --resume --samples 3`; prompts_hash `1e34d3f487ef` | authoritative | legacy/raw_responses_2026-06-16.json | 540 responses (60 prompts x 3 models x 3 samples). MIXED config_hash by design: GPT-4o + Gemini at `c68bd88010e0` (kept from the original collection), Claude at `5069c7ddbd08` (re-collected on `claude-sonnet-4-6` after `claude-sonnet-4-20250514` retired 2026-06-15). See README "Status". |
| blinded_responses.json | processed | 2026-06-17 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blinded_responses_2026-06-17.json | 540 identity-stripped, shuffled responses for judging |
| blind_lookup.json | processed | 2026-06-17 | `ai_eval.blind` on the current raw_responses.json | authoritative | legacy/blind_lookup_2026-06-17.json | 540-entry response_id -> (model, prompt, sample) unblinding map |
| judge_scores.json | raw_output | 2026-06-18 | `ai_eval.judge` (rubric in judge_prompt_template.txt, temp 0.0) | authoritative | legacy/judge_scores_2026-06-17.json | 1620 judgments (540 responses x 3 judges); 7 null (claude 1, gemini 6) from residual provider hiccups, surfaced in the report's tie-breaking section |
| analysis_results.json | processed | 2026-07-02 | `ai_eval.analyze` (analyze_version 3, bootstrap seed 20260521) | authoritative | legacy/analysis_results_2026-07-02.json | Statistics for the 3-sample Sonnet-4.6 run: 1620 judgments, 3 samples/cell; v3 adds variance_components, self-favoritism premium CIs, pressure-drift turn_means, low_n flags |
| report.html | report | 2026-07-02 | `ai_eval.report` on analysis_results.json | authoritative | legacy/report_2026-07-02.html | Self-contained interactive report incl. manual tie-breaking UI; v3 adds premium CI column, per-turn drift trajectories, low-n suppression |

**Current state (2026-06-18):** the `data/` set is an internally consistent
3-sample run. Claude responses and judgments use `claude-sonnet-4-6`; the
`claude-sonnet-4-20250514` model used during the original collection retired
2026-06-15 mid-project, so only the Claude arm was re-collected while GPT-4o
and Gemini responses were kept as-is — hence the two `config_hash` values in
raw_responses.json. All downstream artifacts derive from this raw.
