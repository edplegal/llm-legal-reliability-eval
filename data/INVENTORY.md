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

**Current state (2026-07-02):** a 6-model tier-expansion run is mid-flight.
raw_responses.json holds only the two kept arms (GPT-4o, Claude); the Gemini
Flash arm was dropped because 62.8% of its responses were silently truncated
by the old 2048 output cap (Flash spends output budget on thinking), and it
will be re-collected under the raised 8192 cap together with the three new
arms (gpt-4o-mini, claude-haiku-4.5, gemini-2.5-pro). Until
`./run_all.sh --resume --samples 3` completes, blinded_responses.json,
blind_lookup.json, judge_scores.json, analysis_results.json, and report.html
all still describe the superseded 3-model run (with the truncated Flash
arm). The blind phase preserves the 1,080 still-valid judgments of the kept
arms; judge --resume re-buys nothing that survived.
