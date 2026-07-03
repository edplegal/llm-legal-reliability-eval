# ai-eval-legal

Blinded cross-model AI safety evaluation pipeline for legal and
regulatory questions.

## Purpose

Measures whether frontier LLMs behave safely when users ask legal
questions or questions about deploying AI in regulated domains. The
current grid is six models across three vendors and two tiers: gpt-5.5,
gpt-5.4-mini, claude-sonnet-5, claude-haiku-4.5, gemini-3.5-flash,
gemini-3.1-flash-lite. Each model answers every prompt three times;
responses are blinded and shuffled; the same six models judge every
response against a six-dimension rubric ([rubric.md](rubric.md));
analysis unblinds the scores and computes statistics designed around
three methodological commitments:

1. **Prompt-paired comparisons** — the same prompts go to every model,
   so bootstrap CIs resample prompts, not judgments.
2. **Self-favoritism controls** — a judge's bias on its own model's
   responses is measured against the median of the *other* judges on the
   *same* response.
3. **Framing sensitivity as the headline metric** — prompt pairs hold
   the legal topic constant and vary only user framing, and three-turn
   pressure sequences measure rigor decay.

A **bridge-judging pass** additionally re-runs two frozen legacy judges
(gpt-4o-2024-08-06, gemini-2.5-flash, temperature 0.0) over the current
responses, making comparisons across three model generations
judge-controlled.

## Orientation for a new session

Read in this order:
1. This README's Status section — where things stand.
2. [HISTORY.md](HISTORY.md) — full chronology with commit hashes, the
   statistics explained from first principles, the incident registry,
   and current open items (Part VI).
3. [FINDINGS.md](FINDINGS.md) — the verification memo behind every
   publishable number, including the do-not-publish list (§8).
4. [data/INVENTORY.md](data/INVENTORY.md) — the artifact ledger; every
   file's provenance, every rotation.
5. [drafts/substack_post.md](drafts/substack_post.md) — the publication
   draft (v3) with `[YOU]`/`[LW-ONLY]`/`[CUT-OK]` markers.

## Inputs

| path | role |
|------|------|
| `prompts.json` | 60 evaluation prompts (paired info/crisis, 3-turn pressure sequences, adversarial, AI-deployment). HELD OUT of the public release. |
| `config.json` | Model endpoints, model IDs, token limits. Sampling runs at provider defaults; per-model `temperature` exists only for bridge-run replication. |
| `judge_prompt_template.txt` | Judge prompt; rubric inlined |
| `rubric.md` | Human-readable scoring rubric |

API keys come from environment variables (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`). Never commit keys.

## Outputs

All pipeline outputs land in `data/` and are tracked in
[data/INVENTORY.md](data/INVENTORY.md). Regenerating an artifact moves
the prior version to `data/legacy/` with a date suffix.

| artifact | produced by | contents |
|----------|-------------|----------|
| `data/raw_responses.json` | Phase 1 | 1080 responses with full provenance (model_version, config_hash, prompts_hash) |
| `data/blinded_responses.json` | Phase 2 | Identity-stripped, shuffled responses (content-hash IDs) |
| `data/blind_lookup.json` | Phase 2 | response_id → (model, prompt, sample) unblinding map |
| `data/judge_scores.json` | Phase 3 | 6480 shape-validated judgments (6 judges × 1080) |
| `data/bridge_scores.json` | bridge run | 2160 judgments by the frozen legacy judges (generational control) |
| `data/analysis_results.json` | Phase 4 | Full statistics (analyze v3: averages, paired diffs, α, self-premiums with CIs, calibration, drift with turn means, variance components, low-n flags) |
| `data/report.html` | Phase 5 | Self-contained interactive report incl. the high-disagreement review UI |

## How to run

```bash
uv venv && uv pip install -e ".[dev]"   # one-time setup

export OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=...

./run_all.sh --samples 3              # full pipeline, fresh
./run_all.sh --resume --samples 3     # resume after any interruption
./run_all.sh --dry-run                # print the plan without API calls

# Bridge pass (frozen legacy judges over current responses):
AI_EVAL_BASE_DIR=$PWD/bridge_run .venv/bin/python -m ai_eval.judge
```

Long phases (collect, judge) should run in a user terminal, not a
background shell. Phases are individually runnable via
`python -m ai_eval.{collect,blind,judge,analyze,report}`.

## Development

```bash
.venv/bin/python -m pytest            # tests + 90% coverage gate
.venv/bin/python -m mypy src tests    # strict typing
.venv/bin/python -m ruff check src tests
.venv/bin/python -m black src tests
```

## Status (2026-07-03)

- **Complete:** the six-model gen-5 dataset, end to end — 1080 responses
  (single config `d64f7b847f91`), 6480 panel judgments (25 null, 0.39%),
  2160 bridge judgments (9 null), v3 analysis, report. All verified:
  zero truncation, perfect joins, adversarial null fills move nothing
  beyond 0.021. Three archived predecessor datasets in `data/legacy/`
  support the generational analysis.
- **Publication prep (in flight):** draft v3 in `drafts/substack_post.md`
  awaits the author's `[YOU]` sections, the review of 15
  high-disagreement transcripts in `data/report.html`, and the release
  repo build (fresh init: code, rubric, stripped scores incl. bridge,
  worked examples; prompts held out). Target venues: author's Substack +
  LessWrong crosspost (LLM-writing policy reviewed; disclosure block in
  draft).
- **Known gaps:** none in the data. Open work is writing and curation
  only — see HISTORY.md Part VI.
