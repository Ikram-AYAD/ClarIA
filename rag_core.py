"""
rag_core.py
-----------
Cœur du pipeline RAG (Retrieval-Augmented Generation) de ClarIA :

  1. Découpage des documents en chunks (avec chevauchement, en respectant
     les fins de phrase).
  2. Indexation vectorielle des chunks (embeddings + FAISS, similarité
     cosinus via IndexFlatIP) combinée à une recherche par mots-clés
     (BM25) pour une recherche hybride plus robuste.
  3. Recherche des chunks les plus pertinents pour une question.
  4. Construction du prompt (contexte strict + citation obligatoire).
  5. Appel au modèle Groq (llama-3.1-8b-instant) en mode normal ou streaming.
  6. Résumé automatique de document.

Ce module est volontairement indépendant de Streamlit afin de pouvoir être
testé unitairement (voir tests/test_rag_core.py) et réutilisé dans d'autres
contextes (CLI, API, etc.). L'encodeur d'embeddings est injectable : les
tests peuvent fournir un faux encodeur pour ne pas dépendre du téléchargement
du vrai modèle sentence-transformers.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterator, List, Optional, Protocol, Sequence, Tuple

import numpy as np

# Désactive le protocole de téléchargement accéléré "Xet" de huggingface_hub.
# Sur certains environnements cloud (dont Streamlit Community Cloud), Xet
# reste bloqué plusieurs minutes sans erreur ni log lors du premier
# téléchargement du modèle d'embeddings, ce qui déclenche l'échec du
# health-check de la plateforme et fait planter l'application. Le
# téléchargement HTTP classique, plus lent mais fiable, est utilisé à la
# place. Doit être défini avant tout import de sentence-transformers /
# huggingface_hub, d'où sa position ici (import paresseux plus bas).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
# Bornes de temps strictes pour tout appel réseau vers Hugging Face : si la
# connexion reste bloquée (fréquent sur certains réseaux cloud restreints),
# une erreur claire est levée après quelques secondes au lieu de laisser
# l'application entière rester muette pendant plusieurs minutes jusqu'à ce
# que la plateforme d'hébergement la tue (health-check en échec).
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "20")

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_TOP_K = 5
DEFAULT_SEARCH_MODE = "hybrid"  # "semantic" | "keyword" | "hybrid"
DEFAULT_HYBRID_ALPHA = 0.5  # poids de la similarité sémantique dans le mode hybride


# --------------------------------------------------------------------------
# 1. Découpage en chunks
# --------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def split_into_sentences(text: str) -> List[str]:
    """Découpe un texte en phrases, en normalisant les espaces.

    Utilise une règle simple mais robuste : une phrase se termine par
    '.', '!' ou '?' suivi d'un espace. Cela suffit pour éviter de couper
    des chunks au milieu d'une phrase.
    """
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if not normalized:
        return []
    sentences = _SENTENCE_SPLIT_RE.split(normalized)
    return [s.strip() for s in sentences if s.strip()]


def _tokenize(text: str) -> List[str]:
    """Tokenisation simple (mots, insensible à la casse) pour BM25."""
    return _TOKEN_RE.findall(text.lower())


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Découpe un texte en chunks d'environ `chunk_size` caractères.

    Les coupures se font toujours à une fin de phrase (jamais au milieu
    d'une phrase). Chaque nouveau chunk reprend, en début, les dernières
    phrases du chunk précédent jusqu'à atteindre environ `overlap`
    caractères, ce qui crée le chevauchement demandé.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size doit être strictement positif")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap doit être >= 0 et strictement inférieur à chunk_size")

    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    i = 0

    while i < len(sentences):
        sentence = sentences[i]
        sentence_len = len(sentence) + 1  # +1 pour l'espace de jointure

        if current and current_len + sentence_len > chunk_size:
            chunks.append(" ".join(current))

            # Construit le chevauchement à partir de la fin du chunk courant.
            overlap_sentences: List[str] = []
            overlap_len = 0
            for s in reversed(current):
                overlap_len += len(s) + 1
                overlap_sentences.insert(0, s)
                if overlap_len >= overlap:
                    break

            current = overlap_sentences
            current_len = sum(len(s) + 1 for s in current)
            continue  # réessaie d'ajouter la même phrase au nouveau chunk

        current.append(sentence)
        current_len += sentence_len
        i += 1

    if current:
        chunks.append(" ".join(current))

    return chunks


@dataclass
class Chunk:
    """Un fragment de document indexé, avec ses métadonnées de citation."""

    id: int
    text: str
    doc_name: str
    page: Optional[int] = None

    def citation_label(self) -> str:
        if self.page is not None:
            return f"{self.doc_name}, page {self.page}"
        return self.doc_name


def chunk_document(
    segments: Sequence[dict],
    doc_name: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    start_id: int = 0,
) -> List[Chunk]:
    """Transforme les segments d'un document (voir document_loader) en Chunks."""
    chunks: List[Chunk] = []
    next_id = start_id
    for segment in segments:
        page = segment.get("page")
        for piece in chunk_text(segment["text"], chunk_size, overlap):
            chunks.append(Chunk(id=next_id, text=piece, doc_name=doc_name, page=page))
            next_id += 1
    return chunks


# --------------------------------------------------------------------------
# 2. Index vectoriel (embeddings + FAISS) + recherche hybride (BM25)
# --------------------------------------------------------------------------

class EmbeddingModelUnavailable(RuntimeError):
    """Levée quand le modèle d'embeddings n'a pas pu être chargé/téléchargé
    (timeout réseau, service Hugging Face indisponible, etc.). Permet à
    l'interface (Streamlit) d'afficher un message clair plutôt que de
    rester bloquée silencieusement."""


class Encoder(Protocol):
    """Interface minimale attendue pour un encodeur d'embeddings.

    `SentenceTransformer` la respecte déjà. Les tests peuvent injecter un
    faux encodeur qui respecte cette même interface.
    """

    def encode(self, texts: Sequence[str], **kwargs) -> np.ndarray:
        ...


class VectorIndex:
    """Index hybride en mémoire : recherche sémantique (FAISS IndexFlatIP,
    similarité cosinus via normalisation L2) + recherche par mots-clés
    (BM25 via rank-bm25), combinables ou utilisables séparément.

    Les embeddings sont conservés en cache (`self._embeddings`) afin que la
    suppression d'un document (`remove_document`) puisse reconstruire
    l'index FAISS sans avoir à ré-encoder les chunks restants.
    """

    def __init__(self, encoder: Optional[Encoder] = None, model_name: str = "all-MiniLM-L6-v2"):
        self._encoder = encoder
        self._model_name = model_name
        self.index = None
        self.chunks: List[Chunk] = []
        self._embeddings: List[np.ndarray] = []
        self._bm25 = None
        self._bm25_dirty = True

    @property
    def encoder(self) -> Encoder:
        """Charge paresseusement sentence-transformers si aucun encodeur
        n'a été injecté (évite le téléchargement du modèle dans les tests)."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            try:
                self._encoder = SentenceTransformer(self._model_name)
            except Exception as exc:  # noqa: BLE001 - on veut tout intercepter ici
                raise EmbeddingModelUnavailable(
                    "Impossible de charger le modèle d'embeddings "
                    f"'{self._model_name}' (réseau lent ou indisponible ?)."
                ) from exc
        return self._encoder

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self.encoder.encode(
            list(texts), convert_to_numpy=True, show_progress_bar=False
        )
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-12
        return vectors / norms

    def add_chunks(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        import faiss

        vectors = self._embed([c.text for c in chunks])
        if self.index is None:
            self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self.chunks.extend(chunks)
        self._embeddings.extend(vectors)
        self._bm25_dirty = True

    def remove_document(self, doc_name: str) -> int:
        """Retire de l'index tous les chunks appartenant à `doc_name`.

        Reconstruit l'index FAISS à partir des embeddings mis en cache
        (aucun nouvel appel à l'encodeur n'est nécessaire). Renvoie le
        nombre de chunks retirés.
        """
        keep_indices = [i for i, c in enumerate(self.chunks) if c.doc_name != doc_name]
        removed = len(self.chunks) - len(keep_indices)
        if removed == 0:
            return 0

        self.chunks = [self.chunks[i] for i in keep_indices]
        self._embeddings = [self._embeddings[i] for i in keep_indices]
        self._rebuild_faiss_index()
        self._bm25_dirty = True
        return removed

    def _rebuild_faiss_index(self) -> None:
        import faiss

        if not self._embeddings:
            self.index = None
            return
        dim = self._embeddings[0].shape[0]
        new_index = faiss.IndexFlatIP(dim)
        matrix = np.vstack(self._embeddings).astype("float32")
        new_index.add(matrix)
        self.index = new_index

    def _ensure_bm25(self) -> None:
        if not self._bm25_dirty:
            return
        if not self.chunks:
            self._bm25 = None
        else:
            from rank_bm25 import BM25Okapi

            tokenized = [_tokenize(c.text) for c in self.chunks]
            self._bm25 = BM25Okapi(tokenized)
        self._bm25_dirty = False

    def is_empty(self) -> bool:
        return self.index is None or self.index.ntotal == 0

    def documents(self) -> List[str]:
        """Liste (dédupliquée, dans l'ordre d'ajout) des noms de documents indexés."""
        seen: List[str] = []
        for c in self.chunks:
            if c.doc_name not in seen:
                seen.append(c.doc_name)
        return seen

    # -- Recherche ---------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = DEFAULT_TOP_K,
        mode: str = DEFAULT_SEARCH_MODE,
        alpha: float = DEFAULT_HYBRID_ALPHA,
    ) -> List[Tuple[Chunk, float]]:
        """Renvoie les k chunks les plus pertinents pour `query`.

        `mode` :
          - "semantic" : similarité cosinus (embeddings) seule.
          - "keyword"  : score BM25 (mots-clés) seul.
          - "hybrid"   : combinaison pondérée des deux (par défaut), utile
            pour bien retrouver à la fois le sens général d'une question et
            les termes exacts (noms propres, chiffres, références) qu'elle
            contient.
        `alpha` (mode hybride uniquement) : poids de la similarité
        sémantique, entre 0 (BM25 pur) et 1 (sémantique pur).
        """
        if self.is_empty() or not query.strip():
            return []

        if mode == "semantic":
            return self._semantic_search(query, k)
        if mode == "keyword":
            return self._keyword_search(query, k)
        if mode == "hybrid":
            return self._hybrid_search(query, k, alpha)
        raise ValueError(f"Mode de recherche inconnu : '{mode}' (attendu: semantic, keyword, hybrid)")

    def _semantic_search(self, query: str, k: int) -> List[Tuple[Chunk, float]]:
        k = min(k, self.index.ntotal)
        query_vector = self._embed([query])
        scores, indices = self.index.search(query_vector, k)

        results: List[Tuple[Chunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def _keyword_search(self, query: str, k: int) -> List[Tuple[Chunk, float]]:
        self._ensure_bm25()
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.chunks[i], float(scores[i])) for i in ranked if scores[i] > 0]

    def _hybrid_search(self, query: str, k: int, alpha: float) -> List[Tuple[Chunk, float]]:
        self._ensure_bm25()

        # Scores sémantiques sur l'ensemble des chunks (pas seulement le
        # top-k) afin de pouvoir les combiner équitablement avec BM25.
        query_vector = self._embed([query])
        all_scores, all_indices = self.index.search(query_vector, self.index.ntotal)
        semantic_by_index = {
            int(idx): float(score) for idx, score in zip(all_indices[0], all_scores[0]) if idx != -1
        }

        if self._bm25 is not None:
            bm25_scores = list(self._bm25.get_scores(_tokenize(query)))
        else:
            bm25_scores = [0.0] * len(self.chunks)

        # Normalisation min-max de BM25 dans [0, 1] pour le rendre comparable
        # à la similarité cosinus (déjà dans [-1, 1], typiquement [0, 1] en
        # pratique pour des textes proches).
        max_bm25 = max(bm25_scores) if bm25_scores else 0.0
        normalized_bm25 = [s / max_bm25 if max_bm25 > 0 else 0.0 for s in bm25_scores]

        combined: List[Tuple[int, float]] = []
        for i in range(len(self.chunks)):
            semantic_score = semantic_by_index.get(i, 0.0)
            keyword_score = normalized_bm25[i]
            combined.append((i, alpha * semantic_score + (1 - alpha) * keyword_score))

        combined.sort(key=lambda pair: pair[1], reverse=True)
        top = combined[:k]
        return [(self.chunks[i], score) for i, score in top]


# --------------------------------------------------------------------------
# 3. Construction du prompt
# --------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Tu es ClarIA, un assistant documentaire rigoureux. Tu réponds "
    "UNIQUEMENT à partir des extraits de documents fournis dans le contexte "
    "ci-dessous.\n\n"
    "Règles strictes, non négociables :\n"
    "1. N'utilise aucune connaissance externe au contexte fourni, même si tu "
    "penses connaître la réponse.\n"
    "2. Si l'information demandée ne figure pas dans le contexte, réponds "
    "explicitement : \"Je ne trouve pas cette information dans les documents "
    "fournis.\" Ne comble jamais un manque d'information par une supposition.\n"
    "3. Chaque affirmation factuelle doit citer l'extrait source utilisé, au "
    "format : [Source : nom_du_document, extrait ou page].\n"
    "4. N'invente jamais de chiffre, de nom, de date ou de citation.\n"
    "5. Réponds dans la même langue que la question posée.\n"
    "6. Sois concis et précis ; structure ta réponse si plusieurs points sont "
    "abordés."
)

WEB_SYSTEM_SUFFIX = (
    "\n\nSi, et seulement si, le contexte documentaire ci-dessus ne contient "
    "pas la réponse, tu peux utiliser les résultats de recherche web fournis "
    "sous l'étiquette [RESULTATS WEB]. Dans ce cas, indique très clairement "
    "au début de ta réponse que l'information provient du web et non des "
    "documents fournis par l'utilisateur, et cite la source web (titre / URL)."
)


def format_context(retrieved: Sequence[Tuple[Chunk, float]]) -> str:
    """Met en forme les chunks récupérés pour les insérer dans le prompt."""
    blocks = []
    for i, (chunk, score) in enumerate(retrieved, start=1):
        blocks.append(
            f"[Extrait {i} - {chunk.citation_label()} - similarité={score:.2f}]\n"
            f"{chunk.text}"
        )
    return "\n\n".join(blocks)


def build_messages(
    query: str,
    retrieved: Sequence[Tuple[Chunk, float]],
    history: Optional[Sequence[dict]] = None,
    web_results: Optional[Sequence[dict]] = None,
) -> List[dict]:
    """Construit la liste de messages (format API chat) envoyée à Groq.

    `history` est une liste optionnelle de messages précédents
    ({"role": "user"/"assistant", "content": str}) pour le multi-tours.
    `web_results` est une liste optionnelle de résultats de recherche web
    (fonctionnalité complémentaire, désactivée par défaut) au format
    {"title": str, "url": str, "snippet": str}.
    """
    context = format_context(retrieved)
    if not context:
        context = "(Aucun extrait pertinent trouvé dans les documents indexés.)"

    system_prompt = SYSTEM_PROMPT
    web_block = ""
    if web_results:
        system_prompt = SYSTEM_PROMPT + WEB_SYSTEM_SUFFIX
        web_lines = [
            f"[Résultat web {i}] {r.get('title', '')} ({r.get('url', '')})\n{r.get('snippet', '')}"
            for i, r in enumerate(web_results, start=1)
        ]
        web_block = "\n\n[RESULTATS WEB]\n" + "\n\n".join(web_lines)

    user_content = (
        f"Contexte documentaire :\n{context}{web_block}\n\n"
        f"Question : {query}\n\n"
        "Réponds en te basant strictement sur le contexte ci-dessus et cite "
        "l'extrait utilisé pour chaque affirmation."
    )

    messages: List[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    return messages


# --------------------------------------------------------------------------
# 4. Appels au modèle Groq
# --------------------------------------------------------------------------

def get_groq_client(api_key: Optional[str] = None):
    """Instancie un client Groq. Lève une erreur claire si la clé est absente."""
    from groq import Groq

    if not api_key:
        raise ValueError(
            "Clé API Groq manquante. Définis GROQ_API_KEY dans l'environnement "
            "(ou .env), ou renseigne-la dans l'interface / les secrets Streamlit."
        )
    return Groq(api_key=api_key)


def answer_query(
    client,
    query: str,
    retrieved: Sequence[Tuple[Chunk, float]],
    history: Optional[Sequence[dict]] = None,
    web_results: Optional[Sequence[dict]] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
) -> str:
    """Appelle Groq en mode non-streaming et renvoie la réponse complète."""
    messages = build_messages(query, retrieved, history, web_results)
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return completion.choices[0].message.content


def stream_answer(
    client,
    query: str,
    retrieved: Sequence[Tuple[Chunk, float]],
    history: Optional[Sequence[dict]] = None,
    web_results: Optional[Sequence[dict]] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
) -> Iterator[str]:
    """Appelle Groq en mode streaming et cède les morceaux de texte au fur
    et à mesure de leur réception (pour un affichage mot par mot)."""
    messages = build_messages(query, retrieved, history, web_results)
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


def summarize_document(
    client,
    doc_text: str,
    doc_name: str,
    model: str = DEFAULT_MODEL,
    max_chars: int = 12000,
) -> str:
    """Génère un résumé automatique d'un document juste après son indexation."""
    excerpt = doc_text[:max_chars]
    truncated_note = (
        "\n\n(Note : le document a été tronqué pour le résumé car il est très long.)"
        if len(doc_text) > max_chars
        else ""
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Tu rédiges des résumés clairs, fidèles et neutres de documents, "
                "en français. Tu ne dois jamais ajouter d'information absente du "
                "texte fourni."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Résume le document suivant ('{doc_name}') en 5 à 8 phrases, "
                f"en dégageant les points clés et la structure générale :\n\n"
                f"{excerpt}{truncated_note}"
            ),
        },
    ]
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        stream=False,
    )
    return completion.choices[0].message.content
