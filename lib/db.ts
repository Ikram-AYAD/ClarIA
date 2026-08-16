import { get, set, del } from "idb-keyval";
import type { DocChunk, DocumentMeta, Conversation, ClariaSettings } from "./types";

/**
 * Persistance locale (IndexedDB via idb-keyval) : tout reste dans le
 * navigateur de l'utilisateur, aucun serveur/backend ne stocke ses
 * documents. C'est ce qui permet à ClarIA de tourner sans base de données
 * externe, sur un hébergement 100% serverless (Vercel).
 */

const KEYS = {
  chunks: "claria:chunks",
  documents: "claria:documents",
  conversations: "claria:conversations",
  currentConversationId: "claria:current-conversation-id",
  settings: "claria:settings",
} as const;

export async function loadChunks(): Promise<DocChunk[]> {
  return (await get(KEYS.chunks)) ?? [];
}
export async function saveChunks(chunks: DocChunk[]): Promise<void> {
  await set(KEYS.chunks, chunks);
}

export async function loadDocuments(): Promise<DocumentMeta[]> {
  return (await get(KEYS.documents)) ?? [];
}
export async function saveDocuments(docs: DocumentMeta[]): Promise<void> {
  await set(KEYS.documents, docs);
}

export async function loadConversations(): Promise<Conversation[]> {
  return (await get(KEYS.conversations)) ?? [];
}
export async function saveConversations(convs: Conversation[]): Promise<void> {
  await set(KEYS.conversations, convs);
}

export async function loadCurrentConversationId(): Promise<string | null> {
  return (await get(KEYS.currentConversationId)) ?? null;
}
export async function saveCurrentConversationId(id: string | null): Promise<void> {
  await set(KEYS.currentConversationId, id);
}

export async function loadSettings(): Promise<ClariaSettings | null> {
  return (await get(KEYS.settings)) ?? null;
}
export async function saveSettings(settings: ClariaSettings): Promise<void> {
  await set(KEYS.settings, settings);
}

export async function clearAll(): Promise<void> {
  await Promise.all([
    del(KEYS.chunks),
    del(KEYS.documents),
    del(KEYS.conversations),
    del(KEYS.currentConversationId),
  ]);
}
