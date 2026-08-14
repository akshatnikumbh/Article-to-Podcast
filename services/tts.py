"""Converts a script to an mp3.

Two engines:
- "edge"       : edge-tts, free, no API key, good default quality.
- "elevenlabs" : ElevenLabs API, much more natural/expressive voices, but
                 free tier is capped at ~10,000 characters/month. Requires
                 ELEVENLABS_API_KEY.
"""

import os
import edge_tts
import requests

ELEVEN_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
# Default voice: "Rachel", one of ElevenLabs' standard premade voices.
DEFAULT_ELEVEN_VOICE = "21m00Tcm4TlvDq8ikWAM"


class TTSError(Exception):
    pass


async def _synthesize_edge(script: str, output_path: str) -> None:
    voice = os.environ.get("TTS_VOICE", "en-US-GuyNeural")
    try:
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(output_path)
    except Exception as e:  # noqa: BLE001
        raise TTSError(f"edge-tts failed: {e}") from e


def _synthesize_elevenlabs(script: str, output_path: str) -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise TTSError("ELEVENLABS_API_KEY is not set.")

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_ELEVEN_VOICE)

    try:
        resp = requests.post(
            ELEVEN_TTS_URL.format(voice_id=voice_id),
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": script,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
            },
            timeout=120,
        )
    except requests.RequestException as e:
        raise TTSError(f"ElevenLabs request failed: {e}") from e

    if resp.status_code == 401:
        raise TTSError("ElevenLabs rejected the API key (401).")
    if resp.status_code == 429:
        raise TTSError("ElevenLabs quota exceeded for this month (429).")
    if not resp.ok:
        raise TTSError(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")

    with open(output_path, "wb") as f:
        f.write(resp.content)


async def synthesize(script: str, output_path: str, engine: str = "edge") -> None:
    """engine: "edge" (default, free) or "elevenlabs" (premium, quota-limited)."""
    if engine == "elevenlabs":
        _synthesize_elevenlabs(script, output_path)
    else:
        await _synthesize_edge(script, output_path)
