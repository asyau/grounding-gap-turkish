import os
import nbformat as nbf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MOD = open(os.path.join(ROOT, "src", "gg_tr.py"), encoding="utf-8").read()
STIM = open(os.path.join(ROOT, "data", "stimuli_tr.csv"), encoding="utf-8").read()

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# The Grounding Gap in Turkish

Extension of Chlapanis, Menis Mastromichalakis and Papadimitriou, *The Grounding Gap: How LLMs Anchor the Meaning of Abstract Concepts Differently from Humans* (arXiv 2605.08837). Code: [github.com/odychlapanis/grounding-gap](https://github.com/odychlapanis/grounding-gap).

**What this notebook does.** Runs the paper's Experiment 1 (Harpaintner et al. 2018, 293 abstract words) in English and in Turkish on the same model, **Gemini 2.5 Flash-Lite**, which is both one of the paper's 21 models (Mean r = 0.348) and its canonical coder. Every property in both languages is coded with the paper's own English coding prompt, so generation language is the only thing that changes between the two arms.

**Three comparisons.**
1. Turkish vs English, same model, both against the Harpaintner human norms. The norms come from German speakers, so English is already a translation of the original stimuli; neither language is the privileged one.
2. Within Turkish: does translating a concept into a transparent native word (*izlenim*, from *iz* "footprint") shift its profile more than translating it into an opaque loanword (*adalet*)? Each concept's English profile is its own baseline.
3. A correction to the released English leaderboard (optional, section 7).

**Before you start.**
- Put a Gemini API key in Colab secrets as `GEMINI_API_KEY` (key icon in the left sidebar). Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- **Gemini 2.5 Flash-Lite retires on the Gemini API no earlier than 16 October 2026.** Run this before then, or switch `MODEL` to `gemini-3.1-flash-lite`, which is also on the paper's leaderboard (Mean r = 0.223).
- Free tier works but is slow (about 15 requests a minute). The full run is roughly 3,500 calls. With billing enabled and a spending cap set, the whole study costs well under one US dollar and finishes in minutes. Set `FREE_TIER` accordingly.
- Every step is resumable and, with `USE_DRIVE = True`, saved to Google Drive. If Colab disconnects, reconnect and run all cells again; finished work is skipped.""")

code("""# ---- configuration ----
MODEL      = "gemini-2.5-flash-lite"   # generator; the paper's rank-3 model
CODER      = "gemini-2.5-flash-lite"   # the paper's canonical Experiment 1 coder
SHIPPED_DIR = "gemini-2.5-flash-lite"  # the paper's released runs for the same model (English sanity check)

N_RUNS     = 3        # the paper used 10; 3 gives split-half reliability around 0.74 for this model
SUBSET_N   = 30       # start with 30 words as a pilot, then set to None for all 293
FREE_TIER  = True     # False once billing is enabled with a spending cap
USE_DRIVE  = True     # save everything to Google Drive so a dead session loses nothing
SEED       = 0

RPM, CONCURRENCY = (14, 1) if FREE_TIER else (1500, 8)""")

code("""# ---- setup ----
import os, sys, subprocess
if not os.path.exists("/content/grounding-gap"):
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/odychlapanis/grounding-gap.git", "/content/grounding-gap"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "openai>=1.30", "pandas", "numpy", "scipy", "tqdm", "matplotlib"], check=True)
REPO = "/content/grounding-gap/property_generation_experiments"

if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT = "/content/drive/MyDrive/grounding_gap_tr"
else:
    OUT = "/content/gg_tr_out"
os.makedirs(OUT, exist_ok=True)

try:
    from google.colab import userdata
    API_KEY = userdata.get("GEMINI_API_KEY")
except Exception:
    import getpass
    API_KEY = getpass.getpass("Gemini API key: ")
assert API_KEY, "Add GEMINI_API_KEY to Colab secrets first"
print("repo:", REPO, "\\noutput:", OUT)""")

code("%%writefile /content/gg_tr.py\n" + MOD)

code('''# ---- Turkish stimuli ----
# The table below is the default. To use a corrected version, upload your edited
# stimuli_tr.csv into the output folder on Drive; it takes precedence.
import io, os, pandas as pd
DEFAULT_STIMULI = """''' + STIM.replace('"""', '\\"\\"\\"') + '''"""
path = os.path.join(OUT, "stimuli_tr.csv")
if os.path.exists(path):
    stim = pd.read_csv(path, keep_default_na=False); print("using your edited", path)
else:
    stim = pd.read_csv(io.StringIO(DEFAULT_STIMULI), keep_default_na=False)
    stim.to_csv(path, index=False); print("wrote default table to", path, "(edit it there if you change translations)")
print(stim.flag.value_counts().to_dict(), "|", stim.origin.value_counts().to_dict())
stim.head(8)''')

md("""### The smallest change to the original repo

The repo calls every model through OpenRouter. Gemini exposes an OpenAI-compatible endpoint, so pointing the repo at it is one new client file plus one registry line. The cell below writes both into the cloned repo, so the original `generate.py` and `code.py` also work with `--client gemini`. This notebook uses its own resumable runner, but it calls the same endpoint.""")

code('''gemini_client = \'\'\'"""Gemini client via Google's OpenAI-compatible endpoint.

Set GEMINI_API_KEY in the environment. Use model ids without a provider prefix,
e.g. gemini-2.5-flash-lite.
"""
import os
from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["GEMINI_API_KEY"],
                         base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    return _client


def query_llm(prompt, model_name, seed=None, temperature=1.0, max_tokens=512):
    model_name = model_name.split("/", 1)[-1]  # accept google/gemini-... too
    r = _get_client().chat.completions.create(
        model=model_name, messages=[{"role": "user", "content": prompt}],
        temperature=temperature, max_tokens=max_tokens)
    return r.choices[0].message.content or ""
\'\'\'
p = f"{REPO}/src/llm_clients/gemini.py"
open(p, "w").write(gemini_client)
reg = f"{REPO}/src/llm_clients/__init__.py"
s = open(reg).read()
if \'"gemini"\' not in s:
    s = s.replace(\'"local": "local",\', \'"local": "local",\\n    "gemini": "gemini",\')
    open(reg, "w").write(s)
os.environ["GEMINI_API_KEY"] = API_KEY
print(open(reg).read().split("REGISTRY")[1][:120])''')

code('''# ---- smoke test: one call per arm, printed raw ----
sys.path.insert(0, "/content")
import importlib, gg_tr as G; importlib.reload(G)
query = G.make_gemini_query(API_KEY, rpm=RPM)
avail = [m.id for m in query.client.models.list()]
print("flash-lite models on this key:", [m for m in avail if "flash-lite" in m])
assert any(MODEL in m for m in avail), f"{MODEL} is not available on this key; change MODEL"

EN_GEN = open(f"{REPO}/data/experiment_1/generation_prompt.txt").read()
EN_CODE = open(f"{REPO}/data/experiment_1/coding_prompt.txt").read()
for word, prompt in [("justice", EN_GEN), ("adalet", G.TR_GENERATION_PROMPT)]:
    r = query(prompt.replace("{word}", word), model_name=MODEL)
    props, mode = G.parse_properties(r, word)
    c = query(EN_CODE.replace("{word}", word).replace("{properties}", ", ".join(props)), model_name=CODER, temperature=0.0)
    print(f"--- {word} ---\\n{r}\\nparsed ({mode}): {props}\\ncoder:\\n{c}\\ncodes: {G.parse_codes(c, G.EN_LABEL_MAP)[0]}\\n")''')

md("## 1. Generate and code, both languages\nPilot first with `SUBSET_N = 30`. When the numbers look sane, set `SUBSET_N = None` and run this cell and everything below again.")

code('''rows = stim if SUBSET_N is None else stim.sample(SUBSET_N, random_state=SEED)
EN = list(zip(rows.english, rows.english))
TR = list(zip(rows.english, rows.turkish))
tag = "all" if SUBSET_N is None else f"sub{SUBSET_N}"
calls = len(rows) * 2 * 2 * N_RUNS
print(f"{len(rows)} words x 2 languages x (generate + code) x {N_RUNS} runs = up to {calls} calls")
print(f"at {RPM} requests/min that is about {calls / RPM / 60:.1f} h (finished work is skipped)")

for run in range(1, N_RUNS + 1):
    for lang, items, prompt in [("en", EN, EN_GEN), ("tr", TR, G.TR_GENERATION_PROMPT)]:
        gp = f"{OUT}/{MODEL}/gen/{lang}_run_{run}.csv"
        cp = f"{OUT}/{MODEL}/coded/{lang}_run_{run}.csv"
        G.generate(items, prompt, MODEL, gp, query, concurrency=CONCURRENCY)
        G.code(gp, EN_CODE, CODER, cp, query, G.EN_LABEL_MAP, concurrency=CONCURRENCY)
u = query.usage
print(f"calls this session {u.calls}, tokens in {u.prompt_tokens:,} out {u.completion_tokens:,}, "
      f"cost if billed about ${u.cost():.3f}")''')

md("## 2. Check the raw outputs before trusting any number\nFormat drift between languages is exactly how the released leaderboard lost a quarter of Flash-Lite's answers (section 7). This shows how each language's answers were parsed, and a sample of Turkish outputs for a native speaker to eyeball.")

code('''import glob
for lang in ["en", "tr"]:
    g = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/{MODEL}/gen/{lang}_run_*.csv"))])
    print(lang, "parse modes:", g.parse_mode.value_counts().to_dict())
g = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/{MODEL}/gen/tr_run_*.csv"))])
for _, r in g.sample(min(15, len(g)), random_state=SEED).iterrows():
    print(f"{r.stimulus:22s} -> {r.properties}")''')

md("## 3. Results")

code('''import numpy as np
human = pd.read_csv(f"{REPO}/data/experiment_1/human_norms.csv").rename(columns={"IS/E": "IS_E"})
human["word"] = human.word.astype(str).str.strip(); H = human.set_index("word")
en = G.profile(G.load_coded(glob.glob(f"{OUT}/{MODEL}/coded/en_run_*.csv")))
tr = G.profile(G.load_coded(glob.glob(f"{OUT}/{MODEL}/coded/tr_run_*.csv")))
keys = sorted(set(en.index) & set(tr.index) & set(H.index))
r_en, r_tr = G.mean_r(en, H, keys), G.mean_r(tr, H, keys)

print(f"words with both languages: {len(keys)}  runs: {N_RUNS}")
print(f"Mean r with human norms   English {r_en['mean']:.3f}   Turkish {r_tr['mean']:.3f}")
for c in G.CATS:
    print(f"   {G.CAT_LABELS[c]:20s} EN {r_en[c]:+.3f}   TR {r_tr[c]:+.3f}")

shipped = G.load_shipped_profile(REPO, SHIPPED_DIR, as_released=False)
if shipped is not None:
    rel = G.load_shipped_profile(REPO, SHIPPED_DIR, as_released=True)
    k2 = sorted(set(shipped.index) & set(en.index))
    print(f"\\nsanity: our English vs the paper's released {SHIPPED_DIR} runs, profile agreement r = "
          f"{G.cross_language_agreement(shipped.loc[k2], en.loc[k2])['mean']:.3f}")
    print(f"        paper's released runs on these words: Mean r {G.mean_r(rel, H, k2)['mean']:.3f} as released, "
          f"{G.mean_r(shipped, H, k2)['mean']:.3f} with unparsed answers dropped (see section 7)")

agree = G.cross_language_agreement(en.loc[keys], tr.loc[keys])
print(f"\\nsame model, English vs Turkish profile agreement: mean r = {agree['mean']:.3f}")
print("(how much of each concept's profile survives translation; the model's human alignment is the number above)")''')

code('''boot = G.paired_bootstrap(en, tr, H, keys, n_boot=2000, seed=SEED)
print("Turkish minus English, 95% bootstrap CI over words:")
for k, (p, lo, hi) in boot.items():
    lab = "Mean r with humans" if k == "d_mean_r" else "share of " + G.CAT_LABELS[k.split("_", 2)[2]]
    print(f"  {lab:32s} {p:+.3f}  [{lo:+.3f}, {hi:+.3f}]")

ok = [k for k in keys if stim.set_index("english").loc[k, "flag"] == "ok"]
b2 = G.paired_bootstrap(en, tr, H, ok, n_boot=2000, seed=SEED)
p, lo, hi = b2["d_mean_r"]
print(f"\\nrobustness, only the {len(ok)} confidently translated words: delta Mean r {p:+.3f} [{lo:+.3f}, {hi:+.3f}]")''')

md("### Within Turkish: transparent native words vs loanwords\nFor each concept, shift = Turkish share minus English share for the same model. The table compares the average shift for native words with a visible concrete root against loanwords. A positive Sensorimotor difference would mean a visible concrete root pulls the model toward bodily properties, which English cannot show because its abstract vocabulary is mostly opaque Latinate borrowing.")

code('''did = G.within_turkish_did(en.loc[keys], tr.loc[keys], stim, n_boot=2000, seed=SEED)
did.round(3)''')

code('''png = G.figure(H, en, tr, keys, MODEL, f"{OUT}/{MODEL}/fig_en_vs_tr", n_boot=2000, seed=SEED,
               r_en=r_en["mean"], r_tr=r_tr["mean"])
from IPython.display import Image; Image(png)''')

md("## 4. The numbers for the email")

code('''import json
p, lo, hi = boot["d_mean_r"]
sm = did.set_index("category").loc["Sensorimotor"]
summary = f"""On {len(keys)} abstract concepts, {N_RUNS} runs per language, {MODEL} generating and coding:
  Mean r with the Harpaintner human norms: English {r_en['mean']:.3f}, Turkish {r_tr['mean']:.3f}
  Turkish minus English: {p:+.3f} (95% CI {lo:+.3f} to {hi:+.3f})
  Internal-state share: English {en.loc[keys,'IS_E'].mean():.3f}, Turkish {tr.loc[keys,'IS_E'].mean():.3f}
  Verbal-association share: English {en.loc[keys,'VA'].mean():.3f}, Turkish {tr.loc[keys,'VA'].mean():.3f}
  Transparent native vs loanword, Sensorimotor shift difference: {sm.difference:+.3f} (95% CI {sm.ci_low:+.3f} to {sm.ci_high:+.3f})"""
print(summary)
res = dict(model=MODEL, coder=CODER, n_runs=N_RUNS, n_words=len(keys), subset=SUBSET_N,
           mean_r_en=r_en, mean_r_tr=r_tr, cross_language_agreement=agree,
           bootstrap_tr_minus_en={k: dict(point=v[0], ci_low=v[1], ci_high=v[2]) for k, v in boot.items()},
           bootstrap_ok_words_only=dict(n=len(ok), point=b2["d_mean_r"][0], ci_low=b2["d_mean_r"][1], ci_high=b2["d_mean_r"][2]),
           within_turkish=did.to_dict("records"))
os.makedirs(f"{OUT}/{MODEL}", exist_ok=True)
open(f"{OUT}/{MODEL}/summary_{tag}.txt", "w").write(summary + "\\n")
json.dump(res, open(f"{OUT}/{MODEL}/results_{tag}.json", "w"), indent=2, default=float)
did.to_csv(f"{OUT}/{MODEL}/within_turkish_{tag}.csv", index=False)
print(f"\\nsaved summary_{tag}.txt, results_{tag}.json and within_turkish_{tag}.csv in {OUT}/{MODEL}")''')

md("""## 5. Limitations to state before anyone else does
- **No Turkish human norms.** The human side of both comparisons is German speakers (Harpaintner et al. 2018). English is already a translation of their stimuli, so the Turkish arm is no less legitimate than the English one, but a difference between them is a difference in the model, not proof that the human-model gap differs.
- **Translation.** The Turkish list was translated from the English list, not from the original German, and 29 items have no clean one-to-one equivalent (`flag = hard`). The robustness line in section 3 reruns the main comparison on confidently translated items only.
- **Origins** (native, hybrid, loan) are a first pass and should be checked against Nişanyan Sözlüğü before the within-Turkish contrast is reported.
- **Reform-era coinages.** Many transparent native words (*içgörü*, *öngörü*, *kavram*, *izlenim*) were coined in the 20th-century language reform. Transparency and recency are confounded.
- **Coder.** Turkish properties are coded with the English prompt by a model reading Turkish. Section 6 reruns the coding with a Turkish prompt as a check.
- **Runs.** 3 runs, not the paper's 10.""")

md("## 6. Optional robustness: code the Turkish properties with a Turkish coding prompt")

code('''for run in range(1, N_RUNS + 1):
    G.code(f"{OUT}/{MODEL}/gen/tr_run_{run}.csv", G.TR_CODING_PROMPT, CODER,
           f"{OUT}/{MODEL}/coded_trprompt/tr_run_{run}.csv", query, G.TR_LABEL_MAP, concurrency=CONCURRENCY)
trp = G.profile(G.load_coded(glob.glob(f"{OUT}/{MODEL}/coded_trprompt/tr_run_*.csv")))
kk = sorted(set(keys) & set(trp.index))
print(f"Turkish, Turkish coding prompt: Mean r = {G.mean_r(trp, H, kk)['mean']:.3f} (English prompt: {G.mean_r(tr, H, kk)['mean']:.3f})")
print("agreement between the two codings of the same Turkish properties:",
      round(G.cross_language_agreement(tr.loc[kk], trp.loc[kk])['mean'], 3))''')

md("""## 7. Optional: correcting the released English leaderboard

The repo's parser only accepts answers that contain the literal label `properties:`. When a model answers `anger: shouting, red face, clenched fists, frustration` instead, the parser returns nothing, and `evaluate.py` averages that word's run in as an all-zero profile. In the released data this affects 25% of Gemini 2.5 Flash-Lite's word-runs, 41% of Llama 3.1 8B's and 17% of GPT-OSS 120B's. Simply dropping those rows (no API calls) moves Flash-Lite from 0.348 to 0.394 and Llama 3.1 8B from 0.283 to 0.339.

This cell does it properly: recovers the properties with a format-tolerant parser, codes them with the paper's coder, and recomputes. It is the only way to get the exact corrected numbers, and it needs Gemini 2.5 Flash-Lite, so it too has to run before the model retires.""")

code('''AFFECTED = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gpt-oss-120b", "llama-3.1-8b"]
rows_out = []
for m in AFFECTED:
    rec = G.recover_shipped(REPO, m)
    rec = rec[rec.properties.apply(len) > 0]
    paths = {}
    for run, grp in rec.groupby("run"):
        gp = f"{OUT}/corrected/{m}/gen_run_{run}.csv"
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        grp[["key", "stimulus", "response", "properties", "parse_mode"]].to_csv(gp, index=False)
        cp = f"{OUT}/corrected/{m}/coded_run_{run}.csv"
        G.code(gp, EN_CODE, CODER, cp, query, G.EN_LABEL_MAP, concurrency=CONCURRENCY)
        paths[run] = cp
    released = G.load_shipped_profile(REPO, m, as_released=True)
    dropped, _ = G.corrected_profile(REPO, m, {})
    fixed, info = G.corrected_profile(REPO, m, paths)
    rows_out.append(dict(model=m, released=G.mean_r(released, H)["mean"], empties_dropped=G.mean_r(dropped, H)["mean"],
                         recovered_and_recoded=G.mean_r(fixed, H)["mean"], **info))
corr = pd.DataFrame(rows_out).round(3); corr.to_csv(f"{OUT}/corrected_leaderboard.csv", index=False); corr''')

code('''# ---- bundle everything for download ----
import shutil
z = shutil.make_archive("/content/grounding_gap_tr_results", "zip", OUT)
print(z)
try:
    from google.colab import files; files.download(z)
except Exception:
    pass''')

nb["cells"] = C
nb["metadata"] = {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"},
                  "language_info": {"name": "python"}}
nbf.write(nb, os.path.join(ROOT, "notebooks", "grounding_gap_turkish.ipynb"))
print("cells:", len(C))
