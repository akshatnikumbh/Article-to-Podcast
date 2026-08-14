# Article → Podcast

Paste a blog URL, get back a short spoken-word mp3.

| Step | Tool | Why |
|---|---|---|
| Extract article text | [trafilatura](https://github.com/adbar/trafilatura), falls back to [Firecrawl](https://firecrawl.dev) | trafilatura is free/local but misses JS-rendered or lightly-protected pages; Firecrawl catches those (1,000 free pages/month) |
| Understand + write script | [Gemini API](https://ai.google.dev) | Free tier, generous rate limits |
| Voice | [edge-tts](https://github.com/rany2/edge-tts) (default, free) or [ElevenLabs](https://elevenlabs.io) (optional, toggle per article) | edge-tts is unlimited and free; ElevenLabs sounds noticeably more natural but its free tier is ~10 min of audio/month |
| App | FastAPI + plain HTML/JS | No frontend build step |

## Setup

```bash
cd blog-to-podcast
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste in your GEMINI_API_KEY (required)
# FIRECRAWL_API_KEY and ELEVENLABS_API_KEY are both optional -- see below

uvicorn app:app --reload
```

Open **http://localhost:8000**, paste an article URL, hit **Tap**.

## How it works

1. `services/extractor.py` tries trafilatura first (fast, free, fully local). If that comes back empty -- common on JS-rendered pages or sites with light bot protection -- and `FIRECRAWL_API_KEY` is set, it falls back to Firecrawl automatically. You don't have to do anything for this to kick in; it's silent unless both fail.
2. `services/scriptwriter.py` sends the article text to Gemini with a system prompt that rewrites it as a ~400–600 word solo-narrator script -- written for the ear (short sentences, a hook, no bullet points), staying faithful to the article's actual facts.
3. `services/tts.py` voices that script. Default is edge-tts (free, unlimited). If you check "Use premium voice" in the UI and `ELEVENLABS_API_KEY` is set, it uses ElevenLabs instead; if that request fails for any reason (quota, bad key, outage) it automatically falls back to edge-tts rather than losing the episode, and tells you that happened.
4. The mp3 is served back to the browser and playable/downloadable immediately.

## Optional integrations

**Firecrawl** (better extraction): get a free key at [firecrawl.dev](https://firecrawl.dev) (1,000 pages/month, no card required), paste it into `FIRECRAWL_API_KEY` in `.env`. Nothing else to configure -- it only activates when trafilatura fails.

**ElevenLabs** (premium voice): get a free key at [elevenlabs.io](https://elevenlabs.io) (10,000 characters/month ≈ 10 minutes of audio, non-commercial use only on the free tier), paste it into `ELEVENLABS_API_KEY` in `.env`. Once set, a "Use premium voice" checkbox appears in the UI -- it's off by default so you don't burn through the free quota on every article. You can also set `ELEVENLABS_VOICE_ID` to pick a specific voice from your ElevenLabs voice library; it defaults to a standard preset voice ("Rachel").

## Things worth knowing

- **Paywalled or heavily JS-rendered sites** may still fail even with the Firecrawl fallback -- some sites actively block scrapers regardless of tooling.
- **Model name drift**: Google renames/retires Gemini model IDs periodically. `GEMINI_MODEL` defaults to `gemini-flash-latest`, an alias that always points at their current recommended flash model, so this shouldn't need updating. If you want to pin an exact version instead, list what's live on your key:
  ```bash
  python3 -c "import google.generativeai as genai, os; from dotenv import load_dotenv; load_dotenv(); genai.configure(api_key=os.environ['GEMINI_API_KEY']); [print(m.name) for m in genai.list_models()]"
  ```
- **Voice options**: `edge-tts --list-voices` shows every voice/accent/language available for the free engine. Set `TTS_VOICE` in `.env`.
- **Rate limits**: Gemini and edge-tts's free tiers are generous for personal use (dozens of articles/day). ElevenLabs' free tier is the tight one (~10 min/month) -- it's meant as an occasional upgrade, not your daily driver.

## Natural next steps

- **True "on tap"**: turn the URL box into a bookmarklet or iOS Shortcut that POSTs the current tab's URL straight to `/generate` -- skips the copy-paste.
- **Queue + history**: save past conversions (title, script, mp3 path) to a small SQLite file so you get a running feed/library instead of one-at-a-time.
- **Batch from RSS**: point it at a feed URL and auto-generate episodes for new posts.
- **Audio/video input via Whisper**: if you want to feed in podcasts, YouTube videos, or voice memos (not just blog text), a local Whisper transcription step could turn those into text first, then reuse the exact same script + voice pipeline. Not built yet -- worth adding if your inputs expand past articles.
- **Longer-form / two-host mode**: swap the system prompt in `scriptwriter.py` for a two-speaker version and use two different voices, stitching the audio with `pydub`.
