"""Apply patches/grounding-gap-parser-fix.patch to a scratch copy of upstream and
check that it changes exactly what it should.

Unpatched evaluate.py must reproduce Table 4 (Gemini 2.5 Flash-Lite 0.348).
Patched evaluate.py must give the corrected value (0.394) and leave unaffected
models unchanged (Claude Opus 4.6 stays 0.264).
"""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPSTREAM = os.environ.get("GG_UPSTREAM", os.path.join(ROOT, "upstream", "grounding-gap"))
if not os.path.isdir(UPSTREAM):
    sys.exit("run scripts/setup_upstream.sh first")


def leaderboard(repo):
    code = ("import sys, json; sys.path.insert(0, '.');"
            "from evaluate import evaluate_experiment; from src.experiments import get_config;"
            "rows, _ = evaluate_experiment(get_config(1));"
            "print(json.dumps({r['model']: round(r['mean'], 3) for r in rows}))")
    out = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(repo, "property_generation_experiments"),
                         capture_output=True, text=True, check=True).stdout
    import json
    return json.loads(out.strip().splitlines()[-1])


with tempfile.TemporaryDirectory() as tmp:
    dst = os.path.join(tmp, "grounding-gap")
    shutil.copytree(UPSTREAM, dst)
    before = leaderboard(dst)
    subprocess.run(["git", "apply", os.path.join(ROOT, "patches", "grounding-gap-parser-fix.patch")], cwd=dst, check=True)
    after = leaderboard(dst)

expect = {"gemini-2.5-flash-lite": (0.348, 0.394), "llama-3.1-8b": (0.283, 0.339),
          "gpt-oss-120b": (0.199, 0.239), "claude-opus-4.6": (0.264, 0.264)}
ok = True
print(f"{'model':24s} {'before':>7s} {'after':>7s}   expected")
for m, (b, a) in expect.items():
    good = abs(before[m] - b) < 0.0015 and abs(after[m] - a) < 0.0015
    ok &= good
    print(f"{m:24s} {before[m]:7.3f} {after[m]:7.3f}   {b:.3f} -> {a:.3f}  {'ok' if good else 'MISMATCH'}")
print("\nPATCH CHECK", "PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
