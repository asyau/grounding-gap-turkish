"""Does the composition of a model's 'Verbal Association' mass predict its alignment?

'Verbal Association' merges two coder categories: plain 'association' (thematic /
symbolic links) and 'other abstract concept' (abstract features that define the word).
Harpaintner merged them too, so the merge is fair. But the merged number hides which
of the two a model actually produces, and that varies a lot across models.
"""
import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")

import sys, os, glob, ast, collections
sys.path.insert(0, EXP)
os.chdir(EXP)
import pandas as pd, numpy as np
from scipy import stats
from evaluate import aggregate, discover_models, correlate
from src.experiments import get_config

cfg = get_config(1)
human = cfg.load_norms(); human[cfg.word_column] = human[cfg.word_column].astype(str).str.strip()
models = discover_models(cfg.coded_dir)

rows = []
for m, runs in models.items():
    c = collections.Counter()
    for p in runs:
        for v in pd.read_csv(p)["codes"]:
            try:
                for x in ast.literal_eval(str(v)):
                    c[str(x).strip().lower()] += 1
            except Exception:
                pass
    oa, asc = c.get("other abstract concept", 0), c.get("association", 0)
    va = oa + asc
    tot = sum(v for k, v in c.items() if k in
              {"sensorimotor feature", "internal state and emotion", "social constellation",
               "association", "other abstract concept"})
    obs = correlate(aggregate(runs, cfg.cats), human, cfg.word_column, cfg.cats)
    rows.append(dict(model=m, oa_share_of_va=oa/va, oa_of_all=oa/tot, va_of_all=va/tot,
                     mean_r=obs["mean"], sm=obs["SM"], ise=obs["IS_E"], sc=obs["SC"], va_r=obs["VA"]))

df = pd.DataFrame(rows).sort_values("oa_share_of_va", ascending=False)
print("=== 'Other abstract concept' as a share of each model's Verbal Association mass ===")
print(f"{'model':24s} {'oa/VA':>8s} {'VA share':>9s} {'Mean r':>8s}")
print("-" * 54)
for _, r in df.iterrows():
    print(f"{r['model']:24s} {r['oa_share_of_va']*100:7.1f}% {r['va_of_all']*100:8.1f}% {r['mean_r']:8.3f}")

print()
print("range: %.1f%% (%s) to %.1f%% (%s) -> %.1fx spread" % (
    df["oa_share_of_va"].min()*100, df.iloc[-1]["model"],
    df["oa_share_of_va"].max()*100, df.iloc[0]["model"],
    df["oa_share_of_va"].max()/df["oa_share_of_va"].min()))
print()

print("=== Correlation across the 21 models ===")
for target, name in [("mean_r", "Mean r"), ("sm", "Sensorimotor r"), ("ise", "Internal r"),
                     ("sc", "Social r"), ("va_r", "Verbal r")]:
    r, p = stats.pearsonr(df["oa_share_of_va"], df[target])
    rho, prho = stats.spearmanr(df["oa_share_of_va"], df[target])
    print(f"  oa/VA  vs  {name:16s}  pearson r = {r:+.3f} (p={p:.4f})   spearman = {rho:+.3f} (p={prho:.4f})")
print()
r, p = stats.pearsonr(df["va_of_all"], df["mean_r"])
print(f"  control: total VA share vs Mean r          pearson r = {r:+.3f} (p={p:.4f})")
r, p = stats.pearsonr(df["oa_of_all"], df["mean_r"])
print(f"  control: oa share of ALL codes vs Mean r   pearson r = {r:+.3f} (p={p:.4f})")

df.to_csv(os.path.join(ROOT, "results", "august_audit", "abstract_share.csv"), index=False)
print("\nwrote results/august_audit/abstract_share.csv")
