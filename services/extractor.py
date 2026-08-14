"""Pulls clean article text (title + body) out of a blog URL.

Tries trafilatura first (fast, free, fully local). If that comes up empty
(common on JS-rendered pages, some paywalls, or sites with basic bot
protection), falls back to Firecrawl -- but only if FIRECRAWL_API_KEY is set.
"""

import os
import trafilatura
import requests

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"


class ExtractionError(Exception):
    pass


def _extract_with_trafilatura(url: str):
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None

    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not text or len(text.strip()) < 200:
        return None

    metadata = trafilatura.extract_metadata(downloaded)
    title = (metadata.title if metadata and metadata.title else None) or url
    return {"title": title.strip(), "text": text.strip(), "url": url}


def _extract_with_firecrawl(url: str):
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            FIRECRAWL_SCRAPE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"url": url, "formats": ["markdown"]},
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return None

    data = payload.get("data") if isinstance(payload, dict) else None
    if not data:
        return None

    text = data.get("markdown") or data.get("content")
    if not text or len(text.strip()) < 200:
        return None

    metadata = data.get("metadata", {}) or {}
    title = metadata.get("title") or url
    return {"title": title.strip(), "text": text.strip(), "url": url}


def extract_article(url: str) -> dict:
    article = _extract_with_trafilatura(url)
    if article:
        return article

    article = _extract_with_firecrawl(url)
    if article:
        return article

    hint = (
        "Couldn't extract article text from that page, even with the Firecrawl "
        "fallback. It may be paywalled, blocked, or not a standard article layout."
        if os.environ.get("FIRECRAWL_API_KEY")
        else "Couldn't extract article text from that page. It may be JS-rendered "
        "or paywalled -- add FIRECRAWL_API_KEY to .env to enable a fallback that "
        "handles those."
    )
    raise ExtractionError(hint)
