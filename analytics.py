"""
analytics.py
------------
Métriques quantifiées pour ClarIA :

  - Score de confiance par réponse, calculé à partir des scores de
    pertinence des extraits utilisés (cosinus / BM25 / hybride).
  - Historique de requêtes quantifié (QueryLogEntry) : une entrée par
    question posée, avec confiance, documents cités, temps de réponse et
    estimation de tokens consommés.
  - Agrégation de statistiques d'usage (taux de réponses sourcées,
    documents les plus consultés, temps de réponse moyen, etc.), pensées
    pour un usage en entreprise (tableau de bord, export CSV/Excel).

Ce module est indépendant de Streamlit : testable et réutilisable tel quel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple

if TYPE_CHECKING:
    from rag_core import Chunk

# Phrase exacte imposée par le prompt système (voir rag_core.SYSTEM_PROMPT)
# quand l'information n'est pas dans les documents. Sert à détecter si une
# réponse est "sourcée" ou non pour les statistiques d'usage.
NO_INFO_PHRASE = "Je ne trouve pas cette information dans les documents fournis."

# Seuils (score_fort, score_moyen) au-delà desquels une réponse est jugée de
# confiance "Forte" / "Moyenne" ; en dessous du second seuil : "Faible".
# Les scores BM25 (mode "keyword") ne sont pas bornés dans [0, 1] comme la
# similarité cosinus : ils utilisent donc des seuils différents.
CONFIDENCE_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "hybrid": (0.55, 0.30),
    "semantic": (0.55, 0.30),
    "keyword": (5.0, 1.0),
}

CONFIDENCE_LABELS = ("Fort", "Moyen", "Faible", "Aucune source")


def confidence_from_score(score: float, mode: str = "hybrid") -> dict:
    """Traduit un score de recherche brut en niveau de confiance lisible."""
    strong_threshold, medium_threshold = CONFIDENCE_THRESHOLDS.get(
        mode, CONFIDENCE_THRESHOLDS["hybrid"]
    )
    if score >= strong_threshold:
        label = "Fort"
    elif score >= medium_threshold:
        label = "Moyen"
    else:
        label = "Faible"
    return {"score": round(float(score), 3), "label": label}


def compute_answer_confidence(
    retrieved: Sequence[Tuple["Chunk", float]], mode: str = "hybrid"
) -> dict:
    """Calcule un score de confiance global pour une réponse à partir des
    scores des extraits utilisés : combinaison du meilleur score (70%) et
    de la moyenne des scores (30%), pour lisser le cas d'un seul très bon
    extrait noyé parmi des extraits moins pertinents."""
    if not retrieved:
        return {"score": 0.0, "label": "Aucune source"}
    scores = [score for _, score in retrieved]
    best = max(scores)
    average = sum(scores) / len(scores)
    combined = 0.7 * best + 0.3 * average
    return confidence_from_score(combined, mode)


def estimate_tokens(text: str) -> int:
    """Estimation grossière du nombre de tokens (environ 4 caractères par
    token en moyenne pour du texte français/anglais). Purement indicative :
    Groq étant gratuit, il ne s'agit pas d'une estimation de coût mais d'un
    indicateur de volume d'usage de l'API."""
    if not text:
        return 0
    return max(1, round(len(text) / 4))


@dataclass
class QueryLogEntry:
    """Une entrée d'historique quantifié pour une question posée à ClarIA."""

    timestamp: str
    question: str
    answer: str
    confidence_label: str
    confidence_score: float
    source_documents: List[str]
    response_time_seconds: float
    used_web_fallback: bool
    search_mode: str
    prompt_tokens_estimate: int
    completion_tokens_estimate: int
    is_answer_found: bool

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "question": self.question,
            "answer": self.answer,
            "confidence_label": self.confidence_label,
            "confidence_score": self.confidence_score,
            "source_documents": ", ".join(self.source_documents),
            "response_time_seconds": round(self.response_time_seconds, 2),
            "used_web_fallback": self.used_web_fallback,
            "search_mode": self.search_mode,
            "prompt_tokens_estimate": self.prompt_tokens_estimate,
            "completion_tokens_estimate": self.completion_tokens_estimate,
            "is_answer_found": self.is_answer_found,
        }


def build_query_log_entry(
    question: str,
    answer: str,
    retrieved: Sequence[Tuple["Chunk", float]],
    response_time_seconds: float,
    search_mode: str = "hybrid",
    used_web_fallback: bool = False,
    prompt_text: str = "",
) -> QueryLogEntry:
    """Construit une entrée de log quantifiée à partir du résultat d'une
    question posée (à appeler juste après l'obtention de la réponse)."""
    confidence = compute_answer_confidence(retrieved, mode=search_mode)
    source_documents = sorted({chunk.doc_name for chunk, _ in retrieved})
    is_answer_found = NO_INFO_PHRASE not in answer

    return QueryLogEntry(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        question=question,
        answer=answer,
        confidence_label=confidence["label"],
        confidence_score=confidence["score"],
        source_documents=source_documents,
        response_time_seconds=response_time_seconds,
        used_web_fallback=used_web_fallback,
        search_mode=search_mode,
        prompt_tokens_estimate=estimate_tokens(prompt_text),
        completion_tokens_estimate=estimate_tokens(answer),
        is_answer_found=is_answer_found,
    )


def aggregate_usage_stats(entries: Sequence[QueryLogEntry]) -> dict:
    """Calcule des statistiques agrégées à partir d'un historique de
    requêtes : nombre total, taux de réponses sourcées, répartition de la
    confiance, documents les plus consultés, temps de réponse moyen et
    tokens estimés cumulés."""
    total = len(entries)
    empty_distribution = {label: 0 for label in CONFIDENCE_LABELS}

    if total == 0:
        return {
            "total_questions": 0,
            "answered_rate": 0.0,
            "no_info_rate": 0.0,
            "avg_response_time_seconds": 0.0,
            "avg_confidence_score": 0.0,
            "confidence_distribution": empty_distribution,
            "most_consulted_documents": [],
            "web_fallback_count": 0,
            "total_api_calls": 0,
            "total_tokens_estimate": 0,
        }

    answered = sum(1 for e in entries if e.is_answer_found)
    avg_response_time = sum(e.response_time_seconds for e in entries) / total
    avg_confidence = sum(e.confidence_score for e in entries) / total

    confidence_distribution = dict(empty_distribution)
    for e in entries:
        confidence_distribution[e.confidence_label] = (
            confidence_distribution.get(e.confidence_label, 0) + 1
        )

    doc_counts: Dict[str, int] = {}
    for e in entries:
        for doc in e.source_documents:
            doc_counts[doc] = doc_counts.get(doc, 0) + 1
    most_consulted = sorted(doc_counts.items(), key=lambda pair: pair[1], reverse=True)

    web_fallback_count = sum(1 for e in entries if e.used_web_fallback)
    total_tokens = sum(
        e.prompt_tokens_estimate + e.completion_tokens_estimate for e in entries
    )

    return {
        "total_questions": total,
        "answered_rate": round(answered / total, 3),
        "no_info_rate": round((total - answered) / total, 3),
        "avg_response_time_seconds": round(avg_response_time, 2),
        "avg_confidence_score": round(avg_confidence, 3),
        "confidence_distribution": confidence_distribution,
        "most_consulted_documents": most_consulted,
        "web_fallback_count": web_fallback_count,
        "total_api_calls": total,
        "total_tokens_estimate": total_tokens,
    }
