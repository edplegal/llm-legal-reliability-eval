# Data inventory

One row per artifact. Schemas, model versions, dates and caveats are in
[DATA_CARD.md](DATA_CARD.md). Regenerating any file through the pipeline
rotates the prior copy into `data/legacy/`, which is gitignored; update this
table in the same commit.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| raw_responses.json | raw_output | 2026-07-02 | `./run_all.sh --samples 3` (config `d64f7b847f91`, prompts `1e34d3f487ef`) | authoritative | — | 1,080 answers: 60 questions × 6 models × 3 samples |
| blinded_responses.json | processed | 2026-07-02 | `ai_eval.blind` | authoritative | — | identity-stripped, shuffled answers shown to judges |
| blind_lookup.json | processed | 2026-07-02 | `ai_eval.blind` | authoritative | — | response_id → (model, prompt, sample) |
| judge_scores.json | raw_output | 2026-07-03 | `ai_eval.judge` | authoritative | — | 6,480 panel grades (25 null) with justifications |
| bridge_scores.json | raw_output | 2026-07-03 | `ai_eval.judge` with `config/bridge_config.json` | authoritative | — | 2,160 grades by the two frozen judges (9 null) |
| analysis_results.json | processed | 2026-07-08 | `ai_eval.analyze` (v4, seed 20260521) | authoritative | — | every panel statistic in the report |
| bridge_results.json | processed | 2026-10-09 | `ai_eval.bridge` (v1, seed 20260521) | authoritative | — | Finding 5: levels, steps and crisis shifts under the frozen judges across three generations |
| null_refill_results.json | processed | 2026-10-11 | `ai_eval.robustness` (v1), `math.fsum` summation | authoritative | earlier version in git history | largest movement of every reported statistic when the nulls are refilled with 1s and with 5s |
| report.html | report | 2026-07-08 | `ai_eval.report` | authoritative | — | interactive report incl. the high-disagreement review cards |
| archive/gen4/gen4_*.json | raw_output, processed | 2026-05-22 | `ai_eval.collect`, `blind`, `judge` (May 2026 pipeline) | reference | — | the spring 2026 run: 180 answers, 540 grades |
| archive/gen46/gen46_*.json | raw_output, processed | 2026-06-12 to 06-18 | `ai_eval.collect --samples 3`, `blind`, `judge` (June 2026 pipeline) | reference | — | the June 2026 run: 540 answers, 1,620 grades; Gemini arm truncated |
| archive/gen46/gen46_analysis_results.json | processed | 2026-10-11 | `ai_eval.analyze` (v4), `math.fsum` summation, over the June 2026 run | reference | earlier version in git history | the previous run's panel statistics, cited for its variance split |
| DATA_CARD.md | doc | 2026-10-09 | hand-written | authoritative | — | schemas, model versions, dates, caveats, licenses |
