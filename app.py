import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.extractor import extract_article, ExtractionError
from services.scriptwriter import generate_script, ScriptError
from services.tts import synthesize, TTSError

load_dotenv()

BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "audio_output"
AUDIO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Blog to Podcast")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")


class GenerateRequest(BaseModel):
    url: str
    premium_voice: bool = False  # ask for ElevenLabs instead of the free edge-tts voice


class GenerateResponse(BaseModel):
    title: str
    script: str
    audio_url: str
    voice_engine: str  # "edge" or "elevenlabs" -- whichever actually ran
    notice: Optional[str] = None  # e.g. a fallback message worth surfacing to the user


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/config")
def config():
    """Lets the frontend know which optional features are actually configured."""
    return {"elevenlabs_available": bool(os.environ.get("ELEVENLABS_API_KEY"))}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(400, "Please provide a valid http(s) URL.")

    try:
        article = extract_article(url)
    except ExtractionError as e:
        raise HTTPException(422, str(e)) from e

    try:
        script = generate_script(article["title"], article["text"])
    except ScriptError as e:
        raise HTTPException(502, str(e)) from e

    file_id = uuid.uuid4().hex
    audio_path = AUDIO_DIR / f"{file_id}.mp3"

    engine = "elevenlabs" if (req.premium_voice and os.environ.get("ELEVENLABS_API_KEY")) else "edge"
    notice = None
    if req.premium_voice and engine == "edge":
        notice = "Premium voice requested but ELEVENLABS_API_KEY isn't set -- used the free voice instead."

    try:
        await synthesize(script, str(audio_path), engine=engine)
    except TTSError as e:
        if engine == "elevenlabs":
            # Quota exceeded, bad key, service hiccup, etc. -- don't lose the
            # script over it, just fall back to the always-available engine.
            try:
                await synthesize(script, str(audio_path), engine="edge")
                engine = "edge"
                notice = f"ElevenLabs voice failed ({e}) -- used the free voice instead."
            except TTSError as e2:
                raise HTTPException(502, str(e2)) from e2
        else:
            raise HTTPException(502, str(e)) from e

    return GenerateResponse(
        title=article["title"],
        script=script,
        audio_url=f"/audio/{file_id}.mp3",
        voice_engine=engine,
        notice=notice,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
