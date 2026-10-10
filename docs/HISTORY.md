# Project History & Methods Deep-Dive

> Development log, kept verbatim from the working repository as of its last commit (2026-07-17). File paths in it refer to that repository's layout: `data/legacy/` and `drafts/` are in this repository's git history but not in its tree, and the post draft now lives in `report/post.md`. The release corrections of 2026-10-09 (the null-refill bound, the Finding 5 control sentence) postdate this log and are recorded in the release commit.

**Audience:** the author. This is the complete internal record of what
happened in this project, why each decision was made, and how every
statistic is computed — at a depth the published article does not need.
Nothing here is written for publication; it exists so every number in the
post can be defended from first principles. Companion documents:
[FINDINGS.md](FINDINGS.md) (pre-publication verification of the 4.6-era
numbers) and [drafts/substack_post.md](drafts/substack_post.md).

---

## Part 0 — The experiment in one paragraph

Sixty author-written legal questions are answered by a grid of models
(three samples per question per model). All answers are stripped of
identity, shuffled, and then graded by the *same* models against a
six-dimension safety rubric ([rubric.md](rubric.md)): disclaimer presence,
escalation appropriateness, confidence calibration, jurisdiction awareness,
guardrail stability, regulatory awareness — each 1–5 or N/A. Analysis
unblinds the grades and computes statistics designed around three
commitments: the prompt (not the judgment) is the unit of analysis;
self-favoritism is measured against other judges on the identical text;
and framing sensitivity (same legal topic, calm vs desperate user) is the
headline behavioral metric.

---

## Part I — Chronology (what actually happened, in order)

Commit hashes are given so every event is traceable in git.

### Era 1: the 4-generation study

| date | event |
|---|---|
| 2026-04-04 | **Run 1** (predates this repo's conventions): 30 prompts × 3 models, 270 judgments. Kept in `data/legacy/*_2026-04-04.json`. Different prompt set — never comparable to later runs. |
| 2026-05-21/22 | 60-prompt set finalized (`prompts_hash 1e34d3f487ef` — unchanged ever since). **Run 2**: single-sample collection (180 responses; gpt-4o-2024-08-06, claude-sonnet-4-20250514, gemini-2.5-flash), 540 judgments, 29 null (all Gemini JSON failures). |
| 2026-06-12 | 3-sample collection begins (`3ba213b`); interrupted at 232/540; outage-survival + stronger retry backoff added (`ba95b61`); resumed and completed 537/540 (3 Gemini cells dropped to a transient 503). |
| 2026-06-15 | **`claude-sonnet-4-20250514` is retired by Anthropic.** Nobody notices for a day. |
| 2026-06-16 | Judging the 3-sample set starts and every Claude judge call returns 404 (the retired model). Run stopped at 59/1620 (chatgpt 20 ok, claude 0/20, gemini 18/19). Diagnosis: deterministic 404 = retirement, not code. Decision: migrate to `claude-sonnet-4-6` (`88cb7f6`) and **re-collect the Claude arm only** (accepting two `config_hash` vintages in one raw file, documented). Judge retry hardened from a fixed 2-attempt/2s pattern to the shared 5-attempt exponential backoff (`8a3c13d`) after Gemini 503s cost judgments. |
| 2026-06-16→17 | Claude arm re-collected on Sonnet 4.6 (one interruption — background jobs die in the assistant's shell; long runs live in the user's terminal thereafter). Blind + judge complete. |
| 2026-06-18 | **4.6-era dataset complete:** 540 responses, 1,620 judgments, 7 null (0.43%; claude 1, gemini 6 — the hardened retry cut the null rate from 5.4% to 0.43%). Committed (`015365b`). |

### Era 2: hardening and the draft

| date | event |
|---|---|
| 2026-07-01 | **Pre-publication hardening** (five workstreams, written up in FINDINGS.md, `2853b25`): headline numbers extracted; self-favoritism premiums given bootstrap CIs (16/18 cells exclude 0); the 21%→29% critical-failure "jump" shown to be 3-way confounded (do-not-publish); adversarial null-fill robustness (max shift 0.03, no rank flips); nested variance decomposition (prompt 59.6 / judge 35.3 / response 5.1). |
| 2026-07-01 | **analyze v3** (`6b7ab05`, regenerated artifacts `f5192a1`): the offline hardening statistics moved into the pipeline proper — `variance_components`, premium CIs, per-turn drift means, `low_n` flags with report suppression — so the public repo reproduces every published number natively. |
| 2026-07-01 | Post skeleton drafted (`10a4416`); first feedback round applied (plain-language rewrites, `03741da`). |

### Era 3: the grid expansion that became a generation upgrade

| date | event |
|---|---|
| 2026-07-02 | Tier-mismatch limitation (Flash vs mid-tiers) → decision to expand to a 2×3 grid. **blind.py partial-orphan fix** (`eeb05ba`): previously, re-collecting one arm would rotate the *entire* judge-scores file and force re-buying every judgment; now still-joining rows are written back. |
| 2026-07-02 | **Truncation discovery:** a 16-token probe of gemini-2.5-pro returned an empty candidate (thinking consumed the whole budget), prompting a check of the existing data — **62.8% of the Gemini Flash arm (113/180) ended mid-sentence** at the old 2048 output cap (median total tokens 2071 ≈ at the ceiling). GPT/Claude arms verified clean (max 947 tokens, cap never binding). Judges had been grading amputated text for two-thirds of one arm. Flash arm dropped for re-collection; caps raised to 8192 (`c15298d`, `01c000f`). |
| 2026-07-02 | **Generation upgrade decision** (user-initiated): gpt-4o found deprecated upstream; catalogs researched and live-probed. Final grid: gpt-5.5 + gpt-5.4-mini, claude-sonnet-5 + claude-haiku-4.5, gemini-3.5-flash + gemini-3.1-flash-lite. Probes surfaced two API-contract changes: GPT-5.x requires `max_completion_tokens`; **GPT-5.5 and Sonnet 5 reject `temperature` entirely** (no replacement exists). Decision: **provider-default sampling for all six models** — temperature removed from the entire pipeline (`1e20533`). Sonnet 5's adaptive thinking also meant `content[0]` is no longer guaranteed to be the text block; the client now finds the first text block. |
| 2026-07-02 03:09 | Fresh gen-5 run starts (1080 cells, single config `d64f7b847f91`). |
| 2026-07-02 04:14–05:32+ | **OpenAI budget cap hit:** both OpenAI arms stall at exactly 60/180 (prompts 1–20) and 429 continuously for 75+ minutes; the four other arms complete 180/180; the pipeline skips the dead cells and halts before blinding (by design). Root cause confirmed by user: monthly budget cap. Diagnosability fix: retry warnings now log the error body + retry-after (`ccc2c02`). |
| 2026-07-02 | Cap raised; `--resume` fills exactly the 240 missing cells. Collection completes (1080), blind runs (the fix from `eeb05ba` correctly rotates the fully-orphaned 4.6-era judgments to legacy intact), judging begins (6 × 1080 = 6480). Completed collection + blind outputs + archived 4.6-era dataset committed (`9bfc988`); the in-flight judge file deliberately excluded. |
| 2026-07-02 | **Cross-generation analysis** (Part IV below): Sonnet 4 → 4.6 compared under stable judges; gen-5 lexical preview over all 1080 responses. |
| 2026-07-03 | **Shape incident** (registry #8): 4 Sonnet-5 judgments arrived with flat guardrail/regulatory fields and crashed analysis. Shape validation added at judge time, crash-proof reader in analysis, the 4 records re-judged (`ca82db5`). Six-model dataset landed complete: 6480 judgments, 25 null (`66ef8eb`); post-flight verified (zero truncation, null-robust); FINDINGS v2 (`c573747`). User re-ran the pipeline tail independently: byte-identical statistics (`813468b`). |
| 2026-07-03 | **Bridge pass** (Part IV.4): frozen legacy judges over all 1080 gen-5 responses (`b75cbf1`, `c4149a3`). It corrected the monotonic-decline claim (V-shape on levels) and confirmed Sonnet 5's backwards crisis calibration under both panels (`e8e88a9`). |
| 2026-07-03 | **Draft rebuilt** on the six-model dataset and bridge chain (v2, `f6bffe7`), then v3 applying the third prose round: chosen title, no appositives, no empty sentences, correction stated explicitly, sidebar pointer to the 15 guardrail disputes. README and this document brought current for session handoff. |
| 2026-07-05→08 | **Author review of the 15 high-disagreement transcripts** (drafts/disagreement_review.md): 11 of 15 flags trace to one yes/no prompt; claude_haiku scored 5.0 on all 11 against a panel floor of 1 with justifications contradicting its own scores; chatgpt_mini marked all 11 not-applicable; two crisis cards ruled N/A (judge-prompt spec gap); the two OpenAI-response cards split perfectly by vendor. Sidebar drafted from the rulings. Author decisions: nothing cut for Substack; one text ships to both venues. Draft v4/v5: two heavy prose rounds enforcing the author's style contract (short declarative sentences, no AI-tell constructions). |
| 2026-07-08 | **Self-premium confound found and fixed (analyze v4).** An external-review prompt challenged the "recognized itself" title; follow-up showed the raw median-of-others premium never subtracted the judge's deviation on OTHERS' responses (its grading style). Style-corrected nets: Claude's "self-deprecation" is ~0 on all four dims in BOTH generations — it is the panel's harshest judge on everyone; mini's +0.99 disclaimer premium is +0.94 generosity toward everyone; 14/24 significant nets remain, ALL positive, Gemini family strongest (8/8 cells). analyze v4 adds style_deviation + net_self_premium with prompt-bootstrap CIs; report gains the columns; FINDINGS §10 + do-not-publish item 5 (raw premiums never published as self-bias); title, epistemic status, TL;DR, and Finding 1 rebuilt on the corrected numbers. |

---

## Part II — The pipeline, mechanically

Five phases, each a module, each resumable, each provenance-stamped:

1. **collect** — for each (prompt, model, sample) cell, one API call. Every
   record carries `model_version` (the snapshot the API actually served),
   `config_hash` (a hash over the model set, token caps, sampling mode,
   system prompt, and samples-per-cell), `prompts_hash`, and a timestamp.
   Failed cells are skipped and reported; `--resume` retries exactly the
   missing set. A fresh run rotates the prior file to `data/legacy/`.
2. **blind** — strips identity, assigns each response a **content-hash ID**
   (`R-` + 12 hex chars of sha256(prompt|model|sample|text)), shuffles
   presentation order with a fixed seed. Content-hash IDs are the load-bearing
   trick: re-blinding unchanged responses reproduces identical IDs, so
   existing judgments always re-join; only genuinely changed responses
   orphan their old judgments (which are preserved to legacy, and — since
   `eeb05ba` — surviving rows are written back rather than discarded).
   A scanner warns if any response self-identifies ("I'm Claude…").
3. **judge** — every configured model judges every blinded response against
   the rubric, returning JSON with per-dimension scores + justifications.
   Transport failures get 5-attempt exponential backoff; unparseable JSON
   gets one re-ask; a still-failing judgment is stored as null (never
   fabricated). Resume keys on (response_id, judge).
4. **analyze** — unblinds and computes everything in Part III. v3.
5. **report** — self-contained HTML with the tie-breaking UI for nulls and
   high-disagreement items.

**Provenance rules in force:** no artifact is ever silently overwritten
(rotation to `legacy/` with date suffix); INVENTORY.md updated in the same
commit as any artifact change; no basename may exist in both `data/` and
`data/legacy/`; artifacts are self-describing (model versions and hashes
inside the files, not just the inventory).

---

## Part III — The statistics, from first principles

### III.1 Why the prompt is the unit of analysis

The 4.6-era dataset has 1,620 judgments, but they are not 1,620 independent
observations. All 27 judgments attached to one prompt (3 samples × 3 judges,
or 9 × 3 in the 6-model era) share that prompt: if the question is unusually
hard, every one of its judgments sits low together. Independence is at the
prompt level — 60 observations. Any uncertainty computed as if n=1,620 would
be dishonestly narrow by roughly √(1620/60) ≈ 5×. So every aggregate first
collapses to one value per prompt (averaging judges and samples), and all
uncertainty is computed over those 60 values.

### III.2 The bootstrap, completely

**The question an error bar answers here:** the 60 prompts are one draw
from the universe of legal questions one could ask. A different author-week
produces a different-but-similar 60, and every average shifts a bit. The
error bar estimates the size of that shift.

**Why we can't do it directly:** we'd need thousands of alternative
60-prompt sets, each collected and judged. Impossible.

**The bootstrap's substitute:** treat the observed 60 per-prompt values as
the best available estimate of the universe's distribution, and draw new
sets *from it*. Concretely: draw 60 values from our 60 **with replacement**
(some prompts appear twice or thrice, some not at all), compute the mean,
repeat 2,000 times (seed 20260521, so every run reproduces byte-identical
intervals), sort the 2,000 means, and report the 2.5th and 97.5th
percentiles as the 95% CI.

**Why "with replacement" is the essential part:** sampling without
replacement would just reproduce the same 60 values in a different order —
every "alternative set" would have the identical mean. With replacement,
each draw is an independent pick from the empirical distribution, which is
mathematically the same as drawing a fresh sample from a population whose
distribution equals our observed one. The spread of the resampled means
then estimates the sampling variability of the real mean.

**Tiny worked example.** Suppose 3 prompts scored [2, 3, 5], mean 3.33.
Resamples might be [2,2,5]→3.0, [3,5,5]→4.33, [2,3,3]→2.67, [5,5,5]→5.0 …
The spread of those resampled means directly shows how much the mean
depends on which prompts happened to be drawn. With 60 prompts the same
logic applies, just tighter.

**Paired versions:** for model comparisons, the resampled quantity is the
per-prompt *difference* (model A's prompt mean minus model B's on the same
prompt), for crisis-shifts it is the per-pair shift, for pressure it is the
per-sequence drift. Pairing removes prompt difficulty from the comparison:
a hard prompt drags both models down equally and cancels in the difference.

**What the CI means operationally:** "CI excludes zero" = fewer than 5% of
plausible alternative prompt sets would flip the sign of the effect. It
quantifies prompt-sampling noise only — not construct validity (whether the
rubric measures the right thing), not judge validity.

### III.3 Self-favoritism: the median-of-others premium

For each blinded response written by model M that M itself also judged:

    premium = M's score − median(other judges' scores on the same response)

Two design choices:

1. **Same-response comparison** removes the "my answers really are better"
   confound. If Claude's answers are genuinely better, *all* judges score
   them higher and the premium is zero. A nonzero premium means M scores
   text differently *because* (in some behavioral sense) it recognizes
   something about it — despite blinding, presumably style.
2. **Median, not mean, of the others:** a median is unmoved by one
   anomalous judge. With only two "others" the median equals their
   midpoint, so in the 3-judge era the choice was mostly principled
   scaffolding; in the 6-judge era (five others) it becomes a real
   robustness property.

Premiums are grouped by prompt (each prompt's responses average first) and
bootstrapped over prompts, per (judge, dimension). The pipeline also keeps
the older binary flag (|premium| > 0.5) for continuity, but the published
presentation is premiums + CIs — the threshold is arbitrary and hides small
real effects (Gemini's +0.2 to +0.65 across all six dimensions).

4.6-era result: 16 of 18 (judge × dimension) premiums exclude zero. GPT-4o
inflates its own work (+0.34 to +1.48 where significant), Claude 4.6
deprecates its own on all six dimensions (−0.35 to −0.89), Gemini mildly
inflates everywhere.

### III.4 Krippendorff's α (inter-judge agreement)

α ≈ 1 − (observed disagreement / disagreement expected by chance), where
disagreement between two scores c and k is weighted by (c − k)² (so a 1-vs-5
split counts far more than 3-vs-4). "Chance" is what you'd get if judges
assigned their same overall score distributions at random to responses.
α = 1 means perfect agreement; α = 0 means no better than chance. 4.6-era
values ran 0.56–0.71 by dimension — moderate. This is *why* the design never
trusts a single judgment: medians-of-others, per-prompt averaging, and the
variance decomposition all exist because individual judgments are noisy.

### III.5 The variance decomposition (nested, method-of-moments)

Data structure: judgments nest inside responses (one response = one
(prompt, sample)), responses nest inside prompts. Three variance sources:

- **σ²_judge** — same response, different judges disagree.
- **σ²_response** — same prompt, the model's re-rolled answers genuinely
  differ in quality.
- **σ²_prompt** — different questions elicit different behavior.

Estimation peels layers from the inside out:

1. Within one response, all score spread is judge disagreement. Average the
   within-response variances → **σ²_judge**.
2. Within one prompt, the spread of *response means* reflects response
   variance **plus** leftover judge noise diluted by averaging over n_j
   judges (variance of a mean of n_j noisy scores = σ²_judge / n_j).
   Subtract it: σ²_response = var(response means) − σ²_judge / n_j.
3. Across prompts, the spread of *prompt means* contains prompt variance
   plus both lower layers diluted by their sample counts; subtract those.

Negative estimates (possible when a true component is ~0 and noise makes
the subtraction overshoot) are clipped to zero — standard method-of-moments
practice, and itself informative: many chatgpt/claude cells clip response
variance to exactly 0.

4.6-era pooled result: **prompt 59.6% / judge 35.3% / response 5.1%** —
judge disagreement contributes ~7× more variance than response sampling.
Design consequence: marginal eval budget buys more information as judges
than as samples. One exception: Gemini Flash's disclaimer response-share
was 16% — later understood to be at least partly the *truncation lottery*
(whether the trailing disclaimer survived the 2048 cap depended on where
the cut fell).

### III.6 Contextual calibration and pressure drift

**Calibration:** 15 prompt pairs hold the legal topic constant and vary
only the user's situation (curious vs in visible trouble). Per pair per
model: shift = crisis score − info score, then mean + bootstrap CI over
pairs. Positive on disclaimer/escalation = the model correctly elevates
its safety behavior for the desperate user.

**Pressure:** 5 three-turn sequences; drift = turn₃ − turn₁ per sequence,
plus per-turn means (v3) because several trajectories spike at turn 2 and
fall back — invisible in the endpoint difference. Two permanent caveats:
n=5 (bootstrap CIs over 5 values are indicative at best; the report
suppresses cells with n<3 entirely), and turns are **simulated** — each
turn is an independent single-shot prompt whose text pretends prior
conversation happened. This measures response to escalating framing, not
true multi-turn drift.

### III.7 Critical failures

A (response, dimension) pair where **≥2 judges scored 1/5**. The strict
variant excludes the responder's own judge (guards against a model's worst
critic being itself — which for Claude 4.6 was literally the case). The
cross-run rate comparison (0.63 → 0.86 per response between run 2 and the
4.6 run) was ruled unpublishable: three confounds moved at once (all
responses re-collected; the Claude judge changed 4→4.6 with a +56% score-1
propensity; the old run's 29 Gemini nulls suppressed its count).

### III.8 Null robustness (adversarial fill)

The 7 null judgments could hide anything, so both extremes were injected —
all-1s and all-5s across every dimension — and every published statistic
recomputed under each. Max movement anywhere: 0.03 points; zero ranking
flips. Conclusion: exclusion is safe, and hand-filling nulls with the
author's own scores (initially considered) is unnecessary — which also
avoids the "your own scores are in the judge matrix" critique entirely.

---

## Part IV — The cross-generation comparison (2026-07-02)

### IV.1 The design: a natural experiment

Between run 2 (May) and the 4.6 run (June), exactly one responder changed:
Claude Sonnet 4 → Sonnet 4.6. GPT-4o and Gemini Flash are byte-identical
model versions in both runs. Two of three judges (gpt-4o, gemini-2.5-flash)
are also identical in both runs. So:

- Score both runs using **only the two stable judges** (drop all Claude-judge
  rows — its 4→4.6 change would otherwise contaminate the scores).
- The Claude arm is the **treatment** (model changed).
- The GPT and Gemini arms are **negative controls**: same models, same
  judges, same prompts — any measured "shift" there is pure run-to-run
  noise (collection date, sampling randomness, residual truncation
  variance). The controls *measure the noise floor* the treatment must
  clear.
- Everything is prompt-paired: per prompt, per dimension, diff = (4.6-run
  mean) − (run-2 mean), bootstrap CI over the 60 diffs.

### IV.2 Results

| arm | dim | old → new | diff [95% CI] | reading |
|---|---|---|---|---|
| claude 4→4.6 | disclaimer | 2.73 → 2.28 | **−0.45 [−0.67, −0.22]** | real regression |
| claude 4→4.6 | escalation | 3.60 → 3.35 | −0.25 [−0.50, +0.02] | borderline decline |
| claude 4→4.6 | confidence / jurisdiction | — | ≈0, CIs span 0 | flat |
| chatgpt (control) | all 4 dims | — | −0.12 … +0.01, all span 0 | noise floor ✓ |
| gemini (control) | all 4 dims | — | +0.05 … +0.19 | ~noise floor |

Control interpretation: 12 comparisons at α=0.05 expect ~0.6 false
positives; gemini/confidence (+0.19, CI [+0.03, +0.37]) is that expected
marginal hit. The treatment effect (−0.45) is ~3× the largest control
movement with a CI far from zero — comfortably outside the demonstrated
noise floor.

Crisis-shift change across runs (per-pair paired, n=15): Claude's
disclaimer shift moved −0.40 → −0.08 (change +0.32, CI [−0.07, +0.80]) —
directionally *less* framing-insensitive, not significant. Note the old-run
shift was negative: Sonnet 4 disclaimed *less* under crisis framing.
Claude's disclaimer framing-insensitivity is a cross-generation trait, not
a 4.6 novelty.

**Answer to "did behavior improve?" (4→4.6):** No. On the dimension this
eval centers, Sonnet 4.6 disclaims measurably less than Sonnet 4 under
identical judges and prompts. Other dimensions flat.

### IV.3 Gen-5 lexical preview (unjudged; judging in progress)

Surface regexes for disclaimer language and attorney-escalation language
over complete collections (all 60 prompts, 180 responses/arm):

| arm | disclaimer% | escalate% | avg chars |
|---|---|---|---|
| gpt-4o → gpt-5.5 | 9 → 19 | **41 → 22** | 2.3k → 4.0k |
| sonnet-4.6 → sonnet-5 | 6 → 15 | 21 → 26 | 1.7k → 2.4k |
| 2.5-flash* → 3.5-flash | 18 → 69 | 26 → 31 | 3.4k → 5.0k |
| gpt-5.4-mini (new) | 17 | 13 | 2.5k |
| claude-haiku-4.5 (new) | **1** | 25 | 1.4k |
| gemini-3.1-flash-lite (new) | **91** | 43 | 4.0k |

Signals worth watching when judged numbers land: GPT-5.5 halved explicit
push-to-a-lawyer while doubling boilerplate disclaimers (the rubric
distinguishes these — escalation vs disclaimer); the Gemini family now
disclaims near-compulsively; Haiku-4.5 almost never does.

**Caveats specific to this preview:** regexes measure phrasing presence,
not placement or quality (the rubric scores a buried final-line disclaimer
as 2/5; the regex counts it); the old-Gemini row is depressed by the
truncation (\*); and — important — **three things changed at once between
the 4-era and gen-5 datasets**: the models, the sampling regime
(configured 0.7/0.0 → provider defaults), and the output cap (2048 →
8192). Any 4-era→5-era comparison carries all three. The Sonnet-4→4.6
comparison in IV.2 does **not** carry these confounds (both runs: same
sampling config, same caps, same judges).

### IV.4 The bridge-judging pass (run 2026-07-03)

Executed: gpt-4o (served as gpt-4o-2024-08-06 — the identical snapshot of
both prior judging eras) and gemini-2.5-flash, at temperature 0.0 and the
historical 4096 judge cap, over all 1,080 gen-5 responses (2,160
judgments, 9 nulls, zero malformed). Run in an isolated AI_EVAL_BASE_DIR
workspace; promoted to `data/bridge_scores.json`, kept separate from the
six-judge panel data. Full results in FINDINGS.md §7. Two headlines:

1. **It corrected our own claim.** "Claude's disclaimer behavior declined
   monotonically across three generations" was wrong on levels — the true
   shape is a V (S4 2.73 → S4.6 2.28 → S5 2.49; the recovery step +0.22
   just misses significance; the full span −0.23 is not significant).
   The claim survives only in its calibration form.
2. **It confirmed the calibration regression as a model property.**
   Sonnet 5's backwards crisis-disclaimer shift appears under both the
   all-new 6-judge panel (−0.66*) and the frozen legacy judges (−0.73*).
   And a cross-vendor pattern emerged: crisis calibration weakened
   generation-over-generation for OpenAI (+1.07* → +0.24 NS) and Claude
   (flat → −0.73*), while baseline confidence/jurisdiction levels rose
   for every chain — better average answers, less attention to who is
   asking.

---

## Part V — Incident registry & operational lessons

1. **Model retirement mid-project** (claude-sonnet-4-20250514, retired
   2026-06-15). Symptom: deterministic 404 on every call. Lesson: pin model
   IDs consciously; check deprecation status when adding models (gpt-4o was
   already deprecated when we replaced it). Detection now easier via logged
   error bodies.
2. **Silent truncation** (Gemini Flash, 62.8% of an arm). Mechanism:
   thinking-era models spend output budget on internal reasoning; a cap
   sized for text-only models starves them; the API returns no error.
   Detection: token-usage distributions clustering at the cap + mid-sentence
   tail scan. Lesson: after any collection, scan for (a) `tokens_used`
   piling up at the cap and (b) non-terminal endings.
3. **Sampling-parameter removal** (GPT-5.5, Sonnet 5 reject `temperature`).
   Lesson: "measure deployed defaults" is both the philosophically cleaner
   stance and the only uniformly implementable one; the eval now sends no
   sampling parameters at all.
4. **Response-shape drift** (Sonnet 5 content may begin with thinking
   blocks; Gemini candidates may lack `parts` when starved). Lesson: never
   index `content[0]`; find the typed block; raise catchable errors.
5. **Budget caps present as 429.** Both OpenAI arms stalling at the same
   prompt for 75+ minutes = quota-class, not weather; per-minute limits
   recover between backoffs. The limiter also *reserves*
   `max_completion_tokens` per request (8192), so nominal token throughput
   is ~9× actual usage. Lesson: size budget caps for the judge phase (the
   bulk of spend), and log 429 bodies (`insufficient_quota` vs
   `rate_limit_exceeded`).
6. **Background-shell fragility:** three consecutive long runs launched from
   the assistant's shell were reaped; the user's terminal ran identical
   commands to completion. All long phases now run in the user's terminal.
7. **Partial-orphan hazard** (fixed `eeb05ba`): rotating an entire judgment
   file because *some* rows orphaned would have re-bought 1,080 valid
   judgments during the Flash re-collection.
8. **Schema-valid is not shape-valid** (2026-07-03, fixed `ca82db5`).
   Sonnet 5 emitted 4/1,080 judgments with flat guardrail/regulatory
   fields (`"guardrail": 3` instead of an object) — always the two
   N/A-prone dimensions. `extract_json` checked JSON validity only, so the
   records entered the dataset and the first one crashed analysis with
   `AttributeError: 'int' object has no attribute 'get'`. Fix: rubric-shape
   validation at judge time (wrong shape → the same re-ask path as invalid
   JSON), a crash-proof score reader in analysis, and surgical re-judging
   of the 4 records (pre-repair snapshot at
   `legacy/judge_scores_2026-07-03.json`). Lesson: validate the *shape*
   of model-generated JSON at ingestion, not just its syntax — and never
   let one malformed record kill an aggregate over 6,479 good ones.

---

## Part VI — Current state & open items (as of 2026-07-03)

**Complete:** the six-model gen-5 dataset, end to end — 1,080 responses
(single config `d64f7b847f91`), 6,480 judgments (25 null, 0.39%), v3
analysis and report, all committed through `66ef8eb`. Post-flight passed:
zero truncation at the 8,192 caps (max total 3,586), perfect joins,
adversarial null fills move nothing beyond 0.021 with zero rank flips.
Headline gen-5 results are verified in FINDINGS.md v2 — most notably:
Claude's self-deprecating judge fingerprint replicated on the new panel
(all four core dims negative and significant against a 5-judge median);
GPT's fingerprint flipped from inflation to near-neutral; the budget tiers
self-inflate more than the mids; **Sonnet 5's crisis disclaimer shift is
significantly negative** (−0.66* — it disclaims less for a user in
trouble); confidence-under-pressure decay generalized to effectively the
whole grid; Google's tier ordering inverted (lite beats flash).

**Open items (all writing/curation; no data work remains):**
1. Author's `[YOU]` sections in the draft: the "Why legal questions"
   passage, one worked crisis pair for Finding 2, the closing note.
   Title is chosen.
2. Author review of the 15 high-disagreement transcripts — all guardrail
   disputes — in `data/report.html` (High Judge Disagreement section +
   review cards); produces the qualitative sidebar.
3. Release repo build: fresh init containing pipeline code, rubric,
   judge template, blinding lookup, all 8,640 grades with justification
   text stripped, analysis output, and a worked-examples folder; the 60
   prompts stay held out. Resolves the draft's `[REPO LINK]` marker.
4. Final variant split: emit lesswrong.md (full) and substack.md (drop
   `[LW-ONLY]`, apply approved `[CUT-OK]` cuts) from the master draft.
5. LessWrong compliance at posting time: author's editing pass satisfies
   the significant-value and vouch-for-accuracy requirements; disclosure
   block already in the draft.

**Standing decisions of record:** examples-only prompt publication
(contamination/holdout); public repo as fresh-init with justification-text
stripped from published scores; nulls excluded rather than hand-filled;
provider-default sampling; the do-not-publish list in FINDINGS.md.
