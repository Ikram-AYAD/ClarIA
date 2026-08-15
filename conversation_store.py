"""
conversation_store.py
----------------------
Persistance de plusieurs conversations ClarIA sous forme de fichiers JSON,
pour permettre de sauvegarder, recharger et gérer un historique multi-
conversations (en plus du simple export PDF de la conversation en cours).

Indépendant de Streamlit : testable et réutilisable tel quel (CLI, script,
notebook...).
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]

# Stockage par défaut : un dossier "conversations/" à côté de ce module.
# Sur Streamlit Community Cloud, ce stockage est éphémère (remis à zéro au
# redémarrage de l'application) ; voir le README pour les limites connues.
DEFAULT_STORE_DIR = Path(__file__).resolve().parent / "conversations"


@dataclass
class ConversationRecord:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list
    document_names: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
            "document_names": self.document_names,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationRecord":
        return cls(
            id=data["id"],
            title=data.get("title") or "Conversation sans titre",
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            messages=data.get("messages", []),
            document_names=data.get("document_names", []),
        )


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:max_len] or "conversation"


def _ensure_store_dir(store_dir: PathLike) -> Path:
    path = Path(store_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_conversation_id(title: str) -> str:
    """Génère un identifiant unique, lisible et triable (préfixe horodaté)."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{_slugify(title)}-{uuid.uuid4().hex[:6]}"


def save_conversation(
    messages: list,
    title: str,
    store_dir: PathLike = DEFAULT_STORE_DIR,
    document_names: Optional[list] = None,
    conversation_id: Optional[str] = None,
) -> ConversationRecord:
    """Sauvegarde (création ou mise à jour) une conversation en JSON.

    Si `conversation_id` correspond à une conversation déjà sauvegardée,
    elle est mise à jour (le champ `created_at` d'origine est conservé).
    Sinon, une nouvelle conversation est créée avec un nouvel identifiant.
    """
    directory = _ensure_store_dir(store_dir)
    now = datetime.now().isoformat(timespec="microseconds")
    created_at = now

    if conversation_id:
        existing_path = directory / f"{conversation_id}.json"
        if existing_path.exists():
            try:
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
                created_at = existing.get("created_at", now)
            except json.JSONDecodeError:
                pass
    else:
        conversation_id = new_conversation_id(title)

    record = ConversationRecord(
        id=conversation_id,
        title=(title or "").strip() or "Conversation sans titre",
        created_at=created_at,
        updated_at=now,
        messages=messages,
        document_names=list(document_names or []),
    )

    path = directory / f"{record.id}.json"
    path.write_text(
        json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record


def load_conversation(
    conversation_id: str, store_dir: PathLike = DEFAULT_STORE_DIR
) -> ConversationRecord:
    """Charge une conversation sauvegardée. Lève FileNotFoundError si absente."""
    path = _ensure_store_dir(store_dir) / f"{conversation_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Conversation introuvable : {conversation_id}")
    return ConversationRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_conversations(store_dir: PathLike = DEFAULT_STORE_DIR) -> List[ConversationRecord]:
    """Liste toutes les conversations sauvegardées, les plus récemment mises
    à jour en premier. Les fichiers corrompus ou incomplets sont ignorés."""
    directory = _ensure_store_dir(store_dir)
    records: List[ConversationRecord] = []
    for path in directory.glob("*.json"):
        try:
            records.append(
                ConversationRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            )
        except (json.JSONDecodeError, KeyError):
            continue
    records.sort(key=lambda r: r.updated_at, reverse=True)
    return records


def delete_conversation(conversation_id: str, store_dir: PathLike = DEFAULT_STORE_DIR) -> bool:
    """Supprime une conversation sauvegardée. Renvoie True si un fichier a été supprimé."""
    path = _ensure_store_dir(store_dir) / f"{conversation_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
