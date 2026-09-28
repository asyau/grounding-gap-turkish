import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os
sys.path.insert(0, EXP)
os.chdir(EXP)
import pandas as pd, numpy as np
from src.experiments import get_config

cfg = get_config(1)
gt = pd.read_csv("data/experiment_1/coding_human_ground_truth.csv")
gt["word"] = gt["word"].astype(str).str.strip()

print("=== Expert ground-truth coding set ===")
print("rows (properties):", len(gt))
print("distinct words   :", gt["word"].nunique())
print("properties/word  : mean %.2f  min %d  max %d" % (
    gt.groupby("word").size().mean(), gt.groupby("word").size().min(), gt.groupby("word").size().max()))
print()

LAB2CAT = {"sensorimotor": "SM", "emotion": "IS_E", "social": "SC", "association": "VA"}
gt["cat"] = gt["label"].map(LAB2CAT)
assert gt["cat"].notna().all(), "unmapped label"

# marginal distribution over all properties
marg = gt["cat"].value_counts(normalize=True).reindex(cfg.cats)
# per-word profile then averaged (this is how the norms are built)
prof = (gt.groupby(["word", "cat"]).size().unstack(fill_value=0).reindex(columns=cfg.cats, fill_value=0))
prof = prof.div(prof.sum(axis=1), axis=0)

human = cfg.load_norms()
human["word"] = human["word"].astype(str).str.strip()
norms_mean = [human[c].mean() for c in cfg.cats]

print(f"{'source':38s} " + " ".join(f"{l[:6]:>8s}" for l in cfg.cat_labels))
print("-" * 74)
print(f"{'expert GT, pooled over properties':38s} " + " ".join(f"{marg[c]:8.3f}" for c in cfg.cats))
print(f"{'expert GT, per-word then averaged':38s} " + " ".join(f"{prof[c].mean():8.3f}" for c in cfg.cats))
print(f"{'published human norms (293 words)':38s} " + " ".join(f"{x:8.3f}" for x in norms_mean))
print(f"{'Harpaintner 2018 reported means':38s} " + " ".join(f"{x:8.3f}" for x in [0.337, 0.325, 0.078, 0.260]))
print()

# overlap of GT words with the norms
ov = set(prof.index) & set(human["word"])
print(f"GT words also in the 293-word norms: {len(ov)}")
sub = prof.loc[sorted(ov)]
hsub = human.set_index("word").loc[sorted(ov)]
print()
print("Per-category correlation between the expert GT subset profiles and the published norms")
print("(sanity check that the GT file is a subsample of the same coding process)")
from scipy import stats
for c in cfg.cats:
    r, _ = stats.pearsonr(sub[c].values, hsub[c].values.astype(float))
    print(f"   {c:6s} r = {r:.3f}")

sub.to_csv(os.path.join(ROOT, "results", "august_audit", "gt_expert_profiles.csv"))
print("\nwrote results/august_audit/gt_expert_profiles.csv  (per-word expert profiles, the reference for the coder-bias test)")
