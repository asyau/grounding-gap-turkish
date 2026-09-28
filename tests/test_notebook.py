"""Execute the notebook's own cells in order with a mock model.

Colab-only pieces (Drive, secrets, git clone, file download) are stubbed; every
other line of every cell runs exactly as written.
"""
import os as _os, sys as _sys
ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
UPSTREAM = _os.environ.get("GG_UPSTREAM", _os.path.join(ROOT, "upstream", "grounding-gap"))
EXP = _os.path.join(UPSTREAM, "property_generation_experiments")
if not _os.path.isdir(EXP):
    _sys.exit(f"upstream repo not found at {UPSTREAM}; run scripts/setup_upstream.sh or set GG_UPSTREAM")

import json, os, re, shutil, sys, types, random

NB = os.path.join(ROOT, "notebooks", "grounding_gap_turkish.ipynb")
SANDBOX = os.path.join(ROOT, "tests", "_out", "notebook")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX)
shutil.copytree(UPSTREAM, f"{SANDBOX}/grounding-gap")   # the notebook edits the repo; use a copy

cells = [c for c in json.load(open(NB))["cells"] if c["cell_type"] == "code"]
src = ["".join(c["source"]) for c in cells]

# mock query built from test_mock.py's mock (replays shipped English runs)
mock_ns = {"__file__": os.path.join(ROOT, "tests", "test_mock.py")}
exec(open(os.path.join(ROOT, "tests", "test_mock.py")).read().split("random.seed(0)")[0]
     .replace('OUT = os.path.join(ROOT, "tests", "_out", "mock")', 'OUT = os.path.join(ROOT, "tests", "_out", "unused")'), mock_ns)
mock_query = mock_ns["mock_query"]

class U:  # usage stub
    calls = prompt_tokens = completion_tokens = failures = 0
    def cost(self): return 0.0
mock_query.usage = U()
mock_query.client = types.SimpleNamespace(models=types.SimpleNamespace(
    list=lambda: [types.SimpleNamespace(id="gemini-2.5-flash-lite"), types.SimpleNamespace(id="gemini-3.1-flash-lite")]))

ns = {"__name__": "__main__"}
CONTENT = f"{SANDBOX}/content"   # stands in for Colab's /content
os.makedirs(CONTENT, exist_ok=True)
src = [s.replace("/content", CONTENT) for s in src]
for i, s in enumerate(src):
    if s.startswith("%%writefile"):
        target = s.splitlines()[0].split()[1]
        body = s.split("\n", 1)[1]
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write(body)
        print(f"[cell {i}] wrote {target}")
        continue
    if "# ---- setup ----" in s:
        ns.update(REPO=f"{SANDBOX}/grounding-gap/property_generation_experiments",
                  OUT=f"{SANDBOX}/out", API_KEY="dummy")
        os.makedirs(ns["OUT"], exist_ok=True)
        exec("import os, sys, subprocess", ns)
        print(f"[cell {i}] setup stubbed")
        continue
    if "# ---- configuration ----" in s:
        s = s.replace("SUBSET_N   = 30", "SUBSET_N   = None").replace("USE_DRIVE  = True", "USE_DRIVE  = False")
    if "make_gemini_query" in s:
        s = s.replace("query = G.make_gemini_query(API_KEY, rpm=RPM)", "query = MOCK")
        ns["MOCK"] = mock_query
    print(f"[cell {i}] running ({len(s.splitlines())} lines)")
    try:
        exec(compile(s, f"cell_{i}", "exec"), ns)
    except SystemExit:
        pass
    # show the key outputs of result cells
    if "did = G.within_turkish_did" in s:
        print(ns["did"].round(3).to_string(index=False))
    if "corr = pd.DataFrame(rows_out)" in s:
        print(ns["corr"].to_string(index=False))
print("\nALL CELLS RAN")
