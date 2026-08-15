"""
pdf_export.py
-------------
Export d'une conversation ClarIA (questions, réponses, sources citées,
score de confiance) au format PDF, via ReportLab. Indépendant de
Streamlit.
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import List, Optional, TypedDict, Union

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

PathLike = Union[str, Path]


class SourceRef(TypedDict, total=False):
    doc_name: str
    page: Optional[int]
    text: str


class ConfidenceInfo(TypedDict, total=False):
    label: str
    score: float


class ConversationMessage(TypedDict, total=False):
    role: str  # "user" ou "assistant"
    content: str
    sources: List[SourceRef]
    confidence: ConfidenceInfo
    timestamp: str


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ClarIATitle",
            parent=styles["Title"],
            fontSize=20,
            spaceAfter=6,
            textColor=colors.HexColor("#1F2A44"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIAMeta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#666666"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIAUser",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            backColor=colors.HexColor("#EEF3FF"),
            borderPadding=8,
            spaceBefore=10,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIAAssistant",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            backColor=colors.HexColor("#F5F5F0"),
            borderPadding=8,
            spaceBefore=4,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIASource",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#444444"),
            leftIndent=14,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIALabel",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#888888"),
            spaceBefore=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ClarIAConfidence",
            parent=styles["Normal"],
            fontSize=8.5,
            textColor=colors.HexColor("#2E7D32"),
            spaceAfter=4,
        )
    )
    return styles


def _escaped_paragraph(text: str, style) -> Paragraph:
    """Échappe le texte utilisateur avant insertion (ReportLab interprète
    un mini-langage HTML dans les Paragraph)."""
    safe = escape(text or "").replace("\n", "<br/>")
    return Paragraph(safe, style)


def export_conversation_to_pdf(
    messages: List[ConversationMessage],
    output_path: PathLike,
    title: str = "Conversation ClarIA",
    document_names: Optional[List[str]] = None,
) -> Path:
    """Génère un PDF récapitulant l'intégralité d'une conversation.

    `messages` est une liste ordonnée de dicts :
        {"role": "user", "content": "..."}
        {"role": "assistant", "content": "...", "sources": [
            {"doc_name": "...", "page": 3, "text": "extrait cité..."}
        ], "confidence": {"label": "Fort", "score": 0.82}}

    Le champ `confidence` est optionnel (rétro-compatible avec des
    conversations sauvegardées avant l'ajout du score de confiance).

    Renvoie le chemin du fichier PDF généré.
    """
    output_path = Path(output_path)
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
    )

    story = []
    story.append(_escaped_paragraph(title, styles["ClarIATitle"]))

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    meta_text = f"Généré le {generated_at}"
    if document_names:
        meta_text += " - Documents : " + ", ".join(document_names)
    story.append(_escaped_paragraph(meta_text, styles["ClarIAMeta"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 10))

    if not messages:
        story.append(_escaped_paragraph("Aucun échange dans cette conversation.", styles["Normal"]))

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            story.append(_escaped_paragraph("Vous", styles["ClarIALabel"]))
            story.append(_escaped_paragraph(content, styles["ClarIAUser"]))
        else:
            story.append(_escaped_paragraph("ClarIA", styles["ClarIALabel"]))
            story.append(_escaped_paragraph(content, styles["ClarIAAssistant"]))

            confidence = msg.get("confidence")
            if confidence and confidence.get("label"):
                score = confidence.get("score")
                score_text = f" (score {score:.2f})" if isinstance(score, (int, float)) else ""
                story.append(
                    _escaped_paragraph(
                        f"Confiance : {confidence['label']}{score_text}", styles["ClarIAConfidence"]
                    )
                )

            sources = msg.get("sources") or []
            if sources:
                story.append(_escaped_paragraph("Sources citées :", styles["ClarIALabel"]))
                for src in sources:
                    doc_name = src.get("doc_name", "document inconnu")
                    page = src.get("page")
                    loc = f", page {page}" if page else ""
                    excerpt = (src.get("text") or "").strip()
                    if len(excerpt) > 220:
                        excerpt = excerpt[:220].rstrip() + "..."
                    label = f"[{doc_name}{loc}] {excerpt}"
                    story.append(_escaped_paragraph(label, styles["ClarIASource"]))

        story.append(Spacer(1, 6))

    doc.build(story)
    return output_path
