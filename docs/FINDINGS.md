# Pre-Publication Findings — v2 (six-model gen-5 dataset)

> Development log, kept verbatim from the working repository as of its last commit (2026-07-17). File paths in it refer to that repository's layout: `data/legacy/` and `drafts/` are in this repository's git history but not in its tree, and the post draft now lives in `report/post.md`. The release corrections of 2026-10-09 (the null-refill bound, the Finding 5 control sentence) postdate this log and are recorded in the release commit.

**Date:** 2026-07-03
**Basis:** `data/analysis_results.json` (analyze v3 over 6,480 judgments:
1,080 responses × 6 judges; 25 null, 0.39%) plus post-flight verification
(truncation audit, adversarial null fills). Supersedes the v1 memo
(2026-07-01, 4.6-era numbers — preserved in git history and summarized in
[HISTORY.md](HISTORY.md)); the 4.6-era dataset itself remains archived in
`data/legacy/*_2026-07-02*` and still backs the Sonnet 4→4.6 comparison.
**Grid:** gpt-5.5 / gpt-5.4-mini / claude-sonnet-5 / claude-haiku-4.5 /
gemini-3.5-flash / gemini-3.1-flash-lite; provider-default sampling; 8192
output caps; single config vintage `d64f7b847f91`.

---

## 0. Dataset integrity (verified)

- **No truncation anywhere:** max total tokens 3,586 vs 8,192 cap; every
  arm has 2×+ headroom; mid-sentence tail scan clean (0–3% heuristic
  false-positive range, vs 62.8% in the old truncated Flash arm).
- **Joins perfect:** 6,480 unique (response, judge) pairs, all IDs join the
  lookup. 25 nulls, all gemini-3.5-flash JSON failures.
- **Null robustness:** adversarially filling all 25 nulls with all-1s /
  all-5s moves no published statistic by more than 0.021 and flips zero
  rankings.
- Four Sonnet-5 judgments arrived shape-malformed (flat guardrail/
  regulatory ints), were dropped, and re-judged under the new shape
  validation. See HISTORY.md incident #8.

## 1. Self-favoritism — the fingerprint finding, replicated and enriched

Premium = own score − median of the **five** other judges on the identical
blinded response; CIs bootstrap over 60 prompts. **20 of 24 core
(judge × dimension) cells exclude zero.**

| judge | signature (core dims) |
|---|---|
| claude (Sonnet 5) | **self-deprecates on all four: −0.23 to −0.71, all significant** |
| chatgpt (GPT-5.5) | near-neutral, mixed signs: disclaimer −0.28*, confidence +0.24* |
| chatgpt_mini | **strongest self-inflator: +0.23 to +0.99 all significant** (guardrail flag +2.1) |
| claude_haiku | mixed: inflates disclaimer/escalation (+0.44*/+0.22*), deflates confidence/jurisdiction |
| gemini (3.5-flash) | near-neutral (+0.08 NS ×2, +0.46*/+0.12*) |
| gemini_lite | inflates across the board: +0.25 to +0.64, all significant |

**Publishable claims:**
1. **Claude's self-deprecation survived a generation and a panel change** —
   Sonnet 4.6 (−0.35..−0.89 vs 2 judges) → Sonnet 5 (−0.23..−0.71 vs 5
   judges). This is now a replicated, cross-generation, cross-panel trait.
2. **GPT's fingerprint flipped:** gpt-4o inflated its own work (+0.63 to
   +1.48); gpt-5.5 is near-neutral-to-mildly-self-critical. Fingerprints
   are model properties, not vendor properties.
3. **New: the budget tiers inflate themselves more than the mid tiers** —
   gpt-5.4-mini is the most self-flattering judge in the panel; gemini-lite
   inflates everywhere it can be measured. (Haiku partially bucks this.)

## 2. Crisis calibration (n = 15 pairs)

| arm | disclaimer shift | escalation shift |
|---|---|---|
| chatgpt | +0.21 (NS) | **+1.07*** |
| chatgpt_mini | **+1.09*** | **+1.64*** |
| claude | **−0.66*** [−1.09, −0.25] | **+0.62*** |
| claude_haiku | −0.39 (NS) | **+0.63*** |
| gemini | **+0.67*** | **+0.64*** |
| gemini_lite | **+0.49*** | **+0.59*** |

**Publishable claims:**
1. Escalation calibration is universal: all six arms significantly push
   harder toward a lawyer under crisis framing.
2. **Claude Sonnet 5's disclaimer calibration is significantly BACKWARDS**
   (−0.66*): it disclaims *less* when the user is in visible trouble.
   Sonnet 4.6 was flat (−0.12 NS); Sonnet 5 crossed into significantly
   negative. This is the strongest single behavioral finding in the study.
   Haiku trends the same way (−0.39 NS) — it reads as an Anthropic-family
   trait in this generation.
3. gpt-5.5 lost gpt-4o's disclaimer calibration (+0.83* → +0.21 NS), while
   its own mini (+1.09*) is now the best-calibrated arm in the grid —
   tier does not predict calibration.

## 3. Pressure drift (n = 5 sequences — exploratory, simulated turns)

- **Confidence decay is now universal:** all six arms negative; four
  significant (chatgpt −1.38*, mini −1.33*, claude −1.01*, gemini −1.41*;
  lite −0.56*; haiku −0.48 NS). In the 4-era data only GPT-4o showed this
  clearly. Under sustained pushiness, current models get more definitive.
- **Gemini 3.5-flash reversed its predecessor's pattern:** it now *starts*
  high (turn-1 disclaimer 4.46) and collapses at turn 3 (2.57; drift
  −1.89*). The old floor-to-ceiling ramp is gone (and was partly a
  truncation artifact anyway).
- Claude shows the inverted-V (2.57 → 3.24 → 1.66, drift −0.91*): rigor
  rises at the vulnerable turn 2, then collapses when the user demands
  actionable steps.
- Same standing rules: n=5, per-sequence data shown, n<3 cells suppressed.

## 4. Tier effects (within-provider, prompt-paired)

No uniform "bigger is safer":
- **OpenAI:** mid beats small on all four dims (+0.18* to +0.47*).
- **Anthropic:** mid ≥ small on confidence/jurisdiction only (+0.28*/+0.45*);
  disclaimers/escalation indistinguishable.
- **Google: inverted** — the budget lite tier *beats* flash on three of
  four dims (disclaimer −0.64* in flash-minus-lite terms; lite's absolute
  disclaimer mean of 4.08 is the highest in the grid).

## 5. Where the variance lives (provider-default sampling)

Pooled over 24 cells: **prompt 55.2% | judge 36.6% | response 8.2%.**
Response share rose from 5.1% (configured temp 0.7) to 8.2% (provider
defaults) — the predicted direction — but judge disagreement still
dominates response sampling ~4.5×. The "spend on judges, not samples"
design lesson stands. α by dimension: 0.55–0.73 (confidence weakest,
consistent with the 4-era panel).

## 6. Absolute levels (failure floor)

Disclaimer means outside the Gemini family remain low (1.92–2.36 of 5);
the Gemini family is the outlier (3.44 flash / 4.08 lite — consistent with
the near-compulsive lexical rates). 910 critical failures incl. self (881
strict) over 1,080 responses. **Do not compare this rate to the 4.6-era
0.86/response:** the threshold is ≥2 judges scoring 1, and a 6-judge panel
reaches that bar far more easily than a 3-judge panel.

## 7. Cross-generation story — now judge-controlled end-to-end (bridge pass)

The bridge pass (data/bridge_scores.json: gpt-4o-2024-08-06 +
gemini-2.5-flash at temperature 0.0 — the identical judge conditions of
both prior eras — over all 1,080 gen-5 responses) makes every step below
judge-controlled. Remaining response-side confounds for any →gen-5 step:
sampling regime (configured 0.7 → provider defaults) and output caps
(2048 → 8192); these are each era's deployed conditions and are disclosed.

**Levels under identical judges (60 prompts, paired):**

| chain | disclaimer | escalation | confidence | jurisdiction |
|---|---|---|---|---|
| Claude S4 → S4.6 → S5 | 2.73 → 2.28 → 2.49 | 3.60 → 3.35 → 3.45 | 3.78 → 3.75 → 3.97 | 3.31 → 3.38 → 3.70 |
| gpt-4o → gpt-5.5 | 2.58 → 2.58 | 2.98 → 3.32* | 3.50 → 3.95* | 3.10 → 3.51* |
| 2.5-flash† → 3.5-flash | 2.62 → 3.85* | 3.12 → 3.64* | 3.69 → 3.84 | 3.24 → 3.62* |

† old-side truncation inflates the Gemini step.

**Crisis-disclaimer calibration by generation (identical judges):**

| arm | gen-4 | gen-4.6 | gen-5 |
|---|---|---|---|
| Claude | −0.40 (NS) | −0.08 (NS) | **−0.73*** [−1.26, −0.20] |
| OpenAI | **+1.07*** | **+1.06*** | +0.24 (NS) |
| Gemini | **+1.17*** | **+1.46*** | **+0.95*** |

**Corrected and confirmed claims:**
1. **CORRECTION (v2 §7 overclaimed):** Claude's disclaimer *level* did not
   decline monotonically. It is V-shaped: the 4.6 dip (−0.45*) partially
   recovered at Sonnet 5 (+0.22, CI [−0.02, +0.44]); the full S4→S5 span
   is −0.23 [−0.51, +0.04], not significant. The bridge exists precisely
   to test such claims, and it trimmed this one.
2. **CONFIRMED, now judge-controlled:** Sonnet 5's backwards crisis
   calibration (−0.73* under the legacy judges, −0.66* under the new
   panel) is a property of the model, not of either judge panel. Claude
   recovered disclaimer *volume* at S5 but distributes it backwards —
   fewest disclaimers exactly when the user is in trouble.
3. **New cross-vendor pattern:** crisis-disclaimer calibration weakened
   from the 4-era to gen-5 for the two mainline non-Google arms — OpenAI
   collapsed from +1.07* to +0.24 (NS), Claude from ~flat to
   significantly negative; only Gemini retained calibration. Meanwhile
   **baseline quality rose generation-over-generation for every chain**
   (confidence/jurisdiction levels up, all steps positive, most
   significant). The generational thesis the data supports: *newer models
   give better average answers while attending less to who is asking.*

## 8. Do-not-publish list (v3)

1. Cross-panel critical-failure rate comparisons (threshold changes with
   panel size).
2. Any n<3 pressure/calibration cell (low_n-suppressed in the report).
3. Judged 4-era→5-era model comparisons without the bridge pass — lexical
   preview and directional language only, three confounds disclosed.
4. The 4.6-era cross-run critical-failure trend (three-way confounded; v1
   ruling stands).
5. **Raw self-premiums presented as self-bias** (added 2026-07-08; see
   §10). The raw median-of-others premium confounds judge grading style
   with self-treatment. Publish net premiums; raw premiums may appear
   only alongside the style deviation that explains them.

## 9. Open items

1. ~~Bridge-judging pass~~ — DONE (see §7; data/bridge_scores.json).
2. ~~Author review of high-disagreement transcripts~~ — DONE 2026-07-03
   (drafts/disagreement_review.md; sidebar drafted).
3. Draft rebuild on the corrected Finding 1 per §10.
4. Release repo build (code + shape-validated scores incl. bridge +
   examples).

## 10. Style-corrected self-favoritism (analyze v4, 2026-07-08)

**The catch.** An external-reviewer prompt questioned the title claim
("recognized itself"). Follow-up analysis showed the raw self-premium
(judge minus median-of-others on OWN responses) never subtracted the
judge's deviation on OTHERS' responses — its general grading style. A
uniformly harsh or generous judge shows a large raw premium with zero
self-specific treatment. analyze v4 adds `style_deviation` and
`net_self_premium` (self minus style, per prompt, bootstrap CI over
prompts).

**Corrected gen-5 results (core dims):**

- **Claude Sonnet 5's "self-deprecation" is dead.** Nets: disclaimer
  −0.08, escalation +0.02, confidence +0.05, jurisdiction +0.03 — no CI
  excludes zero. Claude is the panel's harshest judge on everyone
  (style −0.27 to −0.72). Same result in the 4.6 era (nets |≤0.04| on
  all four dims): the "replicated trait" was style both times.
- **GPT-5.4-mini's +0.99 disclaimer premium is style (+0.94).** Real
  nets survive on escalation +0.20* and confidence +0.22*; guardrail
  net +1.29 (low-n, n_self=20).
- **14 of 24 core cells have significant nets, and every one is
  positive.** No judge favors others over itself. The Gemini family is
  the standout: all 8 of its cells significant (up to lite escalation
  +0.45*).
- **GPT-4o (4.6 era) splits:** style +0.39/+0.71 on
  disclaimer/escalation with genuine net self-favoritism +0.23/+0.43.

**The two-layer replacement finding:** (1) judge style offsets are
large (up to ±0.9 points) and are a first-order hazard for
LLM-as-judge panels regardless of blinding; (2) after removing style, a
smaller, uniformly positive self-preference remains for most judges.
Headline retirements: "Claude is its own harshest critic" (it is the
harshest judge, period), "the budget tiers flatter themselves" (they
flatter everyone), and any "recognized itself" framing on the raw
numbers.
