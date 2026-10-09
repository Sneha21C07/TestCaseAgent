"""Simple in-memory index for requirement objects using token overlap retrieval."""
from typing import List, Dict
from collections import defaultdict
from .requirements_embeddings import tokenize, build_requirement_vectors, score_requirement


class RequirementsIndex:
    def __init__(self, reqs: List[Dict]):
        self.reqs = reqs
        build_requirement_vectors(self.reqs)
        self.index = defaultdict(set)
        for r in self.reqs:
            for t in r.get('tokens', set()):
                self.index[t].add(r['id'])

    def search(self, query: str, top_n: int = 5):
        # score by token overlap (Jaccard)
        scored = []
        for r in self.reqs:
            s = score_requirement(r, query)
            if s > 0:
                scored.append((s, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_n]]

    def related_requirements(self, req_id: str, top_n: int = 5):
        # Return requirements that share tokens with the given requirement
        base = None
        for r in self.reqs:
            if r['id'] == req_id:
                base = r
                break
        if base is None:
            return []
        candidates = []
        for r in self.reqs:
            if r['id'] == req_id:
                continue
            s = score_requirement(r, ' '.join(base.get('tokens', [])))
            if s > 0:
                candidates.append((s, r))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in candidates[:top_n]]
