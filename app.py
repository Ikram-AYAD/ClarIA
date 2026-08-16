"""
app.py
------
Interface Streamlit de ClarIA, un assistant documentaire par IA (RAG).

Assemble document_loader.py, rag_core.py, pdf_export.py,
conversation_store.py, analytics.py et stats_export.py dans une
application de chat multi-tours :

  1. L'utilisateur dépose un ou plusieurs documents (PDF / DOCX / TXT).
     Les PDF scannés (sans couche de texte) sont automatiquement OCRisés.
  2. Chaque document est résumé automatiquement dès son indexation.
  3. L'utilisateur pose des questions en langage naturel ; ClarIA répond
     uniquement à partir du contenu indexé, en citant ses sources, en
     streaming (mot par mot). La recherche est hybride (sémantique + mots-
     clés) par défaut. Chaque réponse affiche un score de confiance.
  4. La conversation courante peut être exportée en PDF, et plusieurs
     conversations peuvent être sauvegardées / rechargées.
  5. Chaque document peut être retiré individuellement de l'index.
  6. Un tableau de bord quantifie l'usage (questions posées, taux de
     réponses sourcées, confiance moyenne, documents les plus consultés,
     temps de réponse, volume d'appels API) et s'exporte en CSV / Excel.

Bonus : une recherche web complémentaire (via DuckDuckGo, sans clé API)
peut être activée pour les cas où l'information n'est pas dans les
documents fournis ; elle est alors toujours annoncée explicitement comme
provenant du web, et non des documents de l'utilisateur.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import analytics
import conversation_store
import document_loader
import rag_core
import stats_export
import ui_theme
from pdf_export import export_conversation_to_pdf

load_dotenv()

APP_TITLE = "ClarIA"
APP_TAGLINE = "Votre assistant documentaire par IA - réponses sourcées, sans invention."

MAX_HISTORY_TURNS = 6  # nombre de tours (question+réponse) conservés pour le contexte LLM
LOW_RELEVANCE_THRESHOLD = 0.35  # score en dessous duquel on juge le contexte documentaire pauvre

SEARCH_MODE_LABELS = {
    "hybrid": "Hybride (sémantique + mots-clés)",
    "semantic": "Sémantique seule",
    "keyword": "Mots-clés seuls (BM25)",
}

# --------------------------------------------------------------------------
# Configuration et état de session
# --------------------------------------------------------------------------

def get_groq_api_key() -> str | None:
    try:
        secret_key = st.secrets.get("GROQ_API_KEY")  # type: ignore[union-attr]
    except Exception:
        secret_key = None
    return (
        st.session_state.get("groq_api_key_override")
        or secret_key
        or os.environ.get("GROQ_API_KEY")
    )


def init_session_state() -> None:
    defaults = {
        "vector_index": rag_core.VectorIndex(),
        "doc_summaries": {},          # doc_name -> résumé
        "doc_ocr_pages": {},          # doc_name -> nombre de pages OCRisées
        "indexed_docs": [],           # liste ordonnée des noms de documents indexés
        "display_messages": [],       # messages affichés (+ sources) pour l'UI et l'export PDF
        "llm_history": [],            # historique compact envoyé au LLM
        "query_log": [],              # historique quantifié (analytics.QueryLogEntry) pour le tableau de bord
        "web_search_enabled": False,
        "ocr_enabled": True,
        "chunk_size": rag_core.DEFAULT_CHUNK_SIZE,
        "chunk_overlap": rag_core.DEFAULT_CHUNK_OVERLAP,
        "top_k": rag_core.DEFAULT_TOP_K,
        "search_mode": rag_core.DEFAULT_SEARCH_MODE,
        "hybrid_alpha": rag_core.DEFAULT_HYBRID_ALPHA,
        "groq_api_key_override": "",
        "current_conversation_id": None,
        "current_conversation_title": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# --------------------------------------------------------------------------
# Indexation des documents
# --------------------------------------------------------------------------

def index_uploaded_files(uploaded_files, groq_client) -> None:
    index: rag_core.VectorIndex = st.session_state.vector_index
    progress = st.progress(0.0, text="Indexation en cours...")
    total = len(uploaded_files)

    for i, uploaded_file in enumerate(uploaded_files, start=1):
        doc_name = uploaded_file.name
        if doc_name in st.session_state.indexed_docs:
            progress.progress(i / total, text=f"{doc_name} déjà indexé, ignoré.")
            continue

        suffix = Path(doc_name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            segments = document_loader.load_document(
                tmp_path, ocr_fallback=st.session_state.ocr_enabled
            )
        except document_loader.UnsupportedFileType as exc:
            st.warning(str(exc))
            continue
        except Exception as exc:  # robustesse de l'extraction
            st.error(f"Erreur lors de la lecture de '{doc_name}' : {exc}")
            continue
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not segments:
            st.warning(f"Aucun texte exploitable trouvé dans '{doc_name}'.")
            continue

        ocr_pages = document_loader.ocr_page_count(segments)
        if ocr_pages:
            st.info(f"'{doc_name}' : {ocr_pages} page(s) scannée(s) traitée(s) par OCR.")
        st.session_state.doc_ocr_pages[doc_name] = ocr_pages

        next_id = len(index.chunks)
        chunks = rag_core.chunk_document(
            segments,
            doc_name=doc_name,
            chunk_size=st.session_state.chunk_size,
            overlap=st.session_state.chunk_overlap,
            start_id=next_id,
        )

        progress.progress(i / total, text=f"Calcul des embeddings pour {doc_name}...")
        try:
            index.add_chunks(chunks)
        except rag_core.EmbeddingModelUnavailable as exc:
            st.error(
                f"{exc} Le service d'hébergement a peut-être une connexion "
                "lente vers Hugging Face en ce moment. Réessaie dans une "
                "minute ; si le problème persiste, redémarre l'app depuis "
                "'Manage app' sur Streamlit Cloud."
            )
            continue
        st.session_state.indexed_docs.append(doc_name)

        if groq_client is not None:
            try:
                full_text = document_loader.full_text(segments)
                summary = rag_core.summarize_document(groq_client, full_text, doc_name)
                st.session_state.doc_summaries[doc_name] = summary
            except Exception as exc:
                st.session_state.doc_summaries[doc_name] = (
                    f"(Résumé indisponible : {exc})"
                )

        progress.progress(i / total, text=f"{doc_name} indexé.")

    progress.empty()


def remove_document(doc_name: str) -> None:
    index: rag_core.VectorIndex = st.session_state.vector_index
    removed = index.remove_document(doc_name)
    if doc_name in st.session_state.indexed_docs:
        st.session_state.indexed_docs.remove(doc_name)
    st.session_state.doc_summaries.pop(doc_name, None)
    st.session_state.doc_ocr_pages.pop(doc_name, None)
    if removed:
        st.toast(f"'{doc_name}' retiré de l'index ({removed} extraits supprimés).")


# --------------------------------------------------------------------------
# Recherche web complémentaire (bonus, optionnelle)
# --------------------------------------------------------------------------

def web_search(query: str, max_results: int = 3) -> list[dict]:
    """Recherche web gratuite (sans clé API) via DuckDuckGo. Renvoie une
    liste vide en cas d'échec (réseau indisponible, dépendance absente...)."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except ImportError:
            return []

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href") or r.get("url", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw_results
    ]


# --------------------------------------------------------------------------
# Conversations (multi-sessions sauvegardées)
# --------------------------------------------------------------------------

def start_new_conversation() -> None:
    st.session_state.display_messages = []
    st.session_state.llm_history = []
    st.session_state.current_conversation_id = None
    st.session_state.current_conversation_title = ""


def save_current_conversation(title: str) -> None:
    record = conversation_store.save_conversation(
        messages=st.session_state.display_messages,
        title=title,
        document_names=st.session_state.indexed_docs,
        conversation_id=st.session_state.current_conversation_id,
    )
    st.session_state.current_conversation_id = record.id
    st.session_state.current_conversation_title = record.title
    st.toast(f"Conversation '{record.title}' sauvegardée.")


def load_saved_conversation(conversation_id: str) -> None:
    record = conversation_store.load_conversation(conversation_id)
    st.session_state.display_messages = record.messages
    st.session_state.current_conversation_id = record.id
    st.session_state.current_conversation_title = record.title
    # Reconstruit un historique LLM compact à partir des messages affichés.
    st.session_state.llm_history = [
        {"role": m["role"], "content": m["content"]} for m in record.messages
    ]


# --------------------------------------------------------------------------
# Interface Streamlit - barre latérale
# --------------------------------------------------------------------------

def render_documents_section() -> None:
    st.markdown(ui_theme.section_title_html("📁", "Documents"), unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Dépose un ou plusieurs fichiers",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    st.session_state.ocr_enabled = st.checkbox(
        "OCR automatique pour les PDF scannés",
        value=st.session_state.ocr_enabled,
        help="Si un PDF ne contient pas de couche de texte (page scannée), le texte est extrait par reconnaissance optique de caractères.",
    )

    if st.button("Indexer les documents", disabled=not uploaded_files, use_container_width=True, type="primary"):
        groq_client = None
        api_key = get_groq_api_key()
        if api_key:
            try:
                groq_client = rag_core.get_groq_client(api_key)
            except Exception as exc:
                st.error(f"Impossible d'initialiser le client Groq : {exc}")
        index_uploaded_files(uploaded_files, groq_client)
        st.rerun()

    if st.session_state.indexed_docs:
        st.caption(f"{len(st.session_state.indexed_docs)} document(s) indexé(s)")
        for name in list(st.session_state.indexed_docs):
            col_name, col_remove = st.columns([5, 1])
            ocr_pages = st.session_state.doc_ocr_pages.get(name)
            note = f"OCR : {ocr_pages} page(s)" if ocr_pages else ""
            col_name.markdown(
                ui_theme.doc_card_html(ui_theme.file_icon(name), name, note),
                unsafe_allow_html=True,
            )
            if col_remove.button("🗑️", key=f"remove_{name}", help=f"Retirer '{name}' de l'index"):
                remove_document(name)
                st.rerun()


def render_search_settings() -> None:
    with st.expander("⚙️ Paramètres avancés"):
        st.session_state.chunk_size = st.slider(
            "Taille des chunks (caractères)", 300, 2000, st.session_state.chunk_size, step=50
        )
        st.session_state.chunk_overlap = st.slider(
            "Chevauchement (caractères)", 0, 500, st.session_state.chunk_overlap, step=25
        )
        st.session_state.top_k = st.slider(
            "Nombre d'extraits récupérés (top-k)", 1, 10, st.session_state.top_k
        )
        st.caption("La taille des chunks et le chevauchement s'appliquent aux prochains documents indexés.")

        st.divider()
        mode_label = st.radio(
            "Mode de recherche",
            options=list(SEARCH_MODE_LABELS.keys()),
            format_func=lambda m: SEARCH_MODE_LABELS[m],
            index=list(SEARCH_MODE_LABELS.keys()).index(st.session_state.search_mode),
            help="Hybride combine la recherche sémantique (sens) et la recherche par mots-clés BM25 (termes exacts), pour de meilleurs résultats dans la plupart des cas.",
        )
        st.session_state.search_mode = mode_label

        if st.session_state.search_mode == "hybrid":
            st.session_state.hybrid_alpha = st.slider(
                "Poids sémantique vs mots-clés",
                0.0, 1.0, st.session_state.hybrid_alpha, step=0.05,
                help="0 = mots-clés (BM25) seuls, 1 = sémantique seule.",
            )


def render_conversation_section() -> None:
    st.markdown(ui_theme.section_title_html("💬", "Conversation"), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Nouvelle conversation", use_container_width=True):
            start_new_conversation()
            st.rerun()
    with col2:
        if st.session_state.display_messages:
            pdf_path = Path(tempfile.gettempdir()) / "claria_conversation.pdf"
            export_conversation_to_pdf(
                st.session_state.display_messages,
                pdf_path,
                document_names=st.session_state.indexed_docs,
            )
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Exporter en PDF",
                    data=f.read(),
                    file_name="claria_conversation.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    with st.expander("Historique des conversations sauvegardées", expanded=False):
        title_default = st.session_state.current_conversation_title or "Nouvelle conversation"
        title_input = st.text_input("Titre de la conversation", value=title_default)
        if st.button(
            "Sauvegarder la conversation actuelle",
            disabled=not st.session_state.display_messages,
            use_container_width=True,
        ):
            save_current_conversation(title_input)
            st.rerun()

        st.divider()
        saved = conversation_store.list_conversations()
        if not saved:
            st.caption("Aucune conversation sauvegardée pour l'instant.")
        for record in saved:
            col_title, col_load, col_delete = st.columns([4, 1, 1])
            active = " (active)" if record.id == st.session_state.current_conversation_id else ""
            col_title.markdown(f"**{record.title}**{active}\n\n_{record.updated_at}_")
            if col_load.button("Charger", key=f"load_{record.id}"):
                load_saved_conversation(record.id)
                st.rerun()
            if col_delete.button("Suppr.", key=f"delete_{record.id}"):
                conversation_store.delete_conversation(record.id)
                if record.id == st.session_state.current_conversation_id:
                    start_new_conversation()
                st.rerun()


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(ui_theme.sidebar_logo_html(APP_TITLE), unsafe_allow_html=True)
        st.caption(APP_TAGLINE)

        st.markdown(ui_theme.section_title_html("🔑", "Clé API Groq"), unsafe_allow_html=True)
        if get_groq_api_key():
            st.success("Clé API détectée.", icon="✅")
        else:
            st.session_state.groq_api_key_override = st.text_input(
                "Clé API Groq",
                type="password",
                help=(
                    "Obtiens une clé gratuite sur console.groq.com. "
                    "Tu peux aussi la définir via GROQ_API_KEY (.env ou secrets Streamlit)."
                ),
            )

        render_documents_section()
        render_search_settings()

        st.session_state.web_search_enabled = st.toggle(
            "Recherche web complémentaire",
            value=st.session_state.web_search_enabled,
            help=(
                "Si activée, ClarIA peut chercher sur le web quand l'information "
                "n'est pas dans tes documents. La réponse indique alors clairement "
                "qu'elle provient du web et non de tes documents."
            ),
        )

        render_conversation_section()


# --------------------------------------------------------------------------
# Interface Streamlit - chat
# --------------------------------------------------------------------------

def render_summaries() -> None:
    if not st.session_state.doc_summaries:
        return
    with st.expander("Résumés automatiques des documents", expanded=False):
        for name, summary in st.session_state.doc_summaries.items():
            st.markdown(f"**{name}**")
            st.write(summary)
            st.divider()


def _render_sources_and_confidence(sources: list, confidence: dict | None) -> None:
    if confidence:
        st.markdown(
            ui_theme.confidence_badge_html(confidence["label"], confidence["score"]),
            unsafe_allow_html=True,
        )
    if sources:
        with st.expander("Sources citées"):
            for src in sources:
                loc = f", page {src['page']}" if src.get("page") else ""
                st.markdown(f"**{src['doc_name']}{loc}**")
                st.caption(src["text"])


def render_chat_history() -> None:
    if not st.session_state.display_messages:
        if not st.session_state.indexed_docs:
            st.markdown(
                ui_theme.empty_state_html(
                    "📄",
                    "Aucun document indexé pour l'instant",
                    "Dépose un PDF, un DOCX ou un TXT dans la barre latérale, puis clique sur "
                    "\"Indexer les documents\" pour commencer.",
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                ui_theme.empty_state_html(
                    "💬",
                    "Prêt à répondre à tes questions",
                    "Pose ta première question sur "
                    + (", ".join(st.session_state.indexed_docs))
                    + " dans le champ ci-dessous.",
                ),
                unsafe_allow_html=True,
            )
        return

    for msg in st.session_state.display_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                _render_sources_and_confidence(msg.get("sources") or [], msg.get("confidence"))


def handle_user_question(question: str) -> None:
    index: rag_core.VectorIndex = st.session_state.vector_index
    api_key = get_groq_api_key()

    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.display_messages.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        if not api_key:
            error_msg = (
                "Aucune clé API Groq n'est configurée. Renseigne-la dans la barre "
                "latérale pour que je puisse répondre."
            )
            st.error(error_msg)
            st.session_state.display_messages.append({"role": "assistant", "content": error_msg, "sources": []})
            return

        if index.is_empty():
            error_msg = "Indexe d'abord au moins un document pour que je puisse répondre."
            st.warning(error_msg)
            st.session_state.display_messages.append({"role": "assistant", "content": error_msg, "sources": []})
            return

        try:
            client = rag_core.get_groq_client(api_key)
        except Exception as exc:
            st.error(f"Erreur client Groq : {exc}")
            return

        retrieved = index.search(
            question,
            k=st.session_state.top_k,
            mode=st.session_state.search_mode,
            alpha=st.session_state.hybrid_alpha,
        )
        best_score = retrieved[0][1] if retrieved else 0.0

        web_results = []
        if st.session_state.web_search_enabled and (not retrieved or best_score < LOW_RELEVANCE_THRESHOLD):
            with st.spinner("Information absente des documents, recherche web..."):
                web_results = web_search(question)

        start_time = time.perf_counter()
        full_answer = None
        try:
            stream = rag_core.stream_answer(
                client,
                question,
                retrieved,
                history=st.session_state.llm_history[-MAX_HISTORY_TURNS * 2 :],
                web_results=web_results,
            )
            full_answer = st.write_stream(stream)
        except Exception as exc:
            full_answer = f"Une erreur est survenue lors de l'appel au modèle : {exc}"
            st.error(full_answer)
        response_time = time.perf_counter() - start_time

        sources = [
            {"doc_name": chunk.doc_name, "page": chunk.page, "text": chunk.text}
            for chunk, _score in retrieved
        ]
        confidence = analytics.compute_answer_confidence(retrieved, mode=st.session_state.search_mode)
        _render_sources_and_confidence(sources, confidence)

        if web_results:
            with st.expander("Résultats web utilisés (complémentaires)"):
                for r in web_results:
                    st.markdown(f"**{r['title']}** — {r['url']}")
                    st.caption(r["snippet"])

        prompt_text = rag_core.SYSTEM_PROMPT + rag_core.format_context(retrieved) + question
        log_entry = analytics.build_query_log_entry(
            question=question,
            answer=full_answer or "",
            retrieved=retrieved,
            response_time_seconds=response_time,
            search_mode=st.session_state.search_mode,
            used_web_fallback=bool(web_results),
            prompt_text=prompt_text,
        )
        st.session_state.query_log.append(log_entry)

    st.session_state.display_messages.append(
        {"role": "assistant", "content": full_answer, "sources": sources, "confidence": confidence}
    )
    st.session_state.llm_history.append({"role": "user", "content": question})
    st.session_state.llm_history.append({"role": "assistant", "content": full_answer})


# --------------------------------------------------------------------------
# Interface Streamlit - tableau de bord (métriques quantifiées)
# --------------------------------------------------------------------------

def render_dashboard() -> None:
    st.subheader("📊 Tableau de bord d'usage")
    entries = st.session_state.query_log

    if not entries:
        st.info("Pose au moins une question dans l'onglet Chat pour voir apparaître des statistiques ici.")
        return

    stats = analytics.aggregate_usage_stats(entries)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Questions posées", stats["total_questions"])
    col2.metric("Réponses sourcées", f"{stats['answered_rate'] * 100:.0f} %")
    col3.metric("Temps de réponse moyen", f"{stats['avg_response_time_seconds']:.1f} s")
    col4.metric("Confiance moyenne", f"{stats['avg_confidence_score']:.2f}")

    col5, col6 = st.columns(2)
    col5.metric("Appels API Groq (session)", stats["total_api_calls"])
    col6.metric("Tokens estimés cumulés", f"{stats['total_tokens_estimate']:,}".replace(",", " "))

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Répartition de la confiance des réponses**")
        dist = stats["confidence_distribution"]
        dist_df = pd.DataFrame({"Nombre de réponses": list(dist.values())}, index=list(dist.keys()))
        st.bar_chart(dist_df)
    with col_b:
        if stats["most_consulted_documents"]:
            st.markdown("**Documents les plus consultés**")
            docs, counts = zip(*stats["most_consulted_documents"])
            doc_df = pd.DataFrame({"Réponses citant ce document": counts}, index=docs)
            st.bar_chart(doc_df)
        else:
            st.caption("Aucun document cité pour l'instant.")

    st.markdown("**Historique détaillé des questions**")
    st.dataframe(pd.DataFrame([e.to_dict() for e in entries]), use_container_width=True)

    st.divider()
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button(
            "⬇️ Exporter en CSV",
            data=stats_export.query_log_to_csv_bytes(entries),
            file_name="claria_statistiques.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        xlsx_path = Path(tempfile.gettempdir()) / "claria_statistiques.xlsx"
        stats_export.export_query_log_to_excel(entries, xlsx_path)
        with open(xlsx_path, "rb") as f:
            st.download_button(
                "⬇️ Exporter en Excel",
                data=f.read(),
                file_name="claria_statistiques.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------

def _page_icon():
    """Utilise le logo ClarIA comme favicon si disponible, sinon un émoji."""
    try:
        from PIL import Image

        return Image.open(ui_theme.LOGO_PNG_PATH)
    except Exception:
        return "📄"


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=_page_icon(), layout="wide")
    st.markdown(ui_theme.CUSTOM_CSS, unsafe_allow_html=True)
    init_session_state()

    st.markdown(
        ui_theme.hero_banner_html(
            APP_TITLE,
            APP_TAGLINE,
            active_conversation=st.session_state.current_conversation_title,
        ),
        unsafe_allow_html=True,
    )

    render_sidebar()

    chat_tab, dashboard_tab = st.tabs(["💬 Chat", "📊 Tableau de bord"])

    with chat_tab:
        render_summaries()
        render_chat_history()
        question = st.chat_input("Pose une question sur tes documents...")
        if question:
            handle_user_question(question)

    with dashboard_tab:
        render_dashboard()


if __name__ == "__main__":
    main()
