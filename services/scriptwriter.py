"""Turns raw article text into a spoken, solo-narrator podcast script using Gemini."""

import os
import google.generativeai as genai

SYSTEM_PROMPT = """You are a podcast scriptwriter. You turn written articles into a \
short, solo-narrator podcast script that sounds natural when read aloud.

Rules:
- Write for the EAR, not the eye: short sentences, natural spoken rhythm, no bullet \
points, no markdown, no headers.
- Open with a one-sentence hook that tells the listener why this matters, not "In this \
article...".
- Cover the actual substance of the article faithfully: the real claims, numbers, and \
examples. Do not invent facts, statistics, or quotes that aren't in the source text.
- Keep it tight: aim for roughly 400-600 words (about 3-4 minutes spoken).
- Close with a one-sentence takeaway, not a generic "thanks for listening".
- Output ONLY the script text the narrator will read aloud. No stage directions, no \
labels like "[INTRO]", no title, no notes to yourself.
"""


class ScriptError(Exception):
    pass


def generate_script(title: str, article_text: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ScriptError("GEMINI_API_KEY is not set. Add it to your .env file.")

    genai.configure(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)

    # Trim very long articles so we stay well within free-tier context/rate limits.
    trimmed = article_text[:20000]

    prompt = f'Article title: "{title}"\n\nArticle text:\n{trimmed}'

    try:
        response = model.generate_content(prompt)
    except Exception as e:  # noqa: BLE001 - surface a clean error to the API layer
        raise ScriptError(f"Gemini request failed: {e}") from e

    script = (response.text or "").strip()
    if not script:
        raise ScriptError("Gemini returned an empty script.")
    return script
