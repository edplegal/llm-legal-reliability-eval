# Data card

Everything in `data/` was produced by the pipeline in `src/ai_eval/` from the
sixty questions in `prompts.json`, the rubric in `rubric.md`, and the judge
prompt in `judge_prompt_template.txt`. Nothing was hand-edited. All files are
JSON; every analysis output carries its own `metadata` block with the
analyzer version, the bootstrap seed, and a `generated_at` stamp.

## The current run (July 2026)

| file | records | schema | produced by |
|---|---|---|---|
| `raw_responses.json` | 1,080 | `prompt_id`, `model_id`, `sample_idx` (0 to 2), `response_text`, `timestamp`, `model_version`, `tokens_used`, `config_hash`, `prompts_hash` | `ai_eval.collect --samples 3` |
| `blinded_responses.json` | 1,080 | `prompt_id`, `response_id` (content hash), `response_text` | `ai_eval.blind` |
| `blind_lookup.json` | 1,080 | `response_id` → `{model_id, prompt_id, sample_idx, timestamp}` | `ai_eval.blind` |
| `judge_scores.json` | 6,480 | `response_id`, `prompt_id`, `judge_model`, `judge_model_version`, `scores` (per dimension `{score, justification}`; `null` when the judge returned unparseable JSON), `timestamp` | `ai_eval.judge` |
| `bridge_scores.json` | 2,160 | same shape; judges `bridge_gpt4o` and `bridge_gemini25` | `ai_eval.judge` with `config/bridge_config.json` |
| `analysis_results.json` | 1 | panel statistics, analyze v4, seed 20260521 | `ai_eval.analyze` |
| `bridge_results.json` | 1 | generational chain under the frozen judges, bridge v1 | `ai_eval.bridge` |
| `null_refill_results.json` | 1 | adversarial null refill, robustness v1 | `ai_eval.robustness` |
| `report.html` | 1 | self-contained interactive report over the analysis, with the review cards for the fifteen high-disagreement answers | `ai_eval.report` |

Scores run 1 to 5. A score of 0 means the judge marked the dimension not
applicable; the analysis treats 0 as missing. Dimensions: `disclaimer`,
`escalation`, `confidence`, `jurisdiction`, `guardrail`, `regulatory`.

A handful of judgments carry stray sibling keys next to `score` and
`justification` (`justify`, `borderline`, `italic`, `note`, `thought`,
`guardrail_note`). They are the judges' own output, kept verbatim; the
analysis reads `score` only.

### Models, versions and dates

| id in the data | served version | role |
|---|---|---|
| `chatgpt` | `gpt-5.5-2026-04-23` | responder and judge |
| `chatgpt_mini` | `gpt-5.4-mini-2026-03-17` | responder and judge |
| `claude` | `claude-sonnet-5` | responder and judge |
| `claude_haiku` | `claude-haiku-4-5-20251001` | responder and judge |
| `gemini` | `gemini-3.5-flash` | responder and judge |
| `gemini_lite` | `gemini-3.1-flash-lite` | responder and judge |
| `bridge_gpt4o` | `gpt-4o-2024-08-06` | frozen judge, temperature 0.0, 4,096-token cap |
| `bridge_gemini25` | `gemini-2.5-flash` | frozen judge, temperature 0.0, 4,096-token cap |

- Answers collected 2026-07-02, 03:09 to 10:49 UTC, at provider-default sampling with an 8,192-token output cap; single configuration, `config_hash` `d64f7b847f91`, `prompts_hash` `1e34d3f487ef`.
- Panel judging 2026-07-02 10:50 to 2026-07-03 11:31 UTC, provider defaults, 8,192-token cap. 25 of 6,480 judgments are null, all from `gemini`.
- Bridge judging 2026-07-03 11:42 to 22:07 UTC. 9 of 2,160 are null, all from `bridge_gemini25`.
- Four Sonnet 5 judgments originally arrived with flat integer fields where objects were expected; they were dropped and re-judged under shape validation. Collection was interrupted once by an OpenAI spending cap and resumed.

## The two earlier runs (`data/archive/`)

Both used the same sixty questions and the judges `chatgpt` (`gpt-4o-2024-08-06`) and `gemini` (`gemini-2.5-flash`) at temperature 0.0, which is what makes them comparable to the bridge pass. Their Claude judge changed between runs and is not used in any cross-generation statistic.

| folder | collected | judged | responders | records |
|---|---|---|---|---|
| `gen4/` | 2026-05-22 | 2026-05-22 | `claude` = `claude-sonnet-4-20250514`, `chatgpt` = `gpt-4o-2024-08-06`, `gemini` = `gemini-2.5-flash`; one sample per question | 180 answers, 540 grades (29 null, all `gemini`) |
| `gen46/` | 2026-06-12 to 06-17 | 2026-06-17 to 06-18 | `claude` = `claude-sonnet-4-6`; the other two unchanged; three samples per question | 540 answers, 1,620 grades (7 null) |

Files follow the current-run schema with an era prefix: `gen4_raw_responses.json`, `gen4_blinded_responses.json`, `gen4_blind_lookup.json`, `gen4_judge_scores.json`, and likewise for `gen46_`, plus `gen46_analysis_results.json` (analyze v4 over that run, generated 2026-10-09 for the release; it backs the report's statement that the re-asked-answer share of variance was 5 percent in the previous run).

Caveats on the archive:

- Both earlier runs sampled responders at temperature 0.7 with a 2,048-token output cap. The current run uses provider defaults and 8,192 tokens. Every generational comparison in the report carries that difference and says so.
- The `gemini` arm of `gen46` is truncated: 113 of its 180 answers stop mid-sentence because the model's internal reasoning consumed the output budget. The report discusses this (Limitation 9). The frozen judges graded the cut-off text; the truncation inflates the Gemini step in Finding 5 and the report says so.
- `gen4` is a single-sample run; its per-question means pool two judges over one answer.

## What is in the git history but not in the tree

The repository carries the development history from June 2026 onward. Earlier states of the working tree therefore hold files that the release tree omits:

- The April 2026 pilot (30 questions, 90 answers, 270 grades), under `data/legacy/`; it used an earlier question set and appears in no claim.
- Two aborted or superseded collections from June 2026 under `data/legacy/` (a Sonnet 4 three-sample collection never fully judged because the model was retired mid-run, and a 59-judgment partial); they appear in no claim.
- Rotated intermediate copies of the files above, which differ only in `generated_at` or in four repaired records.
- The post drafts under `drafts/`, versions 1 through 7.

API keys were never committed; the pipeline reads them from the environment.

## Licenses

Data, prompts, rubric and judge prompt: CC BY 4.0 (`LICENSE-DATA`). Code: MIT (`LICENSE`). Attribution: edplegal, "Judge Bias in a Blind Legal-Advice Evaluation", https://github.com/edplegal/llm-legal-reliability-eval.
