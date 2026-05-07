"""Multi-provider LLM generation service (OpenAI -> Ollama -> mock)."""

from __future__ import annotations

import json
import logging
import re

import httpx

from services.config import settings

logger = logging.getLogger("rizzai.llm")
_LAST_PROVIDER_USED = "none"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELS = ("llama3", "phi3", "tinyllama")
MAX_REPLY_WORDS = 16


def build_reply_prompt(
    conversation_text: str,
    tone: str,
    user_style: str,
    retrieved_examples: list[dict[str, str]] | None = None,
) -> str:
    """Build a strong prompt for multi-provider reply generation."""
    examples = retrieved_examples or []
    formatted_examples: list[str] = []
    for idx, item in enumerate(examples[:5], start=1):
        formatted_examples.append(
            (
                f"[{idx}] id={item.get('id', '')} tone={item.get('tone', '')}\n"
                f"situation={item.get('situation', '')}\n"
                f"example_reply={item.get('example_reply', '')}"
            )
        )
    examples_block = "\n\n".join(formatted_examples) if formatted_examples else "No retrieved examples."

    return (
        "You are CharmAI, a dating reply assistant.\n\n"
        f"conversation_text:\n{conversation_text.strip()}\n\n"
        f"selected_tone: {tone.strip() or 'playful'}\n"
        f"user_style: {user_style.strip() or 'calm'}\n\n"
        f"retrieved_rag_examples:\n{examples_block}\n\n"
        "Task:\n"
        "Generate 5 replies that are short, natural, confident, respectful, and slightly varied.\n\n"
        "Avoid:\n"
        "- long messages\n"
        "- cringe pickup lines\n"
        "- repetition\n"
        "- overly formal tone\n\n"
        "Output format:\n"
        "Return only a clean list of 5 replies, one per line, no extra commentary."
    )


def _clean_reply(text: str) -> str:
    """Clean formatting and keep short natural style."""
    cleaned = re.sub(r"^[-*\d.)\s]+", "", text).strip().strip('"')
    words = cleaned.split()
    if len(words) > MAX_REPLY_WORDS:
        cleaned = " ".join(words[:MAX_REPLY_WORDS]).rstrip(",.;:-") + "."
    return cleaned


def _extract_replies(raw_text: str) -> list[str]:
    """Extract reply lines from text or JSON formats."""
    text = (raw_text or "").strip()
    if not text:
        return []

    # Try JSON first.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            if isinstance(parsed.get("replies"), list):
                return [_clean_reply(str(x)) for x in parsed["replies"] if str(x).strip()]
            if isinstance(parsed.get("suggestions"), list):
                return [_clean_reply(str(x)) for x in parsed["suggestions"] if str(x).strip()]
        if isinstance(parsed, list):
            return [_clean_reply(str(x)) for x in parsed if str(x).strip()]
    except json.JSONDecodeError:
        pass

    lines = [_clean_reply(line) for line in text.split("\n") if line.strip()]
    return [line for line in lines if line]


def _dedupe_replies(replies: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for reply in replies:
        key = reply.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(reply)
    return unique


def _mock_replies() -> list[str]:
    """Safe fallback responses when providers are unavailable."""
    global _LAST_PROVIDER_USED
    _LAST_PROVIDER_USED = "mock"
    logger.info("[LLM] provider=mock (fallback)")
    return [
        "Haha fair, I like your energy. What are you up to today?",
        "Low-key curious now. Give me one fun detail about you.",
        "Nice, keeping it simple works. Want to keep chatting?",
        "You seem cool. Coffee person or tea person?",
        "I can work with this vibe. What should I know next?",
    ]


def _ensure_five_replies(replies: list[str]) -> list[str]:
    """Guarantee exactly 5 short, non-repetitive replies."""
    safe = _dedupe_replies([_clean_reply(r) for r in replies if r.strip()])
    while len(safe) < 5:
        safe.append("Tell me one more detail and I will tailor this better.")
        safe = _dedupe_replies(safe)
    return safe[:5]


def generate_with_openai(prompt: str) -> str:
    """Generate text with OpenAI-compatible API if key is present."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    global _LAST_PROVIDER_USED
    _LAST_PROVIDER_USED = "openai"
    logger.info("[LLM] provider=openai")
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate high-quality dating chat replies. "
                    "Always follow the user prompt constraints and return only the requested clean list."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 400,
    }

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OpenAI generation failed: {exc}") from exc


def generate_with_ollama(prompt: str) -> str:
    """
    Generate text with local Ollama server.

    Tries models in order: llama3 -> phi3 -> tinyllama.
    """
    last_error: Exception | None = None

    for model in OLLAMA_MODELS:
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    OLLAMA_URL,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
            text = str(data.get("response", "")).strip()
            if text:
                global _LAST_PROVIDER_USED
                _LAST_PROVIDER_USED = f"ollama:{model}"
                logger.info("[LLM] provider=ollama:%s", model)
                return text
            last_error = RuntimeError(f"Ollama model '{model}' returned empty response.")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    raise RuntimeError(f"Ollama generation failed: {last_error}")


def generate_replies(
    prompt: str | None = None,
    *,
    conversation_text: str = "",
    tone: str = "playful",
    user_style: str = "calm",
    retrieved_examples: list[dict[str, str]] | None = None,
) -> list[str]:
    """
    Generate exactly 5 replies with multi-provider fallback.

    Order:
    1) OpenAI
    2) Ollama
    3) Mock fallback
    """
    final_prompt = prompt or build_reply_prompt(
        conversation_text=conversation_text,
        tone=tone,
        user_style=user_style,
        retrieved_examples=retrieved_examples,
    )

    try:
        text = generate_with_openai(final_prompt)
        replies = _extract_replies(text)
        return _ensure_five_replies(replies)
    except Exception:  # noqa: BLE001
        pass

    try:
        text = generate_with_ollama(final_prompt)
        replies = _extract_replies(text)
        return _ensure_five_replies(replies)
    except Exception:  # noqa: BLE001
        pass

    return _ensure_five_replies(_mock_replies())


def get_last_provider_name() -> str:
    """Return provider used by the latest generate_replies call."""
    return _LAST_PROVIDER_USED
