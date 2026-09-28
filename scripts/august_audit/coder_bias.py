"""Does the LLM coder label the SAME properties differently from human experts?

The repo ships expert hand-coded labels for 2077 model-generated properties, and every
coded run stores the coder's own raw label for each property it saw. Intersecting the
two gives the coder's confusion matrix and its MARGINAL BIAS on identical inputs.

No API calls. Everything comes from files already in the repository.
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
from src.parsers import EXP1_LABEL_MAP

CATS = ["SM", "IS_E", "SC", "VA"]
LABELS = {"SM": "Sensorimotor", "IS_E": "Internal", "SC": "Social", "VA": "Verbal"}
LAB2CAT = {"sensorimotor": "SM", "emotion": "IS_E", "social": "SC", "association": "VA"}

gt = pd.read_csv("data/experiment_1/coding_human_ground_truth.csv")
gt["word"] = gt["word"].astype(str).str.strip().str.lower()
gt["property"] = gt["property"].astype(str).str.strip().str.lower()
gt["cat"] = gt["label"].map(LAB2CAT)
expert = dict(zip(zip(gt["word"], gt["property"]), gt["cat"]))

coder = collections.defaultdict(list)
coder5 = collections.defaultdict(list)
n_dec = n_bad = 0
for m in sorted(os.listdir("coded_generations/exp1")):
    for p in glob.glob(f"coded_generations/exp1/{m}/*.csv"):
        df = pd.read_csv(p)
        for w, props, codes in zip(df["word"], df["properties"], df["codes"]):
            try:
                pl = ast.literal_eval(str(props)); cl = ast.literal_eval(str(codes))
            except Exception:
                continue
            if not isinstance(pl, list) or not isinstance(cl, list) or len(pl) != len(cl):
                continue
            w = str(w).strip().lower()
            for pr, raw in zip(pl, cl):
                raw = str(raw).strip().lower()
                n_dec += 1
                cd = next((v for k, v in EXP1_LABEL_MAP.items() if k in raw), None)
                if cd is None:
                    n_bad += 1
                    continue
                key = (w, str(pr).strip().lower())
                coder[key].append(cd)
                coder5[key].append(raw if raw in EXP1_LABEL_MAP else raw)

print(f"coder decisions parsed        : {n_dec}")
print(f"unmappable (silently dropped) : {n_bad}  ({100.0*n_bad/n_dec:.2f}%)")
print()

pairs = [k for k in expert if k in coder]
print(f"expert-labelled properties    : {len(expert)}")
print(f"also seen by the LLM coder    : {len(pairs)}  ({100.0*len(pairs)/len(expert):.1f}%)")
print(f"coder decisions on those      : {sum(len(coder[k]) for k in pairs)}")
print()

modal = lambda v: collections.Counter(v).most_common(1)[0][0]
y_true = [expert[k] for k in pairs]
y_pred = [modal(coder[k]) for k in pairs]

cm = pd.DataFrame(0, index=CATS, columns=CATS)
for t, p in zip(y_true, y_pred):
    cm.loc[t, p] += 1

print("=== Confusion matrix: rows = expert, cols = LLM coder (modal label) ===")
d = cm.copy(); d.index = [LABELS[c] for c in CATS]; d.columns = [LABELS[c] for c in CATS]
print(d.to_string()); print()

N = cm.values.sum()
acc = np.trace(cm.values) / N
pe = sum((cm.values.sum(1)[i]/N) * (cm.values.sum(0)[i]/N) for i in range(4))
print(f"overall agreement : {acc*100:.1f}%   (paper reports 67.2%)")
print(f"Cohen's kappa     : {(acc-pe)/(1-pe):.3f}      (paper reports 0.505)")
print()

print(f"{'category':14s} {'n_expert':>9s} {'recall':>8s} {'precision':>10s}   paper recall")
paper_rec = {"SM": 66.2, "IS_E": 75.9, "SC": 62.1, "VA": 67.1}
for c in CATS:
    n = cm.loc[c].sum(); npred = cm[c].sum()
    print(f"{LABELS[c]:14s} {n:9d} {cm.loc[c,c]/n*100:7.1f}% {cm.loc[c,c]/npred*100:9.1f}%   {paper_rec[c]:11.1f}%")
print()

print("=== MARGINAL BIAS: same properties, two labellers ===")
e = np.array([cm.loc[c].sum() for c in CATS], float); e /= e.sum()
o = np.array([cm[c].sum() for c in CATS], float); o /= o.sum()
gap = np.array([-0.060, -0.187, 0.019, 0.186])
print(f"{'':32s} " + " ".join(f"{LABELS[c]:>13s}" for c in CATS))
print(f"{'expert humans':32s} " + " ".join(f"{x:13.3f}" for x in e))
print(f"{'gemini-2.5-flash-lite coder':32s} " + " ".join(f"{x:13.3f}" for x in o))
print(f"{'coder minus expert':32s} " + " ".join(f"{x:+13.3f}" for x in o - e))
print(f"{'paper reported gap, for scale':32s} " + " ".join(f"{x:+13.3f}" for x in gap))
print()
print("coder shift as a share of the reported gap:")
for c, s in zip(CATS, (o - e) / gap):
    print(f"   {LABELS[c]:14s} {s*100:+6.1f}%")
