from __future__ import annotations

from typing import List, Optional
import os
import re
from collections import Counter

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# This router focuses on title recommendations from free-form note content.
router = APIRouter(prefix="", tags=["Title Recommendation"])

# Perplexity settings (align with existing chatbot integration)
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")
DEFAULT_MAX_TOKENS = int(os.getenv("PERPLEXITY_MAX_TOKENS", "120"))
DEFAULT_TEMPERATURE = float(os.getenv("PERPLEXITY_TEMPERATURE", "0.2"))


class RecommendTitleRequest(BaseModel):
    """Input containing the note content from which to suggest titles."""
    content: str = Field(..., description="User-authored note content to analyze for title suggestions")


class RecommendTitleResponse(BaseModel):
    """Output containing a list of suggested titles."""
    suggestions: List[str] = Field(..., description="List of suggested titles ordered by relevance")


def _get_api_key() -> Optional[str]:
    """Get Perplexity API key if configured; return None if missing."""
    return os.getenv("PERPLEXITY_API_KEY")


def _heuristic_titles_from_content(content: str, max_titles: int = 5) -> List[str]:
    """
    Simple heuristic to generate candidate titles:
    - Use first non-empty line if present
    - Extract frequent nouns/keywords (basic), build concise phrases
    - Fallbacks: trimmed summary and generic titles
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", content).strip()

    suggestions: List[str] = []

    # 1) First significant line
    first_line = None
    for line in content.splitlines():
        line = line.strip(" #\t")
        if len(line) >= 8:  # skip very short lines
            first_line = line[:120].rstrip(". ")
            break
    if first_line:
        suggestions.append(first_line)

    # 2) Keyword frequency approach
    # Tokenize basic words, filter stopwords, and rank by frequency
    words = re.findall(r"[A-Za-z][A-Za-z\-']{1,}", content.lower())
    stopwords = {
        "the", "and", "or", "to", "of", "in", "a", "an", "for", "on", "with", "is", "it", "this", "that",
        "by", "from", "as", "be", "are", "at", "was", "were", "but", "if", "then", "into", "out", "so",
        "about", "can", "you", "your", "we", "our", "their", "they", "them", "i", "me", "my", "mine",
        "he", "she", "his", "her", "hers", "him", "us", "will", "just", "not", "no", "yes", "do", "does",
        "did", "done", "than", "too", "very", "have", "has", "had", "up", "down", "over", "under"
    }
    tokens = [w for w in words if w not in stopwords and len(w) > 2]
    freq = Counter(tokens)

    # Build top keyword phrases
    top_keywords = [w for w, _ in freq.most_common(6)]
    if top_keywords:
        suggestions.append(" ".join(k.capitalize() for k in top_keywords[:3]))
        if len(top_keywords) >= 4:
            suggestions.append(" ".join(k.capitalize() for k in top_keywords[:4]))
        if len(top_keywords) >= 5:
            suggestions.append(f"{top_keywords[0].capitalize()} {top_keywords[1].capitalize()} Guide")

    # 3) Short summary
    if text:
        summary = text[:90].rstrip()
        if len(text) > 90:
            summary += "..."
        suggestions.append(summary)

    # 4) Deduplicate and clean
    cleaned: List[str] = []
    seen = set()
    for s in suggestions:
        s = re.sub(r"\s+", " ", s).strip(" -–—:;,.")
        if not s:
            continue
        # Soft normalize for duplicates
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)

    # 5) Ensure we return at least one generic title if everything fails
    if not cleaned:
        cleaned = ["Notes Summary"]

    return cleaned[:max_titles]


async def _titles_via_perplexity(content: str, max_titles: int = 5) -> List[str]:
    """
    Call Perplexity API to obtain title suggestions. Falls back to heuristic
    if the upstream call fails or returns an unexpected format.
    """
    api_key = _get_api_key()
    if not api_key:
        return _heuristic_titles_from_content(content, max_titles=max_titles)

    system_prompt = (
        "You are a helpful assistant that writes succinct, catchy, and informative note titles. "
        "Return only a JSON array of strings with 3-5 title suggestions. Avoid quotes around the JSON block."
    )
    user_prompt = (
        "Generate concise and relevant titles for the following note content. "
        f"Return a JSON array of strings only, with no extra text.\n\nContent:\n{content}\n"
    )

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": DEFAULT_TEMPERATURE,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(PERPLEXITY_API_URL, json=payload, headers=headers)
            if resp.status_code >= 400:
                return _heuristic_titles_from_content(content, max_titles=max_titles)
            data = resp.json()
    except httpx.HTTPError:
        return _heuristic_titles_from_content(content, max_titles=max_titles)

    # Parse response text to extract an array of titles.
    try:
        choices = data.get("choices") or []
        if not choices:
            return _heuristic_titles_from_content(content, max_titles=max_titles)
        message = choices[0].get("message") or {}
        text = message.get("content") or ""

        # Extract JSON array from the content robustly
        # Find the first [ ... ] block
        m = re.search(r"\[.*\]", text, flags=re.S)
        if not m:
            return _heuristic_titles_from_content(content, max_titles=max_titles)

        import json
        arr = json.loads(m.group(0))
        titles = [str(x).strip() for x in arr if isinstance(x, (str, int, float))]
        titles = [t for t in titles if t]
        if not titles:
            return _heuristic_titles_from_content(content, max_titles=max_titles)

        # Deduplicate and cap
        deduped: List[str] = []
        seen = set()
        for t in titles:
            k = t.lower().strip()
            if k not in seen:
                seen.add(k)
                deduped.append(t.strip(" -–—:;,."))
        return deduped[:max_titles]
    except Exception:
        return _heuristic_titles_from_content(content, max_titles=max_titles)


# PUBLIC_INTERFACE
@router.post(
    "/recommend-title",
    response_model=RecommendTitleResponse,
    summary="Recommend titles for note content",
    description=(
        "Suggest relevant and concise titles for user-authored notes. "
        "Uses Perplexity API when configured via PERPLEXITY_API_KEY; otherwise falls back to a local heuristic."
    ),
    responses={
        200: {"description": "Title suggestions generated"},
        400: {"description": "Invalid input"},
        500: {"description": "Service error"},
    },
)
async def recommend_title(payload: RecommendTitleRequest) -> RecommendTitleResponse:
    """
    Recommend titles for a given note content.

    Parameters:
      - content: The body of the note text.

    Returns:
      - A list of suggested titles (best-effort). If Perplexity is not configured or fails,
        a heuristics-based fallback is used.
    """
    content = (payload.content or "").strip()
    if not content or len(content) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content is required and must be at least 3 characters.",
        )

    suggestions = await _titles_via_perplexity(content, max_titles=5)
    return RecommendTitleResponse(suggestions=suggestions)
