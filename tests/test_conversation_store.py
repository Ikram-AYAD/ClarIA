"""
tests/test_conversation_store.py
----------------------------------
Tests unitaires pour conversation_store.py : sauvegarde, chargement,
listing et suppression de conversations persistees en JSON.

Chaque test utilise un repertoire temporaire (`tmp_path`) comme
`store_dir`, afin de ne jamais toucher au vrai dossier de conversations de
l'utilisateur.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import conversation_store as cs  # noqa: E402


SAMPLE_MESSAGES = [
    {"role": "user", "content": "Quel est le budget ?"},
    {
        "role": "assistant",
        "content": "Le budget est de 4.2 millions d'euros [Source : rapport.pdf, page 1].",
        "sources": [{"doc_name": "rapport.pdf", "page": 1, "text": "Le budget..."}],
    },
]


def test_save_conversation_creates_a_json_file(tmp_path):
    record = cs.save_conversation(
        SAMPLE_MESSAGES, title="Ma conversation", store_dir=tmp_path, document_names=["rapport.pdf"]
    )
    expected_path = tmp_path / f"{record.id}.json"
    assert expected_path.exists()
    assert record.title == "Ma conversation"
    assert record.document_names == ["rapport.pdf"]
    assert record.created_at == record.updated_at


def test_save_conversation_blank_title_gets_default(tmp_path):
    record = cs.save_conversation(SAMPLE_MESSAGES, title="   ", store_dir=tmp_path)
    assert record.title == "Conversation sans titre"


def test_load_conversation_round_trip(tmp_path):
    saved = cs.save_conversation(SAMPLE_MESSAGES, title="Titre test", store_dir=tmp_path)
    loaded = cs.load_conversation(saved.id, store_dir=tmp_path)

    assert loaded.id == saved.id
    assert loaded.title == "Titre test"
    assert loaded.messages == SAMPLE_MESSAGES


def test_load_conversation_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        cs.load_conversation("inconnue", store_dir=tmp_path)


def test_save_conversation_with_existing_id_updates_in_place(tmp_path):
    first = cs.save_conversation(SAMPLE_MESSAGES, title="Version 1", store_dir=tmp_path)
    updated_messages = SAMPLE_MESSAGES + [{"role": "user", "content": "Une autre question ?"}]

    second = cs.save_conversation(
        updated_messages, title="Version 2", store_dir=tmp_path, conversation_id=first.id
    )

    assert second.id == first.id
    assert second.created_at == first.created_at  # preserve
    assert second.title == "Version 2"

    reloaded = cs.load_conversation(first.id, store_dir=tmp_path)
    assert reloaded.title == "Version 2"
    assert len(reloaded.messages) == 3

    # Un seul fichier doit exister pour cette conversation (pas de doublon).
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_list_conversations_orders_by_most_recently_updated(tmp_path):
    first = cs.save_conversation(SAMPLE_MESSAGES, title="Ancienne", store_dir=tmp_path)
    second = cs.save_conversation(SAMPLE_MESSAGES, title="Recente", store_dir=tmp_path)
    # Force un updated_at strictement plus recent pour 'first' en le re-sauvegardant.
    cs.save_conversation(SAMPLE_MESSAGES, title="Ancienne", store_dir=tmp_path, conversation_id=first.id)

    records = cs.list_conversations(store_dir=tmp_path)
    assert records[0].id == first.id
    assert {r.id for r in records} == {first.id, second.id}


def test_list_conversations_ignores_corrupted_files(tmp_path):
    cs.save_conversation(SAMPLE_MESSAGES, title="Valide", store_dir=tmp_path)
    (tmp_path / "corrompue.json").write_text("{ceci n'est pas du json valide", encoding="utf-8")

    records = cs.list_conversations(store_dir=tmp_path)
    assert len(records) == 1
    assert records[0].title == "Valide"


def test_delete_conversation_removes_file(tmp_path):
    record = cs.save_conversation(SAMPLE_MESSAGES, title="A supprimer", store_dir=tmp_path)
    assert cs.delete_conversation(record.id, store_dir=tmp_path) is True
    assert not (tmp_path / f"{record.id}.json").exists()
    assert cs.list_conversations(store_dir=tmp_path) == []


def test_delete_conversation_missing_returns_false(tmp_path):
    assert cs.delete_conversation("inconnue", store_dir=tmp_path) is False
