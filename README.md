# Hashtag Generator

A local web app that analyzes your text and generates relevant, platform-tuned hashtags with popularity scores. Powered by an LLM of your choice.

---

## What it does

Paste any text — a caption, blog post, tweet, or product description — and the app returns a ranked list of hashtags. Each hashtag includes a popularity tier (Mega, Trending, Popular, Niche, Low), a short rationale, and an animated score bar. You can filter, select, favorite, copy, and export results in multiple formats.

---

## Setup

**1. Install dependencies**

```bash
pip3 install -r requirements.txt
```

**2. Add your API key**

Copy `.env.example` to `.env` and add your key(s):

```bash
cp .env.example .env
```

```
ABACUS_API_KEY=your_key_here
# or any of the other providers below
```

**3. Run**

```bash
python3 app.py
```

Open http://127.0.0.1:5000 in your browser.

---

## How to use

1. Select a **platform tab** (All, Instagram, X/Twitter, TikTok, LinkedIn) — this tunes the prompt and auto-sets a sensible hashtag count.
2. Paste your content into the text box. Live character and word counts update as you type. Your draft is auto-saved across reloads.
3. Optionally expand **Advanced options** to add seed hashtags (must include) or an exclusion list (never include).
4. Choose your **LLM provider** from the dropdown. A green dot means it is ready; red means not configured.
5. Adjust the **hashtag count** slider (5–30) if needed.
6. Click **Generate** or press `⌘ Enter` (Mac) / `Ctrl Enter` (Windows/Linux).
7. Browse results. Use the **tier filter pills** to show only Mega, Trending, etc. tags.
8. Click any hashtag text to copy it instantly. Check multiple hashtags and use **Copy Selected** for a subset. Use **Copy All** for everything visible.
9. Star (☆) hashtags to save them to **Favorites**, accessible from the History & Favs drawer.

---

## Features

### Platform presets
| Tab | Default count | Prompt tuning |
|-----|--------------|---------------|
| All Platforms | 20 | Balanced mix across all platforms |
| Instagram | 25 | Reach + niche mix, respects the 30-tag limit |
| X / Twitter | 3 | 2–3 punchy, widely recognized tags |
| TikTok | 20 | Short, trending, energetic, viral tags |
| LinkedIn | 10 | Professional, B2B, industry-specific tags |

### Advanced options
- **Seed hashtags** — space-separated tags the LLM must include verbatim (e.g. `#branding #design`)
- **Exclusion list** — tags the LLM must never return (e.g. `#spam #competitor`)

### Results panel
- **Tier distribution chips** — quick summary (e.g. "5 Mega · 8 Trending · 4 Niche") above the list
- **Detected themes** — topic chips extracted from your content
- **Filter pills** — show All, Mega, Trending, Popular, Niche, or Low tags only
- **Tier-colored score bars** — each bar is colored by its tier and animates in on render
- **Tier badge tooltips** — hover a badge (e.g. "Trending") to see the score range and definition
- **Click-to-copy** — click any `#hashtag` text to copy it to the clipboard
- **Checkboxes + Copy Selected** — check individual tags across tiers, then copy just those
- **Retry button** — if the LLM fails and the heuristic fallback is used, a Retry button appears

### History & Favorites
- **History** — the last 15 generations are saved in `localStorage`. Click any entry to reload its results. Includes platform, top tags, and a snippet of the original content.
- **Favorites** — star hashtags from any result to save them permanently. Open the drawer to copy individual tags or copy all favorites at once.

### SEO / AEO
- On-page **"How it works"** section and an **FAQ** with matching `WebApplication`, `HowTo`, and `FAQPage` JSON-LD structured data.
- Open Graph and Twitter Card meta tags for link previews.
- `/robots.txt`, `/sitemap.xml`, and `/llms.txt` (a machine-readable summary for AI answer engines).
- Set `SITE_URL` in `.env` (e.g. `https://yourdomain.com`) to point canonical/OG tags and the sitemap at your real domain in production. Defaults to `http://localhost:5000`.

---

## Export options

| Format | Contents |
|--------|----------|
| Copy All | All visible hashtags as a space-separated string |
| Copy Selected | Only the checked hashtags |
| `.txt` | Plain text, one line of hashtags |
| `.csv` | Columns: hashtag, score, tier, rationale |
| `.json` | Full structured data: hashtags array + topics array |

---

## Supported LLM providers

The app tries providers in this order and uses the first one that is configured:

| Provider | How to enable |
|----------|---------------|
| Abacus (default) | Set `ABACUS_API_KEY` in `.env` |
| Ollama | Run Ollama locally (no key needed) |
| Groq | Set `GROQ_API_KEY` in `.env` |
| OpenAI | Set `OPENAI_API_KEY` in `.env` |
| Anthropic | Set `ANTHROPIC_API_KEY` in `.env` |
| Built-in heuristic | Always available — no LLM required |

The provider dropdown shows a green dot when a provider is ready and a red dot when it is not configured.

---

## Popularity tiers

| Tier | Score | Meaning |
|------|-------|---------|
| Mega | 90–100 | Millions of uses (e.g. #love, #travel) |
| Trending | 70–89 | Widely used in large communities |
| Popular | 55–69 | Well-established niches |
| Niche | 40–54 | Smaller but engaged audiences |
| Low | 0–39 | Very specific, low volume |

Scores are LLM estimates — useful as a relative guide, not exact platform metrics.

---

## Keyboard shortcut

| Shortcut | Action |
|----------|--------|
| `⌘ Enter` / `Ctrl Enter` | Generate hashtags |

---

## Requirements

- Python 3.13 or higher
- At least one configured provider key, or use the built-in heuristic (no key needed)
