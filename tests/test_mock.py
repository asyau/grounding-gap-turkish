"""End-to-end test of gg_tr.py with no network.

English arm: the mock replays the paper's own shipped gemini-2.5-flash-lite
generations and codes, so a correct pipeline should reproduce a Mean r close to
the published 0.348 (slightly different because we use 3 of the 10 runs).
Turkish arm: random but well-formed outputs, to exercise parsing and the stats.
"""
import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")

import ast, glob, os, random, re, shutil, sys, collections
import pandas as pd
sys.path.insert(0, os.path.join(ROOT, "src"))
import gg_tr as G

REPO = EXP
OUT = os.path.join(ROOT, "tests", "_out", "mock")
shutil.rmtree(OUT, ignore_errors=True)

en_gen_prompt = open(f"{REPO}/data/experiment_1/generation_prompt.txt").read()
en_code_prompt = open(f"{REPO}/data/experiment_1/coding_prompt.txt").read()
stim = pd.read_csv(os.path.join(ROOT, "data", "stimuli_tr.csv"), keep_default_na=False)
human = pd.read_csv(f"{REPO}/data/experiment_1/human_norms.csv").rename(columns={"IS/E": "IS_E"}).set_index("word")

# shipped flash-lite: per word, list of property lists (one per run), and (word, prop) -> raw label
ship_props = collections.defaultdict(list)
ship_label = {}
for p in sorted(glob.glob(f"{REPO}/coded_generations/exp1/gemini-2.5-flash-lite/*.csv")):
    df = pd.read_csv(p)
    for w, props, codes in zip(df["word"], df["properties"], df["codes"]):
        try:
            pl, cl = ast.literal_eval(props), ast.literal_eval(codes)
        except Exception:
            continue
        ship_props[str(w).strip()].append(pl)
        for a, b in zip(pl, cl):
            ship_label[(str(w).strip(), str(a).strip())] = str(b)

tr2en = dict(zip(stim["turkish"], stim["english"]))
call_count = collections.Counter()
TR_LABELS = ["Duyusal-motor özellik", "İçsel durum ve duygu", "Sosyal yapı", "Çağrışım", "Diğer soyut kavram"]
EN_LABELS = ["Sensorimotor feature", "Internal state and emotion", "Social constellation", "Association", "Other abstract concept"]

def mock_query(prompt, model_name, temperature=1.0, **_):
    if "word generation task" in prompt:                  # English generation
        w = re.search(r"given word '(.+?)'", prompt).group(1)
        k = call_count[("en", w)]; call_count[("en", w)] += 1
        props = ship_props[w][k % len(ship_props[w])]
        return f"word: {w}\nproperties: {', '.join(props)}"
    if "kelime üretme görevi" in prompt:                   # Turkish generation
        w = re.search(r"Verilen '(.+?)' kelimesi", prompt).group(1)
        return f"kelime: {w}\nözellikler: ağaç, kalp, aile, yol"
    if "Abstract word:" in prompt:                         # English-prompt coder (both arms)
        w = re.findall(r"Abstract word: (.+)", prompt)[-1].strip()
        props = [p.strip() for p in re.findall(r"Properties: (.+)", prompt)[-1].split(",")]
        key = tr2en.get(w, w)
        lines = []
        for p in props:
            lab = ship_label.get((key, p)) if key == w else None
            lines.append(f"{p}: {lab.title() if lab else random.choice(EN_LABELS)}")
        return "\n".join(lines)
    if "Soyut kelime:" in prompt:                          # Turkish-prompt coder
        props = [p.strip() for p in re.findall(r"Özellikler: (.+)", prompt)[-1].split(",")]
        return "\n".join(f"{p}: {random.choice(TR_LABELS)}" for p in props)
    raise ValueError("unexpected prompt")

random.seed(0)
N_RUNS = 3
en_stim = list(zip(stim["english"], stim["english"]))
tr_stim = list(zip(stim["english"], stim["turkish"]))
for run in range(1, N_RUNS + 1):
    G.generate(en_stim, en_gen_prompt, "m", f"{OUT}/gen/en_run_{run}.csv", mock_query, concurrency=8)
    G.generate(tr_stim, G.TR_GENERATION_PROMPT, "m", f"{OUT}/gen/tr_run_{run}.csv", mock_query, concurrency=8)
    G.code(f"{OUT}/gen/en_run_{run}.csv", en_code_prompt, "c", f"{OUT}/coded/en_run_{run}.csv", mock_query, G.EN_LABEL_MAP, 8)
    G.code(f"{OUT}/gen/tr_run_{run}.csv", en_code_prompt, "c", f"{OUT}/coded/tr_run_{run}.csv", mock_query, G.EN_LABEL_MAP, 8)
    G.code(f"{OUT}/gen/tr_run_{run}.csv", G.TR_CODING_PROMPT, "c", f"{OUT}/coded_trprompt/tr_run_{run}.csv", mock_query, G.TR_LABEL_MAP, 8)

# resume check: a second pass must do nothing
print("--- resume pass (should all say complete) ---")
G.generate(en_stim, en_gen_prompt, "m", f"{OUT}/gen/en_run_1.csv", mock_query)
G.code(f"{OUT}/gen/en_run_1.csv", en_code_prompt, "c", f"{OUT}/coded/en_run_1.csv", mock_query, G.EN_LABEL_MAP)

en = G.profile(G.load_coded(glob.glob(f"{OUT}/coded/en_run_*.csv")))
tr = G.profile(G.load_coded(glob.glob(f"{OUT}/coded/tr_run_*.csv")))
trp = G.profile(G.load_coded(glob.glob(f"{OUT}/coded_trprompt/tr_run_*.csv")))
keys = list(en.index.intersection(tr.index).intersection(human.index))
print(f"\nwords with both arms: {len(keys)}")
r_en, r_tr = G.mean_r(en, human, keys), G.mean_r(tr, human, keys)
print(f"English Mean r (mock replays shipped runs) = {r_en['mean']:.3f}   paper: 0.348 on 10 runs")
print(f"Turkish Mean r (random mock, expect ~0)    = {r_tr['mean']:.3f}")
print(f"Turkish-prompt coder parsed rows: {len(trp)} words")

shipped = G.load_shipped_profile(REPO, "gemini-2.5-flash-lite")
agree = G.cross_language_agreement(shipped, en)
print(f"our English vs shipped English profile agreement, mean r = {agree['mean']:.3f} (3 of 10 runs, expect high)")

b = G.paired_bootstrap(en, tr, human, keys, n_boot=300)
print("\npaired bootstrap Turkish minus English:")
for k, (p, lo, hi) in b.items():
    print(f"  {k:12s} {p:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
print("\nwithin-Turkish difference-in-differences:")
print(G.within_turkish_did(en, tr, stim, n_boot=300).round(3).to_string(index=False))
png = G.figure(human, en, tr, keys, "gemini-2.5-flash-lite (MOCK)", f"{OUT}/fig_mock",
               n_boot=300, r_en=r_en["mean"], r_tr=r_tr["mean"])
print("\nfigure:", png)
