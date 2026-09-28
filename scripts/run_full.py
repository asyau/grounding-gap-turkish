import glob
import io
import json
import os
import sys
import pandas as pd

sys.path.insert(0, ".")
import src.gg_tr as G

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required.")
MODEL = "gemini-3.1-flash-lite"
CODER = "gemini-3.1-flash-lite"
SHIPPED_DIR = "gemini-3.1-flash-lite"
REPO = "upstream/grounding-gap/property_generation_experiments"
OUT = "results/live_run"
CONCURRENCY = 8
RPM = 1500
N_RUNS = 3
SUBSET_N = None
SEED = 0

os.makedirs(OUT, exist_ok=True)
query = G.make_gemini_query(API_KEY, rpm=RPM)

stim = pd.read_csv("data/stimuli_tr.csv", keep_default_na=False)

EN_GEN = open(f"{REPO}/data/experiment_1/generation_prompt.txt", encoding="utf-8").read()
EN_CODE = open(f"{REPO}/data/experiment_1/coding_prompt.txt", encoding="utf-8").read()

rows = stim if SUBSET_N is None else stim.sample(SUBSET_N, random_state=SEED)
EN = list(zip(rows.english, rows.english))
TR = list(zip(rows.english, rows.turkish))
tag = "all" if SUBSET_N is None else f"sub{SUBSET_N}"
calls = len(rows) * 2 * 2 * N_RUNS
print(f"\n=== Full Run ({len(rows)} words) ===")
print(f"{len(rows)} words x 2 languages x (generate + code) x {N_RUNS} runs = up to {calls} calls")

for run in range(1, N_RUNS + 1):
    for lang, items, prompt in [("en", EN, EN_GEN), ("tr", TR, G.TR_GENERATION_PROMPT)]:
        gp = f"{OUT}/{MODEL}/gen/{lang}_run_{run}.csv"
        cp = f"{OUT}/{MODEL}/coded/{lang}_run_{run}.csv"
        G.generate(items, prompt, MODEL, gp, query, concurrency=CONCURRENCY)
        G.code(gp, EN_CODE, CODER, cp, query, G.EN_LABEL_MAP, concurrency=CONCURRENCY)

u = query.usage
print(f"\nCalls so far {u.calls}, tokens in {u.prompt_tokens:,} out {u.completion_tokens:,}, cost ~${u.cost():.3f}")

print("\n=== Section 2: Parse modes and Turkish samples ===")
for lang in ["en", "tr"]:
    g = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/{MODEL}/gen/{lang}_run_*.csv"))])
    print(lang, "parse modes:", g.parse_mode.value_counts().to_dict())

g_tr = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(f"{OUT}/{MODEL}/gen/tr_run_*.csv"))])
print("\nSample of Turkish outputs (15 random concepts):")
for _, r in g_tr.sample(min(15, len(g_tr)), random_state=SEED).iterrows():
    print(f"{r.stimulus:22s} -> {r.properties}")

print("\n=== Section 3: Results ===")
human = pd.read_csv(f"{REPO}/data/experiment_1/human_norms.csv").rename(columns={"IS/E": "IS_E"})
human["word"] = human.word.astype(str).str.strip()
H = human.set_index("word")

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
    print(f"\nsanity: our English vs the paper's released {SHIPPED_DIR} runs, profile agreement r = "
          f"{G.cross_language_agreement(shipped.loc[k2], en.loc[k2])['mean']:.3f}")
    print(f"        paper's released runs on these words: Mean r {G.mean_r(rel, H, k2)['mean']:.3f} as released, "
          f"{G.mean_r(shipped, H, k2)['mean']:.3f} with unparsed answers dropped (see section 7)")

agree = G.cross_language_agreement(en.loc[keys], tr.loc[keys])
print(f"\nsame model, English vs Turkish profile agreement: mean r = {agree['mean']:.3f}")

boot = G.paired_bootstrap(en, tr, H, keys, n_boot=2000, seed=SEED)
print("\nTurkish minus English, 95% bootstrap CI over words:")
for k, (p, lo, hi) in boot.items():
    lab = "Mean r with humans" if k == "d_mean_r" else "share of " + G.CAT_LABELS[k.split("_", 2)[2]]
    print(f"  {lab:32s} {p:+.3f}  [{lo:+.3f}, {hi:+.3f}]")

ok = [k for k in keys if stim.set_index("english").loc[k, "flag"] == "ok"]
b2 = G.paired_bootstrap(en, tr, H, ok, n_boot=2000, seed=SEED)
p, lo, hi = b2["d_mean_r"]
print(f"\nrobustness, only the {len(ok)} confidently translated words: delta Mean r {p:+.3f} [{lo:+.3f}, {hi:+.3f}]")

did = G.within_turkish_did(en.loc[keys], tr.loc[keys], stim, n_boot=2000, seed=SEED)
print("\nWithin Turkish differences:")
print(did.round(3).to_string())

png = G.figure(H, en, tr, keys, MODEL, f"{OUT}/{MODEL}/fig_en_vs_tr", n_boot=2000, seed=SEED,
               r_en=r_en["mean"], r_tr=r_tr["mean"])
print(f"\nFigure saved to {png}")

# Section 4: Summary for email
p, lo, hi = boot["d_mean_r"]
sm = did.set_index("category").loc["Sensorimotor"]
summary = f"""On {len(keys)} abstract concepts, {N_RUNS} runs per language, {MODEL} generating and coding:
  Mean r with the Harpaintner human norms: English {r_en['mean']:.3f}, Turkish {r_tr['mean']:.3f}
  Turkish minus English: {p:+.3f} (95% CI {lo:+.3f} to {hi:+.3f})
  Internal-state share: English {en.loc[keys,'IS_E'].mean():.3f}, Turkish {tr.loc[keys,'IS_E'].mean():.3f}
  Verbal-association share: English {en.loc[keys,'VA'].mean():.3f}, Turkish {tr.loc[keys,'VA'].mean():.3f}
  Transparent native vs loanword, Sensorimotor shift difference: {sm.difference:+.3f} (95% CI {sm.ci_low:+.3f} to {sm.ci_high:+.3f})"""
print("\n=== Summary ===")
print(summary)

res = dict(model=MODEL, coder=CODER, n_runs=N_RUNS, n_words=len(keys), subset=SUBSET_N,
           mean_r_en=r_en, mean_r_tr=r_tr, cross_language_agreement=agree,
           bootstrap_tr_minus_en={k: dict(point=v[0], ci_low=v[1], ci_high=v[2]) for k, v in boot.items()},
           bootstrap_ok_words_only=dict(n=len(ok), point=b2["d_mean_r"][0], ci_low=b2["d_mean_r"][1], ci_high=b2["d_mean_r"][2]),
           within_turkish=did.to_dict("records"))
os.makedirs(f"{OUT}/{MODEL}", exist_ok=True)
open(f"{OUT}/{MODEL}/summary_{tag}.txt", "w").write(summary + "\n")
json.dump(res, open(f"{OUT}/{MODEL}/results_{tag}.json", "w"), indent=2, default=float)
did.to_csv(f"{OUT}/{MODEL}/within_turkish_{tag}.csv", index=False)
print(f"\nsaved summary_{tag}.txt, results_{tag}.json and within_turkish_{tag}.csv in {OUT}/{MODEL}")

# Section 6: Robustness check with Turkish coding prompt
print("\n=== Section 6: Turkish coding prompt robustness check ===")
for run in range(1, N_RUNS + 1):
    G.code(f"{OUT}/{MODEL}/gen/tr_run_{run}.csv", G.TR_CODING_PROMPT, CODER,
           f"{OUT}/{MODEL}/coded_trprompt/tr_run_{run}.csv", query, G.TR_LABEL_MAP, concurrency=CONCURRENCY)
trp = G.profile(G.load_coded(glob.glob(f"{OUT}/{MODEL}/coded_trprompt/tr_run_*.csv")))
kk = sorted(set(keys) & set(trp.index))
r_tr_trp = G.mean_r(trp, H, kk)['mean']
r_tr_enp = G.mean_r(tr, H, kk)['mean']
agree_prompts = round(G.cross_language_agreement(tr.loc[kk], trp.loc[kk])['mean'], 3)
print(f"Turkish, Turkish coding prompt: Mean r = {r_tr_trp:.3f} (English prompt: {r_tr_enp:.3f})")
print(f"agreement between the two codings of the same Turkish properties: {agree_prompts}")

u = query.usage
print(f"\nTotal run complete! Calls this session {u.calls}, tokens in {u.prompt_tokens:,} out {u.completion_tokens:,}, cost ~${u.cost():.3f}")
