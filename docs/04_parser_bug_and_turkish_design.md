# Parser bug in the released code, and the design of the Turkish run (24 September 2026)

## Why the Turkish run was built as a Colab notebook

Gemini and OpenRouter were both blocked by network policy from the environment where this code was
written, so no live model call was ever made from it. The notebook was instead executed cell by cell
against a mock model that replays the paper's own released English outputs. Through our pipeline
those replayed answers give Mean r 0.343 on 3 runs, against the paper's 0.348 on 10, and a
per-concept profile agreement of r = 0.90 with the released runs. The plumbing is right; the live
numbers have to come from a real run (see the README, "Running in Google Colab").

## Deadline

Gemini 2.5 Flash-Lite, the paper's canonical Experiment 1 coder and one of its 21 models, retires on
the Gemini API no earlier than 16 October 2026 (Google has said the exact date is set when Gemini 3
reaches general availability, with notice). Both the Turkish run and the exact corrected leaderboard
(notebook section 7) need it. Fallback generator: `gemini-3.1-flash-lite`, also on the paper's
leaderboard at 0.223. There is no drop-in fallback for the coder that keeps comparability with the
paper, so run section 7 first if time is short.

## The finding: unreadable answers are scored as zeros

The repo's parser (`src/parsers.py`, `parse_exp1_response`) only accepts answers containing the
literal label `properties:`. When a model replies `anger: shouting, red face, clenched fists,
frustration`, the parser returns an empty list, `code.py` writes an all-zero frequency vector, and
`evaluate.py` averages that word-run in as a real observation. API error strings stored as
responses (for example `Error: 503 UNAVAILABLE`) take the same path.

| Model | Word-runs scored as zero | Mean r as released | Unparsed answers treated as missing |
| --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | 720 of 2930 (25%) | 0.348, rank 3 | 0.394, rank 1 |
| Llama 3.1 8B | 1194 of 2930 (41%) | 0.283, rank 11 | 0.339, rank 4 |
| GPT-OSS 120B | 493 of 2930 (17%) | 0.199, rank 20 | 0.239, rank 18 |
| Gemini 2.5 Flash | 89 of 2930 (3%) | 0.296 | 0.301 |

The other 17 models are unaffected or affected by a handful of rows. Full table:
`results/parser_bug/phantom_codes_by_model.csv`, produced by `scripts/phantom_codes.py`.

**How it was verified.**
1. 673 of Flash-Lite's 720 empty answers contain exactly four properties in the `word: a, b, c, d`
   format; 491 of GPT-OSS 120B's 493 do; Llama 3.1 8B's remainder are mostly numbered or bulleted
   lists. The rest are API errors, which are genuinely missing.
2. The unpatched `evaluate.py` reproduces Table 4 exactly; the patched one
   (`patches/grounding-gap-parser-fix.patch`) gives the right-hand column. `scripts/verify_patch.py`
   checks both.
3. A small secondary issue: 96 released rows (0.2%) have category codes even though their property
   list is empty, meaning the coder was given nothing and produced labels anyway.

**What it does and does not change.** The headline survives: the best corrected model is 0.394,
against a human ceiling of 0.974. But the top of the leaderboard changes, and so does the Llama 3.1
8B versus 70B comparison the paper uses when discussing scale (0.339 versus 0.375 after correction,
rather than 0.283 versus 0.375).

**Drop versus recover.** The right-hand column simply drops the lost rows, which needs no API calls.
The better correction recovers the four properties with a format-tolerant parser and codes them with
the paper's coder; notebook section 7 does that and writes `corrected_leaderboard.csv`. Those are the
numbers to quote once they exist.

## Design of the Turkish comparison

- **Same model, two languages.** Gemini 2.5 Flash-Lite generates properties for each concept in
  English and in Turkish. The Turkish prompt is a direct translation of the paper's, with the same
  worked example (sympathy: hug, friends, joy, sun).
- **Same coder prompt in both arms.** Every property, English or Turkish, is coded with the paper's
  English coding prompt, so the language of generation is the only thing that differs. Section 6 of
  the notebook repeats the Turkish coding with a Turkish prompt as a robustness check.
- **Same human reference.** Both arms are correlated against the Harpaintner norms. Those norms come
  from German speakers, so English is already a translation of the stimuli; Turkish is not at a
  disadvantage relative to English on that score, although it is one translation step further from
  the German original.
- **Paired statistics.** Turkish minus English differences are bootstrapped over concepts, paired,
  2000 resamples. The main comparison is repeated on the confidently translated items only.
- **Within-Turkish contrast.** For each concept, shift = Turkish category share minus English share
  for the same model. Mean shift for native Turkish words with a visible concrete root (izlenim, from
  iz, footprint; ayaklanma, from ayak, foot) is compared with the mean shift for loanwords (adalet,
  keşif). Using each concept's English profile as its own baseline controls for what the concept is,
  which a raw native-versus-loan comparison cannot.
- **Parse modes are recorded.** Every generated answer stores which parsing rule read it (`label`,
  `word_colon`, `list`, `bare`, `error`, `none`), so format drift between languages is visible
  rather than silently becoming missing data, which is exactly the failure found above.

## Stimulus table

`data/stimuli_tr.csv`: 293 rows, one per Harpaintner word, no two English words mapped to the same
Turkish word. Flags: 203 ok, 61 check, 29 hard. After the 25 September review: 154 native (122 with a
transparent concrete root), 25 hybrid, 114 loan; see `06_translation_review.md`. The origin labels are a first pass and must be checked against Nişanyan
Sözlüğü before the within-Turkish contrast is reported. Many transparent native words are
20th-century language-reform coinages (içgörü, öngörü, kavram, izlenim), so transparency is
confounded with recency.
