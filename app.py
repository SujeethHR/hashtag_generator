"""
Hashtag Generator (LLM-powered)

Analyzes pasted content with an LLM, generates relevant hashtags, and
estimates popularity for each. Supports multiple LLM providers — pick
whichever you have access to:

  1. Ollama (local, no API key)        -- default if running
  2. Groq (free tier)                  -- set GROQ_API_KEY
  3. OpenAI                            -- set OPENAI_API_KEY
  4. Anthropic                         -- set ANTHROPIC_API_KEY

If none are configured, the app falls back to a built-in heuristic
generator so it still works out of the box.

Run:
    pip install -r requirements.txt
    python app.py

Open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify, Response
import json
import os
import re
import urllib.request
import urllib.error
import ssl
import certifi
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
ABACUS_API_KEY = os.environ.get("ABACUS_API_KEY")
ABACUS_MODEL = os.environ.get("ABACUS_MODEL", "route-llm")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# ----------------------------------------------------------------------
# Prompt
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """You are a social-media hashtag strategist. You analyze
content and produce highly relevant hashtags optimized for engagement on
Instagram, X/Twitter, TikTok, and LinkedIn.

For each hashtag you must estimate a popularity score from 0-100 based
on how widely it is used on social platforms:

  90-100  Mega       (e.g. #love, #travel, #food — millions of uses)
  70-89   Trending   (widely used in big communities)
  55-69   Popular    (well established niches)
  40-54   Niche      (smaller but engaged audiences)
   0-39   Specialized (very specific, low volume)

Also include a short rationale (max 8 words) for each hashtag.

ALWAYS respond with VALID JSON ONLY, no preamble or markdown fences.
Schema:
{
  "topics": ["short topic 1", "short topic 2", ...],
  "hashtags": [
    {"tag": "#example", "score": 85, "rationale": "matches main subject"},
    ...
  ]
}
"""

PLATFORM_NOTES = {
    "instagram": "Platform: Instagram. Mix mega-popular reach tags with niche engagement tags. Instagram allows up to 30 hashtags.",
    "twitter":   "Platform: X/Twitter. Use only 2-3 punchy, widely recognized hashtags. Brevity is critical.",
    "tiktok":    "Platform: TikTok. Favor short, trending, energetic, visual hashtags. Lean into viral TikTok trends.",
    "linkedin":  "Platform: LinkedIn. Use professional, industry-specific, B2B-focused hashtags. Avoid slang.",
    "all":       "Target all major platforms: Instagram, X/Twitter, TikTok, LinkedIn. Provide a balanced mix.",
}


def build_user_prompt(content: str, n: int, platform: str = "all",
                      exclusions=None, seeds=None) -> str:
    note = PLATFORM_NOTES.get(platform, PLATFORM_NOTES["all"])
    lines = [
        f"Generate exactly {n} hashtags for the following content. {note}",
        "Mix mega-popular tags for reach with niche tags for relevance.",
    ]
    if exclusions:
        lines.append(f"NEVER use these hashtags: {', '.join(str(e) for e in exclusions)}.")
    if seeds:
        lines.append(f"You MUST include these hashtags verbatim: {', '.join(str(s) for s in seeds)}.")
    lines.append(f"Return JSON only.\n\n--- CONTENT ---\n{content.strip()}\n--- END ---")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Provider detection
# ----------------------------------------------------------------------
def ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5, context=_SSL_CTX) as r:
            return r.status == 200
    except Exception:
        return False


def list_providers() -> list:
    """Return providers in priority order, marking which are ready."""
    providers = [
        {"id": "abacus",    "label": f"Abacus ({ABACUS_MODEL})",       "ready": bool(ABACUS_API_KEY)},
        {"id": "ollama",    "label": f"Ollama ({OLLAMA_MODEL})",        "ready": ollama_available()},
        {"id": "groq",      "label": f"Groq ({GROQ_MODEL})",            "ready": bool(GROQ_API_KEY)},
        {"id": "openai",    "label": f"OpenAI ({OPENAI_MODEL})",        "ready": bool(OPENAI_API_KEY)},
        {"id": "anthropic", "label": f"Anthropic ({ANTHROPIC_MODEL})",  "ready": bool(ANTHROPIC_API_KEY)},
        {"id": "heuristic", "label": "Built-in heuristic (no LLM)",    "ready": True},
    ]
    return providers


def default_provider() -> str:
    for p in list_providers():
        if p["ready"]:
            return p["id"]
    return "heuristic"


# ----------------------------------------------------------------------
# HTTP helper
# ----------------------------------------------------------------------
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def http_post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        return json.loads(r.read().decode("utf-8"))


# ----------------------------------------------------------------------
# Provider implementations
# ----------------------------------------------------------------------
def call_ollama(content: str, n: int, platform="all", exclusions=None, seeds=None) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(content, n, platform, exclusions, seeds)},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.4},
    }
    res = http_post_json(f"{OLLAMA_URL}/api/chat", payload, {})
    return res.get("message", {}).get("content", "")


def call_abacus(content: str, n: int, platform="all", exclusions=None, seeds=None) -> str:
    payload = {
        "model": ABACUS_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(content, n, platform, exclusions, seeds)},
        ],
        "temperature": 0.4,
    }
    res = http_post_json(
        "https://routellm.abacus.ai/v1/chat/completions",
        payload,
        {
            "Authorization": f"Bearer {ABACUS_API_KEY}",
            "User-Agent": "Mozilla/5.0",
        },
    )
    return res["choices"][0]["message"]["content"]


def call_groq(content: str, n: int, platform="all", exclusions=None, seeds=None) -> str:
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(content, n, platform, exclusions, seeds)},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    res = http_post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        payload,
        {"Authorization": f"Bearer {GROQ_API_KEY}"},
    )
    return res["choices"][0]["message"]["content"]


def call_openai(content: str, n: int, platform="all", exclusions=None, seeds=None) -> str:
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(content, n, platform, exclusions, seeds)},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    res = http_post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        {"Authorization": f"Bearer {OPENAI_API_KEY}"},
    )
    return res["choices"][0]["message"]["content"]


def call_anthropic(content: str, n: int, platform="all", exclusions=None, seeds=None) -> str:
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "temperature": 0.4,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_user_prompt(content, n, platform, exclusions, seeds)}],
    }
    res = http_post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
    )
    return res["content"][0]["text"]


# ----------------------------------------------------------------------
# JSON cleanup (LLMs sometimes wrap in code fences)
# ----------------------------------------------------------------------
def parse_llm_json(raw: str) -> dict:
    if not raw:
        return {}
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    # Sometimes models wrap JSON in extra text — find the first {...}
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


# ----------------------------------------------------------------------
# Heuristic fallback (used if no LLM provider is available)
# ----------------------------------------------------------------------
STOPWORDS = {
    "a","an","the","and","or","but","if","while","with","to","of","in","on",
    "at","by","for","from","as","is","are","was","were","be","been","being",
    "have","has","had","do","does","did","will","would","shall","should","can",
    "could","may","might","must","i","me","my","we","us","our","you","your",
    "he","him","his","she","her","it","its","they","them","their","this","that",
    "these","those","what","which","who","whom","whose","when","where","why",
    "how","all","any","both","each","few","more","most","other","some","such",
    "no","not","only","own","same","so","than","too","very","just","also",
    "really","get","got","go","like","one","two","way","things","thing",
    "people","time","day","good","great","well","even","still","back","out",
    "up","down","into","about","after","before","over","under","again","then",
    "here","there","much","many","every",
}


def heuristic_generate(content: str, n: int, seeds=None) -> dict:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", content.lower())
    keywords = Counter(
        w for w in tokens if len(w) > 2 and w not in STOPWORDS
    )
    hashtags = []
    seen = set()
    for s in (seeds or []):
        tag = normalize_tag(str(s))
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            hashtags.append({"tag": tag, "score": 75, "rationale": "user-specified seed"})
    for w, _ in keywords.most_common(n):
        if len(hashtags) >= n:
            break
        tag = "#" + w
        if tag.lower() in seen:
            continue
        seen.add(tag.lower())
        score = max(20, min(90, 90 - (len(w) - 4) * 4))
        hashtags.append({"tag": tag, "score": score, "rationale": "frequent keyword in content"})
    return {"topics": [w for w, _ in keywords.most_common(3)], "hashtags": hashtags}


# ----------------------------------------------------------------------
# Pipeline
# ----------------------------------------------------------------------
def label_for(score: int) -> str:
    if score >= 90: return "Mega"
    if score >= 70: return "Trending"
    if score >= 55: return "Popular"
    if score >= 40: return "Niche"
    return "Low"


def normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        return ""
    if not tag.startswith("#"):
        tag = "#" + tag
    # Strip whitespace and disallowed chars (keep letters, numbers, underscore)
    body = re.sub(r"[^A-Za-z0-9_]", "", tag[1:])
    return ("#" + body) if body else ""


def normalize_result(parsed: dict) -> dict:
    hashtags = []
    seen = set()
    for h in parsed.get("hashtags", []) or []:
        if not isinstance(h, dict):
            continue
        tag = normalize_tag(str(h.get("tag", "")))
        if not tag or tag.lower() in seen:
            continue
        seen.add(tag.lower())
        try:
            score = int(h.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        rationale = str(h.get("rationale", "")).strip()
        hashtags.append({
            "tag": tag,
            "score": score,
            "label": label_for(score),
            "rationale": rationale,
        })
    hashtags.sort(key=lambda x: -x["score"])
    topics = [str(t).strip() for t in (parsed.get("topics") or []) if str(t).strip()]
    return {"hashtags": hashtags, "topics": topics}


def run_provider(provider_id: str, content: str, n: int,
                 platform: str = "all", exclusions=None, seeds=None) -> dict:
    kwargs = dict(platform=platform, exclusions=exclusions, seeds=seeds)
    if provider_id == "abacus":
        raw = call_abacus(content, n, **kwargs)
    elif provider_id == "ollama":
        raw = call_ollama(content, n, **kwargs)
    elif provider_id == "groq":
        raw = call_groq(content, n, **kwargs)
    elif provider_id == "openai":
        raw = call_openai(content, n, **kwargs)
    elif provider_id == "anthropic":
        raw = call_anthropic(content, n, **kwargs)
    elif provider_id == "heuristic":
        return heuristic_generate(content, n, seeds=seeds)
    else:
        raise ValueError(f"Unknown provider: {provider_id}")
    return parse_llm_json(raw) or {}


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        providers=list_providers(),
        default_provider=default_provider(),
    )


@app.route("/providers")
def providers():
    return jsonify({
        "providers": list_providers(),
        "default": default_provider(),
    })


@app.route("/generate", methods=["POST"])
def generate():
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    try:
        n = max(5, min(30, int(body.get("max_tags", 20))))
    except (TypeError, ValueError):
        n = 20
    requested = body.get("provider") or default_provider()
    platform = (body.get("platform") or "all").lower()
    seeds_raw = (body.get("seeds") or "").strip()
    excl_raw  = (body.get("exclusions") or "").strip()
    seeds      = [t for t in re.findall(r"#?\w+", seeds_raw) if t] if seeds_raw else None
    exclusions = [t for t in re.findall(r"#?\w+", excl_raw) if t]  if excl_raw  else None

    if not content:
        return jsonify({"error": "Please paste some content first."}), 400

    used = requested
    error = None
    parsed = {}
    try:
        parsed = run_provider(requested, content, n, platform=platform,
                              exclusions=exclusions, seeds=seeds)
        if not parsed.get("hashtags"):
            raise RuntimeError("LLM returned no hashtags")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        error = f"{requested} HTTP {e.code}: {err_body[:200]}"
    except Exception as e:
        error = f"{requested} error: {e}"

    if error or not parsed.get("hashtags"):
        parsed = heuristic_generate(content, n, seeds=seeds)
        used = "heuristic"

    result = normalize_result(parsed)
    avg = (
        round(sum(h["score"] for h in result["hashtags"]) / len(result["hashtags"]), 1)
        if result["hashtags"] else 0
    )
    return jsonify({
        "hashtags": result["hashtags"],
        "topics": result["topics"],
        "stats": {
            "word_count": len(re.findall(r"\S+", content)),
            "hashtag_count": len(result["hashtags"]),
            "avg_popularity": avg,
            "provider_used": used,
            "provider_requested": requested,
            "fallback_reason": error,
        },
    })


@app.route("/export/<fmt>", methods=["POST"])
def export(fmt):
    """Export the supplied hashtag list as txt or csv."""
    body = request.get_json(silent=True) or {}
    hashtags = body.get("hashtags") or []
    if fmt == "txt":
        text = " ".join(h.get("tag", "") for h in hashtags) + "\n"
        return Response(
            text,
            mimetype="text/plain",
            headers={"Content-Disposition": "attachment; filename=hashtags.txt"},
        )
    if fmt == "csv":
        lines = ["hashtag,score,tier,rationale"]
        for h in hashtags:
            tag = (h.get("tag") or "").replace('"', '""')
            rat = (h.get("rationale") or "").replace('"', '""')
            lines.append(f'"{tag}",{h.get("score", 0)},"{h.get("label", "")}","{rat}"')
        csv_data = "\n".join(lines) + "\n"
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=hashtags.csv"},
        )
    return jsonify({"error": "Unsupported format"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
