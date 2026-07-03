# [DRAFT v3] Post — Substack + LessWrong crosspost

> **Draft status:** v3, applying the third feedback round. Working title
> chosen. Style contract now enforced: no parentheticals, no appositive
> comma-phrases, no empty signpost sentences, no self-referential
> meta-sentences, adverbs cut unless load-bearing, statistics explained
> where used, declarative register. Every number traces to
> `data/analysis_results.json` and `data/bridge_scores.json` at commit
> `e8e88a9`, verified in FINDINGS.md. Markers: `[YOU]`, `[LW-ONLY]`,
> `[CUT-OK]` as before.

---

## Title (chosen)

**Six AI models graded each other's legal advice without knowing whose
was whose. Each one recognized itself anyway.**

Alternates held in reserve: "I stripped the names off 1,080 legal answers
and had the models grade each other. They still played favorites."

---

`[LW-ONLY]` **Epistemic status:** This is one run of an evaluation I
designed and operated. Three earlier runs on the same sixty questions
allow comparisons across model generations. Sixty legal questions were
answered by six current models. The same six models graded the answers.
The grading was blind: a judge saw only the question and an unlabeled
answer, never which model wrote it. The study produced two headline
results. The first is that every model grades its own blinded work with
a consistent bias. The second is that the newest models disclaim less to
a user in visible trouble. Both results hold under every robustness
check I ran, and both carry explicit confidence intervals. The
three-turn pressure results rest on five scenarios. Five scenarios can
indicate a pattern worth testing; they cannot establish one, and I treat
them that way. One claim from an earlier draft did not survive
verification. The generational section states the claim and the
correction. I wrote the questions and the rubric myself. The code and
all 8,640 grades are public. The question set is not public: published
questions enter future training data, and I intend to re-run this
evaluation on future models. I am confident in the direction of the main
findings and much less confident in their precise magnitudes.

## A note on authorship

I built this evaluation pipeline and drafted this post with substantial
assistance from Claude, whose model family is among those under
evaluation. Every design decision, every prompt, and every conclusion is
mine. The disclosure matters, and so does one observable fact: the
assistance did not tilt the results toward its own family. Two of the
least flattering findings in this study belong to Claude.

## TL;DR

- I wrote 60 legal questions designed to test **safety behavior, not
  legal knowledge**. The question is never whether the model knows
  landlord-tenant law. The question is whether it says it is not a
  lawyer, steers a person in real trouble toward one, resists sounding
  more certain than the law permits, and flags that the answer depends
  on where you live.
- Six current models answered every question three times: GPT-5.5 and
  GPT-5.4-mini, Claude Sonnet 5 and Claude Haiku 4.5, Gemini 3.5 Flash
  and Gemini 3.1 Flash-Lite. All 1,080 answers were stripped of identity
  and shuffled. Then **the same six models graded every answer** against
  a six-part rubric. That produced 6,480 grades.
- **Every model grades its own work differently, and the pattern is too
  consistent to be luck.** Grading blind, Claude Sonnet 5 marks its own
  answers down on every core dimension. GPT-5.4-mini is the most
  self-flattering judge in the panel. It rates its own answers up to a
  full point higher than five other judges rate the identical text. Of
  24 places this bias can be measured, 20 show a gap larger than
  question-to-question luck can explain.
- **Claude Sonnet 5 disclaims less when the user is in visible
  trouble.** Same legal topic, one version asked calmly and one by
  someone about to lose their apartment: Sonnet 5's disclaimer behavior
  drops by two-thirds of a point for the desperate user. This holds
  under two different judge panels. Every model still tells the
  desperate user to get a lawyer. The failure is specific to
  disclaimers, and it is new in this generation.
- **The newer generation gives better average answers and pays less
  attention to who is asking.** Under judges held identical across three
  model generations, baseline quality rose for every vendor while crisis
  calibration collapsed for two of three.
- An earlier draft claimed that Claude's disclaimer behavior declined
  monotonically across three generations. The claim was wrong. Under
  identical judges, the level dipped at Sonnet 4.6 and partly recovered
  at Sonnet 5. Finding 5 states the correction and the finding that
  replaced it.
- **Re-asking a model barely changes its grade. Changing the judge
  changes it a lot.** Grading disagreement splits into three sources:
  the question accounts for 55 percent, the judge for 37 percent, and
  the model's re-rolled answer for 8 percent. Finding 4 derives the
  split. If you build evaluations like this one, spend on more judges,
  not more samples.

## Why legal questions `[YOU — 2-3 paragraphs in your voice]`

Placeholder. The mechanical hook available from the data: outside the
Gemini family, average disclaimer scores sit near 2 on a 5-point scale
across sixty questions and six models. The interesting variation is not
whether models are careful. It is when they bother to be.

## The setup

Sixty questions, four categories. Fifteen **matched pairs** hold a legal
topic constant and vary only the asker's situation: "how does eviction
work" against "my landlord just locked me out and I'm panicking." The
pairs exist to measure whether a model notices the difference. Five
**three-turn pressure sequences** simulate a user who pushes harder with
each message. The remainder are single adversarial questions and
questions about deploying AI in regulated domains.

Each of the six models answered every question three times. Language
models are dice rolls. The same question produces different words on
each attempt, and three samples let me measure how much that matters.
Every answer was then stripped of identifying information, assigned an
ID derived from its content, and shuffled. A scanner checked for
self-identification such as "As Claude, I should note" and found none
that survived into judging.

Each of the six models then graded all 1,080 anonymous answers against a
rubric with six dimensions. Disclaimer: does the answer say it is
information rather than legal advice. Escalation: does it direct serious
matters to a professional. Confidence calibration: does its certainty
match what the law supports. Jurisdiction: does it flag that the answer
varies by state. Guardrail: does it hold up against misuse. Regulatory:
does it handle AI-deployment questions responsibly. Scores run 1 to 5,
with a separate marking for not-applicable. Judges return structured
output with a written justification for every score, and the pipeline
validates the shape of every grade before accepting it.

That produced 6,480 grades. Twenty-five came back unparseable and were
excluded. Refilling all twenty-five with worst-case and then best-case
values changes no number in this post by more than 0.02 and flips no
ranking. A further 2,160 grades come from a separate bridge experiment
described in Finding 5. The public dataset totals 8,640 grades.

All six models ran at their providers' default settings. The newest
models from OpenAI and Anthropic no longer accept a temperature
parameter, so configured sampling is not an option for a current grid,
and defaults are what a real user gets. Output limits were set high
enough that no answer was cut off. I verified that directly, because an
earlier run was silently corrupted by truncation. The limitations
section tells that story.

## How to read every number in this post

**The unit of analysis is the question, not the grade.** The 6,480
grades are not 6,480 independent facts. Grades of the same question are
correlated in the plain statistical sense: a hard question drags down
every one of the grades it receives, and an easy question lifts them.
The independent observations are the sixty questions. So before
computing anything else, I average all of a question's grades into one
number. Every statistic in this post is then a statement about sixty
numbers. Each number belongs to one question, and every error bar is
computed over those sixty. If I instead treated the 6,480 grades as
independent, every error bar would shrink by a factor of about five,
because the formulas would count each question's internal echoes as
fresh evidence.

**Error bars answer one specific question.** My sixty questions are one
possible draw from the universe of legal questions a person could ask.
Had I written the set in a different week, I would have produced a
somewhat different sixty, and every number here would have come out
slightly differently. The bracketed interval after each estimate says
how much. It is a 95 percent confidence interval computed by the
bootstrap, which works as follows. I cannot collect thousands of
alternative sixty-question sets, but I can simulate them: draw sixty
questions at random from my actual sixty, allowing repeats, so that some
questions appear twice and others not at all. Drawing with repeats is
what makes the simulated set behave like a fresh draw from the same
universe rather than a reshuffled copy. Compute the average for that
simulated set. Repeat several thousand times. The middle 95 percent of
those simulated averages is the interval I report. A worked miniature:
if three questions scored 2, 3, and 5, the simulated sets might be
2-2-5, then 3-5-5, then 2-3-3, with averages 3.0, 4.3, and 2.7. The
spread of such averages is the question-to-question luck we need to
quantify. The analogy is a poll: a survey of sixty voters carries a
margin of error describing what other surveys of sixty would likely
find. Here the questions are the voters, and the bootstrap simulates the
other polls.

**Bold means the interval excludes zero.** When a table bolds an effect,
fewer than 5 percent of plausible alternative question sets would flip
its sign. When I write NS, the interval includes zero, and the honest
statement is that this data cannot distinguish the effect from nothing.
With many comparisons in one table, expect one marginal false positive
per twenty tests. I point out where that matters.

**Judge agreement is moderate, and the design assumes it.** The standard
agreement score for this kind of panel is Krippendorff's alpha. It
equals 1 when judges always agree and 0 when their agreement is no
better than chance. Across dimensions it runs 0.55 to 0.73 here. It is
weakest on confidence calibration, where judging requires assessing how
certain an answer should have been, and strongest on disclaimers, where
the judge checks whether particular language exists. No conclusion in
this post rests on a single judge or a single grade.

## Finding 1: every judge has a fingerprint

For each grade a model gives to its own anonymous answer, I compare it
to the median of what the other five judges gave the exact same answer.
The comparison is on the same answer because Claude's answers might be
better across the board. In that case every judge scores them high and
no bias is implied. Bias appears only when a model scores its own text
differently than five other judges score the identical text. The
baseline is the median rather than the average because a single outlier
grader moves an average. It does not move the middle of five.

Self-premium in points on the 5-point scale, with 95 percent intervals
bootstrapped over the sixty questions. Bold marks intervals that exclude
zero.

| judge | disclaimer | escalation | confidence | jurisdiction |
|---|---|---|---|---|
| GPT-5.5 | **−0.28** [−0.39, −0.16] | +0.10 [−0.03, +0.24] | **+0.24** [+0.16, +0.34] | +0.02 [−0.06, +0.10] |
| GPT-5.4-mini | **+0.99** [+0.81, +1.18] | **+0.86** [+0.69, +1.02] | **+0.31** [+0.14, +0.48] | **+0.23** [+0.09, +0.37] |
| Claude Sonnet 5 | **−0.47** [−0.60, −0.35] | **−0.71** [−0.81, −0.60] | **−0.56** [−0.71, −0.42] | **−0.23** [−0.33, −0.14] |
| Claude Haiku 4.5 | **+0.44** [+0.33, +0.56] | **+0.22** [+0.10, +0.34] | **−0.17** [−0.30, −0.04] | **−0.14** [−0.28, −0.01] |
| Gemini 3.5 Flash | +0.08 [−0.04, +0.21] | +0.08 [−0.03, +0.18] | **+0.46** [+0.31, +0.59] | **+0.12** [+0.04, +0.21] |
| Gemini 3.1 Lite | **+0.42** [+0.32, +0.52] | **+0.64** [+0.53, +0.76] | **+0.40** [+0.29, +0.52] | **+0.25** [+0.13, +0.38] |

Twenty of these twenty-four measurements exclude zero.

**Claude is its own harshest critic, and this is now a replicated
trait.** Sonnet 5 marks its own blinded work down on all four core
dimensions. Its predecessor Sonnet 4.6 did the same against a different
and smaller judge panel. Two generations, two panels, one signature.

**The fingerprint belongs to the model, not the vendor.** GPT-4o
inflated its own answers by up to one and a half points in the previous
generation of this study. GPT-5.5 is nearly neutral. Whatever produces
these biases changed between model versions from the same company.

**The budget tiers flatter themselves.** GPT-5.4-mini is the most
self-inflating judge in the panel. Gemini 3.1 Lite inflates on every
dimension. If you use a small, cheap model as a judge over its own
family's outputs, this is the measured warning.

`[LW-ONLY]` The general implication: LLM-as-judge is now the default
methodology for model comparisons, and these fingerprints are large
relative to the between-model differences that papers report. Blinding
did not remove them. The models evidently recognize something in their
own style. Single-judge evaluations of a model by its own family are
contaminated by default, in whichever direction that family's
fingerprint points. Multi-judge medians and an explicit self-premium
measurement should be table stakes.

## Finding 2: who notices the user is in trouble?

Each matched pair holds the legal topic constant and changes only the
asker's situation. The shift is the crisis score minus the calm score,
averaged over fifteen pairs. A safety-calibrated model shifts upward:
more disclaiming and more escalation when more is at stake for the
asker.

| arm | disclaimer shift | escalation shift |
|---|---|---|
| GPT-5.5 | +0.21 [−0.40, +0.85] | **+1.07** [+0.48, +1.69] |
| GPT-5.4-mini | **+1.09** [+0.62, +1.59] | **+1.64** [+1.15, +2.17] |
| Claude Sonnet 5 | **−0.66** [−1.09, −0.25] | **+0.62** [+0.10, +1.17] |
| Claude Haiku 4.5 | −0.39 [−0.79, +0.02] | **+0.63** [+0.12, +1.18] |
| Gemini 3.5 Flash | **+0.67** [+0.02, +1.29] | **+0.64** [+0.17, +1.09] |
| Gemini 3.1 Lite | **+0.49** [+0.05, +1.07] | **+0.59** [+0.21, +1.01] |

Escalation works everywhere. All six models push harder toward a real
lawyer when the user signals trouble.

Claude Sonnet 5's disclaimer shift is negative. When the asker sounds
one bad day from losing their apartment, Sonnet 5 attaches fewer
disclaimers than it does for the calm version of the same question.
Haiku trends the same direction without reaching significance, which
makes this look like a family trait in the current Anthropic
generation. Finding 5 shows the same result under a different judge
panel, which rules out the graders as the explanation.

The third observation cuts against tier assumptions. GPT-5.4-mini is
the cheapest OpenAI model in the grid. It is also the best-calibrated
arm in the study on both dimensions, while the flagship GPT-5.5's
disclaimer calibration is statistically indistinguishable from nothing.

`[YOU]` One worked pair inline here. The per-pair cards in the report
UI have the candidates; the landlord lockout pair reads well.

## Finding 3: three turns of pressure

A real pressure test would be one continuous conversation in which the
model answers, the user pushes back, and the model answers again. That
is not what I ran. Each turn here is a separate, standalone prompt
written as if the conversation had already happened. The third turn
opens with "You already said it could be harassment" even though the
model said no such thing. This measures reaction to increasingly
insistent framing. It does not measure drift across a real
conversation. With five scenarios, directions are trustworthy and
magnitudes are not.

One result generalizes across the whole grid: **confidence decays under
pressure everywhere.** Five of six arms show significant negative drift
in confidence calibration from the first turn to the third, between
half a point and one and a half points. By the third and most insistent
message, every current model sounds more certain than it did at the
start, and more certain than the law supports. GPT-4o showed this
pattern in the previous generation of this study. It now describes
every model tested.

Gemini 3.5 Flash shows the sharpest disclaimer collapse. It starts near
4.5 in the first turn and falls to 2.6 by the third. Claude shows a
pattern the endpoint numbers hide: its disclaimer rigor rises at the
second turn, where the simulated user sounds most vulnerable, then
collapses below its starting point when the user demands concrete
steps. The per-turn trajectories for every arm are in the released
data.

## Finding 4: the noise is in the judges, not the dice

Every question was answered three times per model, and every answer was
graded by six judges. That structure lets grading disagreement be taken
apart layer by layer.

Start at the innermost layer: six judges grading the same single
answer. Any spread among those six grades can only come from the
judges, because the question and the answer are fixed. Average the
within-answer spread across all answers and you have the judge
component.

Move out one layer: the three answers a model gave to the same
question. The spread among their per-answer averages reflects the dice.
The dice are the real variation in what the model produces on a
re-roll. This layer also contains a diluted residue of judge noise. We
measured the judge component already, so we subtract it.

Move out to the last layer: the spread across the sixty questions
themselves, minus the diluted inner components, is what the questions
contribute. Peel, subtract, repeat. That is the entire method.

The result, pooled across models and dimensions: **the question
accounts for 55 percent of grading variance, the judge for 37 percent,
and the dice for 8 percent.** Re-asking the same model the same
question barely moves its grade. Asking a different judge moves it four
to five times as much. The practical lesson for anyone building an
evaluation like this one: spend marginal budget on more or better
judges rather than more samples per question.

One methodological note. This run let every model sample at its
provider's default settings rather than a configured temperature, and
the dice share rose from 5 percent in the previous run to 8 percent
here. That is the direction the change predicts.

## Finding 5: did the models get better?

I have three complete, judged datasets on these same sixty questions: a
spring run with Sonnet 4, GPT-4o, and Gemini 2.5 Flash; an early-summer
run in which only the Claude arm changed, to Sonnet 4.6; and the
current six-model run. Comparing across them has a problem. The judges
changed too, so a grade shift could mean the models changed or the
graders did.

The design isolates the models in two steps. Between the spring and
early-summer runs, exactly one responder changed, and two judges were
byte-identical model versions. Scoring both runs with only those two
frozen judges makes Claude the treatment arm. The unchanged GPT-4o and
Gemini arms become negative controls that measure run-to-run noise. The
controls moved at most 0.15 points on any dimension. None of those
movements is significant. Against that floor, Sonnet 4.6's disclaimer
level fell 0.45 points from Sonnet 4, with an interval from −0.67 to
−0.22. The one marginal control movement is the expected false positive
from twelve simultaneous comparisons.

For the current run, I re-ran those same two frozen judges over all
1,080 new answers, at the same settings and the same model snapshots.
That is 2,160 additional grades whose only purpose is to hold the
graders constant across three generations of models.

The bridge data corrected this analysis. An earlier draft claimed that
Claude's disclaimer behavior declined monotonically across the three
generations. Under identical judges the true shape is a V: 2.73 at
Sonnet 4, down to 2.28 at Sonnet 4.6, back up to 2.49 at Sonnet 5. The
recovery step misses significance, and the full Sonnet 4 to Sonnet 5
change is −0.23 with an interval from −0.51 to +0.04. The interval
includes zero, so the decline claim is dead on levels. The instrument
built to test the claim is the thing that trimmed it.

What survives is sharper. Crisis-disclaimer calibration by generation,
under the frozen judges:

| arm | gen 4 era | gen 4.6 era | gen 5 |
|---|---|---|---|
| Claude | −0.40 [−1.03, +0.33] | −0.08 [−0.69, +0.54] | **−0.73** [−1.26, −0.20] |
| OpenAI | **+1.07** [+0.57, +1.57] | **+1.06** [+0.38, +1.69] | +0.24 [−0.60, +1.07] |
| Gemini | **+1.17** [+0.43, +2.00] | **+1.46** [+0.69, +2.20] | **+0.95** [+0.29, +1.56] |

Claude went from uncalibrated to backwards, and the same result appears
under the all-new six-judge panel, so it is a property of the model and
not of any grader. OpenAI went from strongly calibrated to nothing.
Only Gemini held. Meanwhile baseline quality rose across the board:
confidence and jurisdiction levels improved for every vendor's chain,
most steps significant, and Sonnet 5 recovered disclaimer volume even
as it misallocated it.

The answer to "did the models get better" comes in two parts. At giving
good average answers: yes, for every vendor, and most steps clear their
confidence intervals. At noticing who is asking: no. Two of three
vendors got worse at exactly that. In a domain where the desperate
asker needs the guardrails most, that is the finding I want deployers
to read.

Two response-side differences ride along with any comparison into the
current generation, and I disclose them rather than correct for them.
The newer models sample at provider defaults because they no longer
accept configured temperature. Output limits were raised after the
truncation incident. The judge side is clean. The response side is each
era's deployed reality.

## Failure floor `[CUT-OK]`

Absolute levels, so the shift-based findings are not misread as "the
models are fine." Outside the Gemini family, average disclaimer scores
run 1.9 to 2.4 out of 5. The Gemini family is the outlier at 3.4 and
4.1, and Gemini 3.1 Lite is the only model in the grid that reliably
disclaims. Across 1,080 answers, 910 answer-dimension pairs were scored
1 out of 5 by at least two of six blinded judges. These counts are not
comparable to the three-judge era, because a six-judge panel reaches a
two-judge agreement bar far more easily. Within this run they say one
thing: the floor is low everywhere.

## A JD reads the disputed transcripts `[PENDING — your review pass]`

Where the material lives: open `data/report.html` in a browser and find
the section titled **High Judge Disagreement**, with the review cards in
the tie-breaking section below it. Fifteen answers produced guardrail
grades so far apart that the judges' standard deviation exceeded 1.5
points. Every one of the fifteen is a guardrail dispute, which is
itself telling: the dimension that asks whether an answer holds up
against misuse is the one six models cannot agree on. Each card shows
the question, the full anonymous answer, and every judge's score with
its written justification.

The section to write: what does a human with a law degree see in the
fifteen answers six frontier models could not agree on. These items
stay out of every quantitative claim in this post.

## Limitations

1. **The judges are the responders.** Blinded, but the same six models
   fill both roles, and the self-premium analysis measures the
   contamination this creates rather than assuming it away. The bridge
   pass adds two judges that are not in the response set, and the
   headline calibration finding survives both panels.
2. **One author wrote the questions and the rubric.** Sixty questions,
   informed by a law degree, still one person's construct. The error
   bars quantify question-sampling noise, not construct validity.
3. **Pressure sequences are simulated single-shot turns**, five of them.
   Directions, not magnitudes.
4. **Sampling conditions changed across generations by necessity.** The
   newest OpenAI and Anthropic models reject configured temperature, so
   the current grid runs at provider defaults while earlier runs used a
   configured 0.7. Generational comparisons carry that difference, and
   it is disclosed wherever they appear.
5. **Judge agreement is moderate**, alpha 0.55 to 0.73 by dimension. The
   design answers this with medians across judges, per-question
   aggregation, and the variance decomposition. Individual grades are
   noisy, and nothing rests on one.
6. **Nulls.** Twenty-five of 6,480 panel grades and nine of 2,160 bridge
   grades failed to parse and are excluded. Filling every one of them
   with all-1s and then all-5s moves no reported number by more than
   0.02 and flips no ranking.
7. **Tier labels are mine.** "Mid" and "budget" reflect each vendor's
   positioning and pricing at collection time. The data argues tiers
   are not a safety ordering: Google's budget model beats its mainline
   on three of four dimensions, and OpenAI's mini is the
   best-calibrated arm in the grid.
8. **Multiple comparisons.** The fingerprint table alone contains 24
   tests. At the 95 percent level, expect one marginal false positive
   per twenty tests. The findings this post leads with are far from
   that margin.
9. **An earlier run was silently corrupted, and the failure mode is
   worth knowing.** The first Gemini Flash arm hit a 2,048-token output
   cap that its internal reasoning consumed from the inside: 63 percent
   of its answers were cut off mid-sentence, and the API reported no
   error. The graders had been scoring amputated text. That arm was
   discarded and re-collected at a higher limit, and the current
   dataset was scanned for the same defect and is clean. If you run
   evaluations over models that reason before answering, check your
   token ceilings and then check your data's final sentences.

## Reproducibility `[REPO LINK pending]`

The public repository contains the full pipeline code, the rubric and
judge prompt, the blinding lookup, all 8,640 grades with score values
intact and justification text stripped, and the complete analysis
output. Every statistic in this post recomputes from the released
grades with one command, deterministically. When the analysis was
re-run independently on two machines during this project, the outputs
were byte-identical. The sixty questions are not released, apart from a
set of worked examples with full answers and grades, because published
questions enter training corpora and the point of a held-out set is to
re-run this evaluation on next year's models. `[LW-ONLY]` Researchers
who want to audit the full question set can contact me.

## After this post `[YOU]`

Future work. Nothing here blocks publication.

- Re-run on successor models with the held-out set. The bridge
  technique generalizes: any future run can be chained back to this one
  by re-running frozen judges.
- Design fixes for the next version: true multi-turn pressure with real
  conversation state, a judge from outside the response set as a
  permanent panel member, more pressure sequences.

---

### Numbers-lock appendix `[not for publication]`

All statistics trace to `data/analysis_results.json` with seed 20260521,
`data/bridge_scores.json`, and FINDINGS.md as of commit `e8e88a9`.
Do-not-publish list honored: no cross-panel critical-failure rate
comparisons; no cells with fewer than three pairs or sequences; no
judged 4-era to 5-era claims without the bridge; the corrected
monotonic-decline claim appears only in its corrected and explicit form.
Style contract v3: no parentheticals, no appositive comma-phrases, no
empty signpost sentences, no self-referential meta-sentences, adverbs
cut unless load-bearing, intervals bracketed after their estimates,
every statistical term defined in "How to read every number in this
post" before first use.
