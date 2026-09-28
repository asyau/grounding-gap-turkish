import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os, random
sys.path.insert(0, EXP)
os.chdir(EXP)
import numpy as np
from scipy import stats
from evaluate import aggregate, discover_models, correlate
from src.experiments import get_config

cfg = get_config(1)
human = cfg.load_norms()
human[cfg.word_column] = human[cfg.word_column].astype(str).str.strip()
models = discover_models(cfg.coded_dir)
random.seed(0)
REL_H = 0.974

print("Split-half reliability of each MODEL's own per-word category profile")
print("(5v5 run splits x50, Pearson per category, Spearman-Brown corrected to 10 runs)")
print()
hdr = f"{'model':24s} {'obs r':>7s} {'rel_m':>7s} {'r_corr':>7s}   " + " ".join(f"{l[:6]:>7s}" for l in cfg.cat_labels)
print(hdr)
print("-" * len(hdr))

rows = []
for m, runs in models.items():
    idx = list(range(len(runs)))
    rels = {c: [] for c in cfg.cats}
    for _ in range(50):
        random.shuffle(idx)
        h = len(idx) // 2
        a = aggregate([runs[i] for i in idx[:h]], cfg.cats)
        b = aggregate([runs[i] for i in idx[h:2 * h]], cfg.cats)
        mg = a.merge(b, on="word", suffixes=("_a", "_b"))
        for c in cfg.cats:
            r, _ = stats.pearsonr(mg[f"{c}_a"], mg[f"{c}_b"])
            rels[c].append(r)
    sb = {}
    for c in cfg.cats:
        rh = float(np.mean(rels[c]))
        sb[c] = 2 * rh / (1 + rh)
    rel_m = float(np.mean(list(sb.values())))
    obs = correlate(aggregate(runs, cfg.cats), human, cfg.word_column, cfg.cats)
    rows.append((m, obs["mean"], rel_m, obs["mean"] / np.sqrt(rel_m * REL_H), [sb[c] for c in cfg.cats]))

rows.sort(key=lambda r: -r[1])
for m, obs, rel, corr, per in rows:
    print(f"{m:24s} {obs:7.3f} {rel:7.3f} {corr:7.3f}   " + " ".join(f"{x:7.3f}" for x in per))

print()
print(f"{'MEAN over 21 models':24s} {np.mean([r[1] for r in rows]):7.3f} "
      f"{np.mean([r[2] for r in rows]):7.3f} {np.mean([r[3] for r in rows]):7.3f}")
print()
print(f"Human ceiling used: {REL_H}")
print(f"Best observed r = {max(r[1] for r in rows):.3f}")
print(f"Best disattenuated r = {max(r[3] for r in rows):.3f}")
