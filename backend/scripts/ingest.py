"""Ingest reply patterns JSON into ChromaDB with LangChain."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from services.config import settings  # noqa: E402
from services.embeddings import get_embeddings  # noqa: E402


def load_patterns(file_path: Path) -> list[dict]:
    """Load pattern data from JSON."""
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("reply_patterns.json must contain a JSON array.")
    return data


def to_documents(items: list[dict]) -> list[Document]:
    """Convert raw pattern items to LangChain documents."""
    docs: list[Document] = []
    for item in items:
        intent = item.get("intent", "")
        stage = item.get("stage", "")
        difficulty = item.get("difficulty", "")
        content = (
            f"Situation: {item['situation']}\n"
            f"Tone: {item['tone']}\n"
            f"Intent: {intent}\n"
            f"Stage: {stage}\n"
            f"Difficulty: {difficulty}\n"
            f"Pattern: {item['pattern']}\n"
            f"Example Reply: {item['example_reply']}\n"
            f"Safety Note: {item['safety_note']}"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": item["id"],
                    "tone": item["tone"],
                    "situation": item["situation"],
                    "intent": intent,
                    "stage": stage,
                    "difficulty": difficulty,
                },
            )
        )
    return docs


def ingest(reset: bool = True) -> None:
    """Run the ingestion pipeline."""
    data_path = BACKEND_DIR / "data" / "reply_patterns.json"
    patterns = load_patterns(data_path)
    docs = to_documents(patterns)

    persist_dir = Path(settings.chroma_persist_dir)
    if not persist_dir.is_absolute():
        persist_dir = BACKEND_DIR / persist_dir

    if reset and persist_dir.exists():
        shutil.rmtree(persist_dir)

    embeddings = get_embeddings()

    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(persist_dir),
        collection_name=settings.chroma_collection,
    )

    print(
        f"Ingested {len(docs)} documents into '{settings.chroma_collection}' "
        f"at {persist_dir}."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest RAG reply patterns into Chroma.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Keep existing Chroma data and append new documents.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest(reset=not args.no_reset)
