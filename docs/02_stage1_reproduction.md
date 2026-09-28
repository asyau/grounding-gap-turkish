# Stage 1 report: reproducing the Grounding Gap leaderboards

Run date: 2026-08-26. No API key, no GPU. Repo cloned at `github.com/odychlapanis/grounding-gap`.

## Verification first

Both the paper and the code are real and consistent with each other.

- arXiv 2605.08837v1 resolves, HTML version readable.
- Repo README, citation block, and badge all point at the same eprint.
- Authors: Odysseas S. Chlapanis, Orfeas Menis Mastromichalakis, Christos H. Papadimitriou.

## Experiment 1 vs paper Table 4

`evaluate.py` discovers 21 model directories, merges 293 words per model, 10 coded
runs each. Result versus the published Table 4:

- 19 of 21 models reproduce **exactly** to three decimal places on all five
  reported columns (Mean r plus four per-category r).
- Rank order is identical to Table 4 for all 21 rows.
- Max absolute deviation across 21 models x 5 columns: **0.0095**.

Two rows deviate:

| Model | Column | Repro | Paper | Delta |
| --- | --- | --- | --- | --- |
| `claude-haiku-4.5` | Mean r | 0.258 | 0.257 | +0.001 |
| `claude-haiku-4.5` | Internal | 0.196 | 0.191 | +0.005 |
| `qwen3-4b-2507` | Mean r | 0.312 | 0.314 | -0.002 |
| `qwen3-4b-2507` | Sensorimotor | 0.326 | 0.335 | -0.009 |

### Claude Haiku 4.5: fully explained

Table 4's caption says "Ten generation runs per model (Claude Haiku 4.5: nine)."
The repo ships ten. Dropping `run_7` and averaging the remaining nine reproduces
the paper's row to within 0.0003 on every column. The repo simply ships one more
run than the paper scored.

### Qwen3 4B: small unexplained residual

No leave-one-out subset of the ten shipped runs gets closer than 0.0044 to the
published row. The deviation is 0.002 on Mean r and 0.009 on Sensorimotor, and it
does not change the model's rank. Most likely a re-coded or re-generated run
landing in the release that was not the exact run scored for the table. Worth one
sentence of curiosity, not a complaint.

## Rating experiment vs paper Table 6

`rating_experiment/src/evaluate.py` runs clean with no key. All 21 models, all
Mean r values match Table 6 to three decimal places, rank order identical.

## Experiment 2: not run

`evaluate.py` runs experiments 1 and 2 in one pass and raises `FileNotFoundError`
on the missing `data/experiment_2/human_norms.csv` **before writing anything**, so
the Experiment 1 table is lost too. `fetch_kelly.py` failed here only because this
sandbox blocks OSF at the network layer (`403 Forbidden` on the tunnel). On Colab
it should work. Until then, call `evaluate_experiment(get_config(1))` directly
rather than patching the repo.

## Headline finding reproduces

Mean per-category frequency, averaged over all 293 words:

| Source | Sensorimotor | Internal | Social | Verbal |
| --- | --- | --- | --- | --- |
| Human (Harpaintner) | 0.336 | 0.324 | 0.078 | 0.261 |
| Mean of 21 models | 0.276 | 0.137 | 0.097 | 0.447 |
| Delta | -0.060 | **-0.187** | +0.019 | **+0.186** |

Models under-produce internal-state properties by 18.7 points and over-produce
verbal associations by 18.6 points, exactly the direction and rough magnitude the
paper claims.

## The thing worth knowing before Stage 3

Harpaintner et al. 2018 is a **German** study. Sixty native German speakers, German
stimulus words, drawn from a German dictionary. The Grounding Gap paper says:

> "We derive a 293-word English stimulus set from the original 296 German
> abstract concepts."

So the human norms are German humans responding in German, and the models are
prompted in English. The paper does not discuss language, translation, or
multilinguality anywhere, including its Limitations section, which covers only
three things: generality of the replicated experiments, LLMs as coders, and SAE
analysis limits.

That means a language mismatch is already baked into the paper's central
comparison, and it is unacknowledged.
