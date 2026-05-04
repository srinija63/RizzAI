"""Generate dating replies using RAG + OpenAI-compatible chat API."""

import json
import re
from typing import Any

import httpx

from services.config import settings
from services.rag_service import retrieve_patterns


def _is_unsafe_text(text: str) -> bool:
    """Basic safety screen for risky or coercive language."""
    t = text.lower()
    blocked_markers = [
        "nudes",
        "send pics",
        "explicit",
        "sex",
        "hook up",
        "manipulate",
        "guilt",
        "pressure",
        "force",
        "stalk",
        "track her",
        "catfish",
        "lie to",
        "deceive",
        "harass",
    ]
    return any(marker in t for marker in blocked_markers)


def _safe_redirect_replies(tone: str) -> tuple[list[str], list[str], str]:
    """Fallback safe alternatives when user input or model output is unsafe."""
    t = tone.lower().strip() or "calm"
    replies = [
        "I want to keep this respectful and comfortable for both people.",
        "A better move is honest interest and clear communication.",
        "Try a simple message: hey, would you like to chat this week?",
        "If they are unsure, give space and avoid pushing.",
        f"Keep it {t} and kind - confidence works better than pressure.",
    ]
    labels = ["safe", "safe", "smooth", "safe", "safe"]
    note = "Safety mode: returned respectful alternatives."
    return replies, labels, note


def _mock_rag_replies(
    conversation_text: str,
    tone: str,
    user_style: str,
    examples: list[dict[str, Any]],
) -> tuple[list[str], list[str], str]:
    """Return local mock replies grounded by retrieved examples."""
    if _is_unsafe_text(conversation_text):
        return _safe_redirect_replies(tone)

    soft_tone = tone.lower()
    style_hint = user_style.lower()
    lead = "calm" if "calm" in style_hint else "natural"
    return (
        [
            f"{lead.title()} take: haha fair, that was a short one. Want to keep it going?",
            f"I like your vibe. Should I read that '{conversation_text.strip()[:18]}' as playful or mysterious?",
            f"Keeping it {soft_tone}: I can work with a lol, give me one more clue about you.",
            "No pressure, we can keep it light. What are you up to today?",
            f"Little {soft_tone} reset: was that a playful maybe or a polite maybe?",
        ],
        ["safe", "playful", "smooth", "safe", "bold"],
        "Mock mode with RAG context: set OPENAI_API_KEY for full model generation.",
    )


def _build_prompt(
    conversation_text: str,
    tone: str,
    user_style: str,
    examples: list[dict[str, Any]],
) -> str:
    """Build grounded user prompt for the model."""
    formatted_examples = []
    for idx, item in enumerate(examples, start=1):
        formatted_examples.append(
            (
                f"[{idx}] tone={item.get('tone')} situation={item.get('situation')}\n"
                f"{item.get('content')}"
            )
        )
    examples_block = "\n\n".join(formatted_examples) if formatted_examples else "No examples available."
    return (
        f"User conversation:\n{conversation_text}\n\n"
        f"Selected tone: {tone}\n\n"
        f"User style: {user_style}\n\n"
        f"Retrieved examples:\n{examples_block}\n\n"
        "Return valid JSON with this exact format:\n"
        '{"replies":["...","...","...","...","..."],"labels":["playful","bold","safe","smooth","playful"]}\n'
        "Rules:\n"
        "- Exactly 5 replies.\n"
        "- Each reply: short, natural, witty, respectful.\n"
        "- Keep each reply under 16 words.\n"
        "- Do NOT copy any retrieved example wording. Paraphrase and create fresh lines.\n"
        "- Sound like a real text message, not an advisor or narrator.\n"
        "- Avoid meta phrasing like 'based on this vibe' or 'you could say'.\n"
        "- Avoid repeating the same opener across replies.\n"
        "- Safety policy: avoid explicit sexual content, manipulation, pressure, harassment, stalking, deception, or pushy dating advice.\n"
        "- If the user asks for unsafe behavior, refuse that direction and rewrite into respectful, consent-aware alternatives.\n"
        "- Labels must be from: playful, bold, safe, smooth.\n"
        "- Keep labels aligned by index to replies."
    )


def _parse_llm_output(content: str) -> tuple[list[str], list[str]]:
    """Parse model output into replies and labels."""
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            replies = [str(x).strip() for x in parsed.get("replies", []) if str(x).strip()]
            labels = [str(x).strip().lower() for x in parsed.get("labels", []) if str(x).strip()]
            if replies:
                return replies, labels
    except json.JSONDecodeError:
        pass

    replies: list[str] = []
    labels: list[str] = []
    for line in content.split("\n"):
        clean = re.sub(r"^[-*\d.)\s]+", "", line).strip()
        if not clean:
            continue
        match = re.match(r"^\[(playful|bold|safe|smooth)\]\s*(.+)$", clean, flags=re.I)
        if match:
            labels.append(match.group(1).lower())
            replies.append(match.group(2).strip())
        else:
            replies.append(clean)
    return replies, labels


def _normalize_output(
    replies: list[str],
    labels: list[str],
    tone: str,
) -> tuple[list[str], list[str]]:
    """Ensure exactly 5 replies and aligned labels."""
    allowed = {"playful", "bold", "safe", "smooth"}
    cleaned_replies = [r.strip().strip('"') for r in replies if r.strip()]
    cleaned_labels = [l.lower() for l in labels if l.lower() in allowed]

    while len(cleaned_replies) < 5:
        cleaned_replies.append("Tell me a bit more and I can tailor this better.")
    cleaned_replies = cleaned_replies[:5]

    if len(cleaned_labels) < 5:
        fallback_cycle = [tone.lower(), "safe", "smooth", "playful", "bold"]
        for label in fallback_cycle:
            if label in allowed and len(cleaned_labels) < 5:
                cleaned_labels.append(label)
            elif len(cleaned_labels) < 5:
                cleaned_labels.append("safe")
    cleaned_labels = cleaned_labels[:5]
    return cleaned_replies, cleaned_labels


async def generate_reply_suggestions(
    message: str,
    tone: str | None = None,
) -> tuple[list[str], list[str], str | None]:
    """
    Produce 5 short, natural, witty, respectful replies with labels.

    Uses RAG retrieval from ChromaDB to ground generation when API key is set.
    Falls back to mock replies if API key is missing.
    """
    selected_tone = (tone or "playful").strip() or "playful"
    result = await generate_rag_replies(
        conversation_text=message,
        tone=selected_tone,
        user_style="calm",
    )
    return result["replies"], result["labels"], result.get("note")


async def generate_rag_replies(
    conversation_text: str,
    tone: str,
    user_style: str = "calm",
) -> dict[str, Any]:
    """Generate RAG-grounded replies and include retrieval context."""
    selected_tone = (tone or "playful").strip() or "playful"
    style = (user_style or "calm").strip() or "calm"
    if _is_unsafe_text(conversation_text):
        replies, labels, note = _safe_redirect_replies(selected_tone)
        return {
            "inspiration_examples": [],
            "replies": replies,
            "labels": labels,
            "note": note,
        }

    try:
        examples = retrieve_patterns(
            conversation_text=conversation_text,
            tone=selected_tone,
            k=5,
        )
    except Exception:
        examples = []

    if not settings.openai_api_key:
        replies, labels, note = _mock_rag_replies(
            conversation_text=conversation_text,
            tone=selected_tone,
            user_style=style,
            examples=examples,
        )
        replies, labels = _normalize_output(replies, labels, selected_tone)
        return {
            "inspiration_examples": examples,
            "replies": replies,
            "labels": labels,
            "note": note,
        }

    system = (
        "You are RizzAI, an expert dating reply assistant. "
        "Use retrieved patterns as style guidance, not as text to copy. "
        "Output only valid JSON."
    )
    user_payload = _build_prompt(
        conversation_text=conversation_text,
        tone=selected_tone,
        user_style=style,
        examples=examples,
    )

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload},
        ],
        "temperature": 0.8,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    replies, labels = _parse_llm_output(content)
    replies, labels = _normalize_output(replies, labels, selected_tone)
    if any(_is_unsafe_text(reply) for reply in replies):
        safe_replies, safe_labels, safe_note = _safe_redirect_replies(selected_tone)
        return {
            "inspiration_examples": examples,
            "replies": safe_replies,
            "labels": safe_labels,
            "note": safe_note,
        }

    note = None
    if not examples:
        note = "RAG note: no retrieved examples found, generated from base instructions."

    return {
        "inspiration_examples": examples,
        "replies": replies,
        "labels": labels,
        "note": note,
    }
