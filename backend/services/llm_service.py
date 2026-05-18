"""Multi-provider LLM generation service (Gemini -> Ollama -> mock)."""

from __future__ import annotations

import json
import logging
import re

import httpx

from services.config import settings

logger = logging.getLogger("rizzai.llm")
_LAST_PROVIDER_USED = "none"

MAX_REPLY_WORDS = 52


def _ollama_generate_url() -> str:
    base = settings.ollama_base_url.rstrip("/")
    return f"{base}/api/generate"


def _ollama_models() -> tuple[str, ...]:
    raw = (settings.ollama_models or "tinyllama,phi3,llama3").strip()
    models = tuple(m.strip() for m in raw.split(",") if m.strip())
    return models or ("tinyllama", "phi3", "llama3")


def _gemini_text_from_response(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    chunks = [str(p.get("text", "")).strip() for p in parts if p.get("text")]
    text = "\n".join(chunk for chunk in chunks if chunk).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text.")
    return text


def build_reply_prompt(
    conversation_text: str,
    tone: str,
    user_style: str,
    retrieved_examples: list[dict[str, str]] | None = None,
    reply_count: int = 3,
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

    n = max(3, min(12, int(reply_count)))
    return (
        "You are CharmAI, a dating reply assistant.\n\n"
        f"conversation_text:\n{conversation_text.strip()}\n\n"
        f"selected_tone: {tone.strip() or 'playful'}\n"
        f"user_style: {user_style.strip() or 'calm'}\n\n"
        f"retrieved_rag_examples:\n{examples_block}\n\n"
        "Task:\n"
        f"Generate exactly {n} replies to pick from — natural, confident, respectful, and clearly different angles.\n"
        "Each reply MUST reference something specific from the conversation (a topic, word, joke, plan, or detail).\n"
        "Length should match the chat context: keep dry chats brief, but when needed use up to "
        "three short sentences in a natural texting style.\n\n"
        "Avoid:\n"
        "- generic filler (e.g. 'what are you up to', 'tell me about yourself', 'you seem cool', "
        "'how's your day', 'keep chatting', 'I like your energy')\n"
        "- long messages\n"
        "- cringe pickup lines\n"
        "- repetition\n"
        "- overly formal tone\n\n"
        "Output format:\n"
        f"Return only a clean list of {n} replies, one per line, no extra commentary."
    )


def _clean_reply(text: str) -> str:
    """Clean formatting and keep short natural style."""
    cleaned = re.sub(r"^[-*\d.)\s]+", "", text).strip().strip('"').strip("'")
    words = cleaned.split()
    if len(words) > MAX_REPLY_WORDS:
        cleaned = " ".join(words[:MAX_REPLY_WORDS]).rstrip(",.;:-") + "."
    return cleaned


def _unwrap_markdown_json(raw: str) -> str:
    """Strip ```json fences and surrounding whitespace from model output."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _is_json_artifact(line: str) -> bool:
    """True if a line is JSON structure, not an actual chat reply."""
    s = line.strip()
    if not s:
        return True
    lowered = s.lower()
    if lowered in {"{", "}", "[", "]", "```", "```json", "json"}:
        return True
    if re.match(r'^["\']?(replies|labels|suggestions)["\']?\s*:', lowered):
        return True
    if s.startswith("```"):
        return True
    if re.fullmatch(r"[\{\}\[\],]+", s):
        return True
    if re.match(r'^["\']', s) and s.endswith((",", '",', "],")):
        return True
    return False


def _parse_json_payload(text: str) -> tuple[list[str], list[str]]:
    """Parse a JSON object/array into replies and optional labels."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\"replies\"[\s\S]*\}", text)
        if not match:
            return [], []
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return [], []

    replies: list[str] = []
    labels: list[str] = []

    if isinstance(parsed, dict):
        for key in ("replies", "suggestions"):
            if isinstance(parsed.get(key), list):
                replies = [_clean_reply(str(x)) for x in parsed[key] if str(x).strip()]
                break
        if isinstance(parsed.get("labels"), list):
            labels = [str(x).strip().lower() for x in parsed["labels"] if str(x).strip()]
    elif isinstance(parsed, list):
        replies = [_clean_reply(str(x)) for x in parsed if str(x).strip()]

    replies = [r for r in replies if r and not _is_json_artifact(r)]
    return replies, labels


def parse_reply_content(raw_text: str) -> tuple[list[str], list[str]]:
    """
    Extract reply strings (and optional labels) from LLM output.

    Handles markdown-wrapped JSON, plain JSON, labeled lines, and plain lists.
    """
    text = _unwrap_markdown_json(raw_text)
    if not text:
        return [], []

    replies, labels = _parse_json_payload(text)
    if replies:
        return replies, labels

    replies = []
    labels = []
    for line in text.split("\n"):
        clean = re.sub(r"^[-*\d.)\s]+", "", line).strip().strip('"').strip("'")
        if not clean or _is_json_artifact(clean):
            continue
        match = re.match(r"^\[(playful|bold|safe|smooth)\]\s*(.+)$", clean, flags=re.I)
        if match:
            labels.append(match.group(1).lower())
            replies.append(_clean_reply(match.group(2)))
        else:
            replies.append(_clean_reply(clean))

    replies = [r for r in replies if r and not _is_json_artifact(r)]
    return replies, labels


def _extract_replies(raw_text: str) -> list[str]:
    """Extract reply lines from text or JSON formats."""
    replies, _ = parse_reply_content(raw_text)
    return replies


def _dedupe_replies(replies: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    unique: list[str] = []
    for reply in replies:
        key = reply.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(reply)
    return unique


_VARIED_REPLY_PADS: tuple[str, ...] = (
    "Fair point — what made you say that?",
    "I'm curious where you're going with this.",
    "That tracks. What's the story behind it?",
    "Ha, noted. What would you want me to say back?",
    "Okay but give me one more detail to work with.",
    "Low-key invested now — expand on that?",
    "Solid. What's your take if we flip it around?",
    "I hear you. What's the vibe you're aiming for here?",
    "Interesting — is that playful or serious on your end?",
    "Got it. What would feel like a natural next message?",
    "Say more — I can match your energy better.",
    "Wait, that's vague in a fun way. Clarify?",
)


def pad_unique_replies(replies: list[str], *, count: int) -> list[str]:
    """Return exactly `count` unique replies, adding varied lines if needed."""
    n = max(3, min(12, int(count)))
    out = _dedupe_replies([_clean_reply(r) for r in replies if r and r.strip()])
    pad_i = 0
    guard = 0
    while len(out) < n and guard < n * 4:
        guard += 1
        candidate = _VARIED_REPLY_PADS[pad_i % len(_VARIED_REPLY_PADS)]
        pad_i += 1
        key = candidate.lower()
        if key not in {r.lower() for r in out}:
            out.append(candidate)
    return out[:n]


def _mock_replies(count: int = 3) -> list[str]:
    """Safe fallback responses when providers are unavailable."""
    global _LAST_PROVIDER_USED
    _LAST_PROVIDER_USED = "mock"
    logger.info("[LLM] provider=mock (fallback)")
    base = [
        "Haha fair, I like your energy. What are you up to today?",
        "Low-key curious now. Give me one fun detail about you.",
        "Nice, keeping it simple works. Want to keep chatting?",
        "You seem cool. Coffee person or tea person?",
        "I can work with this vibe. What should I know next?",
    ]
    n = max(3, min(12, int(count)))
    return [base[i % len(base)] for i in range(n)]


def _ensure_reply_count(replies: list[str], *, count: int) -> list[str]:
    """Guarantee exactly `count` unique replies."""
    return pad_unique_replies(replies, count=count)


def generate_with_gemini(prompt: str, max_tokens: int = 400) -> str:
    """Generate text with Google Gemini API if key is present."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    global _LAST_PROVIDER_USED
    _LAST_PROVIDER_USED = "gemini"
    logger.info("[LLM] provider=gemini")
    model = (settings.gemini_model or "gemini-2.0-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    wants_json = "json" in prompt.lower() and ("replies" in prompt.lower() or '"replies"' in prompt)
    gen_cfg: dict = {
        "temperature": 0.85,
        "maxOutputTokens": max(256, min(8192, int(max_tokens))),
    }
    if wants_json:
        gen_cfg["responseMimeType"] = "application/json"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_cfg,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        return _gemini_text_from_response(data)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Gemini generation failed: {exc}") from exc


def generate_with_ollama(prompt: str) -> str:
    """Generate text with local Ollama server (models from OLLAMA_MODELS)."""
    last_error: Exception | None = None

    for model in _ollama_models():
        try:
            with httpx.Client(timeout=90.0) as client:
                response = client.post(
                    _ollama_generate_url(),
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


def generate_text(prompt: str, *, max_tokens: int = 400) -> str:
    """
    Generate raw text using the first available provider.

    Order: Gemini -> Ollama.
    """
    errors: list[str] = []
    if settings.gemini_api_key:
        try:
            return generate_with_gemini(prompt, max_tokens=max_tokens)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"gemini: {exc}")
    try:
        return generate_with_ollama(prompt)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ollama: {exc}")

    raise RuntimeError("All LLM providers failed: " + "; ".join(errors))


def generate_replies(
    prompt: str | None = None,
    *,
    conversation_text: str = "",
    tone: str = "playful",
    user_style: str = "calm",
    retrieved_examples: list[dict[str, str]] | None = None,
    reply_count: int = 3,
) -> list[str]:
    """
    Generate reply_count replies with multi-provider fallback.

    Order:
    1) Gemini
    2) Ollama
    3) Mock fallback
    """
    rc = max(3, min(12, int(reply_count)))
    final_prompt = prompt or build_reply_prompt(
        conversation_text=conversation_text,
        tone=tone,
        user_style=user_style,
        retrieved_examples=retrieved_examples,
        reply_count=rc,
    )

    try:
        text = generate_text(final_prompt, max_tokens=1200)
        replies, _ = parse_reply_content(text)
        if replies:
            return _ensure_reply_count(replies, count=rc)
    except Exception:  # noqa: BLE001
        pass

    return _ensure_reply_count(_mock_replies(count=rc), count=rc)


def extract_conversation_text_from_screenshot(
    *,
    image_base64: str,
    mime_type: str,
) -> tuple[str, str | None]:
    """
    OCR-ish extraction via Gemini vision (screenshots of chat apps).

    Returns (conversation_text, optional_warning).
    """
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing — cannot read screenshots. Paste text manually instead."
        )

    model = (settings.gemini_model or "gemini-2.0-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Extract the visible conversation text from this chat screenshot. "
                            "Output only transcribed messages in chronological order, one per line. "
                            "Use 'Them:' or 'You:' when the speaker is clear; otherwise 'Message:'. "
                            "No preamble."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64.strip(),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2000},
    }

    global _LAST_PROVIDER_USED
    _LAST_PROVIDER_USED = "gemini:vision"
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        text = _gemini_text_from_response(data)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Vision extraction failed: {exc}") from exc

    warning = None
    if len(text) > 3500:
        text = text[:3500].rstrip() + "\n…(truncated)"
        warning = "Extracted text was long and was truncated — you can edit before generating."

    return text, warning


def get_last_provider_name() -> str:
    """Return provider used by the latest generate_replies call."""
    return _LAST_PROVIDER_USED
