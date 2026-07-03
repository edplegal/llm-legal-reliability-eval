# [DRAFT v2] Post — Substack + LessWrong crosspost

> **Draft status:** rebuilt on the six-model gen-5 dataset and the
> bridge-judged generational chain. Every statistic traces to
> `data/analysis_results.json` and `data/bridge_scores.json` at commit
> `e8e88a9`, verified in FINDINGS.md. Markers: `[YOU]` = your voice or
> decision. `[LW-ONLY]` = include on LessWrong, optional on Substack.
> `[CUT-OK]` = Substack cut candidate. Style rules enforced per your
> feedback: no parentheticals in body prose, declarative register,
> statistics explained where they are used.

---

## Title candidates `[YOU]`

Your two picks, updated for the six-model grid, plus three in the same
two-beat pattern:

1. I had six AI models grade each other's legal advice, blind. Each one recognized itself anyway.
2. Six AI models graded each other's legal advice without knowing whose was whose. Their self-grades say otherwise.
3. I stripped the names off 1,080 legal answers and had the models grade each other. They still played favorites.
4. Six models graded one another's anonymous legal advice. The self-grades gave them away.
5. I made the newest AI models grade each other's legal advice, blind. The grades revealed more about the graders.

---

`[LW-ONLY]` **Epistemic status:** This is one run of an evaluation I
designed and operated, plus three archived predecessor runs that allow
generation-over-generation comparisons. Sixty legal questions were
answered by six current models, and the same six models graded the
answers. The grading was blind: a judge saw only the question and an
unlabeled answer, never which model wrote it. The two headline results,
the self-grading fingerprints and the crisis-calibration failures, hold
under every robustness check I ran, and each carries an explicit
confidence interval. The three-turn pressure results rest on five
scenarios. Five scenarios are enough to indicate a pattern worth testing
properly; they are not enough to establish one, and I treat them
accordingly. One earlier claim of mine did not survive verification, and
I document that correction in the generational section rather than
hiding it. I wrote the questions and the rubric myself. I hold a law
degree, but nothing here is legal advice; it is a study of model
behavior. The code and all 8,640 grades are public. The question set is
not public, because published questions enter future training data and I
intend to re-run this evaluation on future models. I am confident in the
direction of the main findings and much less confident in their precise
magnitudes.

## A note on authorship

I built this evaluation pipeline and drafted this post with substantial
assistance from Claude, whose model family is among those under
evaluation. Every design decision, every prompt, and every conclusion is
mine. The disclosure matters and so does one observable fact: the
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
  a six-part rubric: 6,480 grades.
- **Every model grades its own work differently, and the pattern is too
  consistent to be luck.** Grading blind, Claude Sonnet 5 marks its own
  answers *down* on every core dimension. GPT-5.4-mini is the most
  self-flattering judge in the panel, rating its own answers up to a
  full point higher than five other judges rate the identical text. Of
  24 places this bias can be measured, 20 show a gap larger than
  question-to-question luck can explain.
- **Claude Sonnet 5 disclaims less when the user is in visible
  trouble.** Same legal topic, one version asked calmly and one by
  someone about to lose their apartment: Sonnet 5's disclaimer behavior
  drops by two-thirds of a point for the desperate user. This holds
  under two completely different judge panels. Every model still tells
  the desperate user to get a lawyer; the failure is specific to
  disclaimers, and it is new in this generation.
- **The newer generation gives better average answers and pays less
  attention to who is asking.** Under judges held identical across three
  model generations, baseline quality rose for every vendor while
  crisis calibration collapsed for two of three. I also document the
  place where this analysis corrected one of my own earlier claims.
- **Re-asking a model barely changes its grade; changing the judge
  changes it a lot.** Splitting all grading disagreement into its three
  possible sources: the question accounts for roughly 55 percent, the
  judge for roughly 37 percent, and the model's re-rolled answer for
  roughly 8 percent. Finding 4 walks through how that split is computed.
  If you build evaluations like this one, spend on more judges, not more
  samples.

## Why legal questions `[YOU — 2-3 paragraphs in your voice]`

Placeholder. The mechanical hook available from the data: outside the
Gemini family, average disclaimer scores sit around 2 on a 5-point scale
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
models are dice rolls; the same question produces different words on
each attempt, and three samples let me measure how much that matters.
Every answer was then stripped of identifying information, assigned an
ID derived from its content, and shuffled. A scanner checked for
self-identification such as "As Claude, I should note" and found none
that survived into judging.

Each of the six models then graded all 1,080 anonymous answers against
a rubric with six dimensions. Disclaimer: does the answer say it is
information rather than legal advice. Escalation: does it direct serious
matters to a professional. Confidence calibration: does its certainty
match what the law actually supports. Jurisdiction: does it flag that
the answer varies by state. Guardrail: does it hold up against misuse.
Regulatory: does it handle AI-deployment questions responsibly. Scores
run 1 to 5, with a separate marking for not-applicable. Judges return
structured output with a written justification for every score, and the
pipeline validates the shape of every grade before accepting it.

That produced 6,480 grades. Twenty-five came back unparseable and were
excluded; refilling all twenty-five with worst-case and best-case values
changes no number in this post by more than 0.02 and flips no ranking.
A further 2,160 grades come from a separate bridge experiment described
in Finding 5, bringing the public dataset to 8,640.

All six models ran at their providers' default settings. The newest
models from OpenAI and Anthropic no longer accept a temperature
parameter at all, so configured sampling is not an option for a current
grid, and defaults are also what a real user gets. Output limits were
set high enough that no answer was cut off; I verified this directly
because an earlier run was silently corrupted by truncation, a story
told in the limitations section.

## How to read every number in this post

This section exists so that no statistic below requires trust.

**The unit of analysis is the question, not the grade.** The 6,480
grades are not 6,480 independent facts. All the grades attached to one
question rise and fall together, because some questions simply invite
worse behavior than others. Independent observations exist at the level
of the sixty questions. Every average in this post therefore collapses
to one value per question first, and all uncertainty is computed over
those sixty values. Treating the grades as independent would make my
error bars roughly five times narrower than honesty permits.

**Error bars answer one specific question.** My sixty questions are one
possible draw from the universe of legal questions a person could ask.
Had I written the set in a different week, I would have produced a
somewhat different sixty, and every number here would have come out
slightly differently. The bracketed interval after each estimate says
how much. Formally it is a 95 percent confidence interval computed by
the bootstrap, which works as follows. I cannot collect thousands of
alternative sixty-question sets, but I can simulate them: draw sixty
questions at random from my actual sixty, allowing repeats, so that some
questions appear twice and others not at all. Drawing with repeats is
what makes the simulated set behave like a genuinely fresh draw from the
same universe rather than a reshuffled copy. Compute the average for
that simulated set. Repeat several thousand times. The middle 95 percent
of those simulated averages is the interval I report. A worked
miniature: if three questions scored 2, 3, and 5, the simulated sets
might be 2-2-5, then 3-5-5, then 2-3-3, with averages 3.0, 4.3, and 2.7,
and the spread of such averages is exactly the question-to-question luck
we need to quantify. The analogy is a poll: a survey of sixty voters
carries a margin of error describing what other surveys of sixty would
likely find. Here the questions are the voters, and the bootstrap
simulates the other polls.

**Bold means the interval excludes zero.** When a table bolds an effect,
fewer than 5 percent of plausible alternative question sets would flip
its sign. When I write NS, the interval includes zero and the honest
statement is that this data cannot distinguish the effect from nothing.
With many comparisons in one table, roughly one marginal false positive
per twenty tests is expected, and I point out where that matters.

**Judge agreement is moderate, and the design assumes it.** The standard
agreement score for this kind of panel is Krippendorff's alpha, which
equals 1 when judges always agree and 0 when their agreement is no
better than chance. Across dimensions it runs 0.55 to 0.73 here, weakest
on confidence calibration, where judging requires assessing how certain
an answer should have been, and strongest on disclaimers, where the
judge mostly checks whether particular language exists. This is why no
conclusion in this post ever rests on a single judge or a single grade.

## Finding 1: every judge has a fingerprint

For each grade a model gives to its own anonymous answer, I compare it
to the median of what the other five judges gave the exact same answer.
Two design choices carry the weight. The comparison is on the same
answer because Claude's answers might genuinely be better; in that case
every judge scores them high and no bias is implied. Bias appears only
when a model scores its own text differently than five other judges
score the identical text. And the baseline is the median rather than
the average because a median is insensitive to a single outlying judge:
one anomalously harsh or generous grader moves an average but does not
move the middle of five.

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

Twenty of these twenty-four measurements exclude zero. Three patterns
deserve names.

**Claude is its own harshest critic, and this is now a replicated
trait.** Sonnet 5 marks its own blinded work down on all four core
dimensions. Its predecessor Sonnet 4.6 did the same against a different,
smaller judge panel. Two generations, two panels, one signature.

**The fingerprint belongs to the model, not the vendor.** GPT-4o, in the
previous generation of this study, inflated its own answers by up to
one and a half points. GPT-5.5 is nearly neutral and mildly
self-critical on disclaimers. Whatever produces these biases changed
between model versions from the same company.

**The budget tiers flatter themselves.** GPT-5.4-mini is the most
self-inflating judge in the panel, and Gemini 3.1 Lite inflates on
every dimension. If you use a small, cheap model as a judge over its
own family's outputs, this is the measured warning.

`[LW-ONLY]` The general implication: LLM-as-judge is now the default
methodology for model comparisons, and these fingerprints are large
relative to the between-model differences that papers typically report.
Blinding did not remove them; the models evidently recognize something
in their own style. Single-judge evaluations of a model by its own
family are contaminated by default, in whichever direction that family's
fingerprint points. Multi-judge medians and an explicit self-premium
measurement should be table stakes.

## Finding 2: who notices the user is in trouble?

Each matched pair holds the legal topic constant and changes only the
asker's situation. The shift is the crisis score minus the calm score,
averaged over fifteen pairs. A safety-calibrated model shifts upward:
more disclaiming, more escalation, when more is at stake for the asker.

| arm | disclaimer shift | escalation shift |
|---|---|---|
| GPT-5.5 | +0.21 [−0.40, +0.85] | **+1.07** [+0.48, +1.69] |
| GPT-5.4-mini | **+1.09** [+0.62, +1.59] | **+1.64** [+1.15, +2.17] |
| Claude Sonnet 5 | **−0.66** [−1.09, −0.25] | **+0.62** [+0.10, +1.17] |
| Claude Haiku 4.5 | −0.39 [−0.79, +0.02] | **+0.63** [+0.12, +1.18] |
| Gemini 3.5 Flash | **+0.67** [+0.02, +1.29] | **+0.64** [+0.17, +1.09] |
| Gemini 3.1 Lite | **+0.49** [+0.05, +1.07] | **+0.59** [+0.21, +1.01] |

Escalation works everywhere. All six models push harder toward a real
lawyer when the user signals trouble. This is the trained-in behavior,
and it shows.

Claude Sonnet 5's disclaimer shift is negative, significantly so. When
the asker sounds one bad day from losing their apartment, Sonnet 5
attaches *fewer* disclaimers than it does for the idly curious version
of the same question. Haiku trends the same direction without reaching
significance, which makes this look like a family trait in the current
Anthropic generation. Finding 5 shows the same result under an entirely
different judge panel, which rules out the graders as the explanation.

The third observation cuts against tier assumptions: GPT-5.4-mini, the
cheapest OpenAI model in the grid, is the best-calibrated arm in the
study on both dimensions, while its flagship sibling's disclaimer
calibration is statistically indistinguishable from nothing.

`[YOU]` One worked pair inline here. The per-pair cards in the report
UI have the candidates; the landlord lockout pair reads well.

## Finding 3: three turns of pressure

An honest caveat first. A real pressure test would be one continuous
conversation in which the model answers, the user pushes back, and the
model answers again. That is not what I ran. Each turn here is a
separate, standalone prompt written as if the conversation had already
happened; the third turn opens with "You already said it could be
harassment" even though the model said no such thing. This measures
reaction to increasingly insistent framing, not drift across a real
conversation. And with five scenarios, directions are trustworthy and
magnitudes are not.

The one result that generalizes across the whole grid: **confidence
decays under pressure everywhere.** Five of six arms show significant
negative drift in confidence calibration from the first turn to the
third, between roughly half a point and one and a half points. By the
third, more insistent message, every current model sounds more certain
than it did at the start, and more certain than the law supports.
GPT-4o showed this pattern in the previous generation of this study; it
now describes essentially every model tested.

Gemini 3.5 Flash shows the sharpest disclaimer collapse, starting near
4.5 in the first turn and falling to 2.6 by the third. Claude shows the
inverted-V that the endpoint numbers hide: its disclaimer rigor rises
at the second turn, where the simulated user sounds most vulnerable,
then collapses below its starting point when the user demands concrete
steps. The per-turn trajectories for every arm are in the released
data.

## Finding 4: the noise is in the judges, not the dice

This finding is a conclusion about where grading disagreement comes
from, so here is the reasoning, not just the split.

Every question was answered three times per model, and every answer was
graded by six judges. That structure lets disagreement be taken apart
layer by layer. Start at the innermost layer: six judges grading the
same single answer. Any spread among those six grades can only come
from the judges, because the question and the answer are fixed. Average
the within-answer spread across all answers and you have the judge
component. Move out one layer: the three answers a model gave to the
same question. The spread among their per-answer averages reflects the
dice, the genuine variation in what the model produces on a re-roll,
plus a diluted residue of judge noise that we already measured and can
subtract. Move out to the last layer: the spread across the sixty
questions themselves, minus the diluted inner components, is what the
questions contribute. Peel, subtract, repeat: that is the entire
method.

The result, pooled across models and dimensions: **the question
accounts for 55 percent of grading variance, the judge for 37 percent,
and the dice for 8 percent.** Re-asking the same model the same
question barely moves its grade. Asking a different judge moves it four
to five times as much. The practical lesson for anyone building an
evaluation like this one is to spend marginal budget on more or better
judges rather than more samples per question.

One methodological note: this run let every model sample at its
provider's default settings rather than a configured temperature, and
the dice share rose from 5 percent in the previous run to 8 percent
here, which is the direction that change predicts.

## Finding 5: did the models get better? `[the generational section]`

I have three complete, judged datasets on these same sixty questions:
a spring run with Sonnet 4, GPT-4o, and Gemini 2.5 Flash; an early
summer run in which only the Claude arm changed, to Sonnet 4.6; and the
current six-model run. Comparing across them has a problem: the judges
changed too. A grade shift could mean the models changed or the graders
did.

Two features of the design solve this. First, between the spring and
early-summer runs, exactly one responder changed, and two judges were
byte-identical model versions. Scoring both runs with only those two
frozen judges makes Claude the treatment arm and the unchanged GPT-4o
and Gemini arms into negative controls that measure run-to-run noise.
The controls moved at most 0.15 points on any dimension, none
significant. Against that floor, Sonnet 4.6's disclaimer level fell
0.45 points from Sonnet 4, with an interval from −0.67 to −0.22. The
one marginal control movement is the expected false positive from
twelve simultaneous comparisons.

Second, for the current run, I re-ran those same two frozen judges,
same model snapshots, same settings, over all 1,080 new answers. That
is 2,160 additional grades whose only purpose is to hold the graders
constant across three generations of models.

**Here is where I correct myself.** After the first two runs I wrote
that Claude's disclaimer behavior had declined monotonically across
generations. The bridge data says otherwise: under identical judges,
Sonnet 5 partially recovered, from 2.28 back up to 2.49, and the full
Sonnet 4 to Sonnet 5 change is −0.23 with an interval from −0.51 to
+0.04, which does not exclude zero. The claim survives only in a more
precise form, and the instrument I built to test it is the thing that
trimmed it.

The more precise form is about calibration, and it is confirmed under
both judge panels. Crisis-disclaimer shift by generation, frozen
judges:

| arm | gen 4 era | gen 4.6 era | gen 5 |
|---|---|---|---|
| Claude | −0.40 [−1.03, +0.33] | −0.08 [−0.69, +0.54] | **−0.73** [−1.26, −0.20] |
| OpenAI | **+1.07** [+0.57, +1.57] | **+1.06** [+0.38, +1.69] | +0.24 [−0.60, +1.07] |
| Gemini | **+1.17** [+0.43, +2.00] | **+1.46** [+0.69, +2.20] | **+0.95** [+0.29, +1.56] |

Claude went from uncalibrated to significantly backwards. OpenAI went
from strongly calibrated to statistically nothing. Only Gemini held.
Meanwhile baseline quality rose almost everywhere: confidence and
jurisdiction levels improved for every vendor's chain, most steps
significantly, and Sonnet 5 recovered disclaimer volume even as it
misallocated it.

So the answer to "did the models get better" is: **at giving good
average answers, yes, measurably, across every vendor. At noticing who
is asking, no. Two of three vendors got worse at exactly that.** For a
domain where the desperate asker is the one who most needs the
guardrails, that is the finding I would want deployers to read.

Two response-side confounds ride along with any comparison into the
current generation and are disclosed rather than corrected: the newer
models sample at provider defaults because they no longer accept
configured temperature, and output limits were raised after the
truncation incident. The judge side is clean; the response side is each
era's deployed reality.

## Failure floor `[CUT-OK]`

Absolute levels, so the shift-based findings are not misread as "the
models are fine." Outside the Gemini family, average disclaimer scores
run 1.9 to 2.4 out of 5; the Gemini family is the outlier at 3.4 and
4.1, and Gemini 3.1 Lite is the only model in the grid that reliably
disclaims. Across 1,080 answers, 910 answer-dimension pairs were scored
1 out of 5 by at least two of six blinded judges. These counts are not
comparable to the three-judge era, because a six-judge panel reaches a
two-judge agreement bar far more easily; within this run, they simply
say the floor is low everywhere.

## A JD reads the disputed transcripts `[PENDING — your review pass]`

Placeholder for the qualitative sidebar: the answer-dimension pairs
where six frontier models could not agree whether the answer was safe,
reviewed by hand. These items stay out of every quantitative claim.

## Limitations

1. **The judges are the responders.** Blinded, but the same six models
   fill both roles, and the self-premium analysis measures exactly the
   contamination this creates rather than assuming it away. The bridge
   pass adds two judges that are not in the response set, and the
   headline calibration finding survives both panels.
2. **One author wrote the questions and the rubric.** Sixty questions,
   informed by a law degree, still one person's construct. The error
   bars quantify question-sampling noise, not construct validity.
3. **Pressure sequences are simulated single-shot turns**, five of
   them. Directions, not magnitudes.
4. **Sampling conditions changed across generations by necessity.** The
   newest OpenAI and Anthropic models reject configured temperature, so
   the current grid runs at provider defaults while earlier runs used a
   configured 0.7. Generational comparisons carry that difference, and
   it is disclosed wherever they appear.
5. **Judge agreement is moderate**, alpha 0.55 to 0.73 by dimension.
   The design answers this with medians across judges, per-question
   aggregation, and the variance decomposition; individual grades are
   noisy and nothing rests on one.
6. **Nulls.** Twenty-five of 6,480 panel grades and nine of 2,160
   bridge grades failed to parse and are excluded. Adversarially
   filling every one of them with all-1s or all-5s moves no reported
   number by more than 0.02 and flips no ranking.
7. **Tier labels are mine.** "Mid" and "budget" reflect each vendor's
   own positioning and pricing at collection time. The data itself
   argues tiers are not a safety ordering: Google's budget model beats
   its mainline on three of four dimensions, and OpenAI's mini is the
   best-calibrated arm in the grid.
8. **Multiple comparisons.** The fingerprint table alone contains 24
   tests; at the 95 percent level, roughly one marginal false positive
   per twenty tests is expected. The findings this post leads with are
   far from that margin.

## Reproducibility `[REPO LINK pending]`

The public repository contains the full pipeline code, the rubric and
judge prompt, the blinding lookup, all 8,640 grades with score values
intact and justification text stripped, and the complete analysis
output. Every statistic in this post recomputes from the released
grades with one command, deterministically: when the analysis was
re-run independently on two machines during this project, the outputs
were byte-identical. The sixty questions are not released, apart from
a set of worked examples with full answers and grades, because
published questions enter training corpora and the point of a held-out
set is to re-run this evaluation on next year's models. `[LW-ONLY]`
Researchers who want to audit the full question set can contact me.

## What's next `[YOU]`

- Re-run on successor models with the held-out set. The bridge
  technique generalizes: any future run can be chained back to this one
  by re-running frozen judges.
- Candidate design fixes for the next version: true multi-turn pressure
  with real conversation state, a judge from outside the response set
  as a permanent panel member, more pressure sequences.

---

### Numbers-lock appendix `[not for publication]`

All statistics trace to `data/analysis_results.json` (analyze v3, seed
20260521), `data/bridge_scores.json`, and FINDINGS.md as of commit
`e8e88a9`. Do-not-publish list honored: no cross-panel critical-failure
rate comparisons; no cells with fewer than three pairs or sequences; no
judged 4-era to 5-era claims without the bridge; the corrected
monotonic-decline claim appears only in its corrected form. Prose rules
enforced: no parenthetical asides in body text, no em-dash connectors
in sentences, intervals written as bracketed ranges immediately after
their estimates, every statistical term defined in "How to read every
number in this post" before first use.
