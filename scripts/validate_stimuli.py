"""Check data/stimuli_tr.csv after any hand edit. Read-only.

Fails if a stimulus is missing or extra relative to the human norms, if two English
words map to the same Turkish word, or if a flag or origin value is misspelled.
"""
import os, sys
from collections import Counter
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPSTREAM = os.environ.get("GG_UPSTREAM", os.path.join(ROOT, "upstream", "grounding-gap"))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "stimuli_tr.csv")
norms = pd.read_csv(os.path.join(UPSTREAM, "property_generation_experiments", "data", "experiment_1", "human_norms.csv"))
s = pd.read_csv(path, keep_default_na=False)

need = {"english", "turkish", "alternative", "origin", "concrete_root", "flag", "note"}
errs = []
if need - set(s.columns):
    errs.append(f"missing columns: {sorted(need - set(s.columns))}")
else:
    en, nw = set(s.english.str.strip()), set(norms.word.astype(str).str.strip())
    if en != nw:
        errs.append(f"stimuli differ from the norms. missing={sorted(nw - en)} extra={sorted(en - nw)}")
    tr = s.turkish.str.strip()
    dup = sorted(tr[tr.duplicated()].unique())
    if dup:
        errs.append(f"two English words share a Turkish target: {dup}")
    if (tr == "").any():
        errs.append(f"empty Turkish for: {s.english[tr == ''].tolist()}")
    bad_o = set(s.origin) - {"native", "hybrid", "loan-arabic", "loan-persian", "loan-french", "loan-other"}
    bad_f = set(s.flag) - {"ok", "check", "hard"}
    if bad_o: errs.append(f"unknown origin values: {sorted(bad_o)}")
    if bad_f: errs.append(f"unknown flag values: {sorted(bad_f)}")
    print(f"rows {len(s)} | flags {dict(Counter(s.flag))} | origins {dict(Counter(s.origin))}")
    print(f"native with a transparent concrete root: {((s.origin == 'native') & (s.concrete_root != '')).sum()}")
if errs:
    print("STIMULI INVALID:"); [print("  -", e) for e in errs]; sys.exit(1)
print("STIMULI VALID")
