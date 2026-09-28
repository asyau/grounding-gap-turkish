"""Cross-language extension of the Grounding Gap property-generation experiment.

Runs Harpaintner-style property generation in English and Turkish on the same
model, codes every property with the paper's own coder, and compares the two
languages against each other and against the published human norms.

Designed for Google Colab: every step is resumable, so a dead session loses at
most the call that was in flight.
"""
from __future__ import annotations

import ast
import csv
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

CATS = ["SM", "IS_E", "SC", "VA"]
CAT_LABELS = {"SM": "Sensorimotor", "IS_E": "Internal state", "SC": "Social", "VA": "Verbal association"}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

# Turkish generation prompt. A direct translation of the repo's
# data/experiment_1/generation_prompt.txt, keeping the same worked example.
TR_GENERATION_PROMPT = (
    "Bir kelime üretme görevi yapacaksınız. Verilen '{word}' kelimesi için, aklınıza "
    "olabildiğince kendiliğinden gelen dört farklı çağrışım/durum/özellik (bundan sonra "
    "'özellikler' olarak anılacak) üretin. Eş anlamlı kelimeler kullanmayın. Cevabınız "
    "yalnızca kelimeyi ve dört özelliği içermeli ve şu örnekteki gibi biçimlendirilmelidir:\n"
    "kelime: sempati\n"
    "özellikler: sarılma, arkadaşlar, neşe, güneş"
)

# Optional robustness check only. The main design keeps the coder prompt in
# English for both languages, so that generation language is the only thing
# that changes between the two arms.
TR_CODING_PROMPT = (
    "Size soyut bir kelime ve bu kelimeye ait dört özellik verilecek. Her özelliği aşağıdaki "
    "beş kategoriden birine sınıflandırmanız gerekiyor.\n\n"
    "Duyusal-motor özellik: Duyularımızla deneyimlenebilen bir özellik. Soyut kavramın anlamını "
    "betimler ya da soyut kavram bu özelliğe uygulanabilir.\n"
    "Sosyal yapı: Farklı kişilerin bir arada bulunmasını betimleyen ya da en az iki farklı kişi "
    "arasında bir etkileşimi ima eden bir özellik veya durum.\n"
    "İçsel durum ve duygu: İçsel, bilişsel süreçleri (ör. motivasyon, duygu, irade) yansıtan bir "
    "özellik veya durum.\n"
    "Çağrışım: Soyut kavramı betimlemeyen, ama onunla tematik ya da sembolik olarak ilişkili olan "
    "bir özellik veya durum.\n"
    "Diğer soyut kavram: Soyut kavramı betimleyen ya da soyut kavramın uygulanabileceği soyut bir "
    "özellik.\n\n"
    "Her özelliği ve kategorisini aşağıdaki örnekteki gibi yazın (Soyut kelime: sempati, "
    "Özellikler: sarılma, arkadaşlar, neşe, güneş).\n"
    "sarılma: Duyusal-motor özellik\n"
    "arkadaşlar: Sosyal yapı\n"
    "neşe: İçsel durum ve duygu\n"
    "güneş: Çağrışım\n\n"
    "Soyut kelime: {word}\n"
    "Özellikler: {properties}"
)

EN_LABEL_MAP = {  # identical to the repo's EXP1_LABEL_MAP
    "sensorimotor feature": "SM",
    "internal state and emotion": "IS_E",
    "social constellation": "SC",
    "association": "VA",
    "other abstract concept": "VA",
}
TR_LABEL_MAP = {
    "duyusal-motor özellik": "SM",
    "duyusal motor özellik": "SM",
    "içsel durum ve duygu": "IS_E",
    "sosyal yapı": "SC",
    "diğer soyut kavram": "VA",
    "çağrışım": "VA",
}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_PROP_RE = re.compile(r"(?:properties|özellikler|ozellikler)\s*:", re.IGNORECASE)
_ITEM_RE = re.compile(r"^\s*(?:\d+[\.\)]|[-*•])\s*(.+?)\s*$")
_ERROR_RE = re.compile(r"^\s*error\b|\b50[0-9]\b.*(unavailable|server error)|rate limit", re.IGNORECASE)


def _split(line: str) -> List[str]:
    return [p.strip().strip(".").strip() for p in line.split(",") if p.strip().strip(".").strip()]


def parse_properties(text: str, word: Optional[str] = None) -> Tuple[List[str], str]:
    """Properties from a Harpaintner-style answer, English or Turkish.

    Returns (properties, mode). mode records which rule fired, so format drift
    between languages is visible instead of silently becoming missing data:
      label      'properties: a, b, c, d' (the format the prompt asks for)
      word_colon 'anger: a, b, c, d'      (the format the repo's parser misses)
      list       numbered or bulleted lines
      bare       a single comma-separated line
      error      an API error string stored as a response
      none       nothing recoverable
    """
    text = (text or "").replace("**", "").strip()
    if not text or _ERROR_RE.search(text[:200]):
        return [], "error"
    m = _PROP_RE.search(text)
    if m:
        rest = text[m.end():]
        for line in rest.splitlines():
            if line.strip():
                if _ITEM_RE.match(line):
                    break
                return _split(line), "label"
        items = [_ITEM_RE.match(l).group(1) for l in rest.splitlines() if _ITEM_RE.match(l)]
        if items:
            return [i.strip().strip(".") for i in items], "list"
        return [], "none"
    lines = [l for l in text.splitlines() if l.strip()]
    for l in lines:
        if ":" in l:
            head, tail = l.split(":", 1)
            if tail.count(",") >= 2 and (word is None or head.strip().lower().strip("'\"") in
                                         (word.lower(), "word", "kelime")):
                return _split(tail), "word_colon"
    items = [_ITEM_RE.match(l).group(1) for l in lines if _ITEM_RE.match(l)]
    if len(items) >= 2:
        return [i.strip().strip(".") for i in items], "list"
    commas = [l for l in lines if l.count(",") >= 2 and ":" not in l]
    if commas:
        return _split(commas[-1]), "bare"
    return [], "none"


def _tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def parse_codes(text: str, label_map: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """Map each '<property>: <Category>' line to a category.

    Returns (codes, raw_labels). raw_labels keeps the coder's own wording so the
    'other abstract concept' share can be recovered later, which the original
    release does not make easy.
    """
    codes, raws = [], []
    # longest keys first so 'other abstract concept' never matches as 'association'
    keys = sorted(label_map, key=len, reverse=True)
    for line in (text or "").strip().splitlines():
        if ":" not in line:
            continue
        tail = line.rsplit(":", 1)[1].strip()
        # try both case-foldings: plain lower() for English labels, Turkish-aware
        # lower for Turkish ones (plain lower() maps 'I' to 'i', which breaks
        # 'İçsel'; Turkish lower maps 'I' to 'ı', which breaks 'Internal')
        cands = (tail.lower(), _tr_lower(tail))
        for k in keys:
            if any(k in c for c in cands):
                codes.append(label_map[k])
                raws.append(k)
                break
    return codes, raws


def frequencies(codes: List[str]) -> List[float]:
    n = len(codes)
    return [codes.count(c) / n for c in CATS] if n else [0.0] * len(CATS)


# ---------------------------------------------------------------------------
# Client with rate limiting, retries and usage accounting
# ---------------------------------------------------------------------------

class Limiter:
    def __init__(self, rpm: float):
        self.interval = 60.0 / rpm if rpm else 0.0
        self.lock = threading.Lock()
        self.next_t = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next_t)
            self.next_t = t + self.interval
        delay = t - time.monotonic()
        if delay > 0:
            time.sleep(delay)


class Usage:
    def __init__(self):
        self.lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.failures = 0

    def add(self, p, c):
        with self.lock:
            self.calls += 1
            self.prompt_tokens += p or 0
            self.completion_tokens += c or 0

    def cost(self, in_per_m=0.10, out_per_m=0.40):
        return self.prompt_tokens / 1e6 * in_per_m + self.completion_tokens / 1e6 * out_per_m


def make_gemini_query(api_key: str, rpm: float = 14, max_retries: int = 8,
                      base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"):
    """Query function with the same signature the repo's clients use."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)
    limiter, usage = Limiter(rpm), Usage()

    def query(prompt: str, model_name: str, temperature: float = 1.0, max_tokens: int = 1024,
              **_ignored) -> str:
        last = None
        for attempt in range(max_retries):
            limiter.wait()
            try:
                r = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                u = getattr(r, "usage", None)
                usage.add(getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
                return r.choices[0].message.content or ""
            except Exception as e:  # rate limits, 5xx, transient network
                last = e
                msg = str(e)
                fatal = any(s in msg for s in ("API key not valid", "PERMISSION_DENIED", "404", "not found"))
                if fatal:
                    raise
                time.sleep(min(60, 2 ** attempt + random.random()))
        usage.failures += 1
        raise RuntimeError(f"gave up after {max_retries} attempts: {last}")

    query.usage = usage
    query.client = client
    return query


# ---------------------------------------------------------------------------
# Resumable runners
# ---------------------------------------------------------------------------

def _done_keys(path: str) -> set:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return set()
    return set(pd.read_csv(path, usecols=["key"])["key"].astype(str))


def _pool(items, fn, concurrency, desc):
    try:
        from tqdm.auto import tqdm
    except Exception:  # pragma: no cover
        tqdm = lambda x, **k: x
    errors = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(fn, it) for it in items]
        for f in tqdm(as_completed(futs), total=len(futs), desc=desc):
            try:
                f.result()
            except Exception as e:
                errors += 1
                if errors == 1:
                    import traceback
                    traceback.print_exc()
                elif errors <= 5:
                    print(f"  error: {e}")
    if errors:
        print(f"  {errors} item(s) failed; re-run this cell to retry only those")
    return errors


def generate(stimuli: List[Tuple[str, str]], prompt: str, model: str, out_path: str,
             query: Callable, concurrency: int = 1, temperature: float = 1.0) -> int:
    """stimuli: list of (key, word shown to the model). key is the English norm word."""
    done = _done_keys(out_path)
    todo = [s for s in stimuli if s[0] not in done]
    if not todo:
        print(f"  complete: {os.path.basename(out_path)}")
        return 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    new = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
    lock = threading.Lock()
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["key", "stimulus", "response", "properties", "parse_mode"])
            f.flush()

        def one(item):
            key, word = item
            resp = query(prompt.replace("{word}", word), model_name=model, temperature=temperature)
            props, mode = parse_properties(resp, word)
            with lock:
                w.writerow([key, word, resp, props, mode])
                f.flush()

        return _pool(todo, one, concurrency, os.path.basename(out_path))


def code(gen_path: str, coding_prompt: str, coder: str, out_path: str, query: Callable,
         label_map: Dict[str, str], concurrency: int = 1) -> int:
    gen = pd.read_csv(gen_path)
    done = _done_keys(out_path)
    todo = [r for _, r in gen.iterrows() if str(r["key"]) not in done]
    if not todo:
        print(f"  complete: {os.path.basename(out_path)}")
        return 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    new = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
    lock = threading.Lock()
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["key", "stimulus", "properties", "codes", "raw_labels", "frequencies"])
            f.flush()

        def one(r):
            try:
                props = ast.literal_eval(str(r["properties"]))
            except Exception:
                props = []
            if not props:
                with lock:
                    w.writerow([r["key"], r["stimulus"], [], [], [], [0.0] * 4])
                    f.flush()
                return
            p = coding_prompt.replace("{word}", str(r["stimulus"])).replace("{properties}", ", ".join(props))
            resp = query(p, model_name=coder, temperature=0.0)
            codes, raws = parse_codes(resp, label_map)
            with lock:
                w.writerow([r["key"], r["stimulus"], props, codes, raws, frequencies(codes)])
                f.flush()

        return _pool(todo, one, concurrency, os.path.basename(out_path))


# ---------------------------------------------------------------------------
# Loading and aggregation
# ---------------------------------------------------------------------------

def load_coded(paths: List[str]) -> pd.DataFrame:
    """Long table: one row per (run, key) with the four frequencies."""
    rows = []
    for i, p in enumerate(sorted(paths)):
        df = pd.read_csv(p)
        for _, r in df.iterrows():
            try:
                fr = ast.literal_eval(str(r["frequencies"]))
                codes = ast.literal_eval(str(r["codes"]))
            except Exception:
                continue
            if not codes:  # no usable coding: drop rather than count as zeros
                continue
            rows.append(dict(run=i, key=str(r["key"]), **dict(zip(CATS, fr))))
    return pd.DataFrame(rows)


def profile(long: pd.DataFrame) -> pd.DataFrame:
    """Per-word mean frequency vector across runs, indexed by English key."""
    return long.groupby("key")[CATS].mean()


def load_shipped_profile(repo_exp_dir: str, model_dir: str, as_released: bool = True) -> Optional[pd.DataFrame]:
    """English profile from the paper's own released runs for the same model, if shipped.

    as_released=True reproduces evaluate.py exactly, including the all-zero rows
    left by answers its parser could not read. as_released=False drops them.
    """
    import glob
    paths = sorted(glob.glob(os.path.join(repo_exp_dir, "coded_generations", "exp1", model_dir, "*.csv")))
    if not paths:
        return None
    rows = []
    for p in paths:
        df = pd.read_csv(p)
        for _, r in df.iterrows():
            try:
                fr = ast.literal_eval(str(r["frequencies"]))
            except Exception:
                continue
            if len(fr) == 4 and (as_released or sum(fr) > 0):
                rows.append(dict(key=str(r["word"]).strip(), **dict(zip(CATS, fr))))
    return pd.DataFrame(rows).groupby("key")[CATS].mean()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def mean_r(prof: pd.DataFrame, human: pd.DataFrame, keys=None) -> Dict[str, float]:
    keys = list(prof.index.intersection(human.index) if keys is None else keys)
    out = {c: stats.pearsonr(prof.loc[keys, c], human.loc[keys, c])[0] for c in CATS}
    out["mean"] = float(np.mean([out[c] for c in CATS]))
    out["n"] = len(keys)
    return out


def paired_bootstrap(en: pd.DataFrame, tr: pd.DataFrame, human: pd.DataFrame,
                     keys: List[str], n_boot: int = 2000, seed: int = 0) -> Dict[str, Tuple]:
    """Resample words (paired across languages). CIs for Turkish minus English."""
    rng = np.random.default_rng(seed)
    keys = np.array(keys)
    E, T, H = en.loc[keys, CATS].values, tr.loc[keys, CATS].values, human.loc[keys, CATS].values

    def mr(M, Hh):
        return np.mean([np.corrcoef(M[:, j], Hh[:, j])[0, 1] for j in range(4)])

    point = {"d_mean_r": mr(T, H) - mr(E, H)}
    for j, c in enumerate(CATS):
        point[f"d_share_{c}"] = T[:, j].mean() - E[:, j].mean()
    boots = {k: [] for k in point}
    n = len(keys)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        e, t, h = E[idx], T[idx], H[idx]
        boots["d_mean_r"].append(mr(t, h) - mr(e, h))
        for j, c in enumerate(CATS):
            boots[f"d_share_{c}"].append(t[:, j].mean() - e[:, j].mean())
    return {k: (point[k], np.percentile(boots[k], 2.5), np.percentile(boots[k], 97.5)) for k in point}


def within_turkish_did(en: pd.DataFrame, tr: pd.DataFrame, stim: pd.DataFrame,
                       n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Difference-in-differences: does translation into a transparent native Turkish
    word shift the profile more than translation into an opaque loanword?

    For each concept, delta = Turkish share - English share (same model). Compare
    mean delta for native words with a visible concrete root against loanwords.
    Using the English profile of the same concept as the baseline controls for
    what the concept is, which a raw native-vs-loan comparison cannot.
    """
    rng = np.random.default_rng(seed)
    s = stim.set_index("english")
    keys = [k for k in tr.index.intersection(en.index) if k in s.index]
    d = (tr.loc[keys, CATS] - en.loc[keys, CATS])
    grp_a = [k for k in keys if s.loc[k, "origin"] == "native" and str(s.loc[k, "concrete_root"]) not in ("", "nan")]
    grp_b = [k for k in keys if str(s.loc[k, "origin"]).startswith("loan")]
    rows = []
    for c in CATS:
        a, b = d.loc[grp_a, c].values, d.loc[grp_b, c].values
        point = a.mean() - b.mean()
        bs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n_boot)]
        rows.append(dict(category=CAT_LABELS[c], native_transparent_shift=a.mean(), loanword_shift=b.mean(),
                         difference=point, ci_low=np.percentile(bs, 2.5), ci_high=np.percentile(bs, 97.5),
                         n_native=len(a), n_loan=len(b)))
    return pd.DataFrame(rows)


def cross_language_agreement(en: pd.DataFrame, tr: pd.DataFrame) -> Dict[str, float]:
    keys = en.index.intersection(tr.index)
    out = {c: stats.pearsonr(en.loc[keys, c], tr.loc[keys, c])[0] for c in CATS}
    out["mean"] = float(np.mean([out[c] for c in CATS]))
    return out


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def figure(human: pd.DataFrame, en: pd.DataFrame, tr: pd.DataFrame, keys: List[str],
           model_label: str, out_base: str, n_boot: int = 2000, seed: int = 0,
           r_en: Optional[float] = None, r_tr: Optional[float] = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(seed)
    keys = np.array(keys)
    series = [("Human norms (Harpaintner 2018)", human, "#8a8a8a"),
              (f"{model_label}, English", en, "#2f6db5"),
              (f"{model_label}, Turkish", tr, "#c8553d")]
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=200)
    width = 0.26
    x = np.arange(len(CATS))
    for i, (lab, df, col) in enumerate(series):
        M = df.loc[keys, CATS].values
        means = M.mean(0)
        bs = np.array([M[rng.integers(0, len(M), len(M))].mean(0) for _ in range(n_boot)])
        lo, hi = np.percentile(bs, 2.5, 0), np.percentile(bs, 97.5, 0)
        ax.bar(x + (i - 1) * width, means, width, color=col, label=lab,
               yerr=[means - lo, hi - means], capsize=3, error_kw=dict(lw=0.8, ecolor="#333"))
    ax.set_xticks(x, [CAT_LABELS[c] for c in CATS])
    ax.set_ylabel("Mean share of generated properties")
    ax.set_ylim(0, max(0.6, ax.get_ylim()[1]))
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    sub = f"{len(keys)} abstract concepts"
    if r_en is not None and r_tr is not None:
        sub += f"  |  Mean r with human norms: English {r_en:.3f}, Turkish {r_tr:.3f}"
    ax.set_title(f"Where the properties come from, English vs Turkish\n{sub}", fontsize=10.5)
    fig.text(0.01, 0.005, "Error bars: 95% bootstrap CI over concepts. Coder: gemini-2.5-flash-lite "
             "with the paper's English coding prompt in both arms.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out_base + ".png")
    fig.savefig(out_base + ".pdf")
    plt.close(fig)
    return out_base + ".png"


# ---------------------------------------------------------------------------
# Correcting the released leaderboard
# ---------------------------------------------------------------------------

def _run_no(path: str) -> int:
    return int(re.search(r"_run_(\d+)\.csv$", path).group(1))


def recover_shipped(repo_exp_dir: str, model_dir: str) -> pd.DataFrame:
    """Rows of the released generations that the repo's parser read as empty but
    which contain properties in another format. One row per (run, word)."""
    import glob
    rows = []
    for p in sorted(glob.glob(os.path.join(repo_exp_dir, "generations", "exp1", f"{model_dir}_run_*.csv"))):
        g = pd.read_csv(p)
        for _, r in g.iterrows():
            try:
                orig = ast.literal_eval(str(r["properties"]))
            except Exception:
                orig = []
            if orig and any(str(x).strip() for x in orig):
                continue
            props, mode = parse_properties(str(r["response"]), str(r["word"]))
            rows.append(dict(run=_run_no(p), key=str(r["word"]).strip(), stimulus=str(r["word"]).strip(),
                             response=r["response"], properties=props, parse_mode=mode))
    return pd.DataFrame(rows)


def corrected_profile(repo_exp_dir: str, model_dir: str, recovered_coded: Dict[int, str]) -> Tuple[pd.DataFrame, Dict]:
    """Released coded runs with the empty-parse rows removed and, where available,
    replaced by freshly coded recovered properties.

    recovered_coded: {run number: path to a coded CSV produced by code()}.
    """
    import glob
    rows, dropped, added = [], 0, 0
    for p in sorted(glob.glob(os.path.join(repo_exp_dir, "coded_generations", "exp1", model_dir, "*_run_*.csv"))):
        run = _run_no(p)
        gen = pd.read_csv(os.path.join(repo_exp_dir, "generations", "exp1", f"{model_dir}_run_{run}.csv"))
        empty = set()
        for _, r in gen.iterrows():
            try:
                pr = ast.literal_eval(str(r["properties"]))
            except Exception:
                pr = []
            if not (pr and any(str(x).strip() for x in pr)):
                empty.add(str(r["word"]).strip())
        for _, r in pd.read_csv(p).iterrows():
            w = str(r["word"]).strip()
            if w in empty:
                dropped += 1
                continue
            try:
                fr = ast.literal_eval(str(r["frequencies"]))
            except Exception:
                continue
            if len(fr) == 4:
                rows.append(dict(run=run, key=w, **dict(zip(CATS, fr))))
        rp = recovered_coded.get(run)
        if rp and os.path.exists(rp):
            for _, r in pd.read_csv(rp).iterrows():
                try:
                    codes = ast.literal_eval(str(r["codes"]))
                    fr = ast.literal_eval(str(r["frequencies"]))
                except Exception:
                    continue
                if codes:
                    rows.append(dict(run=run, key=str(r["key"]), **dict(zip(CATS, fr))))
                    added += 1
    df = pd.DataFrame(rows)
    return df.groupby("key")[CATS].mean(), dict(dropped=dropped, added=added)
