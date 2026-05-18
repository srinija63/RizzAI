"""Generate dating replies using RAG + Gemini/Ollama LLM providers."""

import json
import logging
import re
from collections import Counter
from typing import Any

from services.config import settings
from services.llm_service import (
    generate_replies,
    generate_text,
    get_last_provider_name,
    pad_unique_replies,
    parse_reply_content,
    _is_json_artifact,
)
from services.rag_service import retrieve_patterns

logger = logging.getLogger("rizzai.rag")

# Long pasted chats: keep recent tail for retrieval and prompts (tokens + stability).
_MAX_INPUT_CHARS = 4000
_TRUNC_TAIL_CHARS = 3200
_MICRO_LEN_CAP = 4  # blanket: one-word-ish cues ("ok", "k", "lol")
_MICRO_TOKENS = frozenset(
    {
        "lol",
        "lmao",
        "lmfao",
        "ok",
        "okay",
        "k",
        "kk",
        "hmm",
        "hmmm",
        "hm",
        "idk",
        "maybe",
        "sure",
        "yeah",
        "yep",
        "yup",
        "nah",
        "nope",
        "fine",
        "nice",
        "cool",
        "hey",
        "yo",
        "sup",
        "wtf",
        "omg",
    },
)
_REPEATED_MIN_LINES = 4
_REPEATED_MIN_REPEAT_RATIO = 0.75
_REPEATED_MIN_WORD_REPS = 6  # e.g. "lol lol lol lol lol lol"
_MAX_REPLY_WORDS = 52
_SIMILARITY_REWRITE_THRESHOLD = 0.58
_LOG_INPUT_PREVIEW_CHARS = 400
_MAX_REPLY_LINES = 4
_GENERIC_PHRASES = (
    "what are you up to",
    "how's your day",
    "how is your day",
    "tell me more about you",
    "tell me about yourself",
    "you seem cool",
    "you seem nice",
    "keep chatting",
    "want to keep chatting",
    "i like your energy",
    "love your energy",
    "low-key curious",
    "one fun detail",
    "coffee person or tea",
    "what should i know",
    "nice, keeping it simple",
    "good vibes",
    "how are you doing",
    "what are you into",
    "want to get to know you",
)
_STYLE_GUIDANCE = {
    "funny": "Playful teasing + witty, light humor.",
    "calm": "Relaxed, emotionally steady, low-pressure phrasing.",
    "bold": "Confident, direct, assertive (without arrogance).",
    "romantic": "Warm, expressive, slightly deeper emotional connection.",
    "simple": "Concise, natural, low-fluff language.",
}


def _is_generic_reply(reply: str) -> bool:
    """Detect vague dating-app filler that ignores conversation specifics."""
    t = reply.lower()
    return any(phrase in t for phrase in _GENERIC_PHRASES)


def _generic_reply_count(replies: list[str]) -> int:
    return sum(1 for r in replies if _is_generic_reply(r))


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


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines; keep content readable."""
    t = (text or "").strip()
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    return t


def _preview_text(text: str, max_chars: int = _LOG_INPUT_PREVIEW_CHARS) -> str:
    """Compact input preview for logs."""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return f"{compact[:max_chars]}... (truncated)"


def _log_rag_event(
    *,
    stage: str,
    conversation_text: str,
    tone: str,
    retrieved_ids: list[str] | None = None,
    replies: list[str] | None = None,
    note: str | None = None,
) -> None:
    """Emit a clean bracketed log line for each pipeline stage."""
    preview = _preview_text(conversation_text)[:50]
    if stage == "start":
        logger.info("[Pipeline] start  tone=%s  input=%r", tone, preview)
    elif stage.startswith("edge_case"):
        label = stage.replace("edge_case_", "")
        logger.info("[Pipeline] edge_case=%s  tone=%s  replies=%d", label, tone, len(replies or []))
    elif stage == "safety_redirect_input":
        logger.info("[Pipeline] safety_redirect  tone=%s", tone)
    elif stage == "retrieved":
        ids = ", ".join(retrieved_ids or []) or "none"
        logger.info("[Pipeline] retrieved  ids=[%s]", ids)
    elif stage == "llm_generated":
        logger.info("[Pipeline] llm_generated  replies=%d", len(replies or []))
    elif stage == "final":
        top = (replies or [""])[0][:50]
        logger.info(
            "[Pipeline] done  replies=%d  ids=[%s]  top=%r",
            len(replies or []),
            ", ".join(retrieved_ids or []),
            top,
        )
    else:
        logger.info("[Pipeline] stage=%s  tone=%s", stage, tone)


def _is_mostly_repeated_lines(text: str) -> bool:
    """Detect paste spam / same line many times."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) >= _REPEATED_MIN_LINES:
        top_count = Counter(lines).most_common(1)[0][1]
        if top_count >= len(lines) * _REPEATED_MIN_REPEAT_RATIO:
            return True
    words = text.split()
    if len(words) >= _REPEATED_MIN_WORD_REPS and len(set(words)) == 1:
        return True
    return False


def _is_micro_input(text: str) -> bool:
    """Dry / low-effort single-line cues (not full sentences like 'thank you')."""
    stripped = text.strip()
    if not stripped or "\n" in stripped:
        return False
    if len(stripped) <= _MICRO_LEN_CAP:
        return True
    tokens = stripped.split()
    if len(tokens) != 1:
        return False
    word = re.sub(r"[^\w]+$", "", tokens[0]).lower()
    return word in _MICRO_TOKENS


def _truncate_for_rag_and_llm(text: str) -> tuple[str, str | None]:
    """
    If the user pasted a huge chat, keep a recent tail plus small head for context.
    Returns (possibly_truncated_text, note_or_none).
    """
    if len(text) <= _MAX_INPUT_CHARS:
        return text, None
    head = text[:500]
    tail = text[-_TRUNC_TAIL_CHARS:]
    note = (
        f"Long chat trimmed ({len(text)} characters). "
        "Suggestions focus on the most recent messages below."
    )
    combined = (
        "[Context: start of conversation]\n"
        f"{head}\n\n"
        "[… middle omitted …]\n\n"
        "[Most recent — use this for reply ideas]\n"
        f"{tail}"
    )
    return combined, note


def _edge_case_bundle(
    tone: str,
    kind: str,
    micro_snippet: str = "",
) -> dict[str, Any]:
    """Structured response for empty / micro / repeated inputs (no LLM)."""
    t = (tone or "playful").lower().strip() or "playful"

    if kind == "empty":
        replies = [
            "Paste a line or two from the chat so I can suggest a reply.",
            "Tell me what they said last — even one sentence helps.",
            "Not much to go on yet. What vibe are you going for?",
            "Quick setup: what did you last send, and what did they reply?",
            "Add their last message here and I will tailor something natural.",
        ]
        note = "No conversation text — add their message or yours for tailored replies."
        labels = ["safe", "safe", "playful", "safe", "smooth"]

    elif kind == "micro":
        cue = micro_snippet.strip() or "that"
        opener = f"Fair — '{cue}' is pretty brief." if len(cue) <= 4 else "That is a short message."
        replies = [
            f"{opener} What did you send right before?",
            "Low-effort texts happen. Try one light follow-up question.",
            "No stress — you can match energy or ask something easy about their day.",
            "If you want to keep it moving, one curious line usually beats overthinking.",
            "If replies stay one-word, give space or switch to a clear, kind ask.",
        ]
        note = "Very short input — replies assume a dry or low-effort message."
        labels = ["safe", "playful", "smooth", "bold", "safe"]

    else:  # repeated
        replies = [
            "Sending the same line many times can read as spam — one clear message works better.",
            "Try one calm follow-up instead of repeating: hey, still good to chat?",
            "If you are excited, show it once with a question, not a loop.",
            "Reset: send one honest line and give them space to answer.",
            "A single thoughtful message beats a wall of duplicates.",
        ]
        note = "Repeated messages detected — here are cleaner, natural alternatives."
        labels = ["safe", "bold", "safe", "smooth", "safe"]

    return {
        "inspiration_examples": [],
        "replies": replies,
        "labels": labels,
        "note": note,
    }


def _merge_notes(*parts: str | None) -> str | None:
    """Join non-empty note fragments into one message."""
    merged = " ".join(p.strip() for p in parts if p and str(p).strip())
    return merged or None


def _reply_tokens(text: str) -> set[str]:
    """Tokenize reply for quick similarity checks."""
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    return {t for t in tokens if len(t) > 2}


def _truncate_reply(reply: str, max_words: int = _MAX_REPLY_WORDS) -> str:
    """Keep response concise if model overshoots target length."""
    words = reply.split()
    if len(words) <= max_words:
        return reply.strip()
    trimmed = " ".join(words[:max_words]).rstrip(",.;:-")
    return f"{trimmed}."


def _rewrite_similar_reply(
    reply: str,
    tone: str,
    used_starters: set[str],
) -> str:
    """Light rewrite to diversify repetitive structures."""
    base = re.sub(r"\s+", " ", reply).strip().strip('"')
    lower = base.lower()
    tone_lower = tone.lower()

    if "?" in base:
        prefix_options = [
            "Curious one:",
            "Quick question:",
            "Low-key ask:",
            "Small follow-up:",
        ]
    elif tone_lower in {"flirty", "playful"}:
        prefix_options = [
            "Playful angle:",
            "Smooth option:",
            "Light move:",
            "Fresh take:",
        ]
    elif tone_lower in {"confident", "direct"}:
        prefix_options = [
            "Clear option:",
            "Direct move:",
            "Simple line:",
            "Confident take:",
        ]
    else:
        prefix_options = [
            "Gentle option:",
            "Calm take:",
            "Natural line:",
            "Easy follow-up:",
        ]

    for prefix in prefix_options:
        candidate = _truncate_reply(f"{prefix} {base}")
        starter = " ".join(candidate.lower().split()[:2])
        if starter not in used_starters and candidate.lower() != lower:
            return candidate
    return _truncate_reply(base)


def _diversify_replies(
    replies: list[str],
    labels: list[str],
    tone: str,
    reply_count: int = 5,
) -> tuple[list[str], list[str]]:
    """
    Reduce repetitive outputs while preserving meaning and tone.

    Rules:
    - avoid duplicate or near-duplicate sentences
    - vary first words / sentence pattern
    - keep short and natural
    """
    diversified: list[str] = []
    diversified_labels: list[str] = []
    used_starters: set[str] = set()

    for reply, label in zip(replies, labels):
        candidate = _truncate_reply(reply.strip())
        if not candidate:
            continue

        cand_tokens = _reply_tokens(candidate)
        too_similar = False
        for existing in diversified:
            ex_tokens = _reply_tokens(existing)
            union = len(cand_tokens | ex_tokens)
            if union == 0:
                continue
            similarity = len(cand_tokens & ex_tokens) / union
            if similarity >= _SIMILARITY_REWRITE_THRESHOLD:
                too_similar = True
                break

        starter = " ".join(candidate.lower().split()[:2])
        if starter in used_starters or too_similar:
            candidate = _rewrite_similar_reply(candidate, tone, used_starters)
            starter = " ".join(candidate.lower().split()[:2])

        diversified.append(candidate)
        diversified_labels.append(label)
        used_starters.add(starter)

    n = max(3, min(12, int(reply_count)))
    if len(diversified) < n:
        diversified = pad_unique_replies(diversified, count=n)
        while len(diversified_labels) < len(diversified):
            diversified_labels.append("safe")

    return diversified[:n], diversified_labels[:n]


def _tone_score(reply: str, label: str, tone: str) -> float:
    """Score how well a reply matches requested tone."""
    requested = tone.lower().strip()
    text = reply.lower()
    label_l = label.lower().strip()

    score = 0.5 if label_l in {"playful", "bold", "safe", "smooth"} else 0.2
    if requested in {"playful", "flirty"} and ("?" in reply or "vibe" in text or "fun" in text):
        score += 0.25
    if requested in {"confident", "direct"} and any(x in text for x in ("clear", "simple", "no pressure", "direct")):
        score += 0.25
    if requested == "sweet" and any(x in text for x in ("kind", "easy", "no stress", "gentle")):
        score += 0.25
    if requested == "funny" and any(x in text for x in ("haha", "lol", "fair", "mysterious")):
        score += 0.25
    return min(score, 1.0)


def _naturalness_score(reply: str) -> float:
    """Score readability and text-message naturalness."""
    text = reply.strip()
    words = text.split()
    wc = len(words)

    score = 1.0
    if wc < 4:
        score -= 0.25
    if wc > _MAX_REPLY_WORDS:
        score -= 0.35
    if any(token in text.lower() for token in ("based on this vibe", "you could say", "as an ai")):
        score -= 0.5
    if _is_generic_reply(text):
        score -= 0.45
    if "  " in text:
        score -= 0.1
    if re.search(r"[A-Z]{5,}", text):
        score -= 0.2
    return max(0.0, min(score, 1.0))


def _engagement_score(reply: str) -> float:
    """Score whether the reply naturally continues conversation."""
    text = reply.lower()
    score = 0.35
    if "?" in reply:
        score += 0.35
    if any(x in text for x in ("what", "how", "want to", "you up to", "tell me", "your")):
        score += 0.2
    if any(x in text for x in ("no pressure", "keep it light", "easy", "calm")):
        score += 0.1
    return min(score, 1.0)


def _safety_score(reply: str) -> float:
    """Score safety compliance of a reply."""
    if _is_unsafe_text(reply):
        return 0.0
    text = reply.lower()
    score = 0.85
    if any(x in text for x in ("no pressure", "respect", "kind", "comfortable")):
        score += 0.15
    return min(score, 1.0)


def _score_reply(reply: str, label: str, tone: str) -> float:
    """
    Weighted score for ranking replies.

    Dimensions:
    - tone match
    - naturalness
    - engagement
    - safety
    """
    tone_s = _tone_score(reply, label, tone)
    natural_s = _naturalness_score(reply)
    engage_s = _engagement_score(reply)
    safe_s = _safety_score(reply)
    return round(
        (tone_s * 0.30) + (natural_s * 0.25) + (engage_s * 0.20) + (safe_s * 0.25),
        4,
    )


def _rank_replies(
    replies: list[str],
    labels: list[str],
    tone: str,
) -> tuple[list[str], list[str]]:
    """Rank replies using multi-factor quality scoring."""
    scored = []
    for idx, (reply, label) in enumerate(zip(replies, labels)):
        scored.append(
            (
                _score_reply(reply, label, tone),
                idx,  # stable tie-breaker
                reply,
                label,
            )
        )
    scored.sort(key=lambda x: (-x[0], x[1]))
    sorted_replies = [x[2] for x in scored]
    sorted_labels = [x[3] for x in scored]
    return sorted_replies, sorted_labels


def _line_count(text: str) -> int:
    return max(1, len([ln for ln in text.splitlines() if ln.strip()]))


def _post_generation_validate(
    replies: list[str],
    labels: list[str],
    tone: str,
    reply_count: int = 5,
) -> tuple[list[str], list[str], bool]:
    """
    Simple final validation:
    - exactly reply_count replies
    - remove duplicates / near-duplicates
    - cap each reply to a few lines
    - trigger fallback if overall quality looks weak
    """
    rc = max(3, min(12, int(reply_count)))
    normalized_replies: list[str] = []
    normalized_labels: list[str] = []

    for reply, label in zip(replies, labels):
        trimmed = re.sub(r"\s+$", "", reply.strip())
        if not trimmed:
            continue
        # Keep first few non-empty lines if model rambles.
        lines = [ln.strip() for ln in trimmed.splitlines() if ln.strip()]
        if len(lines) > _MAX_REPLY_LINES:
            trimmed = "\n".join(lines[:_MAX_REPLY_LINES])
        normalized_replies.append(trimmed)
        normalized_labels.append(label)

    unique_replies: list[str] = []
    unique_labels: list[str] = []
    for reply, label in zip(normalized_replies, normalized_labels):
        cand_tokens = _reply_tokens(reply)
        is_dup = False
        for existing in unique_replies:
            ex_tokens = _reply_tokens(existing)
            union = len(cand_tokens | ex_tokens)
            if union == 0:
                continue
            sim = len(cand_tokens & ex_tokens) / union
            if sim >= 0.85 or reply.lower() == existing.lower():
                is_dup = True
                break
        if not is_dup:
            unique_replies.append(reply)
            unique_labels.append(label)

    if len(unique_replies) < rc:
        unique_replies = pad_unique_replies(unique_replies, count=rc)
        while len(unique_labels) < len(unique_replies):
            unique_labels.append(tone.lower() if tone.lower() in {"playful", "bold", "safe", "smooth"} else "safe")

    unique_replies, unique_labels = _normalize_output(
        unique_replies, unique_labels, tone, reply_count=rc
    )
    unique_replies, unique_labels = _diversify_replies(
        unique_replies, unique_labels, tone, reply_count=rc
    )
    unique_replies, unique_labels = _rank_replies(unique_replies, unique_labels, tone)
    unique_replies = pad_unique_replies(unique_replies, count=rc)
    unique_labels = unique_labels[: len(unique_replies)]
    while len(unique_labels) < len(unique_replies):
        unique_labels.append("safe")

    low_quality = False
    if any(not r.strip() for r in unique_replies):
        low_quality = True
    min_distinct = rc if rc <= 3 else max(3, min(4, rc // 2))
    if len(set(r.lower() for r in unique_replies)) < min_distinct:
        low_quality = True
    if all(len(_reply_tokens(r)) < 3 for r in unique_replies):
        low_quality = True
    if any(_line_count(r) > _MAX_REPLY_LINES for r in unique_replies):
        low_quality = True
    if _generic_reply_count(unique_replies) >= max(1, rc - 1):
        low_quality = True

    return unique_replies, unique_labels, low_quality


def _finalize_replies(
    replies: list[str],
    labels: list[str],
    tone: str,
    *,
    reply_count: int,
) -> tuple[list[str], list[str], bool]:
    """Normalize, diversify, rank, and validate a reply batch."""
    rc = max(3, min(12, int(reply_count)))
    out_replies, out_labels = _normalize_output(replies, labels, tone, reply_count=rc)
    out_replies, out_labels = _diversify_replies(out_replies, out_labels, tone, reply_count=rc)
    out_replies, out_labels = _rank_replies(out_replies, out_labels, tone)
    return _post_generation_validate(out_replies, out_labels, tone, reply_count=rc)


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
        "Mock mode with RAG context: set GEMINI_API_KEY (or run Ollama) for full model generation.",
    )


def _build_prompt(
    conversation_text: str,
    tone: str,
    user_style: str,
    examples: list[dict[str, Any]],
    reply_count: int = 5,
    confidence_level: str = "medium",
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
    n = max(3, min(12, int(reply_count)))
    cl = (confidence_level or "medium").lower().strip()
    if cl not in {"low", "medium", "high"}:
        cl = "medium"
    confidence_notes = {
        "low": (
            "Confidence energy: LOW — keep wording soft and low-pressure, more hedging is fine, "
            "avoid sounding forward or intense."
        ),
        "medium": (
            "Confidence energy: MEDIUM — balanced: clear and warm without being timid or overwhelming."
        ),
        "high": (
            "Confidence energy: HIGH — more direct and assertive framing, still respectful and never pushy; "
            "no desperation or neediness."
        ),
    }
    conf_block = confidence_notes[cl]
    angles = [
        "callback — quote or riff on something specific they said",
        "curious question — ask about one concrete detail they mentioned",
        "playful tease — light joke tied to the chat, not a generic pickup line",
        "warm statement — genuine reaction plus a small invite to continue",
        "direct move — clear next step or opinion tied to the thread",
        "hypothesis — playful guess about them based on one profile/chat detail",
    ]
    angle_lines = "\n".join(
        f"  - Reply {i + 1}: {angles[i % len(angles)]}" for i in range(n)
    )
    style_line = (
        f"User style notes: {user_style.strip()}\n\n" if (user_style or "").strip() else ""
    )
    return (
        f"User conversation:\n{conversation_text}\n\n"
        f"Selected tone (user chose — do not change): {tone}\n\n"
        f"{style_line}"
        f"{conf_block}\n\n"
        f"Retrieved examples:\n{examples_block}\n\n"
        "Return valid JSON with keys: replies (array of strings), labels (array of strings).\n"
        f"- The replies array must contain exactly {n} strings; labels must be the same length.\n"
        f"- Quality over quantity: all {n} replies must be clearly different from each other.\n"
        "Required angles (each reply must follow its assigned angle — no duplicates):\n"
        f"{angle_lines}\n"
        "Rules:\n"
        "- If the conversation contains a marked 'Most recent' section, base replies mainly on that part.\n"
        "- Each reply: natural, witty, respectful.\n"
        "- Length should fit the situation: keep dry contexts short, but when needed use up to 3 short sentences.\n"
        "- Each reply MUST reference at least one concrete detail from the conversation "
        "(topic, word, joke, plan, place, typo, or emoji context).\n"
        "- Vary sentence structure: mix question, statement, and light invite formats.\n"
        f"- Subtly vary within the selected tone; do not make all {n} lines sound identical.\n"
        "- Do NOT copy any retrieved example wording. Paraphrase and create fresh lines.\n"
        "- Sound like a real text message, not an advisor or narrator.\n"
        "- Avoid meta phrasing like 'based on this vibe' or 'you could say'.\n"
        "- Avoid generic filler: 'what are you up to', 'tell me about yourself', 'you seem cool', "
        "'how's your day', 'keep chatting', 'I like your energy'.\n"
        "- Avoid repeating the same opener, phrase, or sentence structure across replies.\n"
        "- Every reply must be meaningfully different — no copy-paste with tiny edits.\n"
        "- Safety policy: avoid explicit sexual content, manipulation, pressure, harassment, stalking, deception, or pushy dating advice.\n"
        "- If the user asks for unsafe behavior, refuse that direction and rewrite into respectful, consent-aware alternatives.\n"
        "- Labels must be from: playful, bold, safe, smooth.\n"
        "- Keep labels aligned by index to replies."
    )


def _parse_llm_output(content: str) -> tuple[list[str], list[str]]:
    """Parse model output into replies and labels."""
    return parse_reply_content(content)


def _normalize_output(
    replies: list[str],
    labels: list[str],
    tone: str,
    reply_count: int = 5,
) -> tuple[list[str], list[str]]:
    """Ensure exactly reply_count replies and aligned labels."""
    n = max(3, min(12, int(reply_count)))
    allowed = {"playful", "bold", "safe", "smooth"}
    cleaned_replies = [
        r.strip().strip('"')
        for r in replies
        if r.strip() and not _is_json_artifact(r)
    ]
    cleaned_labels = [l.lower() for l in labels if l.lower() in allowed]

    cleaned_replies = pad_unique_replies(cleaned_replies, count=n)

    if len(cleaned_labels) < n:
        fallback_cycle = [tone.lower(), "safe", "smooth", "playful", "bold"]
        for label in fallback_cycle:
            if label in allowed and len(cleaned_labels) < n:
                cleaned_labels.append(label)
            elif len(cleaned_labels) < n:
                cleaned_labels.append("safe")
    cleaned_labels = cleaned_labels[:n]
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
    reply_count: int = 5,
    confidence_level: str = "medium",
) -> dict[str, Any]:
    """Generate RAG-grounded replies and include retrieval context."""
    selected_tone = (tone or "playful").strip() or "playful"
    style = (user_style or "").strip()
    conf = (confidence_level or "medium").strip().lower()
    if conf not in {"low", "medium", "high"}:
        conf = "medium"
    rc = max(3, min(12, int(reply_count)))

    normalized = _normalize_whitespace(conversation_text or "")
    _log_rag_event(
        stage="start",
        conversation_text=normalized,
        tone=selected_tone,
    )

    if not normalized:
        bundle = _edge_case_bundle(selected_tone, "empty")
        r, lab = _normalize_output(bundle["replies"], bundle["labels"], selected_tone, reply_count=rc)
        r, lab = _rank_replies(r, lab, selected_tone)
        _log_rag_event(
            stage="edge_case_empty",
            conversation_text=normalized,
            tone=selected_tone,
            replies=r,
            note=bundle["note"],
        )
        return {**bundle, "replies": r, "labels": lab, "provider_used": "mock"}

    if _is_unsafe_text(normalized):
        replies, labels, note = _safe_redirect_replies(selected_tone)
        _log_rag_event(
            stage="safety_redirect_input",
            conversation_text=normalized,
            tone=selected_tone,
            replies=replies,
            note=note,
        )
        return {
            "inspiration_examples": [],
            "replies": replies,
            "labels": labels,
            "note": note,
            "provider_used": "mock",
        }

    if _is_mostly_repeated_lines(normalized):
        bundle = _edge_case_bundle(selected_tone, "repeated")
        r, lab = _normalize_output(bundle["replies"], bundle["labels"], selected_tone, reply_count=rc)
        r, lab = _rank_replies(r, lab, selected_tone)
        _log_rag_event(
            stage="edge_case_repeated",
            conversation_text=normalized,
            tone=selected_tone,
            replies=r,
            note=bundle["note"],
        )
        return {**bundle, "replies": r, "labels": lab, "provider_used": "mock"}

    if _is_micro_input(normalized):
        bundle = _edge_case_bundle(selected_tone, "micro", micro_snippet=normalized)
        r, lab = _normalize_output(bundle["replies"], bundle["labels"], selected_tone, reply_count=rc)
        r, lab = _rank_replies(r, lab, selected_tone)
        _log_rag_event(
            stage="edge_case_micro",
            conversation_text=normalized,
            tone=selected_tone,
            replies=r,
            note=bundle["note"],
        )
        return {**bundle, "replies": r, "labels": lab, "provider_used": "mock"}

    work_text, long_note = _truncate_for_rag_and_llm(normalized)

    try:
        examples = retrieve_patterns(
            conversation_text=work_text,
            tone=selected_tone,
            k=5,
        )
    except Exception:
        examples = []
    retrieved_ids = [str(x.get("id")) for x in examples if x.get("id")]

    prompt = _build_prompt(
        conversation_text=work_text,
        tone=selected_tone,
        user_style=style,
        examples=examples,
        reply_count=rc,
        confidence_level=conf,
    )
    raw_llm = generate_text(prompt, max_tokens=1200)
    provider_name = get_last_provider_name()
    replies, labels = _parse_llm_output(raw_llm)
    if not replies:
        replies = generate_replies(
            prompt,
            conversation_text=work_text,
            tone=selected_tone,
            user_style=style,
            reply_count=rc,
        )
        labels = []
    logger.info("[LLM] provider=%s  replies_raw=%d", provider_name, len(replies))
    replies, labels, low_quality = _finalize_replies(
        replies, labels, selected_tone, reply_count=rc
    )
    if low_quality:
        retry_prompt = (
            f"{prompt}\n\n"
            "RETRY — previous replies were too vague or generic. "
            f"Write exactly {rc} replies. Each must hook to a specific detail from the conversation "
            "(topic, phrase, joke, plan, place, or emoji). "
            "Never use filler like 'what are you up to', 'tell me about yourself', "
            "'you seem cool', 'how's your day', or 'keep chatting'."
        )
        retry_raw_text = generate_text(retry_prompt, max_tokens=1200)
        retry_replies, retry_labels = _parse_llm_output(retry_raw_text)
        if not retry_replies:
            retry_replies = generate_replies(
                retry_prompt,
                conversation_text=work_text,
                tone=selected_tone,
                user_style=style,
                reply_count=rc,
            )
            retry_labels = []
        replies, labels, low_quality = _finalize_replies(
            retry_replies, retry_labels, selected_tone, reply_count=rc
        )
        provider_name = get_last_provider_name()
        logger.info("[LLM] retry provider=%s", provider_name)

    if low_quality:
        replies, labels, mock_note = _mock_rag_replies(
            conversation_text=work_text,
            tone=selected_tone,
            user_style=style,
            examples=examples,
        )
        replies, labels, _ = _finalize_replies(replies, labels, selected_tone, reply_count=rc)
        rag_note = _merge_notes(
            "Low-quality output detected; switched to mock fallback.",
            None if examples else "RAG note: no retrieved examples found, generated from base instructions.",
        )
        merged_note = _merge_notes(long_note, mock_note, rag_note)
        _log_rag_event(
            stage="llm_generation_fallback_mock",
            conversation_text=work_text,
            tone=selected_tone,
            retrieved_ids=retrieved_ids,
            replies=replies,
            note=merged_note,
        )
        return {
            "inspiration_examples": examples,
            "replies": replies,
            "labels": labels,
            "note": merged_note,
            "provider_used": "mock",
        }

    if any(_is_unsafe_text(reply) for reply in replies):
        safe_replies, safe_labels, safe_note = _safe_redirect_replies(selected_tone)
        merged_note = _merge_notes(long_note, safe_note)
        _log_rag_event(
            stage="safety_redirect_output",
            conversation_text=work_text,
            tone=selected_tone,
            retrieved_ids=retrieved_ids,
            replies=safe_replies,
            note=merged_note,
        )
        return {
            "inspiration_examples": examples,
            "replies": safe_replies,
            "labels": safe_labels,
            "note": merged_note,
            "provider_used": provider_name,
        }

    rag_note = None
    if not examples:
        rag_note = "RAG note: no retrieved examples found, generated from base instructions."
    merged_note = _merge_notes(long_note, rag_note)
    _log_rag_event(
        stage="llm_generation",
        conversation_text=work_text,
        tone=selected_tone,
        retrieved_ids=retrieved_ids,
        replies=replies,
        note=merged_note,
    )

    return {
        "inspiration_examples": examples,
        "replies": replies,
        "labels": labels,
        "note": merged_note,
        "provider_used": provider_name,
    }
