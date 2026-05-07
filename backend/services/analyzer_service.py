"""Analyze dating conversation text into structured intent/mood insights."""

from __future__ import annotations

import json
import re
from typing import Any

from services.llm_service import generate_with_ollama, generate_with_openai

DEFAULT_ANALYSIS: dict[str, str] = {
    "mood": "dry",
    "intent": "continue chat",
    "interest_level": "medium",
    "suggested_tone": "playful",
}

ALLOWED_MOOD = {"playful", "dry", "interested", "confused"}
ALLOWED_INTENT = {"continue chat", "ask out", "recover", "flirt"}
ALLOWED_INTEREST = {"low", "medium", "high"}
ALLOWED_TONE = {"funny", "flirty", "confident", "direct", "sweet"}

_MAX_ANALYZE_CHARS = 3500


def _normalize_text(text: str) -> str:
    """Normalize whitespace and keep analysis input concise."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= _MAX_ANALYZE_CHARS:
        return t
    return f"{t[:600]} ... [middle omitted] ... {t[-2200:]}"


def _quick_rule_based_analysis(conversation_text: str) -> dict[str, str] | None:
    """Fast deterministic analysis for obvious short/simple patterns."""
    t = (conversation_text or "").strip().lower()
    if not t:
        return dict(DEFAULT_ANALYSIS)

    # If input is longer than 5 words, always use LLM path.
    if len(t.split()) > 5:
        return None

    # Keep rules narrow and explicit.
    if t in {"ok", "k", "hmm"}:
        return {
            "mood": "dry",
            "intent": "recover",
            "interest_level": "low",
            "suggested_tone": "playful",
        }

    if t in {"lol", "haha"}:
        return {
            "mood": "playful",
            "intent": "flirt",
            "interest_level": "medium",
            "suggested_tone": "funny",
        }

    if t in {"idk", "maybe"}:
        return {
            "mood": "confused",
            "intent": "recover",
            "interest_level": "low",
            "suggested_tone": "playful",
        }

    return None


def _attach_debug(
    result: dict[str, str],
    *,
    source: str,
    reason: str,
    enabled: bool,
) -> dict[str, str]:
    """Optionally add source/reason fields for debug mode."""
    out = dict(result)
    if enabled:
        out["source"] = source
        out["reason"] = reason
    return out


def _rule_reason(normalized: str) -> str:
    """Short debug reason for rule-based path."""
    t = normalized.strip().lower()
    if t in {"ok", "k", "hmm"}:
        return "pattern detected: dry short reply"
    if t in {"lol", "haha"}:
        return "pattern detected: playful short signal"
    if t in {"idk", "maybe"}:
        return "pattern detected: uncertain short signal"
    return "pattern detected"


def _build_analysis_prompt(conversation_text: str) -> str:
    """Prompt model for strict JSON analysis output only."""
    return (
        "You analyze dating conversation snippets.\n\n"
        "INTERNAL REASONING STEP (do this silently before writing JSON):\n"
        "Before classifying, ask yourself:\n"
        "  1. What is the emotional intent of this message?\n"
        "  2. Does the person show any of the following?\n"
        "       - desire to continue talking or meet again\n"
        "       - appreciation of a past interaction\n"
        "       - regret that a conversation or event ended\n"
        "       - enjoyment, warmth, or positive reflection\n"
        "  3. Based on that reasoning, what are the correct mood, intent,\n"
        "     interest level, and tone?\n"
        "DO NOT output this reasoning. Output final JSON only.\n\n"
        "CLASSIFICATION PRINCIPLE:\n"
        "Classification must be based on emotional meaning, not just keywords.\n"
        "If a message expresses wanting more time, enjoying a conversation, or\n"
        "positive reflection, it MUST NOT be classified as dry or low interest.\n\n"
        "Carefully read the text and infer emotional tone + intent from evidence in the text.\n"
        "Do not over-assume hidden context. Do not hallucinate missing details.\n\n"
        "CRITICAL RULES (DO NOT VIOLATE):\n"
        "- Messages expressing appreciation, enjoyment, or positive emotional experience\n"
        "  MUST NOT be classified as 'dry', 'low' interest, or purely 'playful'.\n"
        "- Such messages MUST be classified as:\n"
        "    mood: 'interested'\n"
        "    interest_level: at least 'medium'\n"
        "- Incorrect classification of positive/warm messages will be considered a failure.\n\n"
        "INTERPRETATION GUIDELINES:\n"
        "1. Messages that express wanting more time, wanting to continue, or regret about\n"
        "   the conversation ending are POSITIVE INTEREST signals. Treat them as interested.\n"
        "   Examples: 'wish we had more time', 'should have talked more',\n"
        "             'didn't want it to end', 'wish the night was longer'\n"
        "2. Soft hedging words ('kinda', 'wish', 'sorta', 'a little') do NOT reduce interest.\n"
        "   Focus on the UNDERLYING EMOTIONAL MEANING, not the softening word.\n"
        "   'kinda wish we talked more' = high interest, not low.\n"
        "3. Regret about an ending (conversation, date, event) = strong engagement signal.\n"
        "   Do NOT classify as dry or confused.\n"
        "4. Prioritize intent over literal wording:\n"
        "   Even if phrasing is indirect or humble, the emotional meaning is what matters.\n"
        "5. Output must reflect emotional meaning, not just surface keywords.\n\n"
        "Classification rules:\n"
        "1) Enjoyment, appreciation, affection, positive memory, or wanting more:\n"
        "   mood = interested | intent = flirt OR continue chat\n"
        "   interest_level = medium OR high | suggested_tone = flirty OR confident\n"
        "2) Short/low-effort (ok, k, hmm):\n"
        "   mood = dry\n"
        "3) Uncertainty (idk, maybe, not sure):\n"
        "   mood = confused\n"
        "4) Fun/light but not especially warm:\n"
        "   mood = playful\n\n"
        "Return STRICT JSON ONLY (no markdown, no explanation, no extra keys).\n\n"
        "Allowed values:\n"
        "- mood: playful | dry | interested | confused\n"
        "- intent: continue chat | ask out | recover | flirt\n"
        "- interest_level: low | medium | high\n"
        "- suggested_tone: funny | flirty | confident | direct | sweet\n\n"
        "Examples:\n"
        "Example A (warm/positive memory):\n"
        "Input: \"I had a really nice time talking to you yesterday\"\n"
        "Output: {\"mood\":\"interested\",\"intent\":\"flirt\",\"interest_level\":\"medium\",\"suggested_tone\":\"flirty\"}\n\n"
        "Example B (regret about ending — soft wording still = high interest):\n"
        "Input: \"I kinda wish we had more time to talk\"\n"
        "Output: {\"mood\":\"interested\",\"intent\":\"continue chat\",\"interest_level\":\"high\",\"suggested_tone\":\"flirty\"}\n\n"
        "Example C (wanting more — indirect phrasing = interested):\n"
        "Input: \"Should've talked more honestly\"\n"
        "Output: {\"mood\":\"interested\",\"intent\":\"continue chat\",\"interest_level\":\"medium\",\"suggested_tone\":\"confident\"}\n\n"
        "Example D (appreciation/enjoyment):\n"
        "Input: \"That conversation really made my day\"\n"
        "Output: {\"mood\":\"interested\",\"intent\":\"continue chat\",\"interest_level\":\"high\",\"suggested_tone\":\"confident\"}\n\n"
        "Example E (dry reply):\n"
        "Input: \"ok\"\n"
        "Output: {\"mood\":\"dry\",\"intent\":\"recover\",\"interest_level\":\"low\",\"suggested_tone\":\"playful\"}\n\n"
        "Example F (playful short):\n"
        "Input: \"lol\"\n"
        "Output: {\"mood\":\"playful\",\"intent\":\"continue chat\",\"interest_level\":\"medium\",\"suggested_tone\":\"funny\"}\n\n"
        "Example G (uncertain):\n"
        "Input: \"idk maybe\"\n"
        "Output: {\"mood\":\"confused\",\"intent\":\"recover\",\"interest_level\":\"low\",\"suggested_tone\":\"direct\"}\n\n"
        "Now classify this conversation:\n"
        f"{conversation_text}\n\n"
        "Output JSON schema:\n"
        '{'
        '"mood":"playful|dry|interested|confused",'
        '"intent":"continue chat|ask out|recover|flirt",'
        '"interest_level":"low|medium|high",'
        '"suggested_tone":"funny|flirty|confident|direct|sweet"'
        "}\n"
        "Output MUST be valid JSON only. No extra text outside the JSON object."
    )


# Phrases that unambiguously signal positive sentiment / warm engagement.
# If any appear in the conversation, LLM output is overridden to reflect real interest.
_POSITIVE_PHRASES: tuple[str, ...] = (
    # Direct positive experience
    "nice time",
    "enjoyed",
    "had a good time",
    "liked talking",
    "had fun",
    "great time",
    "loved talking",
    "loved chatting",
    "really liked",
    "made my day",
    "appreciate",
    "appreciated",
    # Wanting more / regret about ending (soft wording still = interest)
    "wish we had more time",
    "wish i had more time",
    "should've talked more",
    "should have talked more",
    "didn't want it to end",
    "did not want it to end",
    "wish the night was longer",
    "wish it was longer",
    "wanted to talk more",
    "could have talked longer",
    "wish we talked more",
    "didn't want to stop",
    "did not want to stop",
)

_INTEREST_RANK = {"low": 0, "medium": 1, "high": 2}


def _post_validate(
    result: dict[str, str],
    conversation_text: str,
    *,
    analysis_debug: bool,
) -> dict[str, str]:
    """
    Minimal guardrail — LLM stays in control.

    Only fires when a positive-sentiment phrase is detected AND the LLM made
    an obvious factual mistake on a specific field. Each field is corrected
    independently; unaffected fields are left exactly as the LLM returned them.

    Corrections applied:
    - mood "dry"       → "interested"   (dry is factually wrong for a warm message)
    - interest "low"   → "medium"       (floor, never raised above LLM's own value)
    - tone not warm    → "flirty"       (only if mood was also wrong; tone alone is
                                         not forced when LLM mood is already good)

    LLM intent is always preserved.
    """
    lowered = conversation_text.lower()
    matched_phrase = next((p for p in _POSITIVE_PHRASES if p in lowered), None)
    if matched_phrase is None:
        return result

    mood = result.get("mood", "")
    interest = result.get("interest_level", "")

    # Determine which fields are clearly wrong.
    mood_wrong = mood == "dry"                              # "playful" is borderline — leave it
    interest_wrong = _INTEREST_RANK.get(interest, 1) < 1   # strictly below "medium"

    if not mood_wrong and not interest_wrong:
        # LLM output already reasonable — no adjustment needed.
        return result

    corrected = dict(result)
    changed_fields: list[str] = []

    if mood_wrong:
        corrected["mood"] = "interested"
        changed_fields.append("mood")
        # Tone is only adjusted when mood was wrong AND tone is clearly cold.
        if corrected.get("suggested_tone") not in {"flirty", "confident", "sweet"}:
            corrected["suggested_tone"] = "flirty"
            changed_fields.append("suggested_tone")

    if interest_wrong:
        corrected["interest_level"] = "medium"
        changed_fields.append("interest_level")

    # Intent is never touched — LLM intent is always kept as-is.

    if analysis_debug:
        corrected["source"] = "llm+guardrail"
        corrected["reason"] = (
            f"Adjusted LLM output due to positive sentiment mismatch "
            f"('{matched_phrase}'); fields corrected: {', '.join(changed_fields)}"
        )

    return corrected


def _safe_parse(raw: str) -> dict[str, str]:
    """Parse/validate strict JSON. Fallback to defaults on any issue."""
    try:
        text = raw.strip()
        # If model wrapped extra text, try to recover first JSON object.
        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, flags=re.S)
            if match:
                text = match.group(0)
        parsed: Any = json.loads(text)
        if not isinstance(parsed, dict):
            return dict(DEFAULT_ANALYSIS)

        mood = str(parsed.get("mood", "")).strip().lower()
        intent = str(parsed.get("intent", "")).strip().lower()
        interest = str(parsed.get("interest_level", "")).strip().lower()
        tone = str(parsed.get("suggested_tone", "")).strip().lower()

        out = dict(DEFAULT_ANALYSIS)
        if mood in ALLOWED_MOOD:
            out["mood"] = mood
        if intent in ALLOWED_INTENT:
            out["intent"] = intent
        if interest in ALLOWED_INTEREST:
            out["interest_level"] = interest
        if tone in ALLOWED_TONE:
            out["suggested_tone"] = tone
        return out
    except Exception:  # noqa: BLE001
        return dict(DEFAULT_ANALYSIS)


def analyze_conversation(conversation_text: str, analysis_debug: bool = False) -> dict[str, str]:
    """
    Analyze chat mood/intent/interest/tone with provider fallback.

    Flow:
    1) Rule-based (narrow short patterns)
    2) OpenAI
    3) Ollama
    4) Safe defaults
    """
    normalized = _normalize_text(conversation_text)
    if not normalized:
        return _attach_debug(
            DEFAULT_ANALYSIS,
            source="llm",
            reason="LLM semantic analysis",
            enabled=analysis_debug,
        )
    quick = _quick_rule_based_analysis(normalized)
    if quick is not None:
        return _attach_debug(
            quick,
            source="rule-based",
            reason=_rule_reason(normalized),
            enabled=analysis_debug,
        )

    prompt = _build_analysis_prompt(normalized)

    try:
        raw = generate_with_openai(prompt)
        parsed = _safe_parse(raw)
        if parsed:
            result = _attach_debug(
                parsed,
                source="llm",
                reason="LLM semantic analysis",
                enabled=analysis_debug,
            )
            return _post_validate(result, normalized, analysis_debug=analysis_debug)
    except Exception:  # noqa: BLE001
        pass

    try:
        raw = generate_with_ollama(prompt)
        parsed = _safe_parse(raw)
        if parsed:
            result = _attach_debug(
                parsed,
                source="llm",
                reason="LLM semantic analysis",
                enabled=analysis_debug,
            )
            return _post_validate(result, normalized, analysis_debug=analysis_debug)
    except Exception:  # noqa: BLE001
        pass

    fallback = _attach_debug(
        DEFAULT_ANALYSIS,
        source="llm",
        reason="LLM semantic analysis",
        enabled=analysis_debug,
    )
    return _post_validate(fallback, normalized, analysis_debug=analysis_debug)

