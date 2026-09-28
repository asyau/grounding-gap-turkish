# Category-merge audit: result

Run 2026-08-28. Everything below comes from files already in the repository. No API
calls, no key, no cost.

## Summary

The hypothesis was that merging "Other abstract concept" into "Verbal Association"
inflates the models' verbal-association count and manufactures part of the paper's
headline gap. **The hypothesis is wrong, and I can say why precisely.** Two further
checks aimed at the same target also came back clean. One genuinely new descriptive
finding survived, plus a suggestive trend that does not reach significance.

## Why the merge hypothesis is dead

Harpaintner et al. did the same merge, on the human side, for the same reason. From
the Frontiers paper, the original scheme has five main categories, and the study
"combined Association and Other abstract concept into a broader verbal association
category for analysis." Their reported means are:

| | Sensorimotor | Internal | Social | Verbal |
| --- | --- | --- | --- | --- |
| Harpaintner 2018 as published | 0.337 | 0.325 | 0.078 | 0.260 |
| `human_norms.csv` in the repo | 0.336 | 0.324 | 0.078 | 0.261 |

The grounding-gap paper also documents its own merge explicitly, in Appendix G.3:
"After coding, the two abstract categories: Association and Other abstract concept
are merged to form the final abstract category Verbal association."

So the merge is symmetric, inherited from the source study, and disclosed. There is
no artefact. I was wrong, and it cost nothing to find out.

## Second check: is the coder biased?

A subtler version of the same worry. The human norms were coded by Harpaintner's human
experts; the model outputs are coded by `gemini-2.5-flash-lite` at Cohen's kappa
around 0.5. If the coder systematically shifts mass toward Verbal and away from
Internal relative to human experts, every model's gap would be inflated by the coder
alone.

This is directly testable with shipped data. The repo includes expert hand-coded labels
for 2077 model-generated properties, and every coded run stores the coder's own label
for each property. 1930 of the 2077 (92.9%) were also seen by the coder, giving 74006
coder decisions on properties whose expert label is known.

Confusion matrix, rows expert, columns coder:

| | Sensorimotor | Internal | Social | Verbal |
| --- | --- | --- | --- | --- |
| **Sensorimotor** | 409 | 22 | 4 | 162 |
| **Internal** | 34 | 131 | 4 | 23 |
| **Social** | 19 | 5 | 123 | 65 |
| **Verbal** | 149 | 38 | 69 | 673 |

Overall agreement 69.2%, Cohen's kappa 0.527. The paper reports 67.2% and 0.505, so
this approximately reproduces their Table 2 as a side effect.

The marginal test is the point:

| | Sensorimotor | Internal | Social | Verbal |
| --- | --- | --- | --- | --- |
| expert humans | 0.309 | 0.099 | 0.110 | 0.481 |
| gemini-2.5-flash-lite | 0.317 | 0.102 | 0.104 | 0.478 |
| **coder minus expert** | **+0.007** | **+0.002** | **-0.006** | **-0.003** |
| paper's reported gap | -0.060 | -0.187 | +0.019 | +0.186 |

The coder's Verbal shift is -0.003 against a reported gap of +0.186, and its Internal
shift is +0.002 against -0.187. Coder bias accounts for roughly 1% of the effect, in
the wrong direction to help the hypothesis. The coder is noisy but not biased, which
is exactly the property this design needs.

## Third check: is the gap measurement noise?

The paper compares model r near 0.3 against a human ceiling of 0.974, but 0.974 is the
reliability of the *human* measurement. The models' own reliability is never reported.
Computed from the shipped runs by 5-versus-5 split halves, 50 random splits per model,
Spearman-Brown corrected:

- Mean model split-half reliability: **0.918** (range 0.728 to 0.973)
- Disattenuating the whole leaderboard moves the mean from 0.281 to 0.298
- The best model moves from **0.375 to 0.404**, against a ceiling of 0.974

So the gap is not an artefact of noisy model measurement either. Models are internally
very consistent; they consistently do something different from people. This is a result
that strengthens the paper rather than challenging it, and it is the kind of check a
referee would ask for.

## What did survive: the merge hides a 6x spread

The merge is fair, but the merged number conceals which of the two behaviours a model
actually produces. Across all shipped coded runs, "Other abstract concept" is 14.9% of
every coder decision made. Its share of each model's Verbal Association mass:

| Model | other-abstract as share of Verbal | Verbal share overall | Mean r |
| --- | --- | --- | --- |
| gemini-2.5-flash-lite | 51.0% | 41.4% | 0.348 |
| qwen3-vl-8b | 47.1% | 45.3% | 0.273 |
| gemma-3-4b-it | 44.1% | 41.4% | 0.270 |
| ... | | | |
| gpt-oss-20b | 18.6% | 49.6% | 0.302 |
| gemini-3.1-pro | 11.4% | 47.9% | 0.256 |
| gemini-3-flash | 8.2% | 53.0% | 0.216 |

A 6.2x spread. Two models can post nearly identical Verbal Association scores while
doing qualitatively different things: gemini-3-flash and llama-3.1-8b both sit at 53.0%
Verbal, but for one that mass is 8% abstract redefinition and for the other 26%. The
paper's claim that models over-produce verbal associations is true at the merged level,
and under it there are at least two distinct behaviours that the released data can
separate and the paper does not report.

## The trend that is only a trend

Across the 21 models, other-abstract share of Verbal correlates with alignment:

- vs Mean r: pearson +0.365, p = 0.104
- vs Internal r: pearson +0.404, p = 0.069
- vs Verbal r: pearson +0.486, p = 0.026
- control, total Verbal share vs Mean r: pearson -0.364, p = 0.105

With n = 21 and five tests, only the Verbal correlation is nominally significant and it
does not survive a Bonferroni correction. **This is a trend, not a finding, and it
should not go in an email as anything more.** It is worth one sentence as a question,
not a claim.

## Minor data-hygiene note

189 coder calls returned `503 unavailable` and the error string was written into the
`codes` column as though it were a label. A few dozen other rows contain the coder
echoing properties instead of categories. The parser silently drops all of these, so
72 decisions out of 235055 (0.03%) vanish from the frequency vectors rather than
raising. The effect is negligible; the silent-drop behaviour is worth a line in an
issue, not an email.

## Where this leaves the email

Three of the four things worth saying are now checkable claims that survived a real
attempt to break them:

1. The Experiment 1 leaderboard reproduces exactly for 19 of 21 models, and the two
   that do not are explained (Claude Haiku 4.5 is the nine-versus-ten run difference
   the caption already notes).
2. The gap is not measurement noise. Model split-half reliability averages 0.918, so
   disattenuation moves the best model only from 0.375 to 0.404.
3. The gap is not coder bias. On 1930 expert-labelled properties the coder's marginal
   distribution differs from human experts by 0.003 on Verbal, against a reported
   effect of 0.186.
4. The merged Verbal Association category hides a 6.2x spread in composition across
   models, recoverable from the released data.

Points 2 and 3 are the unusual ones. An applicant who says "I tried to break your
result two ways and it held, here are the numbers" is doing something different from
an applicant who says the paper is interesting.

The language question from the Stage 1 report is still open and still unaddressed by
the paper.
