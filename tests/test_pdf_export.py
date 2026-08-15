"""
tests/test_pdf_export.py
--------------------------
Tests unitaires pour pdf_export.py : le PDF genere doit etre valide et
contenir le contenu de la conversation (questions, reponses, sources).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdf_export import export_conversation_to_pdf  # noqa: E402


SAMPLE_CONVERSATION = [
    {"role": "user", "content": "Quel est le budget de l'entreprise ?"},
    {
        "role": "assistant",
        "content": "Le budget est de 4.2 millions d'euros [Source : rapport.pdf, page 1].",
        "sources": [{"doc_name": "rapport.pdf", "page": 1, "text": "Le budget total s'eleve a 4.2 millions d'euros."}],
    },
    {"role": "user", "content": "Et les risques ?"},
    {"role": "assistant", "content": "Je ne trouve pas cette information dans les documents fournis.", "sources": []},
]


def test_export_creates_a_valid_pdf_file(tmp_path):
    output_path = tmp_path / "export.pdf"
    result_path = export_conversation_to_pdf(SAMPLE_CONVERSATION, output_path, document_names=["rapport.pdf"])

    assert result_path == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert output_path.read_bytes()[:5] == b"%PDF-"


def test_export_contains_conversation_content(tmp_path):
    from pypdf import PdfReader

    output_path = tmp_path / "export.pdf"
    export_conversation_to_pdf(SAMPLE_CONVERSATION, output_path, document_names=["rapport.pdf"])

    reader = PdfReader(str(output_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "budget" in text.lower()
    assert "4.2 millions" in text
    assert "rapport.pdf" in text
    assert "Je ne trouve pas cette information" in text


def test_export_handles_empty_conversation(tmp_path):
    output_path = tmp_path / "empty.pdf"
    export_conversation_to_pdf([], output_path)
    assert output_path.exists()
    assert output_path.read_bytes()[:5] == b"%PDF-"


def test_export_escapes_html_special_characters(tmp_path):
    tricky_messages = [
        {"role": "user", "content": "Que signifie <script>alert('x')</script> & un test ?"},
        {"role": "assistant", "content": "Reponse avec des caracteres <speciaux> & non echappes.", "sources": []},
    ]
    output_path = tmp_path / "tricky.pdf"
    # Ne doit pas lever d'exception malgre les caracteres speciaux de type HTML.
    export_conversation_to_pdf(tricky_messages, output_path)
    assert output_path.exists()


def test_export_includes_confidence_when_present(tmp_path):
    from pypdf import PdfReader

    messages_with_confidence = [
        {"role": "user", "content": "Quel est le budget ?"},
        {
            "role": "assistant",
            "content": "Le budget est de 4.2 millions d'euros.",
            "sources": [{"doc_name": "rapport.pdf", "page": 1, "text": "..."}],
            "confidence": {"label": "Fort", "score": 0.83},
        },
    ]
    output_path = tmp_path / "confidence.pdf"
    export_conversation_to_pdf(messages_with_confidence, output_path)

    reader = PdfReader(str(output_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Confiance" in text
    assert "Fort" in text
    assert "0.83" in text


def test_export_without_confidence_key_still_works(tmp_path):
    messages_without_confidence = [
        {"role": "user", "content": "Question ?"},
        {"role": "assistant", "content": "Reponse.", "sources": []},
    ]
    output_path = tmp_path / "no_confidence.pdf"
    # Ne doit pas lever d'exception meme sans cle "confidence" (retro-compatibilite).
    export_conversation_to_pdf(messages_without_confidence, output_path)
    assert output_path.exists()
