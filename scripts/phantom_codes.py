"""How many coded rows in the shipped release have codes but no properties?

When a model answers without the literal 'properties:' label (e.g. 'anger: a, b, c, d'),
the repo's parser returns an empty list. The shipped coded files nevertheless contain
four category codes for many of those rows: the coder was given nothing to classify
and produced labels anyway. evaluate.py counts them. This script measures how often
that happens per model and what the leaderboard looks like with those rows removed.
"""
import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")

import ast, glob, os, sys
import numpy as np, pandas as pd
from scipy import stats

REPO = EXP
sys.path.insert(0, REPO)
from src.parsers import parse_exp1_response

CATS = ["SM", "IS_E", "SC", "VA"]
human = pd.read_csv(f"{REPO}/data/experiment_1/human_norms.csv").rename(columns={"IS/E": "IS_E"})
human["word"] = human["word"].astype(str).str.strip()
H = human.set_index("word")

PAPER = {  # Table 4 Mean r
 "llama-3.1-70b":0.375,"qwen3-8b":0.373,"gemini-2.5-flash-lite":0.348,"qwen3-4b-2507":0.314,
 "gpt-oss-20b":0.302,"openai-gpt-5.4":0.301,"gemini-2.5-flash":0.296,"qwen3-vl-4b":0.295,
 "gemma-3-12b-it":0.292,"qwen3-vl-30b":0.292,"llama-3.1-8b":0.283,"claude-sonnet-4.6":0.277,
 "qwen3-vl-8b":0.273,"gemma-3-4b-it":0.270,"claude-opus-4.6":0.264,"claude-haiku-4.5":0.257,
 "gemini-3.1-pro":0.256,"gemini-3.1-flash-lite":0.223,"gemini-3-flash":0.216,"gpt-oss-120b":0.199,
 "gemma-3-27b-it":0.196}


def lit(s):
    try:
        v = ast.literal_eval(str(s))
        return v if isinstance(v, list) else None
    except Exception:
        return None


def is_empty(props):
    return props is None or len([p for p in props if str(p).strip()]) == 0


def mean_r(rows):
    df = pd.DataFrame(rows)
    prof = df.groupby("word")[CATS].mean()
    keys = prof.index.intersection(H.index)
    return float(np.mean([stats.pearsonr(prof.loc[keys, c], H.loc[keys, c])[0] for c in CATS])), len(keys), prof


out = []
examples = {}
for m in sorted(os.listdir(f"{REPO}/coded_generations/exp1")):
    rows_all, rows_clean = [], []
    n = n_phantom = n_empty_nocode = 0
    for p in sorted(glob.glob(f"{REPO}/coded_generations/exp1/{m}/*.csv")):
        for _, r in pd.read_csv(p).iterrows():
            fr = lit(r["frequencies"]); codes = lit(r["codes"]) or []; props = lit(r["properties"])
            if fr is None or len(fr) != 4:
                continue
            n += 1
            w = str(r["word"]).strip()
            row = dict(word=w, **dict(zip(CATS, [float(x) for x in fr])))
            rows_all.append(row)                     # what evaluate.py uses
            if is_empty(props):
                if codes:
                    n_phantom += 1
                    examples.setdefault(m, (w, r["properties"], r["codes"]))
                else:
                    n_empty_nocode += 1
                continue                              # clean: drop rows with no properties at all
            rows_clean.append(row)
    r_all, _, _ = mean_r(rows_all)
    r_clean, nk, _ = mean_r(rows_clean)
    out.append(dict(model=m, rows=n, phantom=n_phantom, phantom_pct=100 * n_phantom / n,
                    empty_zero=n_empty_nocode, r_repro=r_all, r_clean=r_clean,
                    delta=r_clean - r_all, words_clean=nk, paper=PAPER.get(m)))

df = pd.DataFrame(out).sort_values("r_repro", ascending=False).reset_index(drop=True)
df["rank_paper"] = df["r_repro"].rank(ascending=False, method="first").astype(int)
df["rank_clean"] = df["r_clean"].rank(ascending=False, method="first").astype(int)
pd.set_option("display.width", 200)
print(df[["model", "rows", "phantom", "phantom_pct", "empty_zero", "paper", "r_repro", "r_clean",
          "delta", "rank_paper", "rank_clean", "words_clean"]].round(3).to_string(index=False))
print()
print(f"total phantom rows: {df.phantom.sum()} of {df.rows.sum()} ({100*df.phantom.sum()/df.rows.sum():.1f}%)")
print(f"models with any phantom rows: {(df.phantom>0).sum()} / {len(df)}")
print(f"mean r, all 21, as released: {df.r_repro.mean():.3f}; with unparsed rows removed: {df.r_clean.mean():.3f}")
print(f"best model as released: {df.loc[df.r_repro.idxmax(),'model']} {df.r_repro.max():.3f}; "
      f"best after cleaning: {df.loc[df.r_clean.idxmax(),'model']} {df.r_clean.max():.3f}")
rho, p = stats.spearmanr(df.r_repro, df.r_clean)
print(f"rank agreement released vs cleaned: spearman {rho:.3f}")
r, p = stats.pearsonr(df.phantom_pct, df.delta)
print(f"phantom share vs change in r across models: pearson {r:+.3f} (p={p:.4f})")
print()
print("one example per affected model (word, stored properties, stored codes):")
for m, ex in list(examples.items())[:8]:
    print(f"  {m:24s} {ex[0]:14s} props={ex[1]}  codes={ex[2]}")

# what did the model actually say for those rows? check the raw generation for one model
m = "gemini-2.5-flash-lite"
g = pd.read_csv(f"{REPO}/generations/exp1/{m}_run_1.csv")
bad = g[g["properties"].apply(lambda s: is_empty(lit(s)))]
print(f"\n{m} run 1: {len(bad)} of {len(g)} raw responses produced no parsed properties. Five raw responses:")
for _, r in bad.head(5).iterrows():
    print("   ", repr(str(r["response"])[:90]))
df.to_csv(os.path.join(ROOT, "results", "parser_bug", "phantom_codes_by_model.csv"), index=False)
