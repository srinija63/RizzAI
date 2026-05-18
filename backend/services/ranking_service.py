"""Reply ranking service — scores and sorts generated replies by quality."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from services.llm_service import generate_text

logger = logging.getLogger("rizzai.ranking")

# ---------------------------------------------------------------------------
# Embedding similarity (lazy-loaded local model, no API key required)
# ---------------------------------------------------------------------------

# How many top replies to embed at most (keeps startup fast).
_EMBED_TOP_K = 10
# Cosine similarity above this → treat as semantic duplicate.
_COSINE_THRESHOLD = 0.85

_local_encoder: Optional[object] = None  # SentenceTransformer, loaded on first use


def _get_encoder():
    """Lazy-load the local sentence-transformer model (singleton)."""
    global _local_encoder
    if _local_encoder is None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            from services.config import settings  # noqa: PLC0415
            _local_encoder = SentenceTransformer(settings.local_embedding_model)
            logger.debug("ranking: loaded local encoder %s", settings.local_embedding_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ranking: could not load local encoder (%s); embedding check disabled", exc)
            _local_encoder = False  # sentinel — don't retry
    return _local_encoder if _local_encoder else None


def _embed_batch(texts: list[str]) -> list[list[float]] | None:
    """
    Encode a list of texts into normalised float vectors.

    Returns None if the encoder is unavailable (graceful degradation).
    """
    enc = _get_encoder()
    if enc is None:
        return None
    try:
        vecs = enc.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vecs.tolist()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ranking: embedding failed (%s); skipping cosine check", exc)
        return None


def _cosine(v1: list[float], v2: list[float]) -> float:
    """Cosine similarity for pre-normalised vectors (= dot product)."""
    return sum(a * b for a, b in zip(v1, v2))


def _build_embedding_index(
    sorted_scored: list[RankedReply],
    limit: int = _EMBED_TOP_K,
) -> dict[str, list[float]]:
    """
    Compute embeddings for the top `limit` replies and return a reply→vector map.
    Falls back to an empty dict if embeddings are unavailable.
    """
    top_texts = [item["reply"] for item in sorted_scored[:limit]]
    vectors = _embed_batch(top_texts)
    if vectors is None:
        return {}
    return {text: vec for text, vec in zip(top_texts, vectors)}


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

RankedReply = dict  # typed explicitly below via TypedDict-style comments:
# {
#   "reply":          str,
#   "score":          int,          # 1-10, average of four metrics
#   "metrics": {
#       "naturalness":    int,
#       "confidence":     int,
#       "tone_match":     int,
#       "respectfulness": int,
#   },
#   "explanation":    str,
# }

# ---------------------------------------------------------------------------
# LLM scoring
# ---------------------------------------------------------------------------

_TONE_DESCRIPTIONS: dict[str, str] = {
    "funny":     "humorous and light, makes her laugh",
    "flirty":    "playful with a hint of romantic tension",
    "confident": "calm, assured, not needy",
    "direct":    "clear and honest, no games",
    "sweet":     "warm, kind, genuine",
    "playful":   "fun and energetic, keeps things light",
}


def _build_ranking_prompt(replies: list[str], tone: str) -> str:
    tone_desc = _TONE_DESCRIPTIONS.get(tone.lower(), tone)
    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(replies))

    return (
        "You are a dating coach evaluating reply quality.\n\n"
        f"Selected tone: {tone} ({tone_desc})\n\n"
        "Replies to evaluate:\n"
        f"{numbered}\n\n"
        "For each reply, score it on these four metrics (1-10 each):\n"
        "- naturalness:    sounds like a real person, not robotic or try-hard\n"
        "- confidence:     not needy, not desperate, not over-apologetic\n"
        "- tone_match:     aligns with the selected tone\n"
        "- respectfulness: not pushy, no manipulation, no pressure\n\n"
        "Rules:\n"
        "- Be honest and discriminating — do not give every reply the same score.\n"
        "- explanation must be one short sentence, unique per reply.\n"
        "- final score = round(average of all four metrics).\n\n"
        "Return STRICT JSON ONLY — a JSON array, one object per reply, in the same order.\n"
        "Schema:\n"
        '[\n'
        '  {\n'
        '    "reply": "<exact reply text>",\n'
        '    "score": <int 1-10>,\n'
        '    "metrics": {\n'
        '      "naturalness": <int>,\n'
        '      "confidence": <int>,\n'
        '      "tone_match": <int>,\n'
        '      "respectfulness": <int>\n'
        '    },\n'
        '    "explanation": "<one sentence>"\n'
        '  }\n'
        ']\n'
        "No extra text outside the JSON array."
    )


def _parse_llm_scores(raw: str, replies: list[str]) -> list[RankedReply] | None:
    """Parse and validate LLM scoring output. Returns None on any issue."""
    text = (raw or "").strip()

    # Recover array if wrapped in extra text.
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, flags=re.S)
        if match:
            text = match.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list) or len(parsed) != len(replies):
        return None

    results: list[RankedReply] = []
    for item, original_reply in zip(parsed, replies):
        if not isinstance(item, dict):
            return None
        metrics = item.get("metrics", {})
        if not isinstance(metrics, dict):
            return None

        nat  = _clamp(metrics.get("naturalness",    5))
        conf = _clamp(metrics.get("confidence",     5))
        tone = _clamp(metrics.get("tone_match",     5))
        resp = _clamp(metrics.get("respectfulness", 5))
        avg  = round((nat + conf + tone + resp) / 4)

        results.append({
            "reply": original_reply,
            "score": _clamp(item.get("score", avg)),
            "metrics": {
                "naturalness":    nat,
                "confidence":     conf,
                "tone_match":     tone,
                "respectfulness": resp,
            },
            "explanation": str(item.get("explanation", "")).strip() or "No explanation provided.",
        })

    return results


# ---------------------------------------------------------------------------
# Heuristic fallback scorer
# ---------------------------------------------------------------------------

_NEEDY_PATTERNS = re.compile(
    r"\b(please|sorry|just wondering|if that.s ok|i don.t know|maybe i|"
    r"i hope that.s|not sure if|you probably|desperate|begging)\b",
    flags=re.I,
)

_PUSHY_PATTERNS = re.compile(
    r"\b(you have to|you need to|you must|you should|come on|stop ignoring|"
    r"why won.t you|i.m serious|be honest with me|just tell me)\b",
    flags=re.I,
)

# Cringe / pedestalising phrases that read as try-hard.
_CRINGE_PHRASES = re.compile(
    r"\b(queen|goddess|perfect girl|you.re perfect|absolutely perfect|"
    r"literal angel|you.re an angel|ethereal|you.re flawless|flawless|"
    r"you complete me|you.re everything|my everything|"
    r"most beautiful|most amazing|most incredible|"
    r"like no one i.ve ever|unlike anyone|one in a million|"
    r"you.re out of my league|way out of my league)\b",
    flags=re.I,
)

# Overly effusive adjectives — penalise when ≥ 3 appear in one reply.
_FLOWERY_ADJECTIVES = re.compile(
    r"\b(amazing|incredible|stunning|breathtaking|extraordinary|"
    r"phenomenal|magnificent|spectacular|unbelievable|insanely|"
    r"absolutely gorgeous|drop-dead|ravishing|mesmerising|mesmerizing|"
    r"jaw-dropping|mind-blowing|otherworldly|indescribable)\b",
    flags=re.I,
)

# Overly long replies (word count threshold for try-hard check).
_TRYHARD_LENGTH = 58

# Max word count for a reply to qualify as "purely grounded" (short + simple).
_GROUNDED_MAX_WORDS = 14

# Simple, grounded appreciation indicators — genuine but not exaggerated.
_GROUNDED_SIGNALS = re.compile(
    # Optional modifier word (really, so, pretty, actually, genuinely, etc.)
    # is allowed between "you're/you seem" and the adjective.
    r"\b("
    r"you seem(?:\s+\w+)?\s*(cool|fun|nice|interesting|thoughtful|smart|"
    r"different|real|genuine|chill|down to earth)|"
    r"you'?re(?:\s+\w+)?\s*(cool|fun|nice|interesting|thoughtful|smart|"
    r"different|real|genuine|chill|down to earth)|"
    r"i like your (vibe|energy|style|humor|humour|personality)|"
    r"something about you|you'?ve got (good|great|a nice)|"
    r"i appreciate|i respect|that'?s (cool|nice|real|honest|solid)|"
    r"genuinely (interesting|cool|fun|nice)"
    r")\b",
    flags=re.I,
)


def _is_grounded_appreciation(reply: str) -> bool:
    """
    Return True when a reply is simple, genuine appreciation — not exaggerated.

    A reply is considered grounded when ALL of the following hold:
    - It matches at least one grounded signal (natural phrasing)
    - It has fewer than _GROUNDED_MAX_WORDS words (short = less room for excess)
    - It contains ZERO flowery/effusive adjectives
    - It contains NO explicitly pedestalising phrases

    Grounded replies should not be penalised even if a surface pattern
    (like a long reply) would otherwise trigger a flag.
    """
    if not _GROUNDED_SIGNALS.search(reply):
        return False
    if len(reply.split()) >= _GROUNDED_MAX_WORDS:
        return False
    if _FLOWERY_ADJECTIVES.search(reply):
        return False
    if _CRINGE_PHRASES.search(reply):
        return False
    return True


def _try_hard_flags(reply: str) -> list[str]:
    """
    Return a list of detected try-hard signals (empty = none detected).

    Semantic guard: if the reply is a simple, grounded appreciation,
    the cringe check is skipped entirely — only adjective overload and
    excessive length can still fire (both require more than short phrasing).

    Checks:
    - cringe / pedestalising phrases  (skipped for grounded replies)
    - adjective overload (≥ 3 flowery adjectives)
    - excessive length (> _TRYHARD_LENGTH words)
    """
    grounded = _is_grounded_appreciation(reply)
    flags: list[str] = []

    # Cringe check — bypass completely for grounded, genuine appreciation.
    if not grounded and _CRINGE_PHRASES.search(reply):
        flags.append("cringe phrasing")

    if len(_FLOWERY_ADJECTIVES.findall(reply)) >= 3:
        flags.append("adjective overload")

    if len(reply.split()) > _TRYHARD_LENGTH:
        flags.append("too long")

    return flags

_TONE_KEYWORDS: dict[str, list[str]] = {
    "funny":     ["haha", "lol", "joke", "laugh", "funny", "😂", "classic", "honestly"],
    "flirty":    ["😏", "honestly", "curious", "wonder", "interesting", "subtle", "maybe"],
    "confident": ["clear", "know", "definitely", "straight", "honest", "real", "lets"],
    "direct":    ["lets", "tell", "know", "straight", "honest", "question", "actually"],
    "sweet":     ["love", "sweet", "care", "warm", "genuinely", "appreciate", "kind"],
    "playful":   ["haha", "fun", "game", "silly", "bet", "challenge", "playful", "vibe"],
}


def _clamp(val: object, lo: int = 1, hi: int = 10) -> int:
    """Clamp to [lo, hi]. Accepts int or float — floats are rounded normally."""
    try:
        return max(lo, min(hi, round(float(val))))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 5


def _heuristic_score(reply: str, tone: str) -> RankedReply:
    """Score a single reply using lightweight text heuristics."""
    words = reply.split()
    word_count = len(words)

    # Naturalness: reward concise texting but allow longer grounded replies.
    if word_count < 3:
        nat = 3
    elif word_count <= 18:
        nat = 8
    elif word_count <= 40:
        nat = 7
    elif word_count <= 52:
        nat = 6
    else:
        nat = 4

    # Confidence: penalise needy/apologetic patterns.
    needy_hits = len(_NEEDY_PATTERNS.findall(reply))
    conf = max(1, 8 - needy_hits * 3)

    # Tone match: keyword presence.
    keywords = _TONE_KEYWORDS.get(tone.lower(), [])
    hits = sum(1 for kw in keywords if kw.lower() in reply.lower())
    tone_score = min(10, 5 + hits * 2)

    # Respectfulness: penalise pushy language.
    pushy_hits = len(_PUSHY_PATTERNS.findall(reply))
    resp = max(1, 9 - pushy_hits * 4)

    # Try-hard / unnatural penalty — severity scales with number of signals.
    tryhard = _try_hard_flags(reply)
    if tryhard:
        n = len(tryhard)
        if n == 1:
            nat_pen, conf_pen = 1.0, 0.5
        elif n == 2:
            nat_pen, conf_pen = 2.0, 1.0
        else:                           # 3+
            nat_pen, conf_pen = 3.0, 2.0
        nat  = _clamp(nat  - nat_pen)
        conf = _clamp(conf - conf_pen)

    # Brevity bonus: short, clean, unflagged reply gets a small naturalness boost.
    _natural_tone = not needy_hits and not pushy_hits
    _brevity_bonus = (
        not tryhard
        and word_count <= 22
        and word_count >= 4      # avoid rewarding near-empty replies
        and _natural_tone
    )
    if _brevity_bonus:
        nat  = _clamp(nat  + 1.0)
        conf = _clamp(conf + 0.5)

    avg = round((nat + conf + tone_score + resp) / 4)

    # Build a short, specific human-readable explanation.

    # Try-hard explanation: pick the most specific message for the dominant flag.
    def _tryhard_explanation(flags: list[str]) -> str:
        if "cringe phrasing" in flags and "adjective overload" in flags:
            return "Overly flattering language reduces authenticity."
        if "cringe phrasing" in flags:
            return "Overly flattering language reduces authenticity."
        if "adjective overload" in flags:
            return "Feels slightly forced rather than natural."
        if "too long" in flags:
            return "Too long, loses conversational feel."
        return "Feels slightly forced rather than natural."

    issues: list[str] = []
    if not tryhard and word_count > 55:
        issues.append("too long, loses conversational feel")
    if needy_hits:
        issues.append("slightly needy phrasing")
    if pushy_hits:
        issues.append("pushy or pressuring tone")
    if hits == 0:
        issues.append(f"weak {tone} signal")

    # Separate hard issues (needy/pushy/long) from the soft tone-match note.
    # Brevity bonus can coexist with a weak-tone note — the bonus wins for explanation.
    _hard_issues = [i for i in issues if not i.startswith(f"weak {tone}")]

    if tryhard:
        base = _tryhard_explanation(tryhard)
        extra = [i for i in issues if i not in ("too long, loses conversational feel",)]
        explanation = base[:-1] + ("; " + ", ".join(extra) + "." if extra else ".")
    elif _hard_issues:
        lead = _hard_issues[0].capitalize()
        rest = _hard_issues[1:]
        explanation = lead + ("" if not rest else "; " + ", ".join(rest)) + "."
    elif _brevity_bonus:
        explanation = "Feels natural and easygoing."
    elif issues:
        # Only soft notes remain (weak tone signal).
        lead = issues[0].capitalize()
        explanation = lead + "."
    elif avg >= 8:
        explanation = "Short, confident, and on-tone."
    else:
        explanation = "Decent reply with room to improve."

    return {
        "reply": reply,
        "score": avg,
        "metrics": {
            "naturalness":    nat,
            "confidence":     conf,
            "tone_match":     tone_score,
            "respectfulness": resp,
        },
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Diversity enforcement
# ---------------------------------------------------------------------------

# Replies whose token overlap exceeds this threshold are considered too similar.
_SIMILARITY_THRESHOLD = 0.60


def _token_set(text: str) -> set[str]:
    """Lowercase word tokens, stripped of punctuation."""
    return set(re.sub(r"[^\w\s]", "", text.lower()).split())


def _jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two reply strings (0.0 – 1.0)."""
    sa, sb = _token_set(a), _token_set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def _enforce_diversity(
    sorted_scored: list[RankedReply],
    top_n: int = 5,
    jaccard_threshold: float = _SIMILARITY_THRESHOLD,
    cosine_threshold: float = _COSINE_THRESHOLD,
) -> list[RankedReply]:
    """
    Select up to `top_n` replies that are mutually dissimilar.

    A candidate is rejected if it is too similar to any already-accepted reply
    by either measure:
        - Jaccard token-overlap  >= jaccard_threshold (0.60)  — catches lexical dupes
        - Cosine embedding sim   >= cosine_threshold  (0.85)  — catches semantic dupes

    Embeddings are only computed for the top _EMBED_TOP_K replies; replies
    outside that window fall back to Jaccard-only checking.  If the embedding
    model is unavailable the cosine check is silently skipped.

    The list is already sorted score-descending, so "keep the higher-scored
    version" is guaranteed by construction.
    """
    # Pre-compute embeddings once for the top slice.
    emb_index = _build_embedding_index(sorted_scored)
    if emb_index:
        logger.debug("ranking diversity: embeddings available for %d replies", len(emb_index))
    else:
        logger.debug("ranking diversity: embedding index empty, using Jaccard only")

    accepted: list[RankedReply] = []

    for candidate in sorted_scored:
        if len(accepted) >= top_n:
            break

        reply = candidate["reply"]
        drop_reason: str | None = None

        for kept in accepted:
            kept_reply = kept["reply"]

            # --- Jaccard check (always runs) ---
            if _jaccard(reply, kept_reply) >= jaccard_threshold:
                drop_reason = f"Jaccard={_jaccard(reply, kept_reply):.2f} >= {jaccard_threshold}"
                break

            # --- Cosine check (only when both replies have embeddings) ---
            v_candidate = emb_index.get(reply)
            v_kept = emb_index.get(kept_reply)
            if v_candidate and v_kept:
                sim = _cosine(v_candidate, v_kept)
                if sim >= cosine_threshold:
                    drop_reason = f"cosine={sim:.2f} >= {cosine_threshold}"
                    break

        if drop_reason:
            logger.debug("ranking diversity: dropped %r (%s)", reply[:40], drop_reason)
        else:
            accepted.append(candidate)
            logger.debug(
                "ranking diversity: accepted %r (slot %d/%d)",
                reply[:40],
                len(accepted),
                top_n,
            )

    if len(accepted) < top_n:
        seen_text = {item["reply"].strip().lower() for item in accepted}
        for candidate in sorted_scored:
            if len(accepted) >= top_n:
                break
            text_key = candidate["reply"].strip().lower()
            if text_key and text_key not in seen_text:
                accepted.append(candidate)
                seen_text.add(text_key)

    return accepted[:top_n]


# ---------------------------------------------------------------------------
# Intent-aware score adjustment
# ---------------------------------------------------------------------------

# Signals that a reply is confident (decisive, assertive, not hedging).
_CONFIDENT_SIGNALS = re.compile(
    r"\b(let'?s|let us|definitely|absolutely|honestly|clearly|"
    r"straight up|for sure|no doubt|i know|i'?m sure|trust me|"
    r"tell you what|here'?s the thing)\b",
    flags=re.I,
)

# Signals that a reply is vague / non-committal.
_VAGUE_SIGNALS = re.compile(
    r"\b(maybe|perhaps|kind of|kinda|sort of|sorta|i guess|"
    r"i think|not sure|might|could be|possibly|if you want|"
    r"whenever you'?re ready|no pressure|up to you)\b",
    flags=re.I,
)

# Signals that a reply is light / playful (good for recovery).
_LIGHT_SIGNALS = re.compile(
    r"\b(haha|lol|ha|funny|laugh|joke|play|fun|silly|bet|"
    r"honestly though|fair enough|classic|well well)\b",
    flags=re.I,
)

# Signals that a reply is intense / overly serious (bad for recovery).
_INTENSE_SIGNALS = re.compile(
    r"\b(we need to|i need you to|you should|you must|be honest|"
    r"seriously|i'?m serious|let'?s be real|the truth is|"
    r"i have to say|i'?ve been thinking)\b",
    flags=re.I,
)

# Signals that a reply is smooth / subtly bold (good for flirt).
_SMOOTH_SIGNALS = re.compile(
    r"\b(curious|intriguing|interesting|honestly|"
    r"something about you|can'?t help|i notice|"
    r"not gonna lie|ngl|lowkey|bold of|dare i say)\b",
    flags=re.I,
)

# How much to nudge the score in each direction.
_NUDGE_CONFIRMED = 1.0   # rule confirmed by LLM
_NUDGE_DISPUTED  = 0.5   # rule fired but LLM disagrees → soften

# Maps intent → (classifications LLM should use, description for prompt)
_INTENT_CLASS_SCHEMA: dict[str, tuple[list[str], str]] = {
    "ask out": (
        ["confident", "vague", "neutral"],
        "confident = decisive / proposes something clearly, "
        "vague = hedges / avoids commitment even if wording is unfamiliar, "
        "neutral = neither",
    ),
    "recover": (
        ["light", "intense", "neutral"],
        "light = playful / breezy / defuses tension, "
        "intense = serious / heavy / emotionally demanding, "
        "neutral = neither",
    ),
    "flirt": (
        ["smooth", "neutral"],
        "smooth = subtly bold / intriguing / has quiet confidence, "
        "neutral = ordinary / no flirty pull",
    ),
}


def _build_classify_prompt(replies: list[str], intent: str) -> str:
    schema = _INTENT_CLASS_SCHEMA.get(intent.lower())
    if not schema:
        return ""
    classes, description = schema
    numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(replies))
    return (
        f"Conversation intent: {intent}\n\n"
        f"Classify each reply as one of: {' | '.join(classes)}\n"
        f"Definitions: {description}\n\n"
        "Focus on MEANING, not surface keywords — the same idea can be expressed many ways.\n\n"
        f"Replies:\n{numbered}\n\n"
        f"Return a JSON array of exactly {len(replies)} strings, one classification per reply, "
        "in the same order. No extra text outside the JSON array.\n"
        f'Example for {len(replies)} replies: {json.dumps([classes[0]] * len(replies))}'
    )


def _parse_classifications(raw: str, n: int, valid: list[str]) -> list[str] | None:
    """Parse and validate the LLM classification array."""
    text = (raw or "").strip()
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, flags=re.S)
        if match:
            text = match.group(0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != n:
        return None
    result = [str(x).strip().lower() for x in parsed]
    if not all(r in valid for r in result):
        return None
    return result


def _llm_semantic_classify(
    replies: list[str],
    intent: str,
) -> list[str] | None:
    """
    Ask the LLM to classify each reply's character for the given intent.

    Uses Gemini → Ollama fallback.  Returns None if unavailable or parsing fails,
    so callers can gracefully fall back to rule-only scoring.
    """
    schema = _INTENT_CLASS_SCHEMA.get(intent.lower())
    if not schema:
        return None

    valid_classes = schema[0]
    prompt = _build_classify_prompt(replies, intent)
    if not prompt:
        return None

    try:
        raw = generate_text(prompt, max_tokens=500)
        result = _parse_classifications(raw, len(replies), valid_classes)
        if result:
            logger.debug("ranking semantic: classified %d replies via LLM", len(result))
            return result
    except Exception:  # noqa: BLE001
        pass

    logger.debug("ranking semantic: LLM unavailable, skipping semantic check")
    return None


def _intent_adjustment(reply: str, intent: str) -> tuple[int, str | None]:
    """
    Rule-based check: return (delta, reason) for a reply given conversation intent.

    delta  : +1, -1, or 0  (float multiplication happens in _apply_intent_adjustments)
    reason : short string appended to explanation when non-zero, else None
    """
    intent = (intent or "").strip().lower()

    if intent == "ask out":
        if _CONFIDENT_SIGNALS.search(reply):
            return +1, "confident tone suits ask-out intent"
        if _VAGUE_SIGNALS.search(reply):
            return -1, "vague phrasing weakens ask-out intent"

    elif intent == "recover":
        if _LIGHT_SIGNALS.search(reply):
            return +1, "playful tone suits recovery"
        if _INTENSE_SIGNALS.search(reply):
            return -1, "intense tone is too heavy for recovery"

    elif intent == "flirt":
        if _SMOOTH_SIGNALS.search(reply):
            return +1, "smooth and bold — good for flirting"

    # "continue chat" and unknown intents → no adjustment
    return 0, None


def _apply_intent_adjustments(
    scored: list[RankedReply],
    intent: str,
) -> list[RankedReply]:
    """
    Nudge each reply's score by ±1.0 (rule confirmed) or ±0.5 (rule disputed by LLM).

    Flow per reply:
    1. Rule-based check fires first (primary signal).
    2. LLM semantic check is run once as a batch for all replies that had a non-zero delta.
    3. If LLM agrees with the rule   → keep full  ±1.0 nudge.
       If LLM disagrees or is absent → soften to  ±0.5 nudge.
    4. Float delta is rounded via _clamp (round-half-even) into the final int score.

    Rules stay primary; LLM is a refinement layer only.
    """
    if not intent or intent.lower() in {"", "continue chat"}:
        return scored

    # Step 1 — compute rule-based deltas for every reply.
    rule_results: list[tuple[float, str | None]] = []
    needs_llm: list[int] = []  # indices where delta != 0
    for idx, item in enumerate(scored):
        delta, reason = _intent_adjustment(item["reply"], intent)
        rule_results.append((float(delta), reason))
        if delta != 0:
            needs_llm.append(idx)

    # Step 2 — run ONE batched LLM call for replies that the rules flagged.
    llm_classes: dict[int, str] = {}
    if needs_llm:
        flagged_replies = [scored[i]["reply"] for i in needs_llm]
        classifications = _llm_semantic_classify(flagged_replies, intent)
        if classifications:
            llm_classes = dict(zip(needs_llm, classifications))

    # Step 3 — confirm or soften each delta.
    def _confirm(idx: int, delta: float) -> float:
        """Return full or softened delta based on LLM agreement."""
        cls = llm_classes.get(idx)
        if cls is None:
            # LLM unavailable — keep rule delta as-is (rules are primary).
            return delta

        intent_lower = intent.lower()
        # Map intent + rule direction → expected LLM class for confirmation.
        confirms = {
            ("ask out", +1.0): "confident",
            ("ask out", -1.0): "vague",
            ("recover", +1.0): "light",
            ("recover", -1.0): "intense",
            ("flirt",   +1.0): "smooth",
        }.get((intent_lower, delta), None)

        if confirms and cls == confirms:
            logger.debug("ranking semantic: LLM CONFIRMS rule for idx=%d (%s)", idx, cls)
            return delta                   # full ±1.0
        else:
            logger.debug(
                "ranking semantic: LLM DISPUTES rule for idx=%d (rule=%+.1f, llm=%s)",
                idx, delta, cls,
            )
            return delta * 0.5             # soften to ±0.5

    adjusted: list[RankedReply] = []
    for idx, (item, (raw_delta, reason)) in enumerate(zip(scored, rule_results)):
        if raw_delta == 0:
            adjusted.append(item)
            continue

        final_delta = _confirm(idx, raw_delta)
        new_item = dict(item)
        new_item["metrics"] = dict(item["metrics"])
        new_item["score"] = _clamp(item["score"] + final_delta)

        # Append reason + confirmation note to explanation.
        if reason:
            confirmed = abs(final_delta) >= 1.0
            qualifier = "" if confirmed else " (softened by semantic check)"
            sep = " — " if not item["explanation"].endswith(".") else " "
            new_item["explanation"] = (
                item["explanation"].rstrip(".") + sep + reason + qualifier + "."
            )

        logger.debug(
            "ranking intent(%s): raw=%+.1f final=%+.1f on %r",
            intent, raw_delta, final_delta, item["reply"][:40],
        )
        adjusted.append(new_item)

    return adjusted


# ---------------------------------------------------------------------------
# Deduplication of explanations
# ---------------------------------------------------------------------------

def _dedupe_explanations(ranked: list[RankedReply]) -> list[RankedReply]:
    """Ensure no two explanations are identical."""
    seen: dict[str, int] = {}
    for item in ranked:
        expl = item["explanation"]
        if expl in seen:
            seen[expl] += 1
            item["explanation"] = f"{expl} (variant {seen[expl]})"
        else:
            seen[expl] = 1
    return ranked


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rank_replies(
    replies: list[str],
    tone: str,
    intent: str = "",
    top_n: int = 5,
) -> list[RankedReply]:
    """
    Score, adjust for intent, diversify, and sort replies.

    Flow:
    1. Score all replies (Gemini → Ollama → heuristic fallback)
    2. Apply intent-aware ±1 nudges
    3. Sort by adjusted score descending
    4. Enforce diversity: drop near-duplicates, keep the higher-scored version
    5. Deduplicate explanations

    Args:
        replies: List of generated reply strings.
        tone:    Selected tone (funny / flirty / confident / direct / sweet / playful).
        intent:  Conversation intent from analyzer (ask out / recover / flirt /
                 continue chat). Optional — pass "" to skip adjustment.
        top_n:   Maximum number of replies to return (default 5).

    Returns:
        List of up to `top_n` RankedReply dicts, sorted by adjusted score descending,
        with near-duplicate replies removed.
    """
    if not replies:
        return []

    prompt = _build_ranking_prompt(replies, tone)
    scored: list[RankedReply] | None = None

    if scored is None:
        try:
            raw = generate_text(prompt, max_tokens=700)
            scored = _parse_llm_scores(raw, replies)
            if scored:
                logger.info("ranking: scored %d replies via LLM", len(scored))
        except Exception:  # noqa: BLE001
            pass

    # --- Heuristic fallback ---
    if scored is None:
        logger.info("ranking: using heuristic fallback scorer")
        scored = [_heuristic_score(r, tone) for r in replies]

    # --- Intent-aware adjustment (before sort, so ordering reflects intent) ---
    if intent:
        scored = _apply_intent_adjustments(scored, intent)
        logger.info("ranking: applied intent adjustments for intent=%r", intent)

    scored.sort(key=lambda x: x["score"], reverse=True)
    diverse = _enforce_diversity(scored, top_n=top_n)
    logger.info(
        "ranking: %d/%d replies kept after diversity enforcement",
        len(diverse), len(scored),
    )
    return _dedupe_explanations(diverse)
