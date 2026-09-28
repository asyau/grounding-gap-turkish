import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os, itertools, glob
os.chdir(EXP); sys.path.insert(0, EXP)
from evaluate import aggregate, correlate
from src.experiments import get_config

cfg = get_config(1)
human = cfg.load_norms(); human[cfg.word_column]=human[cfg.word_column].astype(str).str.strip()

targets = {
 "claude-haiku-4.5": [0.257,0.251,0.191,0.310,0.276],
 "qwen3-4b-2507":   [0.314,0.335,0.405,0.318,0.200],
}
for model,tgt in targets.items():
    d=os.path.join(cfg.coded_dir,model)
    runs=sorted(glob.glob(os.path.join(d,"*_coded_with_*_run_*.csv")))
    print(f"\n### {model}: {len(runs)} coded run files")
    # row counts per run
    import pandas as pd
    for p in runs:
        n=len(pd.read_csv(p)); print(f"   {os.path.basename(p):70s} rows={n}")
    print(f"   paper target: mean={tgt[0]} {tgt[1:]}")
    best=None
    for k in (len(runs), len(runs)-1):
        for subset in itertools.combinations(runs,k):
            rs=correlate(aggregate(list(subset),cfg.cats),human,cfg.word_column,cfg.cats)
            got=[rs["mean"]]+[rs[c] for c in cfg.cats]
            err=max(abs(g-t) for g,t in zip(got,tgt))
            excluded = [os.path.basename(p).split("_run_")[-1].replace(".csv","") for p in runs if p not in subset]
            if best is None or err<best[0]: best=(err,k,excluded,got)
    err,k,excl,got=best
    print(f"   BEST FIT: n_runs={k} excluded_run={excl or 'none'} maxerr={err:.4f}")
    print(f"      repro:  mean={got[0]:.3f} " + " ".join(f"{x:.3f}" for x in got[1:]))
