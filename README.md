# ai-eval-legal

Blinded cross-model AI safety evaluation pipeline for legal and regulatory
questions.

## Purpose

Measures whether frontier LLMs (GPT-4o, Claude Sonnet, Gemini Flash) behave
safely when users ask legal questions or questions about deploying AI in
regulated domains. Each model answers every prompt; responses are blinded and
shuffled; every model then judges every response against a six-dimension
rubric ([rubric.md](rubric.md)); analysis unblinds the scores and computes
statistics designed around three methodological commitments:

1. **Prompt-paired comparisons** — the same prompts go to every model, so
   bootstrap CIs resample prompts, not judgments.
2. **Self-favoritism controls** — a judge's bias on its own model's responses
   is measured against the median of the *other* judges on the *same*
   response, removing the "my responses really are better" confound.
3. **Framing sensitivity as the headline metric** — prompt pairs hold the
   legal topic constant and vary only user framing (information-seeking vs.
   crisis), and three-turn pressure sequences measure rigor decay.

This iteration (previously `mvp_3`) extends prior runs with paired
info/crisis prompts, pressure sequences, multi-sample collection, bootstrap
CIs, Krippendorff's α, and a provenance-stamped pipeline.

## Inputs

| path | role |
|------|------|
| `prompts.json` | 60 evaluation prompts (paired info/crisis, 3-turn pressure sequences, adversarial, AI-deployment) |
| `config.json` | Model endpoints, model IDs, temperatures, token limits |
| `judge_prompt_template.txt` | Judge prompt; rubric inlined, placeholders for prompt/response |
| `rubric.md` | Human-readable scoring rubric (source of truth mirrored in the template) |

API keys come from environment variables (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`). Never commit keys.

## Outputs

All pipeline outputs land in `data/` and are tracked in
[data/INVENTORY.md](data/INVENTORY.md). Regenerating an artifact moves the
prior version to `data/legacy/` with a date suffix — no silent overwrites.

| artifact | produced by | contents |
|----------|-------------|----------|
| `data/raw_responses.json` | Phase 1 | One entry per (prompt, model, sample): response text + provenance (`model_version`, `config_hash`, `prompts_hash`, timestamp) |
| `data/blinded_responses.json` | Phase 2 | Identity-stripped, shuffled responses for judging |
| `data/blind_lookup.json` | Phase 2 | `response_id` → (model, prompt, sample) unblinding map |
| `data/judge_scores.json` | Phase 3 | One entry per (response, judge): six-dimension scores + justifications |
| `data/analysis_results.json` | Phase 4 | Full statistics (see Purpose) |
| `data/report.html` | Phase 5 | Self-contained interactive report incl. manual tie-breaking UI |

## How to run

```bash
uv venv && uv pip install -e ".[dev]"   # one-time setup

export OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=...

./run_all.sh                  # full pipeline, 1 sample per (prompt, model)
./run_all.sh --samples 3      # 3 samples per cell (separates response from judge variance)
./run_all.sh --resume         # skip already-collected/judged work after an interruption
./run_all.sh --dry-run        # print the plan without API calls
```

Phases can also be run individually: `python -m ai_eval.collect`,
`ai_eval.blind`, `ai_eval.judge`, `ai_eval.analyze`, `ai_eval.report`
(or via the installed `ai-eval-*` console scripts).

## Development

```bash
.venv/bin/python -m pytest            # tests + 90% coverage gate
.venv/bin/python -m mypy src tests    # strict typing
.venv/bin/python -m ruff check src tests
.venv/bin/python -m black src tests
```

## Status

- **Complete:** full 5-phase pipeline; current `data/` set is an internally
  consistent run (2026-05-22): 60 prompts × 3 models × 3 judges, 540
  judgments (29 null = judge JSON parse failures, listed in the report's
  tie-breaking section).
- **Known gaps:** null judge scores await manual tie-breaking via the report
  UI; multi-sample (`--samples 3+`) has not yet been run against the live
  APIs.
- **Prior iterations:** `mvp_1`/`mvp_2` predate this repo; the run-1 (30
  prompt) artifacts live in `data/legacy/`.
