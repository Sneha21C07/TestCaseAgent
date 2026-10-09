"""Lightweight embedding and tokenization utilities for requirements.

This module intentionally avoids external dependencies and uses simple token
sets and Jaccard similarity for semantic retrieval in the RAG layer.
"""
import re
from typing import List, Dict


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    toks = [t for t in text.split() if len(t) > 1]
    return toks


def build_requirement_vectors(reqs: List[Dict]) -> None:
    """Annotate each requirement dict with a `tokens` set for retrieval."""
    for r in reqs:
        txt = (r.get('title') or '') + ' ' + (r.get('raw') or '')
        r['tokens'] = set(tokenize(txt))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def score_requirement(req: Dict, query: str) -> float:
    qtokens = set(tokenize(query))
    return jaccard(req.get('tokens', set()), qtokens)
