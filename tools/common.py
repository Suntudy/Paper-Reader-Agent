"""Shared paths and utilities for all tools."""

from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
KNOWLEDGE_DIR.mkdir(exist_ok=True)
PAPERS_INDEX_PATH = KNOWLEDGE_DIR / "papers.json"
