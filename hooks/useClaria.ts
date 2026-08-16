"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuid } from "uuid";
import { chunkText } from "@/lib/chunk";
import { search, computeConfidence } from "@/lib/search";
import { buildMessages, NO_INFO_PHRASE } from "@/lib/prompt";
import * as db from "@/lib/db";
import type {
  ChatMessage,
  ClariaSettings,
  Conversation,
  DocChunk,
  DocumentMeta,
  QueryLogEntry,
  SourceRef,
} from "@/lib/types";
import { DEFAULT_SETTINGS } from "@/lib/types";

async function embedTexts(texts: string[]): Promise<number[][]> {
  const res = await fetch("/api/embed", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ texts }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error ?? "Erreur d'embeddings inconnue.");
  return data.embeddings;
}

export function useClaria() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [chunks, setChunks] = useState<DocChunk[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [queryLog, setQueryLog] = useState<QueryLogEntry[]>([]);
  const [settings, setSettings] = useState<ClariaSettings>(DEFAULT_SETTINGS);

  const [indexing, setIndexing] = useState(false);
  const [indexProgress, setIndexProgress] = useState<{ done: number; total: number; label: string } | null>(null);
  const [asking, setAsking] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // -- Hydratation depuis IndexedDB au premier montage ----------------------
  useEffect(() => {
    (async () => {
      const [docs, ch, convs, currentId, savedSettings] = await Promise.all([
        db.loadDocuments(),
        db.loadChunks(),
        db.loadConversations(),
        db.loadCurrentConversationId(),
        db.loadSettings(),
      ]);
      setDocuments(docs);
      setChunks(ch);
      setConversations(convs);
      if (savedSettings) setSettings(savedSettings);

      const activeId = currentId && convs.some((c) => c.id === currentId) ? currentId : null;
      setCurrentConversationId(activeId);
      setMessages(activeId ? convs.find((c) => c.id === activeId)?.messages ?? [] : []);
      setHydrated(true);
    })();
  }, []);

  useEffect(() => {
    if (hydrated) db.saveSettings(settings);
  }, [settings, hydrated]);

  // -- Documents --------------------------------------------------------
  const addDocuments = useCallback(
    async (files: File[]) => {
      setIndexing(true);
      setGlobalError(null);
      const total = files.length;
      let done = 0;

      const newChunks: DocChunk[] = [...chunks];
      const newDocs: DocumentMeta[] = [...documents];

      for (const file of files) {
        if (newDocs.some((d) => d.name === file.name)) {
          done++;
          continue;
        }
        try {
          setIndexProgress({ done, total, label: `Lecture de ${file.name}...` });
          const formData = new FormData();
          formData.append("file", file);
          const parseRes = await fetch("/api/parse", { method: "POST", body: formData });
          const parseData = await parseRes.json();
          if (!parseRes.ok) throw new Error(parseData.error ?? "Erreur de lecture.");

          const pages: { page: number | null; text: string }[] = parseData.pages;

          const docId = uuid();
          const pieces: { page: number | null; text: string }[] = [];
          for (const p of pages) {
            for (const piece of chunkText(p.text, settings.chunkSize, settings.chunkOverlap)) {
              pieces.push({ page: p.page, text: piece });
            }
          }

          if (pieces.length === 0) {
            setGlobalError(`Aucun texte exploitable trouvé dans '${file.name}'.`);
            done++;
            continue;
          }

          setIndexProgress({ done, total, label: `Calcul des embeddings pour ${file.name}...` });
          const embeddings = await embedTexts(pieces.map((p) => p.text));

          const docChunks: DocChunk[] = pieces.map((p, i) => ({
            id: uuid(),
            docId,
            docName: file.name,
            page: p.page,
            text: p.text,
            embedding: embeddings[i],
            ocr: false,
          }));

          newChunks.push(...docChunks);
          const meta: DocumentMeta = {
            id: docId,
            name: file.name,
            addedAt: Date.now(),
            chunkCount: docChunks.length,
            ocrPages: 0,
            summary: null,
            summaryLoading: true,
          };
          newDocs.push(meta);

          setChunks([...newChunks]);
          setDocuments([...newDocs]);
          await db.saveChunks(newChunks);
          await db.saveDocuments(newDocs);

          // Résumé généré en arrière-plan (n'empêche pas l'indexation de continuer).
          const fullText = pages.map((p) => p.text).join("\n\n");
          fetch("/api/summarize", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ text: fullText, docName: file.name }),
          })
            .then((r) => r.json())
            .then((data) => {
              setDocuments((prev) => {
                const updated = prev.map((d) =>
                  d.id === docId
                    ? { ...d, summary: data.summary ?? data.error ?? "Résumé indisponible.", summaryLoading: false }
                    : d
                );
                db.saveDocuments(updated);
                return updated;
              });
            })
            .catch(() => {
              setDocuments((prev) => {
                const updated = prev.map((d) =>
                  d.id === docId ? { ...d, summary: "Résumé indisponible.", summaryLoading: false } : d
                );
                db.saveDocuments(updated);
                return updated;
              });
            });
        } catch (err: any) {
          setGlobalError(err?.message ?? String(err));
        }
        done++;
        setIndexProgress({ done, total, label: `${file.name} indexé.` });
      }

      setIndexing(false);
      setIndexProgress(null);
    },
    [chunks, documents, settings]
  );

  const removeDocument = useCallback(
    async (docId: string) => {
      const newChunks = chunks.filter((c) => c.docId !== docId);
      const newDocs = documents.filter((d) => d.id !== docId);
      setChunks(newChunks);
      setDocuments(newDocs);
      await db.saveChunks(newChunks);
      await db.saveDocuments(newDocs);
    },
    [chunks, documents]
  );

  // -- Conversations ------------------------------------------------------
  const persistConversation = useCallback(
    async (msgs: ChatMessage[], docIds: string[]) => {
      const existing = conversations.find((c) => c.id === currentConversationId);
      const title =
        existing?.title ||
        msgs.find((m) => m.role === "user")?.content.slice(0, 60) ||
        "Nouvelle conversation";

      const id = currentConversationId ?? uuid();
      const updated: Conversation = {
        id,
        title,
        updatedAt: Date.now(),
        messages: msgs,
        documentIds: docIds,
      };
      const others = conversations.filter((c) => c.id !== id);
      const nextConvs = [updated, ...others].sort((a, b) => b.updatedAt - a.updatedAt);
      setConversations(nextConvs);
      setCurrentConversationId(id);
      await db.saveConversations(nextConvs);
      await db.saveCurrentConversationId(id);
    },
    [conversations, currentConversationId]
  );

  const startNewConversation = useCallback(async () => {
    setMessages([]);
    setCurrentConversationId(null);
    await db.saveCurrentConversationId(null);
  }, []);

  const loadConversation = useCallback(
    async (id: string) => {
      const conv = conversations.find((c) => c.id === id);
      if (!conv) return;
      setMessages(conv.messages);
      setCurrentConversationId(id);
      await db.saveCurrentConversationId(id);
    },
    [conversations]
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      const next = conversations.filter((c) => c.id !== id);
      setConversations(next);
      await db.saveConversations(next);
      if (id === currentConversationId) {
        setMessages([]);
        setCurrentConversationId(null);
        await db.saveCurrentConversationId(null);
      }
    },
    [conversations, currentConversationId]
  );

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      const next = conversations.map((c) => (c.id === id ? { ...c, title } : c));
      setConversations(next);
      await db.saveConversations(next);
    },
    [conversations]
  );

  // -- Question / réponse --------------------------------------------------
  const askQuestion = useCallback(
    async (question: string) => {
      if (!question.trim() || asking) return;

      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: question,
        createdAt: Date.now(),
      };
      const withUser = [...messages, userMsg];
      setMessages(withUser);
      setAsking(true);

      if (chunks.length === 0) {
        const warn: ChatMessage = {
          id: uuid(),
          role: "assistant",
          content: "Indexe d'abord au moins un document pour que je puisse répondre.",
          createdAt: Date.now(),
        };
        const withWarn = [...withUser, warn];
        setMessages(withWarn);
        await persistConversation(withWarn, documents.map((d) => d.id));
        setAsking(false);
        return;
      }

      const start = performance.now();
      let placeholderId: string | null = null;
      try {
        const [queryEmbedding] = await embedTexts([question]);
        const results = search(
          chunks,
          settings.searchMode,
          queryEmbedding,
          question,
          settings.topK,
          settings.hybridAlpha
        );

        const history = withUser
          .slice(-13, -1)
          .map((m) => ({ role: m.role, content: m.content } as const));

        const chatMessages = buildMessages(question, results, history, []);

        const assistantId = uuid();
        placeholderId = assistantId;
        let assistantContent = "";
        const withAssistantPlaceholder: ChatMessage[] = [
          ...withUser,
          { id: assistantId, role: "assistant", content: "", createdAt: Date.now() },
        ];
        setMessages(withAssistantPlaceholder);

        const controller = new AbortController();
        abortRef.current = controller;

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ messages: chatMessages }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error ?? `Erreur serveur (${res.status}).`);
        }
        if (!res.body) throw new Error("Réponse vide du serveur.");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          assistantContent += decoder.decode(value, { stream: true });
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: assistantContent } : m))
          );
        }

        const sources: SourceRef[] = results.map((r) => ({
          docName: r.chunk.docName,
          page: r.chunk.page,
          text: r.chunk.text,
          score: r.score,
        }));
        const confidence = computeConfidence(results);
        const responseTimeSeconds = (performance.now() - start) / 1000;
        const isAnswerFound = !assistantContent.includes(NO_INFO_PHRASE);

        const finalMessages: ChatMessage[] = withAssistantPlaceholder.map((m) =>
          m.id === assistantId
            ? { ...m, content: assistantContent, sources, confidence }
            : m
        );
        setMessages(finalMessages);

        const logEntry: QueryLogEntry = {
          id: uuid(),
          timestamp: Date.now(),
          question,
          answer: assistantContent,
          confidence,
          sourceDocuments: Array.from(new Set(sources.map((s) => s.docName))),
          responseTimeSeconds,
          searchMode: settings.searchMode,
          usedWebFallback: false,
          isAnswerFound,
        };
        setQueryLog((prev) => [...prev, logEntry]);

        await persistConversation(finalMessages, documents.map((d) => d.id));
      } catch (err: any) {
        const errorText = `Une erreur est survenue : ${err?.message ?? err}`;
        setMessages((prev) => {
          if (placeholderId && prev.some((m) => m.id === placeholderId)) {
            const updated = prev.map((m) =>
              m.id === placeholderId ? { ...m, content: errorText } : m
            );
            persistConversation(updated, documents.map((d) => d.id));
            return updated;
          }
          const withError = [
            ...prev,
            { id: uuid(), role: "assistant" as const, content: errorText, createdAt: Date.now() },
          ];
          persistConversation(withError, documents.map((d) => d.id));
          return withError;
        });
      } finally {
        setAsking(false);
      }
    },
    [asking, messages, chunks, settings, documents, persistConversation]
  );

  return {
    documents,
    chunks,
    conversations,
    currentConversationId,
    messages,
    queryLog,
    settings,
    setSettings,
    indexing,
    indexProgress,
    asking,
    hydrated,
    globalError,
    setGlobalError,
    addDocuments,
    removeDocument,
    askQuestion,
    startNewConversation,
    loadConversation,
    deleteConversation,
    renameConversation,
  };
}
