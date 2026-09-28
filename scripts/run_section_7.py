import os
import sys
import pandas as pd

sys.path.insert(0, ".")
import src.gg_tr as G

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required.")
CODER = "gemini-3.1-flash-lite"
REPO = "upstream/grounding-gap/property_generation_experiments"
OUT = "results/live_run"
CONCURRENCY = 8
RPM = 1500

os.makedirs(OUT, exist_ok=True)
query = G.make_gemini_query(API_KEY, rpm=RPM)
human = pd.read_csv(f"{REPO}/data/experiment_1/human_norms.csv").rename(columns={"IS/E": "IS_E"})
human["word"] = human.word.astype(str).str.strip()
H = human.set_index("word")
EN_CODE = open(f"{REPO}/data/experiment_1/coding_prompt.txt", encoding="utf-8").read()

AFFECTED = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gpt-oss-120b", "llama-3.1-8b"]
rows_out = []

print("Running Section 7: Correcting the released English leaderboard...")
for m in AFFECTED:
    print(f"\nProcessing model: {m}")
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
    rows_out.append(dict(
        model=m,
        released=G.mean_r(released, H)["mean"],
        empties_dropped=G.mean_r(dropped, H)["mean"],
        recovered_and_recoded=G.mean_r(fixed, H)["mean"],
        **info
    ))

corr = pd.DataFrame(rows_out).round(3)
corr_path = f"{OUT}/corrected_leaderboard.csv"
corr.to_csv(corr_path, index=False)
corr.to_csv("corrected_leaderboard.csv", index=False)
print("\n--- Corrected Leaderboard ---")
print(corr.to_string(index=False))
print(f"\nSaved to {corr_path} and ./corrected_leaderboard.csv")
u = query.usage
print(f"\nUsage: {u.calls} calls, tokens in {u.prompt_tokens:,} out {u.completion_tokens:,}, cost ~${u.cost():.3f}")
