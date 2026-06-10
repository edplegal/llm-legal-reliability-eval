# Legacy Data Inventory

Superseded artifacts, date-suffixed. Nothing in this folder is authoritative.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses_2026-04-04.json | raw_output | 2026-04-04 | `python -m ai_eval.collect` (pre-multi-sample, pre-provenance-hash version) | superseded | — | Run 1: 90 responses (30 prompts x 3 models); lacks sample_idx, config_hash, prompts_hash fields |
| blinded_responses_2026-04-04.json | processed | 2026-04-04 | `python -m ai_eval.blind` on run-1 raw responses | superseded | — | Run 1 blinded set |
| blind_lookup_2026-04-04.json | processed | 2026-04-04 | `python -m ai_eval.blind` on run-1 raw responses | superseded | — | Run 1 unblinding map |
| judge_scores_2026-04-04.json | raw_output | 2026-04-04 | `python -m ai_eval.judge` on run-1 blinded set | superseded | — | Run 1: 270 judgments (90 responses x 3 judges); lacks judge_model_version field |
| analysis_results_2026-05-22.json | processed | 2026-05-22 | `python -m ai_eval.analyze` (analyze_version 2) re-run against run-1 data | superseded | — | Run-1 statistics, regenerated with the v2 analyzer shortly before the run-2 (60-prompt) dataset replaced it |
