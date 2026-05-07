"""RAG retrieval service for dating reply patterns."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from services.config import settings
from services.embeddings import get_embeddings

logger = logging.getLogger("rizzai.rag")

TONE_BOOST = 0.35
KEYWORD_BOOST = 0.15
INTENT_BOOST = 0.2
MIN_SAME_TONE = 3
MAX_CANDIDATES = 30


def _get_vector_store() -> Chroma:
    """Create a Chroma vector store client."""
    persist_dir = Path(settings.chroma_persist_dir)
    if not persist_dir.is_absolute():
        persist_dir = Path(__file__).resolve().parents[1] / persist_dir

    embeddings = get_embeddings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )


def _infer_keywords(conversation_text: str) -> tuple[list[str], str]:
    """Infer retrieval keywords and a high-level intent from user text."""
    text = conversation_text.lower()
    keywords: list[str] = []
    intent = "general_reply"

    dry_markers = ["ok", "k", "lol", "haha", "hmm", "idk", "maybe"]
    if any(re.search(rf"\b{re.escape(m)}\b", text) for m in dry_markers):
        keywords.extend(["dry reply", "low effort reply", "short response recovery"])
        intent = "dry_reply_recovery"

    if any(w in text for w in ["ask her out", "ask out", "meet", "date", "weekend plan"]):
        keywords.extend(["ask out", "date invitation", "confident planning"])
        if intent == "general_reply":
            intent = "ask_out"

    if any(w in text for w in ["playful", "tease", "banter"]):
        keywords.append("playful recovery")
    if not keywords:
        keywords.append("natural respectful dating reply")

    return keywords, intent


def _build_query(conversation_text: str, tone: str) -> tuple[str, str]:
    """Build richer retrieval query with inferred context."""
    keywords, inferred_intent = _infer_keywords(conversation_text)
    query = (
        f"Conversation: {conversation_text}\n"
        f"Selected tone: {tone}\n"
        f"Inferred intent: {inferred_intent}\n"
        f"Situation keywords: {', '.join(keywords)}"
    )
    return query, inferred_intent


def _doc_key(doc: Document) -> str:
    return str(doc.metadata.get("id") or doc.metadata.get("situation") or doc.page_content[:50])


def _metadata_keyword_hits(metadata: dict[str, Any], query: str) -> int:
    haystack = " ".join(
        [
            str(metadata.get("situation", "")),
            str(metadata.get("intent", "")),
            str(metadata.get("stage", "")),
        ]
    ).lower()
    tokens = [t for t in re.findall(r"[a-zA-Z]+", query.lower()) if len(t) > 2]
    return sum(1 for t in set(tokens) if t in haystack)


def _tone_quota_select(
    scored_items: list[dict[str, Any]],
    tone: str,
    k: int,
) -> list[dict[str, Any]]:
    """Select top-k while targeting at least 3 same-tone results when possible."""
    same_tone = [x for x in scored_items if x["tone"] == tone]
    other = [x for x in scored_items if x["tone"] != tone]

    selected: list[dict[str, Any]] = []
    target_same_tone = min(MIN_SAME_TONE, len(same_tone), k)

    selected.extend(same_tone[:target_same_tone])
    needed = k - len(selected)

    remaining_pool = same_tone[target_same_tone:] + other
    selected.extend(remaining_pool[:needed])
    return selected[:k]


def _format_results(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return clean retrieval payload including debug reasoning."""
    return [
        {
            "id": item["id"],
            "tone": item["tone"],
            "situation": item["situation"],
            "content": item["content"],
            "relevance_score": item["relevance_score"],
            "retrieval_debug": {
                "pattern_id": item["id"],
                "tone": item["tone"],
                "situation": item["situation"],
                "score": item["relevance_score"],
                "reason": item["reason"],
            },
        }
        for item in items
    ]


def retrieve_patterns(conversation_text: str, tone: str, k: int = 5) -> list[dict[str, Any]]:
    """
    Retrieve top-k relevant pattern examples from ChromaDB.

    Strategy:
    1) Build intent-aware query.
    2) Retrieve candidates using similarity + MMR.
    3) Apply tone-aware reranking and debug reasoning.
    4) Ensure at least 3 same-tone items in top 5 if available.
    """
    store = _get_vector_store()
    selected_tone = tone.lower().strip()
    query, inferred_intent = _build_query(conversation_text, selected_tone)

    # Dense candidates with scores (lower distance is better for Chroma).
    similarity_items = store.similarity_search_with_score(query=query, k=MAX_CANDIDATES)

    # MMR candidates reduce near-duplicate clusters.
    mmr_docs = store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": min(MAX_CANDIDATES, max(k * 3, 12)), "fetch_k": MAX_CANDIDATES},
    ).invoke(query)
    mmr_keys = {_doc_key(doc) for doc in mmr_docs}

    combined: dict[str, dict[str, Any]] = {}
    for doc, score in similarity_items:
        key = _doc_key(doc)
        tone_match = str(doc.metadata.get("tone", "")).lower() == selected_tone
        keyword_hits = _metadata_keyword_hits(doc.metadata, query)
        intent_match = str(doc.metadata.get("intent", "")).lower() == inferred_intent

        adjusted = float(score)
        reasons: list[str] = [f"base_distance={score:.4f}"]
        if tone_match:
            adjusted -= TONE_BOOST
            reasons.append(f"tone_boost=-{TONE_BOOST}")
        if key in mmr_keys:
            reasons.append("selected_by_mmr")
        if keyword_hits > 0:
            bonus = min(KEYWORD_BOOST, 0.03 * keyword_hits)
            adjusted -= bonus
            reasons.append(f"keyword_boost=-{bonus:.2f} ({keyword_hits} hits)")
        if intent_match:
            adjusted -= INTENT_BOOST
            reasons.append(f"intent_boost=-{INTENT_BOOST}")

        combined[key] = {
            "id": doc.metadata.get("id"),
            "tone": doc.metadata.get("tone"),
            "situation": doc.metadata.get("situation"),
            "content": doc.page_content,
            "relevance_score": round(adjusted, 4),
            "raw_score": float(score),
            "reason": "; ".join(reasons),
        }

    scored = sorted(combined.values(), key=lambda x: x["relevance_score"])
    final_items = _tone_quota_select(scored, selected_tone, k)
    results = _format_results(final_items)
    tone_hits = sum(1 for r in results if r.get("tone", "").lower() == selected_tone)
    logger.info(
        "[RAG] retrieved=%d patterns  tone_match=%d/%d  query=%r",
        len(results), tone_hits, len(results), query[:60],
    )
    return results
