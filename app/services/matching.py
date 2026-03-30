from rapidfuzz import fuzz

from app.models.document import Document
from app.schemas.document import MatchResult


def find_best_matches(query: str, documents: list[Document], threshold: float = 55.0) -> list[MatchResult]:
    results: list[MatchResult] = []
    for doc in documents:
        score = max(
            fuzz.token_set_ratio(query, doc.title),
            fuzz.partial_ratio(query, doc.content),
        )
        if score >= threshold:
            results.append(MatchResult(id=doc.id, title=doc.title, score=float(score)))
    return sorted(results, key=lambda item: item.score, reverse=True)
