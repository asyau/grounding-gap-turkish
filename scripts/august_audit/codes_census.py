import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os, glob, ast, collections
os.chdir(EXP)
import pandas as pd

c = collections.Counter()
per_model = collections.defaultdict(collections.Counter)
for m in sorted(os.listdir("coded_generations/exp1")):
    for p in glob.glob(f"coded_generations/exp1/{m}/*.csv"):
        for v in pd.read_csv(p)["codes"]:
            try:
                for x in ast.literal_eval(str(v)):
                    c[str(x).strip().lower()] += 1
                    per_model[m][str(x).strip().lower()] += 1
            except Exception:
                pass

print("=== distinct raw coder labels across all shipped coded runs ===")
tot = sum(c.values())
for k, v in c.most_common():
    print(f"   {k:30s} {v:8d}  {100.0*v/tot:5.2f}%")
print(f"   {'TOTAL':30s} {tot:8d}")
print()

key = "other abstract concept"
print(f"=== share of '{key}' per model (this is the half of Verbal Association that is NOT plain association) ===")
rows = []
for m, cc in per_model.items():
    t = sum(cc.values())
    va = cc.get("association", 0) + cc.get(key, 0)
    rows.append((m, 100.0 * cc.get(key, 0) / t, 100.0 * cc.get("association", 0) / t, 100.0 * va / t,
                 100.0 * cc.get(key, 0) / va if va else 0.0))
rows.sort(key=lambda r: -r[1])
print(f"{'model':24s} {'other-abs%':>11s} {'assoc%':>9s} {'VA total%':>10s} {'other/VA%':>10s}")
print("-" * 70)
for m, oa, a, va, frac in rows:
    print(f"{m:24s} {oa:10.2f}% {a:8.2f}% {va:9.2f}% {frac:9.1f}%")
