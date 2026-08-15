"""
tests/test_analytics.py
-------------------------
Tests unitaires pour analytics.py : score de confiance, estimation de
tokens, construction d'entrees de log et agregation de statistiques
d'usage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analytics  # noqa: E402
import rag_core  # noqa: E402


def _chunk(doc_name: str, page=None) -> rag_core.Chunk:
    return rag_core.Chunk(id=0, text="texte", doc_name=doc_name, page=page)


# --------------------------------------------------------------------------
# Score de confiance
# --------------------------------------------------------------------------

def test_confidence_from_score_strong():
    result = analytics.confidence_from_score(0.9, mode="hybrid")
    assert result["label"] == "Fort"
    assert result["score"] == 0.9


def test_confidence_from_score_medium():
    result = analytics.confidence_from_score(0.4, mode="hybrid")
    assert result["label"] == "Moyen"


def test_confidence_from_score_weak():
    result = analytics.confidence_from_score(0.1, mode="hybrid")
    assert result["label"] == "Faible"


def test_confidence_from_score_uses_keyword_thresholds():
    # Un score BM25 de 6.0 est "Fort" avec les seuils du mode "keyword",
    # mais serait hors-echelle pour le mode "hybrid" (bornee a [-1, 1]).
    result = analytics.confidence_from_score(6.0, mode="keyword")
    assert result["label"] == "Fort"


def test_compute_answer_confidence_no_retrieved_chunks():
    result = analytics.compute_answer_confidence([], mode="hybrid")
    assert result == {"score": 0.0, "label": "Aucune source"}


def test_compute_answer_confidence_combines_best_and_average():
    retrieved = [(_chunk("a.pdf"), 0.9), (_chunk("b.pdf"), 0.1)]
    result = analytics.compute_answer_confidence(retrieved, mode="hybrid")
    # combinaison : 0.7*0.9 + 0.3*((0.9+0.1)/2) = 0.63 + 0.15 = 0.78
    assert result["score"] == 0.78
    assert result["label"] == "Fort"


# --------------------------------------------------------------------------
# Estimation de tokens
# --------------------------------------------------------------------------

def test_estimate_tokens_empty_string():
    assert analytics.estimate_tokens("") == 0


def test_estimate_tokens_roughly_four_chars_per_token():
    text = "a" * 40
    assert analytics.estimate_tokens(text) == 10


def test_estimate_tokens_minimum_one_for_nonempty():
    assert analytics.estimate_tokens("a") == 1


# --------------------------------------------------------------------------
# Construction d'une entree de log
# --------------------------------------------------------------------------

def test_build_query_log_entry_marks_answer_found():
    retrieved = [(_chunk("doc.pdf", page=2), 0.8)]
    entry = analytics.build_query_log_entry(
        question="Quel est le montant ?",
        answer="Le montant est de 100 euros [Source : doc.pdf, page 2].",
        retrieved=retrieved,
        response_time_seconds=1.5,
        search_mode="hybrid",
    )
    assert entry.is_answer_found is True
    assert entry.source_documents == ["doc.pdf"]
    assert entry.confidence_label == "Fort"
    assert entry.response_time_seconds == 1.5


def test_build_query_log_entry_marks_no_info_found():
    entry = analytics.build_query_log_entry(
        question="Question hors sujet ?",
        answer=analytics.NO_INFO_PHRASE,
        retrieved=[],
        response_time_seconds=0.8,
    )
    assert entry.is_answer_found is False
    assert entry.confidence_label == "Aucune source"
    assert entry.source_documents == []


def test_build_query_log_entry_tracks_web_fallback():
    entry = analytics.build_query_log_entry(
        question="Question ?",
        answer="Reponse trouvee sur le web.",
        retrieved=[],
        response_time_seconds=1.0,
        used_web_fallback=True,
    )
    assert entry.used_web_fallback is True


def test_query_log_entry_to_dict_has_expected_keys():
    entry = analytics.build_query_log_entry(
        question="Q", answer="A", retrieved=[], response_time_seconds=0.1
    )
    d = entry.to_dict()
    expected_keys = {
        "timestamp", "question", "answer", "confidence_label", "confidence_score",
        "source_documents", "response_time_seconds", "used_web_fallback",
        "search_mode", "prompt_tokens_estimate", "completion_tokens_estimate",
        "is_answer_found",
    }
    assert expected_keys <= set(d.keys())


# --------------------------------------------------------------------------
# Agregation de statistiques
# --------------------------------------------------------------------------

def test_aggregate_usage_stats_empty_list():
    stats = analytics.aggregate_usage_stats([])
    assert stats["total_questions"] == 0
    assert stats["answered_rate"] == 0.0
    assert stats["most_consulted_documents"] == []


def test_aggregate_usage_stats_computes_rates_and_counts():
    entries = [
        analytics.build_query_log_entry(
            "Q1", "Reponse sourcee [Source : a.pdf].", [(_chunk("a.pdf"), 0.9)], 1.0
        ),
        analytics.build_query_log_entry(
            "Q2", "Reponse sourcee [Source : a.pdf].", [(_chunk("a.pdf"), 0.6)], 2.0
        ),
        analytics.build_query_log_entry(
            "Q3", analytics.NO_INFO_PHRASE, [], 0.5
        ),
    ]
    stats = analytics.aggregate_usage_stats(entries)

    assert stats["total_questions"] == 3
    assert stats["answered_rate"] == round(2 / 3, 3)
    assert stats["no_info_rate"] == round(1 / 3, 3)
    assert stats["avg_response_time_seconds"] == round((1.0 + 2.0 + 0.5) / 3, 2)
    assert stats["most_consulted_documents"] == [("a.pdf", 2)]
    assert stats["total_api_calls"] == 3


def test_aggregate_usage_stats_web_fallback_count():
    entries = [
        analytics.build_query_log_entry("Q1", "R1", [], 1.0, used_web_fallback=True),
        analytics.build_query_log_entry("Q2", "R2", [], 1.0, used_web_fallback=False),
    ]
    stats = analytics.aggregate_usage_stats(entries)
    assert stats["web_fallback_count"] == 1
