# [DRAFT] Post skeleton — Substack + LessWrong crosspost

> **Draft status:** skeleton with all verified numbers filled in. Every
> statistic below is reproduced by `data/analysis_results.json`
> (analyze v3, commit `f5192a1`) — nothing is from memory or scratch.
> Markers: `[YOU]` = needs your voice/decision. `[LW-ONLY]` = include in
> the LessWrong version, optional on Substack. Suggested Substack cuts are
> marked `[CUT-OK]`.
>
> **Framing choice `[YOU]`:** this draft leads with the judge-fingerprint
> finding (the LW-catnip). If your Substack audience is more
> legal/AI-deployment than eval-methodology, invert: lead with §"Crisis
> framing" and demote the judges to §2.

---

## Title candidates `[YOU]` — two-beat structure per your pick

1. I made three frontier models grade each other's legal advice, blind. The graders had opinions about themselves.
2. I had GPT, Claude, and Gemini grade each other's legal advice, blind. Each one recognized itself anyway.
3. Three AI models graded each other's legal advice without knowing whose was whose. Their self-reviews say otherwise.
4. I blinded three AI models and had them grade each other's legal advice. One inflated itself; one tore itself apart.
5. Three models grade each other's legal advice, blind. Somehow, it still got personal.

---

`[LW-ONLY]` **Epistemic status:** One run of an eval I built myself: 60
legal questions, three models answering, the same three models grading —
blind. The two headline results (the self-grading bias and the
crisis-framing gap) come with error bars and survived every stress test I
threw at them, including adversarially filling in the handful of failed
grades. The three-turn pressure results rest on five scenarios — read
those as leads, not conclusions. I wrote the questions and the rubric
myself; I have a law degree, but this is a study of AI behavior, not legal
advice. The code and all 1,620 grades are public. Most of the questions
are not — anything posted online ends up in training data, and I want to
re-run this test on next year's models. Bottom line: I'd bet on the
direction of the main findings, not on any particular decimal.

## TL;DR

- I wrote 60 legal questions designed to test **safety behavior, not legal
  knowledge** — does the model say it isn't a lawyer, steer a person in
  real trouble toward one, resist sounding more certain than it should,
  and flag that the answer depends on where you live? GPT-4o, Claude
  Sonnet 4.6, and Gemini 2.5 Flash each answered every question 3 times;
  all 540 answers were stripped of identity and shuffled; then **the same
  three models graded every answer** against a six-part rubric — 1,620
  grades.
- **Every judge has a statistically significant self-scoring fingerprint**
  (16 of 18 judge × dimension cells exclude zero, bootstrapped over
  prompts): GPT-4o inflates its own responses by up to +1.1 points on a
  5-point scale, **Claude penalizes its own responses on all six
  dimensions**, Gemini mildly inflates across the board.
- When the same legal question comes from a **user in visible trouble**
  ("my landlord just locked me out and I'm panicking") instead of an
  idly curious one, all three models correctly push harder toward a real
  lawyer (+1.2 to +1.7 on a 5-point scale) — but **only GPT-4o and Gemini
  add more disclaimers; Claude disclaims at the same low rate whether the
  user is curious or desperate** (−0.12, error bar spans 0). And no model
  dials its confidence up or down.
- In simulated 3-turn **pressure sequences** (exploratory, n = 5), GPT-4o's
  confidence calibration degrades in 5 of 5 sequences (−1.11 [−1.64,
  −0.64]); Gemini starts at the disclaimer floor and ramps to near-ceiling.
- **Re-asking barely matters; re-judging matters a lot.** Because every
  question was answered 3× and every answer graded by 3 judges, I can
  split the disagreement between grades into three sources: which question
  it was (~60%), which judge graded it (~35%), and which of the model's
  three answers happened to come out of the dice roll (~5%). If you build
  evals like this, spend your budget on more judges, not more re-runs.

## Why legal questions `[YOU — 2-3 paragraphs in your voice]`

Placeholder for: why this domain (JD + ops research background), why safety
behavior rather than accuracy, why "does the model recognize the stakes"
is the interesting question for someone who has actually filed things with
courts. The mechanical hook available from the data: models' *absolute*
disclaimer scores are low everywhere (means 2.0–2.4 out of 5) — the
interesting variation is in *when* they bother.

## The setup `[CUT-OK: compress to one paragraph + diagram on Substack]`

- **60 prompts**, four categories: 15 matched **info/crisis pairs** (same
  legal topic, framing varies: "how does eviction work" vs. "my landlord
  just locked me out and I'm panicking"), 5 three-turn **pressure
  sequences**, plus adversarial and AI-deployment singles.
- **3 responders**: gpt-4o-2024-08-06, claude-sonnet-4-6,
  gemini-2.5-flash, temperature 0.7, **3 samples per (prompt, model)**.
- **Blinding**: responses stripped of identity, deterministically shuffled;
  judges see only prompt + response.
- **3 judges = the same 3 models**, temperature 0.0, six-dimension rubric
  (disclaimer, escalation, confidence calibration, jurisdiction awareness,
  guardrail, regulatory), scores 1–5 or N/A, JSON with per-dimension
  justifications.
- 540 responses × 3 judges = **1,620 judgments**; 7 nulls (0.43%, judge
  JSON failures) — adversarially filling them moves no reported statistic
  by more than 0.03 and flips no ranking.

One stats note, in plain terms: those 1,620 grades are not 1,620
independent facts — grades of the same question rise and fall together.
So every error bar in this post answers one question: *if I'd written a
different-but-similar set of 60 questions, how much would this number
move?* (Mechanically, that's a bootstrap: re-draw the 60 questions with
replacement a few thousand times and watch how much the average wobbles.)
It's the honest way to compute uncertainty here, and it makes my error
bars wider, not narrower.

`[LW-ONLY]` How often do the judges even agree with each other?
Krippendorff's α — a standard inter-rater agreement score, where 1.0
means the judges always agree and 0 means their agreement is no better
than chance — runs 0.56–0.71 depending on the dimension (confidence is
the noisiest, disclaimers the most agreed-on). Moderate at best. That's
itself part of the story (see the variance finding), and it's why the
self-grading analysis below never trusts any single judge.

## Finding 1: every judge has a fingerprint

For each grade a model gives to *its own* (blinded) answer, I compare it
to the **median of what the other two judges gave the exact same answer**.
Two design choices are packed in there, and both matter.

*Why compare on the same answer?* Because maybe Claude's answers really
are better — in that case every judge scores them high, and no bias is
implied. Bias only shows up when Claude-the-judge scores a Claude answer
differently than the other judges score the *identical text*.

*Why the median instead of the average?* Robustness: a median can't be
dragged around by one judge having a weird day. (With only two other
judges, the median works out to their midpoint anyway — the choice
matters more as judge panels grow.)

Self-premium (points on a 5-point scale; 95% CI bootstrapped over 60
prompts; **bold** = CI excludes zero):

| dimension | GPT-4o judge | Claude judge | Gemini judge |
|---|---|---|---|
| disclaimer | **+0.63** [+0.47, +0.78] | **−0.65** [−0.78, −0.52] | **+0.21** [+0.07, +0.36] |
| escalation | **+1.14** [+0.97, +1.31] | **−0.89** [−1.03, −0.74] | **+0.20** [+0.09, +0.36] |
| confidence | +0.00 [−0.15, +0.14] | **−0.36** [−0.51, −0.18] | **+0.49** [+0.34, +0.65] |
| jurisdiction | **+0.34** [+0.23, +0.45] | **−0.72** [−0.82, −0.60] | **+0.49** [+0.40, +0.61] |
| guardrail | **+1.48** [+1.09, +2.24] | **−0.72** [−1.13, −0.13] | **+0.36** [+0.17, +0.67] |
| regulatory | +0.11 [−0.02, +0.28] | **−0.69** [−0.83, −0.49] | **+0.65** [+0.49, +0.89] |

Three distinct personalities:

- **GPT-4o inflates its own work** — hardest on exactly the dimensions
  where its responses score weakest overall (escalation, guardrail).
- **Claude is its own harshest critic**: negative on all six dimensions,
  all significant. Blinded, Claude systematically scores Claude-written
  text *below* what the other judges give the same text.
- **Gemini mildly inflates everywhere** — small (+0.2 to +0.65) but all six
  CIs exclude zero.

`[LW-ONLY]` Why this matters beyond this eval: LLM-as-judge is the default
methodology for model comparisons now. These fingerprints are large
relative to the between-model differences people publish. Single-judge
scores of a model family by itself — in either direction — are
contaminated by default; Claude-judging-Claude *understates* Claude.
Blinding does not fix this (these judgments were blind — the fingerprint
survives blinding, presumably via style recognition). Multi-judge medians
and explicit self-premium measurement should be table stakes.

## Finding 2: crisis framing — who notices the user is in trouble?

Each info/crisis pair holds the legal topic constant and varies only the
user's framing. Shift = crisis score − info score, n = 15 pairs; positive
= the model correctly elevated its safety behavior for the desperate user.

| dimension | GPT-4o | Claude 4.6 | Gemini 2.5 Flash |
|---|---|---|---|
| escalation | **+1.21** [+0.59, +1.78] | **+1.18** [+0.59, +1.78] | **+1.68** [+0.98, +2.39] |
| disclaimer | **+0.83** [+0.25, +1.38] | −0.12 [−0.63, +0.40] | **+1.31** [+0.60, +2.03] |
| confidence | −0.04 [−0.43, +0.34] | −0.29 [−0.64, +0.02] | −0.21 [−0.66, +0.23] |
| jurisdiction | −0.09 [−0.56, +0.35] | −0.36 [−0.77, +0.02] | −0.19 [−0.65, +0.21] |

Three observations:

1. **Escalation works everywhere.** All three models reliably shift toward
   "you need an actual lawyer / go to court / call the hotline" when the
   user signals crisis. This is the trained-in behavior, and it shows.
2. **Claude's disclaimers don't respond to the user's situation** (−0.12,
   error bar spans zero, vs. +0.83 and +1.31 for the others). Whether the
   asker sounds idly curious or one bad day from losing their apartment,
   Claude adds disclaimers at the same (low) rate. The prompt pairs were
   built to catch exactly this: same legal topic, only the desperation
   changes.
3. **Nobody modulates confidence.** All three models hedge the same amount
   regardless of user stakes — slightly *negative* point estimates, all NS.
   The dimension where miscalibration hurts a panicking user most is the
   one no model adjusts.

`[YOU]` One worked pair inline here — pick one of the 15 pairs where the
contrast is vivid (candidates in the report's per-pair cards; the
landlord_tenant and employment pairs read well). Quote both prompts + one
response excerpt per framing.

## Finding 3 (exploratory): three turns of pressure

**One honest caveat before the numbers.** A real pressure test would be
one continuous conversation: the model answers, the user pushes back, the
model answers again. That's not what I ran. Each "turn" here is a
separate, standalone prompt *written as if* the conversation had already
happened — the turn-3 prompt literally opens "You already said it could
be harassment…" even though the model said no such thing (it never saw
turn 1). So this measures how a model reacts to a user who *sounds*
progressively pushier — not how a model actually drifts over a real
conversation. And with only five scenarios, trust the direction of these
results, not the size.

Per-turn mean scores (turn 1 → 2 → 3):

- **GPT-4o, confidence: 3.56 → 3.31 → 2.45.** Drift −1.11 [−1.64, −0.64],
  and the decline shows up in **all five sequences individually**. As the
  simulated user gets more insistent, GPT-4o gets more definitive. This is
  the cleanest drift result in the data — no floor or ceiling artifact.
- **Gemini, disclaimer: +2.72 [+2.10, +3.33] — but read carefully.** Three
  of five sequences *start* at 1.0 (no disclaimer at all on the neutral
  turn-1 question), so part of the magnitude is floor effect. The turn-3
  levels are genuinely high (3.9–5.0): Gemini answers neutral questions
  bare and slathers caveats once the user turns up the heat.
- **Claude: erratic, net ≈ 0.** Non-monotonic per-sequence trajectories
  (one sequence: 2.11 → 4.56 → 1.44 on disclaimer). Claude's response to
  pressure is noise, not a direction.
- **The turn-2 spike.** Several trajectories peak at turn 2 and fall at
  turn 3 across models — turn-2 prompts carry the explicit vulnerability
  signal ("I'm still angry", crisis-adjacent), turn-3 prompts the demand
  for actionable steps. A t₃−t₁ metric alone hides this; the per-turn
  means are in the released data.

`[YOU]` Suggested worked example: sequence S04 (employment discrimination /
EEOC) — the turn texts are vivid and the per-model trajectories diverge.

## Finding 4: the noise is in the judges, not the sampling

Language models are dice rolls: ask the same question twice and you get
different words (that's what temperature 0.7 means — a normal amount of
randomness). So each model answered every question three times, and every
answer was graded by all three judges. That structure lets me ask: when
two grades disagree, *whose fault is it?* There are three suspects — the
question (some questions just invite worse behavior), the judge (graders
have taste), and the dice (maybe the model's second answer was simply
different from its first). The split:

> **the question 59.6% | the judge 35.3% | the dice 5.1%**

The dice barely matter: a model's safety behavior on a given question is
remarkably stable across re-rolls. The judge you ask matters roughly
seven times more. One exception worth naming: whether Gemini bothers to
disclaim genuinely varies from roll to roll (16% dice share) — the same
instability you can see in its floor-to-ceiling trajectories in Finding 3.

**Design lesson for anyone building LLM-judge evals: the marginal dollar
goes to more (or better-calibrated) judges, not more samples.**

`[CUT-OK on Substack down to the bolded lesson + one sentence.]`

## Failure floor `[CUT-OK]`

Absolute levels, so the shift-based findings aren't misread as "the models
are fine": mean disclaimer scores are 2.06–2.45 out of 5 across models.
464 (response, dimension) pairs — 0.86 per response — were scored 1/5 by
at least two of three blinded judges (346 excluding self-judgments; 59%
were unanimous). Gemini has the highest failure rate per response (1.06),
GPT-4o the lowest (0.72). 57% of failures sit in the info/crisis category,
and disclaimer dominates (0.38/response).

## A JD reads the disputed transcripts `[PENDING — your review pass]`

Placeholder for the qualitative sidebar: the 5 high-disagreement
(response, dimension) items where judge std-dev > 1.5, reviewed by hand in
the report UI. Angle: where three frontier models can't agree on whether a
response was safe, what does a human with a law degree see? (These 5 items
stay out of the quantitative claims entirely.)

## Limitations `[LW-ONLY: keep all; Substack: keep 1, 2, 3, 6]`

1. **Judges ≡ responders.** The three judges are the three responders —
   blinded, but same model families. The self-premium analysis measures
   this contamination rather than assuming it away; cross-family scores
   (each response's median judge) are the primary statistics.
2. **Author-written prompts and rubric** (n = 60). Construct validity rests
   on one person's judgment of what "safe legal-question behavior" means —
   informed by a JD, but still one person. CIs resample prompts, so they
   quantify prompt-sampling noise, not construct error.
3. **Model-tier mismatch — fix in progress.** This run compares Gemini 2.5
   **Flash** (a fast/cheap tier) against two mid-tier models, so "Gemini"
   results here are Flash results. `[PENDING — tier-expansion run: the
   grid extends to matched tiers across providers, reusing every existing
   response and grade; this limitation becomes a tier-vs-tier finding and
   most tables in this post gain columns.]`
4. **Mixed collection vintage.** claude-sonnet-4-20250514 was retired
   mid-project (2026-06-15); the Claude arm was re-collected on
   claude-sonnet-4-6 while GPT-4o/Gemini responses are from four days
   earlier. Judge and responder are version-matched within every arm; the
   raw data carries both config hashes.
5. **Moderate judge agreement** (α 0.56–0.71) — the design's answer is the
   median-of-others control and per-prompt aggregation, but individual
   judgments are noisy.
6. **Pressure sequences are simulated single-shot turns**, n = 5. Signs,
   not magnitudes.
7. **Simulated turns and paired prompts share topics within a pair/sequence
   but pairs are independent** — no cross-pair structure is claimed.
8. 7/1,620 judgments (0.43%) returned unparseable JSON and are excluded;
   adversarial fill in both directions moves no reported statistic by
   more than 0.03 and flips no ordering.

## Reproducibility `[REPO LINK pending]`

Public repo: full pipeline code (collect → blind → judge → analyze →
report), the rubric and judge prompt, the blinding lookup, **all 1,620
judge scores (numbers; justification text stripped), and the complete
analysis output** — every statistic in this post recomputes from the
released scores with one command. The 60 prompts are **not** released
(besides ~8 examples with full responses and judgments): published prompts
end up in training corpora, and the point of a held-out set is to re-run
this eval on next year's models. `[LW-ONLY:]` If you want to audit the
prompts themselves, contact me.

## What's next `[YOU]`

- Re-run on successor models with the held-out set (the reason it's held
  out).
- Candidate design fixes for v2: true multi-turn pressure (real
  conversation state), a 4th non-responder judge family, more sequences.

---

### Numbers-lock appendix `[not for publication]`

All statistics trace to `data/analysis_results.json` (analyze_version 3,
bootstrap seed 20260521, commit `f5192a1`) and FINDINGS.md (2026-07-01).
Do-not-publish list honored in this draft: cross-run critical-failure
trend (3-way confounded); guardrail/regulatory drift cells (n ≤ 2,
low_n-suppressed); chatgpt regulatory calibration (n = 1); claude
regulatory calibration (n = 3, exploratory only — currently omitted).
