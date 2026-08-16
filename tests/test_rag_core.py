"""
tests/test_rag_core.py
-----------------------
Tests unitaires pour rag_core.py : découpage en chunks, recherche
vectorielle et construction du prompt.

Un encodeur factice (FakeEncoder) est injecté dans VectorIndex afin de ne
pas dépendre d'un appel réseau à l'API d'inférence Hugging Face pendant les
tests (rapide, déterministe, fonctionne hors ligne). HFInferenceEncoder
(l'encodeur utilisé en production) est testé séparément avec un faux client
HTTP, voir plus bas dans ce fichier.
"""

import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rag_core  # noqa: E402


# --------------------------------------------------------------------------
# Encodeur factice pour les tests
# --------------------------------------------------------------------------

class FakeEncoder:
    """Encodeur déterministe basé sur un hachage de mots (sac de mots).

    Suffisamment sensible au contenu pour que des textes proches sur le
    plan lexical obtiennent une similarité cosinus plus élevée que des
    textes sans mot en commun, ce qui permet de tester la recherche
    vectorielle sans dépendre d'un vrai modèle de langage.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _word_index(self, word: str) -> int:
        return zlib.crc32(word.encode("utf-8")) % self.dim

    def encode(self, texts, **kwargs):
        vectors = np.zeros((len(texts), self.dim), dtype="float32")
        for i, text in enumerate(texts):
            for word in text.lower().split():
                vectors[i, self._word_index(word)] += 1.0
        return vectors


# --------------------------------------------------------------------------
# split_into_sentences / chunk_text
# --------------------------------------------------------------------------

def test_split_into_sentences_basic():
    text = "Le chat dort. Le chien court ! Est-ce vrai ?"
    sentences = rag_core.split_into_sentences(text)
    assert sentences == ["Le chat dort.", "Le chien court !", "Est-ce vrai ?"]


def test_split_into_sentences_empty_string():
    assert rag_core.split_into_sentences("") == []
    assert rag_core.split_into_sentences("   ") == []


def test_chunk_text_empty_returns_no_chunks():
    assert rag_core.chunk_text("") == []
    assert rag_core.chunk_text("   \n  ") == []


def test_chunk_text_single_short_text_is_one_chunk():
    text = "Une phrase courte. Une autre phrase courte."
    chunks = rag_core.chunk_text(text, chunk_size=800, overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_never_cuts_mid_sentence():
    sentence = "Ceci est une phrase de test qui sera repetee plusieurs fois."
    text = " ".join([sentence] * 20)
    chunks = rag_core.chunk_text(text, chunk_size=200, overlap=50)

    assert len(chunks) > 1
    for chunk in chunks:
        # Chaque chunk doit se terminer par une ponctuation de fin de phrase :
        # preuve qu'aucune coupe n'a lieu au milieu d'une phrase.
        assert chunk.strip().endswith((".", "!", "?"))
        # Chaque chunk doit etre compose de phrases completes issues du texte source.
        for piece in chunk.split(". "):
            cleaned = piece.strip().rstrip(".")
            assert cleaned == "" or cleaned in sentence


def test_chunk_text_produces_overlap_between_consecutive_chunks():
    sentence = "Le systeme documentaire indexe les extraits pertinents avec soin."
    text = " ".join([sentence] * 15)
    chunks = rag_core.chunk_text(text, chunk_size=180, overlap=60)

    assert len(chunks) >= 2
    for first, second in zip(chunks, chunks[1:]):
        first_sentences = set(rag_core.split_into_sentences(first))
        second_sentences = set(rag_core.split_into_sentences(second))
        assert first_sentences & second_sentences, "les chunks consécutifs devraient partager du contenu (chevauchement)"


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        rag_core.chunk_text("Un texte.", chunk_size=100, overlap=100)
    with pytest.raises(ValueError):
        rag_core.chunk_text("Un texte.", chunk_size=100, overlap=-1)


def test_chunk_text_rejects_invalid_chunk_size():
    with pytest.raises(ValueError):
        rag_core.chunk_text("Un texte.", chunk_size=0, overlap=0)


# --------------------------------------------------------------------------
# chunk_document
# --------------------------------------------------------------------------

def test_chunk_document_assigns_doc_name_and_page():
    segments = [
        {"page": 1, "text": "Contenu de la premiere page. Elle parle du budget."},
        {"page": 2, "text": "Contenu de la deuxieme page. Elle parle des risques."},
    ]
    chunks = rag_core.chunk_document(segments, doc_name="rapport.pdf", chunk_size=1000, overlap=100)

    assert len(chunks) == 2
    assert all(c.doc_name == "rapport.pdf" for c in chunks)
    assert chunks[0].page == 1
    assert chunks[1].page == 2
    assert chunks[0].id == 0
    assert chunks[1].id == 1


def test_chunk_document_start_id_offset():
    segments = [{"page": None, "text": "Un seul segment de texte simple."}]
    chunks = rag_core.chunk_document(segments, doc_name="notes.txt", start_id=42)
    assert chunks[0].id == 42


def test_chunk_citation_label_with_and_without_page():
    with_page = rag_core.Chunk(id=0, text="x", doc_name="doc.pdf", page=3)
    without_page = rag_core.Chunk(id=1, text="x", doc_name="doc.txt", page=None)
    assert with_page.citation_label() == "doc.pdf, page 3"
    assert without_page.citation_label() == "doc.txt"


# --------------------------------------------------------------------------
# VectorIndex (avec encodeur factice injecte)
# --------------------------------------------------------------------------

def _make_index_with_sample_chunks() -> rag_core.VectorIndex:
    index = rag_core.VectorIndex(encoder=FakeEncoder())
    chunks = [
        rag_core.Chunk(id=0, text="Le budget annuel augmente de dix pourcent cette annee.", doc_name="finance.pdf", page=1),
        rag_core.Chunk(id=1, text="Les chats sont des animaux domestiques independants.", doc_name="animaux.txt", page=None),
        rag_core.Chunk(id=2, text="Le budget previsionnel prevoit une reduction des couts.", doc_name="finance.pdf", page=2),
    ]
    index.add_chunks(chunks)
    return index


def test_vector_index_is_empty_before_adding_chunks():
    index = rag_core.VectorIndex(encoder=FakeEncoder())
    assert index.is_empty()
    assert index.search("question") == []


def test_vector_index_search_ranks_relevant_chunks_higher():
    index = _make_index_with_sample_chunks()
    results = index.search("Quel est le budget de l'entreprise ?", k=3)

    assert not index.is_empty()
    assert len(results) == 3
    top_chunk, top_score = results[0]
    assert top_chunk.doc_name == "finance.pdf"
    assert "budget" in top_chunk.text.lower()

    # Le chunk sur les chats (hors sujet) doit etre moins bien classe
    # que les deux chunks sur le budget.
    scores_by_id = {chunk.id: score for chunk, score in results}
    assert scores_by_id[0] > scores_by_id[1]
    assert scores_by_id[2] > scores_by_id[1]


def test_vector_index_search_respects_k():
    index = _make_index_with_sample_chunks()
    results = index.search("budget", k=1)
    assert len(results) == 1


def test_vector_index_documents_lists_unique_doc_names_in_order():
    index = _make_index_with_sample_chunks()
    assert index.documents() == ["finance.pdf", "animaux.txt"]


# --------------------------------------------------------------------------
# build_messages (construction du prompt)
# --------------------------------------------------------------------------

def test_build_messages_includes_system_prompt_and_context():
    chunk = rag_core.Chunk(id=0, text="Le contrat expire en 2027.", doc_name="contrat.pdf", page=4)
    messages = rag_core.build_messages("Quand expire le contrat ?", [(chunk, 0.87)])

    assert messages[0]["role"] == "system"
    assert "UNIQUEMENT" in messages[0]["content"]
    assert "Je ne trouve pas cette information" in messages[0]["content"]

    user_message = messages[-1]
    assert user_message["role"] == "user"
    assert "contrat.pdf" in user_message["content"]
    assert "Le contrat expire en 2027." in user_message["content"]
    assert "Quand expire le contrat ?" in user_message["content"]


def test_build_messages_with_no_retrieved_chunks_uses_placeholder():
    messages = rag_core.build_messages("Question sans contexte", [])
    user_message = messages[-1]
    assert "Aucun extrait pertinent" in user_message["content"]


def test_build_messages_includes_history_in_order():
    chunk = rag_core.Chunk(id=0, text="Texte.", doc_name="doc.txt", page=None)
    history = [
        {"role": "user", "content": "Premiere question"},
        {"role": "assistant", "content": "Premiere reponse"},
    ]
    messages = rag_core.build_messages("Deuxieme question", [(chunk, 0.5)], history=history)

    assert messages[0]["role"] == "system"
    assert messages[1] == history[0]
    assert messages[2] == history[1]
    assert messages[3]["role"] == "user"
    assert "Deuxieme question" in messages[3]["content"]


def test_build_messages_with_web_results_adds_web_instructions_and_block():
    web_results = [{"title": "Actu", "url": "https://example.com", "snippet": "Info recente."}]
    messages = rag_core.build_messages("Question", [], web_results=web_results)

    assert "RESULTATS WEB" in messages[0]["content"]
    assert "[RESULTATS WEB]" in messages[-1]["content"]
    assert "https://example.com" in messages[-1]["content"]


def test_build_messages_without_web_results_has_no_web_instructions():
    chunk = rag_core.Chunk(id=0, text="Texte.", doc_name="doc.txt", page=None)
    messages = rag_core.build_messages("Question", [(chunk, 0.5)])
    assert "RESULTATS WEB" not in messages[0]["content"]


# --------------------------------------------------------------------------
# Recherche hybride (BM25 + semantique) et suppression de document
# --------------------------------------------------------------------------

def _make_richer_index() -> rag_core.VectorIndex:
    index = rag_core.VectorIndex(encoder=FakeEncoder())
    chunks = [
        rag_core.Chunk(id=0, text="Le contrat mentionne le montant de 45000 euros pour la prestation.", doc_name="contrat.pdf", page=1),
        rag_core.Chunk(id=1, text="La procedure de resiliation est decrite dans la clause 12.", doc_name="contrat.pdf", page=3),
        rag_core.Chunk(id=2, text="Les chats et les chiens sont les animaux preferes des Francais.", doc_name="animaux.txt", page=None),
    ]
    index.add_chunks(chunks)
    return index


def test_keyword_search_finds_exact_term():
    index = _make_richer_index()
    results = index.search("45000 euros", k=2, mode="keyword")
    assert results, "la recherche par mots-clés devrait trouver au moins un résultat"
    assert results[0][0].id == 0


def test_semantic_search_mode_still_works():
    index = _make_richer_index()
    results = index.search("Quel est le montant du contrat ?", k=3, mode="semantic")
    assert results
    assert results[0][0].doc_name == "contrat.pdf"


def test_hybrid_search_is_default_mode():
    index = _make_richer_index()
    default_results = index.search("montant du contrat", k=2)
    explicit_results = index.search("montant du contrat", k=2, mode="hybrid")
    assert [c.id for c, _ in default_results] == [c.id for c, _ in explicit_results]


def test_hybrid_search_alpha_extremes_match_pure_modes():
    index = _make_richer_index()
    query = "clause de resiliation"

    hybrid_keyword_only = index.search(query, k=3, mode="hybrid", alpha=0.0)
    keyword_only = index.search(query, k=3, mode="keyword")
    assert [c.id for c, _ in hybrid_keyword_only][:1] == [c.id for c, _ in keyword_only][:1]

    hybrid_semantic_only = index.search(query, k=3, mode="hybrid", alpha=1.0)
    semantic_only = index.search(query, k=3, mode="semantic")
    assert [c.id for c, _ in hybrid_semantic_only] == [c.id for c, _ in semantic_only]


def test_search_rejects_unknown_mode():
    index = _make_richer_index()
    with pytest.raises(ValueError):
        index.search("question", mode="not-a-real-mode")


def test_remove_document_removes_only_matching_chunks():
    index = _make_richer_index()
    assert set(index.documents()) == {"contrat.pdf", "animaux.txt"}

    removed = index.remove_document("contrat.pdf")

    assert removed == 2
    assert index.documents() == ["animaux.txt"]
    assert index.index.ntotal == 1
    assert all(c.doc_name != "contrat.pdf" for c in index.chunks)


def test_remove_document_rebuilds_index_without_reencoding():
    index = _make_richer_index()
    calls_before = 0

    class CountingEncoder(FakeEncoder):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def encode(self, texts, **kwargs):
            self.calls += 1
            return super().encode(texts, **kwargs)

    counting_encoder = CountingEncoder()
    index2 = rag_core.VectorIndex(encoder=counting_encoder)
    index2.add_chunks([
        rag_core.Chunk(id=0, text="Un premier extrait.", doc_name="a.txt", page=None),
        rag_core.Chunk(id=1, text="Un second extrait.", doc_name="b.txt", page=None),
    ])
    calls_after_add = counting_encoder.calls
    index2.remove_document("a.txt")
    assert counting_encoder.calls == calls_after_add, "remove_document ne devrait pas appeler l'encodeur"
    assert index2.documents() == ["b.txt"]


def test_remove_document_not_found_returns_zero():
    index = _make_richer_index()
    assert index.remove_document("inexistant.pdf") == 0
    assert len(index.chunks) == 3


def test_remove_all_documents_empties_index():
    index = _make_richer_index()
    index.remove_document("contrat.pdf")
    index.remove_document("animaux.txt")
    assert index.is_empty()
    assert index.search("quoi que ce soit") == []


# --------------------------------------------------------------------------
# HFInferenceEncoder (embeddings via l'API d'inférence Hugging Face)
# --------------------------------------------------------------------------

class _FakeInferenceClient:
    """Remplace huggingface_hub.InferenceClient : aucun appel réseau."""

    def __init__(self, responses=None, fail_times=0, **kwargs):
        self.calls = []
        self._responses = responses
        self._fail_times = fail_times

    def feature_extraction(self, payload):
        self.calls.append(payload)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("service momentanément indisponible")
        if self._responses is not None:
            return self._responses.pop(0)
        # Réponse par défaut : un vecteur déjà poolé par texte.
        if isinstance(payload, list):
            return [[0.1, 0.2, 0.3] for _ in payload]
        return [0.1, 0.2, 0.3]


def _make_hf_encoder(monkeypatch, fake_client):
    import huggingface_hub

    monkeypatch.setattr(
        huggingface_hub, "InferenceClient", lambda **kwargs: fake_client
    )
    return rag_core.HFInferenceEncoder("all-MiniLM-L6-v2", token="fake-token")


def test_hf_inference_encoder_batch_call_returns_matrix(monkeypatch):
    fake_client = _FakeInferenceClient()
    encoder = _make_hf_encoder(monkeypatch, fake_client)

    vectors = encoder.encode(["bonjour", "au revoir"])

    assert vectors.shape == (2, 3)
    assert fake_client.calls == [["bonjour", "au revoir"]]


def test_hf_inference_encoder_pools_token_level_embeddings(monkeypatch):
    # Simule une réponse "brute" [batch, tokens, dim] non poolée.
    fake_client = _FakeInferenceClient(responses=[[[[1.0, 1.0], [3.0, 3.0]]]])
    encoder = _make_hf_encoder(monkeypatch, fake_client)

    vectors = encoder.encode(["un seul texte"])

    assert vectors.shape == (1, 2)
    assert vectors[0].tolist() == [2.0, 2.0]  # moyenne de [1,1] et [3,3]


def test_hf_inference_encoder_falls_back_to_per_text_calls(monkeypatch):
    monkeypatch.setattr(rag_core.time, "sleep", lambda _seconds: None)
    # Le premier appel (batch) échoue à chaque tentative -> repli par texte.
    fake_client = _FakeInferenceClient(fail_times=3)
    encoder = _make_hf_encoder(monkeypatch, fake_client)

    vectors = encoder.encode(["a", "b"])

    assert vectors.shape == (2, 3)
    # 3 tentatives batch ratées, puis 1 appel par texte (2 appels réussis).
    assert fake_client.calls[-2:] == ["a", "b"]


def test_hf_inference_encoder_empty_input_returns_empty_matrix(monkeypatch):
    fake_client = _FakeInferenceClient()
    encoder = _make_hf_encoder(monkeypatch, fake_client)

    vectors = encoder.encode([])

    assert vectors.shape == (0, rag_core.EMBEDDING_DIM)


def test_vector_index_wraps_encoder_errors_in_embedding_model_unavailable():
    class AlwaysFailsEncoder:
        def encode(self, texts, **kwargs):
            raise RuntimeError("HF API indisponible")

    index = rag_core.VectorIndex(encoder=AlwaysFailsEncoder())
    chunk = rag_core.Chunk(id=0, text="texte", doc_name="doc.txt", page=None)

    with pytest.raises(rag_core.EmbeddingModelUnavailable):
        index.add_chunks([chunk])
