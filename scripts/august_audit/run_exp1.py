import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")
import sys, os
os.chdir(EXP); sys.path.insert(0, EXP)
from evaluate import evaluate_experiment, render_table
from src.experiments import get_config

cfg = get_config(1)
rows, _ = evaluate_experiment(cfg)
print("N models discovered:", len(rows))
print("N words merged (first model):", rows[0]["n"])
print()
print(render_table(cfg, rows))

# Paper Table 4 (arXiv 2605.08837v1): model -> [mean, senso, internal, social, verbal]
paper = {
 "llama-3.1-70b":[0.375,0.344,0.464,0.424,0.267],
 "qwen3-8b":[0.373,0.351,0.390,0.462,0.288],
 "gemini-2.5-flash-lite":[0.348,0.276,0.382,0.456,0.278],
 "qwen3-4b-2507":[0.314,0.335,0.405,0.318,0.200],
 "gpt-oss-20b":[0.302,0.326,0.255,0.429,0.196],
 "openai-gpt-5.4":[0.301,0.332,0.258,0.400,0.213],
 "gemini-2.5-flash":[0.296,0.291,0.310,0.364,0.218],
 "qwen3-vl-4b":[0.295,0.344,0.251,0.326,0.260],
 "gemma-3-12b-it":[0.292,0.277,0.283,0.357,0.251],
 "qwen3-vl-30b":[0.292,0.278,0.240,0.412,0.237],
 "llama-3.1-8b":[0.283,0.186,0.356,0.406,0.185],
 "claude-sonnet-4.6":[0.277,0.287,0.242,0.352,0.225],
 "qwen3-vl-8b":[0.273,0.313,0.256,0.325,0.199],
 "gemma-3-4b-it":[0.270,0.279,0.266,0.291,0.244],
 "claude-opus-4.6":[0.264,0.203,0.205,0.362,0.284],
 "claude-haiku-4.5":[0.257,0.251,0.191,0.310,0.276],
 "gemini-3.1-pro":[0.256,0.307,0.163,0.383,0.171],
 "gemini-3.1-flash-lite":[0.223,0.264,0.134,0.279,0.216],
 "gemini-3-flash":[0.216,0.251,0.182,0.294,0.137],
 "gpt-oss-120b":[0.199,0.210,0.238,0.230,0.116],
 "gemma-3-27b-it":[0.196,0.262,0.115,0.262,0.144],
}
print("\n=== DIFF vs paper Table 4 (repro - paper) ===")
print(f"{'model':24s} {'runs':>4s} {'mean':>7s} {'senso':>7s} {'intern':>7s} {'social':>7s} {'verbal':>7s}  {'maxabs':>7s}")
worst=0; nonzero=[]
for r in rows:
    p = paper.get(r["model"])
    if p is None:
        print(f"{r['model']:24s}  NOT IN PAPER TABLE"); continue
    got=[r["mean"]]+[r[c] for c in cfg.cats]
    d=[g-pp for g,pp in zip(got,p)]
    m=max(abs(x) for x in d); worst=max(worst,m)
    if m>0.0005: nonzero.append((r["model"],m))
    print(f"{r['model']:24s} {r['runs']:>4d} " + " ".join(f"{x:+7.3f}" for x in d) + f"  {m:7.3f}")
print(f"\nMax absolute deviation across all 21 models x 5 columns: {worst:.4f}")
print("Models with any deviation > 0.0005:", nonzero if nonzero else "none")
