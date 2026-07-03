# Pre-Publication Findings — v2 (six-model gen-5 dataset)

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

## 7. Cross-generation story (with confound discipline)

- **Judge-controlled (clean):** Sonnet 4 → 4.6 disclaimer regression
  (−0.45 [−0.67, −0.22] under identical judges; controls flat). See
  HISTORY.md Part IV.
- **Same-dataset (clean):** everything in §§1–5 above.
- **4-era → 5-era comparisons (three confounds: models + sampling regime +
  output caps):** directional only, pending the bridge-judging pass. The
  through-line that survives even this caveat: **Claude's disclaimer
  behavior has declined monotonically across three generations** (stable-
  judge 4→4.6 drop; 4.6 flat-crisis-shift → 5 significantly-negative
  crisis shift on an all-new panel), while its self-deprecating judge
  fingerprint persisted.

## 8. Do-not-publish list (v2)

1. Cross-panel critical-failure rate comparisons (threshold changes with
   panel size).
2. Any n<3 pressure/calibration cell (low_n-suppressed in the report).
3. Judged 4-era→5-era model comparisons without the bridge pass — lexical
   preview and directional language only, three confounds disclosed.
4. The 4.6-era cross-run critical-failure trend (three-way confounded; v1
   ruling stands).

## 9. Open items

1. Bridge-judging pass (gpt-4o + gemini-2.5-flash over the 1,080 gen-5
   responses, ~2,160 calls) — would make the generational chain
   judge-controlled end-to-end. Decision pending.
2. Author review of high-disagreement transcripts (report UI) — sidebar.
3. Draft rebuild on these numbers + second-round prose fixes.
4. Release repo build (code + shape-validated scores + examples).
