# Legacy Data Inventory

Superseded artifacts, date-suffixed. Nothing in this folder is authoritative.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses_2026-04-04.json | raw_output | 2026-04-04 | `python -m ai_eval.collect` (pre-multi-sample, pre-provenance-hash version) | superseded | — | Run 1: 90 responses (30 prompts x 3 models); lacks sample_idx, config_hash, prompts_hash fields |
| blinded_responses_2026-04-04.json | processed | 2026-04-04 | `python -m ai_eval.blind` on run-1 raw responses | superseded | — | Run 1 blinded set |
| blind_lookup_2026-04-04.json | processed | 2026-04-04 | `python -m ai_eval.blind` on run-1 raw responses | superseded | — | Run 1 unblinding map |
| judge_scores_2026-04-04.json | raw_output | 2026-04-04 | `python -m ai_eval.judge` on run-1 blinded set | superseded | — | Run 1: 270 judgments (90 responses x 3 judges); lacks judge_model_version field |
| analysis_results_2026-05-22.json | processed | 2026-05-22 | `python -m ai_eval.analyze` (analyze_version 2) re-run against run-1 data | superseded | — | Run-1 statistics, regenerated with the v2 analyzer shortly before the run-2 (60-prompt) dataset replaced it |
| raw_responses_2026-06-12.json | raw_output | 2026-05-22 | `python -m ai_eval.collect` (run 2, single sample; rotated here 2026-06-12 when the 3-sample collection began) | superseded | — | The 2026-05-22 collection: 180 responses (60 prompts x 3 models x 1 sample); the run-2 blinded/judge/analysis artifacts in data/ derive from this file |
| blinded_responses_2026-06-16.json | processed | 2026-05-22 | `python -m ai_eval.blind` on the 2026-05-22 single-sample raw; rotated here 2026-06-16 | superseded | — | The 2026-05-22 single-sample blinded set (180 responses) |
| blind_lookup_2026-06-16.json | processed | 2026-05-22 | `python -m ai_eval.blind` on the 2026-05-22 single-sample raw; rotated here 2026-06-16 | superseded | — | The 2026-05-22 single-sample unblinding map (180) |
| judge_scores_2026-06-16.json | raw_output | 2026-05-22 | `python -m ai_eval.judge` on the 2026-05-22 blinded set; rotated here 2026-06-16 | superseded | — | 540 judgments of the 2026-05-22 single-sample responses; 29 gemini null |
| raw_responses_2026-06-16.json | raw_output | 2026-06-16 | `ai_eval.collect --samples 3` (config_hash `c68bd88010e0`); snapshotted here 2026-06-16 before the Claude re-collection | superseded | — | Full pre-retirement 3-sample collection (540) with Claude on `claude-sonnet-4-20250514`. Its Claude arm is superseded by the Sonnet-4.6 re-collection in data/raw_responses.json; its GPT-4o/Gemini arms are byte-identical to the authoritative raw. Do NOT union with data/raw_responses.json. |
| blinded_responses_2026-06-17.json | processed | 2026-06-16 | `ai_eval.blind` on the 2026-06-16 Sonnet-4 3-sample raw; rotated here 2026-06-17 | superseded | — | 540-response blinded set built from Claude's pre-retirement (Sonnet-4) responses; superseded when the Sonnet-4.6 raw was re-blinded |
| blind_lookup_2026-06-17.json | processed | 2026-06-16 | `ai_eval.blind` on the 2026-06-16 Sonnet-4 3-sample raw; rotated here 2026-06-17 | superseded | — | Unblinding map (540) for the Sonnet-4 blinded set |
| judge_scores_2026-06-17.json | raw_output | 2026-06-16 | `ai_eval.judge` (aborted) on the Sonnet-4 blinded set; rotated here 2026-06-17 | superseded | — | Aborted partial: 59 judgments, Claude 100% null (`claude-sonnet-4-20250514` 404'd after its 2026-06-15 retirement); diagnostic only |
| analysis_results_2026-06-18.json | processed | 2026-05-22 | `ai_eval.analyze` (analyze_version 2) on the 2026-05-22 single-sample run; rotated here 2026-06-18 | superseded | — | Statistics for the 2026-05-22 single-sample (60-prompt) run: 540 judgments, 1 sample/cell |
| report_2026-06-18.html | report | 2026-05-22 | `ai_eval.report` on the 2026-05-22 analysis; rotated here 2026-06-18 | superseded | — | Report for the 2026-05-22 single-sample run |
| analysis_results_2026-07-02.json | processed | 2026-06-18 | `ai_eval.analyze` (analyze_version 2) on the 3-sample Sonnet-4.6 run; rotated here 2026-07-02 when analyze v3 regenerated it | superseded | — | v2 statistics for the current 1620-judgment dataset; same inputs as the authoritative v3 file, fewer computed stats |
| report_2026-07-02.html | report | 2026-06-18 | `ai_eval.report` on the v2 analysis; rotated here 2026-07-02 | superseded | — | Report over the v2 statistics for the current dataset |
