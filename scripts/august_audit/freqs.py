import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os, glob
os.chdir(EXP); sys.path.insert(0, EXP)
import numpy as np, pandas as pd
from evaluate import aggregate, discover_models
from src.experiments import get_config
cfg=get_config(1)
h=cfg.load_norms()
print("human norms columns:", list(h.columns), " rows:", len(h))
hm=[h[c].mean() for c in cfg.cats]
print(f"\n{'source':24s} " + " ".join(f"{l:>13s}" for l in cfg.cat_labels))
print(f"{'HUMAN (Harpaintner)':24s} " + " ".join(f"{x:13.3f}" for x in hm))
print("-"*24)
models=discover_models(cfg.coded_dir)
allm=[]
for m,runs in models.items():
    a=aggregate(runs,cfg.cats); mv=[a[c].mean() for c in cfg.cats]; allm.append(mv)
    print(f"{m:24s} " + " ".join(f"{x:13.3f}" for x in mv))
am=np.mean(allm,axis=0)
print("-"*24)
print(f"{'MODEL MEAN (21)':24s} " + " ".join(f"{x:13.3f}" for x in am))
print(f"{'DELTA (model - human)':24s} " + " ".join(f"{x:+13.3f}" for x in am-np.array(hm)))
