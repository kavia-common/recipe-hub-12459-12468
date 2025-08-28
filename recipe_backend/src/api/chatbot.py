from __future__ import annotations

from typing import List, Optional, Any, Dict

import os
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.core.config import get_settings

router = APIRouter(prefix="", tags=["Chatbot"])

settings = get_settings()

# Constants for Perplexity API
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
# Default model; can be adjusted if needed or made configurable
DEFAULT_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")
DEFAULT_MAX_TOKENS = int(os.getenv("PERPLEXITY_MAX_TOKENS", "512"))
DEFAULT_TEMPERATURE = float(os.getenv("PERPLEXITY_TEMPERATURE", "0.2"))


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role in the conversation, usually 'user' or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """
    Input schema for chatbot requests. Accepts an array of messages and optional parameters.
    """
    messages: List[ChatMessage] = Field(..., description="Ordered chat messages for the conversation")
    model: Optional[str] = Field(None, description="Perplexity model to use; overrides default if provided")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens in the response")
    temperature: Optional[float] = Field(None, description="Sampling temperature")


class ChatChoice(BaseModel):
    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Message content for this choice")
    finish_reason: Optional[str] = Field(None, description="Reason the generation finished")


class ChatbotResponse(BaseModel):
    """
    Standardized response from the chatbot endpoint, wrapping Perplexity's response.
    """
    id: Optional[str] = Field(None, description="Completion id")
    model: Optional[str] = Field(None, description="Model used for generation")
    object: Optional[str] = Field(None, description="Object type, e.g., 'chat.completion'")
    created: Optional[int] = Field(None, description="Creation timestamp (epoch seconds)")
    choices: List[ChatChoice] = Field(..., description="Completion choices from the model")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage info from provider")


def _get_api_key() -> str:
    """
    Obtain the Perplexity API key from environment via the centralized settings/config.
    Raises an HTTP 500 if not configured.
    """
    # We read from env via os.getenv to avoid exposing secrets in settings dumps.
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        # Hide exact configuration details in response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service is not configured",
        )
    return key


# PUBLIC_INTERFACE
@router.post(
    "/chatbot",
    response_model=ChatbotResponse,
    summary="Chat with the Perplexity-powered assistant",
    description=(
        "Proxy chat messages to the Perplexity API using a backend-held API key. "
        "This endpoint never exposes the provider API key to the client."
    ),
    responses={
        200: {"description": "Chat response returned"},
        400: {"description": "Invalid input"},
        500: {"description": "Upstream service error"},
    },
)
async def chatbot(request: ChatRequest) -> ChatbotResponse:
    """
    Chat endpoint that forwards the conversation to Perplexity API.

    Parameters:
      - request: ChatRequest containing messages and optional generation parameters.

    Returns:
      - ChatbotResponse with the model output. On error from the provider, returns 500 with a generic message.
    """
    api_key = _get_api_key()

    payload = {
        "model": request.model or DEFAULT_MODEL,
        "messages": [m.model_dump() for m in request.messages],
        "max_tokens": request.max_tokens or DEFAULT_MAX_TOKENS,
        "temperature": request.temperature if request.temperature is not None else DEFAULT_TEMPERATURE,
        # You may add other supported fields here (e.g., top_p, presence_penalty, frequency_penalty) as needed.
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(PERPLEXITY_API_URL, json=payload, headers=headers)
    except httpx.HTTPError as e:
        # Network or timeout issue
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service temporarily unavailable",
        ) from e

    if resp.status_code >= 400:
        # Do not leak upstream details broadly; send generic message
        # Optionally log resp.text/server error via your logging system here.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service returned an error",
        )

    # Map Perplexity's response into our ChatbotResponse schema
    try:
        data = resp.json()
        # Ensure choices/messages structure matches our schema; default to safe empty list on anomalies
        choices_raw = data.get("choices") or []
        choices: List[ChatChoice] = []
        for idx, ch in enumerate(choices_raw):
            msg = ch.get("message") or {}
            # Normalize: Perplexity usually returns role/content fields
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            finish_reason = ch.get("finish_reason")
            choices.append(
                ChatChoice(
                    index=ch.get("index", idx),
                    message=ChatMessage(role=role, content=content),
                    finish_reason=finish_reason,
                )
            )

        return ChatbotResponse(
            id=data.get("id"),
            model=data.get("model"),
            object=data.get("object"),
            created=data.get("created"),
            choices=choices,
            usage=data.get("usage"),
        )
    except Exception as e:
        # Defensive: if provider format changes unexpectedly
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse chat response",
        ) from e
