"""Profile openers and bio generation (LLM with mock fallback)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from services.llm_service import generate_text, get_last_provider_name, pad_unique_replies

logger = logging.getLogger("rizzai.writing")

BIO_STYLE_GUIDE: dict[str, str] = {
    "witty_minimal": "Short, clever, curiosity-forward; avoid clichés; max ~2 short sentences unless facts demand slightly more.",
    "warm_story": "Warm, sincere, one concrete detail; approachable and human.",
    "bold_confident": "Confident and direct without arrogance; clear you are intentional, not pushy.",
    "playful": "Light humor, self-aware; no cringe pickup lines or try-hard jokes.",
    "authentic_soft": "Soft vulnerability, emotionally intelligent; no therapy-speak or humble-brag spam.",
}

_OPENER_ANGLES = (
    "callback — quote or riff on one specific profile line or interest",
    "curious question — ask about one concrete detail they listed",
    "playful tease — light joke tied to something they wrote",
    "warm observation — genuine reaction to a specific hobby or prompt answer",
    "direct invite — clear, low-pressure next step tied to their interests",
    "hypothesis — playful guess based on one profile detail",
)

_BIO_ANGLES = (
    "punchy hook — lead with their strongest specific detail from the notes",
    "mini-story — one short vignette built around a fact they gave",
    "contrast line — personality quirk + what they want (from their notes)",
    "warm direct — sincere line that names an interest or value they listed",
    "playful list — 2–3 real hobbies/facts from notes, light tone",
)

_GENERIC_BIO_MARKERS = (
    "partner in crime",
    "love to laugh",
    "here for a good time",
    "go with the flow",
    "don't be shy",
    "looking for my person",
    "good vibes only",
    "work hard play hard",
    "fluent in sarcasm",
    "adventure and tacos",
    "[your",
    "[interest]",
    "[detail]",
)

_GENERIC_OPENER_MARKERS = (
    "what are you up to",
    "how's your day",
    "you seem cool",
    "you seem nice",
    "tell me about yourself",
    "love your energy",
    "hey beautiful",
    "hey gorgeous",
    "your profile",
    "[one detail",
    "[interest]",
)

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "that",
        "with",
        "this",
        "from",
        "your",
        "you",
        "are",
        "was",
        "have",
        "about",
        "just",
        "like",
        "what",
        "when",
        "they",
        "them",
        "their",
        "looking",
        "someone",
        "who",
        "into",
        "here",
    }
)


def _parse_json_list(raw: str, key: str, *, max_items: int) -> list[str]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    if not text:
        return []
    try:
        data: Any = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get(key), list):
            items = [_clean_line(str(x)) for x in data[key] if str(x).strip()]
            return [x for x in items if x][:max_items]
    except json.JSONDecodeError:
        match = re.search(rf'\{{[\s\S]*"{key}"[\s\S]*\}}', text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data.get(key), list):
                    items = [_clean_line(str(x)) for x in data[key] if str(x).strip()]
                    return [x for x in items if x][:max_items]
            except json.JSONDecodeError:
                pass
    return []


def _clean_line(s: str) -> str:
    return re.sub(r"^[-*\d.)\s]+", "", s).strip().strip('"')


def _input_cues(text: str) -> list[str]:
    """Pull concrete hooks from user notes or profile text for grounding and validation."""
    cues: list[str] = []
    seen: set[str] = set()

    for line in re.split(r"[\n•]+", text):
        chunk = line.strip().strip("-").strip()
        if len(chunk) < 4:
            continue
        key = chunk.lower()
        if key in seen:
            continue
        seen.add(key)
        cues.append(chunk[:120])

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{3,}", text.lower())
    for w in words:
        if w in _STOPWORDS or w in seen:
            continue
        seen.add(w)
        cues.append(w)
        if len(cues) >= 10:
            break

    return cues[:10]


def _profile_cues(profile: str) -> list[str]:
    return _input_cues(profile)


def _input_tokens(text: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{3,}", text)
        if w.lower() not in _STOPWORDS
    }


def _profile_tokens(profile: str) -> set[str]:
    return _input_tokens(profile)


def _opener_uses_profile(opener: str, profile: str, cues: list[str]) -> bool:
    text = opener.lower()
    if any(marker in text for marker in _GENERIC_OPENER_MARKERS):
        return False
    prof_tokens = _profile_tokens(profile)
    opener_tokens = _profile_tokens(opener)
    if prof_tokens & opener_tokens:
        return True
    return any(cue.lower() in text for cue in cues if len(cue) >= 4)


def _grounded_opener_count(openers: list[str], profile: str, cues: list[str]) -> int:
    return sum(1 for o in openers if _opener_uses_profile(o, profile, cues))


def _is_generic_opener(opener: str) -> bool:
    t = opener.lower()
    return any(m in t for m in _GENERIC_OPENER_MARKERS)


def _mock_openers(profile: str, tone: str, n: int) -> list[str]:
    cues = _profile_cues(profile)
    c1 = cues[0] if cues else "that line in your bio"
    c2 = cues[1] if len(cues) > 1 else c1
    c3 = cues[2] if len(cues) > 2 else c1
    t = tone.lower()
    templates = [
        f"Okay the {c1} detail is doing a lot — what's the story there?",
        f"Low-key need to know more about {c2}. How did you get into that?",
        f"Your profile mentions {c1} — is that a recent thing or a lifelong obsession?",
        f"I have a {t} theory about people into {c2} — want me to test it?",
        f"Genuine question: what would you want someone to ask about {c3} first?",
        f"Not gonna lie, {c1} caught my eye. What's the best version of that lately?",
    ]
    out: list[str] = []
    for i in range(max(3, min(10, n))):
        out.append(templates[i % len(templates)])
    return pad_unique_replies(out, count=n)


def _finalize_openers(
    openers: list[str],
    profile: str,
    *,
    count: int,
    tone: str,
) -> list[str]:
    cues = _profile_cues(profile)
    cleaned = [_clean_line(o) for o in openers if o.strip() and not _is_generic_opener(o)]
    unique = pad_unique_replies(cleaned, count=count)
    if _grounded_opener_count(unique, profile, cues) < max(2, count // 2):
        return _mock_openers(profile, tone, count)
    return unique


def _build_opener_prompt(*, profile_description: str, tone: str, count: int) -> str:
    n = max(3, min(10, int(count)))
    cues = _profile_cues(profile_description)
    cues_block = "\n".join(f"  - {c}" for c in cues[:8]) if cues else "  - (use whatever specifics appear in the profile text)"
    angle_lines = "\n".join(
        f"  - Opener {i + 1}: {_OPENER_ANGLES[i % len(_OPENER_ANGLES)]}" for i in range(n)
    )
    return (
        "You are CharmAI, a dating conversation coach.\n\n"
        f"THEIR profile / prompts / facts (this is who you are messaging — read carefully):\n"
        f"{profile_description.strip()}\n\n"
        f"Profile hooks you should use (quote or reference at least one per opener):\n{cues_block}\n\n"
        f"User-selected tone ONLY (do not change): {tone}\n"
        f"(funny = witty/light tease | flirty = warm spark | confident = assured | direct = clear/honest)\n\n"
        "Task:\n"
        f"- Write exactly {n} distinct first messages (dating app openers or first texts).\n"
        "- EVERY opener must reference at least one specific detail from THEIR profile above "
        "(hobby, prompt answer, place, job, joke, pet, food, sport, quote, etc.).\n"
        "- Do NOT write generic openers that could apply to anyone.\n"
        "- Do NOT use placeholders like [interest] or [one detail] — use their actual words.\n"
        "- Natural texting voice; respectful; no manipulation; no 'hey beautiful'.\n"
        "- Vary structure across openers; no repeated opener pattern.\n"
        "Required angles (one per opener):\n"
        f"{angle_lines}\n\n"
        f'Return ONLY valid JSON: {{"openers":["...","..."]}} with exactly {n} strings. '
        "No markdown, no commentary."
    )


def generate_openers(*, profile_description: str, tone: str, count: int) -> tuple[list[str], str]:
    profile = profile_description.strip()
    selected_tone = (tone or "").strip().lower()
    if selected_tone not in {"funny", "flirty", "confident", "direct"}:
        raise ValueError("tone is required — choose funny, flirty, confident, or direct.")

    n = max(3, min(10, int(count)))
    prompt = _build_opener_prompt(profile_description=profile, tone=selected_tone, count=n)

    try:
        raw = generate_text(prompt, max_tokens=1200)
        items = _parse_json_list(raw, "openers", max_items=n)
        if items:
            finalized = _finalize_openers(items, profile, count=n, tone=selected_tone)
            if _grounded_opener_count(finalized, profile, _profile_cues(profile)) >= max(2, n // 2):
                return finalized[:n], get_last_provider_name()

            retry_prompt = (
                f"{prompt}\n\n"
                "RETRY — previous openers were too generic or ignored the profile. "
                f"Write exactly {n} openers. Each MUST name or riff on a specific detail from THEIR profile text. "
                "Forbidden: generic filler, placeholders, compliments with no profile hook."
            )
            retry_raw = generate_text(retry_prompt, max_tokens=1200)
            retry_items = _parse_json_list(retry_raw, "openers", max_items=n)
            if retry_items:
                return _finalize_openers(retry_items, profile, count=n, tone=selected_tone)[:n], get_last_provider_name()
    except Exception as exc:  # noqa: BLE001
        logger.info("[openers] LLM failed: %s", exc)

    return _mock_openers(profile, selected_tone, n), "mock"


def _is_generic_bio(bio: str) -> bool:
    t = bio.lower()
    return any(m in t for m in _GENERIC_BIO_MARKERS)


def _bio_uses_input(bio: str, about: str, cues: list[str]) -> bool:
    text = bio.lower()
    if _is_generic_bio(bio):
        return False
    about_tokens = _input_tokens(about)
    bio_tokens = _input_tokens(bio)
    if about_tokens & bio_tokens:
        return True
    return any(cue.lower() in text for cue in cues if len(cue) >= 4)


def _grounded_bio_count(bios: list[str], about: str, cues: list[str]) -> int:
    return sum(1 for b in bios if _bio_uses_input(b, about, cues))


def _dedupe_bios(bios: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for bio in bios:
        cleaned = bio.strip()
        if not cleaned:
            continue
        key = re.sub(r"\s+", " ", cleaned.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _mock_bios(about_text: str, style: str, n: int) -> list[str]:
    cues = _input_cues(about_text)
    c1 = cues[0] if cues else "what I actually do on weekends"
    c2 = cues[1] if len(cues) > 1 else c1
    c3 = cues[2] if len(cues) > 2 else c1
    style_l = style.lower()
    templates: dict[str, list[str]] = {
        "witty_minimal": [
            f"{c1} is my entire personality (no notes).\nLooking for someone who gets the bit.",
            f"Professional overthinker. Side quest: {c2}.\nWill trade good recs for better conversation.",
        ],
        "warm_story": [
            f"Still thinking about {c1} — it says a lot about me.\nHere for slow chats and real plans.",
            f"I care about {c2} more than I should admit.\nWarm energy, low drama, good coffee.",
        ],
        "bold_confident": [
            f"I do {c1} on purpose.\nIf that aligns with you, say hi — I prefer clear over vague.",
            f"Into {c2} and people who mean what they type.\nLet's skip small talk when it makes sense.",
        ],
        "playful": [
            f"Ranking: {c1}, {c2}, and finding someone who laughs at my bad jokes.",
            f"Certified fan of {c3}.\nBonus points if you have a take I haven't heard.",
        ],
        "authentic_soft": [
            f"{c1} matters to me — it's the honest version of who I am.\nLooking for kindness and curiosity.",
            f"Trying to be upfront: I love {c2}, I'm working on {c3}, and I like people who are real.",
        ],
    }
    pool = templates.get(style_l, templates["authentic_soft"])
    out: list[str] = []
    for i in range(max(1, min(5, n))):
        out.append(pool[i % len(pool)])
    return _dedupe_bios(out)[:n]


def _finalize_bios(
    bios: list[str],
    about: str,
    *,
    count: int,
    style: str,
) -> list[str]:
    cues = _input_cues(about)
    cleaned = [b for b in bios if b.strip() and not _is_generic_bio(b)]
    unique = _dedupe_bios(cleaned)
    if len(unique) < count:
        unique = _mock_bios(about, style, count)
    if _grounded_bio_count(unique, about, cues) < max(1, count // 2):
        return _mock_bios(about, style, count)[:count]
    return unique[:count]


def _build_bio_prompt(*, about_text: str, style_template: str, count: int) -> str:
    n = max(1, min(5, int(count)))
    guide = BIO_STYLE_GUIDE.get(style_template, BIO_STYLE_GUIDE["authentic_soft"])
    cues = _input_cues(about_text)
    cues_block = "\n".join(f"  - {c}" for c in cues[:8]) if cues else "  - (use specifics from the notes below)"
    angle_lines = "\n".join(
        f"  - Bio {i + 1}: {_BIO_ANGLES[i % len(_BIO_ANGLES)]}" for i in range(n)
    )
    return (
        "You are CharmAI, helping write dating app bios.\n\n"
        f"USER notes / facts / voice (this is the person writing their OWN bio — use their details):\n"
        f"{about_text.strip()}\n\n"
        f"Hooks from their notes (each bio must use at least one):\n{cues_block}\n\n"
        f"User-selected style ONLY (do not change): {style_template}\n"
        f"Style guide: {guide}\n\n"
        "Task:\n"
        f"- Produce exactly {n} complete bio variants they can paste into a dating profile.\n"
        "- EVERY bio must include at least one specific detail from THEIR notes above "
        "(job, hobby, city, food, humor, values, pets, music, goals, etc.).\n"
        "- Do NOT write generic bios that could fit anyone.\n"
        "- Do NOT use placeholders like [interest] or [your job] — use their actual words.\n"
        "- Each variant must differ in structure and opening hook.\n"
        "- No hashtags unless the user used them; no cringe; no explicit content.\n"
        "- Length: roughly 2–5 short lines per bio (line breaks OK).\n"
        "Required angles (one per bio):\n"
        f"{angle_lines}\n\n"
        f'Return ONLY valid JSON: {{"bios":["...","..."]}} with exactly {n} strings. '
        "No markdown, no commentary."
    )


def generate_bios(*, about_text: str, style_template: str, variant_count: int) -> tuple[list[str], str]:
    about = about_text.strip()
    style = (style_template or "").strip().lower()
    if style not in BIO_STYLE_GUIDE:
        raise ValueError(
            "style_template is required — choose witty_minimal, warm_story, bold_confident, playful, or authentic_soft."
        )

    n = max(1, min(5, int(variant_count)))
    prompt = _build_bio_prompt(about_text=about, style_template=style, count=n)

    try:
        raw = generate_text(prompt, max_tokens=1200)
        items = _parse_json_list(raw, "bios", max_items=n)
        if items:
            finalized = _finalize_bios(items, about, count=n, style=style)
            if _grounded_bio_count(finalized, about, _input_cues(about)) >= max(1, n // 2):
                return finalized[:n], get_last_provider_name()

            retry_prompt = (
                f"{prompt}\n\n"
                "RETRY — previous bios were too generic or ignored the user's notes. "
                f"Write exactly {n} bios. Each MUST include specific details from the notes above "
                "(interests, job, places, personality, goals). "
                "Forbidden: clichés, placeholders, bios that could apply to anyone."
            )
            retry_raw = generate_text(retry_prompt, max_tokens=1200)
            retry_items = _parse_json_list(retry_raw, "bios", max_items=n)
            if retry_items:
                return _finalize_bios(retry_items, about, count=n, style=style)[:n], get_last_provider_name()
    except Exception as exc:  # noqa: BLE001
        logger.info("[bio] LLM failed: %s", exc)

    return _mock_bios(about, style, n), "mock"
